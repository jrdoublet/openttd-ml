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

**Orchestrateur multi-lignes par partie — implémenté, avec contrainte de villes disjointes
(2026-08-26).** Voir la sous-section dédiée plus bas (« Cannibalisation multi-lignes ») pour le
détail complet : mécanisme, chiffres de contrôle, limites connues. Note historique : ce passage
disait auparavant que l'idée n'avait « pas encore d'orchestrateur » et listait deux contraintes à
respecter (villes disjointes + distance minimale entre lignes) — seule la première a été
implémentée (demande explicite de l'utilisateur) ; la **distance minimale entre lignes** reste
une piste future, non traitée. La corrélation intra-partie (même monde, même conjoncture) reste
couverte par le split par graine, pas par la contrainte villes disjointes.

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
  `PATHLIM`=path_search_limit, `TRKFAIL`=track_build_failed, `STNFAIL`=station_build_failed,
  `DEPFAIL`=depot_build_failed, `NOENG`=no_engine_available, `ENGOOR`=engine_rank_out_of_range,
  `PAIROOR`=pair_rank_out_of_range (2026-08-26, voir gradient de difficulté `pair_rank` plus bas),
  `NODISJ`=no_disjoint_town_pair (2026-08-26, voir contrainte villes disjointes plus bas),
  `OK`=succès/pas d'échec.
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
`sweeps/phase2_profit_ligne.py`/`phase2_trainline_run.py`. `profit_ligne = Σ profit_last_year
(véhicules de tête) − vehicle_cost/max_age_années − infra_cost/INFRA_LIFE_YEARS` — `profit_last_year`
et pas `profit_this_year`, voir plus bas ("Unité manquante").

---

## Quatre bugs réels trouvés en creusant un signal suspect (2026-08-25, revue externe)

Un examen des trois premières valeurs de `sum_profit_this_year` de la campagne
(`docs/phase2_trainline_run.json`) a révélé une anomalie : trois lignes de graines et distances
différentes (77, 88, 33 tuiles) donnaient **exactement** -924600, au franc près. Une coïncidence
à ce niveau de précision n'existe pas — c'est le signe d'une variable confondue à 100 %, pas d'un
signal de ligne. L'anomalie suivait `engine_rank` et rien d'autre. Investigation menée en suivant
la piste jusqu'au bout plutôt que de s'arrêter à la première explication plausible ; quatre bugs
réels trouvés, tous vérifiés empiriquement avant d'être corrigés dans `ai/TrainLineAI/main.nut`.

### Bug 1 — quai d'une seule tuile : les wagons restaient hors quai

`platform_length` était fixé à `1` (limitation déjà notée dans le code, mais jamais quantifiée).
Avec un convoi de 1 locomotive + N wagons, seule la locomotive tient sur un quai d'1 tuile — les
wagons (qui sont les seuls à transporter du cargo, voir plus haut) restent physiquement hors
quai en permanence. **Vérifié empiriquement** (`sweeps/debug_ai.py` + inspection directe du
savegame) : sur 3 ans, les deux wagons d'une ligne construite affichaient `cargo_cap=40` (capacité
réelle) mais `cargo.packets=[]` (jamais rien chargé) en permanence, alors que
`AITile.GetCargoProduction`/`GetCargoAcceptance` autour de la gare étaient tous les deux non nuls
(la ville produit et accepte bien des passagers à cet endroit — ce n'était donc pas un problème de
zone de chalandise). `profit_this_year`/`profit_last_year` des locomotives n'étaient donc qu'un
pur coût de roulement : même moteur × même nombre de véhicules × même durée écoulée = même
montant, quelle que soit la ligne — exactement le signal repéré.

**Corrigé** : `platformLength = ceil((1 + wagons_per_train) / 2) + 1` (un convoi de N unités
occupe environ N/2 tuiles en pratique, +1 de marge), passé en 4ᵉ argument de
`AIRail.BuildRailStation` pour les deux gares. Conséquence acceptée : une gare plus longue a une
emprise plus grande, donc plus difficile à placer — `station_build_failed` devrait augmenter, pour
de vraies raisons de terrain cette fois (bonne nouvelle pour la variance de l'étage 1 du modèle
hurdle, mais rend les anciens taux d'échec, ex. graine 999, non comparables aux nouveaux — d'où le
re-baseline complet de la campagne).

