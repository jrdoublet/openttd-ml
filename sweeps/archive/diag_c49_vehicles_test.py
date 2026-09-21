"""Test unitaire et diagnostic C49 (§10.1 du contrat) : preuve d'execution forcee de la branche vehicles.

Ce script abaisse intentionnellement le plafond de vehicules dans openttd.cfg a des valeurs basses
(max_roadveh = 5, max_aircraft = 5, max_trains = 5, max_ships = 5) afin de forcer l'atteinte
de la rarete 'vehicles' et de verifier de bout en bout l'activation du regime 'vehicles'
et le calcul du score Profit / vehicules.
"""
import argparse
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, quarter_profit, year_profit
)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug


def make_cfg_low_vehicles(starting_year=1970, map_size=8):
    return f"""[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = {starting_year}
map_x = {map_size}
map_y = {map_size}
[vehicle]
max_trains = 5
max_roadveh = 5
max_aircraft = 5
max_ships = 5
"""


# Monkey-patch make_cfg dans bench_v2
bench_v2.make_cfg = make_cfg_low_vehicles

C49_SCARCITY_RE = re.compile(r"OPEX \d+-\d+-\d+ C49_SCARCITY (.*)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--out", type=str, default="/tmp/diag_c49_vehicles_test.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = out_path.with_suffix(".jsonl")
    arms = build_arms(["OpexAI[c49_variable_denominator=1]"])
    exps = experiments(arms, args.seeds, args.years, repeats=1)

    rows = list(run_experiments(
        exps,
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
        result_processor=bench_v2.keep,
    ))

    summary = bench_v2.summarise(rows)
    print(f"\nResultats de la verification plafond bas (annees={args.years}):")
    vehicle_regime_triggered = False
    vehicle_scarcity_count = 0
    all_events = []
    for record in summary:
        print(f"Seed {record['seed']} : {record['n_vehicles']} vehicules, {record['n_stations']} gares, value={record['company_value']}")
        output = record.get("openttd_output", "")
        for line in output.splitlines():
            m = C49_SCARCITY_RE.search(line)
            if m:
                ev = m.group(1)
                all_events.append(ev)
                print(f"  {ev}")
                if "regime=vehicles" in ev:
                    vehicle_regime_triggered = True
                m_v = re.search(r"vehicles=(\d+)", ev)
                if m_v and int(m_v.group(1)) > 0:
                    vehicle_scarcity_count += int(m_v.group(1))

    print(f"\nBilan :")
    print(f"  Total occurrences de blocage 'vehicles' : {vehicle_scarcity_count}")
    print(f"  Bascule au regime 'vehicles' observee : {vehicle_regime_triggered}")

    assert vehicle_scarcity_count > 0, "ECHEC: Aucun blocage de type vehicles n'a ete observe !"
    assert vehicle_regime_triggered, "ECHEC: Le regime vehicles n'a pas ete active !"
    print("SUCCESS: La branche vehicles a ete executee et testee de bout en bout avec succes (§10.1 valide) !")

    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Ecrit {args.out}")


if __name__ == "__main__":
    main()
