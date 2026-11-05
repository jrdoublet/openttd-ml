"""Project reviewed opt-in V233L edits to OFF for immutable legacy contracts.

The fixture records both sides, anchored by surrounding source. A changed
guard must fail rather than silently get erased. This is a source-level
projection; execution timing and VM equivalence still require a real smoke.
"""
import hashlib
import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / "fixtures/v233_long_good_off.json")
                     .read_text(encoding="utf-8"))

# V233L guards were extended by the opt-in constructibility fallback, and its
# setting was inserted between two older V233L settings.  Never alter the
# original 2026-10-27 fixture or treat an arbitrary partial guard as OFF: only
# these reviewed, exact pre-V233L merge sources may use the alternate spans.
# Hashes are taken AFTER the newer policy projectors below, not from the live
# worktree (which can be further pre-projected by a historical test).
_MERGED_PRE_V233_SHA = {
    "builder_rail.nut": {
        "3a9366a7f938bb59c1563e48f1c7f3f311e44913f7234269bf4964308880b73c",
    },
    "economy.nut": {
        "7af7993d86b6f2605072caeebf197a6f73361dad947acf7b0dca81cd8a2aad06",
    },
    "globals_pre.nut": {
        "83eeb53e34010c64d1fdf0026dd5939b09d91d66389f81902de0da6fda80194d",
    },
    "info.nut": {
        "0d8c3fe5d72736df54af53d7a3bfbd87598c8a66b8cfa0ceba16cae7fc92e4f5",
        "5630090c0d7e9ff8cd35e41ec47582744b311704a3eb1f4ee02fac9dca13fd2a",
        # SEARCH-PRIO config OFF is applied first by the frozen V233 witness;
        # record its two independent source stages rather than weakening the
        # historical V233 guard or mutating the original fixture.
        "03ed4993d7efe3e4794f64c2cdd76e0a5494dc276fe4504420eab847fa234349",
        "466aa0eee271d4da237633696d12aa7754880ea47f9abba1ac553a879c7a1665",
    },
    "settings.nut": {
        "75afcaa5c58e82c5f8051161c403f8fcb5c13c37daa170048afde5f601dd24c8",
    },
}

# Full output identities for the same reviewed inputs, after *all* frozen
# V233L edits have been subtracted.  They prevent a coincidentally matching
# local fragment from producing a silently changed historical projection.
# The pre-merge witnesses and hashes in v233_long_good_off.json remain frozen.
_MERGED_V233_PROJECTED_SHA = {
    "builder_rail.nut": {
        "3a9366a7f938bb59c1563e48f1c7f3f311e44913f7234269bf4964308880b73c":
            "b73636334bfb6b3537e335644ec0d355910dbf1fba1be0063b645a8d74c6b452",
    },
    "economy.nut": {
        "7af7993d86b6f2605072caeebf197a6f73361dad947acf7b0dca81cd8a2aad06":
            "a5e75086c455d9b6102a5fc8f2aa0a1210e0b6ec8968314eda191c174e71262c",
    },
    "globals_pre.nut": {
        "83eeb53e34010c64d1fdf0026dd5939b09d91d66389f81902de0da6fda80194d":
            "320007389a5997fc5d8c52ba06b40966d98644844b27703fd47adb96988df0a0",
    },
    "info.nut": {
        "0d8c3fe5d72736df54af53d7a3bfbd87598c8a66b8cfa0ceba16cae7fc92e4f5":
            "f28a4896bcbcd2140a50710032c70fb689af16f0c18c914f29288d14ecaaeaa0",
        "5630090c0d7e9ff8cd35e41ec47582744b311704a3eb1f4ee02fac9dca13fd2a":
            "03b57d0237ee4aaac31e94eb6e4df824042ae126824d9560c70a530c20e4adac",
        "03ed4993d7efe3e4794f64c2cdd76e0a5494dc276fe4504420eab847fa234349":
            "c669d27ea7bfdbaa7fb940a98cdac828b2680ecc6880242184bb6c3b3eb1277d",
        "466aa0eee271d4da237633696d12aa7754880ea47f9abba1ac553a879c7a1665":
            "6fcb3f8e5f33ff8e7be0c5d657de655a051e05fafdfdef44db5c680a8e4907a1",
    },
    "settings.nut": {
        "75afcaa5c58e82c5f8051161c403f8fcb5c13c37daa170048afde5f601dd24c8":
            "f8359098b70e994d4dcafcf037c0c06bfec9c3eccdb323d79fdb14ceae7e7f2f",
    },
}


