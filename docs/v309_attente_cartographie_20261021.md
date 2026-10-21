# V309 — temps d'attente et cartographie, étape 0 hors partie

21 octobre 2026. Aucun nouveau banc, aucune modification du comportement IA.
Diagnostic reproductible :

```powershell
python -X utf8 sweeps/diag_v309_idle.py --selftest
python -X utf8 sweeps/diag_v309_idle.py
```

La campagne `v299_regen_3x10` avec `probes=10` n'est pas présente dans les
résultats PC accessibles. En remplacement, on a exploité l'archive **valide et
figée** `results/ac04v3_usage_B20x10_holdout_20261012_r1_opcode.json`, issue
d'une campagne **20 paires × 10 ans du 12/10** sous `probe_loop_ops=1`. Le
lecteur ne prend que le bras de référence (20 parties indépendantes), sans
doubler les observations avec les variantes. `LOOP_OPS post=sleep_left`
comptabilise les opcodes disponibles au moment de `Sleep(1)` et abandonnés
par le tick ; les agrégats annuels sont émis l'année suivante.

## Budget laissé au Sleep(1)

| Année close | Parties | Sleep moyen (M opcodes/partie) | Part du budget journalisé | Appels Sleep/partie | Blocs V308 à 430 ops (plafond théorique) | Cartes 256² équivalentes |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | 20 | 3,87 | 5,74 % | 715 | 9 006 | 8,79 |
| 1971 | 20 | 4,24 | 6,32 % | 741 | 9 869 | 9,64 |
| 1972 | 20 | 2,09 | 3,04 % | 339 | 4 856 | 4,74 |
| 1973 | 20 | 0,85 | 1,27 % | 130 | 1 979 | 1,93 |
| 1974 | 20 | 1,25 | 1,85 % | 212 | 2 909 | 2,84 |
| 1975 | 20 | 1,60 | 2,38 % | 280 | 3 713 | 3,63 |
| 1976 | 20 | 1,37 | 1,95 % | 247 | 3 193 | 3,12 |
| 1977 | 20 | 1,24 | 1,90 % | 216 | 2 872 | 2,80 |
| 1978 | 20 | 1,27 | 1,89 % | 228 | 2 952 | 2,88 |

1979 est **censurée par le flush annuel**, donc absente du tableau. Le
reliquat moyen est de **3,40 M opcodes/an en 1970–1972** contre environ
**1,26 M en 1973–1978**. La conversion est volontairement un **plafond** :
`sleep_left / 430` suppose que l'intégralité du reliquat peut être utilisée
sans surcharge de dispatch, mise à jour, ni allocation de temps aux autres
workers ; elle peut compter plusieurs fois les mêmes 1 024 blocs d'une carte
256². Elle n'indique ni les blocs nouveaux effectivement lisibles, ni la
validité du cache, ni les jours pendant lesquels une boucle est inoccupée.

## Les deux autres mesures demandées ne sont pas identifiables

| Mesure demandée | Résultat hors partie | Pourquoi |
|---|---|---|
| Régénérations C76 dont les clés candidates sont toutes inchangées (`cand_*_same_keys_pct`) | **Indisponible** | Les seuls agrégats `LOOP_OPS` archivés n'ont pas ces champs ; les logs `v299_regen_3x10` requis manquent sur ce PC |
| Opcodes de `pub.select` alors que les clés restent identiques | **Indisponible** | Les spans d'opcodes ne sont pas corrélés à une comparaison des mêmes clés au même instant |
| Jours avec caisse inférieure au coût du plus petit projet sélectionné | **Indisponible** | Ni un coût minimal quotidien du portefeuille ni une synchronisation journalière avec la caisse ne figurent dans l'archive |
| Tours réellement inutiles (révisions inchangées, meilleur projet identique, caisse insuffisante) | **Indisponible** | Il faut observer les trois conditions **simultanément à chaque tour** ; `sleep_left` seul ne les démontre pas |

Le script accepte `--logs <répertoire>` si une archive
`reference_seed*_r0.log[.gz]` munie de `C76_REGEN` est récupérée. Il compte
alors seulement les régénérations ayant tous les pourcentages de clés à
100 % et un `best_same_top1=1` documenté ; les données sans ces champs
restent inconnues et ne sont pas assimilées à des régénérations inchangées.

