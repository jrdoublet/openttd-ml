#!/usr/bin/env python3
"""P4 : chaîne événementielle de décisions, constructions et lignes matures.

Lecture *sans simulation* des artefacts C66.4 matched-shadow. L'exposition
causale n'est pas un effet causal : les journaux ne donnent pas à chaque
sélection les deux classements C77 dans le *même* état du monde.
"""

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re

SIM_DATE = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) ")
FIELDS = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)")
TOKENS = ("PROJECT_CHOSEN", "AIR_BUILD", "RAIL_BUILD", "LINE_REVENUE", "P4_VYEAR_MODE")


def read_log(path):
    events = {k: [] for k in TOKENS}
    with path.open(encoding="utf8", errors="replace") as stream:
        lines = list(stream)
    last_opex_date = None
    for index, line in enumerate(lines):
        if "[0] [I]" not in line:
            continue
        match = SIM_DATE.search(line)
        simulation_date = (f"{int(match[1]):04d}-{int(match[2]):02d}-{int(match[3]):02d}"
                           if match else None)
        if simulation_date:
            last_opex_date = simulation_date
        for name in TOKENS:
            pos = line.find(name + " ")
            if pos < 0:
                continue
            value = dict(FIELDS.findall(line[pos + len(name) + 1:]))
            value["log_index"] = index
            if simulation_date:
                value["date"] = simulation_date
            if name == "P4_VYEAR_MODE":
                # Le rapport d'exercice N n'est PAS toujours publie le 1er
                # janvier N+1 (scheduler/opcodes : juin dans une graine).
                # P4_VYEAR_MODE n'imprime pas sa date : la derniere ligne
                # OPEX datee fournit une borne chronologique observable.
                value["date"] = last_opex_date or f"{int(value['exercise']) + 1}-01-01"
                value["date_evidence"] = "last_opex_log" if last_opex_date else "year_lower_bound_only"
            events[name].append(value)
            break
    return events


def selected_signature(record):
    return (record.get("mode"), record.get("cargo"), record.get("kind"),
            record.get("src"), record.get("dst"))


def construction_signature(record, mode):
    return (record.get("date"), mode, record.get("src"), record.get("dst"),
            record.get("cargo") if mode == "rail" else "PASS")


def first_sequence_difference(left, right, signature):
    """Premier désaccord ordonné; jamais une paire au seul rang temporel."""
    for i in range(max(len(left), len(right))):
        x = left[i] if i < len(left) else None
        y = right[i] if i < len(right) else None
        if x is None or y is None or signature(x) != signature(y):
            return {"index": i, "reference": x, "variant": y,
                    "first_date": min([row["date"] for row in (x, y) if row is not None])}
    return None


def factors(events):
    result = []
    for row in events["P4_VYEAR_MODE"]:
        try:
            if (int(row["applied"]) == 1
                    and abs(float(row["factor"]) - float(row["legacy_k"])) > 1e-7):
                result.append({"date": row["date"], "mode": row["mode"],
                               "factor": float(row["factor"]),
                               "legacy": float(row["legacy_k"]),
                               "covered": int(row["covered"])})
        except (KeyError, ValueError):
            raise ValueError("Invalid P4_VYEAR_MODE payload") from None
    return result


def builds_with_revenue(events):
    reports = defaultdict(list)
    for r in events["LINE_REVENUE"]:
        reports[r.get("line")].append(r)
    outcome = []
    for mode, marker in (("air", "AIR_BUILD"), ("rail", "RAIL_BUILD")):
        for row in events[marker]:
            line_id = row.get("line")
            if line_id is None:
                raise ValueError(f"{marker} has no line ID")
            matured = [r for r in reports[line_id] if int(r.get("age", "-1")) >= 2]
            outcome.append({
                "line": line_id, "mode": mode, "date": row["date"],
                "src": row.get("src"), "dst": row.get("dst"),
                "cargo": row.get("cargo", "PASS"),
                "predicted_build_profit": row.get("profit", row.get("pred_profit")),
                "mature_reports": [
                    {"year": r.get("year"), "age": int(r["age"]),
                     "real_prof": int(r["real_prof"]),
                     "pred_prof": int(r["pred_prof"]),
                     "vehs": int(r.get("vehs", -1))}
                    for r in matured],
            })
    return sorted(outcome, key=lambda x: (x["date"], x["mode"], x["line"]))


