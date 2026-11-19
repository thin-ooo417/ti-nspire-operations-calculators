local TITLE = "Process: capacity, bottleneck, WIP"
local FORMULA = "cap = 60c/t;  I = R x T;  left/right = map"

local fields = {
  {k="la", lab="L   arrivals /hr", v=""},
  {k="bk", lab="b   balk fraction (dec)", v="", d=0},
  {k="t1", lab="t1  stage1 min/unit", v=""},
  {k="c1", lab="c1  stage1 servers", v="", d=1},
  {k="t2", lab="t2  stage2 min/unit", v=""},
  {k="c2", lab="c2  stage2 servers", v="", d=1},
  {k="t3", lab="t3  stage3 min/unit", v=""},
  {k="c3", lab="c3  stage3 servers", v="", d=1},
  {k="tf", lab="T   visit time (min)", v=""},
}

-- Shared model used by BOTH the calc rows and the map pane, so the two panes
-- can never disagree.
local function model(V)
  local M = {}
  M.lam = V.la
  M.b = V.bk
  M.t = {V.t1, V.t2, V.t3}
  M.c = {V.c1, V.c2, V.c3}
  M.cap = {}
  M.tf = V.tf

  if M.lam and M.b then M.R = M.lam * (1 - M.b) end

  local best
  M.work = 0
  M.baddom = false
  for i = 1, 3 do
    local t, c = M.t[i], M.c[i]
    if t then
      M.work = M.work + t
      if t <= 0 then M.baddom = true end
      if c and c <= 0 then M.baddom = true end
      if t > 0 and c and c > 0 then
        M.cap[i] = 60 * c / t
        if best == nil or M.cap[i] < M.cap[best] then best = i end
      end
    end
  end
  if M.b and (M.b < 0 or M.b >= 1) then M.baddom = true end

  M.bn = best
  if best then M.pcap = M.cap[best] end
  if M.R and M.pcap and M.pcap ~= 0 then M.util = M.R / M.pcap end
  if M.lam and M.pcap and M.pcap ~= 0 then M.iutil = M.lam / M.pcap end
  if M.R and M.tf then M.wip = M.R * M.tf / 60 end
  return M
end

local function calc(V)
  local out = {}
  local n = 0
  local function row(a, b) n = n + 1 out[n] = {a, b} end

  local M = model(V)

  row("Throughput R/hr", fmt(M.R))

  local cs = ""
  for i = 1, 3 do
    if i > 1 then cs = cs .. "/" end
    if M.cap[i] then cs = cs .. fmt(M.cap[i]) else cs = cs .. "-" end
  end
  row("Cap S1/S2/S3", cs)

  if M.bn then
    row("Bottleneck", "S" .. M.bn .. "  " .. fmt(M.pcap) .. "/hr")
  else
    row("Bottleneck", "-")
  end

  row("BN utilisation", pct(M.util))
  row("In store I=RxT", fmt(M.wip))

  if M.iutil and M.iutil > 1 then
    row("!", "Demand > capacity: queue grows, balking.")
  end
  if M.baddom then
    row("!", "Check inputs: b in 0-1, t and c > 0.")
  end
  if M.tf and M.work > 0 and M.tf < M.work then
    row("!", "T is below total work time: check T.")
  end
  return out
end


--@include shared/form_standard.lua

-- ===== map pane (appended; the engine v2 block above is unmodified) =====
-- Adds a second view reached with left/right. The engine's own handlers are
-- captured and delegated to, so every v2 guarantee still holds on the input
-- pane, and the map pane refuses to draw on bad or empty input exactly as the
-- input pane refuses to show results.

local mode = 1
local basePaint = on.paint
local baseChar = on.charIn
local baseBack = on.backspaceKey
local baseEsc = on.escapeKey
local baseEnter = on.enterKey
local baseArrow = on.arrowKey

local function arrowTo(gc, x1, x2, y)
  gc:drawLine(x1, y, x2, y)
  gc:drawLine(x2, y, x2 - 3, y - 3)
  gc:drawLine(x2, y, x2 - 3, y + 3)
end

local function bufferMark(gc, x, y)
  gc:drawLine(x - 4, y, x + 4, y)
  gc:drawLine(x - 4, y, x, y + 6)
  gc:drawLine(x + 4, y, x, y + 6)
end

local function hint(gc, h)
  gc:setColorRGB(150, 150, 150)
  gc:setFont("sansserif", "r", 7)
  gc:drawString("left/right or esc: back to inputs", 4, h - 12, "top")
end

