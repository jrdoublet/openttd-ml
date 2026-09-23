# C67.1 — contrat de cartographie et protocole initial

Spécification du 22 septembre 2026, branche `feat/c67-cartographie`, base `de6e48e`.
Ce document fixe le premier prototype ; il ne rapporte aucune mesure runtime et ne
choisit pas encore entre 5×5 et 10×10. Le travail restant est dans [taches.md](taches.md).

## 1. Périmètre du premier prototype

Créer un service `OpexTerrainMap` dans un futur `terrain_map.nut`, distinct de
`OpexSpatialGrid` (index de villes). Il calcule des résumés à la demande, par tranches,
sans scans au constructeur et sans changement du portefeuille. Le prototype sera
exercé par une fixture de diagnostic avant son branchement dans OpexAI.

Trois couches séparées : résumés physiques, observations dynamiques et topologie eau.
C67.2 implémente seulement les résumés et leur cycle de calcul. La topologie détaillée
vient en C67.5 : un bloc riche en eau ne sera jamais assimilé à un bassin connecté.
Les classifications « plat/vallonné/montagne » attendent une calibration ; les données
brutes sont disponibles sans ces étiquettes.

## 2. Coordonnées et identité

Pour une carte de largeur W et hauteur H et un côté S dans {5, 10} :

- `nx = (W + S - 1) / S`, `ny = (H + S - 1) / S`, en division entière ;
- `bx = x / S`, `by = y / S`, `block_id = by * nx + bx` ;
- emprise demi-ouverte `[bx*S, min(W, (bx+1)*S)) × [by*S, min(H, (by+1)*S))` ;
- l'identité du cache inclut W, H, S et la version de schéma : pas de partage entre grilles ;
- contrôle x/y avant conversion en TileIndex, puis validité de la tuile selon l'API.

Les blocs de bord partiels utilisent leur aire réelle. Les tuiles invalides ne sont
ni eau ni terre : `sample_count` les exclut et `invalid_count` les compte. Un bloc sans
échantillon valide conserve des mesures inconnues, jamais une altitude ou un ratio zéro.
Sur une carte 2048² : nx=410 pour S=5 (168 100 blocs) et nx=205 pour S=10 (42 025 blocs).
Ces nombres sont des capacités géométriques, pas des allocations au démarrage.

## 3. Données publiées

Un résumé est publié atomiquement seulement lorsque toutes ses tuiles ont été lues.
Les compteurs intermédiaires restent privés au calcul.

| Champ logique | Définition |
|---|---|
| `schema_version`, `block_id`, `generation` | Identité et version locale d'invalidation |
| `sample_count`, `invalid_count` | Tuiles valides et invalides de l'emprise |
| `water_count`, `coast_count` | Résultats indépendants des prédicats eau et côte ; ne pas les sommer pour déduire une partition |
| `height_min`, `height_max` | Minimum des minima et maximum des maxima d'altitude des tuiles valides |
| `height_min_sum` | Somme des altitudes minimales ; moyenne explicitement nommée `mean_tile_min_height`, pas hauteur moyenne des quatre coins |
| `flat_count` | Nombre de tuiles dont la pente vaut `SLOPE_FLAT` |
| `first_sample_tick`, `last_sample_tick` | Fenêtre d'observation, pas promesse d'un snapshot instantané du monde |
| `buildable_count`, `dynamic_sample_tick` | Observation dynamique du prédicat `IsBuildable` ; ne prouve pas la faisabilité d'un ouvrage |

Les ratios sont dérivés des compteurs sur `sample_count`, sans division entière accidentelle.
L'amplitude est `height_max-height_min` ; la proportion non plate vaut
`(sample_count-flat_count)/sample_count`. Une pente enum ne se moyenne pas.
Les API correspondantes sont déjà utilisées dans les builders : `GetMinHeight`,
`GetMaxHeight`, `GetSlope`, `IsBuildable`, `IsWaterTile`, `IsCoastTile`.
Le format mémoire concret (table compacte ou tableau indexé avec constantes nommées)
sera mesuré ; aucun objet par tuile n'est retenu une fois le bloc terminé.

## 4. Demandes, reprise et invalidation

Interface de conception, à implémenter en C67.2 :

