"""C63+C58 : tableau joint depenses / recettes attendues vs reelles / occasions perdues.

Inventaire (code courant, pas un banc) : les panneaux RC|/AC|/RP|/DC| et les sondes C50/C49/
LINE_REVENUE ne ferment pas le tableau. Presque tous les OpexSign ecrasent la tuile (1,1) ;
un chunk SIGN de sauvegarde ne garde que le dernier nom. C50 a pred_profit, pas pred_revenue,
et le cout de project_built est le modele. C49 compte des passes, pas des jours. LINE_REVENUE
est derriere decision_log. L'eau n'a pas d'actualCost. VEHS n'est pas une flotte.

--selftest est du Python pur (standard library). Il refuse les pieges : VEHS-as-fleet,
double comptage des jours d'occasion, caisse >= 300 k£ => CPU, perdants sans temoin profitable.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
try:
    from bench_v2 import quarter_profit, year_profit
except ImportError:
    # Permet a --selftest de s'executer en Python pur sur l'hote (sans openttdlab)
    def quarter_profit(entry):
        if not isinstance(entry, dict):
            return None
        income = entry.get("income")
        expenses = entry.get("expenses")
        if income is None or expenses is None:
            return None
        return income + expenses

    def year_profit(closed):
        profits = [quarter_profit(entry) for entry in (closed or [])[:4]]
        profits = [value for value in profits if value is not None]
        if not profits:
            return None
        return sum(profits)

FIXTURE = ROOT / "sweeps" / "fixtures" / "c63_c58_traces.json"

OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
C63_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) C63_INVEST\s*(.*)$")
C50_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) C50_CHRONO\s*(.*)$")
C49_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) C49_SCARCITY\s*(.*)$")

MODES = ("rail", "road", "air", "water", "fleet")
LEFTOVER_KINDS = ("absent", "invalid", "unaffordable", "demand", "waiting_compute")
OPP_KINDS = LEFTOVER_KINDS + ("launched",)
ABSENT_CAUSES = (
    "empty_pool",
    "unprofitable",
    "already_served",
    "no_site",
    "mode_cargo_filter",
    "selection_empty",
    "stage_empty",
    "cache_exhausted",
    "abandon_filtered",
)
DOMINANT = 0.50
OVERCOST_RATIO = 1.30
REVENUE_SHORTFALL = 0.50

NAMED_GAPS = (
    "spend_planned_vs_actual_including_failures",
    "pred_revenue_vs_real_including_profitable_witnesses",
    "opportunity_days_with_available_capital",
    "one_leftover_kind_per_pass",
)

EMPTY_SPEND = {
    "planned_ok": 0, "actual_ok": 0, "n_ok": 0,
    "planned_fail": 0, "actual_fail": 0, "n_fail": 0,
}


def parse_fields(rest):
    fields = {}
    for token in (rest or "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            fields[key] = value
    return fields


def _ai(path):
    return (ROOT / "ai" / "OpexAI" / path).read_text(encoding="utf-8")


def inventory_from_source():
    """Couverture reelle lue dans les .nut, pas une liste memorisee."""
    road = _ai("task_road.nut")
    air = _ai("task_air.nut")
    rail = _ai("task_rail.nut")
    water = _ai("task_water.nut")
    report = _ai("task_report.nut")
    probes = _ai("probes.nut")
    ledgers = _ai("ledgers.nut")
    capital = _ai("capital.nut")
    info = _ai("info.nut")
    projects = _ai("task_projects.nut")

    rc_ok = 'OpexSign(anchor, "RC|"' in road
    rp_gated = "ROAD_COST_PROBE" in road and 'OpexSign(anchor, "RP|"' in road
    ac_gated = "AIR_COST_PROBE" in air and 'OpexSign(anchor, "AC|"' in air
    dc_gated = "RAIL_COST_PROBE" in rail and 'OpexSign(anchor, "DC|"' in rail
    water_no_actual = "actualCost" not in water
    water_pred_zero = "predicted = 0" in water
    sign_overwrite = "AISign.BuildSign(anchor, name)" in probes
    tile_11 = "AIMap.GetTileIndex(1, 1)" in projects and "AIMap.GetTileIndex(1, 1)" in road
    c50_pred_profit = "pred_profit=" in report
    c50_line = ""
    for line in report.splitlines():
        if "phase=line_profit" in line or ("pred_profit=" in line and "OpexC50ChronologyLog" in line):
            c50_line += line
    c50_no_pred_rev = "pred_rev=" not in c50_line and "pred_r=" not in c50_line
    line_rev = 'OpexDecide("LINE_REVENUE"' in report
    decision_before_rev = report.find("if (DECISION_LOG)") < report.find('OpexDecide("LINE_REVENUE"')
    c49_counts = "decision_attempted" in ledgers and "entry.cash" in ledgers
    c49_no_days = "absent_d" not in ledgers and "unaffordable_d" not in ledgers
    available = (
        "GetBankBalance" in capital
        and "GetMaxLoanAmount" in capital
        and "OpexCashReserve" in capital
    )
    probe_setting = 'name = "c63_invest_probe"' in info
    helpers = (
        "OpexC63RecordSpend" in probes and "C63_INVEST" in probes
        and "OpexC63FlushLedger" in probes and "OpexC63NotePass" in probes
        and "OpexC63RecordSpendResult" in probes
        and "OpexC63CachedAvailable" in probes
        and "OpexC63EnsureYear" in probes
        and "OpexC63YearStart" in probes
        and "OpexC63RecordEmptyProbe" in probes
        and "phase=empty_probe year=" in probes
        and "OpexC63ClassifyAbsent" in probes
        and "OpexC63ChildLen" in probes
        and "stage_empty_n=" in probes
        and "cache_exhausted_n=" in probes
        and "abandon_filtered_n=" in probes
        and "function OpexAI::_c63RecordPassAndProbe" in projects
        and "this._lastBestCount" in projects
        and "this._lastEmptyProbeMonth" in projects
        and "OpexC63RecordEmptyProbe" in projects
    )

    gaps = []
    # Signs cannot persist a time series; cost probes default 0 and write signs not AILog.
    if rc_ok and sign_overwrite and tile_11:
        gaps.append("spend_planned_vs_actual_including_failures")
    if c50_pred_profit and c50_no_pred_rev and decision_before_rev:
        gaps.append("pred_revenue_vs_real_including_profitable_witnesses")
    if c49_counts and c49_no_days and available:
        gaps.append("opportunity_days_with_available_capital")
    if c49_counts and c49_no_days:
        gaps.append("one_leftover_kind_per_pass")

    return {
        "rc_success_actual_sign": rc_ok,
        "rp_behind_road_cost_probe": rp_gated,
        "ac_behind_air_cost_probe": ac_gated,
        "dc_behind_rail_cost_probe": dc_gated,
        "water_no_actual_cost": water_no_actual,
        "water_predicted_hardcoded_zero": water_pred_zero,
        "signs_overwrite_same_tile": sign_overwrite and tile_11,
        "c50_has_pred_profit_not_pred_revenue": c50_pred_profit and c50_no_pred_rev,
        "line_revenue_behind_decision_log": line_rev and decision_before_rev,
        "c49_pass_counts_not_days": c49_counts and c49_no_days,
        "opex_available_capital_defined": available,
        "c63_setting_in_info": probe_setting,
        "c63_helpers_present": helpers,
        "named_gaps": gaps,
        "existing_sources_close_joint_table": False,
    }


def signs_close_spend(signs):
    """Un snapshot SIGN (dernier nom par tuile) ne reconstitue pas RC|/AC|/RP|/DC|."""
    names = []
    for item in signs or []:
        if isinstance(item, dict):
            names.append(str(item.get("name", "")))
        else:
            names.append(str(item))
    prefixes = tuple(n.split("|", 1)[0] for n in names if n)
    has_cost = any(p in ("RC", "AC", "RP", "DC") for p in prefixes)
    return {
        "n_signs": len(names),
        "has_any_cost_prefix": has_cost,
        "last_write_only": True,
        "closes_spend_series": False,
        "closes_joint_table": False,
    }


def fleet_from_line_rows(lines):
    return sum(int(row.get("vehs", 0) or 0) for row in lines)


def fleet_from_vehs_chunks(chunks):
    raise ValueError("VEHS chunks are not a vehicle fleet")


def attach_physical(chunks):
    """STNN peut compter des gares. len(VEHS) n'est jamais une flotte."""
    stnn = (chunks or {}).get("STNN", {}) or {}
    return {"n_stations": len(stnn)}


