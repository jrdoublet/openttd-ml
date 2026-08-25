**Question.** Peut-on prédire le profit d'une ligne ferroviaire à partir de ses caractéristiques
de construction, sans simuler la partie ?

**Unité d'observation.** Une ligne construite (couple villes × cargo × matériel × nombre de rames).

**Métrique.** MAE sur le profit annuel moyen.

**Baseline.** Profit médian du jeu d'entraînement.

**Protocole de split.** Par graine, jamais par ligne : deux lignes d'une même partie partagent
le monde, la conjoncture et la concurrence.

**Critère de réussite.** Battre la baseline de 20 % en MAE, sur des graines jamais vues.

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
- `AISign.BuildSign(...)` : construit dans le jeu mais **n'apparaît pas non plus** dans le chunk
  `SIGN` parsé — testé et vérifié vide.
- **Ce qui marche** : les chunks de vérité-terrain du savegame — `VEHS` (filtré par `owner` +
  liste `train`/`roadveh` non vide), `STNN`, `DEPT`, `ORDR` — donnent le compte exact de ce qui a
  été construit (véhicules, moteur, cargo, gares, dépôt, ordres), sans rien inventer. Comparer à
  `AIPL.settings` (demandé) permet de détecter une construction partielle (ex. mesuré :
  `num_trains=50` demandés, 17 réellement construits, faute d'argent).
- **Angle mort persistant** : un échec pathfinder (aucune route trouvée) et un échec financier total
  (aucun train acheté) produisent tous les deux "0 construit" — strictement indiscernables l'un de
  l'autre sans un canal de sortie que je n'ai pas trouvé de moyen de faire fonctionner via
  OpenTTDLab. `TrainLineAI` maintient un état structuré interne (`this.state`, retourné par `Save()`)
  qui documente la cause exacte si vous inspectez le savegame par un autre moyen plus tard.

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
