# P0 opcodes — autopsie du portefeuille 1970–1973

**Analyse hors moteur du 12/10/2026, diagnostic, aucun correctif adopté.**
Référence : `docs/diagnostic_opcodes_1970_1973_20261012.md`, profil gelé
`evidence/review/opcode_early4_20261012/`. Les données d'appels nouvelles
sont dans `projects_calls.json`, générées par
`sweeps/analyse_projects_passes_early4.py` à partir des cinq journaux originaux.
Les cinq graines 42/100/999/1234/5678 sont exploratoires ; les métriques
économiques proviennent **du témoin sans sondes**, et ces nombres d'appels
**du diagnostic instrumenté**. Aucun rapprochement graine par graine n'est
une preuve de causalité économique.

## Première différence structurante : fréquence contre longueur des passes

`C39_PASS_CLOCK` (exercice comptable précédent) mesure environ 139,6 / 186,2 /
80,2 / **45,0** sélections de `projects` par graine de 1970 à 1973.
Le budget occupé correspondant vaut 9,425 / 18,261 / 23,416 /
**29,730 M** par graine et par an. Le coût apparent par passage atteint
environ **661 k en 1973**, contre **98 k en 1971**, malgré quatre fois
moins de passages. Cette évolution ne s'explique donc pas par le nombre
de passages vides.

La distribution des **sommes internes** `PROJECTS_COST.build_ops + fleet_ops +
regen_ops` par appel horodaté confirme la queue de distribution. Les
quantiles ci-dessous sont calculés sur tous les appels des cinq graines
(685 / 936 / 399 / 214 appels), avec interpolation linéaire :

| Année | Moyenne | Médiane | p95 | Maximum | Passes avec `built>0` / passes enregistrées |
|---|---:|---:|---:|---:|---:|
| 1970 | 56,1 k | 4,8 k | 571,6 k | 1,370 M | 51 / 685 |
| 1971 | 104,1 k | 7,5 k | 663,3 k | 1,975 M | 145 / 936 |
| 1972 | 289,5 k | 10,8 k | 1,845 M | 4,930 M | 82 / 399 |
| 1973 | **639,5 k** | **133,7 k** | **2,249 M** | **21,279 M** | **107 / 214** |

La moitié des appels enregistrés de 1973 ont `built>0` ; `built` est le
**nombre de projets aboutis dans la passe** et comprend les projets
de flotte, ce qui ne vaut pas autant de nouvelles lignes. La classe
`SCHED_IDLE` `projects_useful` est encore plus large (peut inclure un
travail de recherche qui progresse). **Ni l'une ni l'autre ne mesure la
rentabilité**, et les passes sorties avant `PROJECTS_COST` peuvent manquer.

Exemple extrême, graine **999**, `1973-07-13` :
`PROJECTS_COST build_ops=17546253 fleet_ops=89706 regen_ops=3642995
regen=incremental built=3 stop=rail_search` ; `SCHED_IDLE t=projects`
relève **21 300 656 unités de fenêtre, 2 135 ticks, 116 jours**.
`SELECTION_LIGHT path=incremental` est simultanément à 1 298 749 unités,
524 alternatives, 64 retenues. Les traces `P2_BUILD`/`P5_BUILD_LINE`
constatent **une seule nouvelle ligne physique nette rail** (id 40),
alors que `PROJECTS_COST built=3` compte trois projets aboutis pendant
la passe (dont des projets de flotte possibles). **Aucune recherche
`P5_RAIL_SEARCH` à coût positif sur la graine 999 pendant 1973** :
le pic de 17,546 M en `build_ops` ne peut donc être imputé à une
recherche A* facturée par P5. À lui seul, il représente **34,9 % de
tous les `build_ops` 1973 des cinq graines**. Le p95 `build_ops` par
passage est beaucoup plus bas, ~0,684 M ; c'est un événement extrême.
Ce passage prouve que de longues opérations peuvent monopoliser la fenêtre
de calcul/commande pendant que le portefeuille essaie de construire. Il
ne prouve pas que ces **21 M** correspondent à des instructions Squirrel
CPU éliminables, ni que ces trois constructions expliquent la perte de profit.