def year_close_tail(last_date, next_year_start):
    """Queue (lastDate, 1er janv.] exclusive du 1er janv. : nextStart - lastDate - 1."""
    tail = next_year_start - last_date - 1
    return tail if tail > 0 else 0


def opportunity_days_exclusive(opp, calendar_days):
    leftover_days = sum(int(opp.get(kind, {}).get("days", 0) or 0) for kind in LEFTOVER_KINDS)
    launched_days = int(opp.get("launched", {}).get("days", 0) or 0)
    total = leftover_days + launched_days
    leftover_n = sum(int(opp.get(kind, {}).get("n", 0) or 0) for kind in LEFTOVER_KINDS)
    launched_n = int(opp.get("launched", {}).get("n", 0) or 0)
    errors = []
    if calendar_days is not None and total > int(calendar_days):
        errors.append("double_counted_opportunity_days")
    if leftover_n + launched_n < max(leftover_n, launched_n):
        errors.append("double_counted_opportunity_passes")
    return {
        "leftover_days": leftover_days,
        "launched_days": launched_days,
        "total_days": total,
        "leftover_n": leftover_n,
        "launched_n": launched_n,
        "errors": errors,
    }


def cpu_from_idle_cash(cash, leftover_kind):
    """Caisse oisive n'est pas un goulot CPU, meme au-dessus de 300 k£."""
    del cash, leftover_kind
    return False


def empty_opp():
    return {kind: {"n": 0, "days": 0} for kind in OPP_KINDS}


def empty_absent_causes():
    return {cause: {"n": 0, "days": 0} for cause in ABSENT_CAUSES}


def _minmaxmed(values):
    values = [int(v) for v in values if v is not None]
    if not values:
        return None
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "median": int(statistics.median(values)),
    }


def summarise_empty_probes(probes):
    """Agrège les sondes empty_probe : alternatives, capitaux, cache, abandons."""
    probes = list(probes or [])
    if not probes:
        return {"n": 0, "causes": {}, "n_min_cap_gt_avail": 0}
    considered = [p.get("considered") for p in probes if p.get("considered", -1) >= 0]
    min_caps = [p.get("min_cap") for p in probes if p.get("min_cap", -1) >= 0]
    avails = [p.get("avail_cap") for p in probes if p.get("avail_cap") is not None]
    n_unaffordable = sum(
        1 for p in probes
        if p.get("min_cap", -1) > 0 and p.get("min_cap", -1) > p.get("avail_cap", 0)
    )
    return {
        "n": len(probes),
        "causes": dict(Counter(p.get("cause") or "?" for p in probes)),
        "considered": _minmaxmed(considered),
        "min_cap": _minmaxmed(min_caps),
        "avail_cap": _minmaxmed(avails),
        "n_min_cap_gt_avail": n_unaffordable,
        "cache_scanned_sum": sum(int(p.get("cache_scanned") or 0) for p in probes if int(p.get("cache_scanned") or 0) >= 0),
        "cache_retained_sum": sum(int(p.get("cache_retained") or 0) for p in probes if int(p.get("cache_retained") or 0) >= 0),
        "abandon_filtered_sum": sum(int(p.get("abandon_filtered") or 0) for p in probes if int(p.get("abandon_filtered") or 0) >= 0),
    }


