# Revue de code — Tâche 4 : ALT-COND (`road1y_alt_load_cond`)

**Date :** 8 novembre 2026  
**Auteur :** Antigravity  
**Réglage :** `road1y_alt_load_cond` (0 = inerte / master, 1..100 = seuil de potentiel passagers en attente ou taille de ville à B pour activer le chargement complet au terminus B)  
**Fichiers modifiés :**
- `ai/OpexAI/globals_pre.nut` : déclaration `ROAD1Y_ALT_LOAD_COND <- 0;`.
- `ai/OpexAI/info.nut` : déclaration du réglage dans `GetSettings()` aux 4 difficultés à 0, plage 0..100.
- `ai/OpexAI/settings.nut` : lecture dans `OpexLoadSettings`, forçage à 0 si `!road1yRoadOnly`.
- `ai/OpexAI/bus_districts.nut` :
  - `OpexRoad1yAltLoadIsInverted(vehicle)` : détection du sens d'un bus par lecture des drapeaux d'ordres réels.
  - `OpexRoad1yAltLoadOrient(vehicle, inverted)` : application des ordres inversés propres (plein à B, rien à A).
  - `OpexRoad1yAltLoadCondEligible(line)` : vérification conditionnelle sur ligne en service (`waitingB >= seuil` ou `popB >= seuil * 15`).
  - `OpexRoad1yAltLoadCondEligibleCandidate(candidate)` : vérification conditionnelle à l'ouverture de ligne (`popB >= seuil * 15`).
  - `OpexRoad1yAltLoadCondAdjustFleet(lineOrCandidate, built, site)` : réajustement des bus construits jusqu'au quota de 33 % sous condition de potentiel, avec partage d'ordres entre bus inversés et trace `OpexDecide("ROAD1Y_ALT_LOAD_COND", ...)`.
- `ai/OpexAI/builder_road.nut` :
  - Dans `OpexBuildRoadRoute` : appel de `OpexRoad1yAltLoadCondAdjustFleet` sur la flotte initiale à l'ouverture.
  - Dans `OpexRoadRefleet` : appel de `OpexRoad1yAltLoadCondAdjustFleet` sur les renforts achetés.
- `sweeps/test_road1y_alt_load_cond.py` : test unitaire dédié (déclaration, 4 valeurs à 0, lecture, fonctions de conditionnement et d'ajustement, appels dans le constructeur).
- `sweeps/test_road1y_multimodal_gate.py` : ajout dans l'inventaire route seule.
- `sweeps/test_v251_inventory.py` : ajustement du plafond des réglages à 71 avec justification.
- `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py` : intégration des empreintes de projection multi-époques.

---

## 1. Contexte économique et mécanique

La version aveugle `road1y_alt_load` (testée dans la session cloud `a3246a97`) appliquait l'inversion des ordres à 33 % de la flotte sur toutes les paires sans distinction. Bien que très prometteuse (+14,7 k£/an, 25 victoires contre 15 défaites), elle échouait sous le seuil d'adoption de 20,7 k£ en raison d'un effet pervers précis :
- Lorsque le terminus B est un petit village à faible production (ex. 150 habitants, 10 passagers/mois), un bus inversé en plein chargement à B y attendait plusieurs mois consécutifs pour se remplir, bloquant le quai et gelant son capital.

`road1y_alt_load_cond` résout exactement cette faiblesse :
- L'inversion (plein chargement à B, rien à A) n'est autorisée **que si le potentiel de B est mesuré suffisant** :
  1. Pour une ligne en service : stock de passagers en attente à la station B `waitingB >= seuil` (les passagers sont déjà là, pas d'attente bloquante) OU population de la ville B `popB >= seuil * 15`.
  2. Pour une ouverture de ligne : population de la ville B `popB >= seuil * 15`.
- Sur les petits sites (potentiel < seuil), aucun bus n'est inversé : tous les bus chargent normalement à la source A.

---

## 2. Examen des règles Squirrel et garanties

- **Identifiants réservés :** Aucun mot-clé interdit utilisé.
- **Fonctions anonymes et closures :** Zéro fonction anonyme ou closure capturante.
- **Tableaux :** Pas d'appel `.find(`.
- **Chemin par défaut (valeur 0) :**
  Quand `road1y_alt_load_cond == 0`, toutes les gardes `if (ROAD1Y_ALT_LOAD_COND > 0)` neutralisent immédiatement le code. Le comportement exécuté est 100 % rigoureusement identique à master.
- **Préservation des fixtures figées :**
  Les insertions dans `builder_road.nut` sont situées aux lignes 5536 et 6542, strictement en dehors de tous les 33 hunks de `road100_bus_districts_hunks.json`, garantissant la propreté absolue des 236 tests de projection `road100`.

---

## 3. Validation des tests

- `test_road1y*.py` : 88/88 tests OK.
- `test_road100*.py` : 236/236 tests OK (3 sautés autorisés).
- `test_v251*.py` : 7/7 tests OK (plafond 71 AddSetting respecté).
- `git diff --check` : 0 anomalie.

---

## 4. Recommandation pour la qualification

- Réglage à banquer : `road1y_alt_load_cond=20` (seuil de 20 passagers en attente à B ou ville B ≥ 300 habitants).
