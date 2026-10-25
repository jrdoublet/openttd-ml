#!/usr/bin/env python3
"""Read CARTO-1 shadow map costs alongside real rail A* diagnostic logs.

Usage:
    python sweeps/analyze_carto1.py results/carto1_engine --format markdown
    python sweeps/analyze_carto1.py results/carto1_engine --format json --out report.json

Only CARTO1_COST and CARTO1_ASTAR with an identical, explicitly logged key
are joined. COST may be emitted after the A* search because map scans resume
asynchronously. Some real rail stock paths log only A* END: in that case a
matching CARTO1_QUEUE is required. Only the last episode of a repeated key
is used.
RAIL_ATTEMPT, RAIL_SEARCH, P5_RAIL_SEARCH and C56_TASK RAIL_SEARCH_END
are separate reference diagnostics: their src/dst fields do not identify the
same cargo, episode or map snapshot as a CARTO1_COST. Correlations here are
descriptive and cannot establish predictive or causal performance.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import statistics


LOG_NAME = re.compile(
    r"^(?P<policy>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$",
    re.I,
)
EVENT = re.compile(
    r"\bOPEX\s+(?P<date>\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(?P<tag>CARTO1_(?:START|QUEUE|BLOCK|COST|SKIP|ASTAR|SUMMARY)|"
    r"RAIL_ATTEMPT|RAIL_SEARCH|P5_RAIL_SEARCH)"
    r"(?:\s+(?P<fields>.*))?$"
)
C56_END = re.compile(
    r"\bOPEX\s+\d{4}-\d{1,2}-\d{1,2}\s+C56_TASK\s+"
    r"RAIL_SEARCH_END\s+(?P<fields>.*)$"
)
FIELD = re.compile(r"(?<!\S)([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)")
RAIL_TAGS = ("RAIL_ATTEMPT", "RAIL_SEARCH", "P5_RAIL_SEARCH", "C56_RAIL_SEARCH_END")
COST_KEYS = ("direct", "route", "blocks", "route_blocks", "water", "relief",
             "town", "direct_per_block", "route_per_block")
LIMITATIONS = [
    "CARTO1 est une mesure shadow : ni le coût cartographique ni la corrélation ne "
    "prouvent qu'une ligne est constructible ou plus rentable.",
    "Une jointure exige la même clé CARTO1, un COST valide et un END, avec "
    "START ou QUEUE précédent (stock rail). Le COST peut arriver après END.",
    "Si une clé apparaît dans plusieurs essais, seul le dernier END apparié "
    "est corrélé au dernier COST : le lien exact entre révisions est inconnu.",
    "Une même paire peut être recherchée plusieurs fois : les épisodes ne sont "
    "pas des observations indépendantes et les corrélations ne sont pas des tests.",
    "Les événements A* historiques RAIL_ATTEMPT/RAIL_SEARCH/P5/C56 sont affichés "
    "séparément : les relier à CARTO1 par src/dst serait ambigu.",
    "Les valeurs négatives sont des sentinelles absentes, exclues des mesures ; "
    "le dernier CARTO1_SUMMARY par fichier prévaut sur les précédents.",
    "route_per_block divise la somme des coûts grossiers du plus court trajet "
    "par ses blocs (lorsqu'elle est définie). Ce n'est pas un devis de travaux.",
]


def integer(value, *, nonnegative=True):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if not nonnegative or result >= 0 else None


def numeric(values):
    values = list(values)
    if not values:
        return {"n": 0, "sum": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(values), "sum": sum(values),
        "mean": round(statistics.mean(values), 3),
        "median": statistics.median(values),
        "min": min(values), "max": max(values),
    }


def correlation(rows, x_field, y_field):
    """Pearson r; null for insufficient data or zero variance in either variable."""
    pairs = [(r.get(x_field), r.get(y_field)) for r in rows]
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    n = len(pairs)
    result = {"n": n, "r": None}
    if n < 3:
        return result
    xs, ys = zip(*pairs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx > 0 and vy > 0:
        result["r"] = round(
            sum((x - mx) * (y - my) for x, y in pairs) / (vx * vy) ** 0.5, 6
        )
    return result


def event_line(line):
    """Return (event, string fields) for production OPEX lines with arbitrary prefixes."""
    match = EVENT.search(line.rstrip())
    if match:
        return match["tag"], dict(FIELD.findall(match["fields"] or ""))
    match = C56_END.search(line.rstrip())
    if match:
        return "C56_RAIL_SEARCH_END", dict(FIELD.findall(match["fields"]))
    return None


def identity(path):
    match = LOG_NAME.fullmatch(Path(path).name)
    if not match:
        raise ValueError(
            f"Nom de log non compatible <policy>_seed<N>_r<K>.log[.gz] : {path}"
        )
    return match["policy"], int(match["seed"]), int(match["repeat"])


def summarize_rail(events):
    by_tag = {}
    for tag in RAIL_TAGS:
        rows = events.get(tag, [])
        outcomes = Counter()
        metrics = defaultdict(list)
        for row in rows:
            outcome = row.get("outcome")
            if tag == "RAIL_ATTEMPT":
                outcome = ("OK" if row.get("ok") == "1" else row.get("reason")
                           if row.get("ok") == "0" else "UNKNOWN")
            outcomes[outcome or "UNKNOWN"] += 1
            for field in ("iters", "ops", "ticks", "search_ops", "budget"):
                value = integer(row.get(field))
                if value is not None:
                    metrics[field].append(value)
        by_tag[tag] = {
            "count": len(rows), "outcomes": dict(sorted(outcomes.items())),
            **{field: numeric(metrics[field]) for field in
               ("iters", "ops", "ticks", "search_ops", "budget")},
        }
    return by_tag


def summarize_joined(rows):
    by_outcome = {}
    for outcome in sorted({r["outcome"] for r in rows}):
        subset = [r for r in rows if r["outcome"] == outcome]
        by_outcome[outcome] = {
            "count": len(subset),
            **{name: numeric(r[name] for r in subset if r.get(name) is not None)
               for name in (*COST_KEYS, "iters", "ops", "ticks")},
        }
    correlations = {
        name: {
            target: correlation(rows, name, target)
            for target in ("success", "abandoned", "iters")
        }
        for name in COST_KEYS
    }
    return {"n": len(rows), "by_outcome": by_outcome, "correlations": correlations}


def parse_lines(lines, *, source="reference_seed42_r0.log"):
    """Produce a one-file report, preserving the timeline for cost/A* associations."""
    policy, seed, repeat = identity(source)
    counts = Counter()
    block_index = {}
    block_measurements = defaultdict(list)
    block_counters = Counter()
    queue_sources = Counter()
    queued_keys = set()
    skip_reasons = Counter()
    start_fields = None
    latest_cost = {}
    cost_count = Counter()
    cost_rows = []
    starts = Counter()
    astar_ends = Counter()
    completed_ends = defaultdict(list)
    astar_unpaired = 0
    ends_without_start_with_queue = 0
    astar_start_unpaired = 0
    joined = []
    summaries = []
    rail_events = defaultdict(list)
    warnings = []

    for line_number, raw in enumerate(lines, 1):
        parsed = event_line(raw)
        if parsed is None:
            continue
        tag, fields = parsed
        counts[tag] += 1
        if tag in RAIL_TAGS:
            rail_events[tag].append(fields)
            continue
        if tag == "CARTO1_START":
            start_fields = fields
            continue
        if tag == "CARTO1_SKIP":
            skip_reasons[fields.get("reason") or "unknown"] += 1
            continue
        if tag == "CARTO1_SUMMARY":
            summaries.append(fields)
            continue
        if tag == "CARTO1_QUEUE":
            queue_sources[fields.get("source", "unknown")] += 1
            if fields.get("key"):
                queued_keys.add(fields["key"])
            continue
        if tag == "CARTO1_BLOCK":
            bx, by = integer(fields.get("bx")), integer(fields.get("by"))
            if bx is None or by is None:
                warnings.append(f"{line_number}: CARTO1_BLOCK sans bx/by valides")
                continue
            block_id = fields.get("id")
            coord = (bx, by)
            if coord not in block_index:
                block_index[coord] = {"bx": bx, "by": by, "id": block_id, "reads": 0,
                                      "ops": 0, "ticks": 0}
            entry = block_index[coord]
            entry["reads"] += 1
            for name in ("ops", "ticks"):
                value = integer(fields.get(name))
                if value is not None:
                    entry[name] += value
                    block_measurements[name].append(value)
            for name in ("water", "relief", "town", "river", "sea", "blocked"):
                value = integer(fields.get(name))
                if value is not None:
                    block_counters[name] += value
            cost = integer(fields.get("cost"))
            if cost is not None:
                entry["cost"] = cost
            continue
        if tag == "CARTO1_COST":
            key = fields.get("key")
            if not key or key.count(":") < 3:
                warnings.append(f"{line_number}: CARTO1_COST sans clé complète")
                continue
            row = {name: integer(fields.get(name)) for name in COST_KEYS}
            if row["blocks"] and row["direct"] is not None:
                row["direct_per_block"] = round(row["direct"] / row["blocks"], 6)
            if row["route_blocks"] and row["route"] is not None:
                row["route_per_block"] = round(row["route"] / row["route_blocks"], 6)
            row["valid"] = integer(fields.get("valid"))
            row["key"] = key
            cost_rows.append(row)
            latest_cost[key] = row
            cost_count[key] += 1
            continue
        if tag == "CARTO1_ASTAR":
            key = fields.get("key")
            phase = fields.get("phase")
            if not key or key.count(":") < 3 or phase not in ("start", "end"):
                warnings.append(f"{line_number}: CARTO1_ASTAR sans key/phase valides")
                continue
            if phase == "start":
                starts[key] += 1
                continue
            outcome = fields.get("outcome") or "UNKNOWN"
            astar_ends[outcome] += 1
            if starts[key] < 1:
                # Production stock search and NOPA can emit END without START.
                # Require the logged CARTO1_QUEUE to establish the same key.
                if key not in queued_keys:
                    astar_unpaired += 1
                    continue
                ends_without_start_with_queue += 1
            else:
                starts[key] -= 1
            row = {"key": key, "outcome": outcome,
                   "success": int(outcome == "OK"),
                   "abandoned": int(outcome in ("ABND", "DEAD"))}
            row.update({name: integer(fields.get(name))
                        for name in ("iters", "ops", "ticks")})
            completed_ends[key].append(row)

    astar_start_unpaired = sum(starts.values())
    repeated_keys = []
    for key, ends in completed_ends.items():
        cost = latest_cost.get(key)
        if cost is None or cost.get("valid") != 1:
            continue
        if len(ends) > 1 or cost_count[key] > 1:
            repeated_keys.append(key)
        row = dict(ends[-1])
        row.update({name: cost[name] for name in COST_KEYS})
        joined.append(row)
    latest = summaries[-1] if summaries else None
    total_blocks = integer((latest or start_fields or {}).get("total_blocks"))
    read = integer((latest or {}).get("read"))
    if read is None and latest is not None:
        read = integer(latest.get("covered"))
    read_source = "summary" if read is not None else None
    if read is None and start_fields is not None:
        read = len(block_index)
        read_source = "observed_blocks"
    covered_pct = (round(read / total_blocks * 100, 3)
                   if read is not None and total_blocks and read <= total_blocks else None)
    by_block = sorted(block_index.values(), key=lambda r: (r["by"], r["bx"]))
    cost_valid = [r for r in cost_rows if r.get("valid") == 1]
    report = {
        "source": str(source), "policy": policy, "seed": seed, "repeat": repeat,
        "events": dict(sorted(counts.items())),
        "queue_sources": dict(sorted(queue_sources.items())),
        "skip_reasons": dict(sorted(skip_reasons.items())),
        "carto_start": start_fields,
        "last_summary": latest,
        "summary_count": len(summaries),
        "summary_work": {
            name: integer((latest or {}).get(name))
            for name in ("ops", "work_ops", "scans", "ticks", "overruns")
        },
        "coverage": {
            "total_blocks": total_blocks, "read": read, "percent": covered_pct,
            "read_source": read_source,
            "observed_unique_blocks": len(block_index),
        },
        "blocks": {
            "events": counts["CARTO1_BLOCK"], "unique": len(block_index),
            "ops": numeric(block_measurements["ops"]),
            "ticks": numeric(block_measurements["ticks"]),
            "tile_counters": dict(sorted(block_counters.items())),
            "by_block": by_block,
        },
        "costs": {
            "events": len(cost_rows), "valid": len(cost_valid),
            **{name: numeric(r[name] for r in cost_valid if r[name] is not None)
               for name in COST_KEYS},
        },
        "astar": {
            "starts": counts["CARTO1_ASTAR"] - sum(astar_ends.values()),
            "ends": sum(astar_ends.values()),
            "outcomes": dict(sorted(astar_ends.items())),
            "unpaired_ends": astar_unpaired,
            "unpaired_starts": astar_start_unpaired,
            "ends_without_start_with_queue": ends_without_start_with_queue,
        },
        "joined": {**summarize_joined(joined),
                   "repeated_keys": sorted(repeated_keys),
                   "completed_keys_without_valid_cost": sum(
                       key not in latest_cost or latest_cost[key]["valid"] != 1
                       for key in completed_ends)},
        "rail_diagnostics": summarize_rail(rail_events),
        "warnings": warnings,
    }
    return report, joined


def _open_log(path):
    if str(path).endswith(".log.gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def find_logs(inputs, policy=None):
    selected = {}
    for raw in inputs:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(path)
        candidates = path.iterdir() if path.is_dir() else (path,)
        for candidate in candidates:
            if not candidate.is_file() or LOG_NAME.fullmatch(candidate.name) is None:
                continue
            if policy is not None and identity(candidate)[0] != policy:
                continue
            selected[str(candidate.resolve())] = candidate
    if not selected:
        raise ValueError("Aucun journal <policy>_seed<N>_r<K>.log[.gz] trouvé")
    return [selected[key] for key in sorted(selected)]


def analyze_sources(sources):
    """Analyze (filename, iterable_of_lines) and never mix policies or seeds."""
    grouped = defaultdict(list)
    joined_all = defaultdict(list)
    for source, lines in sources:
        record, joined = parse_lines(lines, source=str(source))
        grouped[record["policy"]].append(record)
        joined_all[record["policy"]].extend(joined)
    return {
        "scope": "CARTO1_shadow_descriptive",
        "limitations": LIMITATIONS,
        "policies": {
            policy: {
                "seeds": sorted(grouped[policy],
                                key=lambda r: (r["seed"], r["repeat"], r["source"])),
                "pooled_joined": summarize_joined(joined_all[policy]),
            }
            for policy in sorted(grouped)
        },
    }


def analyze_paths(inputs, policy=None):
    paths = find_logs(inputs, policy)

    def sources():
        for path in paths:
            with _open_log(path) as handle:
                yield path, handle

    return analyze_sources(sources())


def render_markdown(report):
    lines = ["# CARTO-1 — cartographie shadow et A* rail", "",
             "Les corrélations r sont descriptives ; une case vide signifie non calculable.", ""]
    for policy, data in report["policies"].items():
        lines += [f"## {policy}", "",
                  "| Graine/rép. | Blocs vus/total | Couverture | Ops full6 Σ | "
                  "Ops travail Σ | Ticks full6 | Dépassements | "
                  "Coûts valides | A* fins OK/ABND/autres | Jointures |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for row in data["seeds"]:
            c, b, a = row["coverage"], row["blocks"], row["astar"]
            out = a["outcomes"]
            ok, abnd = out.get("OK", 0), out.get("ABND", 0)
            rest = a["ends"] - ok - abnd
            percent = f'{c["percent"]:.2f}%' if c["percent"] is not None else "?"
            lines.append(
                f'| {row["seed"]}/r{row["repeat"]} | {c["observed_unique_blocks"]}/'
                f'{c["total_blocks"] if c["total_blocks"] is not None else "?"} | '
                f'{percent} | {b["ops"]["sum"]} | '
                f'{row["summary_work"]["work_ops"]} | '
                f'{row["summary_work"]["ticks"]} | '
                f'{row["summary_work"]["overruns"]} | '
                f'{row["costs"]["valid"]} | {ok}/{abnd}/{rest} | {row["joined"]["n"]} |'
            )
        lines += ["", "### Blocs les plus coûteux (par graine, cinq au maximum)", "",
                  "| Graine/rép. | (bx, by) | Coût du bloc | Ops full6 Σ | Ticks full6 Σ | Lectures |",
                  "|---|---|---:|---:|---:|---:|"]
        for row in data["seeds"]:
            ordered = sorted((block for block in row["blocks"]["by_block"]
                              if "cost" in block),
                             key=lambda block: (-block["cost"], block["by"], block["bx"]))
            for block in ordered[:5]:
                lines.append(
                    f'| {row["seed"]}/r{row["repeat"]} | '
                    f'({block["bx"]}, {block["by"]}) | {block["cost"]} | '
                    f'{block["ops"]} | {block["ticks"]} | {block["reads"]} |'
                )
        if all(not r["blocks"]["by_block"] for r in data["seeds"]):
            lines.append("| — | — | — | — | — | — |")
        pooled = data["pooled_joined"]
        lines += ["", f'Jointures par clé : **{pooled["n"]}** épisodes.', "",
                  "| Coût | r(OK) [n] | r(ABND/DEAD) [n] | r(itérations) [n] |",
                  "|---|---:|---:|---:|"]
        for cost in COST_KEYS:
            corr = pooled["correlations"][cost]

            def display(target):
                result = corr[target]
                return f'{result["r"] if result["r"] is not None else "—"} [{result["n"]}]'

            lines.append(f'| {cost} | {display("success")} | {display("abandoned")} | '
                         f'{display("iters")} |')
        lines += ["", "Coûts par issue :", "",
                  "| Issue | n | route médiane | route/bloc médian | direct médiane | itérations médianes |",
                  "|---|---:|---:|---:|---:|---:|"]
        for outcome, stats in pooled["by_outcome"].items():
            lines.append(f'| {outcome} | {stats["count"]} | '
                         f'{stats["route"]["median"]} | '
                         f'{stats["route_per_block"]["median"]} | '
                         f'{stats["direct"]["median"]} | '
                         f'{stats["iters"]["median"]} |')
        lines += [""]
    lines += ["## Limites", ""] + [f"- {item}" for item in report["limitations"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("inputs", nargs="+", type=Path, help="Logs et dossiers *_engine")
    cli.add_argument("--policy", help="Filtrer la politique dans le nom des logs")
    cli.add_argument("--format", choices=("json", "markdown"), default="markdown")
    cli.add_argument("--out", type=Path, help="Rapport de sortie (sinon stdout)")
    args = cli.parse_args(argv)
    try:
        report = analyze_paths(args.inputs, policy=args.policy)
    except (ValueError, OSError) as exc:
        cli.error(str(exc))
    output = (json.dumps(report, ensure_ascii=False, indent=2) + "\n"
              if args.format == "json" else render_markdown(report))
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
