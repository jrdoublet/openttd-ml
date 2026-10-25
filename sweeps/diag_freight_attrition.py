"""Strict decoder for bounded 256x256 freight candidate attrition logs (schema 1).

One row is one *completed producer invocation*, not one selected/published project.
PO01C visits cargos in order and may stop after a cargo produces a candidate:
`cargo=OTHER visited_good=0` is an unvisited GOOD cargo, NOT zero GOOD losses.
No projected profit or recoverable route is inferred from these counters.
"""

import argparse
import gzip
import json
import re
import statistics
from datetime import date
from pathlib import Path


LINE = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) FREIGHT_ATTRITION(?:\s+|$)(.*)$")
SOURCE_LINE = re.compile(r"\bOPEX (\d{4})-(\d{1,2})-(\d{1,2}) FREIGHT_ATTRITION_SOURCE(?:\s+|$)(.*)$")
KEYS = frozenset(("schema", "path", "scope", "cargo", "visited_cargos",
                  "visited_good", "total", "good", "good_qpos", "good_served",
                  "good_zero", "good_kept", "good_other", "truncated", "bins"))
SAMPLE_META = frozenset(("source_samples", "truncated_sources"))
SOURCE_KEYS = frozenset(("schema", "path", "source", "src_tile", "station",
                         "monthly", "pairs", "min_town", "min_tile", "min_dist",
                         "max_town", "max_tile", "max_dist"))
COUNTS = ("visited_cargos", "visited_good", "total", "good", "good_qpos",
          "good_served", "good_zero", "good_kept", "good_other")
BANDS = ("le78", "79_160", "gt160")
SIDES = ("source", "destination", "both")
MATCHES = ("same", "other", "mixed", "unknown")
MAX_VALUE = 2147483647
MAX_SOURCE_FLUSH_DAYS = 30


def _integer(text, key):
    if not re.fullmatch(r"0|[1-9][0-9]*", text):
        raise ValueError(f"{key}: expected nonnegative decimal integer")
    value = int(text)
    if value > MAX_VALUE:
        raise ValueError(f"{key}: exceeds signed 32-bit range")
    return value


