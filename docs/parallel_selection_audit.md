# Audit du classement des investissements — 30 septembre 2026

## Verdict

**Absence de preuve mesurée que le classement courant privilégie les projets au
profit surestimé.** Ce n'est pas une preuve d'absence de biais. Les données ne
réunissent pas estimation immuable à l'élection, identité de l'action, périmètre
comptable homogène et exercice complet exploitable sur le code courant.

**Constat statique le mieux étayé :** le renfort AIR legacy est valorisé avant
amortissement du matériel ajouté, alors que les nouvelles liaisons le sont après
amortissement. Cela favorise son numérateur relativement à une convention nette
homogène ; ni la fréquence des inversions de classement ni une perte économique
imputable à cet écart ne sont mesurées ici. R2, déjà présent, corrige un autre
problème : la recalibration d'une observation. Il n'est pas réimplémenté.

Une seule correction comportementale candidate est proposée au §7. Aucune
modification sous `ai/`, aucun défaut changé, aucune partie ni conteneur lancé.
**C115 protégé ; options cadence OFF inchangées.** Les artefacts d'expériences
existantes sont lus séparément, sans les considérer comme le défaut.

## 1. Périmètre, livrables et reproductibilité

Instructions relues : `AGENTS.md`, état courant de `docs/taches.md`, revue R2,
note 38, journal du 30 septembre et contexte historique du 13 septembre / archive
des tâches. Aucune instruction locale `AGENTS.md` trouvée sous les répertoires
d'écriture. Git absent du PATH, copie sans `.git` : **status/diff et
`git diff --check` non exécutables**, aucun SHA de dépôt revendiqué.

Fichiers du lot seulement :

- `sweeps/parallel_selection_audit.py` : analyse passive, imports purs ;
- `sweeps/test_parallel_selection_audit.py` : 24 tests hors moteur ;
- ce rapport ;
- `results/parallel_selection_audit/audit_20260930_r2.json` : **résultat final** ;
- `results/parallel_selection_audit/audit_20260930_r1.json` : première sortie
  conservée, remplacée pour la lecture par r2 après durcissement des tests.

SHA-256 de la sortie finale :
`2b166115bdc541be4b6e1bada3ad2db9bbbed9072c3db7063da96b23db8faeb2`.
Elle contient les hashes de chaque entrée et des cinq modules d'analyse/test
concernés. Les chemins source et localisateurs JSON/numéros de ligne sont
conservés. Une sortie préexistante est refusée, non écrasée.

Analyse exécutée depuis la racine, Python 3.14.4 du venv existant : invocation
`-B -X utf8 -m sweeps.parallel_selection_audit --out results/parallel_selection_audit/audit_20260930_r2.json`.
Le module accepte aussi une liste explicite d'entrées. Sans liste : JSON/JSONL
`*20260930*` à la racine de `results/`, logs de leurs dossiers `.artifacts`,
deux JSONL C70 historiques, leurs deux rapports, rapport C50 et les deux chemins
lineprofit cités. **Ce n'est pas un scan de toutes les archives historiques ni
un décodage de sauvegardes.** Aucun package de preuve lineprofit/C70 retrouvé
dans l'index `evidence/review` consulté.

## 2. Chaîne existante, vérifiée dans le code

Les chemins `.nut` ci-dessous sont relatifs à `ai/OpexAI/`.

### Prévision

| Action | Producteur courant | Nature du profit |
|---|---|---|
| Nouvelle liaison rail | `OpexMakeCandidate` → `economy.nut::OpexLineEconomics` | Revenu − fonctionnement − amortissement, £/an ; choix **1 ou 2 trains**, pas seulement 1 |
| Nouvelle liaison route | `OpexMakeRoadCandidate` → `OpexRoadLineEconomics` | Même convention nette ; demande/capacité/fréquence et rendement de vitesse déjà présents |
| Nouvelle liaison AIR | `OpexAirEconomics`, `air_engine_choice.nut::OpexC115ChooseRoutePlane` | Convention nette ; C115 peut retenir C68 ou replay C100 selon capital et `K_dec` |
| Nouvelle liaison eau | `builder_water.nut::OpexWaterEconomics` | Convention nette ; référence de calibration incomplète à l'enregistrement de la ligne |
| Renfort AIR legacy | `projects_builders.nut:156–251`, `OpexProjectFromFleet` | Si positif : `lastProfit / have × want` ; sinon `(predRevenue − predRunning) / predTrains × want`. **Pas de retrait de l'amortissement ajouté** |
| Renfort AIR C84/C121 | Branches dédiées du même producteur | Marges spécifiques ; ne pas les confondre avec la moyenne legacy ; non adoptées |
| Renfort route/rail | `_refleetRoadLines`, `_expandRailLines` | Décisions directes de flotte, pas toutes soumises au classement intermodal |
| Remplacement | Autoreplace / `_onVehicleAutoreplaced` ; V92 `OpexAirConsiderReplace` / `OpexAirReplaceFleet` | Autoreplace n'est pas un projet de profit marginal ; V92, défaut 0, peut transformer l'exécution d'un renfort en remplacement |

