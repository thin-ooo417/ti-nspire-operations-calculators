"""Hammer every sheet with random keys: nothing may raise, leak NaN, or run away."""

from __future__ import annotations

import random
import re
import zlib

import pytest

from conftest import SHEETS, load, names

POOL = ["", "0", "1", "2", "5", "10", "100", "0.05", "0.5", "0.08", "-1", "-0.5", "1000000000000",
        "0.0000001", "3", "1.5", "-", ".", "-.", "12", "0.3", "60", "3600", "0.95", "1.96", "25", "999999999"]
ODD_KEYS = ["a", "E", " ", "+", "10^(", "sin(", "\u2212", ",", "π", "%", "(", "1e5"]

# The standard form promises never to show these; the other engines print "inf"/"undef"/"n/a" on purpose.
NOT_A_NUMBER = re.compile(r"\bnan\b|\binf\b|1\.#|-?nan\(|#IND|#INF", re.I)

BUDGET = 150_000   # Lua VM instructions for one repaint; the largest measured is about a third of this


def _press_randomly(sheet, rng):
    for _ in range(rng.randint(1, 14)):
        roll = rng.random()
        if roll < 0.40:
            if sheet.has("clearKey"):
                sheet.clear()
            else:
                for _ in range(16):
                    sheet.backspace()
            sheet.type(rng.choice(POOL))
        elif roll < 0.48:
            sheet.char(rng.choice(ODD_KEYS))
        elif roll < 0.72:
            sheet.down()
        elif roll < 0.82:
            sheet.up()
        elif roll < 0.87:
            sheet.right()
        elif roll < 0.90:
            sheet.left()
        elif roll < 0.93:
            sheet.tab()
        elif roll < 0.95:
            sheet.fire("backtabKey")
        elif roll < 0.97:
            sheet.backspace()
        elif roll < 0.98:
            sheet.fire("deleteKey")
        elif roll < 0.99:
            sheet.fire("mouseDown", rng.randint(0, 317), rng.randint(0, 211))
        else:
            sheet.escape()


@pytest.mark.parametrize("name", names())
def test_random_keys(name):
    rng = random.Random(zlib.crc32(name.encode()))
    sheet = load(name)
    is_v2 = b"shared engine v2" in SHEETS[name]
    worst = 0
    for _ in range(200):
        _press_randomly(sheet, rng)
        worst = max(worst, sheet.instructions(sheet.paint))
        texts = sheet.texts()
        assert "error" not in texts, f"{name}: calculation raised: {texts}"
        assert "check inputs" not in texts, f"{name}: calculation raised inside the engine"
        if is_v2:
            leaked = [t for t in texts if NOT_A_NUMBER.search(t)]
            assert not leaked, f"{name}: {leaked}"
    assert sheet.runtime_globals() == set(), "sheets must not create globals after load"
    assert worst <= BUDGET, f"{name}: a repaint took {worst} VM instructions"
