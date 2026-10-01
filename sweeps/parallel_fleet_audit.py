"""Audit AIR hors ligne : événements de renfort != rendement marginal causal.

Usage depuis la racine : python -B -m sweeps.parallel_fleet_audit artefact.json
JSON/JSONL lus seulement ; résultat sur stdout, aucun lanceur ni fichier de sortie.
Chaque journal reste isolé (campagne, phase Save/Load, checkpoint, compagnie).
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path

from sweeps.game_health import parse_script_errors
from sweeps.harness import _LINE_RE, _OPEX_RE, parse_fields

METADATA = ("seed", "run", "bench_run", "arm", "bench_arm", "policy_id", "repeat",
            "company_id", "date", "status", "health", "config", "starting_year",
            "years_a", "years_b", "reloaded_savegame", "phantom_company_confound")
SERVICE_GAPS = ("departure_load", "completed_legs", "waiting_time_days",
                "airport_occupation", "residual_demand")


def number(value):
    """Absence, sentinelle non numérique et valeur non finie restent inconnues."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def integer(value):
    value = number(value)
    return int(value) if value is not None and value.is_integer() else None


def count(value):
    value = integer(value)
    return value if value is not None and value >= 0 else None


def events_from_log(text):
    """Conserve enveloppe, date et champs bruts des collecteurs partagés.

    Pas de parse_opex_decisions : il retire date et compagnie. Un log dépouillé
    sans enveloppe est inventorié mais ne peut pas être joint à une autre ligne.
    """
    events, rejected = [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        envelope = _LINE_RE.search(raw)
        company, level, message = envelope.groups() if envelope else (None, None, raw)
        match = _OPEX_RE.match(message.strip())
        if not match:
            continue
        y, m, d, tag, rest = match.groups()
        fields = parse_fields(rest)
        if tag != "FLEET_PROJECT" and not (tag == "C50_CHRONO" and fields.get("phase")
                in {"fleet_built", "project_built", "line_profit"}):
            continue
        try:
            game_date = date(int(y), int(m), int(d)).isoformat()
        except ValueError:
            rejected.append({"log_line": lineno, "reason": "invalid_date", "raw": raw})
            continue
        events.append({"tag": tag, "date": game_date, "raw_date": f"{y}-{m}-{d}",
                       "company": integer(company), "level": level,
                       "line": integer(fields.get("line")), "fields": fields,
                       "log_line": lineno, "raw": raw})
    return events, rejected


def streams(payload, pointer="$", inherited=None):
    """Pas de fusion entre journaux cumulés ni entre phases de rechargement.

    Un alias nettoyé et son raw dans le même objet ne sont pas deux journaux.
    Les schémas sans stdout ne sont pas convertis en absence de renforts.
    """
    if isinstance(payload, dict):
        metadata = dict(inherited or {})
        metadata.update({k: payload[k] for k in METADATA if k in payload})
        output_key = next((k for k in ("openttd_output_raw", "openttd_output")
                           if isinstance(payload.get(k), str) and payload[k]), None)
        if output_key:
            yield pointer + "/" + output_key, payload[output_key], metadata
        for key, value in payload.items():
            if isinstance(value, (dict, list)) and key not in METADATA:
                yield from streams(value, pointer + "/" + key, metadata)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            yield from streams(item, f"{pointer}/{index}", inherited)


def same_line(a, b):
    return (a["company"] is not None and a["line"] is not None
            and a["line"] >= 0 and a["company"] == b["company"] and a["line"] == b["line"])


def annual_observation(events, purchase, year):
    candidates = [e for e in events if same_line(e, purchase)
                  and e["tag"] == "C50_CHRONO" and e["fields"].get("phase") == "line_profit"
                  and e["fields"].get("mode") == "air"
                  and integer(e["fields"].get("profit_year")) == year]
    # Identical repeated annual reports are one observation, not independent samples.
    unique = {json.dumps(e["fields"], sort_keys=True): e for e in candidates}
    if len(unique) != 1:
        return {"year": year, "status": "missing" if not unique else "conflicting_reports",
                "report_count": len(candidates), "data": None}
    event = next(iter(unique.values()))
    fields = event["fields"]
    age = integer(fields.get("age"))
    full = age is not None and age >= 2
    consistent = (integer(fields.get("year")) == year + 1
                  and int(event["date"][:4]) == year + 1)
    return {"year": year, "status": ("full_by_line_age" if full else "partial_or_unknown_age")
            if consistent else "inconsistent_year", "report_count": len(candidates),
            "data": {"date": event["date"], "log_line": event["log_line"], "fields": fields,
                     "profit_gbp": number(fields.get("profit")),
                     "revenue_proxy_gbp": number(fields.get("rev")),
                     "running_cost_proxy_gbp": number(fields.get("run_cost")),
                     "vehicles_at_report": count(fields.get("vehs"))}}


def audit_purchase(purchase, events):
    f = purchase["fields"]
    year = int(purchase["date"][:4])
    added, want, total = (count(f.get(k)) for k in ("added", "want", "total"))
    decisions = [e for e in events if same_line(e, purchase) and e["date"] == purchase["date"]
                 and e["tag"] == "FLEET_PROJECT" and e["fields"].get("action") == "grow"]
    same_day = [e for e in events if same_line(e, purchase) and e["date"] == purchase["date"]
                and e["tag"] == "C50_CHRONO" and e["fields"].get("phase") == "fleet_built"]
    decision = decisions[0] if len(decisions) == len(same_day) == 1 else None
    if decision and (count(decision["fields"].get("added")) != added
                     or count(decision["fields"].get("want")) != want):
        decision = None
    price = number(decision["fields"].get("price")) if decision else None
    if price is not None and price <= 0:
        price = None
    before = annual_observation(events, purchase, year - 1)
    after = annual_observation(events, purchase, year + 1)
    other_growth = [e for e in events if same_line(e, purchase) and e is not purchase
                    and e["tag"] == "C50_CHRONO" and e["fields"].get("phase") == "fleet_built"
                    and year - 1 <= int(e["date"][:4]) <= year + 1]
    blockers = []
    if purchase["company"] is None or purchase["line"] is None or purchase["line"] < 0:
        blockers.append("missing_identity")
    if added is None or added <= 0:
        blockers.append("not_confirmed_growth")
    if total is None or added is None or total < added:
        blockers.append("invalid_or_missing_inventory")
    if before["status"] != "full_by_line_age":
        blockers.append("no_full_pre_year")
    if before["data"] and before["data"]["date"] >= purchase["date"]:
        blockers.append("baseline_report_not_before_purchase")
    if after["status"] != "full_by_line_age":
        blockers.append("no_full_post_year")
    if other_growth:
        blockers.append("other_fleet_events_in_window")
    for observation, expected in ((before, total - added if total is not None and added is not None else None),
                                  (after, total)):
        if observation["data"] and observation["data"]["vehicles_at_report"] != expected:
            blockers.append("fleet_composition_not_reconciled")
    delta_profit = delta_revenue = None
    if not blockers:
        b, a = before["data"], after["data"]
        if all(v is not None for v in (a["profit_gbp"], b["profit_gbp"])):
            delta_profit = a["profit_gbp"] - b["profit_gbp"]
        if all(v is not None for v in (a["revenue_proxy_gbp"], b["revenue_proxy_gbp"])):
            delta_revenue = a["revenue_proxy_gbp"] - b["revenue_proxy_gbp"]
    signal = "insufficient_observations"
    if delta_profit is not None and delta_revenue is not None:
        signal = ("positive_before_after_signal" if delta_profit > 0 and delta_revenue > 0
                  else "capital_at_risk_signal")
    return {"date": purchase["date"], "company": purchase["company"], "line": purchase["line"],
            "log_line": purchase["log_line"], "fields": f, "added": added, "total": total,
            "want_fitted": want, "original_want": None,
            "execution_partial": added < want if added is not None and want is not None else None,
            "r1_budget_fit_exposed": None,
            "unit_price_estimate_gbp": price,
            "purchase_capital_estimate_gbp": price * added if price is not None and added is not None and added > 0 else None,
            "actual_purchase_cost_gbp": None,
            "decision_log_line": decision["log_line"] if decision else None,
            "predicted_profit_fitted_gbp_per_year": number(decision["fields"].get("profit")) if decision else None,
            "before": before, "after": after, "blockers": sorted(set(blockers)),
            "delta_profit_gbp_per_year": delta_profit,
            "delta_revenue_proxy_gbp_per_year": delta_revenue,
            "service_measurements": {key: None for key in SERVICE_GAPS},
            "signal": signal, "economic_verdict": "not_identified_no_counterfactual"}


def audit_stream(text, pointer, metadata):
    events, rejected = events_from_log(text)
    purchases = [e for e in events if e["tag"] == "C50_CHRONO"
                 and e["fields"].get("phase") == "fleet_built" and e["fields"].get("mode") == "air"]
    rows = [audit_purchase(e, events) for e in purchases]
    owners = {e["company"] for e in events if e["company"] is not None}
    # Do not infer OpexAI's slot from a shared fatal marker.
    slots = {c: {"company_id": c, "name": f"company:{c}"} for c in owners}
    health = parse_script_errors(text, slots)
    for row in rows:
        if (health["engine_marker"] or health["unattributed"]
                or any(e["company_id"] == row["company"] for e in health["attributed"])):
            row["blockers"].append("log_health_error")
            row["signal"] = "insufficient_observations"
            row["delta_profit_gbp_per_year"] = None
            row["delta_revenue_proxy_gbp_per_year"] = None
    known_added = [r["added"] for r in rows if r["added"] is not None]
    return {"pointer": pointer, "metadata": metadata, "health_log_scan": health,
            "health_scope": "log_markers_only_not_horizon_validation",
            "observed_event_count": len(events), "rejected_events": rejected,
            "coverage": {"air_fleet_event_records": len(rows),
                         "added_quantity_known_records": sum(r["added"] is not None for r in rows),
                         "added_quantity_sum_known": sum(known_added) if known_added else None,
                         "estimated_capital_records": sum(r["purchase_capital_estimate_gbp"] is not None for r in rows),
                         "full_before_after_records": sum(not r["blockers"] for r in rows),
                         "signals": dict(Counter(r["signal"] for r in rows))},
            "purchases": rows,
            "events": events,
            "caveats": ["No event is not proof of no purchase; probe coverage is unknown.",
                        "Streams may overlap; never sum purchases across streams.",
                        "C50 project_built mode=fleet is not a second purchase.",
                        "C50 added=0 can hide a replacement; crashes and sales are not reconciled.",
                        "Revenue is profit plus running-cost proxy, not receipts measured independently.",
                        "Before/after signals do not control demand, competition, engine or airport changes."]}


def analyse_payload(payload):
    reports = [audit_stream(text, pointer, metadata) for pointer, text, metadata in streams(payload)]
    return {"schema": "parallel_fleet_audit_v1", "scope": "offline_descriptive_only",
            "economic_verdict": "not_identified_no_counterfactual",
            "input_coverage": "logs_found" if reports else "no_supported_nonempty_logs",
            "streams": reports}


def analyse_file(path):
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    payload = ([json.loads(line) for line in text.splitlines() if line.strip()]
               if path.suffix.lower() == ".jsonl" else json.loads(text))
    return {"source": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
            **analyse_payload(payload)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([analyse_file(path) for path in args.artifacts], ensure_ascii=False,
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()