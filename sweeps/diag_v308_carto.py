#!/usr/bin/env python3
"""V308: compare cinq motifs de sondage 8x8 a la verite exhaustive.

Usage: python sweeps/diag_v308_carto.py results/<campaign>_engine [--json out.json]
Les comptes de rivieres vus sont un indice de detection, pas une reconstruction de
leur connexite: seul le balayage des 64 tuiles etablit une riviere traversante.
"""

import argparse
import gzip
import hashlib
import json
import re
import statistics
from pathlib import Path


ARM_NAMES = ("v307", "full6", "short6", "parity6", "flatdry6")
CLASSES = ("sea", "lake", "river", "coast", "house", "town", "city", "obst", "mountain", "river_cross")
PATTERN = re.compile(r"\bV308_BLOCK\s+(.*)$")
EVENT_PATTERN = re.compile(r"\bV308_(START|BLOCK|END)\s+(.*)$")
EXPECTED_BLOCKS = 400
GAME_NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")
TRUTH_FIELDS = ("n", "sea", "lake", "river", "river_cross", "coast", "house", "town", "build", "road", "obst", "relief")
ARM_FIELDS = ("n", "sea", "lake", "river", "coast", "house", "town", "obst", "relief", "ops")


def parse_fields(payload):
    fields = {}
    for part in payload.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        try:
            fields[key] = int(value)
        except ValueError:
            fields[key] = value
    return fields


def logs(paths):
    selected_physical = set()
    selected_games = {}
    for path in paths:
        path = Path(path)
        if path.is_dir():
            candidates = sorted(path.rglob("*.log")) + sorted(path.rglob("*.log.gz"))
        elif path.is_file():
            candidates = [path]
        else:
            continue
        for file in candidates:
            resolved = file.resolve()
            if resolved in selected_physical:
                continue
            selected_physical.add(resolved)
            basename = file.name[:-3] if file.name.endswith(".gz") else file.name
            match = GAME_NAME.fullmatch(basename)
            parent = str(file.parent.resolve())
            if match:
                identity = (parent, match["arm"], int(match["seed"]),
                            int(match["repeat"]))
            else:
                identity = (parent, basename)
            if identity in selected_games:
                previous, previous_basename = selected_games[identity]
                if basename != previous_basename:
                    raise ValueError(f"identite V308 ambigue : {previous} / {file}")
                if _digest_text(previous) != _digest_text(file):
                    raise ValueError(f"copies V308 contradictoires : {previous} / {file}")
                continue
            selected_games[identity] = (file, basename)
            yield file


def _digest_text(path):
    """Hash uncompressed bytes; never load a whole engine log in memory."""
    digest = hashlib.sha256()
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.digest()


def complete_record(fields):
    """Ne pas assimiler une mesure manquante ou impossible a une classe observee."""
    required = ("i", "bx", "by") + tuple("t_" + key for key in TRUTH_FIELDS)
    required += tuple(name + "_" + key for name in ARM_NAMES for key in ARM_FIELDS)
    if any(not isinstance(fields.get(key), int) for key in required):
        return False
    if fields["t_n"] != 64 or fields["t_river_cross"] not in (0, 1):
        return False
    if any(fields[name + "_n"] != expected for name, expected in
           (("v307", 5), ("full6", 6), ("parity6", 6))):
        return False
    if any(fields[name + "_n"] not in (4, 6) for name in ("short6", "flatdry6")):
        return False
    if any(fields["t_" + key] < 0 or fields["t_" + key] > 64
           for key in TRUTH_FIELDS if key not in ("relief", "river_cross")):
        return False
    for name in ARM_NAMES:
        if any(fields[name + "_" + key] < 0
               or fields[name + "_" + key] > fields[name + "_n"]
               for key in ARM_FIELDS if key not in ("n", "relief", "ops")):
            return False
    if any(fields[name + "_relief"] < 0 for name in ("t",) + ARM_NAMES):
        return False
    if any(fields[name + "_ops"] < 0 for name in ARM_NAMES):
        return False
    return True


def read_blocks(paths):
    """Read valid individual blocks (permissive API for exploratory fixtures)."""
    for path in logs(paths):
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                match = PATTERN.search(line)
                if match:
                    fields = parse_fields(match.group(1))
                    if complete_record(fields):
                        fields["source"] = str(path)
                        yield fields


