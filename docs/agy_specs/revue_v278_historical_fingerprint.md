# Revue de code : Neutralisation de l'extension PAX_AIR_FIRST_AIR_UNBOUNDED dans le contrat V278 (Famille K)

Date : 2026-11-07  
Auteur : Agent agy (tour 3)  
Périmètre :
- `sweeps/test_v278_air_lazy_sites.py`

## 1. Contexte et objectif
Le test `TestV278Source.test_historical_driver_and_economics_fingerprint` vérifie que la fonction `OpexAirPlansNewPairs` dans `ai/OpexAI/air_planning.nut` conserve son empreinte historique SHA-256 (`PAIRS_HASH = bb2d4cab20680ad35b7695595e7359d25f8359ea514a24d6454f1ff3a994ed06`).
Le test applique déjà une soustraction ciblée pour l'extension `front-pax2` (`fp2_pair`), afin de prouver que le cœur historique du driver aérien n'a subi aucune dérive non documentée plutôt que de rebaseliner l'empreinte.
Lors de l'adoption d'ESTIM-31 (commit `7160c6f5`), l'adjonction de l'option `PAX_AIR_FIRST_AIR_UNBOUNDED` sur la garde de distance minimale (`if (distance < minDist && !PAX_AIR_FIRST_AIR_UNBOUNDED)`) a altéré le hash calculé.

## 2. Analyse ligne à ligne du diff
- Ligne 213 : ajout de `pairs = pairs.replace(" && !PAX_AIR_FIRST_AIR_UNBOUNDED", "")`.
- Effet : retire strictement les octets de l'extension opt-in ESTIM-31 ajoutés sur la condition de distance.
- Résultat : le hash calculé correspond exactement au SHA `PAIRS_HASH` d'origine, prouvant l'intégrité byte-à-byte du reste de la fonction.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN** (aucun code IA altéré).
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect des suites de régression obligatoires :
  - `test_road1y*.py` : 74 tests OK
  - `test_road100*.py` : 236 tests OK (3 skipped)
  - `test_v251*.py` : 7 tests OK
  - `test_v278_air_lazy_sites.py` : 19 tests OK (100% vert)
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant. Le test garantit désormais à la fois la non-régression de V278 et la compatibilité avec l'extension `PAX_AIR_FIRST_AIR_UNBOUNDED`.
