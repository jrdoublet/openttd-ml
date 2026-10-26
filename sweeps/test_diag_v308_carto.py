"""Contrats du lecteur V308 : exclure les mesures physiquement impossibles.

Fixtures de journaux uniquement ; aucune partie ni dépendance moteur.
"""

import gzip
import tempfile
import unittest
from pathlib import Path

from sweeps.diag_v308_carto import (
    ARM_FIELDS,
    ARM_NAMES,
    TRUTH_FIELDS,
    complete_record,
    read_blocks,
    read_complete_surveys,
    summarize,
)


def block_record(index=0):
    record = {"i": index, "bx": 3, "by": 4}
    record.update({"t_" + field: 0 for field in TRUTH_FIELDS})
    record.update(t_n=64, t_build=64)
    for name in ARM_NAMES:
        record.update({name + "_" + field: 0 for field in ARM_FIELDS})
        record[name + "_n"] = (
            5 if name == "v307" else 4 if name in ("short6", "flatdry6") else 6
        )
        record[name + "_ops"] = 900
    return record


def block_line(record):
    return "[0] [I] OPEX 1970-1-1 V308_BLOCK " + " ".join(
        f"{key}={value}" for key, value in record.items()
    ) + "\n"


def survey_body(indices=range(400), *, ending=True):
    body = "[0] [I] OPEX 1970-1-1 V308_START n=400 side=8\n"
    body += "".join(block_line(block_record(index)) for index in indices)
    if ending:
        body += "[0] [I] OPEX 1970-2-11 V308_END n=400\n"
    return body


