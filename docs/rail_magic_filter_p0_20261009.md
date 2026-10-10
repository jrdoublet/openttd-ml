# P0 — Seuils et classement RAIL (09/10/2026)

## Périmètre et constat statique

Source `ai/OpexAI/candidates.nut`: `profitAnnual * 1000 / predictedIterations` est en £/an par 1000 **itérations A\***, pas en £/opcode VM. Seuils d'exclusion `500` voyageurs et `200` fret activés par `policy_portfolio=1`. Le bonus de rotation (130/115/100/60 %) et `roi * 15` mélangent ce ratio avec le ROI (pour mille/an). Ce `ratio` classe le TOP20 local, qui **ne** supprime pas à lui seul les autres candidats du portefeuille normal : `OpexBuildProjects` utilise `rail.candidates`. Il peut en revanche modifier les places `reuse`/stock et les champs de classement local. Les projets effectivement reçus par le sélecteur passent par le profit calibré C70, le capital finançable puis `K_dec` C69 ; priorités AIR C77 et early-slot peuvent modifier l'ordre effectif.

`OpexIterationBudget` prend le même 500 comme plancher terminal de recherche, avec un plafond physique `HARD_ITERATION_CAP`. Les opcodes A\* sont estimés séparément dans `projects_builders.nut` (`min(predictedIterations, HARD_ITERATION_CAP)*3105+200000`). La limite d'itérations reste une contrainte de constructibilité/ressources : abaisser 500/200 ne démontre pas un nouveau chantier rentable.

## Intervention isolée et instrumentation

- `rail_economic_preselect=0` par défaut : lorsque activé, conserver les candidats au profit prédit net positif malgré `500/200`, classer le TOP20 RAIL via `OpexTopKFund` (profit calibré / financement) et supprimer le `MIN_RATIO` terminal comme borne économique A\* ; le plafond dur A\* reste actif. Aucun changement de revenu AIR, prix de construction ni demande RAIL.
- `rail_magic_shadow=0` par défaut, indépendant : les mêmes devis éliminés par 500/200 sont conservés *uniquement* en mémoire de sonde. Sur une reconstruction complète, `RAIL_MAGIC_CF` enregistre les visites et les sommes de profits projetés éliminés, ainsi que l'effet du bonus sur le TOP20. `RAIL_MAGIC_ITEM` révèle les candidates financables qui surpassent le meilleur AIR noté du même classement sur le score calibré. La valeur `search_ops_est` (opcodes VM) convertie en `wait_days_est` (74 ticks/j × 10k op/tick) permet d'estimer un coût du délai face à AIR en £, **sans** l'injecter comme coefficient de classement.

Limites pré-enregistrées : les paires rejetées peuvent être impossibles à construire ou partager le même bassin, les sommes de profits ne sont donc pas additives et la supériorité papier ne prouve pas une substitution faisable. Les reconstructions répétées sont des **observations**, et les dédupliquages OD/graine/année doivent être faits au décodage. `AIR` sans `fundScore` connu est exclu du comparateur : l'absence de meilleur AIR est *inconnu*, pas un profit AIR nul. Des reconstructions ciblées/incrémentales peuvent ne pas produire une photographie AIR simultanée.

## Pré-enregistrement du banc

