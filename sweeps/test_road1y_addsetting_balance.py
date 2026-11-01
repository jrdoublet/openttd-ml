"""Opener AddSetting de info.nut et délimiteurs de chaque .nut.

Le nombre de « AddSetting( » égale le nombre de `name = "...",` des blocs.
Un opener manquant laisse cette ligne hors bloc et casse l'égalité.
Chaque ai/OpexAI/*.nut a des accolades et des parenthèses équilibrées.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
NAME_LINE = re.compile(r'name = "[^"]+",')
_CLOSES = {"}": "{", ")": "("}

# Forme du conflit : le name de rail_repair_join_site sans AddSetting({.
_MISSING_OPENER = (
    "AddSetting({\n"
    "  name = \"kept\",\n"
    "});\n"
    "  name = \"orphan\",\n"
    "});\n"
)


def delimiter_error(text):
    """None si () et {} s'empilent, chaînes et commentaires ignorés."""
    stack = []
    i = 0
    n = len(text)
    line = 1
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "\n":
                    line += 1
                i += 1
            i += 1
            continue
        if text.startswith("//", i):
            nl = text.find("\n", i)
            if nl < 0:
                break
            i = nl
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                return "commentaire non fermé ligne %d" % line
            line += text.count("\n", i, end + 2)
            i = end + 2
            continue
        if ch in "{(":
            stack.append((ch, line))
        elif ch in "})":
            if not stack or stack[-1][0] != _CLOSES[ch]:
                return "délimiteur %s ligne %d" % (ch, line)
            stack.pop()
        i += 1
    if stack:
        return "non fermé %s ligne %d" % stack[-1]
    return None


def _addsetting_blocks(text):
    blocks = []
    cursor = 0
    while True:
        start = text.find("AddSetting(", cursor)
        if start < 0:
            break
        brace = start + len("AddSetting(")
        while brace < len(text) and text[brace] in " \t\r\n":
            brace += 1
        if brace >= len(text) or text[brace] != "{":
            raise AssertionError("AddSetting sans bloc à l'offset %d" % start)
        depth = 0
        i = brace
        end = None
        while i < len(text):
            ch = text[i]
            if ch in "\"'":
                quote = ch
                i += 1
                while i < len(text) and text[i] != quote:
                    if text[i] == "\\":
                        i += 2
                        continue
                    i += 1
                i += 1
                continue
            if text.startswith("//", i):
                nl = text.find("\n", i)
                i = len(text) if nl < 0 else nl
                continue
            if text.startswith("/*", i):
                stop = text.find("*/", i + 2)
                i = len(text) if stop < 0 else stop + 2
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
            i += 1
        if end is None:
            raise AssertionError("AddSetting non fermé à l'offset %d" % start)
        blocks.append((brace, end))
        cursor = end
    return blocks


def addsetting_names_match(text):
    """True si chaque AddSetting( a exactement un `name = "...",` dans son bloc."""
    openers = text.count("AddSetting(")
    names = list(NAME_LINE.finditer(text))
    if openers != len(names):
        return False
    blocks = _addsetting_blocks(text)
    if len(blocks) != openers:
        return False
    for begin, end in blocks:
        if len(NAME_LINE.findall(text[begin:end])) != 1:
            return False
    return all(any(begin <= match.start() < end for begin, end in blocks) for match in names)


class TestAddSettingOpenersAndNutBalance(unittest.TestCase):
    def test_info_addsetting_openers_match_name_lines(self):
        text = (AI / "info.nut").read_text(encoding="utf-8")
        self.assertTrue(addsetting_names_match(text))
        self.assertFalse(addsetting_names_match(_MISSING_OPENER))
        self.assertIsNotNone(delimiter_error(_MISSING_OPENER))

    def test_each_nut_has_balanced_braces_and_parens(self):
        paths = sorted(AI.glob("*.nut"))
        self.assertGreater(len(paths), 0)
        for path in paths:
            with self.subTest(path=path.name):
                error = delimiter_error(path.read_text(encoding="utf-8"))
                self.assertIsNone(error, error)


if __name__ == "__main__":
    unittest.main()
