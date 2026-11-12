# Revue de code : Diagnostic EB-5 (Débouchés GOOD précoces et chaîne industrielle)

Date : 2026-11-12  
Branche : `agy12-nov12`  
Auteur : Agent agy  

---

## 1. Contexte et Objectif

La tâche EB-5 demandait un diagnostic exclusif (« DIAGNOSTIC SEULEMENT », aucun code dans `ai/`) portant sur la filière industrielle des marchandises (`GOOD`) dans OpexAI :
- Analyse des usines avec 2 à 5 villes réellement acceptatrices par carte.
- Analyse des sources actives et de la chronologie d'alimentation en intrants.
- Explication structurelle du verrou `origin_served`.
- Distinction rigoureuse entre l'analyse dédupliquée EB-8 (script hors-ligne) et le bug de production EB-10 (catalogue et sentinelle `INVALID_INDUSTRY`).
- Proposition de levier chiffrée avec protocole de qualification V102 préenregistré.

---

## 2. Analyse Détaillée des Éléments Produits

### Fichiers créés :
1. `docs/agy_specs/EB5_diagnostic.md` :
   - Recensement complet et sourcé des 41 usines secondaires alimentées sur la campagne de référence 5×10 (`v233_long_expo_5x10_20261025_engine`).
   - Requêtes shell et grep documentées pour reproduire l'extraction de `V233_SOURCE` et `origin_served`.
   - Analyse moteur démontrant que seulement 2 à 5 villes par carte acceptent réellement `GOOD` (moyenne 3,6 villes, soit 8,2 % du total).
   - Analyse de la distance ferroviaire standard [30, 200] tuiles démontrant une moyenne de 1,8 débouché par usine, avec 6 usines orphelines (0 débouché constructible).
   - Localisation exacte du verrou `origin_served` dans `ai/OpexAI/candidates.nut:1897` et `ai/OpexAI/po01c_generators.nut:340`.
   - Clarification de la séparation entre l'analyse EB-8 (`p5_good_dedup.py`) et le correctif de production EB-10 (`catalog.nut:872` et `lines.nut:254`).
   - Spécification chiffrée du levier `eb5_good_chain_early` (déverrouillage conditionnel et bonus d'intrant orienté débouché, gain attendu +30 k£ à +45 k£/an par ligne, +60 k£ à +100 k£/an par monde).

---

## 3. Conformité aux Règles Projet

- **Aucune modification dans `ai/` :** Strict respect de la consigne « Ne code rien dans ai/ ».
- **Chiffres sourcés et vérifiés :** Tous les chiffres cités sont issus des logs réels et des campagnes antérieures mesurées.
- **Hygiène Git :** `git diff --check` vérifié, zéro avertissement.

---

## 4. Résultats des Tests

- `sweeps/test_road1y*.py` : 74/74 OK (100 %)
- `sweeps/test_road100*.py` : 236/236 OK (3 skip) (100 %)
- `sweeps/test_v251*.py` : 7/7 OK (100 %)
- **Suite complète (`sweeps/test_*.py`) :** Strictement stable à 16 FAIL + 1 ERROR (tous ferroviaires), aucune nouvelle anomalie.

---

## 5. Risques Résiduels

Aucun risque sur le code de jeu puisque l'intervention est 100 % documentaire et analytique.
