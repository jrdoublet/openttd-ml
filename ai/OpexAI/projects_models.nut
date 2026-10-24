/* Extrait de projects.nut (R14) : Modeles de projet : cles, facteurs de realisation C70/C82/C121, score. Requis depuis projects.nut. */

/* Cle stable d'un projet dans candidateGroups. */
function OpexProjectKeyFor(project)
{
  local prefix = "";
  if (project.mode == "fleet") {
    /* C34.2 : un achat d'avion n'a pas d'origine-destination -- il appartient a UNE ligne. */
    local lid = (("payload" in project) && project.payload != null
                 && ("line" in project.payload) && ("lineId" in project.payload.line))
                ? project.payload.line.lineId : -1;
    return "fleet|" + lid;
  }
  if (("payload" in project) && project.payload != null
      && ("isSubsidy" in project.payload) && project.payload.isSubsidy) {
    return "subsidy|" + project.payload.subsidyId;
  }
  /* Garde de forme conservee pour le cout d'opcodes historique. La generation d'extensions
   * route a disparu, mais retirer ces tests de table deplace les frontieres de suspension NoAI
   * et change les resultats deterministes du smoke. */
  if (("payload" in project) && project.payload != null
      && ("isRoadExtension" in project.payload) && project.payload.isRoadExtension) {
    return "road_extension|" + project.payload.targetLineId + "|"
           + project.payload.extensionTown;
  }
  return prefix + OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
}

function OpexProjectPairKey(kind, cargo, src, dst)
{
  if (kind == "pax" && src > dst) {
    local swap = src;
    src = dst;
    dst = swap;
  }
  return kind + "|" + cargo + "|" + src + "|" + dst;
}

/* C70 : facteurs par mode recalcules depuis les cumuls par ligne (sauvegardes avec les lignes).
 * Meme formule que le rapport annuel (task_report.nut) : pseudo-ligne a 1. Appele au chargement
 * pour ne pas repartir de k = 1 jusqu'au rapport suivant. */
function OpexC70RecomputeFactors(lines)
{
  local sums = { rail = [0.0, 0], road = [0.0, 0], air = [0.0, 0], water = [0.0, 0] };
  if (lines != null) {
    foreach (line in lines) {
      if (line == null || !("mode" in line) || !(line.mode in sums)) continue;
      if (!("c70Pred" in line) || !("c70Real" in line) || line.c70Pred <= 0) continue;
      sums[line.mode][0] += line.c70Real.tofloat() / line.c70Pred.tofloat();
      sums[line.mode][1]++;
    }
  }
  foreach (m, acc in sums) {
    C70_MODE_FACTOR[m] = (acc[0] + 1.0) / (acc[1] + 1).tofloat();
    OpexC69Log("phase=c70_reload mode=" + m + " lines=" + acc[1] + " k=" + C70_MODE_FACTOR[m]);
  }
}

/* C121 : le facteur de realisation corrige le revenu brut du modele physique,
 * jamais une prediction deja corrigee. Une pseudo-ligne a 1.0 stabilise les
 * petits echantillons ; sous MIN_LINES on conserve strictement le cold-start. */
function OpexC121RealizationFactor(plan)
{
  /* Les anciens essais r4/r5 appliquaient trop brutalement le facteur appris.
   * Le levier reste separe et ne corrige que les bras reutilisant un hub. */
  if (!C121_AIR_PROJECT_REALIZATION_ADAPTIVE
      || plan == null || !("arm" in plan)) return 1.0;
  local arm = plan.arm;
  if (arm != "hubsite" && arm != "hubhub") return 1.0;
  if (!(arm in C121_AIR_REALIZATION_FACTOR)) return 1.0;
  /* Moyenne directe des ratios C121 matures, uniquement pour les hubs AIR. */
  if (AIR_P0_DIRECT_REALIZATION_ACTIVE)
    return C121_AIR_P0_DIRECT_FACTOR[arm];
  /* La stratégie adaptative reste disponible dans les trois états de pression.
   * Le régime continue de piloter C122, mais ne bloque plus la correction
   * apprise ; sans observation suffisante, learned reste 1.0. */
  local learned = C121_AIR_REALIZATION_FACTOR[arm];
  if (learned < 0.0 || learned >= 1.0) return 1.0;
  /* Appliquer seulement 25 % de l'ecart appris pour preserver la valeur et
   * la capacite d'expansion ; le régime C121/C122 ne bloque plus ce calcul. */
  return 0.75 + 0.25 * learned;
}

function OpexC121RealizationSums()
{
  return { newpair = [0, 0], hubsite = [0, 0], hubhub = [0, 0] };
}

