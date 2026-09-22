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
