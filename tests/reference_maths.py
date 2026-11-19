"""Independent reference calculations for the tests.

Written from the textbook definitions rather than from the Lua, and using
different methods where the sheets use closed forms or approximations
(summation instead of annuity formulas, erfc instead of rational
approximations, numerical integration for Student's t, Erlang C for queues).
Standard library only.
"""

from __future__ import annotations

import math
import statistics

# --- time value of money -------------------------------------------------------

def npv(rate: float, cashflows: list[float]) -> float:
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def annuity_factor(rate: float, periods: int) -> float:
    return sum(1 / (1 + rate) ** t for t in range(1, periods + 1))


def bond_price(coupon: float, face: float, yld: float, periods: int) -> float:
    return sum(coupon / (1 + yld) ** t for t in range(1, periods + 1)) + face / (1 + yld) ** periods


def payback(cashflows: list[float]) -> float | None:
    """Undiscounted payback in years, interpolating within the year it turns positive."""
    running = cashflows[0]
    if running >= 0:
        return 0.0
    for year in range(1, len(cashflows)):
        before = running
        running += cashflows[year]
        if running >= 0:
            return (year - 1) + (-before) / cashflows[year]
    return None


# --- portfolios ------------------------------------------------------------------

def two_asset_variance(xa: float, xb: float, sa: float, sb: float, rho: float) -> float:
    cov = [[sa * sa, rho * sa * sb], [rho * sa * sb, sb * sb]]
    w = [xa, xb]
    return sum(w[i] * w[j] * cov[i][j] for i in range(2) for j in range(2))


# --- distributions ---------------------------------------------------------------

def norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2))


def norm_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2))


def norm_ppf(p: float) -> float:
    return statistics.NormalDist().inv_cdf(p)


def _t_pdf(x: float, df: float) -> float:
    log_c = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)
    return math.exp(log_c - (df + 1) / 2 * math.log1p(x * x / df))


def t_cdf(t: float, df: float, steps: int = 4000) -> float:
    """Student's t CDF by Simpson's rule on the density."""
    if t == 0:
        return 0.5
    upper = abs(t)
    h = upper / steps
    total = _t_pdf(0, df) + _t_pdf(upper, df)
    for i in range(1, steps):
        total += (4 if i % 2 else 2) * _t_pdf(i * h, df)
    area = total * h / 3
    return 0.5 + area if t > 0 else 0.5 - area


def t_ppf(p: float, df: float) -> float:
    lo, hi = -200.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --- queues ----------------------------------------------------------------------

def erlang_c_wait(arrival: float, service: float, servers: int) -> float:
    """Exact mean wait in queue for M/M/c."""
    offered = arrival / service
    rho = offered / servers
    head = sum(offered ** k / math.factorial(k) for k in range(servers))
    tail = offered ** servers / (math.factorial(servers) * (1 - rho))
    p_wait = tail / (head + tail)
    return p_wait / (servers * service - arrival)
