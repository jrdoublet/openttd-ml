/* Copy-only marker for the C121 economics/catalog isolation smoke. */

function C121ABCDSource()
{
  AILog.Info("C121_ABCD v=1 econ=" + (C121_AIR_ECONOMICS ? 1 : 0)
      + " catalog=" + (C121_CATALOG_INCREMENTAL ? 1 : 0)
      + " c115=" + (C115_AIR_C100_CAPITAL_REPLAY ? 1 : 0));
}
