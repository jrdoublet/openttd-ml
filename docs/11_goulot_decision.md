# C69 — Facturer le goulot : `P / max(C, F·τ)`

**Contrat écrit avant code, 2026-09-21. Aucun code, aucun banc, aucun diagnostic dans ce document.**
Les références de code visent `master` après la fusion de la PR #12 (`62179fb`).

## 0. Statut, et d'où vient l'autorisation

⚠️ **Décision utilisateur explicite du 2026-09-21** : dernière tentative de faire passer le
classement du ROI au profit **sans constante en dur**, avant de reproduire le mécanisme
d'AAAHogEx (§2) pour avancer.

⛔ **Ne pas présenter cette fiche comme validée.** Sur l'axe « ce que le portefeuille choisit »,
tous les leviers bencés ont perdu ou sont restés neutres, C49 et la frontière λ compris (§6).
Ce qui autorise l'instruction est un choix ; ce qui autorisera l'adoption, c'est le banc C66.4.

🔑 **Si l'étape 1 ferme la fiche, la suite est déjà décidée** : reproduire ce qu'AAAHogEx change
dans sa **génération** quand il devient riche, pas son classement (§12).

---

## 1. Le problème, tel qu'il est mesuré

| fait | mesure | source |
|---|---|---|
| Le classement est une densité pure, à tout moment de la partie | `fundScore = P × 1000 / financeCapital` | `projects.nut:681`, `:699` |
| Un ratio seul est *cheap-first* | `portfolio_v2` isolé : gares **+27 %**, valeur **−24,4 %**, profit **−30,7 %** | `journal_2026-09-02.md:259`, `bench_isolation_3y_20seeds` |
| La trésorerie ne bloque que les premières années | cause `cash` : **53 %** des non-chantiers en 1972, **0 %** en 1974-1975 ; `decision` **92–94 %** après correction du biais | `06_denominateur_variable.md` §9-§10 |
| La caisse s'accumule sans emploi (C68, médiane 5 graines) | **0,2 M£** au 1972-01, **1,3 M£** au 1974-01, **3,3 M£** fin 1975 | `results/opcode_frontier_optimized_final_vs_c68_5x6.json`, bras C68 |
| Les décisions deviennent rares | **168 → 18,3** passes pour 100 jours entre 1971 et 1975 (÷9,2) | C39.6b, `journal_2026-09-13.md:259` |
| Une décision coûte de plus en plus cher | régénération **573 k → 2 355 k** opcodes par appel, environ **38 k par ligne possédée** | C48.1, `journal_2026-09-13.md:2510` |
| Le vivier est souvent vide | **58,6–61,8 %** des passes `projects` | C39.5b, C49 §9 |

**Lecture.** Le capital est la ressource rare pendant environ trois ans ; ensuite, c'est la
**décision** (une passe qui construit, à `PORTFOLIO_MAX_BATCH = 1`). Un classement par ratio
dépense alors des décisions rares sur de petits projets. La question n'est pas *s'il faut*
basculer vers le profit, mais **quand** et **comment**, sans seuil inventé.

---

## 2. Ce que fait AAAHogEx (vérifié dans `ai/AAAHogEx-115`)

| régime | classement | déclencheur |
|---|---|---|
| `roiBase` | `routeIncome × 1000 / (véhicules + construction + coût d'opportunité du transit)` | pas riche, ou inflation (`main.nut:781-786`, `estimator.nut:76-88`) |
| `buildingTimeBase` | revenu / temps de chantier | riche, et un mode garde ≥ 100 places libres et < 70 % du plafond (`main.nut:790-801`) |
| `vehicleProfitBase` | revenu / véhicule | sinon |

`_IsRich()` (`main.nut:4324-4332`) repose sur des **constantes** : argent utilisable > 500 k£ avec
un revenu trimestriel ≥ 100 k£, ou > 2 M£, ou > 10 M£ ; **et** un prêt remboursé ou en baisse.

🔑 **En régime riche, AAAHogEx change aussi ce qu'il génère :**

- seuil de production des sources : adaptatif en `roiBase`, **890** sinon (`main.nut:1425-1469`) ;
- score des sources pondéré par le volume (`main.nut:1500-1506`) ;
- extension de lignes et chaînes d'approvisionnement, **seulement** en riche (`main.nut:2767`, `:3133`) ;
- seuil d'acceptation `value < 200`, **seulement** en `roiBase` (`main.nut:1054`).

Les deux premiers régimes sont les deux limites de la formule du §3. Les constantes de `_IsRich()`
sont ce que le §4 remplace. Les changements de génération sont **hors de ce contrat** (§11).

---

## 3. La formule

### 3.1 Dérivation

À `PORTFOLIO_MAX_BATCH = 1`, un chantier occupe le goulot de l'entreprise pendant :

$$D_i = \max\left(\tau,\ \frac{C_i}{F}\right)$$

- $\tau$ : la durée d'une décision, c'est-à-dire l'intervalle moyen entre deux constructions ;
- $C_i / F$ : le temps nécessaire pour regagner le prix du projet avec le flux de trésorerie
  d'exploitation $F$.

On garde le **max** et non la somme : l'argent s'accumule pendant que l'on décide et construit.
Si le projet coûte moins que ce qu'on gagne pendant une décision, c'est la décision qui limite ;
sinon, c'est l'argent.

Classer par profit par jour de goulot (règle de Smith, qui maximise le profit cumulé quand les
tâches passent une à une sur une ressource unique) donne $P_i / D_i$. En multipliant par $F$,
on obtient une forme sans division par $F$, définie aussi quand $F = 0$ :

$$\boxed{\text{score}_i = \frac{P_i \times 1000}{\max(C_i,\ K_{dec})} \qquad K_{dec} = F \times \tau}$$

🔑 **$K_{dec}$ est ce que l'entreprise gagne pendant une décision.** Un projet moins cher que
$K_{dec}$ ne consomme pas vraiment son capital : il consomme une décision.

### 3.2 Les deux limites

