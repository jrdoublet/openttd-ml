# CARTO-2 — préparation cartographique des longs trajets rail (24 octobre 2026)

## Objet et contrat

L'objectif est d'exploiter le reliquat réel d'opcodes à la fin des tours de 1970 à
1974 et les fenêtres de stabilité **sans projet finançable** observées par V309.
Le jeu, le financement, les projets AIR et les recherches rail réelles restent
prioritaires. CARTO-2 est un consommateur **shadow**, sans construction ni
persistance Save/Load. L'activation exige simultanément les sondes RLW-04b
(bit 24), CARTO-1 (bit 25) et V309 (bit 26), soit
`probes=117440770` avec panneaux bit 1 et journal bit 8. Le défaut
`probes=2` est inchangé. Aucun nouveau AddSetting n'est introduit : les
31 bits du masque sont déjà affectés.

La sonde utilise les paires longues non périssables de RLW-04b (224–288 tuiles)
et des candidats rail du portefeuille réel. Le score de classement du réservoir
est `AIIndustry.GetLastMonthProduction(src,cargo) ×
AICargo.GetCargoIncome(cargo,distance,jours_estimés)`. Ce score n'est pas un
profit net. Pour les paires du réservoir, les deux extrémités du premier A*
sont des sorties **virtuelles** choisies près des industries, comme dans
CARTO-1 LONG ; elles ne constituent pas des plans de gare réellement construits.
Les travaux ultérieurs doivent retenir, lorsqu'ils existent, les vrais plans
du constructeur pour le sous-ensemble des projets live.

Le corridor est une ligne de blocs de 8×8 élargie de ±1 bloc. Chaque lecture
unique `OpexV308Arm(...,1)` produit un coût heuristique. On journalise
séparément les blocs centraux, la bande entière, l'eau, le relief et les
obstacles bâtis, puis un plus court chemin Dijkstra sur la bande. Les
`line_ops` et `band_ops` sont des **coûts marginaux de lectures du cache**
dans un ordre fixé, et non la totalité des opcodes de planification ;
`line_cost`, `band_cost`, `route` sont des points arbitraires. `quote`
est un devis grossier en £, non un montant de construction garanti.

L'indicateur ville de V308 `s.town` utilisait
`AITile.GetTownAuthority`, qui renvoie une autorité locale même loin du bâti.
La carte CARTO-2 compte désormais maisons et routes réelles, en excluant les
routes d'un bloc sans maison du coût urbain. Une instrumentation supplémentaire
inventorie les centres AITown, en distinguant le comptage de centres des
échantillons construits. Cela corrige la confusion de sémantique derrière les
58 % de blocs marqués « ville » sans prétendre que six échantillons par bloc
donnent une occupation cadastrale exhaustive.

Le vrai moteur rail reçoit en mode shadow son paramètre de guidage
`_guideTiles` issu des blocs de la route coarse. Le libre et le guidé
utilisent la même paire et les mêmes extrémités figées, séquentiellement.
La préparation du guide est découpée et les A* font des appels
`FindPath(1)` avec garde de reliquat et journal des ticks. Un A* réel
prioritaire interrompt le shadow (`CANCEL`). Il faut surveiller la limite
fondamentale : une expansion atomique du moteur V296 peut encore coûter
plus que le reliquat disponible, même avec le contrôle préalable. Dans ce
cas `CARTO2_SAFETY phase=abort` arrête la sonde ; **zéro tick traversé doit
être démontré en jeu, il n'est pas garanti par le seul contrat statique**.
Les plans retenus sont transitoires, avec expiration à 180 jours.

## Campagnes initiales exécutées

Tous les bancs utilisent `sweeps/run_c66_reference.py`, OpenTTD 15.3,
OpenGFX 7.1, adversaire AAAHogEx-115 figé, image
`openttd-lab:latest` SHA256 `f4b2b9b3…`, carte partagée, 10 CPU au maximum
et un seul Docker à la fois. Les variantes expérimentales ont
`probes=117440770`, références `probes=2`. Le banc est **diagnostique**,
pas une porte V102 d'adoption.

| Campagne / carte | Horizon | Santé parties | Paires recensées | Coûts achevés | Recherches libre/guidé appariées |
|---|---|---|---:|---:|---:|
| `carto2_smoke256_1x1_20261024`, 256², 42 | 1 an | 2/2 complètes | 18 | 2 | 0 |
| `carto2_smoke1024_1x1_20261024`, 1024², 42 | 1 an | 2/2 complètes | 36 (30 longues, 6 live) | 1 | 0 |
| `carto2_expo1024_3x5_20261024`, 1024², 42/100/999 | 5 ans | 6/6 complètes | 108 (90 longues, 18 live) | **3** | **0** |

Les premières parties ne déclenchent aucun A* CARTO-2 terminé. Pour la
campagne 3×5, le dernier état observé est toujours
`CARTO2_SUMMARY phase=progress` ; il n'y a pas de
`phase=done` et le critère `--require-complete` échoue. La fin des
trois parties à 1974 **ne prouve pas l'achèvement du travail shadow**.

| Graine 1024² 3×5 | Couloirs achevés | Ligne, ops de lecture | Bande ±1, ops de lecture | Surcoût bande | Blocs ligne / bande | Ticks mesurés cartographie | A* libre | A* guidé | Plans prêts démontrés fin 1974 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 42 | 1 | 26 804 | 121 282 | 94 478 | 21 / 95 | 0 | 1 annulé, 3 itérations, 6 270 ops | 0 | 0 observé, état final non certifié |
| 100 | 1 | 28 054 | 112 233 | 84 179 | 22 / 88 | 0 | 0 | 0 | 0 observé, état final non certifié |
| 999 | 1 | 25 543 | 122 589 | 97 046 | 20 / 96 | 0 | 0 | 0 | 0 observé, état final non certifié |
| **Total** | **3** | **80 401** | **356 104** | **275 703** | **63 / 279** | **0** | **3 itérations, 6 270 ops, CANCEL** | **0** | **aucun plan prouvé prêt** |

