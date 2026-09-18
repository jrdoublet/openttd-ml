# Étape 12 — Événements et fraîcheur

- **SHA revu** : `2c317cc`
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `ai/OpexAI/events.nut`, `event_handlers.nut` — 1 200 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

G2 : `hadAbandons` jamais déclenché ; invalidation qui rafraîchit le catalogue mais pas le
portefeuille dérivé. Trancher `event_vehicle_autoreplaced` (adopté sans banc, ignoré du code ?).

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 12.1 — `EngineAvailable` rafraîchit le catalogue sans condition mais l'invalidation du portefeuille reste optionnelle et à défaut off        [gravité : P2]

`event_handlers.nut:770-808` (`OpexAI::_onEngineAvailable`). Les deux premières lignes du corps
s'exécutent **sans aucune garde de réglage** :
```
770  function OpexAI::_onEngineAvailable(event)
771  {
772
773    this._recomputeEpochBounds = true;
774    if (this._catalog != null) OpexRefreshEpochBounds(this._catalog);
```
`OpexRefreshEpochBounds` (définie `candidates.nut:388`, appliquée sur `this._catalog`) modifie
tout de suite les bornes modales/temporelles du catalogue à chaque `ET_ENGINE_AVAILABLE` — c'est
le rafraîchissement du catalogue annoncé par l'enjeu, et il est inconditionnel, donc actif au
défaut. La suite du corps (lignes 775-806) est, elle, gardée par
`C39_INVALIDATION_PROBE` (sonde de mesure, défaut 0, voir `info.nut:308-312`) et par
`C39_ENGINE_REFRESH` (défaut 0, `info.nut:337-341` : *« C39.2 experimental: rebuild
catalog/portfolio after EngineAvailable; 1 = enabled, 0 = off (default) »*) : c'est ce second bloc
seul qui pose `this._portfolioInvalidated = true` et remet `dueCycle = 0` sur les tâches
`catalog`/`projects` (`event_handlers.nut:796-803`). Au défaut, `C39_ENGINE_REFRESH = 0`, donc ce
second bloc ne s'exécute jamais.

*Conséquence observable* : à la configuration livrée, chaque nouveau moteur disponible modifie
tout de suite les bornes du catalogue utilisées par la génération de candidats, mais ne force
aucune reconstruction du portefeuille dérivé (`this._projects`) dans le même mois — celui-ci
n'est rafraîchi qu'au prochain passage naturel des tâches `catalog`/`projects` sur leur
`dueCycle` habituel (`scheduler.nut`/`scheduler_tasks.nut`, hors périmètre). C'est exactement le
couplage manquant décrit par l'enjeu G2, mais **borné à un seul type d'événement** et **documenté
comme expérimental non adopté** par le commentaire `C39.2` lui-même — ce n'est pas une régression
silencieuse, c'est un flag qui n'a jamais été activé par défaut. À comparer au 12.3 (industrie
et ville, où les deux rafraîchissements sont couplés sous un seul et même flag).

### 12.2 — `_onIndustryClose` peut rafraîchir le catalogue sans jamais invalider le portefeuille, même quand son propre flag est actif        [gravité : P3]

`event_handlers.nut:354-384`. Sous `EVENT_INDUSTRY_CLOSE` (défaut 0, `info.nut:165-171`), le
handler ferrait les lignes touchées (`this._triggerScrapLine`) puis appelle
`this._catalog._refreshIndustries()` (ligne 378-380) — mais ne pose ni
`this._portfolioInvalidated = true`, ni de remise à `dueCycle = 0` des tâches
`catalog`/`projects`, contrairement à `_onIndustryOpen` (ligne 700-734) et `_onTownFounded`
(ligne 735-769) qui, sous le même genre de garde (`EVENT_CATALOG_INVALIDATE`, défaut 1),
déclenchent systématiquement les deux dans le même bloc.

