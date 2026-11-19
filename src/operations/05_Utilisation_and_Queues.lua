-- ===== Utilisation and queueing =====
TITLE    = "Utilisation & Queues"
SUBTITLE = "rho = lambda / (c x mu)"

FIELDS = {
    { key = "lam", lbl = "Arrival rate lambda", txt = "",  def = ""  },
    { key = "mu",  lbl = "Service rate mu",     txt = "",  def = ""  },
    { key = "c",   lbl = "Servers c",           txt = "1", def = "1" },
    { key = "cva", lbl = "CV arrivals (opt)",   txt = "",  def = ""  },
    { key = "cvs", lbl = "CV service (opt)",    txt = "",  def = ""  },
}

NOTE = "lambda and mu must use the same time unit.\n" ..
       "M/M/1 results shown when c = 1.\n" ..
       "CVs give the Kingman VUT waiting-time estimate.\n" ..
       "ESC resets all fields."

function OUTPUTS()
    local lam, mu = V("lam"), V("mu")
    local c = V("c") or 1
    if not (lam and mu) then return { { "Enter lambda and mu", "" } } end
    if mu <= 0 or c <= 0 then return { { "mu and c must be > 0", "" } } end

    local rho = lam / (c * mu)
    local te  = 1 / mu

    local out = {
        { "Utilisation rho", fmt(rho, 4) },
        { "rho as %",        pct(rho, 2) },
        { "Service time te", fmt(te, 4) },
    }

    if rho >= 1 then
        out[#out + 1] = { "--" }
        out[#out + 1] = { "UNSTABLE", "rho >= 1: queue grows" }
        out[#out + 1] = { "Shortfall in capacity", fmt(lam - c * mu, 4) }
        return out
    end

    local king = rho / (1 - rho)
    out[#out + 1] = { "Kingman factor r/(1-r)", fmt(king, 4) }

    if c == 1 then
        local L  = rho / (1 - rho)
        local Lq = rho * rho / (1 - rho)
        local W  = 1 / (mu - lam)
        local Wq = rho / (mu - lam)
        out[#out + 1] = { "--" }
        out[#out + 1] = { "M/M/1  L  in system",  fmt(L, 4) }
        out[#out + 1] = { "M/M/1  Lq in queue",   fmt(Lq, 4) }
        out[#out + 1] = { "M/M/1  W  in system",  fmt(W, 4) }
        out[#out + 1] = { "M/M/1  Wq in queue",   fmt(Wq, 4) }
        out[#out + 1] = { "P(system empty)",      fmt(1 - rho, 4) }
    end

    local cva, cvs = V("cva"), V("cvs")
    if cva and cvs then
        local varf = (cva * cva + cvs * cvs) / 2
        -- Multi-server form (Sakasegawa): the waiting term is divided by c.
        -- It was missing, which overstated Wq by a factor of c when c > 1.
        local Wqk  = varf * (rho ^ (math.sqrt(2 * (c + 1)) - 1) / (c * (1 - rho))) * te
        if c == 1 then Wqk = varf * king * te end
        out[#out + 1] = { "--" }
        out[#out + 1] = { "Variability factor V", fmt(varf, 4) }
        out[#out + 1] = { "Kingman Wq (VUT)",     fmt(Wqk, 4) }
        out[#out + 1] = { "Kingman Lq",           fmt(Wqk * lam, 4) }
    end

    -- how the queue explodes as rho rises
    out[#out + 1] = { "--" }
    for _, r in ipairs({ 0.8, 0.9, 0.95, 0.99 }) do
        out[#out + 1] = { "r/(1-r) at rho=" .. r, fmt(r / (1 - r), 2) }
    end

    return out
end
--@include shared/form_scrolling.lua
