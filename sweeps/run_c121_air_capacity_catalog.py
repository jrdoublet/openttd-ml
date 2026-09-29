#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile

import openttdlab
from openttdlab import local_folder, run_experiments

from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
CAP_RE = re.compile(r"C121_CAP\s+(.*)")
DONE_RE = re.compile(r"C121_CAP_DONE\s+(.*)")

def parse_fields(text):
    out = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            out[key] = int(value)
        except ValueError:
            out[key] = value
    return out

def write_probe_ai(folder):
    folder.mkdir(parents=True, exist_ok=True)
    info = (
        'class C121CapInfo extends AIInfo {\n'
        '  function GetAuthor() { return "openttd-ml"; }\n'
        '  function GetName() { return "C121CapProbe"; }\n'
        '  function GetDescription() { return "C121 one-shot AIR capacity catalog probe"; }\n'
        '  function GetVersion() { return 1; }\n'
        '  function GetDate() { return "2026-09-28"; }\n'
        '  function CreateInstance() { return "C121CapProbe"; }\n'
        '  function GetShortName() { return "CACP"; }\n'
        '  function GetAPIVersion() { return "15"; }\n'
        '}\nRegisterAI(C121CapInfo());\n'
    )
    (folder / "info.nut").write_text(info, encoding="utf-8")
    main_nut = r'''class C121CapProbe extends AIController {
  function Save() { return {}; }
  function _FindCargo(cls) {
    local list = AICargoList();
    for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
      if (AICargo.HasCargoClass(c, cls)) return c;
    }
    return -1;
  }

  function _BuildAirport() {
    local airportType = AIAirport.AT_LARGE;
    if (!AIAirport.IsValidAirportType(airportType)) return -1;
    local w = AIAirport.GetAirportWidth(airportType);
    local h = AIAirport.GetAirportHeight(airportType);
    local sx = AIMap.GetMapSizeX();
    local sy = AIMap.GetMapSizeY();
    for (local y = 2; y + h + 2 < sy; y++) {
      for (local x = 2; x + w + 2 < sx; x++) {
        local tile = AIMap.GetTileIndex(x, y);
        local ok = false;
        {
          local test = AITestMode();
          ok = AIAirport.BuildAirport(tile, airportType, AIStation.STATION_NEW);
        }
        if (!ok) continue;
        if (AIAirport.BuildAirport(tile, airportType, AIStation.STATION_NEW) ) return tile;
      }
    }
    return -1;
  }

  function _Measure(hangar, pax, mail, seen) {
    local engines = AIEngineList(AIVehicle.VT_AIR);
    for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
      if (e in seen || !AIEngine.IsBuildable(e) || !AIEngine.CanRefitCargo(e, pax)) continue;
      local pt = AIEngine.GetPlaneType(e);
      if (pt != AIAirport.PT_SMALL_PLANE && pt != AIAirport.PT_BIG_PLANE) continue;
      local vehicle = AIVehicle.BuildVehicleWithRefit(hangar, e, pax);
      if (!AIVehicle.IsValidVehicle(vehicle)) continue;
      local paxCap = AIVehicle.GetCapacity(vehicle, pax);
      local mailCap = AIVehicle.GetCapacity(vehicle, mail);
      AILog.Warning("C121_CAP engine=" + e
          + " pax=" + paxCap + " mail=" + mailCap
          + " price=" + AIEngine.GetPrice(e)
          + " running=" + AIEngine.GetRunningCost(e)
          + " speed=" + AIEngine.GetMaxSpeed(e)
          + " plane_type=" + pt);
      seen.rawset(e, true);
      AIVehicle.SellVehicle(vehicle);
    }
  }

  function Start() {
    AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
    local pax = this._FindCargo(AICargo.CC_PASSENGERS);
    local mail = this._FindCargo(AICargo.CC_MAIL);
    if (pax < 0 || mail < 0) {
      AILog.Error("C211_CAP_ERROR cargo pax=" + pax + " mail=" + mail);
      return;
    }
    local airport = this._BuildAirport();
    if (!AIAirport.IsAirportTile(airport)) {
      AILog.Error("C121_CAP_ERROR no_airport tile=" + airport);
      return;
    }
    local hangar = AIAirport.GetHangarOfAirport(airport);
    if (hangar < 0) {
      AILog.Error("C211_CAP_ERROR no_hangar tile=" + hangar);
      return;
    }
    local seen = {};
    for (local day = 0; day <= 365; day += 30) {
      this._Measure(hangar, pax, mail, seen);
      this.Sleep(30);
    }
    AILog.Warning("C121_CAP_DONE count=" + seen.len());
    while (true) this.Sleep(365);
  }
}
'''
    (folder / "main.nut").write_text(main_nut, encoding="utf-8")

def main():
    out = ROOT / "results" / "c121_air_capacity_catalog_1975_20260928.json"
    enable_savegame_cleanup()
    with tempfile.TemporaryDirectory(prefix="c121-cap-") as tmp:
        ai_dir = Path(tmp) / "C121CapProbe"
        write_probe_ai(ai_dir)
        ai = local_folder(str(ai_dir), "C121CapProbe")
        experiment = {
            "seed": 42,
            "days": 365 + 60,
            "openttd_config": make_cfg(1975),
            "ais": (ai,),
        }
        real_check_output = openttdlab.subprocess.check_output

        def debug_output(call_args, *rest, **kwargs):
            call_args = tuple(call_args)
            if any(str(arg).startswith("-vnull") for arg in call_args):
                call_args = call_args[:1] + ("-d", "script=4") + call_args[1:]
            return real_check_output(call_args, *rest, **kwargs)

        openttdlab.subprocess.check_output = debug_output
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=(experiment,),
            max_workers=1,
            result_processor=lambda row: (row,),
        ))

    capacities = {}
    errors = []
    done = []
    for row in rows:
        output = row.get("output", "") or ""
        if "C121_CAP_ERROR" in output or "SCRIPE ERROR" in output or "Script died unexpectedly" in output:
            errors.append(output[-4000:])
        for fields in CAP_RE.findall(output):
            parsed = parse_fields(fields)
            engine = parsed.get("engine")
            if isinstance(engine, int):
                capacities[str(engine)] = parsed
        done.extend(parse_fields(fields) for fields in DONE_RE.findall(output))

    result = {
        "purpose": "C121 disposable static AIR PASS/MAIL capacity catalog; host-side replay only",
        "openttd_version": OPENTTD_VERSION,
      "opengfx_version": OPENGFX_VERSION,
      "start_year": 1975,
        "years": 1,
        "capacity_count": len(capacities),
        "capacities": capacities,
        "done": done,
        "errors": errors,
        "output_tail": [str(row.get("output", "") or "")[-8000:] for row in rows],
    }
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Sortie: {out}")
    if errors or not capacities:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
