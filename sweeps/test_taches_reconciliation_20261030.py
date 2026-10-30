"""Documentation reconciliation: provenance, checklist coverage, public defaults."""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

from sweeps.migrate_taches_20261030 import ROOT, rebase_link


class TaskLedgerReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', '2429d175:docs/taches.md']
        ).decode('utf-8').replace('\r\n', '\n')
        cls.archive = (ROOT / 'docs/journaux/journal_2026-10-30_transfert_taches.md').read_text(
            encoding='utf-8'
        ).replace('\r\n', '\n')
        cls.tasks = (ROOT / 'docs/taches.md').read_text(encoding='utf-8')
        cls.journal = (ROOT / 'docs/journaux/journal_2026-10-30_mise_a_jour.md').read_text(
            encoding='utf-8'
        )

    def test_complete_original_preserved_in_journal(self):
        rebased = re.sub(r'(\]\()([^\s)]+)(\))', rebase_link, self.original)
        self.assertTrue(self.archive.endswith(rebased), 'Lost original task lines in archive')
        self.assertIn('55dc840715dc5cfc1abb0a23ed623ac26614550c544fcf05712e03f1b23dfa7c',
                      self.archive)
        self.assertEqual(len(self.original.splitlines()), 2874)

    def test_all_old_unchecked_entries_accounted_for(self):
        original_numbers = {
            i for i, line in enumerate(self.original.splitlines(), 1)
            if re.match(r'^\s*- \[ \]', line)
        }
        self.assertEqual(len(original_numbers), 39)
        table = self.journal.split('### Réconciliation des 39 anciennes cases non cochées', 1)[1]
        table = table.split('Il y avait **39 lignes', 1)[0]
        covered = set()
        for line in table.splitlines():
            if not line.startswith('| '):
                continue
            fragment = line.split('|', 2)[1].strip()
            if re.fullmatch(r'[\d, ]+', fragment):
                covered.update(int(x.strip()) for x in fragment.split(','))
        self.assertEqual(original_numbers, covered)

    def test_no_new_default_misrepresented(self):
        info = (ROOT / 'ai/OpexAI/info.nut').read_text(encoding='utf-8')
        for setting, value in [('estim_unifie', 31), ('eb14_progressive', 3), ('probes', 2)]:
            idx = info.index('name = "' + setting + '"')
            block = info[idx:info.index('});', idx)]
            self.assertIn('easy_value = ' + str(value), block)
            self.assertIn('hard_value = ' + str(value), block)
            self.assertIn('custom_value = ' + str(value), block)
            self.assertIn('medium_value = ' + str(value), block)
        self.assertIn('estim_unifie=31', self.tasks)
        self.assertIn('probes=2', self.tasks)

    def test_current_links_are_files(self):
        files = [
            ROOT / 'README.md', ROOT / 'docs/taches.md', ROOT / 'docs/README.md',
            ROOT / 'docs/journaux/README.md',
            ROOT / 'docs/journaux/journal_2026-10-30_mise_a_jour.md',
        ]
        for path in files:
            body = path.read_text(encoding='utf-8')
            for match in re.finditer(r'\]\(([^\s)]+)\)', body):
                dest = match.group(1).split('#')[0].split('?')[0]
                if not dest or re.match(r'^[A-Za-z][\w+.-]*:', dest) or dest.startswith('/'):
                    continue
                with self.subTest(from_file=path.name, target=dest):
                    self.assertTrue((path.parent / dest).exists(), f'Broken link: {path}: {dest}')

    def test_repointed_historical_task_links(self):
        # Only newly introduced pointers are validated here. Older report links
        # to unmounted results/ or removed modules are a separate historical debt.
        for filename in (
            '18_orchestrateur_double_registre.md',
            'c116_graine100_chronologie_20261012.md',
            'estime_realise_par_ligne_20261012.md',
            'notrain_adapt400_20261021.md',
            'pcal03_inventaire_20261021.md',
        ):
            page = (ROOT / 'docs' / filename).read_text(encoding='utf-8')
            target = ROOT / 'docs/journaux/journal_2026-10-30_transfert_taches.md'
            self.assertTrue(target.exists())
            self.assertIn('journaux/journal_2026-10-30_transfert_taches.md', page)
            self.assertNotIn('](taches.md#L', page)
            self.assertNotIn('](../docs/taches.md#L', page)

    def test_checklist_is_an_active_registry(self):
        self.assertLess(len(self.tasks.splitlines()), 120)
        self.assertGreaterEqual(self.tasks.count('- [x]'), 10)
        self.assertGreaterEqual(self.tasks.count('- [ ]'), 20)
        self.assertIn('QUALITÉ-TESTS-ESTIM31', self.tasks)
        self.assertIn('MULTI-1 — suspendu', self.tasks)


if __name__ == '__main__':
    unittest.main()
