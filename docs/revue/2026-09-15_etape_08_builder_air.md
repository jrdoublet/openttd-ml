# Étape 08 — Constructeur aérien

- **SHA revu** : `5b770ac` (branche `claude/zen-goodall-ivgpbh`)
- **Modèle / effort prévus** : Opus 5 / high
- **Périmètre** : `ai/OpexAI/builder_air.nut` — 1 737 l. (lecture intégrale)
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Erreur 771 : 1 396/1 590 `build_failed`, sonde 09-15 à 291/291 sans aéroport OpexAI en ville.
G4 (demande figée à 22 %, coût des arrêts hors ROI) et G7 (`OpexAirRollback` destructeur).

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

**Défauts lus dans `info.nut` (déclaratif, pour qualifier les constats)** :
`air_cheap_site=1` (2484-2487), `air_site_cache=1` (2476-2479), `air_joined_stops=1` (2492-2495),
`air_joined_stop_limit=2` (2500-2504), `air_hub_fix=1` (1994-1997), `fleet_portfolio=1`
(1219-1222) — et **à 0** : `air_demand_plan` (2021-2024), `air_presite` (146-149),
`air_town_limit_memory` (2460-2463), `air_abandon_site` (2448-2451), `marginal_fleet` (2240-2243).

---

## Constats

### 08.1 — `OpexAirFindSite` n'élit plus un site *constructible* mais un site *nivelable* : l'erreur 771 est avalée à l'élection        [gravité : P1]
`builder_air.nut:567-585` (chemin nominal) et `builder_air.nut:471-485` (chemin cache) —
sous `AIR_CHEAP_SITE` (défaut **1**), le sondage `AIAirport.BuildAirport(...)` en `AITestMode`
échoue, le code lit `err`, ne traite explicitement que `ERR_LOCAL_AUTHORITY_REFUSES` (575-577 /
478-480), puis **jette `err`** et délègue à `OpexAirCanLevelFootprint` (581 / 481). Or cette
fonction (`407-419`) ne regarde jamais `err` : elle rend `true` dès `OpexAirFootprintIsFlat`
(`411`) et sinon dès que `AITile.LevelTiles` réussirait en test (`413`). Un refus
`ERR_STATION_TOO_MANY_STATIONS_IN_TOWN` (771) sur un terrain plat ressort donc en `ok = true`,
le site est élu (`603-606`) **et mis en cache** (`604`).
· Ce que le code prétend faire : le commentaire `347-351` annonce un filtre d'emprise dont
« un hit n'est pas encore un site : `OpexAirFindSite` confirme en une sonde », et `580` dit
« test-mode seulement ; le terrassement réel est fait par le constructeur ». La sonde de
confirmation existe bien mais son verdict est écrasé par un test de terrain.
· Le chemin legacy `AIR_CHEAP_SITE=0` (`586-598`) ne présente **pas** ce défaut : il rejoue
`BuildAirport` en test après `LevelTiles` (`594-596`), donc un 771 y laisse `ok = false` et la
ville est écartée. C36.3 a donc converti, sans le dire, une précondition « l'aéroport passerait »
en « le terrain est plat », en même temps qu'il économisait des opcodes.
· Conséquence observable : les villes dont les deux emplacements de station sont pris par
l'adversaire restent élues à chaque scan, et chaque projet élu part en `build_failed` / 771.
C'est le mécanisme qui produit 1 396/1 590 et 291/291 sans aéroport OpexAI en ville.

