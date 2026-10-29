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
  /* ESTIM-1 bit 1 : un facteur de recette AIR unique, tous bras, remplace la
   * realisation directe P0 des hubs et la calibration C70 des paires neuves. */
  if ((ESTIM_UNIFIE & 1) != 0) return ESTIM_K_R.air;
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
  /* V161 : la recette marginale est deja calibree (C121 ou ESTIM), la perte
   * des voisines et les couts sont decomptes ; ne pas recalibrer le profit. */
  if (project != null && ("v161NetMarginalModeled" in project)
      && project.v161NetMarginalModeled) return project.profitAnnual;
  if ((ESTIM_UNIFIE & 4) != 0 && project != null
      && ("estimMarginalModeled" in project) && project.estimMarginalModeled)
    return project.profitAnnual;
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
  if (project != null && ("mode" in project) && project.mode == "fleet"
      && OpexC121ProjectHasRealization(project)) return project.profitAnnual;

  return project.profitAnnual * OpexC70Factor(project);
}

/* ESTIM-1 bit 16 : multiplier le profil fixe de distance par le niveau rail
 * appris (rapport de sommes retreci vers le prior 0.92). Valeur 0.92 au centre
 * de la population de calibration ; aucun apprentissage d'une pente sur quelques lignes. */
function OpexEstimRailRevenueFactor(distance)
{
  if ((ESTIM_UNIFIE & 16) == 0 || distance <= 0) return ESTIM_K_R.rail;
  /* Le corpus DUEL couvre 15..250 tuiles. Conserver le dernier niveau observe
   * hors de cette plage, sans extrapoler une pente a tres grande distance. */
  local calibratedDistance = distance;
  if (calibratedDistance < 15) calibratedDistance = 15;
  if (calibratedDistance > 250) calibratedDistance = 250;
  local profile = ESTIM_RAIL_KR_PROFILE_A + ESTIM_RAIL_KR_PROFILE_B * calibratedDistance;
  if (profile < 0.05) profile = 0.05;
  return ESTIM_K_R.rail * profile / ESTIM_K_R_PRIOR.rail;
}

/* ESTIM-1 bit 16 : corriger le capital RAIL pour le seul classement des
 * candidats non traces. Un devis physique issu d'A* reste facteur 1.
 * Le cout estime ne doit jamais modifier la garde de financement. */
function OpexEstimRailScoreCapital(project, decisionFinanceCapital)
{
  if ((ESTIM_UNIFIE & 16) == 0 || project == null
      || !("mode" in project) || project.mode != "rail"
      || !("distance" in project) || project.distance <= 0
      || !("capital" in project) || project.capital <= 0) return decisionFinanceCapital;
  if ((("capitalIsActual" in project) && project.capitalIsActual)
      || (("payload" in project) && project.payload != null
          && ("capitalIsActual" in project.payload) && project.payload.capitalIsActual))
    return decisionFinanceCapital;
  local calibratedDistance = project.distance;
  if (calibratedDistance < 15) calibratedDistance = 15;
  if (calibratedDistance > 250) calibratedDistance = 250;
  local factor = ESTIM_RAIL_KC_A + ESTIM_RAIL_KC_B * calibratedDistance;
  local extra = decisionFinanceCapital - project.capital;
  if (extra < 0) extra = 0;
  return (project.capital.tofloat() * factor + 0.5).tointeger() + extra;
}

/* ESTIM-1 bit 1 : P = P_modele - (1 - k_R) * R. Le facteur corrige la recette, jamais le
 * profit : un projet a faible marge peut devenir negatif. AIR C121 porte deja k_R dans son
 * economie (OpexC121RealizationFactor). Flotte et observations : logique historique (lot 3). */
function OpexEstimProfit(project)
{
  if (project != null && ("v161NetMarginalModeled" in project)
      && project.v161NetMarginalModeled) return project.profitAnnual;
  if ((ESTIM_UNIFIE & 4) != 0 && project != null
      && ("estimMarginalModeled" in project) && project.estimMarginalModeled)
    return project.profitAnnual;
  if (project == null || !("mode" in project) || !(project.mode in ESTIM_K_R)
      || (("profitIsObserved" in project) && project.profitIsObserved)
      || !("revenueAnnual" in project) || project.revenueAnnual <= 0)
    return OpexC70Profit(project);
  if ((ESTIM_UNIFIE & 1) == 0 && !((ESTIM_UNIFIE & 16) != 0 && project.mode == "rail"))
    return OpexC70Profit(project);
  if (project.mode == "air" && OpexC121ProjectHasRealization(project))
    return project.profitAnnual;
  local kR = (project.mode == "rail" && (ESTIM_UNIFIE & 16) != 0) ? OpexEstimRailRevenueFactor(
      ("distance" in project) ? project.distance : 0) : ESTIM_K_R[project.mode];
  return (project.profitAnnual - (1.0 - kR) * project.revenueAnnual).tointeger();
}

