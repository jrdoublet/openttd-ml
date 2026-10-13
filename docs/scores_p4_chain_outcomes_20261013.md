# P4 — chaîne score → tentative → construction → flotte/rendement (13/10/2026)

## Source et protocole

Nouveau worktree isolé `results/scores_p4_chain_stage_20261013`, détaché de
`c2a5be3`, depuis les overlays de la sonde P4 C77 déjà validée. Aucun fichier
du stage P4 comportemental 40×5, de `master` ou d'`origin/master` n'a été
modifié. Le flag `score_p4_flip_shadow=0` reste OFF dans les quatre difficultés.

Instrumentation supplémentaire sous le même flag de sonde :
`P4_FLIP_OUTCOME` est émis **après** retour du constructeur AIR/RAIL/ROAD/
WATER/FLEET, avec résultat `built/rejected/pending`, nombre de lignes avant/
après et ID réellement créé si applicable. Un `pending` RAIL apparié à la
reprise A* émet `P4_FLIP_RESUME` ; ne jamais appeler `pending` une construction.
La sonde émet un nouvel épisode après une tentative précédente même si les
deux têtes du projet demeurent identiques : l'ancien dédoublonnage masquait
les réélections. `P4_FLIP_HEAD` continue d'exiger tête historique rejouée
par identité, même tier C77 et simultanément finançables.

Campagne smoke `scores_p4_chain_smoke2x3_20261013`, 2 graines × 3 ans,
4/4 parties saines, image `openttd-lab:latest`. La première inversion
graine 123457 montre une tête RAIL qui entre en `pending` dans le témoin
et la construction AIR effective sous P4, `line_delta=1`.

Campagne développement
`scores_p4_chain_dev5x5_20261013`, bundle
`c61d66dfb12174bfe79928da058d8e44efdb92004b5fa2592c937ddc407422ee`,
graines 314159, 271828, 161803, 123457, 987653, 5 ans, 10 workers,
10 CPU, 8 Go, **10/10 parties saines et 5/5 paires**. Les deux bras
activent explicitement `decision_log=1` et `score_p4_flip_shadow=1`,
seule différence de politique :
`score_c70_stable_cohort=0` versus `=1`. Ces logs coûtent des opcodes.

## Résultats de la chaîne

Analyseur :
`sweeps/analyse_scores_p4_chain_20261013.py`.
Preuve JSON :
`results/scores_p4_chain_dev5x5_20261013_chain_analysis.json`.

| Événement, les deux bras réunis | N |
|---|---:|
| Inversions effectives de tête du même vivier C77 | 30 |
| Entrées constructeur `P4_FLIP_ATTEMPT` | 18 |
| Résultats directs `built` | 6 |
| Résultats directs `rejected` | 8 |
| Recherches RAIL `pending` | 4 |
| Reprises RAIL ultérieures `built` | 3 |
| Reprise RAIL `not_built` | 1 |
| **Constructions réconciliées à AIR_BUILD/RAIL_BUILD et ID ligne** | **9** |
| Inversions sans entrée constructeur | 12 |

Les 6 `built` directs étaient des créations AIR ; les 3 autres des
reprises de construction RAIL. Les chemins de constructeurs redonnent
le statut avant le journal de ligne, ce qui permet une jointure exacte
par ID. Des choix de projets en rang 0 peuvent être réévalués et rejetés :
une tête inversée n'est donc ni un achat certain, ni une construction
rentable, ni 30 décisions indépendantes.

Quatre lignes bâties en conséquence d'un flip ont un relevé
`LINE_REVENUE` à âge ≥2 en 1974 :

| Bras / seed / ligne | Modèle `pred_prof` | `real_prof` reporté | Événement flotte connu |
|---|---:|---:|---|
| Référence RAIL 123457, L37 | 40 074 £ | −2 531 £ | aucun |
| P4 stable AIR 123457, L29 | 79 076 £ | 15 266 £ | 1 |
| P4 stable AIR 314159, L26 | 101 641 £ | 39 002 £ | 0 |
| P4 stable AIR 987653, L41 | 74 036 £ | 28 335 £ | 1 |

