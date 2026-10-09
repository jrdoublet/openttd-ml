# P0 rail — opportunités réellement bloquées au créneau A* (09/10, prolongement)

## Observation historique analysée avant nouvel instrument

Le bundle observationnel `rail_p0_funnel_obs_5x6_20261009_r1` est 5/5 sain,
mais ses journaux `RAIL_BLOCKER` n'enregistrent pas le score courant du projet
refusé. `PORTFOLIO_RANK` intervient à une génération antérieure, donc son score
ne représente pas nécessairement le classement au jour du refus. L'analyseur
HOST `sweeps/analyse_rail_p0_blocked_choices.py` rapproche strictement
`RAIL_AUDIT stage=early reason=search_in_progress` immédiatement suivi de
`RAIL_BLOCKER` (date, kind, src, dst), sans prétendre qu'une occurrence est un
projet nouveau. Il conserve les non-appariés et les scores absents. La présence
ultérieure d'une `RAIL_BUILD` de même OD/cargo reste *one_possible_pair_match*,
jamais preuve absolue d'identité ou de rentabilité.

Sur les cinq parties existantes, **1973** contient **85 visites bloquées**, dont
**64 par upgrade** et **21 par primaire**, sur **34 identités OD+cargo+graine** ;
les graines concernées par des refus réellement logués sont 42, 999, 515222.
Le primaire seed100 est encore actif mais aucune tentative de refus n'est
loguée en 1973 ; seed512 n'a pas de recherche A* active cette année. Ne pas
confondre « état A* occupé » et « projet concurrent présenté ».
Sur toute la série 1972–1975, les **2 431 visites** incluent 10 liaisons
audit→blocker ambiguës/absentes ; les nombres par année sont : 165, 85,
715 et 1 466. Le nombre d'événements de refus ne donne ni l'opportunité
finançable exacte ni le bénéfice d'un second état A*.

## Protocole annoncé avant la nouvelle mesure

L'ajout à la **sonde existante** `rail_failure_audit` reste strictement sous
son défaut **0** aux quatre difficultés. Dans
`OpexRailSearchBlockerAudit`, le projet réel `project` et son rang `i` sont
passés depuis les deux gardes `search_in_progress` sans modifier l'exécution.
Seuls ses champs **déjà calculés** sont lus : `fundScore`, `profitAnnual`,
`budgetCapital`, `rank` et `payload.dstTown/isChain` pour distinguer fret
industry→industry, industry→town ou chaîne. Aucun nouveau calcul économique,
balayage du catalogue, A*, devis, API de cash ou tri. Ces valeurs n'indiquent
**pas** un solde de caisse au moment de la pose ; `budgetCapital` est un indice
de capital demandé, qui peut différer de `OpexProjectFinanceCapital`.

Validation pré-enregistrée : contrats HOST du parseur, smoke apparié
`rail_failure_audit=0,probe_rail_preastar=0` vs
`rail_failure_audit=1,probe_rail_preastar=1`, graine42 × 1 an ; puis, si
sain, collecte observationnelle ON **5 graines 42/100/999/512/515222 ×
6 ans** (1970–1975), profil Windows Docker Desktop `--cpus 10 --memory 8g
--max-workers 5`, `--script-debug --line-telemetry`. Le code est figé dans
un nouveau bundle et l'analyse sera rejointe seulement aux logs du **même**
banc. Une campagne à la fois. Les différences de trajectoire entre ON/OFF
sont de l'intrusion instrumentale, pas un gain de politique.

Décision attendue : si des projets en attente réellement classés, à profit
prévu positif, peuvent devenir des lignes construites avec profit observé
favorable, une expérience d'ordonnancement coopératif à deux **états A***
sera seulement alors candidate. V89 consomme déjà le budget d'opcodes libre ;
deux workers naïfs ne créent pas de nouveaux opcodes et pourraient retarder
des `OK` historiques. Un vrai test devra mesurer les réussites retardées,
la caisse des investissements alternatifs et l'effet net avec A/B V102.

## Résultat du second banc et provenance

La campagne `rail_p0_blocked_score_5x6_20261009_r1` est **terminée** : cinq
parties sur cinq `complete`, `game_ok=true`, horizon 1975-12-01 atteint par
OpexAI et AAAHogEx, aucune `failed_runs`. Graines 42/100/999/512/515222,
1970–1975, une répétition. Bundle SHA256
`293d8e65b4a3036c3c5fff0fde437f4d889e80c8e6ed1eee79420732c44c518d`,
manifeste SHA256
`c4fda4ed4fc54663899cbe2d005dba4282301786d61434cc11392a8866f88ea9`.
Bras OpexAI `rail_failure_audit=1,probe_rail_preastar=1`, tous les autres
réglages au défaut du bundle. Le smoke apparié 42×1, **2/2 sain**, a décalé
`profit_year` ON−OFF de **−21 667 £/an** et le ratio de valeur de **−2,012 %**.
L'observation du second banc **n'est donc pas une mesure du défaut de
production**, ni un A/B de scheduler. Ne pas amalgamer ses effectifs avec le
premier bundle `d85053dd…`, plus richement instrumenté.