| Opération | Contrat |
|---|---|
| `Request(block_id, priority)` | Déduplique ; priorité demande métier avant remplissage de fond. Refuse explicitement une nouvelle demande si la file est pleine. |
| `Peek(block_id)` | Lecture sans calcul : `absent`, `pending`, `ready` ou `stale`, avec version. Aucun résumé incomplet présenté comme valide. |
| `Step(ops_budget, deadline_tick)` | Avance le curseur intra-bloc ; contrôle l'échéance et les opcodes entre unités de travail ; retourne progression/fin sans attendre dans une boucle. |
| `InvalidateRect(x0,y0,x1,y1)` | Rectangle demi-ouvert ; invalide les blocs touchés et leurs liens de frontière. Une modification sur un bord invalide aussi la preuve de liaison avec le voisin. |
| `Clear()` | Abandonne cache et demandes ; aucune décision économique déclenchée. |

États : absent → pending → ready ; invalidation de ready → stale. Une invalidation
pendant pending change sa génération : abandonner ses agrégats avant publication et
recommencer à la demande. Une éviction rend absent. Une demande stale ne consomme pas
l'ancien résumé comme une valeur actuelle.

Une tranche interrompue reprend à la prochaine tuile ; le cache vide, un refus de file,
une éviction ou une limite de budget rendent une donnée indisponible, jamais un rejet
de projet. Réponse sans travail si budget non positif ou échéance déjà atteinte.
Pas de `Sleep()` ajouté au service ; l'appelant décide quand demander la tranche suivante.

**Intégration ordonnanceur cible (précisée le 2026-09-25).** C67 est destiné à devenir un worker
résumable consommant en priorité le **reliquat d'opcodes du tick**, pas une nouvelle tâche
monolithique du round-robin. Une demande issue d'un projet réellement bloqué par une donnée de carte
est prioritaire sur le remplissage opportuniste. Lorsque plusieurs workers sont prêts (A* rail,
`town_growth`, cartographie), l'orchestrateur doit réarbitrer tranche par tranche selon l'état du
pipeline : résultats déjà prêts, demande métier en attente et capacité de la prochaine tranche à
débloquer une décision. Exemple : si suffisamment de tracés A* sont déjà prêts, la valeur marginale
d'un A* supplémentaire baisse et le reliquat peut servir C67 ou `town_growth`. Le détail de cette
politique est décrit dans [34_arbitrage_economique_unifie.md](34_arbitrage_economique_unifie.md)
§5.5.

Les travaux propres invalident explicitement leurs emprises. Les modifications adverses
et naturelles ne sont pas toutes signalées : fraîcheur limitée et revalidation fine
obligatoire avant une décision de construction. Aucun TTL ne prouve l'absence de changement.
La politique de rafraîchissement en jeu et les points d'accroche restent C67.4.

## 5. Bornes initiales, proposées avant mesure

Ces bornes sont des critères d'ingénierie du prototype, **pas des limites mesurées de la VM**.
Si elles échouent, publier l'échec et réviser explicitement le contrat avant un nouvel essai.

- Cache : 4 096 résumés maximum pour chaque grille testée séparément ; file de demandes
  dédupliquées limitée à 256 ; un seul bloc en cours (100 tuiles maximum).
- Éviction LRU par accès, avec opérations constantes : ne pas scanner tous les blocs
  pour chaque lecture/éviction. Le bloc en calcul n'est pas un résumé épinglé indéfiniment.
- Tranche cible : 2 000 opcodes ; tolérance maximale d'une unité de lecture de tuile,
  mesurée séparément. Sur le banc : aucune tranche au-delà de 10 000 opcodes et aucune
  boucle complète de carte cachée dans une opération Request/Peek/Invalidate.
- Mémoire : delta RSS médian ≤ 32 Mio, maximum observé ≤ 48 Mio, cache saturé et témoin
  apparié. RSS inclut l'allocateur/runtime : conserver aussi entrées, files et tailles de
  travail ; ne pas présenter ce delta comme une mesure exacte du heap Squirrel.
- Exactitude : zéro erreur d'agrégats sur fixtures, zéro publication de génération
  invalidée, zéro résultat différent entre exécution continue et reprise sur monde figé.
- Réemploi : après remplissage, relire un même bloc valide ne déclenche aucune lecture
  d'API de terrain. Constructor et Peek absent ne lisent aucune tuile.

