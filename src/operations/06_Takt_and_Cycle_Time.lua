-- ===== Takt time, cycle time and capacity =====
TITLE    = "Takt / Cycle / Capacity"
SUBTITLE = "Pace, rate and stations required"

FIELDS = {
    { key = "av", lbl = "Available time",     txt = "",  def = "" },
    { key = "dm", lbl = "Customer demand",    txt = "",  def = "" },
    { key = "p",  lbl = "Proc. time per unit",txt = "",  def = "" },
    { key = "R",  lbl = "Flow rate R (opt)",  txt = "",  def = "" },
    { key = "wc", lbl = "Total work content", txt = "",  def = "" },
}

NOTE = "Takt = available time / demand.\n" ..
       "Capacity = available time / processing time per unit.\n" ..
       "Work content / takt = minimum number of stations.\n" ..
       "ESC resets all fields."

function OUTPUTS()
    local av, dm, p = V("av"), V("dm"), V("p")
    local R, wc = V("R"), V("wc")
    local out = {}

    if av and dm and dm > 0 then
        local takt = av / dm
        out[#out + 1] = { "TAKT time",        fmt(takt, 4) }
        out[#out + 1] = { "Required rate",    fmt(dm / av, 6) }
        if wc and wc > 0 then
            local n = wc / takt
            out[#out + 1] = { "Work content",       fmt(wc, 4) }
            out[#out + 1] = { "Stations (exact)",   fmt(n, 4) }
            out[#out + 1] = { "Stations (round up)",fmt(math.ceil(n - 1e-9), 0) }
        end
    end

    if av and p and p > 0 then
        local C = av / p
        if #out > 0 then out[#out + 1] = { "--" } end
        out[#out + 1] = { "CAPACITY from p", fmt(C, 4) }
        out[#out + 1] = { "Cycle time = p",  fmt(p, 4) }
        if dm and dm > 0 then
            out[#out + 1] = { "Capacity vs demand", fmt(C - dm, 4) }
            out[#out + 1] = { "Utilisation needed", pct(dm / C, 2) }
            out[#out + 1] = { "Feasible?", (C >= dm) and "yes" or "NO - too slow" }
        end
    end

    if R and R > 0 then
        if #out > 0 then out[#out + 1] = { "--" } end
        out[#out + 1] = { "Cycle time 1/R", fmt(1 / R, 6) }
        if av then out[#out + 1] = { "Output in avail. time", fmt(R * av, 4) } end
    end

    if #out == 0 then
        return { { "Enter available time plus demand,", "" },
                 { "processing time or flow rate", "" } }
    end
    return out
end
--@include shared/form_scrolling.lua
