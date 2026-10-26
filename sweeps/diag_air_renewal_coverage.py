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
import re

try:
    from sweeps.analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, num, open_text
except ModuleNotFoundError:
    from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, num, open_text


LINE_ID_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z")


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
            line_id = kv.get("line")
            valid_line = line_id is not None and LINE_ID_RE.fullmatch(line_id) is not None
            if (not valid_line or old_id is None or new_id is None
                    or old_id == new_id):
                counts["incomplete_identity"] += 1
            if num(kv.get("price")) is None:
                counts["missing_purchase_price"] += 1
            else:
                counts["purchase_price_reported"] += 1
            if num(kv.get("profit")) is None:
                counts["missing_prior_vehicle_profit"] += 1
            replacements.append((date, line_id if valid_line else None))
        elif tag == "LINE_REVENUE" and kv.get("mode") == "air":
            age = num(kv.get("age"))
            if age is None or age < 2:
                continue
            line_id = kv.get("line")
            if line_id is None or LINE_ID_RE.fullmatch(line_id) is None:
                counts["invalid_mature_line_id"] += 1
                continue
            year = num(kv.get("year"))
            if year is None or not year.is_integer():
                counts["invalid_mature_revenue_year"] += 1
                continue
            key = (line_id, int(year))
            if key in annual:
                counts["duplicate_line_year"] += 1
            else:
                annual[key] = date
    for date, line in replacements:
        future = [(yr, d) for (lid, yr), d in annual.items()
                  if line is not None and lid == line and d > date]
        # LINE_REVENUE year=Y is published in Y but describes earnings during
        # Y-1. A report published after the purchase can therefore describe
        # only the *previous* year's activity. Conservatively, the purchase
        # year is partial and the first full post-purchase calendar year is Y+1
        # (observed by a LINE_REVENUE record whose year is at least Y+2).
        any_post_period = [(yr, d) for yr, d in future if yr > date[0]]
        full_post_year = [(yr, d) for yr, d in future if yr >= date[0] + 2]
        if future:
            counts["events_with_later_mature_line_report"] += 1
            first_date = min(d for _, d in future)
            if any(other_line == line and date < other_date < first_date
                   for other_date, other_line in replacements):
                counts["events_with_intervening_v252"] += 1
            if not any_post_period:
                counts["events_with_published_later_only_pre_purchase_period"] += 1
        else:
            counts["events_without_later_mature_line_report"] += 1
        if any_post_period:
            counts["events_with_any_profit_period_after_purchase"] += 1
            if not full_post_year:
                counts["events_with_later_partial_post_period_only"] += 1
        if full_post_year:
            counts["events_with_full_calendar_year_after_purchase"] += 1
            first_full_date = min(d for _, d in full_post_year)
            if any(other_line == line and date < other_date < first_full_date
                   for other_date, other_line in replacements):
                counts["events_with_intervening_v252_before_full_calendar_year"] += 1
        else:
            counts["events_without_full_calendar_year_after_purchase"] += 1
    counts["observed_net_purchase_minus_sale_cost"] = 0
    counts["observed_marginal_replacement_profit"] = 0
    return dict(counts)


def directory_report(folder: Path):
    if not folder.is_dir():
        raise ValueError(f"dossier introuvable : {folder}")
    games = {}
    raw_inputs = {}
    canonical_names = {}
    for file in sorted(folder.iterdir()):
        if not (file.name.endswith(".log") or file.name.endswith(".log.gz")):
            continue
        stem = file.name[:-3] if file.name.endswith(".gz") else file.name
        match = SEED_RE.search(stem)
        if match is None:
            continue
        # Numeric seed/repeat aliases identify the same game, even if the
        # filename spells them differently. Keep separate experimental arms.
        identity = (stem[:match.start()], int(match[1]), int(match[2]))
        previous_name = canonical_names.setdefault(identity, stem)
        if previous_name != stem:
            raise ValueError(f"identite de partie V252 ambigue : {previous_name} et {stem}")
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
                "LINE_REVENUE year Y describes accounting year Y-1; reports published after a replacement may measure only pre-purchase activity",
                "Full post-replacement calendar years conservatively require report_year >= purchase_year + 2; this does not isolate replacement effects",
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
