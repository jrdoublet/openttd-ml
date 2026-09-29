#!/usr/bin/env python3
"""Summarise passive C116 legacy incremental-capital candidates from C104."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

C114_LOSS_SEEDS = {100, 7, 17, 314, 1024, 12345, 424242, 8675309}

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
unique = {}
for row in payload.get("rows") or []:
    for event in row.get("events") or []:
        key = (event.get("seed"), event.get("year"), event.get("arm"), event.get("airport"),
               event.get("dist"), event.get("pax"), event.get("maxC"))
        unique[key] = event
events = list(unique.values())

def stats(values):
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {"n": len(vals), "mean": statistics.mean(vals),
            "median": statistics.median(vals), "min": min(vals), "max": max(vals)}

def ratio(a, b):
    return float(a) / float(b) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None

def project_hurdle(event, slot):
    profit = event.get(f"c116p{slot}_P")
    capital = event.get(f"c116p{slot}_C")
    if not isinstance(profit, (int, float)) or profit <= 0:
        return None
    if not isinstance(capital, (int, float)) or capital <= 0:
        return None
    return 1000.0 * float(profit) / float(capital)

def project_rule(rows, slot):
    available = [e for e in rows if project_hurdle(e, slot) is not None]
    comparable = [e for e in available
                  if e.get("c116_runner_id") != e.get("legacy_id")
                  and isinstance(e.get("c116_dC"), (int, float)) and e.get("c116_dC") > 0
                  and isinstance(e.get("c116_dP"), (int, float)) and e.get("c116_dP") > 0
                  and isinstance(e.get("c116_mroi"), (int, float))]
    switched = [e for e in comparable if e.get("c116_mroi") < project_hurdle(e, slot)]

    gap_comparable = []
    gap_switched = []
    if slot >= 2:
        for e in comparable:
            budget = e.get("c116p_budget")
            if not isinstance(budget, (int, float)):
                continue
            prior = 0.0
            ok = True
            for prior_slot in range(1, slot):
                capital = e.get(f"c116p{prior_slot}_C")
                if not isinstance(capital, (int, float)) or capital <= 0:
                    ok = False
                    break
                prior += float(capital)
            target = e.get(f"c116p{slot}_C")
            if not ok or not isinstance(target, (int, float)) or target <= 0:
                continue
            gap = max(0.0, prior + float(target) - float(budget))
            gap_comparable.append((e, gap))
            if e.get("c116_mroi") < project_hurdle(e, slot) and e.get("c116_dC") >= gap:
                gap_switched.append((e, gap))

    return {
        "available": len(available),
        "available_pct": 100.0 * len(available) / len(rows) if rows else None,
        "project_hurdle": stats(project_hurdle(e, slot) for e in available),
        "marginal_roi_over_project_hurdle": stats(
            ratio(e.get("c116_mroi"), project_hurdle(e, slot)) for e in comparable),
        "switches": len(switched),
        "switch_pct_all": 100.0 * len(switched) / len(rows) if rows else None,
        "switch_pct_comparable": 100.0 * len(switched) / len(comparable) if comparable else None,
        "replay_match_on_switch_pct": (
            100.0 * sum(e.get("c116_runner_id") == e.get("replay_id") for e in switched) / len(switched)
            if switched else None),
        "capital_ratio_on_switch": stats(ratio(e.get("c116_runner_C"), e.get("legacy_C")) for e in switched),
        "profit_ratio_on_switch": stats(ratio(e.get("c116_runner_P"), e.get("legacy_P")) for e in switched),
        "gap_comparable": len(gap_comparable),
        "gap": stats(gap for _, gap in gap_comparable),
        "gap_switches": len(gap_switched),
        "gap_switch_pct_comparable": (
            100.0 * len(gap_switched) / len(gap_comparable) if gap_comparable else None),
        "gap_replay_match_on_switch_pct": (
            100.0 * sum(e.get("c116_runner_id") == e.get("replay_id") for e, _ in gap_switched) / len(gap_switched)
            if gap_switched else None),
    }

def unlockable_rule(rows, prefix="c116u"):
    available = [e for e in rows
                 if isinstance(e.get(prefix + "_gap"), (int, float)) and e.get(prefix + "_gap") >= 0
                 and isinstance(e.get(prefix + "_hurdle"), (int, float)) and e.get(prefix + "_hurdle") > 0]
    comparable = [e for e in available
                  if e.get("c116_runner_id") != e.get("legacy_id")
                  and isinstance(e.get("c116_mroi"), (int, float))]
    switched = [e for e in comparable if e.get("c116_mroi") < e.get(prefix + "_hurdle")]
    return {
        "frontier_size": stats(e.get(prefix + "_n") for e in rows if isinstance(e.get(prefix + "_n"), (int, float))),
        "available": len(available),
        "available_pct": 100.0 * len(available) / len(rows) if rows else None,
        "gap": stats(e.get(prefix + "_gap") for e in available),
        "project_hurdle": stats(e.get(prefix + "_hurdle") for e in available),
        "marginal_roi_over_project_hurdle": stats(ratio(e.get("c116_mroi"), e.get(prefix + "_hurdle")) for e in comparable),
        "switches": len(switched),
        "switch_pct_all": 100.0 * len(switched) / len(rows) if rows else None,
        "switch_pct_comparable": 100.0 * len(switched) / len(comparable) if comparable else None,
        "replay_match_on_switch_pct": (100.0 * sum(e.get("c116_runner_id") == e.get("replay_id") for e in switched) / len(switched) if switched else None),
        "capital_ratio_on_switch": stats(ratio(e.get("c116_runner_C"), e.get("legacy_C")) for e in switched),
        "profit_ratio_on_switch": stats(ratio(e.get("c116_runner_P"), e.get("legacy_P")) for e in switched),
        "mode_on_switch": dict(Counter(str(e.get(prefix + "_mode")) for e in switched).most_common()),
    }

def self_unlock_rule(rows):
    switched = [e for e in rows
                if e.get("c116_self_unlock") == 1
                and e.get("c116_runner_id") != e.get("legacy_id")]
    return {
        "switches": len(switched),
        "switch_pct": 100.0 * len(switched) / len(rows) if rows else None,
        "replay_match_pct": (100.0 * sum(e.get("c116_runner_id") == e.get("replay_id") for e in switched) / len(switched)
                             if switched else None),
        "gap": stats(e.get("c116_self_gap") for e in switched),
        "delta_capital_over_gap": stats(ratio(e.get("c116_dC"), e.get("c116_self_gap")) for e in switched),
        "capital_ratio": stats(ratio(e.get("c116_runner_C"), e.get("legacy_C")) for e in switched),
        "profit_ratio": stats(ratio(e.get("c116_runner_P"), e.get("legacy_P")) for e in switched),
    }

def top_shadow_rule(rows):
    available = [e for e in rows
                 if isinstance(e.get("c116t_hurdle"), (int, float)) and e.get("c116t_hurdle") > 0]
    comparable = [e for e in available
                  if e.get("c116_runner_id") != e.get("legacy_id")
                  and isinstance(e.get("c116_mroi"), (int, float))]
    switched = [e for e in comparable if e.get("c116_mroi") < e.get("c116t_hurdle")]
    return {
        "available": len(available),
        "available_pct": 100.0 * len(available) / len(rows) if rows else None,
        "hurdle": stats(e.get("c116t_hurdle") for e in available),
        "marginal_roi_over_hurdle": stats(ratio(e.get("c116_mroi"), e.get("c116t_hurdle")) for e in comparable),
        "switches": len(switched),
        "switch_pct": 100.0 * len(switched) / len(rows) if rows else None,
        "replay_match_pct": (100.0 * sum(e.get("c116_runner_id") == e.get("replay_id") for e in switched) / len(switched)
                             if switched else None),
        "top_mode_on_switch": dict(Counter(str(e.get("c116t_mode")) for e in switched).most_common()),
        "capital_ratio": stats(ratio(e.get("c116_runner_C"), e.get("legacy_C")) for e in switched),
        "profit_ratio": stats(ratio(e.get("c116_runner_P"), e.get("legacy_P")) for e in switched),
    }

def summarise(rows):
    out = {"events": len(rows)}
    out["project_snapshot"] = {
        "available_pct": 100.0 * sum(isinstance(e.get("c116p_n"), (int, float)) and e.get("c116p_n") > 0 for e in rows) / len(rows) if rows else None,
        "age_days": stats(e.get("c116p_age") for e in rows if isinstance(e.get("c116p_age"), (int, float)) and e.get("c116p_age") >= 0),
        "top_mode": dict(Counter(str(e.get("c116p_top_mode")) for e in rows).most_common()),
        "p1": project_rule(rows, 1),
        "p2": project_rule(rows, 2),
        "p3": project_rule(rows, 3),
        "unlockable": unlockable_rule(rows, "c116u"),
        "global_unlockable": unlockable_rule(rows, "c116g"),
        "self_unlock": self_unlock_rule(rows),
        "top_shadow": top_shadow_rule(rows),
    }
    out["runner_available_pct"] = 100.0 * sum(e.get("c116_runner_id") != e.get("legacy_id") for e in rows) / len(rows) if rows else None
    out["delta_capital_over_kdec"] = stats(
        ratio(e.get("c116_dC"), e.get("kdec")) for e in rows
        if isinstance(e.get("kdec"), (int, float)) and e.get("kdec") > 0)
    out["marginal_roi_over_runner_score"] = stats(
        ratio(e.get("c116_mroi"), e.get("c116_rscore")) for e in rows
        if isinstance(e.get("c116_rscore"), (int, float)) and e.get("c116_rscore") > 0)
    for rule in ("c116_gate", "c116_score", "c116_marg", "c116_opp"):
        switched = [e for e in rows if e.get(rule + "_id") != e.get("legacy_id")]
        out[rule] = {
            "switches": len(switched),
            "switch_pct": 100.0 * len(switched) / len(rows) if rows else None,
            "replay_match_pct": 100.0 * sum(e.get(rule + "_id") == e.get("replay_id") for e in rows) / len(rows) if rows else None,
            "replay_match_on_switch_pct": 100.0 * sum(e.get(rule + "_id") == e.get("replay_id") for e in switched) / len(switched) if switched else None,
            "transitions": dict(Counter(
                f"{e.get('legacy_id')}->{e.get(rule + '_id')}" for e in switched).most_common()),
            "legacy_profit_ratio_on_switch": stats(ratio(e.get(rule + "_P"), e.get("legacy_P")) for e in switched),
            "legacy_capital_ratio_on_switch": stats(ratio(e.get(rule + "_C"), e.get("legacy_C")) for e in switched),
            "price_ratio_on_switch": stats(ratio(e.get(rule + "_price"), e.get("legacy_price")) for e in switched),
            "capital_saved_on_switch": stats(
                e.get("legacy_C") - e.get(rule + "_C") for e in switched
                if isinstance(e.get("legacy_C"), (int, float)) and isinstance(e.get(rule + "_C"), (int, float))),
            "profit_given_up_on_switch": stats(
                e.get("legacy_P") - e.get(rule + "_P") for e in switched
                if isinstance(e.get("legacy_P"), (int, float)) and isinstance(e.get(rule + "_P"), (int, float))),
            "delta_capital_over_kdec_on_switch": stats(
                ratio(e.get("c116_dC"), e.get("kdec")) for e in switched
                if isinstance(e.get("kdec"), (int, float)) and e.get("kdec") > 0),
            "marginal_roi_over_runner_score_on_switch": stats(
                ratio(e.get("c116_mroi"), e.get("c116_rscore")) for e in switched
                if isinstance(e.get("c116_rscore"), (int, float)) and e.get("c116_rscore") > 0),
        }
    out["gate_marginal_disagree"] = sum(
        e.get("c116_gate_id") != e.get("c116_marg_id") for e in rows)
    out["opportunity_marginal_disagree"] = sum(
        e.get("c116_opp_id") != e.get("c116_marg_id") for e in rows)
    out["opportunity_steps"] = stats(e.get("c116_opp_steps") for e in rows)
    out["opportunity_steps_histogram"] = dict(Counter(
        int(e.get("c116_opp_steps")) for e in rows
        if isinstance(e.get("c116_opp_steps"), (int, float))).most_common())
    self_hurdle = [e for e in rows
                   if isinstance(e.get("kdec"), (int, float)) and e.get("kdec") > 0
                   and isinstance(e.get("c116_dC"), (int, float)) and e.get("c116_dC") > e.get("kdec")
                   and isinstance(e.get("c116_dP"), (int, float)) and e.get("c116_dP") > 0
                   and isinstance(e.get("c116_mroi"), (int, float))
                   and isinstance(e.get("c116_lscore"), (int, float)) and e.get("c116_lscore") > 0
                   and e.get("c116_mroi") < e.get("c116_lscore")
                   and e.get("c116_runner_id") != e.get("legacy_id")]
    out["c116_self_hurdle"] = {
        "switches": len(self_hurdle),
        "switch_pct": 100.0 * len(self_hurdle) / len(rows) if rows else None,
        "replay_match_on_switch_pct": 100.0 * sum(e.get("c116_runner_id") == e.get("replay_id") for e in self_hurdle) / len(self_hurdle) if self_hurdle else None,
        "transitions": dict(Counter(f"{e.get('legacy_id')}->{e.get('c116_runner_id')}" for e in self_hurdle).most_common()),
        "legacy_profit_ratio_on_switch": stats(ratio(e.get("c116_runner_P"), e.get("legacy_P")) for e in self_hurdle),
        "legacy_capital_ratio_on_switch": stats(ratio(e.get("c116_runner_C"), e.get("legacy_C")) for e in self_hurdle),
        "delta_capital_over_kdec_on_switch": stats(ratio(e.get("c116_dC"), e.get("kdec")) for e in self_hurdle),
        "marginal_roi_over_legacy_score_on_switch": stats(ratio(e.get("c116_mroi"), e.get("c116_lscore")) for e in self_hurdle),
    }
    replay_pathological = [e for e in rows if e.get("replay_id") != e.get("legacy_id") and (
        not isinstance(e.get("replay_legacy_P"), (int, float)) or e.get("replay_legacy_P") <= 0
        or not isinstance(e.get("replay_legacy_C"), (int, float))
        or not isinstance(e.get("legacy_C"), (int, float))
        or e.get("replay_legacy_C") >= e.get("legacy_C"))]
    out["replay_pathological_switch_pct"] = (
        100.0 * len(replay_pathological) / len(rows) if rows else None)
    return out

by_arm = defaultdict(list)
by_year = defaultdict(list)
by_seed = defaultdict(list)
for event in events:
    by_arm[str(event.get("arm"))].append(event)
    by_year[str(event.get("year"))].append(event)
    by_seed[str(event.get("seed"))].append(event)

c114_losses = [e for e in events if e.get("seed") in C114_LOSS_SEEDS]
c114_wins = [e for e in events if isinstance(e.get("seed"), int) and e.get("seed") not in C114_LOSS_SEEDS]

report = {"overall": summarise(events),
          "by_arm": {k: summarise(v) for k, v in sorted(by_arm.items())},
          "by_year": {k: summarise(v) for k, v in sorted(by_year.items())},
          "c114_cohorts": {
              "old_winners": summarise(c114_wins),
              "old_losers": summarise(c114_losses),
          },
          "by_seed": {k: summarise(v) for k, v in sorted(by_seed.items(), key=lambda kv: int(kv[0]))}}
encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
if len(sys.argv) >= 3:
    Path(sys.argv[2]).write_text(encoded, encoding="utf-8")
else:
    print(encoded, end="")
