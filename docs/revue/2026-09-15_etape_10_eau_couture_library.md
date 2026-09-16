# Étape 10 — Mode eau et couture avec ai/library

- **SHA revu** : `5b770ac`
- **Modèle / effort prévus** : Sonnet 5 / medium
- **Périmètre** : `ai/OpexAI/builder_water.nut`, `lib_water.nut` — 1 474 l., plus les points d'appel MinchinWeb/SuperLib
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Gel `MinchinWeb.Lakes` (3/20 graines, C56), `WATER_LAKES_OPS` jamais calibré, repli Manhattan non
conservateur, et le seul `Valuate` à fonction Squirrel du dépôt (`lib_water.nut:306`).

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 10.1 — `WATER_LAKES_OPS = 50 000` : premier jet non calibré, et ne couvre pas tout le coût d'une requête        [gravité : P1]
`lib_water.nut:550-551` porte le commentaire explicite « Premier jet non calibré : le banc dira
si 50 000 opcodes coupe trop de paires » — le drapeau qui active ce plafond
(`water_lakes_ops_budget`, `info.nut:416-422`, défaut 1) a été adopté sur un banc 20×10 dont le
gain de *score* est significatif (8/0/12, p = 0,008) mais le gain de *valeur* ne l'est pas
(7/1/12, p = 0,070) — adopté « sur suppression d'un mode d'échec dur », donc le mécanisme est
validé, la valeur numérique 50 000 ne l'est pas.
Plus grave : ce budget ne couvre pas ce qu'il prétend borner. Le contrôle
(`lib_water.nut:194-201`, dans `FindPath`) n'est évalué qu'entre deux tours de la boucle externe
`for (local i = 0; i < iterations; i++)` — jamais à l'intérieur d'un tour, ni pendant
`InitializePath`/`AddPoint` (`lib_water.nut:161-174`, `310-366`), qui s'exécutent avant tout
contrôle d'opcodes et qui déclenchent `_AllGroups` (`lib_water.nut:368-389`, boucle
`do...while (MoreAdded)`) sur un graphe de connexions dont la taille croît avec la partie. Le
code le documente lui-même dans `builder_water.nut:577-580` : « le budget de FindPath ... borne
le NOMBRE d'iterations, pas le cout d'UNE iteration ». Conséquence observable : un tour
d'expansion coûteux (beaucoup de bassins déjà fusionnés) ou un `InitializePath` coûteux peut
dépasser 50 000 opcodes sans jamais être intercepté par ce garde-fou — exactement le mécanisme
que C56 (gel silencieux, non résolu) suspecterait en premier lieu, sans que cette étape prétende
trancher C56.

### 10.2 — Repli Manhattan : plancher géométrique correct, mais optimiste sur le ROI économique        [gravité : P2]
`builder_water.nut:599-606` : quand Lakes prouve la connectivité mais que le BFS borné
(`OpexWaterFindConnection`, `builder_water.nut:340-374`) ne trouve pas de chemin dans sa fenêtre
`WATER_BFS_MARGIN`/`WATER_BFS_MAX_NODES`, `navigableDistance` retombe sur `tariffDistance`
(Manhattan entre quais), avec le commentaire « Repli conservateur ... toujours <= la distance
navigable reelle ». La borne géométrique elle-même est correcte (le nombre minimal de pas sur
une grille 4-connexe est le Manhattan ; un vrai détour côtier ne peut être plus court). Mais
`navigableDistance` n'est pas qu'un affichage : il devient directement `oneWayDays` dans
`OpexWaterEconomics` (`builder_water.nut:423-443`), qui pilote `tripsPerMonth` (donc la capacité
mensuelle transportée) et sert d'argument « jours » à `AICargo.GetCargoIncome` (bonus de vitesse
sur le revenu unitaire, `builder_water.nut:443`). Sous-estimer la distance navigable sous-estime
donc `oneWayDays`, ce qui surestime À LA FOIS la capacité et le revenu unitaire : le repli est un
plancher de distance conservateur, mais un plafond de ROI optimiste — l'inverse de ce que « repli
conservateur » suggère au lecteur. Le compteur `profile.lakes_fallback_navigable`
(`lib_water.nut` via `OpexWaterLakesConnected`, incrémenté `builder_water.nut:606`) existe déjà
pour mesurer la fréquence réelle de ce cas, mais rien dans le fichier ne l'exploite pour corriger
le biais.

