"""V263b : retraits explicites et comparabilite stricte des deux arbres."""
import argparse
import copy
import unittest
from unittest.mock import patch
from sweeps.compare_cd_cross_tree_c66 import compare, parse_expected_removed, validate_settings


class RemovedSettings(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_expected_removed("a=1,b=0,c=2"), {"a": 1, "b": 0, "c": 2})

    def test_invalid_declarations(self):
        for value in ("", "a", "=1", "a=x", "a=1,a=1", "a=1,"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                parse_expected_removed(value)

    def test_only_declared_removals_accepted(self):
        validate_settings({"a": 1, "b": 0}, {"b": 0}, {"a": 1})
        for ref, var, removed in (
            ({"a": 1}, {}, None),
            ({"a": 1}, {"a": 1}, {"a": 1}),
            ({}, {}, {"a": 1}),
            ({"a": 0}, {}, {"a": 1}),
            ({"a": 1, "b": 0}, {}, {"a": 1}),
            ({"a": 1, "b": 0}, {"b": 1}, {"a": 1}),
            ({"a": 1}, {"extra": 0}, {"a": 1}),
        ):
            with self.subTest(ref=ref, var=var), self.assertRaises(AssertionError):
                validate_settings(ref, var, removed)

    def test_economic_only_integration(self):
        data = {"years": 10, "seeds": [42], "repeats": 1}
        manifest = {"sources": {"AAAHogEx": {"sha256": "aaa"}, "OpexAI": {"sha256": "ref"}},
                    "configuration": {"raw": "cfg"}, "versions": {}, "libraries": {},
                    "policies": [{"settings": {"effective": {"a": 2, "b": 0}}}]}
        variant = copy.deepcopy(manifest)
        variant["sources"]["OpexAI"]["sha256"] = "var"
        variant["policies"][0]["settings"]["effective"] = {"b": 0}
        records = {(42, 0): dict.fromkeys(("profit_year", "company_value", "primary_vehicles", "n_stations"), 1)}
        def collect(path, opcode):
            self.assertFalse(opcode)
            return data, manifest if path == "ref" else variant, records, {(42, 0): {}}
        with patch("sweeps.compare_cd_cross_tree_c66.collect", side_effect=collect):
            with self.assertRaises(AssertionError):
                compare("ref", "var", opcode=False)
            result = compare("ref", "var", opcode=False, expected_removed={"a": 2})
        self.assertTrue(result["valid"])
        self.assertEqual(result["expected_removed"], {"a": 2})
        self.assertEqual(result["economic"]["profit_year"]["mean_delta"], 0)
