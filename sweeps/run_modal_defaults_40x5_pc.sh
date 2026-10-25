#!/usr/bin/env bash
# C66.3 descriptive benchmarks, *not* adoption gates. 1970-1974, 256x256,
# default OpexAI settings except the switches needed to isolate one mode;
# the same mode is isolated for AAAHogEx. One Opex policy only, no ON/OFF.
# Use MODE=rail / MODE=air, each independently; never run concurrently.
# Daily savegames/checkpoint aggregation and monthly passive line telemetry
# are extracted after the game; do not enable decision_log or other probes.
# Usage: MODE=rail bash sweeps/run_modal_defaults_40x5_pc.sh
#        MODE=air  bash sweeps/run_modal_defaults_40x5_pc.sh
set -euo pipefail
MODE="${MODE:-rail}"
case "$MODE" in
  rail)
    REF='OpexAI[mode_air=0,mode_road=0,mode_water=0]'
    AAA=(--aaahogex-setting disable_veh_aircraft=1
         --aaahogex-setting disable_veh_roadveh=1
         --aaahogex-setting disable_veh_tram=1
         --aaahogex-setting disable_veh_ship=1)
    ;;
  air)
    REF='OpexAI[mode_rail=0,mode_road=0,mode_water=0]'
    AAA=(--aaahogex-setting disable_veh_train=1
         --aaahogex-setting disable_veh_roadveh=1
         --aaahogex-setting disable_veh_tram=1
         --aaahogex-setting disable_veh_ship=1)
    ;;
  *) echo "MODE doit etre rail ou air" >&2; exit 2 ;;
esac

if [ "$(docker ps -q | wc -l)" -ne 0 ]; then
  echo 'Docker est occupe : attendre la fin du banc precedent' >&2
  exit 3
fi

SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191
       12345 54321 65537 123456 424242 8675309 423960 613553 515222
       781335 375172 999533 442018 746035 455216 230185 706990 983759
       802204 232037 723002 313707 701256 292001 841478 59527)
CAMP="${CAMPAIGN:-modal_${MODE}_defaults_master85c88_40x5_20261025}"
if [ -e "results/${CAMP}.json" ] || [ -e "results/${CAMP}.manifest.json" ]; then
  echo "Campagne deja figee : ${CAMP}, refus de relance" >&2
  exit 4
fi

echo "=== ${CAMP} | master=$(git rev-parse --short HEAD) | ${#SEEDS[@]} seeds | one arm ==="
python3 sweeps/run_c66_reference.py --campaign "$CAMP" --reference "$REF" \
  --policy-id "${MODE}_defaults" --start-year 1970 --map-size 8 \
  --years 5 --repeats 1 --seeds "${SEEDS[@]}" \
  --line-telemetry --line-telemetry-monthly --station-supply-telemetry \
  --script-debug --probes 2 \
  "${AAA[@]}" --cpus 9 --memory 8g --max-workers 9 --network host
