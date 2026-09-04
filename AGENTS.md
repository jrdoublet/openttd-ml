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
