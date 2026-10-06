#!/usr/bin/env python3
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SEEDS4 = (999, 802204, 983759, 230185)

CAMPAIGNS = {
    "fastpath2": (
        "rail_origin_reuse_freight_fastpath2_autopsy_4x5_20261005_r4",
        "origin_reuse_freight_fastpath2",
    ),
    "full40": (
        "rail_origin_reuse_fallback_gateA5_20261005",
        "origin_reuse_fallback",
    ),
    "freight40": (
        "rail_origin_reuse_freight_only_gateA5_20261005_r2",
        "origin_reuse_freight_only",
    ),
    "pax40": (
        "rail_origin_reuse_pax_only_gateA5_20261005",
        "origin_reuse_pax_only",
    ),
    "current40": (
        "rail_origin_reuse_onepass_compact_gateA5_20261005",
        "origin_reuse_freight_onepass_compact",
    ),
    "currentB": (
        "rail_origin_reuse_onepass_compact_gateB_20261005",
        "origin_reuse_freight_onepass_compact",
    ),
}


def compact_row(row):
    modes = row.get("primary_vehicles_by_mode") or {}
    stations = row.get("stations_by_facility") or {}
    return {
        "profit_year": row.get("profit_year"),
        "company_value": row.get("company_value"),
        "rail": modes.get("rail"),
        "air": modes.get("air"),
        "road": modes.get("road"),
        "rail_stations": stations.get("rail"),
        "airports": row.get("air_airports"),
        "stations": row.get("n_stations"),
        "airport_slots_opex": row.get("airport_slots_opex"),
        "airport_slots_aaahogex": row.get("airport_slots_aaahogex"),
        "airport_towns_opex_present": row.get("airport_towns_opex_present"),
        "airport_towns_aaahogex_present": row.get("airport_towns_aaahogex_present"),
        "project_builds": row.get("project_builds_sign_total"),
    }


def load_monthly(stem, seeds=None):
    path = RESULTS / f"{stem}.jsonl"
    wanted = set(seeds) if seeds is not None else None
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            row = json.loads(raw)
            run = row.get("run") or []
            if len(run) < 2:
                continue
            seed = int(run[1])
            if wanted is not None and seed not in wanted:
                continue
            policy = row.get("duel_policy_id")
            slot = row.get("company_slot")
            date = row.get("date")
            if policy is None or slot not in (0, 1) or not date:
                continue
            data[policy][seed][slot][date] = compact_row(row)
    return data


def delta(a, b, key):
    av = a.get(key) if a else None
    bv = b.get(key) if b else None
    if av is None or bv is None:
        return None
    return av - bv


def monthly_effect(data, variant, seed):
    ref = data["reference"][seed]
    var = data[variant][seed]
    dates = sorted(set(ref[0]) & set(ref[1]) & set(var[0]) & set(var[1]))
    out = []
    for date in dates:
        ro = ref[0][date]
        ra = ref[1][date]
        vo = var[0][date]
        va = var[1][date]
        op = delta(vo, ro, "profit_year")
        aa = delta(va, ra, "profit_year")
        gap = None if op is None or aa is None else op - aa
        row = {
            "date": date,
            "profit_delta": op,
            "aaa_profit_delta": aa,
            "gap_evolution": gap,
            "company_value_delta": delta(vo, ro, "company_value"),
            "rail_delta": delta(vo, ro, "rail"),
            "air_delta": delta(vo, ro, "air"),
            "road_delta": delta(vo, ro, "road"),
            "rail_station_delta": delta(vo, ro, "rail_stations"),
            "airports_delta": delta(vo, ro, "airports"),
            "stations_delta": delta(vo, ro, "stations"),
            "slots_delta": delta(vo, ro, "airport_slots_opex"),
            "opex_air_towns_delta": delta(vo, ro, "airport_towns_opex_present"),
            "aaa_air_towns_delta": delta(va, ra, "airport_towns_aaahogex_present"),
            "project_builds_delta": delta(vo, ro, "project_builds"),
        }
        out.append(row)
    return out


