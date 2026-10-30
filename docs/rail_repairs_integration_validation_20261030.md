# Intégration RAIL-REPAIR + V233L-CONSTRUCTIBILITE — 30 octobre 2026

## Portée et règle de sécurité

Base `origin/master` au commit `729eafb8`, défauts publiés `estim_unifie=31`
et `eb14_progressive=3` **inchangés**. Le `master` local contient des
modifications d'autres tâches : l'intégration a été faite dans le worktree
`feat/rail-repairs-combined-20261030`, sans lui substituer un état.

| Dossier | Option opt-in (valeur 0 sur les 4 difficultés) | Comportement limité |
|---|---|---|
| RAIL-REPAIR-SITE | `rail_repair_join_site=1` | Après échec de jointure `shared_dest`, deux anneaux de quais physiques alternatifs, même gare |
| RAIL-REPAIR-V131 | `rail_repair_v131_focus=1` | Une obstruction locale de ≤4 tuiles, un seul splice, A* ≤900 |
| RAIL-REPAIR-ASTAR | `rail_repair_astar_pair=1` | Un seul A* 1×1 sur autre paire déjà testée, après `ABND/NOPA`, ≤900 itérations |
| RAIL-REPAIR-POSE | `rail_repair_pose_order=1` | Une inversion de deux poses contiguës sur emprises vierges, rollback sur échec |
| V233L-CONSTRUCTIBILITE | `v233l_constructibilite=1/2` | 1 devis physique monovoie passif ou 2 repli mono expérimental financé, une seule rame |

En OFF, chaque volet laisse son chemin historique. Les mécanismes
préexistants V131c, EB-2, V303/V307 restent déclarés **non adoptés**.
La reprise STNFAIL/LOOPFAIL transactionnelle globale n'est **pas** livrée
par ces options : il faut encore une comptabilité d'ownership par objet
(quai, rail, pont, tunnel, véhicule), reprise sûre et preuve sur carte.

## Validation croisée en moteur

Après fusion, un premier smoke toutes options ON, seed42, année 1970,
échouait : Squirrel signalait dans `_continueRailSearch()` l'accès au champ
inexistant `astarRepairTried`. Le chemin de préchargement C121
`_startRailStockSearch()` crée lui aussi `kind="primary"`, mais le nouveau
champ n'avait été initialisé que par `_startRailSearch()`. **Bug corrigé** :
initialiser les trois champs A* de la recherche stock lorsque l'opt-in est
activé et vérifier par contrat hôte les deux producteurs de l'état.

Pour contourner l'indisponibilité temporaire HTTP 502 de BaNaNaS au moment
des smokes, les bibliothèques suivantes ont été copiées **sans modification**
depuis le bundle immuable
`v233l_construct_seed42_1x10_20261030b` et leur SHA-256 a été vérifié
contre son manifeste : Queue.FibonacciHeap-3, Pathfinder.Rail-1,
Graph.AyStar-4, Queue.BinaryHeap-1. Seuls des lanceurs dans `results/`
(ignorés par Git) les utilisent ; **aucune dépendance système n'est changée**.

**Smoke 1×1 1970, graine 42, 256², OpenTTD 15.3 :** les cinq options ON
passent, `profit_year=341 965 £`, valeur=262 389 £, 14 véhicules,
19 gares. Un second banc OFF contre toutes options ON sur la même graine
donne exactement ces cinq mesures dans les deux bras, `run_ok=1`.
Cela valide le chemin moteur sur un an **sans démontrer l'exposition**
aux réparations ou le comportement sur cinq/dix ans.

**Save/Load réel Docker, toutes options ON :** `seed=42`, phase A 1 an,
13 sauvegardes ; reload de `1970-07-01` depuis `000000005.sav` ; phase B
1 an, 13 sauvegardes ; `status=OK`, ligne `LOAD_RECONCILE` présente et
aucune erreur `Load function` / `Your script made an error`.
Un compte de compagnie humaine fantôme additionnelle est connu du harnais
au rechargement : ne pas utiliser les agrégats globaux du test pour un
classement économique.

**Tests hôtes :** 79/79 réussis sur les suites intégrées
`test_rail_repair_astar_pose_20261030`,
`test_rail_repair_site_v131_focus`, `test_v233l_constructibilite`,
`test_diag_v233l`, `test_v199_robust_build`,
`test_v184_rail_search_slots`, `test_v131_rail_repair`,
`test_v131_town_clearance`. Les tests historiques qui projettent une
ancienne chaîne `info.nut` vers ESTIM=0 échouaient déjà sur le HEAD
initial (`ESTIM-1 info.nut hunk 0`, attentes 83 réglages alors que 85
existent déjà) ; ils ne sont pas présentés comme verts.

## Décision économique

Le banc V233L monovoie de dix ans graine42 donne −429 580 £/an de
`profit_year` et −10,44 % de valeur de compagnie face au mode passif,
deux bras sains, `fail_primary_and_value_guard`. Il ne démontre pas
le sauvetage des trois OD historiques sur la même sauvegarde et ne
justifie pas l'adoption. Rapport :
[V233L-CONSTRUCTIBILITE](v233l_constructibilite_20261030.md).

**Les cinq options restent OFF / non qualifiées pour adoption**. Les tâches
physiques restent ouvertes : déterminer sur des parties instrumentées
quelles OD sont effectivement converties en `RAIL_BUILD`, retrouver une
constructibilité réelle et profitable et seulement alors pré-enregistrer
la porte 40×5 / non-érosion 20×10. Ne pas réinterpréter la présence d'un
plan ou d'un devis `AITestMode` comme une construction réelle.

### Exposition exploratoire, cinq graines sur cinq ans

Un second banc de **10 parties saines sur 10** (seed 42, 100, 7, 999, 2026,
1970–1974, 256², une seule répétition) compare `OpexAI` avec les cinq
options à 0 contre `rail_repair_join_site=1`,
`rail_repair_v131_focus=1`, `rail_repair_astar_pair=1`,
`rail_repair_pose_order=1` et **V233L en mode `1` passif**. L'adversaire
AAAHogEx n'est pas inclus dans ces deux bras de diagnostic d'exposition.

| Graine | Différence `profit_year` ON − OFF | Différence valeur ON − OFF |
|---|---:|---:|
| 7 | +89 029 £/an | +486 620 £ |
| 42 | +191 405 £/an | +285 484 £ |
| 100 | +79 303 £/an | −413 770 £ |
| 999 | −471 382 £/an | −866 313 £ |
| 2026 | +586 116 £/an | +455 071 £ |

**Moyenne appariée : +94 894,2 £/an ; ratio des moyennes `1,0184483`
(+1,84 %), 4 victoires / 1 défaite.** Wilcoxon bilatéral exact :
`p=0,4375`. IC95 bootstrap empirique sur les 5 paires,
`[−228 688 ; +385 336] £/an` (énumération exhaustive des `5^5`
rééchantillonnages). Ratio de valeurs des moyennes `0,99905`.
Résultats locaux :
`results/rail_repairs_off_vs_alloptins_exposure_5x5_20261030.json`.

**Lecture :** ce signal n'est pas assez robuste pour une porte A, et une
différence globale ne dit pas si SITE, V131, ASTAR ou POSE a sauvé une OD
physique particulière. Il faut attribuer des `RAIL_BUILD` à la réparation
qui les a permises, contrôler coûts, déchets et profit de la ligne, puis
tester chaque opt-in isolément avant tout protocole multi-graines A/B.
Le mode V233L `1` n'autorise aucun repli : son essai `2` décennal négatif
reste une expérience distincte et **non adoptée**.
