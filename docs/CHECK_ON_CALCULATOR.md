# Checking on a real calculator

The automated tests run on a computer and cannot show that a sheet looks right on a TI-Nspire.
Before you rely on a new build, and after any change to `src/shared/`, work through this list.
It takes about ten minutes. `docs/LOADING_GUIDE.txt` explains how to copy the files across.

## 1. One sheet of each layout

Words in square brackets are keys to press; the rest are numbers to type.

| Sheet | Press | You should see |
|---|---|---|
| `01_Littles_Law` | [down] 4 [down] 30 | Inventory I  <-- solved 120.00 |
| `08_Process_Capacity` | 30 [enter] 0.1 [enter] 4 [enter] 2 [enter] 3 | Throughput R/hr 27 |

For each, also check:

- the title, labels and boxes are all on screen and nothing overlaps;
- a letter key does nothing;
- the `(-)` key types a minus sign in an empty field.

## 2. Changes in version 1.0.0

| Check | How |
|---|---|
| Results below the screen can be reached | `02_Serial_Line_Bottleneck`: enter stage times 30, 45, 60. Press down past the last field until the screen stops moving. "WIP  I = R x T" and the notes should come into view, and up comes back to the fields. |
| The `(-)` key | `06_Takt_and_Cycle_Time`: press `(-)` then 5 in an empty field. It should read -5. |
| The process map | `08_Process_Capacity`: 30, 0.1, 4, 2, 3 (enter between them), then right. Expect "Bottleneck: S2   20/hr"; esc goes back to the inputs. |

## If something is wrong

Note the sheet, what you typed and what the screen showed, and open an issue.
