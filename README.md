# openttd-ml

Peut-on prédire le profit d'une ligne ferroviaire à partir de ses caractéristiques de
construction, sans simuler la partie ? Voir `docs/methode.md` pour le protocole complet.

## Décisions figées (Phase 0)

| Élément | Valeur | Raison |
|---|---|---|
| OpenTTD | `13.4` | Voir note ci-dessous |
| OpenGFX | `7.1` | Version appariée à 13.4 dans les exemples de référence |
| Python | 3.12 | Testé par le projet (3.8.2 minimum) |
| IA de calibration | trAIns, `unique_id='54524149'` | IA de référence utilisée dans les exemples |
| Durée de partie | `days = 365 * 10` | Révisé après la 1ère calibration (`s_per_game` plus bas que prévu) : 10 ans de jeu au lieu des 4 ans de l'exemple officiel |
| Config OpenTTD | voir `OPENTTD_CONFIG` dans `sweeps/phase0_*.py` | `inflation=false`, `map_x`/`map_y=8`, `starting_year=1950`, `number_towns=2`, `industry_density=4` — figés pour ne pas dépendre d'un défaut qui changerait entre deux versions |

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
docker build -t openttd-lab .

docker run --rm -it \
  --name openttd-lab \
  --cpus=3 \
  --memory=2g --memory-swap=2g \
  -v openttd-lab-home:/home/lab \
  -v "$PWD":/work \
  -w /work \
  openttd-lab bash
```

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
  d'une observation à l'autre pour une même graine. Bornes vérifiées empiriquement (23 à 30 villes
  observées sur la carte figée, `number_towns=2` étant une densité, pas un nombre — voir
  `docs/methode.md`).
- `engine_rank` (0-2, défaut 0) : rang dans la liste des moteurs triée par vitesse, au lieu de
  toujours prendre le plus rapide — casse la colinéarité totale entre matériel et date de
  construction. Seuls 3 moteurs rail sont disponibles en 1950 avec l'OpenGFX de base, d'où la borne.
- `line_index` (0-19, défaut 0) : identifiant de tentative, échoïsé dans le panneau de statut —
  rattache un panneau à une tentative précise dès qu'il y en a plusieurs dans la même partie.
- `cargo_index` : pas encore ajouté, prévu une fois les rangs ci-dessus stabilisés.

Emprunte le maximum au premier tick (`AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())`) —
supprime le manque d'argent comme cause d'échec possible ; un échec ne peut plus venir que du
terrain/pathfinder. Pose **deux panneaux** (`AISign.BuildSign`) à chaque tentative : un statut
(`TRLN|<line_index>|<stage>|<raison_courte>|<construits>/<demandés>`) et, dès que les villes sont
choisies, un détail (`TRLN|<line_index>|T<town_a>-<town_b>|D<distance>|C<coût>` — paire de villes,
distance à vol d'oiseau, coût de construction mesuré par `AIAccounting`). Canal confirmé
fonctionnel via le chunk `SIGN` du savegame (texte + position + owner). Les raisons d'échec sont
abrégées (`REASON_CODES` dans `main.nut`) car `AISign.BuildSign` refuse silencieusement tout texte
au-delà de 31 caractères — bug trouvé en durcissant ce format : la quasi-totalité des panneaux
d'échec de l'ancien format (raison en toutes lettres) dépassaient déjà cette limite et ne se
posaient donc probablement jamais. Détail complet, y compris un second bug de portée Squirrel
trouvé en corrigeant celui-ci, dans `docs/methode.md`.

`sweeps/debug_ai.py` : lance le binaire OpenTTD en direct (hors OpenTTDLab) avec `-d script=4`
pour voir la sortie `AILog` — le seul moyen trouvé de déboguer un script Squirrel qui échoue
silencieusement. A servi à trouver et corriger plusieurs bugs (voir `docs/methode.md`, section IA).

`sweeps/phase2_vehs_explore.py` : vérifie que `VEHS.<id>.train[0].common[0]` expose bien
`profit_this_year`/`profit_last_year` (uniquement sur le véhicule de tête de chaque train — les
wagons ont ces champs à 0), avant d'investir dans une cible de profit ligne-level construite en
sommant ces champs par ligne (`old_economy` est company-level, non exploitable tel quel). Dump
filtré dans `docs/phase2_vehs_explore.json`. Détail, y compris la nuance profit d'exploitation
(hors voie/gares/infrastructure) vs coût de construction, dans `docs/methode.md`.

`sweeps/phase2_trainline_run.py` : première campagne de bout en bout (12 tentatives, 4 graines ×
3 combinaisons de rangs, 3 ans de jeu), vérifie que les deux panneaux se lisent correctement via
le chunk `SIGN` sur un vrai batch (pas un cas isolé), et calcule `profit_ligne` pour chaque ligne
construite (voir ci-dessous). Résultats bruts dans `docs/phase2_trainline_run.json`, visualisation
(jauges + nuage distance/coût + barres de profit par ligne + table complète) dans
`docs/phase2_trainline_run.html`. 5 lignes construites, 3 échecs (1 `no_path_found`, 2
`station_build_failed`), 4 encore en construction au-delà des 3 ans de jeu accordés — la queue
lente est réelle, pas un artefact (voir `docs/methode.md`).

`sweeps/phase2_profit_ligne.py` : valide `profit_ligne = Σ(profit_this_year des véhicules de
tête de la ligne) − amortissement(coût de construction)` sur 3 parties isolées avant de l'intégrer
à la campagne ci-dessus, en assemblant le profit d'exploitation (`VEHS`) et le coût de
construction (panneau de détail). Amortissement sur `max_age` du matériel (déjà présent dans le
savegame, pas une durée inventée) — simplification assumée (amortit voie et gares sur la durée de
vie du matériel roulant, plus courte que la leur) documentée dans `docs/methode.md`.
`AICompany.GetBankBalance` avant/après essayé pour le coût de construction et rejeté : pollué par
les intérêts du prêt maximal emprunté au premier tick (`GetBankBalance` dérive de 2100 sur ~27
jours sans aucune construction, `AIAccounting.GetCosts()` rapporte correctement 0 sur la même
fenêtre) — détail dans `docs/methode.md`. Résultats dans `docs/phase2_profit_ligne.json`.

Détails complets, bugs trouvés/corrigés, et ce qui a été testé et rejeté (`Save()`, sortie
console) : `docs/methode.md`, section **IA (Phase 2 — préparatoire)**.

## Prochaines étapes

- [ ] Lancer une campagne multi-graines avec `TrainLineAI` pour mesurer le taux d'échec réel
      (terrain/pathfinder) une fois l'argent neutralisé
- [ ] Descendre `old_economy` (company-level) au niveau ligne : source à identifier parmi les
      chunks véhicules/stations (`VEHS`/`STNN`/`ORDR`) pour attribuer un profit par ligne
- [ ] Construire le jeu de données du modèle hurdle (classifieur constructible + régression
      profit conditionnelle, voir `docs/methode.md`)
- [ ] Alerte mémoire Netdata sur le conteneur — toujours pas faite (Netdata non déployé sur ce VPS)
- [ ] Traiter le confondant matériel × date de construction avant tout entraînement (voir
      `docs/methode.md`)
- [ ] Orchestrateur multi-lignes par partie (plusieurs instances de `TrainLineAI` avec des rangs
      différents dans la même expérience) : à écrire pour diviser le coût par observation, avec la
      contrainte villes disjointes / distance minimale entre lignes (voir `docs/methode.md`)

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
