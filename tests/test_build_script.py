"""The build script: include expansion, checks, outputs."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile

import pytest

import build
import tns_file


def _sheets(built):
    return {key: rec for key, rec in built.items() if not key.startswith("__")}


def test_builds_every_sheet_in_src(built):
    sheets = _sheets(built)
    expected = {f"{p.parent.name}/{p.stem}.tns" for p in build.sheet_sources()}
    assert sheets and set(sheets) == expected


def test_a_lua_51_syntax_gate_ran(built):
    assert built["__checker__"]["name"] in ("luac5.1", "lupa (Lua 5.1)")


def test_every_document_holds_exactly_its_expanded_source(built):
    for key, rec in _sheets(built).items():
        assert tns_file.unpack_lua(rec["tns"]) == rec["lua"], key
        assert b"--@include" not in rec["lua"], key


def test_build_is_repeatable(built):
    again = build.build_all(require_syntax_check=True)
    for key, rec in _sheets(built).items():
        assert again[key]["tns"] == rec["tns"], key


def test_sheet_names_are_unique_and_simple(built):
    stems = [key.split("/")[1][:-4] for key in _sheets(built)]
    assert len({s.lower() for s in stems}) == len(stems)
    for stem in stems:
        # two-digit number, then words joined by underscores; short enough for the handheld's file list
        assert re.fullmatch(r"\d\d_[A-Za-z0-9]+(_[A-Za-z0-9]+)*", stem), stem
        assert len(stem) <= 30, stem
    for folder in {key.split("/")[0] for key in _sheets(built)}:
        assert re.fullmatch(r"[a-z]+", folder), folder


def test_write_check_and_zip(built, tmp_path):
    out = tmp_path / "dist"
    build.write_dist(built, out, tmp_path / "lua")
    assert build.check_dist(built, out) == []
    sheets = _sheets(built)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["version"] == build.version() and len(manifest["sheets"]) == len(sheets)
    key = sorted(sheets)[0]
    assert manifest["sheets"][key]["tns_sha256"] == hashlib.sha256((out / key).read_bytes()).hexdigest()
    assert (tmp_path / "lua" / key).with_suffix(".lua").read_bytes() == built[key]["lua"]

    assert (out / "README.txt").read_bytes() == build.handheld_readme()

    archive = build.write_zip(built, out)
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        assert names[0] == "README.txt" and z.read("README.txt") == build.handheld_readme()
        assert len(names) == len(sheets) + 1 and sum(n.endswith(".tns") for n in names) == len(sheets)
        assert z.read(key) == built[key]["tns"]
    first = archive.read_bytes()
    assert build.write_zip(built, out).read_bytes() == first          # the zip is repeatable too


def test_check_reports_stale_missing_and_stray_files(built, tmp_path):
    out = tmp_path / "dist"
    build.write_dist(built, out, None)
    first, second = sorted(_sheets(built))[:2]
    (out / first).unlink()
    (out / second).write_bytes(tns_file.pack_lua(b"-- something else\n"))
    (out / second).with_name("Stray.tns").write_bytes(tns_file.pack_lua(b"-- stray\n"))
    problems = "\n".join(build.check_dist(built, out))
    assert "missing" in problems and "out of date" in problems and "not built from src/" in problems


def test_handheld_readme_is_the_loading_guide_with_a_version_line():
    shipped = build.handheld_readme()
    shipped.decode("ascii")
    assert b"\r\n" in shipped and b"\n" not in shipped.replace(b"\r\n", b"")     # CRLF throughout
    source = (build.ROOT / "docs" / "LOADING_GUIDE.txt").read_bytes()
    assert shipped.replace(b"\r\n", b"\n").startswith(source.rstrip(b"\n"))
    last = shipped.decode("ascii").rstrip().splitlines()[-1]
    assert last == f"Version {build.version()}. Built from the {build.PROJECT} repository."


def test_check_notices_a_missing_or_edited_readme(built, tmp_path):
    out = tmp_path / "dist"
    build.write_dist(built, out, None)
    (out / "README.txt").write_bytes(b"something else\r\n")
    assert any("out of date" in line and "README.txt" in line for line in build.check_dist(built, out))
    (out / "README.txt").unlink()
    assert any("missing" in line and "README.txt" in line for line in build.check_dist(built, out))


def _fake_tree(tmp_path, monkeypatch, sheet: bytes, shared: dict[str, bytes] | None = None):
    src = tmp_path / "src"
    (src / "demo").mkdir(parents=True)
    (src / "shared").mkdir()
    (src / "demo" / "X_01_Demo.lua").write_bytes(sheet)
    for rel, data in (shared or {}).items():
        (src / rel).write_bytes(data)
    (tmp_path / "VERSION").write_text("0.0.0\n")
    monkeypatch.setattr(build, "ROOT", tmp_path)
    monkeypatch.setattr(build, "SRC", src)
    return src


def test_include_expansion(tmp_path, monkeypatch):
    _fake_tree(tmp_path, monkeypatch, b"local a = 1\n--@include shared/e.lua\nlocal c = 3\n",
               {"shared/e.lua": b"local b = 2\n"})
    built = build.build_all(require_syntax_check=True)
    assert built["demo/X_01_Demo.tns"]["lua"] == b"local a = 1\nlocal b = 2\nlocal c = 3\n"


@pytest.mark.parametrize("sheet,shared,message", [
    (b"--@include shared/missing.lua\n", {}, "include not found"),
    (b"--@include ../VERSION\n", {}, "escapes src/"),
    (b"--@include shared/a.lua\n", {"shared/a.lua": b"--@include shared/a.lua\n"}, "include cycle"),
    (b"--@inlcude shared/a.lua\n", {"shared/a.lua": b"x = 1\n"}, "unknown directive"),
    (b"x = 1\r\n", {}, "CR line endings"),
    (b"x = 1", {}, "must end with a newline"),
    (b"x = '\xff'\n", {}, "not valid UTF-8"),
    (b"x = = 1\n", {}, "syntax error"),
    (b"goto done\n", {}, "syntax error"),                 # Lua 5.2+ syntax must not get through
])
def test_build_refuses_bad_sources(tmp_path, monkeypatch, sheet, shared, message):
    _fake_tree(tmp_path, monkeypatch, sheet, shared)
    with pytest.raises(build.BuildError, match=message):
        build.build_all(require_syntax_check=True)


def test_duplicate_names_differing_only_by_case_are_refused(tmp_path, monkeypatch):
    src = _fake_tree(tmp_path, monkeypatch, b"x = 1\n")
    (src / "other").mkdir()
    (src / "other" / "x_01_demo.lua").write_bytes(b"x = 2\n")
    with pytest.raises(build.BuildError, match="duplicate sheet name"):
        build.build_all(require_syntax_check=True)


@pytest.mark.skipif(__import__("sys").platform == "win32", reason="uses a shell script as a stand-in")
def test_luac_is_preferred_when_installed(tmp_path, monkeypatch):
    """CI installs luac5.1; check the build calls it and reports its verdict."""
    stub = tmp_path / "luac5.1"
    stub.write_text('#!/bin/sh\n[ "$1" = "-p" ] || exit 2\n'
                    'if grep -q BROKEN "$2"; then echo "luac5.1: $2:1: unexpected symbol" >&2; exit 1; fi\nexit 0\n')
    stub.chmod(0o755)
    monkeypatch.setattr(build.shutil, "which", lambda name: str(stub) if name == "luac5.1" else None)
    name, check = build.syntax_checker()
    assert name == "luac5.1"
    check("ok.lua", b"x = 1\n")
    with pytest.raises(build.BuildError, match="unexpected symbol"):
        check("bad.lua", b"BROKEN\n")


def test_build_without_any_syntax_checker(tmp_path, monkeypatch, capsys):
    _fake_tree(tmp_path, monkeypatch, b"x = 1\n")
    monkeypatch.setattr(build, "syntax_checker", lambda: (None, None))
    with pytest.raises(build.BuildError, match="no Lua 5.1 syntax checker"):
        build.build_all(require_syntax_check=True)
    built = build.build_all(require_syntax_check=False)
    assert "demo/X_01_Demo.tns" in built and "without the syntax gate" in capsys.readouterr().err
