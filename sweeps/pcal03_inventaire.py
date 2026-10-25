#!/usr/bin/env python3
"""sweeps/pcal03_inventaire.py — Extraction et inventaire des gros postes d'opcodes précalculables (PCAL-03).

Ce script analyse un dossier `results/<campagne>_engine` (ou des fichiers journaux .log / .log.gz)
issus d'une exécution OpenTTD-ML / OpexAI, filtre la compagnie [0] (OpexAI), et extrait les opcodes
consommés par poste d'après les différentes étiquettes de mesure :
  - SPAN / SPAN_AGG : instrumentations hiérarchiques sous `probe_span_trace=1` (ou `probes & 8 != 0`)
  - LOOP_OPS        : ventilation annuelle de la boucle principale sous `probe_loop_ops=1`
  - RAIL_ATTEMPT    : décomposition des phases rail (phases=plans/search/stations/track/trains) sous `decision_log=1`
  - C76_REGEN       : coûts des régénérations (full/reactive/incremental) sous `probe_catalogue=1`
  - CATALOG_COST    : rapport détaillé du catalogue sous `catalog_cost_probe=1`
  - V257_OPS        : révisions périodiques des moteurs rail sous `decision_log=1`

Configuration recommandée pour une campagne profilée complète (profilage sans biais économique) :
  Réglages OpexAI :
    `probe_span_trace=1,probe_loop_ops=1,probe_catalogue=1,decision_log=1`
    (ou de façon équivalente via le masque probes : `probes=13` -> bits 1+4+8 = signs, decision_log, probes group 8)

Exemples de commandes de lancement de campagne profilée :
  1. Banc solo / diagnostic 1 an sur graine 42 (profil VPS) :
     docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work \\
       openttd-lab python3 sweeps/bench_v2.py \\
       --arms "OpexAI[probe_span_trace=1,probe_loop_ops=1,probe_catalogue=1,decision_log=1]" \\
       --seeds 42 --years 1 --max-workers 3 --out results/pcal03_profil_seed42.json

  2. Duel contre AAAHogEx 3 ans via le harnais hôte :
     python3 sweeps/run_c66_reference.py --campaign pcal03_profil_3x3 \\
       --reference "OpexAI[probe_span_trace=1,probe_loop_ops=1,probe_catalogue=1,decision_log=1]" \\
       --years 3 --seeds 42 7 100 --cpus 10 --memory 8g --max-workers 10

Utilisation de cet extracteur :
  python3 sweeps/pcal03_inventaire.py results/pcal03_profil_3x3_engine
  python3 sweeps/pcal03_inventaire.py --json results/v277v279_profil_42x1_20261020_engine
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_LINE_RE = re.compile(r"\[script:\d+\]\s+\[(\d+)\]\s+\[\w\]\s+(.*)")
OPEX_PREFIX_RE = re.compile(r"^OPEX\s+(\d{4})-(\d{1,2})-(\d{1,2})\s+(.*)$")

SPAN_RE = re.compile(
    r"\bSPAN\s+id=(\d+)\s+par=(\d+)\s+dep=(\d+)\s+n=([A-Za-z0-9_.]+)(?:\s+ds=[\d-]+)?(?:\s+t0=\d+)?(?:\s+tk=\d+)?\s+op=(\d+)"
)
SPAN_AGG_RE = re.compile(
    r"\bSPAN_AGG\s+par=(\d+)\s+n=([A-Za-z0-9_.]+)\s+cnt=(\d+)(?:\s+tk=\d+)?\s+op=(\d+)"
)
LOOP_OPS_RE = re.compile(
    r"\bLOOP_OPS\s+y=(\d+)\s+post=([A-Za-z0-9_.]+)\s+n=(\d+)\s+ops=(\d+)"
)
RAIL_ATTEMPT_RE = re.compile(
    r"\bRAIL_ATTEMPT\b.*?\bphases=([-\d]+)/([-\d]+)/([-\d]+)/([-\d]+)/([-\d]+)"
)
RAIL_ATTEMPT_OPS_RE = re.compile(r"\bRAIL_ATTEMPT\b.*?\bops=(\d+)")
RAIL_ATTEMPT_SOPS_RE = re.compile(r"\bRAIL_ATTEMPT\b.*?\bsearch_ops=(\d+)")
C76_REGEN_RE = re.compile(
    r"\bC76_REGEN\b.*?\bphase=regen\b.*?\bkind=([A-Za-z0-9_]+)\b.*?\breason=([A-Za-z0-9_]+)\b.*?\bops=(\d+)"
)
C76_REGEN_YEAR_RE = re.compile(
    r"\bC76_REGEN\b.*?\bphase=regen_year\b.*?\byear=(\d+)\b.*?\bops_total=(\d+)"
)
V257_OPS_RE = re.compile(r"\bV257_OPS\b.*?\bops=(\d+)")
CATALOG_COST_RE = re.compile(r"\bCATALOG_COST\b.*?\btotal_ops=(\d+)")


class PostInventory:
    def __init__(self, name: str, description: str, inclusive_mode: bool = False):
        self.name = name
        self.description = description
        self.inclusive_mode = inclusive_mode
        self.items: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "inclusive_ops": 0,
                "exclusive_ops": 0,
                "total_ops": 0,
                "source": set(),
            }
        )

    def add(
        self,
        item_name: str,
        calls: int,
        inclusive_ops: int,
        source_tag: str,
        exclusive_ops: Optional[int] = None,
    ):
        entry = self.items[item_name]
        entry["calls"] += calls
        entry["inclusive_ops"] += inclusive_ops
        if exclusive_ops is None:
            # Pour un élément sans décomposition d'enfants : coût propre = inclusif
            # Pour SPAN_AGG, c'est une sous-mesure interne d'un span déjà compté : coût propre = 0
            if source_tag == "SPAN_AGG":
                exclusive_ops = 0
            else:
                exclusive_ops = inclusive_ops
        entry["exclusive_ops"] += exclusive_ops
        if self.inclusive_mode:
            entry["total_ops"] += inclusive_ops
        else:
            entry["total_ops"] += exclusive_ops
        entry["source"].add(source_tag)

    @property
    def total_ops(self) -> int:
        if self.inclusive_mode:
            return sum(v["inclusive_ops"] for v in self.items.values())
        return sum(v["exclusive_ops"] for v in self.items.values())

    @property
    def total_exclusive_ops(self) -> int:
        return sum(v["exclusive_ops"] for v in self.items.values())

    @property
    def total_inclusive_ops(self) -> int:
        return sum(v["inclusive_ops"] for v in self.items.values())


class EngineLogParser:
    def __init__(self):
        self.files_parsed: set = set()
        self.years_by_file: Dict[str, set] = defaultdict(set)
        self.min_year = 9999
        self.max_year = 0

        # Raw metrics
        self.spans: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"calls": 0, "ops": 0, "inclusive_ops": 0, "exclusive_ops": 0}
        )
        self.raw_spans_by_file: Dict[str, Dict[int, Dict[str, Any]]] = defaultdict(dict)
        self.children_by_file: Dict[str, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        self.span_aggs: Dict[str, Dict[str, int]] = defaultdict(lambda: {"calls": 0, "ops": 0})
        self.loop_ops: Dict[str, Dict[str, int]] = defaultdict(lambda: {"calls": 0, "ops": 0})
        self.c76_regens: List[Dict[str, Any]] = []
        self.rail_phases: Dict[str, Dict[str, int]] = {
            "plans": {"calls": 0, "ops": 0},
            "search": {"calls": 0, "ops": 0},
            "stations": {"calls": 0, "ops": 0},
            "track": {"calls": 0, "ops": 0},
            "trains": {"calls": 0, "ops": 0},
        }
        self.rail_attempts_total_ops = 0
        self.rail_attempts_search_ops = 0
        self.rail_attempts_count = 0
        self.v257_calls = 0
        self.v257_ops = 0
        self.catalog_cost_calls = 0
        self.catalog_cost_ops = 0

    def parse_file(self, filepath: Path) -> None:
        filename = filepath.name
        self.files_parsed.add(filename)
        is_gz = filepath.suffix == ".gz"
        open_fn = gzip.open if is_gz else open
        try:
            with open_fn(filepath, "rt", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    self._parse_line(filename, line)
            self._resolve_spans(filename)
        except Exception as e:
            print(f"Erreur de lecture de {filepath}: {e}", file=sys.stderr)

    def parse_line(self, filename: str, line: str) -> None:
        self._parse_line(filename, line)

    def _resolve_spans(self, filename: Optional[str] = None) -> None:
        files = [filename] if filename is not None else list(self.raw_spans_by_file.keys())
        for fn in files:
            file_spans = self.raw_spans_by_file.get(fn, {})
            children_map = self.children_by_file.get(fn, {})
            for sid, span in file_spans.items():
                child_ids = children_map.get(sid, [])
                child_ops = sum(file_spans[cid]["ops"] for cid in child_ids if cid in file_spans)
                exclusive_ops = max(0, span["ops"] - child_ops)
                name = span["name"]
                ops = span["ops"]
                self.spans[name]["calls"] += 1
                self.spans[name]["ops"] += ops
                self.spans[name]["inclusive_ops"] += ops
                self.spans[name]["exclusive_ops"] += exclusive_ops
            if fn in self.raw_spans_by_file:
                del self.raw_spans_by_file[fn]
            if fn in self.children_by_file:
                del self.children_by_file[fn]

    def finalize(self) -> None:
        self._resolve_spans()

    def _parse_line(self, filename: str, line: str) -> None:
        script_match = SCRIPT_LINE_RE.search(line)
        if not script_match:
            # Check if line has company [0] or direct OPEX prefix
            if "[0]" not in line and not line.startswith("OPEX"):
                return
            body = line
        else:
            company_id = int(script_match.group(1))
            if company_id != 0:
                return  # Skip competitors (AAAHogEx is company 1)
            body = script_match.group(2)

        opex_match = OPEX_PREFIX_RE.match(body)
        if opex_match:
            year = int(opex_match.group(1))
            self.years_by_file[filename].add(year)
            if year < self.min_year:
                self.min_year = year
            if year > self.max_year:
                self.max_year = year

        # 1. SPAN
        m = SPAN_RE.search(body)
        if m:
            sid = int(m.group(1))
            par = int(m.group(2))
            dep = int(m.group(3))
            name = m.group(4)
            ops = int(m.group(5))
            if sid in self.raw_spans_by_file[filename]:
                self._resolve_spans(filename)
            self.raw_spans_by_file[filename][sid] = {
                "id": sid,
                "par": par,
                "dep": dep,
                "name": name,
                "ops": ops,
            }
            if par != 0:
                self.children_by_file[filename][par].append(sid)
            return

        # 2. SPAN_AGG
        m = SPAN_AGG_RE.search(body)
        if m:
            name = m.group(2)
            cnt = int(m.group(3))
            ops = int(m.group(4))
            self.span_aggs[name]["calls"] += cnt
            self.span_aggs[name]["ops"] += ops
            return

        # 3. LOOP_OPS
        m = LOOP_OPS_RE.search(body)
        if m:
            year = int(m.group(1))
            post = m.group(2)
            cnt = int(m.group(3))
            ops = int(m.group(4))
            self.years_by_file[filename].add(year)
            if year < self.min_year:
                self.min_year = year
            if year > self.max_year:
                self.max_year = year
            self.loop_ops[post]["calls"] += cnt
            self.loop_ops[post]["ops"] += ops
            return

        # 4. RAIL_ATTEMPT phases
        m = RAIL_ATTEMPT_RE.search(body)
        if m:
            self.rail_attempts_count += 1
            phase_names = ["plans", "search", "stations", "track", "trains"]
            for idx, pname in enumerate(phase_names):
                val = int(m.group(idx + 1))
                if val >= 0:
                    self.rail_phases[pname]["calls"] += 1
                    self.rail_phases[pname]["ops"] += val
            m_ops = RAIL_ATTEMPT_OPS_RE.search(body)
            if m_ops:
                self.rail_attempts_total_ops += int(m_ops.group(1))
            m_sops = RAIL_ATTEMPT_SOPS_RE.search(body)
            if m_sops:
                self.rail_attempts_search_ops += int(m_sops.group(1))
            return

        # 5. C76_REGEN
        m = C76_REGEN_RE.search(body)
        if m:
            kind = m.group(1)
            reason = m.group(2)
            ops = int(m.group(3))
            self.c76_regens.append({"kind": kind, "reason": reason, "ops": ops})
            return

        # 6. V257_OPS
        m = V257_OPS_RE.search(body)
        if m:
            self.v257_calls += 1
            self.v257_ops += int(m.group(1))
            return

        # 7. CATALOG_COST
        m = CATALOG_COST_RE.search(body)
        if m:
            self.catalog_cost_calls += 1
            self.catalog_cost_ops += int(m.group(1))
            return

    def get_total_years(self) -> float:
        # Sum of distinct calendar years per file, or at least 1.0
        total_file_years = sum(len(years) for years in self.years_by_file.values())
        return max(1.0, float(total_file_years))


def compile_pcal03_inventory(parser: EngineLogParser, inclusive: bool = False) -> Dict[str, Any]:
    parser.finalize()
    years_simulated = parser.get_total_years()
    num_files = len(parser.files_parsed) if parser.files_parsed else len(parser.years_by_file)

    p1 = PostInventory("Poste 1", "AIR plans, hubs et demande", inclusive_mode=inclusive)
    p2 = PostInventory("Poste 2", "Régénérations, filtrage et sélection", inclusive_mode=inclusive)
    p3 = PostInventory("Poste 3", "Constructibilité rail avant A*", inclusive_mode=inclusive)
    p4 = PostInventory("Poste 4", "Route et flotte", inclusive_mode=inclusive)
    p5 = PostInventory("Poste 5", "Cartographie / eau C67", inclusive_mode=inclusive)

    # --- Poste 1: AIR ---
    air_spans = [
        "air.plans", "air.new_pairs", "air.hub_site", "air.hub_discover",
        "air.hub_hub", "air.sites", "air.prepare", "air.finalize",
        "build.air.choose_plan", "loop.c121_catalog_resume", "catalog.slice"
    ]
    for s in air_spans:
        if s in parser.spans:
            p1.add(
                s,
                parser.spans[s]["calls"],
                parser.spans[s]["ops"],
                "SPAN",
                exclusive_ops=parser.spans[s].get("exclusive_ops", parser.spans[s]["ops"]),
            )
    for s in ["air.c121.demand", "air.c121.winner", "air.c121.cache", "air.pair", "air.hub_site_pair"]:
        if s in parser.span_aggs:
            p1.add(f"agg:{s}", parser.span_aggs[s]["calls"], parser.span_aggs[s]["ops"], "SPAN_AGG")

    # --- Poste 2: Régénérations & Sélection ---
    regen_spans = [
        "catalog.rebuild", "pub.filter", "pub.select.filter", "select.reselect",
        "select.full", "select.incremental", "pub.select.score", "pub.select.stats",
        "pub.insert", "pub.partition", "projects.pass", "projects.post_regen.incremental",
        "projects.post_regen.full", "projects.post_regen.staged_full", "regen.step",
        "regen.air_slice"
    ]
    for s in regen_spans:
        if s in parser.spans:
            p2.add(
                s,
                parser.spans[s]["calls"],
                parser.spans[s]["ops"],
                "SPAN",
                exclusive_ops=parser.spans[s].get("exclusive_ops", parser.spans[s]["ops"]),
            )
    if parser.c76_regens:
        for r in parser.c76_regens:
            p2.add(f"c76_regen_{r['kind']}_{r['reason']}", 1, r["ops"], "C76_REGEN")

    # --- Poste 3: Constructibilité rail avant A* ---
    # Phase 'plans' = OpexRailPlatformPlans (sites de gares/quais)
    if parser.rail_phases["plans"]["calls"] > 0:
        p3.add("rail_platform_plans (phases.plans)",
               parser.rail_phases["plans"]["calls"],
               parser.rail_phases["plans"]["ops"], "RAIL_ATTEMPT:phases")
    if "railprep.after_pass" in parser.spans:
        p3.add(
            "railprep.after_pass",
            parser.spans["railprep.after_pass"]["calls"],
            parser.spans["railprep.after_pass"]["ops"],
            "SPAN",
            exclusive_ops=parser.spans["railprep.after_pass"].get(
                "exclusive_ops", parser.spans["railprep.after_pass"]["ops"]
            ),
        )

    # Rail comparison context
    if parser.rail_phases["search"]["calls"] > 0:
        p3.add("context_rail_search (A*)",
               parser.rail_phases["search"]["calls"],
               parser.rail_phases["search"]["ops"], "RAIL_ATTEMPT:phases")
    if parser.rail_phases["track"]["calls"] > 0:
        p3.add("context_rail_track",
               parser.rail_phases["track"]["calls"],
               parser.rail_phases["track"]["ops"], "RAIL_ATTEMPT:phases")
    if parser.rail_phases["trains"]["calls"] > 0:
        p3.add("context_rail_trains",
               parser.rail_phases["trains"]["calls"],
               parser.rail_phases["trains"]["ops"], "RAIL_ATTEMPT:phases")

    # --- Poste 4: Route et flotte ---
    road_fleet_spans = [
        "task.town_growth", "task.road", "build.road",
        "task.air_fleet", "fleet.resize", "fleet.sort", "fleet.inject",
        "task.v257_rail_refresh", "task.v252_air_engine_refresh"
    ]
    for s in road_fleet_spans:
        if s in parser.spans:
            p4.add(
                s,
                parser.spans[s]["calls"],
                parser.spans[s]["ops"],
                "SPAN",
                exclusive_ops=parser.spans[s].get("exclusive_ops", parser.spans[s]["ops"]),
            )
    for s in ["fleet.sort", "fleet.cadence_cap", "fleet.refusal", "fleet.first_live"]:
        if s in parser.span_aggs:
            p4.add(f"agg:{s}", parser.span_aggs[s]["calls"], parser.span_aggs[s]["ops"], "SPAN_AGG")
    if parser.v257_calls > 0:
        p4.add("v257_rail_refresh_ops", parser.v257_calls, parser.v257_ops, "V257_OPS")

    # --- Poste 5: Cartographie / eau C67 ---
    c67_water_spans = [
        "loop.c67", "task.terrain", "task.water", "build.water", "catalog.refresh.water"
    ]
    for s in c67_water_spans:
        if s in parser.spans:
            p5.add(
                s,
                parser.spans[s]["calls"],
                parser.spans[s]["ops"],
                "SPAN",
                exclusive_ops=parser.spans[s].get("exclusive_ops", parser.spans[s]["ops"]),
            )

    posts = [p1, p2, p3, p4, p5]

    data = {
        "summary": {
            "num_files": num_files,
            "years_simulated": years_simulated,
            "min_year": parser.min_year if parser.min_year <= parser.max_year else None,
            "max_year": parser.max_year if parser.min_year <= parser.max_year else None,
        },
        "mode": "inclusif" if inclusive else "exclusif",
        "posts": {}
    }

    for p in posts:
        post_data = {
            "name": p.name,
            "description": p.description,
            "mode": "inclusif" if inclusive else "exclusif",
            "total_ops": p.total_ops,
            "ops_per_year": round(p.total_ops / years_simulated, 1),
            "total_exclusive_ops": p.total_exclusive_ops,
            "total_inclusive_ops": p.total_inclusive_ops,
            "items": {}
        }
        for iname, iv in sorted(
            p.items.items(),
            key=lambda x: (x[1]["total_ops"], x[1]["inclusive_ops"]),
            reverse=True,
        ):
            post_data["items"][iname] = {
                "calls": iv["calls"],
                "calls_per_year": round(iv["calls"] / years_simulated, 1),
                "total_ops": iv["total_ops"],
                "ops_per_year": round(iv["total_ops"] / years_simulated, 1),
                "inclusive_ops": iv["inclusive_ops"],
                "inclusive_ops_per_year": round(iv["inclusive_ops"] / years_simulated, 1),
                "exclusive_ops": iv["exclusive_ops"],
                "exclusive_ops_per_year": round(iv["exclusive_ops"] / years_simulated, 1),
                "mean_ops_per_call": round(iv["inclusive_ops"] / max(1, iv["calls"]), 1),
                "mean_exclusive_ops_per_call": round(iv["exclusive_ops"] / max(1, iv["calls"]), 1),
                "sources": list(iv["source"]),
            }
        data["posts"][p.name] = post_data

    return data


def format_table(data: Dict[str, Any]) -> str:
    lines = []
    s = data["summary"]
    mode = data.get("mode", "exclusif")
    mode_str = f" [mode: {mode}]"
    lines.append(f"Campagne analysée : {s['num_files']} fichiers, {s['years_simulated']:.1f} années cumulées "
                 f"(millésimes {s['min_year']} à {s['max_year']}){mode_str}")
    lines.append("-" * 92)
    lines.append(f"{'Poste':<9} | {'Description':<38} | {'Opcodes/an':<14} | {'Mesure':<22}")
    lines.append("-" * 92)

    for pname, pdata in data["posts"].items():
        ops_yr = pdata["ops_per_year"]
        desc = pdata["description"]
        if ops_yr > 0:
            ops_str = f"{int(ops_yr):,d}".replace(",", " ")
            mesure = f"mesuré ({len(pdata['items'])} balises)"
        else:
            ops_str = "0"
            mesure = "non mesuré / inactif"
        lines.append(f"{pname:<9} | {desc:<38} | {ops_str:<14} | {mesure:<22}")

    lines.append("-" * 92)
    lines.append("")
    lines.append("Détail par poste et sous-éléments :")
    mode_label = "inclusif" if mode == "inclusif" else "propre"
    for pname, pdata in data["posts"].items():
        lines.append(f"\n### {pname} : {pdata['description']} (Total {mode_label} : {int(pdata['ops_per_year']):,d} ops/an)".replace(",", " "))
        if not pdata["items"]:
            lines.append("  (Aucune ligne enregistrée dans les journaux analysés)")
            continue
        lines.append(f"  {'Élément / Balise':<34} | {'Appels/an':<9} | {'Propre/an':<14} | {'Inclusif/an':<14} | {'Ops/appel':<10} | {'Source'}")
        lines.append("  " + "-" * 98)
        for iname, idata in pdata["items"].items():
            excl_yr_str = f"{int(idata['exclusive_ops_per_year']):,d}".replace(",", " ")
            incl_yr_str = f"{int(idata['inclusive_ops_per_year']):,d}".replace(",", " ")
            mean_str = f"{int(idata['mean_ops_per_call']):,d}".replace(",", " ")
            src_str = ",".join(idata["sources"])
            lines.append(f"  {iname:<34} | {idata['calls_per_year']:<9.1f} | {excl_yr_str:<14} | {incl_yr_str:<14} | {mean_str:<10} | {src_str}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Inventaire chiffré des postes d'opcodes précalculables (PCAL-03)."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Dossier d'engine (ex: results/<campagne>_engine) ou fichiers de journal (.log, .log.gz)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sortie au format JSON pour exploitation automatisée",
    )
    parser.add_argument(
        "--inclusive",
        action="store_true",
        help="Sommer les coûts inclusifs des spans au lieu des coûts propres (ancien comportement)",
    )
    args = parser.parse_args()

    # Collect files
    log_files: List[Path] = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_dir():
            for f in sorted(p.iterdir()):
                if f.name.endswith(".log") or f.name.endswith(".log.gz"):
                    log_files.append(f)
        elif p.is_file():
            log_files.append(p)
        else:
            print(f"Avertissement: chemin inexistant ignoré : {inp}", file=sys.stderr)

    if not log_files:
        print("Erreur: aucun fichier .log ou .log.gz trouvé.", file=sys.stderr)
        sys.exit(1)

    engine_parser = EngineLogParser()
    for f in log_files:
        engine_parser.parse_file(f)

    data = compile_pcal03_inventory(engine_parser, inclusive=args.inclusive)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_table(data))


if __name__ == "__main__":
    main()
