"""Mesure ponctuelle du pret et du solde de TrainLineAI sur une graine.

Ce script ne modifie jamais l'IA versionnee : il en copie une dans SCRATCH et
instrumente seulement cette copie par str.replace. Les panneaux LNM sont les
lectures directes exposees par OpenTTDLab dans le chunk SIGN.
"""
import json
import re
import shutil
import sys
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

NAME = "TrainLineAILoanMeasure20260827"
SCRATCH_BASE = "sweeps/loan_measurement_scratch_seed_"
OUTDIR = Path("data/loan_measurement_20260827")
EXPECTED = ("BEFORE", "MAX", "LOAN", "AFTER", "INTERVAL")
MEASURE_RE = re.compile(r"^LNM\|(BEFORE|MAX|LOAN|AFTER|INTERVAL|FINAL)\|(-?\d+)$")
STATUS_RE = re.compile(r"^TRLN\|\d+\|(success|partial)\|")


def make_scratch(seed):
    scratch = Path(SCRATCH_BASE + str(seed))
    if scratch.exists():
        raise RuntimeError(f"scratch already exists; refusing to overwrite: {scratch}")
    shutil.copytree("ai/TrainLineAI", scratch)

    main = scratch / "main.nut"
    text = main.read_text()
    old_loan = "  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());"
    new_loan = """  local loanBalanceBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  this._report("LNM|BEFORE|" + loanBalanceBefore);
  local loanMaximum = AICompany.GetMaxLoanAmount();
  this._report("LNM|MAX|" + loanMaximum);
  AICompany.SetLoanAmount(loanMaximum);
  this._report("LNM|LOAN|" + AICompany.GetLoanAmount());
  this._report("LNM|AFTER|" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
  this._report("LNM|INTERVAL|" + AICompany.GetLoanInterval());"""
    if text.count(old_loan) != 1:
        raise RuntimeError("expected exactly one SetLoanAmount call to patch")
    text = text.replace(old_loan, new_loan)

    old_report_all = """  if (this.costs != null) this.state.construction_cost = this.costs.GetCosts();
  this._report(this._code());"""
    new_report_all = """  if (this.costs != null) this.state.construction_cost = this.costs.GetCosts();
  /* Solde immediatement apres la construction complete, avant la boucle de sommeil. */
  if (this.state.stage == "success") {
    this._report("LNM|FINAL|" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
  }
  this._report(this._code());"""
    if text.count(old_report_all) != 1:
        raise RuntimeError("expected exactly one _reportAll prologue to patch")
    main.write_text(text.replace(old_report_all, new_report_all))

    info = scratch / "info.nut"
    info_text = info.read_text()
    old_name = 'function GetName()        { return "TrainLineAI"; }'
    if info_text.count(old_name) != 1:
        raise RuntimeError("expected exactly one AI name to patch")
    info.write_text(info_text.replace(old_name, f'function GetName()        {{ return "{NAME}"; }}'))
    return scratch


def retain(row):
    return ({
        "date": str(row["date"]),
        "seed": row["experiment"]["seed"],
        "raw_signs": [v["name"] for v in row["chunks"].get("SIGN", {}).values()],
    },)


def main(seed):
    scratch = make_scratch(seed)
    OUTDIR.mkdir(exist_ok=True)
    results = run_experiments(
        openttd_version="13.4",
        opengfx_version="7.1",
        max_workers=1,
        result_processor=retain,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
        experiments=(
            {
                "seed": seed,
                "days": 730,
                "openttd_config": CFG,
                "ais": (
                    local_folder(
                        str(scratch), NAME,
                        ai_params=(
                            ("num_trains", 2), ("wagons_per_train", 2),
                            ("engine_rank", 1), ("pair_rank", 0),
                            ("line_index", 0), ("stagger_slot", 0),
                        ),
                    ),
                ),
            },
        ),
    )
    latest = max(results, key=lambda r: r["date"])
    values = {}
    for sign in latest["raw_signs"]:
        match = MEASURE_RE.match(sign)
        if match:
            values[match.group(1)] = int(match.group(2))
    missing = [key for key in EXPECTED if key not in values]
    statuses = [m.group(1) for sign in latest["raw_signs"] if (m := STATUS_RE.match(sign))]
    payload = {
        "seed": seed,
        "days": 730,
        "config": CFG,
        "scratch": str(scratch),
        "all_captures": results,
        "latest_capture": latest,
        "measured_panel_values": values,
        "statuses": statuses,
        "verification": {
            "expected_panels_present": not missing,
            "missing": missing,
            "successful_construction_has_final_panel": "success" not in statuses or "FINAL" in values,
        },
    }
    output = OUTDIR / f"seed_{seed}.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "seed": seed,
        "latest_capture": latest,
        "measured_panel_values": values,
        "statuses": statuses,
        "verification": payload["verification"],
        "output": str(output),
    }, indent=2))
    if missing:
        raise RuntimeError(f"missing required measured panels: {missing}")
    if "success" in statuses and "FINAL" not in values:
        raise RuntimeError("success status lacks final-balance panel")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: measure_trainline_loan_20260827.py SEED")
    main(int(sys.argv[1]))
