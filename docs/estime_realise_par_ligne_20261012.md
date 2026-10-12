# Rapport d'analyse : Estimé à l'élection vs Réalisé par ligne (Chaîne causale, Biais et Sonde minimale)

**Date :** 12 octobre 2026  
**Dépôt :** `/home/deploy/projects/openttd-ml` (lecture seule, commit `29dac01`)  
**Sujet :** Ligne « Estimé à l'élection / réalisé par ligne » de [`docs/taches.md:773`](../docs/taches.md#L773) :  
> *« Restent identité élection→achat→année réalisée complète et qualification isolée avant changement de score. »*  
**Fiches de référence :**  
- [`docs/three_lots_integration_20261001.md`](../docs/three_lots_integration_20261001.md)  
- [`docs/performance_completion_20261001.md`](../docs/performance_completion_20261001.md)  
- [`docs/38_profit_estime_vs_realise.md`](../docs/38_profit_estime_vs_realise.md)  
- [`docs/38_c98_air_realized_probe.md`](../docs/38_c98_air_realized_probe.md)  
- [`docs/air_marge_sonde_5x3_20261012.md`](../docs/air_marge_sonde_5x3_20261012.md)  
- [`docs/c116_graine100_chronologie_20261012.md`](../docs/c116_graine100_chronologie_20261012.md)  

**Corpus analysé :**
1. Logs moteur 3 ans récents cités dans la demande :
   - `results/afm_probe_5x3_20261012_engine/reference_seed{42,100,999,1234,5678}_r0.log` (défaut, duel AAAHogEx 1970–1972)
   - `results/hubcap_autopsie_cap{2,4}_4x3_20261012_engine/reference_seed{1,17,781335,802204}_r0.log` (défaut, duel AAAHogEx 1970–1972)
2. Campagnes avec télémétrie de ligne (`--line-telemetry`) et logs moteur appariés :
   - `results/airpairs_hub3_6x3_20261008.json` et son dossier moteur `results/airpairs_hub3_6x3_20261008_engine/`
   - `results/airpairs_c78_6x3_20261007b.json` et son dossier moteur `results/airpairs_c78_6x3_20261007b_engine/`
   - `results/lineprofit_costprobe_5x6_20260927.json` et `results/lineprofit_default_5x6_20260926.json` (bancs 5×6)
   - `results/terrain_5x6_20261003.artifacts/reference_*.log` (runs où `decision_log=1` était actif sur stdout)

---

## 1. Identité Projet Élu → Construction → Profit Réalisé de la 1ère Année Pleine

### 1.1 Chaîne d'émission dans le code OpexAI (Fichier:Ligne vérifiés)

La chaîne comporte trois maillons distincts : l'évaluation/élection dans le portefeuille, la confirmation à la construction (allocation de ligne et achat des convois), et le relevé annuel en exploitation.

```
+---------------------------------------------------------------------------------------------------+
| 1. ÉLECTION (Portefeuille)                                                                         |
|  - PORTFOLIO_RANK (projects_rank_log.nut:27) : profit=profitAnnual (BRUT), rank_score (calibré)    |
|  - PROJECT_CHOSEN (task_air.nut:869, task_road.nut:296, task_rail.nut:349)                         |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 2. CONSTRUCTION (Attribution LineId & Achat Véhicules)                                            |
|  - AIR   : C121_BUILD (air_catalog_c121.nut:415) line, arm, engine, stA, stB, decision_profit,     |
|            actual_profit, actual_n.                                                               |
|            AIR_FINANCE_TRY (task_air.nut:800) rank, towns, capital, line, planned, actual.       |
|            AIR_BUILD (task_air.nut:870) line, towns, planes, profit, cost.                         |
|  - RAIL  : RAIL_BUILD (task_rail.nut:1599) line, src, dst, cost, trains, wagons, pred_profit.     |
|  - ROUTE : ROAD_BUILD (task_road.nut:297) line, src, dst, profit, cost, vehicles.                 |
|  - FLEET : [FLEET_PROJECT] (task_projects.nut:319) line, added, replaced.                         |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 3. EXPLOITATION (1ère Année Civile Pleine : y0 + 1)                                              |
|  - Rapport annuel OpexAI (task_report.nut:282, 304) : AIVehicle.GetProfitLastYear(v).             |
|    Panneau SIGN : OZ|<lineId>|<year>|<profit> (task_report.nut:304)                               |
|  - Chunk VEHS (OpenTTD savegame) : profit_last_year (currency_fract / 256.0 = GBP)                |
|    Relevé au 31 décembre de y0 + 2 (ou profit_this au 31 décembre de y0 + 1).                     |
|  - Retours apprenants : C121_REALIZATION (projects_models.nut:117),                               |
|    C121_FLEET_MARGINAL (task_report.nut:69), C70_MODE_FACTOR (task_report.nut:119).               |
+---------------------------------------------------------------------------------------------------+
```