`air_route_economics.nut:128–135` soustrait explicitement l'amortissement :
prix des avions / durée de vie retenue + amortissement aéroports. Le profit
véhicule observé ne comporte pas cette charge. La moyenne des avions existants
n'est pas, non plus, une observation du supplément de profit du prochain avion.
Le nombre `have` peut déjà différer de celui de l'exercice observé.

### Calibration et R2

`task_report.nut:79–120`, `OpexC70C82AccumulateLine` et
`OpexC70PublishModeFactors` : pour `age >= 2`, prédiction positive et effectifs
valides, le réalisé utilisé pour apprendre vaut

$$R^*_{l,y}=P^{veh}_{l,y}\,N_{0,l}/N_{courant,l}-A^{pred}_{l}.$$

Le facteur C70 est la moyenne des ratios cumulés par ligne avec une pseudo-ligne
à 1 : $(1+\sum_l\sum_y R^*_{l,y}/\sum_y P^{pred}_{l,y})/(1+n)$.
Ce n'est pas la médiane hors partie du script diagnostique C70. Les cumuls sont
persistés, puis les facteurs recalculés au chargement.

**R2 confirmé :** `profitIsObserved` est vrai uniquement pour l'observation
positive legacy (`projects_builders.nut:210–242`). `OpexC70Profit` et
`OpexC82Profit` (`projects_models.nut:228–252`) retournent alors le profit sans
facteur. Le repli prédictif reste calibrable ; C84 reste modélisé et C121 conserve
son exemption. Les six contrats existants passent. Ils ne simulent pas le moteur
aux facteurs 0,5 / 1 / 1,5 et ne qualifient pas l'effet économique de R2.

### Classement

`projects_selection.nut::OpexProjectSelectAffordable` ajuste d'abord le lot AIR
au budget (R1), filtre le financement puis applique le profit calibré. Au chemin
ordinaire C69/C70 :

$$score=1000\,P^{classement}/\max(C^{financement},K_{dec}).$$

La flotte legacy est exemptée du plancher `K_dec`. Priorité défensive C77 et
éventuel early-slot interviennent aussi : ce n'est pas un simple tri global par
profit absolu. `K_dec = F × τ` est en £, avec F en £/jour et τ en jours.
**Financement rail = 100 %, pas 170 %.** Le facteur terrain est distinct.

### Construction et réalisé

- Rail : recalcul après quais et tracé réel (`builder_rail.nut:1501–1552`).
- Route : réapplication de l'économie avant construction (`task_road.nut`).
- AIR : `OpexAirReconcileActualBuild` (`air_route_economics.nut:227–282`)
  remplace `plan.economics` après flotte/site/coût réellement construits. Le
  chemin non-C121 rappelle l'économie AIR sans conserver un instantané du choix
  C115. **AF/OF/OJ/OK et `line.predicted` ne sont donc pas des copies garanties
  du numérateur à l'élection.**
- `_recordPortfolioProjectBuilt` (`task_projects.nut:1110–1128`) émet rang,
  ligne, `project.profitAnnual` et `project.capital` : le champ C50 `cost` est
  ici le **capital du projet**, pas une mesure universelle du coût payé.
- `_reportLines` (`task_report.nut:250–450`) somme `GetProfitLastYear` des
  véhicules actuellement associés : profit véhicule de l'année civile
  précédente. Les véhicules vendus/disparus et changements d'effectifs doivent
  être connus pour une couverture annuelle de ligne réellement complète.
- `OU` est le **coût nominal annuel** courant ; `OO = profit + runCost` est un
  revenu implicite estimé, pas un journal des recettes encaissées.

Les profits compagnie `PLYR/old_economy` et `profit_year` du harnais restent
distincts : quatre trimestres clos, dépenses compagnie hors véhicules, couverture
propre. Ils ne sont jamais substitués au résultat d'une ligne.

## 3. Contrat de l'analyseur

Réutilisation par import : regex et `parse_fields` de `sweeps.harness`,
`parse_sign` et échelle 256 de `line_profit_analysis`, calcul M1/M2 de
`analyse_c70_calibration`. Pas d'import de `diag_c50_chronology_probe` ou
`diag_c69_bottleneck_probe` : ils modifient `subprocess` dès l'import.

