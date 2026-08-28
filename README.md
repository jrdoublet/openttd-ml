# openttd-ml

Peut-on prédire le profit d'une ligne ferroviaire à partir de ses caractéristiques de
construction, sans simuler la partie ? Voir `docs/methode.md` pour le protocole complet.

## OpexAI

`ai/OpexAI/` est l'IA de production actuelle, ciblée sur OpenTTD 15.3 / API NoAI 15. Elle
construit des lignes ferroviaires ainsi qu'une première liaison aérienne et une première liaison
maritime de passagers. La conception, les invariants de rollback et les validations sont décrits
dans [`docs/opexai_multimodal.md`](docs/opexai_multimodal.md). Les correctifs de rentabilité et de
croissance (modèle économique pax/fret, séparation des lignes, remboursement d'emprunt, détection
des lignes fret mortes) et les pistes envisagées puis écartées sont dans
[`docs/opexai_croissance.md`](docs/opexai_croissance.md).

Les versions et règles de la section Phase 0 ci-dessous restent celles de la campagne historique
de calibration ; elles ne définissent pas la cible d'exécution d'OpexAI.

## Décisions figées (Phase 0)

| Élément | Valeur | Raison |
|---|---|---|
| OpenTTD | `13.4` | Voir note ci-dessous |
| OpenGFX | `7.1` | Version appariée à 13.4 dans les exemples de référence |
| Python | 3.12 | Testé par le projet (3.8.2 minimum) |
| IA de calibration | trAIns, `unique_id='54524149'` | IA de référence utilisée dans les exemples |
| Durée de partie | `days = 365 * 10` | Révisé après la 1ère calibration (`s_per_game` plus bas que prévu) : 10 ans de jeu au lieu des 4 ans de l'exemple officiel |
| Config OpenTTD | voir `OPENTTD_CONFIG` dans `sweeps/phase0_*.py` | Révisée le 2026-08-26 après `phase0_town_distribution` : `inflation=false`, `town_growth_rate=2`, `map_x`/`map_y=8`, `starting_year=1970`, `number_towns=3`, `industry_density=4` — figés explicitement pour les futures cartes |

**Rupture de campagne à 1970.** Le catalogue ferroviaire de 1970 n'est pas celui de 1950 : il
contient des moteurs plus rapides, plus chers et plus nombreux. `engine_rank` ne désigne donc pas
les mêmes locomotives et les coûts de construction ne sont pas directement comparables. Les JSON
antérieurs en 1950/densité 2 restent des artefacts historiques; les mesures 1970/densité 3 forment
une campagne distincte et ne doivent pas être mélangées avec elles.

**Note sur la version.** La documentation d'OpenTTDLab se contredit : la section *Compatibility*
annonce le support des branches 12, 13 et 15+, tandis que l'avertissement sur `run_experiments`
indique que 13.4 est la dernière version connue pour fonctionner. La branche 14.x n'est supportée
dans aucun des deux cas. → On pin 13.4, on note la contradiction ici, on ne teste 15.x que si le
besoin s'en fait sentir.

## Version exacte d'OpenTTDLab

```
OpenTTDLab==0.0.75
```

## MD5 de trAIns

```
c4c069dc797674e545411b59867ad0c2
```
(`ai/54524149`, trAIns 2.1, GPL v2 — obtenu via `download_from_bananas('ai/54524149')`,
utilisé comme `bananas_ai("54524149", "trAIns", md5="c4c069dc797674e545411b59867ad0c2")`
dans `sweeps/phase0_timing.py` et `sweeps/phase0_plot.py`.)

## Installation — VPS (Docker)

```bash
docker build \
  --build-arg UID="$(id -u)" \
  --build-arg GID="$(id -g)" \
  -t openttd-lab .

docker run --rm -it \
  --name openttd-lab \
  --cpus=3 \
  --memory=2g --memory-swap=2g \
  -v openttd-lab-home:/home/lab \
  -v "$PWD":/work \
  -w /work \
  openttd-lab bash
```

- `--build-arg UID` / `GID` — construit l'utilisateur `lab` avec votre identité hôte pour que
  les écritures dans le dépôt monté gardent les bonnes permissions, tout en donnant accès à son
  volume `/home/lab` persistant.
