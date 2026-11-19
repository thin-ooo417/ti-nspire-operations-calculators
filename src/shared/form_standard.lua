-- ===== shared engine v2.1 (TI-Nspire CX CAS, Lua 5.1, OS 3.0.2+) =====
local cur = 1

-- Build value table. Returns V, hasBad (unparseable text), hasAny (any entry).
local function state()
  local V = {}
  local bad, any = false, false
  for i = 1, #fields do
    local f = fields[i]
    if f.v == "" then
      V[f.k] = f.d
      f.bad = false
    else
      any = true
      local n = tonumber(f.v)
      if n == nil then
        bad = true
        f.bad = true
        V[f.k] = f.d
      else
        f.bad = false
        V[f.k] = n
      end
    end
  end
  return V, bad, any
end

function fmt(x)
  if x == nil then return "-" end
  if x ~= x then return "-" end
  if x == math.huge or x == -math.huge then return "-" end
  -- "%.6g" drops decimals from 10,000 up and switches to 1.23457e+06 from a
  -- million, so money amounts lost digits. Show those to 2 dp, trimmed.
  local a = math.abs(x)
  if a >= 1e4 and a < 1e15 then
    local s = string.format("%.2f", x)
    s = string.gsub(s, "0+$", "")
    s = string.gsub(s, "%.$", "")
    return s
  end
  return string.format("%.6g", x)
end

function pct(x)
  if x == nil then return "-" end
  if x ~= x then return "-" end
  if x == math.huge or x == -math.huge then return "-" end
  return string.format("%.4g", x * 100) .. "%"
end

function on.paint(gc)
  local w = platform.window:width()
  local h = platform.window:height()

  local V, bad, any = state()

  -- Work out what goes below the line before drawing, so row height can be
  -- fitted to the window instead of assumed. Keeps tall sheets from clipping.
  local out
  if bad then
    out = {{"!!", "Entry in red is not a number."},
           {"!!", "Fix it (Esc clears) to see results."}}
  elseif not any then
    out = {{"!!", "Enter values above."}}
  else
    out = calc(V)
  end

  local top = 20 + 14
  local rows = #fields + #out
  local lh = 13
  local avail = h - top - 6 - 12          -- 12 reserved for the hint line
  if rows > 0 then
    local fit = math.floor(avail / rows)
    if fit < lh then lh = fit end
  end
  local small = false
  if lh < 11 then small = true end
  if lh < 9 then lh = 9 end
  local fs = 9
  if small then fs = 7 end
  local bh = lh - 1
  if bh > 12 then bh = 12 end

  gc:setColorRGB(20, 60, 120)
  gc:fillRect(0, 0, w, 17)
  gc:setColorRGB(255, 255, 255)
  gc:setFont("sansserif", "b", 10)
  gc:drawString(TITLE, 4, 1, "top")

  local y = 20
  gc:setColorRGB(110, 110, 110)
  gc:setFont("sansserif", "i", fs)
  gc:drawString(FORMULA, 4, y, "top")
  y = top

  local boxW = 86
  local boxX = w - boxW - 4
  for i = 1, #fields do
    local f = fields[i]
    if i == cur then
      gc:setColorRGB(208, 224, 245)
      gc:fillRect(0, y - 1, w, lh)
    end
    gc:setColorRGB(0, 0, 0)
    gc:setFont("sansserif", "r", fs)
    gc:drawString(f.lab, 4, y, "top")
    gc:setColorRGB(255, 255, 255)
    gc:fillRect(boxX, y - 1, boxW, bh)
    if f.bad then
      gc:setColorRGB(200, 0, 0)
    else
      gc:setColorRGB(130, 130, 130)
    end
    gc:drawRect(boxX, y - 1, boxW, bh)
    local s = f.v
    local gray = false
    if s == "" and f.d ~= nil then
      s = tostring(f.d)
      gray = true
    end
    if i == cur then s = s .. "_" end
    if #s > 15 then s = string.sub(s, #s - 14) end
    if f.bad then
      gc:setColorRGB(200, 0, 0)
    elseif gray then
      gc:setColorRGB(150, 150, 150)
    else
      gc:setColorRGB(0, 0, 0)
    end
    gc:drawString(s, boxX + 3, y, "top")
    y = y + lh
  end

  y = y + 2
  gc:setColorRGB(150, 150, 150)
  gc:drawLine(0, y, w, y)
  y = y + 4

  for i = 1, #out do
    local lab, s = out[i][1], out[i][2]
    if lab == "!!" then
      if bad then gc:setColorRGB(200, 0, 0) else gc:setColorRGB(150, 150, 150) end
      gc:setFont("sansserif", "i", fs)
      gc:drawString(s, 4, y, "top")
    elseif lab == "!" then
      gc:setColorRGB(190, 90, 0)
      gc:setFont("sansserif", "i", fs)
      gc:drawString(s, 4, y, "top")
    else
      gc:setColorRGB(20, 60, 120)
      gc:setFont("sansserif", "b", fs)
      gc:drawString(lab, 4, y, "top")
      local tw = gc:getStringWidth(s)
      gc:drawString(s, w - tw - 6, y, "top")
    end
    y = y + lh
  end

  if y <= h - 13 then
    gc:setColorRGB(150, 150, 150)
    gc:setFont("sansserif", "r", fs)
    gc:drawString("digits . (-)  |  updown move  |  esc clear", 4, h - 12, "top")
  end
end

function on.charIn(ch)
  if ch == "\226\136\146" then ch = "-" end
  local v = fields[cur].v
  if ch == "." then
    if string.find(v, ".", 1, true) then return end   -- only one decimal point
  elseif ch == "-" then
    if v ~= "" then return end                        -- minus only in first position
  elseif not string.match(ch, "^[0-9]$") then
    return
  end
  fields[cur].v = v .. ch
  platform.window:invalidate()
end

function on.backspaceKey()
  local v = fields[cur].v
  if #v > 0 then fields[cur].v = string.sub(v, 1, #v - 1) end
  platform.window:invalidate()
end

function on.escapeKey()
  fields[cur].v = ""
  platform.window:invalidate()
end

function on.enterKey()
  cur = cur % #fields + 1
  platform.window:invalidate()
end

function on.tabKey()
  on.enterKey()
end

function on.arrowKey(k)
  if k == "down" then
    cur = cur % #fields + 1
  elseif k == "up" then
    cur = (cur - 2) % #fields + 1
  end
  platform.window:invalidate()
end

function on.resize()
  platform.window:invalidate()
end