/* ESTIM-1 bit 1 : cumul par ligne, annees pleines (age >= 2) a flotte de construction, sans
 * normalisation par la flotte. Recette predite brute : AIR = recette C121 avant facteur. */
function OpexEstimAccumulateLine(line, year, vehCount, currentRevenue, sums)
{
  local mode = ("mode" in line) ? line.mode : "unknown";
  if (!(mode in sums)) return;
  if ((ESTIM_UNIFIE & 1) == 0 && mode != "rail") return;
  /* Sous bit 1, predRevenue AIR contient deja k_R. Quand le shadow C121 n'a
   * pas pu fournir la recette brute, ne jamais apprendre sur cette valeur
   * deja calibree (ce qui ferait artificiellement tendre k_R vers 1). */
  if (mode == "air" && (!("c121RawRevenueAnnual" in line)
      || line.c121RawRevenueAnnual <= 0)) return;
  local age = ("year" in line) ? year - line.year : -1;
  local n0 = ("trains0" in line) ? line.trains0 : 0;
  local pred = mode == "air" ? line.c121RawRevenueAnnual
      : (("predRevenue" in line) ? line.predRevenue : 0);
  if (age >= 2 && n0 > 0 && vehCount == n0 && pred > 0) {
    if (!("estimRevPred" in line)) { line.estimRevReal <- 0; line.estimRevPred <- 0; line.estimRevN <- 0; }
    line.estimRevReal += currentRevenue > 0 ? currentRevenue.tointeger() : 0;
    line.estimRevPred += pred.tointeger();
    line.estimRevN++;
  }
  if (("estimRevPred" in line) && line.estimRevPred > 0) {
    sums[mode][0] += line.estimRevReal.tofloat();
    sums[mode][1] += line.estimRevPred.tofloat();
    sums[mode][2] += line.estimRevN;
  }
}

function OpexEstimRevenueSums()
{
  return { rail = [0.0, 0.0, 0], road = [0.0, 0.0, 0], air = [0.0, 0.0, 0], water = [0.0, 0.0, 0] };
}

/* k = (n * rho + w0 * k0) / (n + w0) : rho rapport des sommes, n annees-lignes. */
function OpexEstimPublishRevenueFactors(sums, year, phase)
{
  local w0 = ESTIM_K_R_PRIOR_WEIGHT;
  local airChanged = false;
  foreach (m, acc in sums) {
    if ((ESTIM_UNIFIE & 1) == 0 && m != "rail") continue;
    local n = acc[2].tofloat();
    local k = ESTIM_K_R_PRIOR[m];
    if (n > 0 && acc[1] > 0) k = (n * acc[0] / acc[1] + w0 * k) / (n + w0);
    local changed = ESTIM_K_R[m] != k;
    ESTIM_K_R[m] = k;
    if (m == "air" && changed) airChanged = true;
    /* Le catalogue C121 met en cache l'economie par bras : invalider quand k_R AIR change. */
    if (m == "air" && changed) {
      foreach (arm in ["newpair", "hubsite", "hubhub"])
        C121_CATALOG_ARM_LEARN_REV.rawset(arm,
          (arm in C121_CATALOG_ARM_LEARN_REV ? C121_CATALOG_ARM_LEARN_REV[arm] : 0) + 1);
    }
    AILog.Info("ESTIM_KR phase=" + phase + " year=" + year + " mode=" + m
        + " line_years=" + acc[2] + " real=" + acc[0].tointeger() + " pred=" + acc[1].tointeger()
        + " k=" + k);
  }
  return airChanged;
}

function OpexEstimRecomputeRevenueFactors(lines)
{
  local sums = OpexEstimRevenueSums();
  if (lines != null) {
    foreach (line in lines) {
      if (line == null || !("mode" in line) || !(line.mode in sums)
          || !("estimRevPred" in line) || line.estimRevPred <= 0) continue;
      sums[line.mode][0] += line.estimRevReal.tofloat();
      sums[line.mode][1] += line.estimRevPred.tofloat();
      sums[line.mode][2] += line.estimRevN;
    }
  }
  OpexEstimPublishRevenueFactors(sums, AIDate.GetYear(AIDate.GetCurrentDate()), "reload");
}

/* Profit calibre des scores : OpexC70Profit, ou OpexEstimProfit sous estim_unifie bit 1. */
OpexCalibratedProfit <- OpexC70Profit;

function OpexProjectScore(value, cost)
{
  if (value <= 0 || cost <= 0) return 0.0;
  return (value.tofloat() * 1000.0) / cost;
}
