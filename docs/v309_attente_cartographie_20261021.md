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

Campagne d'exposition **préparée, non lancée** (trois graines, dix ans,
duels référence et instrumentation sur même arbre ; ne constitue pas une
porte V102) :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign v309_idle_expo_3x10_20261021 --reference "OpexAI[decision_log=1]" --variant "OpexAI[decision_log=1,v309_idle_probe=1]" --variant-policy-id v309_idle --decision-rule gain_short --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --map-size 8 --repeats 1 --years 10 --seeds 42 7 100 --script-debug --cpus 10 --memory 8g --max-workers 3 --network host
```

**Table empirique 1970–1979 : en attente du 3×10 et des journaux V309_IDLE.**
Les résultats déjà mesurés dans l'étape 0 restent les seules valeurs
quantifiées disponibles ; aucune extrapolation de tours inutiles ou de jours
finançables n'est permise. Une décision de comportement devra séparer la
période 1970–1972, où l'attente de trésorerie reste plausible, de la période
postérieure à 1973, où le problème constaté concerne surtout un vivier ou
une sélection insuffisante. V308 doit être validé et avoir un consommateur
concret avant toute modification comportementale.
