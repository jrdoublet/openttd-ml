# CARTO-1 — cartographie de couloirs ferroviaires à la demande (24 octobre 2026)

**Verdict : fonctionnement shadow et budget validés ; CARTO-1 non qualifié pour usage décisionnel.** Sur trois graines × trois ans à 1 024², les 22 recherches A* rail primaires terminées ont toutes abouti à `OK` ; dix sont appariées à un coût de couloir complet. Il n'existe donc **aucun échec A*** (`ABND`, `DEAD`, `NOPA`) dans le panel observable pour mesurer sensibilité, spécificité, AUC ou précision du classement des échecs. La corrélation descriptive coût de route / itérations est **r = +0,361** sur les dix paires appariées ; cela ne qualifie pas un filtre préalable à l'A*. Le smoke OFF 1024² échoue aussi à l'exigence d'identité stricte malgré l'égalité des principaux bilans terminaux. Aucun commit, push ou changement de défaut.

## Base, périmètre et mécanisme

- Base `master` **`eec5db814734b99c03ed005bfc476c7ff20006c7`** ; modification isolée dans **`.worktrees/carto1`**. Témoin propre sur la même base dans `.worktrees/carto1_reference`.
- Bit libre **25** de `probes` (`33554432`) ; **ON = `probes=33554434`**, **OFF = `probes=2`**, valeur par défaut conservée. Le canal n'active pas `DECISION_LOG` globalement, mais produit ses lignes `CARTO1_*` dans le journal moteur `--script-debug`.
- Source prioritaire : candidats **rail réels** du portefeuille (`_projects.rail.best` et secours `candidates`) et recherches A* primaires du portefeuille/stock rail. Aucun portage de RLW-04b : son classement long reste une extension facultative et le problème des 43 dépassements de RLW-06 n'est pas réintroduit.
- Par paire, coordonnées des blocs 8×8 à partir des tuiles `candidate.src`/`candidate.dst`. Bande autour d'un segment de blocs (centre discrétisé et voisinage ±1 sur x et y). Les coordonnées sont calculées par petits lots ; aucun parcours exhaustif de la carte.
- Cache physique **partagé** indexé par `by × nombre_blocs_x + bx`, un `OpexV308Arm(bx, by, 1)` **full6** par bloc non encore connu. Il contient eau (mer, lac, rivière), maisons/autorité urbaine, relief et un coût entier heuristique. Un bloc déjà en cache est réutilisé ; aucune lecture répétée constatée dans les journaux de la campagne.
- Consommateur **shadow** : somme des coûts du couloir et Dijkstra à huit voisins sur ses blocs, avec pénalité diagonale ; `CARTO1_COST` journalise `direct`, `route`, nombre de blocs, relief/eau/ville et validité. Ces unités **ne sont pas des livres sterling**, ni un devis exact de gare, pont ou voie. Aucun tracé réel, décision de sélection, construction, état persistant de ligne ou projet n'est modifié.
- Exécution en tranches : **au maximum trois petites opérations par tour** (lecture full6 ou constitution de bande), une expansion Dijkstra par tour, admission à partir de 6 500 opcodes restants et 5 000 pour une lecture ; filet de sécurité 6 000 pour le routage. Journalisation du coût des lectures, du travail et des ticks traversés. File bornée à 16 intentions, 72 admissions maximales ; la priorité est donnée aux demandes `astar` lors de l'insertion.
- Le cache est **transitoire**, remis à zéro à `Start()` et après rechargement. **Limite** : aucune invalidation locale lors d'une modification de terrain par les joueurs ; ce niveau d'actualité serait obligatoire avant tout usage décisionnel. Le canal est branché dans les deux boucles (`main.nut` et `_mainLoopProfiled`), sans construction propre à CARTO-1.

## Campagnes et santé

Protocole : harnais `sweeps/run_c66_reference.py` ; OpenTTD 15.3, adversaire **AAAHogEx-115** figé, départ 1970, carte partagée, une répétition, `--script-debug` en ON ; même moteur Docker `openttd-lab:latest` SHA256 `f4b2b9b3b7399cbfecacfe03b8dda49bff2921de36a61fed4e9441e5d44659`, un seul conteneur à la fois, `--cpus 10 --memory 8g --max-workers 10`.