*Conséquence observable* : inerte au défaut livré (le flag qui l'active est lui-même à 0), donc
sans effet sur le comportement mesuré du dépôt tel quel — mais si `event_industry_close` est un
jour activé (c'est un réglage prévu pour l'être, cf. description `info.nut:167` « 1 = actif »),
le catalogue perdrait immédiatement l'industrie fermée alors que le portefeuille continuerait, le
mois courant, à proposer/financer des candidats bâtis sur son ancien état — la même famille de
bug que 12.1, sur un chemin actuellement mort.

### 12.3 — Le compteur `33/33 événements untracked` mesure l'absence de correspondance ligne, pas l'absence de remap véhicule        [gravité : P3 — constat de mesure]

`event_handlers.nut:110-213` (`OpexAI::_onVehicleAutoreplaced`), compteur produit ligne 185-209
dans `C52_AUTOREPLACE_LEDGER` (sonde, `c52_autoreplace_log` défaut 0, `info.nut:219-224`,
persistant en globale `globals_pre.nut:412-413`). Le corps du handler (lignes 116-165) remappe
**sans condition de réglage** — le commentaire d'ouverture (ligne 113-115) le dit explicitement :
« *Toujours remapper les references, les sondes ne controlent que le log* » — `oldVehicle` vers
`newVehicle` dans `line.vehicles`, `line.vehicle`, `line.scrapVehicles`,
`this._vehiclesToScrap`, `this._vehiclesToRetire` et `this._unprofitableStreaks`. `tracked`
(ligne 125, mis à `true` à la première correspondance trouvée dans une de ces structures) reste
`false` si `oldVehicle` n'apparaît dans **aucune** d'elles ; c'est alors `entry.untracked++`
(ligne 192) et le commentaire attenant (lignes 193-197) confirme que la mesure du 16 ans
(2026-09-11, hors périmètre pour la source du chiffre) a rendu les 33 événements réels tous
`untracked` — donc tous classés `mode="unknown"` dans la ventilation `line_rail/road/air/water`
(lignes 205-208, toutes restées à 0). La seule ventilation qui a effectivement fonctionné pour ces
33 événements est celle par **type réel du nouveau véhicule** (`entry.rail/road/air/water/unknown`,
lignes 198-204), lue via `AIVehicle.GetVehicleType(newVehicle)` — indépendante de tout
suivi de ligne.

*Ce que le compteur signifie réellement* : il ne mesure pas si un remplacement automatique a eu
lieu (18 fois plus large : voir `OpexC52EventExposureObserve`,
`events.nut:25`, `entry.vehicle_autoreplaced`, sous `c52_event_exposure_probe`, autre sonde,
défaut 0), mais si le véhicule remplacé était, au moment de l'événement, présent dans une des
cinq structures internes de suivi d'OpexAI. `33/33 = 0 %` signifie que, sur cet échantillon, le
filet de sécurité de remap (utile en cas de réutilisation d'ID) n'a jamais eu de référence
interne à corriger — sans permettre de trancher si c'est parce que ces véhicules n'étaient
tout simplement pas suivis (hors `this._lines`) ou parce que le suivi les avait déjà perdus avant
l'événement. Cette question déborde `events.nut`/`event_handlers.nut` (elle porte sur le
peuplement de `this._lines`, `lines.nut`/`task_rail.nut`/`task_road.nut`/`task_air.nut`, hors
périmètre).

## Vérifié, n'est PAS un bug

### V1 — Les 14 types d'événement sont cohérents dans les trois endroits câblés

Comparaison exhaustive, à la main, des trois listes : le dispatch `_processEvents`
(`events.nut:279-357`, 14 branches `if (eventType == AIEvent.ET_...)` avec `continue`),
les 14 prototypes de classe (`main.nut:377-390`, `function _onXxx(event);`) et les 14
définitions effectives (`event_handlers.nut`, une fonction `OpexAI::_onXxx` par type). Les 14
types (`VEHICLE_CRASHED`, `VEHICLE_WAITING_IN_DEPOT`, `VEHICLE_AUTOREPLACED`,
`VEHICLE_UNPROFITABLE`, `INDUSTRY_CLOSE`, `SUBSIDY_OFFER`, `SUBSIDY_OFFER_EXPIRED`,
`SUBSIDY_AWARDED`, `SUBSIDY_EXPIRED`, `VEHICLE_LOST`, `INDUSTRY_OPEN`, `TOWN_FOUNDED`,
`ENGINE_AVAILABLE`, `STATION_FIRST_VEHICLE`) coïncident exactement entre les trois listes : aucun
type câblé à un endroit et pas à un autre, aucun prototype orphelin, aucun handler jamais appelé.
Le seul écart trouvé est volontaire et documenté : `OpexC52EventExposureObserve`
(`events.nut:5-36`, sonde `c52_event_exposure_probe`, défaut 0) compte en plus 4 types sans
handler (`AIRCRAFT_DEST_TOO_FAR`, `ROAD_RECONSTRUCTION`, `ENGINE_PREVIEW`,
`EXCLUSIVE_TRANSPORT_RIGHTS`) plus un compartiment `other` — l'en-tête du fichier
(`events.nut:1-4`) prévient explicitement que ce comptage d'exposition est volontairement plus
large que le dispatch réel (« RX reste le filet annuel pour toute disparition sans evenement
reconnu »).

### V2 — `event_vehicle_autoreplaced` est un réglage mort, déjà tranché à l'étape 1 — confirmé ici sans le rouvrir

`info.nut:210-216` documente désormais explicitement le réglage comme
« *Deprecated compatibility setting: ET_VEHICLE_AUTOREPLACED always remaps persisted IDs to
prevent VehicleID reuse; value is ignored* ». Lecture de `_onVehicleAutoreplaced`
(`event_handlers.nut:110-213`) confirmée : aucune occurrence de `EVENT_VEHICLE_AUTOREPLACED` dans
tout le corps de la fonction ni ailleurs dans `events.nut`/`event_handlers.nut` — le remap tourne
inconditionnellement (voir 12.3). Conforme au constat 01.4 de l'étape 1 : rien à trancher de plus
ici, le code ignore bel et bien ce réglage, et la seule chose que ce périmètre ajoute est le détail
du mécanisme (12.3) derrière le chiffre « 33/33 » cité par le plan.

### V3 — `_markDirty` est un enregistreur de mesure pur, jamais un déclencheur : ce n'est pas le mécanisme d'invalidation réel

`events.nut:40-142` (`OpexAI::_markDirty`) et `events.nut:146-275` (`_logStalenessRefresh`). Les
champs qu'il met à jour (`this._staleness.catalog[...]`, `.candidates[...]`, `.portfolio`,
`.selection`) ne sont lus nulle part ailleurs dans tout le dépôt sauf par `_logStalenessRefresh`
lui-même, pour construire une ligne de log (`C39_REFRESH`, ligne 183-186) et pour les remettre à
`false`/vider en fin de fenêtre (lignes 256-274) — confirmé par une recherche exhaustive de
`_staleness.portfolio`/`_staleness.selection` dans `ai/OpexAI/`. `_markDirty` lui-même est gardé
par `C39_INVALIDATION_PROBE` (défaut 0, `info.nut:308-312`) et documenté comme tel dans son
propre commentaire (`events.nut:37-39` : « *note une invalidation sans la consommer* »). Le vrai
mécanisme de couplage catalogue/portefeuille passe ailleurs, par `this._portfolioInvalidated` et
la remise à `dueCycle = 0` des tâches `catalog`/`projects`, posés directement dans les handlers
concernés (`event_handlers.nut:416-423, 449-457, 483-491, 723-730, 758-765, 796-803`) — c'est ce
second mécanisme, pas `_markDirty`, qu'il faut lire pour juger d'un vrai couplage manquant (voir
12.1 et 12.2).

