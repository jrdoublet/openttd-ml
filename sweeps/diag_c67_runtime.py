"""C67.4 runtime diagnostic: bench_v2 solo arms, script log level 4, equivalence check.

Runs `bench_v2.main()` unchanged (same arms syntax, config, extractors, audits and
checkpoints) with `-d script=4` injected into the OpenTTD command, so that the yearly
`C67_TERRAIN` AILog line is captured. Then, from the written JSON:

* compares every paired monthly checkpoint of the reference arm (first) with each other
  arm on all game fields (opcode telemetry fields are reported separately);
* extracts the C67_TERRAIN lines of each run.

Without a consumer, the C67.4 contract (section 14) expects identical game fields: the
service only uses tick slack before Sleep(1). A difference is a defect, not a result.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import openttdlab

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_v2  # noqa: E402

C67_RE = re.compile(r"(C67[A-Z_]*) ((?:[a-z_]+=[^ \n]+ ?)+)")
DECISION_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+) ([^\n]*)")
_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


def parse_terrain(output: str | None) -> list[dict]:
    """C67 AILog lines (C67_TERRAIN, C67W_YEAR, C67W_EXPO...), each tagged by its prefix."""
    lines = []
    for match in C67_RE.finditer(output or ""):
        fields: dict = {"tag": match.group(1)}
        for item in match.group(2).split():
            key, value = item.split("=", 1)
            try:
                fields[key] = int(value)
            except ValueError:
                fields[key] = value
        lines.append(fields)
    return lines


def parse_decisions(output: str | None, kinds: set[str]) -> list[dict]:
    """OpexDecide lines of the requested kinds, with their date and key=value fields."""
    out = []
    for match in DECISION_RE.finditer(output or ""):
        if match.group(4) not in kinds:
            continue
        fields: dict = {"event": match.group(4),
                        "date": f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"}
        for item in match.group(5).split():
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            try:
                fields[key] = int(value)
            except ValueError:
                fields[key] = value
        out.append(fields)
    return out


def is_opcode_field(name: str) -> bool:
    return "opcode" in name or "kopcodes" in name


def equivalence(series: list[dict], reference: str) -> dict:
    by: dict[tuple, dict[str, dict]] = {}
    for row in series:
        arm, seed, repeat = row["run"][:3]
        by.setdefault((seed, repeat, row["date"]), {})[arm] = row
    report: dict[str, dict] = {}
    for key, arms in sorted(by.items()):
        base = arms.get(reference)
        for arm, row in arms.items():
            if arm == reference:
                continue
            entry = report.setdefault(arm, {"paired": 0, "unpaired": 0, "game_diffs": [],
                                            "opcode_diff_checkpoints": 0})
            if base is None:
                entry["unpaired"] += 1
                continue
            entry["paired"] += 1
            fields = set(base) | set(row)
            game = sorted(f for f in fields if f != "run" and not is_opcode_field(f)
                          and base.get(f) != row.get(f))
            if game:
                entry["game_diffs"].append({"seed": key[0], "repeat": key[1], "date": key[2],
                                            "fields": game})
            if any(base.get(f) != row.get(f) for f in fields if is_opcode_field(f)):
                entry["opcode_diff_checkpoints"] += 1
    return report


def selftest():
    out = ("x\nC67_TERRAIN year=1970 resident=12 ops_max=1240\n"
           "C67W_EXPO dock_a=5 result=connected profit=-\n")
    assert parse_terrain(out) == [
        {"tag": "C67_TERRAIN", "year": 1970, "resident": 12, "ops_max": 1240},
        {"tag": "C67W_EXPO", "dock_a": 5, "result": "connected", "profit": "-"}]
    row = {"run": ["A", 1, 0], "date": "1970-02-01", "money": 5, "observed_opcodes_total": 1}
    other = dict(row, run=["B", 1, 0], observed_opcodes_total=2)
    rep = equivalence([row, other], "A")
    assert rep["B"]["paired"] == 1 and not rep["B"]["game_diffs"]
    assert rep["B"]["opcode_diff_checkpoints"] == 1
    rep = equivalence([row, dict(other, money=6)], "A")
    assert rep["B"]["game_diffs"][0]["fields"] == ["money"]
    log = ("[I] OPEX 1971-3-5 RAIL_ATTEMPT src=10 dst=20 model=100 reason=- ok=1\n"
           "[I] OPEX 1971-3-5 TASK name=projects\n")
    got = parse_decisions(log, {"RAIL_ATTEMPT"})
    assert got == [{"event": "RAIL_ATTEMPT", "date": "1971-03-05", "src": 10, "dst": 20,
                    "model": 100, "reason": "-", "ok": 1}]


def main():
    if "--selftest" in sys.argv:
        selftest()
        print("C67 runtime selftest OK")
        return
    kinds: set[str] = set()
    if "--decision-kinds" in sys.argv:
        i = sys.argv.index("--decision-kinds")
        kinds = set(sys.argv[i + 1].split(","))
        del sys.argv[i:i + 2]
    openttdlab.subprocess.check_output = _check_output_with_script_debug
    try:
        bench_v2.main()
    finally:
        openttdlab.subprocess.check_output = _real_check_output
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    data = json.loads(out.read_text(encoding="utf-8"))
    reference = data["arms"][0]
    terrain = {f"{r['arm']}|{r['seed']}|{r['repeat']}": parse_terrain(r.get("openttd_output"))
               for r in data["summary"]}
    decisions = ({f"{r['arm']}|{r['seed']}|{r['repeat']}": parse_decisions(r.get("openttd_output"), kinds)
                  for r in data["summary"]} if kinds else {})
    report = {"reference": reference, "equivalence": equivalence(data["series"], reference),
              "terrain": terrain, "decisions": decisions, "completeness": data["completeness"]}
    report_path = out.with_name(out.stem + "_c67.json")
    bench_v2.write_json_atomically(report_path, report)
    print(json.dumps({"equivalence": {arm: {k: (len(v) if k == "game_diffs" else v)
                                            for k, v in entry.items()}
                                      for arm, entry in report["equivalence"].items()},
                      "c67_lines": {run: {tag: sum(1 for l in lines if l["tag"] == tag)
                                          for tag in {l["tag"] for l in lines}}
                                    for run, lines in terrain.items()}}, indent=2))


if __name__ == "__main__":
    main()