function OpexC121ApplyRealizationSums(sums, year, phase)
{
  AIR_P0_DIRECT_REALIZATION_ACTIVE = false;
  foreach (arm, acc in sums) {
    local n = acc[1];
    local factor = 1.0;
    if (n >= C121_AIR_REALIZATION_MIN_LINES) {
      factor = (acc[0].tofloat() + 1000.0) / ((n + 1).tofloat() * 1000.0);
    }
    local oldFactor = C121_AIR_REALIZATION_FACTOR[arm];
    C121_AIR_REALIZATION_FACTOR[arm] = factor;
    local directChanged = false;
    if ((arm == "hubsite" || arm == "hubhub")) {
      local direct = n > 0 ? acc[0].tofloat() / (n.tofloat() * 1000.0) : 1.0;
      directChanged = C121_AIR_P0_DIRECT_FACTOR[arm] != direct;
      C121_AIR_P0_DIRECT_FACTOR[arm] = direct;
      if (direct != 1.0) AIR_P0_DIRECT_REALIZATION_ACTIVE = true;
    }
    if ((oldFactor != factor || directChanged))
      C121_CATALOG_ARM_LEARN_REV.rawset(arm,
        (arm in C121_CATALOG_ARM_LEARN_REV ? C121_CATALOG_ARM_LEARN_REV[arm] : 0) + 1);
    AILog.Info("C121_REALIZATION phase=" + phase + " year=" + year
        + " arm=" + arm + " lines=" + n + " factor=" + factor);
  }
}

function OpexC121RecomputeRealizationFactors(lines)
{
  local sums = OpexC121RealizationSums();
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (lines != null) {
    foreach (line in lines) {
      if (line == null || !("mode" in line) || line.mode != "air"
          || !("c121Arm" in line) || !(line.c121Arm in sums)
          || !("c121RealizationPm" in line) || !("c121RealizationYear" in line)
          || line.c121RealizationYear < year - 1) continue;
      sums[line.c121Arm][0] += line.c121RealizationPm;
      sums[line.c121Arm][1]++;
    }
  }
  OpexC121ApplyRealizationSums(sums, year, "reload");
}

function OpexC121ProjectHasRealization(project)
{
  if (project == null || !("mode" in project)
      || !("payload" in project) || project.payload == null) return false;
  if (project.mode == "air") {
    return ("economics" in project.payload) && project.payload.economics != null
        && ("c121RealizationApplied" in project.payload.economics)
        && project.payload.economics.c121RealizationApplied;
  }
  if (project.mode == "fleet" && ("line" in project.payload) && project.payload.line != null) {
    local line = project.payload.line;
    return ("c121MarginalProfit" in line) && ("c121MarginalRevenue" in line);
  }
  return false;
}

/* C70 : facteur du mode d'un projet. Un projet de flotte ajoute des avions a une ligne aerienne. */
function OpexC70Factor(project)
{
  local mode = ("mode" in project) ? project.mode : "unknown";
  if (mode == "fleet") {
    mode = "air";
  }
  return (mode in C70_MODE_FACTOR) ? C70_MODE_FACTOR[mode] : 1.0;
}

/* C70 : profit servant au classement. Le brut reste dans profitAnnual, et donc dans
 * line.predicted : le facteur mesure le modele, jamais sa propre correction. */
function OpexC70Profit(project)
{
  /* Flow marginal is already net of the purchased engine's costs. */
  if (AIR_GROW_MARGINAL == 2 && project != null && ("airGrowMarginalProfit" in project)
      && project.airGrowMarginalProfit) return project.profitAnnual;
  /* R2 : une observation n'est pas une prediction a recalibrer. Le marqueur
   * vient de la branche qui a fourni profitAnnual, pas de l'etat actuel de la ligne. */
  if (project != null && ("profitIsObserved" in project) && project.profitIsObserved)
    return project.profitAnnual;
  /* Eviter une seconde calibration C70 apres une correction C121 non neutre. */
  if (AIR_P0_DIRECT_REALIZATION_ACTIVE && project != null && ("mode" in project)
      && project.mode == "air" && OpexC121ProjectHasRealization(project)
      && ("realizationFactor" in project.payload.economics)
      && project.payload.economics.realizationFactor != 1.0)
    return project.profitAnnual;
  /* Le learner de realisation AIR C121 reste en shadow (facteur causal = 1.0),
   * donc une nouvelle ligne AIR doit continuer a beneficier de la calibration
   * C70 existante. Seule la flotte C121 porte deja sa propre marge observee. */
  /* V161 : un renfort dont la valeur reste celle du modele perd cette exemption. */
  if (project != null && ("mode" in project) && project.mode == "fleet"
      && !("v161Calibrate" in project)
      && OpexC121ProjectHasRealization(project)) return project.profitAnnual;

  return project.profitAnnual * OpexC70Factor(project);
}

/* Profit calibre des scores : OpexC70Profit. */
OpexCalibratedProfit <- OpexC70Profit;

function OpexProjectScore(value, cost)
{
  if (value <= 0 || cost <= 0) return 0.0;
  return (value.tofloat() * 1000.0) / cost;
}
