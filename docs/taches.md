# Tâches — travail restant

**Mise à jour : 2 octobre 2026. Seule liste autoritaire des actions ouvertes.**
Les décisions et résultats terminés sont dans la [synthèse historique](journaux/synthese_decisions_2026-09-30.md)
et les [journaux](journaux/README.md). Les anciennes mentions « à faire » des fiches
ne créent pas une tâche. Protocole et pilotage des bancs : [AGENTS.md](../AGENTS.md), §4/§4.1.

## État courant

- Runtime cible : OpenTTD 15.3 / NoAI 15 / OpenGFX 7.1 / OpenTTDLab 0.0.75.
- Socle adopté : C68, C69 bis/C70/C75, C77 permanent, C76 ciblé, mémo urbain,
  régénération par mode, index hub, C75 bis, C83.1 (six villes), C87, V89/V90,
  V91=120, V94 et C96 ; financement rail=100, distinct du facteur terrain 170.
  Déclarations et chargement exacts : `info.nut`/`settings.nut`.
- **C115=1 temporaire et protégé : ne pas le modifier.** C116/C118/C119/C120/C121/C122
  ne sont pas adoptés. Workers rail/ville, stock A* et `homogeneous_preselect` : défaut 0.
- C67.3–.6 livrés, sans consommateur métier exposé ; Lakes et feeders retirés.
- **Quatorze findings implémentés localement, sans qualification individuelle** :
   R1/R2/R3/R4/R5/R18/R19/R20/R21/R22/R23/R24/R25/R26. Aucun run GitHub attesté dans ce suivi.
  L'arbre local n'est donc pas une nouvelle référence économique qualifiée.
