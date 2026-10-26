# MULTI-1 — troisième pilote ROUTE/TRACEX : NO-GO non exposé (26 octobre 2026)

**Verdict définitif de la variante `multi1_road_detour=2` : `NO-GO_NON_EXPOSE`.**
Les deux seuils d'exposition pré-enregistrés ont échoué. Les portes économiques
A 40×5 et B 20×10 **ne sont pas autorisées** pour ce pilote ; son réglage reste
`0` par défaut aux quatre difficultés, sans adoption.

## Provenance et validation préalable

- [Pré-enregistrement immuable](multi1_road_detour_prereg_20261026.md), publié
  **avant code** sous `733b92f5` ; implémentation publiée sous `1ef97a09`.
  Six variantes ROAD historiques, puis au maximum quatre détours bornés et
  64 essais additionnels, seulement en 1971–1973, multimodal, après échec
  historique `TRACEX` (jamais `DEPOTX` ou SITE). OFF=0, shadow=1, ON=2.
- Contrats et suite complète avant mesure : **2 926 tests OK** (5 ignorés,
  2 échecs attendus), `git diff --check` OK ; 58 réglages historiques préservés.
  Smoke 1×1 en 1970 : deux parties complètes, aucune différence de profit,
  attendu hors fenêtre. Save/Load réel graine 42 : **25 + 13** sauvegardes,
  `LOAD_RECONCILE` positif, pas d'erreur bloquante. La compagnie fantôme inerte
  du harnais solo n'est pas une preuve d'équivalence économique same-world.
- Campagne de diagnostic réutilisée **sans la relancer** :
  `results/multi1_roaddetour_exposure_5x5_20261026.{json,jsonl,manifest.json}`
  et dix logs `results/multi1_roaddetour_exposure_5x5_20261026_engine/`.
  Graines **42,100,7,999,2026**, une répétition, 1970–1974, 256²,
  `OpexAI[multi1_road_detour=0,probes=258]` contre
  `OpexAI[multi1_road_detour=2,probes=258]`, `--script-debug`, AAAHogEx
  figé, 10 workers, 10 CPU, 8 Gio. **10/10 parties et 5/5 paires complètes**,
  deux compagnies actives par duel, quatre trimestres de `profit_year`,
  aucune exécution en échec. Manifeste Git **propre** sur
  `1ef97a09ab723c8492eff0be155a4d13d079a3c2`, bundle
  `701dfc81192029831ebc1b65db1ea89e2da13f7092bbe21163f9c4e4cf6f3c20`,
  image Docker `openttd-lab:latest` SHA256
  `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.

## Exposition physique et conditions d'arrêt

Les journaux moteur ont été parcourus dans leur intégralité, **bras par bras**.
`MULTI1_ROAD_DETOUR action=rescue` est **absent des cinq logs ON**, et le
marqueur `MULTI1_ROAD_DETOUR` est absent des dix logs. Un `ROAD_BUILD` sans
`rescue` préalable sur son `(src,dst)` ne compte **jamais** comme construction
attribuable au levier.

| Graine | Rescues ON | `ROAD_BUILD` ON | `ROAD_BUILD` OFF | Rejets ROAD `detail=TRACEX` ON / OFF | Constructions associées ≤90 j |
|---|---:|---:|---:|---:|---:|
| 42 | 0 | 2 | 4 | 4 / 11 | 0 |
| 100 | 0 | 2 | 1 | 22 / 40 | 0 |
| 7 | 0 | 1 | 2 | 4 / 4 | 0 |
| 999 | 0 | 2 | 1 | 16 / 3 | 0 |
| 2026 | 0 | 4 | 4 | 0 / 0 | 0 |
| **Total** | **0** | **11** | **12** | **46 / 58** | **0** |

Critère 1 : **0/5** graines ayant au moins un `rescue`, contre **≥3/5** exigées.
Critère 2 : **0/5** graines ayant un `ROAD_BUILD` du même couple `(src,dst)`
moins de 90 jours après un rescue, contre **≥2/5** exigées. Le premier seuil
échoue déjà ; le second échoue nécessairement en l'absence de rescue.
Les 46/58 rejets sont des **tentatives**, pas des marchés uniques ni des
constructions rattrapables. Ils ne démontrent pas que la recherche additionnelle
a été franchie pour chacun, ni que les détours proposés sont constructibles.

## Résultat économique descriptif — **pas** une porte A

Sur ces seules cinq paires instrumentées avec `probes=258`, `profit_year`
Opex ON−OFF à fin 1974 vaut par graine :

| Graine | Δ `profit_year` (£/an) |
|---|---:|
| 42 | −116 133 |
| 100 | −325 414 |
| 7 | +599 441 |
| 999 | −97 834 |
| 2026 | 0 |

**Moyenne +12 012 £/an**, médiane −97 834, **1 victoire / 3 défaites /
1 égalité**, Wilcoxon bilatéral exact **p=0,875**, IC95 bootstrap de la moyenne
**[−214 815,2 ; +316 871,2] £/an**, 20 000 rééchantillonnages, graine 0.
Le ratio des valeurs moyennes ON/OFF est **1,025782** (+2,58 %), et le
profit moyen de référence **2 924 577,8 £/an**.

Les trajectoires des bras diffèrent parfois malgré **zéro rescue** : les
tentatives supplémentaires peuvent consommer des opcodes et décaler des
décisions, mais ces journaux ne démontrent pas cette explication causale.
À plus forte raison, le delta n'est **pas attribuable à des routes sauvées**.
La comparaison est explicitement `diagnostic_only` dans le JSON du harnais :
elle n'a que cinq graines (non les 40 de A), des sondes lourdes, et elle ne
valide aucun critère de gain économique.

## Décision et suite du chantier

`NO-GO_NON_EXPOSE` **sans retouche du pré-enregistrement**, sans porte A/B et
sans changement du défaut. Préserver les trois essais négatifs de MULTI-1 et
leurs résultats bruts. H3 reste soutenue **descriptivement** par l'important
parc ROUTE d'AAAHogEx, mais aucun des trois mécanismes essayés n'a démontré une
exposition constructive suffisante. Une quatrième intervention devra porter
sur **un mécanisme distinct** avec gisement mesuré et critères publiés **avant**
le code ; elle ne pourra réutiliser ni assouplir les seuils des trois pilotes.
