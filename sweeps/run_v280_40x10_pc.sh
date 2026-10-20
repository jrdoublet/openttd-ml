#!/usr/bin/env bash
# V280 : lignes rail fret longues (jusqu'à 350 tuiles) en fin de partie, relancé par-dessus V284
# (croissance de flotte fret, défaut 3 sur master), 40 graines x 10 ans, sur le PC.
# À lancer depuis la racine d'un checkout de la branche v280b (master ffd0f51 + v280).
# V280_N = nombre d'années après le départ avant d'ouvrir la portée longue (il faut aussi 1 M£ de
# capital disponible). Le 40x10 GitHub à N = 3 était neutre (−19,3 k£/an) : 2 lignes longues
# seulement, posées en 1977 ; on déclenche donc plus tôt par défaut (N = 1).
#   V280_N=2 bash sweeps/run_v280_40x10_pc.sh
#   PROFILE=vps SMOKE_ONLY=1 bash sweeps/run_v280_40x10_pc.sh  # smoke seul, profil VPS
# 1) smoke 1 graine x 3 ans des deux bras avec decision_log : arrêt sur erreur Squirrel, compte des
#    ouvertures V280_RAIL_LONG ;
# 2) règle gain_short à 40 graines et 10 ans (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %).
# Graines : SEEDS_40, la 73 (plantage déterministe d'AAAHogEx) remplacée par 373684.
set -euo pipefail

V280_N="${V280_N:-1}"
PC=(--cpus 10 --memory 8g --max-workers 10 --network host)
if [ "${PROFILE:-pc}" = "vps" ]; then PC=(--cpus 2 --memory 2g --max-workers 1 --network host); fi
REF="OpexAI[v280_rail_long=0]"
VAR="OpexAI[v280_rail_long=${V280_N}]"
CAMPAIGN="${CAMPAIGN:-v280b_n${V280_N}_v284_40x10_pc_20261020}"
SMOKE="${CAMPAIGN}_smoke"
RULE=(--decision-rule gain_short --required-seeds 40 --required-years 10
      --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5)

python3 sweeps/run_c66_reference.py --campaign "$SMOKE" \
  --reference "OpexAI[v280_rail_long=0,decision_log=1]" \
  --variant "OpexAI[v280_rail_long=${V280_N},decision_log=1]" \
  --variant-policy-id v280_rail_long \
  "${RULE[@]}" --primary-metric profit_year \
  --years 3 --repeats 1 --seeds 42 --script-debug "${PC[@]}"
if zcat -f results/"$SMOKE"_engine/* | grep -q "Your script made an error"; then
  zcat -f results/"$SMOKE"_engine/* | grep "Your script made an error" | head -5
  echo "ARRET : erreur Squirrel au smoke, 40x10 non lance" >&2
  exit 1
fi
n=$(zcat -f results/"$SMOKE"_engine/v280_rail_long_seed*_r0.log* 2>/dev/null | grep -c "V280_RAIL_LONG" || true)
echo "smoke sain ; ouvertures V280_RAIL_LONG (variante, 3 ans) : ${n}"
if [ "${SMOKE_ONLY:-0}" = "1" ]; then exit 0; fi

SEEDS=(
  42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

python3 sweeps/run_c66_reference.py \
  --campaign "$CAMPAIGN" \
  --reference "$REF" \
  --variant "$VAR" \
  --variant-policy-id v280_rail_long \
  "${RULE[@]}" \
  --primary-metric profit_year \
  --years 10 --repeats 1 --seeds "${SEEDS[@]}" \
  --script-debug \
  "${PC[@]}" \
  "$@"