L'analyseur HOST
`sweeps/analyse_rail_p0_blocked_choices.py` produit le JSON d'événements et
le CSV par graine/année/cargo/destination. Une seconde jointure
`sweeps/rapport_rail_p0_blocked_score.py` utilise
`analyse_rail_preastar.py` pour retrouver, dans **le même log**, le RID A*
occupant sur un intervalle START→END, avec mode et OD exactes (ou mode
upgrade sans OD), puis les RID START et BUILD ultérieurs de **même**
kind/cargo/src/dst. Ces derniers sont des rapprochements **de paire**, pas
des identifiants persistants de projet. Le nouveau banc a `decision_log=0` :
`PORTFOLIO_RANK`, `PROJECT_CHOSEN` et `RAIL_BUILD` n'y sont pas observables ;
une absence de `RAIL_BUILD` ne démontre aucune absence de ligne construite.
La jointure RID avec `RAIL_PREASTAR_BUILD` est la preuve disponible.

| Année | Tous refus A* (pax + fret) | Fret apparié | Fret auto-revisite | Visites fret concurrentes | Paires fret concurrentes (graine+année+cargo+OD) | Score initial positif |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1972 | 554 | 117 | 10 | 107 | 17 | 17 |
| 1973 | 319 | 198 | 23 | 175 | 21 | 21 |
| 1974 | 2 788 | 232 | 47 | 185 | 19 | 17 |
| 1975 | 3 966 | 76 | 25 | 51 | 26 | 26 |
| **Total** | **7 627** | **623** | **105** | **518** | **83 paires-années** | **81 paires-années** |

Les 7 627 refus incluent **6 981 pax** et **23 non appariables** ;
`RAIL_AUDIT` adjacent et cargo présent couvrent **623/623 visites fret**.
Les 83 paires-années correspondent à **64 identités de paire uniques sur
1972–1975** (graine/cargo/src/dst, sans année), et chacune retrouve un seul
RID occupant. Aucune visite ci-dessus n'est une ligne construite ni un profit.
Sur les 83 paires-années, seulement **5** ont un rang initial 0 parmi les
*paires concurrentes* ; les premières places sont souvent des auto-revisites.
La répartition du fret est par cargo : GOOD→town (seed100 1972 ; seed512
1974), COAL→industry, WOOD→industry, IORE→industry, GRAI→industry/town.
**Aucun événement `chain` n'est exposé dans cette collecte**, ce qui ne
prouve pas une absence de candidats de chaîne dans le pipeline entier.

## Cas de causalité locale et contre-exemples

**Seed515222, 1973-08-15**, moteur
`results/rail_p0_blocked_score_5x6_20261009_r1_engine/rail_p0_blocked_score_obs_seed515222_r0.log:12459-12506` :
`RAIL_POOL_AUDIT phase=reselect` dénombre **14 alternatives fret / 14
affordable / 14 selected**, avec 2 AIR et 17 fleet dans le classement ;
`head_mode=rail`, `head_kind=freight`. L'A* primaire de COAL
58012→39838, **RID 23756_6**, démarré le **1973-07-08**, monopolise le
créneau. Le 15/08, les rangs 1–4 (paires COAL différentes) sont réellement
présentés au dispatch puis refusés `search_in_progress` : scores
**182,30 / 182,03 / 181,55 / 160,31**, profits prévus
**40 782 / 40 722 / 40 614 / 35 862 £/an**, capital indicatif
**41 655–44 567 £**. Rang 0 est la paire déjà en recherche : score 208,10,
donc c'est une **auto-revisite**. Le RID occupant finit `OK` 1973-10-28,
chantier `OK` 1973-11-03 : une solution N=2 qui l'interromprait
définitivement pourrait sacrifier un vrai succès.

Une addition de flotte **réelle** `[FLEET_PROJECT] line=34 added=1` figure
avant les traces datées du 16 août ; un `C75_BYPASS mode=air phase=consumed`
y porte capital 101 364 £, cash 2 271 659 £ et disponible 2 246 178 £.
**`C75_BYPASS consumed` est une autorisation, pas une construction AIR** ;
ne jamais l'ajouter aux chantiers posés. L'achat de flotte prouve qu'un
autre mode a avancé pendant le monopole du créneau ; la caisse était
abondante à cette date proche. Ces événements ne
prouvent pas que le cash ni la constructibilité des quatre paires auraient
été identiques dans un monde N=2 ; le capital indicatif reste distinct du
devis de financement live et du coût final.

