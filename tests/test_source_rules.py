"""Rules every source file and every built sheet has to meet."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from calculator_mock import DOCUMENTED_EVENTS
from conftest import ROOT, SHEET_FOLDER, SHEETS, load, names

SRC = ROOT / "src"
LUA_FILES = sorted(SRC.rglob("*.lua"))

# Libraries and functions the handheld's script sandbox does not provide.
FORBIDDEN = re.compile(rb"\b(io|os|debug|package)\s*\.|\b(require|dofile|loadfile|loadstring|module|setfenv|getfenv)\s*[(\"']")

# Syntax from Lua 5.2 and later that Lua 5.1 either rejects or reads differently.
NEWER_LUA = re.compile(rb"//|<<|>>|\bgoto\b|::\w+::|\\z|\\x[0-9a-fA-F]{2}|\\u\{")


@pytest.mark.parametrize("path", LUA_FILES, ids=lambda p: p.relative_to(SRC).as_posix())
def test_source_file_hygiene(path: Path):
    data = path.read_bytes()
    assert b"\r" not in data, "LF line endings only"
    assert b"\t" not in data, "indent with spaces"
    assert data.endswith(b"\n") and not data.endswith(b"\n\n\n"), "end with one newline"
    data.decode("utf-8")
    assert not data.startswith(b"\xef\xbb\xbf"), "no byte-order mark"
    for number, line in enumerate(data.split(b"\n"), start=1):
        assert line == line.rstrip() or line.strip() == b"", f"line {number}: trailing space"


@pytest.mark.parametrize("name", names())
def test_sheet_uses_only_what_the_handheld_provides(name):
    code = re.sub(rb"--[^\n]*", b"", SHEETS[name])            # ignore comments
    assert not FORBIDDEN.search(code), FORBIDDEN.search(code)
    strings_removed = re.sub(rb'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', b'""', code)
    assert not NEWER_LUA.search(strings_removed), NEWER_LUA.search(strings_removed)


@pytest.mark.parametrize("name", names())
def test_sheet_defines_only_documented_event_handlers(name):
    sheet = load(name)
    handlers = sheet.handlers()
    assert "paint" in handlers and "charIn" in handlers
    assert handlers <= DOCUMENTED_EVENTS, sorted(handlers - DOCUMENTED_EVENTS)


@pytest.mark.parametrize("name", names())
def test_sheet_fits_a_handheld_document(name):
    # a generous ceiling; the largest sheet is about 13 kB of Lua
    assert len(SHEETS[name]) < 64 * 1024


def test_shared_files_are_all_used():
    included = set()
    for path in LUA_FILES:
        included |= {m.decode() for m in re.findall(rb"^--@include (\S+)$", path.read_bytes(), re.M)}
    shared = {p.relative_to(SRC).as_posix() for p in LUA_FILES if p.parent.name == "shared"}
    assert included == shared


def test_api_level_declarations_are_as_documented():
    """Analytics sheets declare API level 1.0; the others leave it to the document (2.0)."""
    for name in names():
        declared = re.search(rb"^platform\.apilevel\s*=\s*'([\d.]+)'", SHEETS[name], re.M)
        if SHEET_FOLDER[name] == "analytics":
            assert declared and declared.group(1) == b"1.0" and SHEETS[name].startswith(b"platform.apilevel"), name
        else:
            assert declared is None, name
