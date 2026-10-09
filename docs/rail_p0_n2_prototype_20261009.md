# P0 RAIL — prototype coopératif N=2 (9 octobre 2026)

## Statut

Prototype expérimental **non adopté**. Réglage `rail_cooperative_n2=0` sur
les quatre difficultés et en mode personnalisé. La décision est d'abord de
mesurer l'admission effective de deux recherches, la conservation des succès
historiques et les coûts ; il ne s'agit pas encore d'une politique économiquement
qualifiée.

Source de la priorité : [`taches.md`](taches.md), P0 RAIL, et
[`rail_p0_blocked_opportunity_20261009.md`](rail_p0_blocked_opportunity_20261009.md).
Sur le diagnostic 5×6, le singleton a refusé 518 visites de projets fret
concurrents correspondant à 64 paires OD, mais **ni la constructibilité de ces
alternatives, ni leur profit net contrefactuel n'ont été prouvés**.

## Mécanisme et invariants

* Un état historique `_railSearch` et au maximum un état secondaire transitoire
  `_railN2Secondary` ; uniquement deux recherches **primaires** distinctes,
  identifiées par `kind,cargo,src,dst` et non une répétition de la même paire.
* Un seul chemin de construction `_consumeRailSearch` et un seul registre
  `_activeWorker`. Le second pathfinder utilise l'initialiseur historique puis
  demeure parqué. Le premier chantier reste prioritaire : B, même si son A*
  finit avant A, n'est pas exécuté avant consommation de A.
* La routine V89 existante continue de borner **globalement** les tranches par
  `AIController.GetOpsTillSuspend()` ; l'alternance des états se fait à
  l'intérieur de `_advanceRailSearchSliceWithLedgers`. Aucun deuxième budget de
  tick, aucun second worker.
* Avant une éventuelle pose de B, comparaison `_tooClose` contre les lignes
  réellement construites, puis revalidation sous `AITestMode` de la trésorerie,
  disponibilité d'un train, industries (avec destination town autorisée),
  gares, voie et dépôt. Si ce plan préparé est périmé, refus sans tentative de
  pose. La qualification économique doit également vérifier les refus
  conservateurs de cette revalidation.
* Les recherches C121 de préparation de première année, les chaînes V88,
  upgrades, stock C80 et workers rail C80 restent sur les chemins historiques.
  N=2 est automatiquement désactivé avec le worker/stock C80, la supersession
  `origin_reuse` et la réparation V131. Un upgrade ne doit jamais démarrer
  tant que B est encore parqué.
* Les pathfinders Squirrel/C++ ne sont pas sérialisés : `Save` ne persiste que
  le signal `railSearchPending` (A **ou** B). `Load` abandonne A et B et force
  l'invalidation/régénération du portefeuille. Les anciennes sauvegardes
  restent compatibles.

## Instrumentation et validation

`RAIL_N2 phase=second_start`, `phase=second_ready` et `phase=promote` sont
émis sous `decision_log=1`. Les signatures existantes `RAIL_PREASTAR_*`
(`probe_rail_preastar=1`) et `RAIL_ATTEMPT` complètent l'analyse par RID, A*
`OK`, chantier réalisé, échec, coût et date. **Attention : les deux états
progressent avec les mêmes opcodes disponibles, mais l'identité du travail
dans les anciens agrégats singleton P5/V89 est à clarifier ; ne pas en tirer
un bénéfice d'opcodes sans comptage par état.**

Contrats hôte : `sweeps/test_rail_cooperative_n2.py`, suite existante
`test_b5_rail_persistence.py`, `test_c121_air_first_year_rail_prep.py`,
`test_c80_rail_stock_worker.py`. Un smoke moteur n'est pas un A/B de valeur.

### Résultats vérifiés (prototype au 09/10)

* Tests Docker ciblés : N=2 **9/9**, B5 persistance **11/11**, préparation
  C121 **9/9**, worker C80 **18/18**. Ce dernier contrat a été ajusté à la
  signature de revalidation optionnelle et au 4e site d'appel N=2 ; une
  assertion déjà obsolète a également été réconciliée avec la mémoire
  `RAIL_FREIGHT_TRKFAIL_MEMORY` présente dans `builder_rail.nut`.
* Smoke 1×3 `rail_cooperative_n2_smoke_1x3_20261009` : les deux bras
  terminent sains, 1972 `profit_year` 3 397 464 £ OFF et 3 437 685 £ ON ;
  **non qualifiant et antérieur à l'ajout de la revalidation B**.
