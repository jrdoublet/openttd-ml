"""Diagnostic observatoire des echecs de construction aerienne (5 graines x 6 ans).

Le banc ne modifie aucun defaut : `air_cost_probe` ajoute seulement des panneaux ``AC``
pour conserver le capital prevu et le cout reel, y compris apres un nivellement annule.
Les panneaux ``OA``/``OE`` sont emis par le chemin normal et permettent de joindre,
dans leur ordre de creation, distance, raison et code d'erreur d'une meme tentative.

OpenTTDLab ne sait capturer qu'a la fin de chaque partie et exige un rendu OpenGL disponible;
``--screenshots repertoire`` active ces cartes finales comme complement visuel des mesures.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

RE_OA = re.compile(r"^OA\|(\d+)\|(\d+)\|(\d+)\|(.+)$")
RE_OE = re.compile(r"^OE\|A\|(\d+)$")
RE_AC = re.compile(r"^AC\|(\d+)\|(\d+)\|(-?\d+)\|(\d+)\|(\d+)$")
ERROR_NAMES = {258: "ERR_LOCAL_AUTHORITY_REFUSES", 260: "ERR_AREA_NOT_CLEAR",
               263: "ERR_FLAT_LAND_REQUIRED"}


def _signs_in_order(chunks):
    signs = chunks.get("SIGN", {})
    def key(item):
        try:
            return int(item[0])
        except (TypeError, ValueError):
            return 0
    return [sign.get("name", "") for _, sign in sorted(signs.items(), key=key)]


def parse_air_attempts(signs):
    """Joint OA, OE et AC adjacents : ces trois panneaux sont poses sans autre action entre eux."""
    attempts, active = [], None
    for sign in signs:
        if m := RE_OA.match(sign):
            active = {"year": int(m.group(1)), "distance": int(m.group(2)),
                      "planning_opcodes": int(m.group(3)), "reason": m.group(4),
                      "error": 0, "error_name": None}
            attempts.append(active)
        elif active is not None and (m := RE_OE.match(sign)):
            active["error"] = int(m.group(1))
            active["error_name"] = ERROR_NAMES.get(active["error"], f"ERR_{active['error']}")
        elif active is not None and (m := RE_AC.match(sign)):
            active.update({"line_index": int(m.group(1)), "model_capital": int(m.group(2)),
                           "actual_cost": int(m.group(3)), "planned_planes": int(m.group(4)),
                           "built_planes": int(m.group(5)), "ok": int(m.group(5)) > 0})
            active = None
    return attempts


def keep(row):
    chunks = row.get("chunks", {})
    return ({
        "seed": row["experiment"]["seed"], "date": str(row["date"]),
        "signs": _signs_in_order(chunks), "output": row.get("output", ""),
    },)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 12345])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results" / "diag_air_afail_6y_5seeds.json")
    parser.add_argument("--screenshots", type=Path, default=None,
                        help="repertoire de captures finales (optionnel : le rendu requiert OpenGL)")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI",
                      (("air_cost_probe", 1),))
    experiments = [{"seed": seed, "days": 365 * args.years, "openttd_config": CFG,
                    "ais": (ai,)} for seed in args.seeds]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=args.workers, result_processor=keep,
        final_screenshot_directory=str(args.screenshots) if args.screenshots else None,
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))

    final = {}
    for row in rows:
        if row["seed"] not in final or row["date"] > final[row["seed"]]["date"]:
            final[row["seed"]] = row
    runs, all_attempts = [], []
    for seed in args.seeds:
        attempts = parse_air_attempts(final[seed]["signs"])
        for attempt in attempts:
            attempt["seed"] = seed
        all_attempts.extend(attempts)
        runs.append({"seed": seed, "attempts": attempts})

    failures = [a for a in all_attempts if not a.get("ok")]
    summary = {
        "attempts": len(all_attempts), "successes": len(all_attempts) - len(failures),
        "failures": len(failures),
        "failure_rate": len(failures) / len(all_attempts) if all_attempts else None,
        "errors": dict(Counter(a.get("error_name") or "no_error_code" for a in failures)),
        "failed_actual_cost": sum(a.get("actual_cost", 0) for a in failures),
        "failed_model_capital": sum(a.get("model_capital", 0) for a in failures),
        "failed_distances": [a["distance"] for a in failures],
    }
    payload = {"openttd_version": OPENTTD_VERSION, "years": args.years, "seeds": args.seeds,
               "openttd_config": CFG, "air_cost_probe": True,
               "screenshots": str(args.screenshots) if args.screenshots else None,
               "summary": summary, "runs": runs}
    args.out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"ecrit {args.out}")


if __name__ == "__main__":
    main()