class TestV308RecordValidation(unittest.TestCase):
    def test_complete_survey_has_exactly_400_indexed_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            path.write_text(survey_body(), encoding="utf-8")
            blocks = list(read_complete_surveys([path]))
            self.assertEqual(len(blocks), 400)
            self.assertEqual({b["i"] for b in blocks}, set(range(400)))
            self.assertEqual(summarize(blocks)[0]["ops_total"], 360000)

    def test_missing_block_rejected_despite_end_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log.gz"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(survey_body(range(399)))
            with self.assertRaisesRegex(ValueError, "sondage incomplet.*399/400"):
                list(read_complete_surveys([path]))

    def test_duplicate_index_and_missing_index_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            # 400 records but index 0 twice, index 1 never observed.
            path.write_text(survey_body([0] + [0] + list(range(2, 400))),
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "indice invalide ou duplique"):
                list(read_complete_surveys([path]))

    def test_missing_end_and_bad_start_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            path.write_text(survey_body(ending=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "START/END manquant"):
                list(read_complete_surveys([path]))
            path.write_text(survey_body().replace("START n=400", "START n=399"),
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "START absent, duplique ou n invalide"):
                list(read_complete_surveys([path]))

    def test_invalid_block_cannot_be_silently_skipped_from_complete_survey(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            invalid = block_record(0)
            invalid["full6_river"] = 7
            body = survey_body().replace(block_line(block_record(0)), block_line(invalid))
            path.write_text(body, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "BLOCK hors sondage ou invalide"):
                list(read_complete_surveys([path]))

    def test_same_source_given_as_directory_and_file_is_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / "reference_seed42_r0.log"
            file.write_text(block_line(block_record()), encoding="utf-8")
            for inputs in ([root, file, file], [file, file]):
                blocks = list(read_blocks(inputs))
                self.assertEqual(len(blocks), 1)
                self.assertEqual(summarize(blocks)[0]["ops_total"], 900)

    def test_matching_gzip_copy_is_one_source_and_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            body = block_line(block_record())
            plain = root / "reference_seed42_r0.log"
            zipped = root / "reference_seed42_r0.log.gz"
            plain.write_text(body, encoding="utf-8")
            with gzip.open(zipped, "wt", encoding="utf-8") as stream:
                stream.write(body)
            self.assertEqual(len(list(read_blocks([root]))), 1)
            with gzip.open(zipped, "wt", encoding="utf-8") as stream:
                stream.write(block_line(block_record(1)))
            with self.assertRaisesRegex(ValueError, "copies V308 contradictoires"):
                list(read_blocks([root]))

    def test_numeric_aliases_are_not_independent_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            body = block_line(block_record())
            (root / "reference_seed42_r0.log").write_text(body, encoding="utf-8")
            (root / "reference_seed042_r00.log").write_text(body, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identite V308 ambigue"):
                list(read_blocks([root]))

    def test_same_log_name_in_independent_directories_keeps_both(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for dirname in ("campaign_a", "campaign_b"):
                directory = root / dirname
                directory.mkdir()
                (directory / "reference_seed42_r0.log").write_text(
                    block_line(block_record()), encoding="utf-8")
            self.assertEqual(len(list(read_blocks([root]))), 2)

    def test_sampled_counts_must_fit_each_motifs_actual_sample_size(self):
        for name in ARM_NAMES:
            for field in ARM_FIELDS:
                if field in ("n", "relief", "ops"):
                    continue
                for bound in ("negative", "above_sample_size"):
                    record = block_record()
                    value = -1 if bound == "negative" else record[name + "_n"] + 1
                    record[name + "_" + field] = value
                    with self.subTest(motif=name, field=field, value=value):
                        self.assertFalse(complete_record(record))

    def test_relief_cannot_be_negative_in_truth_or_any_motif(self):
        for name in ("t",) + ARM_NAMES:
            record = block_record()
            record[name + "_relief"] = -1
            with self.subTest(prefix=name):
                self.assertFalse(complete_record(record))

    def test_invalid_counts_are_excluded_before_rates_and_costs_are_computed(self):
        good = block_record()
        bad_river = dict(good, full6_river=7, full6_ops=999999)
        bad_city = dict(good, short6_house=-1, short6_ops=999999)
        bad_relief = dict(good, t_relief=-1)
        payload = "".join(block_line(record) for record in (
            bad_river, bad_city, bad_relief, good,
        ))
        with tempfile.TemporaryDirectory() as folder:
            for suffix in (".log", ".log.gz"):
                path = Path(folder) / ("variant_seed42_r0" + suffix)
                opener = gzip.open if suffix == ".log.gz" else open
                with opener(path, "wt", encoding="utf-8") as stream:
                    stream.write(payload)
                with self.subTest(suffix=suffix):
                    blocks = list(read_blocks([path]))
                    self.assertEqual(len(blocks), 1)
                    self.assertEqual(blocks[0]["source"], str(path))
                    for row in summarize(blocks):
                        self.assertEqual(row["n"], 1)
                        self.assertEqual(row["ops_total"], 900)
                        for kind in ("river", "river_cross", "city", "mountain"):
                            observed = row["classes"][kind]
                            self.assertEqual(observed["truth"], 0)
                            self.assertIsNone(observed["miss_pct"])
                            self.assertEqual(observed["false_pos"], 0)
                            self.assertEqual(observed["false_pct"], 0)

    def test_valid_boundaries_and_repeated_block_draws_are_preserved(self):
        dry = block_record(0)
        wet = block_record(1)
        dry["short6_n"] = dry["flatdry6_n"] = 6
        wet["t_build"] = 0
        wet["t_river"] = 64
        wet["t_river_cross"] = 1
        wet["t_relief"] = 4
        for name in ARM_NAMES:
            dry[name + "_ops"] = 0
            wet[name + "_river"] = wet[name + "_n"]
            wet[name + "_relief"] = 4
            wet[name + "_ops"] = 1200
        # Tirage avec remise : deux indices sur le même (bx, by) restent deux
        # observations. short6 lit les centres malgré la rivière ; flatdry6
        # s'arrête à quatre points dès que la périphérie est humide.
        wet["short6_n"] = wet["short6_river"] = 6
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "variant_seed42_r0.log"
            path.write_text(block_line(dry) + block_line(wet), encoding="utf-8")
            blocks = list(read_blocks([path]))
        self.assertEqual([block["i"] for block in blocks], [0, 1])
        for row in summarize(blocks):
            self.assertEqual(row["n"], 2)
            self.assertEqual(row["ops_total"], 1200)
            self.assertEqual(row["ops_median"], 600)
            self.assertEqual(row["ops_p90"], 1080)
            self.assertEqual(row["four_point_blocks"],
                             1 if row["motif"] == "flatdry6" else 0)
            for kind in ("river", "river_cross", "mountain"):
                self.assertEqual(row["classes"][kind], {
                    "truth": 1, "missed": 0, "miss_pct": 0,
                    "false_pos": 0, "false_pct": 0,
                })


if __name__ == "__main__":
    unittest.main()
