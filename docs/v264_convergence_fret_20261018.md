# V264 — Convergence de fret vers une industrie déjà desservie

Réglage `v264_convergent_freight`, défaut 0 aux quatre niveaux. À 0, aucune
décision nouvelle : le drapeau est lu une fois au démarrage, et tout le reste
est derrière ce drapeau. Le défaut n'est pas adopté. Aucun banc n'a été lancé.

Le diagnostic V226 (branche `v226`, `docs/v226_reseau_araignee_20261018.md`
§4.1) demandait que plusieurs sources livrent la même industrie sur la gare
déjà posée, au lieu d'une gare d'arrivée par ligne. V194 avait gardé ces
paires sans quai joint : `_tooClose` les rejetait toutes par
`too_close_no_join`.

## 1. Comment ce chantier évite la perte de V207+V212+V214

En partie complète, V207+V212+V214 ont perdu −904,1 k£/an à 10 ans (0/20,
valeur −19,5 %) alors que le rail seul passait. L'ablation a montré que
V207+V212 prenaient la caisse de l'aérien : mêmes villes, même capital
(V149). V214 seul était dans le bruit.

V264 ne rejoue pas ce mécanisme.

- Fret industrie seulement. `OpexPaxCandidates` (`candidates.nut:964`) n'est
  pas touché. La boucle des puits urbains (`candidates.nut:1205`) non plus.
  Pas de courrier, pas de part de captage, pas de classement de sites, pas
  de poids A*, pas de coût de virage.
- Le score et `OpexLineEconomics` ne changent pas. Le capital compte toujours
  deux quais (`economy.nut:337`, `2 * platformLength * catalog.costStation`).
  La construction réelle n'en paie qu'un, joint à la gare existante. Le
  portefeuille voit donc une ligne au moins aussi chère que l'estimation
  historique, jamais une ligne bradée.
- La garde de caisse reste `candidate.capital + OpexCashReserve()`
  (`task_rail.nut:285`), avec `CASH_RESERVE_MIN` 5 000 £ et
  `CASH_RESERVE_MAX` 25 000 £ (`main.nut:42-43`).
- `originServed = true` (`candidates.nut:1116`) dit à la tension qu'une seule
  origine est consommée (`tension.nut:253-256`). C'est l'usage du sol : la
  gare d'usine existe déjà. Ce n'est pas un bonus de profit. Risque résiduel :
  cette détente peut remonter la ligne dans le classement et, en partie
  complète, prendre de la caisse à l'aérien. Si un banc complet le montre,
  le défaut reste 0.

Le seuil de caisse de 150 000 £ proposé en V226 §4.1, et la porte « à partir
de l'année 3 » copiée sur V217, sont retirés. Ni l'un ni l'autre n'est un
mécanisme d'OpenTTD 15.3. Une ligne qui ne paie pas le capital estimé plus
la réserve n'est pas construite, comme aujourd'hui.

## 2. Les deux causes de V194, et ce que V264 en fait

1. Géométrie. V194 gardait une destination à moins de `MIN_SEPARATION`
   (`main.nut:74`, 10 tuiles) d'une gare à nous, sans quai à joindre.
   `_tooClose` (`task_rail.nut:271`, corps dans `lines.nut:314`) rejetait
   `too_close_no_join` (`task_rail.nut:278`). Le joint parallèle
   (`OpexJoinPlatformPlans`, `builder_rail.nut:399`) ne couvre que le même
   axe, la même longueur, à au plus `JOIN_PARALLEL_MAX_SIDE` = 4 tuiles de
   côté (`builder_rail.nut:29`, 4 × 2 × 2 = 16 sondes). Un quai en T échoue,
   et l'échec retombait sur une seconde gare libre.
2. Économie. Une ligne courte autonome paie locomotive, dépôt et quai neuf
   pour un petit revenu. V194 l'exemptait du plancher de distance V182.

V264 ne rouvre pas V182. Le filtre de `OpexMakeCandidate`
(`candidates.nut:644`) est inchangé. Une paire trop courte pour le plancher
courant (défaut 0) reste refusée. Il n'y a pas d'exemption de distance.

La paire n'est gardée que si la source est neuve, la destination est une
industrie déjà servie par exactement une de nos gares rail, cette gare
accepte le cargo, et le quai connu de la ligne est encore là. À la
construction, on tente d'abord le parallèle existant. S'il échoue, on
cherche un quai de la même longueur dont l'union avec la gare tient dans
`station.station_spread`. S'il n'y en a pas, `strictOriginReuseJoin` refuse
le site (`SITEAB` ou `SITEA`/`SITEB`) : pas de seconde gare à l'usine.