local function paintMap(gc)
  local w = platform.window:width()
  local h = platform.window:height()
  local V, bad, any = state()

  gc:setColorRGB(20, 60, 120)
  gc:fillRect(0, 0, w, 17)
  gc:setColorRGB(255, 255, 255)
  gc:setFont("sansserif", "b", 10)
  gc:drawString("Process map", 4, 1, "top")

  gc:setFont("sansserif", "r", 8)
  if bad then
    gc:setColorRGB(200, 0, 0)
    gc:drawString("An entry is not a number.", 4, 26, "top")
    gc:drawString("Fix it on the input page.", 4, 38, "top")
    hint(gc, h)
    return
  end
  if not any then
    gc:setColorRGB(150, 150, 150)
    gc:drawString("Enter values on the input page first.", 4, 26, "top")
    hint(gc, h)
    return
  end

  local M = model(V)

  local idx = {}
  for i = 1, 3 do
    if M.t[i] then idx[#idx + 1] = i end
  end
  if #idx == 0 then
    gc:setColorRGB(150, 150, 150)
    gc:drawString("Enter at least one stage time.", 4, 26, "top")
    hint(gc, h)
    return
  end

  gc:setColorRGB(110, 110, 110)
  gc:setFont("sansserif", "i", 7)
  local sub = "arrivals " .. fmt(M.lam) .. "/hr"
  if M.b then sub = sub .. "   balk " .. pct(M.b) end
  if M.tf then sub = sub .. "   visit " .. fmt(M.tf) .. " min" end
  gc:drawString(sub, 4, 20, "top")

  local n = #idx
  local inW, outW, gap = 34, 46, 10
  local boxW = math.floor((w - 8 - inW - outW - gap * (n + 1)) / n)
  if boxW > 120 then boxW = 120 end
  if boxW < 38 then boxW = 38 end

  local bt, bh = 44, 36
  local mid = bt + 18

  gc:setFont("sansserif", "r", 7)
  gc:setColorRGB(0, 0, 0)
  gc:drawString("IN", 4, bt + 4, "top")
  gc:drawString(fmt(M.lam) .. "/hr", 4, bt + 16, "top")

  local x = 4 + inW
  local balkX = x + 5
  for j = 1, n do
    local i = idx[j]
    gc:setColorRGB(120, 120, 120)
    arrowTo(gc, x, x + gap, mid)
    bufferMark(gc, x + 5, bt - 12)
    x = x + gap

    local isBN = (M.bn == i)
    if isBN then gc:setColorRGB(190, 90, 0) else gc:setColorRGB(20, 60, 120) end
    gc:drawRect(x, bt, boxW, bh)
    gc:setFont("sansserif", "b", 7)
    gc:drawString("S" .. i, x + 4, bt + 2, "top")
    gc:setColorRGB(0, 0, 0)
    gc:setFont("sansserif", "r", 7)
    gc:drawString("t=" .. fmt(M.t[i]) .. " c=" .. fmt(M.c[i]), x + 4, bt + 13, "top")
    if isBN then gc:setColorRGB(190, 90, 0) end
    if M.cap[i] then
      gc:drawString(fmt(M.cap[i]) .. "/hr", x + 4, bt + 24, "top")
    else
      gc:drawString("-", x + 4, bt + 24, "top")
    end
    x = x + boxW
  end

  gc:setColorRGB(120, 120, 120)
  arrowTo(gc, x, x + gap, mid)
  x = x + gap
  gc:setColorRGB(0, 0, 0)
  gc:setFont("sansserif", "r", 7)
  gc:drawString("OUT", x, bt + 4, "top")
  gc:drawString(fmt(M.R) .. "/hr", x, bt + 16, "top")

  if M.lam and M.b and M.b > 0 then
    gc:setColorRGB(150, 150, 150)
    gc:drawLine(balkX, mid, balkX, bt + bh + 8)
    gc:drawLine(balkX, bt + bh + 8, balkX - 3, bt + bh + 5)
    gc:drawLine(balkX, bt + bh + 8, balkX + 3, bt + bh + 5)
    gc:drawString("balk " .. fmt(M.lam * M.b) .. "/hr", balkX + 6, bt + bh + 2, "top")
  end

  local y = 96
  gc:setFont("sansserif", "b", 8)
  if M.bn then
    gc:setColorRGB(190, 90, 0)
    gc:drawString("Bottleneck: S" .. M.bn .. "   " .. fmt(M.pcap) .. "/hr", 4, y, "top")
  else
    gc:setColorRGB(150, 150, 150)
    gc:drawString("Bottleneck: -", 4, y, "top")
  end
  y = y + 13

  gc:setFont("sansserif", "r", 8)
  gc:setColorRGB(0, 0, 0)
  gc:drawString("Throughput R = " .. fmt(M.R) .. "/hr", 4, y, "top")
  y = y + 12
  gc:drawString("Util at R " .. pct(M.util) .. "   implied " .. pct(M.iutil), 4, y, "top")
  y = y + 12
  gc:drawString("In store  I = R x T = " .. fmt(M.wip), 4, y, "top")
  y = y + 12

  if M.iutil and M.iutil > 1 then
    gc:setColorRGB(190, 90, 0)
    gc:setFont("sansserif", "i", 7)
    gc:drawString("Demand exceeds capacity: queue grows.", 4, y, "top")
  end

  hint(gc, h)
end

function on.paint(gc)
  if mode == 2 then
    paintMap(gc)
    return
  end
  basePaint(gc)
end

function on.arrowKey(k)
  if k == "left" or k == "right" then
    if mode == 1 then mode = 2 else mode = 1 end
    platform.window:invalidate()
    return
  end
  if mode == 1 then baseArrow(k) end
end

function on.charIn(ch)
  if mode == 1 then baseChar(ch) end
end

function on.backspaceKey()
  if mode == 1 then baseBack() end
end

function on.escapeKey()
  if mode == 2 then
    mode = 1
    platform.window:invalidate()
    return
  end
  baseEsc()
end

function on.enterKey()
  if mode == 1 then baseEnter() end
end

function on.tabKey()
  on.enterKey()
end
