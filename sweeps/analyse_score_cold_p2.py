"""Audit P2: complete, simultaneously affordable project rankings in 1970-71.

Requires score_cold_prior_shadow=1 on a frozen bundle (and decision_log=1
to relate subsequent PROJECT_CHOSEN/BUILD). This is a *snapshot* analysis;
neither repeated selection passes nor monthly measurements are independent
seeds. Optional JSON factors are researcher-supplied, never fitted here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def fields(line, marker):
    pos = line.find(marker + " ")
    if pos == -1:
        return None
    output = {}
    for token in line[pos + len(marker) + 1 :].strip().split():
        if "=" in token:
            key, value = token.split("=", 1)
            output[key] = value
    return output


def num(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def project_key(p, head=False):
    prefix = "head_" if head else ""
    return tuple(p.get(prefix + f) for f in
                 ("mode", "kind", "arm", "src", "dst", "cargo", "engine", "line"))


def service_key(p):
    """New transport OD (or growth on an existing named line)."""
    if p["mode"] == "fleet":
        return ("fleet", p.get("line"))
    return (p["mode"], p["kind"], p["src"], p["dst"], p["cargo"])


def family(p):
    if p["mode"] == "air":
        return "air:" + p["arm"]
    if p["mode"] == "rail":
        return "rail:" + p["kind"]
    return p["mode"]


def can_apply(p):
    """Eligibility of a cold prior, preserving observed and C121/V161 margins."""
    if p["mode"] not in ("air", "rail"):
        return False
    if p["observed"] == "1" or p["v161_source"] == "prior":
        return False
    if p["c121_real"] == "1" and num(p["realization_factor"], 1) != 1:
        return False
    # The model may already have learned a non-neutral C70/C82 factor.
    return abs(num(p["factor"], 1) - 1) < 0.0000001


def order(rows, factors=None):
    factors = factors or {}
    def new_score(p):
        k = num(factors.get(family(p), 1), 1) if can_apply(p) else 1
        return num(p["rank_score"]) * k
    return sorted(rows, key=lambda p: (-num(p["tier"]), -new_score(p),
                                      -num(p["revenue"]), int(p["ordinal"])))


def audit_lines(lines, factors=None):
    passes = defaultdict(lambda: {"rows": [], "head": []})
    for line in lines:
        c = fields(line, "SCORE_COLD_P2_CAND")
        if c is not None:
            passes[c.get("pass")]["rows"].append(c)
        h = fields(line, "SCORE_COLD_P2_HEAD")
        if h is not None:
            passes[h.get("pass")]["head"].append(h)
    counts = Counter()
    flips = []
    by_family = Counter()
    seen_passes = Counter()
    for pass_id, event in passes.items():
        heads = event["head"]
        rows = event["rows"]
        if len(heads) != 1 or len(rows) != int(heads[0].get("eligible", -1)):
            counts["incomplete_passes"] += 1
            continue
        head = heads[0]
        if head.get("dedupe") != "0":
            counts["deduplicated_unsupported"] += 1
            continue
        # The rescue loop replaces the first one; both phases are logged to
        # preserve provenance, but only rescue alternatives remain electable.
        if head["fallback"] == "1":
            rows = [r for r in rows if r["phase"] == "fallback"]
        if not rows:
            counts["empty_passes"] += 1
            continue
        if len({int(p["ordinal"]) for p in rows}) != len(rows):
            counts["duplicate_ordinal"] += 1
            continue
        baseline = order(rows)
        expected = project_key(head, True)
        if project_key(baseline[0]) != expected or (
            "head_tier" in head and num(baseline[0]["tier"]) != num(head["head_tier"])
        ) or ("head_score" in head
              and abs(num(baseline[0]["rank_score"]) - num(head["head_score"])) > 0.001):
            counts["baseline_mismatch"] += 1
            continue
        counts["complete_passes"] += 1
        seen_passes[head["year"]] += 1
        for p in rows:
            if can_apply(p):
                by_family[family(p)] += 1
        winner = order(rows, factors)[0]
        if project_key(winner) != expected:
            counts["head_flips"] += 1
            if num(winner["tier"]) != num(baseline[0]["tier"]):
                counts["tier_mismatch"] += 1
            same_od = service_key(winner) == service_key(baseline[0])
            if same_od:
                counts["same_service_head_changes"] += 1
            else:
                counts["different_service_head_flips"] += 1
            same_tier = winner["tier"] == baseline[0]["tier"]
            if not same_tier:
                counts["non_c77_compliant_changes"] += 1
            if same_tier and not same_od:
                counts["actionable_same_tier_od_flips"] += 1
            if winner["mode"] == "fleet" and baseline[0]["mode"] == "rail":
                counts["prohibited_fleet_over_rail"] += 1
            flips.append({"pass": pass_id, "year": head["year"],
                          "month": head["month"], "day": head["day"],
                          "before": family(baseline[0]), "after": family(winner),
                          "before_key": project_key(baseline[0]),
                          "after_key": project_key(winner),
                          "before_score": num(baseline[0]["rank_score"]),
                          "after_score": num(winner["rank_score"]),
                          "priority": int(winner["tier"]),
                          "same_tier": same_tier, "same_service": same_od,
                          "candidate_was_affordable": True,
                          "build_confirmed": False})
    return {"counts": dict(counts), "complete_passes_by_year": dict(seen_passes),
            "cold_candidates_by_family": dict(by_family), "flips": flips}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path, help="One engine log per seed/arm")
    parser.add_argument("--factors", type=Path,
                        help='JSON object e.g. {"air:newpair":0.8,"rail:freight":1.1}; diagnostic only')
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    factors = json.loads(args.factors.read_text(encoding="utf-8")) if args.factors else None
    if factors is not None and (not isinstance(factors, dict)
                                 or any(num(v, -1) <= 0 for v in factors.values())):
        parser.error("factors must be a mapping of strictly positive numbers")
    result = {"factors": factors, "logs": {}, "calibrated_factors_verified": False,
              "builds_linked": False,
              "scope": "1970-71 snapshot rank replay; exploratory what-if factors only, no causal profit claim"}
    for path in args.logs:
        with path.open(encoding="utf-8", errors="replace") as file:
            result["logs"][str(path)] = audit_lines(file, factors)
    result_text = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
    if args.out:
        args.out.write_text(result_text + "\n", encoding="utf-8")
    else:
        print(result_text)


if __name__ == "__main__":
    main()
