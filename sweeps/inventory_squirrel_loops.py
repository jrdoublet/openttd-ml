#!/usr/bin/env python3
"""Static, read-only locator for OpexAI loops (OPCODE-AILIST-1 step 1).

This is a location/cross-reference aid, not a Squirrel parser or an opcode probe.
The accompanying review document makes the replacement decisions. It deliberately
does not assign a performance gain to unmeasured loops.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ai" / "OpexAI"
LOOP_RE = re.compile(r"\b(foreach|for|while)\s*\(")
FUNCTION_RE = re.compile(r"\bfunction\s+([\w:]+)\s*\(")
DOMAIN_RE = re.compile(
    r"industr|town|station|vehicle|tile|cargo|engine|line|candidate|"
    r"project|pair|site|source|sink|accept|produc|freight|pax|fleet|"
    r"locos|wagon|bridge|dock|ship|road|rail|water|airport|hub|plan|"
    r"neighbor|path|open|front|route|cities|towns|alternatives|funded|"
    r"best|scored|winners|ranked", re.I)

# Reviewed loop starts. These overrides are assertions about the entire loop,
# not about the availability of a native subfilter inside a partial C loop.
OVERRIDES = {
    ("probe_v307.nut", 408): "A",
    ("task_v250.nut", 188): "B",
    ("candidates.nut", 1037): "C",
    ("candidates.nut", 1049): "C",
    ("candidates.nut", 1062): "C",
    ("candidates.nut", 1064): "C",
    ("candidates.nut", 1714): "C",
    ("candidates.nut", 1737): "C",
    ("candidates.nut", 1778): "C",
    ("po01c_generators.nut", 148): "C",
    ("po01c_generators.nut", 156): "C",
    ("po01c_generators.nut", 208): "C",
    ("po01c_generators.nut", 307): "C",
    ("po01c_generators.nut", 333): "C",
    ("po01c_generators.nut", 376): "C",
    ("po01c_generators.nut", 499): "C",
    ("po01c_generators.nut", 501): "C",
    ("air_planning.nut", 584): "C",
    ("air_planning.nut", 587): "C",
    ("air_planning.nut", 1257): "C",
    ("air_coverage.nut", 449): "C",
    ("air_towns.nut", 175): "C",
    ("air_towns.nut", 197): "C",
    ("air_sites.nut", 580): "C",
    ("air_sites.nut", 581): "C",
    ("air_sites.nut", 582): "C",
    ("builder_water.nut", 143): "C",
    ("builder_water.nut", 144): "C",
    ("builder_water.nut", 145): "C",
    ("builder_water.nut", 396): "C",
    ("builder_water.nut", 397): "C",
    ("builder_rail.nut", 677): "C",
    ("builder_rail.nut", 6295): "C",
    ("builder_rail.nut", 6296): "C",
    ("projects_selection.nut", 147): "C",
    ("projects_selection.nut", 174): "C",
    ("projects_selection.nut", 748): "C",
    ("projects_selection.nut", 796): "C",
    ("projects_selection.nut", 865): "C",
    ("lines.nut", 99): "C",
    ("lines.nut", 111): "C",
    ("task_v250.nut", 193): "C",
    ("task_v250.nut", 217): "C",
    ("candidates_v276.nut", 264): "D",
    ("projects_selection.nut", 987): "D",
    ("projects_selection.nut", 1032): "D",
    ("builder_water.nut", 216): "D",
    ("builder_water.nut", 260): "D",
}


@dataclasses.dataclass
class Occurrence:
    file: str
    line: int
    function: str
    kind: str
    header: str
    body: str


def mask_comments_strings(src: str) -> str:
    """Preserve offsets and newlines, mask comments and quoted strings."""
    out = list(src)
    i = 0
    state = "code"
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if state == "code":
            if ch == '"':
                state = '"'
            elif ch == "'":
                state = "'"
            elif ch == "/" and nxt == "/":
                state = "line"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            elif ch == "/" and nxt == "*":
                state = "block"
                out[i] = out[i + 1] = " "
                i += 2
                continue
        elif state in ('"', "'"):
            if ch == "\\" and nxt:
                if ch != "\n":
                    out[i] = " "
                i += 1
                if src[i] != "\n":
                    out[i] = " "
            elif ch == state:
                state = "code"
            elif ch != "\n":
                out[i] = " "
        elif state == "line":
            if ch == "\n":
                state = "code"
            else:
                out[i] = " "
        else:
            if ch == "*" and nxt == "/":
                out[i] = out[i + 1] = " "
                i += 2
                state = "code"
                continue
            if ch != "\n":
                out[i] = " "
        i += 1
    return "".join(out)


def bracket_end(src: str, start: int, opening: str, closing: str) -> int | None:
    if start >= len(src) or src[start] != opening:
        return None
    depth = 0
    for i in range(start, len(src)):
        if src[i] == opening:
            depth += 1
        elif src[i] == closing:
            depth -= 1
            if depth == 0:
                return i
    return None


def functions(masked: str) -> list[tuple[int, int, str]]:
    found = []
    for match in FUNCTION_RE.finditer(masked):
        # Also support multiline function arguments; include only actual bodies.
        paren = masked.find("(", match.start(), match.end())
        end_args = bracket_end(masked, paren, "(", ")")
        if end_args is None:
            continue
        brace = masked.find("{", end_args + 1)
        if brace < 0 or masked[end_args + 1:brace].strip():
            continue
        end = bracket_end(masked, brace, "{", "}")
        if end is not None:
            found.append((match.start(), end, match.group(1)))
    return found


def scan_text(src: str, filename: str) -> list[Occurrence]:
    masked = mask_comments_strings(src)
    funcs = functions(masked)
    found = []
    for match in LOOP_RE.finditer(masked):
        paren = masked.find("(", match.start(), match.end())
        end_args = bracket_end(masked, paren, "(", ")")
        if end_args is None:
            continue
        hdr = " ".join(src[match.start():end_args + 1].split())
        next_token = re.search(r"\S", masked[end_args + 1:])
        if next_token is None:
            continue
        body_start = end_args + 1 + next_token.start()
        if masked[body_start] == "{":
            body_end = bracket_end(masked, body_start, "{", "}")
            if body_end is None:
                continue
            body = src[body_start:body_end + 1]
        else:
            body = src[body_start:src.find("\n", body_start) if "\n" in src[body_start:] else len(src)]
        enclosing = [(e - s, name) for s, e, name in funcs if s < match.start() < e]
        enclosing.sort()
        name = enclosing[0][1] if enclosing else "<top-level>"
        found.append(Occurrence(filename, src.count("\n", 0, match.start()) + 1,
                                name, match.group(1), hdr, body))
    return found


def scan(root: pathlib.Path = SOURCE) -> list[Occurrence]:
    rows = []
    for path in sorted(root.rglob("*.nut")):
        if any(part.lower() in ("library", ".worktrees") for part in path.parts):
            continue
        rows.extend(scan_text(path.read_text(encoding="utf-8-sig"),
                              path.relative_to(ROOT).as_posix() if root == SOURCE else path.relative_to(root).as_posix()))
    return rows


def classify(row: Occurrence) -> tuple[str, str, str, str]:
    """Conservative first pass; C/D not a substitute for reviewing the body."""
    file = pathlib.PurePosixPath(row.file).name
    key = (file, row.line)
    expr = row.header
    sample = row.body[:800]
    relevant = bool(DOMAIN_RE.search(expr) or DOMAIN_RE.search(sample))
    if "/pathfinder_v90/" in row.file:
        relevant = True
    if key in OVERRIDES:
        cls = OVERRIDES[key]
    elif not relevant:
        cls = "H"
    elif row.kind == "while":
        cls = "D"
    elif re.search(r"\b(?:Build|Remove|Demolish|Sell|Send|Rollback|Start|Stop|Move)\w*\(", sample):
        cls = "D"
    elif re.search(r"\b(?:continue|if\s*\(|DistanceManhattan|GetCargoAcceptance|GetPopulation|IsValid|GetValue)\b", sample) and (
        file.startswith("candidates") or file.startswith("po01c_generators")
        or file.startswith("air_") or file in ("catalog.nut", "spatial.nut", "terrain_valuate.nut", "task_v250.nut")
    ):
        cls = "C"
    else:
        cls = "D"
    if cls == "A":
        nature = "min/max/tri simple de liste déjà native"
    elif cls == "B":
        nature = "valuation de valeur API puis tri/filtre natif"
    elif cls == "C":
        nature = "préfiltrage API éventuel, décision/ordre conservés"
    elif cls == "H":
        nature = "contrôle/constantes hors parcours d'entités"
    elif "yield" in sample or "resume" in sample:
        nature = "curseur et suspension à conserver"
    elif row.kind == "while":
        nature = "état cumulatif, recherche, tri ou sortie anticipée"
    elif "/pathfinder_v90/" in row.file or file.startswith("builder_"):
        nature = "voisinage/construction, actions ou historique"
    else:
        nature = "objets Squirrel/effets par élément ou ordre observable"
    if re.search(r"\b(tile|dx|dy|x|y|r|radius)\b", expr, re.I) and (
            file.startswith(("builder", "air_sites", "terrain", "probe_v307"))):
        volume = "rectangle/voisinage local sur 256² et 1024²"
    elif re.search(r"(industr|source|sink|accept|produc)", expr, re.I):
        volume = "I/P/Q selon cargo (256² / 1024²)"
    elif re.search(r"(town|cities)", expr, re.I):
        volume = "T villes (256² / 1024²)"
    elif re.search(r"(vehicle|engine|wagon|loco)", expr, re.I):
        volume = "V/E selon partie/NewGRF, deux cartes"
    elif re.search(r"(station)", expr, re.I):
        volume = "N_gares par compagnie, deux cartes"
    elif re.search(r"(line)", expr, re.I):
        volume = "L lignes possédées, deux cartes"
    elif re.search(r"(project|candidate|alternative|funded|winners|ranked|best|scored)", expr, re.I):
        volume = "N_vivier/K, deux cartes"
    elif re.search(r"(sites|hubs|plan|pairs|neighbor)", expr, re.I):
        volume = "S/H/voisins, deux cartes"
    else:
        volume = "borne fonction/curseur, deux cartes"
    if file.startswith(("scheduler", "orchestrator", "task_", "po01c_regen", "candidates_v276")):
        cadence = "tick/tranche ou événement"
    elif file.startswith(("builder_", "pathfinder_")) or "/pathfinder_" in row.file:
        cadence = "construction/chemin"
    elif file.startswith(("probe_", "probes", "opcode_", "terrain_valuate")):
        cadence = "sonde si activée"
    elif file.startswith(("catalog", "candidates", "po01c_generators", "projects", "air_planning", "air_sites")):
        cadence = "passe/regen ou tranche"
    else:
        cadence = "appel métier/rapport"
    return cls, nature, volume, cadence


def markdown_index(rows: list[Occurrence]) -> str:
    by_class = collections.Counter(classify(row)[0] for row in rows)
    out = ["<!-- INDEX_BEGIN -->", "", "### Totaux de repérage", "",
           "Ce **premier tri lexical** compte les occurrences, pas les fonctions ni les lots ; "
           "C/D dans l'index sont **conservateurs et révisables** lors de la revue de chaque famille. "
           "Les classes de la table priorisée, documentées avec contexte métier, prévalent.", "",
           "| A | B | C | D | H (hors cible) | Total parcouru |", "|---:|---:|---:|---:|---:|---:|",
           "| " + " | ".join(str(by_class[c]) for c in ("A", "B", "C", "D", "H")) + f" | {len(rows)} |", "",
           "Pour chaque ligne : volume et cadence sont des **modèles**, pas des observations "
           "de partie ; coût individuel **n.m.** sauf mention du tableau principal. "
           "Estimation exploratoire pour C : `~25–200 × N` opcodes de boucle et tests Squirrel "
           "hors API et calcul métier ; D et H : gain AIList présumé nul, à revalider avant modification. "
           "Les fragments natifs applicables sont ceux du tableau et des extraits ci-dessus.", ""]
    previous = None
    for row in rows:
        if row.file != previous:
            previous = row.file
            out.extend([f"#### `{row.file}`", "", "| Ligne | Fonction | Classe | Travail / taille 256² et 1024² | Cadence ; coût ; équivalent / motif |",
                        "|---:|---|:---:|---|---|"])
        cls, nature, volume, cadence = classify(row)
        op = "n.m.; " + ("AIList/Valuate API possible" if cls in ("A", "B", "C") else "pas de substitution AIList directe")
        out.append(f"| {row.line} | `{row.function}` | {cls} | `{row.kind}` — {volume} | {cadence}; {op}; {nature} |")
    out.extend(["", "<!-- INDEX_END -->", ""])
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="output machine-readable locations")
    parser.add_argument("--all", action="store_true", help="show all loop locations")
    parser.add_argument("--summary", action="store_true", help="counts by file")
    parser.add_argument("--sort-calls", action="store_true", help="list Squirrel array.sort call sites")
    parser.add_argument("--append-index", type=pathlib.Path,
                        help="insert/replace marked auto index in an existing markdown file")
    args = parser.parse_args()
    rows = scan()
    if args.append_index is not None:
        report_path = args.append_index
        doc = report_path.read_text(encoding="utf-8-sig")
        marker = "<!-- L'index automatique est ajouté sous cette ligne par sweeps/inventory_squirrel_loops.py. -->"
        start, end = "<!-- INDEX_BEGIN -->", "<!-- INDEX_END -->"
        index = markdown_index(rows)
        if start in doc and end in doc:
            head = doc[:doc.index(start)]
            tail = doc[doc.index(end) + len(end):]
            doc = head + index + tail
        elif marker in doc:
            doc = doc.replace(marker, index, 1)
        else:
            raise SystemExit("Index marker missing; refusing to change document")
        report_path.write_text(doc, encoding="utf-8")
        print(f"Indexed {len(rows)} loops into {report_path}; classes: " +
              ", ".join(f"{k}={v}" for k, v in sorted(collections.Counter(classify(r)[0] for r in rows).items())))
    elif args.json:
        print(json.dumps([dataclasses.asdict(r) | {"body": r.body[:240]} for r in rows],
                         indent=2, ensure_ascii=False))
    elif args.summary:
        for name, n in sorted(collections.Counter(row.file for row in rows).items()):
            print(f"{n:4}  {name}")
        print(f"TOTAL {len(rows)} occurrences / {len(set(row.file for row in rows))} fichiers")
    elif args.sort_calls:
        total = 0
        for path in sorted(SOURCE.rglob("*.nut")):
            src = path.read_text(encoding="utf-8-sig")
            masked = mask_comments_strings(src)
            funcs = functions(masked)
            for m in re.finditer(r"\.sort\s*\(", masked):
                containing = sorted([(end - start, name) for start, end, name in funcs
                                     if start < m.start() < end])
                name = containing[0][1] if containing else "<top-level>"
                print(f"{path.relative_to(ROOT).as_posix()}:{src.count(chr(10), 0, m.start()) + 1} | {name}")
                total += 1
        print(f"TOTAL {total} Squirrel array.sort calls")
    elif args.all:
        for row in rows:
            print(f"{row.file}:{row.line} | {row.function} | {row.kind} | {row.header}")
    else:
        print(f"{len(rows)} loops in {len(set(row.file for row in rows))} .nut files; --all, --summary or --json")


if __name__ == "__main__":
    main()
