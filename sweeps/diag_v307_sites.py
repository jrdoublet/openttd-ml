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


def iso_state(observations):
    """V307S=3 : cout du complement rapporte a la spirale du MEME appel (iso-etat)."""
    lines = ["| Bras | Appels v=3 | Epuisees | Complement tente | Quais ajoutes | "
             "Ratio ops/spirale med. | p90 | max |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    by_arm = defaultdict(list)
    for record in observations["sites"]:
        if "spiral_ops" in record:
            by_arm[record["arm"]].append(record)
    for arm, calls in sorted(by_arm.items()):
        ratios = []
        for rec in calls:
            spiral_ops = int(rec["spiral_ops"])
            if spiral_ops > 0:
                ratios.append(int(rec["ops"]) / spiral_ops)
        exhausted = sum(1 for rec in calls if rec.get("max_ring") == "-1")
        tried = sum(1 for rec in calls if int(rec.get("extra_ops", "0")) > 0
                    and rec.get("max_ring") != "-1")
        added = sum(int(rec.get("native_added", "0")) for rec in calls)
        seq = sorted(ratios)
        lines.append(f"| {arm} | {len(calls)} | {exhausted} | {tried} | {added} | "
                     f"{median(seq):.3f} | {percentile_float(seq, 90):.3f} | {seq[-1]:.3f} |"
                     if seq else f"| {arm} | {len(calls)} | {exhausted} | {tried} | {added} | - | - | - |")
    return "\n".join(lines)


def percentile_float(values, percent):
    if not values:
        return float("nan")
    seq = sorted(values)
    return seq[(percent * (len(seq) - 1) + 99) // 100]


def autopsy(observations):
    """Pre-existing logs: annual empty-plan rates; newer logs: first empty stage.

    Stages are conditional diagnostic bounds, never an inference from opcodes.
    """
    groups = defaultdict(list)
    for record in observations["sites"]:
        key = (record["arm"], record["date"][:4], record.get("side", "?"),
               record.get("mode", "?"))
        groups[key].append(record)
    lines = ["| Bras | Année | Côté | Type | Plans=0 | Appels | Taux |",
             "|---|---|---|---|---:|---:|---:|"]
    stage_counts = Counter()
    undiagnosed = Counter()
    total_zeros = Counter()
    for (arm, year, side, mode), calls in sorted(groups.items()):
        zeros = [x for x in calls if x.get("plans") == "0"]
        lines.append(f"| {arm} | {year} | {side} | {mode} | {len(zeros)} | "
                     f"{len(calls)} | {len(zeros) / len(calls):.1%} |")
        total_zeros[arm] += len(zeros)
        for rec in zeros:
            stages = (("native_empty", "native"), ("no_flat", "flat"),
                      ("not_buildable", "buildable"), ("out_of_radius_or_quota", "bucketed"),
                      ("no_tested_start", "tested"), ("no_clear_platform_and_lead", "clear"),
                      ("insufficient_cargo", "cargo_ok"),
                      ("AITestMode_or_encroachment", "station"),
                      ("parallel_platform_or_budget", "accepted"))
            if "native" not in rec:
                undiagnosed[arm] += 1
                continue
            for label, key in stages:
                if int(rec.get(key, "-1")) == 0:
                    stage_counts[(arm, label)] += 1
                    break
            else:
                stage_counts[(arm, "other") ] += 1
    lines += ["", "| Bras | Premiers filtres vides (diagnostic) | Appels |",
              "|---|---|---:|"]
    for (arm, label), count in sorted(stage_counts.items()):
        lines.append(f"| {arm} | {label} | {count} |")
    for arm in sorted(total_zeros):
        if undiagnosed[arm]:
            lines.append(f"| {arm} | étape inconnue (anciens logs sans compteurs) | "
                         f"{undiagnosed[arm]} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--autopsy", action="store_true",
                        help="Taux plans=0 par année/côté/type et étapes de filtrage disponibles")
    args = parser.parse_args()
    paths = sorted(p for p in args.logs.iterdir() if p.name.endswith((".log", ".log.gz")))
    observations = parse_logs(paths)
    if not observations["files"]:
        parser.error("aucun journal moteur attendu (arm_seedN_rN.log) dans --logs")
    print(format_report(summarise(observations)))
    if any("spiral_ops" in record for record in observations["sites"]):
        print("\n" + iso_state(observations))
    if args.autopsy:
        print("\n" + autopsy(observations))


if __name__ == "__main__":
    main()