`joinLineId` n'est pas posé. V178 le pose et `_tooClose` saute alors toute
la ligne, y compris le contrôle de la source. V264 n'exempte que l'extrémité
B (`lines.nut:324-325`, continues `338` et `362`). L'extrémité A reste
soumise à `ORIGIN_SEPARATION` (`main.nut:83`, 3 tuiles) et à
`MIN_SEPARATION`. Le saut `stationId == joinStationId` reste réservé à V178
(`lines.nut:357`).

Si V179 est aussi actif, son chemin (`v179Keep`) ne reçoit pas la marque
convergente (`candidates.nut:1168-1171`). V178 rattache plus tard, comme
aujourd'hui.

## 3. Points d'insertion

| Rôle | Endroit |
|---|---|
| Réglage, défaut 0 | `info.nut:682-689` (`easy`/`medium`/`hard`/`custom` = 0) |
| Globale | `globals_pre.nut:22` |
| Lecture unique | `settings.nut:103` |
| Service de la destination | `OpexOriginService`, `candidates.nut:931` |
| Garde de génération | `OpexFreightCandidates`, `candidates.nut:1171-1184`, seulement dans l'exclusion déjà en place |
| Fonctions | `OpexV264ConvergentService` `candidates.nut:1062`, `OpexV264EmitConvergent` `candidates.nut:1096` |
| Précheck | `_tooClose`, `lines.nut:324` |
| Parallèle, non modifié | `OpexJoinPlatformPlans`, `builder_rail.nut:399-441` |
| Repli dans la boîte | `OpexV264SpreadJoinPlans`, `builder_rail.nut:630` |
| Branchement | `OpexRailPlatformPlans`, `builder_rail.nut:732-735` et `761-773` |
| Pose | `planB.stationId` passé à `BuildRailStation`, `builder_rail.nut:3391` et `3395` |
| Journal | `V264_KEEP` (`candidates.nut:1119`), `V264_JOIN` (`builder_rail.nut:769`), tous deux sous `DECISION_LOG` |

`OpexJoinPlatformPlans` n'est pas modifié. `task_rail.nut` non plus : le
candidat porte déjà `joinPlatform`, donc le bloc V178
(`task_rail.nut:267`) ne le rattache pas une seconde fois. Aucun état
nouveau dans `persist.nut`.

## 4. Données utilisées

Toutes déjà disponibles, et lues seulement si le réglage est à 1.

- Service rail de la tuile d'industrie : `OpexOriginService` (ligne, extrémité,
  `stationId`, `blocked` si deux gares distinctes).
- Géométrie du quai que nous avons posé : `line.platformA` / `platformB`
  (`anchor`, `direction`, `step`, `length`).
- Acceptation : `AICargoList_StationAccepting`.
- Proximité de la source : tuile d'industrie contre `line.stationA` /
  `line.stationB`, seuil `MIN_SEPARATION` déjà utilisé par `_tooClose`.
  Pas de second rayon.
- Tuiles train de la gare : `AITileList_StationType(..., STATION_TRAIN)`.
- `AIGameSettings.GetValue("station.distant_join_stations")`. Sans lui,
  `CmdBuildRailStation` refuse la jointure distante
  (`station_cmd.cpp:1469`). Défaut vrai (`game_settings.ini:136-138`).
- `AIGameSettings.GetValue("station.station_spread")`. L'union du rectangle
  train existant et du quai neuf doit avoir largeur et hauteur ≤ spread
  (`station_cmd.cpp:1204`, `CanExpandRailStation`). Le morceau neuf aussi
  (`station_cmd.cpp:1471`). Défaut 12, minimum 4, maximum 64
  (`game_settings.ini:108-112`). Un spread inférieur à 4 est refusé. On ne
  substitue pas 12.
- Axe : `RAILTRACK_NW_SE` → Y, `RAILTRACK_NE_SW` → X (`script_rail.cpp:162`).
  Le décalage perpendiculaire du parallèle est celui déjà codé : NE_SW en
  (0, 1), sinon (1, 0) (`builder_rail.nut:403-404`).

