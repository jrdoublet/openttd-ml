# Étape 16 — Transversale — conformité NoAI et robustesse

- **SHA revu** : `421f14d`
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : Tout le périmètre, revue dirigée par grep
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Checklist `docs/00_conseils.md`, jamais testée : 90° interdits, `max_trains = 0`, absence
d'interrupteurs modaux, identifiants NewGRF supposés, gares orphelines, empreinte RAM.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 16.1 — `pf.forbid_90_deg` jamais lu, comportement délégué à une bibliothèque non auditable        [gravité : P2]
Grep sur `forbid_90|90_deg|pf\.` dans `ai/OpexAI/*.nut` (34 fichiers) : **zéro occurrence**. Le
rail passe entièrement par la bibliothèque standard NoAI importée en direct —
`ai/OpexAI/main.nut:28` `import("pathfinder.rail", "RailPathFinder", 1)` — dont le source n'est
pas vendorisé dans ce dépôt (contrairement à `lib_water.nut`) : son traitement réel de
`pf.forbid_90_deg` est donc invérifiable depuis ce dépôt. Le code OpexAI qui l'entoure est
correctement borné : `builder_rail.nut:377-410` (`OpexAdvanceRailPathfinder`) impose
`iterationBudget`/`sliceIters`/`deadlineTick` à chaque tranche, donc pas de boucle infinie *côté
appelant* même si la bibliothèque peine à converger. Le raccordement manuel du dépôt
(`builder_rail.nut:1075-1129`, `OpexBuildDepot`) ne présuppose pas non plus la connectivité : il
pose puis vérifie `AIRail.AreTilesConnected(...)` et retente une autre direction sinon (4
offsets), donc un rejet de virage à 90° y serait absorbé sans planter. Conséquence observable :
le risque de crash/boucle infinie décrit par le plan n'est ni confirmé ni réfuté par le code
OpexAI lui-même — il dépend d'un composant tiers importé à l'exécution, jamais banqué avec
`forbid_90_deg=1` (aucune trace de banc à ce sujet dans le périmètre lu). À tester explicitement
avant de clore ce point.

### 16.2 — Aucun contrôle amont de `vehicle.max_trains/max_roadveh/max_aircraft/max_ships` avant chantier        [gravité : P2]
Grep large (`max_trains|max_roadveh|max_aircraft|max_ships|MaxVehicles`) ne touche que
`tension.nut:70-75` (nommage de la clé) et deux consommateurs, tous deux hors du chemin de
décision réel :
- `tension.nut:133-137` : lu uniquement quand `tension_probe` est actif, pour une sonde de
  mesure passive (`OpexTensionContext`), ne bloque rien.
- `ledgers.nut:255-265` (`_recordC49ScarcityPass`) : compare `AIGroup.GetNumVehicles(...) +
  planned > cap` mais n'est appelé (`task_projects.nut:427,442,740,848`) qu'après coup et
  seulement si `C49_SCARCITY_LEDGER` est actif — c'est un journal de diagnostic « pourquoi le
  rang suivant n'a pas été bâti », pas une porte d'entrée à la construction.
Aucune occurrence de ces clés dans `task_projects.nut`, `task_rail.nut`, `task_road.nut`,
`task_air.nut`, `task_water.nut`, `projects.nut`, `candidates.nut` — le chemin réel de sélection
et de construction ne consulte jamais ces plafonds. Conséquence observable si
`max_trains = 0` (ou équivalent) au démarrage : le code génère quand même des candidats rail,
paie de vrais chantiers de voie/gare/dépôt, et échoue seulement à `AIVehicle.BuildVehicle`
(confirmé robuste en rollback, voir 16.V2) — le couple origine/destination est alors marqué
abandonné (`lines.nut:37-44`, `OpexBuildFailureIsAbandonable` traite `VEHICLE` comme abandonnable)
et n'est pas retenté avant le cooldown (`abandon_memory_cooldown_days`, 365 jours par défaut).
Pas de crash observable, mais un gaspillage systématique d'argent et d'opcodes le temps que
chaque paire du vivier soit découverte une à une comme irréalisable, alors qu'un test unique de
`AIGameSettings.GetValue("vehicle.max_trains")` en tête de cycle l'aurait évité pour tout le
mode. Jamais banqué avec un mode à plafond nul au démarrage.