| situation | score | équivaut à |
|---|---|---|
| $K_{dec} \le C_i$ (pauvre vis-à-vis de ce projet) | $P_i \times 1000 / C_i$ | **exactement** le `fundScore` actuel, et le `roiBase` d'AAAHogEx |
| $K_{dec} > C_i$ (riche vis-à-vis de ce projet) | $P_i \times 1000 / K_{dec}$, donc un classement par $P_i$ | profit par décision, le `buildingTimeBase` d'AAAHogEx avec un temps de chantier commun |

🔑 **La bascule se fait projet par projet, et en continu.** Un bus bascule quand $K_{dec}$
dépasse une dizaine de k£, un aéroport quand $K_{dec}$ dépasse son prix. Il n'y a pas de régime
global, pas d'argmax annuel, pas de seuil.

### 3.3 Point d'insertion

Le score remplace `OpexProjectScore(project.profitAnnual, financeCapital)` aux deux branches de
`OpexProjectSelectAffordable` (`projects.nut:681`, `:699`), là où C49 s'était branché.

- $C_i$ reste `financeCapital`, comme aujourd'hui ;
- l'échelle ×1000 est conservée, donc le score est **identique au bit près** quand $K_{dec} \le C_i$ ;
- le bonus `early_slot` continue de multiplier le score (`OpexProjectSelectionScore`, `projects.nut:711`) ;
- $K_{dec}$ est calculé **une fois par appel** de la sélection, jamais par candidat.

---

## 4. Mesurer F et τ sans constante

La seule fenêtre utilisée est **l'année comptable du jeu**, déjà employée par la tâche `report`
et par C49 (§5 de `06_denominateur_variable.md`). Ce n'est pas un nombre inventé.

### 4.1 F — flux de trésorerie d'exploitation

$$F = \frac{\sum_{q=1}^{4} \big(\text{GetQuarterlyIncome}(q) + \text{GetQuarterlyExpenses}(q)\big)}{\text{jours couverts}}$$

- $q = 1..4$ : les quatre derniers trimestres **complets** (moins en début de partie ; le
  dénominateur est alors le nombre de jours réellement couverts) ;
- **le prêt n'entre pas dans F, ni le stock de caisse**. C'est ce qui remplace la condition
  « prêt remboursé » d'AAAHogEx : 300 k£ empruntés ne rendent pas riche ;
- $F \le 0$ (entreprise qui perd de l'argent) ⇒ $K_{dec} = 0$ ⇒ classement ROI. C'est le
  comportement prudent voulu.

🔴 **Correction du 2026-09-21, mesurée à l'étape 1.** La première version ajoutait un terme $I$
(investissements propres) en supposant que `GetQuarterlyExpenses` contenait la construction et
les achats de véhicules. **C'est faux** : graine 42, premier trimestre 1970, dépenses **−3,7 k£**
pour **278 k£** investis. Les deux appels donnent déjà le flux d'exploitation ; ajouter $I$
comptait l'investissement comme un revenu et multipliait $F$ par ~2,5 (K_dec ≈ 80 k£ dès 1970).
Le terme est retiré.

La sonde publie aussi un second estimateur, $F_{veh} = \sum_v$ `GetProfitLastYear`, pour
contrôle. Il n'est pas retenu pour la décision parce qu'il a un an de retard et ignore la
maintenance d'infrastructure.

### 4.2 τ — durée d'une décision

$$\tau = \frac{D}{N}$$

- $D$ : jours de la fenêtre glissante, soit $\min(365, \text{jours depuis le début})$ ;
- $N$ : constructions réussies du portefeuille dans la fenêtre, tous modes et projets de flotte
  compris (`attempt.outcome == "built"` dans `_tryBuildProjects`, `task_projects.nut:350`) ;
- $N = 0$ ⇒ $K_{dec} = 0$ ⇒ classement ROI.

⚠️ **Ambiguïté connue** : quand le vivier est vide, les constructions se raréfient, ce qui
gonfle $\tau$ alors que ce n'est pas la décision qui manque, mais l'offre. Le critère C1 (§10)
le détecte. Si C1 échoue, on remplace $\tau$ par la durée des seules passes qui construisent
(horloge de passe C39.6), sans changer la formule.

---

## 5. Propriétés garanties (à verrouiller par test unitaire à l'étape 2)

1. **Neutralité d'amorçage** : $F = 0$ ou $N = 0$ ⇒ classement actuel au bit près.
2. **Neutralité tant que l'on est pauvre** : si $K_{dec}$ est inférieur au plus petit $C$ du
   vivier, l'ordre est identique à l'actuel, égalités comprises.
3. **Aucun filtre** : le même ensemble finançable est classé et le premier rang existe
   toujours. Le mode d'échec n°1 (« plus rien ne se construit ») est impossible par construction.
4. **Aucun prix tiré du vivier** : pas de LP, pas d'item critique, pas de saturation.
5. **Aucun terme par projet exprimé en opcodes** : $\tau$ est le même pour tous les projets.
6. **Pas de double comptage** : un projet paie son capital **ou** sa décision, jamais les deux.
7. **Invariance à l'inflation** : $F$ et $C$ sont dans la même monnaie courante.
8. **Monotonie** : à capital égal, plus de profit ne baisse jamais le score ; à profit égal,
   plus de capital ne le monte jamais.

---

## 6. Pourquoi ce n'est pas une formulation déjà réfutée

| formulation | résultat | cause de l'échec | différence ici |
|---|---|---|---|
| `shadow_pricing` (C35) | −11,2 % valeur | prix duaux calculés sur un vivier toujours saturé ; `λ_ops × a_ops` incommensurable, plus aucun rail | pas de prix tiré du vivier, pas de terme opcodes (P4, P5) |
| surplus `P − λC` (C35.4) | 7/7 défaites | soustraction, donc profit absolu : « réseau posé, pas rempli » | ratio, jamais de soustraction |
| filtre densité `< λ` (C35.4), `portfolio_floor_pct` | 7/7 défaites ; floor50 **4 V / 16 D** au 20×10 | seuil d'acceptation, donc moins de chantiers | aucun filtre (P3) |
| frontière λ (2026-09-21) | 5×6 : **1,55 M£ contre 5,39 M£**, 0/5 ; 50–97 M opcodes de sélection | λ ≈ 1,7–2,2 tiré du vivier ; 4 à 5 survivants, tous non constructibles | pas de λ, pas de survivants à filtrer |
| empreinte `K/C_dispo + Ops/Φ` (`02_empreinte.md`) | écartée | temps propre à chaque projet en opcodes (rail ×300) ; stock `C_dispo` | temps = la décision, commun à tous ; flux F et non stock |
| C37, verrou calendaire | abandonné | terme calendaire **ajouté** au capital, donc doublon | `max`, pas somme (P6) |
| C49, dénominateur variable | **9 V / 11 D**, neutre | régime annuel par argmax de causes biaisées ; compromis `P/√K` ; seul le classement final change | bascule continue par projet, pilotée par deux flux mesurés. **Même risque sur le dernier point** : voir §9 |

⚠️ **L'objection du §11.1 de `06_denominateur_variable.md`.** La courbe du plancher (0 % → −16,2 %,
50 % → +0,1 %, 75 % → performance −12,4 %) mettait en garde contre le profit absolu nu. Elle a été
mesurée sur **3 ans**, donc dans la phase où la trésorerie est rare. Dans cette phase,
$K_{dec} < C$ pour presque tous les projets, et ce score **reste un ratio**. De plus, un plancher
**exclut** les petits projets, alors qu'ici ils restent classés et sont construits dès qu'il n'y
a rien de mieux.

