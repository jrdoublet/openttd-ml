"""Exact OFF projection of concurrent experimental RAIL-CONSIST source hunks.

This helper touches historical test views only. Production source and its
rail_consist_pct=100 default are preserved unchanged.
"""

EDITS = {
    "economy.nut": """  /* RAIL-CONSIST : AAAHogEx exploite des rames fret ~2,7x plus capacitaires (240 contre 90
   * unites, 40x5 rail seul du 02/11) et garde une note de gare ~210/255 contre ~143 : une rame
   * plus longue reste a quai en chargement complet. Borne par le quai et max_train_length. */
  if (RAIL_CONSIST_PCT > 100 && kind != "pax") calibrationOffered = calibrationOffered * RAIL_CONSIST_PCT / 100.0;
""",
    "globals_pre.nut": """/* RAIL-CONSIST : rame fret dimensionnee pour ce % de l'offre calibree (100 = historique). */
RAIL_CONSIST_PCT <- 100;
""",
    "info.nut": """    AddSetting({ name = "rail_consist_pct",
      description = "RAIL-CONSIST: freight train sized for this % of the calibrated offer (longer trains stay loading, higher station rating); 100 = historic (default)",
      min_value = 100, max_value = 400,
      easy_value = 100, medium_value = 100, hard_value = 100, custom_value = 100,
      step_size = 50, flags = 0 });
""",
    "settings.nut": """  local railConsist = AIController.GetSetting("rail_consist_pct");
  RAIL_CONSIST_PCT = (railConsist != null && railConsist > 100 && railConsist <= 400) ? railConsist : 100;
""",
}


def off_source(name, source):
    from fleet_arb_off import off_source as fleet_off
    source = fleet_off(name, source)
    # RAIL-LONG is newer than this frozen RAIL-CONSIST baseline.  Strip its
    # exact opt-in hunks before checking the historical RAIL-CONSIST bytes.
    from rail_long_source_off import off_source as rail_long_off
    source = rail_long_off(name, source)
    edit = EDITS.get(name)
    if edit is None:
        return source
    n = source.count(edit)
    if n > 1:
        raise AssertionError(f"RAIL-CONSIST {name}: duplicate opt-in bytes")
    if n == 1:
        return source.replace(edit, "", 1)
    if "RAIL_CONSIST" in source or "rail_consist_pct" in source:
        raise AssertionError(f"RAIL-CONSIST {name}: altered opt-in bytes")
    return source


def off_bytes(name, raw):
    return off_source(name, raw.decode("utf-8")).encode("utf-8")
