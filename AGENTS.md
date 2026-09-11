# Guidelines et Modèles pour OpenTTD-ML / OpexAI

Ce fichier contient les règles d'architecture et les modèles canoniques pour le développement et l'évaluation sur ce projet.

---

## 1. Modèle canonique pour les scripts de benchmark et diagnostic (`sweeps/*.py`)

Tout script exécutant `openttdlab.run_experiments` doit respecter STRICTEMENT ce canevas pour éviter les erreurs d'exécution récurrentes.

### Piège critique n°1 : `result_processor=keep`
`keep(row)` DOIT retourner un **tuple contenant le dictionnaire** : `return ({ ... },)`.
Si `keep(row)` retourne un dictionnaire directement `return { ... }`, Python itère sur les clés (`['arm', 'seed', ...]`), corrompant la liste des résultats en liste de chaînes (`TypeError: string indices must be integers, not 'str'`).

### Piège critique n°2 : Structure des chunks OpenTTD 15.3
- **Économie** : Ne pas utiliser `cur_economy` pour la valeur (vaut 0). Utiliser `old_economy` du joueur 0 :
  ```python
  chunks = row.get("chunks", {})
  player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
  closed = (player or {}).get("old_economy") or []
  last_closed = closed[0] if closed else {}
  company_value = last_closed.get("company_value", 0)
  perf_hist = last_closed.get("performance_history", 0)
  profit_yr = year_profit(closed) if closed else 0
  profit_qtr = quarter_profit(last_closed) if last_closed else 0
  ```
- **Véhicules & Stations** :
  ```python
  n_vehicles = len(chunks.get("VEHS", {}))
  n_stations = len(chunks.get("STNN", {}))
  ```
- **Notes de gare** (`STNN.goods.rating`) :
  ```python
  stnn = chunks.get("STNN", {})
  stations_list = stnn.values() if isinstance(stnn, dict) else stnn
  ratings = [g["rating"] for s in stations_list for g in s.get("goods", []) if g.get("rating", 0) > 0]
  med_rating = statistics.median(ratings) if ratings else 0
  ```
- **Métadonnées de l'expérience** :
  ```python
  arm = row["experiment"]["bench_arm"]
  seed = row["experiment"]["seed"]
  ```

### Modèle de code réutilisable

```python
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import sys

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
STARTING_YEAR = 1970

_real_check_output = openttdlab.subprocess.check_output
def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)
openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_EVENT_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")

def parse_decisions(output):
    counts = Counter()
    for line in (output or "").splitlines():
        m = OPEX_EVENT_RE.search(line)
        if m:
            counts[m.group(4)] += 1
    return counts

def keep(row):
    chunks = row.get("chunks", {})
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    dec = parse_decisions(row.get("output", ""))
    py = year_profit(closed)

    stnn = chunks.get("STNN", {})
    stations_list = stnn.values() if isinstance(stnn, dict) else stnn
    ratings = [g["rating"] for s in stations_list for g in s.get("goods", []) if g.get("rating", 0) > 0]
    med_rating = statistics.median(ratings) if ratings else 0

    return ({
        "arm": row["experiment"]["bench_arm"],
        "seed": row["experiment"]["seed"],
        "company_value": last_closed.get("company_value", 0),
        "profit_year": py if py is not None else 0,
        "profit": quarter_profit(last_closed) or 0,
        "performance_history": last_closed.get("performance_history", 0),
        "median_station_rating": med_rating,
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "decisions": dict(dec),
    },)  # ⚠️ VIRGULE OBLIGATOIRE : tuple à 1 élément
```

---

## 2. Règles de modification et outils de code

1. **Création de fichiers hors artifacts** : Toujours utiliser `run_command` avec `cat << 'EOF' > path` ou `write_to_file` SANS ArtifactMetadata si la destination est hors du répertoire d'artifacts.
2. **Exécution Docker** : Toujours passer par `docker run --rm -v "$PWD":/work -w /work openttd-lab python3 ...`.
3. **Validation statistique** : Tout changement dans le comportement IA doit être validé par :
   - Un diagnostic 5 graines × 6 ans pour vérifier les grandeurs physiques et le sens de l'effet.
   - Un banc officiel 20 graines × 10 ans apparié avant toute adoption par défaut.

