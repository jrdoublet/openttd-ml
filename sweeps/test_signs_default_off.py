"""Chaque AISign.BuildSign d'OpexAI doit etre sous la garde des panneaux.

La garde existante (V167) est DEBUG_SIGNS = (probes bit 2).
Elle peut etre coupee (probes sans bit 2) sans changer les
defauts historiques (probes=2) exiges par les bancs.

Le test echoue si une pose resterait atteignable une fois cette garde a faux.
Les appels dans les commentaires sont ignores. Une pose qui servirait une
decision (lecture du panneau pour choisir) n'est pas reclassee ici : elle
doit etre signalee hors test.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
BUILD = re.compile(r"AISign\.BuildSign\s*\(")


def _code_only(source: str) -> str:
    return COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), source)


def _function_span(source: str, pos: int) -> tuple[int, int, str]:
    header = source.rfind("function ", 0, pos)
    if header < 0:
        raise AssertionError("BuildSign hors de toute fonction")
    brace = source.index("{", header)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                name_m = re.search(r"function\s+([A-Za-z0-9_:]+)\s*\(", source[header:brace])
                name = name_m.group(1) if name_m else "?"
                return brace, i, name
    raise AssertionError("fonction non terminee")


def _positive_debug_signs(condition: str) -> bool:
    cond = re.sub(r"\s+", "", condition)
    if not re.search(r"\bDEBUG_SIGNS\b", cond):
        return False
    # `!DEBUG_SIGNS` seul n'est pas une garde d'activation du then-block.
    stripped = re.sub(r"!DEBUG_SIGNS", "", cond)
    return bool(re.search(r"\bDEBUG_SIGNS\b", stripped))


def _early_return_guard(body: str, rel_pos: int) -> bool:
    """True si `if (!DEBUG_SIGNS) return;` precede l'appel au niveau du corps."""
    prefix = body[:rel_pos]
    for m in re.finditer(r"if\s*\(([^)]*)\)\s*return\s*;", prefix):
        cond = re.sub(r"\s+", "", m.group(1))
        if cond == "!DEBUG_SIGNS" or cond == "DEBUG_SIGNS==false" or cond == "DEBUG_SIGNS==0":
            # profondeur 1 = corps de fonction (la `{` ouvrante n'est pas dans body)
            depth = 0
            for ch in prefix[:m.start()]:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
            if depth == 0:
                return True
    return False


def _inside_debug_signs_then(body: str, rel_pos: int) -> bool:
    for m in re.finditer(r"if\s*\(", body):
        cond_start = m.end()
        depth = 1
        i = cond_start
        while i < len(body) and depth:
            if body[i] == "(":
                depth += 1
            elif body[i] == ")":
                depth -= 1
            i += 1
        condition = body[cond_start:i - 1]
        rest = body[i:].lstrip()
        if not rest.startswith("{"):
            continue
        brace = i + body[i:].find("{")
        inner = 0
        j = brace
        while j < len(body):
            if body[j] == "{":
                inner += 1
            elif body[j] == "}":
                inner -= 1
                if inner == 0:
                    if brace < rel_pos < j and _positive_debug_signs(condition):
                        return True
                    break
            j += 1
    return False


def _is_guarded(source: str, pos: int) -> tuple[bool, str]:
    brace, end, name = _function_span(source, pos)
    body = source[brace + 1:end]
    rel = pos - (brace + 1)
    if _early_return_guard(body, rel):
        return True, name + ": early-return DEBUG_SIGNS"
    if _inside_debug_signs_then(body, rel):
        return True, name + ": if (DEBUG_SIGNS)"
    return False, name


class TestSignsDefaultOff(unittest.TestCase):
    def test_panel_guard_is_probes_bit2(self):
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        self.assertIn(
            'DEBUG_SIGNS = (probes & 2) != 0;',
            settings,
        )
        info = (AI / "info.nut").read_text(encoding="utf-8")
        probes = info.split('name = "probes"', 1)[1].split("});", 1)[0]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(probes, key + r" = 2\b")
        self.assertNotIn('name = "debug_signs"', info)

    def test_opexsign_is_the_wrapper(self):
        probes = (AI / "probes.nut").read_text(encoding="utf-8")
        start = probes.index("function OpexSign(")
        end = probes.index("function OpexDecide(", start)
        body = probes[start:end]
        self.assertIn("if (!DEBUG_SIGNS) return;", body)
        self.assertLess(body.index("if (!DEBUG_SIGNS) return;"), body.index("AISign.BuildSign"))

    def test_every_buildsign_is_behind_debug_signs(self):
        unguarded = []
        found = 0
        for path in sorted(AI.rglob("*.nut")):
            original = path.read_text(encoding="utf-8")
            source = _code_only(original)
            for match in BUILD.finditer(source):
                found += 1
                ok, where = _is_guarded(source, match.start())
                line = source[:match.start()].count("\n") + 1
                if not ok:
                    unguarded.append(f"{path.relative_to(ROOT)}:{line} in {where}")
        self.assertGreaterEqual(found, 3, "OpexSign + BT + BC attendus")
        self.assertEqual(unguarded, [], "BuildSign sans garde DEBUG_SIGNS:\n" + "\n".join(unguarded))

    def test_budget_signs_are_display_only(self):
        report = (AI / "task_report.nut").read_text(encoding="utf-8")
        body_start = report.index("function OpexAI::_reportYear(")
        # Les panneaux BT/BC mettent a jour un cache d'ids pour SetName, ils ne
        # pilotent aucune decision (pas de lecture de nom, pas de branche metier).
        self.assertIn("if (DEBUG_SIGNS) {", report[body_start:])
        self.assertNotIn("AISign.GetName", report)
        self.assertNotIn("AISign.GetLocation", report)
        joined = ""
        for path in AI.rglob("*.nut"):
            joined += path.read_text(encoding="utf-8")
        self.assertNotIn("AISign.GetName", joined)
        self.assertNotIn("AISign.GetLocation", joined)


if __name__ == "__main__":
    unittest.main()