### 16.3 — Pas d'interrupteur natif `enable_rail/road/air/water` — mécanisme réel non gardé, mais cas voisin (liste d'engins vide) correctement géré        [gravité : P3]
OpenTTD n'expose pas de réglage `enable_rail`/`enable_road`/`enable_air`/`enable_water` distinct :
le seul levier de partie qui désactive un mode est le plafond de véhicules (`vehicle.max_*`,
couvert en 16.2). Le cas voisin réellement présent dans l'API — un mode sans aucun engin
constructible (NewGRF qui ne fournit aucun matériel roulant rail) — est lui géré proprement :
`catalog.nut:326-330` renvoie tôt (`this.platformLength < 1 || ... || this.railCoverage < 1`)
et `catalog.nut:344-349` renvoie aussi tôt si `chosen < 0` (aucun type de rail disponible),
laissant `wagonByCargo`/`railLocos` vides (`catalog.nut:318-319`). `candidates.nut:59`
(`hasRail = catalog.wagonByCargo != null && (cargo in catalog.wagonByCargo)`) fait qu'aucun
candidat rail n'est jamais généré dans ce cas — pas de tentative, pas de gaspillage. Reclassé en
P3 : le risque concret est celui de 16.2, pas une absence d'interrupteur qui n'existe pas.

### 16.4 — Empreinte RAM de la VM Squirrel : confirmée jamais mesurée        [gravité : P3]
Grep `memoire|memory|ram\b|footprint|heap` sur les 34 fichiers : tous les hits sont soit
`OpexAirFootprint*` (nivellement de terrain aéroport, sans rapport), soit `ABANDON_MEMORY` /
`AIR_TOWN_LIMIT_MEMORY` (mémoire de décision applicative, pas mémoire VM), soit une structure de
tas Fibonacci (`lib_water.nut`, algorithmique, pas une mesure). Aucune ligne ne lit ni ne
journalise une consommation mémoire de la VM elle-même — confirmé conforme à l'affirmation du
plan. Note : l'API NoAI n'expose de toute façon aucun accesseur de taille de tas Squirrel, donc
cette mesure ne peut se faire qu'en externe (outil de banc), pas depuis le script.

## Vérifié, n'est PAS un bug

### 16.V1 — Cargos et type de rail résolus dynamiquement, aucun ID en dur
`catalog.nut:333-348` choisit le type de rail via `AIRailTypeList()` + `AIRail.IsRailTypeAvailable`
(le plus grand ID disponible, trié explicitement pour ne pas dépendre de l'ordre d'itération) ;
`catalog.nut:740-751` (`_refreshCargos`) résout pax/mail via `AICargoList()` +
`AICargo.HasCargoClass`. Aucun littéral numérique de cargo ou de rail type trouvé ailleurs dans
les 34 fichiers.

### 16.V2 — Rollback systématique après échec à mi-chantier (rail/route/air/eau)
Quatre fonctions de rollback dédiées, chacune démolissant dans l'ordre inverse de la pose et
vendant les véhicules encore en dépôt avant de démolir la gare/le dépôt : `OpexRollback`
(`builder_rail.nut:1138-1161`), `OpexRoadRollback` (`builder_road.nut:854-869`),
`OpexAirRollback` (`builder_air.nut:1394-1405`), `OpexWaterRollback` (`builder_water.nut:663-668`).
Appelées systématiquement à chaque point d'échec observé dans `builder_road.nut:1107-1349` et
l'équivalent air/eau/rail. Contredit l'hypothèse du plan sur les gares orphelines pour les
chemins vérifiés ; limite de cette vérification : uniquement des points d'échec représentatifs
ont été relus, pas l'exhaustivité des branches (voir Hors périmètre).

### 16.V3 — Liste d'engins vide gérée sans crash (voir 16.3)
Voir 16.3 : retour anticipé propre dans `catalog.nut` + garde `cargo in catalog.wagonByCargo`
dans `candidates.nut:59`.

