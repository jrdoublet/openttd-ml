# PCAL-02 — sites d'aéroports préparés dans le reliquat du tick

Conception préalable, 25 octobre 2026. Branche locale `pcal02`, départ propre
`269ec7bcfe13b9960716eb59b3ea6f3c97a7b7de`. Prototype **OFF**, réglage
`pcal02_air_sites=0` aux quatre difficultés. Aucun moteur, Docker, banc,
push ou fusion autorisé par cette tâche. Commit local demandé.

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

Le premier appel reste synchrone sur miss. Après publication du lot courant et
en l'absence de projet AIR immédiatement finançable, les appels suivants au
hook peuvent préparer les **prochaines** générations. Conséquence assumée :
aucune accélération promise du tout premier scan ni des villes jamais demandées.
Le prototype refuse aussi de travailler pendant un worker actif, un lot C78,
ou une reconstruction PO-01c en cours/en attente. Le contrôle de financement
lit les plans AIR publiés et la sélection, avec borne de réserve et marge AIR ; s'il
ne finit pas dans le reliquat, il cède le tick sans commencer de géométrie.
La lecture de `OpexCashReserve` parcourt toute la flotte : elle est exclue du
worker. Celui-ci soustrait `CASH_RESERVE_MIN`, borne inférieure de la réserve
réelle, et utilise le coût minimal d'un avion, même si le plan en propose plus.
Il surestime donc les projets immédiatement finançables et peut refuser du
précalcul utile ; il ne libère pas le worker sur une réserve périmée trop haute.

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

Une entrée est identifiée par ville/type, avion et année, dimensions, époque
d'invalidation et date ; TTL 90 jours depuis la demande, y compris calcul
inachevé et résultat vide. Les invalidations géométriques existantes de tous
les modes et l'échec d'un site invalident le stock par son époque. Les deux
appels actuels à `OpexAirResetSiteCache` sont dans le constructeur et `Start` :
ils vident aussi PCAL-02, donc notamment après Load. Les reprises C78/V278
n'appellent pas ce reset et peuvent lire le stock préparé entre générations.
Les changements de catalogue, d'avion, d'année ou de dimensions interdisent
le réemploi ; les changements externes passent par la revalidation vivante.

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

Fichiers et points d'entrée (numéros de lignes de cette livraison) :

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
petits ; un plan finançable mais devenu non constructible peut bloquer le
worker ; une longue liste de vetos peut épuiser l'admission sans progression ;
invalidations globales conservatrices pouvant rejeter un site encore sain ;
préparation des seuls futurs scans, pas d'accélération promise du premier ;
scans doubles possibles entre stock préparé et cache historique ; profit,
économie **nette** d'opcodes et calendrier de construction non mesurés.
La compilation Squirrel, les suspensions réelles et le roundtrip Save/Load
restent à valider au smoke/harnais autorisés ultérieurement. Aucune partie lancée.

Validation finale effective : **2 445 tests en 26,493 s, OK**,
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
