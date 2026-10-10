# AIR — coûts réels des aéroports et marge de risque (8 octobre 2026)

## Décision et périmètre

**Prototype existant corrigé, conservé OFF, non qualifié économiquement.** Les deux réglages
`air_site_cost_quote=0` et `air_site_cost_margin_pct=0` sont inchangés aux quatre difficultés.
Le premier active l'ajout du devis de terrassement et des arrêts joints au capital du
projet C121 ; le second est un pourcentage **du coût des sites neufs** ajouté à 2 000 £.
Le prototype de devis, les sondes, leur décodeur et les tests existaient déjà avant ce
chantier. Le nom V126 est partagé avec la **réadmission des villes AIR déjà servies** ;
les résultats de cette dernière ne qualifient pas le devis.

## Parcours réel des fonds

Le prix catalogue d'un nouvel aéroport est `plan.airport.price`, multiplié par le
nombre d'extrémités **non réutilisées**. `OpexC121PrepareEngineStatic` construit
`state.airportCapital`. Le modèle économique ajoute les avions réellement prévus
(au démarrage, puis éventuellement la flotte N=2) ; le refit de construction est
`BuildVehicleWithRefit` et les clones utilisent des commandes distinctes. Les
plantations dans `OpexBoostTownRating` peuvent être dépensées pendant les refus
municipaux. Le devis `OpexAirV95LevelCost` simule `AITile.LevelTiles` sur l'emprise
exacte ; `OpexAirLevelFootprint` fait ensuite le vrai terrassement, puis
`AIAirport.BuildAirport` facture la station. Pour chaque nouvel aéroport seulement,
`OpexAirBuildJoinedStops` peut poser au maximum deux arrêts traversants joints.

| Aéroports neufs | Prix catalogue | Nivellement devisé | Arrêts joints devisés* | Marge historique |
|---|---|---|---|---|
| 0 (hub→hub) | 0 | 0 | 0 | 2 000 £ |
| 1 (hub→site) | 1 × prix | 1 devis | jusqu'à 2 × 2 250 £ | 12 000 £ |
| 2 (newpair) | 2 × prix | 2 devis | jusqu'à 4 × 2 250 £ | 30 000 £ |

* Coût **modélisé maximal sur les limites de pose**, distinct de l'argent dépensé.
La mesure B9 antérieure indiquait 450 à 2 250 £ par arrêt ; le forfait expérimental
initial de 300 £ était inférieur même à cette borne basse. Ces observations ne
garantissent pas un plafond futur. Un devis impossible est `-1` ; il n'est pas une
dépense nulle : la marge historique est conservée dans ce cas. Une extrémité
réutilisée est codée `-2` dans la sonde et **ne déclenche aucun devis**.

`OpexProjectFromAir` et la branche C111 ajoutent la marge à `budgetCapital` et à
`decisionFinanceCapital`, avec `immobilise` lorsque positif. L'arbitrage du
portefeuille et ses scores utilisent ces capitaux. Au dernier garde d'exécution,
`task_air.nut` vérifie `capital + OpexCashReserve() + OpexAirRequiredMargin(...)`.
Cette réserve de caisse ne se confond ni avec l'immobilisation économique, ni avec
la marge de chantier. C83 et les contrôles physiques restent inchangés.

`OpexBuildAirRoute` mesure les vrais travaux et frais de repli dans `AIAccounting`.
Les sorties anticipées `PREA/PREB` précèdent ce compteur ; ensuite `AFAIL/BFAIL`,
`STNFAIL`, `HANGAR`, `PLANE`, `ORDFAIL`, `START` peuvent laisser des dépenses.
`OpexAirRollback` peut supprimer des infrastructures/véhicules et récupérer un
montant ; si la maintenance des infrastructures est désactivée, une station A
orpheline peut être conservée sur `BFAIL`. Le coût net comptabilisé ne représente
donc pas nécessairement la perte définitive, ni le capital immobilisé jusqu'à la
première recette. `OpexAirReconcileActualBuild` réinjecte le capital réel après
succès. Le devis expérimental inclut aussi l'amortissement correspondant quand
`INFRA_AMORT_PCT` est positif (0 au défaut courant).

