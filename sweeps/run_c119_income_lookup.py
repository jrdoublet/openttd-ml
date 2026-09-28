#!/usr/bin/env python3
"""C119: query AICargo.GetCargoIncome for the static C117 route tuples.

The generated NoAI is a pure lookup probe: it does not build anything and does
not reuse OpexAI decision code. This lets C117 be re-analysed offline with the
exact OpenTTD 15.3 cargo-income API.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tempfile

import openttdlab
from openttdlab import local_folder, run_experiments

from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"C119_INCOME\s+(.*)")


def parse_fields(text: str):
    result = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            result[key] = int(value)
        except ValueError:
            result[key] = value
    return result


def line_queries(payload):
    queries = {}
    for row in payload.get("rows", []):
        seed = row.get("seed")
        for event in row.get("events", []):
            line = event.get("line")
            engine = event.get("build_engine")
            distance = event.get("distance")
            pred_days = event.get("pred_oneway_days")
            if not all(isinstance(v, (int, float)) for v in (seed, line, engine, distance, pred_days)):
                continue
            key = f"{int(seed)}_{int(line)}"
            queries[key] = {
                "key": key,
                "engine": int(engine),
                "distance": int(distance),
                "legacy_days": max(1, int(float(pred_days) + 0.999999999)),
            }
    return [queries[key] for key in sorted(queries)]


def write_probe_ai(folder: Path, queries):
    folder.mkdir(parents=True, exist_ok=True)
    info = (
        'class C119IncomeProbeInfo extends AIInfo {\n'
        '  function GetAuthor() { return "openttd-ml"; }\n'
        '  function GetName() { return "C119IncomeProbe"; }\n'
        '  function GetDescription() { return "Pure cargo-income lookup for C119"; }\n'
        '  function GetVersion() { return 1; }\n'
        '  function GetDate() { return "2026-09-28"; }\n'
        '  function CreateInstance() { return "C119IncomeProbe"; }\n'
        '  function GetShortName() { return "C119"; }\n'
        '  function GetAPIVersion() { return "15"; }\n'
        '}\n'
        'RegisterAI(C119IncomeProbeInfo());\n'
    )
    (folder / "info.nut").write_text(info, encoding="utf-8")

    query_lines = ",\n".join(
        '    { key = "%s", engine = %d, distance = %d, legacyDays = %d }'
        % (q["key"], q["engine"], q["distance"], q["legacy_days"])
        for q in queries
    )
    main = f'''class C119IncomeProbe extends AIController {{
  function Start() {{
    local pax = -1;
    local mail = -1;
    local cargos = AICargoList();
    for (local c = cargos.Begin(); !cargos.IsEnd(); c = cargos.Next()) {{
      if (pax < 0 && AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) pax = c;
      if (mail < 0 && AICargo.HasCargoClass(c, AICargo.CC_MAIL)) mail = c;
    }}
    if (pax < 0 || mail < 0) {{
      AILog.Error("C119_INCOME_ERROR pax=" + pax + " mail=" + mail);
      while (true) this.Sleep(1000);
    }}
    local queries = [
{query_lines}
    ];
    foreach (q in queries) {{
      if (!AIEngine.IsValidEngine(q.engine)) {{
        AILog.Warning("C119_INCOME key=" + q.key + " invalid=1 engine=" + q.engine);
        continue;
      }}
      local speed = AIEngine.GetMaxSpeed(q.engine);
      if (speed <= 0) continue;
      local aaaDays = max(1, (q.distance + 30) * 664 / speed / 24);
      AILog.Warning("C119_INCOME key=" + q.key
          + " engine=" + q.engine + " distance=" + q.distance + " speed=" + speed
          + " legacy_days=" + q.legacyDays + " aaa_days=" + aaaDays
          + " pax_legacy=" + AICargo.GetCargoIncome(pax, q.distance, q.legacyDays)
          + " mail_legacy=" + AICargo.GetCargoIncome(mail, q.distance, q.legacyDays)
          + " pax_aaa=" + AICargo.GetCargoIncome(pax, q.distance, aaaDays)
          + " mail_aaa=" + AICargo.GetCargoIncome(mail, q.distance, aaaDays));
    }}
    while (true) this.Sleep(1000);
  }}
}}
'''
    (folder / "main.nut").write_text(main, encoding="utf-8")


def keep(row):
    return (row,)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, nargs="?",
        default=ROOT / "results" / "c117_air_throughput_5x6_20260927_r2.json",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "results" / "c119_income_lookup_c117_20260928.json",
    )
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    queries = line_queries(payload)
    if not queries:
        raise SystemExit("no C117 queries")

    enable_savegame_cleanup()
    with tempfile.TemporaryDirectory(prefix="c119-income-") as tmp:
        ai_dir = Path(tmp) / "C119IncomeProbe"
        write_probe_ai(ai_dir, queries)
        ai = local_folder(str(ai_dir), "C119IncomeProbe")
        experiment = {
            "seed": 42,
            "days": 31,
            "openttd_config": make_cfg(1970),
            "ais": (ai,),
        }
        real_check_output = openttdlab.subprocess.check_output

        def debug_output(call_args, *rest, **kwargs):
            call_args = tuple(call_args)
            if any(str(arg).startswith("-vnull") for arg in call_args):
                call_args = call_args[:1] + ("-d", "script=4") + call_args[1:]
            return real_check_output(call_args, *rest, **kwargs)

        debug_output._c119_script_debug = True
        openttdlab.subprocess.check_output = debug_output
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=[experiment],
            max_workers=1,
            result_processor=keep,
        ))

    lookup = {}
    errors = []
    for row in rows:
        output = row.get("output", "") or ""
        if "C119_INCOME_ERROR" in output:
            errors.append("cargo_detection")
        for fields in TAG_RE.findall(output):
            parsed = parse_fields(fields)
            key = parsed.get("key")
            if key is not None:
                lookup[str(key)] = parsed
    result = {
        "source": str(args.input),
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "query_count": len(queries),
        "lookup_count": len(lookup),
        "errors": errors,
        "lookup": lookup,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("query_count", "lookup_count", "errors")}, indent=2))
    print(f"Sortie: {args.out}")
    if errors or len(lookup) != len(queries):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