def decode_lines(lines, filename="<stream>"):
    rows = []
    pending_sources = []
    for number, line in enumerate(lines, 1):
        source_record = SOURCE_LINE.search(line)
        match = source_record or LINE.search(line)
        if not match:
            # SOURCE rows and the closing invocation must be contiguous among
            # Opex events. Raw engine logs also interleave the opponent's
            # [script:*] entries while the calendar advances between Info calls.
            if pending_sources and re.search(r"\bOPEX\s+", line):
                raise ValueError(f"{filename}:{number}: interrupted source sample block")
            # Truncated or corrupted target records must not become silent zeros.
            if "FREIGHT_ATTRITION" in line and "OPEX " in line:
                raise ValueError(f"{filename}:{number}: invalid FREIGHT_ATTRITION framing")
            continue
        try:
            year, month, day = map(int, match.group(1, 2, 3))
            if not 1970 <= year <= 2100:
                raise ValueError("invalid report date")
            event_date = date(year, month, day)  # Reject non-calendar dates.
            tokens = match.group(4).split()
            pairs = [t.split("=", 1) for t in tokens]
            if any(len(p) != 2 or not p[0] or not p[1] for p in pairs):
                raise ValueError("malformed key=value")
            fields = dict(pairs)
            expected = SOURCE_KEYS if source_record else KEYS
            if (len(fields) != len(pairs) or
                    (set(fields) != expected and not (
                        not source_record and set(fields) == KEYS | SAMPLE_META))):
                raise ValueError("missing, unknown or duplicated fields")
            if fields["schema"] != "1" or fields["path"] not in ("legacy", "po01c"):
                raise ValueError("unsupported schema/path")
            if source_record:
                fields_int = {key: _integer(fields[key], key)
                              for key in SOURCE_KEYS - {"schema", "path", "station"}}
                station = fields["station"]
                fields_int["station"] = (-1 if station == "-1"
                                         else _integer(station, "station"))
                if (fields_int["src_tile"] > 65535
                        or fields_int["min_tile"] > 65535
                        or fields_int["max_tile"] > 65535
                        or fields_int["monthly"] == 0
                        or fields_int["pairs"] == 0
                        or fields_int["min_dist"] > fields_int["max_dist"]
                        or fields_int["max_dist"] > 200
                        or (fields_int["pairs"] == 1
                            and (fields_int["min_town"], fields_int["min_tile"],
                                 fields_int["min_dist"]) != (
                                     fields_int["max_town"], fields_int["max_tile"],
                                     fields_int["max_dist"]))):
                    raise ValueError("invalid bounded source sample")
                pending_sources.append(dict(fields_int, path=fields["path"],
                                            year=year, month=month, day=day,
                                            file=filename, line=number))
                if len(pending_sources) > 8:
                    raise ValueError("too many source records in one invocation")
                continue
            if fields["scope"] != "invocation" or fields["cargo"] not in ("GOOD", "OTHER"):
                raise ValueError("unsupported scope/cargo")
            row = {key: _integer(fields[key], key) for key in COUNTS}
            bins = [_integer(token, "bins") for token in fields["bins"].split(",")]
            if len(bins) != 36:
                raise ValueError("36 attrition bins required")
            if fields["truncated"] not in ("0", "1"):
                raise ValueError("invalid truncated flag")
            row["truncated"] = int(fields["truncated"])
            if (row["visited_good"] > row["visited_cargos"]
                    or (row["visited_good"] > 0) != (fields["cargo"] == "GOOD")
                    or row["good"] > row["total"]
                    or row["good"] > 16384
                    or (row["truncated"] and row["good"] != 16384)
                    or row["good"] != row["good_qpos"] + row["good_zero"]
                    or row["good_qpos"] != (row["good_served"]
                                              + row["good_kept"] + row["good_other"])
                    or sum(bins) != row["good_served"]
                    or (row["visited_good"] == 0 and row["good"] != 0)):
                raise ValueError("incoherent attrition partition")
            row.update({"bins": bins, "path": fields["path"], "cargo": fields["cargo"],
                        "year": year, "month": month, "day": day,
                        "file": filename, "line": number})
            if set(fields) == KEYS:
                if pending_sources:
                    raise ValueError("source samples preceding historical record")
                row.update(samples=None, source_samples=None, truncated_sources=None)
            else:
                row["source_samples"] = _integer(fields["source_samples"], "source_samples")
                if fields["truncated_sources"] not in ("0", "1"):
                    raise ValueError("invalid truncated_sources flag")
                row["truncated_sources"] = int(fields["truncated_sources"])
                if (row["source_samples"] > 8 or row["source_samples"] != len(pending_sources)
                        or (row["truncated_sources"] and row["source_samples"] != 8)
                        or sum(s["pairs"] for s in pending_sources) > row["good_served"]
                        or len({s["source"] for s in pending_sources}) != len(pending_sources)
                        or any(s["path"] != row["path"] for s in pending_sources)
                        or (pending_sources and row["visited_good"] == 0)):
                    raise ValueError("source sample block inconsistent with invocation")
                previous_date = None
                for sample in pending_sources:
                    sample_date = date(sample["year"], sample["month"], sample["day"])
                    # OpexDecide's calendar can advance between individual Info
                    # calls. Keep only monotonically dated, contiguous batches.
                    if (sample_date > event_date
                            or (event_date - sample_date).days > MAX_SOURCE_FLUSH_DAYS
                            or (previous_date is not None and sample_date < previous_date)):
                        raise ValueError("source sample outside monotonic flush window")
                    previous_date = sample_date
                    # Source's original emission date stays visible for audit;
                    # attribution uses the final invocation date, including NYE.
                    sample["accounting_year"] = year
                row["samples"] = pending_sources
                pending_sources = []
            rows.append(row)
        except ValueError as exc:
            raise ValueError(f"{filename}:{number}: {exc}") from exc
    if pending_sources:
        raise ValueError(f"{filename}: source records without final invocation record")
    return rows


def _counts(rows):
    return {key: sum(row[key] for row in rows) for key in COUNTS + ("truncated",)}


