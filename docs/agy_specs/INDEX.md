# Index des Spécifications Techniques — Chantiers Complexes Hors Rail

Ce dossier regroupe les 7 spécifications techniques approfondies préparées pour la suite des développements d'OpexAI. Conformément aux consignes de mission, chaque document détaille l'objectif chiffré, les lignes de code vérifiées dans le worktree, la conception sous réglage (défaut 0), les pièges historiques répertoriés dans les journaux, le plan de test (contrats, smoke, portes V102) et l'estimation de rentabilité / opcodes.

---

## 1. Tableau Synthétique Comparatif

Les dossiers sont classés ci-dessous par **ratio décroissant Effet attendu / Difficulté de réalisation** :

| Rang | Sujet / Fichier | Nature | Difficulté | Effet attendu | Ratio | Recommandation |
|:---:|---|---|:---:|---|:---:|---|
| **1** | [EB-10](EB10_SENTINEL_GUARD.md)<br>`EB10_SENTINEL_GUARD.md` | Correctif Bug / Garde | **1.5 / 5** | $+15$ à $+40\text{ k£/an}$<br>(Déblocage fret urbain) | **Très élevé** | **Priorité 1** : Corriger la sentinelle `65535` directement comme bugfix ou sous setting. |
| **2** | [AIR-COVERAGE-STOP / EB-1](AIR_COVERAGE_STOP.md)<br>`AIR_COVERAGE_STOP.md` | Économie Opcodes & Agilité | **2.0 / 5** | $15$ à $30\text{ M ops/an}$<br>Accélération lignes AIR | **Très élevé** | **Priorité 2** : Éviter les scans complets de 64 tuiles dès que la couverture passagers est saturée. |
| **3** | [OPCODES / IDLE-1 / AIList](OPCODES_IDLE1.md)<br>`OPCODES_IDLE1.md` | Optimisation Opcodes & Tick | **2.5 / 5** | $15$ à $30\text{ M ops/an}$<br>Valorisation sleep slack | **Élevé** | **Priorité 3** : Remplir le reliquat de tick avec un consommateur de fond identifié (C78/PO-02). |
| **4** | [PO-02](PO02_VIVIER_EXPIRATION.md)<br>`PO02_VIVIER_EXPIRATION.md` | Architecture Portefeuille | **3.5 / 5** | $10$ à $25\text{ M ops/an}$<br>Suppression pics réactifs | **Élevé** | **Priorité 4** : Donner une durée de vie propre à chaque mode (30j rail/route, 90j eau). |
| **5** | [EB-4](EB4_ARBITRAGE_CASH.md)<br>`EB4_ARBITRAGE_CASH.md` | Sélection Économique | **3.5 / 5** | $+30$ à $+80\text{ k£/an}$<br>(Années 1 à 3) | **Moyen / Élevé** | **Priorité 5** : Arbitrer la trésorerie 1970–72 entre AIR et ROUTE sans effet "cheap-first". |
| **6** | [EB-7 Phase 2](EB7_PHASE2.md)<br>`EB7_PHASE2.md` | Instrumentation Financière | **3.0 / 5** | Sonde passive pure<br>(ROI décisionnel EB-4) | **Moyen** | **Priorité 6** : Isoler les coûts réels d'infrastructure/véhicules hors AITestMode. |
| **7** | [LATE-GAME-1 / V249 / V251](LATE_GAME_1.md)<br>`LATE_GAME_1.md` | Stratégie Fin de Partie | **4.5 / 5** | $+50$ à $+150\text{ k£/an}$<br>(Années 8 à 10) | **Différé** | **Conditionné** : Bloqué par la décision du 26/10 jusqu'à validation de la parité sur 48 cellules. |

---

## 2. Recommandation d'Ordre d'Exécution pour le Chef de Session

### Phase 1 — Quick-Wins et Correctifs Immédiats
1. **EB-10 (`EB10_SENTINEL_GUARD.md`) :**
   Le bug `AIIndustry.GetIndustryID(...) == 65535` dans `lines.nut:255` et `bus_districts_overrides.nut:445` empoisonne les clés d'abandon depuis plusieurs versions. C'est un correctif propre, sûr, à fort retour économique immédiat sur le fret de biens.
2. **AIR-COVERAGE-STOP (`AIR_COVERAGE_STOP.md`) :**
   Interrompre la recherche de tuiles d'aéroport dès que le bassin de population atteint le seuil critique libère immédiatement des millions d'opcodes au démarrage de l'IA.

### Phase 2 — Fluidité et Architecture des Opcodes
3. **OPCODES / IDLE-1 (`OPCODES_IDLE1.md`)** et **PO-02 (`PO02_VIVIER_EXPIRATION.md`) :**
   Ces deux chantiers s'épaulent mutuellement. PO-02 fournit un consommateur légitime et progressif au travail de fond d'IDLE-1, tandis que PO-02 stabilise la consommation CPU en éliminant les tempêtes de régénérations synchrones.

### Phase 3 — Arbitrage Financier et Fin de Partie
4. **EB-7 Phase 2 (`EB7_PHASE2.md`) puis EB-4 (`EB4_ARBITRAGE_CASH.md`) :**
   La comptabilité fine d'EB-7 phase 2 permet de calibrer les seuils exacts d'éviction pour l'arbitrage caisse 1970–1972 entre AIR et ROUTE sans risque d'effondrement de la valeur de compagnie.
5. **LATE-GAME-1 (`LATE_GAME_1.md`) :**
   À aborder uniquement après confirmation formelle que le prérequis de parité d'OpexAI face à AAAHogEx à 5 ans est satisfait sur la grille des 48 cellules.
