#!/usr/bin/env bash
# V294all + V295 : combinaison A* rail (ponts 20, A* continu, poids 200, couts AAA, sonde
# inverse 300, railMax 200, pente selon le moteur) + A* rapide exact V295, contre master
# (tous ces reglages a 0). A lancer depuis la racine d'un checkout de master (>= 6dcd532), sur le PC.
#   START_YEAR=1970 (defaut) | 1927 : annee de depart (1920 injouable : aucun vehicule avant 1925) ;
#   RAILSEUL=0 (defaut)      : partie complete ;
#   RAILSEUL=1               : rail seul des deux cotes (OpexAI sans air/route/eau, AAAHogEx sans
#                              avions/routiers/trams/bateaux), comme v294c_a400_porteA_40x3_rail ;
#   GATE=A (defaut)          : smoke 1 graine x 1 an, puis porte A gain_short 40 graines x 3 ans
#                              (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %) ;
#   GATE=B                   : porte B non_erosion 20 graines x 10 ans (sur accord de l'utilisateur).
#   ADAPT=0 (defaut)         : A* continu (V294b), V294c adaptatif exclu ;
#   ADAPT=N (100..400)       : recherche segmentee (v294_rail_continuous=0) et V294c adaptatif a N ;
#                              le poids 200 de v294_rail_weight_pct sert alors de premier repli.
# V294c adaptatif n'agit que dans la recherche segmentee : sous v294_rail_continuous=1 il est inerte.
# V294h (v294_rail_defer) est exclu (porte A -36,9 k, et inerte sous l'A* continu).
# Graines : SEEDS_40 de bench_v2.py, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684 ;
# porte B = les 20 premieres. PROFILE remplace le profil Docker ; SMOKE_ONLY=1 s'arrete apres le smoke.
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
GATE="${GATE:-A}"
YEAR="${START_YEAR:-1970}"
MODES=""; AAA=(); TAG=complet
if [ "${RAILSEUL:-0}" = 1 ]; then
  MODES=",mode_air=0,mode_road=0,mode_water=0"
  AAA=(--aaahogex-setting disable_veh_aircraft=1 --aaahogex-setting disable_veh_roadveh=1
       --aaahogex-setting disable_veh_tram=1 --aaahogex-setting disable_veh_ship=1)
  TAG=railseul
fi
ADAPT="${ADAPT:-0}"
if [ "$ADAPT" = 0 ]; then SEARCH="v294_rail_continuous=1"; else SEARCH="v294_rail_continuous=0,v294_rail_weight_adapt=${ADAPT}"; TAG="${TAG}_adapt${ADAPT}"; fi
COMBO="v294_rail_bridge_len=20,${SEARCH},v294_rail_weight_pct=200,v294_rail_aaa_costs=1"
COMBO="${COMBO},rail_reverse_astar_iters=300,v294_rail_dist_decouple=200,v294_rail_slope_engine=1"
REF="OpexAI[v294_rail_continuous=0${MODES}]"
VAR="OpexAI[${COMBO}${MODES}]"
COMMON=(--variant-policy-id v294all --primary-metric profit_year --min-useful-primary-delta-pct 4
        --value-guard-max-loss-pct 5 --start-year "$YEAR" --map-size 8)

SEEDS=(
  42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

if [ "$GATE" = A ]; then
  CAMP="${CAMPAIGN:-v294all_${TAG}_${YEAR}_porteA_40x3_pc_20261021}"
  RULE=(--decision-rule gain_short --required-seeds 40 --required-years 3 "${COMMON[@]}")
  python3 sweeps/run_c66_reference.py --campaign "${CAMP}_smoke" \
    --reference "$REF" --variant "$VAR" "${RULE[@]}" \
    --years 1 --repeats 1 --seeds 42 --script-debug "${AAA[@]}" "${PC[@]}" || true
  # Seules les erreurs d'OpexAI (compagnie 0) arretent : AAAHogEx plante parfois seul (IsBiDirectional).
  if zcat -f results/"${CAMP}_smoke"_engine/* | grep -q "\[0\] \[S\] Your script made an error"; then
    zcat -f results/"${CAMP}_smoke"_engine/* | grep -A6 "\[0\] \[S\] Your script made an error" | head -20
    echo "ARRET : erreur Squirrel d'OpexAI au smoke, porte A non lancee" >&2
    exit 1
  fi
  [ "${SMOKE_ONLY:-0}" = 1 ] && exit 0
  python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
    --reference "$REF" --variant "$VAR" "${RULE[@]}" \
    --years 3 --repeats 1 --seeds "${SEEDS[@]}" --script-debug "${AAA[@]}" "${PC[@]}" "$@"
elif [ "$GATE" = B ]; then
  CAMP="${CAMPAIGN:-v294all_${TAG}_${YEAR}_porteB_20x10_pc_20261021}"
  RULE=(--decision-rule non_erosion "${COMMON[@]}")
  python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
    --reference "$REF" --variant "$VAR" "${RULE[@]}" \
    --years 10 --repeats 1 --seeds "${SEEDS[@]:0:20}" --script-debug "${AAA[@]}" "${PC[@]}" "$@"
else
  echo "GATE doit valoir A ou B" >&2
  exit 2
fi