Pas de filtre `isTransformer`. `catalog.nut:965` exige à la fois un cargo
produit et un cargo accepté. Une centrale produit `CT_INVALID` et accepte
`CT_COAL` (`table/build_industry.h:1161-1165`) : elle n'est pas
transformatrice, et c'est pourtant le cas mesuré de plusieurs mines vers
une centrale. La boucle industrie n'apparie déjà que producteur et
accepteur du même cargo. Les villes restent dehors.

Une seule longueur : `platform.length`, celle que le train lira via
`candidate.platformLength` une fois le plan retenu (`builder_rail.nut:3666`
pose `planB.length`). Un quai plus court désaccorderait le train. S'il ne
tient pas dans la boîte, la liste est vide.

## 5. Coût en opcodes

À 0 :

- Les paires dont les deux extrémités sont libres ne voient pas le drapeau.
  La condition d'exclusion est la même qu'avant (`candidates.nut:1171`).
- Les paires déjà exclues font une lecture du drapeau, faux, puis
  `pairsOriginServed` comme avant. Pas d'appel API.
- `_tooClose` calcule `shareEndB` par une lecture du drapeau, puis les deux
  `continue` historiques de V178. Pas de distance nouvelle.
- Le repli spread et le journal ne sont atteints que si un candidat porte
  déjà `joinEnd == "B"` et `convergent_dest`. Rien ne les pose à 0.

À 1, seulement pour une source neuve vers une industrie déjà servie :

- Génération : validité de gare, liste d'acceptation, distances de Manhattan
  vers nos gares rail (`MIN_SEPARATION`), puis `OpexMakeCandidate` — le même
  calcul que pour une paire libre. Pas de balayage de boîte à la génération.
- Construction, après les 16 sondes parallèles, et seulement si elles
  échouent : anneaux de Tchebychev du rectangle train, du rayon 1 à
  `JOIN_PARALLEL_MAX_SIDE`, puis jusqu'au spread si moins de
  `MAX_STATION_PLANS` plans (`builder_rail.nut:23`, 12). Chaque ancre
  retenue est plate et constructible, puis `BuildRailStation` sous
  `AITestMode`. On s'arrête à 12 plans. Cela remplace, pour cette extrémité,
  la recherche libre de rayon `STATION_SEARCH_RADIUS` = 30
  (`builder_rail.nut:22`), que le mode strict ne fait de toute façon pas.

Le « ~60 % d'opcodes d'A* » du tableau V226 §5 est le chiffre de la
proposition 2 (embranchement). Il n'est pas mesuré et n'est pas utilisé.
Les 80 tuiles de cette même proposition ne le sont pas non plus : V264 ne
prolonge pas une voie et n'ajoute pas de seuil de distance.

## 6. Risques

- La boîte est pleine ou le quai existant est plus long que le spread :
  échec de site, pas de ligne. C'est le comportement voulu.
- La source est à moins de `MIN_SEPARATION` d'une gare à nous : la paire
  reste comptée `origin_served` et n'est pas chiffrée.
- `blocked` (deux gares distinctes sur l'industrie) : pas de jointure.
- La tension à une origine peut classer la ligne plus haut. Voir §1.
- Le capital estimé est plus haut que la dépense réelle (deux quais
  comptés, un quai payé). On sous-construit plutôt qu'on ne brade.
- Aucune persistance nouvelle. Les clés du candidat sont transitoires.

## 7. Banc proposé, non lancé

Même arbre, bras `OpexAI[v264_convergent_freight=0]` et
`OpexAI[v264_convergent_freight=1]`, les autres réglages aux défauts.

1. Exposition, `decision_log=1` : smoke causal 1 graine × 1 an (deux duels).
   On attend `V264_KEEP` à la génération et `V264_JOIN` (`mode=parallel` ou
   `mode=spread`) à la construction, et moins de `too_close_no_join` sur
   une seconde source vers la même industrie. Santé seulement, pas de
   verdict économique.
2. Porte A `gain_short`, 40 × 3 ans, une répétition, `profit_year`,
   Wilcoxon p < 0,05, borne basse de l'IC95 bootstrap > 0, delta moyen
   ≥ 4 % du profit de référence, garde de valeur −5 %. D'abord en rail
   seul, puis en partie complète : le rail seul ne suffit pas, vu
   V207+V212+V214. La porte B `non_erosion` 20 × 10 n'est lancée que si A
   est complète, saine et `pass`. Le défaut ne bouge qu'après les deux
   portes, dans les deux contextes.
