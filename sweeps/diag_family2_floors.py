"""C43/E3 famille 2 (planchers) -- methode d'instrumentation avant etalonnage, meme protocole
que sweeps/diag_constants_binding.py (famille 1). MIN_SEPARATION est deja fait (famille 1) ;
ce script couvre les deux planchers routiers qui ont deja une telemetrie complete livree, sans
aucun nouveau code de jeu :

ROAD_MIN_PROFIT_ANNUAL (candidates.nut:1002, =1000) : panneau VIVIER_GEN mode=road donne le
denominateur (produced=pairsInBand) ; VIVIER_REJECT reason=road_profit_too_low compte les
candidats sous le plancher de profit annuel.

ROAD_ACCEPTANCE_MIN (candidates.nut:1007, =8) : meme denominateur ; VIVIER_REJECT
reason=road_town_rejected compte les candidats sous le plancher d'acceptance de ville.

Les autres planchers de la famille 2 (ATTEMPT_FLOOR, CASH_RESERVE_MIN, LOOP_BUDGET_FLOOR,
DYNAMIC_BATCH_OPS_FLOOR, PORTFOLIO_REFRESH_MIN_GAIN, PAX_NEAR_MIN_PROFIT, ORIGIN_SEPARATION,
ROAD_MIN_DISTANCE) n'ont PAS de compteur binaire pret a l'emploi -- hors perimetre de cette
passe, a instrumenter separement si necessaire.
"""
import argparse
import re
import statistics
from collections import Counter
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, keep, make_cfg
import bench_v2

SCRIPT_DEBUG_LEVEL = "4"
_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_opex_decisions(output):
    events = []
    for line in (output or "").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        _company, _level, text = m.groups()
        m2 = OPEX_RE.match(text.strip())
        if not m2:
            continue
        _y, _mo, _d, kind, rest = m2.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"kind": kind, "fields": fields})
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 42, 73, 100, 2026])
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--out", type=Path,
                        default=Path("docs/diag_family2_floors_6y_5seeds.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    bench_v2.CHECKPOINT_PATH = args.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()

    arm_name = "OpexAI[decision_log=1]"
    arms = build_arms([arm_name])
    cfg = make_cfg(1970)

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=3,
        result_processor=keep,
        experiments=[
            {"seed": seed, "days": 365 * args.years, "openttd_config": cfg,
             "ais": (arms[arm_name],), "bench_run": [arm_name, seed, 0]}
            for seed in args.seeds
        ],
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    by_run = {}
    for row in rows:
        key = tuple(row["run"])
        by_run.setdefault(key, []).append(row)

    gen_calls = []  # {seed, produced, kept}
    reject_reasons = Counter()
    per_seed_kept = Counter()
    per_seed_produced = Counter()
    per_seed_profit_too_low = Counter()
    per_seed_town_rejected = Counter()
    n_gen_calls_by_seed = Counter()

    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        for row in series:
            for ev in parse_opex_decisions(row.get("openttd_output")):
                f = ev["fields"]
                if ev["kind"] == "VIVIER_GEN" and f.get("mode") == "road":
                    produced = int(f["produced"])
                    gen_calls.append({"seed": seed, "produced": produced, "kept": int(f["kept"])})
                    per_seed_produced[seed] += produced
                    per_seed_kept[seed] += int(f["kept"])
                    n_gen_calls_by_seed[seed] += 1
                elif ev["kind"] == "VIVIER_REJECT":
                    reason = f["reason"]
                    n = int(f["n"])
                    reject_reasons[reason] += n
                    if reason == "road_profit_too_low":
                        per_seed_profit_too_low[seed] += n
                    elif reason == "road_town_rejected":
                        per_seed_town_rejected[seed] += n

    total_produced = sum(per_seed_produced.values())
    total_kept = sum(per_seed_kept.values())
    total_profit_too_low = reject_reasons.get("road_profit_too_low", 0)
    total_town_rejected = reject_reasons.get("road_town_rejected", 0)

    def per_seed_table(counter):
        return {seed: counter.get(seed, 0) for seed in args.seeds}

    payload = {
        "purpose": "C43/E3 famille 2 (planchers) : ROAD_MIN_PROFIT_ANNUAL et ROAD_ACCEPTANCE_MIN, "
                   "comptes bruts via la telemetrie VIVIER_GEN/VIVIER_REJECT deja livree",
        "caveat": "PAS de pourcentage de morsure fiable : road_town_rejected est incremente dans "
                  "la boucle industrie x ville de OpexRoadFreightCandidates AVANT le pairsInBand++ "
                  "de CETTE boucle precise (candidates.nut:1346), alors que VIVIER_GEN.produced "
                  "agrege pairsInBand de PLUSIEURS boucles distinctes (frets industrie-industrie, "
                  "frets industrie-ville, pax, feeders). Le denominateur correct (evaluations de "
                  "cette boucle precise) n'est pas isole par la telemetrie livree -- seuls les "
                  "comptes absolus sont fiables ici, pas un ratio contre produced/kept.",
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "n_vivier_gen_calls": len(gen_calls),
        "total_produced": total_produced,
        "total_kept": total_kept,
        "reject_reason_counts": dict(reject_reasons),
        "road_min_profit_annual": {
            "constant": 1000,
            "n_rejected_total": total_profit_too_low,
            "per_seed": per_seed_table(per_seed_profit_too_low),
        },
        "road_acceptance_min": {
            "constant": 8,
            "n_rejected_total": total_town_rejected,
            "per_seed": per_seed_table(per_seed_town_rejected),
        },
    }
    import json
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print(f"n_vivier_gen_calls={len(gen_calls)} total_produced={total_produced} total_kept={total_kept}")
    print("reject_reason_counts:", dict(reject_reasons))
    print("ROAD_MIN_PROFIT_ANNUAL n_rejected_total:", total_profit_too_low,
          "per_seed:", dict(per_seed_profit_too_low))
    print("ROAD_ACCEPTANCE_MIN n_rejected_total:", total_town_rejected,
          "per_seed:", dict(per_seed_town_rejected))
    print("out", args.out)


if __name__ == "__main__":
    main()