### Production effective de lignes dans les parties profilées

Le journal `P5_BUILD_LINE` suit les **variations positives nettes du
nombre de lignes `_lines` après une tâche `projects`**, pas
nécessairement chaque création brute lorsqu'une suppression survient dans
la même tâche. Le journal
`P5_RAIL_SEARCH` suit les recherches. L'analyseur indépendant
`sweeps/analyse_project_output_early4.py` conserve les événements par
année, graine, mois et mode dans `project_builds_searches.json`.
Il distingue les **recherches à coût non nul** de leurs rappels/relectures
`P5_RAIL_SEARCH ops=0` : ceux-ci ne doivent pas être comptabilisés
comme de nouvelles recherches coûteuses P5 (ils peuvent correspondre
à des callbacks sur une recherche précédemment avancée). Les événements
de croissance nette
ne disent pas si la ligne sera encore active ou rentable fin d'année.

| Année | Lignes AIR | Lignes RAIL | Autres lignes | Recherches rail avec `ops>0` | Fenêtres de recherche rail | Jours rapportés |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | 7,4 | 0,0 | 0,0 | 2,8 | 2,974 M | 19,6 |
| 1971 | **19,0** | 1,8 | 0,8 ROAD | 0,6 | 0,611 M | 9,6 |
| 1972 | 12,0 | 1,2 | 0,0 | 1,6 | 6,390 M | 137,6 |
| 1973 | **7,2** | **1,8** | 0,6 ROAD + 0,2 WATER | 2,2 | **6,943 M** | **157,2** |

