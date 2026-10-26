#!/usr/bin/env python3
"""Read-only V303 exposure of the current synchronous V294f reverse probe.

Counts actual V294F_PROBE outcomes, their consumed iterations and candidate
Manhattan distance from existing OpexAI engine logs. This cannot measure
wall time, saved opcodes or a resumable V303 variant that was never run.

Example:
  python -X utf8 sweeps/diag_v303_reverse_probe.py \
    results/rail_cal4_40x10_multimodal_pc_20261021_engine \
    --arm reference --expected-games 40
"""

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from statistics import median


NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<rep>\d+)\.log(?:\.gz)?$")
LINE = re.compile(r"\[0\]\s+\[I\]\s+OPEX\s+(?P<year>\d{4})-\d{1,2}-\d{1,2}\s+V294F_PROBE\s+(?P<payload>[^\r\n]*)")
TOKEN = re.compile(r"([a-z_][a-z_0-9]*)=(\S+)")
BINS = ((0, 80, "0-79"), (80, 160, "80-159"),
        (160, 250, "160-249"), (250, None, "250+"))


def _open(path, mode):
    return (gzip.open if path.suffix == ".gz" else open)(path, mode)


def _digest(path):
    h = hashlib.sha256()
    with _open(path, "rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def read_events(path, cap):
    events = []
    with _open(path, "rt") as stream:
        for line_no, raw in enumerate(stream, 1):
            found = LINE.search(raw)
            if not found:
                continue
            parts = found["payload"].split()
            matched = [TOKEN.fullmatch(part) for part in parts]
            context = f"{path}:{line_no}"
            if any(part is None for part in matched):
                raise ValueError(f"malformed V294F_PROBE payload: {context}")
            names = [part[1] for part in matched]
            if len(set(names)) != len(names):
                raise ValueError(f"duplicate V294F_PROBE field: {context}")
            fields = {part[1]: part[2] for part in matched}
            if any(key not in fields for key in ("ok", "iters", "manh")):
                raise ValueError(f"missing V294F_PROBE field: {context}")
            try:
                ok = int(fields["ok"])
                iterations = int(fields["iters"])
                distance = int(fields["manh"])
                year = int(found["year"])
            except ValueError as exc:
                raise ValueError(f"invalid V294F_PROBE integer: {context}") from exc
            if (ok not in (0, 1) or iterations < 0 or iterations > cap
                    or distance < 0 or year < 1900 or year > 2100):
                raise ValueError(f"out of range V294F_PROBE: {context}")
            if ok == 1 and iterations == 0:
                raise ValueError(f"successful V294F_PROBE without iterations: {context}")
            distance_band = next(label for lo, hi, label in BINS
                                 if distance >= lo and (hi is None or distance < hi))
            events.append({"year": year, "distance_manhattan": distance,
                           "band": distance_band, "ok": bool(ok),
                           "iterations": iterations})
    return events


def _metrics(events, cap):
    total = len(events)
    found = [event for event in events if event["ok"]]
    return {
        "attempts": total,
        "found": len(found),
        "not_found": total - len(found),
        "found_pct": round(len(found) * 100 / total, 3) if total else None,
        "at_iteration_cap": sum(event["iterations"] == cap for event in events),
        "iterations_sum": sum(event["iterations"] for event in events),
        "iterations_median": median([event["iterations"] for event in events]) if total else None,
        "found_iterations_median": median([event["iterations"] for event in found]) if found else None,
        "not_found_iterations_median": median([event["iterations"] for event in events if not event["ok"]]) if len(found) < total else None,
    }


def analyze(path, arm="reference", expected_games=40, cap=300):
    if not Path(path).is_dir() or expected_games < 1 or cap < 1:
        raise ValueError("invalid V303 input directory, game count or iteration cap")
    paths = sorted([*Path(path).glob("*.log"), *Path(path).glob("*.log.gz")])
    if not paths:
        raise ValueError(f"no engine logs in {path}")
    games = {}
    copies_collapsed = 0
    for file in paths:
        match = NAME.fullmatch(file.name)
        if match is None or match["arm"] != arm:
            continue
        identity = (arm, int(match["seed"]), int(match["rep"]))
        basename = file.name[:-3] if file.suffix == ".gz" else file.name
        digest = _digest(file)
        if identity in games:
            existing = games[identity]
            if basename != existing["basename"] or digest != existing["digest"]:
                raise ValueError(f"contradictory or ambiguous V303 game copies: {existing['path']} / {file}")
            copies_collapsed += 1
            continue
        games[identity] = {"basename": basename, "digest": digest,
                           "path": str(file), "events": read_events(file, cap)}
    if len(games) != expected_games:
        raise ValueError(f"expected {expected_games} games for arm={arm}; found {len(games)}")
    by_band = defaultdict(list)
    by_year = defaultdict(list)
    per_game = []
    all_events = []
    for identity, game in sorted(games.items()):
        events = game["events"]
        all_events.extend(events)
        for event in events:
            by_band[event["band"]].append(event)
            by_year[str(event["year"])].append(event)
        per_game.append({"arm": identity[0], "seed": identity[1],
                         "repeat": identity[2], **_metrics(events, cap)})
    return {
        "source_directory": str(path), "arm": arm, "iteration_cap": cap,
        "games": len(games), "games_with_events": sum(bool(g["events"]) for g in games.values()),
        "games_without_events": sum(not g["events"] for g in games.values()),
        "log_gzip_copies_collapsed": copies_collapsed,
        "overall": _metrics(all_events, cap),
        "by_manhattan_band": {label: _metrics(by_band[label], cap) for _, _, label in BINS},
        "by_year": {year: _metrics(rows, cap) for year, rows in sorted(by_year.items())},
        "per_game": per_game,
        "limits": [
            "manh is the logged candidate Manhattan distance, not built-track length",
            "not_found includes exhausted cap and missing initial endpoints, not only impossible paths",
            "iteration counts are not elapsed ticks or measured opcodes",
            "event groups are observational; the same candidate may be retried",
            "no comparison with a V303 resumable or alternating implementation exists",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--arm", default="reference")
    parser.add_argument("--expected-games", type=int, default=40)
    parser.add_argument("--cap", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.directory, args.arm, args.expected_games, args.cap)
    except (OSError, ValueError, EOFError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
