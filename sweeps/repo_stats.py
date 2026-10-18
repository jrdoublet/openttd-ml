"""V260 : rapport « Repo stats » d'OpexAI, publie dans une section du README.

Deux parties, au format du rapport montre par l'utilisateur le 18/10 :
1. lignes par langage (fichiers, vides, commentaires, code) des fichiers suivis
   de `ai/OpexAI/`, a la maniere de cloc (cloc n'est pas installe sur le VPS) ;
   les tests vivent dans `sweeps/`, hors du perimetre ;
2. couverture de l'API NoAI : elements exposes aux IA (classes, methodes,
   constantes, dont enums et types d'erreur) utilises par le code, et nombre
   de references.

L'inventaire de l'API ne se recopie pas : `extract` le tire des liaisons
Squirrel que genere OpenTTD (`cmake/scripts/SquirrelExport.cmake`, APIUC=AI,
un `ai_*.sq.hpp` par en-tete `src/script/api/script_*.hpp`) plus
`src/script/api/ai/ai_controller.sq.hpp`, ecrit a la main par OpenTTD.

    python3 sweeps/repo_stats.py extract --bindings GEN_DIR --controller ai_controller.sq.hpp
    python3 sweeps/repo_stats.py report --write-readme

Limites de l'analyse statique, assumees : une methode d'instance (AIList.Valuate)
compte comme utilisee des que `.Valuate(` apparait, quel que soit l'objet ; une
methode d'AIController compte aussi appelee sans prefixe (`Sleep(`, `import(`).
Les fonctions d'AIInfo (info.nut) ne sont pas dans les liaisons et ne comptent pas.
"""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AI_DIR = "ai/OpexAI"
API_FILE = ROOT / "docs" / "noai_api_15.3.tsv"
README = ROOT / "README.md"
BEGIN = "<!-- repo-stats:begin -->"
END = "<!-- repo-stats:end -->"

LANGUAGES = {".nut": "Squirrel", ".md": "Markdown", ".json": "JSON", ".sh": "Bourne Shell", ".py": "Python"}

_CLASS = re.compile(r'DefSQClass<\w+, ScriptType::AI> SQ(AI\w+)\("(AI\w+)"\)')
_ENTRY = re.compile(r'SQ(AI\w+)\.(DefSQ\w+)\(engine, [^"]*"([^"]+)"')
_KIND = {"DefSQConst": "const", "DefSQStaticMethod": "static", "DefSQAdvancedStaticMethod": "static",
         "DefSQMethod": "method", "DefSQAdvancedMethod": "method"}


def extract(bindings, controller):
    rows = set()
    for path in sorted(Path(bindings).glob("ai_*.sq.hpp")) + [Path(controller)]:
        text = path.read_text(errors="replace")
        for _, name in _CLASS.findall(text):
            rows.add(("class", name, ""))
        for cls, macro, name in _ENTRY.findall(text):
            if macro in _KIND:
                rows.add((_KIND[macro], cls, name))
    API_FILE.write_text("".join("\t".join(r) + "\n" for r in sorted(rows)))
    return len(rows)


def tracked_files():
    out = subprocess.run(["git", "ls-files", AI_DIR], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / f for f in out.stdout.split()]


def _strip_strings(line):
    return re.sub(r'"(?:\\.|[^"\\])*"' + r"|'(?:\\.|[^'\\])'", '""', line)