Le cache borné peut oublier des régions ; la couverture est donc décrite par deux nombres :
blocs distincts calculés et blocs actuellement résidents. Le banc de couverture complète
parcourt toute la carte **en streaming avec éviction**, sans contourner la borne de cache.

## 6. Connectivité : contrat réservé pour C67.5

La future réponse sera `{status, reason, distance_kind, distance, generations}`.
`status` vaut connected/disconnected/unknown ; `distance_kind` vaut exact/estimate/none.
L'estimation d'un corridor ne remplace pas la distance navigable du modèle économique.

Pour affirmer connected, conserver une chaîne de passages réellement reliés et revalider
ses dépendances. Plusieurs composantes peuvent coexister dans un bloc. Un état manquant,
un plafond d'exploration ou un chemin possible hors du domaine exploré donne unknown.
Disconnection globale exige l'épuisement d'un domaine complet et fermé, pas l'échec du
BFS actuel limité à 12 000 nœuds et au rectangle élargi de 24 tuiles.

Les passages inter-blocs devront utiliser les arêtes navigables réelles, pas seulement
la présence d'eau de chaque côté. Le cache détaillé aura sa propre borne à fixer en
C67.5 ; il ne transforme pas les 4 096 résumés en une grille permanente par tuile.

## 7. Cas de revue et futurs tests

`~` = eau, `#` = terre ; `|` matérialise une frontière de blocs (hors grille).
Ce sont des fixtures logiques ; les tests moteur confirmeront les arêtes navigables.

```text
Deux bassins dans un bloc       Chenal passant une frontière
~~~~#~~~~~                     #####|#####
~~~~#~~~~~                     ~~~~~|~~~~~
~~~~#~~~~~                     #####|#####
```

| Cas | Résultat attendu / piège exclu |
|---|---|
| Deux bassins ci-dessus | Même bloc et fort ratio eau ne permettent pas d'affirmer connected. |
| Chenal ci-dessus | Pas de rejet sur faible ratio eau ; vérifier le passage réel à la frontière. |
| Île entourée d'eau | Détour possible autour de l'île ; distance navigable distincte de Manhattan. |
| Contact diagonal seulement | Aucune connexion déduite d'un simple voisinage diagonal. |
| Péninsule sortant du rectangle local | Oracle local épuisé → unknown, pas disconnected. |
| Carte logique 13×7, S=5 | Grille 3×2 ; dernier bloc d'aire 3×2=6, sans débordement de ligne. |
| Tuile invalide en bord | Compteur invalide incrémenté, moyenne sur seules tuiles valides. |
| Invalidation au milieu d'un bloc | L'ancienne génération ne devient jamais ready. |
| Changement externe après lecture | Résumé seulement observé ; validation fine requise avant construction. |
| 4 097 blocs puis retour au premier | Cache ≤4 096 ; une éviction entraîne recalcul, pas valeur neutre. |
| 257 demandes différentes | Refus explicite/différé de la demande excédentaire ; file ≤256. |
| Save/Load pendant pending | Pas de sérialisation implicite des objets de service ni de reprise d'agrégats obsolètes. |

## 8. Protocole C67.3 pré-enregistré

Runtime canonique OpenTTD 15.3 / NoAI 15 / OpenGFX 7.1, OpenTTDLab 0.0.75.
Partir des helpers de `bench_v2.py`, du gel `campaign_freeze.py`, des contrôles
`game_health.py` et de la méthode RSS de `diag_water_memory.py` ; ne pas réutiliser son
ancien bras Opex/Lakes. Configuration et listes de requêtes exportées et hashées avant runs.

- Tailles carrées : 256, 512, 1024, 2048 ; ajouter les fixtures de bord rectangulaire.
- Graines de qualification technique : 42, 100, 999 ; trois répétitions indépendantes.
  Elles ne constituent pas un jeu de validation économique indépendant.
- Trois bras : témoin même fixture sans service, S=5, S=10. Soit 108 runs pour la matrice
  4 tailles × 3 graines × 3 répétitions × 3 bras, lancés séquentiellement par campagne.
- Alterner l'ordre des bras entre répétitions ; conserver les mêmes points de requête,
  configuration, checkpoints et limites. Une paire terrain identique se vérifie par
  empreinte des entrées observées ; les mutations pendant mesure sont un scénario distinct.
