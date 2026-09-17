"""C65 passe 3 : decouper _processEvents et _runNextTask par type.

Chaque branche `if (eventType == ET_X)` devient OpexAI::_onX(event).
Chaque branche `if (task.name == "y")` devient OpexAI::_dispatchY(task, year).
Les corps sont copies tels quels (continue de boucle d'evenements laisse au
dispatch). Ce n'est plus un deplacement pur : un appel de plus par evenement
et par tache. Banc 20x10 obligatoire.

  python3 sweeps/c65_pass3.py --selftest
  python3 sweeps/c65_pass3.py --apply
  python3 sweeps/c65_pass3.py --prove
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from c65_split_main import find_matching_brace, squeeze_blank_lines

AI_DIR = ROOT / "ai" / "OpexAI"
EVENTS_PATH = AI_DIR / "events.nut"
SCHEDULER_PATH = AI_DIR / "scheduler.nut"
HANDLERS_PATH = AI_DIR / "event_handlers.nut"
TASKS_PATH = AI_DIR / "scheduler_tasks.nut"
MAIN_PATH = AI_DIR / "main.nut"

EVENT_HEADER = (
    "/* C65 passe 3 : un handler par type d'evenement, corps deplace depuis\n"
    " * _processEvents. Le continue de la boucle reste dans le dispatch. */\n"
)
TASK_HEADER = (
    "/* C65 passe 3 : un dispatch par tache de file, corps deplace depuis\n"
    " * _runNextTask. */\n"
)

EVENT_IF_RE = re.compile(
    r"^(?P<indent>    )if \(eventType == AIEvent\.(?P<et>ET_[A-Z0-9_]+)\) \{",
    re.M,
)
TASK_IF_RE = re.compile(
    r'^(?P<indent>  )if \(task\.name == "(?P<name>[^"]+)"\) \{',
    re.M,
)
FUNC_RE = re.compile(
    r"^function OpexAI::(_processEvents|_runNextTask)\(\)\n\{",
    re.M,
)

EXPECTED_EVENTS = (
    "ET_VEHICLE_CRASHED",
    "ET_VEHICLE_WAITING_IN_DEPOT",
    "ET_VEHICLE_AUTOREPLACED",
    "ET_VEHICLE_UNPROFITABLE",
    "ET_INDUSTRY_CLOSE",
    "ET_SUBSIDY_OFFER",
    "ET_SUBSIDY_OFFER_EXPIRED",
    "ET_SUBSIDY_AWARDED",
    "ET_SUBSIDY_EXPIRED",
    "ET_VEHICLE_LOST",
    "ET_INDUSTRY_OPEN",
    "ET_TOWN_FOUNDED",
    "ET_ENGINE_AVAILABLE",
    "ET_STATION_FIRST_VEHICLE",
)
EXPECTED_TASKS = (
    "catalog",
    "c41_water",
    "c41_road",
    "c41_rail_signals",
    "c41_rail_junction",
    "report",
    "scrap",
    "air",
    "air_fleet",
    "projects",
    "expand",
    "refleet",
    "town_growth",
    "repay",
)


def et_to_method(et):
    parts = et.split("_")[1:]
    return "_on" + "".join(part.capitalize() for part in parts)


def task_to_method(name):
    return "_dispatch" + "".join(part[:1].upper() + part[1:] for part in name.split("_"))


def extract_main_task_queue(text):
    start = text.index("this._taskQueue = [")
    end = text.index("];", start)
    return tuple(re.findall(r'\{\s*name\s*=\s*"([^"]+)"', text[start:end]))


def function_span(text, name):
    match = re.search(
        r"^function OpexAI::" + re.escape(name) + r"\(\)\n\{",
        text,
        re.M,
    )
    if not match:
        raise ValueError(name + " introuvable")
    brace = text.find("{", match.start())
    close = find_matching_brace(text, brace)
    return match.start(), close + 1, text[match.start():close + 1]


def _loop_block_spans(text):
    """Intervalles { } des for/while/foreach, continues internes a conserver."""
    spans = []
    for match in re.finditer(r"\b(?:for|while|foreach)\s*\(", text):
        paren = match.end() - 1
        depth = 0
        i = paren
        n = len(text)
        while i < n:
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        while i < n and text[i] in " \t\n":
            i += 1
        if i < n and text[i] == "{":
            close = find_matching_brace(text, i)
            spans.append((i, close))
    return spans


def rewrite_event_continues(body):
    """continue de la boucle d'evenements -> return ; continue de for/while inchanges."""
    loops = _loop_block_spans(body)
    out = []
    last = 0
    for match in re.finditer(r"\bcontinue\s*;", body):
        pos = match.start()
        if any(a <= pos <= b for a, b in loops):
            continue
        out.append(body[last:pos])
        out.append("return;")
        last = match.end()
    out.append(body[last:])
    return "".join(out)