def parse_c63_invest(output):
    years = defaultdict(lambda: {
        "spend": {mode: dict(EMPTY_SPEND) for mode in MODES},
        "opp": empty_opp(),
        "absent_causes": empty_absent_causes(),
        "opp_absent_seen": False,
        "lines": [],
        "empty_probes": [],
    })
    for raw in (output or "").splitlines():
        match = C63_RE.search(raw)
        if not match:
            continue
        fields = parse_fields(match.group(4))
        year = int(fields.get("year", match.group(1)))
        bucket = years[year]
        phase = fields.get("phase")
        if phase == "spend":
            mode = fields.get("mode", "fleet")
            if mode not in bucket["spend"]:
                mode = "fleet"
            slot = bucket["spend"][mode]
            for key in EMPTY_SPEND:
                slot[key] += int(fields.get(key, 0) or 0)
        elif phase == "opp":
            for kind in OPP_KINDS:
                bucket["opp"][kind]["n"] += int(fields.get(kind + "_n", 0) or 0)
                bucket["opp"][kind]["days"] += int(fields.get(kind + "_d", 0) or 0)
        elif phase == "opp_absent":
            bucket["opp_absent_seen"] = True
            for cause in ABSENT_CAUSES:
                bucket["absent_causes"][cause]["n"] += int(fields.get(cause + "_n", 0) or 0)
                bucket["absent_causes"][cause]["days"] += int(fields.get(cause + "_d", 0) or 0)
        elif phase == "empty_probe":
            bucket["empty_probes"].append({
                "stage": int(fields.get("stage", -1) or -1),
                "cargo": fields.get("cargo", "-1"),
                "rail_c": int(fields.get("rail_c", 0) or 0),
                "road_c": int(fields.get("road_c", 0) or 0),
                "air_p": int(fields.get("air_p", 0) or 0),
                "water_p": int(fields.get("water_p", 0) or 0),
                "mode_c": int(fields.get("mode_c", 0) or 0),
                "considered": int(fields.get("considered", 0) or 0),
                "selected": int(fields.get("selected", 0) or 0),
                "min_cap": int(fields.get("min_cap", -1) or -1),
                "avail_cap": int(fields.get("avail_cap", 0) or 0),
                "cache_scanned": int(fields.get("cache_scanned", 0) or 0),
                "cache_retained": int(fields.get("cache_retained", 0) or 0),
                "abandon_filtered": int(fields.get("abandon_filtered", 0) or 0),
                "abandon_pairs": int(fields.get("abandon_pairs", 0) or 0),
                "cause": fields.get("cause", ""),
            })
        elif phase == "line":
            bucket["lines"].append({
                "line": int(fields.get("line", -1) or -1),
                "mode": fields.get("mode", "unknown"),
                "age": int(fields.get("age", -1) or -1),
                "pred_p": int(fields.get("pred_p", 0) or 0),
                "real_p": int(fields.get("real_p", 0) or 0),
                "pred_r": int(fields.get("pred_r", 0) or 0),
                "real_r": int(fields.get("real_r", 0) or 0),
                "vehs": int(fields.get("vehs", 0) or 0),
            })
    return dict(years)


def parse_existing_partial(output):
    """Ce que C50/C49 donnent : utile, insuffisant pour le tableau joint."""
    years = defaultdict(lambda: {
        "c50_lines": [],
        "c50_built_model_cost": 0,
        "c50_refused_cash_n": 0,
        "c49_passes": 0,
        "has_pred_revenue": False,
        "has_fail_actual": False,
        "has_opportunity_days": False,
    })
    for raw in (output or "").splitlines():
        c50 = C50_RE.search(raw)
        if c50:
            fields = parse_fields(c50.group(4))
            year = int(fields.get("year", c50.group(1)))
            phase = fields.get("phase")
            if phase == "line_profit":
                years[year]["c50_lines"].append({
                    "line": int(fields.get("line", -1) or -1),
                    "mode": fields.get("mode", "unknown"),
                    "age": int(fields.get("age", -1) or -1),
                    "pred_p": int(fields.get("pred_profit", 0) or 0),
                    "real_p": int(fields.get("profit", 0) or 0),
                    "real_r": int(fields.get("rev", 0) or 0),
                    "pred_r": None,
                    "vehs": int(fields.get("vehs", 0) or 0),
                })
            elif phase == "project_built":
                years[year]["c50_built_model_cost"] += int(fields.get("cost", 0) or 0)
            elif phase == "refused_cash":
                years[year]["c50_refused_cash_n"] += 1
            continue
        c49 = C49_RE.search(raw)
        if c49:
            fields = parse_fields(c49.group(4))
            year = int(fields.get("year", c49.group(1)))
            years[year]["c49_passes"] += int(fields.get("passes", 0) or 0)
    return dict(years)


def cohort_key(line):
    return (line.get("mode", "unknown"), int(line.get("age", -1) or -1))


def median_ratio(values):
    """Mediane : moyenne des deux centraux si l'effectif est pair."""
    if not values:
        return None
    return statistics.median(values)


def profitable_witnesses(lines):
    """Temoins profitables du meme mode et age ; les seuls perdants ne suffisent pas (C58)."""
    groups = defaultdict(list)
    for line in lines:
        groups[cohort_key(line)].append(line)
    witnessed = []
    for key, cohort in groups.items():
        positive = [row for row in cohort if int(row.get("real_p", 0) or 0) > 0]
        if not positive:
            continue
        witnessed.extend(cohort)
    return witnessed


