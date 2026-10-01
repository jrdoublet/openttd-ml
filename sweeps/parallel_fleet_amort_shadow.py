"""Passive AIR added-equipment amortisation audit; never launches a game.

The opt-in Squirrel helper has no caller yet. Future selector snapshots must use
SCHEMA; legacy JSON/JSONL/logs only yield coverage via parallel_fleet_audit.
Ranks are NEVER reconstructed from rounded scores or a truncated portfolio.
CLI output is stdout only (use -B to avoid bytecode files).
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path

from sweeps.parallel_fleet_audit import analyse_payload as fleet_coverage

SCHEMA = "fleet_amort_elections_v1"
IDENTITY = ("campaign", "arm", "seed", "repeat", "company", "phase", "decision_id", "revision", "date")
CONTEXT = ("budget", "finance_capital", "denominator", "calibration_factor",
           "priority", "early_slot_bonus_pct", "revenue_annual", "admitted",
           "stable_index", "quantity")


def finite(value):
    return (type(value) in (int, float) and math.isfinite(value))


def positive_int(value):
    return type(value) is int and value > 0


def estimate_shadow(project, *, enabled=False, c84=False, c121=False,
                    service_choice=False, plane=None, calibrated=False, factor=None):
    """Arithmetic contract, NOT execution of Squirrel. Input must be post-R1.

    factor is the effective model factor selected by C70 OR C82, not their
    product. R2 overrides it with 1 for an observation. Missing != zero.
    """
    if not enabled or c84 or c121 or not isinstance(project, dict):
        return None
    profit = project.get("profitAnnual")
    observed = project.get("profitIsObserved")
    entry = project.get("payload")
    if (project.get("mode") != "fleet" or not finite(profit) or profit <= 0
            or type(observed) is not bool or not isinstance(entry, dict)):
        return None
    q, price = entry.get("want"), entry.get("planePrice")
    if (not positive_int(q) or not positive_int(price)
            or not isinstance(entry.get("line"), dict) or entry["line"].get("mode") != "air"):
        return None
    life = 20
    if service_choice:
        if not isinstance(plane, dict):
            return None
        age = plane.get("ageYears")
        if age is not None and (not finite(age) or type(age) is not int):
            return None
        if age is not None and age > 1:
            life = age
    applied = 1 if observed or not calibrated else factor
    if not finite(applied) or applied < 0:
        return None
    # Multiply BEFORE integer division. Do not divide the initial lot's amort.
    amort = q * price // life
    net = profit - amort
    return {"quantity": q, "planePrice": price, "lifeYears": life,
            "profitSource": "observed" if observed else "predictive_fallback",
            "profitIsObserved": observed, "grossProfitAnnual": profit,
            "addedAmortAnnual": amort, "netProfitAnnual": net,
            "calibratedProfitAnnual": net * applied}


def close(a, b):
    # Squirrel floats/log serialization need tolerance for validation only.
    # Never use this tolerance to infer a tie, compare candidates or rank them.
    return finite(a) and finite(b) and math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)


def candidate_check(row, settings):
    """Require frozen identical contexts; validate only the accounting delta."""
    errors = []
    if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
        return ["invalid_candidate_identity"], None
    original, shadow = row.get("baseline"), row.get("alternative")
    if not isinstance(original, dict) or not isinstance(shadow, dict):
        return ["missing_candidate_snapshots"], None
    before, after = original.get("context"), shadow.get("context")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return ["missing_context"], None
    if any(k not in before or before[k] is None for k in CONTEXT) or before != after:
        return ["missing_or_changed_context"], None
    for k in CONTEXT:
        if k != "admitted" and not finite(before[k]):
            errors.append("invalid_context:" + k)
    if before["admitted"] is not True:
        errors.append("not_fixed_admitted_population")
    if (not finite(before["denominator"]) or before["denominator"] <= 0
            or not finite(before["calibration_factor"]) or before["calibration_factor"] < 0):
        errors.append("invalid_denominator_or_calibration")
    if (not finite(before["finance_capital"]) or not finite(before["budget"])
            or before["finance_capital"] <= 0 or before["finance_capital"] > before["budget"]):
        errors.append("invalid_budget")
    for snap in (original, shadow):
        if any(not finite(snap.get(k)) for k in ("profitAnnual", "calibratedProfitAnnual", "score")):
            errors.append("missing_profit_or_score")
    if errors:
        return errors, None
    for snap in (original, shadow):
        expected_score = (max(0, snap["calibratedProfitAnnual"]) * 1000.0 / before["denominator"]
                          * (1.0 + before["early_slot_bonus_pct"] / 100.0))
        if not close(snap["score"], expected_score):
            errors.append("inconsistent_score")
        if not close(snap["calibratedProfitAnnual"], snap["profitAnnual"] * before["calibration_factor"]):
            errors.append("inconsistent_calibration")
    estimate = None
    if row.get("category") == "fleet_legacy":
        project = row.get("project")
        estimate = estimate_shadow(project, enabled=True, c84=settings["c84"],
                                   c121=settings["c121"], service_choice=settings["v92"],
                                   plane=row.get("plane"), calibrated=settings["calibrated"],
                                   factor=before["calibration_factor"])
        if estimate is None:
            return ["missing_or_unsupported_fleet_inputs"], None
        applied = 1 if project["profitIsObserved"] or not settings["calibrated"] else before["calibration_factor"]
        if before["calibration_factor"] != applied:
            errors.append("r2_or_disabled_calibration_violation")
        if (before["quantity"] != estimate["quantity"]
                or not close(original["profitAnnual"], estimate["grossProfitAnnual"])
                or not close(original["calibratedProfitAnnual"], estimate["grossProfitAnnual"] * applied)
                or not close(shadow["profitAnnual"], estimate["netProfitAnnual"])
                or not close(shadow["calibratedProfitAnnual"], estimate["calibratedProfitAnnual"])):
            errors.append("accounting_or_r1_mismatch")
    elif row.get("category") in ("new_link", "other_unchanged"):
        if row.get("category") == "new_link" and row.get("mode") not in ("air", "road", "rail", "water"):
            errors.append("unknown_new_link_mode")
        if original != shadow:
            errors.append("non_legacy_candidate_changed")
    else:
        errors.append("unsupported_category")
    return errors, estimate


def analyse_election(election):
    """Consume TWO full orders computed by the selector on diagnostic copies.

    Admission, budget, calibration, denominator and priorities stay fixed. This
    measures sensitivity of the current admitted set, not another policy's
    admissions, future purchases, or marginal economic returns.
    """
    result = {"identity": {}, "status": "not_measurable", "blockers": [],
              "inversions": None, "fleet_vs_new_link_inversions": None,
              "winner_changed": None, "accounting": []}
    if not isinstance(election, dict):
        result["blockers"] = ["invalid_election"]
        return result
    result["identity"] = {k: election.get(k) for k in IDENTITY}
    errors = result["blockers"]
    if any(election.get(k) is None or election.get(k) == "" for k in IDENTITY):
        errors.append("missing_identity")
    if election.get("complete") is not True:
        errors.append("incomplete_candidates")
    if (election.get("order_source") != "selector"
            or election.get("comparison_scope") != "fixed_admission"
            or election.get("all_admitted_before_limit") is not True):
        errors.append("not_full_selector_orders")
    settings = election.get("settings")
    required_flags = ("c84", "c85", "c121", "c122", "v92", "calibrated")
    settings_ok = isinstance(settings, dict) and all(type(settings.get(k)) is bool for k in required_flags)
    if (not settings_ok or any(settings.get(k) for k in ("c84", "c85", "c121", "c122"))
            or settings.get("c115") != 1 or settings.get("cadence_off") is not True):
        errors.append("unsupported_or_missing_settings")
        settings_ok = False
    rows = election.get("candidates")
    if not isinstance(rows, list):
        errors.append("missing_candidates")
        return result
    if type(election.get("candidate_count")) is not int or election["candidate_count"] != len(rows):
        errors.append("candidate_count_mismatch")
    ids = [r.get("id") if isinstance(r, dict) else None for r in rows]
    valid_ids = all(isinstance(k, str) and k for k in ids)
    if not valid_ids or len(set(ids)) != len(ids):
        errors.append("invalid_or_duplicate_candidate_ids")
    if settings_ok:
        for row in rows:
            blockers, estimate = candidate_check(row, settings)
            errors.extend(blockers)
            if estimate is not None:
                result["accounting"].append({"id": row["id"], **estimate})
    for key in ("baseline_order", "alternative_order"):
        order = election.get(key)
        if (not isinstance(order, list) or not all(isinstance(k, str) for k in order)
                or len(order) != len(ids) or not valid_ids or set(order) != set(ids)):
            errors.append("missing_or_truncated_order:" + key)
    # Candidates share the same budget; stable indices identify the unchanged
    # insertion order. No regrouping by mode, town, rank or current line state.
    if not errors and rows:
        contexts = [r["baseline"]["context"] for r in rows]
        if len({c["budget"] for c in contexts}) != 1:
            errors.append("mixed_budgets")
        indices = [c["stable_index"] for c in contexts]
        if any(type(i) is not int or i < 0 for i in indices) or len(set(indices)) != len(indices):
            errors.append("invalid_stable_indices")
    if errors:
        result["blockers"] = sorted(set(errors))
        return result
    original, shadow = election["baseline_order"], election["alternative_order"]
    positions = {key: i for i, key in enumerate(shadow)}
    pairs = [[a, b] for a, b in itertools.combinations(original, 2) if positions[a] > positions[b]]
    categories = {r["id"]: r["category"] for r in rows}
    result.update(status="measured_selector_snapshot", inversions=pairs,
                  fleet_vs_new_link_inversions=[p for p in pairs if {categories[k] for k in p} == {"fleet_legacy", "new_link"}],
                  winner_changed=(original[0] != shadow[0]) if original else False)
    return result


def analyse_payload(payload):
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        coverage = fleet_coverage(payload)
        return {"schema": SCHEMA, "status": "not_measurable", "inversions": None,
                "reason": "no_complete_election_snapshots", "legacy_coverage": coverage}
    elections = payload.get("elections")
    if not isinstance(elections, list):
        return {"schema": SCHEMA, "status": "not_measurable", "inversions": None,
                "reason": "missing_elections"}
    output = [analyse_election(e) for e in elections]
    keys = [json.dumps(r["identity"], sort_keys=True) for r in output]
    duplicates = {key for key, count in Counter(keys).items() if count > 1}
    for key, row in zip(keys, output):
        if key in duplicates:
            row.update(status="not_measurable", inversions=None,
                       fleet_vs_new_link_inversions=None, winner_changed=None)
            row["blockers"].append("duplicate_election_identity")
    return {"schema": SCHEMA, "elections": output,
            "coverage": {"elections": len(output),
                         "measurable": sum(r["status"] == "measured_selector_snapshot" for r in output)},
            "economic_verdict": "not_identified_no_counterfactual"}


def analyse_file(path):
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    if path.suffix.lower() == ".log":
        payload = {"openttd_output_raw": text}
    elif path.suffix.lower() == ".jsonl":
        # Preserve each record as a separate scope; never pool checkpoints.
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
        return {"source": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
                "records": [{"record": i, "analysis": analyse_payload(p)} for i, p in enumerate(records, 1)]}
    else:
        payload = json.loads(text)
    return {"source": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
            "analysis": analyse_payload(payload)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps([analyse_file(p) for p in args.inputs], ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()