def dedent_block(body, spaces):
    """Retire `spaces` espaces en tete de chaque ligne, si presents."""
    out = []
    prefix = " " * spaces
    for line in body.splitlines(keepends=True):
        if line.startswith(prefix):
            out.append(line[spaces:])
        elif line.strip() == "":
            out.append(line if line.endswith("\n") else line + "\n")
        else:
            out.append(line)
    return "".join(out)


def extract_event_branches(events_text):
    _, _, func = function_span(events_text, "_processEvents")
    found = []
    for match in EVENT_IF_RE.finditer(func):
        brace = func.find("{", match.start())
        close = find_matching_brace(func, brace)
        # include through closing brace
        header = match.group(0)
        inner = func[brace + 1:close]
        found.append({
            "et": match.group("et"),
            "method": et_to_method(match.group("et")),
            "abs_start": function_span(events_text, "_processEvents")[0] + match.start(),
            "abs_end": function_span(events_text, "_processEvents")[0] + close + 1,
            "inner": inner,
            "header": header,
        })
    return found


def extract_task_branches(sched_text):
    func_start, _, func = function_span(sched_text, "_runNextTask")
    found = []
    for match in TASK_IF_RE.finditer(func):
        brace = func.find("{", match.start())
        close = find_matching_brace(func, brace)
        inner = func[brace + 1:close]
        found.append({
            "name": match.group("name"),
            "method": task_to_method(match.group("name")),
            "abs_start": func_start + match.start(),
            "abs_end": func_start + close + 1,
            "inner": inner,
        })
    return found


def render_event_handlers(branches):
    chunks = [EVENT_HEADER]
    for item in branches:
        body = rewrite_event_continues(item["inner"])
        body = dedent_block(body, 4)
        chunks.append(
            "function OpexAI::" + item["method"] + "(event)\n{\n"
            + body.rstrip() + "\n}\n"
        )
    return "\n".join(chunk.rstrip("\n") for chunk in chunks) + "\n"


def render_task_handlers(branches):
    chunks = [TASK_HEADER]
    for item in branches:
        body = dedent_block(item["inner"], 2)
        chunks.append(
            "function OpexAI::" + item["method"] + "(task, year)\n{\n"
            + body.rstrip() + "\n}\n"
        )
    return "\n".join(chunk.rstrip("\n") for chunk in chunks) + "\n"


def rewrite_process_events(events_text, branches):
    func_start, func_end, _ = function_span(events_text, "_processEvents")
    # remplacer chaque if-block par appel + continue, de la fin vers le debut
    new = events_text
    for item in reversed(branches):
        replacement = (
            "    if (eventType == AIEvent." + item["et"] + ") {\n"
            "      this." + item["method"] + "(event);\n"
            "      continue;\n"
            "    }"
        )
        new = new[:item["abs_start"]] + replacement + new[item["abs_end"]:]
    return squeeze_blank_lines(new)


def rewrite_run_next_task(sched_text, branches):
    new = sched_text
    for item in reversed(branches):
        replacement = (
            '  if (task.name == "' + item["name"] + '") '
            "return this." + item["method"] + "(task, year);"
        )
        new = new[:item["abs_start"]] + replacement + new[item["abs_end"]:]
    return squeeze_blank_lines(new)