### 16.V4 — Un seul `Valuate` à fonction Squirrel personnalisée, confirmé en code tiers vendorisé
`grep -n "\.Valuate("` sur les 34 fichiers : toutes les occurrences utilisent une fonction d'API
native (`AIBridge.GetMaxSpeed`, `AIEngine.*`, `AIVehicle.GetRunningCost`,
`AIRail.IsRailTypeAvailable`, `AIStation.GetNearestTown`, `AITile.GetDistanceManhattanToTile`)
sauf une : `lib_water.nut:306` (`BList.Valuate(_MinchinWeb_Extras_.MinDistance, this._A)`).
`lib_water.nut:1-37` confirme qu'il s'agit d'un extrait adapté de MinchinWeb's MetaLibrary
(code tiers vendorisé, licence permissive, déjà traité à l'étape 10) — pas une deuxième occurrence
à traiter ici.

### 16.V5 — `pathfinder_sleep_ticks` respecte bien la philosophie « armes égales » par défaut
`info.nut:2735-2742` : défaut 0 = « no self-handicap (equal terms vs other AIs) », justifié par
une lecture directe du code source d'AAAHogEx (`ai/AAAHogEx-115/pathfinder.nut:202-216`,
`road.nut:914-919`, cité en commentaire) confirmant qu'il ne dort jamais entre ses tranches de
recherche. Décision explicitement gelée (« NE PAS ROUVRIR », 2026-08-29).

## Hors périmètre, à relire ailleurs

- **`loop_budget` (`info.nut:2259-2285`)** : défaut `0` conserve *une tâche puis `Sleep(1)`* par
  tick — exactement le patron d'auto-handicap que le commentaire du même réglage qualifie
  d'interdit par la philosophie « armes égales » (comparer avec `pathfinder_sleep_ticks`, 16.V5,
  qui lui défaut bien à « pas de handicap »). Le mode `1` (« plays like AAAHogEx ») n'est pas le
  défaut. Aucune mention « adopté au banc » sur ce réglage (contrairement à d'autres, ex.
  `air_cheap_site`), et son voisin `marginal_fleet` (`info.nut:2229-2245`) est explicitement noté
  « non mesuré au banc, défaut choisi par prudence » — donc probablement le même statut
  (expérience non encore tranchée) plutôt qu'un oubli. À confirmer contre `docs/taches.md` par un
  humain avant de qualifier ceci de non-conformité.
- **Recherche rail segmentée/reprenable à travers une sauvegarde** (`builder_rail.nut`,
  `rail_search_resumable`, `persist.nut::_reconcileAfterLoad`) : la robustesse du rollback (16.V2)
  n'a été vérifiée que sur les échecs en cours de tick, pas sur une interruption
  sauvegarde/rechargement en plein chantier segmenté — relève d'une étape dédiée à
  `persist.nut`/`scheduler.nut`, pas de celle-ci.
- **Plafonds air/route grossiers (`OpexAirCadenceCap`, `OpexRoadPhysicalVehicleCap`, C61)** :
  déjà documentés comme chantier connu dans `ai/OpexAI/CLAUDE.md` — pas relitigés ici.
- **Mode eau incomplet** : `builder_water.nut`/`lib_water.nut` sont un chantier explicitement non
  fini par ailleurs (voir `docs/taches.md`, hors lecture de cette étape) ; les rollbacks d'eau ont
  été vérifiés existants (16.V2) mais pas la complétude fonctionnelle du mode.

## Clôture dynamique M4 — workspace du 2026-09-16

M4 a finalement été exercé sans modifier le comportement de l'IA, via
`sweeps/run_m4_conformity.py` + `diag_m4_conformity.py`. Les deux scénarios utilisent les
defaults courants (`air_early_slot=1`, abandon `1/365`) et activent uniquement les canaux
diagnostiques `decision_log` + `c63_invest_probe`.

### 16.2 — `vehicle.max_trains=0` : défaut réel, mais P2

