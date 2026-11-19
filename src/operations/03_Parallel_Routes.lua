-- ===== Parallel routes: each route serial, routes concurrent =====
TITLE    = "Parallel Routes Capacity"
SUBTITLE = "Route capacity = min stage; total = sum of routes"

FIELDS = {
    { key = "av", lbl = "Available time",   txt = "60", def = "60" },
    { key = "a1", lbl = "Route A stage 1",  txt = "",   def = ""   },
    { key = "a2", lbl = "Route A stage 2",  txt = "",   def = ""   },
    { key = "a3", lbl = "Route A stage 3",  txt = "",   def = ""   },
    { key = "b1", lbl = "Route B stage 1",  txt = "",   def = ""   },
    { key = "b2", lbl = "Route B stage 2",  txt = "",   def = ""   },
    { key = "b3", lbl = "Route B stage 3",  txt = "",   def = ""   },
    { key = "base",lbl = "Baseline total",  txt = "",   def = ""   },
}

NOTE = "Available time 60 with minute stage times gives per-hour.\n" ..
       "Leave unused stages blank. A route with no stages is ignored.\n" ..
       "Baseline total (optional) gives the % change.\n" ..
       "ESC resets all fields."

local function route(av, keys)
    local mx, n = -1, 0
    for _, k in ipairs(keys) do
        local v = V(k)
        if v and v > 0 then n = n + 1; if v > mx then mx = v end end
    end
    if n == 0 then return nil, nil, 0 end
    return av / mx, mx, n
end

function OUTPUTS()
    local av = V("av")
    if not av or av <= 0 then return { { "Enter available time > 0", "" } } end

    local Ca, ta, na = route(av, { "a1", "a2", "a3" })
    local Cb, tb, nb = route(av, { "b1", "b2", "b3" })

    if na == 0 and nb == 0 then
        return { { "Enter at least one stage time", "" } }
    end

    local out = {}
    if Ca then
        out[#out + 1] = { "Route A bottleneck t", fmt(ta, 4) }
        out[#out + 1] = { "Route A capacity",     fmt(Ca, 4) }
    end
    if Cb then
        out[#out + 1] = { "Route B bottleneck t", fmt(tb, 4) }
        out[#out + 1] = { "Route B capacity",     fmt(Cb, 4) }
    end

    local tot = (Ca or 0) + (Cb or 0)
    out[#out + 1] = { "--" }
    out[#out + 1] = { "TOTAL CAPACITY", fmt(tot, 4) }

    local base = V("base")
    if base and base > 0 then
        out[#out + 1] = { "--" }
        out[#out + 1] = { "Baseline total", fmt(base, 4) }
        out[#out + 1] = { "Change",         fmt(tot - base, 4) }
        out[#out + 1] = { "% CHANGE",       pct((tot - base) / base, 2) }
    end

    -- serial reading of the same figures, for contrast
    if Ca and Cb then
        out[#out + 1] = { "--" }
        out[#out + 1] = { "If routes were SERIAL", fmt(math.min(Ca, Cb), 4) }
    end

    return out
end
--@include shared/form_scrolling.lua
