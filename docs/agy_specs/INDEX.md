# Index des Spécifications Techniques — Chantiers Complexes Hors Rail

Ce dossier regroupe les 10 spécifications techniques approfondies préparées pour la suite des développements d'OpexAI. Conformément aux consignes de mission, chaque document détaille l'objectif chiffré, les lignes de code vérifiées dans le worktree, la conception sous réglage (défaut 0), les pièges historiques répertoriés dans les journaux, le plan de test (contrats, smoke, portes V102) et l'estimation de rentabilité / opcodes.

---

## 1. Tableau Synthétique Comparatif

Les dossiers sont classés ci-dessous par **ratio décroissant Effet attendu / Difficulté de réalisation** :

| Rang | Sujet / Fichier | Nature | Difficulté | Effet attendu | Ratio | Recommandation |
|:---:|---|---|:---:|---|:---:|---|
| **1** | [EB-10](EB10_SENTINEL_GUARD.md)<br>`EB10_SENTINEL_GUARD.md` | Correctif Bug / Garde | **1.5 / 5** | $+15$ à $+40\text{ k£/an}$<br>(Déblocage fret urbain) | **Très élevé** | **Priorité 1** : Corriger la sentinelle `65535` directement comme bugfix ou sous setting. |
| **2** | [FAIR-PLAY / JOURNAUX-NORMAL](FAIR_PLAY_PARTIES_NORMALES.md)<br>`FAIR_PLAY_PARTIES_NORMALES.md` | Courtoisie & Hygiène | **1.5 / 5** | $+30$ à $+60\text{ k ops/an}$<br>Carte propre (0 panneau) | **Très élevé** | **Priorité 2** : Supprimer les panneaux de debug carte et filtrer les logs pour les parties humaines sans toucher au mode compétitif. |
| **3** | [FLOTTE-EQUILIBRE](FLOTTE_EQUILIBRE.md)<br>`FLOTTE_EQUILIBRE.md` | Dimensionnement Flottes | **2.0 / 5** | $+30$ à $+60\text{ k£/an}$ (3 ans)<br>$+80$ à $+150\text{ k£/an}$ (10 ans) | **Très élevé** | **Priorité 3** : Éliminer la surcapacité oisive (8,75 vs 6,81 bus/ligne, 84,3 vs 48 avions) sans bris de ligne. |
| **4** | [AIR-COVERAGE-STOP / EB-1](AIR_COVERAGE_STOP.md)<br>`AIR_COVERAGE_STOP.md` | Économie Opcodes & Agilité | **2.0 / 5** | $15$ à $30\text{ M ops/an}$<br>Accélération lignes AIR | **Très élevé** | **Priorité 4** : Éviter les scans complets de 64 tuiles dès que la couverture passagers est saturée. |
| **5** | [OPCODES / IDLE-1 / AIList](OPCODES_IDLE1.md)<br>`OPCODES_IDLE1.md` | Optimisation Opcodes & Tick | **2.5 / 5** | $15$ à $30\text{ M ops/an}$<br>Valorisation sleep slack | **Élevé** | **Priorité 5** : Remplir le reliquat de tick avec un consommateur de fond identifié (C78/PO-02). |
| **6** | [PO-02](PO02_VIVIER_EXPIRATION.md)<br>`PO02_VIVIER_EXPIRATION.md` | Architecture Portefeuille | **3.5 / 5** | $10$ à $25\text{ M ops/an}$<br>Suppression pics réactifs | **Élevé** | **Priorité 6** : Donner une durée de vie propre à chaque mode (30j rail/route, 90j eau). |
| **7** | [MULTI-1 Relance](MULTI1_CONDITIONS_RELANCE.md)<br>`MULTI1_CONDITIONS_RELANCE.md` | Stratégie Multimodale Tardive | **3.0 / 5** | $+50$ à $+120\text{ k£/an}$ (10 ans)<br>Ratio AAA de 66 % à $\ge 75\,\%$ | **Élevé** | **Priorité 7** : Débloquer la starvation 1975–1979 (16 M£ de caisse dormante, 0 jour unaffordable) sous conditions strictes. |
| **8** | [EB-4](EB4_ARBITRAGE_CASH.md)<br>`EB4_ARBITRAGE_CASH.md` | Sélection Économique | **3.5 / 5** | $+30$ à $+80\text{ k£/an}$<br>(Années 1 à 3) | **Moyen / Élevé** | **Priorité 8** : Arbitrer la trésorerie 1970–72 entre AIR et ROUTE sans effet "cheap-first". |
| **9** | [EB-7 Phase 2](EB7_PHASE2.md)<br>`EB7_PHASE2.md` | Instrumentation Financière | **3.0 / 5** | Sonde passive pure<br>(ROI décisionnel EB-4) | **Moyen** | **Priorité 9** : Isoler les coûts réels d'infrastructure/véhicules hors AITestMode. |
| **10** | [LATE-GAME-1 / V249 / V251](LATE_GAME_1.md)<br>`LATE_GAME_1.md` | Stratégie Fin de Partie | **4.5 / 5** | $+50$ à $+150\text{ k£/an}$<br>(Années 8 à 10) | **Différé** | **Conditionné** : Bloqué par la décision du 26/10 jusqu'à validation de la parité sur 48 cellules. |

