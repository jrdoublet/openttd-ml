# Audit d'hygiène documentaire : Entrées périmées ou contredites dans `docs/taches.md`

Date : 2026-11-07  
Branche de travail : `agy-easy` (base `origin/master 7e5ad9d4`)  
Règle : **Document d'audit seul — ne pas modifier `docs/taches.md` lui-même.**

---

## 1. Synthèse de l'audit

L'analyse de `docs/taches.md` au regard de l'historique récent de Git (`origin/master` du 02/11 au 07/11/2026) révèle plusieurs catégories d'obsolescence documentaire :
1. **Défauts adoptés sur `master` non répercutés** dans les sections de synthèse et de priorités (`rail_loop=1`, `v257_demand=1`).
2. **Leviers route seule ROAD1Y testés et formellement rejetés** entre le 02/11 et le 07/11, dont certaines pistes restent présentées comme « ouvertes » ou dont les résultats ne sont pas synchronisés dans le registre bas.
3. **Périmètre et compteurs de tests obsolètes** sur la tâche `QUALITÉ-TESTS-ESTIM31`.
4. **Tâches ferroviaires et multimodales suspendues ou écartées** restant listées en statut ouvert (`- [ ]`) en contradiction avec les décisions utilisateur formelles du 04/11.

---

## 2. Inventaire détaillé des contradictions et obsolescences

### Entrée 1 : Adoption par défaut de `rail_loop=1` absente du bilan ferroviaire du 04/11
- **Emplacement dans `docs/taches.md` :** Lignes 10–28 (`### 04/11 — RAIL-SIBLING + RAIL-OPEN : adoption explicite utilisateur`).
- **Texte actuel :**
  > *« Décision utilisateur du 04/11 : adopter sur `master` `rail_sibling=1` et `rail_open=1` aux quatre difficultés. Les autres prototypes ferroviaires RAIL-LONG v2/v3, INVEST-STALL et DOUBLE-GROW restent absents de cette intégration et désactivés. »*
- **Preuve de contradiction / décision plus récente :**
  - Commit `a8cfb1e8` (04/11) : `feat(rail-loop): corriger depot_flow et passer rail_loop=1 par défaut (décision utilisateur)`.
  - Commit `80df60e9` (04/11) : `fix(rail-fill): ignorer une ligne en conversion RAIL-LOOP (désormais par défaut)`.
- **Analyse :** La boucle de retournement arrière des quais (`rail_loop=1`) a été formellement adoptée par défaut sur `master` sur décision explicite de l'utilisateur le même jour (04/11). La section introductive de `docs/taches.md` ne cite que `rail_sibling=1` et `rail_open=1`, omettant `rail_loop=1` qui est pourtant actif en production.

---

### Entrée 2 : Activation par défaut de `V257-DEMAND` non consignée dans le registre
- **Emplacement dans `docs/taches.md` :** Mentionné uniquement comme code de révision réactive existant (L1174, etc.), aucune entrée d'adoption par défaut.
- **Preuve de contradiction / décision plus récente :**
  - Commit `11f29b13` (06/11) : `Activer V257-DEMAND par défaut et consigner la décision de nuit`.
  - Commit `056dae12` (06/11) : `Corriger les projections historiques après adoption de V257-DEMAND`.