- Chaque run : initialisation sans requête ; 64 points localisés déterministes à froid ;
  relecture à chaud ; parcours complet en streaming ; cycle d'évictions ; invalidation locale.
  Les points sont définis en coordonnées de tuile, pas en identifiants de blocs, pour ne pas
  favoriser une granularité. Le générateur de traces doit être figé avant le premier run.
- Exporter durée et opcodes par phase, lectures de tuiles, hits/misses/évictions,
  demandes refusées, pic de file, résidents, couverture cumulée, RSS, distributions de
  tranches et contrôles d'exactitude. Conserver les échecs ; ne pas les remplacer par zéro.
- Horizon du premier pilote : un an. Un run tronqué reste incomplet ; si le parcours
  complet n'y tient pas, fixer un nouvel horizon commun dans une révision du protocole
  avant la matrice, sans mélanger les deux versions.

Choix de granularité : éliminer les variantes qui échouent aux bornes/exactitude.
Parmi les restantes, comparer les opcodes des mêmes demandes localisées (médiane des
deltas appariés) puis la mémoire. Retenir provisoirement S=5 si son coût médian ne dépasse
pas S=10 de plus de 10 %, pour sa résolution plus fine ; sinon retenir S=10. Ce départage
est un choix de conception déclaré, pas une preuve d'utilité économique. La topologie
C67.5 et le premier consommateur C67.6 peuvent encore invalider ce choix.

## 9. Persistance et sortie de C67.1

Intention retenue : cache reconstructible, non sauvegardé ; demandes métier reconstruites
depuis leur consommateur après Load. Aucun consommateur n'existe en C67.2. C67.4 devra
vérifier que perdre le cache ne perd pas une intention métier et mesurer le coût de reprise.

Revue statique effectuée : géométrie de bord, compteurs, état inconnu, bornes et cas ci-dessus.
**Non exécutés :** prototype Squirrel, tests de fixtures, mémoire/opcodes réels et parties.
C67.1 fournit le contrat ; la prochaine livraison est le prototype C67.2 accompagné de ses
tests et du smoke réel, avant toute intégration au comportement.

## 10. Implémentation C67.2 — 22 septembre, smoke moteur réussi

`ai/OpexAI/terrain_map.nut` implémente le service isolé ; il n'est pas chargé par OpexAI.
Les paramètres de capacité peuvent être réduits pour les fixtures, jamais dépasser
4 096 résumés et 256 demandes. Les listes liées assurent accès/éviction LRU et promotion
de file sans scan. `Peek` rend une copie du résumé complet, sans exposer l'accumulateur.
Les versions sont monotones par instance ; aucune table permanente de générations par
tuile ou par bloc absent n'est allouée. Le comptage de couverture distincte sera externe
au service dans C67.3 : `completed` compte les calculs terminés, y compris les recalculs.

Précisions d'implémentation :

- L'invalidation parcourt les seuls résidents et demandes bornés, pas les tuiles de la
  carte. Son découpage et son coût maximal restent à traiter en C67.4 avant branchement.
- Une demande en cours invalidée conserve son intention mais recommence ses agrégats
  sous une nouvelle génération. Les résumés périmés ne sont pas lisibles comme valides.
- Une demande métier peut préempter un calcul de fond à la prochaine tranche : pour
  conserver un seul accumulateur, le calcul de fond est remis en file et recommencera.
  Une simple expiration de budget reprend, elle, à la tuile suivante.
- L'unité indivisible finale inclut lecture, agrégation et éventuelle publication du
  résumé. Son dépassement réel en opcodes doit être mesuré ; les horloges synthétiques
  ne qualifient pas le coût VM ni la borne de 10 000 opcodes.
- Le cache n'est ni persisté ni rattaché à C80. Il n'affirme aucune connectivité.

La fixture et le harnais sont décrits [ici](../sweeps/fixtures/TerrainMapProbe/README.md).
Tests Python de collecte/provenance exécutés ; tests Squirrel et appels API réels exécutés
avec succès après rétablissement de Docker et du partage du dossier. Rapport :
`results/c67_terrain_smoke_20260922_retry01.json`, graine 42, un an, douze mois couverts,
marqueur final présent, aucune erreur moteur/NoAI. Les seuils de mémoire/opcodes et la
granularité restent non qualifiés : ils relèvent de C67.3.

## 11. C67.3 — révision du protocole avant la matrice

