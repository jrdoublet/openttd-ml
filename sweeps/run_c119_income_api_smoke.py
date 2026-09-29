#!/usr/bin/env python3
"""C119: smoke Docker de l'API AIR utilisée par le shadow C117.

Le mini-NoAI ne construit rien et ne modifie aucune décision OpexAI. Il vérifie
sur les lignes seed 42 que la reconstruction hors ligne reproduit exactement :
  - AIEngine.GetMaxSpeed(engine) ;
  - AICargo.GetCargoIncome(PASS/MAIL, distance, legacyDays) ;
  - AICargo.GetCargoIncome(PASS/MAIL, distance, aaaDays).
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile

import openttdlab
from openttdlab import local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_c119_air_income_shadow import (  # noqa: E402
    MAIL_PAYMENT,
    PAX_PAYMENT,
    cargo_income,
    script_air_speed,
)
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg  # noqa: E402


TAG_RE = re.compile(r"C119_API\s+(.*)")


def parse_fields(text):
    out = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key == "key":
            out[key] = value
            continue
        try:
            out[key] = int(value)
        except ValueError:
            out[key] = value
    return out


def seed_queries(payload, seed=42):
    queries = {}
    for row in payload.get("rows", []):
        if row.get("seed") != seed:
            continue
        for event in row.get("events", []):
            line = event.get("line")
            engine = event.get("build_engine")
            distance = event.get("distance")
            pred_days = event.get("pred_oneway_days")
            if not all(isinstance(v, (int, float)) for v in (line, engine, distance, pred_days)):
                continue
            key = f"{seed}_{int(line)}"
            queries[key] = {
                "key": key,
                "engine": int(engine),
                "distance": int(distance),
                "legacy_days": max(1, int(float(pred_days) + 0.999999999)),
            }
    return [queries[k] for k in sorted(queries)]


def write_probe_ai(folder, queries):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "info.nut").write_text(
        """class C119ApiSmokeInfo extends AIInfo {
  function GetAuthor() { return "openttd-ml"; }
  function GetName() { return "C119ApiSmoke"; }
  function GetDescription() { return "C119 pure NoAI API smoke"; }
  function GetVersion() { return 1; }
  function GetDate() { return "2026-09-28"; }
  function CreateInstance() { return "C119ApiSmoke"; }
  function GetShortName() { return "C119"; }
  function GetAPIVersion() { return "15"; }
}
RegisterAI(C119ApiSmokeInfo());
""",
        encoding="utf-8",
    )
    query_lines = ",\n".join(
        '      { key = "%s", engine = %d, distance = %d, legacyDays = %d }'
        % (q["key"], q["engine"], q["distance"], q["legacy_days"])
        for q in queries
    )
    (folder / "main.nut").write_text(
        f"""class C119ApiSmoke extends AIController {{
  function Start() {{
    local pax = -1;
    local mail = -1;
    local cargos = AICargoList();
    for (local c = cargos.Begin(); !cargos.IsEnd(); c = cargos.Next()) {{
      if (pax < 0 && AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) pax = c;
      if (mail < 0 && AICargo.HasCargoClass(c, AICargo.CC_MAIL)) mail = c;
    }}
    if (pax < 0 || mail < 0) {{
      AILog.Error("C119_API_ERROR pax=" + pax + " mail=" + mail);
      return;
    }}
    local queries = [
{query_lines}
    ];
    foreach (q in queries) {{
      if (!AIEngine.IsValidEngine(q.engine)) {{
        AILog.Error("C119_API_ERROR invalid_engine=" + q.engine + " key=" + q.key);
        continue;
      }}
      local speed = AIEngine.GetMaxSpeed(q.engine);
      local aaaDays = max(1, (q.distance + 30) * 664 / speed / 24);
      AILog.Warning("C119_API key=" + q.key
          + " engine=" + q.engine
          + " distance=" + q.distance
          + " speed=" + speed
          + " legacy_days=" + q.legacyDays
          + " aaa_days=" + aaaDays
          + " pax_legacy=" + AICargo.GetCargoIncome(pax, q.distance, q.legacyDays)
          + " mail_legacy=" + AICargo.GetCargoIncome(mail, q.distance, q.legacyDays)
          + " pax_aaa=" + AICargo.GetCargoIncome(pax, q.distance, aaaDays)
          + " mail_aaa=" + AICargo.GetCargoIncome(mail, q.distance, aaaDays));
    }}
    this.Sleep(1000);
  }}
}}
""",
        encoding="utf-8",
    )


def main():
    source = ROOT / "results" / "c117_air_throughput_5x6_20260927_r2.json"
    out = ROOT / "results" / "c119_income_api_smoke_seed42_20260928.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    queries = seed_queries(payload, 42)
    if not queries:
        raise SystemExit("no seed-42 C117 queries")

    enable_savegame_cleanup()
    with tempfile.TemporaryDirectory(prefix="c119-api-") as tmp:
        ai_dir = Path(tmp) / "C119ApiSmoke"
        write_probe_ai(ai_dir, queries)
        ai = local_folder(str(ai_dir), "C119ApiSmoke")
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

        openttdlab.subprocess.check_output = debug_output
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            experiments=(experiment,),
            max_workers=1,
            result_processor=lambda row: (row,),
        ))

    lookup = {}
    errors = []
    for row in rows:
        output = row.get("output", "") or ""
        if "C119_API_ERROR" in output or "SCRIPT ERROR" in output or "Script died unexpectedly" in output:
            errors.append(output[-4000:])
        for fields in TAG_RE.findall(output):
            parsed = parse_fields(fields)
            key = parsed.get("key")
            if key:
                lookup[str(key)] = parsed

    mismatches = []
    for q in queries:
        got = lookup.get(q["key"])
        if got is None:
            mismatches.append({"key": q["key"], "reason": "missing"})
            continue
        speed = script_air_speed(q["engine"])
        aaa_days = max(1, (q["distance"] + 30) * 664 // speed // 24)
        expected = {
            "speed": speed,
            "legacy_days": q["legacy_days"],
            "aaa_days": aaa_days,
            "pax_legacy": cargo_income(q["distance"], q["legacy_days"], PAX_PAYMENT),
            "mail_legacy": cargo_income(q["distance"], q["legacy_days"], MAIL_PAYMENT),
            "pax_aaa": cargo_income(q["distance"], aaa_days, PAX_PAYMENT),
            "mail_aaa": cargo_income(q["distance"], aaa_days, MAIL_PAYMENT),
        }
        bad = {k: {"expected": v, "actual": got.get(k)} for k, v in expected.items() if got.get(k) != v}
        if bad:
            mismatches.append({"key": q["key"], "fields": bad})

    result = {
        "purpose": "C119 pure API smoke; no OpexAI decision change",
        "seed": 42,
        "openttd_version": OPENTTD_VERSION,
        "opengfx_version": OPENGFX_VERSION,
        "query_count": len(queries),
        "lookup_count": len(lookup),
        "errors": errors,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "sample": [lookup[q["key"]] for q in queries[:5] if q["key"] in lookup],
    }
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if errors or len(lookup) != len(queries) or mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