Le rapport de coût bande/ligne vaut **4,43×** sur ces trois observations
pour le temps de lecture de blocs ; il correspond à 279/63 = **4,43×**
autant de blocs étudiés. Cela ne mesure pas un gain de routage.
La carte RLW des couloirs achevés comporte 37 détections de maison et
26 de route proches du bâti sur les six points de chacun des 279 blocs,
dont un seul couloir présente cinq unités urbaines sur son chemin coarse.
Le devis heuristique vaut respectivement **228 500 £** (graine 42),
**213 500 £** (100) et **233 500 £** (999), sans validation constructeur.

## Re-test apparié final sur les trois graines, 1024², 1970–1974

La campagne indépendante
`results/carto2_paired1024_3x5_20261024_r2`
utilise le bundle source SHA256
`88db3f4a93397f6d8299933b36ea3295086888cd2fc498a1b7dc18aa1c652da7`,
le même que les smokes OFF sans `script_debug`. Les six parties sont
`complete` et `game_ok`. Le mode ON conserve `script_debug` pour les
journaux de preuve CARTO-2 ; la référence de chaque duel porte `probes=2`.
L'analyseur vérifie la concordance de la provenance JSON/manifeste
(`campaign_verified=True`, sans erreur), tout en refusant
`--require-complete` pour l'échantillon CARTO-2 :
`log_complete=False` et `SUMMARY phase=done` absent.

| Graine | Paires identifiées (long/live) | Couloirs calculés | A* libre (issue, itérations, ops) | A* guidé (issue, itérations, ops) | Ticks CARTO-2 traversés | Plans prêts au 31/12/1974 |
|---|---:|---:|---|---|---:|---:|
| **42** | 30 / 6 | 1 | CANCEL, **2**, **5 197** | CANCEL, **4**, **6 939** | **0** | **0** |
| **100** | 30 / 6 | 1 | aucun épisode terminé | aucun | **0** | **0** |
| **999** | 30 / 6 | 1 | CANCEL, **442**, **862 164** | aucun | **0** | **0** |
| **Total** | **90 / 18** | **3** | **444 itérations, 867 361 ops** | **4 itérations, 6 939 ops** | **0** | **0** |

Au total, **448 itérations A*** et **874 300 opcodes** ont été mesurés
sur les fragments réellement exécutés, sans franchissement de tick
signalé. Les trois recherches terminées sont toutes des
`CANCEL` dus à la priorité au rail de production. La seule paire
libre/guidé appariée, id 0 de la graine 42, donne
`libre − guidé = −2 itérations, −1 742 opcodes` **entre deux recherches
inachevées**. Aucun raccourcissement ni coût de tracé complet n'est
estimable ; le taux de plans réellement prêts est **0/36 par graine**, soit
**0/108** déclarés. Le compteur terminal de plans prêts n'est pas attesté
par `SUMMARY phase=done`, mais aucun `SEARCH outcome=OK` n'apparaît
dans les logs des parties complètes : aucun plan prêt n'a été publié
par le canal.

Les trois paires prioritaires ont exactement **63 blocs centraux contre
279 blocs de bande**. Les coûts de **lecture** sont
**80 401 opcodes pour la ligne**, **356 106 pour la bande**, soit
**275 705 opcodes supplémentaires** et un facteur **4,43×**.
Les trois premiers couloirs présentent respectivement
**maisons/routes = 9/7, 10/7, 18/12** dans les échantillons
full6, au lieu d'un marqueur d'autorité urbaine. Les
`real_towns=-1 town_centers_complete=0` du re-test déclarent
honnêtement que l'inventaire facultatif des **centres de ville
géographiques** n'était pas complet lors de chaque mesure.
Il ne faut pas transformer ce `-1` en zéro ni les maisons/voies
échantillonnées en surface urbaine exhaustive. Les scénarios recensent
toujours jusqu'à 36 paires mais la chaîne ne complète qu'une paire
au mieux dans les cinq années fixées.

La comparaison économique ON − OFF du re-test donne **+61 636 £/an**
en moyenne de `profit_year`, **2 victoires / 1 défaite**,
IC95 bootstrap **[−1 167 623 ; +905 456]**, Wilcoxon **p=1**,
ratio moyen des valeurs de compagnie **0,983991** (−1,60 %).
Le harnais conclut **`diagnostic_only`**. Ces valeurs différentes
du premier essai montrent la sensibilité de l'ordonnancement à
l'instrumentation ; elles ne prouvent aucun gain CARTO-2 et ne
qualifient pas un changement de politique.

**Verdict d'exposition : non qualifié.** La cible de **zéro tick
traversé** est tenue sur les étapes journalisées par cette campagne,
mais la comparaison des coûts, de la qualité et de la disponibilité
des **trajets libres vs guidés achevés** est impossible : pas un seul
des deux modes ne fournit un chemin OK. Le blocage principal est la
préemption avant achèvement par le rail réel, puis le faible nombre
de créneaux de fin de tour, et non le seul coût arithmétique d'un
couloir. L'inventaire incomplet des centres ville et la
couverture d'une paire sur 36 limitent la portée du diagnostic.

La seule mesure A* CARTO-2 observée est le témoin libre de la graine 42 :
`CARTO2_SEARCH id=0 mode=free outcome=CANCEL iters=3 ops=6270 ticks=0`
daté du 1er décembre 1972. Le guidé n'a pas commencé. Par conséquent,
**delta d'itérations/opcodes, comparaison des longueurs, ratio de réussite
et disponibilité exacte fin 1974 ne sont pas calculables** sur cette
première exposition. Afficher un gain de 6 270 opcodes ou zéro plan comme
preuve exhaustive serait erroné.

## Économie de l'exposition, sans verdict d'adoption

Résultat terminal ON − OFF pour la campagne 1024² 3×5 :
**−1 157 742 £/an** de `profit_year` en moyenne, **0 victoire / 3 défaites**,
IC95 bootstrap **[−1 490 509 ; −847 549]**, Wilcoxon
bilatéral **p = 0,25** ; ratio des moyennes de valeur de compagnie
**0,853556**, soit **−14,64 %**. Le verdict du harnais est
`diagnostic_only`, car il ne s'agit pas d'une porte V102. Ces écarts ne
permettent pas d'imputer précisément la perte au guidage, absent des logs.
La valeur de compagnie dépasse négativement la garde de −5 %.

