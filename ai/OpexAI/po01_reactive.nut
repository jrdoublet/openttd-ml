/* PO-01 : diagnostic passif, active seulement pendant une reconstruction reactive. */
function OpexPO01Describe(owner)
{
  local layers = [];
  local modes = [];
  if (owner._c76Revisions == null || owner._c76AckRevisions == null)
    return { layers = ["bootstrap"], modes = ["air", "rail", "road", "water", "fleet"] };
  local r = owner._c76Revisions;
  local a = owner._c76AckRevisions;
  if (r.towns > a.towns) layers.append("towns");
  if (r.industries > a.industries) layers.append("industries");
  if (r.lines > a.lines) layers.append("lines");
  foreach (mode in ["air", "rail", "road", "water"]) {
    if (r.engines[mode] > a.engines[mode]) layers.append("engines." + mode);
  }
  foreach (mode in ["air", "rail", "road", "water", "fleet"]) {
    local affected = false;
    foreach (dep in owner._c76GetModeDeps(mode)) {
      foreach (layer in layers) if (dep == layer) affected = true;
    }
    if (affected) modes.append(mode);
  }
  return { layers = layers, modes = modes };
}

function OpexPO01ProbeBegin(owner)
{
  local cause = OpexPO01Describe(owner);
  local layers = "";
  foreach (layer in cause.layers) layers += (layers == "" ? "" : ",") + layer;
  local modes = "";
  foreach (mode in cause.modes) modes += (modes == "" ? "" : ",") + mode;
  PO01_PROBE_SEQUENCE++;
  PO01_PROBE_CONTEXT = "batch=" + PO01_PROBE_SEQUENCE + " cause=" + layers + " modes=" + modes;
  OpexDecide("PO01_REACTIVE", PO01_PROBE_CONTEXT);
  return PO01_PROBE_CONTEXT;
}

function OpexPO01ProbeCost(mark, phase, unit)
{
  local ops = OpexOpsMeasureEnd(mark);
  OpexDecide("PO01_COST", PO01_PROBE_CONTEXT + " phase=" + phase
      + " unit=" + unit + " ops=" + ops);
}
