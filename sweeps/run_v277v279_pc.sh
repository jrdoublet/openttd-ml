#!/usr/bin/env bash
# V277 + V279 ensemble (opcodes AIR : publication rapide et re-selection memorisee), contre master.
# Reprise 25/10 : master actualise (4c64ca2a), n75_multi_cargo=2 par defaut dans les deux bras.
# Chacun a passe seul un 20x10 non_erosion (V277 -2,78 %, V279 +3,26 %) ; jamais testes ensemble.
# Regle des optimisations d'opcodes (AGENTS.md, feedback du 24/09) : gain d'opcodes + 20x10 neutre
# => adoption. A lancer depuis la racine d'un checkout de master, sur le PC.
#   smoke 1 graine x 1 an (arret sur erreur Squirrel d'OpexAI), puis non_erosion 20 graines x 10 ans.
# PROFILE remplace le profil Docker ; SMOKE_ONLY=1 s'arrete apres le smoke.
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
REF="OpexAI[v277_air_pub_fast=0,v279_reselect_memo=0]"
VAR="OpexAI[v277_air_pub_fast=1,v279_reselect_memo=1]"
CAMP="${CAMPAIGN:-v277v279_porteB_20x10_multicargo_20261025}"
RULE=(--variant-policy-id v277v279 --decision-rule non_erosion
      --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5)

# 20 premieres graines canoniques (73 remplacee par 373684).
SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309)

python3 sweeps/run_c66_reference.py --campaign "${CAMP}_smoke" \
  --reference "$REF" --variant "$VAR" "${RULE[@]}" \
  --years 1 --repeats 1 --seeds 42 --script-debug "${PC[@]}" || true
# Seules les erreurs d'OpexAI (compagnie 0) arretent : AAAHogEx plante parfois seul (IsBiDirectional).
if zcat -f results/"${CAMP}_smoke"_engine/* | grep -q "\[0\] \[S\] Your script made an error"; then
  zcat -f results/"${CAMP}_smoke"_engine/* | grep -A6 "\[0\] \[S\] Your script made an error" | head -20
  echo "ARRET : erreur Squirrel d'OpexAI au smoke, banc non lance" >&2
  exit 1
fi
[ "${SMOKE_ONLY:-0}" = 1 ] && exit 0
python3 sweeps/run_c66_reference.py --campaign "$CAMP" \
  --reference "$REF" --variant "$VAR" "${RULE[@]}" \
  --years 10 --repeats 1 --seeds "${SEEDS[@]}" --script-debug "${PC[@]}" "$@"