### 08.2 — Aucune mémoire de ville pour le 771 au défaut, et l'invalidation de site est un no-op pour une erreur de portée ville        [gravité : P1]
`builder_air.nut:40-45` — `OpexAirInvalidateCachedSite` supprime la seule entrée de cache
`town.id + "_" + airport.type` qui pointe encore vers l'ancre refusée ; elle est appelée sur
`PREB`/`PREA`/`AFAIL`/`BFAIL` (`1567`, `1603`, `1629`). C'est une mémoire **de site**, alors que
771 est une erreur **de ville** : la couronne de recherche (`518-609`) est déterministe et le
terrain n'a pas changé, donc le scan suivant réélit la même ancre, la remet en cache (`604`) et
le chantier réchoue à l'identique. Rien dans le fichier ne borne ce cycle.
· La clé de portée ville existe pourtant ici (`OpexAirTownLimitAbandonKey`, `886-889`) et est
**lue** par le planificateur (`1037-1038` pour le bras `newpair`, `1230` pour `hubsite`), mais
elle n'est **jamais écrite** dans ce fichier ; son unique écrivain est `task_air.nut:9-16`,
conditionné à `air_town_limit_memory`, **défaut 0** (`info.nut:2460-2463`). Au défaut,
`_markAirFailedSites` sort dès sa première ligne (`task_air.nut:6`).
· Conséquence observable : dans la configuration par défaut, un refus 771 n'est mémorisé à
aucun niveau — ni ville, ni site (`air_abandon_site` = 0) — et la paire repart au scan suivant.

### 08.3 — Ni nettoyage ni jointure : les 11 appels `BuildAirport` passent `STATION_NEW`, le seul « join » du fichier ne peut pas débloquer un 771        [gravité : P1]
`builder_air.nut:474, 488, 495, 571, 588, 595, 1375, 1595, 1598, 1620, 1623` — tous les appels
utilisent `AIStation.STATION_NEW`. L'API `AIAirport.BuildAirport(tile, type, station_id)` accepte
un `StationID` existant en troisième argument ; ce chemin n'est **jamais** emprunté, donc aucun
*distant join* n'est tenté, ni comme repli sur 771 ni ailleurs.
· Aucun nettoyage n'est tenté non plus : `AIAirport.RemoveAirport` n'apparaît qu'en `1404-1405`
(rollback de nos propres aéroports neufs) et il n'y a **aucun** `AITile.DemolishTile` dans le
fichier. Le code ne cherche jamais à libérer un emplacement.
· Le seul mécanisme de jointure du fichier est `OpexAirBuildJoinedStops` (`1411-1529`) : il joint
des **arrêts de bus** à *notre* station d'aéroport (`stationId`, `1474` et `1512`). Il exige donc
que l'aéroport existe déjà — il est appelé après coup (`1709-1724`) — et ne peut structurellement
pas contourner le plafond de stations de la ville.
· Conséquence observable : confirmation par lecture de l'affirmation du plan (« ni nettoyage ni
distant join ne débloquent ») ; ce n'est pas un repli qui échoue, c'est un repli qui n'existe pas.

### 08.4 — `BFAIL` conserve délibérément l'aéroport A payé, sur le chemin d'échec dominant, ce que le commentaire G7§1 dit avoir supprimé        [gravité : P2]
`builder_air.nut:1628-1638` — quand B échoue, `keepOrphan = (AIGameSettings.GetValue(
"economy.infrastructure_maintenance") == 0)` ; si vrai, le `OpexAirRollback` de la ligne `1634`
**n'est pas appelé** et l'aéroport A, construit et payé en `1595-1600`, reste sur la carte.
· Le commentaire `1401-1403` annonce l'inverse : « l'ancien code ne retirait que airportB […]
laissant un aeroport orphelin sur la carte apres chaque echec BFAIL/STNFAIL/… ». Le correctif
G7§1 couvre bien `STNFAIL`/`HANGAR`/`PLANE`/`ORDFAIL`/`START`, mais `BFAIL` — le seul cas
majoritaire en pratique — réintroduit l'orphelin par une branche explicite.
· Et la configuration de banc est précisément celle qui l'active : le commentaire `950-953` du
même fichier affirme que « la configuration gelee le laisse a false », donc `keepOrphan = true`.
· Conséquence observable : chaque `build_failed` de type `BFAIL` dépense le prix d'un aéroport
sans ligne ; l'orphelin est ensuite récupérable comme hub (`1176-1195`, `routes = 0`) mais il
occupe entre-temps un emplacement de station dans la ville de A — le mécanisme 08.1/08.2 se
nourrit donc aussi de nos propres orphelins. Le coût est bien comptabilisé
(`result.actualCost`, `1636`), ce qui n'est pas contradictoire : il est payé, pas caché.

