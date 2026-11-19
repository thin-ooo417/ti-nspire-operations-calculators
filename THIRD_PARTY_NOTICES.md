# Third-party notices

No third-party code is included in this repository.

## Luna

`scripts/tns_file.py` was written for this project. It writes the same file layout as **Luna v2.1**
(<https://github.com/ndless-nspire/Luna>, by Olivier Armand and contributors, Mozilla Public
License 1.1), and uses the same fixed values: the body key and counter, the 40-byte body header, the
304-byte default `Document.xml`, and the wrapper around the Lua script.

`docs/TNS_FILE_FORMAT.md` also draws on the **rust-tns** project's `FORMAT.md`
(<https://github.com/dev1837457/rust-tns>, MPL 1.1).

This repository has no licence yet. When one is chosen, keep this notice. Because the fixed values
come from MPL-licensed code, the safest route is to release `scripts/tns_file.py` under MPL 1.1.

## Development tools (installed separately, not included)

| Tool | Licence | Used for |
|---|---|---|
| pytest | MIT | running the tests |
| lupa | MIT (includes Lua 5.1, MIT) | running the sheets under Lua 5.1 |
| ruff | MIT | checking the Python |

## Trademarks

TI-Nspire is a trademark of Texas Instruments. This project is not affiliated with or endorsed by
Texas Instruments.
