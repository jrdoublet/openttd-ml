# ROAD100-14 v5 — index clairsemé des productions nouvelles

Préréservation du 28 octobre 2026, après le smoke v4 et avant modification
v5. Le budget initial de 100k opcodes, les gardes d'affaires et le protocole
des stations indépendantes restent inchangés.

## Résultat v4 et cause de la nouvelle intervention

`road100_tour_v4_smoke_1x3_20261028` : 2/2 parties saines, mais
2 `OPCAP` (100 409 et 100 661), zéro A1, aucun test de station.
Le calcul de sommes préfixes alloue puis traverse une grille dense
pour une production qui est clairsemée : le coût d'initialisation
devient supérieur au coût évité pour cette carte. Le +701 £/an
apparié n'est **pas** causé par ROAD100-14, qui ne s'est pas exposé.

## Changement isolé

Réutiliser la liste native `production` à évaluation unique. Classer
une fois les tuiles de production **hors couvertures A0/B0** par
colonne x dans une zone bornée au rayon12+coverage autour de A0.
Chaque colonne contient `{y, volume}` seulement si le volume est
positif. Le marginal d'un site est exactement la somme des volumes
de ces colonnes compris dans le rectangle de coverage ; seuls les
points réellement productifs sont parcourus, sans grille dense ni
consultations répétées de `HasItem`.

L'équivalence aux sommes v3/v4 est requise pour toutes les positions,
y compris limites de carte, chevauchements et zones sans production.
Le seul comportement modifié est le coût en opcodes du calcul :
`roadSitesSeen<=64`, au plus 12 positifs, 4 AITestMode,
100k cumulatif soft, stations/ROI/finance/ordres/rollback inchangés.

Tests exacts OFF et statiques, puis smoke `road100_tour_v5_smoke_1x3_20261028`
sur graine42 et, en cas de NO_MARGINAL, diagnostic déterministe 100
qui a présenté des candidats positifs en v3. Aucun 5×5 sans A1 réel
et contrôle de ses ordres. Le but de parité à 1–5 ans n'est pas
déclaré atteint par une simple suppression d'OPCAP.
