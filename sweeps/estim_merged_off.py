"""Reviewed source-hunk compatibility for ESTIM-1 on ROAD1Y + RAIL.

The source diff in estim_unifie_off_lots.py, its 29/10 V161 overlays and the
pre-merge SHA witnesses are immutable.  Only explicitly SHA-bound merged
inputs may use these additional exact on/off pairs.  No diff is generated
from current production source at runtime.
"""

import hashlib
import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "estim_merged_20261105.json"

NEW_C121 = (
    '  /* Experiment: leave the historical C121 scanner untouched OFF. */\n'
    '  if ((ESTIM_UNIFIE & 1) != 0) {\n'
    '    require("air_economics_c121_fullscan.nut");\n'
    '    ::OpexC121ChooseRoutePlane <- OpexC121ChooseRoutePlaneFullScan;\n'
    '  }\n'
)

V233_CONSTRUCT = (
    '  V233L_CONSTRUCT = AIController.GetSetting("v233l_constructibilite");\n'
    '  if (V233L_CONSTRUCT == null || V233L_CONSTRUCT < 0 || V233L_CONSTRUCT > 2) V233L_CONSTRUCT = 0;\n'
)

PAX_CAP = (
    '  local paxRatingCap = (ROAD1Y_PAX_ECONOMY && kind == "pax")\n'
    '      ? (ROAD1Y_FLEET > 0 ? (ROAD1Y_FLEET * 2) : 2)\n'
    '      : OpexRoadPhysicalVehicleCap(1, 1);\n'
    '  if (fleetCapOverride > 0 && fleetCapOverride > paxRatingCap) paxRatingCap = fleetCapOverride;\n'
)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fixture():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    from estim_unifie_off_lots import PATCH_TEXT
    if _sha(PATCH_TEXT) != fixture["historical_patch_sha256"]:
        raise AssertionError("ESTIM-1 merged: original 2026-10-29 PATCH_TEXT changed")
    frozen_compat = Path(__file__).parent / "estim_unifie_v161_compat.py"
    if hashlib.sha256(frozen_compat.read_bytes()).hexdigest() != (
            fixture["historical_v161_compat_sha256"]):
        raise AssertionError("ESTIM-1 merged: original V161 overlays changed")
    return fixture


def _exact_replace(text, old, new, name, index):
    if old == new or text.count(old) != 1:
        raise AssertionError(f"ESTIM-1 merged {name} #{index}: nonunique reviewed edit")
    return text.replace(old, new, 1)


def _reviewed_overlay(name, frozen_hunks):
    """Pure reviewed text transformations; no access to production source."""
    overlay = list(frozen_hunks)
    if name == "globals_pre.nut":
        on, old = overlay[0]
        on = _exact_replace(on,
            "ESTIM_K_R_PRIOR <- { rail = 0.92, road = 0.57, air = 0.40, water = 1.0 };",
            "ESTIM_K_R_PRIOR <- { rail = 1.00, road = 0.57, air = 1.50, water = 1.0 };",
            name, 0)
        on = _exact_replace(on, "ESTIM_K_R_PRIOR_WEIGHT <- 10.0;",
                            "ESTIM_K_R_PRIOR_WEIGHT <- 15.0;", name, 0)
        on = _exact_replace(on,
            "ESTIM_K_R <- { rail = 0.92, road = 0.57, air = 0.40, water = 1.0 };",
            "ESTIM_K_R <- { rail = 1.00, road = 0.57, air = 1.50, water = 1.0 };",
            name, 0)
        overlay[0] = on, old
    elif name == "economy.nut":
        on, old = overlay[2]
        before = "if (longModel) calibrationOffered /= 2.0;"
        after = "if (longModel && !monoLong) calibrationOffered /= 2.0;"
        overlay[2] = (_exact_replace(on, before, after, name, 2),
                      _exact_replace(old, before, after, name, 2))

        on, old = overlay[4]
        before = 'local startTrains = (longModel || (OpexV190Active() && kind == "freight")) ? 2 : 1;'
        after = 'local startTrains = (!monoLong && (longModel || (OpexV190Active() && kind == "freight"))) ? 2 : 1;'
        on = _exact_replace(on, before, after, name, 4)
        old = _exact_replace(old, before, after, name, 4)
        on = _exact_replace(on,
            'local maxTrains = (ESTIM_UNIFIE & 8) != 0 ? OpexEstimRailPhysicalTrainCap() : MAX_RAIL_TRAINS;',
            'local maxTrains = monoLong ? 1 : ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimRailPhysicalTrainCap() : MAX_RAIL_TRAINS);',
            name, 4)
        old = _exact_replace(old,
            '  for (local trains = startTrains; trains <= MAX_RAIL_TRAINS; trains++) {',
            '  local maxTrains = monoLong ? 1 : MAX_RAIL_TRAINS;\n'
            '  for (local trains = startTrains; trains <= maxTrains; trains++) {',
            name, 4)
        overlay[4] = on, old

        on, old = overlay[5]
        on = _exact_replace(on, '  local volumeRating = (ESTIM_UNIFIE & 8) != 0\n',
                            PAX_CAP + '  local volumeRating = (ESTIM_UNIFIE & 8) != 0\n',
                            name, 5)
        on = _exact_replace(on,
            '? OpexStationRatingForHeadway(roundTripDays / OpexRoadPhysicalVehicleCap(1, 1))',
            '? OpexStationRatingForHeadway(roundTripDays.tofloat() / paxRatingCap)', name, 5)
        old = _exact_replace(old,
            '  local offered = (monthlyUnits * STATION_RATING_PCT) / 100;',
            PAX_CAP + '  local offered = (monthlyUnits * STATION_RATING_PCT) / 100;', name, 5)
        overlay[5] = on, old
    elif name == "settings.nut":
        on, old = overlay[0]
        anchor = '  V233_SITE_FUNNEL = AIController.GetSetting("v233_site_funnel") == 1 ? 1 : 0;'
        on = _exact_replace(on, anchor, V233_CONSTRUCT + anchor, name, 0)
        old = _exact_replace(old, anchor, V233_CONSTRUCT + anchor, name, 0)
        overlay[0] = on, old
    else:
        raise AssertionError(f"ESTIM-1 merged: unreviewed input {name}")
    return overlay


def merged_hunks(name, source, frozen_hunks):
    """Return the original mapping or one explicitly SHA-authorized overlay."""
    fixture = _fixture()
    case = fixture["files"].get(name)
    if case is None or _sha(source) not in case["allowed_pre_hunks_sha256"]:
        return frozen_hunks
    overlay = _reviewed_overlay(name, frozen_hunks)
    expected = case["hunk_sha256"]
    actual = {
        str(idx): [_sha(pair[0]), _sha(pair[1])]
        for idx, pair in enumerate(overlay) if idx in case["changed_indices"]
    }
    if actual != expected:
        raise AssertionError(f"ESTIM-1 merged {name}: reviewed hunks changed")
    return overlay


def strip_merged_c121(name, source):
    """Invert only the exact new C121 inline dispatch on authorized input SHA."""
    if name != "settings.nut":
        return None
    if NEW_C121 not in source:
        return None
    case = _fixture()["files"]["settings.nut"]["c121"]
    pre = _sha(source)
    if pre not in case["on_sha256"] or source.count(NEW_C121) != 1:
        raise AssertionError("C121 merged dispatch: unreviewed/duplicated source")
    stripped = source.replace(NEW_C121, "", 1)
    if _sha(stripped) != case["on_sha256"][pre]:
        raise AssertionError("C121 merged dispatch: OFF SHA mismatch")
    return stripped
