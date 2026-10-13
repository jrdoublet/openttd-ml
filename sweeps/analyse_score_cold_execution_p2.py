"""Chaîne P2: score au choix → achat AIR → bilan de ligne de l'exercice.

Lecture stricte d'un journal unique de partie (propriétaire Opex [0]).
Un exercice à flotte inchangée au relevé est seulement *candidat* :
la valeur réelle peut différer du profit réseau C121 et de son amortissement.
Ce module ne produit aucun coefficient économique utilisable en production.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re


DATE = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) (.+)$")
FIELDS = re.compile(r"([a-z0-9_]+)=([^ ]+)")


def event(line, marker):
    # Journal de l'adversaire [1] : aucun événement n'est attribuable à Opex.
    if "[0] [I]" not in line:
        return None
    at = line.find(marker + " ")
    if at == -1:
        return None
    return dict(FIELDS.findall(line[at + len(marker) + 1:].strip()))


def opex_event(line, marker):
    m = DATE.search(line)
    if not m or not m.group(4).startswith(marker + " ") or "[0] [I]" not in line:
        return None
    d = date(*map(int, m.groups()[:3]))
    return d, dict(FIELDS.findall(m.group(4)[len(marker) + 1:]))


def key(row):
    return (row.get("src"), row.get("dst"), row.get("arm"), row.get("engine"))


def analyse_one(lines):
    pending = defaultdict(list)
    heads = defaultdict(list)
    purchases = {}
    reports = defaultdict(list)
    counters = Counter()
    recent_chosen = None
    latest_date = None
    last_build = None
    for index, line in enumerate(lines):
        m = DATE.search(line)
        if m and "[0] [I]" in line:
            latest_date = date(*map(int, m.groups()[:3]))
        row = event(line, "SCORE_COLD_P2_CAND")
        if row:
            pending[row["pass"]].append(row)
            continue
        row = event(line, "SCORE_COLD_P2_HEAD")
        if row and row.get("head_mode") == "air":
            head_key = (row.get("head_src"), row.get("head_dst"),
                        row.get("head_arm"), row.get("head_engine"))
            heads[head_key].append((index, date(int(row["year"]), int(row["month"]),
                                            int(row["day"])), row,
                                    pending.pop(row["pass"], [])))
            continue
        # La sélection est une intention, AIR_BUILD est l'achat effectif.
        chosen = opex_event(line, "PROJECT_CHOSEN")
        if chosen:
            recent_chosen = (index, *chosen)
            continue
        built = opex_event(line, "AIR_BUILD")
        if built:
            d, p = built
            counters["air_built"] += 1
            matched_choice = recent_chosen is not None and index - recent_chosen[0] <= 30 \
                and recent_chosen[2].get("mode") == "air" \
                and recent_chosen[2].get("src") == p.get("src") \
                and recent_chosen[2].get("dst") == p.get("dst") \
                and recent_chosen[2].get("profit") == p.get("profit")
            if matched_choice:
                counters["choice_built_join"] += 1
            contemporaries = [(at, hd, r, rows) for at, hd, r, rows in heads.get(key(p), [])
                               if at < index and 0 <= (d - hd).days <= 30]
            last = max(contemporaries, key=lambda x: x[0]) if contemporaries else None
            if last:
                counters["prior_head_join"] += 1
            head_profit = None
            if last:
                # La tête devrait être un des candidats complets du même pass.
                selected = [r for r in last[3] if r.get("src") == p.get("src")
                            and r.get("dst") == p.get("dst")
                            and r.get("arm") == p.get("arm")
                            and r.get("engine") == p.get("engine")]
                if len(selected) == 1:
                    head_profit = selected[0].get("raw_profit")
                    counters["candidate_head_join"] += 1
                    if head_profit == p.get("profit"):
                        counters["candidate_purchase_profit_equal"] += 1
            purchases[p["line"]] = dict(date=d.isoformat(), build_index=index,
                choice_join=matched_choice, head_join=last is not None,
                candidate_profit=head_profit, purchase_profit=p.get("profit"),
                engine=p.get("engine"), arm=p.get("arm"), src=p.get("src"),
                dst=p.get("dst"), planned_n=p.get("planes"),
                fleet_events=[], c121_decision_profit=None, c121_actual_n=None,
                c121_join=False)
            last_build = (index, p["line"])
            continue
        detail = event(line, "C121_BUILD")
        if detail:
            line_id = detail.get("line")
            if last_build is not None and line_id == last_build[1] \
                    and index - last_build[0] <= 30 and line_id in purchases:
                p = purchases[line_id]
                p["c121_decision_profit"] = detail.get("decision_profit")
                p["c121_actual_n"] = detail.get("actual_n")
                p["c121_join"] = (detail.get("engine") == p["engine"]
                    and detail.get("arm") == p["arm"]
                    and detail.get("decision_profit") == p["purchase_profit"])
                counters["c121_build_join"] += int(p["c121_join"])
            continue
        fleet = opex_event(line, "FLEET_PROJECT")
        if fleet and fleet[1].get("line") in purchases:
            p = purchases[fleet[1]["line"]]
            if index > p["build_index"]:
                p["fleet_events"].append((index, fleet[0].isoformat(), fleet[1].get("action")))
            continue
        annual = opex_event(line, "LINE_REVENUE")
        if annual and annual[1].get("mode") == "air":
            _, row = annual
            reports[row["line"]].append((index, row))
    annual_rows = []
    for line_id, purchase in purchases.items():
        if purchase["choice_join"] and purchase["c121_join"]:
            counters["construction_strict"] += 1
        if not purchase["choice_join"] or not purchase["c121_join"]:
            counters["unresolved_construction"] += 1
        for index, annual in reports.get(line_id, []):
            year = int(annual["year"])
            if int(annual["age"]) < 2 or year <= int(purchase["date"][:4]) + 1:
                continue
            # Le journal est au janvier suivant, et le réalisé correspond au
            # dernier exercice clos. Vérifier les transactions depuis l'achat.
            mutated = any(at < index for at, _, _ in purchase["fleet_events"])
            same_n = annual.get("vehs") == purchase["c121_actual_n"]
            comparable = purchase["choice_join"] and purchase["c121_join"] \
                and purchase["candidate_profit"] is not None and not mutated and same_n \
                and annual.get("pred_prof") == purchase["c121_decision_profit"]
            row = dict(line=line_id, exercise=year - 1, arm=purchase["arm"],
                price_at_candidate=purchase["candidate_profit"],
                profit_at_purchase=purchase["purchase_profit"],
                pred_prof=annual.get("pred_prof"), real_prof=annual.get("real_prof"),
                vehicles=annual.get("vehs"), initial=purchase["c121_actual_n"],
                head_matched=purchase["head_join"],
                candidate_matched=purchase["candidate_profit"] is not None,
                model_same_at_election_and_purchase=(purchase["candidate_profit"]
                    == purchase["purchase_profit"]),
                choice_build_join=purchase["choice_join"] and purchase["c121_join"],
                known_fleet_mutation=mutated, same_vehicles_count=same_n,
                provisional_comparable=comparable,
                prediction_mismatch=(annual.get("pred_prof") != purchase["c121_decision_profit"]),
                network_externality_known=False, amortization_reconciled=False)
            annual_rows.append(row)
            counters["mature_annual_rows"] += 1
            if comparable: counters["provisional_comparable"] += 1
    return {"counts": dict(counters), "purchases": purchases,
        "mature_annual": annual_rows,
        "calibration_ready": False,
        "limitations": [
            "An election snapshot may be repriced before construction, even when OD and engine match.",
            "Vehicle count equality plus observed fleet events cannot exclude hidden buy/sell or crash.",
            "C121 predicted new-line profit may include hub cannibalization absent from LINE_REVENUE.",
            "LINE_REVENUE real_prof excludes the economic amortization term; a raw ratio is NOT a P2 coefficient.",
            "Only individual seeds are independent; repeat annual records are correlated.",
        ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("logs", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = {"sources": {}, "calibration_ready": False}
    for path in args.logs:
        with path.open(encoding="utf8", errors="replace") as f:
            data["sources"][path.name] = analyse_one(f)
        print(path.name, data["sources"][path.name]["counts"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
