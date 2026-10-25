# PCAL-02 — sites d'aéroports préparés dans le reliquat du tick

Conception préalable et suivi du smoke, 25 octobre 2026. Branche locale `pcal02`, départ propre
`269ec7bcfe13b9960716eb59b3ea6f3c97a7b7de`. Prototype **OFF**, réglage
`pcal02_air_sites=0` aux quatre difficultés. Aucun moteur, Docker, banc,
push ou fusion autorisé par cette tâche. Commit local demandé.

**État courant :** l'[autopsie du smoke c](#autopsie-du-smoke-vps-pcal02_smoke_1x3_20261025c)
confirme que le catalogue a déjà trouvé les sites avant PCAL-02. **Aucune rustine
de consommation ajoutée ; défaut 0 conservé.** Le levier à étudier est le coût ou
l'ordonnancement du balayage existant, sans deuxième recherche géométrique.
La [suite du smoke b](#suite-du-smoke-vps-pcal02_smoke_1x3_20261025b) décrit le
code livré en `09993db9` ; les sections antérieures restent l'historique des
livraisons `2e8351f7` et `1b8b3afc`, pas leur qualification.

## Gisement observé et limites de la mesure

Lecture statique : les deux boucles (`Start`, `_mainLoopProfiled`) exécutent
événements, orchestrateur, V276, reprises C78/C121, débit A* puis C67 avant
`Sleep(1)`. Seul le reste **à cet endroit**, après V309, est réaffectable ici.
`OPS_PER_TICK=10000` ; ce débit ne s'accumule pas entre ticks. Les attentes
de commandes et les suspensions automatiques ne constituent pas ce reliquat.
L'inventaire trouve un `Sleep(1)` terminal dans chacune des deux boucles.
Il ne mesure pas son budget disponible en partie.

Aucun `docs/air_opcodes_comptabilite*` présent dans cet arbre. Sources existantes :
[V309](v309_attente_cartographie_20261021.md),
[PCAL-03](pcal03_inventaire_20261021.md),
[V278](v278_air_lazy_sites_20261020.md),
[C78](22_c78_lignes_vs_aaa.md), [C83](c83_slot_reaction_20261002.md).
V309 rapporte 165,61 M opcodes laissés au Sleep sur trois parties × dix ans,
27 111 tours et un seul tour strictement inutile ; 231,46 M opcodes du proxy
stable sont **déjà dépensés**, à ne pas additionner au reliquat. L'archive
antérieure à vingt références indique 3,40 M/an en 1970–1972, 1,26 M/an en
1973–1978. Ce sont des mesures historiques instrumentées, pas celles de ce
prototype. PCAL-03 avertit que les spans parent/enfant ne s'additionnent pas.
Le coût `air.sites` 9,64 M → 0,44 M à 1024² concerne V278, pas un gain PCAL-02.
Les journaux/JSON sources V309, `ac04v3_usage_*_opcode` et
`v277v279_profil_*` ne figurent pas dans `results/` ou `evidence/` de ce
worktree : chiffres repris des rapports cités, aucun recomptage prétendu.

## Intervention isolée

Pas de scan des villes, de moteurs ni de production globale supplémentaire :
les demandes viennent des appels normaux à `OpexAirFindSite`, après leurs
gardes de ville/slot et hors course C83 ciblée. Huit demandes ville/type au
maximum, priorité population, sans réécriture des curseurs, plans ou publications
C78/V278/PO-01c. Le worker choisit l'avion compatible dans `catalog.airCombos`
déjà calculé ; ni moteur ni type d'aéroport codé en dur. Une demande ne lance
jamais une seconde génération de paires ou d'économie C121.

Le premier appel reste synchrone sur miss. En l'absence de projet AIR sélectionné
finançable disposant d'un chemin de dispatch, les appels suivants au hook peuvent
préparer les **prochaines** générations. Conséquence assumée :
aucune accélération promise du tout premier scan ni des villes jamais demandées.
**Correction après le smoke inerte de `2e8351f7` :** un worker de régénération,
un lot C78 ou PO-01c ne sont plus des vetos globaux. Le worker de précalcul
ne modifie ni ces lots ni leur catalogue ; il peut préparer sa géométrie privée
dans le reste du tick après leurs tranches normales. Le contrôle de financement
lit seulement la sélection, après observation des files et des blocages du
dispatch ; s'il ne finit pas dans le reliquat, il cède le tick sans géométrie.
La lecture de `OpexCashReserve` parcourt toute la flotte : elle est exclue du
worker. Celui-ci soustrait `CASH_RESERVE_MIN`, borne inférieure de la réserve
réelle, et compare `OpexProjectFinanceCapital` au disponible ainsi majoré.
Ce veto reste conservateur sur le financement ; il n'utilise pas une réserve
périmée trop haute pour déclarer un chantier indisponible.

Recherche reprenable par ancre puis par tuile, même ordre de couronnes que
`OpexAirFindSite` (r=4..25, X puis Y), et mêmes prédicats natifs de territoire,
emprise et couverture. Sous-ensemble volontaire : **terrain déjà plat**,
au plus 512 ancres, quatre sites valides et un anneau après le premier succès
(bornes C96). Aucun nivellement, arbre, dépense réelle ni réservation de slot.
`BuildAirport` ne s'appelle qu'en `AITestMode` protégé par `AIAccounting`.
Top K=2, tri PASS décroissant, puis MAIL décroissant, coût de construction
simulé croissant, ordre d'énumération conservé à égalité. Ces nombres sont des
comptes de production physique, pas une nouvelle estimation de demande C121.
Le coût de nivellement préparé est nul ; les sites en pente restent au chemin
normal. La concurrence et les droits locaux sont retestés par le moteur.

Une entrée préparée est identifiée par ville/type, avion et année, dimensions,
époque d'invalidation et date ; TTL 90 jours depuis la demande, y compris calcul
inachevé et résultat vide. Les invalidations géométriques existantes de tous
les modes et l'échec d'un site invalident la géométrie préparée par son époque.
Une demande vierge (`plane=null`) n'a aucune géométrie : elle survit à ces
invalidations et au changement d'année, puis prend l'époque et l'année courantes
au début du calcul, **sans repousser sa date/son TTL**. Les deux
appels actuels à `OpexAirResetSiteCache` sont dans le constructeur et `Start` :
ils vident aussi PCAL-02, donc notamment après Load. Les reprises C78/V278
n'appellent pas ce reset et peuvent lire le stock préparé entre générations.
Les changements effectifs d'avion compatible, d'année ou de dimensions interdisent
le réemploi préparé ; remplacer une table catalogue/`airCombos` à avion identique
ne l'interdit plus. Les changements externes passent par la revalidation vivante.

## Consommation et chemin OFF

`OpexAirFindSite` propose une copie d'un site prêt, revalidé avec
`OpexAirSiteStillBuildable` et `OpexAirSiteHasCatchment`. Il renseigne alors
`AIR_SITE_CACHE` comme le chemin normal. Un résultat vide ou périmé laisse
le scan historique travailler ; il n'est jamais un cache négatif global.
Le plan garde une petite provenance transitoire (identifiant, date, avion,
prix simulé et coût de préparation), sans référence mutable au job.

Au chantier AIR, les ancres du plan ne sont pas remplacées : déplacer un bout
après C121 rendrait sa demande et son économie incohérentes. Les contrôles
historiques de plan vivant et de sites restent présents. Pour les bouts
préparés, contrôle supplémentaire de TTL/époque/type/avion, ville autorisée,
couverture et constructibilité/limite municipale, puis nouveau devis simulé.
Refus si le prix dépasse celui préparé ; les gardes de caisse/marge normales
du chantier restent appliquées. Le site n'est marqué construit qu'après une pose physique réussie ;
hit au catalogue n'est pas synonyme de construction de ligne réussie.

Le code historique reste identique octet pour octet **après retrait des seuls
fragments explicitement gardés par le nouveau réglage**. Un contrat SHA fige
cette projection OFF sur les sources initiales. La lecture du réglage et les
branches ont un coût : aucune identité de trajectoire binaire n'est prétendue.
Les copies PO-01c ont été régénérées par leur générateur et vérifiées.

## Budget et journal prévus avant implémentation

Plafond cible : 4 000 opcodes par appel, un appel utile par tick, réserve finale
2 000 ; provision atomique 1 200 avant chaque micro-étape, queue réservée de
600 pour comptabilité/journal, au plus 16 étapes. Entrée seulement avec au moins
6 000 opcodes disponibles ; l'appel à `GetOpsTillSuspend` ne recrée aucun budget.
Les contrôles d'admission font partie du budget. Aucun anneau AIList ni boucle
d'emprise entière n'est amorcé dans une étape. Une étape parcourt une tuile
ou exécute un nombre fixe d'API natives ; coût maximal réel à confirmer au
smoke (la provision n'est pas une mesure moteur). Si une suspension/dépassement
est constaté, arrêt du worker jusqu'au prochain démarrage : pas de dépassement
répété présenté comme du calcul gratuit.

Journal uniquement sous `DECISION_LOG` (`probes & 256`, sans forcer d'autre
sonde) : `PCAL02 calc|hit|miss|stale|built`, ville, type, identifiant, opcodes
dépensés, opcodes de recherche déplacés et coût de revalidation. Les opcodes
« épargnés » sont un **proxy** du travail préparé réutilisé, jamais une mesure
causale du scan OFF évité ; publication de stock et pose restent distinctes.
`hit phase=lookup` puis `hit phase=build` distinguent réemploi au catalogue et
consommation au chantier. Le proxy est crédité une seule fois par entrée,
même si plusieurs plans la lisent. `built` décrit une pose physique, qui peut
encore être démolie par un rollback ultérieur si l'autre bout ou l'avion échoue.
Chaque `calc` porte désormais `deny=none|mode_off|catalog_missing|room|best_air|stock_ready|entry_expired`.
`none` signifie admission ; `best_air` signifie veto de priorité du dispatch AIR.
Les évictions portent en plus `cause=date_reversed|ttl|dimensions|town|epoch|year|engine|none`
et `age_days`. `none` comme cause peut notamment accompagner un site devenu
inconstructible, indépendamment de sa fraîcheur.

`calc op_spent` s'arrête avant sa propre émission ; `total_ops_before` au
message suivant inclut l'émission précédente, les refus d'admission et
l'entretien du stock prêt. Le garde final mesure aussi le journal, et émet
`stale reason=budget_overrun` avant d'arrêter tout précalcul si la provision
est démentie. Les notifications `stale` d'éviction et `built` ont `op_spent=0` :
elles n'imputent pas de recherche. Sous `_mainLoopProfiled`, le compteur
historique `sleep_left` est **avant** PCAL-02 ; ne pas le présenter comme le
reliquat final ON. `calc left1` est le reste avant émission, pas après Sleep.

## Validation et mesures ultérieures (aucun lancement ici)

Contrats Python : défaut/lecture unique, projection OFF exacte, double boucle,
garde de journal, reprises/budget, ordre/top K, TTL/invalidation, concurrence
avec C78/PO-01c/AIR finançable, coût/coverage au chantier et cache non sauvé.
Suite complète demandée : `cd sweeps && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -3`.
Les éventuelles empreintes touchées seront explicitement rebasées et listées.

Smoke futur, même bundle/runtime et masques dans les deux bras, graine 42 ×
un an sur 256² puis 1024², 0 contre 1 ; passage hors adoption. Mesurer tick et
reste avant/après chaque tranche, coût d'admission, aucune suspension du worker,
aucune construction par le worker, santé et fin d'horizon. Relever
`calc → hit → built` par id/ville/type/ancre, stale/TTL/limite municipale,
stock jamais utilisé et budget net AIR (spans sans double compte). Un smoke
sans hit reste une compilation/exécution, pas une exposition de consommation.
Étendre ensuite l'exposition à trois graines avant d'étudier le profit ;
comparaison économique séparée **sans journal**, contrôle observateur OFF/OFF.
Save/Load futur pendant le calcul et après hit : stock vide, plans/reconstruction
ordinaires, aucune erreur. Aucun gain d'opcodes, d'avancement des créations AIR
ou de profit n'est qualifié par les seuls contrats.

## Rapport de livraison

Fichiers et points d'entrée **de la livraison initiale `2e8351f7`** (numéros
historiques ; la correction du smoke est détaillée plus bas) :

| Fichier:ligne | Rôle |
|---|---|
| `ai/OpexAI/pcal02_air_sites.nut:4` | Budget, mémoire bornée, TTL ; état transitoire à la ligne 13 et reset à 16 |
| `ai/OpexAI/pcal02_air_sites.nut:27` | Journal unique sous DECISION_LOG |
| `ai/OpexAI/pcal02_air_sites.nut:48` | Fraîcheur : année, TTL, époque, dimensions, catalogue et moteur |
| `ai/OpexAI/pcal02_air_sites.nut:63` | Demandes population, au plus huit ville/types |
| `ai/OpexAI/pcal02_air_sites.nut:96` | Réemploi et provenance au catalogue |
| `ai/OpexAI/pcal02_air_sites.nut:135` | Reliquat et admission, sans calcul de réserve par flotte |
| `ai/OpexAI/pcal02_air_sites.nut:172` | Curseur d'ancres, top K à 181, micro-étapes à 201 |
| `ai/OpexAI/pcal02_air_sites.nut:263` | Hook borné et arrêt en cas de dépassement constaté |
| `ai/OpexAI/pcal02_air_sites.nut:321` | Revalidation au chantier ; pose vérifiée à 349 |
| `ai/OpexAI/info.nut:26`, `settings.nut:42`, `globals_pre.nut:359` | Réglage 0/1, quatre défauts 0, une seule lecture |
| `ai/OpexAI/builder_air.nut:49`, `air_sites.nut:508` | Chargement du module et réemploi dans FindSite |
| `ai/OpexAI/air_construction.nut:214`, `:268`, `:328` | Contrôles avant dépense, notifications des poses A/B |
| `ai/OpexAI/air_coverage.nut:14`, `:52`, `:88` | Reset et invalidations géométriques déjà appelées par tous les modes |
| `ai/OpexAI/main.nut:845`, `probes.nut:2792` | Même hook terminal dans les deux boucles |
| `ai/OpexAI/po01c_generators.nut:1227` | Copie **générée**, aucun changement manuel ; générateur inchangé |
| `sweeps/test_pcal02_air_sites.py:136` | 18 contrats/projections ; OFF à 146, reprise de couronnes à 299, Save/Load à 352 |
| `sweeps/test_po01c_regen_split.py:422` | Cinq empreintes explicitement rebasées (ci-dessous) |
| `sweeps/test_v158_lazy_select.py:160` | Lecteur de sélection autorisé uniquement comme veto de travail de fond |
| `sweeps/test_parameter_retirements_20261023.py:87`, `test_v246_fixed_policies.py:25`, `test_v251_inventory.py:44`, `test_v259_bridge_renew.py:62`, `test_v276_candidate_slices.py:287`, `test_v284_rail_growth.py:20` | Inventaires 58 → 59, sans rétablir les réglages retirés |
| `docs/taches.md`, entrée PCAL-02 | Statut livré OFF ; les autres chantiers restent inchangés |

Budget livré : 4 000 opcodes **cibles** par appel utile, une seule admission
par tick, entrée à ≥6 000, réserve 2 000, provision d'étape 1 200 et queue
600, maximum 16 étapes. Le test de budget exécute l'expression source et
vérifie l'inégalité pour différentes réserves/coûts atomiques ; il suppose
le coût atomique ≤1 200. Cette hypothèse reste à mesurer dans OpenTTD, et le
garde d'arrêt ne garantit pas qu'un premier dépassement ne peut jamais arriver.
Analyse statique : aucune boucle dans une micro-étape ; phase emprise = une
tuile ; phase géométrie = nombre fixe d'API natives ; phases sonde/catchment
= appels natifs bornés ; tri = au plus deux éléments. L'amorçage et les vetos
ne déclenchent ni `Valuate`, ni liste moteur/villes/véhicules, ni A*.

Empreintes PO-01c rebasées, ancien → nouveau SHA-256 :

| Source | Ancien | Nouveau |
|---|---|---|
| `air_sites.nut` | `1ef05fc3b922e34d5ed800a52d9b5816e2d958492e434075bd0fe1e4e5a546f7` | `66e81b5515110d902885b17222fde74b7308d93335c176beea4afd05fd19e562` |
| `main.nut` | `b716838631daba2621fd9b7d992b72accd042c0ba0a2c4d8d89527709358ad68` | `57cbf1725f83093e7d1fa3460285b41401cc29864d92dd580142345ba9f05f79` |
| `probes.nut` | `005a79a7647c1ddd98754b3854497f5328c6eb4bea62ae3a9192e0a03dfab84e` | `fd75648b490c2614149438d9a91e0be58ca209f35c7233f19a743f43ae3efb8d` |
| `settings.nut` | `6946a9ed7d3864e22714167b4fbb4fe74d8e6b95b39c0fac0054cfde80bc214b` | `94519b3fbd4d3ae781eb59b2006d360a47380c47fd9659aed79a1a5347a126a7` |
| `info.nut` | `1bc76539590e9272aa59849baa54d0248a74ac5f993e0d0e77d679906c7ad2c3` | `a3c86c3cf3c980d1bae9aeecd56d0d079b600a944a1c4fdf67516c6b1d2258b4` |

Cette rebase accompagne uniquement les ajouts gardés OFF demandés ; aucune
qualification moteur/économique transférée. Le contrat PCAL-02 conserve les
**anciens SHA** sur la projection OFF de **dix fichiers**, copie générée comprise.
Aucun nouvel appel `Valuate` : inventaires V261/V262 inchangés.

Limites restantes : mémoire de demandes et sous-ensemble plat volontairement
petits ; un AIR sélectionné finançable mais devenu non constructible peut encore
opposer un veto conservateur lorsque son dispatch est disponible ; une longue
file peut épuiser le budget du contrôle d'admission sans progression ;
invalidations globales conservatrices pouvant rejeter un site encore sain ;
préparation des seuls futurs scans, pas d'accélération promise du premier ;
scans doubles possibles entre stock préparé et cache historique ; profit,
économie **nette** d'opcodes et calendrier de construction non mesurés.
La compilation Squirrel, les suspensions réelles et le roundtrip Save/Load
restent à valider au smoke/harnais autorisés ultérieurement. Aucune partie lancée.

Validation finale **de la livraison initiale** : **2 445 tests en 26,493 s, OK**,
9 ignorés et 2 échecs attendus ; **18 contrats/projections PCAL-02** compris.
Sortie locale : `results/pcal02_unittest_final.log` (ignorée par Git).
`git diff --check` sans diagnostic ; génération PO-01c identique au générateur.
Les ignorés restent distincts des tests réussis : pytest manque pour
`test_analyze_air_load_shadow`, `test_audit_air_roi_renfort1` et
`test_audit_air_roi_renfort1_itt` ; numpy manque pour
`test_bandes_roi_20261021`, `test_roi_extra_predictors_20261021` et
`test_roi_predictors_20261021` ; les deux modules de harnais
`test_b9_air_catchment` et `test_c98_vs_aaa_engines`, ainsi que la fixture
historique `test_ac04_causal_existing`, sont conditionnels à leurs dépendances.
Pas de compilation Squirrel, de smoke ni de roundtrip moteur exécutés.

## Suite du smoke VPS `pcal02_smoke_1x3_20261025`

Reprise demandée sur `pcal02`, HEAD initial `2e8351f7`, arbre propre. Les
résultats fournis sont lus sans être modifiés :
`results/pcal02_smoke_1x3_20261025_engine/pcal02_seed42_r0.log`, bras `pcal02`,
graine 42, trois ans, `pcal02_air_sites=1`, `probes=258`. Ce smoke antérieur
est exécuté par l'utilisateur ; **aucun moteur, Docker ou banc relancé ici**.

### Diagnostic à partir du journal et du code initial

Recomptage local : **125 calc**, tous `admitted=0 ready=0 steps=0` ;
**19 miss, 11 stale, 0 hit, 0 built**, et **43 AIR_BUILD** dans la partie.
`left0` va de **5 980 à 9 967** (la mesure commence après le précontrôle
à 6 000). Le reliquat n'explique donc pas à lui seul le refus systématique.

| Signature `op_spent` des calc | Nombre | Attribution par rapprochement avec le code et les événements |
|---|---:|---|
| 154 | 76 (60,8 %) | Retour de tête, signature du veto `_activeWorker != null` ; commence après `C83_REACTION town=18 action=enqueued` du 19/02 et le démarrage du scan réactif du 20/02 ; dernière occurrence le 17/03 |
| 167 | 9 | Début du scan initial, avant publication du premier portefeuille : veto `_projects == null` ; du 03/01 au 12/01 |
| 212 | 32 | Signature compatible avec le refus du lot `c78AirRebuild` dans la première tâche de file, avant tout parcours de `best` ou `airPlans` ; trois occurrences après première publication, puis 29 après le scan réactif |
| 197 / 252 | 1 / 7 | Éviction `worker_expired`, donc aucun appel à `Admit` dans ces huit calc |

**Le veto worker est l'explication dominante la mieux étayée, puis le lot
C78 ; un plan brut « finançable » n'est pas démontré comme cause dominante.**
Les 76 événements à 154 opcodes ne forment pas une période de worker
ininterrompue : des tâches normales s'intercalent. Aucun `PO01C_SLICE` n'est
émis avant l'arrêt du précalcul. Cela ne prouve pas à lui seul l'absence d'un
pending PO-01c. Les états de ces gardes n'étaient pas journalisés : ces
attributions sont une **inférence**, pas des compteurs `deny` rétrospectifs.
Le faible coût constant et la position des retours excluent comme explication
plausible un parcours complet de la file puis des deux listes AIR à chaque refus.
Les futurs calc nomment directement le refus effectif avec `deny`.

Les huit expirations ne sont **pas le TTL** : ids 1..8 âgés respectivement de
**13, 12, 12, 12, 14, 14, 14, 14 jours**, tous `prepared_ops=0`. Le code initial
testait l'époque globale **avant** `entry.plane == null`. Le 14/01,
`PROJECT_DISCARD reason=build_failed detail=AFAIL error=263` est suivi des
invalidations du chantier ; les demandes sont supprimées du 15 au 18/01.
Avec des entrées jamais admises, aucun moteur choisi, aucune géométrie et
aucun changement d'année/dimensions, le changement d'époque explique ces
rejets précoces. Il effaçait une demande, pas un site devenu caduc.

Enfin, à la ligne **2370** du log, le dernier calc du 30/03 porte
`tick0=1642 tick1=1643 left0=9967 left1=9698 op_spent=212`, puis la ligne
2371 émet `budget_overrun op_spent=411`. L'ancienne variable `tick` était
prise **avant** les précontrôles, alors que `mark` était pris après. Avec la
formule de `OpexOpsMeasureEnd`, un franchissement depuis le tick du mark
aurait coûté plus de 10 000 opcodes, pas 212/411 : le mark se situe déjà
au tick suivant. Le garde comparait deux origines différentes, puis armait
`fault=true` définitivement. Aucun calc ne suit le 30/03, même si des miss
et AIR_BUILD continuent. Ce faux positif aurait masqué toute correction
du seul critère d'admission.

### Choix du correctif

`OpexPCAL02BuildTurn` observe les voies d'exécution existantes, sans avancer
les files ni appeler le constructeur :

- Un worker autre que `rail_search`/`rail_stock` rend la main avant la file
  de fond ; un portefeuille absent ou invalidé attend une publication.
  Ces attentes autorisent la préparation, même avec des plans bruts finançables.
  Les deux workers rail laissent au contraire passer la file de fond : ils
  ne masquent donc pas un AIR prêt à être dispatché.
- La tête de la FIFO réactive `c77_build` disponible garde la priorité AIR,
  en respectant le report C77 existant, notamment PO-01c pending/job en mode 2.
  Le code ne copie pas toute la FIFO : lecture bornée de la tête et `get`.
- La file de fond est observée dans le même ordre suffixe puis cycle suivant
  que `_runNextTask`, avec `enabled`/`dueCycle` et contrôle `Room` à chaque
  itération. Si une autre tâche passe avant `projects`, un AIR attend la file.
- Seulement avec une voie `projects`/réactive disponible, un AIR de `best`
  financé par la caisse minorée de `CASH_RESERVE_MIN` oppose `deny=best_air`.
  **`airPlans` n'est plus parcouru** : posséder un devis finançable ne lui
  donne ni sélection ni créneau. La présence de C78/PO-01c n'est pas un veto
  global ; si un AIR déjà publié peut partir malgré ces lots, il garde son veto.

Le hook reste après orchestrateur, reprises AIR, A* et C67, juste avant Sleep
dans les **deux boucles**. Il ne déclenche aucun chantier ni réordonnancement,
et conserve plafond/provisions/arrêt sur dépassement mesuré. La priorité est
conservatrice lorsque le dispatch est disponible : le contrôle ne rejoue pas
les tests vivants de site, la sélection différée, les plafonds de lignes ou
le ciblage exact d'une intention C77. Il peut donc encore céder inutilement
devant un AIR sélectionné qui échouerait plus loin. Ce compromis évite un
second préflight non borné et ne retarde pas un AIR exécutable.

`OpexPCAL02Expiry` conserve TTL 90 jours depuis la **demande**, contrôle ville
et type/dimensions, puis distingue demande vierge et géométrie préparée.
Seule la première survit aux changements d'époque/année ; au premier calcul
son année/époque sont actualisées sans renouveler le TTL. Une géométrie
préparée reste invalidée à l'époque suivante. Le changement d'identité de
table catalogue/combos à moteur compatible identique n'est plus une expiration ;
un changement effectif de moteur l'est. Les tests physiques au lookup/chantier
et le devis maximal préparé sont conservés.

Le tick d'admission, `lastTick`, `tick0` et le garde final dérivent maintenant
tous de **`mark.tick`**, après précontrôle. Un franchissement **dans**
l'intervalle mesuré ou un dépassement effectif conserve l'arrêt de sécurité.

Points d'entrée corrigés : `pcal02_air_sites.nut:48` (motifs d'expiration),
`:99` (âge/cause au stale), `:161` (disponibilité du dispatch), `:194`
(admission), `:306` (tick et `deny`). Aucun autre module de comportement
modifié ; aucune intervention sur RAIL-LONG-EARLY-1, AIR-FLOTTE-1, C115 ou IDLE-1.

