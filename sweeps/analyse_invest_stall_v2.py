"""Autopsie des décisions INVEST-STALL v2 dans les logs moteur du smoke.

Lecture seule : comptabilise les *réexamens* par événement/raison, pas les
industries ou projets uniques. Les fichiers de sortie doivent être nouveaux.
"""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

LOG = re.compile(r"OPEX\s+(\d{4})-(\d{1,2})-\d+\s+INVEST_STALL\s+(.+)$")
KV = re.compile(r"([A-Za-z][A-Za-z_0-9]*)=([^\s]+)")
SEED = re.compile(r"seed(\d+)_r\d+\.log$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, required=True)
    ap.add_argument("--policy", default="invest_stall_v2",
                    help="Nom du bras variante dans les journaux du bundle")
    ap.add_argument("--out", type=Path, required=True, help="Préfixe CSV/JSON inexistant")
    args = ap.parse_args()
    csv_path = args.out.with_suffix(".csv")
    json_path = args.out.with_suffix(".json")
    if csv_path.exists() or json_path.exists():
        ap.error("refus d'écraser les artefacts existants")
    files = sorted(args.engine.glob(args.policy + "_seed*_r*.log"))
    if not files:
        ap.error("aucun log " + args.policy + " dans --engine")
    counts = Counter()
    distinct = {}
    for path in files:
        m = SEED.search(path.name)
        if m is None:
            continue
        seed = int(m.group(1))
        with path.open(encoding="utf8", errors="replace") as source:
            for line in source:
                hit = LOG.search(line)
                if hit is None:
                    continue
                year, month = int(hit.group(1)), int(hit.group(2))
                fields = dict(KV.findall(hit.group(3)))
                event = fields.get("event", "unknown")
                route = fields.get("route", "origin" if event.startswith("origin_") else "-")
                reason = fields.get("reason", "-")
                k = (seed, year, month, event, route, reason)
                counts[k] += 1
                line_id = fields.get("line")
                if line_id is not None:
                    distinct.setdefault(k, set()).add(line_id)

    rows = [
        dict(seed=s, year=y, month=m, event=e, route=r, reason=reason,
             reviews=n, distinct_line_ids=len(distinct.get(k, ())))
        for k, n in sorted(counts.items())
        for s, y, m, e, r, reason in [k]
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["seed", "year", "month", "event",
                                                      "route", "reason", "reviews", "distinct_line_ids"])
        writer.writeheader()
        writer.writerows(rows)
    totals = Counter()
    for row in rows:
        totals[(row["event"], row["route"], row["reason"])] += row["reviews"]
    result = {
        "source_logs": [str(x) for x in files],
        "important_note": "counts are reexaminations, not unique source industries or candidates",
        "rows": len(rows),
        "event_totals": [dict(event=e, route=r, reason=reason, reviews=n)
                         for (e, r, reason), n in totals.most_common()],
    }
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"logs={len(files)} rows={len(rows)} csv={csv_path} json={json_path}")
    for item in result["event_totals"][:35]:
        print(item["event"], item["route"], item["reason"], item["reviews"])


if __name__ == "__main__":
    main()