- Dépôt `/openttd-ml`, branche `master`, HEAD avant chantier `a0556ab685177480a38d4fe0062685bd33b8c640`, nombreux changements locaux simultanés explicitement préservés ; le SHA seul ne sera pas utilisé comme identification du code exécuté.
- PC local Docker `desktop-linux`, image `openttd-lab` sha256 `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, profil `10 CPU / 8g RAM / 10 workers`, swap=RAM, volume `openttd-lab-home`. Une seule campagne à la fois.
- Contrats puis smoke `rail_magic_shadow=0` vs `rail_magic_shadow=1` en 1 graine × 1 an (santé, traces, intrusivité) et diagnostic par plusieurs graines si exposition. **Un écart entre sonde ON/OFF n'est pas un gain de politique**.
- Après contrôle : smoke comportement `rail_economic_preselect=0` vs `=1` en 1×1, puis porte **A 40 graines × 3 ans**, règle `gain_short`, une répétition, seuil `4 %` du `profit_year` témoin terminal, Wilcoxon exact p<0,05 et IC95 bootstrap bas>0, garde valeur −5 %. Porte **B 20 graines × 10 ans** seulement si A est complète et `pass`, règle `non_erosion`/garde −5 %, IC95 bootstrap haut>=0.
- Mesures par graine/année : rejets 500/200, effets TOP20, meilleur AIR faisable papier, A\* temps/opcodes et ses issues, AIR/RAIL construits, `profit_year`, `company_value`, véhicules/stations. Associer provenance bundle/manifeste et ne pas confondre profits projetés avec réalisation. Aucun changement du défaut, commit ou push sans validation.

## Résultats obtenus et limites

- Contrats Python ciblés en Docker : 4/4 `test_rail_magic_economics`, 56/56 `test_rail_origin_reuse`, 3/3 `test_homogeneous_preselect`, 1/1 `test_analyse_rail_magic_filter_p0`; contrat d'analyse annuelle 1/1 sur l'hôte.
- Sonde ON/OFF smoke 1×1 `rail_magic_probe_smoke_1x1_20261009` : deux parties saines, trajectoires économiques identiques (Δ profit_year 0) ; les journaux moteur étaient vides faute de `--script-debug`.
- Sonde ON/OFF diagnostique 5×6 `rail_magic_probe_diag_5x6_20261009` : 10/10 saines, mais sonde **intrusive** (Δ profit_year Opex moyenne **−82 154 £/an**, valeur **−3,31 %**). Journaux moteur également vides : cette campagne ne fournit pas les rejets.
- Sonde ON/OFF 5×6 avec `--script-debug` `rail_magic_probe_debug_5x6_20261009` : 10/10 saines, bundle `6421111a5edd0076f1e3a244a94001e4f56633e1d66747fdbd7071245fa917bf`, témoin→sonde Δ profit_year **−89 693 £/an** moyen, valeur **−3,65 %** ; lecture et parser des journaux `results/rail_magic_probe_debug_5x6_20261009.analysis.{json,csv}`. La modification de cadence rend les valeurs économiques descriptives et empêche d'attribuer les trajectoires à un effet de filtrage.
- Les 15 snapshots complets couvrent 14 couples graine-année (1972–1975), avec **796 rejets de ratio en visites** : **796 PAX, 0 fret**. Profits positifs cumulés sur les visites **sans correction des répétitions**. Correction de l'audit de couverture : **seules 571 visites** dans 11 snapshots à AIR coté et tier C77=0 sont effectivement comparées par score commun, avec **0** candidat rejeté supérieur dans ce sous-ensemble. **175 visites** dans 3 snapshots à AIR prioritaire C77 tier>0 ont leur comparaison par score court-circuitée ; **50 visites** sans AIR coté restent inconnues. Le résumé initial « 0/796 devant AIR » était excessif. Les snapshots décrivent un vivier papier ; aucune pose réelle n'est prouvée. Certains candidats partagent leurs revenus.
- Smoke du correctif réel `rail_magic_behavior_smoke_1x1_20261009` (réglages RAIL `0` vs `1`, shadow0 dans les deux bras) : 2/2 saines, sur graine42 Δ profit_year **+34 505 £/an** et valeur **+12,33 %** ; `diagnostic_only`, une seule graine. Bundle `be1dc07cfe7b2561d4f76982ad6ca26262d82c7a817a75edc4bc388e536fd6dd`.

**Interprétation provisoire** : le seuil 500 coupe de nombreux petits projets RAIL PAX rentables au devis, mais les observations n'établissent aucune supériorité papier face au meilleur AIR connu. Les bonus peuvent changer le TOP20 local sans retrancher directement ces projets du portefeuille commun. Le smoke économique suggère un effet comportemental, sans preuve de gain robuste. La porte V102 est nécessaire pour trancher ; laisser les deux nouveaux réglages désactivés par défaut.

## Verdict V102 — porte A terminée, variante rejetée

**Campagne** `rail_magic_economic_gateA_40x3_20261009`, référence `OpexAI[rail_economic_preselect=0,rail_magic_shadow=0]` et variante `OpexAI[rail_economic_preselect=1,rail_magic_shadow=0]`. Bundle figé **`d6971225c4c6117e19962aa731f611f3fb94a4a67204ab89bb636c5d9dd8a71c`**, manifeste **`cec939fde584072cc49b994fc42adfa8242d1bac47e700ad333675cf1a93dcf9`**, 40 graines canoniques, une répétition, **80/80 parties saines**, 40/40 paires complètes, horizon 3 ans. PC Docker local 10CPU/8g/10workers, image identifiée ci-dessus. Règle figée avant résultats : `gain_short`, primaire `profit_year` terminal, seuil relatif 4 %, garde valeur −5 %, IC95 bootstrap / Wilcoxon exact.

- **Résultat principal** : delta variante−référence `profit_year` **−31 949,275 £/an** moyen, médiane **−54 602,5 £/an**, V/D/E **17/23/0**, Wilcoxon exact bilatéral **p=0,37538056**, IC95 bootstrap **[−107 723,675 ; +44 992,375] £/an**, gain exigé **+79 244,743 £/an**. Ratio des moyennes `company_value` **0,98655** soit **−1,344966 %** (garde −5 % tenue).
- **Verdict harnais `fail_primary` : NON ADOPTER.** Le test ne montre pas une perte significative au seuil 5 %, mais il ne prouve aucun gain positif utile et rate les conditions pré-enregistrées de la porte A. Porte B 20×10 **non lancée**, conformément à V102 ; `rail_economic_preselect` reste **OFF par défaut**.
- **Trajectoire annuelle** du JSONL du même bundle : sur les 40 graines, delta moyen `profit_year` **+1 200 £** en 1970 (couverture trimestrielle partielle), **+23 147 £** en 1971, puis **−31 949 £** en 1972 ; delta valeur moyen **−4 103 £ / +13 954 £ / −46 610 £** respectivement. À décembre 1972, delta **−0,625 train**, **−2,000 avions**, **−0,575 installation de gare rail** et **−1,975 construction sur panneaux `IB`** par partie. Ces compteurs physiques sont des états ou traces conservées, pas des achats financés exhaustifs. Extractions appariées : `results/rail_magic_economic_gateA_40x3_20261009.annual.csv` et `.annual.json`.
- **Trajectoire contrefactuelle** : 15 snapshots, 14 couples graine/année, **796 visites** de candidats PAX écartés par 500 (0 fret par 200), profits projetés cumulés des visites **1 050 723 £/an** soit ~1 320 £/an par rejet observé. Les mêmes OD peuvent réapparaître ; ce montant n'est **pas** un profit perdu unique, réalisable ou additif. **0/571 passages comparables au score AIR C77 tier0** sont supérieurs ; **175** sont masqués par une priorité C77 et **50** dépourvus de comparaison AIR notée. Il reste donc **225 visites à score intermodal inconnu**. Effet bonus visible sur TOP20, sans exclusion globale des candidats déjà conservés.

### Audit de portée du correctif et actions futures

Le lot ON combinait trois traitements : admission sans seuil 500/200, réévaluation du TOP20 sur P_calibré/capital, et budget A\* sans `MIN_RATIO` terminal. La porte A qualifie/rejette **ce lot** ; elle ne détermine pas l'effet causal isolé de chaque composant. `OpexTopKFund` ne reproduit pas encore `K_dec` du sélecteur C69, mais au défaut le portefeuille reçoit tous les `rail.candidates` et la différence n'agit que sur chemins locaux TOP20. Ces re-classements ajoutent des opcodes, un coût non quantifié exhaustivement dans cette porte. L'estimation de coût d'opportunité en £/jour de retard face à AIR est seulement diagnostique ; faute de distribution de réussite A\* en fonction de l'effort, il serait arbitraire de convertir une telle estimation en un nouveau seuil de décision.

La sonde a été revue après gel de la porte A : sous `homogeneous_preselect=1`, ses wrappers utilisent `OpexTopKLegacy`, le compteur `accepted` ne compte plus ses faux acceptés, et la recotation diagnostique est sortie de `selectionOpcodes` (aucune de ces corrections n'exécute la sonde dans A, `rail_magic_shadow=0` sur les deux bras). Elles sont dans le **code local courant**, pas dans le bundle figé A, donc aucun chiffre ci-dessus ne leur est attribué. Les traces de l'ancienne sonde restent diagnostiques et intrusives. Une nouvelle politique éventuelle devrait d'abord isoler les trois mécanismes, mesurer la constructibilité réelle des candidats additionnels et calibrer le coût/opportunité de recherche au lieu d'abaisser simplement 500/200.

**Vérification finale (après revue)** : 62/62 tests ciblés Docker sains (4 `test_rail_magic_economics`, 56 `test_rail_origin_reuse`, 1 `test_analyse_rail_magic_filter_p0`, 1 `test_analyse_rail_magic_ab_annual`), en plus des 3 contrats `homogeneous_preselect` déjà verts. `git diff --check` code 0, seul avertissement de conversion CRLF d'un journal modifié par une autre session. Aucun commit/push ; aucune campagne de porte B.

## Suite demandée : isolation causale du lot rejeté

La porte A précédente mesure trois effets simultanés. Pour attribuer le résultat
à un mécanisme réel sans chercher un nouveau seuil magique, trois réglages
**indépendants et OFF par défaut** ont été ajoutés, sans changer le comportement
du réglage combiné `rail_economic_preselect` :

| Réglage isolé | Chemin modifié uniquement | Référence fixe |
|---|---|---|
| `rail_magic_admission_only=1` | Génération : conserver les projets RAIL à profitAnnual positif sous 500/200 | TOP20 composite et budget A* historiques |
| `rail_magic_rank_only=1` | TOP20 RAIL local via `OpexTopKFund` | Filtre 500/200 et budget A* historiques |
| `rail_magic_astar_only=1` | `alternativeRatio=0` pour les recherches A* RAIL | Admission 500/200 et TOP20 historiques |

Pour chaque isolation, les quatre autres réglages P0 rail
(`rail_economic_preselect`, `rail_magic_shadow` et les deux autres isolations)
sont forcés à 0 dans les deux bras. `homogeneous_preselect` reste au défaut 0.
Les projets AIR, tarifs, demande RAIL et adversaire ne changent pas. La
validation **pré-enregistrée** est un smoke apparié 1×1, puis A V102
`gain_short` 40 graines canoniques × 3 ans, primaire `profit_year` terminal,
seuil relatif 4 %, Wilcoxon p<0,05, borne basse bootstrap>0,
garde de valeur −5 %. Si A échoue : rejet de l'isolation, pas de B.
Si A passe : porte B 20×10 `non_erosion` avec garde −5 % avant adoption.
Les campagnes successives seront gelées avec un bundle propre et auront des
identifiants distincts ; aucune campagne Docker simultanée.

L'isolation « admission seule » est prioritaire : sa validité peut être testée
en conservant **tous** les plafonds A* existants. L'exposition des rejets PAX
500 a déjà été observée en 5×6, mais cela ne prouve pas une construction
utile ; les différences de profit annuel, installations et véhicules sont
relevées séparément. Les autres isolations serviront à attribuer les effets
du lot si la mécanique le justifie.

### Admission isolée — porte A terminée

**Campagne** `rail_magic_admitonly_A40x3_20261009_r1` : les deux bras
`rail_economic_preselect=rail_magic_rank_only=rail_magic_astar_only=rail_magic_shadow=0`
ont seul `rail_magic_admission_only` différent (0/1).
Bundle figé commun
`acd6c0af022c2c074e8371d8a618a9acc75ed512002a8486dd2ca47545a8fb9a`,
manifeste
`63d87c3d24eb3e5e3cb6f8c6f970a912ebee1a2cb093fcf497047198f29cd9e9`,
40 graines canoniques, 80/80 parties saines.
Smoke préalable `rail_magic_admitonly_smoke_1x1_20261009_r1`
2/2 sain, graine42 +1 398 £/an, `diagnostic_only`.

**Résultat V102** `fail_primary` : delta terminal `profit_year`
**+8 255,7 £/an** moyen, médiane **+7 437 £/an**, V/D/E **21/18/1**,
Wilcoxon exact **p=0,88482048**, IC95 bootstrap
**[−54 162,625 ; +71 922,475] £/an**, seuil 4 % **+79 181,906 £/an** ;
valeur compagnie ratio des moyennes **+0,4115 %** (garde tenue).
Pas de porte B ni adoption. La porte était appariée au même bundle : il est
impossible de réutiliser les données du bras de référence de l'ancien essai
combiné comme témoin officiel.

Moyennes annuelles appariées : `profit_year` variante-réf **+219 £**
en 1970 (année partielle), **+16 933 £** en 1971,
**+8 256 £** en 1972 ; valeur compagnie **+596, +12 670, +14 253 £**.
À décembre 1972 : **−0,350 train**, **−1,150 avion**,
**−0,425 installation ferroviaire**, **−1,675 signe de chantier** par partie.
Extraction `results/rail_magic_admitonly_A40x3_20261009_r1.annual.{json,csv}`.
Les opcodes de tentative sont partiellement visibles seulement, sur 6/40
appariements en 1972 ; ils ne fournissent pas une mesure exhaustive des opcodes
du générateur. Le compteur historique C73 `ratioTooLow` est un nombre de
candidats SOUS le seuil même lorsque l'admission seule les conserve :
il ne doit jamais être nommé « rejets effectués » dans cette variante.

**Interprétation** : l'exposition des seuils est réelle, et leur retrait
isolé modifie quelques trajectoires physiques, mais ne prouve pas un gain
économique utile, ni davantage de rail opérationnel en année terminale.
Le premier horizon V102 couvre seulement jusqu'à 1972, où les premières
expositions historiques apparaissent ; il ne conclut pas sur toutes les
opportunités plus tardives de 1973–1975. Le défaut reste inchangé.

### Allocation A* isolée — porte A terminée

**Campagne** `rail_magic_astaronly_A40x3_20261009_r1` : les deux bras
partagent exactement le même bundle source
`acd6c0af022c2c074e8371d8a618a9acc75ed512002a8486dd2ca47545a8fb9a`,
avec `rail_economic_preselect=rail_magic_admission_only=rail_magic_rank_only=rail_magic_shadow=0`.
Seul `rail_magic_astar_only` varie 0→1, sans changer la génération
ni le classement RAIL, donc la réserve A* peut être étudiée séparément
de l'admission économique. Manifeste
`2963958f82a8b5fd3cc772ad65d9f7834e68fc3926f420da56e356849a77d87b`.
Smoke `rail_magic_astaronly_smoke_1x1_20261009_r1` : 2/2 sain,
graine 42 trajectoire identique à un an.

**Porte A 80/80 parties saines** : delta `profit_year` terminal
**−863,825 £/an** en moyenne, médiane **0**, V/D/E **1/2/37**,
Wilcoxon exact **p=0,5**, IC95 bootstrap
**[−2 560,25 ; +77,35] £/an**, seuil relatif 4 %
**+79 180,15 £/an**, valeur compagnie **−0,009826 %**.
**Verdict `fail_primary`**, garde de valeur tenue ; aucune B20×10 et
aucune adoption. Des 40 graines, **37** ont même profit terminal.

Annuel apparié : en 1970 et 1971 **tous les deltas économiques et
les comptes de véhicules/installations observés sont nuls** ; à fin
1972, delta moyen profit −864 £, valeur −340 £, trains +0,025,
gares rail +0,05, avions −0,025 et panneaux de chantiers **0**.
`results/rail_magic_astaronly_A40x3_20261009_r1.annual.{json,csv}`
permet la vérification par graine. Les panneaux OB n'ont une
couverture d'opcodes appariés exploitable que pour 10/40 graines en
1972 : aucune économie/coût d'opcodes VM total ne peut être affirmé.
La branche budgétaire `alternativeRatio=0` est bien sélectionnée
dans les quatre appels task_rail sous le réglage, mais cette exposition
de code est distincte d'un tracé qui consommerait réellement plus
d'itérations ou aboutirait à une meilleure pose.

### Classement TOP20 isolé — absence de voie métier au défaut

`rail_magic_rank_only=1` active `OpexTopKFund` seulement dans
`OpexRailEconomicTopK`; au défaut courant, `rail.best` n'est
consommé côté chantier que par le stock C80, **OFF**.
`OpexBuildProjects` soumet les `rail.candidates` complets au
classement intermodal TOP64 : modifier le TOP20 ne change donc pas
leurs rangs directement. Le recalcul local reste coûteux et
`OpexTopKFund` utilise le financement sans `K_dec` C69 : ce n'est
pas exactement le score économique final. **Aucune porte de gain
TOP20 isolée lancée faute de voie de décision exposée** ; il serait
trompeur de déclarer cette politique rejetée économiquement.
Elle reste OFF par défaut et ne doit pas être adoptée.

### Décision finale P0

1. **Lot combiné** `rail_economic_preselect=1` : porte A
   `fail_primary` (−31 949 £/an), rejeté.
2. **Admission 500/200 seulement** : porte A `fail_primary`
   (+8 256 £/an sans significativité ni seuil relatif atteint), rejetée.
3. **Budget A* seulement** : porte A `fail_primary`
   (−864 £/an, 37 ex æquo), rejeté.
4. **TOP20 seulement** : pas de qualification économique ni de
   consommateur métier par défaut ; maintien OFF, aucune preuve
   d'adoption.

Les valeurs 500/200, les primes de rotation et `roi×15` sont
empiriques et mélangent des unités incompatibles lorsqu'elles
agissent dans le classement local. Cela ne rend pas profitable leur
suppression. Le classement commun C69/C70 a déjà une unité
économique cohérente (profit marginal calibré / capital de décision
borné par `K_dec`), mais le TOP20 expérimental ne la reproduit pas.
La recherche A* est une contrainte de calcul/constructibilité ;
aucune base empirique suffisamment forte n'a été établie pour
déduire un prix en £ par opcode permettant d'étendre son budget
de façon rentable.

Tous les réglages P0 rail sont conservés **OFF aux quatre difficultés**,
aucun modèle AIR/demande RAIL/prix d'infrastructure n'a été changé
par ce chantier. Le chantier est **clos, sans adoption** : pas de B
pour les variantes ayant échoué A, pas de relance opportuniste du
même code avec d'autres graines. Une étude future sur la bascule
1973–1975 exigerait une nouvelle hypothèse et un protocole fixé
avant résultats, avec identité de projets et essais constructibles
dans le même état, séparée de cette décision.
