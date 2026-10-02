#!/usr/bin/env python3
"""Analyseur des journaux OPEX SPAN / SPAN_AGG / EVT / SPAN_SELF.

Le temps d'un span est inclusif (enfants compris). La part par categorie
utilise uniquement le temps exclusif d'un span :

    exclusif = max(0, op - somme des op des spans enfants directs)

Les lignes SPAN_AGG sont un detail inclusif dans le tableau par nom. Elles
ne sont pas soustraites du parent et elles n'entrent pas dans le camembert :
leur temps est deja dans le span parent. Les agregats n'ont pas d'intervalle
de ticks propre ; le chemin entre deux constructions ne les utilise pas.

Categories (le nom de feuille decide ; le temps enfant part dans la categorie
de l'enfant via l'exclusif) :

- passenger_air : air.*, build.air*, fleet.*, catalog.refresh.air,
  task.air, task.air_fleet
- rail : astar.*, build.rail, catalog.refresh.rail, loop.astar_v89, task.expand
- road : build.road, catalog.refresh.road, task.town_growth
- water : build.water, catalog.refresh.water
- accounting : report.*, repay.*, scrap.*, start.*, event.*, loop.sleep,
  loop.c117, loop.c83, loop.save_projection
- shared : le reste (select.*, catalogue hors mode, loop.orch*, regen.*,
  task.catalog, task.projects, projects.*, loop.c121_catalog_resume,
  task.refleet, loop.events, loop.legacy, loop.c67)

Calendrier OpenTTD : annee de 365 jours, mois 31,28,31,30,31,30,31,31,30,31,30,31,
sans annees bissextiles. Deux dates identiques donnent une duree de 0 jour.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


SCRIPT_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[\w\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) (.*)$")
KV_RE = re.compile(r"([A-Za-z0-9_]+)=(.*)")
MONTH_DAYS = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

PASSENGER_AIR_EXACT = {"catalog.refresh.air", "task.air", "task.air_fleet"}
RAIL_EXACT = {"build.rail", "catalog.refresh.rail", "loop.astar_v89", "task.expand"}
ROAD_EXACT = {"build.road", "catalog.refresh.road", "task.town_growth"}
WATER_EXACT = {"build.water", "catalog.refresh.water"}
ACCOUNTING_EXACT = {
    "loop.sleep", "loop.c117", "loop.c83", "loop.save_projection",
}


def ordinal(year, month, day):
    total = int(year) * 365
    for m in range(1, int(month)):
        total += MONTH_DAYS[m]
    return total + int(day) - 1


def days_between(start, end):
    return ordinal(*end) - ordinal(*start)


def category_of(name):
    if name.startswith("air.") or name.startswith("build.air") or name.startswith("fleet.") or name in PASSENGER_AIR_EXACT:
        return "passenger_air"
    if name.startswith("astar.") or name in RAIL_EXACT:
        return "rail"
    if name in ROAD_EXACT:
        return "road"
    if name in WATER_EXACT:
        return "water"
    if (name.startswith("report.") or name.startswith("repay.") or name.startswith("scrap.")
            or name.startswith("start.") or name.startswith("event.") or name in ACCOUNTING_EXACT):
        return "accounting"
    return "shared"


def _parse_fields(text):
    fields = {}
    for token in text.split():
        match = KV_RE.fullmatch(token)
        if match is None:
            continue
        fields[match.group(1)] = match.group(2)
    return fields


def _as_int(fields, key, default=0):
    raw = fields.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def parse_opex_message(message, company, source=""):
    """Retourne un enregistrement ou None si la ligne n'est pas une sonde SPAN."""
    match = OPEX_RE.match(message.strip())
    if match is None:
        return None
    date = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    rest = match.group(4)
    if rest.startswith("SPAN_AGG "):
        kind = "SPAN_AGG"
        fields = _parse_fields(rest[len("SPAN_AGG "):])
    elif rest.startswith("SPAN_SELF "):
        kind = "SPAN_SELF"
        fields = _parse_fields(rest[len("SPAN_SELF "):])
    elif rest.startswith("SPAN "):
        kind = "SPAN"
        fields = _parse_fields(rest[len("SPAN "):])
    elif rest.startswith("EVT "):
        kind = "EVT"
        fields = _parse_fields(rest[len("EVT "):])
    else:
        return None
    record = {
        "kind": kind,
        "company": int(company),
        "date": date,
        "fields": fields,
        "source": source,
    }
    if kind == "SPAN":
        record.update({
            "id": _as_int(fields, "id"),
            "parent": _as_int(fields, "par"),
            "depth": _as_int(fields, "dep"),
            "name": fields.get("n", ""),
            "start": _parse_date(fields.get("ds", "")),
            "t0": _as_int(fields, "t0"),
            "tk": _as_int(fields, "tk"),
            "op": _as_int(fields, "op"),
            "orphan": fields.get("orphan") == "1",
        })
    elif kind == "SPAN_AGG":
        record.update({
            "parent": _as_int(fields, "par"),
            "name": fields.get("n", ""),
            "count": _as_int(fields, "cnt"),
            "tk": _as_int(fields, "tk"),
            "op": _as_int(fields, "op"),
        })
    elif kind == "SPAN_SELF":
        record.update({
            "lines": _as_int(fields, "lines"),
            "agg_lines": _as_int(fields, "agg_lines"),
        })
    else:
        record.update({
            "event": fields.get("k", ""),
            "t0": _as_int(fields, "t0"),
        })
    return record


