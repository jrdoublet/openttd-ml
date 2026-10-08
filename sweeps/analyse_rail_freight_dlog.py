"""Summarize freight/pax rail funnel from a diagnostic OpexAI decision log.

This parser is host-side and passive. DECISION_LOG itself is intrusive: never
compare these trajectories causally to games run without instrumentation.
Counts are event occurrences, not unique project proposals across refreshes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


OPEX_LINE = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) ([A-Z0-9_]+)(?: (.*))?$")
FIELD = re.compile(r"(\w+)=([^\s]+)")
SHADOW_LINE = re.compile(r"\bRAIL_FREIGHT_SELECT_SHADOW (.*)$")


def decode_line(line: str):
    match = OPEX_LINE.search(line.rstrip())
    if not match:
        probe = SHADOW_LINE.search(line.rstrip())
        if probe is None:
            return None
        values = dict(FIELD.findall(probe[1]))
        if not values.get("year") or not values.get("month"):
            return None
        return int(values["year"]), int(values["month"]), 1, "RAIL_FREIGHT_SELECT_SHADOW", values
    year, month, day, event, fields = match.groups()
    return int(year), int(month), int(day), event, dict(FIELD.findall(fields or ""))


def count_log(lines):
    annual = defaultdict(lambda: {
        "events": Counter(), "ranked_top5": Counter(),
        "ranked_head": Counter(), "chosen": Counter(),
        "rail_attempts": Counter(), "rail_reject_reasons": Counter(),
        "discarded": Counter(), "gen_kept": [],
        "gen_examined": [], "mixed_rail": [],
        "rail_candidate_pairs": defaultdict(set),
        "rail_chosen_pairs": defaultdict(set),
        "min_rank_by_kind": {},
        "chosen_rank_hist": Counter(),
        "rail_generation_details": [],
        "freight_select_shadow": {
            "calls": 0, "alternative_freight": 0, "cash_freight": 0,
            "floor_freight": 0, "eligible_freight": 0, "selected_freight": 0,
            "eligible_freight_calls": 0,
            "eligible_freight_head_modes": Counter(),
            "eligible_freight_head_defensive_air_any_calls": 0,
            "eligible_freight_head_air_score_below_freight_calls": 0,
            "eligible_freight_head_air_score_at_least_freight_calls": 0,
            "eligible_freight_head_air_score_unknown_calls": 0,
            "eligible_freight_but_none_selected_calls": 0,
            "eligible_freight_head_defensive_air_calls": 0,
            "eligible_freight_head_fleet_calls": 0,
            "eligible_freight_selected_calls": 0,
        },
    })
    current_generation = None
    for line in lines:
        decoded = decode_line(line)
        if decoded is None:
            continue
        year, month, day, event, values = decoded
        row = annual[year]
        row["events"][event] += 1
        mode = values.get("mode", "?")
        kind = values.get("kind", "?")
        label = f"{mode}/{kind}"
        if event == "VIVIER_GEN" and mode == "rail":
            try:
                row["gen_examined"].append(int(values["produced"]))
                row["gen_kept"].append(int(values["kept"]))
                current_generation = {
                    "date": f"{year}-{month}-{day}",
                    "examined": int(values["produced"]), "kept": int(values["kept"]),
                    "generate_pax": None, "generate_freight": None,
                    "freight_cargo": None, "target_kind": None,
                    "freight_ind_pairs": 0, "freight_town_pairs": 0,
                    "freight_town_zero_monthly": 0, "rejects": {},
                }
                row["rail_generation_details"].append(current_generation)
            except (KeyError, ValueError):
                pass
        elif event == "VIVIER_GEN":
            current_generation = None
        elif event == "RAIL_PREPAIR" and current_generation is not None:
            for key in ("generate_pax", "generate_freight", "freight_cargo", "target_kind"):
                current_generation[key] = values.get(key)
            for key in ("freight_ind_pairs", "freight_town_pairs",
                        "freight_town_zero_monthly"):
                current_generation[key] = int(values.get(key, "0"))
        elif event == "VIVIER_MIX" and "rail" in values:
            row["mixed_rail"].append(int(values["rail"]))
        elif event == "VIVIER_REJECT":
            reason = values.get("reason", "?")
            if "n" in values:
                row["rail_reject_reasons"][reason] += int(values["n"])
                if current_generation is not None and current_generation["date"] == f"{year}-{month}-{day}":
                    current_generation["rejects"][reason] = int(values["n"])
        elif event == "PORTFOLIO_RANK":
            rank = int(values.get("rank", "-1"))
            if 0 <= rank < 5:
                row["ranked_top5"][label] += 1
            if rank == 0:
                row["ranked_head"][label] += 1
            if mode == "rail":
                row["rail_candidate_pairs"][kind].add(
                    (values.get("cargo"), values.get("src"), values.get("dst")))
                prior = row["min_rank_by_kind"].get(kind)
                if prior is None or rank < prior:
                    row["min_rank_by_kind"][kind] = rank
        elif event == "PROJECT_CHOSEN":
            row["chosen"][label] += 1
            rank = values.get("rank", "?")
            row["chosen_rank_hist"][f"{label}@{rank}"] += 1
            if mode == "rail":
                row["rail_chosen_pairs"][kind].add(
                    (values.get("cargo"), values.get("src"), values.get("dst")))
        elif event == "RAIL_ATTEMPT":
            row["rail_attempts"][f"{kind}/{values.get('reason', '?')}"] += 1
        elif event == "PROJECT_DISCARD":
            row["discarded"][f"{mode}/{values.get('reason', '?')}"] += 1
        elif event == "RAIL_FREIGHT_SELECT_SHADOW":
            stats = row["freight_select_shadow"]
            stats["calls"] += 1
            stats["alternative_freight"] += int(values.get("total_f", "0"))
            stats["cash_freight"] += int(values.get("cash_f", "0"))
            stats["floor_freight"] += int(values.get("floor_f", "0"))
            eligible = int(values.get("eligible_f", "0"))
            selected = int(values.get("selected_f", "0"))
            stats["eligible_freight"] += eligible
            stats["selected_freight"] += selected
            if eligible > 0:
                stats["eligible_freight_calls"] += 1
                head_mode = values.get("head_mode", "?")
                stats["eligible_freight_head_modes"][head_mode] += 1
                if head_mode == "air" and int(values.get("head_tier", "0")) > 0:
                    stats["eligible_freight_head_defensive_air_any_calls"] += 1
                if head_mode == "air":
                    try:
                        head_score = float(values["head_score"])
                        best_f_score = float(values["best_f_score"])
                        if head_score < best_f_score:
                            stats["eligible_freight_head_air_score_below_freight_calls"] += 1
                        else:
                            stats["eligible_freight_head_air_score_at_least_freight_calls"] += 1
                    except (KeyError, ValueError):
                        stats["eligible_freight_head_air_score_unknown_calls"] += 1
            if eligible > 0 and selected > 0:
                stats["eligible_freight_selected_calls"] += 1
            elif eligible > 0:
                stats["eligible_freight_but_none_selected_calls"] += 1
                if values.get("head_mode") == "air" and int(values.get("head_tier", "0")) > 0:
                    stats["eligible_freight_head_defensive_air_calls"] += 1
                if values.get("head_mode") == "fleet":
                    stats["eligible_freight_head_fleet_calls"] += 1
    out = {}
    for year, row in sorted(annual.items()):
        out[str(year)] = {
            "events": dict(row["events"]),
            "ranked_top5_occurrences": dict(row["ranked_top5"]),
            "ranked_head_occurrences": dict(row["ranked_head"]),
            "chosen_occurrences": dict(row["chosen"]),
            "rail_attempt_occurrences": dict(row["rail_attempts"]),
            "rail_reject_occurrences": dict(row["rail_reject_reasons"]),
            "discarded_occurrences": dict(row["discarded"]),
            "rail_generation_calls": len(row["gen_kept"]),
            "rail_generated_pairs_examined_sum": sum(row["gen_examined"]),
            "rail_generated_candidates_kept_sum": sum(row["gen_kept"]),
            "rail_generation_empty_calls": sum(v == 0 for v in row["gen_kept"]),
            "rail_vivier_mix_snapshots": len(row["mixed_rail"]),
            "rail_vivier_mix_nonempty": sum(v > 0 for v in row["mixed_rail"]),
            "distinct_ranked_rail_pairs_by_kind": {
                key: len(pairs) for key, pairs in row["rail_candidate_pairs"].items()},
            "distinct_chosen_rail_pairs_by_kind": {
                key: len(pairs) for key, pairs in row["rail_chosen_pairs"].items()},
            "min_rank_by_rail_kind": dict(row["min_rank_by_kind"]),
            "chosen_rank_hist": dict(row["chosen_rank_hist"]),
            "rail_generation_details": row["rail_generation_details"],
            "freight_select_shadow": row["freight_select_shadow"],
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path, nargs="+")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = {"warning": "Instrumented runs only. Counts repeat across refreshes; no causal baseline.",
              "logs": {}}
    for path in args.logs:
        with path.open(encoding="utf-8", errors="replace") as handle:
            report["logs"][path.name] = count_log(handle)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
