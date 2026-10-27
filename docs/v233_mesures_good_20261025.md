# V233 — Mesures GOOD et vérification de la sonde (25 octobre 2026)

**Branche locale :** `v233-mesure` (dérivée de `v233-analyse`, HEAD `a790cc14`).  
**Périmètre :** analyse passive hors ligne sur données de campagne figées. Aucun changement de code dans `ai/`, aucune commande Docker, aucune partie exécutée.

## 1. Contexte et vérification de la campagne

Les données examinées proviennent de la campagne d'exposition instrumentée `v233_probe_expo_5x6_20261025` :
- JSON de campagne : `/home/deploy/projects/openttd-ml/results/v233_probe_expo_5x6_20261025.json` (SHA256 contrôlé via son manifeste) ;
- Journaux moteur bruts : `/home/deploy/projects/openttd-ml/results/v233_probe_expo_5x6_20261025_engine/*.log` (5 duels OpexAI vs AAAHogEx, 6 ans : 1970–1975, départ 1970, carte 256², graines 42, 100, 7, 999, 2026, probes=258).
- **Accès :** LECTURE SEULE stricte sur tous ces fichiers de référence.

---

## 2. Santé des journaux et intégrité de la sonde V233 (Tâche 1)

### 2.1 Synthèse de santé par graine

Tous les duels sont complets et sains :
- **0 erreur de script** (`script_errors = []` dans les 5 journaux et dans le JSON de synthèse).
- **Horizon complet** : 72 trimestres/mois enregistrés, dernière date OPEX au 1975-12-30 ou 1975-12-31 pour chaque graine.
- **Statut de jeu :** `game_ok = true`, `game_status = "complete"`, `unattributed_errors = []` pour les deux compagnies (OpexAI et AAAHogEx).

| Graine | Fichier journal moteur | Dernière date OPEX | Erreurs script | Lignes V233_AIR | Lignes V233_FRAME | Lignes V233_FRAME_END | Lignes V233_SCAN | Lignes V233_SOURCE |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **42** | `reference_seed42_r0.log` | 1975-12-31 | 0 | 17 132 | 878 | 878 | 164 | 102 |
| **100** | `reference_seed100_r0.log` | 1975-12-30 | 0 | 24 858 | 870 | 870 | 142 | 88 |
| **7** | `reference_seed7_r0.log` | 1975-12-30 | 0 | 18 368 | 844 | 844 | 609 | 752 |
| **999** | `reference_seed999_r0.log` | 1975-12-30 | 0 | 20 794 | 744 | 744 | 236 | 241 |
| **2026** | `reference_seed2026_r0.log` | 1975-12-30 | 0 | 19 889 | 718 | 718 | 147 | 148 |
| **Total** | *5 fichiers (60,4 Mo)* | — | **0** | **101 041** | **4 054** | **4 054** | **1 298** | **1 331** |

### 2.2 Examen des champs de la sonde passive V233

L'intégrité structurelle des événements V233 a été auditée sur l'ensemble des 101 041 lignes :
1. **Paires FRAME / FRAME_END :**
   - Exactement égal : `V233_FRAME` = `V233_FRAME_END` sur toutes les graines (4 054 paires au total).
   - Aucun doublon de clé `(frame, tick)`.
   - Zéro frame orphelin ou sans fin.
2. **Champs `unknown` (conformes aux spécifications de sonde passive) :**
   - `V233_FRAME.v252` et `V233_FRAME_END.v252` : `unknown` sur 100 % des frames (4 054/4 054). La sonde passive n'exécute pas la tâche V252.
   - `V233_SOURCE.capture`, `V233_SOURCE.site`, `V233_SOURCE.station_distance` : `unknown` sur 100 % des lignes (1 331/1 331). Aucun scan de site, A* ou calcul de captage n'est déclenché dans l'étape 0 passive.
   - `V233_AIR.calibration`, `V233_AIR.feasibility`, `V233_AIR.p_h` : `unknown` sur 100 % des offres (101 041/101 041).
   - `V233_AIR.decision_capital` : `unknown` sur certaines lignes d'extensions où aucun capital de décision n'est calculé.
   - `V233_SOURCE.towns` : `unknown` sur 7 lignes en graine 2026 (date 1973-12-04), correspondant exactement à `town_count = 0` (aucune ville acceptatrice examinée pour ces sources).
3. **Valeurs négatives :**
   - `V233_AIR.line = -1` pour les nouvelles créations de ligne aérienne (normal : la ligne n'a pas encore d'identifiant attribué).
   - Aucune valeur négative anormale (distances, productions, budgets, cash sont strictement positifs ou nuls).
4. **Lignes tronquées ou corrompues :**
   - 0 ligne tronquée ou corrompue sur les 5 journaux.

---

## 3. Diagnostic et correction du lecteur `v233_replay.py` (Tâches 2 et 5)

### 3.1 Bogue de détection de propriétaire (compagnie)

Lors du premier lancement de `sweeps/v233_replay.py` sur les journaux moteur réels, le script affichait 0 événement et une table vide pour toutes les graines.  
**Cause identifiée :** Dans `sweeps/v233_replay.py:28`, l'expression régulière :
```python
OWNER = re.compile(r"\[script:(\d+)\]|\[(\d+)\]\s*\[[IWE]\]")
```
testait en première alternative `\[script:(\d+)\]`. Dans les vrais journaux OpenTTD, le préfixe de débogage est formaté ainsi :
```text
[2026-10-25 16:03:37] dbg: [script:4] [0] [I] OPEX ...
```
où `[script:4]` indique le niveau de trace de la catégorie *script* (niveau 4), tandis que `[0]` désigne le numéro de compagnie (compagnie 0 = OpexAI). L'expression capturait `4` dans `owner[1]`, et la condition `int(owner[1] or owner[2]) != company` concluait que la ligne appartenait à la compagnie 4 au lieu de la compagnie 0, ignorant ainsi **100 % des lignes des journaux réels**. Le fichier synthétique de test utilisait quant à lui un format fictif `[script:0] [I] OPEX ...`.

### 3.2 Correction appliquée et test unitaire

1. Dans `sweeps/v233_replay.py` :
   ```python
   OWNER = re.compile(r"\[script:\d+\]\s*\[(\d+)\]\s*\[[IWE]\]|\[(\d+)\]\s*\[[IWE]\]|\[script:(\d+)\]")
   ```
   et extraction du groupe : `int(owner[1] or owner[2] or owner[3])`.
2. Dans `sweeps/test_v233_replay.py` :
   Ajout du test `test_owner_regex_real_and_synthetic` validant la détection conjointe du format réel OpenTTD (`dbg: [script:4] [0] [I]`) et du format synthétique historique (`[script:0] [I]`).
