"""C65 : deplacement pur des fonctions de main.nut vers des modules par famille.

Passe 1 de docs/taches.md C65. Aucune globale, aucune const, aucun corps n'est retouche.
La preuve est mecanique : extraire chaque bloc ^function, trier, comparer -- diff vide
hors lignes require. Start() reste dans main.nut.

  python3 sweeps/c65_split_main.py --selftest
  python3 sweeps/c65_split_main.py --apply
  python3 sweeps/c65_split_main.py --prove
  python3 sweeps/c65_split_main.py --compare-runs old.json new.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "ai" / "OpexAI"
MAIN_PATH = AI_DIR / "main.nut"
KEEP_IN_MAIN = {"OpexAI::Start"}
# Passe 3 reecrit ces deux dispatchers (appels vers handlers extraits).
SKIP_BODY_COMPARE = KEEP_IN_MAIN | {
    "OpexAI::_processEvents",
    "OpexAI::_runNextTask",
}
MAX_MAIN_LINES = 1600
FILE_HEADER = (
    "/* C65 : deplace depuis main.nut "
    "(passe 1, deplacement pur, aucun corps retouche). */\n"
)
REQUIRE_MARKER = "/* C65 : modules extraits de main.nut, requis APRES la classe OpexAI. */"

# Ordre alphabetique par famille, comme la fiche.
MODULE_ORDER = (
    "capital.nut",
    "events.nut",
    "ledgers.nut",
    "lines.nut",
    "persist.nut",
    "probes.nut",
    "scheduler.nut",
    "task_air.nut",
    "task_projects.nut",
    "task_rail.nut",
    "task_report.nut",
    "task_road.nut",
    "task_town.nut",
    "task_water.nut",
)

# Attribution explicite, une entree par fonction deplacee. Start n'y figure pas.
FUNCTION_MODULE = {}


def _assign(module, names):
    for name in names:
        if name in FUNCTION_MODULE:
            raise ValueError(f"fonction assignee deux fois: {name}")
        FUNCTION_MODULE[name] = module


_assign("probes.nut", (
    "OpexC50ResetNonExpansionLedger",
    "OpexSign",
    "OpexDecide",
    "OpexC39Log",
    "OpexC41SchedulerLog",
    "OpexC41RailSliceLog",
    "OpexC49ScarcityLog",
    "OpexC50ChronologyLog",
    "OpexC50LogCashRefusal",
    "OpexC55OriginRelaxLog",
    "OpexC55PaxTraceLog",
    "OpexC56TaskLog",
    "OpexC52AutoreplaceLog",
    "OpexC52EventExposureLog",
    "OpexC55OriginRelaxObserve",
    "OpexC55PaxTraceObserveRevalidated",
    "OpexC55PaxTraceObserveSpared",
    "OpexC55PaxTraceObserveAttempted",
    "OpexC55PaxTraceObservePrecheckOk",
    "OpexC55PaxTraceObserveFinanceable",
    "OpexC55PaxTraceObservePlanned",
    "OpexC55PaxTraceObserveViable",
    "OpexC55PaxTraceObserveBuilt",
    "OpexC49VehicleType",
    "OpexC49IsMapFailure",
    "OpexC41RailCashReleaseLog",
    "OpexC41RailDominationLog",
    "OpexC41ProjectsFallthroughLog",
    "OpexC39ProjectsCadenceLog",
    "OpexC39PassClockLog",
    "OpexC41StalenessLog",
    "OpexC41MicrotaskOpsHint",
    "OpexC41VehicleLostLog",
    "OpexC41RailLostLog",
    "OpexC54VehicleOrdersLog",
    "OpexC41RailLostTopologyLog",
    "OpexC41RailLostPhysicalLog",
    "OpexC41RailSignalRepairLog",
    "OpexC41RailLostConnectivityLog",
    "OpexC41RailJunctionRepairLog",
    "OpexC39ProjectSignature",
    "OpexC41RevisionSnapshot",
    "OpexC39CatalogUsesEngine",
    "OpexC39AirEngineReason",
    "OpexCashReserveProbeLog",
    "OpexPortfolioRefreshProbeLog",
))
_assign("task_rail.nut", (
    "OpexC41RailApproachLead",
    "OpexC41RailApproachFacts",
    "OpexC41BuildPbsAtApproach",
    "OpexC41RailDepotFrontFacts",
    "OpexC41RailLocalLinks",
    "OpexC41RepairJunction",
    "OpexAI::_tryBuildRailProject",
    "OpexAI::_expandRailLines",
    "OpexAI::_continueRailExpansion",
    "OpexAI::_startRailSearch",
    "OpexAI::_continueRailSearch",
    "OpexAI::_consumeRailSearch",
    "OpexAI::_recordRailAttempt",
    "OpexAI::_startRailUpgradeSearch",
    "OpexAI::_consumeRailUpgrade",
))
_assign("lines.nut", (
    "OpexC41PersistedLineForVehicle",
    "OpexAttemptReasonCode",
    "OpexBuildFailureIsAbandonable",
    "OpexVehicleServesStation",
    "OpexLineVehicleIds",
    "OpexFindLineForVehicle",
    "OpexMedianInt",
    "OpexLineVehicleType",
    "OpexLineStationId",
    "OpexRememberClosest",
    "OpexJoinCompatible",
    "OpexFindStationJoin",
    "OpexAbandonedPairKey",
    "OpexAI::_markPairAbandoned",
    "OpexAI::_pruneAbandonedPairs",
    "OpexAI::_findLineById",
    "OpexAI::_tooClose",
))
_assign("capital.nut", (
    "OpexCashReserve",
    "OpexAvailableCapital",
    "OpexTryReborrow",
    "OpexAI::_tryRepayLoan",
))
_assign("task_air.nut", (
    "OpexAI::_markAirFailedSites",
    "OpexAI::_tryBuildAir",
    "OpexAirBatchSiteStillBuildable",
    "OpexAirBatchHubHasCapacity",
    "OpexAirBatchPlanStillLive",
    "OpexAI::_tryBuildAirProject",
    "OpexAirFleetRefusal",
    "OpexAirFleetYield",
    "OpexAirFleetPriorityCompare",
    "OpexAI::_resizeAirFleets",
))
_assign("task_town.nut", (
    "OpexCountTownStations",
    "OpexGetServedTowns",
    "OpexAI::_tryTownGrowth",
))
_assign("task_water.nut", (
    "OpexWaterBatchSiteStillBuildable",
    "OpexAI::_tryBuildWaterProject",
    "OpexAI::_refleetCrashedWaterLines",
))
_assign("task_road.nut", (
    "OpexAI::_tryBuildRoadProject",
    "OpexAI::_refleetRoadLines",
))
_assign("task_projects.nut", (
    "OpexAI::_purgeSubsidyFromProjects",
    "OpexAI::_tryBuildFleetProject",
    "OpexAI::_refreshDynamicBatch",
    "OpexAI::_dynamicBatchBuilt",
    "OpexAI::_dynamicBatchRejected",
    "OpexAI::_stopDynamicBatch",
    "OpexAI::_c39StampFinanceable",
    "OpexAI::_tryBuildProjects",
    "OpexAI::_rebuildProjects",
))
_assign("task_report.nut", (
    "OpexAI::_reportLines",
    "OpexAI::_reportYear",
    "OpexAI::_triggerScrapLine",
    "OpexAI::_scrapDeadLines",
    "OpexAI::_scrapRetiredVehicles",
    "OpexAI::_purgeUnprofitableStreaks",
))
_assign("events.nut", (
    "OpexC52EventExposureObserve",
    "OpexAI::_processEvents",
    "OpexAI::_markDirty",
    "OpexAI::_logStalenessRefresh",
))
_assign("scheduler.nut", (
    "OpexAI::_runNextTaskWithSlackLedger",
    "OpexAI::_runNextTask",
))
_assign("persist.nut", (
    "OpexAI::Save",
    "OpexAI::Load",
    "OpexAI::_reconcileAfterLoad",
))
_assign("ledgers.nut", (
    "OpexAI::_logC41MonthlyBusyLedger",
    "OpexAI::_logC41SlackLedger",
    "OpexAI::_recordC41StaleOpportunity",
    "OpexAI::_logC41AdmissionLedger",
    "OpexAI::_logC41OpportunityLedger",
    "OpexAI::_recordC41RailSliceLedger",
    "OpexAI::_logC41RailSliceLedger",
    "OpexAI::_recordC39PassClockLedger",
    "OpexAI::_logC39PassClockLedger",
    "OpexAI::_recordC49ScarcityPass",
    "OpexAI::_logC49ScarcityLedger",
    "OpexAI::_checkC50MonthlyTreasury",
    "OpexAI::_logC50AnnualReport",
    "OpexAI::_logC50CashRefusal",
    "OpexAI::_logC55OriginRelaxLedger",
    "OpexAI::_logC55PaxTraceLedger",
    "OpexAI::_logC60TownRatingLedger",
    "OpexAI::_logC52AutoreplaceLedger",
    "OpexC52EventExposureFields",
    "OpexAI::_logC52EventExposureLedger",
    "OpexAI::_logC54VehicleOrders",
))

FUNC_HEAD_RE = re.compile(
    r"^function\s+((?:OpexAI::)?[A-Za-z_][A-Za-z0-9_]*)",
    re.M,
)


def skip_string_or_comment(text, i):
    n = len(text)
    if i < n and text[i] == '"':
        i += 1
        while i < n:
            if text[i] == "\\":
                i += 2
                continue
            if text[i] == '"':
                return i + 1
            i += 1
        return i
    if i + 1 < n and text[i:i + 2] == "//":
        j = text.find("\n", i)
        return n if j < 0 else j
    if i + 1 < n and text[i:i + 2] == "/*":
        j = text.find("*/", i + 2)
        if j < 0:
            raise ValueError("commentaire bloc non ferme")
        return j + 2
    return None


def find_matching_brace(text, open_pos):
    i = open_pos + 1
    depth = 1
    n = len(text)
    while i < n:
        skipped = skip_string_or_comment(text, i)
        if skipped is not None:
            i = skipped
            continue
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("accolades non equilibrees")


def _is_comment_line(line):
    stripped = line.strip()
    if stripped == "":
        return True
    return (
        stripped.startswith("//")
        or stripped.startswith("/*")
        or stripped.startswith("*")
        or stripped.endswith("*/")
    )


def leading_comment_start(text, func_start):
    """Bloc de commentaires contigu immediatement au-dessus de la fonction.

    Les globales et les const au-dessus ne sont jamais emportees. Un bloc
    sans aucune ligne de commentaire n'est pas pris (les blancs restent).
    """
    before = text[:func_start]
    if not before:
        return func_start
    lines = before.splitlines(keepends=True)
    idx = len(lines)
    while idx > 0 and lines[idx - 1].strip() == "":
        idx -= 1
    cursor = idx
    saw_comment = False
    while cursor > 0:
        stripped = lines[cursor - 1].strip()
        if stripped == "":
            cursor -= 1
            continue
        if stripped.startswith("//") or stripped.startswith("/*") \
                or stripped.startswith("*") or stripped.endswith("*/"):
            saw_comment = True
            cursor -= 1
            continue
        break
    if not saw_comment:
        return func_start
    while cursor < idx and lines[cursor].strip() == "":
        cursor += 1
    start = sum(len(line) for line in lines[:cursor])
    attached = text[start:func_start]
    if re.search(r"^[A-Za-z_].*<-", attached, re.M):
        raise ValueError("commentaire de tete emporterait une globale")
    if re.search(r"^const ", attached, re.M):
        raise ValueError("commentaire de tete emporterait une const")
    if re.search(r"^require\(", attached, re.M):
        raise ValueError("commentaire de tete emporterait un require")
    return start


def extract_functions(text):
    """Liste de dicts : name, lead, start, end, body, attached.

    body = texte exact de `function` jusqu'a `}` fermante compris.
    lead = debut du commentaire de tete (ou start si aucun).
    """
    found = []
    for match in FUNC_HEAD_RE.finditer(text):
        name = match.group(1)
        cursor = match.end()
        n = len(text)
        brace = None
        while cursor < n:
            skipped = skip_string_or_comment(text, cursor)
            if skipped is not None:
                cursor = skipped
                continue
            if text[cursor] == "{":
                brace = cursor
                break
            cursor += 1
        if brace is None:
            raise ValueError(f"pas d'accolade ouvrante pour {name}")
        end = find_matching_brace(text, brace) + 1
        start = match.start()
        lead = leading_comment_start(text, start)
        found.append({
            "name": name,
            "lead": lead,
            "start": start,
            "end": end,
            "body": text[start:end],
            "attached": text[lead:start],
        })
    return found


def function_bodies_by_name(text):
    return {item["name"]: item["body"] for item in extract_functions(text)}


def load_baseline_main():
    """main.nut d'origine : HEAD git, independant du working tree deja decoupe."""
    return subprocess.check_output(
        ["git", "show", "HEAD:ai/OpexAI/main.nut"],
        cwd=str(ROOT),
        text=True,
    )


