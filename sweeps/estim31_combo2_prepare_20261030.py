"""Freeze new ESTIM31 AIR x RAIL interaction experiments, without product edits.

Only replace existing coefficients/guards; do not add numeric thresholds.
The published default and historical OFF remain byte-for-byte unchanged.
Refuse overwrites of any immutable experiment bundle.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "results" / "estim31_combo2_20261030"

# (AIR prior, RAIL prior, learned prior weight, V284 start year offset,
#  V284 flow gate, AIR minimum load, V249 statue, EB14 policy).
# All values are pre-existing parameter choices or existing constants.
DESIGNS = {
    "c01_a175_r100_v1": (1.75, 1.00, 15, 1, False, 0, 2, 3),
    "c02_a200_r100_v1_flow": (2.00, 1.00, 15, 1, True, 0, 2, 3),
    "c03_a225_r075_w05_v1_flow": (2.25, 0.75, 5, 1, True, 0, 2, 3),
    "c04_a175_r075_v2_flow_load25": (1.75, 0.75, 15, 2, True, 25, 2, 3),
    "c05_a200_r125_w05_v1_statue0": (2.00, 1.25, 5, 1, False, 0, 0, 3),
    "c06_a225_r100_w05_v2_flow_load25_statue0": (2.25, 1.00, 5, 2, True, 25, 0, 3),
    "c07_a150_r150_v1_flow": (1.50, 1.50, 15, 1, True, 0, 2, 3),
    "c08_a250_r050_v2_flow_statue0": (2.50, 0.50, 15, 2, True, 0, 0, 3),
    "c09_a200_r075_v1_flow": (2.00, 0.75, 15, 1, True, 0, 2, 3),
    "c10_a200_r075_v3_flow": (2.00, 0.75, 15, 3, True, 0, 2, 3),
}

WAIT_OLD = "if (capacity <= 0 || wagon.capacity <= 0 || waiting < wagon.capacity) continue;"
WAIT_NEW = ("if (capacity <= 0 || wagon.capacity <= 0 || (waiting < wagon.capacity "
            "&& !((ESTIM_UNIFIE & 4) != 0 && (\"predCarried\" in line) "
            "&& line.predCarried > wagon.capacity))) continue;")
LIMIT_OLD = "if (atLimit && (waiting < capacity || !OpexRailVehicleSlotAvailable())) continue;"
LIMIT_NEW = ("if (atLimit && ((waiting < capacity && !((ESTIM_UNIFIE & 4) != 0 "
             "&& (\"predCarried\" in line) && line.predCarried > capacity)) "
             "|| !OpexRailVehicleSlotAvailable())) continue;")


def replace_exact(content: str, before: str, after: str, path: str) -> str:
    if content.count(before) != 1:
        raise ValueError(f"Unexpected anchor count {content.count(before)}: {path}: {before}")
    return content.replace(before, after, 1)


def prepare(name: str) -> None:
    air, rail, weight, growth, flow, load, statue, eb14 = DESIGNS[name]
    dst = DEST / name
    if dst.exists():
        raise FileExistsError(f"Frozen candidate exists: {dst}")
    if not (ROOT / "ai" / "OpexAI" / "air_economics_c121_fullscan.nut").is_file():
        raise FileNotFoundError("Published ESTIM31 fullscan source unavailable")
    dst.mkdir(parents=True)
    for directory in ("ai", "ai_libraries", "sweeps"):
        shutil.copytree(ROOT / directory, dst / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # The competitor is an installed, untracked AI. Freeze a copy, without
    # touching the shared original or treating it as a Git-tracked dependency.
    adversary = ROOT.parents[1] / "ai" / "AAAHogEx-115"
    if not (adversary / "info.nut").is_file():
        raise FileNotFoundError(f"Installed adversary absent: {adversary}")
    shutil.copytree(adversary, dst / "ai" / "AAAHogEx-115")
    for filename in ("Dockerfile", "requirements.txt", "requirements-ml.txt"):
        shutil.copy2(ROOT / filename, dst / filename)
    module = dst / "ai/OpexAI/air_economics_c121_fullscan.nut"
    code = module.read_text(encoding="utf8")
    for key, value in (("air", f"{air:.2f}"), ("rail", f"{rail:.2f}")):
        original = "2.00" if key == "air" else "0.75"
        code = replace_exact(code, f"ESTIM_K_R_PRIOR.{key} = {original};",
                             f"ESTIM_K_R_PRIOR.{key} = {value};", str(module))
    code = replace_exact(code, "ESTIM_K_R_PRIOR_WEIGHT = 15.0;",
                         f"ESTIM_K_R_PRIOR_WEIGHT = {weight:.1f};", str(module))
    module.write_text(code, encoding="utf8")
    if flow:
        rail_file = dst / "ai/OpexAI/task_v284.nut"
        code = rail_file.read_text(encoding="utf8")
        code = replace_exact(code, WAIT_OLD, WAIT_NEW, str(rail_file))
        code = replace_exact(code, LIMIT_OLD, LIMIT_NEW, str(rail_file))
        rail_file.write_text(code, encoding="utf8")
    sha = {f.relative_to(dst).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
           for f in (dst / "ai").rglob("*") if f.is_file()}
    manifest = {"name": name, "source_git_commit": "10b5197dda97c991f783841b63b1ac19c83cc5b8",
                "configuration": {"air": air, "rail": rail, "weight": weight,
                                  "v284_rail_growth": growth, "v284_flow_gate": flow,
                                  "air_load_min_pct": load, "v249_statue": statue,
                                  "eb14_progressive": eb14, "estim_unifie": 31, "probes": 2},
                "ai_file_sha256": sha, "changed_from_public": sorted(
                    rel for rel, digest in sha.items()
                    if (ROOT / rel).is_file()
                    and hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest),
                "selection_rule": "ratio_of_means_OpexAI_to_AAAHogEx_115",
                "economic_rejection": "none_for_company_value_pvalue_CI95"}
    (dst / "design.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf8")
    print("FROZEN", name, manifest["changed_from_public"])


if __name__ == "__main__":
    for selected in sys.argv[1:] or DESIGNS:
        prepare(selected)
