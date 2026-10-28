# ROAD100-14 v3 — filtrer la recherche sur une production complémentaire non nulle

Préréservation supplémentaire du 28 octobre 2026 ; ne remplace pas la
préréservation originale `road100_tour_prereg_20261028.md`.

Les deux smokes 1×3 graine 42 sont sains mais sans exposition. V1
(`road100_tour_v1_smoke_1x3_20261028`) : `OPCAP` vers 106k opcodes,
0 test physique. V2 (`road100_tour_v2_smoke_1x3_20261028`) : évaluation
native unique, `NO_MARGINAL` après **six sites examinés** et ~88,6k
opcodes, toujours 0 test. Ces six sites sont les premières tuiles de
route rencontrées dans l'énumération géométrique et ne démontrent pas
qu'aucune gare A1 ne capterait des voyageurs ailleurs.

## Intervention isolée

Conserver le même rayon Manhattan 6–12, le même classement final
par captation marginale et les mêmes gardes de 3 StationIDs, 4 ordres,
ROI net prudent, caisse et connectivité. La limite **12 candidats**
ne compte désormais que les sites avec production complémentaire
mesurée positive ; les sites non productifs restent refusés mais ne
saturent pas ce quota. Plafonner aussi à 64 les sites routiers
physiquement filtrés par le garde de couverture. Le budget cumulé
reste **100k opcodes soft** et au plus quatre tests `AITestMode`.
Les compteurs distinguent `road_sites_seen` et `positive_candidates`.
Pas d'augmentation du budget, pas de nouveau chemin de construction,
pas de changement OFF.

## Mesures de décision

Smoke apparié graine 42 ×3 ans sur même bundle OFF/ON et inspection
`ROAD100_TOUR`, vrais StationIDs, 4 ordres, revenus réels et profit.
En cas de `NO_MARGINAL`/`OPCAP` sans construction, ne pas déclarer
de succès : étudier séparément un changement de bassin ou des règles
de réseau. Un 5×5 n'est envisagé qu'avec exposition réelle et absence
de panne. Aucun 40×5 avant signal économique et garde valeur ≥−5 %.
