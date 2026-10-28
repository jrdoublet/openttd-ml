#!/usr/bin/env python3
"""Descriptive paired financial/physical/opcode analysis of ESTIM+AIR sites 40x5.

Reads frozen results only; never launches OpenTTD. A run may be incomplete:
missing campaigns/years/logs are reported as missing, never treated as zero.
SPAN opcodes are *inclusive*; subtract direct children before summing tasks.
Money spent on construction is only observed where ESTIM_SPEND explicitly
reports actual_paid; operating expenses and bank balances are NOT equivalent.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
from pathlib import Path
import re
from statistics import mean, median


ROOT = Path(__file__).resolve().parents[1]
ARMS = ("OpexAI", "AAAHogEx")
YEARS = range(1970, 1975)
LOG_RE = re.compile(r"\[0\]\s+\[I\]\s+OPEX\s+(\d{4})-(\d+)-(\d+)\s+([A-Z0-9_]+)\s+(.*)")
FIELDS_RE = re.compile(r"([\w]+)=([^\s]+)")
LOG_NAME_RE = re.compile(r".*_seed(\d+)_r0\.log(?:\.gz)?$")


def stat(values):
    valid = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    return {"n": len(valid), "mean": round(mean(valid), 3) if valid else None,
            "median": round(median(valid), 3) if valid else None,
            "min": min(valid) if valid else None, "max": max(valid) if valid else None}


def numeric(s):
    try:
        n = float(s)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def clean_int(s):
    n = numeric(s)
    return int(n) if n is not None and n.is_integer() else None


def span_category(name):
    """Best-effort labels for exclusive samples; non-exhaustive by design."""
    if (name.startswith("catalog") or name.startswith("task.catalog") or
            name.startswith("task.v257_rail_refresh")):
        return "catalogue"
    if name.startswith(("report.", "task.report")):
        return "reporting_and_probes"
    if name.startswith(("loop.orch", "loop.c117", "task.expand")):
        return "orchestration_misc"
    if (name.startswith("air.sites") or name.startswith("air.hub_site") or
            "site" in name and ("rail" in name or "air" in name)):
        return "site_search"
    if "astar" in name or "path" in name:
        return "rail_astar"
    if name.startswith("build.") or name.startswith("task.build"):
        return "construction"
    if ("fleet" in name or "replace" in name or "renew" in name or "refill" in name
            or name.startswith("task.v252")):
        return "fleet"
    if name.startswith("loop.save") or "save" in name:
        return "save"
    if name.startswith("loop.sleep"):
        return "sleep"
    if name.startswith(("select.", "pub.select", "pub.filter", "projects.pass")):
        return "selection"
    if name.startswith(("regen.", "air.prepare", "air.new_pairs", "air.plans", "air.hub_discover",
                        "air.finalize", "railprep", "projects.post_regen")):
        return "candidate_generation"
    if name.startswith(("loop.events", "event.")):
        return "events"
    return "other_instrumented"


def read_checkpoints(path):
    dec = {}
    sampled = defaultdict(lambda: defaultdict(list))
    if not path.exists():
        return dec, sampled
    with path.open(encoding="utf-8") as stream:
        for raw in stream:
            try:
                row = json.loads(raw)
                arm, seed, rep = row["run"]
                year = int(row["date"][:4])
            except (ValueError, KeyError, IndexError, TypeError):
                continue
            if arm not in ARMS or rep != 0 or year not in YEARS:
                continue
            seed = int(seed)
            for field in ("money", "current_loan"):
                value = row.get(field)
                if isinstance(value, (int, float)):
                    sampled[(arm, year)][field].append(value)
            if row["date"][5:7] == "12":
                # Only the latest December snapshot of each seed/year.
                dec[(arm, seed, year)] = row
    return dec, sampled


def read_log(path):
    spans = {}
    children = Counter()
    events = Counter()
    v309 = defaultdict(Counter)
    stops = Counter()
    empty = Counter()
    payments = Counter()
    payments_count = Counter()
    outcomes = Counter()
    decisions = Counter()
    pass_counters = Counter()
    build_reasons = Counter()
    rail_attempt_cost = Counter()
    rail_attempt_quote = Counter()
    rail_attempt_paid_count = Counter()
    rail_attempt_unknown = Counter()
    rail_attempt_results = Counter()
    rail_built_lines = Counter()
    air_built_lines = Counter()
    air_build_quote = Counter()
    air_build_quote_records = Counter()
    air_fleet_decisions = Counter()
    air_fleet_added = Counter()
    vivier_counts = Counter()
    vivier_records = Counter()
    spend_na = 0
    topk_months = set()
    line_revenue = Counter()
    raw_year_coverage = set()
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LOG_RE.search(line)
            if not m:
                continue
            y, month, day, tag, payload = m.groups()
            y = int(y)
            if y not in YEARS:
                continue
            raw_year_coverage.add(y)
            fields = dict(FIELDS_RE.findall(payload))
            events[(y, tag)] += 1
            if tag == "SPAN":
                sid, par, op = (clean_int(fields.get(key)) for key in ("id", "par", "op"))
                if sid is not None and par is not None and op is not None and op >= 0:
                    spans[sid] = (par, y, fields.get("n", "unknown"), op)
            elif tag == "V309_IDLE":
                for key in ("loops", "useless", "useless_ops", "sleep_ops", "cash_below",
                            "cash_below_days", "stable_unfunded_loops", "stable_unfunded_ops",
                            "unfunded_cost_loops", "unknown_cost_loops", "blocks", "wait_days"):
                    v = numeric(fields.get(key))
                    if v is not None and v >= 0:
                        v309[y][key] += v
            elif tag == "C69_BOTTLENECK" and fields.get("phase") == "c75_pass":
                stops[(y, fields.get("stop", "unknown"))] += 1
            elif tag == "C69_BOTTLENECK" and fields.get("phase") == "vivier_year":
                ledger_year = clean_int(fields.get("year"))
                mode = fields.get("mode", "unknown")
                if ledger_year in YEARS and mode in ("air", "rail", "road", "water", "fleet"):
                    vivier_records[(ledger_year, mode)] += 1
                    for field, value in fields.items():
                        if field in ("examined", "produced", "after_topk", "to_select",
                                     "affordable", "selected") or field.startswith("rej_"):
                            n = clean_int(value)
                            if n is not None and n >= 0:
                                vivier_counts[(ledger_year, mode, field)] += n
            elif tag == "C63_INVEST" and fields.get("phase") == "empty_probe":
                empty[(y, fields.get("cause", "unknown"))] += 1
            elif tag == "ESTIM_PASS":
                topk_months.add((y, int(month)))
                for key in ("alternatives", "selected", "top_k"):
                    n = clean_int(fields.get(key))
                    if n is not None and n >= 0:
                        pass_counters[(y, key)] += n
            elif tag == "ESTIM_DECISION":
                decisions[(y, fields.get("mode", "unknown"),
                           fields.get("stage", "unknown"),
                           fields.get("reason", "unknown"))] += 1
            elif tag == "ESTIM_OUTCOME":
                outcomes[(y, fields.get("mode", "?"), fields.get("outcome", "?"),
                          fields.get("reason", "?"))] += 1
            elif tag in ("RAIL_ATTEMPT", "AIR_BUILD", "RAIL_BUILD"):
                build_reasons[(y, tag, fields.get("reason", "unknown"),
                               fields.get("ok", "unknown"))] += 1
                if tag == "RAIL_ATTEMPT":
                    reason = fields.get("reason", "unknown")
                    ok = fields.get("ok", "unknown")
                    rail_attempt_results[(y, ok, reason)] += 1
                    actual = numeric(fields.get("actual"))
                    quoted = numeric(fields.get("quote"))
                    if actual is None or actual < 0:
                        rail_attempt_unknown[y] += 1
                    else:
                        rail_attempt_cost[y] += actual
                        rail_attempt_paid_count[y] += 1
                    if quoted is not None and quoted >= 0:
                        rail_attempt_quote[y] += quoted
                elif tag == "RAIL_BUILD":
                    rail_built_lines[y] += 1
                elif tag == "AIR_BUILD":
                    air_built_lines[y] += 1
                    quote = numeric(fields.get("cost"))
                    if quote is not None and quote >= 0:
                        air_build_quote[y] += quote
                        air_build_quote_records[y] += 1
            elif tag == "AIR_FLEET":
                action = fields.get("action", "unknown")
                reason = fields.get("reason", "unspecified")
                air_fleet_decisions[(y, action, reason)] += 1
                if action == "grow":
                    n = clean_int(fields.get("added"))
                    if n is not None and n >= 0:
                        air_fleet_added[y] += n
            elif tag == "ESTIM_SPEND":
                v = numeric(fields.get("actual_paid"))
                if v is None or v < 0:
                    spend_na += 1
                else:
                    k = (y, fields.get("mode", "?"))
                    payments[k] += v
                    payments_count[k] += 1
            elif tag == "LINE_REVENUE":
                line_revenue[y] += 1
    for sid, (par, _year, _name, op) in spans.items():
        if par in spans and par != sid:
            children[par] += op
    ops_by_name = Counter()
    ops_by_year = defaultdict(Counter)
    root_op_by_year = Counter()
    negative_residuals = 0
    for sid, (par, year, name, op) in spans.items():
        if par == 0 or par not in spans:
            root_op_by_year[year] += op
        residual = op - children[sid]
        if residual < 0:
            negative_residuals += 1
            residual = 0
        ops_by_name[name] += residual
        ops_by_year[year][name] += residual
    return {"events": events, "v309": v309, "stops": stops, "empty": empty,
            "payments": payments, "payments_count": payments_count, "spend_na": spend_na,
            "outcomes": outcomes, "decisions": decisions, "pass_counters": pass_counters,
            "build_reasons": build_reasons,
            "rail_attempt_cost": rail_attempt_cost, "rail_attempt_quote": rail_attempt_quote,
            "rail_attempt_paid_count": rail_attempt_paid_count,
            "rail_attempt_unknown": rail_attempt_unknown,
            "rail_attempt_results": rail_attempt_results,
            "rail_built_lines": rail_built_lines, "air_built_lines": air_built_lines,
            "air_build_quote": air_build_quote,
            "air_build_quote_records": air_build_quote_records,
            "air_fleet_decisions": air_fleet_decisions,
            "air_fleet_added": air_fleet_added,
            "vivier_counts": vivier_counts, "vivier_records": vivier_records,
            "topk_months": topk_months, "line_revenue": line_revenue,
            "ops_by_name": ops_by_name, "ops_by_year": ops_by_year,
            "root_op_by_year": root_op_by_year,
            "negative_residuals": negative_residuals, "span_count": len(spans),
            "years": raw_year_coverage}


def summarise_campaign(campaign):
    base = ROOT / "results" / campaign
    result_path = Path(str(base) + ".json")
    if not result_path.is_file():
        return {"campaign": campaign, "status": "missing_result",
                "checkpoints_present": Path(str(base) + ".jsonl").exists()}
    result = json.loads(result_path.read_text(encoding="utf-8"))
    summary = {(r["arm"], int(r["seed"])): r for r in result.get("summary", [])
               if r.get("arm") in ARMS and r.get("repeat") == 0}
    dec, sampled = read_checkpoints(Path(str(base) + ".jsonl"))
    paired_seeds = sorted(set(s for arm, s in summary if arm == "OpexAI") &
                          set(s for arm, s in summary if arm == "AAAHogEx"))
    ok_seeds = [s for s in paired_seeds if all(summary[(a, s)].get("game_ok")
                 and summary[(a, s)].get("horizon_complete") for a in ARMS)]
    arms = {}
    for arm in ARMS:
        seeds = [s for a, s in summary if a == arm]
        d = [summary[(arm, s)] for s in seeds]
        by_year = {}
        for y in YEARS:
            recs = [dec[(arm, s, y)] for s in seeds if (arm, s, y) in dec]
            by_year[str(y)] = {k: stat(r.get(k) for r in recs) for k in (
                "profit_year", "money", "current_loan", "company_value", "income_last_year",
                "expenses_last_year", "n_vehicles", "n_stations")}
            by_year[str(y)]["cash_monthly"] = stat(sampled[(arm, y)]["money"])
            by_year[str(y)]["loan_monthly"] = stat(sampled[(arm, y)]["current_loan"])
            by_year[str(y)]["net_cash"] = stat(
                r["money"] - r["current_loan"] for r in recs
                if isinstance(r.get("money"), (float, int)) and
                isinstance(r.get("current_loan"), (float, int)))
            lines = [(rec.get("line_telemetry") or {}) for rec in recs]
            by_year[str(y)]["lines"] = stat(len(t.get("lines", [])) for t in lines if t.get("ok"))
            by_year[str(y)]["unresolved_line_vehicles"] = stat(
                len(t.get("unresolved_vehicles", [])) for t in lines if t.get("ok"))
            by_year[str(y)]["line_profit_observed_total_gbp"] = stat(
                sum(line["profit_this_year_gbp"] for line in t.get("lines", [])
                    if isinstance(line.get("profit_this_year_gbp"), (float, int)))
                for t in lines if t.get("ok") and any(
                    isinstance(line.get("profit_this_year_gbp"), (float, int))
                    for line in t.get("lines", [])))
            by_year[str(y)]["line_negative_count"] = stat(
                sum(line["profit_this_year_gbp"] < 0 for line in t.get("lines", [])
                    if isinstance(line.get("profit_this_year_gbp"), (float, int)))
                for t in lines if t.get("ok"))
            by_year[str(y)]["line_profit_observed_mean_gbp"] = stat(
                line["profit_this_year_gbp"] for t in lines if t.get("ok")
                for line in t.get("lines", [])
                if isinstance(line.get("profit_this_year_gbp"), (float, int)))
            by_year[str(y)]["stations_facility"] = {k: stat((r.get("stations_by_facility") or {}).get(k)
                for r in recs) for k in ("rail", "airport", "bus", "truck", "dock")}
            by_year[str(y)]["vehicles_mode"] = {k: stat((r.get("primary_vehicles_by_mode") or {}).get(k)
                for r in recs) for k in ("rail", "air", "road", "water")}
        arms[arm] = {"n": len(d), "valid": sum(r.get("game_ok") is True for r in d),
                     "annual": by_year, "final": {k: stat(r.get(k) for r in d) for k in (
                         "profit_year", "money", "current_loan", "company_value",
                         "n_stations", "n_vehicles")},
                     "script_errors": sum(len(r.get("script_errors") or []) for r in d)}
    def vals(arm, field):
        return [summary[(arm, s)].get(field) for s in ok_seeds]
    a, b = vals("OpexAI", "profit_year"), vals("AAAHogEx", "profit_year")
    pa = [v for v in a if isinstance(v, (int, float))]
    pb = [v for v in b if isinstance(v, (int, float))]
    comparisons = {
        "paired_complete": len(ok_seeds),
        "profit_o": stat(pa), "profit_aaa": stat(pb),
        "profit_ratio_of_means_pct": round(100 * mean(pa) / mean(pb), 3) if pa and pb and mean(pb) else None,
        "paired_profit_delta": stat(x - y for x, y in zip(a, b)
                                    if isinstance(x, (int, float)) and isinstance(y, (int, float))),
        "opex_wins_profit": sum(x > y for x, y in zip(a, b)
                                if isinstance(x, (int, float)) and isinstance(y, (int, float))),
    }
    counts = Counter()
    v309 = defaultdict(Counter)
    stops = Counter()
    empty = Counter()
    payments = Counter()
    payments_count = Counter()
    outcomes = Counter()
    decisions = Counter()
    pass_counters = Counter()
    build_reasons = Counter()
    rail_attempt_cost = Counter()
    rail_attempt_quote = Counter()
    rail_attempt_paid_count = Counter()
    rail_attempt_unknown = Counter()
    rail_attempt_results = Counter()
    rail_built_lines = Counter()
    air_built_lines = Counter()
    air_build_quote = Counter()
    air_build_quote_records = Counter()
    air_fleet_decisions = Counter()
    air_fleet_added = Counter()
    vivier_counts = Counter()
    vivier_records = Counter()
    ops = Counter()
    ops_by_year = defaultdict(Counter)
    root_ops = Counter()
    topk_months = Counter()
    logs_n = 0
    diagnostics = Counter()
    log_dir = Path(str(base) + "_engine")
    if log_dir.exists():
        paths = sorted(log_dir.glob("*.log")) + sorted(log_dir.glob("*.log.gz"))
        for path in paths:
            if not LOG_NAME_RE.match(path.name):
                continue
            logs_n += 1
            rec = read_log(path)
            for k, v in rec["events"].items(): counts[k] += v
            for k, v in rec["stops"].items(): stops[k] += v
            for k, v in rec["empty"].items(): empty[k] += v
            for k, v in rec["payments"].items(): payments[k] += v
            for k, v in rec["payments_count"].items(): payments_count[k] += v
            for k, v in rec["outcomes"].items(): outcomes[k] += v
            decisions.update(rec["decisions"])
            pass_counters.update(rec["pass_counters"])
            for k, v in rec["build_reasons"].items(): build_reasons[k] += v
            rail_attempt_cost.update(rec["rail_attempt_cost"])
            rail_attempt_quote.update(rec["rail_attempt_quote"])
            rail_attempt_paid_count.update(rec["rail_attempt_paid_count"])
            rail_attempt_unknown.update(rec["rail_attempt_unknown"])
            rail_attempt_results.update(rec["rail_attempt_results"])
            rail_built_lines.update(rec["rail_built_lines"])
            air_built_lines.update(rec["air_built_lines"])
            air_build_quote.update(rec["air_build_quote"])
            air_build_quote_records.update(rec["air_build_quote_records"])
            air_fleet_decisions.update(rec["air_fleet_decisions"])
            air_fleet_added.update(rec["air_fleet_added"])
            vivier_counts.update(rec["vivier_counts"])
            vivier_records.update(rec["vivier_records"])
            for k, v in rec["ops_by_name"].items(): ops[k] += v
            for y, c in rec["ops_by_year"].items(): ops_by_year[y].update(c)
            root_ops.update(rec["root_op_by_year"])
            for y, c in rec["v309"].items(): v309[y].update(c)
            for y, m in rec["topk_months"]: topk_months[y] += 1
            diagnostics["span_count"] += rec["span_count"]
            diagnostics["negative_span_residuals"] += rec["negative_residuals"]
            diagnostics["spend_unknown"] += rec["spend_na"]
    diagnostics["logs_parsed"] = logs_n
    categories = Counter()
    categories_year = defaultdict(Counter)
    for name, total in ops.items():
        categories[span_category(name)] += total
    for year, counter in ops_by_year.items():
        for name, value in counter.items():
            categories_year[year][span_category(name)] += value

    return {"campaign": campaign, "status": "complete" if len(ok_seeds) == 40 else "partial",
            "source_bundle": result.get("source_bundle_sha256"), "expected_games": 40,
            "reported_games": len(result.get("games") or []), "failed_runs": len(result.get("failed_runs") or []),
            "comparison": comparisons, "arms": arms,
            "telemetry": {
                "logs": logs_n, "events_by_year": {str(y): dict((tag, n) for (yr, tag), n in counts.items() if yr == y)
                                                 for y in YEARS},
                "span_root_opcodes_by_year": dict(sorted(root_ops.items())),
                "span_exclusive_opcodes": dict(ops.most_common(70)),
                "span_category_opcodes": dict(categories.most_common()),
                "span_categories_by_year": {str(y): dict(categories_year[y].most_common()) for y in YEARS},
                "span_exclusive_by_year": {str(y): dict(ops_by_year[y].most_common(30)) for y in YEARS},
                "v309_by_year": {str(y): dict(v309[y]) for y in YEARS},
                "c75_stops_by_year": {str(y): {reason: n for (yr, reason), n in stops.items() if yr == y}
                                       for y in YEARS},
                "empty_candidate_reasons": {str(y): {reason: n for (yr, reason), n in empty.items() if yr == y}
                                             for y in YEARS},
                "construction_paid_observed": {str(y): {mode: v for (yr, mode), v in payments.items() if yr == y}
                                               for y in YEARS},
                "construction_paid_records": {str(y): {mode: v for (yr, mode), v in payments_count.items() if yr == y}
                                               for y in YEARS},
                "rail_attempt_actual_by_year": dict(sorted(rail_attempt_cost.items())),
                "rail_attempt_quote_by_year": dict(sorted(rail_attempt_quote.items())),
                "rail_attempt_actual_records": dict(sorted(rail_attempt_paid_count.items())),
                "rail_attempt_unknown_records": dict(sorted(rail_attempt_unknown.items())),
                "rail_attempt_result_reasons": {str(y): [
                    {"ok": ok, "reason": reason, "n": n}
                    for (year, ok, reason), n in rail_attempt_results.items() if year == y]
                    for y in YEARS},
                "rail_build_events_by_year": dict(sorted(rail_built_lines.items())),
                "air_build_events_by_year": dict(sorted(air_built_lines.items())),
                "air_build_quotes_gbp_by_year": dict(sorted(air_build_quote.items())),
                "air_build_quotes_records": dict(sorted(air_build_quote_records.items())),
                "air_fleet_decisions_by_year": {str(y): [
                    {"action": action, "reason": reason, "n": n}
                    for (yr, action, reason), n in air_fleet_decisions.most_common() if yr == y]
                    for y in YEARS},
                "air_fleet_additions_by_year": dict(sorted(air_fleet_added.items())),
                "vivier_by_year": {str(y): {mode: {
                    "records": vivier_records[(y, mode)],
                    **{field: v for (yr, mo, field), v in vivier_counts.items()
                       if yr == y and mo == mode}}
                    for mode in ("rail", "road", "air", "water", "fleet")}
                    for y in YEARS},
                "estim_outcomes": [{"year": y, "mode": m, "outcome": o, "reason": r, "n": n}
                                   for (y, m, o, r), n in outcomes.most_common(100)],
                "estim_decision_by_stage": [{"year": y, "mode": m, "stage": stage,
                                            "reason": reason, "n": n}
                                           for (y, m, stage, reason), n in decisions.most_common()],
                "estim_pass_totals": {str(y): {key: pass_counters[(y, key)] for key in (
                    "alternatives", "selected", "top_k")} for y in YEARS},
                "build_reasons": [{"year": y, "tag": tag, "reason": reason, "ok": ok, "n": n}
                                  for (y, tag, reason, ok), n in build_reasons.most_common(100)],
                "estim_topk_months_per_year": dict(topk_months),
                "quality": dict(diagnostics)},
            "analysis_caveats": [
                "SPAN ops measure sampled VM work, not wall CPU; inclusive parents overlap children.",
                "ESTIM_SPEND/DECISION only instrumented for 1973-1975; first three years unobserved.",
                "Capital expense cannot be inferred from operating expenses or bank balance alone.",
                "Line telemetry reconstructs groups from vehicle orders, not necessarily built projects.",
                "Heavy probes affect VM opcode budgets; not an uninstrumented adoption gate."]}


def render_md(results):
    lines = ["# ESTIM-1 + sites AIR classés — bancs 40×5 instrumentés", "",
             "Configuration : 1970–1974, 256², 40 graines, AAAHogEx isolé dans les mêmes modes.",
             "`estim_unifie=31`, `air_site_ranked=1`, `air_site_funnel=1`, `probes=67247874`.",
             "Les sondes consomment elles-mêmes des opcodes : il s'agit de diagnostics et non de portes d'adoption.", "",
             "## Résultat terminal apparié (1974)", "",
             "| Mode | paires complètes | Profit Opex/an | AAA/an | Opex/AAA | victoires | cash Opex/AAA | lignes Opex/AAA | véhicules Opex/AAA | gares Opex/AAA |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    def fm(v):
        return "ND" if v is None else f"{v:,.0f}"
    for mode, r in results.items():
        if "arms" not in r:
            lines.append(f"| {mode} | en cours | — | — | — | — | — | — | — | — |")
            continue
        o, a = r["arms"]["OpexAI"], r["arms"]["AAAHogEx"]
        co = r["comparison"]
        lasto, lasta = o["annual"]["1974"], a["annual"]["1974"]
        pair = lambda key: f"{fm(lasto[key]['mean'])}/{fm(lasta[key]['mean'])}"
        lines.append(f"| {mode} | {co['paired_complete']}/40 | {fm(co['profit_o']['mean'])} | "
                     f"{fm(co['profit_aaa']['mean'])} | "
                     f"{co['profit_ratio_of_means_pct'] if co['profit_ratio_of_means_pct'] is not None else 'ND'} % | "
                     f"{co['opex_wins_profit']} | {pair('money')} | {pair('lines')} | "
                     f"{pair('n_vehicles')} | {pair('n_stations')} |")
    for mode, r in results.items():
        lines += ["", f"## {mode.upper()}", ""]
        if "arms" not in r:
            lines.append("Pas encore de résultat complet : " + r["status"])
            continue
        lines += ["| Année | Profits Opex/AAA | Caisse Opex/AAA | Prêt Opex/AAA | Lignes Opex/AAA | Aéroports Opex/AAA | Trains Opex/AAA |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        o, a = r["arms"]["OpexAI"], r["arms"]["AAAHogEx"]
        for y in YEARS:
            x, z = o["annual"][str(y)], a["annual"][str(y)]
            p = lambda k: f"{fm(x[k]['mean'])}/{fm(z[k]['mean'])}"
            lines.append(f"| {y} | {p('profit_year')} | {p('money')} | {p('current_loan')} | "
                         f"{p('lines')} | {fm(x['stations_facility']['airport']['mean'])}/"
                         f"{fm(z['stations_facility']['airport']['mean'])} | "
                         f"{fm(x['vehicles_mode']['rail']['mean'])}/{fm(z['vehicles_mode']['rail']['mean'])} |")
        t = r["telemetry"]
        lines += ["", "### Blocages et travail mesuré", "",
                  f"Journaux exploités : {t['logs']}/40 ; spans : {t['quality'].get('span_count',0):,} ; "
                  f"résidus négatifs de spans : {t['quality'].get('negative_span_residuals',0)}.", "",
                  "| Année | C75 arrêts (top) | Vivier vide (top) | V309 caisse insuffisante / tours | SPAN racines opcodes |",
                  "|---|---|---|---:|---:|"]
        for y in YEARS:
            ys = str(y)
            stop = t["c75_stops_by_year"].get(ys, {})
            empt = t["empty_candidate_reasons"].get(ys, {})
            top = lambda v: ", ".join(f"{k}:{n}" for k,n in sorted(v.items(),key=lambda x:-x[1])[:4]) or "ND"
            idle = t["v309_by_year"].get(ys, {})
            pct = (f"{100*idle['cash_below']/idle['loops']:.1f}%"
                   if idle.get('loops',0) and 'cash_below' in idle else "ND")
            lines.append(f"| {y} | {top(stop)} | {top(empt)} | {pct} | "
                         f"{fm(t['span_root_opcodes_by_year'].get(y, t['span_root_opcodes_by_year'].get(ys)))} |")
        lines += ["", "**Plus gros postes SPAN exclusifs (tous exercices, parent-enfants soustraits)** : "
                  + "; ".join(f"{k} {v:,.0f}" for k,v in list(t['span_exclusive_opcodes'].items())[:12]) + ".", "",
                  "**Répartition par sous-tâche (opcodes mesurés, catégories indicatives)** : "
                  + "; ".join(f"{k} {v:,.0f}" for k,v in t['span_category_opcodes'].items()) + ".", "",
                  "**Paiements physiques explicitement observés** (`ESTIM_SPEND`, fenêtre 1973–74 seulement) : "
                  + "; ".join(f"{year}: {value}" for year,value in t['construction_paid_observed'].items()) + ".", "",
                  "**Rail `RAIL_ATTEMPT.actual`** (comptabilité d'essai; y compris échecs partiels, "
                  "indépendant d'ESTIM_SPEND, ne pas additionner les deux) : "
                  + "; ".join(f"{y}: {fm(t['rail_attempt_actual_by_year'].get(y, t['rail_attempt_actual_by_year'].get(str(y), 0)))} £, "
                              f"{t['rail_attempt_unknown_records'].get(y, t['rail_attempt_unknown_records'].get(str(y), 0))} montants inconnus"
                              for y in YEARS) + ".", "",
                  "**AIR_BUILD devis initiaux** (non payés vérifiés ; ne pas additionner aux "
                  "ESTIM_SPEND ou aux charges d'exploitation) : "
                  + "; ".join(f"{y}: {fm(t['air_build_quotes_gbp_by_year'].get(y, t['air_build_quotes_gbp_by_year'].get(str(y), 0)))} £"
                              for y in YEARS) + ".", "",
                  "**AIR_FLEET refus les plus fréquents en 1974** (événements répétés, non lignes distinctes) : "
                  + "; ".join(f"{r['reason']}={r['n']}" for r in t['air_fleet_decisions_by_year']['1974']
                              if r['action'] == 'refuse') + ".", "",
                  "**Vivier ROAD 1970–73** (bilan annuel émis au début de l'année suivante, "
                  "sélections cumulées par passage, non projets uniques) : "
                  + "; ".join(f"{y}: examiné={t['vivier_by_year'][str(y)]['road'].get('examined', 'ND')}, "
                              f"produit={t['vivier_by_year'][str(y)]['road'].get('produced', 'ND')}, "
                              f"en tête de sélection={t['vivier_by_year'][str(y)]['road'].get('to_select', 'ND')}"
                              for y in range(1970, 1974)) + ".", "",
                  "**Dépenses d'exploitation comptabilisées** (valeur `expenses_last_year` signée) : "
                  + "; ".join(f"{y} Opex {fm(o['annual'][str(y)]['expenses_last_year']['mean'])} / "
                             f"AAA {fm(a['annual'][str(y)]['expenses_last_year']['mean'])}"
                             for y in YEARS) + ".", "",
                  "**Profit moyen des lignes observées en 1974**, Opex/AAA : "
                  f"{fm(o['annual']['1974']['line_profit_observed_mean_gbp']['mean'])}/"
                  f"{fm(a['annual']['1974']['line_profit_observed_mean_gbp']['mean'])} £ "
                  "(par ligne, distinct du profit annuel de la compagnie).", "",
                  "**Issues réelles ESTIM** (1973–74, hors trous et plafond de 60/mois) : "
                  + "; ".join(f"{v['year']}/{v['mode']}/{v['outcome']}/{v['reason']}={v['n']}"
                              for v in t['estim_outcomes'][:12]) + ".", "",
                  "**Premiers classements mensuels ESTIM** (1973–74, top-K par mode) : "
                  + "; ".join(f"{v['year']}/{v['mode']}/{v['stage']}/{v['reason']}={v['n']}"
                              for v in t['estim_decision_by_stage'][:16]) + "."]
    lines += ["", "## Précautions d'interprétation", "",
              "La ligne `ESTIM_SPEND` ne peut pas expliquer toute la dépense 1970–72 ; "
              "les dépenses d'exploitation (annuelles) ne comptent pas les constructions et achats de véhicules.",
              "Un compteur de blocage décrit un passage du planificateur, pas une occasion de profit perdue.",
              "La topologie des lignes est reconstruite depuis les ordres des véhicules ; "
              "les sans-ordre sont signalés sans estimation implicite.",
              "La sonde VPS `early_build_probe` n'existe pas dans cette révision locale ; "
              "C63, C69, V309, ESTIM et SPAN sont les sources exploitées ici.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suffix", default="20261027")
    parser.add_argument("--modes", nargs="+", choices=("air", "rail", "multi"),
                        default=("air", "rail", "multi"),
                        help="Modes a lire ; utiliser --modes rail pour diagnostiquer en cours de campagne")
    parser.add_argument("--out-json", default=None)
    parser.add_argument("--out-md", default=None)
    args = parser.parse_args()
    results = {mode: summarise_campaign(f"estim1_sites_diag_{mode}_40x5_{args.suffix}")
               for mode in args.modes}
    json_path = Path(args.out_json or ROOT / "results" / f"estim1_sites_diag_summary_{args.suffix}.json")
    md_path = Path(args.out_md or ROOT / "results" / f"estim1_sites_diag_summary_{args.suffix}.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_md(results), encoding="utf-8")
    for mode, r in results.items():
        print(mode, r["status"], r.get("comparison", {}).get("paired_complete", 0),
              r.get("comparison", {}).get("profit_ratio_of_means_pct"))
    print(json_path, md_path)


if __name__ == "__main__":
    main()
