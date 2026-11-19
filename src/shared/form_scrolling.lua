-- ============================================================
--  Shared field-form engine for TI-Nspire CX CAS Lua sheets
--  Up/Down or Tab : move between fields
--  0-9 . -        : type a value
--  Backspace/Del  : erase
--  Enter          : recompute (values are live anyway)
--  Rates are entered as DECIMALS (6% -> 0.06)
-- ============================================================

TITLE   = TITLE   or "Calculator"
SUBTITLE= SUBTITLE or ""
FIELDS  = FIELDS  or {}
OUTPUTS = OUTPUTS or function() return {} end
NOTE    = NOTE    or ""

local sel      = 1
local scroll   = 0
local contentH = 0      -- height of everything drawn, set by on.paint

-- ---------- helpers made available to every sheet ----------
function V(key)
    for _, f in ipairs(FIELDS) do
        if f.key == key then return tonumber(f.txt) end
    end
    return nil
end

function fmt(x, dp)
    if x == nil then return "--" end
    if x ~= x then return "undef" end
    if x == math.huge or x == -math.huge then return "inf" end
    dp = dp or 4
    local s = string.format("%." .. dp .. "f", x)
    -- trim trailing zeros but keep at least 2 dp
    if dp > 2 then
        while s:sub(-1) == "0" and #(s:match("%.(%d*)$") or "") > 2 do
            s = s:sub(1, -2)
        end
    end
    return s
end

function money(x, dp) return fmt(x, dp or 2) end

function pct(x, dp)
    if x == nil then return "--" end
    return fmt(x * 100, dp or 3) .. "%"
end

-- ---------- painting ----------
function on.paint(gc)
    local w = platform.window:width()
    local h = platform.window:height()

    gc:setColorRGB(255, 255, 255)
    gc:fillRect(0, 0, w, h)

    -- header
    gc:setColorRGB(0, 51, 102)
    gc:fillRect(0, 0, w, 20)
    gc:setColorRGB(255, 255, 255)
    gc:setFont("sansserif", "b", 10)
    gc:drawString(TITLE, 4, 15, "baseline")

    local y = 22 - scroll

    if SUBTITLE ~= "" then
        gc:setColorRGB(90, 90, 90)
        gc:setFont("sansserif", "i", 7)
        gc:drawString(SUBTITLE, 4, y + 9, "baseline")
        y = y + 13
    end

    -- inputs
    gc:setColorRGB(0, 51, 102)
    gc:setFont("sansserif", "b", 8)
    gc:drawString("INPUTS", 4, y + 9, "baseline")
    y = y + 13

    gc:setFont("sansserif", "r", 8)
    for i, f in ipairs(FIELDS) do
        if i == sel then
            gc:setColorRGB(215, 232, 255)
            gc:fillRect(2, y - 1, w - 4, 15)
            gc:setColorRGB(0, 51, 102)
            gc:drawRect(2, y - 1, w - 5, 14)
        end
        gc:setColorRGB(0, 0, 0)
        gc:drawString(f.lbl, 6, y + 11, "baseline")
        local vx = w - 78
        gc:setColorRGB(250, 250, 250)
        gc:fillRect(vx, y, 72, 13)
        gc:setColorRGB(150, 150, 150)
        gc:drawRect(vx, y, 72, 13)
        gc:setColorRGB(0, 0, 0)
        local shown = f.txt
        if i == sel then shown = shown .. "|" end
        gc:drawString(shown, vx + 3, y + 11, "baseline")
        y = y + 16
    end

    -- outputs
    y = y + 4
    gc:setColorRGB(0, 51, 102)
    gc:setFont("sansserif", "b", 8)
    gc:drawString("RESULTS", 4, y + 9, "baseline")
    y = y + 13

    local ok, res = pcall(OUTPUTS)
    if not ok then res = { { "error", tostring(res) } } end

    for _, r in ipairs(res) do
        if r[1] == "--" then
            gc:setColorRGB(190, 190, 190)
            gc:drawLine(4, y + 5, w - 4, y + 5)
            y = y + 10
        else
            gc:setFont("sansserif", "r", 8)
            gc:setColorRGB(40, 40, 40)
            gc:drawString(r[1], 6, y + 10, "baseline")
            gc:setFont("sansserif", "b", 8)
            gc:setColorRGB(0, 90, 40)
            local s = tostring(r[2])
            gc:drawString(s, w - 6 - gc:getStringWidth(s), y + 10, "baseline")
            y = y + 14
        end
    end

    if NOTE ~= "" then
        y = y + 4
        gc:setFont("sansserif", "i", 7)
        gc:setColorRGB(110, 110, 110)
        for line in NOTE:gmatch("[^\n]+") do
            gc:drawString(line, 4, y + 8, "baseline")
            y = y + 11
        end
    end

    contentH = y + scroll + 6

    -- content got shorter while scrolled down: come back up and repaint
    local limit = math.max(0, contentH - h)
    if scroll > limit then
        scroll = limit
        platform.window:invalidate()
    end
end

-- ---------- input handling ----------
local function refresh() platform.window:invalidate() end

local function ensureVisible()
    local h = platform.window:height()
    local top = 35 + (sel - 1) * 16
    if top - scroll < 20 then scroll = math.max(0, top - 20) end
    if top - scroll > h - 40 then scroll = top - h + 40 end
end

-- Down on the last field scrolls on through the results and notes. The view
-- used to be pinned to the selected field, which left the lower results of
-- the longer sheets impossible to reach.
function on.arrowDown()
    if sel < #FIELDS then
        sel = sel + 1
        ensureVisible()
    else
        local limit = math.max(0, contentH - platform.window:height())
        scroll = math.min(scroll + 16, limit)
    end
    refresh()
end

function on.arrowUp()
    local top = 35 + (sel - 1) * 16
    if scroll > 0 and top - scroll < 20 then
        scroll = math.max(0, scroll - 16)      -- scrolled past the fields: come back first
    elseif sel > 1 then
        sel = sel - 1
        ensureVisible()
    else
        scroll = math.max(0, scroll - 16)
    end
    refresh()
end

function on.tabKey()     on.arrowDown() end
function on.backtabKey() on.arrowUp()   end
function on.enterKey()   on.arrowDown() end

function on.charIn(ch)
    local f = FIELDS[sel]
    if not f then return end
    if ch == "\226\136\146" then ch = "-" end     -- the handheld's (-) key sends U+2212
    if ch:match("^[0-9]$") then                   -- one digit only: keys such as 10^x send longer text
        f.txt = f.txt .. ch
    elseif ch == "." then
        if not f.txt:find("%.") then f.txt = f.txt .. "." end
    elseif ch == "-" then
        if f.txt == "" then f.txt = "-" end
    else
        return
    end
    ensureVisible(); refresh()                    -- typing brings the field back into view
end

function on.backspaceKey()
    local f = FIELDS[sel]
    if f then f.txt = f.txt:sub(1, -2) end
    ensureVisible(); refresh()
end

function on.deleteKey() on.backspaceKey() end
function on.clearKey()
    local f = FIELDS[sel]
    if f then f.txt = "" end
    ensureVisible(); refresh()
end

function on.escapeKey()
    for _, f in ipairs(FIELDS) do f.txt = f.def or "" end
    sel = 1; scroll = 0; refresh()
end

function on.mouseDown(x, y)
    local top = 35
    if SUBTITLE ~= "" then top = top + 13 end
    local i = math.floor((y + scroll - top) / 16) + 1
    if i >= 1 and i <= #FIELDS then sel = i end
    refresh()
end

function on.resize() refresh() end
