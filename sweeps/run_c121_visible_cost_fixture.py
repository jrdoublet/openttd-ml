"""Passive call-body opcode counter on copied AI, no economic verdict."""
import argparse
from pathlib import Path
from .run_c121_visible_newsite_fixture import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--visible", type=int, choices=(0, 1), required=True)
    args = parser.parse_args()
    main(["--out", args.out, "--years", "3"],
         settings=(("c121_air_visible_competition", args.visible), ("decision_log", 1)),
         fixture=Path(__file__).resolve().parents[1] / "tests/mechanisms/c121_visible_cost_vm.nut",
         marker="C121_VISIBLE_COST")
