# Retests numériques C121 — bilan du 4 octobre 2026

**Dix valeurs traitées : neuf portes A complètes et saines, toutes fail_primary ; une valeur non validée faute d'exposition. Aucune porte B, aucun défaut modifié.**

Fin à **20:12:06 Paris**, durée murale **1 h 56 min 48 s**, interruptions et attente de l'autre campagne incluses. 840 parties uniques complètes/saines ; 10 smokes, 10 diagnostics, 9 A. Aucun banc rejoué.

## Référence et protocole

Référence fixe bad7e7b0af401327b039248c91d4086e1ee43b3d, C121 economics/catalogue=1 des deux côtés, plancher marginal et snapshot hubs=1, C115=1 protégé. Chaque valeur est comparée séparément à son défaut, sans cumul de gagnants. Source économique ad85a159c212936daf0064811561a5de5e2dc6481169fe8803d277fe4a52fabb. Hashes des deux arbres figés vérifiés inchangés à la clôture.

10 CPU / 8 Go / 10 workers, un conteneur à la fois, plafond RAM+swap égal à la RAM. Budget initial huit heures non prolongé. Smoke42×1 ; exposition5 graines42/100/999/1234/5678 dans une copie instrumentée séparée ; A40×3 sauf fenêtre live A40×6 pré-enregistrée. Primaire : profit annuel terminal Opex variante−référence. Règle gain_short : Wilcoxon exact bilatéral p<0,05, IC95 bootstrap bas>0, gain moyen≥4 %, garde valeur ratio des moyennes −5 %. Bootstrap20 000/graine0. B20×10 uniquement après A qualifiée.

## Résultats

Les deltas de profit et IC sont en k£/an. Les neuf IC traversent zéro : aucun gain ni perte statistiquement établi ; aucun seuil de gain4 % atteint. Toutes les gardes de valeur sont tenues.

| Réglage | Ancien→candidat | Ans | Δ profit k£ | Δ % | IC95 bootstrap k£ | Wilcoxon p | V/D/E | Δ valeur % | Verdict |
|---|---|---:|---:|---:|---|---:|---|---:|---|
| air_early_slot_target_towns | 6→4 | 3 | +24.14 | +1.49 | [-50.75 ; +100.48] | 0.617865 | 19/21/0 | +1.70 | fail_primary |
| air_early_slot_target_towns | 6→8 | 3 | +32.31 | +2.00 | [-19.46 ; +84.49] | 0.204380 | 22/16/2 | +1.73 | fail_primary |
| air_early_slot_bonus_pct | 50→30 | 3 | -9.86 | -0.61 | [-25.56 ; +2.29] | 0.322266 | 3/7/30 | -0.26 | fail_primary |
| air_early_slot_bonus_pct | 50→70 | 3 | -13.05 | -0.81 | [-42.62 ; +9.83] | 0.640625 | 3/5/32 | -1.00 | fail_primary |
| c121_air_first_live_growth_phase_years | 4→2 | 6 | -13.35 | -0.85 | [-57.68 ; +31.57] | 0.501375 | 19/21/0 | -0.33 | fail_primary |
| c121_air_first_live_growth_phase_years | 4→6 | — | — | — | — | — | — | — | Non validé : exposition absente5×6 |
| air_fleet_cadence_days | 7→14 | 3 | +15.43 | +0.95 | [-32.53 ; +63.27] | 0.481672 | 20/18/2 | +0.47 | fail_primary |
| air_fleet_cadence_days | 7→30 | 3 | +30.87 | +1.91 | [-24.89 ; +88.32] | 0.467972 | 20/20/0 | -0.15 | fail_primary |
| air_early_slot_min_pop | 1000→800 | 3 | +19.93 | +1.23 | [-54.00 ; +93.39] | 0.594945 | 22/17/1 | +2.02 | fail_primary |
| air_early_slot_min_pop | 1000→1500 | 3 | +20.11 | +1.24 | [-42.03 ; +84.73] | 0.744604 | 20/20/0 | +1.46 | fail_primary |

La fenêtre4→6 ans n'a montré aucun événement effectif dans le diagnostic sain5×6 : ses A/B n'ont pas été lancées. Ce constat ne prouve pas l'absence d'effet sur toutes les graines et ne constitue pas un rejet économique.

## Campagnes et récupération

File initiale c121_numeric10_20261004_161323, puis reprises1/2/3 c121_numeric10_resume{1,2,3}_20261004, reliées par leurs continuation.json. Interruptions du client Windows0xc000013a : bonus30 déjà complet et phase2 laissée finir dans son conteneur exact, récupérés sans nouvelles parties. Erreur de casse du message Docker dans le suivi corrigée. L'autre campagne n'a pas été interrompue. Runner hôte corrigé ; 13 tests ciblés réussis. Les statuts historiques d'arrêt restent conservés, avec reçus reconciliation.json séparés.

Tous les JSON, JSONL, logs, manifestes et bundles restent dans les dossiers uniques results. Hashes manifestes vérifiés, métriques annuelles/couverture/échantillons complets et santé contrôlés à la clôture.

## Fichiers des neuf portes A

- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_20261004_161323_target_4_A.json — manifeste 8c8131ed28bed33163fb47cffb6246814bc2e50928c3a68b33d4d2156392f5e0.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_20261004_161323_target_8_A.json — manifeste 0b769110333af01f72517adb901bd06403fd90b3835cae021a832c8261bb4a70.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_20261004_161323_bonus_30_A.json — manifeste 14e8d6962f575ff590a9f74f00e914d4b3246e07c201004540cd864059e46002.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_resume1_20261004_bonus_70_A.json — manifeste c7b8b5836a8ce6b90c31a16c5c4f0249fe60a77ef8d67b428d796aa1c4e367b5.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_resume1_20261004_phase_2_A.json — manifeste 0f6193a877fab3dfe25e9eb50060a7679d7c74e706e86b2d991bdbed82326174.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_resume3_20261004_cadence_14_A.json — manifeste 41aa5513a44a44863b3e455d8dce0cd4af2c5c03931d10d1d5a057c325082839.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_resume3_20261004_cadence_30_A.json — manifeste d70401169c82fb8809b7f7296637f15244f01b331ef06cda5e048f73b9020e0c.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_resume3_20261004_population_800_A.json — manifeste 4cac0b52e9ded99ae51fc54fc813a54f018c89c73a4366457ef95f622c34d09a.
- results/c121_numeric10_20261004_161323/snapshot/results/c121_numeric10_resume3_20261004_population_1500_A.json — manifeste e1c02f7eb05e4dfc7ef5646c87a950377b12f14ef2045c87ef5c74ea88fdb382.

Aucune adoption, publication ou relance supplémentaire. Les défauts numériques restent cible6, bonus50, fenêtre4, cadence7 jours et population1000. Les variantes les plus positives descriptivement sont cible8 (+2,00 %) et cadence30 (+1,91 %), mais elles ne sont pas qualifiées.
