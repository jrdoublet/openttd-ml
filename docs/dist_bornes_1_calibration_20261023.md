# DIST-BORNES-1 — calibration RAIL/AIR, 23 octobre 2026

Diagnostic hors partie sur `dist-bornes-1-diag`, arbre initial propre
`e805725f22ad6b8a6ca6225ed0fc4947d9886e06`. Aucun changement de comportement,
aucune partie, aucun Docker, aucun push. Ce diagnostic ne qualifie aucun défaut.

## Résultat principal

Le capital réel RAIL / devis au choix monte de **1,125 à 1,292 puis 1,558**
avec la distance. Sur le dénominateur `RAIL_ATTEMPT.pre`, disponible pour toutes
les constructions, les médianes sont **1,137 / 1,277 / 1,558**. Il existe donc
un écart de capital sur les lignes construites de ces journaux, mais **pas de
preuve d'une surestimation du profit rail voyageurs à longue distance** :
les **10 RAIL PASS** sont toutes sous 80 tuiles et **aucun RAIL n'a de rapport
mature**. Les 168 autres RAIL sont du fret ; ils ne calibrent pas la frontière PASS.

AIR : le profit opératoire normalisé / profit prédit au choix vaut **0,452**
à 140–200 et **0,408** à 200+, sur 124 lignes matures. Ce ratio mélange deux
conventions comptables et ne suffit pas à corriger un modèle. Le capital réel
AIR n'est pas publié dans les événements lus. **Impossible de conclure au
croisement économique rail/avion vers 140 tuiles**, et encore moins jusqu'à 400.

## Sources et reproduction

Les deux dossiers, en lecture seule, sont sous
`/home/deploy/.claude/jobs/e230de46/tmp/wt_dist/results/` :
`dist_bornes_mesure_8x3_20261023_engine` (8 journaux) et
`dist_bornes_slow_3x3_20261023_engine` (3 journaux).
Les campagnes restent distinctes : mêmes graines éventuelles ≠ observations
indépendantes supplémentaires. Leur agrégation ci-dessous est descriptive,
sans IC ni test causal. Les noms des dossiers ne valident pas santé/horizon ;
ce script ne remplace pas `game_health.py` ni les manifestes du harnais.

```bash
python3 sweeps/diag_calib_rail_air.py   /home/deploy/.claude/jobs/e230de46/tmp/wt_dist/results/dist_bornes_mesure_8x3_20261023_engine   /home/deploy/.claude/jobs/e230de46/tmp/wt_dist/results/dist_bornes_slow_3x3_20261023_engine   --out results/dist_calib_tmp/calibration.json
```

Le JSON contient chaque construction, champs prédits aux différents stades,
coût réel quand disponible, références aux lignes du journal, tous les rapports
annuels (y compris immatures), rapport mature retenu, contrôles et SHA-256 des
sources. Il est reproductible localement ; les logs volumineux ne sont pas versionnés.

## Contrat d'appariement et sens des champs

- Grammaire compagnie **0** et lecture gzip réutilisées depuis
  `analyse_calibration_projets.py`, quantiles linéaires `(n−1)·p` depuis
  `diag_dist_bornes.py`. Aucun appel moteur, aucune dépendance numpy/pytest.
- `PROJECT_CHOSEN` → BUILD : dernier choix précédent, même mode, **paire
  orientée src/dst et cargo**. Consommé une seule fois, jamais partagé entre
  fichiers/campagnes/bras/graines/répétitions. AIR_BUILD omet cargo : PASS selon
  `task_air.nut`. Pas de rapprochement par proximité de distance ou dernier
  choix d'un autre couple. Pas d'identifiant de tentative partagé : une reprise
  ancienne de la même paire ne peut pas être distinguée avec certitude.
- `RAIL_ATTEMPT` → RAIL_BUILD : dernière tentative de même paire, même jour,
  `ok=1`, consommée une fois. Elle ne porte pas de cargo ; cette jointure repose
  sur la séquence `_recordRailAttempt` de `task_rail.nut`, qui émet les deux
  événements successivement. **178/178** appariées, coût `actual` et devis
  `quote` égaux au coût BUILD pour les 178. Le devis post-tracé ne mesure donc
  pas l'erreur du modèle pré-A*.
