"""A small stand-in for the TI-Nspire Lua script environment.

Runs a sheet under real Lua 5.1 (the version the handheld uses) with mock
`platform`, `on` and graphics-context objects, so tests can press keys and read
back what the sheet draws. It checks more than a bare interpreter would:

* only documented graphics-context methods and event handlers may be used;
* drawString / getStringWidth must be given strings (the handheld raises
  otherwise);
* reading an undefined global after load raises, which catches misspelt names
  on any code path the tests reach.

It is not an emulator. Fonts are approximated, so pixel-exact layout is not
tested, and nothing here proves a sheet renders on hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lupa.lua51 as lua51

WIDTH, HEIGHT = 318, 212  # full-page script window on a CX handheld

MINUS_KEY = "−"  # what the handheld's (-) key sends

_PRELUDE = r"""
local W, H = ...
__draw = {}
__invalidated = 0
__runtime_globals = {}

local GC_METHODS = {
  "drawString", "getStringWidth", "getStringHeight", "setFont", "setColorRGB",
  "fillRect", "drawRect", "drawLine", "drawArc", "fillArc", "drawPolyLine",
  "fillPolygon", "setPen", "clipRect", "drawImage", "setAlpha",
}
local known = {}
for _, m in ipairs(GC_METHODS) do known[m] = true end

local font = { family = "sansserif", style = "r", size = 10 }
local color = { 0, 0, 0 }

local function need_number(v, what)
  if type(v) ~= "number" then error(what .. ": number expected, got " .. type(v), 3) end
  if v ~= v then error(what .. ": NaN coordinate", 3) end
end

local function need_string(v, what)
  if type(v) ~= "string" then error(what .. ": string expected, got " .. type(v), 3) end
end

local function utf8len(s)
  local _, n = string.gsub(s, "[^\128-\191]", "")
  return n
end

local function width_of(s)
  local per = font.size * 0.56
  if font.style == "b" or font.style == "bi" then per = font.size * 0.60 end
  return math.floor(utf8len(s) * per + 0.5)
end

local gc = {}

function gc:setColorRGB(r, g, b)
  need_number(r, "setColorRGB"); need_number(g, "setColorRGB"); need_number(b, "setColorRGB")
  for _, c in ipairs({ r, g, b }) do
    if c < 0 or c > 255 then error("setColorRGB: component out of range", 2) end
  end
  color = { r, g, b }
end

function gc:setFont(family, style, size)
  if family ~= "sansserif" and family ~= "serif" then error("setFont: bad family " .. tostring(family), 2) end
  if style ~= "r" and style ~= "b" and style ~= "i" and style ~= "bi" then
    error("setFont: bad style " .. tostring(style), 2)
  end
  need_number(size, "setFont")
  local old = font
  font = { family = family, style = style, size = size }
  return old.family, old.style, old.size
end

function gc:getStringWidth(s)
  need_string(s, "getStringWidth")
  return width_of(s)
end

function gc:getStringHeight(s)
  need_string(s, "getStringHeight")
  return math.floor(font.size * 1.5 + 0.5)
end

function gc:drawString(s, x, y, anchor)
  need_string(s, "drawString"); need_number(x, "drawString"); need_number(y, "drawString")
  anchor = anchor or "none"
  if anchor ~= "top" and anchor ~= "middle" and anchor ~= "bottom" and anchor ~= "baseline"
     and anchor ~= "none" then
    error("drawString: bad vertical alignment " .. tostring(anchor), 2)
  end
  __draw[#__draw + 1] = {
    text = s, x = x, y = y, anchor = anchor, size = font.size, style = font.style,
    width = width_of(s), r = color[1], g = color[2], b = color[3],
  }
  return x + width_of(s)
end

local function shape(name, n)
  gc[name] = function(self, ...)
    local args = { ... }
    for i = 1, n do need_number(args[i], name) end
  end
end
shape("fillRect", 4); shape("drawRect", 4); shape("drawLine", 4)
shape("drawArc", 6); shape("fillArc", 6); shape("clipRect", 0)
function gc:drawPolyLine(t) if type(t) ~= "table" then error("drawPolyLine: table expected", 2) end end
function gc:fillPolygon(t) if type(t) ~= "table" then error("fillPolygon: table expected", 2) end end
function gc:setPen() end
function gc:setAlpha() end
function gc:drawImage() end

setmetatable(gc, { __index = function(_, k)
  if known[k] then return nil end
  error("graphics context has no method '" .. tostring(k) .. "'", 2)
end })
__gc = gc

local window = {}
function window:width() return W end
function window:height() return H end
function window:invalidate() __invalidated = __invalidated + 1 end
function window:setFocus() end

platform = {
  window = window,
  isColorDisplay = function() return true end,
  isDeviceModeRendering = function() return true end,
  isTabletModeRendering = function() return false end,
  hw = function() return 3 end,
}
on = {}

-- Instruction counter for the cost report.
local sethook = debug.sethook
__count = 0
function __count_start()
  __count = 0
  sethook(function() __count = __count + 100 end, "", 100)
end
function __count_stop()
  sethook()
  return __count
end