def revenue_shortfall_by_cohort(lines):
    """Un deficit par cohorte (mode, age) ; l'air/route ne masque pas le rail."""
    groups = defaultdict(list)
    for line in lines:
        groups[cohort_key(line)].append(line)
    details = []
    any_short = False
    for key, cohort in sorted(groups.items()):
        positive = [row for row in cohort if int(row.get("real_p", 0) or 0) > 0]
        if not positive:
            continue
        ratios = []
        for row in cohort:
            pred = int(row.get("pred_p", 0) or 0)
            if pred > 0:
                ratios.append(int(row.get("real_p", 0) or 0) / pred)
        if not ratios:
            continue
        med = median_ratio(ratios)
        short = med < REVENUE_SHORTFALL
        if short:
            any_short = True
        details.append({
            "mode": key[0], "age": key[1], "median": med,
            "n": len(ratios), "shortfall": short,
        })
    return any_short, details


def revenue_shortfall_on_witnessed(lines):
    """True si une cohorte temoin est sous le seuil. La mediane renvoyee est la plus basse."""
    any_short, details = revenue_shortfall_by_cohort(lines)
    if not details:
        return False, None
    return any_short, min(d["median"] for d in details)


def overcost_by_mode(spend_by_mode):
    hits = []
    for mode, slot in spend_by_mode.items():
        planned = int(slot.get("planned_ok", 0) or 0)
        actual = int(slot.get("actual_ok", 0) or 0)
        if planned > 0 and actual / planned >= OVERCOST_RATIO:
            hits.append(mode)
    return hits


def overcost_ratio(spend_by_mode):
    planned = sum(int(slot.get("planned_ok", 0) or 0) for slot in spend_by_mode.values())
    actual = sum(int(slot.get("actual_ok", 0) or 0) for slot in spend_by_mode.values())
    if planned <= 0:
        return None
    return actual / planned


def classify_fn_source():
    probes = _ai("probes.nut")
    start = probes.index("function OpexC63ClassifyOpportunity")
    end = probes.index("function OpexC63RecordOpportunity")
    return probes[start:end]


def failures_logged_as_waiting_compute(spend, opp, leftover_days):
    """Le piege 5x6 v1 : n_fail>0 et tout le reliquat en waiting_compute, invalid=0."""
    n_fail = sum(int(slot.get("n_fail", 0) or 0) for slot in spend.values())
    wait_d = int(opp.get("waiting_compute", {}).get("days", 0) or 0)
    invalid_d = int(opp.get("invalid", {}).get("days", 0) or 0)
    unaff_d = int(opp.get("unaffordable", {}).get("days", 0) or 0)
    if (n_fail > 0 and leftover_days > 0 and wait_d == leftover_days
            and invalid_d == 0 and unaff_d == 0):
        return "failures_counted_as_waiting_compute"
    return None


def discard_append_conditions(path, reason):
    text = _ai(path)
    needle = f'reason = "{reason}"'
    found = []
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            break
        window = text[max(0, idx - 220):idx]
        found.append(window)
        start = idx + len(needle)
    return found


def leftover_shares(opp):
    total = sum(int(opp.get(kind, {}).get("days", 0) or 0) for kind in LEFTOVER_KINDS)
    if total <= 0:
        return {}, 0
    return {
        kind: int(opp.get(kind, {}).get("days", 0) or 0) / total
        for kind in LEFTOVER_KINDS
    }, total


def attribute_year(spend, opp, lines, traps):
    if traps:
        return "insufficient"
    if not lines:
        shares, leftover_total = leftover_shares(opp)
        if leftover_total <= 0:
            return "insufficient"
        dominant = max(shares, key=shares.get)
        if shares[dominant] > DOMINANT:
            if dominant == "unaffordable":
                return "capital"
            if dominant == "waiting_compute":
                return "slow_decision"
            if dominant in ("absent", "invalid"):
                return "missing_opportunity"
            if dominant == "demand":
                return "missing_opportunity"
        return "mixed"

    shares, leftover_total = leftover_shares(opp)
    if leftover_total > 0:
        dominant = max(shares, key=shares.get)
        if shares[dominant] > DOMINANT:
            if dominant == "unaffordable":
                return "capital"
            if dominant == "waiting_compute":
                return "slow_decision"
            if dominant in ("absent", "invalid", "demand"):
                return "missing_opportunity"

    over_modes = overcost_by_mode(spend)
    if over_modes:
        has_positive = any(int(row.get("real_p", 0) or 0) > 0 for row in lines)
        if has_positive:
            return "overcost"

    shortfall, _median = revenue_shortfall_on_witnessed(lines)
    if shortfall:
        return "revenue_model"

    if leftover_total > 0 and shares:
        return "mixed"
    return "mixed"


