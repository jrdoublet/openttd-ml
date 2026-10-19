#!/usr/bin/env bash
# V268 porte B exploratoire : A 40x3 et 40x5 ont echoue. Pas de qualification automatique.
set -euo pipefail
read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
REF="OpexAI[decision_log=1,v268_c70_early=0]"
VAR="OpexAI[decision_log=1,v268_c70_early=2]"
CAMP="${CAMPAIGN:-v268m2_porteB_20x10_pc_20261019}"
SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309)
python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
  --reference "$REF" --variant "$VAR" --variant-policy-id v268_c70_early \
  --decision-rule non_erosion --required-seeds 20 --required-years 10 \
  --primary-metric profit_year --min-useful-primary-delta-pct 4 \
  --value-guard-max-loss-pct 5 --years 10 --repeats 1 \
  --seeds "${SEEDS[@]}" --script-debug "${PC[@]}" "$@"