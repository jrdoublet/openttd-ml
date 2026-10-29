# V161 — duels AIR seul contre AAAHogEx-115 (29/10/2026)

## Protocole et provenance

Deux campagnes descriptives **OpexAI actuel contre AAAHogEx-115**, sur la même
carte par graine, une répétition, 1970 et carte 256×256 : 40 graines sur 3 ans
(1970–1972), puis les 20 graines canoniques sur 10 ans (1970–1979).
Les deux campagnes utilisent le **même bundle figé**
`b21f99c848e795395230359c9b4be6290124c053b8a1330e934a0a588f5ebd45`.
Le code testé est issu de HEAD `12e4d39f` avec des modifications non commitées
(V161 et opt-in concurrents). Le bundle est la référence source exacte de la
simulation ; un commit qui ne reprend que V161 n'est pas byte-for-byte
identique à cet arbre et ne doit pas être présenté comme tel.

Réglages **effectifs**, confirmés dans les manifestes :

| Réglage | Valeur |
|---|---:|
| `estim_unifie` (ESTIM) | **0** |
| `eb2_new_station_fallback` (EB2) | **0** |
| `air_load_min_pct` | **0** |
| `air_fleet_yield_rightsize` (P3) | **0** |
| `air_site_ranked` | **1** |
| `air_site_funnel` | **1** |
| `c121_air_project_realization_adaptive` | **1** |
| `mode_air` | **1** |
| `mode_rail`, `mode_road`, `mode_water` | **0** |
| `probes` | **2**, panneaux uniquement |

AAAHogEx : `disable_veh_train=1`, `disable_veh_roadveh=1`,
`disable_veh_tram=1`, `disable_veh_ship=1` et avions activés.
Les autres réglages sont ceux du manifeste (par défaut dans le bundle).
Le harnais est `sweeps/run_c66_reference.py` / `bench_1v1_5y_20seeds.py`,
avec 9 workers, Docker 10 CPU / 8 Gio, image `openttd-lab:latest` figée par
son SHA256 dans le manifeste ; le réseau sert uniquement à préparer les
bibliothèques avant simulation.

## Résultats `profit_year` de l'année terminale

| Mesure | 40×3 — 1972 | 20×10 — 1979 |
|---|---:|---:|
| Duels complets / invalides | 40 / 0 | 20 / 0 |
| OpexAI, profit annuel moyen | 1 976 565 £ | 2 357 764 £ |
| AAAHogEx, profit annuel moyen | 2 008 117 £ | 2 494 258 £ |
| Ratio des moyennes Opex / AAA | **98,43 %** | **94,53 %** |
| OpexAI, victoires au profit | 21/40 | 9/20 |
| Valeur de société OpexAI | 3 775 100 £ | 15 866 246 £ |
| Valeur de société AAAHogEx | 3 576 648 £ | 10 870 964 £ |
| Écart de valeur Opex / AAA | +5,55 % | **+45,95 %** |
| OpexAI, victoires en valeur | 24/40 | 18/20 |
| Véhicules moyens Opex / AAA | 52,0 / 49,5 | 80,2 / 55,5 |
| Gares moyennes Opex / AAA | 32,7 / 45,5 | 32,6 / 45,8 |

**Trajectoire du ratio des profits annuels (20 graines, mois de décembre) :**

| Année | Ratio Opex / AAA |
|---|---:|
| 1970 | 96,46 % |
| 1971 | 100,21 % |
| 1972 | 102,94 % |
| 1973 | 112,50 % |
| 1974 | 120,13 % |
| 1975 | 119,16 % |
| 1976 | 115,75 % |
| 1977 | 111,32 % |
| 1978 | 104,68 % |
| 1979 | **94,53 %** |

OpexAI est meilleur en profit de 1971 à 1978 sur cet échantillon, mais sa
croissance de profit ralentit vers 1976–1979 tandis qu'AAAHogEx continue de
progresser. La valeur de société élevée ne signifie pas que le rendement du
capital ou le profit annuel sont supérieurs. Les valeurs terminales ne prouvent
pas une amélioration due à V161 : **aucun bras historique pré-V161 n'a été testé**
sur ce bundle, et le test des signes sur le profit 1979 est non concluant.

## Preuves publiées et limites

Sous `evidence/v161_aironly_20261029/` : les JSON finaux compressés **sans
perte** (`*.json.gz`), leurs manifestes de gel, des sommes SHA256 et les
résumés ci-dessus. Les journaux JSONL mensuels, journaux OpenTTD détaillés et
bundles sources gelés demeurent dans `results/` **localement** ; ils ne sont
pas publiés parce que volumineux et, pour le bundle, il contient aussi l'IA
tierce non versionnée. Les JSON finaux contiennent les séries et données du
banc ; le manifeste contient les réglages et empreintes.

**Prochaines questions, différées à la demande utilisateur :** pourquoi
OpexAI a-t-elle environ 13 aéroports/gares de moins par carte que AAAHogEx,
combien de villes sont desservies uniquement par les aéroports AAAHogEx
(monopoles, définition de couverture à fixer), et quelles sont les bornes de
distance minimum/maximum des vols, côté catalogue, moteurs et concurrents ?
Les nombres de « gares » présentés ci-dessus ne sont **pas encore** un
inventaire vérifié d'aéroports : identifier les stations réellement aériennes
avant de compter les monopoles. Voir la tâche ouverte dans `docs/taches.md`.

Ce résultat n'est **pas** une porte de qualification V102 de V161 : il faut
comparer une source pré-V161 isolée et la variante V161 sur un protocole 40×3
`gain_short`, puis éventuellement 20×10 `non_erosion`, pour un gain causal.
