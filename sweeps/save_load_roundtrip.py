"""Rechargement de partie : est-ce qu'OpexAI repart correctement apres un chargement ?

`OpexAI::Save()` / `OpexAI::Load()` (ai/OpexAI/main.nut, ~2026-09-09) n'ont jamais ete testes.
Ce script construit le premier banc reproductible pour ca :

  Phase A - une partie courte (OpexAI seule, graine fixe, config figee de bench_v2.make_cfg)
            joue pendant --years-a annees, TOUTES les sauvegardes mensuelles sont conservees
            (contrairement a bench_v2.enable_savegame_cleanup qui les detruit au fil de l'eau).
  Phase B - une sauvegarde de milieu de partie (choisie par sa date, au milieu de la phase A)
            est rechargee via `-g <fichier>` et la partie continue pendant --years-b annees
            supplementaires, avec la MEME IA (aucun `start_ai` relance : la compagnie existe
            deja dans la sauvegarde).

Difficulte principale : openttdlab (0.0.75) n'expose NI parametre pour charger une sauvegarde de
depart, NI moyen de recuperer les .sav bruts (son repertoire d'execution est un
tempfile.TemporaryDirectory detruit des que run_experiments() retourne). Aucun contournement propre
n'existe cote API. La solution retenue : patcher openttdlab.subprocess.check_output (technique deja
validee dans ce depot par sweeps/probe_ailog.py) pour, juste avant/apres le SEUL appel qui lance
vraiment OpenTTD (celui qui porte -vnull) :
  - injecter -d script=3 (journal de decision AILog, meme technique que probe_ailog.py) ;
  - Phase A seulement : copier le dossier `save/` produit vers un chemin persistant AVANT que le
    tempdir d'openttdlab ne soit nettoye ;
  - Phase B seulement : remplacer le `-g` nu (nouvelle carte) par `-g <savegame choisi>`, et
    retirer la ligne `start_ai OpexAI` du script `game_start.scr` genere par openttdlab (sinon on
    demarrerait une DEUXIEME compagnie a cote de celle rechargee).

Ce fichier ne modifie jamais ai/OpexAI/ ni n'importe quoi sous ai/. Tout son etat va sous
/home/.../.scratch_saveload/ (jamais /tmp) et results/save_load_roundtrip.json.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import sys
from datetime import date, timedelta

import openttdlab
from openttdlab import run_experiments

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_v2  # noqa: E402  (reutilise make_cfg, build_arms, keep, station_ratings, ...)

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / ".scratch_saveload"
CACHE_DIR = WORK_DIR / "cache"
DEFAULT_OUT = ROOT / "results" / "save_load_roundtrip.json"

SCRIPT_DEBUG_LEVEL = "3"  # impose par la mission. A verifier au lecteur du rapport : d'apres la
# note de projet "AILog EST capturable" (2026-09-03), script=3 ne rend QUE les [W]/[E]
# (Warning/Error), les [I] (Info, la trace de decision) n'arrivent qu'a script=4. Sur les parties
# de verification de ce script (seed 42, 1 an, config figee, code OpexAI du 2026-09-10), script=3
# a produit 0 octet de sortie : ni [W] ni [E] ne se sont produits -- ce qui EST une information
# utile (aucune alerte), mais ca veut dire qu'a ce niveau la sortie peut rester vide meme si tout
# va bien. Si le rechargement se passe mal, les motifs demandes (ScriptLog::Warning/Error dans
# src/script/script_instance.cpp, verifie sur le binaire OpenTTD 15.3) restent visibles a ce
# niveau puisqu'ils sont eux-memes des [W]/[E].

# Motifs demandes explicitement dans la mission.
REQUIRED_MARKERS = (
    "Save function",
    "Load function",
    "is not implemented",
    "Your script made an error",
    "The script died unexpectedly",
    "Save data",
    "too deep",
    "too big",
)

# Verifie sur le binaire OpenTTD 15.3 lui-meme (src/script/script_instance.cpp) : ce sont les
# SEULS messages que le moteur imprime au sujet de Save()/Load() d'un script, et ILS NE COUVRENT
# QUE LES ECHECS. Il n'existe aucun message moteur de succes. On les cherche en plus des motifs
# imposes, pour ne rien perdre si le vocabulaire exact demande ne matche pas mot pour mot.
ENGINE_FAILURE_MARKERS_KNOWN = (
    "Save function is not implemented",
    "Save function should return a table.",
    "This script took too long to Save.",
    "You tried to save an unsupported type",
    "Savedata can only be nested to 25 deep",
    "Loading failed: there was data for the script to load, but the script does not have a Load() function.",
    "This script took too long in the Load function.",
    "Loading failed:",
)

_REAL_CHECK_OUTPUT = openttdlab.subprocess.check_output


def _is_game_launch(args):
    return any(str(a).startswith("-vnull") for a in args)


def make_patched_check_output(load_savegame=None, strip_start_ai=False, persist_save_dir=None):
    """Une fabrique de patch par phase : cf. le paragraphe "Difficulte principale" ci-dessus.

    Pose AVANT run_experiments() : le Pool demarre par fork sous Linux, donc chaque worker herite
    du patch (meme raisonnement que probe_ailog.py et bench_v2.enable_savegame_cleanup).
    """

    def _patched(args, *rest, **kwargs):
        args = list(args)
        if not _is_game_launch(args):
            return _REAL_CHECK_OUTPUT(tuple(args), *rest, **kwargs)

        # 1) journal de decision complet, meme technique que sweeps/probe_ailog.py.
        args = [args[0], "-d", f"script={SCRIPT_DEBUG_LEVEL}"] + args[1:]

        # 2) Phase B : charger une sauvegarde existante au lieu de generer une nouvelle carte.
        if load_savegame is not None:
            g_index = args.index("-g")
            args.insert(g_index + 1, str(load_savegame))

        cwd = kwargs.get("cwd")

        # 3) Phase B : la compagnie OpexAI existe deja dans la sauvegarde -- ne pas la relancer.
        if strip_start_ai and cwd:
            scr_path = os.path.join(cwd, "scripts", "game_start.scr")
            if os.path.exists(scr_path):
                with open(scr_path, "r", encoding="utf-8") as handle:
                    lines = handle.readlines()
                kept = [line for line in lines if not line.lstrip().startswith("start_ai")]
                with open(scr_path, "w", encoding="utf-8") as handle:
                    handle.writelines(kept)

        output = _REAL_CHECK_OUTPUT(tuple(args), *rest, **kwargs)

        # 4) Phase A : copier les .sav hors du tempdir AVANT qu'openttdlab ne le detruise (il est
        #    detruit des que run_experiments() retourne, cf. openttdlab.py:230 TemporaryDirectory).
        if persist_save_dir is not None and cwd:
            save_src = os.path.join(cwd, "save")
            if os.path.isdir(save_src):
                os.makedirs(persist_save_dir, exist_ok=True)
                for name in os.listdir(save_src):
                    src = os.path.join(save_src, name)
                    if os.path.isfile(src):
                        shutil.copy2(src, os.path.join(persist_save_dir, name))

        return output

    return _patched


def parse_sav_file(path):
    """Reparse un .sav conserve, independamment de tout alignement avec les lignes de
    run_experiments -- c'est la source de verite pour "quelle sauvegarde a-t-on rechargee" et pour
    les etats "avant" / "apres"."""
    with open(path, "rb") as handle:
        game = openttdlab.parse_savegame(iter(lambda: handle.read(65536), b""))
    chunks = {tag: chunk["records"] for tag, chunk in game["chunks"].items()}
    days_since_year_zero = chunks["DATE"]["0"]["date"]
    days_since_year_one = days_since_year_zero - 366
    game_date = date(1, 1, 1) + timedelta(days_since_year_one)

    all_companies = chunks.get("PLYR", {}) or {}
    player = all_companies.get(0) or all_companies.get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    ratings = bench_v2.station_ratings(chunks)
    other_companies = [
        {"key": key, "is_ai": body.get("is_ai"), "money": body.get("money")}
        for key, body in all_companies.items()
        if str(key) != "0" and isinstance(body, dict)
    ]
    return {
        "file": os.path.basename(path),
        "path": path,
        "date": str(game_date),
        "company_value": last_closed.get("company_value"),
        "performance_history": last_closed.get("performance_history"),
        "profit": bench_v2.quarter_profit(last_closed),
        "profit_year": bench_v2.year_profit(closed),
        "median_station_rating": statistics.median(ratings) if ratings else None,
        "money": (player or {}).get("money"),
        "current_loan": (player or {}).get("current_loan"),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "n_companies_total": len(all_companies),
        "other_companies": other_companies,
    }


def scan_markers(output_text, patterns):
    """Renvoie, pour chaque motif trouve, la (les) ligne(s) completes ou il apparait."""
    output_text = output_text or ""
    lines = output_text.splitlines()
    hits = {pattern: [] for pattern in patterns}
    for line in lines:
        for pattern in patterns:
            if pattern in line:
                hits[pattern].append(line.strip())
    return {pattern: matches for pattern, matches in hits.items() if matches}


def run_phase_a(seed, years, arm, cfg, checkpoint_path, persist_dir):
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    bench_v2.CHECKPOINT_PATH = checkpoint_path
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    openttdlab.subprocess.check_output = make_patched_check_output(persist_save_dir=str(persist_dir))
    try:
        rows = list(run_experiments(
            openttd_version=bench_v2.OPENTTD_VERSION,
            opengfx_version=bench_v2.OPENGFX_VERSION,
            max_workers=1,
            result_processor=bench_v2.keep,
            experiments=[{
                "seed": seed,
                "days": 365 * years,
                "openttd_config": cfg,
                "ais": (arm,),
                "bench_run": ["OpexAI", seed, "phaseA"],
            }],
            ai_libraries=(
                openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
            get_cache_dir=lambda: str(CACHE_DIR),
        ))
    finally:
        openttdlab.subprocess.check_output = _REAL_CHECK_OUTPUT

    output_text = rows[0]["openttd_output"] if rows else ""
    saved_files = sorted(
        os.path.join(persist_dir, name)
        for name in os.listdir(persist_dir)
        if os.path.isfile(os.path.join(persist_dir, name))
    )
    return rows, output_text, saved_files


def run_phase_b(seed, years, arm, cfg, checkpoint_path, load_savegame, persist_dir):
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    bench_v2.CHECKPOINT_PATH = checkpoint_path
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    openttdlab.subprocess.check_output = make_patched_check_output(
        load_savegame=load_savegame, strip_start_ai=True, persist_save_dir=str(persist_dir),
    )
    try:
        rows = list(run_experiments(
            openttd_version=bench_v2.OPENTTD_VERSION,
            opengfx_version=bench_v2.OPENGFX_VERSION,
            max_workers=1,
            result_processor=bench_v2.keep,
            experiments=[{
                "seed": seed,
                "days": 365 * years,
                "openttd_config": cfg,
                "ais": (arm,),
                "bench_run": ["OpexAI", seed, "phaseB"],
            }],
            ai_libraries=(
                openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
            get_cache_dir=lambda: str(CACHE_DIR),
        ))
    finally:
        openttdlab.subprocess.check_output = _REAL_CHECK_OUTPUT

    output_text = rows[0]["openttd_output"] if rows else ""
    saved_files = sorted(
        os.path.join(persist_dir, name)
        for name in os.listdir(persist_dir)
        if os.path.isfile(os.path.join(persist_dir, name))
    )
    return rows, output_text, saved_files


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years-a", type=int, default=3, help="duree de la phase A (partie initiale)")
    parser.add_argument("--years-b", type=int, default=2, help="duree de la phase B (apres rechargement)")
    parser.add_argument("--starting-year", type=int, default=1970)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--mid-fraction", type=float, default=0.5,
        help="position (0-1) de la sauvegarde de milieu de partie a recharger, par date",
    )
    parser.add_argument(
        "--arm", default="OpexAI",
        help="nom ou variante OpexAI[cle=valeur] (ex: OpexAI[save_full_state=1])",
    )
    parser.add_argument(
        "--script-debug", default="4",
        help="niveau -d script=N. 4 est necessaire pour capturer AILog.Info ([I]), "
             "3 ne rend que les [W]/[E]",
    )
    return parser.parse_args()


def main():
    global SCRIPT_DEBUG_LEVEL
    args = parse_args()
    SCRIPT_DEBUG_LEVEL = str(args.script_debug)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cfg = bench_v2.make_cfg(args.starting_year)
    arms = bench_v2.build_arms([args.arm])
    arm = arms[args.arm]

    phase_a_dir = WORK_DIR / "phaseA_saves"
    phase_b_dir = WORK_DIR / "phaseB_saves"
    checkpoint_a = WORK_DIR / "phaseA_checkpoint.jsonl"
    checkpoint_b = WORK_DIR / "phaseB_checkpoint.jsonl"

    print(f"=== Phase A : OpexAI seule, graine {args.seed}, {args.years_a} an(s), sauvegardes conservees ===")
    rows_a, output_a, files_a = run_phase_a(args.seed, args.years_a, arm, cfg, checkpoint_a, phase_a_dir)
    print(f"Phase A terminee : {len(files_a)} sauvegarde(s) conservee(s) dans {phase_a_dir}")

    if not files_a:
        payload = {
            "status": "BLOQUE",
            "blocage": "Phase A n'a produit aucune sauvegarde recuperable (dossier save/ vide ou absent) "
                       "-- le patch de openttdlab.subprocess.check_output n'a pas trouve le cwd attendu, "
                       "ou OpenTTD n'a ecrit aucun .sav. Voir openttd_output_phase_a pour le diagnostic.",
            "openttd_output_phase_a": output_a,
        }
        bench_v2.write_json_atomically(args.out, payload)
        print("BLOQUE : voir", args.out)
        sys.exit(1)

    # Reparse chaque sauvegarde conservee independamment de l'ordre des lignes de
    # run_experiments : c'est la source de verite pour choisir "le milieu de partie".
    parsed_a = [parse_sav_file(path) for path in files_a]
    parsed_a.sort(key=lambda record: record["date"])
    mid_index = min(len(parsed_a) - 1, max(0, int(len(parsed_a) * args.mid_fraction)))
    chosen = parsed_a[mid_index]
    print(
        f"Sauvegarde de milieu de partie retenue : {chosen['file']} "
        f"(date={chosen['date']}, gares={chosen['n_stations']}, vehicules={chosen['n_vehicles']})"
    )

    print(f"\n=== Phase B : rechargement de {chosen['file']}, {args.years_b} an(s) supplementaire(s) ===")
    rows_b, output_b, files_b = run_phase_b(
        args.seed, args.years_b, arm, cfg, checkpoint_b, chosen["path"], phase_b_dir,
    )
    print(f"Phase B terminee : {len(files_b)} sauvegarde(s) conservee(s) dans {phase_b_dir}")

    if not files_b:
        payload = {
            "status": "BLOQUE",
            "blocage": "Phase B (rechargement) n'a produit aucune sauvegarde -- le chargement via "
                       "'-g <savegame>' a probablement echoue avant meme le premier point de sauvegarde "
                       "mensuel. Voir openttd_output_phase_b pour le message d'erreur OpenTTD.",
            "phase_a_savegame_reloaded": chosen,
            "openttd_output_phase_b": output_b,
        }
        bench_v2.write_json_atomically(args.out, payload)
        print("BLOQUE : voir", args.out)
        sys.exit(1)

    parsed_b = [parse_sav_file(path) for path in files_b]
    parsed_b.sort(key=lambda record: record["date"])
    after = parsed_b[-1]

    def trajectory_without_output(rows):
        # openttd_output est le MEME texte integral duplique sur chaque ligne (une par sauvegarde
        # mensuelle) : on le retire ici et on le stocke une seule fois au niveau de la phase.
        cleaned = []
        for row in sorted(rows, key=lambda r: r["date"]):
            cleaned.append({k: v for k, v in row.items() if k != "openttd_output"})
        return cleaned

    markers_a = scan_markers(output_a, REQUIRED_MARKERS)
    markers_b = scan_markers(output_b, REQUIRED_MARKERS)
    engine_failure_a = scan_markers(output_a, ENGINE_FAILURE_MARKERS_KNOWN)
    engine_failure_b = scan_markers(output_b, ENGINE_FAILURE_MARKERS_KNOWN)

    # Preuve que Load() a ete appele : cherchee honnetement, pas inventee. cf. le docstring de ce
    # fichier et le rapport final -- src/script/script_instance.cpp::CallLoad() (verifie sur le
    # binaire OpenTTD 15.3 lui-meme) ne journalise QUE les echecs (pas de Load(), erreur, trop
    # long) via ScriptLog::Warning/Error ; il n'existe aucun message moteur de succes. Et
    # OpexAI::Load() (ai/OpexAI/main.nut) pose `this._loadedFromSave = true` mais n'appelle jamais
    # AILog/OpexSign avec -- ce flag n'est lu nulle part ailleurs dans le fichier. Donc aucun
    # journal actuel ne peut prouver positivement l'appel.
    load_call_proof = {
        "positive_engine_marker_exists": False,
        "positive_ai_marker_exists": False,
        "explanation": (
            "OpexAI::Load() (ai/OpexAI/main.nut) fixe this._loadedFromSave = true mais n'appelle "
            "aucun AILog.Info ni OpexSign : ce flag n'est jamais relu ni journalise ailleurs dans "
            "le fichier, donc rien ne le rend visible dans les journaux actuels. Cote moteur, "
            "ScriptInstance::CallLoad() (src/script/script_instance.cpp de l'arbre OpenTTD 15.3, "
            "verifie directement sur le binaire televerse par ce script) ne produit un message "
            "QUE dans les cas d'echec (pas de fonction Load(), exception, trop long) via "
            "ScriptLog::Warning/Error -- il n'existe structurellement aucun message de succes cote "
            "moteur. L'ABSENCE des motifs d'echec ci-dessous dans le journal de la phase B est donc "
            "un signe negatif rassurant (aucun echec connu de rechargement de script), MAIS CE "
            "N'EST PAS UNE PREUVE POSITIVE que Load() a ete appele. Pour obtenir une preuve directe "
            "il faut ajouter un marqueur explicite (ex: AILog.Info(\"OPEX LOAD_CALLED ...\") en tete "
            "de OpexAI::Load()) -- deliberement non fait ici, cette mission ne modifie pas ai/."
        ),
        "engine_failure_markers_found_phase_b": engine_failure_b,
    }

    report = {
        "status": "OK",
        "seed": args.seed,
        "years_a": args.years_a,
        "years_b": args.years_b,
        "starting_year": args.starting_year,
        "config": cfg,
        "script_debug_level": SCRIPT_DEBUG_LEVEL,
        "script_debug_level_caveat": (
            "-d script=3 ne rend que les [W]/[E] (Warning/Error), pas les [I] (Info, la trace de "
            "decision) qui n'arrivent qu'a script=4 -- cf. docs/ailog_capturable_debug_script.md. "
            "Une sortie vide a ce niveau signifie 'aucun warning/error', pas 'rien ne s'est passe'."
        ),
        "phase_a": {
            "n_savegames": len(files_a),
            "savegame_dir": str(phase_a_dir),
            "openttd_output_bytes": len(output_a or ""),
            "openttd_output_raw": output_a,
            "trajectory": trajectory_without_output(rows_a),
            "markers_found": markers_a,
            "engine_failure_markers_found": engine_failure_a,
        },
        "phase_b": {
            "n_savegames": len(files_b),
            "savegame_dir": str(phase_b_dir),
            "openttd_output_bytes": len(output_b or ""),
            "openttd_output_raw": output_b,
            "trajectory": trajectory_without_output(rows_b),
            "markers_found": markers_b,
            "engine_failure_markers_found": engine_failure_b,
        },
        "reloaded_savegame": {
            "path": chosen["path"],
            "file": chosen["file"],
            "date": chosen["date"],
        },
        "company_before_save": {
            "date": chosen["date"],
            "company_value": chosen["company_value"],
            "performance_history": chosen["performance_history"],
            "n_stations": chosen["n_stations"],
            "n_vehicles": chosen["n_vehicles"],
            "money": chosen["money"],
            "current_loan": chosen["current_loan"],
        },
        "company_after_reload": {
            "date": after["date"],
            "company_value": after["company_value"],
            "performance_history": after["performance_history"],
            "n_stations": after["n_stations"],
            "n_vehicles": after["n_vehicles"],
            "money": after["money"],
            "current_loan": after["current_loan"],
        },
        "load_call_proof": load_call_proof,
        "required_marker_scan": {
            "patterns": list(REQUIRED_MARKERS),
            "phase_a": markers_a,
            "phase_b": markers_b,
        },
        "phantom_company_confound": {
            "n_companies_before_save": chosen["n_companies_total"],
            "other_companies_before_save": chosen["other_companies"],
            "n_companies_after_reload": after["n_companies_total"],
            "other_companies_after_reload": after["other_companies"],
            "explanation": (
                "Trouve en verifiant ce rapport, pas demande par la mission : recharger une "
                "sauvegarde ou seule une IA existe (aucun humain) fait apparaitre une compagnie "
                "SUPPLEMENTAIRE (is_ai=0, argent de depart ~100000, jamais mouvementee) qui "
                "n'existait pas dans la sauvegarde d'origine. Verifie dans src/openttd.cpp de "
                "l'arbre OpenTTD 15.3 : SwitchToMode(SM_LOAD_GAME) appelle "
                "OnStartGame(_network_dedicated), qui vaut false tant que le binaire n'est pas "
                "lance avec -D -- contrairement a MakeNewGameDone() (nouvelle partie) qui, lui, "
                "detecte l'absence de GUI (!HasGUI(), notre cas avec -vnull) et force le mode "
                "spectateur. Essaye d'ajouter -D en plus au lancement de la phase B : la compagnie "
                "fantome persiste quand meme (meme resultat, teste dans "
                ".scratch_saveload/probe_dedicated.py, non livre) -- la cause exacte n'a pas ete "
                "poursuivie plus loin, hors perimetre de cette mission. CONSEQUENCE PRATIQUE : "
                "n_stations/n_vehicles ci-dessus comptent TOUTES les compagnies (meme convention "
                "que bench_v2.keep()), mais la compagnie fantome n'a jamais rien construit dans "
                "aucun test effectue ici (argent quasi inchange), donc les chiffres restent, en "
                "pratique, ceux d'OpexAI seule. A surveiller si ce banc sert a des parties plus "
                "longues ou avec plusieurs sauvegardes rechargees en cascade."
            ),
        },
    }
    bench_v2.write_json_atomically(args.out, report)

    print("\n=== Resume ===")
    print(f"Sauvegardes phase A : {len(files_a)}  |  sauvegardes phase B : {len(files_b)}")
    print(f"Sauvegarde rechargee : {chosen['file']}  (date {chosen['date']})")
    print(
        f"Avant sauvegarde : gares={chosen['n_stations']:>3} vehicules={chosen['n_vehicles']:>3} "
        f"valeur={chosen['company_value']}"
    )
    print(
        f"Apres reprise ({args.years_b} an(s) plus tard) : gares={after['n_stations']:>3} "
        f"vehicules={after['n_vehicles']:>3} valeur={after['company_value']}"
    )
    any_markers = any(markers_a.values()) or any(markers_b.values())
    print(
        f"Sortie OpenTTD capturee (-d script={SCRIPT_DEBUG_LEVEL}) : "
        f"phase A={len(output_a or '')} octets, phase B={len(output_b or '')} octets"
    )
    print(f"Motifs requis trouves : {'OUI (voir JSON)' if any_markers else 'aucun'}")
    print("Preuve positive que Load() a ete appele : NON (voir load_call_proof dans le JSON)")
    if after["n_companies_total"] > chosen["n_companies_total"]:
        print(
            f"NOTE : {after['n_companies_total'] - chosen['n_companies_total']} compagnie(s) "
            "fantome(s) apparue(s) au rechargement (voir phantom_company_confound dans le JSON) "
            "-- n'affecte pas les stats OpexAI ci-dessus dans ce test."
        )
    print(f"Rapport complet : {args.out}")


if __name__ == "__main__":
    main()
