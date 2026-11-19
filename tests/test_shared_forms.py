"""Every sheet uses exactly one of the shared form layouts, or is one of the two grid sheets."""

from __future__ import annotations

from conftest import SHEETS, names

ENGINE_MARKERS = {
    "form_v2": b"-- ===== shared engine v2",
    "form_columns": b"-- ============ FORM ENGINE ============",
    "form_scroll": b"--  Shared field-form engine",
}
GRID_SHEETS = {"12_Decision_Table", "16_Descriptive_Statistics"}


def test_every_sheet_uses_exactly_one_engine_or_is_a_grid_sheet():
    for name in names():
        used = [engine for engine, marker in ENGINE_MARKERS.items() if marker in SHEETS[name]]
        if name in GRID_SHEETS:
            assert used == [], name
        else:
            assert len(used) == 1, (name, used)
