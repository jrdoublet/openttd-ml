# C85 — frontière statique d'équipement AIR

État au 2026-09-23 : **prototype terminé, non adopté**, réglage `c85_air_equipment_frontier=0` par défaut.

## 1. But

Le choix C68 est économiquement simple mais coûteux en génération : pour chaque route,
`OpexAirChooseRoutePlaneFull()` reparcourt les avions compatibles de
`catalog.airPlaneChoicesByAirport[airport.type]` et réévalue `OpexAirEconomics`.

C72 (ROI / score C69) et C82 (calibration par moteur) n'ont pas franchi leur qualification
économique. C85 ne cherche donc **pas un nouvel objectif de choix d'avion** : il cherche à obtenir
le même optimum C68 avec moins d'évaluations.

## 2. Contrat

Au refresh AIR, la liste complète reste intacte. C85 construit en parallèle
`airPlaneFrontierByAirport`, par type d'aéroport.

Un avion `A` ne peut éliminer `B` que si, simultanément :

- capacité `A >= B` ;
- vitesse `A >= B` ;
- prix d'achat `A <= B` ;
- coût d'exploitation `A <= B` ;
- portée de `A` couvrant toute la portée de `B` ;
- au moins une de ces dimensions est strictement meilleure.

La convention historique est conservée : `maxOrderDistance <= 0` signifie portée illimitée.
La compatibilité petit/grand aéroport est déjà résolue avant le pruning puisque chaque frontier
est construite à partir de la liste compatible du type d'aéroport concerné.

Ce critère est volontairement conservateur. Dans le modèle C68 courant, vitesse/capacité plus
grandes ne peuvent dégrader ni le débit ni le revenu transporté, tandis que prix et running cost
plus faibles ne peuvent dégrader ni capital, amortissement ni exploitation. Un avion retiré ne
peut donc pas être le meilleur profit de la route face à son dominateur.

`OpexAirChooseRoutePlaneFull()` utilise cette frontier uniquement quand :

```text
c85_air_equipment_frontier = 1
c72_plane_choice = 0
c82_engine_calibration = 0
```

Les expériences C72/C82 et les probes M3 conservent la liste complète. Le `selectedPlane`
historique reste également évalué avant la frontier, même s'il est structurellement dominé.

## 3. Ce qui n'a pas été fait

C85 n'implémente pas la table fixe `SMALL/STANDARD/HEAVY` proposée pendant l'analyse :

- aucun EngineID vanilla n'est codé en dur ;
- aucun seuil arbitraire `80/250 pax` n'est introduit ;
- la distance et la demande restent dans `OpexAirEconomics` ;
- le Yate Haugan / Concorde n'est pas exclu par nom ;
- une configuration avec portées limitées reste correcte.

Le catalogue 1970 mesuré historiquement contient 13 moteurs AIR
(`results/catalogue_churn.json`). Le pruning sûr n'enlève qu'une partie des évaluations, ce qui
explique que le gain mesuré reste nettement plus petit que l'hypothèse d'une table O(1) à trois rôles.

## 4. Validation

Tests :

- `sweeps.test_c85_air_equipment_frontier` : **5/5** ;
- `sweeps.test_m3_equipment_roi` : **7/7** ;
- `sweeps.test_campaign_freeze` : **11/11** ;
- régressions C84 + B8 : **12/12** ;
- `git diff --check` : propre.

Smoke C85, graine 42 × 1 an :
`results/smoke_c85_air_equipment_frontier_1x1_20260923.json`.
La partie est saine et termine à 351 035 £/an de `profit_year`, contre 269 731 £/an au smoke
défaut correspondant. Ce gain économique sur une seule graine n'est pas une preuve.

Avant divergence physique, février 1970 donne une comparaison opcode propre :

- défaut : 9 759 opcodes AIR, 2 échantillons ;
- C85 : 9 397 opcodes AIR, 2 échantillons ;
- soit **−3,7 %** à physique identique.

Une mesure dédiée 5 graines × 1 an,
`results/diag_c85_opcode_5x1_20260923.json`, donne en moyenne :

- coût AIR par échantillon : **5 188 → 4 779 opcodes**, soit environ **−7,9 %** ;
- médiane par échantillon : **5 220 → 4 993**, soit environ **−4,4 %**.

Le total d'opcodes de compagnie n'est pas une mesure causale du coût du helper après divergence :
C85 construit parfois davantage et déclenche alors davantage de sélection, de projets et de
construction. Sur ce 5×1, le total observé est même supérieur dans le bras C85 pour cette raison.

## 5. Diagnostic économique 5×6

Campagne :
`results/diag_c85_air_equipment_frontier_5x6_20260923.json`.

Graines `100 12345 42 7 999`, 6 ans, 3 workers / 3 CPU / 2 Go, 10/10 parties complètes.
Seul `c85_air_equipment_frontier` diffère entre contrôle et traitement.

Résultat C85 − défaut :

- `profit_year` : **−24,5 k£/an** moyen ;
- médiane : **−68,1 k£/an** ;
- V/D/E : **2/3/0**, p signes `1,0` ;
- IC95 : **[−197,9 ; +149,0] k£/an** ;
- valeur : ratio des moyennes **−2,69 %**, donc garde −5 % respectée.

Par graine, le delta `profit_year` vaut environ :

- 100 : **+251,1 k£/an** ;
- 12345 : **+92,8 k£/an** ;
- 42 : **−68,1 k£/an** ;
- 7 : **−154,0 k£/an** ;
- 999 : **−244,2 k£/an**.

Le résultat est compatible avec un effet économique faible dominé par les bifurcations de timing :
la frontier change le coût opcode et donc le moment où certaines décisions deviennent exécutables,
mais elle ne change pas l'objectif économique C68.

## 6. Décision

C85 reste **expérimental à défaut 0** et aucun 20×10 n'est lancé :

- le seuil économique préfixé `+50 k£/an` n'est pas atteint ;
- le gain opcode local est réel mais modeste (environ 4–8 % du planning AIR par passe) ;
- il ne justifie pas de remplacer le comportement courant sans bénéfice global mesuré.

La conclusion sur le choix d'avion est donc importante : **le scan complet n'est pas le gros
goulot imaginé**. Une frontier mathématiquement sûre retire du travail, mais pas assez pour changer
le profil global. Aller plus loin exigerait soit une short-list approximative de rôles, soit une
borne de profit route-spécifique ; ces variantes changeraient le contrat de sûreté et doivent être
mesurées comme un nouveau chantier, pas durcies silencieusement dans C85.
