# C69 — Suites préparées selon le verdict du 20×10

**Préparé le 2026-09-21, pendant le banc d'autorité de l'étape 4** (`c70_c69` contre `c70`, en duel,
20 graines × 10 ans, `13_banc_c69_20x10_pc.md`). Aucun code dans ce document. Les annexes A, B et
C ont été rédigées par agy à partir des fiches 11 et 12 et du code, puis relues : **les corrections
du §2 prévalent sur leur texte**.

## 1. Arbre de décision

| verdict du 20×10 (critère §10, étape 4 de la fiche 11) | suite | annexe |
|---|---|---|
| **A. adopté** : signes ≥ 15/20 (p < 0,05), écart moyen > +50 k£/an, garde −5 % tenue | 1. second banc 20×10 `c70_c69` contre `default` **avant** tout changement de défaut (C70 seul n'a jamais été validé en 20×10) ; 2. contrat « choix de plan aérien par P/max(C, K_dec) », à la place de `OpexAirPlanBetter` et de sa constante 1,25 | A |
| **B. échec, écart moyen positif** : 10 à 14 victoires, ou garde/seuil manqués avec une moyenne > 0 | contrat « lots de flotte au besoin mesuré », sans le plafond de 4 (risque 5 du §9) ; puis, si l'utilisateur tranche le point ouvert du §2, le levier amont | B |
| **C. échec franc** : ≤ 9 victoires, ou écart moyen ≤ 0 | fermer C69 ; ouvrir C71, le levier amont (`OpexTopK` sous K_dec) | C |

Les cas B et C convergent vers **le même levier amont**, rédigé deux fois (B, contrat 1 ; C, §3-§7).
Il n'y a qu'un contrat à écrire, sous un seul réglage.

## 2. Corrections et points ouverts après relecture

1. **Le levier amont ne touche pas l'avion.** `OpexTopK` tronque le rail (`TOP_K`, candidates.nut:1877)
   et la route (`ROAD_TOP_K`, candidates.nut:2675). Les plans aériens entrent tous au vivier
   (`projects.append(plan)`, builder_air.nut). Or 97 % des divergences de C69 sont aériennes (fiche 11
   §13.3). **Exposition attendue faible** : c'est le critère C1 de sa sonde qui le dira. L'annexe C
   présente « le vivier stérilisé en amont » comme la cause de l'échec : c'est une **hypothèse**.
2. 🔑 **Point ouvert, à trancher avant le code du levier amont.** `candidate.ratio` n'est pas P/C :
   c'est un profit **par itération d'A\*** (plus 15 × ROI pour le rail, candidates.nut:781 et :809 ;
   route candidates.nut:2069). Il facture une ressource que C69 ignore, le calcul. Les deux annexes se
   contredisent :
   - B remplace le ratio par P/max(C, K_dec) **dès 1970** : le classement change alors même avec
     K_dec = 0 (P1 violée) ;
   - C garde le ratio tant que K_dec = 0, puis bascule vers P/max(C, K_dec) : **discontinuité** à la
     première valeur positive de K_dec.
   Forme cohérente possible, non vérifiée : garder le terme opcodes et ne remplacer que le capital,
   par exemple `P×1000/iterations` inchangé et le terme ROI calculé avec max(C, K_dec). Décision
   utilisateur requise.
3. **Annexe A, calibration** : `OpexC70Profit` lit `project.mode`, que l'objet `economics` n'a pas.
   Le facteur de l'air est donc lu directement (`C70_MODE_FACTOR.air`) ; le texte est corrigé.
4. **Critères « ≥ 3/5 en duel » des étapes 5×6 : inopérants.** Le duel n'est pas déterministe (fiche
   11 §16.1 : jusqu'à 18 % d'écart d'un rejeu à l'autre). Pour toutes les suites, le diagnostic 5×6
   se lit **en solo**, qui est déterministe. Le duel ne se lit qu'au 20×10, au test des signes.
5. **Critères d'adoption** : partout, test des signes sur `profit_year` seulement, et garde de valeur
   sur la moyenne (−5 %), comme au §10 de la fiche 11. Les variantes « ou `company_value` » et
   « sur chaque graine » des annexes sont corrigées.
6. **Flotte (annexe B, contrat 2)** : les réfutations citées sont vérifiées (`taches.md:1089-1092`,
   C50b sur 40 graines). Le contrat ne touche ni la réserve `AIR_FLEET_BUFFER` ni le refus `W` ; il
   ne change que la taille du lot quand le renfort est déjà admis.


---

# Annexe A — le levier est adopté

## C69 — Suite conditionnelle Cas A : Le levier est adopté au banc 20×10

**Document de travail rédigé le 2026-09-21.**
Contexte : dépôt `/home/deploy/projects/openttd-ml/.wt_c69` (branche `c69-goulot-decision`).
Hypothèse d'entrée : le banc d'autorité 20×10 en duel de l'étape 4 (`c70_c69` contre `c70`, défini dans `docs/11_goulot_decision.md` §10 et `docs/13_banc_c69_20x10_pc.md` §3) franchit tous ses critères de succès (test des signes ≥ 15/20 avec p < 0,05, écart moyen de `profit_year` > +50 k£/an, garde de −5 % sur `company_value`).

Ce document traite les deux volets consécutifs à cette adoption :
1. La justification méthodologique et la commande exacte du second banc 20×10 indispensable avant toute modification des valeurs par défaut dans `info.nut`.
2. Le contrat formel de l'étape suivante prévue au §12 de la fiche 11 : extension du score $P / \max(C, K_{dec})$ à la planification aérienne en remplacement de la constante 1,25 de `OpexAirPlanBetter` (`ai/OpexAI/builder_air.nut:974-982`).

---

### 1. Pourquoi un second banc est requis avant de changer les défauts

#### 1.1 Justification méthodologique et contractuelle

Le banc officiel de l'étape 4 compare deux politiques :
- Référence : `c70` (`OpexAI[c70_mode_calibration=1]`) ;
- Variante : `c70_c69` (`OpexAI[c70_mode_calibration=1,c69_decision_bottleneck=1]`).

Ce duel isole rigoureusement l'impact marginal de la facturation du goulot C69 (`c69_decision_bottleneck=1`), toutes choses égales par ailleurs (sous calibration par mode C70 active).

Cependant, **C70 seul (`c70_mode_calibration=1`) n'a jamais été validé sur un banc d'autorité 20×10 en duel contre le défaut historique `master` (`policy-id default`)**. Les données disponibles dans les fiches techniques le démontrent :

1. **Mesure C70 incomplète et réservée au solo** (`docs/12_calibration_par_mode.md` §8) :
   - C70 n'a été évalué que sur 20 graines × 10 ans en solo passif sous `probe_portfolio=1` (lignes 130-146).
   - Le critère formel C5 passe tout juste (max/min = 1,46 ≤ 1,5), mais ce résultat est exclusivement porté par l'air (M2 corrigé = 1,11). La route reste sous-estimée (M2 corrigé = 1,51) car bâtie avant que les lignes soient mûres (`age ≥ 2`), et le rail ne compte que 17 lignes mûres sur 20 parties, restant sous le seuil d'échantillonnage de 20 lignes exigé par le §4 (lignes 141-150).
2. **Signal négatif ou neutre de C70 seul au diagnostic 5×6** (`docs/11_goulot_decision.md` §15, lignes 464-469) :
   - En solo, `c70` seul face au défaut (`c70 - default`) perd **−45 k£/an** en profit 1975, avec 3 victoires et 2 défaites.
   - En duel contre AAAHogEx, l'impact sur le ratio de profit n'est que de **+0,010** (3 V / 2 D), non significatif sur 5 graines.
3. **Risque d'illusion de gain par référence dégradée** :
   - Si la référence intermédiaire `c70` est intrinsèquement inférieure ou égale au défaut `default`, battre `c70` ne garantit en rien de battre le code de production `master`.
   - Passer simultanément à 1 les deux réglages (`c69_decision_bottleneck=1` et `c70_mode_calibration=1`) dans `ai/OpexAI/info.nut` (lignes 118-132) exposerait l'IA à adopter une régression nette face au défaut historique.
4. **Conventions de validation OpexAI** (`ai/OpexAI/CLAUDE.md` lignes 9-13 et 96-99) :
   - « AAAHogEx est l'IA adverse utilisée comme arbitre externe de toute décision... Un défaut ne change jamais sur moins que ça : banc officiel 20 graines × 10 ans apparié, lu au test des signes d'abord (≥ 15/20, p < 0,05), moyennes ensuite. »

**Conclusion** : Avant d'altérer un seul défaut dans `info.nut`, la combinaison candidate complète `c70_c69` doit prouver sa supériorité absolue face à la politique `default` sur un banc 20×10 en duel.

---

#### 1.2 Commande exacte du second banc 20×10 en duel

Conformément aux spécifications de `docs/13_banc_c69_20x10_pc.md` §3 (lignes 80-82), la commande exacte exécute la confrontation directe entre la politique `default` (référence implicite de `sweeps/run_c66_reference.py`) et la variante combinée `c70_c69` :

```bash
python3 sweeps/run_c66_reference.py \
  --campaign c69_step4_c70c69_vs_default_10y_20seeds \
  --policy-id default \
  --variant "OpexAI[c70_mode_calibration=1,c69_decision_bottleneck=1]" --variant-policy-id c70_c69 \
  --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 \
  --years 10 --max-workers 9 --cpus 10 --memory 12g \
  2>&1 | tee results/c69_step4_vs_default.log
```

#### 1.3 Paramètres et critères d'acceptation du second banc