def read_complete_surveys(paths):
    """Read complete probe runs; reject partial/duplicate data before reporting.

    Each physical game log must contain exactly one START, 400 valid unique
    indexed BLOCK records, and a matching END. `read_blocks` intentionally
    remains permissive for diagnostics on partial synthetic inputs.
    """
    for path in logs(paths):
        opener = gzip.open if path.suffix == ".gz" else open
        started = False
        ended = False
        indices = set()
        rows = []
        with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                match = EVENT_PATTERN.search(line)
                if not match:
                    continue
                kind, payload = match.groups()
                fields = parse_fields(payload)
                if kind == "START":
                    if started or ended or fields.get("n") != EXPECTED_BLOCKS:
                        raise ValueError(f"V308 START absent, duplique ou n invalide : {path}")
                    started = True
                elif kind == "BLOCK":
                    if not started or ended or not complete_record(fields):
                        raise ValueError(f"V308 BLOCK hors sondage ou invalide : {path}")
                    index = fields["i"]
                    if not 0 <= index < EXPECTED_BLOCKS or index in indices:
                        raise ValueError(f"V308 BLOCK indice invalide ou duplique : {path} i={index}")
                    indices.add(index)
                    fields["source"] = str(path)
                    rows.append(fields)
                else:
                    if not started or ended or fields.get("n") != EXPECTED_BLOCKS:
                        raise ValueError(f"V308 END absent, duplique ou n invalide : {path}")
                    if len(indices) != EXPECTED_BLOCKS:
                        raise ValueError(
                            f"V308 sondage incomplet : {path} "
                            f"{len(indices)}/{EXPECTED_BLOCKS} indices")
                    ended = True
        if not started or not ended:
            raise ValueError(f"V308 START/END manquant : {path}")
        yield from rows


def is_present(record, prefix, kind):
    if kind == "mountain":
        return record.get(prefix + "_relief", 0) >= 4
    if kind == "city":
        return record.get(prefix + "_house", 0) >= 2 or record.get(prefix + "_town", 0) >= 3
    if kind == "river_cross":
        return record.get(prefix + ("_river_cross" if prefix == "t" else "_river"), 0) > 0
    return record.get(prefix + "_" + kind, 0) > 0


def percentile(values, percent):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * percent / 100
    lo = int(position)
    hi = min(lo + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (position - lo), 1)


def summarize(blocks):
    rows = []
    for name in ARM_NAMES:
        ops = [b[name + "_ops"] for b in blocks]
        classes = {}
        for kind in CLASSES:
            truth = [is_present(b, "t", kind) for b in blocks]
            seen = [is_present(b, name, kind) for b in blocks]
            positives = sum(truth)
            negatives = len(truth) - positives
            missed = sum(t and not s for t, s in zip(truth, seen))
            false = sum(not t and s for t, s in zip(truth, seen))
            classes[kind] = {
                "truth": positives, "missed": missed,
                "miss_pct": round(100 * missed / positives, 1) if positives else None,
                "false_pos": false,
                "false_pct": round(100 * false / negatives, 1) if negatives else None,
            }
        rows.append({
            "motif": name, "n": len(blocks), "ops_median": statistics.median(ops) if ops else None,
            "ops_p90": percentile(ops, 90), "ops_total": sum(ops),
            "ops_mean": round(statistics.mean(ops), 1) if ops else None,
            "four_point_blocks": sum(b[name + "_n"] == 4 for b in blocks),
            "classes": classes,
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Dossiers de campagne ou journaux")
    parser.add_argument("--json", type=Path, help="Exporter un tableau machine")
    args = parser.parse_args()
    blocks = list(read_complete_surveys(args.paths))
    rows = summarize(blocks)
    print(f"V308: {len(blocks)} blocs complets (5 bras + verite)")
    for row in rows:
        print(f"{row['motif']:9s} ops median={row['ops_median']} p90={row['ops_p90']}")
        for kind, fields in row["classes"].items():
            print(f"  {kind:12s} truth={fields['truth']:4d} missed={fields['missed']:4d} "
                  f"miss%={fields['miss_pct']} fp={fields['false_pos']:4d} fp%={fields['false_pct']}")
    if args.json:
        args.json.write_text(json.dumps({"blocks": len(blocks), "rows": rows}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
