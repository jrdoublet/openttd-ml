#!/usr/bin/env bash
# V275 : paquet rail voyageurs (V207 part 40 + courrier + 2 arrets joints) + v275_rail_pax_mm=7
# (pas de rail voyageurs vers nos villes a aeroport, recalage V212 150/85, aerien d'abord 2 ans),
# contre le master. A lancer depuis la racine d'un checkout de la branche v275, sur le PC.
#   GATE=A (defaut) : smoke 1 graine x 1 an, puis porte A gain_short 40 graines x 3 ans
#                     (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %) ;
#   GATE=B          : porte B non_erosion 20 graines x 10 ans (borne haute IC95 >= 0, garde 5 %).
#   RAILSEUL=1      : rail seul des deux cotes (OpexAI sans air/route/eau, AAAHogEx sans
#                     avions/routiers/trams/bateaux), comme railseul_master_40x3_20261019.
#   RAILSEUL=0      : partie complete (defaut).
# Graines : SEEDS_40 de bench_v2.py, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684 ;
# porte B = les 20 premieres. PROFILE remplace le profil Docker ; SMOKE_ONLY=1 s'arrete apres le smoke.
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
GATE="${GATE:-A}"
MODES=""; AAA=(); TAG=complet
if [ "${RAILSEUL:-0}" = 1 ]; then
  MODES=",mode_air=0,mode_road=0,mode_water=0"
  AAA=(--aaahogex-setting disable_veh_aircraft=1 --aaahogex-setting disable_veh_roadveh=1
       --aaahogex-setting disable_veh_tram=1 --aaahogex-setting disable_veh_ship=1)
  TAG=railseul
fi
PAX="v207_rail_pax_share_pct=40,v207_rail_mail=1,v207_rail_pax_joined_stops=2,v275_rail_pax_mm=7"
REF="OpexAI[v275_rail_pax_mm=0${MODES}]"
VAR="OpexAI[${PAX}${MODES}]"

SEEDS=(
  42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

if [ "$GATE" = A ]; then
  CAMP="${CAMPAIGN:-v275_${TAG}_porteA_40x3_pc_20261019}"
  RULE=(--variant-policy-id v275 --decision-rule gain_short --required-seeds 40 --required-years 3
        --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5)
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
  CAMP="${CAMPAIGN:-v275_${TAG}_porteB_20x10_pc_20261019}"
  RULE=(--variant-policy-id v275 --decision-rule non_erosion
        --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5)
  python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
    --reference "$REF" --variant "$VAR" "${RULE[@]}" \
    --years 10 --repeats 1 --seeds "${SEEDS[@]:0:20}" --script-debug "${AAA[@]}" "${PC[@]}" "$@"
else
  echo "GATE doit valoir A ou B" >&2
  exit 2
fi
