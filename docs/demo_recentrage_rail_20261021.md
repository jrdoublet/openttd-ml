# Démonstration hors ligne : recaler RAIL à moyenne 1 sans géométrie

21 octobre 2026. Branche `review/roi-calibration-predictors-20261021`.
Script reproductible : `sweeps/demo_recentrage_rail_20261021.py`.
Sortie locale JSON : `results/calibration_pc_20261021/results/demo_recentrage_rail_20261021.json`.
Sources : `calib_solo_40x10_pc_20261021_engine` et
`calib_duel_40x10_pc_20261021_engine`, 40 parties distinctes de dix ans
chacune, avec **les mêmes 40 graines SOLO et DUEL**. Les cinq plis
excluent du SOLO d'entraînement les huit graines DUEL évaluées dans le pli.
Aucun code `ai/OpexAI` modifié et aucun nouveau banc OpenTTD.

## Résultat : choisir un pivot linéaire hors ligne

Le meilleur compromis coût/opcodes sur la carte observée `256×256` est
une correction affine **du score RAIL uniquement** :

```text
F_rail(d) = 1 + alpha * (D0 - d)
score_rail_shadow = rank_score_rail_existant * F_rail(d)
F_air = F_flotte_air = F_road = 1
```

Les **954 lignes RAIL matures SOLO** avec un coût physique donnent :

```text
K_physique_rail(d) = 1.051980876882 + 0.003065879861 * d
D0 = 132.749776809  (moyenne de la distance, pondérée par les rank_score
                       positifs des projets RAIL au top-5 SOLO)
alpha = 0.002101391934 par tuile
F(d) = 1.278950... - 0.002101391934*d
```

`alpha` est la dérivée locale relative de l'inverse du coût au pivot,
`b/(a+b*D0)`. Les seules opérations à chaque classement RAIL seraient,
après pré-calcul des deux constantes, **une multiplication de distance,
une soustraction et une multiplication du score**. La distance est déjà
présente dans le candidat. Aucun appel au terrain, A*, recherche de sites,
division, table par cargo, ni boucle de normalisation en partie.
Le coût Squirrel exact en opcodes reste à mesurer : ces trois opérations
arithmétiques ne sont **pas** une mesure du compteur d'opcodes. Une garde
de domaine serait nécessaire si les distances autorisées atteignaient
plus de ~609 tuiles et rendaient `F` négatif.

Les exemples avec les constantes apprises sur les 40 SOLO sont :

| Distance RAIL | Facteur de score |
|---:|---:|
| 30 | 1,2159 |
| 55 | 1,1634 |
| 100 | 1,0688 |
| 150 | 0,9638 |
| 200 | 0,8587 |
| 250 | 0,7536 |

La moyenne **pondérée par les scores RAIL au top-5 SOLO vaut exactement
1,000000** par construction. La normalisation est préparée **hors ligne**,
et le jeu n'en calcule aucune. Une moyenne exactement égale à 1 sur chaque
partie future est impossible avec ces constantes immuables si la répartition
de distances change. Sur les cinq plis SOLO→DUEL disjoints :

| Quantité | Pivot affine | Inverse du coût linéaire | 4 sous-bandes |
|---|---:|---:|---:|
| Centre pondéré, SOLO entraînement | 1,000000 | 1,000000 après normalisation | 1,000000 après normalisation |
| Moyenne pondérée RAIL, DUEL hors pli | **0,994605** | 0,993675 | 0,997912 |
| Intervalle des facteurs RAIL, DUEL | 0,7513–1,2675 | 0,7935–1,2614 | 0,9245–1,1050 |
| Facteur moyen AIR et flotte, DUEL | **1,000000** | 1,000000 | 1,000000 |
| Facteur moyen ROAD, DUEL | **1,000000** | 1,000000 | 1,000000 |

Les pivots entraînés en cinq plis sont entre **131,15 et 134,73 tuiles**,
les pentes relatives entre **0,002067 et 0,002128**. La formule
complète entraînée sur SOLO, indiquée plus haut, est destinée à illustrer
le code éventuel ; l'évaluation chiffrée sur DUEL utilise **des constantes
réapprises sans ses graines de test**. Le premier résultat fixe la moyenne
sur l'apprentissage, et le second chiffre le décalage effectivement mesuré
sur un autre environnement de jeu.

## Coût physique : bénéfice indépendant du recentrage du score

Pour **958 constructions RAIL matures DUEL**, le coût physique vient de
`RAIL_BUILD.cost`, apparié à `PROJECT_CHOSEN.cost`. Une observation par
ligne, `age ≥ 2`. Le même ajustement linéaire (a+b d) s'applique à un
**devis physique**, en gardant sa moyenne de capital supérieure à 1 :

