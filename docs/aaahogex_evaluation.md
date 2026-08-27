# AAAHogEx — évaluation comme source d'idées

**Date : 2026-08-27.** Évaluation de l'IA tierce [AAAHogEx](https://github.com/rei-artist/AAAHogEx)
(version 115, Rei Ishibashi, GPL v3) comme source d'inspiration pour `ai/TrainLineAI`.

Le code est présent en local dans `ai/AAAHogEx-115/` mais **volontairement exclu du dépôt**
(`.gitignore`) : le versionner ici rendrait `openttd-ml` dérivé de la GPL v3. Ce document est notre
analyse ; il ne reproduit pas son code.

**Conclusion en une phrase** : ne rien porter, mais deux de ses idées valent d'être réimplémentées
proprement — et l'hypothèse de départ qui avait motivé l'évaluation était fausse.

---

## 1. L'hypothèse de départ était fausse

L'idée initiale était : *« pas de pathfinding complet, juste une approximation qui construit au fur
et à mesure et utilise terraforming, tunnels et ponts quand elle rencontre un obstacle. »*

**Vérifié dans le code, c'est faux.** AAAHogEx **planifie entièrement puis construit** :

1. `RailPathBuilder.DoBuild()` appelle `FindPath(limitCount, this)` (`railbuilder.nut:2362-2377`) ;
2. le chemin complet est sérialisé dans `path1` / `path2` ;
3. `RailBuilder` ne reçoit ce chemin **qu'ensuite** et lance `Build()` (`railbuilder.nut:2382-2412`).

Il pose bien les rails tuile par tuile dans `RailBuilder.DoBuild()` (`railbuilder.nut:1090-1242`),
mais il n'y a **pas** d'alternance « chercher un peu → construire → repartir du front construit ».

**Et il subit exactement notre contrainte d'opcodes.** Sa boucle de recherche fait
`path = _FindPath(50)` (`pathfinder.nut:197-219`) — le **même découpage à 50 itérations** que le
nôtre, pour la même raison. Il n'a trouvé aucune astuce pour contourner le budget du VM, parce
qu'il n'y en a pas. Le découpage n'est pas non plus une segmentation géographique : la recherche
reprend le même A* vers son but final.

---

## 2. Les idées qui valent quelque chose

### 2.1 Ponts et tunnels comme **voisins de l'A\***, pas comme réaction à un obstacle

C'est l'idée centrale, et elle est architecturalement inverse de ce qu'on imaginait.
`_GetTunnelsBridges()` renvoie des candidats pont/tunnel qui sont **poussés dans la liste des
voisins** du nœud courant (`pathfinder.nut:1093-1137`) :

- pont proposé quand un obstacle non constructible, une différence de hauteur ou la contrainte de
  voie retour se présente ; les longueurs sont testées et le pont n'est ajouté que si l'essai est
  constructible (`pathfinder.nut:1381-1413`) ;
- tunnel proposé pour une entrée en pente valide, une sortie calculable et une longueur sous la
  limite (`pathfinder.nut:1423-1433`) ;
- **le coût A\* pénalise distinctement pont et tunnel** (`pathfinder.nut:572-604`).

Ce n'est donc pas une règle « obstacle ⇒ tunnel » : les solutions faisables sont proposées, puis
**arbitrées par la fonction de coût**. Toute la recherche se fait en `AITestMode`
(`pathfinder.nut:428-438`), donc les essais ne modifient pas la carte.

> **Note importante ajoutée après coup** : notre bibliothèque `Pathfinder.Rail` fait **déjà** cela.
> Voir §5 — le problème n'était pas l'absence de la technique.

### 2.2 Reprise en conservant le préfixe déjà construit

`RetryToBuild()` (`railbuilder.nut:1127-1153`, `1186-1211`, `1291-1329`) : en cas d'échec de pose
d'un rail, d'un pont ou d'un tunnel, il **conserve le préfixe déjà construit**, relance une
recherche depuis des points de raccordement de ce préfixe vers le but, puis remplace le tronçon
raté. C'est la vraie idée « incrémentale » du code, et elle est réactive, pas planifiée.

