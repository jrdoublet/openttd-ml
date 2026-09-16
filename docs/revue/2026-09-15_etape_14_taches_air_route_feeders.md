# Étape 14 — Tâches air, route et rabattement

- **SHA revu** : `7304613`
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `ai/OpexAI/task_air.nut`, `task_road.nut`, `task_feeders.nut` — 1 754 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

G10 (ligne aérienne déficitaire jamais mise au rebut, flotte sous-comptée) ; état réel de G5
(`rail_refleet` vs `fleet_fix`, cf. `info.nut:2316-2320`) ; rabattement courrier du 09-15.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 14.1 — `_resizeAirFleets` peut réarmer une ligne en cours de mise au rebut        [gravité : P1]
`task_air.nut:619-810` (`OpexAI::_resizeAirFleets`) ne teste jamais `line.scrapping`, contrairement à
l'équivalent routier `task_road.nut:405` (`if (("scrapping" in line) && line.scrapping) continue;`) dans
`_refleetRoadLines`. Les seuls garde-fous indirects sont `deadStreak >= 2` (refus `"D"`, `task_air.nut:659`)
et `lastProfit < 0` (refus `"L"`, `task_air.nut:662` et `714`). Or `task_report.nut::_reportLines` recalcule
`deadStreak` et `lastProfit` **chaque année pour toute ligne aérienne**, y compris celles déjà
`scrapping = true` (`task_report.nut:263-274`, branche `VT_AIR` : `nextStreak = profit < 0 ? priorStreak + 1
: 0`, écrasement inconditionnel). Pendant la fenêtre de vente étalée (`SCRAP_TIMEOUT_YEARS = 2`,
`main.nut:99`), les appareils pas encore rentrés au dépôt continuent de voler et de générer un profit
mesuré ; si cette mesure est positive une année, `deadStreak` retombe à 0 et `lastProfit >= 0` — les deux
seuls refus qui protégeaient la ligne tombent en même temps. Rien dans `_resizeAirFleets` ne vérifie plus
alors que la ligne est en cours de liquidation (`have >= 1` reste vrai tant que la vente n'est pas
terminée), et la boucle de croissance (`task_air.nut:788-798`, `OpexAirAddPlane`) peut acheter un avion
**neuf** sur une ligne dont les avions existants sont au même moment envoyés au hangar pour y être vendus
(`task_report.nut:330`, `AIVehicle.SendVehicleToDepot`) — l'inverse exact de l'intention du correctif G10
documenté juste à côté (`task_report.nut:264`).

### 14.2 — Le mécanisme de mise au rebut d'une ligne aérienne n'existe pas dans `task_air.nut`        [gravité : P3]
`task_air.nut` ne calcule jamais `deadStreak` ni `lastProfit` pour une ligne aérienne : c'est
`task_report.nut::_reportLines` (branche `VT_AIR`, lignes 263-274, commentée explicitement `/* G10 : ... */`)
et `_scrapDeadLines`/`_triggerScrapLine` (lignes 312-459) qui décident et exécutent le rebut.
`task_air.nut::_resizeAirFleets` ne fait que **lire** `line.deadStreak` (refus `"D"` ligne 659, `"S"` ligne
713) et `line.lastProfit` (refus `"L"` lignes 662/714) comme motifs de refus de croissance de flotte — jamais
comme déclencheurs de rebut. Conséquence pour l'énoncé du plan : « tracer pourquoi une ligne déficitaire ne
rejoint jamais le rebut normal » ne peut pas se conclure depuis `task_air.nut` seul ; le fichier qui porte la
décision est `task_report.nut` (étape 15). Voir aussi 14.1, seul point où `task_air.nut` influe réellement sur
le sort d'une ligne en cours de rebut.

### 14.3 — G5 : entièrement rail, aucune trace dans task_air/task_road/task_feeders        [gravité : P3]
`rail_refleet` (`info.nut:2121-2126`, les quatre `*_value` à `1` → actif par défaut) et `rail_expand`
(`info.nut:1418-1423`, les quatre `*_value` à `0` → inactif par défaut) ne sont lus que par
`task_rail.nut::_expandRailLines` (étape 13) — grep ciblé confirmé négatif sur `rail_refleet`/`rail_expand`
dans les trois fichiers du périmètre. Le commentaire `info.nut:2314-2321` documente la rectification :
depuis le commit `3a15646` (« fix items G1 G7 from code review », 2026-09-07), la garde qui rendait
`rail_refleet` inatteignable a été rendue **inconditionnelle** dans `_expandRailLines` et dans la tâche
`"expand"` — `rail_refleet` est donc réellement atteignable au défaut livré (`rail_expand=0,
rail_refleet=1`), **indépendamment de `fleet_fix`**. C'est cette lecture rectifiée qui tient à la lecture
actuelle du code, pas le G5 original repris tel quel par le plan. Vérification exhaustive impossible depuis
ce périmètre : `_expandRailLines` est dans `task_rail.nut`, hors des trois fichiers assignés à l'étape 14.