def _distribution(values, bands):
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None,
                "bands": {name: 0 for name, _, _ in bands}}
    return {"count": len(values), "min": min(values), "median": statistics.median(values),
            "max": max(values),
            "bands": {name: sum(lower <= value <= upper for value in values)
                      for name, lower, upper in bands}}


def _source_years(rows):
    """Deduplicate only observed extreme towns and source identities, per game/seed/year.

    Input filenames distinguish arms/repeats; an unknown seed is not guessed.
    No inference about intermediate towns, distinct full candidate pairs or ROI.
    """
    groups = {}
    seed_rx = re.compile(r"(?:^|_)seed(\d+)_r(\d+)(?:\.log)?(?:\.gz)?$")
    for row in rows:
        if row["samples"] is None:
            continue
        key = (row["file"], row["year"])
        if key not in groups:
            match = seed_rx.search(Path(row["file"]).name)
            groups[key] = {"file": row["file"], "year": row["year"],
                           "seed": int(match.group(1)) if match else None,
                           "repeat": int(match.group(2)) if match else None,
                           "invocations": 0, "truncated_invocations": 0,
                           "sample_rows": 0, "sources": {}}
        group = groups[key]
        group["invocations"] += 1
        group["truncated_invocations"] += row["truncated_sources"]
        group["sample_rows"] += len(row["samples"])
        for sample in row["samples"]:
            ident = (sample["source"], sample["src_tile"])
            if ident not in group["sources"]:
                group["sources"][ident] = {
                    "source": sample["source"], "src_tile": sample["src_tile"],
                    "monthly_min": sample["monthly"], "monthly_max": sample["monthly"],
                    "min_dist": sample["min_dist"], "max_dist": sample["max_dist"],
                    "station_ids": set(), "towns_extremes": set(), "observations": 0}
            s = group["sources"][ident]
            s["monthly_min"] = min(s["monthly_min"], sample["monthly"])
            s["monthly_max"] = max(s["monthly_max"], sample["monthly"])
            s["min_dist"] = min(s["min_dist"], sample["min_dist"])
            s["max_dist"] = max(s["max_dist"], sample["max_dist"])
            s["station_ids"].add(sample["station"])
            s["towns_extremes"].update(((sample["min_town"], sample["min_tile"]),
                                        (sample["max_town"], sample["max_tile"])))
            s["observations"] += 1
    result = []
    for _, group in sorted(groups.items()):
        sources = sorted(group["sources"].values(), key=lambda s: (s["source"], s["src_tile"]))
        towns = set().union(*(s["towns_extremes"] for s in sources)) if sources else set()
        result.append({
            "file": group["file"], "seed": group["seed"], "repeat": group["repeat"],
            "year": group["year"], "invocations": group["invocations"],
            "truncated_invocations": group["truncated_invocations"],
            "sample_rows": group["sample_rows"],
            "distinct_sources_sampled": len(sources),
            "distinct_towns_at_extremes": len(towns),
            "monthly_max_per_source": _distribution([s["monthly_max"] for s in sources],
                (("1_31", 1, 31), ("32_63", 32, 63), ("64_127", 64, 127),
                 ("128_255", 128, 255), ("256_plus", 256, MAX_VALUE))),
            "shortest_per_source": _distribution([s["min_dist"] for s in sources],
                (("le78", 0, 78), ("79_160", 79, 160), ("161_200", 161, 200))),
            "longest_per_source": _distribution([s["max_dist"] for s in sources],
                (("le78", 0, 78), ("79_160", 79, 160), ("161_200", 161, 200))),
            "source_details": [dict((key, value) for key, value in s.items()
                                    if key not in ("station_ids", "towns_extremes")) | {
                "station_ids": sorted(s["station_ids"]),
                "towns_at_extremes": sorted([{"town": t, "tile": tile}
                                             for t, tile in s["towns_extremes"]],
                                            key=lambda x: (x["town"], x["tile"]))}
                for s in sources],
        })
    return result


