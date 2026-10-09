#!/usr/bin/env python3
"""Autopsie passive du nivellement de B : résultat commande, terrain avant/après.

N'utilise que les champs b_level_* du même AIR_FINANCE_TRY que le prétest et
l'issue réelle. Une erreur 263 peut venir de LevelTiles OU de la postvérification
de OpexAirLevelFootprint ; les deux mécanismes restent séparés.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from analyse_air_bfail_precheck_shadow import PATTERN, analyze_lines
from parse_air_finance_margin import RE_KV, clean_log_line, parse_kv_payload


NUMBERS = (
    "b_level_cmd_err", "b_level_retry_err", "b_level_w", "b_level_h",
    "b_level_end", "b_level_x", "b_level_y", "b_level_target_z",
    "b_level_slopes_setting", "b_level_cash_before", "b_level_cash_after",
    "b_level_pre_mismatch", "b_level_post_mismatch",
    "b_level_pre_blocked", "b_level_post_blocked",
    "b_level_pre_slopes", "b_level_post_slopes",
    "b_level_pre_invalid", "b_level_post_invalid",
    "b_level_pre_min", "b_level_pre_max", "b_level_post_min", "b_level_post_max",
    "b_level_changed",
)
TEXT = ("b_level_phase", "b_level_cmd", "b_level_pre_grid", "b_level_post_grid")
PHASES = {"invalid_end", "already_flat", "command_failed", "retry_failed",
          "postcheck_nonflat", "success"}
COMMANDS = {"not_called", "ok", "failed"}


def mismatched_footprint_tiles(grid, width, height):
    """Reproduit le test de GetMaxHeight relatif à l'ancre, avec coordonnées."""
    if grid[0] == "X":
        return None
    try:
        anchor_height = int(grid[0].rstrip("!").split(".")[1])
        tiles = []
        for dx in range(width):
            for dy in range(height):
                cell = grid[dx * (height + 1) + dy]
                if cell == "X":
                    return None
                low, high, slope = (int(s) for s in cell.rstrip("!").split("."))
                if high != anchor_height:
                    tiles.append({"dx": dx, "dy": dy, "low": low,
                                  "high": high, "slope": slope})
        return tiles
    except ValueError:
        return None


def analyze_geometry_lines(lines, filename):
    lines = list(lines)
    base = analyze_lines(lines, filename)
    payload_by_line = {}
    for line_no, line in enumerate(lines, 1):
        match = PATTERN.search(clean_log_line(line))
        if match is None:
            continue
        payload = match.group(1)
        names = [hit.group(1) for hit in RE_KV.finditer(payload)]
        if len(names) == len(set(names)):
            payload_by_line[line_no] = parse_kv_payload(payload)

    cases = []
    warnings = list(base["warnings"])
    for row in base["rows"]:
        if row["real_b_stage"] == "not_attempted":
            continue
        raw = payload_by_line.get(row["line"], {})
        missing = [name for name in (*NUMBERS, *TEXT) if name not in raw]
        if missing:
            warnings.append({"line": row["line"], "code": "missing_geometry_fields",
                             "fields": missing})
            continue
        try:
            parsed = {name: int(raw[name]) for name in NUMBERS}
        except ValueError:
            warnings.append({"line": row["line"], "code": "invalid_geometry_integer"})
            continue
        phase = raw["b_level_phase"]
        command = raw["b_level_cmd"]
        width, height = parsed["b_level_w"], parsed["b_level_h"]
        if (phase not in PHASES or command not in COMMANDS
                or width <= 0 or height <= 0 or width > 20 or height > 20):
            warnings.append({"line": row["line"], "code": "invalid_geometry_phase"})
            continue
        pre_grid = raw["b_level_pre_grid"].split(",")
        post_grid = raw["b_level_post_grid"].split(",")
        if len(pre_grid) != (width + 1) * (height + 1) or len(post_grid) != len(pre_grid):
            warnings.append({"line": row["line"], "code": "invalid_geometry_grid_length"})
            continue
        if (pre_grid.count("X") != parsed["b_level_pre_invalid"]
                or post_grid.count("X") != parsed["b_level_post_invalid"]):
            warnings.append({"line": row["line"], "code": "inconsistent_invalid_tiles"})
            continue
        pre_mismatch = mismatched_footprint_tiles(pre_grid, width, height)
        post_mismatch = mismatched_footprint_tiles(post_grid, width, height)
        if (pre_mismatch is None or post_mismatch is None
                or len(pre_mismatch) != parsed["b_level_pre_mismatch"]
                or len(post_mismatch) != parsed["b_level_post_mismatch"]):
            warnings.append({"line": row["line"], "code": "inconsistent_footprint_heights"})
            continue
        if (phase in {"success", "already_flat"} and post_mismatch
                or phase == "postcheck_nonflat" and not post_mismatch):
            warnings.append({"line": row["line"], "code": "inconsistent_postcheck_phase"})
            continue
        changed_tiles = sum(a != b for a, b in zip(pre_grid, post_grid))
        if parsed["b_level_changed"] != int(changed_tiles > 0):
            warnings.append({"line": row["line"], "code": "inconsistent_changed_flag"})
            continue
        if (row["real_b_stage"] == "level") != (phase in {
                "invalid_end", "command_failed", "retry_failed", "postcheck_nonflat"}):
            warnings.append({"line": row["line"], "code": "inconsistent_stage_phase"})
            continue
        cases.append({
            "seed": row["seed"], "arm": row["arm"], "repeat": row["repeat"],
            "line": row["line"], "date": row["date"], "reason": row["reason"],
            "real_b_stage": row["real_b_stage"],
            "pre_b_verdict": row["pre_b_verdict"],
            "pre_b_anchor": row["pre_b_anchor"],
            "real_b_err": row["real_b_err"],
            "phase": phase, "command": command, "changed_tiles": changed_tiles,
            "post_mismatch_tiles": post_mismatch,
            "pre_grid": pre_grid, "post_grid": post_grid, **parsed,
        })
    return {"file": filename, "seed": base["seed"], "arm": base["arm"],
            "repeat": base["repeat"], "attempted_b": sum(
                row["real_b_stage"] != "not_attempted" for row in base["rows"]),
            "parsed_b": len(cases), "cases": cases, "warnings": warnings}


def analyze(paths):
    runs, identities = [], set()
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as stream:
            run = analyze_geometry_lines(stream, path.name)
        identity = (run["arm"], run["seed"], run["repeat"])
        if identity in identities:
            raise ValueError(f"duplicate run {identity}")
        identities.add(identity)
        runs.append(run)
    cases = [case for run in runs for case in run["cases"]]
    failures = [case for case in cases if case["reason"] == "BFAIL"]
    return {"runs": runs, "summary": {
        "runs": len(runs),
        "attempted_b": sum(run["attempted_b"] for run in runs),
        "parsed_b": len(cases),
        "bfail": len(failures),
        "bfail_phases": dict(Counter(case["phase"] for case in failures)),
        "all_phases": dict(Counter(case["phase"] for case in cases)),
        "bfail_partial_terrain_change": sum(case["changed_tiles"] > 0 for case in failures),
        "warnings": sum(len(run["warnings"]) for run in runs),
    }, "caveat": "passive diagnostic with opcode/timing costs; BFAIL capital is not refunded"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args(argv)
    result = analyze(args.logs)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
