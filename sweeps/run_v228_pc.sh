#!/usr/bin/env bash
# V228 : duel OpexAI contre AAAHogEx sur 10 ans hors du cadre habituel, sur le PC.
# A lancer depuis la racine d'un checkout de la branche v228 (= master du 19/10, defauts actuels).
# Un bras (C66.3, OpexAI aux defauts contre AAAHogEx), 20 graines canoniques x 10 ans par condition :
#   ref1970  depart 1970, carte 256x256 (reference, meme code)
#   y1950    depart 1950, carte 256x256
#   y1990    depart 1990, carte 256x256
#   map1024  depart 1970, carte 1024x1024 (2^10 tuiles par cote : --map-size 10).
#            "1024" designe ici la TAILLE de la carte, jamais une graine.
# Argument : une ou plusieurs conditions. Si map1024 est demande, ce banc passe en premier.
# Chaque condition commence par un smoke 1 graine x 1 an, avec arret sur erreur Squirrel.
# Lecture : ratio profit Opex/AAA par condition, compare a ref1970 (pas de verdict A/B, il n'y a qu'un bras).
set -euo pipefail
PROFILE=(${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host})
# 20 graines canoniques identiques pour chaque taille de carte ; la graine 1024
# est une graine ordinaire parmi les 20 et ne determine jamais la taille de carte.
# La graine 73 (plantage deterministe d AAAHogEx) est remplacee par 373684.
SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309)
# Bras unique aux defauts (C66.3, sans options de decision C66.4) : le lanceur exige OpexAI[cle=valeur],
# on donne un reglage a sa valeur par defaut.
REF="OpexAI[v264_convergent_freight=1]"

opts_for() {
  case "$1" in
    ref1970) echo "--start-year 1970 --map-size 8" ;;
    y1950)   echo "--start-year 1950 --map-size 8" ;;
    y1990)   echo "--start-year 1990 --map-size 8" ;;
    map1024) echo "--start-year 1970 --map-size 10" ;;
    *) echo "condition inconnue : $1" >&2; exit 2 ;;
  esac
}

CONDS=("$@")
[ ${#CONDS[@]} -eq 0 ] && CONDS=(map1024 ref1970 y1950 y1990)
# Keep the large-map benchmark first even if the caller uses the historical order.
if [[ " ${CONDS[*]} " == *" map1024 "* ]]; then
  ORDERED=(map1024)
  for c in "${CONDS[@]}"; do
    [[ "$c" == map1024 ]] || ORDERED+=("$c")
  done
  CONDS=("${ORDERED[@]}")
fi
# Optional suffix for a future fresh run; never overwrite an incomplete campaign.
V228_CAMPAIGN_TAG="${V228_CAMPAIGN_TAG:-}"
if [[ -n "$V228_CAMPAIGN_TAG" && ! "$V228_CAMPAIGN_TAG" =~ ^_[a-zA-Z0-9_]+$ ]]; then
  echo "V228_CAMPAIGN_TAG invalide (attendu : _suffixe_alphanumerique)" >&2
  exit 2
fi
for c in "${CONDS[@]}"; do
  read -r -a OPTS <<< "$(opts_for "$c")"
  camp="v228_${c}_20x10_pc_20261019${V228_CAMPAIGN_TAG}"
  python3 sweeps/run_c66_reference.py --campaign "${camp}_smoke" --reference "$REF" \
    --years 1 --repeats 1 --seeds 42 --script-debug "${OPTS[@]}" "${PROFILE[@]}" || true
  if zcat -f results/"${camp}_smoke"_engine/* | grep -q "\[0\] \[S\] Your script made an error"; then
    zcat -f results/"${camp}_smoke"_engine/* | grep -A6 "\[0\] \[S\] Your script made an error" | head -20
    echo "ARRET : erreur Squirrel au smoke $c" >&2; exit 1
  fi
  python3 sweeps/run_c66_reference.py --campaign "$camp" --reference "$REF" \
    --years 10 --repeats 1 --seeds "${SEEDS[@]}" \
    "${OPTS[@]}" "${PROFILE[@]}"
done