**Seed42, 1973-07-06/07**, même phénomène et contre-épreuve de pose
(`..._engine/rail_p0_blocked_score_obs_seed42_r0.log:11345-11363`) :
le portefeuille indique **6 fret affordable, 5 retenus**, devant
39 AIR et 20 flotte, tête rail/fret. Le WOOD 40752→56143, rang 1,
score **209,78**, profit prévu **35 607 £/an**, capital indicatif
**45 550 £**, est refusé derrière le WOOD 40752→50791, rang 0 et
déjà en recherche (auto-revisite). Entre deux refus fret sur **le même
jour de jeu**, `[FLEET_PROJECT] line=32 added=1` confirme l'achat
d'un avion. Le RID occupant **23140_7** finit A* `OK` le 1974-06-07,
mais sa pose échoue `STNFAIL` le 12/06/1974 ; une simple accélération
de A* n'aurait pas rendu cette ligne rentable. Seed515222 démontre au
contraire un `OK` suivi d'un chantier bâti, donc le scheduler doit
préserver aussi les succès coûteux à obtenir.

Les reprises de paires attestées par **nouveau RID et `BUILD built`** ne
doivent pas être éliminées par une mémoire de refus : seed42 COAL
9815→13978 refusée pendant upgrade le **1972-07-14**, puis bâtie après
`RID 17574_6` ; seed42 WOOD 21920→37550 refusée en 1973 et 1974 pendant
`RID 23140_7` (recherche occupant 1973-06-04→1974-06-07, `OK`), puis
`RID 32870_9` construit ; seed42 IORE 8935→28395 bloquée le
1975-05-31, puis `RID 39442_10` construit. Ce sont **trois OD distinctes**
(quatre paires-années, car WOOD chevauche deux années), sans lien strict
du profit réalisé ni du projet économique d'origine. Les **79 autres
paires-années** n'ont aucun `BUILD built` ultérieur avec la même paire
dans cet horizon ; cela ne veut pas dire qu'elles étaient infaisables.

Sur l'ensemble du second banc : **64 RID**, dont **58 `OK`, 3 `ABND`
au plafond, 3 censurés** ; 15 `OK` sont du *stock* et 10 des *upgrades*.
Les `OK` en A* ne garantissent ni pose ni service, et les recherches
censurées ne sont pas des échecs. Les 3 `ABND` ne suffisent pas pour
prédire l'issue des demandes concurrentes non lancées.

## Verdict causal et décision

Le **verrou local d'admission dispatch→démarrage A*** est prouvé par
`task_rail.nut:234-259` et par les projets fret distincts effectivement
classés/refusés dans le même jour et la même partie. La perte d'accès
simultané est réelle : H2 est **confirmée comme mécanisme de blocage**, y
compris en présence de trésorerie abondante. Cette preuve ne démontre pas
que H2 explique à elle seule l'écart économique à AAAHogEx, ni la
rentabilité d'une deuxième ligne. H1 (élimination en amont) et H3
(rendement des trains réalisés) restent des contributions possibles.

**Scheduler A* multi-état N=2 : techniquement *feasible*, bénéfice économique
*non identifié*.** Chaque `OpexCreateSegmentedSearch` possède ses propres
tables, états et pathfinders. Le pilote est néanmoins un singleton
`_railSearch` et `_activeWorker`, couplé à la reprise, au dispatch, à la
consommation de chantiers et au Save/Load (`task_rail.nut`,
`task_projects.nut`, `scheduler.nut`, `orchestrator.nut`, `persist.nut`).
Une tranche V89 utilise déjà le slack d'opcodes : le partager à deux
retarde potentiellement les vrais `OK`. L'expérience minimale exige un
switch de contexte **transitoire** de deux A* primaires seulement, un
unique worker actif et un chantier consommé à la fois, budget global
d'opcodes inchangé, revalidation cash/site avant pose, annulation correcte
au Load et journaux RID/OK sacrifiés. Garder upgrade et stock au legacy
dans un premier prototype, tout en mesurant séparément leur blocage.
Ne pas dupliquer les workers, doubler V89, sérialiser les pathfinders ou
introduire de priorité/plafond arbitraires.

**Décision actuelle : ne pas implémenter/adopter N=2 sur cette observation
seule.** Un A/B comportemental n'a pas encore de garantie sur les succès
perdus, les opcodes et le capital réellement converti en profit ; mesurer
ce point dans un prototype isolé avec garde des RID `OK` avant toute porte
V102 (A 40×3 puis B 20×10 si A passe). Conserver tous les défauts à 0,
aucun commit ni push. Une expérience ne sera qualifiée que sur son
bundle commun OFF/ON et ses résultats OpexAI propres, pas sur les scores
ou les profits théoriques des projets refusés.

Reproduction :

```powershell
python -X utf8 sweeps/analyse_rail_p0_blocked_choices.py results/rail_p0_blocked_score_5x6_20261009_r1_engine --out results/rail_p0_blocked_score_5x6_20261009.analysis.json --summary-csv results/rail_p0_blocked_score_5x6_20261009.summary.csv
python -X utf8 sweeps/rapport_rail_p0_blocked_score.py results/rail_p0_blocked_score_5x6_20261009.analysis.json results/rail_p0_blocked_score_5x6_20261009_r1_engine --out results/rail_p0_blocked_score_5x6_20261009.rid_cohorts.json
python -X utf8 -m unittest discover -s sweeps -p test_analyse_rail_p0_blocked_choices.py
python -X utf8 -m unittest discover -s sweeps -p test_rapport_rail_p0_blocked_score.py
```
