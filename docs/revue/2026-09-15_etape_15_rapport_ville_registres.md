# Étape 15 — Rapport annuel, ville, eau et registres

- **SHA revu** : `7304613`
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `ai/OpexAI/task_report.nut`, `task_town.nut`, `task_water.nut`, `ledgers.nut` — 1 740 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

C56 : arrêt silencieux de toute activité après 1970, cause non élucidée — se manifeste dans le
cycle annuel. Coût des 26 registres au défaut (une sonde en chemin chaud déplace la trajectoire).

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 15.1 — C56 : aucun mécanisme d'arrêt silencieux trouvé dans le cycle annuel du périmètre        [gravité : P3]
Recherche menée à la main dans les quatre fichiers : aucune boucle `while` (grep confirme zéro
occurrence dans `task_report.nut`, `task_town.nut`, `task_water.nut`, `ledgers.nut`), aucun
`try`/`catch` nulle part dans tout `ai/OpexAI` (donc une exception non gérée dans ce périmètre
resterait visible comme erreur NoAI — elle ne peut pas expliquer un arrêt « sans erreur »), et
toutes les boucles `for` de `task_report.nut` sont bornées par `this._lines.len()` (`task_report.nut:24`,
`349`, `593`) sans recalcul du budget d'opcodes en cours de route (pas de tranche/reprise comme
`builder_rail.nut`, mais pas non plus de boucle infinie constatée). Aucune corruption d'état qui
gèlerait une tâche future n'a été identifiée dans ce sous-ensemble. Je le dis explicitement plutôt
que de forcer un diagnostic : **ce périmètre ne fournit pas de mécanisme concluant pour C56**. Le
candidat le plus solide reste celui déjà trouvé à l'étape 10 (`MinchinWeb.Lakes` gèle 3/20 graines,
mode eau) — cohérent avec « se manifeste dans le cycle annuel » puisque c'est `task_water.nut` +
`_reportLines`/`_scrapDeadLines` qui rescannent l'état eau chaque année, mais la cause elle-même est
ailleurs (`builder_water.nut`/`lib_water.nut`, hors de ce périmètre).

### 15.2 — `scrapStartYear` jamais réinitialisé : un ferraillage relancé peut être déclaré « bloqué » dès sa première passe        [gravité : P2]
`task_report.nut:431-432` — `if (!("scrapStartYear" in line)) line.scrapStartYear <- year;` puis
`local stuck = (year - line.scrapStartYear) >= SCRAP_TIMEOUT_YEARS;` (`SCRAP_TIMEOUT_YEARS = 2`,
`main.nut:99`, une `const`, jamais un réglage). Le champ n'est posé qu'une seule fois dans tout le
dépôt (vérifié par recherche globale) et n'est **jamais retiré ni réécrit** — ni par le
sauvetage feeder (`task_report.nut:357-387`, qui remet `scrapping=false` et `scrapVehicles=[]`
mais ne touche pas `scrapStartYear`), ni par `_triggerScrapLine` (`task_report.nut:312-343`,
qui remet `scrapping=true` et `deadStreak` mais pas non plus `scrapStartYear`) quand il redémarre
un ferraillage sur la même ligne. Conséquence observable : une ligne de rabattement (feeder)
ferraillée une première fois, sauvée par le chemin `infrastructureValid` parce que sa gare/dépôt a
été retrouvé valide, puis redevenue `deadStreak >= DEAD_STREAK_THRESHOLD` des années plus tard,
repart en ferraillage avec l'**ancien** `scrapStartYear` de la première tentative. Si plus de
`SCRAP_TIMEOUT_YEARS` années réelles se sont écoulées depuis (cas courant sur une partie de 10-20
ans), `stuck` est vrai dès le premier passage de `_scrapDeadLines` sur cette seconde tentative :
la ligne est retirée de `_lines` immédiatement (`task_report.nut:444`, `DL|...|4`) et ses véhicules
encore en service sont abandonnés en l'état, sans avoir eu les deux ans de grâce que le
mécanisme est censé garantir. C'est exactement le mode de défaillance que la sortie de secours du
commentaire de `task_report.nut:420-430` cherche à éviter, déclenché plus tôt que prévu par un
champ qui survit à un cycle complet sauvetage→re-ferraillage.

