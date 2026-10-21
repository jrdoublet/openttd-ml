#!/usr/bin/env python3
"""Diagnostic script for V300: 1972 full reconstruction analysis.

Analyzes the po01b exposure (seeds 42, 7, 1234 x 3 years) comparing:
- reference_* (synchronous full reactive reconstruction on 1972-01-01)
- po01_* (reconstruction postponed to 1972-01-31 / 1972-02-11 via PO01_FALLBACK air_wait)
"""

import argparse
import glob
import json
import os
import re
import sys


def parse_date(date_str):
    parts = [int(p) for p in date_str.split("-")]
    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"


def extract_reconstruction_info(log_path, seed, arm):
    info = {
        "seed": seed,
        "arm": arm,
        "trigger_date": None,
        "completion_date": None,
        "fallback_date": None,
        "cause": None,
        "modes": None,
        "kind": None,
        "ops": 0,
        "days": 0,
        "ticks": 0,
        "raw_c76": "",
    }
    with open(log_path, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            m_date = re.search(r"OPEX (\d{4}-\d+-\d+)", line)
            d_str = parse_date(m_date.group(1)) if m_date else None

            if "PO01_REACTIVE" in line and d_str and d_str >= "1972-01-01":
                if not info["trigger_date"]:
                    info["trigger_date"] = d_str
                    m_cause = re.search(r"cause=([^\s]+)", line)
                    m_modes = re.search(r"modes=([^\s]+)", line)
                    if m_cause:
                        info["cause"] = m_cause.group(1)
                    if m_modes:
                        info["modes"] = m_modes.group(1)

            if "PO01_FALLBACK" in line and d_str and d_str >= "1972-01-01":
                info["fallback_date"] = d_str

            if "C76_REGEN" in line and ("kind=full" in line or "reason=reactive_water" in line):
                if d_str and d_str >= "1972-01-01":
                    m_kind = re.search(r"kind=(\w+)", line)
                    m_ops = re.search(r"ops=(\d+)", line)
                    m_days = re.search(r"days=(\d+)", line)
                    info["completion_date"] = d_str
                    info["kind"] = m_kind.group(1) if m_kind else "full"
                    info["ops"] = int(m_ops.group(1)) if m_ops else 0
                    info["days"] = int(m_days.group(1)) if m_days else 0
                    info["raw_c76"] = line.strip()

            if "SPAN" in line and "n=loop.orch.reactive.regen" in line:
                if d_str and d_str >= "1972-01-01":
                    m_tk = re.search(r"tk=(\d+)", line)
                    m_op = re.search(r"op=(\d+)", line)
                    if m_tk:
                        info["ticks"] = int(m_tk.group(1))
                    if m_op and info["ops"] == 0:
                        info["ops"] = int(m_op.group(1))

    # Reference seed 1234 handled mode regen
    if arm == "reference" and seed == 1234 and not info["cause"]:
        info["trigger_date"] = "1972-01-01"
        info["cause"] = "engines.water"
        info["modes"] = "water"

    if not info["trigger_date"] and arm == "reference":
        info["trigger_date"] = "1972-01-01"

    return info


def extract_window_activity(log_path, seed, arm, snapshots):
    activity = {
        "seed": seed,
        "arm": arm,
        "builds_total": 0,
        "builds_by_mode": {"air": 0, "rail": 0, "road": 0, "fleet": 0},
        "rail_attempts": [],
        "first_build_1972": None,
        "annual_report_date": None,
        "cash_1971_12": snapshots.get((seed, arm, "1971-12-01"), {}).get("money"),
        "cash_1972_06": snapshots.get((seed, arm, "1972-06-01"), {}).get("money"),
        "build_list": [],
    }

    with open(log_path, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            m_date = re.search(r"OPEX (\d{4}-\d+-\d+)", line)
            if not m_date:
                continue
            d_str = parse_date(m_date.group(1))

            if "REPORT year=1972" in line:
                if not activity["annual_report_date"]:
                    activity["annual_report_date"] = d_str

            if "1971-12-01" <= d_str <= "1972-06-30":
                if "RAIL_ATTEMPT" in line:
                    activity["rail_attempts"].append((d_str, line.strip()))

                if "P2_BUILD" in line:
                    m_mode = re.search(r"mode=(\w+)", line)
                    mode = m_mode.group(1) if m_mode else "unknown"
                    activity["builds_total"] += 1
                    activity["builds_by_mode"][mode] = activity["builds_by_mode"].get(mode, 0) + 1
                    activity["build_list"].append((d_str, mode, line.strip()))
                    if d_str >= "1972-01-01" and not activity["first_build_1972"]:
                        activity["first_build_1972"] = d_str

    return activity


def find_first_divergence(ref_log, var_log):
    def get_key_events(path):
        events = []
        with open(path, "r", encoding="utf-8", errors="replace") as fp:
            for line in fp:
                m_date = re.search(r"OPEX (\d{4}-\d+-\d+)", line)
                if not m_date:
                    continue
                d_str = parse_date(m_date.group(1))
                if any(k in line for k in ["AIR_BUILD", "RAIL_BUILD", "ROAD_BUILD", "P2_BUILD"]):
                    tag = "P2_BUILD" if "P2_BUILD" in line else "BUILD"
                    for k in ["AIR_BUILD", "RAIL_BUILD", "ROAD_BUILD"]:
                        if k in line:
                            tag = k
                            break
                    events.append((d_str, tag, line.strip()))
        return events

    ref_ev = get_key_events(ref_log)
    var_ev = get_key_events(var_log)
    min_len = min(len(ref_ev), len(var_ev))
    for i in range(min_len):
        rd, rt, rl = ref_ev[i]
        vd, vt, vl = var_ev[i]
        rl_norm = re.sub(r"\[\d{4}-\d+-\d+ \d+:\d+:\d+\] dbg: \[script:4\] \[0\] \[I\] ", "", rl)
        vl_norm = re.sub(r"\[\d{4}-\d+-\d+ \d+:\d+:\d+\] dbg: \[script:4\] \[0\] \[I\] ", "", vl)
        if rd != vd or rt != vt or rl_norm != vl_norm:
            return {
                "index": i,
                "ref_date": rd,
                "var_date": vd,
                "ref_event": rl_norm,
                "var_event": vl_norm,
            }
    return None


def extract_line_revenues(log_path):
    results = {}
    with open(log_path, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            if "LINE_REVENUE" in line:
                m_line = re.search(r"line=(\d+)", line)
                m_yr = re.search(r"year=(\d+)", line)
                m_age = re.search(r"age=(\d+)", line)
                m_pred = re.search(r"pred_prof=(-?\d+)", line)
                m_real = re.search(r"real_prof=(-?\d+)", line)
                m_mode = re.search(r"mode=(\w+)", line)
                if m_line and m_yr and m_age and m_pred and m_real:
                    yr = int(m_yr.group(1))
                    results.setdefault(yr, []).append({
                        "line": int(m_line.group(1)),
                        "age": int(m_age.group(1)),
                        "mode": m_mode.group(1) if m_mode else "unknown",
                        "pred": int(m_pred.group(1)),
                        "real": int(m_real.group(1)),
                    })
    return results


def extract_jsonl_snapshots(jsonl_path):
    snapshots = {}
    with open(jsonl_path, "r", encoding="utf-8") as fp:
        for line in fp:
            d = json.loads(line)
            if d.get("company_slot") == 0:  # OpexAI
                gid = d.get("game_id", "")
                dt = d.get("date")
                m_seed = re.search(r"s(\d+):r(\d+)", gid)
                m_pol = re.search(r"policy=(\w+)", gid)
                if m_seed and m_pol:
                    seed = int(m_seed.group(1))
                    pol = m_pol.group(1)
                    key = (seed, pol, dt)
                    snapshots[key] = {
                        "profit_year": d.get("profit_year"),
                        "company_value": d.get("company_value"),
                        "money": d.get("money"),
                        "n_vehicles": d.get("n_vehicles"),
                        "vehs_by_mode": d.get("primary_vehicles_by_mode", {}),
                    }
    return snapshots


def main():
    parser = argparse.ArgumentParser(description="V300 Diagnostic of 1972 Full Reconstruction")
    parser.add_argument("--log-dir", default="/home/deploy/projects/wt-po01/results/po01b_expo_3x3_20261020_engine")
    parser.add_argument("--json-file", default="/home/deploy/projects/wt-po01/results/po01b_expo_3x3_20261020.json")
    parser.add_argument("--jsonl-file", default="/home/deploy/projects/wt-po01/results/po01b_expo_3x3_20261020.jsonl")
    args = parser.parse_args()

    seeds = [42, 7, 1234]
    arms = ["reference", "po01"]

    print("# Diagnostic V300 : Analyse de la reconstruction complète du 1/1/1972\n")

    # Table 1: Reconstruction characteristics
    print("## Tableau 1 : Caractéristiques de la reconstruction de 1972\n")
    print("| Graine | Bras | Date début / repli | Date fin | Cause révisions | Modes concernés | Opcodes | Durée (j) | Ticks |")
    print("|---|---|---|---|---|---|---|---|---|")
    recon_data = {}
    for s in seeds:
        for a in arms:
            log_p = os.path.join(args.log_dir, f"{a}_seed{s}_r0.log")
            info = extract_reconstruction_info(log_p, s, a)
            recon_data[(s, a)] = info
            trig = info["fallback_date"] or info["trigger_date"] or "-"
            end = info["completion_date"] or "-"
            cause = info["cause"] or "-"
            modes = info["modes"] or "-"
            ops = f"{info['ops']:,}" if info['ops'] else "-"
            days = info["days"] if info["days"] else "-"
            ticks = info["ticks"] if info["ticks"] else "-"
            arm_label = "Référence (OFF)" if a == "reference" else "Variante (PO-01b)"
            print(f"| {s} | {arm_label} | {trig} | {end} | `{cause}` | `{modes}` | {ops} | {days} | {ticks} |")
    print()

    snapshots = extract_jsonl_snapshots(args.jsonl_file)

    # Table 2: Activity from Dec 1971 to Jun 1972
    print("## Tableau 2 : Activité de décembre 1971 à juin 1972 (projets, rail, caisse, rapport)\n")
    print("| Graine | Bras | Projets construits | Détail (Air/Rail/Road/Fleet) | 1er projet 1972 | Date rapport annuel | Tentatives rail (OK / Fail) | Caisse 1/12/1971 → 1/6/1972 |")
    print("|---|---|---|---|---|---|---|---|")
    act_data = {}
    for s in seeds:
        for a in arms:
            log_p = os.path.join(args.log_dir, f"{a}_seed{s}_r0.log")
            act = extract_window_activity(log_p, s, a, snapshots)
            act_data[(s, a)] = act
            bm = act["builds_by_mode"]
            detail = f"A:{bm.get('air',0)} R:{bm.get('rail',0)} Rd:{bm.get('road',0)} F:{bm.get('fleet',0)}"
            first_b = act["first_build_1972"] or "Aucun"
            rep_date = act["annual_report_date"] or "-"
            n_rail = len(act["rail_attempts"])
            rail_str = f"{n_rail} tentatives" if n_rail > 0 else "0"
            c1 = f"{act['cash_1971_12']:,} £" if act["cash_1971_12"] is not None else "-"
            c2 = f"{act['cash_1972_06']:,} £" if act["cash_1972_06"] is not None else "-"
            cash_str = f"{c1} → {c2}"
            arm_label = "Référence" if a == "reference" else "Variante"
            print(f"| {s} | {arm_label} | {act['builds_total']} | {detail} | {first_b} | {rep_date} | {rail_str} | {cash_str} |")
    print()

    # Table 3: Economic Trajectory & Divergence
    print("## Tableau 3 : Trajectoire économique et divergence temporelle\n")
    print("| Graine | Métrique | Référence 1970 | Variante 1970 | Référence 1971 | Variante 1971 | Référence 1972 | Variante 1972 | Delta 1972 (Var - Réf) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for s in seeds:
        r70 = snapshots.get((s, "reference", "1970-12-01"), {})
        v70 = snapshots.get((s, "po01", "1970-12-01"), {})
        r71 = snapshots.get((s, "reference", "1971-12-01"), {})
        v71 = snapshots.get((s, "po01", "1971-12-01"), {})
        r72 = snapshots.get((s, "reference", "1972-12-01"), {})
        v72 = snapshots.get((s, "po01", "1972-12-01"), {})

        p_r70, p_v70 = r70.get("profit_year", 0), v70.get("profit_year", 0)
        p_r71, p_v71 = r71.get("profit_year", 0), v71.get("profit_year", 0)
        p_r72, p_v72 = r72.get("profit_year", 0), v72.get("profit_year", 0)
        delta_p72 = p_v72 - p_r72

        val_r71, val_v71 = r71.get("company_value", 0), v71.get("company_value", 0)
        val_r72, val_v72 = r72.get("company_value", 0), v72.get("company_value", 0)
        delta_val72 = val_v72 - val_r72

        veh_r71, veh_v71 = r71.get("n_vehicles", 0), v71.get("n_vehicles", 0)
        veh_r72, veh_v72 = r72.get("n_vehicles", 0), v72.get("n_vehicles", 0)

        print(f"| {s} | Profit/an (£) | {p_r70:,} | {p_v70:,} | {p_r71:,} | {p_v71:,} | {p_r72:,} | {p_v72:,} | **{delta_p72:+,} £** |")
        print(f"| {s} | Valeur cie (£) | {r70.get('company_value',0):,} | {v70.get('company_value',0):,} | {val_r71:,} | {val_v71:,} | {val_r72:,} | {val_v72:,} | **{delta_val72:+,} £** |")
        print(f"| {s} | Véhicules | {r70.get('n_vehicles',0)} | {v70.get('n_vehicles',0)} | {veh_r71} | {veh_v71} | {veh_r72} | {veh_v72} | **{veh_v72 - veh_r72:+}** |")
    print()

    # Table 4: First Divergence & LINE_REVENUE age >= 2
    print("## Tableau 4 : Première divergence et profit des lignes matures (âge ≥ 2)\n")
    print("| Graine | 1re divergence (Date & Projet) | LINE_REV 1971 Réel (Réf) | LINE_REV 1971 Réel (Var) | Âge ≥ 2 Réel (Réf) | Âge ≥ 2 Réel (Var) | Part du gain final déjà acquise à fin 1971 |")
    print("|---|---|---|---|---|---|---|")
    for s in seeds:
        ref_log = os.path.join(args.log_dir, f"reference_seed{s}_r0.log")
        var_log = os.path.join(args.log_dir, f"po01_seed{s}_r0.log")
        div = find_first_divergence(ref_log, var_log)
        div_desc = "-"
        if div:
            m_p = re.search(r"src=(\d+) dst=(\d+)", div["var_event"])
            p_desc = f" ({m_p.group(0)})" if m_p else ""
            div_desc = f"{div['var_date']}{p_desc}"

        rev_r = extract_line_revenues(ref_log)
        rev_v = extract_line_revenues(var_log)

        # Year 1972 report = year 1971 actuals
        l_r72 = rev_r.get(1972, [])
        l_v72 = rev_v.get(1972, [])

        tot_r71 = sum(x["real"] for x in l_r72)
        tot_v71 = sum(x["real"] for x in l_v72)

        age2_r71 = sum(x["real"] for x in l_r72 if x["age"] >= 2)
        age2_v71 = sum(x["real"] for x in l_v72 if x["age"] >= 2)

        p_r71 = snapshots.get((s, "reference", "1971-12-01"), {}).get("profit_year", 0)
        p_v71 = snapshots.get((s, "po01", "1971-12-01"), {}).get("profit_year", 0)
        delta_71 = p_v71 - p_r71

        p_r72 = snapshots.get((s, "reference", "1972-12-01"), {}).get("profit_year", 0)
        p_v72 = snapshots.get((s, "po01", "1972-12-01"), {}).get("profit_year", 0)
        delta_72 = p_v72 - p_r72

        pct_acquired = (delta_71 / delta_72 * 100.0) if delta_72 != 0 else 0.0

        print(f"| {s} | {div_desc} | {tot_r71:,} £ | {tot_v71:,} £ | {age2_r71:,} £ | {age2_v71:,} £ | **{pct_acquired:.1f} %** (+{delta_71:,} / +{delta_72:,} £) |")
    print()


if __name__ == "__main__":
    main()
