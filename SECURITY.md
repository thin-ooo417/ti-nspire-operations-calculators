# Security

## What this project does

The sheets are Lua scripts that run inside the calculator's sandbox: they cannot read files, use a
network or store anything. The build scripts read `src/` and write `dist/` and `build/`; they make
no network connections.

## Reporting a problem

Use "Report a vulnerability" on this repository's Security tab, or open an issue if it is not
sensitive. A wrong answer from a sheet is worth reporting too: say which sheet, what you typed and
what you expected.

## Good to know

- **`.tns` files are not encrypted in any useful way.** The key is fixed and public. Never put a
  secret in a sheet.
- **No passwords, keys or settings files are needed**, and none are in the repository.
- **The calculators have no dependencies.** The development tools (`pytest`, `lupa`, `ruff`) are
  checked weekly for known problems.
- **`tns_file.py unpack` is meant for files you built.** It limits how much it will unpack and
  rejects damaged files, but has not been hardened against deliberately hostile ones.

Only the latest release is maintained.
