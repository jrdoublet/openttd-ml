# Étape 07 — Constructeur ferroviaire

- **SHA revu** : `5b770ac`
- **Modèle / effort prévus** : Sonnet 5 / xhigh
- **Périmètre** : `ai/OpexAI/builder_rail.nut` — 2 144 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Tranches A* reprenables : fuite d'itérations ou de budget calendaire ?
G6 : `ABND`/`NOPA`/`DEAD` gèle le pipeline ; branche « faible trésorerie » morte.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 07.1 — Le doublement de voie gèle `_railSearch` pour toujours si la caisse ne remonte jamais       [gravité : P1]
`ai/OpexAI/task_rail.nut:1070-1086` (`OpexAI::_consumeRailUpgrade`) — quand `OpexExecuteUpgradeAfterSearch`
(`builder_rail.nut:2004-2098`, garde caisse `builder_rail.nut:2041-2044`) renvoie `reason == "CASH"`,
la fonction fait un simple `return;` **sans jamais remettre `this._railSearch` à `null`** (comparer
avec le `if (C41_RAIL_CASH_RELEASE) { this._railSearch = null; ... }` que la recherche PRIMAIRE
possède à `task_rail.nut:881-885` et `895-899`). `_railSearch` reste donc en `{kind="upgrade",
phase="build"}` indéfiniment tant que `AICompany.GetBankBalance(...) < totalNeeded` (voie + gares +
dépôt + rame, calculé par la même fonction). Ce champ n'est pas persisté (`ai/OpexAI/main.nut:137-138`
ne fait que l'initialiser à `null` au chargement) donc rien d'autre ne le libère en cours de partie.
Conséquence observable : tant que ce blocage dure, **toute** nouvelle recherche rail (candidat neuf
OU expansion) est rejetée — `task_rail.nut:149` (`_tryBuildRailProject`, garde d'entrée
`if (RAIL_SEARCH_RESUMABLE && this._railSearch != null) return rejected`) et `task_rail.nut:308`
(`_expandRailLines`, même garde) — alors que l'amélioration elle-même n'avancera plus jamais tant que
la trésorerie ne remonte pas au-dessus de `totalNeeded` pour CETTE ligne précise. C'est exactement le
mécanisme décrit par « G6 » dans l'enjeu du plan (un plan valide attend un capital qui peut ne jamais
venir, et gèle tout nouveau candidat rail derrière lui) — mais il vit dans le chemin
`OpexUpgradeRailLineToDoubleTrack` / `_consumeRailUpgrade`, pas dans les codes ABND/NOPA/DEAD de la
recherche primaire (ceux-ci sont déjà couverts, voir « Vérifié, n'est PAS un bug » ci-dessous). Le
déclenchement est plausible en pratique : `_startRailUpgradeSearch` n'est lancé qu'après un précheck
caisse suffisant (`task_rail.nut:433-435`), mais la recherche A* reprenable s'étale sur plusieurs
tours de file pendant lesquels la caisse peut redescendre (intérêts d'emprunt, autres dépenses) avant
que la phase `build` ne s'exécute.

### 07.2 — Le franchissement de segment (pont/tunnel) consomme des opcodes hors de toute comptabilité de tranche       [gravité : P2]
`ai/OpexAI/builder_rail.nut:746-803` (`OpexAdvanceSegmentedSearch`, bloc de franchissement) appelle
`OpexLocalStructureChoices` (`builder_rail.nut:532-587`) une fois par coupure de segment. Cette
fonction, quand la voie ne peut pas continuer dans l'axe, sonde jusqu'à 18 longueurs de pont
(`SEGMENTED_BRIDGE_MIN_LEN=3` à `SEGMENTED_BRIDGE_MAX_LEN=20`, ligne 549) plus 1 tunnel
(ligne 569-585), chacune une vraie commande `AIBridge.BuildBridge` / `AITunnel.BuildTunnel` simulée
sous `AITestMode`. Aucun de ces appels n'incrémente `state.iterations` / `sliceSpent`
(`builder_rail.nut:372-376` et `667-669` : « ce compte est le DENOMINATEUR du classement, il doit
etre mesure, pas estime ») et aucun ne revérifie `AIController.GetTick() < deadlineTick` avant de
continuer — la seule vérification a lieu au sommet de la boucle `while` englobante
(`builder_rail.nut:681-684`), donc APRÈS que la sonde a déjà consommé ses opcodes. Conséquence
observable : le compte d'itérations reporté (utilisé pour classer les candidats et pour
`OpexAvailableCapital`/le classement du portefeuille) sous-estime le coût opcode réel d'une ligne qui
traverse un obstacle terrain, d'un montant borné (~19 sondes par franchissement) mais réel. En
pratique la marge `BUILD_TICK_MARGIN=3000` (`task_rail.nut:773`) absorbe largement ce dépassement
côté horloge — aucun gel observable attendu — mais l'invariant de mesure « spent = travail réel »
que le fichier revendique lui-même est rompu à chaque franchissement d'obstacle.

## Vérifié, n'est PAS un bug

- **Réglages de recherche segmentée/reprenable à 1 par défaut** : `rail_search_resumable`
  (`ai/OpexAI/info.nut:1599-1605`), `rail_micro_deadline` (`info.nut:1612-1618`),
  `rail_segmented_search` (`info.nut:1628-1634`) ont bien `easy_value = medium_value = hard_value =
  custom_value = 1`. Conforme à `ai/OpexAI/CLAUDE.md:79-82`.
- **Le gel « ABND/NOPA/DEAD en phase build » décrit littéralement par l'enjeu du plan est déjà
  corrigé pour la recherche PRIMAIRE** : `OpexAI::_consumeRailSearch` (`task_rail.nut:859-906`)
  contourne intégralement le test de caisse pour un plan en échec via
  `planFailed = ... && !candidate.railPlan.ok` (`task_rail.nut:864-869`, commentaire « G3§1 ») —
  ABND/NOPA/DEAD/SITE*/SHORT/NOMATCH/JOINPATH/ECON déclenchent tous `plan.ok = false`
  (`builder_rail.nut:1416`, `1466`, `1469`, `1472-1473`, `1532`), donc aucun n'attend jamais de
  capital. Pour le cas où le plan a RÉUSSI mais la caisse manque, `C41_RAIL_CASH_RELEASE`
  (défaut 1, `globals_pre.nut:205-210`, `info.nut:750-755`, banqué 20×10 le 2026-09-09) libère
  `_railSearch` dès le premier refus de caisse (`task_rail.nut:881-885`, `895-899`), et
  `task_projects.nut:481` remet aussi `_railSearch = null` sans condition dès que l'issue n'est pas
  `"cash"`. Le vrai gel encore ouvert est ailleurs : voir 07.1 (chemin d'amélioration double-voie).
- **La branche « faible trésorerie » de `OpexDynamicHardCap` n'est PAS du code mort**, contrairement
  à ce qu'énonce l'enjeu du plan. Site d'appel unique (`ai/OpexAI/task_rail.nut:236` :
  `OpexDynamicHardCap(this._lines.len(), lowCash)`), avec `lowCash = (money < need)` calculé
  ligne 216-218 à partir du solde bancaire réel. `REBORROW` vaut 0 par défaut
  (`info.nut:1501-1505`, « unmeasured default »), donc rien ne masque `lowCash` par un emprunt
  automatique : elle reflète directement la trésorerie et peut valoir `true` chaque fois qu'un
  nouveau candidat rail est lancé alors que la caisse est courte (le chemin caisse-courte
  `task_rail.nut:226` ne rejette QUE le cas non-reprenable ; en reprenable, `willStartSearch=true`
  laisse passer et appelle `OpexDynamicHardCap(..., true)`). Le commentaire `task_rail.nut:219-223`
  confirme que c'est voulu (« active … la branche isPreplanOrLowCash … pour exploiter les opcodes
  dormants pendant l'attente »).
- **Le chunking `PATH_CHUNK`/`FindPath(50)` en mode classique (non segmenté) dépasse légèrement son
  budget de tranche, mais c'est borné et documenté** : `OpexAdvanceRailPathfinder`
  (`builder_rail.nut:377-410`) vérifie `spent < iterationBudget` / `sliceSpent < sliceIters` /
  `AIController.GetTick() < deadlineTick` AVANT chaque `FindPath(PATH_CHUNK)`, donc un dépassement
  d'au plus 49 itérations (ou la durée d'un seul appel `FindPath(50)`) est possible en fin de
  tranche — comportement assumé par la conception même du chunk (commentaire `builder_rail.nut:28-38`).
  Le mode segmenté (`FindPath(1)`, `builder_rail.nut:699-715`) n'a pas ce problème de granularité.

## Hors périmètre, à relire ailleurs

- Le correctif de 07.1 (ajouter la libération de `_railSearch` sur `reason == "CASH"` côté upgrade)
  se pose dans `ai/OpexAI/task_rail.nut::_consumeRailUpgrade`, pas dans `builder_rail.nut` lui-même
  (qui ne fait que rapporter `reason = "CASH"` correctement depuis `OpexExecuteUpgradeAfterSearch`).
  À traiter par l'étape qui couvre `task_rail.nut`.
- `this._railSearch` n'est pas persisté à la sauvegarde (`ai/OpexAI/main.nut:137-138` ne fait que
  l'initialiser à `null`) : une recherche A* rail en cours (primaire ou upgrade) perd tout son état
  et ses itérations cumulées à un rechargement. Pertinent pour une étape qui couvre `persist.nut`.
