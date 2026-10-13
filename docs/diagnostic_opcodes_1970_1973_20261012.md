# OpexAI contre AAAHogEx : autopsie opcode des quatre premières années (1970–1973)

**Diagnostic du 12 octobre 2026, non expérimentation d'adoption.** Unité des
tableaux : **millions d'opcodes par partie** (moyenne de cinq graines), sauf
mention contraire. Aucune modification de politique ni aucun gain supposé.
Les données chiffrées du profil détaillé sont dans
`evidence/review/opcode_early4_20261012/breakdown.json` ; les traces
originales et manifestes sont archivés dans le même dossier.

## 1. Périmètre, comparabilité et santé

- **Production témoin sans sondes**, C66.3 gelé à `f6139d8` :
  `diag_opcodes_1970_1973_default_5seeds_20261012`, graines
  **42, 100, 999, 1234, 5678** sur **quatre ans**, OpexAI et AAAHogEx-115
  dans une même partie. **5/5 parties et deux compagnies complètes**.
- **Diagnostic instrumenté distinct**, mêmes graines et adversaire,
  `probe_loop_ops=1, probe_scheduler=1, catalog_cost_probe=1`,
  `--script-debug`, **cinq ans simulés pour clôturer les quatre années** :
  `diag_opcodes_1970_1973_detail_worker_5x5_20261012`. **5/5 parties
  complètes**, bundle SHA256
  `efa38f1ae72d035237e046bc6ea0a23f72ce36ccfa184c5b945059ea5f3da05d`.
  Image `openttd-lab:latest`, 10 CPU au plus, 5 workers, 8 Go, campagnes
  strictement successives.
- Les sondes modifient parfois la trajectoire ; **économie = témoin sans
  sonde**, **attribution opcode = campagne diagnostique**, ne jamais fusionner
  leurs entreprises une à une comme une unique partie. Un essai intermédiaire
  avec la première copie de `_mainLoopProfiled` a révélé l'oubli de
  `_refreshSaveProjection` (sur les sauvegardes de >=64 lignes) ; la
  présente campagne repose sur une version corrigée. Le code normal reste
  inchangé quand `probe_loop_ops=0`. Smoke Docker 1/1 sain ; tests
  de l'analyseur 2/2 verts.
- **Important :** tout ratio d'économie de ces cinq graines est descriptif,
  non une inférence fiable sur les autres graines. Les 40 graines
  historiques du catalogue CD ont un autre gel de code et des compteurs
  `LOOP_OPS` clôturés seulement jusqu'en 1972 ; elles confortent l'ordre de
  grandeur, pas cette série de quatre ans.

### Économie observée sur les quatre années, témoin non sondé

| Année | Profit Opex (£/an) | Profit AAA (£/an) | Opex − AAA (£/an) | Véhicules Opex / AAA | Gares Opex / AAA |
|---|---:|---:|---:|---:|---:|
| 1970 | 343 917 | 343 454 | +463 | 10 / 14 | 12 / 14 |
| 1971 | 1 250 957 | 1 378 646 | −127 689 | 37 / 66 | 33 / 54 |
| 1972 | 1 769 957 | 2 031 668 | −261 711 | 60 / 154 | 45 / 109 |
| 1973 | 1 783 129 | 2 579 341 | **−796 212** | 88 / 207 | 50 / 147 |

Fin 1973 : valeur de compagnie OpexAI **4 944 153 £** contre
**4 464 511 £** pour AAAHogEx ; profit supérieur sur **0/5 graines**,
valeur supérieure sur **3/5**. Les profits divergent après 1971 avec
un parc beaucoup plus restreint chez OpexAI. La coexistence d'une valeur
élevée et de peu de matériel **suggère une contrainte de transformation des
occasions de croissance** ; elle ne localise pas encore la causalité.

## 2. Comptabilité globale : budget, exécuté, abandonné

Une instruction ne peut employer que le reliquat du tick d'IA courant,
à raison de 10 000 opcodes maximum. `OpexOpsMeasureEnd` chiffre une
fenêtre traversant des ticks par tranches de 10 000 : **une attente de commande
ou un yield peut être imputé comme une tranche complète sans 10 000
instructions Squirrel effectivement exécutées**. C'est une mesure de
budget temporel, pas un profileur CPU matériel.

Les **seuls postes disjoints `LOOP_OPS`** sont ici
`events`, `save_projection`, `station_flux`, `c117_sample/skip`,
`orchestrator`, `catalog_continuation/check`, `rail_throughput` et
`c67_hook`. Les `tg_*` sont des mesures imbriquées, parfois de simples
**comptages**, et ne doivent pas être additionnées. `AIR_LIGHT`,
`SELECTION_LIGHT`, `PROJECTS_COST`, `C39_PASS_CLOCK` et `SCHED_IDLE`
recoupent les postes de la boucle.

