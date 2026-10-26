# V307 1.9b — censure des puits fret, étape 0 (21/10/2026)

**Mesure hors partie**, sur les 40 journaux du bras `reference` de
`results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine`.
Commande reproductible :

```powershell
python -X utf8 sweeps/diag_v307_sink_censure.py
python -X utf8 sweeps/diag_v307_sink_censure.py --json
```

Le script lit les `RAIL_ATTEMPT shared_dest=1 join_end=B` et les `RAIL_BUILD` ;
il ne lance aucune partie. Il identifie les puits par `(graine, dst)` et ne
compte comme puits initialement ouvert que ceux ayant une première construction
`shared_dest=0`. Les 18 puits reconstruits auparavant dans le rapport 1.10
sans première construction observable sont écartés du dénominateur. L'absence
d'identifiant physique de gare impose cette approximation.

## Demande observée, tentatives et censure

| Mesure | Valeur |
|---|---:|
| Journaux référence, dix ans | 40 |
| Puits initialement ouverts et observés | **701** |
| Puits ayant fait l'objet d'au moins une tentative de nouvelle jonction | **306 / 701 = 43,7 %** |
| Puits ayant reçu plusieurs lignes | **248 / 701 = 35,4 %** |
| Puits visés, mais jamais rejoints | **58 / 306 = 19,0 %** |
| Destinations de tentatives sans première construction observée | 26 |
| Tentatives `shared_dest=1`, total | **986** |
| `OK` | 387 (39,2 %) |
| `SITEAB` | **491 (49,8 %)** |
| `ABND` | 69 (7,0 %) |
| `SITEA` / `TRKFAIL` / `STNFAIL` | 12 / 20 / 7 |

**La demande révélée est supérieure au nombre de puits effectivement
rejoints.** L'indicateur précédent « 64,5 % de puits à une ligne » mélange
les puits sans tentative et ceux dont la tentative échoue. La demande
observée (43,7 %) reste une borne inférieure de la demande potentielle :
les projets jamais proposés ou jamais tentés n'apparaissent pas dans le journal.
Cette correction ne prouve pas qu'un quai supplémentaire convertirait chacune
des tentatives en nouvelle ligne : les sites ou les voies peuvent aussi être
physiquement impraticables.

Les `SITEAB` sont décomposés d'après les **jonctions réussies précédemment sur
la même destination**, au moment de l'échec :

| Jonctions précédentes | `SITEAB` |
|---:|---:|
| 0 (tentative de deuxième ligne) | **244** |
| 1 (troisième ligne) | 110 |
| 2 | 58 |
| 3 | 18 |
| 4 | 58 |
| 5 | 3 |

**26/10 — correction d'interprétation, sans changer le tableau historique.**
Le lecteur `sweeps/diag_v307_sink_censure.py` comptait ci-dessus les `SITEAB`
sur des destinations dont aucune ligne initiale non partagée n'était observée.
La relecture des mêmes 40 journaux de référence sépare désormais ces tentatives :

| Jonctions réussies précédentes | `SITEAB` total historique | Initiale non partagée observée avant la tentative | Initiale non observée |
|---:|---:|---:|---:|
| 0 | 244 | 225 | 19 |
| 1 | 110 | 101 | 9 |
| 2 | 58 | 53 | 5 |
| 3 | 18 | 18 | 0 |
| 4 | 58 | 18 | 40 |
| 5 | 3 | 3 | 0 |
| **Total** | **491** | **418** | **73** |

Sur 986 `RAIL_ATTEMPT`, **121** surviennent sans ouverture initiale observée
(73 `SITEAB`, 6 `ABND`, 33 `OK`, 8 `SITEA`, 1 `STNFAIL`). Un `RAIL_BUILD`
`shared_dest=1` vu après une tentative réussie ne remplace pas la preuve
d'une construction initiale. La formulation « tentative de deuxième/troisième
ligne » n'est donc pas justifiée pour les 73 `SITEAB` orphelins, notamment
40 des 58 cas de la classe 4. Le nouveau champ
`failure_by_prior_joins_known_initial` décrit la sous-population documentée ;
`failure_by_prior_joins` conserve les **491** historiques et
`attempt_reasons_without_observed_initial` décrit les tentatives orphelines.
Même avec ouverture initiale observée, l'absence d'identifiant de gare ne
permet pas de prouver le nombre physique de quais ou la constructibilité.
Aucune conclusion économique ni aucun verdict V307R/P4 n'est changé.

