-- ===== SPC limits, capability and Six Sigma =====
TITLE    = "SPC / Cp / Cpk / DPMO"
SUBTITLE = "Control limits, capability and sigma level"

FIELDS = {
    { key = "mean", lbl = "Process mean",       txt = "", def = "" },
    { key = "sd",   lbl = "Std deviation sigma",txt = "", def = "" },
    { key = "usl",  lbl = "USL",                txt = "", def = "" },
    { key = "lsl",  lbl = "LSL",                txt = "", def = "" },
    { key = "k",    lbl = "Limit multiple k",   txt = "3",def = "3"},
    { key = "def",  lbl = "Defects",            txt = "", def = "" },
    { key = "un",   lbl = "Units",              txt = "", def = "" },
    { key = "op",   lbl = "Opportunities/unit", txt = "", def = "" },
}

NOTE = "k = 3 gives the usual 3-sigma control limits.\n" ..
       "Cp needs both USL and LSL; Cpk also needs the mean.\n" ..
       "Sigma level uses the 1.5-sigma long-term shift.\n" ..
       "ESC resets all fields."

-- inverse standard normal (Acklam's rational approximation)
local function invnorm(p)
    if p <= 0 or p >= 1 then return nil end
    local a = { -3.969683028665376e+01, 2.209460984245205e+02,
                -2.759285104469687e+02, 1.383577518672690e+02,
                -3.066479806614716e+01, 2.506628277459239e+00 }
    local b = { -5.447609879822406e+01, 1.615858368580409e+02,
                -1.556989798598866e+02, 6.680131188771972e+01,
                -1.328068155288572e+01 }
    local c = { -7.784894002430293e-03, -3.223964580411365e-01,
                -2.400758277161838e+00, -2.549732539343734e+00,
                 4.374664141464968e+00,  2.938163982698783e+00 }
    local d = {  7.784695709041462e-03,  3.224671290700398e-01,
                 2.445134137142996e+00,  3.754408661907416e+00 }
    local pl, ph = 0.02425, 1 - 0.02425
    local q, r
    if p < pl then
        q = math.sqrt(-2 * math.log(p))
        return (((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) /
               ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
    elseif p <= ph then
        q = p - 0.5; r = q * q
        return (((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6])*q /
               (((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1)
    else
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) /
                ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
    end
end

function OUTPUTS()
    local mean, sd = V("mean"), V("sd")
    local usl, lsl = V("usl"), V("lsl")
    local k = V("k") or 3
    local out = {}

    -- control limits
    if mean and sd and sd > 0 then
        local ks = string.format("%g", k)      -- shows 2.5 as 2.5, not rounded to 2
        out[#out + 1] = { "UCL = mean + " .. ks .. "s", fmt(mean + k * sd, 4) }
        out[#out + 1] = { "Centre line",                fmt(mean, 4) }
        out[#out + 1] = { "LCL = mean - " .. ks .. "s", fmt(mean - k * sd, 4) }
        out[#out + 1] = { "Control band width",                fmt(2 * k * sd, 4) }
    end

    -- capability
    if sd and sd > 0 and usl and lsl then
        if #out > 0 then out[#out + 1] = { "--" } end
        local Cp = (usl - lsl) / (6 * sd)
        out[#out + 1] = { "Tolerance width", fmt(usl - lsl, 4) }
        out[#out + 1] = { "Cp",              fmt(Cp, 4) }
        if mean then
            local cpu = (usl - mean) / (3 * sd)
            local cpl = (mean - lsl) / (3 * sd)
            local cpk = math.min(cpu, cpl)
            out[#out + 1] = { "CPU (upper)", fmt(cpu, 4) }
            out[#out + 1] = { "CPL (lower)", fmt(cpl, 4) }
            out[#out + 1] = { "Cpk",         fmt(cpk, 4) }
            out[#out + 1] = { "Centred?",
                (math.abs(Cp - cpk) < 1e-6) and "yes" or "no - off centre" }
            if cpk >= 1.33 then
                out[#out + 1] = { "Verdict", "capable (Cpk >= 1.33)" }
            elseif cpk >= 1.0 then
                out[#out + 1] = { "Verdict", "marginal" }
            else
                out[#out + 1] = { "Verdict", "not capable" }
            end
        end
    end

    -- DPMO and sigma level
    local d, u, o = V("def"), V("un"), V("op")
    if d and u and o and u > 0 and o > 0 then
        if #out > 0 then out[#out + 1] = { "--" } end
        local dpo  = d / (u * o)
        local dpmo = dpo * 1e6
        out[#out + 1] = { "Opportunities", fmt(u * o, 0) }
        out[#out + 1] = { "DPO",           fmt(dpo, 6) }
        out[#out + 1] = { "DPMO",          fmt(dpmo, 1) }
        out[#out + 1] = { "Yield",         pct(1 - dpo, 4) }
        local z = invnorm(1 - dpo)
        if z then
            -- z comes from the observed defect rate, so it is the long-term Z;
            -- adding the 1.5 shift gives the (short-term) sigma level.
            out[#out + 1] = { "Z (long term)",      fmt(z, 4) }
            out[#out + 1] = { "Sigma level (+1.5)", fmt(z + 1.5, 4) }
        end
    end

    if #out == 0 then
        return { { "Enter mean + sigma, or spec limits,", "" },
                 { "or defects/units/opportunities", "" } }
    end
    return out
end
--@include shared/form_scrolling.lua
