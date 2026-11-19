-- ===== Serial process line: bottleneck, capacity, WIP =====
TITLE    = "Serial Line / Bottleneck"
SUBTITLE = "Stage times in the same unit as available time"

FIELDS = {
    { key = "md", lbl = "0=times 1=capacities", txt = "0", def = "0" },
    { key = "av", lbl = "Available time",   txt = "3600", def = "3600" },
    { key = "t1", lbl = "Stage 1 time",     txt = "",     def = ""     },
    { key = "t2", lbl = "Stage 2 time",     txt = "",     def = ""     },
    { key = "t3", lbl = "Stage 3 time",     txt = "",     def = ""     },
    { key = "t4", lbl = "Stage 4 time",     txt = "",     def = ""     },
    { key = "t5", lbl = "Stage 5 time",     txt = "",     def = ""     },
    { key = "t6", lbl = "Stage 6 time",     txt = "",     def = ""     },
    { key = "nb", lbl = "New bottleneck t", txt = "",     def = ""     },
}

NOTE = "Mode 0: enter stage TIMES (3600 s = 1 hour, 60 = minutes).\n" ..
       "Mode 1: enter stage CAPACITIES directly (units/period).\n" ..
       "Leave unused stages blank.\n" ..
       "New bottleneck = what-if for improving the slowest stage.\n" ..
       "ESC resets all fields."

function OUTPUTS()
    local av = V("av")
    if not av or av <= 0 then return { { "Enter available time > 0", "" } } end

    local caps = (V("md") == 1)
    local ts, idx = {}, {}
    for i = 1, 6 do
        local v = V("t" .. i)
        -- in capacity mode the entry is units per period, so time = av / capacity
        if v and v > 0 then
            ts[#ts + 1] = caps and (av / v) or v
            idx[#idx + 1] = i
        end
    end
    if #ts == 0 then
        return { { caps and "Enter at least one capacity"
                        or "Enter at least one stage time", "" } }
    end

    local sum, mx, mi = 0, -1, 1
    for i, v in ipairs(ts) do
        sum = sum + v
        if v > mx then mx = v; mi = i end
    end

    local out = {}
    for i, v in ipairs(ts) do
        local tag = "Stage " .. idx[i] .. " cap"
        if i == mi then tag = tag .. "  *BN*" end
        out[#out + 1] = { tag, fmt(av / v, 2) }
    end

    local C = av / mx
    local R = C
    local T = sum
    local WIP = R * (T / av)

    out[#out + 1] = { "--" }
    out[#out + 1] = { "Bottleneck stage",   "Stage " .. idx[mi] }
    out[#out + 1] = { "Bottleneck time",    fmt(mx, 4) }
    out[#out + 1] = { "LINE CAPACITY",      fmt(C, 4) }
    out[#out + 1] = { "--" }
    out[#out + 1] = { "Throughput time T",  fmt(T, 4) }
    out[#out + 1] = { "Cycle time 1/R",     fmt(mx, 4) }
    out[#out + 1] = { "WIP  I = R x T",     fmt(WIP, 4) }

    local nb = V("nb")
    if nb and nb > 0 then
        if caps then nb = av / nb end
        -- new bottleneck is the max of the replacement and the other stages
        local other = 0
        for i, v in ipairs(ts) do
            if i ~= mi and v > other then other = v end
        end
        local newmax = math.max(nb, other)
        local Cn = av / newmax
        out[#out + 1] = { "--" }
        out[#out + 1] = { "New bottleneck time", fmt(newmax, 4) }
        out[#out + 1] = { "New capacity",        fmt(Cn, 4) }
        out[#out + 1] = { "Capacity change",     fmt(Cn - C, 4) }
        out[#out + 1] = { "% change",            pct((Cn - C) / C, 2) }
        if newmax >= mx - 1e-12 then
            out[#out + 1] = { "note", "no gain: still limited" }
        end
    end

    return out
end
--@include shared/form_scrolling.lua