def _parse_date(text):
    match = re.fullmatch(r"(\d+)-(\d+)-(\d+)", text or "")
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def parse_log_text(text, company_filter=0, source=""):
    records = []
    for line in text.splitlines():
        match = SCRIPT_RE.search(line)
        if match is None:
            continue
        company = int(match.group(1))
        if company_filter is not None and company != int(company_filter):
            continue
        record = parse_opex_message(match.group(2), company, source)
        if record is not None:
            records.append(record)
    return records


def seed_from_path(path):
    stem = Path(path).stem
    if "_" in stem:
        _arm, seed = stem.rsplit("_", 1)
        if seed.isdigit():
            return seed
    return stem


def _month_key(date):
    if date is None:
        return "unknown"
    return "%d-%d" % (date[0], date[1])


def _empty_bucket():
    return {"count": 0, "ticks": 0, "opcodes": 0, "days": 0}


def _add_bucket(bucket, count, ticks, opcodes, days):
    bucket["count"] += count
    bucket["ticks"] += ticks
    bucket["opcodes"] += opcodes
    bucket["days"] += days


def build_seed_report(records):
    spans = [r for r in records if r["kind"] == "SPAN"]
    aggs = [r for r in records if r["kind"] == "SPAN_AGG"]
    events = [r for r in records if r["kind"] == "EVT"]
    selves = [r for r in records if r["kind"] == "SPAN_SELF"]
    by_id = {}
    for span in spans:
        by_id[span["id"]] = span
        span["children"] = []
        span["aggs"] = []
    roots = []
    for span in spans:
        parent = by_id.get(span["parent"])
        if parent is None or parent is span:
            roots.append(span)
        else:
            parent["children"].append(span)
    for agg in aggs:
        parent = by_id.get(agg["parent"])
        if parent is not None:
            parent["aggs"].append(agg)

    def exclusive(span):
        child_op = sum(child["op"] for child in span["children"])
        value = span["op"] - child_op
        return value if value > 0 else 0

    for span in spans:
        span["exclusive_op"] = exclusive(span)
        start = span["start"] if span["start"] is not None else span["date"]
        span["days"] = days_between(start, span["date"]) if start is not None else 0

    by_name = {}

    def bucket_for(name):
        if name not in by_name:
            by_name[name] = {
                "count": 0, "ticks": 0, "opcodes": 0, "days": 0,
                "by_month": {}, "kind": "span",
            }
        return by_name[name]

    for span in spans:
        bucket = bucket_for(span["name"])
        bucket["kind"] = "span"
        _add_bucket(bucket, 1, span["tk"], span["op"], span["days"])
        month = bucket["by_month"].setdefault(_month_key(span["date"]), _empty_bucket())
        _add_bucket(month, 1, span["tk"], span["op"], span["days"])
    for agg in aggs:
        bucket = bucket_for(agg["name"])
        if bucket["count"] == 0:
            bucket["kind"] = "agg"
        elif bucket["kind"] == "span":
            bucket["kind"] = "mixed"
        _add_bucket(bucket, agg["count"], agg["tk"], agg["op"], 0)
        month = bucket["by_month"].setdefault(_month_key(agg["date"]), _empty_bucket())
        _add_bucket(month, agg["count"], agg["tk"], agg["op"], 0)

    categories = {
        "passenger_air": 0, "rail": 0, "road": 0, "water": 0,
        "shared": 0, "accounting": 0,
    }
    for span in spans:
        categories[category_of(span["name"])] += span["exclusive_op"]
    total_exclusive = sum(categories.values())
    shares = {}
    for name, value in categories.items():
        shares[name] = (value / total_exclusive) if total_exclusive else 0.0

    paths = []
    builds = [ev for ev in events if ev["event"] == "line_built"]
    for prev, nxt in zip(builds, builds[1:]):
        window_lo = prev["t0"]
        window_hi = nxt["t0"]
        ranked = []
        for span in spans:
            overlap = _overlap(span["t0"], span["t0"] + span["tk"], window_lo, window_hi)
            if overlap <= 0:
                continue
            ranked.append({
                "name": span["name"],
                "id": span["id"],
                "overlap_ticks": overlap,
                "opcodes": span["op"],
                "orphan": span["orphan"],
                "t0": span["t0"],
                "tk": span["tk"],
            })
        ranked.sort(key=lambda item: (-item["overlap_ticks"], item["id"]))
        paths.append({
            "from_tick": window_lo,
            "to_tick": window_hi,
            "from_date": list(prev["date"]),
            "to_date": list(nxt["date"]),
            "top": ranked[:15],
        })

    def node(span):
        return {
            "id": span["id"],
            "parent": span["parent"],
            "depth": span["depth"],
            "name": span["name"],
            "start": list(span["start"]) if span["start"] is not None else None,
            "end": list(span["date"]),
            "days": span["days"],
            "t0": span["t0"],
            "tk": span["tk"],
            "op": span["op"],
            "exclusive_op": span["exclusive_op"],
            "orphan": span["orphan"],
            "extra": _extra(span),
            "category": category_of(span["name"]),
            "aggs": [
                {"name": agg["name"], "count": agg["count"], "ticks": agg["tk"], "opcodes": agg["op"]}
                for agg in span["aggs"]
            ],
            "children": [node(child) for child in span["children"]],
        }

    return {
        "chronology": [node(span) for span in roots],
        "by_name": by_name,
        "categories": categories,
        "category_share": shares,
        "paths": paths,
        "span_self": [
            {"date": list(item["date"]), "lines": item["lines"], "agg_lines": item["agg_lines"]}
            for item in selves
        ],
        "orphan_count": sum(1 for span in spans if span["orphan"]),
        "span_count": len(spans),
        "agg_count": len(aggs),
        "event_count": len(events),
    }


