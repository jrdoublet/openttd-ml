"""Static contract for tests/mechanisms fixtures copied into an OpexAI tree.

Comments and strings are removed before identifier analysis. An all-caps read
must be declared in ai/OpexAI (X <-, const X, enum), in the fixture, in a
fixture it requires, or injected as const NAME by a sweeps stager that names
that fixture. An Opex* call must name a function or Opex* <- binding in the
AI or in that same closure. NoAI names (AI*, COMPANY_*) are not globals.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
MECHANISMS = ROOT / "tests" / "mechanisms"
SWEEPS = ROOT / "sweeps"
NON_CODE = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
READ = re.compile(r"(?<![.\w])([A-Z][A-Z0-9_]{1,})\b")
OPEX_CALL = re.compile(r"(?<!function\s)(?<![.\w])(Opex[A-Za-z0-9_]+)\s*\(")
REQUIRE = re.compile(r'require\s*\(\s*"([^"]+)"\s*\)')
PY_STRING = re.compile(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def strip_code(text):
    return NON_CODE.sub(" ", text)


def without_comments(text):
    """Drop comments, keep string literals so require() paths stay visible."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        quote = text[i]
        if quote in "\"'":
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def enum_members(code):
    names = set()
    for block in re.findall(r"\benum\b[^{]*\{([^}]*)\}", code):
        names.update(re.findall(r"\b([A-Z][A-Z0-9_]*)\b", block))
    return names


def global_decls(code):
    names = set(re.findall(r"\b([A-Z][A-Z0-9_]*)\s*<-", code))
    names.update(re.findall(r"\bconst\s+([A-Z][A-Z0-9_]*)", code))
    names.update(enum_members(code))
    return names


def local_decls(code):
    return set(re.findall(r"\blocal\s+([A-Z][A-Z0-9_]*)", code))


def opex_defs(code):
    names = set(re.findall(r"function\s+(Opex[A-Za-z0-9_]+)\s*\(", code))
    names.update(re.findall(r"\b(Opex[A-Za-z0-9_]+)\s*<-", code))
    return names


def ai_sources():
    return [p for p in sorted(AI.rglob("*.nut"))]


def fixture_paths():
    return [p for p in sorted(MECHANISMS.rglob("*.nut"))]


def require_closure(path):
    """Fixture plus the mechanism files it requires, transitively."""
    seen = []
    stack = [path.resolve()]
    root = MECHANISMS.resolve()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        if root not in current.parents and current != root:
            raise AssertionError(f"{current} is outside tests/mechanisms")
        if not current.is_file():
            raise AssertionError(f"missing required fixture {current}")
        seen.append(current)
        text = without_comments(current.read_text(encoding="utf-8"))
        for rel in REQUIRE.findall(text):
            child = (current.parent / rel).resolve()
            if not child.is_file() or (root not in child.parents and child != root):
                raise AssertionError(f"{current.name} requires missing {rel}")
            stack.append(child)
    return seen


def stager_consts(fixture):
    """const NAME literals staged by a sweeps script that names this fixture.

    The injection is source text (``\\nconst NAME``), so match inside string
    literals after turning ``\\n`` into a newline.
    """
    rel = fixture.relative_to(MECHANISMS).as_posix()
    needle = fixture.name if fixture.name not in ("info.nut", "main.nut") else rel
    names = set()
    for path in SWEEPS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if needle not in text:
            continue
        for literal in PY_STRING.findall(text):
            body = literal[3:-3] if literal[:3] in ('"""', "'''") else literal[1:-1]
            body = body.replace("\\n", "\n").replace("\\t", "\t")
            names.update(re.findall(r"\bconst\s+([A-Z][A-Z0-9_]*)\b", body))
    return names


class V248MechanismFixturesStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parts = [strip_code(p.read_text(encoding="utf-8")) for p in ai_sources()]
        code = "\n".join(parts)
        cls.ai_globals = global_decls(code)
        cls.ai_opex = opex_defs(code)

    def test_uppercase_reads_are_declared(self):
        for path in fixture_paths():
            with self.subTest(path=path.relative_to(MECHANISMS).as_posix()):
                closure = require_closure(path)
                code = strip_code(path.read_text(encoding="utf-8"))
                declared = set(self.ai_globals)
                declared.update(local_decls(code))
                declared.update(stager_consts(path))
                for item in closure:
                    declared.update(global_decls(strip_code(item.read_text(encoding="utf-8"))))
                reads = set(READ.findall(code))
                missing = sorted(
                    name for name in reads - declared
                    if not name.startswith("AI") and not name.startswith("COMPANY_")
                )
                self.assertEqual(missing, [])

    def test_opex_calls_exist(self):
        for path in fixture_paths():
            with self.subTest(path=path.relative_to(MECHANISMS).as_posix()):
                closure = require_closure(path)
                code = strip_code(path.read_text(encoding="utf-8"))
                defined = set(self.ai_opex)
                for item in closure:
                    defined.update(opex_defs(strip_code(item.read_text(encoding="utf-8"))))
                missing = sorted(set(OPEX_CALL.findall(code)) - defined)
                if path.name == "c83_repair_vm.nut":
                    # Fixture historique du reparateur C83 retire au lot 2 :
                    # garder l'audit strict des autres mecanismes, et verifier
                    # que seules ces deux entrees obsoletes manquent.
                    self.assertEqual(missing, ["OpexC83RepairFindSites", "OpexC83RepairSnapshot"])
                    continue
                self.assertEqual(missing, [])
