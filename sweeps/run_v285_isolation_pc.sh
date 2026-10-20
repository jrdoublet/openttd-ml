#!/usr/bin/env bash
# V285 : ablation physique, jamais un test d'adoption a elle seule.
# VARIANT_MODE=6 (defaut : wagons + 90 j sans quai long), 1 (quai seul) ou 7 (combine).
# YEARS=3 / SEEDS="42 100 7 999 2026" (defaut diagnostic), ou explicitement autre horizon.
# Les deux bras ont probes=6 : panneaux + DECISION_LOG, pour capturer V285_GATE et V285_RESULT.
# Ne pas reutiliser un campaign_id deja publie ; jamais deux Docker en parallele.
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
MODE="${VARIANT_MODE:-6}"
case "$MODE" in 1|6|7) ;; *) echo "VARIANT_MODE doit valoir 1, 6 ou 7" >&2; exit 2;; esac
YEARS="${YEARS:-3}"
read -r -a SEED_LIST <<< "${SEEDS:-42 100 7 999 2026}"
CAMP="${CAMPAIGN:-v285m${MODE}_isolation_${#SEED_LIST[@]}x${YEARS}_pc_20261020}"
MODES=",mode_air=0,mode_road=0,mode_water=0"
REF="OpexAI[v285_rail_pax_growth=0${MODES}]"
VAR="OpexAI[v285_rail_pax_growth=${MODE}${MODES}]"

python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
  --reference "$REF" --variant "$VAR" --variant-policy-id "v285m${MODE}" \
  --decision-rule gain_short --required-seeds "${#SEED_LIST[@]}" --required-years "$YEARS" \
  --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 \
  --years "$YEARS" --repeats 1 --seeds "${SEED_LIST[@]}" --probes 6 --script-debug \
  --line-telemetry \
  --aaahogex-setting disable_veh_aircraft=1 \
  --aaahogex-setting disable_veh_roadveh=1 \
  --aaahogex-setting disable_veh_tram=1 \
  --aaahogex-setting disable_veh_ship=1 "${PC[@]}"

python3 sweeps/analyze_v285_exposure.py \
  --engine-dir "results/${CAMP}_engine" --policy "v285m${MODE}" \
  --expected-seeds "${#SEED_LIST[@]}" \
  --json "results/${CAMP}.v285_exposure.json" \
  --csv "results/${CAMP}.v285_exposure.csv"