def collect_split_bodies(main_text, extra_files):
    bodies = function_bodies_by_name(main_text)
    for path in extra_files:
        if not path.exists():
            continue
        for name, body in function_bodies_by_name(path.read_text()).items():
            if name in bodies:
                raise ValueError(f"{name} presente dans main.nut ET {path.name}")
            bodies[name] = body
    return bodies


def prove(baseline_text, split_main_text, extra_files):
    """Compare les corps de fonctions, tries par nom. Diff vide = succes."""
    old = function_bodies_by_name(baseline_text)
    new = collect_split_bodies(split_main_text, extra_files)
    # Start() peut changer en passe 2 (lecture des reglages extraite). Les 160
    # corps deplaces, eux, doivent rester bit-identiques.
    for skip in SKIP_BODY_COMPARE:
        old.pop(skip, None)
        new.pop(skip, None)
    old_names = set(old)
    new_names = set(new)
    missing = sorted(old_names - new_names)
    extra = sorted(new_names - old_names)
    differed = sorted(
        name for name in sorted(old_names & new_names) if old[name] != new[name]
    )
    return {
        "old_count": len(old),
        "new_count": len(new),
        "missing": missing,
        "extra": extra,
        "differed": differed,
        "ok": not missing and not extra and not differed,
    }


def module_files_on_disk():
    return [AI_DIR / name for name in MODULE_ORDER]