def classify_lines(text, language):
    """(vides, commentaires, code) : une ligne qui porte du code compte en code."""
    blank = comment = code = 0
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line and not in_block:
            blank += 1
            continue
        if language == "Markdown":
            if line.startswith("<!--") and line.endswith("-->"):
                comment += 1
            else:
                code += 1
            continue
        if language == "JSON":
            code += 1
            continue
        rest = _strip_strings(line)
        has_code = False
        while rest:
            if in_block:
                end = rest.find("*/")
                if end < 0:
                    rest = ""
                    break
                rest = rest[end + 2:]
                in_block = False
                continue
            start = rest.find("/*")
            single = min([i for i in (rest.find("//"), rest.find("#")) if i >= 0], default=-1)
            if language == "Bourne Shell":
                start = -1
                single = rest.find("#")
            if single >= 0 and (start < 0 or single < start):
                has_code = has_code or bool(rest[:single].strip())
                break
            if start >= 0:
                has_code = has_code or bool(rest[:start].strip())
                rest = rest[start + 2:]
                in_block = True
                continue
            has_code = has_code or bool(rest.strip())
            break
        if has_code:
            code += 1
        elif line:
            comment += 1
        else:
            blank += 1
    return blank, comment, code


def line_stats(files):
    stats = {}
    for path in files:
        language = LANGUAGES.get(path.suffix)
        if language is None:
            continue
        b, c, k = classify_lines(path.read_text(errors="replace"), language)
        row = stats.setdefault(language, [0, 0, 0, 0])
        for i, v in enumerate((1, b, c, k)):
            row[i] += v
    return sorted(stats.items(), key=lambda kv: -kv[1][3])


def api_usage(files):
    api = [tuple(l.split("\t")) for l in API_FILE.read_text().splitlines() if l]
    code = "\n".join(_strip_comments(p.read_text(errors="replace")) for p in files if p.suffix == ".nut")
    used = set()
    calls = 0
    for kind, cls, name in api:
        if kind == "class":
            n = len(re.findall(r"\b%s\b(?!\.)" % cls, code))
        elif kind == "method" or (cls == "AIController" and kind == "static"):
            n = len(re.findall(r"(?:\.|\b)%s\s*\(" % re.escape(name), code)) if cls == "AIController" \
                else len(re.findall(r"\.%s\s*\(" % re.escape(name), code))
        else:
            n = len(re.findall(r"\b%s\.%s\b" % (cls, re.escape(name)), code))
        if n:
            used.add((kind, cls, name))
            calls += n
    return len(api), len(used), calls


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(re.split(r"//|#", _strip_strings(l), maxsplit=1)[0] for l in text.splitlines())


def render(files):
    rows = line_stats(files)
    total = [sum(r[i] for _, r in rows) for i in range(4)]
    out = [BEGIN, "## Repo stats", "",
           "| Language | files | blank | comment | code |", "|---|---:|---:|---:|---:|"]
    for lang, r in rows:
        out.append("| %s | %d | %d | %d | %d |" % (lang, *r))
    out.append("| **SUM** | **%d** | **%d** | **%d** | **%d** |" % tuple(total))
    n_api, n_used, calls = api_usage(files)
    out += ["",
            "- **API usage is %.2f%%**" % (100.0 * n_used / n_api),
            "- **API call count is %d**" % calls,
            "",
            "There are %d APIs (classes, functions, enums, error types etc.) exposed to AIs by OpenTTD 15.3, "
            "of which %d are used by OpexAI. Scope: tracked files of `ai/OpexAI/`; tests (`sweeps/`) are excluded. "
            "Regenerate with `python3 sweeps/repo_stats.py report --write-readme`." % (n_api, n_used),
            END]
    return "\n".join(out)


def write_readme(section):
    text = README.read_text()
    if BEGIN in text:
        text = re.sub(re.escape(BEGIN) + ".*?" + re.escape(END), lambda _: section, text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n"
    README.write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract")
    ex.add_argument("--bindings", required=True)
    ex.add_argument("--controller", required=True)
    rp = sub.add_parser("report")
    rp.add_argument("--write-readme", action="store_true")
    args = parser.parse_args()
    if args.cmd == "extract":
        print("%d elements -> %s" % (extract(args.bindings, args.controller), API_FILE))
        return
    section = render(tracked_files())
    print(section)
    if args.write_readme:
        write_readme(section)


if __name__ == "__main__":
    main()
