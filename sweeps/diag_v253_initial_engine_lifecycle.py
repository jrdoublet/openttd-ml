"""V253: link observed AIR_BUILD engines to later V252 replacements in each game.

This is a descriptive, host-only join on the local ``line`` identifier within
one (directory, experiment arm, seed, repeat).  A replacement is NOT evidence
of a profitable upgrade; lines with no replacement are not necessarily active
through the end of the simulation.

Usage: python -X utf8 sweeps/diag_v253_initial_engine_lifecycle.py LOG_DIR
"""

import argparse
from collections import Counter
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re
from statistics import median

try:
    from sweeps.diag_v253_engine_transitions import (
        KV, _number, _stream, inputs_to_games, parse_events,
    )
except ModuleNotFoundError as error:
    if error.name != "sweeps":
        raise
    # Direct invocation: ``python sweeps/diag_v253_initial_engine_lifecycle.py``.
    from diag_v253_engine_transitions import (
        KV, _number, _stream, inputs_to_games, parse_events,
    )


AIR_BUILD = re.compile(
    r"\[0\]\s+\[I\]\s+OPEX\s+(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})\s+"
    r"AIR_BUILD\b(?P<fields>[^\r\n]*)"
)


def read_builds(path):
    """Return observed builds; invalid line numbers cannot be joined."""
    with _stream(path) as stream:
        for log_line_index, raw in enumerate(stream):
            match = AIR_BUILD.search(raw)
            if not match:
                continue
            pairs = KV.findall(match["fields"])
            if len(pairs) != len({key for key, _ in pairs}):
                raise ValueError(f"AIR_BUILD champ duplique : {path}: {match['fields']}")
            fields = dict(pairs)
            yield {
                "log_line_index": log_line_index,
                "year": int(match["year"]),
                "date": (f"{int(match['year']):04d}-{int(match['month']):02d}-"
                         f"{int(match['day']):02d}"),
                "line": _number(fields.get("line")),
                "engine": _number(fields.get("engine")),
                "dist": _number(fields.get("dist")),
                "planes": _number(fields.get("planes")),
            }


def _rows_for_game(path):
    builds = list(read_builds(path))
    by_line = {}
    for build in builds:
        line = build["line"]
        if line is None:
            continue
        if line in by_line:
            raise ValueError(f"AIR_BUILD ligne locale repetee : {path}, line={line}")
        by_line[line] = build

    v252_events = list(parse_events(path))
    replacements = [row for row in v252_events if row["type"] == "replace"]
    observed_build = bool(builds)
    observed_v252 = bool(v252_events)
    first_seen = set()
    result = {
        "build_events": len(builds),
        "air_build_marker_observed": observed_build,
        "v252_marker_observed": observed_v252,
        "lifecycle_coverage": ("both_markers_observed" if observed_build and observed_v252
                               else "partial_markers_observed" if observed_build or observed_v252
                               else "unknown_no_markers"),
        "distinct_built_lines": len(by_line),
        "builds_missing_line": sum(row["line"] is None for row in builds),
        "builds_missing_engine": sum(row["engine"] is None for row in builds),
        "builds_by_initial_engine": dict(sorted(Counter(
            str(row["engine"]) for row in builds if row["engine"] is not None
        ).items(), key=lambda item: int(item[0]))),
        "replacement_events": len(replacements),
        "replacements_missing_line": 0,
        "replacements_without_prior_build": 0,
        "replacements_with_prior_build": 0,
        "distinct_built_lines_with_replacement": 0,
        "distinct_built_lines_without_observed_replacement": 0,
        "first_replacement_initial_to_new": {},
        "first_replacement_old_to_new": {},
        "first_replacement_old_disagrees_initial": 0,
        "first_replacement_disagreements": [],
    }
    first_transitions = Counter()
    actual_transitions = Counter()
    age_observations = []
    for replace in replacements:
        line = replace["line"]
        if line is None:
            result["replacements_missing_line"] += 1
            continue
        build = by_line.get(line)
        if (build is None or build["log_line_index"] >= replace["log_line_index"] or
                build["date"] > replace["date"]):
            result["replacements_without_prior_build"] += 1
            continue
        result["replacements_with_prior_build"] += 1
        if line in first_seen:
            continue
        first_seen.add(line)
        initial, old, new = build["engine"], replace["old_engine"], replace["new_engine"]
        elapsed_days = (date.fromisoformat(replace["date"]) -
                        date.fromisoformat(build["date"])).days
        if initial is not None:
            age_observations.append((str(initial), elapsed_days))
        if initial is not None and new is not None:
            first_transitions[f"{initial}->{new}"] += 1
        if old is not None and new is not None:
            actual_transitions[f"{old}->{new}"] += 1
        if initial is not None and old is not None and initial != old:
            result["first_replacement_old_disagrees_initial"] += 1
            result["first_replacement_disagreements"].append({
                "line": line, "initial_engine": initial, "old_engine": old,
                "new_engine": new, "build_date": build["date"],
                "replacement_date": replace["date"], "elapsed_days": elapsed_days,
            })
    result["distinct_built_lines_with_replacement"] = len(first_seen)
    result["distinct_built_lines_without_observed_replacement"] = len(by_line) - len(first_seen)
    result["first_replacement_initial_to_new"] = dict(sorted(first_transitions.items()))
    result["first_replacement_old_to_new"] = dict(sorted(actual_transitions.items()))
    result["_age_observations"] = age_observations
    return result


