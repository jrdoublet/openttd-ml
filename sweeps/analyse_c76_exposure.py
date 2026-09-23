#!/usr/bin/env python3
"""Exposition C76 : régénérations, rotation du cargo fret, coût par étape et chronologie.

Lit le jsonl brut de `diag_c69_bottleneck_probe.py --extra-tags C76_REGEN --grep " C56_TASK "`
(bras avec `probe_catalogue=1,probe_events=1`) et produit, par bras :

1. régénérations par an (complètes / incrémentales / évitées, par motif) et cargos fret vus ;
2. coût de chaque étape tracée (TASK, STAGE, INTENT, WORKER) : nombre, ticks, opcodes ;
3. une chronologie CSV (une ligne par étape terminée et par régénération).

Convention des opcodes : `opsclk` suit OpexOpsMeasureEnd — un tick franchi compte pour
OPS_PER_TICK (10 000), y compris les ticks où le script attend une commande de construction.
C'est du « temps script » en opcodes, pas des instructions exécutées ; les ticks sont donnés
à côté. Les étapes imbriquées (STAGE dans TASK) sont comptées dans leur parent : `self_ops`
retire le coût des enfants. `--selftest` est pur Python.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

TRACE_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) C56_TASK (TASK|STAGE|INTENT|WORKER)_(ENTER|EXIT) "
                      r"name=(\S+) cycle=(\S+) tick=(\d+) opsclk=(-?\d+)(.*)")
TICKS_PER_DAY = 74


def parse_extra(text):
    return dict(tok.split("=", 1) for tok in text.split() if "=" in tok)


def date_key(y, m, d):
    return int(y) * 400 + int(m) * 32 + int(d)


def load(path):
    traces = defaultdict(list)
    regens = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            seed = row.get("seed")
            if "grep" in row:
                m = TRACE_RE.search(row["grep"])
                if not m:
                    continue
                y, mo, d, fam, edge, name, cycle, tick, clk, rest = m.groups()
                traces[seed].append({
                    "date": f"{y}-{mo}-{d}", "dkey": date_key(y, mo, d), "year": int(y),
                    "fam": fam, "edge": edge, "name": name, "tick": int(tick),
                    "clk": int(clk), "extra": parse_extra(rest)})
            elif row.get("tag") == "C76_REGEN":
                date = row.get("_log_date")
                if date:
                    y, mo, d = date.split("-")
                    row["dkey"] = date_key(y, mo, d)
                else:
                    row["dkey"] = date_key(row["_log_year"], 12, 31)
                    date = f"{row['_log_year']}-?-?"
                row["date"] = date
                regens[seed].append(row)
    return traces, regens


def pair_steps(events):
    """Apparie ENTER/EXIT par pile ; renvoie les étapes terminées avec coût et coût propre."""
    stack = []
    steps = []
    for ev in events:
        if ev["edge"] == "ENTER":
            ev = dict(ev, child_ops=0)
            if ev["fam"] == "WORKER":
                # Un travailleur s'intercale avec la file : on ne l'empile pas.
                steps.append({"open": ev})
                continue
            stack.append(ev)
            continue
        if ev["fam"] == "WORKER":
            enter = None
            for s in reversed(steps):
                if "open" in s and s["open"]["name"] == ev["name"]:
                    enter = s.pop("open")
                    steps.remove(s)
                    break
            ops = int(ev["extra"].get("step_ops", 0))
            steps.append({
                "date": enter["date"] if enter else ev["date"], "dkey": enter["dkey"] if enter else ev["dkey"],
                "year": ev["year"], "tick": enter["tick"] if enter else ev["tick"], "fam": "WORKER",
                "name": ev["name"], "ops": ops, "self_ops": ops,
                "ticks": ev["tick"] - enter["tick"] if enter else None,
                "detail": "outcome=%s steps=%s" % (ev["extra"].get("outcome"), ev["extra"].get("steps"))})
            continue
        idx = None
        for i in range(len(stack) - 1, -1, -1):
            if stack[i]["fam"] == ev["fam"] and stack[i]["name"] == ev["name"]:
                idx = i
                break
        if idx is None:
            continue
        enter = stack[idx]
        del stack[idx:]
        ops = ev["clk"] - enter["clk"]
        if stack:
            stack[-1]["child_ops"] += ops
        detail = " ".join(f"{k}={v}" for k, v in ev["extra"].items())
        steps.append({"date": enter["date"], "dkey": enter["dkey"], "year": enter["year"],
                      "tick": enter["tick"], "fam": ev["fam"], "name": ev["name"], "ops": ops,
                      "self_ops": ops - enter["child_ops"], "ticks": ev["tick"] - enter["tick"],
                      "detail": detail})
    return [s for s in steps if "open" not in s]


def regen_summary(regens):
    per_year = defaultdict(lambda: {"full": 0, "incremental": 0, "avoided": 0, "full_ops": 0,
                                    "reasons": Counter(), "cargos": [], "rotations": 0})
    last_cargo = None
    for r in sorted(regens, key=lambda r: r["dkey"]):
        rec = per_year[r["_log_year"]]
        if r.get("phase") == "regen_avoided":
            rec["avoided"] += 1
            continue
        if r.get("phase") != "regen":
            continue
        kind = r.get("kind")
        rec[kind] = rec.get(kind, 0) + 1
        rec["reasons"][f"{kind}:{r.get('reason')}"] += 1
        if kind == "full":
            rec["full_ops"] += int(r.get("ops", 0))
        cargo = r.get("freight_cargo")
        if cargo and cargo != "none":
            if cargo not in rec["cargos"]:
                rec["cargos"].append(cargo)
            if last_cargo is not None and cargo != last_cargo:
                rec["rotations"] += 1
            last_cargo = cargo
    return dict(per_year)


def step_table(all_steps):
    by = defaultdict(list)
    for s in all_steps:
        by[(s["fam"], s["name"])].append(s)
    rows = []
    for (fam, name), items in by.items():
        ops = [s["ops"] for s in items]
        self_ops = [s["self_ops"] for s in items]
        ticks = [s["ticks"] for s in items if s["ticks"] is not None]
        rows.append({"fam": fam, "name": name, "n": len(items), "ops_total": sum(ops),
                     "self_ops_total": sum(self_ops), "ops_median": statistics.median(ops),
                     "ops_max": max(ops), "ticks_total": sum(ticks)})
    rows.sort(key=lambda r: -r["self_ops_total"])
    return rows


def write_chrono(path, steps_by_seed, regens):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["seed", "date", "tick", "family", "name", "ops", "self_ops", "ticks", "detail"])
        for seed in sorted(set(steps_by_seed) | set(regens)):
            rows = [(s["dkey"], s["tick"], s["date"], s["fam"], s["name"], s["ops"], s["self_ops"],
                     s["ticks"], s["detail"]) for s in steps_by_seed.get(seed, [])]
            for r in regens.get(seed, []):
                if r.get("phase") == "regen":
                    rows.append((r["dkey"], None, r["date"], "REGEN",
                                 f"{r.get('kind')}:{r.get('reason')}", r.get("ops"), None, None,
                                 f"freight_cargo={r.get('freight_cargo')}"))
                elif r.get("phase") == "regen_avoided":
                    rows.append((r["dkey"], None, r["date"], "REGEN", "avoided", None, None, None, ""))
            rows.sort(key=lambda t: (t[0], t[1] if t[1] is not None else 10**12))
            for t in rows:
                w.writerow([seed, t[2], t[1] if t[1] is not None else ""] + list(t[3:]))


def analyse(path, chrono_out=None, top=25):
    traces, regens = load(path)
    steps_by_seed = {seed: pair_steps(evs) for seed, evs in traces.items()}
    out = {"seeds": {}, "steps": step_table([s for v in steps_by_seed.values() for s in v])}
    for seed in sorted(set(traces) | set(regens)):
        ry = regen_summary(regens.get(seed, []))
        ticks = [e["tick"] for e in traces.get(seed, [])]
        out["seeds"][seed] = {
            "years": {y: {**v, "reasons": dict(v["reasons"])} for y, v in sorted(ry.items())},
            "span_ticks": (max(ticks) - min(ticks)) if ticks else None}
    if chrono_out:
        write_chrono(chrono_out, steps_by_seed, regens)
    return out


def print_report(label, out, top=25):
    print(f"=== {label}")
    for seed, s in out["seeds"].items():
        ys = s["years"]
        full = [v.get("full", 0) for v in ys.values()]
        cargos = [len(v["cargos"]) for v in ys.values()]
        print(f"seed {seed}: full/an med={statistics.median(full) if full else None} "
              f"total={sum(full)} incr={sum(v.get('incremental', 0) for v in ys.values())} "
              f"avoided={sum(v['avoided'] for v in ys.values())} "
              f"rotations={sum(v['rotations'] for v in ys.values())} "
              f"cargos/an={cargos}")
        reasons = Counter()
        for v in ys.values():
            reasons.update(v["reasons"])
        print("   motifs:", dict(reasons.most_common()))
    span = sum(s["span_ticks"] or 0 for s in out["seeds"].values())
    print(f"{'famille':7} {'étape':28} {'n':>6} {'self_ops':>14} {'%temps':>7} {'med ops':>11} {'max ops':>12}")
    for r in out["steps"][:top]:
        share = 100.0 * r["self_ops_total"] / (span * 10000) if span else 0
        print(f"{r['fam']:7} {r['name']:28} {r['n']:6d} {r['self_ops_total']:14d} {share:6.2f}% "
              f"{r['ops_median']:11.0f} {r['ops_max']:12d}")


def selftest():
    import tempfile
    lines = [
        {"seed": 1, "grep": "x OPEX 1970-1-1 C56_TASK TASK_ENTER name=catalog cycle=0 tick=10 opsclk=100000"},
        {"seed": 1, "grep": "x OPEX 1970-1-1 C56_TASK STAGE_ENTER name=c56_stage_rail cycle=- tick=11 opsclk=110000"},
        {"seed": 1, "grep": "x OPEX 1970-1-2 C56_TASK STAGE_EXIT name=c56_stage_rail cycle=- tick=20 opsclk=200000"},
        {"seed": 1, "grep": "x OPEX 1970-1-2 C56_TASK TASK_EXIT name=catalog cycle=0 tick=21 opsclk=250000"},
        {"seed": 1, "grep": "x OPEX 1970-1-3 C56_TASK WORKER_ENTER name=rail_search cycle=- tick=30 opsclk=300000"},
        {"seed": 1, "grep": "x OPEX 1970-1-5 C56_TASK INTENT_ENTER name=c77_build cycle=- tick=40 opsclk=400000"},
        {"seed": 1, "grep": "x OPEX 1970-1-5 C56_TASK INTENT_EXIT name=c77_build cycle=- tick=41 opsclk=405000 dispatched=1"},
        {"seed": 1, "grep": "x OPEX 1970-1-9 C56_TASK WORKER_EXIT name=rail_search cycle=- tick=90 opsclk=900000 outcome=done steps=3 step_ops=77"},
        {"seed": 1, "tag": "C76_REGEN", "_log_year": 1970, "_log_date": "1970-1-1", "phase": "regen",
         "kind": "full", "reason": "initial", "ops": "150000", "freight_cargo": "COAL"},
        {"seed": 1, "tag": "C76_REGEN", "_log_year": 1970, "_log_date": "1970-2-1", "phase": "regen_avoided"},
        {"seed": 1, "tag": "C76_REGEN", "_log_year": 1970, "_log_date": "1970-3-1", "phase": "regen",
         "kind": "full", "reason": "layers", "ops": "100", "freight_cargo": "WOOD"},
        {"seed": 1, "tag": "C76_REGEN", "_log_year": 1971, "_log_date": "1971-3-1", "phase": "regen",
         "kind": "incremental", "reason": "post_build", "ops": "5", "freight_cargo": "WOOD"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.jsonl"
        raw.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
        chrono = Path(tmp) / "chrono.csv"
        out = analyse(raw, chrono)
        steps = {(r["fam"], r["name"]): r for r in out["steps"]}
        assert steps[("TASK", "catalog")]["ops_total"] == 150000
        assert steps[("TASK", "catalog")]["self_ops_total"] == 60000
        assert steps[("STAGE", "c56_stage_rail")]["ops_total"] == 90000
        assert steps[("WORKER", "rail_search")]["ops_total"] == 77
        assert steps[("INTENT", "c77_build")]["ops_total"] == 5000
        y70 = out["seeds"][1]["years"][1970]
        assert y70["full"] == 2 and y70["avoided"] == 1 and y70["cargos"] == ["COAL", "WOOD"]
        assert y70["rotations"] == 1 and out["seeds"][1]["years"][1971]["rotations"] == 0
        rows = list(csv.reader(chrono.open(encoding="utf-8")))
        assert rows[1][3:5] == ["TASK", "catalog"] and rows[1][2] == "10", rows[:3]
        assert rows[3][3:5] == ["REGEN", "full:initial"], rows[:4]
    print("selftest passed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw", nargs="*", type=Path, help="jsonl bruts, un par bras")
    ap.add_argument("--chrono-dir", type=Path, default=None,
                    help="écrit <nom du jsonl>_chrono.csv dans ce dossier")
    ap.add_argument("--json", type=Path, default=None, help="résumé JSON de tous les bras")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.raw:
        ap.error("au moins un jsonl brut")
    summary = {}
    for raw in args.raw:
        chrono = None
        if args.chrono_dir:
            chrono = args.chrono_dir / (raw.stem.replace("_raw", "") + "_chrono.csv")
        out = analyse(raw, chrono, args.top)
        print_report(raw.name, out, args.top)
        summary[raw.name] = out
    if args.json:
        args.json.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
