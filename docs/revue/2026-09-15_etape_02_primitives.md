# Étape 02 — Feuilles et primitives

- **SHA revu** : `83dfcf4` (à corriger si la session revoit un autre commit)
- **Modèle / effort prévus** : Sonnet 5 / medium
- **Périmètre** : `budget.nut`, `capital.nut`, `spatial.nut`, `probes.nut`, `lines.nut` — 1 687 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Compteur d'opcodes, trésorerie/emprunt, grille spatiale C46, canal de mesure, identité de ligne.
`OpexAbandonedPairKey` : vérifier la fermeture de G9, ne pas la rouvrir.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 02.1 — Le ledger d'investissement C63 attribue chaque intervalle au mauvais `kind`        [gravité : P1]
`probes.nut:359-422` (`OpexC63NotePass`) calcule `days = now - lastDate` (l'écart depuis le
*précédent* appel), détermine ensuite le `kind` de la passe **courante**, écrase
`C63_INVEST_LEDGER.lastKind <- kind` puis appelle `OpexC63RecordOpportunity(kind, days, ...)`
(ligne 420-422) : l'intervalle écoulé DEPUIS la dernière observation est donc crédité au résultat
de la passe **qui vient de se produire**, jamais à l'état qui a réellement occupé cet intervalle.
Le code prétend mesurer « combien de jours l'IA a passé dans chaque situation » (description du
réglage `c63_invest_probe`, `info.nut:983` : « one leftover-kind per pass with days »). Mais la
même structure, dans `OpexC63EnsureYear` (`probes.nut:339-357`), fait l'inverse au passage d'année
: `tail = nextStart - lastDate - 1` est crédité à `C63_INVEST_LEDGER.lastKind` (**l'ancien** kind,
ligne 352) — la convention correcte, cohérente avec le fait que `lastKind` décrit l'état établi à
`lastDate` et qui perdure jusqu'à la prochaine observation. `OpexC63NotePass` ne suit pas cette
même convention : elle décale d'une passe l'attribution de chaque intervalle. Conséquence
observable : à chaque transition (ex. `absent` → `launched`), les jours passés réellement `absent`
sont comptés sous `launched`, et inversement. Comme le rappelle `docs/revue_code_2026-09-15_plan.md`
(étape 13), ce ledger alimente directement le diagnostic actuellement prioritaire (C63/C58,
investissement et réinvestissement) : ses totaux `_n`/`_d` par `kind` (flushés par
`OpexC63FlushLedger`, `probes.nut:460-498`) sont donc systématiquement biaisés tant que cette
incohérence n'est pas corrigée. `c63_invest_probe` est à 0 par défaut (`info.nut:982-986`), donc
sans impact sur un banc au défaut — mais actif dès que la sonde est armée pour le chantier en
cours.

### 02.2 — La jointure de gare rail (`OpexJoinCompatible`) refuse systématiquement toute ligne rail réelle        [gravité : P2]
`lines.nut:223` (`OpexJoinCompatible`) et `lines.nut:254` (repli identique dans
`OpexFindStationJoin`) rejettent tout conflit dont la ligne porte une clé `"mode"` :
`if (("mode" in line) || !("platformA" in line) || !("platformB" in line)) return false;`. Le
commentaire (`lines.nut:215-219`) explique que ce test doit exclure les lignes non-rail (air/eau/
route, qui portent `mode`) et ne garder que les lignes rail (historiquement sans `mode`). Or toute
ligne rail réellement construite porte désormais `mode = "rail"` explicitement —
`task_rail.nut:1014` (`this._lines.append({... mode = "rail", ... platformA = ..., platformB =
...})`) et le candidat correspondant en amont, `candidates.nut:813`. `_tooClose`, dans le même
fichier (`lines.nut:381,406`), a bien été mis à jour pour ce nouveau fait (`if (("mode" in line)
&& line.mode != "rail") continue;` — teste la *valeur*, pas la seule présence), mais
`OpexJoinCompatible`/`OpexFindStationJoin` n'ont pas suivi : `"mode" in line` est vrai pour
**toute** ligne rail construite, donc `OpexJoinCompatible` rend toujours `false` face à une vraie
ligne rail et la branche de succès de `OpexFindStationJoin` (retour `{candidateEnd=...}`,
ligne 249-251) est inatteignable pour un conflit rail-rail ; `refuse` reste bloqué à `"N"` (« aucune
ligne rail avec un plan de quai ») même quand le conflit EST une ligne rail avec quai. En aval,
`candidates.nut:1301-1307` (`OpexOriginJoinable`) appelle la même fonction pour décider si une
origine déjà desservie peut être « récupérée » par jointure au lieu d'être rejetée — la
récupération ne peut donc jamais réussir. Conséquence : les réglages `station_join` et
`join_place` (`info.nut:1709-1749`, tous deux à 0 par défaut) sont, s'ils sont activés pour un
banc, garantis à 0 jointure réussie quel que soit le terrain — un futur test de ces drapeaux
mesurerait un échec à 100 % qui n'a rien à voir avec le mérite de l'idée.

