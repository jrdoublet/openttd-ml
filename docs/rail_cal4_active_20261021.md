# RAIL-CAL-1 — prompt 4 exécuté, variante active `rail_cal=1` (21/10/2026)

**Décision de clôture : essai technique et 3×3 terminés ; variante non qualifiée, réglage par défaut `0` conservé.**
Pas de porte A **40×3** ni de pénalisation AIR. Un diagnostic 40×10 supplémentaire a été terminé
le 21/10 et a également échoué aux critères `gain_short` de ce banc (voir ci-dessous).
Le modèle de profit cargo×distance du prompt 2 ne passe pas
la validation hors échantillon du prompt 5, malgré un premier résultat économique favorable sur 3 graines.
Preuves structurées : `evidence/review/rail_cal4_active_20261021/results_summary.json`.

## Implémentation

- `info.nut` : `rail_cal` entier 0/1, valeur `0` aux quatre profils et `default_value=0`.
- `globals_pre.nut`, `settings.nut` : globale `RAIL_CAL`, lue une seule fois.
- `projects_selection.nut` : les **deux** affectations `fundScore` passent par
  `OpexRailCalFundScore` ; seul un projet `mode="rail"` **avant** constat du coût physique
  (`capitalIsActual` sur le projet ou son payload) reçoit les facteurs indépendants :
  coût `1.062686150395 + 0.003008780074 × d` et profit `K_profit(cargo, quartile)`
  dont la table Squirrel reprend `docs/calibration_rail_jointe_20261021.md` (4 décimales).
  La table est indexée par **label cargo** plutôt que par ID NoAI.
- Convention `K_dec` : la note du projet est
  `1000 × (OpexProjectFundProfit × K_profit) / max(K_dec, OpexProjectFinanceCapital × K_cost)`.
  Si `K_dec` domine, le facteur de coût n'agit pas sur le dénominateur ; le profit reste corrigé.
  Lorsque le capital estimé domine, le ratio des scores est précisément
  `K_profit / K_cost`. Si le devis A* est physique, le calcul reste **identique au défaut**.
  L'exemption historique des projets `fleet` reste inchangée.
- **Strictement inchangés** : capital et profit de référence du candidat, factures réelles,
  financabilité, `OpexProjectFinanceCapital`, `K_dec`, C70, AIR, flotte AIR, ROAD, plancher de profit.
  Aucun appel de géométrie, aucune API supplémentaire pour calculer le revenu.
  La lecture du label cargo est la seule résolution dynamique du facteur par candidat.

## Contrôles

`python -X utf8 -m unittest sweeps.test_rail_cal -v` : 4/4 ;
`python -X utf8 -m unittest sweeps.test_rail_profit_components_20261021 -q` : 4/4.
`git diff --check` : OK. Le lancement complet `python -m pytest sweeps -q` n'a pas pu
être exécuté dans les environnements PC et Docker utilisés (`No module named pytest`).
Les deux campagnes réelles OpenTTD 15.3 ont produit **zéro erreur Squirrel**.

## Bancs sur la même source figée

Bundle `e40cb8af50b4ab9f782c69c0c0855c052c351ff4b6af62d2bb8f15ed5682a743`.
Cartes 256², départ 1970, référence `OpexAI[decision_log=1]`, variante
`OpexAI[rail_cal=1,decision_log=1]`, AAAHogEx concurrent, un Docker à la fois,
2 puis 6 workers (limites 10 CPU / 8 Go). Toutes les parties complètes.

| Banc | Paires | Δ profit_year variante − ref | W/L/T | Valeur ratio des moyennes | Verdict |
|---|---:|---:|---:|---:|---|
| `rail_cal4_smoke_1x1_20261021` | 1/1 | +15 558 £/an | 1/0/0 | +2,64 % | `fail_primary` |
| `rail_cal4_probe_3x3_20261021` | 3/3 | **+140 645 £/an** | 3/0/0 | **+3,56 %** | **`fail_primary`** |

Le 3×3 a un IC95 bootstrap de la moyenne [+82 900 ; +196 533] £/an,
mais le test de Wilcoxon donne `p=0,25` (trois graines insuffisantes pour le seuil `p<0,05`).
Le gain moyen dépasse le plancher de +4 % de profit de référence ; la décision reste
**non qualifiante** car la significativité obligatoire échoue. Un bootstrap de trois
observations ne constitue pas une validation de robustesse.

| Graine 3×3 | Référence profit/an | Variante profit/an | Δ £/an | Δ valeur £ |
|---|---:|---:|---:|---:|
| 42 | 2 153 604 | 2 350 137 | +196 533 | +301 957 |
| 7 | 3 022 885 | 3 105 785 | +82 900 | −268 221 |
| 100 | 1 200 266 | 1 342 768 | +142 502 | +384 979 |

## Exposition réelle RAIL (3×3)

