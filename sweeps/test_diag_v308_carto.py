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


class TestV308RecordValidation(unittest.TestCase):
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
