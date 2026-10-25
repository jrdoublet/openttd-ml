#!/usr/bin/env bash
# Banc de calibration des couts et revenus des projets (demande utilisateur du 21/10), sur le PC.
# Master aux defauts actuels, un seul bras OpexAI[probes=6], 40 graines V267 x 10 ans, 1970, 256².
# Hypothese a verifier : calibrer d'abord SANS AAAHogEx (table hors ligne), puis laisser C70 corriger
# en cours de partie. Deux campagnes sur les memes graines :
#   solo : AAAHogEx present mais sans aucun vehicule (5 disable_veh_*), carte identique ;
#   duel : AAAHogEx normal.
# Puis l'analyse (sweeps/analyse_calibration_projets.py) : cout reel/predit, revenu, exploitation et
# profit reels/predits par mode x cargo x distance x epoque, validation croisee a deux plis
# (sans correction / facteur par mode / table par cellule), table apprise en solo testee en duel,
# et part de l'erreur residuelle entre parties (ce que l'apprentissage en partie peut corriger).
# A lancer depuis la racine d'un checkout de openttd-ml a jour (master) contenant ai/AAAHogEx-115 :
#   bash sweeps/run_calibration_pc.sh [smoke|solo|duel|analyse|all]   (defaut : all)
# Environ 80 parties x 10 ans (~1 h a 10 workers) ; journaux ~10 Mo par partie dans results/.
# PROFILE remplace le profil Docker.
set -euo pipefail

read -r -a PC <<< "${PROFILE:---cpus 10 --memory 8g --max-workers 10 --network host}"
[ -d ai/AAAHogEx-115 ] || { echo "ai/AAAHogEx-115 absent de $(pwd)" >&2; exit 2; }
DATE="${DATE:-$(date +%Y%m%d)}"
ARM="OpexAI[probes=6]"
AAA_OFF=(--aaahogex-setting disable_veh_train=1 --aaahogex-setting disable_veh_roadveh=1
         --aaahogex-setting disable_veh_tram=1 --aaahogex-setting disable_veh_ship=1
         --aaahogex-setting disable_veh_aircraft=1)
# 40 graines V267 (origin/v267, evidence/review/v267_pc_20261020/v267_selection_20261019.txt).
SEEDS=(416714 795462 133887 101154 785502 858483 104234 874979 66989 657364 100323 173883 150807
       707080 709384 945977 551035 786605 150301 861251 438248 467272 306616 89252 754022 31249
       621101 952252 875622 497933 404321 283371 933000 625099 17486 697929 341090 550673 628258 659100)
SOLO="calib_solo_40x10_pc_${DATE}"
DUEL="calib_duel_40x10_pc_${DATE}"

check_errors() {  # seules les erreurs d'OpexAI (compagnie 0) comptent
  if zcat -f "results/$1_engine/"* | grep -q "\[0\] \[S\] Your script made an error"; then
    zcat -f "results/$1_engine/"* | grep -A6 "\[0\] \[S\] Your script made an error" | head -20
    echo "=== $1 : erreur Squirrel d'OpexAI ===" >&2
    return 1
  fi
}

run() {  # campagne, annees, graines..., puis options AAAHogEx eventuelles apres --
  local camp="$1" years="$2"; shift 2
  local -a seeds=() aaa=()
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do seeds+=("$1"); shift; done
  [ $# -gt 0 ] && { shift; aaa=("$@"); }
  echo "=== ${camp} : $(git rev-parse --short HEAD), ${#seeds[@]} graines x ${years} ans ==="
  python3 sweeps/run_c66_reference.py --campaign "$camp" --reference "$ARM" \
    --map-size 8 --repeats 1 --years "$years" --seeds "${seeds[@]}" --script-debug \
    "${aaa[@]}" "${PC[@]}" \
    || echo "=== ${camp} : sortie non nulle (attendue en solo : AAAHogEx sans vehicule = inactive_company) ==="
  [ -d "results/${camp}_engine" ] || { echo "=== ${camp} : aucun journal ===" >&2; return 1; }
  check_errors "$camp"
}

step() {
  case "$1" in
    smoke)
      run "calib_smoke_solo_1x1_pc_${DATE}" 1 42 -- "${AAA_OFF[@]}"
      # AAAHogEx sans vehicule ne doit rien faire rouler : verifier dans le resume.
      python3 - "results/calib_smoke_solo_1x1_pc_${DATE}.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
for s in d["summary"]:
    print(s["arm"], "vehicules", s["n_vehicles"], "profit_year", s["profit_year"])
    if s["arm"] == "AAAHogEx" and s["n_vehicles"] > 0:
        sys.exit("AAAHogEx a des vehicules : le solo n'est pas un solo")
EOF
      ;;
    solo)    run "$SOLO" 10 "${SEEDS[@]}" -- "${AAA_OFF[@]}" ;;
    duel)    run "$DUEL" 10 "${SEEDS[@]}" ;;
    analyse)
      python3 sweeps/analyse_calibration_projets.py \
        --campaign "solo=results/${SOLO}_engine" --campaign "duel=results/${DUEL}_engine" \
        --train solo --test duel --out "results/calibration_projets_${DATE}.json" \
        | tee "results/calibration_projets_${DATE}.txt" ;;
    all)     step smoke; step solo; step duel; step analyse ;;
    *) echo "etape inconnue : $1" >&2; exit 2 ;;
  esac
}

git fetch -q origin || true
step "${1:-all}"
