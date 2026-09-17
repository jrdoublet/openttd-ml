# Étape 06 — Sélection de portefeuille

- **SHA revu** : `c694bea` (HEAD au moment de la revue)
- **Modèle / effort prévus** : Opus 5 / xhigh
- **Périmètre** : `ai/OpexAI/projects.nut` — 2 149 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

G1 : borne du branch-and-bound non valide, élection modale avant test de capital, objectif en
revenu et non en profit, fenêtre `capitalCeiling` figée. `biasPct` 170/121 = surcoûts mesurés.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

**Configuration de référence des constats ci-dessous** (défauts `info.nut`, qui écrasent les
valeurs de `globals_*.nut` puisque `OpexLoadSettings()` s'exécute depuis `Start()`, après le
chargement des fichiers) : `portfolio_cache = 1` (**adopté**, `info.nut:2685-2691`),
`capital_calibration = 1`, `project_top_k = 64`, `portfolio_max_batch = 1`,
`staged_bootstrap = 1`, `clean_density_score = 1`, `pricing_road_ops = 1`,
`fleet_portfolio = 1`, `air_portfolio = 1`, `feeder_portfolio = 1` ; et à 0 :
`portfolio_floor_pct`, `portfolio_fresh_budget`, `portfolio_dynamic_batch`, `tension_scoring`,
`shadow_pricing`, `air_early_slot`, `rail_prequote`, `c49_variable_denominator`,
`c48_indexed_regeneration`, `c48_index_shadow`.

Conséquence structurante, à garder en tête pour lire tout ce qui suit : le chemin vivant est
`OpexBuildProjects` (régénération complète, au moins mensuelle, `scheduler_tasks.nut:35-66`) +
`OpexIncrementalUpdateProjects` (après chaque chantier, `task_projects.nut:874-877`).
`OpexReselectProjects` et `OpexDynamicBatchReselect` ne sont atteignables que sous
`portfolio_fresh_budget` ou `portfolio_dynamic_batch`, tous deux à 0 — ils ne sont pas morts,
mais aucun banc au défaut ne les exécute.

## Constats

### 06.1 — Quatre balayages complets du vivier par passe, dont deux dont le résultat est jeté au défaut        [gravité : P1]
`projects.nut:623-631` · `projects.nut:636-648` · `projects.nut:757-763` — `OpexProjectSelectAffordable`
parcourt `alternatives` une première fois pour calculer `bestProfit` en appelant
`OpexProjectFinanceCapital(project)` sur chaque élément (l. 625), **puis seulement** teste
`if (PORTFOLIO_FLOOR_PCT > 0 && bestProfit > 0)` (l. 629). Au défaut `portfolio_floor_pct = 0`
ce premier balayage entier est intégralement perdu. Le second balayage (l. 636-648) rappelle
`OpexProjectFinanceCapital` **deux fois de plus** sur chaque projet finançable (l. 637 pour le
test, l. 644 pour le dénominateur de `fundScore`) au lieu de garder le résultat dans un `local`.
Enfin `OpexProjectsStampSelectionStats` (l. 757-763, appelée inconditionnellement depuis les trois
chemins : l. 842, 1553, 2111) refait un balayage complet avec un appel de plus par projet, pour
`stats.minCapital`, qui n'est lu qu'à la ligne 796 et seulement quand `funded.len() == 0`.

Ce que le code prétend faire : le commentaire d'en-tête (l. 9) annonce « la passe de capital est une
approximation gloutonne bornée » — c'est-à-dire bon marché.

