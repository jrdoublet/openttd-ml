# AIR-ROI-RENFORT-1 — étape 1 : audit des renforts sans nouveau banc (22/10/2026)

> **ARCHIVE HISTORIQUE — étude hors-jeu non adoptée.** Cet audit décrit les traces et le code de l'arbre expérimental local du 22/10/2026, dont les modifications Squirrel non commitées ne sont **pas** intégrées par cette publication. Le script `sweeps/audit_air_roi_renfort1.py` et ses tests synthétiques sont seuls archivés avec ce rapport ; les journaux lourds cités sous `results/` ne font pas partie du dépôt publié. Aucun rendement marginal causal ni changement de politique AIR n'est qualifié par cette archive.

## Périmètre, verdict

Audit **strictement rétrospectif** des cinq logs `results/air_flotte1_shadow_causes_5x6_20261022_engine/air_flotte1_shadow_seed{42,100,999,1234,5678}_r0.log`, campagne de six années 1970–1975, même bundle `b7b8696e4c2f16b3e56ed7f1edf140c77550e1f12f794c7472bc6ea03ead2113`. Les **40 logs** `results/rail_cal4_40x10_multimodal_pc_20261021_engine/reference_seed*_r0.log` sont analysés **séparément**, car ils viennent d'autres parties. Aucun nouveau jeu, aucun changement de code Squirrel, aucune qualification économique.

**Verdict :** le passage de la marge C121 pré-V161 au profit finalement classé est reconstitué pour les **2 388 tentatives de renfort** et le score C69 est retrouvé pour **2 388/2 388**. Le plafonnement V161 est observable et très fort, mais son écart avec le modèle **n'est pas une erreur de prédiction vérifiée** : ni le profit causal de l'avion ajouté, ni les variables physiques/concurrentielles nécessaires à sa calibration ne sont mesurés simultanément. Le ROI marginal vrai reste **non identifié**.

## Chaîne exacte de décision vérifiée dans le code

1. **C121 / amont de V161.** `projects_builders.nut:143-207` valorise `entry.want` avions : si `targetAirPlanes > have`, `c121MarginalProfit`/`c121MarginalRevenue`, depuis le modèle au démarrage puis marges historiques quand elles sont disponibles, avec correction de réalisation pour le cold-start ; sinon profit moyen `lastProfit/have` ou secours `predRevenue - predRunning`. L'épisode ne journalise ni `have`, ni `c121MarginalSamples`, ni quelle **branche amont** a fourni cette marge. `v161_model` est la marge **par avion avant plafond** ; `v161_model × (spend / unit_price)` reconstitue le profit modèle du lot. Ce montant n'est pas un revenu constaté après le nouvel achat.
2. **V161.** `air_fleet.nut:236-257` prend le minimum entre le modèle par avion et l'a priori `V161_PRIOR_OWN − V161_PRIOR_NEIGHBOUR × v161Neighbours − c121VehicleAmortPerPlane`. La valeur finale, multipliée par le nombre d'avions, est `raw_profit` dans `AIRF1_BUY` (`projects_builders.nut:208-251`). `v161_src=prior` atteste le plafonnement ; `v161_src=model` atteste que le modèle est resté inférieur/égal à l'a priori. Les voisins et l'amortissement ne sont **pas publiés** dans le snapshot : impossible de refaire indépendamment l'a priori terme à terme.
3. **C70.** `projects_models.nut:160-180` publie `calibrated_profit` après `OpexC70Profit` : si la valeur V161 est le modèle, `v161Calibrate` fait appliquer le facteur AIR C70 ; si V161 vient de l'a priori, `profitIsObserved` prévient cette calibration. Les deux profitabilités, avec leur provenance, restent distinctes ; la médiane `C70 = calibrated/raw` vaut **1,000** sous `prior`, **0,375** sous `model` dans ce panel.
4. **C69.** `projects_finance.nut:8-36` : pour un renfort, `finance = budgetCapital = prix_du_lot + 1 000 £`, tandis que `spend` = capital prévu sans ce tampon. Le score de sélection `fundScore` utilise `1000 × calibrated_profit / max(finance, K_dec)` pour ces projets C121 (`projects_selection.nut:779-839` et `OpexProjectScore` dans `projects_models.nut:186-190`). **2 388/2 388 scores recollent à ±0,03 point de ‰**. `k_dec_snapshot` porte la dernière sélection, pas nécessairement un recalcul à l'achat : décalage médian **4 ticks**, et **2 388/2 388** avec tick de sélection antérieur. `raw_roi` est le ROI entier du lot après V161, **sans** le dénominateur C69.
5. **C77 / exécution.** `projects_selection.nut:965-1055` insère d'abord selon le niveau défensif C77, ensuite selon score/revenu et règles complémentaires. `AIRF1_BUY.rank` est le **rang effectif du portefeuille** au point d'exécution, non l'ordre d'un ROI pur. `AIRF1_BUY.fund_score` est le score **stocké** de la sélection ; le niveau C77 et la fraîcheur détaillée du candidat ne sont pas loggés. `task_projects.nut:203-299` vérifie état de la ligne, nombre de véhicules et caisse **avant** le hook shadow, puis appelle `OpexAirAddPlane`. La sonde relève la réserve, `cash`, `avail`, `unit_price` coté projet, capital prévu et résultat. Le moteur peut choisir un autre moteur, se rabattre sur l'ancien ou échouer (`air_fleet.nut:70-163`). `cash_before − cash_after` est un **écart de trésorerie** et non une facture certifiée (ni le prix réel exact de l'appareil).

