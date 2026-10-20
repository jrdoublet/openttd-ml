# Diagnostic des mécanismes économiquement nuls — protocole réutilisable

Date : 20 octobre 2026. Source V289 : branche `v289`, commit `642d6e8e`.

## Objectif

Séparer **absence d'exposition**, **échec de transmission au chantier**,
**absence de gain causal** et **effet économique compensé**. Ne pas prolonger
un banc nul avant d'avoir localisé dans quelle catégorie se trouve l'échec.

## Échantillons V289

- Banc économique SANS journal : `results/v289_porteA_rail_40x3_pc_20261020.json` et `.jsonl`, 40 graines × 3 ans, V289 0/1, rail seul, 80 parties. Δ `profit_year` −12 558,725 £/an, V/D/E 19/21/0, IC95 bootstrap [−72 278,85 ; +47 046,45], verdict `fail_primary`, CV +0,6226 %.
- Diagnostic AVEC `decision_log=1`, `--script-debug`, `--line-telemetry` et `--line-telemetry-monthly` dans les deux bras : `results/v289_slack_diag_worst6_2y_log_20261020.json`, 6 graines × 2 ans, 12 parties. Graines sélectionnées post hoc parmi les six pires deltas profit du banc à 3 ans : `65537 701256 230185 424242 59527 455216`. Ce banc est **diagnostique, pas qualifiant**.
- Contrôle de l'observateur : `results/v289_observer_effect_3x2_log_vs_nolog_20261020.json`, 3 graines × 2 ans, `v289_slack_workers=0` DES DEUX CÔTÉS, `decision_log=0` en référence et `decision_log=1` en variante, autres options égales. L'objectif est de quantifier les changements introduits par le journal.

## Preuves d'exposition V289 (6 graines × 2 ans)

Les logs moteur `results/v289_slack_diag_worst6_2y_log_20261020_engine/v289_seed*_r0.log` contiennent les événements `OPEX ... V289_*` :

| Indicateur | Total |
|---|---:|
| `V289_RAIL_START` | 72 (72 `ok=1`) |
| `V289_RAIL_ADOPT` | 42 |
| `V289_RAIL_DEPOSIT` | 11 |
| `V289_RAIL_DROP` | 10 |
| `V289_RAIL_TIMEOUT` | 4 |
| `V289_STOCK_EXPIRE` | 4 |
| `V289_SLACK` mensuels | 138 |
| `V289_SLACK.calls` (somme des mois enregistrés) | 9 541 |
| `V289_SLACK.ops_rail` (somme des mois enregistrés) | 47 229 693 opcodes |

Un suivi par paire `(src,dst)` et ordre temporel relie **31 adoptions à une `RAIL_BUILD` ultérieure sur la même paire** et **4 dépôts à une `RAIL_BUILD` ultérieure sur la même paire**. Cela prouve la présence de constructions ultérieures sur ces paires, **pas** que ces constructions sont incrémentales par rapport au témoin ni que le stock a nécessairement été le chemin consommé (ajouter à l'avenir un événement de consommation avec `lineId`). Le témoin construit 79 lignes et la variante 77 sur les six logs.

| Graine | Starts | Adoptions | Dépôts | Builds OFF/ON | Δ profit journalisé à 2 ans | Δ profit sans journal à 2 ans (mêmes graines du 40×3) |
|---|---:|---:|---:|---:|---:|---:|
| 65537 | 14 | 11 | 2 | 12/14 | −56 368 | −117 544 |
| 701256 | 12 | 7 | 0 | 14/12 | +1 091 | −129 928 |
| 230185 | 14 | 9 | 3 | 16/15 | −87 904 | −225 650 |
| 424242 | 9 | 2 | 3 | 13/10 | −10 057 | −172 392 |
| 59527 | 12 | 7 | 2 | 11/12 | +60 050 | −35 750 |
| 455216 | 11 | 6 | 1 | 13/14 | +38 807 | −95 395 |
| **Moyenne** | | | | | **−9 064** | **−129 443** |

Les 72 `V289_RAIL_START` coûtent individuellement **12 934–296 590 opcodes**, médiane **46 288**, moyenne **57 585**, somme **4 146 095**. Les 72 dépassent le seuil de *déclenchement* `V289_RAIL_START_MIN=6000`; cela n'établit pas le franchissement du tick à chaque démarrage (le reliquat exact n'est pas journalisé), mais prouve que cette garde ne borne PAS leur coût à 6 000. Les démarrages préparent les quais et peuvent modifier les dates de passage des autres tâches. Le worker réserve aussi des extrémités, entretient un stock parfois inutilisé et revalide/cooldown des paires : contrôler les substitutions de projets, pas simplement la fréquence des événements.

## Effet observateur : VALIDÉ, PAS NÉGLIGEABLE

Le contrôle V289=0 contre V289=0 donne, à fin 1971 :

| Graine | Sans `decision_log` | Avec `decision_log` | Δ journal seul |
|---|---:|---:|---:|
| 65537 | 784 093 | 787 939 | +3 846 |
| 701256 | 769 467 | 593 191 | −176 276 |
| 230185 | 746 237 | 673 289 | −72 948 |