### 10.3 — Le BFS borné réintroduit comme juge à la construction, après dépense de capital réelle        [gravité : P1]
`builder_water.nut:735-748` : `OpexBuildWaterRoute` construit d'abord les deux quais réels
(`AIMarine.BuildDock`, lignes 699 et 706 — argent dépensé), puis revérifie la connectivité avec
`OpexWaterFindConnection` (le même BFS borné à `WATER_BFS_MARGIN = 24` tuiles et
`WATER_BFS_MAX_NODES = 12000`, `builder_water.nut:29-30`) — explicitement « pas
`OpexWaterLakesConnected` » (commentaire lignes 735-739), au motif que Lakes ne ferait qu'un hit
de cache sur les mêmes tuiles. C'est exactement la fenêtre bornée que Lakes a été introduit pour
contourner à l'étage du tri des paires (`builder_water.nut:533-536` : « une paire au-dela de
l'ancien `WATER_BFS_MARGIN=24` n'est plus ecartee a tort »). Si la paire choisie doit son
admission à une connexion prouvée par Lakes au-delà de cette fenêtre de 24 tuiles, ce second
contrôle peut échouer (`< 0`) sur une paire réellement viable, déclenchant
`OpexWaterRollback(dockA, dockB, null, null)` (`builder_water.nut:663-669`, `740-743`) : les deux
quais tout juste construits sont démolis (`AIMarine.RemoveDock`), sans qu'aucun mécanisme ne
rembourse leur coût de construction. Conséquence observable : un échec `NOWATER` à ce stade n'est
pas neutre — c'est du capital réellement dépensé puis perdu, sur une paire que le juge amont avait
pourtant validée.

