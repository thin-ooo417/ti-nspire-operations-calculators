-- Test-only sheet for the engine tests. Never built or shipped.
local TITLE = "Engine test sheet"
local FORMULA = "PV = CF / (1+r)^t"

local fields = {
  {k="cf", lab="CF  cashflow", v=""},
  {k="r", lab="r  rate (decimal)", v=""},
  {k="t", lab="t  periods", v=""},
  {k="g", lab="g  default zero", v="", d=0},
}

local function calc(V)
  local p
  if V.cf and V.r and V.t then p = V.cf / (1 + V.r)^V.t end
  local out = {{"PV", fmt(p)}, {"rate as %", pct(V.r)}}
  if V.g and V.g ~= 0 then out[#out + 1] = {"!", "g is not zero."} end
  return out
end

--@include shared/form_standard.lua