---

## 2 bis. 🔴 Les résultats antérieurs au 2026-09-09 ne font PLUS foi

**Décision utilisateur, 2026-09-11.** Les ~320 fichiers de `results/` produits avant cette date ont
été archivés (`results/archive_2026-09-0*.tar.gz`) et retirés de l'arbre de travail. La raison n'est
pas la place disque : **le code a trop changé depuis pour qu'ils mesurent encore l'IA d'aujourd'hui.**

- ⛔ **Ne jamais citer un de ces fichiers comme preuve**, ni dans une fiche, ni dans un commit, ni
  pour arbitrer une décision. Si un chiffre ancien compte, **le re-mesurer**.
- ⚠️ Quatre citations de `docs/taches.md` pointent encore vers des fichiers archivés
  (`bench_floor_3y_20seeds.json`, `bench_1v1_3y_1aeefe1_20seeds.json`,
  `diag_c41_3b_water_site_profile_6y_5seeds.json`, `diag_constants_binding_6y_5seeds_v2.json`).
  Elles sont marquées sur place ; les chiffres qu'elles portent sont **à re-mesurer avant tout
  usage**, pas à reprendre.
- C'est la généralisation d'une leçon déjà payée deux fois : C47 (un chiffre effondré d'un facteur
  36 en deux jours) et C55 (une thèse d'archive réfutée sur le code du jour).

## 3. Bibliothèques tierces vendorisées (`ai/library/`)

`ai/library/SuperLib-41`, `ai/library/MinchinWeb_s_MetaLibrary-11` et `ai/library/Queue.SortedList-3`
sont présentes sur le disque (vendorisées le 2026-09-09) mais **aucune n'est encore importée** par
`ai/OpexAI/main.nut` — seul `import("pathfinder.rail", "RailPathFinder", 1)` y figure. Ne jamais
supposer qu'une de ces bibliothèques est utilisée sans vérifier l'`import` réel dans `main.nut`.

- **Licence.** Le projet est déjà lié au copyleft GPLv2 via `pathfinder.rail` : importer `SuperLib`
  (GPLv2) ne change donc pas le statut de licence du dépôt. `MinchinWeb's MetaLibrary` est
  MIT/Expat, sauf son `RoadPathFinder` en LGPLv2.1. Contrairement à `ai/AAAHogEx-115/` et
  `ai/AdmiralAI/` (GPLv3, volontairement non versionnées — voir `.gitignore` — pour ne pas rendre
  le dépôt dérivé de leur licence), ces trois bibliothèques ne sont PAS gitignorées : elles sont
  prévues pour être committées si elles sont adoptées, pas seulement lues en référence.
- **Décision (utilisateur, 2026-09-09) : commencer par réutiliser une bibliothèque externe plutôt
  que retoucher le BFS interne.** `MinchinWeb.Lakes`/`Pathfinder.Ship` (`Lakes.nut`, `Marine.nut`)
  répondent directement à deux bugs confirmés dans
  [`docs/01_opex_builder_water_review.md`](docs/01_opex_builder_water_review.md) et revérifiés
  dans le code actuel (voir `docs/taches.md`) : c'est le point de départ retenu pour
  `builder_water.nut`, avant d'écrire un seul correctif fait maison sur le BFS ou la marge de
  bounding-box existants.
- **Licence, vérifié fichier par fichier (2026-09-09), pas seulement le `.gitignore`.**
  `SuperLib-41/license.txt` = GPLv2 texte intégral. `MinchinWeb_s_MetaLibrary-11/license.txt` =
  licence maison permissive (« use, copy, modify, merge, publish, distribute, sublicense,
  and/or sell »), sauf l'en-tête propre de `Pathfinder.Road.nut` qui se déclare **LGPLv2.1**. Les
  trois cas autorisent la copie ; seule obligation : conserver les en-têtes de copyright des
  fichiers copiés.
- **Copier plutôt qu'importer, si l'API déclarée pose un souci.** `SuperLib` déclare
  `GetAPIVersion() = "15"` contre le `"13"` d'`OpexAI/info.nut` ; `MinchinWeb` a sa ligne
  `GetAPIVersion()` commentée. Avant de résoudre ce mismatch, vérifier le **graphe de dépendances
  inter-fichiers** (grep `_SuperLib_X::`/`MinchinWeb.X.Y(` croisés) : `engine.nut`, `town.nut`,
  `station.nut`, `airport.nut` sont chacun autonomes (zéro appel vers un autre module), donc
  copiables fonction par fonction sans emporter le reste de la lib. Seul le bloc eau
  (`Lakes`+`Marine`+`Pathfinder.Ship`+`WBC`, ~2000 lignes) a une dépendance interne
  (`Constants`, et `ShipPathfinder↔WBC` via `OverrideWBC`).
- **🔴 Avant de toucher au temps de trajet RAIL avec une de ces bibliothèques : LIRE `docs/taches.md`
  §C41 D'ABORD (`C41.9` à `C41.40`+, grep `C41` obligatoire).** `SuperLib.Engine.GetFullSpeedTraveltime`
  est une formule à un terme (`maxSpeed/27`, aucune accélération). `catalog.nut::OpexRailEffectiveSpeed`
  fait déjà une recherche dichotomique de vitesse de croisière + accélération + intégration, indexée
  `(locomotive, wagon, wagons, distance)`, **avec cache adopté par défaut sur banc officiel 20×10**
  (pax : C41.30 ; fret : C41.38/C41.40). La copier pour le rail serait une **régression mesurable**,
  pas une amélioration. Le rail est **hors périmètre** pour toute bibliothèque de temps de trajet.
- **🔴 La note municipale n'est PAS un bug ouvert.** `OpexBoostTownRating` (`candidates.nut:1935`)
  compare déjà `AITown.GetRating` à `AITown.TOWN_RATING_MEDIOCRE`, le bon enum — **corrigé le
  2026-09-02**, voir [[aitown_getrating_est_un_enum]] (lire la mémoire en entier, pas seulement son
  titre : elle dit explicitement « corrigé »). Ce que `SuperLib.Town.TownRatingAllowStationBuilding`
  apporterait de neuf n'est **pas** ce correctif — c'est un usage différent : un **filtre proactif**
  (écarter une ville sous le seuil de refus *avant* de dépenser des opcodes en recherche de site),
  qui n'existe nulle part aujourd'hui (`AITown.GetRating` n'est appelé que dans
  `OpexBoostTownRating`, jamais en amont). Non mesuré, non implémenté — voir `docs/taches.md`.
- **Plan de réutilisation par module, tel que discuté et priorisé le 2026-09-09** (aucun n'est
  encore implémenté) :
  1. **Air — `airportDelayDays`.** `builder_air.nut::OpexAirTripModel` utilise une constante
     **fixe à 3.0 jours**, quel que soit le type d'aéroport des deux côtés.
     `SuperLib.Engine.GetAircraftTravelTime` a une table par type (small/commuter/large/
     metropolitan/international/intercon, 5 à 10 jours, additionnée aux deux bouts) — mais
     SuperLib dit lui-même dans son propre commentaire que ces valeurs sont devinées
     (*"just been guessed"*). Un diagnostic mesurant le délai réel par type d'aéroport doit
     précéder tout remplacement de la constante, sinon on échange une constante devinée contre
     une table également devinée. L'air pèse ~64 % du capital (voir
     [[opexai_prix_rail_terrain]]) : c'est le seul item où le gain potentiel justifie la mesure.
  2. **Route — `OpexRoadLineEconomics`.** Modèle déjà dérate (`ROAD_SPEED_EFFICIENCY_PCT`), pas
     un maxSpeed brut : `SuperLib` n'apporte pas un meilleur modèle ici (le sien est plus cru que
     le nôtre). Le vrai sujet est l'audit de `ROAD_SPEED_EFFICIENCY_PCT` déjà ouvert en C43/E3
     (« justifiée contre une constante rail supprimée depuis »), pas un remplacement par SuperLib.
  3. **Gare — catchment.** `SuperLib.Station::GetAcceptanceCoverageTiles`/`GetSupplyCoverageTiles`
     donnent les tuiles réelles, contre les approximations `road_pax_catchment_pct`/
     `road_stop_catchment_houses`. Pas encore chiffré.
  4. **Eau — le chantier principal**, voir le point licence/dépendances ci-dessus et
     `docs/taches.md`.
  5. **Aéroports — `SuperLib.Airport`** (placement, bruit, acceptation avant construction) : le
     poste le plus cher (64 % du capital) et le plus défaillant (7× `ERR_FLAT_LAND_REQUIRED` +
     1× `ERR_AREA_NOT_CLEAR` sur 20 tentatives), mais le plus gros chantier de la liste (1117
     lignes). Après l'eau.
  6. **`Pathfinder.Road.nut`** (LGPLv2.1, le seul fichier hors GPLv2/MIT du lot) : en dernier.