| Campagne ON | Carte | Graines / ans | Santé | Blocs uniques / total | Lecture full6 (opcodes) | Ticks traversés / dépassements |
|---|---:|---:|---|---:|---:|---:|
| `carto1_on256_1x1_20261024_v3` | 256² | 42 × 1 | complete | 74 / 1 024 = **7,23 %** | 92 330 | 0 / 0 |
| `carto1_on1024_1x1_20261024` | 1024² | 42 × 1 | complete | 116 / 16 384 = **0,71 %** | 144 727 | 0 / 0 |
| `carto1_on1024_3x3_20261024` | 1024² | 42, 100, 999 × 3 | **3/3 complete** | détail ci-dessous | détail ci-dessous | **0 / 0** |

Les deux smokes ON utilisent la première version fonctionnelle, à une lecture par tour. La campagne 3×3 utilise la version portée à trois lectures au maximum ; c'est la campagne d'autorité pour les chiffres de couverture du nouveau débit. Un smoke préliminaire `...v2` a détecté un branchement manquant sur le stock rail (aucun bloc demandé) : le branchement a été corrigé avant ces résultats.

### Exposition 1024² : 3 graines × 3 ans

| Graine | Blocs **uniques** lus / 16 384 | Pourcentage | Ops full6 (événements BLOCK) | Ops de travail (dernier SUMMARY) | Demandes admises | Coûts achevés | A* terminés OK / échecs | Appariements coût/A* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 309 | 1,89 % | 385 456 | 634 127 | 21 | 4 | 13 / 0 | 4 |
| 100 | 356 | 2,17 % | 443 997 | 712 273 | 21 | 4 | 6 / 0 | 3 |
| 999 | 496 | 3,03 % | 618 597 | 1 010 986 | 23 | 6 | 3 / 0 | 3 |
| **Total** | **1 161 / 49 152** | **2,36 %** | **1 448 050** | **2 357 386** | **65** | **14** | **22 / 0** | **10** |

Les **1 161 événements `CARTO1_BLOCK` ont chacun un identifiant unique dans leur graine** : aucun bloc n'a été relu, et la carte reste partielle. Les lectures coûtent environ **1 247 opcodes médians par bloc** dans cette instrumentation (le chiffre V308 d'environ 1 154 concernait sa propre mesure, avec son autre contexte). Aucun `CARTO1_BLOCK` ni aucune tranche n'a franchi un tick. Les compteurs `work_ops` sont des **minima observés**, car le dernier `CARTO1_SUMMARY` est émis périodiquement (~30 jours), parfois avant la dernière lecture du log ; pour la graine 42, le dernier résumé indique 303 blocs alors que les événements de fin de partie en contiennent 309. `work_ops` couvre les étapes de travail mesurées dans le hook, sans garantir la mesure de toute la journalisation extérieure.

La file était encore occupée au dernier résumé (`queued=16`, `active=1` pour chacune des trois graines). Les demandes refusées à cause des plafonds sont comptées respectivement **162 / 118 / 61**, soit 341 **tentatives** (pas 341 candidats distincts). Avec 65 demandes admises et 14 coûts complets, le taux d'appariement reste limité. Le cache ne prétend donc pas couvrir tous les candidats ferroviaires, même dans cette exposition de trois ans.

## Mesure prédictive contre l'A* réel

`CARTO1_ASTAR phase=end` est pris au retour du **vrai A*** primaire, avec son `outcome` et ses itérations ; la jointure exige exactement la même clé `kind:cargo:src:dst` qu'un `CARTO1_COST`. Le coût étant calculé en tâche reprenable, il peut apparaître **après** l'événement A*. Les épisodes du stock rail peuvent avoir `end` sans `start` explicite ; la demande `CARTO1_QUEUE` constitue alors la preuve de provenance. Les anciennes lignes `RAIL_ATTEMPT` et `RAIL_SEARCH` restent des diagnostics séparés : les relier par deux tuiles seules confondrait des cargos ou tentatives distincts.

