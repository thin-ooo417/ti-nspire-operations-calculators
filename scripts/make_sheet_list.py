#!/usr/bin/env python3
"""Generate docs/SHEET_LIST.md: every sheet with its title, formula and inputs.

The list is read straight from the sheet sources, so it cannot drift from what
the sheets actually show.

    python scripts/make_sheet_list.py            # rewrite docs/SHEET_LIST.md
    python scripts/make_sheet_list.py --check    # fail if docs/SHEET_LIST.md is out of date
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TARGET = ROOT / "docs" / "SHEET_LIST.md"

HEADINGS = {
    "finance": "Business Finance",
    "accounting": "Accounting",
    "analytics": "Analytics",
    "operations": "Technology & Operations",
}


def sets() -> list[tuple[str, str]]:
    """(folder, heading) for each sheet folder present under src/, in a fixed order."""
    present = [(folder, heading) for folder, heading in HEADINGS.items() if (SRC / folder).is_dir()]
    if not present:
        raise SystemExit("no sheet folders found under src/")
    return present

# Sheets whose inputs are a grid rather than a list of labelled fields.
GRID_INPUTS = {
    "12_Decision_Table": "grid: probabilities for up to 4 states, payoffs for up to 3 actions",
    "16_Descriptive_Statistics": "grid: up to 40 rows of X and Y values",
}


def _string(source: str, name: str) -> str:
    match = re.search(rf'^\s*(?:local\s+)?{name}\s*=\s*"((?:[^"\\]|\\.)*)"', source, re.M)
    return match.group(1).replace('\\"', '"') if match else ""


def _labels(source: str) -> list[str]:
    return [m.replace('\\"', '"') for m in re.findall(r'\b(?:lab|lbl)\s*=\s*"((?:[^"\\]|\\.)*)"', source)]


def _cell(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().replace("|", "\\|")


def describe(path: Path) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    engines = re.findall(r"^--@include shared/(form_\w+)\.lua$", source, re.M)
    note = _string(source, "FORMULA") or _string(source, "SUBTITLE") or _string(source, "HINT")
    if path.stem in GRID_INPUTS:
        inputs = GRID_INPUTS[path.stem]
    else:
        inputs = "; ".join(_labels(source))
    return {
        "file": path.stem,
        "title": _string(source, "TITLE"),
        "note": note,
        "inputs": inputs,
        "engine": engines[0] if engines else "its own code",
    }


def render() -> str:
    lines = [
        "# Sheet list",
        "",
        "Made by `python scripts/make_sheet_list.py` from the files in `src/`. Do not edit by hand.",
        "",
        "\"Title on screen\" is what the calculator shows at the top of the sheet. \"Formula or hint\" is the",
        "line printed under it. Inputs are listed in the order they appear on screen.",
        "",
    ]
    total = 0
    for folder, heading in sets():
        sheets = [describe(p) for p in sorted((SRC / folder).glob("*.lua"))]
        total += len(sheets)
        lines += [f"## {heading} ({len(sheets)} sheets)", "", f"Source folder: `src/{folder}/`", "",
                  "| File | Title on screen | Formula or hint | Inputs | Form layout |", "|---|---|---|---|---|"]
        for sheet in sheets:
            lines.append(
                f"| `{sheet['file']}` | {_cell(sheet['title'])} | {_cell(sheet['note'])} | "
                f"{_cell(sheet['inputs'])} | `{sheet['engine']}` |"
            )
        lines.append("")
    lines += [f"Total: {total} sheets.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if docs/SHEET_LIST.md is out of date")
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""
        if current != text:
            print("docs/SHEET_LIST.md is out of date; run `python scripts/make_sheet_list.py`", file=sys.stderr)
            return 1
        print("docs/SHEET_LIST.md is up to date")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