### 08.5 — La boucle de démarrage passe au rollback des avions **déjà démarrés**, contre ce qu'affirme son commentaire        [gravité : P2]
`builder_air.nut:1696-1706` — `foreach (aircraft in built) { if (!StartStopVehicle(aircraft)) {
… OpexAirRollback(…, built); … } }` : au i-ème échec, `built` contient les i-1 appareils **déjà
démarrés**. Or `OpexAirRollback:1396-1400` se justifie par « La flotte n'est demarree qu'apres
tous les clones et ordres valides : elle est donc encore dans le hangar et peut etre vendue avant
que ce hangar ne disparaisse » — faux dans ce cas précis. `AIVehicle.SellVehicle` sur un avion en
vol échoue, puis `1404-1405` retire les deux aéroports (si aucun n'est réutilisé).
· Conséquence observable : sur un plan `newpair` à plusieurs appareils, un échec de démarrage
tardif laisse un avion en vol, non vendu, avec des ordres vers deux stations supprimées — capital
immobilisé, et `result.ok = false` donc la ligne n'est jamais enregistrée ni ferraillée.
· Portée réelle bornée par `fleet_portfolio=1` : `OpexAirEconomics:652` force alors
`maxAllowed = 1`, donc `plan.planes = 1` et la boucle `1686-1695` ne clone rien. Le chemin est
atteignable dès qu'un plan est dimensionné à > 1 appareil (`fleet_portfolio=0`, ou `plan.planes`
fixé ailleurs).