Sur les **10 recherches OK appariées**, coût `route` médian **5 225,5** points, coût `route/route_blocks` médian **274,91** points/bloc et itérations A* médianes **169**. Les corrélations descriptives avec les itérations A* sont :

| Variable | r de Pearson avec les itérations (n=10) |
|---|---:|
| Somme coût `route` | **+0,3613** |
| Coût `route/route_blocks` | +0,3214 |
| Coût total du couloir `direct` | +0,3103 |
| Nombre de blocs de la route | +0,2051 |
| Eau totale échantillonnée | +0,1461 |
| Relief total | +0,2176 |
| Ville/maisons totales | +0,1504 |

**Aucune mesure de discrimination des échecs n'est possible** : `OK=22`, `ABND=0`, `DEAD=0`, `NOPA=0` parmi les A* réels terminés dans cette exposition. Tous les dix couples coût/issue sont également `OK` ; la variance de l'indicateur échec est nulle, r(coût, échec) est indéfini. On ne peut pas annoncer de taux de prédiction, de faux négatifs ou de seuil utile. Le r avec les itérations est modeste, sur dix observations sélectionnées par la vitesse de calcul et le calendrier de la sonde ; il ne mesure ni causalité, ni gain économique, ni qualité d'un routage constructible. **Le critère prioritaire « prédire les abandons A* » n'est pas qualifié.**

## OFF contre témoin propre

Les parties OFF (`probes=2`) comparent le worktree CARTO-1 au témoin `eec5db81` sur les **mêmes** paramètres et le même adversaire. Sur 256², graine 42, un an, analyse intégrale des JSON de résultat et des **26/26 checkpoints JSONL** (13 dates × 2 entreprises) : **zéro différence de jeu** après exclusion stricte des identifiants et des champs de provenance des campagnes. Les **17 différences JSON** et **104 différences JSONL** sont exclusivement ces métadonnées. OpexAI finit à **426 161 £/an**, valeur **390 284 £**, **18 véhicules / 18 gares** ; AAAHogEx à **364 328 £/an**, valeur **364 969 £**, **16 véhicules / 17 gares**, de part et d'autre. Les deux parties sont saines. Cela prouve l'identité de trajectoire **pour ce seul smoke 256²**, sans généralisation automatique.

Sur 1024², graine 42 × 1 an, les **bilans économiques principaux terminaux OFF sont égaux** : OpexAI **23 647 £/an**, valeur **1 £**, **5 véhicules / 8 gares** ; AAAHogEx **187 493 £/an**, valeur **176 973 £**, **11 véhicules / 13 gares**. **Mais l'identité stricte OFF échoue à 1024².** La comparaison exhaustive donne **35 différences JSON** (17 de provenance, **18 métier**) et **141 différences sur les 26 checkpoints JSONL** (104 de provenance, **37 métier**). Les 37 écarts concernent cinq checkpoints : OpexAI aux 1er novembre et 1er décembre 1970 et 1er janvier 1971 ; AAAHogEx aux 1er décembre 1970 et 1er janvier 1971. Aucun écart métier n'a été relevé sur les points antérieurs au 1er novembre 1970. Le second essai de rail au 1er décembre apparaît dans le témoin et seulement au 1er janvier dans le candidat : c'est un **écart de calendrier**, pas seulement un champ diagnostic. Les liquidités finales diffèrent également (OpexAI **18 413 → 18 467 £**, AAAHogEx **43 082 → 43 003 £**) ; note médiane finale AAA **162 → 161,5**. Les deux parties sont saines et les paramètres identiques, mais **le critère demandé « smoke OFF identique au témoin » n'est donc satisfait que sur 256²**, pas 1024². Il faut préserver ce verdict de non-identité en dépit des profits et valeurs égaux.

Une **deuxième exécution du témoin propre 1024²**, campagne `carto1_reference_off1024_repeat_20261024`, utilise **exactement le même bundle** `7f27f8c3d84634256d67233db130e0eb0bde9f7f30b7dcb58ca2b134cafff648` que le premier témoin : **0 différence métier sur l'intégralité des JSON et des 26 checkpoints JSONL**, seules les métadonnées de campagne changent (13 différences JSON et 78 JSONL). Aucune variabilité intrinsèque n'a été **observée dans cette répétition témoin/témoin** ; les différences candidat/témoin ne sont donc pas expliquées par ce contrôle de répétabilité, sans que cela identifie à lui seul une cause unique.