## Premier re-test libre / guidé (graine 42, carte 1024², 5 ans)

Campagne distincte `results/carto2_paired1024_seed42_1x5_20261024`
(bundle source SHA256 `8ba7fca98c866cf90261f35138ea298ba55126f7e842470070f5c7bb93dc4956`).
La garde de travail de la recherche est abaissée à 7 400 opcodes restant
pour mieux utiliser le reliquat de fin de tour, avec une seule itération
`FindPath(1)` et arrêt de sécurité au premier tick franchi. La recherche
shadow est immédiatement annulée à l'entrée d'une recherche rail live.
Les deux extrémités d'une même paire sont figées pour éviter des tests de
sites différents entre libre et guidé.

La graine 42 permet pour la première fois la jointure réelle
`id=0 key=freight:1:529591:692300` des deux bras :

| Recherche | Issue | Itérations | Opcodes | Ticks traversés | Plan prêt |
|---|---|---:|---:|---:|---:|
| Libre (23 novembre 1970) | CANCEL | 2 | 5 194 | 0 | non |
| Guidé (2 juillet 1971) | CANCEL | 4 | 6 936 | 0 | non |

La différence de **−2 itérations** et **−1 742 opcodes** (libre − guidé)
compare uniquement deux fragments censurés à des dates différentes,
préemptés par le jeu réel. Elle ne mesure **ni accélération ni ralentissement
du guidage à tracé achevé**. Aucun résultat sur la longueur du chemin n'est
calculable ; zéro tick traversé sur ces fragments reste un résultat local.
Le dernier résumé publie 1 paire comparée sur 36, 0 plan prêt et pas de
`phase=done`. L'autre bras du duel et le scénario sont complets et sains.

## Identité OFF avec le témoin propre

`sweeps/compare_carto2_off.py` compare les sorties JSON finales et les
26 checkpoints JSONL, en retirant uniquement les identifiants et champs
de provenance. Le témoin CARTO-1 propre est figé ; aucune partie existante
ni aucun bundle n'est modifié.

| OFF CARTO-2 (référence du smoke) vs référence propre | Checkpoints métier divergents / 26 | Champs checkpoint divergents | JSON final divergent | Conclusion |
|---|---:|---:|---:|---|
| 256², graine 42 | 12 | 24 | 5 | non-identité stricte ; profit, valeur et liquidités égaux |
| 1024², graine 42 | 14 | 74 | 25 | non-identité stricte ; opcodes, liquidités et notes divergent |
| Témoin propre 1024² contre répétition du même bundle | 0 | 0 | 0 | répétabilité observée |

Deux smokes supplémentaires ont été effectués avec CARTO-2 OFF et
`script_debug` **désactivé**, comme le témoin propre :
`carto2_off_clean256_1x1_20261024` et
`carto2_off_clean1024_1x1_20261024` (bundle commun SHA256
`88db3f4a93397f6d8299933b36ea3295086888cd2fc498a1b7dc18aa1c652da7`).
Ils sont chacun **1/1 complets**. Sur 256², leur JSON présente seulement
**4 champs différents**, tous des opcodes ou ratios associés, contre
5 avec `script_debug` activé ; les 26 checkpoints gardent 12 écarts,
24 champs. Sur 1024², les chiffres ne changent pas : 14 checkpoints,
74 feuilles et 25 champs JSON différents. Les profits, valeurs et
principales métriques économiques 256² restent identiques. La seule
normalisation opérée pour ces vérifications concerne les métadonnées
de campagne ; aucun champ d'opcode ou de jeu n'est masqué.

Sur 256², le cumul `observed_opcodes_total` final est
**3 251 894 contre 3 251 915**, soit **−21** ; les différences JSONL
sont des compteurs d'opcodes et les diagnostics apparentés. Sur 1024²,
les compteurs terminaux d'opcodes Opex passent de **9 373 222** à
**9 411 226** et sa caisse de **18 413 £** à **32 426 £** ;
la caisse AAAHogEx passe de **43 082 £** à **65 314 £**.
Les profits et valeurs terminaux principaux restent égaux.
Les bundles de code ne sont pas identiques, et le mode script_debug diffère
entre certains essais historiques : l'identité demandée est donc
**non démontrée**, sans attribution causale isolée à CARTO-2.

## Reproduction et réserves

```powershell
python -X utf8 -m unittest sweeps.test_carto1_long_rlw sweeps.test_carto2_runtime sweeps.test_carto2_analysis -q
python -X utf8 sweeps/analyze_carto2.py results/carto2_expo1024_3x5_20261024_engine --format markdown
python -X utf8 sweeps/analyze_carto2.py results/carto2_paired1024_3x5_20261024_r2_engine --result-json results/carto2_paired1024_3x5_20261024_r2.json --manifest results/carto2_paired1024_3x5_20261024_r2.manifest.json --format markdown
python -X utf8 sweeps/compare_carto2_off.py results/carto2_off_clean256_1x1_20261024.json ../carto1_reference/results/carto1_reference_off256_1x1_20261024.json
```

Pour les provenance et journaux complets : fichiers
`results/carto2_*.json`, `.jsonl`, `.manifest.json`,
`*_bundle/` et `*_engine/`. Chaque appel de campagne génère son
propre bundle SHA256 ; ne jamais mélanger les versions pré- et post-correctif
pour prétendre à un appariement.

La sonde reste expérimentale et éteinte. Aucun défaut n'a été changé,
aucun commit ni push effectué.

## CARTO-2b — diagnostic de la perte puis ordonnanceur à tours entiers (24 octobre 2026)

### Étape 1 — autopsie **avant** toute modification

