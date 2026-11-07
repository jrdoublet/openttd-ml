# Spécification Technique — OPCODES / IDLE-1 / AIList (Valorisation des Tours Libres et Optimisation AIList)

## 1. Objectif et critère de succès chiffré

- **Constat d'instrumentation :** Le poste `sleep_slack` (opcodes résiduels non consommés dans le tick avant l'appel à `AIController.Sleep(1)`) représente **24% à 50% du quota total d'opcodes** alloué par le moteur NoAI (10 000 opcodes par tick). Ces opcodes sont purement abandonnés.
- **Problématique des instanciations `AIList` :** De nombreux modules recréent des objets `AIList()` temporaires à chaque itération ou scan de catalogue, induisant une surcharge en allocation C++ et garbage collection Squirrel sans valeur ajoutée.
- **Objectif :**
  1. Identifier et exploiter utilement le reliquat de tick (`slack`) pour des tâches d'arrière-plan interrompables disposant d'un consommateur aval avéré (ex. repérage progressif de sites ou indexation PO-02).
  2. Éliminer les allocations d'`AIList` éphémères dans les boucles de filtrage critique en privilégiant des tables/tableaux Squirrel réutilisés.
- **Critère de succès chiffré :**
  - **Opcodes :** Réduction mesurée de $\ge 15\%$ des opcodes sur les scans de vivier ou gain d'avancement d'arrière-plan sans dépassement de tick.
  - **Neutralité économique (Règle opcodes du 24/09) :** Pas de perte mesurable au banc 20 graines $\times$ 10 ans apparié (IC95 Student du $\Delta\text{profit\_year}$ non entièrement négatif, pas de défaite significative au test des signes, garde de valeur $\ge 0{,}95$).

---

## 2. État du code vérifié dans le worktree

- **`ai/OpexAI/main.nut:885-894` :**
  ```squirrel
  if (C67_SLACK_HOOK) {
    local spC67 = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.c67") : null;
    this._c67SlackHook();
    if (spC67 != null) OpexSpanEnd(spC67);
  }
  if (V309_IDLE_PROBE) OpexV309IdleTick(this);
  local spSleep = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.sleep") : null;
  AIController.Sleep(1);
  if (spSleep != null) OpexSpanEnd(spSleep);
  ```
- **`ai/OpexAI/probes.nut:3208-3220` :**
  - Copie instrumentée obligatoire `_mainLoopProfiled` : les appels ajoutés à la boucle principale doivent impérativement être répercutés ici pour éviter toute divergence d'exécution sous sonde.
  - Ligne 3215 : `OpexLoopProfAddRaw("sleep_left", AIController.GetOpsTillSuspend(), 0);`
- **`ai/OpexAI/task_terrain.nut:147-154` :**
  ```squirrel
  function OpexAI::_c67SlackHook()
  {
    /* Controle AVANT tout travail : sous le seuil, le crochet ne doit rien consommer, sinon il
     * peut franchir le tick et decaler le Sleep(1) (divergence observee en C67.6). */
    if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return;
    if (C67_TERRAIN_MAP) this._c67TerrainSlackStep();
    if (C67_WATER_EXPOSURE) this._c67WaterExposureStep();
  }
  ```
- **`ai/OpexAI/probes.nut:3067-3069` :**
  - `state.sleepOps += AIController.GetOpsTillSuspend();` (Mesure exacte du reliquat abandonné au `Sleep(1)`).

---

## 3. Conception proposée

### Principe de l'ordonnanceur de fond IDLE-1
- **Réglage :** `idle1_slack_worker` dans `info.nut` (défaut 0, 4 niveaux à 0).
- **Garde stricte de frontière de tick :**
  - Conserver une marge de sécurité `IDLE1_SLACK_RESERVE = 2500` opcodes.
  - Ne lancer une tranche de tâche de fond que si `AIController.GetOpsTillSuspend() >= IDLE1_SLACK_RESERVE + trancheMinOps`.
  - Si le reliquat passe sous `IDLE1_SLACK_RESERVE`, céder immédiatement la main sans exécuter d'autre instruction.

