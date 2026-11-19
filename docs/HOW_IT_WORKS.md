# How it works

## From source to calculator file

```
src/operations/<sheet>.lua  ─┐
src/shared/*.lua                 ├─ scripts/build.py ─►  dist/operations/<sheet>.tns
                                 │                       build/lua/operations/<sheet>.lua  (the full script)
```

For each sheet, `build.py`:

1. **Joins** the sheet with the shared files it names on `--@include` lines.
2. **Checks** the result is UTF-8 with Unix line endings and compiles as Lua 5.1, the calculator's
   version. (Newer Lua features would work on a computer and fail only on the calculator.)
3. **Packs** it into a `.tns` file with `scripts/tns_file.py` (see [TNS_FILE_FORMAT.md](TNS_FILE_FORMAT.md)).
4. **Reads it back** and confirms it holds exactly the script that went in.

It also copies `docs/LOADING_GUIDE.txt` to `dist/README.txt`, with Windows line endings so it opens
cleanly in Notepad, and the version added at the end.

## The tests

`tests/calculator_mock.py` runs a sheet in real Lua 5.1 with a stand-in for the calculator's
screen and keys. A test can press keys and read back every line the sheet draws. The stand-in is
strict: unknown drawing calls, misspelt names and stray global variables all fail.

| File | What it checks |
|---|---|
| `test_operations.py` | every sheet's results, warnings and messages |
| `test_form_*.py` | the shared form code: keys, blank and bad entries, number formats, layout |
| `test_random_keys.py` | 200 rounds of random key presses per sheet: no errors, nothing too slow |
| `test_source_rules.py` | Lua 5.1 only, no calculator-unsupported functions, tidy files |
| `test_build_script.py`, `test_tns_file.py` | the build and the `.tns` file code |
| `test_documentation.py` | the README, sheet list and loading guide match the sheets |

`tests/reference_maths.py` holds the independent calculations the results are compared with.
`tests/fixtures/` holds test-only sheets and an old file used to test reading `.tns` files.

## Speed

The calculator has no maths chip and redraws on every key press. `test_random_keys.py` counts the
work done per redraw and fails if any sheet goes over 150,000 Lua instructions.
