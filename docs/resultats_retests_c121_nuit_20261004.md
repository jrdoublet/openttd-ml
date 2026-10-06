# Retests C121 de nuit — résultats du 4 octobre 2026

**27/27 comparaisons terminées, saines, 40/40 paires chacune ; aucun passage.**
22 verdicts bruts `fail_primary`, 5 `fail_primary_and_value_guard`.
Durée : 3 h 30 min 17 s, du 03/10 23:06:56 au 04/10 02:37:13 (Paris).
56 étapes, **2 234 parties** : 27 smokes, deux diagnostics d'exposition, 27 comparaisons.
Aucune porte B, adoption ou modification de défaut.

## Protocole et portée

File `c121_nuit10_20261003_210612`, 10 CPU / 8 Go / 10 workers, un seul
conteneur et aucun swap supplémentaire. Référence fixe :
`c121_air_economics=1,c121_catalog_incremental=1`, C115 déclaré à 1 ;
autres réglages aux défauts de la copie Git isolée à `a848df8`.
La référence n'intègre aucun gagnant d'un essai précédent.

K_pass et K_dec : portes A après smoke sain et exposition positive.
Les 25 autres comparaisons sont exploratoires : statistiques `gain_short`
calculées, sans qualification automatique de l'exposition ni adoption.
24 comparaisons à trois ans ; fenêtre live, plancher marginal et hub-hub à
six ans, horizons décidés avant les parties. Une répétition, 40 graines canoniques.
Profit : variante moins référence à l'année terminale, pas profit cumulé.
Garde : ratio des moyennes de valeur, perte maximale 5 %. Bootstrap
20 000 rééchantillonnages, graine 0 ; Wilcoxon exact bilatéral.

## Résultats de chaque intervention

Les deltas et IC sont en **k£/an** ; la valeur est la variation en %.
`P` = fail_primary ; `P+V` = fail_primary_and_value_guard.
Un échec P peut refléter un gain insuffisamment démontré, pas une perte démontrée.
Les ablations 1→0 sont explicitement orientées vers la désactivation.

| Réglage (variante contre référence) | Ans | Δ profit | Δ % | IC95 bootstrap | Wilcoxon p | Δ valeur % | Brut |
|---|---:|---:|---:|---|---:|---:|---|
| [c121_kpass_air_continue 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_kpass_air_continue_A.json) | 3 | +1.69 | +0.12 | [-3.55 ; +6.84] | 0.24390 | +0.12 | P |
| [c121_kdec_cold_exempt 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_kdec_cold_exempt_A.json) | 3 | -9.13 | -0.64 | [-18.09 ; -0.29] | 0.04977 | -0.77 | P |
| [c121_air_first_live_growth 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_first_live_growth_exploration.json) | 3 | +24.39 | +1.71 | [-27.20 ; +75.60] | 0.34717 | +3.25 | P |
| [c121_air_first_live_air_priority 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_first_live_air_priority_exploration.json) | 3 | +8.32 | +0.57 | [-26.83 ; +45.06] | 0.87851 | +0.57 | P |
| [c121_air_first_observation_growth 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_first_observation_growth_exploration.json) | 3 | +27.51 | +1.92 | [-16.84 ; +71.70] | 0.27069 | +3.80 | P |
| [c121_air_observation_growth 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_observation_growth_exploration.json) | 3 | +16.32 | +1.14 | [-26.61 ; +58.98] | 0.38264 | +5.15 | P |
| [c121_territory_first 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_territory_first_exploration.json) | 3 | -5.79 | -0.41 | [-45.46 ; +32.38] | 0.83676 | -0.58 | P |
| [c121_air_initial_project_economics 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_initial_project_economics_exploration.json) | 3 | +7.33 | +0.51 | [-37.64 ; +52.90] | 0.73527 | -0.45 | P |
| [c121_air_engine_realization 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_engine_realization_exploration.json) | 3 | -33.07 | -2.31 | [-79.18 ; +15.35] | 0.13376 | -2.67 | P |
| [c121_air_project_realization 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_project_realization_exploration.json) | 3 | +2.09 | +0.15 | [-32.25 ; +35.78] | 0.78592 | +0.38 | P |
| [c121_air_project_realization_adaptive 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_project_realization_adaptive_exploration.json) | 3 | +44.26 | +3.10 | [-3.22 ; +93.86] | 0.09568 | +3.26 | P |
| [c121_catalog_air_first_year 1→0](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_catalog_air_first_year_exploration.json) | 3 | -434.31 | -30.37 | [-512.60 ; -354.56] | 0.00000 | -39.72 | P+V |
| [c121_air_first_year_rail_prep 1→0](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_first_year_rail_prep_exploration.json) | 3 | -17.22 | -1.20 | [-79.16 ; +41.36] | 0.97349 | -0.15 | P |
| [c121_air_one_or_two_planes 1→0](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_one_or_two_planes_exploration.json) | 3 | -83.20 | -5.82 | [-153.42 ; -13.33] | 0.03322 | -7.32 | P+V |
| [c121_air_first_live_growth_phase_years 0→4](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_first_live_growth_phase_years_exploration.json) | 6 | +46.25 | +3.83 | [-6.11 ; +100.81] | 0.17009 | +1.10 | P |
| [c83_preempt_open 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_c83_preempt_open_exploration.json) | 3 | -73.61 | -5.15 | [-133.26 ; -16.27] | 0.03322 | -5.19 | P+V |
| [c83_fixes 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_c83_fixes_exploration.json) | 3 | -377.94 | -26.45 | [-484.45 ; -271.27] | 0.00000 | -25.47 | P+V |
| [air_batch_town_reserve 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_batch_town_reserve_exploration.json) | 3 | -17.26 | -1.21 | [-76.16 ; +41.92] | 0.70469 | -0.60 | P |
| [c80_marginal_floor 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_c80_marginal_floor_exploration.json) | 6 | +32.00 | +2.48 | [-28.44 ; +94.04] | 0.33598 | -1.21 | P |
| [air_hubhub_marginal 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_hubhub_marginal_exploration.json) | 6 | +54.66 | +4.23 | [-1.06 ; +109.62] | 0.04816 | +0.51 | P |
| [c69_fleet_demand_batch 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_c69_fleet_demand_batch_exploration.json) | 3 | +0.02 | +0.00 | [+0.00 ; +0.06] | 1.00000 | +0.00 | P |
| [rail_depot_cost 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_rail_depot_cost_exploration.json) | 3 | -24.67 | -1.72 | [-53.17 ; +2.68] | 0.16124 | -1.27 | P |
| [road_loading_fix 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_road_loading_fix_exploration.json) | 3 | +1.46 | +0.10 | [-1.59 ; +5.34] | 0.75000 | +0.03 | P |
| [road_time_scaled_cap 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_road_time_scaled_cap_exploration.json) | 3 | -5.81 | -0.41 | [-31.08 ; +17.75] | 0.80399 | -0.49 | P |
| [road_pax_build 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_road_pax_build_exploration.json) | 3 | -60.36 | -4.22 | [-100.86 ; -22.55] | 0.01411 | -2.66 | P |
| [town_growth 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_town_growth_exploration.json) | 3 | -115.65 | -8.08 | [-190.52 ; -42.40] | 0.00610 | -8.64 | P+V |
| [policy_vehicle_events 0→1](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_policy_vehicle_events_exploration.json) | 3 | -15.20 | -1.06 | [-35.14 ; +1.29] | 0.40603 | -0.49 | P |

