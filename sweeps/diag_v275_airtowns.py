#!/usr/bin/env python3
"""Analyseur hors-ligne des journaux V275_AIRTOWN (Étape 1 — villes aéroportuaires).

Lit des fichiers `.log` ou `.log.gz` (ou des dossiers en contenant) et extrait les
relevés trimestriels émis sous `DECISION_LOG` (`probes` bit 256) :
  OPEX <Y>-<M>-<D> V275_AIRTOWN town= pop= pax_prod= pax_air_transported=
      share_air= air_load_pct= our_stations= catchment_tiles=
"""
import argparse
import gzip
import json
from pathlib import Path
import re
from statistics import median
import sys

LINE_RE = re.compile(
    r"^(?:.*?\[(?P<company>\d+)\]\s+\[[A-Z]\]\s+|.*?\s)?"
    r"OPEX\s+(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+)\s+V275_AIRTOWN\s+"
    r"town=(?P<town>-?\d+)\s+"
    r"pop=(?P<pop>-?\d+)\s+"
    r"pax_prod=(?P<pax_prod>-?\d+)\s+"
    r"pax_air_transported=(?P<pax_air_transported>-?\d+)\s+"
    r"share_air=(?P<share_air>-?\d+)\s+"
    r"air_load_pct=(?P<air_load_pct>-?\d+)\s+"
    r"our_stations=(?P<our_stations>-?\d+)\s+"
    r"catchment_tiles=(?P<catchment_tiles>-?\d+)\b"
)

THRESHOLDS = (10, 15, 20, 25, 30, 35, 40, 45, 50, 60)


def parse_line(line: str, company_filter: str = "0"):
    m = LINE_RE.search(line.strip())
    if not m:
        return None
    comp = m.group("company")
    if comp is not None and company_filter is not None and comp != company_filter:
        return None
    year = int(m.group("year"))
    month = int(m.group("month"))
    day = int(m.group("day"))
    return {
        "date": f"{year:04d}-{month:02d}-{day:02d}",
        "year": year,
        "month": month,
        "day": day,
        "quarter": (month - 1) // 3 + 1,
        "town": int(m.group("town")),
        "pop": int(m.group("pop")),
        "pax_prod": int(m.group("pax_prod")),
        "pax_air_transported": int(m.group("pax_air_transported")),
        "share_air": int(m.group("share_air")),
        "air_load_pct": int(m.group("air_load_pct")),
        "our_stations": int(m.group("our_stations")),
        "catchment_tiles": int(m.group("catchment_tiles")),
    }


def parse_text(text: str, source: str = "<memory>", company_filter: str = "0"):
    records = []
    for raw in text.splitlines():
        if "V275_AIRTOWN" not in raw:
            continue
        rec = parse_line(raw, company_filter=company_filter)
        if rec is not None:
            rec["source"] = source
            records.append(rec)
    return records


def iter_log_files(paths):
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and (
                    child.name.endswith(".log") or child.name.endswith(".log.gz")
                ):
                    yield child
        elif path.is_file():
            yield path


def read_log_file(path: Path, company_filter: str = "0"):
    opener = gzip.open if path.name.endswith(".gz") else open
    records = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            if "V275_AIRTOWN" not in raw:
                continue
            rec = parse_line(raw, company_filter=company_filter)
            if rec is not None:
                rec["source"] = str(path)
                records.append(rec)
    return records


def _stats(values):
    if not values:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": min(values),
        "median": float(median(values)),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def is_free_at_threshold(rec, threshold: int) -> bool:
    if threshold <= 0:
        return False
    return (
        rec["share_air"] < threshold
        and rec["air_load_pct"] >= 0
        and rec["air_load_pct"] < threshold
    )


