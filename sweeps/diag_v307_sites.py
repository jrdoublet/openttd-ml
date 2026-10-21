#!/usr/bin/env python3
"""V307S (1.8) : exposition des sites disperses dans les journaux moteur.

Usage : python sweeps/diag_v307_sites.py --logs results/<campaign>_engine
Le nombre de lignes construites est observe via RAIL_BUILD ; ``pred_profit``
n'est PAS un profit realise et est toujours etiquete comme une prediction.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
from pathlib import Path
import re
from statistics import median


SEED_RE = re.compile(r"(?P<arm>.+)_seed(?P<seed>\d+)_r\d+\.log(?:\.gz)?$")
EVENT_RE = re.compile(r"\bOPEX\s+(?P<date>\d{4}-\d{1,2}-\d{1,2})\s+"
                      r"(?P<event>RAIL_ATTEMPT|RAIL_BUILD|V307S_PLANS)\s+(?P<fields>.*)$")
FIELD_RE = re.compile(r"([a-zA-Z][a-zA-Z_0-9]*)=([^\s]+)")
FAIL_RE = re.compile(r"\[0\] \[S\] Your script made an error")


def percentile(values: list[int], percent: int):
    if not values:
        return None
    seq = sorted(values)
    return seq[(percent * (len(seq) - 1) + 99) // 100]


def parse_logs(paths):
    """Collect per-arm observations without merging two distinct seeds."""
    attempts, sites, builds = [], [], []
    files = Counter()
    script_errors = Counter()
    for path in paths:
        match = SEED_RE.search(path.name)
        if match is None:
            continue
        arm, seed = match.group("arm"), int(match.group("seed"))
        files[arm] += 1
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if FAIL_RE.search(line):
                    script_errors[arm] += 1
                event = EVENT_RE.search(line)
                if event is None:
                    continue
                fields = dict(FIELD_RE.findall(event.group("fields")))
                record = dict(fields, arm=arm, seed=seed, date=event.group("date"))
                name = event.group("event")
                if name == "RAIL_ATTEMPT":
                    attempts.append(record)
                elif name == "RAIL_BUILD":
                    builds.append(record)
                elif name == "V307S_PLANS":
                    sites.append(record)
    return {"attempts": attempts, "sites": sites, "builds": builds,
            "files": files, "script_errors": script_errors}


def summarise(observations):
    report = {}
    arms = sorted(observations["files"])
    for arm in arms:
        attempts = [x for x in observations["attempts"] if x["arm"] == arm]
        sites = [x for x in observations["sites"] if x["arm"] == arm]
        builds = [x for x in observations["builds"] if x["arm"] == arm]
        reasons = Counter(x.get("reason", "UNKNOWN") for x in attempts)
        octants = defaultdict(list)
        ops = defaultdict(list)
        plans = defaultdict(list)
        for record in sites:
            side = record.get("side", "?")
            for label, target in (("oct_n", octants), ("ops", ops), ("plans", plans)):
                try:
                    target[side].append(int(record[label]))
                except (KeyError, ValueError):
                    pass
        report[arm] = {
            "files": observations["files"][arm],
            "script_errors": observations["script_errors"][arm],
            "attempts": len(attempts), "reasons": reasons,
            "abnd_siteb": reasons["ABND"] + reasons["SITEB"],
            "sites": len(sites),
            "sides": {
                side: {
                    "octants_median": median(octants[side]) if octants[side] else None,
                    "plans_median": median(plans[side]) if plans[side] else None,
                    "ops_median": median(ops[side]) if ops[side] else None,
                    "ops_p90": percentile(ops[side], 90),
                    "ops_n": len(ops[side]),
                }
                for side in sorted(set(octants) | set(ops) | set(plans))
            },
            "rail_builds": len(builds),
            "builds_by_seed": dict(sorted(Counter(x["seed"] for x in builds).items())),
            "pred_profit_sum": sum(int(x.get("pred_profit", "0")) for x in builds),
            "real_profit": None,  # RAIL_BUILD does not contain realised profit.
        }
    return report


def format_report(report):
    lines = ["| Bras | Logs | RAIL_ATTEMPT | ABND | SITEA | SITEB | SITEAB | ABND+SITEB | RAIL construites | Erreurs script |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, row in report.items():
        r = row["reasons"]
        lines.append(f'| {arm} | {row["files"]} | {row["attempts"]} | {r["ABND"]} | '
                     f'{r["SITEA"]} | {r["SITEB"]} | {r["SITEAB"]} | '
                     f'{row["abnd_siteb"]} | {row["rail_builds"]} | {row["script_errors"]} |')
    lines += ["", "| Bras | Cote | Appels | Octants med. | Plans med. | Ops med. | Ops p90 |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for arm, row in report.items():
        for side, values in row["sides"].items():
            lines.append(f'| {arm} | {side} | {values["ops_n"]} | '
                         f'{values["octants_median"]} | {values["plans_median"]} | '
                         f'{values["ops_median"]} | {values["ops_p90"]} |')
    lines += ["", "Remarque : `pred_profit` dans RAIL_BUILD est un profit **predit**, "
                    "pas le profit reel de la ligne. La mesure des profits reels demande "
                    "une telemetrie des lignes distincte."]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(p for p in args.logs.iterdir() if p.name.endswith((".log", ".log.gz")))
    observations = parse_logs(paths)
    if not observations["files"]:
        parser.error("aucun journal moteur attendu (arm_seedN_rN.log) dans --logs")
    print(format_report(summarise(observations)))


if __name__ == "__main__":
    main()
