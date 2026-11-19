"""Shared fixtures: build every sheet once, in memory, and hand out loaded sheets."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import build  # noqa: E402
from calculator_mock import Sheet  # noqa: E402

_BUILT = build.build_all(require_syntax_check=True)
SHEETS: dict[str, bytes] = {
    Path(key).stem: record["lua"] for key, record in _BUILT.items() if not key.startswith("__")
}
SHEET_FOLDER: dict[str, str] = {
    Path(key).stem: key.split("/")[0] for key in _BUILT if not key.startswith("__")
}


def load(name: str) -> Sheet:
    """A freshly loaded sheet, as if just opened on the handheld."""
    sheet = Sheet(SHEETS[name])
    sheet.name = name
    return sheet


FIXTURE_SHEETS = ROOT / "tests" / "fixtures" / "sheets"


def fixture_source(filename: str) -> bytes:
    """A test-only sheet from tests/fixtures/sheets/, with its includes expanded."""
    return build.expand(FIXTURE_SHEETS / filename)


def names(folder: str | None = None) -> list[str]:
    return sorted(name for name in SHEETS if folder is None or SHEET_FOLDER[name] == folder)


@pytest.fixture(scope="session")
def built() -> dict:
    return _BUILT