Les 69 `ABND` ont toutes `iters=5000` (médiane = p90 = maximum = 5 000),
ce qui indique ici l'épuisement du budget de recherche enregistré. **Le côté
disponible pour un quai parallèle est impossible à reconstruire** : ni la
géométrie de la voie initiale ni le sens `left/right` des emprises candidates
ne figurent dans ces `RAIL_ATTEMPT`. Les champs `startx`/`endx` sont des codes
de statut (0 ou −1), pas les coordonnées du quai.

## Par catégorie de destination

Le dénominateur est la première ouverture observée (701 puits), par catégorie
inférée du cargo livré ; la proportion « multi » porte sur les constructions
réussies, comme le tableau 1.10, mais sur une population explicitement
restreinte aux puits dont l'ouverture est connue.

| Catégorie | Puits ouverts | Au moins une tentative de nouvelle ligne | Tentés, jamais joints | Plusieurs lignes effectivement reçues |
|---|---:|---:|---:|---:|
| Aciérie | 121 | 51 (42,1 %) | 9 | 42 (34,7 %) |
| Centrale électrique | 131 | 78 (59,5 %) | 14 | 64 (48,9 %) |
| Raffinerie | 80 | 40 (50,0 %) | 6 | 34 (42,5 %) |
| Scierie | 103 | 52 (50,5 %) | 7 | 45 (43,7 %) |
| Usine | 132 | 85 (64,4 %) | 22 | 63 (47,7 %) |
| Banque | 4 | 0 | 0 | 0 |
| Ville, marchandises | 39 | 0 | 0 | 0 |
| Ville, voyageurs | 91 | 0 | 0 | 0 |

Les industries de fret montrent de **42 à 64 % de puits sollicités**. Les
usines et les centrales sont les plus exposées aux tentatives : 85/132 et
78/131. Les 0 des catégories ville/banque ne décrivent que les tentatives
`shared_dest=1 join_end=B`, pas l'intégralité des autres formes de connexion.

## Suite à tester (étape 1 du prompt 5)

Le signal justifie de tester les deux options enregistrées dans
[`lot_21102026_soir.md`](prompts/lot_21102026_soir.md) : réserver l'emprise
d'un second quai parallèle sans surcoût initial (bit 1), ou construire d'emblée
deux quais dans les destinations fret à plusieurs sources (bit 2). Mesurer
pour chaque option les jonctions réussies, `SITEAB`/`ABND`, les lignes neuves,
le coût et les opcodes en conditions identiques. Aucune qualification
économique ni changement de défaut n'est tiré de cette étape 0.

## Préparation de l'étape 1 — tests avant code (file A, 21/10 soir)

Le fichier `sweeps/test_v307_sink_room.py` a été écrit avant toute modification
V307R du builder. Les **cinq tests de référence Python** couvrent : condition
`freight` + au moins deux producteurs **distincts du même cargo**, exclusion
des jonctions déjà existantes, bandes perpendiculaires de 1 ou 2 tuiles avec
leur sortie, orientation opposée à la source et repli sur la liste initiale.
Les tests d'intégration statique sont **rouges par construction** tant que le
réglage `v307_sink_room` et sa logique Squirrel ne sont pas implantés.

Plan de raccordement proposé, à valider après livraison et banc V307S :

1. Déclarer `v307_sink_room` masque `0..3`, défaut `0` aux quatre profils,
   une lecture dans `settings.nut` et la globale correspondante.