def _overlap(start, end, window_lo, window_hi):
    lo = start if start > window_lo else window_lo
    hi = end if end < window_hi else window_hi
    return hi - lo if hi > lo else 0


def _extra(span):
    skip = {"id", "par", "dep", "n", "ds", "t0", "tk", "op", "orphan"}
    return {key: value for key, value in span["fields"].items() if key not in skip}


def _median(values):
    if not values:
        return 0
    return statistics.median(values)


def across_seeds(seed_reports):
    names = set()
    for report in seed_reports.values():
        names.update(report["by_name"].keys())
    by_name = {}
    for name in sorted(names):
        rows = []
        for seed, report in seed_reports.items():
            bucket = report["by_name"].get(name)
            if bucket is None:
                rows.append({"seed": seed, "count": 0, "ticks": 0, "opcodes": 0, "days": 0})
            else:
                rows.append({
                    "seed": seed,
                    "count": bucket["count"],
                    "ticks": bucket["ticks"],
                    "opcodes": bucket["opcodes"],
                    "days": bucket["days"],
                })
        by_name[name] = {
            "per_seed": rows,
            "mean": {
                "count": statistics.fmean(row["count"] for row in rows),
                "ticks": statistics.fmean(row["ticks"] for row in rows),
                "opcodes": statistics.fmean(row["opcodes"] for row in rows),
                "days": statistics.fmean(row["days"] for row in rows),
            },
            "median": {
                "count": _median([row["count"] for row in rows]),
                "ticks": _median([row["ticks"] for row in rows]),
                "opcodes": _median([row["opcodes"] for row in rows]),
                "days": _median([row["days"] for row in rows]),
            },
        }
    categories = {}
    for cat in ("passenger_air", "rail", "road", "water", "shared", "accounting"):
        values = [report["categories"].get(cat, 0) for report in seed_reports.values()]
        categories[cat] = {
            "mean": statistics.fmean(values) if values else 0,
            "median": _median(values),
        }
    return {"by_name": by_name, "categories": categories}