* Duel figé **1×5 diagnostique** `rail_n2_exposure_1x5_20261009_r3`
  (bundle `51ea6fff…`, source OFF/ON commune, `decision_log=1`,
  `script_debug=4`), 2/2 parties complètes. Log variant
  `results/rail_n2_exposure_1x5_20261009_r3_engine/n2_seed42_r0.log` :
  **3 `second_start`, 2 `second_ready`, 2 `promote`, 0 `second_discard`**.
  Le **05/12/1972** B pax `54044→59980` devient `ready` à 62 itérations
  pendant que A pax `59980→44107` reste active. A finit `OK` côté A* mais
  échoue `TRKFAIL` à la pose le **15/05/1973** ; B est promue à cette date,
  puis effectivement construite (`RAIL_ATTEMPT ok=1`, 41 396 £ de coût)
  le **21/06/1973**. Un autre B freight démarre le 04/08/1973,
  A échoue `STNFAIL` le 09/09/1974 ; troisième B démarre 11/11/1974,
  prêt 04/12/1974. La concurrence A* est donc **effectivement exposée**.
  Opex variante−référence `profit_year` fin 1974 **+88 596 £/an**,
  company_value **+1,77 %** ; **N=1**, verdict `diagnostic_only`, aucun
  effet moyen ni statistique établi.
* `sweeps/save_load_roundtrip.py` seed42, phase A 4 ans, reprise
  d'une sauvegarde datée **1973-03-01** pour une année : **status=OK**,
  `LOAD_RECONCILE` observé et 13 sauvegardes produites après reprise.
  Le marqueur `rail_search_dropped=0` et l'absence de `RAIL_N2` dans ce
  parcours **ne démontrent PAS un Load avec les deux recherches présentes** ;
  la partie sans AAA est une autre trajectoire. Le banc détecte par ailleurs
  une compagnie fantôme au reload, sans effet annoncé sur les indicateurs
  de la compagnie principale : conserver cette réserve méthodologique.

## Conditions avant la porte économique V102

1. Démontrer par événements moteur que deux **RID distincts** ont effectivement
   coexisté et avancé pendant un blocage autrement `search_in_progress`.
2. Vérifier sur plusieurs graines la conservation des A* `OK` historiques,
   le temps d'achèvement de A, les échecs de B et les constructions physiques
   **supplémentaires** réellement livrées, sans extrapoler les scores prédits.
3. Comparer le budget d'opcodes global, la cadence AIR/fleet, la revalidation
   et un aller-retour Save/Load avec B actif.
4. Si le prototype respecte ces invariants et expose une opportunité viable,
   seulement alors porte A `gain_short` **40×3**, puis B `non_erosion` **20×10**
   si la porte A passe, sur un bundle source OFF/ON identique.

Aucun défaut comportemental ne change ; aucun commit/push implicite.

## Revue de robustesse complémentaire (09/10, postérieure au duel r3)

Les résultats économiques r3 ne qualifient pas exactement ce nouveau code.

* La revalidation de B utilise maintenant le devis physique
  `OpexSimulateRailInfraCost` du constructeur : démolition simulée des
  emprises, gares et tracé sur la carte courante. Le contrôle C80 était
  susceptible de rejeter des plans avec terrain nettoyable ou voie déjà
  présente. Le devis ne teste pas le dépôt ; la construction réelle et
  son rollback restent responsables de cette étape.
* Un manque transitoire de trésorerie (y compris détecté pendant le devis)
  ou de slot train se distingue d'un plan périmé. Avec C41 cash-release,
  le slot est libéré et le plan B invalidé pour imposer un nouveau calcul
  après une admission ultérieure ; sinon B attend. Aucun abandon durable
  de la paire n'est enregistré par ce préfiltre.
* `Save()` signale désormais une recherche pendante même pendant le
  staging de B, lorsque A n'est que dans une variable locale et que
  `_railSearch` est momentanément vide.
* Sous `rail_cooperative_n2=1,decision_log=1`, les événements
  `RAIL_N2` portent un `rid` stable, `peer` à l'admission B,
  `search_done` (tranches, itérations, opcodes A* attribués à chaque
  recherche) et `build_done`. Les frais de préparation, de revalidation
  et de logging, et l'effet sur AIR/fleet, restent à mesurer à part.

Deux contrôles structurels ajoutés portent le total N=2 à 11 ; la
validation moteur de ce code et le diagnostic multi-graines restent
nécessaires. `sweeps/rail_n2_reload_saved.py` peut recharger une
sauvegarde de duel préservée dans une fenêtre A+B et exiger
`rail_search_dropped=1`. Ce scénario n'a pas encore été vérifié sur moteur.

### Diagnostic suivant pré-enregistré (avant lancement)