## Hors périmètre, à relire ailleurs

### H1 — `hadAbandons` : semble déjà réparé hors périmètre, à confirmer à l'étape 2 / étape 13

`hadAbandons` et `passDiscards` n'apparaissent dans aucune ligne de `ai/OpexAI/events.nut` ni
`ai/OpexAI/event_handlers.nut` (recherche exhaustive, aucune occurrence) — l'enjeu G2 tel que
formulé par le plan porte donc sur des fichiers hors périmètre de cette étape :
`task_projects.nut` (étape 13), `task_road.nut`/`task_air.nut`/`task_feeders.nut` (étape 14),
`lines.nut` (étape 2). À la lecture (autorisée, hors édition) de ces fichiers, le commentaire
`task_projects.nut:855-858` indique que le problème décrit par G2 a déjà été corrigé : « *l'ancien
chemin deduisait hadAbandons de passDiscards, dont le remplissage est garde par DECISION_LOG
(defaut 0). Le drapeau `_hadAbandonsThisPass` est pose directement par `_markPairAbandoned`,
couvrant tous les chemins (air, route, rail bloquant et reprenable)* » — et
`task_projects.nut:859-908` lit désormais `this._hadAbandonsThisPass` (posé par
`_markPairAbandoned`, `lines.nut:307-316`, appelé sans garde `DECISION_LOG` depuis
`task_road.nut`, `task_air.nut`, `task_feeders.nut`, `task_rail.nut`) plutôt que de dériver
`hadAbandons` de `passDiscards`. Le statut « G2 ouvert » du plan paraît donc obsolète pour ce
volet précis ; confirmation formelle (banc, historique git) à faire par l'étape qui possède ces
fichiers, pas ici.

