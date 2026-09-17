# Étape 09 — Constructeur routier

- **SHA revu** : `5b770ac` (dernier commit touchant le périmètre : `c74a123`, « fix feeder and add early air slot »)
- **Modèle / effort prévus** : Opus 5 / high
- **Périmètre** : `ai/OpexAI/builder_road.nut` — 1 606 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Symétrie construction/refleet du correctif feeders bus du 09-15.
`OpexRoadPhysicalVehicleCap = 2 × min(arrêts)` : écrase la cible, confond terminus et transit.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 09.1 — Le correctif feeders a manqué un TROISIÈME chemin d'ordre : `feeder_extension` réinjecte `OF_NONE` en ville        [gravité : P1]
`ai/OpexAI/builder_road.nut:1452` — `OpexBuildRoadExtension` pose `local flags = C53_ORDER_NONSTOP ? AIOrder.OF_NON_STOP_INTERMEDIATE : AIOrder.OF_NONE;` et insère l'ordre avec ces mêmes `flags` (`:1471`), **sans aucun test `isFeeder`**, alors que les lignes 1455-1457 et 1468-1470 juste au-dessus branchent explicitement sur `candidate.extensionType == "feeder_extension"` (cible = `stationB` = le hub, `insertPos = targetPos`, donc l'arrêt neuf s'insère **entre** l'arrêt ville et le hub).
· Ce que le code prétend faire : `c74a123` a rendu les feeders strictement unidirectionnels — ville `OF_NO_UNLOAD`, hub `OF_TRANSFER | OF_NO_LOAD` — sur les deux chemins qu'il a touchés (`:1278-1280` construction, `:1570-1572` refleet).
· Ce qu'il fait réellement : la séquence d'ordres d'un feeder étendu devient `[A ville : OF_NO_UNLOAD] → [A' ville : OF_NONE] → [hub : OF_TRANSFER|OF_NO_LOAD]`. Sous `OF_NONE`, le bus décharge à `A'` tout le cargo que la station accepte — or `A'` est choisi par `OpexRoadExtensionSite` (`:585`) précisément sur une tuile qui **produit** des passagers, donc dans un tissu de maisons qui les **accepte**. Les passagers chargés à `A` sont livrés au trottoir d'en face, à distance ~0, puis le bus recharge et repart. C'est exactement le mode d'échec que le correctif venait d'éliminer à l'ordre 0.
· Le chemin est actif par défaut, pas théorique : `feeder_town_coverage = 1` (`info.nut:1285-1290`), `FEEDER_TOWN_COVERAGE <- true` (`globals_pre.nut:38`), et `candidates.nut:2927-2928` écrit noir sur blanc « Une seule ligne feeder de base par commune. Les arrêts suivants sont des `feeder_extension` de cette ligne et partagent sa liste d'ordres. » L'extension **est** le mode de croissance nominal d'un feeder.
· Conséquence observable : sur toute ligne feeder ayant reçu au moins une extension (panneau `RE|…|F`, `task_road.nut:47-48`), le volume transféré au hub s'effondre pendant que le revenu propre du feeder reste faiblement positif — soit le profil « feeder bâti, hub vide » d'avant le 09-15, mais réapparaissant seulement à partir de la 2ᵉ année de la ligne (`candidates.nut:2372` exige `currentYear > line.year`).

**Clôture B4 — workspace courant, 2026-09-16.** Ce constat était valide au SHA revu mais est
maintenant corrigé. `builder_road.nut` centralise les indicateurs feeder dans
`OpexRoadFeederSourceOrderFlags()` et `OpexRoadFeederHubOrderFlags()` ; construction initiale,
refleet et `OpexBuildRoadExtension()` réutilisent les mêmes helpers. L'extension insère l'arrêt
ville juste avant le hub avec `NO_UNLOAD`, le hub restant `TRANSFER|NO_LOAD`.

Preuve réelle : `results/review_b4_bus_extensions_5x6_ordl.json`, 5 graines × 6 ans, feeders isolés
(`feeder_candidates=1, feeder_hub_check=0, feeder_mail_duplicate=0`), produit **13** événements
`feeder_extension` et **3** `bus_pax_extension`. Les ORDL finaux contiennent 12 listes d'ordres
feeder étendues distinctes : toutes les étapes ville/intermédiaires sont
`LOAD_IF_POSSIBLE + NO_UNLOAD`, tous les hubs `NO_LOAD + TRANSFER`, `errors=[]` et
`invalid_extended_feeders=0` sur les cinq graines. `sweeps/test_b4_feeder_orders.py` passe 6/6 et
le smoke obligatoire après les dernières modifications `.nut` est
`results/review_b4_smoke_2x3.json` (PASSED). Le dernier changement après ce smoke est uniquement
l'inspecteur Python ORDL ; aucun nouveau `.nut` n'a été introduit. Ce 5×6 est une preuve de
fonctionnement/invariant, **pas** une adoption de politique ou de défaut.

### 09.2 — `OpexRoadRefleet` reconstruit 2 ordres et efface silencieusement les extensions payées        [gravité : P2]
`ai/OpexAI/builder_road.nut:1582-1584` — la branche « aucun véhicule survivant » (`template == null`) fait exactement `AppendOrder(first, line.stationA, …)` puis `AppendOrder(first, line.stationB, …)` et exige `GetOrderCount(first) == 2`.
· Ce qu'elle prétend faire : « reconstitue moteur + ordres comme à la construction » (`:1507-1508`).
· Ce qu'elle fait : la construction n'est pas le seul producteur d'ordres. `line.extraStops` (alimenté par `task_road.nut:40-41`) peut contenir jusqu'à `OpexRoadTownStopLimit` arrêts insérés par `OpexBuildRoadExtension`. Le refleet les ignore, et tous les clones suivants (`:1589`, `share = true`) héritent de la liste amputée.
· Conséquence observable : après une perte totale de flotte (âge, passage à niveau, renouvellement raté) sur une ligne étendue, les arrêts d'extension restent bâtis mais plus aucun véhicule ne les dessert → note de station à −1, cargo qui stagne. Et la réparation automatique est bloquée : `OpexRoadLineTownStopCount` (`candidates.nut:2326-2332`) compte toujours `line.extraStops`, donc la ligne est réputée au plafond d'arrêts de sa commune et aucun nouveau `bus_pax_extension` / `feeder_extension` ne sera proposé pour la reconstruire.

### 09.3 — La cible de flotte volumétrique est écrasée avant d'atteindre le constructeur        [gravité : P2]
`ai/OpexAI/builder_road.nut:1321` — `local want = candidate.trains;` est le seul dimensionnement lu par le constructeur.
· `candidate.trains` arrive déjà écrasé : `economy.nut:630-633` calcule `vehiclesForVolume` (la vraie cible, dérivée de `offered / (capacity × tripsPerMonth)`) puis `local roadVehicleCap = MARGINAL_FLEET ? 1 : OpexRoadPhysicalVehicleCap(1, 1);` → `2`, et `if (vehicles > roadVehicleCap) vehicles = roadVehicleCap;`. `MARGINAL_FLEET <- false` par défaut (`globals_post.nut:246`).
· Le plafond est donc appliqué avec les arguments **littéraux `(1, 1)`**, c'est-à-dire l'hypothèse « 1 quai par bout », alors que le commentaire de `economy.nut:586-588` promet que « `OpexRoadPhysicalVehicleCap` est réappelée en aval (`builder_road.nut`, `main.nut`) avec les VRAIS comptes de quais ». En aval, `builder_road.nut:1325-1328` ne relève `want` que si `ROAD_MULTISTOP` — or `ROAD_MULTISTOP <- false` par défaut (`globals_post.nut:94`) **et** le bloc multistop exclut de toute façon les bus (`:1189`, `plan.vehType != AIRoad.ROADVEHTYPE_BUS`). Pour toute ligne de bus, `result.nStopsA = result.nStopsB = 1` à jamais, donc `physicalCap = 2` à jamais.
· Conséquence observable : `vehiclesForVolume` n'est stocké nulle part, ni journalisé, ni reporté sur `line` — l'information « cette ligne voulait 7 bus » est détruite à la source. Le projecteur de revenu de `OpexRoadLineEconomics` tourne ensuite sur la flotte tronquée, donc la ligne est aussi *scorée* comme une ligne à 2 bus. Ni `_refleetRoadLines` (`task_road.nut:514-515`, `if (target > physicalCap) target = physicalCap;`) ni le rapport annuel ne peuvent rattraper ce que le classement a jeté. C'est cohérent avec l'écart de volume mesuré contre AAAHogEx (564 véhicules contre 102).

### 09.4 — Le plafond est une contrainte de *stock* (quais occupés) appliquée à un *flux* (flotte totale)        [gravité : P2]
`ai/OpexAI/builder_road.nut:1311-1314` — le commentaire énonce correctement la règle du jeu : « un arret n'accueille que DEUX vehicules **a la fois**, au-dela ils font la queue sur la route ». C'est une contrainte de simultanéité.
· `OpexRoadPhysicalVehicleCap(nStopsA, nStopsB) = 2 × min(nStopsA, nStopsB)` (`economy.nut:589-595`) la transforme en borne sur la **flotte entière** de la ligne, ce qui n'est exact que si le temps de trajet est nul, c'est-à-dire si tous les véhicules sont en permanence au terminus. Un véhicule en transit n'occupe aucun quai.
· Le même fichier dispose pourtant du modèle temporel qui manque : `oneWayDays = transitDays + dwellDays` avec `ROAD_PAX_STOP_DWELL_DAYS = 6` (`globals_pre.nut:25`, `economy.nut:606-611`). La fraction de cycle réellement passée à quai vaut `dwell / (transit + dwell)` ; sur une liaison de 20 tuiles elle tombe sous 50 %, donc le nombre de bus soutenables sans file d'attente est plus proche de 4-5 que de 2. Le plafond est à peu près juste dans le seul cas dégénéré de la ligne intra-ville très courte, et systématiquement trop serré partout ailleurs — l'erreur croît avec la distance, donc avec le revenu par trajet.
· Second effet du même amalgame : un arrêt d'extension **est** un quai de plus et **ajoute** ~6 jours de dwell au cycle, mais `task_road.nut:40-47` n'incrémente ni `line.nStopsA` ni `line.nStopsB`. Une extension dégrade donc mécaniquement la fréquence de la ligne sans jamais lui ouvrir droit à un véhicule supplémentaire.
· (Conformément au plan : aucune suppression du plafond n'est proposée ici — C50b l'a déjà réfutée. Le constat porte sur la grandeur physique modélisée, pas sur l'existence de la borne.)

### 09.5 — La formule du plafond est réimplémentée à la main au lieu d'être appelée        [gravité : P3]
`ai/OpexAI/builder_road.nut:1325-1328` — `local nMin = result.nStopsA < result.nStopsB ? result.nStopsA : result.nStopsB; if (nMin < 1) nMin = 1; local berths = 2 * nMin;` recopie caractère pour caractère le corps de `OpexRoadPhysicalVehicleCap` (`economy.nut:591-594`), que le commentaire situé six lignes plus haut (`:1318`) nomme pourtant explicitement. `task_road.nut:482` appelle bien la fonction, lui. Trois sites, deux appels et une copie : toute évolution du plafond (l'objet même de C61) devra être faite à deux endroits, dont un qui ne cite pas la fonction dans son code.

### 09.6 — La docstring de `OpexRoadRefleet` annonce un plafond que la fonction n'applique pas        [gravité : P3]
`ai/OpexAI/builder_road.nut:1508-1510` — « N'ajoute jamais au-delà du plafond de quais de la ligne (2 x min(nStopsA, nStopsB), sinon MAX_ROAD_VEHICLES). » Le corps (`:1511-1606`) ne lit ni `nStopsA`, ni `nStopsB`, ni `MAX_ROAD_VEHICLES` : il construit `missing = target - have` (`:1514`) et n'est borné que par la trésorerie (`:1546-1548`). Le plafond est entièrement à la charge de l'unique appelant, `task_road.nut:514-515`. L'invariant est donc externe et non gardé ; il ne survivra pas à un second appelant (le refleet après crash de `event_handlers.nut`, par exemple).

### 09.7 — Le refleet ne revérifie ni la compatibilité de motorisation ni la capacité réelle        [gravité : P3]
`ai/OpexAI/builder_road.nut:1564-1566` vs `:1261-1266` — la construction vérifie après achat `AIVehicle.GetCapacity(first, cargo) <= 0 || !AIRoad.RoadVehHasPowerOnRoad(AIVehicle.GetRoadType(first), catalog.roadType)` et annule la transaction (motif `POWER`). Le refleet, qui rebâtit pourtant le même véhicule depuis zéro avec un moteur relu dans `catalog.roadEngineByCargo` (`:1535`) — donc le moteur *courant* du catalogue, pas celui d'origine de la ligne —, se contente de `OpexRoadRefitCapacity(...) <= 0` (`:1561`). Si le catalogue a basculé sur un type de route que le dépôt de la ligne ne porte pas, le véhicule est acheté, démarré et compté dans `result.added` sans jamais pouvoir rouler.

### 09.8 — `AIController.GetSetting` rappelé par candidat dans le chemin chaud de planification        [gravité : P3]
`ai/OpexAI/builder_road.nut:743` — `local cheapOn = ROAD_CHEAP_TRACE || (AIController.GetSetting("road_cheap_trace") != 0);` alors que ce même réglage est déjà lu une fois dans `settings.nut:349` vers la globale `ROAD_CHEAP_TRACE`. La convention du projet (`CLAUDE.md`, « Réglages ») est la lecture unique. Ici la relecture est faite à chaque appel de `OpexRoadPlanFor`, c'est-à-dire par candidat routier examiné, dans un budget d'opcodes qui ne se cumule pas d'un tick à l'autre. Le `||` rend la valeur identique, donc c'est un coût et une divergence de convention, pas un changement de comportement.

### 09.9 — Le commentaire du bloc multistop affirme `MAX_ROAD_VEHICLES = 2`, la constante vaut 8        [gravité : P3]
`ai/OpexAI/builder_road.nut:1185` — « Le classement reste a MAX_ROAD_VEHICLES = 2 ». `economy.nut:541` déclare `const MAX_ROAD_VEHICLES = 8`. La divergence est déjà documentée à `economy.nut:578-580` (« le commentaire ci-dessus dit […] mais la constante vaut 8, pas 2 : elle a diverge de sa propre justification ») ; la copie de `builder_road.nut` n'a pas été mise à jour. Le chiffre est faux partout où `C50B_ROAD_CAP_RELAX` (défaut `false`, `globals_pre.nut:286`) ferait retomber le plafond sur cette constante.

## Vérifié, n'est PAS un bug

### 09.A — Les deux chemins du correctif feeders du 09-15 sont rigoureusement symétriques
Comparaison ligne à ligne de `builder_road.nut:1273-1299` (construction, `OpexBuildRoadRoute`) et `:1567-1584` (refleet, `OpexRoadRefleet`, branche `template == null`), confirmée par `git show c74a123 -- ai/OpexAI/builder_road.nut` :

| | construction | refleet |
|---|---|---|
| `nonstopFlag` | `:1273` `C53_ORDER_NONSTOP ? OF_NON_STOP_INTERMEDIATE : 0` | `:1567` identique |
| prédicat feeder | `:1274` `("isFeeder" in candidate) && candidate.isFeeder` | `:1569` `("isFeeder" in line) && line.isFeeder` |
| prédicat fret | `:1289` `candidate.kind == "freight"` | `:1568` `("kind" in line) && line.kind == "freight"` |
| `sourceFlags` | `:1278-1280` `(isFeeder ? OF_NO_UNLOAD : (isFreight ? OF_FULL_LOAD_ANY : OF_NONE)) \| nonstopFlag` | `:1570-1572` identique |
| `destFlags` feeder | `:1292` `OF_TRANSFER \| OF_NO_LOAD` (inconditionnel) | `:1575` identique |
| `destFlags` fret | `:1294` `C53_ORDER_NOLOAD ? (OF_UNLOAD\|OF_NO_LOAD) : OF_NONE` | `:1577` identique |
| `destFlags` autre | `:1296` `OF_NONE` | `:1579` identique |
| `\| nonstopFlag` final | `:1298` | `:1581` |

Aucune divergence de logique, d'ordre d'évaluation ni de valeur. Le correctif a bien retiré des deux côtés le conditionnement de `OF_NO_LOAD` à `C53_ORDER_NOLOAD` (défaut `false`, `globals_pre.nut:381`), qui était la cause de la reprise de passagers au hub au retour. Les deux combinaisons produites (`OF_NO_UNLOAD` seul ; `OF_TRANSFER|OF_NO_LOAD`) passent `AreOrderFlagsValid` : les exclusions mutuelles sont `TRANSFER`/`UNLOAD`, `TRANSFER`/`NO_UNLOAD`, `UNLOAD`/`NO_UNLOAD`, `NO_UNLOAD`/`NO_LOAD` et `FULL_LOAD_ANY`/`NO_LOAD` — aucune n'est enfreinte.
**Au SHA revu, la régression survivante n'était pas entre ces deux blocs : c'était le troisième
site d'ordre, `OpexBuildRoadExtension` (constat 09.1).** Elle est maintenant corrigée dans le
workspace courant par la centralisation des helpers feeder décrite dans la clôture B4 ci-dessus.

### 09.B — La lecture `line.isFeeder` seule (sans `|| line.purpose == "feeder"`) est sûre en pratique
`builder_road.nut:1569` n'utilise que la moitié du prédicat employé partout ailleurs (`candidates.nut:1113, 2117, 2148, 2167, 2212, 2326, 2374, 2813` ; `task_report.nut:357-359` ; `event_handlers.nut:238-240`). Vérifié : les trois seuls producteurs d'enregistrement de ligne feeder posent bien `isFeeder = true` — `task_road.nut:362`, `task_feeders.nut:220`, `task_feeders.nut:371`. Et `persist.nut:30-70 / 175-196` recopie les tables de ligne telles quelles (projection superficielle uniquement pour convertir les flottants), donc le champ survit à une sauvegarde/rechargement. Aucune ligne ne porte `purpose == "feeder"` sans `isFeeder`. Prédicat plus étroit que l'idiome du projet, mais pas faux.

### 09.C — `OpexRoadCheapPlan` mute deux globales et les restaure sur tous ses chemins
`builder_road.nut:416-426` sauvegarde `ROAD_MAX_SITE_PROBES` / `ROAD_MAX_SITES_PER_END`, les abaisse à 16/2, et les restaure **avant** le premier `return` possible (`:427`). Aucune sortie anticipée ne saute la restauration. Squirrel n'a pas d'exception ici. Ce n'est pas une fuite d'état global.

### 09.D — Le contournement du filtre d'espacement par le chemin `cheap` est rattrapé transactionnellement
`OpexRoadCheapPlan` ne passe pas `excludeTiles` (`:421` `null`, `:424` défaut `null`), là où `OpexRoadPlanFor` construit `excludeA` depuis `OpexRoadOurBusTiles()` (`:769-777`). Le chemin cheap peut donc planifier un arrêt trop proche d'un arrêt bus existant. Mais `OpexBuildRoadRoute:1092-1100` revalide `ROAD_BUS_STOP_MIN_DISTANCE` contre les arrêts **vivants** avant tout engagement et renvoie `SPACING`. Le coût est un plan perdu, jamais un arrêt mal placé. De plus `road_cheap_trace` vaut 0 par défaut (`info.nut:2572-2577`) et `ROAD_CHEAP_TRACE <- false` (`:34`).

### 09.E — La duplication apparente des vérifications post-pose n'est pas redondante
`:1134-1136`, `:1157-1159` et `:1236-1238` combinent `IsRoadStationTile`/`IsRoadDepotTile` (géométrie déclarée), `GetRoadStationFrontTile`/`GetRoadDepotFrontTile` (offset déclaré) et `AreRoadTilesConnected` (connectivité réelle). Les commentaires attenants justifient chaque prédicat par une mesure du 2026-08-28 ; le test de connectivité est le seul qui prouve que le véhicule peut monter sur la façade. Ne pas fusionner.

## Hors périmètre, à relire ailleurs

### 09.F — `economy.nut:589-595` + `:630-633` : le plafond lui-même et son application au classement
Le cœur du mécanisme décrit en 09.3 et 09.4 vit dans `economy.nut`, pas dans le périmètre. L'appel littéral `OpexRoadPhysicalVehicleCap(1, 1)` et la destruction de `vehiclesForVolume` y sont. → étape couvrant `economy.nut`.

### 09.G — `task_feeders.nut:332-334` : le correctif feeders a un QUATRIÈME site, celui-là conditionnel
`c74a123` a aussi corrigé le camion postal (C29.5), mais derrière un drapeau neuf : `sourceFlags = FEEDER_MAIL_STRICT_ORDERS ? OF_NO_UNLOAD : OF_NONE`, `destFlags = OF_TRANSFER | (FEEDER_MAIL_STRICT_ORDERS ? OF_NO_LOAD : (C53_ORDER_NOLOAD ? OF_NO_LOAD : 0))`. Défaut 1 (`info.nut:1304-1309`, `globals_pre.nut:43`), donc actif. Mais les deux chemins bus (`builder_road.nut:1278`, `:1570`) sont **inconditionnels** : mettre `feeder_mail_strict_orders = 0` ne ramène que le camion postal à l'ancien comportement, jamais le bus. Le « legacy orders for causal benchmark » annoncé par la description du réglage ne peut donc pas isoler l'effet du correctif — le bras 0 est un mélange. → étape couvrant `task_feeders.nut` / méthodologie de banc.

### 09.H — `candidates.nut:2366` : les lignes feeder créées par `task_feeders.nut` n'ont pas de champ `kind`
`OpexRoadExtensionCandidates` exige `("kind" in line) && line.kind == "pax"`. Les enregistrements de `task_feeders.nut:202-230` et `:355-376` posent `mode = "road"` mais **aucun** `kind` (contrairement à `task_road.nut:352`). Ces lignes-là sont donc structurellement inéligibles à `feeder_extension`, alors que les feeders passés par le chemin générique (`candidates.nut:2960-2964` → `task_road.nut:341+`) le sont. Deux populations de feeders au comportement de croissance différent, sans raison apparente. Détermine le rayon d'action réel du constat 09.1. → étape couvrant `task_feeders.nut` / `candidates.nut`.

**Clôture B4 — workspace courant.** Le feeder **bus** de `task_feeders.nut` persiste désormais
`kind = candidate.kind`, ce qui le rend éligible à `feeder_extension`. Le feeder **courrier** reste
volontairement sans `kind` afin de ne pas être classé comme une ligne pax et étendu par ce mécanisme.
Le 5×6 ORDL-aware du 2026-09-16 a effectivement observé 13 `feeder_extension` réelles.

### 09.I — `task_road.nut:40-47` : `extraStops` grandit, `nStopsA`/`nStopsB` non
Bookkeeping de l'extension, hors périmètre, mais c'est lui qui rend permanent le `physicalCap = 2` décrit en 09.4 et qui bloque la reconstruction décrite en 09.2. → étape couvrant `task_road.nut`.

## Clôture B3 — 2026-09-16

09.3/09.4 ont été traités sans supprimer le garde-fou de congestion. `vehiclesForVolume` est
désormais conservé comme cible brute ; `roadBerthCapacity` désigne uniquement la simultanéité de
quai ; `roadVehicleCap` désigne le plafond de flotte. `road_time_scaled_cap` reste **0 par défaut**.
Sous 1, le cap temporel est pax-only, conservateur et borné par `MAX_ROAD_VEHICLES`; le fret conserve
strictement l'ancien cap faute de modèle de chargement démontré. Le chemin `task_road`/refleet,
les feeders, le ranking, `PROJECT_CHOSEN`, le rapport annuel et la persistance portent ces notions
sans réutiliser `vehiclesForVolume` comme capacité physique.

Tests : `sweeps/test_b3_road_fleet_targets.py` **12/12**, selftest du diagnostic et compilation
Python OK, `git diff --check` final OK. Smoke post-dernier `.nut` :
`results/review_b3_time_scaled_cap_smoke_2x3_v3.json` → **PASSED 2/2**.

Diagnostic apparié final : `results/review_b3_time_scaled_cap_paired_5x6_v2.json` → 5 paires,
10/10 runs sains/complets. Tous les invariants de séparation passent ; `variant_pax_temporal_cap_exercised`
est faux pour une raison causale : `road_pax_build=0` au défaut, aucun pax dans ranking/chosen, et
les lignes pax observées sont `town_growth` avec `raw_vehs <= 1`. La variante n'améliore donc pas
un mécanisme réellement exposé et donne `company_value` moyen -52 094,8 £, `profit_year`
-29 119,4 £/an, 2 V / 3 D sur les deux métriques. **Pas de 20×10**, défaut laissé à 0 ; le switch
et l'instrumentation restent disponibles pour un futur contexte où le pax interurbain serait actif.

Le fichier `results/review_b3_time_scaled_cap_paired_5x6.json` antérieur ne doit pas être cité comme
preuve : son harnais avait produit une télémétrie B3 vide. Seul le suffixe `_v2` porte la campagne
diagnostique finale.