* Trois graines **42, 100, 999**, cinq ans, une répétition, 3 paires de
  duels contre AAAHogEx, arbre local figé au lancement ; OFF
  `OpexAI[rail_cooperative_n2=0,decision_log=1]` contre ON
  `OpexAI[rail_cooperative_n2=1,decision_log=1]`, tous autres réglages
  communs et inchangés. `--script-debug`, sauvegardes mensuelles conservées
  hors bundle, une campagne à la fois. Règle descriptive seulement,
  `profit_year` et `company_value` finaux, santé complète, couverture
  des trois paires.
* Mécanisme : `second_start` avec `rid != peer`, deux `search_done`
  attribuables, premier chantier avant B, absence de double pose, sorties
  `second_discard/second_wait`, nombre de constructions réussies et
  opérations A* par RID. Comparer aussi AIR/fleet au niveau physique ;
  le coût total d'opcodes n'est pas identifié par la seule somme des
  `slice_ops`.
* Conserver un checkpoint de la variante seed42 dans la fenêtre A+B
  observée au duel précédent (05/12/1972 au 15/05/1973), et vérifier
  par `rail_n2_reload_saved.py` un rechargement positif
  `rail_search_dropped=1` et une reprise sans erreur moteur. Cette fenêtre
  doit être **reconfirmée dans le log de la nouvelle campagne**.
* Aucun seuil statistique d'adoption pour cette étude 3×5. Si le mécanisme
  est sain et convaincant, protocole V102 ultérieur 40×3 puis 20×10
  seulement si A passe. Le défaut reste désactivé.

### Résultat du premier diagnostic après revalidation : r4

Campagne `rail_n2_diag_3x5_20261009_r4`, bundle
`f67195be0ba88072be28e348060f5814abd08360a13d3e417bb54ead0d3801d7`,
manifest `f8f4312a366c659569edaf0be55d234313b9f9daa3d466dd4266f82a938f55ec`.
6/6 parties complètes et saines ; 3/3 victoires Opex variante contre
Opex référence en `profit_year` terminal, moyenne **+191 497 £/an**,
médiane **+196 710 £/an**, IC95 Student **[−16 082 ; +399 076] £/an**,
valeur des compagnies **+6,244 %** (ratio des moyennes). Verdict brut
`diagnostic_only`, aucune adoption. Le smoke solo 1×1 antérieur
`rail_n2_smoke_postreview_1x1_20261009` était sain mais donnait
**−112 702 £/an** pour ON dès la première année : trajectoires divergentes.

Les journaux r4 révèlent un défaut de priorité plus grave que les écarts
statistiques : graine 100, le B RID4 est promu le 31/05/1973, puis reçoit
un nouveau B RID5 qui termine avant lui. Quand RID4 termine son A*
le 20/10/1973, son ancien marqueur `railN2Second=true` provoque des
`second_ready` répétés pour RID4/RID5. Cette oscillation invalide la
preuve de FIFO stricte pour r4. **Correctif ultérieur :** à la promotion,
`railN2Second` devient false (priorité primaire), tandis que le marqueur
indépendant `railN2NeedsRevalidation` maintient la revalidation physique
de tout projet originellement B. Une nouvelle campagne distincte doit
tester ce changement ; **les chiffres r4 ne s'y transfèrent pas**.

Save/Load r4 : variante seed42, `results/rail_n2_diag_3x5_20261009_r4_saves/1/save/000000037.sav`
du **01/03/1973**, comprise entre `second_start` du 05/12/1972 et
`promote` du 15/05/1973, a été rechargée via
`sweeps/rail_n2_reload_saved.py`. Résultat **OK**, `LOAD_RECONCILE`
avec `rail_search_dropped=1`, 13 sauvegardes post-reprise, aucune
erreur moteur détectée. Preuve positive pour A+B effectivement présents
dans la sauvegarde r4 ; elle ne teste pas encore le nouveau marqueur de
priorité lors d'une deuxième admission.

### Validation du correctif FIFO : r5, et protocole économique suivant

Diagnostic `rail_n2_diag_fifo_3x5_20261009_r5`, bundle
`4d510cbfd465b4dc163323c028850be33616e9677f9d64f1a6eb29dc67acc442`,
manifest `fe9d7317813d60f8bd5fcbf1cf918e04f49dca7dc727fffb460e8482e40e5f5b`.
6/6 parties complètes et saines, 3/3 variantes gagnantes, delta
`profit_year` moyen **+249 786 £/an**, médian **+287 946 £/an**,
IC95 Student descriptif **[85 281 ; 414 291] £/an**, garde valeur
**+8,079 %**. Aucun test formel V102 sur ces trois graines :
`diagnostic_only`.

