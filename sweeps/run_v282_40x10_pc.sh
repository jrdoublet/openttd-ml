#!/usr/bin/env bash
# V282 : correctif V206 (erreur 525, rame > vehicle.max_train_length) retesté avec V280 actif,
# 40 graines x 10 ans, sur le PC. À lancer depuis la racine d'un checkout de la branche v282
# (v280 + v206_train_length_cap).
# Bras par défaut : la référence a V280 = 3 sans correctif, la variante V280 = 3 avec la rame bornée
# (mode 1 : rame seule, quai inchangé). On isole ainsi l'effet du correctif là où il sert : sur les
# lignes longues ouvertes par V280.
#   V206_MODE=2 bash sweeps/run_v282_40x10_pc.sh   # rame ET quai bornés (correctif V206 d'origine)
#   V280_N=0 bash sweeps/run_v282_40x10_pc.sh      # correctif seul, sans V280
#   PROFILE=vps SMOKE_ONLY=1 bash sweeps/run_v282_40x10_pc.sh  # smoke seul, profil VPS
# 1) smoke 1 graine x 1 an des deux bras : arrêt si le journal moteur contient une erreur Squirrel ;
# 2) règle gain_short à 40 graines et 10 ans (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %).
# Graines : SEEDS_40, la 73 (plantage déterministe d'AAAHogEx) remplacée par 373684, comme V280 sur GitHub.
set -euo pipefail

V280_N="${V280_N:-3}"
V206_MODE="${V206_MODE:-1}"
PC=(--cpus 10 --memory 8g --max-workers 10 --network host)
if [ "${PROFILE:-pc}" = "vps" ]; then PC=(--cpus 2 --memory 2g --max-workers 1 --network host); fi
REF="OpexAI[v206_train_length_cap=0,v280_rail_long=${V280_N}]"
VAR="OpexAI[v206_train_length_cap=${V206_MODE},v280_rail_long=${V280_N}]"
CAMPAIGN="${CAMPAIGN:-v282_v206m${V206_MODE}_v280n${V280_N}_40x10_pc_20261020}"
SMOKE="${CAMPAIGN}_smoke"
RULE=(--decision-rule gain_short --required-seeds 40 --required-years 10
      --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5)

python3 sweeps/run_c66_reference.py --campaign "$SMOKE" \
  --reference "$REF" --variant "$VAR" --variant-policy-id v206_train_length_cap \
  "${RULE[@]}" \
  --years 1 --repeats 1 --seeds 42 --script-debug "${PC[@]}"
if zcat -f results/"$SMOKE"_engine/* | grep -q "Your script made an error"; then
  zcat -f results/"$SMOKE"_engine/* | grep "Your script made an error" | head -5
  echo "ARRET : erreur Squirrel au smoke, 40x10 non lance" >&2
  exit 1
fi
if [ "${SMOKE_ONLY:-0}" = "1" ]; then echo "smoke sain"; exit 0; fi

SEEDS=(
  42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

python3 sweeps/run_c66_reference.py \
  --campaign "$CAMPAIGN" \
  --reference "$REF" \
  --variant "$VAR" \
  --variant-policy-id v206_train_length_cap \
  "${RULE[@]}" \
  --primary-metric profit_year \
  --years 10 --repeats 1 --seeds "${SEEDS[@]}" \
  --script-debug \
  "${PC[@]}" \
  "$@"

# Exposition du mécanisme : NOTRAIN en erreur 525 par bras (attendu : 0 dans la variante).
for arm in reference v206_train_length_cap; do
  n=$(zcat -f results/"$CAMPAIGN"_engine/${arm}_seed*_r0.log* 2>/dev/null | grep -c "NOTRAIN error=525" || true)
  echo "NOTRAIN 525 ${arm} : ${n}"
done
