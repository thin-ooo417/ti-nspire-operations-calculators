#!/usr/bin/env python3
"""Read and write TI-Nspire .tns documents that hold one Lua script.

The layout written here follows Luna v2.1 (ndless-nspire/Luna, Olivier Armand),
the packer the original calculator files were built with. See docs/TNS_FILE_FORMAT.md
for the layers and THIRD_PARTY_NOTICES.md for where the fixed constants come
from.

Standard library only.

    python scripts/tns_file.py pack   sheet.lua sheet.tns
    python scripts/tns_file.py unpack sheet.tns sheet.lua
    python scripts/tns_file.py info   sheet.tns
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

from des_cipher import TripleDES

# --- fixed values of the Luna layout ---------------------------------------

# Body key and counter base. Luna hardcodes these; they match _BODY_HEADER.
_BODY_KEY = bytes.fromhex("16a7a73268a7ba73" "d9a886a434459410" "3d808cb5dfb3806b")
_COUNTER_BASE = 0x6FE21307
_COUNTER_PERIOD = 1024

# 40-byte header that precedes every encrypted body Luna writes.
_BODY_HEADER = bytes.fromhex(
    "0fced8d28106865b99dda23dd9e94bd431bb50b64db32924706049381c30f899"
    "004b9264e458e6bc"
)

# The Document.xml entry Luna stores in every file (already processed, 304 bytes).
_DEFAULT_DOCUMENT_ENTRY = bytes.fromhex(
    "0fced8d28106865b4a4ac5cea916f2d51da82f6e0022f2f0c1a606774d7ea6c0"
    "3af05c74baaa4460cd58e670d740f69c17dcf09477bfcadef70209c962b15def"
    "22fa5137a0819148e1834dad08312dd0d3e32d60ab13c2982bed395b09243992"
    "2f0c7a4c9574913b0cf460cc7327cb077e7fa91787e2aca23bcca0c4e38e89f0"
    "c0519fc2bece2845c3d41190a6ec53a0fb5b466b41ade953bb97dbb1d268e2f6"
    "360f2636759be91f48ade92967005819c3c01276a04a73f3b1d30918d606dd97"
    "24533e22a4fb82507b7c12884e7d4180fe72922987e85c5672ff29168c425b8b"
    "9ba7d2086dd398ff91a99ef393a82e1cb2a96b6adff6ce2d1517ce6ec04f9a9c"
    "0edf198d2dfa699f11d22012e07914044e628f0a2a18725a8b80b33c9bd56759"
    "4b514de0c33828c3dccd3922128c4055"
)

# Tokenised XML that wraps the script: a problem with one ScriptApp widget,
# script version 512 (API level 2.0), ending at the CDATA opener.
_LUA_PROLOGUE = bytes.fromhex(
    "54495843303130302d312e303f3e3c70726f6220786d6c6e733d2275726e3a54"
    "492e50a85f5b1f0a22207665723d22312e30222070626e616d653d22223e3c73"
    "796d3e0e013c6361726420636c61793d2230222068313d22f10000ff22206832"
    "3d22f10000ff222077313d22f10000ff222077323d22f10000ff223e3c697344"
    "756d6d79436172643e300e033c666c61673e300e043c7764677420786d6c6e73"
    "3a73633d2275726e3a54492e53ac84f22a4170702220747970653d2254492e53"
    "ac84f22a41707022207665723d22312e30223e3c73633a6d466c6167733e300e"
    "063c73633a76616c75653e2d310e073c73633a7363726970742076657273696f"
    "6e3d22353132222069643d2230223e3c215b43444154415b"
)
_LUA_FOOTER = bytes.fromhex("5d5d3e0e080e050e020e00")

_CDATA_OPEN = b"<![CDATA["
_CDATA_CLOSE = b"]]>"
_CDATA_SPLICE = b"]]><![CDATA["

_FIRST_SIGNATURE = b"*TIMLP"  # followed by four version digits
_LOCAL_SIGNATURE = b"PK\x03\x04"
_CENTRAL_SIGNATURE = b"PK\x01\x02"
_END_SIGNATURE = b"TIPD"

_METHOD_TI = 13
_VERSION_NEEDED = 20
_DOS_DATE = 32  # what minizip writes for an all-zero date

DEFAULT_DOCUMENT_VERSION = "0500"

_MAX_INFLATED = 16 * 1024 * 1024  # far above any real script; stops a decompression bomb


class TnsError(ValueError):
    """The bytes are not a .tns document this module can read or write."""


@dataclass(frozen=True)
class Entry:
    name: str
    method: int
    crc: int
    compressed_size: int
    uncompressed_size: int
    payload: bytes


# --- encryption --------------------------------------------------------------

_keystream_cache: bytes | None = None


def _keystream(length: int) -> bytes:
    """Keystream for a body of `length` bytes.

    Block n is 3DES(00 00 00 00 || LE32(base + n mod 1024)), so only 1024
    distinct blocks exist. They are computed once per process.
    """
    global _keystream_cache
    if _keystream_cache is None:
        cipher = TripleDES(_BODY_KEY)
        blocks = []
        for n in range(_COUNTER_PERIOD):
            counter = (_COUNTER_BASE + n) & 0xFFFFFFFF
            blocks.append(cipher.encrypt_block(b"\x00\x00\x00\x00" + struct.pack("<I", counter)))
        _keystream_cache = b"".join(blocks)
    period = len(_keystream_cache)
    repeats = length // period + 1
    return (_keystream_cache * repeats)[:length]


def _xor_keystream(data: bytes) -> bytes:
    if not data:
        return b""
    stream = _keystream(len(data))
    mixed = int.from_bytes(data, "big") ^ int.from_bytes(stream, "big")
    return mixed.to_bytes(len(data), "big")


# --- packing -----------------------------------------------------------------

def _deflate_raw(data: bytes) -> bytes:
    # Same parameters as Luna: default level, raw stream, memLevel 8.
    compressor = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15, 8)
    return compressor.compress(data) + compressor.flush()


def _wrap_lua(lua: bytes) -> bytes:
    # A literal "]]>" would end the CDATA section early, so split it across
    # two sections exactly as Luna does: "]]" + "]]><![CDATA[" + ">".
    body = lua.replace(_CDATA_CLOSE, b"]]" + _CDATA_SPLICE + b">")
    return _LUA_PROLOGUE + body + _LUA_FOOTER


def _local_header(signature: bytes, name: bytes, payload: bytes) -> bytes:
    # Luna (through minizip) records the size and CRC of the stored payload
    # for both size fields; the handheld accepts this.
    fields = struct.pack(
        "<HHHHHIIIHH",
        _VERSION_NEEDED, 0, _METHOD_TI, 0, _DOS_DATE,
        zlib.crc32(payload) & 0xFFFFFFFF, len(payload), len(payload), len(name), 0,
    )
    return signature + fields + name


def _central_header(name: bytes, payload: bytes, offset: int) -> bytes:
    fields = struct.pack(
        "<HHHHHHIIIHHHHHII",
        0, _VERSION_NEEDED, 0, _METHOD_TI, 0, _DOS_DATE,
        zlib.crc32(payload) & 0xFFFFFFFF, len(payload), len(payload), len(name),
        0, 0, 0, 0, 0, offset,
    )
    return _CENTRAL_SIGNATURE + fields + name


def pack_lua(lua: bytes, document_version: str = DEFAULT_DOCUMENT_VERSION) -> bytes:
    """Return the bytes of a .tns document that runs `lua` as its only page."""
    if not isinstance(lua, (bytes, bytearray)):
        raise TypeError("pack_lua expects bytes")
    if len(document_version) != 4 or not document_version.isdigit():
        raise TnsError("document version must be four digits, e.g. '0500'")
    if b"\x00" in lua:
        raise TnsError("Lua source contains a NUL byte")

    problem = _BODY_HEADER + _xor_keystream(_deflate_raw(_wrap_lua(bytes(lua))))
    entries = [(b"Document.xml", _DEFAULT_DOCUMENT_ENTRY), (b"Problem1.xml", problem)]

    out = bytearray()
    central = bytearray()
    for index, (name, payload) in enumerate(entries):
        offset = len(out)
        signature = _FIRST_SIGNATURE + document_version.encode("ascii") if index == 0 else _LOCAL_SIGNATURE
        out += _local_header(signature, name, payload) + payload
        central += _central_header(name, payload, offset)
    central_offset = len(out)
    out += central
    out += _END_SIGNATURE + struct.pack(
        "<HHHHIIH", 0, 0, len(entries), len(entries), len(central), central_offset, 0
    )
    return bytes(out)


# --- unpacking ---------------------------------------------------------------

def read_entries(tns: bytes) -> list[Entry]:
    """Walk the local file records of a .tns container."""
    if not tns.startswith(_FIRST_SIGNATURE):
        raise TnsError("not a TI-Nspire document (missing *TIMLP signature)")
    entries = []
    pos = 0
    while True:
        if tns.startswith(_FIRST_SIGNATURE, pos) and pos == 0:
            pos += len(_FIRST_SIGNATURE) + 4
        elif tns.startswith(_LOCAL_SIGNATURE, pos):
            pos += len(_LOCAL_SIGNATURE)
        else:
            break
        if pos + 26 > len(tns):
            raise TnsError("truncated local header")
        (_ver, _flag, method, _time, _date, crc, csize, usize, name_len, extra_len) = struct.unpack_from(
            "<HHHHHIIIHH", tns, pos
        )
        pos += 26
        name = tns[pos:pos + name_len].decode("ascii", "replace")
        pos += name_len + extra_len
        payload = tns[pos:pos + csize]
        if len(payload) != csize:
            raise TnsError(f"truncated entry {name!r}")
        entries.append(Entry(name, method, crc, csize, usize, payload))
        pos += csize
    if not entries:
        raise TnsError("no entries found")
    return entries


def document_version(tns: bytes) -> str:
    if not tns.startswith(_FIRST_SIGNATURE):
        raise TnsError("not a TI-Nspire document (missing *TIMLP signature)")
    return tns[6:10].decode("ascii", "replace")


def unpack_lua(tns: bytes) -> bytes:
    """Return the exact Lua source stored in a document written by pack_lua or Luna.

    Documents re-saved by the handheld or by TI's desktop software use a
    different, per-file body key and are rejected with a clear message.
    """
    for entry in read_entries(tns):
        if entry.name != "Problem1.xml":
            continue
        if entry.method != _METHOD_TI:
            raise TnsError("Problem1.xml is not stored with TI method 13")
        if entry.payload[:len(_BODY_HEADER)] != _BODY_HEADER:
            raise TnsError(
                "Problem1.xml does not use the fixed Luna header; the document was "
                "probably re-saved by TI software (see docs/TNS_FILE_FORMAT.md)"
            )
        body = _xor_keystream(entry.payload[len(_BODY_HEADER):])
        inflater = zlib.decompressobj(-15)
        try:
            xml = inflater.decompress(body, _MAX_INFLATED + 1)
        except zlib.error as exc:
            raise TnsError(f"Problem1.xml did not inflate: {exc}") from exc
        if len(xml) > _MAX_INFLATED:
            raise TnsError("Problem1.xml inflates to more than 16 MiB; refusing to read it")
        if not inflater.eof:
            raise TnsError("Problem1.xml is truncated")
        start = xml.find(_CDATA_OPEN)
        end = xml.rfind(_CDATA_CLOSE)
        if start < 0 or end < start:
            raise TnsError("Problem1.xml holds no script (no CDATA section)")
        return xml[start + len(_CDATA_OPEN):end].replace(_CDATA_SPLICE, b"")
    raise TnsError("no Problem1.xml entry")


# --- command line ------------------------------------------------------------

def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pack or unpack single-script .tns documents.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_pack = sub.add_parser("pack", help="Lua source -> .tns")
    p_pack.add_argument("lua", type=Path)
    p_pack.add_argument("tns", type=Path)
    p_unpack = sub.add_parser("unpack", help=".tns -> Lua source")
    p_unpack.add_argument("tns", type=Path)
    p_unpack.add_argument("lua", type=Path)
    p_info = sub.add_parser("info", help="list the entries of a .tns")
    p_info.add_argument("tns", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "pack":
            source = args.lua.read_bytes()
            packed = pack_lua(source)
            if unpack_lua(packed) != source:
                raise TnsError("round-trip check failed")
            args.tns.write_bytes(packed)
            print(f"{args.tns}: {len(packed)} bytes, round-trip verified")
        elif args.command == "unpack":
            source = unpack_lua(args.tns.read_bytes())
            args.lua.write_bytes(source)
            print(f"{args.lua}: {len(source)} bytes of Lua")
        else:
            data = args.tns.read_bytes()
            print(f"document version {document_version(data)}")
            for entry in read_entries(data):
                if entry.payload == _DEFAULT_DOCUMENT_ENTRY:
                    kind = "Luna default document"
                elif entry.payload[:40] == _BODY_HEADER:
                    kind = "Luna key (readable with unpack)"
                else:
                    kind = "per-file key (written by TI software)"
                print(f"  {entry.name:14} method {entry.method:2}  {entry.compressed_size:6} bytes  {kind}")
    except (TnsError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main())
