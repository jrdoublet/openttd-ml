# DIST-BORNES-1 — inventaire des bornes de distance (23/10)

Branche `dist-bornes-1` (depuis `origin/master` `6ccab033`). Lecture du code + journal
`decision_log` du smoke `po03_c77defer_smoke_1x1_20261022` (graine 42, 256², bras référence).
Aucun changement de comportement à ce stade.

## Calcul central : `OpexRefreshEpochBounds` (`candidates.nut:350-435`)

Valeurs journalisées (`EPOCH_BOUNDS`, 1970-1-2, graine 42) :

| Borne | Valeur | Origine |
|---|---:|---|
| `roadMin` | 7 | 2 × rayon arrêt de bus + 1 |
| `roadMax` | **7** | bascule route→rail `OpexComputeRoadToRailDistance` ; retombe sur `roadMin` |
| `roadGenMax` | 200 | horizon de transit du bus (2,5 × horizon / jours par tuile), plafonné à `railMax` |
| `railMin` | **7** | = `roadMax` |
| `railMax` | 200 | table A* (`OpexRailDistanceForIterations`) **écrasée** par `V168_RAIL_MAX_DIST`=160, **puis** par `V294_RAIL_DIST_DECOUPLE`=200 |
| `railAirOverlapMin` | 200 | bascule rail→avion `tFixe/(τrail−τair)`, **plafonnée à `railMax`** |
| `airMin` | **200** | = `railAirOverlapMin` |
| `airMax` | 512 | rentabilité calendaire > étendue de carte → étendue (256+256) |

## Défauts constatés

1. **Pas de bande route.** `roadMax = roadMin = 7` : le modèle de bascule route/rail rend une
   distance < 7 (capital fixe rail amorti dès le bassin, avec toute la production de la ville
   transportée et un ROI cible de 40 %), donc le rail est autorisé dès 7 tuiles. La route ne vit
   que par `roadGenMax` (jusqu'à 200 tuiles en bus), qui ignore la bascule.
2. **`railMax` écrasé deux fois.** Trois sources successives (table, V168, V294) ; la dernière
   gagne silencieusement. V269 (250) peut encore la dépasser pour le fret tardif.
3. **`airMin` = `railMax` par construction.** La bascule rail→avion est plafonnée à `railMax` :
   l'avion en bande `PAX_BAND_ALL` (`OpexAirPairInBand`) exige donc ≥ 200 tuiles Manhattan sur
   une carte de 512. Projets AIR choisis sur la graine 42 : 154-278 tuiles (34 projets) ; ceux
   sous 200 passent par d'autres chemins (bandes AIR_RAIL/hubs) — à confirmer.
   Bornes AIR parallèles non reliées : `AIR_TOWN_MIN_DISTANCE`=32, `minDist` 30/32 selon la
   vitesse (`air_planning.nut:1869`, copie `po01c_generators.nut:1685`), `AIR_MAX_DISTANCE`=0.
4. **`airMax` inopérant** : toujours l'étendue de carte à 256².
5. **Bornes secondaires** : `V177_RAIL_PAX_MIN_DIST`, `V182_RAIL_FREIGHT_MIN_DIST` (+ V195),
   `ROAD_PAX_VOIRIE_SAME_TOWN_MAX_DIST`=12, `WATER_TOWN_MIN_DISTANCE`=45, repli statique
   `candidates.nut:446-452` (avant catalogue). Subventions : `roadMin..roadGenMax`.

## Consommateurs

`OpexAirPairInBand` (air_planning ×3), `OpexRailPaxPairInBand` (candidats rail pax, V276,
PO-01c), filtre rail `candidates.nut:631-645` (+ copie `po01c_generators.nut:2279-2293`),
V233 `goods_v233.nut:304`, V276 `candidates_v276.nut:137`, subventions `candidates.nut:2090`.

## Suite proposée

1. Mesurer sur 5-10 graines (journal `EPOCH_BOUNDS` + distances des projets choisis/rejetés par
   mode) pour confirmer 1 et 3 hors graine 42 et dans le temps (bascules qui bougent avec les
   moteurs).
2. Un seul jeu de bornes par mode, calculé à un seul endroit ; les réglages V168/V294/V269
   deviennent des paramètres de ce calcul, pas des écrasements.
3. Revoir le modèle de bascule route/rail (production transportée, ROI cible) et ne plus
   plafonner la bascule rail/avion à `railMax` ; aligner les `minDist` AIR.
4. Comportement changé ⇒ protocole V102 (porte A 40×3) ; défaut inchangé sans qualification.