Conséquence observable : `alternatives` n'est pas un top-K, c'est le vivier **entier** — l. 2036
et 2047 poussent `rail.candidates` et `road.candidates` en totalité (et non `rail.best`, borné à
`TOP_K = 20`), plus tous les plans air/eau/flotte/subvention. `OpexProjectFinanceCapital` fait de
l'ordre de 10 tests `in` et lectures de table par appel. À quelques milliers d'alternatives, la
sélection paie donc plusieurs dizaines de milliers d'opcodes par passe, pour un budget de l'ordre
de 10 000 par tick (`ai/OpexAI/CLAUDE.md`, « le budget d'opcodes est une ressource de flux »). La
mesure est déjà instrumentée et publiée : `stats.selectionOpcodes` (l. 823, 1528, 2089) et le champ
`sel_ops` du journal VIVIER (l. 716) — le chiffre existe, il n'a simplement jamais été confronté à
ce que la fonction fait réellement. Deux des quatre balayages sont supprimables sans changer un
seul résultat de sélection, ce qui en fait un correctif à comportement strictement identique.

### 06.2 — Le classement final est un ratio, alors qu'un seul projet est construit par passe        [gravité : P1]
`projects.nut:644` · `projects.nut:606` · `projects.nut:2083` — la clé de tri est
`fundScore = OpexProjectScore(profitAnnual, OpexProjectFinanceCapital(project))`, soit
profit annuel **par livre de capital**. Le commentaire l. 606 le dit honnêtement (« le profit par
livre de capital réellement mobilisable »). Mais chaque projet est testé individuellement contre
le budget **entier** (l. 637), et `PORTFOLIO_MAX_BATCH = 1` (`globals_post.nut:107`,
`info.nut` easy_value 1) fait que `_tryBuildProjects` ne bâtit qu'un seul projet par passe, en
descendant `best` par rang.

Ce que le code prétend faire : `info.nut` déclare « meilleur ROI par origine/destination, puis
revenu maximisé sous contraintes de capital et d'opcodes », et l'en-tête de `projects.nut` (l. 6)
« maximiser le revenu annuel par livre immobilisée **et remplir le budget disponible** ».

Conséquence observable : pour un choix unique et indivisible sous contrainte de capital,
l'argmax du ratio n'est pas l'argmax du profit. Une ligne à 45 k£ / 9 k£ de profit (ratio 200)
passe devant une ligne à 280 k£ / 50 k£ de profit (ratio 178) alors que les deux sont finançables
et qu'une seule sera bâtie — c'est **littéralement l'erreur que le commentaire l. 591-596 dit
avoir corrigée** en supprimant le sac à dos (« à 300 k£ de budget, le solveur préférait
{3 × 100 k£ / rev 20k} à {1 × 280 k£ / rev 55k} : le meilleur projet était finançable et n'était
jamais construit »). Le remplacement du sac à dos a changé l'objectif (revenu → profit) mais a
conservé la forme ratio, donc conservé le biais *cheap-first* pour la seule décision qui compte.
Le garde-fou prévu pour ça — le plancher de profit absolu documenté l. 609-622, dont le même
commentaire chiffre la portée : « −24,4 % de valeur et −30,7 % de profit annuel » pour le tri au
seul ratio — est `PORTFOLIO_FLOOR_PCT`, **à 0 par défaut** (`info.nut` easy_value 0), c'est-à-dire
inerte : « à 0 il reproduit exactement le comportement mesuré ci-dessus ».

Réserve explicite : per `ai/OpexAI/CLAUDE.md`, un défaut à 0 peut signifier « hypothèse banquée et
rejetée ». Le journal doit trancher si `portfolio_floor_pct` a été banqué au banc officiel avant
d'agir. Mais l'asymétrie logique — classer sur un ratio pour un choix unique — reste vraie quel que
soit le verdict du banc, et c'est elle qui est le successeur direct du constat « le code ne classe
pas sur ce qu'il prétend classer ».

### 06.3 — `byOpcodes = funded` : la seconde contrainte annoncée en tête de fichier n'existe pas        [gravité : P2]
`projects.nut:2113` · `projects.nut:1555` — `local byOpcodes = funded;` puis `best = byOpcodes`
(l. 2128, 2140, 1568). Aucun tri n'a lieu : le nom de la variable décrit une opération supprimée.

Ce que le code prétend faire : l'en-tête du fichier (l. 5-7) annonce deux contraintes « dans cet
ordre : 1. capital […] ; 2. calcul : ordonner les projets financés par revenu annuel / opcodes
attendus ».

Conséquence observable : `opcodeScore` est calculé pour chaque projet aux quatre fabriques
(l. 340, 399, 435, 465) et n'est lu **nulle part** pour ordonner quoi que ce soit — seulement
publié dans les panneaux `IP|` (`task_rail.nut:232`, `task_road.nut:185`, `task_air.nut:391`,
`task_water.nut:37`). Les deux longs commentaires qui justifient la précision de `expectedOps`
(l. 298-301 pour le rail, l. 308-315 pour la route, « la route défavorisée **au second tri** »)
argumentent sur un tri inexistant. `expectedOpcodes`, lui, reste lu par `tension.nut` (l. 282, 465,
568, 612) — donc seul `opcodeScore` est du calcul mort, pas `expectedOps`.

### 06.4 — `selectedCapital` et `capitalRemaining` décrivent un portefeuille infaisable        [gravité : P2]
`projects.nut:2091-2100` · `projects.nut:829-840` · `projects.nut:1536-1545` — après la sélection,
le code somme `OpexProjectFinanceCapital` sur les **64** projets retenus et pose
`capitalRemaining = capitalBudget - selectedCap`, borné à 0.

Ce que le code prétend faire : le commentaire l. 807-809 exige que « IG| et IB| décrivent la même
solution que `best` ». L'en-tête l. 6 parle de « remplir le budget disponible ».

Conséquence observable : chaque projet de `best` a été testé **seul** contre le budget entier
(l. 637) ; leur somme n'a aucune raison d'y tenir et la dépasse en pratique d'un ordre de grandeur.
`selectedCapital` est publié tel quel dans le panneau `IB|` (`task_projects.nut:905`,
`scheduler_tasks.nut:306`), qui est un canal de mesure de banc : il ne mesure donc ni le capital
engagé, ni le capital qui sera engagé. `capitalRemaining` est écrit sur les trois chemins mais
**n'est lu nulle part** dans le dépôt : il vaut 0 en permanence et alimente le champ `remaining=`
du journal VIVIER (l. 715), qui est donc constant.

### 06.5 — Le budget de capital est lu 230 lignes avant d'être utilisé, avec la découverte aérienne entre les deux        [gravité : P2]
`projects.nut:1850` · `projects.nut:2083` — `local capitalBudget = OpexAvailableCapital();` est
évalué après la génération rail et route, puis utilisé comme seuil de finançabilité à la ligne 2083.
Entre les deux : `OpexAirPlans` (l. 1858, plus un second appel de repli l. 1883) et `OpexWaterPlans`
(l. 1914).

Ce que le code prétend faire : `capital.nut:44-46` commente `OpexAvailableCapital` par « cette
valeur doit **toujours être relue après une dépense** : la caisse, le reliquat d'emprunt et la
réserve peuvent tous avoir changé ».

Conséquence observable : le commentaire de `scheduler_tasks.nut:570-575` chiffre le balayage aérien
à « ~21 jours de temps de jeu » par passage. Le portefeuille est donc élu contre une trésorerie
vieille de plusieurs dizaines de jours de jeu, pendant lesquels les recettes tombent, l'entretien
est prélevé et `OpexCashReserve()` (qui dépend de la flotte) peut changer. Le seuil sert à la fois
au filtre de finançabilité (l. 625, 637, 655) et au panneau `IB|`. Le décalage joue dans les deux
sens : projets écartés comme infinançables alors que la caisse a monté, projets retenus qui ne le
sont plus au chantier. À noter : le chemin incrémental, lui, relit bien le capital juste avant la
sélection (`task_projects.nut:875-877`) — l'asymétrie est entre les deux chemins.

### 06.6 — `OpexIncrementalUpdateProjects` jette les projets `fleet` sans toujours les régénérer        [gravité : P2]
`projects.nut:1398` · `projects.nut:1462` — l'étape 1 écarte inconditionnellement tout projet de
flotte du vivier recyclé (`if (p.mode == "fleet") continue;`), au motif, écrit l. 1397, que « la
flotte et les feeders sont régénérés frais ci-dessous ». Mais l'étape 3 est conditionnée :
`if (FLEET_PORTFOLIO && fleetPlan != null)`.

Conséquence observable : quand l'appelant passe `fleetPlan = null`, les projets de flotte
disparaissent définitivement de `candidateGroups` sans remplacement. Le cas se produit à
`task_projects.nut:864-877` : `fleetPlan` n'est calculé que si `!PORTFOLIO_DYNAMIC_BATCH`, or la
branche `PORTFOLIO_CACHE` de la ligne 877 reste atteignable sous `portfolio_dynamic_batch = 1`
quand `batchBuilt == 0` et `hadAbandons` est vrai. Au défaut (`portfolio_dynamic_batch = 0`) le
bug est inerte ; il ne mord que dans le **bras expérimental**, ce qui est le pire endroit : il
biaise silencieusement l'A/B qui doit trancher ce réglage (C34.2 arbitre justement les achats
d'avion contre les lignes neuves — les retirer du vivier annule l'arbitrage qu'on mesure).
Même asymétrie, un cran plus bas, l. 1405 (`AIR_EARLY_SLOT && p.mode == "air"` → skip) contre
l. 1483 (régénération gardée par `AIR_PORTFOLIO`) : la combinaison `air_early_slot = 1` +
`air_portfolio = 0` viderait le vivier aérien.

### 06.7 — `knapsackExact` et `knapsackNodes` : deux scories du sac à dos, publiées comme mesure        [gravité : P2]
`projects.nut:821-822` · `projects.nut:1353-1354` · `projects.nut:1526-1527` ·
`projects.nut:1933` · `projects.nut:2087-2088` — les cinq sites écrivent la même paire de
constantes : `knapsackNodes = 0`, `knapsackExact = true`. Aucun solveur ne les calcule plus :
il n'existe **aucun** branch-and-bound ni sac à dos dans le dépôt (vérifié par lecture de
`OpexProjectSelectAffordable`, seul sélecteur, et par recherche de `knapsack|branch|bound` sur
les 34 `.nut`).

