#!/usr/bin/env bash
# V265 : prolongement d'une ligne rail par embranchement, 40 graines x 10 ans, sur le PC.
# A lancer depuis la racine d'un checkout de la branche (master du 19/10 fusionne, V257 a 1 compris).
# 1) smoke 1 graine x 1 an des deux bras : arret si le journal moteur contient une erreur Squirrel
#    (pas de compilateur sur le VPS, la fusion n'a pas ete jouee) ;
# 2) regle gain_short a 40 graines et 10 ans (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %).
# Graines : SEEDS_40 de bench_v2.py, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684, comme V229.
set -euo pipefail

PC=(--cpus 10 --memory 8g --max-workers 10 --network host)
REF="OpexAI[v265_branch_extension=0]"
VAR="OpexAI[v265_branch_extension=1]"
SMOKE="${CAMPAIGN:-v265_40x10_pc_20261019}_smoke"

python3 sweeps/run_c66_reference.py --campaign "$SMOKE" \
  --reference "$REF" --variant "$VAR" --variant-policy-id v265_branch_extension \
  --decision-rule gain_short --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --required-seeds 1 --required-years 1 --years 1 --repeats 1 --seeds 42 --script-debug "${PC[@]}"
if zcat -f results/"$SMOKE"_engine/* | grep -q "Your script made an error"; then
  zcat -f results/"$SMOKE"_engine/* | grep "Your script made an error" | head -5
  echo "ARRET : erreur Squirrel au smoke, 40x10 non lance" >&2
  exit 1
fi

SEEDS=(
  42 100 314159 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

python3 sweeps/run_c66_reference.py \
  --campaign "${CAMPAIGN:-v265_40x10_pc_20261019}" \
  --reference "$REF" \
  --variant "$VAR" \
  --variant-policy-id v265_branch_extension \
  --decision-rule gain_short --required-seeds 40 --required-years 10 \
  --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 \
  --years 10 --repeats 1 --seeds "${SEEDS[@]}" \
  --script-debug \
  "${PC[@]}" \
  "$@"