### 10.4 — `lib_water.nut:306` : le `Valuate` à fonction Squirrel existe, mais il est mort et, même actif, sans risque de crash        [gravité : P3]
`lib_water.nut:301-308` (`GetPathLength`) : `BList.Valuate(_MinchinWeb_Extras_.MinDistance,
this._A)` — confirmé : c'est bien un appel `Valuate` avec une closure Squirrel (pas un
`AITile.*`/`AIEngine.*` natif), le piège classique NoAI (« excessive CPU usage in valuator
function »). Vérification faite à la main (pas au grep seul) sur les deux fichiers du périmètre
et sur un grep de tout `ai/OpexAI` : `GetPathLength` n'a **aucun appelant** en dehors de sa propre
déclaration/définition (`lib_water.nut:185, 301`) — ni dans `builder_water.nut`, ni ailleurs dans
`ai/OpexAI`. La méthode est du code mort hérité de la copie MinchinWeb, jamais invoqué par
`OpexWaterLakesConnected` ni par aucun appelant du projet.
Même en supposant un futur appel : `BList`/`this._A` proviennent de `this._B`/`this._A`, passés
depuis `waterTilesA`/`waterTilesB` (`OpexWaterLakesConnected`, `lib_water.nut:573-583`), qui sont
les fronts d'eau d'un site, plafonnés à `WATER_MAX_WATER_TILES = 8`
(`builder_water.nut:27`, appliqué ligne 85). Le pire cas serait donc ~8×8 = 64 comparaisons
Manhattan — trois ordres de grandeur sous un budget de 10 000 opcodes/tick
(`budget.nut:14`), donc pas le volume (listes de milliers d'entrées) qui caractérise
habituellement ce crash. Statut : motif confirmé présent, mais actuellement inerte et, si
réactivé sans changer les tailles en jeu, sans danger réel de dépassement d'opcodes.

### 10.5 — Grandes cartes (1024²/2048²) : coût RAM/opcodes du graphe Lakes jamais mesuré, proportionnel à la surface        [gravité : P2]
`lib_water.nut:147-159` : le constructeur de `_MinchinWeb_Lakes_` peuple `this._map` (un `AIList`)
avec une entrée par tuile de la carte entière (`for (local i = 0; i < AIMap.GetMapSize(); i++)
this._map.AddItem(i, -2);`), instance unique et persistante pour toute la partie
(`::OpexWaterLakes`, `lib_water.nut:527-532`). Le commentaire ne chiffre que le cas 256×256
(« ~65 536 »). Rien dans `persist.nut` ne sauvegarde `::OpexWaterLakes` : l'instance est
reconstruite en entier à chaque (re)chargement du script, y compris après un `Load()` de partie.
À 1024² (~1,05 M tuiles) et 2048² (~4,19 M tuiles), c'est 16× puis 64× plus d'entrées qu'au cas
mesuré, donc 16×/64× plus de RAM pour cette seule structure et une boucle de construction 16×/64×
plus longue (répartie sur plus de ticks, pas un crash immédiat, mais un coût jamais échantillonné
ni comparé au repère « > 50 Mo = mauvaise IA » cité par `ai/OpexAI/CLAUDE.md`). Aucun banc ni
sonde du périmètre ne couvre une carte au-delà de 256².

**Réconciliation M4 du 2026-09-16.** Le banc 1024² C46 déjà existant est sain et n'a pas été
rejoué. Il ne contient toutefois ni RSS/heap externe ni attribution mémoire à Lakes. 10.5 reste
donc une **question de mesure externe**, pas un défaut technique P1 démontré ; aucun patch de
`lib_water.nut` n'est justifié.

## Vérifié, n'est PAS un bug

- **`OpexWaterDockAccess` : seul `.fronts` est lu par l'appelant** — `builder_water.nut:161-163`
  affirme que seul `.fronts` du retour de `OpexWaterFindDockAccess`/`OpexWaterDockAccess` est
  utilisé ; vérifié à la main : l'unique site d'appel (`builder_water.nut:727-734`) ne lit
  jamais `.waterPart`. Confirmé, pas un oubli.
- **`OpexOpsMeasureBegin`/`OpexOpsMeasureEnd` (`budget.nut:19-31`)** : la formule additionne
  correctement `OPS_PER_TICK` pour chaque tick entièrement traversé entre les deux mesures
  (`mark.left + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left)`) plutôt que de soustraire
  deux restes bruts — sûre pour un contrôle répété à cheval sur plusieurs ticks, comme le fait
  `_MinchinWeb_Lakes_::FindPath`. Le mécanisme de mesure n'est pas en cause dans les constats
  ci-dessus.
- **`water_lakes_connectivity` et son BFS de repli ne sont pas des drapeaux d'expérience
  inertes** : défaut `1`/`1` (`info.nut:408-422`), donc les constats 10.1 à 10.3 portent sur le
  chemin par défaut réellement joué, pas sur du code mort sous un flag à 0.

## Hors périmètre, à relire ailleurs

- **C56 (gel silencieux sur certaines graines)** : le constat 10.1 éclaire un mécanisme
  compatible (le budget d'opcodes ne couvre pas `InitializePath`/`AddPoint` ni le coût d'un seul
  tour de `FindPath`), mais ne prétend pas clore C56 — le diagnostic complet et le cycle annuel
  concerné relèvent de l'étape 15 (`task_report.nut`, `ledgers.nut`), qui porte déjà C56 dans son
  périmètre.
- **Le code source de `ai/library/MinchinWeb_s_MetaLibrary-11` et `ai/library/SuperLib-41`** :
  consultés uniquement pour confirmer la forme des appels (`Lakes.nut`, `Marine.nut`,
  `Pathfinder.Ship.nut`, `Waterbody.Check.nut`) ; la bibliothèque tierce elle-même reste hors
  périmètre de cette étape.
- **Incohérences générales déjà connues du mode eau** (chantier non fini, `docs/taches.md`) :
  volontairement non relistées ici, conformément à la consigne de l'étape.
