# Revue de Code — EB-10 (Garde Sentinelle 65535 et Acceptation Express Fictive)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `eb10_guards` (min=0, max=1, défaut 0, 4 niveaux à 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `EB10_GUARDS <- false;`.
  - `ai/OpexAI/info.nut` : déclaration `AddSetting({ name = "eb10_guards", ... })`.
  - `ai/OpexAI/settings.nut` : lecture unique `EB10_GUARDS = AIController.GetSetting("eb10_guards") == 1;`.
  - `ai/OpexAI/lines.nut` & `ai/OpexAI/bus_districts_overrides.nut` : garde sentinelle `65535` / invalidité industrie pour préfixer la ville `"t" + dstTown` dans `OpexAbandonedPairKey`.
  - `ai/OpexAI/catalog.nut` & `ai/OpexAI/po01c_generators.nut` : filtrage conditionnel `acceptance >= 8` sur fret express urbain si le réglage est actif.
  - `ai/OpexAI/persist.nut` : filtre de chargement purgeant les clés d'abandon polluées par `|65535`.
  - `sweeps/test_eb10_guards.py` : test de contrat unitaire hôte validant la présence, les bornes, les gardes et l'hygiène.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_road100_bus_districts.py`, `sweeps/test_v251_inventory.py` : maintenance des empreintes SHA et projections de compatibilité.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Risques

1. **Innocuité au défaut 0 :**
   - À `eb10_guards = 0`, `EB10_GUARDS` est `false`.
   - Les conditions de sentinelle `lines.nut` et `bus_districts_overrides.nut` sont court-circuitées (`if (EB10_GUARDS ...)`). Le chemin d'exécution résiduel `if (dst < 0 ...)` s'exécute à l'identique de l'état historique au bit près.
   - Dans `catalog.nut` et `po01c_generators.nut`, la clause ternaire sélectionne l'expression historique `(acceptance >= 8 || (pop >= 300 && AICargo.HasCargoClass(cargo, AICargo.CC_EXPRESS)))`.
   - Dans `persist.nut`, aucune clé n'est ignorée à la restauration.
2. **Hygiène Squirrel :**
   - Aucune métaméthode implicite, aucun identifiant réservé.
   - Aucun usage de `.find(` (interdit sur les tableaux et proscrit dans les nouveaux modules).
   - Aucun impact sur le rail (`builder_rail.nut`, `task_v2*` strictement intacts).
3. **Vérification des Suites de Tests :**
   - `test_eb10_guards.py` : 6/6 tests passants.
   - `test_road1y*.py` : 74/74 passants.
   - `test_road100*.py` : 236/236 passants (3 sautés attendus).
   - `test_v251*.py` : 7/7 passants.
   - `git diff --check` : aucun avertissement de syntaxe ou whitespace.

---

## 3. Conclusion

Le code est rigoureusement conforme au contrat, inoffensif au défaut 0, et prêt pour qualification sur banc Docker ultérieure.