2. Dans `OpexRailTryPlatformLength`, filtrer **les seuls plans B libres** de la
   première ligne fret vers une industrie, quand `catalog.producers[cargo]`
   contient au moins deux sources. Garder tous les plans d'origine lorsque
   aucun ne laisse de place. Les candidats `shared_dest`, avec `joinPlatform`
   ou les voyageurs gardent le traitement existant. Tester la bande et sa
   tuile d'entrée (constructibles et plates, `AITestMode` moteur), côté opposé
   au départ ; ne pas confondre une gare initiale avec une gare déjà jointe.
3. **Préserver physiquement la bande** pendant l'A* : ajouter ses tuiles aux
   `ignoredTiles` dans les deux constructeurs du builder
   `OpexCreateRailPathfinder` et `OpexCreateSegmentedSearch`. Les passages
   bloquant et reprenable ont actuellement leurs appels dans deux modules
   (`builder_rail.nut` et `task_rail.nut`) ; cette interception dans les deux
   constructeurs permet de ne pas toucher `task_rail.nut`.
4. Pour le bit 2, seul un second quai **adjacent** (`dist=1`) peut être bâti
   par `BuildRailStation(..., 2, ...)` ; si le côté libre est négatif, l'ancre
   physique du rectangle doit être décalée sans modifier l'interface du quai
   choisi pour l'A*. Propager largeur/ancre au devis physique
   `OpexSimulateRailInfraCost`, aux deux constructeurs
   `OpexExecuteRailPlan` et `OpexV190ExecuteRailPlan`, ainsi qu'à
   `OpexRollback` : sinon le surcoût est oublié ou un quai reste orphelin.
5. Journaliser `V307R_SITE` seulement sous `decision_log`, avec le nombre de
   plans avant/après filtre, le côté, le bit actif et les opcodes. Vérifier le
   plafond ×1,3 en partie, avec les deux réglages 1 et 2 séparément.

**Point à résoudre avant le bit 2 :** `OpexJoinPlatformPlans` exige aujourd'hui
`AITile.IsBuildable` sur chaque tuile du nouveau quai et appelle
`BuildRailStation(..., 1, existingStationId)` ; or un quai déjà construit par
le bit 2 n'est plus constructible et ne sera donc **pas réutilisé** par cette
fonction. Permettre à une seconde ligne de reprendre ce quai prébâti touche
le chemin de jointure, qui sort du périmètre initial « choix du plan B de la
PREMIÈRE construction ». Le test `test_built_spare_platform_must_be_reusable_on_later_v178_join`
rend cette limite explicite. Ne pas lancer le bit 2 avec l'hypothèse d'une
augmentation des jonctions avant de régler ce point. Le côté opposé à la
source est par ailleurs un substitut de l'approche réelle de la voie : les
premiers segments A* devront confirmer qu'ils n'empiètent pas sur la bande.

## Étape 1 codée — V307R expérimental, en attente de smoke

Le code garde `v307_sink_room = 0` aux quatre profils, lecture unique dans
`settings.nut` et globale initialisée à zéro. Modes expérimentaux **1**
(emprise réservée, un seul quai construit), **2** (construction immédiate de
deux quais à la destination) et **3** (combinaison avec repli sur une bande
seulement réservable). L'éligibilité exige une **première ligne fret vers
une industrie**, sans `joinPlatform`/destination déjà partagée, avec au
moins deux producteurs du même cargo dans `catalog.producers`.

Seuls les plans B sont filtrés. Pour chacun, une bande de même longueur et
sa tuile d'entrée sont vérifiées du côté transversal opposé à la source,
à une ou deux tuiles, avec vérification native sous `AITestMode`.
Distance 1 : la simulation vérifie une gare de deux quais ; distance 2 :
elle vérifie la constructibilité de la bande éloignée. Aucun site satisfaisant
⇒ liste des plans B originelle conservée. Pour une longueur retenue,
`OpexCreateRailPathfinder` et `OpexCreateSegmentedSearch` protègent
les tuiles et le lead réservés ; le chemin effectivement choisi est ensuite
revérifié avant tout devis. Journal `V307R_SITE` : `before`, `after`,
`side`, `bit`, `ops`, `fallback` (seulement sous `decision_log`).