- **Analyse :** `v257_demand` a été activé par défaut le 06 novembre 2026. `docs/taches.md` (dont la dernière date d'en-tête affichée est le 4 novembre) n'a pas été incrémenté pour refléter cette décision de production.

---

### Entrée 3 : Leviers route seule (ROAD1Y) rejetés du 02 au 07/11
- **Emplacement dans `docs/taches.md` :** Lignes 77–82 et L98–102 (`4. Pistes encore ouvertes`).
- **Preuves de contradiction / commits de rejet :**
  1. `road1y_pax_min` :
     - Commit `1be5d747` : `docs(taches): road1y pax_min gate A fail (100 and 50)`.
     - Résultat : Porte A 40×3 = 100 à −11,6 k£/an, = 50 à −2,9 k£/an (`fail_primary`). Fil clos.
  2. `road1y_alt_load` :
     - Commit `564d7892` : `docs(taches): road1y_alt_load gate A fail (33 and 50)`.
     - Résultat : Porte A 40×3 = 33 à +14,7 k£/an, = 50 à +12,5 k£/an (sous le seuil 20,7 k£/an requis). Fil clos.
  3. `road1y_aaa_fleet=1` :
     - Commit `10d3a6c1` : `docs(taches): road1y_aaa_fleet gate A fail (-22.7k, value guard)`.
     - Résultat : Porte A 40×3 à −22,7 k£/an (valeur −9,4 %, rupture garde de valeur). Fil flotte clos.
  4. `road1y_truck_fleet=1` et `road1y_pair_fleet=8` :
     - Commit `70d4e6d3` : `docs(taches): road1y truck_fleet and pair_fleet gate A fail`.
     - Résultat : Porte A 40×3 à +16,9 k£/an et +18,6 k£/an, mais médianes négatives (−6,7 k£ et −5,6 k£). Rejetés.
  5. `road1y_town_reuse=1` :
     - Commit `44d9313e` : `docs(taches): road1y_town_reuse gate A harmful (-38.3k)`.
     - Résultat : Porte A 40×3 à −38,3 k£/an (p = 0,0098, valeur −6,0 %). Nuisible, rejeté.
- **Analyse :** Alors que les lignes 77–82 consignent bien ces rejets au fil de l'eau, la sous-section 4 (« Pistes encore ouvertes », L98–102) évoque encore des travaux sur la flotte et les paires, créant une ambiguïté sur le statut réel de ces chantiers qui sont désormais scellés par des NO-GO statistiques stricts.

---

### Entrée 4 : Compteurs et périmètre de `QUALITÉ-TESTS-ESTIM31`
- **Emplacement dans `docs/taches.md` :** Lignes 1163 et 1188.
- **Texte actuel :**
  > *« La découverte générale historique affiche 3 175 tests, 84 échecs, 16 erreurs sous le nouveau défaut, dont des attentes estim_unifie=0 et des instantanés obsolètes ; avant promotion elle avait déjà 3 124 tests, 2 échecs et 12 erreurs. »*
- **Preuve d'obsolescence :**
  - La suite de tests globale sous Python 3.14 compte désormais **3 849 tests** (enrichissement post-merge RAIL et ROAD100, commits `6f57003f`, `7e5ad9d4`).
  - Au démarrage de la mission `agy-easy`, la suite présentait 107 anomalies (83 FAIL, 24 ERROR).
  - Après les corrections des tours 1 et 2 (commits `f637c2a5` à `67b469af`), il ne reste plus que **35 anomalies** (34 FAIL, 1 ERROR), dont **18 sont des tests ferroviaires gelés**.
- **Analyse :** Les chiffres de 3 175 tests et 100 anomalies datent du 30 octobre 2026 et ne reflètent plus la réalité du dépôt.

---

### Entrée 5 : Statut de `INVEST-STALL` dans le registre des tâches ouvertes
- **Emplacement dans `docs/taches.md` :** Ligne 1144 (`- [ ] **04/11 — INVEST-STALL, achats de wagons et extension transactionnelle des quais 7→6 : NON QUALIFIÉS.**`).
- **Preuve de contradiction :**
  - Section introductive Ligne 13–14 : *« Les autres prototypes ferroviaires RAIL-LONG v2/v3, INVEST-STALL et DOUBLE-GROW restent absents de cette intégration et désactivés. »*
  - Ligne 1144 : Noté comme tâche ouverte non cochée (`- [ ]`), alors que le diagnostic P0 est clos, qu'aucune extension de quai n'a pu être observée, et que l'utilisateur a expressément exclu INVEST-STALL de l'intégration `master` du 04/11.
- **Analyse :** Cette entrée devrait être classée en `[x] clos / NO-GO` pour être cohérente avec le paragraphe introductif du 04/11.

---

### Entrée 6 : Présence de `MULTI-1` dans la section « Priorités ouvertes »
- **Emplacement dans `docs/taches.md` :** Ligne 1211.
- **Texte actuel :**
  > *- [ ] **MULTI-1 — suspendu par décision du 26/10, pas de relance automatique.** Trois leviers ROUTE/AIR non exposés, SHADOW fret routier sans projet physique qualifié et autopsie tardive C63 conservés aux journaux.*
- **Preuve de contradiction :**
  - La tâche est placée sous la rubrique `## Priorités ouvertes — actions avec critères de sortie` (L1186).
  - Or son titre et son contenu énoncent formellement qu'elle est **suspendue** depuis le 26/10 sans aucune action ouverte ni relance autorisée.
- **Analyse :** Conflit de classification entre le titre de section (« Priorités ouvertes ») et l'état gelé/suspendu de la tâche.