Ce que le code prétend faire : `knapsackNodes` est resté dans la structure de statistiques comme
si un compteur de nœuds l'alimentait, et `knapsackExact` est publié comme cinquième champ du
panneau `IG|` sous la forme `(knapsackExact ? 0 : 1)` (`task_projects.nut:892`,
`scheduler_tasks.nut:296`), au-dessus d'un commentaire de 8 lignes qui explique pourquoi ce champ
est indispensable : « `maxNodes = 2000` pour n = 64 fait tronquer la recherche couramment : sans ce
champ, on ne peut pas distinguer "le solveur a prouvé l'optimum" de "il a épuisé son budget de
nœuds" ».

Conséquence observable : le champ 5 de `IG|` vaut 0 sur toutes les parties, de toutes les graines,
depuis la suppression du sac à dos. Un dépouillement de banc qui lirait ce champ conclurait
« optimum prouvé à chaque passe » alors que rien n'est prouvé et que le mot « optimum » n'a plus
d'objet. C'est la scorie `portfolio_v2` demandée par le plan — et la plus dangereuse, parce
qu'elle est branchée sur un canal de mesure. (L'émission du panneau et son commentaire périmé sont
hors périmètre : étape 13.)

### 06.8 — `poolInfundable` et `modeReplaced` : compteurs jamais incrémentés, l'un publié        [gravité : P3]
`projects.nut:1347` · `projects.nut:1933` · `projects.nut:714` — `poolInfundable` est initialisé à
0 aux deux constructeurs de `stats` et n'est incrémenté nulle part, mais il est publié par
`OpexLogVivier` sous l'étiquette `infundable=`. Idem pour `modeReplaced` (l. 1346, 1930), résidu de
l'ancienne élection modale d'avant `portfolio_v2` (le remplacement d'une alternative par une autre
n'existe plus : `OpexProjectRememberAll` empile, l. 492). Conséquence : le journal de décision
affiche un zéro constant présenté comme une mesure du vivier écarté faute de capital — cette
information existe pourtant (`budgetRejected`, l. 2086), sous un autre nom et avec un autre sens.

### 06.9 — `generationCapitalBudget` n'est jamais rafraîchi par les chemins incrémentaux        [gravité : P3]
`projects.nut:2129` — le champ n'est posé que par `OpexBuildProjects`, et seulement dans le retour
gardé par `PORTFOLIO_FRESH_BUDGET || PORTFOLIO_CACHE`. Ni `OpexReselectProjects` (l. 838-840) ni
`OpexIncrementalUpdateProjects` (l. 1570-1572) ne le mettent à jour, alors que tous deux
réécrivent `capitalBudget`.

Conséquence observable : `task_projects.nut:368` le lit comme `initialBudget` et le publie dans le
panneau `FB|` (champ 3) comme « budget de la génération ». Sous `portfolio_cache = 1`, la valeur
survit à un nombre arbitraire de passes incrémentales : `FB|` compare donc la trésorerie du jour à
celle de la dernière régénération **complète**, pas à celle du cycle. Inerte au défaut
(`portfolio_fresh_budget = 0`), mais c'est exactement la fenêtre de capital visée par le point 4
de l'enjeu — voir la section « Vérifié, n'est PAS un bug » pour le mécanisme qui, lui, fonctionne.

### 06.10 — `emptyCause` est calculé sur les listes de génération, périmées dans le chemin incrémental        [gravité : P3]
`projects.nut:1553` · `projects.nut:765-768` — l'appel incrémental passe l'objet `projects`
complet à `OpexProjectsStampSelectionStats`, qui y lit `projects.rail.candidates.len()`,
`projects.road.candidates.len()`, `projects.airPlans.len()` et `projects.waterPlans.len()`. Or
`OpexIncrementalUpdateProjects` ne réécrit ni `projects.rail`, ni `projects.road`, ni
`projects.airPlans` (l. 1567-1572) : ces listes datent de la dernière régénération complète,
jusqu'à un mois plus tôt.

Conséquence observable : le diagnostic `emptyCause` (l. 780-802), dont tout le rôle est d'expliquer
pourquoi `funded` est vide, arbitre entre `stage_empty` et `empty_pool` (l. 791-794) sur des
compteurs qui ne décrivent pas la passe en cours. `this._ranked = this._projects.rail` après chaque
appel incrémental (`task_projects.nut:881`, `scheduler_tasks.nut:593`) hérite de la même péremption.

### 06.11 — L'économie des candidats recyclés n'est jamais recalculée        [gravité : P3]
`projects.nut:1390-1414` — l'étape 1 réinjecte les projets rail et route du vivier **tels quels**.
`OpexIncrementalCandidateStillValid` (l. 1410) vérifie la topologie (doublon de ligne, origine
desservie, site constructible, paire abandonnée) mais aucun champ économique :
`profitAnnual`, `capital`, `budgetCapital` et `roi` restent ceux calculés à la génération. Seuls
les feeders (étape 2), la flotte (étape 3) et l'aérien (étape 4) sont régénérés frais.

Conséquence observable : `fundScore` est recalculé à chaque passe (l. 644) mais à partir d'entrées
gelées ; un candidat rail peut être classé pendant tout un mois sur une économie établie avant
qu'un concurrent ne se pose sur la même paire ou qu'un rafraîchissement de catalogue ne change le
matériel retenu. La péremption est bornée à un mois par la régénération mensuelle
(`scheduler_tasks.nut:35`), ce qui rend le constat P3 et non P2 — mais l'asymétrie
« air régénéré / rail gelé » favorise structurellement le mode dont les chiffres sont frais.

### 06.12 — Le pré-devis rail P1.1 s'applique à un classement *antérieur* au test de capital        [gravité : P3]
`projects.nut:237` · `projects.nut:1817` — `OpexPrequoteRailCandidates` itère sur `rail.best`,
c'est-à-dire le top-`TOP_K` (20) issu de `OpexTopK`, un classement au ratio effectué pendant la
génération, et s'arrête à `RAIL_PREQUOTE_MAX_CANDIDATES = 2` (`main.nut:36`).

Ce que le code prétend faire : le commentaire l. 228-231 annonce « pour les quelques meilleurs
rails du préfiltre, on peut payer […] le même devis `AITestMode` que le constructeur **AVANT
l'élection** », et celui de `OpexProjectFinanceCapital` (l. 195-196) que « P1.1 doit remplacer le
rail par un devis physique avant l'élection ».

Conséquence observable : les deux candidats qui reçoivent un devis réel — et échappent donc au
×1,7 — sont désignés par un préclassement au ratio qui ne connaît pas la contrainte de capital,
tandis que la sélection, elle, aplatit **toutes** les alternatives (l. 2036). C'est le dernier
reste de forme « élire d'abord, financer ensuite » dans le fichier. Inerte au défaut
(`rail_prequote = 0`) ; à documenter avant que le chantier P1.1 ne l'active.

## Vérifié, n'est PAS un bug

**Point 1 de l'enjeu — la borne du branch-and-bound : le constat est caduc, pas corrigé.** Il n'y a
plus de branch-and-bound, ni de sac à dos, ni de borne, nulle part dans le dépôt. Le seul sélecteur
est `OpexProjectSelectAffordable` (`projects.nut:607-668`), un test de finançabilité projet par
projet suivi d'une insertion ordonnée bornée (`OpexProjectInsert`, l. 692-705). Il n'y a donc plus
rien à prouver ni à borner : la question d'optimalité qui se pose aujourd'hui est celle du 06.2
(ratio contre profit absolu pour un choix unique), pas celle d'une borne supérieure. Ne pas
rouvrir le constat sous sa forme de 2026-09-01. Seules subsistent les scories du 06.7.

**Point 2 — l'élection modale : corrigé, et vérifié ligne à ligne.** `OpexProjectRememberAll`
(l. 482-493) empile **toutes** les alternatives d'un couple dans `winners[key]` au lieu d'en élire
une (`winners[key].push(project)`, l. 492 ; aucun comparateur, aucun `OpexProjectModeBetter` dans
le fichier). Les trois chemins aplatissent ensuite le dictionnaire entier avant la sélection
(l. 2078-2083, 1516-1521, 816-819), et c'est bien le test de capital de la ligne 637 qui tranche
le premier. Le commentaire l. 477-481 décrit fidèlement ce que fait le code.

**Point 3 — l'objectif : corrigé.** `fundScore` (l. 644) et le plancher `bestProfit` (l. 626)
lisent `profitAnnual`, pas `revenueAnnual`. Ce qui reste en revenu est identifié et sans effet sur
le classement : `budgetScore`/`opcodeScore` (l. 339-340, 398-399, 434-435, 464-465) et le
départage d'égalité de `OpexProjectInsert` (l. 700, `prior.revenueAnnual >= project.revenueAnnual`,
qui ne joue qu'à `fundScore` strictement égal). **Une réserve à signaler plutôt qu'un bug** :
`OpexLogPortfolioRank` publie `score=` en lisant `budgetScore` (l. 51 et 94) quand
`tension_scoring` et `shadow_pricing` sont à 0 — c'est-à-dire au défaut. Le journal
`PORTFOLIO_RANK` affiche donc un score en **revenu** par livre, alors que le rang affiché a été
produit par `fundScore`, en **profit** par livre. Deux projets peuvent y apparaître dans un ordre
qui contredit le champ `score`. `portfolio_log` étant à 0 au défaut, c'est une gêne de diagnostic,
pas un défaut de comportement — mais quiconque relit un `PORTFOLIO_RANK` doit le savoir.

**Point 4 — la fenêtre de capital : le mécanisme fonctionne, sous un autre nom.** `capitalCeiling`
n'existe plus dans `projects.nut` ; sa seule occurrence dans le dépôt est un paramètre de
`OpexTensionMacroRegime` (`tension.nut:319`), fonction qui n'est appelée de nulle part. La fenêtre
qui joue réellement est celle de `scheduler_tasks.nut:15-31` : `stale = gainOk && doubleOk` compare
`OpexAvailableCapital()` à `this._projects.capitalBudget`. Or `OpexIncrementalUpdateProjects`
**réécrit bien** `projects.capitalBudget` à chaque passe (`projects.nut:1570`), avec une valeur
relue juste avant (`task_projects.nut:875`). La référence avance donc, et le déclencheur
« capital » de régénération complète n'est pas gelé par `portfolio_cache`. Le constat du 09-06 ne
se reproduit pas sur ce code. Ce qui reste figé est le champ voisin `generationCapitalBudget`
(constat 06.9), inerte au défaut.

**Point 5 — `portfolio_v2` seul chemin : confirmé.** Aucun sélecteur concurrent, aucune branche
morte de sélection. Ce qui subsiste et qu'il ne faut PAS signaler comme legacy :
`OpexLegacyCandidateStillValid` (l. 890-1067) n'est pas du code mort — c'est la branche **par
défaut** de `OpexIncrementalCandidateStillValid` (l. 1273), puisque `c48_indexed_regeneration = 0` ;
la variante indexée (l. 1070) et le miroir d'assertion (l. 1257-1266) sont les branches inertes. De
même `OpexLogPortfolioRankWithTension` (l. 61) n'est pas un doublon : `tension.nut:35` le substitue
à `OpexLogPortfolioRank` par réassignation du symbole global. Les scories réelles de `portfolio_v2`
sont les constats 06.3, 06.7 et 06.8, pas ces trois-là.

**Point 6 — `biasPct` = 170 / 121 (`projects.nut:205-206`) : constantes assumées, à ne pas
toucher.** Le commentaire l. 188-197 donne l'origine de chaque chiffre (rail :
`docs/opexai_prix_rail_terrain.md` ; route : mesure `road_cost_probe` du 2026-09-08, 5 graines × 6
ans, 4 812 tentatives), le statut (repli, pas devis) et la sortie prévue (P1.1). Le code est par
ailleurs cohérent avec ce qu'il annonce : le surcoût ne s'applique qu'à la part travaux
(`modelCapital`, l. 210, 221), la part non-construction (marge, capital immobilisé) est préservée
à l'identique (l. 221-225), et un devis réel présent sur le candidat court-circuite le facteur
(l. 212-223). Conforme à `ai/OpexAI/CLAUDE.md`. **À ne pas signaler non plus** : le fait que l'air,
l'eau et la flotte ressortent à ×1,0 (l. 207) n'est pas un oubli — l'air porte sa propre marge en
dur (l. 417-419) et un achat d'avion a un prix catalogue exact.

