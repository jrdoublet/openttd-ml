#!/usr/bin/env bash
# V267 : choisir 40 graines de banc diverses (types de cartes et situations), sur le PC.
# A lancer depuis la racine d'un checkout de la branche v267.
# Etapes (argument 1) :
#   smoke   1 graine x 1 an, un bras : verifie que la commande demarre et que le journal est sain ;
#   maps    lit la carte de MAPS graines (partie d'un jour sans IA, deterministe) : relief, mer,
#           rivieres, cotes, villes, industries, rivieres et mer a franchir entre villes ;
#   pop     choisit COUNT graines diverses parmi les MAPS (quotas des deciles extremes, puis MMD) ;
#   main    joue la population COUNT x 10 ans, un bras (OpexAI aux defauts contre AAAHogEx) ;
#   select  relit cartes + parties et retient 40 graines : results/v267_selection_20261019.{json,txt}.
# Variables : MAPS (defaut 3000), COUNT (defaut 300 ; ~38 s par partie de 10 ans a 10 workers),
#             CONTROL=1 (second bras V252 0 contre 2, cout x2 ; desactive par defaut).
set -euo pipefail
PROFILE=(${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host})
STEP="${1:?smoke|maps|pop|main|select}"
MAPS="${MAPS:-3000}"
COUNT="${COUNT:-300}"
MAPS_FILE="results/v267_maps_${MAPS}.jsonl"
# Criblage VPS du 19/10 (3000 cartes, init 20261019) versionne : l'etape maps est facultative.
[ -f "$MAPS_FILE" ] || [ "$MAPS" != 3000 ] || MAPS_FILE="sweeps/v267_data/v267_maps_3000.jsonl.gz"
POP_FILE="results/v267_pop_${COUNT}.txt"
CTRL=(--no-control)
[ "${CONTROL:-0}" = "1" ] && CTRL=()
mkdir -p results

run_cmd() {  # la sous-commande "command" imprime une ligne run_c66_reference.py par tranche
  python3 sweeps/v267_seeds.py command --seeds-file "$POP_FILE" "${CTRL[@]}" "$@" | while read -r line; do
    echo "+ $line"
    eval "$line"
  done
}

case "$STEP" in
  smoke)
    python3 sweeps/run_c66_reference.py --campaign v267_smoke_1x1_pc_20261019 \
      --years 1 --repeats 1 --seeds 42 --script-debug \
      "${PROFILE[@]}" || true
    if zcat -f results/v267_smoke_1x1_pc_20261019_engine/* | grep -q "\[0\] \[S\] Your script made an error"; then
      echo "ARRET : erreur Squirrel au smoke" >&2; exit 1
    fi ;;
  maps)
    docker run --rm --network host --cpus=10 --memory=8g -v openttd-lab-home:/home/lab \
      -v "$PWD":/work -w /work openttd-lab:latest \
      python3 sweeps/v267_maps.py screen --count "$MAPS" --out "$MAPS_FILE" --workers 10 --batch 200 ;;
  pop)
    python3 sweeps/v267_seeds.py select --maps "$MAPS_FILE" --no-control --k "$COUNT" \
      --exclude 73 --out "results/v267_pop_${COUNT}.json" --seeds-out "$POP_FILE" ;;
  main)
    [ -f "$POP_FILE" ] || { echo "lancer d'abord l'etape pop" >&2; exit 1; }
    run_cmd --campaign v267_main_x10_pc_20261019 ;;
  select)
    python3 sweeps/v267_seeds.py select results/v267_main_x10_pc_20261019*.jsonl --maps "$MAPS_FILE" \
      "${CTRL[@]}" --k 40 --out results/v267_selection_20261019.json \
      --seeds-out results/v267_selection_20261019.txt ;;
  *) echo "etape inconnue : $STEP" >&2; exit 2 ;;
esac
