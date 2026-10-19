#!/usr/bin/env python3
"""Rapport « Repo stats » d'OpexAI (V260).

Génère docs/repo_stats_opexai.md :
1. Tableau cloc par langage sur ai/OpexAI/ (fichiers, vides, commentaires, code, total) ;
2. Couverture de l'API NoAI d'OpenTTD 15 (classes, méthodes statiques, méthodes d'instance,
   constantes/enums) et top 20 des classes les plus utilisées.

Bibliothèque standard Python 3 uniquement (cloc n'est pas requis).
"""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
AI_DIR = ROOT / "ai" / "OpexAI"
DEFAULT_API_FILE = ROOT / "docs" / "noai_api_15.3.tsv"
DEFAULT_OUT_FILE = ROOT / "docs" / "repo_stats_opexai.md"

LANGUAGES = {
    ".nut": "Squirrel",
    ".md": "Markdown",
    ".json": "JSON",
    ".txt": "Text",
    ".sh": "Bourne Shell",
    ".py": "Python",
}


def _strip_strings(line: str) -> str:
    """Remplace les chaînes littérales par des guillemets vides pour éviter les faux commentaires."""
    return re.sub(r'"(?:\\.|[^"\\])*"' + r"|'(?:\\.|[^'\\])'", '""', line)


def classify_lines(text: str, language: str) -> tuple[int, int, int]:
    """Classifie les lignes d'un texte en (vides, commentaires, code).

    Règles :
    - Une ligne portant du code compte comme code, même si elle porte aussi un commentaire.
    - Ligne ne contenant que des commentaires (mono-ligne ou bloc) -> commentaire.
    - Ligne vide (ou vide au sein d'un bloc) -> vide (conforme à cloc 2.06).
    """
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
            elif not line:
                blank += 1
            else:
                code += 1
            continue

        if language == "JSON":
            if not line:
                blank += 1
            else:
                code += 1
            continue

        if language == "Text":
            if not line:
                blank += 1
            else:
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
            single_candidates = [rest.find("//"), rest.find("#")]
            if language == "Bourne Shell" or language == "Python":
                single_candidates = [rest.find("#")]
                start = -1

            single = min([i for i in single_candidates if i >= 0], default=-1)

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


def get_tracked_files(ai_dir: Path = None, root: Path = None) -> list[Path]:
    """Récupère les fichiers suivis sous ai_dir en excluant les répertoires de tests."""
    target_dir = Path(ai_dir or AI_DIR).resolve()
    base_root = Path(root or ROOT).resolve()

    try:
        rel_dir = target_dir.relative_to(base_root)
        out = subprocess.run(
            ["git", "ls-files", str(rel_dir)],
            cwd=base_root,
            capture_output=True,
            text=True,
            check=True,
        )
        files = [base_root / f for f in out.stdout.splitlines() if f.strip()]
    except Exception:
        files = [p for p in target_dir.rglob("*") if p.is_file()]

    # Exclure tout répertoire de tests s'il en existe sous ai_dir
    filtered = []
    for f in sorted(files):
        parts = [p.lower() for p in f.relative_to(target_dir).parts]
        if any(part in ("test", "tests", "unit_tests") for part in parts[:-1]):
            continue
        filtered.append(f)
    return filtered


def compute_line_stats(files: list[Path]) -> dict:
    """Calcule le volume de code par langage pour les fichiers donnés."""
    stats_by_lang = {}

    for path in files:
        language = LANGUAGES.get(path.suffix)
        if language is None:
            continue
        text = path.read_text(errors="replace")
        blank, comment, code = classify_lines(text, language)
        row = stats_by_lang.setdefault(language, {"files": 0, "blank": 0, "comment": 0, "code": 0})
        row["files"] += 1
        row["blank"] += blank
        row["comment"] += comment
        row["code"] += code

    sorted_rows = []
    for lang, r in sorted(stats_by_lang.items(), key=lambda kv: -kv[1]["code"]):
        total = r["blank"] + r["comment"] + r["code"]
        sorted_rows.append({
            "language": lang,
            "files": r["files"],
            "blank": r["blank"],
            "comment": r["comment"],
            "code": r["code"],
            "total": total,
        })

    summary = {
        "files": sum(r["files"] for r in sorted_rows),
        "blank": sum(r["blank"] for r in sorted_rows),
        "comment": sum(r["comment"] for r in sorted_rows),
        "code": sum(r["code"] for r in sorted_rows),
        "total": sum(r["total"] for r in sorted_rows),
    }

    return {"rows": sorted_rows, "summary": summary}