Le premier pilote 256², graine 42, a exposé deux faits techniques. La fixture de télémétrie
traitait à tort l'ID numérique d'un panneau comme un booléen ; le premier JSON est invalide
et conservé. Le pilote corrigé terminait, mais observait un pic de tranche de ~12 000
opcodes, au-dessus de la borne de 10 000 définie en C67.1. Abaisser seulement le budget
demandé de 2 000 à 1 000 n'a pas éliminé ce pic.

Le service vérifie désormais qu'au moins 3 000 opcodes restent dans le tick avant de
commencer une lecture ; une demande trop tardive rend `idle` à l'appelant. La fixture
attend le tick suivant puis reprend. Elle mesure aussi le maximum d'une lecture de tuile.
Ce contrôle protège la borne observée, mais réserve parfois une partie du tick pour
d'autres travaux ; son coût réel est inclus dans C67.3. Le smoke C67.2 sur cette version
est sain (`results/c67_terrain_smoke_20260922_after_budget.json`).

Le pilote corrigé sous ce service (256², trois bras, graine 42, un an,
`results/c67_pilot_256_20260922_04.json`) mesure 25,6 M opcodes pour le balayage 5×5
et 20,9 M pour 10×10, avec pics de tranche 1 240 et 1 299. Une extrapolation linéaire
à 2048² donne environ 1,6 milliard d'opcodes pour 5×5. À 10 000 opcodes/tick et
74 ticks/jour, cela dépasse six ans de jeu ; l'horizon initial d'un an ne permet donc
pas de qualifier le balayage complet 2048². Ce calcul est une estimation de capacité,
pas un résultat 2048².

**Version 2 du protocole, fixée avant les runs de matrice :** horizon commun de huit ans
(2 920 jours) pour témoin, 5×5 et 10×10 sur les quatre tailles. Graines 42/100/999,
trois répétitions, ordre des bras alterné, un worker à la fois, 108 parties attendues.
Conserver les mêmes 64 points de tuile, phases et seuils de C67.1. Contrôler les
96 mois de 1970–1977, le marqueur final, les erreurs NoAI/moteur et les empreintes
du code et des entrées. Le pilote 2048² doit confirmer que cet horizon suffit avant
la matrice. Si non, publier la limite puis réviser à nouveau **avant** toute matrice ;
ne pas mélanger les versions 1 et 2 dans un verdict.

RSS est un pic du processus, échantillonné par le moniteur déjà utilisé dans
`diag_water_memory.py`, comparé au témoin apparié. Il inclut l'allocateur et le monde
du jeu : le qualifier de delta de processus, pas de taille exacte des objets Squirrel.
Les opcodes et ticks sont mesurés séparément par phase dans la fixture. Les tests
de seize blocs sur chaque bras détectent les erreurs d'agrégats ; ils ne constituent
pas une preuve sur toutes les tuiles. Le balayage complet vérifie le nombre de blocs,
les lectures, la résidence bornée et l'horizon.

## 12. Pilote 2048² et version bornée du protocole

Le pilote version 2 (`results/c67_pilot_2048_8y_20260922_01.json`) a couvert les 96 mois
pour les trois bras sans erreur moteur ni NoAI. Les phases locales 64 blocs sont valides,
mais le balayage complet n'a pas atteint `scan` avant la fin de l'horizon : `evict` et
`invalidate` sont donc absents. Ce résultat est une limite de durée, pas un échec de
compilation ou d'exactitude ; il interdit de traiter le balayage complet 2048² comme une
mesure qualifiée sous huit ans.

La version bornée ajoute le réglage de fixture `scan_blocks` et l'option du harnais
`--scan-tiles`. Le pilote `results/c67_pilot_2048_bounded_20260923_01.json` fixe une
enveloppe commune de 409 600 tuiles par granularité, sur 2048², graine 42, un worker,
96 mois : 16 384 blocs 5×5 et 4 096 blocs 10×10. Les trois bras ont 96 checkpoints,
empreinte d'entrée identique, marqueur final, zéro erreur et les contrôles d'oracle sur
16 blocs. Les deux paires sont valides ; le pic RSS du processus contre le témoin est de
8 436 KiB (5×5) et 8 516 KiB (10×10). Le balayage borné mesure respectivement 163 684 997
et 142 683 642 opcodes, 409 160 et 408 620 lectures, avec 1 240 opcodes de tranche au
maximum et 4 096 résidents. Ces chiffres décrivent cette enveloppe progressive ; ils ne
qualifient pas la couverture complète 2048².

