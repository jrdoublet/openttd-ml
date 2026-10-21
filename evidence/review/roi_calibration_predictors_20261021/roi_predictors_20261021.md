# Variables predictives du ROI annuel, calibration PC 40x10

Methode : une observation par ligne, profit median des annees age >=2,
normalise a la flotte initiale, divise par capital physique RAIL/ROAD
ou par le devis AIR (aucun cout physique AIR dans les journaux).
Prediction de depart : profit prevu / capital prevu, en pourcentage annuel.
Evaluation supervisee : 5 plis par graines disjointes, bras duel uniquement.
Modeles ridge fixes, sans optimisation de l'hyperparametre sur le test.
Les variables subtype/reuse viennent du plan journalise a la construction ;
leur disponibilite au choix doit etre verifiee dans le constructeur.

Attention : correction ne vaut que pour les lignes construites, avec suivi
jusqu'a age 2. Quartiler sur le ROI reel amplifie la regression vers
la moyenne par construction. Aucune causalite n'est demontree ici.

## AIR : 1892 lignes en duel

| Modele | MAE ROI (points) | Median abs. (points) | Biais median (points) | Rang intra-graine rho |
|---|---:|---:|---:|---:|
| raw | 119.34 | 121.39 | 121.39 | 0.706 |
| factor | 15.5 | 12.73 | 0.02 | 0.706 |
| affine_roi | 14.93 | 12.4 | 3.22 | 0.706 |
| roi_quadratic | 14.47 | 11.75 | 3.28 | 0.706 |
| plus_distance | 14.52 | 11.76 | 3.02 | 0.709 |
| plus_cargo | 14.47 | 11.75 | 3.28 | 0.706 |
| plus_capital | 14.1 | 11.11 | 3.19 | 0.75 |
| plus_year | 14.41 | 11.51 | 3.33 | 0.711 |
| plus_rank | 14.48 | 11.72 | 3.24 | 0.723 |
| plus_subtype | 13.78 | 10.74 | 3.3 | 0.74 |
| all_available | 13.88 | 10.81 | 3.01 | 0.735 |

### Effets additionnels vs ROI seul quadratique (graines bootstrappees)

| Ajout | Gain MAE moyen par graine (points, positif=mieux) | IC95 | Graines favorables |
|---|---:|---:|---:|
| raw | -104.79 | -110.92 a -98.25 | 0/40 |
| factor | -1.08 | -1.51 a -0.64 | 7/40 |
| affine_roi | -0.47 | -0.59 a -0.34 | 4/40 |
| plus_distance | -0.05 | -0.1 a 0.0 | 16/40 |
| plus_cargo | 0.0 | 0.0 a 0.0 | 0/40 |
| plus_capital | 0.4 | 0.21 a 0.6 | 33/40 |
| plus_year | 0.07 | -0.01 a 0.14 | 21/40 |
| plus_rank | -0.01 | -0.05 a 0.02 | 23/40 |
| plus_subtype | 0.72 | 0.51 a 0.94 | 33/40 |
| all_available | 0.61 | 0.36 a 0.84 | 31/40 |

### by_predicted_roi_quartile

| Quartile | N lignes | ROI prevu % | ROI reel % | Profit reel/predit | Distance med. |
|---|---:|---:|---:|---:|---:|
| Q1 | 473 | 37.3 | 20.19 | 0.56 | 184.0 |
| Q2 | 473 | 116.79 | 26.66 | 0.226 | 184.0 |
| Q3 | 473 | 191.03 | 38.28 | 0.195 | 191.0 |
| Q4 | 473 | 276.8 | 64.52 | 0.231 | 207.0 |

### by_realized_roi_quartile

| Quartile | N lignes | ROI prevu % | ROI reel % | Profit reel/predit | Distance med. |
|---|---:|---:|---:|---:|---:|
| Q1 | 473 | 64.01 | 14.47 | 0.175 | 186.0 |
| Q2 | 473 | 132.82 | 27.56 | 0.204 | 186.0 |
| Q3 | 473 | 183.97 | 42.54 | 0.233 | 190.0 |
| Q4 | 473 | 264.71 | 70.73 | 0.296 | 204.0 |

### Sous-groupes descriptifs

- subtype : hubhub: {'n': 700, 'roi_pred_pct': 114.3, 'roi_real_pct': 36.8, 'profit_ratio': 0.326}; hubsite: {'n': 972, 'roi_pred_pct': 168.8, 'roi_real_pct': 31.5, 'profit_ratio': 0.214}; newpair: {'n': 220, 'roi_pred_pct': 223.4, 'roi_real_pct': 44.7, 'profit_ratio': 0.195}


## RAIL : 958 lignes en duel