def render_markdown(report, depth=None):
    lines = ["# Trace des micro-taches", ""]
    for seed, seed_report in report["seeds"].items():
        lines.append("## Graine %s" % seed)
        lines.append("")
        lines.append("### Chronologie")
        lines.append("")
        for node in seed_report["chronology"]:
            lines.extend(_render_node(node, depth))
        lines.append("")
        lines.append("### Part du temps exclusif")
        lines.append("")
        for cat, share in seed_report["category_share"].items():
            lines.append("- %s : %d opcodes exclusifs (%.1f %%)" % (
                cat, seed_report["categories"][cat], 100.0 * share))
        lines.append("")
        lines.append("### Chemins entre constructions")
        lines.append("")
        if not seed_report["paths"]:
            lines.append("Aucune paire de lignes construites.")
        for path in seed_report["paths"]:
            lines.append("- ticks %d -> %d" % (path["from_tick"], path["to_tick"]))
            for item in path["top"]:
                orphan = " orphan" if item["orphan"] else ""
                lines.append("  - %s id=%d chevauchement=%d op=%d%s" % (
                    item["name"], item["id"], item["overlap_ticks"], item["opcodes"], orphan))
        lines.append("")
    lines.append("## Agregat inter-graines")
    lines.append("")
    lines.append("| nom | compte moyen | ticks moyens | opcodes moyens | jours moyens | opcodes medians |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for name, stats in report["across"]["by_name"].items():
        mean = stats["mean"]
        median = stats["median"]
        lines.append("| %s | %.1f | %.1f | %.1f | %.1f | %.1f |" % (
            name, mean["count"], mean["ticks"], mean["opcodes"], mean["days"], median["opcodes"]))
    lines.append("")
    return "\n".join(lines)


def _render_node(node, depth, indent=0):
    if depth is not None and node["depth"] > depth:
        return []
    start = "-".join(str(part) for part in node["start"]) if node["start"] else "?"
    extra = " ".join("%s=%s" % (key, value) for key, value in sorted(node["extra"].items()))
    suffix = (" " + extra) if extra else ""
    orphan = " orphan" if node["orphan"] else ""
    line = "%s- %s debut=%s jours=%d ticks=%d op=%d%s%s" % (
        "  " * indent, node["name"], start, node["days"], node["tk"], node["op"], orphan, suffix)
    lines = [line]
    for child in node["children"]:
        lines.extend(_render_node(child, depth, indent + 1))
    return lines


def analyse_records_by_seed(grouped, company=0):
    seeds = {}
    for seed, records in grouped.items():
        seeds[seed] = build_seed_report(records)
    return {
        "company": company,
        "seeds": seeds,
        "across": across_seeds(seeds),
    }


def analyse_paths(paths, company_filter=0):
    grouped = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        seed = seed_from_path(path)
        grouped.setdefault(seed, []).extend(parse_log_text(text, company_filter, str(path)))
    return analyse_records_by_seed(grouped, company_filter)


def collect_logs(target):
    path = Path(target)
    if path.is_dir():
        return sorted(path.glob("*.log"))
    return [path]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyse un journal de spans OpexAI.")
    parser.add_argument("target", help="Fichier .log ou dossier de journaux")
    parser.add_argument("--json", dest="json_out", default=None)
    parser.add_argument("--md", dest="md_out", default=None)
    parser.add_argument("--depth", type=int, default=None)
    parser.add_argument("--company", type=int, default=0)
    args = parser.parse_args(argv)
    report = analyse_paths(collect_logs(args.target), args.company)
    markdown = render_markdown(report, args.depth)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        Path(args.md_out).write_text(markdown, encoding="utf-8")
    if not args.json_out and not args.md_out:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
