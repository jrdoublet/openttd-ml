"""One-shot lossless transfer of the October 2026 task ledger to journals.

Execute once from a clean isolated worktree. Never overwrite the archived source.
The source is versioned in Git; the SHA below proves what has been transferred.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/taches.md'
STUB = ROOT / 'docs/taches_20261030_nouveau.tmp'
DEST = ROOT / 'docs/journaux/journal_2026-10-30_transfert_taches.md'


def rebase_link(match: re.Match[str]) -> str:
    target = match.group(2)
    if target.startswith(('#', '/', '//')) or re.match(r'^[A-Za-z][\w+.-]*:', target):
        return match.group(0)
    # Links in the source file resolve relative to docs/, while archive links
    # resolve relative to docs/journaux/. Prefix one parent for the same target.
    return match.group(1) + '../' + target + match.group(3)


def main() -> None:
    if DEST.exists():
        raise SystemExit('Refusing to overwrite archived task ledger')
    if not SOURCE.is_file() or not STUB.is_file():
        raise SystemExit('Missing source/stub')
    original = SOURCE.read_bytes()
    text = original.decode('utf-8')
    if not text.startswith('# Tâches — travail restant') or len(text.splitlines()) < 2500:
        raise SystemExit('Unexpected original task ledger; refusing to migrate')
    new_text = STUB.read_text(encoding='utf-8')
    if not new_text.startswith('# Tâches — registre actif'):
        raise SystemExit('Unexpected replacement task ledger')
    digest = hashlib.sha256(original).hexdigest()
    # Rebase Markdown links only; code, dates, findings, and wording are preserved.
    rebased = re.sub(r'(\]\()([^\s)]+)(\))', rebase_link, text)
    header = (
        '# Transfert intégral du registre de tâches du 30 octobre 2026\n\n'
        '> **Archive historique, non autoritaire pour les tâches courantes.** '
        'Copie de `docs/taches.md` telle qu’elle existait dans le commit '
        '`2429d175` avant la réconciliation du 30/10. Des notes très anciennes '
        'étaient encore marquées « à faire » ; cela **ne** prouve **pas** '
        'qu’elles soient ouvertes aujourd’hui. Pour agir, utiliser '
        '[le registre courant](../taches.md).\n'
        '> Liens relatifs adaptés au déplacement sous `docs/journaux/`.\n\n'
        f'- SHA-256 des octets UTF-8 du `docs/taches.md` source : `{digest}`.\n'
        f'- Taille originale : **{len(original)} octets**, '
        f'**{len(text.splitlines())} lignes**.\n'
        f'- Cases historiquement ouvertes : **{text.count("- [ ]")}**, '
        f'cases cochées : **{text.count("- [x]")}** ; '
        'leurs statuts sont à interpréter à la date de chaque note.\n'
        '- Les rapports externes et les campagnes `results/` ne sont pas '
        'déplacés, supprimés ou relancés par ce transfert.\n\n'
        '---\n\n'
    )
    # A second reproduction copy using the old path and line endings is held
    # by Git in the parent commit, ensuring an exact byte-for-byte restore.
    DEST.write_text(header + rebased, encoding='utf-8')
    SOURCE.write_text(new_text, encoding='utf-8')
    STUB.unlink()
    print('ARCHIVED_TASKS', 'sha256=' + digest, 'original_lines=' + str(len(text.splitlines())),
          'new_lines=' + str(len(new_text.splitlines())), 'archive=' + str(DEST))


if __name__ == '__main__':
    main()