Pour le **bit 2**, le devis `AIAccounting` appelle `BuildRailStation`
avec `num_platforms=2` et l'ancre physique appropriée ; les deux exécuteurs
rail font strictement la même pose et `OpexRollback` retire également
le second quai. Les attributs du quai libre sont enregistrés dans
`platformB` de la ligne, y compris après Save/Load. Lors d'une future
jonction V178, `OpexJoinPlatformPlans` vérifie que ce quai appartient à
la gare et que son entrée est libre, le réutilise sans reposer ni démolir
la gare et ne le détruit **jamais** au rollback de cette seconde ligne.
Ce cas était le blocage identifié à la préparation de l'étape 1.

**Coût et entretien.** Le capital total de la pose à deux quais est le
devis natif réel avant financement et sert à recalculer amortissement,
profit et ROI. Sous `economy.infrastructure_maintenance=1`, le
supplément annuel d'entretien des **L tuiles de gare supplémentaires**
est estimé à partir de `AIInfrastructure.GetInfrastructurePieceCount`
et `GetMonthlyInfrastructureCosts`, par la croissance du coût entre
`N + 2L` et `N + 3L` (loi de maintenance d'OpenTTD proportionnelle à
`N × (1 + √N)`). La charge n'est ajoutée qu'une fois à `runningAnnual`.
L'incertitude résiduelle est annoncée par `V307R_MAINT unknown=1` si
la société n'a pas encore d'infrastructure de gare permettant de calibrer
le coefficient du moteur : aucune charge inventée n'est alors ajoutée.
Ces estimations et la limite de coût d'opcodes ×1,3 devront être confirmées
en partie ; les tests hors partie ne peuvent pas les mesurer.

Vérification hors Docker :

```powershell
python -X utf8 -m unittest discover -s sweeps -p 'test_v307*.py' -q
# 34 tests OK
$env:PYTHONPATH='sweeps'
python -X utf8 -m unittest sweeps.test_v131_rail_repair sweeps.test_v131_town_clearance sweeps.test_v153_rail_end_jump sweeps.test_v296b_astar_native -q
# 48 tests OK
```

**Bancs à faire par le prime, sans chevauchement Docker :** smoke 1×1
avec `decision_log=1` et `--script-debug`, d'abord bit 1 puis bit 2 ;
ensuite expositions **3×10** séparées, mêmes graines **42, 7, 100**,
chaque bit contre `v307_sink_room=0`. Vérifier l'absence d'erreur
Squirrel, `V307R_SITE` / `V307R_MAINT`, la réutilisation réelle d'un
quai prébâti, l'évolution `RAIL_BUILD` / `SITEAB` / `ABND`,
le capital et l'entretien et les opcodes des sites. Critères enregistrés :
+50 % de réussite relative des jonctions et −40 % de `SITEAB+ABND`,
sans perte du nombre de lignes neuves. Aucune porte lancée.

## Mesure V307R sur le bundle gelé `78d2aa5e` (21 octobre au soir)

L'analyseur reproductible est `sweeps/diag_v307r_exposition.py`, qui lit les
journaux moteur et le JSON final de chaque campagne sous
`results/v307r_bench_clean_20261021/results/`. Le manifeste donne le commit
`78d2aa5e1329e8905cdc026d648f43a5d65821d0`, arbre propre, et le bundle
`51e0a09a4a1c7f35b7fcabf6ad9aac20c55506127f5eb7bfd5220cef52897f97`.
Les comparaisons de volumes ne mélangent jamais des graines sans leurs deux
bras ; si le JSON final est absent ou qu'un seul bras existe, tous les critères
restent `not_evaluable`.

### Smokes 1×1, année 1970 (graine 42)

