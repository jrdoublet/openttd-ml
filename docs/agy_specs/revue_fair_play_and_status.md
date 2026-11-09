# Revue de code : Spécification FAIR-PLAY et Actualisation de l'État des Tests (Tour 4)

Date : 2026-11-07  
Auteur : Agent agy (tour 4)  
Périmètre :
- `docs/agy_specs/FAIR_PLAY_PARTIES_NORMALES.md` (création)
- `docs/agy_specs/INDEX.md` (actualisation)
- `docs/agy_specs/tests_estim31_etat.md` (actualisation)

## 1. Contexte et objectif
- **Spécification FAIR-PLAY / JOURNAUX-NORMAL :** Répondre à la consigne 4 du tour 4 et au point `docs/taches.md:1216` en formalisant une option de courtoisie (`fair_play_courtesy`, défaut 0) pour les parties avec joueur humain ou normales : suppression intégrale des panneaux de debug sur la carte (`AISign.BuildSign`), modération des journaux, respect des règles d'emprise concurrentes via `difficulty.nut`, tout en sanctuarisant le profil compétitif par défaut (`probes=2`).
- **Actualisation des tests et index :** Intégrer cette 10e spécification dans le tableau comparatif d'INDEX.md (classée rang 2 par ratio effet/difficulté) et consigner la réduction des anomalies de 33 à 27 suite au commit `6891e303` (Famille M - centrage profil 0.92 DUEL et tolérance de préfixe).

## 2. Analyse ligne à ligne du diff
- `docs/agy_specs/FAIR_PLAY_PARTIES_NORMALES.md` :
  - Lignes de code vérifiées dans `difficulty.nut:1-54`, `task_report.nut:945-964`, `probes.nut:36-42`, `settings.nut:39-72`.
  - Conception sous réglage `fair_play_courtesy` (défaut 0, 4 zéros dans `info.nut`).
  - Garde `OpexSignAllowed(kind)` et destruction propre des panneaux résiduels de budget sur la tuile `(20, 1)`.
  - Pièges documentés : interdiction absolue de toucher au défaut compétitif `probes=2`, plafond 31 caractères NoAI, interdiction des `Sleep()` par politesse (AGENTS.md §2).
  - Plan de validation sans modification de `.nut`.
- `docs/agy_specs/INDEX.md` :
  - Comptage porté à 10 spécifications.
  - Ajout de la ligne au tableau comparatif (difficulté 1.5/5, ratio Très élevé).
  - Intégration en Phase 1 (Quick-Wins et Courtoisie) des recommandations d'exécution.
- `docs/agy_specs/tests_estim31_etat.md` :
  - Tableau d'évolution actualisé : Tour 4 à **26 failures + 1 error = 27 anomalies** (-80 anomalies par rapport aux 107 initiales, soit -75%).
  - Bilan des 27 anomalies restantes : 19 ferroviaires gelées, 8 liées à la divergence d'ordonnanceur EB14/PO01C (documentée avec options dans `defauts_decouverts.md`), 1 d'empreinte historique pré-fusions.
  - Documentation de la Famille M résolue au commit `6891e303`.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN** (respect strict de l'interdiction de modifier le code de jeu pour les spécifications).
- Identifiants réservés Squirrel : N/A (documentation markdown).
- Suites de régression obligatoires :
  - `test_road1y*.py` : 74 tests OK
  - `test_road100*.py` : 236 tests OK (3 skipped attendus)
  - `test_v251*.py` : 7 tests OK
- `git diff --check` : **propre** (zéro erreur d'espaces/retours à la ligne).

## 4. Risques résiduels
Néant. Documentation et spécification pures.
