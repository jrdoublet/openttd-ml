#!/usr/bin/env bash
# Portes B non_erosion 20 graines x 10 ans de la nuit du 21/10, sur le PC (accord de l'utilisateur).
# A lancer depuis la racine d'un checkout de openttd-ml contenant ai/AAAHogEx-115 :
#   bash sweeps/run_porteB_nuit_20261021_pc.sh [adapt400|v297|v296a|finpartie|all]   (defaut : all, dans cet ordre)
# Chaque candidat tourne dans un worktree detache de sa branche (origin), cree a cote du checkout
# (../porteB-<candidat>) ; AAAHogEx y est copie. NE PAS retirer ces worktrees avant d'avoir copie
# results/ : `git worktree remove` efface les fichiers ignores.
#   adapt400 : multimodal, master, v294_rail_weight_adapt 0 contre 400 (40x5 1970 prometteur, 21/10) ;
#   v297     : rail seul, branche v297, plancher de ROI rail 0 contre 400 (porte A rail seul passee :
#              +68,7 k, p = 0,019) ;
#   v296a    : partie complete, branche v296a, pose groupee 0 contre 1 (portes A neutres, regle des
#              optimisations d'opcodes) ;
#   finpartie : partie complete, branche finpartie, V249s mode 2 + V292b contre master (40x10 gain_short
#              GitHub 39531909017 : +286,5 k, p = 0,0005, valeur -3,4 %).
# Toutes les branches contiennent le correctif du renfort aerien (IsValidVehicle(null), graine 123456).
# Graines : les 20 premieres de SEEDS_40 (la 73 remplacee par 373684). Sans decision_log.
# PROFILE remplace le profil Docker ; EXTRA_VAR ajoute des reglages a la variante adapt400
# (ex. EXTRA_VAR=",v294_rail_dist_decouple=250").
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
ROOT="$(pwd)"
[ -d "$ROOT/ai/AAAHogEx-115" ] || { echo "ai/AAAHogEx-115 absent de $ROOT" >&2; exit 2; }
RAIL_ONLY="mode_air=0,mode_road=0,mode_water=0"
AAA_RAIL=(--aaahogex-setting disable_veh_aircraft=1 --aaahogex-setting disable_veh_roadveh=1
          --aaahogex-setting disable_veh_tram=1 --aaahogex-setting disable_veh_ship=1)
SEEDS=(42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309)
RULE=(--decision-rule non_erosion --primary-metric profit_year --min-useful-primary-delta-pct 4
      --value-guard-max-loss-pct 5 --map-size 8 --repeats 1)

git fetch -q origin

run_one() {
  local cand="$1" branch ref var setting camp
  local -a aaa=()
  case "$cand" in
    adapt400) branch=master; setting=v294_rail_weight_adapt
              ref="OpexAI[v294_rail_weight_adapt=0]"
              var="OpexAI[v294_rail_weight_adapt=400${EXTRA_VAR:-}]" ;;
    v297)     branch=v297; setting=v297_rail_roi_floor; aaa=("${AAA_RAIL[@]}")
              ref="OpexAI[${RAIL_ONLY}]"
              var="OpexAI[${RAIL_ONLY},v297_rail_roi_floor=400]" ;;
    v296a)    branch=v296a; setting=v296_rail_batch_build
              ref="OpexAI"
              var="OpexAI[v296_rail_batch_build=1]" ;;
    finpartie) branch=finpartie; setting=v292_hq_hub
              ref="OpexAI"
              var="OpexAI[v249_statue=2,v292_hq_hub=1]" ;;
    *) echo "candidat inconnu : $cand" >&2; return 2 ;;
  esac
  camp="${cand}_porteB_20x10_pc_20261021"
  local wt="$ROOT/../porteB-${cand}"
  if [ ! -d "$wt" ]; then
    git worktree add -q --detach "$wt" "origin/${branch}"
  fi
  [ -d "$wt/ai/AAAHogEx-115" ] || cp -r "$ROOT/ai/AAAHogEx-115" "$wt/ai/"
  grep -q "name = \"${setting}\"" "$wt/ai/OpexAI/info.nut" \
    || { echo "reglage ${setting} absent de origin/${branch}" >&2; return 2; }
  grep -q "extra == null || !AIVehicle.IsValidVehicle(extra)" "$wt/ai/OpexAI/air_fleet.nut" \
    || { echo "correctif du renfort aerien absent de origin/${branch}" >&2; return 2; }
  echo "=== ${cand} : $(git -C "$wt" rev-parse --short HEAD) (${branch}) -> results/${camp} ==="
  (cd "$wt" && python3 sweeps/run_c66_reference.py --campaign "${camp}_smoke" \
     --reference "$ref" --variant "$var" --variant-policy-id "$cand" "${RULE[@]}" \
     --years 1 --seeds 42 --script-debug "${aaa[@]}" "${PC[@]}") || true
  # Seules les erreurs d'OpexAI (compagnie 0) arretent : AAAHogEx plante parfois seul (IsBiDirectional).
  if zcat -f "$wt/results/${camp}_smoke_engine/"* | grep -q "\[0\] \[S\] Your script made an error"; then
    zcat -f "$wt/results/${camp}_smoke_engine/"* | grep -A6 "\[0\] \[S\] Your script made an error" | head -20
    echo "=== ${cand} : ARRET, erreur Squirrel d'OpexAI au smoke, porte B non lancee ===" >&2
    return 0
  fi
  (cd "$wt" && python3 sweeps/run_c66_reference.py --campaign "$camp" \
     --reference "$ref" --variant "$var" --variant-policy-id "$cand" "${RULE[@]}" \
     --years 10 --seeds "${SEEDS[@]}" --script-debug "${aaa[@]}" "${PC[@]}") || echo "=== ${cand} : echec $? ==="
}

CANDS=("${1:-all}")
[ "${CANDS[0]}" = all ] && CANDS=(adapt400 v297 v296a)
for c in "${CANDS[@]}"; do run_one "$c"; done
