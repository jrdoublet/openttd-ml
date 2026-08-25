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
