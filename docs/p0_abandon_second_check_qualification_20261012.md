# P0 — seconde vérification d'abandon incrémentale : qualification du 12/10/2026

**Verdict : NON DÉMONTRÉ, réglage `p0_abandon_second_check_skip=0` maintenu.** Aucun portage en `master`, aucun commit/push, aucune adoption. Ce microcorrectif est indépendant des causes économiques recherchées pour 1973.

## Périmètre et contrat

Stage isolé `results/p0_projects_abandon_stage_20261012` (HEAD de départ `f6139d89`). Dans `OpexIncrementalUpdateProjects`, la vérification pure `OpexCandidateIsAbandoned(p, abandonedPairs)` est déjà effectuée avant `OpexIncrementalCandidateStillValid`, qui appelle `OpexCandidateStillValid` et reproduit la même vérification. ON transmet uniquement à ce callsite l'argument optionnel `abandonAlreadyClear=true` après un premier contrôle négatif ; OFF et tous les autres appels restent identiques. Aucune décision de score, priorisation, cadence, finance, politique modale, air_fleet, C76/C121/V141 ou Save/Load modifiée volontairement. Les trois overlays C121 `air_planning.nut`, `projects_builders.nut`, `probes.nut` copiés dans le stage sont communs aux deux bras et ne sont **pas** un résultat de la microvariante.

Tests hôte réalisés depuis le stage : nouveau contrat de parité modèle **6/6**, 32 768 états testés ; C121 incrémental **8/8** ; AIR0310 incrémental **5/5** ; V141 **6/6** ; C78 **18/18** précédemment mesurés dans ce tour ; `git diff --check` et compilation Python de l'analyseur OK. Le modèle Python ne constitue pas une preuve d'identité exhaustive de la VM Squirrel, mais le smoke moteur a démarré/exécuté les deux réglages.

## Preuves moteur gelées

- Smoke graine42, un an, 2/2 sains, bundle commun `6f4657e035f799123fc1a1df4decda57ccf2ea41fda3404b528679f37bdc5f05` ; gain apparent local +18 403 £/an **non qualifiant**.
- C66 `p0_abandon_skip_b20x10_20261012`, référence OFF vs ON, 20 graines canoniques × 10 ans, 40 duels appariés OpexAI/AAAHogEx, `probe_loop_ops=1` commun, `--script-debug`, `--line-telemetry` annuelle, 10 CPU/10 workers/8 Go, une seule campagne. Bundle identique au smoke ; manifest SHA256 `3ef8ecc766ec738162c648a6ee39cdaaa5bdaa75fb632be912401d8d06676bfa`. **40/40 jeux, 20/20 paires, 80/80 lignes de synthèse sains, zéro échec et zéro `script_errors`**, profit terminal couvert sur quatre trimestres. 800 snapshots de services annuels. Ne pas répéter cette campagne.
- Neuf snapshots de **AAAHogEx uniquement** présentent chacun un véhicule non résolu dans la télémétrie malgré `ok=true`. Les moyennes de services actifs correspondantes excluent ces snapshots (effectif reporté) ; les statistiques économiques C66 restent inchangées. Tous les 400 snapshots Opex sont entièrement résolus.
- Données brutes/manifeste/logs moteur dans le stage `results/p0_projects_abandon_stage_20261012/results/` (fichiers ignorés Git) ; résumé et audit reproductible dans `evidence/review/p0_projects_conversion_20261012/abandon_skip_b20x10_analysis.json` (SHA256 `bbccf36acce0dfc7f89381f970b9e359ec928c2375647b2a1080f12cdca37603`), analyseur `sweeps/analyse_p0_abandon_b20x10.py`.

## Économie B20×10 et comparaison 1973

