"""Technology & Operations sheets."""

from __future__ import annotations

import math

import pytest

import reference_maths as ref
from conftest import load, names
from form_drivers import V2, Scroll, check_dp, check_v2


def test_every_operations_sheet_is_covered():
    here = {"01_Littles_Law", "02_Serial_Line_Bottleneck", "03_Parallel_Routes", "04_Batch_Size_and_Setup",
            "05_Utilisation_and_Queues", "06_Takt_and_Cycle_Time", "07_SPC_and_Six_Sigma", "08_Process_Capacity"}
    assert set(names(folder="operations")) == here


# --- 01 Little's Law -------------------------------------------------------------

def test_littles_law_solves_inventory_with_a_unit_divisor():
    form = Scroll("01_Littles_Law").set({"R": "4", "T": "30", "div": "60"})
    form.expect({"Inventory I  <-- solved": 2.0, "Flow rate R": 4.0, "Flow time T": 0.5,
                 "T in original units": 30.0, "Cycle time 1/R": 0.25})


def test_littles_law_solves_rate_and_time():
    Scroll("01_Littles_Law").set({"I": "120", "T": "30"}).expect({"Flow rate R  <-- solved": 4.0})
    Scroll("01_Littles_Law").set({"I": "120", "R": "4"}).expect({"Flow time T  <-- solved": 30.0})


def test_littles_law_target_flow_time_and_saving():
    form = Scroll("01_Littles_Law").set({"I": "120", "T": "30", "Ttg": "24", "ppy": "12", "cost": "500"})
    form.expect({
        "Flow rate R  <-- solved": 4.0, "Target T": 24.0, "Required new R": 5.0, "Change in R": -1.0,
        "R per year (now)": (48.0, 2), "R per year (new)": (60.0, 2), "Avoided per year": (-12.0, 2),
        "ANNUAL SAVING": (-6000.0, 2),
    })


def test_littles_law_messages():
    assert ("Enter any two of I, R, T", "") in Scroll("01_Littles_Law").set({"I": "5"}).rows()
    assert ("T cannot be zero", "") in Scroll("01_Littles_Law").set({"I": "5", "T": "0"}).rows()
    assert ("R cannot be zero", "") in Scroll("01_Littles_Law").set({"I": "5", "R": "0"}).rows()


# --- 02 serial line ----------------------------------------------------------------

def test_serial_line_from_stage_times():
    times = [30, 45, 60, 20]
    form = Scroll("02_Serial_Line_Bottleneck").set(
        {"t1": "30", "t2": "45", "t3": "60", "t4": "20", "nb": "40"})
    shown = form.results()
    for i, t in enumerate(times, start=1):
        label = f"Stage {i} cap" + ("  *BN*" if t == max(times) else "")
        check_dp(shown[label], 3600 / t, 2)
    assert shown["Bottleneck stage"] == "Stage 3"
    capacity = 3600 / max(times)
    form.expect({"Bottleneck time": 60.0, "LINE CAPACITY": capacity, "Throughput time T": float(sum(times)),
                 "Cycle time 1/R": 60.0, "WIP  I = R x T": capacity * sum(times) / 3600,
                 # speeding stage 3 up to 40 leaves stage 2 (45) as the limit
                 "New bottleneck time": 45.0, "New capacity": 80.0, "Capacity change": 20.0,
                 "% change": (80 / 60 - 1, 2)})


def test_serial_line_from_capacities():
    form = Scroll("02_Serial_Line_Bottleneck").set({"md": "1", "av": "8", "t1": "40", "t2": "25", "t3": "32"})
    assert form.results()["Bottleneck stage"] == "Stage 2"
    form.expect({"LINE CAPACITY": 25.0, "Bottleneck time": 8 / 25})


def test_serial_line_no_gain_note():
    form = Scroll("02_Serial_Line_Bottleneck").set({"t1": "30", "t2": "60", "nb": "70"})
    assert form.results()["note"] == "no gain: still limited"


# --- 03 parallel routes --------------------------------------------------------------

def test_parallel_routes():
    form = Scroll("03_Parallel_Routes").set({"a1": "5", "a2": "6", "b1": "4", "b2": "10", "base": "12"})
    form.expect({"Route A bottleneck t": 6.0, "Route A capacity": 10.0, "Route B bottleneck t": 10.0,
                 "Route B capacity": 6.0, "TOTAL CAPACITY": 16.0, "Change": 4.0, "% CHANGE": (4 / 12, 2),
                 "If routes were SERIAL": 6.0})


def test_parallel_routes_single_route():
    form = Scroll("03_Parallel_Routes").set({"a1": "5", "a2": "6"})
    form.expect({"TOTAL CAPACITY": 10.0})
    assert "Route B capacity" not in form.results()


# --- 04 batch size and setup -----------------------------------------------------------