## 4. Filtrer une revue externe générique avant d'en tirer une tâche

`docs/00_conseils.md` est une synthèse générique de bonnes pratiques NoAI (wiki OpenTTD + le
benchmark *Redirect Left*), pas une revue du code actuel — plusieurs de ses recommandations sont
déjà appliquées, déjà mesurées et écartées, ou hors sujet pour ce projet. Avant d'agir sur une
revue de ce type, vérifier dans cet ordre :

- **Déjà respecté, pas une tâche.** IDs de cargo (`AICargo.CC_PASSENGERS`/`CC_MAIL`,
  `catalog.nut:734-735`) et de rail (`AIRailTypeList()`, `catalog.nut:320`) déjà résolus
  dynamiquement, jamais en dur. Limite de 31 caractères d'`AISign.BuildSign` déjà découverte et
  documentée (`docs/methode.md`, section panneaux). Piège de capture de closure Squirrel déjà
  documenté ([[squirrel_closure_scoping]], `docs/methode.md`).
- **Déjà mesuré et écarté, ne pas reproposer.** Les arrêts routiers traversants
  (`BuildDriveThroughRoadStation`) ont été testés et abandonnés : 912 232 opcodes pour aucun gain
  mesuré (`builder_road.nut:12`). Les droits exclusifs municipaux ne sont utilisés nulle part dans
  le code ; à laisser ainsi.
