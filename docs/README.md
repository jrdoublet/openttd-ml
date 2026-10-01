# Documentation — index et statut des documents

**Réconcilié le 30 septembre 2026 ; lecture documentaire, pas nouvelle validation.**

## Commencer ici

| Document courant | Rôle |
|---|---|
| [Tâches](taches.md) | **Seule file de travail** : à valider, à implémenter, conditionnel, interdit de relance |
| [AGENTS.md](../AGENTS.md) | Invariants, environnement, mesure et protocole de qualification ; prime sur les anciens exemples |
| [Architecture courante](architecture_courante.md) | Carte de lecture du code et ordre de chargement |
| [Bancs GitHub](bancs_github.md) | Parcours opérationnel ; publication et accès requis |
| [Qualification enchaînée](../qualifications/README.md) | Plan pré-enregistré, portes et limites de `qualify.yml` ; intégration à valider |
| [Journaux](journaux/README.md) | Chronologie, décisions et résultats ; pas un second backlog |
| [Synthèse des décisions](journaux/synthese_decisions_2026-09-30.md) | Défauts adoptés, exceptions et rejets, avec sources |
| [Preuves](../evidence/review/README.md) | Audit, archives et limites de couverture |
| [Archives](archives/README.md) | Sources anciennes/corrompues, propositions non intégrées |

Instructions complémentaires : [Claude dépôt](../CLAUDE.md),
[Copilot](../.github/copilot-instructions.md), [contexte OpexAI](../ai/OpexAI/CLAUDE.md).
Elles renvoient aux mêmes autorités ; aucune liste de priorités propre à un agent.

## Comment lire le reste du corpus

Les documents ci-dessous sont des **références de conception, fiches de chantier ou
comptes rendus datés**, pas des consignes de lancement. Une fiche peut conserver
un protocole initial puis son rejet : le statut présent est celui de `taches.md`
et de la synthèse des décisions. Les numéros C/V ne sont pas des versions du logiciel.
Ne pas lire un ancien « défaut », « prochain banc » ou « à faire » au présent.
Les lignes de code citées se rapportent à l'arbre étudié, pas nécessairement au code local.

Les résultats antérieurs au 9 septembre ne font plus preuve actuelle. Les résultats
plus récents restent soumis à provenance, santé et protocole ; C116/C117/C122
ont des sources manquantes explicitement signalées. Aucun chiffre n'a été inventé
pour compléter une archive. Les HTML/CSV et bundles sont des artefacts, pas des guides.

## Fiches économie, cadence et exploitation

| Fiche | Portée / lecture actuelle |
|---|---|
| [00 Conseils](00_conseils.md), [01 eau](01_opex_builder_water_review.md) | Suggestions anciennes à confronter au code, pas findings actuels |
| [02 Empreinte](02_empreinte.md), [03 candidats PAX](03_decoupage_pax_candidates.md) | Raisonnements et échanges de conception historiques |
| [04 rail](04_arbitrage_rail_search.md), [05 cadence](05_cadence_projects_rail_search.md) | Diagnostics C41/C39 ; ne pas restaurer leurs anciens réglages |
| [06 dénominateur](06_denominateur_variable.md), [11 goulot C69](11_goulot_decision.md) | Chronologie de la finance ; modèle courant à vérifier dans le code |
| [07 early slot](07_air_early_slot_causal_analysis.md) | Mécanisme historique adopté, pas nouveau banc dû |
| [08 marchés](08_opex_vs_aaahogex_same_markets.md), [09 service](09_air_service_quality.md), [10 fréquence](10_air_frequency_variant.md) | Mesures AIR datées ; pas résultats du défaut local |
| [12 calibration](12_calibration_par_mode.md) | C70 ; distinguer profit estimé et déjà observé (R2 local) |
| [13 banc PC](13_banc_c69_20x10_pc.md), [14 suites C69](14_suites_c69.md) | Protocoles historiques ; limites VPS et workflow courant priment |
| [15 avion](15_choix_avion.md), [16 volume](16_bilan_volume.md) | Décisions/mesures historiques C68–C75 |
| [17 événements](17_evenements_regeneration.md), [18 ordonnanceur](18_orchestrateur_double_registre.md) | Contrats et implémentations successives C76/C77/C80 ; reliquat dans tâches |
| [19 rechargement](19_rechargement_partie.md) | Diagnostic de persistance ; R5/R20 locaux ont leur propre validation restante |
| [21 cartographie](21_cartographie_opportuniste.md), [contrat C67](c67_cartographie_contrat.md) | C67.3–.6 livrés, pas de consommateur économique adopté |
| [22 occasions AAA](22_c78_lignes_vs_aaa.md) | C78 et C83.1 retenus ; variantes C83 séparées/non adoptées |
| [24 flotte C84](24_c84_air_target_fleet.md), [25 frontière C85](25_c85_air_equipment_frontier.md) | Non adoptées ; C85 avant C84 sous conditions |
| [26 bus C87](26_c87_bus_et_lignes_aaa.md) | Garde de rentabilité retenue ; télémétrie historique |
| [27 V88 goods](27_v88_chaines_biens.md) | Suspendu jusqu'aux workers A*, aucun duel automatique |
| [28 V89](28_v89_debit_recherche_rail.md), [29 V90](29_v90_pathfinder_rail.md), [30 V91](30_v91_astar_pondere.md) | Défauts V89=1, V90=1, poids V91=120 ; décisions et limites dans synthèse |
| [30 V94 sites](30_v94_air_site_list.md) | Préfiltre retenu, distinct du poids A* V91 |
| [31 V92](31_v92_choix_service_air.md), [32 V93](32_v93_petits_aeroports.md) | Formulations rejetées, pas de réactivation générale |
| [33 caisse](33_caisse_1970_1972_et_leviers_aaa.md) | C75 bis adopté, finance rail 100 ; MAIL-only non implémenté |
| [34 arbitrage](34_arbitrage_economique_unifie.md) | Cible conceptuelle, pas architecture entièrement livrée |
| [35 V95 AIR](35_v95_air_post1973.md) | Diagnostic terminé ; distinct de V95 scheduler P1/P2/P5 |
| [36 workers A*](36_astar_workers_conception.md), [37 préclassement](37_preselection_homogene.md) | Implémentés expérimentaux, défauts 0, reprise conditionnelle |
| [36 C96 catchment](36_c96_air_site_catchment.md) | Placement retenu ; ne change pas la demande du modèle |
| [37 C97 moteur](37_c97_air_c69_engine_probe.md), [38 C98 réalisé](38_c98_air_realized_probe.md) | Sondes/diagnostics, pas chooser actif à ouvrir |
| [38 estimé/réalisé](38_profit_estime_vs_realise.md) | Réalisé mesuré ; estimation à l'élection encore à appairer |
| [39 C100–C115](39_c100_c101_air_physical_engine_choice.md) | Échecs et replays ; **C115=1 temporaire protégé**, pas succès statistique |
| [40 B9](40_b9_demande_catchment_20260927.md) | Diagnostic clos ; 461 builds / 923 endpoints, chiffres rapportés |
| [41 C117](41_c117_air_throughput_20260927.md) | Méthode reconstruite depuis le code ; original corrompu archivé |
| [42 C119](42_c119_air_income_model_20260928.md) | Modèle revenu non qualifié, défaut 0 |
| [43 C121 AIR](43_c121_air_economics_shadow_20260928.md) | Dernière décision du 29 prime sur étapes shadow ; pas de 20×10 |
| [44 C122](44_c122_air_regime_priority_20260929.md) | Arrêt au smoke, défauts 0 ; pas de 5×6/20×10 |
| [Catalogue C121](catalogue_decoupe_phase2_20260929.md) | Prototype phases 2/3 non adoptable ; correctif R4 local non mesuré |