## Décision de suite

Le budget d'opcodes de `Sleep(1)` est suffisant, **sur le plan arithmétique**,
pour cartographier au moins une carte 256² chaque année de l'échantillon ;
les données disponibles ne disent pas quelle part correspond à une attente
financière. En 1970–1972 le déficit de caisse est une hypothèse plausible à
instrumenter ; après 1973, la documentation V309 signale au contraire une
caisse de 14 à 21 M£ et un vivier sec. Un déclencheur limité à « caisse
insuffisante » serait donc particulièrement mal adapté à cette période.

**Ne pas introduire le comportement V309 sur la seule base de cette archive.**
La sonde passive `v309_idle_probe` de l'étape 1 doit mesurer les tours, leur
coût, le meilleur projet, les révisions et la financabilité au même instant
dans les deux boucles (`main.nut` et `_mainLoopProfiled`), après coordination
avec PO-01c. L'exploitation des blocs demande également la validation du
quinconce V308 et un consommateur de la carte. Aucun nouveau défaut ni porte
économique n'est décidé ici.

## Étape 1 — instrumentation passive V309 (21/10, préparation sans partie)

`v309_idle_probe` a été ajouté, **désactivé aux quatre difficultés** et lu
une seule fois au chargement. Le diagnostic est conditionné par ce flag, et
la ligne mensuelle `V309_IDLE` n'est émise que si `decision_log=1`.
Le comptage est branché au début et à la fin de chaque tour dans les **deux**
boucles, `OpexAI::Start()` et `_mainLoopProfiled()` : la seconde est effectivement
utilisée lorsque `probe_loop_ops` est actif. Aucune tâche ni politique de
sélection, de financement ou de construction n'est modifiée par le code V309.

Un tour est classé « inutile » lorsque, simultanément, les sept révisions C76
des villes, industries, lignes et moteurs n'ont pas changé depuis le tour
précédent, la clé stable du premier projet sélectionné est identique, et le
solde bancaire est inférieur au **plus petit capital de financement** des
projets sélectionnés (`OpexProjectFinanceCapital`). Les compteurs V279
correspondant aux lignes, abandons et à la validité des sites AIR sont aussi
contrôlés, par prudence. Le premier tour ne peut pas être déclaré inutile.
Ce critère détecte une **occasion potentielle d'économiser des opcodes** ; il
ne prouve pas que tous les travaux déjà exécutés dans le tour seraient
supprimables sans retarder un événement ou une tâche asynchrone.

Le tableau `_projects.best` provient du **sélecteur déjà financé** : quand
toutes les alternatives sont refusées pour manque de capital, il est vide.
La sonde lit alors les statistiques existantes `stats.nextProjectCapital`
(plus petit projet rejeté par financement), puis `stats.minCapital` en repli,
seulement si ce dernier dépasse le budget de sélection publié, sans
reconstruire la sélection. Ce prix est marqué `unfunded_snapshot` :
il n'a **pas d'identité de meilleur projet prouvée**, et ne permet donc
pas de classer ces tours comme « inutiles » selon les trois critères.
Si aucune estimation n'est disponible, `cost_source=unknown` et les compteurs
`unknown_cost_loops` le signalent explicitement. Les statistiques et le
prix peuvent être périmés entre deux élections : ce sont des instantanés,
pas des devis actualisés. Le scan de la sélection financée est mis en cache
jusqu'à changement de sélection, de tête, de taille ou de prix publié.
Le filtre `OpexProjectSelectAffordable` garantit déjà que les projets de
`best` passent le budget de sélection (`capitalBudget`, caisse moins réserve).
Par construction, `cash < min_cost` est donc improbable pour `best` non vide,
sauf baisse de caisse postérieure à la sélection. **Un `useless=0` ne démontre
pas l'absence de tours d'attente.** Pour couvrir ce cas sans inventer une
identité de projet rejeté, V309 distingue `stable_unfunded_loops` et
`stable_unfunded_ops` : sélection vide, prix `unfunded_snapshot` inchangé
et révisions inchangées depuis le tour précédent. Ce sont des **proxys de
stabilité du portefeuille**, pas des tours démontrés inutiles : le prix peut
être périmé et les tâches/événements peuvent encore être utiles.