## Défauts corrigés le 8 octobre

1. `AIR_SITE_COST_QUOTES` réutilisait les devis **365 jours** malgré les travaux
   possibles sur les sites. Désormais cache **journalier** par ancre et type,
   table réinitialisée chaque jour et entrée immédiatement invalidée lorsque
   `OpexAirInvalidateCachedSite` constate une contradiction de chantier. Le
   concurrent peut encore modifier une emprise **dans la même journée** ; la
   constructibilité reste contrôlée séparément. Le cache n'est pas sauvegardé.
2. Un devis `-1` était traité comme coût connu nul tout en permettant de ramener
   la marge de 12/30 k£ à 2 k£. La marge historique prend désormais le relais
   si l'un des nouveaux sites est indévisable ; les coûts connus des autres
   sites restent dans le capital calculé.
3. `OpexAirBuildJoinedStops` exécutait des `BuildDriveThroughRoadStation` en
   `AITestMode` sans `AIAccounting` imbriqué : les **coûts simulés gonflaient**
   `actualCost` et `joinedStopCost` sans décaissement, puis pouvaient fausser
   la réconciliation économique. Le bouclier comptable existant du sondage
   d'aéroport est reproduit pour les essais d'arrêts **uniquement** quand le
   devis ou la sonde financière est activé. Chemin OFF historique préservé.
4. Le forfait d'un arrêt joint est passé de 300 à **2 250 £** pour le devis
   expérimental, selon le maximum constaté par B9, sans prétendre modéliser
   précisément chaque arrêt. `margin_v126` journalise maintenant le repli si
   un devis a échoué ; le pourcentage reste expérimental et à 0 au défaut.
5. L'amortissement annuel de l'infrastructure suit désormais l'ajout de
   capital coté lorsque le mode expérimental est activé.

## Preuves et limites du calibrage

Le **résumé** `afm_expo_6s_y3` (6 graines × 3 ans, 6 octobre), conservé dans
`docs/taches.md`, rapporte 35–74 jours par graine avec AIR sans sélection à cause
de la marge, essentiellement en 1970–1971, déficit médian de 4–12 k£. Le ratio
réel/prévu historique est médiane 1,00, p90 1,15, maximum 1,74 ; 2,9 % dépassent
la marge. On relève 47 échecs / ~370 k£, dont ~343 k£ en `BFAIL`, 2,8 % de
brèches de réserve avant recette et un premier revenu à 43 jours de médiane
(95 jours pour deux nouveaux aéroports). Les épisodes de sélection sont **répétés**
et ne désignent pas autant de projets distincts.

Les **artefacts bruts** `afm_expo_6s_y3` n'ont pas été retrouvés dans `results/`,
`evidence/`, `docs/` ou les arbres voisins accessibles lors de cet audit. Il
n'existe donc pas de ventilation recontrôlable par graine, type d'aéroport,
nombre de sites neufs, échec et année. Surtout, les ratios p90 1,15 et max 1,74
comparent l'exécution à **l'ancien capital sans devis** ; ils ne mesurent pas le
risque résiduel après nivellement et arrêts joints. Le faux coût des essais de bus
peut en plus biaiser ces ratios. Choisir 15 % d'après p90 serait injustifié.

Le décodeur `sweeps/parse_air_finance_margin.py` sait déjà lire les champs V126
`quote_a/b`, `quote_fail`, `stops_model`, `site_cost`, `extra`, `margin_legacy`,
`margin_v126`, `levelA/B`, `airportA/B`, `planes`, `stops` sur `AIR_FINANCE_TRY`.
Il calcule les résidus sur les **succès documentés**, avec divers seuils de
pourcentage, mais les valeurs des tests sont synthétiques. Il ne reconstitue
ni l'identité unique des projets ni les `AIR_FINANCE_SELECT` de tous les jours ;
les échecs, coût irrécupérable et remboursements doivent donc être étudiés à
part, sous peine de biais vers les chantiers qui réussissent. Aucune distribution
V126 réelle n'est disponible pour choisir le pourcentage.

## Validation, exposition et décision

