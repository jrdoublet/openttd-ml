# Calibration : cout physique et profit, par cargo et quartile de distance

## Methode

* Distances : quartiles **par mode** mesures sur chaque construction unique des 40 parties solo et 40 duel reunies. Les memes seuils sont utilises dans chaque bras. Q0 = tous les quartiles ; Q1 a Q4 = quartiles croissants.
* Cout : comparaison du montant inscrit a PROJECT_CHOSEN et du cout inscrit a RAIL_BUILD / ROAD_BUILD. AIR_BUILD et WATER_BUILD contiennent un devis, **pas un cout physique mesure**. Les couts reels <= 0 et les predictions absentes ou <= 0 sont comptes comme exclusions.
* Profit : profit annuel LINE_REVENUE a age >= 2, normalise par le nombre de vehicules initial (vehs initiaux / vehs actuels) et compare au profit annuel predit BRUT avant C70. Les profits observes negatifs restent inclus.
* Ratio = reel / predit : 1,00 parfait, 0,50 = moitie du predit, 1,50 = +50 %. Erreur abs. mediane en £ par construction ou ligne-annee. Les medians de ratio et des montants ne sont pas necessairement leurs quotients.
* Fiabilite : n < 5 tres faible ; n < 20 indicatif. Les observations ligne-annee d'une meme ligne ne sont pas independantes ; la colonne 'ratio/ligne' pondere chaque ligne une fois.

## Seuils des quartiles (distance du moteur)

| Mode | Q1/Q2 | Q2/Q3 | Q3/Q4 |
|---|---:|---:|---:|
| air | 169.0 | 189.0 | 213.0 |
| rail | 90.0 | 127.0 | 172.0 |
| road | 25.2 | 33.0 | 40.8 |
| water | 58.0 | 66.0 | 142.5 |

## Cout de construction