def _reviewed_merge_guard(name, code, index):
    """Return an exact, unique reviewed replacement span, or fail closed."""
    anchors = {
        ("builder_rail.nut", 42): (
            "  if (OpexV233LIs(candidate) && plan.doubleTrack != 1) {\n",
            "  plan.ok = true;\n",
        ),
        ("builder_rail.nut", 48): (
            "  if (OpexV233LIs(candidate) && !OpexV233LRecheck(candidate, plan)) {\n",
            "  local replanGeometry = false;\n",
        ),
        ("builder_rail.nut", 58): (
            "  if (OpexV233LIs(candidate) && !okD && !OpexV233LMonoAllowed(candidate, plan)) {\n",
            "  local started = [];\n",
        ),
        ("economy.nut", 0): (
            "                           wagonOverride = null, locoChoicesOverride = null, secondary = null,\n"
            "                           longGood = false, v233Single = false)\n",
            None,
        ),
        ("economy.nut", 3): (
            "  if (longModel && !monoLong) calibrationOffered /= 2.0; // deux rames partageant le debit observe.\n",
            None,
        ),
        ("economy.nut", 4): (
            '  } else if ((longModel && !monoLong) || (OpexV190Active() && kind == "freight" && !monoLong)) {\n',
            None,
        ),
        ("economy.nut", 5): (
            '  local startTrains = (!monoLong && (longModel || (OpexV190Active() && kind == "freight"))) ? 2 : 1;\n',
            None,
        ),
        ("globals_pre.nut", 0): (
            "V233_LONG_GOOD <- 1; // Defaut 1 depuis le 27/10 (decision utilisateur).\n"
            "V233L_CONSTRUCT <- 0; // 0 historique, 1 devis monovoie passif, 2 repli monovoie physique opt-in.\n"
            "V233L_STATE <- null; // Fenetres mensuelles entieres, sauvegardees seulement sous l'option.\n"
            "V233_SITE_FUNNEL <- 1; // 0 = spirale B urbaine ; 1 = entonnoir natif (defaut 1 depuis le 27/10).\n"
            "V233_FUNNEL_CENTER_TEST <- 1; // 0 = off ; 1 = pre-test d'acceptation au centre de la ville.\n",
            None,
        ),
        ("info.nut", 0): (
            "    });\n\n    AddSetting({\n      name = \"v233_long_good\",\n",
            "    AddSetting({\n      name = \"v284_rail_growth\",\n",
        ),
        ("settings.nut", 0): (
            '  V233_LONG_GOOD = AIController.GetSetting("v233_long_good") == 1 ? 1 : 0;\n'
            '  V233L_CONSTRUCT = AIController.GetSetting("v233l_constructibilite");\n'
            '  if (V233L_CONSTRUCT == null || V233L_CONSTRUCT < 0 || V233L_CONSTRUCT > 2) V233L_CONSTRUCT = 0;\n'
            '  V233_SITE_FUNNEL = AIController.GetSetting("v233_site_funnel") == 1 ? 1 : 0;\n'
            '  V233_FUNNEL_CENTER_TEST = AIController.GetSetting("v233_funnel_center_test") == 0 ? 0 : 1;\n',
            None,
        ),
    }
    start, end = anchors[(name, index)]
    if code.count(start) != 1:
        raise AssertionError(f"V233L {name}: merged guard anchors modified")
    if end is None:
        return start
    a = code.index(start)
    b = code.find(end, a + len(start))
    if b < 0 or b - a > 3000:
        raise AssertionError(f"V233L {name}: merged guard scope changed")
    fragment = code[a:b]
    # No unrelated feature may be erased: these are all V233L guards/settings.
    if name == "info.nut" and not all(
        marker in fragment for marker in (
            'name = "v233_long_good"', 'name = "v233l_constructibilite"',
            'name = "v233_site_funnel"', 'name = "v233_funnel_center_test"',
        )
    ):
        raise AssertionError("V233L info.nut: merged settings changed")
    return fragment


