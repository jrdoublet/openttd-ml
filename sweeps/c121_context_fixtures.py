"""Copy-only context fixture and reader; used by the existing integration driver."""
from pathlib import Path
import re
import shutil
from .run_mechanism_fixtures import replace_once
from .run_c121_winner_fixtures import markers as winner_markers

ROOT = Path(__file__).resolve().parents[1]


def stage_context(folder):
    target = folder / "ai/OpexAI"
    shutil.copytree(ROOT / "ai/OpexAI", target)
    text = (ROOT / "tests/mechanisms/c121_winner_vm.nut").read_text(encoding="utf-8")
    text = replace_once(text, "foreach (cap in [1, 2, 4])", "foreach (cap in [1, 6, 13])")
    (target / "c121_winner_vm.nut").write_text(text, encoding="utf-8")
    shutil.copy2(ROOT / "tests/mechanisms/c121_context_vm.nut", target)
    main = target / "main.nut"
    text = replace_once(main.read_text(encoding="utf-8"), "function OpexAI::Start()",
        'require("c121_winner_vm.nut");\nrequire("c121_context_vm.nut");\n\nfunction OpexAI::Start()')
    text = replace_once(text, "  OpexLoadSettings();", "  OpexLoadSettings();\n  FxCtxStart(this);")
    main.write_text(text, encoding="utf-8")
    return target


def markers(log):
    matrix = winner_markers(log)["matrix"]
    live = [dict(arm=a, checked=int(c), old_ops=int(o), new_ops=int(n))
            for a, c, o, n in re.findall(r"C121_CONTEXT_LIVE arm=(\w+) checked=(\d+) old_ops=(\d+) new_ops=(\d+) pass=1", log)]
    checked = [x for x in live if x["checked"]]
    domain = {(cap, mail, mode, aaa) for cap in (1, 6, 13) for mail in range(3) for mode in range(4) for aaa in range(2)}
    checks = {"context_start": "C121_CONTEXT_START fusion=1 witness=0 pass=1" in log,
              "context_guards": "C121_CONTEXT_GUARDS checks=12 reused=1 restored=1 pass=1" in log,
              "matrix_domain": {(r["cap"], r["mail"], r["mode"], r["aaa"]) for r in matrix} == domain,
              "matrix_complete": [r["case"] for r in matrix] == list(range(1, 73)),
              "matrix_stable": bool(matrix) and all(r["stable"] for r in matrix),
              "matrix_restored": "C121_WINNER_VM complete=1 cases=72 restored=1" in log,
              "natural_exposure": bool(checked), "no_fixture_assertion": "C121_WINNER_ASSERT" not in log}
    return {"checks": checks, "matrix": matrix, "live": live, "checked_count": len(checked),
            "old_ops": sum(r["old_ops"] for r in checked), "new_ops": sum(r["new_ops"] for r in checked)}
