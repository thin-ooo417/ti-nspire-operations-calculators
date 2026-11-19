# Changelog

All notable changes. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and versions follow [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-19

First public release.

### Fixed since the earlier, unpublished version

- **`05_Utilisation_and_Queues`: waiting time with more than one server was too high.** The estimate left out a division by the number of servers, so "Kingman Wq" and "Kingman Lq" were c times too large. Single-server results were right and are unchanged.
- **Sheets 01–07: lower results could not be reached.** Pressing down on the last field now scrolls to the end, and up comes back.
- **Sheets 01–07: the `(-)` key did nothing,** and keys that send several characters (such as 10^x) could put text in a field. Both fixed.
- **`07_SPC_and_Six_Sigma`: two labels.** The control-limit label rounded the multiple ("mean + 2s" for 2.5), and "Z (short term)" was the long-term Z. The numbers were right.
- **`08_Process_Capacity`: large results keep their digits** from 10,000 upward.

### Added

- One source file per sheet, with shared code in `src/shared/`.
- A build that needs only Python (`scripts/build.py`).
- Automated tests that run every sheet under Lua 5.1 and check its results.
- A step-by-step guide to loading the sheets with TI-Nspire Computer Link Software, shipped as
  `README.txt` in the download.
- Automatic tests, releases and a weekly dependency check on GitHub.