- **Ne s'applique PAS ici, à ne jamais implémenter tel quel.** La recommandation d'un `Sleep()`
  défensif dès que `AIController.GetOpsTillSuspend()` passe sous ~2500-3000, pour ne pas ralentir
  un joueur humain partageant la carte, ne vaut pas pour ce projet : OpexAI joue contre une IA
  adverse, pas contre un humain — voir [[philosophie_armes_egales]] et
  [[philosophie_opcodes_ressource]], l'opcode est une ressource à dépenser au mieux, pas à
  économiser par politesse. `GetOpsTillSuspend()` est déjà utilisé (`budget.nut`,
  `builder_air.nut`, `main.nut`), mais pour **mesurer** un coût (télémétrie, panneaux de
  diagnostic), jamais pour brider un `Sleep()`. Ne pas ajouter de throttling CPU « pour ne pas
  gêner le joueur » sans revérifier d'abord le contexte (partie réelle avec des humains, pas le
  banc contre AAAHogEx).
- **Gaps réels, pas encore vérifiés — voir `docs/taches.md`.** Robustesse aux réglages de partie
  (`forbid_90_degree_turns`, un type de véhicule désactivé) jamais testée explicitement ; aucun
  interrupteur `enable_rail`/`enable_road`/`enable_air`/`enable_water` exposé en `info.nut` (le
  portefeuille suppose toujours les quatre modes disponibles) ; empreinte RAM de la VM Squirrel
  jamais mesurée.