| Paramètre / Critère | Valeur | Justification / Source |
|---|---|---|
| `--campaign` | `c69_step4_c70c69_vs_default_10y_20seeds` | Identifiant d'archive unique, sans écrasement (`13_banc_c69_20x10_pc.md:81`) |
| `--policy-id` | `default` | Politique de référence : le défaut `master` actuel (`c69=0, c70=0`) |
| `--reference` | *(absent)* | Sans `--reference`, le script teste les réglages par défaut du code (`13_banc_c69_20x10_pc.md:81`) |
| `--variant` | `OpexAI[c70_mode_calibration=1,c69_decision_bottleneck=1]` | Bras candidat combiné (étapes 2 de C70 et C69) |
| `--variant-policy-id` | `c70_c69` | Identifiant du bras testé |
| Test des signes | **≥ 15 / 20** victoires sur `profit_year` | p < 0,05 (`11_goulot_decision.md` §10, étape 4) |
| Écart moyen primaire | **> +50 k£/an** sur `profit_year` | Seuil d'utilité économique (`13_banc_c69_20x10_pc.md:69`) |
| Garde de valeur | Perte relative sur `company_value` **≤ 5 %** | `11_goulot_decision.md` §10, étape 4 |

Si ce banc est validé, les deux drapeaux `c69_decision_bottleneck` et `c70_mode_calibration` peuvent être adoptés par défaut dans `info.nut`.

---

### 2. Contrat de l'étape suivante : Choix de variante aérienne par le score de goulot

*Faisant suite à la condition du §12 de `docs/11_goulot_decision.md` : « le levier est adopté → appliquer le même score au choix de variante à l'intérieur d'un groupe (avion, profondeur). Il remplacerait OpexAirPlanBetter et sa constante 1,25 (builder_air.nut:974-981) ».*

#### 2.1 Le problème dans le code actuel

Dans `ai/OpexAI/builder_air.nut` (lignes 974-982), la fonction `OpexAirPlanBetter` décide quel plan prime entre deux options concurrentes :

```squirrel
function OpexAirPlanBetter(plan, bestPlan)
{
  if (bestPlan == null) return true;
  /* Arbitrage ROI vs Volume : si un plan offre un ROI significativement superieur (>25% d'ecart),
   * il deploie le capital plus vite et permet de batir plus de lignes. */
  if (plan.economics.roi > (bestPlan.economics.roi * 1.25).tointeger()) return true;
  if (bestPlan.economics.roi > (plan.economics.roi * 1.25).tointeger()) return false;
  return plan.economics.profitAnnual > bestPlan.economics.profitAnnual;
}
```

Ce mécanisme présente trois défauts majeurs :
1. **Une constante magique en dur (1,25 / +25 %)** : exactement le type d'arbitrage heuristique non fondé que C69 vise à éliminer (comme les seuils de `_IsRich()` d'AAAHogEx décrits au §2 de la fiche 11).
2. **Discontinuité de décision** : un plan avec un ROI supérieur de 24,9 % est classé par profit brut, tandis qu'à 25,1 % le ROI prend le pas, indépendamment de la richesse réelle de l'entreprise ou de la rareté de la décision.
3. **Incohérence verticale avec le portefeuille** : le portefeuille classe par $P / \max(C, K_{dec})$ (`projects.nut:707-709`), tandis que la génération aérienne pré-sélectionne ses plans phares avec une règle hybride divergente.

---

#### 2.2 Analyse précise des 3 appelants dans `builder_air.nut`

La fonction `OpexAirPlanBetter` est appelée exactement à 3 endroits, tous situés dans la boucle de planification `OpexAirPlans` (`ai/OpexAI/builder_air.nut:1148-1619`) :

```
OpexAirPlans(catalog, lines, maxCapital, projects, abandoned, paxBand)
 │
 ├── foreach (combo in combos) [kind="large", kind="small"]
 │    │
 │    ├── 1. Boucle double newpair (lignes 1272-1341)
 │    │    └── Appelant 1 (ligne 1336) : if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
 │    │
 │    ├── 2. Boucle hubsite (lignes 1494-1520)
 │    │    └── Appelant 2 (ligne 1518) : if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
 │    │
 │    ├── 3. Boucle hubhub (lignes 1523-1584)
 │    │    └── Appelant 3 (ligne 1582) : if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
 │    │
 │    └── Coupure précoce (ligne 1591) : if (bestPlan != null && bestPlan.airport.allowBig) break;
 │
 └── return bestPlan; (ligne 1618)
```

##### Ce qui est comparé par chaque appelant

| Appelant | Emplacement | Ce qui est comparé | Capital typique | Rôle de l'arbitrage |
|---|---|---|---|---|
| **1. `newpair`** | `builder_air.nut:1336` | Deux paires de villes/sites distinctes `(sites[a], sites[b])` avec 2 aéroports neufs | 70 k£ – 140 k£ (2 aéroports + 1 appareil) | Élire la meilleure ouverture de ligne neuve |
| **2. `hubsite`** | `builder_air.nut:1518` | Un hub existant réutilisé (`reuseA=true`) + 1 nouvel aéroport contre `bestPlan` | 40 k£ – 80 k£ (1 aéroport + 1 appareil) | Arbitrer entre ouvrir une ligne neuve et étendre un hub |
| **3. `hubhub`** | `builder_air.nut:1582` | Deux hubs existants réutilisés (`reuseA=true, reuseB=true`) contre `bestPlan` | ~25 k£ – 45 k£ (0 aéroport, 1 appareil seul) | Arbitrer entre liaisons d'infrastructure et remplissage hub-à-hub |

##### Ce qui N'EST PAS comparé par `OpexAirPlanBetter` dans le code existant

1. **Le nombre d'avions (profondeur de flotte)** :
   - N'est **pas** arbitré par `OpexAirPlanBetter`.
   - Il est déterminé en amont dans la fonction `OpexAirEconomics` (`builder_air.nut:783-802`).
   - De plus, sous la politique par défaut `FLEET_PORTFOLIO=1` (`settings.nut:52`, actif via `policy_air`), la profondeur est restreinte à **1 seul avion initial** (`builder_air.nut:759` : `maxAllowed = (MARGINAL_FLEET || FLEET_PORTFOLIO) ? 1 : ...`).
2. **Le choix du type d'avion (appareil)** :
   - N'est **pas** arbitré par `OpexAirPlanBetter`.
   - Il est choisi pour chaque aéroport et paire en amont par `OpexAirChooseRoutePlane` (`builder_air.nut:988-1013`, appelé aux lignes 1308, 1500 et 1563).
   - Ce choix retient déjà l'appareil au profit maximal pur (mécanisme C68, ligne 1007 : `economics.profitAnnual > bestEconomics.profitAnnual`).
3. **Conséquence directe** :
   - `OpexAirPlanBetter` arbitre en réalité **des plans complets entre paires de villes différentes et entre régimes d'infrastructure différents** (2 aéroports vs 1 aéroport vs 0 aéroport neuf).

##### L'impact critique de `bestPlan`

Dans l'architecture OpexAI, `bestPlan` a deux rôles selon le point d'entrée :
1. **Appel autonome sans portefeuille** (`task_air.nut:107`) : `projects` est `null`. `bestPlan` retourné à la ligne 1618 est **l'unique plan construit** par le cycle air.
2. **Appel sous portefeuille** (`projects.nut:1886` et `2261`) : `projects` n'est pas `null`, donc **tous les plans rentables** sont versés au vivier via `projects.append(plan)` (lignes 1335, 1517, 1581).
3. **Le verrou inter-combos** (`builder_air.nut:1591`) :
   `if (bestPlan != null && bestPlan.airport.allowBig) break;`
   Si `bestPlan` appartient au premier combo (`kind = "large"`, grand aéroport), la boucle `combos` s'arrête immédiatement : le second combo (`kind = "small"`, petit aéroport) n'est **jamais évalué ni injecté dans le vivier**. Une mauvaise élection par `OpexAirPlanBetter` dans le combo large peut donc verrouiller ou masquer des alternatives valides sur petits aéroports.

---

#### 2.3 Formule proposée

Remplacement de la condition 1,25 par la fonction de score unifiée de C69 :

$$\text{score}(plan) = \frac{P_{\text{calib}} \times 1000}{\max(C,\ K_{dec})}$$

Où :
- $P_{\text{calib}}$ est le profit annuel estimé du plan, calibré par le facteur C70 si armé :
  - $P_{\text{calib}} = plan.\text{economics.profitAnnual} \times$ `C70_MODE_FACTOR.air` si `C70_MODE_CALIBRATION` est actif ;
  - $P_{\text{calib}} = plan.\text{economics.profitAnnual}$ sinon.
- $C = plan.\text{economics.capital}$ est le capital d'investissement du plan (aéroports neufs éventuels + premier appareil).
- $K_{dec} = F \times \tau$ est le capital accumulé par décision, calculé par `OpexC69ComputeKDec()`.

##### Implémentation fonctionnelle de `OpexAirPlanBetter`

```squirrel
function OpexAirPlanBetter(plan, bestPlan, kDec = 0)
{
  if (bestPlan == null) return true;

  if (!C69_AIR_PLAN_BOTTLENECK) {
    /* Comportement historique bit-identique */
    if (plan.economics.roi > (bestPlan.economics.roi * 1.25).tointeger()) return true;
    if (bestPlan.economics.roi > (plan.economics.roi * 1.25).tointeger()) return false;
    return plan.economics.profitAnnual > bestPlan.economics.profitAnnual;
  }

  /* Formule C69 sans constante : P / max(C, K_dec) */
  /* economics n'a pas de champ mode : OpexC70Profit y verrait "unknown" et un facteur 1. */
  local kAir = C70_MODE_CALIBRATION ? C70_MODE_FACTOR.air : 1.0;
  local p1 = plan.economics.profitAnnual * kAir;
  local c1 = plan.economics.capital;
  local denom1 = (kDec > c1) ? kDec : c1;
  local score1 = denom1 > 0 ? (p1 * 1000) / denom1 : 0;

  local p2 = bestPlan.economics.profitAnnual * kAir;
  local c2 = bestPlan.economics.capital;
  local denom2 = (kDec > c2) ? kDec : c2;
  local score2 = denom2 > 0 ? (p2 * 1000) / denom2 : 0;

  if (score1 != score2) return score1 > score2;
  if (p1 != p2) return p1 > p2;
  return plan.economics.roi > bestPlan.economics.roi;
}
```