| Bras | Mode | Cargo | Quartile | n | lignes | ratio med. | IQR ratio | err. abs. med. £ | reel <= 0 | ratio/ligne |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| solo | rail | ALL | total | 985 | 985 | 1.44 | 1.26–1.65 | 23066 | 0 | - |
| solo | rail | ALL | Q1 | 164 | 164 | 1.19 | 1.09–1.34 | 8306 | 0 | - |
| solo | rail | ALL | Q2 | 255 | 255 | 1.37 | 1.22–1.52 | 17400 | 0 | - |
| solo | rail | ALL | Q3 | 292 | 292 | 1.51 | 1.35–1.68 | 27455 | 0 | - |
| solo | rail | ALL | Q4 | 274 | 274 | 1.59 | 1.43–1.79 | 36674 | 0 | - |
| solo | rail | COAL | total | 199 | 199 | 1.39 | 1.21–1.57 | 20940 | 0 | - |
| solo | rail | COAL | Q1 | 36 | 36 | 1.15 | 1.08–1.27 | 8048 | 0 | - |
| solo | rail | COAL | Q2 | 51 | 51 | 1.29 | 1.16–1.49 | 15152 | 0 | - |
| solo | rail | COAL | Q3 | 58 | 58 | 1.48 | 1.31–1.63 | 25266 | 0 | - |
| solo | rail | COAL | Q4 | 54 | 54 | 1.55 | 1.42–1.72 | 33578 | 0 | - |
| solo | rail | GOOD | total | 6 | 6 | 1.32 | 1.21–1.48 | 14698 | 0 | - |
| solo | rail | GOOD | Q1 | 1 | 1 | 1.03 | 1.03–1.03 | 1339 | 0 | - |
| solo | rail | GOOD | Q2 | 3 | 3 | 1.22 | 1.21–1.32 | 10084 | 0 | - |
| solo | rail | GOOD | Q4 | 2 | 2 | 1.57 | 1.54–1.61 | 33972 | 0 | - |
| solo | rail | GRAI | total | 217 | 217 | 1.53 | 1.38–1.72 | 26952 | 0 | - |
| solo | rail | GRAI | Q1 | 23 | 23 | 1.29 | 1.26–1.43 | 12350 | 0 | - |
| solo | rail | GRAI | Q2 | 60 | 60 | 1.42 | 1.31–1.58 | 20497 | 0 | - |
| solo | rail | GRAI | Q3 | 76 | 76 | 1.59 | 1.42–1.72 | 29858 | 0 | - |
| solo | rail | GRAI | Q4 | 58 | 58 | 1.72 | 1.51–1.85 | 41853 | 0 | - |
| solo | rail | IORE | total | 169 | 169 | 1.45 | 1.29–1.66 | 23371 | 0 | - |
| solo | rail | IORE | Q1 | 13 | 13 | 1.16 | 1.11–1.35 | 6885 | 0 | - |
| solo | rail | IORE | Q2 | 51 | 51 | 1.38 | 1.27–1.50 | 17525 | 0 | - |
| solo | rail | IORE | Q3 | 54 | 54 | 1.51 | 1.33–1.68 | 29086 | 0 | - |
| solo | rail | IORE | Q4 | 51 | 51 | 1.55 | 1.36–1.83 | 31455 | 0 | - |
| solo | rail | LVST | total | 39 | 39 | 1.58 | 1.40–1.73 | 31121 | 0 | - |
| solo | rail | LVST | Q1 | 6 | 6 | 1.19 | 1.16–1.32 | 7675 | 0 | - |
| solo | rail | LVST | Q2 | 10 | 10 | 1.57 | 1.41–1.70 | 26432 | 0 | - |
| solo | rail | LVST | Q3 | 10 | 10 | 1.61 | 1.56–1.74 | 32150 | 0 | - |
| solo | rail | LVST | Q4 | 13 | 13 | 1.68 | 1.57–1.92 | 41689 | 0 | - |
| solo | rail | OIL_ | total | 135 | 135 | 1.46 | 1.31–1.68 | 23915 | 0 | - |
| solo | rail | OIL_ | Q1 | 23 | 23 | 1.21 | 1.15–1.36 | 8723 | 0 | - |
| solo | rail | OIL_ | Q2 | 31 | 31 | 1.42 | 1.28–1.47 | 19608 | 0 | - |
| solo | rail | OIL_ | Q3 | 47 | 47 | 1.50 | 1.36–1.76 | 27465 | 0 | - |
| solo | rail | OIL_ | Q4 | 34 | 34 | 1.64 | 1.44–1.80 | 41142 | 0 | - |
| solo | rail | PASS | total | 51 | 51 | 1.12 | 1.04–1.29 | 5542 | 0 | - |
| solo | rail | PASS | Q1 | 45 | 45 | 1.12 | 1.04–1.27 | 5461 | 0 | - |
| solo | rail | PASS | Q2 | 5 | 5 | 1.16 | 1.09–1.38 | 5622 | 0 | - |
| solo | rail | PASS | Q3 | 1 | 1 | 0.80 | 0.80–0.80 | 17235 | 0 | - |
| solo | rail | STEL | total | 1 | 1 | 1.74 | 1.74–1.74 | 28318 | 0 | - |
| solo | rail | STEL | Q1 | 1 | 1 | 1.74 | 1.74–1.74 | 28318 | 0 | - |
| solo | rail | VALU | total | 19 | 19 | 1.41 | 1.19–1.68 | 19327 | 0 | - |
| solo | rail | VALU | Q1 | 6 | 6 | 1.22 | 1.07–1.49 | 9117 | 0 | - |
| solo | rail | VALU | Q2 | 4 | 4 | 1.36 | 1.29–1.51 | 17514 | 0 | - |
| solo | rail | VALU | Q3 | 5 | 5 | 1.65 | 1.17–2.13 | 39032 | 0 | - |
| solo | rail | VALU | Q4 | 4 | 4 | 1.65 | 1.58–1.71 | 38677 | 0 | - |
| solo | rail | WOOD | total | 149 | 149 | 1.40 | 1.25–1.58 | 21941 | 0 | - |
| solo | rail | WOOD | Q1 | 10 | 10 | 1.11 | 1.04–1.21 | 4386 | 0 | - |
| solo | rail | WOOD | Q2 | 40 | 40 | 1.26 | 1.14–1.42 | 12598 | 0 | - |
| solo | rail | WOOD | Q3 | 41 | 41 | 1.42 | 1.33–1.53 | 21941 | 0 | - |
| solo | rail | WOOD | Q4 | 58 | 58 | 1.50 | 1.38–1.64 | 30203 | 0 | - |
| solo | road | ALL | total | 32 | 32 | 1.25 | 0.75–1.41 | 4880 | 0 | - |
| solo | road | ALL | Q1 | 9 | 9 | 1.26 | 1.21–1.40 | 4396 | 0 | - |
| solo | road | ALL | Q2 | 7 | 7 | 1.04 | 0.53–1.37 | 4809 | 0 | - |
| solo | road | ALL | Q3 | 6 | 6 | 1.13 | 0.92–1.52 | 6518 | 0 | - |
| solo | road | ALL | Q4 | 10 | 10 | 1.17 | 0.82–1.39 | 5536 | 0 | - |
| solo | road | COAL | total | 2 | 2 | 1.41 | 1.40–1.41 | 4602 | 0 | - |
| solo | road | COAL | Q1 | 1 | 1 | 1.40 | 1.40–1.40 | 4396 | 0 | - |
| solo | road | COAL | Q2 | 1 | 1 | 1.42 | 1.42–1.42 | 4809 | 0 | - |
| solo | road | GRAI | total | 1 | 1 | 0.26 | 0.26–0.26 | 9302 | 0 | - |
| solo | road | GRAI | Q3 | 1 | 1 | 0.26 | 0.26–0.26 | 9302 | 0 | - |
| solo | road | IORE | total | 1 | 1 | 1.28 | 1.28–1.28 | 3390 | 0 | - |
| solo | road | IORE | Q1 | 1 | 1 | 1.28 | 1.28–1.28 | 3390 | 0 | - |
| solo | road | LVST | total | 2 | 2 | 1.73 | 1.72–1.74 | 8480 | 0 | - |
| solo | road | LVST | Q1 | 1 | 1 | 1.76 | 1.76–1.76 | 8156 | 0 | - |
| solo | road | LVST | Q4 | 1 | 1 | 1.71 | 1.71–1.71 | 8805 | 0 | - |
| solo | road | MAIL | total | 4 | 4 | 1.14 | 0.87–1.34 | 4743 | 0 | - |
| solo | road | MAIL | Q1 | 3 | 3 | 1.26 | 0.85–1.42 | 6431 | 0 | - |
| solo | road | MAIL | Q4 | 1 | 1 | 1.01 | 1.01–1.01 | 191 | 0 | - |
| solo | road | OIL_ | total | 2 | 2 | 1.44 | 1.39–1.49 | 5342 | 0 | - |
| solo | road | OIL_ | Q2 | 1 | 1 | 1.54 | 1.54–1.54 | 6354 | 0 | - |
| solo | road | OIL_ | Q4 | 1 | 1 | 1.34 | 1.34–1.34 | 4329 | 0 | - |
| solo | road | PASS | total | 20 | 20 | 1.01 | 0.67–1.32 | 4734 | 0 | - |
| solo | road | PASS | Q1 | 3 | 3 | 1.21 | 0.83–1.22 | 1775 | 0 | - |
| solo | road | PASS | Q2 | 5 | 5 | 0.71 | 0.34–1.04 | 4515 | 0 | - |
| solo | road | PASS | Q3 | 5 | 5 | 1.28 | 0.98–1.60 | 4148 | 0 | - |
| solo | road | PASS | Q4 | 7 | 7 | 0.99 | 0.66–1.37 | 6119 | 0 | - |
| duel | rail | ALL | total | 1014 | 1014 | 1.47 | 1.27–1.69 | 24291 | 0 | - |
| duel | rail | ALL | Q1 | 248 | 248 | 1.22 | 1.08–1.35 | 9142 | 0 | - |
| duel | rail | ALL | Q2 | 254 | 254 | 1.43 | 1.29–1.61 | 20118 | 0 | - |
| duel | rail | ALL | Q3 | 254 | 254 | 1.56 | 1.41–1.75 | 30488 | 0 | - |
| duel | rail | ALL | Q4 | 258 | 258 | 1.69 | 1.49–1.85 | 41714 | 0 | - |
| duel | rail | COAL | total | 190 | 190 | 1.42 | 1.22–1.62 | 21996 | 0 | - |
| duel | rail | COAL | Q1 | 41 | 41 | 1.18 | 1.09–1.34 | 7917 | 0 | - |
| duel | rail | COAL | Q2 | 51 | 51 | 1.35 | 1.21–1.51 | 17398 | 0 | - |
| duel | rail | COAL | Q3 | 41 | 41 | 1.50 | 1.35–1.69 | 27454 | 0 | - |
| duel | rail | COAL | Q4 | 57 | 57 | 1.61 | 1.45–1.83 | 36040 | 0 | - |
| duel | rail | GOOD | total | 39 | 39 | 1.32 | 1.04–1.60 | 23238 | 0 | - |
| duel | rail | GOOD | Q1 | 5 | 5 | 0.99 | 0.98–1.00 | 1211 | 0 | - |
| duel | rail | GOOD | Q2 | 3 | 3 | 1.60 | 1.37–1.67 | 27557 | 0 | - |
| duel | rail | GOOD | Q3 | 14 | 14 | 1.47 | 1.24–1.58 | 29948 | 0 | - |
| duel | rail | GOOD | Q4 | 17 | 17 | 1.32 | 1.05–1.66 | 23238 | 0 | - |
| duel | rail | GRAI | total | 179 | 179 | 1.56 | 1.39–1.75 | 29788 | 0 | - |
| duel | rail | GRAI | Q1 | 36 | 36 | 1.31 | 1.25–1.38 | 12302 | 0 | - |
| duel | rail | GRAI | Q2 | 50 | 50 | 1.50 | 1.38–1.68 | 24082 | 0 | - |
| duel | rail | GRAI | Q3 | 49 | 49 | 1.61 | 1.50–1.75 | 32773 | 0 | - |
| duel | rail | GRAI | Q4 | 44 | 44 | 1.78 | 1.57–1.95 | 45604 | 0 | - |
| duel | rail | IORE | total | 170 | 170 | 1.49 | 1.30–1.70 | 25388 | 0 | - |
| duel | rail | IORE | Q1 | 22 | 22 | 1.17 | 1.11–1.39 | 8861 | 0 | - |
| duel | rail | IORE | Q2 | 54 | 54 | 1.41 | 1.26–1.52 | 19194 | 0 | - |
| duel | rail | IORE | Q3 | 56 | 56 | 1.54 | 1.36–1.82 | 29357 | 0 | - |
| duel | rail | IORE | Q4 | 38 | 38 | 1.70 | 1.57–1.81 | 39996 | 0 | - |
| duel | rail | LVST | total | 61 | 61 | 1.63 | 1.42–1.84 | 30653 | 0 | - |
| duel | rail | LVST | Q1 | 11 | 11 | 1.35 | 1.28–1.45 | 14712 | 0 | - |
| duel | rail | LVST | Q2 | 17 | 17 | 1.55 | 1.42–1.67 | 27918 | 0 | - |
| duel | rail | LVST | Q3 | 11 | 11 | 1.82 | 1.46–2.02 | 45349 | 0 | - |
| duel | rail | LVST | Q4 | 22 | 22 | 1.78 | 1.74–1.89 | 47799 | 0 | - |
| duel | rail | OIL_ | total | 129 | 129 | 1.53 | 1.31–1.81 | 28427 | 0 | - |
| duel | rail | OIL_ | Q1 | 25 | 25 | 1.23 | 1.12–1.44 | 10101 | 0 | - |
| duel | rail | OIL_ | Q2 | 33 | 33 | 1.46 | 1.25–1.68 | 23511 | 0 | - |
| duel | rail | OIL_ | Q3 | 39 | 39 | 1.62 | 1.48–1.82 | 34164 | 0 | - |
| duel | rail | OIL_ | Q4 | 32 | 32 | 1.77 | 1.55–1.90 | 47212 | 0 | - |
| duel | rail | PASS | total | 91 | 91 | 1.17 | 1.05–1.41 | 7021 | 0 | - |
| duel | rail | PASS | Q1 | 88 | 88 | 1.15 | 1.05–1.39 | 6136 | 0 | - |
| duel | rail | PASS | Q2 | 3 | 3 | 1.60 | 1.60–1.64 | 27061 | 0 | - |
| duel | rail | STEL | total | 4 | 4 | 1.51 | 1.43–1.63 | 22964 | 0 | - |
| duel | rail | STEL | Q2 | 2 | 2 | 1.51 | 1.48–1.55 | 22684 | 0 | - |
| duel | rail | STEL | Q3 | 2 | 2 | 1.58 | 1.49–1.67 | 34972 | 0 | - |
| duel | rail | VALU | total | 4 | 4 | 1.48 | 1.39–1.63 | 28204 | 0 | - |
| duel | rail | VALU | Q2 | 3 | 3 | 1.42 | 1.37–1.65 | 21083 | 0 | - |
| duel | rail | VALU | Q4 | 1 | 1 | 1.55 | 1.55–1.55 | 35326 | 0 | - |
| duel | rail | WOOD | total | 147 | 147 | 1.46 | 1.26–1.64 | 24796 | 0 | - |
| duel | rail | WOOD | Q1 | 20 | 20 | 1.12 | 1.05–1.22 | 5168 | 0 | - |
| duel | rail | WOOD | Q2 | 38 | 38 | 1.38 | 1.17–1.47 | 18399 | 0 | - |
| duel | rail | WOOD | Q3 | 42 | 42 | 1.53 | 1.42–1.68 | 29108 | 0 | - |
| duel | rail | WOOD | Q4 | 47 | 47 | 1.62 | 1.44–1.77 | 36007 | 0 | - |
| duel | road | ALL | total | 49 | 49 | 1.17 | 0.45–1.42 | 5440 | 0 | - |
| duel | road | ALL | Q1 | 14 | 14 | 1.04 | 0.33–1.26 | 3118 | 0 | - |
| duel | road | ALL | Q2 | 10 | 10 | 1.33 | 0.49–1.64 | 6650 | 0 | - |
| duel | road | ALL | Q3 | 17 | 17 | 1.17 | 0.54–1.44 | 5615 | 0 | - |
| duel | road | ALL | Q4 | 8 | 8 | 1.11 | 0.52–1.26 | 5178 | 0 | - |
| duel | road | COAL | total | 4 | 4 | 1.27 | 1.22–1.36 | 3142 | 0 | - |
| duel | road | COAL | Q1 | 1 | 1 | 1.52 | 1.52–1.52 | 5665 | 0 | - |
| duel | road | COAL | Q2 | 1 | 1 | 1.31 | 1.31–1.31 | 3546 | 0 | - |
| duel | road | COAL | Q3 | 2 | 2 | 1.20 | 1.18–1.22 | 2392 | 0 | - |
| duel | road | GRAI | total | 5 | 5 | 0.58 | 0.36–0.72 | 7684 | 0 | - |
| duel | road | GRAI | Q2 | 3 | 3 | 0.72 | 0.54–1.31 | 7684 | 0 | - |
| duel | road | GRAI | Q3 | 1 | 1 | 0.20 | 0.20–0.20 | 10131 | 0 | - |
| duel | road | GRAI | Q4 | 1 | 1 | 0.58 | 0.58–0.58 | 5505 | 0 | - |
| duel | road | IORE | total | 6 | 6 | 0.77 | 0.48–1.16 | 6048 | 0 | - |
| duel | road | IORE | Q1 | 2 | 2 | 0.70 | 0.57–0.83 | 3554 | 0 | - |
| duel | road | IORE | Q3 | 2 | 2 | 1.43 | 1.00–1.85 | 11294 | 0 | - |
| duel | road | IORE | Q4 | 2 | 2 | 0.71 | 0.45–0.97 | 7118 | 0 | - |
| duel | road | MAIL | total | 3 | 3 | 0.18 | 0.11–0.77 | 10205 | 0 | - |
| duel | road | MAIL | Q1 | 1 | 1 | 0.05 | 0.05–0.05 | 11200 | 0 | - |
| duel | road | MAIL | Q3 | 1 | 1 | 0.18 | 0.18–0.18 | 10205 | 0 | - |
| duel | road | MAIL | Q4 | 1 | 1 | 1.37 | 1.37–1.37 | 4851 | 0 | - |
| duel | road | OIL_ | total | 4 | 4 | 0.39 | 0.20–0.67 | 7290 | 0 | - |
| duel | road | OIL_ | Q2 | 1 | 1 | 0.23 | 0.23–0.23 | 8964 | 0 | - |
| duel | road | OIL_ | Q3 | 2 | 2 | 0.32 | 0.21–0.43 | 8212 | 0 | - |
| duel | road | OIL_ | Q4 | 1 | 1 | 1.06 | 1.06–1.06 | 746 | 0 | - |
| duel | road | PASS | total | 19 | 19 | 1.20 | 0.97–1.50 | 4618 | 0 | - |
| duel | road | PASS | Q1 | 8 | 8 | 1.12 | 0.83–1.22 | 2428 | 0 | - |
| duel | road | PASS | Q2 | 4 | 4 | 1.63 | 1.31–1.76 | 7026 | 0 | - |
| duel | road | PASS | Q3 | 6 | 6 | 1.40 | 1.01–1.51 | 6086 | 0 | - |
| duel | road | PASS | Q4 | 1 | 1 | 1.17 | 1.17–1.17 | 2564 | 0 | - |
| duel | road | WOOD | total | 8 | 8 | 1.36 | 0.90–1.42 | 5496 | 0 | - |
| duel | road | WOOD | Q1 | 2 | 2 | 0.82 | 0.56–1.10 | 5266 | 0 | - |
| duel | road | WOOD | Q2 | 1 | 1 | 1.36 | 1.36–1.36 | 4495 | 0 | - |
| duel | road | WOOD | Q3 | 3 | 3 | 1.42 | 1.25–1.43 | 5362 | 0 | - |
| duel | road | WOOD | Q4 | 2 | 2 | 1.14 | 0.75–1.53 | 10421 | 0 | - |

