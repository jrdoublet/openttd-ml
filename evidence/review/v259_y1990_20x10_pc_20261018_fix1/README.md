# V259 ? renouvellement des ponts, porte 20?10, d?part 1990

Campagne **v259_y1990_20x10_pc_20261018_fix1**, 20 graines ? 10 ans (1990?1999), 40 parties et 20 paires compl?tes. Ex?cution fig?e sur la branche `v259y1990`, source parente `efc0717224e6144498ff92144740fece22c6830a` avec correctif non commit? au lancement ; bundle fig? et manifeste fournis ci-dessous.

## Incident pr?alable et correctif

La campagne pr?c?dente `v259_y1990_20x10_pc_20261018` a ?chou? : les 20 variantes plantaient en 1995 avec `the index 'GetMaxSpeed' does not exist` depuis `OpexV259LineMaxVehicleSpeed` (`task_v259.nut:88`). **Cette campagne initiale est invalide, sans verdict ?conomique.** Correctif minimal : `AIVehicle.GetMaxSpeed(v)` remplac? par `AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v))`, plus un test de non-r?gression. Validation : 14 tests V259 r?ussis et smoke 1?6 ans (graine 42) sans crash, avec 2 renouvellements de pont observ?s.

## R?sultat complet du banc corrig?

- R?f?rence : `OpexAI[decision_log=1,v259_bridge_renew=0]` ; variante : `OpexAI[decision_log=1,v259_bridge_renew=1]`.
- `profit_year` moyen r?f?rence : **4,471,018.45 ?/an**, variante : **4,367,177.00 ?/an**.
- Delta appari? moyen : **-103,841.45 ?/an**, m?dian : **-110,358.00 ?/an** ; victoires/d?faites/?galit?s : **8/12/0**.
- Bootstrap IC95 : **[-280,156.30 ; 65,867.90] ?/an** ; Wilcoxon bilat?ral `p=0.3488102`.
- Variation de la valeur d'entreprise (ratio des moyennes) : **-2.683 %**, garde-fou ?5 % **respect?**.
- Verdict : **`fail_primary`**, non adopt? : gain de +4 % non ?tabli, m?me si les 20 paires sont valides et les 40 parties sans ?chec.

## Exposition V259

Analyse de **tous les 20 journaux de variante**, 1990?1999 : **748 d?cisions `V259_BRIDGE`**, toutes en 1995, dont **49 `renew`**, **235 `skip_unprofitable`** et **464 `skip_speed`**. Le m?canisme a donc r?ellement remplac? des ponts apr?s l'introduction du mod?le tubulaire de 1995. Ce fait ne rend pas son effet financier positif.

## Preuves publi?es

Le JSON de r?sultats complet, le manifeste de gel, le flux brut `.jsonl.gz` et les **40 journaux moteur complets en `.log.gz`** (20 r?f?rences + 20 variantes) sont conserv?s dans ce dossier. `file_integrity.json` donne les tailles et empreintes SHA-256 des sources et des fichiers compress?s. Tous les logs sont conserv?s, et aucun n'est un simple extrait. Le dossier des r?sultats de l'?chec pr?alable demeure local dans `results/` ; il ne faut pas confondre le premier run invalide avec cette campagne corrig?e.
