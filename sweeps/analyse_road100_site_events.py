#!/usr/bin/env python3
"""ROAD100 physical/economic event reader (not an estimator of realized profit).

Logs have many unrelated OpenTTD lines and several epochs per seed. Preserve
all events; missing probes are null, not invented zero values. This reader
does not mistake ROAD100_SITE_FIRST admission for a built route.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

PREFIX = re.compile(r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+"
                    r"(ROAD100_[A-Z_]+|ROAD_BUILD|PROJECT_DISCARD|LINE_REVENUE)\s+(.*)")
FILENAME = re.compile(r"(?P<policy>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")
PAIR_FIELDS = ("src", "dst")
SUMMARY_KINDS = ("ROAD100_SITE_FIRST", "ROAD100_JOINED_STOP", "ROAD100_REPRICE",
                 "ROAD100_PLAN_DRIFT", "ROAD100_SITE_FLEET", "ROAD100_SITE_PICK",
                 "ROAD_BUILD", "PROJECT_DISCARD", "LINE_REVENUE")


def parse_payload(raw: str) -> dict[str, object]:
    fields: dict[str, object] = {}
    for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*)=([^\s]+)", raw):
        key, value = match.groups()
        if re.fullmatch(r"-?\d+", value):
            fields[key] = int(value)
        else:
            fields[key] = value
    return fields


def parse_log(path: Path) -> dict:
    match = FILENAME.match(path.name)
    if match is None:
        raise ValueError(f"not a ROAD duel log: {path.name}")
    meta = match.groupdict()
    counts: dict[str, int] = collections.Counter()
    rejected: dict[str, int] = collections.Counter()
    records: list[dict] = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            found = PREFIX.search(line)
            if found is None:
                continue
            date, kind, raw = found.groups()
            if kind not in SUMMARY_KINDS:
                continue
            fields = parse_payload(raw)
            if kind == "ROAD100_SITE_FIRST":
                kind += "_" + str(fields.get("phase", "unknown"))
            elif kind == "ROAD100_SITE_FLEET":
                kind += "_" + str(fields.get("phase", "unknown"))
            counts[kind] += 1
            if kind == "PROJECT_DISCARD":
                reason = str(fields.get("reason", "missing"))
                detail = str(fields.get("detail", ""))
                rejected[reason + ("/" + detail if detail else "")] += 1
            # A build record's 'profit' is still a model prediction, not the
            # realized LINE_REVENUE. Keep event types separate.
            records.append({"date": date, "kind": kind, "fields": fields})
    summaries = [r for r in records if r["kind"] == "ROAD100_SITE_FIRST_summary"]
    admissions = [r for r in records if r["kind"] == "ROAD100_SITE_FIRST_admit"]
    road_builds = [r for r in records if r["kind"] == "ROAD_BUILD"]
    pax_built = [r for r in road_builds if r["fields"].get("cargo") == "PASS"]
    returns = [r for r in records if r["kind"] == "ROAD100_REPRICE"]
    # A build is matched to a specific accepted pair, not every PAX BUILD
    # (other generators may build passengers too). An accepted pair might
    # change sites between admission and construction.
    admitted_pairs = {
        tuple(admit["fields"].get(field) for field in PAIR_FIELDS)
        for admit in admissions
    }
    matched_builds = [r for r in pax_built
                      if tuple(r["fields"].get(f) for f in PAIR_FIELDS) in admitted_pairs]
    return {
        **{k: int(v) for k, v in meta.items() if k != "policy"},
        "policy": meta["policy"], "source": str(path),
        "event_counts": dict(counts), "refusals": dict(rejected),
        "site_summary_last": summaries[-1]["fields"] if summaries else None,
        "admitted_pairs_count": len(admitted_pairs),
        "admission_events": len(admissions),
        "passenger_build_events": len(pax_built),
        "matched_passenger_build_events": len(matched_builds),
        "reprice_events": len(returns),
        "has_realized_line_revenue": counts.get("LINE_REVENUE", 0) > 0,
        "records": records,
    }


def parse_campaign(engine_dir: Path) -> dict:
    files = sorted(engine_dir.glob("*_seed*_r*.log"))
    if not files:
        raise FileNotFoundError(f"no duel logs in {engine_dir}")
    parsed = [parse_log(path) for path in files]
    return {"engine_dir": str(engine_dir), "logs": parsed, "count": len(parsed)}


def as_markdown(campaign: dict) -> str:
    lines = [
        "# ROAD100 — événements physiques et économiques",
        "",
        "Les bénéfices de ROAD_BUILD sont **prévus** ; sans LINE_REVENUE, "
        "aucun revenu réalisé par ligne ne peut être déduit de ce journal.",
        "L'admission d'un plan n'est pas une construction.",
        "",
        "| Politique | Graine | Plans | Admis | PAX bâtis par paire admise | "
        "PAX bâtis toutes origines | Refus | OpCodes préflight | Reprice | Recettes réelles traçables |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for data in campaign["logs"]:
        summ = data["site_summary_last"] or {}
        counts = data["event_counts"]
        lines.append(
            f"| {data['policy']} | {data['seed']} | {summ.get('plans', 'NA')} | "
            f"{data['admission_events']} | {data['matched_passenger_build_events']} | "
            f"{data['passenger_build_events']} | "
            f"{sum(data['refusals'].values())} | {summ.get('ops', 'NA')} | "
            f"{data['reprice_events']} | "
            f"{'oui' if data['has_realized_line_revenue'] else 'non'} |"
        )
    lines += ["", "## Refus par type", ""]
    for data in campaign["logs"]:
        refus = ", ".join(f"{key}: {value}" for key, value in sorted(data["refusals"].items())) or "aucun journalisé"
        lines.append(f"- {data['policy']}, graine {data['seed']} : {refus}")
    lines += ["", "Méthode : les événements bruts avec date et tous champs sont disponibles "
              "dans le JSON ; les absences de sonde sont représentées par `null`, "
              "non par des zéros."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    result = parse_campaign(args.engine_dir)
    for output in (args.out_json, args.out_md):
        output.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(as_markdown(result), encoding="utf-8")
    print(f"ROAD100 log reader: {result['count']} files; output {args.out_json} {args.out_md}")


if __name__ == "__main__":
    main()