| Prévision du coût physique | MAE DUEL (£) | Variantes |
|---|---:|---|
| Devis du jeu, sans correction | 26 948 | Référence brute |
| Devis × rapport médian global SOLO | 12 786 | Niveau global seulement |
| Devis × 4 sous-bandes de distance | 11 008 | Rétrécissement 20 observations |
| **Devis × (1,051981 + 0,00306588 × d)** | **10 342** | Linéaire, le plus précis |

Les cinq plis apprennent le coût physique uniquement sur 32 graines SOLO
et mesurent l'erreur sur les huit graines DUEL restantes. Dans l'étude
précédente, la formule linéaire gagne **2 408 £ de MAE par graine** face
au facteur global, IC95 bootstrap **[1 999 ; 2 795] £**, 39/40 graines
favorables. L'approximation affine du **score** conserve ce même estimateur
linéaire pour le **coût physique** ; ce sont deux usages distincts :

- `K_physique(d)` est généralement **supérieur à 1** et corrige le montant
  estimé pour construire ; son emploi avant financement ou `K_dec`
  modifierait la liste finançable et éventuellement le dénominateur de
  classement. Il n'est donc pas intermodalement neutre.
- `F_rail(d)` réalloue les préférences entre distances RAIL, sans changer
  les devis, la trésorerie disponible, le plafond de coût, le profit brut
  ni C70. Sa moyenne en apprentissage est **1** et AIR/ROAD restent à 1.

Le champ de financement journalisé confirme la distinction : parmi les
**13 695** entrées RAIL du top-5 DUEL, **13 632** ont
`finance_capital == cost` à 0,01 £ près, et **13 663** auraient un coût
physique **prédit** supérieur à `finance_capital`. Ce constat n'indique
pas combien auraient été rejetées : il manque le budget au moment du
choix et le marqueur de coût déjà réel pour chaque projet. Dans le code
**courant**, `RAIL_FINANCE_BIAS_PCT` est fixé à **100**, donc le commentaire
historique de `projects_finance.nut` qui parle de ×1,7 ne décrit plus le
comportement présent. Les devis RAIL déjà physiques ne doivent jamais
être corrigés une deuxième fois.

## Score et classements, sur les snapshots réellement enregistrés

Le journal `PORTFOLIO_RANK` contient `rank_score` (après bonus AIR),
`finance_capital`, mode, distance, profit et coût pour les cinq projets
visibles. Il contient 4 848 snapshots DUEL, dont 1 919 mixtes. La masse
de score est la **somme des `rank_score` positifs**, chaque occurrence
de snapshot comptant, et n'est pas une masse de profits ni de projets
construits distincts.

| Famille au top-5 | Occurrences | Score initial total | Après pivot affine | Moyenne pondérée |
|---|---:|---:|---:|---:|
| RAIL | 13 695 | 4 031 381 | 4 009 632 | **0,994605** |
| AIR + flotte AIR | 6 831 | 1 079 460 | 1 079 460 | **1,000000** |
| ROAD | 377 | 42 170 | 42 170 | **1,000000** |

Impact du pivot affine par distance, **pondéré par le score** des entrées
RAIL observées sur les cinq plis DUEL :

| Distance | Entrées RAIL | Facteur moyen |
|---|---:|---:|
| jusqu'à 55 | 1 011 | 1,1847 |
| 56–103 | 3 399 | 1,1054 |
| 104–151 | 4 578 | 1,0056 |
| 152–200 | 4 060 | 0,9117 |
| au-delà de 200 | 647 | 0,8126 |

Les anciennes bornes d'époque sont réutilisables sans géométrie ; sur
ces 80 parties elles valent `roadMin=roadMax=railMin=7`, `railAir=railMax
=airMin=200`, `roadGen=200`, `airMax=512`. Les quartiles arithmétiques
RAIL 55/103/151 peuvent faire une table, mais le pivot affine évite
ces comparaisons et prédit mieux le coût. La distance du candidat RAIL
est déjà journalisée ; il ne faut pas lui appliquer la conversion
AIR_BUILD distance de vol ↔ Manhattan des villes.

Trois démonstrations de réordonnancement sont recalculées sur les **mêmes
snapshots** et le `rank_score` classant, avec entraînement excluant chaque
graine DUEL test :

| Mesure (occurrences de snapshot, pas constructions) | Pivot affine | Inverse linéaire borné | 4 bandes |
|---|---:|---:|---:|
| Le maximum numérique du top-5 change, toutes compositions | **639** | 606 | 422 |
| Le maximum change, **1 919** snapshots multimodaux uniquement | **239** | 220 | 130 |
| Le `rank=0` historique est non-AIR, et son rival classé visible le dépasserait | **628** | 596 | 413 |
| Même mesure, snapshots multimodaux uniquement | **228** | 210 | 121 |
| Inversions de paires non-AIR, classe C77=0 connue | 2 721 | 2 709 | 2 037 |

