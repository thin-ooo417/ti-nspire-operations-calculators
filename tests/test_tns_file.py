"""The .tns container code: encryption primitive, packing, unpacking, reference files."""

from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path

import pytest

import tns_file
from des_cipher import DES, TripleDES

FIXTURES = Path(__file__).parent / "fixtures" / "reference"

# SHA-256 of the Lua source inside each packer-built reference file. A repository holds the
# ones that belong to its own subject; the tests run over whichever are present.
KNOWN = {
    "luna_reference_finance.tns": "14752591e74e6f96965c167b57d0df99df82f550b454f6643afaddbf2330aadb",
    "luna_reference_accounting.tns": "a0870a4d86fd3f414d36e2983fefebaca9736e9b6d0314376bb22dade40ece03",
    "luna_reference_analytics.tns": "620d990b9d5ac7c6a57dd2c8955ddf1e4db25f5cc5d4913915f90bf3795486a5",
    "luna_reference_operations.tns": "75dc73b5dfaaa1b235b6709f22ccc24ae98d32f43c2eaec58afaedb257839883",
}
PACKER_BUILT = {name: digest for name, digest in KNOWN.items() if (FIXTURES / name).is_file()}


def test_reference_files_are_present_and_known():
    present = {p.name for p in FIXTURES.glob("*.tns")}
    assert PACKER_BUILT and present == set(PACKER_BUILT)


# --- DES ---------------------------------------------------------------------------

def test_des_known_answer():
    cipher = DES(bytes.fromhex("133457799BBCDFF1"))
    assert cipher.encrypt_block(bytes.fromhex("0123456789ABCDEF")) == bytes.fromhex("85E813540F0AB405")
    assert cipher.decrypt_block(bytes.fromhex("85E813540F0AB405")) == bytes.fromhex("0123456789ABCDEF")


def test_des_weak_key_vector():
    # all-zero block under the all-0x01 key (a published single-DES vector)
    assert DES(bytes.fromhex("0101010101010101")).encrypt_block(bytes(8)) == bytes.fromhex("8CA64DE9C1B123A7")


def test_triple_des_with_three_equal_keys_is_single_des():
    key = bytes.fromhex("133457799BBCDFF1")
    block = bytes.fromhex("0123456789ABCDEF")
    assert TripleDES(key * 3).encrypt_block(block) == DES(key).encrypt_block(block)


def test_triple_des_matches_an_independent_implementation():
    cryptography = pytest.importorskip("cryptography")  # noqa: F841 - optional cross-check
    from cryptography.hazmat.primitives.ciphers import Cipher, modes

    try:
        from cryptography.hazmat.decrepit.ciphers import algorithms
    except ImportError:  # older releases
        from cryptography.hazmat.primitives.ciphers import algorithms

    for seed in range(40):
        key = hashlib.sha256(b"key%d" % seed).digest()[:24]
        block = hashlib.sha256(b"block%d" % seed).digest()[:8]
        expected = Cipher(algorithms.TripleDES(key), modes.ECB()).encryptor().update(block)
        assert TripleDES(key).encrypt_block(block) == expected


def test_key_lengths_are_checked():
    with pytest.raises(ValueError):
        DES(b"short")
    with pytest.raises(ValueError):
        TripleDES(b"sixteen byte key")


# --- pack / unpack -------------------------------------------------------------------

@pytest.mark.parametrize("source", [
    b"",
    b"print('hi')\n",
    "local s = \"σ ρ μ − £\"\n".encode(),
    b"local t = a[b[1]]>2  -- contains the CDATA terminator ]]> twice: x[y[1]]>0\n",
    b"]]>" * 50,
    bytes(range(1, 256)) * 40,                    # every byte value except NUL
    b"x = 1\n" * 3000,                            # longer than the 1024-block keystream period
])
def test_round_trip(source):
    packed = tns_file.pack_lua(source)
    assert tns_file.unpack_lua(packed) == source
    assert tns_file.pack_lua(source) == packed     # same input, same bytes


def test_container_layout():
    packed = tns_file.pack_lua(b"x = 1\n")
    assert packed.startswith(b"*TIMLP0500")
    assert tns_file.document_version(packed) == "0500"
    entries = tns_file.read_entries(packed)
    assert [e.name for e in entries] == ["Document.xml", "Problem1.xml"]
    assert all(e.method == 13 for e in entries)
    for entry in entries:                         # Luna records the stored payload's CRC and size
        assert entry.crc == zlib.crc32(entry.payload) and entry.uncompressed_size == len(entry.payload)
    end = packed.rindex(b"TIPD")
    count, total, size, offset = struct.unpack_from("<HHII", packed, end + 8)
    assert (count, total) == (2, 2)
    assert packed[offset:offset + 4] == b"PK\x01\x02" and offset + size == end
    assert len(packed) == end + 22


def test_document_version_can_be_chosen():
    assert tns_file.pack_lua(b"x = 1\n", "0700").startswith(b"*TIMLP0700")
    with pytest.raises(tns_file.TnsError):
        tns_file.pack_lua(b"x = 1\n", "7")


def test_pack_rejects_bad_input():
    with pytest.raises(TypeError):
        tns_file.pack_lua("text, not bytes")
    with pytest.raises(tns_file.TnsError):
        tns_file.pack_lua(b"x = 1\x00")


