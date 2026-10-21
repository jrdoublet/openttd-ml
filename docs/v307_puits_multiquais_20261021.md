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
