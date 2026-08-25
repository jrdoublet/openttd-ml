**Question.** Peut-on prédire le profit d'une ligne ferroviaire à partir de ses caractéristiques
de construction, sans simuler la partie ?

**Unité d'observation.** Une tentative de ligne (couple villes × cargo × matériel × nombre de
rames) — construite ou non. Les tentatives ratées ne sont pas jetées : voir modèle hurdle ci-dessous.

**Modèle.** Hurdle à deux étages, pour traiter la censure honnêtement plutôt que la masquer :
1. **Classifieur** — cette ligne est-elle constructible ? Entraîné sur *toutes* les tentatives,
   réussies ou non (le signal vient du panneau posé par l'IA à chaque tentative, voir plus bas).
2. **Régression** — profit conditionnel à la construction réussie. Entraînée uniquement sur les
   lignes effectivement construites.

**Métrique.**
- Étage 1 (classifieur) : F1 sur constructible / non constructible.
- Étage 2 (régression) : MAE sur `company_value` (ou le profit trimestriel `old_economy`, voir
  section VPS ci-dessus), conditionnel à la construction — pas le capital brut (`money`).

**Baseline.**
- Étage 1 : taux de base (proportion de lignes constructibles dans le jeu d'entraînement).
- Étage 2 : `company_value` médiane des lignes construites dans le jeu d'entraînement.

**Protocole de split.** Par graine, jamais par ligne : deux lignes d'une même partie partagent
le monde, la conjoncture et la concurrence.

**Critère de réussite.**
- Étage 1 : battre le taux de base en F1 (marge à fixer avant de voir les résultats).
- Étage 2 : battre la baseline de 20 % en MAE, sur des graines jamais vues.

---

## Notes techniques (Phase 0)

**Source du profit — `old_economy`, pas un delta de `money`.** Le chunk `PLYR.<company>.old_economy`
est une liste de trimestres clos, index 0 = le plus récent, avec les champs `income`, `expenses`,
`company_value`, `delivered_cargo`, `performance_history` (confirmé par inspection directe du
savegame, `sweeps/phase0_explore.py` et `phase0_explore3.py`).

**Piège vérifié en pratique : `len(old_economy)` n'est PAS une clé de trimestre fiable.** Le tableau
est une fenêtre glissante plafonnée à 24 entrées (6 ans) : `len()` augmente de 1 par trimestre
jusqu'à 24, puis reste bloqué à 24 pour le reste de la partie. Un premier essai de dédup sur
`(seed, len(old_economy))` a silencieusement tronqué toutes les séries à 6 ans sur des parties de
10 ans (perte muette des trimestres 25 à ~40, aucune erreur levée). Correctif retenu dans
`sweeps/phase0_plot.py` : dédupliquer sur la **date calendaire réelle** du trimestre clos, déduite
de la date du savegame (`old_economy[0]` correspond toujours au trimestre précédant celui de la
date du savegame — voir `closed_quarter_start()`), pas sur la profondeur du tableau. Robuste
indépendamment de la taille de la fenêtre glissante.

`money` seul est écarté comme indicateur : il inclut `current_loan`, donc un emprunt gonfle `money`
sans rien construire, et son remboursement le fait chuter sans échec économique réel (exemple mesuré :
`money=289299` avec `current_loan=300000`, trésorerie nette réelle négative). `company_value` est net
de l'emprunt — un emprunt déplace de la dette vers du cash, ne change pas la valeur d'entreprise — et
`income`/`expenses` trimestriels donnent le profit directement, sans dérivation.

**Granularité : company-level, pas encore line-level.** `old_economy`/`cur_economy` sont agrégés au
niveau de la compagnie entière, pas par ligne. La question de phase 2 porte sur le profit d'une ligne
individuelle (couple villes × cargo × matériel) — il faudra une source supplémentaire (chunks
véhicules/stations) pour redescendre au niveau de la ligne ; non exploré en phase 0.

**Inflation désactivée.** `[economy] inflation = false`, fixé explicitement dans `openttd_config`
(vérifié dans le `openttd.cfg` généré par le binaire 13.4, pas supposé). Sur un horizon de 10 ans,
l'inflation compose sérieusement et confondrait la date avec la qualité économique d'une ligne — un
modèle entraîné dessus apprendrait à lire l'année plutôt que la ligne. Négligeable à 4 ans, plus à 10.

**Autres paramètres figés dans `openttd_config`** (pour ne pas dépendre d'un défaut qui changerait
entre deux versions) : `map_x`/`map_y = 8` (256×256), `starting_year = 1950`, `number_towns = 2`,
`industry_density = 4`.

**Confondant à traiter en phase 2 : catalogue de matériel × date.** Sur 10 ans à partir de 1950, les
locomotives disponibles évoluent (déblocages par date). « Modèle de matériel » et « date de
construction » seront donc corrélés. Le split par graine ne neutralise pas ce confondant — il
faudra soit inclure la date comme feature, soit contraindre les constructions à une fenêtre
temporelle courte.

---

## IA (Phase 2 — préparatoire)

**Déclaration des paramètres `info.nut` — vérifié empiriquement, pas supposé** (voir
`ai/ParameterisedAI/`) :
- Un paramètre supplémentaire non déclaré, ou un typo sur le nom d'un paramètre déclaré, est
  **ignoré silencieusement** : pas d'erreur, pas de warning. Un typo sur le nom réel d'un paramètre
  fait retomber silencieusement sur sa valeur par défaut (`custom_value` dans `info.nut`).
- Une valeur hors `[min_value, max_value]` est **clampée silencieusement** à la borne. Une valeur
  proche/au-dessus d'INT32_MAX déborde en entier signé et peut retomber très en dessous de
  `min_value`, clampée à 0 sans erreur.
- → Ne jamais faire confiance à `ai_params` côté Python : toujours vérifier `AIPL.settings` (chunk
  du savegame) dans les résultats pour confirmer que chaque paramètre a bien la valeur voulue.

**Comment savoir ce qu'une IA a construit — canaux testés un par un :**
- `Save()`/`Load()` : **ne remonte pas** via OpenTTDLab. Vérifié en écrivant un marqueur distinctif
  dans `Save()` et en cherchant sa présence dans tous les chunks parsés — absent. `AIPL` n'expose
  que l'écho des réglages déclarés (`settings`), jamais le contenu retourné par `Save()`.
- `AILog.Info(...)` / sortie console : **absente par défaut**. `row['output']` existe dans le
  résultat brut de `run_experiments` (avant `result_processor`), mais OpenTTD ne produit aucune
  sortie console en mode headless sans un flag `-d` explicite, qu'`run_experiments` ne permet pas
  de passer.
- `AISign.BuildSign(...)` : **fonctionne**, corrigé après un premier faux négatif. Le premier essai
  (jours=40) ne laissait pas assez de temps simulé à l'IA pour même démarrer — verifié en direct
  avec le binaire OpenTTD : sur 200 ticks (~2.7 jours) aucune sortie IA du tout, sur 8000 ticks
  (~108 jours) l'IA s'exécute normalement. Une fois cette confusion levée, le chunk `SIGN` expose
  bien `name` (texte), `x`/`y`/`z` (position) et `owner` — confirmé par `run_experiments`, pas
  seulement en direct. C'est le canal retenu : un panneau posé à chaque tentative, texte compact
  `TRLN|<stage>|<raison>|<construits>/<demandés>` (ex. `TRLN|success|n/a|2/2`), positionné sur la
  meilleure tuile connue au moment de l'échec (dépôt > tuile de départ > centre-ville > centre carte).
- Les chunks de vérité-terrain (`VEHS` filtré par `owner`, `STNN`, `DEPT`, `ORDR`) restent utiles en
  complément pour le détail fin (moteur, cargo, nombre exact de wagons) et pour détecter une
  construction partielle en comparant à `AIPL.settings` (ex. mesuré : `num_trains=50` demandés,
  17 réellement construits, faute d'argent — avant le correctif de l'emprunt max, voir plus bas).

**Angle mort pathfinder vs argent — supprimé par construction.** `TrainLineAI` emprunte le
maximum (`AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())`) au tout premier tick, avant toute
construction. Un échec ne peut donc plus venir du manque d'argent (dans la limite de ce que
`max_loan` permet sur cette carte/ces paramètres) — seul le terrain ou le pathfinder peuvent encore
faire échouer une tentative. `company_value` (net de l'emprunt) reste la cible : le remboursement du
prêt ne pollue rien.

**Déclaration des paramètres générée depuis un schéma unique — plus de typo possible par
construction.** `src/trainlineai_schema.py` définit `PARAMS` (nom, min, max, défaut, description)
une seule fois ; `render_info_nut()` génère `info.nut` depuis ce dict, `make_ai_params(**values)`
construit le tuple `ai_params` pour Python. Un nom de paramètre inconnu ou une valeur hors bornes
lève une `ValueError` **immédiate côté Python**, avant même de lancer OpenTTD — testé :
`make_ai_params(num_tarins=5)` (typo) et `make_ai_params(num_trains=999)` (hors bornes) lèvent
tous les deux, avec le message listant les paramètres réellement déclarés / les bornes réelles.

**`ai/TrainLineAI/`** : squelette fonctionnel (testé de bout en bout via `run_experiments`), deux
paramètres (`num_trains`, `wagons_per_train`), construit une ligne entre les deux villes les plus
peuplées la première année. Bugs rencontrés et corrigés pendant le développement, tous trouvés en
lançant le binaire OpenTTD directement avec `-d script=4` (le seul moyen d'obtenir la sortie
`AILog` en dehors d'OpenTTDLab) :
- `AITown.GetLocation()` renvoie le centre-ville (occupé par des bâtiments) : impossible d'y
  construire du rail contrairement à la route. Il faut chercher une tuile constructible à proximité.
- `RailPathFinder.InitializePath` attend des paires `[tuile, tuile_précédente]` pour établir une
  direction d'entrée ; utiliser deux fois la même tuile produit un triplet dégénéré et casse la
  recherche dès le premier pas.
- Le chemin retourné peut contenir un aller-retour sur une même tuile (artefact du pathfinder avec
  plusieurs directions d'entrée candidates) — à ignorer, pas à traiter comme un échec.
- `AIRail.BuildRailStation` n'auto-nettoie pas la tuile (contrairement à `AIRail.BuildRail`) : un
  `AITile.DemolishTile()` explicite est nécessaire avant.
- Une locomotive ne transporte pas elle-même de cargo (seuls les wagons le font) : filtrer les
  locomotives par `CanRefitCargo` élimine tout le catalogue.

**Rangs paramétrés (`town_a_rank`, `town_b_rank`, `engine_rank`) — passer d'une ligne par graine à
des dizaines.** Avec `Begin()`/`Next()` fixes, chaque graine ne produisait qu'une seule
observation (toujours les deux villes les plus peuplées, toujours le moteur le plus rapide) : pas
de variation de distance/terrain à l'intérieur d'une graine, et le matériel parfaitement déterminé
par la date (confondant total avec `AIEngine.GetMaxSpeed`, voir plus haut). Trois nouveaux
paramètres dans `src/trainlineai_schema.py::PARAMS`, consommés par `main.nut` via
`AIController.GetSetting` :
- `town_a_rank`/`town_b_rank` : index (0 = premier) dans la liste des villes triée par population
  décroissante, au lieu de `Begin()`/`Next()`. Rejet explicite (`town_rank_same_town`) si les deux
  rangs coïncident, et (`town_rank_out_of_range`) si un rang dépasse le nombre de villes réellement
  présent sur la carte — deux raisons d'échec distinctes du terrain/pathfinder, pour ne pas polluer
  le signal du classifieur.
- `engine_rank` : index dans la liste des moteurs rail non-wagon, constructibles, triée par
  vitesse décroissante, au lieu de `Begin()`. Même garde `engine_rank_out_of_range`.
- `cargo_index` : pas encore ajouté, prévu une fois ces trois-là stabilisés.

**Bornes vérifiées empiriquement, pas devinées** (`sweeps/debug_ai.py`, config figée de
`sweeps/phase0_timing.py`, carte 256×256, `number_towns=2`) :
- `AITown.GetTownList().Count()` loggée une fois par run : 23 à 30 villes selon la graine (12
  graines testées, seeds 1-10/42/100/999). Confirme que `number_towns=2` dans `openttd.cfg` est
  une densité ("normale"), pas un nombre de villes — à ne jamais reconfondre. `town_a_rank`/
  `town_b_rank` bornés à `[0, 15]` dans `PARAMS` : marge de sécurité sous le minimum observé (23),
  pour que le clamp silencieux d'OpenTTD (voir plus haut, "Déclaration des paramètres") ne
  transforme jamais un rang demandé en un rang inatteignable sur cette carte.
- Moteurs rail non-wagon constructibles disponibles à la toute première année (1950), avec le seul
  OpenGFX de base (pas de NewGRF supplémentaire) : **3 seulement** (`Kirby Paul Tank`, `Chaney
  'Jubilee'`, `Ginzu 'A4'`, tous à vapeur). `engine_rank` borné à `[0, 2]` en conséquence — le
  catalogue réel au démarrage est étroit, ce qui limite mécaniquement de combien `engine_rank`
  peut casser la colinéarité matériel × date en début de partie (à garder en tête si le confondant
  reste visible malgré ce paramètre).

**Contrainte à respecter pour la campagne multi-lignes (pas encore implémentée) : villes
disjointes entre lignes d'une même partie, et distance minimale entre lignes.** L'idée du
« bénéfice collatéral » (diviser le coût par observation en construisant plusieurs lignes
disjointes dans la même partie plutôt qu'une ligne par graine) n'a pas encore d'orchestrateur —
`main.nut` reste une IA à une seule ligne par instance de compagnie. Quand cet orchestrateur sera
écrit (un script dans `sweeps/`, probablement plusieurs instances de `TrainLineAI` avec des
`ai_params` différents dans la même expérience), il devra choisir des combinaisons de rangs telles
que les paires de villes ne se recouvrent pas entre lignes et restent séparées d'une distance
minimale — sans quoi deux lignes concurrentes sur les mêmes villes se cannibaliseraient les
passagers, ce qui fausserait `company_value` par ligne indépendamment de la qualité de chaque
ligne. La corrélation intra-partie (même monde, même conjoncture) reste couverte par le split par
graine, pas par cette contrainte.

**Bug trouvé en préparant l'attribution multi-lignes : les panneaux d'échec ne se posaient
probablement jamais.** `AISign.BuildSign` accepte au plus **31 caractères** — vérifié
empiriquement par recherche binaire (`sweeps/debug_ai.py` + une IA de test jetable) : 31 passe, 32
échoue avec `ERR_PRECONDITION_STRING_TOO_LONG`, **silencieusement** (pas d'exception Squirrel, pas
de sortie `-d script=4`, aucune entrée dans le chunk `SIGN`). Le format d'origine
(`TRLN|<stage>|<raison>|<construits>/<demandés>`) dépassait déjà cette limite à lui seul pour
presque toutes les raisons d'échec (ex. `TRLN|failed|no_buildable_tile_near_town|0/1` = 43
caractères) — seul `no_path_found` passait de justesse (29). Le seul panneau garanti de se poser
jusqu'ici était donc `TRLN|success|n/a|<n>/<n>` : tous les échecs de terrain/pathfinder,
c'est-à-dire le signal principal du classifieur constructible/non-constructible, étaient
vraisemblablement muets. Non détecté plus tôt car `AILog.Info(code)` s'exécute inconditionnellement
juste après `BuildSign` — la sortie `-d script=4` semblait donc confirmer que « le panneau a été
posé », alors qu'elle ne prouve que l'exécution de la ligne, pas le succès de `BuildSign` (dont le
retour n'était jamais vérifié). Corrigé par une table `REASON_CODES` (raison → code ≤ 7 caractères,
légende ci-dessous), et reconfirmé cette fois par lecture directe du chunk `SIGN` (pas seulement
`AILog`), sur un cas d'échec précoce (`town_rank_same_town`) et un cas de succès.

**Deuxième bug trouvé en écrivant `REASON_CODES` : une `local` de fichier n'est pas visible depuis
les méthodes `TrainLineAI::méthode()`.** Chaque `function TrainLineAI::x() { ... }` est compilée
comme une affectation de haut niveau indépendante ; un `local REASON_CODES = {...}` placé plus haut
dans le fichier n'est pas capturé par leur fermeture (contrairement aux fonctions imbriquées dans
`Start()`, ex. `nth`, qui elles fonctionnent normalement). Erreur obtenue à l'exécution : `the
index 'REASON_CODES' does not exist` — le script meurt, sans panneau ni log au-delà de ce point.
Corrigé en déclarant `::REASON_CODES <- {...}` (slot de la table racine, visible partout) au lieu
de `local`.

**Format des panneaux, révisé (deux panneaux par tentative au lieu d'un) :**
- Panneau de statut, toujours posé : `TRLN|<line_index>|<stage>|<raison_courte>|<construits>/<demandés>`.
  `line_index` (nouveau paramètre `PARAMS`, 0 par défaut) sert à rattacher un panneau à une
  tentative précise dès qu'il y en a plusieurs dans la même partie — nécessaire dès que
  l'orchestrateur multi-lignes ci-dessus existera. Légende `REASON_CODES` (`ai/TrainLineAI/main.nut`) :
  `NORAIL`=no_rail_type_available, `NOTOWN`=not_enough_towns, `TWNOOR`=town_rank_out_of_range,
  `TWNDUP`=town_rank_same_town, `NOTILE`=no_buildable_tile_near_town, `NOPATH`=no_path_found,
  `TRKFAIL`=track_build_failed, `STNFAIL`=station_build_failed, `DEPFAIL`=depot_build_failed,
  `NOENG`=no_engine_available, `ENGOOR`=engine_rank_out_of_range, `OK`=succès/pas d'échec.
- Panneau de détail, posé seulement si les villes ont été choisies (absent pour les 4 raisons
  d'échec qui précèdent le choix des villes) : `TRLN|<line_index>|T<town_a>-<town_b>|D<distance>|C<coût>`.
  `town_a`/`town_b` sont les IDs `AITown` bruts (joignables au chunk `CITY`). `distance` est la
  distance à vol d'oiseau (euclidienne, `sqrt(AIMap.DistanceSquare(...))` — `sqrt()` et
  `DistanceSquare` confirmés disponibles côté Squirrel) entre les deux centre-villes, connue avant
  tout pathfinding. `coût` est mesuré par `AIAccounting`, démarré juste après le choix des villes
  et lu à chaque rapport (succès ou échec) : couvre voie, ponts/tunnels, gares, dépôt et achats de
  véhicules — tout le capital dépensé pour cette tentative.
- Les deux panneaux sont posés à la même tuile (`AISign.BuildSign` accepte plusieurs panneaux par
  tuile, confirmé empiriquement) ; vérifié bout en bout par lecture du chunk `SIGN` complet, pas
  seulement `AILog` (voir les deux bugs ci-dessus).

**Fuite de feature identifiée : `path_length` n'est pas une caractéristique connue avant
tentative.** C'est un résultat du pathfinder (nombre de tuiles du chemin *trouvé*), disponible
seulement après une recherche réussie — l'utiliser comme feature d'entrée d'un modèle de
constructibilité ou de profit fuiterait de l'information sur l'issue même qu'on cherche à prédire.
Toujours calculé et gardé dans `Save()` à titre de diagnostic (non lu par OpenTTDLab de toute façon,
voir plus haut), mais commenté explicitement dans `main.nut` pour ne pas le confondre avec
`distance_straight` (distance à vol d'oiseau entre les deux villes choisies, connue dès le choix des
villes, donc légitime comme feature).

**Cible ligne-level : `VEHS.<id>.train[0].common[0].profit_this_year`/`profit_last_year` existent,
vérifié empiriquement — pas encore exploité.** `old_economy` (`PLYR`) est company-level, inutilisable
tel quel pour une cible par ligne (déjà noté plus haut). Vérification directe du chunk `VEHS` d'une
partie avec `TrainLineAI` (`sweeps/phase2_vehs_explore.py`, dump complet dans
`docs/phase2_vehs_explore.json`) :
- `profit_this_year`/`profit_last_year` sont bien présents, mais uniquement sur l'enregistrement du
  **véhicule de tête** (la locomotive) de chaque train — les wagons du même consist ont ces deux
  champs à 0. Cohérent avec la comptabilité de profit d'OpenTTD, qui l'attribue au véhicule de tête
  du consist plutôt qu'à chaque unité. Pour sommer le profit d'une ligne : ne garder que les
  véhicules `type=0` (train) dont `common[0].unitnumber != 0` (les wagons ont `unitnumber=0` dans
  ce dump), pas la totalité des entrées `VEHS`.
- **Cette cible est un profit d'exploitation** (income − coûts de fonctionnement), **hors voie,
  gares et entretien d'infrastructure** — c'est la nuance à ne pas perdre en la nommant : elle
  répond le mieux à « cette ligne, une fois construite, est-elle rentable à exploiter ? », pas à
  « ce projet de ligne, capital de construction inclus, est-il rentable ? ». D'où le panneau de
  coût de construction ci-dessus, à faire remonter et sommer séparément si la deuxième question
  est celle qui compte.
- Paire de gares d'une ligne, retrouvable via `ORDR` : chaque véhicule porte un pointeur `orders`
  (index dans `ORDR`) vers le premier maillon de sa liste d'ordres ; chaque nœud `ORDR` porte
  `dest` (ID de gare, chunk `STNN`) et `next` (maillon suivant du même véhicule). Un instantané ne
  donne que la gare de la commande *courante* (`current_order.dest`) — retrouver la paire complète
  demande de suivre la chaîne depuis `orders`, pas de lire un seul champ. **Non implémenté** : avec
  une seule ligne par compagnie aujourd'hui, grouper par `owner` suffit à attribuer les véhicules à
  « la » ligne de cette compagnie ; le chaînage `ORDR` ne devient nécessaire que lorsqu'une même
  compagnie (ou plusieurs lignes à distinguer autrement que par `owner`) construit plusieurs lignes
  disjointes dans la même partie — reporté à ce moment-là, pas engagé maintenant.
- Ordre de grandeur observé (3 ans de jeu, 1 seule ligne, squelette non optimisé) :
  `profit_this_year` très négatif (environ -540 000) sur chaque locomotive, plausible et cohérent
  avec l'accumulation de coûts de fonctionnement sur ~1095 jours sans revenu confirmé pour ce
  squelette (limitation `platform_length=1` déjà documentée plus haut) — pas un signe d'erreur
  d'échelle par rapport à `old_economy`/`money` (aucune incohérence d'unité détectée), juste une
  ligne-jouet qui perd probablement de l'argent en l'état.

**`AICompany.GetBankBalance` avant/après essayé pour le coût de construction, rejeté : pollué par
les intérêts du prêt.** `TrainLineAI` emprunte le maximum au tout premier tick (voir plus haut) ;
`GetBankBalance` baisse donc aussi sous l'effet des intérêts courus, indépendamment de toute
construction. Vérifié empiriquement avec une IA de test jetable (`sweeps/debug_ai.py`) : sur une
fenêtre d'environ 27 jours de jeu (`Sleep(2000)`) **sans aucune action de construction**,
`GetBankBalance` chute de **2100** pendant qu'`AIAccounting.GetCosts()`, ouvert sur la même
fenêtre, rapporte correctement **0**. Sur une fenêtre avec construction réelle (quelques
`DemolishTile`), les deux méthodes concordent exactement (`bankDelta` = `AIAccounting.GetCosts()`
= 1155) — la divergence n'apparaît que lorsque du temps s'écoule sans dépense, ce qui est
justement le cas pendant une recherche de chemin longue ou une construction étalée sur plusieurs
tuiles. `AIAccounting` (déjà utilisé, voir plus haut) reste donc la seule mesure fiable : il ne
compte que le coût des actions effectuées dans sa portée, insensible aux intérêts ou à toute autre
variation passive du solde. Aucun changement de code nécessaire — confirme simplement que le choix
initial était le bon.

**Cible ligne-level, deuxième étage : `profit_ligne = Σ(profit véhicules de la ligne) −
amortissement(coût de construction)`.** Assemble les deux morceaux vérifiés ci-dessus (profit
d'exploitation par véhicule de tête, coût de construction du panneau de détail) en une seule
métrique comparable à un profit annuel complet, capital inclus. Implémenté et testé sur des
parties réelles dans `sweeps/phase2_profit_ligne.py` — résultats dans
`docs/phase2_profit_ligne.json`.

**Piège vérifié en séparant infrastructure et véhicules : `AIAccounting` ne s'imbrique PAS.**
Première version : amortir tout le coût de construction (voie + gares + dépôt + véhicules) sur
l'âge maximal du matériel roulant — simplification assumée et documentée ici (le matériel roulant
a un `max_age` connu du jeu, l'infrastructure non). Décision utilisateur : séparer les deux
composantes et leur donner chacune leur propre horizon d'amortissement plutôt que de partager
celui du matériel. Premier essai d'implémentation : ouvrir un second `AIAccounting()` juste avant
l'achat des véhicules (étape 7), en gardant le premier (`this.costs`, ouvert à l'étape 4) actif en
parallèle pour mesurer l'infrastructure. **Cassé, vérifié empiriquement avant de le livrer** (IA
de test jetable, `sweeps/debug_ai.py`) : deux segments de voie construits l'un après l'autre,
coûts 90 puis 360. Le premier `AIAccounting` (ouvert avant les deux) affiche correctement 90 puis
450 (90+360, cumulatif). Le second, ouvert *entre les deux* segments, aurait dû isoler le coût du
second segment seul (360) — il affiche **450**, exactement la même valeur que le premier. Un
`AIAccounting` ouvert pendant qu'un autre est encore en vie ne démarre pas à zéro : il reflète le
même cumul depuis l'ouverture du plus ancien, pas son propre coût isolé. Si livré tel quel,
`vehicle_cost` aurait été quasiment égal à `construction_cost` en entier, et `infra_cost` (déduit
par soustraction) proche de zéro — silencieusement faux, sans aucune erreur pour le signaler.
**Corrigé** en abandonnant le second `AIAccounting` : `vehicle_cost` se lit par différence sur le
*même* `this.costs`, avant et après l'étape 7 (`GetCosts()` appelé aux deux instants, la
différence est le coût des achats de véhicules). `infra_cost` se déduit côté Python par
soustraction (`construction_cost − vehicle_cost`), sans panneau dédié.

**Format des panneaux, complété (trois panneaux au lieu de deux) :** un troisième panneau
`TRLN|<line_index>|V<vehicle_cost>` s'ajoute au statut et au détail, posé dans les mêmes
conditions que le détail (villes choisies), toujours présent (à 0 si l'échec précède l'achat de
véhicules) pour simplifier le parsing côté Python — les trois panneaux coexistent toujours
ensemble, ou aucun des trois.

**Amortissement à deux horizons, séparés :** `vehicle_cost / max_age_matériel_en_années`
(inchangé, horizon tiré du jeu) plus `infra_cost / INFRA_LIFE_YEARS`, où `INFRA_LIFE_YEARS` est
une **hypothèse explicite fixée à 30 ans** (horizon courant pour de l'infrastructure ferroviaire
dans la vraie vie ; OpenTTD ne modélise aucune durée de vie ou dépréciation pour la voie/les gares
— rien à en tirer empiriquement, contrairement à `max_age`) — voir `INFRA_LIFE_YEARS` dans
`sweeps/phase2_profit_ligne.py`/`phase2_trainline_run.py`. `profit_ligne = Σ profit_this_year
(véhicules de tête) − vehicle_cost/max_age_années − infra_cost/INFRA_LIFE_YEARS`.