- `PROJECT_CHOSEN.cost/profit` sont les estimations au choix ; `pre` conserve
  le capital avant préparation A*, `model` le capital avant devis dans
  `OpexBuildLine`. Ils peuvent différer ; pas de substitution silencieuse.
  `RAIL_BUILD.pred_profit` est une estimation après construction, pas un réalisé.
- `PORTFOLIO_RANK` est inventorié (1 220 événements), mais un rang n'est pas
  une décision de construire : aucune utilisation comme faux choix de secours.
  22 RAIL sans choix apparié restent visibles. `task_rail.nut` n'émet le choix
  que sans `railPlan` ; ce chemin explique une possibilité d'absence sans prouver
  individuellement l'origine de chacun des 22 cas.
- **RAIL_BUILD.cost** = `result.actualCost` (AIAccounting, builder rail).
  **AIR_BUILD.cost** = `buildPlan.capital`, donc devis, malgré l'existence de
  `result.actualCost` dans `air_construction.nut`. L'ancien analyseur générique
  appelle tous les BUILD des coûts réels : on réutilise son lecteur, pas cette
  hypothèse. `AIR_COST_PROBE` publie `plannedCapital/actualCost` dans un **signe AC**,
  pas dans AIR_BUILD ; les seuls journaux texte fournis ne livrent pas cette mesure.
- `LINE_REVENUE` → BUILD : mode + identifiant de ligne dans le même fichier,
  cargo cohérent. `real_prof` = somme `GetProfitLastYear` des véhicules attribués
  (`task_report.nut`), donc année **year−1**, hors achat/amortissement/infrastructure.
  Premier rapport exploitable d'âge ≥2, une observation par ligne, normalisation
  `real_prof × flotte_initiale / vehs`, puis division par `PROJECT_CHOSEN.profit`.
  Les prédictions brutes `pred_prof` du rapport sont conservées séparément.
  **44/124** AIR retenues ont changé de taille de flotte : ce redimensionnement
  est un proxy, pas une mesure contrefactuelle des seuls véhicules initiaux.
- 39 lignes RAIL ont un rapport, **toutes immatures** ; leurs profits bruts sont
  conservés dans le JSON mais exclus du tableau de calibration mature.
  AIR : 359 lignes avec au moins un rapport, 124 matures exploitables ; une
  autre ligne mature (mesure, graine 1, ligne 10) a `vehs=0`, `real_prof=0` :
  résultat brut conservé, ratio normalisé indéfini, pas transformé en zéro.
  Les lignes sans rapport ne sont pas assimilées à un profit nul.
- Tentatives RAIL : **209 = 178 réussies + 31 échouées**. Le tableau porte sur
  les constructions, pas le capital perdu dans les échecs. Les entrées AIR_FLEET
  ne sont pas de nouvelles lignes ; croissance et renouvellement restent hors
  de la calibration du capital initial.

## Couverture

| Campagne | Mode | Construites | Choix appariés | Tentatives appariées | Profits matures utilisables |
|---|---|---:|---:|---:|---:|
| mesure 8×3 | RAIL | 120 | 104 (86,7 %) | 120 (100 %) | 0 |
| slow 3×3 | RAIL | 58 | 52 (89,7 %) | 58 (100 %) | 0 |
| mesure 8×3 | AIR | 320 | 320 (100 %) | n/a | 87 (27,2 %) |
| slow 3×3 | AIR | 102 | 102 (100 %) | n/a | 37 (36,3 %) |
| total | RAIL | 178 | 156 (87,6 %) | 178 (100 %) | 0 |
| total | AIR | 422 | 422 (100 %) | n/a | 124 (29,4 %) |

## Ratios par tranche

Intervalles **[0,80), [80,140), [140,200), [200,+∞)** ; `n` est le nombre
réellement exploitable pour chaque ratio, pas le nombre total de constructions.
Distances BUILD : rail distance du candidat, AIR distance de vol du plan ;
ce n'est ni la longueur de voie posée ni la distance des centres-villes du filtre.

