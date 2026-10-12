# AC04-A v3 — correction adoptée au point d'usage

**Décision du 12 octobre 2026 : AC04-A v3 adoptée** sous
`ac04_hub_usage_gate=1` par défaut, **rollback 0**.
Les anciennes AC04-A v1/v2 et V142/V143 restent rejetées.

## Correctif distinct de v1/v2

La découverte historique omet de marquer dans `seenStations`
un hub saturé : ce hub réapparaît dans la passe « orpheline »
avec `routes=0`. La v3 ne touche ni cette découverte ni
l'ordre des hubs. Avant l'évaluation des paires
`hub→site` et `hub→hub`, elle corrige uniquement les hubs
à zéro route avec `OpexAir0310CountStationRoutes`, lequel
utilise l'index C80 en O(1) lorsque actif, ou son repli
historique quand désactivé. La capacité inclut les lignes
`deadStreak >= 2`, comme la garde finale de construction.
Un hub saturé ne peut ainsi prendre la place d'un candidat
valide dans le classement. Les snapshots et les indices
`hubSiteI/J` et `hubHubI/J` sont conservés.

## Porte économique A : 40 graines × 4 ans

Campagne gelée `results/ac04v3_usage_A40x4_20261012_r1.json`.
**80/80 parties saines**, C66.4 `gain_short=pass` :
profit annuel terminal **+90 736,9 £/an**,
IC95 bootstrap **[+29 527,8 ; +150 402,1]**,
27 victoires / 13 défaites, Wilcoxon p = 0,00758,
valeur de compagnie **+4,165 %**.
Le gain dépasse le seuil de 4 % préenregistré.
**Aucun opcode inféré de cette porte** : `--script-debug`
n'était pas activé et ses 80 fichiers moteur sont vides.

## Porte B indépendante : 20 graines × 10 ans

Campagne gelée
`results/ac04v3_usage_B20x10_holdout_20261012_r1.json`.
**40/40 parties saines**, C66.4 `non_erosion=pass` :
profit annuel terminal **+80 386,95 £/an** (+2,348 %),
IC95 **[−98 433,15 ; +257 562,95]**, 13V/7D.
Cela démontre la non-érosion selon la porte prévue,
**pas un gain économiquement significatif à dix ans**.
Valeur de compagnie : **+0,982 %**.

Sondes `probe_loop_ops=1` bilatérales et `--script-debug`.
`LOOP_OPS` globaux exécutés, années *closes* 1970–1978 :
delta ON−OFF moyen **−2 906 092,1 opcodes**,
**−0,4927 %** ; IC95 bootstrap
**[−4 691 476 ; −1 196 413]**, 17 diminutions
pour 3 augmentations. L'année terminale 1979 est
censurée par l'absence de flush annuel. Analyse retenue :
`results/ac04v3_usage_B20x10_holdout_20261012_r1_opcode.json`.

## Décision, limites et rollback

La v3 a donc franchi la porte de gain à quatre ans,
la porte indépendante de non-érosion à dix ans et
présente **une diminution**, non une hausse, des
opcodes globaux. Elle n'exige pas la nouvelle tolérance
sur une légère dégradation opcode.
Le coût intrinsèque sur fixture synthétique et
l'exposition passive Top64 ont été préparés mais
**aucun résultat VM non exécuté n'est allégué** :
la décision repose sur les parties réelles appariées.

La garde finale `OpexAirBatchPlanStillLive` reste
nécessaire ; ce correctif traite le classement, pas
la constructibilité future. Le réglage 0 désactive
la validation au point d'usage et les gardes de paires,
et reproduit le comportement antérieur.

Le refactoring CD-01 à CD-06 est indépendant de ce
verdict AC04 et doit être validé économiquement
et en opcodes avant intégration.