def insert_requires(main_text):
    text = main_text
    if 'require("event_handlers.nut");' not in text:
        text = text.replace(
            'require("events.nut");\n',
            'require("events.nut");\nrequire("event_handlers.nut");\n',
            1,
        )
    if 'require("scheduler_tasks.nut");' not in text:
        text = text.replace(
            'require("scheduler.nut");\n',
            'require("scheduler.nut");\nrequire("scheduler_tasks.nut");\n',
            1,
        )
    return text


def insert_prototypes(main_text, event_methods, task_methods):
    close = main_text.find("  function _purgeSubsidyFromProjects(subId);\n}")
    if close < 0:
        raise ValueError("fin de classe introuvable")
    lines = ["  function " + name + "(event);" for name in event_methods]
    lines += ["  function " + name + "(task, year);" for name in task_methods]
    block = "\n".join(lines) + "\n"
    at = close + len("  function _purgeSubsidyFromProjects(subId);\n")
    return main_text[:at] + block + main_text[at:]


def prove(orig_events, orig_sched, new_events, new_sched, handlers, tasks):
    problems = []
    orig_e = extract_event_branches(orig_events)
    orig_t = extract_task_branches(orig_sched)
    ets = [item["et"] for item in orig_e]
    names = [item["name"] for item in orig_t]
    if tuple(ets) != EXPECTED_EVENTS:
        problems.append("events: " + str(ets))
    if tuple(names) != EXPECTED_TASKS:
        problems.append("tasks: " + str(names))
    # les nouveaux fichiers portent les corps
    for item in orig_e:
        needle = "function OpexAI::" + item["method"] + "(event)"
        if needle not in handlers:
            problems.append("handler manquant " + item["method"])
    for item in orig_t:
        needle = "function OpexAI::" + item["method"] + "(task, year)"
        if needle not in tasks:
            problems.append("dispatch manquant " + item["method"])
    # dispatchers minces : chaque if reste, mais le corps n'est plus que l'appel.
    for item in orig_e:
        stub = "this." + item["method"] + "(event);"
        inner = None
        for nb in extract_event_branches(new_events):
            if nb["et"] == item["et"]:
                inner = nb["inner"]
                break
        if inner is None or stub not in inner or "Convert(event)" in inner:
            problems.append("branche evenement non reduite " + item["et"])
    for item in orig_t:
        stub = "this." + item["method"] + "(task, year);"
        inner = None
        for nb in extract_task_branches(new_sched):
            if nb["name"] == item["name"]:
                inner = nb["inner"]
                break
        # les taches deviennent un if ... return this._dispatchX(...) sans { } ?
        # rewrite produit une ligne unique, donc plus de branche extraite.
        if inner is not None:
            problems.append("branche tache encore bloquee " + item["name"])
        elif stub not in new_sched:
            problems.append("dispatch tache sans appel " + item["method"])
    for item in orig_e:
        call = "this." + item["method"] + "(event);"
        if call not in new_events:
            problems.append("dispatch evenement sans appel " + item["method"])
    for item in orig_t:
        call = "this." + item["method"] + "(task, year);"
        if call not in new_sched:
            problems.append("dispatch tache sans appel " + item["method"])
    if "this." in handlers.split("function", 1)[0]:
        pass
    # handlers ne doivent pas contenir la boucle d'evenements
    if "IsEventWaiting" in handlers:
        problems.append("event_handlers contient la boucle")
    if "_taskQueue" in tasks and "this._taskCursor" in tasks:
        # town_growth rappelle _runNextTask, pas le curseur
        pass
    if "this._taskCursor" in tasks:
        problems.append("scheduler_tasks deplace le curseur")
    return {"ok": not problems, "problems": problems,
            "n_events": len(orig_e), "n_tasks": len(orig_t)}