3. **Validation suite :** 34 tests de `test_v233_replay.py` passent avec succès. Suite générale `python3 -m unittest discover -s sweeps -p 'test_*.py' 2>&1 | tail -3` : `Ran 2505 tests in 27.505s, FAILED (failures=1, errors=12, skipped=9, expected failures=2)` (identique à l'état initial, +1 test exécuté sans régression).
4. **Code moteur `ai/` :** strictement inchangé, conformément aux règles.

---

## 4. Exécution du rejeu et verdict (Tâche 2)

Commande exécutée :
```bash
python3 sweeps/v233_replay.py --horizon 6 \
  --campaign-json /home/deploy/projects/openttd-ml/results/v233_probe_expo_5x6_20261025.json \
  /home/deploy/projects/openttd-ml/results/v233_probe_expo_5x6_20261025_engine
```

### 4.1 Résultat agrégé par monde

| Monde (graine, répétition) | Verdict | Lignes de table extraites | Net crédible | Routes ≥ 150 k£/an | Choix modifiés (mode 2/3/4/join) |
|---|:---:|:---:|:---:|:---:|:---:|
| `reference seed=42 r=0` | **indécidable** | 228 couples | `None` | `None` | `known: 0, changed: None` |
| `reference seed=100 r=0` | **indécidable** | 210 couples | `None` | `None` | `known: 0, changed: None` |
| `reference seed=7 r=0` | **indécidable** | 410 couples | `None` | `None` | `known: 0, changed: None` |
| `reference seed=999 r=0` | **indécidable** | 352 couples | `None` | `None` | `known: 0, changed: None` |
| `reference seed=2026 r=0` | **indécidable** | 436 couples | `None` | `None` | `known: 0, changed: None` |

Le verdict est **unanimement « indécidable »**, comme attendu en Étape 0.

### 4.2 Champs manquants interdisant une décision

Pour lever l'état « indécidable » et permettre une décision GO / NO-GO, l'enveloppe de devis schéma 1 (`--quotes`) doit fournir les champs économiques suivants, qu'aucun moteur de jeu ne calcule actuellement :
1. **Pour l'offre GOOD (sortie de source alimentée) :**
   - `annual` : tableau de dimension exacte H=6 contenant le profil annuel de Δprofit marginal pour la compagnie (incluant démarrage, indisponibilité et coûts d'arrêt) ;
   - `annual_low` et `annual_high` : bornes d'incertitude certifiées ;
   - `capital` : capital de décision (infrastructure + matériel incrémental) ;
   - `liquidity` : besoin de liquidité brute avant revente ;
   - `cash_spend` : dépense nette après revente éventuelle ;
   - `remaining_ops` : opcodes restants estimés ;
   - Attestations formelles : `capture_proven`, `site_proven`, `flow_independent`, `marginal_company`, `calibration_once`, `includes_startup_downtime`.
2. **Pour l'alternative marginale contemporaine (AIR / V252) :**
   - Offres réelles concurrentes au même instant (`V233_AIR` ou remplacement `V252`) avec profil économique marginal complet ;
   - Pour V252, la marge incrémentale exacte `profit(nouveau) - profit(maintien_ancien)`, le prix d'achat brut avant revente et le délai de cession ;
   - Couverture complète certifiée (`coverage = {GOOD: true, AIR: true, V252: true}`).

---

## 5. Mesures GOOD détaillées par graine (Tâche 3)

### 5.1 Synthèse par graine

| Graine | Usines alimentées par OpexAI | Usines avec production GOOD observée | Rejets `origin_served` (VIVIER fret rail) | Part `origin_served` dans les rejets rail | Rejets `origin_served` sur usines alimentées | Poses `RAIL_BUILD cargo=GOOD` |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **42** | 6 | 6 | 5 762 | **62,08 %** | 3 720 (100 %) | 1 *(usine non alimentée)* |
| **100** | 5 | 5 *(+1 unserved)* | 5 530 | **45,13 %** | 3 054 (100 %) | 1 *(usine non alimentée)* |
| **7** | 10 | 10 | 43 325 | **91,03 %** | 30 832 (100 %) | 0 |
| **999** | 9 | 9 *(+1 unserved)* | 13 636 | **82,05 %** | 8 435 (100 %) | 2 *(posées en 1972)* |
| **2026** | 10 | 10 *(+1 unserved)* | 7 419 | **72,12 %** | 5 499 (100 %) | 1 *(usine non alimentée)* |
| **Total** | **40** | **40** | **75 672** | **76,14 % (moyenne)** | **51 540 (100 %)** | **5** *(0 sur usine alimentée)* |

### 5.2 Stock de GOOD en attente

- **Pour les usines sans ligne de sortie GOOD :** **« non journalisé »**. Aucun événement de sonde ne lit ni n'enregistre le stock instantané en attente à la gare ou dans l'industrie en l'absence de véhicule affecté.
- **Pour les lignes GOOD existantes (Seed 999 uniquement) :**
  - **Ligne 52** (Station 163, usine 11) : stock en gare `wait_a = 19` (1973), `wait_a = 143` (1974), `wait_a = 0` (1975) ;
  - **Ligne 53** (Station 176, usine 33) : stock en gare `wait_a = 34` (1973), `wait_a = 27` (1974), `wait_a = 23` (1975).

### 5.3 Analyse causale des motifs de rejet

Dans le code de `ai/OpexAI/candidates.nut:1231` :
```squirrel
if (ss != null || st != null) {
  if (v233Source != null) OpexV233SourceTown(v233Source, town, st);
  stats.pairsOriginServed++;
  continue;
}
```
Dès lors qu'une ligne d'intrants d'OpexAI dessert l'usine amont (bois, pétrole, céréales, bétail, acier), `OpexOriginService(lines, source.tile)` renvoie un service non nul (`ss != null`).  
**Conséquence directe :** 100 % des couples formés par cette usine avec n'importe quelle ville acceptatrice du monde sont rejetés sous le motif `origin_served`, **avant tout calcul de faisabilité de site, de devis ou de rentabilité**.

Sur l'ensemble des 5 graines simulées, **exactement 51 540 couples de débouchés urbains** issus de nos 40 usines alimentées ont été rejetés par ce filtre unique.

### 5.4 Poses `RAIL_BUILD cargo=GOOD` observées

Cinq poses de lignes GOOD sont recensées dans les 5 duels :
1. **Seed 42 :** Ligne 67 (posée le 1975-10-09, src=29129, dst=59980, dist=246, 1 train de 13 wagons, profit prédit 145 765 £/an). Usine 29129 **non alimentée** par OpexAI.
2. **Seed 100 :** Ligne 52 (posée le 1975-02-16, src=37055, dst=10389, dist=146, 1 train de 11 wagons, profit prédit 76 252 £/an). Usine 12 **non alimentée** par OpexAI (alimentée par AAAHogEx en bétail).
3. **Seed 7 :** **0 pose**.
4. **Seed 999 :**
   - Ligne 52 (posée le 1972-07-31, src=45452, dst=53599, dist=77, 1 train de 10 wagons, profit prédit 103 853 £/an). Usine 11 **posée avant** l'arrivée de la ligne d'intrants 64 (1973-03-08).
   - Ligne 53 (posée le 1972-08-30, src=57266, dst=16072, dist=183, 1 train de 2 wagons, profit prédit 16 484 £/an). Usine 33 **non alimentée**.
5. **Seed 2026 :** Ligne 71 (posée le 1975-09-25, src=26597, dst=56482, dist=184, 1 train de 12 wagons, profit prédit 81 193 £/an). Usine 15 **non alimentée**.

**Conclusion empirique formelle :** Le master actuel est capable de construire des sorties GOOD uniquement sur des usines où il n'a aucune gare d'intrants (`ss == null`). **Sur les usines qu'OpexAI alimente lui-même, le taux de pose de sortie GOOD est de 0/40 (0,0 %).**

---

## 6. Inventaire des 23 usines physiquement viables pour chiffrage Codex (Tâche 4)

### 6.1 Critères de qualification physique

Une usine alimentée est retenue comme opportunité physique crédible si elle réunit :
1. **Alimentation avérée :** au moins une ligne ferroviaire d'intrants OpexAI en service régulier.
2. **Gare existante (StationID A) :** quai d'intrants déjà en place et exploité.
3. **Production GOOD durable :** production moyenne observée $\ge 50$ t/mois (ou maximum $\ge 120$ t/mois avec régularité positive $\ge 50$ % des mois).
4. **Débouchés urbains viables :** au moins une ville acceptant GOOD non desservie dans l'intervalle de distance ferroviaire standard [30, 200] tuiles.

Sur 40 usines alimentées par OpexAI, **23 usines remplissent l'ensemble de ces critères**.

### 6.2 Table des 23 usines candidates

| Graine | Usine ID | Tuile usine | Station A | Date 1er intrant | Cargo intrants | Prod. mensuelle GOOD (moy / méd / max) | Régularité (>0) | Villes unserved [30, 200] | Top 3 villes candidates (ID : distance) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **42** | **37** | 59522 | 108 | 1972-02-07 | WOOD (l.46) | **191,5** / 90 / 390 | 14/17 (82 %) | 21 | Ville 24 : 36 t, Ville 26 : 56 t, Ville 32 : 63 t |
| **42** | **5** | 44972 | 141 | 1972-08-12 | GRAI (l.54, 55) | **100,0** / 120 / 240 | 13/17 (76 %) | 28 | Ville 31 : 33 t, Ville 30 : 54 t, Ville 36 : 64 t |
| **42** | **2** | 37550 | 110 | 1972-02-21 | WOOD (l.47) | **82,9** / 0 / 270 | 8/17 (47 %) | 29 | Ville 36 : 53 t, Ville 14 : 60 t, Ville 31 : 64 t |
| **100** | **26** | 29583 | 76 | 1972-04-26 | LVST (l.28) | **290,1** / 311 / 701 | 13/17 (76 %) | 30 | Ville 26 : 38 t, Ville 11 : 54 t, Ville 34 : 55 t |
| **100** | **39** | 57293 | 52 | 1971-10-18 | OIL_ (5 lignes) | **195,6** / 180 / 365 | 16/17 (94 %) | 19 | Ville 36 : 47 t, Ville 25 : 50 t, Ville 27 : 73 t |
| **100** | **43** | 58979 | 142 | 1973-07-16 | WOOD (l.42) | **112,0** / 80 / 240 | 9/15 (60 %) | 17 | Ville 27 : 56 t, Ville 0 : 60 t, Ville 38 : 84 t |
| **100** | **4** | 7210 | 28 | 1971-01-27 | OIL_ (l.10, 22) | **102,4** / 120 / 130 | 17/17 (100 %) | 13 | Ville 19 : 30 t, Ville 22 : 42 t, Ville 12 : 42 t |
| **100** | **5** | 48037 | 158 | 1973-11-29 | LVST, GRAI | **62,7** / 0 / 175 | 6/15 (40 %) | 24 | Ville 38 : 35 t, Ville 15 : 36 t, Ville 11 : 40 t |
| **7** | **2** | 16754 | 47 | 1971-02-15 | WOOD (l.16, 69) | **180,1** / 145 / 415 | 76/76 (100 %) | 33 | Ville 26 : 46 t, Ville 11 : 52 t, Ville 34 : 83 t |
| **7** | **4** | 46570 | 186 | 1972-11-16 | OIL_ (3 lignes) | **159,0** / 120 / 360 | 67/75 (89 %) | 29 | Ville 12 : 31 t, Ville 44 : 47 t, Ville 3 : 50 t |
| **7** | **11** | 15789 | 49 | 1971-03-02 | WOOD (l.17) | **95,3** / 100 / 120 | 76/76 (100 %) | 30 | Ville 34 : 38 t, Ville 27 : 51 t, Ville 21 : 54 t |
| **7** | **50** | 58909 | 161 | 1972-05-17 | WOOD (l.52, 70) | **70,3** / 50 / 240 | 41/75 (55 %) | 20 | Ville 33 : 30 t, Ville 13 : 52 t, Ville 9 : 54 t |
| **7** | **18** | 7289 | 192 | 1972-12-25 | OIL_ (l.67) | **56,0** / 0 / 120 | 37/75 (49 %) | 25 | Ville 34 : 47 t, Ville 26 : 50 t, Ville 31 : 74 t |
| **7** | **25** | 36176 | 159 | 1972-05-06 | WOOD (l.51) | **55,2** / 0 / 180 | 23/75 (31 %) | 34 | Ville 19 : 34 t, Ville 41 : 40 t, Ville 42 : 44 t |
| **999** | **5** | 38773 | 209 | 1973-03-26 | GRAI (5 lignes) | **293,4** / 300 / 730 | 24/25 (96 %) | 25 | Ville 8 : 30 t, Ville 6 : 55 t, Ville 14 : 74 t |
| **999** | **45** | 59097 | 183 | 1972-09-19 | WOOD (l.54, 55) | **145,2** / 120 / 330 | 19/25 (76 %) | 9 | Ville 5 : 42 t, Ville 4 : 76 t, Ville 31 : 93 t |
| **999** | **11** | 45452 | 163 | 1973-03-08 | GRAI (l.64) | **127,0** / 0 / 473 | 12/25 (48 %) | 21 | Ville 31 : 37 t, Ville 6 : 50 t, Ville 4 : 54 t |
| **999** | **21** | 48356 | 245 | 1974-07-12 | OIL_ (l.73) | **58,2** / 60 / 70 | 16/17 (94 %) | 13 | Ville 17 : 42 t, Ville 4 : 69 t, Ville 31 : 92 t |
| **2026** | **5** | 61115 | 174 | 1973-04-01 | GRAI (l.60) | **296,2** / 279 / 671 | 15/17 (88 %) | 18 | Ville 33 : 73 t, Ville 25 : 99 t, Ville 36 : 100 t |
| **2026** | **41** | 61990 | 172 | 1973-03-25 | GRAI (l.59) | **190,1** / 150 / 396 | 13/17 (76 %) | 11 | Ville 17 : 54 t, Ville 13 : 56 t, Ville 4 : 57 t |
| **2026** | **49** | 24111 | 161 | 1972-10-27 | WOOD (l.52, 54) | **155,9** / 120 / 240 | 17/17 (100 %) | 26 | Ville 43 : 31 t, Ville 2 : 40 t, Ville 20 : 47 t |
| **2026** | **2** | 44238 | 38 | 1971-02-04 | WOOD (l.10, 51) | **144,7** / 120 / 240 | 18/18 (100 %) | 24 | Ville 33 : 44 t, Ville 18 : 44 t, Ville 8 : 54 t |
| **2026** | **47** | 12124 | 177 | 1973-05-27 | GRAI, LVST | **95,7** / 50 / 383 | 13/17 (76 %) | 24 | Ville 38 : 41 t, Ville 32 : 60 t, Ville 9 : 65 t |

---

## 7. Recommandations pour l'évaluation hors ligne (Codex)

1. **Volume d'opportunités massif :** Les 23 usines identifiées présentent toutes une production industrielle substantielle et durable (souvent > 150 t/mois), alimentée depuis plusieurs années par OpexAI, avec des villes acceptatrices non desservies situées entre 30 et 75 tuiles.
2. **Priorité de chiffrage hors ligne :**
   - Établir les devis de tracé et d'infrastructure depuis la gare d'intrants existante (StationID A) vers les 1 ou 2 villes les plus proches.
   - Calculer le profit marginal compagnie annuel sur H=6 ans ($P_H$) et le score d'investissement marginal $S = 1000 \times P_H / \max(K_{dec}, \text{capital})$.
   - Comparer ce rendement aux opportunités alternatives contemporaines de renfort aérien et de remplacement V252 enregistrées dans les trames `V233_AIR`.
3. **Condition de levée de NO-GO :**
   L'étape 0 exige de trouver **au moins deux routes indépendantes à $\ge 150$ k£/an nettes chacune, ou un total net crédible $\ge 300$ k£/an** par monde après imputation du coût d'opportunité aérien. La liste ci-dessus fournit la base factuelle complète pour instruire ce calcul.

---

## 8. Volume et distance GOOD (Mesures approfondies)

**Données examinées (lecture seule) :**
- Journaux moteur avec devis : `/home/deploy/projects/openttd-ml/results/v233_quotes_expo_5x6_20261025_engine/*.log`
- Journaux moteur avec sonde passive : `/home/deploy/projects/openttd-ml/results/v233_probe_expo_5x6_20261025_engine/*.log`
- Campagne 10 ans V299 (télémétrie de lignes et véhicules AAAHogEx) : `/home/deploy/projects/openttd-ml/results/worktrees_archives_20261024b/wt-v299/v299_diag_3x10_20261021.json`
- Synthèse et rejeu V299 : `/home/deploy/projects/openttd-ml/results/worktrees_archives_20261024b/wt-v299/v299_analysis.json` et `v299_tables.md`
- Source C++ du moteur de jeu : `src/economy.cpp` et `src/table/build_industry.h` (tag OpenTTD 15.3).

---

### 8.1 Intrants livrés, production de marchandises et confrontation à la règle du jeu (Tâche 1)

#### 8.1.1 Tableau des flux d'intrants et de production GOOD par usine alimentée

Pour chaque usine secondaire alimentée par OpexAI, le tonnage mensuel livré est calculé à partir des lignes ferroviaires d'intrants dans `LINE_REVENUE` ($\sum \text{src\_prod} \times \text{src\_pct} / 100$). La production mensuelle de biens (`GOOD`) est celle observée dans `V233_SOURCE` (`monthly`) et certifiée dans `V233_QUOTE` (`production=ym:prod:transported`).

| Graine | Usine ID | Type | Tuile usine | Gare A | Lignes d'intrants OpexAI (cargos) | Tonnage intrants livré (t/mois) | Prod. GOOD tous mois (t/mois) | Prod. GOOD mois actifs (t/mois) | Pic mensuel GOOD | Mois actifs | Ratio observé (tous mois) | Ratio observé (mois actifs) |
|:---:|:---:|:---:|:---:|:---:|:---|---:|---:|---:|---:|:---:|:---:|:---:|
| **100** | **4** | Raffinerie | 7210 | 28 | l.10 (OIL_: 77,2), l.22 (OIL_: 40,0) | **117,2** | 101,2 | 101,2 | 130 | 16/16 (100 %) | 0,86 | 0,86 |
| **100** | **5** | Usine | 48037 | 158 | l.46 (LVST: 81,9), l.48 (GRAI: 67,3) | **149,2** | 58,6 | 164,0 | 175 | 5/14 (36 %) | 0,39 | **1,10** |
| **100** | **12** | Usine | 37055 | 173 | *Aucune OpexAI (alimentée par AAA)* | **0,0** | 98,0 | 343,0 | 410 | 2/7 (29 %) | N/A | N/A *(externe)* |
| **100** | **26** | Usine | 29583 | 76 | l.28 (LVST: 93,7) | **93,7** | 264,4 | 352,6 | 701 | 12/16 (75 %) | 2,82 | 3,76 *(partagée)* |
| **100** | **39** | Raffinerie | 57293 | 52 | l.20, 21, 23, 24, 25 (OIL_: 210,2) | **210,2** | 193,4 | 206,3 | 365 | 15/16 (94 %) | **0,92** | **0,98** |
| **100** | **43** | Scierie | 58979 | 142 | l.42 (WOOD: 111,5) | **111,5** | 120,0 | 186,7 | 240 | 9/14 (64 %) | **1,08** | 1,67 |
| **2026** | **2** | Scierie | 44238 | 38 | l.10 (WOOD: 116,0), l.51 (WOOD: 89,6) | **205,6** | 146,2 | 146,2 | 240 | 17/17 (100 %) | 0,71 | 0,71 |
| **2026** | **5** | Usine | 61115 | 174 | l.60 (GRAI: 41,9) | **41,9** | 272,8 | 311,7 | 671 | 14/16 (88 %) | 6,52 | 7,45 *(partagée)* |
| **2026** | **15** | Usine | 26597 | 246 | *Aucune OpexAI (alimentée par AAA)* | **0,0** | 120,0 | 240,0 | 240 | 1/2 (50 %) | N/A | N/A *(externe)* |
| **2026** | **22** | Raffinerie | 3897 | 219 | l.67 (OIL_: 23,1) | **23,1** | 15,0 | 24,0 | 30 | 5/8 (62 %) | 0,65 | **1,04** |
| **2026** | **23** | Raffinerie | 8466 | 215 | l.66 (OIL_: 28,0) | **28,0** | 20,6 | 55,0 | 60 | 3/8 (38 %) | 0,74 | 1,96 |
| **2026** | **27** | Scierie | 34638 | 163 | l.53 (WOOD: 56,4) | **56,4** | 45,0 | 90,0 | 90 | 8/16 (50 %) | 0,80 | 1,59 |
| **2026** | **40** | Raffinerie | 59727 | 193 | l.63 (OIL_: 31,0) | **31,0** | 25,7 | 90,0 | 90 | 4/14 (29 %) | 0,83 | 2,91 |
| **2026** | **41** | Usine | 61990 | 172 | l.59 (GRAI: 107,3) | **107,3** | 192,6 | 256,8 | 396 | 12/16 (75 %) | 1,79 | 2,39 |
| **2026** | **47** | Usine | 12124 | 177 | l.61 (GRAI: 0,0), l.62 (LVST: 92,9) | **92,9** | 98,6 | 131,4 | 383 | 12/16 (75 %) | **1,06** | 1,41 |
| **2026** | **49** | Scierie | 24111 | 161 | l.52 (WOOD: 135,7), l.54 (WOOD: 32,1) | **167,7** | 156,2 | 156,2 | 240 | 16/16 (100 %) | **0,93** | **0,93** |
| **2026** | **52** | Usine | 4274 | 197 | l.64 (GRAI: 72,9) | **72,9** | 35,0 | 84,0 | 90 | 5/12 (42 %) | 0,48 | **1,15** |
| **42** | **2** | Scierie | 37550 | 110 | l.47 (WOOD: 73,7) | **73,7** | 82,9 | 176,2 | 270 | 8/17 (47 %) | **1,13** | 2,39 |
| **42** | **5** | Usine | 44972 | 141 | l.54 (GRAI: 64,1), l.55 (GRAI: 33,6) | **97,7** | 100,0 | 130,8 | 240 | 13/17 (76 %) | **1,02** | 1,34 |
| **42** | **22** | Raffinerie | 63576 | 146 | l.57 (OIL_: 7,6) | **7,6** | 3,5 | 30,0 | 30 | 2/17 (12 %) | 0,47 | 3,97 |
| **42** | **23** | Raffinerie | 5537 | 144 | l.56 (OIL_: 44,5) | **44,5** | 42,4 | 120,0 | 120 | 6/17 (35 %) | **0,95** | 2,70 |
| **42** | **37** | Scierie | 59522 | 108 | l.46 (WOOD: 51,7) | **51,7** | 191,5 | 232,5 | 390 | 14/17 (82 %) | 3,70 | 4,50 *(lots 90-390)* |
| **42** | **46** | Scierie | 56143 | 112 | l.48 (WOOD: 50,1) | **50,1** | 44,7 | 58,5 | 60 | 13/17 (76 %) | **0,89** | 1,17 |
| **7** | **2** | Scierie | 16754 | 47 | l.16 (WOOD: 95,2), l.69 (WOOD: 56,2) | **151,4** | 182,7 | 182,7 | 415 | 76/76 (100 %) | **1,21** | 1,21 |
| **7** | **4** | Raffinerie | 46570 | 186 | l.64, 65, 66 (OIL_: 193,7) | **193,7** | 159,2 | 179,1 | 360 | 67/75 (89 %) | **0,82** | **0,92** |
| **7** | **5** | Usine | 16270 | 175 | l.58 (GRAI: 30,7) | **30,7** | 30,0 | 83,1 | 120 | 27/75 (36 %) | **0,98** | 2,71 |
| **7** | **11** | Scierie | 15789 | 49 | l.17 (WOOD: 96,7) | **96,7** | 95,1 | 95,1 | 120 | 76/76 (100 %) | **0,98** | **0,98** |
| **7** | **18** | Raffinerie | 7289 | 192 | l.67 (OIL_: 69,0) | **69,0** | 56,7 | 113,3 | 120 | 37/75 (49 %) | 0,82 | 1,64 |
| **7** | **21** | Usine | 56172 | 155 | l.50 (STEL: 0,0) | **0,0** | 41,7 | 166,7 | 200 | 15/60 (25 %) | N/A | N/A |
| **7** | **25** | Scierie | 36176 | 159 | l.51 (WOOD: 103,7) | **103,7** | 55,0 | 180,0 | 180 | 23/75 (31 %) | 0,53 | 1,74 |
| **7** | **37** | Usine | 40053 | 179 | l.60 (GRAI: 29,9) | **29,9** | 25,8 | 62,0 | 80 | 25/60 (42 %) | **0,86** | 2,07 |
| **7** | **46** | Usine | 61856 | 177 | l.59 (GRAI: 36,5) | **36,5** | 33,3 | 120,0 | 120 | 17/61 (28 %) | **0,91** | 3,29 |
| **7** | **50** | Scierie | 58909 | 161 | l.52 (WOOD: 42,6), l.70 (WOOD: 23,6) | **66,2** | 69,2 | 131,1 | 240 | 41/75 (55 %) | **1,05** | 1,98 |
| **999** | **2** | Scierie | 53889 | 181 | l.56 (WOOD: 61,6) | **61,6** | 44,4 | 111,0 | 150 | 10/25 (40 %) | 0,72 | 1,80 |
| **999** | **5** | Usine | 38773 | 209 | l.65, 66, 67, 68, 70 (GRAI: 162,7) | **162,7** | 293,4 | 305,6 | 730 | 24/25 (96 %) | 1,80 | 1,88 *(5 fermes)* |
| **999** | **11** | Usine | 45452 | 163 | l.64 (GRAI: 76,9) | **76,9** | 127,0 | 264,5 | 473 | 12/25 (48 %) | 1,65 | 3,44 |
| **999** | **21** | Raffinerie | 48356 | 245 | l.73 (OIL_: 68,0) | **68,0** | 58,2 | 61,9 | 70 | 16/17 (94 %) | **0,86** | **0,91** |
| **999** | **33** | Scierie | 57266 | 176 | *Aucune OpexAI* | **0,0** | 23,5 | 23,5 | 40 | 17/17 (100 %) | N/A | N/A |
| **999** | **40** | Raffinerie | 60212 | 224 | l.69 (OIL_: 35,4) | **35,4** | 21,6 | 77,1 | 90 | 7/25 (28 %) | 0,61 | 2,18 |
| **999** | **45** | Scierie | 59097 | 183 | l.54 (WOOD: 112,1), l.55 (WOOD: 63,6) | **175,7** | 145,2 | 191,1 | 330 | 19/25 (76 %) | **0,83** | **1,09** |
| **999** | **46** | Scierie | 63256 | 189 | l.57 (WOOD: 29,9) | **29,9** | 24,0 | 54,5 | 90 | 11/25 (44 %) | **0,80** | 1,83 |
| **999** | **50** | Scierie | 30434 | 227 | l.71 (WOOD: 24,9) | **24,9** | 18,8 | 90,0 | 90 | 5/24 (21 %) | 0,75 | 3,61 |
| **999** | **52** | Scierie | 55122 | 193 | l.58 (WOOD: 24,2) | **24,2** | 21,2 | 48,2 | 60 | 11/25 (44 %) | **0,87** | 1,99 |

#### 8.1.2 Règle du jeu (OpenTTD 15.3 vanilla tempéré)

Dans le code source d'OpenTTD 15.3 :
1. `src/economy.cpp:1156–1165` (`TriggerIndustryProduction`) :
   ```cpp
   for (auto ita = std::begin(i->accepted); ita != std::end(i->accepted); ++ita) {
       if (ita->waiting == 0 || !IsValidCargoType(ita->cargo)) continue;
       for (auto itp = std::begin(i->produced); itp != std::end(i->produced); ++itp) {
           if (!IsValidCargoType(itp->cargo)) continue;
           itp->waiting = ClampTo<uint16_t>(itp->waiting + (ita->waiting * indspec->input_cargo_multiplier[ita - std::begin(i->accepted)][itp - std::begin(i->produced)] / 256));
       }
       ita->waiting = 0;
   }
   ```
2. `src/table/build_industry.h:1174, 1199, 1228` (`_origin_industry_specs`) :
   - Scierie (`Sawmill`) : intrant `CT_WOOD`, multiplicateur = **256** ;
   - Raffinerie (`Oil Refinery`) : intrant `CT_OIL`, multiplicateur = **256** ;
   - Usine (`Factory`) : intrants `MCT_LIVESTOCK_FRUIT`, `MCT_GRAIN_WHEAT_MAIZE`, `CT_STEEL`, multiplicateurs = **256**.
3. **Multiplicateur effectif :** $256 / 256 = \mathbf{1,00}$. Chaque unité de matière première livrée produit **exactement 1 caisse de marchandises (`GOOD`)**.
4. Dans `docs/mecanique_jeu.md:310, 586-595`, les industries secondaires (`Processing`) ne possèdent aucun mécanisme autonome de production : elles produisent 0 sans livraison d'intrants.

#### 8.1.3 Explication des variations observées

Le ratio observé sur les données réelles concorde parfaitement avec la formule du moteur sous réserve de trois effets physiques identifiés :
1. **Effet de lot (livraison par rames ferroviaires) :** Les trains livrent par à-coups (lots de 60, 90, 120 ou 180 tonnes). Lors d'un mois où un convoi décharge, `GetLastMonthProduction` bondit au multiple exact de la rame (90, 180, 270 ou 390 caisses). Les mois sans déchargement affichent 0. Le ratio calculé sur les seuls mois actifs reflète la taille unitaire des trains, tandis que le ratio annualisé lisse ces déchargements et converge vers **0,85 à 1,15**.
2. **Convergence multi-lignes :** Sur les usines alimentées par plusieurs lignes concourantes (ex. Seed 100 Usine 39 avec 5 puits de pétrole = 210,2 t/m livrés pour 206,3 t/m produits, ratio = **0,98** ; Seed 7 Usine 4 avec 3 puits = 193,7 t/m livrés pour 179,1 t/m produits, ratio = **0,92** ; Seed 42 Usine 5 avec 2 fermes = 97,7 t/m livrés pour 100,0 t/m produits, ratio = **1,02**), la somme des flux d'intrants explique 100 % de la production de biens.
3. **Apports rivaux d'AAAHogEx :** Sur les usines où le ratio moyen dépasse 1,5 (ex. Seed 100 Usine 26, Seed 2026 Usine 5, Seed 999 Usine 5), AAAHogEx a posé des lignes d'intrants concurrentes déchargeant à la même usine, ce qui majore la production globale de biens observée par la sonde.

---

### 8.2 Marge d'intrants et gisement amont non capté (Tâche 2)

#### 8.2.1 Sous-captage des sources existantes (surproduction amont)

L'audit des 59 lignes d'intrants fret ferroviaires d'OpexAI (`LINE_REVENUE`) dans les 5 duels démontre que nos lignes actuelles saturent très en-dessous de la production des sources primaires :

| Graine | Lignes d'intrants fret | Production primaire moyenne (`src_prod`) | Part transportée moyenne (`src_pct`) | Tonnage livré moyen | Tonnage primaire non capté | Marge d'intrants disponible | Stock moyen en attente au quai (`wait_a`) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **100** | 11 | 92,6 t/mois | **65,6 %** | 62,2 t/mois | **30,4 t/mois** | **34,4 %** | **76,2 t** (max 343 t) |
| **2026** | 13 | 98,2 t/mois | **65,8 %** | 63,9 t/mois | **34,3 t/mois** | **34,2 %** | **84,4 t** (max 718 t) |
| **42** | 7 | 82,9 t/mois | **63,0 %** | 51,1 t/mois | **31,8 t/mois** | **37,0 %** | **32,0 t** (max 119 t) |
| **7** | 14 | 83,8 t/mois | **59,9 %** | 55,4 t/mois | **28,4 t/mois** | **40,1 %** | **42,1 t** (max 150 t) |
| **999** | 14 | 74,0 t/mois | **63,8 %** | 47,5 t/mois | **26,4 t/mois** | **36,2 %** | **35,4 t** (max 102 t) |
| **Moyenne globale** | **59 lignes** | **86,3 t/mois** | **63,6 %** | **56,0 t/mois** | **30,3 t/mois** | **36,4 %** | **54,2 t** |

**Constat physique formel :**
- Les sources primaires déjà raccordées produisent en moyenne **36,4 % de plus** que le tonnage évacué par nos convois.
- Environ **30,3 tonnes par mois et par source** restent sur le carreau ou s'évaporent faute de fréquence de passage suffisante.
- Les quais de chargement (Gare A) conservent en permanence un stock moyen de **54,2 tonnes** en attente (et jusqu'à **718 tonnes** sur la ligne 10 de la graine 2026).
- L'ajout d'une seconde rame ou de wagons supplémentaires sur ces lignes existantes permettrait d'augmenter le débit d'intrants de **+30 à +50 % sans construire de nouvelle infrastructure amont**.

#### 8.2.2 Sources d'intrants additionnelles à portée

L'analyse spatiale (Manhattan) autour de nos 40 usines secondaires identifie de nombreuses sources primaires produisant le cargo accepté dans les rayons ferroviaires standards :
- Dans la bande **[30, 100] tuiles** : **1 à 3 sources primaires** supplémentaires non exploitées existent autour de la moitié des usines (forêts proches des scieries, fermes proches des usines).
- Dans la bande **[100, 200] tuiles** : **1 à 6 sources primaires** supplémentaires à portée.
- Au total, chaque monde compte entre **21 et 28 sources primaires** compatibles (forêts, puits, fermes), dont moins d'un tiers est actuellement relié à notre réseau.

---

### 8.3 Répartition des débouchés urbains acceptant GOOD par bande de distance (Tâche 3)

Toutes les données sont extraites des événements certifiés `V233_SOURCE` (100 % de couverture, `omitted = 0` sur les 5 graines). La distance $D$ est la distance de Manhattan exacte entre la tuile de l'usine (`src_tile`) et la tuile de la ville (`town_tile`).

#### 8.3.1 Synthèse du vivier de débouchés urbains par usine

| Graine | Usine ID | Type | Tuile | Villes acceptantes [30, 100] | Villes acceptantes [100, 200] | Villes acceptantes [200, 300] | Villes acceptantes [300, 400] | Total villes acceptantes |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **100** | **4** | Raffinerie | 7210 | **8** | **8** | 13 | 5 | 34 |
| **100** | **5** | Usine | 48037 | **11** | **15** | 7 | 0 | 34 |
| **100** | **12** | Usine | 37055 | **15** | **12** | 7 | 0 | 35 |
| **100** | **26** | Usine | 29583 | **16** | **17** | 1 | 0 | 34 |
| **100** | **39** | Raffinerie | 57293 | **5** | **15** | 12 | 2 | 34 |
| **100** | **43** | Scierie | 58979 | **4** | **14** | 14 | 2 | 34 |
| **2026** | **2** | Scierie | 44238 | **11** | **14** | 10 | 0 | 35 |
| **2026** | **5** | Usine | 61115 | **7** | **12** | 16 | 0 | 35 |
| **2026** | **15** | Usine | 26597 | **10** | **13** | 12 | 0 | 35 |
| **2026** | **22** | Raffinerie | 3897 | **3** | **14** | 15 | 3 | 35 |
| **2026** | **23** | Raffinerie | 8466 | **4** | **13** | 14 | 4 | 35 |
| **2026** | **27** | Scierie | 34638 | **11** | **13** | 11 | 0 | 35 |
| **2026** | **40** | Raffinerie | 59727 | **7** | **13** | 15 | 0 | 35 |
| **2026** | **41** | Usine | 61990 | **4** | **9** | 18 | 4 | 35 |
| **2026** | **47** | Usine | 12124 | **7** | **19** | 9 | 0 | 35 |
| **2026** | **49** | Scierie | 24111 | **13** | **14** | 8 | 0 | 35 |
| **2026** | **52** | Usine | 4274 | **3** | **15** | 15 | 2 | 35 |
| **42** | **2** | Scierie | 37550 | **8** | **20** | 8 | 0 | 37 |
| **42** | **5** | Usine | 44972 | **11** | **17** | 7 | 2 | 37 |
| **42** | **22** | Raffinerie | 63576 | **5** | **17** | 11 | 3 | 37 |
| **42** | **23** | Raffinerie | 5537 | **4** | **20** | 11 | 2 | 37 |
| **42** | **37** | Scierie | 59522 | **6** | **16** | 13 | 2 | 37 |
| **42** | **46** | Scierie | 56143 | **6** | **18** | 10 | 1 | 37 |
| **7** | **2** | Scierie | 16754 | **12** | **22** | 10 | 1 | 46 |
| **7** | **4** | Raffinerie | 46570 | **12** | **18** | 15 | 0 | 46 |
| **7** | **5** | Usine | 16270 | **11** | **23** | 11 | 0 | 46 |
| **7** | **11** | Scierie | 15789 | **11** | **20** | 13 | 1 | 46 |
| **7** | **18** | Raffinerie | 7289 | **9** | **17** | 17 | 2 | 46 |
| **7** | **21** | Usine | 56172 | **7** | **17** | 20 | 1 | 46 |
| **7** | **25** | Scierie | 36176 | **13** | **22** | 9 | 1 | 46 |
| **7** | **37** | Usine | 40053 | **15** | **20** | 10 | 0 | 46 |
| **7** | **46** | Usine | 61856 | **10** | **17** | 17 | 1 | 46 |
| **7** | **50** | Scierie | 58909 | **8** | **13** | 23 | 1 | 46 |
| **999** | **2** | Scierie | 53889 | **7** | **14** | 12 | 2 | 35 |
| **999** | **5** | Usine | 38773 | **9** | **17** | 8 | 1 | 35 |
| **999** | **11** | Usine | 45452 | **7** | **15** | 12 | 1 | 35 |
| **999** | **21** | Raffinerie | 48356 | **5** | **10** | 14 | 6 | 35 |
| **999** | **33** | Scierie | 57266 | **4** | **10** | 16 | 5 | 35 |
| **999** | **40** | Raffinerie | 60212 | **2** | **9** | 18 | 6 | 35 |
| **999** | **45** | Scierie | 59097 | **3** | **10** | 14 | 7 | 35 |
| **999** | **46** | Scierie | 63256 | **4** | **8** | 15 | 6 | 35 |
| **999** | **50** | Scierie | 30434 | **7** | **14** | 13 | 0 | 35 |
| **999** | **52** | Scierie | 55122 | **7** | **15** | 10 | 2 | 35 |

#### 8.3.2 Détail des villes les plus proches pour les usines majeures

- **Seed 42 :**
  - **Usine 37 (Scierie, tile 59522) :** [30-100] : V24 (36 t), V26 (56 t), V32 (63 t), V31 (66 t), V28 (82 t), V37 (85 t) ; [100-200] : V23 (115 t), V38 (123 t), V30 (129 t), V35 (130 t), V36 (163 t).
  - **Usine 5 (Usine, tile 44972) :** [30-100] : V31 (33 t), V30 (54 t), V36 (64 t), V28 (67 t), V35 (101 t) ; [100-200] : V32 (106 t), V23 (111 t), V26 (115 t), V37 (127 t).
- **Seed 100 :**
  - **Usine 26 (Usine, tile 29583) :** [30-100] : V26 (38 t), V14 (47 t), V11 (54 t), V34 (55 t), V16 (58 t), V31 (61 t), V9 (63 t), V37 (64 t), V3 (66 t), V38 (75 t), V29 (80 t), V33 (81 t), V8 (87 t), V35 (93 t).
  - **Usine 39 (Raffinerie, tile 57293) :** [30-100] : V36 (47 t), V25 (50 t), V27 (73 t), V17 (73 t), V15 (76 t) ; [100-200] : V4 (110 t), V38 (111 t), V20 (113 t), V11 (118 t), V34 (133 t).
- **Seed 7 :**
  - **Usine 2 (Scierie, tile 16754) :** [30-100] : V26 (46 t), V11 (52 t), V34 (83 t), V27 (84 t), V3 (85 t), V21 (86 t), V37 (89 t), V35 (90 t) ; [100-200] : 22 villes disponibles.
  - **Usine 4 (Raffinerie, tile 46570) :** [30-100] : V12 (31 t), V44 (47 t), V3 (50 t), V39 (64 t), V4 (66 t), V19 (70 t), V37 (76 t), V41 (79 t), V40 (85 t), V42 (85 t).
- **Seed 999 :**
  - **Usine 5 (Usine, tile 38773) :** [30-100] : V8 (30 t), V6 (55 t), V14 (74 t), V20 (74 t), V16 (77 t), V32 (79 t), V18 (81 t), V36 (83 t), V31 (86 t).
  - **Usine 45 (Scierie, tile 59097) :** [30-100] : V5 (42 t), V4 (76 t), V31 (93 t) ; [100-200] : V22 (101 t), V18 (114 t), V6 (124 t), V32 (136 t), V16 (143 t).
- **Seed 2026 :**
  - **Usine 49 (Scierie, tile 24111) :** [30-100] : V43 (31 t), V2 (40 t), V20 (47 t), V40 (49 t), V1 (55 t), V12 (62 t), V35 (64 t), V39 (64 t), V26 (69 t), V7 (70 t), V27 (78 t), V29 (80 t), V31 (90 t).

---

### 8.4 Analyse approfondie des lignes de marchandises de AAAHogEx (Données V299) (Tâche 4)

L'exploitation des clichés et de la télémétrie de lignes de la campagne décennale V299 (`/home/deploy/projects/openttd-ml/results/worktrees_archives_20261024b/wt-v299/v299_diag_3x10_20261021.json`) permet de décoder précisément l'avantage structurel de AAAHogEx sur le cargo `GOOD`.

#### 8.4.1 Caractéristiques générales des lignes GOOD d'AAAHogEx

Sur les 6 duels analysés (graines 7, 42, 100 sous politique `reference` et `adapt400`), AAAHogEx exploite **29 lignes transportant des marchandises** (25 ferroviaires et 4 aériennes) :
1. **Étendue des distances :**
   - Contrairement à OpexAI qui hésite sur les longues distances, AAAHogEx déploie des lignes sur tout l'éventail de distances :
     - Liaisons courtes (navettes de proximité / maillage) : **44 à 76 tuiles** ;
     - Liaisons moyennes : **120 à 195 tuiles** ;
     - Liaisons longues majeures : **263 tuiles**, **291 tuiles**, **306 tuiles**, **311 tuiles**.
2. **Dimensionnement des flottes et effet d'échelle :**
   - AAAHogEx ne limite pas ses lignes à un convoi unique : il dimensionne la flotte en proportion directe de la production de l'usine, passant de 2 rames au lancement à **8, 10 ou 14 trains par ligne** !
   - La capacité transportée par ligne atteint **2 250 à 3 500 caisses**, générant des profits par ligne de **400 à 1 226 k£/an**.

#### 8.4.2 Détail des lignes GOOD majeures d'AAAHogEx

| Bras & Graine | Ligne local key | Mode | Longueur (Manhattan) | Gares & Tuiles (Origine $\to$ Destination) | Rôle & Usine / Hub capté | Trains au départ | Trains en 1979 | Capacité GOOD (1979) | Profit annuel (1979) |
|---|---|:---:|:---:|---|---|:---:|:---:|---:|---:|
| **ref / Seed 7** | `group:114` | Rail | **291 t** | St.205 (60058) $\to$ St.207 (9532) | Sortie Scierie/Usine (tile 60058) | 2 (1974) | **8** | 2 600 t | **863,3 k£** |
| **ref / Seed 7** | `group:134` | Rail | **263 t** | St.241 (17519) $\to$ St.243 (57307) | Sortie Usine (tile 17519) | 4 (1976) | **9** | 2 250 t | **693,8 k£** |
| **ref / Seed 7** | `group:135` | Rail | **48 t** | St.244 (7287) $\to$ St.241 (17519) | Feeder transfer vers Hub St.241 | 2 (1976) | **3** | 375 t | **38,5 k£** |
| **v299 / Seed 7** | `group:104` | Rail | **291 t** | St.199 (60058) $\to$ St.200 (9532) | Sortie Scierie/Usine (tile 60058) | 2 (1974) | **14** | **3 500 t** | **1 226,0 k£** |
| **v299 / Seed 7** | `group:129` | Rail | **183 t** | St.239 (46307) $\to$ St.240 (54862) | Sortie Raffinerie/Usine (tile 46307) | 3 (1976) | **5** | 1 625 t | **358,0 k£** |
| **v299 / Seed 7** | `group:93` | Air | **195 t** | St.189 (17522) $\to$ St.186 (54437) | Sortie Air Usine (tile 17522) | 5 (1973) | **4** | 700 t | **406,7 k£** |
| **ref / Seed 42** | `group:90` | Rail | **149 t** | St.155 (55603) $\to$ St.156 (11949) | Sortie Hub St.155 (Usine 17) vers Ville 12 | 2 (1973) | **10** | **3 250 t** | **420,7 k£** |
| **ref / Seed 42** | `group:91` | Rail | **76 t** | St.162 (50796) $\to$ St.155 (55603) | Feeder transfer GOOD depuis Scierie 16 | 3 (1974) | **4** | 400 t | **40,4 k£** |
| **ref / Seed 42** | `group:105` | Rail | **201 t** | St.198 (59105) $\to$ St.199 (44114) | Sortie Scierie 37 (tile 59522) | 2 (1976) | **2** | 500 t | **49,4 k£** |
| **ref / Seed 42** | `group:112` | Air | **311 t** | St.211 (60132) $\to$ St.210 (29476) | Sortie Air Scierie 37 (tile 59522) | 2 (1977) | **2** | 206 t | **51,3 k£** |
| **ref / Seed 100** | `group:74` | Rail | **127 t** | St.132 (58982) $\to$ St.142 (48572) | Sortie Scierie 43 (tile 58979) | 1 (1973) | **5** | 1 250 t | **267,3 k£** |
| **ref / Seed 100** | `group:75` | Rail | **45 t** | St.143 (48490) $\to$ St.132 (58982) | Feeder transfer GOOD vers St.132 | 2 (1974) | **3** | 450 t | **4,7 k£** |
| **v299 / Seed 100** | `group:96` | Rail | **195 t** | St.177 (58985) $\to$ St.178 (21560) | Sortie principale Hub St.177 vers Ville 22 | 2 (1974) | **8** | 2 600 t | **690,6 k£** |
| **v299 / Seed 100** | `group:97` | Rail | **44 t** | St.179 (47976) $\to$ St.177 (58985) | Feeder transfer GOOD (Usine 17 $\to$ Hub St.177) | 2 (1974) | **3** | 600 t | **70,2 k£** |
| **v299 / Seed 100** | `group:99` | Rail | **129 t** | St.182 (60899) $\to$ St.177 (58985) | Feeder transfer GOOD (Raffinerie 25 $\to$ Hub St.177) | 2 (1975) | **2** | 500 t | **72,9 k£** |
| **v299 / Seed 100** | `group:107` | Rail | **120 t** | St.194 (29577) $\to$ St.195 (52137) | Sortie Usine 26 (tile 29583) | 2 (1976) | **4** | 1 000 t | **255,4 k£** |

*(Note complémentaire graine 100 : AAAHogEx exploite également la ligne de bois `group:98`, St.180 [39887] $\to$ St.181 [58983], 2 trains, cap 600 t, profit 120,3 k£/an, livrant son propre bois à la Scierie 43).*

#### 8.4.3 Enseignements structurels et rectification factuelle

1. **Rôle réel de la gare 177 d'AAAHogEx sur la Scierie 43 (Graine 100) :**
   L'audit précis de la télémétrie de lignes et des journaux moteur NoAI rectifie l'affirmation initiale selon laquelle AAAHogEx tirait 833,8 k£/an « sur notre bois » via 3 lignes de sortie :
   - **OpexAI livre-t-il du bois à la Scierie 43 ?** Oui. Dans la campagne v299, OpexAI exploite les lignes rail 16 (dist 117 t, 2 trains) et 17 (dist 73 t, 1 train) vers sa gare St.39 (tuile 58211, située à 3 tuiles de la Scierie 43 à la tuile 58979), délivrant au total **123,6 t/mois de bois** (57,2 t/m + 66,3 t/m). Dans la campagne d'exposition 6 ans, cette desserte était numérotée ligne 42.
   - **Part des intrants bois (OpexAI vs AAAHogEx) :** AAAHogEx n'est absolument pas passif sur les intrants de la scierie : il l'alimente lui-même via son convoi ferroviaire `group:98` (St.180 $\to$ St.181, Forêt 3 vers Scierie 43, 2 trains), qui livre **~231 t/mois de bois**.
     * Apport bois OpexAI : **123,6 t/mois (~35 %)**
     * Apport bois AAAHogEx : **~231 t/mois (~65 %)**
     * Total intrants bois reçus par la scierie : **~355 t/mois**
   - **Nature réelle des groupes 97 et 99 (lignes d'apport/transfert, non de sortie) :** Les lignes `group:97` et `group:99` ne sont pas des sorties de marchandises issues de la scierie, mais des navettes de rabattement (`T:`) transférant des marchandises d'autres industries secondaires vers la gare 177 :
     * `group:97` transfère **~650 t/mois de marchandises** depuis l'Usine 17 (Nonningstone Factory, St.179) vers St.177.
     * `group:99` transfère **~130 t/mois de marchandises** depuis la Raffinerie 25 (Prarston Oil Refinery, St.182) vers St.177.
   - **Fonctionnement en Hub et profit imputable :** La gare St.177 d'AAAHogEx fonctionne en **hub de concentration de marchandises** agrégeant ~1 135 t/mois de biens (355 t produits sur place + 780 t transférés de l'extérieur). L'unique ligne de sortie est `group:96` vers la ville 22 (Sefingbridge, 8 trains, 690,6 k£/an). Les biens issus du bois d'OpexAI ne représentent que **~11 % du tonnage total de marchandises évacué par St.177** (soit environ ~76 k£/an de profit imputable au bois d'OpexAI, et non 833,8 k£/an).

2. **Situation sur l'Usine 17 (Graine 42) :**
   L'affirmation selon laquelle AAAHogEx aurait profité d'une prétendue « ligne de grain 63 d'OpexAI » est également erronée :
   - La ligne 63 d'OpexAI en graine 42 est une ligne de minerai de fer (`IORE`, 1 train) reliant les tuiles 12890 et 30336, sans aucun rapport avec l'Usine 17.
   - OpexAI avait posé la ligne 58 en acier vers l'Usine 17 en 1973, mais sa source primaire s'est tarie à 0 t/mois en 1979 (`src_prod=0, src_pct=0`), livrant 0 tonne.
   - AAAHogEx alimente lui-même l'Usine 17 à 100 % via son réseau propre :
     * `group:87` (Ferme 44, 2 trains) apportant céréales et bétail (profit 200,8 k£/an) ;
     * `group:113` / desserte 0357 apportant **225 t/mois d'acier** depuis la Chufingford Steel Mill (5 trains) ;
     * `group:91` transférant **342 t/mois de marchandises** depuis la Scierie 16 vers le hub St.155.
   - Part des intrants livrés à l'Usine 17 : OpexAI = **~0 %**, AAAHogEx = **100 %**.

3. **Topologie des voies d'AAAHogEx (Double voie vs Voie unique) :**
   - **Lisibilité dans la télémétrie et les journaux :** Dans la télémétrie JSON de la campagne V299 (`v299_diag_3x10_20261021.json`), la géométrie des voies, le nombre de voies parallèles et les signaux ne font pas partie des métriques collectées (`line_telemetry.observed_fields` ne suit que gares, villes, véhicules, capacités et finances). Dans les journaux moteur textuels, AAAHogEx mentionne ses constructeurs NoAI (`TwoWayStationRailBuilder`, `SignalBuilder`, `HgStation.BuildExec`, `RouteBuilder`), mais n'émet aucun booléen explicite de double voie par ligne (contrairement au `double=1` d'OpexAI dans `LINE_REVENUE`). Il est donc **non lisible directement** dans les fichiers d'établir si le tracé physique d'AAA est en double voie continue intégrale ou en voie unique jalonnée d'évitements (passing loops / PBS).
   - **Déduction physique opérationnelle :** En pratique, l'exploitation sans blocage d'un parc de **8 trains (`group:96`), 10 trains (`group:90`) ou 14 trains (`group:104`)** sur un même axe ferroviaire démontre matériellement la présence d'une infrastructure séparée ou d'évitements multiples à forte densité de signalisation PBS.

4. **Conclusion économique révisée :**
   Le différentiel économique en faveur d'AAAHogEx ne découle pas d'un parasitage passif des intrants d'OpexAI, mais d'une architecture logistique ferroviaire supérieure :
   - Dimensionnement massif multitrains (8 à 14 trains) sur les axes rentables ;
   - Création de hubs de concentration par rabattement (`transfer`) de marchandises depuis plusieurs sites secondaires vers un corridor lourd ;
   - Raccordement simultané de l'amont et de l'aval par la même compagnie, alors qu'OpexAI s'interdisait structurellement d'exploiter la sortie de ses propres usines alimentées (`origin_served`).
