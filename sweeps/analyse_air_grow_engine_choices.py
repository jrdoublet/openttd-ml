"""Count actual AIR_GROW_MARGINAL engine choices from script-debug logs.

Each phase is counted separately: rank, execute and purchase logs are not
independent buying decisions. Unknown (-1) engines are excluded from exposure.
No OpenTTD runtime or third-party modules required.

Usage:
    python -X utf8 sweeps/analyse_air_grow_engine_choices.py results/my_campaign_engine
    python -X utf8 sweeps/analyse_air_grow_engine_choices.py "results/*_engine/*.log"
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import glob
from pathlib import Path
import re


MARKER = "AIR_GROW_MARGINAL "
FIELDS = re.compile(r"([a-z_]+)=([^\s]+)")


def parse_record(line: str):
    if MARKER not in line:
        return None
    fields = dict(FIELDS.findall(line.split(MARKER, 1)[1]))
    if "phase" not in fields or "fallback" not in fields:
        return None
    try:
        old = int(fields.get("old_engine", "-1"))
        buy = int(fields.get("buy_engine", "-1"))
    except ValueError:
        old, buy = -1, -1
    return {
        "phase": fields["phase"],
        "fallback": fields["fallback"],
        "decision": fields.get("decision", "unknown"),
        "old_engine": old,
        "buy_engine": buy,
        "rot_old": fields.get("rot_old", "unknown"),
        "rot_buy": fields.get("rot_buy", "unknown"),
    }


def summarize(records):
    phases = defaultdict(lambda: {
        "rows": 0, "accept": 0, "known_engines": 0, "different_engines": 0,
        "different_accepted": 0, "fallbacks": Counter(),
        "rotation_sources_different_engine": Counter(),
        "engine_pairs": Counter(),
    })
    for record in records:
        if record is None:
            continue
        stat = phases[record["phase"]]
        stat["rows"] += 1
        if record["decision"] == "accept":
            stat["accept"] += 1
        stat["fallbacks"][record["fallback"]] += 1
        old, buy = record["old_engine"], record["buy_engine"]
        if record["fallback"] != "none" or old < 0 or buy < 0:
            continue
        stat["known_engines"] += 1
        if old != buy:
            stat["different_engines"] += 1
            stat["engine_pairs"][(old, buy)] += 1
            stat["rotation_sources_different_engine"][(record["rot_old"], record["rot_buy"])] += 1
            if record["decision"] == "accept":
                stat["different_accepted"] += 1
    return phases


def expand_logs(args):
    paths = []
    for expression in args:
        matches = glob.glob(expression, recursive=True) if glob.has_magic(expression) else [expression]
        for match in matches:
            path = Path(match)
            if path.is_dir():
                paths.extend(path.rglob("*.log"))
            elif path.is_file():
                paths.append(path)
    return sorted(set(paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", help="Log files, directory paths or file globs")
    args = parser.parse_args()
    paths = expand_logs(args.logs)
    if not paths:
        parser.error("Aucun fichier .log trouve : verifier le repertoire *_engine et --script-debug")

    def records():
        for path in paths:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    record = parse_record(line)
                    if record is not None:
                        yield record

    result = summarize(records())
    print(f"Logs lus: {len(paths)} (phases = traces, PAS choix d'achat independants)")
    if not result:
        print("Aucune trace AIR_GROW_MARGINAL : verifier probes=258 et --script-debug")
        raise SystemExit(1)
    for phase, stat in sorted(result.items()):
        print(f"phase={phase} rows={stat['rows']} accept={stat['accept']} "
              f"known={stat['known_engines']} different={stat['different_engines']} "
              f"different_accept={stat['different_accepted']}")
        for (old, buy), count in stat["engine_pairs"].most_common():
            print(f"  moteur {old} -> {buy}: {count} traces")
        for (old_rot, buy_rot), count in stat["rotation_sources_different_engine"].most_common():
            print(f"  rotation {old_rot} -> {buy_rot}: {count} traces")
        unknown = stat["rows"] - stat["known_engines"]
        if unknown:
            print(f"  {unknown} traces sans moteurs fiables (fallback ou ID inconnu)")
    print("ATTENTION : les phases rank/purchase peuvent concerner la meme ligne/date;")
    print("une phase=purchase accept est une estimation, pas une preuve d'avion achete.")


if __name__ == "__main__":
    main()
