"""Dépouillement en lecture seule des refus détaillés INVEST-STALL.

Les compteurs sont des événements, non des industries/transactions uniques.
Ne jamais interpréter ce diagnostic comme un duel de qualification économique.
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

LOG = re.compile(r"OPEX\s+(\d{4})-(\d{1,2})-(\d{1,2})\s+INVEST_STALL\s+(.+)$")
KV = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)")
SEED = re.compile(r"_seed(\d+)_r\d+\.log$")


def parse_logs(logs):
    rejects = Counter()
    detail = Counter()
    primary = Counter()
    causes = Counter()
    rows = []
    txns = defaultdict(set)
    for path in logs:
        match = SEED.search(path.name)
        if match is None:
            continue
        seed = int(match.group(1))
        with path.open(encoding="utf8", errors="replace") as src:
            for raw in src:
                hit = LOG.search(raw)
                if not hit:
                    continue
                year, month, day = (int(s) for s in hit.group(1, 2, 3))
                kv = dict(KV.findall(hit.group(4)))
                if kv.get("route") != "fleet":
                    continue
                event = kv.get("event", "")
                reason = kv.get("reason", "")
                if "txn" in kv:
                    txns[(seed, event)].add(kv["txn"])
                if event == "skip" and reason in ("invest_stall_recheck", "unsafe_or_busy"):
                    kind = "platform" if kv.get("kind") == "platform" else "wagon"
                    rejects[(seed, kind, reason)] += 1
                if event != "diagnostic":
                    continue
                kind = kv.get("kind", "unknown")
                if reason not in ("invest_stall_recheck", "unsafe_or_busy"):
                    continue
                main = kv.get("primary", "unclassified")
                key = (seed, kind, reason)
                detail[key] += 1
                primary[(seed, kind, main)] += 1
                for cause in kv.get("failed", "").split(","):
                    if cause:
                        causes[(seed, kind, cause)] += 1
                row = {
                    "seed": seed, "year": year, "month": month, "day": day,
                    "line": kv.get("line", ""), "kind": kind,
                    "reason": reason, "primary": main,
                    "failed": kv.get("failed", ""), "margin_detail": kv.get("margin_detail", ""),
                    "gap": kv.get("gap", ""), "production": kv.get("production", ""),
                    "rating": kv.get("rating", ""), "rated_offer": kv.get("rated_offer", ""),
                    "capacity_month": kv.get("capacity_month", ""),
                    "waiting": kv.get("waiting", ""), "cash": kv.get("cash", ""),
                    "loco_capacity": kv.get("loco_capacity", ""),
                    "wagon_mismatches": kv.get("wagon_mismatches", ""),
                    "first_mismatch": kv.get("first_mismatch", ""),
                    "expected_wagon_id": kv.get("expected_wagon_id", ""),
                    "actual_wagon_id": kv.get("actual_wagon_id", ""),
                    "txn": kv.get("txn", ""), "elapsed_days": kv.get("elapsed_days", ""),
                    "at_target": kv.get("at_target", ""),
                    "target": kv.get("target", ""), "platform": kv.get("platform", ""),
                    "worker": kv.get("worker", "")
                }
                rows.append(row)
    return rejects, detail, primary, causes, txns, rows


def mixed_wagon_subcauses(rows):
    """Séparer les deux gardes de composition, sans supposer de valeur API.

    Les anciens logs sans sous-sonde sont comptés comme non mesurés ; des
    valeurs incohérentes ne deviennent jamais des preuves de sous-cause.
    """
    counts = Counter()
    for row in rows:
        if row["kind"] != "wagon" or "mixed_wagons" not in row["failed"].split(","):
            continue
        try:
            capacity = int(row["loco_capacity"])
            mismatches = int(row["wagon_mismatches"])
        except (TypeError, ValueError):
            cause = "unmeasured"
        else:
            if mismatches < 0:
                cause = "invalid_measurement"
            elif capacity != 0 and mismatches > 0:
                cause = "both"
            elif capacity != 0:
                cause = "loco_capacity_only"
            elif mismatches > 0:
                cause = "wagon_ids_only"
            else:
                cause = "inconsistent_no_failed_subcondition"
        counts[(row["seed"], cause)] += 1
    return [
        {"seed": seed, "subcause": cause, "count": count}
        for (seed, cause), count in sorted(counts.items())
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, required=True)
    ap.add_argument("--policy", default="invest_stall_probe")
    ap.add_argument("--out", type=Path, required=True,
                    help="Préfixe d'artefacts inexistant")
    args = ap.parse_args()
    logs = sorted(args.engine.glob(args.policy + "_seed*_r*.log"))
    if not logs:
        ap.error("aucun log pour la politique demandée")
    csv_path = args.out.with_suffix(".csv")
    json_path = args.out.with_suffix(".json")
    if csv_path.exists() or json_path.exists():
        ap.error("refus d'écraser les résultats existants")
    rejects, detail, primary, causes, txns, rows = parse_logs(logs)
    all_rejects = sum(rejects.values())
    all_details = sum(detail.values())
    classified = sum(n for (s, k, c), n in primary.items() if c != "unclassified")
    result = {
        "logs": [str(p) for p in logs],
        "note": "Reevaluations; diagnostic-only; no efficacy verdict",
        "refus_generiques": all_rejects,
        "diagnostics": all_details,
        "classified": classified,
        "coverage_pct": round(100 * min(all_details, all_rejects) / all_rejects, 2)
        if all_rejects else None,
        "classified_pct": round(100 * classified / all_rejects, 2)
        if all_rejects else None,
        "rejects": [
            {"seed": s, "kind": k, "reason": r, "count": n}
            for (s, k, r), n in sorted(rejects.items())
        ],
        "diagnostics_by_seed": [
            {"seed": s, "kind": k, "reason": r, "count": n}
            for (s, k, r), n in sorted(detail.items())
        ],
        "primary_causes": [
            {"seed": s, "kind": k, "primary": c, "count": n}
            for (s, k, c), n in sorted(primary.items())
        ],
        "all_failed_clauses": [
            {"seed": s, "kind": k, "clause": c, "count": n}
            for (s, k, c), n in sorted(causes.items())
        ],
        "mixed_wagons_subcauses": mixed_wagon_subcauses(rows),
        "distinct_txn_by_event": [
            {"seed": s, "event": e, "unique_txn": len(ids)}
            for (s, e), ids in sorted(txns.items())
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf8") as dst:
        writer = csv.DictWriter(dst, fieldnames=list(rows[0]) if rows else [
            "seed", "year", "month", "day", "line", "kind", "reason", "primary",
            "failed", "margin_detail", "gap", "production", "rating", "rated_offer",
            "capacity_month", "waiting", "cash", "txn", "elapsed_days",
            "loco_capacity", "wagon_mismatches", "first_mismatch",
            "expected_wagon_id", "actual_wagon_id",
            "at_target", "target", "platform", "worker"
        ])
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"logs={len(logs)} refus={all_rejects} diagnostics={all_details}"
          f" classified={classified} coverage={result['classified_pct']}%")
    for item in result["primary_causes"]:
        print(item["seed"], item["kind"], item["primary"], item["count"])
    print(f"details={csv_path} summary={json_path}")


if __name__ == "__main__":
    main()