**Bug de portée Squirrel trouvé en l'implémentant, même famille que celui déjà documenté pour
`REASON_CODES` :** passer `platformLength` (une `local` de `Start()`) à `buildStation` (une
fonction imbriquée `local buildStation = function(tile) {...}` définie plus loin dans le même
`Start()`) échouait avec `the index 'platformLength' does not exist` — un closure imbriqué ne
capture pas les locals de sa fonction englobante dans cet environnement, même entre deux locals du
*même* `Start()` (pas seulement entre fichier et méthode de classe, comme observé la première
fois). **Règle générale retenue : ne jamais compter sur la capture de closure dans ce dépôt —
passer explicitement tout ce dont une fonction imbriquée a besoin en paramètre.** Corrigé en
ajoutant `platformLength` comme second paramètre de `buildStation`.

### Bug 2 — dépôt raccordé à la mauvaise tuile, trains bloqués à vie

Le quai plus long **n'a pas suffi** : après correction, les wagons restaient encore à
`cargo.packets=[]`. Inspection de `VEHS` pour les deux locomotives : `last_station_visited=65535`
(`INVALID_STATION` — **jamais visité aucune gare**, en ~1020 jours de jeu chacune), `tile=27337`
identique à `DEPT[0].xy` (le dépôt), immobiles depuis leur construction. Les deux trains n'avaient
jamais quitté le dépôt.

**Cause : le dépôt était construit adjacent à la tuile de la gare elle-même**
(`AIRail.BuildRailDepot(candidate, tiles[0])`, `tiles[0]` = tuile de la gare A), avec une
orientation choisie arbitrairement (le premier offset `(0,1)` qui réussissait), sans rapport avec
l'orientation réelle du quai (`NE_SW` ou `NW_SE`, dont on ne sait pas à l'avance laquelle a
réussi). Une gare (contrairement à une tuile de voie ordinaire) n'accepte pas un raccordement
perpendiculaire à son propre axe — le dépôt se retrouvait construit avec un aiguillage qui ne
menait nulle part.

