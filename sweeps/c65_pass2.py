"""C65 passe 2 : extraire GetSetting vers settings.nut, puis les globales en deux fichiers.

  python3 sweeps/c65_pass2.py --selftest
  python3 sweeps/c65_pass2.py --apply-settings
  python3 sweeps/c65_pass2.py --prove-settings
  python3 sweeps/c65_pass2.py --apply-globals
  python3 sweeps/c65_pass2.py --prove-globals
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from c65_split_main import leading_comment_start, squeeze_blank_lines

AI_DIR = ROOT / "ai" / "OpexAI"
MAIN_PATH = AI_DIR / "main.nut"
SETTINGS_PATH = AI_DIR / "settings.nut"
GLOBALS_PRE_PATH = AI_DIR / "globals_pre.nut"
GLOBALS_POST_PATH = AI_DIR / "globals_post.nut"
HEADER = (
    "/* C65 passe 2 : lecture unique des reglages, deplacee depuis Start().\n"
    " * Fonction libre : n'affecte que des globales. Les mutations d'instance\n"
    " * restent dans Start(), juste apres l'appel. */\n"
)
REQUIRE_LINE = 'require("settings.nut");'
MARKER = "require(\"scheduler.nut\");"
GETSETTING_RE = re.compile(r'AIController\.GetSetting\("([^"]+)"\)')

# Region extraite : du commentaire "Lu une seule fois" jusqu'avant _reconcileAfterLoad.
LOAD_BEGIN = "  /* Lu une seule fois :"
LOAD_END = "  if (this._loadedFromSave) this._reconcileAfterLoad();"


def start_span(text):
    match = re.search(r"^function OpexAI::Start\(\)\n\{", text, re.M)
    if not match:
        raise ValueError("Start() introuvable")
    return match.start()


def load_region(text):
    start_at = start_span(text)
    begin = text.find(LOAD_BEGIN, start_at)
    end = text.find(LOAD_END, start_at)
    if begin < 0 or end < 0:
        raise ValueError("bornes de la region GetSetting introuvables")
    return begin, end, text[begin:end]


# Blocs d'instance a retirer de OpexLoadSettings, dans l'ordre du source.
STAGED_LINE = "  if (!STAGED_BOOTSTRAP) this._generationStage = OPEX_STAGE_COMPLETE;\n"

FLEET_BLOCK = """  /* La file a ete batie par le constructeur, avant que ce reglage ne soit lisible : c'est donc
   * ici, et seulement ici, que l'ordre de service peut etre echange. */
  if (FLEET_BEFORE_NEW) {
    for (local i = 0; i < this._taskQueue.len() - 1; i++) {
      if (this._taskQueue[i].name == "air" && this._taskQueue[i + 1].name == "air_fleet") {
        local swap = this._taskQueue[i];
        this._taskQueue[i] = this._taskQueue[i + 1];
        this._taskQueue[i + 1] = swap;
        break;
      }
    }
  }
"""

TENSION_BLOCK = """  if (TENSION_PROBE) {
    PORTFOLIO_LOG = true;
    OpexTensionEnable(this._budget);
  }
"""
TENSION_GLOBAL = """  if (TENSION_PROBE) {
    PORTFOLIO_LOG = true;
  }
"""

C49_BLOCK = """  if (C49_SCARCITY_LEDGER) {
    this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
        decision_attempted = 0, decision_unattempted = 0, none = 0 };
    this._c49ScarcityRegime = "cash";
    ::C49_CURRENT_REGIME = "cash";
  }
"""
C49_GLOBAL = """  if (C49_SCARCITY_LEDGER) {
    ::C49_CURRENT_REGIME = "cash";
  }
"""

C50_BLOCK = """  if (C50_CHRONOLOGY_PROBE) {
    this._c50RefuseCache = {};
    this._c50LastTreasuryMonth = -1;
    OpexC50ResetNonExpansionLedger();
  }
"""
C50_GLOBAL = """  if (C50_CHRONOLOGY_PROBE) {
    OpexC50ResetNonExpansionLedger();
  }
"""

WATER_BLOCK = """  if (C41_WATER_REFRESH && this._taskQueue != null) {
    foreach (task in this._taskQueue) {
      if (task.name == "c41_water") { task.enabled = true; break; }
    }
  }
  if (C41_ROAD_REFRESH && this._taskQueue != null) {
    foreach (task in this._taskQueue) {
      if (task.name == "c41_road") { task.enabled = true; break; }
    }
  }