@pytest.mark.parametrize("data", [b"", b"PK\x03\x04 not a tns", b"%PDF-1.6 a PDF renamed to .tns", b"*TIMLP0500" + b"\x00" * 10])
def test_unpack_rejects_what_it_cannot_read(data):
    with pytest.raises(tns_file.TnsError):
        tns_file.unpack_lua(data)


def test_unpack_rejects_a_corrupted_body():
    packed = bytearray(tns_file.pack_lua(b"print('hi')\n" * 20))
    start = packed.index(b"Problem1.xml") + len(b"Problem1.xml") + 40
    packed[start:start + 16] = bytes(16)
    with pytest.raises(tns_file.TnsError):
        tns_file.unpack_lua(bytes(packed))


def _document_around(xml: bytes) -> bytes:
    """A container whose Problem1.xml body is `xml`, built with the module's own primitives."""
    body = tns_file._BODY_HEADER + tns_file._xor_keystream(tns_file._deflate_raw(xml))
    return (tns_file._local_header(b"*TIMLP0500", b"Document.xml", tns_file._DEFAULT_DOCUMENT_ENTRY)
            + tns_file._DEFAULT_DOCUMENT_ENTRY + tns_file._local_header(b"PK\x03\x04", b"Problem1.xml", body) + body)


def test_unpack_refuses_a_decompression_bomb(monkeypatch):
    monkeypatch.setattr(tns_file, "_MAX_INFLATED", 4096)
    bomb = _document_around(b"<![CDATA[" + b"A" * 100_000 + b"]]>")
    with pytest.raises(tns_file.TnsError, match="refusing to read"):
        tns_file.unpack_lua(bomb)


def test_unpack_reports_a_truncated_body():
    whole = tns_file.pack_lua(b"print('hello')\n" * 200)
    entry = tns_file.read_entries(whole)[1]
    body = entry.payload[:-30]
    cut = (tns_file._local_header(b"*TIMLP0500", b"Document.xml", tns_file._DEFAULT_DOCUMENT_ENTRY)
           + tns_file._DEFAULT_DOCUMENT_ENTRY + tns_file._local_header(b"PK\x03\x04", b"Problem1.xml", body) + body)
    with pytest.raises(tns_file.TnsError, match="truncated|did not inflate"):
        tns_file.unpack_lua(cut)


def test_unpack_requires_a_script():
    with pytest.raises(tns_file.TnsError, match="no script"):
        tns_file.unpack_lua(_document_around(b"TIXC0100-1.0?><prob></prob>"))


# --- the original files ----------------------------------------------------------------

@pytest.mark.parametrize("name,digest", sorted(PACKER_BUILT.items()))
def test_reads_documents_built_by_luna(name, digest):
    lua = tns_file.unpack_lua((FIXTURES / name).read_bytes())
    assert hashlib.sha256(lua).hexdigest() == digest
    assert lua.endswith(b"end\n")


@pytest.mark.parametrize("name", sorted(PACKER_BUILT))
def test_repacking_reproduces_a_luna_document(name):
    """Everything matches byte for byte except the deflate stream, whose exact
    bytes depend on which zlib build compressed it (and the CRC and sizes that
    follow from it)."""
    original = (FIXTURES / name).read_bytes()
    rebuilt = tns_file.pack_lua(tns_file.unpack_lua(original))
    old, new = tns_file.read_entries(original), tns_file.read_entries(rebuilt)
    assert original[:10] == rebuilt[:10]
    assert old[0] == new[0]                                   # Document.xml is identical
    assert old[1].payload[:40] == new[1].payload[:40]         # same body header
    assert (old[1].name, old[1].method) == (new[1].name, new[1].method)
    assert original[-22:-10] == rebuilt[-22:-10]              # same end record up to the sizes
    if old[1].payload == new[1].payload:
        assert original == rebuilt


def test_explains_documents_resaved_by_ti_software():
    """TI software gives each entry its own key, carried in a different 40-byte header."""
    packed = tns_file.pack_lua(b"x = 1\n")
    start = packed.index(b"Problem1.xml") + len(b"Problem1.xml")
    resaved = packed[:start] + bytes(reversed(packed[start:start + 40])) + packed[start + 40:]
    with pytest.raises(tns_file.TnsError, match="re-saved by TI software"):
        tns_file.unpack_lua(resaved)


# --- command line ------------------------------------------------------------------------

def test_command_line_round_trip(tmp_path, capsys):
    source = tmp_path / "sheet.lua"
    source.write_bytes(b"function on.paint(gc) gc:drawString('hi', 0, 0, 'top') end\n")
    assert tns_file._main(["pack", str(source), str(tmp_path / "sheet.tns")]) == 0
    assert tns_file._main(["unpack", str(tmp_path / "sheet.tns"), str(tmp_path / "back.lua")]) == 0
    assert (tmp_path / "back.lua").read_bytes() == source.read_bytes()
    assert tns_file._main(["info", str(tmp_path / "sheet.tns")]) == 0
    assert "Problem1.xml" in capsys.readouterr().out
    assert tns_file._main(["unpack", str(source), str(tmp_path / "nope.lua")]) == 1
