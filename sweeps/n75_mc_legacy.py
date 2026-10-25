"""N75-MC isolation: remove ONLY the known opt-in setting additions.

Historical inventory ceilings and PO01C byte hashes must continue to cover
the same 58 legacy settings and the exact original bytes. Never rebaseline.
"""


INFO_DELTA = (
    b'    AddSetting({ name = "n75_multi_cargo",\n'
    b'      description = "Experimental 1972+ cash-idle rail refill: 0=off, 1=shadow, 2=one extra freight cargo on empty funded rail pool",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
SETTINGS_DELTA = (
    b'  local n75MultiCargo = AIController.GetSetting("n75_multi_cargo");\n'
    b'  N75_MULTI_CARGO = (n75MultiCargo >= 1 && n75MultiCargo <= 2) ? n75MultiCargo : 0;\n'
    b'  N75_MC_LAST_MONTH = (N75_MULTI_CARGO > 0) ? N75_MC_SAVED_MONTH : -1;\n'
    b'  N75_MC_SAVED_MONTH = -1;\n'
)


def historical_bytes(name, raw):
    delta = {"info.nut": INFO_DELTA, "settings.nut": SETTINGS_DELTA}.get(name)
    if delta is None:
        return raw
    assert raw.count(delta) == 1, f"N75-MC {name}: expected precisely one unchanged opt-in fragment"
    return raw.replace(delta, b"", 1)


def historical_info(info):
    return historical_bytes("info.nut", info.encode("utf-8")).decode("utf-8")