def build_joint_table(parsed, calendar_days=365, chunks=None, use_vehs_chunks=False):
    if use_vehs_chunks:
        fleet_from_vehs_chunks(chunks or {})

    physical = attach_physical(chunks) if chunks is not None else {}
    table = []
    for year in sorted(parsed):
        bucket = parsed[year]
        opp_check = opportunity_days_exclusive(bucket["opp"], calendar_days)
        traps = list(opp_check["errors"])
        fail_trap = failures_logged_as_waiting_compute(
            bucket["spend"], bucket["opp"], opp_check["leftover_days"])
        if fail_trap:
            traps.append(fail_trap)
        if year < 1970:
            traps.append("fictional_prestart_year")
        lines = bucket["lines"]
        absent_causes = bucket.get("absent_causes", empty_absent_causes())
        total_absent_d = sum(int(absent_causes[c]["days"]) for c in ABSENT_CAUSES)
        opp_absent_d = int(bucket["opp"]["absent"]["days"])
        if bucket.get("opp_absent_seen"):
            if total_absent_d != opp_absent_d:
                traps.append(
                    f"absent_causes_do_not_sum: causes={total_absent_d} absent_d={opp_absent_d}"
                )
        elif opp_absent_d > 0:
            traps.append("absent_causes_unlogged")
        absent_shares = (
            {c: int(absent_causes[c]["days"]) / total_absent_d for c in ABSENT_CAUSES}
            if total_absent_d > 0
            else {}
        )
        empty_probes = bucket.get("empty_probes", [])
        row = {
            "year": year,
            "spend": bucket["spend"],
            "opp": bucket["opp"],
            "absent_causes": absent_causes,
            "absent_shares": absent_shares,
            "lines": lines,
            "cohorts": {},
            "fleet_vehs": fleet_from_line_rows(lines),
            "leftover_days": opp_check["leftover_days"],
            "launched_days": opp_check["launched_days"],
            "leftover_shares": leftover_shares(bucket["opp"])[0],
            "traps": traps,
            "n_stations": physical.get("n_stations"),
            "capital_immobilized_until_first_revenue": "unmeasured",
            "empty_probes": empty_probes,
            "empty_probe_summary": summarise_empty_probes(empty_probes),
        }
        grouped = defaultdict(list)
        for line in lines:
            grouped[f"{line['mode']}|age={line['age']}"].append(line)
        row["cohorts"] = dict(grouped)
        _short, cohort_rev = revenue_shortfall_by_cohort(lines)
        row["cohort_revenue"] = cohort_rev
        row["attribution"] = attribute_year(bucket["spend"], bucket["opp"], lines, traps)
        row["cpu_from_idle_cash"] = False
        table.append(row)
    return table