-- The handheld's script sandbox has no file, process or module access.
-- (`debug` stays because the Python bridge needs it; the source scan in
-- test_sources.py makes sure no sheet uses it.)
io, os, require, dofile, loadfile, package, module, newproxy = nil
"""

_STRICT = r"""
setmetatable(_G, {
  __index = function(_, k) error("read of undefined global '" .. tostring(k) .. "'", 2) end,
  __newindex = function(t, k, v) __runtime_globals[k] = true; rawset(t, k, v) end,
})
"""

# Event handlers documented for TI-Nspire script apps.
DOCUMENTED_EVENTS = frozenset(
    """
    paint resize construction create destroy activate deactivate getFocus loseFocus
    charIn enterKey returnKey tabKey backtabKey backspaceKey deleteKey clearKey escapeKey
    arrowKey arrowUp arrowDown arrowLeft arrowRight help contextMenu
    mouseDown mouseUp mouseMove rightMouseDown rightMouseUp grabDown grabUp
    timer save restore cut copy paste getSymbolList varChange keyboardUp
    """.split()
)


class SheetError(AssertionError):
    """The sheet raised a Lua error."""


@dataclass(frozen=True)
class Text:
    text: str
    x: float
    y: float
    anchor: str
    size: float
    style: str
    width: float
    rgb: tuple[int, int, int]

    @property
    def right(self) -> float:
        return self.x + self.width


class Sheet:
    """One loaded script. Methods mirror the keys on the handheld."""

    def __init__(self, source: str | bytes | Path, width: int = WIDTH, height: int = HEIGHT) -> None:
        if isinstance(source, Path):
            self.name = source.name
            source = source.read_bytes()
        else:
            self.name = "<sheet>"
        if isinstance(source, str):
            source = source.encode("utf-8")
        self.source = source
        self.width, self.height = width, height
        self.lua = lua51.LuaRuntime(encoding=None, unpack_returned_tuples=True)
        self.lua.execute(_PRELUDE.encode(), width, height)
        loader = self.lua.eval(b"loadstring")
        chunk = loader(source, b"@" + self.name.encode())
        if isinstance(chunk, tuple):  # (nil, message) on a syntax error
            raise SheetError(f"{self.name}: {_text(chunk[1])}")
        try:
            chunk()
        except lua51.LuaError as exc:  # pragma: no cover - reported by tests
            raise SheetError(f"{self.name}: error at load: {exc}") from exc
        self.lua.execute(_STRICT.encode())
        self._g = self.lua.globals()

    # -- events ---------------------------------------------------------------

    def handlers(self) -> set[str]:
        return {_text(k) for k in self._g[b"on"].keys()}

    def has(self, event: str) -> bool:
        return self._g[b"on"][event.encode()] is not None

    def fire(self, event: str, *args) -> None:
        handler = self._g[b"on"][event.encode()]
        if handler is None:
            return
        encoded = [a.encode("utf-8") if isinstance(a, str) else a for a in args]
        try:
            handler(*encoded)
        except lua51.LuaError as exc:
            raise SheetError(f"{self.name}: on.{event} raised: {exc}") from exc

    def char(self, ch: str) -> None:
        self.fire("charIn", ch)

    def type(self, text: str) -> None:
        for ch in text:
            self.char(ch)

    def arrow(self, direction: str) -> None:
        specific = "arrow" + direction.capitalize()
        if self.has(specific):
            self.fire(specific)
        else:
            self.fire("arrowKey", direction)

    def down(self, times: int = 1) -> None:
        for _ in range(times):
            self.arrow("down")

    def up(self, times: int = 1) -> None:
        for _ in range(times):
            self.arrow("up")

    def left(self) -> None:
        self.arrow("left")

    def right(self) -> None:
        self.arrow("right")

    def enter(self) -> None:
        self.fire("enterKey")

    def tab(self) -> None:
        self.fire("tabKey")

    def backspace(self) -> None:
        self.fire("backspaceKey")

    def escape(self) -> None:
        self.fire("escapeKey")

    def clear(self) -> None:
        self.fire("clearKey")

    # -- painting -------------------------------------------------------------

    def paint(self) -> list[Text]:
        self.lua.execute(b"__draw = {}")
        handler = self._g[b"on"][b"paint"]
        if handler is None:
            raise SheetError(f"{self.name}: no on.paint handler")
        try:
            handler(self._g[b"__gc"])
        except lua51.LuaError as exc:
            raise SheetError(f"{self.name}: on.paint raised: {exc}") from exc
        out = []
        for item in self._g[b"__draw"].values():
            out.append(
                Text(
                    text=_text(item[b"text"]), x=item[b"x"], y=item[b"y"], anchor=_text(item[b"anchor"]),
                    size=item[b"size"], style=_text(item[b"style"]), width=item[b"width"],
                    rgb=(int(item[b"r"]), int(item[b"g"]), int(item[b"b"])),
                )
            )
        return out

    def lines(self) -> list[list[Text]]:
        """Painted strings grouped into rows by y, each row left to right."""
        rows: dict[float, list[Text]] = {}
        for item in self.paint():
            rows.setdefault(item.y, []).append(item)
        return [sorted(rows[y], key=lambda t: t.x) for y in sorted(rows)]

    def texts(self) -> list[str]:
        return [t.text for t in self.paint()]

    def pairs(self) -> dict[str, str]:
        """Rows that hold exactly a label and a value, as {label: value}."""
        return {row[0].text: row[1].text for row in self.lines() if len(row) == 2}

    def runtime_globals(self) -> set[str]:
        return {_text(k) for k in self._g[b"__runtime_globals"].keys()}

    def instructions(self, action) -> int:
        """Lua VM instructions executed while `action()` runs, to the nearest hundred."""
        self._g[b"__count_start"]()
        try:
            action()
        finally:
            count = self._g[b"__count_stop"]()
        return int(count)


def _text(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def number(text: str) -> float:
    """Parse a value the sheets display: '13.5%', '1,234', '4672.9', '-'."""
    cleaned = text.strip().replace(",", "").replace("−", "-")
    if cleaned.endswith("%"):
        return float(cleaned[:-1]) / 100.0
    return float(cleaned)
