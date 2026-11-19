# Contributing

## Set up

```bash
python -m pip install -r requirements-dev.txt
python scripts/build.py
python -m pytest
```

## Changing a sheet

1. Edit the sheet's file in `src/`.
2. Add or update a test. The expected answer must be worked out independently (written in the test,
   or in `tests/reference_maths.py`), not copied from the sheet.
3. Run `python -m pytest`.
4. Add a line to `CHANGELOG.md` under an "Unreleased" heading.

## Adding a sheet

1. Copy the closest existing sheet. `src/shared/README.md` explains the shared code.
2. Name it with the next two-digit number and a short name, words joined by underscores:
   `45_Duration.lua`. Keep names to 30 characters.
3. Check every input before using it: a blank field arrives as `nil`. Warn when an input is out of
   range instead of quietly working something out.
4. Add tests for the main result, each warning, and an awkward input such as zero or a negative.
5. Add the sheet to the table in `README.md`, update the sheet counts in `README.md` and
   `docs/LOADING_GUIDE.txt`, and run `python scripts/make_sheet_list.py`. The tests fail until
   these match.

## Changing the shared code

A change in `src/shared/` reaches every sheet that uses it. Keep it small, add a test that fails
without it, and check on a real calculator (`docs/CHECK_ON_CALCULATOR.md`) before releasing.

## Rules the tests enforce

- Lua 5.1 only: no `goto`, `//`, bit operators or `\x` escapes.
- Only the calculator's own functions: no `io`, `os`, `require` or `debug`.
- UTF-8, Unix line endings, spaces not tabs, no trailing spaces, one newline at the end.
- No new global variables after a sheet loads.
- Each redraw under 150,000 Lua instructions.

`scripts/` uses only Python's standard library; please keep it that way. `ruff check .` must pass.

## Releasing

1. Update `VERSION` and move the "Unreleased" notes in `CHANGELOG.md` under the new version.
2. Check on a real calculator (`docs/CHECK_ON_CALCULATOR.md`).
3. Commit, then `git tag v<version>` and `git push origin v<version>`. GitHub builds the zip and
   attaches it to a release automatically.

## Please do not add

Copyrighted material such as textbook pages, published questions or worked solutions to them.