| Modele | MAE ROI (points) | Median abs. (points) | Biais median (points) | Rang intra-graine rho |
|---|---:|---:|---:|---:|
| raw | 25.12 | 18.57 | 18.14 | 0.711 |
| factor | 14.02 | 9.58 | 0.04 | 0.711 |
| affine_roi | 14.16 | 10.65 | 1.71 | 0.711 |
| roi_quadratic | 13.4 | 10.07 | 1.59 | 0.711 |
| plus_distance | 13.32 | 9.64 | 1.38 | 0.711 |
| plus_cargo | 12.55 | 9.13 | 1.1 | 0.747 |
| plus_capital | 13.24 | 9.71 | 1.29 | 0.721 |
| plus_year | 13.39 | 9.79 | 1.74 | 0.701 |
| plus_rank | 13.49 | 10.59 | 1.42 | 0.706 |
| plus_subtype | 13.47 | 10.0 | 1.61 | 0.713 |
| all_available | 12.48 | 8.88 | 0.93 | 0.744 |

### Effets additionnels vs ROI seul quadratique (graines bootstrappees)

| Ajout | Gain MAE moyen par graine (points, positif=mieux) | IC95 | Graines favorables |
|---|---:|---:|---:|
| raw | -11.74 | -13.28 a -10.07 | 1/40 |
| factor | -0.57 | -1.17 a 0.01 | 14/40 |
| affine_roi | -0.7 | -0.97 a -0.44 | 11/40 |
| plus_distance | 0.07 | -0.11 a 0.25 | 23/40 |
| plus_cargo | 0.79 | 0.35 a 1.21 | 32/40 |
| plus_capital | 0.14 | 0.03 a 0.25 | 30/40 |
| plus_year | -0.01 | -0.23 a 0.19 | 20/40 |
| plus_rank | -0.08 | -0.19 a 0.02 | 15/40 |
| plus_subtype | -0.06 | -0.12 a -0.0 | 15/40 |
| all_available | 0.86 | 0.35 a 1.37 | 30/40 |

### by_predicted_roi_quartile

| Quartile | N lignes | ROI prevu % | ROI reel % | Profit reel/predit | Distance med. |
|---|---:|---:|---:|---:|---:|
| Q1 | 239 | 28.44 | 15.34 | 1.031 | 93.0 |
| Q2 | 240 | 48.49 | 31.58 | 1.049 | 148.0 |
| Q3 | 239 | 64.46 | 42.62 | 0.996 | 142.0 |
| Q4 | 240 | 93.38 | 58.08 | 0.836 | 130.5 |

### by_realized_roi_quartile

| Quartile | N lignes | ROI prevu % | ROI reel % | Profit reel/predit | Distance med. |
|---|---:|---:|---:|---:|---:|
| Q1 | 239 | 31.05 | 12.89 | 0.671 | 98.0 |
| Q2 | 240 | 49.42 | 28.61 | 0.905 | 136.5 |
| Q3 | 239 | 61.12 | 42.88 | 1.077 | 140.0 |
| Q4 | 240 | 82.44 | 64.78 | 1.109 | 149.0 |

### Sous-groupes descriptifs

- cargo : COAL: {'n': 187, 'roi_pred_pct': 89.2, 'roi_real_pct': 55.5, 'profit_ratio': 0.921}; GOOD: {'n': 37, 'roi_pred_pct': 160.0, 'roi_real_pct': 34.4, 'profit_ratio': 0.36}; GRAI: {'n': 176, 'roi_pred_pct': 50.1, 'roi_real_pct': 26.8, 'profit_ratio': 0.878}; IORE: {'n': 167, 'roi_pred_pct': 54.2, 'roi_real_pct': 36.3, 'profit_ratio': 1.07}; LVST: {'n': 57, 'roi_pred_pct': 41.2, 'roi_real_pct': 23.2, 'profit_ratio': 0.896}; OIL_: {'n': 128, 'roi_pred_pct': 45.8, 'roi_real_pct': 30.3, 'profit_ratio': 0.946}; PASS: {'n': 54, 'roi_pred_pct': 7.3, 'roi_real_pct': 7.9, 'profit_ratio': 1.423}; WOOD: {'n': 146, 'roi_pred_pct': 65.2, 'roi_real_pct': 48.5, 'profit_ratio': 1.101}

- subtype : freight: {'n': 904, 'roi_pred_pct': 57.2, 'roi_real_pct': 36.4, 'profit_ratio': 0.971}; pax: {'n': 54, 'roi_pred_pct': 7.3, 'roi_real_pct': 7.9, 'profit_ratio': 1.423}

- reuse : 0: {'n': 581, 'roi_pred_pct': 59.2, 'roi_real_pct': 35.3, 'profit_ratio': 0.933}; 1: {'n': 377, 'roi_pred_pct': 51.7, 'roi_real_pct': 34.9, 'profit_ratio': 1.012}