Les six parties de la première exposition
`results/carto2_expo1024_3x5_20261024` sont complètes. Le bundle
**figé de cet essai historique**, différent de CARTO-2b, porte la SHA256
`99ed2aea04572eb4c458bbfd0a11ce3f75b17838e90888af8849224102fa6c3a`.
Sa manifestation prouve `script_debug=True` **dans les deux bras** ;
il est donc faux d'attribuer la perte au seul paramètre `--script-debug`.
En revanche, ON = `probes=117440770` inclut le bit **256** de
`DECISION_LOG`, tandis qu'OFF = `probes=2` ne l'inclut pas. Les journaux
OPEX de janvier 1970 comptent respectivement **63 / 79 / 78** événements
ON (graines 42/100/999), contre **0 / 0 / 0** OFF ; sur cinq ans,
**13 917 / 9 287 / 7 864** événements ON contre
**115 / 84 / 81** OFF. Les logs OFF ne permettent donc pas de
reconstituer les décisions AIR détaillées à un niveau équivalent.

Les premiers écarts de **l'état du jeu** apparaissent sur les
**trois graines avant les premières lectures CARTO-2** et sur
**deux graines sur trois avant le démarrage de RLW-04b**
(la graine 42 diverge en mars, après son début RLW en février) :

| Graine | Premier écart ON vs OFF, checkpoint | Première activité RLW-04b / CARTO-2 | Trajectoire AIR en fin 1974 |
|---|---|---|---|
| **42** | **1er mars 1970** : trésorerie 126 391 £ contre 126 387 £ (écart **+4 £**) ; premier écart d'aéroports **1er novembre 1970**, **2 contre 4** | RLW **23 février** ; CARTO-2 **9 juin** ; premières lectures **juillet** | **23 contre 25** aéroports ; **18 contre 24** avions, **5 000 contre 5 600** places |
| **100** | **1er février 1970** : **0 contre 1** avion, trésorerie **260 886 £ contre 199 363 £** ; premier `AIR_BUILD` ON le **2 février** | RLW **13 mars** ; CARTO-2 **15 mai** ; premières lectures **octobre** | **2 contre 8** aéroports ; **2 contre 7** avions, **600 contre 1 700** places |
| **999** | **1er février 1970** : **1 contre 2** aéroports, trésorerie **277 057 £ contre 246 941 £** ; premier `AIR_BUILD` ON le **2 février** | RLW **13 février** ; CARTO-2 **27 avril** ; premières lectures **août** | **4 contre 6** aéroports ; **4 contre 6** avions, **1 200 contre 1 600** places |

Pour la première campagne, ON − OFF en `profit_year` terminal vaut,
par graine, **−1 490 509 / −1 135 168 / −847 549 £/an**,
soit **−1 157 742 £/an** en moyenne. Les valeurs de compagnie
agrégées valent **19 591 088 £ ON contre 22 952 323 £ OFF**,
soit **−14,64 %**. Les écarts de capacité AIR constituent le
**médiateur économique visible** : constructions ou mise en service
retardées, puis croissance de flotte et revenus inférieurs.
Cette chronologie exclut une causalité directe des **premiers couloirs**
CARTO-2 dans la divergence initiale ; elle ne départage pas V309,
le surcoût du journal, l'ordre des autres sondes et les
perturbations ultérieures de CARTO-2.

Le travail directement instrumenté sur les trois mondes est de
**1 739 176 opcodes RLW-04b** (605 622 / 596 492 / 537 062),
**593 919 opcodes CARTO-2 cartographie** (202 892 / 186 730 / 204 297)
et **6 270 opcodes A\*** (graine 42 seulement, trois itérations
`CANCEL`), total **2 339 365 opcodes** sur trois parties de cinq ans.
Ce total exclut le surcoût de `DECISION_LOG`, V309 et les
éventuelles perturbations du scheduler : **ce n'est pas un budget
économique causal**. La métrique V309 `stable_unfunded_ops` mesure
des travaux de la boucle de jeu, *pas* des opcodes consommés par
CARTO-2. La file CARTO-1 reste alimentée mais n'est pas vidée lorsque
CARTO-2 prend la place de `OpexCarto1Step` ; on observe
`pending=16` (plafond) pour la graine 42 le 31 mai 1971,
`pending=13` pour 100 et `pending=3` pour 999,
sans preuve de `queueDrops` ni de perte AIR propre à cette file.
Contrairement à une première hypothèse de lecture de `main.nut`,
la sonde CARTO-1 LONG se désarme d'elle-même sous CARTO-2 :
**aucun deuxième A\* LONG en activité simultanée** n'est attesté.

**Conclusion diagnostique chiffrée :** la perte observée est portée
par le sous-déploiement AIR (jusqu'à **6 aéroports et 5 avions de moins**
sur la graine 100), mais **l'effet propre de CARTO-2 est non identifiable**
dans l'essai initial, à cause des sondes et du journal non appariés.
Il serait inexact d'attribuer la perte de **−1,16 M£/an** aux seuls
**0,594 M opcodes** cartographiques (pour trois mondes cumulés).

Un témoin diagnostique spécifiquement destiné à isoler le journal,
`carto2_diag_equal_log1024_3x5_20261024`, a été commandé
**avant l'édition CARTO-2b** sur trois graines : référence
`OpexAI[probes=258]` (DECISION_LOG activé) contre
`OpexAI[probes=117440770]`, `--script-debug` commun.
**Aucun conteneur n'a démarré** : le client `docker run`
s'est bloqué avant toute création de fichiers `results` ;
le client bloqué a été arrêté sans conteneur en cours.
Il n'existe **aucun résultat économique de ce témoin**.
Cela empêche d'affiner aujourd'hui le partage causal entre
journal et travail shadow.

### Étape 2 — CARTO-2b implémenté dans le worktree, non encore qualifié en jeu

L'état, les fonctions et les résultats historiques CARTO-2 restent distincts
de la **nouvelle version expérimentale 2b**, toujours activée seulement
par la conjonction des bits 24, 25, 26 :

- Dans les **deux boucles** (normale et profilée), un tour dédié est
  affecté **en tête** de boucle lorsque V309 a constaté au tour
  normal précédent une sélection `unfunded_snapshot` stable.
  Le début de tour revalide le coût, le capital disponible,
  la révision du monde, l'absence de recherche/worker/
  expansion rail active, les travaux PO01C et le portefeuille.
  **Trois tours shadow consécutifs au plus** précèdent obligatoirement
  un tour normal. Sinon, toute la boucle du jeu conserve la priorité.