---

#### 2.4 Disponibilité et passage de $K_{dec}$

1. **Où réside la fonction de calcul** :
   - `OpexC69ComputeKDec()` est déclarée dans `ai/OpexAI/probes.nut` (lignes 938-1010).
2. **Ordre de chargement des scripts** (`ai/OpexAI/main.nut`) :
   - `builder_air.nut` est chargé au premier bloc `require` (ligne 54).
   - `probes.nut` est chargé au second bloc `require` (ligne 420).
   - Lors de l'exécution en jeu (`OpexAI::Start()`), l'ensemble des modules est chargé : la fonction globale `OpexC69ComputeKDec()` est parfaitement accessible depuis n'importe quelle méthode.
3. **Disponibilité temporelle lors de la passe** :
   - `OpexAirPlans` s'exécute pendant la phase de génération (`projects.nut:1886` ou `2261`), avant que la sélection `OpexProjectSelectAffordable` (`projects.nut:688`) ne soit appelée.
   - Or, `OpexC69ComputeKDec()` est une fonction **purement macroscopique** : elle interroge l'historique comptable (`AICompany.GetQuarterlyIncome`, `GetQuarterlyExpenses`) et la liste calendaire des chantiers passés (`C69_BUILD_DATES`). Elle ne dépend aucunement des projets de la passe en cours.
   - Elle peut donc être appelée à tout instant.
4. **Point d'évaluation et propagation** :
   - Pour éviter des recalculs redondants à chaque comparaison, $K_{dec}$ est évalué **une seule fois au début de `OpexAirPlans`** :
     ```squirrel
     local kDec = 0;
     if (C69_AIR_PLAN_BOTTLENECK) {
       local kData = OpexC69ComputeKDec();
       kDec = kData.K_dec;
     }
     ```
   - Puis passé en 3e paramètre lors des 3 appels à `OpexAirPlanBetter(plan, bestPlan, kDec)` (lignes 1336, 1518, 1582).
5. **Suivi des chantiers (`C69_TRACK_BUILDS`)** :
   - Dans `ai/OpexAI/settings.nut` (ligne 222), `C69_TRACK_BUILDS` doit être activé si le levier air est armé :
     ```squirrel
     C69_TRACK_BUILDS = C69_BOTTLENECK_PROBE || C69_DECISION_BOTTLENECK || C69_AIR_PLAN_BOTTLENECK;
     ```

---

#### 2.5 Réglage et switch d'expérience

- **Nom du réglage** : `c69_air_plan_bottleneck`.
- **Déclaration** dans `ai/OpexAI/info.nut` :
  ```squirrel
  AddSetting({
    name = "c69_air_plan_bottleneck",
    description = "C69: rank air plans in builder_air by P/max(C, K_dec) instead of ROI*1.25; 1 = on, 0 = off (default)",
    easy_value = 0, medium_value = 0, hard_value = 0,
    custom_value = 0,
    flags = AICONFIG_BOOLEAN
  });
  ```
- **Lecture** dans `ai/OpexAI/settings.nut` :
  ```squirrel
  C69_AIR_PLAN_BOTTLENECK = AIController.GetSetting("c69_air_plan_bottleneck") != 0;
  ```
- **Défaut strict à 0** : garantit que le comportement historique demeure inerte tant que le levier n'est pas activé.

---

#### 2.6 Propriétés garanties

1. **P1 — Neutralité stricte au défaut** : sous `c69_air_plan_bottleneck = 0`, la fonction retourne exactement le résultat de la logique historique `roi * 1.25` au bit près.
2. **P2 — Neutralité d'amorçage** : en début de partie (1970), $F = 0 \implies K_{dec} = 0$. Alors $\max(C, K_{dec}) = C$, le score se réduit à $(P \times 1000) / C$, c'est-à-dire le ROI standard. Le comportement est celui d'une allocation par efficacité de capital pure, sans le seuil artificiel de 25 %.
3. **P3 — Continuité et disparition de la constante arbitraire** : élimination définitive du facteur 1,25. La transition entre priorité ROI (plans peu capitalistiques hub-à-hub) et priorité profit brut (lignes complètes 2 aéroports) se fait de manière continue en fonction du flux réel d'accumulation $K_{dec}$.
4. **P4 — Cohérence inter-niveaux** : la fonction d'utilité qui sélectionne le meilleur plan dans `builder_air.nut` est formellement identique à celle qui classe les projets dans `projects.nut:707`.
5. **P5 — Invariance à l'inflation** : $P$, $C$ et $K_{dec}$ sont tous libellés dans la monnaie courante de l'année.
6. **P6 — Monotonie** : à capital identique, une hausse de profit ne diminue jamais le score ; à profit identique, une hausse de capital ne l'augmente jamais.

---

#### 2.7 Coût estimé en opcodes

Unité de référence : **186 000 opcodes ≈ 1 jour de jeu** (`11_goulot_decision.md` §8, ligne 217).

| Opération | Coût unitaire | Fréquence | Coût cumulé sur 6 ans | Impact relatif |
|---|---|---|---|---|
| Calcul de $K_{dec}$ (`OpexC69ComputeKDec`) | ~1 000 opcodes | 1 fois par balayage `OpexAirPlans` (~20 passes/an) | ~0,12 M opcodes | Négligeable (< 0,03 % du temps de jeu) |
| Score dans `OpexAirPlanBetter` | ~20 opcodes par comparaison | ~100 à 300 comparaisons par passe | ~0,4 M opcodes | Négligeable |
| **Total du levier** | | | **~0,5 M opcodes** | **< 0,15 % d'un an de calcul** |

---

#### 2.8 Ce que ce contrat ne fait pas

1. **Il ne modifie pas les autres modes de transport** (rail, route, eau).
2. **Il ne modifie pas le filtre géographique des villes** ni les bassins de population (`AIR_TOWN_POOL`, `OpexAirSortedTowns`).
3. **Il ne force pas la réouverture de la profondeur de flotte** au démarrage : sous `FLEET_PORTFOLIO`, les nouvelles lignes démarrent toujours à 1 avion (`builder_air.nut:759`).
4. **Il ne modifie pas l'arbitrage d'appareil au sein de la route** (`OpexAirChooseRoutePlane`, `builder_air.nut:988-1013`), qui reste au profit annuel maximal.
5. **Il ne modifie pas la sélection finale du portefeuille** (`OpexProjectSelectAffordable`, `projects.nut:688`).

---

#### 2.9 Protocole d'expérience et critères de validation écrits d'avance

##### Étape 1 — Sonde passive (5 graines × 6 ans, contexte duel contre AAAHogEx)
- **Graines** : `100, 12345, 42, 7, 999` (graines de référence C49/C69, `11_goulot_decision.md` §10).
- **Instrumentation** : sous `probe_portfolio=1`, logger à chaque appel de `OpexAirPlans` :
  - L'indice du plan élu sous l'ancien `OpexAirPlanBetter` (1,25) ;
  - L'indice du plan élu sous le score C69 ;
  - L'état du verrou d'interruption `allowBig` (ligne 1591).
- **Critères d'étape 1** :
  - **Exposition** : divergence constatée sur au moins **15 %** des passes d'évaluation à partir de 1972.
  - **Absence d'anomalie** : 0 crash, 0 assert NoAI.

##### Étape 2 — Implémentation du levier et tests d'identité
- Implémentation sous le réglage `c69_air_plan_bottleneck`, défaut 0.
- Smoke test 2 graines × 3 ans (graines 42 et 100).
- Smoke 1×1 sur 1970 : vérification de l'identité de comportement tant que $K_{dec} = 0$.

##### Étape 3 — Diagnostic 5×6 apparié en duel contre AAAHogEx
- Comparaison entre `c70_c69` (référence) et `c70_c69_airplan` (variante avec `c69_air_plan_bottleneck=1`).
- **Critère de passage** :
  - ≥ 3 graines sur 5 gagnent sur `profit_year` à 6 ans ;
  - Pas de dégradation anormale de la valeur d'entreprise par rapport au bras de référence.

##### Étape 4 — Banc d'autorité 20×10 en duel contre AAAHogEx (C66.4)
- 20 graines × 10 ans apparié en duel, plateforme officielle Docker.
- **Critères stricts d'adoption définitive** :
  - Test des signes : **≥ 15 / 20** victoires sur `profit_year` (p < 0,05) ;
  - Écart moyen primaire : **> +50 k£/an** sur `profit_year` ;
  - Garde de valeur d'entreprise : perte relative sur `company_value` **≤ 5 %**.


---

# Annexe B — échec, écart moyen positif

## Suite conditionnelle B — Traitement des deux brides de C69 en cas de gain moyen sans quorum de signes

**Contrat écrit avant code, 2026-09-21. Aucun code, aucun banc, aucun diagnostic dans ce document.**  
Références de code vérifiées sur `/home/deploy/projects/openttd-ml/.wt_c69` (branche `c69-goulot-decision`).

---

### 0. Contexte et déclenchement du Cas B

Le banc 20×10 apparié en duel contre AAAHogEx (`c70_c69` contre `c70`, étape 4 de `docs/11_goulot_decision.md`) est évalué selon les critères écrits d'avance au §10 :
- Test des signes sur `profit_year` ≥ 15/20 ($p < 0{,}05$) ;
- Écart moyen de `profit_year` > +50 k£/an ;
- Garde de −5 % sur `company_value`.