def _age_summary(observations):
    by_engine = defaultdict(list)
    for engine, days in observations:
        by_engine[engine].append(days)
    return {
        engine: {"n": len(values), "min": min(values),
                 "median": median(values), "max": max(values)}
        for engine, values in sorted(by_engine.items(), key=lambda item: int(item[0]))
    }


def analyze(inputs):
    games = inputs_to_games(inputs)
    summaries = []
    age_by_arm = defaultdict(list)
    for (directory, arm, seed, repeat), path, sources in games:
        data = _rows_for_game(path)
        ages = data.pop("_age_observations")
        age_by_arm[arm].extend(ages)
        data["first_replacement_delay_days_by_initial_engine"] = _age_summary(ages)
        summaries.append({"directory": directory, "arm": arm, "seed": seed,
                          "repeat": repeat, "source_files": sources, **data})
    by_arm = {}
    for arm in sorted({game["arm"] for game in summaries}):
        selected = [game for game in summaries if game["arm"] == arm]
        summed = {field: sum(game[field] for game in selected) for field in (
            "build_events", "distinct_built_lines", "builds_missing_line",
            "builds_missing_engine", "replacement_events", "replacements_missing_line",
            "replacements_without_prior_build", "replacements_with_prior_build",
            "distinct_built_lines_with_replacement",
            "distinct_built_lines_without_observed_replacement",
            "first_replacement_old_disagrees_initial",
        )}
        for key in ("builds_by_initial_engine", "first_replacement_initial_to_new",
                    "first_replacement_old_to_new"):
            counter = Counter()
            for game in selected:
                counter.update(game[key])
            summed[key] = dict(sorted(counter.items()))
        summed["first_replacement_delay_days_by_initial_engine"] = _age_summary(age_by_arm[arm])
        summed["first_replacement_disagreements"] = [
            {"directory": game["directory"], "seed": game["seed"],
             "repeat": game["repeat"], **row}
            for game in selected for row in game["first_replacement_disagreements"]
        ]
        summed["games_with_both_lifecycle_markers"] = sum(
            game["lifecycle_coverage"] == "both_markers_observed" for game in selected)
        summed["games_with_partial_lifecycle_markers"] = sum(
            game["lifecycle_coverage"] == "partial_markers_observed" for game in selected)
        summed["games_without_lifecycle_markers"] = sum(
            game["lifecycle_coverage"] == "unknown_no_markers" for game in selected)
        summed["lifecycle_coverage"] = (
            "unknown" if summed["games_without_lifecycle_markers"] == len(selected)
            else "partial" if (summed["games_without_lifecycle_markers"] or
                                   summed["games_with_partial_lifecycle_markers"])
            else "both_markers_observed")
        by_arm[arm] = {"logical_games": len(selected), **summed}
    return {
        "scope": "observed AIR_BUILD to first subsequent V252_REPLACE per game-line; descriptive only",
        "logical_games": len(summaries), "by_arm": by_arm, "games": summaries,
        "limitations": [
            "AIR_BUILD engine is the engine at line creation; not the complete model-choice candidate set.",
            "The build cost/profit fields are estimates, not observed incremental profit.",
            "Replacement is not a causal improvement; unmatched lines can predate the log or lack a build event.",
            "Initial-to-new is a historical endpoint pair, not necessarily the engine physically removed; "
            "use first_replacement_old_to_new for the directly logged replacement.",
            "A line without replacement is not proven to remain operational throughout the horizon.",
            "Elapsed calendar days to first logged replacement describe observed transactions, "
            "not engine longevity or a replacement profit effect.",
            "Local line IDs are never matched across different games, arms or repeats.",
            "No AIR_BUILD or V252 marker in a log means instrumentation is unknown, "
            "not evidence that no AIR lines or replacements existed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, help="New JSON file (never overwrite); default stdout")
    args = parser.parse_args()
    try:
        report = analyze(args.inputs)
        body = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(body)
        else:
            print(body, end="")
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
