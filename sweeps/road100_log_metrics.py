#!/usr/bin/env python3
"""ROAD100 : comptes de construction/sondes issus des logs figés du duel.

Les coûts sont les `cost=` publiés à `ROAD_BUILD`, pas une reconstitution
comptable de toutes les dépenses du jeu. Les reflets du portefeuilles et
les refus mensuels sont des événements, pas des projets uniques.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
LOG_RE = re.compile(r"\[0\]\s+\[I\]\s+OPEX\s+(\d{4})-\d+-\d+\s+([A-Z0-9_]+)\s+(.*)$")
FIELD_RE = re.compile(r"([\w]+)=([^\s]+)")


def decode_one_log(path: Path, start_year: int, years: int):
    """Compter des événements année × type, sans transformer une absence en zéro."""
    out = {y: {"builds": 0, "vehicles_purchased_on_new_lines": 0,
               "reported_build_cost_gbp": 0, "predicted_build_profit_gbp_year": 0,
               "generation_produced": 0, "generation_samples": 0,
               "batch_allow": 0, "batch_refuse": 0, "batch_pass_limit": 0,
               "pax_local_positive": 0, "pax_intertown_positive": 0,
               "discard_reasons": Counter(), "c75_stop_reasons": Counter(),
               "events": Counter()}
           for y in range(start_year, start_year + years)}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            matched = LOG_RE.search(line)
            if matched is None:
                continue
            year, tag, payload = matched.groups()
            year = int(year)
            if year not in out:
                continue
            metrics = out[year]
            fields = dict(FIELD_RE.findall(payload))
            metrics["events"][tag] += 1
            if tag == "ROAD_BUILD":
                metrics["builds"] += 1
                for key, field in (("reported_build_cost_gbp", "cost"),
                                   ("predicted_build_profit_gbp_year", "profit"),
                                   ("vehicles_purchased_on_new_lines", "vehicles")):
                    val = fields.get(field)
                    if val is not None and val.isdigit():
                        metrics[key] += int(val)
            elif tag == "VIVIER_GEN" and fields.get("mode") == "road":
                val = fields.get("produced")
                if val is not None and val.isdigit():
                    metrics["generation_produced"] += int(val)
                    metrics["generation_samples"] += 1
            elif tag == "ROAD100_BATCH":
                action = fields.get("action", "unknown")
                key = {"allow": "batch_allow", "refuse": "batch_refuse",
                       "pass_limit": "batch_pass_limit"}.get(action)
                if key is not None:
                    metrics[key] += 1
            elif tag == "ROAD100_TOWN_GEN":
                val = fields.get("positive")
                if val is not None and val.isdigit():
                    metrics["pax_local_positive"] += int(val)
            elif tag == "ROAD100_PAX_GEN":
                val = fields.get("positive")
                if val is not None and val.isdigit():
                    metrics["pax_intertown_positive"] += int(val)
            elif tag == "PROJECT_DISCARD":
                metrics["discard_reasons"][fields.get("reason", "unknown")] += 1
            elif tag == "C69_BOTTLENECK" and fields.get("phase") == "c75_pass":
                metrics["c75_stop_reasons"][fields.get("stop", "unknown")] += 1
    return out


def summarise(campaign: str):
    path = ROOT / "results" / (campaign + ".json")
    obj = json.loads(path.read_text(encoding="utf-8"))
    logdir = ROOT / "results" / (campaign + "_engine")
    start, years = int(obj["start_year"]), int(obj["years"])
    result = {"campaign": campaign, "bundle": obj.get("source_bundle_sha256"), "policies": {}}
    for policy in obj["policies"]:
        name = policy["id"]
        per_year = {}
        missing = []
        reads = []
        for seed in obj["seeds"]:
            filename = logdir / f"{name}_seed{seed}_r0.log"
            gz = filename.with_name(filename.name + ".gz")
            if not filename.exists() and not gz.exists():
                missing.append(seed)
                continue
            reads.append(decode_one_log(filename if filename.exists() else gz, start, years))
        for year in range(start, start + years):
            common = ("builds", "vehicles_purchased_on_new_lines", "reported_build_cost_gbp",
                      "predicted_build_profit_gbp_year", "generation_produced", "generation_samples",
                      "batch_allow", "batch_refuse", "batch_pass_limit",
                      "pax_local_positive", "pax_intertown_positive")
            row = {"logs_present": len(reads), "expected_logs": len(obj["seeds"])}
            row.update({field: sum(item[year][field] for item in reads) if reads else None
                        for field in common})
            for field in ("discard_reasons", "c75_stop_reasons", "events"):
                counter = Counter()
                for item in reads:
                    counter.update(item[year][field])
                row[field] = dict(counter) if reads else None
            per_year[str(year)] = row
        result["policies"][name] = {"missing_log_seeds": missing, "years": per_year}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--out", required=True, type=Path)
    opts = parser.parse_args()
    data = summarise(opts.campaign)
    opts.out.parent.mkdir(parents=True, exist_ok=True)
    opts.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("log coverage:", {p: len(v["missing_log_seeds"]) for p, v in data["policies"].items()})


if __name__ == "__main__":
    main()