**Déclarations dupliquées en tête de fichier** : `PROJECT_TOP_K` (l. 24),
`PROJECT_TOP_K_DYNAMIC` (l. 27) et `CLEAN_DENSITY_SCORE` (l. 38) sont réassignés par
`settings.nut` (l. 123, 124, 323) au démarrage, puisque `OpexLoadSettings()` s'exécute depuis
`Start()`, après le chargement de tous les `require`. L'ordre de chargement ne décide donc rien
ici et la branche `if (!CLEAN_DENSITY_SCORE)` (l. 327-331) est inerte par **réglage** (défaut 1),
pas par ordre de chargement. Le triple `CLEAN_DENSITY_SCORE` est déjà au périmètre de l'étape 1.

**`OpexProjectInsert`** (l. 692-705) : l'insertion bornée est correcte, y compris le cas limite où
le projet inséré en queue est immédiatement retiré par `best.pop()`.

## Hors périmètre, à relire ailleurs

- **Étape 3** (`tension.nut`) — `OpexTensionMacroRegime` (`tension.nut:319`) est le seul porteur
  restant de `capitalCeiling` et n'est appelée de nulle part : le plan l'a déjà fléchée comme code
  mort. Vérifier au passage que la substitution globale `::OpexLogPortfolioRank =
  OpexLogPortfolioRankWithTension` (`tension.nut:35`) est bien exécutée inconditionnellement au
  chargement — c'est elle qui décide laquelle des deux fonctions de `projects.nut` vit.
