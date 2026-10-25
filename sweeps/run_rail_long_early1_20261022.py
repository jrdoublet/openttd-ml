#!/usr/bin/env python3
"""Bancs apparies RAIL-LONG-EARLY-1 (un seul Docker par invocation).

Exemples :
  python sweeps/run_rail_long_early1_20261022.py --case initial --stage smoke
  python sweeps/run_rail_long_early1_20261022.py --case secondary --stage diagnostic --probes 6
  python sweeps/run_rail_long_early1_20261022.py --case timing --stage a
  python sweeps/run_rail_long_early1_20261022.py --case secondary --stage smoke --map-size 10

La porte B est volontairement une invocation distincte et conditionnee a la porte A.
Le protocole 'diagnostic' a trois graines n'est pas une qualification economique.
Tous les bras gardent rail_cal=0 ; les modifications de bornes sont isolees.
"""

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SEEDS_A = (42, 100, 7, 999, 2026, 1, 17, 373684, 314, 512,
           1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309,
           423960, 613553, 515222, 781335, 375172, 999533, 442018, 746035, 455216, 230185,
           706990, 983759, 802204, 232037, 723002, 313707, 701256, 292001, 841478, 59527)
# (borne initiale, cap secondaire 0=ancien 250, annee de relachement V269)
CASES = {
    "initial": ((200, 0, 5), (250, 0, 5)),
    # 250 dans la ref force aussi le correctif d'exposition V276 asynchrone,
    # isolant 250 -> 400 au lieu de melanger correction et elargissement.
    "secondary": ((250, 250, 5), (250, 400, 5)),
    "timing": ((250, 400, 5), (250, 400, 2)),
    "joint": ((200, 0, 5), (250, 400, 2)),
}


def spec(values, v276_slices=None):
    initial, secondary, year = values
    extra = f",v276_cand_slices={v276_slices}" if v276_slices is not None else ""
    return (f"OpexAI[rail_cal=0,v294_rail_dist_decouple={initial},"
            f"v269_rail_long_max={secondary},v269_rail_late_relax={year}{extra}]")


def command(case, stage, map_size, probes, campaign, v276_slices=None):
    ref, variant = CASES[case]
    stage_info = {
        "smoke": (3, (42,), "gain_short"),
        "three": (3, (42, 100, 7), "gain_short"),
        "one-ten": (10, (42,), "non_erosion"),
        "ten": (10, (42, 100, 7), "non_erosion"),
        "a": (3, SEEDS_A, "gain_short"),
        "b": (10, SEEDS_A[:20], "non_erosion"),
    }
    years, seeds, rule = stage_info[stage]
    campaign = campaign or f"rail_long_early1_{case}_{stage}_m{map_size}_20261022"
    cmd = [sys.executable, "sweeps/run_c66_reference.py",
           "--campaign", campaign,
           "--reference", spec(ref, v276_slices), "--variant", spec(variant, v276_slices),
           "--variant-policy-id", f"rail_long_early_{case}",
           "--primary-metric", "profit_year", "--min-useful-primary-delta-pct", "4",
           "--value-guard-max-loss-pct", "5", "--decision-rule", rule,
           "--map-size", str(map_size), "--years", str(years),
           "--repeats", "1", "--seeds", *map(str, seeds),
           "--cpus", "10", "--max-workers", "10", "--memory", "8g", "--network", "host"]
    if rule == "gain_short" and stage == "a":
        cmd += ["--required-seeds", "40", "--required-years", "3"]
    if probes:
        cmd += ["--probes", str(probes)]
    return cmd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="joint")
    parser.add_argument("--stage", choices=("smoke", "three", "one-ten", "ten", "a", "b"), default="smoke")
    parser.add_argument("--map-size", type=int, choices=range(8, 11), default=8)
    parser.add_argument("--probes", type=int, choices=(0, 6, 10), default=0,
                        help="6=decision_log des deux bras, 10=scheduler+decision_log; autres tests sans sonde")
    parser.add_argument("--v276-slices", type=int, choices=(0, 2),
                        help="force V276 2 pour tester sur petite carte sa grille et son execution asynchrone")
    parser.add_argument("--campaign", help="nom explicite distinct pour chaque re-execution")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cmd = command(args.case, args.stage, args.map_size, args.probes, args.campaign, args.v276_slices)
    print(" ".join(cmd), flush=True)
    if args.dry_run:
        return
    active = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True,
                            cwd=ROOT, check=True).stdout.strip()
    if active:
        parser.error("un conteneur Docker est deja actif ; ne pas lancer une autre campagne")
    raise SystemExit(subprocess.run(cmd, cwd=ROOT).returncode)


if __name__ == "__main__":
    main()
