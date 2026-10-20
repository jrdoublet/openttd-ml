# V285 — porte A rail seul, PC, 20 octobre 2026

## Protocole

- Branche `v285`, commit testé `a4b59d337815ab46f59c5f774b390d829fdd10ba`, arbre propre au lancement.
- `bash sweeps/run_v285_pc.sh` : smoke 1 graine × 1 an, puis porte A **40 graines × 3 ans**, 1 répétition, 80 parties C66.4 en duels séparés contre AAAHogEx sur cartes appariées.
- Référence `OpexAI[v285_rail_pax_growth=0,mode_air=0,mode_road=0,mode_water=0]` ; variante `OpexAI[v285_rail_pax_growth=7,mode_air=0,mode_road=0,mode_water=0]`. Le masque 7 active les quais longs (1), l'ajout de wagons (2) et le délai de 90 jours par ligne (4).
- Ressources PC : 10 CPU, 8 Go RAM, 10 workers, Docker `openttd-lab:latest`, SHA256 `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
- Bundle figé : `3365b7542326c75357805fbb0e5adb3320e8d9cd087144d31775101433305f56`.

## Résultats

- Smoke 1×1 terminé (2/2 parties), diagnostic de profit annuel variante − référence **−70 575 £/an** ; une seule graine, non probant économiquement.
- Porte A : **40/40 paires complètes**, 80/80 parties. Aucun échec de run. Critère `gain_short`, gain utile prédéfini ≥ **40 496,418 £/an** (+4 % de la référence).
- Profit annuel variante − référence : **+3 399,65 £/an** en moyenne ; médiane **−18 073,5 £/an** ; victoires/défaites/égalités **18/22/0** ; Wilcoxon **p = 0,941724** ; IC95 bootstrap **[−43 990,825 ; +53 394,425] £/an**.
- Valeur d'entreprise, ratio des moyennes variante / référence : **0,977471** (**−2,252857 %**), garde de valeur −5 % respectée.
- Comparaison secondaire du bras de **référence** avec AAAHogEx : OpexAI **1 012 410 £/an** contre AAAHogEx **1 273 706 £/an**, soit **79,49 %** ; valeur d'entreprise **1 467 287 £** contre **1 244 137 £** (117,94 %). Ne pas confondre ce duel avec l'effet causal V285/référence.

**Verdict officiel : `fail_primary`**. Le gain minimal, la significativité et la borne inférieure de l'IC ne sont pas atteints ; la garde de valeur passe. **V285 non qualifié, défaut `v285_rail_pax_growth=0` conservé ; aucune porte B autorisée par cette campagne.** Pas de nouveau banc lancé pour cet archivage.

## Preuves versionnées

Les résultats et manifestes originaux sont dans `results/v285_railseul_porteA_40x3_pc_20261020{,_smoke}.{json,manifest.json}` ; les relevés mensuels dans les fichiers `*.jsonl.gz` correspondants (gzip sans modification des lignes). Les logs moteur et bundles sont conservés localement dans les dossiers `results/*_engine/` et `results/*_bundle/`, non publiés dans ce commit.