Il faut distinguer trois dénominateurs : ROI modèle et ROI après V161 calculés sur `spend` (capital prévisionnel), ROI C70 affiché sur `finance` (capital de financement avec tampon), et `fundScore` sur `max(finance, K_dec)` avec priorité C77 additionnelle au moment du classement. Aucun de ces ratios n'est le rendement contrefactuel du prochain avion.

## Couverture et résultats (5 graines × 6 ans)

| Mesure | Relevé |
|---|---:|
| Épisodes AIRF1 complets (BUY, CLOCK, READY, OUTCOME) | **2 506 / 2 506** |
| Tentatives renfort C121 ; renouvellements V252 | **2 388 ; 118** |
| Renforts réellement ajoutés ; V252 réussis | **311 ; 118** |
| Renforts bâtis et clichés tick/caisse stables ; V252 stables | **141 ; 38** |
| Renforts bâtis mais clichés instables | **170 / 311** |
| Modèle pré-V161, profit post-V161, C70, capital, prix, réserve, rang disponibles | **2 388 / 2 388** |
| Scores C69 reconstitués au dénominateur observé | **2 388 / 2 388** |
| Identifiants AIRF1 dupliqués (désélection des clichés stables) | **4** |
| Nombre **exact** d'avions avant l'achat / saturation / capacité / âge / rotation / concurrence / type de ligne | **0 / 2 388**, chaque variable |
| Facture physique unitaire / profit contrefactuel de l'avion | **0 / 311** |

Les 2 077 échecs concernent **tous canaux** ; les renouvellements ne sont pas comptés comme ajouts de flotte. Les 141 clichés stables sont les seuls comparables à un budget RAIL **à même tick** ; la reconstitution des chiffres stockés de la tentative reste possible hors stabilité, avec avertissement. Aucun duplicata n'est éliminé silencieusement de la statistique d'exposition.