- Un événement C69 associe lui-même estimation stockée et réalisation à sa
  ligne : identité **locale à cet enregistrement**, non preuve de l'élection.
- Jointure C50→C69 seulement dans le même fichier/conteneur, même compagnie,
  graine/répétition présentes, mode et identifiant interne, construction unique,
  antérieure au rapport et cohérente avec l'âge. Les valeurs non renseignées
  restent nulles ; pour les logs la portée est le fichier de partie, pas une
  graine devinée dans son nom. Les phases Save/Load restent séparées.
- Plusieurs constructions candidates : refus, **jamais la plus proche**. Ni
  villes, ni gares, ni rang, ni mode seul ne servent de substitut d'identité.
- Dates validées avant déduplication ; doublons identiques comptés une fois,
  conflits de ligne/exercice exclus. Identifiants numériques normalisés avant
  le réducteur importé. Les localisateurs et dates répétées restent disponibles.
- `line_calib.year` = exercice ; `line_profit.profit_year` = exercice ;
  `OZ.year` = **année du rapport**, donc exercice précédent. Les signes ne sont
  qu'inventoriés, faute de propriétaire/contexte attesté dans les chaînes seules.
- `age = 1` : année d'ouverture, partielle si date de construction connue et
  postérieure au 1er janvier ; sinon couverture exacte inconnue. `age = 2` :
  première année civile entière, montée en charge possible. `age >= 3` ne
  prouve pas un régime stabilisé. Pas de borne 1975 codée en dur, ni annualisation
  d'un exercice partiel, ni assimilation première observation = ouverture.
- NoAI : £ déjà converties. `VEHS.currency_fract` : /256 **une fois**. Un champ
  `*_gbp` n'est pas redivisé ; unités inconnues refusées.
- Null/NaN/invalide ≠ zéro. Les zéros **émis** par les producteurs sont conservés,
  mais `trains0 <= 0` signale une référence initiale absente/non qualifiée : les
  bus urbains à prédiction nulle ne deviennent pas des modèles parfaits.

`calibration_proxy_not_election_bias` reproduit la statistique C70 existante,
après validation explicite des champs dont `pred_amort`. Le « net » résultant
soustrait un **amortissement prédit** et normalise linéairement la flotte : ce
n'est pas un profit net réalisé. M2 signifie **effectif égal**, pas preuve
d'identité des véhicules ni d'absence de remplacement. Les sources restent
séparées ; aucun pooling de fichiers résumés, JSONL et Save/Load.

Limite assumée : l'analyseur ne prend pas en charge un hypothétique schéma futur
d'estimations immuables. Les biais d'élection restent nulls dans le schéma actuel,
plutôt qu'une valeur calculée sur des périmètres incompatibles.

## 4. Mesures de couverture

**57 chemins examinés : 55 lisibles, 2 absents**, aucun illisible dans ce corpus.
Les absents sont `lineprofit_default_5x6_20260926.{json,jsonl}`. Les profits de
la note 38 ne sont donc pas revalidés par cette copie.

### Sources récentes : aucune année pleine appariable

Les quatre logs d'exposition ci-dessous sont sous
`results/diag_cadence_exposure_20260930_r1.artifacts/`. Leur manifeste
`diag_cadence_exposure_20260930_r1.json`, `games[].log_path`, confirme les bras,
graine 42 et fin au 1971-02-01. L'analyse ne déduit pas ces métadonnées du nom.

| Source | C69 ligne/exercice | C50 projets construits | Liens construction→C69 | Fenêtres |
|---|---:|---:|---:|---|
| `reference_42.log` | 12 | 8 | 8 | 8 ouvertures partielles + 4 dates inconnues |
| `skip_not_due_42.log` | 12 | 9 | 8 | 8 partielles + 4 inconnues |
| `hub_prefilter_42.log` | 13 | 10 | 9 | 9 partielles + 4 inconnues |
| `watch_daily_42.log` | 0 | 10 | 0 | résultat annuel absent, pas profit nul |
| `save_load_exp_cadence_20260930_r2.json` | 22 | 54 | 8 | 8 partielles + 14 inconnues, phases séparées |
| `save_load_r4_probes_20260930.json` | 24 | 29 | 10 | 10 partielles + 14 inconnues, phases séparées |