- **Étape 13** (`task_projects.nut`) — l'émission des panneaux `IG|` et `IB|`
  (`task_projects.nut:883-906`, dupliquée mot pour mot en `scheduler_tasks.nut:287-308`) publie les
  champs dénoncés aux constats 06.4 et 06.7, sous un commentaire de 8 lignes qui décrit un solveur
  supprimé (`maxNodes = 2000`, budget de nœuds, optimum prouvé). Le commentaire est à réécrire en
  même temps que les champs. Y relire aussi `_tryBuildProjects` : c'est lui qui matérialise
  `PORTFOLIO_MAX_BATCH = 1`, donc la moitié du constat 06.2, et lui qui alimente `fleetPlan = null`
  du constat 06.6 (`task_projects.nut:864-877`).
- **Étape 2** (`capital.nut`) — `OpexAvailableCapital()` inclut le reliquat d'emprunt mobilisable
  (`capital.nut:48-56`) : « finançable » au sens de `projects.nut:637` signifie donc « finançable
  après tirage d'emprunt », et le tirage effectif se fait ailleurs (`OpexTryReborrow`). Vérifier que
  les deux définitions coïncident, sinon le filtre de finançabilité du portefeuille promet un
  capital que le constructeur ne peut pas lever.
- **Étapes 4 et 5** (`candidates.nut`) — la taille de `alternatives`, qui conditionne le coût du
  constat 06.1, est fixée par la génération : `projects.nut:2036` et 2047 consomment
  `rail.candidates` / `road.candidates` **entières**, pas les top-K. Si un plafond doit être posé,
  c'est là qu'il se discute, pas dans le sélecteur.
