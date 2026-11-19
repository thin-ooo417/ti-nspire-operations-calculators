-- ===== Little's Law: I = R x T =====
TITLE    = "Little's Law"
SUBTITLE = "Leave ONE of I, R, T blank to solve it"

FIELDS = {
    { key = "I",   lbl = "Inventory / WIP  I",  txt = "",   def = ""   },
    { key = "R",   lbl = "Flow rate R /period", txt = "",   def = ""   },
    { key = "T",   lbl = "Flow time T (raw)",   txt = "",   def = ""   },
    { key = "div", lbl = "T divisor (min>hr=60)",txt = "1", def = "1"  },
    { key = "Ttg", lbl = "Target T (optional)",  txt = "",  def = ""   },
    { key = "ppy", lbl = "Periods per year",     txt = "12",def = "12" },
    { key = "cost",lbl = "Cost per unit of flow",txt = "",  def = ""   },
}

NOTE = "R and T must share a time unit. If T is in minutes\n" ..
       "and R is per hour, set divisor 60.\n" ..
       "Target T + cost gives the saving from slower flow.\n" ..
       "ESC resets all fields."

function OUTPUTS()
    local I, R, Traw = V("I"), V("R"), V("T")
    local div = V("div"); if not div or div == 0 then div = 1 end
    local T = Traw and (Traw / div) or nil

    local known = 0
    if I then known = known + 1 end
    if R then known = known + 1 end
    if T then known = known + 1 end
    if known < 2 then
        return { { "Enter any two of I, R, T", "" } }
    end

    local solved = ""
    if not I then
        I = R * T; solved = "I"
    elseif not R then
        if T == 0 then return { { "T cannot be zero", "" } } end
        R = I / T; solved = "R"
    elseif not T then
        if R == 0 then return { { "R cannot be zero", "" } } end
        T = I / R; solved = "T"
    end

    local out = {
        { "Inventory I" .. (solved == "I" and "  <-- solved" or ""), fmt(I, 4) },
        { "Flow rate R" .. (solved == "R" and "  <-- solved" or ""), fmt(R, 4) },
        { "Flow time T" .. (solved == "T" and "  <-- solved" or ""), fmt(T, 4) },
    }
    if div ~= 1 then
        out[#out + 1] = { "T in original units", fmt(T * div, 4) }
    end
    out[#out + 1] = { "--" }
    out[#out + 1] = { "Cycle time 1/R", fmt(R ~= 0 and 1 / R or nil, 4) }

    -- target flow-time extension (tenure / hiring style questions)
    local Ttg = V("Ttg")
    if Ttg then
        local Tt = Ttg / div
        if Tt > 0 then
            local Rnew = I / Tt
            local ppy  = V("ppy") or 1
            local drop = R - Rnew
            out[#out + 1] = { "--" }
            out[#out + 1] = { "Target T",          fmt(Tt, 4) }
            out[#out + 1] = { "Required new R",    fmt(Rnew, 4) }
            out[#out + 1] = { "Change in R",       fmt(drop, 4) }
            out[#out + 1] = { "R per year (now)",  fmt(R * ppy, 2) }
            out[#out + 1] = { "R per year (new)",  fmt(Rnew * ppy, 2) }
            out[#out + 1] = { "Avoided per year",  fmt(drop * ppy, 2) }
            local cost = V("cost")
            if cost then
                out[#out + 1] = { "ANNUAL SAVING", money(drop * ppy * cost, 2) }
            end
        end
    end

    return out
end
--@include shared/form_scrolling.lua
