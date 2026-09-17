"""Analyse ciblée M4 : plafonds véhicules et pf.forbid_90_deg."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path


def _tokens(text):
    out = {}
    for token in text.strip().split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass
        out[key] = value
    return out


def collect_logs(engine_dir):
    rows = []
    for path in sorted(Path(engine_dir).glob("*.log")):
        rows.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
    return rows


def analyse_logs(engine_dir):
    result = {
        "logs": 0,
        "rail_build_fail_reasons": Counter(),
        "rail_build_fail_errors": Counter(),
        "rail_projects_chosen": 0,
        "abandon_pairs": 0,
        "rail_spend": {
            "planned_ok": 0, "actual_ok": 0, "n_ok": 0,
            "planned_fail": 0, "actual_fail": 0, "n_fail": 0,
        },
        "noai_errors": 0,
        "fatal_markers": [],
        "pure_notrain_years": [],
    }
    failures_by_log_year = defaultdict(Counter)
    spend_by_log_year = {}
    for name, text in collect_logs(engine_dir):
        result["logs"] += 1
        for line in text.splitlines():
            if "RAIL_BUILD_FAIL " in line:
                data = _tokens(line.split("RAIL_BUILD_FAIL ", 1)[1])
                result["rail_build_fail_reasons"][str(data.get("reason", "unknown"))] += 1
                result["rail_build_fail_errors"][str(data.get("error", "unknown"))] += 1
                marker = line.find(" OPEX ")
                if marker >= 0:
                    date_token = line[marker + 6:].split(" ", 1)[0]
                    try:
                        failures_by_log_year[(name, int(date_token.split("-", 1)[0]))][str(data.get("reason", "unknown"))] += 1
                    except (ValueError, IndexError):
                        pass
            if "PROJECT_CHOSEN " in line and " mode=rail " in f" {line} ":
                result["rail_projects_chosen"] += 1
            if "ABANDON_PAIR " in line:
                result["abandon_pairs"] += 1
            if "C63_INVEST " in line and "phase=spend" in line and "mode=rail" in line:
                data = _tokens(line.split("C63_INVEST ", 1)[1])
                for key in result["rail_spend"]:
                    result["rail_spend"][key] += int(data.get(key, 0))
                if "year" in data:
                    spend_by_log_year[(name, int(data["year"]))] = data
            lowered = line.lower()
            if "the script died unexpectedly" in lowered or ("noai" in lowered and "error" in lowered):
                result["noai_errors"] += 1
                if len(result["fatal_markers"]) < 20:
                    result["fatal_markers"].append({"log": name, "line": line[-500:]})
    result["rail_build_fail_reasons"] = dict(result["rail_build_fail_reasons"])
    result["rail_build_fail_errors"] = dict(result["rail_build_fail_errors"])
    result["infrastructure_spend_before_failed_rail_build"] = result["rail_spend"]["actual_fail"] > 0
    for key, reasons in sorted(failures_by_log_year.items()):
        spend = spend_by_log_year.get(key)
        if not spend or set(reasons) != {"NOTRAIN"}:
            continue
        if int(spend.get("n_fail", 0)) != reasons["NOTRAIN"] or int(spend.get("actual_fail", 0)) <= 0:
            continue
        result["pure_notrain_years"].append({
            "log": key[0],
            "year": key[1],
            "notrain_failures": reasons["NOTRAIN"],
            "actual_fail": int(spend["actual_fail"]),
            "planned_fail": int(spend.get("planned_fail", 0)),
        })
    result["pure_notrain_actual_fail"] = sum(row["actual_fail"] for row in result["pure_notrain_years"])
    return result


def scenario_summary(summary, scenario):
    rows = [row for row in summary if row.get("scenario") == scenario and row.get("arm") == "OpexAI"]
    return {
        "runs": len(rows),
        "complete": sum(row.get("run_ok") is True for row in rows),
        "company_value": [row.get("company_value") for row in rows],
        "profit_year": [row.get("profit_year") for row in rows],
        "primary_vehicles": [row.get("primary_vehicles") for row in rows],
        "stations": [row.get("n_stations") for row in rows],
        "vehicles_by_mode": [row.get("primary_vehicles_by_mode") for row in rows],
    }


def selftest():
    data = _tokens("reason=NOTRAIN error=10 iters=123 budget=456")
    assert data["reason"] == "NOTRAIN"
    assert data["iters"] == 123
    print("diag_m4_conformity selftest OK")


if __name__ == "__main__":
    selftest()