- La carte construit exclusivement les **centres Bresenham**
  de blocs 8×8 dédupliqués, utilise le lecteur **full6**, puis le
  Dijkstra coarse sur ce sous-graphe. `map_mode=line`,
  `band_ops=-1` et `band_cells=-1` signifient
  **bande non exécutée / non mesurée** ; le gain par rapport à la bande
  reste l'**estimation historique**, non une mesure CARTO-2b.
- Un quantum `OpexCarto2FullTurn` exécute plusieurs étapes et
  `FindPath(1)` séquentiels, avec cible de **9 000 opcodes sur
  10 000** (90 %) et au plus **128 étapes**, puis rend le contrôle
  au `Sleep(1)` **unique du dispatcher** pour ce tour.
  Une expansion A\* inconnue requiert initialement une réserve de
  **4 500 opcodes** ; les pas ultérieurs nécessitent la
  **plus grande expansion observée + 1 200**, au minimum
  2 200 et au maximum 6 500. Cette précaution **peut empêcher
  d'atteindre 90 %**, et le coût extrême d'une expansion atomique
  n'est pas encore étalonné en jeu. Chaque opération sensible journalise
  un franchissement potentiel de tick et arrête le shadow en
  `SAFETY` si nécessaire ; **zéro tick reste une exigence de banc,
  pas un résultat 2b acquis**.
- À l'arrivée d'une recherche rail réelle, `YieldToLive` passe
  le `pathfinder` shadow en **pause** sans effacer
  itérations, frontier ni plans. Le travail ne reprend qu'en
  l'absence de recherche rail réelle ; un seul shadow A\*
  est mis en progression à la fois (libre puis guidé).
  Les extrémités `lead` et `station_exit` des vrais
  plans live sont copiées et figées, sans recalcul de devis.
  Les lignes virtuelles RLW restent distinctes des gares physiques.
- Les nouveaux journaux `CARTO2_TURN`, `CARTO2_PAUSE`,
  `CARTO2_RESUME`, `CARTO2_COST map_mode=line` et
  `CARTO2_SUMMARY full_turn_ops/full_turns/paused_turns`
  rendent les opcodes prélevés sur les tours V309 vérifiables.
  Les événements de tour peuvent être **échantillonnés** faute
  d'opcodes de journalisation ; le résumé cumulé fait foi.
  Les analyseurs restent stricts sur la provenance, les parties
  complètes, les deux chemins **OK/OK** pour une comparaison
  d'itérations, opcodes et longueur, et le cache réellement
  présent au 31 décembre 1974.
- La file CARTO-1 n'est plus alimentée sous CARTO-2b
  (`OpexCarto1Request` et hook du rail réel gardés),
  corrigeant le problème d'une file orpheline sans changer
  le comportement normal lorsque CARTO-2 est OFF.

**Contrats statiques :** tests Python ciblés
`sweeps.test_carto2_runtime`, `sweeps.test_v309_idle`,
`sweeps.test_carto2_analysis`, `sweeps.test_carto1_runtime`,
`sweeps.test_carto1_long_rlw` et
`sweeps.test_carto1_long_analysis` :
**95 tests exécutés, 95 réussis**, avec `py_compile`
et `git diff --check` verts. Ces contrats ne remplacent
ni une compilation Squirrel moteur ni une mesure de tick.

La suite élargie
`python -X utf8 -m unittest discover -s sweeps -p 'test_*.py' -q`
a également été exécutée : **2 522 tests, 19 échecs,
5 erreurs, 3 ignorés et 2 échecs attendus** (retour non nul).
Parmi les blocages visibles : `pytest` absent pour trois
modules de tests, anciennes assertions d'ordre exact de boucle
(`test_po01c_regen_split`) incompatibles avec la nouvelle
branche entière, empreintes source historiques
(`test_station_plan_precheck`), contrats non actualisés
`Valuate` pour le module RLW-04b préexistant, et
`test_v158_lazy_select` sur une lecture de `rail.best`
dans le module CARTO-1 antérieur. Ces échecs ne constituent
**ni une validation 2b ni la preuve d'une régression moteur** ;
ils restent à trier et résoudre dans le périmètre de chaque
fonction, sans changer de défaut. Il serait inexact
d'annoncer toute la suite verte.

### Étape 3 — tableau final des mesures CARTO-2b (campagnes terminées)

Le blocage initial du client Docker a été résolu ; les exécutions réelles
et les corrections de sécurité sont détaillées aux étapes 4 à 6.
La dernière campagne appariée est
`carto2b_budget9000_equal_log1024_3x5_20261024` : carte **1024²**,
**1970–1974**, graines **42/100/999**, **6/6 parties moteur saines et
terminées, 3/3 paires ON/OFF**, OpexAI contre le même AAAHogEx figé.
ON `probes=117440770` et OFF `probes=258` partagent `script_debug=True`,
l'image Docker `f4b2b9b3…` et le **même bundle source SHA256
`00bd19838a2e6e891a2c80237dc731de58dfabd234226ba9403a17daee825c29`**.
Le témoin OFF indépendant
`carto2b_budget9000_off258_witness1024_3x5_20261024`
est également **3/3 sain et terminé**, avec cette même provenance.
Les deltas du tableau comparent expressément le **ON final à ce témoin
OFF indépendant** (et non au OFF interne à la campagne).