def off_source(name, code):
    from fleet_arb_off import off_source as fleet_off
    code = fleet_off(name, code)
    from double_grow_off import off_source as double_grow_off
    code = double_grow_off(name, code)
    if name in ("globals_pre.nut", "settings.nut", "info.nut", "main.nut", "scheduler.nut", "persist.nut",
                "task_rail.nut", "orchestrator.nut", "candidates.nut", "po01c_generators.nut",
                "lines.nut", "builder_rail.nut", "task_v284.nut") and (
        "INVEST_STALL" in code or "invest_stall" in code or "investStall" in code
    ):
        from invest_stall_source_off import project_off as invest_stall_off
        code = invest_stall_off(name, code)
    from rail_long_source_off import off_source as rail_long_off
    code = rail_long_off(name, code)
    from rail_sibling_legacy import off_source as sibling_off
    code = sibling_off(name, code)
    from estim_unifie_legacy import estim_off
    code = estim_off(name, code)
    from air_site_probe_legacy import off_source as air_probe_off
    code = air_probe_off(name, code)
    entry = FIXTURE["files"].get(name)
    if entry is None:
        return code
    merge_sha = hashlib.sha256(code.encode("utf-8")).hexdigest()
    merge_reviewed = merge_sha in _MERGED_PRE_V233_SHA.get(name, ())
    if merge_reviewed and name == "economy.nut":
        # The mono-rail opt-in added two independent lines outside the legacy
        # V233L hunks. The V233L OFF model must restore the original train cap
        # and remove the local before erasing its v233Single parameter.
        for guarded, off in (
            ("  local monoLong = longModel && v233Single && V233L_CONSTRUCT > 0;\n", ""),
            ("  local maxTrains = monoLong ? 1 : MAX_RAIL_TRAINS;\n",
             "  local maxTrains = MAX_RAIL_TRAINS;\n"),
        ):
            if code.count(guarded) != 1:
                raise AssertionError("V233L economy.nut: merged mono-rail guard modified")
            code = code.replace(guarded, off, 1)
    for index in range(len(entry["edits"]) - 1, -1, -1):
        edit = entry["edits"][index]
        guarded = edit["guarded"]
        # The frozen V233L fixture predates permanent cash-reserve removal.
        # Its V233L dispatch is still exact once the obsolete argument is dropped.
        if (name == "builder_rail.nut" and guarded ==
                "  if (OpexV233LIs(candidate)) return OpexV190ExecuteRailPlan(catalog, budget, candidate, plan, cashReserve);\n"):
            guarded = "  if (OpexV233LIs(candidate)) return OpexV190ExecuteRailPlan(catalog, budget, candidate, plan);\n"
        if merge_reviewed and (name, index) in (
            ("builder_rail.nut", 42), ("builder_rail.nut", 48),
            ("builder_rail.nut", 58), ("economy.nut", 0),
            ("economy.nut", 3), ("economy.nut", 4), ("economy.nut", 5),
            ("globals_pre.nut", 0), ("info.nut", 0),
            ("settings.nut", 0),
        ):
            guarded = _reviewed_merge_guard(name, code, index)
        assert code.count(guarded) == 1, f"V233L {name}: guarded hunk changed"
        code = code.replace(guarded, edit["off"], 1)
    if merge_reviewed:
        expected = _MERGED_V233_PROJECTED_SHA[name][merge_sha]
        if hashlib.sha256(code.encode("utf-8")).hexdigest() != expected:
            raise AssertionError(f"V233L {name}: reviewed merge OFF SHA mismatch")
    return code


def off_bytes(name, code):
    return off_source(name, code.decode("utf-8")).encode("utf-8")