### Contrats, empreintes et limites de validation

**2 452 tests, 26,980 s, OK** (9 ignorés, 2 échecs attendus), commande demandée
`cd sweeps && python3 -m unittest discover -p 'test_*.py'` ; sortie locale
`results/pcal02_followup_unittest_worktree_20261025.log` (temporaires de cette
dernière passe dirigés vers `results/pcal02_test_tmp`). **25 contrats PCAL-02**, dont
projections des prédicats Squirrel réellement livrés : worker/file/portefeuille
en attente, lot partiellement publié, workers rail, AIR sélectionné prioritaire,
devis brut sans sélection, report C77/PO-01c, cycle de file, épuisement de budget,
TTL non glissant, époque et remplacement de catalogue. Les suites PO-01c
(27) et V158 (12) passent également ; le lecteur `best` V158 est redocumenté.
Les dépendances manquantes et exclusions sont celles du bilan initial ci-dessus.

**Défaut 0 aux quatre difficultés ; projection OFF des dix sources inchangée
octet pour octet**, anciens SHA conservés. Pas de nouveau réglage, `Valuate`,
état comportemental ou champ Save/Load. Le cache et les défauts de budget sont
toujours reconstruits/effacés à Start après Load. Le générateur PO-01c n'a pas
changé ; sa sortie reste exactement égale à `po01c_generators.nut`.

