# Revue de Code — OPCODES/IDLE-1 (Valorisation du Reliquat de Tick / Slack Worker)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `idle1_slack_worker` (min=0, max=1, défaut 0, 4 difficultés à 0, flags 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `IDLE1_SLACK_WORKER <- 0;`, `IDLE1_SLACK_RESERVE <- 2500;`, `IDLE1_TOWN_CURSOR <- 0;`.
  - `ai/OpexAI/info.nut` : déclaration du réglage public avec description et bornes.
  - `ai/OpexAI/settings.nut` : lecture unique `IDLE1_SLACK_WORKER = AIController.GetSetting("idle1_slack_worker") == 1 ? 1 : 0;`.
  - `ai/OpexAI/scheduler.nut` : implémentation de `OpexAI::_idle1SlackStep()` avec garde stricte de réserve (`IDLE1_SLACK_RESERVE + 500`) et progression progressive d'arrière-plan.
  - `ai/OpexAI/main.nut` & `ai/OpexAI/probes.nut` : insertion symétrique rigoureuse de `if (IDLE1_SLACK_WORKER) this._idle1SlackStep();` juste avant `AIController.Sleep(1)` dans les deux boucles principales.
  - `sweeps/test_idle1_contract.py` : test de contrat unitaire hôte vérifiant déclaration, symétrie des boucles, garde de réserve et absence de mots réservés.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_v251_inventory.py` : mise à jour des empreintes SHA et projections de configuration.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Invariants

1. **Innocuité au défaut 0 :**
   - À `idle1_slack_worker = 0`, `IDLE1_SLACK_WORKER` vaut 0.
   - Les appels dans `main.nut` et `probes.nut` sont court-circuités au test du booléen sans aucun calcul.
   - Le chemin par défaut et les temps de tick sont inchangés au microsecond près.
2. **Garde anti-dépassement de tick (Leçon C67.6) :**
   - La constante `IDLE1_SLACK_RESERVE = 2500` assure une marge incompressible de 25% du quota de tick avant de céder la main à `Sleep(1)`.
   - Si `GetOpsTillSuspend()` est inférieur à 3000 opcodes, la fonction retourne immédiatement sans consommer d'opcodes d'API.
3. **Symétrie obligatoire `main.nut` / `probes.nut` :**
   - La règle Squirrel §2 ("Sous probes, OpexAI::Start tourne dans _mainLoopProfiled... tout appel ajouté à la boucle va dans les deux") est respectée à la ligne près.
4. **Hygiène Squirrel & Non-rail :**
   - Aucun tableau `.find(`, aucune closure.
   - Aucun fichier rail touché.

---

## 3. Conclusion

Le code est rigoureusement conforme à la spécification `OPCODES_IDLE1.md`, inoffensif au défaut 0, et validé par les 328 tests hôte.