### 14.4 — Lignes feeder sans champ `kind` : confirmé (hérité étape 9)        [gravité : P2]
Les deux constructeurs de feeders dans `task_feeders.nut` — bus (`_tryBuildFeeders`, dict de ligne
`task_feeders.nut:202-230`) et camion postal (`_tryBuildMailFeeder`, dict de ligne `task_feeders.nut:354-376`)
— omettent tous deux `kind` du dictionnaire de ligne, alors que `task_road.nut:349` l'inclut
systématiquement (`kind = candidate.kind`) pour toute ligne pax/fret classique construite par
`_tryBuildRoadProject`. `candidate.kind` est pourtant lu par `task_feeders.nut:175` pour calculer
l'économie de la ligne (`OpexRoadLineEconomics(..., candidate.kind, ...)`) — la valeur existe côté candidat,
elle n'est simplement jamais reportée sur `this._lines`. Confirme le constat de l'étape 9 : les lignes
feeder créées par `task_feeders.nut` sont structurellement hors de portée de toute logique de sélection
indexée sur `line.kind` (dont `feeder_extension`, dont l'éligibilité vit dans `builder_road.nut`/`candidates.nut`).

### 14.5 — `feeder_mail_strict_orders` conditionnel côté courrier, correctif inconditionnel côté bus : confirmé        [gravité : P2]
`task_feeders.nut:332-334` conditionne encore les indicateurs d'ordre du camion postal à
`FEEDER_MAIL_STRICT_ORDERS` (`info.nut:1303-1309`, défaut `1`) :
```
local sourceFlags = (FEEDER_MAIL_STRICT_ORDERS ? AIOrder.OF_NO_UNLOAD : AIOrder.OF_NONE) | nonstopFlag;
local destFlags = AIOrder.OF_TRANSFER
    | (FEEDER_MAIL_STRICT_ORDERS ? AIOrder.OF_NO_LOAD : (C53_ORDER_NOLOAD ? AIOrder.OF_NO_LOAD : 0))
    | nonstopFlag;
```
Sous `0`, `sourceFlags` retombe à `AIOrder.OF_NONE` : le camion peut charger/décharger à l'arrêt ville, un
comportement distinct du défaut. `task_road.nut` ne contient aucune construction d'ordre (grep confirmé :
seule occurrence de `OF_TRANSFER` dans ce fichier est un commentaire, `task_road.nut:325`) — la construction
d'ordres des deux chemins bus vit entièrement dans `builder_road.nut`, hors périmètre, où l'étape 9 avait
déjà noté que le même correctif y est **inconditionnel**. Conséquence pratique de l'asymétrie confirmée
ici côté courrier : la description du réglage (« `0 = legacy orders for causal benchmark` »,
`info.nut:1305`) est trompeuse — mettre `feeder_mail_strict_orders=0` ne restaure le comportement legacy que
pour le camion postal, jamais pour les bus feeder correspondants, donc le « banc causal » que le réglage
prétend permettre ne compare pas des bras symétriques.

## Vérifié, n'est PAS un bug

### 14.6 — Flotte aérienne : pas de sous-comptage reproductible avant le premier rapport annuel
`vehCount` et `lastLiveVehicles` sont écrits **immédiatement** à la construction d'une ligne aérienne, sur
les deux chemins de construction identiques : `task_air.nut:193-195` (`_tryBuildAir`) et `task_air.nut:487-489`
(`_tryBuildAirProject`), tous deux avec `result.vehicles.len()` — la flotte réellement livrée par
`OpexBuildAirRoute`, pas une prévision (`plan.planes`, distinct, sert uniquement à `predTrains`). Le seul
autre point de mise à jour hors cycle de rapport annuel est le crash confirmé (`event_handlers.nut:47`,
hors périmètre : `line.vehCount--`), également immédiat, pas différé au rapport suivant. Dans
`_resizeAirFleets`, `have` (`task_air.nut:657`) lit `vehCount` avec un repli sur `vehicles.len()` puis `0` —
aucune des deux valeurs ne peut être inférieure à la flotte réelle au moment où ce code s'exécute. Aucune
fenêtre de sous-comptage n'a été trouvée dans les trois fichiers du périmètre ; si le symptôme mesuré par le
plan est réel, sa cause est ailleurs (candidats/portefeuille amont, ou état antérieur à un correctif déjà
appliqué ici) — pas dans `task_air.nut` tel qu'il se lit aujourd'hui.

## Hors périmètre, à relire ailleurs

- **G10, décision et exécution du rebut** (14.2) — `task_report.nut::_reportLines` /
  `_scrapDeadLines` / `_triggerScrapLine` (lignes 20-459) : étape 15.
- **G5, `rail_refleet`/`rail_expand`/`fleet_fix`** (14.3) — `task_rail.nut::_expandRailLines` : étape 13.
- **Construction d'ordres des feeders bus** (contexte de 14.5) — `builder_road.nut` : étape 9 (déjà traité,
  confirmation croisée uniquement ici).
- **`feeder_extension` / éligibilité par `line.kind`** (contexte de 14.4) — `candidates.nut` : étape 9 a
  déjà renvoyé ce point ici ; la génération du candidat d'extension elle-même reste dans `candidates.nut`,
  non revue en détail dans cette étape.
