"""What the shared standard form (form_standard.lua) promises, independent of any one sheet's formulas.

Tests that need a sheet use tests/fixtures/sheets/demo_form_standard.lua, so they do not depend on
which calculators are in this repository. Tests that run over every sheet use the real ones.
"""

from __future__ import annotations

import pytest

from calculator_mock import HEIGHT, MINUS_KEY
from conftest import SHEETS, fixture_source, names
from form_drivers import RED, V2

V2_SHEETS = [n for n in names() if b"shared engine v2" in SHEETS[n]]


def _demo() -> V2:
    return V2("demo_form_v2", fixture_source("demo_form_standard.lua"))


def test_this_repository_has_form_v2_sheets():
    assert V2_SHEETS


# --- engine v2 -----------------------------------------------------------------------

@pytest.mark.parametrize("name", V2_SHEETS)
def test_v2_empty_sheet_shows_a_prompt_and_no_results(name):
    form = V2(name)
    assert form.notices() == ["Enter values above."]
    assert form.results() == {} and form.warnings() == []


@pytest.mark.parametrize("name", V2_SHEETS)
def test_v2_unparseable_entry_withholds_all_results(name):
    form = V2(name)
    form.sheet.type("5")
    form.sheet.enter()
    form.sheet.char("-")                      # a lone minus is not a number
    assert form.notices() == ["Entry in red is not a number.", "Fix it (Esc clears) to see results."]
    assert form.results() == {} and form.warnings() == []
    assert any(t.rgb == RED and t.text.startswith("-") for t in form.sheet.paint())
    form.sheet.escape()                       # clearing the field brings results back
    assert "Entry in red is not a number." not in form.notices()


def _field_text(sheet, label):
    for line in sheet.lines():
        if line[0].text == label:
            return line[1].text
    raise AssertionError(f"no field {label!r}")


def test_v2_accepts_only_number_keys():
    sheet = _demo().sheet
    for ch in ("a", "e", " ", "+", "*", "10^(", "sin(", ",", "π"):
        sheet.char(ch)
    assert _field_text(sheet, "CF  cashflow") == "_"
    sheet.type("1.5.2")                       # second decimal point is refused
    assert _field_text(sheet, "CF  cashflow") == "1.52_"
    sheet.char("-")                           # minus only in first position
    assert _field_text(sheet, "CF  cashflow") == "1.52_"


def test_v2_maps_the_handheld_minus_key():
    form = _demo()
    form.sheet.char(MINUS_KEY)
    form.sheet.type("250")
    form.set({"r": "0.1", "t": "1"})
    assert abs(float(form.results()["PV"]) - (-250 / 1.1)) < 1e-3


def test_v2_backspace_escape_and_wraparound():
    sheet = _demo().sheet
    sheet.type("123")
    sheet.backspace()
    assert _field_text(sheet, "CF  cashflow") == "12_"
    sheet.escape()
    assert _field_text(sheet, "CF  cashflow") == "_"
    sheet.up()                                # up from the first field wraps to the last
    assert _field_text(sheet, "g  default zero") == "0_"
    sheet.down()
    assert _field_text(sheet, "CF  cashflow") == "_"
    sheet.tab()
    assert _field_text(sheet, "r  rate (decimal)") == "_"


def test_v2_shows_defaults_in_grey_until_typed_over():
    sheet = _demo().sheet
    field = [line for line in sheet.lines() if line[0].text == "g  default zero"][0]
    assert field[1].text == "0" and field[1].rgb == (150, 150, 150)


def test_v2_results_and_warnings():
    form = _demo().set({"cf": "100", "r": "0.1", "t": "1", "g": "2"})
    assert form.results() == {"PV": "90.9091", "rate as %": "10%"}
    assert form.warnings() == ["g is not zero."]


@pytest.mark.parametrize("value,shown", [
    (None, "-"), (float("nan"), "-"), (float("inf"), "-"), (float("-inf"), "-"),
    (0, "0"), (4672.897196, "4672.9"), (0.5, "0.5"), (97.276752, "97.2768"), (1.234e-6, "1.234e-06"),
    (9999.994, "9999.99"),
    # from 10,000 up: two decimals, trimmed, never exponent notation
    (12000, "12000"), (12345.678, "12345.68"), (123456.78, "123456.78"), (4329476.666, "4329476.67"),
    (-2500000.5, "-2500000.5"), (1e12, "1000000000000"), (141461.8449, "141461.84"),
    (1e15, "1e+15"),
])
def test_v2_number_format(value, shown):
    fmt = _demo().sheet.lua.globals()[b"fmt"]
    assert fmt(value).decode() == shown


@pytest.mark.parametrize("value,shown", [(None, "-"), (float("inf"), "-"), (float("nan"), "-"), (0.135, "13.5%"),
                                         (0.0285714, "2.857%"), (-0.05355, "-5.355%"), (1.35, "135%")])
def test_v2_percent_format(value, shown):
    pct = _demo().sheet.lua.globals()[b"pct"]
    assert pct(value).decode() == shown


def _fill_v2_fully(name):
    form = V2(name)
    for key in form.keys:
        form.goto(key)
        form.sheet.type("0.2")
    return form


@pytest.mark.parametrize("name", V2_SHEETS)
def test_v2_everything_drawn_fits_the_screen(name):
    """Fonts are approximated, so this checks row positions rather than pixels."""
    for form in (V2(name), _fill_v2_fully(name)):
        drawn = form.sheet.paint()
        assert all(0 <= t.y <= HEIGHT - 10 for t in drawn), [(t.text, t.y) for t in drawn if t.y > HEIGHT - 10]
        rows = sorted({t.y for t in drawn if t.y >= 34})
        assert all(b - a >= 9 for a, b in zip(rows, rows[1:], strict=False)), f"{name}: rows closer than 9 px"