### 15.3 — `company_value` toujours à 0 dans le rapport C50 : champ jamais alimenté depuis sa création        [gravité : P2]
`ledgers.nut:335,338` — `local val = 0;` puis
`OpexC50ChronologyLog("... company_value=" + val + ...)`. Vérifié par `git log -S"local val = 0"` :
ce champ est codé en dur à 0 **depuis le commit qui a introduit `_logC50AnnualReport`**
(`4ccdff6`, avant le déplacement pur C65), jamais un régression récente. Aucun appel à
`AICompany.GetCompanyValue` n'existe nulle part dans `ai/OpexAI` (recherche globale) : la métrique
que CLAUDE.md désigne comme la mesure qui compte (`company_value`, comparée à AAAHogEx) n'est donc
jamais lue par l'IA elle-même, y compris dans la sonde censée en tracer la chronologie. Coût nul
au défaut (`C50_CHRONOLOGY_PROBE` = 0, `info.nut:972-977`) mais quiconque active la sonde pour lire
une trajectoire de `company_value` dans les logs `phase=treasury_annual` lira une constante
trompeuse, jamais la vraie valeur.

### 15.4 — `task_water.nut` : code mort après le chemin de succès de `_tryBuildWaterProject`        [gravité : P3]
`task_water.nut:43-77` — la fonction retourne déjà (`return { outcome = "rejected", ... }`) dès que
`!result.ok` (ligne 43-49). Le `if (result.ok) { ... }` qui suit (ligne 50) est donc toujours vrai
à ce point et se termine lui-même par un `return { outcome = "built", ... }` (ligne 75) : la ligne
77 (`return { outcome = "rejected", discards = passDiscards };`) après la fermeture du bloc est
inatteignable. Sans conséquence fonctionnelle (aucun chemin ne l'emprunte), mais un futur ajout de
branche entre les lignes 50 et 77 pourrait silencieusement tomber sur ce retour mort plutôt que sur
le comportement voulu.

## Vérifié, n'est PAS un bug

### Coût des 26 registres C39→C60 au défaut (`ledgers.nut`)
Vérifié à la main, pas seulement par grep : chaque registre a été tracé jusqu'à son site d'appel
réel.
- Les fonctions d'écriture appelées sur un chemin réellement chaud (par tentative de projet, par
  tranche A*) sont gardées **au point d'appel**, pas seulement dans la fonction de publication :
  `_recordC48AttemptLedger`/`_recordC48PassLedger` sous `if (C48_PROJECT_ATTEMPT_LEDGER)`
  (`task_projects.nut:563,567,423-425,438-441,736-741,914-915,925-926`),
  `_recordC49ScarcityPass` sous `if (C49_SCARCITY_LEDGER)` (mêmes sites), `_recordC41RailSliceLedger`
  et `_recordC39PassClockLedger` sous leurs drapeaux respectifs dans `scheduler.nut:63,80` — et
  l'enveloppe elle-même, `_runNextTaskWithSlackLedger` (`scheduler.nut:7-13`), retombe sur l'appel
  nu `_runNextTask()` dès qu'aucun des six drapeaux C41/C39 n'est actif : zéro table allouée, zéro
  incrément, sur le chemin le plus chaud de tout le scheduler.