La matrice complète n'a pas été lancée après ce pilote. Les versions complète 256²/512²/
1024² et bornée 2048² devront conserver dans leur manifeste l'enveloppe de tuiles, les
empreintes et le statut `limited`; un résultat tronqué reste incomplet. Aucun choix de
granularité ni défaut de jeu n'est adopté par ce pilote technique.

## 13. Matrice C67.3 version 2 — choix provisoire S=5

Deux campagnes séquentielles (un worker chacune, exécutées en parallèle dans deux
conteneurs plafonnés séparément), graines 42/100/999, trois répétitions, 96 mois :
`results/c67_matrix_full_8y_20260923_01.json` (256²/512²/1024², balayage complet) et
`results/c67_matrix_2048_bounded_8y_20260923_01.json` (2048², 409 600 tuiles). 108/108
parties, 72/72 paires valides, aucune erreur, oracle et bornes respectés (tranche ≤ 1 299
opcodes, résidents ≤ 4 096). Rapport `sweeps/report_c67_terrain.py` :
`results/c67_matrix_8y_20260923_01_report.json`.

Delta relatif apparié des opcodes à froid S5 vs S10 : médiane −71,8 % (36 paires).
S=10 est ~12 % moins cher par tuile en balayage et plus économe en mémoire tant que le
cache n'est pas saturé (256²/512²) ; au plafond, ΔRSS ≈ 8,4 MiB pour les deux.
**S=5 est retenu provisoirement** selon la règle §8. Non couverts : balayage complet
2048², fixtures de bord rectangulaire. Chiffres détaillés : journal du 23 septembre.

## 14. C67.4 — cycle de vie et ordonnancement (conception du 23 septembre)

Décisions fixées **avant** implémentation et mesure. Granularité : S=5 (§13).

**Activation.** Réglage `c67_terrain_map`, booléen, défaut 0. À 0, aucun service n'est
construit et la boucle principale ne paie qu'un test de constante. Il n'active ni
C80 ni aucun autre réglage ; les deux boucles (historique et C80) portent le même crochet.

**Place dans la boucle : reliquat avant `Sleep(1)`.** Après la passe métier du tick
(tâche de file ou tick d'orchestrateur), et juste avant le `Sleep(1)` qui abandonne de
toute façon le reste du tick, le crochet avance le service avec
`budget = GetOpsTillSuspend() − 3 000` et l'échéance « tick courant + 1 ». Il ne
franchit jamais un tick : les tâches métier ne sont ni préemptées ni retardées, et
reprennent au même tick qu'en l'absence du service. Corollaire testable : sans
consommateur, une partie avec le service doit être **identique** (mêmes grandeurs
physiques et économiques) à la même graine sans lui. Toute divergence est un défaut.

**Priorités et interruption.** Les demandes métier (priorité 1) sont servies avant
le remplissage de fond. Un calcul de fond en cours est remis en file à la tranche
suivante (contrat C67.2 inchangé). `Cancel(id)` retire une demande, y compris le
calcul actif. Aucun consommateur n'existe en C67.4 : l'API est prête pour C67.6.

**Remplissage de fond.** Un curseur parcourt les blocs en ordre raster et soumet au
plus quelques demandes de priorité 0 par crochet, sans jamais remplir la file au-delà
d'une petite réserve. Le fond **n'évince jamais** : une demande de fond est refusée
quand `résidents + demandes ≥ capacité`, et un résultat de fond est abandonné plutôt
que d'évincer. Sonder un bloc prêt par le fond ne modifie ni l'ordre LRU ni les hits.
Après un tour complet sans nouvelle demande, le fond s'arrête jusqu'à la prochaine
invalidation. L'ordre raster est arbitraire : l'ordre pertinent viendra du consommateur.

**Invalidation paresseuse et bornée.** `InvalidateRect` n'itère plus sur les résidents :
il ajoute un rectangle daté par numéro de série à une liste d'au plus 32 entrées
(fusion conservatrice des deux plus anciennes en boîte englobante quand elle est
pleine). Un résident dont la génération précède un rectangle qui le touche devient
`stale` à sa prochaine lecture. Seul le calcul actif est annulé immédiatement ; une
demande en attente reçoit sa génération au début de son calcul. Coût : O(32) par
lecture, O(1) par invalidation, indépendant du cache et de la carte.

**Travaux propres et changements externes.** Chaque nouvelle ligne inscrite dans
`_lines` invalide la boîte englobante de ses deux extrémités élargie de 8 tuiles,
détectée par le crochet via la longueur de `_lines` (aucune modification des six
sites de construction). Non couverts : démolitions, agrandissements de gares,
double voie, routes de croissance urbaine et tous les changements adverses ou
naturels. Pour eux, aucun TTL : le résumé reste une observation datée et une
revalidation fine au niveau tuile est obligatoire avant toute construction.

**Save/Load.** Rien n'est sauvegardé. Après chargement, le service repart vide et le
fond reprend au curseur 0 ; les intentions métier appartiennent à leur consommateur.
Contrôle : Save/Load avec le réglage actif, sans erreur ni divergence de format.

**Télémétrie.** Une ligne `AILog` annuelle `C67_TERRAIN` (résidents, calculs, lectures,
opcodes cumulés et maximum par tranche, refus, évictions, invalidations, crochets
actifs/sautés), uniquement sous le réglage.

**Validation C67.4.** Tests de fixture Squirrel des nouveaux cas (invalidation
paresseuse, fond sans éviction, annulation, génération au début du calcul), smoke
1×1 avec le réglage, diagnostic d'équivalence solo 3 graines × 2 ans (référence
contre réglage actif : grandeurs identiques attendues), puis Save/Load. Aucun gain
économique n'est attendu ni recherché : le service n'a pas encore de consommateur.