"""

INSTANCE_AFTER_LOAD = (
    STAGED_LINE
    + "\n"
    + FLEET_BLOCK
    + "  if (TENSION_PROBE) OpexTensionEnable(this._budget);\n"
    + """  if (C49_SCARCITY_LEDGER) {
    this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
        decision_attempted = 0, decision_unattempted = 0, none = 0 };
    this._c49ScarcityRegime = "cash";
  }
"""
    + """  if (C50_CHRONOLOGY_PROBE) {
    this._c50RefuseCache = {};
    this._c50LastTreasuryMonth = -1;
  }
"""
    + WATER_BLOCK
)


def build_settings_body(region):
    body = region
    for original, missing in (
        (STAGED_LINE, ""),
        (FLEET_BLOCK, ""),
        (TENSION_BLOCK, TENSION_GLOBAL),
        (C49_BLOCK, C49_GLOBAL),
        (C50_BLOCK, C50_GLOBAL),
        (WATER_BLOCK, ""),
    ):
        if original not in body:
            raise ValueError("bloc d'instance introuvable:\n" + original[:80])
        body = body.replace(original, missing, 1)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body


def build_settings_file(region):
    body = build_settings_body(region)
    return HEADER + "function OpexLoadSettings()\n{\n" + body.rstrip() + "\n}\n"


def build_new_start(text):
    begin, end, region = load_region(text)
    call = "  OpexLoadSettings();\n\n" + INSTANCE_AFTER_LOAD
    return text[:begin] + call + text[end:]


def insert_require(text):
    if REQUIRE_LINE in text:
        return text
    needle = MARKER + "\n"
    if needle not in text:
        raise ValueError("require scheduler.nut introuvable")
    return text.replace(needle, needle + REQUIRE_LINE + "\n", 1)


def setting_keys(text):
    return GETSETTING_RE.findall(text)


def prove_settings(original_main, new_main, settings_text):
    _, _, orig_region = load_region(original_main)
    orig_keys = setting_keys(orig_region)
    start_fn = new_main[start_span(new_main):]
    start_keys = setting_keys(start_fn)
    settings_keys = setting_keys(settings_text)
    # Le reread road_cheap_trace dans OpexDecide("SETTINGS") reste dans Start.
    log_only = [k for k in start_keys]
    problems = []
    if orig_keys != settings_keys:
        problems.append(
            f"cles GetSetting: origin {len(orig_keys)} vs settings {len(settings_keys)}"
        )
        if orig_keys != settings_keys:
            for i, (a, b) in enumerate(zip(orig_keys, settings_keys)):
                if a != b:
                    problems.append(f"  diverge a {i}: {a} vs {b}")
                    break
            if len(orig_keys) != len(settings_keys):
                problems.append(
                    f"  extra orig={orig_keys[len(settings_keys):len(settings_keys)+5]} "
                    f"extra settings={settings_keys[len(orig_keys):len(orig_keys)+5]}"
                )
    if log_only != ["road_cheap_trace"]:
        problems.append(f"Start() GetSetting restants: {log_only}")
    if "OpexLoadSettings();" not in new_main:
        problems.append("Start() n'appelle pas OpexLoadSettings")
    if "this._generationStage" not in start_fn:
        problems.append("Start() a perdu this._generationStage")
    if "OpexTensionEnable(this._budget)" not in start_fn:
        problems.append("Start() a perdu OpexTensionEnable")
    if "this._budget" in settings_text:
        problems.append("settings.nut reference this._budget")
    if re.search(r"\bthis\.", settings_text):
        problems.append("settings.nut contient this.")
    if REQUIRE_LINE not in new_main:
        problems.append("require settings.nut manquant")
    # require settings apres probes (OpexC50ResetNonExpansionLedger) et scheduler.
    probes_at = new_main.find('require("probes.nut");')
    settings_at = new_main.find(REQUIRE_LINE)
    if not (0 <= probes_at < settings_at):
        problems.append("settings.nut n'est pas requis apres probes.nut")
    return {"ok": not problems, "problems": problems,
            "n_settings": len(settings_keys), "n_orig": len(orig_keys)}


def apply_settings():
    original = MAIN_PATH.read_text()
    if SETTINGS_PATH.exists() and "function OpexLoadSettings()" in SETTINGS_PATH.read_text():
        raise SystemExit("settings.nut existe deja -- refuse de reappliquer")
    _, _, region = load_region(original)
    settings = build_settings_file(region)
    new_main = insert_require(build_new_start(original))
    report = prove_settings(original, new_main, settings)
    if not report["ok"]:
        print("FAIL avant ecriture:")
        for p in report["problems"]:
            print(" ", p)
        raise SystemExit(1)
    SETTINGS_PATH.write_text(settings)
    MAIN_PATH.write_text(new_main)
    print(f"ecrit settings.nut ({settings.count(chr(10))} lignes), "
          f"{report['n_settings']} GetSetting")
    print("OK")


GLOBAL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*) <- .+$", re.M)
PRE_HEADER = (
    "/* C65 passe 2 : globales du bloc AVANT require(budget/catalog/...). */\n"
)
POST_HEADER = (
    "/* C65 passe 2 : globales du bloc APRES require(builder_road.nut),\n"
    " * donc apres TOP_K de candidates.nut. */\n"
)
REQUIRE_PRE = 'require("globals_pre.nut");'
REQUIRE_POST = 'require("globals_post.nut");'


def classify_globals(text):
    req_budget = text.find('require("budget.nut");')
    req_road = text.find('require("builder_road.nut");')
    cls = text.find("class OpexAI extends AIController")
    if min(req_budget, req_road, cls) < 0:
        raise ValueError("bornes require/classe introuvables")
    found = []
    for match in GLOBAL_RE.finditer(text):
        start = match.start()
        end = match.end()
        if end < len(text) and text[end] == "\n":
            end += 1
        lead = leading_comment_start(text, start)
        if start < req_budget:
            where = "pre"
        elif req_road < start < cls:
            where = "post"
        else:
            where = "other"
        found.append({
            "name": match.group(1),
            "lead": lead,
            "start": start,
            "end": end,
            "stmt": text[start:end],
            "attached": text[lead:start],
            "where": where,
        })
    return found


def render_globals_file(header, items):
    chunks = [header]
    for item in items:
        attached = item["attached"].lstrip("\n")
        piece = attached + item["stmt"]
        chunks.append(piece if piece.endswith("\n") else piece + "\n")
    return "\n".join(chunk.rstrip("\n") for chunk in chunks) + "\n"


def split_globals(text):
    items = classify_globals(text)
    other = [item for item in items if item["where"] == "other"]
    if other:
        raise ValueError("globales hors des deux blocs: "
                         + ", ".join(item["name"] for item in other))
    pre = [item for item in items if item["where"] == "pre"]
    post = [item for item in items if item["where"] == "post"]
    pre_file = render_globals_file(PRE_HEADER, pre)
    post_file = render_globals_file(POST_HEADER, post)
    spans = [(item["lead"], item["end"]) for item in items]
    spans.sort()
    pieces = []
    last = 0
    for lead, end in spans:
        if lead < last:
            raise ValueError("chevauchement de globales")
        pieces.append(text[last:lead])
        last = end
    pieces.append(text[last:])
    new_main = squeeze_blank_lines("".join(pieces))
    # require pre : juste apres l'import.
    import_line = 'import("pathfinder.rail", "RailPathFinder", 1);'
    if import_line not in new_main:
        raise ValueError("import introuvable")
    if REQUIRE_PRE not in new_main:
        new_main = new_main.replace(
            import_line + "\n",
            import_line + "\n\n" + REQUIRE_PRE + "\n",
            1,
        )
    # require post : juste apres builder_road.
    road_line = 'require("builder_road.nut");'
    if road_line not in new_main:
        raise ValueError("require builder_road introuvable")
    if REQUIRE_POST not in new_main:
        new_main = new_main.replace(
            road_line + "\n",
            road_line + "\n" + REQUIRE_POST + "\n",
            1,
        )
    new_main = squeeze_blank_lines(new_main)
    if not new_main.endswith("\n"):
        new_main += "\n"
    return new_main, pre_file, post_file, pre, post


def global_stmts(text):
    return [(m.group(1), m.group(0)) for m in GLOBAL_RE.finditer(text)]


def prove_globals(original, new_main, pre_file, post_file):
    orig = classify_globals(original)
    problems = []
    main_stmts = global_stmts(new_main)
    if main_stmts:
        problems.append("main.nut a encore " + str(len(main_stmts)) + " globales: "
                        + ", ".join(n for n, _ in main_stmts[:8]))
    pre_stmts = global_stmts(pre_file)
    post_stmts = global_stmts(post_file)
    orig_pre = [(item["name"], item["stmt"].rstrip("\n")) for item in orig if item["where"] == "pre"]
    orig_post = [(item["name"], item["stmt"].rstrip("\n")) for item in orig if item["where"] == "post"]
    got_pre = [(n, s) for n, s in pre_stmts]
    got_post = [(n, s) for n, s in post_stmts]
    if [n for n, _ in orig_pre] != [n for n, _ in got_pre]:
        problems.append("ordre pre diverge")
    if [n for n, _ in orig_post] != [n for n, _ in got_post]:
        problems.append("ordre post diverge")
    if orig_pre != got_pre:
        problems.append("corps pre non identiques")
    if orig_post != got_post:
        problems.append("corps post non identiques")
    if REQUIRE_PRE not in new_main:
        problems.append("require globals_pre manquant")
    if REQUIRE_POST not in new_main:
        problems.append("require globals_post manquant")
    pre_at = new_main.find(REQUIRE_PRE)
    budget_at = new_main.find('require("budget.nut");')
    road_at = new_main.find('require("builder_road.nut");')
    post_at = new_main.find(REQUIRE_POST)
    cls_at = new_main.find("class OpexAI extends AIController")
    if not (0 <= pre_at < budget_at):
        problems.append("globals_pre n'est pas avant budget.nut")
    if not (0 <= road_at < post_at < cls_at):
        problems.append("globals_post n'est pas entre builder_road et la classe")
    orig_const = len(re.findall(r"^const ", original, re.M))
    new_const = len(re.findall(r"^const ", new_main, re.M))
    if orig_const != new_const:
        problems.append(f"const {orig_const} -> {new_const}")
    if "CASH_CANDIDATE_SCAN_LIMIT <- TOP_K" not in post_file:
        problems.append("CASH_CANDIDATE_SCAN_LIMIT hors du bloc post")
    names_pre = [n for n, _ in got_pre]
    names_post = [n for n, _ in got_post]
    if "CASH_CANDIDATE_SCAN_LIMIT" in names_post:
        if names_post.index("CASH_CANDIDATE_SCAN_LIMIT") < names_post.index("TOP_K"):
            problems.append("CASH_CANDIDATE_SCAN_LIMIT avant TOP_K")
    if "const " in pre_file or "const " in post_file:
        problems.append("une const a ete deplacee")
    return {
        "ok": not problems,
        "problems": problems,
        "n_pre": len(got_pre),
        "n_post": len(got_post),
    }


def apply_globals():
    if GLOBALS_PRE_PATH.exists() or GLOBALS_POST_PATH.exists():
        raise SystemExit("globals_pre/post existent deja -- refuse de reappliquer")
    original = MAIN_PATH.read_text()
    new_main, pre_file, post_file, pre, post = split_globals(original)
    report = prove_globals(original, new_main, pre_file, post_file)
    if not report["ok"]:
        print("FAIL avant ecriture:")
        for p in report["problems"]:
            print(" ", p)
        raise SystemExit(1)
    GLOBALS_PRE_PATH.write_text(pre_file)
    GLOBALS_POST_PATH.write_text(post_file)
    MAIN_PATH.write_text(new_main)
    print(f"ecrit globals_pre.nut ({pre_file.count(chr(10))} lignes, {report['n_pre']} slots), "
          f"globals_post.nut ({post_file.count(chr(10))} lignes, {report['n_post']} slots)")
    print(f"main.nut -> {new_main.count(chr(10))} lignes")
    print("OK")


def run_selftest():
    original = MAIN_PATH.read_text()
    if "function OpexLoadSettings()" in original or SETTINGS_PATH.exists():
        # Arbre deja applique : prouver sur disque contre une copie du Start
        # n'est plus possible (region extraite). Verifier les invariants restants.
        settings = SETTINGS_PATH.read_text()
        assert "function OpexLoadSettings()" in settings
        assert "this." not in settings
        start = original[start_span(original):]
        assert setting_keys(start) == ["road_cheap_trace"]
        assert "OpexLoadSettings();" in start
        assert REQUIRE_LINE in original
        n = len(setting_keys(settings))
        assert n == 213, n  # 214 dans Start d'origine, moins le log
        print(f"selftest settings ok (deja applique): {n} GetSetting")
        if GLOBALS_PRE_PATH.exists():
            leftover = global_stmts(MAIN_PATH.read_text())
            assert leftover == [], leftover
            assert "CASH_CANDIDATE_SCAN_LIMIT <- TOP_K" in GLOBALS_POST_PATH.read_text()
            print("selftest globals ok (deja applique)")
            return
        new_main, pre_file, post_file, pre, post = split_globals(original)
        report = prove_globals(original, new_main, pre_file, post_file)
        assert report["ok"], report["problems"]
        print(f"selftest globals ok: pre={report['n_pre']} post={report['n_post']}")
        return
    _, _, region = load_region(original)
    orig_keys = setting_keys(region)
    assert len(orig_keys) == 213, len(orig_keys)
    settings = build_settings_file(region)
    new_main = insert_require(build_new_start(original))
    report = prove_settings(original, new_main, settings)
    assert report["ok"], report["problems"]
    assert "this." not in settings
    print(f"selftest ok: {report['n_settings']} GetSetting extraits, Start() propre")
    original = MAIN_PATH.read_text()
    if "function OpexLoadSettings()" in original or SETTINGS_PATH.exists():
        # Arbre deja applique : prouver sur disque contre une copie du Start
        # n'est plus possible (region extraite). Verifier les invariants restants.
        settings = SETTINGS_PATH.read_text()
        assert "function OpexLoadSettings()" in settings
        assert "this." not in settings
        start = original[start_span(original):]
        assert setting_keys(start) == ["road_cheap_trace"]
        assert "OpexLoadSettings();" in start
        assert REQUIRE_LINE in original
        n = len(setting_keys(settings))
        assert n == 213, n  # 214 dans Start d'origine, moins le log
        print(f"selftest ok (deja applique): {n} GetSetting dans settings.nut, "
              f"1 log reste dans Start()")
        return
    _, _, region = load_region(original)
    orig_keys = setting_keys(region)
    assert len(orig_keys) == 213, len(orig_keys)
    settings = build_settings_file(region)
    new_main = insert_require(build_new_start(original))
    report = prove_settings(original, new_main, settings)
    assert report["ok"], report["problems"]
    assert "this." not in settings
    print(f"selftest ok: {report['n_settings']} GetSetting extraits, Start() propre")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--apply-settings", action="store_true")
    parser.add_argument("--prove-settings", action="store_true")
    parser.add_argument("--apply-globals", action="store_true")
    parser.add_argument("--prove-globals", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.apply_settings:
        apply_settings()
        return
    if args.apply_globals:
        apply_globals()
        return
    if args.prove_globals:
        if not GLOBALS_PRE_PATH.exists():
            raise SystemExit("globals_pre.nut absent")
        leftover = global_stmts(MAIN_PATH.read_text())
        if leftover:
            print("FAIL main.nut globales restantes:", leftover[:8])
            sys.exit(1)
        pre_n = len(global_stmts(GLOBALS_PRE_PATH.read_text()))
        post_n = len(global_stmts(GLOBALS_POST_PATH.read_text()))
        print(f"globals_pre={pre_n} globals_post={post_n} main leftover=0")
        print("OK")
        return
    if args.prove_settings:
        if not SETTINGS_PATH.exists():
            raise SystemExit("settings.nut absent")
        # Sans l'ancien Start(), on verifie les invariants post-application.
        main_text = MAIN_PATH.read_text()
        settings = SETTINGS_PATH.read_text()
        start = main_text[start_span(main_text):]
        problems = []
        if setting_keys(start) != ["road_cheap_trace"]:
            problems.append(f"Start GetSetting={setting_keys(start)}")
        if "this." in settings:
            problems.append("this. dans settings.nut")
        if "OpexLoadSettings();" not in start:
            problems.append("appel manquant")
        if REQUIRE_LINE not in main_text:
            problems.append("require manquant")
        n = len(setting_keys(settings))
        print(f"settings GetSetting={n}  Start restants={setting_keys(start)}")
        if problems:
            print("FAIL", problems)
            sys.exit(1)
        print("OK")
        return
    parser.error("indiquer --selftest, --apply-settings/--prove-settings ou --apply-globals/--prove-globals")


if __name__ == "__main__":
    main()
