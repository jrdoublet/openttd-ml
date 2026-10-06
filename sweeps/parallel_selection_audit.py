"""Audit passif C50/C70 : identité attestée != comparaison économique valide.

Exécution depuis la racine : python -m sweeps.parallel_selection_audit --out ...
Aucun import de lanceur (certains diagnostics modifient subprocess à l'import).
Les sorties refusent l'écrasement et restent dans results/parallel_selection_audit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from sweeps.analyse_c70_calibration import analyse as calibration_summary
from sweeps.harness import _LINE_RE, _OPEX_RE, parse_fields
from sweeps.line_profit_analysis import PROFIT_RAW_UNITS_PER_GBP, parse_sign

ROOT = Path(__file__).resolve().parents[1]
PHASES = {"line_calib", "line_profit", "project_built", "fleet_built"}
MISSING_FIELDS = {
    "election": ["decision_id", "attempt_id", "project_revision", "estimate_at_election",
                 "profitIsObserved", "calibration_factor_applied", "calibrated_profit",
                 "financeCapital", "effective_denominator", "K_dec", "priority", "full_candidate_set"],
    "identity": ["run/repeat/company provenance", "internal_line_id -> station/vehicle history",
                 "explicit action new/reinforcement/replacement/recovery"],
    "operation": ["commissioning_date", "vehicle membership intervals", "fleet changes during year",
                  "replacement/sale proceeds", "actual constructed quantity"],
    "accounting": ["actual airport/infrastructure costs", "consistent amortisation convention",
                   "marginal counterfactual for reinforcement/replacement"],
}


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def integer(value: Any) -> int | None:
    n = number(value)
    return int(n) if n is not None and n.is_integer() else None


def vehicle_profit_gbp(value: Any, unit: str) -> float | None:
    """Conversion explicite seulement ; les champs *_gbp ne sont jamais redivisés."""
    if unit not in {"GBP", "currency_fract"}:
        raise ValueError(f"Unknown profit unit: {unit}")
    n = number(value)
    return None if n is None else n / (PROFIT_RAW_UNITS_PER_GBP if unit == "currency_fract" else 1)


def annual_window(year: Any, age: Any, built_date: str | None = None) -> dict:
    """year C69 = exercice clos ; age = année du rapport - année de construction.

    Une première observation n'est jamais une date d'ouverture. Une année civile
    complète n'atteste pas un trafic stabilisé ni une composition de flotte constante.
    """
    y, a = integer(year), integer(age)
    result = {"profit_year": y, "start": None, "end_exclusive": None,
              "exposure": "unknown", "maturity": "unknown"}
    if y is None or not 1 <= y < 9999:
        return result
    result.update(start=f"{y:04d}-01-01", end_exclusive=f"{y + 1:04d}-01-01")
    if a is not None and a >= 2:
        result["exposure"] = "full_calendar_year_by_build_year"
        result["maturity"] = "first_full_year_ramp_possible" if a == 2 else "later_year_not_proven_stable"
    elif a == 1:
        result["exposure"] = "opening_year_date_unknown"
        result["maturity"] = "opening"
    if built_date:
        b = date.fromisoformat(built_date)
        if b.year > y:
            result.update(exposure="before_build", maturity="not_operating")
        elif b.year == y:
            result["exposure"] = "full_calendar_year" if b == date(y, 1, 1) else "partial_opening"
            result["maturity"] = "opening"
        elif b.year < y:
            result["exposure"] = "full_calendar_year"
    return result


def action_category(event: dict) -> str:
    # Explicit replacement/reinforcement requires a producer which actually says so.
    if event.get("action") in {"new_line", "reinforcement", "replacement", "recovery"}:
        return event["action"]
    if event.get("phase") == "project_built":
        return "fleet_action_unresolved" if event.get("mode") == "fleet" else "new_line_reported"
    return "unknown"


def log_events(text: str, segment: str):
    """Réutilise les regex du collecteur, en conservant date et compagnie perdues
    par parse_opex_decisions. Les champs sont décodés par le helper partagé."""
    for lineno, line in enumerate(text.splitlines(), 1):
        envelope = _LINE_RE.search(line)
        if not envelope:
            continue
        company, level, message = envelope.groups()
        match = _OPEX_RE.match(message.strip())
        if not match:
            continue
        y, m, d, kind, rest = match.groups()
        fields = parse_fields(rest)
        if fields.get("phase") not in PHASES and kind != "PORTFOLIO_RANK":
            continue
        if kind not in {"C69_BOTTLENECK", "C50_CHRONO", "PORTFOLIO_RANK"}:
            continue
        yield dict(fields, _kind=kind, _company=int(company), _level=level,
                   _date=date(int(y), int(m), int(d)).isoformat(),
                   _segment=segment, _locator=f"{segment}:L{lineno}")


def collect(data: Any, pointer: str = "$", segment: str = "$",
            inventory: Counter | None = None):
    """Accepte JSON/JSONL existants, sans inventer de métadonnées héritées.
    Les phases Save/Load et les champs de sortie moteur restent cloisonnés.
    """
    if inventory is None:
        inventory = Counter()
    if isinstance(data, dict):
        segment = data.get("_segment", segment)
        if data.get("phase") in PHASES:
            yield dict(data, _segment=segment, _locator=pointer)
        if "profit_year" in data and "profit_year_coverage" in data:
            inventory["company_profit_records"] += 1
        if "line_key_local" in data:
            inventory["station_key_line_records"] += 1
        for key, value in data.items():
            child = f"{pointer}/{key}"
            if key == "openttd_output_raw" and isinstance(value, str):
                yield from log_events(value, child)
            elif isinstance(value, (dict, list)):
                # Dictionaries below the root can be phases or independent runs.
                # Keep event arrays together, but never join across containers.
                child_scope = child if isinstance(value, dict) else segment
                yield from collect(value, child, child_scope, inventory)
            elif isinstance(value, str) and parse_sign(value) is not None:
                inventory["parsed_sign_strings_no_owner_binding"] += 1
    elif isinstance(data, list):
        for index, value in enumerate(data):
            child = f"{pointer}/{index}"
            scope = segment if isinstance(value, dict) and value.get("phase") in PHASES else child
            yield from collect(value, child, scope, inventory)


def identity(event: dict) -> tuple | None:
    """Cross-event key. Company and run scope must be explicit, never inferred
    from a seed, city pair or a nearby log line. Each file is handled separately."""
    lid = integer(event.get("line"))
    if lid is None or lid < 0 or event.get("_company") is None:
        return None
    return (event.get("_segment"), event.get("_company"), event.get("seed"),
            event.get("repeat"), event.get("mode"), lid)


def audit_events(events: list[dict]) -> dict:
    counts = Counter(e.get("phase", e.get("_kind", "unknown")) for e in events)
    builds = defaultdict(list)
    for e in events:
        key = identity(e)
        if e.get("phase") == "project_built" and key is not None:
            builds[key].append(e)

    # Duplicated line-years must not overweight recurring observations. Conflicts
    # are excluded altogether; all raw events remain in the hashed source file.
    slots = defaultdict(list)
    rejected = Counter()
    for e in events:
        if e.get("phase") != "line_calib":
            continue
        lid, y = integer(e.get("line")), integer(e.get("year"))
        if lid is None or lid < 0 or y is None or not 1 <= y < 9999 or not e.get("mode"):
            rejected["missing_or_invalid_line_identity_or_year"] += 1
            continue
        if e.get("_company") is None and e.get("seed") is None:
            rejected["missing_run_scope"] += 1
            continue
        try:
            report_year = date.fromisoformat(e["_date"]).year if e.get("_date") else None
        except (TypeError, ValueError):
            rejected["invalid_report_date"] += 1
            continue
        log_year = integer(e.get("_log_year"))
        if any(v is not None and v != y + 1 for v in (report_year, log_year)):
            rejected["inconsistent_report_year"] += 1
            continue
        # A C69 row binds its own prediction and observation even if the exported
        # JSONL lost company; it is NOT allowed to join any other source/event.
        key = (e.get("_segment"), e.get("_company"), e.get("seed"),
               e.get("repeat"), e["mode"], lid, y)
        slots[key].append(e)

    pairs, groups = [], defaultdict(list)
    duplicates = conflicts = 0
    relevant = ("age", "pred_p", "real_p", "pred_r", "real_r", "pred_run", "pred_amort", "trains0", "vehs")
    for key, rows in slots.items():
        signatures = {tuple(number(r.get(f)) for f in relevant) for r in rows}
        if len(signatures) != 1:
            conflicts += 1
            continue
        duplicates += len(rows) - 1
        e = min(rows, key=lambda r: (r.get("_date") is None, r.get("_date") or "", r["_locator"]))
        pred, real = number(e.get("pred_p")), vehicle_profit_gbp(e.get("real_p"), "GBP")
        if pred is None or real is None:
            rejected["missing_or_invalid_profit"] += 1
            continue
        y, age = integer(e.get("year")), integer(e.get("age"))
        candidates = builds.get(identity(e), []) if identity(e) is not None else []
        # More than one same-line build is ambiguous; never pick nearest by date.
        build = candidates[0] if len(candidates) == 1 else None
        if build and (not build.get("_date") or not e.get("_date") or build["_date"] >= e["_date"]):
            build = None
        if build and age is not None and age != y + 1 - date.fromisoformat(build["_date"]).year:
            build = None
        window = annual_window(y, age, build.get("_date") if build else None)
        n0, n = integer(e.get("trains0")), integer(e.get("vehs"))
        amort = number(e.get("pred_amort"))
        proxy_ok = (age is not None and age >= 2 and pred > 0 and amort is not None
                    and n0 is not None and n0 > 0 and n is not None and n > 0)
        pair = {
            "identity": dict(segment=key[0], company=key[1], seed=key[2], repeat=key[3],
                             mode=key[4], line_id=key[5], profit_year=key[6]),
            "source_locator": e["_locator"], "report_date": e.get("_date"),
            "all_source_locators": sorted({r["_locator"] for r in rows}),
            "all_report_dates": sorted({r["_date"] for r in rows if r.get("_date")}),
            "identity_evidence": "same_line_calib_record",
            "category": action_category(build) if build else "unknown",
            "window": window, "predicted_net_gbp_per_year": pred,
            "observed_vehicle_profit_gbp": real, "predicted_amort_gbp_per_year": amort,
            "initial_vehicles": n0, "current_vehicles": n,
            "prediction_reference_status": "initial_fleet_missing_or_zero" if n0 is None or n0 <= 0 else "declared",
            "same_vehicle_count_not_composition": n0 == n if n0 is not None and n is not None else None,
            "build_binding": ({"locator": build["_locator"], "date": build["_date"],
                               "rank": integer(build.get("rank")),
                               "reported_project_profit_gbp_per_year": number(build.get("profit")),
                               "reported_capital_gbp": number(build.get("cost"))} if build else None),
            "calibration_proxy_eligible": proxy_ok,
            "election_bias_gbp_per_year": None,
            "not_comparable_reasons": ["no_immutable_election_estimate", "vehicle_vs_net_accounting",
                                       "no_vehicle_membership_history"],
        }
        pairs.append(pair)
        if proxy_ok:
            # Existing C70 convention, not duplicated here. Namespace seed prevents
            # its (seed,mode,line) reducer merging companies/phases/repetitions.
            row = dict(e, seed=key[:4], line=key[5], age=age, year=y,
                       pred_p=pred, real_p=real, pred_amort=amort, trains0=n0, vehs=n)
            groups[key[:2]].append(row)

    proxies = [{"segment": scope[0], "company": scope[1],
                "summary": calibration_summary(rows)} for scope, rows in groups.items()]
    bias = {}
    for category in ("new_line_reported", "reinforcement", "replacement", "fleet_action_unresolved", "unknown"):
        selected = [p for p in pairs if p["category"] == category]
        bias[category] = {"identity_pairs": len(selected), "comparable_election_pairs": 0,
                          "mean_bias_gbp_per_year": None, "median_bias_gbp_per_year": None}
    return {"event_counts": dict(counts), "rejected": dict(rejected),
            "duplicate_line_year_rows": duplicates, "conflicting_line_years": conflicts,
            "identity_pairs": len(pairs), "build_bindings": sum(p["build_binding"] is not None for p in pairs),
            "windows": dict(Counter(p["window"]["exposure"] for p in pairs)),
            "project_actions": dict(Counter(action_category(e) for e in events if e.get("phase") == "project_built")),
            "bias_by_category": bias, "calibration_proxy_not_election_bias": proxies,
            "pairs": pairs}


def audit_file(path: Path) -> dict:
    result = {"source": str(path), "status": "missing", "sha256": None}
    if not path.is_file():
        return result
    content = path.read_bytes()
    result.update(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
    inventory = Counter()
    events = []
    try:
        text = content.decode("utf-8-sig")
        if path.suffix == ".log":
            events = list(log_events(text, "$"))
        elif path.suffix == ".jsonl":
            for lineno, line in enumerate(text.splitlines(), 1):
                if line.strip():
                    events.extend(collect(json.loads(line), f"L{lineno}", inventory=inventory))
        else:
            events = list(collect(json.loads(text), inventory=inventory))
    except (UnicodeError, ValueError) as exc:
        # Never silently keep a favorable prefix of a corrupt input.
        result.update(status="unreadable", error=str(exc))
        return result
    result.update(status="read", inventory=dict(inventory), audit=audit_events(events),
                  performance_provenance="not_qualified_by_this_audit")
    return result


def default_inputs(root: Path) -> list[Path]:
    results = root / "results"
    paths = set(results.glob("*20260930*.json")) | set(results.glob("*20260930*.jsonl"))
    paths.update(results.glob("*20260930*.artifacts/*.log"))
    paths.update(results.glob("c70_calib*raw*.jsonl"))
    paths.update(results / n for n in ("diag_c50_chronology_probe_6y_5seeds.json",
                 "diag_c70_calib_10y_20seeds.json", "diag_c70_calib_on_10y_20seeds.json",
                 "lineprofit_default_5x6_20260926.json", "lineprofit_default_5x6_20260926.jsonl"))
    return sorted(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / "results" / "parallel_selection_audit"):
        parser.error("Output must be inside results/parallel_selection_audit")
    if out.exists():
        parser.error("Refusing to overwrite an existing artifact")
    sources = [audit_file(p.resolve()) for p in sorted(set(args.inputs or default_inputs(ROOT)))]
    report = {"schema_version": 1, "scope": "passive audit; no games; per-source, not pooled",
              "analysis_source_sha256": {
                  name: hashlib.sha256((ROOT / "sweeps" / name).read_bytes()).hexdigest()
                  for name in ("parallel_selection_audit.py", "test_parallel_selection_audit.py",
                               "harness.py", "line_profit_analysis.py", "analyse_c70_calibration.py")},
              "units": {"prediction": "GBP/year net of predicted amortisation",
                        "observation": "GBP for previous calendar year; vehicle profit",
                        "calibration_proxy": "(vehicle profit * initial/current fleet - predicted amortisation) / predicted net"},
              "missing_fields": MISSING_FIELDS, "sources": sources,
              "coverage": dict(Counter(s["status"] for s in sources)),
              "verdict": "no_comparable_election_bias_measurement"}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(out), "coverage": report["coverage"], "verdict": report["verdict"]}))


if __name__ == "__main__":
    main()