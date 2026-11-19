"""Drive each form engine the way a person would: move to a field, type, read the screen."""

from __future__ import annotations

import math
import re

from calculator_mock import Sheet, number
from conftest import SHEETS, load

BLUE = (20, 60, 120)     # engine v2 result rows
ORANGE = (190, 90, 0)    # warnings in every engine
RED = (200, 0, 0)


# --- tolerances that match what each formatter can actually show ---------------

def tol_sig(expected: float, digits: int) -> float:
    """Half a unit in the last of `digits` significant figures."""
    if expected == 0:
        return 10.0 ** (-digits)
    return 0.5 * 10.0 ** (math.floor(math.log10(abs(expected))) - digits + 1) * 1.0001


def check_v2(text: str, expected: float) -> None:
    """Engine v2: fmt shows 6 significant figures (2 dp from 10,000 up); pct shows 4."""
    shown = number(text)
    if text.strip().endswith("%"):
        tol = tol_sig(expected * 100, 4) / 100
    elif abs(expected) >= 1e4:
        tol = 0.00501
    else:
        tol = tol_sig(expected, 6)
    assert abs(shown - expected) <= tol, f"shows {text!r}, expected {expected!r} (tolerance {tol:g})"


def check_dp(text: str, expected: float, dp: int | None = None) -> None:
    """Fixed-decimal formatters: correct to half a unit in the last place shown."""
    stripped = text.strip()
    percent = stripped.endswith("%")
    body = stripped[:-1] if percent else stripped
    if dp is None:
        dp = len(body.split(".")[1]) if "." in body else 0
    shown = float(body.replace("−", "-"))
    target = expected * 100 if percent else expected
    tol = 0.5 * 10.0 ** (-dp) * 1.0001 + abs(target) * 1e-12
    assert abs(shown - target) <= tol, f"shows {text!r}, expected {target!r} to {dp} dp"


# --- engine v2 ------------------------------------------------------------------

class V2:
    def __init__(self, name: str, source: bytes | None = None) -> None:
        self.name = name
        if source is None:
            source = SHEETS[name]
            self.sheet: Sheet = load(name)
        else:
            self.sheet = Sheet(source)
        header = source.decode("utf-8").split("-- ===== shared engine v2")[0]
        self.keys = re.findall(r'\{k="(\w+)"', header)
        assert self.keys, f"{name}: no fields found"
        self.cur = 0

    def goto(self, key: str) -> None:
        target = self.keys.index(key)
        while self.cur != target:
            self.sheet.enter()
            self.cur = (self.cur + 1) % len(self.keys)

    def set(self, values: dict[str, str]) -> V2:
        for key, text in values.items():
            self.goto(key)
            self.sheet.escape()
            self.sheet.type(text)
        return self

    def rows(self) -> list[tuple[str, str]]:
        out = []
        for line in self.sheet.lines():
            if len(line) == 2 and line[0].rgb == BLUE and line[0].style == "b":
                out.append((line[0].text, line[1].text))
        return out

    def results(self) -> dict[str, str]:
        return dict(self.rows())

    def warnings(self) -> list[str]:
        return [t.text for t in self.sheet.paint() if t.rgb == ORANGE]

    def notices(self) -> list[str]:
        return [t.text for t in self.sheet.paint() if t.style == "i" and t.rgb in (RED, (150, 150, 150))]

    def expect(self, expected: dict[str, float]) -> None:
        shown = self.results()
        for label, value in expected.items():
            assert label in shown, f"{self.name}: no row {label!r}; rows are {list(shown)}"
            check_v2(shown[label], value)


# --- two-column form engine (Analytics) ------------------------------------------

class Columns:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sheet: Sheet = load(name)
        self.count = len(list(self.sheet.lua.globals()[b"FIELDS"].values()))
        self.sel = 1

    def goto(self, index: int) -> None:
        while self.sel != index:
            self.sheet.tab()
            self.sel = self.sel % self.count + 1

    def set(self, values: dict[int, str]) -> Columns:
        for index, text in values.items():
            self.goto(index)
            self.sheet.clear()
            self.sheet.type(text)
        return self

    def rows(self) -> list[tuple[str, str, bool]]:
        return result_rows(self.sheet)

    def results(self) -> dict[str, str]:
        return {label: value for label, value, _ in self.rows()}

    def warnings(self) -> list[tuple[str, str]]:
        return [(label, value) for label, value, warn in self.rows() if warn]

    def expect(self, expected: dict[str, float]) -> None:
        shown = self.results()
        for label, value in expected.items():
            assert label in shown, f"{self.name}: no row {label!r}; rows are {list(shown)}"
            check_dp(shown[label], value)


def result_rows(sheet: Sheet) -> list[tuple[str, str, bool]]:
    """Label/value rows drawn under the RESULTS heading of the Analytics sheets."""
    drawn = sheet.paint()
    heading = [t for t in drawn if t.text == "RESULTS"]
    assert heading, "no RESULTS heading drawn"
    start = heading[0].y
    hint_y = max(t.y for t in drawn)
    rows: dict[float, list] = {}
    for t in drawn:
        if start < t.y < hint_y:
            rows.setdefault(t.y, []).append(t)
    out = []
    for y in sorted(rows):
        line = sorted(rows[y], key=lambda t: t.x)
        if len(line) == 2:
            out.append((line[0].text, line[1].text, line[1].rgb == ORANGE))
    return out


# --- scrolling form engine (Technology & Operations) -----------------------------

class Scroll:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sheet: Sheet = load(name)
        fields = self.sheet.lua.globals()[b"FIELDS"]
        self.keys = [f[b"key"].decode() for f in fields.values()]

    def goto(self, key: str) -> None:
        for _ in range(80):          # back to the first field from wherever we are
            self.sheet.up()
        self.sheet.down(self.keys.index(key))

    def set(self, values: dict[str, str]) -> Scroll:
        for key, text in values.items():
            self.goto(key)
            self.sheet.clear()
            self.sheet.type(text)
        return self

    def rows(self) -> list[tuple[str, str]]:
        drawn = self.sheet.paint()
        heading = [t for t in drawn if t.text == "RESULTS"]
        assert heading, "no RESULTS heading drawn"
        rows: dict[float, list] = {}
        for t in drawn:
            if t.y > heading[0].y and t.style != "i":
                rows.setdefault(t.y, []).append(t)
        out = []
        for y in sorted(rows):
            line = sorted(rows[y], key=lambda t: t.x)
            if len(line) == 2:
                out.append((line[0].text, line[1].text))
        return out

    def results(self) -> dict[str, str]:
        return dict(self.rows())

    def expect(self, expected: dict[str, float | tuple[float, int]]) -> None:
        """Values are checked to 4 dp unless given as (value, dp)."""
        shown = self.results()
        for label, value in expected.items():
            assert label in shown, f"{self.name}: no row {label!r}; rows are {list(shown)}"
            if isinstance(value, tuple):
                check_dp(shown[label], value[0], value[1])
            else:
                check_dp(shown[label], value, 4)