| Renforts C121 | Avant V161 : ROI modèle médian (‰) | Après V161 : ROI brut médian (‰) | ROI C70/finance médian (‰) | Rapport médian `post-V161 / pré-V161` |
|---|---:|---:|---:|---:|
| **Toutes tentatives** (2 388) | 1 350,1 | **16,73** | **16,31** | **0,0301** |
| **311 achats réussis** | 561,2 | **16,73** | **16,31** | **0,0577** |
| Dont **141 clichés stables** | non repris comme échantillon indépendant | **16,73** | — | **0,0577** |
| Source `prior` (2 278 tentatives ; 294 achats) | 1 396,5 | **16,73** | **16,31** | **0,0271** |
| Source `model` (110 tentatives ; 17 achats) | 46,24 | **46,24** | **17,07** | **1,000** |

Tous les ratios sont des **médianes des épisodes**, sans pondération par graine ; le ratio des médianes n'est pas la médiane des ratios. L'écart médian de profit `modèle − V161` est **51 952 £/an** sur les tentatives. Cette différence est déterminée mécaniquement par la politique V161 et la distribution de ses sources : elle ne permet pas de conclure que le modèle C121 surestime le gain marginal ou que le plafond est trop faible. Les 2 388 lots planifiés contiennent **un seul avion** selon `spend / unit_price`, et **tous** sont des tentatives après filtres, souvent répétées après un échec ; ce ne sont pas 2 388 décisions indépendantes.

Le montant médian prévu pour les achats effectivement réussis est **38 964 £** ; l'écart médian `cash_before − cash_after` de ces mêmes épisodes est **33 159 £**. Ces deux nombres ne mesurent pas une erreur de devis : prêt, autres commandes/flux et changement de tick peuvent modifier la trésorerie ; l'invoice réelle n'est pas isolée dans `AIRF1_OUTCOME`.

### Période, rang, approximations de flotte

| Année | Tentatives | Achats | ROI modèle médian (‰) | ROI post-V161 médian (‰) | Rang médian |
|---|---:|---:|---:|---:|---:|
| 1970 | 188 | 9 | 2 239,5 | 216,92 | 0 |
| 1971 | 709 | 24 | 2 266,0 | 150,19 | 0 |
| 1972 | 828 | 48 | 1 229,7 | 16,73 | 4 |
| 1973 | 523 | 100 | 643,4 | 16,73 | 2 |
| 1974 | 71 | 61 | 479,5 | 16,73 | 3 |
| 1975 | 69 | 69 | 342,4 | 18,70 | 3 |

L'analyseur offre une cohorte **proxy** « achats de renfort réussis antérieurs sur le même lineId dans ce même log » : **2 256 tentatives à 0**, **122 à 1**, **10 à 2** événements antérieurs ; ROI modèle médian **1 370,5 / 982,5 / 577,9 ‰**, respectivement. Ce compteur ne comprend ni les avions présents dès la construction de la ligne, ni pertes/crashs, ni remplacements ; **il ne représente pas `vehCount`**. Les rangs observés sont effectifs, mais ni une rangée `0` ni un grand score modèle ne prouvent que le renfort aurait dû précéder un RAIL.

### Ce que mesure, et ne mesure pas, l'après-achat

Les logs contiennent **148** `C121_FLEET_MARGINAL` après achat. **116** observations ont une unique tentative de croissance réussie de l'année `observation−2`, avec un avion ajouté et sans autre achat ultérieur répertorié sur cette ligne avant la fenêtre de mesure ; parmi elles, **52** achats avaient un cliché initial stable. Sur ces 116 rapprochements, la médiane du delta de profit **de la ligne** vaut **+3 182,5 £/an**, dont **54** négatifs ; la médiane `profit V161 − delta de ligne` vaut **−898,5 £/an**. Les années de reporting C121 et le caractère différé sont respectés ; les logs ne garantissent toutefois ni l'absence de concurrence ou d'autre projet, ni la stabilité du service, ni un témoin sans achat. Ces nombres ne sont **pas** un biais d'estimation du ROI marginal et ne doivent pas servir à entraîner un coefficient. Le reste des observations est non attribuable de façon prudente dans ce lecteur.

