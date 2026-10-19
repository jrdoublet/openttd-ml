#!/usr/bin/env bash
# V267 : choisir les 40 graines de banc les plus complementaires, sur le PC.
# A lancer depuis la racine d'un checkout de la branche v267 (master du 19/10 fusionne).
# Etapes (argument 1) :
#   smoke   1 graine x 1 an, un bras : verifie que la commande demarre et que le journal est sain ;
#   pilote  30 graines x 10 ans, deux bras (controle V252 2 contre 0) : cout par partie, sert a dimensionner ;
#   main    les graines restantes de la population (offset 30), memes bras ;
#   select  relit pilote + main et retient 40 graines (glouton MMD), resultat dans results/v267_selection_20261019.json.
# Variables : COUNT (taille de la population, defaut 300), NOCONTROL=1 (un seul bras, cout / 2).
set -euo pipefail
PROFILE=(${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host})
STEP="${1:?smoke|pilote|main|select}"
COUNT="${COUNT:-300}"
SEEDS_FILE="results/v267_seeds_${COUNT}.txt"
CTRL=()
[ "${NOCONTROL:-0}" = "1" ] && CTRL=(--no-control)
mkdir -p results
[ -f "$SEEDS_FILE" ] || python3 sweeps/v267_seeds.py generate --count "$COUNT" --out "$SEEDS_FILE"

run_cmd() {  # la sous-commande "command" imprime une ligne run_c66_reference.py par tranche
  python3 sweeps/v267_seeds.py command --seeds-file "$SEEDS_FILE" "${CTRL[@]}" "$@" | while read -r line; do
    echo "+ $line"
    eval "$line"
  done
}

case "$STEP" in
  smoke)
    python3 sweeps/run_c66_reference.py --campaign v267_smoke_1x1_pc_20261019 \
      --reference "OpexAI[v252_air_engine_refresh=2]" \
      --years 1 --repeats 1 --seeds 42 --script-debug \
      "${PROFILE[@]}" || true
    if zcat -f results/v267_smoke_1x1_pc_20261019_engine/* | grep -q "\[0\] \[S\] Your script made an error"; then
      echo "ARRET : erreur Squirrel au smoke" >&2; exit 1
    fi ;;
  pilote) run_cmd --campaign v267_pilote_30x10_pc_20261019 --limit 30 ;;
  main)   run_cmd --campaign v267_main_x10_pc_20261019 --offset 30 ;;
  select)
    python3 sweeps/v267_seeds.py select results/v267_pilote_30x10_pc_20261019.jsonl results/v267_main_x10_pc_20261019*.jsonl \
      "${CTRL[@]}" --k 40 --out results/v267_selection_20261019.json ;;
  *) echo "etape inconnue : $STEP" >&2; exit 2 ;;
esac
