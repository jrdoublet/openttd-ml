"""Shadow topology retention on economic misses, with fresh geometry oracle.

Ordinary cache/results still drive play. Shadow topology is cleared on every
invalidation other than catalogue age/input. Epoch and demand refresh stay intact.
"""
import argparse
from pathlib import Path
from .run_c121_visible_newsite_fixture import main
from .run_c121_visible_redundancy_fixture import transform as economics_transform
from .run_mechanism_fixtures import replace_once

ROOT = Path(__file__).resolve().parents[1]


def transform(target):
    economics_transform(target)
    fixture = ROOT / "tests/mechanisms/c121_visible_topology_vm.nut"
    (target / fixture.name).write_bytes(fixture.read_bytes())
    source = target / "main.nut"
    text = replace_once(source.read_text(encoding="utf8"), "function OpexAI::Start()",
                        f'require("{fixture.name}");\n\nfunction OpexAI::Start()')
    source.write_text(text, encoding="utf8")
    source = target / "air_coverage.nut"
    text = source.read_text(encoding="utf8")
    text = replace_once(text, "function OpexC121InvalidateEndpointGeometry()",
                        'function OpexC121InvalidateEndpointGeometry(reason = "other")')
    text = replace_once(text, "  C121_CATALOG_ENDPOINT_EPOCH++;",
                        "  FxVTInvalidate(reason);\n  C121_CATALOG_ENDPOINT_EPOCH++;")
    text = replace_once(text, "function OpexC121StationCoverageTiles(stationId)",
                        "function FxVTOriginalCoverage(stationId)")
    # Explicit origin labels, without changing any original invalidation.
    # Both reset call sites are distinct in their function spans.
    for fn, reason in (("OpexAirResetSiteCache", "site_reset"),
                       ("OpexAirResetStationCoverageTownCache", "coverage_reset")):
        start = text.index("function " + fn + "()")
        end = text.index("\nfunction ", start+1)
        section = replace_once(text[start:end], "OpexC121InvalidateEndpointGeometry();",
                               f'OpexC121InvalidateEndpointGeometry("{reason}");')
        text = text[:start]+section+text[end:]
    source.write_text(text, encoding="utf8")
    source = target / "air_catalog_c121.nut"
    text = replace_once(source.read_text(encoding="utf8"),
                        "if (changed) OpexC121InvalidateEndpointGeometry();",
                        'if (changed) OpexC121InvalidateEndpointGeometry("station_lines");')
    text = replace_once(text, "if (plan.c121CatalogRefreshEndpoints) OpexC121InvalidateEndpointGeometry();",
                        "if (plan.c121CatalogRefreshEndpoints) OpexC121InvalidateEndpointGeometry(reason);")
    source.write_text(text, encoding="utf8")
    source = target / "c121_visible_redundancy_vm.nut"
    text = replace_once(source.read_text(encoding="utf8"), "  FXVR_CASES++;",
                        "  FxVTDepthMatrix(catalog, quote, plane, pax, mail, target);\n  FXVR_CASES++;")
    source.write_text(text, encoding="utf8")


def scoped_transform(target):
    transform(target)
    source = target / "c121_visible_topology_vm.nut"
    text = source.read_text(encoding="utf8")
    text = replace_once(text, 'reason == "age" || reason == "input"',
                        'reason == "age" || reason == "input" || reason == "station_lines"')
    text = replace_once(text, "  if (stationId in FXVT_CACHE) return FXVT_CACHE[stationId];",
        "  local revision = stationId in C121_CATALOG_STATION_REV ? C121_CATALOG_STATION_REV[stationId] : 0;\n"
        "  if (stationId in FXVT_CACHE && FXVT_CACHE[stationId].revision == revision)\n"
        "    return FXVT_CACHE[stationId].tiles;")
    text = replace_once(text, "  FXVT_CACHE.rawset(stationId, out);",
                        "  FXVT_CACHE.rawset(stationId, { revision = revision, tiles = out });")
    text = replace_once(text, "  local newHit = stationId in FXVT_CACHE;",
        "  local revision = stationId in C121_CATALOG_STATION_REV ? C121_CATALOG_STATION_REV[stationId] : 0;\n"
        "  local newHit = stationId in FXVT_CACHE && FXVT_CACHE[stationId].revision == revision;")
    source.write_text(text, encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--scoped", action="store_true")
    args, rest = parser.parse_known_args()
    main(rest, fixture=ROOT / "tests/mechanisms/c121_visible_redundancy_vm.nut",
         marker="C121_VISIBLE_TOPOLOGY", stage_transform=scoped_transform if args.scoped else transform)
