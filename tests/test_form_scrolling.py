"""What the shared scrolling form (form_scrolling.lua) promises; used by operations sheets 01 to 07."""

from __future__ import annotations

import pytest

from calculator_mock import HEIGHT, MINUS_KEY
from conftest import SHEETS, load, names
from form_drivers import Scroll

SCROLL_SHEETS = [n for n in names() if b"Shared field-form engine" in SHEETS[n]]


def test_this_repository_has_form_scroll_sheets():
    assert SCROLL_SHEETS


# --- scrolling engine -------------------------------------------------------------------

def _visible(text) -> bool:
    return 30 <= text.y <= HEIGHT            # baseline below the title bar and on the screen


@pytest.mark.parametrize("name,typed", [
    ("01_Littles_Law", {"I": "120", "T": "30", "Ttg": "24", "cost": "500"}),
    ("02_Serial_Line_Bottleneck", {"t1": "30", "t2": "45", "t3": "60", "t4": "20", "t5": "50", "t6": "40", "nb": "40"}),
    ("03_Parallel_Routes", {"a1": "5", "a2": "6", "b1": "4", "b2": "10", "base": "12"}),
    ("04_Batch_Size_and_Setup", {"S1": "30", "p1": "2", "S2": "60", "p2": "1", "B": "20"}),
    ("05_Utilisation_and_Queues", {"lam": "8", "mu": "10", "cva": "1", "cvs": "1"}),
    ("06_Takt_and_Cycle_Time", {"av": "480", "dm": "240", "p": "1.5", "R": "0.4", "wc": "7"}),
    ("07_SPC_and_Six_Sigma", {"mean": "10", "sd": "0.5", "usl": "12", "lsl": "8.5", "def": "34", "un": "1000", "op": "10"}),
])
def test_scroll_every_result_and_note_can_be_reached(name, typed):
    """Scrolling used to stop while the last field was still on screen, hiding the lower rows."""
    form = Scroll(name).set(typed)
    sheet = form.sheet
    for _ in range(80):
        sheet.up()
    everything = {(t.text, t.y) for t in sheet.paint() if t.y > 22}      # y is relative to scroll 0 here
    seen = set()
    offsets = []
    for _ in range(80):
        drawn = sheet.paint()
        top = min(t.y for t in drawn if t.text == "INPUTS")
        offsets.append(top)
        seen |= {t.text for t in drawn if _visible(t)}
        sheet.down()
    missing = {text for text, _ in everything} - seen
    assert not missing, f"never on screen: {sorted(missing)}"
    assert offsets[-1] == offsets[-2], "scrolling should stop at the end of the content"
    # and the way back up returns to the first field
    for _ in range(80):
        sheet.up()
    assert min(t.y for t in sheet.paint() if t.text == "INPUTS") == offsets[0]


def test_scroll_typing_brings_the_field_back_into_view():
    form = Scroll("02_Serial_Line_Bottleneck").set({"t1": "30", "t2": "45"})
    sheet = form.sheet
    for _ in range(40):
        sheet.down()                          # now deep in the results
    sheet.type("5")
    cursor = [t for t in sheet.paint() if t.text.endswith("|")]
    assert cursor and _visible(cursor[0])


def test_scroll_view_recovers_when_results_shrink():
    form = Scroll("01_Littles_Law").set({"I": "120", "T": "30", "Ttg": "24", "cost": "500"})
    sheet = form.sheet
    for _ in range(60):
        sheet.down()
    sheet.escape()                            # back to defaults: far less to draw
    sheet.paint()
    assert any(t.text == "INPUTS" and _visible(t) for t in sheet.paint())


def test_scroll_input_rules():
    sheet = load("06_Takt_and_Cycle_Time")
    for ch in ("10^(", "e", "x2", " "):       # multi-character key events must not leak in
        sheet.char(ch)
    assert [t.text for t in sheet.paint() if t.text.endswith("|")] == ["|"]
    sheet.char(MINUS_KEY)                     # the handheld's (-) key
    sheet.type("4.5.6")
    assert [t.text for t in sheet.paint() if t.text.endswith("|")] == ["-4.56|"]
    sheet.backspace()
    assert [t.text for t in sheet.paint() if t.text.endswith("|")] == ["-4.5|"]
    sheet.clear()
    assert [t.text for t in sheet.paint() if t.text.endswith("|")] == ["|"]


def test_scroll_escape_restores_defaults():
    form = Scroll("02_Serial_Line_Bottleneck").set({"av": "60", "t1": "5"})
    form.sheet.escape()
    assert ("Enter at least one stage time", "") in form.rows()
    texts = form.sheet.texts()
    assert "0|" in texts and "3600" in texts      # cursor back on the first field, defaults restored


def test_scroll_calculation_errors_are_shown_not_thrown():
    sheet = load("06_Takt_and_Cycle_Time")
    sheet.lua.execute(b"OUTPUTS = function() error('boom') end")
    rows = [t.text for t in sheet.paint()]
    assert "error" in rows and any("boom" in r for r in rows)
