#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Orchestrateur Nuit OpexAI : Pack Nuit Complet
# 1. Phase 1 : Duel 1v1 OpexAI vs AAAHogEx (carte partagée, 20 graines x 5 ans)
#    -> results/bench_1v1_5y_20seeds_reference.json
# 2. Phase 2 : Banc Causal Adaptatif Richesse (20 graines x 10 ans)
#    -> results/bench_air_cadence_adaptive_10y_20seeds.json
# ==============================================================================

START_TIME=$(date +%s)
echo "=============================================================================="
echo "LANCEMENT DU PACK NUIT OPEXAI - $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=============================================================================="

SEEDS="42 100 7 999 2026 1 17 73 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309"

if [ -f "results/bench_1v1_5y_20seeds_reference.json" ]; then
    echo ">>> [1/2] Duel 1v1 déjà terminé et présent (results/bench_1v1_5y_20seeds_reference.json), passage direct à la phase 2."
    T2=$(date +%s)
else
    echo ""
    echo ">>> [1/2] DÉMARRAGE DUEL 1v1 OPEXAI vs AAAHOGEX (20 graines x 5 ans)..."
    T1=$(date +%s)
    python3 sweeps/bench_1v1_5y_20seeds.py \
        --years 5 \
        --seeds $SEEDS \
        --max-workers 3 \
        --out results/bench_1v1_5y_20seeds_reference.json
    T2=$(date +%s)
    echo ">>> [1/2] Duel 1v1 terminé en $(( T2 - T1 )) secondes."
fi

echo ""
echo ">>> [2/2] DÉMARRAGE BANC CAUSAL ADAPTATIF RICHESSE (20 graines x 10 ans)..."
python3 sweeps/bench_v2.py \
    --arms "OpexAI" "OpexAI[air_cadence_cap_adaptive=1]" \
    --years 10 \
    --seeds $SEEDS \
    --max-workers 3 \
    --out results/bench_air_cadence_adaptive_10y_20seeds.json
T3=$(date +%s)
echo ">>> [2/2] Banc Causal Adaptatif terminé en $(( T3 - T2 )) secondes."

TOTAL_ELAPSED=$(( T3 - START_TIME ))
echo ""
echo "=============================================================================="
echo "PACK NUIT TERMINÉ AVEC SUCCÈS en $(( TOTAL_ELAPSED / 60 )) min $(( TOTAL_ELAPSED % 60 )) s !"
echo "Résultats produits :"
ls -lh results/bench_1v1_5y_20seeds_reference.json* results/bench_air_cadence_adaptive_10y_20seeds.json*
echo "=============================================================================="
