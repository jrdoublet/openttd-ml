# T10 — Synthèse de la revue rail (4 novembre 2026)

Sources : les branches `cloud/revue-rail-T1-20261104` à `cloud/revue-rail-T9-20261104` et leurs
rapports `docs/revue_rail_20261104/T1_rail_loop.md`, `T2_ordonnanceur_slot.md`,
`T3_stock_upgrade_reparations.md`, `T4_pathfinder_segmente.md`, `T5_plans_gare_quai.md`,
`T6_construction_rollback.md`, `T7_execution_mise_en_service.md`, `T8_rames.md` et
`T9_inventaire_experimental.md`. Chaque rapport ne vit que sur sa propre branche.

- **Bases** : T1 part de `fbc0f100` (avant RAIL-FILL et RAIL-KEEP) ; T2 à T9 partent de `8268b653`.
- **Aucun gain causal n'est mesuré** : tout ce qui suit attend les bancs du PC.

## 1. Les 10 constats au plus fort gain attendu

Le classement est qualitatif, faute de banc : gain estimé × probabilité × coût de mise en
œuvre.

| Rang | Constat (rapport) | Classe | Pourquoi ce rang | État |
|---|---|---|---|---|
| 1 | **Quai et rame dimensionnés pour une rame unique à 50 % de la production** : quais de 3-4 tuiles, rames de 2 à 4 wagons, recopiés par les jointures (T5-01, T5-04). Traction choisie sur le plat (T8-01) | (a) mécanisme, (b) effet | Écart structurel avec AAA (quais de 7, rames de 10 à 13 wagons, note 196 contre 134). RAIL-LOOP et RAIL-FILL butent sur cette longueur | Proposé (opt-in « quai minimal », motrice départagée en pente) ; non codé |
| 2 | **Le Cas 2 double avant RAIL-LOOP** et retire la ligne des boucles à vie (T2-03) | (b) | RAIL-LOOP vaut environ +29 k£/an par rame, jusqu'à 8 rames ; le Cas 2 n'en ajoute qu'une | Proposé (« boucle d'abord », opt-in) ; à mesurer d'abord (`RAIL_EXPAND` contre `RLOOP commit` par ligne) |
| 3 | **Dépôt sur une courbe → `depot_front_curve`**, premier rejet de RAIL-LOOP, 46 au smoke 4×6 (T6-02) | (a) mécanisme | Correctif local et bon marché : préférer une ancre droite dans les 8 premières cases | Proposé, non codé |
| 4 | **Le devis compte 2 rames sur une voie unique** ; le constructeur n'en pose qu'une (T7-01) | (a) code, (c) fréquence | Classement du portefeuille biaisé par une flotte fictive | Mesure livrée (`pred_trains`, `built_trains`) ; opt-in proposé selon la fréquence |
| 5 | **Refus de jointure RAIL-OPEN → bannissement de 365 j** au lieu de 45 j (T5-03) | (a) | 708 cas dans le pack, dans le **bras de référence** de tous les bancs rail | Proposé, non codé (dynamique de repassage à banquer) |
| 6 | **Bannissements durables sur échecs transitoires** : `STNFAIL`, `NOTRAIN` au plafond, `TRKFAIL`, `ABND` (40 % des échecs) ; compteur jamais remis à zéro (T3-02, T4-03) | (b) | 545 `STNFAIL` et 3 543 rejets `abandoned_pair` dans le pack | Proposé (délai court selon le code d'erreur), après la mesure `RAIL_STN_FAIL err=` |
| 7 | **Coude à 90° possible à la jonction de deux segments A\*** (T4-01) | (a) code, (c) fréquence | Sous `pf.forbid_90_deg=1`, ligne non roulable, donc capital perdu | Mesure livrée (`ninety=`) ; correctif opt-in prêt dans son principe (source à 3 éléments) |
| 8 | **Deux propriétaires pour une même ligne** : RAIL-LOOP contre V284 (T1-01), RAIL-LOOP contre upgrade (T3-01) | (a) | Conversions détournées ou rames doublées pendant une boucle | **T3-F2 codé** (côté upgrade) ; côté V284 proposé (réservation par `lineId`) |
| 9 | **Voie 2 payée puis gelée 100 × 365 j** après un seul refus d'armement (T1-05) | (a) | 4 cas au 20×10 : de l'investissement déjà payé et récupérable | Proposé (reprise contrôlée) |
| 10 | **INVEST-STALL : 0 complément sur 37** à cause de `GetCapacity(locomotive) == 0` (T8-03) | (a) mesuré | Débloque une fonctionnalité opt-in déjà « B pass » (+35,9 k, 20×10) | **T8-F1 codé** |

Hors classement mais à garder en tête :
- T6-01, rollback qui rasait routes et arbres : robustesse et note des villes, **codé** ;
- T4-02, pente sous-pondérée dans l'A\* ;
- T5-02, arrière de quai jamais regardé ; mesure `back_a`/`back_b` livrée ;
- T9 : coût opcodes de `OpexV190Active()` par candidat.

## 2. Doublons et contradictions

| Thème | Rapports | Constat | Arbitrage |
|---|---|---|---|
| Propriété d'une ligne par plusieurs transactions | T1-01, T3-01, T2-03, T7-01 | Même racine : aucune réservation par ligne entre RAIL-LOOP, V284, Cas 2, RAIL-FILL, INVEST-STALL et V257 | Une **réservation `lineId` unique** plutôt que des gardes au cas par cas. T3-F2 en est le premier cas, à replier dans ce mécanisme |
| Politique de bannissement | T3-02, T4-03, T5-03, T2-01 | Quatre chemins vers `_markPairAbandoned`, avec le même délai 365 × n et sans tenir compte de la cause | Une seule table de délais par motif (transitoire, physique, caisse), à concevoir une fois |
| Préemption du slot | T3-04, T9 (SEARCH-PRIO) | T3 cite RAIL-SEARCH-PRIO comme remède ; T9 recommande de le retirer (−325 k, −409 k) | **T9 l'emporte** : traiter T3-04 par un délai de 180 jours sur la préparation C121 |
| V190 | T2-02 (F1 codé), T9 | T2 corrige un bug sous V190 ; T9 recommande de retirer V190 | F1 est sans effet au défaut. Le garder jusqu'au retrait, qui le rendra caduc |
| Longueur de quai | T5-01, T8-02, RAIL-LONG (T9) | RAIL-LONG v3 « NO-GO », mais son exposition n'a jamais atteint la cible : l'idée n'est pas réfutée | Ne pas conclure contre les rames longues avant T5-01 et T8-02 |
| Comptages RAIL-LOOP | T1 (20×10 : 56 échecs, dont 31 plafonds A\* et 17 absences de chemin), T6-02 (smoke 4×6 : 46 `depot_front_curve`) | Campagnes et étapes différentes (recherche contre précontrôle d'armement) : pas de contradiction | Le smoke de la phase 0 doit compter les deux motifs |

## 3. Corrections déjà codées et risques croisés

| Branche | Correction | Effet au défaut | Fonction touchée |
|---|---|---|---|
| T2 | F1 : `_startRailUpgradeSearch` ne réécrit plus un slot occupé | Aucun (V190) | `task_rail.nut::_startRailUpgradeSearch` |
| T2 | F2 : `rail_upgrade_cash_memory` (opt-in, nouveau réglage) | Aucun | `_expandRailLines`, `_consumeRailUpgrade` (sortie CASH), `OpexExecuteUpgradeAfterSearch` |
| T3 | F1 : pas d'upgrade sans slot train (`NOVEHSLOT`) ; F2 : l'upgrade cède à RAIL-LOOP | Seulement au plafond de trains, ou dans la course | `_consumeRailUpgrade` (tête de fonction) |
| T4, T5, T7 | Mesures `ninety=`, `back_a`/`back_b`, `pred_trains` | Aucun (`decision_log`) | `_continueRailSearch`, `_recordRailAttempt` (deux lignes de journal distinctes) |
| T6 | F1 : le rollback ne défait que notre rail | Seulement en cas d'échec de pose | `builder_rail.nut::OpexRollback` |
| T8 | F1 : `<= 0` à la revalidation d'INVEST-STALL | Aucun (opt-in) | `task_v284.nut` |

**Risques croisés.**

1. **T2 et T3 dans `_consumeRailUpgrade`.**
   - Les hunks sont distincts : la tête de fonction pour T3, la branche CASH pour T2.
   - T3-F1 produit `{reason="NOVEHSLOT", cost=0}`, que T2-F2 ne lit qu'en cas de `CASH` : pas
     d'interaction.
   - T2-F2 lit `upgrade.cost` posé par `OpexExecuteUpgradeAfterSearch`, que T3 n'appelle plus en
     l'absence de slot : cohérent.
2. **T6-F1 et les autres** : `OpexRollback` sert aussi au chemin `TRAINFAIL` que T3-F1 évite
   désormais. Aucune contradiction ; T6 réduit seulement les dégâts d'un rollback encore possible.
3. **Projections OFF.**
   - T2 à T8 ajoutent chacune une couche **à la même ligne** de
     `sweeps/invest_stall_diagnostic_off.py`, et modifient **la même expression** dans
     `test_rail_{loop,fill,keep}_20261104.py`.
   - Conflits textuels certains à la fusion. Résolution : empiler toutes les couches, la plus
     récente fusionnée en premier ; dans les tests, imbriquer les `revue_rail_tN_off`.
   - Les hunks Squirrel ne se recouvrent pas : chaque projection reste indépendante.
4. **T2 ajoute un réglage** (compteurs de réglages, `test_v251_inventory`, etc. mis à jour dans
   T2). À fusionner **en premier** parmi T2 à T8, pour que les autres rebasent sur les compteurs à
   jour.
5. **T1** part de `fbc0f100` et ne contient **que de la documentation et des preuves**, pas de
   code. Fusion sans risque, mais sa comparaison avec `8268b653` montre RAIL-FILL et RAIL-KEEP
   « supprimés » : fusionner son commit seul, sans réinitialiser la base.

## 4. Ordre de fusion et de banc pour le PC (un banc à la fois)

Bras de référence partout :
`OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]` contre AAA rail seul.
Graines du smoke : 17, 512, 314, 8191. Les portes suivent `AGENTS.md` §4.1, avec le lanceur
`run_c66_reference.py` et ses options explicites.

| Étape | Fusion (branche d'intégration, jamais `master` sans accord) | Banc | Critère pour continuer |
|---|---|---|---|
| 0 | T1, T9 (docs), puis T2, puis T4, T5, T7 (mesures `decision_log`) | **Smoke 4×6 rail seul**, `decision_log=1` contre référence | Santé 8/8. Relever `ninety`, `back_*`, `pred_trains` contre `built_trains`, `RAIL_STN_FAIL err=`, `RAIL_EXPAND` contre `RLOOP`, `depot_front_curve`, `skip_fallback`. **Pas de porte** : mesure sans changement de jeu |
| 1 | T3 et T6 (corrections sans condition) | **Smoke 4×6** contre la base `8268b653` | 8/8, aucune régression visible, `NOVEHSLOT` et `RLOOP_OWNED` rares |
| 1A | idem | **Porte A 40×5** `gain_short` | Neutre ou mieux, garde de valeur 5 % (correction de bug : attendre la non-régression, pas un gain) |
| 1B | idem | **Porte B 20×10** `non_erosion` | Pass ; ensuite seulement, proposer la fusion dans `ccr-6d627d08-tlnphk` |
| 2 | T8 (INVEST-STALL, opt-in) | Smoke 4×6 `invest_stall=1` → porte A 40×5 → porte B 20×10 | `done route=fleet` > 0 au smoke ; puis portes économiques pour décider de l'adoption |
| 3 | Premier opt-in à coder selon l'étape 0 : T6-02 (dépôt droit) si `depot_front_curve` domine, sinon T2-03 (boucle d'abord) | Smoke 4×**10** (RAIL-LOOP ne paie qu'à 10 ans) → porte A 40×5 → porte B 20×10 | Un opt-in à la fois. Ordre suivant : T7-01, T5-03, T4-01 (si `ninety > 0`), T3-02/T4-03 (bannissements), T5-01 + T8-01 (quai et rame) |
| 4 | Nettoyage T9 après validation de la liste par l'utilisateur | Suite complète, puis smoke 1×1 de compilation par lot ; règle de neutralité opcodes pour `OpexV190Active()` | Identité au bit près entre deux bras du même code |

GitHub Actions reste refusé à cette session (403) : l'exécution se fait sur le PC.

T10 TERMINÉ
