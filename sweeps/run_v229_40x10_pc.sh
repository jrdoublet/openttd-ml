#!/usr/bin/env bash
# V229 : facteur C70 par cellule (mode x pax/fret x tranche de distance), 40 graines x 10 ans, sur le PC.
# A lancer depuis la racine d'un checkout de origin/v229 (master fusionne le 19/10).
# Regle gain_short a 40 graines et 10 ans (Wilcoxon, IC95 bootstrap, seuil relatif 4 %, garde de valeur 5 %).
# Graines : SEEDS_40 de bench_v2.py, la 73 (plantage deterministe d'AAAHogEx) remplacee par 373684,
# 21e valeur de la suite LCG qui a produit SEEDS_EXTRA_20 (graine 20260923), choisie avant le lancement.
# --script-debug : le journal moteur garde les lignes phase=c70_factor (une par cellule et par an),
# pour verifier au retour que les cellules ont bien remplace le facteur de mode.
set -euo pipefail

SEEDS=(
  42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309
  423960 613553 515222 781335 375172 999533 442018 746035 455216 230185
  706990 983759 802204 232037 723002 313707 701256 292001 841478 59527
)

python3 sweeps/run_c66_reference.py \
  --campaign "${CAMPAIGN:-v229_40x10_pc_20261019}" \
  --reference "OpexAI[v229_c70_cells=0]" \
  --variant "OpexAI[v229_c70_cells=1]" \
  --variant-policy-id v229_c70_cells \
  --decision-rule gain_short --required-seeds 40 --required-years 10 \
  --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 \
  --years 10 --repeats 1 --seeds "${SEEDS[@]}" \
  --script-debug \
  --cpus 10 --memory 8g --max-workers 10 --network host \
  "$@"
