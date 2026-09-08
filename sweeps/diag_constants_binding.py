"""Instrumentation avant etalonnage (docs/taches.md C43/E3, methode : "compter combien de fois un
plafond mord reellement avant de le regler"). PROJECT_TOP_K et MIN_SEPARATION ont deja une
telemetrie complete dans le code livre (panneaux VIVIER et PROJECT_DISCARD via OpexDecide/AILog) --
aucun nouveau code de jeu, juste ce harnais de lecture avec -d script=4 sur le defaut courant.

PROJECT_TOP_K : panneau VIVIER (path=build|reselect|incremental) donne considered/selected/rejected
pour chaque appel de selection. TOP_K mord un appel donne si rejected > 0 (des candidats existaient
au-dela de la fenetre retenue).

MIN_SEPARATION : panneau PROJECT_DISCARD, reason=too_close_no_join, compte face aux autres motifs
de rejet et face aux PROJECT_CHOSEN (lignes effectivement elues), sur le defaut station_join=0.

TARGET_HEADWAY_DAYS : PAS instrumente ici -- pas de compteur binaire simple (mordre/pas mordre),
demande une mesure de sensibilite au seuil d'arrondi (OpexCeilDiv), hors perimetre de cette passe.
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
                        default=Path("results/diag_constants_binding_6y_5seeds.json"))
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

    vivier_rows = []       # {seed, path, considered, selected, rejected}
    discard_reasons = Counter()
    chosen_count = 0

    for key, series in by_run.items():
        _arm, seed, _rep = key
        series.sort(key=lambda r: r["date"])
        # C41.10 (docs/taches.md, 2026-09-08) : openttd_output est IDENTIQUE (meme capture du
        # sous-processus) a chaque ligne de checkpoint mensuel d'une meme partie -- verifie
        # empiriquement (longueur identique sur 72 lignes d'une partie de 6 ans). Parcourir
        # `series` comptait donc chaque evenement une fois par mois du jeu (~72x pour 6 ans).
        # Corrige : le lire une seule fois par (graine, arm), depuis la derniere ligne.
        output = series[-1].get("openttd_output") if series else None
        for ev in parse_opex_decisions(output):
            f = ev["fields"]
            if ev["kind"] == "VIVIER":
                vivier_rows.append({
                    "seed": seed, "path": f["path"],
                    "considered": int(f["considered"]), "selected": int(f["selected"]),
                    "rejected": int(f["rejected"]),
                })
            elif ev["kind"] == "PROJECT_DISCARD":
                discard_reasons[f["reason"]] += 1
            elif ev["kind"] == "PROJECT_CHOSEN":
                chosen_count += 1

    # PROJECT_TOP_K : sur combien d'appels de selection un candidat a-t-il ete rejete
    # uniquement parce que la fenetre etait pleine (rejected > 0) ?
    by_path = {}
    for r in vivier_rows:
        by_path.setdefault(r["path"], []).append(r)
    # ATTENTION : "rejected" melange deux causes distinctes (plancher de profit relatif
    # PORTFOLIO_FLOOR_PCT dans OpexProjectSelectAffordable, ET la troncature TOP_K elle-meme).
    # OpexProjectInsert ne pop QUE quand best.len() > limit=TOP_K : donc TOP_K n'a reellement
    # tronque un appel que si selected == TOP_K (64) -- c'est le seul critere correct.
    TOP_K = 64
    top_k_summary = {}
    for path, rows_p in by_path.items():
        binds = [r for r in rows_p if r["selected"] >= TOP_K]
        top_k_summary[path] = {
            "n_calls": len(rows_p),
            "n_binding": len(binds),
            "pct_binding": 100.0 * len(binds) / len(rows_p) if rows_p else None,
            "mean_considered": statistics.mean(r["considered"] for r in rows_p) if rows_p else None,
            "mean_selected": statistics.mean(r["selected"] for r in rows_p) if rows_p else None,
            "mean_rejected": statistics.mean(r["rejected"] for r in rows_p) if rows_p else None,
            "max_considered": max((r["considered"] for r in rows_p), default=None),
            "max_selected": max((r["selected"] for r in rows_p), default=None),
            "n_selected_at_cap": sum(1 for r in rows_p if r["selected"] >= 64),
        }

    total_discards = sum(discard_reasons.values())
    min_separation_rejections = discard_reasons.get("too_close_no_join", 0) + discard_reasons.get("too_close_hard", 0)

    payload = {
        "purpose": "Instrument PROJECT_TOP_K (VIVIER) and MIN_SEPARATION (PROJECT_DISCARD) binding "
                   "rates before any factorial bench, per docs/taches.md C43/E3 method",
        "seeds": args.seeds, "years": args.years, "arm": arm_name,
        "project_top_k_by_path": top_k_summary,
        "min_separation": {
            "discard_reason_counts": dict(discard_reasons),
            "total_discards": total_discards,
            "min_separation_rejections": min_separation_rejections,
            "pct_of_discards": (100.0 * min_separation_rejections / total_discards
                               if total_discards else None),
            "lines_chosen": chosen_count,
            "min_separation_rejections_per_line_chosen": (
                min_separation_rejections / float(chosen_count) if chosen_count else None),
        },
    }
    import json
    with open(args.out, "w") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

    print("=== PROJECT_TOP_K (VIVIER) ===")
    for path, s in top_k_summary.items():
        print(f"  path={path}: n_calls={s['n_calls']} binding(selected>=64)={s['n_binding']} "
              f"({s['pct_binding']:.1f}%) mean_considered={s['mean_considered']:.1f} "
              f"mean_selected={s['mean_selected']:.1f} mean_rejected={s['mean_rejected']:.1f} "
              f"max_considered={s['max_considered']} max_selected={s['max_selected']}")
    print("=== MIN_SEPARATION (PROJECT_DISCARD) ===")
    print(" reasons:", dict(discard_reasons))
    print(" min_separation_rejections:", min_separation_rejections, "/", total_discards,
          "discards ; lines_chosen=", chosen_count)
    print("out", args.out)


if __name__ == "__main__":
    main()