Sur les trois AIR à maturité, les ratios descriptifs de profit
observé/prévu sont environ 0,193, 0,384, 0,383. Il s'agit de
**profits propres aux lignes**, pas de profits marginaux nets du
réseau C121 : amortissement, évolution de flotte (y compris mutations
non interceptées), concurrence et cannibalisation ne sont pas
neutralisés. Quatre lignes sont un échantillon insuffisant pour en
déduire un nouveau facteur ou un mode gagnant.

## Première divergence et séparation des mécanismes

Analyseur mensuel :
`sweeps/analyse_scores_p4_chain_trajectories_20261013.py`.
Source :
`results/scores_p4_chain_dev5x5_20261013.jsonl`.
Preuve :
`results/scores_p4_chain_dev5x5_20261013_trajectories.json`.

| Graine | Premier écart argent ON/OFF | Première tête C77 inversée observée | Premier écart profit annuel | Delta `profit_year` terminal |
|---|---|---|---|---:|
| 123457 | juin 1972 | mai 1972 | août 1972 | +84 905 £/an |
| 161803 | mai 1973 | **aucune dans la sonde** | août 1973 | −58 685 £/an |
| 271828 | juin 1972 | **janvier 1973 (après l'argent)** | août 1972 | +308 447 £/an |
| 314159 | novembre 1972 | novembre 1972 | février 1973 | −175 698 £/an |
| 987653 | mai 1972 | avril 1972 | août 1972 | −134 088 £/an |

La graine **271828** diverge financièrement bien **avant** son premier
flip déclaré ; la graine **161803** diverge sans aucun flip observé.
Ces deux cas interdisent d'attribuer toutes les différences de
trajectoire au score C70 : il existe des décalages de cadence/opcodes
et/ou des choix non capturés par le périmètre tête C77 de la sonde.
Sur les autres graines, la proximité chronologique constitue une
**hypothèse causale**, non une expérience de construction contrefactuelle
réussie. Toute nouvelle campagne économique devra désactiver
`decision_log` et `score_p4_flip_shadow` des deux bras.

Le delta moyen terminal du **5×5 instrumenté** est +4 976,2 £/an,
médiane −58 685 £/an, 2V/3D, Wilcoxon p=1, bootstrap
IC95 [−135 651,4 ; +174 321,8] £/an ;
`company_value` +2,02 % en ratio des moyennes. **Diagnostic only**,
aucune adoption. La gate P4 économique **pure 40×5** négative demeure
la seule qualification recevable du stable-cohort testé.

La télémétrie SIGNS des opcodes est **incomplète dans les dix parties**
(`observed_opcode_complete_cpu=false`) : référence
**79 107 931,8** événements-opcodes observés par graine en moyenne,
variant **73 377 784,2**, différence moyenne **−5 730 147,6**.
Ces chiffres reflètent des trajectoires et charges de travail différentes ;
ils ne sont ni des opcodes VM totaux, ni une preuve que la sonde P4 est
moins chère. Sur une graine, la différence est −24,15 M ; d'autres
graines divergent moins, ou même augmentent. Des profils exacts
hors instrumentation seraient nécessaires pour isoler le coût VM.

## Limites et prochaines expériences recevables

- Une décision locale contrefactuelle ne peut être assimilée à une
  construction contrefactuelle : A*, C83, V88, cash vivant,
  contraintes de site et ordonnancement ultérieur restent endogènes.
- L'API de profit de véhicules disparus ne permet pas de reconstruire
  exactement l'historique de la flotte sans transactions persistées.
  Le filtre « stable survivants » omet sélectivement les exercices
  perturbés, qui sont justement ceux où la calibration est nécessaire.
- Corriger l'estimation d'une cohorte doit tenir compte de véhicule
  survivant / capacité réellement livrée / amortissement / externalités ;
  Save/Load doit préserver état et année comptable, pas seulement
  l'instantané mensuel.
- Une calibration P4 adaptée ou P2 hors échantillon doit d'abord passer
  tests fonctionnels et smoke Squirrel, puis exploration 5×5,
  puis porte A40×5 **sur nouveau bundle strictement apparié** et
  validation indépendante si signal positif. Les résultats de ces sondes
  ne sont jamais utilisés comme gain économique.