def terminal_pairs(stem):
    data = json.loads((RESULTS / f"{stem}.json").read_text(encoding="utf-8"))
    pc = data["policy_comparison"]
    pairs = {}
    for pair in pc.get("per_pair", []):
        if not pair.get("complete"):
            continue
        py = (pair.get("metrics") or {}).get("profit_year") or {}
        pv = (pair.get("metrics") or {}).get("primary_vehicles") or {}
        air = pair.get("air_structural_metrics") or {}
        pairs[int(pair["seed"])] = {
            "profit_delta": py.get("policy_delta"),
            "gap_evolution": py.get("duel_gap_evolution"),
            "vehicle_delta": pv.get("policy_delta"),
            "slots_delta": (air.get("airport_slots_opex") or {}).get("policy_delta"),
            "air_towns_delta": (air.get("airport_towns_opex_present") or {}).get("policy_delta"),
        }
    return data, pairs


EVENT_RE = re.compile(r"OPEX (\d{4}-\d+-\d+) ([A-Z0-9_]+)\s*(.*)$")


def event_summary(stem, variant, seed):
    path = RESULTS / f"{stem}_engine" / f"{variant}_seed{seed}_r0.log"
    if not path.exists():
        return None
    events = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = EVENT_RE.search(raw)
        if not m:
            continue
        date, kind, rest = m.groups()
        if (kind.startswith("RAIL_ORIGIN_REUSE") or kind in {
            "PROJECT_CHOSEN", "RAIL_ATTEMPT", "RAIL_BUILD", "AIR_BUILD", "FREIGHT_CARGO_FALLBACK"
        }):
            events.append((date, kind, rest))
    by_kind = defaultdict(list)
    for e in events:
        by_kind[e[1]].append(e)
    return {
        "events": events,
        "first": {k: vals[0] for k, vals in by_kind.items()},
        "counts": {k: len(vals) for k, vals in sorted(by_kind.items())},
        "reuse_attempts": [e for e in events if e[1] == "RAIL_ATTEMPT" and "reuse=1" in e[2]],
        "reuse_builds": [e for e in events if e[1] == "RAIL_BUILD" and "reuse=1" in e[2]],
        "active_fallbacks": [
            e for e in events if e[1].startswith("RAIL_ORIGIN_REUSE")
            and any(token in e[2] for token in ("preflight=1", "reuse_total=1", "admitted=1", "queued=1"))
        ],
    }


def project_signature(event):
    rest = event[2]
    fields = dict(token.split("=", 1) for token in rest.split() if "=" in token)
    return tuple(fields.get(k) for k in ("mode", "kind", "cargo", "src", "dst"))


def first_project_divergence(stem, variant, seed):
    base = RESULTS / f"{stem}_engine"
    ref_path = base / f"reference_seed{seed}_r0.log"
    var_path = base / f"{variant}_seed{seed}_r0.log"
    def chosen(path):
        out = []
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = EVENT_RE.search(raw)
            if not m:
                continue
            date, kind, rest = m.groups()
            if kind == "PROJECT_CHOSEN":
                out.append((date, kind, rest))
        return out
    ref = chosen(ref_path)
    var = chosen(var_path)
    n = min(len(ref), len(var))
    for i in range(n):
        if project_signature(ref[i]) != project_signature(var[i]):
            return i, ref[i], var[i]
    if len(ref) != len(var):
        return n, ref[n] if n < len(ref) else None, var[n] if n < len(var) else None
    return None


def first_meaningful(series):
    keys = ("profit_delta", "gap_evolution", "rail_delta", "air_delta", "rail_station_delta", "airports_delta")
    for row in series:
        if any(row.get(k) not in (None, 0) for k in keys):
            return row
    return None