Chaque ligne porte `loops`, `useless`, `useless_ops` (comptage d'opcodes entre
début et fin du tour, sans le calcul final de la sonde), `sleep_ops` (budget
encore disponible au crochet avant `Sleep(1)`), `cash_below` (tours sous le
capital minimal), `cash_below_days` (dates effectivement observées où ce
déficit est présent), `wait_days`, `blocks`, `money`, `min_cost` et
`net_month`, ainsi que `unfunded_cost_loops`, `unknown_cost_loops`,
`stable_unfunded_loops`, `stable_unfunded_ops`, `cost_source` et
`wait_capped`. Les opcodes et jours de trésorerie sont des **mesures
instrumentées, pas des capacités de cartographie garanties**. Le nombre de
blocs théoriques est
`floor((useless_ops + sleep_ops) / 430)` ; à comparer aux **1 024 blocs**
distincts d'une carte 256², sans multiplier indûment le bénéfice par des
relectures déjà faites. Les deux budgets peuvent nécessiter une orchestration
différente et le coût de la sonde doit être audité au banc.

L'attente est calculée à partir du plus petit capital de financement et du
dernier **trimestre comptable clos** publié par l'API NoAI :
`net_month = (income_q1 + expenses_q1)/3`, où les dépenses sont négatives ;
`wait_days = ceil(30 × max(0, min_cost − money) / net_month)` pour
`net_month > 0`. Une attente non calculable est notée **`-1`**, notamment
avant le premier trimestre clos ou lorsque le profit est non positif. Pour
les mois sans projet sélectionné et sans coût historique disponible, la sonde
conserve « inconnu » et ne fabrique pas un délai nul. Le résultat est plafonné
à **36 500 jours (100 ans)**, avec `wait_capped=1` pour distinguer la censure
d'une durée mesurée. Le trimestre est lu une fois par mois, puis
réutilisé par les tours de ce mois. La ligne du mois clos est émise au
premier tour du mois suivant ; l'ultime mois d'une partie peut donc ne pas
être journalisé, et un long blocage sans passage de boucle peut laisser
des mois entièrement non observés.
La durée du tour est désormais calculée à partir de deux points
`OpexOpsMeasureBegin/End` relatifs aux ticks traversés, afin d'éviter le
produit `tick absolu × 10 000` de l'horloge C56 qui pourrait dépasser la
plage d'un entier Squirrel sur les parties longues. Le `sleep_ops` est lu
à la fin de la sonde, au plus près de `Sleep(1)` ; l'appel et les dernières
instructions gardent un coût résiduel non nul.

Le décodeur `sweeps/diag_v309_idle.py --idle-logs <répertoire>` agrège les
mesures **par bras, année et ensemble des graines**, en séparant les
indisponibilités (`wait_days=-1`, champs absents) des vrais zéros. Il présente
les boucles inutiles en pourcentage, leurs opcodes, les opcodes laissés au
`Sleep`, les périodes avec sélection vide stable et leurs opcodes, les dates
de déficit observées, les jours d'attente connus et le nombre de blocs
rapporté à 1 024. Le lecteur dédoublonne une ligne mensuelle répétée ou
présente dans les deux formats `.log` et `.log.gz` d'une même partie.

Validation locale : `python -X utf8 -m unittest sweeps.test_v309_idle -v`
(8 tests réussis), `python -X utf8 sweeps/diag_v309_idle.py --selftest`
(OK) et `git diff --check` (OK). Le lancement plus large
`python -X utf8 -m pytest sweeps -q` est bloqué dans l'environnement Python
Windows de cette session (**module `pytest` absent**). Les 10 tests V147 ont
également réussi avec `PYTHONPATH=sweeps`. Aucun smoke Squirrel,
aucune campagne Docker et aucune mesure économique V309 n'ont été exécutés
par ce worker ; compilation effective et coût d'instrumentation restent à
vérifier avec le prime après intégration V308.

