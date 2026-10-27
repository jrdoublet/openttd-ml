#!/usr/bin/env python3
"""Diagnostic en lecture seule des choix ESTIM-1, années 1973 à 1975.

Exemple (depuis la racine du dépôt) :
  python -X utf8 sweeps/diag_estim1_decision_probe.py \
    --campaign estim1_dtrace_15v0_sixseeds_6y_20261027 \
    --out-json results/estim1_dtrace_decisions.json \
    --out-md results/estim1_dtrace_decisions.md

Chaque bras désigne un duel distinct OpexAI contre AAAHogEx. Les lineId sont
locaux à chaque partie. LINE_REVENUE year=Y observe l'année Y-1 ; la comparaison
se fait par graine, mode, année comptable et âge exact, sans identifier deux
lignes de bras différents comme une seule ligne.

La télémétrie et les sondes n'impliquent aucune modification d'OpenTTD.
Les comptes de tentatives et la somme de paid_accounting sont descriptifs :
pending, skipped et les débits de caisse ne prouvent pas un coût physique.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import json
import math
from pathlib import Path
import re
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
YEARS = (1973, 1974, 1975)
MODES = ("air", "rail", "fleet")
TAGS = {"ESTIM_PASS", "ESTIM_DECISION", "ESTIM_OUTCOME", "ESTIM_SPEND",
        "RAIL_ATTEMPT", "LINE_REVENUE", "AIR_BUILD", "RAIL_BUILD"}
LOG_NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$")
LOG_EVENT = re.compile(
    r"\[0\]\s+\[I\]\s+OPEX\s+"
    r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})\s+"
    r"(?P<tag>ESTIM_PASS|ESTIM_DECISION|ESTIM_OUTCOME|ESTIM_SPEND|RAIL_ATTEMPT|LINE_REVENUE|AIR_BUILD|RAIL_BUILD)\s+"
    r"(?P<fields>[^\r\n]*)"
)
INTEGER = re.compile(r"^[+-]?\d+$")
NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
NUMERIC = {
    "month", "budget", "k_dec", "alternatives", "selected", "top_k",
    "rank", "dist", "raw_r", "k_r", "r", "e", "a", "c_quote", "c_score",
    "p", "score", "finance", "cash", "available", "cash_before",
    "cash_after", "paid_accounting", "line", "age", "year", "vehs",
    "real_prof", "pred_prof", "real_rev", "pred_rev", "real_run",
    "pred_run", "planes", "trains", "cost", "profit", "actual_paid",
    "quote", "actual", "paid_cash_delta", "ok", "src", "dst",
}
# Explicit unknown sentinels: rank=-1 means "not selected", not missing.
SENTINEL = {
    "ESTIM_DECISION": {"dist", "raw_r", "r", "e", "a", "c_quote",
                       "c_score", "p", "score"},
    "ESTIM_OUTCOME": {"line", "paid_accounting"},
    "ESTIM_SPEND": {"actual_paid", "line"},
    "RAIL_ATTEMPT": {"actual", "quote"},
}


def campaign_paths(campaign: str) -> tuple[Path, Path, Path]:
    source = Path(campaign)
    if not source.is_absolute() and source.parent == Path("."):
        source = ROOT / "results" / source
    if source.suffix == ".json":
        source = source.with_suffix("")
    elif source.name.endswith("_engine"):
        source = source.with_name(source.name[:-7])
    return source.with_suffix(".json"), source.with_suffix(".jsonl"), Path(str(source) + "_engine")


def decode_fields(tag: str, source: str) -> tuple[dict, list[str], list[str]]:
    fields: dict = {}
    sentinels: list[str] = []
    problems: list[str] = []
    for token in source.split():
        if "=" not in token:
            problems.append("invalid_token:" + token)
            continue
        key, value = token.split("=", 1)
        if not key or key in fields:
            problems.append("duplicate_or_empty_key:" + key)
            continue
        if key not in NUMERIC:
            fields[key] = value
            continue
        if value == "-1" and key in SENTINEL.get(tag, set()):
            fields[key] = None
            sentinels.append(key)
        elif INTEGER.fullmatch(value):
            fields[key] = int(value)
        elif NUMBER.fullmatch(value):
            number = float(value)
            if math.isfinite(number):
                fields[key] = number
            else:
                fields[key] = None
                problems.append("non_finite:" + key)
        else:
            fields[key] = None
            problems.append("invalid_number:" + key)
    return fields, sentinels, problems


def parse_log(path: Path) -> dict:
    """Ne lit que les traces Opex (slot [0]) ; accepte .log et .log.gz."""
    result = {"path": str(path), "events": [], "invalid": [], "counts": {},
              "last_game_date": None}
    opener = gzip.open if path.suffix == ".gz" else open
    counts: Counter = Counter()
    with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line_no, raw in enumerate(stream, 1):
            match = LOG_EVENT.search(raw)
            if not match:
                continue
            tag = match["tag"]
            if tag not in TAGS:
                continue
            try:
                stamped = date(int(match["year"]), int(match["month"]), int(match["day"]))
            except ValueError:
                result["invalid"].append({"line": line_no, "problem": "invalid_date"})
                continue
            fields, na, errors = decode_fields(tag, match["fields"])
            if errors:
                result["invalid"].append({"line": line_no, "problem": errors})
            event = {"date": stamped.isoformat(), "tag": tag, "fields": fields,
                     "na_sentinel": na, "source_line": line_no}
            result["events"].append(event)
            counts[tag] += 1
            result["last_game_date"] = event["date"]
    _attach_costs(result["events"])
    result["counts"] = dict(counts)
    return result


def _attach_costs(events: list[dict]) -> None:
    """Joindre un coût une seule fois : id + line, puis proximité datée.

    Le constructeur peut publier ESTIM_SPEND la veille d'ESTIM_OUTCOME, après
    reprise/suspension de la tâche. Une dépense ne peut appartenir qu'à une
    tentative, les skipped/pending ne reçoivent aucune dépense de constructeur.
    Le fallback RAIL_ATTEMPT ne connaît pas le cargo (clé moins précise).
    """
    spends = defaultdict(list)
    attempts = defaultdict(list)
    for ev in events:
        f = ev["fields"]
        if ev["tag"] == "ESTIM_SPEND":
            spends[f.get("id")].append(ev)
        elif ev["tag"] == "RAIL_ATTEMPT":
            attempts[(f.get("src"), f.get("dst"), f.get("kind"))].append(ev)
    used_spend = set()
    used_attempt = set()
    for ev in events:
        if ev["tag"] != "ESTIM_OUTCOME":
            continue
        f = ev["fields"]
        outcome, mode = f.get("outcome"), f.get("mode")
        cash_before, cash_after = _num(f.get("cash_before")), _num(f.get("cash_after"))
        proxy = (cash_before - cash_after if cash_before is not None and
                 cash_after is not None else None)
        cost = {"source": "unknown", "amount_gbp": None, "builder_exact": False,
                "matched_date": None, "lag_days": None, "line_id_local": f.get("line"),
                "cash_delta_proxy_gbp": proxy,
                "reported_paid_cash_delta_gbp": _num(f.get("paid_cash_delta"))}
        ev["cost_observation"] = cost
        if outcome not in {"built", "rejected", "failed"}:
            continue
        event_day = date.fromisoformat(ev["date"])
        line = f.get("line")
        matches = []
        for candidate in spends.get(f.get("id"), []):
            if candidate["source_line"] in used_spend:
                continue
            c = candidate["fields"]
            if c.get("mode") != mode:
                continue
            # Fail-closed when both events report a valid local line ID.
            if isinstance(line, int) and isinstance(c.get("line"), int) and line != c["line"]:
                continue
            if outcome == "built" and c.get("ok") != 1:
                continue
            if outcome != "built" and c.get("ok") == 1:
                continue
            lag = (event_day - date.fromisoformat(candidate["date"])).days
            if 0 <= lag <= 7:
                matches.append((0 if line is not None and c.get("line") == line else 1,
                                lag, abs(ev["source_line"] - candidate["source_line"]),
                                candidate))
        matches.sort(key=lambda item: item[:3])
        if matches:
            picked = matches[0][3]
            used_spend.add(picked["source_line"])
            exact = _num(picked["fields"].get("actual_paid"))
            if exact is not None:
                cost.update({"source": "ESTIM_SPEND", "amount_gbp": exact,
                             "builder_exact": True, "matched_date": picked["date"],
                             "lag_days": matches[0][1]})
                continue
            cost.update({"spend_trace_unknown": True, "matched_date": picked["date"],
                         "lag_days": matches[0][1]})
        if mode == "rail":
            parts = (f.get("id") or "").split("|")
            if len(parts) == 5 and parts[0] == "rail":
                try:
                    rail_key = (int(parts[1]), int(parts[2]), parts[4])
                except ValueError:
                    rail_key = None
                candidates = []
                for candidate in attempts.get(rail_key, []):
                    if candidate["source_line"] in used_attempt:
                        continue
                    c = candidate["fields"]
                    if outcome == "built" and c.get("ok") != 1:
                        continue
                    if outcome != "built" and c.get("ok") == 1:
                        continue
                    lag = (event_day - date.fromisoformat(candidate["date"])).days
                    if 0 <= lag <= 7:
                        candidates.append((lag, abs(ev["source_line"] -
                                                    candidate["source_line"]), candidate))
                candidates.sort(key=lambda item: item[:2])
                if candidates:
                    picked = candidates[0][2]
                    used_attempt.add(picked["source_line"])
                    actual = _num(picked["fields"].get("actual"))
                    if actual is not None:
                        cost.update({"source": "RAIL_ATTEMPT", "amount_gbp": actual,
                                     "builder_exact": True, "matched_date": picked["date"],
                                     "lag_days": candidates[0][0]})
                        continue
        if mode == "air" and proxy is not None:
            cost.update({"source": "cash_delta_proxy", "amount_gbp": proxy,
                         "builder_exact": False, "matched_date": ev["date"],
                         "lag_days": 0})


def discover_logs(folder: Path) -> tuple[dict, list[str]]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Journaux moteur absents : {folder}")
    selected: dict = {}
    warnings: list[str] = []
    for path in sorted((*folder.glob("*.log"), *folder.glob("*.log.gz"))):
        matched = LOG_NAME.fullmatch(path.name)
        if matched is None:
            warnings.append(f"Nom de journal ignoré : {path.name}")
            continue
        identity = (matched["arm"], int(matched["seed"]), int(matched["repeat"]))
        old = selected.get(identity)
        if old:
            # Two representations of the same game are not separate samples.
            old_bytes = gzip.open(old, "rb").read() if old.suffix == ".gz" else old.read_bytes()
            new_bytes = gzip.open(path, "rb").read() if path.suffix == ".gz" else path.read_bytes()
            if old_bytes != new_bytes:
                raise ValueError(f"Copies contradictoires : {old} / {path}")
            if path.suffix == ".log":
                selected[identity] = path
        else:
            selected[identity] = path
    if not selected:
        raise ValueError(f"Aucun journal reconnu : {folder}")
    return selected, warnings


def _num(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _median(values):
    valid = [_num(v) for v in values]
    valid = [v for v in valid if v is not None]
    return median(valid) if valid else None


def _sum_or_none(values):
    valid = [v for v in values if _num(v) is not None]
    return sum(valid) if valid else None


def paid_stats(outcomes: list[dict]) -> dict:
    """La valeur -1 de paid_accounting est inconnue, zéro est observé."""
    observed = [e["fields"].get("paid_accounting") for e in outcomes]
    valid = [v for v in observed if _num(v) is not None]
    return {
        "known_events": len(valid), "zero_events": sum(v == 0 for v in valid),
        "positive_events": sum(v > 0 for v in valid),
        "na_or_missing_events": len(observed) - len(valid),
        "observed_sum": sum(valid) if valid else None,
        "meaning": "variation comptable d'événement ; pas une somme de coûts physiques",
    }


def cost_stats(outcomes: list[dict]) -> dict:
    """Séparer montants constructeur observés et approximations de caisse."""
    sources = Counter()
    by_mode = {}
    for mode in MODES:
        candidates = [ev["cost_observation"] for ev in outcomes
                      if ev["fields"].get("mode") == mode]
        exact = [ev["amount_gbp"] for ev in candidates if ev["builder_exact"] and
                 _num(ev["amount_gbp"]) is not None]
        proxy = [ev["amount_gbp"] for ev in candidates if
                 ev["source"] == "cash_delta_proxy" and
                 _num(ev["amount_gbp"]) is not None]
        for item in candidates:
            sources[item["source"]] += 1
        by_mode[mode] = {
            "outcomes": len(candidates),
            "builder_exact_events": len(exact),
            "builder_exact_total_gbp": sum(exact) if exact else None,
            "cash_proxy_events": len(proxy),
            "cash_proxy_total_gbp": sum(proxy) if proxy else None,
            "unknown_cost_events": sum(c["source"] == "unknown" for c in candidates),
        }
    return {"by_mode": by_mode, "by_source_events": dict(sources),
            "caution": "Montants exacts (ESTIM_SPEND ou RAIL_ATTEMPT) et proxy "
                       "de caisse ne doivent jamais être additionnés sans distinction."}


def _month_record(month: int, events: list[dict], within_horizon: bool) -> dict:
    passes = [e for e in events if e["tag"] == "ESTIM_PASS"]
    decisions = [e for e in events if e["tag"] == "ESTIM_DECISION"]
    outcomes = [e for e in events if e["tag"] == "ESTIM_OUTCOME"]
    spends = [e for e in events if e["tag"] == "ESTIM_SPEND"]
    rail_attempts = [e for e in events if e["tag"] == "RAIL_ATTEMPT"]
    top = {mode: sorted(
        [e for e in decisions if e["fields"].get("mode") == mode
         and re.fullmatch(r"mode_top_\d+", str(e["fields"].get("stage", "")))],
        key=lambda e: int(e["fields"]["stage"].rsplit("_", 1)[1]))
        for mode in MODES}
    selected = [e for e in decisions if e["fields"].get("stage") == "selected"]
    refusal = Counter()
    for e in outcomes:
        if e["fields"].get("outcome") in {"rejected", "skipped", "failed"}:
            refusal[str(e["fields"].get("reason", "missing_reason"))] += 1
    for e in decisions:
        if e["fields"].get("reason") in {"cash_selection", "excluded_or_topk"}:
            refusal["topk:" + e["fields"]["reason"]] += 1
    return {
        "month": month,
        "status": ("out_of_horizon" if not within_horizon else
                   "pass_observed" if passes else "no_ESTIM_PASS_trace"),
        "pass_count": len(passes), "pass_events": passes,
        "selected": selected, "top_k": top,
        "top_k_status": {mode: (
            "out_of_horizon" if not within_horizon else
            "no_ESTIM_PASS_trace" if not passes else
            "observed" if top[mode] else "no_mode_top_trace"
        ) for mode in MODES},
        "outcomes": outcomes,
        "spend_events": spends, "rail_attempts": rail_attempts,
        "outcomes_by_type": dict(Counter(e["fields"].get("outcome", "missing") for e in outcomes)),
        "refusal_reasons": dict(refusal),
        "cash_before_median": _median(e["fields"].get("cash_before") for e in outcomes),
        "cash_after_median": _median(e["fields"].get("cash_after") for e in outcomes),
        "cash_decision_median": _median(e["fields"].get("cash") for e in decisions),
        "paid_accounting": paid_stats(outcomes),
        "construction_costs": cost_stats(outcomes),
    }


def _year_record(months: list[dict]) -> dict:
    in_scope = [m for m in months if m["status"] != "out_of_horizon"]
    outcomes = [e for m in in_scope for e in m["outcomes"]]
    decisions = [e for m in in_scope for e in m["selected"]]
    counters = Counter(e["fields"].get("outcome", "missing") for e in outcomes)
    reasons = Counter()
    for m in in_scope:
        reasons.update(m["refusal_reasons"])
    return {
        "months_in_horizon": len(in_scope),
        "months_with_pass": sum(m["pass_count"] > 0 for m in in_scope),
        "months_without_pass_trace": [m["month"] for m in in_scope if not m["pass_count"]],
        "duplicate_pass_months": [m["month"] for m in in_scope if m["pass_count"] > 1],
        "selected_decisions": len(decisions),
        "top_k_by_mode": {mode: sum(len(m["top_k"][mode]) for m in in_scope) for mode in MODES},
        "top_k_months_by_mode": {
            mode: sum(bool(m["top_k"][mode]) for m in in_scope) for mode in MODES},
        "outcomes": dict(counters),
        "refusal_reasons": dict(reasons),
        "cash_before_median": _median(e["fields"].get("cash_before") for e in outcomes),
        "cash_after_median": _median(e["fields"].get("cash_after") for e in outcomes),
        "cash_decision_median": _median(e["fields"].get("cash") for e in decisions),
        "paid_accounting": paid_stats(outcomes),
        "construction_costs": cost_stats(outcomes),
        "spend_trace_events": sum(len(m["spend_events"]) for m in in_scope),
        "rail_attempt_trace_events": sum(len(m["rail_attempts"]) for m in in_scope),
    }


def _line_profits(events: list[dict]) -> tuple[list[dict], list[str]]:
    """Observe 1973-75 via LINE_REVENUE publié en 1974-76, âge >= 2."""
    built = {}
    warnings = []
    for ev in events:
        if ev["tag"] not in {"RAIL_BUILD", "AIR_BUILD"}:
            continue
        f = ev["fields"]
        mode = ev["tag"].split("_", 1)[0].lower()
        lid = f.get("line")
        if not isinstance(lid, int) or lid < 0:
            continue
        key = (mode, lid)
        if key in built:
            warnings.append(f"Construction multiple {mode} line={lid}")
            continue
        size = f.get("trains") if mode == "rail" else f.get("planes")
        built[key] = {"initial_vehicles": size if isinstance(size, int) and size > 0 else None,
                      "build_date": ev["date"], "cost_quote": f.get("cost")}
    rows = []
    seen = set()
    for ev in events:
        if ev["tag"] != "LINE_REVENUE":
            continue
        f = ev["fields"]
        published_year, age = f.get("year"), f.get("age")
        if not isinstance(published_year, int) or published_year - 1 not in YEARS:
            continue
        if not isinstance(age, int) or age < 2:
            continue
        mode, lid = f.get("mode"), f.get("line")
        if not isinstance(lid, int) or lid < 0 or mode not in ("air", "rail", "road", "water"):
            warnings.append(f"LINE_REVENUE identité invalide ligne {ev['source_line']}")
            continue
        key = (mode, lid, published_year)
        if key in seen:
            warnings.append(f"LINE_REVENUE dupliqué {key}")
            continue
        seen.add(key)
        build = built.get((mode, lid), {})
        n0 = build.get("initial_vehicles")
        n = f.get("vehs")
        actual = _num(f.get("real_prof"))
        normalized = (actual * n0 / n if actual is not None and
                      isinstance(n0, int) and isinstance(n, int) and n > 0 else None)
        rows.append({
            "accounting_year": published_year - 1, "published_year": published_year,
            "source_game_date": ev["date"], "mode": mode, "line_id_local": lid,
            "age": age, "cargo": f.get("cargo"),
            "real_profit_gbp": actual, "pred_profit_gbp": _num(f.get("pred_prof")),
            "real_revenue_gbp": _num(f.get("real_rev")),
            "real_running_gbp": _num(f.get("real_run")),
            "vehicles": n, "initial_vehicles": n0,
            "normalized_profit_initial_fleet_gbp": normalized,
            "initial_build_date": build.get("build_date"),
            "source_line": ev["source_line"],
        })
    return rows, warnings


def _line_aggregates(rows: list[dict]) -> dict:
    by = defaultdict(list)
    for row in rows:
        by[(row["accounting_year"], row["mode"], row["age"])].append(row)
    out = {}
    for (year, mode, age), samples in sorted(by.items()):
        valid = [x["real_profit_gbp"] for x in samples if x["real_profit_gbp"] is not None]
        scaled = [x["normalized_profit_initial_fleet_gbp"] for x in samples
                  if x["normalized_profit_initial_fleet_gbp"] is not None]
        out[f"{year}|{mode}|{age}"] = {
            "year": year, "mode": mode, "age": age, "line_years": len(samples),
            "real_profit_n": len(valid), "real_profit_sum_gbp": sum(valid) if valid else None,
            "real_profit_median_gbp": _median(valid),
            "normalized_n": len(scaled),
            "normalized_profit_median_gbp": _median(scaled),
        }
    return out


def _read_json(path: Path):
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _snapshots(path: Path, campaign_id: str, allowed: dict) -> dict:
    """Dernier cliché de décembre par graine/année, sans transformer NA en zéro."""
    chosen = {}
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            row = json.loads(raw)
            if row.get("campaign_id") != campaign_id:
                raise ValueError(f"{path}:{line_no}: campaign_id contradictoire")
            run = row.get("run")
            if not isinstance(run, list) or len(run) != 3 or run[0] != "OpexAI":
                continue
            arm = row.get("duel_policy_id")
            if arm not in allowed:
                continue
            stamp = str(row.get("date") or "")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
                continue
            year = int(stamp[:4])
            if year not in YEARS or stamp[5:7] != "12":
                continue
            key = (arm, run[1], run[2], year)
            if key in chosen and stamp <= chosen[key]["date"]:
                continue
            fleet = row.get("primary_vehicles_by_mode") or {}
            chosen[key] = {
                "date": stamp, "company_value": row.get("company_value"),
                "profit_year": row.get("profit_year"),
                "cash": row.get("money"), "loan": row.get("current_loan"),
                "air_vehicles": fleet.get("air"), "rail_vehicles": fleet.get("rail"),
            }
    return chosen


def analyze(campaign: str) -> dict:
    json_path, jsonl_path, engine = campaign_paths(campaign)
    result = _read_json(json_path)
    campaign_id = json_path.stem
    if result is not None and result.get("campaign_id") != campaign_id:
        raise ValueError("Identité JSON campagne incompatible")
    policies = result.get("policies", []) if result else []
    arms = {p["id"]: p.get("role") for p in policies if "id" in p}
    source_logs, discovery_warnings = discover_logs(engine)
    source_arms = {a for (a, _, _) in source_logs}
    if arms and not source_arms.issubset(arms):
        raise ValueError(f"Bras journaux non déclarés : {sorted(source_arms - set(arms))}")
    if not arms:
        arms = {a: ("reference" if a == "reference" else "variant") for a in source_arms}
    references = [a for a in arms if arms[a] == "reference"]
    variants = [a for a in arms if arms[a] == "variant"]
    if len(references) != 1 or len(variants) != 1:
        raise ValueError("Une référence et une variante sont nécessaires")
    ref, var = references[0], variants[0]
    seeds = sorted({(seed, repeat) for _, seed, repeat in source_logs} |
                   {(int(s), r) for s in (result.get("seeds", []) if result else [])
                    for r in range(int(result.get("repeats", 1)))})
    start = result.get("start_year") if result else None
    horizon = result.get("years") if result else None
    snapshots = _snapshots(jsonl_path, campaign_id, arms)
    games = {}
    warnings = list(discovery_warnings)
    for (arm, seed, repeat), path in sorted(source_logs.items()):
        parsed = parse_log(path)
        grouped = defaultdict(list)
        for ev in parsed["events"]:
            if ev["tag"] not in {"ESTIM_PASS", "ESTIM_DECISION", "ESTIM_OUTCOME",
                                 "ESTIM_SPEND", "RAIL_ATTEMPT"}:
                continue
            yr, mo = int(ev["date"][:4]), int(ev["date"][5:7])
            if yr in YEARS:
                grouped[(yr, mo)].append(ev)
        years = {}
        for year in YEARS:
            months = [_month_record(
                m, grouped[(year, m)],
                not (isinstance(start, int) and isinstance(horizon, int))
                or (start <= year < start + horizon))
                for m in range(1, 13)]
            years[str(year)] = {
                "months": months, "summary": _year_record(months),
                "december_snapshot": snapshots.get((arm, seed, repeat, year)),
            }
        line_rows, line_warnings = _line_profits(parsed["events"])
        warnings.extend(f"{path.name}: {issue}" for issue in line_warnings)
        games[(arm, seed, repeat)] = {
            "arm": arm, "seed": seed, "repeat": repeat, "log_path": str(path),
            "last_game_date": parsed["last_game_date"], "log_event_counts": parsed["counts"],
            "invalid_events": parsed["invalid"], "years": years,
            "line_profits": line_rows, "line_profit_by_year_mode_age": _line_aggregates(line_rows),
        }
    pairs = []
    for seed, repeat in seeds:
        by_arm = {arm: games.get((arm, seed, repeat)) for arm in (ref, var)}
        equal_age = []
        for year in YEARS:
            ref_rows = (by_arm[ref] or {}).get("line_profit_by_year_mode_age", {})
            var_rows = (by_arm[var] or {}).get("line_profit_by_year_mode_age", {})
            keys = sorted({k for k in set(ref_rows) | set(var_rows)
                           if k.startswith(str(year) + "|")})
            for key in keys:
                a, b = ref_rows.get(key), var_rows.get(key)
                ma = a["real_profit_median_gbp"] if a else None
                mb = b["real_profit_median_gbp"] if b else None
                equal_age.append({
                    "accounting_year": year, "mode": key.split("|")[1],
                    "age": int(key.split("|")[2]), "reference": a, "variant": b,
                    "delta_median_gbp": mb - ma if ma is not None and mb is not None else None,
                    "status": "both_observed" if ma is not None and mb is not None else
                              "no_equal_age_comparison",
                })
        annual = []
        for year in YEARS:
            a = (by_arm[ref] or {}).get("years", {}).get(str(year), {})
            b = (by_arm[var] or {}).get("years", {}).get(str(year), {})
            sa, sb = a.get("december_snapshot"), b.get("december_snapshot")
            va = sa.get("company_value") if sa else None
            vb = sb.get("company_value") if sb else None
            annual.append({
                "year": year, "reference_summary": a.get("summary"),
                "variant_summary": b.get("summary"),
                "reference_snapshot": sa, "variant_snapshot": sb,
                "delta_company_value_gbp": (vb - va if _num(va) is not None and
                                            _num(vb) is not None else None),
            })
        pairs.append({
            "seed": seed, "repeat": repeat, "reference_arm": ref, "variant_arm": var,
            "arms_present": {a: bool(by_arm[a]) for a in (ref, var)},
            "annual": annual, "equal_age_line_profit": equal_age,
        })
    return {
        "schema": "estim1_decisions_v1", "campaign_id": campaign_id,
        "campaign_json_present": result is not None,
        "campaign_jsonl_present": jsonl_path.is_file(),
        "campaign_complete": (result.get("policy_comparison", {}).get("comparison_complete")
                              if result else None),
        "source_bundle_sha256": result.get("source_bundle_sha256") if result else None,
        "reference": ref, "variant": var, "years": list(YEARS),
        "window_semantics": {
            "decision_years": "1973-1975 dates du jeu",
            "line_profit_year": "LINE_REVENUE year=Y mesure l'année comptable Y-1",
            "line_age": "âge >=2; comparaison par année, mode et âge exact, pas par lineId inter-parties",
            "missing_pass": "absence de ESTIM_PASS : aucun constat de sélection mensuelle; ne prouve pas zéro candidat",
            "missing_value": "null=absent/inconnu, 0=observé zéro, -1 sentinelle enregistrée dans na_sentinel",
            "paid_accounting": "delta comptable de tentative, ne signifie pas coût de ligne",
        },
        "warnings": warnings,
        "games": [games[key] for key in sorted(games)],
        "pairs": pairs,
    }


def _fmt(value, decimals=0):
    if _num(value) is None:
        return "—"
    if decimals:
        return f"{value:,.{decimals}f}".replace(",", " ")
    return f"{value:,.0f}".replace(",", " ")


def markdown(report: dict) -> str:
    content = [
        f"# ESTIM-1 — sondes de décisions {report['campaign_id']}",
        "",
        f"Référence : {report['reference']} ; variante : {report['variant']}. "
        f"Campagne complète : {report['campaign_complete']} ; "
        f"JSONL présent : {report['campaign_jsonl_present']}.",
        "",
        "Les absences de ESTIM_PASS indiquent une trace mensuelle manquante, "
        "pas une preuve de zéro projet. Le compteur topK compte des offres observées "
        "(dont les offres exclues), pas des constructions. "
        "Coût exact = ESTIM_SPEND actual_paid ou, en secours, RAIL_ATTEMPT actual ; "
        "proxy = différence de caisse pour AIR. Les deux postes sont séparés. "
        "paid_accounting est conservé comme compteur historique, parfois trompeur "
        "(pending, AITestMode). NA (-1) et 0 sont distincts.",
        "",
        "## Bilan annuel par graine et bras",
        "",
        "| Graine | Année | Bras | PASS mois/attendus | Top AIR/RAIL/FLEET | "
        "Selected | Built / rejected / skipped / pending | Refus (top 3) | "
        "Caisse avant méd. £ | Coût exact AIR/RAIL £ (n) | Proxy AIR £ (n) | "
        "Paid: connus / 0 / NA ; somme £ | Valeur déc. £ |",
        "|---:|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---|---:|",
    ]
    game_index = {(g["arm"], g["seed"], g["repeat"]): g for g in report["games"]}
    for pair in report["pairs"]:
        for annual in pair["annual"]:
            y = annual["year"]
            for arm in (report["reference"], report["variant"]):
                game = game_index.get((arm, pair["seed"], pair["repeat"]))
                yr = game["years"][str(y)] if game else None
                s = yr["summary"] if yr else None
                t = (s or {}).get("top_k_by_mode", {})
                oc = (s or {}).get("outcomes", {})
                reason = (s or {}).get("refusal_reasons", {})
                paid = (s or {}).get("paid_accounting", {})
                costs = (s or {}).get("construction_costs", {}).get("by_mode", {})
                air_cost = costs.get("air", {})
                rail_cost = costs.get("rail", {})
                shot = yr["december_snapshot"] if yr else None
                top_refusals = ", ".join(f"{k}:{v}" for k, v in
                                        Counter(reason).most_common(3)) or "—"
                content.append(
                    f"| {pair['seed']} r{pair['repeat']} | {y} | {arm} | "
                    f"{s['months_with_pass']}/{s['months_in_horizon']}" if s else
                    f"| {pair['seed']} r{pair['repeat']} | {y} | {arm} | —"
                )
                tail = (
                    f" | {t.get('air', 0)}/{t.get('rail', 0)}/{t.get('fleet', 0)}"
                    f" | {s['selected_decisions']} "
                    f"| {oc.get('built', 0)}/{oc.get('rejected', 0)}/"
                    f"{oc.get('skipped', 0)}/{oc.get('pending', 0)}"
                    f" | {top_refusals} | {_fmt(s['cash_before_median'])}"
                    f" | {_fmt(air_cost.get('builder_exact_total_gbp'))}"
                    f" ({air_cost.get('builder_exact_events', 0)})/"
                    f"{_fmt(rail_cost.get('builder_exact_total_gbp'))}"
                    f" ({rail_cost.get('builder_exact_events', 0)})"
                    f" | {_fmt(air_cost.get('cash_proxy_total_gbp'))}"
                    f" ({air_cost.get('cash_proxy_events', 0)})"
                    f" | {paid.get('known_events', 0)}/{paid.get('zero_events', 0)}/"
                    f"{paid.get('na_or_missing_events', 0)} ; {_fmt(paid.get('observed_sum'))}"
                    f" | {_fmt(shot.get('company_value') if shot else None)} |"
                    if s else " | — | — | — | — | — | — | — | — | — |"
                )
                content[-1] += tail
        content += [
            "",
            f"## Graine {pair['seed']} (répétition {pair['repeat']}) — mois 1973-75",
            "",
            "| Année-mois | Bras | PASS | Top AIR/RAIL/FLEET | Selected | "
            "Built/Refus/Skipped/Pending | Coût exact AIR/RAIL £ | "
            "Proxy AIR £ | Paid NA / zéro / somme connue £ |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
        for y in YEARS:
            for month in range(1, 13):
                for arm in (report["reference"], report["variant"]):
                    game = game_index.get((arm, pair["seed"], pair["repeat"]))
                    mm = game["years"][str(y)]["months"][month - 1] if game else None
                    if not mm:
                        content.append(f"| {y}-{month:02d} | {arm} | journal absent | — | — | — | — | — | — |")
                        continue
                    paid = mm["paid_accounting"]
                    outcomes = mm["outcomes_by_type"]
                    costs = mm["construction_costs"]["by_mode"]
                    flag = (str(mm["pass_count"]) if mm["pass_count"] else
                            "hors horizon" if mm["status"] == "out_of_horizon" else "trace absente")
                    content.append(
                        f"| {y}-{month:02d} | {arm} | {flag} | "
                        + "/".join(str(len(mm["top_k"][m])) for m in MODES)
                        + f" | {len(mm['selected'])} | {outcomes.get('built', 0)}/"
                        f"{outcomes.get('rejected', 0)}/{outcomes.get('skipped', 0)}/"
                        f"{outcomes.get('pending', 0)} | "
                        f"{_fmt(costs['air']['builder_exact_total_gbp'])}/"
                        f"{_fmt(costs['rail']['builder_exact_total_gbp'])} | "
                        f"{_fmt(costs['air']['cash_proxy_total_gbp'])} | "
                        f"{paid['na_or_missing_events']}/{paid['zero_events']}/"
                        f"{_fmt(paid['observed_sum'])} |")
        content += [
            "",
            f"## Graine {pair['seed']} — profits de lignes à âge égal",
            "",
            "| Année comptable | Mode | Âge exact | Lignes ref/var | "
            "Profit médian réel ref/var £ | Δ médiane £ | Profit médian ajusté flotte initiale ref/var £ |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
        for row in pair["equal_age_line_profit"]:
            a, b = row["reference"], row["variant"]
            content.append(
                f"| {row['accounting_year']} | {row['mode']} | {row['age']} | "
                f"{a['real_profit_n'] if a else '—'}/{b['real_profit_n'] if b else '—'} | "
                f"{_fmt(a['real_profit_median_gbp'] if a else None)}/"
                f"{_fmt(b['real_profit_median_gbp'] if b else None)} | "
                f"{_fmt(row['delta_median_gbp'])} | "
                f"{_fmt(a['normalized_profit_median_gbp'] if a else None)}/"
                f"{_fmt(b['normalized_profit_median_gbp'] if b else None)} |")
        if not pair["equal_age_line_profit"]:
            content.append("| — | — | — | — | — | — | — |")
    content += [
        "",
        "Les médianes d'âge comparent des *cohortes* de lignes par âge et mode. "
        "Les lignes construites peuvent différer entre les bras ; ces différences "
        "ne constituent pas des effets causaux par ligne. "
        "LINE_REVENUE publié en janvier 1976 serait nécessaire pour l'année "
        "comptable 1975, absente d'une simulation terminée en décembre 1975.",
        "",
    ]
    if report["warnings"]:
        content += ["## Alertes de lecture", ""]
        content += ["- " + w for w in report["warnings"]]
    return "\n".join(content) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, help="Identifiant, préfixe ou dossier _engine")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    if args.out_json.resolve() == args.out_md.resolve():
        parser.error("Les deux sorties doivent être distinctes")
    report = analyze(args.campaign)
    for output in (args.out_json, args.out_md):
        output.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    args.out_md.write_text(markdown(report), encoding="utf-8")
    print(f"Diagnostic : {len(report['games'])} journaux, {len(report['pairs'])} paires")
    print(f"Complétude : {report['campaign_complete']} ; avertissements : {len(report['warnings'])}")
    print(f"JSON : {args.out_json}")
    print(f"Markdown : {args.out_md}")


if __name__ == "__main__":
    main()
