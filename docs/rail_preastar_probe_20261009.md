# Rail A* : accès aux quais avant recherche — mesure du 09/10/2026

## Statut et provenance

Le suivi de [l'autopsie du 08/10](rail_astar_prelaunch_20261008.md)
introduit uniquement la sonde passive `probe_rail_preastar`, **défaut 0
aux quatre difficultés**. La sonde n'ajoute aucune règle de décision,
borne A*, priorité ou filtre. À ON, les opcodes de télémétrie peuvent
néanmoins déplacer la trajectoire de simulation.

- Code de départ : `/openttd-ml`, `master`, HEAD `cb23a17`, arbre dirty
  avec d'autres travaux en cours, conservés sans nettoyage.
- Fonctions de la sonde : `ai/OpexAI/rail_preastar_probe.nut` ; chargement
  `main.nut`, déclaration `info.nut`, lecture `settings.nut`, garde
  `globals_pre.nut`, appels `task_rail.nut` et `orchestrator.nut`.
- `RAIL_PREASTAR_START` : identifiant `rid` par recherche dans une partie,
  mode primaire/upgrade/stock, cargo/OD/ligne, budget, nombres de quais
  et signatures ordonnées `[lead,station_exit]` avec voisinage de 4 tuiles
  (libre/eau/rail) **avant le premier FindPath**. Cette mesure est une
  *covariable*, pas un test de chemin.
- `RAIL_PREASTAR_END` : arrêt et itérations cumulées, y compris abandon
  ou timeout, une seule fois par recherche ; `RAIL_PREASTAR_BUILD` :
  construction, échec, attente de cash ou dépôt de stock. Le dépôt
  `ready` n'est pas une construction. L'ID est reporté aux plans stockés.
- Décodeur : `sweeps/analyse_rail_preastar.py` et tests
  `sweeps/test_analyse_rail_preastar.py`. Les doublons, conflits, champs
  illisibles, absences d'END et `BUILD` différés ne deviennent jamais
  silencieusement des réussites/échecs supplémentaires.

## Validation moteur et jeu observationnel

Smoke A/B `rail_preastar_smoke_42x1_20261009_r1` : référence
`OpexAI[probe_rail_preastar=0]`, variante `=1`, seed42, un an, deux
duels complets ; **mêmes résultats Opex** (profit `439524 £/an`,
valeur `397634 £`, 16 véhicules, 19 gares), aucune erreur Squirrel.
Les premiers `START→END→BUILD ready` apparaissent effectivement dans
`results/rail_preastar_smoke_42x1_20261009_r1_engine`. Test de
compilation/exécution et inertie observée à un an seulement, sans
conclusion de neutralité générale.

Collecte diagnostique MONO-BRAS, **sans politique candidate**, campagne
`rail_preastar_collect_5x6_20261009_r2`, cinq graines
`42,100,999,1234,5678`, horizon 6 ans, `script-debug`, 5/5 parties
complètes. Bundle
`ded83cd439aad1d8ece07db9995cf8e00dc189aad8c8bfaa53a309b977f459f9`,
manifeste `79c4dfc8ff22c5cf2ef94cb613a15390d16f7d2fce4bba92e64271c7c7719f97`.
Artefacts : `results/rail_preastar_collect_5x6_20261009_r2.json`,
`.jsonl`, `.manifest.json`, `_engine/` et
`results/rail_preastar_collect_5x6_20261009_r2.analysis.json`.

Sur 54 `START` distincts : **43 recherches A* OK**, **7 `ABND`
avec 10000/10000 itérations**, **4 recherches censurées** (START sans
END avant la fin de la partie). Les 50 autres START/END sont appariés,
aucun doublon ni conflit ; les **quatre avertissements** sont des
`missing_end` correspondant à ces censures.

| Mode | `OK` A* | `ABND` 10000 | En cours à la fin |
|---|---:|---:|---:|
| Primaire | 24 | 6 | 4 |
| Upgrade | 4 | 1 | 0 |
| Stock / préparation C121 | 15 | 0 | 0 |
| Total | **43** | **7** | **4** |

Parmi les 24 primaires `OK` d'A*, **13 chantiers construits**,
**10 échecs de pose** et **1 attente cash** au dernier événement.
Les 4 upgrades `OK` ont donné 3 poses et 1 échec. Les 15 préparations
de stock A* `OK` ont donné **8 constructions observées** et **7 plans
encore seulement `ready`** au dernier événement. On ne peut donc pas
assimiler l'issue du pathfinder à la valeur économique livrée.

Le coût de la lecture locale, mesuré avant l'émission `AILog`, varie
de **699 à 6119 opcodes** selon le nombre de quais ; pour 12+12 quais
il tourne autour de 6100. La journalisation coûte davantage et peut
déplacer la trajectoire. Cette collecte est observationnelle, sans
preuve d'identité des trajectoires avec la sonde OFF.

## Discrimination et verdict

Développement désigné avant la collecte : graines **42, 100, 999**
(4 des 7 `ABND`), réserves prévues : **1234, 5678** (3 `ABND`).
Le critère préalable est d'éliminer une part significative des
recherches plafonnées pour **au maximum un `OK` supprimé**, avant une
validation indépendante. L'exploration a également affiché des
enregistrements des graines réservées ; elle ne permet donc pas de
revendiquer ensuite un essai de seuil complètement aveugle.

Le voisinage local libre ne porte pas un certificat de non-constructibilité :

- **Seed999**, primaire démarré le 04/07/1974, `ABND` le 29/12/1974 :
  12 accès A, **un seul accès B mais trois voisins B constructibles**,
  donc aucune sortie B localement fermée.
- **Seed42**, upgrade démarré le 12/05/1972, `ABND` le 22/12/1972 :
  un accès B avec **zéro** voisin B constructible ; un autre upgrade
  de la même partie, démarré le 22/12/1972 et dont le côté B vaut
  également **zéro**, trouve pourtant un chemin `OK` en 1973.
- Sur les primaires réussis, plusieurs ont aussi un minimum de
  voisins B libres de **zéro**. Un `azero`/`bzero` positif ne prouve
  donc aucune impossibilité ; ponts, tunnels et alternatives de quai
  rendent la règle trop grossière.

Une exploration **univariée sur les graines de développement seulement**
(`na`, `nb`, `amin`, `bmin`, `azero`, `bzero` ; seuils `≤` ou `≥`
aux valeurs observées) porte sur les recherches terminées de
**budget exactement 10 000** : 7 `ABND` et 27 `OK` au total,
dont 4/17 en développement et 3/10 sur les graines réservées.
Les 15 recherches stock à budget moindre, une primaire `OK` de
seed100 à budget 4 848, et les quatre censures sont exclues du test
de précision, et restent visibles séparément dans le JSON.
La recherche de seuil laisse seulement deux règles capturant au
moins un plafond avec au maximum un `OK` sacrifié. Leur application
descriptive aux deux graines réservées montre l'absence de transfert :

| Règle candidate issue du développement | Développement : ABND détectés / OK perdus | Graines réservées : ABND détectés / OK perdus |
|---|---:|---:|
| `nb ≤ 1` | 2 / 1 | **0 / 1** |
| `bmin ≥ 3` | 1 / 0 | **0 / 2** |

Cette comparaison est **exploratoire**, car des enregistrements des
graines réservées ont été consultés pendant l'analyse et ne sont plus
strictement aveugles. Même ainsi, les deux règles échouent à retrouver
les trois plafonnements des graines réservées. Ne jamais considérer
`bmin ≥ 3` comme un certificat d'échec : le caractère paradoxal du
signal reflète seulement l'insuffisance du voisinage local.

**Aucun prédicteur assez fiable n'est démontré.** Il n'y a donc
**aucun filtre ajouté, aucun réglage de comportement nouveau, aucun
banc économique A40×5 et aucune porte B20×10**. Le fait de libérer du
créneau A* ne prouve pas que les lignes supplémentaires sont rentables.
Les défauts historiques restent inchangés.

## Portée et limites

La sonde couvre les A* reprenables `primary`, `upgrade` et `stock`.
Le chemin synchrone historique `rail_search_resumable=0` n'est pas
couvert ; l'analyse ne doit pas se présenter comme exhaustive si ce
profil est activé. Le compteur ID est transitoire dans la partie :
l'appariement inclut impérativement fichier, bras, graine, répétition
et `rid`. Aucune validation Save/Load de la sonde n'a été exécutée.

Pour démontrer une cause géométrique, il faudrait des données plus
proches des transitions natives `_Neighbours` et des contraintes
pont/tunnel ; ce nouveau diagnostic montre que la seule disponibilité
des quatre voisins d'un `lead` n'est pas suffisamment discriminante.
Ne pas transformer la corrélation de la destination ou du relief en
garde sans contre-épreuve sur les chemins `OK`.

## Suite du 09/10 — observation de la frontière segmentée

L'audit suivant a identifié le mécanisme à instrumenter : au défaut courant,
`policy_rail=1` active la recherche segmentée, et
`v129_rail_astar_exact_opt=1` son moteur V129. Les 10 000 itérations
peuvent couvrir plusieurs recherches de segments et retours arrière,
chacune avec son propre ensemble de nœuds explorés. Les signatures de
voisinage `START` ne permettent pas de distinguer ces trajectoires.

Sous la **même garde `probe_rail_preastar=1`**, sans nouveau réglage
décisionnel, chaque véritable coupure de segment enregistre :

- `RAIL_PREASTAR_FRONTIER rid=... segment=... iters=... used=...`
  `open=... sampled=... viable=... backtracks=... prefix=...` ;
  `open` provient du `Count()` du tas déjà vivant, `sampled` des
  candidats déjà extraits par `OpexFrontierAlternatives`, et `viable`
  des alternatives retenues par `OpexCanAppendSegment`.
- L'événement `END` inclut désormais `segments/backtracks/choices/`
  `alternatives/prefix/active_open/segment_used`. `active_open=-1`
  indique qu'il n'y a plus de tas actif : ce n'est pas une frontière
  mesurée comme nulle.
- L'identifiant reste celui de la recherche primaire/upgrade/stock.
  Les `FRONTIER` se regroupent avec START/END/BUILD dans
  `sweeps/analyse_rail_preastar.py`, sans convertir les recherches
  censurées en `ABND`. Un événement incomplet ou contradictoire
  reste `non_pairable`. Les anciens logs sans FRONTIER sont compatibles.

Aucun échantillonnage supplémentaire de `_Neighbours`, nouveau
`BuildRail`, nouveau tri de tas ni chemin A* auxiliaire n'est ajouté.
La sonde ON reste susceptible de modifier le calendrier des recherches
par ses opcodes et ses logs. Elle observe le fonctionnement **après**
le démarrage d'A* : même une séparation nette `ABND/OK` ici ne serait
pas encore un prédicteur ex ante autorisant un filtre.

À l'ajout : tests HOST de l'analyseur **16/16**, diagnostics rail
connexes **10/10**, `git diff --check` OK. Smoke moteur
`rail_preastar_frontier_smoke_42x1_20261009_r1` :
2/2 parties complètes, profit et valeur Opex identiques OFF/ON
(439 524 £/an, 397 634 £), 3 recherches stock `OK` appariées avec
résumé segmenté et zéro avertissement du décodeur. Ces recherches
font moins de 2 000 itérations, donc aucune coupure `FRONTIER`
n'est encore exposée par ce smoke. Bundle
`56e2d91c4997a84909da52b87d27a7381812e81c0ef2776274ca7efd6a9cce49`,
manifeste
`7476fb386274c7461092d4ef24d6109c043bbdcc649b2c2b866b610b54611244`.

Nouvelle collecte observationnelle décidée avant lecture des issues :
`rail_preastar_frontier_5x6_20261009_r1`, graines indépendantes
`7,512,65537,515222,230185`, six ans, mono-bras
`OpexAI[probe_rail_preastar=1]`. Les trois premières serviront
à explorer les motifs internes, les deux dernières seulement
à décrire leur transportabilité. Aucun seuil prédictif, ni porte
économique n'est pré-enregistré : cet essai ne qualifiera aucun filtre.
Ne pas réutiliser l'ancien 5×6 comme validation de seuil.

### Résultat de la collecte FRONTIER (09/10)

Les **5/5 parties** ont terminé en bonne santé. Bundle figé :
`d85053ddcd41e57aa5a9f325ed5e783432643a45b227f1f0d8948a077da5cd7a` ;
manifeste :
`282f74d54a5fda5e4006221fc711e138818ef07445b38ffe4ae1dbb04c6723c5`.
Artefacts : `results/rail_preastar_frontier_5x6_20261009_r1.json`,
`.jsonl`, `.manifest.json`, `_engine/` et
`.analysis.json`. L'analyseur dénombre **57 RID**, dont
**45 `OK` A\*, 6 `ABND` à 10000/10000, 2 `NOPA` et 4
recherches censurées**. Les 53 recherches achevées sont appariées,
sans événement invalide ni doublon ; quatre avertissements
`missing_end` correspondent aux recherches toujours en cours
à la fin de 1975 (aucune issue attribuée).

| Mode | OK A\* | ABND 10000 | NOPA | Censuré |
|---|---:|---:|---:|---:|
| Primary | 21 | 4 | 0 | 3 |
| Upgrade | 9 | 2 | 2 | 1 |
| Stock | 15 | 0 | 0 | 0 |
| **Total** | **45** | **6** | **2** | **4** |

La nouvelle observation écarte une hypothèse simple d'épuisement
précoce de la frontière : **les 6 ABND**, les **12 OK** atteignant
une coupure et les **2 NOPA** ont tous `viable=3` à la
*première* coupure. Les ouvertures de tas se recouvrent :
`open=977` sur un ABND seed515222, mais `open=980`
sur un OK seed512. Les 6 plafonnements sont distincts :

- Seed **515222**, trois primaires `ABND` (COAL, PASS, PASS) :
  5 segments et 0 backtrack chacun, cinq coupures à
  `viable=3` avec une frontière encore large (minimum
  des cinq `open` de chaque recherche : respectivement
  315, 912 et 564). `active_open=-1` au END signifie
  que le pathfinder a été libéré après la dernière coupure,
  **pas** que le tas était vide.
- Seed **65537**, deux upgrades COAL `ABND` :
  4 segments et 2 backtracks chacun ; le dernier
  `active_open` vaut respectivement 1569 et 1579.
- Seed **7**, un primaire COAL `ABND` :
  3 segments, 1 backtrack ; `active_open=2903`.
- Les deux `NOPA` de seed515222 sont des upgrades :
  chacun 2006 itérations, 4 segments et 2 backtracks.
  Leurs premières frontières conservaient 486 nœuds
  ouverts et 3 alternatives viables : ces alternatives
  ne garantissent donc pas non plus un chemin final.

Cette mesure isole une **consommation du budget à travers
les segments/reprises alors que des branches existent encore**,
et distingue ce phénomène de `NOPA`, mais ne démontre
aucune impossibilité géométrique ou prédiction ex ante.
Une diminution de plafond supprimerait aussi des `OK`
sur des trajectoires comparables ; aucun seuil n'est
autorisé sur ces seules données. Cette campagne n'est pas
un A/B OFF/ON économique : les différences de profits face
à AAAHogEx n'évaluent pas l'effet de la sonde.

**Verdict : aucune politique nouvelle, aucune porte A/B de
qualification, défaut `probe_rail_preastar=0` maintenu.**
Une future preuve pré-A* demanderait des caractéristiques
du corridor/accès reliées directement aux contraintes
réelles `AIRail.BuildRail` ; les compteurs de frontière
observés ici n'existent qu'après avoir dépensé des itérations.

### Reconstitution des échecs par RID

Les lignes ci-dessous sont extraites du JSON d'analyse de la
campagne `rail_preastar_frontier_5x6_20261009_r1`. `open₁`
et `viable₁` désignent **la première coupure de segment**, jamais
l'état *avant* A*. `open_fin` désigne `active_open` lu à
`END` ; `−1` signifie « plus de pathfinder actif ». Chaque
ligne possède un `START` et un `END` valides.

| Graine / RID | Mode | Issue | Itérations | Segments | Retours arrière | Coupures | `open₁` / `viable₁` | `open_fin` |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 515222 / `25607_7` | primary | ABND | 10 000 | 5 | 0 | 5 | 977 / 3 | −1 |
| 515222 / `33722_11` | primary | ABND | 10 000 | 5 | 0 | 5 | 1 082 / 3 | −1 |
| 515222 / `37315_12` | primary | ABND | 10 000 | 5 | 0 | 5 | 986 / 3 | −1 |
| 65537 / `34409_8` | upgrade | ABND | 10 000 | 4 | 2 | 1 | 342 / 3 | 1 569 |
| 65537 / `37349_9` | upgrade | ABND | 10 000 | 4 | 2 | 1 | 342 / 3 | 1 579 |
| 7 / `19152_6` | primary | ABND | 10 000 | 3 | 1 | 1 | 1 005 / 3 | 2 903 |
| 515222 / `32366_9` | upgrade | NOPA | 2 006 | 4 | 2 | 1 | 486 / 3 | −1 |
| 515222 / `33282_10` | upgrade | NOPA | 2 006 | 4 | 2 | 1 | 486 / 3 | −1 |

Les `NOPA` ne sont **pas** des `ABND` : ils se terminent
avant la limite d'itérations, faute de continuation trouvée après
les essais internes. Les trois `ABND` de graine 515222 ont un
`open_fin=-1` parce que la frontière du dernier segment est
libérée au moment du `END`, et non parce que leur `open`
aurait atteint zéro. Les champs `segments`, `backtracks` et
`choices` décrivent les reprises *internes* ; ils ne
comptabilisent ni projets supplémentaires ni lignes construites.

Les contre-exemples `OK` empêchent d'interpréter une frontière
importante ou `viable₁=3` comme preuve de blocage :

| Graine / RID | Mode | Issue A* | Itérations | Première frontière `open₁/viable₁` | Résultat observé après A* |
|---|---|---|---:|---:|---|
| 512 / `23453_13` | primary | OK | 4 460 | 980 / 3 | attente cash |
| 512 / `18991_10` | primary | OK | 2 243 | 1 235 / 3 | construction |
| 65537 / `19895_7` | primary | OK | 2 241 | 1 130 / 3 | construction |
| 512 / `39301_19` | primary | OK | 6 304 | 966 / 3 | aucune construction finale attestée |

Ce sont des **contre-exemples descriptifs** : le budget total
consommé et le succès sont connus a posteriori. Ils ne constituent
pas une validation d'un prédicteur. Les `viable` sont limités
par la largeur d'alternatives de la recherche segmentée ; `3`
signifie « trois alternatives retenues au contrôle », et non
« exactement trois chemins géométriquement possibles ».

Quatre autres `START` n'ont pas de `END` dans l'horizon
(seed230185 `32097_7`, seed515222 `39786_13`,
seed65537 `39477_10`, seed7 `32122_8`).
Leurs 3, 1, 1 et 3 coupures respectives restent disponibles
dans `frontier_history` mais **aucun résultat final n'est
imputé**. Les quatre warnings `missing_end` du décodeur
portent précisément sur ces quatre RID.

### Contrôle de reproduction et conditions d'emploi

Depuis la racine `/openttd-ml`, le rapport est reproductible
**hors moteur et sans relancer Docker** avec :

```powershell
python -X utf8 sweeps/analyse_rail_preastar.py results/rail_preastar_frontier_5x6_20261009_r1_engine --out results/rail_preastar_frontier_5x6_20261009_r1.analysis.json
python -X utf8 -m unittest discover -s sweeps -p test_analyse_rail_preastar.py
```

La source primaire reste les cinq journaux `.log` du dossier
`_engine/`, qui contiennent les événements datés et les RID.
Le JSON de résultat et le manifeste servent à vérifier la
complétude des cinq parties et l'identité du bundle.
L'analyseur conserve séparément `START`, `FRONTIER`,
`END` et `BUILD` ; l'appariement doit inclure
**fichier/bras/graine/répétition/RID**, et non le RID seul
entre deux parties. Les tests HOST valident le décodage et
les cas malformés ; le smoke valide l'exécution Squirrel,
mais pas l'invariance de trajectoire au-delà d'un an.

**Usage autorisé des conclusions :** documenter un épuisement
de budget à travers plusieurs segments/reprises, pas
inférer une cause géométrique unique, décider d'un abandon
avant A*, extrapoler un gain de rentabilité, ni déclencher
les portes A40×5/B20×10. L'instrumentation de la frontière
observe des variables connues seulement après le lancement
de la recherche. Un filtre éventuel demanderait une
signature *ex ante* issue des transitions réalisables,
une confrontation aux `OK` sacrifiés, puis une validation
sur graines réellement indépendantes.