def load_fixtures(path=FIXTURE):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def run_selftest():
    inv = inventory_from_source()
    for gap in NAMED_GAPS:
        assert gap in inv["named_gaps"], (gap, inv)
    assert inv["existing_sources_close_joint_table"] is False
    assert inv["signs_overwrite_same_tile"] is True
    assert inv["water_no_actual_cost"] is True
    assert inv["c50_has_pred_profit_not_pred_revenue"] is True
    assert inv["line_revenue_behind_decision_log"] is True
    assert inv["c49_pass_counts_not_days"] is True
    assert inv["opex_available_capital_defined"] is True
    assert inv["c63_helpers_present"] is True
    assert inv["c63_setting_in_info"] is True

    body = classify_fn_source()
    empty_idx = body.index('reason == null || reason == ""')
    empty_tail = body[empty_idx:empty_idx + 80]
    assert "waiting_compute" not in empty_tail, empty_tail
    assert 'return "invalid"' in empty_tail, empty_tail
    assert body.count('return "waiting_compute"') == 2, body
    assert 'if (railSearch) return "waiting_compute"' in body
    assert 'if (reason == "search_in_progress") return "waiting_compute"' in body
    note = _ai("probes.nut")
    assert 'railSearching && (reason == "" || reason == "search_in_progress")' in note
    assert "else if (railSearching) kind = \"waiting_compute\"" not in note
    sched = _ai("scheduler.nut")
    assert "OpexC63FlushLedger(c63y)" not in sched
    assert "c63d >= 28" not in sched
    assert "OpexC63EnsureYear" in sched
    tasks = _ai("scheduler_tasks.nut")
    assert "OpexC63FlushLedger(year - 1)" not in tasks
    assert "OpexC63EnsureYear(year)" in tasks
    flush_src = note[note.index("function OpexC63FlushLedger"):note.index("function OpexC50ChronologyLog")]
    assert "lastDate = last" not in flush_src
    assert "year < 1970" in flush_src
    assert "OpexC63YearStart(year + 1)" in flush_src
    assert "nextStart - C63_INVEST_LEDGER.lastDate - 1" in note
    assert year_close_tail(10, 22) == 11
    assert year_close_tail(21, 22) == 0
    assert year_close_tail(22, 22) == 0

    for path, reason in (
        ("task_air.nut", "build_failed"),
        ("task_air.nut", "insufficient_cash"),
        ("task_road.nut", "build_failed"),
        ("task_road.nut", "insufficient_cash"),
        ("task_water.nut", "build_failed"),
        ("task_water.nut", "insufficient_cash"),
        ("task_rail.nut", "insufficient_cash"),
        ("task_rail.nut", "cash_at_build"),
        ("task_projects.nut", "insufficient_cash"),
    ):
        conds = discard_append_conditions(path, reason)
        assert conds, (path, reason)
        for cond in conds:
            assert "C63_INVEST_PROBE" in cond, (path, reason, cond)

    rail_fail = _ai("task_rail.nut")
    assert "if (!recorded && C63_INVEST_PROBE)" in rail_fail

    assert "P1.1" not in json.dumps(inv)
    assert "P1.3" not in json.dumps(inv)

    fixtures = load_fixtures()
    calendar = int(fixtures["calendar_days"])

    full = parse_c63_invest(fixtures["full_c63"]["output"])
    table = build_joint_table(full, calendar_days=calendar)
    years = {row["year"]: row for row in table}
    assert 1970 in years and 1971 in years, years.keys()
    y70, y71 = years[1970], years[1971]
    assert y70["spend"]["air"]["actual_ok"] == 420000
    assert y70["spend"]["air"]["actual_fail"] == 180000
    assert y70["spend"]["road"]["n_fail"] == 1
    assert y71["attribution"] == "capital", y71
    assert y71["leftover_shares"]["unaffordable"] > DOMINANT
    assert y70["attribution"] == "mixed", y70
    road_cohort = y71["cohorts"]["road|age=1"]
    assert any(int(row["real_p"]) > 20000 for row in road_cohort)
    assert any(0 < int(row["real_p"]) < 20000 for row in road_cohort)
    assert y70["fleet_vehs"] == 7
    assert "n_vehicles" not in y70
    assert y70["capital_immobilized_until_first_revenue"] == "unmeasured"

    partial = parse_existing_partial(fixtures["c50_only"]["output"])
    p70 = partial[1970]
    assert p70["c50_built_model_cost"] == 30000
    assert p70["has_pred_revenue"] is False
    assert p70["has_fail_actual"] is False
    assert p70["has_opportunity_days"] is False
    assert p70["c49_passes"] == 20
    # C50 seul : pas de lignes C63 => insuffisant
    empty_c63 = parse_c63_invest(fixtures["c50_only"]["output"])
    assert empty_c63 == {}
    c50_table = build_joint_table(empty_c63, calendar_days=calendar)
    assert c50_table == []

    sign_cov = signs_close_spend(fixtures["sign_snapshot"]["signs"])
    assert sign_cov["closes_joint_table"] is False
    assert sign_cov["closes_spend_series"] is False
    assert sign_cov["last_write_only"] is True

    vehs = fixtures["vehs_trap"]
    try:
        fleet_from_vehs_chunks(vehs["chunks"])
        raise AssertionError("VEHS must be rejected as a fleet")
    except ValueError as exc:
        assert "VEHS" in str(exc)
    try:
        build_joint_table(parse_c63_invest(vehs["output"]), chunks=vehs["chunks"],
                          use_vehs_chunks=True)
        raise AssertionError("use_vehs_chunks must raise")
    except ValueError as exc:
        assert "VEHS" in str(exc)
    vehs_table = build_joint_table(parse_c63_invest(vehs["output"]), chunks=vehs["chunks"])
    assert vehs_table[0]["fleet_vehs"] == 7
    assert len(vehs["chunks"]["VEHS"]) == 12
    assert vehs_table[0]["fleet_vehs"] != len(vehs["chunks"]["VEHS"])
    physical = attach_physical(vehs["chunks"])
    assert "n_vehicles" not in physical

    doubled = parse_c63_invest(fixtures["double_count"]["output"])
    doubled_table = build_joint_table(doubled, calendar_days=calendar)
    assert "double_counted_opportunity_days" in doubled_table[0]["traps"]
    assert doubled_table[0]["attribution"] == "insufficient"

    wait_fail_log = (
        "OPEX 1972-1-1 C63_INVEST phase=spend year=1971 mode=air "
        "planned_ok=0 actual_ok=0 n_ok=0 planned_fail=468138 actual_fail=16209 n_fail=6\n"
        "OPEX 1972-1-1 C63_INVEST phase=opp year=1971 absent_n=0 absent_d=0 invalid_n=0 invalid_d=0 "
        "unaffordable_n=0 unaffordable_d=0 demand_n=0 demand_d=0 waiting_compute_n=8 "
        "waiting_compute_d=213 launched_n=0 launched_d=0\n"
        "OPEX 1972-1-1 C63_INVEST phase=line year=1971 line=1 mode=air age=1 "
        "pred_p=10000 real_p=9000 pred_r=12000 real_r=11000 vehs=2\n"
    )
    wait_fail = build_joint_table(parse_c63_invest(wait_fail_log), calendar_days=calendar)
    assert "failures_counted_as_waiting_compute" in wait_fail[0]["traps"], wait_fail[0]
    assert wait_fail[0]["attribution"] == "insufficient"

    prestart = parse_c63_invest(
        "OPEX 1970-1-1 C63_INVEST phase=opp year=1969 absent_n=1 absent_d=10 "
        "invalid_n=0 invalid_d=0 unaffordable_n=0 unaffordable_d=0 demand_n=0 demand_d=0 "
        "waiting_compute_n=0 waiting_compute_d=0 launched_n=0 launched_d=0\n"
    )
    pre_table = build_joint_table(prestart, calendar_days=calendar)
    assert pre_table[0]["year"] == 1969
    assert "fictional_prestart_year" in pre_table[0]["traps"]

    idle = fixtures["idle_cash"]
    idle_parsed = parse_c63_invest(idle["output"])
    idle_table = build_joint_table(idle_parsed, calendar_days=calendar)
    assert idle_table[0]["attribution"] == "missing_opportunity", idle_table[0]
    assert cpu_from_idle_cash(idle["cash"], "absent") is False
    assert idle_table[0]["cpu_from_idle_cash"] is False
    assert idle["cash"] >= 300000

    losers = build_joint_table(parse_c63_invest(fixtures["losers_only"]["output"]),
                               calendar_days=calendar)
    shortfall, _ = revenue_shortfall_on_witnessed(losers[0]["lines"])
    assert shortfall is False
    assert losers[0]["attribution"] != "revenue_model"

    assert median_ratio([0.1, 0.6]) == 0.35
    assert median_ratio([0.1, 0.5, 0.9]) == 0.5
    mask_log = "\n".join((
        "OPEX 1972-1-1 C63_INVEST phase=opp year=1971 absent_n=0 absent_d=0 invalid_n=0 "
        "invalid_d=0 unaffordable_n=0 unaffordable_d=0 demand_n=0 demand_d=0 "
        "waiting_compute_n=0 waiting_compute_d=0 launched_n=5 launched_d=365",
        "OPEX 1972-1-1 C63_INVEST phase=spend year=1971 mode=air planned_ok=100000 "
        "actual_ok=100000 n_ok=3 planned_fail=0 actual_fail=0 n_fail=0",
        "OPEX 1972-1-1 C63_INVEST phase=spend year=1971 mode=rail planned_ok=80000 "
        "actual_ok=80000 n_ok=2 planned_fail=0 actual_fail=0 n_fail=0",
        "OPEX 1972-1-1 C63_INVEST phase=line year=1971 line=1 mode=air age=1 "
        "pred_p=100 real_p=150 pred_r=200 real_r=250 vehs=2",
        "OPEX 1972-1-1 C63_INVEST phase=line year=1971 line=2 mode=air age=1 "
        "pred_p=100 real_p=160 pred_r=200 real_r=260 vehs=2",
        "OPEX 1972-1-1 C63_INVEST phase=line year=1971 line=3 mode=rail age=1 "
        "pred_p=100 real_p=10 pred_r=200 real_r=40 vehs=1",
        "OPEX 1972-1-1 C63_INVEST phase=line year=1971 line=4 mode=rail age=1 "
        "pred_p=100 real_p=60 pred_r=200 real_r=80 vehs=1",
    ))
    mask = build_joint_table(parse_c63_invest(mask_log), calendar_days=calendar)
    assert mask[0]["attribution"] == "revenue_model", mask[0]
    rail_rev = [c for c in mask[0]["cohort_revenue"] if c["mode"] == "rail" and c["age"] == 1][0]
    assert rail_rev["shortfall"] is True
    assert abs(rail_rev["median"] - 0.35) < 1e-12
    air_rev = [c for c in mask[0]["cohort_revenue"] if c["mode"] == "air"][0]
    assert air_rev["shortfall"] is False

    water_src = _ai("builder_water.nut")
    assert "AIAccounting" in water_src
    assert "function OpexWaterStampCost" in water_src
    assert "function OpexWaterPlannedCapital" in water_src
    assert "result.ok ? capital : 0" not in _ai("task_water.nut")
    assert 'OpexC63RecordSpendResult("water"' in _ai("task_water.nut")
    fleet_src = _ai("task_projects.nut")
    assert "entry.planePrice * added, entry.planePrice * added" not in fleet_src
    assert "plannedFull" in fleet_src
    assert "missed > 0" in fleet_src

    classify_abs = note[note.index("function OpexC63ClassifyAbsent"):note.index("function OpexC63ClassifyOpportunity")]
    assert "OpexC63ChildLen(projects, \"rail\", \"candidates\")" in classify_abs
    assert "st.railCandidates : 0" not in classify_abs
    assert "st.roadCandidates : 0" not in classify_abs
    flush_src = note[note.index("function OpexC63FlushLedger"):note.index("function OpexC50ChronologyLog")]
    assert "stage_empty_n=" in flush_src
    assert "cache_exhausted_n=" in flush_src
    assert "abandon_filtered_n=" in flush_src
    tp = _ai("task_projects.nut")
    helper = tp[tp.index("function OpexAI::_c63RecordPassAndProbe"):tp.index("function OpexAI::_purgeSubsidyFromProjects")]
    assert "this._lastBestCount > 0 || curMonth != this._lastEmptyProbeMonth" in helper
    assert "OpexC63RecordEmptyProbe" in helper
    assert 'kind == "absent" || kind == "unaffordable"' in helper
    stamp = _ai("projects.nut")
    assert "function OpexProjectsStampSelectionStats" in stamp
    assert stamp.count("OpexProjectsStampSelectionStats(") >= 4

    cause_log = "\n".join((
        "OPEX 1972-1-1 C63_INVEST phase=opp year=1971 absent_n=9 absent_d=90 invalid_n=0 "
        "invalid_d=0 unaffordable_n=0 unaffordable_d=0 demand_n=0 demand_d=0 "
        "waiting_compute_n=0 waiting_compute_d=0 launched_n=0 launched_d=0",
        "OPEX 1972-1-1 C63_INVEST phase=opp_absent year=1971 empty_pool_n=1 empty_pool_d=10 "
        "unprofitable_n=0 unprofitable_d=0 already_served_n=0 already_served_d=0 "
        "no_site_n=0 no_site_d=0 mode_cargo_filter_n=0 mode_cargo_filter_d=0 "
        "selection_empty_n=2 selection_empty_d=20 stage_empty_n=3 stage_empty_d=30 "
        "cache_exhausted_n=1 cache_exhausted_d=15 abandon_filtered_n=2 abandon_filtered_d=15",
        "OPEX 1972-1-1 C63_INVEST phase=empty_probe year=1971 stage=4 cargo=7 rail_c=12 road_c=4 "
        "air_p=8 water_p=0 mode_c=24 considered=24 selected=0 min_cap=50000 avail_cap=20000 "
        "cache_scanned=10 cache_retained=2 abandon_filtered=1 abandon_pairs=3 cause=all_unaffordable",
    ))
    cause_table = build_joint_table(parse_c63_invest(cause_log), calendar_days=calendar)
    assert cause_table[0]["absent_causes"]["stage_empty"]["days"] == 30
    assert cause_table[0]["absent_causes"]["cache_exhausted"]["days"] == 15
    assert cause_table[0]["absent_causes"]["abandon_filtered"]["days"] == 15
    assert not any(t.startswith("absent_causes") for t in cause_table[0]["traps"]), cause_table[0]["traps"]
    summary = cause_table[0]["empty_probe_summary"]
    assert summary["n"] == 1
    assert summary["min_cap"]["median"] == 50000
    assert summary["avail_cap"]["median"] == 20000
    assert summary["considered"]["median"] == 24
    assert summary["n_min_cap_gt_avail"] == 1

    mismatch_log = "\n".join((
        "OPEX 1972-1-1 C63_INVEST phase=opp year=1971 absent_n=3 absent_d=100 invalid_n=0 "
        "invalid_d=0 unaffordable_n=0 unaffordable_d=0 demand_n=0 demand_d=0 "
        "waiting_compute_n=0 waiting_compute_d=0 launched_n=0 launched_d=0",
        "OPEX 1972-1-1 C63_INVEST phase=opp_absent year=1971 empty_pool_n=1 empty_pool_d=40 "
        "unprofitable_n=0 unprofitable_d=0 already_served_n=0 already_served_d=0 "
        "no_site_n=0 no_site_d=0 mode_cargo_filter_n=0 mode_cargo_filter_d=0 "
        "selection_empty_n=0 selection_empty_d=0 stage_empty_n=0 stage_empty_d=0 "
        "cache_exhausted_n=0 cache_exhausted_d=0 abandon_filtered_n=0 abandon_filtered_d=0",
    ))
    mismatch = build_joint_table(parse_c63_invest(mismatch_log), calendar_days=calendar)
    assert any(t.startswith("absent_causes_do_not_sum") for t in mismatch[0]["traps"]), mismatch[0]["traps"]
    assert mismatch[0]["attribution"] == "insufficient"

    unlogged = build_joint_table(parse_c63_invest(
        "OPEX 1972-1-1 C63_INVEST phase=opp year=1971 absent_n=1 absent_d=10 invalid_n=0 "
        "invalid_d=0 unaffordable_n=0 unaffordable_d=0 demand_n=0 demand_d=0 "
        "waiting_compute_n=0 waiting_compute_d=0 launched_n=0 launched_d=0\n"
    ), calendar_days=calendar)
    assert "absent_causes_unlogged" in unlogged[0]["traps"]

    print("selftest ok")
    print("named_gaps", ",".join(inv["named_gaps"]))
    print("1970_attribution", y70["attribution"])
    print("1971_attribution", y71["attribution"])
    print("existing_close_table", inv["existing_sources_close_joint_table"])
    print("c63_setting_in_info", inv["c63_setting_in_info"])