### Consommateur métier impératif
Contrairement à C67 qui remplissait une carte sans client, IDLE-1 doit alimenter un consommateur validé :
- Pré-scan par tranches des aéroports candidats pour PO-02 / C78.
- Indexation incrémentale des industries productrices pour le catalogue fret sans figer la boucle principale.

### Optimisation des allocations `AIList`
- Remplacer les motifs :
  ```squirrel
  local list = AIList();
  list.AddList(sourceList);
  list.Valuate(...);
  list.KeepValue(...);
  ```
  par un filtrage Squirrel itératif direct sur tableau ou table préallouée lorsque la taille est modeste ($< 50$ éléments), évitant l'instanciation de l'objet natif C++ OpenTTD.

### Interaction avec Save / Load
- Les générateurs d'arrière-plan doivent être réinitialisables sans corruption d'état : aucun état de tranche de fond n'est persisté ; au `Load`, le worker d'arrière-plan repart simplement de la position zéro ou reconstruit son index.

---

## 4. Pièges connus et historique

- **Piège de divergence causale C67.6 (`task_terrain.nut:149-150`) :** Si le travail dans le slack consomme un opcode de trop et que le moteur NoAI suspend la coroutine Squirrel avant l'appel à `Sleep(1)`, le script saute un tick et désynchronise toute la trajectoire de jeu. La réserve doit être absolue et vérifiée par `GetOpsTillSuspend()`.
- **Faux diagnostic V309 (`docs/journaux/journal_2026-10-30_transfert_taches.md:475-479`) :** L'ancien diagnostic V309 prétendait que 7 409 tours étaient en attente avec caisse suffisante. L'autopsie du 25/10 a démontré que le calcul ignorait la réserve obligatoire de trésorerie (5 à 25 k£) : seuls 12 tours étaient réellement finançables ! Ne jamais présumer de l'oisiveté sans confronter la caisse à la réserve financière réelle.
- **Règle Squirrel des deux boucles :** Tout appel inséré dans `main.nut::_mainLoop` DOIT être inséré à l'identique dans `probes.nut::_mainLoopProfiled` sous peine de rompre le contrat d'instrumentation.

---

## 5. Plan de test

1. **Test unitaire de non-régression et de contrat (`sweeps/test_idle1_contract.py`) :**
   - Vérifier la présence symétrique des hooks dans `main.nut` et `probes.nut`.
   - Vérifier qu'à `idle1_slack_worker=0`, le comportement et le coût sont strictement inchangés.
   - Vérifier le respect du plafond `IDLE1_SLACK_RESERVE`.
2. **Smoke test causale 1 graine $\times$ 1 an :**
   - Comparaison appariée des ticks d'arrivée : le nombre de ticks écoulés doit être strictement identique entre référence et variante si aucune décision de construction n'a été altérée.
3. **Qualification d'adoption (Règle d'optimisation d'opcodes du 24/09) :**
   - Porte unique : 20 graines $\times$ 10 ans apparié complet et sain.
   - Critère : absence de perte ($\text{IC95}$ Student du $\Delta\text{profit\_year}$ non entièrement négatif, $p \ge 0{,}05$ ou majorité de victoires aux signes, garde de valeur $\ge 0{,}95$).

---

## 6. Estimation de difficulté et d'effet attendu

- **Difficulté :** **Moyenne** (2.5/5). Le mécanisme de tranche de slack est déjà éprouvé par C67 (`_c67SlackHook`), mais le couplage avec un vrai consommateur utile et l'étanchéité des ticks demandent de la rigueur.
- **Effet attendu :** Récupération utile de **$15$ à $30\text{ M opcodes/an}$** sur le budget global sans allonger le temps réel d'exécution de la partie.
- **Source des données :** Audit `sleep_slack` (`docs/brief_idle1_20261024.md`, `probes.nut:3067`), autopsie V309 du 25/10 (`docs/journaux/journal_2026-10-30_transfert_taches.md:475`).
