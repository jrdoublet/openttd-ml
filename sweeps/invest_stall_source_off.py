"""Projection OFF stricte de INVEST-STALL sans retoucher les SHA antérieurs.

Les SHA attendus sont les bytes constatés avant l'intervention dans le worktree
dirty du 3 novembre 2026, non des empreintes du master ou de fixtures régénérées.
"""

import hashlib
from pathlib import Path


BEFORE = {
    "globals_pre.nut": "914714c898439406914994e5d037a6fd94c9082797027554a0f6035c399720c8",
    "settings.nut": "5c94d07096921599ae076e6a2fa9c658a314a32f726be0aaae5c84cfff863637",
    "info.nut": "8725fd9026c4e540b73b364efc2989cf03a1f4625ebc31b6eb3a2854e96a89bb",
    "main.nut": "511d9b5cb6cc74472d4693d576858994ab63c9a037c1fb85648dc4752a4a6673",
    "scheduler.nut": "dbb1eb8113962c7f37f7463f880291e72d052c9b1cbbcf4a51fb7cab703860cc",
    "persist.nut": "f7cb9a52b155e3487fef0c003bc70fb23b35178515e0c35cbfc80f0c1d5ffdcd",
    # Empreintes du bundle R1, avant les interventions v2 dans ces deux modules.
    "task_rail.nut": "8c2db51b25da16749a69ee94c0e6172733a1a51624743f9189b7c22be917f64c",
    "orchestrator.nut": "621936521518af7349f5bc16df167e8ebec97c39cf6b62408bb2ed478baf61cd",
    "candidates.nut": "2c4d291ab9ced16eb1ef51d8eeda388d124acf445ca784f5331d433544e8ea70",
    "po01c_generators.nut": "673493c900113bb4702b038f21f84a3367eeda37547de1185eb286cd8c035671",
    "lines.nut": "c4a736461126622141e309824332b4699ce9c45d2a3c12b907ab80e26f8170f3",
    "builder_rail.nut": "2823c835fd1f54f4fab33e7c5f5f99c8a029c6a0371cbdc2412c6b75d90a5570",
    "task_v284.nut": "7128df03c22e1f2c2501b0cbda501e521996251fcfffe62580792182ab1240e1",
}

REMOVED = {
    "globals_pre.nut": [
        "/* INVEST-STALL : recharge additionnelle du vivier rail apres 1973, strict opt-in. */\n"
        "INVEST_STALL <- false;\n"
        "INVEST_STALL_LAST_MONTH <- -1;\n"
        "INVEST_STALL_SAVED_MONTH <- -1;\n",
    ],
    "settings.nut": [
        '  INVEST_STALL = AIController.GetSetting("invest_stall") == 1;\n'
        "  INVEST_STALL_LAST_MONTH = INVEST_STALL ? INVEST_STALL_SAVED_MONTH : -1;\n"
        "  INVEST_STALL_SAVED_MONTH = -1;\n",
    ],
    "info.nut": [
        '    AddSetting({ name = "invest_stall",\n'
        '      description = "INVEST-STALL: reinvest idle cash in underserved existing rail freight origins (default 0)",\n'
        "      min_value = 0, max_value = 1,\n"
        "      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n"
        "      flags = AICONFIG_BOOLEAN });\n",
    ],
    "main.nut": ['require("invest_stall.nut");\n', 'require("invest_stall_fleet.nut");\n'],
    "scheduler.nut": ['  if (INVEST_STALL) OpexInvestStallTick(this);\n'],
    "persist.nut": [
        "    if (INVEST_STALL) shortSave.investStallLastMonth <- INVEST_STALL_LAST_MONTH;\n",
        "  if (INVEST_STALL) saveObj.investStallLastMonth <- INVEST_STALL_LAST_MONTH;\n",
        "  INVEST_STALL_SAVED_MONTH = -1;\n",
        '  if (("investStallLastMonth" in data) && typeof data.investStallLastMonth == "integer")\n'
        "    INVEST_STALL_SAVED_MONTH = data.investStallLastMonth;\n",
    ],
}