def test_batch_size_two_stages():
    s1, p1, s2, p2, batch, avail = 30.0, 2.0, 60.0, 1.0, 20.0, 3600.0
    e1, e2 = p1 + s1 / batch, p2 + s2 / batch
    form = Scroll("04_Batch_Size_and_Setup").set({"S1": "30", "p1": "2", "S2": "60", "p2": "1", "B": "20"})
    form.expect({"Stage 1 p_eff": e1, "Stage 1 capacity": avail / e1, "Stage 1 batch time": s1 + batch * p1,
                 "Stage 2 p_eff": e2, "Stage 2 capacity": avail / e2, "Stage 2 batch time": s2 + batch * p2,
                 "Bottleneck p_eff": max(e1, e2), "LINE CAPACITY": avail / max(e1, e2),
                 "Crossover B": (s1 - s2) / (p2 - p1)})
    shown = form.results()
    assert shown["BOTTLENECK"] == "Stage 2"
    assert shown["Below crossover BN"] == "Stage 2" and shown["Above crossover BN"] == "Stage 1"


def test_batch_size_one_stage_and_messages():
    form = Scroll("04_Batch_Size_and_Setup").set({"S1": "30", "p1": "2", "B": "10"})
    form.expect({"Stage 1 p_eff": 5.0, "Stage 1 capacity": 720.0, "Stage 1 batch time": 50.0})
    assert "BOTTLENECK" not in form.results()
    assert ("Enter batch size B > 0", "") in Scroll("04_Batch_Size_and_Setup").set({"S1": "30", "p1": "2"}).rows()


def test_batch_size_no_crossover():
    form = Scroll("04_Batch_Size_and_Setup").set({"S1": "30", "p1": "2", "S2": "60", "p2": "3", "B": "10"})
    assert form.results()["Crossover B"] == "none for B > 0"


# --- 05 utilisation and queues ----------------------------------------------------------

def test_single_server_queue():
    lam, mu = 8.0, 10.0
    rho = lam / mu
    form = Scroll("05_Utilisation_and_Queues").set({"lam": "8", "mu": "10", "cva": "1", "cvs": "1"})
    form.expect({
        "Utilisation rho": rho, "rho as %": (rho, 2), "Service time te": 1 / mu, "Kingman factor r/(1-r)": rho / (1 - rho),
        "M/M/1  L  in system": lam / (mu - lam), "M/M/1  Lq in queue": lam ** 2 / (mu * (mu - lam)),
        "M/M/1  W  in system": 1 / (mu - lam), "M/M/1  Wq in queue": ref.erlang_c_wait(lam, mu, 1),
        "P(system empty)": 1 - rho, "Variability factor V": 1.0,
        # with both CVs at 1 the Kingman estimate is exact for one server
        "Kingman Wq (VUT)": ref.erlang_c_wait(lam, mu, 1), "Kingman Lq": lam * ref.erlang_c_wait(lam, mu, 1),
        "r/(1-r) at rho=0.8": (4.0, 2), "r/(1-r) at rho=0.99": (99.0, 2),
    })


def test_single_server_queue_with_low_variability():
    form = Scroll("05_Utilisation_and_Queues").set({"lam": "8", "mu": "10", "cva": "0.5", "cvs": "1.5"})
    form.expect({"Variability factor V": (0.25 + 2.25) / 2, "Kingman Wq (VUT)": 1.25 * 4 * 0.1})


@pytest.mark.parametrize("lam,mu,servers", [(1.6, 1.0, 2), (2.4, 1.0, 3), (7.0, 2.0, 4), (4.5, 1.0, 5)])
def test_multi_server_wait_uses_the_per_server_form(lam, mu, servers):
    """The multi-server estimate left out the division by c, so it was c times too large."""
    rho = lam / (servers * mu)
    form = Scroll("05_Utilisation_and_Queues").set(
        {"lam": str(lam), "mu": str(mu), "c": str(servers), "cva": "1", "cvs": "1"})
    expected = rho ** (math.sqrt(2 * (servers + 1)) - 1) / (servers * (1 - rho)) / mu
    form.expect({"Kingman Wq (VUT)": expected, "Kingman Lq": expected * lam})
    # and the approximation should sit close to the exact M/M/c wait
    exact = ref.erlang_c_wait(lam, mu, servers)
    assert abs(float(form.results()["Kingman Wq (VUT)"]) - exact) <= 0.06 * exact
    assert "M/M/1  L  in system" not in form.results()


def test_unstable_queue():
    form = Scroll("05_Utilisation_and_Queues").set({"lam": "12", "mu": "10"})
    shown = form.results()
    assert shown["UNSTABLE"] == "rho >= 1: queue grows"
    form.expect({"Shortfall in capacity": 2.0})
    assert "Kingman factor r/(1-r)" not in shown


# --- 06 takt ---------------------------------------------------------------------------

def test_takt_cycle_capacity():
    form = Scroll("06_Takt_and_Cycle_Time").set({"av": "480", "dm": "240", "p": "1.5", "R": "0.4", "wc": "7"})
    form.expect({"TAKT time": 2.0, "Required rate": (0.5, 6), "Work content": 7.0, "Stations (exact)": 3.5,
                 "Stations (round up)": (4, 0), "CAPACITY from p": 320.0, "Cycle time = p": 1.5,
                 "Capacity vs demand": 80.0, "Utilisation needed": (0.75, 2), "Cycle time 1/R": (2.5, 6),
                 "Output in avail. time": 192.0})
    assert form.results()["Feasible?"] == "yes"


