/* RVA-06 : descripteur ponctuel, jamais un nouveau selecteur de catalogue.
 * Lecture seule, aucune cache/persistance, aucun appel au defaut.
 * Contrats API NoAI 15.3 : capacite principale != capacite apres refit ;
 * CanPullCargo vrai ne garantit pas les callbacks d'assemblage NewGRF. */
function OpexRvaEquipment(engine, cargo, railType)
{
  if (!RVA_CYCLE_PROBE) return null;
  if (!AIEngine.IsValidEngine(engine) || !AICargo.IsValidCargo(cargo)) return null;
  if (AIEngine.GetVehicleType(engine) != AIVehicle.VT_RAIL) return null;
  if (!AIRail.IsRailTypeAvailable(railType)) return null;
  local wagon = AIEngine.IsWagon(engine);
  local primary = AIEngine.GetCargoType(engine);
  local articulated = AIEngine.IsArticulated(engine);
  local canRefit = AIEngine.CanRefitCargo(engine, cargo);
  return {
    engine = engine, cargo = cargo, railType = railType, date = AIDate.GetCurrentDate(),
    buildable = AIEngine.IsBuildable(engine), wagon = wagon, articulated = articulated,
    canRefit = canRefit, primaryCargo = primary,
    nominalMainCapacity = AIEngine.GetCapacity(engine),
    capacity = null, capacityStatus = canRefit ? "unknown_before_build_refit" : "unsupported",
    length16 = null, lengthStatus = "requires_vehicle",
    runs = AIEngine.CanRunOnRail(engine, railType),
    powered = wagon ? null : AIEngine.HasPowerOnRail(engine, railType),
    canPullCargo = wagon ? null : AIEngine.CanPullCargo(engine, cargo),
    assemblyStatus = "requires_builder_callbacks_and_length_check",
    price = AIEngine.GetPrice(engine), runningPerEconomyYear = AIEngine.GetRunningCost(engine),
    loadingUnitsPerStep = null, loadingStatus = "not_exposed_by_engine_api"
  };
}