| Campagne | Sites V307R | Plans avant → après | Replis | Opcodes/site médiane, p90 | Tentatives rail | Lignes rail |
|---|---:|---:|---:|---:|---:|---:|
| `v307r_bit1_smoke_retry1_20261021` | 3 | 36 → 16 | 0 | 4 758 ; 5 487,6 | 0/0 | 0/0 |
| `v307r_bit2_smoke_1x1_20261021` | 3 | 36 → 16 | 0 | 3 591 ; 11 183,8 | 0/0 | 0/0 |

Les deux sondes sont exposées dans le choix de site : trois filtrages effectifs
sur chaque variante. Aucun `RAIL_ATTEMPT` ni `RAIL_BUILD` n'a cependant été
émis pendant les smokes. Ils ne renseignent donc ni la conversion en jonctions,
ni les échecs de construction. Le `profit_year` initial ne contient que trois
trimestres valides et n'entre pas dans la comparaison économique.

### Bit 1 : réserver une bande, exposition 3 graines × 10 ans

Campagne `v307r_bit1_expo_3x10_20261021`, **3/3 paires complètes** (42, 7,
100), aucune erreur Squirrel. Le témoin porte `v307_sink_room=0`, la variante
`=1`, `decision_log=1` pour les deux bras.

| Mesure | Témoin | Bit 1 | Écart / lecture |
|---|---:|---:|---:|
| `V307R_SITE` | 0 | 65 | 60 sans repli, 5 avec repli |
| Plans proposés avant → après filtre | — | 700 → 316 | 57 événements réduisent la liste |
| Opcodes du filtre, total | — | 283 947 | médiane 4 640 ; p90 5 766,6 |
| `RAIL_ATTEMPT` | 117 | 117 | 0 |
| `RAIL_ATTEMPT ok=1` | 74 | 77 | +3 |
| `SITEAB` | 27 | 11 | −16 |
| `ABND` | 2 | 13 | +11 |
| `SITEAB + ABND` | **29** | **24** | **−17,24 %** |
| Tentatives de jonction B (`shared_dest=1`) | 54 | 43 | −11 |
| Jonctions B construites / tentatives | 23/54 (42,6 %) | 20/43 (46,5 %) | **+9,2 %** de taux relatif |
| `RAIL_BUILD` total | 74 | 77 | +3 |
| Lignes neuves (destination non partagée) | **51** | **57** | **+6** |

Les critères structurels préenregistrés donnent **2 échecs / 1 succès** :
le taux de réussite des jonctions monte de seulement 9,2 % contre +50 % exigés ;
`SITEAB+ABND` baisse de 17,24 % contre −40 % exigés ; les lignes neuves ne
baissent pas (+6). Le nombre brut de jonctions construites diminue de 23 à 20.
La diminution des `SITEAB` est partiellement compensée par davantage d'`ABND`.

Au terme des dix ans, Δ `profit_year` OpexAI moyen = **+52 791,7 £/an**
(IC95 bootstrap **[−73 138 ; +224 218]**, Wilcoxon p=0,75, 2 victoires sur 3).
La valeur de société évolue en moyenne de **−220 136,7 £**
(IC95 bootstrap **[−1 572 772 ; +767 711]**). Le moteur de comparaison
rend `fail_primary` ; ce 3×10 n'est pas une porte économique d'adoption.

**Limite opcodes :** les opcodes des 65 appels `V307R_SITE` sont directement
mesurés, mais le témoin `v307_sink_room=0` n'exécute pas ce filtre et n'a donc
pas de mesure du coût équivalent par plan. Le plafond de coût ×1,3 ne peut pas
être validé par le simple ratio d'opcodes des tentatives, qui englobe A*, pose,
choix de paire et trajectoires économiques différentes.

### Bit 2 : bâtir immédiatement deux quais

Campagne `v307r_bit2_expo_3x10_20261021`, **3/3 paires complètes** (42, 7,
100), six parties saines, zéro erreur Squirrel, `comparison_complete`,
`adoption_sample_complete` et `metric_coverage_complete` vérifiés dans le JSON
final. Même commit/bundle que le bit 1. Le témoin porte `v307_sink_room=0`,
la variante `=2`, `decision_log=1` pour les deux bras.

