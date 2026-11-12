# Revue de code : Audit ESTIM-1 (Recette Prévue vs Réalisée Hors Rail : Air et Route)

Date : 2026-11-12  
Branche : `agy12-nov12`  
Auteur : Agent agy  

---

## 1. Contexte et Objectif

La tâche ESTIM-1 suite demandait un audit complet des erreurs de prévision de recette (prévue vs réalisée) sur les modes hors ferroviaires (**AIR** et **ROUTE**), fondé sur les données déjà mesurées :
- Tableau synthétique par mode et par classe d'âge (mise en service, montée en charge, régime établi, maturité).
- Analyse causale des biais systématiques observés.
- Évaluation de l'impact sur le classement du portefeuille (`PORTFOLIO_RANK`).
- Recommandations d'étalonnage pour le modèle unifié ESTIM-1 sans modification de code dans `ai/`.

---

## 2. Analyse Détaillée des Éléments Produits

### Fichiers créés :
1. `docs/agy_specs/ESTIM1_audit_recette.md` :
   - Tableau complet ventilé par mode (AIR, ROUTE) et par classe d'âge (Âge 0, Âge 1, Âge 2, Âge $\ge 3$).
   - Mesure de la sur-estimation brute médiane de l'aérien (2,16×, ratio réalisé/prévu de 0,463) et décomposition par typologie (`newpair` 0,446, `hubsite` 0,512, `hubhub` 0,423).
   - Analyse physique des délais d'encombrement au sol (`hub_delay` de 20 à 70 jours) et de la dissymétrie de charge pax (15–20 %) vs mail (65 %).
   - Mesure de l'effondrement économique de la route (ratio médian 0,121, sur-estimation de 8,26×, 23 % de lignes déficitaires en régime).
   - Démonstration de l'éviction causale du rail en 1970–1971 par la sur-estimation de l'aérien.
   - Recommandations d'ajustement préenregistrées conformes au protocole V102.

---

## 3. Conformité aux Règles Projet

- **Aucun fichier `.nut` modifié :** Travail purement analytique et documentaire.
- **Données réelles et sourcées :** Exploitation rigoureuse des campagnes mesurées (`lineprofit_default_5x6_20260926`, `diag_c98_air_realized_3x4_20260926_v2`, `airpairs_hub3_6x3_20261008`).
- **Hygiène Git :** `git diff --check` vérifié, zéro avertissement.

---

## 4. Résultats des Tests

- `sweeps/test_road1y*.py` : 74/74 OK (100 %)
- `sweeps/test_road100*.py` : 236/236 OK (3 skip) (100 %)
- `sweeps/test_v251*.py` : 7/7 OK (100 %)
- **Suite complète (`sweeps/test_*.py`) :** Strictement stable à 16 FAIL + 1 ERROR (tous ferroviaires), aucune nouvelle anomalie.

---

## 5. Risques Résiduels

Aucun risque. Le rapport fournit les bases quantifiées nécessaires à de futurs étalonnages d'estimateurs sous protocole V102.