Contrats de réglage, construction, cache et finance :
`sweeps/test_v126_air_site_cost_quote.py` ; décodeur :
`sweeps/test_parse_air_finance_margin.py` ; sonde :
`sweeps/test_air_finance_margin_probe.py`. Les tests Python ne compilent pas
Squirrel. Les réglages OFF n'effectuent aucun devis supplémentaire et conservent
les marges historiques. Le cache est transitoire et recalculé après chargement ;
la validation moteur Save/Load reste à produire.

**Smoke apparié technique terminé** : `air_site_quote_fix_smoke_1x1_20261008_r2`,
un an, graine 42, deux duels complets/sains, même bundle
`406219ec402ce1547a382008ae91c2e0fbd758a33d6fbe118588af1d7fe6f2de`,
manifeste `1991ff9510274accc88eb343b663b21c341a53819e56d653fb8d05d4ce4252b7`.
Référence `air_site_cost_quote=0`, variante `=1`, sonde financière à 1 dans
les deux bras et pourcentage commun à 0 ; tous les autres réglages aux défauts.
Profit Opex de l'année 1970 : 408 296 → 466 958 £, delta **+58 662 £** ;
valeur de compagnie 366 584 → 416 944 £ ; installations aéroportuaires
en 1970 **15 → 19**, soit quatre de plus sur cette graine, mais **20 → 21**
au point terminal. Véhicules Opex 16 → 17. Aucune de ces différences sur une
seule graine ne permet de conclure à un gain économique, une protection de
caisse suffisante ou une augmentation stable des ouvertures rentables.
Verdict moteur `diagnostic_only` (1/1 paire complète, horizon et échantillon
insuffisants pour V102). La première tentative sans suffixe `_r2` a été
rejetée avant partie par validation de réglage redondant.

**Limite de télémétrie** : les deux fichiers
`results/air_site_quote_fix_smoke_1x1_20261008_r2_engine/*.log` sont vides
(0 octet). Malgré l'exécution Squirrel saine et la différence de trajectoire,
les événements `AIR_FINANCE_TRY` et compteurs `AIR_PLAN_PERF c121_static_ops`
ne sont pas exploitables sur ce smoke. Un **rejeu r3 du même bundle, avec
`--script-debug` sur les deux bras** produit deux journaux de 427/448 ko.
Les deux duels sont à nouveau complets et économiquement identiques à r2,
verdict `diagnostic_only`, manifeste
`2d0574e097400f218d000d5d5161504a8d347b23c5b0c6564144665ee62463c0`.

Le décodeur `sweeps/parse_air_finance_margin.py`, appliqué **séparément par
bras** aux logs r3 (ne pas utiliser ses agrégats mélangés), donne :

| Graine 42, année 1970 | Référence devis OFF | Variante devis ON |
|---|---:|---:|
| Événements `AIR_FINANCE_TRY` | 76 | 12 |
| `built` | 10 | 11 |
| `failed` | 2 (BFAIL 27 300 £, AFAIL 898 £) | 1 (AFAIL 898 £) |
| `refused_margin` | 64 | 0 |
| Coût comptabilisé des échecs | 28 198 £ | 898 £ |
| Première recette observée, médiane | 100 jours | 83,5 jours |
| Brèches de réserve observées | 0 | 0 |
| Devis V126 présents sur les `built` | 10/10 passifs | 11/11 actifs |
| Résidu réel après devis, médiane | −8 349 £ | −7 215 £ |
| Résidu réel après devis, p90 | −6 881 £ | −5 085 £ |

Les 64 refus sont des **événements répétés de sélection**, pas 64 projets
uniques. Le devis ON couvre 21 extrémités neuves réussies, sans `-1` :
écart `level` réel−devis médian/p90 = **0/0 £** ; dans les 11 réussites,
résidu maximal +810 £ (2,4 % du coût site), aucun dépassement du plancher
de 2 000 £. Les arrêts joints mesurés coûtent médiane **225 £ par aéroport
neuf** (max 300 £), contre réserve modélisée de **4 500 £ par site**
(deux arrêts × 2 250 £). Ce devis est volontairement prudent et surestime
fortement le coût des arrêts sur cet échantillon ; les résidus négatifs ne
justifient aucun pourcentage universel. Les échecs ne sont pas intégrés
au calcul des quantiles sur les constructions réussies : biais de sélection
et risque BFAIL résiduel. Il reste impossible de séparer le « jour gagné »
sur les **mêmes projets** : la trajectoire de sélection a changé.

