# OpexAI P2/P4 — résultat expérimental complémentaire V166 (13 octobre 2026)

L'investigation P2/P4 a été **rouverte expérimentalement** après le rejet
indépendant de la garde AIR P4 (+68 191,8 £/an sur le pilote de cinq graines,
mais −52 352,375 £/an sur 40 graines à cinq ans, même bundle). Les autres
rejets P3, stable-cohort, `fresh_equal`, `partial` et P4 véhicule-année
restent acquis : **aucune campagne ancienne n'a été relancée**.

## Nouveaux travaux réalisés et exposés en moteur

- Cinq worktrees **neufs, isolés** basés sur `7ecbabe` (V166), pour
  archives physiques, P4-sorties, C77-chaîne, réparation AIR crash-only,
  intégration contrôlée ; `master`, `origin/master`, le checkout principal,
  C121/R2/V161, C77/V88, P1/V165 et la trésorerie historique sont préservés.
- Deux jeux de référence cinq ans (graines 314159/161803) ont archivé
  **120 sauvegardes mensuelles** et identifié deux avions disparus des
  relevés en 1973. L'interprétation honnête est disparition d'ID, pas
  crash/prix final imputé.
- Sonde P4 passive : captures pré-vente YTD, crash confirmé + dernier C117
  daté, autoreplace, inventaires et tombstones. Sonde C77 passive : tête et
  première alternative réellement **de même tier et simultanément
  finançables**, tentative, veto, construction immédiate ou A* différée,
  `lineId`. Les deux flags restent OFF sur les quatre difficultés.
- **50 tests** hôte des deux sondes + crash-only et régressions de
  persistance, puis **un test de reconstruction de chronologie** : tout
  vert. Save→Load réel ciblé réussi : 25 saves phase A, chargement positif
  `LOAD_RECONCILE` et 13 saves phase B (un an supplémentaire), avec
  réserve connue concernant une compagnie humaine fantôme du harness.
  Le smoke moteur de deux ans a été complet, avec **12 épisodes C77**
  admis (9 constructions prouvées).
- A/A ON/ON d'une graine pendant cinq ans : **60/60 checkpoints identiques**
  et **872/872 événements identiques**, 120 saves. C77 trace 103 paires,
  75 dispatch, 44 constructions, 10 retours rail différés.
- Matched sondes OFF/ON deux graines à cinq ans : **premiers écarts dès
  mai/septembre 1970**, Δ `profit_year` moyen **−108 623 £/an**,
  `company_value` **−11,045 %**. Cela établit **une perturbation des
  trajectoires par l'instrumentation** : les sondes doivent être activées
  dans les **deux** bras de tout essai causal.

## Seule nouvelle politique behaviorale suffisamment fondée et testée

`score_p4_air_crash_only=1` restaure seulement les avions après crash
confirmé, en réutilisant le constructeur V166 avec garde de cash + réserve.
Contrairement à `policy_vehicle_events`, elle n'active ni les retraites
C52 ni les autres modes. Flag OFF par défaut, pas de prior numérique.

Deux lots **disjoints** 2×5 et 3×5 dans le **même bundle gelé**
`ac2e4950…` donnent, réunis : **1 victoire / 4 défaites**, Δ `profit_year`
terminal moyen **−5 291,8 £/an**, médiane −28 393 £/an,
IC95 bootstrap **[−81 137,8 ; +91 073,6] £/an** ; Δ moyen `company_value`
**+61 687,8 £**. Pas de signal robuste justifiant 40×5.

Le contrôle additionnel **avec P4/C77 sondes activées dans les deux bras**
(deux graines, quatre parties complètes sur cinq ans, 240 saves, bundle
`d34cd312…`) donne **0 victoire / 2 défaites** : Δ `profit_year`
**−54 809,5 £/an**, `company_value` ratio **−5,656 %**.

Ce contrôle a identifié **les mêmes deux crashs initiaux exactement aux
mêmes dates/VehicleIDs des deux côtés**, puis cinq paires C77 identiques
avant crash pour chaque graine. Sur la graine 314159, l'avion 45 perdu
le 22 mars 1971 est réellement reconstitué : l'année suivante la ligne
a **deux avions ON contre un OFF**. Néanmoins les premières décisions
C77 post-crash sont décalées (+72 jours graine 314159, +32 jours graine
161803), les constructions et le réseau divergent et le `profit_year`
terminal **n'augmente pas**. Ceci établit une chaîne de politique
**exposée et non gagnante**, pas une variante non testée.

## Décision économique et limites restantes

**Rejeter la politique crash-only dans le chantier P2/P4. Pas de
qualification 40×5 ni de validation indépendante**, puisque les deux
portes courtes sont défavorables. La valeur d'entreprise doit continuer
à être surveillée conjointement, mais une légère moyenne positive dans
un échantillon de cinq graines n'est pas un gain terminal de profit.

Les seuls mécanismes demeurant ouverts à *une identification causale future*
sont les profits des véhicules crashés **entre** échantillonnages, le
profit marginal de réseau de l'alternative C77 non bâtie, les externalités
de hubs, et le froid P2 (43 lignes strictes, 55 descriptives, 102 tôt
construites, trois flips admissibles sans alternative réalisée). Les
sauvegardes mensuelles obtenues depuis lors ne sont pas des instantanés
**au tick immédiatement avant C77** ; elles ne remplacent pas un fork
strict du même état et les A/A. Inventer un coefficient de compensation
ne serait donc ni identifiable ni rentable d'après ces expériences.

**Ce verdict s'applique aux hypothèses et interventions réellement testées.
Il ne prétend pas démontrer qu'aucune amélioration future d'OpexAI n'est
possible.** Aucun commit, merge, reset, push ou intégration V166.

### Preuves détaillées

Rapport technique et référentiel de tous les chemins :
`results/scores_p2_p4_integrated_probe_stage_20261013/docs/scores_p2_p4_experimental_verdict_20261013.md`.

Reçus de campagnes :
`results/scores_p4_air_crash_only_stage_20261013/results/scores_p4_air_crash_only_pilot5x5_consolidated_20261013.json`,
`results/scores_p2_p4_integrated_probe_stage_20261013/results/scores_p2_p4_probes_aa1x5_r2_20261013.json`,
`.../results/scores_p2_p4_probes_onoff2x5_20261013.json`,
`.../results/scores_p2_p4_probe_crash_policy2x5_20261013.json`,
`.../results/scores_p2_p4_probe_crash_policy2x5_trace_20261013.json`.

Les bundles et manifests C66/versions sont enregistrés par chaque campagne.
Les 2 127 tests, l'ancien Save/Load 80 lignes, et les 40×5 déjà qualifiés
n'ont pas été répétés.