Cette distinction des compositions explique pourquoi le **221** du
rapport précédent (coefficient linéaire avec normalisation directement
sur DUEL, snapshots multimodaux uniquement) est proche du **220** en
validation croisée et différent des **606** de toutes compositions.
Pour le pivot affine, parmi les 639 maxima numériques modifiés, 611 sont
RAIL→RAIL ; seuls **28** changent entre familles (14 AIR→RAIL,
14 RAIL→AIR ; la famille AIR inclut des projets de flotte).

Le comparateur du jeu trie d'abord sur la **classe défensive C77**, puis
sur le score, puis sur le revenu. Les classes AIR ne sont pas indiquées
dans le top-5 : les changements de maximum purement numérique sont un
**proxy**, pas un décompte de choix effectifs. En revanche, quand le
premier projet enregistré est RAIL, ROAD ou flotte, sa classe C77 est 0 ;
les projets qui le suivent sont aussi de classe 0, ce qui permet
d'identifier des dépassements **entre entrées visibles** sans ignorer C77.
Cela concerne 4 604 snapshots et produit les 628 dépassements visibles
indiqués, sous l'hypothèse de candidats et de financement figés.
La sonde révèle 11 snapshots où le premier projet historique n'est pas
le maximum numérique, dont trois premiers AIR dépassés numériquement
par du RAIL : il serait incorrect de forcer un AIR défensif à perdre sa
priorité à cause de la correction du score.

Exemple contrôlable, graine DUEL **100323, 4 mai 1971** : le premier
RAIL de 171 tuiles a `rank_score=757,657`, un second RAIL de 53 tuiles
`rank_score=728,811`. Après pivot, les scores deviennent respectivement
**695,373 et 851,900**. L'inversion est arithmétique dans les cinq
projets visibles ; elle ne dit pas que ce second projet serait effectivement
construit, ni avec quel profit. Les snapshots sont corrélés dans une
même partie ; 39/40 graines exposent au moins un dépassement visible.

## Chemins d'intégration éventuels et conséquences

Le score réellement utilisé est calculé dans
`projects_selection.nut::OpexProjectSelectAffordable`, avec :

```text
fundScore = OpexProjectScore(OpexProjectFundProfit(project),
                 max(K_dec, scoreDecisionFinanceCapital))
```

`OpexProjectFundProfit` contient C70 ou ses exemptions ; un renfort de
flotte peut avoir sa propre règle C121. `OpexProjectInsertDefensive` gère
les classes C77, la priorité `earlySlotBonusPct` AIR et le départage de
revenu. Deux affectations de `fundScore` existent dans la routine de
sélection, aux alentours des lignes 777 et 830. Une intervention
score-only hypothétique y appliquerait, pour RAIL et une distance déjà
connue, `fundScore *= (A-B*distance)` **avant** l'insertion dans la liste.
Cela évite tout rescannage, conserve le calcul de `K_dec`, la finance
et la priorité AIR, et suppose un coût de trois opérations arithmétiques
RAIL plus le branchement modal déjà en place. Le résultat de ce changement
actif n'est pas mesuré.

Une correction du **capital physique en amont** devrait être logée dans
le devis du projet RAIL **avant** `OpexProjectFinanceCapital` et
`OpexProjectSelectAffordable`, avec un drapeau pour ne pas recorriger
un coût de chemin déjà tracé et mesuré (`capitalIsActual`). Elle ferait
évoluer l'éligibilité (`financeCapital > capitalBudget`), le dénominateur
`max(K_dec, financeCapital)`, le nombre et l'ordre des projets admissibles
et possiblement l'amortissement et le profit projeté. `K_dec` et le budget
exact par candidat ne sont pas dans `PORTFOLIO_RANK` ; le top-5 est
postérieur aux filtres. **Aucune simulation fidèle du choix avec devis
corrigé avant `K_dec` n'est possible à partir de ces seuls logs.**
En outre, `K_dec` peut rendre une variation de coût sans effet sur le
score tant qu'il reste le dénominateur dominant. Une réévaluation globale
du coût sans réévaluer le profit, les prêts et les projets actualisés
serait incohérente.

Verdict technique de cette démonstration : le **pivot affine centré sur
SOLO**, sans appels API, est suffisant pour reproduire le signe et l'ordre
de grandeur du déplacement des scores RAIL sur DUEL. La formule linéaire
**non centrée** reste la meilleure prédiction observée du coût physique
RAIL. Ni l'une ni l'autre n'a été activée ; le gain économique, les effets
de budget et les opcodes réels restent inconnus. Toute expérimentation
active requiert des mesures et des graines indépendantes de ce panel.

Reproduire sans simulation :

```powershell
python -X utf8 sweeps/demo_recentrage_rail_20261021.py --selftest
python -X utf8 sweeps/demo_recentrage_rail_20261021.py --solo results/calibration_pc_20261021/results/calib_solo_40x10_pc_20261021_engine --duel results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine --out results/calibration_pc_20261021/results/demo_recentrage_rail_20261021.json
```
