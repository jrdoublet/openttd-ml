"""Summarize a frozen C66 RAIL-SEARCH-PRIO/LONG duel without modifying it.

Usage:
    python -X utf8 sweeps/analyse_rail_search_prio.py results/<campaign>.json

Reads only frozen JSON and per-arm engine logs. The comparison is *Opex ON -
Opex OFF*, never AAA ON - AAA OFF; AAA ratios are descriptive and can diverge
between otherwise paired games. A RAIL_SEARCH "OK" is a slice, not a line.
"""

import argparse
import collections
import json
import re
from pathlib import Path


BUILD = re.compile(
    r"OPEX (\d{4})-\d+-\d+ RAIL_BUILD .*?\btrains=(\d+)\b.*?\bwagons=(\d+)\b"
)
DATE = re.compile(r"OPEX (\d{4})-\d+-\d+ ")
DISCARD = re.compile(r"PROJECT_DISCARD .*?reason=search_in_progress")
SEARCH = re.compile(r"RAIL_SEARCH type=resumable outcome=OK")
PRIO_EVENT = re.compile(r"RAIL_SEARCH_PRIO event=([a-z_]+)\b.*?owner=([a-z_]+)")


def read_logs(path, policy, seed, repeat):
    filename = path.with_suffix("").with_name(path.stem + "_engine")
    log_path = filename / f"{policy}_seed{seed}_r{repeat}.log"
    found = collections.defaultdict(lambda: collections.Counter())
    built = collections.defaultdict(list)
    if not log_path.is_file():
        return found, built, log_path
    for line in log_path.open("r", encoding="utf-8", errors="replace"):
        date = DATE.search(line)
        if date is None:
            continue
        year = int(date.group(1))
        build = BUILD.search(line)
        if build:
            found[year]["builds"] += 1
            found[year]["initial_trains"] += int(build.group(2))
            built[year].append(int(build.group(3)))
        if DISCARD.search(line):
            found[year]["search_block_discards"] += 1
        if SEARCH.search(line):
            found[year]["search_ok_slices"] += 1
        event = PRIO_EVENT.search(line)
        if event:
            found[year][f"{event.group(1)}:{event.group(2)}"] += 1
    return found, built, log_path


def format_money(number):
    return f"{number:,.0f}".replace(",", " ")


def format_ci(values):
    if not values or len(values) != 2:
        return "n/a"
    return f"[{format_money(values[0])}; {format_money(values[1])}]"


def final_rail_lines(campaign, policy, seed, repeat):
    """Final observed Opex rail services; not the cumulative number opened."""
    snapshots = (
        s for s in campaign.get("line_telemetry", {}).get("snapshots", [])
        if s.get("duel_policy_id") == policy and s.get("arm") == "OpexAI"
        and int(s.get("seed", -1)) == seed
        and int(s.get("repeat", -1)) == repeat and s.get("ok")
    )
    last = max(snapshots, key=lambda s: s.get("date", ""), default=None)
    if last is None:
        return None
    lines = [line for line in last.get("lines", []) if line.get("mode") == "rail"]
    trains = sum(len(line.get("vehicle_ids", [])) for line in lines)
    return {
        "date": last["date"],
        "lines": len(lines),
        "trains": trains,
        "trains_per_line": (trains / len(lines)) if lines else 0,
        "max_trains": max((len(line.get("vehicle_ids", [])) for line in lines), default=0),
    }