def summarize_records(records, thresholds=THRESHOLDS):
    total = len(records)
    valid_load = [r for r in records if r["air_load_pct"] >= 0]
    by_town = {}
    for r in records:
        by_town.setdefault(r["town"], []).append(r)

    town_summaries = {}
    for town_id, rows in sorted(by_town.items()):
        loads = [x["air_load_pct"] for x in rows if x["air_load_pct"] >= 0]
        town_summaries[town_id] = {
            "samples": len(rows),
            "pop_max": max(x["pop"] for x in rows),
            "pax_prod_mean": sum(x["pax_prod"] for x in rows) / len(rows),
            "pax_air_transported_mean": sum(x["pax_air_transported"] for x in rows) / len(rows),
            "share_air_mean": sum(x["share_air"] for x in rows) / len(rows),
            "air_load_pct_mean": (sum(loads) / len(loads)) if loads else None,
            "our_stations_max": max(x["our_stations"] for x in rows),
            "catchment_tiles_max": max(x["catchment_tiles"] for x in rows),
        }

    threshold_table = {}
    for n in thresholds:
        share_ok = sum(1 for r in records if r["share_air"] < n)
        load_ok = sum(1 for r in records if 0 <= r["air_load_pct"] < n)
        both_ok = sum(1 for r in records if is_free_at_threshold(r, n))
        threshold_table[n] = {
            "threshold": n,
            "share_below": share_ok,
            "load_below": load_ok,
            "both_below": both_ok,
            "both_pct": (both_ok * 100.0 / total) if total > 0 else 0.0,
        }

    return {
        "samples": total,
        "distinct_towns": len(by_town),
        "pop": _stats([r["pop"] for r in records]),
        "pax_prod": _stats([r["pax_prod"] for r in records]),
        "pax_air_transported": _stats([r["pax_air_transported"] for r in records]),
        "share_air": _stats([r["share_air"] for r in records]),
        "air_load_pct": _stats([r["air_load_pct"] for r in valid_load]),
        "our_stations": _stats([r["our_stations"] for r in records]),
        "catchment_tiles": _stats([r["catchment_tiles"] for r in records]),
        "thresholds": threshold_table,
        "by_town": town_summaries,
    }


def format_report(summary):
    lines = [
        f"V275_AIRTOWN samples={summary['samples']} distinct_towns={summary['distinct_towns']}",
    ]
    if summary["samples"] == 0:
        return "\n".join(lines)
    for field in (
        "pop",
        "pax_prod",
        "pax_air_transported",
        "share_air",
        "air_load_pct",
        "our_stations",
        "catchment_tiles",
    ):
        st = summary[field]
        if st["count"] > 0:
            lines.append(
                f"  {field}: count={st['count']} min={st['min']} "
                f"median={st['median']:.1f} mean={st['mean']:.1f} max={st['max']}"
            )
    lines.append("  thresholds (share_air < N and 0 <= air_load_pct < N):")
    for n, row in sorted(summary["thresholds"].items()):
        lines.append(
            f"    N={n:2d}%: share<{n}={row['share_below']} "
            f"load<{n}={row['load_below']} both={row['both_below']} "
            f"({row['both_pct']:.1f}%)"
        )
    return "\n".join(lines)


def _selftest():
    sample = (
        "[0] [I] OPEX 1973-1-1 V275_AIRTOWN town=12 pop=3400 pax_prod=420 "
        "pax_air_transported=84 share_air=20 air_load_pct=25 our_stations=1 catchment_tiles=64\n"
        "[0] [I] OPEX 1973-4-1 V275_AIRTOWN town=18 pop=5100 pax_prod=600 "
        "pax_air_transported=300 share_air=50 air_load_pct=45 our_stations=2 catchment_tiles=92\n"
        "[1] [I] OPEX 1973-4-1 V275_AIRTOWN town=99 pop=9999 pax_prod=999 "
        "pax_air_transported=0 share_air=0 air_load_pct=0 our_stations=1 catchment_tiles=16\n"
    )
    recs = parse_text(sample)
    assert len(recs) == 2, f"expected 2 records, got {len(recs)}"
    summary = summarize_records(recs)
    assert summary["samples"] == 2
    assert summary["distinct_towns"] == 2
    assert summary["thresholds"][20]["both_below"] == 0
    assert summary["thresholds"][30]["both_below"] == 1
    assert summary["thresholds"][60]["both_below"] == 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Fichiers .log/.log.gz ou dossiers")
    parser.add_argument("--json", action="store_true", help="Sortie JSON")
    parser.add_argument("--selftest", action="store_true", help="Auto-test interne")
    args = parser.parse_args(argv)

    if args.selftest:
        _selftest()
        print("OK")
        return 0

    records = []
    for log_file in iter_log_files(args.paths):
        records.extend(read_log_file(log_file))
    summary = summarize_records(records)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(format_report(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
