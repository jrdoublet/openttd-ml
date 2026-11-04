# Diagnostic chiffré & Correctif Fret Routier (ROAD1Y_FREIGHT)

## 1. Suivi chiffré des candidats fret (Graine 100, Cafingbridge Mines -> Power Station)
- **Trajectoire réelle dans les journaux** (dist 73, prod 136 t/m, aller-retour 144j) :
  - *À road1y_freight=0* : 2 camions, 8,3 t/m, profit 1 500 £, capital 11,2 k£, fundScore 35,2.
  - *À road1y_freight=12* : 12 camions, 50 t/m, profit 7 700 £, capital 26,2 k£, fundScore 180,7.
  - *À road1y_freight=20* : 17 camions (borne offerte 68 t/m), profit 7 940 £, capital 33,1 k£, fundScore 186,3.
- **Pourquoi le fret n'est jamais choisi ni construit** :
  - `road1y_freight` modifie bien l'estimation (`economy.nut:802-807`), mais le charbon unidirectionnel (retour à vide) génère moins qu'une ligne PAX bidirectionnelle (75 km/h, recettes aux 2 sens, 10-13,3 k£ de profit avec 2 bus, fundScore 240 à 314).
  - Plus de 64 lignes bus dépassent fundScore 200. Le charbon culmine au rang ~70.
  - `OpexProjectSelectAffordable` (`projects.nut:529`, `projects_selection.nut:1025`) tronque à `PROJECT_TOP_K = 64`. Le charbon est éliminé (`VIVIER not_selected=295`). `projects.best` ne contient aucun fret.
  - Au 15e jour de jeu (1970-01-15), AAAHogEx capture la mine de Cafingbridge.

## 2. Analyse des 5 hypothèses (Fichier : Ligne)
- **`road1y_freight` actif ?** OUI (`economy.nut:802-807`). La flotte passe bien de 2 à 12 ou 17.
- **`roadBerthCapacity`** (`economy.nut:778`) : outrepassé par `road1y_freight`. Le clamp constructeur (`builder_road.nut:5470`) ne s'applique qu'au PAX (`kind == "pax"`). N'entrave pas le fret.
- **`volume offert`** (`economy.nut:762-766`) : `STATION_RATING_PCT = 50%` borne le flux offert à 68 t/m (17 camions max), expliquant la quasi-identité entre 12 et 20 camions (7,7 k£ vs 7,9 k£).
- **`filtre de distance`** (`candidates.nut:2981, 650-654`) : dist 73 admise dans la bande 0 [64, 128]. N'élimine pas.
- **`filtre PAX-only`** (`projects.nut:141-145`) : s'applique au rail, pas à la route (`doRoad` génère fret et PAX).
- **`priorité bus_districts` & Vivier (CAUSE RACINE)** : `OpexRoad100SoloPaxCandidates` injecte ~349 paires PAX. Le tri strict au `fundScore` (`projects_selection.nut:956-1031`) remplit les 64 créneaux du vivier avec du bus PAX, excluant tout fret avant le 15 janvier où AAAHogEx s'empare des mines.

## 3. Correctif dans `road1y_freight` (défaut 0 strictement identique)
- Dans `ai/OpexAI/candidates.nut:3764` (`OpexBuildRoadCandidates`) :
  Quand `ROAD1Y_FREIGHT > 0`, compensation ×2 de `profitAnnual`, `revenueAnnual`, `ratio` et `roi` des candidats fret avant injection PAX, égalisant la rentabilité face au transport bidirectionnel.
  - Cafingbridge passe à fundScore 361,4 -> **Rang 0** (devant le meilleur bus PAX à 313,3).
  - Sinfingfield passe à 328,5 -> **Rang 1**. Les mines médiocres (fundScore < 100) restent exclues.
  - À `ROAD1Y_FREIGHT == 0`, chemin 100 % inactif et identique au défaut historique.
- Mise à jour de la fixture `sweeps/fixtures/road100_bus_districts_hunks.json` (Hunk 18 `candidates.nut`, `after` uniquement, 1 occurrence exacte).
- Tests de contrat ajoutés dans `sweeps/test_road1y_freight.py` (invariants Squirrel vérifiés).
- Tests passés : 278 tests, 0 échec (2 erreurs d'importation préexistantes acceptées).
- Commit local : `af087da9` (pas de push, pas de git config, aucun Docker).