Rebase des hashes : **aucune des empreintes d'isolation existantes n'a besoin
d'être rebasée pour cette suite**, car leurs sources n'ont pas changé. Les cinq
rebases de la livraison initiale restent celles du tableau précédent et les
SHA de projection OFF ne sont pas relâchés. Pour tracer le seul module de
production corrigé, SHA-256 initial → corrigé :

- `pcal02_air_sites.nut` : `e6cca1199d3859e455ca1edb5ae3b02622fec90dc3368ad748006c996e1e1e5b`
  → `75f6296dbcaeb6183e33fe01574a12670261babd92e994a5487bc43b6f33061f`.
- `po01c_generators.nut` : **inchangé**,
  `dd3098151ff5c6bf6a45a7ae14d2833d8731d0ddb7b7cd9a8162a6f17e1476d4`.

Les contrats démontrent des voies d'admission atteignables et les gardes, pas
une consommation en partie. **Compilation/exposition moteur du correctif,
progression jusqu'à ready/hit/built et Save/Load moteur restent non validés**,
conformément à l'interdiction de parties de cette reprise. Aucun gain d'opcodes,
de calendrier AIR ou de profit n'est attribué au correctif par ces tests.

## Suite du smoke VPS `pcal02_smoke_1x3_20261025b`

Reprise demandée le 25/10 sur `pcal02`, HEAD initial **`1b8b3afc`**, arbre
propre, après `2e8351f7`. Autorisation : correctif local, contrats, document et
commit. **Aucun Docker, moteur, partie, push, merge ni configuration Git** ;
temporaires et sortie de tests dirigés dans le worktree.

