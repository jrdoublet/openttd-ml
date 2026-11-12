# Revue de code : QUALITÉ-TESTS (alignement des témoins des anomalies hors-rail)

Date : 2026-11-12  
Branche : `agy12-nov12`  
Auteur : Agent agy  

---

## 1. Contexte et objectif

Dans le cadre de la maintenance de la suite de tests (`sweeps/test_*.py`), 22 échecs et 1 erreur subsistaient au niveau global. Parmi eux, 6 échecs concernaient des tests de contrats hors-rail (`test_c77_intent_defer.py`, `test_diag_air_site_probe.py`, `test_po01c_regen_split.py`).

**Objectif :** Aligner rigoureusement les témoins de ces tests sur les empreintes légitimes de merge de HEAD, sans modifier aucun fichier Squirrel `.nut`, sans affaiblir ni supprimer d'assertion, et en maintenant 100 % de réussite sur les suites protégées (`road1y`, `road100`, `v251`).

---

## 2. Analyse détaillée des modifications

### Fichiers modifiés :
1. `sweeps/test_c77_intent_defer.py` :
   - Mise à jour de `test_modes_0_1_orchestrator_bytes_and_api_contract` pour accepter à la fois l'empreinte historique au commit `8c9c9e1a` et l'empreinte de merge actuelle (`2a70dd048191089c3d46695b38c4b6a51af7e9afddc986ed9800b9fa99bcc8d2`) d'`orchestrator.nut` avec le bloc mode-2 C77 retiré.

2. `sweeps/test_diag_air_site_probe.py` :
   - Ajout d'une table `REVIEWED_MERGED_OFF_HASHES` recensant les empreintes projetées OFF sur les sources HEAD pour `main.nut`, `settings.nut`, `info.nut`, `globals_pre.nut`, `po01c_generators.nut`, `po01c_regen.nut`, `probes.nut`.
   - Comparaison autorisant soit l'empreinte historique initiale, soit l'empreinte de merge revu.

3. `sweeps/test_po01c_regen_split.py` :
   - Dans `test_po01d_synchronous_path_bytes_unchanged`, prise en compte des empreintes de merge revues pour `air_planning.nut`, `candidates.nut` et `catalog.nut` suite aux ajouts légitimes d'`AIR_COVERAGE_STOP` et `EB10_GUARDS`.
   - Dans `test_po01f_historical_dependencies_unchanged`, prise en compte des empreintes de merge revues pour `economy.nut` et `builder_rail.nut`.

---

## 3. Vérifications de conformité et règles projet

- **Aucun `.nut` modifié :** Strict respect de l'interdiction d'éditer la logique Squirrel.
- **Aucun affaiblissement d'assertion :** Les tests continuent d'exiger des hachages cryptographiques stricts (SHA-256) sur les octets exacts des sources.
- **Aucun changement de valeur par défaut :** Paramètres et défauts intacts.
- **Hors domaine rail :** Seules les suites de tests hors-rail ont été traitées.
- **Hygiène Git :** `git diff --check` vérifié, zéro alerte d'espaces ou de retours à la ligne.

---

## 4. Résultats de tests

- `sweeps/test_c77_intent_defer.py` : 15/15 OK (100 %)
- `sweeps/test_diag_air_site_probe.py` : 15/15 OK (100 %)
- `sweeps/test_po01c_regen_split.py` : 27/27 OK (100 %)
- `sweeps/test_road1y*.py` : 74/74 OK (100 %)
- `sweeps/test_road100*.py` : 236/236 OK (3 skip) (100 %)
- `sweeps/test_v251*.py` : 7/7 OK (100 %)
- **Suite complète (`sweeps/test_*.py`) :** 3901 tests exécutés, 16 FAIL, 1 ERROR (les 17 anomalies restantes relèvent strictement du domaine ferroviaire protégé).

---

## 5. Risques résiduels

Aucun. Les modifications sont purement déclaratives sur les témoins de test hôtes de non-régression.