def squeeze_blank_lines(text):
    return re.sub(r"\n{3,}", "\n\n", text)


def find_class_close(text):
    match = re.search(r"^class OpexAI extends AIController\s*\{", text, re.M)
    if not match:
        raise ValueError("classe OpexAI introuvable")
    brace = text.find("{", match.start())
    close = find_matching_brace(text, brace)
    return match.start(), close


def require_block(modules):
    lines = [REQUIRE_MARKER]
    for name in MODULE_ORDER:
        if name in modules:
            lines.append(f'require("{name}");')
    return "\n".join(lines) + "\n"


def split_source(main_text, only_modules=None):
    """Retourne (nouveau main, {module: contenu}) sans ecrire le disque."""
    functions = extract_functions(main_text)
    names = [item["name"] for item in functions]
    if len(names) != len(set(names)):
        raise ValueError("fonctions en double")

    unknown = [
        item["name"] for item in functions
        if item["name"] not in KEEP_IN_MAIN and item["name"] not in FUNCTION_MODULE
    ]
    if unknown:
        raise ValueError("fonctions non assignees: " + ", ".join(unknown))

    moved = []
    for item in functions:
        if item["name"] in KEEP_IN_MAIN:
            continue
        module = FUNCTION_MODULE[item["name"]]
        if only_modules is not None and module not in only_modules:
            continue
        moved.append((module, item))

    by_module = {name: [] for name in MODULE_ORDER}
    for module, item in moved:
        by_module[module].append(item)

    files = {}
    for module in MODULE_ORDER:
        items = by_module[module]
        if not items:
            continue
        chunks = [FILE_HEADER]
        for item in items:
            attached = item["attached"].lstrip("\n")
            piece = attached + item["body"]
            chunks.append(piece if piece.endswith("\n") else piece + "\n")
        body = "\n".join(chunk.rstrip("\n") for chunk in chunks) + "\n"
        files[module] = body

    spans = [(item["lead"], item["end"]) for _, item in moved]
    spans.sort()
    pieces = []
    last = 0
    for lead, end in spans:
        if lead < last:
            raise ValueError("chevauchement de fonctions a extraire")
        pieces.append(main_text[last:lead])
        last = end
    pieces.append(main_text[last:])
    new_main = squeeze_blank_lines("".join(pieces))
    if not new_main.endswith("\n"):
        new_main += "\n"

    _, class_close = find_class_close(new_main)
    insert_at = class_close + 1
    if insert_at < len(new_main) and new_main[insert_at] == "\n":
        insert_at += 1
    existing = set()
    for match in re.finditer(r'^require\("([^"]+)"\);', new_main, re.M):
        existing.add(match.group(1))
    # Retirer un ancien bloc C65 avant d'en reinserer un complet.
    new_main = re.sub(
        r"\n?" + re.escape(REQUIRE_MARKER) + r"\n(?:require\(\"[^\"]+\"\);\n)+",
        "\n",
        new_main,
        count=1,
    )
    _, class_close = find_class_close(new_main)
    insert_at = class_close + 1
    if insert_at < len(new_main) and new_main[insert_at] == "\n":
        insert_at += 1
    modules_present = set(files)
    for name in MODULE_ORDER:
        path = AI_DIR / name
        if path.exists() and name not in files:
            modules_present.add(name)
    block = require_block(modules_present)
    new_main = new_main[:insert_at] + "\n" + block + "\n" + new_main[insert_at:]
    new_main = squeeze_blank_lines(new_main)
    if not new_main.endswith("\n"):
        new_main += "\n"
    return new_main, files