Le 2×3 `results/review_m4_conformity_2x3.json` est sain 4/4 et expose déjà quatre
`RAIL_BUILD_FAIL reason=NOTRAIN error=513` avec 10 147 £ de dépense rail échouée.

Le 5×6 final `results/review_m4_conformity_5x6.json` est **10/10 sain et complet**. OpexAI termine
les cinq graines avec **0 véhicule rail**, mais choisit 30 projets rail et atteint malgré tout le
chantier : 15 `RAIL_BUILD_FAIL reason=NOTRAIN error=513`, 2 `TRKFAIL`, 2 `ABND`. Le ledger
C63 rail totalise `planned_fail=768632`, `actual_fail=176313`, `n_fail=16`. Les compteurs
physiques finaux donnent aussi **0 station avec facility rail** sur les cinq runs Opex, donc aucun
train ni gare rail ne persiste après rollback. Le harnais ne compte pas séparément les tuiles de
voie et dépôts : leur absence persistante n'est donc pas une preuve dynamique disponible.

Surtout, l'analyse année-grain isole huit périodes où **les seuls échecs rail sont NOTRAIN** et où
`n_fail` est exactement ce nombre : elles cumulent **120 018 £** de coût réel. Exemples : graine
42/1971 = un NOTRAIN et 10 147 £ ; graine 999/1972 = trois NOTRAIN et 24 732 £ ; graine
1234/1973 = un NOTRAIN et 21 669 £.

La causalité historique est donc confirmée : l'IA construit l'infrastructure, puis
`AIVehicle.BuildVehicle` échoue avec le plafond à zéro et le rollback intervient trop tard pour
éviter le coût réel. Ce n'est néanmoins **pas un P1** selon la grille actuelle : aucun crash,
aucune corruption de mesure, rollback sain et horizon complet. C'est un défaut P2
d'admission/politique. Aucun garde `vehicle.max_*` n'est ajouté dans cette passe.

Un contrôle séparé, `results/review_m4_conformity_control_5x6.json`, est lui aussi **10/10 sain**.
Sur les cinq runs Opex, le `max_trains=0` termine descriptivement à 720 197 £/an de
`profit_year` moyen contre 747 876,2 £/an au contrôle (−27 679,2 £/an, −3,70 %) et à
2 182 885,2 £ de `company_value` moyen contre 2 226 222,2 £ (−43 337 £, −1,95 %).
Ce 5×6 n'a aucune autorité d'adoption : il donne seulement l'ordre de grandeur économique du
scénario contraint, la preuve causale de 16.2 restant le coût C63 des échecs `NOTRAIN`.

### 16.1 — `pf.forbid_90_deg=1` : robustesse dynamique

Le même 5×6 est **10/10 sain**, sans erreur NoAI, avec 34 projets rail choisis et les cinq parties
Opex qui construisent encore du rail (1/4/2/2/2 véhicules rail finaux ; C63 `n_ok=11`).
Les échecs observés sont ABND/TRKFAIL/SITEB/STNFAIL, jamais NOTRAIN. Cela ferme l'hypothèse forte
« l'option fait crasher ou bloquer l'IA » sur ce périmètre. Le contrôle séparé n'est pas une
autorité de performance et le banc ne prouve ni la conformité interne de `Pathfinder.Rail`
(bibliothèque non vendorisée), ni une neutralité économique ; aucun changement de pathfinder
n'est justifié.

### 16.3 / 16.4 / 10.5

16.3 reste clos. 16.4 reste une **absence de preuve externe**, pas un bug actif : NoAI n'expose
aucun compteur de heap/RSS. Le banc C46 1024² déjà présent est sain et n'a pas été rejoué, mais
il ne contient aucune mesure mémoire. Les runs M4 finissent eux-mêmes avec zéro véhicule eau :
ils n'exposent donc pas 10.5/Lakes. 2048² et RSS/heap restent backlog de banc externe, sans
promotion en défaut technique courant.

**Décision : M4 est clos comme lot de conformité/diagnostic, sans patch comportemental ni
adoption.** Aucun `.nut` n'ayant changé, aucun smoke supplémentaire n'est requis pour M4 et aucun
20×10 n'est justifié.
