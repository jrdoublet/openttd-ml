#!/usr/bin/env python3
"""
diag_notrain_adapt400.py - Autopsie des échecs NOTRAIN sous adapt400 vs Master
Analyse détaillée des 10 occurrences NOTRAIN sous v294_rail_weight_adapt=400 et de l'unique occurrence de master
sur les journaux du banc v299 (3 graines x 10 ans, partie complète).
"""

import os
import sys
import glob
import re
import gzip
import argparse
from typing import Dict, List, Any, Optional

DEFAULT_DIR = "/home/deploy/projects/wt-v299/results/v299_diag_3x10_20261021_engine"

def open_log(path: str):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "r", encoding="utf-8", errors="ignore")

def parse_line_tokens(line: str) -> Dict[str, str]:
    tokens = {}
    for part in line.strip().split():
        if "=" in part:
            k, v = part.split("=", 1)
            tokens[k] = v
    return tokens

def find_notrain_events(log_dir: str) -> List[Dict[str, Any]]:
    pattern = os.path.join(log_dir, "*.log*")
    files = sorted(glob.glob(pattern))
    events = []

    for fpath in files:
        fname = os.path.basename(fpath)
        arm = "reference" if "reference" in fname else ("v299" if "v299" in fname else "unknown")
        m_seed = re.search(r"seed(\d+)", fname)
        seed = int(m_seed.group(1)) if m_seed else 0

        with open_log(fpath) as f:
            all_lines = f.readlines()

        for idx, line in enumerate(all_lines):
            if "[0]" in line and "RAIL_ATTEMPT" in line and "reason=NOTRAIN" in line:
                tokens = parse_line_tokens(line)
                date_match = re.search(r"OPEX\s+([\d\-]+)\s+RAIL_ATTEMPT", line)
                date_str = date_match.group(1) if date_match else ""
                
                # Look for corresponding RAIL_BUILD_FAIL right next to it
                build_fail_line = ""
                build_fail_error = None
                build_fail_iters = None
                build_fail_budget = None
                for offset in range(1, 5):
                    if idx + offset < len(all_lines):
                        next_line = all_lines[idx + offset]
                        if "RAIL_BUILD_FAIL" in next_line:
                            build_fail_line = next_line.strip()
                            bf_tokens = parse_line_tokens(next_line)
                            build_fail_error = int(bf_tokens.get("error", -1))
                            build_fail_iters = int(bf_tokens.get("iters", -1))
                            build_fail_budget = int(bf_tokens.get("budget", -1))
                            break

                # Extract last 200 lines belonging to company [0]
                co0_lines = []
                for b_idx in range(idx - 1, -1, -1):
                    if "[0]" in all_lines[b_idx]:
                        co0_lines.append((b_idx + 1, all_lines[b_idx].strip()))
                        if len(co0_lines) >= 200:
                            break
                co0_lines.reverse()

                # Extract bank cash from preceding [0] lines
                cash_found = None
                cash_date = None
                for lno, text in reversed(co0_lines):
                    if "live_budget=" in text:
                        m_cash = re.search(r"live_budget=(\d+)", text)
                        if m_cash:
                            cash_found = int(m_cash.group(1))
                            m_d = re.search(r"OPEX\s+([\d\-]+)\s+", text)
                            cash_date = m_d.group(1) if m_d else ""
                            break
                    elif "money=" in text:
                        m_cash = re.search(r"money=(\d+)", text)
                        if m_cash:
                            cash_found = int(m_cash.group(1))
                            m_d = re.search(r"OPEX\s+([\d\-]+)\s+", text)
                            cash_date = m_d.group(1) if m_d else ""
                            break

                # If not found in 200 lines, search further back for cash
                if cash_found is None:
                    for b_idx in range(idx - 1, -1, -1):
                        text = all_lines[b_idx]
                        if "[0]" in text:
                            if "live_budget=" in text:
                                m_cash = re.search(r"live_budget=(\d+)", text)
                                if m_cash:
                                    cash_found = int(m_cash.group(1))
                                    m_d = re.search(r"OPEX\s+([\d\-]+)\s+", text)
                                    cash_date = m_d.group(1) if m_d else ""
                                    break
                            elif "money=" in text:
                                m_cash = re.search(r"money=(\d+)", text)
                                if m_cash:
                                    cash_found = int(m_cash.group(1))
                                    m_d = re.search(r"OPEX\s+([\d\-]+)\s+", text)
                                    cash_date = m_d.group(1) if m_d else ""
                                    break

                # Find PROJECT_CHOSEN by searching backwards through all previous lines
                chosen_cargo = None
                chosen_cost = None
                chosen_profit = None
                chosen_roi = None
                src = int(tokens.get("src", 0))
                dst = int(tokens.get("dst", 0))

                for b_idx in range(idx - 1, -1, -1):
                    text = all_lines[b_idx]
                    if "[0]" in text and "PROJECT_CHOSEN" in text and f"src={src}" in text and f"dst={dst}" in text:
                        ch_tokens = parse_line_tokens(text)
                        chosen_cargo = ch_tokens.get("cargo", "")
                        chosen_cost = int(ch_tokens.get("cost", 0))
                        chosen_profit = int(ch_tokens.get("profit", 0))
                        chosen_roi = int(ch_tokens.get("roi", 0))
                        break

                events.append({
                    "file": fname,
                    "filepath": fpath,
                    "arm": arm,
                    "seed": seed,
                    "line_no": idx + 1,
                    "raw_attempt": line.strip(),
                    "date": date_str,
                    "src": src,
                    "dst": dst,
                    "src_coord": (src % 256, src // 256),
                    "dst_coord": (dst % 256, dst // 256),
                    "kind": tokens.get("kind", ""),
                    "cargo": chosen_cargo if chosen_cargo else "UNKNOWN",
                    "manh": int(tokens.get("manh", 0)),
                    "route_len": int(tokens.get("len", -1)),
                    "pred_profit": int(tokens.get("pred_profit", 0)),
                    "pred_roi": int(tokens.get("pred_roi", 0)),
                    "pre_capital": int(tokens.get("pre", 0)),
                    "model_capital": int(tokens.get("model", 0)),
                    "quote_capital": int(tokens.get("quote", 0)),
                    "actual_cost": int(tokens.get("actual", 0)),
                    "iters": int(tokens.get("iters", 0)),
                    "opcodes": int(tokens.get("ops", 0)),
                    "search_ops": int(tokens.get("search_ops", 0)),
                    "weight": int(tokens.get("weight", 0)),
                    "adapt": tokens.get("adapt", "-"),
                    "build_fail_error": build_fail_error,
                    "build_fail_iters": build_fail_iters,
                    "build_fail_budget": build_fail_budget,
                    "build_fail_raw": build_fail_line,
                    "preceding_cash": cash_found,
                    "preceding_cash_date": cash_date,
                    "preceding_200_lines": co0_lines,
                })

    return events

def analyze_subsequent_history(events: List[Dict[str, Any]], log_dir: str):
    """Vérifie si les gares ou voies sont réutilisées plus tard ou si elles ont été démolies."""
    for ev in events:
        fpath = ev["filepath"]
        src = ev["src"]
        dst = ev["dst"]
        line_no = ev["line_no"]

        with open_log(fpath) as f:
            all_lines = f.readlines()

        later_attempts = []
        later_builds = []
        for idx in range(line_no, len(all_lines)):
            line = all_lines[idx]
            if "[0]" in line:
                if f"src={src}" in line or f"dst={dst}" in line or f"src={dst}" in line or f"dst={src}" in line:
                    if "RAIL_ATTEMPT" in line:
                        later_attempts.append((idx + 1, line.strip()))
                    elif "RAIL_BUILD" in line:
                        later_builds.append((idx + 1, line.strip()))

        ev["later_attempts_count"] = len(later_attempts)
        ev["later_attempts"] = later_attempts
        ev["later_builds"] = later_builds

def print_summary(events: List[Dict[str, Any]]):
    print("=" * 110)
    print("AUTOPSIE DES 10 NOTRAIN SOUS ADAPT400 ET DU CAS MASTER UNIQUE")
    print("=" * 110)
    print(f"Nombre total d'événements NOTRAIN analysés : {len(events)}")
    print(f"  - Bras Master (référence) : {sum(1 for e in events if e['arm'] == 'reference')}")
    print(f"  - Bras V299 (adapt=400)   : {sum(1 for e in events if e['arm'] == 'v299')}")
    print()

    header = f"{'N°':<3} {'Bras':<9} {'Graine':<6} {'Date':<11} {'Paire Src->Dst':<16} {'Cargo':<6} {'Manh':<5} {'Len':<4} {'Quote £':<8} {'Actual £':<9} {'Error':<6} {'Iters':<6} {'Opcodes M':<10}"
    print(header)
    print("-" * len(header))

    total_cost_ref = 0
    total_cost_v299 = 0

    for idx, e in enumerate(events, 1):
        err_str = str(e["build_fail_error"])
        ops_m = f"{e['opcodes'] / 1e6:.2f} M"
        print(f"{idx:<3} {e['arm']:<9} {e['seed']:<6} {e['date']:<11} {e['src']}->{e['dst']:<9} {e['cargo']:<6} {e['manh']:<5} {e['route_len']:<4} {e['quote_capital']:<8} {e['actual_cost']:<9} {err_str:<6} {e['iters']:<6} {ops_m:<10}")
        if e["arm"] == "reference":
            total_cost_ref += e["actual_cost"]
        else:
            total_cost_v299 += e["actual_cost"]

    print("-" * len(header))
    print(f"Capital total dépensé (perdu après rollback) :")
    print(f"  - Référence (1 cas) : {total_cost_ref:,} £")
    print(f"  - V299 (10 cas)     : {total_cost_v299:,} £ (Moyenne : {total_cost_v299/10:,.0f} £ / tentative)")
    print()

    print("=" * 110)
    print("ANALYSE DÉTAILLÉE PAR GROUPE DE PAIRES")
    print("=" * 110)

    # Group by pair
    groups = {}
    for e in events:
        key = (e["arm"], e["src"], e["dst"])
        groups.setdefault(key, []).append(e)

    for (arm, src, dst), ev_list in groups.items():
        first = ev_list[0]
        print(f"\n[GROUPE] Bras={arm} | Paire {src} -> {dst} | Cargo={first['cargo']} | Distance Manh={first['manh']} | {len(ev_list)} tentative(s)")
        print(f"  Coordonnées carte : Src=({first['src_coord'][0]}, {first['src_coord'][1]}), Dst=({first['dst_coord'][0]}, {first['dst_coord'][1]})")
        sub_cost = sum(x["actual_cost"] for x in ev_list)
        print(f"  Capital total brûlé : {sub_cost:,} £")
        print(f"  Dates des tentatives : {', '.join(x['date'] for x in ev_list)}")
        print(f"  Codes d'erreur RAIL_BUILD_FAIL : {', '.join(str(x['build_fail_error']) for x in ev_list)}")
        print(f"  Itérations A* : {', '.join(str(x['iters']) for x in ev_list)}")
        cash_str = f"{first['preceding_cash']:,} £" if first['preceding_cash'] is not None else "non journalisée"
        date_str = f"au {first['preceding_cash_date']}" if first['preceding_cash_date'] else ""
        print(f"  Trésorerie précédant l'achat : {cash_str} ({date_str})")

        # Rollback & subsequent reuse analysis
        print("  Autopsie physique et devenir des infrastructures :")
        if first["build_fail_error"] == 525:
            print("    -> Motif d'échec : OpenTTD Error 525 (ERR_VEHICLE_TOO_LONG).")
            print("       La rame compte plus de 13 wagons (ou dépasse 7 tuiles). MoveWagon refuse l'attelage au dépôt.")
            print("       OpexRollback() démolit la voie (tiles[1..n-1]), les 2 quais et le dépôt.")
        elif first["build_fail_error"] == 0:
            print("    -> Motif d'échec : OpexAI Failure 'LENGTH' (error 0).")
            print("       TrainLengthLimit dépassé au dépôt (ex: motrice multi-head SH 125 mesurée à 16/16e de case au lieu de 8/16e).")
            print("       OpexRollback() démolit la voie (tiles[1..n-1]), les 2 quais et le dépôt.")

        print(f"    -> Réutilisation ultérieure sur ces gares :")
        if ev_list[-1]["later_builds"]:
            for lno, text in ev_list[-1]["later_builds"]:
                print(f"       * {text}")
        else:
            print("       * Aucune réutilisation ultérieure (0 ligne posée sur ces gares).")

def run_selftest():
    # Test parse_line_tokens
    t = parse_line_tokens("foo=1 bar=baz qux=test")
    assert t["foo"] == "1" and t["bar"] == "baz" and t["qux"] == "test", "Failed token parse"
    print("Selftest OK: basic parser verified.")
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Autopsie des échecs NOTRAIN sous adapt400 vs Master")
    parser.add_argument("--log-dir", default=DEFAULT_DIR, help="Dossier contenant les journaux du banc")
    parser.add_argument("--json", action="store_true", help="Sortie JSON structurée")
    parser.add_argument("--selftest", action="store_true", help="Exécute les tests unitaires internes")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()

    if not os.path.exists(args.log_dir):
        print(f"Erreur : dossier introuvable : {args.log_dir}", file=sys.stderr)
        sys.exit(1)

    events = find_notrain_events(args.log_dir)
    analyze_subsequent_history(events, args.log_dir)

    if args.json:
        import json
        clean_events = []
        for e in events:
            c = dict(e)
            del c["preceding_200_lines"]
            clean_events.append(c)
        print(json.dumps(clean_events, indent=2))
    else:
        print_summary(events)

if __name__ == "__main__":
    main()