| Mode | Distance | Construits | Choix | Tentatives | Matures | Capital réel/choix : médiane [q25;q75], n | Capital réel/pre : médiane [q25;q75], n | Profit opératoire normalisé/choix : médiane [q25;q75], n |
|---|---|---:|---:|---:|---:|---|---|---|
| rail | 0-80 | 45 | 25 | 45 | 0 | 1.125 [1.054;1.237], n=25 | 1.137 [1.094;1.237], n=45 | NA, n=0 |
| rail | 80-140 | 63 | 61 | 63 | 0 | 1.292 [1.197;1.424], n=61 | 1.277 [1.188;1.424], n=63 | NA, n=0 |
| rail | 140-200 | 70 | 70 | 70 | 0 | 1.558 [1.428;1.766], n=70 | 1.558 [1.428;1.766], n=70 | NA, n=0 |
| rail | 200+ | 0 | 0 | 0 | 0 | NA, n=0 | NA, n=0 | NA, n=0 |
| air | 0-80 | 0 | 0 | 0 | 0 | NA, n=0 | NA, n=0 | NA, n=0 |
| air | 80-140 | 1 | 1 | 0 | 0 | NA, n=0 | NA, n=0 | NA, n=0 |
| air | 140-200 | 216 | 216 | 0 | 57 | NA, n=0 | NA, n=0 | 0.452 [0.362;0.544], n=57 |
| air | 200+ | 205 | 205 | 0 | 67 | NA, n=0 | NA, n=0 | 0.408 [0.319;0.483], n=67 |
| rail_PASS | 0-80 | 10 | 10 | 10 | 0 | 1.080 [1.045;1.112], n=10 | 1.061 [1.045;1.112], n=10 | NA, n=0 |
| rail_PASS | 80-140 | 0 | 0 | 0 | 0 | NA, n=0 | NA, n=0 | NA, n=0 |
| rail_PASS | 140-200 | 0 | 0 | 0 | 0 | NA, n=0 | NA, n=0 | NA, n=0 |
| rail_PASS | 200+ | 0 | 0 | 0 | 0 | NA, n=0 | NA, n=0 | NA, n=0 |
| rail_FREIGHT | 0-80 | 35 | 15 | 35 | 0 | 1.201 [1.118;1.297], n=15 | 1.159 [1.101;1.239], n=35 | NA, n=0 |
| rail_FREIGHT | 80-140 | 63 | 61 | 63 | 0 | 1.292 [1.197;1.424], n=61 | 1.277 [1.188;1.424], n=63 | NA, n=0 |
| rail_FREIGHT | 140-200 | 70 | 70 | 70 | 0 | 1.558 [1.428;1.766], n=70 | 1.558 [1.428;1.766], n=70 | NA, n=0 |
| rail_FREIGHT | 200+ | 0 | 0 | 0 | 0 | NA, n=0 | NA, n=0 | NA, n=0 |

## Vérification par campagne (pas un A/B)

| Campagne | Mode | Tranche | Capital réel/choix médiane (n) | Profit normalisé/choix médiane (n) |
|---|---|---|---|---|
| mesure | rail | 0-80 | 1.125 (17) | NA (0) |
| mesure | rail | 80-140 | 1.306 (43) | NA (0) |
| mesure | rail | 140-200 | 1.564 (44) | NA (0) |
| mesure | air | 80-140 | NA (0) | NA (0) |
| mesure | air | 140-200 | NA (0) | 0.440 (41) |
| mesure | air | 200+ | NA (0) | 0.428 (46) |
| slow | rail | 0-80 | 1.136 (8) | NA (0) |
| slow | rail | 80-140 | 1.239 (18) | NA (0) |
| slow | rail | 140-200 | 1.512 (26) | NA (0) |
| slow | air | 140-200 | NA (0) | 0.472 (16) |
| slow | air | 200+ | NA (0) | 0.354 (21) |

## Ce qui manque pour conclure — proposition, non implémentée

1. Ajouter sous `decision_log` un identifiant de projet/tentative stable porté par
   CHOSEN, ATTEMPT, BUILD, échecs et revenus. À la construction AIR, journaliser
   **result.plannedCapital et result.actualCost**, déjà calculés ; distinguer
   infrastructures, véhicules, réutilisation et dépenses irrécupérables d'échec.
   Faire de même pour la décomposition rail (voie, terrassement/ponts, quais,
   dépôts, rames) : le total actuel ne permet pas d'imputer l'écart aux ~370 £/tuile.
