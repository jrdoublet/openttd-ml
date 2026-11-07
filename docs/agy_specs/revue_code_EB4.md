# Revue de Code — EB-4 (Arbitrage de Caisse 1970–1972, Volet AIR / ROUTE)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `eb4_air_road_arbitrage` (min=0, max=1, défaut 0, 4 difficultés à 0, flags 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `EB4_AIR_ROAD_ARBITRAGE <- 0;`.
  - `ai/OpexAI/info.nut` : déclaration du réglage public avec description et bornes.
  - `ai/OpexAI/settings.nut` : chargement unique `EB4_AIR_ROAD_ARBITRAGE = AIController.GetSetting("eb4_air_road_arbitrage") == 1 ? 1 : 0;`.
  - `ai/OpexAI/projects_selection.nut` :
    - Implémentation de la fonction d'arbitrage `OpexEB4RoadAllowed(roadProject, roadCapital, bestAir, deltaC, monthlyIncome, capitalBudget)`.
    - Calcul en amont de la sélection du meilleur projet aérien non finançable `bestUnaffordableAir`, du besoin résiduel $\Delta C$, et du revenu mensuel estimé via `AICompany.GetQuarterlyIncome`.
    - Application de la règle d'arbitrage dans la boucle principale de sélection et dans la boucle de repli (safety net).
  - `sweeps/test_eb4_arbitrage.py` : tests unitaires validant déclaration, globales, logique d'arbitrage et hygiène.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_v251_inventory.py` : synchronisation mécanique des empreintes SHA et projections de configuration.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Invariants

1. **Innocuité au défaut 0 :**
   - À `eb4_air_road_arbitrage = 0`, `EB4_AIR_ROAD_ARBITRAGE` vaut 0.
   - Le bloc de détection `eb4BestAir` est court-circuité.
   - Les gardes `if (EB4_AIR_ROAD_ARBITRAGE && project.mode == "road")` sont inactives.
   - La sélection de projets produit exactement la même séquence qu'auparavant au bit près.
2. **Logique économique d'arbitrage :**
   - Zone de protection : si le projet aérien manque de moins de 2 mois de cash flow ($\Delta C \le 2 \times \text{revenu mensuel}$), les investissements routiers sont suspendus pour préserver la caisse de l'aéroport.
   - Zone d'opportunité : si l'attente est longue ($\Delta C > 3 \times \text{revenu mensuel}$), les projets routiers ne sont autorisés que s'ils sont ultra-légers ($C \le 25\%$ du budget), à retour ultra-rapide ($\le 6$ mois), et ne touchent pas aux villes de l'aéroport réservé.
3. **Hygiène Squirrel & Non-rail :**
   - Aucun fichier rail touché (`builder_rail.nut`, etc.).
   - Aucune fonction anonyme, aucun `.find(`.
   - Utilisation de tables et de fonctions NoAI officielles.

---

## 3. Conclusion

Le code est rigoureusement conforme à la spécification `EB4_ARBITRAGE_CASH.md`, inoffensif au défaut 0, et validé par les suites de tests hôte.
