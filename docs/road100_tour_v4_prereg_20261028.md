# ROAD100-14 v4 — cache spatial du marginal, avant nouvelle simulation

Préréservation du 28 octobre 2026. Elle complète, sans les remplacer,
`road100_tour_prereg_20261028.md` et `road100_tour_v3_prereg_20261028.md`.

## Faits observés avant intervention

- Le smoke v3 `road100_tour_v3_smoke_1x3_20261028` sur la graine 42
  donne deux `NO_MARGINAL` et zéro A1.
- Le pilote d'exposition v3 `road100_tour_v3_expo_5x3_20261028`
  donne neuf tentatives, sept `OPCAP` (100 151 à 100 766 ops), deux
  `NO_MARGINAL`, **zéro test station et zéro extension**. Sur les graines
  100, 2026, 7 et 999, plusieurs sites ont pourtant un marginal positif.
- Le calcul par site repasse sur le carré `(2*coverage+1)^2`, avec
  consultations répétées de `covered.HasItem` et `production.HasItem`.
  Cette charge précède les tests de construction et interdit de vérifier
  les 12 sites positifs, malgré une limite de 64 sites physiques.

## Intervention unique v4

Dans `OpexRoad100TryTourAddStop`, conserver la **seule** évaluation native
`production.Valuate(AITile.GetCargoProduction,...)`, le calcul historique
des bassins A0/B0 et toutes les gardes existantes. Après `covered` :

1. Construire une grille numérique de la zone autour de A0 contenant
   uniquement les tuiles productrices **hors couverture A0/B0**, en
   itérant une fois sur `production` (zéro réévaluation de production).
2. Former la somme préfixe bidimensionnelle de cette grille. Pour tout
   site A1, le marginal est la somme rectangulaire exacte dans le rayon
   de couverture, découpée aux limites de la zone et de la carte.
3. Supprimer la double boucle `sx/sy` propre à chaque site candidat.
   Conserver l'ordre spatial déterministe, la séparation des bassins,
   `roadSitesSeen <= 64`, `candidatesChecked <= 12` **positifs** et
   `stationTests <= 4`.
4. Garder `OpexOpsMeasureEnd(mark)` comme garde cumulative 100 000 soft,
   avec refus `OPCAP` distinct ; ne jamais employer le tick restant comme
   budget, ne pas construire si le pré-calcul l'a épuisé. Tracer toujours
   les deux compteurs.

Invariant de calcul : pour chaque tuile admissible, le marginal v4 doit
être égal au marginal v3 (somme des productions positives non couvertes
dans le carré de coverage) ; l'intervention ne change **ni ROI, ni
financement, ni station nouvelle, ni BFS, ni ordres, ni rollback, ni OFF**.

## Qualification et décision

Projection exacte OFF, tests ciblés dont contrat du pré-calcul et contrôle
des bornes, `git diff --check`, puis smoke apparié nouveau bundle
`road100_tour_v4_smoke_1x3_20261028` graine 42. Si aucun marginal sur
42, compléter par une sélection préfixée de graines du précédent 5×3,
qui montraient déjà des sites positifs, sans choisir selon le profit.
Mesurer `ROAD100_TOUR`, `OPCAP`, `NO_MARGINAL`, `CONNECT`, `ROI`,
`TEST_STATION`, vrai A1 (3 StationIDs) et quatre ordres. **Aucun 5×5
économique si aucune conversion réelle sûre**. Toute modification
structurelle supplémentaire exige sa propre hypothèse explicite.

La cible finale reste cinq ratios de profit annuel réalisé Opex/AAAHogEx
>=100 %, un à cinq ans, sans érosion. Le v4 ne prétend pas l'atteindre.