| Graine | Parties ON/OFF appariées | Plans prêts **31/12/1974** | A* libre/guidé terminés **OK/OK** : itérations, opcodes, longueurs | Ticks CARTO-2b | `CARTO2_TURN` / `full_turn_ops` observés | Δ `profit_year` ON − témoin OFF | Δ valeur ON − témoin OFF |
|---|---|---|---|---|---|---:|---:|
| **42** | **2/2 saines** | **Inconnu** (pas de SUMMARY terminal) | **0 paire OK/OK** ; mesures comparables indisponibles, aucun START | **0 signalé**, aucune activité shadow | **0 événement / 0 opcode observé** ; cumul terminal inconnu | **+3 171 352 £/an** | **+2 973 979 £** |
| **100** | **2/2 saines** | **Inconnu** (pas de SUMMARY terminal) | **0 paire OK/OK** ; libre **≥115 itérations partielles** aux PAUSE ; opcodes, longueur et guidé achevé **non mesurés** | **0 SAFETY signalé** ; absence absolue non démontrée | **141 événements / ≥397 545 opcodes** ; cumul terminal inconnu | **+4 639 185 £/an** | **+10 801 532 £** |
| **999** | **2/2 saines** | **Inconnu** (pas de SUMMARY terminal) | **0 paire OK/OK** ; mesures comparables indisponibles, aucun START | **0 signalé**, aucune activité shadow | **0 événement / 0 opcode observé** ; cumul terminal inconnu | **+779 764 £/an** | **+2 695 152 £** |
| **Moyenne / total** | **6/6 ; 3 paires** | **0 disponibilité terminale attestée** | **0 comparaison OK/OK**, donc aucun delta fiable d'itérations, opcodes ou longueurs | **0 alerte signalée** sur le dernier 3×5 | **≥141 événements / ≥397 545 opcodes**, graine 100 seulement | **+2 863 434 £/an** (3/0/0) | **+86,2397 %** en ratio des moyennes |

Pour la **garde de valeur −5 %**, la somme des valeurs finales OpexAI
est **35 569 362 £ ON** contre **19 098 699 £** pour le témoin OFF,
soit **+86,2397 %** : la garde est **satisfaite numériquement**, avec
les trois valeurs OFF strictement positives. Le lanceur de cette
campagne avait cependant `value_guard_max_loss_pct=100` ; le contrôle
**−5 % est recalculé ici explicitement**, sans transformer le verdict
brut `diagnostic_only` en qualification. Le Wilcoxon reste **p=0,25**
sur seulement trois paires.

Le journal `CARTO2_TURN` est **échantillonné**, et `full_turn_ops` dans
le seul `SUMMARY` de la graine 100 est un **snapshot initial de phase
`progress`**, pas un bilan au 31 décembre 1974. Les **397 545 opcodes**
additionnent seulement les 141 événements lisibles : c'est une **borne
inférieure** de la consommation effective. Les **3 PAUSE / 2 RESUME**
de la graine 100 prouvent la progression d'un A* libre (33, 111 puis
115 itérations), mais **aucun `CARTO2_SEARCH` terminal**. Cinq lignes
CARTO-2 sont illisibles dans ce log ; aucun `CARTO2_SUMMARY phase=done`
n'établit les plans restés en cache au terme. L'analyseur
`sweeps/analyze_carto2.py` refuse à bon droit `--require-complete`.

La campagne antérieure `carto2b_equal_log1024_3x5_20261024`, source
`5b150e4e…`, avait déjà **6/6 parties terminées**, mais la graine
100 a traversé **un tick atomique A*** (deux alertes SAFETY pour le
même franchissement), avec **31 tours et 173 949 opcodes** déclarés
avant arrêt : ce résultat de sécurité reste **un échec**, sans être
confondu avec le dernier bundle `00bd1983…`. Les contrôles intermédiaires
`carto2b_safety1024_seed100_1x5_20261024` (2/2 sains,
143 TURN, 0 SEARCH, 0 SAFETY) et
`carto2b_budget9000_seed100_1x5_20261024` (2/2 sains,
141 TURN, 0 SEARCH, 0 SAFETY) n'ont pas apporté de paire OK/OK.
Le smoke 256² `carto2b_smoke256_equal_log_v2_20261024`
est **2/2 terminé** (ON : issue économique `bankrupt`),
**68 TURN**, **0 SEARCH achevé**, **0 SAFETY**,
delta **−2 511 £/an** et valeur **−0,183 %** ; son OFF n'est pas
directement comparable au témoin 1024² de cinq ans.

**Contrôle indépendant OFF, identité stricte : ÉCHEC.** L'OFF interne
du dernier 1024² contre le témoin OFF de même SHA et options donne
**360/360 checkpoints de chaque côté**, **6 checkpoints différents**,
**76 feuilles JSONL différentes**, **0 manquant** et **93 différences
dans le JSON récapitulatif**. Les graines **42 et 100 sont identiques** ;
la graine **999 diverge** sur **octobre, novembre et décembre 1974**
(3 checkpoints OpexAI, 3 AAAHogEx). Son profit terminal OFF diffère de
**1 £/an** (`887 668` interne contre `887 667` témoin), ce qui explique
le delta **+779 764** ici contre **+779 763 £/an** à l'étape 5.

**Verdict final sur les preuves existantes : CARTO-2b NON QUALIFIÉ.**
La garde de valeur passe arithmétiquement mais aucun A* libre/guidé
**OK/OK** n'est achevé, les plans prêts en fin 1974 ne sont pas
attestés, le cumul final des opcodes et une preuve générale de zéro
tick manquent, et le contrôle OFF n'est pas strictement reproductible.
Sur deux graines le shadow ne démarre même pas : le gain économique
observé reste **diagnostique et non attribuable au guidage**.

### Étape 4 — reprise Docker et première vraie campagne CARTO-2b (24 octobre)