| Mesure | Référence | Variante `rail_cal=1` |
|---|---:|---:|
| Lignes RAIL construites | 40 | 43 |
| Distance médiane (tuiles) | 116,5 | 116 |
| COAL | 14 | 17 |
| GRAI | 3 | 2 |
| IORE | 6 | 5 |
| LVST | 2 | 1 |
| OIL_ | 3 | 5 |
| PASS | 2 | 2 |
| STEL | 0 | 1 |
| WOOD | 10 | 10 |

Par graine (référence → variante) : 42, 16→10 lignes ; 7, 14→18 ; 100, 10→15.
Le smoke 1×1 ne construit **aucune ligne RAIL** dans les deux bras, malgré un
écart de profit de +15 558 £/an : les différences de score et d'ordonnancement,
et/ou de trajectoire du monde, peuvent avoir un effet indirect ; ne pas
attribuer mécaniquement cet écart à de nouvelles voies.

## Statistique hors ligne et décision

La mesure passive préalable prédisait un score RAIL pondéré **−17,21 %**.
Le diagnostic RAIL-PROFIT-1 (`docs/diag_rail_profit_components_20261021.md`)
montre, sur **1 032 lignes DUEL matures** et cinq plis disjoints, une **MAE
du profit de 11 495 £/an brut contre 12 881 £/an avec facteur cargo×distance** :
le profit calibré du présent prompt n'est **pas qualifié comme estimateur**.
La comptabilité réalisée ne contient pas l'amortissement prévu, empêchant
une attribution naïve du biais à la recette.

## Porte A — vérification de la demande du lot du 21/10 au soir

Le [prompt 3](prompts/lot_21102026_soir.md) indique une **porte A 40×3 déjà
terminée** ; aucun résultat local de `rail_cal=1` avec 40 graines × 3 ans
n'a pu être identifié. Les chiffres du 3×3 exposés ci-dessus sont ceux d'un
diagnostic, pas une porte A : son `p=0,25` ne satisfait pas le critère V102.
Il n'existe donc **aucun verdict vérifié de porte A 40×3** à recopier.

En revanche, une campagne **distincte**
`rail_cal4_40x10_multimodal_pc_20261021` a terminé ses 40 paires de dix ans
sur le bundle `e40cb8af...`, avec `gain_short`, année terminale 1979 et
`required_years=10`. Résultat local reproductible :
`results/rail_cal4_40x10_multimodal_pc_20261021.json`.

| Critère du diagnostic **40×10** | Mesure |
|---|---:|
| Verdict | **`fail_primary`** |
| Paires complètes | 40/40 |
| Δ `profit_year` variante − référence, moyenne | **+70 538 £/an** |
| Médiane | +34 616 £/an |
| Victoires / défaites / égalités | 22 / 18 / 0 |
| Wilcoxon exact bilatéral | p = 0,24793 |
| IC95 bootstrap moyenne (20 000 rééchantillonnages) | [−40 682 ; +183 854] £/an |
| Seuil 4 % du profit référence | **+173 126 £/an** |
| `company_value`, ratio des moyennes | **+1,57 %** (garde −5 % respectée) |

Exposition des constructions `RAIL_BUILD` sur les 80 journaux complets
(distance en tuiles, cargo de chaque nouvelle ligne) :

| Mesure | Référence `rail_cal=0` | Variante `rail_cal=1` |
|---|---:|---:|
| Lignes construites | **1 086** | **1 105** |
| Distance médiane | 118 | 127 |
| COAL | 225 | 229 |
| GRAI | 199 | 179 |
| IORE | 166 | 177 |
| WOOD | 161 | 165 |
| OIL_ | 119 | 123 |
| PASS | 105 | 91 |
| LVST | 70 | 93 |
| GOOD | 26 | 37 |
| STEL | 9 | 7 |
| VALU | 6 | 4 |

Le signal de gain à dix ans (+70,5 k£/an) reste incertain et inférieur au
plancher du banc (173,1 k£/an). Ce **40×10 n'est pas une porte A 40×3** ;
il n'autorise ni porte B automatique ni adoption. Le réglage reste à 0,
indépendamment de la MAE de l'estimateur de profit.
L'exploration de facteurs rétrécis dans `docs/rail_cal_profit_safe_20261021.md`
réduit légèrement la MAE de certains candidats, **mais a été sélectionnée
après inspection du DUEL** : pas de validation indépendante, pas de motif
pour remplacer cette expérience ni activer un nouveau défaut.

**Sujet clos au niveau expérimental :** prompt 4 livré et mesuré ; conserver
`rail_cal=0`, ne pas appliquer AIR×0,8, ne pas déclencher de porte A sur
le présent estimateur. Une nouvelle politique demanderait un estimateur de
profit indépendant qualifié sur d'autres graines, et constituerait une autre tâche.
