# AIR-ROI-RENFORT-1 — étape 2b, expérience ITT par report aléatoire (22/10/2026)

> **ARCHIVE HISTORIQUE — WIP LOCAL NON INTÉGRÉ (22/10/2026).** Expérience décrite depuis le `master` local au HEAD `41031a7f`, incluant du Squirrel non commité. L'assignation `air_roi_renfort1_itt` et le report de renfort sont du **code expérimental non intégré et non adopté** ici. Ce rapport couvre des smokes et une première exposition **interrompue** ; la campagne complète ultérieure est relatée dans des rapports distincts, mais aucune de ces mesures n'a qualifié un ROI marginal causal ou une politique économique. Les fichiers `results/` et les logs de l'étude sont **locaux au WIP et non archivés ici** ; les analyseurs Python déjà versionnés restent des éléments distincts.

Le protocole prospectif figure dans l'[amendement §7](air_roi_renfort1_protocole_fourches_20261022.md#7-amendement-prospectif-22102026--itt-par-assignation-intra-partie). Le précédent [blocage transactionnel](air_roi_renfort1_etape2b_fourches_20261022.md) reste valable pour les fourches *same-save*. Le présent dispositif assigne le report dans une partie vivante et mesure une autre intervention.

## Contrat effectivement implémenté