def apply():
    if HANDLERS_PATH.exists() or TASKS_PATH.exists():
        raise SystemExit("event_handlers/scheduler_tasks existent deja")
    events = EVENTS_PATH.read_text()
    sched = SCHEDULER_PATH.read_text()
    e_branches = extract_event_branches(events)
    t_branches = extract_task_branches(sched)
    handlers = render_event_handlers(e_branches)
    tasks = render_task_handlers(t_branches)
    new_events = rewrite_process_events(events, e_branches)
    new_sched = rewrite_run_next_task(sched, t_branches)
    report = prove(events, sched, new_events, new_sched, handlers, tasks)
    if not report["ok"]:
        print("FAIL avant ecriture:")
        for p in report["problems"]:
            print(" ", p)
        raise SystemExit(1)
    main = MAIN_PATH.read_text()
    main = insert_requires(main)
    main = insert_prototypes(
        main,
        [item["method"] for item in e_branches],
        [item["method"] for item in t_branches],
    )
    HANDLERS_PATH.write_text(handlers)
    TASKS_PATH.write_text(tasks)
    EVENTS_PATH.write_text(new_events)
    SCHEDULER_PATH.write_text(new_sched)
    MAIN_PATH.write_text(main)
    print(f"events {len(e_branches)} handlers, tasks {len(t_branches)} dispatch")
    print(f"events.nut {new_events.count(chr(10))}  event_handlers.nut {handlers.count(chr(10))}")
    print(f"scheduler.nut {new_sched.count(chr(10))}  scheduler_tasks.nut {tasks.count(chr(10))}")
    print("OK")


def run_selftest():
    if HANDLERS_PATH.exists():
        events = EVENTS_PATH.read_text(encoding="utf-8")
        sched = SCHEDULER_PATH.read_text(encoding="utf-8")
        leftover_tasks = extract_task_branches(sched)
        assert leftover_tasks == [], [t["name"] for t in leftover_tasks]
        for br in extract_event_branches(events):
            assert "Convert(event)" not in br["inner"], br["et"]
        handlers = HANDLERS_PATH.read_text(encoding="utf-8")
        tasks = TASKS_PATH.read_text(encoding="utf-8")
        main = MAIN_PATH.read_text(encoding="utf-8")
        loops = _loop_block_spans(handlers)
        for match in re.finditer(r"\bcontinue\s*;", handlers):
            assert any(a <= match.start() <= b for a, b in loops), (
                "continue hors boucle dans event_handlers")
        for et in EXPECTED_EVENTS:
            assert et_to_method(et) in handlers, et
            assert "this." + et_to_method(et) + "(event);" in events
        for name in EXPECTED_TASKS:
            assert task_to_method(name) in tasks, name
            assert "this." + task_to_method(name) + "(task, year);" in sched
        assert extract_main_task_queue(main) == EXPECTED_TASKS, extract_main_task_queue(main)
        assert 'AILog.Error("Unknown scheduler task name: " + task.name);' in sched
        assert 'require("event_handlers.nut");' in main
        assert 'require("scheduler_tasks.nut");' in main
        print("selftest ok (deja applique): "
              f"{len(EXPECTED_EVENTS)} events, {len(EXPECTED_TASKS)} tasks")
        return
    events = EVENTS_PATH.read_text(encoding="utf-8")
    sched = SCHEDULER_PATH.read_text(encoding="utf-8")
    e_branches = extract_event_branches(events)
    t_branches = extract_task_branches(sched)
    assert [item["et"] for item in e_branches] == list(EXPECTED_EVENTS), [
        item["et"] for item in e_branches]
    assert [item["name"] for item in t_branches] == list(EXPECTED_TASKS)
    handlers = render_event_handlers(e_branches)
    tasks = render_task_handlers(t_branches)
    new_events = rewrite_process_events(events, e_branches)
    new_sched = rewrite_run_next_task(sched, t_branches)
    report = prove(events, sched, new_events, new_sched, handlers, tasks)
    assert report["ok"], report["problems"]
    # un corps connu : depot sell
    assert "EVENT_DEPOT_SELL" in handlers
    assert "this._tryBuildProjects(year)" in tasks
    assert "IsEventWaiting" in new_events
    assert "IsEventWaiting" not in handlers
    print(f"selftest ok: {report['n_events']} events, {report['n_tasks']} tasks")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--prove", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.apply:
        apply()
        return
    if args.prove:
        if not HANDLERS_PATH.exists():
            raise SystemExit("pas encore applique")
        run_selftest()
        return
    parser.error("indiquer --selftest, --apply ou --prove")


if __name__ == "__main__":
    main()