- **Docker local disponible (30/09)** : smoke 1×1 OK et Save/Load OK sur l'arbre
  courant (compilation Squirrel et `require` validés), 830/832 tests Python (2 = Git absent).
  Correctifs de revue OpexAI (`REPLACE`, file réactive, budget imbriqué) inclus.
  [Journal](journaux/journal_2026-09-30.md#revue-concurrente-opexai-et-premières-exécutions-moteur-locales).
- **Lots cadence P4/P7/hubs (30/09)** : intégrés derrière trois options OFF ;
   diagnostic 4 bras × 5 graines × 6 ans complet et sain, aucun gain moyen de
   profit Opex en 1975. Save/Load combiné technique réussi ; suite finale :
   896 réussites / 1 erreur Git absent / 1 skip sur 898 tests.
   [Résultats et limites](cadence_parallel_20260930.md). Aucune adoption.
- **Audits parallèles intégrés (01/10)** : 95 tests de lecteurs réussis ; suite
   complète finale 996 réussites / 1 erreur Git absent / 1 skip sur 998 tests.
   Exposition technique r2 : deux duels sains, sources inchangées ; sondes larges
   fortement perturbatrices, aucune qualification économique. Dans ce profil,
   AIR domine le coût catalogue, pas rail pax. Aucun changement Squirrel.
   [Bilan et protocole](parallel_integration_20261001.md),
   [journal](journaux/journal_2026-10-01.md).
- Sources C116/C117/C122 absentes ou corrompues : résultats rapportés, non revalidés.
  Date récente, code livré et job vert ne remplacent pas une preuve qualifiée.
- **Trois lots AIR/shadow/R1-R3 intégrés (01/10)** : 1113 réussites /1 erreur
   Git absent /1 skip sur 1115 tests. Smokes finaux sains, trois Save/Load OK.
   Sonde légère : 20/20 duels 5×6 sains, filtre de perturbation passé, neutralité
   non prouvée. Shadow : 48 élections complètes, 369 inversions de paires mais
   zéro changement de tête ; sonde coûteuse OFF. R3 observé naturellement,
   huit scénarios dirigés alors non validés. [Bilan](three_lots_integration_20261001.md).
- **Compléments performances/fixtures (01/10)** : défaut contre AAAHogEx,
   5×6 complet et sain ; profit moyen1975 1,524 M£ contre4,748 M£, moyenne des
   ratios31,82 %, aucune victoire finale. Huit fixtures dirigées R1/R3 et
   matrice VM48+9 validées dans des copies, dont deux frontières Save/Load R1.
   R3 caducité validé par relecture après correction du lecteur ; verdict brut
   conservé. Suite complète1124 réussites /1 erreur Git /1 skip, puis136 contrats
   finaux réussis. Aucune modification de production ni qualification économique.
   [Résultats, preuves et limites](performance_completion_20261001.md).
- **C121 cache, lot 1 (01/10)** : snapshots complets et invalidation des caches
   enfants corrigés ; 61 contrats Python, 32 assertions NoAI et smoke défaut OK.
   Reload sur scan actif au 1970-02-01 : caches dérivés abandonnés/reconstruits,
   hits réels `newpair`/`hubsite`, `hubhub` non exposé. Aucun gain/opcode ni
   qualification économique. [Bilan](c121_cache_coherence_20261001.md).
- **C121 post-chantier, lot 2 (01/10)** : deux smokes OK ; 20 duels courts
   récupérés hors moteur après interruption de l'assemblage, couverture/santé
   complètes. **Rectification : dix témoins contaminés par la sonde**, filtre
   ON/OFF invalide ; −41,33 % décrit des trajectoires instrumentées, pas un
   résultat sans sonde. Copies préparées ≠ sources chargées. Lanceur isolé par
   bras et contrôles négatifs corrigés, 25 tests ciblés OK, correction non
   exercée moteur. Bootstrap laissé de côté à la demande utilisateur ; reprise
   sur service valorisé/acheté/réalisé. [Rectification](c121_investments_20261001.md).
- **C121 profondeur de décision (01/10)** : incohérence exposée entre économie
  full-fleet propagée au classement et profondeur déjà choisie par le score C121.
  Correctif minimal `c121_air_decision_depth_economics`, défaut 0 : moteur,
  achat initial N=1 et cible post-build inchangés. Isolation A/B/C/D exercée au
  moteur dans des copies ; B reste impossible en production car le catalogue est
  volontairement dépendant de C121. La sonde décision→réalisé est perturbatrice
  en 5×3 (+85,3 k£/an trace−témoin en moyenne), donc exclue de la preuve
  économique. Pilote non instrumenté 5×6 candidat vs C115 : Δ `profit_year`
  **−493,1 k£/an** moyen, médiane −717,4 k£, 1/4, IC95 Student-t
  [−991,4 ; +5,2] k£/an ; valeur ratio-des-moyennes **−29,34 %**, garde 5 %
  échouée. **Verdict : rejeté ; aucun 20×10.**
- **C121 profondeur portefeuille / split (01/10)** : le socle courant C121 est
  déjà très déficitaire contre C115 (−459,1 k£/an, valeur −33,30 %, −5,4 slots
  Opex). L'isolation `portfolio_depth` sur le même bundle ne rajoute que
  −61,6 k£/an : le couplage du profit de profondeur au plancher absolu est réel,
  mais secondaire. Le correctif distinct `c121_air_portfolio_split_economics=0`
  sépare max-profit long terme (qualification) et profondeur `P/max(C,K_dec)`
  (seul `fundScore`) sans changer moteur/N=1/cible post-build. Son 5×6 contre
  C115 perd **−684,5 k£/an**, 0/5, IC95 Student-t
  [−1 109,1 ; −260,0] k£/an, valeur **−35,36 %**, slots/villes Opex −9,6.
  **Rejeté ; aucun 20×10.** Ne plus empiler de profondeur statique ; prochaine
  hypothèse à définir : valeur de continuation marginale N=1→N+1, revalorisée
  après observation, sans réarmer les variantes C121/C122 rejetées.

## 1. Priorité immédiate — valider les livraisons locales

Ordre de dépendance, pas autorisation de publier ni de modifier un défaut.

| Action | Statut / blocage | Prochaine étape et critère de sortie |
|---|---|---|
| Publication et accès aux bancs | **Bloqué localement** : copie sans Git, accès Actions non établi | Identifier dépôt, branche et SHA publié avec accord utilisateur ; vérifier authentification, quota et absence de doublon. Aucun push implicite. [Guide GitHub](bancs_github.md). |
| R24–R26 : admissibilité, couverture du profit, harnais figé | **Implémentés, à valider** | `benchmark-regressions.yml` : fixtures Windows/Linux, OpenTTDLab fixé et selftest ; puis smoke moteur 1×1. Vérifier couverture et provenance du collecteur. [Journal du 30](journaux/journal_2026-09-30.md). |
| R18/R21/R23 : nivellement AIR, débouché fret, devis rail | **Implémentés, à valider** | Contrats source, injections d'échecs/contre-tests moteur, smoke 1×1 puis diagnostics 5×6 **isolés par lot**. Les contrats textuels ne compilent pas Squirrel. |
| R2/R3/R22 : profit observé, bypass AIR, retraite | **R2 VM et trois fixtures R3 validés ; qualification économique distincte** | R2 : facteurs observé/prédit0,5/1/1,5 exercés en VM C70/C82. R3 : caducité A–B/A–C/D–E, cash et vrai refus API après bypass validés ; K_pass=0 naturel, portefeuille de test réduit, pas tous les régimes ni gain causal. R22 reste : dépôt >90 j, ordre disparu, entretien, vente/timeout et Save/Load. [Compléments](performance_completion_20261001.md). |
| R4/R5/R20 : continuation, autotests au chargement, régime persistant | **R5/R20 observés au reload (30/09) ; R4 clos sans effet** | R4 : 167 tranches, `chained_slices=0` ; le budget n'est testé qu'entre paires et une paire (~40 k opcodes médian) dépasse un tick, donc enchaînement intra-tick inatteignable. Décision : garde-fou conservé tel quel, aucun gain attribuable ; points d'arrêt intra-paire = chantier distinct. R5 : `selftest skipped` ×2 ; R20 : `C121_STRATEGY_RELOAD` restauré. Restent : verrou race/efficiency, ancien format, file/worker en cours, options séparées. |
| R1/R19 : renfort partiel AIR et récupération de chantier | **Cinq fixtures R1 validées ; récupération R19 partielle** | Besoin réel4/budget1, seuil prix +1 000 £ après réserve et contre-test +999, achat réel+1, mutation API, non-duplication et deux frontières Save/Load validés. Pas de gain marginal attribué. Refus R3 à A : pas d'orphelin, mais pas toute la récupération partielle R19. **R19 observé moteur local** (`r19_fault_inject`, défaut0) : PENDING→DONE ; ticket pendant rechargé puis terminé (`results/save_load_r19_inject_mid_20260930.json`). Restent vente refusée, aéroport occupé et hubs réutilisés. [Compléments](performance_completion_20261001.md), [historique R19](journaux/journal_2026-09-30.md#clôture-du-groupe-r1r19). |
| Bancs manuels GitHub | **Préparés, intégration non validée** | Après publication autorisée : solo/smoke et duel/smoke pour l'intégration ; paired/smoke pour une intervention causale. Contrôler santé, horizon, artefacts et bras réellement différents. |
| Qualification GitHub enchaînée | **Implémentée, à valider** | `qualify.yml` : contrats puis smoke→diagnostic→adoption, décisions déterministes et preuves d'exposition. [Plan pré-enregistré](../qualifications/README.md). Publication/accès supposés satisfaits pour ce développement selon demande utilisateur ; aucune campagne ni modification de défaut effectuée. Fixtures et intégration réelle restent à exécuter. |
| Image Docker et audit de preuves | **Fait localement (30/09)** | Image `/opt/venv` construite et exercée (smoke, Save/Load, 5×6) ; proxy TLS via `SSL_CERT_FILE`. `test_review_evidence.py` : 13/13 OK. Limite maintenue : L'intégrité des 57 archives ne prouve pas la couverture de toutes les citations. [Bilan documentaire](revue_documentation_2026-09-30.md). |
| Récupération des preuves | **Sources absentes (reconfirmé 30/09)** | Recherche locale dans tout `PRV/` : seuls scripts, tests, fiches et archives non autoritaires C116/C117/C122 ; aucun JSON de résultat ni manifeste. Récupération seulement depuis une autre copie/le dépôt distant. Réconcilier capacités C116.4 et identifiant du bundle C122. Auditer les autres citations manquantes sans relancer les campagnes ni inventer de chiffres. |

**Isolation indispensable :** le workflow A/B compare deux réglages du même arbre.
Sans chemin témoin représentant l'ancien comportement, un run du cumul ne qualifie
pas causalement chacun des correctifs. Figer sources et protocole avant mesure.
Depuis le 30/09 : Python (venv 3.14) et Docker local disponibles ; Git/gh toujours
absents, donc ni SHA, ni référence de code figée, ni publication/campagne GitHub.

## 2. Revue du code — restant à implémenter ou à décider

Références : [revue du 30](revue_code_2026-09-30.md). Reconfirmer le constat sur le
code au moment de l'intervention ; ne pas coder toute la liste d'un bloc.

| Référence | Action restante | Condition / validation |
|---|---|---|
| R6–R10 | **Partiellement traité localement** : clarification interface R6/R7, retrait ciblé R8 (2 fonctions sans appel), contrats R10 consolidés ; R9 : verrouillage figé par contrat (`test_r9_…`), aucun retrait de code car toutes les branches BASIN_SHARE/compat sont évaluées (retrait = changement d'opcodes non mesurable sans moteur) | Exécuter smoke 1×1 et tests moteurs ciblés ; vérifier migration des lecteurs documentaires pointant les deux fonctions retirées ; confirmer absence d'impact cadence/opcodes puis statuer R9 séparément (gardes compat et branches verrouillées). |
| R11–R17 | Découper les responsabilités et organiser les tests | Lots métier isolés : builder AIR, sélection/exécution, rapport annuel, projets, résultats C121, autotests. Aucun refactoring transversal simultané aux correctifs comportementaux. |
| F-RAIL-ECON-01 (revue du 22/09) | **Implémenté derrière `rail_depot_cost`, défaut 0, non mesuré** | `economy.nut` ajoute `costRailDepot` si le flag est actif. Mesurer l'effet sur le classement rail (diagnostic 5×6 isolé) avant tout changement de défaut. |
| F-EVENT-BACKLOG-01 (revue du 22/09) | **Ouvert, faible priorité** | `events.nut::_processEvents` vide toujours la file sans quota. Mesurer d'abord l'exposition (taille des rafales, opcodes) ; corriger seulement si elle est démontrée. |

Revue du 22/09 revérifiée sur le code le 30/09 et close pour : F-ROAD-TXN-01 (ventes vérifiées, `allSold`), F-RAIL-START-01 (retour de `StartStopVehicle` lu, arrêt des trains déjà démarrés), F-RAIL-TXN-02 (`OpexBuildSecondTrain` appelle `OpexRollback` avec `rollbackVehicles`), F-LIFE-SCRAP-01 (retrait conditionné au retour de `SellVehicle`), F-SIGN-01 (troncature à 31 dans `OpexSign`). F-C80-TOWN-01/F-C77-SLICE-01 sont suivis par les chantiers C80 et régénération (§3). F-TEST-01 : les deux échecs historiques ne ressortent plus, les 2 échecs actuels sont dus à l'absence de Git. Ces fermetures sont des relectures, pas des validations moteur.

## 3. Chantiers ouverts — prochaine intervention bornée

<a id="c76-c77"></a>
<a id="revue-c76-c77"></a>
<a id="plan-ordonnanceur-début-de-partie--admission-priorité-et-réactivité-c83-2026-09-25"></a>

| Chantier | Statut | Prochaine étape / condition de passage |
|---|---|---|
| C121 catalogue / économie | **Prototype non adoptable ; decision-depth, portfolio-depth et portfolio-split rejetés** | Le déficit principal est déjà dans le socle C121 courant : −459,1 k£/an vs C115 et sous-expansion AIR. L'isolation portfolio-depth n'ajoute que −61,6 k£/an ; le couplage au plancher absolu est secondaire. Le split propre qualification/score perd −684,5 k£/an vs C115, 0/5, valeur −35,36 % : **aucun 20×10**. Ne plus optimiser une profondeur de flotte statique. Prochaine hypothèse seulement après spécification : valoriser N=1 + option marginale N+1 revalorisée sur données ultérieures, avec identité élection→réalisé non perturbatrice. Ne pas réarmer stock-growth/two-aircraft/territoire/bootstrap ; C115 reste protégé. [Lot cache](c121_cache_coherence_20261001.md), [rectification](c121_investments_20261001.md), [journal](journaux/journal_2026-10-01.md). |
| C121 cadence AIR live | **Live 1→2 prometteur tôt ; défaut K_pass confirmé/corrigé expérimentalement ; phase4 reste meilleur signal de gap** | Seuils fixes clos. Live corrected 5×6 : Δprofit −19,5 k£/an, gap −10,2 k£ mais gain net 1971–73. Phase4 : Δprofit −112,3 k£/an mais **gap +265,6 k£/an, 5/5**. Garde immédiate opcode-paritaire : +29,3 k£/an profit, +28,4 k£/an gap, 4/5 ; phase4+garde sans synergie. Shadow K_pass 2×3 : 59 arrêts, 8 blockers fleet, **6/8 cachent un AIR finançable dans les cinq rangs suivants**. Correctif OFF `c121_kpass_air_continue` : saute seulement le blocker fleet/K_pass, sans forcer son achat. Causal 5×6 demandé malgré le screening : Δprofit Opex **+42,2 k£/an**, 3/2, mais Δgap **−156,5 k£/an**, 1/4 ; 50 continues, slots/villes Opex +0,4. **Défaut logique à corriger, mais pas levier de rattrapage validé.** Audit C69 : un fleet C121 `samples=0` est déjà vu comme « réalisé » et perd l'exemption K_dec ; prochaine étape = shadow cold-vs-warm K_dec avant tout causal. Aucun 20×10 cadence. [Bilan cadence](c121_air_cadence_live_20261002.md), [journal](journaux/journal_2026-10-02.md). |
| C83 watcher / corrections (P4) | **Prototype OFF ; diagnostic défavorable** | `exp_c83_watch_daily` : 5×6, Δ profit Opex 1975 −114,3 k£/an, valeur −8,16 %. Exposition : 0 enqueue, intervalles jusqu'à 38 jours ; Save/Load technique réussi. Diagnostiquer blocages et détection→action avant variante ; aucune relance identique. Top-six et politique C83 conservés, `c83_fixes` non activé. Réarmement/coalescence et changement de villes restent séparés. [Bilan](cadence_parallel_20260930.md), [fiche C83](22_c78_lignes_vs_aaa.md). |
| C76/C77 reliquat | **À réconcilier** | Vérifier vivier injecté, invalidation non-AIR, intention mutatrice pendant worker, cycle de subvention et Save/Load. Points 1–5, horloge et premiers selftests déjà codés : ne pas les refaire. Réévaluation légère du vivier reste une piste distincte, pas retour à `lean`/rotation rejetés. |
| C80 workers / P5–P6 | **Piste mesurée, pas adoptée** | Réutiliser P1/P2/P5 ; arbitrage tranche par tranche selon travail prêt et blocage aval, sans famine ni boucle chaude `projects`. Stock A* en pause : expliquer l'éviction du rail avant relance. C67 s'intègre au futur arbitre, pas par multiplication de hooks. [Conception](36_astar_workers_conception.md). |
| Scheduler P7 | **Prototype OFF ; gain propre non démontré** | 5×6 : Δ profit Opex 1975 −17,2 k£/an malgré ratio +1,08 pt ; valeur +4,85 %. Exposition 7 sauts, Save/Load réussi ; mesurer coût net et délai vers tâche utile avant suite. `report_same_year`/`repay_same_month` seulement ; **`catalog_fresh` exclu** (effets avant garde), pas de batch accru ni `fleet_before_new`. [Bilan](cadence_parallel_20260930.md). |
| C80 rapport / catalogue / hubs | **Préfiltre OFF ; mesure légère intégrée et exercée** | 2×5×6 sondes : filtre pratique passé, IC95 du Δprofit inclut zéro, neutralité non prouvée. 939/942 invocations AIR appariées, 1564 sélections valides. Scope synchrone général : hub→hub premier 3/5, hub→site 2/5 ; aucun bloc premier ≥4/5. Choisir une intervention isolée sans mélanger bootstrap/ciblé ; pas de découpage automatique, pas de retour au préfiltre défavorable sur 42. Préserver C115/C121. [Trois lots](three_lots_integration_20261001.md). |
| C67 lecteur par Valuate | **Mesure à faire** | Fixture 5×5/10×10 : exactitude, opcodes, borne non suspendable ; pas de carte entière ni partie longue. Consommateur économique seulement après exposition démontrée. [Contrat](c67_cartographie_contrat.md). |
| Estimé à l'élection / réalisé par ligne | **Shadow OFF ; VM calibrations/V92 validée ; réalisé non raccordé** | 48 élections complètes, 20 mixtes, 61 occurrences fleet : 369 inversions fleet↔nouvelle liaison, zéro changement de tête. VM48+9 et achat dirigé4→1 validés ; aucun gain marginal démontré. Restent copie/tri diagnostic coûteux à alléger, identité élection→achat→année réalisée complète et qualification isolée avant changement de score. R2 conservé, C84/C121 exclus ; finance rail=100. [Trois lots](three_lots_integration_20261001.md), [compléments](performance_completion_20261001.md). |
| C116 graine 100 | **Conditionné aux preuves** | Chronologie cash/projets face à 999/1234/5678 dans C116.2 ; aucune nouvelle règle ni 20×10 sous les formulations rejetées. |
| C85 puis C84 | **Reprise conditionnelle** | C85 d'abord ; changement de sûreté mesuré séparément. C84 seulement après 5×6 C85 >+50 k£/an et garde valeur tenue ; pas de 20×10 avant ces portes. [C85](25_c85_air_equipment_frontier.md), [C84](24_c84_air_target_fleet.md). |
| C88 compagnies humaines/IA | **Reconnaissance seule** | Confirmer API NoAI 15.3 ; si `is_ai` inaccessible, constater et arrêter. Aucune heuristique nom/argent/activité, aucune décision changée. |
| Estimateurs low-opcode | **Après stabilisation C121** | Revue cold start physique + moyenne glissante : observations, fenêtre, invalidation, coût mesuré ; pas de constantes ajoutées sans modèle. |
| C121 calcul du gagnant AIR — opcodes | **Adopté : fusion=1 quand C121 est utilisé** | 20×10 complet et sain, 40/40 duels, neutralité selon règle pré-enregistrée : moyenne −68,5 k£/an, IC95 Student [−243,6 ; +106,6] k£/an, 7/20, p=0,263176, valeur −3,52 % (garde −5 % tenue). Verdict brut `fail_primary` conservé, pas de gain économique démontré. Pilote AIR −5,93 %/−6,61 %. Quatre difficultés à1, 109 tests et smoke du défaut livré sain. Économie C121=0 et C115 inchangés ; aucune adoption des autres changements. [Bilan et preuves](c121_air_winner_economic_validation_20261002.md). |
| C121 contexte commun paire/avion — opcodes (item 1) | **Non retenu ; défaut OFF** | Fixture saine, 72 cas/399 choix égaux, mais scan+gagnant +9,88 % à entrées identiques. Évaluation économique 5×6 complète et saine, 5/5 paires : profit moyen −49,34 k£/an, IC95 Student [−151,29 ; +52,62] k£/an, 2/5 victoires, p=1. Garde de valeur échouée : −5,7733 % (limite −5 %). Neutralité non validée, verdict brut `diagnostic_only`. Arrêt sans 20×10, aucune adoption ni relance. [Bilan et preuves](c121_air_engine_context_20261002.md). |
| Protocole `mean40` | **Choix avant campagne** | Déjà implémenté et utilisé : décider sa généralisation, règle et graines avant mesure. `signs20` reste le défaut, aucun changement après résultats. |

## 4. En pause ou sous condition — pas de lancement automatique

<a id="c61"></a><a id="c59"></a><a id="c64"></a><a id="c63"></a>
<a id="c58"></a><a id="c39"></a><a id="c41"></a><a id="c44"></a>

| Sujet | Condition indispensable avant reprise |
|---|---|
| V88 goods | Workers A* prêts et régression résolue ; corriger financement étape 1/profit global et faux compteur après simple lancement A*. **Pas de duel V88 avant.** |
| C121 économie / C122 stratégie | Aucun 20×10 pour qualifier l'économie C121 ; exceptions utilisateur limitées à la neutralité de `c121_air_winner_fusion` et à l'évaluation du contexte paire/avion (02/10), voir leurs plans. Aucun nouveau 5×6/20×10 C122 actuel. Classifieur diagnostique seulement ; hypothèse nouvelle distincte des formulations rejetées. Cold start PASS-only puis apprentissage PASS/MAIL, pas retour au catalogue exhaustif à froid. |
| C116 / C118 / C120 | Formulations C116/C118 rejetées ; C120 gelé jusqu'à correction du modèle. R8 préparé n'est pas un lancement dû. |
| V93 / V95 AIR / C97 / B9 | Pas de réactivation globale V93 ni de chooser C97 ; demande résiduelle/valeur marginale à démontrer. B9 diagnostic clos, aucun traitement ouvert. |
| C61 AIR / Route / Rail | AIR : audit flotte intégré, aucun avant/après complet ni profit marginal démontré ; identifier renforts/ventes et mesurer rotations, attente, demande et occupation avant capacités. Pas de plafond arbitraire. [Audit](parallel_fleet_audit.md). Route : réconcilier l'autre session ; Rail : exposition rentable `NOSPOT`/`TRACKFAIL` avant géométrie, conserver modèle d'accélération C41. |
| C59 / C81 | Corréler attente, chargement au départ et profit ; examen des solos défavorables avant éventuel duel C81. Fin du banc C82 ≠ autorisation. |
| C68 pertes historiques | Suivi sans urgence graines 7,42,1337,12345,424242, graine 7 d'abord ; pas de nouvelle adoption. |
| MAIL-only | Analyse disponible, prototype non implémenté ; si repris, aéroports existants seulement, demande/refit MAIL mesurés, aucune infrastructure initiale. Pas un substitut automatique aux pistes AIR rejetées. |
| C63/C58 ; C39/C41/C44 ; C43/E3 ; C42 bis ; C55 | Erreur ou exposition actuelle mesurée ; préserver ledger corrigé, producteurs C77 et politiques abandonnées. Pas de balayage général ni restauration de prédevis/anciens flags. |
| C64 adaptatif | Mécanisme établi, règle pré-enregistrée et nouvelles graines ; aucun réglage sur les graines de découverte. |
| NewGRF/M3 ; risques M2/M5/G2/M6/M7/B6 | Chemin/runtime exposé et validation dédiée ; vanilla ne qualifie pas les refits NewGRF. |
| Eau, jointures, RAM et implantation | Besoin actuel démontré ; accord explicite avant nouveau diagnostic maritime. Pas de Lakes/feeders. |
| Réseau rail partagé | **À la toute fin**, hors file active : exposition passive du raccord au réseau, trains directs, capacité/signalisation avant chantier ; aucun transbordement. |

## 5. Tenue du suivi

1. Une action restante a un statut, une condition de sortie et une source. À la clôture,
   consigner au journal demande, code/branche, changements, tests réellement exécutés,
   artefacts, verdict et limites ; retirer l'action terminée, garder son éventuelle validation.
2. Ne pas importer une ancienne revue comme backlog sans réconciliation. La revue du 30
   remplace pour le suivi courant le « prochain lot 01 » proposé le 26.
3. Dérogations d'activation : [synthèse](journaux/synthese_decisions_2026-09-30.md).
   Elles ne transforment jamais `fail_primary` en succès statistique.
4. Numérotation commune C/V : vérifier les deux préfixes avant allocation. Alias :
   **C88 compagnies ≠ V88 goods ; V95 AIR ≠ V95 scheduler P1/P2/P5**.
   Ne pas renommer les artefacts historiques.
5. Appliquer les validations d'AGENTS.md : contrat et smoke ≠ rentabilité ; diagnostic
   ≠ adoption ; Save/Load si nécessaire. Ne retirer aucune graine historique du banc.

**Dernière mise à jour : 01/10, performances et compléments** : défaut5×6 mesuré,
huit scénarios dirigés R1/R3 et VM48+9 exécutés/validés, deux frontières R1
rechargées. Sources de production inchangées ; année réalisée par ligne et scan
AIR suspendu restent ouverts. Deux répétitions du profil léger passent le filtre
pratique, pas preuve de neutralité. Aucune qualification économique nouvelle.
Les expériences ont leur témoin dans le même arbre, sans bundle immuable ni SHA.
Git/gh absents : publication et qualification GitHub toujours bloquées.
Aucun réglage C115/C121/C122 modifié, aucun commit ni publication.

**Complément 01/10 — lot cache C121** : trois sources de production modifiées,
modèle et défauts inchangés ; cohérence et reconstruction du cache testées dans
le périmètre décrit ci-dessus. Le scan suspendu n'est plus entièrement non
vérifié, mais son état dérivé est jeté au reload ; aucune continuité économique
ni persistance d'apprentissage nouvelle attestée. Suite complète non réexécutée.
