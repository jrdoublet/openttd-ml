#!/usr/bin/env bash
# V294c adaptatif (v294_rail_weight_adapt=400) contre le poids historique (120 % sous 100 tuiles,
# 200 % au-dela), RAIL SEUL des deux cotes, candidats rail bornes a 250 tuiles dans les deux bras
# (v294_rail_dist_decouple=250). A lancer depuis la racine d'un checkout de master (>= 277d7ede), sur le PC.
# Diagnostic VPS du 21/10 (v294c_adapt400_long250_6x3_20261021) : >= 200 tuiles ABND 5 -> 1,
# iterations medianes 2 472 -> 406, detour +1 % ; +54,4 k sur 6 graines (diagnostic seulement).
#   GATE=A (defaut) : smoke 1 graine x 1 an, puis porte A gain_short 40 graines x 3 ans
#                     (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %) ;
#   GATE=B          : porte B non_erosion 20 graines x 10 ans (sur accord de l'utilisateur).
# Sans decision_log : pas d'effet observateur sur les opcodes (porte du 20/10 : meme choix).
# Graines : SEEDS_40 de bench_v2.py, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684 ;
# porte B = les 20 premieres. PROFILE remplace le profil Docker ; SMOKE_ONLY=1 s'arrete apres le smoke.
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
GATE="${GATE:-A}"
ADAPT="${ADAPT:-400}"
DIST="${DIST:-250}"
MODES="mode_air=0,mode_road=0,mode_water=0,v294_rail_dist_decouple=${DIST}"
AAA=(--aaahogex-setting disable_veh_aircraft=1 --aaahogex-setting disable_veh_roadveh=1
     --aaahogex-setting disable_veh_tram=1 --aaahogex-setting disable_veh_ship=1)
REF="OpexAI[${MODES},v294_rail_weight_adapt=0]"
VAR="OpexAI[${MODES},v294_rail_weight_adapt=${ADAPT}]"
COMMON=(--variant-policy-id v294c_long --primary-metric profit_year --min-useful-primary-delta-pct 4
        --value-guard-max-loss-pct 5 --map-size 8)

SEEDS=(
  42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

if [ "$GATE" = A ]; then
  CAMP="${CAMPAIGN:-v294c_a${ADAPT}_long${DIST}_railseul_porteA_40x3_pc_20261021}"
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
  CAMP="${CAMPAIGN:-v294c_a${ADAPT}_long${DIST}_railseul_porteB_20x10_pc_20261021}"
  RULE=(--decision-rule non_erosion "${COMMON[@]}")
  python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
    --reference "$REF" --variant "$VAR" "${RULE[@]}" \
    --years 10 --repeats 1 --seeds "${SEEDS[@]:0:20}" --script-debug "${AAA[@]}" "${PC[@]}" "$@"
else
  echo "GATE doit valoir A ou B" >&2
  exit 2
fi