### 02.3 — `_tryRepayLoan` n'a pas la garde `interval <= 0` de son symétrique `OpexTryReborrow`        [gravité : P3]
`capital.nut:99-136` (`OpexAI::_tryRepayLoan`) lit `interval = AICompany.GetLoanInterval()`
(ligne 118) puis divise dessus sans contrôle : `((minNewLoan + interval - 1) / interval) *
interval` (ligne 121). `OpexTryReborrow`, décrit dans le même fichier comme le pendant symétrique
de cette fonction (commentaire ligne 97 : « Le reemprunt a la demande ... est le pendant »),
contrôle explicitement `if (interval <= 0) return money;` (ligne 70) avant la même division. Si
`GetLoanInterval()` peut valoir 0 dans une configuration de jeu donnée (NewGRF, difficulté),
`_tryRepayLoan` fait une division entière par zéro — en Squirrel une exception d'exécution, non
rattrapée ici. Risque faible en pratique (le palier d'emprunt est presque toujours positif) mais
le coût de la garde est nul et son absence casse la symétrie que le code lui-même revendique.

## Vérifié, n'est PAS un bug

- **`budget.nut` — le piège `GetOpsTillSuspend` annoncé par le plan n'est pas présent dans ce
  périmètre.** `OpexOpsMeasureBegin/End` (`budget.nut:19-31`) et `OpexBudget.begin/end`
  (`budget.nut:49-70`) appliquent tous deux la formule correcte pour un bloc qui traverse un
  nombre `elapsed` de ticks : `mark.left + (elapsed-1)*OPS_PER_TICK + (OPS_PER_TICK-left)`,
  jamais une simple soustraction de deux restes quand `elapsed > 0`. Seul site du périmètre à
  appeler `AIController.GetOpsTillSuspend()` ; aucun autre fichier de l'étape ne le fait.
- **`budget.nut:38-42,51` — le compteur `nested` n'est pas de l'instrumentation morte.** La classe
  documente elle-même la non-réentrance de `begin()/end()` comme non vérifiée avant l'ajout de ce
  compteur (S0 septies, `docs/taches.md`) ; `nested` est bien lu et publié ailleurs
  (`task_projects.nut:893`, `scheduler_tasks.nut:297`, hors périmètre), donc l'imbrication, si elle
  se produit, n'est pas silencieuse. La limitation elle-même (coût du bloc interne perdu pour la
  catégorie externe en cas d'imbrication réelle) reste un gap connu et déjà tracé, pas une
  découverte de cette étape.
- **`lines.nut:268-305` (`OpexAbandonedPairKey`) — le correctif G9§1 du 09-06 tient à la lecture
  actuelle.** Le repli `"t" + dstTown` (ligne 297-299, fret vers une ville dont
  `AIIndustry.GetIndustryID` rend -1) est maintenant symétrique côté source
  (`"t" + srcTown`, ligne 300-302) : un fret ville→industrie ou industrie→ville ne retombe plus sur
  la collision `freight|cargo|id|-1` que G9 décrivait. Le préfixe `"t"` empêche toute collision
  avec un identifiant d'industrie numérique réel, et `kind`/`cargo` restent en tête de clé, donc
  aucune collision entre `pax` et `freight` n'est possible. Rien à rouvrir.
- **`probes.nut:42-54` (`OpexDecide`) — l'absence de garde interne est le contrat documenté, pas un
  oubli.** `ai/OpexAI/CLAUDE.md` : « gardé par `decision_log` ou une sonde dédiée ». Sondage des
  sites d'appel hors périmètre (`task_projects.nut`, `task_road.nut`, `task_air.nut`,
  `task_town.nut`, `candidates.nut`) : tous gardent l'appel par `DECISION_LOG` ou par le drapeau de
  sonde dédié de la fonction englobante (ex. `projects.nut:61-102`,
  `OpexLogPortfolioRankWithTension`, gardée par `!DECISION_LOG && !TENSION_PROBE`). Aucun site
  d'appel non gardé trouvé.
