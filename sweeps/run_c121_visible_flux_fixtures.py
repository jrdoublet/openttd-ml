"""Real VM and Save/Load checks using the existing diagnostic driver."""
from pathlib import Path
from .run_c121_target_limit_fixtures import main

if __name__ == "__main__":
    main(settings=(("c121_air_visible_competition", 1), ("decision_log", 1)),
         fixture=Path(__file__).resolve().parents[1] / "tests/mechanisms/c121_visible_flux_vm.nut",
         marker="C121_VISIBLE")