def run(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    pc = data.get("policy_comparison")
    if pc is None:
        raise ValueError("This is not a C66 paired policy-comparison campaign")
    ref_name = pc["reference_policy_id"]
    on_name = pc["variant_policy_id"]
    pairs = [p for p in pc["per_pair"] if p["complete"]]
    delta = pc["aggregates"]["profit_year"]["policy_delta"]
    print(f"# {path.stem}")
    print(
        f"Source SHA: `{data.get('source_bundle_sha256', '?')}`; "
        f"years={data.get('years')}; seeds={data.get('seeds')}; "
        f"complete_pairs={len(pairs)}; verdict={pc.get('verdict')}."
    )
    print(
        "Delta profit Opex: mean **"
        f"{format_money(delta['mean'])} £/an**, V/D/N = "
        f"{delta['wins']}/{delta['losses']}/{delta['ties']}, "
        f"Wilcoxon p={delta['wilcoxon_p']}, bootstrap IC95="
        f"{format_ci(delta['mean_bootstrap_95pct_ci'])} £/an."
    )
    print()
    print("| Seed | REF Opex | ON Opex | Δ profit | REF AAA | ON AAA | Opex/AAA REF→ON |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for pair in pairs:
        m = pair["metrics"]["profit_year"]
        ref = m["reference_opex"]
        on = m["variant_opex"]
        ref_aaa = m["reference_aaahogex"]
        on_aaa = m["variant_aaahogex"]
        rat = f"{100 * ref / ref_aaa:.1f}%→{100 * on / on_aaa:.1f}%" if ref_aaa > 0 and on_aaa > 0 else "n/a"
        print(
            f"| {pair['seed']} | {format_money(ref)} | {format_money(on)} | "
            f"{format_money(m['policy_delta'])} | {format_money(ref_aaa)} | "
            f"{format_money(on_aaa)} | {rat} |"
        )
    print()
    print("| Seed | Final rail lines REF/ON | Trains REF/ON | Trains per line REF/ON | Max trains per line REF/ON |")
    print("|---:|---:|---:|---:|---:|")
    for pair in pairs:
        a = final_rail_lines(data, ref_name, pair["seed"], pair["repeat"])
        b = final_rail_lines(data, on_name, pair["seed"], pair["repeat"])
        if a is None or b is None:
            print(f"| {pair['seed']} | unavailable | unavailable | unavailable | unavailable |")
            continue
        print(
            f"| {pair['seed']} | {a['lines']}/{b['lines']} | {a['trains']}/{b['trains']} | "
            f"{a['trains_per_line']:.2f}/{b['trains_per_line']:.2f} | "
            f"{a['max_trains']}/{b['max_trains']} |"
        )
    print()
    print("| Seed | Year | Lines REF/ON | Blocked REF/ON | Search slices REF/ON | Wagons built REF/ON (mean) |")
    print("|---:|---:|---:|---:|---:|---|")
    missing = []
    totals = collections.Counter()
    for pair in pairs:
        seed = pair["seed"]
        repeat = pair["repeat"]
        ref, ref_w, ref_path = read_logs(path, ref_name, seed, repeat)
        on, on_w, on_path = read_logs(path, on_name, seed, repeat)
        for path_ in (ref_path, on_path):
            if not path_.is_file():
                missing.append(str(path_))
        for year in sorted(set(ref) | set(on)):
            a, b = ref[year], on[year]
            aw, bw = ref_w[year], on_w[year]
            avg = lambda values: (f"{sum(values)/len(values):.1f}" if values else "—")
            print(
                f"| {seed} | {year} | {a['builds']}/{b['builds']} | "
                f"{a['search_block_discards']}/{b['search_block_discards']} | "
                f"{a['search_ok_slices']}/{b['search_ok_slices']} | {avg(aw)}/{avg(bw)} |"
            )
            totals["build_ref"] += a["builds"]
            totals["build_on"] += b["builds"]
            totals["blocked_ref"] += a["search_block_discards"]
            totals["blocked_on"] += b["search_block_discards"]
            for key, value in b.items():
                if ":" in key:
                    totals[key] += value
    print(
        f"\nAggregate lines REF/ON {totals['build_ref']}/{totals['build_on']}; "
        f"PROJECT_DISCARD search_in_progress REF/ON "
        f"{totals['blocked_ref']}/{totals['blocked_on']}."
    )
    if any(":" in key for key in totals):
        print("\nInstrumentation ON owner events:")
        for key, value in sorted(totals.items()):
            if ":" in key:
                print(f"- {key}: {value}")
    if missing:
        print("\nWARNING missing engine logs (cannot infer zero actions):")
        for filename in missing:
            print(f"- {filename}")
    return not missing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.campaign) else 2)