Campagne d'exposition **exécutée et close** (trois graines, dix ans,
duels référence et instrumentation sur même arbre ; ne constitue pas une
porte V102) :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign v309_idle_expo_3x10_20261021 --reference "OpexAI[decision_log=1]" --variant "OpexAI[decision_log=1,v309_idle_probe=1]" --variant-policy-id v309_idle --decision-rule gain_short --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --map-size 8 --repeats 1 --years 10 --seeds 42 7 100 --script-debug --cpus 10 --memory 8g --max-workers 3 --network host
```

## Résultats finaux V309 — exposition 3×10 (21/10/2026)

`results/v309_bench_clean_20261021/results/v309_idle_expo_3x10_20261021.json` :
**6/6 duels `complete` et `game_ok`, 3/3 paires**, `failed_runs=[]`,
`comparison_complete=true`, `metric_coverage_complete=true`, zéro erreur
Squirrel rapportée. Graines **42, 7, 100**, années **1970–1979**, une
répétition ; mêmes paramètres de jeu et adversaire AAAHogEx par bras.
Worktree propre au lancement, Git `0f934dd46c531b1ed4a0f61a159fc5eecedf819b` ;
bundle figé SHA256 `ba54bf95d0e11161f62904394ec7e4dd3987b41ac85eb3c4fe936986b879a68e`,
manifeste SHA256 `a7dea092a0725e9a8b1148de568776cfc1b149dda43cc5254d9290009eb9fc71`.
Logs moteur dans le dossier frère `_engine`, trois références et trois variantes.
Le smoke préalable 1×1 avait terminé **2/2** avec onze `V309_IDLE` et aucune
erreur Squirrel.

Décodage après **JSON final uniquement** :
`python -X utf8 sweeps/diag_v309_idle.py --idle-logs results/v309_bench_clean_20261021/results/v309_idle_expo_3x10_20261021_engine`.
Table du bras `v309_idle` : sommes sur les **trois parties** (ops en millions,
arrondies) ; le pourcentage strict est `useless/loops`, l'attente est la
moyenne des seuls `wait_days ≥ 0` rapportés dans les mois observés.

| Année | Mois/36 | Tours | Strict `useless` | Proxy stable, tours | Proxy stable, Mops | `sleep_ops`, Mops | Jours sous capital | Attente connue, jours | Blocs théoriques / 1 024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1970 | 36 | 3 810 | 0 (0 %) | 3 145 (82,55 %) | 118,04 | 22,86 | 565 | 33,9 | 53 150 / 1 024 |
| 1971 | 36 | 4 426 | 0 (0 %) | 1 812 (40,94 %) | 45,65 | 28,01 | 98 | 1,3 | 65 108 / 1 024 |
| 1972 | 36 | 2 989 | 0 (0 %) | 1 598 (53,46 %) | 43,34 | 17,38 | 66 | 0,2 | 40 411 / 1 024 |
| 1973 | 36 | 1 792 | 1 (0,06 %) | 674 (37,61 %) | 14,69 | 10,96 | 19 | 0,0 | 26 619 / 1 024 |
| 1974 | 34 | 2 044 | 0 (0 %) | 180 (8,81 %) | 9,75 | 11,84 | 4 | 0,0 | 27 518 / 1 024 |
| 1975 | 33 | 2 436 | 0 (0 %) | 0 | 0 | 15,11 | 0 | 0,0 | 35 128 / 1 024 |
| 1976 | 36 | 2 843 | 0 (0 %) | 0 | 0 | 17,28 | 0 | 0,0 | 40 165 / 1 024 |
| 1977 | 36 | 2 661 | 0 (0 %) | 0 | 0 | 16,16 | 0 | 0,0 | 37 570 / 1 024 |
| 1978 | 33 | 2 258 | 0 (0 %) | 0 | 0 | 14,33 | 0 | 0,0 | 33 315 / 1 024 |
| 1979 | 29 | 1 852 | 0 (0 %) | 0 | 0 | 11,67 | 0 | 0,0 | 27 127 / 1 024 |

Au total, **27 111 tours** et **345 mois observés sur 360 possibles** : un seul
tour répond au contrat strict `useless`, alors que **7 409 tours** relèvent du
proxy de stabilité sans projet finançable, pour **231,46 M opcodes exécutés**.
Le reliquat `Sleep` totalise séparément **165,61 M opcodes**. L'essentiel du
proxy se situe de 1970 à 1974, et plus aucun tour de ce type n'est détecté à
partir de 1975 dans ces trois parties.

Le proxy `stable_unfunded` observe un portefeuille financé vide, un devis
publié identique et les mêmes révisions ; il **ne prouve pas qu'une tâche
entière serait évitable**. `best` ne contient que des projets déjà jugés
finançables, d'où un `useless` strict quasi nul. Le prix peut être périmé et
`wait_days` dépend d'un flux comptable trimestriel, sans modélisation de la
prochaine dépense ; zéro observé et inconnu restent distincts dans le JSON du
décodeur. La couverture mensuelle est partielle en 1974, 1975, 1978 et surtout
1979 (flush du mois suivant indisponible en fin de partie et/ou mois non
observés) : aucune interpolation des mois manquants.

**Ne pas additionner** `stable_unfunded_ops` au nombre `blocks` : le proxy
mesure des opcodes déjà dépensés, tandis que `blocks` est calculé sur
`useless_ops + sleep_ops` (sans ces opcodes proxy), puis divisé par 430.
Ces 27 000 à 65 000 blocs annuels cumulés sur trois graines ne sont ni des
blocs de carte effectivement lus ni un gain net ; ils peuvent rebalayer les
mêmes **1 024 blocs distincts** d'une carte 256². Leur réaffectation exigerait
une orchestration, un cache valide et des coûts additionnels mesurés.

Deux biais empêchent de convertir directement ces volumes en rentabilité :
la condition enregistrée `cash < cost` **ignore la réserve de financement**
effective de 5 000 à 25 000 £. Dans le smoke, deux mois affichent ainsi
`wait_days=0` bien que le coût plus la réserve ne soit pas finançable ; les
jours d'attente de capital sont sous-détectés. Et **430 opcodes/bloc** vient
du V307 simplifié : V308 a observé environ **988 opcodes moyens/bloc** pour
`short6` et 1 154–1 161 pour `full6`. La capacité de cartographie affichée
peut donc surestimer d'environ ×2,3 le nombre de lectures `short6` réalisables,
même avant les coûts du cache, des invalidations et de l'ordonnancement.
Avant toute optimisation, mesurer le même instant `OpexAvailableCapital()` /
capital requis, la cause de sélection vide et le coût réel d'une lecture
cacheable.

Comparaison économique terminale **ON − référence** sur le même arbre :

| Graine | `profit_year` réf. | `profit_year` ON | Δ £/an | Δ valeur de compagnie |
|---|---:|---:|---:|---:|
| 42 | 4 589 234 | 4 175 446 | −413 788 | −2 403 048 |
| 7 | 5 550 944 | 5 354 910 | −196 034 | −962 281 |
| 100 | 2 596 485 | 2 592 963 | −3 522 | −934 987 |

**Moyenne Δ `profit_year` −204 448 £/an**, médiane −196 034,
3 pertes/0 gain, écart-type **205 262 £/an**, IC95 bootstrap de moyenne
**[−413 788 ; −3 522]**, Wilcoxon exact bilatéral **p=0,25** (trois paires
seulement). La valeur de compagnie baisse de **7,017 %** en ratio des moyennes,
au-delà de la garde −5 %. Verdict brut du JSON :
`fail_primary_and_value_guard`. Ce **3×10 est une exposition diagnostique**,
pas une porte V102 de qualification ; aucune attribution causale précise à
une ligne de sonde ne découle de trois trajectoires divergentes. L'activation
de la sonde, malgré sa passivité fonctionnelle, consomme des opcodes et peut
décaler les ordonnancements : neutralité économique **non établie**.
Conserver `v309_idle_probe=0` par défaut. Aucun nouveau comportement de
cartographie n'est qualifié à ce stade.