Pour la priorité live et la fenêtre live 0→4, `c121_air_first_live_growth=1`
est commun aux deux bras. Leur résultat est conditionnel à ce parent.

## Lecture des signaux

- **Hub-hub marginal à six ans** : +54,66 k£/an (+4,23 %), p=0,04816,
  mais borne basse bootstrap −1,06 k£/an : échec du critère IC95, pas de B.
- **Fenêtre live quatre ans** : +46,25 k£/an (+3,83 %), IC traversant zéro,
  p=0,17009 : ni seuil 4 % ni preuve statistique de gain.
- **Réalisation adaptative** : +44,26 k£/an (+3,10 %), IC traversant zéro,
  p=0,09568 : signal exploratoire, pas qualification.
- **Désactiver air-first-year** : −30,37 % de profit, −39,72 % de valeur ;
  désactiver N=1/N=2 : −5,82 % de profit, −7,32 % de valeur.
  Ces ablations défavorables soutiennent le maintien de ces réglages à 1
  dans ce profil C121 ; elles ne qualifient pas C121 face au défaut C115.
- **C83 preempt/fixes et town_growth ON** échouent aussi la garde de valeur.
  Road pax ON perd 4,22 % de profit ; la garde de valeur reste tenue.
- K_dec froid : delta −9,13 k£/an, IC95 [−18,09 ; −0,29], p=0,04977.
  Pas de réactivation ni de B. K_pass ne démontre pas de gain utile.

## Provenance et limites

Tous les 56 hashes de manifeste ont été contrôlés contre les JSON ;
santé, horizon, comparaison et couverture annuelle complets pour les 27
échantillons. Source bundle commun :
`212039023d0c7ad37b36738c87f9fc7143bc17d99ee7dad0a6701870feefff5d`.
Runtime/image conservés dans les manifestes. Requête et suivi :
[plan](../results/c121_nuit10_20261003_210612/plan.json),
[statut final](../results/c121_nuit10_20261003_210612/status.json).
Les liens du tableau pointent les JSON locaux ; bundles, JSONL et logs
homonymes sont conservés dans le même `results/` de la copie isolée.
Ces artefacts ignorés par Git ne constituent pas une archive versionnée.

La première file 3 CPU / 2 Go annulée conserve ses résultats séparés,
dont son verdict K_pass fail_primary et sa porte A K_dec interrompue.
La reprise a été explicitement demandée par l'utilisateur, sans effacer
les essais initiaux. Aucun résultat exploratoire n'est reclassé en opcodes.
Ces nombreux essais ne forment pas une confirmation indépendante d'un
signal sélectionné ; ne pas relancer un échec pour obtenir un passage.