- Les 26 réglages (`c39_pass_clock_ledger`, `c41_slack_ledger`, `c41_monthly_busy_ledger`,
  `c41_opportunity_ledger`, `c41_admission_ledger`, `c41_rail_slice_ledger`,
  `c48_project_attempt_ledger`, `c48_incremental_profile`, `c49_scarcity_ledger`,
  `c50_chronology_probe`, `c52_autoreplace_log`, `c52_event_exposure_probe`,
  `c54_vehicle_orders_probe`, `c55_origin_relax_probe`, `c55_pax_trace_probe`,
  `c60_town_rating_probe`, etc., `info.nut:219-990`) sont **tous à 0/off par défaut** sur les
  quatre valeurs (`easy/medium/hard/custom`) — vérifié un par un, pas supposé.
- Les cinq fonctions de publication annuelle appelées sans garde au point d'appel
  (`_logC41SlackLedger`, `_logC41OpportunityLedger`, `_logC41AdmissionLedger`,
  `_logC41RailSliceLedger`, `_logC39PassClockLedger`, `scheduler_tasks.nut:538-542`) se gardent
  chacune en tête de fonction (`ledgers.nut:16,85,95,122,155`) et ne s'exécutent qu'une fois par an
  (tâche `report`) : le coût au défaut est un test booléen par registre, une fois par an — sans
  commune mesure avec une sonde en chemin chaud comme C63 (`c63_invest_probe`, déjà établi
  ailleurs, −37,6 % smoke ON/OFF, coût explicitement documenté en commentaire
  `info.nut:979-980` : « Compteurs mémoire en boucle chaude »). L'inconsistance de style (garde au
  point d'appel pour les uns, garde interne seule pour les autres) est réelle mais n'a aucun effet
  mesurable ici : **dans ce périmètre, aucun des 26 registres ne paie de coût caché au défaut.**

### `_tryTownGrowth` ne retourne jamais `true` (confirmation croisée)
`task_town.nut:53-219` — confirmé à la lecture complète : aucun `return true` dans toute la
fonction, seuls des `return;` implicites (`continue`/retours anticipés) et un `break;` final
(`task_town.nut:217`) qui laisse tomber en fin de fonction sans instruction `return`. Ce constat
appartient à l'étape 11 (`town_growth_skip_noop`, `scheduler_tasks.nut:682`) — je ne le reprends
pas à mon compte, je confirme seulement que la cause côté `task_town.nut` est bien l'absence totale
de `return true`, pas un chemin de retour conditionnel oublié.

## Hors périmètre, à relire ailleurs

- Le seul site de récursion de l'ordonnanceur, `_dispatchTownGrowth` → `_runNextTask()` récursif
  quand `town_growth_skip_noop` est actif et que `_tryTownGrowth` (constat ci-dessus) ne retourne
  jamais `true` — déjà identifié et à traiter à l'**étape 11** (`scheduler_tasks.nut:678-693`,
  `main.nut`, `scheduler.nut`). Vérifié que `town_growth_skip_noop` vaut 0 par défaut
  (`info.nut:1907-1912`, `globals_post.nut:272`) : cette récursion n'est donc pas active sous
  configuration par défaut et ne peut pas à elle seule expliquer C56 en configuration standard —
  mais elle reste à corriger pour tout banc qui active ce drapeau.
- La cause racine de C56 la plus probable (`MinchinWeb.Lakes` gèle 3/20 graines, budget
  `WATER_LAKES_OPS`) est dans `builder_water.nut`/`lib_water.nut`, couverts par l'**étape 10** — pas
  redécouverte ici, seulement confirmée compatible avec « se manifeste dans le cycle annuel »
  puisque c'est ce périmètre (`task_water.nut`, `_reportLines`/`_scrapDeadLines`) qui rescanne
  l'état eau chaque année sans lui-même contenir la cause.
- Le contrat nom-de-tâche à trois endroits et les 28 méthodes `OpexAI::` sans prototype
  (`main.nut`, `scheduler.nut`, `scheduler_tasks.nut`) : étape 11.
- `Save`/`Load`/`_reconcileAfterLoad` face aux champs persistés (dont `_lastReportYear`,
  `_c48AttemptLedger` et consorts) : étape 11 (`persist.nut`).