Notre IA n'a pas d'équivalent : un `TRKFAIL` est terminal. C'est **l'idée la plus directement
transposable**, et la moins risquée pour la barrière (elle n'intervient qu'après la première
mutation).

### 2.3 Terrassement pendant la construction

`RaiseTileIfNeeded()` (`railbuilder.nut:1105-1108`, logique en `1593-1722`, `Raise()` en
`1725-1745`) est appelé **avant chaque segment** du tracé déjà choisi. Les tunnels « underground »
nivellent aussi leurs entrées via `LevelBound()` (`railbuilder.nut:1529-1586`, `tile.nut:276-303`).
C'est une adaptation à la construction, pas une décision de recherche.

### 2.4 Instrumentation d'opcodes

`PerformanceCounter` lit `AIController.GetOpsTillSuspend()` et journalise ticks et opcodes
(`utils.nut:1039-1085`) ; la sauvegarde mesure aussi ses sous-étapes (`main.nut:4032-4089`).

**Mais aucune de ces lectures ne pilote une boucle.** Il n'y a pas de « tant qu'il reste N opcodes,
avancer ; sinon sauver l'état et reprendre au tick suivant ». Le découpage à 50 itérations est
fixe. Il mesure son coût, il ne s'y adapte pas.

### 2.5 Caches

Frontière prioritaire `AIPriorityQueue` + ensemble fermé `AIList` dans l'A* (`aystar.nut:77-108`,
déduplication en `121-140`, `171-190`) ; connectivité terrestre mémorisée dans `landConnectedCache`
(`tile.nut:506-527`) ; caches de sélection de stations, cargaisons et production
(`station.nut:15-38`, `place.nut:733-755`, `1007-1023`).

Ces caches servent surtout son IA économique multi-réseaux. Ils ne transforment pas la recherche
ferroviaire de bout en bout en construction locale bon marché.

---

## 3. Pourquoi ne rien porter

**Blocage d'API.** `info.nut:11` déclare `GetAPIVersion() = "14"` ; OpenTTD 13.4 (notre version
épinglée) n'accepte que jusqu'à `"13"`, et le refus arrive **avant** l'exécution de `main.nut`.
Le seul ajout v14 réellement utilisé est `AITileList_StationCoverage`
(`station.nut:626-649`) — et il a déjà un repli compatible pré-14 dans le code. Ce blocage
empêche donc de *l'exécuter*, pas de *le lire*.