Le contrôle sans journal reproduit exactement les anciens checkpoints non journalisés. Le contrôle avec journal reproduit exactement la référence journalisée du diagnostic. Donc ce n'est ni la graine ni un changement de code : **activer le journal est une intervention sur l'ordonnancement**. Ne jamais qualifier sur les gains/pertes du diagnostic lourd et ne pas inférer d'un diagnostic `decision_log=1` la distribution des événements du banc propre.

## Protocole commun pour V131c, V285 mode 7, V275 sobre multimodal

1. **Geler l'économie** : comparaison originale sans `decision_log`, mêmes sources, graines, horizon, cartes, rival, ressources, valeurs d'option. Préserver résultats JSON/JSONL et manifeste, avec verdict apparié et bootstrap. Ce banc seul qualifie économiquement.
2. **Vérifier l'exposition** : sur 3–6 graines discriminantes et horizon suffisamment court pour capter les premiers événements, activer `decision_log=1` **dans les deux bras**, avec `--script-debug`; conserver le même `probes` et la télémétrie désirée dans les deux bras. Les graines ciblées sont un outil de diagnostic, jamais une population de validation.
3. **Contrôler l'observateur** : réaliser au besoin 2–3 paires où le *mécanisme reste OFF dans les deux bras*, seule l'option de journal diffère. Comparer les checkpoints économiques au contrôle propre. Si les valeurs divergent, les événements lourds servent à la compréhension **qualitative** uniquement.
4. **Construire un entonnoir causal** par graine, date et identifiant stable : `éligible → appelé → tentative → accepté/plan prêt → sélection → constructeur → lineId/véhicule → ligne mature → profit terminal`. Journaliser séparément les rejets et `reason` (finance, concurrence, géométrie, timeout, cooldown, échéance). Conserver les coûts en opcodes et le reliquat réel avant/après, ainsi que `tick_before/tick_after`, surtout si une action franchit le tick.
5. **Tracer les substitutions** : comparer premier point de divergence des décisions, `PROJECT_CHOSEN`, `RAIL_ATTEMPT`, `RAIL_BUILD`, flotte, cash, coûts réels, lignes et profits. Une construction réussie sur la même paire ne suffit pas : il faut prouver le **contre-factuel** (quel projet a été retardé/évincé ?).
6. **Améliorer l'instrumentation peu intrusive si nécessaire** : compteurs en mémoire incrémentés sans `AILog.Info` à chaque décision, sortie groupée à une fréquence basse (ou un événement final compact) et un contrôle AA. Préférer une trace ciblée, proche de zéro coût, avant tout 20×10 instrumenté.
7. **Décision de poursuite** : (i) zéro exposition : corriger garde, ne pas rallonger ; (ii) exposition forte mais conversion faible : corriger liaison/filtrage/chantier ; (iii) construction mais éviction défavorable : traiter financement et priorités ; (iv) exposition mature favorable mais horizon trop court : petit banc 5–10 ans **sans** journal puis vraie validation indépendante. Jamais de conclusion statistique sur 3–6 graines choisies post hoc.

### Application par variante

- **V131c (+3,9 k, nul)** : mesurer la fréquence des entrées en réparation, tracés sauvés, coût A* et travaux finalement construits (`RAIL_ATTEMPT`, raisons géométriques, `RAIL_BUILD_FAIL`), contre candidats abandonnés et budget CPU. Distinguer réparation d'une vraie ligne marginale.
- **V285 mode 7 (+3,4 k, nul)** : séparer le bit des quais longs des bits de wagons ; journaliser par ligne `éligible → quai suffisant → essai wagon → succès/échec → composition trains → remplissage → recette/profit mature`, avec limites « un wagon / 90 jours » et lignes à train unique. Tester le mode 6 (wagons seuls) seulement après exposition observée ; distinguer hausse de capital précoce et revenu tardif.
- **V275 sobre multimodal (+0,2 k, nul)** : identifier d'abord le point exact de décision dans le code et compter les actions effectivement différentes selon les modes AIR/RAIL/ROAD/WATER, puis les travaux substitués, le cash non investi, les effets de concurrence et les horizons de maturation. Ne pas supposer que faible delta implique faible exposition.

Les six graines ciblées avaient un Δ `profit_year` moyen sans journal de **−129 443 £/an à fin 1971** puis **−325 823 £/an à fin 1972** ; sélectionnées sur les pertes à fin 1972, elles ne prouvent pas une tendance populationnelle, mais ne suggèrent aucune récupération à court terme.

## Conclusion V289

L'exposition est **positive et fréquente**, mais 19 des 72 démarrages n'aboutissent ni à une adoption ni à un dépôt journalisé ; le déclenchement n'est pas borné en opcodes par le seuil de 6 000, et les réseaux construits changent. **Pas de banc plus long en priorité**, avant de mesurer le franchissement de ticks, l'utilisation exacte du stock et les substitutions de projets sur une instrumentation peu intrusive. Conserver V289 OFF par défaut.