| Année | Budget 10k × ticks | Imputé aux postes disjoints | Reliquat `sleep_left` | Non réconcilié* | % du budget perdu au Sleep |
|---|---:|---:|---:|---:|---:|
| 1970 | 67,710 M | 62,702 M | 4,626 M | 0,383 M | 6,83 % |
| 1971 | 67,356 M | 62,741 M | 4,250 M | 0,365 M | 6,31 % |
| 1972 | 68,894 M | 66,652 M | 2,065 M | 0,177 M | 3,00 % |
| 1973 | 66,400 M | 65,079 M | 1,209 M | 0,111 M | 1,82 % |
| **Total 1970–1973** | **270,360 M** | **257,174 M** | **12,150 M** | **1,036 M** | **4,49 %** |

\* Le « non réconcilié » est le faible résidu de mesure, hooks,
formatage, sommeil et synchronisation du compteur ; **ce n'est pas une
réserve disponible**. Le reliquat est relevé avant quelques écritures de
sonde finales et constitue donc une borne observatoire légèrement optimiste
des opcodes jetés exactement au `Sleep(1)`.

### Où va le budget global (postes de première profondeur, M)

| Poste | 1970 | 1971 | 1972 | 1973 |
|---|---:|---:|---:|---:|
| `catalog_continuation` | 46,121 | 44,370 | 13,857 | 6,936 |
| `orchestrator` | 15,965 | 16,763 | 50,365 | 55,446 |
| Échantillonnage C117 | 0,431 | 1,497 | 2,359 | 2,629 |
| Débit rail supplémentaire V89 | 0,098 | 0,032 | 0,019 | 0,015 |
| Autres petits postes (événements, vérifications, Save) | 0,087 | 0,109 | 0,052 | 0,053 |

**Ne pas assimiler `catalog_continuation` au seul calcul du catalogue :**
dans `probes.nut:2638-2665`, la continuation C121 peut réappeler
`_runOrchestratorTick()` et exécuter d'autres tâches dans le **même
tick**. À partir de 1972, le registre principal de l'ordonnanceur devient
prépondérant. Les chiffres ci-dessous lèvent partiellement cette ambiguïté.

## 3. Détail par tâche et worker : C39, sous-postes

Les lectures C39 sont classées par tâche, déduisent la tranche A* mesurée
pour éviter son attribution *dans la même tâche*, et rebasculent les
rapports annuels à l'exercice écoulé. Elles restent un **autre découpage
imbriqué**, pas une table supplémentaire à ajouter à la précédente.

| Sous-poste (M opcodes) | 1970 | 1971 | 1972 | 1973 |
|---|---:|---:|---:|---:|
| `projects` : portefeuille/exécution | **9,425** | **18,261** | **23,416** | **29,730** |
| `air_fleet` | 1,594 | 2,675 | **10,000** | **10,940** |
| Recherche A* rail (tranches mesurées C39) | 2,974 | 0,611 | 8,981 | 7,766 |
| `catalog` dans la file (hors reprises same-tick) | 8,418 | 5,996 | 1,437 | 0,809 |
| Régénération C77 réactive `regen` | ~0 | 6,760 | 4,493 | 3,200 |
| Worker `regen_candidates` | 4,970 | ~0 | ~0 | 0,435 |
| Worker `rail_stock` observé | 2,988 | ~0 | ~0 | ~0 |
| `report` annuel | 0,347 | 0,964 | 2,196 | 2,860 |
| `expand` | 1,127 | 1,541 | 2,340 | 0,535 |
| C77 `c77_build` | 0,447 | 1,976 | 0,236 | 0,027 |
| C77 `c77_subsidy` | 0,108 | 0,928 | 1,177 | 0,438 |

En 1972–1973, les deux lignes **`projects` et `air_fleet`**
atteignent ensemble environ **33,4 puis 40,7 M opcodes par an** dans
ce registre : c'est la priorité naturelle du prochain audit de coût
et de rendement. **Anomalie C80 expliquée par lecture code et traces :**
`_activeWorker.kind == "rail_stock"` existe bien malgré
`c80_rail_stock_gate=0` et `c80_rail_stock_worker=0`, car
`c121_air_first_year_rail_prep=1` appelle le moteur de recherche stock
pour la préparation rail (`rail_prep_c121.nut:260-288`,
`task_rail.nut:2002-2007`). Le même type interne sert deux origines.
En 1970 `worker|rail_stock` **2,988 M** et `rail_astar_slice`
**2,974 M** se chevauchent presque intégralement : **ne pas sommer
ces deux postes**. La distinction analytique devrait inclure
`isC121RailPrep` sans changement comportemental.

