# V307 1.8 — Sites de gare dispersés par octant

21 octobre 2026. Changement expérimental **désactivé par défaut** ; aucune porte A ni adoption.

## Hypothèse et périmètre

L'autopsie `docs/v307_extremites_20261021.md` (§ décisions) montre que la spirale
`OpexStationPlans` privilégie les douze premiers plans valides, généralement proches
et rassemblés. Un terrain plat dans un autre octant ne prouve pas qu'un quai y
capte assez de cargo ou qu'un tracé ferroviaire y est possible.

Le réglage `v307_sites` reste **0** aux quatre niveaux. À 0, la recherche de plans
reste la spirale historique ; sous `decision_log` uniquement, un relevé de coût
`V307S_PLANS` est ajouté. À 1 :

- fret : ensemble natif `AITileList_IndustryProducing` ou
  `AITileList_IndustryAccepting`, filtré par évaluateurs natifs de pente et de
  constructibilité, puis classé selon la distance au centre ; au maximum douze
  positions de départ examinées par octant, trois quais retenus par octant,
  douze plans au total, servis en tours des huit octants ;
- villes : anneaux de spirale prolongés avec trois plans retenus au maximum par
  octant ; le budget de travail de la variante est borné à 73 000 opcodes mesurés ;
- dans les deux cas, mêmes filtres locaux de longueur, quai, entrée, cargo,
  empiètement rival, validation réelle par `AITestMode(BuildRailStation)`, et
  exigence de quai parallèle lorsque demandée ;
- journal de contrôle `V307S_PLANS` : type, côté, centre, nombre d'octants,
  plans et opcodes (horloge reposant sur `AIController.GetOpsTillSuspend`).

Le tri natif n'est pas une preuve d'un coût inférieur à la spirale et n'élargit
pas l'emprise au carré complet. Le résultat économique ne peut pas être déduit
du seul nombre d'octants.

## Validation du code

`sweeps/test_v307_sites.py` vérifie le défaut 0 à quatre niveaux, la lecture
unique, la distribution octants/quota, l'usage du sous-ensemble natif et les
cas de logs sans sonde. L'inventaire exhaustif des `.Valuate` est mis à jour
dans `sweeps/fixtures/v262_valuate_inventory.json` (test V262).

La suite complète `python -m pytest sweeps -q` n'est pas disponible dans les
interpréteurs Python du PC ou de l'image Docker de simulation : module `pytest`
absent. Le contrôle `unittest` ciblé et la vérification `git diff --check`
ont été exécutés séparément. Ce manque n'est pas un succès implicite de pytest.

## Exposition et critères pré-enregistrés

- Smoke `v307s_smoke_1x1_20261021` : 1 graine (42) × 1 an, deux bras
  `OpexAI[decision_log=1]` et `OpexAI[decision_log=1,v307_sites=1]`.
  Bundle `30bac441d8ecb44d6814db79e7b8f71e1596bd8ea4ab136e66edaffe4e95929e` ;
  **2/2 parties terminées, zéro erreur script**, verdict `diagnostic_only`.
  Le premier exercice ne comporte aucune tentative RAIL : les seuls appels aux
  sites portent sur des préparations. La sonde observe, respectivement référence
  puis variante : côté A 4→6 octants, médiane d'opcodes 8 134→13 514 ; côté B
  4→6 octants, 5 497→11 169. C'est **au-dessus de ×1,5** sur le petit smoke,
  non concluant sur les tentatives de construction.
- Exposition prescrite : `v307s_expo_3x10_20261021`, mêmes bras et options,
  graines 42, 7, 100, dix ans, 3 workers, `--script-debug` et télémetrie
  par ligne (`--line-telemetry`) pour éviter d'assimiler le profit prédit au
  profit effectivement constaté. Elle seule permettra de comparer les motifs
  `ABND`, `SITEB`, `SITEA`, `SITEAB`, les constructions et la distribution du
  coût par appel.

Critère du prompt avant toute porte A : réduction d'au moins **30 %** du total
`ABND + SITEB` **et** coût par appel au plus **×1,5** de la spirale historique.
Ces critères ne sont pas remplacés par le profit brut d'un banc exploratoire.

## Résultats du banc 3×10

Campagne complète `results/v307s_expo_3x10_20261021.json`, manifeste
`8569caf6c1066067a46c455861e74ddd669ba97ba5c007f324d9a071ee8efdb4`,
**3/3 paires complètes, six journaux, zéro erreur script** ; même bundle
`30bac441d8ecb44d6814db79e7b8f71e1596bd8ea4ab136e66edaffe4e95929e`
que le smoke. Le banc exploratoire est `diagnostic_only`, et non une porte A.

| Mesure | Référence 0 | V307S=1 |
|---|---:|---:|
| `RAIL_ATTEMPT` | 126 | 189 |
| `ABND` | 6 | 2 |
| `SITEA` | 5 | 29 |
| `SITEB` | 3 | 27 |
| `SITEAB` | 27 | 62 |
| **`ABND + SITEB`** | **9** | **29** |
| `RAIL_BUILD` | 78 | 69 |
| Octants médians côté A | 4 | 1 |
| Octants médians côté B | 3 | 0 |
| Ops médianes côté A | 12 390 | 9 083 |
| Ops p90 côté A | 2 246 642 | 17 335 |
| Ops médianes côté B | 14 187 | 2 472 |
| Ops p90 côté B | 2 593 663 | 13 287 |

Les faibles opcodes de la variante sont **trompeurs** : des appels échouent vite
avec `plans=0`, d'où les médianes d'octants de 0 ou 1. Il ne s'agit pas d'une
accélération à service identique. Les très grands p90 de la référence indiquent
des franchissements de ticks dans l'horloge, non un coût de calcul plat par appel.
La population des appels diffère aussi entre bras ; ces statistiques ne sont pas
des paires iso-état.

**Économie exploratoire :** Δ profit_year variante − référence moyen
`+47 100,67 £/an`, médiane `−73 429 £/an`, 1V/2D ; IC95 bootstrap
`[−77 480 ; +292 211] £/an`, valeur ratio des moyennes `+1,2335 %`.
La télémétrie annuelle au dernier point (1979, somme des trois parties) observe
le profit `profit_this_year_gbp` des services ferroviaires à environ
`7,927 M£` en référence et `6,593 M£` en variante. Ces services ne sont pas
un proxy interchangeable avec les seuls nouveaux `RAIL_BUILD`, et ce total
n'est ni le profit consolidé de la compagnie ni un profit prédit.

**Décision : refus de la qualification technique.** L'objectif `ABND + SITEB`
−30 % est inversé (9 → 29, +222 %), et le nombre de nouvelles constructions
recule de 78 à 69. La variante supprime des sites sur certains gisements
industriels : les listes natives filtrées à plat/constructible et limitées aux
premiers candidats peuvent produire zéro quai là où la spirale en proposait.
Le critère `ops ≤ ×1,5` ne peut pas rattraper cet échec : en particulier,
les faibles mesures d'opcodes viennent des retours sans plan. **Aucune porte A,
aucun changement de défaut ; `v307_sites=0`.** Pour reprendre cette piste, il
faudrait garantir un repli de faisabilité (ou élargir les listes natives tout en
préservant le rayon de captage) puis soumettre un nouveau bundle à une
qualification indépendante.