- **`spatial.nut` — les deux grilles (`OpexSpatialGrid`, `OpexDirectedSpatialGrid`) sont
  géométriquement correctes.** Vérification à la main : pour une taille de cellule `S`, si
  `|dx|+|dy| <= S` alors nécessairement `|dx| <= S` et `|dy| <= S`, et pour tout axe, deux tuiles à
  distance `<= S` ont des indices de cellule différant d'au plus 1 (si `|cx1-cx2| >= 2`, la
  distance minimale entre les deux cellules est `S+1 > S`) — donc aucun faux négatif, exactement
  la garantie annoncée en tête de fichier. L'empaquetage de clé `(cx<<16)|(cy&0xFFFF)` dans
  `OpexDirectedSpatialGrid` ne déborde pas : `cx,cy < 2048` sur la plus grande carte OpenTTD.

## Hors périmètre, à relire ailleurs

- **Étape 4/5 (`candidates.nut`)** : `candidates.nut:1301-1307` (`OpexOriginJoinable`) et ses trois
  sites d'appel (`:1569`, `:1573`, `:1687`, `:1691`, `:1776`, `:1781`) héritent du constat 02.2 —
  toute logique de génération de candidats qui suppose qu'une origine servie peut être « récupérée »
  par jointure (le long commentaire historique `candidates.nut:1240-1275` sur la régression du
  2026-08-28/29) repose sur une fonction actuellement inopérante dès que `station_join`/`join_place`
  est actif.
- **Étape 13 (`task_projects.nut`, `task_rail.nut`)** : `task_projects.nut:5` est le seul site
  d'appel de `OpexC63NotePass` (constat 02.1) — vérifier si un correctif d'attribution y a une
  contrepartie à ajuster (ex. lecture des totaux flushés). `task_rail.nut:202`
  (`OpexFindStationJoin`) est le seul site d'appel côté construction rail pour le constat 02.2.
- **Étape 11 (`scheduler_tasks.nut`)** : `scheduler_tasks.nut:510-516` lit
  `CASH_RESERVE_PROBE_CALLS/MIN_BINDS/MAX_BINDS` (définis et incrémentés dans `capital.nut:26-32`)
  en delta annuel — confirme que la sonde n'est pas morte, mais ne compte pas les cas où
  `RESERVE_MAINT_CAP` (`capital.nut:37-40`) écrase ensuite `reserve` ; à vérifier si cette étape
  veut élargir la sonde le jour où `reserve_maint_cap` est banqué pour de bon (défaut 0 aujourd'hui).
- **Étape 10 (`lib_water.nut`)** : `lib_water.nut:193` documente déjà, dans du code hors périmètre,
  le même piège `GetOpsTillSuspend` que le plan annonce pour cette étape — cohérent avec ce qui est
  vérifié ici en 02, rien à réconcilier.