def summarize(rows):
    by_band = {band: {side: {relation: 0 for relation in MATCHES}
                      for side in SIDES} for band in BANDS}
    for row in rows:
        for band_index, band in enumerate(BANDS):
            for side_index, side in enumerate(SIDES):
                for match_index, relation in enumerate(MATCHES):
                    index = band_index * 12 + side_index * 4 + match_index
                    by_band[band][side][relation] += row["bins"][index]
    observed = [row for row in rows if row["samples"] is not None]
    annual = _source_years(rows)
    return {
        "schema": 1,
        "generations": len(rows),
        "coverage": {
            "good_visited_generations": sum(row["visited_good"] > 0 for row in rows),
            "good_unvisited_generations": sum(row["visited_good"] == 0 for row in rows),
            "truncated_generations": sum(row["truncated"] for row in rows),
            "historical_no_source_probe": len(rows) - len(observed),
            "source_probe_invocations": len(observed),
            "source_probe_zero_sample_invocations": sum(not row["samples"] for row in observed),
            "source_probe_truncated_invocations": sum(row["truncated_sources"] for row in observed),
        },
        "total": _counts(rows),
        "by_path": {path: _counts([row for row in rows if row["path"] == path])
                    for path in ("legacy", "po01c")},
        "by_band": by_band,
        "source_years": annual,
        "records": [{k: v for k, v in row.items() if k not in ("bins", "samples")} for row in rows],
    }


def render(result):
    if result["generations"] == 0:
        print("Aucun événement FREIGHT_ATTRITION : couverture inconnue, pas zéro rejet GOOD.")
        return
    cover = result["coverage"]
    counts = result["total"]
    print(f"Générations terminées={result['generations']} ; GOOD visité="
          f"{cover['good_visited_generations']} ; GOOD non visité="
          f"{cover['good_unvisited_generations']} ; tronquées="
          f"{cover['truncated_generations']}")
    print(f"GOOD positif (paires observées)={counts['good_qpos']} ; "
          f"origin_served={counts['good_served']} ; candidats={counts['good_kept']} ; "
          f"autres refus de candidats={counts['good_other']} ; production nulle="
          f"{counts['good_zero']}")
    print(f"Échantillon sources : invocations mesurées="
          f"{cover['source_probe_invocations']}, historiques sans sonde="
          f"{cover['historical_no_source_probe']}, mesurées sans source="
          f"{cover['source_probe_zero_sample_invocations']}, cap atteint="
          f"{cover['source_probe_truncated_invocations']}")
    for entry in result["source_years"]:
        print(f"  seed={entry['seed']} an={entry['year']} "
              f"usines distinctes ÉCHANTILLONNÉES={entry['distinct_sources_sampled']} "
              f"villes distinctes parmi extrêmes={entry['distinct_towns_at_extremes']} "
              f"troncatures={entry['truncated_invocations']}; "
              f"q mensuel max/source={entry['monthly_max_per_source']['median']} médiane, "
              f"trajet le plus court/source={entry['shortest_per_source']['median']} médiane, "
              f"le plus long/source={entry['longest_per_source']['median']} médiane")
    print("| Distance | Source (même/autre/mixte/inconnu) | "
          "Destination (même/autre/mixte/inconnu) | Deux (même/autre/mixte/inconnu) |")
    print("|---|---|---|---|")
    for band in BANDS:
        columns = ["/".join(str(result["by_band"][band][side][m]) for m in MATCHES)
                   for side in SIDES]
        print(f"| {band} | " + " | ".join(columns) + " |")
    print("Ces paires ne sont ni uniques entre générations ni des projets construisibles.")
    print("Villes distinctes = seulement les extrêmes échantillonnés, ni inventaire ni ROI/quai.")


def read_paths(paths):
    rows = []
    for path in paths:
        path = Path(path)
        files = sorted(path.glob("*.log*")) if path.is_dir() else [path]
        for filename in files:
            if filename.suffix not in (".log", ".gz"):
                continue
            opener = gzip.open if filename.suffix == ".gz" else open
            with opener(filename, "rt", encoding="utf-8", errors="strict") as fh:
                rows.extend(decode_lines(fh, str(filename)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="moteur .log[.gz] ou répertoire")
    parser.add_argument("--json", action="store_true", help="JSON strict sur stdout")
    args = parser.parse_args()
    result = summarize(read_paths(args.paths))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        render(result)


if __name__ == "__main__":
    main()