- `air_roi_renfort1_itt=0` est le défaut aux quatre difficultés ; `1` journalise un témoin p=0 ; `2` assigne un report p=50 % au dernier point de renfort AIR financeable. Pas de changement de C121/V161/C70/C69, tier C77, rang ni priorité. Au mode 0, aucun état supplémentaire n'est sérialisé et aucun tirage n'est effectué.
- Graine du monde (`game_creation.generation_seed` lorsqu'elle est accessible), hachage borné `(seed, lineId, numéro d'épisode)` et journal `AIRR1_ITT_ASSIGN` avant `OpexAirAddPlane`. Le report verrouille les renforts de la ligne pour 732 jours, y compris l'ancien chemin `plan=null` ; l'état reste dans Save/Load. En traitement, la politique poursuit naturellement ses choix, avec possibilité d'autres renforts. Une ligne ne reçoit pas de deuxième assignation expérimentale avant 732 jours.
- `AIRR1_ITT_OUTCOME` publie `added`, `replaced`, motif constructeur et `AIAccounting.GetCosts()`. Ce dernier capture une **transaction nette** éventuellement multi-unités et un délai de ticks, et ne garantit pas une facture par VehicleID. `added=0` reste au dénominateur ITT. La reconstitution d'un crash suit un autre mécanisme.
- Deux estimands distincts : différence de résultat ligne à +24 mois entre affectations randomisées **à l'intérieur** des parties p50, et différence compagnie p50 − p0 entre parties de même graine, contre AAAHogEx. IC95 par bootstrap de 20 000 grappes de graines, sous-groupes de flotte initiale 1/2/3–4/≥5, saturation cible et type de ligne. Effet physique net par avion impossible à déduire sans premier étage et un suivi de ligne non ambigu ; un rapport comptable `per added` éventuel reste descriptif et conditionné.

## Validation initiale

Tests de contrat, auditeur et mécanismes AIR voisins : **94/94 réussis** par `uvx --from 'pytest==8.4.2' pytest -q` sur `test_air_roi_renfort1_itt_contract.py`, `test_audit_air_roi_renfort1_itt.py`, `test_audit_air_roi_renfort1.py`, `test_v251_inventory.py`, `test_v161_fleet_net_marginal.py`, `test_r1_partial_fleet.py`, `test_c121_air_economics.py`, `test_c84_air_target_fleet.py`, `test_v160_fleet_routes_index.py` et `test_v246_fixed_policies.py`, après réconciliation des deux inventaires à 102 réglages.

Le smoke `air_roi_renfort1_itt_smoke42_1y_20261022`, duel p0/p50, graine 42, un an, est complet et identique en `profit_year` terminal à ce stade (**0 £** de différence). Les logs contiennent dans p50 **6 assignations dont 4 reportées**, publiées avant les issues constructeur ; la référence p0 livre un renfort `added=1`, `replaced=0`, coût comptable **32 812 £**. Le premier an ne vérifie pas un succès p50.

Le smoke prolongé `air_roi_renfort1_itt_smoke42_3y_20261022`, même graine, montre **26 assignations p50, 11 renforts immédiats et 15 reports** ; huit ajouts p50 sont déclarés `added=1`, `replaced=0`, avec coûts comptables positifs (32 812 ou 38 964 £). Deux parties complètes, sans alerte de compilation Squirrel ; la comparaison compagnie p50 − p0 à 3 ans vaut **−439 921 £/an**, soit une valeur de compagnie relative **−19,27 %**. Ce seul couple de parties ne fournit aucun IC inférentiel ni qualification V102, et ne préjuge pas du résultat 20×6.

### Audit ITT par graine et cohortes, smoke 1×3

L'auditeur `sweeps/audit_air_roi_renfort1_itt.py` et ses **7 tests synthétiques** contrôlent les assignations/outcomes, exclusions manquantes, doublons, suivi mensuel explicite, jointure `VEHS` et rééchantillonnage de **grappes de graines**, avec un IC95 seulement si plusieurs grappes contributrices. Commande effectivement exécutée :

```powershell
python -X utf8 sweeps/audit_air_roi_renfort1_itt.py 'results/air_roi_renfort1_itt_smoke42_3y_20261022_engine/airr1_itt_p50_seed42_r0.log' --telemetry 'results/air_roi_renfort1_itt_smoke42_3y_20261022.jsonl' --telemetry-policy-id airr1_itt_p50 --format markdown
```

| Cohorte prétraitement | Nombre d'assignations p50 (1 graine) | ITT net ligne 24 mois / IC95 |
|---|---:|---|
| 1 avion initial | 24 | `null` / `null` |
| 2 avions initiaux | 2 | `null` / `null` |
| 3–4 ou ≥5 avions | 0 | sans effectif |
| Sous cible (`vehCount < target`) | 26 | `null` / `null` |
| À la cible/saturée | 0 | sans effectif |
| Type `newpair` / `hubsite` / `hubhub` | 5 / 20 / 1 | `null` / `null` |
| Source V161 `prior` | 26 | `null` / `null` |

Les 26 épisodes n'ont **aucune** série mensuelle de profit **net** `AIRR1_ITT_MONTH` ; `seeds_with_both_arms` pour ce résultat est **0**. Le contraste descriptif de profit de **flotte VEHS** construit par l'auditeur vaut **+43 871,26 £/an** (`treatment − deferred`) dans cette unique graine, **sans IC95**, et concerne la flotte sur 24 mois civils, pas le profit net à la date exacte `t0 + 24 mois`. Le ROI V161 utilisé (`roi`, `v161_model`, `v161_source`) est bien journalisé au choix, mais son rapprochement avec un **rendement marginal net causal** reste non calculable. Ni ce proxy ni le delta compagnie d'une graine ne démontrent l'éviction d'un investissement ferroviaire.

## Exposition préenregistrée sur 20 graines × 6 ans

Campagne `air_roi_renfort1_itt_exposure20x6_20261022` : 20 graines listées au §7, deux parties par graine (témoin p0 et assignation p50), une répétition, 6 années, `--script-debug --line-telemetry --line-telemetry-monthly`, Docker `openttd-lab` et harnais `sweeps/run_c66_reference.py`, plafond 10 CPU/10 workers/8 Gio. Ce diagnostic n'est pas une porte A ni B d'adoption.

**Campagne interrompue, NON QUALIFIABLE (code de sortie Docker 137).** Le lanceur AIR avait démarré seul puis une autre session a lancé simultanément le conteneur `rlw04_on_engine1024_20261022` (2 workers). La règle d'une seule campagne active étant violée, nous avons stoppé **uniquement** le conteneur AIR `077e63ff21f1…` ; le conteneur RLW-04 `c1758ccc1fc4…` est resté actif, sans modification. Le lancement AIR a généré un JSONL partiel `results/air_roi_renfort1_itt_exposure20x6_20261022.jsonl` mais pas de bilan final complet. Les données partielles restent documentaires, n'ouvrent aucune porte V102 et ne peuvent être prises pour 20 graines × 6 ans finies. Aucune relance automatique en concurrence avec RLW-04.

L'auditeur compte **237 assignations p50 sur seulement quatre graines dont les logs sont présents** : 137 renforts immédiats, 100 reports, 113 ajouts déclarés. Ces effectifs sont **partiels, censurés et non comparables aux 20 graines planifiées**. Aucun des 237 épisodes ne possède ici 24 observations explicites de profit net par mois ; les ITT et IC95 à +24 mois restent `null`. Les données descriptives partielles sont conservées à seule fin de diagnostic et ne servent pas à choisir un sous-échantillon favorable.

Un `lineId` NoAI ne correspond pas directement à la clé par stations des lignes reconstruites depuis `VEHS`. La télémétrie `profit_last_year_gbp` représente les véhicules et exclut potentiellement des coûts d'infrastructure : une jointure et un suivi mensuel complets sont nécessaires pour publier une estimation ITT de profit de ligne. Les épisodes censurés, coûts manquants, `REPLACE`, refus et rattrapages doivent être comptés séparément. L'effet de trésorerie/éviction doit être mesuré via des événements d'investissement, pas inféré d'une variation de caisse à elle seule. En attendant une campagne saine, **effet ITT à 24 mois, IC95 par graine et ROI physique par avion : non estimables**.