### Constats recomptés sur les artefacts fournis

Sources inchangées : `results/pcal02_smoke_1x3_20261025b.json`, son manifeste
et `results/pcal02_smoke_1x3_20261025b_engine/pcal02_seed42_r0.log` ; graine 42,
trois ans, `pcal02_air_sites=1`, `probes=258`, bundle SHA-256
`66cc48c05724fcde5f3b7937a895626a8b69e3309943a21cf4e4d48b63a0c38d`.
**337 calc** : 237 `deny=none`, 80 `stock_ready`, 19 `entry_expired`,
1 `best_air` ; **42 miss, 21 stale, 0 hit, 0 built**. Les stale comprennent
19 `worker_expired cause=epoch` et deux `lookup_expired cause=ttl`.
Admission corrigée, consommation toujours non exposée.

Les JSON donnent dans les deux smokes a/b les mêmes métriques terminales
Opex : référence **2 492 048 £/an**, variante **2 470 777 £/an**, delta
**−21 271 £/an** ; valeurs respectives 4 860 385 et 4 623 840 £.
Cela confirme l'identité de ces métriques, sans prouver une identité complète
des trajectoires. Le smoke reste hors échantillon d'adoption.

Ville 18, entrée 1 : demande le 02/01/1970, **12 calc, 111 micro-étapes**,
jamais prête ; éviction le 15/01 à 13 jours. `prepared_ops=23 966` correspond
au travail géométrique ; la somme des `calc op_spent` vaut **27 872**, avant
leurs propres émissions. Ni l'un ni l'autre n'est le prix de deux sites finis.