Trace `results/rail_n2_diag_fifo_3x5_20261009_r5_invariants.json` :
sur trois graines, **9 admissions B**, dont **7 second_ready**,
**7 promotions** et **2 second_discard** (graine100 : deux too_close),
aucun RID `second_ready` en doublon, aucune construction B avant
consommation du primaire enregistré. En r4, la même vérification trouvait
des doublons sur RID4 et RID5 seed100. Les sommes d'opcodes de recherche
A* ON des seules recherches terminées sont de l'ordre de 13,14 M
(graine42), 37,71 M (100), 4,56 M (999). Ces sommes excluent setup,
revalidation, toutes autres fonctions et recherches encore en cours ;
ce ne sont ni une économie ni un total global comparable à OFF.

Nouveau reload de la variante r5 seed42 le **01/03/1973** dans la
fenêtre A+B : `results/rail_n2_active_save_load_fifo_20261009_r5.json`,
`status=OK`, `rail_search_dropped=1`, 13 sauvegardes après rechargement,
aucune erreur moteur. La reconstruction est démontrée pour ce checkpoint,
pas pour chaque état intermédiaire ni pour le court staging.

**Pré-enregistrement porte A V102 après exposition r5** : code actuel
N=2 OFF-by-default, ancien défaut **0**, candidat **1**, mêmes sources
et réglages annexes par bras ; `decision_log=0` commun pour écarter le
coût de la sonde. `gain_short`, **40 graines canoniques × 3 ans**,
une répétition, 80 duels OpexAI vs AAAHogEx sur carte partagée
(160 compagnies IA). Métrique primaire Opex variante−référence
`profit_year` terminal, seuil moyen **≥4 %** du profit moyen référence,
Wilcoxon exact bilatéral **p<0,05**, IC95 bootstrap 20 000 rééchantillonnages
(graine 0) borne basse **>0**, garde ratio des valeurs moyennes
**≥−5 %** ; couverture 40/40, santé/horizon annuels complets,
`policy_comparison.verdict=pass` obligatoire. Ressources locales
10 CPU, 8 GiB RAM/swap, au plus 10 workers ; une campagne à la fois,
bundle figé. En cas d'échec primaire, arrêter la qualification,
défaut 0 inchangé. Si A passe, porte B `non_erosion` **20×10**
selon V102. Ni les 3×5 ni les opcodes de RID ne sont des critères
d'adoption.

### Porte A V102 formelle : r6 — `fail_primary`

Campagne `rail_n2_gain_short_40x3_20261009_r6`, bundle figé
`4d510cbfd465b4dc163323c028850be33616e9677f9d64f1a6eb29dc67acc442`,
manifest `ddbe34bf87b41041abf1f1d8d0d12171a00e3f6eb35055451e64bac074b8126b`,
image Docker digest
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
HEAD `49616b0cf83c721e51b842f507eb1471a775f2d1`, modifications locales
figées. Référence `OpexAI[rail_cooperative_n2=0]` et variante
`OpexAI[rail_cooperative_n2=1]`, journal de décisions au défaut OFF
dans les deux bras, même AAAHogEx et autres réglages.

Porte `gain_short` **40 graines canoniques × 3 ans**,
une répétition, **80 duels** ; **80/80 parties saines**,
**40/40 paires complètes** ; `comparison_complete=true`,
`adoption_sample_complete=true`, `metric_coverage_complete=true`.
Delta terminal `profit_year` Opex variante−référence :
**−47 870,4 £/an** de moyenne, **−42 690,5 £/an** de médiane,
V/D/E **15/23/2**, Wilcoxon exact bilatéral **p=0,118111**,
IC95 bootstrap **[−111 082,675 ; +15 248,4] £/an**,
seuil de +4 % **+79 122,084 £/an**.
Ratio des valeurs moyennes **0,979289**, soit **−2,071118 %**
(garde −5 % respectée). `primary_pass=false`,
`value_guard_pass=true`, verdict brut
`policy_comparison.verdict=fail_primary`.

Preuves :
`results/rail_n2_gain_short_40x3_20261009_r6.json`,
`results/rail_n2_gain_short_40x3_20261009_r6.jsonl`,
`results/rail_n2_gain_short_40x3_20261009_r6.manifest.json`
et bundle associé.

**Décision : ne pas adopter N=2.** Arrêt de la porte B 20×10
selon le protocole puisque A échoue. Les résultats positifs sur
trois graines à cinq ans ne requalifient pas cette porte.
L'expérience reste désactivée par défaut
(`rail_cooperative_n2=0`) ; le goulot de développement du fret
après 1971 demeure une tâche distincte. Aucun commit/push.