## Références techniques et anciennes architectures

- [Mécanique du jeu](mecanique_jeu.md) : référence de conception ; vérifier version/API
  et distinguer formules établies, approximations et hypothèses.
- [Méthode](methode.md) : carnet détaillé de méthodes/expériences Phase 0–ML et pièges
  Squirrel ; le protocole d'adoption actuel est celui d'AGENTS.md.
- [Architecture historique](architecture_opexai.md), [cible](cible.md) : schémas datés,
  non inventaire du chargement courant.
- [Croissance](opexai_croissance.md), [multimodal](opexai_multimodal.md),
  [route](opexai_route.md), [plafonnement](opexai_plafonnement.md),
  [raccordement](opexai_raccordement_gare.md) : guides/diagnostics historiques.
- [AAAHogEx](aaahogex_evaluation.md), [jointure rail AAA](aaahogex_rail_join.md),
  [AdmiralAI](admiralai_evaluation.md) : études de références, pas permission de copie.
- [Plan C48](plan_c48_indexing.md), [plan C55](plan_c55_road_pax.md) : plans anciens,
  pas actions non livrées par défaut.
- [Walkthrough](walkthrough.md), [paramètres](walkthrough_regroupement_parametres.md),
  [sondes](walkthrough_regroupement_probes.md) : comptes rendus de livraisons, pas instructions.
- [Walkthrough racine](../walkthrough.md) : ancien point d'entrée, redirigé vers le corpus courant.

## Revues — constats à réconcilier, pas files parallèles

- [30 septembre](revue_code_2026-09-30.md) : findings R1–R26 ; dernières implémentations
  au journal du 30 et validations restantes dans tâches.
- [26 septembre](revue_code_2026-09-26_plan.md) : plan initial remplacé pour le suivi courant.
- [AIR du 24](revue_air_c68_c69_c84_c85_v92_2026-09-24.md).
- [22 intégrale](revue_code_2026-09-22_integrale.md),
  [22 réconciliation](revue_code_2026-09-22_reconciliation_courante.md),
  [21 plan](revue_code_2026-09-21_plan.md).
- [15 plan](revue_code_2026-09-15_plan.md),
  [15 correctifs](revue_code_2026-09-15_correctifs.md), [21 lots détaillés](revue/README.md).
- [6 plan](revue_code_2026-09-06_plan.md), [6 correctifs](revue_code_2026-09-06_correctifs.md) :
  antérieurs au seuil de preuve, aucun statut opérationnel courant.
- [Revue documentaire ciblée](revue_documentation_2026-09-30.md) et
  [réorganisation globale](journaux/reorganisation_documentation_2026-09-30.md) : deux lots distincts.

## Recherche initiale, artefacts et périmètre

[Phase 0/TrainLineAI](archives/phase0_trainline_synthese.md),
[pause](pause_feasibility_findings.md), [dataset hurdle](phase2_hurdle_dataset.md),
[Phase 3 ML](phase3_ml.md). Les graphiques `phase0_*`/`phase2_*` et CSV restent
à leur emplacement ; leurs valeurs ne sont pas actualisées artificiellement.

Le corpus maintenu comprend les Markdown racine, `docs/`, instructions `.github/`
et OpexAI, documentation de preuves et des harnais/fixtures du projet.
Voir aussi [scripts archivés](../sweeps/archive/README.md) et
[fixture TerrainMapProbe](../sweeps/fixtures/TerrainMapProbe/README.md).
Documentation/licences tierces dans `ai/library` et `content_download` : conservées,
pas réécrites comme des instructions OpexAI. Bundles, sorties générées et archives
corrompues ne sont pas des sources à « nettoyer » pour obtenir un verdict favorable.