def matched_mature_same_od(reference, variant):
    """Rapproche lignes au même OD; leurs profits ne sont PAS des effets nets."""
    pools = []
    for arm in (reference, variant):
        by_key = defaultdict(list)
        for row in arm:
            by_key[(row["mode"], row["cargo"], row["src"], row["dst"])].append(row)
        pools.append(by_key)
    matches = []
    ambiguous = 0
    for key in pools[0].keys() & pools[1].keys():
        x, y = pools[0][key], pools[1][key]
        if len(x) != 1 or len(y) != 1:
            ambiguous += 1
            continue
        xr = {r["year"]: r for r in x[0]["mature_reports"]}
        yr = {r["year"]: r for r in y[0]["mature_reports"]}
        for year in sorted(xr.keys() & yr.keys()):
            a, b = xr[year], yr[year]
            matches.append({
                "od": list(key), "year": year,
                "reference_line": x[0]["line"], "variant_line": y[0]["line"],
                "reference_build_date": x[0]["date"], "variant_build_date": y[0]["date"],
                "reference_real_prof": a["real_prof"], "variant_real_prof": b["real_prof"],
                "profit_delta": b["real_prof"] - a["real_prof"],
                "reference_vehs": a["vehs"], "variant_vehs": b["vehs"],
            })
    return sorted(matches, key=lambda m: (m["year"], m["od"])), ambiguous


def first_money_difference(jsonl, reference, variant, seed, company="OpexAI"):
    months = defaultdict(dict)
    with jsonl.open(encoding="utf8") as fh:
        for line in fh:
            row = json.loads(line)
            if row["run"][0] == company and int(row["run"][1]) == seed:
                # Le rival est `policy_id=AAAHogEx` dans les DEUX bras.
                # Le segment du duel qui l'heberge est `duel_policy_id`.
                key = row["policy_id"] if company == "OpexAI" else row["duel_policy_id"]
                months[row["date"]][key] = row
    for month in sorted(months):
        if reference not in months[month] or variant not in months[month]:
            raise ValueError(f"Missing monthly pair {seed} {month}")
        a, b = months[month][reference], months[month][variant]
        if a["source_bundle_sha256"] != b["source_bundle_sha256"]:
            raise ValueError("Bundles differ across paired arms")
        if a.get("money") != b.get("money"):
            return month
    return None


def classify_fork(fork, first_factor, first_money):
    if fork is None:
        return "no_observed_fork"
    if first_factor is None or fork["first_date"] < first_factor:
        return "before_p4_factor_or_no_factor"
    if first_money is not None and fork["first_date"] >= first_money:
        return "after_observed_world_divergence"
    return "post_factor_pre_money_unproven_same_state"


