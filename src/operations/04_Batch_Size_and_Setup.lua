-- ===== Batch size, setup time and bottleneck switching =====
TITLE    = "Batch Size & Setup"
SUBTITLE = "p_eff = p + S / B"

FIELDS = {
    { key = "S1", lbl = "Stage 1 setup S1",  txt = "",     def = ""     },
    { key = "p1", lbl = "Stage 1 run p1",    txt = "",     def = ""     },
    { key = "S2", lbl = "Stage 2 setup S2",  txt = "",     def = ""     },
    { key = "p2", lbl = "Stage 2 run p2",    txt = "",     def = ""     },
    { key = "B",  lbl = "Batch size B",      txt = "",     def = ""     },
    { key = "av", lbl = "Available time",    txt = "3600", def = "3600" },
}

NOTE = "Setup is per batch, run time is per item, same time unit.\n" ..
       "Stage 2 optional: leave blank to analyse one stage.\n" ..
       "Crossover B is where the bottleneck switches.\n" ..
       "ESC resets all fields."

function OUTPUTS()
    local S1, p1 = V("S1"), V("p1")
    local S2, p2 = V("S2"), V("p2")
    local B, av  = V("B"), V("av")

    if not (S1 and p1) then return { { "Enter S1 and p1", "" } } end
    if not B or B <= 0 then return { { "Enter batch size B > 0", "" } } end

    local e1 = p1 + S1 / B
    local out = {
        { "Stage 1 p_eff", fmt(e1, 4) },
    }
    if av and av > 0 then
        out[#out + 1] = { "Stage 1 capacity", fmt(av / e1, 4) }
    end
    out[#out + 1] = { "Stage 1 batch time", fmt(S1 + B * p1, 4) }

    local two = (S2 ~= nil and p2 ~= nil)
    if two then
        local e2 = p2 + S2 / B
        out[#out + 1] = { "--" }
        out[#out + 1] = { "Stage 2 p_eff", fmt(e2, 4) }
        if av and av > 0 then
            out[#out + 1] = { "Stage 2 capacity", fmt(av / e2, 4) }
        end
        out[#out + 1] = { "Stage 2 batch time", fmt(S2 + B * p2, 4) }

        out[#out + 1] = { "--" }
        local slow, bt
        if e1 > e2 then slow, bt = "Stage 1", e1
        elseif e2 > e1 then slow, bt = "Stage 2", e2
        else slow, bt = "tie", e1 end
        out[#out + 1] = { "BOTTLENECK",       slow }
        out[#out + 1] = { "Bottleneck p_eff", fmt(bt, 4) }
        if av and av > 0 then
            out[#out + 1] = { "LINE CAPACITY", fmt(av / bt, 4) }
        end

        -- crossover batch size: p1 + S1/B = p2 + S2/B
        local dp = p2 - p1
        local dS = S1 - S2
        out[#out + 1] = { "--" }
        if math.abs(dp) < 1e-12 then
            out[#out + 1] = { "Crossover B", "none (equal run times)" }
        else
            local Bx = dS / dp
            if Bx > 0 then
                out[#out + 1] = { "Crossover B", fmt(Bx, 4) }
                local lo = (p1 + S1 / (Bx * 0.5) > p2 + S2 / (Bx * 0.5))
                          and "Stage 1" or "Stage 2"
                local hi = (p1 + S1 / (Bx * 2) > p2 + S2 / (Bx * 2))
                          and "Stage 1" or "Stage 2"
                out[#out + 1] = { "Below crossover BN", lo }
                out[#out + 1] = { "Above crossover BN", hi }
            else
                out[#out + 1] = { "Crossover B", "none for B > 0" }
            end
        end
    end

    return out
end
--@include shared/form_scrolling.lua