### H2 — Contenu détaillé de `catalog.nut`, `candidates.nut`, `lines.nut`, `task_projects.nut`

Toute lecture ligne à ligne de `OpexRefreshEpochBounds` (`candidates.nut:388`),
`_refreshIndustries`/`_refreshTowns` (`catalog.nut`), `_markPairAbandoned` (`lines.nut:307`) et de
la boucle `_tryBuildProjects` (`task_projects.nut`) reste à faire par les étapes qui couvrent ces
fichiers (2, 3, 13) ; ce rapport ne les cite que pour situer la frontière catalogue/portefeuille
vue depuis `events.nut`/`event_handlers.nut`.

## Passe de clôture — 2026-09-16

- **12.1** : le rafraîchissement moteur sans invalidation du portefeuille reste réel sous
  `C39_ENGINE_REFRESH=0`. L'activer par défaut change les décisions d'investissement dans le mois ;
  c'est une variante comportementale à mesurer, et le code fonctionnel est dans
  `event_handlers.nut`, hors périmètre d'édition de cette passe.
- **12.2** : même verdict pour la fermeture d'industrie. Un refresh catalogue sans reconstruction
  immédiate est confirmé ; l'invalidation supplémentaire doit être évaluée avant adoption.
- **12.3** : aucun correctif de code nécessaire. « untracked » décrit l'absence de suivi interne de
  l'autoreplace, pas une absence de remapping des véhicules.
- **V1/V2/V3** restent fermés tels que documentés. En particulier `events.nut::_markDirty` reste
  un enregistreur de mesure pur ; lui donner un effet fonctionnel mélangerait la sonde C39 et le
  mécanisme réel `_portfolioInvalidated`.

Aucun changement n'a donc été appliqué à `events.nut` : les deux écarts fonctionnels exigent un
banc et se trouvent dans `event_handlers.nut`, tandis que les autres constats sont descriptifs.

## Préparation du chantier AIR post-C68 — 2026-09-18

Le moteur AIR multi-équipements fixe la cible fonctionnelle de 12.1 : `ET_ENGINE_AVAILABLE` ne doit pas porter sa propre logique de choix d’appareil. À terme, l’événement doit seulement rafraîchir le catalogue puis invalider/réévaluer de façon ciblée les opportunités et lignes AIR concernées ; la comparaison `(airportType, plane, fleet)` reste dans `OpexAirBestEquipment`/`OpexAirEconomics`. La même règle vaut pour `ET_ENGINE_PREVIEW` : un prototype ou une exclusivité peut déclencher une évaluation anticipée, mais pas une seconde économie AIR.

Cette passe ne modifie pas encore `event_handlers.nut` : C68 reste la baseline, `air_best_equipment` reste default-off après un 5×6 sain mais non concluant économiquement, et aucun 20×10 n’a été lancé. Le couplage exact invalidation catalogue/portefeuille devra être traité avec le lot upgrade/réévaluation.

## Clôture du contrat événements AIR — 2026-09-18