| ON moins OFF, sur 20 graines | Résultat |
|---|---:|
| Profit annuel terminal 1979, moyenne | **−67 847,35 £/an** (ratio des moyennes **−2,1482 %**) |
| IC95 bootstrap du gain terminal | **[−247 234,45 ; +97 157,80] £/an** |
| Signes profit terminal | 11 favorables / 9 défavorables, Wilcoxon p=0,9854 |
| Valeur compagnie terminale | **−174 623,8 £** (ratio des moyennes **−1,0256 %**) |
| IC95 bootstrap de valeur | [−802 655,9 ; +436 727,95] £ |
| Profit annuel fin 1973 | +28 238,8 £/an en moyenne, **pas une amélioration qualifiée** |

Le harnais rapporte `non_erosion=pass` parce que la borne supérieure bootstrap du profit n'est pas négative et la garde de valeur −5 % est respectée. **Ce PASS de non-érosion n'est ni preuve de gain, ni neutralité stricte, ni autorisation d'adoption.** La cible utile de +4 % n'est pas atteinte, la moyenne terminale est négative, et l'intervalle traverse zéro.

La stagnation de 1973 subsiste : moyenne de profit annuel Opex **référence** 1 925 370 £ en 1972 puis **1 920 910 £** en 1973 ; variante 1 948 518 £ puis **1 949 149 £**. Dans les duels de référence strictement partagés Opex−AAA, écart annuel moyen **−60 028 £** en 1972 puis **−586 453 £** en 1973. L'économie de deux tests Squirrel ne résout pas la conversion des projets en lignes.

## Occupation totale LOOP_OPS, sans double compte

`LOOP_OPS` n'additionne que les catégories *top-level* (`orchestrator`, `catalog_continuation`, événements, sondes communes, etc.), **jamais** les sous-postes `C39`, `SPAN`, `tg_*` ni `sleep_left`. Les années closes disponibles pour 10 ans couvrent **1970–1978** (1979 = année terminale du profit). Cette occupation de fenêtre inclut attentes/commandes ; elle ne vaut **pas** le nombre exact d'instructions VM Squirrel utiles.

| Mesure 1970–1978, par graine | Valeur |
|---|---:|
| OFF, moyenne des top-level occupés | 585 181 442 |
| ON, moyenne | 584 704 840 |
| Delta ON−OFF | **−476 602** (environ **−0,081 %**) |
| IC95 bootstrap delta | **[−2 729 976 ; +1 845 582]** |
| Graines avec baisse / hausse | 13 / 7 |
| Année 1973 seule, delta moyen | −165 922 ; IC95 [−1 338 151 ; +1 080 014] |

**Économie globale NON DÉMONTRÉE** : l'effet est petit, le CI inclut un surcoût et les trajectoires économiques divergent. Le coût intrinsèque à état VM figé n'a pas été isolé ; aucune mesure ne démontre une réduction de famine de nouveaux projets.

## Croissance physique constatée, pas constructions prouvées

Sur le bras OFF en moyenne annuelle, services **actifs** reconstitués : Opex AIR 24,4 (1971), 38,65 (1972), **44,75** (1973) ; RAIL 2,55, 3,05, **4,4** ; ROAD 0,55, 0,8, **1,15**. AAA AIR 12,25, 14,10, **15,84** ; RAIL 5,30, 10,25, **14,95** ; ROAD 14,55, 55,1, **76,74**. Le dénominateur AAA est 19 pour 1973 à cause d'une lacune de résolution ; Opex=20. Ce sont des routes ayant des véhicules et ordres interprétables ; ni leur variation, ni `P5_BUILD_LINE` net ne prouve l'ouverture brute de chantiers indépendants.

## Suite et limites

Conserver OFF. L'économie locale du check dupliqué est logiquement plausible, mais les vérifications supplémentaires Save/Load ON et parité VM exhaustive sont inutiles à une adoption **déjà non qualifiée** et ne sont pas revendiquées. Pas de deuxième 20×10 pour tenter d'obtenir un meilleur hasard. L'investigation P0 doit poursuivre des mécanismes indépendants avec preuve physique transactionnelle avant toute nouvelle A40×3/B20×10 ; ne pas requalifier la stagnation 1973 à partir de cette variante opcode.