## 15. Résultats C67.4 (23 septembre)

Fixture de contrat avec les cas §14 : passe. Équivalence `OpexAI` contre
`OpexAI[c67_terrain_map=1]`, 3 graines × 3 ans (`results/c67_runtime_3y_20260923_01.json`) :
108 checkpoints appariés, zéro écart de jeu ni d'opcodes. Une première version, qui
construisait le service dans `Start()`, décalait de 1–2 opcodes la télémétrie du premier
mois ; la construction est désormais paresseuse, dans le premier crochet. Save/Load
(`results/c67_saveload_20260923_01.json`) : OK, service reconstruit vide après chargement.

Débit mesuré sur 256² : 85 à 760 blocs par an dans le reliquat seul, pic de tranche
7 161 opcodes. Le fond ne peut pas servir de source rapide ; le consommateur C67.6 devra
budgéter ses propres tranches. Saturation du cache en jeu et boucle C80 non exercées.

## 16. C67.5 — graphe de composantes eau et oracle (conception du 23 septembre)

Fixé avant implémentation. Complète §6 ; S=5 (§13).

**Périmètre.** Connectivité **eau** seulement : c'est la seule relation qui dispose déjà
d'une référence exacte dans le code (`OpexWaterFindConnection`). Prédicat identique :
tuile navigable = `AITile.IsWaterTile` ; arête = voisin cardinal, les deux tuiles eau et
`AIMarine.AreWaterTilesConnected`. Pas de diagonale. Quais, écluses, aqueducs et bouées
ne sont pas modélisés, comme dans le builder actuel. Corridors rail/route : hors C67.5.

**Analyse d'un bloc (reprenable).** Pour chaque bloc, lecture tuile par tuile avec
curseur : eau, puis arêtes internes est/sud, puis arêtes de frontière est/sud vers le
bloc voisin. Union-find sans API pour étiqueter les composantes internes. Enregistrement
publié atomiquement : `comps`, étiquettes des tuiles (absentes si aucun eau), drapeaux de
passage est/sud par tuile de frontière, génération. Cache LRU propre, ≤ 4 096
enregistrements, distinct des résumés ; invalidation paresseuse par rectangles comme §14.

**Graphe implicite.** Nœud = (bloc, composante). Voisins est/sud lus dans l'enregistrement
du bloc, ouest/nord dans celui du voisin. Le quotient est **exact** : tout chemin de tuiles
se décompose en segments internes et passages de frontière observés. Aucune table
permanente par tuile sur la carte.

**Oracle `Query(tileA, tileB)`, par tranches.** Parcours en largeur des nœuds depuis celui
de A ; un bloc manquant est analysé avant l'expansion qui en dépend.