| Ville / entrée | Première terminaison `ready=1` du code précédent | Calc admis jusqu'à cette date | Micro-étapes | Somme `calc op_spent`, hors émissions propres |
|---|---|---:|---:|---:|
| 2 / 9 | 26/02/1970 | 41 | 468 | 92 645 |
| 30 / 4 | 23/03/1970 | 65 | 614 | 151 832 |
| 27 / 11 | 16/04/1970 | 24 | 265 | 54 470 |

L'ancien `ready` signifiait fin du scan, y compris résultat vide/plafond de
gares. Les logs n'exposaient ni le nombre d'ancres ni celui des sites valides :
ne pas déduire deux sites plats de ces terminaisons. Les entrées 4 et 11
expirent au TTL avant demande ; l'entrée 9 expire à l'époque au 10/04.

### Invalidation et consommation corrigées

- Les invalidations géométriques générales ne modifient plus PCAL-02.
  Un reset ordinaire du catalogue/site-cache ne vide plus ce stock.
  L'époque PCAL-02 devient une **génération de démarrage**, avancée seulement
  par `OpexPCAL02Reset`, appelé explicitement dans `Start` après les réglages.
  Travail en cours et top prêts survivent aux constructions éloignées.
- Le refus d'une ancre appelle `OpexPCAL02InvalidateSite` : seule l'entrée
  ville/type qui contient cette ancre (top ou étape en cours) est retirée.
  Une autre ancre du même type/ville et tous les travaux éloignés survivent.
  Cela évite de resservir sans fin un devis refusé au chantier.
- Le TTL **90 jours depuis la demande** reste non glissant. Type, dimensions,
  ville et avion compatible réellement changé restent des causes d'expiration.
  Le passage au 1er janvier seul ne l'est plus. Remplacer une table catalogue
  avec les mêmes caractéristiques ne détruit pas la géométrie.
- `OpexAirSiteStillBuildable` et le catchment sont rejoués à chaque lookup ;
  au chantier, type/dimensions/avion, génération de démarrage, TTL, politique
  municipale, constructibilité/couverture et devis maximal restent contrôlés.
  Aucune ancre de plan ni économie C121 n'est déplacée après sélection.

### Anticipation et réemploi du travail déjà fait

Le hook n'exige plus une demande existante. Son curseur privé lit uniquement
`owner._catalog.towns`, `airCombos` publiés et `owner._lines` : **aucune lecture
ni écriture des lots C78/C121/PO-01c**, aucun appel de génération de plans, de
catalogue ou de flotte. Le choix retenu est le vivier de population, plutôt
qu'une inspection des lots pour prédire leurs curseurs.

Une passe conserve les **K=4 prochaines villes non desservies en AIR**, par
population décroissante et ordre catalogue à égalité. Le test de desserte
reprend `OpexAirTownServed` (origines AIR à moins de 15 tuiles Manhattan),
**une ligne par micro-étape**, avec le plancher V93. Elle demande les types
d'aéroport des combos publiés, au plus deux actuellement, donc **huit entrées**.
Le catalogue n'est ni trié ni modifié. La politique de niveau/slots reste au
consommateur normal et au chantier : son implémentation aux niveaux bas peut
scanner des gares, elle n'est pas rappelée dans une micro-étape de reliquat.
Le stock peut donc anticiper un candidat que ces gardes refuseront ensuite.

La passe complète précède l'éviction des villes sorties des quatre suivantes,
une entrée par étape ; une passe partielle ne purge rien. Elle recommence à
changement de liste des villes/lignes ou de nombre de lignes, sinon après
sept jours. Ce redémarrage du **curseur d'anticipation** ne vide pas les sites
ni leur progression. Le veto du dispatch AIR sélectionné et finançable demeure
prioritaire, avant toute anticipation.

Au plus **quatre étapes d'anticipation par tick** avec un stock existant,
seize pour amorcer un stock vide ; anticipation et recherche partagent le
**même plafond total de seize étapes et 4 000 opcodes**, les mêmes provisions
et le même arrêt sur dépassement. Le coût du curseur est inclus dans
`totalOps`/`calc op_spent`, pas dans le proxy géométrique `preparedOps` d'une
entrée. Pendant un amorçage encore sans entrée, les coûts sont comptés dans
`totalOps` mais aucun `calc` ville n'est émis ; le prochain `total_ops_before`
les inclut. Il n'y a pas de budget supplémentaire créé par l'anticipation.

Deux réemplois rendent le résultat disponible plus tôt :

1. Le gagnant du **finder normal** (trois retours C96 et retour du cache positif,
   hors course C83 ciblée) fournit son ancre à `OpexPCAL02SeedSite`. Le worker
   l'essaie avant sa spirale, une fois, puis reprend son curseur sans décalage
   et sans retester cette ancre. Aucun coût/platitude n'est supposé acquis :
   emprise tuile par tuile, devis en `AITestMode` + bouclier `AIAccounting`,
   couverture et scores sont encore validés. Aucun résultat n'est publié
   directement par la notification du finder.
2. **`ready` distingue maintenant disponibilité et fin de recherche (`done`).**
   Dès le premier site réellement validé, il est consommable. Le worker peut
   affiner le top 2 jusqu'aux quatre candidats C96 ou à ses autres limites.
   Un résultat vide terminé a `done=1 ready=0`. Consommer avant la fin peut
   choisir un autre site qu'attendre le top final : changement ON explicite,
   sans qualification économique transférée.

### Coût : ce qui est expliqué, ce qui reste à mesurer

~24 k opcodes n'est **pas un coût qualifié « normal » pour deux sites**.
Une emprise 6×6 prend au moins **40 étapes** : ancre, 36 tuiles, commande
simulée, PASS, MAIL. Quatre candidats demandent au moins 160 étapes, avant
ancres refusées, admission, comptabilité, garde par étape et journaux. Le
stock n'en garde que deux. Les 265–614 étapes observées ci-dessus montrent
que la conservation de deux sorties ne borne pas le travail à deux emprises.

Le réemploi de l'ancre gagnante évite une redécouverte aveugle ; publication
précoce réduit l'attente jusqu'au premier usage. L'appel synchrone complet à
`OpexAirFindSite`, `OpexAirFootprintCheapOk` ou aux anneaux AIList n'est pas
réutilisé dans une micro-étape : leurs boucles peuvent suspendre et dépasser
ce reliquat. Le contrôle natif vivant est réservé au consommateur normal.
Pas de gain net chiffré prétendu : les nouvelles phases et l'anticipation
doivent être mesurées dans un futur smoke autorisé.

### Journal et preuve de consommation attendue

Chaque candidat conservé porte sa propre `readyDate`. Les événements
**`hit phase=lookup`**, **`hit phase=build`** et **`built`** ajoutent
`lead_days=` (date d'événement moins date de disponibilité de **l'ancre
choisie**). Les deux hit portent aussi `ready_date=`. Si le classement
s'améliore, la date du nouveau gagnant remplace celle de l'ancien dans sa
preuve, sans rajeunir le TTL de la demande.

