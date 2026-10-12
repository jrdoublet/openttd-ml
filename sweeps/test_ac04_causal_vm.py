"""AC04-A fixed-input Squirrel VM exposure fixture; no production changes.

Prepare the fixture with --prepare-out, inspect it, then (only when coordinated)
run --run-out through the existing single-game NoAI driver. This is a synthetic
projection of the four orphan loops plus the actual production route counter;
it is not a full discovery replay or a behavioral A/B qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_NAME = "ac04_causal_vm.nut"

FIXTURE = r'''/* VM only: route count calls through real OpexAir0310CountStationRoutes.
 * All station IDs/lines below are synthetic; API doubles restored before play.
 * ref/v1/v2 are PROJECTIONS of the discovery branch, not entire air_planning.
 */
FXAC04_SINK <- 0;
function FxAC04Index(lines) {
  local index = {};
  foreach (line in lines) {
    if (line.mode != "air") continue;
    local a = line.stationA, b = line.stationB;
    index.rawset(a, (a in index ? index[a] : 0) + 1);
    if (b != a) index.rawset(b, (b in index ? index[b] : 0) + 1);
  }
  return index;
}
function FxAC04Data(kind, c80) {
  local lines = [];
  local n = kind == "free" ? 2 : (kind == "saturated" || kind == "dead" ? 4 : 0);
  for (local i=0; i<n; i++) {
    lines.append({ mode="air", stationA=10, stationB=40+i,
      deadStreak=kind == "dead" ? 2 : 0 });
  }
  return { lines=lines, hubIndex=c80 ? {routes=FxAC04Index(lines)} : null,
    hubs=[], stations=[10,20,30], maxRoutes=4 };
}
/* Real production fallback, with fake station-ID API to ensure the VM sees
 * exact route counts on synthetic lines and no physical world is affected. */
function FxAC04Count(ctx, st) {
  return OpexAir0310CountStationRoutes(ctx, st);
}
function FxAC04Direct(ctx, st) {
  if (ctx.hubIndex != null) return st in ctx.hubIndex.routes ? ctx.hubIndex.routes[st] : 0;
  return OpexAir0310CountStationRoutes(ctx, st);
}
/* Modes: 0=HEAD historical, 1=v1 orphan rescan, 2=v2 early-mark + index,
 * 3=targeted candidate: exact same sequence as v2 for this local projection. */
function FxAC04Discover(ctx, mode, restored) {
  local seen = {}, hubs = [], origins = [];
  foreach (line in ctx.lines) {
    if (line.mode != "air" || line.deadStreak >= 2) continue;
    foreach (st in [line.stationA, line.stationB]) {
      if (st in seen) continue;
      if (mode >= 2) seen.rawset(st,true);
      local count = FxAC04Count(ctx, st);
      if (count >= ctx.maxRoutes) continue;
      seen.rawset(st,true);
      hubs.append({stationId=st,routes=count}); origins.append(0);
    }
  }
  foreach (st in ctx.stations) {
    if (st in seen) continue;
    local count = mode == 0 ? 0 : (mode == 1 ? FxAC04Count(ctx, st)
        : FxAC04Direct(ctx, st));
    if (mode != 0 && count >= ctx.maxRoutes) continue;
    seen.rawset(st,true);
    hubs.append({stationId=st,routes=count});
    origins.append(count > 0 && mode != 0 ? 0 : 1);
  }
  if (restored) {
    /* v1/v2 update formerly orphan hubs; legacy snapshot deliberately does not. */
    for (local i=0; i<hubs.len(); i++) {
      if (origins[i] && mode == 0) continue;
      hubs[i].routes = FxAC04Count(ctx, hubs[i].stationId);
    }
  }
  local digest=0;
  foreach (hub in hubs) digest += hub.stationId * 100 + hub.routes;
  return {digest=digest, count=hubs.len(), hubs=hubs, origin=origins};
}
function FxAC04Empty(ctx, mode, restored) { return {digest=0,count=0}; }
function FxAC04Ops(ctx, mode, restored, repeats, blank) {
  local start = OpexOpsClock(), sink = 0;
  for (local i=0; i<repeats; i++) {
    local row = blank ? FxAC04Empty(ctx, mode, restored)
      : FxAC04Discover(ctx, mode, restored);
    sink += row.digest + row.count;
  }
  local used = OpexOpsClock() - start;
  FXAC04_SINK += sink;
  return used;
}
function FxAC04Assert(ok, msg) { if (!ok) throw "AC04_CAUSAL_ASSERT " + msg; }
function FxAC04Start() {
  local oldStation = AIStation;
  local oldLineStation = OpexAirLineStationId;
  local failure = null;
  try {
    ::AIStation = { IsValidStation = function(st) { return st > 0; },
      GetStationID = function(tile) { return tile; } };
    ::OpexAirLineStationId = function(line, side) {
      return side == 0 ? line.stationA : line.stationB;
    };
    local kinds = ["zero","free","saturated","orphan","dead"];
    foreach (kind in kinds) {
      foreach (c80 in [0,1]) {
        foreach (restored in [0,1]) {
          local ctx = FxAC04Data(kind, c80);
          local legacy = FxAC04Discover(ctx,0,restored);
          local v1 = FxAC04Discover(ctx,1,restored);
          local v2 = FxAC04Discover(ctx,2,restored);
          local direct = FxAC04Discover(ctx,3,restored);
          FxAC04Assert(v1.digest == v2.digest && v1.count == v2.count,
            kind+" v1_v2 " + c80 + ":" + restored);
          FxAC04Assert(v2.digest == direct.digest && v2.count == direct.count,
            kind+" v2_direct " + c80 + ":" + restored);
          FxAC04Assert(kind != "saturated" || legacy.digest != v2.digest,
            "saturated_not_exposed");
          local loops = 16;
          local empty = FxAC04Ops(ctx,0,restored,loops,true);
          /* Rotating AB / BA order removes a fixed first-run advantage. */
          for (local pass=0; pass<2; pass++) {
            for (local j=0; j<4; j++) {
              local arm = pass == 0 ? j : 3-j;
              local ops = FxAC04Ops(ctx,arm,restored,loops,false);
              AILog.Info("AC04_CAUSAL_VM kind="+kind+" c80="+c80
                +" restored="+restored+" pass="+pass+" arm="+arm
                +" calls="+loops+" ops="+ops+" empty_ops="+empty
                +" digest="+(arm==0?legacy.digest:v2.digest)
                +" hubs="+(arm==0?legacy.count:v2.count));
            }
          }
        }
      }
    }
    AILog.Info("AC04_CAUSAL_VM_COMPLETE pass=1 sink="+FXAC04_SINK);
  } catch (err) { failure = err; }
  ::AIStation = oldStation;
  ::OpexAirLineStationId = oldLineStation;
  if (failure != null) throw failure;
}
'''


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stage(folder: Path):
    folder.mkdir(parents=True, exist_ok=False)
    source = ROOT / "ai/OpexAI"
    target = folder / "ai/OpexAI"
    shutil.copytree(source, target)
    (target / SCRIPT_NAME).write_text(FIXTURE, encoding="utf-8")
    main = target / "main.nut"
    code = main.read_text(encoding="utf-8")
    assert code.count("function OpexAI::Start()") == 1
    assert code.count("  OpexLoadSettings();") == 1
    code = code.replace("function OpexAI::Start()",
                        f'require("{SCRIPT_NAME}");\nfunction OpexAI::Start()')
    code = code.replace("  OpexLoadSettings();",
                        "  OpexLoadSettings();\n  if (!this._loadedFromSave) FxAC04Start();")
    main.write_text(code, encoding="utf-8")
    manifest = {
        "kind": "AC04-A matched-input synthetic Squirrel VM, not global A/B",
        "base_sha256": sha((source / "air_planning.nut").read_bytes()),
        "fixture_sha256": sha(FIXTURE.encode("utf-8")),
        "stage_main_sha256": sha(main.read_bytes()),
        "source_root": str(source), "stage_root": str(target),
        "scenarios": ["zero", "free", "saturated", "orphan", "dead"],
        "c80": [0, 1], "snapshot_refresh": [0, 1],
        "arms": ["legacy", "v1 projection", "v2 projection", "direct-index projection"],
        "repeat": 16, "order": "ABCD then DCBA", "measured": "NoAI VM opcode clock",
        "limitations": ["synthetic station IDs and stubbed AIStation, restored at end",
                        "discovery control-flow projection; not entire production DiscoverHubs",
                        "no ranking, no terrain, no economic and no global VM equivalence"],
    }
    (folder / "plan.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def parse(log):
    rows = []
    pat = re.compile(r"AC04_CAUSAL_VM kind=(\w+) c80=(\d) restored=(\d) pass=(\d) "
                     r"arm=(\d) calls=(\d+) ops=(\d+) empty_ops=(\d+) "
                     r"digest=(\d+) hubs=(\d+)")
    for matched in pat.finditer(log):
        kind = matched.group(1)
        nums = list(map(int, matched.groups()[1:]))
        rows.append(dict(zip(("c80", "restored", "pass", "arm", "calls", "ops",
                              "empty_ops", "digest", "hubs"), nums), kind=kind))
    scenarios = {(r["kind"], r["c80"], r["restored"], r["pass"], r["arm"]) for r in rows}
    expected = {(kind, c80, restored, pass_no, arm)
                for kind in ("zero", "free", "saturated", "orphan", "dead")
                for c80 in (0, 1) for restored in (0, 1)
                for pass_no in (0, 1) for arm in (0, 1, 2, 3)}
    ok = (len(rows) == 160 and scenarios == expected
          and "AC04_CAUSAL_VM_COMPLETE pass=1" in log)
    if not ok:
        raise ValueError(f"incomplete VM matrix {len(rows)}/160 (unique={len(scenarios)})")
    for kind in ("zero", "free", "saturated", "orphan", "dead"):
        for c80 in (0, 1):
            for restored in (0, 1):
                s = [r for r in rows if (r["kind"], r["c80"], r["restored"]) == (kind,c80,restored)]
                assert len(s) == 8 and all(r["calls"] == 16 for r in s)
                by_arm = {(r["pass"], r["arm"]): r for r in s}
                for pass_no in (0, 1):
                    for arm in (1, 2, 3):
                        lhs = by_arm[(pass_no, arm)]
                        rhs = by_arm[(pass_no, 2)]
                        assert lhs["digest"] == rhs["digest"] and lhs["hubs"] == rhs["hubs"]
                for arm in (0, 1, 2, 3):
                    assert by_arm[(0, arm)]["digest"] == by_arm[(1, arm)]["digest"]
                    assert by_arm[(0, arm)]["hubs"] == by_arm[(1, arm)]["hubs"]
    return rows


def run(folder: Path):
    import openttdlab
    from . import save_load_roundtrip as driver
    from .game_health import assess_game, parse_script_errors
    from .run_mechanism_fixtures import parse_saves, phase_integrity

    target = stage(folder)
    driver.CACHE_DIR = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
    driver.SCRIPT_DEBUG_LEVEL = "4"
    arm = openttdlab.local_folder(str(target), "OpexAI", ())
    _, log, saves = driver.run_phase_a(42, 1, arm, driver.bench_v2.make_cfg(1970),
                                     folder / "rows.jsonl", folder / "saves")
    log = log or ""
    (folder / "engine.log").write_text(log, encoding="utf-8")
    rows = parse(log)
    records = parse_saves(saves)
    health = assess_game([r["company"] for r in records], starting_year=1970,
                        years=1, expected_companies=("OpexAI",), engine_log=log)
    checks = phase_integrity({"records": records, "health": health,
                              "script_errors": parse_script_errors(log)}, "1970-01-01", 1)
    report = {"technical_pass": all(checks.values()), "checks": checks,
              "rows": rows, "health": health, "economic_verdict": "not_evaluated",
              "global_opcode_verdict": "not_evaluated"}
    (folder / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["technical_pass"]:
        raise RuntimeError("VM fixture failed technical health")
    print(json.dumps({"checks": checks, "rows": len(rows)}))


class TestAC04CausalVM(unittest.TestCase):
    def test_contracts_and_vm_branch_isolation(self):
        head = (ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
        self.assertIn("function OpexAir0310CountStationRoutes(ctx, stationId)", head)
        self.assertIn("if (routeCount >= maxRoutes) continue;", head)
        self.assertIn("hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 });", head)
        self.assertIn("if (isOrphan) continue;", head)
        self.assertEqual(FIXTURE.count("::AIStation ="), 2)

    def test_parse_requires_full_matrix(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            parse("AC04_CAUSAL_VM_COMPLETE pass=1")

    def test_parse_complete_matrix_and_order(self):
        rows = []
        for kind in ("zero", "free", "saturated", "orphan", "dead"):
            for c80 in (0, 1):
                for restored in (0, 1):
                    for pass_no in (0, 1):
                        for arm in ((0, 1, 2, 3) if pass_no == 0 else (3, 2, 1, 0)):
                            digest = 100 if arm == 0 else 99
                            rows.append("AC04_CAUSAL_VM kind=" + kind
                                        + f" c80={c80} restored={restored} pass={pass_no}"
                                        + f" arm={arm} calls=16 ops=100 empty_ops=4"
                                        + f" digest={digest} hubs=1")
        rows.append("AC04_CAUSAL_VM_COMPLETE pass=1 sink=3199")
        self.assertEqual(len(parse("\n".join(rows))), 160)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-out", type=Path)
    parser.add_argument("--run-out", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.prepare_out:
        print(stage(args.prepare_out.resolve()))
    elif args.run_out:
        run(args.run_out.resolve())
    else:
        unittest.main(argv=[__file__])
