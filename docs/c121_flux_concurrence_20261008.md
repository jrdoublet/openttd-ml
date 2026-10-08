# C121 — concurrence entre compagnies, audit du 8 octobre 2026

Le partage explicite du modèle courant ne contient pas la concurrence adverse.
Cela donne une direction de surestimation pour une source effectivement partagée,
mais le diagnostic géométrique disponible ne suffit pas à mesurer sa contribution
aux erreurs de demande. Aucune correction de flotte ou de défaut n'est adoptée.

## Code courant et mécanisme moteur

`air_coverage.nut::OpexC121StationCompetitionBuckets` énumère
`AIStationList(STATION_ANY)`, donc les stations de notre compagnie seulement.
`OpexC121StationAllocatedMonthly` alloue la production selon le meilleur rating
Opex puis le partage entre nos stations. Les chemins économiques complets et
de sélection moteur utilisent cette allocation.

Une compensation indirecte existe : `projects_models.nut::OpexC121RealizationFactor`
corrige les revenus des bras hubsite/hubhub. Au défaut adaptatif1, elle applique
25 % de l'écart appris, si une observation suffisante existe. Elle peut modifier
le classement et la flotte choisie, mais ne mesure pas une capture par station.
Elle laisse newpair à1. Les corrections expérimentales engine-only et project
non adaptatif restent à0. Ne pas les réactiver ou étendre implicitement à newpair.

Dans le moteur, pour chaque source couverte, la répartition est faite entre
compagnies puis entre stations d'une compagnie. Pour la candidate Opex :

- P : production de la source avant rating ; r : rating de la candidate.
- a : meilleur rating Opex éligible sur cette source, candidate comprise.
- S : somme des ratings Opex éligibles, candidate comprise.
- B : somme des meilleurs ratings des autres compagnies éligibles sur la source.
- M : meilleur rating toutes compagnies confondues.

À l'arrondi/fractions de cargo près, le moteur attribue
`P × (M+1)/256 × a/(a+B) × r/S` à la candidate. L'allocation ignorant les autres
compagnies donne `P × (a+1)/256 × r/S`. Le rapport moteur/modèle est
`q = (M+1)/(a+1) × a/(a+B)` : q=1 sans rival, q<1 avec un rival éligible.

Exemple théorique : P=1 000, une station Opex et une AAA de rating200, même source
couverte. Modèle sans AAA : environ785 PASS/mois Opex ; moteur : environ393.
Ce facteur deux ne s'applique qu'aux sources partagées de cet exemple, pas à
toute la demande d'une station ni directement au nombre d'avions.

Le rating adverse peut relever M : appliquer seulement a/(a+B) au modèle
existant serait incorrect. Le moteur utilise le maximum par compagnie à la
première étape, pas la somme de tous ses ratings.

Sources primaires : [répartition moteur 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station_cmd.cpp#L4238),
[portée d'AIStationList](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_stationlist.cpp#L15),
[restriction de lecture des ratings adverses](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_station.cpp#L18).
L'IA ne peut donc pas reproduire exactement ce partage par une simple lecture
des stations/ratings d'AAAHogEx. Le test Python de la formule est un contrôle
mathématique, pas une observation du moteur en partie.

## Diagnostic géométrique hors ligne

Réutilisation de la campagne figée `c121_town_flux_10x10_20261008`, dix duels
de dix ans complets/sains ; aucune nouvelle partie. Même sélection de 522 cas
de prévision que l'analyse du supply : labels exacts mais années partielles,
stations issues de nouvelles paires, oracle externe pour la vérité reçue.
Le proxy initial ne reproduit pas l'économie C121 complète.

Pour chaque station/ancre, prendre la géométrie des aéroports actifs PASS des
deux compagnies dans les douze mois précédant l'ancre, au moins huit observations.
Dédoublonner les stations apparaissant sur plusieurs routes. Classer selon le
recouvrement possible des rectangles d'aéroport dilatés de 4, 6 ou 10 cases.
Ces trois valeurs sont des sensibilités, pas une prétention au catchment exact.
Les stations non-AIR adverses et les installations jointes sont absentes.
Même un recouvrement des zones ne prouve pas qu'elles contiennent une maison
productrice partagée. Le classement utilise seulement la période passée.

Graines réservées73/314/512, sept autres pour développement. Aucun coefficient
appris, aucun verdict causal, pas de bootstrap sur les cas répétés d'une station.

| Dilatation | Cas réservés avec / sans contact potentiel | WAPE avec / sans | Biais avec / sans | Surestimation >50 %, avec / sans |
|---|---:|---:|---:|---:|
| 4 | 108 / 74 | 40,43 % / 31,72 % | +13,00 % / −11,81 % | 34/108 / 10/74 |
| 6 | 160 / 22 | 37,54 % / 25,18 % | +2,17 % / +13,49 % | 41/160 / 3/22 |
| 10 | 170 / 12 | 37,20 % / 24,29 % | +2,81 % / +2,67 % | 43/170 / 1/12 |

À quatre cases, le lot réservé présente davantage de fortes surestimations au
contact potentiel, mais le développement ne reproduit pas ce contraste :
33/190 contre27/150, biais−2,58 % contre−2,46 %. Le biais comparé change aussi
de sens à six cases. Les groupes restants à six/dix cases sont petits et les
cas se répètent dans les mêmes stations. **Signal descriptif non robuste** :
ne pas annoncer la concurrence comme cause principale établie, ne pas calibrer
une réduction sur ce classement géométrique.

Provenance commune, contrôlée par l'analyse partagée :

- Bundle `544c5411596da3922fd2160940125b868abfbbbe3a5b0db5f2aa9b3cf33cbb27`.
- Manifeste `593f5687f3bcf68b0f7c5ecf7a0c7ddce6aee158af4258cc2858f8a08d938010`.
- Checkpoints `62bd810065a08bc3f49c10c348767ec6086793b766d3e5cff29e0a7cede102e3`.
- Analyse `results/c121_town_flux_20261008/diag_10x10/air_contact_analysis.json`,
  empreintes des logs inclues. Script `sweeps/analyse_c121_air_contact.py`.

## Suite isolée et critères

Mesurer le recouvrement des **producteurs** avec toutes les installations
adverses, et non la seule proximité d'aéroports : mêmes sources et mêmes
géométries dans le modèle témoin/corrigé, seule l'allocation intercompagnies
varie. Respecter l'éligibilité moteur, notamment station ayant essayé de charger,
rating non nul, types d'installation et éventuelle exclusivité. Valider contre
les intervalles LGRP qualifiés, sans injecter ces données cachées dans NoAI.

Un estimateur utilisable par l'IA doit ensuite apprendre une capture locale
depuis ses propres observations qualifiées. Il devra distinguer demande reçue,
débit transporté censuré par la capacité, variation de stock et pertes, et
conserver le total d'une station lorsqu'il le partage entre ses routes.
Le dénominateur municipal B9 constitue une piste indépendante à mesurer,
sans attribution prématurée de toutes les erreurs à la concurrence.

Validation : trois tests ciblés (allocation par compagnie, conservation du
total, géométrie/bords, services non cotés et dédoublonnage), analyse complète
des checkpoints existants et contrôle du diff. Pas de modification Squirrel,
donc pas de nouvelle compilation/smoke nécessaire pour cet audit hors ligne.