def main():
    loaded = {}
    terminals = {}
    meta = {}
    for name, (stem, variant) in CAMPAIGNS.items():
        data, pairs = terminal_pairs(stem)
        meta[name] = data
        terminals[name] = pairs
        seeds = SEEDS4 if name == "fastpath2" else None
        loaded[name] = load_monthly(stem, seeds)

    print("=== TERMINAL 4 SEEDS: FASTPATH2 -> CURRENT ===")
    for seed in SEEDS4:
        old = terminals["fastpath2"][seed]
        cur = terminals["current40"][seed]
        print(
            seed,
            "fast", old,
            "current", cur,
            "degrade_profit", cur["profit_delta"] - old["profit_delta"],
            "degrade_gap", cur["gap_evolution"] - old["gap_evolution"],
        )

    print("\n=== TERMINAL 40 SEEDS: FULL / PAX / FREIGHT / CURRENT ===")
    for seed in meta["current40"]["seeds"]:
        print(
            seed,
            "full", terminals["full40"].get(seed),
            "pax", terminals["pax40"].get(seed),
            "freight", terminals["freight40"].get(seed),
            "current", terminals["current40"].get(seed),
        )

    print("\n=== 40-SEED AGGREGATES / ZERO RATE ===")
    for campaign in ("full40", "pax40", "freight40", "current40"):
        pairs = terminals[campaign]
        profit = [v["profit_delta"] for v in pairs.values()]
        gap = [v["gap_evolution"] for v in pairs.values()]
        aaa = [p - g for p, g in zip(profit, gap)]
        zero = sum(p == 0 and g == 0 for p, g in zip(profit, gap))
        print(campaign,
              "profit_mean", statistics.mean(profit),
              "gap_mean", statistics.mean(gap),
              "aaa_profit_effect_mean", statistics.mean(aaa),
              "terminal_exact_zero", f"{zero}/{len(profit)}")

    print("\n=== SAME CODE RE-RUN: A5 vs B FIRST FIVE YEARS (20 COMMON SEEDS) ===")
    common = meta["currentB"]["seeds"]
    rerun_rows = []
    changed_seeds = 0
    ref_changed = 0
    var_changed = 0
    for seed in common:
        a = monthly_effect(loaded["current40"], CAMPAIGNS["current40"][1], seed)
        b = monthly_effect(loaded["currentB"], CAMPAIGNS["currentB"][1], seed)
        ad = {r["date"]: r for r in a if r["date"] <= "1974-12-01"}
        bd = {r["date"]: r for r in b if r["date"] <= "1974-12-01"}
        dates = sorted(set(ad) & set(bd))
        diffs = []
        for date in dates:
            pa, pb = ad[date]["profit_delta"], bd[date]["profit_delta"]
            ga, gb = ad[date]["gap_evolution"], bd[date]["gap_evolution"]
            if pa != pb or ga != gb or ad[date]["rail_delta"] != bd[date]["rail_delta"] or ad[date]["air_delta"] != bd[date]["air_delta"]:
                diffs.append(date)
        if diffs:
            changed_seeds += 1
        raw_ref_a = loaded["current40"]["reference"][seed]
        raw_ref_b = loaded["currentB"]["reference"][seed]
        raw_var_a = loaded["current40"][CAMPAIGNS["current40"][1]][seed]
        raw_var_b = loaded["currentB"][CAMPAIGNS["currentB"][1]][seed]
        def arm_changed(aa, bb):
            dates2 = sorted(set(aa[0]) & set(aa[1]) & set(bb[0]) & set(bb[1]))
            for d in dates2:
                if d > "1974-12-01": continue
                for slot in (0, 1):
                    for key in ("profit_year", "company_value", "rail", "air", "stations"):
                        if aa[slot][d].get(key) != bb[slot][d].get(key):
                            return d
            return None
        ref_first = arm_changed(raw_ref_a, raw_ref_b)
        var_first = arm_changed(raw_var_a, raw_var_b)
        if ref_first: ref_changed += 1
        if var_first: var_changed += 1
        lasta = ad.get("1974-12-01", {})
        lastb = bd.get("1974-12-01", {})
        rerun_rows.append({
            "seed": seed,
            "first_difference": diffs[0] if diffs else None,
            "reference_first_rerun_difference": ref_first,
            "variant_first_rerun_difference": var_first,
            "a_profit_delta_1974_12": lasta.get("profit_delta"),
            "b_profit_delta_1974_12": lastb.get("profit_delta"),
            "a_gap_1974_12": lasta.get("gap_evolution"),
            "b_gap_1974_12": lastb.get("gap_evolution"),
            "a_rail_1974_12": lasta.get("rail_delta"),
            "b_rail_1974_12": lastb.get("rail_delta"),
            "a_air_1974_12": lasta.get("air_delta"),
            "b_air_1974_12": lastb.get("air_delta"),
        })
        print(rerun_rows[-1])
    print("same-code rerun seeds differing within five years:", changed_seeds, "/", len(common))
    print("reference policy raw rerun differences:", ref_changed, "/", len(common))
    print("variant policy raw rerun differences:", var_changed, "/", len(common))
    out_rerun = RESULTS / "rail_origin_reuse_same_code_rerun_20seed_20261005.csv"
    with out_rerun.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rerun_rows[0]))
        writer.writeheader(); writer.writerows(rerun_rows)
    print("WROTE", out_rerun)

    print("\n=== CURRENT B TERMINAL 10Y ON REPEAT-STABLE 5Y SEEDS ===")
    for seed in (100, 12345, 17, 4096, 65537, 54321, 512, 1024):
        print(seed, terminals["currentB"].get(seed))

    long_rows = []
    print("\n=== CURRENT B YEAR-END TRAJECTORIES ===")
    for seed in (100, 12345, 17, 4096, 65537, 54321, 512, 1024):
        series = monthly_effect(loaded["currentB"], CAMPAIGNS["currentB"][1], seed)
        prev_sign = 0
        turns = []
        for row in series:
            long_rows.append({"seed": seed, **row})
            gap = row.get("gap_evolution")
            sign = 0 if gap in (None, 0) else (1 if gap > 0 else -1)
            if sign != 0 and sign != prev_sign:
                turns.append((row["date"], gap))
                prev_sign = sign
        print("SEED", seed, "turns", turns)
        for row in series:
            if row["date"].endswith("-12-01"):
                print(" ", row["date"], "profit", row["profit_delta"], "AAA", row["aaa_profit_delta"],
                      "gap", row["gap_evolution"], "rail", row["rail_delta"], "air", row["air_delta"])
    out_long = RESULTS / "rail_origin_reuse_currentB_selected_monthly_20261005.csv"
    with out_long.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(long_rows[0]))
        writer.writeheader(); writer.writerows(long_rows)
    print("WROTE", out_long)

    report_rows = []
    compare_rows = []
    print("\n=== MONTHLY TURNING POINTS ON 4 FASTPATH2 SEEDS ===")
    for seed in SEEDS4:
        old_series = monthly_effect(loaded["fastpath2"], CAMPAIGNS["fastpath2"][1], seed)
        cur_series = monthly_effect(loaded["current40"], CAMPAIGNS["current40"][1], seed)
        old_by_date = {r["date"]: r for r in old_series}
        cur_by_date = {r["date"]: r for r in cur_series}
        print("SEED", seed, "first_fast", first_meaningful(old_series), "first_current", first_meaningful(cur_series))
        dates = sorted(set(old_by_date) & set(cur_by_date))
        worst = []
        for date in dates:
            o = old_by_date[date]
            c = cur_by_date[date]
            dp = None if o["profit_delta"] is None or c["profit_delta"] is None else c["profit_delta"] - o["profit_delta"]
            dg = None if o["gap_evolution"] is None or c["gap_evolution"] is None else c["gap_evolution"] - o["gap_evolution"]
            compare_rows.append({
                "seed": seed, "date": date,
                "fast_profit_delta": o["profit_delta"], "current_profit_delta": c["profit_delta"],
                "profit_effect_change": dp,
                "fast_gap_evolution": o["gap_evolution"], "current_gap_evolution": c["gap_evolution"],
                "gap_effect_change": dg,
                "fast_rail_delta": o["rail_delta"], "current_rail_delta": c["rail_delta"],
                "fast_air_delta": o["air_delta"], "current_air_delta": c["air_delta"],
                "fast_rail_station_delta": o["rail_station_delta"], "current_rail_station_delta": c["rail_station_delta"],
                "fast_airports_delta": o["airports_delta"], "current_airports_delta": c["airports_delta"],
            })
            if dp is not None or dg is not None:
                score = max(abs(dp or 0), abs(dg or 0))
                worst.append((score, date, dp, dg, o, c))
        for item in sorted(worst, reverse=True)[:6]:
            _, date, dp, dg, o, c = item
            print(" ", date, "change_profit", dp, "change_gap", dg,
                  "fast(P,G,R,A)", (o["profit_delta"], o["gap_evolution"], o["rail_delta"], o["air_delta"]),
                  "cur(P,G,R,A)", (c["profit_delta"], c["gap_evolution"], c["rail_delta"], c["air_delta"]))

        for campaign in ("fastpath2", "current40"):
            series = old_series if campaign == "fastpath2" else cur_series
            for row in series:
                report_rows.append({"campaign": campaign, "seed": seed, **row})

    out = RESULTS / "rail_origin_reuse_monthly_causal_20261005.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(report_rows[0]))
        writer.writeheader()
        writer.writerows(report_rows)
    out2 = RESULTS / "rail_origin_reuse_fastpath2_vs_current_monthly_20261005.csv"
    with out2.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(compare_rows[0]))
        writer.writeheader()
        writer.writerows(compare_rows)
    print("\nWROTE", out)
    print("WROTE", out2)

    monthly40_rows = []
    seed40_rows = []
    monthly40_seed_rows = []
    print("\n=== MONTHLY 40-SEED MEANS (YEAR-END + FIRST/LAST EFFECT) ===")
    for campaign in ("full40", "pax40", "freight40", "current40"):
        variant = CAMPAIGNS[campaign][1]
        series_by_seed = {}
        for seed in meta[campaign]["seeds"]:
            series_by_seed[seed] = monthly_effect(loaded[campaign], variant, seed)
            for row in series_by_seed[seed]:
                monthly40_seed_rows.append({"campaign": campaign, "seed": seed, **row})
            first = first_meaningful(series_by_seed[seed])
            last = series_by_seed[seed][-1] if series_by_seed[seed] else {}
            seed40_rows.append({
                "campaign": campaign,
                "seed": seed,
                "first_effect_date": first["date"] if first else None,
                "terminal_profit_delta": terminals[campaign][seed]["profit_delta"],
                "terminal_gap_evolution": terminals[campaign][seed]["gap_evolution"],
                "terminal_rail_delta": last.get("rail_delta"),
                "terminal_air_delta": last.get("air_delta"),
                "terminal_rail_station_delta": last.get("rail_station_delta"),
                "terminal_airports_delta": last.get("airports_delta"),
            })
        dates = sorted({r["date"] for series in series_by_seed.values() for r in series})
        date_rows = {seed: {r["date"]: r for r in series} for seed, series in series_by_seed.items()}
        aggregates = []
        for date in dates:
            rows = [date_rows[s][date] for s in date_rows if date in date_rows[s]]
            def mean_key(key):
                vals = [r[key] for r in rows if r.get(key) is not None]
                return statistics.mean(vals) if vals else None
            agg = {
                "campaign": campaign,
                "date": date,
                "n": len(rows),
                "profit_delta_mean": mean_key("profit_delta"),
                "aaa_profit_delta_mean": mean_key("aaa_profit_delta"),
                "gap_evolution_mean": mean_key("gap_evolution"),
                "rail_delta_mean": mean_key("rail_delta"),
                "air_delta_mean": mean_key("air_delta"),
                "rail_station_delta_mean": mean_key("rail_station_delta"),
                "airports_delta_mean": mean_key("airports_delta"),
                "slots_delta_mean": mean_key("slots_delta"),
            }
            monthly40_rows.append(agg)
            aggregates.append(agg)
        nonzero = [a for a in aggregates if any(a.get(k) not in (None, 0) for k in
                   ("profit_delta_mean", "gap_evolution_mean", "rail_delta_mean", "air_delta_mean"))]
        print(campaign, "first_mean_effect", nonzero[0] if nonzero else None)
        for agg in aggregates:
            if agg["date"].endswith("-12-01"):
                print(" ", agg)

        gaps = []
        profits = []
        rails = []
        airs = []
        for seed, series in series_by_seed.items():
            if not series:
                continue
            last = series[-1]
            g = terminals[campaign][seed]["gap_evolution"]
            p = terminals[campaign][seed]["profit_delta"]
            r = last.get("rail_delta")
            a = last.get("air_delta")
            if None not in (g, p, r, a):
                gaps.append(g); profits.append(p); rails.append(r); airs.append(a)
        def corr(x, y):
            try:
                return statistics.correlation(x, y)
            except Exception:
                return None
        print(" ", campaign, "corr gap/rail", corr(gaps, rails), "gap/air", corr(gaps, airs),
              "profit/rail", corr(profits, rails), "profit/air", corr(profits, airs))

    out3 = RESULTS / "rail_origin_reuse_40seed_monthly_effects_20261005.csv"
    with out3.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(monthly40_rows[0]))
        writer.writeheader()
        writer.writerows(monthly40_rows)
    out4 = RESULTS / "rail_origin_reuse_40seed_seed_summary_20261005.csv"
    with out4.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(seed40_rows[0]))
        writer.writeheader()
        writer.writerows(seed40_rows)
    out5 = RESULTS / "rail_origin_reuse_40seed_monthly_by_seed_20261005.csv"
    with out5.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(monthly40_seed_rows[0]))
        writer.writeheader()
        writer.writerows(monthly40_seed_rows)
    print("WROTE", out3)
    print("WROTE", out4)
    print("WROTE", out5)

    print("\n=== EVENT SUMMARIES (decision_log campaigns) ===")
    for seed in SEEDS4:
        old = event_summary(CAMPAIGNS["fastpath2"][0], CAMPAIGNS["fastpath2"][1], seed)
        cur = event_summary("rail_origin_reuse_onepass_autopsy_4x5_20261005_r10", "origin_reuse_freight_onepass", seed)
        print("SEED", seed)
        print(" FAST counts", old["counts"] if old else None)
        print(" FAST first", old["first"] if old else None)
        print(" FAST first active fallback", old["active_fallbacks"][0] if old and old["active_fallbacks"] else None)
        print(" FAST reuse attempts/builds", len(old["reuse_attempts"]) if old else None,
              len(old["reuse_builds"]) if old else None)
        print(" FAST first project divergence", first_project_divergence(CAMPAIGNS["fastpath2"][0], CAMPAIGNS["fastpath2"][1], seed))
        print(" CUR counts", cur["counts"] if cur else None)
        print(" CUR first", cur["first"] if cur else None)
        print(" CUR first active fallback", cur["active_fallbacks"][0] if cur and cur["active_fallbacks"] else None)
        print(" CUR reuse attempts/builds", len(cur["reuse_attempts"]) if cur else None,
              len(cur["reuse_builds"]) if cur else None)
        print(" CUR first project divergence", first_project_divergence("rail_origin_reuse_onepass_autopsy_4x5_20261005_r10", "origin_reuse_freight_onepass", seed))


if __name__ == "__main__":
    main()