- `connected` : le nœud de B est atteint ; la chaîne de nœuds est la preuve.
- `disconnected` : la frontière est épuisée, la composante de A est entièrement énumérée et
  ne contient pas B. Preuve fermée, seule forme admise de déconnexion.
- `unknown` : plafond de blocs analysés ou d'opcodes, invalidation d'un bloc visité pendant
  la requête, ou A/B non navigables (raison explicite).

`distance_kind` : `none` pour l'oracle. `CorridorDistance` fait ensuite un BFS de tuiles
**restreint aux blocs de la chaîne dilatés d'un bloc**, par tranches : longueur d'un chemin
réel (majorant du plus court), `distance_kind = corridor`. Elle ne remplace pas la distance
tarifaire. Un échec dans le corridor rend `unknown`, jamais `disconnected`.

**Livraison.** `water_graph.nut`, non chargé par OpexAI en C67.5 (comme C67.2) ;
branchement éventuel par le consommateur C67.6 sous réglage à défaut 0.

**Validation C67.5.**
1. Fixture Squirrel, source factice : cas §7 (deux bassins dans un bloc, chenal traversant
   une frontière, île et détour, contact diagonal, péninsule, bassins disjoints, bord de
   carte, invalidation pendant requête) contre un BFS de tuiles exhaustif ; cartes
   aléatoires : oracle sans plafond = BFS exhaustif sur toutes les paires testées ; oracle
   borné = même réponse ou `unknown`, jamais l'inverse.
2. Sonde sur cartes réelles (IA de diagnostic, entrées figées) : paires de tuiles d'eau
   déterministes ; comparaison oracle borné, BFS exhaustif et prédicat du builder actuel
   (marge 24, 12 000 nœuds). Rapporter accord, taux `unknown`, faux `-1` du builder actuel
   (paires connectées qu'il rejette), opcodes par requête et pic de tranche.
Aucun connecté/déconnecté affirmé à tort n'est toléré. Pas de gain économique mesuré ici.

## 17. Résultats C67.5 (23 septembre)

`ai/OpexAI/water_graph.nut` (non chargé par OpexAI), fixture `sweeps/fixtures/WaterGraphProbe`,
harnais `sweeps/diag_c67_water.py`. Rapport final `results/c675_water_6y_20260923_04.json` :
3 graines × 256² et 512², six parties saines, marqueurs de fin présents.

- Cas adverses §7 et 30 cartes aléatoires (≈ 300 paires) contre un BFS exhaustif : passe ;
  oracle borné jamais contradictoire, corridor toujours trouvé et ≥ distance exacte.
- Cartes réelles, 1 200 paires comparées à un étiquetage exact de toute la carte :
  **zéro réponse fausse** ; 642 `connected`, 557 `disconnected` (preuves fermées), 1 `unknown`
  (plafond de 1 024 blocs).
- Builder actuel (`OpexWaterFindConnection`, marge 24, 12 000 nœuds) : 21 faux rejets sur
  642 paires connectées (3,3 %), tous sur des paires lointaines (Manhattan 266–961, chemin
  navigable 433–961) ; aucun sur les 600 paires proches. Aucun faux accept. Sur les 621
  paires trouvées par les deux, la distance de corridor est **égale** à celle du builder.
- Coût propre au service (opcodes) : oracle médiane 83 k si connecté, 210 k si déconnecté
  (p90 0,6 M / 1,6 M, max 8,2 M ; l'inconnu 13 M) ; builder médiane 153 k (p90 0,6 M) ;
  corridor médiane 166 k. Blocs analysés : 674 à 2 455 par carte, aucune éviction.
- Tranches ≤ 8 024 opcodes ; unité indivisible ≤ 3 578. La réserve de tick est portée à
  4 000 et vérifiée avant **chaque** unité (un premier essai, vérifiant seulement à l'entrée,
  montrait des unités coupées par un tick à ~12 000).

Limites : eau seulement ; déconnexion coûteuse sur grande composante (une recherche
bidirectionnelle réduirait ce coût, non implémentée) ; pas de mesure 1024²/2048² ; les paires
sont des tuiles d'eau tirées au hasard, pas les paires de quais du builder. L'exposition
réelle (paires lointaines rejetées à tort) reste à établir en C67.6 avant tout branchement.