---

## 2. Recommandation d'Ordre d'Exécution pour le Chef de Session

### Phase 1 — Quick-Wins, Courtoisie et Rééquilibrage Immédiat
1. **EB-10 (`EB10_SENTINEL_GUARD.md`) :**
   Le bug `AIIndustry.GetIndustryID(...) == 65535` dans `lines.nut:255` et `bus_districts_overrides.nut:445` empoisonne les clés d'abandon depuis plusieurs versions. C'est un correctif propre, sûr, à fort retour économique immédiat sur le fret de biens.
2. **FAIR-PLAY / JOURNAUX-NORMAL (`FAIR_PLAY_PARTIES_NORMALES.md`) :**
   Suppression des panneaux de debug sur la carte (panneaux budget sur tuile `(20, 1)`, marques d'ancres) et filtrage des logs pour les parties avec joueur humain, sans altérer le profil compétitif par défaut (`probes=2`).
3. **FLOTTE-EQUILIBRE (`FLOTTE_EQUILIBRE.md`) :**
   S'attaque au gisement de rentabilité le plus documenté des duels récents (04/11) : résorption de l'excédent de 1,94 bus par ligne et plafonnement des 36 appareils excédentaires à 10 ans sans perte de chiffre d'affaires.
4. **AIR-COVERAGE-STOP (`AIR_COVERAGE_STOP.md`) :**
   Interrompre la recherche de tuiles d'aéroport dès que le bassin de population atteint le seuil critique libère immédiatement des millions d'opcodes au démarrage de l'IA.

### Phase 2 — Fluidité et Architecture des Opcodes
4. **OPCODES / IDLE-1 (`OPCODES_IDLE1.md`)** et **PO-02 (`PO02_VIVIER_EXPIRATION.md`) :**
   Ces deux chantiers s'épaulent mutuellement. PO-02 fournit un consommateur légitime et progressif au travail de fond d'IDLE-1, tandis que PO-02 stabilise la consommation CPU en éliminant les tempêtes de régénérations synchrones.

### Phase 3 — Arbitrage Financier et Déblocage Tardif
5. **MULTI-1 Conditions de Relance (`MULTI1_CONDITIONS_RELANCE.md`) :**
   Permet d'attaquer directement le décrochage tardif 1975–1979 sans risquer de déstabiliser les 5 premières années où le multimodal OpexAI surperforme (92,67 % fin 1974). Le réinvestissement ciblé de 2 à 4 M£ de caisse oisive comble l'écart face à AAAHogEx.
6. **EB-7 Phase 2 (`EB7_PHASE2.md`) puis EB-4 (`EB4_ARBITRAGE_CASH.md`) :**
   La comptabilité fine d'EB-7 phase 2 permet de calibrer les seuils exacts d'éviction pour l'arbitrage caisse 1970–1972 entre AIR et ROUTE sans risque d'effondrement de la valeur de compagnie.
7. **LATE-GAME-1 (`LATE_GAME_1.md`) :**
   À aborder uniquement après confirmation formelle que le prérequis de parité d'OpexAI face à AAAHogEx à 5 ans est satisfait sur la grille des 48 cellules.
