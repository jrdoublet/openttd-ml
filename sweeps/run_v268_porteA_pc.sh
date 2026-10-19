#!/usr/bin/env bash
# V268 mode 2 : C70 lit l'estimation a 6 mois des lignes de moins de 2 ans. Porte A 40 graines x 3 ans, sur le PC.
# A lancer depuis la racine d'un checkout de la branche v268.
# 1) smoke 1 graine x 1 an des deux bras : arret si le journal moteur contient une erreur Squirrel ;
# 2) regle gain_short a 40 graines et 3 ans (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %).
# Graines : SEEDS_40 de bench_v2.py, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684.
# PROFILE remplace le profil Docker du PC ; SMOKE_ONLY=1 s'arrete apres le smoke.
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
REF="OpexAI[v268_c70_early=0]"
VAR="OpexAI[v268_c70_early=2]"
CAMP="${CAMPAIGN:-v268m2_porteA_40x3_pc_20261019}"
RULE=(--variant-policy-id v268_c70_early --decision-rule gain_short --required-seeds 40 --required-years 3
      --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5)

python3 sweeps/run_c66_reference.py --campaign "${CAMP}_smoke" \
  --reference "$REF" --variant "$VAR" "${RULE[@]}" \
  --years 1 --repeats 1 --seeds 42 --script-debug "${PC[@]}"
if zcat -f results/"${CAMP}_smoke"_engine/* | grep -q "Your script made an error"; then
  zcat -f results/"${CAMP}_smoke"_engine/* | grep "Your script made an error" | head -5
  echo "ARRET : erreur Squirrel au smoke, porte A non lancee" >&2
  exit 1
fi
[ "${SMOKE_ONLY:-0}" = 1 ] && exit 0

SEEDS=(
  42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
  --reference "$REF" --variant "$VAR" "${RULE[@]}" \
  --years 3 --repeats 1 --seeds "${SEEDS[@]}" --script-debug "${PC[@]}" "$@"