CFG_SHARED = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""


def keep_c63(row):
    """Conserve le journal C63_INVEST et des compteurs de gare qualifies par proprietaire."""
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0") or {}
    closed = player.get("old_economy") or []
    last_closed = closed[0] if closed else {}
    stnn = chunks.get("STNN")
    from physical_counters import decode_stations
    stn_dec = decode_stations(stnn, target_owner=0)
    py = year_profit(closed)
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "company_value": last_closed.get("company_value", 0),
        "profit_year": py if py is not None else 0,
        "profit": quarter_profit(last_closed) or 0,
        "n_stations": stn_dec["total_stations"] if stn_dec["chunk_valid"] else None,
        "stnn_chunk_valid": stn_dec["chunk_valid"],
        "stnn_chunk_error": stn_dec["chunk_error"],
        "output": row.get("output", ""),
    },)


def run_campaign(args):
    """Diagnostic 5x6 partage contre AAAHogEx : c63_invest_probe=1 et -d script=4."""
    if not inventory_from_source()["c63_setting_in_info"]:
        raise SystemExit(
            "c63_invest_probe n'est pas un reglage : brancher la sonde defaut 0 avant "
            "la campagne 5x6, ou lancer --selftest."
        )
    import openttdlab
    from openttdlab import bananas_ai_library, local_folder, run_experiments
    sys.path.insert(0, str(ROOT / "sweeps"))
    from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, write_json_atomically

    real_check = openttdlab.subprocess.check_output

    def check_output_with_script_debug(cmd, *rest, **kwargs):
        cmd = tuple(cmd)
        if any(str(arg).startswith("-vnull") for arg in cmd):
            cmd = cmd[:1] + ("-d", "script=4") + cmd[1:]
        return real_check(cmd, *rest, **kwargs)

    openttdlab.subprocess.check_output = check_output_with_script_debug
    if "c63_invest_probe=1" not in args.arm:
        raise SystemExit("--arm doit contenir c63_invest_probe=1")
    out = args.out or (ROOT / "results" / f"diag_c63_c58_{args.years}y_{len(args.seeds)}seeds.json")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    enable_savegame_cleanup()
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("c63_invest_probe", 1),))
    hogex = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=args.workers,
        result_processor=keep_c63,
        experiments=tuple(
            {
                "seed": seed,
                "days": 365 * args.years,
                "openttd_config": CFG_SHARED,
                "ais": (opex, hogex),
            }
            for seed in args.seeds
        ),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    by_seed = {}
    years_seen = set()
    for seed in args.seeds:
        seed_rows = sorted((row for row in rows if row["seed"] == seed), key=lambda r: r["date"])
        if not seed_rows:
            raise SystemExit(f"ABORT: aucune ligne pour la graine {seed}")
        last = seed_rows[-1]
        last_year = int(str(last["date"])[:4])
        years_seen.add(last_year)
        parsed = parse_c63_invest(last.get("output", ""))
        table = build_joint_table(parsed, calendar_days=365)
        c63_years = sorted(parsed)
        by_seed[str(seed)] = {
            "last_date": last["date"],
            "company_value": last["company_value"],
            "n_stations": last["n_stations"],
            "stnn_chunk_valid": last.get("stnn_chunk_valid"),
            "stnn_chunk_error": last.get("stnn_chunk_error"),
            "table": table,
            "c63_years": c63_years,
            "has_1970_1972": {1970, 1971, 1972} <= set(c63_years),
        }
    expected_last = 1970 + args.years - 1
    missing_early = [seed for seed, payload in by_seed.items() if not payload["has_1970_1972"]]
    payload = {
        "arm": args.arm,
        "shared_game": True,
        "opponent": "AAAHogEx",
        "seeds": args.seeds,
        "years": args.years,
        "expected_last_year": expected_last,
        "inventory": inventory_from_source(),
        "by_seed": by_seed,
        "missing_1970_1972": missing_early,
        "probe_displaced": None,
    }
    write_json_atomically(out, payload)
    print("out", out)
    print("seeds", len(by_seed), "last_years", sorted(years_seen))
    if missing_early:
        print("WARN missing 1970-1972 C63 years for seeds", missing_early)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--arm", default="OpexAI[c63_invest_probe=1]")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.inventory:
        print(json.dumps(inventory_from_source(), indent=2, sort_keys=True))
        return
    run_campaign(args)


if __name__ == "__main__":
    main()