Les logs du diagnostic cadence 5×6 et du smoke cadence n'ont aucun des événements
de ligne recherchés. Les résultats compagnie existent, mais ne comblent pas cette
lacune. Les 22/24 observations Save/Load ne sont **pas** autant d'expériences
indépendantes. Les quatre premières lignes du tableau constituent des expériences
distinctes ; elles ne sont pas fusionnées avec ces tests techniques.

| Catégorie | Couverture récente attestée | Biais d'élection mesuré |
|---|---|---|
| Nouvelle liaison rapportée C50 | 25 liens dans les trois logs avec rapport annuel ; 18 supplémentaires dans les phases techniques, non indépendants | **Non mesurable** : année d'ouverture, référence mutable, bases comptables différentes |
| Renfort | 3 événements `mode=fleet` dans les logs d'exposition, 16 dans le Save/Load cadence ; action détaillée non attestée | **Non mesurable** : pas de gain marginal identifié |
| Remplacement | Pas de paire explicitement identifiée | **Non mesurable**, pas « aucun remplacement » |
| Inconnue / ligne sans construction reliée | Conservée séparément, dont lignes urbaines hors portefeuille | **Non mesurable** |

### C70 historique : diagnostics de référence stockée uniquement

Fichiers liés à la fiche C70 du 21 septembre ; aucun bundle complet/code courant
attesté par cet audit. Ils ne mesurent ni R2 corrigé ni le défaut C115 courant.
`raw` n'est pas supposé signifier le défaut actuel ; les bras déclarés des rapports
compagnons sont respectivement `OpexAI[probe_portfolio=1]` et
`OpexAI[c70_mode_calibration=1,probe_portfolio=1]`.

| JSONL | C69 bruts | Années civiles entières par âge | Éligibles au proxy C70 |
|---|---:|---:|---:|
| `c70_calib_raw_10y_20seeds.jsonl` | 6 315 | 5 271 | 4 089 |
| `c70_calib_on_raw_10y_20seeds.jsonl` | 6 187 | 5 178 | 3 975 |

Exclusions du proxy : ouverture, prédiction non positive ou effectif initial
invalide notamment. Pas de doublon/conflit détecté dans ces deux fichiers.

| Source | Mode | Lignes / lignes-années retenues | M1 réalisé proxy / prédit | M2 (lignes) |
|---|---|---:|---:|---:|
| raw | AIR | 684 / 3 508 | 1,273 | 1,444 (424) |
| raw | rail | 27 / 143 | 0,681 | 0,868 (24) |
| raw | route | 58 / 438 | 1,514 | 1,514 (58) |
| on | AIR | 667 / 3 388 | 1,241 | 1,403 (398) |
| on | rail | 19 / 129 | 0,809 | 1,033 (17) |
| on | route | 59 / 458 | 1,511 | 1,511 (59) |

Ces valeurs sont recalculées, pas recopiées de la fiche. Sous leur convention,
raw rail paraît optimiste et raw AIR plutôt pessimiste ; **cela ne démontre pas
une préférence actuelle pour des projets surestimés**. Populations sélectionnées,
flottes modifiées, coefficient de classement à l'élection absent, petit effectif
rail, absence de comparaison causale/code figé : aucune correction numérique
tirée de ce tableau. Les médianes M1/M2 ne sont pas des moyennes de biais en £.

## 5. Exemples récents vérifiables

Même fichier témoin `diag_cadence_exposure_20260930_r1.artifacts/reference_42.log`,
compagnie 0, IDs internes exacts :

| Ligne AIR | C50 construction | Profit projet rapporté | C69 au rapport | Référence stockée | Profit véhicules exercice 1970 |
|---|---|---:|---|---:|---:|
| 0 | L1367, 1970-02-05, rang 0 | 143 535 £/an | L6242, 1971-01-15 | 56 549 £/an | 130 778 £ |
| 1 | L1392, 1970-02-06, rang 1 | 133 301 £/an | L6246, 1971-01-16 | 53 304 £/an | 74 242 £ |

Dans les deux cas : capital projet 71 364 £, amortissement prédit stocké
1 948 £/an, effectif initial/courant 1/1. **Mesure établie : les deux références
prédites diffèrent.** Elle est compatible avec la réconciliation après chantier,
mais n'identifie pas seule toutes les causes de l'écart. Aucun ratio « erreur à
l'élection » n'est calculé : exercice partiel, comptabilité différente et absence
du profit calibré exact au choix.

L6250 : ligne route 2, prédiction et `trains0` émis à zéro, profit véhicule
236 £. Conservée comme référence initiale manquante/non qualifiée, exclue du
proxy ; **ce n'est pas une sous-estimation infinie à corriger**.