---

## 7. Ordres de grandeur attendus (à confirmer par la sonde)

Estimations tirées du bras C68 de `opcode_frontier_optimized_final_vs_c68_5x6.json` (médianes
sur 5 graines). $F$ y est approché par `profit_year`. ⚠️ Ce proxy ne soustrait pas
l'investissement (§4.1) ; les valeurs mesurées sont au §13. $N$ est approché par la croissance du réseau (environ +8 gares et +11 à 13 véhicules
par an, soit une dizaine de constructions par an).

| année | $F$ (proxy) | $\tau$ (proxy) | $K_{dec}$ | projets qui passent en régime « décision » |
|---|---:|---:|---:|---|
| 1970 | 0 | — | **0** | aucun : classement actuel |
| 1971 | 0,23–0,61 M£/an | ~30 j | **~20–50 k£** | bus (~12 k£), +1 avion (~35 k£) |
| 1973 | 0,9–1,2 M£/an | ~30–35 j | **~75–115 k£** | nouvelles lignes aériennes (70–115 k£) |
| 1975 | 1,3–1,4 M£/an | ~35 j | **~110–135 k£** | presque tout, sauf le rail lourd, qui reste classé en ratio |

🔑 **Prédiction falsifiable** : les lignes aériennes basculent vers 1973, l'année où C49 voit la
trésorerie disparaître comme cause de non-chantier. Si la bascule mesurée tombe ailleurs, les
définitions de $F$ ou de $\tau$ sont fausses (critère C1).

🔑 **Deuxième prédiction** : sur un banc apparié, l'écart annuel doit être nul en 1970 et
n'apparaître qu'après la première bascule. Un gain dès 1970 signifierait qu'on mesure autre
chose, et il faudrait le dire.

---

## 8. Coût en opcodes

Unité : **186 000 opcodes ≈ 1 jour de jeu** (C39.6), soit environ 400 M sur 6 ans.

