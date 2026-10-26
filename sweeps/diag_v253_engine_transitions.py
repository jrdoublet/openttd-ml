"""Descriptive V252 engine replacement matrix for the open V253 aircraft task.

Read existing C66 engine logs only; do not run OpenTTD or infer incremental
profit. An observed V252_REPLACE is a transaction, NOT proof of a good chooser.
``old_veh`` and ``new_veh`` are vehicle IDs, not fleet sizes.

Usage: python -X utf8 sweeps/diag_v253_engine_transitions.py PATH [PATH ...]
"""

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from statistics import median


NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$")
EVENT = re.compile(
    r"\[0\]\s+\[I\]\s+OPEX\s+(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})\s+"
    r"(?P<tag>V252_REPLACE|V252_SKIP)\b(?P<fields>[^\r\n]*)"
)
KV = re.compile(r"\b([A-Za-z_]\w*)=(\S+)")
REPLACEMENT_FIELDS = ("line", "old_engine", "new_engine", "price", "age", "profit")


def _stream(path, binary=False):
    mode = "rb" if binary else "rt"
    extra = {} if binary else {"encoding": "utf-8", "errors": "replace"}
    return (gzip.open(path, mode, **extra) if str(path).endswith(".gz")
            else open(path, mode, **extra))


def content_hash(path):
    digest = hashlib.sha256()
    with _stream(path, binary=True) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inputs_to_games(inputs):
    files = {}
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            candidates = [p for p in path.iterdir() if p.is_file() and NAME.fullmatch(p.name)]
        elif path.is_file() and NAME.fullmatch(path.name):
            candidates = [path]
        else:
            raise ValueError(f"journal ou repertoire moteur V253 inexistant : {path}")
        files.update((str(p.resolve()), p.resolve()) for p in candidates)
    if not files:
        raise ValueError("aucun journal *_seedN_rR.log[.gz]")
    groups = defaultdict(list)
    for path in files.values():
        logical_name = path.name[:-3] if path.name.endswith(".gz") else path.name
        match = NAME.fullmatch(logical_name)
        key = (str(path.parent), match["arm"], int(match["seed"]), int(match["repeat"]))
        groups[key].append((logical_name, path))
    result = []
    for key, copies in sorted(groups.items()):
        names = {name for name, _ in copies}
        if len(names) != 1:
            raise ValueError(f"identite de partie V253 ambigue : {key}, {sorted(names)}")
        digests = [(path, content_hash(path)) for _, path in copies]
        if len({digest for _, digest in digests}) != 1:
            raise ValueError(f"copies texte/gzip contradictoires : {[str(p) for p, _ in digests]}")
        preferred = sorted((path for _, path in copies), key=lambda p: p.suffix == ".gz")[0]
        result.append((key, preferred, [str(p) for p, _ in digests]))
    return result


def _number(value, *, allow_negative=False):
    if value is None:
        return None
    try:
        result = int(value)
        return result if allow_negative or result >= 0 else None
    except ValueError:
        return None


def parse_events(path):
    """Yield replacement or skip; missing fields remain None, never zero."""
    with _stream(path) as stream:
        for log_line_index, raw in enumerate(stream):
            match = EVENT.search(raw)
            if not match:
                continue
            pairs = KV.findall(match["fields"])
            if len(pairs) != len({name for name, _ in pairs}):
                raise ValueError(f"champ V252 duplique dans {path}: {match['fields']}")
            fields = dict(pairs)
            event_date = (f"{int(match['year']):04d}-{int(match['month']):02d}-"
                          f"{int(match['day']):02d}")
            if match["tag"] == "V252_SKIP":
                yield {"type": "skip", "year": int(match["year"]),
                       "date": event_date, "reason": fields.get("reason"),
                       "log_line_index": log_line_index}
                continue
            # Historical line profit may be negative; unlike an invalid engine
            # ID or purchase price, it is a legitimate observed measurement.
            values = {name: _number(fields.get(name), allow_negative=(name == "profit"))
                      for name in REPLACEMENT_FIELDS}
            yield {"type": "replace", "year": int(match["year"]),
                   "date": event_date, "log_line_index": log_line_index, **values,
                   "fields_missing_or_invalid": [name for name, value in values.items()
                                                 if value is None]}


def aggregate(events):
    transitions, new_engines, years, skips = Counter(), Counter(), Counter(), Counter()
    prices = defaultdict(list)
    unique_lines = set()
    missing = Counter()
    replacements = 0
    for event in events:
        if event["type"] == "skip":
            skips[event["reason"] if event["reason"] is not None else "<missing>"] += 1
            continue
        replacements += 1
        years[event["year"]] += 1
        missing.update(event["fields_missing_or_invalid"])
        old, new = event["old_engine"], event["new_engine"]
        if old is not None and new is not None:
            transitions[f"{old}->{new}"] += 1
            new_engines[str(new)] += 1
        if event["line"] is not None:
            unique_lines.add(event["line"])
        if new is not None and event["price"] is not None:
            prices[str(new)].append(event["price"])
    return {
        "replacements": replacements,
        "classified_transitions": sum(transitions.values()),
        "distinct_line_ids_with_replacements": len(unique_lines),
        "transitions": dict(sorted(transitions.items())),
        "new_engines": dict(sorted(new_engines.items(), key=lambda p: int(p[0]))),
        "replacements_by_year": dict(sorted(years.items())),
        "skip_events_by_reason": dict(sorted(skips.items())),
        "missing_or_invalid_replacement_fields": dict(sorted(missing.items())),
        "observed_price_median_by_new_engine": {
            key: median(values) for key, values in sorted(prices.items(), key=lambda p: int(p[0]))
        },
    }


def analyze(inputs):
    games = inputs_to_games(inputs)
    rows = []
    by_arm_events = defaultdict(list)
    by_arm_distinct_game_lines = defaultdict(int)
    for (directory, arm, seed, repeat), path, source_files in games:
        events = list(parse_events(path))
        by_arm_events[arm].extend(events)
        game_stats = aggregate(events)
        by_arm_distinct_game_lines[arm] += game_stats["distinct_line_ids_with_replacements"]
        rows.append({"directory": directory, "arm": arm, "seed": seed,
                     "repeat": repeat, "source_files": source_files,
                     **game_stats})
    return {
        "scope": "observed V252 replacement events only; not a marginal profit or V102 estimate",
        "logical_games": len(games),
        "physical_files": sum(len(row["source_files"]) for row in rows),
        "by_arm": {
            arm: {**aggregate(events),
                  "distinct_game_line_pairs_with_replacements":
                      by_arm_distinct_game_lines[arm]}
            for arm, events in sorted(by_arm_events.items())
        },
        "games": rows,
        "limitations": [
            "Vehicle IDs old_veh/new_veh are not fleet counts.",
            "Recorded price is purchase price, not net cash or lifetime cost.",
            "Recorded profit is historical line profit, not causal replacement gain.",
            "Skip events can repeat while a financial condition persists.",
            "Identical text/gzip copies count once; contradictory copies fail closed.",
            "Arm-level distinct_line_ids_with_replacements omits game identity "
            "and aliases repeated local IDs; use distinct_game_line_pairs_with_replacements.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        report = analyze(args.inputs)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