| Mesure | Témoin | Bit 2 | Écart / lecture |
|---|---:|---:|---:|
| `V307R_SITE` | 0 | 57 | 51 sans repli, 6 avec repli |
| Plans proposés avant → après filtre | — | 618 → 316 | 48 événements réduisent la liste |
| Opcodes du filtre, total | — | 181 002 | médiane 3 267 ; p90 4 030 |
| `RAIL_ATTEMPT` | 119 | 114 | −5 |
| `RAIL_ATTEMPT ok=1` | 74 | 73 | −1 |
| `SITEAB` | 26 | 15 | −11 |
| `ABND` | 5 | 17 | +12 |
| `SITEAB + ABND` | **31** | **32** | **+3,23 %** (hausse) |
| Tentatives de jonction B (`shared_dest=1`) | 54 | 43 | −11 |
| Jonctions B construites / tentatives | 23/54 (42,6 %) | 21/43 (48,8 %) | **+14,66 %** de taux relatif |
| `RAIL_BUILD` total | 74 | 73 | −1 |
| Lignes neuves (destination non partagée) | **51** | **52** | **+1** |

Les critères structurels préenregistrés donnent **2 échecs / 1 succès** :
+14,66 % de réussite relative des jonctions contre +50 % exigés ;
`SITEAB+ABND` augmente de 3,23 % alors qu'une baisse de 40 % est exigée ;
le nombre de lignes neuves ne baisse pas (+1). Le total de jonctions
construites passe de 23 à 21. La baisse des échecs `SITEAB` est plus que
compensée par les `ABND` (5 → 17).

Le bilan économique est **défavorable sur chacune des trois graines** :
Δ `profit_year` OpexAI moyen = **−569 884,3 £/an**, médiane −618 419 £/an,
IC95 bootstrap **[−669 247 ; −421 987]**, 0 victoire / 3 défaites.
La valeur de société baisse en moyenne de **−1 732 326 £**,
IC95 bootstrap **[−2 813 947 ; −654 548]** et ratio des moyennes
**−8,328 %**. Le verdict économique du harnais est
`fail_primary_and_value_guard`. Les résultats ne justifient pas d'adopter le
bit 2.

**Bilan des deux essais :** les deux mécanismes sont réellement activés dans
la sélection des sites, mais **aucun ne passe les critères structurels**.
Le bit 1 donne un profit moyen positif mais non concluant à trois graines ;
le bit 2 présente une perte de profit et de valeur. Les réglages conservent
leur défaut `0`. Les mesures d'opcodes V307R permettent de comparer le coût
*absolu des sondages activés* (bit 1 : 4 640 opcodes médians ; bit 2 : 3 267),
mais ne valident pas le plafond relatif ×1,3 : aucun chemin témoin ne mesure
le même travail de sélection sans filtre et les tentatives ferroviaires ne sont
pas des appels appariés sur un état physique identique. **Aucune porte
d'adoption n'est autorisée par ces campagnes exploratoires 3×10.**

## Bits 4 et 8 (22/10)

### Étape 0 — autopsie hors partie des abandons

Analyse reproductible, sur les **3/3 paires saines** de chaque campagne du
21/10 (bundle `51e0a09a4a1c7f35b7fcabf6ad9aac20c55506127f5eb7bfd5220cef52897f97`) :

```powershell
python -X utf8 sweeps/diag_v307r_exposition.py --abnd --campaign v307r_bit1_expo_3x10_20261021
python -X utf8 sweeps/diag_v307r_exposition.py --abnd --campaign v307r_bit2_expo_3x10_20261021
```

L'option `--abnd` rapproche par campagne, bras, graine, répétition, paire
exacte `(src,dst)` et ordre du journal chaque `RAIL_ATTEMPT ABND` de son
dernier `V307R_SITE` antérieur. Aucun site d'une autre paire n'est imputé.

