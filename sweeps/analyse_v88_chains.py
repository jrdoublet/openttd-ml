#!/usr/bin/env python3
"""Analyse des traces de chaînes industrielles de biens (V88).

Lit les journaux JSONL produits par `diag_c69_bottleneck_probe.py --raw ...`
ou les sorties de consoles OpenTTD contenant les sondes `CHAIN_*` et `C56_TASK`.

Analyse pour chaque graine et agrège :
1. Le cycle de vie complet de chaque chaîne :
   - Décision / sélection (CHAIN_CHOSEN)
   - Recherche A* étape 1 (CHAIN_STEP1_SEARCH -> CHAIN_SEARCH_END step=1)
   - Mise en service étape 1 (CHAIN_STEP1)
   - Recherche A* étape 2 (CHAIN_STEP2_SEARCH -> CHAIN_SEARCH_END step=2)
   - Mise en service étape 2 (CHAIN_STEP2)
   - Premières livraisons de biens (CHAIN_DELIVERY)
   - Attentes et blocages (CHAIN_WAIT : cash, rail_search)
   - Échecs éventuels (CHAIN_FAIL : too_close, no_goods_candidate, cash...)
2. Les métriques de délai physique par phase :
   - Délai recherche étape 1 (jours, itérations, longueur)
   - Délai mise en service étape 1 (jours depuis fin de recherche)
   - Délai recherche étape 2 (jours, itérations, longueur)
   - Délai mise en service étape 2 (jours depuis fin de recherche)
   - Délai total de décision à mise en service étape 2
   - Délai jusqu'aux premières livraisons de biens
3. Taux d'achèvement et goulots identifiés.

Usage :
  python3 sweeps/analyse_v88_chains.py results/diag_v88_raw.jsonl
  python3 sweeps/analyse_v88_chains.py --selftest
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys


LINE_RE = re.compile(
    r"OPEX (?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+) "
    r"(?P<tag>CHAIN_[A-Z0-9_]+|C56_TASK\s+\S+)\s*(?P<rest>.*)"
)


def parse_fields(text: str) -> dict[str, str]:
    fields = {}
    for tok in text.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            fields[k] = v
    return fields


def date_to_days(year: int, month: int, day: int) -> int:
    return year * 365 + (month - 1) * 30 + day


def parse_date(date_str: str) -> tuple[int, int, int]:
    parts = date_str.split("-")
    return int(parts[0]), int(parts[1]), int(parts[2])


def load_events(path: Path) -> dict[int | str, list[dict]]:
    """Charge les événements CHAIN_* depuis un fichier JSONL ou texte brut."""
    events_by_seed: dict[int | str, list[dict]] = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            seed = "unknown"
            raw_text = ""
            if line.startswith("{"):
                try:
                    row = json.loads(line)
                    seed = row.get("seed", "unknown")
                    if "grep" in row:
                        raw_text = row["grep"]
                    elif "tag" in row and row["tag"].startswith("CHAIN_"):
                        tag = row["tag"]
                        date_str = row.get("_log_date", "1970-1-1")
                        y, m, d = parse_date(date_str)
                        rest_fields = {k: v for k, v in row.items() if not k.startswith("_") and k != "tag" and k != "seed"}
                        events_by_seed[seed].append({
                            "year": y, "month": m, "day": d,
                            "days": date_to_days(y, m, d),
                            "tag": tag,
                            "fields": rest_fields,
                            "raw": line
                        })
                        continue
                    else:
                        continue
                except Exception:
                    raw_text = line
            else:
                raw_text = line

            m = LINE_RE.search(raw_text)
            if not m:
                continue
            y, mth, d = int(m.group("year")), int(m.group("month")), int(m.group("day"))
            tag = m.group("tag").strip()
            rest = m.group("rest").strip()
            fields = parse_fields(rest)
            events_by_seed[seed].append({
                "year": y, "month": mth, "day": d,
                "days": date_to_days(y, mth, d),
                "tag": tag,
                "fields": fields,
                "raw": raw_text
            })
    return events_by_seed


def analyse_seed_events(events: list[dict]) -> dict:
    """Analyse chronologique des chaînes pour une graine donnée."""
    chains: list[dict] = []
    current_chain: dict | None = None
    waits: list[dict] = []
    failures: list[dict] = []
    states: list[dict] = []

    for ev in events:
        tag = ev["tag"]
        fields = ev["fields"]
        days = ev["days"]

        if tag == "CHAIN_CHOSEN":
            if current_chain is not None:
                # Une chaîne terminée peut recevoir sa première CHAIN_DELIVERY
                # après la sélection de la suivante. Il faut donc toujours
                # l'archiver avant de remplacer current_chain, pas seulement
                # lorsqu'elle est encore incomplète.
                if not current_chain.get("completed", False) and not current_chain.get("failed", False):
                    current_chain["abandoned_implicit"] = True
                chains.append(current_chain)
            current_chain = {
                "chosen_days": days,
                "chosen_date": f"{ev['year']}-{ev['month']}-{ev['day']}",
                "factory": fields.get("fact"),
                "town": fields.get("town"),
                "inCargo": fields.get("inCargo"),
                "goodsCargo": fields.get("goodsCargo"),
                "step1_search_start": None,
                "step1_search_end": None,
                "step1_built": None,
                "step1_line": None,
                "step2_search_start": None,
                "step2_search_end": None,
                "step2_built": None,
                "step2_line": None,
                "delivery": None,
                "completed": False,
                "failed": False,
                "fail_reason": None,
            }

        elif tag == "CHAIN_STEP1_SEARCH":
            if current_chain is not None:
                current_chain["step1_search_start"] = days

        elif tag == "CHAIN_SEARCH_END":
            step = fields.get("step")
            if current_chain is not None:
                info = {
                    "days": days,
                    "iters": int(fields.get("iters", 0)),
                    "len": int(fields.get("len", 0)),
                    "weight": int(fields.get("weight", 100)),
                    "outcome": fields.get("outcome")
                }
                if step == "1":
                    current_chain["step1_search_end"] = info
                elif step == "2":
                    current_chain["step2_search_end"] = info

        elif tag == "CHAIN_STEP1":
            if current_chain is not None:
                current_chain["step1_built"] = days
                current_chain["step1_line"] = fields.get("line")

        elif tag == "CHAIN_STEP2_SEARCH":
            if current_chain is not None:
                current_chain["step2_search_start"] = days

        elif tag == "CHAIN_STEP2":
            if current_chain is not None:
                current_chain["step2_built"] = days
                current_chain["step2_line"] = fields.get("line")
                current_chain["completed"] = True

        elif tag == "CHAIN_DELIVERY":
            line = fields.get("line")
            deliv_info = {
                "days": days,
                "year": int(fields.get("year", ev["year"])),
                "profit": int(fields.get("profit", 0)),
                "rev": int(fields.get("rev", 0)),
                "line": line
            }
            if current_chain is not None and current_chain.get("step2_line") == line:
                current_chain["delivery"] = deliv_info
            else:
                # Cherche parmi les chaînes terminées avec cette ligne
                for ch in chains:
                    if ch.get("step2_line") == line and ch.get("delivery") is None:
                        ch["delivery"] = deliv_info
                        break

        elif tag == "CHAIN_WAIT":
            waits.append({
                "days": days,
                "year": ev["year"],
                "step": fields.get("step"),
                "reason": fields.get("reason"),
                "own": fields.get("own"),
                "need": fields.get("need"),
                "money": fields.get("money")
            })

        elif tag == "CHAIN_FAIL":
            fail_step = fields.get("step")
            fail_reason = fields.get("reason")
            failures.append({
                "days": days,
                "year": ev["year"],
                "step": fail_step,
                "reason": fail_reason
            })
            if current_chain is not None:
                current_chain["failed"] = True
                current_chain["fail_reason"] = fail_reason
                chains.append(current_chain)
                current_chain = None

        elif tag == "CHAIN_STATE":
            states.append({
                "days": days,
                "year": ev["year"],
                "active": fields.get("active"),
                "search": fields.get("search"),
                "spent": int(fields.get("spent", -1)),
                "budget": int(fields.get("budget", -1))
            })

    if current_chain is not None:
        chains.append(current_chain)

    # Calcul des délais pour chaque chaîne
    for ch in chains:
        # Recherche étape 1
        if ch.get("step1_search_start") and ch.get("step1_search_end"):
            ch["delay_step1_search_days"] = ch["step1_search_end"]["days"] - ch["step1_search_start"]
        else:
            ch["delay_step1_search_days"] = None

        # Mise en service étape 1 depuis fin de recherche
        if ch.get("step1_search_end") and ch.get("step1_built"):
            ch["delay_step1_commission_days"] = ch["step1_built"] - ch["step1_search_end"]["days"]
        else:
            ch["delay_step1_commission_days"] = None

        # Recherche étape 2
        if ch.get("step2_search_start") and ch.get("step2_search_end"):
            ch["delay_step2_search_days"] = ch["step2_search_end"]["days"] - ch["step2_search_start"]
        else:
            ch["delay_step2_search_days"] = None

        # Mise en service étape 2 depuis fin de recherche
        if ch.get("step2_search_end") and ch.get("step2_built"):
            ch["delay_step2_commission_days"] = ch["step2_built"] - ch["step2_search_end"]["days"]
        else:
            ch["delay_step2_commission_days"] = None

        # Délai total décision -> mise en service étape 2
        if ch.get("chosen_days") and ch.get("step2_built"):
            ch["delay_total_decision_to_step2_days"] = ch["step2_built"] - ch["chosen_days"]
        else:
            ch["delay_total_decision_to_step2_days"] = None

        # Délai étape 2 -> première livraison
        if ch.get("step2_built") and ch.get("delivery"):
            ch["delay_step2_to_delivery_days"] = ch["delivery"]["days"] - ch["step2_built"]
        else:
            ch["delay_step2_to_delivery_days"] = None

    return {
        "chains": chains,
        "waits": waits,
        "failures": failures,
        "states": states,
        "total_chosen": len(chains),
        "total_completed": sum(1 for c in chains if c.get("completed")),
        "total_delivering": sum(1 for c in chains if c.get("delivery")),
        "total_failed": len(failures)
    }


def aggregate_metrics(seed_analyses: dict[int | str, dict]) -> dict:
    """Agrège les statistiques sur toutes les graines."""
    total_chosen = 0
    total_completed = 0
    total_delivering = 0
    total_failed = 0
    failure_reasons = Counter()
    wait_reasons = Counter()

    delays_step1_search = []
    delays_step1_comm = []
    delays_step2_search = []
    delays_step2_comm = []
    delays_decision_step2 = []
    delays_step2_deliv = []

    iters_step1 = []
    iters_step2 = []
    lens_step1 = []
    lens_step2 = []

    for seed, analysis in seed_analyses.items():
        total_chosen += analysis["total_chosen"]
        total_completed += analysis["total_completed"]
        total_delivering += analysis["total_delivering"]
        total_failed += analysis["total_failed"]

        for f in analysis["failures"]:
            failure_reasons[f.get("reason", "unknown")] += 1
        for w in analysis["waits"]:
            wait_reasons[f"{w.get('step')}:{w.get('reason')}"] += 1

        for ch in analysis["chains"]:
            if ch.get("delay_step1_search_days") is not None:
                delays_step1_search.append(ch["delay_step1_search_days"])
            if ch.get("delay_step1_commission_days") is not None:
                delays_step1_comm.append(ch["delay_step1_commission_days"])
            if ch.get("delay_step2_search_days") is not None:
                delays_step2_search.append(ch["delay_step2_search_days"])
            if ch.get("delay_step2_commission_days") is not None:
                delays_step2_comm.append(ch["delay_step2_commission_days"])
            if ch.get("delay_total_decision_to_step2_days") is not None:
                delays_decision_step2.append(ch["delay_total_decision_to_step2_days"])
            if ch.get("delay_step2_to_delivery_days") is not None:
                delays_step2_deliv.append(ch["delay_step2_to_delivery_days"])

            if ch.get("step1_search_end"):
                iters_step1.append(ch["step1_search_end"]["iters"])
                lens_step1.append(ch["step1_search_end"]["len"])
            if ch.get("step2_search_end"):
                iters_step2.append(ch["step2_search_end"]["iters"])
                lens_step2.append(ch["step2_search_end"]["len"])

    def med(lst):
        return statistics.median(lst) if lst else 0

    return {
        "seeds_count": len(seed_analyses),
        "total_chosen": total_chosen,
        "total_completed": total_completed,
        "total_delivering": total_delivering,
        "total_failed": total_failed,
        "failure_reasons": dict(failure_reasons),
        "wait_reasons": dict(wait_reasons),
        "delays": {
            "step1_search_days_med": med(delays_step1_search),
            "step1_commission_days_med": med(delays_step1_comm),
            "step2_search_days_med": med(delays_step2_search),
            "step2_commission_days_med": med(delays_step2_comm),
            "decision_to_step2_days_med": med(delays_decision_step2),
            "step2_to_delivery_days_med": med(delays_step2_deliv),
        },
        "pathfinder": {
            "step1_iters_med": med(iters_step1),
            "step1_len_med": med(lens_step1),
            "step2_iters_med": med(iters_step2),
            "step2_len_med": med(lens_step2),
        }
    }


def print_report(summary: dict) -> None:
    print("=" * 68)
    print("  RAPPORT D'ANALYSE DES CHAINES DE BIENS V88 (V90/V91)")
    print("=" * 68)
    print(f"Graines analysées      : {summary['seeds_count']}")
    print(f"Chaînes choisies       : {summary['total_chosen']}")
    print(f"Chaînes terminées (1+2): {summary['total_completed']}")
    print(f"Chaînes avec livraisons: {summary['total_delivering']}")
    print(f"Chaînes échouées       : {summary['total_failed']}")
    if summary["failure_reasons"]:
        print(f"  Motifs d'échec       : {summary['failure_reasons']}")
    if summary["wait_reasons"]:
        print(f"  Motifs d'attente     : {summary['wait_reasons']}")

    d = summary["delays"]
    print("\n--- Délais médians mesurés ---")
    print(f"  Recherche étape 1    : {d['step1_search_days_med']:.1f} jours")
    print(f"  Mise en service ét.1 : {d['step1_commission_days_med']:.1f} jours")
    print(f"  Recherche étape 2    : {d['step2_search_days_med']:.1f} jours")
    print(f"  Mise en service ét.2 : {d['step2_commission_days_med']:.1f} jours")
    print(f"  Total décision -> ét2: {d['decision_to_step2_days_med']:.1f} jours ({d['decision_to_step2_days_med']/365:.2f} ans)")
    print(f"  Étape 2 -> livraison : {d['step2_to_delivery_days_med']:.1f} jours")

    pf = summary["pathfinder"]
    print("\n--- Pathfinder A* (V90 / V91) ---")
    print(f"  Étape 1 (intrant)    : {pf['step1_iters_med']:.0f} itérations, {pf['step1_len_med']:.0f} tuiles")
    print(f"  Étape 2 (biens)      : {pf['step2_iters_med']:.0f} itérations, {pf['step2_len_med']:.0f} tuiles")
    print("=" * 68)


def selftest() -> None:
    """Auto-test complet sans dépendance externe."""
    sample_lines = [
        {"seed": 42, "grep": "OPEX 1971-03-10 CHAIN_CHOSEN fact=14 town=3 inCargo=2 goodsCargo=5 src=100 dst=500"},
        {"seed": 42, "grep": "OPEX 1971-03-10 CHAIN_STEP1_SEARCH pending=1"},
        {"seed": 42, "grep": "OPEX 1971-05-20 CHAIN_SEARCH_END step=1 iters=520 len=62 weight=120 outcome=OK"},
        {"seed": 42, "grep": "OPEX 1971-06-01 CHAIN_STEP1 line=3 fact=14"},
        {"seed": 42, "grep": "OPEX 1971-06-01 CHAIN_STEP2_SEARCH pending=1"},
        {"seed": 42, "grep": "OPEX 1971-08-15 CHAIN_SEARCH_END step=2 iters=490 len=54 weight=120 outcome=OK"},
        {"seed": 42, "grep": "OPEX 1971-09-01 CHAIN_STEP2 line=4 town=3"},
        {"seed": 42, "grep": "OPEX 1972-01-15 CHAIN_DELIVERY line=4 year=1972 profit=15200 rev=22000"},
        {"seed": 42, "grep": "OPEX 1972-12-31 CHAIN_STATE active=0 search=none own=0 spent=-1 budget=-1"},
    ]
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / "test_raw.jsonl"
        with open(tmp_file, "w", encoding="utf-8") as f:
            for line in sample_lines:
                f.write(json.dumps(line) + "\n")

        events = load_events(tmp_file)
        assert 42 in events
        analysis = analyse_seed_events(events[42])
        assert analysis["total_chosen"] == 1
        assert analysis["total_completed"] == 1
        assert analysis["total_delivering"] == 1
        assert analysis["total_failed"] == 0

        ch = analysis["chains"][0]
        assert ch["step1_line"] == "3"
        assert ch["step2_line"] == "4"
        assert ch["delay_step1_search_days"] == date_to_days(1971, 5, 20) - date_to_days(1971, 3, 10)
        assert ch["delay_step2_search_days"] == date_to_days(1971, 8, 15) - date_to_days(1971, 6, 1)
        assert ch["delay_total_decision_to_step2_days"] == date_to_days(1971, 9, 1) - date_to_days(1971, 3, 10)

        agg = aggregate_metrics({42: analysis})
        assert agg["total_completed"] == 1
        assert agg["pathfinder"]["step1_iters_med"] == 520
        assert agg["pathfinder"]["step2_iters_med"] == 490

        # Régression : une nouvelle chaîne peut être choisie après CHAIN_STEP2
        # mais avant la première livraison de la chaîne précédente. La chaîne
        # terminée doit rester retrouvable par son numéro de ligne.
        delayed_delivery_lines = [
            {"seed": 7, "grep": "OPEX 1973-08-24 CHAIN_CHOSEN fact=2 town=1 inCargo=7 goodsCargo=5 src=11447 dst=11056"},
            {"seed": 7, "grep": "OPEX 1976-06-17 CHAIN_STEP2 line=78 town=1"},
            {"seed": 7, "grep": "OPEX 1976-11-09 CHAIN_CHOSEN fact=11 town=32 inCargo=7 goodsCargo=5 src=2699 dst=31912"},
            {"seed": 7, "grep": "OPEX 1977-04-07 CHAIN_DELIVERY line=78 year=1977 profit=12834 rev=15716"},
        ]
        delayed_file = Path(tmpdir) / "test_delayed_delivery.jsonl"
        with open(delayed_file, "w", encoding="utf-8") as f:
            for line in delayed_delivery_lines:
                f.write(json.dumps(line) + "\n")
        delayed_events = load_events(delayed_file)
        delayed_analysis = analyse_seed_events(delayed_events[7])
        assert delayed_analysis["total_chosen"] == 2
        assert delayed_analysis["total_completed"] == 1
        assert delayed_analysis["total_delivering"] == 1
        assert delayed_analysis["chains"][0]["delivery"]["line"] == "78"
    print("selftest passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", nargs="*", type=Path, help="Fichiers jsonl bruts")
    parser.add_argument("--json", type=Path, default=None, help="Écrit le résumé agrégé en JSON")
    parser.add_argument("--selftest", action="store_true", help="Exécute les auto-tests internes")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    if not args.raw:
        parser.error("Au moins un fichier JSONL brut doit être spécifié")

    seed_analyses = {}
    for raw in args.raw:
        events = load_events(raw)
        for seed, ev_list in events.items():
            seed_analyses[seed] = analyse_seed_events(ev_list)

    summary = aggregate_metrics(seed_analyses)
    print_report(summary)

    if args.json:
        args.json.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
