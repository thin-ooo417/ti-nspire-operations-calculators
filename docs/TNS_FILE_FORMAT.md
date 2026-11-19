# The .tns file format used here

`scripts/tns_file.py` writes the same layout as Luna v2.1 (ndless-nspire/Luna), a well-known tool
for making TI-Nspire Lua files. This describes what `tns_file.py` writes, not every kind of
TI-Nspire file.

## Layers, outside in

1. **Container.** Like a ZIP file, except the first header starts with `*TIMLP0500` instead of
   `PK\x03\x04` and the end record starts with `TIPD`. Entries use compression method 13.
2. **Entries.** `Document.xml`, a fixed 304-byte block, and `Problem1.xml`, which holds the script.
3. **Problem1.xml.** A fixed 40-byte header, then the body mixed with a keystream: block n is
   Triple-DES (three fixed keys) of `00 00 00 00` followed by `0x6FE21307 + (n mod 1024)` as a
   little-endian number.
4. **Body.** Compressed with raw DEFLATE.
5. **Inside.** TI's compact XML for one page holding a Lua script, with the script as plain text in a
   CDATA section.

The key is fixed and public, so this is a file format, not protection.

## What is checked

- The output was compared with Luna itself on the same computer: identical for every sheet.
- `tests/fixtures/reference/` holds an old file built by Luna. The tests read it back and rebuild
  it; everything matches except the compressed bytes, which depend on the zlib version.
- Every build reads each new file back and compares it with its source.

## Files saved by the calculator

If a sheet is saved on the calculator, the calculator rewrites the file with its own key per entry.
`tns_file.py unpack` cannot read those and says so. Rebuild from `src/` instead.
