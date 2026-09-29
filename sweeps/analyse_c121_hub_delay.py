#!/usr/bin/env python3
"""Diagnostic compact C121 hub-delay + replay economique au timing live."""

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from analyse_c121_air_economics_shadow import replay_fleet  # noqa: E402


def stat(values):
    values = [float(v) for v in values if isinstance(v, (int, float))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    values.sort()
    n = len(values)

    def q(p):
        if n == 1:
            return values[0]
        x = (n - 1) * p
        lo = int(x)
        hi = min(lo + 1, n - 1)
        frac = x - lo
        return values[lo] * (1.0 - frac) + values[hi] * frac

    return {
        "n": n,
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p25": q(0.25),
        "p75": q(0.75),
    }


def weighted(events, field, weight="period_days"):
    pairs = [
        (float(e[field]), float(e[weight]))
        for e in events
        if isinstance(e.get(field), (int, float)) and e[field] > 0
        and isinstance(e.get(weight), (int, float)) and e[weight] > 0
    ]
    den = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / den if den > 0 else None


def ratio(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or b == 0:
        return None
    return float(a) / float(b)


def observed_leg_days(events):
    total = sum(float(e.get("leg_days_sum", 0) or 0) for e in events
                if isinstance(e.get("leg_days_sum"), (int, float)))
    count = sum(float(e.get("leg_days_n", 0) or 0) for e in events
                if isinstance(e.get("leg_days_n"), (int, float)))
    return total / count if count > 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    summary_path = args.input.with_name(args.input.stem + "_summary.json")
    age_path = args.input.with_name(args.input.stem + "_age_windows.json")
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    age_payload = json.loads(age_path.read_text(encoding="utf-8")) if age_path.exists() else None
    builds = {}
    events = defaultdict(list)
    updates = []
    last_update_by_seed = {}
    for row in payload.get("rows", []):
        seed = row.get("seed")
        for build in row.get("c121_builds", []):
            if isinstance(seed, int) and isinstance(build.get("line"), (int, float)):
                builds[(seed, int(build["line"]))] = build
        for event in row.get("events", []):
            if isinstance(seed, int) and isinstance(event.get("line"), (int, float)):
                events[(seed, int(event["line"]))].append(event)
        row_updates = row.get("hub_delay_updates", [])
        for update in row_updates:
            item = dict(update)
            item["seed"] = seed
            updates.append(item)
        if row_updates:
            last_update_by_seed[seed] = max(
                row_updates, key=lambda u: int(u.get("update_samples", 0)))

    history_any = 0
    history_both = 0
    delay_sums = []
    for build in builds.values():
        a = int(build.get("hub_delay_window_obs_a", 0) or 0)
        b = int(build.get("hub_delay_window_obs_b", 0) or 0)
        if a > 0 or b > 0:
            history_any += 1
        if a > 0 and b > 0:
            history_both += 1
        da = build.get("hub_delay_a")
        db = build.get("hub_delay_b")
        if isinstance(da, (int, float)) and isinstance(db, (int, float)):
            delay_sums.append(float(da) + float(db))

    total_update_ops = 0
    total_update_samples = 0
    for update in last_update_by_seed.values():
        if isinstance(update.get("update_ops_total"), (int, float)):
            total_update_ops += int(update["update_ops_total"])
        if isinstance(update.get("update_samples"), (int, float)):
            total_update_samples += int(update["update_samples"])

    replay_rows = []
    live_growth = defaultdict(list)
    history_quality = defaultdict(list)
    summary_rows = {}
    if summary_payload is not None:
        summary_rows = {
            (int(row["seed"]), int(row["line"])): row
            for row in summary_payload.get("rows", [])
            if isinstance(row.get("seed"), (int, float))
            and isinstance(row.get("line"), (int, float))
        }
    for key, build in builds.items():
        mature = [
            e for e in events.get(key, [])
            if isinstance(e.get("age_bucket"), (int, float)) and e["age_bucket"] >= 6
        ]
        if not mature:
            continue
        live_oneway = weighted(mature, "c121_adapted_oneway_days")
        if live_oneway is None:
            continue
        mature_leg = observed_leg_days(mature)
        live_oneway_leg = weighted(mature, "c121_adapted_oneway_days", weight="leg_days_n")
        if live_oneway_leg is None:
            live_oneway_leg = live_oneway
        summary_row = summary_rows.get(key)
        if summary_row is not None and mature_leg is not None:
            live_growth[summary_row.get("route_growth_bucket", "unknown")].append(
                ratio(mature_leg, live_oneway_leg))
            ready = sum(1 for field in ("hub_delay_window_obs_a", "hub_delay_window_obs_b")
                        if isinstance(build.get(field), (int, float)) and build[field] > 0)
            history_quality[str(ready)].append({
                "leg_build": summary_row.get("actual_over_pred_leg_days"),
                "leg_live": ratio(mature_leg, live_oneway_leg),
                "total": summary_row.get("actual_over_pred_total"),
                "revenue": summary_row.get("actual_over_pred_revenue"),
                "profit": summary_row.get("actual_over_pred_profit"),
                "decision_fleet": summary_row.get("actual_over_decision_fleet"),
            })
        original = replay_fleet(build)
        adapted = replay_fleet(build, one_way_override=live_oneway)
        if original is None or adapted is None:
            continue
        od = original["decision"]
        ad = adapted["decision"]
        replay_rows.append({
            "engine": build.get("engine"),
            "planes_original": od["planes"],
            "planes_adapted": ad["planes"],
            "fleet_ratio": ratio(ad["planes"], od["planes"]),
            "revenue_ratio": ratio(ad["revenue"], od["revenue"]),
            "profit_ratio": ratio(ad["profit"], od["profit"]),
            "score_ratio": ratio(ad["score"], od["score"]),
            "profit_delta": ad["profit"] - od["profit"],
            "score_delta": ad["score"] - od["score"],
            "oneway_build": build.get("one_way_days"),
            "oneway_live": live_oneway,
        })

    result = {
        "source_campaign": payload.get("campaign_id", args.input.stem),
        "hub_delay": {
            "update_count": len(updates),
            "station_seed_count": len({(u.get("seed"), u.get("station")) for u in updates}),
            "published_days": stat([u.get("days") for u in updates]),
            "raw_days": stat([u.get("raw_days") for u in updates]),
            "window_n": stat([u.get("window_n") for u in updates]),
            "variance": stat([u.get("variance") for u in updates]),
            "positive_fraction": (
                sum(1 for u in updates if isinstance(u.get("days"), (int, float)) and u["days"] > 0)
                / len(updates) if updates else None
            ),
            "measured_update_ops_per_leg": (
                total_update_ops / total_update_samples if total_update_samples > 0 else None
            ),
            "measured_update_samples": total_update_samples,
        },
        "build_history": {
            "build_count": len(builds),
            "any_endpoint_history_count": history_any,
            "both_endpoints_history_count": history_both,
            "any_endpoint_history_fraction": history_any / len(builds) if builds else None,
            "both_endpoints_history_fraction": history_both / len(builds) if builds else None,
            "hub_delay_sum_days": stat(delay_sums),
        },
        "selected_engine_live_timing_replay": {
            "scope": "same engine as built; exact inter-engine economic ranking is not reconstructible from this artifact",
            "line_count": len(replay_rows),
            "fleet_changed_count": sum(
                1 for r in replay_rows if r["planes_original"] != r["planes_adapted"]),
            "fleet_ratio": stat([r["fleet_ratio"] for r in replay_rows]),
            "revenue_ratio": stat([r["revenue_ratio"] for r in replay_rows]),
            "profit_ratio": stat([r["profit_ratio"] for r in replay_rows]),
            "score_ratio": stat([r["score_ratio"] for r in replay_rows]),
            "profit_delta": stat([r["profit_delta"] for r in replay_rows]),
            "score_delta": stat([r["score_delta"] for r in replay_rows]),
            "live_over_build_oneway": stat([
                ratio(r["oneway_live"], r["oneway_build"]) for r in replay_rows
            ]),
        },
        "engine_timing_note": (
            "hubDelay(A)+hubDelay(B) is added as the same engine-independent constant to every candidate round-trip; "
            "therefore the learned term itself cannot favor a particular engine, although economics may still change "
            "because the relative value of speed changes."
        ),
        "mature_live_leg_ratio_by_route_growth": {
            key: stat(values) for key, values in sorted(live_growth.items())
        },
        "mature_quality_by_ready_endpoints_at_build": {
            key: {
                "n": len(rows),
                "leg_build": stat([row.get("leg_build") for row in rows]),
                "leg_live": stat([row.get("leg_live") for row in rows]),
                "total": stat([row.get("total") for row in rows]),
                "revenue": stat([row.get("revenue") for row in rows]),
                "profit": stat([row.get("profit") for row in rows]),
                "decision_fleet": stat([row.get("decision_fleet") for row in rows]),
            }
            for key, rows in sorted(history_quality.items())
        },
    }
    if summary_payload is not None:
        compact_growth = {}
        for bucket, row in summary_payload.get("by_route_growth", {}).items():
            compact_growth[bucket] = {
                "line_count": row.get("line_count"),
                "total_median": row.get("actual_over_pred_total", {}).get("median"),
                "leg_median": row.get("actual_over_pred_leg_days", {}).get("median"),
                "headway_median": row.get("actual_over_pred_headway", {}).get("median"),
                "revenue_median": row.get("actual_over_pred_revenue", {}).get("median"),
                "profit_median": row.get("actual_over_pred_profit", {}).get("median"),
            }
        result["route_growth"] = compact_growth
    if age_payload is not None:
        result["age_windows_all"] = {
            name: data.get("ALL", {}) for name, data in age_payload.items()
        }
    out = args.out or args.input.with_name(args.input.stem + "_hub_delay.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Sortie: {out}")


if __name__ == "__main__":
    main()
