"""Lecteur AIR léger hors ligne et protocole, sans import/lancement moteur.

Réutilise le lecteur de latence (enveloppes, sessions, distributions, sources).
Les bilans catalogue et AIR historiques restent des publications non jointes :
ils ne portent pas d'identité suffisante pour dénombrer des générations uniques.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

if __package__:
    # Les lecteurs existants utilisent les imports directs du dossier sweeps.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from parallel_latency_audit import (
    OWNER, difference, distribution, nonnegative, parse_fields, parse_log,
    read_sources, reference,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "results" / "air_selection_light"
PHASES = ("prepare", "sites", "new_pairs", "hub_discover", "hub_site", "hub_hub", "finalize")
UNITS = {"days": "AIDate_calendar_days", "ticks": "AIController_ticks",
         "ops_proxy": "OpexOpsMeasure_convention_not_CPU_time",
         "legacy_days_tick74": "ticks_div_74_not_calendar_days"}
ARMS = {"reference": "OpexAI", "light": "OpexAI[catalog_cost_probe=1]"}
PROTOCOL = {
    "status": "pre_registered_not_executed", "arms": ARMS,
    "harness": "sweeps.diag_cadence_duel.main",
    "harness_kwargs": {"arm_specs": ARMS, "force_debug": True,
                       "purpose": "air_selection_light_exposure_perturbation_not_adoption"},
    "forbidden_cli": ["--probe"], "global_cpu_worker_ceiling": 12,
    "smoke": {"seeds": [42], "years": 1, "workers": 2},
    "perturbation_after_smoke": {"seeds": [42, 100, 999, 1234, 5678], "years": 6,
                                 "workers": 3, "replicates": 2},
    "primary": "paired_Opex_profit_year_variant_minus_reference",
    "value_guard_max_loss_pct": 5,
    "screen_only": "mean profit >= -5% reference, value >= -5%, >=3/5 nonnegative seed means",
    "neutrality": "not_established_by_smoke_or_small_diagnostic",
}


def strict_sum(values):
    values = list(values)
    return sum(values) if values and all(v is not None for v in values) else None


def measures(fields, prefix):
    return {unit: nonnegative(fields.get(prefix + suffix))
            for unit, suffix in (("days", "days"), ("ticks", "ticks"), ("ops_proxy", "ops"))}


def audit_stream(events):
    """Une seule compagnie/session/époque de ticks. Aucun raccord temporel implicite."""
    invocations = defaultdict(list)
    issues, catalog, legacy = [], [], []
    selections = defaultdict(list)
    for event in events:
        fields, tag = event["fields"], event["tag"]
        if tag == "AIR_LIGHT":
            inv = nonnegative(fields.get("inv"))
            if fields.get("v") != "1" or inv is None or inv == 0:
                issues.append({"reason": "invalid_version_or_invocation", "event": reference(event)})
            else:
                invocations[inv].append(event)
        elif tag == "SELECTION_LIGHT":
            selections[fields.get("inv")].append(event)
        elif tag == "CATALOG_COST":
            # Mode/reselect enveloppes ne sont PAS la mesure selectionOpcodes.
            path = fields.get("path")
            catalog.append({"event": reference(event), "path": path, "fields": fields,
                            "identity_verified": False, "days": None, "ticks": None,
                            "selection_ops_proxy": nonnegative(fields.get("selection_ops"))
                            if path == "full" else None,
                            "reselect_envelope_ops_proxy": nonnegative(fields.get("reselect_ops")),
                            "air_ops_proxy": nonnegative(fields.get("air_ops"))})
        elif tag == "AIR_PLAN_PERF":
            legacy.append({"event": reference(event), "fields": fields, "days": None,
                           "ticks": nonnegative(fields.get("ticks")),
                           "ops_proxy": nonnegative(fields.get("total_ops")),
                           "legacy_days_tick74": nonnegative(fields.get("days")),
                           "identity_verified": False})

    slices = []
    tainted_generations = set()
    duplicate_lines = 0
    for inv, records in invocations.items():
        unique = {}
        for event in records:
            fingerprint = (event["date"], tuple(sorted(event["fields"].items())))
            if fingerprint in unique:
                duplicate_lines += 1
            else:
                unique[fingerprint] = event
        records = list(unique.values())
        enters = [e for e in records if e["fields"].get("edge") == "enter"]
        exits = [e for e in records if e["fields"].get("edge") == "exit"]
        start = enters[0] if len(enters) == 1 else None
        end = exits[0] if len(exits) == 1 else None
        anchor = start or end or records[0]
        f = anchor["fields"]
        valid = len(records) == 2 and start is not None and end is not None
        identity = ("gen", "slice", "origin", "sliced", "target", "band")
        if valid:
            valid = (start["line"] < end["line"] and
                     all(start["fields"].get(k) is not None and
                         start["fields"].get(k) == end["fields"].get(k) for k in identity))
        if valid:
            for clock in ("day", "tick"):
                a, b = (nonnegative(e["fields"].get(clock)) for e in (start, end))
                if a is not None and b is not None and b < a:
                    valid = False
        if not valid:
            tainted_generations.update(nonnegative(e["fields"].get("gen")) for e in records)
            issues.append({"reason": "unpaired_or_conflicting_invocation", "inv": inv,
                           "lines": [e["line"] for e in records]})
        ef = end["fields"] if valid else {}
        sf = start["fields"] if valid else {}
        days = difference(nonnegative(sf.get("day")), nonnegative(ef.get("day")))
        ticks = difference(nonnegative(sf.get("tick")), nonnegative(ef.get("tick")))
        rec = {"inv": inv, "gen": nonnegative(f.get("gen")),
               "slice": nonnegative(f.get("slice")), "origin": f.get("origin"),
               "sliced": f.get("sliced"), "target": f.get("target"), "band": f.get("band"),
               "paired": valid, "complete": ef.get("complete"),
               "reason": ef.get("reason"), "days": days, "ticks": ticks,
               "ops_proxy": nonnegative(ef.get("ops")),
               "start_day": nonnegative(sf.get("day")), "end_day": nonnegative(ef.get("day")),
               "start_tick": nonnegative(sf.get("tick")), "end_tick": nonnegative(ef.get("tick")),
               "start": reference(start) if start else None,
               "end": reference(end) if end else None,
               "phases": {p: {**measures(ef, p + "_"), "calls": nonnegative(ef.get(p + "_calls"))}
                          for p in PHASES}}
        slices.append(rec)

    grouped = defaultdict(list)
    for rec in slices:
        # Missing generation IDs must not join unrelated invocations.
        grouped[rec["gen"] if rec["gen"] is not None else f"unknown:{rec['inv']}"].append(rec)
    generations = []
    for gen, items in grouped.items():
        items.sort(key=lambda r: r["inv"])
        expected = list(range(1, len(items) + 1))
        complete = (isinstance(gen, int) and gen > 0 and gen not in tainted_generations and
                    [r["slice"] for r in items] == expected and
                    all(r["paired"] and r["origin"] == "1" for r in items) and
                    all(r["complete"] == "0" for r in items[:-1]) and
                    items[-1]["complete"] == "1" and
                    len({(r["target"], r["band"], r["sliced"]) for r in items}) == 1)
        if len(items) > 1 and items[0]["sliced"] != "1":
            complete = False
        for previous, following in zip(items, items[1:]):
            for clock in ("day", "tick"):
                a, b = previous["end_" + clock], following["start_" + clock]
                if a is not None and b is not None and b < a:
                    complete = False
        generations.append({"gen": gen, "complete": complete,
                            "invocations": [r["inv"] for r in items],
                            "days": difference(items[0]["start_day"], items[-1]["end_day"]) if complete else None,
                            "ticks": difference(items[0]["start_tick"], items[-1]["end_tick"]) if complete else None,
                            "slice_days_sum": strict_sum(r["days"] for r in items) if complete else None,
                            "slice_ticks_sum": strict_sum(r["ticks"] for r in items) if complete else None,
                            "slice_ops_sum": strict_sum(r["ops_proxy"] for r in items) if complete else None,
                            "observed_slices": len(items)})
    summaries = {"slice": {u: distribution(r[u] for r in slices) for u in ("days", "ticks", "ops_proxy")},
                 "generation": {u: distribution(r[u] for r in generations)
                                for u in ("days", "ticks", "slice_days_sum", "slice_ticks_sum", "slice_ops_sum")},
                 "phases": {p: {u: distribution(r["phases"][p][u] for r in slices)
                                  for u in ("days", "ticks", "ops_proxy")} for p in PHASES}}
    selection_rows = []
    for inv, publications in selections.items():
        unique = {tuple(sorted(e["fields"].items())): e for e in publications}
        e = publications[0]
        f = e["fields"]
        valid = (len(unique) == 1 and nonnegative(inv) not in (None, 0)
                 and f.get("v") == "1" and f.get("path") in ("full", "incremental", "reselect"))
        days = difference(nonnegative(f.get("start_day")), nonnegative(f.get("end_day")))
        ticks = difference(nonnegative(f.get("start_tick")), nonnegative(f.get("end_tick")))
        valid = valid and days is not None and ticks is not None and nonnegative(f.get("ops")) is not None
        if not valid:
            issues.append({"reason": "invalid_selection_publication", "inv": inv})
        selection_rows.append({"inv": inv, "path": f.get("path"), "valid": valid,
                               "days": days if valid else None, "ticks": ticks if valid else None,
                               "ops_proxy": nonnegative(f.get("ops")) if valid else None,
                               "considered": nonnegative(f.get("considered")),
                               "selected": nonnegative(f.get("selected")), "event": reference(e)})
    return {"selections": selection_rows,
            "coverage": {"markers": dict(Counter(e["tag"] for e in events)),
                          "invocations": len(slices), "paired": sum(r["paired"] for r in slices),
                          "duplicate_lines": duplicate_lines, "generations": len(generations),
                          "complete_generations": sum(r["complete"] for r in generations),
                          "catalog_publications": len(catalog), "legacy_publications": len(legacy)},
            "issues": issues, "slices": slices, "generations": generations,
            "summaries": summaries, "catalog_publications": catalog, "legacy_publications": legacy}


def audit_text(text, source):
    events, issues = parse_log(text, source)
    # Sessions/reload du lecteur existant. Une répétition d'identité n'est PAS
    # une preuve de reload : dédupliquer ou rejeter, jamais créer deux générations.
    # Les phases Save/Load sont des sources distinctes même sans LOAD_RECONCILE.
    groups = defaultdict(list)
    for event in events:
        key = (event["company"], event["session"])
        groups[key].append(event)
    # Le AILog.Info historique non OPEX existe sans decision_log. Pas de date
    # fabriquée, pas d'association avec la copie structurée ou un catalogue.
    raw_legacy = []
    for line, raw in enumerate(text.splitlines(), 1):
        match = re.search(r"\bAIR_PLAN_PERF:\s*(.*)$", raw)
        if match:
            f = parse_fields(match.group(1))
            owner = OWNER.search(raw)
            raw_legacy.append({"line": line, "company": owner.group(1) if owner else None,
                               "fields": f, "days": None, "ticks": nonnegative(f.get("ticks")),
                               "ops_proxy": nonnegative(f.get("total_ops")),
                               "legacy_days_tick74": nonnegative(f.get("days")),
                               "identity_verified": False})
    return {"source": source, "parse_issues": issues, "raw_legacy_publications": raw_legacy,
            "streams": [{"company": company, "session": session,
                         **audit_stream(items)}
                        for (company, session), items in groups.items()
                        if any(e["tag"] in {"AIR_LIGHT", "SELECTION_LIGHT", "CATALOG_COST", "AIR_PLAN_PERF"} for e in items)]}


def run(paths, output):
    output = output.resolve()
    if output == OUTPUT_ROOT.resolve() or not output.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("Sortie obligatoire dans un nouveau sous-dossier results/air_selection_light/")
    if output.exists():
        raise FileExistsError(output)
    paths = [p.resolve() for p in paths]
    if not paths or len(set(paths)) != len(paths):
        raise ValueError("Sources absentes ou dupliquées")
    report = {"schema": 1, "scope": "offline_coverage_not_engine_validation",
              "units": UNITS, "protocol": PROTOCOL, "sources": [], "analyses": []}
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        streams, metadata = read_sources(path)
        report["sources"].append({"path": str(path), "sha256": digest, "metadata": metadata,
                                  "raw_streams": len(streams), "raw_missing": not streams})
        report["analyses"].extend(audit_text(text, source) for source, text in streams)
    for source in report["sources"]:
        if hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
            raise RuntimeError("Source modifiée pendant lecture : " + source["path"])
    output.mkdir(parents=True)
    with (output / "audit.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, help="Logs bruts ou JSON Save/Load ; jamais un moteur")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--plan", action="store_true", help="Afficher le protocole sans exécuter de partie")
    args = parser.parse_args(argv)
    if args.plan:
        if args.inputs or args.out:
            parser.error("--plan ne prend ni source ni sortie")
        print(json.dumps(PROTOCOL, indent=2, ensure_ascii=False))
        return
    if not args.inputs or args.out is None:
        parser.error("Fournir les sources et --out, ou --plan")
    result = run(args.inputs, args.out)
    print(f"{len(result['sources'])} sources, {len(result['analyses'])} flux ; {args.out / 'audit.json'}")


if __name__ == "__main__":
    main()