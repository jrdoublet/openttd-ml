"""Lanceur hote C75 bis : smoke puis duel causal 5x6, protocole C66.4 fixe."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

PROTOCOLS = {
    "smoke": {
        "campaign": "c75_kpass_bypass_smoke3_2x4_20260925",
        "years": 4,
        "seeds": [42, 100],
    },
    "5x6": {
        "campaign": "c75_kpass_bypass_vs_default_5x6_20260925",
        "years": 6,
        "seeds": [42, 100, 999, 1234, 5678],
        "line_telemetry": True,
    },
    "20x10": {
        "campaign": "c75_kpass_bypass_vs_default_20x10_20260925_r2",
        "years": 10,
        "seeds": [
            42, 100, 7, 999, 2026, 1, 17, 73, 314, 512,
            1024, 1337, 4096, 8191, 12345, 54321, 65537,
            123456, 424242, 8675309,
        ],
        "line_telemetry": False,
    },
    "20x10b": {
        "campaign": "c75_kpass_bypass_vs_default_20x10_20260925_r3",
        "years": 10,
        "seeds": [
            20001, 20002, 20003, 20004, 20005, 20006, 20007, 20008, 20009, 20010,
            20011, 20012, 20013, 20014, 20015, 20016, 20017, 20018, 20019, 20020,
        ],
        "line_telemetry": False,
    },
    "40x10": {
        "campaign": "c75_kpass_bypass_vs_default_40x10_20260925_r4",
        "years": 10,
        "seeds": [
            20021, 20022, 20023, 20024, 20025, 20026, 20027, 20028, 20029, 20030,
            20031, 20032, 20033, 20034, 20035, 20036, 20037, 20038, 20039, 20040,
            20041, 20042, 20043, 20044, 20045, 20046, 20047, 20048, 20049, 20050,
            20051, 20052, 20053, 20054, 20055, 20056, 20057, 20058, 20059, 20060,
        ],
        "line_telemetry": False,
    },
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=sorted(PROTOCOLS))
    args = parser.parse_args()
    protocol = PROTOCOLS[args.phase]

    command = [
        sys.executable,
        "-X",
        "utf8",
        str(ROOT / "sweeps" / "run_c66_reference.py"),
        "--campaign",
        protocol["campaign"],
        "--policy-id",
        "c75_bypass0",
        "--reference",
        "OpexAI[c75_kpass_bypass=0]",
        "--variant",
        "OpexAI[c75_kpass_bypass=1]",
        "--variant-policy-id",
        "c75_bypass1",
        "--primary-metric",
        "profit_year",
        "--min-useful-primary-delta",
        "50000",
        "--value-guard-max-loss-pct",
        "5",
        "--years",
        str(protocol["years"]),
        "--seeds",
        *(str(seed) for seed in protocol["seeds"]),
        "--max-workers",
        "10",
        "--cpus",
        "10",
        "--memory",
        "2g",
    ]
    if protocol.get("line_telemetry", True):
        command.append("--line-telemetry")
    completed = subprocess.run(command, cwd=ROOT)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