Les `calc` ajoutent `ahead_steps`, `done`, `ready_date` du premier résultat
utilisable, `anchors`, `valid`, `phase`, `tile`, `prepared_ops`. Ils permettent
de séparer exploration, emprises, fin vide et attente de consommation.
`stale reason=ahead_not_next` distingue la sortie du vivier anticipé ;
`site_failed` identifie le refus ciblé. Plus de `cause=epoch` ou `cause=year`
pour un chantier ordinaire. La garde de journal `DECISION_LOG` reste unique.

La projection des **corps réellement livrés** produit désormais
`hit lookup lead_days=7 → hit build lead_days=12 → built lead_days=12` avec
des API factices, et vérifie qu'un gagnant plus récent donne son propre délai.
**Ce n'est pas un hit moteur observé.** Le prochain smoke doit exposer ce
parcours réel et ses coûts ; 0 hit resterait une exposition non validée.
Aucune partie ni dépense économique n'a été exécutée dans cette reprise.

### Validation, Save/Load et empreintes

Commande demandée, depuis `sweeps/`, avec `TMPDIR` dans
`results/pcal02_revision_test_tmp` :
`python3 -m unittest discover -p 'test_*.py'`.
**2 459 tests, 27,889 s, OK**, 9 ignorés et 2 échecs attendus, dont
**32 contrats PCAL-02**. Sortie ignorée par Git :
`results/pcal02_followup_b_unittest_20261025.log`.
Les dépendances manquantes restent celles du bilan précédent.

Les projections couvrent notamment anticipation sans miss, ordre/égalité de
population, deux types/huit entrées, ville déjà desservie, changement de lignes
sans perte du travail survivant, ancre réutilisée sans avancer la spirale,
publication avant fin, hit/built et délai, refus ciblé, terrain changé,
surcoût de devis, moteur/dimensions et reset après chargement. Elles ne
compilent pas Squirrel et ne mesurent ni commandes natives ni opcodes réels.

**Save/Load :** cache, curseurs d'anticipation et de géométrie, dates, top,
comptabilité et défaut de budget restent transitoires, absents de `persist.nut`.
`Load` invalide déjà `_projects` ; `Start` vide explicitement le stock et le
curseur avant l'une ou l'autre boucle. Le test exécute le reset et rejette une
ancienne preuve de la génération précédente. Le roundtrip moteur reste
**non exécuté**, comme demandé. **Défaut 0 aux quatre difficultés.**

Deux empreintes du contrat PO-01c sont **explicitement rebasées**, uniquement
pour les ajouts gardés OFF (commentaire justificatif dans le test) :

| Source | SHA-256 avant (`1b8b3afc`) | SHA-256 livré |
|---|---|---|
| `air_sites.nut` | `66e81b5515110d902885b17222fde74b7308d93335c176beea4afd05fd19e562` | `9e1cac01481c02f13b1aa41ed6a8c42f87dce40af5c01b0ec812155d279e6050` |
| `main.nut` | `57cbf1725f83093e7d1fa3460285b41401cc29864d92dd580142345ba9f05f79` | `cec4b3778884dc55f1718ab4bf6485b3867c11255c1d137a8a06aec2c45e243f` |

Les **dix SHA de projection OFF restent ceux de `269ec7bc`**, sans rebase :
retrait exact des seuls ajouts gardés, y compris les quatre notifications
dans la copie générée. `po01c_generators.nut` a été régénéré avec
`sweeps/po01c_generate.py` inchangé et son égalité au générateur est testée.
Autres empreintes de production pour la revue :

| Source | Avant | Après |
|---|---|---|
| `pcal02_air_sites.nut` | `75f6296dbcaeb6183e33fe01574a12670261babd92e994a5487bc43b6f33061f` | `fa61665352fdfceb3ce124f9b618162a594561c7a035a5f225d4430326f9d839` |
| `air_coverage.nut` | `f1824d342112f4881f0da36e52d1a77697882c45b721191c1e0500df72396e66` | `675a4245a73bf47f5a52712c552abf38eaa1b8f5e2e315c126b2da104f49d50a` |
| `po01c_generators.nut` | `dd3098151ff5c6bf6a45a7ae14d2833d8731d0ddb7b7cd9a8162a6f17e1476d4` | `4457ef28548d3c14854e260d146a776df100e1900a95ccebee1ad90af966c422` |

`git diff --check` sans diagnostic. Aucun nouvel appel `Valuate`, fermeture
anonyme, identifiant réservé ou `const` ; inventaires Valuate inchangés.
Aucune modification de RAIL-LONG-EARLY-1, AIR-FLOTTE-1, C115 ou IDLE-1.
Restent à vérifier au moteur : compilation de cette version, suspension/coût
de chaque nouvelle micro-étape, `calc ready → hit → built` et ses délais,
Save/Load, puis économie nette et effet de calendrier/profit. **Aucun gain
qualifié ni adoption ; le smoke b concerne seulement le code précédent.**

## Autopsie du smoke VPS `pcal02_smoke_1x3_20261025c`

Reprise du 25/10, branche `pcal02`, HEAD propre
`09993db9ab8eae0582802367c312c8a56497ea9e`, après `2e8351f7` et `1b8b3afc`.
Lecture des artefacts fournis, sans les modifier ni relancer de partie : JSON,
JSONL, manifeste, bundle et journaux sous `results/pcal02_smoke_1x3_20261025c*`.
Le manifeste identifie ce même HEAD propre et le bundle SHA-256
`286548338928daf866bd4f4c92613c886bb058932cd73c95ec16c50155a8a01b`.
Les **85 fichiers OpexAI du bundle sont identiques octet pour octet** aux
sources locales. Les lignes de code ci-dessous désignent donc aussi le code
exécuté. Les numéros de journal désignent
`results/pcal02_smoke_1x3_20261025c_engine/pcal02_seed42_r0.log`, sauf mention
explicite du bras `reference`.

**Conclusion : PCAL-02 refait ici une recherche de sites déjà payée par le
catalogue C78/C121. Le chantier reçoit un plan muni de ses sites ; il n'a pas
à les rechercher une seconde fois.** L'absence de hit ne démontre pas un hook
oublié dans le finder : il est consulté, mais avant que le stock soit prêt.
Conformément à la demande, aucune modification Squirrel ni branchement tardif
sur le chantier. Remplacer une ancre à ce stade changerait la couverture et
l'économie C121 d'un projet déjà évalué.

### Les trois premières poses et l'origine des sites

| Ville | Choix normal C96, avant PCAL prêt | Premier `ready=1` PCAL | Première pose `AIR_BUILD` | Dernière consultation du finder attestée avant la pose |
|---|---|---|---|---|
| 23 | 03/01/1970, ancre **45637**, `valid=4`, 4 sondes ; journal :154 | 27/02/1970, id 5 ; :1712 | **09/02/1971**, ligne 19, **11→23**, `hubsite`, station B 45 ; :9110–9111 | Miss le 21/02/1970, :1513, **six jours avant** le premier ready ; le site normal existe déjà depuis janvier |
| 24 | 04/01/1970, ancre **55663**, `valid=4`, 4 sondes ; :179 | 11/10/1970, id 18 ; :6430 | **18/11/1970**, ligne 11, **15→24**, `hubsite`, station B 29 ; :7279–7280 | Recherche initiale le 04/01 ; contrôle de desserte dans le scan réactif le 21/02, :1523 ; aucun hit avant/après |
| 38 | 04/01/1970, ancre **55072**, `valid=3`, 4 sondes ; :169 | 24/03/1970, id 7 ; :2202 | **09/08/1970**, ligne 6, **36→38**, `hubsite`, station B 18 ; :5150–5151 | Miss le 21/02/1970, :1515, **31 jours avant** le premier ready ; le site normal existe déjà depuis janvier |