Le panel historique distinct de **40 références × 10 ans** redonne **3 437** constructions de renfort dans `FLEET_PROJECT`, ROI V161 entier médian **16 ‰**, ROI modèle avant plafonnement médian **461,9 ‰**, **3 251** achats `prior` et **186** `model`. Ces 40 parties n'ont pas le même horizon, ni les mêmes traces transactionnelles que les cinq parties shadow : **aucune jointure d'épisodes par date/ligne/graine** ne les relie. L'ancien `sweeps/analyse_c121_air_economics_shadow.py` analyse des prédictions **d'ouverture de ligne C121** face aux observations C117 et des hypothèses physiques de hub à échéance ; ce n'est pas une série temporelle du prochain renfort d'une ligne déjà exploitée.

## Couverture des facteurs explicatifs et prochaine sonde passive (étape 2 seulement)

| Facteur demandé | Déjà mesurable au tick achat ? | Champ passif minimal manquant et risque de confusion |
|---|---|---|
| Nombre d'avions | **Non (0/2 388)** | `entry.baseVehicles`, `line.vehCount`, `entry.want`, flotte réellement vivante par type ; séparer croissance, remplacement, appareil perdu |
| Saturation et capacité | **Non (0/2 388)** | stock attente PASS/MAIL aux deux gares, capacité/refit par appareil, occupation, cadence, débit de prise en charge avant achat, cible/limite `targetAirPlanes` |
| Âge de ligne et stade de maturation | **Non (0/2 388)** | date construction/dernier renfort, `c121MarginalSamples`, année de base, état cold-start, longueur de fenêtre économique |
| Rotation/attente aéroport | **Non (0/2 388)** | durée prévue de cycle C121, rotation effective **historique avant achat**, délai observé en gare ; ne jamais remplacer par une rotation calculée après achat |
| Concurrence et cannibalisation | **Non (0/2 388)** | `v161Neighbours`, amortissement V161, nombre de lignes propres partageant chaque aéroport, concurrence AAA déjà présente et capacité commune avant achat |
| Type de ligne | **Non (0/2 388)** | `c121Arm` (`newpair`, `hubsite`, `hubhub`…), cargos et gares d'origine/destination, moteurs/refits et aéroports ; ne pas inférer à partir du `lineId` |
| Capital/ordre | **Oui**, mais partiel | conserver `fundScore`, ROI avant/après C70, `K_dec` avec tick de sélection, **tier C77**, coût réel de chaque unité après commande et `added`, échec précis, rang et portefeuilles au moment de la sélection |

Sonder ces champs **uniquement par copie de valeurs déjà calculées**, avec `id`, graine, tick de sélection, tick avant commande, et ordre des achats. Publier explicitement **valeur absente** et **origine temporelle** par champ. Ne pas inspecter le stock/la concurrence une fois le nouvel avion construit puis la présenter comme l'état ayant conduit à l'achat. La comparaison des profits incrémentaux demandera en étape 2 des fourches de **même sauvegarde** et un contrôle AA/AA avant toute calibration.

## Reproductibilité et garde-fous

Depuis la racine, sans Docker ni moteur :

```powershell
uvx --from 'pytest==8.4.2' pytest sweeps/test_audit_air_roi_renfort1.py -q
python -X utf8 sweeps/audit_air_roi_renfort1.py "results/air_flotte1_shadow_causes_5x6_20261022_engine/*.log" --reference "results/rail_cal4_40x10_multimodal_pc_20261021_engine/reference_*.log"
```

Pour chaque tentative complète avec champs et manquants explicites, ajouter `--details` à la commande JSON. Six tests `pytest` passés (2026-10-22), arithmétique C69 et V161, séparation des parties, rejet des doublons/clichés instables, lots multiples, rattachement différé non causal et référence indépendante. Le rapport garde les **0** de couverture et les `null` de causalité : aucun proxy post-achat n'est réinterprété comme un profit contrefactuel. Aucun score, défaut, ordre du portefeuille ou priorité AIR/RAIL n'a été modifié.
