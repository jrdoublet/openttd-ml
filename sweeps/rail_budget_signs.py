"""Read existing OpexAI annual RAIL budget signs from saves, host-side only.

These are cumulative OpexBudget sections, *not* total NoAI VM opcodes.  The
counter for ``cand_rank`` measures the generator TOP20, not all presorts nor
the arithmetic producing the candidate score. Never sum repeated snapshots.
"""

import re


_SIGN = re.compile(r"(OP|OS)\|([0-9]{4})\|([0-9]+)\|([0-9]+)\Z")


def rail_budget_sign_metrics(chunks, *, target_owner=0):
    signs = (chunks or {}).get("SIGN")
    if not isinstance(signs, (dict, list)):
        return {
            "rail_budget_sign_schema": "op-os-annual-v1",
            "rail_budget_sign_coverage": "missing_SIGN",
            "rail_budget_sign_by_year": None,
            "rail_budget_sign_invalid": None,
            "rail_budget_sign_conflicts": None,
        }

    records = signs.values() if isinstance(signs, dict) else signs
    years = {}
    invalid = 0
    conflicts = 0
    for sign in records:
        if not isinstance(sign, dict):
            continue
        if "owner" in sign and str(sign["owner"]) != str(target_owner):
            continue
        name = sign.get("name")
        if not isinstance(name, str) or not name.startswith(("OP|", "OS|")):
            continue
        # AISign names are truncated at 31 characters by OpexSign(). A full
        # 31-byte sign could have lost a numeric suffix: treat it as unknown.
        if len(name) >= 31:
            invalid += 1
            continue
        match = _SIGN.fullmatch(name)
        if match is None:
            invalid += 1
            continue
        kind, year, a, b = match.groups()
        values = (int(a), int(b))
        entry = years.setdefault(year, {})
        if kind in entry:
            # Duplicate even if values match: publication may have left a stale
            # annual sign, so this checkpoint cannot be treated as unique.
            conflicts += 1
            entry[kind] = None
        else:
            entry[kind] = values

    by_year = {}
    for year, entry in sorted(years.items()):
        op = entry.get("OP")
        os = entry.get("OS")
        by_year[year] = {
            "cand_pax": op[0] if op is not None else None,
            "cand_freight": op[1] if op is not None else None,
            "cand_rank": os[0] if os is not None else None,
            "budget_util_per_mille": os[1] if os is not None else None,
            "complete": op is not None and os is not None,
        }
    return {
        "rail_budget_sign_schema": "op-os-annual-v1",
        "rail_budget_sign_coverage": "retained_annual_signs",
        "rail_budget_sign_by_year": by_year,
        "rail_budget_sign_invalid": invalid,
        "rail_budget_sign_conflicts": conflicts,
    }