## Contrats, analyse et reproduction

- `sweeps/analyze_carto1.py` lit les journaux complets `.log`/`.gz` avec sorties `--format markdown|json`, expose statistiques par graine, dernier SUMMARY, bloc, opcodes, coût normalisé, issues et corrélations. `sweeps/test_carto1.py` : **9/9 tests** de décodage et fixtures passés.
- `sweeps/test_carto1_runtime.py` : **10/10 contrats** passés, couvrant notamment bit25 OFF, les deux boucles, absence d'actions constructeur, full6, cache, bornes, A* direct et stock, et état non persisté. Contrats existants `sweeps/test_v308_quinconce.py` : **18 tests dont 1 ignoré, aucun échec**. Au total, `python -X utf8 -m unittest sweeps.test_carto1 sweeps.test_carto1_runtime sweeps.test_v308_quinconce -q` : **37 tests, OK (1 ignoré)**. Les smokes ON prouvent compilation Squirrel, exposition, absence d'erreur moteur et 0 franchissement mesuré. `git diff --check` passe.
- Recalcul de la table d'exposition : `python -X utf8 sweeps/analyze_carto1.py results/carto1_on1024_3x3_20261024_engine --format markdown`. Données détaillées : `results/carto1_analysis_3x3_20261024.json`. Manifeste et bundles immuables `results/<nom_campagne>.manifest.json` et `results/<nom_campagne>_bundle/` dans chaque worktree.

**Suite conditionnelle, sans activation par défaut** : mieux prioriser les A* en cours dans la file et relever suffisamment d'`ABND`/`NOPA` sur des projets rail réels pour créer une vraie population positive, puis mesurer les seuils du coût normalisé en validation hors-échantillon. Ajouter l'invalidation de blocs touchés et vérifier l'erreur des cartes full6 contre le terrain réel avant toute admission, rejet ou guidage de construction.

## Paires longues

### Échantillon figé et méthode

Le complément expérimental réutilise **RLW-04b original** : bit `24` (`16777216`), admission `RLW04B_RESERVE=8500`, `RLW04B_SOURCE_RESERVE=2700`, sans le relâchement de RLW-06 qui avait fait franchir 43 ticks. L'énumération passive retient les couples fret non périssable situés à **224–288 tuiles Manhattan** ; à l'issue du balayage complet des industries, un réservoir Algorithm R de **30 couples par graine**, tiré avec un générateur privé Park-Miller déterministe (seed calculée de la carte et du catalogue, tracée dans `RLW04B_ENUM`), devient immuable. Le tirage ne consomme pas le RNG du jeu. L'activation expérimentale requiert à la fois CARTO-1 bit `25` et RLW bit `24` (`probes=50331650`, panneaux compris) ; **les deux bits restent OFF par défaut**.

L'ordre des opérations est fixé avant observation des échecs : `CARTO1_LONG_SAMPLE` pour les 30 indices distincts, puis `CARTO1_LONG_COST` pour **tous les 30 couples avant le premier A*** de cet échantillon. Les coûts `route`, `route_blocks` et les opcodes marginaux de cartographie sont mesurés sous le cache full6 partagé avec CARTO-1. La prédiction préenregistrée est **`route/route_blocks` (grand = risque accru)**. La recherche témoin utilise réellement `OpexCreateRailPathfinder` ou `OpexCreateSegmentedSearch` et leurs `FindPath` de production, avec plafond dur `HARD_ITERATION_CAP=5000`, continuation sous réserve d'opcodes, un seul état A* shadow actif et aucune pose effective. Ses deux extrémités sont des sorties **virtuelles de terrain plat** proches des industries : elle teste le comportement du moteur de recherche sur le relief réel, mais **ne valide pas la constructibilité des gares ni les compromis économiques des candidats live**. Une absence d'extrémité est tracée `NOPA started=0`, séparée des vrais échecs d'A* (`started=1`).

