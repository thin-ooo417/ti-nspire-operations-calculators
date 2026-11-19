"""Documentation that is generated or that quotes numbers must match the sources."""

from __future__ import annotations

import re

import make_sheet_list
from calculator_mock import HEIGHT
from conftest import ROOT, SHEET_FOLDER, SHEETS, load

KEYS = {"enter", "down", "up", "tab", "left", "right", "backspace", "esc"}


def _loading_guide() -> str:
    return (ROOT / "docs" / "LOADING_GUIDE.txt").read_text(encoding="ascii")


def test_sheet_list_is_up_to_date():
    assert (ROOT / "docs" / "SHEET_LIST.md").read_text(encoding="utf-8") == make_sheet_list.render(), \
        "run `python scripts/make_sheet_list.py`"


def test_sheet_list_names_every_sheet():
    text = make_sheet_list.render()
    for name in SHEETS:
        assert f"`{name}`" in text


def test_readme_counts_match_the_sources():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{len(SHEETS)} calculator sheets" in readme
    rows = re.findall(r"^\| `(\d\d_\w+)` \|", readme, re.M)
    assert sorted(rows) == sorted(SHEETS), "the sheet table in README.md must list every sheet once"


def test_changelog_has_an_entry_for_the_current_version():
    version = (ROOT / "VERSION").read_text(encoding="ascii").strip()
    assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_loading_guide_is_plain_text_that_any_editor_can_show():
    data = (ROOT / "docs" / "LOADING_GUIDE.txt").read_bytes()
    data.decode("ascii")
    assert b"\r" not in data and b"\t" not in data and data.endswith(b"\n")
    assert max(len(line) for line in data.splitlines()) <= 78


def test_loading_guide_counts_and_names_match_the_sources():
    text = _loading_guide()
    assert f"{len(SHEETS)} calculator sheets" in text
    for folder in set(SHEET_FOLDER.values()):
        count = sum(1 for name in SHEETS if SHEET_FOLDER[name] == folder)
        assert re.search(rf"^  {folder}/\s+{count} sheets\b", text, re.M), folder
    named = set(re.findall(r"\b\d\d_[A-Z]\w+", text))
    assert named and named <= set(SHEETS), named - set(SHEETS)


def test_readme_names_every_sheet():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in SHEETS:
        assert f"`{name}`" in readme, name


def _press(sheet, keys: str) -> None:
    """Press '5000 [enter] 0.07': bracketed words are keys, everything else is typed."""
    for token in re.findall(r"\[\w+\]|[^\s\[\]]+", keys):
        if token.startswith("["):
            key = token[1:-1]
            assert key in KEYS, f"unknown key {token}"
            {"enter": sheet.enter, "down": sheet.down, "up": sheet.up, "tab": sheet.tab, "left": sheet.left,
             "right": sheet.right, "backspace": sheet.backspace, "esc": sheet.escape}[key]()
        else:
            sheet.type(token)


def _checks(text: str):
    """Every worked check in the guide, written as

          SHEET_NAME
              press:   5000  [enter]  0.07  [enter]  1
              shows:   PV  4672.9
    """
    pattern = re.compile(r"^  (\d\d_[A-Z]\w+)\n      press:\s+(.+)\n((?:      shows:\s+.+\n)+)", re.M)
    for match in pattern.finditer(text):
        keys = match.group(2).strip()
        shows = []
        for line in match.group(3).splitlines():
            parts = re.split(r"\s{2,}", line.split("shows:", 1)[1].strip())
            shows.append(("  ".join(parts[:-1]), parts[-1]))
        yield match.group(1), keys, shows


def test_loading_guide_examples_show_what_the_sheets_show():
    """Type exactly the keys the guide gives and compare with the results it promises."""
    checks = list(_checks(_loading_guide()))
    assert checks, "the guide should hold at least one worked check"
    for name, keys, shows in checks:
        sheet = load(name)
        _press(sheet, keys)
        drawn = sheet.paint()
        for label, value in shows:
            row = [t for t in drawn if t.text == label]
            assert row, f"{name}: no row {label!r}"
            assert 30 <= row[0].y <= HEIGHT, f"{name}: {label!r} must be on screen without scrolling"
            assert sheet.pairs()[label] == value, f"{name}: {label!r} shows {sheet.pairs()[label]!r}, guide says {value!r}"


def test_readme_example_shows_what_the_sheet_shows():
    """The worked example in README.md: type its keys into the sheet and compare every row."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    match = re.search(r"^\*\*Example\.\*\* [^\n]*?\(`(\d\d_\w+)`\)[^\n]*? Press ([^\n]+?):\n\n"
                      r"\| Row \| Shows \|\n\|---\|---\|\n((?:\|[^\n]*\|\n)+)", readme, re.M)
    assert match, "README.md should hold a worked example"
    name, keys, rows = match.groups()
    sheet = load(name)
    _press(sheet, keys)
    shown = sheet.pairs()
    for line in rows.splitlines():
        label, value = (cell.strip() for cell in line.strip().strip("|").split("|"))
        assert shown.get(label) == value, f"{name}: {label!r} shows {shown.get(label)!r}, README says {value!r}"
