#!/usr/bin/env bash
# V263 : passe de suppression de reglages (code mort V258 + V252 fige au mode 2), sur le PC.
# Regle des optimisations d'opcodes, deux arbres : un bras C66.3 par arbre (OpexAI aux defauts
# contre AAAHogEx), memes 20 graines x 10 ans, puis compare_cd_cross_tree_c66.py --economic-only.
# A lancer depuis la racine d'un checkout de la branche v263. Le script cree (ou remet a jour)
# un worktree detache d'origin/master dans MASTER_WT et y copie ai/AAAHogEx-115 (non suivi).
# Ne pas retirer ce worktree avant d'avoir copie ses results/ (git worktree remove efface les ignores).
# Les options de decision C66.4 ne sont pas passees : le lanceur les refuse en un seul bras.
# Variables : PROFILE (profil Docker), MASTER_WT (defaut ../v263-master-tree), SMOKE_ONLY=1.
set -euo pipefail
PROFILE=(${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host})
# 20 graines canoniques, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684 :
# compare_cd_cross_tree_c66.py exige que toutes les parties soient saines.
SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309)
REF="OpexAI[opex_difficulty=2]"
ROOT="$(pwd)"
MASTER_WT="${MASTER_WT:-../v263-master-tree}"
[ -f sweeps/run_c66_reference.py ] && [ -d ai/AAAHogEx-115 ] || { echo "lancer depuis la racine du checkout v263" >&2; exit 2; }

git fetch -q origin
if [ -d "$MASTER_WT" ]; then
  git -C "$MASTER_WT" checkout -q --detach origin/master
else
  git worktree add -q --detach "$MASTER_WT" origin/master
fi
[ -d "$MASTER_WT/ai/AAAHogEx-115" ] || cp -r ai/AAAHogEx-115 "$MASTER_WT/ai/"
MASTER_WT="$(cd "$MASTER_WT" && pwd)"

run_tree() {  # $1 = racine de l'arbre, $2 = campagne
  cd "$1"
  python3 sweeps/run_c66_reference.py --campaign "$2_smoke" --reference "$REF" \
    --years 1 --repeats 1 --seeds 42 --script-debug "${PROFILE[@]}" || true
  if zcat -f results/"$2_smoke"_engine/* | grep -q "\[0\] \[S\] Your script made an error"; then
    zcat -f results/"$2_smoke"_engine/* | grep -A6 "\[0\] \[S\] Your script made an error" | head -20
    echo "ARRET : erreur Squirrel d'OpexAI au smoke de $2" >&2; exit 1
  fi
  [ "${SMOKE_ONLY:-0}" = 1 ] && { cd "$ROOT"; return; }
  python3 sweeps/run_c66_reference.py --campaign "$2" --reference "$REF" \
    --years 10 --repeats 1 --seeds "${SEEDS[@]}" "${PROFILE[@]}"
  cd "$ROOT"
}

run_tree "$MASTER_WT" v263_master_n2_20x10_pc_20261019
run_tree "$ROOT" v263_branch_n2_20x10_pc_20261019
[ "${SMOKE_ONLY:-0}" = 1 ] && exit 0
python3 sweeps/compare_cd_cross_tree_c66.py \
  "$MASTER_WT/results/v263_master_n2_20x10_pc_20261019.json" \
  results/v263_branch_n2_20x10_pc_20261019.json \
  --economic-only --out results/v263_cross_tree_20x10_pc_20261019.json
cat results/v263_cross_tree_20x10_pc_20261019.json