Pour évaluer sans fuite d'étiquette, chaque graine test est tenue entièrement à l'écart de l'apprentissage : seuil optimisant le J de Youden sur les **deux autres graines**, appliqué tel quel à la troisième ; les sensibilités/spécificités sont ensuite agrégées hors-échantillon. L'AUC est calculée sur les observations éligibles avec les deux classes ; sinon elle reste indéfinie. Le seuil ne saurait être qualifié avec moins de **20 échecs A*** réels. L'économie annoncée n'est qu'une **borne supérieure contrefactuelle en opcodes** : somme des opcodes A* des échecs vrais positifs qui seraient rejetés, diminuée des opcodes réellement consommés par la cartographie ; les faux positifs et le coût de modification du calendrier de jeu ne sont pas monétisés.

Analyse reproductible : `sweeps/analyze_carto1_long.py` (`--years N`, validation des indices, clés, issues, budgets et campagnes JSON/manifeste, puis AUC/LOSO/coûts), `sweeps/test_carto1_long_analysis.py` (21 fixtures) et `sweeps/test_carto1_long_rlw.py` (5 contrats d'admission, RNG et hooks). Les tests `sweeps/test_carto1_runtime.py` et `sweeps/test_carto1.py` couvrent toujours le canal CARTO-1 original. Au total, **45 tests ciblés passent**.

### Exposition 1024² sur trois ans : volume insuffisant

Campagne de référence diagnostique saine `results/carto1_long_shadow1024_3x3_20261024` : trois parties terminées à horizon complet (graines `42`, `100`, `999`, 1970–1972, carte 1024², un Docker et dix CPU au plus), `probes=50331650`, image `openttd-lab:latest` SHA `f4b2b9b3…`. Tous les trois balayages RLW-04b se terminent avec 30 paires fixées. Les **coûts CARTO terminés** comptent respectivement **24, 30 et 30** ; les **A* terminés**, **0, 7 et 8**. Les 90 épisodes complets nécessaires au seuil et à la validation croisée n'ont donc pas été observés à trois ans. **AUC, sensibilité, spécificité et économie au seuil : non calculables sur cette campagne**, pas de verdict favorable. Les coûts observés ne rapportent aucun franchissement de tick. L'extension distincte à **dix ans** figure ci-dessous.

### Extension 1024² sur dix ans : zéro échec et plafond de tick non tenu

La campagne distincte `results/carto1_long_shadow1024_3x10_20261024` contient **trois parties achevées à dix ans** (graines 42, 100, 999 ; 1970–1979 ; une répétition ; carte 1024²). La provenance du JSON et du manifeste est concordante, mais le comparateur `sweeps/analyze_carto1_long.py --years 10 --require-complete` **refuse le statut complet** de l'échantillon.

| Graine | Coûts achevés | A* terminés | OK / échecs | Coût `route/route_blocks` médian (appariés) | Ops cartographie (échantillon) | Ops A* terminés | Max itérations |
|---|---:|---:|---:|---:|---:|---:|---:|
| 42 | 30/30 | 30/30 | 30 / 0 | 279,8 | 5 369 509 | 17 809 574 | 1 225 |
| 100 | 30/30 | 23/30 | 23 / 0 | 269,2 | 5 689 737 | 12 399 011 | 984 |
| 999 | 30/30 | 30/30 | 30 / 0 | 272,5 | 5 711 170 | 15 748 829 | 461 |
| **Total** | **90/90** | **83/90** | **83 / 0** | **273,0** | **16 770 416** | **45 957 414** | **1 225** |

La médiane totale du coût normalisé est calculée sur les **83 couples coût/A* terminés**, et non sur 90 : l'étendue observée est **195,0 à 599,4 points par bloc**. Ce sont des scores de couloir sur des recherches toutes réussies, sans contraste positif/négatif permettant de calibrer un rejet. Les opcodes de cartographie du tableau comprennent en revanche les **90 coûts** enregistrés, y compris ceux des sept recherches non achevées de la graine 100.

Les **sept issues manquantes** sont les indices 23–29 de la graine 100 ; son `CARTO1_LONG_SUMMARY phase=done` manque. **83/83 A* observés se terminent OK**. Même si les sept derniers échouaient, le total ne pourrait dépasser **7 échecs sur 90**, contre 20 pré-enregistrés. Rejouer plus longtemps les mêmes paires ne peut désormais plus constituer le panel exigé. L'AUC, la sensibilité, la spécificité, le seuil hors graine et les opcodes potentiellement évités **restent indéfinis**. Les totaux ci-dessus représentent les coûts réellement observés, pas une économie théorique.

**Limite du budget tick :** les résumés de la sonde comptent **78 franchissements/dépassements** pour la graine 42 et **69** pour la graine 999 ; les 23 recherches achevées de la graine 100 en comptent **57** sans résumé final. La somme observée est donc **204**, et chacune des **83 recherches A*** terminées signale au moins un franchissement. Des `CARTO1_LONG_ASTAR phase=end` individuels comportent `overruns>0`. La demande de zéro franchissement n'est donc pas satisfaite. Le pathfinder utilisé est bien celui de production, mais les paires utilisent des **extrémités virtuelles** de terrain plat et le plafond dur fixe de 5 000 itérations, et non des plans réels de gare avec leur budget économique variable. Les 83 réussites ne prouvent pas que les échecs de construction réels sont rares.

**Verdict Paires longues : non qualifié**, pour manque de cas positifs et franchissements de tick. Avant une nouvelle campagne, il faut sécuriser les tranches A* et préenregistrer un panel de cas difficiles représentatifs avec extrémités réelles. L'expérience reste en shadow, OFF par défaut ; aucun défaut ni filtre de décision n'est adopté.

Reproduction : `python -X utf8 sweeps/analyze_carto1_long.py results/carto1_long_shadow1024_3x10_20261024_engine --years 10 --format markdown --require-complete` (retour 1 attendu). Analyse détaillée : `results/carto1_long_shadow1024_3x10_20261024_analysis.json`.

### Préparation des prochains bancs — exécution réservée à l'utilisateur

Après le verdict ci-dessus, le code de `probe_carto1_long.nut` a reçu un **arrêt de sécurité irréversible pour le reste de la partie** : dès qu'une tranche de cartographie, la préparation d'un A* ou un pas de recherche franchit un tick, le canal publie `CARTO1_LONG_SAFETY phase=abort` et `CARTO1_LONG_SUMMARY phase=unsafe`, libère son pathfinder et arrête la sonde. La première traversée peut encore se produire dans un `FindPath(1)` atomique : ce changement en réduit la répétition, **sans garantir zéro franchissement**. L'A* en jeu et les politiques par défaut ne changent pas.

`sweeps/analyze_carto1_long.py` exige désormais explicitement `overruns=0` dans les sorties A*, `ticks=0` sur les coûts, `overruns=0 ticks=0` à la fin de RLW-04b, et `overruns=0` dans le résumé terminal. Un compteur absent ou non nul annule la qualification statistique, même en présence d'au moins 20 échecs. Recalcul hors Docker des anciens journaux : `results/carto1_long_shadow1024_3x10_20261024_safety_audit.json` documente **204 traversées** parmi les 83 A* terminés (78 pour la graine 42, 57 pour 100, 69 pour 999), avec 0 échec A*. L'ancienne mesure n'est pas « réparée » rétroactivement.

Pré-enregistrement des expériences futures : `docs/carto1_long_prelaunch_20261024.json` ; commandes PowerShell **manuelles et séquentielles** : `docs/carto1_long_commandes_manuelles_20261024.md`. Les commandes prévoient un smoke 1×1, un diagnostic 3×3 puis, seulement si la santé et les ticks le permettent, une extension 3×10. Un arrêt `phase=unsafe` interdit de poursuivre aux bancs longs. L'inventaire est préparatoire et **aucun des trois bancs n'a été lancé**.

Validation hors Docker : `python -X utf8 -m unittest sweeps.test_carto1 sweeps.test_carto1_runtime sweeps.test_carto1_long_rlw sweeps.test_carto1_long_analysis sweeps.test_v308_quinconce -q` : **66 tests, OK (1 ignoré)** ; compilation Python et `git diff --check` : OK. **La compilation Squirrel de cette nouvelle protection n'est pas encore validée en moteur.** Aucun commit, aucun push ni changement de défaut.

### Relecture intégrale des campagnes et décision de relance (24 octobre, suite)

Le jeu complet de résultats horodatés est présent dans `results/carto1_long_existing_audit_20261024.json`, reproductible avec `python -X utf8 -m sweeps.audit_carto1_long_existing --out results/carto1_long_existing_audit_20261024.json`. Toutes les heures ci-dessous sont **Europe/Paris, UTC+2**. Elles sont extraites des journaux du moteur, et non inférées de l'heure d'écriture des rapports.

| Campagne | Fenêtre locale des journaux | Parties saines | Coûts CARTO | A* terminés OK / ABND+DEAD+NOPA réels | Ops carto COST | Ops A* | Franchissements A* |
|---|---|---:|---:|---:|---:|---:|---:|
| `early1024_3x3` | 15:42–15:43 | 2/3 | 84/90 | 0 / 0 | 15 716 870 | 0 | 0 |
| `shadow1024_3x3` | 15:47–15:49 | 3/3 | 84/90 | 15 / 0 | 15 716 870 | 7 372 386 | 38 |
| `shadow1024_3x10` | 15:50–15:57 | 3/3 | 90/90 | 83 / 0 | **16 770 416** | **45 957 414** | **204** |
| `safe1024_1x5` (graine 999) | 16:01–16:03 | 1/1 | 30/30 | 4 / 0 | 5 711 170 | 2 010 746 | 4 |

Le premier banc utilise un ancien bundle et la graine 100 meurt sur l'erreur Squirrel **`index 'searchStartTick' does not exist`**, corrigée avant les séries shadow suivantes. Les quatre campagnes représentent des **reprises de graines identiques**, pas quatre panels indépendants. Le compteur `CARTO1_LONG_COST` couvre les 30 coûts de la graine 100 en 3×10 malgré l'absence de sa synthèse finale ; le total corrigé de **16 770 416** vient des 90 événements COST et remplace le chiffre incomplet de 15 459 594 du rapport antérieur.

**Fenêtre de concurrence 15:40–16:05 :** d'autres bancs utilisateur ont pu consommer des CPU simultanément. Il est prudent de considérer la durée murale, les mesures d'opcodes et les franchissements comme **potentiellement perturbés**, sans attribuer causalement les dépassements à cette concurrence. Contrôle croisé plus fort : les **7 A*** de la graine 100 et les **8 A*** de la graine 999 terminés dans les deux campagnes `shadow1024_3x3` et `shadow1024_3x10` ont chacun **clé, `search_ops` et `ticks` identiques, 15/15** ; le bundle source de ces deux campagnes a la même empreinte. L'égalité des mesures malgré deux fenêtres d'exécution distinctes constitue un indice de reproductibilité. Les coûts `COST` de la campagne early et de shadow3×3 sont également exactement identiques en cumul.

Un **cinquième résultat plus récent** est disponible : `results/carto1_long_safety_latest1024_s999_1x3_20261024`, exécuté vers **17:53–17:55 heure de Paris**, donc hors de la fenêtre litigieuse. Sa partie est saine à 3 ans, l'énumération de 2 643 couples avec réservoir de 30 et les **30 coûts CARTO** (5 711 170 ops) sont achevés sans franchissement. Mais le **premier A*** (269 itérations, **553 601 ops**) aboutit `OK` avec **1 franchissement**, puis `CARTO1_LONG_SAFETY phase=abort reason=astar_slice_tick_cross` et `CARTO1_LONG_SUMMARY phase=unsafe completed=1 overruns=1` interrompent la sonde. Ce test prouve la réaction du disjoncteur, **pas la conformité du budget sans franchissement**. Son résultat reste impropre à l'estimation de l'AUC.

**Calcul économique possible, mais non qualifiant :** sur les 83 A* terminés de 3×10, la dépense brute est **45 957 414 opcodes A***, contre **16 770 416 opcodes COST** de cartographie (sans imputer ici tous les coûts de sondes, initialisations ou journalisation). **Aucun A* échoué n'existe** dans les épisodes observés : il n'y a ni vrais positifs ni seuil LOSO appris, donc **aucun opcode A* évitable démontré**. Même si les 7 issues manquantes échouaient, ce panel n'atteindrait que **7/20** échecs requis ; le même réservoir ne peut pas satisfaire le protocole, quel que soit le prolongement temporel.

**Décision : ne pas relancer les mêmes bancs**. Le problème est désormais double et structurel : (1) une recherche A* segmentée de production peut franchir un tick, même appelée par pas de 1 et sous réserve de 9 500 opcodes ; l'arrêt de sécurité ne peut pas empêcher le premier franchissement ; (2) les extrémités virtuelles des 90 couples préenregistrés conduisent à 83 succès. Une prochaine campagne ne sera informative qu'après mise au point, **sans changer les défauts**, d'une tranche réellement bornée au niveau de l'algorithme A* et d'un **nouveau protocole indépendant** de cas difficiles avec sites réalistes et échantillon préenregistré, conservant un jeu tenu à l'écart. Aucun benchmark supplémentaire n'a été déclenché lors de cette relecture : les expériences répétées ne peuvent pas remplir le critère `>=20` et le résultat de sécurité récent aurait arrêté la première sonde.

Le parseur `sweeps/analyze_carto1_long.py` rejette maintenant aussi explicitement un `CARTO1_LONG_SAFETY`, tout début de recherche avant **30 SAMPLE + 30 COST**, une distance hors **224–288**, et une prétendue recherche A* réelle sans itération/opcode. Il contrôle également dans le manifeste les `probes`, `script_debug`, la présence du SHA Git et celle de l'empreinte image. Le champ `predictive_validated` est distinct de `complete` : au-delà de données complètes et de 20 échecs, il exige des AUC strictement supérieures à 0,5 sur **chacune** des graines tenues à l'écart, des vrais positifs/négatifs et un solde positif d'opcodes avec le coût CARTO complet. C'est une garde directionnelle minimale, **pas un test de significativité statistique**. Sans classe positive aujourd'hui, les deux champs restent faux.

Sur le 3×10, le rapport brut entre les dépenses est **16 770 416 / 45 957 414 = 36,5 %**. Par graine complètement observée, CARTO représente **30,1 %** des opcodes A* de la graine 42 et **36,3 %** de ceux de la graine 999. Faute du moindre échec, les **opcodes A* évités prouvés valent zéro**, donc le solde descriptif serait **−16 770 416 opcodes** en imputant tous les COST à un filtre qui ne rejette aucune réussite ; ce chiffre n'est **ni** une économie mesurée **ni** une prédiction validée. Les éventuels coûts de préparation et l'interférence avec la cadence de jeu ne sont pas entièrement imputés dans cette différence.

La vérification finale hors Docker passe **68 tests unitaires (67 réussis, 1 ignoré)**, la compilation Python, l'audit sur cinq campagnes, et `git diff --check`. La compilation Squirrel de la protection a entretemps été prouvée par le banc de sécurité `safety_latest1024_s999_1x3`, mais son premier A* franchit toujours un tick. **Aucune nouvelle partie n'a été démarrée dans cette reprise** : la relance à protocole inchangé serait invalide et ne pourrait atteindre l'objectif de 20 échecs. Aucun défaut, commit ni push n'a été modifié.

**Contrôle de reprise supplémentaire :** nouvel audit complet des cinq campagnes depuis les journaux, **68/68 tests sans échec (1 ignoré)**, puis nouvelle exécution de `sweeps/analyze_carto1_long.py` sur `shadow1024_3x10` avec `--years 10 --require-complete` : sortie **1 attendue**, `campaign_verified=True`, `complete=False`, `predictive_validated=False`, **83/90**, **0/20 échecs**. La vérification croisée rejette aussi les 204 franchissements historiques, les sept indices absents de la graine 100 et son résumé terminal manquant. Aucun nouveau run Docker n'est utile avant un nouveau protocole préenregistré et la correction du budget tick.