| ABND, trois graines | Bit 1 | Bit 2 |
|---|---:|---:|
| Témoin / variante | 2 / **13** | 5 / **17** |
| Variante : filtrés (`after < before`, `fallback=0`) | **3** | **3** |
| Variante : non filtrés (`fallback=1` ou `after=before`) | **0** | **0** |
| Variante : sans `V307R_SITE` de même paire | **10** | **14** |
| Paires ABND communes au témoin et à la variante | **0** | **0** |
| Paires ABND variante avec une tentative quelconque dans le témoin | **3** | **2** |

Les six abandons filtrés (`freight`, `shared_dest=0`, aucune tentative
intermédiaire de même paire) donnent les réductions suivantes :

| Bit | Graine | `src → dst` | Plans avant → après |
|---|---:|---|---:|
| 1 | 100 | `7548 → 32285` | 12 → 2 |
| 1 | 100 | `57293 → 27842` | 12 → 5 |
| 1 | 100 | `4664 → 25972` | 12 → 3 |
| 2 | 42 | `63361 → 56143` | 12 → 1 |
| 2 | 42 | `12890 → 55647` | 12 → 3 |
| 2 | 42 | `9580 → 4884` | 12 → 3 |

Les dix ABND sans site au bit 1 sont **neuf jonctions fret
`shared_dest=1` et un trajet voyageurs** ; ceux du bit 2 sont **six
jonctions fret `shared_dest=1` et huit trajets voyageurs**. Ils sont hors
périmètre *direct* du filtrage V307R, sans exclure une conséquence indirecte
de trajectoire. Les paires ABND du témoin sont toutes absentes des abandons
de la variante.

**Conclusion : indéterminée.** L'hypothèse **(a)** — buts A* retirés — est
compatible avec les six abandons filtrés, sans chemin contrefactuel observé.
L'hypothèse **(b)** — bande/entrée bloquant l'A* — reste possible, sans cas
discriminant ici. Les deux trajectoires divergent et aucune paire ABND ne
coïncide : on ne peut attribuer les hausses 2→13 et 5→17 aux seuls filtres.

### Étape 1 — code et choix de variante pré-enregistré

Le résultat étant indéterminé, **`v307_sink_room=13` (bits 1+4+8)** est
choisi **avant** le nouveau banc, conformément au protocole :

- Bit **4** : ne plus écarter de buts, présenter les plans B avec réserve
  en tête, puis tous les autres, dans l'ordre initial de chaque groupe.
- Bit **8** : ne plus ajouter les tuiles des réserves aux interdictions de
  recherche. Si le chemin choisi occupe la réserve de son plan B, émettre
  `V307R_DROP src= dst=` sous `decision_log`, supprimer les six attributs
  `v307Room*` et revenir au quai simple, plutôt que `TRKFAIL`.
- Bits 4 et 8 **inertes sans 1 ou 2** ; `max_value=15`, défaut 0 aux quatre
  niveaux, lecture unique inchangée. **Garde runtime `settings.nut` corrigée**
  de `v307Room <= 3` à `<= 15` : sinon le masque 13 aurait été ramené
  silencieusement à 0 malgré la borne de `info.nut`. C'est l'unique exception
  indispensable au périmètre de fichiers initial. Ni `OpexExecuteRailPlan` ni
  `OpexSimulateRailInfraCost` ne sont modifiés.

Tests V307R ciblés **19/19 réussis**, diagnostic **8/8 réussis**. Le contrôle
du diagnostic distingue désormais la complétude d'une porte structurelle 3×10
(`comparison_complete`, `metric_coverage_complete`) de la non-éligibilité
économique normale à 40 paires (`adoption_sample_complete=false`) ; il accepte
les masques `1..15` et compte les événements `V307R_DROP`.