- **Étape 12** (`events.nut`) — le constat G2 du plan (« l'invalidation événementielle rafraîchit
  le catalogue mais pas le portefeuille dérivé dans le même mois ») se referme du côté
  `projects.nut` : `_portfolioInvalidated` court-circuite bien la garde mensuelle
  (`scheduler_tasks.nut:35-38`) et mène à `_rebuildProjects`. La question restante est en amont,
  sur ce qui pose le drapeau.

## Passe de clôture — 2026-09-16

La configuration des lignes 20-28 reste la photographie utilisée par la revue du 15 septembre ;
`air_early_slot` a été adopté depuis. Les décisions ci-dessous ont donc été revérifiées sur le
HEAD courant, sans réutiliser de résultat archivé antérieur au 2026-09-09.

- **06.1 corrigé sans changement de classement** : le scan `bestProfit` n'existe plus quand le
  plancher vaut 0, le capital est mémorisé par itération, et `minCapital` n'est calculé que pour
  une sélection vide.
- **06.2 différé** : remplacer le ratio profit/capital par un objectif de profit change le
  comportement économique. Il faut un diagnostic 5×6 puis, si le signal tient, le 20×10 apparié.
- **06.3 corrigé** : les alias `byOpcodes` ont été supprimés ; `best` reçoit directement
  `funded`.
