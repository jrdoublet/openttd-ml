#!/usr/bin/env bash
# V263b : passe de suppression approuvee le 20/10, depuis master d1fc302, sur le PC.
# Regle des optimisations d'opcodes, deux arbres : un bras C66.3 par arbre (OpexAI aux defauts
# contre AAAHogEx), memes 20 graines x 10 ans, puis compare_cd_cross_tree_c66.py --economic-only.
# A lancer depuis la racine d'un checkout de la branche v263b. Le script cree ou verifie
# un worktree detache de MASTER_REF (d1fc302 par defaut) dans MASTER_WT et y copie ai/AAAHogEx-115 (non suivi).
# Ne pas retirer ce worktree avant d'avoir copie ses results/ (git worktree remove efface les ignores).
# Les options de decision C66.4 ne sont pas passees : le lanceur les refuse en un seul bras.
# Variables : PROFILE (profil Docker), MASTER_WT (defaut ../v263b-master-tree), SMOKE_ONLY=1.
set -euo pipefail
PROFILE=(${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host})
# 20 graines canoniques, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684 :
# compare_cd_cross_tree_c66.py exige que toutes les parties soient saines.
SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309)
REF="OpexAI[opex_difficulty=2]"
EXPECTED_REMOVED="v252_air_engine_refresh=2,v178_rail_shared_dest=1,v179_rail_gen_dest_served=1,v257_rail_refresh=1,v93_airport_no_pop_floor=1,v163_multi_cargo=0,c76_freight_rotation=0,c80_air_choice_memo=0,c80_air_eval_fast=0,v180_rail_wagon_boost_pct=0,v180_rail_wagon_boost_delay=0"
ROOT="$(pwd)"
MASTER_WT="${MASTER_WT:-../v263b-master-tree}"
[ -f sweeps/run_c66_reference.py ] && [ -d ai/AAAHogEx-115 ] || { echo "lancer depuis la racine du checkout v263b" >&2; exit 2; }

# Reference explicite et immuable : ne pas comparer a un master qui a avance.
MASTER_REF="${MASTER_REF:-d1fc302}"
MASTER_SHA="$(git rev-parse "$MASTER_REF^{commit}")"
if [ -d "$MASTER_WT" ]; then
  [ "$(git -C "$MASTER_WT" rev-parse HEAD)" = "$MASTER_SHA" ] || { echo "worktree master different : choisir MASTER_WT neuf" >&2; exit 2; }
  [ -z "$(git -C "$MASTER_WT" status --porcelain)" ] || { echo "worktree master modifie" >&2; exit 2; }
else
  git worktree add -q --detach "$MASTER_WT" "$MASTER_SHA"
fi
[ -d "$MASTER_WT/ai/AAAHogEx-115" ] || cp -r ai/AAAHogEx-115 "$MASTER_WT/ai/"
MASTER_WT="$(cd "$MASTER_WT" && pwd)"

run_tree() {  # $1 = racine de l'arbre, $2 = campagne
  cd "$1"
  python3 sweeps/run_c66_reference.py --campaign "$2_smoke" --reference "$REF" \
    --years 1 --repeats 1 --seeds 42 --script-debug "${PROFILE[@]}"
  python3 - "results/$2_smoke.json" <<'PYSMOKE'
import json
import sys
from pathlib import Path
result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert not result.get("failed_runs"), "smoke: failed runs"
assert len(result["games"]) == 1, "smoke: expected exactly one game"
assert all(game["game_ok"] for game in result["games"]), "smoke: unhealthy game"
assert len(result["summary"]) == 2, "smoke: missing company summaries"
assert all(row["run_ok"] and row["horizon_complete"] for row in result["summary"]), "smoke: incomplete horizon"
PYSMOKE
  [ "${SMOKE_ONLY:-0}" = 1 ] && { cd "$ROOT"; return; }
  python3 sweeps/run_c66_reference.py --campaign "$2" --reference "$REF" \
    --years 10 --repeats 1 --seeds "${SEEDS[@]}" "${PROFILE[@]}"
  cd "$ROOT"
}

run_tree "$MASTER_WT" v263b_master_n2_20x10_pc_20261020
run_tree "$ROOT" v263b_branch_n2_20x10_pc_20261020
[ "${SMOKE_ONLY:-0}" = 1 ] && exit 0
python3 sweeps/compare_cd_cross_tree_c66.py \
  "$MASTER_WT/results/v263b_master_n2_20x10_pc_20261020.json" \
  results/v263b_branch_n2_20x10_pc_20261020.json \
  --economic-only --expected-removed "$EXPECTED_REMOVED" --out results/v263b_cross_tree_20x10_pc_20261020.json
cat results/v263b_cross_tree_20x10_pc_20261020.json