## Profit annuel

| Bras | Mode | Cargo | Quartile | n | lignes | ratio med. | IQR ratio | err. abs. med. £ | reel <= 0 | ratio/ligne |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| solo | air | ALL | total | 15608 | 2448 | 0.31 | 0.21–0.49 | 62307 | 98 | 0.32 |
| solo | air | ALL | Q1 | 3880 | 635 | 0.32 | 0.21–0.52 | 49148 | 24 | 0.33 |
| solo | air | ALL | Q2 | 3845 | 626 | 0.33 | 0.22–0.52 | 49798 | 26 | 0.34 |
| solo | air | ALL | Q3 | 3891 | 608 | 0.31 | 0.21–0.49 | 62681 | 24 | 0.32 |
| solo | air | ALL | Q4 | 3992 | 579 | 0.30 | 0.20–0.43 | 91620 | 24 | 0.29 |
| solo | air | PASS | total | 15608 | 2448 | 0.31 | 0.21–0.49 | 62307 | 98 | 0.32 |
| solo | air | PASS | Q1 | 3880 | 635 | 0.32 | 0.21–0.52 | 49148 | 24 | 0.33 |
| solo | air | PASS | Q2 | 3845 | 626 | 0.33 | 0.22–0.52 | 49798 | 26 | 0.34 |
| solo | air | PASS | Q3 | 3891 | 608 | 0.31 | 0.21–0.49 | 62681 | 24 | 0.32 |
| solo | air | PASS | Q4 | 3992 | 579 | 0.30 | 0.20–0.43 | 91620 | 24 | 0.29 |
| solo | rail | ALL | total | 5857 | 1037 | 1.17 | 0.83–1.57 | 9482 | 363 | 1.24 |
| solo | rail | ALL | Q1 | 1326 | 222 | 0.91 | 0.63–1.19 | 4752 | 93 | 0.92 |
| solo | rail | ALL | Q2 | 1488 | 260 | 1.11 | 0.83–1.41 | 8276 | 91 | 1.14 |
| solo | rail | ALL | Q3 | 1614 | 287 | 1.29 | 0.93–1.62 | 12938 | 102 | 1.32 |
| solo | rail | ALL | Q4 | 1429 | 268 | 1.42 | 1.07–1.77 | 17268 | 77 | 1.45 |
| solo | rail | COAL | total | 1405 | 244 | 1.11 | 0.75–1.49 | 13931 | 54 | 1.18 |
| solo | rail | COAL | Q1 | 480 | 75 | 0.84 | 0.65–1.03 | 8026 | 15 | 0.85 |
| solo | rail | COAL | Q2 | 334 | 59 | 1.10 | 0.75–1.38 | 12044 | 11 | 1.11 |
| solo | rail | COAL | Q3 | 318 | 58 | 1.39 | 1.16–1.67 | 22218 | 17 | 1.35 |
| solo | rail | COAL | Q4 | 273 | 52 | 1.50 | 1.11–1.85 | 27171 | 11 | 1.51 |
| solo | rail | GOOD | total | 31 | 6 | 1.27 | 0.38–1.94 | 7300 | 5 | 1.32 |
| solo | rail | GOOD | Q1 | 6 | 1 | 0.43 | 0.13–0.96 | 8374 | 0 | 0.43 |
| solo | rail | GOOD | Q2 | 17 | 3 | 1.81 | 0.71–2.03 | 6218 | 4 | 1.37 |
| solo | rail | GOOD | Q4 | 8 | 2 | 1.45 | 0.61–2.50 | 12025 | 1 | 1.88 |
| solo | rail | GRAI | total | 1240 | 219 | 1.21 | 0.92–1.59 | 8361 | 62 | 1.26 |
| solo | rail | GRAI | Q1 | 150 | 26 | 1.03 | 0.84–1.18 | 2870 | 1 | 1.03 |
| solo | rail | GRAI | Q2 | 343 | 59 | 1.12 | 0.89–1.41 | 6490 | 8 | 1.14 |
| solo | rail | GRAI | Q3 | 432 | 76 | 1.31 | 0.96–1.64 | 9442 | 26 | 1.34 |
| solo | rail | GRAI | Q4 | 315 | 58 | 1.37 | 1.06–1.75 | 14537 | 27 | 1.40 |
| solo | rail | IORE | total | 1033 | 178 | 1.25 | 0.94–1.59 | 8472 | 43 | 1.30 |
| solo | rail | IORE | Q1 | 136 | 22 | 1.02 | 0.86–1.33 | 3256 | 3 | 1.02 |
| solo | rail | IORE | Q2 | 305 | 52 | 1.19 | 0.91–1.48 | 7914 | 23 | 1.21 |
| solo | rail | IORE | Q3 | 314 | 54 | 1.29 | 0.99–1.60 | 9926 | 7 | 1.30 |
| solo | rail | IORE | Q4 | 278 | 50 | 1.45 | 1.05–1.75 | 14002 | 10 | 1.45 |
| solo | rail | LVST | total | 213 | 41 | 1.34 | 0.90–1.75 | 8794 | 11 | 1.38 |
| solo | rail | LVST | Q1 | 46 | 8 | 1.23 | 0.56–1.52 | 5705 | 0 | 1.31 |
| solo | rail | LVST | Q2 | 52 | 10 | 1.02 | 0.66–1.30 | 6276 | 7 | 0.96 |
| solo | rail | LVST | Q3 | 54 | 10 | 1.50 | 1.14–1.75 | 10142 | 2 | 1.43 |
| solo | rail | LVST | Q4 | 61 | 13 | 1.71 | 1.43–2.00 | 18885 | 2 | 1.50 |
| solo | rail | OIL_ | total | 719 | 133 | 1.07 | 0.69–1.42 | 7715 | 60 | 1.09 |
| solo | rail | OIL_ | Q1 | 115 | 21 | 0.87 | 0.56–1.14 | 3092 | 11 | 0.85 |
| solo | rail | OIL_ | Q2 | 170 | 31 | 1.01 | 0.75–1.25 | 5738 | 9 | 1.06 |
| solo | rail | OIL_ | Q3 | 257 | 47 | 1.06 | 0.57–1.42 | 9188 | 31 | 1.05 |
| solo | rail | OIL_ | Q4 | 177 | 34 | 1.33 | 1.02–1.74 | 13110 | 9 | 1.48 |
| solo | rail | PASS | total | 227 | 44 | 0.57 | -0.15–2.33 | 4289 | 73 | 0.45 |
| solo | rail | PASS | Q1 | 205 | 40 | 0.61 | -0.26–2.47 | 4144 | 62 | 0.52 |
| solo | rail | PASS | Q2 | 17 | 3 | -0.05 | -0.15–1.60 | 12597 | 9 | -0.12 |
| solo | rail | PASS | Q3 | 5 | 1 | 0.06 | -0.00–0.15 | 23015 | 2 | 0.06 |
| solo | rail | STEL | total | 6 | 1 | 2.94 | 2.85–4.87 | 3508 | 0 | 2.94 |
| solo | rail | STEL | Q1 | 6 | 1 | 2.94 | 2.85–4.87 | 3508 | 0 | 2.94 |
| solo | rail | VALU | total | 6 | 4 | 2.34 | 1.11–2.70 | 45546 | 1 | 1.55 |
| solo | rail | VALU | Q1 | 1 | 1 | -7.49 | -7.49–-7.49 | 3267 | 1 | -7.49 |
| solo | rail | VALU | Q2 | 1 | 1 | 0.77 | 0.77–0.77 | 16742 | 0 | 0.77 |
| solo | rail | VALU | Q3 | 2 | 1 | 2.34 | 2.25–2.44 | 45546 | 0 | 2.34 |
| solo | rail | VALU | Q4 | 2 | 1 | 2.78 | 2.77–2.79 | 57014 | 0 | 2.78 |
| solo | rail | WOOD | total | 977 | 167 | 1.21 | 0.88–1.62 | 11233 | 54 | 1.29 |
| solo | rail | WOOD | Q1 | 181 | 27 | 0.91 | 0.71–1.23 | 4766 | 0 | 0.91 |
| solo | rail | WOOD | Q2 | 249 | 42 | 1.13 | 0.86–1.46 | 10190 | 20 | 1.18 |
| solo | rail | WOOD | Q3 | 232 | 40 | 1.39 | 0.94–1.76 | 15474 | 17 | 1.43 |
| solo | rail | WOOD | Q4 | 315 | 58 | 1.38 | 1.05–1.72 | 20078 | 17 | 1.41 |
| solo | road | ALL | total | 350 | 57 | 0.40 | 0.17–1.00 | 5221 | 6 | 0.28 |
| solo | road | ALL | Q1 | 82 | 14 | 0.67 | 0.23–1.00 | 2238 | 2 | 0.63 |
| solo | road | ALL | Q2 | 91 | 16 | 0.48 | 0.18–1.03 | 4356 | 0 | 0.43 |
| solo | road | ALL | Q3 | 57 | 9 | 0.48 | 0.19–0.77 | 9533 | 0 | 0.21 |
| solo | road | ALL | Q4 | 120 | 18 | 0.25 | 0.12–1.01 | 11008 | 4 | 0.25 |
| solo | road | COAL | total | 34 | 5 | 1.07 | 0.89–1.74 | 1488 | 0 | 1.01 |
| solo | road | COAL | Q1 | 7 | 1 | 0.79 | 0.79–0.79 | 1524 | 0 | 0.79 |
| solo | road | COAL | Q2 | 13 | 2 | 1.14 | 0.89–1.31 | 783 | 0 | 1.10 |
| solo | road | COAL | Q4 | 14 | 2 | 1.79 | 1.01–1.89 | 2677 | 0 | 1.40 |
| solo | road | GOOD | total | 2 | 1 | -0.36 | -0.36–-0.36 | 3159 | 2 | -0.36 |
| solo | road | GOOD | Q1 | 2 | 1 | -0.36 | -0.36–-0.36 | 3159 | 2 | -0.36 |
| solo | road | GRAI | total | 14 | 2 | 1.15 | 1.09–1.25 | 600 | 0 | 1.15 |
| solo | road | GRAI | Q2 | 7 | 1 | 1.14 | 1.10–1.18 | 563 | 0 | 1.14 |
| solo | road | GRAI | Q3 | 7 | 1 | 1.16 | 1.10–1.26 | 642 | 0 | 1.16 |
| solo | road | IORE | total | 7 | 1 | 0.63 | 0.53–0.64 | 2554 | 0 | 0.63 |
| solo | road | IORE | Q1 | 7 | 1 | 0.63 | 0.53–0.64 | 2554 | 0 | 0.63 |
| solo | road | LVST | total | 26 | 4 | 1.64 | 1.45–2.14 | 995 | 0 | 1.53 |
| solo | road | LVST | Q1 | 12 | 2 | 1.57 | 1.25–1.64 | 912 | 0 | 1.38 |
| solo | road | LVST | Q3 | 7 | 1 | 2.22 | 2.02–2.22 | 1726 | 0 | 2.22 |
| solo | road | LVST | Q4 | 7 | 1 | 1.45 | 1.45–1.93 | 749 | 0 | 1.45 |
| solo | road | MAIL | total | 44 | 7 | 0.86 | 0.56–1.19 | 1616 | 2 | 0.72 |
| solo | road | MAIL | Q1 | 24 | 4 | 0.73 | 0.32–1.06 | 1902 | 0 | 0.70 |
| solo | road | MAIL | Q2 | 7 | 1 | 0.66 | 0.64–0.98 | 1636 | 0 | 0.66 |
| solo | road | MAIL | Q4 | 13 | 2 | 1.12 | 0.93–1.30 | 1371 | 2 | 0.92 |
| solo | road | OIL_ | total | 13 | 2 | 0.48 | 0.39–1.07 | 2633 | 2 | 0.70 |
| solo | road | OIL_ | Q2 | 7 | 1 | 0.98 | 0.39–1.11 | 2633 | 0 | 0.98 |
| solo | road | OIL_ | Q4 | 6 | 1 | 0.42 | -0.07–0.65 | 3788 | 2 | 0.42 |
| solo | road | PASS | total | 201 | 33 | 0.20 | 0.12–0.34 | 12766 | 0 | 0.20 |
| solo | road | PASS | Q1 | 30 | 5 | 0.23 | 0.18–0.65 | 3666 | 0 | 0.22 |
| solo | road | PASS | Q2 | 48 | 9 | 0.19 | 0.11–0.39 | 11378 | 0 | 0.20 |
| solo | road | PASS | Q3 | 43 | 7 | 0.21 | 0.14–0.50 | 15443 | 0 | 0.21 |
| solo | road | PASS | Q4 | 80 | 12 | 0.18 | 0.11–0.27 | 15577 | 0 | 0.15 |
| solo | road | WOOD | total | 9 | 2 | 1.05 | 0.98–1.17 | 262 | 0 | 1.09 |
| solo | road | WOOD | Q2 | 9 | 2 | 1.05 | 0.98–1.17 | 262 | 0 | 1.09 |
| duel | air | ALL | total | 12272 | 1892 | 0.24 | 0.16–0.40 | 71274 | 128 | 0.24 |
| duel | air | ALL | Q1 | 2833 | 448 | 0.25 | 0.16–0.43 | 57984 | 32 | 0.25 |
| duel | air | ALL | Q2 | 3017 | 478 | 0.26 | 0.16–0.42 | 57969 | 49 | 0.26 |
| duel | air | ALL | Q3 | 3116 | 481 | 0.24 | 0.16–0.39 | 75763 | 32 | 0.25 |
| duel | air | ALL | Q4 | 3306 | 485 | 0.23 | 0.15–0.35 | 92805 | 15 | 0.23 |
| duel | air | PASS | total | 12272 | 1892 | 0.24 | 0.16–0.40 | 71274 | 128 | 0.24 |
| duel | air | PASS | Q1 | 2833 | 448 | 0.25 | 0.16–0.43 | 57984 | 32 | 0.25 |
| duel | air | PASS | Q2 | 3017 | 478 | 0.26 | 0.16–0.42 | 57969 | 49 | 0.26 |
| duel | air | PASS | Q3 | 3116 | 481 | 0.24 | 0.16–0.39 | 75763 | 32 | 0.25 |
| duel | air | PASS | Q4 | 3306 | 485 | 0.23 | 0.15–0.35 | 92805 | 15 | 0.23 |
| duel | rail | ALL | total | 5502 | 1030 | 0.99 | 0.62–1.37 | 8581 | 350 | 1.04 |
| duel | rail | ALL | Q1 | 1629 | 278 | 0.76 | 0.44–1.10 | 5819 | 101 | 0.80 |
| duel | rail | ALL | Q2 | 1385 | 254 | 0.95 | 0.65–1.25 | 7578 | 94 | 0.97 |
| duel | rail | ALL | Q3 | 1309 | 249 | 1.14 | 0.79–1.46 | 10063 | 83 | 1.14 |
| duel | rail | ALL | Q4 | 1179 | 249 | 1.16 | 0.78–1.54 | 13287 | 72 | 1.18 |
| duel | rail | COAL | total | 1253 | 225 | 0.86 | 0.53–1.17 | 12701 | 50 | 0.91 |
| duel | rail | COAL | Q1 | 458 | 73 | 0.66 | 0.46–0.89 | 10456 | 5 | 0.66 |
| duel | rail | COAL | Q2 | 318 | 57 | 0.81 | 0.59–1.12 | 12090 | 12 | 0.83 |
| duel | rail | COAL | Q3 | 211 | 40 | 1.12 | 0.79–1.48 | 16827 | 16 | 1.06 |
| duel | rail | COAL | Q4 | 266 | 55 | 1.14 | 0.83–1.55 | 20202 | 17 | 1.28 |
| duel | rail | GOOD | total | 162 | 37 | 0.49 | 0.17–0.83 | 47576 | 29 | 0.55 |
| duel | rail | GOOD | Q1 | 29 | 5 | 0.25 | 0.05–0.31 | 85829 | 6 | 0.29 |
| duel | rail | GOOD | Q2 | 16 | 3 | 0.98 | 0.42–7.14 | 19716 | 3 | 0.81 |
| duel | rail | GOOD | Q3 | 58 | 12 | 0.58 | 0.15–0.94 | 42950 | 11 | 0.56 |
| duel | rail | GOOD | Q4 | 59 | 17 | 0.58 | 0.21–0.80 | 29140 | 9 | 0.60 |
| duel | rail | GRAI | total | 954 | 180 | 0.95 | 0.64–1.30 | 7079 | 63 | 1.00 |
| duel | rail | GRAI | Q1 | 223 | 40 | 0.86 | 0.47–1.22 | 3886 | 12 | 0.93 |
| duel | rail | GRAI | Q2 | 267 | 49 | 0.82 | 0.57–1.08 | 7063 | 24 | 0.85 |
| duel | rail | GRAI | Q3 | 259 | 49 | 1.07 | 0.79–1.38 | 7293 | 12 | 1.10 |
| duel | rail | GRAI | Q4 | 205 | 42 | 1.10 | 0.69–1.41 | 11251 | 15 | 1.08 |
| duel | rail | IORE | total | 986 | 176 | 1.13 | 0.80–1.44 | 7490 | 42 | 1.16 |
| duel | rail | IORE | Q1 | 181 | 30 | 0.88 | 0.54–1.21 | 5359 | 1 | 0.95 |
| duel | rail | IORE | Q2 | 311 | 54 | 1.07 | 0.79–1.38 | 6726 | 21 | 1.10 |
| duel | rail | IORE | Q3 | 313 | 56 | 1.25 | 0.97–1.46 | 9005 | 16 | 1.29 |
| duel | rail | IORE | Q4 | 181 | 36 | 1.28 | 0.93–1.70 | 11620 | 4 | 1.31 |
| duel | rail | LVST | total | 267 | 59 | 0.93 | 0.64–1.31 | 6250 | 22 | 0.96 |
| duel | rail | LVST | Q1 | 64 | 13 | 0.75 | 0.38–1.35 | 7389 | 4 | 0.74 |
| duel | rail | LVST | Q2 | 82 | 17 | 0.86 | 0.64–1.18 | 5496 | 8 | 0.86 |
| duel | rail | LVST | Q3 | 44 | 10 | 1.10 | 0.87–1.30 | 4471 | 0 | 1.09 |
| duel | rail | LVST | Q4 | 77 | 19 | 1.10 | 0.79–1.37 | 8878 | 10 | 1.13 |
| duel | rail | OIL_ | total | 617 | 130 | 1.04 | 0.63–1.42 | 8459 | 58 | 1.06 |
| duel | rail | OIL_ | Q1 | 124 | 26 | 0.76 | 0.44–1.02 | 4394 | 10 | 0.80 |
| duel | rail | OIL_ | Q2 | 160 | 33 | 0.95 | 0.57–1.24 | 6225 | 21 | 1.02 |
| duel | rail | OIL_ | Q3 | 182 | 39 | 1.13 | 0.73–1.56 | 9253 | 18 | 1.06 |
| duel | rail | OIL_ | Q4 | 151 | 32 | 1.34 | 1.06–1.66 | 13316 | 9 | 1.32 |
| duel | rail | PASS | total | 289 | 52 | 1.28 | 0.21–3.05 | 3334 | 57 | 1.10 |
| duel | rail | PASS | Q1 | 289 | 52 | 1.28 | 0.21–3.05 | 3334 | 57 | 1.10 |
| duel | rail | STEL | total | 18 | 4 | 1.11 | 0.48–4.32 | 6106 | 1 | 1.46 |
| duel | rail | STEL | Q2 | 9 | 2 | 4.54 | 2.45–5.15 | 5474 | 1 | 3.79 |
| duel | rail | STEL | Q3 | 9 | 2 | 0.49 | 0.45–0.51 | 6527 | 0 | 0.49 |
| duel | rail | VALU | total | 5 | 2 | 1.45 | 0.99–2.29 | 15387 | 0 | 1.61 |
| duel | rail | VALU | Q2 | 2 | 1 | 0.93 | 0.90–0.96 | 2664 | 0 | 0.93 |
| duel | rail | VALU | Q4 | 3 | 1 | 2.29 | 1.87–2.45 | 44063 | 0 | 2.29 |
| duel | rail | WOOD | total | 951 | 165 | 1.09 | 0.74–1.42 | 9851 | 28 | 1.12 |
| duel | rail | WOOD | Q1 | 261 | 39 | 0.80 | 0.51–1.10 | 7242 | 6 | 0.82 |
| duel | rail | WOOD | Q2 | 220 | 38 | 1.14 | 0.84–1.51 | 8370 | 4 | 1.18 |
| duel | rail | WOOD | Q3 | 233 | 41 | 1.22 | 0.89–1.49 | 11129 | 10 | 1.26 |
| duel | rail | WOOD | Q4 | 237 | 47 | 1.21 | 0.88–1.53 | 12211 | 8 | 1.21 |
| duel | road | ALL | total | 372 | 58 | 0.87 | 0.17–1.62 | 2712 | 26 | 0.82 |
| duel | road | ALL | Q1 | 92 | 14 | 0.21 | 0.04–0.68 | 3876 | 16 | 0.10 |
| duel | road | ALL | Q2 | 81 | 13 | 0.88 | 0.24–1.68 | 2542 | 0 | 0.59 |
| duel | road | ALL | Q3 | 121 | 19 | 0.87 | 0.12–1.68 | 3429 | 10 | 0.99 |
| duel | road | ALL | Q4 | 78 | 12 | 1.53 | 1.15–2.02 | 2336 | 0 | 1.41 |
| duel | road | COAL | total | 24 | 4 | 1.59 | 1.17–1.71 | 2084 | 0 | 1.48 |
| duel | road | COAL | Q1 | 7 | 1 | 1.06 | 1.05–1.25 | 415 | 0 | 1.06 |
| duel | road | COAL | Q2 | 7 | 1 | 1.35 | 1.06–1.65 | 1252 | 0 | 1.35 |
| duel | road | COAL | Q3 | 10 | 2 | 1.71 | 1.63–1.88 | 2446 | 0 | 1.73 |
| duel | road | GRAI | total | 36 | 6 | 1.82 | 1.13–1.96 | 2039 | 0 | 1.77 |
| duel | road | GRAI | Q2 | 19 | 3 | 1.13 | 0.92–1.73 | 984 | 0 | 1.12 |
| duel | road | GRAI | Q3 | 6 | 1 | 1.82 | 1.82–1.95 | 2042 | 0 | 1.82 |
| duel | road | GRAI | Q4 | 11 | 2 | 2.05 | 1.87–2.06 | 2405 | 0 | 1.97 |
| duel | road | IORE | total | 53 | 8 | 1.42 | 1.01–1.65 | 1803 | 4 | 1.38 |
| duel | road | IORE | Q1 | 12 | 2 | 0.46 | -0.28–0.57 | 3414 | 4 | 0.13 |
| duel | road | IORE | Q3 | 14 | 2 | 1.43 | 1.28–1.75 | 1336 | 0 | 1.61 |
| duel | road | IORE | Q4 | 27 | 4 | 1.47 | 1.15–1.73 | 1472 | 0 | 1.40 |
| duel | road | MAIL | total | 35 | 5 | 0.27 | 0.07–0.95 | 3869 | 6 | 0.18 |
| duel | road | MAIL | Q1 | 14 | 2 | 0.05 | -0.05–0.12 | 4436 | 6 | 0.03 |
| duel | road | MAIL | Q3 | 7 | 1 | 0.18 | 0.13–0.29 | 3869 | 0 | 0.18 |
| duel | road | MAIL | Q4 | 14 | 2 | 1.06 | 0.81–1.28 | 1234 | 0 | 1.03 |
| duel | road | OIL_ | total | 23 | 4 | 1.12 | 1.05–1.82 | 887 | 0 | 1.24 |
| duel | road | OIL_ | Q2 | 7 | 1 | 1.05 | 0.70–1.05 | 219 | 0 | 1.05 |
| duel | road | OIL_ | Q3 | 11 | 2 | 1.12 | 1.12–1.82 | 1381 | 0 | 1.48 |
| duel | road | OIL_ | Q4 | 5 | 1 | 1.35 | 1.16–1.93 | 887 | 0 | 1.35 |
| duel | road | PASS | total | 139 | 22 | 0.15 | 0.06–0.31 | 9417 | 16 | 0.11 |
| duel | road | PASS | Q1 | 45 | 7 | 0.09 | 0.03–0.24 | 5684 | 6 | 0.09 |
| duel | road | PASS | Q2 | 34 | 6 | 0.20 | 0.13–0.34 | 6662 | 0 | 0.17 |
| duel | road | PASS | Q3 | 53 | 8 | 0.10 | 0.04–0.23 | 11634 | 10 | 0.10 |
| duel | road | PASS | Q4 | 7 | 1 | 0.38 | 0.35–0.54 | 9099 | 0 | 0.38 |
| duel | road | WOOD | total | 62 | 9 | 1.71 | 1.25–1.95 | 1993 | 0 | 1.71 |
| duel | road | WOOD | Q1 | 14 | 2 | 0.96 | 0.79–1.21 | 363 | 0 | 1.04 |
| duel | road | WOOD | Q2 | 14 | 2 | 1.71 | 1.71–1.83 | 1993 | 0 | 1.77 |
| duel | road | WOOD | Q3 | 20 | 3 | 1.60 | 1.27–1.91 | 1747 | 0 | 1.60 |
| duel | road | WOOD | Q4 | 14 | 2 | 2.16 | 2.00–2.16 | 2971 | 0 | 2.16 |

## Exclusions

| Bras | Compteur | n |
|---|---|---:|
| solo | cost_eligible_rail | 1070 |
| solo | cost_eligible_road | 59 |
| solo | cost_no_valid_prediction | 85 |
| solo | cost_nonpositive_actual | 27 |
| solo | cost_unobservable_air | 2492 |
| solo | cost_unobservable_water | 8 |
| solo | games | 40 |
| solo | profit_no_vehicles | 123 |
| solo | profit_nonpositive_prediction | 60 |
| duel | cost_eligible_rail | 1088 |
| duel | cost_eligible_road | 59 |
| duel | cost_no_valid_prediction | 74 |
| duel | cost_nonpositive_actual | 10 |
| duel | cost_unobservable_air | 1932 |
| duel | cost_unobservable_water | 7 |
| duel | games | 40 |
| duel | profit_no_vehicles | 232 |
| duel | profit_nonpositive_prediction | 57 |
