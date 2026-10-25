"""AIR-ROI-RENOUVELLEMENT-1: couverture V252 sans calcul de ROI causal.

Les evenements V252_REPLACE publient le prix d'achat mais pas la revente,
le cout net, l'opportunite ecartee ni le benefice contrefactuel du remplacement.
Le LINE_REVENUE ulterieur porte sur la ligne entiere et n'est pas un ROI V252.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

try:
    from sweeps.analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, num, open_text
except ModuleNotFoundError:
    from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, num, open_text


def audit(lines):
    counts = Counter()
    replacements = []
    annual = {}
    for raw in lines:
        match = LINE_RE.search(raw)
        if match is None:
            continue
        tag = match.group(4)
        if tag not in ("V252_REPLACE", "V252_SKIP", "LINE_REVENUE"):
            continue
        date = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        kv = dict(KV_RE.findall(match.group(5)))
        if tag == "V252_SKIP":
            counts["skip_" + kv.get("reason", "unspecified")] += 1
        elif tag == "V252_REPLACE":
            counts["replace_events"] += 1
            old_id, new_id = kv.get("old_veh"), kv.get("new_veh")
            if (not kv.get("line") or old_id is None or new_id is None
                    or old_id == new_id):
                counts["incomplete_identity"] += 1
            if num(kv.get("price")) is None:
                counts["missing_purchase_price"] += 1
            else:
                counts["purchase_price_reported"] += 1
            if num(kv.get("profit")) is None:
                counts["missing_prior_vehicle_profit"] += 1
            replacements.append((date, kv.get("line")))
        elif tag == "LINE_REVENUE" and kv.get("mode") == "air":
            year = num(kv.get("year"))
            if year is None or num(kv.get("age"), -1) < 2:
                continue
            key = (kv.get("line"), int(year))
            if key in annual:
                counts["duplicate_line_year"] += 1
            else:
                annual[key] = date
    for date, line in replacements:
        future = [(yr, d) for (lid, yr), d in annual.items() if lid == line and d > date]
        if future:
            counts["events_with_later_mature_line_report"] += 1
            first_date = min(d for _, d in future)
            if any(other_line == line and date < other_date < first_date
                   for other_date, other_line in replacements):
                counts["events_with_intervening_v252"] += 1
        else:
            counts["events_without_later_mature_line_report"] += 1
    counts["observed_net_purchase_minus_sale_cost"] = 0
    counts["observed_marginal_replacement_profit"] = 0
    return dict(counts)


def directory_report(folder: Path):
    if not folder.is_dir():
        raise ValueError(f"dossier introuvable : {folder}")
    games = {}
    raw_inputs = {}
    for file in sorted(folder.iterdir()):
        if not (file.name.endswith(".log") or file.name.endswith(".log.gz")):
            continue
        stem = file.name[:-3] if file.name.endswith(".gz") else file.name
        if SEED_RE.search(stem) is None:
            continue
        with open_text(str(file)) as source:
            # Compare exact relevant content of duplicate log copies, not only counters.
            relevant = tuple(line for line in source if LINE_RE.search(line) and any(
                tag in line for tag in (" V252_REPLACE ", " V252_SKIP ", " LINE_REVENUE ")))
        if stem in games:
            if raw_inputs[stem] != relevant:
                raise ValueError(f"copies V252 contradictoires : {file}")
            continue
        raw_inputs[stem] = relevant
        games[stem] = audit(relevant)
    if not games:
        raise ValueError("aucun log seed interpretable")
    total = Counter()
    for value in games.values():
        total.update(value)
    return {"games": len(games), "counts": dict(sorted(total.items())),
            "limitations": [
                "V252_REPLACE.price is purchase price; sale proceeds not reported",
                "V252_REPLACE.profit is prior vehicle historical profit, not marginal benefit",
                "LINE_REVENUE contains whole-line performance, not causal replacement yield",
                "Other fleet reinforcement, age, competition, and alternative investments remain confounders",
                "No actual paired same-world replacement/no-replacement counterfactual",
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("ne pas ecraser une sortie existante")
    data = directory_report(args.logs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
