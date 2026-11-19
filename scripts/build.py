#!/usr/bin/env python3
"""Build every calculator sheet in src/ into a .tns document in dist/.

A sheet is a short Lua file holding its title, fields and formulas. Shared code
(the form layouts and a few maths helpers in src/shared/) is pulled in with a comment line:

    --@include shared/form_standard.lua

The path is relative to src/. This script expands those lines, checks the
result compiles as Lua 5.1 (the handheld's Lua version), packs it and unpacks
it again to confirm the document holds exactly the source that went in.

    python scripts/build.py            # build everything into dist/
    python scripts/build.py --zip      # also write dist/<name>-<version>.zip
    python scripts/build.py --check    # fail if dist/ is missing or out of date

dist/ and the zip also get README.txt, the guide to loading the sheets onto a
handheld. Its text lives in docs/LOADING_GUIDE.txt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import tns_file

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SHARED_DIRS = ("shared",)  # included by sheets, never built on their own
INCLUDE = b"--@include "
PROJECT = "ti-nspire-operations-calculators"
LOADING_GUIDE = ROOT / "docs" / "LOADING_GUIDE.txt"   # shipped with the sheets as README.txt
README_NAME = "README.txt"


class BuildError(Exception):
    pass


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="ascii").strip()


def handheld_readme() -> bytes:
    """The loading guide as shipped next to the .tns files.

    Plain ASCII with CRLF line endings so it opens cleanly in any text editor,
    with the version added as a last line.
    """
    try:
        text = LOADING_GUIDE.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise BuildError(f"cannot read {LOADING_GUIDE.name} as ASCII text: {exc}") from exc
    if "\r" in text:
        raise BuildError(f"{LOADING_GUIDE.name}: contains CR line endings; sources must use LF only")
    text = text.rstrip("\n") + f"\n\nVersion {version()}. Built from the {PROJECT} repository.\n"
    return text.replace("\n", "\r\n").encode("ascii")


def sheet_sources() -> list[Path]:
    sheets = []
    for folder in sorted(p for p in SRC.iterdir() if p.is_dir() and p.name not in SHARED_DIRS):
        sheets.extend(sorted(folder.glob("*.lua")))
    if not sheets:
        raise BuildError(f"no sheets found under {SRC}")
    return sheets


def expand(path: Path, _stack: tuple[Path, ...] = ()) -> bytes:
    """Return the sheet with every --@include line replaced by the file it names."""
    if path in _stack:
        chain = " -> ".join(p.name for p in (*_stack, path))
        raise BuildError(f"include cycle: {chain}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc
    rel = path.relative_to(ROOT)
    if b"\r" in data:
        raise BuildError(f"{rel}: contains CR line endings; sources must use LF only")
    if data and not data.endswith(b"\n"):
        raise BuildError(f"{rel}: must end with a newline")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BuildError(f"{rel}: not valid UTF-8 ({exc})") from exc

    out = []
    for number, line in enumerate(data.splitlines(keepends=True), start=1):
        if line.startswith(INCLUDE):
            target = line[len(INCLUDE):].strip().decode("utf-8")
            included = (SRC / target).resolve()
            if SRC.resolve() not in included.parents:
                raise BuildError(f"{rel}:{number}: include escapes src/: {target}")
            if not included.is_file():
                raise BuildError(f"{rel}:{number}: include not found: {target}")
            out.append(expand(included, (*_stack, path)))
        elif line.lstrip().startswith(b"--@"):
            raise BuildError(f"{rel}:{number}: unknown directive {line.strip().decode('utf-8', 'replace')}")
        else:
            out.append(line)
    return b"".join(out)


def syntax_checker():
    """Return (name, function) for the best available Lua 5.1 syntax check, or (None, None)."""
    luac = shutil.which("luac5.1")
    if luac:
        def check_luac(name: str, source: bytes) -> None:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "sheet.lua"
                path.write_bytes(source)
                done = subprocess.run([luac, "-p", str(path)], capture_output=True, text=True)
            if done.returncode != 0:
                raise BuildError(f"{name}: Lua 5.1 syntax error: {done.stderr.strip()}")
        return "luac5.1", check_luac
    try:
        import lupa.lua51 as lua51
    except ImportError:
        return None, None
    loadstring = lua51.LuaRuntime(encoding=None).eval(b"loadstring")

    def check_lupa(name: str, source: bytes) -> None:
        result = loadstring(source, b"@" + name.encode())
        if isinstance(result, tuple):
            raise BuildError(f"{name}: Lua 5.1 syntax error: {result[1].decode('utf-8', 'replace')}")
    return "lupa (Lua 5.1)", check_lupa


def build_all(require_syntax_check: bool) -> dict[str, dict]:
    """Expand, check and pack every sheet. Returns {relative .tns path: record}."""
    checker_name, check = syntax_checker()
    if check is None:
        message = "no Lua 5.1 syntax checker found (install lua5.1 or `pip install lupa`)"
        if require_syntax_check:
            raise BuildError(message)
        print(f"warning: {message}; building without the syntax gate", file=sys.stderr)

    seen: dict[str, Path] = {}
    built: dict[str, dict] = {}
    for source in sheet_sources():
        stem = source.stem
        if stem.lower() in seen:
            raise BuildError(f"duplicate sheet name {stem!r}: {seen[stem.lower()]} and {source}")
        seen[stem.lower()] = source
        lua = expand(source)
        if check is not None:
            check(str(source.relative_to(ROOT)), lua)
        packed = tns_file.pack_lua(lua)
        if tns_file.unpack_lua(packed) != lua:
            raise BuildError(f"{source.relative_to(ROOT)}: round-trip check failed")
        key = f"{source.parent.name}/{stem}.tns"
        built[key] = {
            "source": source.relative_to(ROOT).as_posix(),
            "lua": lua,
            "tns": packed,
            "lua_sha256": hashlib.sha256(lua).hexdigest(),
            "tns_sha256": hashlib.sha256(packed).hexdigest(),
        }
    built["__checker__"] = {"name": checker_name}
    return built


def manifest_of(built: dict[str, dict]) -> dict:
    sheets = {
        key: {
            "source": rec["source"],
            "lua_bytes": len(rec["lua"]),
            "lua_sha256": rec["lua_sha256"],
            "tns_bytes": len(rec["tns"]),
            "tns_sha256": rec["tns_sha256"],
        }
        for key, rec in built.items()
        if not key.startswith("__")
    }
    return {"project": PROJECT, "version": version(), "sheets": sheets}


def write_dist(built: dict[str, dict], out: Path, lua_out: Path | None) -> None:
    for folder in {key.split("/")[0] for key in built if not key.startswith("__")}:
        target = out / folder
        if target.exists():
            for stale in target.glob("*.tns"):
                stale.unlink()
    for key, rec in built.items():
        if key.startswith("__"):
            continue
        path = out / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(rec["tns"])
        if lua_out is not None:
            lua_path = (lua_out / key).with_suffix(".lua")
            lua_path.parent.mkdir(parents=True, exist_ok=True)
            lua_path.write_bytes(rec["lua"])
    (out / README_NAME).write_bytes(handheld_readme())
    (out / "manifest.json").write_text(json.dumps(manifest_of(built), indent=2) + "\n", encoding="utf-8")


def write_zip(built: dict[str, dict], out: Path) -> Path:
    path = out / f"{PROJECT}-{version()}.zip"
    members = {README_NAME: handheld_readme()}
    members.update({key: built[key]["tns"] for key in sorted(k for k in built if not k.startswith("__"))})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))  # fixed stamp: repeatable zip
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return path


def _show(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def check_dist(built: dict[str, dict], out: Path) -> list[str]:
    problems = []
    expected = {key for key in built if not key.startswith("__")}
    for key in sorted(expected):
        path = out / key
        if not path.is_file():
            problems.append(f"missing: {_show(path)}")
            continue
        try:
            stored = tns_file.unpack_lua(path.read_bytes())
        except tns_file.TnsError as exc:
            problems.append(f"unreadable: {_show(path)} ({exc})")
            continue
        if stored != built[key]["lua"]:
            problems.append(f"out of date: {_show(path)}")
    readme = out / README_NAME
    if not readme.is_file():
        problems.append(f"missing: {_show(readme)}")
    elif readme.read_bytes() != handheld_readme():
        problems.append(f"out of date: {_show(readme)}")
    if out.is_dir():
        for path in sorted(out.rglob("*.tns")):
            if path.relative_to(out).as_posix() not in expected:
                problems.append(f"not built from src/: {_show(path)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the calculator sheets into .tns documents.")
    parser.add_argument("--out", type=Path, default=ROOT / "dist", help="output folder (default: dist/)")
    parser.add_argument("--lua-out", type=Path, default=ROOT / "build" / "lua",
                        help="where to write the expanded Lua sources (default: build/lua/)")
    parser.add_argument("--zip", action="store_true", help="also write a zip of all .tns files")
    parser.add_argument("--check", action="store_true",
                        help="do not write; fail if the output folder does not match src/")
    parser.add_argument("--no-syntax-check", action="store_true",
                        help="build even when no Lua 5.1 syntax checker is available")
    args = parser.parse_args(argv)

    try:
        built = build_all(require_syntax_check=not args.no_syntax_check)
        count = sum(1 for key in built if not key.startswith("__"))
        if args.check:
            problems = check_dist(built, args.out)
            for line in problems:
                print(line, file=sys.stderr)
            if problems:
                print(f"{len(problems)} problem(s); run `python scripts/build.py`", file=sys.stderr)
                return 1
            print(f"{count} sheets in {args.out} match src/")
            return 0
        write_dist(built, args.out, args.lua_out)
        print(f"built {count} sheets into {args.out} (syntax gate: {built['__checker__']['name'] or 'none'}; "
              "round-trip verified)")
        if args.zip:
            print(f"wrote {write_zip(built, args.out)}")
    except (BuildError, tns_file.TnsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