def test_takt_infeasible():
    form = Scroll("06_Takt_and_Cycle_Time").set({"av": "480", "dm": "400", "p": "1.5"})
    assert form.results()["Feasible?"] == "NO - too slow"


# --- 07 SPC ------------------------------------------------------------------------------

def test_control_limits_and_capability():
    form = Scroll("07_SPC_and_Six_Sigma").set({"mean": "10", "sd": "0.5", "usl": "12", "lsl": "8.5"})
    form.expect({"UCL = mean + 3s": 11.5, "Centre line": 10.0, "LCL = mean - 3s": 8.5, "Control band width": 3.0,
                 "Tolerance width": 3.5, "Cp": 3.5 / 3, "CPU (upper)": 2 / 1.5, "CPL (lower)": 1.0, "Cpk": 1.0})
    shown = form.results()
    assert shown["Centred?"] == "no - off centre" and shown["Verdict"] == "marginal"


def test_control_limit_label_shows_a_fractional_multiple():
    """k = 2.5 used to be labelled 'mean + 2s'."""
    form = Scroll("07_SPC_and_Six_Sigma").set({"mean": "10", "sd": "2", "k": "2.5"})
    form.expect({"UCL = mean + 2.5s": 15.0, "LCL = mean - 2.5s": 5.0})


@pytest.mark.parametrize("usl,lsl,verdict", [("13", "7", "capable (Cpk >= 1.33)"), ("11.6", "8.4", "marginal"),
                                             ("11", "9", "not capable")])
def test_capability_verdict(usl, lsl, verdict):
    form = Scroll("07_SPC_and_Six_Sigma").set({"mean": "10", "sd": "0.5", "usl": usl, "lsl": lsl})
    assert form.results()["Verdict"] == verdict


def test_dpmo_and_sigma_level():
    form = Scroll("07_SPC_and_Six_Sigma").set({"def": "34", "un": "1000", "op": "10"})
    z = ref.norm_ppf(1 - 0.0034)
    form.expect({"Opportunities": (10000, 0), "DPO": (0.0034, 6), "DPMO": (3400.0, 1), "Yield": (0.9966, 4),
                 "Z (long term)": z, "Sigma level (+1.5)": z + 1.5})


def test_three_sigma_process_reads_as_sigma_level_three():
    # 66,807 defects per million is the textbook figure for a 3-sigma process
    form = Scroll("07_SPC_and_Six_Sigma").set({"def": "66807", "un": "1000000", "op": "1"})
    assert abs(float(form.results()["Sigma level (+1.5)"]) - 3.0) < 0.001


# --- 08 process (standard form plus a map pane) ---------------------------------------------------

def test_process_capacity_and_bottleneck():
    form = V2("08_Process_Capacity").set({"la": "30", "bk": "0.1", "t1": "4", "c1": "2", "t2": "3", "t3": "10",
                                     "c3": "4", "tf": "25"})
    shown = form.results()
    check_v2(shown["Throughput R/hr"], 27.0)
    assert shown["Cap S1/S2/S3"] == "30/20/24"
    assert shown["Bottleneck"] == "S2  20/hr"
    check_v2(shown["BN utilisation"], 27 / 20)
    check_v2(shown["In store I=RxT"], 27 * 25 / 60)
    assert "Demand > capacity: queue grows, balking." in form.warnings()


def test_process_input_checks():
    form = V2("08_Process_Capacity").set({"la": "10", "bk": "1.5", "t1": "4"})
    assert "Check inputs: b in 0-1, t and c > 0." in form.warnings()
    form = V2("08_Process_Capacity").set({"la": "10", "t1": "4", "t2": "6", "tf": "5"})
    assert "T is below total work time: check T." in form.warnings()


def test_process_map_pane():
    form = V2("08_Process_Capacity").set({"la": "30", "bk": "0.1", "t1": "4", "c1": "2", "t2": "3", "t3": "10",
                                     "c3": "4", "tf": "25"})
    sheet = form.sheet
    sheet.right()
    texts = sheet.texts()
    assert "Process map" in texts
    assert "Bottleneck: S2   20/hr" in texts
    assert "Throughput R = 27/hr" in texts
    assert "balk 3/hr" in texts
    sheet.type("999")                       # typing is ignored on the map
    sheet.escape()                          # esc returns to the inputs without clearing a field
    assert "Process map" not in sheet.texts()
    check_v2(form.results()["Throughput R/hr"], 27.0)


def test_process_map_refuses_bad_or_empty_input():
    sheet = load("08_Process_Capacity")
    sheet.right()
    assert "Enter values on the input page first." in sheet.texts()
    sheet.left()
    sheet.type("-")
    sheet.right()
    assert "An entry is not a number." in sheet.texts()