La note 38 ne permet donc pas de conclure que « le rail réalisé par ligne est
supérieur, donc l'AIR n'est pas surestimé ». Profit par ligne, rendement du capital,
profit marginal et biais de prévision sont des questions différentes. Son
argument du financement rail ×1,7 et son affirmation d'un seul train sont
contredits par le code courant.

## 6. Instrumentation minimale manquante — raccordement, pas implémentation

1. **Au classement** (`OpexProjectSelectAffordable` / journal `PORTFOLIO_RANK`) :
   exporter un `decision_id`, clé/révision de projet, catégorie d'action et date,
   revenu/fonctionnement/amortissement, profit brut, source observation/modèle,
   facteur réellement appliqué, profit calibré, capital de financement,
   dénominateur effectif, priorité/bonus, rang. Conserver aussi les candidats
   non retenus pour tester une préférence, pas seulement les survivants construits.
2. **Au résultat de tentative** (`_recordPortfolioProjectBuilt` et fin des tâches
   asynchrones) : même identifiant, succès/échec/rollback, `lineId`, quantités
   prévues/construites, coût payé, produit de revente, date de mise en service ;
   conserver côte à côte estimation d'élection et économie réconciliée.
3. **Au rapport et aux événements de flotte** (`_reportLines`, ajouts,
   `_onVehicleAutoreplaced`, ventes/crashs) : identités véhicule/ligne historisées,
   intervalles d'appartenance, exercice exact et couverture. Un renfort ou
   remplacement exige un résultat différentiel, non le total de la ligne.
4. **Collecte** : raccorder ces données au `keep`/`extract_line_telemetry` courant,
   avec campagne/politique/bras/graine/répétition/compagnie. Aujourd'hui OpexAI est
   regroupée par mode + ensemble de gares (`bench_1v1_5y_20seeds.py:713–758`),
   **pas par `lineId` NoAI** ; une fermeture peut changer la clé. Vérifier la
   complétude de chaque composante profit : l'extracteur courant initialise ses
   sommes à zéro et ignore les champs véhicule non numériques.

`probe_cost=1` seul n'ajoute ni l'identité d'élection ni l'export des panneaux
d'estimation dans `keep`. Les panneaux sont limités à 31 caractères ; ne pas
leur attribuer 100 % de couverture sans preuve. Instrumentation symétrique,
mesure de son coût et bancs exclusivement centralisés après les éditions.

## 7. Une seule correction candidate, à examiner ensuite

**Soustraire au renfort AIR legacy l'amortissement du seul matériel ajouté,
selon la même convention prix/durée de vie que le modèle AIR courant.**

Pas de coefficient empirique nouveau ; pas de second amortissement des aéroports
déjà construits. Conserver R2 : le profit d'origine observée ne reçoit toujours
pas le facteur C70/C82. Traiter la même convention dans le repli prédictif, sans
modifier les marges C84/C121, C115, ni les quantités ajustées par R1.

Cette piste résout l'écart comptable démontré, **pas** le problème moyenne versus
marge ni la mutation des références. Son effet économique est inconnu. Prochaine
intervention minimale : raccordement des identités/estimations ci-dessus dans un
lot explicitement autorisé, puis observation des inversions de classement et
qualification centralisée d'une variante isolée, sans changement préalable de
défaut. Aucun nouveau multiplicateur par mode proposé.

## 8. Validation exécutée et limites finales

- `test_parallel_selection_audit.py` : **24/24** réussis (premier passage 21/21,
  puis trois cas supplémentaires après relecture indépendante).
- `test_r2_fleet_profit_calibration.py` : **6/6** réussis, fichier inchangé.
- `test_line_profit_analysis.py` : **8/8** réussis, fichier inchangé.
- Total final des suites ciblées : **38 tests**. Exécution `unittest discover`
  par motif exact, option Python `-B` ; aucune suite générale lancée. La découverte
  de tests de l'éditeur n'en trouvait pas : utilisation du runner unittest.
- Analyse finale r2 : 55 fichiers lus, 2 absents, sortie exclusive vérifiée ;
  contrôle de l'éditeur sans erreur sur les deux nouveaux modules Python.
- Contrôle final : les 55 empreintes d'entrées et les cinq empreintes de modules
  correspondent toujours au résultat r2 ; aucun espace final détecté dans les
  trois fichiers texte du lot.
- Aucun test Python ne compile Squirrel ; aucune validation moteur, aucun gain
  économique, aucun verdict d'adoption ni comparaison causale revendiqué.
- Pas de modification de `taches.md`, journaux communs, dépendances, harnais,
  réglages éditeur ou code IA. Pas de commit, push, nettoyage ou activation.