| poste | coût | sur 6 ans |
|---|---|---|
| mise à jour de $F$ (8 appels API, un registre d'investissement) | ~1 k par sélection | ~0,1 M |
| $\tau$ (liste des dates de construction de l'année) | négligeable | négligeable |
| score (un `max()` de plus par candidat, ~300 candidats) | ~1,5 k par sélection | ~0,2 M |
| **total du levier** | | **~0,3 M, 1 à 2 jours de jeu, < 0,1 %** |
| sonde de l'étape 1 (second argmax, une ligne de journal par passe) | ~5 k par sélection | ~0,6 M, diagnostic seulement |

Repères : la sélection C68 actuelle coûte ~9 M sur 6 ans ; la frontière λ en coûtait 50 à 97 M.

**Coût indirect.** La régénération coûte environ 38 k opcodes par ligne possédée et par passe
qui construit (C48.1). Ce contrat ne crée pas ce coût, mais il peut le déplacer :

- en moins : moins de petites lignes de bus en 1971-1972 ;
- en plus : si des décisions libérées servent à ouvrir davantage de lignes, chaque ligne
  supplémentaire coûte ~0,27 M par an en fin de partie, soit ~1,5 jour de jeu par an.

À suivre par passe avec les compteurs H5 aux étapes 3 et 4.

---

## 9. Risques connus

1. 🔑 **Le précédent C49** : un changement de classement seul a peu bougé les résultats.
   Hypothèse principale : le vivier est **tronqué en amont** par des critères de densité
   (`TOP_K = 20` pour le rail, `candidates.nut:26` ; `ROAD_TOP_K = 48`, `candidates.nut:1962` ;
   `PROJECT_TOP_K = 64`, `projects.nut:24`). S'il ne contient rien de gros, le régime
   « décision » n'a rien à choisir. Critères C2, C3 et C4.
2. **Biais de prédiction par mode.** En régime « décision », on compare des profits absolus
   entre modes : un mode surestimé l'emporte. Seul cas AIR suivi en détail : 44 k£ réalisés
   pour 79 k£ prédits. La calibration AIR à 104 % a été établie avec l'ancien délai d'aéroport
   de 3 jours. Critère C5.
3. **Malédiction de l'optimiseur.** L'argmax sur le profit absolu favorise le projet le plus
   surestimé, et la variance d'erreur croît avec la taille. Même parade que le point 2.
4. **τ confond rareté de décision et rareté d'offre** (§4.2). Critère C1.
5. **Taille des lots de flotte plafonnée à 4** (`maxAddedPerPass`, `task_air.nut:748`), et
   nouvelles lignes aériennes à **un seul avion** sous `FLEET_PORTFOLIO` (`builder_air.nut:759`).
   Le régime « décision » peut préférer une nouvelle ligne (P ≈ 80 k£) à un +1 avion
   (P ≈ 30 k£), sans pouvoir proposer un lot plus gros. C'est une suite possible (§12), pas ce
   contrat.
6. **Stock de caisse ignoré.** C'est voulu tôt dans la partie (le prêt ne rend pas riche). En
   fin de partie, seul un projet plus cher que $K_{dec}$, comme le rail lourd, reste classé au
   ratio alors que la caisse pourrait le financer. Effet attendu marginal ; la sonde le mesure.

---

## 10. Étapes et critères de fermeture — écrits d'avance

Les seuils ci-dessous sont des **critères d'expérience**, fixés avant le run et non modifiables
après. Ce ne sont pas des constantes de l'IA.

### Étape 1 — sonde passive, aucune décision changée

Sous `probe_portfolio` (`settings.nut:208`), qui active **aussi** le registre de rareté C49 :
C1 se mesure donc sur les mêmes parties. À chaque passe qui construit, publier :

- $F$, $F_{veh}$, $\tau$, $K_{dec}$ ;
- le premier rang actuel et celui du nouveau score : mode, $P$, $C$, et le rang du second dans
  l'ordre actuel ;
- si le premier rang du nouveau score est construit par la politique actuelle dans les **deux
  passes** suivantes.

Chaque année, publier aussi la médiane réalisé/prédit par mode (`LINE_REVENUE`,
`task_report.nut:234`, lignes d'au moins une année pleine).

**Protocole** : 5 graines × 6 ans, contexte duel C66 (carte partagée avec AAAHogEx), graines de
C49 (`100 12345 42 7 999`) pour pouvoir comparer.

| critère | mesure | continuer si | sinon |
|---|---|---|---|
| **C1** cohérence | écart entre l'année où $K_{dec}$ dépasse le capital médian des lignes aériennes élues et l'année où `cash` passe sous `decision` dans le registre C49 | ≤ 1 an, sur ≥ 4 graines sur 5 | revoir $\tau$ (§4.2), puis refaire la sonde ; pas de banc |
| **C2** exposition | part des passes qui construisent, années 2 à 6, où les deux premiers rangs diffèrent | ≥ 20 % | **fermer** : neutre par construction |
| **C3** ensemble ou ordre | parmi ces passes, part où le premier rang du nouveau score est construit quand même dans les 2 passes suivantes | ≤ 50 % | **fermer** : seul l'ordre change (mécanisme de C49) |
| **C4** ampleur | médiane de $P(\text{nouveau}) / P(\text{actuel})$ sur les passes qui diffèrent | ≥ 1,5 | **fermer** : gain trop faible pour un 20×10 |
| **C5** calibration | écart max/min des ratios réalisé/prédit médians par mode | ≤ 1,5 | ouvrir d'abord une fiche de calibration par mode ; l'étape 2 attend |

### Étape 2 — le levier, un seul changement

Réglage `c69_decision_bottleneck`, **défaut 0**. Rien d'autre ne change : ni le vivier, ni les
troncatures amont, ni la flotte, ni les seuils.

- tests unitaires des propriétés P1 à P8 (§5) ;
- smoke 2×3 ;
- smoke 1×1 sur 1970, pendant que $F = 0$ : **identité au bit près** avec le défaut.

### Étape 3 — diagnostic 5×6 apparié, en duel

Bras défaut contre `c69_decision_bottleneck=1`. On continue si :

- ≥ 3 graines sur 5 gagnent sur `profit_year` ;
- les deux prédictions du §7 tiennent : écart nul en 1970, divergence après la bascule.

⛔ Ne pas conclure d'un 5×6 (précédent C41.47).

### Étape 4 — autorité C66.4

20 graines × 10 ans apparié en duel. Adoption seulement si le test des signes donne **≥ 15/20**
avec p < 0,05, si l'écart moyen de `profit_year` dépasse **+50 k£/an**, et si la garde de −5 % sur
`company_value` est respectée.

---

## 11. Ce que ce contrat ne fait pas

- **Il ne touche pas la génération** : `TOP_K`, `ROAD_TOP_K`, filtres du vivier, sources et
  extensions restent tels quels.
- **Il ne change pas la taille des lots de flotte**, ni la profondeur initiale des lignes aériennes.
- **Il ne touche pas le choix de variante à l'intérieur d'un groupe** : l'avion d'une route
  reste choisi par C68 (profit maximal).
- **Pas de τ propre à un mode, pas de stock de caisse** : ce seraient des raffinements
  conditionnels.
- **Pas de seuil d'acceptation** (« ne rien construire ce tour ») : hors périmètre, comme au §8
  de C49.

---

## 12. Suites conditionnelles

| si | alors |
|---|---|
| C2, C3 ou C4 ferment la fiche | la rareté n'est pas dans le classement : reproduire le **côté génération** du régime riche d'AAAHogEx (sources à forte production, extension des lignes existantes), pas son classement |
| C4 passe mais l'étape 3 est neutre | appliquer le même score aux troncatures amont (`TOP_K`, `ROAD_TOP_K`) |
| la phase « décision » laisse des lignes sous-remplies | un seul projet de flotte par ligne, avec `want` égal au besoin mesuré et sans le plafond de 4. **Pas** k variantes par ligne : la régénération en O(projets × lignes) grossirait d'environ 20 % |
| C5 révèle un biais par mode | facteur de calibration mesuré par mode (ratio réalisé/prédit glissant) avant l'étape 2 |
| le levier est adopté | appliquer le même score au choix de variante à l'intérieur d'un groupe (avion, profondeur). Il remplacerait `OpexAirPlanBetter` et sa constante 1,25 (`builder_air.nut:974-981`) |

---

## 13. Résultats de l'étape 1 (2026-09-21)

Sonde passive sous `probe_portfolio=1`, 5 graines × 6 ans (`100 12345 42 7 999`), **0 échec**.
Script `sweeps/diag_c69_bottleneck_probe.py` ; résultats `results/diag_c69_bottleneck_probe_6y_5seeds.json`,
lignes brutes `results/c69_raw_6y_5seeds.jsonl`. F corrigé (§4.1), rangs figés au début de la passe.

### 13.1 K_dec mesuré (médiane par passe)

| graine | 1970 | 1971 | 1972 | 1973 | 1975 |
|---|---:|---:|---:|---:|---:|
| 100 | 0 | 39 k£ | 47 k£ | 149 k£ | 234 k£ |
| 12345 | 11 k£ | 59 k£ | 128 k£ | 181 k£ | 253 k£ |
| 42 | 9 k£ | 66 k£ | 162 k£ | 160 k£ | 223 k£ |
| 7 | 0 | 78 k£ | 160 k£ | 231 k£ | 230 k£ |
| 999 | 6 k£ | 58 k£ | 144 k£ | 283 k£ | 313 k£ |

1971 tombe dans la fourchette prévue au §7 ; à partir de 1973, K_dec est environ deux fois plus
élevé que prévu. Première divergence de classement : **1971 sur les 5 graines** (§7, prédiction 2).

### 13.2 Critères

| critère | seuil | 100 | 12345 | 42 | 7 | 999 | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| C1 écart d'années | ≤ 1 sur ≥ 4/5 | 1 | 1 | 1 | 0 | 0 | ✅ 5/5 |
| C2 exposition | ≥ 20 % | 34 % | 84 % | 73 % | 83 % | 73 % | ✅ |
| C3 construit quand même | ≤ 50 % | 21 % | 3 % | 0 % | 8 % | 0 % | ✅ |
| C4 ratio médian de P | ≥ 1,5 | 1,34 | 2,08 | 1,84 | 2,44 | 1,86 | ✅ médiane 1,86 ; 4/5 |
| C5 écart de calibration | ≤ 1,5 | 1,44 | 3,79 | 2,05 | 2,64 | 1,53 | ❌ 1/5 |

C1 : la médiane K_dec dépasse le capital médian des lignes aériennes élues en 1971-1972 ; le
registre C49 voit `cash < decision` en 1971-1973.

### 13.3 C5 échoue, mais sur des modes qui ne divergent presque jamais

- **Calibration par convoi.** Le réalisé porte sur la flotte courante, la prédiction sur la flotte
  initiale : sans normalisation, l'air sortait à 1,5–2,2 (croissance de flotte, pas erreur de
  modèle). Normalisé par convoi (`trains0`), **air 0,93–1,31**, sur 8 à 28 lignes par graine.
- **Route et rail reposent sur une seule ligne.** Route : `n_prof = 1` (les autres lignes de bus
  viennent de `task_town`, sans prédiction), ratio 1,6–1,8. Rail : 1 ligne, 0,46–1,14.
- **Les divergences sont à 97 % aériennes.** Sur 156 passes divergentes : air → air **75**,
  flotte (+1 avion) → nouvelle ligne aérienne **70**, vers le rail 6, route 2. Le levier arbitre
  donc surtout entre **ajouter un avion** et **ouvrir une ligne**, soit le risque 5 du §9.

⚠️ **Décision à prendre, non tranchée ici** : le critère C5 écrit d'avance dit « l'étape 2
attend ». Sa lettre échoue ; son objet, le biais inter-modes du profit absolu, porte sur des
modes quasi absents des divergences.

### 13.4 Passivité : aucune variante n'est neutre

Le banc est déterministe : deux lancements séparés de `master` donnent le même résultat au bit
près. Graine 42, 3 ans :

| code | `probe_portfolio` | valeur | véhicules | gares |
|---|---|---:|---:|---:|
| `master` | 0 | 2,58 M£ | 52 | 38 |
| `master` | 1 | 2,74 M£ | 52 | 40 |
| C69 étape 1 | 0 | 2,54 M£ | 53 | 38 |
| C69 étape 1 | 1 | 2,54 M£ | 47 | 32 |

(Graine 100 : 2,13 / 1,89 / 2,06 / 1,88 M£.) Même au défaut, où il ne fait que tester des
drapeaux, le code C69 déplace la partie de −1,7 % : la trajectoire est chaotique, et le moindre
opcode ajouté la décale, comme à la passe 3 de C65. Les sondes font de même.

**Conséquences.** Aucune mesure mono-graine ne départage deux variantes. C2–C4 restent valides,
puisque les deux classements sont calculés dans la même partie. L'étape 3 compare deux bras du
**même code** avec la sonde dans le même état.

### 13.5 Écarts à l'implémentation décrite

- Le terme $I$ et son registre sont supprimés (§4.1).
- `trains0` est ajouté aux lignes air, route et rail à la construction (champ inerte, lu par la
  sonde seulement).
- Les suivis C3 encore ouverts sont publiés au rapport annuel (`phase=c3_pending`) ; ils sont
  exclus du calcul de C3.

---

## 14. Étape 2 — le levier (2026-09-21)

**Préalable** : C5 a été traité par C70 (`12_calibration_par_mode.md`). Après le facteur
glissant, max/min = 1,46, avec les réserves du §8 de cette fiche sur la route et le rail.

**Implémentation** : `c69_decision_bottleneck`, défaut 0.

- `fundScore = P × 1000 / max(C, K_dec)`, avec `P` calibré si `c70_mode_calibration=1`. C'est
  le seul changement de décision.
- `C69_TRACK_BUILDS = sonde ou levier` : τ exige les dates de chantier, qui sont donc enregistrées
  sous le levier même sans sonde. Journaux sous la sonde seulement.

**P1–P8 : pas de test unitaire possible.** Il n'y a d'interpréteur Squirrel ni sur l'hôte ni dans
l'image `openttd-lab`. P1 et P2 sont vérifiés en jeu. Les autres propriétés découlent de la forme
de la formule (un `max`, aucun filtre, aucun terme par projet en opcodes) et sont relues, pas
testées.

**Smokes**, graines 42 et 100, 0 échec :

- 2 × 3 ans, trois bras : sonde seule, sonde + levier, levier seul ;
- **identité** : sonde seule contre sonde + levier, graine 42, 2 ans. Même code exécuté, donc
  mêmes opcodes. **Les 18 premières passes qui construisent sont identiques au bit près** : les
  13 de 1970 (K_dec ≤ 26 k£) et les 5 premières de 1971. La divergence apparaît en 1971, quand
  K_dec approche 58–69 k£.
- `diff` ne compare que le premier rang. Il reste à 0 jusqu'à la divergence, alors que F diffère
  déjà : le levier a d'abord réordonné des rangs inférieurs, construits après l'échec d'un
  premier rang.

**Étape 3 non lancée.**

---

## 15. Étape 3 — diagnostic 5×6 apparié, solo et duel (2026-09-21)

`sweeps/diag_c69_paired_solo_duel_5x6.py`, graines de C49 (`100 12345 42 7 999`), trois bras :
`default`, `c70` (calibration seule), `c70_c69` (calibration + levier). Aucune sonde. **30 parties,
0 échec.** Résultats : `results/diag_c69_paired_solo_duel_5x6.json`.

**Profit annuel OpexAI en 1975 :**

| comparaison | solo | duel (profit OpexAI) | duel (OpexAI / AAAHogEx) |
|---|---|---|---|
| `c70_c69` − `c70` (**C69 isolé**) | **+394 k£**, 4 V / 1 D | 2 V / 3 D | −0,001, 2 V / 3 D |
| `c70` − `default` (C70 seul) | −45 k£, 3 V / 2 D | — | +0,010, 3 V / 2 D |
| `c70_c69` − `default` | +349 k£, 4 V / 1 D | — | +0,008, 3 V / 2 D |

**Chronologie, C69 isolé** (graines où `c70_c69` dépasse `c70`, au mois de décembre) :

| | 1970 | 1971 | 1972 | 1973 | 1975 |
|---|---|---|---|---|---|
| solo | 2 V, 2 égalités | 4 | 4 | 5 | 4 |
| duel | 1 V, 3 égalités | 4 | 4 | 3 | **2** |

- **Prédiction 2 du §7 : tenue.** Les parties sont presque identiques en 1970, et l'écart naît en
  1971, l'année de la bascule.
- **En solo, le levier gagne nettement** : +18 % de profit moyen, et devant sur 4 ou 5 graines
  chaque année à partir de 1971.
- **En duel, l'avance de 1971-1972 s'érode**, de 4/5 à 2/5 en 1975. Hypothèse, non vérifiée :
  C69 préfère ouvrir de nouvelles lignes aériennes (§13.3), et c'est justement sur les villes que
  AAAHogEx dispute.

**Verdict selon le critère écrit d'avance** (« ≥ 3 graines sur 5 gagnent sur `profit_year` », en
duel) : **2/5, échec. L'étape 4 n'est pas lancée.** Un 5×6 ne conclut rien en valeur (C41.47) ;
c'est la règle de passage qui tranche.

⚠️ **Décision utilisateur requise**, entre la lettre du critère (duel) et le signal solo.

---

## 16. Pourquoi le duel s'érode — diagnostic (2026-09-21)

`sweeps/diag_c69_duel_erosion.py` rejoue en duel les bras `c70` et `c70_c69` (5 graines × 6 ans,
sans sonde) et lit chaque décembre, dans la sauvegarde, les lignes des deux compagnies.
Résultats : `results/diag_c69_duel_erosion_5x6.json`.

### 16.1 🔴 Le duel n'est pas déterministe

Le solo l'est (deux lancements de `master`, identiques au bit près, §13.4). **Le duel ne l'est
pas** : relancé avec le même code, le profit OpexAI de 1975 ne se reproduit exactement que sur
2 parties sur 10.

| graine | `c70` banc → rejeu | `c70_c69` banc → rejeu |
|---|---|---|
| 100 | 619 → 582 k£ | 575 → 578 k£ |
| 12345 | 1 153 → 1 153 k£ | 1 297 → 1 297 k£ |
| 42 | 992 → 1 037 k£ | 1 278 → 1 302 k£ |
| 7 | 1 262 → 1 262 k£ | **1 046 → 1 234 k£** |
| 999 | 1 237 → 1 263 k£ | 1 090 → 1 107 k£ |

L'écart d'un rejeu à l'autre va jusqu'à 18 %, soit l'ordre de grandeur de l'effet mesuré.
Écart moyen C69 − C70 en duel : **+4 k£** au banc, **+44 k£** au rejeu ; 2 V / 3 D les deux fois,
avec les mêmes graines gagnantes (42, 12345) et perdante (999).

### 16.2 L'hypothèse de concurrence est réfutée

| décembre, moyenne 5 graines | 1972 c70 → c69 | 1973 | 1975 |
|---|---|---|---|
| lignes OpexAI | 34,2 → 35,6 | 43,6 → 44,0 | 54,6 → 54,0 |
| dont aériennes | 21,8 → 22,2 | 27,8 → 28,8 | 35,4 → 36,6 |
| avions | 27,4 → 26,2 | 34,0 → 33,0 | 44,2 → 42,4 |
| profit par avion | **22,2 → 26,6 k£** | **23,0 → 28,3 k£** | 20,9 → 23,0 k£ |
| lignes touchant une ville d'AAAHogEx | 97 % → 96 % | 98 % → 98 % | 99 % → 99 % |
| véhicules AAAHogEx | 176 → 164 | 227 → 220 | 279 → 284 |

- **Le chevauchement ne discrimine rien** : AAAHogEx est dans presque toutes les villes. 97 à 99 %
  des lignes OpexAI en touchent une, **dans les deux bras**. C69 n'y va pas davantage.
- **Le levier fait ce que la formule prévoit** : un peu plus de lignes aériennes, un peu moins
  d'avions, et **+19 à +23 % de profit par avion** en 1972-1973.
- **Cet avantage par avion se resserre ensuite** (+10 % en 1975), pendant que la flotte reste
  légèrement plus petite.

### 16.3 Lecture

Le 2/5 du §15 n'est pas le signe d'une mauvaise interaction avec AAAHogEx. En duel, l'effet est
proche de zéro, et du même ordre que le bruit d'un rejeu à l'autre. **Un 5×6 en duel ne peut
donc pas trancher le critère du §10.** L'étape 4 (20×10, test des signes) a été conçue pour ce
cas, mais le critère écrit de l'étape 3 reste formellement non atteint.

---

## 17. Étape 4 — banc d'autorité 20×10 en duel (2026-09-21)

Campagne `c69_step4_c70c69_vs_c70_10y_20seeds`, lancée sur le PC de l'utilisateur (9 workers),
code `1df5cfb`, `dirty=0`, 20/20 paires complètes. Résultats :
`results/c69_step4_c70c69_vs_c70_10y_20seeds.json` ; journal `results/c69_step4.log` (UTF-16).

| métrique, `c70_c69` − `c70` | moyenne | médiane | V / D | lecture |
|---|---:|---:|---|---|
| **`profit_year`** (primaire) | **+87,6 k£/an** (+5,6 %) | +71,6 k£ | **12 / 8**, p = 0,50 | IC95 [−45,6 ; +220,9] k£ |
| `company_value` (garde) | −187 k£ (−2,2 %) | +33 k£ | 11 / 9 | garde −5 % tenue |
| véhicules | −7,7 | −11 | 5 / 15 | |
| note de gare médiane | −5,1 | −6 | **3 / 16** | |
| aéroports OpexAI | **+5,65** | +5,5 | **19 / 1** | |
| panneaux d'erreur aérienne `OE\|A\|771` | +103 | +99 | 19 / 1 | cause non examinée |

**Verdict : `fail_primary`.** Le test des signes donne 12/20, loin de 15/20. L'écart moyen dépasse
le seuil de +50 k£, mais son intervalle de confiance contient zéro. **C69 n'est pas adopté ;
`c69_decision_bottleneck` reste à 0.** C'est le cas B de `14_suites_c69.md` : échec, écart moyen
positif.

**Ce que le banc montre sans ambiguïté** : le levier construit **plus d'aéroports** (19/20) avec
**moins de véhicules** (15/20), et la **note de gare baisse** (16/20). C'est le risque 5 du §9 : le
régime « décision » ouvre des lignes qu'il ne remplit pas, parce qu'un renfort de flotte est plafonné
à 4 avions et qu'une ligne neuve naît à 1 avion. Le contrat 2 de l'annexe B (lots de flotte au
besoin mesuré) vise exactement ce mécanisme.

---

## 18. C69 bis — les projets de flotte exemptés de K_dec (2026-09-21)

**Hypothèse** (décision utilisateur, option 1). Un projet de flotte (`mode = "fleet"`, des avions
ajoutés à une ligne existante) ne construit rien : pour lui τ ≈ 0, et la dérivation du §3 donne
D = C/F, soit le score P/C. Le levier du §14 lui appliquait pourtant max(C, K_dec), ce qui le
pénalisait face aux lignes neuves. C'est cohérent avec 70 des 156 divergences du §13.3 (« +1
avion » remplacé par une ligne neuve) et avec le §17 (plus d'aéroports, moins de véhicules).

**Implémentation** (agy, relue) : réglage `c69_fleet_exempt`, défaut 0. Sous le levier, un projet
`fleet` garde `financeCapital` comme dénominateur. Le défaut est inchangé à une condition près,
évaluée en court-circuit.

**Diagnostic** `sweeps/diag_c69_bis_solo_5x6.py`, **solo**, 5 graines × 6 ans, 0 échec :
`results/diag_c69_bis_solo_5x6.json`.

| paire | profit annuel | valeur | véhicules |
|---|---|---|---|
| `c70_c69_bis` − `c70_c69` | +40 k£, 3 V / 2 D | −79 k£, 2 V / 3 D | **+5,4, 5 V / 0 D** |
| `c70_c69_bis` − `c70` | +358 k£, 3 V / 2 D | +1,02 M£, 3 V / 2 D | −2,0, 2 V / 3 D |
| `c70_c69` − `c70` | +319 k£, 4 V / 1 D | +1,10 M£, 4 V / 1 D | −7,4, 1 V / 4 D |

- **Le mécanisme est confirmé** : l'exemption rend à C69 ses avions (5/5), à 2 véhicules près du
  témoin `c70`.
- **Le profit ne se départage pas** : +40 k£ face à C69, 3/5, dans le bruit d'un 5×6.
- ⚠️ **Aucun critère de passage n'avait été écrit avant ce diagnostic.** Le seuil habituel des
  5×6 (≥ 3/5 sur le profit) est atteint face à C69 comme face à `c70`, mais de justesse.
- Les chiffres de `c70_c69` diffèrent de ceux du §15 (graine 100 : 1,614 → 1,646 M£) : la
  condition ajoutée décale les opcodes, comme au §13.4.

**Suite possible** : le 20×10 d'autorité en duel, `c70_c69_bis` contre `c70`, sur le PC de
l'utilisateur (commande dans `13_banc_c69_20x10_pc.md` §5).

---

## 19. C69 bis — banc d'autorité 20×10 en duel (2026-09-21)

Campagne `c69bis_c70c69bis_vs_c70_10y_20seeds` (PC de l'utilisateur), 20/20 paires complètes :
`results/c69bis_c70c69bis_vs_c70_10y_20seeds.json`, journal `results/c69bis_step4.log`.

| métrique, `c70_c69_bis` − `c70` | moyenne | médiane | V / D | rappel C69 (§17) |
|---|---:|---:|---|---|
| **`profit_year`** | **+111,0 k£/an** (+7,2 %) | +76,4 k£ | **12 / 8** | +87,6 k£, 12 / 8 |
| `company_value` | −112 k£ (−1,35 %) | −320 k£ | 6 / 14 | −2,2 %, 11 / 9 |
| véhicules | −8,65 | −9,5 | 4 / 16 | −7,7, 5 / 15 |
| note de gare médiane | −5,5 | −3 | 7 / 13 | −5,1, 3 / 16 |
| aéroports OpexAI | +5,05 | | 16 / 2 | +5,65, 19 / 1 |

**Verdict : `fail_primary`** (12/20). C69 bis n'est pas adopté ; `c69_fleet_exempt` reste à 0.

- **L'exemption de flotte ne rend pas les avions en duel** : −8,65 véhicules (4/16), alors que le
  5×6 solo du §18 en rendait +5,4 sur 5/5. Le levier ouvre toujours ~5 aéroports de plus pour
  moins de véhicules.
- **Deux bancs indépendants, même lecture** : écart moyen positif (+88 et +111 k£/an, au-dessus du
  seuil de +50 k£), mais 12/20 les deux fois. Le gain moyen n'est pas porté par une majorité de
  graines.

**C69 : non adopté, en pause** (décision utilisateur du 2026-09-21, qui remplace une première
rédaction « fermé »). Les deux formes du levier échouent au critère d'autorité, mais c'est la
meilleure tentative de changement de régime ROI → profit à ce jour (C35.4 4/16, C49 9/11, frontière
λ 0/5) : gain moyen positif sur deux bancs indépendants, non porté par une majorité de graines
(cumul 24 V / 16 D, p ≈ 0,27). Réglages à 0, code inerte conservé.

**Reprise prévue :**

1. mesurer pourquoi la flotte ne suit pas les lignes ouvertes : refus `W` (attente au sol) contre
   plafond de cadence (`room`) ; les deux causes testées (plafond de lot, exemption de flotte)
   sont écartées ;
2. si C72 est adopté, rebancer C69 bis par-dessus C72, contre C72 seul.

---

## 20. Graines extrêmes de C69, C69 bis et C72 (2026-09-21)

Les bancs C69 et C69 bis ont la même référence (`c70`), les deux bancs C72 aussi (`default`) :
chaque paire contient **deux parties indépendantes de la même politique**. Leur écart mesure le
bruit du duel graine par graine.

### 20.1 Le bruit

| même politique jouée deux fois | parties identiques | écart médian | écart max | écart-type |
|---|---|---|---|---|
| `c70` (C69 et C69 bis) | 0 / 20 | 157 k£ (10,3 %) | 354 k£ (27,6 %) | 189 k£ |
| `default` (deux bancs C72) | 2 / 20 | 117 k£ (7,5 %) | 466 k£ (42,9 %) | 203 k£ |

Écart-type des écarts variante − référence : C69 296 k£, C69 bis 314 k£, C72 ROI 257 k£, C72 C69
330 k£. Pour C72, c'est à peine plus que le bruit ; pour C69, il y a une part propre.

### 20.2 C69 : un effet réel, qui dépend de la carte

Écarts par graine de C69 et de C69 bis : **corrélation +0,53** sur 20 graines (C72 contre C69 :
±0,1). Les mêmes cartes gagnent et perdent :

| graine | C69 | C69 bis | bruit `c70` | Δ avions | Δ aéroports | Δ gares de bus |
|---|---:|---:|---:|---|---|---|
| 424242 | **+728** | **+943** | −221 | −20 / −13 | +11 / +9 | +20 / +7 |
| 73 | +403 | +378 | +41 | −13 / −16 | +6 / +8 | +14 / +8 |
| 314 | +278 | +514 | −236 | −5 / −7 | +3 / +6 | +8 / +3 |
| 8675309 | +306 | +173 | −29 | −5 / −11 | +6 / +7 | +6 / +9 |
| 100 | **−224** | **−181** | +12 | +2 / +1 | +2 / −1 | **−13 / −8** |
| 65537 | −347 | −37 | −189 | +4 / +8 | +4 / 0 | −6 / −1 |
| 4096 | −278 | −418 | **+354** | −19 / −14 | +9 / +7 | +8 / +2 |
| 999 | −109 | −276 | −245 | −11 / −6 | +4 / 0 | 0 / −10 |

(k£/an, puis deltas C69 / C69 bis en fin de partie.)

- 🔴 **« Plus d'aéroports, moins d'avions » n'est PAS le mécanisme de la perte.** Les plus grands
  gagnants le font davantage que les perdants : graine 424242, −20 avions et +11 aéroports pour
  +728 k£. La reprise n° 1 du §19 (chercher pourquoi la flotte ne suit pas) visait donc un faux
  coupable.
- **Ce qui sépare les deux groupes, c'est la route.** Les gagnantes gagnent des gares de bus (+3 à
  +20) ; les perdantes au bruit faible (100, 65537) en perdent (−13, −6) avec leurs bus (−15, −10).
  Corrélation constatée sur 8 graines, cause non établie.
- La graine 4096 perd dans les deux bancs, mais son bruit (354 k£) est aussi grand que sa perte.

### 20.3 C72 : dans le bruit, sauf deux graines

- Écarts du même ordre que le bruit ; les deux bras C72 se corrèlent à +0,37 (deux politiques
  différentes, donc pas un test de reproductibilité).
- **512 perd dans les deux bras** (−754 et −500 k£, bruit −192) sans changement visible de flotte
  ou de gares ; **8191 gagne dans les deux** (+446 et +311 k£) avec +8 à +15 avions et −13 à −17
  bus.

### 20.4 Face à AAAHogEx — l'arbitre du projet

Rapport `profit_year` OpexAI / AAAHogEx dans la même partie, moyenne sur 20 graines :

| banc | référence | variante | Δ | V / D | Δ profit AAAHogEx |
|---|---:|---:|---:|---|---:|
| C69 | 16,5 % | 16,8 % | +0,3 pt | 10 / 10 | +210 k£ |
| C69 bis | 15,7 % | 17,2 % | **+1,5 pt** | 12 / 8 (p = 0,50) | −323 k£ |
| C72 ROI | 15,8 % | 15,7 % | −0,2 pt | 10 / 10 | +186 k£ |
| C72 C69 | 16,2 % | 15,8 % | −0,3 pt | 8 / 12 | +224 k£ |

**Bruit de ce rapport** (même politique jouée deux fois) : écart-type **2,7 à 3,5 pt**, écart médian
1,5 à 1,9 pt. Tous les Δ sont dans ce bruit. En valeur d'entreprise (≈ 23 % d'AAAHogEx), même
lecture : de −1,7 à +1,6 pt.

- Le gain de profit de C69 disparaît presque face à AAAHogEx : dans ce banc, AAAHogEx gagne aussi
  +210 k£ en moyenne. Les variations d'AAAHogEx d'une partie à l'autre ne sont pas corrélées à
  celles d'OpexAI (|r| ≤ 0,19) : c'est du bruit de duel, pas une réaction.
- 🔑 **Ordre de grandeur.** OpexAI fait **~16 % du profit d'AAAHogEx** et ~23 % de sa valeur, avec
  environ 98 véhicules contre 365. Les leviers de classement testés aujourd'hui déplacent ce
  rapport de ±1,5 point ; il en manque ~84. Ce ne sont pas eux qui combleront l'écart, qui est
  un écart de **volume** (`ai/OpexAI/CLAUDE.md` : rendement par véhicule à 93 % d'AAAHogEx).

### 20.5 Suite proposée

Rejouer en duel, avec la télémétrie de lignes du harnais C66 (`--line-telemetry`), la graine
gagnante 424242 et la perdante 100 (bruit faible), bras `c70` contre `c70_c69_bis`, pour voir
quelles lignes, bus et avions changent. Le duel n'étant pas déterministe, deux répétitions.
