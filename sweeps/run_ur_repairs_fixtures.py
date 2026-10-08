"""UR-15a/16b directed NoAI checks using the existing Save/Load fixture driver."""
from pathlib import Path
import re

from .run_c121_target_limit_fixtures import main as run_fixture
from .test_rail_track_failure_capture import function_body, digest, PRE_EXTRACTION_HASHES
from .test_generation_stage_month import readers
from .run_mechanism_fixtures import tree_hashes

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/mechanisms/ur_repairs_vm.nut"


def transform(target):
    before = (ROOT / "ai/OpexAI/builder_rail.nut").read_text(encoding="utf-8")
    helper = function_body(before, "OpexRailCaptureTrackFailure")
    legacy = function_body(before, "OpexBuildTrack")
    for kind in ('"connect"', "segmentKind"):
        call = ("OpexRailCaptureTrackFailure(failure, tiles, i, cur, " + kind
                + ", err, manhPrev, manhNext);")
        assert legacy.count(call) == 1
        legacy = legacy.replace(call, helper.replace("failure.kind <- kind;",
                                                    "failure.kind <- " + kind + ";"))
    assert digest(legacy) == PRE_EXTRACTION_HASHES["OpexBuildTrack"]
    builder = target / "builder_rail.nut"
    builder.write_text(builder.read_text(encoding="utf-8")
                       + "\nfunction FxURLegacy(tiles, structures = null, failure = null)\n{"
                       + legacy + "}\n", encoding="utf-8")
    functions = []
    for index, (_, expression) in enumerate(readers()):
        expression = re.sub(r"(?:owner|this)\._generationStageMonth", "stamp", expression)
        functions.append(f"function FxURYear{index}(stamp) {{ return {expression}; }}")
    assert len(functions) == 5
    fixture = target / FIXTURE.name
    fixture.write_text(fixture.read_text(encoding="utf-8") + "\n" + "\n".join(functions),
                       encoding="utf-8")


if __name__ == "__main__":
    original = tree_hashes(ROOT / "ai/OpexAI")
    try:
        run_fixture(settings=(("decision_log", 1),), fixture=FIXTURE,
                    marker="UR_REPAIRS", stage_transform=transform)
    finally:
        if original != tree_hashes(ROOT / "ai/OpexAI"):
            raise RuntimeError("Production AI changed during fixture execution")