- **06.4 non modifié** : `selectedCapital` est aussi lu par `task_town.nut` sous
  `GROWTH_YIELDS`, et `IB|` a un second émetteur dans `scheduler_tasks.nut`. Une correction
  locale changerait potentiellement le jeu et laisserait les deux canaux incohérents.
- **06.5 différé** : relire le budget après la génération modifie l'admission au portefeuille et
  doit être évalué comme variante comportementale.
- **06.6 corrigé sur le bras expérimental** : un projet flotte en cache n'est retiré que si un
  `fleetPlan` frais est effectivement disponible pour le régénérer.
- **06.7 corrigé côté source de vérité et parseur** : les cinq initialisations de `knapsackExact`
  valent `false`. Le bit IG historique reste émis comme **`selection_not_exact`** ; le parseur ne
  le nomme plus `knapsack_truncated`, notion qui supposerait un solveur B&B encore actif. La clé
  JSON historique `knapsack_truncated` est conservée à `null` pour compatibilité de schéma.
- **06.8 corrigé côté journal** : `VIVIER` ne publie plus `infundable=0`, compteur mort qui
  se lisait comme une mesure. `budgetRejected` reste la métrique réellement alimentée.
- **06.9 conservé** : `generationCapitalBudget` décrit la génération complète d'origine ;
  changer sa sémantique doit être coordonné avec le consommateur `FB|`.
- **06.10 corrigé** : pour distinguer `stage_empty` de `empty_pool`, la passe utilise le
  `modeCandidates` courant au lieu des listes de génération potentiellement vieilles du cache.
- **06.11 et 06.12 différés** : rafraîchir l'économie recyclée ou déplacer le pré-devis rail
  change le classement et exige les bancs comportementaux prévus par la méthode.

## Réconciliation B6 finale — 2026-09-16

M1 a d'abord rendu explicite la différence entre **pool sélectionné** et dépense exécutable :
`selectedCapital` reste inchangé pour préserver `GROWTH_YIELDS`, tandis que
`selectionPoolCapital` et `nextProjectCapital` rendent la mesure honnête et
`IB|` reste rétrocompatible.

Le diagnostic apparié `review_b6_portfolio_causality_paired_5x6.json` établit ensuite :

- **06.2 exposé, non adopté** : 146/501 choix comparables diffèrent du meilleur profit abordable,
  delta contre-factuel moyen +1 742 £/an, médiane 0, max +23 113. Cela ne prouve pas l'effet aval
  d'un nouvel objectif. `portfolio_floor_pct` reste 0 ; la variante 50 % a déjà un 20×10
  post-09/09 défavorable (−4,94 % valeur, 4 V / 16 D).
- **06.5 actif P2** : 630/639 snapshots diffèrent du capital vivant, âge moyen 4,44 j, max 12 ;
  50 événements changent l'abordabilité, 1 203 bascules cumulées. Aucune réactivation silencieuse
  de `portfolio_fresh_budget`.
- **06.11 actif P3** : 139/345 choix incrémentaux utilisent un projet recyclé ; âge moyen 14,36 j,
  max 43. L'erreur économique de péremption n'est pas quantifiée, donc aucun refresh adopté.
- **06.12 dormant** avec `rail_prequote=0`.
- `PORTFOLIO_MAX_BATCH=1` et `portfolio_floor_pct=0` ont été observés partout.

B6 est clos comme chantier P1 : instrumentation et causalité établies, aucun défaut de politique
changé et aucun nouveau 20×10 lancé.

### Clôture 06.5 — budget vivant mesuré puis variante rejetée (2026-09-17)

La reprise finale a d'abord rendu le contre-factuel exact sans changer la politique : sous
`decision_log=1`, `OpexB6LogSelectionCausality` clone les alternatives puis rejoue le **sélecteur
courant** `OpexProjectSelectAffordable` avec `OpexAvailableCapital()` au même instant. Les clones
empêchent le calcul de `fundScore`/`early_slot` de muter le portefeuille réel.

- le full rebuild photographie aujourd'hui le capital à
  `projects.nut:1977-1978`, avant `OpexAirPlans` (`:1986` et repli `:2011`) et
  `OpexWaterPlans` (`:2042`), puis passe encore ce snapshot à
  `OpexProjectSelectAffordable` (`:2212`) ;
- le nouveau diagnostic passif `results/review_b6_065_live_budget_5x6.json` est sain **10/10** :
  620/630 événements ont un budget différent, 69 présentent au moins une bascule
  d'abordabilité, soit 2 695 bascules cumulées ; le sélecteur live change réellement le premier
  projet **41/630** fois ;
- sur ces 41 changements, **39** ont un `profitAnnual` supérieur et **2** inférieur ; delta moyen
  **+25 123,68 £/an**, médiane **+17 322 £/an**, plage −16 623 à +130 030. Le signal local est donc
  réel et suffisait à tester le levier, sans constituer une preuve économique aval ;