**Licence.** GPL v3 (`license.txt`). Copier ou adapter une fonction, un bloc ou une structure
expressive identifiable créerait vraisemblablement une œuvre dérivée, avec obligation de
distribuer l'ensemble sous GPL v3 en cas de publication. S'inspirer d'une *idée* — « conserver un
front local et réagir à l'obstacle » — ne pose pas ce problème : les algorithmes ne sont pas
protégés en tant que tels. Le dépôt `openttd-ml` ne déclare aucune licence à la racine, ce qui
devrait être clarifié avant toute publication. *(Ceci n'est pas un avis juridique.)*

**Taille.** 37 531 lignes sur 16 fichiers, contre 1 166 pour `TrainLineAI`. C'est une IA
compétitive multi-modale (train, route, bateau, avion) ; la nôtre est un **instrument de mesure**
à une compagnie et une ligne. Les objectifs n'ont rien à voir.

---

## 4. Compatibilité avec notre barrière

Notre comparabilité temporelle repose sur : preflight non mutant → attente jusqu'au tick 11000 →
construction. La crainte était qu'une construction incrémentale, qui mute tôt et souvent, soit
**fondamentalement** incompatible.

**Elle ne l'est pas**, à une condition stricte : aucune mutation avant la barrière. Muter
fréquemment *après* le tick 11000 ne rompt rien. Ironiquement, comme AAAHogEx planifie puis
construit, sa forme épouse déjà la nôtre.

**Le vrai risque est ailleurs, et il est silencieux.** `first_mutation_tick` est capturé juste
avant le premier `DemolishTile` (`ai/TrainLineAI/main.nut:852-860`). Avec du terrassement ou un
pont, **la première mutation pourrait être un `RaiseTile` ou un `BuildBridge`** et échapper à
l'instrumentation, faussant `barrier_flag` sans que rien ne le signale. Toute évolution dans cette
direction impose de généraliser ce point de contrôle à une fonction unique appelée avant le premier
`DemolishTile`, `RaiseTile`, `LowerTile`, `BuildRail`, `BuildBridge` **ou** `BuildTunnel`.

Autre point : la contrainte de villes disjointes (`main.nut:575-623`) ne protège pas de tout
conflit territorial — deux lignes reliant des villes distinctes peuvent se rencontrer sur le
terrain. Un builder plus long devrait prévoir une politique explicite face à une tuile devenue
occupée.

---

## 5. Ce qu'on a appris APRÈS cette évaluation — et qui la relativise

L'évaluation supposait qu'il fallait *ajouter* ponts et tunnels. **C'est faux : notre IA en
construit déjà.**

- La bibliothèque `Pathfinder.Rail` explore nativement des candidats pont/tunnel, avec les défauts
  `_max_bridge_length = 6`, `_max_tunnel_length = 6`, `_cost_bridge_per_tile = 150`,
  `_cost_tunnel_per_tile = 120`, `_max_cost = 10000000`.
- `ai/TrainLineAI/main.nut` ne règle que `cost.max_cost` (à 200000, soit 50× moins que le défaut).
- Un pont a été mesuré sur 15 lignes construites (graine 7, rang 120, saut de 3 tuiles).

**Et relever les plafonds ne sert à rien.** Essai apparié sur 9 cas `PATHLIM` avec
`max_bridge_length = 20` : **0/9** bascule, **aucun pont de plus de 6 tuiles jamais retenu**, et
**+12,6 % de ticks** de pathfinding (18 longueurs candidates testées par nœud d'obstacle au lieu
de 4). Un cas est même passé à 11 159 ticks, au-delà de la barrière de 11 000.

La contrainte réelle est le **plafond de 30 000 itérations d'A\***, couplé à la barrière : une
itération coûte ~2 700 opcodes pour un budget de ~10 000 par tick, soit 3,7 itérations par tick,
donc 30 000 itérations ≈ 8 100 ticks — contre une barrière à 11 000. **Le pathfinding consomme
déjà ~96 % de son budget disponible.** On ne peut pas chercher plus loin sans déplacer la barrière.

---

## 6. Ce qu'il reste à retenir

| Idée | Verdict |
|---|---|
| Construction incrémentale | **Inexistante** dans AAAHogEx — l'hypothèse de départ était fausse |
| Ponts/tunnels en voisins d'A* arbitrés par le coût | **Déjà présent** chez nous via `Pathfinder.Rail` |
| `RetryToBuild` conservant le préfixe construit | **À retenir** — la meilleure idée transposable, sans risque pour la barrière |
| Terrassement pendant la pose | À retenir, mais impose de généraliser la capture de `first_mutation_tick` |
| Pilotage par budget d'opcodes | **N'existe pas** — il mesure, il ne s'adapte pas |

**Recommandation** : pas de portage, pas d'exposition GPL v3. La seule idée à réimplémenter en
clean-room est la reprise conservant le préfixe (§2.2). Le reste du gain est ailleurs — dans le
couple barrière / plafond d'itérations, pas dans la technique de construction.

---

*Rapport d'origine produit par une session Codex, reprise possible via
`codex resume 01a0427d-aece-7ba1-8910-72fb3e773b98`. Les affirmations §1 (planifie puis construit,
découpage à 50 itérations) et §5 (défauts de la bibliothèque, résultat 0/9) ont été revérifiées
directement dans le code et par la mesure.*