def analyse(report_path):
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf8"))
    policies = {x["role"]: x["id"] for x in report["policies"]}
    reference, variant = policies["reference"], policies["variant"]
    folder = report_path.with_name(report_path.stem + "_engine")
    rows = []
    for seed in report["seeds"]:
        files = [folder / f"{policy}_seed{seed}_r0.log" for policy in (reference, variant)]
        if any(not f.is_file() for f in files):
            raise FileNotFoundError(f"Missing engine log for seed {seed}: {files}")
        a, b = [read_log(f) for f in files]
        first_money = first_money_difference(report_path.with_suffix(".jsonl"),
                                            reference, variant, seed)
        first_rival_money = first_money_difference(report_path.with_suffix(".jsonl"),
                                                  reference, variant, seed, "AAAHogEx")
        first_any_money = min((d for d in (first_money, first_rival_money) if d), default=None)
        applied = factors(b)
        first_factor = min((r["date"] for r in applied), default=None)
        choice_timing = first_sequence_difference(
            a["PROJECT_CHOSEN"], b["PROJECT_CHOSEN"],
            lambda x: (x["date"], selected_signature(x)))
        choices = first_sequence_difference(
            a["PROJECT_CHOSEN"], b["PROJECT_CHOSEN"], selected_signature)
        abuilds, bbuilds = builds_with_revenue(a), builds_with_revenue(b)
        paired_mature, ambiguous_od = matched_mature_same_od(abuilds, bbuilds)
        build_timing = first_sequence_difference(
            abuilds, bbuilds,
            lambda x: (x["date"], x["mode"], x["src"], x["dst"], x["cargo"]))
        first_build = first_sequence_difference(
            abuilds, bbuilds,
            lambda x: (x["mode"], x["src"], x["dst"], x["cargo"]))
        rows.append({
            "seed": seed, "first_money_difference": first_money,
            "first_rival_money_difference": first_rival_money,
            "first_any_company_money_difference": first_any_money,
            "first_factor_publication": first_factor,
            "factor_changes": applied,
            "chosen_counts": [len(a["PROJECT_CHOSEN"]), len(b["PROJECT_CHOSEN"])],
            "built_counts": [len(abuilds), len(bbuilds)],
            "mature_built_lines": [sum(bool(r["mature_reports"]) for r in abuilds),
                                   sum(bool(r["mature_reports"]) for r in bbuilds)],
            "same_od_mature_line_year_pairs": paired_mature,
            "same_od_mature_pair_count": len(paired_mature),
            "same_od_ambiguous_multiple_lines": ambiguous_od,
            "first_choice_timing_or_od_difference": choice_timing,
            "first_choice_fork": choices,
            "first_choice_fork_class": classify_fork(choices, first_factor, first_money),
            "first_choice_fork_class_both_companies": classify_fork(choices, first_factor, first_any_money),
            "first_build_timing_or_od_difference": build_timing,
            "first_build_fork": first_build,
            "first_build_fork_class": classify_fork(first_build, first_factor, first_money),
            "first_build_fork_class_both_companies": classify_fork(first_build, first_factor, first_any_money),
            "built_reference": abuilds, "built_variant": bbuilds,
        })
    return {
        "campaign": report["campaign_id"], "bundle": report["source_bundle_sha256"],
        "reference": reference, "variant": variant, "seeds": rows,
        "limitations": [
            "The first observed choice fork may reflect scheduling, not a C77 ranking flip.",
            "Timing-only shifts of the same OD are recorded separately from different-OD forks.",
            "A monthly money fork can occur after an earlier intra-month world fork.",
            "The rival is already divergent in some seeds before the Opex money snapshot diverges.",
            "AIR/RAIL_BUILD proves a construction; PROJECT_CHOSEN does not.",
            "LINE_REVENUE is line profit, not marginal network profit or the alternative's outcome.",
            "Same-OD mature line-years are conditioning on survival and may have distinct build dates/fleets.",
            "The two policies lack a same-state replay of all eligible same-C77 candidates.",
            "RAIL resumable construction does not necessarily happen on the choice date.",
        ],
        "causal_gain_demonstrated": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = analyse(args.report)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("campaign", result["campaign"])
    for row in result["seeds"]:
        print(row["seed"], "money", row["first_money_difference"],
              "rival", row["first_rival_money_difference"],
              "factor", row["first_factor_publication"],
              "choice timing", row["first_choice_timing_or_od_difference"]["first_date"]
              if row["first_choice_timing_or_od_difference"] else "none",
              "choice", row["first_choice_fork"]["first_date"] if row["first_choice_fork"] else "none",
              row["first_choice_fork_class_both_companies"],
              "build timing", row["first_build_timing_or_od_difference"]["first_date"]
              if row["first_build_timing_or_od_difference"] else "none",
              "build", row["first_build_fork"]["first_date"] if row["first_build_fork"] else "none",
              row["first_build_fork_class_both_companies"],
              "buildcounts", row["built_counts"], "mature", row["mature_built_lines"])


if __name__ == "__main__":
    main()