2. Figer au choix les versions de modèle et profits bruts/calibrés, revenus,
   fonctionnement, amortissement, nombre de véhicules, cargo et demande. Ne pas
   remplacer la prédiction par celle recalculée après tracé. Conserver distance
   Manhattan, distance payée, distance de vol et longueur réellement construite.
3. Réutiliser LINE_REVENUE et l'attribution des véhicules existante ; suivre les
   achats/retraits et les jours actifs pour observer une année pleine comparable,
   et expliciter maintenance/amortissement. Aucun nouvel A* ou scan de candidats
   n'est nécessaire pour cette sonde proposée, dont le coût d'opcodes resterait
   à mesurer avant usage.
4. Il manque surtout une exposition **RAIL PASS à 80–200 et au-delà**, ainsi que
   des années complètes après construction. Ces journaux ne la créent pas.
   Comparer le scénario synthétique EPOCH_BOUNDS_COST (populations fixes, AIR
   legacy à un avion) aux vrais plans C121 à flotte/demande/sites connus, sans
   extrapoler les lignes fret ni assimiler les deux campagnes à un test causal.
   Aucun changement de bornes ni lancement de campagne proposé comme acquis.

## Validation

- `python3 -m unittest discover -s sweeps -p 'test_diag_calib_rail_air.py'` : **7 OK**.
  Couverture : gzip, doublons, compagnie/cargo/paire orientée, choix consommé,
  tentative échouée/ancienne, capital AIR non observé, année immature,
  normalisation de flotte, bornes, quartiles, zéro et valeurs absentes.
- Suite demandée : **2 472 tests**, **2 erreurs d'import pytest**, 7 ignorés,
  2 échecs attendus, aucun autre échec, 27,246 s. Modules concernés :
  `test_analyze_air_load_shadow`, `test_audit_air_roi_renfort1_itt`.
  Journal local : `results/dist_calib_tmp/unittest.log`. TMPDIR fixé dans ce
  worktree pour les fichiers temporaires des tests. Aucun pytest installé.
- Pas de smoke : parseur hors ligne uniquement, aucune intégration moteur modifiée.

## Empreintes des journaux lus

Chemins relatifs aux deux dossiers cités plus haut. Les hashes portent sur les
fichiers originaux, sans les modifier.

| Campagne | Fichier | SHA-256 |
|---|---|---|
| mesure | reference_seed100_r0.log | `6ca874d8a1a895697b98fef2b0a1a7e33cb5b598e62d4fe00761a3ac9401ccd3` |
| mesure | reference_seed1234_r0.log | `815f55243cb50b60320d353e5ed352bee16694535fa559aa03332e50f1701ce8` |
| mesure | reference_seed17_r0.log | `b1c6dfaa434d6f1a5970aa5606d04fb3fe844d5b784f7809439fab438c9c9437` |
| mesure | reference_seed1_r0.log | `07aad77477ff437f20cef193acfa575977557bc75630c71e12b08274cefa3285` |
| mesure | reference_seed2026_r0.log | `f7b7dcf354a7689177a0464743759f2d0077069a723771a883f455b1b0c2fb9d` |
| mesure | reference_seed42_r0.log | `73da8fa22b2b62051dedadd05537c360fc3b3770eadc8168bff66038c3cf92db` |
| mesure | reference_seed7_r0.log | `f9d9cdff94e6b3fb118422286032a7a06364cb040af6452f4e090aa1291367ee` |
| mesure | reference_seed999_r0.log | `51d26d50255223f0fdb8dae012e1e514d8203d44c0e633fd2e80f04ebe3510e0` |
| slow | reference_seed100_r0.log | `eb5eeb45f1914a71ef9280e2183109824091d68d3343cf3a93cd641746da46eb` |
| slow | reference_seed42_r0.log | `1c3a13b876419b0028c31a749c422ebb5f870ee963f57ed6cbdc7066cd02a4d5` |
| slow | reference_seed7_r0.log | `67f19a4d8b15b46a51dc9fb6a39e765f45b7b526b45b3360738f22a36530c884` |
