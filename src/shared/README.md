# Shared code

Each sheet in `src/operations/` holds its own title, fields and formulas, then pulls in the shared
code here with a line such as `--@include shared/form_standard.lua`. The build pastes the file
in at that point, so every `.tns` file is still one complete script. A fix made here reaches every
sheet that uses the file.

| File | Used by |
|---|---|
| `form_standard.lua` | 1 of 8 sheets |
| `form_scrolling.lua` | 7 of 8 sheets |

Everything here must run on Lua 5.1 and fit the calculator's 318 × 212 pixel screen.

## `form_standard.lua`

A single column of fields with the results underneath. The sheet defines its title, a formula line,
its fields and a `calc` function, then includes the shared code:

```lua
local TITLE = "Present value"
local FORMULA = "PV = CFt x 1/(1+r)^t"

local fields = {
  -- k: name used in calc   lab: label on screen   v: always ""   d: optional default
  {k="cf", lab="CFt  cashflow at t", v=""},
  {k="r",  lab="r  rate (decimal)", v=""},
  {k="t",  lab="t  periods", v="", d=1},
}

local function calc(V)
  -- V.cf, V.r, V.t are numbers, the default, or nil if blank. Check before using them.
  local p
  if V.cf and V.r and V.t then p = V.cf / (1 + V.r)^V.t end
  return {{"PV", fmt(p)}}
end

--@include shared/form_standard.lua
```

`calc` returns rows: `{"label", text}` for a result, `{"!", text}` for a warning. `fmt(x)` and
`pct(x)` format numbers and turn missing or impossible values into a dash.

What it guarantees (and the tests check): an empty sheet shows a prompt instead of results; an
entry that is not a number turns red and hides all results; only digits, one decimal point and a
leading minus can be typed; and rows shrink to fit the screen. Keep fields plus result rows to 19
or fewer, and keep `calc` quick: it runs on every key press and the calculator has no maths chip.

## `form_scrolling.lua`

A list of fields with results that can run below the screen. The sheet defines `TITLE`,
`SUBTITLE`, `NOTE`, `FIELDS` (a list of `{key=..., lbl=..., txt=..., def=...}`, with `txt` equal to
`def`) and a function `OUTPUTS()`. `OUTPUTS` reads values with `V("key")` and returns rows of
`{label, text}`; `{"--"}` draws a dividing line. `fmt(x, dp)`, `money(x, dp)` and `pct(x, dp)`
format numbers.