def load_api_inventory(api_path: Path = None) -> list[tuple[str, str, str]]:
    """Charge l'inventaire officiel de l'API NoAI (kind, cls, name)."""
    path = Path(api_path or DEFAULT_API_FILE)
    if not path.is_file():
        raise FileNotFoundError(f"Inventaire d'API introuvable : {path}")

    entries = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        kind = parts[0]
        cls = parts[1] if len(parts) > 1 else ""
        name = parts[2] if len(parts) > 2 else ""
        entries.append((kind, cls, name))
    return entries


def strip_squirrel_code(text: str) -> str:
    """Supprime les blocs commentaires, chaînes et commentaires de ligne pour l'analyse statique."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    lines = []
    for line in text.splitlines():
        l_no_str = _strip_strings(line)
        l_no_com = re.split(r"//|#", l_no_str, maxsplit=1)[0]
        lines.append(l_no_com)
    return "\n".join(lines)


def analyze_api_usage(files: list[Path], api: list[tuple[str, str, str]]) -> dict:
    """Analyse l'utilisation de l'API NoAI par OpexAI.

    Recherche statique :
    - AIXxx.Yyy (méthodes statiques et constantes)
    - AIXxx( ou AIXxx sans point (instanciations ou références de classe)
    - .Yyy( (méthodes d'instance)
    - AIController sans préfixe (Sleep(, import() etc.)
    """
    nut_files = [p for p in files if p.suffix == ".nut"]
    clean_code = "\n".join(strip_squirrel_code(p.read_text(errors="replace")) for p in nut_files)

    # Extraction rapide en une passe
    dot_counts = Counter(re.findall(r"\b(AI[A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\b", clean_code))
    method_counts = Counter(re.findall(r"\.([A-Za-z0-9_]+)\s*\(", clean_code))
    bare_counts = Counter(re.findall(r"\b([A-Za-z0-9_]+)\s*\(", clean_code))
    class_counts = Counter(re.findall(r"\b(AI[A-Za-z0-9_]+)\b(?!\.)", clean_code))

    total_api = len(api)
    used_elements = set()
    total_calls = 0

    by_kind = {
        "class": {"total": 0, "used": 0, "calls": 0},
        "static": {"total": 0, "used": 0, "calls": 0},
        "method": {"total": 0, "used": 0, "calls": 0},
        "const": {"total": 0, "used": 0, "calls": 0},
    }

    by_class_calls = Counter()
    by_class_used_items = defaultdict(set)
    by_class_total_items = defaultdict(set)

    for kind, cls, name in api:
        by_class_total_items[cls].add((kind, name))
        if kind in by_kind:
            by_kind[kind]["total"] += 1

        if kind == "class":
            n = class_counts.get(cls, 0)
        elif kind == "method":
            n = method_counts.get(name, 0)
        elif cls == "AIController" and kind == "static":
            n = bare_counts.get(name, 0)
        else:
            n = dot_counts.get((cls, name), 0)

        if n > 0:
            used_elements.add((kind, cls, name))
            total_calls += n
            by_class_calls[cls] += n
            by_class_used_items[cls].add((kind, name))
            if kind in by_kind:
                by_kind[kind]["used"] += 1
                by_kind[kind]["calls"] += n

    # Top 20 classes ordonnées par appels décroissants, puis part utilisée décroissante, puis nom
    all_classes = sorted(by_class_total_items.keys())
    class_records = []
    for cls in all_classes:
        calls = by_class_calls[cls]
        used_items = len(by_class_used_items[cls])
        tot_items = len(by_class_total_items[cls])
        pct_class = (100.0 * used_items / tot_items) if tot_items else 0.0
        pct_calls = (100.0 * calls / total_calls) if total_calls else 0.0
        class_records.append({
            "class": cls,
            "calls": calls,
            "used_items": used_items,
            "total_items": tot_items,
            "pct_class": pct_class,
            "pct_calls": pct_calls,
        })

    class_records.sort(key=lambda r: (-r["calls"], -r["pct_class"], r["class"]))
    top_20 = class_records[:20]

    return {
        "total_api": total_api,
        "used_count": len(used_elements),
        "coverage_pct": (100.0 * len(used_elements) / total_api) if total_api else 0.0,
        "total_calls": total_calls,
        "by_kind": by_kind,
        "top_20": top_20,
    }


def generate_markdown_report(line_stats: dict, api_stats: dict) -> str:
    """Génère le document Markdown complet pour docs/repo_stats_opexai.md."""
    lines = []
    lines.append("# Statistiques du dépôt OpexAI (V260)")
    lines.append("")
    lines.append("Rapport automatisé et reproductible généré par `sweeps/repo_stats_opexai.py`.")
    lines.append("")
    lines.append("## 1. Tableau par langage")
    lines.append("")
    lines.append("Périmètre : fichiers suivis sous `ai/OpexAI/` (répertoires de tests exclus s'il en existe).")
    lines.append("")
    lines.append("| Langage | Fichiers | Lignes vides | Commentaires | Code | Total |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for r in line_stats["rows"]:
        lines.append(
            f"| {r['language']} | {r['files']} | {r['blank']:,} | {r['comment']:,} | {r['code']:,} | {r['total']:,} |"
            .replace(",", " ")
        )
    s = line_stats["summary"]
    lines.append(
        f"| **SUM** | **{s['files']}** | **{s['blank']:,}** | **{s['comment']:,}** | **{s['code']:,}** | **{s['total']:,}** |"
        .replace(",", " ")
    )
    lines.append("")

    lines.append("## 2. Couverture de l'API NoAI (OpenTTD 15)")
    lines.append("")
    lines.append("- **Source officielle de l'API 15** :")
    lines.append("  - Liaisons Squirrel générées d'OpenTTD 15.3 (`SquirrelExport.cmake`, APIUC=AI, `ai_*.sq.hpp` et `ai_controller.sq.hpp`), répertoriées dans `docs/noai_api_15.3.tsv` (1 167 éléments).")
    lines.append("  - En-têtes C++ officiels `src/script/api/script_*.hpp` du tag `15.0` / `15.3` (https://github.com/OpenTTD/OpenTTD/tree/15.3) archivés dans `results/api15/`.")
    lines.append(f"- **Éléments d'API utilisés** : **{api_stats['used_count']:,} / {api_stats['total_api']:,}** ({api_stats['coverage_pct']:.2f} %)".replace(",", " "))
    lines.append(f"- **Nombre total d'appels / références d'API** : **{api_stats['total_calls']:,}**".replace(",", " "))
    lines.append("")

    lines.append("### Ventilation par catégorie d'API")
    lines.append("")
    lines.append("| Catégorie | Utilisés | Total API | Couverture (%) | Appels | Part des appels (%) |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    kind_labels = {
        "static": "Méthodes statiques",
        "method": "Méthodes d'instance",
        "const": "Constantes & Enums",
        "class": "Classes (constructeurs/refs)",
    }
    for k in ["static", "method", "const", "class"]:
        info = api_stats["by_kind"][k]
        u = info["used"]
        tot = info["total"]
        pct = (100.0 * u / tot) if tot else 0.0
        calls = info["calls"]
        pct_calls = (100.0 * calls / api_stats["total_calls"]) if api_stats["total_calls"] else 0.0
        lbl = kind_labels.get(k, k)
        lines.append(
            f"| {lbl} | {u:,} | {tot:,} | {pct:.2f} % | {calls:,} | {pct_calls:.2f} % |"
            .replace(",", " ")
        )
    lines.append(
        f"| **Total** | **{api_stats['used_count']:,}** | **{api_stats['total_api']:,}** | **{api_stats['coverage_pct']:.2f} %** | **{api_stats['total_calls']:,}** | **100.00 %** |"
        .replace(",", " ")
    )
    lines.append("")

    lines.append("### 20 classes NoAI les plus utilisées")
    lines.append("")
    lines.append("| Rang | Classe | Appels | Part des appels (%) | Éléments utilisés | Couverture classe (%) |")
    lines.append("|---:|---|---:|---:|---:|---:|")

    for rank, r in enumerate(api_stats["top_20"], start=1):
        lines.append(
            f"| {rank} | `{r['class']}` | {r['calls']:,} | {r['pct_calls']:.2f} % | {r['used_items']} / {r['total_items']} | {r['pct_class']:.1f} % |"
            .replace(",", " ")
        )
    lines.append("")

    lines.append("## 3. Méthodologie et limites de l'analyse")
    lines.append("")
    lines.append("1. **Nettoyage préalable** :")
    lines.append("   - Les blocs de commentaires `/* ... */`, les commentaires de fin de ligne `//` et `#`, ainsi que les chaînes littérales `\"...\"` et `'...'` sont purgés avant l'analyse statique des symboles afin d'éliminer tout faux positif.")
    lines.append("2. **Motifs d'appels identifiés** :")
    lines.append("   - Appels statiques et constantes : motif `AIXxx.Yyy`.")
    lines.append("   - Instanciations directes : motif `AIXxx(` ou référence de classe seule sans point.")
    lines.append("   - Méthodes d'instance : motif `.Methode(` (ex: `.Valuate(`, `.Count(`).")
    lines.append("   - Fonctions `AIController` : motif sans préfixe (`Sleep(`, `import(`).")
    lines.append("3. **Limites assumées** :")
    lines.append("   - En Squirrel (langage dynamiquement typé), une méthode d'instance comme `.Valuate(` est comptabilisée sans inférence de type complète de l'objet hôte.")
    lines.append("   - Les déclarations du fichier `info.nut` (métadonnées `AIInfo`) ne font pas partie de l'API NoAI runtime et ne sont pas incluses dans les 1 167 éléments.")
    lines.append("")
    lines.append("---")
    lines.append("*Régénération : `python3 sweeps/repo_stats_opexai.py`*")
    lines.append("")

    return "\n".join(lines)


def run_pipeline(
    ai_dir: Path = None,
    api_file: Path = None,
    output_file: Path = None,
) -> tuple[dict, dict, str]:
    """Exécute l'analyse complète et écrit le fichier Markdown."""
    tracked = get_tracked_files(ai_dir)
    line_stats = compute_line_stats(tracked)
    api_entries = load_api_inventory(api_file)
    api_stats = analyze_api_usage(tracked, api_entries)
    report_md = generate_markdown_report(line_stats, api_stats)

    out_path = Path(output_file or DEFAULT_OUT_FILE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")

    return line_stats, api_stats, report_md


def main():
    parser = argparse.ArgumentParser(description="Génère les statistiques du dépôt OpexAI (V260).")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUT_FILE,
        help="Chemin du fichier Markdown généré (défaut: docs/repo_stats_opexai.md)",
    )
    parser.add_argument(
        "--api",
        type=Path,
        default=DEFAULT_API_FILE,
        help="Chemin du fichier d'inventaire API NoAI (défaut: docs/noai_api_15.3.tsv)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Affiche le rapport sur stdout en plus de l'écriture",
    )
    args = parser.parse_args()

    _, _, report_md = run_pipeline(api_file=args.api, output_file=args.output)
    if args.stdout:
        print(report_md)
    else:
        print(f"Rapport généré avec succès dans {args.output}")


if __name__ == "__main__":
    main()