### 08.6 — G4 résiduel : à l'élection, le coût des arrêts joints est réservé mais leur demande vaut zéro        [gravité : P2]
`builder_air.nut:744-763` — `OpexAirReserveJoinedStops` charge `newAirports * 2 * stopCost` sur
`economics.capital`, recalcule amortissement, profit et ROI, et est appelée sur les trois bras
(`1068`, `1252`, `1310`). Côté demande, rien n'est ajouté : le commentaire `745-746` l'assume
(« Le bassin est inconnu tant que la station jointe n'existe pas »). Le captage réel n'entre dans
le modèle qu'**après** le chantier, via `OpexAirReconcileActualBuild:711-742` (`monthlyPax =
baseMonthly + joinedMonthly`, `716-718`).
· `air_joined_stops` est à **1** par défaut (`info.nut:2492-2495`) — le global `AIR_JOINED_STOPS
<- false` de `builder_air.nut:29` est écrasé par `settings.nut:338`, ce n'est pas un drapeau
inerte. La réserve est donc active sur tous les plans.
· Conséquence observable : biais directionnel à la sélection, proportionnel au nombre
d'aéroports **neufs** — 4 arrêts réservés pour un `newpair`, 2 pour un `hubsite`, 0 pour un
`hubhub` — soit exactement dans le sens qui défavorise l'ouverture de nouvelles paires, alors que
l'écart mesuré avec AAAHogEx est un écart de volume. L'amplitude est modeste
(`catalog.costRoadBusStop`, `catalog.nut:684`) : à quantifier avant d'agir, pas à supposer.
· Second point, plus petit : la réserve utilise la constante 2 et ignore `AIR_JOINED_STOP_LIMIT`
(lu en `1495-1497`). Au défaut (2) c'est exact ; si le réglage descend à 1 ou 0, la réserve
surcharge tous les plans air de stations qui ne seront jamais posées.

### 08.7 — `result.error` est périmé sur les chemins `HUB` et `HUBB`        [gravité : P3]
`builder_air.nut:1587-1592` et `1612-1617` — la branche de réutilisation n'exécute **aucune**
commande : `IsAirportTile` et `GetAirportType` sont des lectures. Si le hub attendu a disparu,
`airportA`/`airportB` reste `null` et le code appelle pourtant `AIError.GetLastError()`
(`1604`, `1630`), qui rend l'erreur d'une commande antérieure sans rapport.
· Conséquence observable : `result.error` est faux pour `reason = "HUB"`/`"HUBB"`, et les
consommateurs qui branchent dessus (`task_air.nut:436` teste précisément
`ERR_STATION_TOO_MANY_STATIONS_IN_TOWN`) peuvent attribuer un 771 à un échec de hub. Pollue le
comptage même si `_markAirFailedSites` filtre par `reason` (`task_air.nut:10-15`).

### 08.8 — Les 22 % sont écrits en dur trois fois alors que `TOWN_CATCHMENT_SHARE_PCT` est utilisé dans le même fichier        [gravité : P3]
`builder_air.nut:1045` (`((popA + popB) * 22) / 100`), `1233-1234`, `1290-1291` — le chemin vivant
(`air_demand_plan` = **0**, `info.nut:2021-2024`) fixe bien la demande captée à 22 % de la
population, avant construction, sur les trois bras. La même part existe en constante nommée
(`candidates.nut:1342`, `const TOWN_CATCHMENT_SHARE_PCT = 22`) et est employée dix lignes plus
haut dans ce fichier, par le chemin `AIR_DEMAND_PLAN` (`255-256`).
· Conséquence observable : trois littéraux qui doivent rester synchrones avec une constante
qu'ils pourraient référencer (Squirrel l'autorise dans une expression, contrairement à `const x
= y`). Le fait — demande figée à 22 % avant chantier — est confirmé ; c'est la duplication qui
est signalée ici, pas la valeur.

### 08.9 — Le captage marginal d'un arrêt joint n'exclut que sa tuile, pas son rayon        [gravité : P3]
`builder_air.nut:1454-1463` — le commentaire annonce « un arret dans la couverture deja assuree
par l'emprise aeroport ne rapporte aucune demande marginale », et le test rejette le candidat si
`dx + dy <= airportCoverage`. Mais la valeur retenue ensuite est
`AITile.GetCargoProduction(tile, paxCargo, 1, 1, coverage)` (`1465`), c'est-à-dire la production
de tout le disque de rayon `coverage` autour de l'arrêt — dont une partie peut rester dans la
couverture de l'aéroport. La déduplication **entre arrêts** utilise pourtant le bon critère
(`2 * coverage`, `1505`).
· Conséquence observable : `summary.monthlyPax` (`1521`) surestime la demande marginale, et cette
surestimation remonte telle quelle dans `OpexAirReconcileActualBuild` (`717-718`) donc dans le
ROI réconcilié de la ligne.

### 08.10 — Mélange d'unités dans la réconciliation post-chantier        [gravité : P3]
`builder_air.nut:716-718` — `monthlyPax = baseMonthly + joinedMonthly` additionne `plan.monthlyPax`
(22 % d'une **population**, `1045`) et `result.joinedMonthlyPax` (somme de
`AITile.GetCargoProduction`, `1465`/`1521`). Sous `AIR_DEMAND_PLAN` la base change encore de
nature (`GetLastMonthProduction`, `251-256`) sans que le terme joint ne change.
· Conséquence observable : le `monthlyPax` réconcilié n'a pas d'unité homogène ; il alimente
`OpexAirEconomics` (`722`) donc le profit et le ROI post-chantier, c'est-à-dire la grandeur qui
sert de vérité pour les registres. Aucun effet au défaut si `air_joined_stops` ne pose rien, mais
il est à 1 et pose jusqu'à 2 arrêts par aéroport neuf.

### 08.11 — Scories : deux globales déclarées jamais lues, un champ de sonde mort, une variable masquée, une disjonction morte        [gravité : P3]
`builder_air.nut:12` (`AIR_HUB_TOWN_POOL`) et `:15` (`AIR_TOWN_MIN_DISTANCE`) — une seule
occurrence chacune dans tout `ai/OpexAI/` : leur propre déclaration. La distance minimale
réellement appliquée est calculée en `982` (`(plane.speed >= 400) ? 32 : 30`).
· `builder_air.nut:508` — `probes.townsLeft--` : le champ est initialisé (`984`, `1091`) et
décrémenté, jamais lu. (`builder_water.nut:180-182` lit le sien : le motif a été copié sans
l'allocation par ville qui le justifiait.)
· `builder_air.nut:948` — `local limit` calculé puis systématiquement masqué par le `local limit`
de `981`, à l'intérieur de la boucle sur les combos.
· `builder_air.nut:610` — `used >= allowance || probes.left > 0` : la première branche est
inatteignable, ce cas ayant déjà provoqué un `return null` en `561-564`.
· Conséquence observable : aucune en exécution ; signalé pour ne pas être rediagnostiqué.

## Vérifié, n'est PAS un bug

- **G7 est fermé dans ce fichier.** `OpexAirRollback:1394-1406` **n'ignore pas A** : la ligne
  `1405` retire `airportA` après `airportB` (commentaire G7§1, `1401-1403`). Et **B est protégé**
  à *chacun* des six sites d'appel, qui passent tous `reuseA ? null : airportA` et
  `reuseB ? null : airportB` : `1634` (BFAIL/HUBB), `1644` (STNFAIL), `1651` (HANGAR), `1663`
  (PLANE), `1679` (ORDFAIL), `1701` (START). `OpexAirRollback` n'a aucun appelant hors de ce
  fichier (vérifié par grep sur `ai/OpexAI/`). Pour un plan `hubhub`, `reuseA` et `reuseB` valent
  tous deux `true` (`1307`) : l'échec ne démolit **rien**, seuls les avions sont vendus. Aucun
  aéroport existant ne peut être démoli par ce chemin, donc aucune ligne tierce ne peut être
  cassée. L'énoncé du plan (« un échec sur un plan hub-à-hub peut démolir un aéroport existant »)
  ne tient plus au SHA `5b770ac`. Réserve : le cas `START` reste imparfait pour les *véhicules*
  (constat 08.5), pas pour les aéroports.
- **G4 : la boucle de retour existe.** Contrairement à l'énoncé, le captage des arrêts joints
  **revient** dans le modèle (`OpexAirReconcileActualBuild:711-742`, appelée en `1735`, qui refait
  tourner `OpexAirEconomics` avec `monthlyPax` augmenté et fige la flotte au nombre réellement
  livré), et leur **coût est dans le ROI** deux fois plutôt que zéro : réservé avant élection
  (`744-763`) et inclus dans `result.actualCost` puisque le compteur `AIAccounting` ouvert en
  `1553` est arrêté en `1726`, après la pose des arrêts (`1709-1724`). Il n'y a pas de double
  comptage : la réconciliation recalcule `economics` depuis zéro (`722`) avant de substituer le
  coût réel (`727-737`). Le résidu réel est l'asymétrie coût/demande à l'élection (constat 08.6).
- **`airportDelayDays = 3.0` (`185`) et `OpexAirCadenceCap` (`296-339`) sont des approximations
  connues, pas des bugs.** `CLAUDE.md` les nomme explicitement comme le chantier ouvert C61
  (« approximations grossières connues ; la cible est un modèle temporel partagé, pas une
  suppression brute »). Non signalés. Nuance de traçabilité, sans gravité : la chaîne C61
  n'apparaît nulle part dans `ai/OpexAI/*.nut` (0 occurrence) ; le fichier cite C16 pour le
  plafond de cadence (`281-282`, `296-298`) et le délai de 3 jours n'a **aucun** commentaire
  d'origine (`185`). Un relecteur sans `CLAUDE.md` le prendrait pour un nombre magique.
- **`AIR_JOINED_STOPS <- false` (`29`), `AIR_CHEAP_SITE <- true` (`27`), `AIR_SITE_CACHE_ENABLED
  <- true` (`24`) ne sont pas les défauts effectifs** : ce sont des valeurs d'amorçage écrasées
  par `settings.nut:336-340` depuis `info.nut`. Ne pas conclure « drapeau inerte » sur la lecture
  de ce fichier seul. (La triple définition de `AIR_JOINED_STOPS` — ici, `globals_pre.nut:67`,
  `settings.nut:338` — est déjà au programme de l'étape 1.)
- **Le bouclier `AIAccounting` imbriqué d'`OpexAirProbeSite` (`1371-1380`)** est délibéré et
  correctement documenté (`1355-1370`) : il jette le coût *simulé* des sondages `AITestMode`.
  Conforme au piège listé dans `CLAUDE.md`.
- **`OpexAirFootprintEnd` (`376-385`) rend bien `anchor + (w, h)`** et non `(w-1, h-1)` : c'est la
  convention de terrassement de `LevelTiles`, pas la dernière tuile de l'aéroport. Le commentaire
  explique le mode d'échec passé (`ERR_FLAT_LAND_REQUIRED` après une sonde positive). Correct.
- **`OpexAirLineStationId` (`172-177`) et la convention « `stationA`/`stationB` sont des TUILES »**
  (`160-171`) sont cohérentes dans tout le fichier : `245-246`, `317`, `326-329`, `1132-1133`,
  `1271-1274`. Le correctif `air_hub_fix` (défaut 1) est en place ; la branche `AIR_HUB_FIX == 0`
  (`1135-1140`, `1148-1149`, `1155-1158`, `1271-1274`) est le comportement cassé conservé
  volontairement pour rejouabilité, pas du code mort à supprimer.
- **`OpexAirEconomics:652`** force `maxAllowed = 1` sous `MARGINAL_FLEET || FLEET_PORTFOLIO`
  (`fleet_portfolio` = 1 par défaut), ce qui rend `demandCap` inopérant (`653`) : c'est la
  politique « démarrage minimal, croissance par `_resizeAirFleets` après un an de données »
  documentée en `645-650`, pas un plafond oublié.

## Hors périmètre, à relire ailleurs

- **Étape 14 (`task_air.nut`)** — l'unique écrivain de la mémoire de ville pour le 771
  (`task_air.nut:6-16`) est derrière `air_town_limit_memory`, défaut 0. C'est la moitié manquante
  du constat 08.2 : décider si ce drapeau doit devenir le défaut, et vérifier que le filtre par
  `reason` (`PREA`/`AFAIL`/`PREB`/`BFAIL`) couvre bien le chemin réel alors que `air_presite` est
  à 0. Vérifier aussi que `result.error` périmé (constat 08.7) ne fausse pas `task_air.nut:436`.
- **Étape 13 (`task_projects.nut`)** — `task_projects.nut:66-90` construit une clé
  `build_error_air_town_limit_<townTile>` sur le même fait ; à confronter à
  `OpexAirTownLimitAbandonKey` (`builder_air.nut:886-889`), qui indexe aussi sur `site.town.tile`.
  Deux mémoires du même événement, sur des drapeaux différents.
- **Étape 1 (`info.nut`/`settings.nut`/globales)** — le faisceau
  `air_presite=0` + `air_town_limit_memory=0` + `air_abandon_site=0` + `air_cheap_site=1` est
  exactement la combinaison qui laisse le cycle 08.1/08.2 ouvert et sans mémoire. Le volet B
  (audit d'adoption) devrait retrouver le banc qui a adopté `air_cheap_site=1` et vérifier qu'il
  mesurait bien la construction réussie, pas seulement le coût en opcodes.
- **Étape 6 (`projects.nut`)** — `projects.nut:870-876` relit les mêmes clés d'abandon air à la
  sélection ; cohérence à vérifier avec `builder_air.nut:1034-1041` et `1227-1232` (le bras
  `hubsite` ne teste que `site`, jamais `hub`).
- **Étape 15 (`ledgers.nut`)** — `OpexAirDemandCap` et `OpexAirCadenceCap` y sont consommés
  (grep) : si l'un d'eux est appelé en chemin chaud, le coût de sonde relevé pour C63 s'applique.
- **Étape 3 (`catalog.nut`)** — `catalog.costRoadBusStop` (`catalog.nut:684`) fixe l'amplitude du
  biais du constat 08.6 ; sa valeur conditionne la gravité réelle.