Le lot lifecycle supersède la préparation ci-dessus. Sous `air_best_equipment=1`,
`ET_ENGINE_AVAILABLE` rafraîchit le catalogue AIR et les bornes, raccorde éventuellement un
`previewCommitment` au vrai `EngineID`, marque uniquement les lignes physiquement concernées dirty,
invalide le portefeuille et remet `catalog`/`projects`/`air_fleet` à échéance immédiate. Le handler
ne contient aucun appel à `OpexAirEconomics`, `OpexAirBestEquipment`,
`OpexAirAssessExistingLine` ou `OpexAirAssessPreviewPlane` : la décision reste dans le lifecycle.

`ET_ENGINE_PREVIEW` reste une pré-évaluation distincte et prudente, nécessaire parce que l’API ne
fournit ni `EngineID`, ni `planeType`, ni portée. Il exige une ligne concrète, un gain/payback
acceptables et le cash `prix + réserve`. Après `AcceptPreview()`, le catalogue est rafraîchi et le
nouvel EngineID est résolu par delta avant/après, puis vérifié par la signature stable
nom/type/capacité/vitesse ; les cas ambigus refusent de deviner. La ligne est alors seulement marquée
dirty. L’engagement ne devient `resolved` qu’après un assessment normal
`OpexAirAssessExistingLine -> OpexAirBestEquipment -> OpexAirEconomics`; si le moteur commun préfère
une autre cible, l’engagement est abandonné explicitement. Il est considéré honoré au premier achat
réel du moteur promis, en `growth` ou `upgrade`.

La clôture finale borne aussi l’état `resolved` : `resolvedDate` n’est fixé qu’à la première
résolution et, passé `AIR_PREVIEW_COMMITMENT_MAX_DAYS` sans achat réel, l’engagement est abandonné
explicitement avec raison `timeout`, puis la ligne redevient dirty pour une assessment normale. Un
preview résolu ne peut donc plus verrouiller indéfiniment une cible.

`ET_VEHICLE_CRASHED` distingue désormais un véhicule encore actif d’un véhicule déjà retiré
logiquement de la ligne. Si l’ID est une clé de `_vehiclesToRetire`, le ticket est supprimé et le
handler retourne avant `OpexFindLineForVehicle` : aucun second décrément de `vehCount/trains` et
aucun `needsRefleet`. Pour un crash AIR actif, la ligne devient dirty avec raison `crash` avant
reconstitution ; le refleet attend une assessment commune valide, respecte `targetFleetSize` et
n’achète rien si le crash a déjà ramené la flotte à la profondeur cible.

`ET_VEHICLE_AUTOREPLACED` remappe maintenant les références lifecycle complètes : listes/scalaires
de ligne, clé éventuelle de `_vehiclesToRetire` **et** chaque `ticket.replacementVehicle`. Si le
remplaçant exact d’un ticket crashe, le ticket est marqué puis remappé sur l’ID construit par le
refleet commun ; le timeout ne peut donc plus conclure à tort que le remplaçant a disparu et restaurer
l’ancien.

Dans `results/diag_air_lifecycle_6y_5seeds.json`, chaque graine expose un preview : **5 vus, 5
acceptés, 5 EngineID résolus sans ambiguïté**. Les cinq sont ensuite abandonnés explicitement parce
que le moteur commun préfère une autre configuration (`previewAbandonCommon=5`) ; **0 timeout** et
0 engagement silencieusement perdu. Un événement `ENGINE_AVAILABLE` est vu par graine et cible au
total **60 lignes**, donnant 60 réévaluations dédiées. Aucun 20×10 n’est justifié par le verdict
économique global négatif ; C68/default reste inchangé.

Le 5×6 qui porte ces compteurs a `air_equipment_regret_probe=1` partagé entre les deux bras : son
`setting_audit` marque `transportable_to_shipped_defaults=false`, tout en confirmant
`air_best_equipment` comme unique différence effective entre bras. Il expose dynamiquement
`engine_available` et `preview`, mais aucun crash ; les autres dirty-causes lifecycle sont couvertes
statiquement plutôt que par cette campagne.

Validation du source final : **55 tests** verts, `py_compile`, les deux selftests historiques et
`git diff --check` verts ; `results/smoke_air_lifecycle_final_1y_seed42.json` est **1/1 sain**
sous OpenTTD 15.3 / OpenGFX 7.1. Le 5×6 reste antérieur à ces derniers correctifs events/preview et
ne constitue pas une preuve dynamique de ces branches rares.