- la divergence ne permet toutefois pas un chantier « sans argent » : air
  (`task_air.nut:378-390`), route (`task_road.nut:175-181`), eau
  (`task_water.nut:27-35`) et flotte (`task_projects.nut:179-185`) refont un contrôle de cash
  vivant juste avant construction ; rail précontrôle à `task_rail.nut:216-230` et
  `OpexBuildLine` peut encore rendre `CASH` au dernier instant (`:272-276`).

Le flag existant `portfolio_fresh_budget=1` implémente précisément la variante comportementale
utile sur le code actuel : juste avant les tentatives, il rappelle `OpexReselectProjects`, qui
réaplatit `candidateGroups` et utilise le même `OpexProjectSelectAffordable` avec le capital vivant.
Le 5×6 apparié C66.4 `results/review_b6_065_fresh_budget_c66_4_5x6.json` est complet **5/5** mais
défavorable : `profit_year` variante−référence moyen **−135 528,6 £/an**, médiane −161 563,
V/D/E **1/4/0**, et `company_value` **−27,307 %** en ratio des moyennes. Le verdict protocolaire
reste `diagnostic_only` parce que cinq paires n'ont pas autorité d'adoption ; précisément parce que
le signal est négatif, il **ne justifie pas** de 20×10.

**Décision 06.5 : clos, candidat non adopté.** `portfolio_fresh_budget` reste **0**. Le budget
périmé est bien une cause locale de changement d'élection, mais le rafraîchir à cet endroit dégrade
la trajectoire économique observée ; ne pas réouvrir 06.5 sans mécanisme différent ou fait nouveau.
Après la dernière modification `.nut` d'instrumentation, le smoke C66.3
`results/review_b6_065_final_smoke_2x3.json` passe **2/2**, horizon complet et zéro erreur NoAI.

**06.11** reste également actif mais P3 : 139/345 sélections incrémentales prennent un projet
recyclé, âge moyen 14,36 jours et maximum 43 jours. Le banc mesure l'âge mais pas l'erreur
économique induite ; aucun recalcul de ROI n'est adopté sans mesure dédiée. Le refresh concurrent
audité le 2026-09-17 a été retiré : il mettait `null` les subventions et extensions routières, mais
`OpexIncrementalUpdateProjects` ne régénère ensuite que feeders, flotte et air. Il changeait donc le
vivier par perte de familles, indépendamment de la fraîcheur économique recherchée.

### Clôture diagnostique 06.11 — économie recyclée (2026-09-17)

La mesure dédiée est désormais disponible dans
`results/review_b6_0611_join_resolved_5x6.json` (**10/10 runs sains**, cinq graines × six ans),
sans refresh comportemental. Deux oracles passifs sont utilisés :

- au rebuild complet normal, les objets **réellement recyclés** depuis la génération précédente
  sont comparés au vivier fraîchement généré uniquement quand leur clé stable est unique des deux
  côtés ; les absences/ambiguïtés ne sont jamais imputées ;
- pour le top fret recyclé, l'économie courante est repricée sans modifier l'objet réel puis
  comparée au runner-up sous le même budget et le même score de sélection. Les joins, subventions,
  extensions, feeders et autres familles ne sont ni supprimés ni reconstruits artificiellement.

Sur le chemin incrémental, **136/348** élections prennent un top recyclé, âge moyen **15,74 j**,
maximum **44 j**. Le rebuild fournit 11 100 observations équivalentes `rail_pax` : erreur absolue
de profit moyenne **608,59 £/an**, maximum **6 969 £/an**, mais biais signé moyen seulement
**+51,54 £/an** (frais − cache). Pour les tops fret, **127** événements sont sondés ; 117 sont
repricés exactement, 17 changent de profit, delta moyen **−414,32 £/an**, médiane 0, plage
**−14 570 à +10 321 £/an**.

Le contre-factuel de décision est local mais actionnable : parmi les cas décidables, **108** gardent
le même choix et **6** changeraient (4 inversions de classement, 2 candidats qui ne seraient plus
générés), soit **6/114 = 5,3 %** ; 5 égalités exactes et 8 cas hors oracle restent explicitement
non tranchés. Cela prouve que la péremption économique peut changer une élection, mais ne prouve
ni qu'un refresh général améliore la trajectoire aval, ni qu'il est sûr pour toutes les familles.

**Décision 06.11 : diagnostic clos, correctif général non adopté.** `portfolio_cache` reste actif ;
ne pas réintroduire le refresh rejeté. Un futur correctif comportemental devra préserver exactement
les métadonnées/constructeurs spéciaux et être évalué séparément ; ce 5×6 n'a aucune autorité de
promotion et ne justifie pas de 20×10 en l'état.

Validation après la dernière modification `.nut` d'instrumentation : le smoke Docker C66.3
`results/review_b6_0611_final_smoke_2x3_v2.json` est sain **2/2** (graines 42/100), horizon complet
pour OpexAI et AAAHogEx, sans erreur script/non attribuée. Il conserve explicitement
`air_early_slot=1`, `abandon_gen_filter=1` et `abandon_cooldown_days=365`.