Une ligne `AIR_PLAN_PERF` comparable avant divergence rapporte pour le premier
scan (32 évaluations C121, 40 sites) `c121_static_ops` **41 584 OFF → 42 000 ON**,
soit **+416 opcodes** sur les calculs statiques ; `total_ops` du scan
1 248 937 → 1 246 609, soit −2 328 opcodes. Il s'agit d'une **mesure de
ce premier scan**, et non du surcoût complet de l'année ni d'un ratio
causal à décisions constantes. Les scans futurs divergent ; le budget
opcode global reste non qualifié.

**Save/Load du devis ON contrôlé** avec `sweeps/save_load_roundtrip.py` en
Docker local, graine 42, partie initiale 1 an et poursuite 1 an après reprise
de la sauvegarde datée du **01/07/1970**. 13 sauvegardes à chaque phase,
marqueur positif `LOAD_RECONCILE saved=5 kept=5 dropped=0`, aucun motif de
plantage recherché, rapport `results/air_site_quote_roundtrip_20261008.json`
`status=OK`. Valeur Opex 6 349→1 340 451 £, stations 10→47, véhicules
22→86 entre l'état sauvegardé et la fin de reprise : vérification de
continuité, **pas une comparaison économique**. Le harnais détecte une
compagnie humaine fantôme supplémentaire lors de `-g` ; ses statistiques
n'ont pas été attribuées à Opex, mais l'essai reste **un contrôle de reprise
avec ce biais d'environnement**, pas une preuve d'identité des trajectoires.
Le cache V126 est transitoire/reconstructible d'après le code ; son contenu
exact avant/après chargement n'est pas mesuré séparément.

Pas de porte A ni B, aucune adoption.

Nombre unique de projets AIR supplémentaires, jours gagnés avant recette
pour des projets comparables et coût des retards : inconnus. La borne
historique de profit retardé ~25 k£/graine (~1,6 %) reste indicative.

### Conditions avant la qualification

Sur Docker local libre (10 CPU, 8 Go, 10 workers au maximum), figer **un seul
bundle** incluant les fixes et produire une campagne instrumentée avec la
sonde `probe_air_finance_margin=1`, devis actif et marges explicites. Mesurer
les écarts devis/réel **par site** et par 0/1/2 nouveaux aéroports, incidents
et pertes nettes, distributions des résidus et des dépassements, cache et
**opcodes** `C121` du devis à entrée comparable, financement quotidien,
ouvertures 1970/1971 et première recette. Réduire les épisodes répétés à des
fenêtres/identifiants de projet vérifiables. Choisir ensuite une marge simple
capable de couvrir le quantile résiduel ET la perte en cas d'échec, sans
recopier aveuglément 15 % de l'ancien coût. Tester en smoke apparié et vérifier
le Save/Load. Porte A `gain_short` 40×3 uniquement après exposition réelle
et hypothèse de gain préalable crédible (IC95 bootstrap borne basse >0,
Wilcoxon p<0,05, gain moyen ≥4 %, valeur ≥−5 %). Porte B `non_erosion` 20×10
seulement si A passe. Défauts inchangés jusqu'à qualification et adoption.

**Prolongement 6 graines × 3 ans du 08/10 :** la variante perd en moyenne
**70 729 £/an**, avec 3 victoires et 3 défaites, IC95 bootstrap englobant
zéro ; 58 échecs de chantier AIR et 7/149 dépassements de 2 000 £ sur les
seuls chantiers achevés avec nouveau site. Aucune marge résiduelle sûre
n'est identifiable ; le devis reste OFF, sans qualification V102.
Les 12 duels et l'analyse des devis/coûts par graine sont documentés dans
[AIR — risque résiduel 6×3](air_risque_residuel_6x3_20261008.md).