Les ancres sont les champs `best` de `C96_SITE`. **`AIR_BUILD src/dst` sont
les tuiles des villes**, ici 44107/54641/54044 pour 23/24/38, pas les ancres
des aéroports (`task_air.nut:296`). `AIR_BUILD` ne réémet pas l'ancre ni l'ID
du scan producteur : le lien à l'ancre est reconstitué par les choix C96 et
le transport sans remplacement du site décrit ci-dessous, pas par une trace
de pose contenant ces champs.

Chemin du choix à la construction (fichiers relatifs à `ai/OpexAI/`) :

1. `_dispatchAirCatalogPhase` (`scheduler_tasks.nut:133`) appelle
   `_dispatchCatalog` (:317), puis `OpexC78ContinueCatalogAirRebuild` (:242).
   Son appel à **`OpexAirPlans` (:275)** utilise le curseur privé C78 et
   `targetTownId=-1`. Le scan principal est identifié **scan 1** dans le
   journal. Sur cette carte **256²**, `v278_air_lazy_sites=2` signifie OFF
   (`settings.nut:49`) : ce n'est pas le parcours paresseux 1024².
2. `OpexAirPlans` (`air_planning.nut:1717`) appelle
   `OpexAirPlansStepFindSites` (:1594), puis **`OpexAirPlansFindSites`
   (:296)**. Ce dernier appelle **`OpexAirFindSite` (:366)**. Le finder
   (`air_sites.nut:503`) essaie PCAL-02 **:511–513, avant le cache :520**,
   puis le retour positif du cache ou `OpexAirFindSiteCatchmentListed`
   (:378, appel :569). C96 choisit et journalise le gagnant, écrit
   `AIR_SITE_CACHE` et appelle seulement **`OpexPCAL02SeedSite`** aux
   retours :427/:483/:493. Cette notification fait revalider/rechercher le
   même site au worker ; elle ne transforme pas le gagnant C96 en hit.
   Pour 24, la demande initiale peut rester sans `miss` : huit entrées de
   villes plus peuplées existent déjà (:118–172 du journal), et
   `OpexPCAL02Request` refuse la neuvième position
   (`pcal02_air_sites.nut:85–86`) ; le finder continue normalement.
3. Le site rejoint `scanSites` (`air_planning.nut:370`), est revalidé puis
   conservé dans **`resumeState.sites` (:476)**. Les reprises de hubs gardent
   aussi `air0310HubSnap.sites` (`OpexAir0310HubSnapshotStore`, :941) et les
   recopient sans nouvelle recherche (`OpexAir0310HubSnapshotPrepare`, :911).
   **`AIR_PLAN_SETS scan=1` contient les trois villes dès le 24/06/1970**
   (journal :4309), puis 38 passe des sites aux hubs après sa pose (:5162),
   24 après la sienne (:7289), et 23 après la sienne (:9118).
   Un changement de topologie réactualise ce stock et les hubs ; il ne
   redemande pas les sites déjà conservés au finder.
4. **`OpexAirPlansHubToSite` (:1157)** prend `site = sites[sj]` (:1194),
   crée **`siteB=site`, `reuseA=true`, `reuseB=false` (:1238–1241)**,
   puis `OpexC121CatalogChoice` (:1245) chiffre ce plan. Le choix C121
   utilise les sites dans sa clé (`air_catalog_c121.nut:109–115`) ; il ne
   recherche pas une autre ancre. `OpexAirStoreRoutePlan`
   (`air_engine_choice.nut:18`) conserve le plan. Publication partielle
   par `OpexC78PublishPartialAir` (`scheduler_tasks.nut:152`), conversion
   `OpexProjectFromAir` (`projects_builders.nut:262`, **`payload=plan` :287**).
5. **`_tryBuildAirProject` (`task_air.nut:142`)** reprend `project.payload`
   (:146), revalide les deux sites (:154/:160), garde **`buildPlan=plan`
   (:193)** et appelle **`OpexBuildAirRoute` (:238)**. Ce constructeur
   (`air_construction.nut:177`) pose les ancres du plan, dont le bout B
   (:309), sans appeler `FindSite`. `OpexPCAL02BuildSiteOk`
   (`pcal02_air_sites.nut:501`) retourne aussitôt vrai **:503 si le site
   n'a pas de champ `pcal02`** ; `OpexPCAL02Built` (:531) est muet dans
   le même cas (:533). Seul un hit du finder aurait attaché cette preuve
   (:239). Le `AIR_BUILD` est émis après succès (:296 de `task_air.nut`).

Le scan réactif **scan 2**, déclenché par `C83_REACTION town=18` le 19/02
(journal :1485), revoit notamment 23/24/38 avant qu'elles soient prêtes.
La restriction de slot est réservée à **la ville cible 18**
(`air_planning.nut:362–366`) : `requiredSlotTownId >= 0` n'explique pas
l'absence de hit des trois autres villes. Les miss de 23 et 38 confirment
le passage dans le hook. Ses plans `hubsite` doivent avoir un bout 18
(:1198–1199) : ils ne sont pas les trois paires construites ci-dessus.
PO-01c n'exécute ses premières tranches journalisées que le 02/01/1972
(:20555), après ces poses ; sa copie générée n'est pas leur producteur.

Les **huit** `AIR_BUILD` touchant ces villes comprennent seulement les
trois premières poses ci-dessus. Les cinq suivants réemploient un aéroport :
38→41 le 15/12/1970 (ligne 13, `hubsite`, 38 côté hub), 24→17 le 26/04/1971
(25, `hubsite`, 24 côté hub), 11→38 le 04/07/1971 (30, `hubhub`), 6→24 le
02/09/1971 (37, `hubhub`), 41→23 le 10/10/1971 (40, `hubhub`). Ils ne
constituent pas cinq autres occasions de consommer un site neuf PCAL-02.

### Coûts comparés : duplication, sans gain net démontré

Recomptage du bras ON : **1 917 calc**, dont 1 594 `deny=none`,
289 `stock_ready`, 34 `entry_expired` ; **15 miss, 40 stale, 0 hit, 0 built**.
Les six villes ayant eu un ready sont bien 18/19/23/24/34/38 (13 entrées).
La somme des **`calc op_spent` vaut 4 164 735**, avant leurs propres
émissions. Ce n'est pas le total PCAL-02 : le dernier calc, le 17/12/1972
(:29157), porte **`total_ops_before=5 563 841`**, donc **au moins 5,564 M**
déjà comptabilisés avant ce dernier appel. Ce compteur inclut aussi les
émissions précédentes et les appels sans entrée journalisable
(`pcal02_air_sites.nut:479–491`). Il n'y a pas de bilan final permettant
d'en faire un total exact à la fin du journal. Aucun `budget_overrun`,
aucun changement de tick dans les calc émis ; maximum `op_spent=2 485`
avant émission. Ces observations ne mesurent pas tout le coût ON/OFF.

Le journal existant expose les bilans suivants, **un seul des deux messages
`AIR_PLAN_PERF` compté par scan**, car la version avec et sans `OPEX` est
le même compteur émis deux fois :