**Définition du Cas B** : Le levier C69 échoue au critère du test des signes (ex. 10 à 14 victoires sur 20), mais son **écart moyen reste positif** (ex. `profit_year` moyen en hausse, confirmation du signal solo de l'étape 3 où C69 apportait +394 k£/an, §15).  
Cette issue indique que le principe du goulot ($P / \max(C, K_{dec})$) fonctionne sur le fond mais se heurte à deux brides structurelles identifiées dans la fiche 11 :
1. **Les troncatures amont** (§9 risque 1 et §12) : le vivier est tronqué avant sélection par `OpexTopK` sur un critère qui n'est pas le score goulot ;
2. **Le bridage de la flotte aérienne** (§9 risque 5, §12 et §13.3) : les projets de flotte existants sont plafonnés à 4 avions (et les lignes neuves naissent à 1 avion), forçant le régime « décision » à ouvrir des lignes neuves plutôt qu'à densifier les lignes rentables.

Ce document formalise les deux contrats conditionnels correspondants, selon les conventions de `CLAUDE.md`.

---

### Contrat 1 — Appliquer $K_{dec}$ aux troncatures amont de génération (Rail et Route)

#### 1.1 Le problème et l'état des lieux dans le code

Le risque 1 du §9 de la fiche 11 posait l'hypothèse d'une troncature amont privant le régime « décision » de projets à fort profit absolu.

| Troncature | Constante / Variable | Définition / Fichier | Lieu d'application dans le code |
|---|---|---|---|
| Troncature rail | `TOP_K = 20` | `ai/OpexAI/candidates.nut:26` et `ai/OpexAI/globals_post.nut:8` | `candidates.nut:1877` (`OpexRailCandidates`), `projects.nut:2055, :2155, :2165` |
| Troncature route | `ROAD_TOP_K = 48` | `ai/OpexAI/candidates.nut:1962` | `candidates.nut:2675` (`OpexRoadCandidates`), `projects.nut:2245` |
| Borne portefeuille | `PROJECT_TOP_K = 64` | `ai/OpexAI/projects.nut:24`, `catalog.nut:955-964` (si dynamique), lu `settings.nut:98` | `projects.nut:910, :1916, :2487` (`OpexProjectSelectAffordable`) |

Toutes les troncatures amont de candidats reposent sur la fonction `OpexTopK(all, k)` définie dans `ai/OpexAI/candidates.nut:954-966` :
```squirrel
function OpexTopK(all, k)
{
  local best = [];
  local floor = 0;
  foreach (candidate in all) {
    if (best.len() >= k && candidate.ratio <= floor) continue;
    local pos = best.len();
    while (pos > 0 && best[pos - 1].ratio < candidate.ratio) pos--;
    best.insert(pos, candidate);
    if (best.len() > k) best.pop();
    if (best.len() >= k) floor = best[best.len() - 1].ratio;
  }
  return best;
}
```

#### 1.2 Nature exacte de `candidate.ratio` : incomparable à $P/C$

La vérification de l'affectation de `.ratio` sur chaque famille de candidats met en évidence une propriété fondamentale :

| Mode / Candidat | Affectation dans le code | Dénominateur effectif | Nature de la grandeur |
|---|---|---|---|
| Rail ordinaire | `candidates.nut:809` : `ratio = opcodeRatio + (adjustedRoi * 15)` avec `opcodeRatio = (economics.profitAnnual * 1000) / iterations` (`:781`) | `iterations = OpexRailIterations(distance)` (`:123-142`) | Score composite : profit par **itération d'A\*** + $15 \times \text{ROI}$ |
| Rail passagers proches | `candidates.nut:882` : `ratio = PAX_NEAR_RATIO` (valeur 1) | — | Priorité minimale forcée sous tout candidat rentable |
| Rail probe | `candidates.nut:940` : `ratio = 0` | — | Non admissible |
| Route ordinaire | `candidates.nut:2069` : `ratio = (economics.profitAnnual * 1000) / iterations` | `iterations = ROAD_PLAN_ITERATIONS_BASE + distance` (`:1992-1995`) | Profit par **itération équivalente** (~2 700 opcodes) |
| Extension bus ville | `candidates.nut:2317` : `iterations = 1, ratio = profit * 1000` | 1 | Profit brut |
| Subventions routières | `candidates.nut:3003` : `ratio = (subProfit * 1000) / iterations` | `iterations = OpexRoadIterations(distance)` | Profit subventionné par itération |

**Constat majeur : `candidate.ratio` N'EST PAS comparable à $P/C$**.
1. **Incommensurabilité des unités** : Le dénominateur de `candidate.ratio` n'est pas le capital $C$ (en £), mais une estimation du nombre d'itérations de calcul (A* ferroviaire ou routier). Pour la route, `iterations` est de l'ordre de 25 à 150 (alors que le capital $C$ est de ~12 000 £). Pour le rail, `iterations` croît fortement avec la distance (table `OpexRailIterations`, `:101-104`).
2. **Pénalité sur les grandes lignes** : Parce que `iterations` explose avec la distance, `OpexTopK` privilégie drastiquement les lignes ultra-courtes qui consomment peu de calcul, au détriment des lignes longues dont le profit absolu $P$ annuel est élevé.
3. **Conséquence pour C69** : Lorsque $K_{dec}$ monte (régime « décision » riche, $K_{dec} > C$), le portefeuille sélectionne sur le profit $P$, mais le vivier amont fourni au portefeuille a déjà été amputé de ses candidats à fort profit par `OpexTopK` !

#### 1.3 Disponibilité temporelle de $K_{dec}$ à la génération

La fonction `OpexC69ComputeKDec()` (`ai/OpexAI/probes.nut:938-1010`) calcule $F$, $\tau$ et $K_{dec}$ :
- $F$ est calculé par `AICompany.GetQuarterlyIncome` et `GetQuarterlyExpenses` sur les 4 derniers trimestres (`probes.nut:961-972`) ;
- $\tau$ est calculé par $D / N$ sur la fenêtre glissante des dates de chantier `C69_BUILD_DATES` (`probes.nut:979-997`).

**$K_{dec}$ ne dépend d'aucun projet ni candidat.** Il est dérivé uniquement de l'état macroéconomique de la compagnie.

Concernant l'ordonnancement de l'exécution :
- **Dans `OpexBuildProjects`** (`ai/OpexAI/projects.nut:2069-2530`) : la génération rail (`:2118-2216`) et route (`:2235-2249`) s'exécute **dans la même passe** que la sélection du portefeuille (`:2487`, `OpexProjectSelectAffordable`).
- **Dans `_rebuildProjects`** (`ai/OpexAI/task_projects.nut:971-1020`), appelée lors des dispatches de `catalog` (`ai/OpexAI/scheduler_tasks.nut:66`) et de `projects` (`ai/OpexAI/task_projects.nut:923, :929`) : génération et sélection se déroulent séquentiellement au sein du même tick/cycle.
- **Dans `OpexIncrementalUpdateProjects`** (`ai/OpexAI/projects.nut:1758-1935`) : les candidats existants sont filtrés et ré-arbitrés sans régénération complète.

**Conclusion** : $K_{dec}$ peut être calculé **une seule fois** dès l'entrée de `OpexBuildProjects` et passé directement aux générateurs de candidats.

#### 1.4 Spécification de la formule amont et levier proposé

On introduit le réglage `c69_upstream_bottleneck` (défaut 0).  
Sous `c69_upstream_bottleneck = 0` : comportement historique bit-identique (`candidate.ratio`).

Sous `c69_upstream_bottleneck = 1` :  
Chaque candidat disposant de `profitAnnual` et de `capital` (présents dans `economics.profitAnnual` et `economics.capital` tant pour le rail que pour la route, cf. `candidates.nut:850-855` et `:2057-2069`) reçoit un score de troncature amont :
$$\text{upstreamScore} = \frac{P \times 1000}{\max(C,\ K_{dec})}$$
- En régime pauvre ($K_{dec} \le C$) : le score est le ROI économique brut $P \times 1000 / C$ (sans division par les itérations d'A*).
- En régime riche ($K_{dec} > C$) : le score devient $P \times 1000 / K_{dec}$, classant par profit annuel absolu $P$.
- `OpexTopK` trie sur `upstreamScore` au lieu de `candidate.ratio`.

#### 1.5 Coût en opcodes

| Poste | Coût par appel | Fréquence | Coût cumulé sur 6 ans |
|---|---|---|---|
| Calcul de $K_{dec}$ via `OpexC69ComputeKDec()` | ~1 000 opcodes | 1 fois au début de `OpexBuildProjects` | ~0,1 M opcodes |
| Calcul de `upstreamScore` par candidat | ~4 opcodes (1 `max`, 1 multiplication, 1 division) | ~300 candidats rail + ~500 candidats route | ~3 200 opcodes par génération |
| Tri d'insertion dans `OpexTopK` | Inchangé par rapport à aujourd'hui | À chaque candidat | Inchangé |
| **Total surcoût amont** | | | **< 0,5 M opcodes (< 3 jours de jeu, < 0,1 %)** |

#### 1.6 Critères de passage écrits d'avance

| Étape | Protocole | Critères de succès | Sinon |
|---|---|---|---|
| **Étape 1 — Diagnostic 5×6** | 5 graines × 6 ans (`100 12345 42 7 999`), duel contre AAAHogEx | ≥ 3 graines sur 5 avec `profit_year` en hausse vs `c70_c69` de référence ; présence de lignes longues admises au portefeuille | **Fermer la piste amont** : le vivier actuel n'est pas le goulot |
| **Étape 2 — Banc 20×10** | 20 graines × 10 ans apparié duel | Test des signes ≥ 15/20 ($p < 0{,}05$), profit annuel moyen > +50 k£/an, garde −5 % valeur | Maintien du réglage à 0 |

#### 1.7 Ce que ce contrat ne fait pas
- Il ne supprime pas `TOP_K` ni `ROAD_TOP_K` : les plafonds de 20 et 48 restent stricts pour borner le coût d'A*.
- Il ne touche pas aux filtres d'élimination précoce (`_tooClose`, `MIN_PROFIT_ANNUAL`).
- Il ne modifie pas le format des candidats ni la sélection finale `PROJECT_TOP_K`.

---

### Contrat 2 — Arbitrage et dimensionnement de la flotte aérienne (Risque 5 du §9)

#### 2.1 Le problème et l'état des lieux dans le code

Le risque 5 du §9 et les résultats de l'étape 1 (§13.3) ont mis en lumière une distorsion structurelle :
- Sur 156 passes divergentes sous C69, **70 sont des arbitrages où C69 préfère ouvrir une nouvelle ligne aérienne plutôt que d'ajouter un avion à une ligne existante**.
- Au §16.2, C69 produit plus de lignes aériennes (+1,2 ligne en moyenne), mais **moins d'avions au total** (−1,8 avion en 1975) et un profit par avion supérieur (+19 à +23 % en 1972-1973), avec un resserrement en fin de période.
- Cette situation découle d'une asymétrie de modélisation dans le code actuel :

| Mécanisme | Fichier et ligne | Implémentation actuelle | Effet sur le régime « décision » |
|---|---|---|---|
| Dotation initiale des lignes neuves | `ai/OpexAI/builder_air.nut:759` | `local maxAllowed = (MARGINAL_FLEET \|\| FLEET_PORTFOLIO) ? 1 : ...` | Sous `FLEET_PORTFOLIO = true` (défaut, `globals_pre.nut:312`), **toute nouvelle ligne aérienne naît avec 1 seul avion**. |
| Plafond de renfort par passe | `ai/OpexAI/task_air.nut:748, :779` | `local maxAddedPerPass = MARGINAL_FLEET ? 1 : 4;` puis `maxAddedPerPass = (buildNum < 4) ? buildNum : 4;` | Une ligne existante saturée ne peut demander **au maximum que 4 avions** par passage. |
| Taille de lot soumise au portefeuille | `ai/OpexAI/task_air.nut:784-787` | `local want = (room < maxAddedPerPass) ? room : maxAddedPerPass; plan.append({ line = line, want = want, planePrice = planePrice });` | `want` est borné par `maxAddedPerPass` ($\le 4$). Un seul projet par ligne est émis. |
| Scoring du projet flotte | `ai/OpexAI/projects.nut:425-441` (`OpexProjectFromFleet`) | `profit = perPlaneProfit * want; capital = planePrice * want;` | En régime $K_{dec} > C$, le score est $(P \times 1000) / K_{dec} = (\text{perPlaneProfit} \times want \times 1000) / K_{dec}$. |

**Conséquence** : Une nouvelle ligne aérienne promet un profit total annuel $P \approx 70\text{--}115\text{ k£}$. Un projet de renfort d'un seul avion promet $P \approx 20\text{--}35\text{ k£}$. Le score $P / K_{dec}$ favorise systématiquement l'ouverture de la ligne neuve, même si la ligne existante dispose d'un potentiel de trafic prouvé au sol de 6 ou 8 avions !

#### 2.2 Ce que le code mesure déjà comme « besoin »

Le code dispose déjà de plusieurs métriques de calibrage de flotte :

1. **Le stock physique en attente aux aéroports** (`ai/OpexAI/task_air.nut:763-774`) :
   - `waitA` et `waitB` lus via `AIStation.GetCargoWaiting(st, line.cargo)` ;
   - `maxWait = max(waitA, waitB)` ;
   - `buildNum = (maxWait - bottom) / planeCap` (où `bottom = min(AIR_FLEET_BUFFER, planeCap)`) ;
   - Si `buildNum < 1` : refus `W` (`OpexAirFleetRefusal(line, year, "W")`, `:776`).
2. **Le flux mensuel de production urbaine** (`ai/OpexAI/builder_air.nut:329-369`) :
   - `OpexAirDemandCap(line, catalog, lines)` calcule `monthlyDemand = demandA + demandB` à partir de `AITown.GetLastMonthProduction` divisé par le nombre de lignes partagées à chaque aéroport (`routesA`, `routesB`) ;
   - En déduit `demandCap = OpexCeilDiv(monthlyDemand, trip.capacityPerPlane)` (`:361-364`). Utilisé sous `AIR_DEMAND_PLAN` (`:760, :1298-1302`).
3. **Le plafond physique d'absorption de piste** (`ai/OpexAI/builder_air.nut:402-440`) :
   - `OpexAirCadenceCap(line, catalog, lines)` modélise le holding pattern : `cap = (roundTripDays / effectiveSpan.tofloat()).tointeger() + 1` avec `effectiveSpan = OpexAirportStationDateSpan(airportType) * routes` (`:386-397`).
   - Utilisé dans `task_air.nut:706` : `physicalMaxPlanes = OpexAirCadenceCap(line, this._catalog, this._lines)`.
4. **La marge physique de la ligne** (`ai/OpexAI/task_air.nut:784`) :
   - `room = maxPlanesForAirport - have`, où `maxPlanesForAirport = min(physicalMaxPlanes, AIR_MAX_PLANES_PER_ROUTE)`.

#### 2.3 Réfutations causales antérieures (à ne pas reproduire)

La consultation de `docs/taches.md` et de `docs/journal_2026-09-13.md` rappelle les impasses fermement établies :

| Expérience / Levier | Réfutation dans l'historique | Résultat mesuré | Source |
|---|---|---|---|
| `air_fleet_buffer = -1` (suppression de la réserve d'attente W) | Réserve aérienne indispensable : forcer des avions sans passagers au sol détruit le capital | **0 V / 20 D**, −5,093 M£ de valeur, −666 k£/an de profit | `docs/taches.md:1089-1092`, `journal_2026-09-13.md:2356` |
| Seuil de buffer à 50 % de capacité | Forcer la profondeur consomme le capital sans rentabilité | Graine 42 × 3 ans : **−240,2 k£/an**, **−32,3 % de valeur** | `docs/taches.md:1401` |
| `air_cadence_cap = 0` (suppression du cap de cadence) | Suppression du plafond de holding pattern | 21 V / 19 D (neutre, non concluant) | `docs/taches.md:1091`, `journal_2026-09-13.md:2357` |
| Causalité fréquence/rating | « 1 avion ⇒ mauvais rating ⇒ refus W » est réfutée | Opex a un meilleur rating qu'AAA sur 4/7 marchés mais 5 fois moins de profit/capacité | `docs/taches.md:1413-1420` |

**Règle d'or** : Le refus `W` et la réserve `AIR_FLEET_BUFFER` sont des gardes indispensables qui protègent la trésorerie. Le contrat ne touche pas à l'admission d'un renfort, mais uniquement au **dimensionnement du lot (`want`) lorsque le renfort est légitime**.

#### 2.4 Spécification de la proposition du §12

La proposition du §12 de la fiche 11 s'énonce :
« *un seul projet de flotte par ligne, avec `want` égal au besoin mesuré et sans le plafond de 4. Pas $k$ variantes par ligne : la régénération en $O(\text{projets} \times \text{lignes})$ grossirait d'environ 20 %.* »

On introduit le réglage `c69_fleet_demand_batch` (défaut 0).  
Sous `c69_fleet_demand_batch = 0` : comportement historique (`maxAddedPerPass` borné à 4, `task_air.nut:779`).

Sous `c69_fleet_demand_batch = 1` :
1. Dans `_resizeAirFleets` (`ai/OpexAI/task_air.nut:781-796`) :
   - Le besoin physique mesuré par le stock au sol est `buildNum = (maxWait - bottom) / planeCap` (sous la condition `maxWait > bottom && planeCap > 0`, inchangée).
   - Au lieu de borner à 4, le besoin admis est :
     $$\text{needPlanes} = \text{buildNum}$$
   - Le lot proposé au portefeuille devient :
     $$\text{want} = \min(\text{room},\ \text{needPlanes})$$
     où `room = maxPlanesForAirport - have` respecte strictement le plafond physique d'aéroport `OpexAirCadenceCap`.
2. Dans `OpexProjectFromFleet` (`ai/OpexAI/projects.nut:407-455`) :
   - Le projet unique émis pour cette ligne porte ce `want` débridé.
   - `profit = perPlaneProfit * want` et `capital = planePrice * want`.
   - Si 6 avions attendent au sol sur une ligne rapportant 25 k£/avion, le projet pèse $P = 150\text{ k£}$ pour un capital de $6 \times 30\text{ k£} = 180\text{ k£}$.
   - En régime « décision » ($K_{dec} > C$), son score $P / K_{dec}$ bat légitimement une nouvelle ligne neuve à 80 k£, permettant de saturer les aéroports existants avant d'en construire d'autres.

#### 2.5 Coût en opcodes

- **Aucun projet supplémentaire généré** : exactement 1 projet de flotte par ligne aérienne éligible, préservant la complexité de régénération $O(\text{projets} \times \text{lignes})$.
- **Gain indirect** : Permet de combler le déficit de flotte en moins de passes de portefeuille, économisant des cycles de décision pour d'autres chantiers.

#### 2.6 Critères de passage écrits d'avance

| Étape | Protocole | Critères de succès | Sinon |
|---|---|---|---|
| **Étape 1 — Diagnostic 5×6** | 5 graines × 6 ans (`100 12345 42 7 999`), duel contre AAAHogEx | ≥ 3 graines sur 5 avec `profit_year` en hausse vs référence C69 ; apparition de lots de flotte > 4 construits | **Fermer la fiche flotte** : l'asymétrie de lot n'est pas le frein |
| **Étape 2 — Banc 20×10** | 20 graines × 10 ans apparié duel | Test des signes ≥ 15/20 ($p < 0{,}05$), profit annuel moyen > +50 k£/an, garde −5 % valeur | Maintien du réglage à 0 |

#### 2.7 Ce que ce contrat ne fait pas
- Il ne supprime ni `AIR_FLEET_BUFFER` ni le refus `W` (gardes causales C50b préservées).
- Il ne génère pas de variantes multiples par ligne ($k$ projets avec $want \in \{1, \dots\}$ restent interdits).
- Il ne modifie pas le calcul de `perPlaneProfit` ni le plafond physique de cadence `OpexAirCadenceCap`.
- Il ne touche pas aux modes rail ni route.


---

# Annexe C — échec franc : C71

## C71 — Reproduire le côté génération du régime riche d'AAAHogEx

**Contrat écrit avant code, 2026-09-21. Aucun code, aucun banc, aucun diagnostic dans ce document.**  
Contexte : dépôt `/home/deploy/projects/openttd-ml/.wt_c69` (branche `c69-goulot-decision`).  
Références directes : `docs/11_goulot_decision.md` (§0, §2, §9, §12, §15-§16), `docs/12_calibration_par_mode.md` (C70), `docs/aaahogex_evaluation.md`, et conventions `ai/OpexAI/CLAUDE.md`.

---

### 0. Déclenchement du Cas C et fermeture de C69

#### 0.1 Le verdict du banc d'autorité
Le banc officiel 20×10 en duel de l'étape 4 (`c70_c69` contre `c70`) a été évalué selon les critères écrits d'avance au §10 de `docs/11_goulot_decision.md` :
- Test des signes sur `profit_year` ≥ 15/20 ($p < 0{,}05$) ;
- Écart moyen de `profit_year` > +50 k£/an ;
- Garde de −5 % sur `company_value`.

**Constat du Cas C** : Le levier échoue (≤ 9 victoires sur 20 ou écart moyen de profit annuel négatif ou nul). Le goulot de décision appliqué uniquement à l'arbitrage final du portefeuille dans `projects.nut` ne bat pas AAAHogEx en duel.

#### 0.2 Fermeture de C69
Conformément à la règle de décision explicite du 2026-09-21 formulée au §0 de `docs/11_goulot_decision.md` (lignes 8-11 et 16-18) :
1. **La fiche C69 est formellement fermée** : le réglage `c69_decision_bottleneck` reste fixé à son défaut 0 dans `ai/OpexAI/info.nut` (ligne 128) et `settings.nut` (ligne 116).
2. **Hypothèse d'échec (non démontrée)** : Comme anticipé au §9 (Risque 1, lignes 241-246) et au §12 (lignes 338-340) de `docs/11_goulot_decision.md`, modifier l'ordonnancement final dans `projects.nut` est inopérant si le vivier de projets est **stérilisé en amont** par des critères de densité pure (`TOP_K = 20` pour le rail, `ROAD_TOP_K = 48` pour la route, `PROJECT_TOP_K = 64`). Le sélecteur de portefeuille n'avait simplement rien de volumineux ni de très profitable à choisir au moment où l'entreprise devenait riche.
3. **Ouverture de C71** : La suite décidée d'avance est d'ouvrir la fiche C71 pour « reproduire le côté génération du régime riche d'AAAHogEx, pas son classement » (`docs/11_goulot_decision.md`, ligne 339).

---

### 1. Dissection du régime riche d'AAAHogEx (`ai/AAAHogEx-115`)

Toutes les lignes ci-dessous ont été vérifiées directement dans le code source d'AAAHogEx-115 présent dans `ai/AAAHogEx-115/`.

| Mécanisme AAAHogEx | Fichier et lignes vérifiés | Comportement en régime pauvre (`roiBase`) | Comportement en régime riche (`!roiBase`) | Ce que cela change quand l'entreprise est riche |
|---|---|---|---|---|
| **1. Choix du régime de profit** | `main.nut:781-807` (`CalculateProfitModel`) | `roiBase = true`, `buildingTimeBase = false`, `vehicleProfitBase = false` (l. 783-785) si `!IsRich()` ou inflation. | `roiBase = false` ; bascule vers `buildingTimeBase` si `room >= 100` et `current < max * 0.7` (l. 796-800), sinon `vehicleProfitBase` (l. 805). | Abandonne la rentabilité par livre immobilisée (ROI). Maximise le revenu par unité de temps de construction (`buildingTimeBase`), puis par véhicule quand le plafond de véhicules approche. |
| **2. Seuil d'acceptation de rentabilité** | `main.nut:1054-1057` (`ScanPlaces`) | Rejet immédiat si `roiBase && next.estimate.value < 200` (l. 1054-1057). | Le test est inactif car `!roiBase` ; les candidats avec `estimate.value < 200` sont construits. | Lève le filtre d'exclusion de rentabilité unitaire minimale : quand l'argent abonde, construire une ligne moyennement efficace vaut mieux que ne rien construire. |
| **3. Production standard et score des sources** | `main.nut:1425, 1439, 1469, 1483, 1498-1507` (`ScanPlacesGen`) | `stdProduction = 0` puis `max(stdProduction, production)` (l. 1439, 1469). Score : `r.score <- maxValue * 1000 + r.production` (l. 1501). | `stdProduction = 890` (l. 1425). Score : `r.score <- maxValue / 100 * r.production` (l. 1503) sous `buildingTimeBase`. | **Bascule majeure de génération** : au lieu d'un départage additif où le ROI domine écrasant la production, le score des sources devient **multiplicatif par le volume**. Les sources à gros débit (890 t/mois) évincent totalement les petites sources. |
| **4. Chaînes d'approvisionnement (feeders)** | `main.nut:2766-2774`, appelé dans `route.nut:3519` | `if (roiBase) return [];` (l. 2767-2769). Aucun apport amont n'est recherché ni construit. | Recherche et construit des lignes secondaires d'apport (`SearchAndBuildToMeetSrcDemandMin`) vers l'industrie source pour amorcer ou booster sa production (l. 2771). | Investit son surplus de capital pour alimenter les industries de transformation en matières premières afin de gonfler la cargaison disponible pour la ligne principale. |
| **5. Extension de lignes existantes** | `main.nut:3132-3147`, `3149-3175`, appelé dans `main.nut:1240` et `route.nut:3582` | `if (roiBase) return null;` (l. 3133-3135). Aucune extension de ligne n'est tentée. | Boucle `while (SearchAndBuildAdditionalDest(...) != null)` (l. 3137-3140) pour étendre les lignes construites vers autant de destinations successives que possible. | Transforme les liaisons simples point-à-point en lignes longues multi-arrêts maillées, captant du volume additionnel sur l'infrastructure existante. |
| **6. Déclencheur de richesse (`_IsRich`)** | `main.nut:4324-4332` (`_IsRich`) | Évalué dans `IsRich()` (l. 4317-4322). Condition : voir détail §1.1. | Retourne `true` dès que les seuils de liquidités et d'emprunt sont atteints. | Bascule globale binaire de l'IA, pilotée par des constantes financières en dur. |

#### 1.1 Détail du déclencheur `_IsRich()` d'AAAHogEx (`main.nut:4324-4332`)
```squirrel
function _IsRich() {
    local usableMoney = HogeAI.GetUsableMoney();
    local loanAmount = AICompany.GetLoanAmount();
    if(usableMoney > HogeAI.GetInflatedMoney(10000000)) return true;
    return ((usableMoney > HogeAI.GetInflatedMoney(500000) && HasIncome(100000))
        || usableMoney > HogeAI.GetInflatedMoney(2000000)) 
            && (loanAmount == 0 || prevLoadAmount > loanAmount);
}
```
Ce déclencheur repose sur des **constantes financières en dur** :
- `usableMoney > 10 000 000 £` (inconditionnel) ;
- ou (`usableMoney > 500 000 £` ET revenu trimestriel ≥ 100 000 £) ;
- ou `usableMoney > 2 000 000 £` ;
- avec la condition obligatoire que l'emprunt soit totalement remboursé (`loanAmount == 0`) ou en cours de diminution (`prevLoadAmount > loanAmount`).

Ces seuils de 500 k£ et 2 M£ sont arbitraires et dépendent de l'inflation.

---

### 2. Inventaire dans OpexAI et antériorités dans `taches.md`

Pour chacun des mécanismes ci-dessus, voici l'état des lieux dans OpexAI, les équivalents existants ou absents, et l'historique des bancs documentés dans `docs/taches.md` et `docs/aaahogex_evaluation.md`.

#### 2.1 Tableau comparatif des mécanismes dans OpexAI

| Mécanisme AAAHogEx | Présence dans OpexAI | Fichiers et lignes dans OpexAI | Historique dans `taches.md` et fiches | Statut pour C71 |
|---|---|---|---|---|
| **1. Choix du régime de profit** | Portefeuille : `P/C` historique. C69 a tenté $P/\max(C, K_{dec})$ au portefeuille seul. Pas de bascule de régime en génération. | `projects.nut:685-716` (`fundScore`), `probes.nut:938-1010` (`OpexC69ComputeKDec`). | C49 (`06_denominateur_variable.md`) : 9 V / 11 D (neutre). C69 étape 3 (5×6) : 2 V / 3 D en duel. | ⛔ **Fermé par Cas C** : modifier le seul classement du portefeuille ne suffit pas. |
| **2. Seuil d'acceptation `value < 200`** | Plancher de portefeuille `PORTFOLIO_FLOOR_PCT = 0`. Filtre de ratio minimal `MIN_RATIO = 500` (rail). | `settings.nut:325`, `candidates.nut:27`, `candidates.nut:808-812`. | C35.4 / C49 : plancher 50 % bancé à **4 V / 16 D au 20×10** (`11_goulot_decision.md` §6). Rejet formel. | ⛔ **Réfuté** : les filtres d'exclusion appauvrissent le vivier et provoquent des arrêts de construction. |
| **3. Production standard et score des sources** | **ABSENT** au niveau des sources. Toutes les industries et villes sont scannées, mais le vivier est **tronqué en amont par la densité pure** via `OpexTopK`. | Rail : `candidates.nut:26` (`TOP_K = 20`), `:809` (`ratio`), `:1877` (`OpexTopK`). Route : `candidates.nut:1962` (`ROAD_TOP_K = 48`), `:2069`, `:2675`. Portefeuille : `projects.nut:24` (`PROJECT_TOP_K = 64`). | `11_goulot_decision.md` §9 Risque 1 et §12 ligne 340 : « appliquer le même score aux troncatures amont (`TOP_K`, `ROAD_TOP_K`) ». Jamais bancé isolément. | ✅ **Piste prioritaire retenue** (voir justification §3). |
| **4. Chaînes d'approvisionnement (feeders)** | Autrefois présent pour bus/courrier vers aéroports (`task_feeders.nut`). Totalement absent pour le fret industriel. | Nettoyé de `candidates.nut`, `builder_road.nut`, `settings.nut`, `info.nut`. | `docs/taches.md` lignes 936-950 (décision du 2026-09-17) : `feeder_candidates=1` bancé en 5×6 apparié : **4 défaites / 1 victoire**, profit −105 k£/an, valeur −14,36 %. Code retiré. | ⛔ **Réfuté et clos** : les feeders autonomes dégradent fortement l'économie. Ne pas rouvrir. |
| **5. Extension de lignes existantes** | Route : `OpexRoadExtensionCandidates` (ajoute des arrêts de bus à une ligne). Rail : absent (uniquement `STATION_JOIN`, raccordement en gare commune). | Route : `candidates.nut:2255-2332`, `task_road.nut:12-54`, `settings.nut:333` (`ROAD_PAX_EXTENSIONS = false`). Rail : `lines.nut`, `candidates.nut:1535-1541`. | Revue B4 (`docs/taches.md` lignes 979-985) : 13 `feeder_extension` et seulement **3 `bus_pax_extension`** en 6 ans sur 5 graines. L'extension routière pèse un volume négligeable. | ⚠️ **Secondaire / trop lourd** : la route est marginale ; le rail exigerait un refactoring d'A* et de signalisation démesuré. |
| **6. Déclencheur de richesse sans constante** | C69 a créé le calcul continu de $K_{dec} = F \times \tau$ sans aucune constante en dur. | `probes.nut:938-1010` (`OpexC69ComputeKDec`), `ledgers.nut:780`. | C69 étape 1 (§13.1-§13.2) : C1 validé (5/5 graines). $K_{dec}$ mesuré à 0 en 1970, 39–78 k£ en 1971, 144–283 k£ en 1973, 223–313 k£ en 1975. | ✅ **À réutiliser obligatoirement** pour piloter C71 sans seuil en dur. |

#### 2.2 Analyse des enseignements de `aaahogex_evaluation.md`
Le document `docs/aaahogex_evaluation.md` souligne plusieurs points structurants :
1. **Évaluation économique par la production** (§5bis, lignes 173-179) : « Le score n'est pas population_a * population_b / distance comme chez nous : la variable quantitative est la production de cargo attendue... ».
2. **Fonction objectif selon la contrainte active** (§5quinquies, lignes 368-376) : « AAAHogEx change de fonction objectif selon la contrainte active. Quand la compagnie manque d'argent, il classe par ROI ; riche et loin du plafond de véhicules, par revenu rapporté à un temps de construction... Son rythme initial vient donc d'un arbitrage de capital, puis d'un arbitrage de débit. »
3. **Le piège des règles structurelles lourdes** (§3, lignes 100-116) : Ne rien porter de la machinerie interne d'AAAHogEx (GPL v3, complexité excessive, 37 500 lignes), mais s'inspirer de ses grandeurs physiques.

---

### 3. Choix et justification du premier mécanisme à reproduire : C71

#### 3.1 Élimination motivée des autres options
1. **Les chaînes d'approvisionnement (feeders)** : Formellement exclues. Le banc apparié 5×6 du 2026-09-17 (`results/review_feeder_candidates_5x6_20260917.json`, `docs/taches.md:945-950`) a démontré un effondrement économique (4 défaites, 1 victoire, −105 350 £/an de profit, −14,36 % de valeur de compagnie). Le code a été retiré. Rejouer cette piste violerait les décisions antérieures.
2. **Le seuil d'acceptation minimal (`value < 200`)** : Formellement exclu. Filtrer les candidats a déjà échoué dans C35.4 et C49 (le plancher de portefeuille C35.4 a donné 4 V / 16 D au 20×10). OpexAI a besoin de proposer de gros projets, pas d'interdire les petits projets rentables quand il n'y a rien d'autre.
3. **L'extension de lignes existantes (multi-destinations)** :
   - Côté route, `ROAD_PAX_EXTENSIONS` (`candidates.nut:2255`) ne produit que 3 extensions en 6 ans (revue B4) ; la route ne pèse que 2 des 156 divergences C69 (`11_goulot_decision.md` §13.3).
   - Côté rail, OpexAI est conçu autour de lignes point-à-point strictes (`stationA` / `stationB`). Construire des extensions multi-destinations exigerait une réécriture complète du planificateur de liaisons, des ordres de trains et de la signalisation de passage, avec un coût de développement et un risque de régression critique.

#### 3.2 Le mécanisme retenu : La sélection amont orientée volume / production
Le mécanisme d'AAAHogEx le plus puissant, le plus propre et le plus directement transposable est sa **pondération des candidats par le volume en régime riche** (`main.nut:1500-1506` : `r.score <- maxValue / 100 * r.production`).

Dans OpexAI, pourquoi C69 a-t-il échoué en Cas C ?
- Dans `candidates.nut`, `OpexPaxCandidates` et `OpexFreightCandidates` génèrent toutes les paires envisageables dans le tableau local `all` (~300 à 700 candidats, `candidates.nut:951`).
- Mais immédiatement après, `candidates.nut:1877` exécute :
  ```squirrel
  local best = OpexTopK(all, TOP_K); // TOP_K = 20
  ```
  et `candidates.nut:2675` exécute :
  ```squirrel
  local best = OpexTopK(all, ROAD_TOP_K); // ROAD_TOP_K = 48
  ```
- Dans `OpexTopK` (`candidates.nut:954-966`), les candidats sont classés exclusivement sur `candidate.ratio`.
  - Pour le rail (`candidates.nut:809`) : `ratio = opcodeRatio + (adjustedRoi * 15)`, où `opcodeRatio = (profitAnnual * 1000) / iterations` et `adjustedRoi` est proportionnel à `profitAnnual / capital`.
  - Pour la route (`candidates.nut:2069`) : `ratio = (profitAnnual * 1000) / iterations`.
- **Conséquence directe** : Le tri amont divise systématiquement le profit par le capital ou par les itérations d'A*. Une mine de charbon produisant 800 t/mois avec une longue ligne ferroviaire (capital 120 k£) présente un ratio de densité bien inférieur à une petite desserte locale de 50 t/mois (capital 15 k£). Les 20 places de `TOP_K` sont alors **intégralement monopolisées par des projets nains à fort ratio**.
- Les projets à fort volume et fort profit absolu sont **jetés à la poubelle dès la génération amont** (`topKOmitted`, `candidates.nut:1881`), avant même que `projects.nut` ne voie leur existence.
- Quand l'entreprise accumule des millions en caisse, le sélecteur de portefeuille ne peut choisir que parmi les 20 nains que `TOP_K` lui a laissés.

#### 3.3 Transposition sans constante en dur via $K_{dec}$
Pour éliminer les seuils en dur d'AAAHogEx (500 k£, 2 M£) tout en respectant l'esprit de sa formule de volume (`maxValue / 100 * r.production`), la bascule du tri dans `OpexTopK` réutilise directement $K_{dec} = F \times \tau$ issu de C69 (`probes.nut:938-1010`) :
- Quand l'entreprise est pauvre ($K_{dec} \le C$, ou en 1970 avec $K_{dec} = 0$) : le classement amont reste le ratio de densité actuel (`candidate.ratio`), assurant une **stricte neutralité d'amorçage au bit près**.
- Dès que l'entreprise s'enrichit ($K_{dec} > C$) : le dénominateur de capital s'efface devant le coût de décision $K_{dec}$, et le score amont devient strictement proportionnel au **profit annuel absolu** (qui est le produit direct du volume de production par le tarif de transport). Les sources à forte production remontent naturellement dans le top 20 de `TOP_K`.

---

### 4. Spécification du contrat C71

#### 4.1 Définition du levier
- **Nom du contrat** : C71 — Troncature amont du vivier sous goulot de décision (`TOP_K` rail et `ROAD_TOP_K` route sous $K_{dec}$).
- **Réglage unique** : `c71_upstream_bottleneck`, entier (0 ou 1), **défaut 0** dans `info.nut` et `settings.nut`.
- **Principe** : Appliquer le score de goulot de décision lors du tri amont `OpexTopK` dans `candidates.nut`, afin que les projets à fort volume ne soient plus éliminés au profit exclusif des petits projets à forte densité de capital.

#### 4.2 Formule mathématique et substitution de score
Dans `candidates.nut:954`, pour chaque candidat évalué par `OpexTopK(all, k)` :

$$\text{score}_{\text{amont}} = \begin{cases} 
\text{candidate.ratio} & \text{si } \texttt{c71\_upstream\_bottleneck} = 0 \text{ ou } K_{dec} = 0 \\
\dfrac{\text{profitAnnual} \times 1000}{\max(\text{capital},\ K_{dec})} & \text{si } \texttt{c71\_upstream\_bottleneck} = 1 \text{ et } K_{dec} > 0 
\end{cases}$$

Où :
- $\text{profitAnnual}$ est le profit annuel net estimé du candidat (`economics.profitAnnual`) ;
- $\text{capital}$ est le capital d'infrastructure et matériel roulant estimé du candidat (`economics.capital`) ;
- $K_{dec} = F \times \tau$ est calculé par `OpexC69ComputeKDec()` (`probes.nut:938`), une seule fois au début du cycle de génération de candidats.

#### 4.3 Comportement aux limites et propriétés garanties (P1 à P7)
1. **P1 — Neutralité d'amorçage (1970)** : Durant l'année 1970, $F = 0 \implies K_{dec} = 0$. Le score sous C71 est alors calculé sur $\max(\text{capital}, 0) = \text{capital}$. L'ordre est rigoureusement identique au ratio ROI de base, et le smoke 1×1 doit afficher une **identité au bit près** avec le défaut.
2. **P2 — Bascule continue sans constante en dur** : Aucun seuil arbitraire (ni 500 k£, ni 2 M£). La bascule s'opère candidat par candidat selon son coût propre : une petite ligne de bus (capital 12 k£) bascule dès 1971 quand $K_{dec} \approx 40\text{ k£}$ ; une ligne ferroviaire lourde (capital 150 k£) ne bascule qu'en 1973-1974 quand $K_{dec} \approx 180\text{ k£}$.
3. **P3 — Aucun filtre d'exclusion** : Le nombre de candidats retenus en amont reste exactement `TOP_K = 20` pour le rail et `ROAD_TOP_K = 48` pour la route. Aucun candidat n'est disqualifié inconditionnellement.
4. **P4 — Orientation volume / production en régime riche** : Quand $K_{dec} > \text{capital}$, le dénominateur $K_{dec}$ est constant pour tous les candidats de la passe. Le tri de `OpexTopK` devient alors un tri pur sur $\text{profitAnnual} = \text{volume} \times \text{tarif} - \text{charges}$. Les sources à 800 t/mois entrent immédiatement dans le vivier final.
5. **P5 — Invariance à l'inflation** : $\text{profitAnnual}$, $\text{capital}$ et $K_{dec}$ (dérivé des revenus trimestriels récents) évoluent dans la même unité monétaire courante.
6. **P6 — Monotonie** : À capital égal, une augmentation du profit annuel ne peut jamais rétrograder un candidat. À profit égal, une augmentation du capital ne peut jamais l'avancer.
7. **P7 — Coût calculatoire marginal** : Le calcul de $K_{dec}$ est mutualisé (1 appel par génération), et l'évaluation du score dans `OpexTopK` n'ajoute qu'un `max()` par candidat.

#### 4.4 Points d'insertion dans le code
1. **Lecture de $K_{dec}$ dans la génération** (`candidates.nut:1850` et `candidates.nut:2650`) :
   Au début de `OpexBuildCandidates` et `OpexRoadCandidates`, si `C71_UPSTREAM_BOTTLENECK` est actif (ou sous sonde), appeler `local kDecData = OpexC69ComputeKDec(); local kDec = kDecData.K_dec;`.
2. **Tri dans `OpexTopK`** (`candidates.nut:954-966`) :
   Passer `kDec` en paramètre optionnel à `OpexTopK(all, k, kDec = 0)`.
   Si `kDec > 0`, comparer sur le score goulot au lieu de `candidate.ratio`.
3. **Enregistrement des dates de construction** :
   Le suivi `C69_BUILD_DATES` et le calcul `OpexC69ComputeKDec()` créés pour C69 dans `probes.nut:938-1010` sont conservés et activés lorsque `c71_upstream_bottleneck = 1` ou sous la sonde dédiée.

---

### 5. Ce que ce contrat NE fait PAS

Pour éviter toute dispersion ou régression collatérale :
- **Il ne modifie pas les plafonds d'échantillonnage amont** : `TOP_K` reste 20 (`candidates.nut:26`), `ROAD_TOP_K` reste 48 (`candidates.nut:1962`), `PROJECT_TOP_K` reste 64 (`projects.nut:24`).
- **Il ne réactive pas les feeders** : la suppression des feeders du 2026-09-17 est strictement respectée.
- **Il ne touche pas aux extensions de lignes routières** : `ROAD_PAX_EXTENSIONS` reste inactif à son défaut `false` (`settings.nut:333`).
- **Il ne modifie pas l'A\* ferroviaire ni le placement de gares** : aucun multi-destinations ferroviaire n'est introduit.
- **Il n'introduit aucun seuil financier en dur** : les montants 500 k£, 2 M£ et 10 M£ d'AAAHogEx sont totalement ignorés.
- **Il ne modifie pas la sélection interne du matériel roulant** : le choix de l'avion ou du train sur une ligne donnée reste régi par les modèles actuels.

---

### 6. Coût en opcodes estimé

Unité de référence : **186 000 opcodes ≈ 1 jour de jeu** (mesure C39.6).

| Poste de calcul | Coût unitaire par passe | Fréquence | Coût total sur 6 ans | Impact relatif |
|---|---:|---|---:|---|
| Calcul de $F$, $\tau$ et $K_{dec}$ (`OpexC69ComputeKDec`) | ~1 000 opcodes | 1 fois par régénération de vivier (~20/an) | ~0,12 M opcodes | Négligeable (< 0,03 %) |
| Calcul du score amont dans `OpexTopK` (rail : ~600 candidats, route : ~300) | ~1 500 opcodes | 1 fois par passe de vivier | ~0,18 M opcodes | Négligeable (< 0,05 %) |
| **Total du levier C71** | **~2 500 opcodes** | **par génération** | **~0,30 M opcodes** | **< 0,1 % (moins de 2 jours de jeu)** |
| Sonde passive Étape 1 (double tri comparatif et journal) | ~6 000 opcodes | par passe sous sonde | ~0,70 M opcodes | Diagnostic uniquement |

---

### 7. Protocole expérimental et critères de passage écrits d'avance

#### Étape 1 — Sonde passive, aucune décision changée
- **Instrumentation** : Réglage `probe_c71 = 1` (défaut 0). À chaque exécution de `OpexTopK` (rail et route), calculer en parallèle le classement de contrôle actuel et le classement C71.
- **Métriques publiées** :
  - $K_{dec}$ au moment du tri ;
  - Nombre de candidats du top 20 rail (et top 48 route) qui diffèrent entre les deux classements ;
  - Somme des profits annuels $\sum P$ des 20 candidats retenus par la politique actuelle vs la politique C71 ;
  - Production mensuelle médiane des sources retenues dans les deux classements.
- **Protocole** : 5 graines × 6 ans (`100 12345 42 7 999`), en duel contre AAAHogEx (carte partagée).

| Critère d'étape 1 | Grandeur mesurée | Seuil requis pour continuer | Action si échec |
|---|---|---|---|
| **C1 — Exposition amont** | Part des passes où le top 20 rail change d'au moins 3 candidats (années 2 à 6) | ≥ 25 % des passes sur ≥ 4/5 graines | **Fermer C71** : le vivier `all` ne contient pas de candidats alternatifs à proposer. |
| **C2 — Gain de volume** | Ratio de la production mensuelle médiane des sources du top 20 (C71 / actuel) quand $K_{dec} > 50\text{ k£}$ | ≥ 1,50 en médiane sur les 5 graines | **Fermer C71** : le changement de tri ne sélectionne pas des sources significativement plus volumineuses. |
| **C3 — Potentiel de profit** | Ratio du profit cumulé des candidats du top 20 ($\sum P_{\text{C71}} / \sum P_{\text{actuel}}$) | ≥ 1,30 en médiane | **Fermer C71** : gain de profit potentiel insuffisant pour justifier un banc. |

---

#### Étape 2 — Implémentation du levier isolé
- Création du réglage `c71_upstream_bottleneck` dans `info.nut` et `settings.nut`, **défaut 0**.
- Branchement conditionnel dans `candidates.nut` (`OpexBuildCandidates`, `OpexRoadCandidates`, `OpexTopK`).
- **Validation technique obligatoire** :
  - Smoke test 2 graines × 3 ans sans crash (`results/smoke_c71_2x3.json`) ;
  - Test d'identité stricte en 1970 : graine 42, an 1970, bras témoin vs `c71_upstream_bottleneck=1` : **identité au bit près** (zéro divergence d'opcodes ou de décisions tant que $K_{dec} = 0$).

---

#### Étape 3 — Diagnostic 5×6 apparié en duel
- **Protocole** : 5 graines × 6 ans (`100 12345 42 7 999`), duel contre AAAHogEx sur carte partagée.
- **Comparaison appariée** : Référence `c70` contre Variante `c70_c71` (`c71_upstream_bottleneck=1`).
- **Critères de passage pour aller en étape 4** :
  - ≥ 3 victoires sur 5 sur `profit_year` à 6 ans contre la référence ;
  - Écart annuel de profit nul ou non significatif en 1970, naissant à partir de 1971 (année de la première bascule de $K_{dec}$) ;
  - Écart moyen de `profit_year` > 0 en 1975.
- Si < 3 victoires sur 5 en duel : arrêt, pas de banc 20×10.

---

#### Étape 4 — Autorité C66.4 (Banc 20×10 en duel)
- **Protocole** : 20 graines × 10 ans apparié, en duel direct sur carte partagée contre AAAHogEx (plateforme OpenTTD 15.3).
- **Critères stricts d'adoption définitive** (selon `CLAUDE.md`) :
  1. **Test des signes** : ≥ 15 victoires sur 20 ($p < 0{,}05$) sur `profit_year` face à la référence ;
  2. **Gain économique moyen** : écart moyen de `profit_year` > +50 k£/an ;
  3. **Garde de valeur** : `company_value` moyenne pas plus de 5 % sous la référence.
- Si et seulement si ces 3 critères sont satisfaits, `c71_upstream_bottleneck` pourra être proposé pour basculer à 1 par défaut dans `info.nut`.
