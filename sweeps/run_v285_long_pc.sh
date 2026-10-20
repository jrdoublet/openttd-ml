#!/usr/bin/env bash
# V285 : suivi economique a dix ans, UNIQUEMENT apres exposition physique prouvee.
# 20 graines independantes x 10 ans, sans decision_log ni probes supplementaires :
# l'activation du journal integral modifie les trajectoires et invaliderait
# une comparaison avec les portes habituelles. Mode 6 (wagons sans quai long).
set -euo pipefail
read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
CAMP="${CAMPAIGN:-v285m6_railseul_20x10_pc_20261020}"
SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309)
MODES=",mode_air=0,mode_road=0,mode_water=0"
REF="OpexAI[v285_rail_pax_growth=0${MODES}]"
VAR="OpexAI[v285_rail_pax_growth=6${MODES}]"
python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
  --reference "$REF" --variant "$VAR" --variant-policy-id v285m6 \
  --primary-metric profit_year --decision-rule non_erosion \
  --min-useful-primary-delta-pct 0 --value-guard-max-loss-pct 5 \
  --required-seeds 20 --required-years 10 --years 10 --repeats 1 --seeds "${SEEDS[@]}" \
  --script-debug --line-telemetry \
  --aaahogex-setting disable_veh_aircraft=1 \
  --aaahogex-setting disable_veh_roadveh=1 \
  --aaahogex-setting disable_veh_tram=1 \
  --aaahogex-setting disable_veh_ship=1 "${PC[@]}"