| Bras / scan terminé | Date du bilan | `total_ops` catalogue AIR | `ops_sites` inclus dans ce total | Sites trouvés / sondes | Journal |
|---|---|---:|---:|---|---|
| ON, scan 2 réactif | 02/03/1970 | 650 869 | 298 428 | 40 / 66 | `pcal02_seed42_r0.log:1813` |
| OFF, scan 2 réactif | 01/03/1970 | 617 092 | 266 465 | 40 / 63 | `reference_seed42_r0.log:1685` |
| OFF, scan 1 principal | 15/10/1971 | 6 699 095 | **1 428 610** | 41 / 318 | `reference_seed42_r0.log:16381` |
| OFF, somme des deux scans terminés | — | **7 316 187** | **1 695 075** | Compteurs de scans, pas sites physiques distincts | Deux lignes précédentes |

Ainsi, les **4,165 M** des seuls calc PCAL-02 représentent **2,46 fois**
les **1,695 M** de recherche de sites publiés par les scans terminés de
référence ; le compteur PCAL plus large dépasse déjà **3,28 fois** ce
montant. Les périmètres diffèrent : PCAL comprend admission/anticipation et
émissions selon le compteur, `ops_sites` couvre la recherche normale, et
`total_ops` comprend aussi les paires et leur économie. **Aucun de ces
ratios n'est une économie causale d'opcodes.** Ne pas additionner les
sous-compteurs C121 ou les deux émissions de chaque bilan à ces totaux.

**Limite précise du bras ON :** son scan 1 ne publie aucun `AIR_PLAN_PERF`
dans ce journal, alors que `air_cat_scan` tourne encore au 30/12/1972
(:29435). La recherche déjà prouvée en janvier ne vaut donc pas zéro opcode,
mais son coût cumulé complet n'est pas récupérable dans ces seuls bilans.
Le coût ON connu de 298 428 est celui du scan réactif seulement. Ne pas
substituer le total OFF au total ON manquant. Les panneaux `OA|`/compteurs
JSON donnent un coût de planification **réparti par projet tenté**
(`projects.nut:445`, `task_air.nut:235–247`), pas un compteur complet de
balayage ; leurs 4 579 799 ON / 7 837 965 OFF ne comblent pas ce manque.

Le levier pertinent est donc **avancer ou rendre moins cher le balayage
existant**, en réutilisant son résultat et ses reprises, plutôt que maintenir
une seconde géométrie privée qui arrive après lui. Pour ces trois villes,
les sites sont déjà trouvés les 3–4 janvier : avancer leur géométrie ne peut
à lui seul expliquer les poses d'août, novembre et février suivant. Le canal
à mesurer ensuite serait l'évaluation/publication des paires et leur
financement ; cette autopsie n'attribue pas toute l'attente à un seul canal.
Aucune modification de ces mécanismes ni nouveau banc dans cette reprise.

### Pourquoi encore 34 `worker_expired` ?

**Les 34 portent `cause=ttl`, zéro `epoch`, `year`, `engine` ou `reset`.**
Les six autres stale sont `ahead_not_next cause=none`. Le correctif de b
sur les invalidations globales fonctionne sur cette observation ; ce n'est
plus la cause des pertes de stock.

Le TTL reste **90 jours depuis la demande**, y compris attente en file et
affinage après le premier ready (`pcal02_air_sites.nut:52–56`, :90–94).
Le worker prend la première entrée non terminée par population, après le
curseur d'anticipation (:448–459), et enlève au plus une entrée expirée par
appel. L'expiration peut être constatée tard si une entrée moins prioritaire
n'est pas inspectée : **24 à 90 jours, 2 à 91, 5 à 92, 2 à 95 et 1 à 137**.
Exemple : ville 34, id 10, évincée le 10/07/1970 à 137 jours (:4556),
9 406 opcodes de géométrie perdus ; dernière progression le 06/04. Ce retard
de nettoyage ne prolonge pas sa validité pour le consommateur.

| État observé avant éviction TTL | Entrées | Somme `prepared_ops` évincée |
|---|---:|---:|
| Site prêt, recherche terminée | 12 | 744 632 |
| Site prêt, recherche encore en cours | 1 | 75 140 |
| Recherche terminée sans site | 13 | 948 610 |
| Recherche commencée mais sans site prêt | 4 | 138 145 |
| Géométrie jamais commencée | 4 | 0 |
| **Total** | **34** | **1 906 527** |

La classification utilise le dernier calc antérieur à chaque stale, par
**ID**, avec `ready/done/valid`, et `prepared_ops` du stale ; les quatre
entrées à zéro n'ont aucun calc de progression. Ce proxy géométrique n'est
pas à ajouter aux 4,165/5,564 M ci-dessus. Répartition des évictions :
18 **9**, 34 **8**, 23 **5**, 19 **4**, 22 **4**, 38 **2**, 24 **1**, 10 **1**.

Deux causes structurelles expliquent la répétition : aucune nouvelle
consultation du finder après ready dans le scan déjà muni de ses sites,
et l'anticipation qui redemande les mêmes villes non desservies après une
expiration, sans savoir que leurs sites existent dans le lot C78. Les
recherches terminées vides sont également redemandées après le TTL. Les
villes plus petites attendent derrière la première recherche par population ;
quatre demandes expirent même sans géométrie. Allonger le TTL ne crée pas
le consommateur absent de ce cycle et ne résout pas cette duplication.

En outre, « prêt un jour, construit plus tard » ne garantit pas une entrée
fraîche à la pose : pour **38**, id 7 prêt le 24/03 expire le 04/04, bien
avant le 09/08 ; pour **23**, le dernier stock prêt avant la pose (id 20,
06/12/1970) expire le **01/02/1971**, huit jours avant sa pose. Pour **24**,
id 18 est bien prêt le 11/10, terminé le 01/11 et non expiré à la pose du
18/11 : le plan conservé l'ignore néanmoins. Les **38 jours** entre ce
premier ready et `AIR_BUILD` sont une avance de disponibilité observée,
**pas un `lead_days` d'ancre consommée**, puisqu'il n'y a eu aucun hit.

### Décision et validation de cette reprise

Le JSON confirme deux duels complets et sains, quatre trimestres valides
terminaux, **`diagnostic_only`**, pas d'échantillon d'adoption : Opex passe
de **2 492 048 à 2 432 110 £/an**, delta **−59 938 £/an** ; valeur de
4 860 385 à 4 406 390 £ (**−9,34 %**, tension avec la garde −5 %).
Une seule graine avec journal et coût ON supplémentaire ne qualifie ni un
gain ni un rejet économique général. **Aucune porte ni adoption.**

Modification documentaire uniquement : ce rapport et l'entrée PCAL-02 de
`docs/taches.md`. **Aucun hash rebasé dans cette reprise** : sources et
contrats inchangés ; les rebases historiques restent explicites plus haut.
SHA-256 conservés : `pcal02_air_sites.nut`
`fa61665352fdfceb3ce124f9b618162a594561c7a035a5f225d4430326f9d839` ;
`po01c_generators.nut`
`4457ef28548d3c14854e260d146a776df100e1900a95ccebee1ad90af966c422`.
Le générateur `sweeps/po01c_generate.py` produit exactement la copie livrée,
vérifié sans réécriture ; les dix projections OFF restent exactes et le
défaut reste 0 aux quatre difficultés.

Validation demandée : depuis `sweeps/`,
`python3 -m unittest discover -p 'test_*.py'`, `TMPDIR` sous le worktree :
**2 459 tests en 27,164 s, OK**, 9 ignorés (mêmes dépendances/fixtures que
précédemment), 2 échecs attendus. Sortie locale ignorée :
`results/pcal02_trace_c_unittest_20261025.log`. `git diff --check` sans
diagnostic. Aucun moteur, Docker, partie, écriture hors worktree,
configuration Git, push ou merge ; aucun changement de RAIL-LONG-EARLY-1,
AIR-FLOTTE-1, C115 ou IDLE-1. Commit local demandé, sans publication.