### Ce qui a été sélectionné mais ne produit pas de résultat immédiat

Classification `SCHED_IDLE w=0` (non-productive selon les critères de
la sonde ; **pas nécessairement inutile ni supprimable en bloc**) :

| Motif (M opcodes, inclus dans la table précédente) | 1970 | 1971 | 1972 | 1973 |
|---|---:|---:|---:|---:|
| `air_fleet_no_work` | 1,594 | 2,675 | **9,505** | **≈10,9** |
| `catalog_c78_partial_pending` | 4,895 | 3,106 | 0,532 | 0,056 |
| `catalog_c78_slice_incomplete` | 3,102 | 2,688 | 1,237 | ≈0,75 |
| `projects_empty` | 2,202 | 1,770 | 0,772 | ≈0,29 |
| `expand_no_work` | 1,121 | 1,541 | 2,301 | ≈0,54 |
| `projects_examined_no_effect` | 0,375 | 1,171 | 0,372 | ≈0,21 |

En **1973**, `air_fleet_no_work` à lui seul représente environ
**10,9 M/an**, sur **≈45 sélections par partie**. Une nouvelle
attribution des événements `SELECTION_LIGHT` au dispatch montre qu'environ
**5,965 M (54,8 %) de cette fenêtre correspondent à une resélection
du portefeuille**, souvent sans achat immédiat : le registre
`SCHED_IDLE` classe incorrectement comme « no_work » une injection qui
modifie le portefeuille en place, puisque l'identité de la table demeure
inchangée (`scheduler_tasks.nut:941-963`, `projects_update.nut:5-42`,
`ledgers.nut:718-725`). Les chiffres ne sont pas des opcodes
éliminables : préserver sélection et ordre des opportunités de flotte.
Voir [l'autopsie appel par appel](diagnostic_projects_causal_20261012.md)
et `evidence/review/opcode_early4_20261012/air_fleet_reselect_calls.json`.
Attention :
les continuations de catalogue non terminées sont des travaux
véritables de scan et de publication, **pas des tours jetés**. Toute
optimisation des cycles `air_fleet` doit mesurer ce qui a été
vérifié et si cela change l'évolution de flotte avant A/B ; les anciennes
optimisations AIR de cadence rejetées ne sont pas autorisées à renaître
sans mécanisme distinct.

## 4. Le détail du catalogue et du portefeuille

Sous-sondes `AIR_LIGHT` (M opcodes, incluses dans les postes précédents) :

| Phase AIR | 1970 | 1971 | 1972 | 1973 |
|---|---:|---:|---:|---:|
| **Catalogue AIR mesuré `total`** | **13,741** | **11,970** | **8,620** | **5,975** |
| Paires neuves `new_pairs` | 9,285 | 1,993 | 0,912 | 0,466 |
| Sites `sites` | 2,164 | 0,067 | 0,324 | 0,254 |
| Hubs → sites `hub_site` | 1,144 | 4,079 | 2,365 | 1,445 |
| Hubs → hubs `hub_hub` | 0,005 | 1,439 | 2,068 | 2,205 |
| Préparation `prepare` | 0,515 | 1,847 | 1,784 | 0,911 |
| Découverte `hub_discover` | 0,185 | 0,481 | 0,247 | 0,174 |

Les sept phases internes `AIR_LIGHT` identifiées se suivent dans
`air_planning.nut` mais ne sont **pas exhaustives** : leurs sommes
restent inférieures au total de **0,422 / 2,062 / 0,913 / 0,506 M**
en 1970–1973. En 1973, `hub_site` + `hub_hub` représentent **3,651 M**
sur 5,975 M mesurés, soit **61,1 %**. Ce résidu inclut wrappers et
autres opérations non attribuées et ne mesure aucun travail perdu.
Le catalogue AIR dépense surtout dans les **paires neuves la première
année**, puis dans les **combinaisons avec hubs**. Mais sa part baisse
à environ **6 M en 1973**, loin derrière `projects` et
`air_fleet`. Le découpage CD00–CD07 reste à continuer dans le prochain
cycle ; ces mesures ne justifient ni V142 ni V143.

Autres postes imbriqués, sans addition possible entre familles :

| Poste (M opcodes) | 1970 | 1971 | 1972 | 1973 |
|---|---:|---:|---:|---:|
| `PROJECTS_COST.regen.incremental` | 5,043 | 10,327 | **17,123** | **14,502** |
| `PROJECTS_COST.build_ops` | 2,633 | 8,972 | 5,578 | 10,066 |
| `SELECTION_LIGHT.total` | **15,343** | **11,525** | **15,855** | **13,205** |
| Dont resélection `reselect` | 14,680 | 10,284 | 8,880 | 7,135 |
| Dont sélection incrémentale | 0,657 | 1,240 | 6,519 | 5,377 |

`CATALOG_COST_SLICE` relève également environ **9,87 / 11,77 /
3,39 / 1,83 M** de `slice_ops` annuels, déjà compris dans les
ensembles ci-dessus. Les différents profils `PROJECTS_COST` et
`SELECTION_LIGHT` peuvent recouvrir une même régénération ou
resélection : il serait erroné de les additionner.

## 5. Le vrai budget « perdu » et le plafond disponible pour les workers

Définir, pour la boucle *i*, `L_i = GetOpsTillSuspend()`
juste **avant** `Sleep(1)`. La perte brute observée vaut
`P = somme(L_i)` : **12,150 M sur quatre ans**, et diminue
de **4,626 M (1970)** à **1,209 M (1973)**. Elle n'est pas
le budget pris par les tâches inutiles : celles-ci l'ont déjà
**consommé**.

Sonde opportunité : compter le **nombre de boucles** et
`L_i`, puis simuler le patron conservateur C67 (`L_i >= 4000`,
réserve de 3000 opcodes). Pour chaque boucle :
`cap_i = (L_i >= 4000) ? (L_i - 3000) : 0`.
Il s'agit **d'un plafond arithmétique non réalisé** ; aucun worker
n'a été lancé grâce à lui dans cette campagne.

| Situation observée au Sleep | Boucles sur 4 ans (moy./graine) | Reliquat jeté, M | Plafond avec réserve 3k, M |
|---|---:|---:|---:|
| Aucun worker ni recherche rail en attente | 1 711 | **8,797** | **4,325** |
| Worker `regen_candidates` actif | 248 | 1,647 | 0,946 |
| Worker `rail_stock` actif | 43 | 0,228 | 0,114 |
| Recherche A* rail suspendue, sans worker actif | 288 | 1,479 | 0,708 |
| **Total** | **2 290** | **12,150** | **6,093** |

Les **4,325 M de plafond sans worker en attente** ne sont pas
immédiatement attribuables aux workers actuels : il faudrait d'abord
un travail réellement prêt, sûr et ordonnancé. Les trois autres
cas totalisent **1,768 M** d'opcodes de plafond sur
quatre ans, **0,65 % du budget global**, et sont eux-mêmes une
**borne haute conditionnelle**. Ainsi :

1. **12,150 M** : borne haute brute des opcodes volontairement abandonnés
   (4,49 % du budget, sans réserve ni condition).
2. **6,093 M** : borne haute du budget compatible avec le test
   simplifié 4k/3k, **même sans worker prêt** (2,25 %).
3. **1,768 M** : plafond 4k/3k avec un worker ou une recherche A* déjà
   en attente (0,65 %). Les workers actuels ne savent pas tous utiliser
   cette fraction sans changer de tick ou de décision.
4. **0 M récupérés et validés expérimentalement** : aucun nouveau
   micro-worker n'a été exécuté. Le chiffre exact de capacité réellement
   récupérable exige une expérience passive d'**admissibilité** puis
   une expérience d'exécution sous garde.

Variation entre les cinq graines, cumul 1970–1973 :

| Graine | Reliquat jeté, M | Plafond 4k/3k, M | Dont worker/recherche déjà en attente, M |
|---|---:|---:|---:|
| 42 | 15,257 | 7,166 | 0,752 |
| 100 | 14,133 | 7,127 | 2,508 |
| 999 | 10,337 | 5,414 | 1,910 |
| 1234 | 9,447 | 5,027 | 2,243 |
| 5678 | 11,578 | 5,730 | 1,428 |

La présence d'un worker ne prouve **pas** qu'il puisse progresser :
un `rail_stock` peut franchir un tick ou attendre une commande ;
`regen_candidates` peut avoir des étapes synchrones ; `rail_search`
peut ignorer le budget transmis. Un micro-worker sûr doit démontrer
qu'il reste dans le même tick, conserve une réserve et n'évince pas
publication, construction, événement ou continuation prioritaire.

## 6. Comparaison des opcodes avec AAAHogEx : ce qui est observé et ce qui manque

AAAHogEx-115 fournit certains `PerformanceCounter` :
`CheckBuildVehicle` **0,824 / 10,974 / 14,266 / 6,487 M**
pour 1970–1973 dans ce profil, et
`CheckRenewal` **0,012 / 0,174 / 0,428 / 0,649 M**.
Ce sont les **moyennes des postes explicitement imprimés**, non un
total par IA. D'autres mesures (`CloneVehicle`, `BuildVehicle`)
sont **imbriquées** dans les premières ; des périodes et phases
entières n'ont aucun compteur. L'IA utilise également des `Sleep`
explicites. **Aucune preuve actuelle ne permet de comparer les
270,360 M de budget Opex avec un total réellement consommé par
AAAHogEx, ni leurs reliquats perdus**.

Un comparatif homogène exigera soit un compteur moteur par AI,
soit une **copie d'AAAHogEx strictement instrumentée et gelée**
qui logue des postes exclusifs, les changements de tick, les waits
et les reliquats `Sleep`, en contrôlant sa perturbation économique.
Ne pas présenter les `PerformanceCounter` existants comme une
comptabilité totale.

## 7. Priorités d'investigation, sans modification comportementale acquise

1. **`projects`, la première dépense tardive.** 9,425 → 29,730
   M/an en quatre années ; la première autopsie mesure des passages
   plus longs, non plus nombreux, et distingue 14,502 M de régénération
   post-build, 10,066 M de construction/attente, 2,802 M de flotte.
   Poursuivre sur scans, coût A*, appels de sélection,
   régénérations, instructions VM réellement exécutées contre
   ticks d'attente, et nombre de projets effectivement bâtis.
   La forte dépense d'`air_fleet` en parallèle peut concurrencer le
   portefeuille en 1972–1973.
2. **`air_fleet_no_work`, resélection masquée.**
   ~10,9 M/an en 1973 dont ~5,965 M de resélections attribuées :
   caractériser les 45 passages annuels, destinations, cooldowns,
   états candidats et achats, en mesurant les décisions réellement
   changées par `OpexInjectFleetProjects`. Reprendre
   **les rejets antérieurs** des politiques de cadence plutôt que
   relancer sans nouvelle hypothèse.
3. **`catalog_continuation` de 1970–1971** : 46,121 et
   44,370 M. Son nom masque des passages d'ordonnanceur ; séparer
   `dispatchCatalog` et les appels imbriqués à
   `_runOrchestratorTick` à budget constant avant de cibler AIR seul.
4. **Worker d'opportunité à borne sûre.** D'abord *shadow* très léger
   indiquant : type de worker réellement prêt, taille de file,
   budget avant le hook, coût de l'entrée/sortie, réserve, progression
   sans changement de tick et blocage. Ensuite seulement, si un
   gisement existe, worker **micro-résumable**, plafond strict et
   sorties A/B appariées profit annuel, valeur, `LOOP_OPS`,
   cadence de file et émissions de projets. Un micro-worker dont
   le coût de décision est supérieur au reliquat gagnerait zéro.
5. **AAAHogEx complet** : tracer le budget global/les waits de
   l'adversaire dans un clone expérimental, afin de juger enfin
   « par opcode » plutôt que seulement le rendement économique final.

Le rendement d'ensemble de l'IA **ne peut pas gagner les 10–40 M/an de
postes `projects` ou `air_fleet` en les réaffectant** : ces millions
sont déjà exécutés. Les rendre disponibles réclame des changements de
calcul validés indépendamment. Le gisement « gratuit » de fin de tick
se limite aux **1,2–4,6 M/an réellement abandonnés** sur cette fenêtre,
et probablement à une fraction seulement pour les workers déjà prêts.

## 8. Reproductibilité et statut

- Analyseur : `python -X utf8 sweeps/analyse_opcode_early4.py
  results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_engine
  --out results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_breakdown.json
  --label detail_worker`.
- Tests dirigés : `python -X utf8 -m unittest discover -s sweeps
  -p test_analyse_opcode_early4.py -v` : **2/2**. Suite générale hôte :
  **1 970/1 970 PASS**, après adaptation d'une fixture source qui exigeait
  l'ancienne écriture sur une ligne de la sonde C121 ; son contrôle
  du flag et de l'action commune aux deux boucles reste actif.
- Smoke 1×1 diagnostique : `results/smoke_opprof_corrected_20261012.json`,
  statut moteur OK.
- Le code de production **par défaut** n'est pas modifié :
  `ai/OpexAI/probes.nut` contient seulement une correction de parité et
  des compteurs sous `probe_loop_ops=1`, défaut **0**.
  **Aucun correctif d'ordonnancement, aucun réglage worker activé,
  aucune adoption, aucun commit ni push au titre de cette analyse.**