Moyennes sur cinq graines **instrumentées**, différentes des entreprises
du témoin économique sans sondes. `P5_RAIL_SEARCH.ops` recouvre C39
et ne constitue pas un budget additionnel (le C39 inclut notamment
d'autres recherches C121). En 1973, seuls 2,2 appels de recherche par
graine ont un coût strictement positif pour 9,8 événements `P5_RAIL_SEARCH`
au total ; les 7,6 autres sont des résultats/rappels non facturés par
cette sonde. La stagnation des nouvelles lignes AIR et RAIL est un
**signal de débit de réalisation** cohérent avec l'écart économique,
mais il reste à relier aux raisons d'admission, de construction et aux
attentes individuelles avant d'en déduire une cause.

### Première contraction 1972 et hétérogénéité des mécanismes

Un quatrième analyseur `sweeps/analyse_project_admission_early4.py`
décode `P2_PASS` et `P5_RAIL_PASS`. La preuve
`project_admission_p2.json` contient les distributions **par graine,
mois et année** :

| Mesure instrumentée (moyenne/graine) | 1971 | 1972 | 1973 |
|---|---:|---:|---:|
| Passages `P2_PASS` | 186,2 | 80,6 | 44,6 |
| `in_best=0` à l'entrée de la tâche | 144,2 | 59,2 | 14,4 |
| Passages avec progression physique nette (`n_built>0`) | 28,2 | 16,2 | 21,4 |
| Alternatives rail présentes **après** dispatch | 0,0 | 21,0 | 44,6 |
| Rail finançable dans la photo **après** dispatch | 0,0 | 20,6 | 36,4 |
| Lignes RAIL nettes observées | 1,8 | 1,2 | 1,8 |

L'absence de vivier au début de certains passages n'est **pas un
phénomène homogène**. En 1972, **276 des 296** passages initialement
vides proviennent de la **seule graine 42**, qui effectue 296 passages,
contre seulement 12 pour la graine 999. En 1973, **les 72 passages
initialement vides sont tous ceux de la graine 100**. Les quatre autres
graines n'ont aucun passage initialement vide cette année-là. Les
goulots possibles comprennent des réitérations fréquentes avec vivier
vide et des passages très longs avec candidats encore disponibles.

Le **premier signal annuel de coût** apparaît en 1972 : régénérations
`PROJECTS_COST.regen.incremental` de 10,327 M (1971) à 17,123 M,
resélection incrémentale de 1,240 M à 6,519 M, tandis que les lignes
AIR nettes observées passent de 19 à 12. La hausse de régénération
existe chez **quatre graines sur cinq**, 42 étant l'exception. Cela
ne démontre pas que les refresh ont empêché des constructions : il
peut aussi s'agir d'un coût consécutif aux constructions abouties.

En 1973, les six premiers mois n'enregistrent que **44 passages P2
sur cinq graines**, contre **179** sur les six derniers mois. Par
graine sur ce premier semestre : 42 enregistre 15 passages, 100 en
enregistre 19, 999 **zéro**, 1234 et 5678 en enregistrent 5 chacune.
La distribution temporelle, les suspensions et les candidats doivent
être joints à la même exécution avant de décider de son mécanisme.
`P5_RAIL_PASS` examine les alternatives **après** le dispatch ; son
état rail finançable ne prouve pas qu'un rail aurait pu être construit
au début de la passe. Son compteur `stop` n'est pas non plus un motif
causal de rejet des commandes.

## Où vont les unités de fenêtre mesurées ?

En **1973**, les trois intervalles consécutifs de `PROJECTS_COST`
totalisent en moyenne par graine : **14,502 M** en mise à jour de
portefeuille (`regen.incremental`), **10,066 M** dans la passe de
construction (`build_ops`, commandes/attentes comprises), et **2,802 M**
pour préparer la flotte (`fleet_ops`). Soit **27,370 M** mesurés dans
les appels journalisés. L'écart avec les **29,730 M** du registre C39
ne doit pas être artificiellement affecté à une phase : fenêtres,
retours précoces et redécoupage A* diffèrent. En particulier, les
`SELECTION_LIGHT` suivants sont des **sous-fenêtres chevauchantes** :

| Sous-fenêtre sélection | 1970 (total, 5 graines) | 1973 (total, 5 graines) | Candidats moyens par appel |
|---|---:|---:|---:|
| `reselect` | 73,402 M / 1 668 appels | 35,677 M / 178 appels | 87,2 → 82,2 |
| `incremental` | 3,283 M / 56 appels | 26,883 M / 108 appels | 65,9 → 95,5 |
| `full` | 0,032 M / 5 appels | 3,464 M / 5 appels | 1 → 278,8 |

La resélection passe d'environ **44 k à 200 k par appel** alors que le
nombre moyen d'alternatives reste voisin. C'est un **signal d'augmentation
du coût intrinsèque de revalidation/score ou de coût d'accès à l'état
vivant**. L'augmentation n'est pas entièrement expliquée par un pool
plus vaste. Elle demeure une hypothèse, car `OpexOpsMeasureEnd`
impute chaque tick traversé et le nombre de projets par mode varie.

Appels à examiner à l'échelle des sous-fonctions :

- `projects_update.nut:92-138,194-245` : parcours de tous les
  `candidateGroups`, `OpexIncrementalCandidateStillValid`, `RememberAll`,
  filtrage des alternatives, `OpexProjectSelectAffordable` et finalisation.
  Une vraie construction ou un abandon peut rendre une partie de ce
  travail **nécessaire** ; le scan n'est pas un gaspillage démontré.
- `projects_selection.nut:1115-1168,1188-1337,1576-1650` : fit de flotte,
  états de slots, scoring et insertion bornée Top-K avec comparateurs
  dépendant de l'état courant. La sélection est **sensible à l'ordre** ;
  pas de tri ou mémoïsation de score sans preuve de parité VM.
- `task_projects.nut:1385-1439,1567-1584,1666-1738,1761-1965` :
  passages d'admission, revalidation d'AIR, seuil de batch C75, tentatives
  par mode et recherche rail reprenable. Le compteur `built` ne suffit
  pas à classer une vérification comme utile/inutile.
- `task_projects.nut:2048-2155` : après construction ou abandon,
  `_resizeAirFleets` en mode plan et `OpexIncrementalUpdateProjects`.
  Cette zone domine le coût de régénération mesuré ; conserver le
  rafraîchissement des décisions AIR après une nouvelle ligne.
- `scheduler.nut:25-112`, `budget.nut:19-30` : la mesure est une
  **fenêtre de budget, pas les instructions VM**. `SCHED_IDLE` recouvre C39.

Dans `SCHED_IDLE`, `projects_empty` tombe à environ **0,292 M en 1973**
contre `projects_useful` à **28,488 M**. Les 14,4 passages vides par
graine ne constituent pas la cible principale ; ceux avec progrès
dominent le coût observé.

## `air_fleet_no_work` : une classe qui masque la resélection du portefeuille

Sur les cinq mêmes journaux, la sonde `SELECTION_LIGHT path=reselect`
attribuée séquentiellement au passage `SCHED_IDLE t=air_fleet` qui se
termine donne les coûts annuels **moyens par graine** suivants :

| Année | `air_fleet` (M) | Resélection incluse (M) | Fraction | Resélections/passe (moy.) |
|---|---:|---:|---:|---:|
| 1970 | 1,594 | 1,057 | 66,3 % | 31,8 / 139,6 |
| 1971 | 2,675 | 1,378 | 51,5 % | 42,8 / 186,2 |
| 1972 | 9,992 | 6,186 | 61,9 % | 10,4 / 80,0 |
| 1973 | **10,886** | **5,965** | **54,8 %** | **28,8 / 45,0** |

En **1973**, aucune fenêtre appariée ne présente de resélections
attribuées supérieures à l'enveloppe de sa tâche ; en 1970–1971,
on compte en moyenne **5,2 et 11 fenêtres par graine** avec un
dépassement, signal de limite de l'appariement par ordre des journaux,
réentrance ou différence de fenêtres. Les fractions 1970–1971 restent
**des indices** plutôt qu'une comptabilité exclusive certaine.
Le fichier `air_fleet_reselect_calls.json` conserve ce diagnostic
et ses limites pour les cinq graines ; le script et les fixtures se trouvent
dans `sweeps/analyse_air_fleet_reselect_early4.py` et
`sweeps/test_analyse_air_fleet_reselect_early4.py`.

Le chemin de code démontre l'explication de la fausse étiquette :
`scheduler_tasks.nut:941-963` exécute `_resizeAirFleets(year, fleetPlan)`;
si `fleetPlan.len()>0`, appelle `OpexInjectFleetProjects`, qui remplace
les candidats flotte, puis appelle `OpexReselectProjects` **sur le même
objet** (`projects_update.nut:5-42`). Le registre
`ledgers.nut:718-725` considère néanmoins l'absence de nouveau véhicule
et la conservation de l'identité `this._projects` comme « no_work ».
Une nouvelle flotte peut ainsi modifier la liste finançable et les rangs
sans que `SCHED_IDLE` le reconnaisse. La priorité est **distinguer
aucune nouvelle opportunité, injection/résélection, achat et report**, puis
de mesurer la part de scoring coûteux qui se répète à données identiques.
Ce mécanisme ne permet **pas** de supprimer les 5,965 M : la resélection
peut conserver des décisions nécessaires.

## Hiérarchie des pistes, à valeur de diagnostic

### Coût intrinsèque du classement Top-K : exposition plus précise

Un profil complémentaire a exécuté la sonde existante
`probe_span_trace=1` sur **deux graines choisies pour leur contraste
42 et 999**, horizon cinq ans (1970–1973 clôturés). L'analyseur
`sweeps/analyse_spans_intrinsic_p0.py` reconstruit `SPAN id/par`
et les `SPAN_AGG` dans `spans_ab2_5y.json`, sans additionner les
parents aux enfants. Ce profil est **intrusif** : l'A/B observateur
avec/sans spans (4/4 duels sains) a un delta terminal de
**−154 909 £/an**, une variation de compagnie −15,78 %,
verdict brut `diagnostic_only` sur deux graines. Aucun chiffre
intrinsèque n'est directement convertible en profit économisé.

En 1973 dans la variante instrumentée :

| Sous-fenêtre | Graine 42 | Graine 999 |
|---|---:|---:|
| `select.full` (tous appels) | 23,552 M / 28 | 24,523 M / 31 |
| Dont `pub.select.score.insert`, agrégat intrafonction | **14,446 M / 7 247** | **14,461 M / 8 091** |
| `select.reselect` (parent, partiel) | 13,486 M / 14 | 15,320 M / 17 |
| `select.incremental` (parent, partiel) | 26,672 M / 13 | 23,797 M / 13 |
| `select.incremental` hors descendants directs | 16,485 M | 14,393 M |

L'insertion dans `Top-K` concentre donc **environ 60 % des fenêtres
`select.full`** de ces deux parties (environ 2 000 opcodes de fenêtre
par insertion instrumentée). Le chemin courant
`projects_selection.nut:1576-1682` cherche une position par boucle
arrière `O(K)` avec `K<=64`, comparant les priorités défensives,
scores (bonus early-slot) et revenus. En conditions par défaut,
une recherche binaire `O(log K)` sur le même comparateur stable
permet de tester une **optimisation de coût pur**. La preuve de
parité doit porter sur l'ordre exact sous égalités, V88, C77,
C118/C122 et les changements d'état d'une passe.

**Limites du sous-arbre SPAN** : 12 et 16 cas `negative_exclusive`,
6 parents manquants sur la graine 999 et des agrégats sans parent
dans les traces ; quelques spans franchissent les années de clôture.
Ces incohérences interdisent de présenter toutes les différences
parent − enfants comme une comptabilité CPU exclusive certaine.
Elles ne retirent pas le signal de coût local de
`pub.select.score.insert`, qui est publié explicitement comme somme
d'intervalles intra-fonction.

Le prototype de recherche binaire reste dans le worktree isolé
`results/p0_topk_binary_stage_20261012` avec deux réglages OFF aux
quatre difficultés : `p0_topk_binary` et `p0_topk_binary_check`.
Son contrôle sur cinq graines, années 1970–1973, a comparé
**57 859 insertions sur les mêmes références et états, zéro divergence
de sélection** ; fenêtres mesurées sur les entrées contrôlées :
103,690 M historique contre 34,584 M binaire, **−66,65 % local**.
Le contrôle lui-même perturbe la simulation et son A/B économique
est `diagnostic_only`. Le banc global 20×10 C66, sans check, est
le juge de l'admissibilité de cette variante ; aucune adoption à
ce stade.

| Rang | Mécanisme à vérifier | Enveloppe observée | Risque de modification |
|---|---|---:|---|
| P0a | Revalidation/résélection et mise à jour incrémentale après construction | 14,50 M/an en 1973, incluant sélection | **Élevé** : vivier obsolète, ordre et compatibilité C76/V141 |
| P0b | Longues tentatives de construction, recherche et commandes | 10,07 M/an dans `build_ops` en 1973 | **Élevé** : transaction partielle, franchissement de tick |
| P0c | Calcul de préparation de flotte après construction | 2,80 M/an (`fleet_ops`), imbriqué dans `projects` | Moyen/élevé : nouveaux avions et cash dynamique |
| P1 | Resélection lors des passages `air_fleet_no_work` | **5,965 M** de ses 10,886 M/an en 1973 | Élevé pour cadence ; vérifier calcul local répétitif dans le sélecteur et identité des sorties |
| P2 | Opportunités avant `Sleep` | 6,093 M de plafond 4 ans, dont 1,768 M worker/recherche en attente | Élevé si tâche peut franchir le tick |

Il ne s'agit **pas** de gains estimés : les enveloppes se recouvrent,
et supprimer intégralement les calculs nécessaires serait régressif.
Le classement reflète le volume, le signal de duplication possible
et la difficulté de maintenir la décision identique.

## Expériences préalables nécessaires

1. **Distinguer coût intrinsèque du portefeuille et ticks d'attente.**
   Tirer parti du réglage existant `probe_span_trace=1` (défaut 0), qui
   comporte déjà des spans `projects.pass`, `select.incremental`,
   `select.reselect`, `pub.select.filter`, `pub.select.score`,
   `pub.select.score.refresh_slots`, `pub.select.score.insert`
   et `projects.post_regen.incremental`. Les sous-fenêtres doivent être
   réconciliées sans addition parent/enfant et leur propre coût contrôlé
   contre le profil sans cette sonde. Cette sonde logue abondamment ;
   **ne pas la traiter comme neutre**.
2. **Découper les passages de construction par mode et résultat**, en
   incluant les p95, les jours/ticks franchis, le motif d'échec,
   l'effet sur la file et l'évolution des lignes physiques. Une
   instrumentation passive agrégée est préférable à un log par tentative
   si la première sonde perturbe la trajectoire.
3. **Tester une seule optimisation intrinsèque** après avoir démontré
   que le résultat est réutilisable à entrée vivante inchangée. Préserver
   l'ordre Top-K et les gardes C75/C76, ainsi que la publication AIR
   V141, les caches reconstructibles et Save/Load. Une comparaison
   VM sur des entrées figées vient avant la mesure moteur.
4. **Qualification économique/opcodes** : smoke puis 20 graines ×
 10 ans appariées C66 selon le protocole d'optimisation d'opcodes
   d'`AGENTS.md` §4 ; preuve de coût local et absence de dégradation
   économique, opcode globale, construction et cadence. Les règles
   de gain économique V102 portent sur les modifications réellement
   comportementales, préenregistrées séparément.

Au moment de cette lecture, Docker `desktop-linux` occupait déjà une
campagne `c121-initial-40x5-20261012-r1`. Aucun nouveau banc moteur
n'a été lancé et **aucun A/B de variante d'optimisation n'a de verdict**.

**Mise à jour postérieure le 12/10 (ne remplace pas l'état historique
ci-dessus)** : le prototype Top-K a finalement passé deux B20×10
économiques (`non_erosion`, avec et sans `probe_loop_ops`), mais l'économie
globale d'opcodes n'est pas statistiquement établie et les événements de
création de nouvelles lignes AIR/RAIL ne sont pas mesurés. **Adoption
NON DÉMONTRÉE, défaut OFF**. Les 57 859 insertions comparées en VM
sans mismatch prouvent la parité locale sur les entrées observées, pas
la neutralité de trajectoire. Voir
[`p0_topk_binary_qualification_20261012.md`](p0_topk_binary_qualification_20261012.md)
et [les preuves](../evidence/review/opcode_early4_20261012/topk_binary/README.md).

## Anomalie de vocabulaire du registre C39 résolue

Le worker `_activeWorker.kind="rail_stock"` visible en 1970 avec les
deux flags C80 désactivés provient du **rail prep C121** :
`rail_prep_c121.nut:260-288` appelle `_startRailStockSearch`, qui crée
un worker du même type interne via `task_rail.nut:2002-2007`.
`orchestrator.nut:269-295` connaît cette origine. Les deux compteurs
`worker|rail_stock` et `rail_astar_slice` se recouvrent alors presque
entièrement : **ils ne s'additionnent pas**, même au sein des tableaux C39.
L'étiquette analytique devrait inclure `isC121RailPrep`, sans changer
la création ni la politique des workers.

La limite de fin de tick reste celle du diagnostic parent :
**12,150 M** bruts abandonnés en quatre ans, **6,093 M** de plafond
4k/3k, **1,768 M** en présence d'un worker/recherche déjà en attente,
et **zéro opcodes supplémentaires exécutés et qualifiés**.