def line_count(text):
    if not text:
        return 0
    return text.count("\n") if text.endswith("\n") else text.count("\n") + 1


def apply_split(only_modules=None):
    original = MAIN_PATH.read_text()
    new_main, files = split_source(original, only_modules=only_modules)
    for name, content in files.items():
        (AI_DIR / name).write_text(content)
    MAIN_PATH.write_text(new_main)
    return new_main, files


def remaining_functions(text):
    return [item["name"] for item in extract_functions(text)]


def run_selftest():
    # Toujours l'arbre d'origine : apres --apply, main.nut du working tree n'a plus que Start().
    baseline = load_baseline_main()
    functions = extract_functions(baseline)
    assert len(functions) == 161, len(functions)
    names = [item["name"] for item in functions]
    assert len(set(names)) == 161
    assert names[-1] == "OpexAI::Start"
    mapped = set(FUNCTION_MODULE)
    assert mapped == (set(names) - KEEP_IN_MAIN), (
        "mapping != fonctions: missing "
        + str(sorted((set(names) - KEEP_IN_MAIN) - mapped))
        + " extra "
        + str(sorted(mapped - (set(names) - KEEP_IN_MAIN)))
    )
    for item in functions:
        assert item["body"].startswith("function ")
        assert item["body"].rstrip().endswith("}")
        i = item["body"].find("{")
        close = find_matching_brace(item["body"], i)
        assert close == len(item["body"].rstrip("\n")) - 1 or item["body"][close] == "}"

    identity = prove(baseline, baseline, [])
    assert identity["ok"], identity

    current = MAIN_PATH.read_text()
    already_split = (
        remaining_functions(current) == ["OpexAI::Start"]
        and REQUIRE_MARKER in current
    )
    if already_split:
        extra = [AI_DIR / name for name in MODULE_ORDER if (AI_DIR / name).exists()]
        assert len(extra) == len(MODULE_ORDER), [p.name for p in extra]
        report = prove(baseline, current, extra)
        assert report["ok"], report
        n_lines = line_count(current)
        assert n_lines <= MAX_MAIN_LINES, n_lines
        class_at, _ = find_class_close(current)
        hist = current.find('require("budget.nut");')
        assert 0 <= hist < class_at
        assert current.find(REQUIRE_MARKER) > class_at
        print(
            f"selftest ok (arbre deja decoupe): 161 fonctions, "
            f"{len(MODULE_ORDER)} modules, main.nut {n_lines} lignes, preuve vide"
        )
        return

    new_main, files = split_source(current)
    assert set(files) == set(MODULE_ORDER), set(MODULE_ORDER) - set(files)
    leftover = remaining_functions(new_main)
    assert leftover == ["OpexAI::Start"], leftover
    assert "class OpexAI extends AIController" in new_main
    assert "constructor()" in new_main
    assert REQUIRE_MARKER in new_main
    for name in MODULE_ORDER:
        assert f'require("{name}");' in new_main
    class_at, _ = find_class_close(new_main)
    hist = new_main.find('require("budget.nut");')
    assert 0 <= hist < class_at
    assert new_main.find(REQUIRE_MARKER) > class_at
    for name, content in files.items():
        assert "\nconst " not in "\n" + content, name
        assert not re.search(r"^[A-Z0-9_]+ <-", content, re.M), name
    mem_files = [_MemFile(name, content) for name, content in files.items()]
    report = prove(baseline, new_main, mem_files)
    assert report["ok"], report
    n_lines = line_count(new_main)
    assert n_lines <= MAX_MAIN_LINES, n_lines
    for item in extract_functions(new_main):
        assert "require(" not in item["body"]
    print(
        f"selftest ok: 161 fonctions, {len(files)} modules, "
        f"main.nut -> {n_lines} lignes, preuve vide"
    )