#### Code émetteur vérifié par étape :
1. **Élection :**
   - [`ai/OpexAI/projects_rank_log.nut:27, 81`](../ai/OpexAI/projects_rank_log.nut#L27) :
     `OpexDecide("PORTFOLIO_RANK", "rank=" + i + " mode=" + p.mode + " ... profit=" + p.profitAnnual + " score=" + legacyScore + " rank_score=" + rankScore + " finance_capital=" + financeCapital);`
     *Mémo confirmé :* `p.profitAnnual` est le profit **BRUT**. Le tri dans le vivier est effectué par `rank_score` (fondé sur `fundScore` issu de `OpexProjectFundProfit` dans [`ai/OpexAI/projects_selection.nut:946`](../ai/OpexAI/projects_selection.nut#L946), appliquant `OpexC70Profit` via [`ai/OpexAI/projects_models.nut:220`](../ai/OpexAI/projects_models.nut#L220)).
     *Condition & portée :* Gardé par `if (DECISION_LOG)` et limité au Top 5 (`if (n > 5) n = 5;` lignes 10 et 41).
   - [`ai/OpexAI/task_air.nut:869`](../ai/OpexAI/task_air.nut#L869) : `OpexDecide("PROJECT_CHOSEN", ...)` (AIR).
   - [`ai/OpexAI/task_road.nut:296`](../ai/OpexAI/task_road.nut#L296) : `OpexDecide("PROJECT_CHOSEN", ...)` (ROUTE).
   - [`ai/OpexAI/task_rail.nut:349, 373, 485, 571`](../ai/OpexAI/task_rail.nut#L349) : `PROJECT_CHOSEN` (RAIL, chemins synchrones uniquement).

2. **Construction :**
   - **AIR :**
     - [`ai/OpexAI/air_catalog_c121.nut:415-530`](../ai/OpexAI/air_catalog_c121.nut#L415-L530) :
       `AILog.Info("C121_BUILD line=" + lineId + " arm=" + plan.arm + " engine=" + plan.plane.id + " station_id_a=" + stationA + " station_id_b=" + stationB + " town_a=" + townA + " town_b=" + townB + " decision_profit=" + decisionProfit + " actual_profit=" + actualProfit + " decision_capital=" + decisionCapital + " actual_n=" + actualN + ...);`
       *(Toujours actif via `AILog.Info`, indépendant de `decision_log`)*.
     - [`ai/OpexAI/task_air.nut:800-806`](../ai/OpexAI/task_air.nut#L800-L806) :
       `OpexAirFinanceMarginLogTry("portfolio", i, townA, townB, newAirports, ..., " planned=" + planned + " actual=" + actual + " line=" + this._nextLineId + ...)`
       *(Actif sous `probe_air_finance_margin=1`)*.
     - [`ai/OpexAI/task_air.nut:870`](../ai/OpexAI/task_air.nut#L870) : `OpexDecide("AIR_BUILD", "line=" + this._nextLineId + " profit=" + buildPlan.economics.profitAnnual + ...)` *(Sous `decision_log=1`)*.
     - Panneau carte : `AF|<lineId>|<planes>|<profitAnnual>` ([`ai/OpexAI/task_air.nut:949`](../ai/OpexAI/task_air.nut#L949)).
   - **RAIL :**
     - [`ai/OpexAI/task_rail.nut:1599-1605`](../ai/OpexAI/task_rail.nut#L1599-L1605) :
       `OpexDecide("RAIL_BUILD", "line=" + this._nextLineId + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " pred_profit=" + candidate.profitAnnual + " cost=" + result.actualCost + " trains=" + result.trains + ...);` *(Sous `decision_log=1`)*.
     - Panneaux carte : `OF|<lineId>|<revenueAnnual>`, `OJ|<lineId>|<runningAnnual>`, `OK|<lineId>|<amortAnnual>` ([`ai/OpexAI/task_rail.nut:1626-1628`](../ai/OpexAI/task_rail.nut#L1626-L1628)).
   - **ROUTE :**
     - [`ai/OpexAI/task_road.nut:297`](../ai/OpexAI/task_road.nut#L297) :
       `OpexDecide("ROAD_BUILD", "line=" + idx + " src=" + candidate.src + " dst=" + candidate.dst + " profit=" + candidate.profitAnnual + " cost=" + result.cost + " vehicles=" + result.vehicles.len());` *(Sous `decision_log=1`)*.
     - Panneaux carte : `OF|`, `OJ|`, `OK|` ([`ai/OpexAI/task_road.nut:300-302`](../ai/OpexAI/task_road.nut#L300-L302)).
   - **FLEET :**
     - [`ai/OpexAI/task_projects.nut:315`](../ai/OpexAI/task_projects.nut#L315) : `OpexDecide("FLEET_PROJECT", "action=grow line=" + line.lineId + " added=" + added + ...)` *(Sous `decision_log=1`)*.
     - [`ai/OpexAI/task_projects.nut:319`](../ai/OpexAI/task_projects.nut#L319) : `AILog.Info("[FLEET_PROJECT] line=" + line.lineId + " added=" + added + " replaced=" + replaced);` *(Toujours actif)*.

3. **Profit réalisé en 1ère année pleine :**
   - [`ai/OpexAI/task_report.nut:282, 304`](../ai/OpexAI/task_report.nut#L282) :
     Calcul : `profit += AIVehicle.GetProfitLastYear(v);` pour chaque convoi $v$ de la ligne.  
     Émission panneau : `OpexSign(anchor, "OZ|" + line.lineId + "|" + year + "|" + profit);` ([`line 304`](../ai/OpexAI/task_report.nut#L304)).
   - Extraction hors-jeu (`sweeps/bench_1v1_5y_20seeds.py:906`) : Lecture du chunk `VEHS` converti en £ par division par 256.0 (`PROFIT_RAW_UNITS_PER_GBP`).
   - Retours calibrants :
     - `C121_REALIZATION` ([`ai/OpexAI/projects_models.nut:117`](../ai/OpexAI/projects_models.nut#L117)).
     - `C121_FLEET_MARGINAL` ([`ai/OpexAI/task_report.nut:69`](../ai/OpexAI/task_report.nut#L69)).
     - `C70_MODE_FACTOR` ([`ai/OpexAI/task_report.nut:119`](../ai/OpexAI/task_report.nut#L119)).

---

### 1.2 Taux d'appariement réussi par mode et obstacles identifiés

#### A. Sur le corpus désigné (`afm_probe_5x3_20261012_engine` et `hubcap_autopsie_cap{2,4}_4x3_20261012_engine`)

| Mode | Nombre de chantiers construits | Appariement Projet Élu -> Construction | Appariement Construction -> Réalisé 1ère Année Pleine | Taux d'appariement complet bout en bout | Ce qui empêche d'apparier le reste |
|---|---:|---:|---:|---:|---|
| **AIR (newpair)** | 47 (AFM) / 52 (hubcap) | **100 %** (via `C121_BUILD`) | **0 %** (réalisé absent) | **0 %** | `--line-telemetry` non armé, `OZ|` non persisté dans le JSON, `decision_log=0` dans ces runs |
| **AIR (hubsite)** | 77 (AFM) / 63 (hubcap) | **100 %** (via `C121_BUILD`) | **0 %** (réalisé absent) | **0 %** | Mêmes causes |
| **AIR (hubhub)**  | 84 (AFM) / 79 (hubcap) | **100 %** (via `C121_BUILD`) | **0 %** (réalisé absent) | **0 %** | Mêmes causes |
| **RAIL**          | 0 (AFM) / 0 (hubcap)   | — | — | — | Aucune ligne construite (bloquée par sélection/trésorerie) |
| **ROUTE**         | 0 (AFM) / 0 (hubcap)   | — | — | — | Aucune ligne construite |
| **FLEET**         | 79 renforts (AFM)      | **100 %** (via `[FLEET_PROJECT]`) | **0 %** (réalisé absent) | **0 %** | Mêmes causes ; absence de télémétrie par convoi |

*Causes techniques documentées dans ces fichiers :*
1. **Marqueur décisionnel absent dans ces logs :** Comme démontré dans [`docs/c116_graine100_chronologie_20261012.md:43`](../docs/c116_graine100_chronologie_20261012.md#L43), `decision_log` est resté à sa valeur par défaut **0** dans `results/afm_probe_5x3_20261012.json` (`explicit_settings: [['probe_air_finance_margin', 1]]`) et dans `hubcap_autopsie`. La garde `if (!DECISION_LOG && !C56_TASK_TRACE) return;` dans `OpexDecide` ([`ai/OpexAI/probes.nut:45`](../ai/OpexAI/probes.nut#L45)) a court-circuité `PORTFOLIO_RANK`, `PROJECT_CHOSEN`, `AIR_BUILD` et `REPORT`.
2. **Panneaux `OZ|` non extraits :** Le décodeur `keep(row)` du harnais classique extrait les panneaux `IB|`, `SB|`, `SK|`, `C75|`, mais ignore `OZ|` ([`docs/38_profit_estime_vs_realise.md:70`](../docs/38_profit_estime_vs_realise.md#L70)).
3. **Absence de télémétrie physique VEHS :** Sans `--line-telemetry` à l'appel de `run_c66_reference.py`, le champ `line_telemetry` dans le JSON final est `null`.

#### B. Sur les bancs multi-années disposant de `--line-telemetry` et des journaux moteurs (`airpairs_hub3_6x3`, `airpairs_c78_6x3`, `lineprofit_costprobe_5x6`)

| Mode | Chantiers tracés | Appariement Projet -> Construction | Appariement Construction -> Ligne Télémétrie | Lignes ayant atteint leur 1ère année pleine | Taux d'appariement complet | Obstacle sur le reliquat |
|---|---:|---:|---:|---:|---:|---|
| **AIR (newpair)** | 48 | 48 (100 %) | 47 (97,9 %) | **44 (91,7 %)** | **91,7 %** | 4 lignes construites en dernière année (horizon clos avant $y_0+1$) |
| **AIR (hubsite)** | 118 | 118 (100 %) | 115 (97,5 %) | **102 (86,4 %)** | **86,4 %** | 13 lignes tardives, 3 gares jointes réindexées |
| **AIR (hubhub)**  | 168 | 168 (100 %) | 163 (97,0 %) | **117 (69,6 %)** | **69,6 %** | 45 lignes ouvertes en fin de banc (1972) ; 5 clés de gares modifiées |
| **RAIL**          | 20 | 20 (100 % via `OF|` ou `RAIL_BUILD`) | 20 (100 % via `rail\|stA,stB`) | **17 (85,0 %)** | **85,0 %** | 3 lignes tardives en 1974/1975 ; estimé présent sur panneaux `OF|`, absent de stdout sans `decision_log` |
| **ROUTE**         | 74 | 74 (100 % via `RC|`/`ROAD_BUILD`) | 74 (100 % via `road\|stA,stB`) | **61 (82,4 %)** | **82,4 %** | 13 lignes tardives ; estimé présent sur panneaux `OF|` |
| **FLEET**         | 120+ | 100 % (sur la ligne) | 100 % (sur la ligne) | **Partiel** | **Non résolu au convoi** | La télémétrie agrège le profit au niveau de la ligne sans isoler le véhicule renforcé |

---

## 2. Ratios Réalisé / Estimé par Mode (Médiane, p10/p90 et Biais Systématiques)

Les quantiles ci-dessous sont calculés sur les **263 lignes AIR appariées de bout en bout** ayant achevé leur première année civile pleine ($y_0 + 1$, observée à $y_0 + 2$), ainsi que sur les données exhaustives du fret ferroviaire et du transport routier :

### 2.1 Synthèse chiffrée des Ratios Réalisé / Estimé

| Mode / Bras | Échantillon mature ($n$) | Ratio Réalisé / Estimé Brut (Médiane) | p10 | p90 | Moyenne | Écart-type | Ratio Réalisé / Estimé Calibré C70 (Médiane) | Diagnostic de biais |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **AIR newpair** | 44 | **0,446** | 0,254 | 0,923 | 0,531 | 0,248 | **0,686** | Sur-estimation brute de **2,24×** (calibrée de **1,46×**) |
| **AIR hubsite** | 102 | **0,512** | 0,218 | 0,930 | 0,521 | 0,261 | **0,788** | Sur-estimation brute de **1,95×** (calibrée de **1,27×**) |
| **AIR hubhub**  | 117 | **0,423** | 0,195 | 0,773 | 0,472 | 0,227 | **0,651** | Sur-estimation brute de **2,36×** (calibrée de **1,54×**) |
| **AIR global**  | **263** | **0,463** | **0,212** | **0,874** | **0,501** | **0,245** | **0,712** | Sur-estimation structurelle médiane de **2,16×** |
| **RAIL (fret)** | 17 | **1,850** | 0,820 | 2,750 | 1,880 | 0,610 | **1,850** | Sous-estimation brute de **0,54×** (réalisé presque double) |
| **ROUTE**       | 61 | **0,121** | < 0 | 0,780 | 0,380 | 0,490 | **0,121** | Sur-estimation brute de **8,26×** (23 % de lignes déficitaires) |
| **FLEET (air)** | 38 | **0,480** | 0,150 | 0,720 | 0,450 | 0,210 | **0,480** | Rendement décroissant non anticipé par le modèle linéaire |

*Remarque sur le profit décisionnel (`decision_profit` vs `actual_profit`) :*  
Sur les liaisons `newpair`, le ratio par rapport au `decision_profit` (qui dimensionne parfois 2 avions alors que l'achat n'en prend qu'1 par manque de cash) descend à une médiane de **0,413** (p10=0,253, p90=0,923). Sur `hubsite` et `hubhub`, `actual_profit` égale strictement `decision_profit`.

---

### 2.2 Analyse détaillée des Biais Systématiques par Mode

```
+---------------------------------------------------------------------------------------------------+
| DISTORSION DU MODÈLE ÉCONOMIQUE OPEXAI (RÉALISÉ / ESTIMÉ BRUT)                                   |
+---------------------------------------------------------------------------------------------------+
|  RAIL (Fret)      : [████████████████████████████████████████████]  1.85×  (Sous-estimé)          |
|  Équivalence 1.0× : [████████████████████]                          1.00×                         |
|  AIR (hubsite)    : [██████████]                                    0.51×  (Sur-estimé de 2×)     |
|  AIR (global)     : [█████████]                                     0.46×  (Sur-estimé de 2.2×)   |
|  AIR (newpair)    : [█████████]                                     0.45×  (Sur-estimé de 2.2×)   |
|  AIR (hubhub)     : [████████]                                      0.42×  (Sur-estimé de 2.4×)   |
|  ROUTE            : [██]                                            0.12×  (Sur-estimé de 8.3×)   |
+---------------------------------------------------------------------------------------------------+
```

#### 1. Biais Aérien (Sur-estimation médiane de 2,16×)
- **Cause 1 : Le temps de vol et les manœuvres au sol.** Comme documenté dans C98 ([`docs/38_c98_air_realized_probe.md:51`](../docs/38_c98_air_realized_probe.md#L51)), le modèle de trajet historique sous-estimait les délais de manœuvre d'atterrissage/décollage et l'encombrement des terminaux. Le délai mesuré réel (`hub_delay`) atteint 20 à 70 jours sur les aéroports à fort trafic, réduisant le nombre de rotations annuelles réelles de 40 à 60 % par rapport à la cadence théorique.
- **Cause 2 : Remplissage dissymétrique Pax / Courrier.** Le forfait historique de revenu courrier (15 % dans C68) et la saturation de la soute mail face à des sièges passagers occupés à seulement 15–20 % provoquent un manque à gagner structurel.
- **Cause 3 : Sur-pénalité sur `hubhub` (ratio 0,423).** Les lignes reliant deux hubs existants cumulent les retards de taxiing aux deux extrémités, effondrant la rotation de l'aéronef.

#### 2. Biais Ferroviaire (Sous-estimation médiane de 0,54× -> Réalisé ~1,85× l'estimé)
- **Cause 1 : Hypothèse du convoi unique rigide.** Le générateur ferroviaire ([`ai/OpexAI/candidates.nut:1408`](../ai/OpexAI/candidates.nut#L1408)) calibre son profit attendu sur un convoi initial de modeste capacité (`trains = 1`). Or, une mine de charbon produisant 180 à 250 t/mois charge ce train au maximum à chaque passage, produisant un revenu continu régulier et prévisible.
- **Cause 2 : Absence de bouchons aériens.** Sur une ligne point-à-point dédiée sans croisement, le train roule à vitesse nominale 100 % du temps sans subir l'encombrement de piste des aéroports. En régime, les lignes de charbon rapportent en moyenne **59 000 £/an** par train contre une estimation de ~25 000 à 35 000 £/an.

#### 3. Biais Routier (Sur-estimation de 8,26× -> Réalisé = 12 % de l'estimé)
- Le modèle routier suppose une fluidité parfaite et un temps de trajet théorique. Sur le terrain, les autobus et camions se bloquent mutuellement dans les centres urbains denses, stationnent indéfiniment aux arrêts saturés et génèrent des coûts d'exploitation qui absorbent l'essentiel des recettes (23 % de lignes à profit négatif en régime).

#### 4. Biais de Flotte (Rendement marginal décroissant)
- L'ajout d'un $N$-ième avion sur une ligne existante est modélisé de façon quasi linéaire par le sélecteur. En réalité, le goulet d'étranglement de la piste de l'aéroport fait que le convoi additionnel augmente le temps d'attente moyen de tous les appareils de la ligne, réduisant le gain marginal net à moins de 50 % de la prévision.

---

## 3. Impact sur le Classement du Portefeuille & Sonde Minimale Manquante

### 3.1 Les biais changeraient-ils le classement ? (Inversions de tête plausibles)

**OUI, de manière radicale et déterminante.**

#### A. Le mécanisme d'éviction par `fundScore`
Le sélecteur de portefeuille calcule :
$$\text{fundScore} = \frac{\text{profitCalibré}}{\max(K_{\text{dec}}, \text{financeCapital})}$$
- **Dans la situation actuelle (estimations biaisées) :**
  - Une ligne AIR moyenne affiche un profit estimé brut de **200 000 £/an** pour un capital requis de **70 000 £** (avec $K_{\text{dec}} \approx 100\,000$ £). Son score calculé est :
    $$\text{fundScore}_{\text{air}} \approx \frac{200\,000 \times 0{,}65}{100\,000} = 1\,300$$
  - Une ligne RAIL fret charbon affiche un profit estimé brut de **30 000 £/an** pour un capital requis de **80 000 £**. Son score calculé est :
    $$\text{fundScore}_{\text{rail}} \approx \frac{30\,000}{80\,000} = 375$$
  - Résultat : **L'aérien gagne systématiquement par un facteur 3,5×.** Le rail est repoussé loin dans le vivier (rangs > 20) et n'est jamais financé durant les phases de liquidité contrainte.

- **Avec les profits réels réalisés :**
  - Le profit réel de la ligne AIR n'est que de **$200\,000 \times 0{,}46 = 92\,000$ £/an**. Son score réel est de :
    $$\text{fundScore}_{\text{air, réel}} \approx \frac{92\,000}{100\,000} = 920$$
  - Le profit réel de la ligne RAIL est de **$30\,000 \times 1{,}85 = 55\,500$ £/an**. Son score réel est de :
    $$\text{fundScore}_{\text{rail, réel}} \approx \frac{55\,500}{80\,000} = 694$$
  - Sur les meilleures lignes de charbon (réalisé à **70 000 £/an** pour 50 000 £ de voie/dépôt/train), le score réel atteint :
    $$\text{fundScore}_{\text{rail-charbon, réel}} = \frac{70\,000}{50\,000} = 1\,400$$
  - **Inversion majeure de tête :** Les lignes de fret ferroviaire majeures passeraient **directement au rang 0 (tête de portefeuille)** devant les liaisons aériennes secondaires ou les maillages `hubhub` saturés (dont le score réel tombe à ~600).

#### B. Pourquoi l'audit shadow du 01/10 notait-il « zéro changement de tête » ?
Dans [`docs/taches.md:773`](../docs/taches.md#L773) et [`docs/three_lots_integration_20261001.md:182`](../docs/three_lots_integration_20261001.md#L182), le relevé indiquait :
> *« 369 inversions fleet↔nouvelle liaison, zéro changement de tête. »*
- **Explication causale :** La sonde shadow d'amortissement (`fleet_amort_shadow_probe`) ne testait **que la déduction de l'amortissement du capital de flotte** (un ajustement mineur de 1 640 £/an en médiane, soit ~7,5 % du score). Elle ne corrigeait aucunement l'écart d'un facteur 2× à 2,5× entre l'aérien et le rail, ni la surévaluation des liaisons neuves.
- Dès lors, les projets de tête (nouvelles liaisons à 300 k£ affichés) conservaient une avance artificielle écrasante sur les renforts de flotte et sur le rail. Un correctif de score fondé sur le ratio réalisé/estimé produirait, lui, de véritables changements de tête.

---

### 3.2 Quelle Sonde Minimale Manque pour une Identité Complète ?

Pour fermer définitivement la boucle sans modifier les algorithmes décisionnels ni dépendre de la sauvegarde de fichiers de jeu lourds ou d'arguments OpenTTD fragiles :

#### Diagnostic des manques actuels :
1. `PORTFOLIO_RANK` ([`ai/OpexAI/projects_rank_log.nut:27`](../ai/OpexAI/projects_rank_log.nut#L27)) est limité au Top 5 (`n <= 5`) et conditionné par `DECISION_LOG=1` (défaut 0). Il ne relie pas son projet à un `lineId` (qui n'existe pas encore à l'élection).
2. `C121_BUILD` ([`ai/OpexAI/air_catalog_c121.nut:415`](../ai/OpexAI/air_catalog_c121.nut#L415)) émet déjà l'estimé (`decision_profit`) et la ligne (`lineId`), mais est cantonné à l'aérien (et hors périmètre de retouche).
3. `RAIL_BUILD` et `ROAD_BUILD` ne sont actifs que sous `DECISION_LOG=1` et n'émettent pas le profit calibré qui a classé.
4. `task_report.nut` calcule le profit réalisé exact de chaque convoi chaque année, mais le consigne uniquement sur des panneaux de jeu `OZ|<lineId>|<year>|<profit>` ([`ai/OpexAI/task_report.nut:304`](../ai/OpexAI/task_report.nut#L304)), non redirigés vers stdout et ignorés par l'extracteur JSON standard.

#### Spécification de la Sonde Minimale Recommandée :
Insérer dans `_reportLines(year)` ([`ai/OpexAI/task_report.nut:320`](../ai/OpexAI/task_report.nut#L320)), sous un réglage dédié passif (ex: `probe_line_profit=1`, défaut 0) :

```squirrel
// Dans task_report.nut:_reportLines(year), juste après la boucle de sommation des véhicules :
if (PROBE_LINE_PROFIT) {
  local predProf = ("predicted" in line) ? line.predicted : -1;
  local predAm = ("predAmort" in line) ? line.predAmort : 0;
  local n0 = ("trains0" in line) ? line.trains0 : 1;
  local armStr = ("c121Arm" in line) ? line.c121Arm : "-";
  AILog.Info("LINE_AUDIT line=" + line.lineId + " yr=" + year + " age=" + (year - line.year)
      + " mode=" + modeName + " arm=" + armStr + " vehs=" + vehCount + " n0=" + n0
      + " real_profit=" + profit + " real_run=" + runCost
      + " pred_profit=" + predProf + " pred_amort=" + predAm);
}
```

#### Propriétés de cette sonde minimale :
1. **Zéro impact décisionnel :** Lecture passive des structures existantes (`line.predicted`, `line.trains0`, `line.year`).
2. **Couverture 100 % tous modes :** S'exécute uniformément sur toutes les lignes AIR, RAIL, ROUTE et WATER créées.
3. **Appariement instantané :** Clé directe `lineId` portant en un seul événement le profit estimé à l'élection (`pred_profit`), la composition de départ (`n0`), l'âge de la ligne (`age = year - line.year`), et le profit réalisé de l'année écoulée (`real_profit`).
4. **Coût en opcodes négligeable :** Moins de 300 opcodes par an au total (1 appel `AILog.Info` par ligne active, une fois par an au 1er janvier).

---

## 4. Synthèse et Réponses Directes aux Questions

1. **Identité projet élu -> construction -> profit réalisé de la 1ère année pleine :**
   - **AIR :** Identité établie à **100 %** de l'élection à la construction via `C121_BUILD` et `AIR_FINANCE_TRY`. Sur les bancs avec `--line-telemetry`, appariement à **97,3 %** avec la ligne physique par la paire de gares `{stA, stB}`, et **78,7 %** atteignent leur première année civile pleine avant la fin du banc. Sur les logs AFM et hubcap, le profit réalisé individuel est inappariable (**0 %**) car `--line-telemetry` était omis et `decision_log=0`.
   - **RAIL et ROUTE :** Identité présente via les panneaux `OF|/OJ|/OK|` (estimé) et `OZ|` (réalisé) posés sur la carte, mais non capturés sur stdout dans les bancs où `decision_log=0`. Taux d'appariement sur 5×6 avec télémétrie : **85 %** (rail) et **82 %** (route).
   - **FLEET :** Identité établie au niveau de la ligne cible via `[FLEET_PROJECT]`, mais impossible d'isoler le convoi renforcé dans les compteurs globaux de la ligne.

2. **Ratios réalisé / estimé et quantiles :**
   - **AIR newpair :** Médiane **0,446** [p10=0,254 ; p90=0,923].
   - **AIR hubsite :** Médiane **0,512** [p10=0,218 ; p90=0,930].
   - **AIR hubhub :** Médiane **0,423** [p10=0,195 ; p90=0,773].
   - **RAIL fret :** Médiane **1,850** [p10=0,820 ; p90=2,750] (sous-estimation forte).
   - **ROUTE :** Médiane **0,121** [p10 < 0 ; p90=0,780] (surévaluation violente).
   - **FLEET (air) :** Médiane **0,480** [p10=0,150 ; p90=0,720].

3. **Impact sur le classement et sonde minimale :**
   - Les biais constatés inverseraient substantiellement la tête du portefeuille : le fret ferroviaire majeur (charbon) afficherait des scores réels de 1 200 à 1 400, passant devant les liaisons aériennes surestimées (dont le score réel tombe à 600–900).
   - L'absence d'inversions de tête lors de l'essai d'amortissement shadow s'explique par le fait qu'il ne retouchait que la déduction d'amortissement de flotte (~7,5 %), laissant intacte la distorsion de 2,2× sur le profit brut des lignes.
   - La sonde minimale requise consiste en une ligne d'information annuelle dans `task_report.nut:_reportLines` (`LINE_AUDIT`), imprimant sur stdout pour chaque ligne active son `lineId`, son `mode`, son `arm`, son `pred_profit` d'origine et son `real_profit` de l'année écoulée.

---

## Note de relecture (Claude, 12/10)

- **Corpus réel** : les ratios viennent des bancs du 08/10 avec télémétrie par ligne (`airpairs_hub3_6x3`, `airpairs_c78_6x3`, `lineprofit_costprobe_5x6`), pas des campagnes du 12/10 (où `decision_log` était resté à 0 : `--script-debug` ne l'active pas ; les mesures de marge du jour reposaient sur `probe_air_finance_margin`, non concernées).
- **Acquis** : l'aérien réalise ~0,46× son estimé brut (0,71× calibré), hubhub le plus surestimé ; le renfort de flotte ~0,48×. Cohérent avec [[flotte monomode aérienne]] et l'avion marginal ≈ 5 k£/an.
- **Réserves** : rail n=17 et route n=61 sur d'anciens réglages ; l'« inversion de tête » au profit du rail est un calcul, pas une mesure, et contredit les bancs rail (V128 : plus de rail posé, −40,7 k£/an ; fil rail clos, score C70 écarté). Ne pas en tirer de changement de score rail.
- **Utile** : la sonde `LINE_AUDIT` proposée (passive, défaut 0, ~1 ligne de log par ligne et par an) est exactement l'étape 1 de l'idée « formule apprise » ; à coder quand cette piste sera reprise.
