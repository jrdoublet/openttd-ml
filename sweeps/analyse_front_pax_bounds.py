#!/usr/bin/env python3
"""FRONT-PAX-1: analyse descriptive des FRONT_PAX_BOUNDS des journaux moteur.

Exemple (PowerShell, aucun OpenTTD requis) :
  python -B sweeps/analyse_front_pax_bounds.py "results/bench_engine/*.log" --start-year 1970 --end-year 1979 --json-out rapport.json --markdown-out rapport.md

Une observation = un recalcul des bornes sous DECISION_LOG, pas une liaison
construite. Les valeurs *100 sont des centiemes de jour tronques par Squirrel.
Une annee observee ne signifie PAS que sa couverture est exhaustive.
Les bras/repetitions restent distincts, meme pour une graine commune.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import glob
import json
import math
from pathlib import Path
import re
from statistics import mean, median


EVENT = re.compile(
    r"\bOPEX\s+(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
    r"\s+FRONT_PAX_BOUNDS(?:\s+(?P<payload>.*))?$"
)
FIELD = re.compile(r"(?P<key>[A-Za-z][A-Za-z0-9_]*)=(?P<value>\S+)")
SEED = re.compile(r"(?:^|[_-])seed(?P<seed>\d+)(?=$|[_-])", re.I)
REPEAT = re.compile(r"(?:^|[_-])r(?P<repeat>\d+)(?=$|[_-])", re.I)

CATEGORIES = ("road_reason", "rail_clamp", "rail_model", "rail_bound")
NUMERICS = (
    "road_raw", "road_delta", "road_num", "road_denom", "road_M",
    "rail_raw", "rail_source", "rail_road_floor", "rail_map_cap", "rail_max",
    "train", "plane", "airport", "air_div",
    "rail_tau100", "air_tau100", "rail_dwell100", "air_fixed100",
)
REASONS = {
    "road_reason": {"ok", "missing_mode", "delta_nonpositive",
                    "denom_nonpositive", "num_nonpositive", "minimum"},
    "rail_clamp": {"none", "map_span", "rail_max", "road_max"},
    "rail_model": {"missing_mode", "rail_faster", "crossing"},
    "rail_bound": {"v294", "v168", "iterations"},
}
# Les branches s'appliquent dans cet ordre dans OpexRefreshEpochBounds.
RAIL_CLAMP_ORDER = ("map_span", "road_max", "rail_max")
METRICS = (
    "road_raw", "road_delta", "road_num", "road_denom", "road_M",
    "rail_raw", "rail_source", "rail_road_floor", "rail_map_cap",
    "rail_max", "rail_raw_minus_max", "rail_source_minus_max", "air_div",
    "rail_tau100", "air_tau100", "rail_tau_gap100",
    "rail_dwell100", "air_fixed100",
)
MAX_ISSUES = 100


def reason_components(name, value):
    """Retourne les causes elementaires dans l'ordre Squirrel, ou None.

    Ne pas assimiler les sequences invalides (ex. rail_max+map_span)
    aux motifs successifs de l'implementation courante.
    """
    parts = value.split("+")
    if name == "road_reason":
        if parts[0] not in REASONS[name]:
            return None
        if len(parts) == 1 or (len(parts) == 2 and parts[1] == "map_span"):
            return parts
        return None
    if name == "rail_clamp":
        if value == "none":
            return parts
        if not parts or any(p not in RAIL_CLAMP_ORDER for p in parts):
            return None
        if list(parts) != [p for p in RAIL_CLAMP_ORDER if p in parts]:
            return None
        return parts
    return parts if value in REASONS[name] else None


def source_identity(path):
    """Inferer la graine sans confondre le bras et la repetition du duel."""
    stem = Path(path).stem
    match = SEED.search(stem)
    if match:
        seed = int(match.group("seed"))
        prefix = stem[:match.start()].strip("-_") or "unspecified"
    else:
        fallback = re.search(r"(?:^|[_-])(\d+)(?:_r\d+)?$", stem)
        seed = int(fallback.group(1)) if fallback else None
        prefix = stem[:fallback.start()].strip("-_") if fallback else stem
        if not prefix:
            prefix = "unspecified"
    repeat = REPEAT.search(stem)
    run = prefix + (":r" + repeat.group("repeat") if repeat else ":r?")
    return seed, run


def _issue(path, line_no, code, detail):
    return {"file": str(path), "line": line_no, "code": code,
            "detail": str(detail)[:200]}


def parse_log_lines(lines, path="<memory>"):
    """Parse le marqueur reel, tout prefixe [script] admis, erreurs explicites.

    Renvoie (observations, anomalies, compteur_marqueurs).
    Les lignes des autres sondes sont ignorees. Une ligne malformed n'est pas
    convertie en une observation partielle.
    """
    observations, errors = [], []
    markers = 0
    seed, run = source_identity(path)
    for line_no, raw in enumerate(lines, 1):
        if "FRONT_PAX_BOUNDS" not in raw:
            continue
        markers += 1
        match = EVENT.search(raw.rstrip("\r\n"))
        if not match:
            errors.append(_issue(path, line_no, "bad_prefix", raw.strip()))
            continue
        try:
            stamp = date(int(match["year"]), int(match["month"]), int(match["day"]))
        except ValueError:
            errors.append(_issue(path, line_no, "invalid_date", match.group(0)))
            continue

        tokens = (match["payload"] or "").split()
        fields = {}
        invalid = []
        for token in tokens:
            item = FIELD.fullmatch(token)
            if item is None:
                invalid.append("bad_token:" + token)
                continue
            key, value = item["key"], item["value"]
            if key in fields:
                invalid.append("duplicate_field:" + key)
            else:
                fields[key] = value
        missing = (set(CATEGORIES) | set(NUMERICS)) - set(fields)
        if missing:
            invalid.append("missing:" + ",".join(sorted(missing)))
        unexpected = set(fields) - (set(CATEGORIES) | set(NUMERICS))
        if unexpected:
            invalid.append("unknown:" + ",".join(sorted(unexpected)))
        values = {}
        for name in CATEGORIES:
            if name in fields:
                if reason_components(name, fields[name]) is None:
                    invalid.append("invalid_category:" + name + "=" + fields[name])
                else:
                    values[name] = fields[name]
        for name in NUMERICS:
            if name not in fields:
                continue
            try:
                # air_div seul peut etre non entier (le reste vient de tointeger).
                value = float(fields[name]) if name == "air_div" else int(fields[name])
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError("nonfinite")
                if name == "road_raw" and value < -1:
                    raise ValueError("invalid_road_raw_sentinel")
                if name in ("rail_raw", "rail_source", "rail_max", "rail_tau100",
                            "air_tau100", "rail_dwell100", "air_fixed100") and value < 0:
                    raise ValueError("negative")
                if name in ("rail_road_floor", "rail_map_cap") and value not in (0, 1):
                    raise ValueError("invalid_flag")
                if name == "air_div" and value <= 0:
                    raise ValueError("nonpositive")
                values[name] = value
            except ValueError:
                invalid.append("invalid_number:" + name + "=" + fields[name])
        if invalid:
            errors.append(_issue(path, line_no, "malformed_event", ";".join(invalid)))
            continue
        values.update({
            "date": stamp.isoformat(), "year": stamp.year,
            "seed": seed, "run": run, "file": str(path), "line": line_no,
        })
        observations.append(values)
    return observations, errors, markers


def _distribution(values):
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {"n": len(ordered), "min": ordered[0], "max": ordered[-1],
            "mean": round(mean(ordered), 3),
            "median": median(ordered)}


def _summarize(records):
    counts = {name: dict(sorted(Counter(row[name] for row in records).items()))
              for name in CATEGORIES}
    # Motifs exacts ET attribution non exclusive des causes elementaires :
    # map_span+rail_max produit 1 dans chaque cause, 1 dans la chaine exacte.
    causes = {
        name: dict(sorted(Counter(
            part for row in records for part in reason_components(name, row[name])
            if part not in ("none", "ok")
        ).items()))
        for name in ("road_reason", "rail_clamp")
    }
    data = {name: [] for name in METRICS}
    for row in records:
        for name in METRICS:
            if name == "rail_raw_minus_max":
                value = row["rail_raw"] - row["rail_max"]
            elif name == "rail_source_minus_max":
                value = row["rail_source"] - row["rail_max"]
            elif name == "rail_tau_gap100":
                value = row["rail_tau100"] - row["air_tau100"]
            else:
                value = row[name]
            data[name].append(value)
    dates = sorted({row["date"] for row in records})
    return {
        "n": len(records), "distinct_dates": len(dates),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "motives": counts,
        "causes": causes,
        "road_raw_unavailable": sum(r["road_raw"] == -1 for r in records),
        "rail_road_floor_applied": sum(r["rail_road_floor"] == 1 for r in records),
        "rail_map_cap_applied": sum(r["rail_map_cap"] == 1 for r in records),
        "rail_raw_above_max": sum(r["rail_raw"] > r["rail_max"] for r in records),
        "rail_raw_equal_max": sum(r["rail_raw"] == r["rail_max"] for r in records),
        # Separer sentinelle -1 (garde precoce) du calcul du seuil brut.
        "road_raw_known": _distribution([r["road_raw"] for r in records
                                           if r["road_raw"] != -1]),
        "values": {name: _distribution(values) for name, values in data.items()},
    }


def analyze_files(paths, expected_years=None):
    """Agrege (run, seed, annee) ; doublons exacts exclus, conflits conserves."""
    files = sorted({str(Path(path).resolve()) for path in paths})
    expected = sorted(set(expected_years)) if expected_years is not None else None
    observations, problems, file_coverage = [], [], []
    seen = set()
    raw_events = 0
    duplicates = 0
    for filename in files:
        seed, run = source_identity(filename)
        with open(filename, encoding="utf-8", errors="replace") as stream:
            events, errors, markers = parse_log_lines(stream, filename)
        raw_events += len(events)
        problems.extend(errors)
        dupe_file = 0
        for row in events:
            signature = (
                run, seed, row["date"],
                tuple((field, row[field]) for field in CATEGORIES + NUMERICS),
            )
            if signature in seen:
                duplicates += 1
                dupe_file += 1
                if len(problems) < MAX_ISSUES:
                    problems.append(_issue(filename, row["line"], "duplicate_event",
                                           "exact repeated run/seed/date/payload"))
                continue
            seen.add(signature)
            observations.append(row)
        if seed is None:
            problems.append(_issue(filename, 0, "unidentified_seed",
                                   "filename has no recognizable seed; kept separate"))
        file_coverage.append({
            "file": filename, "seed": seed, "run": run, "markers": markers,
            "parsed_before_duplicates": len(events),
            "parse_errors": len(errors), "duplicates": dupe_file,
            "unique_events": len(events) - dupe_file,
            "observed_years": sorted({r["year"] for r in events}),
        })

    # Une repetition reelle de recalcul au meme jour peut avoir une valeur
    # differente : garder ces observations, sans presumer un seul refresh/jour.
    group = defaultdict(list)
    per_run_seed = defaultdict(set)
    for row in observations:
        key = (row["run"], row["seed"], row["year"])
        group[key].append(row)
        per_run_seed[(row["run"], row["seed"])].add(row["year"])
    rows = []
    for (run, seed, year), subset in sorted(
            group.items(), key=lambda x: (x[0][0], -1 if x[0][1] is None
                                          else x[0][1], x[0][2])):
        rows.append({"run": run, "seed": seed, "year": year, **_summarize(subset)})
    seed_coverage = [{
        "run": run, "seed": seed, "observed_years": sorted(years),
        "missing_expected_years": [y for y in expected if y not in years]
        if expected is not None else None,
        "gaps_between_observed_years": [
            y for y in range(min(years), max(years) + 1) if y not in years
        ],
        "full_year_coverage_proven": False,
    } for (run, seed), years in sorted(
        per_run_seed.items(), key=lambda x: (x[0][0], -1 if x[0][1] is None else x[0][1]))]
    global_counts = _summarize(observations)
    return {
        "schema": "front_pax_bounds_v2",
        "interpretation": "diagnostic_only; counts are refresh events, not built routes",
        "coverage_note": "year presence does not prove full year, seed, or game coverage",
        "files": len(files), "events": raw_events,
        "unique_events": len(observations), "duplicates": duplicates,
        "parse_errors": sum(item["parse_errors"] for item in file_coverage),
        "unidentified_seed_files": sum(item["seed"] is None for item in file_coverage),
        "expected_years": expected, "file_coverage": file_coverage,
        "seed_coverage": seed_coverage,
        "by_seed_year": rows, "overall": global_counts,
        "issues": problems[:MAX_ISSUES],
        "issues_truncated": max(0, len(problems) - MAX_ISSUES),
    }


def expand_log_patterns(patterns):
    files = set()
    unmatched = []
    for pattern in patterns:
        matches = [Path(p) for p in glob.glob(str(pattern), recursive=True)]
        selected = [p for p in matches if p.is_file() and p.suffix.lower() == ".log"]
        if not selected:
            unmatched.append(str(pattern))
        files.update(p.resolve() for p in selected)
    return sorted(files), unmatched


def render_markdown(result):
    coverage = result
    lines = [
        "# FRONT-PAX-1 — bornes observées (shadow)",
        "",
        "Diagnostic descriptif seulement : aucun gain AIR/RAIL n'est inféré.",
        "",
        "## Couverture",
        "",
        f"- Fichiers : {coverage['files']}; marqueurs valides : {coverage['events']}; "
        f"uniques : {coverage['unique_events']}; doublons exacts : {coverage['duplicates']}.",
        f"- Erreurs de parsing : {coverage['parse_errors']}; fichiers sans graine : "
        f"{coverage['unidentified_seed_files']}.",
        "- Une année observée ne prouve ni couverture annuelle complète ni fin de partie.",
        "",
        "| Exécution | Graine | Années observées | Années attendues manquantes |",
        "|---|---:|---|---|",
    ]
    for row in coverage["seed_coverage"]:
        observed = ",".join(map(str, row["observed_years"]))
        missing = row["missing_expected_years"]
        lines.append(f"| {row['run']} | {row['seed'] if row['seed'] is not None else '?'} "
                     f"| {observed} | {','.join(map(str, missing)) if missing is not None else 'non renseignées'} |")
    lines.extend(["", "## Par graine, année et exécution", "",
                  "| Exécution | Graine | Année | N | road_reason | rail_clamp | rail_model | rail_raw méd. | rail_max méd. | rail_tau100 méd. | air_tau100 méd. |",
                  "|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|"])
    for row in result["by_seed_year"]:
        def fmt_counter(key):
            return ", ".join(f"{k}:{v}" for k, v in row["motives"][key].items())
        lines.append(
            f"| {row['run']} | {row['seed'] if row['seed'] is not None else '?'} "
            f"| {row['year']} | {row['n']} | {fmt_counter('road_reason')} "
            f"| {fmt_counter('rail_clamp')} | {fmt_counter('rail_model')} "
            f"| {row['values']['rail_raw']['median']} | {row['values']['rail_max']['median']} "
            f"| {row['values']['rail_tau100']['median']} | {row['values']['air_tau100']['median']} |"
        )
    lines.extend(["", "## Motifs globaux (chaînes exactes)", "",
                  "| Catégorie | Motif exact | Recalculs |", "|---|---|---:|"])
    for category, counts in result["overall"]["motives"].items():
        for name, count in counts.items():
            lines.append(f"| {category} | {name} | {count} |")
    lines.extend(["", "## Causes élémentaires (non exclusives)", "",
                  "| Catégorie | Cause | Recalculs |", "|---|---|---:|"])
    for category, counts in result["overall"]["causes"].items():
        for name, count in counts.items():
            lines.append(f"| {category} | {name} | {count} |")
    lines.extend([
        "",
        f"- road_raw=-1 (pas de seuil brut, garde précoce) : {result['overall']['road_raw_unavailable']}.",
        f"- rail_road_floor=1 : {result['overall']['rail_road_floor_applied']}.",
        f"- rail_map_cap=1 : {result['overall']['rail_map_cap_applied']}.",
    ])
    lines.extend(["", "## Distributions globales", "",
                  "| Champ | N | Minimum | Médiane | Moyenne | Maximum |",
                  "|---|---:|---:|---:|---:|---:|"])
    for name, values in result["overall"]["values"].items():
        lines.append(f"| {name} | {values['n']} | {values.get('min', '—')} "
                     f"| {values.get('median', '—')} | {values.get('mean', '—')} "
                     f"| {values.get('max', '—')} |")
    lines.extend(["", "## Anomalies (échantillon)", ""])
    if not result["issues"]:
        lines.append("Aucune.")
    else:
        for issue in result["issues"][:30]:
            lines.append(f"- {issue['file']}:{issue['line']} "
                         f"{issue['code']}: {issue['detail']}")
        if len(result["issues"]) > 30 or result["issues_truncated"]:
            lines.append("- D'autres anomalies sont répertoriées dans le JSON.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", nargs="+", help="Logs engine .log (globs entre guillemets)")
    parser.add_argument("--start-year", type=int)
    parser.add_argument("--end-year", type=int)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="Retour 1 si parsing invalide ou graine inconnue ; doublons descriptifs toleres")
    args = parser.parse_args(argv)
    if (args.start_year is None) != (args.end_year is None):
        parser.error("--start-year et --end-year sont indissociables")
    if args.start_year is not None and args.end_year < args.start_year:
        parser.error("--end-year doit être >= --start-year")
    if args.json_out is not None and args.markdown_out is not None:
        if args.json_out.resolve() == args.markdown_out.resolve():
            parser.error("JSON et Markdown doivent avoir des chemins distincts")
    for output in (args.json_out, args.markdown_out):
        if output is not None and output.exists():
            parser.error("refus d'écraser le fichier existant : " + str(output))
    paths, unmatched = expand_log_patterns(args.patterns)
    if unmatched:
        parser.error("aucun journal .log pour : " + ", ".join(unmatched))
    if not paths:
        parser.error("aucun journal .log fourni")
    years = range(args.start_year, args.end_year + 1) if args.start_year is not None else None
    result = analyze_files(paths, expected_years=years)
    markdown = render_markdown(result)
    if args.json_out:
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.write_text(markdown, encoding="utf-8")
    if not args.markdown_out:
        print(markdown, end="")
    # Deux recalculs independants peuvent produire la meme charge utile un
    # meme jour : faute d'identifiant de refresh, le doublon reste un
    # diagnostic et n'invalide pas a lui seul la sante du journal.
    return int(bool(args.strict and (result["parse_errors"]
                                     or result["unidentified_seed_files"])))


if __name__ == "__main__":
    raise SystemExit(main())