Suite Python générale **2 398 tests, 2 échecs, 2 ignorés et 2 échecs attendus**.
Les deux échecs (`test_exactly_five_public_settings_retired` et
`test_single_setting_default_three_and_loaded_once`) figuraient déjà dans
la suite de la file A (2 397 tests, 4 échecs) : **aucune nouvelle régression
observée** entre ces deux validations. Le code V307S du commit de file A a
par ailleurs dû être rétabli dans un commit correctif séparé (`aac77e26`) :
la copie de travail des deux bancs contenait déjà ce code correct.

### Étape 2 — critères et résultats du banc séquentiel

Ordre respecté : **file A 3×10 complète d'abord**, puis Docker libre ; smoke
1×1 sur 42 (2/2 saines), puis 3×10 sur 42, 7, 100 (6/6 saines), référence
`OpexAI[decision_log=1]`, variante
`OpexAI[decision_log=1,v307_sink_room=13]`. **Zéro erreur Squirrel,
3/3 paires à quatre trimestres et JSON FINAL**. Smoke et campagne 3×10 ont
exactement le même bundle figé
`a1b5df6865936b89ed345189d9a100be0265a2eacf004e9de4a7f17a0664e645` ;
source Git lors du bundle `e8c6f73d` avec modifications locales consignées
(`dirty=1`). Les critères structurels ci-dessous sont ceux fixés **avant**
le lancement :

| Critère (somme des trois graines) | Référence | Valeur 13 | Seuil | Verdict |
|---|---:|---:|---|---|
| `SITEAB+ABND` | 27+10 = **37** | 31+7 = **38** | variante ≤ 22,2 (−40 %) | **ÉCHEC** (+2,70 %) |
| Réussite jonctions B (`shared_dest=1`) | 23/60 = **38,33 %** | 24/58 = **41,38 %** | taux variante ≥ 57,5 % (+50 % relatif) | **ÉCHEC** (+7,95 % relatif) |
| Lignes neuves (destination non partagée) | **55** | **52** | variante ≥ 55 | **ÉCHEC** (−3) |

**Exposition et coûts descriptifs :** 58 `V307R_SITE`, dont 6 fallback et
52 occasions avec réserve ; **651 → 651 plans** (zéro filtrage, bit 4 actif),
`V307R_DROP=0` (aucun chemin retenu n'a nécessité l'abandon d'une réserve).
Sondage `V307R_SITE` : médiane **4 718,5**, p90 **6 288,2**, somme
**269 802 opcodes** sur les trois parties variantes. `RAIL_ATTEMPT` :
128 → 118, `OK` 78 → 76 ; `ABND` seuls 10 → 7, mais `SITEAB`
27 → 31 ; jonctions B construites 23 → 24. Les trajectoires divergent :
l'absence de `DROP` ne démontre pas la neutralité de l'assouplissement bit 8.

**Économie exploratoire, non décisionnelle :**

| Graine | Δ `profit_year` (variante − témoin) | Δ valeur |
|---:|---:|---:|
| 42 | −245 393 £/an | +451 630 £ |
| 7 | +220 388 £/an | −1 959 986 £ |
| 100 | −433 273 £/an | −2 048 650 £ |

Moyenne **−152 759,3 £/an**, médiane **−245 393 £/an**,
**1 victoire / 2 défaites**, bootstrap IC95 **[−433 273 ; +220 388] £/an**.
Valeur moyenne −1 185 668,7 £, IC95 bootstrap
**[−2 048 650 ; +451 630] £** ; ratio des moyennes voisin de **−5,66 %**.
Le rapport C66.4 reste `diagnostic_only` sur 3 graines, distinct du verdict
structurel. Reproduire avec :

```powershell
python -X utf8 sweeps/diag_v307r_exposition.py --root results --campaign v307r_v13_expo_3x10_20261022 --json results/v307r_v13_expo_3x10_20261022_diagnostic.json
```

**Verdict B : ÉCHEC des trois critères structurels.** Pas de porte A
GitHub 40×3 à proposer ou lancer ; le réglage par défaut reste **0**. Le
test n'isole pas les retours marginaux des bits 4 et 8 pris séparément.