- `--cpus=3` — laisse un cœur pour Traefik, Netdata et le reste de la stack.
- `--memory-swap=2g` égal à `--memory` — désactive le swap : le conteneur se fait tuer proprement
  au lieu d'entraîner l'hôte dans une saturation.
- Volume nommé sur `/home/lab` — cache persistant pour OpenTTD/OpenGFX/IA téléchargés par
  OpenTTDLab, pour éviter de tout retélécharger à chaque `docker run`.

**Alerte Netdata : pas encore faite.** Netdata n'est pas déployé sur ce VPS actuellement — à poser
avant la première vraie campagne de nuit (voir la stack Docker existante du VPS pour l'intégrer
proprement, ex. via `socket-proxy` comme les autres outils d'observabilité de ce serveur).

## Calibration (Phase 0)

```bash
MACHINE=vps python sweeps/phase0_timing.py   # coût unitaire, point d'inflexion du parallélisme
python sweeps/phase0_plot.py                 # graphique company_value x date sur 10 graines
```

### Résultats — VPS (4 CPU hôte, conteneur `--cpus=3`), `days = 365 * 10`, batch fixe de 24 graines

Chaque niveau de worker exécute le **même batch de 24 graines** (`sweeps/phase0_timing.py`,
`BATCH_SEEDS`) — mesure du vrai coût marginal du parallélisme, pas de l'artefact "on lance
`workers` parties pour `workers` workers" (qui gardait le wallclock artificiellement plat).

| workers | wallclock (s) | s/partie | rows |
|---|---|---|---|
| 1 | 884.1 | 36.8 | 2856 |
| 2 | 448.2 | 18.7 | 2856 |
| 3 | 306.2 | 12.8 | 2856 |
| 4 | 319.6 | 13.3 | 2856 |

**Point d'inflexion : `max_workers=3`.** Sur un batch fixe, 4 workers est **strictement pire** que 3
(wallclock 319.6 vs 306.2, `s_per_game` 13.3 vs 12.8) — cohérent avec la limite `--cpus=3` du
conteneur, mais démontré cette fois sur un vrai volume de travail plutôt que déduit d'un design de
mesure qui gonflait le nombre de parties avec le nombre de workers. `max_workers=3` confirmé pour
la production sur ce VPS.

*Mesures précédentes, design "N parties pour N workers" (non fiables pour le scaling, conservées
pour mémoire) : 4 ans → 12.9/6.4/4.3/4.3 s ; 10 ans → 34.9/17.4/12.9/12.6 s, pour 1/2/3/4 workers.*

**Granularité temporelle.** ~119 lignes par partie de 10 ans ≈ un savegame par mois (`autosave=monthly,
keep_all_autosave=true` sur les versions OpenTTD 12–13.x). Granularité mensuelle pour les savegames,
**trimestrielle** pour les données économiques exploitables (`old_economy`, voir plus bas).

**Débit de production (VPS, s_per_game_optimal = 12.8s à 3 workers) :**

```
parties_par_jour_vps = 24 * 3600 / 12.8 ≈ 6 750 parties/jour
```

### Laptop / sharding — non applicable

La section 2 de la spec ignore l'installation portable pour cette phase. Sans second point de
mesure, `docs/phase0_laptop.json`, le calcul de `ratio_sharding` et le test de déterminisme
inter-machines (section 5) ne s'appliquent pas — VPS seul pour l'instant. À reprendre si une
seconde machine est ajoutée au projet.

Graphique produit : `docs/phase0_company_value_vs_date.html` (données brutes dans
`docs/phase0_company_value_vs_date.csv`), `company_value` par trimestre sur 10 graines (300–309),
IA trAIns, 10 ans de jeu, `max_workers=3`. 39 trimestres par graine, de 1950-01-01 à 1959-07-01.

*Première version du graphique (`docs/phase0_money_vs_date.html`, `money` brut, 4 ans de jeu,
conservée pour référence) : c'est elle qui a révélé le problème ci-dessous.*

## Le capital brut est un mauvais indicateur de succès

Sur le graphique `money`, les graines 300 et 304 culminent à ~400 k puis retombent à ~3 400.
Inspection du chunk `PLYR` complet (`sweeps/phase0_explore.py`) : `money` ne tient pas compte de
`current_loan`. Exemple concret tiré du run : `money=289299` avec `current_loan=300000` →
trésorerie nette réelle **négative** (-10 701) alors que `money` seul a l'air positif. Une IA qui
emprunte gonfle `money` sans avoir rien construit ; quand elle rembourse (ou se fait rappeler le
prêt), `money` s'effondre sans que ça reflète un échec économique réel.

**La bonne source : `old_economy.company_value`, pas `money`.** Confirmé par inspection directe
(`sweeps/phase0_explore3.py`) : `PLYR.<company>.old_economy` est une liste de trimestres clos
(index 0 = le plus récent) avec `income`, `expenses`, `company_value`, `delivered_cargo`,
`performance_history`. `company_value` est net de l'emprunt (un prêt déplace de la dette vers du
cash, ne bouge pas la valeur d'entreprise) — le graphique regénéré avec `company_value` ne montre
plus les pics/chutes brutaux de la version `money`.

**Piège vérifié en la construisant : la clé de dédup.** Un premier essai dédupliquait sur
`(seed, len(old_economy))` — `old_economy` est une fenêtre glissante plafonnée à 24 entrées (6 ans),
`len()` se bloque à 24 après coup, donc cet essai tronquait silencieusement toutes les séries à 6 ans
sur des parties de 10 ans, sans erreur. Corrigé dans `sweeps/phase0_plot.py` en dédupliquant sur la
date calendaire réelle du trimestre clos (déduite de la date du savegame), robuste quelle que soit
la profondeur de la fenêtre glissante. Détail dans `docs/methode.md`.

`docs/methode.md` fixait déjà la métrique sur le **profit** (pas le capital brut) — cette
observation confirme que c'était le bon choix, précise la source exacte à utiliser en phase 2, et
écarte `money` seul comme feature ou comme proxy de succès. Reste non résolu : `old_economy` est
agrégé au niveau de la compagnie entière, pas par ligne — la descente au niveau ligne (l'unité
d'observation de `methode.md`) demandera une source supplémentaire (véhicules/stations), à explorer
en phase 2.

## ParameterisedAI — le paramètre atteint bien l'IA et change le résultat

[`ParameterisedAI`](https://github.com/michalc/ParameterisedAI) (commit
`74662403e0764329112dc78e5b279d7f1b5fd510`, fixé dans `ai/ParameterisedAI/`) est un bus AI dont le
seul paramètre, `maximum_buses`, est déclaré dans `info.nut` (`AddSetting`) et importé via
`import("pathfinder.road", "RoadPathFinder", 4)` — nécessite la librairie
`bananas_ai_library('5046524f', 'Pathfinder.Road')`. Usage confirmé sur le propre test de
régression du dépôt (`local_folder` + cette seule librairie, sans les deux autres mentionnées dans
son README qui ne sont pas nécessaires en pratique).

**Vérification** (`sweeps/phase0_parameterised_ai_check.py`) : même graine (42), deux valeurs de
`maximum_buses` (1 et 8), 2 ans de jeu. Le paramètre brut (`experiment['ais'][0][1]`) est bien
`(('maximum_buses', 1),)` / `(('maximum_buses', 8),)` dans chaque run — il arrive donc jusqu'à
l'expérience. Les deux trajectoires `money` sont identiques jusqu'au premier achat de véhicules
(1950-04-01, 78794 vs 44265 — la version à 8 bus dépense nettement plus en achat initial, cohérent),
puis divergent tout le reste de la partie : **83911 vs 69076 en fin de run**, sur une carte et une
graine strictement identiques. Le paramètre atteint donc bien l'IA et change effectivement le
résultat. Détail complet dans `docs/phase0_parameterised_ai_check.json`.

## TrainLineAI (Phase 2 — préparatoire)

`ai/TrainLineAI/` : squelette fonctionnel et testé de bout en bout, construit une ligne de train
entre deux villes choisies par rang de population, en année 1. Six paramètres déclarés dans
`src/trainlineai_schema.py` — source unique qui génère `info.nut` **et** construit les
`ai_params` Python (`make_ai_params(**valeurs)`), pour qu'un typo ou une valeur hors bornes lève
une erreur Python immédiate plutôt que d'être avalée silencieusement par OpenTTD. Régénérer
`info.nut` après modif du schéma : `python src/trainlineai_schema.py`.

- `num_trains`, `wagons_per_train` : nombre de rames et de wagons par rame.
- `town_a_rank`, `town_b_rank` (0-15, défauts 0/1) : rang dans la liste des villes triée par
  population, au lieu de toujours prendre les deux plus peuplées — fait varier distance et terrain
  d'une observation à l'autre pour une même graine. La config figée révisée (`number_towns=3`)
  produit 46 à 52 villes sur les huit graines diagnostiquées ; `number_towns` reste une densité,
  pas un nombre exact (voir `docs/methode.md`).
- `engine_rank` (0-2, défaut 0) : rang dans la liste des moteurs triée par vitesse, au lieu de
  toujours prendre le plus rapide — casse la colinéarité totale entre matériel et date de
  construction. La borne vient de l'ancien démarrage 1950 (3 moteurs observés). Re-sondage réel à
  1970/densité 3 : **8 moteurs rail constructibles non-wagon** (9 sur la graine 5) — la borne reste
  donc valide mais conservatrice, et le catalogue comme son ordre par vitesse ont bien rompu avec
  1950 (voir la rupture de campagne ci-dessus).
- `line_index` (0-19, défaut 0) : identifiant de tentative, échoïsé dans le panneau de statut —
  rattache un panneau à une tentative précise dès qu'il y en a plusieurs dans la même partie.
- `cargo_index` : pas encore ajouté, prévu une fois les rangs ci-dessus stabilisés.

Emprunte le maximum au premier tick (`AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())`) —
supprime le manque d'argent comme cause d'échec possible ; un échec ne peut plus venir que du
terrain/pathfinder. Pose **trois panneaux** (`AISign.BuildSign`) à chaque tentative : un statut
(`TRLN|<line_index>|<stage>|<raison_courte>|<construits>/<demandés>`) et, dès que les villes sont
choisies, un détail (`TRLN|<line_index>|T<town_a>-<town_b>|D<distance>|C<coût_total>` — paire de
villes, distance à vol d'oiseau, coût de construction total mesuré par `AIAccounting`) et un coût
véhicules (`TRLN|<line_index>|V<coût>` — la part infrastructure se déduit côté Python par
soustraction). Canal confirmé fonctionnel via le chunk `SIGN` du savegame (texte + position +
owner). Les raisons d'échec sont abrégées (`REASON_CODES` dans `main.nut`) car `AISign.BuildSign`
refuse silencieusement tout texte au-delà de 31 caractères — bug trouvé en durcissant ce format :
la quasi-totalité des panneaux d'échec de l'ancien format (raison en toutes lettres) dépassaient
déjà cette limite et ne se posaient donc probablement jamais. Détail complet, y compris un second
bug de portée Squirrel trouvé en corrigeant celui-ci, dans `docs/methode.md`.

`sweeps/debug_ai.py` : lance le binaire OpenTTD en direct (hors OpenTTDLab) avec `-d script=4`
pour voir la sortie `AILog` — le seul moyen trouvé de déboguer un script Squirrel qui échoue
silencieusement. A servi à trouver et corriger plusieurs bugs (voir `docs/methode.md`, section IA).

`sweeps/phase2_vehs_explore.py` : vérifie que `VEHS.<id>.train[0].common[0]` expose bien
`profit_this_year`/`profit_last_year` (uniquement sur le véhicule de tête de chaque train — les
wagons ont ces champs à 0), avant d'investir dans une cible de profit ligne-level construite en
sommant ces champs par ligne (`old_economy` est company-level, non exploitable tel quel). Dump
filtré dans `docs/phase2_vehs_explore.json`. Détail, y compris la nuance profit d'exploitation
(hors voie/gares/infrastructure) vs coût de construction, dans `docs/methode.md`.

`sweeps/phase2_trainline_run.py` : campagne de bout en bout (12 tentatives, 4 graines × 3
combinaisons de rangs, **re-baselinée sur 6 ans** après la correction de trois bugs réels — voir
plus bas), vérifie que les trois panneaux se lisent correctement via le chunk `SIGN` sur un vrai
batch (pas un cas isolé), et calcule `profit_ligne` pour chaque ligne construite (voir ci-dessous).
Résultats bruts dans `docs/phase2_trainline_run.json`, visualisation (jauges + nuage distance/coût
+ barres de profit par ligne + table complète) dans `docs/phase2_trainline_run.html`. À 6 ans, les
12 tentatives sont toutes résolues (0 en attente) : 6 lignes construites, 6 échecs (4
`no_path_found`, 2 `station_build_failed`).

**Trois bugs réels trouvés en creusant un signal suspect** (`sum_profit_this_year` identique au
franc près sur trois graines/distances différentes — impossible par hasard) et corrigés dans
`ai/TrainLineAI/main.nut`, détail complet et vérifications empiriques dans `docs/methode.md` :
1. **Quai d'une seule tuile** : seule la locomotive tenait dessus, les wagons (qui seuls
   transportent du cargo) restaient hors quai en permanence — `platform_length` calculé depuis
   `wagons_per_train` à la place. Bug de portée Squirrel trouvé en l'implémentant (même famille
   que celui de `REASON_CODES`, cette fois entre deux `local` du même `Start()`).
2. **Dépôt raccordé à la mauvaise tuile** : ancré sur la gare elle-même avec une orientation
   arbitraire, sans rapport avec l'axe réel du quai — les deux trains restaient bloqués au dépôt à
   vie (`last_station_visited` jamais renseigné, vérifié empiriquement). Ancré sur `tiles[1]` (la
   première tuile de voie réelle) à la place.
3. **Coût de construction contaminé par l'exploration du pathfinder** : `AIAccounting` ouvert
   avant la recherche de chemin captait les évaluations de coût de pont/tunnel du pathfinder
   (jamais construits) — un échec `no_path_found` rapportait un coût de plus de 55 millions.
   Corrigé en ouvrant `this.costs` après le pathfinding. Effet sur les lignes réussies : coût
   divisé par un facteur ~31 sur le cas de test.

**Un quatrième problème, creusé sur suggestion externe (inspection du code source de trAIns et
d'AdmiralAI), partiellement résolu.** Cause du chargement à zéro identifiée : les ordres
utilisaient `AIOrder.OF_NONE`, qui ne force aucune attente — un train reparaît quasi toujours à
vide sur une ligne neuve à faible fréquentation. Corrigé avec `OF_FULL_LOAD_ANY` (patron trAIns) :
**vérifié empiriquement, les wagons chargent désormais à pleine capacité** (40/40, confirmé via
`cargo.action_counts`) — une première pour ce squelette. Mais le revenu reste à zéro : en traçant
la position du train tick par tick, il ne quitte **jamais** le voisinage immédiat du dépôt même
après des années, alors que la gare de destination est à des dizaines de tuiles — un problème de
**navigation du train**, pas de chargement.

**Sept hypothèses testées pour ce blocage de navigation, aucune ne le résout** (détail et
vérifications empiriques dans `docs/methode.md`) : patron de flags d'ordre symétrique (trAIns) ou
asymétrique (AdmiralAI), position du dépôt éloignée de la gare, signal PBS sur la jonction,
service automatique désactivé. Une collision réelle a été trouvée en cours de route (le premier
offset de placement du dépôt tombait parfois exactement sur la voie principale elle-même, la
coupant en cul-de-sac) — **corriger cette collision fait régresser le résultat** (le train ne
rejoint alors plus aucune gare), donc ce n'est pas la cause principale non plus. Le code retenu
est la version la plus fonctionnelle trouvée (le train atteint au moins la première gare), sans
revendiquer d'avoir compris le blocage. `profit_ligne` reste donc un pur coût de roulement.

`sweeps/phase2_profit_ligne.py` : valide `profit_ligne = Σ(profit_last_year des véhicules de
tête de la ligne) − amortissement(coût véhicules) − amortissement(coût infrastructure)` sur 3
parties isolées avant de l'intégrer à la campagne ci-dessus, en assemblant le profit
d'exploitation (`VEHS`), le coût de construction total et la part véhicules (panneaux).
`profit_last_year` (année complète) plutôt que `profit_this_year` (potentiellement partielle,
mauvaise unité face à un amortissement annuel). Coût véhicules amorti sur `max_age` du matériel
(donnée du jeu) ; coût infrastructure (déduit par soustraction) amorti sur `INFRA_LIFE_YEARS = 30`,
hypothèse assumée et documentée dans `docs/methode.md` — OpenTTD ne modélise aucune durée de vie
pour la voie/les gares, contrairement au matériel roulant. Décision explicite de séparer les deux
plutôt que d'amortir tout sur `max_age` (version précédente) : **piège trouvé en l'implémentant** —
`AIAccounting` ne s'imbrique
pas (un second `AIAccounting` ouvert pendant qu'un premier est encore actif ne repart pas de zéro,
il reflète le même cumul que le premier), corrigé en mesurant le coût véhicules par différence sur
le même `AIAccounting`, avant/après l'achat des trains — détail dans `docs/methode.md`.
`AICompany.GetBankBalance` avant/après essayé pour le coût de construction et rejeté : pollué par
les intérêts du prêt maximal emprunté au premier tick (`GetBankBalance` dérive de 2100 sur ~27
jours sans aucune construction, `AIAccounting.GetCosts()` rapporte correctement 0 sur la même
fenêtre) — détail dans `docs/methode.md`. Résultats dans `docs/phase2_profit_ligne.json`.

Détails complets, bugs trouvés/corrigés, et ce qui a été testé et rejeté (`Save()`, sortie
console) : `docs/methode.md`, section **IA (Phase 2 — préparatoire)**.

## Cannibalisation multi-lignes : le coût réel de l'absence de contrainte de villes disjointes

Question de départ : une même ligne (graine 42, paire de villes T6-2, coût de construction
identique) donne un profit d'exploitation très différent d'une campagne à l'autre — est-ce que
plusieurs lignes IA partagent la même partie et se disputent les mêmes passagers ? Vérifié en
lisant directement le code source d'OpenTTDLab : jusqu'ici, non — chaque expérience tourne dans
son propre processus OpenTTD isolé (une compagnie, une partie). Mais OpenTTDLab sait très bien
démarrer plusieurs compagnies IA dans **une seule partie partagée** si on le lui demande — un
mécanisme jamais utilisé dans ce dépôt avant `sweeps/phase2_multiline_control.py`.

**Mesuré avant de corriger quoi que ce soit** : même graine, même ligne de référence
(`pair_rank=0`, toujours la paire T6-2, coût de construction inchangé à la livre près), 1 puis 5
puis 15 compagnies IA construisant chacune leur propre ligne dans la même partie.

| Compagnies dans la partie | Profit de la ligne de référence | vs isolée |
|---|---|---|
| 1 (isolée) | -154 257 | — |
| 5 | -278 673 | 81 % pire |
| 15 | -690 833 | 348 % pire |

La cannibalisation est réelle, forte, et monotone avec le nombre de lignes concurrentes — pas une
hypothèse.

**Correctif** : contrainte dure dans `ai/TrainLineAI/main.nut` — une ville déjà desservie par une
autre compagnie de la même partie (détectée en scannant les tuiles autour de son centre à la
recherche d'une gare rail, tous propriétaires confondus) est exclue des paires candidates avant
toute sélection. Les démarrages sont échelonnés (`line_index` fixe l'ordre) pour que chaque
compagnie voie bien ce que les précédentes ont déjà construit.

**Re-mesuré après le correctif** :

| Compagnies dans la partie | Profit de la ligne de référence |
|---|---|
| 1 (isolée) | -247 186 |
| 15 | -49 298 |

La dégradation massive et monotone disparaît — à 15 compagnies dans la même partie, la ligne de
référence n'est plus écrasée par la concurrence (ses deux villes ne sont jamais réutilisées).
Effet secondaire observé, conforme à l'attente : le nombre de lignes constructibles par partie
plafonne vite une fois les villes disjointes épuisées (`n_villes/2` est un ordre de grandeur
théorique ; en pratique, avec les filtres population/distance/coût déjà en place, le plafond réel
est atteint plus tôt). Détail complet, limites connues, et un mystère de profit séparé et non
résolu (la comparaison N=1 avant/après correctif n'est elle-même pas stable, pour une raison
encore non identifiée) : `docs/methode.md`.

## Le plancher d'erreur : ce que le modèle ne pourra jamais expliquer

Sur une **même ligne**, construction rigoureusement identique, en ne changeant que le décalage de
timing de l'IA (un `Sleep` de 0 à 200 ticks avant qu'elle n'agisse), `profit_ligne` varie de plus
d'un million. Deux observations aux features identiques, séparées d'un million sur la cible :
aucune régression ne peut prédire les deux. C'est le plancher d'erreur du projet.

L'hypothèse naturelle était que des villes trop petites rendaient chaque ligne dépendante d'une
poignée de passagers. Elle a été testée : configuration révisée (densité 3, départ 1970, villes
plus grandes et profits plus élevés), même balayage de délais, sur trois lignes différentes.

| | 1950 / densité 2 | 1970 / densité 3 |
|---|---:|---:|
| amplitude du balayage | 667 136 | 968 704 à 1 583 360 |
| ratio amplitude / étendue entre lignes réelles¹ | 0,163 | 0,148 à 0,242 |

¹ *À design de dénominateur comparable des deux côtés (rangs 0 et 5). Comparer au dénominateur
historique complet donnerait 0,067 et laisserait croire à tort à une dégradation — artefact de
design, pas signal.*

**L'amplitude ne s'effondre pas, elle augmente ; le ratio ne bouge pas.** La taille des villes
n'était donc pas la cause. Le bruit de timing représente environ un cinquième de l'écart entre
deux lignes réellement différentes, avant comme après.

### Le plancher est supprimable : normaliser le moment de la construction

La construction elle-même était déjà reproductible au tick près (38 ticks). La fenêtre variable
était le **preflight** — sélection de paire et pathfinding — mesuré sur 30 routes à 678 ticks au
minimum, 957 en médiane, 4397 au maximum. D'où une **barrière** : une fois tout le preflight
terminé et avant de toucher la moindre tuile, l'IA attend jusqu'au tick absolu 11000. La première
estimation à 5000 était limitée aux rangs 0..40; la mesure 0..150 (86 mutations) atteint 9916,
donc 11000 les couvre avec 1084 ticks de marge (~4,1 % de la partie). En multi-compagnies la cible
reste échelonnée (`11000 + stagger_slot × 6000`) pour préserver l'ordre
de visibilité dont dépend la contrainte de villes disjointes ; `line_index` reste seulement
l'identifiant affiché, afin que les campagnes isolées ne soient jamais retardées par leur numéro.

Même balayage de délais, barrière active, mêmes trois lignes :

| Ligne | amplitude avant | amplitude après |
|---|---:|---:|
| graine 42 | 1 219 072 | **0** |
| graine 1 | 1 583 360 | **0** |
| graine 7 | 968 704 | **0** |

Les sept points de délai donnent un profit **rigoureusement identique**. Le plancher d'erreur dû
au timing passe du million à zéro.

Deux réserves assumées. Normaliser *quand* la construction démarre ne rend pas la simulation
insensible au timing absolu : cela rend les runs comparables entre eux, rien de plus. Et puisque
la construction se produit maintenant au tick 11000 et non vers 950, **les valeurs de profit
changent** (graine 42 : +1 719 409 avant, +1 352 050 après) : c'est une nouvelle rupture de
campagne, au même titre que 1950 → 1970. Chaque ligne signale désormais dans ses panneaux si elle
a respecté la barrière (`M`) ou l'a dépassée (`O`) — une ligne `O` n'est pas comparable aux
autres.

La baseline fraîche `docs/phase2_baseline_v3.json` est la première campagne à cible
temporellement reproductible sur tout son domaine échantillonné : 100 lignes isolées, 75 construites / 25 échecs (19 `PATHLIM`, 6
`TRKFAIL`). Les buckets 0–24, 25–49, 50–74 et 75–120 réussissent à 88 %, 88 %, 68 % et 56 %.
Les 75 lignes bâties sont normalisées (`M`; 0 `O`) et forment la nouvelle cible comparable.

Détail, contrôles successifs et faisabilité d'une construction « en pause » (impossible : la pause
fige aussi l'ordonnanceur d'IA) dans `docs/methode.md` et `docs/pause_feasibility_findings.md`.

## Prochaines étapes

- [x] Lancer une campagne multi-graines avec `TrainLineAI` pour mesurer le taux d'échec réel
      (terrain/pathfinder) une fois l'argent neutralisé — `sweeps/phase2_trainline_run.py`,
      12 tentatives, re-baselinée sur 6 ans : 6 construites, 6 échecs, 0 en attente
- [x] Descendre `old_economy` (company-level) au niveau ligne : `VEHS.<id>.train[0].common[0]`
      expose `profit_this_year`/`profit_last_year` par véhicule de tête — `profit_ligne` calculé
      et testé (`sweeps/phase2_profit_ligne.py`)
- [x] Revoir l'amortissement de `profit_ligne` : coût véhicules et coût infrastructure séparés,
      chacun amorti sur son propre horizon (`max_age` pour le matériel, 30 ans assumés pour
      l'infrastructure — voir `docs/methode.md`)
- [ ] **Corriger la navigation du train vers la gare d'arrivée, toujours bloquée.** Le chargement
      de cargo (zéro auparavant) est résolu (`OF_FULL_LOAD_ANY`, wagons à pleine capacité
      confirmé) mais le train ne quitte jamais le voisinage du dépôt. Sept hypothèses testées
      (flags d'ordre, position du dépôt ×2, signal PBS, service automatique, collision dépôt/voie)
      **toutes écartées empiriquement** — voir `docs/methode.md`, bug 4. Recommandation : accès
      visuel réel au jeu (capture d'écran / observation directe) plutôt que d'autres itérations à
      l'aveugle sur des coordonnées. **Bloquant pour tout signal de rentabilité réel** —
      `profit_ligne` ne reflète pour l'instant que des coûts de roulement.
- [ ] Construire le jeu de données du modèle hurdle (classifieur constructible + régression
      profit conditionnelle, voir `docs/methode.md`) — les briques existent (panneaux, `VEHS`,
      `profit_ligne`) et l'étage 1 (constructible/non) est déjà exploitable ; l'étage 2 (régression
      profit) attend la résolution du bug de chargement ci-dessus
- [x] Orchestrateur multi-lignes par partie (plusieurs instances de `TrainLineAI` dans la même
      expérience), avec contrainte de villes disjointes — voir section **Cannibalisation
      multi-lignes** ci-dessous et `docs/methode.md`. Distance minimale entre lignes : toujours
      pas traitée, piste future.

**Explicitement hors scope pour la suite du projet** (décision utilisateur) : le confondant
matériel × date de construction (3 moteurs jugés suffisants pour les tests actuels) et l'alerte
mémoire Netdata sur le conteneur.

## Checklist de sortie de phase 0

- [x] Dépôt git initialisé, versions figées dans `requirements.txt`
- [x] Conteneur VPS avec limites CPU/mémoire, volume de cache persistant
- [ ] Alerte Netdata — **pas encore faite**, Netdata non déployé sur ce VPS
- [ ] WSL2 plafonné sur le portable — non applicable (portable ignoré en phase 0)
- [x] `docs/phase0_vps.json` produit — `docs/phase0_laptop.json` non applicable
- [x] `max_workers` optimal déterminé sur le VPS (3) — non applicable sur portable
- [ ] Déterminisme inter-machines — non applicable, une seule machine pour l'instant
- [x] MD5 de trAIns noté et épinglé (`c4c069dc797674e545411b59867ad0c2`)
- [x] `docs/methode.md` rédigé
- [x] Un graphique company_value × date sur 10 graines, commité — premier résultat
- [x] Inflation désactivée et figée explicitement (`inflation = false`)
- [x] Config OpenTTD figée (map, année de départ, villes, industries)
- [x] Source de métrique fiable identifiée (`old_economy`, trimestriel, net de l'emprunt)
- [x] Mesure de scaling refaite sur batch fixe (coût marginal réel, pas un artefact de design)