**Corrigé** : le dépôt est maintenant ancré sur `tiles[1]` (la première tuile de **voie réelle**,
garantie connectée à `tiles[0]` par construction — `BuildRail` y a été appelé avec `tiles[0]`
comme tuile précédente à l'étape 4), avec `front=tiles[1]`. Une tuile de voie ordinaire accepte un
raccordement/aiguillage depuis n'importe laquelle de ses directions valides, contrairement à une
gare. **Vérifié empiriquement** : après correction, `last_station_visited` passe de `65535` à `0`
(gare valide), `cur_real_order_index` avance (le train complète ses arrêts et passe à l'ordre
suivant) — les deux trains bougent et visitent effectivement les gares, ce qui n'arrivait jamais
avant.

### Bug 3 — le coût de construction comptait l'exploration du pathfinder, pas juste la construction

Effet de bord découvert en creusant les lignes sans panneau (voir plus bas) : une tentative en
échec `no_path_found` — donc *avant toute commande de construction* — rapportait un coût de
**55 856 940**. `no_path_found` se déclenche immédiatement après la boucle de recherche de chemin,
avant la voie, les gares, le dépôt ou les véhicules : ce coût ne pouvait provenir d'aucune
construction réelle.

**Cause** : `this.costs = AIAccounting()` était ouvert *avant* la recherche de chemin (pour
englober toute dépense de l'étape 3 à l'étape 7). `RailPathFinder` évalue des candidats de
pont/tunnel pendant sa recherche (probablement en `AITestMode`, pour connaître leur coût sans les
construire réellement) — ces évaluations, bien que jamais suivies d'une construction effective, se
retrouvaient comptées dans `this.costs`, pour la même raison de fond que le piège déjà documenté
plus haut : **un `AIAccounting` ouvert capte tout ce qui se passe dans sa portée temporelle, y
compris une activité de coût produite par du code qu'on n'a pas écrit soi-même** (ici, l'intérieur
d'une librairie tierce), pas seulement nos propres appels de construction.

**Corrigé** : `this.costs = AIAccounting()` est maintenant ouvert **après** `path_found = true`,
une fois le chemin trouvé — plus aucune activité du pathfinder ne peut être comptée.
**Vérifié empiriquement** : le même cas `no_path_found` rapporte maintenant `C0` (au lieu de
55 856 940). Effet de bord sur les lignes *réussies* : le coût de la ligne de test (graine 42,
`A0/B1/E0`) est passé de **1 964 441 à 62 241** — un facteur ~31. **Toutes les données de coût de
la campagne précédente (`docs/phase2_trainline_run.json`, `docs/phase2_profit_ligne.json`,
la visualisation) étaient gonflées par ce bug et ont été regénérées.**

### Bug 4 (non résolu) — le chargement de cargo reste à zéro même avec les trois corrections ci-dessus

Après les corrections 1 et 2, un test dédié (graine 42, `A0/B1/E0`, **1 seul train** — pour
exclure tout risque d'auto-blocage entre deux trains sur voie unique sans signaux, voir plus bas)
montre `AITile.GetCargoProduction` non nul et `STNN.goods[0].max_waiting_cargo` atteignant **290**
à un moment donné (des passagers s'accumulent bien en gare) — mais `cargo.packets=[]` sur les
wagons reste **vrai après 10 ans de jeu**, même avec un seul train, sans concurrence possible.
Cause non identifiée : ni le quai, ni le dépôt, ni la zone de chalandise, ni un conflit
multi-trains (`num_trains=1` exclut ce dernier) n'expliquent ce symptôme. Piste écartée en
passant : **absence totale de signaux** (`AISignal`/`AIRail.BuildSignal` : aucun appel dans tout
`main.nut`) — confirmée comme un risque réel de blocage mutuel pour `num_trains≥2` sur une voie
unique (un train immobile à `cur_speed=0` près du dépôt observé avec `num_trains=2`, absent avec
`num_trains=1`), mais insuffisante à elle seule pour expliquer le symptôme à `num_trains=1`.
**Reporté** : creusé jusqu'à la limite raisonnable de cette session : les données de profit restent
donc `revenu ≈ 0` (uniquement des coûts de roulement) même après les corrections 1-3, tant que ce
quatrième problème n'est pas résolu. `profit_ligne` continue d'être calculé et affiché — c'est
maintenant un chiffre honnête (les trois biais identifiés sont corrigés), mais qui ne reflète pas
encore une ligne rentable en l'état, puisque le revenu lui-même reste nul.

### Unité manquante : `profit_last_year` remplace `profit_this_year`

`profit_this_year` couvre l'année **en cours** au moment de la sauvegarde — partielle si la
sauvegarde tombe en milieu d'année civile — alors que `amortization_annual` est une figure
annuelle complète. Comparer les deux mélangeait deux unités de durée différentes.
`profit_last_year` est toujours une année complète par construction (le dernier trimestre clos,
composé sur 4 trimestres). `sweeps/phase2_profit_ligne.py` et `phase2_trainline_run.py` sommaient
`profit_this_year` ; corrigé pour sommer `profit_last_year` (champ renommé `sum_profit_last_year`
dans les deux scripts et les JSON produits).

### Lignes sans panneau : diagnostiquées, pas juste supposées lentes

Sur les 12 tentatives de la campagne, 4 n'avaient produit aucun panneau même après 3 ans de jeu.
Hypothèse à vérifier : censure corrélée au terrain (donc biaisante), pas du hasard. Une des quatre
(graine 100, `A0/B1/E0`) a été relancée en direct (`sweeps/debug_ai.py`, `-d script=4`) avec un
budget de ticks croissant : toujours aucun panneau à 5 000 ticks (~68 jours, cohérent avec 3 ans de
budget de campagne), résolu à **200 000 ticks (~2703 jours, ~7,4 ans)** avec `NOPATH` — un vrai
échec de recherche de chemin, pas un blocage. La recherche de chemin elle-même reste bornée
(`iterations_left`, ~500 itérations de boucle max côté script) — le temps réel consommé vient du
budget CPU/opcode qu'OpenTTD alloue au script par tick : une carte où le chemin est difficile à
écarter (beaucoup de candidats à explorer avant d'épuiser l'espace de recherche) fait consommer un
nombre de *ticks réels* largement supérieur au nombre d'itérations de notre propre boucle. **Confirme
l'hypothèse de départ** : ces échecs sont corrélés à la difficulté réelle du terrain, pas des
artefacts aléatoires d'instrumentation — les censurer silencieusement biaiserait le classifieur de
l'étage 1 vers les cartes faciles. Les 3 autres lignes silencieuses n'ont pas été testées
individuellement (par souci de temps) mais partagent vraisemblablement la même cause. **Mitigation
retenue** : allonger la fenêtre de la campagne à 6 ans (`DAYS = 365 * 6` dans
`phase2_trainline_run.py`) — sachant qu'un budget encore plus long resterait insuffisant pour les
pires cas (7,4 ans observé sur un seul exemple) ; certaines lignes resteront probablement encore
sans panneau même à 6 ans, ce qui est attendu et pas un signe d'échec du diagnostic.

---

## Bug 4, repris : indices trouvés dans trAIns, un flag d'ordre corrigé, un mystère qui reste

Sur suggestion explicite (« regarde l'IA trAIns ou AdmiralAI pour mieux comprendre la construction
de gares et de lignes de trains, et leur exploitation »), le code source de trAIns a été extrait
directement du cache local OpenTTDLab (`~/.cache/OpenTTDLab/.../bananas/54524149-trAIns-2.1.tar`,
déjà téléchargé pour la calibration de phase 0 — pas de nouveau téléchargement nécessaire) plutôt
que recherché en ligne, où le lien fourni (wiki `Development/Script/RailPathfinder`) ne documente
que l'algorithme de recherche de chemin, pas l'exploitation d'une ligne une fois construite.

**Indice trouvé : les ordres de trAIns portent `AIOF_FULL_LOAD_ANY`, les nôtres `OF_NONE`.**
(`railroad/railroad_manager/railroad_route/town_town_railroad_route.nut`,
`railroad_route.nut::SetTrainOrders`). `AIOrder.OF_FULL_LOAD_ANY` existe bien dans l'API v13 utilisée
ici (`AIOrder.OF_FULL_LOAD_ANY = 96`, vérifié empiriquement). `OF_NONE` ne force aucune attente :
le train marque un arrêt par défaut (~74 ticks observés, ~1 jour) et repart que du cargo soit
disponible ou non — sur une ligne neuve à faible fréquentation, il repart quasiment toujours à vide.
**Corrigé** : `AIOrder.OF_FULL_LOAD_ANY` sur les deux arrêts. **Effet vérifié empiriquement,
décisif** : les wagons, qui affichaient `cargo.packets=[]` en permanence dans *tous* les tests
précédents (jusqu'à 20 ans de jeu, un seul train), atteignent maintenant leur pleine capacité
(`cargo_cap=40`, confirmé par `cargo.action_counts` dans `VEHS` sur les deux wagons). C'est la
première fois, toutes tentatives confondues, qu'un wagon de `TrainLineAI` transporte du cargo.

**Deuxième indice, qui a fait fausse route puis a été corrigé : `OF_UNLOAD`.** trAIns combine
`AIOF_FULL_LOAD_ANY | AIOF_UNLOAD` sur ses deux arrêts ville-à-ville ; `OF_UNLOAD` ajouté par
symétrie. Wagons pleins confirmés (comme ci-dessus), mais **`income` restait à 0** après 20 ans.
Recherche sur le wiki OpenTTD (le lien fourni par la review ne couvrait pas ce point ; recherche
élargie) : *« When the train has the order to unload at a station then it won't be paid »* — `OF_UNLOAD`
signifie explicitement que **ce véhicule n'est pas payé** ; c'est une sémantique de *feeder service*
(un premier véhicule dépose le cargo, un second complète le trajet et touche le paiement). Sans
second véhicule, le cargo est simplement déposé, jamais vendu. **`OF_UNLOAD` retiré** — le
déchargement par défaut (sans flag transfer/unload explicite) paie directement ce qui correspond à
l'acceptation de la gare, le bon choix pour une navette simple à deux gares sans correspondance.

**État actuel, non résolu : même sans `OF_UNLOAD`, `income` reste à 0 malgré des wagons pleins
(40/40 confirmé) sur 5 ans de jeu.** Pistes testées et écartées une par une, chacune vérifiée
empiriquement plutôt que supposée :
- Mode de distribution du cargo (`[linkgraph] distribution_pax`) : testé en `manual` (valeur `0`,
  confirmée appliquée via le chunk `PATS` du savegame) — même symptôme.
- `AIVehicle.RefitVehicle` explicite sur le wagon après achat (trAIns le fait systématiquement,
  même quand le cargo par défaut correspond déjà) — testé, même symptôme, retiré (n'apportait rien).
- Zone de chalandise / distance gare-ville, blocage multi-trains, raccordement dépôt/voie : déjà
  écartés au tour précédent (voir bug 4 ci-dessus).
- `cargo.action_counts` des deux wagons affiche `[0, 0, 40, 0]` de façon constante, avec ou sans
  `OF_UNLOAD`, en mode `manual` comme dans la configuration par défaut — l'indice 2 (40 unités)
  correspond vraisemblablement à `MTA_TRANSFER` dans l'énumération interne d'OpenTTD (à confirmer
  contre le code source du jeu, pas accessible depuis cet environnement), pas à `MTA_DELIVER` —
  mais retirer `OF_UNLOAD` n'a pas changé cette répartition, ce qui contredit l'explication la plus
  simple et indique qu'un autre mécanisme, non identifié, est à l'œuvre.

**Troisième indice, décisif celui-là : AdmiralAI utilise un patron asymétrique, pas symétrique.**
Code source cloné directement depuis `github.com/Yexo/AdmiralAI` (`rail/trainline.nut`, fonction
qui construit chaque train) : contrairement à trAIns (symétrique, `FULL_LOAD_ANY` aux deux arrêts),
AdmiralAI pose `OF_FULL_LOAD_ANY | OF_NON_STOP_INTERMEDIATE` à l'aller et
`OF_UNLOAD | OF_NO_LOAD | OF_NON_STOP_INTERMEDIATE` au retour — chargement complet dans un sens,
déchargement forcé sans rechargement dans l'autre. **Testé, même résultat exact** que tous les
essais précédents (mêmes ID de paquets de cargo, `1962-...` non atteint, `income` toujours à 0) —
ce qui a orienté l'investigation vers autre chose que les flags d'ordre : si trois patrons de
flags différents (aucun, symétrique, asymétrique) donnent tous exactement le même résultat, les
flags ne sont probablement pas la variable en jeu.

**La vraie cause, trouvée en traçant la position du train tick par tick sur 2 ans (pas seulement
un instantané final) : le train ne quitte jamais le voisinage immédiat du dépôt.** Chaque
instantané mensuel du chunk `VEHS` montre `last_station_visited=0` (gare A) et
`cur_real_order_index=1` (en route vers la gare B, `dest=1`) — mais la tuile du train reste
confinée à une zone de 4×2 tuiles autour de la gare A/du dépôt (`x:200-203, y:105-106`) du premier
au dernier instantané, alors que la gare B se trouve à 63 tuiles de distance. Le train tourne en
rond près du départ, vitesse non nulle (jusqu'à 84), sans jamais progresser vers la destination.
**Ce n'est donc pas un problème de chargement de cargo mais de navigation du train lui-même** — le
chargement complet observé (40/40, bug 4 "résolu" plus haut) n'a jamais pu déboucher sur une
livraison parce que le train n'atteint jamais la seconde gare, point final.

**Hypothèse de la jonction sans signal — testée, pas confirmée.** Quatre variantes de placement du
dépôt essayées, chacune vérifiée empiriquement sur le même cas de test (graine 42, `A0/B1/E0`,
`num_trains=1`), en traçant la position du train mois par mois sur 2 ans :

1. **Dépôt sur `tiles[1]`, ordre d'offset fixe (l'état issu du tour précédent).** Le train atteint
   la gare A (`last_station_visited=0`), se déplace à vitesse réelle, oscille dans un rayon
   limité (~6 tuiles) sans jamais atteindre la gare B (à 63 tuiles). **Meilleur résultat obtenu.**
2. **Dépôt déplacé plus loin sur la voie** (`tiles[5]` au lieu de `tiles[1]`) : même oscillation,
   mais centrée sur le nouveau point d'ancrage — élimine l'hypothèse « adjacent à la gare »
   spécifiquement, sans rien résoudre.
3. **Signal PBS posé sur la jonction dépôt/voie** (`AIRail.BuildSignal`, `SIGNALTYPE_PBS`) :
   résultat **strictement identique** à la variante 1, au tick près. Élimine l'hypothèse
   « absence de signal ».
4. **`vehicle_breakdowns = 0`** dans la config (élimine tout service automatique en dépôt,
   confirmé sans effet lui non plus, même résultat que la variante 1.

**Cause réelle trouvée par inspection directe des coordonnées de la voie** (`AIMap.GetTileX/Y`
des 10 premières tuiles loggé) : `tiles[1]` est un **virage**, pas une section droite (la voie va
plein ouest de `tiles[0]` à `tiles[1]`, puis plein sud de `tiles[1]` à `tiles[2]`). Le premier
offset essayé, `(0,1)`, tombe alors exactement sur `tiles[2]` — démolir puis construire le dépôt
dessus écrase une tuile de la voie principale elle-même, coupant la ligne en cul-de-sac juste
après le départ. **Un bug réel, confirmé** — mais le corriger (en excluant les candidats déjà
présents dans `tiles[]`, ou en ancrant le dépôt sur la première section droite trouvée, ou en
n'essayant que les deux offsets perpendiculaires à l'axe réel de la voie à cet endroit) **fait
régresser** le résultat sur ce cas de test : le train ne rejoint alors plus **aucune** gare, pas
même la première — pire que l'état de départ. Testé avec trois formulations différentes du
correctif, même régression à chaque fois. **Conclusion contre-intuitive mais reproductible : la
collision dépôt/voie repérée est un vrai défaut, mais ce n'est pas (ou pas seule) la cause du
blocage de navigation.** Un autre mécanisme, non identifié, est à l'œuvre — la version actuelle du
code (celle qui atteint au moins la gare A) a été conservée comme la plus fonctionnelle trouvée à
ce jour, sans revendiquer d'avoir compris ni résolu le problème de fond.

**Bilan honnête** : `OF_FULL_LOAD_ANY` (patron trAIns, symétrique) reste le choix retenu dans le
code — c'est une amélioration réelle et vérifiée par rapport à `OF_NONE` (chargement désormais
possible, jamais observé avant cette session). Le blocage de navigation, lui, a résisté à sept
hypothèses testées dans l'ordre (asymétrie des flags, patron AdmiralAI, position du dépôt ×2,
signal, désactivation du service automatique, collision dépôt/voie) — chacune vérifiée
empiriquement, aucune n'a résolu le symptôme, et corriger le seul vrai bug confirmé parmi elles
(la collision dépôt/voie) régresse le résultat. Le sujet a largement débordé du cadre initial
(« regarder trAIns/AdmiralAI pour des indices ») sans aboutir. `profit_ligne` reste à ce stade un
pur coût de roulement. **Recommandation pour la suite** : ce problème mérite un accès visuel réel
au jeu (capture d'écran ou observation directe en jeu de la voie/du train autour du dépôt) plutôt
que d'autres itérations à l'aveugle sur des coordonnées seules — l'inspection de coordonnées a
permis de trouver un vrai bug (la collision), mais pas LE bug qui bloque la navigation.

## Sélection de paire par rang, orchestrateur multi-lignes, cannibalisation (2026-08-26)

**`pair_rank` — gradient de difficulté contrôlé sur le choix de paire.** La sélection de paire
(score `population_a*population_b/distance`, inchangée) ne se contente plus d'essayer les paires
dans l'ordre du score jusqu'à en trouver une viable (jusqu'à 12 essais, repli automatique sur la
paire suivante en cas d'échec) : toutes les paires candidates sont triées par score décroissant et
la paire au rang `pair_rank` (nouveau paramètre d'IA, 0-99, 0 = meilleur score) est tentée seule,
sans repli. Un échec à un rang donné est donc un vrai point de donnée sur la difficulté de ce rang
plutôt qu'un échec masqué. Banc `sweeps/phase2_pair_rank_run.py` (100 lignes, 5 graines × 20 rangs
échantillonnés par une loi géométrique pour densifier les petits rangs) : taux de succès net par
tranche de rang — **0-4 : 100 % (24/24) · 5-9 : 83 % (19/23) · 10-19 : 82 % (28/34) · 20-59 : 53 %
(10/19)**. Gradient confirmé, contrôlé par un seul paramètre.

**Orchestrateur multi-lignes par partie, avec contrainte de villes disjointes.** Question de
départ : la paire T6-2/graine 42/`pair_rank`=0 a un coût de construction et un matériel roulant
identiques entre deux campagnes différentes, mais un profit d'exploitation très différent
(+64216 puis -152360) — est-ce que plusieurs lignes partagent la même partie et se cannibalisent
les passagers ? Réponse, confirmée par lecture directe du code source d'OpenTTDLab
(`run_experiments`/`_run_experiment`) : non, jusqu'ici — chaque dico d'expérience tourne dans son
propre processus OpenTTD isolé (une compagnie, une partie), tant qu'il ne contient qu'une seule
entrée `local_folder(...)` dans son tuple `ais` (le cas de tous les bancs `sweeps/` avant celui-ci).
Mais le mécanisme existe bel et bien côté OpenTTDLab : plusieurs entrées `local_folder(...)` dans
UN MÊME dico démarrent bien plusieurs compagnies IA simultanées dans une seule partie partagée —
exactement l'« orchestrateur multi-lignes » anticipé plus haut mais jamais construit, et déjà
préparé côté `main.nut` (boucle anti-collision de nom de compagnie, champ `line_index`).

Décision : construire cet orchestrateur maintenant, mesurer d'abord la cannibalisation brute, puis
corriger avec une contrainte dure. Nouveau script `sweeps/phase2_multiline_control.py` (même
graine 42, même config, `pair_rank`/`line_index`=0..N-1 pour N compagnies simultanées ;
`pair_rank`=0/`line_index`=0 est le point de référence fixe présent dans toutes les tailles).

**Mesure brute (avant correctif, `docs/phase2_multiline_control.json`)** — `profit_ligne` de la
ligne `pair_rank`=0 (toujours T6-2, coût 41520, inchangé) selon le nombre de compagnies
simultanées dans la même partie :

| N compagnies | profit_ligne (pair_rank=0) | delta vs N=1 |
|---|---|---|
| 1 (isolé) | -154 257 | — |
| 5 | -278 673 | -124 416 (+81 %) |
| 15 | -690 833 | -536 576 (+348 %) |

Dégradation nette et monotone avec le nombre de compagnies partageant la partie — la
cannibalisation est réelle et mesurable, pas une hypothèse. Effet secondaire observé (attendu,
sans échelonnement des démarrages à ce stade) : de vraies collisions de construction, ex. deux
compagnies tentant de bâtir près de la même ville (ville 8, `STNFAIL` à coût quasi nul).

**Correctif implémenté (`ai/TrainLineAI/main.nut`)** :
- `TrainLineAI::_isTownServed(townID, radius)` : scanne un rayon de tuiles autour du centre-ville
  (`AITown.GetLocation`) à la recherche d'une gare rail (`AIRail.IsRailStationTile`, requête
  d'état de tuile globale, non filtrée par compagnie — déjà utilisée pour le placement du dépôt).
  `AIStationList()`/`AISignList()` sont, elles, filtrées sur la compagnie appelante : inutilisables
  pour voir ce qu'une AUTRE compagnie a construit dans la même partie. Un scan de tuiles est la
  seule vraie option pour une détection cross-compagnie depuis une instance IA en cours
  d'exécution. `DISJOINT_CHECK_RADIUS`=40 (rayon 30 de `_makeStationPlans` + marge).
- Contrainte dure : toute ville déjà desservie est exclue des paires candidates *avant* le tri par
  score/`pair_rank` — `pair_rank`=0 reste « la meilleure paire encore disponible ». Nouveau code
  d'échec `NODISJ` si le filtre épuise toutes les paires.
- Échelonnement des démarrages (`STAGGER_TICKS`=6000, ~81 jours/compagnie) : sans lui, toutes les
  compagnies choisiraient leur paire au même tick, avant que quiconque n'ait rien construit, et le
  filtre serait inutile. `line_index` sert de clé d'ordonnancement (compagnie `line_index`=0 sans
  délai, comparable à une partie isolée). Valeur vérifiée par bissection via `sweeps/debug_ai.py`
  avant le run réel : une ligne facile (`pair_rank`=0) se termine en ~1700-1800 ticks pour cette
  graine — 6000 laisse une marge ×3 confortable, sans être re-calibré pour des rangs plus
  difficiles (voir limites ci-dessous).
- **Limite connue et acceptée, pas un bug à chasser** : le scan est centré sur le centre-ville
  candidat, pas sur les tuiles réelles de sa propre gare — deux villes candidates proches peuvent
  se parasiter (la gare d'une ville C dans le rayon d'une ville B fait percevoir B comme déjà
  desservie). Pas de cas observé dans les vérifications de cette session, mais pas exclu sur
  d'autres cartes.

**Vérification après correctif (`docs/phase2_multiline_verify.json`, N=1 et 15 seulement — les
deux extrêmes suffisent)** :

| N compagnies | profit_ligne (pair_rank=0) |
|---|---|
| 1 (isolé) | -247 186 |
| 15 | -49 298 |

La dégradation massive et monotone a disparu : à N=15, `pair_rank`=0 n'est plus écrasé par la
concurrence (villes 6/2 jamais réutilisées par les 14 autres compagnies, confirmé). Chiffre à
lire avec prudence, pas comme une identité parfaite entre N=1 et N=15 — voir le mystère non résolu
ci-dessous, qui affecte aussi la comparaison N=1 avant/après correctif. Confirmation du
plafonnement annoncé : sur ~23 villes pour cette graine, les compagnies `line_index`=5 à 11
échouent en `PAIROOR` (plus aucune paire disjointe disponible) une fois ~4-5 lignes construites —
`n_villes/2` reste un ordre de grandeur théorique, le plafond réel observé est plus bas une fois
les filtres distance/population/coût appliqués en plus de la contrainte disjointe. Trois
compagnies (`line_index`=12-14) n'ont posté aucun panneau dans le savegame final capturé — piste
non éclaircie, pas creusée davantage (compagnies tardives dans un ordre d'échelonnement déjà
poussé à N=15, comportement à surveiller plutôt qu'à corriger à l'aveugle).

**Mystère séparé, non résolu, à ne pas confondre avec la cannibalisation ci-dessus.** La même
paire T6-2/graine 42/`pair_rank`=0, construction et matériel roulant strictement identiques (coût
41520-41535, `vehicle_cost` 36256, `avg_max_age_years` 21.06), donne un profit d'exploitation
différent à chaque changement de code de `main.nut`, même quand ce changement ne modifie rien à
CE QUI est construit : +64216 (avant la refonte `pair_rank`) → -152360 (après, scan linéaire
remplacé par un tri complet) → -247186 (après l'ajout de la contrainte villes disjointes, qui pour
`line_index`=0 seul ne devrait rien changer en pratique — aucune ville servie, aucun délai). Trois
versions de code, trois profits différents, pour une construction identique au tick de coût près.
Hypothèse non vérifiée : le calcul supplémentaire exécuté avant la première `DoCommand` (tri
complet, puis pré-calcul `townServed` sur ~23 villes) décale le tick auquel elle se déclenche, ce
qui suffit à faire diverger toute la simulation RNG-dépendante (passagers, croissance des villes)
sur les 10 années suivantes malgré une ligne construite à l'identique. Implication méthodologique
sérieuse si confirmée : `profit_ligne` n'est comparable qu'*à l'intérieur* d'une même version de
`main.nut`, jamais entre deux versions, même fonctionnellement équivalentes pour ce qui est
construit. Pas encore vérifié empiriquement (nécessiterait d'instrumenter les ticks autour de la
sélection de paire et de la première commande de jeu, ancien code vs nouveau, même graine) —
reporté, pas résolu.
