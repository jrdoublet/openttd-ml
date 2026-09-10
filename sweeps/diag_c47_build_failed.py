"""Diagnostic C47 : pourquoi `build_failed` vaut 45,8 % des PROJECT_DISCARD (docs/taches.md,
fiche C47). Relais de C39.5/C41.48 : le candidat de tete n'est pas toujours celui qui se
construit, et `results/diag_constants_binding_6y_5seeds_v2.json` donne deja
discard_reason_counts = {build_failed: 1795, search_in_progress: 1729, abandoned_pair: 343,
plan_failed: 56} sans jamais avoir agrege le detail/error de build_failed. Ce script ne fait
qu'agreger un journal deja emis par le jeu (`ai/OpexAI/main.nut:2816` eau, `2957` air, `3129`
route) -- aucun code de jeu ecrit ou modifie ici, aucune campagne lancee par ce fichier.

Panneau retenu pour "projet effectivement construit" : PROJECT_CHOSEN, mais SEULEMENT pour
mode != rail (voir CHOSEN_TOTAL_NOTE dans le code). Pour eau (main.nut:2827), air (2969) et
route (3142), le panneau n'est atteint qu'apres un chantier reussi (le retour anticipe sur
!result.ok a deja eu lieu) -- un vrai denominateur "chantier". Pour rail, les deux sites
emetteurs (2756 et 2778) marquent l'ELECTION du candidat, avant/independamment de tout essai
de construction reel (verifie : le succes/echec reel du rail est signale plus loin par
RAIL_BUILD/RAIL_BUILD_FAIL dans _recordRailAttempt) -- ce n'est pas un chantier. Comme
build_failed n'existe de toute facon que pour eau/air/route (le rail echoue par
plan_failed/TRACEX), `chosen_built_nonrail` (PROJECT_CHOSEN, mode != rail) est le seul
denominateur homogene pour le ratio echecs/lignes construites que demande la fiche ;
`chosen_total`/`chosen_by_mode` restent publies mais ne doivent pas servir a ce ratio.

Pieges deja payes dans ce depot, tous evites ici :
- Double comptage (C41.10) : `openttd_output` est la capture COMPLETE et IDENTIQUE du
  sous-processus, repetee a chaque ligne de checkpoint mensuel d'une meme partie. On ne lit
  jamais `series` : `summarise()` ne garde que le dernier etat par (arm, graine, repetition),
  donc chaque partie n'est parsee qu'une seule fois.
- Disque (commit 594262e) : `decision_log=1` + `-d script=4` produit des journaux enormes.
  `openttd_output` n'est jamais serialise dans le JSON de sortie -- ni par seed ni dans
  `failed_runs` (vide explicitement avant serialisation, comme diag_c37_cheap_trace.py).
- Distribution, pas moyenne : toutes les sorties de ce script sont des comptes tries par
  effectif decroissant, jamais des moyennes.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)
import bench_v2

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

ARM = "OpexAI[decision_log=1]"

import re

OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_events(output):
    """Une entree par panneau OPEX rencontre dans une capture. Voir OPEX_RE : recherche libre
    (search, pas match) car chaque ligne porte un prefixe [script:N] [company] [level] devant.
    """
    events = []
    for line in (output or "").splitlines():
        m = OPEX_RE.search(line)
        if not m:
            continue
        _y, _mo, _d, kind, rest = m.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"kind": kind, "fields": fields})
    return events


def counter_to_sorted_list(counter, key_name):
    """Tri par effectif decroissant, puis par cle pour un ordre stable a egalite."""
    return [
        {key_name: key, "count": count}
        for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))
    ]


def joint_counter_to_sorted_list(counter, key_names):
    rows = []
    for key_tuple, count in counter.items():
        row = dict(zip(key_names, key_tuple))
        row["count"] = count
        rows.append(row)
    rows.sort(key=lambda row: (-row["count"], tuple(str(row[k]) for k in key_names)))
    return rows


def discard_summary(events):
    """Repartition PROJECT_DISCARD par reason (controle face aux 1795/1729/343/56 deja
    connus), puis, pour reason=build_failed seulement, les distributions par mode/detail/error
    (marginales et jointes) et par rang de portefeuille.
    """
    discards = [event for event in events if event["kind"] == "PROJECT_DISCARD"]
    reason_counts = Counter(event["fields"].get("reason", "unknown") for event in discards)

    build_failed = [event for event in discards if event["fields"].get("reason") == "build_failed"]
    mode_of = lambda event: event["fields"].get("mode", "unknown")
    detail_of = lambda event: event["fields"].get("detail", "unknown")
    error_of = lambda event: event["fields"].get("error", "unknown")
    rank_of = lambda event: event["fields"].get("rank", "unknown")

    mode_counts = Counter(mode_of(event) for event in build_failed)
    detail_counts = Counter(detail_of(event) for event in build_failed)
    error_counts = Counter(error_of(event) for event in build_failed)
    mode_detail_counts = Counter((mode_of(event), detail_of(event)) for event in build_failed)
    mode_error_counts = Counter((mode_of(event), error_of(event)) for event in build_failed)
    rank_counts = Counter(rank_of(event) for event in build_failed)

    return {
        "discard_total": len(discards),
        "discard_reason_counts": counter_to_sorted_list(reason_counts, "reason"),
        "build_failed_total": len(build_failed),
        "build_failed_by_mode": counter_to_sorted_list(mode_counts, "mode"),
        "build_failed_by_detail": counter_to_sorted_list(detail_counts, "detail"),
        "build_failed_by_error": counter_to_sorted_list(error_counts, "error"),
        "build_failed_by_mode_detail": joint_counter_to_sorted_list(mode_detail_counts, ["mode", "detail"]),
        "build_failed_by_mode_error": joint_counter_to_sorted_list(mode_error_counts, ["mode", "error"]),
        "build_failed_by_rank": counter_to_sorted_list(rank_counts, "rank"),
    }


CHOSEN_TOTAL_NOTE = (
    "chosen_total/chosen_by_mode melangent deux significations differentes de PROJECT_CHOSEN : "
    "pour mode=water (main.nut:2827), mode=air (2969) et mode=road (3142), le panneau n'est "
    "atteint qu'apres un chantier REUSSI (result.ok / le retour anticipe sur !result.ok a deja "
    "eu lieu) -- c'est un chantier. Pour mode=rail, les DEUX sites emetteurs (2756, dans le "
    "chemin RAIL_SEARCH_RESUMABLE, avant meme l'appel a _startRailSearch donc avant l'A* ; et "
    "2778, dans le chemin non-resumable, apres OpexBuildLine mais AVANT que _recordRailAttempt "
    "ne determine result.ok et n'emette RAIL_BUILD/RAIL_BUILD_FAIL) marquent l'ELECTION du "
    "candidat, pas un chantier reussi -- le rail peut encore echouer ensuite (voir "
    "RAIL_BUILD_FAIL, reason=plan_failed/TRACEX, jamais reason=build_failed). Consequence : "
    "chosen_total est gonfle par les elections rail et NE DOIT PAS servir de denominateur au "
    "ratio build_failed/lignes -- build_failed n'existe d'ailleurs que pour eau/air/route. "
    "Utiliser chosen_built_nonrail (mode != rail) a la place ; c'est ce que fait "
    "build_failed_per_nonrail_line."
)


def chosen_summary(events):
    """PROJECT_CHOSEN : panneau heterogene, voir CHOSEN_TOTAL_NOTE. `chosen_built_nonrail`
    (mode != rail) est le seul denominateur homogene pour le ratio echecs/lignes construites,
    car build_failed n'existe que pour eau/air/route et ces trois modes n'emettent
    PROJECT_CHOSEN qu'apres un chantier reussi.
    """
    chosen = [event for event in events if event["kind"] == "PROJECT_CHOSEN"]
    by_mode = Counter(event["fields"].get("mode", "unknown") for event in chosen)
    chosen_built_nonrail = sum(1 for event in chosen if event["fields"].get("mode") != "rail")
    return {
        "chosen_total": len(chosen),
        "chosen_by_mode": counter_to_sorted_list(by_mode, "mode"),
        "chosen_total_note": CHOSEN_TOTAL_NOTE,
        "chosen_built_nonrail": chosen_built_nonrail,
    }


def event_summary(events):
    result = discard_summary(events)
    result.update(chosen_summary(events))
    result["build_failed_per_nonrail_line"] = (
        result["build_failed_total"] / float(result["chosen_built_nonrail"])
        if result["chosen_built_nonrail"] else None
    )
    return result


def _selftest():
    """Auto-verification hors ligne (aucune campagne) : quelques lignes PROJECT_DISCARD/
    PROJECT_CHOSEN factices, avec et sans detail/error, pour verifier les comptes.
    """
    fake_output = "\n".join([
        "[script:37] [1] [P] OPEX 1970-01-05 PROJECT_DISCARD rank=0 mode=water src=5 dst=9 reason=build_failed detail=SITE_UNAVAIL error=-1",
        "[script:37] [1] [P] OPEX 1970-01-05 PROJECT_DISCARD rank=1 mode=air src=5 dst=9 reason=search_in_progress",
        "[script:37] [1] [P] OPEX 1970-01-06 PROJECT_DISCARD rank=0 mode=road src=3 dst=4 reason=build_failed detail=ERR_FLAT_LAND_REQUIRED error=-1",
        "[script:37] [1] [P] OPEX 1970-01-06 PROJECT_DISCARD rank=2 mode=road src=1 dst=2 reason=build_failed detail=ERR_FLAT_LAND_REQUIRED error=-1",
        "[script:37] [1] [P] OPEX 1970-01-06 PROJECT_CHOSEN rank=3 mode=rail kind=new src=3 dst=4",
        # Second election rail (site 2778, chemin non-resumable) : le meme candidat peut etre
        # elu deux fois dans le meme flux sans qu'aucune des deux ne corresponde forcement a un
        # chantier reussi -- c'est exactement le piege que ce test couvre.
        "[script:37] [1] [P] OPEX 1970-01-06 PROJECT_CHOSEN rank=1 mode=rail kind=new src=1 dst=2",
        "[script:37] [1] [P] OPEX 1970-01-07 PROJECT_DISCARD rank=0 mode=air src=1 dst=2 reason=abandoned_pair",
        "[script:37] [1] [P] OPEX 1970-01-08 PROJECT_DISCARD rank=0 mode=water src=6 dst=7 reason=build_failed detail=SITE_UNAVAIL error=-2",
        "[script:37] [1] [P] OPEX 1970-01-09 PROJECT_CHOSEN rank=0 mode=water src=6 dst=7",
        "[script:37] [1] [P] OPEX 1970-01-10 PROJECT_DISCARD rank=1 mode=road src=8 dst=9 reason=plan_failed detail=no_candidate",
    ])
    events = parse_events(fake_output)
    summary = event_summary(events)

    # Compte a la main (7 PROJECT_DISCARD, 3 PROJECT_CHOSEN dont 2 rail + 1 water,
    # 4 build_failed parmi les PROJECT_DISCARD) :
    #   build_failed : (water,SITE_UNAVAIL,-1,rank0), (road,ERR_FLAT_LAND_REQUIRED,-1,rank0),
    #                  (road,ERR_FLAT_LAND_REQUIRED,-1,rank2), (water,SITE_UNAVAIL,-2,rank0)
    #   => mode: road=2, water=2 ; detail: ERR_FLAT_LAND_REQUIRED=2, SITE_UNAVAIL=2 ;
    #      error: -1=3, -2=1 ; rank: 0=3, 2=1
    #   PROJECT_CHOSEN : mode=rail x2 (des elections, pas des chantiers -- voir
    #   CHOSEN_TOTAL_NOTE), mode=water x1 (un vrai chantier reussi) => chosen_total=3 mais
    #   chosen_built_nonrail=1. Si le ratio utilisait chosen_total par erreur, il vaudrait
    #   4/3=1.33 au lieu de 4/1=4.0 -- exactement le sous-comptage d'echec que ce test detecte.
    checks = []
    checks.append(("discard_total == 7", summary["discard_total"] == 7))
    checks.append(("build_failed_total == 4", summary["build_failed_total"] == 4))
    checks.append(("chosen_total == 3 (2 elections rail + 1 chantier water)", summary["chosen_total"] == 3))
    checks.append(("chosen_built_nonrail == 1 (seul le water compte)", summary["chosen_built_nonrail"] == 1))
    checks.append((
        "build_failed_per_nonrail_line == 4.0 (build_failed_total / chosen_built_nonrail, PAS / chosen_total)",
        summary["build_failed_per_nonrail_line"] == 4.0,
    ))
    checks.append((
        "build_failed_per_nonrail_line != build_failed_total/chosen_total (le piege corrige)",
        summary["build_failed_per_nonrail_line"] != summary["build_failed_total"] / float(summary["chosen_total"]),
    ))
    checks.append(("chosen_total_note mentions rail elections", "election" in summary["chosen_total_note"]))
    checks.append((
        "discard_reason_counts head is build_failed=4",
        summary["discard_reason_counts"][0] == {"reason": "build_failed", "count": 4},
    ))
    checks.append((
        "build_failed_by_mode == road:2, water:2 (tie, sorted alphabetically)",
        summary["build_failed_by_mode"] == [{"mode": "road", "count": 2}, {"mode": "water", "count": 2}],
    ))
    checks.append((
        "build_failed_by_detail sorted desc, tie broken by key",
        summary["build_failed_by_detail"] == [
            {"detail": "ERR_FLAT_LAND_REQUIRED", "count": 2},
            {"detail": "SITE_UNAVAIL", "count": 2},
        ],
    ))
    checks.append((
        "build_failed_by_mode_detail joint distribution",
        summary["build_failed_by_mode_detail"] == [
            {"mode": "road", "detail": "ERR_FLAT_LAND_REQUIRED", "count": 2},
            {"mode": "water", "detail": "SITE_UNAVAIL", "count": 2},
        ],
    ))
    checks.append((
        "build_failed_by_mode_error joint distribution",
        summary["build_failed_by_mode_error"] == [
            {"mode": "road", "error": "-1", "count": 2},
            {"mode": "water", "error": "-1", "count": 1},
            {"mode": "water", "error": "-2", "count": 1},
        ],
    ))
    checks.append((
        "build_failed_by_rank == rank0:3, rank2:1",
        summary["build_failed_by_rank"] == [{"rank": "0", "count": 3}, {"rank": "2", "count": 1}],
    ))
    checks.append((
        "chosen_by_mode == rail:2, water:1 (sorted desc)",
        summary["chosen_by_mode"] == [{"mode": "rail", "count": 2}, {"mode": "water", "count": 1}],
    ))
    # motifs sans detail/error (search_in_progress, abandoned_pair, plan_failed) : verifie
    # qu'ils ne polluent pas les compteurs build_failed_by_*.
    checks.append((
        "no build_failed leak from search_in_progress/abandoned_pair/plan_failed",
        sum(row["count"] for row in summary["build_failed_by_mode"]) == 4,
    ))

    all_ok = all(ok for _, ok in checks)
    print("=== _selftest() ===")
    for label, ok in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    print("summary:", summary)
    print("all_ok:", all_ok)
    if not all_ok:
        raise SystemExit(1)
    return all_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true", help="lance _selftest() et quitte, aucune campagne")
    args = parser.parse_args()
    if args.selftest:
        _selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / f"diag_c47_build_failed_{args.years}y_{len(args.seeds)}seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms([ARM]), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)

    per_seed = []
    all_events = []
    for record in summary:
        events = parse_events(record.get("openttd_output"))
        all_events.extend(events)
        per_seed.append({
            "seed": record["seed"],
            "run_ok": record["run_ok"],
            "metrics": event_summary(events),
        })

    failed = [dict(record, openttd_output="") for record in summary if not record["run_ok"]]
    payload = {
        "years": args.years,
        "seeds": args.seeds,
        "arm": ARM,
        "per_seed": per_seed,
        "cumulative": event_summary(all_events),
        "failed_runs": failed,
        "failed_run_count": len(failed),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    print("cumulative discard_reason_counts:", payload["cumulative"]["discard_reason_counts"])
    print("cumulative build_failed_total:", payload["cumulative"]["build_failed_total"],
          "chosen_built_nonrail:", payload["cumulative"]["chosen_built_nonrail"],
          "build_failed_per_nonrail_line:", payload["cumulative"]["build_failed_per_nonrail_line"])
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