Le blocage d'infrastructure a cessé : `docker run --rm --cpus=1 --memory=1g
openttd-lab:latest python3 --version` rend `Python 3.12.14` (code 0).
Avant les bancs, la garde d'éligibilité a été durcie : elle vérifie aussi
les statistiques de prix modifiables `nextProjectCapital`/`minCapital`
du cache V309 et la file d'intentions réactives C80 ; les champs de cache
existent bien dans `V309_IDLE_STATE`. **96 tests ciblés verts** après ce
correctif et `git diff --check` sans erreur. Les autres échecs de la
suite globale signalés ci-dessus ne sont pas magiquement résolus.

La campagne 256² `carto2b_smoke256_equal_log_v2_20261024` (graine 42,
1970, 2/2 parties complètes) confirme le chargement Squirrel et
**68 événements CARTO2_TURN**, un `CARTO2_COST` ligne seule, aucun
`CARTO2_SAFETY` mais **aucun A* achevé**. Son delta ON − OFF est
**−2 511 £/an**, valeur **−0,183 %**, *diagnostic uniquement*.
Les 68 événements échantillonnés représentent **277 863 opcodes**
observés (moyenne **4 086**, maximum **6 919** par événement) ;
faute de SUMMARY terminal, ce n'est **pas** le cumul autoritaire.

La campagne principale **`carto2b_equal_log1024_3x5_20261024`** a tourné
sur la carte **1024²**, 1970–1974, graines **42 / 100 / 999**, **6/6 jeux
complets**, même bundle source SHA256
`5b150e4e3a386aabe6a0fc3a99a5af881bae27a904242d1c0448d69a0d937ba3`
(identique au smoke 256), même image Docker SHA
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
`--script-debug` commun, OFF **`probes=258`**, ON **`probes=117440770`**
(bit `DECISION_LOG` 256 actif **dans les deux bras**), six workers,
10 CPU, 8 Gio et un seul conteneur. Il ne s'agit pas d'un rejeu du
bundle historique `99ed2a...` : les sources et les canaux de journalisation
ont changé, donc aucune causalité rétroactive n'est démontrée.

| Graine | Δ `profit_year` ON − OFF | Δ valeur société ON − OFF | Activité CARTO-2b dans ON |
|---|---:|---:|---|
| 42 | **+3 171 352 £/an** | **+2 973 979 £** | Aucun `CARTO2_START` malgré RLW done |
| 100 | **+435 575 £/an** | **+514 367 £** | 31 tours déclarés puis SAFETY |
| 999 | **+823 281 £/an** | **+2 739 569 £** | Aucun `CARTO2_START` malgré RLW done |
| **Moyenne / ensemble** | **+1 476 736 £/an**, 3/0/0 | **+32,685 %** ratio des moyennes | **Non attribuable au guidage** |

IC bootstrap 95 % du delta moyen `profit_year` :
**[+435 575 ; +3 171 352] £/an** ; Wilcoxon **p=0,25**,
verdict harnais **`diagnostic_only`**. L'amélioration de résultats
économiques est une observation des bras instrumentés : sur **deux
graines aucun tour CARTO-2b n'a été pris**, il serait donc fautif de
la qualifier de gain causal de la cartographie ou de l'A* guidé.

| Exigence de mesure 3×5 | Résultat **effectivement démontré** pour cette version |
|---|---|
| Parties saines, mêmes source / paramètres debug | **6/6**, manifest vérifié ; appariement graines 42/100/999 |
| Plans prêts par graine au **31/12/1974** | **Non mesurés / non mesurés / non mesurés** ; aucun SUMMARY terminal |
| A* libre et guidé **OK/OK** mêmes paires/monde | **0 comparaison achevée** ; pas de mesure itérations/opcodes/longueurs |
| Tick traversé / sécurité | **ÉCHEC** seed100 le **7 juillet 1970** : `astar_atomic_tick` puis `full_turn_tick` pour le même franchissement |
| OpCodes consacrés aux tours V309 | seed100 : **31 tours / 173 949 opcodes** déclarés avant arrêt ; seeds42/999 : **aucun démarrage et pas de cumul SUMMARY** |
| Ligne seule / bande | 1 `CARTO2_COST` seed100 : **22 blocs**, `line_ops=28 054` ; `band_ops=-1` = **non mesurée** |
| Delta terminal diagnostique | **+1 476 736 £/an**, valeur **+32,685 %**, non causal, non qualifiant |
| Smoke OFF identique à un témoin indépendant, même debug/SHA | **Non encore démontré** |

Sur seed100, le premier `FindPath(1)` atomique consomme **7 844 opcodes**
avec une réserve initiale de seulement 4 500 (puis plafonnée à 6 500).
La réserve ne couvre donc pas le coût observé et **un tick est traversé**.
Deux événements SAFETY enregistrent le même incident : le compteur
`SUMMARY.ticks=2` **double comptabilise** ce franchissement ; cela
ne prouve pas deux franchissements distincts. Les recherches sont
interrompues avant tout `CARTO2_SEARCH` terminal. L'analyseur strict
`--require-complete` refuse donc **correctement** ce banc malgré les
six parties OpenTTD complètes. Les deux graines sans démarrage et le
budget atomique devront être corrigés puis **remesurés avec un
nouveau SHA de bundle**.

**Verdict expérimental de cette première version : NON QUALIFIÉE**
(critère zéro tick violé, zéro paire A* OK/OK et plans terminaux inconnus).
**Aucun défaut modifié, aucun commit ni push.**

### Étape 5 — révision de sécurité et réétalonnage réel A* (24 octobre)

Après le dépassement atomique de la graine 100, la recherche shadow a été
limitée à **une expansion `FindPath(1)` au début d'un tour entièrement
attribué à CARTO-2b** ; une recherche initialisée au cours d'un tour ne
peut commencer ses expansions que lors d'un prochain tour éligible.
Les états du pathfinder et ses itérations survivent aux pauses ; une
alerte `OpexCarto2Unsafe` est désormais **idempotente** pour éviter de
compter deux fois le même dépassement (`astar_atomic_tick` puis
`full_turn_tick`, ou le dépassement cartographique). L'arrêt de sécurité
reste indispensable, puisque le coût atomique de l'API A* ne possède
pas de borne stricte démontrée. Aucun réglage par défaut n'est changé.

**Premier étalonnage, réserve de 9 300 opcodes**, campagne
`carto2b_safety1024_seed100_1x5_20261024`, bundle SHA256
`2c87a8108fd31962f2b13364b11b1ba2a4780d5249a5c45c3077a495d0d4b0d9` :
2/2 parties moteur terminées, **0 SAFETY**, **143 TURN observés**,
**1 coût de ligne**, **1 PAUSE**, mais **0 SEARCH** terminal.
Des tours à seulement **298 opcodes** ont montré que l'admission de
9 300 plus les frais d'appel bloquait également `FindPath(1)` :
cette version est sûre dans l'exposition constatée mais improductive.
Son delta diagnostique pour une seule graine (100) était
**+4 639 185 £/an** et **+344,35 %** de valeur ON/OFF ; il ne
qualifie ni le guidage ni une adoption.

**Réétalonnage 9 000 opcodes réels restants**, ou maximum observé d'un
pas atomique +1 200 s'il est supérieur, sans plafond artificiel.
L'admission prend une marge initiale de 100 opcodes et contrôle un
maximum de 500 opcodes de préambule jusqu'à l'appel effectif ; la
vérification du budget restant, du tick, de la priorité rail et le
SAFETY restent présents. Les **98 tests ciblés** passent, ainsi que
`git diff --check`. La campagne de contrôle graine 100 (cinq ans)
`carto2b_budget9000_seed100_1x5_20261024` a eu **2/2 jeux terminés**,
**0 SAFETY**, **141 TURN**,
**3 PAUSE / 2 RESUME**, sans SEARCH achevé ; le journal de PAUSE
atteste **au moins 115 itérations A*** libres au moment de la dernière
interruption, en septembre 1971. Le chantier rail réel reste prioritaire.

La campagne complète, source figée **SHA256**
`00bd19838a2e6e891a2c80237dc731de58dfabd234226ba9403a17daee825c29`,
`carto2b_budget9000_equal_log1024_3x5_20261024`, compare à nouveau
**ON probes=117440770** et **OFF probes=258**, avec `script_debug=True`
dans les deux bras, même image Docker, même carte **1024²** et années
**1970–1974**, graines **42/100/999**, **6/6 jeux terminés**.

| Graine | Δ `profit_year` ON − OFF | Présence shadow | `CARTO2_SAFETY` |
|---|---:|---|---:|
| 42 | **+3 171 352 £/an** | Pas de `CARTO2_START` | 0 observé |
| 100 | **+4 639 185 £/an** | Recherche libre en progression puis pause | 0 observé |
| 999 | **+779 763 £/an** | Pas de `CARTO2_START` | 0 observé |
| **Moyenne** | **+2 863 433 £/an** | **0 paire A* OK/OK** | **0 signalé** |

Valeur ON/OFF : **+86,2397 %** en ratio des moyennes.
Bootstrap 95 % sur le delta de profit :
**[+779 763 ; +4 639 185] £/an** ; 3 victoires /0 défaite,
Wilcoxon **p=0,25**, verdict harnais **`diagnostic_only`**.
Sur la graine 100, **141 TURN journalisés** (échantillon dépendant
du budget de journalisation), **397 545 opcodes observés** sur ces
événements, moyenne **2 819**, médiane **1 927**, maximum **6 652** ;
**3 PAUSE / 2 RESUME**, **0 SEARCH terminal**, **1 COST** ligne
`line_ops=28 054`, `band_ops=-1` = non mesuré.
Les lignes PAUSE attestaient 33, 111 puis 115 itérations libres.
Il n'existe ni SUMMARY final autoritaire ni instantané de cache au
31 décembre 1974. En conséquence les tours et opcodes réellement
consommés sur cinq ans restent **au moins** ceux journalisés, les
plans prêts par graine restent **non mesurés**, et les itérations,
opcodes et longueurs libre/guidé **OK/OK** restent **non mesurés**.
L'analyseur `--require-complete` rend **code 1** comme prévu.

**Verdict de cette révision : toujours NON QUALIFIÉE** : aucune
traversée de tick n'est signalée dans les sondes effectivement activées,
mais absence d'achèvement A* et de plans prêts ; ni l'admission
de 9 000 opcodes ni ces bons deltas ne démontrent un guide utilisable.
Sur 42 et 999, aucun shadow n'a effectivement démarré ; le delta
économique ne peut donc pas être imputé causalement au couloir.
La stabilité du monde entre A* libre et guidé après pause n'a pas été
démontrée. **Aucun défaut changé, aucun commit ni push.**

### Étape 6 — témoin OFF indépendant à instrumentation égale

La référence seule, campagne
`carto2b_budget9000_off258_witness1024_3x5_20261024`, s'est
terminée **3/3 jeux** avec le même bundle SHA256
`00bd19838a2e6e891a2c80237dc731de58dfabd234226ba9403a17daee825c29`,
la même image SHA256 `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
la même carte, la même référence **probes=258**, le même adversaire,
`--script-debug=True`, les mêmes graines et cinq années.
Ce témoin est **un jeu OFF indépendant**, non une réutilisation du
résultat d'un autre bundle et non le contrôle historique OFF probes=2.