def print_prove(report):
    print(
        f"preuve: old={report['old_count']} new={report['new_count']} "
        f"missing={len(report['missing'])} extra={len(report['extra'])} "
        f"differed={len(report['differed'])}"
    )
    if report["missing"]:
        print("  missing:", ", ".join(report["missing"][:20]))
    if report["extra"]:
        print("  extra:", ", ".join(report["extra"][:20]))
    if report["differed"]:
        print("  differed:", ", ".join(report["differed"][:20]))
    print("OK" if report["ok"] else "FAIL")
    return 0 if report["ok"] else 1


def compare_runs(old_path, new_path):
    old = json.loads(Path(old_path).read_text())
    new = json.loads(Path(new_path).read_text())
    metrics = ("company_value", "n_vehicles", "n_stations")
    old_rows = {
        (row["arm"], row["seed"]): row
        for row in old["summary"]
    }
    new_rows = {
        (row["arm"], row["seed"]): row
        for row in new["summary"]
    }
    keys = sorted(set(old_rows) | set(new_rows))
    mismatches = []
    print(f"{'seed':>8} {'metric':>16} {'old':>12} {'new':>12}")
    identical = True
    for key in keys:
        if key not in old_rows or key not in new_rows:
            print(f"FAIL cle absente {key}")
            identical = False
            continue
        a, b = old_rows[key], new_rows[key]
        if not a.get("run_ok", True) or not b.get("run_ok", True):
            print(f"FAIL run_ok seed={key[1]} old={a.get('run_ok')} new={b.get('run_ok')}")
            identical = False
        for metric in metrics:
            av, bv = a.get(metric), b.get(metric)
            mark = "OK" if av == bv else "DIFF"
            if av != bv:
                identical = False
                mismatches.append((key[1], metric, av, bv))
            print(f"{key[1]:>8} {metric:>16} {av:>12} {bv:>12} {mark}")
    print("BIT-IDENTIQUE" if identical else "PAS IDENTIQUE")
    return 0 if identical else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--prove", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--modules", nargs="*", default=None,
                        help="restreindre l'extraction a ces fichiers")
    parser.add_argument("--compare-runs", nargs=2, metavar=("OLD", "NEW"))
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if args.compare_runs:
        sys.exit(compare_runs(*args.compare_runs))

    only = set(args.modules) if args.modules else None
    if only:
        unknown = only - set(MODULE_ORDER)
        if unknown:
            parser.error("modules inconnus: " + ", ".join(sorted(unknown)))

    if args.dry_run:
        new_main, files = split_source(MAIN_PATH.read_text(), only_modules=only)
        print(f"main.nut {line_count(MAIN_PATH.read_text())} -> {line_count(new_main)}")
        for name in MODULE_ORDER:
            if name in files:
                print(f"  {name:22} {line_count(files[name]):5} lignes")
        leftover = remaining_functions(new_main)
        print("reste:", leftover)
        report = prove(
            load_baseline_main(),
            new_main,
            [_MemFile(name, files[name]) for name in files],
        )
        sys.exit(print_prove(report))

    if args.apply:
        new_main, files = apply_split(only_modules=only)
        print(f"ecrit main.nut ({line_count(new_main)} lignes) + {len(files)} modules")
        for name in MODULE_ORDER:
            if name in files:
                print(f"  {name:22} {line_count(files[name]):5} lignes")
        extra = [AI_DIR / name for name in MODULE_ORDER if (AI_DIR / name).exists()]
        report = prove(load_baseline_main(), MAIN_PATH.read_text(), extra)
        sys.exit(print_prove(report))

    if args.prove:
        extra = [AI_DIR / name for name in MODULE_ORDER if (AI_DIR / name).exists()]
        report = prove(load_baseline_main(), MAIN_PATH.read_text(), extra)
        leftover = remaining_functions(MAIN_PATH.read_text())
        print("reste dans main.nut:", leftover)
        print("lignes main.nut:", line_count(MAIN_PATH.read_text()))
        sys.exit(print_prove(report))

    parser.error("indiquer --selftest, --apply, --prove, --dry-run ou --compare-runs")


class _MemFile:
    def __init__(self, name, text):
        self.name = name
        self._text = text

    def exists(self):
        return True

    def read_text(self):
        return self._text


if __name__ == "__main__":
    main()
