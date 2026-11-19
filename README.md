# TI-Nspire Operations Management Calculators

8 calculator sheets for Little's Law, production lines and bottlenecks, batch sizing, queues, takt time, SPC and Six Sigma. Each sheet opens as a simple form on a TI-Nspire CX or CX CAS: type the numbers you
have and the answer appears underneath.

> **Version 1.0.0.** Every sheet has been tested on a computer but this version has not yet
> been tried on a calculator. Check one sheet first (step 6 below).

## Contents

1. [Put the sheets on your calculator](#1-put-the-sheets-on-your-calculator)
2. [Use a sheet](#2-use-a-sheet)
3. [The sheets](#3-the-sheets)
4. [Notes on particular sheets](#4-notes-on-particular-sheets)
5. [If something goes wrong](#5-if-something-goes-wrong)
6. [Known limitations](#6-known-limitations)
7. [For developers](#7-for-developers)
8. [Licence, security and support](#8-licence-security-and-support)

## 1. Put the sheets on your calculator

You need a TI-Nspire CX or CX CAS, its USB cable, and **TI-Nspire Computer Link Software** (free from
education.ti.com) on a Windows or Mac computer.

1. **Download.** Open this repository's **Releases** page, download `ti-nspire-operations-calculators-1.0.0.zip` and unzip it.
   You get a folder called `operations` and a `README.txt`.
2. **Connect.** Turn the calculator on and plug it into the computer.
3. **Open Computer Link.** In the Select Handheld window, click your calculator, then **Select**.
4. **Copy.** The top pane shows your computer and the bottom pane shows the calculator. Drag the
   `operations` folder from the top pane to the bottom pane.
5. **Leave `README.txt` behind.** Computer Link only copies calculator files and cancels the whole
   copy if you include anything else.
6. **Check.** On the calculator press [home], open **My Documents**, then `operations`, then
   `01_Littles_Law`. Press [down] 4 [down] 30 (words in square brackets are keys; the rest
   are numbers to type). You should see **Inventory I  <-- solved** 120.00.

The `README.txt` in the zip has the same steps in more detail, with fixes for common problems.
No release yet? Build the zip yourself (section 7).

## 2. Use a sheet

| Sheets | Move | Type | Reset |
|---|---|---|---|
| Sheets 01–07 | [up] [down], or [enter] / [tab]; keep pressing [down] to scroll through the results | number keys, `.` and `(-)`; [backspace] deletes | [esc] puts every field back to its default |
| Sheet 08 | [up] [down], or [enter] / [tab]; [left] or [right] shows the process map | number keys, `.` and `(-)`; [backspace] deletes | [esc] empties the field (on the map: back to the inputs) |

- Keep time units the same within a sheet. With stage times in minutes, an available time of 60 gives capacity per hour.
- In sheets 01–07 the results continue below the screen. Press down past the last field to see them.
- In sheet 08, **grey** values are defaults used while a field is empty and **red** means
  an entry is not a complete number yet.
- If the calculator asks to save changes when you close a sheet, either answer is fine.

**Example.** Two-server queue (`05_Utilisation_and_Queues`): arrival rate 1.6, service rate 1, 2 servers, both coefficients of variation 1. Press 1.6 [down] 1 [down] [backspace] 2 [down] 1 [down] 1:

| Row | Shows |
|---|---|
| Utilisation rho | 0.80 |
| Kingman Wq (VUT) | 1.8091 |
| Kingman Lq | 2.8946 |

## 3. The sheets

| Sheet | What it works out |
|---|---|
| `01_Littles_Law` | Inventory, flow rate or flow time from the other two, and the effect of a target time |
| `02_Serial_Line_Bottleneck` | Bottleneck, capacity, throughput time and WIP of a line of up to six stages |
| `03_Parallel_Routes` | Capacity of two parallel routes |
| `04_Batch_Size_and_Setup` | Effective time per unit with setups, and where the bottleneck switches |
| `05_Utilisation_and_Queues` | Utilisation and waiting time for one or more servers |
| `06_Takt_and_Cycle_Time` | Takt time, capacity and the number of stations needed |
| `07_SPC_and_Six_Sigma` | Control limits, Cp and Cpk, defects per million and sigma level |
| `08_Process_Capacity` | Capacity, bottleneck and stock of a three-stage process, with a process map |

[docs/SHEET_LIST.md](docs/SHEET_LIST.md) lists every input of every sheet.

## 4. Notes on particular sheets

- **`01_Littles_Law`.** Leave one of I, R and T blank. The divisor converts T into R's time unit (60 for minutes against an hourly rate).
- **`02_Serial_Line_Bottleneck`.** Mode 0 takes stage times, mode 1 takes stage capacities. "New bottleneck t" shows what happens if the slowest stage is sped up.
- **`04_Batch_Size_and_Setup`.** Shows the batch size at which the bottleneck moves to the other stage.
- **`05_Utilisation_and_Queues`.** Exact results for one server. With both coefficients of variation it also gives the Kingman waiting-time estimate, for one or more servers.
- **`07_SPC_and_Six_Sigma`.** Three separate parts: control limits, capability, and sigma level from defect counts. Fill in whichever you need.

## 5. If something goes wrong

| Problem | What to do |
|---|---|
| The calculator is not in the Select Handheld list | Turn it on, push the cable in fully at both ends, click Refresh. Try another USB port. |
| Computer Link says a file is not supported and copies nothing | You included `README.txt`. Drag only the `operations` folder or `.tns` files. |
| A sheet will not open | Copy that file again. If it still fails, open an issue saying which sheet. |
| A percentage looks 100 times too big or small | Type rates as decimals: `0.08`, not `8`. |
| Nothing appears under the fields | The sheet needs more inputs. A dash means that row cannot be worked out yet. |
| A number looks wrong | Open an issue with the sheet name, what you typed and what it showed. |

## 6. Known limitations

- Not yet tried on a calculator in this version. Check one sheet first (step 6 above).
- Made for the TI-Nspire CX and CX CAS. CX II models have not been tried.
- In sheets 01–07 a field holding only `-` or `.` counts as empty.
- The waiting time for more than one server in `05_Utilisation_and_Queues` is an approximation, within a few per cent of the exact figure in the cases tested.

## 7. For developers

### What is in this repository

```
ti-nspire-operations-calculators/
├── src/
│   ├── operations/              one .lua file per sheet (8)
│   └── shared/                  code the sheets share
│       ├── form_standard.lua
│       └── form_scrolling.lua
├── scripts/
│   ├── build.py                 builds every sheet into dist/
│   ├── tns_file.py              reads and writes .tns calculator files
│   ├── des_cipher.py            the cipher the .tns format needs
│   └── make_sheet_list.py       rebuilds docs/SHEET_LIST.md
├── tests/                       automated tests
├── docs/
│   ├── LOADING_GUIDE.txt        becomes README.txt in the download
│   ├── SHEET_LIST.md            every sheet and its inputs
│   ├── CHECK_ON_CALCULATOR.md   what to check on a real calculator
│   ├── HOW_IT_WORKS.md          how the build and tests work
│   └── TNS_FILE_FORMAT.md       the calculator file format
├── .github/workflows/           automatic tests and releases
├── CHANGELOG.md  CONTRIBUTING.md  SECURITY.md  THIRD_PARTY_NOTICES.md
└── VERSION  pyproject.toml  requirements-dev.txt
```

### Set up

You need Python 3.10 or later. Nothing else: no compiler and no TI software.

```bash
git clone <GITHUB_REPOSITORY_URL>
cd ti-nspire-operations-calculators
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS or Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

### Build

```bash
python scripts/build.py --zip
```

This writes `dist/operations/` (the `.tns` files), `dist/README.txt` and `dist/ti-nspire-operations-calculators-1.0.0.zip`.
Each build checks every sheet compiles as Lua 5.1 (the calculator's version) and that every file
holds exactly its source.

| Option | What it does |
|---|---|
| `--zip` | also make the zip |
| `--check` | change nothing; fail if `dist/` does not match `src/` |
| `--out FOLDER` | write somewhere other than `dist/` |

### Test

```bash
python -m pytest
ruff check .
python scripts/make_sheet_list.py --check
```

The tests check every result against an independent calculation, press random keys on every
sheet, and type the worked checks from the loading guide into the sheets.
[docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) explains more.

### One file at a time

```bash
python scripts/tns_file.py pack   my_sheet.lua my_sheet.tns
python scripts/tns_file.py unpack my_sheet.tns my_sheet.lua
```

`unpack` cannot read a file the calculator has saved over; rebuild it from `src/` instead.

## 8. Licence, security and support

- **Licence:** none chosen yet, so all rights are reserved. See
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for code this project draws on.
- **Security:** the sheets cannot read files or use a network, and the repository holds no
  passwords or personal data. See [SECURITY.md](SECURITY.md).
- **Assessments:** check the rules before taking stored programs into any test or exam.
- **Contributing:** see [CONTRIBUTING.md](CONTRIBUTING.md).
- **Support:** open an issue on this repository.
