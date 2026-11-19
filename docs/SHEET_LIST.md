# Sheet list

Made by `python scripts/make_sheet_list.py` from the files in `src/`. Do not edit by hand.

"Title on screen" is what the calculator shows at the top of the sheet. "Formula or hint" is the
line printed under it. Inputs are listed in the order they appear on screen.

## Technology & Operations (8 sheets)

Source folder: `src/operations/`

| File | Title on screen | Formula or hint | Inputs | Form layout |
|---|---|---|---|---|
| `01_Littles_Law` | Little's Law | Leave ONE of I, R, T blank to solve it | Inventory / WIP I; Flow rate R /period; Flow time T (raw); T divisor (min>hr=60); Target T (optional); Periods per year; Cost per unit of flow | `form_scrolling` |
| `02_Serial_Line_Bottleneck` | Serial Line / Bottleneck | Stage times in the same unit as available time | 0=times 1=capacities; Available time; Stage 1 time; Stage 2 time; Stage 3 time; Stage 4 time; Stage 5 time; Stage 6 time; New bottleneck t | `form_scrolling` |
| `03_Parallel_Routes` | Parallel Routes Capacity | Route capacity = min stage; total = sum of routes | Available time; Route A stage 1; Route A stage 2; Route A stage 3; Route B stage 1; Route B stage 2; Route B stage 3; Baseline total | `form_scrolling` |
| `04_Batch_Size_and_Setup` | Batch Size & Setup | p_eff = p + S / B | Stage 1 setup S1; Stage 1 run p1; Stage 2 setup S2; Stage 2 run p2; Batch size B; Available time | `form_scrolling` |
| `05_Utilisation_and_Queues` | Utilisation & Queues | rho = lambda / (c x mu) | Arrival rate lambda; Service rate mu; Servers c; CV arrivals (opt); CV service (opt) | `form_scrolling` |
| `06_Takt_and_Cycle_Time` | Takt / Cycle / Capacity | Pace, rate and stations required | Available time; Customer demand; Proc. time per unit; Flow rate R (opt); Total work content | `form_scrolling` |
| `07_SPC_and_Six_Sigma` | SPC / Cp / Cpk / DPMO | Control limits, capability and sigma level | Process mean; Std deviation sigma; USL; LSL; Limit multiple k; Defects; Units; Opportunities/unit | `form_scrolling` |
| `08_Process_Capacity` | Process: capacity, bottleneck, WIP | cap = 60c/t; I = R x T; left/right = map | L arrivals /hr; b balk fraction (dec); t1 stage1 min/unit; c1 stage1 servers; t2 stage2 min/unit; c2 stage2 servers; t3 stage3 min/unit; c3 stage3 servers; T visit time (min) | `form_standard` |

Total: 8 sheets.
