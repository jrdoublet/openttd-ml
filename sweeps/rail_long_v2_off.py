"""Projection strictement soustractive de RAIL-LONG v2.

La fixture fige les seules différences constatées entre le bundle immuable
INVEST-STALL v3 R2 et le code RAIL-LONG v2. Les empreintes historiques v1,
INVEST-STALL et SEARCH-PRIO ne sont jamais mises à jour par ce projecteur.
"""

import hashlib
import json
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "rail_long_v2_off_20261103.json"


def _off_source(name, source):
    # La couche v3 n'appartient pas aux empreintes gelées v2/v1.
    # La soustraire d'abord, même quand le mode v3 est actif sur le code live.
    from rail_long_v3_off import off_source as rail_long_v3_off
    source = rail_long_v3_off(name, source)
    # L'entree _expandRailLines porte desormais la reservation upgrade v3.
    # La retirer avant de matcher le contexte INVEST-STALL, sans retoucher
    # son hunk historique ni ses empreintes.
    from rail_long_merged_off import platform_after_v3 as platform_off
    source = platform_off(name, source)
    entry = json.loads(FIXTURE.read_text(encoding="utf-8"))["files"].get(name)
    if entry is None:
        return source
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if digest == entry["before_sha256"]:
        return source
    if digest == entry["after_sha256"]:
        # Le cas normal exige tous les ancrages aux positions figées et un
        # SHA historique inchangé, même lorsque deux lignes sont identiques.
        rows = source.splitlines(keepends=True)
        for edit in reversed(entry["edits"]):
            pos = edit["after_start"]
            if rows[pos:pos + len(edit["after"])] != edit["after"]:
                raise AssertionError(f"RAIL-LONG v2 {name}: position divergente {pos + 1}")
            rows[pos:pos + len(edit["after"])] = edit["before"]
        projected = "".join(rows)
        if hashlib.sha256(projected.encode("utf-8")).hexdigest() != entry["before_sha256"]:
            raise AssertionError(f"RAIL-LONG v2 {name}: projection altère la référence")
        return projected
    # Une projection d'un ancien levier peut précéder cette fonction ; elle
    # change le SHA total, mais pas les blocs RAIL-LONG v2. Comparer alors
    # chaque hunk exactement plutôt que supposer un ordre unique de retrait.
    markers = {
            "globals_pre.nut": "RAIL_LONG_V2",
            "settings.nut": "railLongMode",
            "info.nut": "RAIL-LONG: 1=production-based long train",
            "builder_rail.nut": "OpexRailLongV2SiteLength",
            "task_rail.nut": "RAIL_LONG_V2",
            "task_v284.nut": "railLongV2",
            "main.nut": "_railLongV2Pending",
            "orchestrator.nut": "_railLongV2Pending",
            "persist.nut": "railLongV2Upgrade",
    }
    if markers[name] not in source:
        return source
    if name == "info.nut":
        # « flags = 0 » est courant dans info.nut : les deux edits doivent
        # impérativement être groupés dans le bloc de réglage rail_long.
        old_fixture = Path(__file__).parent / "fixtures" / "rail_long_off_20261103.json"
        old_setting = json.loads(old_fixture.read_text(encoding="utf-8"))["insertions"][name][0]
        new_setting = old_setting
        for edit in entry["edits"]:
            before = "".join(edit["before"])
            after = "".join(edit["after"])
            if new_setting.count(before) != 1:
                raise AssertionError("RAIL-LONG v2 info.nut : fixture v1 incohérente")
            new_setting = new_setting.replace(before, after, 1)
        if source.count(new_setting) != 1:
            raise AssertionError("RAIL-LONG v2 info.nut : réglage modifié ou dupliqué")
        projected = source.replace(new_setting, old_setting, 1)
        if (digest == entry["after_sha256"]
                and hashlib.sha256(projected.encode("utf-8")).hexdigest() != entry["before_sha256"]):
            raise AssertionError("RAIL-LONG v2 info.nut : projection altère la référence")
        return projected
    projected = source
    for edit in entry["edits"]:
        inserted = "".join(edit["after"])
        original = "".join(edit["before"])
        if name == "builder_rail.nut" and edit["after_start"] == 1756:
            anchor = '  /* Le premier devis court est le repli physique après un A* long échoué.'
            if projected.count(anchor) != 1 or projected.count(inserted) != 2:
                raise AssertionError("RAIL-LONG v2 builder_rail.nut : garde de plan ambiguë")
            pos = projected.index(inserted, projected.index(anchor))
            projected = projected[:pos] + original + projected[pos + len(inserted):]
            continue
        if not inserted or projected.count(inserted) != 1:
            raise AssertionError(f"RAIL-LONG v2 {name}: hunk absent ou dupliqué "
                                 f"à {edit['after_start'] + 1}")
        projected = projected.replace(inserted, original, 1)
    if markers[name] in projected:
        raise AssertionError(f"RAIL-LONG v2 {name}: marqueur résiduel après retrait")
    if (digest == entry["after_sha256"]
            and hashlib.sha256(projected.encode("utf-8")).hexdigest() != entry["before_sha256"]):
        raise AssertionError(f"RAIL-LONG v2 {name}: projection altère la référence")
    return projected


def off_source(name, source):
    from rail_long_merged_off import already_v2_off, verify_stage
    if already_v2_off(name, source):
        return source
    output = _off_source(name, source)
    verify_stage("v2", name, source, output)
    return output