# Les remplacements des gardes V284 doivent rendre les bytes R1 exactement,
# et non simplement supprimer des lignes laissant une forme OFF differente.
REPLACED = {
    "task_rail.nut": [(
        "  /* INVEST-STALL v2 : examen des vraies origines sous-transportees avant\n"
        "   * l'extension classique. Pas d'appel ni de lecture de flotte en OFF. */\n"
        "  if (INVEST_STALL && OpexInvestStallFleetSelect(this, year)) return;\n",
        "",
    )],
    "orchestrator.nut": [(
        "  if (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0 || (INVEST_STALL && OpexV284Busy(this))\n"
        "      || OpexInvestStallPending(this)) OpexV284Tick(this);\n"
        "  if ((V284_RAIL_GROWTH <= 0 && V233_LONG_GOOD <= 0 && !(INVEST_STALL && OpexV284Busy(this))\n"
        "      && !OpexInvestStallPending(this))\n"
        "      || !OpexV284Busy(this)) this._v257ReactiveStep();\n",
        "  if (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0) OpexV284Tick(this);\n"
        "  if ((V284_RAIL_GROWTH <= 0 && V233_LONG_GOOD <= 0) || !OpexV284Busy(this)) this._v257ReactiveStep();\n",
    )],
    "persist.nut": [(
        "  if (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0 || (INVEST_STALL && this._v284State != null)\n"
        "      || OpexInvestStallPending(this))\n"
        "    saveObj.v284Growth <- this._v284State;\n",
        "  if (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0) saveObj.v284Growth <- this._v284State;\n",
    ), (
        "  if (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0 || (INVEST_STALL && this._v284State != null)\n"
        "      || OpexInvestStallPending(this))\n"
        "    OpexV284Reconcile(this);\n",
        "  if (V284_RAIL_GROWTH > 0 || V233_LONG_GOOD > 0) OpexV284Reconcile(this);\n",
    )],
}


def project_off(name, source):
    from v257_demand_off import off_source as demand_off
    source = demand_off(name, source)
    # DOUBLE-GROW est une couche posterieure au snapshot INVEST-STALL.
    # L'enlever d'abord permet de conserver les SHA geles et l'idempotence.
    from double_grow_off import off_source as double_grow_off
    source = double_grow_off(name, source)
    # Les modifications RAIL-LONG v2 sont postérieures au bundle R2 et
    # doivent être soustraites avant les SHA et ancrages INVEST-STALL.
    from rail_long_v2_off import off_source as rail_long_v2_off
    source = rail_long_v2_off(name, source)
    # V3 est une couche au-dessus des bundles v2-r2 et v2 : elle doit etre
    # projetee AVANT leurs hunks ancrés et leurs SHA historiques.
    from invest_stall_v3_off import off_source as v3_off
    source = v3_off(name, source)
    # V2 : retirer d'abord ses hunks ancrés au bundle R1, puis v1 des six
    # modules de configuration. Les fixtures historiques restent inchangées.
    from invest_stall_v2_r2_off import off_source as r2_off
    from invest_stall_v2_off import off_source as v2_off
    source = v2_off(name, r2_off(name, source))
    if name not in REMOVED and name not in REPLACED:
        return source
    removals = REMOVED.get(name, [])
    replacements = REPLACED.get(name, [])
    counts = [source.count(hunk) for hunk in removals] + [source.count(old) for old, _ in replacements]
    if all(count == 0 for count in counts):
        if hashlib.sha256(source.encode("utf8")).hexdigest() == BEFORE[name]:
            return source
        raise ValueError(f"INVEST_STALL OFF marker absent on unrecognized source: {name}")
    if any(count != 1 for count in counts):
        raise ValueError(f"INVEST_STALL OFF partial or duplicated layer: {name}")
    for hunk in removals:
        source = source.replace(hunk, "", 1)
    for old, new in replacements:
        source = source.replace(old, new, 1)
    return source


def check_off(root=None):
    ai = Path(root) if root is not None else Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
    result = {}
    for name, before in BEFORE.items():
        current = (ai / name).read_text(encoding="utf8")
        projected = project_off(name, current)
        digest = hashlib.sha256(projected.encode("utf8")).hexdigest()
        if digest != before:
            raise AssertionError(f"{name}: OFF projection changed {digest} != {before}")
        if project_off(name, projected) != projected:
            raise AssertionError(f"{name}: OFF projection non-idempotent")
        result[name] = digest
    return result


if __name__ == "__main__":
    for file, digest in check_off().items():
        print(file, digest)