## ROAD : 48 lignes en duel

| Modele | MAE ROI (points) | Median abs. (points) | Biais median (points) | Rang intra-graine rho |
|---|---:|---:|---:|---:|
| raw | 62.4 | 46.4 | 2.64 | -0.6 |
| factor | 61.42 | 50.43 | 0.63 | -0.6 |
| affine_roi | 44.83 | 31.76 | 21.92 | 0.6 |
| roi_quadratic | 43.14 | 28.93 | 19.64 | 0.6 |
| plus_distance | 43.92 | 30.49 | 21.81 | 0.2 |
| plus_cargo | 42.77 | 32.68 | 18.2 | 1.0 |
| plus_capital | 42.76 | 32.99 | 19.97 | 0.3 |
| plus_year | 46.81 | 31.4 | 22.37 | 0.7 |
| plus_rank | 44.87 | 31.8 | 22.11 | 0.2 |
| plus_subtype | 42.77 | 32.68 | 18.2 | 1.0 |
| all_available | 52.93 | 43.43 | 21.45 | 0.3 |

### Effets additionnels vs ROI seul quadratique (graines bootstrappees)

| Ajout | Gain MAE moyen par graine (points, positif=mieux) | IC95 | Graines favorables |
|---|---:|---:|---:|
| raw | -17.46 | -30.72 a -5.13 | 10/29 |
| factor | -16.0 | -28.44 a -5.64 | 8/29 |
| affine_roi | -1.63 | -3.07 a -0.47 | 10/29 |
| plus_distance | -0.34 | -5.63 a 4.81 | 14/29 |
| plus_cargo | 2.24 | -1.55 a 6.26 | 13/29 |
| plus_capital | 1.3 | -3.16 a 5.91 | 12/29 |
| plus_year | -5.24 | -10.61 a -0.82 | 11/29 |
| plus_rank | -1.65 | -3.84 a 0.14 | 10/29 |
| plus_subtype | 2.24 | -1.59 a 6.3 | 13/29 |
| all_available | -10.82 | -20.38 a -3.03 | 11/29 |

### by_predicted_roi_quartile

| Quartile | N lignes | ROI prevu % | ROI reel % | Profit reel/predit | Distance med. |
|---|---:|---:|---:|---:|---:|
| Q1 | 12 | 19.92 | 31.33 | 1.786 | 37.0 |
| Q2 | 12 | 27.03 | 36.0 | 1.388 | 37.0 |
| Q3 | 12 | 39.45 | 23.31 | 0.449 | 27.5 |
| Q4 | 12 | 127.86 | 14.54 | 0.111 | 34.5 |

### by_realized_roi_quartile

| Quartile | N lignes | ROI prevu % | ROI reel % | Profit reel/predit | Distance med. |
|---|---:|---:|---:|---:|---:|
| Q1 | 12 | 80.28 | 5.35 | 0.087 | 25.0 |
| Q2 | 12 | 36.25 | 20.05 | 1.091 | 36.5 |
| Q3 | 12 | 32.48 | 33.73 | 1.21 | 35.0 |
| Q4 | 12 | 25.23 | 106.57 | 1.483 | 36.0 |

### Sous-groupes descriptifs

- subtype : freight: {'n': 30, 'roi_pred_pct': 24.8, 'roi_real_pct': 35.5, 'profit_ratio': 1.35}; pax: {'n': 18, 'roi_pred_pct': 89.0, 'roi_real_pct': 12.7, 'profit_ratio': 0.111}


## Couverture et limites

{
  "solo": {
    "games": 40,
    "built_air": 2492,
    "matched_air": 2492,
    "built_rail": 1070,
    "unmatched_choice_rail": 85,
    "built_road": 59,
    "matched_road": 32,
    "matched_rail": 985,
    "mature_air": 2448,
    "mature_road": 32,
    "mature_rail": 954,
    "no_mature": 75,
    "invalid_physical_cost": 27
  },
  "duel": {
    "games": 40,
    "built_air": 1932,
    "matched_air": 1930,
    "built_rail": 1088,
    "unmatched_choice_rail": 74,
    "matched_rail": 1014,
    "built_road": 59,
    "matched_road": 49,
    "mature_air": 1892,
    "mature_rail": 958,
    "mature_road": 48,
    "no_mature": 95,
    "invalid_physical_cost": 10,
    "invalid_prediction": 2
  }
}

La validation par graines isole les parties, mais ne corrige pas
le biais de selection du catalogue. Les conditions de production,
saturation, demande concurrente, stations, vitesse et utilisation
ne sont pas journalisees au moment du choix dans ces traces.