`sweeps/compare_carto2_off.py` compare les résultats complets avec
métadonnées de campagne écartées : **360 contre 360 checkpoints**,
**6 checkpoints modifiés / 360**, **76 feuilles JSONL différentes**,
**0 checkpoint manquant**, **93 différences dans le JSON récapitulatif**.
Les graines **42 et 100** sont rigoureusement identiques pour OpexAI
et AAAHogEx (0 différence de checkpoint). Sur la graine **999**, les
écarts apparaissent seulement aux **1er octobre, 1er novembre et
1er décembre 1974** ; **3 checkpoints OpexAI** présentent **15 feuilles
différentes**, **3 checkpoints AAAHogEx** présentent **61 feuilles
différentes**. Le premier écart OpexAI connu au 1er octobre est de
**1 £ en trésorerie** et d'une entrée de pool de véhicules ; des
écarts de capacité AIR et de valeur AAAHogEx existent aussi.
La cause exacte de cette variabilité tardive n'est pas identifiée ;
**l'exigence « OFF strictement identique au témoin » échoue sur la
graine 999**, même si les SHA et options instrumentales sont identiques.
Ne pas écrire « OFF identique » en se fondant sur les deux autres
graines, ni attribuer mécaniquement ces écarts tardifs au shadow.

**Verdict final expérimental de CARTO-2b, source SHA `00bd1983…` :
NON QUALIFIÉ.** Aucun tick traversé n'est **signalé** par la sonde
sur les trois jeux ON 1970–1974, mais il manque une preuve formelle
de pire cas `FindPath(1)`, une recherche A* libre/guidée **OK/OK**,
des plans prêts fin 1974, un SUMMARY terminal et l'identité complète
du contrôle OFF. Le gain de **+2,863 M£/an** est **diagnostique,
non causal**, et l'expérience ne satisfait pas la porte fonctionnelle.
