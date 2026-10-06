# Ordre proposé des retests V102 — 3 octobre 2026

**Périmètre corrigé par l'utilisateur : C121 uniquement. Premier banc autorisé :
`c83_local_repair=0→1` sous C121 + catalogue incrémental.** Les comparaisons D
du plan initial ci-dessous sont retirées de la file de lancement. Les autres
candidats restent proposés ; cette demande déclenche seulement le premier banc.

**Premier banc terminé : C83 local, porte A `fail_primary`, 40/40 paires
saines.** Aucun gain établi ; porte B non lancée, défaut 0 conservé.
[Résultat et limites](journaux/journal_2026-10-03.md#retests-v102--premier-banc-c121--réparation-locale-c83).

**Autorisation suivante : file de nuit sous C121, lancée à 22:45 Paris, plafond
8 heures (04/10 06:45 Paris).** 27 comparaisons indépendantes ; K_pass / K_dec
avec exposition puis A, 25 autres comparaisons exploratoires. Pas de qualification
automatique pour les explorations ; règles, horizons, arrêts et bras exacts dans
[le pré-enregistrement de nuit](journaux/journal_2026-10-03.md#file-c121-pour-la-nuit).
Cette décision remplace l'attente de lancement de la proposition initiale.

**Reprise demandée ensuite : 10 CPU / 8 Go / 10 workers sur Docker local.**
La file initiale est annulée en conservant ses preuves ; nouvelle file
`c121_nuit10_20261003_210612`, même ordre, départ au premier smoke, nouveau plafond huit heures.
[Annulation et ressources](journaux/journal_2026-10-03.md#annulation-et-reprise-à-10-cpu--8-go).

**File terminée le 04/10 à 02:37 Paris, en 3 h 30** : 27/27 comparaisons
saines et complètes, aucun passage, aucune B/adoption.
[Résultats et limites de chaque essai](resultats_retests_c121_nuit_20261004.md).

Demande : préparer un gros banc pour retenter les paramètres avec les nouvelles règles,
et fournir l'ordre le plus pertinent. Inventaire : **190 réglages déclarés** dans
`ai/OpexAI/info.nut`, sur `c121-catalog` à `a848df8`, avec documentation locale modifiée.
Ce plan couvre chaque réglage ; il ne propose pas le produit cartésien de toutes ses valeurs.
Il ne lève pas les protections et arrêts spécifiques des chantiers.

## Références fixes avant la série

- **D** : défaut livré, `c115_air_c100_capital_replay=1`,
  `c121_air_economics=0`, `c121_catalog_incremental=0`.
- **C** : profil de recherche C121, mêmes autres défauts, avec
  `c121_air_economics=1,c121_catalog_incremental=1`. Sur cet arbre,
  `c121_flat_bootstrap`, `c121_catalog_air_first_year`,
  `c121_air_first_year_rail_prep`, `c121_air_one_or_two_planes`,
  `c121_air_game_engine` et `c121_air_winner_fusion` valent déjà 1.
  C115 reste déclaré à 1 ; C121 prend la main sur son chemin économique.

**C n'est pas le défaut courant.** Un gain dans C ne qualifie ni C121 contre D,
ni le même paramètre au défaut. Comparer les variantes à leur référence fixe,
sans ajouter les gagnants précédents au fil des essais. Figer sources, adversaire,
image et réglages effectifs ; ne pas mélanger les anciennes bases C121 avec C.

Le cadrage des références comprend deux comparaisons distinctes :
D avec `c121_air_economics=0→1`, puis sous C121 `c121_catalog_incremental=0→1`.
Ces interrupteurs activent aussi des sous-fonctions déjà à 1 : ils mesurent un
**ensemble effectif**, pas chacun de ses composants. Ces comparaisons de modèles
ne sont pas un motif de changer C115 ni un préalable obligeant à abandonner toute
recherche conditionnelle dans C. Pour les modèles AIR historiques, vérifier
les priorités de branches : un drapeau masqué par C115/C121 n'est pas un vrai bras.

## Ordre recommandé

Les paramètres d'une ligne sont testés **séparément, dans l'ordre écrit**.
Pour un booléen expérimental à 0 : référence 0, variante 1. Pour une ablation
d'un réglage adopté : référence 1, variante 0 ; le delta garde cette orientation.
Aucun réglage de sonde ne devient implicitement un candidat économique.

| Ordre | Paramètres / famille | Profil et justification |
|---|---|---|
| **1** | `c83_local_repair` | **D puis C**, résultats séparés. Meilleur dossier à requalifier : ancien 20×10 à +64,4 k£/an et valeur +5,40 %, rejet par l'ancienne porte statistique. Les opcodes C83 observés ne sont pas une preuve à entrées appariées ; retenir ici le protocole comportemental. |
| **2** | `c121_kpass_air_continue` | **C**. Blocage réel exposé, ancien 5×6 à +42,2 k£/an Opex ; écart à AAA défavorable, à conserver comme secondaire. |
| **3** | `c121_kdec_cold_exempt` | **C**. Exposition déjà établie, ancien 20×10 à +22,4 k£/an, effet indécis. Bon candidat pour distinguer effet d'amorçage et dilution tardive. |
| **4** | `c72_plane_choice=1`, puis `=2` contre `=0` | **D**. Anciennes moyennes proches de zéro (−1,9/−4,5 k£/an dans le bilan C84) ; moins dissuasif qu'une perte nette. Vérifier que le chooser testé est effectivement utilisé avec C115. |
| **5** | `c121_air_first_live_growth` → `c121_air_first_live_air_priority` | **C**. Live 1→2 : effet précoce documenté, érosion ensuite. Le second essai exige live=1 **dans les deux bras**, puis priorité 0→1 ; résultat conditionnel, pas qualification de live. |
| **6** | `c121_air_first_observation_growth` → `c121_air_observation_growth` | **C**, deux variantes alternatives de cadence, sans les empiler. Séparer premier renfort et renforts successifs ; vérifier l'exposition avec l'ouverture N=1/N=2 déjà active. |
| **7** | `c80_marginal_floor` → `air_hubhub_marginal` → `c69_fleet_demand_batch` → `rail_depot_cost` | **D puis transfert conditionnel vers C**, sauf levier masqué. Arbitrage marginal et coûts réels avant nouveau volume ; les anciens résultats ne promettent pas un gain. Horizon A6 pour les effets matures. |
| **8** | `air_batch_town_reserve` → `c83_preempt_open` → `c83_fixes` → `c122_air_threat_retry` → `c120_air_territorial_ranking` → `c118_air_territorial_expansion` → `c121_territory_first` | Concurrence et occupation, du changement local au changement de politique. D pour les options génériques, C pour celles dépendant de C121. Exposition des refus/réparations obligatoire ; C118/C120 ne sont pas des bonus gratuits au même modèle. |
| **9** | `road_loading_fix` → `road_time_scaled_cap` → `road_pax_build` → `town_growth` et ses auxiliaires → `policy_vehicle_events` | **D**, puis C si résultat justifiant ce transfert. Garder les effets sur la demande aéroportuaire. `town_growth=1` est comparé à OFF ; memo/skip/ROI ne sont testables qu'avec croissance active dans les deux bras. Le ciblage des monopoles n'est pas un réglage livré ici. |
| **10** | `c85_air_equipment_frontier` → `exp_scheduler_skip_not_due` → `exp_air_hub_pair_prefilter` → `c76_lean_invalidation` → `c76_freight_rotation` → `c80_air_choice_memo` → `c80_air_eval_fast` → `homogeneous_preselect` | Coût du catalogue et planification. Définir **avant** les mesures la catégorie de chaque essai : optimisation d'opcodes mesurable ou comportement. Une option de rotation/préselection n'obtient pas une dispense de gain du seul fait de son nom. Contrôler cache, invalidation et Save/Load. |
| **11** | Fenêtres de croissance AIR → `v88_goods_chain` puis auxiliaires → `rail_expand` → workers rail/ville et stock A* → `rail_upgrade_failure_memory` | **A6**, profils exposant réellement le mécanisme. V88 de base précède les cinq auxiliaires ; stock gate précède stock worker. Très conditionnel : les diagnostics rail du 03/10 réfutent une simple réallocation du créneau. Le nouveau test ne corrige pas ce mécanisme. |
| **12** | Modèles/calibrations AIR : C82/C110/C119, corrections de réalisation C121, économie du projet initial, puis C99–C114 et C116 | Comparaisons exclusives, après vérification des chemins prioritaires. C111/C113 contiennent « shadow » mais changent financement/construction : **pas des sondes passives**. Sources de preuves C116 incomplètes ; contrôler techniquement avant économie. |
| **13** | Anciens rejets forts : suppression réaction C83, watcher quotidien, préflight/déduplication/reselect AIR, contexte moteur C121, profondeurs statiques C121, stock-growth/AAA-line, C122, V93, V92/C84, plafonds rail, full-load | **Tout à la fin, sous conditions de reprise de chaque chantier.** Une règle plus puissante peut confirmer une perte. Le préflight a déjà un IC95 entièrement négatif ; le contexte moteur augmente les opcodes. C85 précède C84. Pas de restauration de code abandonné, ni de 20×10 interdit déclenché par ce plan. |
| **14** | Contrôles des réglages déjà adoptés ; ensuite paramètres numériques | Ablations ciblées 1→0, puis une valeur alternative pré-enregistrée par paramètre, avant toute grille. Les adoptions ne changent pas pendant les mesures. `c121_flat_bootstrap` a déjà passé V102 : témoin utile, répétition individuelle de faible priorité. C70 fonctionne selon V99 ; ne pas le remettre en tête. |
| **15** | Combinaison des gagnants | Seulement après lecture de toutes les portes individuelles retenues : combinaison limitée, puis ablation des composants et nouvelle comparaison contre D ou C initial. Le cumul n'hérite pas des verdicts individuels. |

Les classements sont un **jugement de priorité**, fondé sur les dossiers existants,
pas de nouvelles mesures. En particulier, davantage d'aéroports, de trains ou un meilleur
gap AAA n'assurent pas un meilleur profit Opex.

## Horizons, dépendances et coût

- **A3 ordinaire** : 40 graines × 3 ans, Wilcoxon exact bilatéral p<0,05,
  borne basse IC95 bootstrap >0, delta moyen ≥4 % de la moyenne de référence terminale,
  garde de valeur −5 %. Puis **B : 20×10**, borne haute IC95 bootstrap ≥0 et garde −5 %.
- **A6 pré-enregistrée** pour les effets tardifs : mêmes 40 graines et critères,
  mais `--required-years 6 --years 6`. Proposition à inscrire au plan définitif
  **avant** toute partie, pas passage à six ans parce que trois ans a échoué.
  Exemple : live=1 commun et `c121_air_first_live_growth_phase_years=0→4`
  ne diffèrent qu'après quatre ans. Un 40×3 serait structurellement incapable
  de tester cette différence. Même vigilance sur cargos transformés/renforts matures.
- **Opcodes** : mesurer d'abord un gain net sur le poste visé à travail comparable,
  puis appliquer la règle de neutralité distincte d'AGENTS §4. Ne pas transformer
  tous les essais du lot 10 en essais opcodes pour éviter la porte A.
- **Dépendances** : ne tester les sous-options V88 qu'avec `v88_goods_chain=1`,
  les sous-options de croissance qu'avec leur parent actif, les sous-options
  town-growth qu'avec `town_growth=1`. `c80_rail_stock_worker` exige le gate et
  désactive V89 ; `c121_aaa_line` force le full-load. Rapporter ces effets effectifs.
- **Pas de référence mobile** : isoler chaque option, sauf comparaison de famille
  annoncée comme telle. Les sous-options conditionnelles ne deviennent pas des
  qualifications au défaut. Les réglages numériques restent à choisir précisément
  avant exécution ; ce livrable est un ordre, pas un manifeste exécutable.
- **Volume par comparaison comportementale** : 2 parties smoke + 80 porte A,
  puis 40 porte B uniquement si A passe. Donc **82 à 122 parties**.
  Un premier budget de **12 comparaisons** représente **984 parties avant B**,
  au plus **1 464** si les douze passent. À trois ans : 2 904 années-parties avant B,
  au plus 7 704 avec toutes les B ; chaque A6 ajoute 240 années-parties.
  Les essais D et C d'un même drapeau comptent comme **deux comparaisons**.
  Aucun temps mural promis à partir des anciennes campagnes.
- **Premier lot concret de 12 comparaisons** : C83 local/D, C83 local/C,
  K_pass/C, K_dec froid/C, C72=1/D, C72=2/D, live/C, priorité sous live/C,
  première observation/C, observation annuelle/C, plancher marginal/D,
  hub-hub marginal/C. Vérifier exposition et arrêts de chantier avant de figer
  leurs plans. Les deux derniers sont proposés à A6. Ce lot est une proposition,
  pas une autorisation de lancer 1 464 parties.
- Les nombreux essais augmentent le risque de retenir un résultat favorable par
  hasard. Publier tous les résultats, y compris les échecs, ne pas relancer jusqu'au
  passage. Pour la combinaison finale sélectionnée, pré-enregistrer une confirmation
  sur des graines distinctes de la série de sélection ; conserver les verdicts
  individuels V102 sans prétendre à une correction globale de multiplicité.
- Une seule campagne Docker à la fois, 3 CPU/2 Go/sans swap, au plus trois workers.
  Le lanceur hôte expose V102 ; les workflows GitHub ne sont pas encore migrés.
  **Aucune commande de lancement ni automatisation n'est créée par ce document.**

## Hors série économique automatique

Les sondes et contrôles servent à mesurer ; leur ON/OFF n'est pas un nouveau modèle
économique. Conserver les protections de C115 et du plancher défensif, les politiques
composites et les invariants de sauvegarde. Ne pas tester des paramètres sans consommateur :
`c80_double_register`, les deux options V95 inactives, `c102_air_station_rating_probe`.
C67 n'a pas de consommateur économique livré : ce serait un chantier d'intégration.

`v107_densify_portfolio` a **déjà échoué sous V102 40×3** : pas de nouvelle tentative
identique justifiée par le changement de règle. Une hypothèse tardive différente
devrait être pré-enregistrée séparément. Les pistes AIR 3a/3b, cache de hubs,
publication incrémentale et alternative N=1 non finançable restent des développements
à faire ; elles ne sont pas des paramètres déjà disponibles à retester.

## Sources et limites de préparation

- [Consignes de validation](../AGENTS.md#4-validation-proportionnée-puis-adoption),
  [état courant et décisions](taches.md), notamment V99–V112.
- [C83 local](c83_local_repair_20261002.md),
  [K_dec froid](c121_kdec_cold_20261002.md),
  [cadence AIR](c121_air_cadence_live_20261002.md),
  [C84](24_c84_air_target_fleet.md), [C85](25_c85_air_equipment_frontier.md).
- [Déclarations](../ai/OpexAI/info.nut), [chargement/dépendances](../ai/OpexAI/settings.nut).

Lecture documentaire et des réglages seulement : les anciens bundles n'ont pas été
réanalysés, les profits cités restent ceux des bilans. Avant exécution, confirmer
chaque chemin effectif, les fixtures techniques et la preuve d'exposition ; aucune
équivalence entre versions du code n'est supposée.

## Inventaire exhaustif — rattachement à l'ordre ci-dessus

Valeurs **déclarées** (`custom_value`), pas preuve que le chemin soit actif.
Les lignes H ne représentent pas des bancs économiques prévus. Les valeurs
numériques alternatives et toute levée de condition sont à définir dans le plan
d'exécution ultérieur. Les numéros correspondent aux familles, et non au nombre
de parties ; voir l'ordre détaillé pour les priorités à l'intérieur des familles.

| Réglage | Défaut déclaré | Famille |
|---|---:|---|
| `debug_signs` | 1 | H — Invariants et politiques composites |
| `decision_log` | 0 | H — Invariants et politiques composites |
| `save_full_state` | 1 | H — Invariants et politiques composites |
| `pathfinder_sleep_ticks` | 0 | H — Invariants et politiques composites |
| `probe_cost` | 0 | H — Instrumentation |
| `probe_scheduler` | 0 | H — Instrumentation |
| `probe_loop_ops` | 0 | H — Instrumentation |
| `probe_span_trace` | 0 | H — Instrumentation |
| `probe_c121_engine_table` | 0 | H — Instrumentation |
| `exp_opcode_exact` | 1 | 14 — Contrôles des adoptions |
| `exp_opcode_exact_check` | 0 | H — Instrumentation |
| `catalog_cost_probe` | 0 | H — Instrumentation |
| `fleet_amort_shadow_probe` | 0 | H — Instrumentation |
| `r19_fault_inject` | 0 | H — Invariants et politiques composites |
| `probe_candidates_road` | 0 | H — Instrumentation |
| `probe_candidates_rail` | 0 | H — Instrumentation |
| `probe_catalogue` | 0 | H — Instrumentation |
| `probe_rail_search` | 0 | H — Instrumentation |
| `probe_vehicle_lost` | 0 | H — Instrumentation |
| `probe_portfolio` | 0 | H — Instrumentation |
| `c69_fleet_demand_batch` | 0 | 7 — Arbitrage marginal |
| `c69_decision_bottleneck` | 1 | 14 — Contrôles des adoptions |
| `c69_fleet_exempt` | 1 | 14 — Contrôles des adoptions |
| `c70_mode_calibration` | 1 | 14 — Contrôles des adoptions |
| `c72_plane_choice` | 0 | 1–4 — Priorités |
| `c84_air_target_fleet` | 0 | 13 — Réfutations fortes, dernier recours |
| `c85_air_equipment_frontier` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `c83_slot_reaction` | 1 | 13 — Réfutations fortes, dernier recours |
| `c83_local_repair` | 0 | 1–4 — Priorités |
| `c83_fixes` | 0 | 8 — Occupation et concurrence |
| `exp_c83_watch_daily` | 0 | 13 — Réfutations fortes, dernier recours |
| `exp_scheduler_skip_not_due` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `exp_air_hub_pair_prefilter` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `c83_preempt_open` | 0 | 8 — Occupation et concurrence |
| `air_batch_town_reserve` | 0 | 8 — Occupation et concurrence |
| `v92_air_service_choice` | 0 | 13 — Réfutations fortes, dernier recours |
| `v93_airport_no_pop_floor` | 0 | 13 — Réfutations fortes, dernier recours |
| `v93_air_demand_production` | 0 | 13 — Réfutations fortes, dernier recours |
| `v95_air_post73_probe` | 0 | H — Instrumentation |
| `v95_air_targeted_second` | 0 | H — Inertes/protégés ou sans consommateur métier |
| `v95_air_post73_targeted` | 0 | H — Inertes/protégés ou sans consommateur métier |
| `c96_air_site_catchment` | 1 | 14 — Contrôles des adoptions |
| `c97_air_c69_engine_probe` | 0 | H — Instrumentation |
| `c98_air_realized_probe` | 0 | H — Instrumentation |
| `c99_air_speed_api_fix` | 0 | 12 — Modèles AIR alternatifs |
| `c100_air_trip_physical` | 0 | 12 — Modèles AIR alternatifs |
| `c101_air_physical_engine_choice` | 0 | 12 — Modèles AIR alternatifs |
| `c103_air_c100_rank_replay` | 0 | 12 — Modèles AIR alternatifs |
| `c104_air_c100_compare_probe` | 0 | H — Instrumentation |
| `c105_air_replay_choice_physical_economics` | 0 | 12 — Modèles AIR alternatifs |
| `c106_air_marginal_physical_engine_choice` | 0 | 12 — Modèles AIR alternatifs |
| `c108_air_onestep_physical_economics` | 0 | 12 — Modèles AIR alternatifs |
| `c109_air_speed_elasticity_physical` | 0 | 12 — Modèles AIR alternatifs |
| `c110_air_engine_calibration_choice_only` | 0 | 12 — Modèles AIR alternatifs |
| `c111_air_c100_decision_shadow` | 0 | 12 — Modèles AIR alternatifs |
| `c112_air_speed_elasticity_e75_physical` | 0 | 12 — Modèles AIR alternatifs |
| `c113_air_c100_full_decision_shadow` | 0 | 12 — Modèles AIR alternatifs |
| `c114_air_c100_full_replay` | 0 | 12 — Modèles AIR alternatifs |
| `c115_air_c100_capital_replay` | 1 | H — Inertes/protégés ou sans consommateur métier |
| `c116_air_marginal_capital` | 0 | 12 — Modèles AIR alternatifs |
| `c116_air_project_probe` | 0 | H — Instrumentation |
| `c117_air_throughput_probe` | 0 | H — Instrumentation |
| `c119_air_income_model` | 0 | 12 — Modèles AIR alternatifs |
| `c118_air_territorial_expansion` | 0 | 8 — Occupation et concurrence |
| `c118_air_coverage_probe` | 0 | H — Instrumentation |
| `c120_air_territorial_ranking` | 0 | 8 — Occupation et concurrence |
| `c121_air_economics_shadow` | 0 | H — Instrumentation |
| `c121_air_economics` | 0 | 0 — Références |
| `c121_air_winner_fusion` | 1 | 14 — Contrôles des adoptions |
| `c121_air_engine_context` | 0 | 13 — Réfutations fortes, dernier recours |
| `c121_air_game_engine` | 1 | 14 — Contrôles des adoptions |
| `c121_air_decision_depth_economics` | 0 | 13 — Réfutations fortes, dernier recours |
| `c121_air_portfolio_depth_economics` | 0 | 13 — Réfutations fortes, dernier recours |
| `c121_air_portfolio_split_economics` | 0 | 13 — Réfutations fortes, dernier recours |
| `c121_catalog_incremental` | 0 | 0 — Références |
| `c121_catalog_air_first_year` | 1 | 14 — Contrôles des adoptions |
| `c121_flat_bootstrap` | 1 | 14 — Contrôles des adoptions |
| `c121_air_first_year_rail_prep` | 1 | 14 — Contrôles des adoptions |
| `c121_air_one_or_two_planes` | 1 | 14 — Contrôles des adoptions |
| `c121_aaa_line` | 0 | 13 — Réfutations fortes, dernier recours |
| `c121_territory_first` | 0 | 8 — Occupation et concurrence |
| `c121_fleet_stock_growth` | 0 | 13 — Réfutations fortes, dernier recours |
| `c121_air_observation_growth` | 0 | 5–6 — Croissance AIR précoce |
| `c121_air_first_observation_growth` | 0 | 5–6 — Croissance AIR précoce |
| `c121_air_first_growth_min_days` | 0 | 14 — Réglages numériques |
| `c121_air_first_growth_phase_years` | 0 | 11 — Effets tardifs et fret |
| `c121_air_first_growth_late_days` | 0 | 11 — Effets tardifs et fret |
| `c121_air_first_growth_min_wait_pct` | 0 | 14 — Réglages numériques |
| `c121_air_first_live_shadow` | 0 | H — Instrumentation |
| `c121_air_first_live_growth` | 0 | 5–6 — Croissance AIR précoce |
| `c121_air_first_live_growth_phase_years` | 0 | 11 — Effets tardifs et fret |
| `c121_air_first_live_air_priority` | 0 | 5–6 — Croissance AIR précoce |
| `c121_kpass_shadow` | 0 | H — Instrumentation |
| `c121_kpass_air_continue` | 0 | 1–4 — Priorités |
| `c121_kdec_cold_shadow` | 0 | H — Instrumentation |
| `c121_kdec_cold_exempt` | 0 | 1–4 — Priorités |
| `c121_air_engine_realization` | 0 | 12 — Modèles AIR alternatifs |
| `c121_air_project_realization` | 0 | 12 — Modèles AIR alternatifs |
| `c121_air_project_realization_adaptive` | 0 | 12 — Modèles AIR alternatifs |
| `c121_air_pressure_probe` | 0 | H — Instrumentation |
| `c121_air_defensive_floor` | 0 | H — Inertes/protégés ou sans consommateur métier |
| `c121_air_initial_project_economics` | 0 | 12 — Modèles AIR alternatifs |
| `c121_air_engine_replay_shadow` | 0 | H — Instrumentation |
| `c122_air_regime_priority` | 0 | 13 — Réfutations fortes, dernier recours |
| `c122_air_regime_shadow` | 0 | H — Instrumentation |
| `c122_air_threat_probe` | 0 | H — Instrumentation |
| `c122_air_threat_retry` | 0 | 8 — Occupation et concurrence |
| `c102_air_station_rating_probe` | 0 | H — Inertes/protégés ou sans consommateur métier |
| `v88_goods_chain` | 0 | 11 — Effets tardifs et fret |
| `v88_chain_force` | 0 | H — Invariants et politiques composites |
| `v88_step2_plan_immediate` | 0 | 11 — Effets tardifs et fret |
| `v88_all_inputs` | 0 | 11 — Effets tardifs et fret |
| `v88_chain_step1_finance` | 0 | 11 — Effets tardifs et fret |
| `v88_step2_rail_prio` | 0 | 11 — Effets tardifs et fret |
| `v88_step2_cash_reserve` | 0 | 11 — Effets tardifs et fret |
| `air_full_load` | 0 | 13 — Réfutations fortes, dernier recours |
| `c82_engine_calibration` | 0 | 12 — Modèles AIR alternatifs |
| `c75_multi_build` | 1 | 14 — Contrôles des adoptions |
| `c75_kpass_bypass` | 1 | 14 — Contrôles des adoptions |
| `probe_events` | 0 | H — Instrumentation |
| `b9_air_catchment_probe` | 0 | H — Instrumentation |
| `b9_air_demand_shadow` | 0 | H — Instrumentation |
| `policy_caches` | 1 | H — Invariants et politiques composites |
| `air_route_plane_selection` | 1 | 14 — Contrôles des adoptions |
| `policy_rail` | 1 | H — Invariants et politiques composites |
| `policy_road` | 1 | H — Invariants et politiques composites |
| `policy_air` | 1 | H — Invariants et politiques composites |
| `policy_abandon` | 1 | H — Invariants et politiques composites |
| `policy_portfolio` | 1 | H — Invariants et politiques composites |
| `policy_vehicle_events` | 0 | 9 — Route et villes |
| `loan_repay_floor_k` | 300 | 14 — Réglages numériques |
| `pathfinder_hard_cap_k` | 10 | 13 — Réfutations fortes, dernier recours |
| `rail_search_day_cap` | 0 | 13 — Réfutations fortes, dernier recours |
| `rail_upgrade_failure_memory` | 0 | 11 — Effets tardifs et fret |
| `probe_rail_terrain` | 0 | H — Instrumentation |
| `abandon_cooldown_days` | 365 | 14 — Réglages numériques |
| `rail_terrain_factor` | 100 | 14 — Réglages numériques |
| `rail_finance_bias_pct` | 100 | 14 — Réglages numériques |
| `rail_depot_cost` | 0 | 7 — Arbitrage marginal |
| `project_top_k` | 64 | 14 — Réglages numériques |
| `project_top_k_dynamic` | 0 | 14 — Réglages numériques |
| `road_pax_build` | 0 | 9 — Route et villes |
| `road_loading_fix` | 0 | 9 — Route et villes |
| `road_pax_catchment_pct` | 86 | 14 — Réglages numériques |
| `road_stop_catchment_houses` | 10 | 14 — Réglages numériques |
| `road_pax_dwell_days` | 6 | 14 — Réglages numériques |
| `air_early_slot` | 1 | 14 — Contrôles des adoptions |
| `air_early_slot_target_towns` | 6 | 14 — Réglages numériques |
| `air_early_slot_min_pop` | 1000 | 14 — Réglages numériques |
| `air_early_slot_bonus_pct` | 50 | 14 — Réglages numériques |
| `air_fleet_cadence_days` | 7 | 14 — Réglages numériques |
| `air_fleet_cooldown_prefilter` | 1 | 14 — Contrôles des adoptions |
| `air_joined_stop_limit` | 2 | 14 — Réglages numériques |
| `air_pax_revenue_calibration_pct` | 104 | 14 — Réglages numériques |
| `town_growth` | 0 | 9 — Route et villes |
| `town_growth_plan_memo` | 1 | 14 — Contrôles des adoptions |
| `town_growth_skip_noop` | 0 | 9 — Route et villes |
| `town_growth_roi_gate` | 1 | 9 — Route et villes |
| `rail_expand` | 0 | 11 — Effets tardifs et fret |
| `road_time_scaled_cap` | 0 | 9 — Route et villes |
| `c80_double_register` | 0 | H — Inertes/protégés ou sans consommateur métier |
| `c80_worker_rail` | 0 | 11 — Effets tardifs et fret |
| `c80_rail_stock_gate` | 0 | 11 — Effets tardifs et fret |
| `c80_rail_stock_worker` | 0 | 11 — Effets tardifs et fret |
| `c80_worker_town` | 0 | 11 — Effets tardifs et fret |
| `c76_regen_targeted` | 1 | 14 — Contrôles des adoptions |
| `c76_lean_invalidation` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `c76_freight_rotation` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `c67_water_exposure_probe` | 0 | H — Instrumentation |
| `c67_terrain_map` | 0 | H — Inertes/protégés ou sans consommateur métier |
| `c80_mode_regen` | 1 | 14 — Contrôles des adoptions |
| `c80_air_choice_memo` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `c80_air_hub_index` | 1 | 14 — Contrôles des adoptions |
| `c80_marginal_floor` | 0 | 7 — Arbitrage marginal |
| `c80_air_eval_fast` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `air_hubhub_marginal` | 0 | 7 — Arbitrage marginal |
| `air_hub_max_routes` | 0 | 14 — Réglages numériques |
| `v89_rail_search_throughput` | 1 | 14 — Contrôles des adoptions |
| `unprofitable_streak_threshold` | 3 | 14 — Réglages numériques |
| `v90_fast_pathfinder` | 1 | 14 — Contrôles des adoptions |
| `v90_pathfinder_check` | 0 | H — Instrumentation |
| `v91_astar_weight_pct` | 120 | 14 — Réglages numériques |
| `v94_air_site_list` | 1 | 14 — Contrôles des adoptions |
| `v94_air_site_check` | 0 | H — Instrumentation |
| `homogeneous_preselect` | 0 | 10 — Catalogue/coût, catégorie à fixer |
| `air_efficiency_batch` | 0 | 13 — Réfutations fortes, dernier recours |
| `air_efficiency_preflight` | 0 | 13 — Réfutations fortes, dernier recours |
| `air_efficiency_dedupe` | 0 | 13 — Réfutations fortes, dernier recours |
| `air_efficiency_reselect` | 0 | 13 — Réfutations fortes, dernier recours |
| `v107_densify_portfolio` | 0 | H — Déjà mesuré sous V102 |
