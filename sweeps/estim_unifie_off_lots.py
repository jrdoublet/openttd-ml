"""Reviewed inverse source patches for the four opt-in ESTIM-1 lots.

Only ESTIM-1 changes made since HEAD belong in this table. The diff is frozen
explicitly with ``python sweeps/estim_unifie_off_lots.py --refresh`` AFTER a
source review; never derive an OFF projection from HEAD at test/runtime.
The mapping is strict: a missing, duplicated or partly applied hunk is an error.
Other opt-in edits, including dist_bornes_unified, survive unchanged.
"""

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BEGIN = "# BEGIN REVIEWED ESTIM-1 SOURCE DIFF\n"
END = "# END REVIEWED ESTIM-1 SOURCE DIFF\n"
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
FILE_RE = re.compile(r"^diff --git a/ai/OpexAI/(\S+) b/ai/OpexAI/\1$")
ESTIM_FILES = {
    "air_catalog_c121.nut", "air_economics_c121.nut", "air_engine_choice.nut",
    "air_fleet.nut", "air_route_economics.nut", "air_trip.nut",
    "candidates.nut", "economy.nut", "globals_pre.nut", "info.nut",
    "persist.nut", "projects_builders.nut", "projects_finance.nut",
    "projects_models.nut", "projects_selection.nut", "settings.nut",
    "task_air.nut", "task_rail.nut", "task_report.nut", "task_road.nut",
    "task_v249.nut", "task_v252.nut", "task_v257.nut", "task_v259.nut",
    "task_v284.nut",
    "task_water.nut",
}
# Contiguous edits with no ESTIM symbol, manually reviewed as part of bit 4.
# Every future unmarked edit must be reviewed before refreshing the frozen map.
REVIEWED_UNMARKED = {
    "task_v249.nut": {
        "local bestProject = null;", "local townModeRevenues = {};",
        "local cargoModeRevenues = {};", "bestProject = statueProject;",
    },
    "task_v257.nut": {
        "local selectedScore = 0;",
        "local currentPlan = null;\nlocal targetPlan = null;",
        "currentPlan = current;\ntargetPlan = target;",
    },
    "task_v284.nut": {
        "function OpexV284Equipment(line, vehicle, wagon, number, add = false, waiting = 0, kDec = -1)",
        "|| AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cashNeed) {",
    },
}


def _parse_patches(patch):
    """Get (new source, HEAD source) hunks; include unified context as guards."""
    mapping = {}
    name = None
    hunk = None
    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git "):
            match = FILE_RE.match(line.rstrip("\n"))
            if match is None or match.group(1) not in ESTIM_FILES:
                raise AssertionError(f"ESTIM-1 unexpected diff path: {line.strip()}")
            name = match.group(1)
            if name in mapping:
                raise AssertionError(f"ESTIM-1 duplicate diff file: {name}")
            mapping[name] = []
            hunk = None
        elif line.startswith("@@ "):
            match = HUNK_RE.match(line)
            if not match or name is None:
                raise AssertionError(f"ESTIM-1 malformed hunk: {line.strip()}")
            hunk = [[], []]  # guarded source, historical source
            mapping[name].append(hunk)
        elif hunk is not None:
            if line.startswith("+"):
                hunk[0].append(line[1:])
            elif line.startswith("-"):
                hunk[1].append(line[1:])
            elif line.startswith(" "):
                hunk[0].append(line[1:])
                hunk[1].append(line[1:])
            elif not line.startswith("\\ No newline at end of file"):
                raise AssertionError(f"ESTIM-1 malformed diff body: {line.strip()}")
    if not mapping or any(not hunks for hunks in mapping.values()):
        raise AssertionError("ESTIM-1 empty source patch")
    return {name: [("".join(new), "".join(old)) for new, old in hunks]
            for name, hunks in mapping.items()}


def _unique_location(code, snippet, name, index):
    if not snippet:
        raise AssertionError(f"ESTIM-1 {name} hunk {index}: empty matching anchor")
    found = code.find(snippet)
    if found < 0:
        return -1
    if code.find(snippet, found + 1) >= 0:
        raise AssertionError(f"ESTIM-1 {name} hunk {index}: non-unique anchor")
    return found


def estim_off(name, code):
    """Remove only the frozen ESTIM changes, retaining every other source edit."""
    hunks = PATCHES.get(name)
    if hunks is None:
        return code
    states = []
    for index, (guarded, old) in enumerate(hunks):
        on_at = _unique_location(code, guarded, name, index)
        off_at = _unique_location(code, old, name, index)
        if (on_at >= 0) == (off_at >= 0):
            raise AssertionError(f"ESTIM-1 {name} hunk {index}: missing/ambiguous source")
        states.append(on_at >= 0)
    if any(states) and not all(states):
        raise AssertionError(f"ESTIM-1 {name}: partial OFF projection")
    if not any(states):
        return code
    # Hunk guards contain unchanged context. Apply in descending source order
    # so offsets remain valid, and check each guard immediately before replacement.
    positions = [(_unique_location(code, guarded, name, i), guarded, old)
                 for i, (guarded, old) in enumerate(hunks)]
    for pos, guarded, old in sorted(positions, reverse=True):
        assert code[pos:pos + len(guarded)] == guarded
        code = code[:pos] + old + code[pos + len(guarded):]
    return code


def estim_off_bytes(name, raw):
    return estim_off(name, raw.decode("utf-8")).encode("utf-8")


def unmarked_change_groups(patch):
    """Review hints: newly changed groups without an obvious ESTIM identifier."""
    name = None
    change = []
    markers = ("ESTIM_UNIFIE", "OpexEstim", "estim_unifie", "ESTIM-1", "estimMarginal")
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            match = FILE_RE.match(line)
            if change and not any(m in s for s in change for m in markers):
                yield name, change
            change = []
            name = match.group(1) if match else None
        elif line.startswith("@@ ") or line.startswith(" "):
            if change and not any(m in s for s in change for m in markers):
                yield name, change
            change = []
        elif line.startswith("+") and not line.startswith("+++"):
            change.append(line[1:])
    if change and not any(m in s for s in change for m in markers):
        yield name, change


def _reviewable_diff():
    patch = _working_source_diff()
    # All modified paths must be in the reviewed allowlist. Each path also
    # needs an ESTIM marker; inspect its complete diff before final refresh.
    mapping = _parse_patches(patch)
    for name, hunks in mapping.items():
        additions = "\n".join(on for on, off in hunks)
        if not any(s in additions for s in ("ESTIM_UNIFIE", "OpexEstim", "estim_unifie", "ESTIM-1")):
            raise AssertionError(f"ESTIM-1 {name}: change lacks the opt-in marker")
    for name, added in unmarked_change_groups(patch):
        code = "\n".join(line.strip() for line in added)
        if code not in REVIEWED_UNMARKED.get(name, set()):
            raise AssertionError(f"ESTIM-1 unreviewed change in {name}: {code!r}")
    return patch


def _working_source_diff():
    result = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--no-color", "--unified=6", "HEAD", "--", "ai/OpexAI"],
        cwd=ROOT, check=True, capture_output=True)
    return result.stdout.decode("utf-8")


def refresh_reviewed_patch():
    """Manual snapshot; only call on instruction at a stable source revision."""
    patch = _reviewable_diff()
    path = Path(__file__)
    code = path.read_text(encoding="utf-8")
    begin = code.index(BEGIN) + len(BEGIN)
    end = code.index(END, begin)
    if '\"\"\"' in patch:
        raise AssertionError("Source diff contains Python triple-quote delimiter")
    updated = code[:begin] + 'PATCH_TEXT = r"""\n' + patch + '"""\n' + code[end:]
    path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"ESTIM-1 mapping refreshed: {len(_parse_patches(patch))} .nut files")


# BEGIN REVIEWED ESTIM-1 SOURCE DIFF
PATCH_TEXT = r"""
diff --git a/ai/OpexAI/air_catalog_c121.nut b/ai/OpexAI/air_catalog_c121.nut
--- a/ai/OpexAI/air_catalog_c121.nut
+++ b/ai/OpexAI/air_catalog_c121.nut
@@ -260,10 +260,18 @@
   result.c121ActualEconomics <- actual;
   result.c121MarginalProfit <- (next != null && actual != null)
       ? next.profitAnnual - actual.profitAnnual : 0;
   result.c121MarginalRevenue <- (next != null && actual != null)
       ? next.revenueAnnual - actual.revenueAnnual : 0;
+  if ((ESTIM_UNIFIE & 4) != 0 && next != null && actual != null) {
+    /* Le modele physique C121 fournit des deltas bruts persistables, au palier
+     * n -> n+1 reellement construit. Aucun historique V161/C70 dans ces champs. */
+    result.estimMarginalRawRevenue <- next.rawRevenueAnnual - actual.rawRevenueAnnual;
+    result.estimMarginalRunning <- next.runningAnnual - actual.runningAnnual;
+    result.estimMarginalAmort <- next.vehicleAmortAnnual - actual.vehicleAmortAnnual;
+    result.estimMarginalBaseVehicles <- actualN;
+  }
   result.c121EvalTicks <- tick1 - tick0;
   result.c121EvalOps <- OpexAirCalcDeltaOps(tick0, ops0);
 }
 
 function OpexC121AttachLineShadow(line, lineId, plan, result)
@@ -284,10 +292,16 @@
    * relisent pas ces tables apres le build ; conserver uniquement les scalaires
    * necessaires au probe maintient la telemetry et un graphe de sauvegarde plat. */
   line.c121Arm <- ("arm" in plan) ? plan.arm : "unknown";
   line.c121MarginalProfit <- ("c121MarginalProfit" in result) ? result.c121MarginalProfit : 0;
   line.c121MarginalRevenue <- ("c121MarginalRevenue" in result) ? result.c121MarginalRevenue : 0;
+  if ((ESTIM_UNIFIE & 4) != 0 && ("estimMarginalRawRevenue" in result)) {
+    line.estimMarginalRawRevenue <- result.estimMarginalRawRevenue;
+    line.estimMarginalRunning <- result.estimMarginalRunning;
+    line.estimMarginalAmort <- result.estimMarginalAmort;
+    line.estimMarginalBaseVehicles <- result.estimMarginalBaseVehicles;
+  }
   /* 0 = aucune marge reelle encore observee. Le cold-start physique reste
    * disponible dans c121Marginal*, mais la premiere observation complete le
    * remplace ; seules les observations reelles suivantes sont moyennees. */
   line.c121MarginalSamples <- 0;
   if (actual != null) {
diff --git a/ai/OpexAI/air_economics_c121.nut b/ai/OpexAI/air_economics_c121.nut
--- a/ai/OpexAI/air_economics_c121.nut
+++ b/ai/OpexAI/air_economics_c121.nut
@@ -381,11 +381,11 @@
 {
   if (rawMonthly <= 0 || servicePickupRate <= 0.0 || serviceCargoRate <= 0.0) return 0.0;
   local runwayScale = 1.0;
   if (runwayRate > 0.0 && servicePickupRate > runwayRate) runwayScale = runwayRate / servicePickupRate;
   local allocated = OpexC121StationAllocatedMonthly(rawMonthly, currentRating, competition);
-  local capacityMonthly = serviceCargoRate * runwayScale * 30.4;
+  local capacityMonthly = serviceCargoRate * runwayScale * OpexEstimMonthDays(30.4);
   return allocated < capacityMonthly ? allocated : capacityMonthly;
 }
 
 /* C121 : points de rating OpenTTD calculables avant construction.
  * Aucune ancre STATION_RATING_PCT n'entre ici. */
@@ -468,11 +468,11 @@
    * Eviter ici la table `seen` supprime une allocation/hash dans le coeur du
    * scan flotte (jusqu'a quatre ratings par N). */
   for (local iter = 0; iter < 8; iter++) {
     local offered = capturableMonthly > 0
         ? capturableMonthly * rating.tofloat() / 255.0 : 0.0;
-    local waitingUpper = offered * headwayDays / 30.4;
+    local waitingUpper = offered * headwayDays / OpexEstimMonthDays(30.4);
     /* OpenTTD 15.3 note le stock via ge->max_waiting_cargo = waiting_avg.
      * Meme en distribution manuelle, num_dests + 1 vaut au moins 2 :
      * waiting_avg <= waiting / 2. Garder waitingUpper pour savoir si une
      * visite vide physiquement la gare, mais appliquer au rating la borne
      * source waiting/2 plutot que le stock accumule sur tout le headway. */
@@ -486,11 +486,11 @@
     if (previous != null && target == previous) {
       cycled = true;
       /* Si les paliers oscillent autour de la saturation, la note moyenne est
        * imposee par la conservation du flux : production offerte = capacite. */
       if (capturableMonthly > 0 && headwayDays > 0 && capacityPerVisit > 0) {
-        rating = (capacityPerVisit * 30.4 * 255.0
+        rating = (capacityPerVisit * OpexEstimMonthDays(30.4) * 255.0
             / (capturableMonthly * headwayDays)).tointeger();
         if (rating < 0) rating = 0;
         if (rating > 255) rating = 255;
       } else if (target < rating) {
         rating = target;
@@ -500,11 +500,11 @@
     previous = rating;
     rating = target;
   }
   local offered = capturableMonthly > 0
       ? capturableMonthly * rating.tofloat() / 255.0 : 0.0;
-  local waitingUpper = offered * headwayDays / 30.4;
+  local waitingUpper = offered * headwayDays / OpexEstimMonthDays(30.4);
   if (pointsOnly) return rating;
   return {
     points = rating, offered = offered, waitingUpper = waitingUpper,
     ratingWaiting = waitingUpper / 2.0, cycled = cycled
   };
@@ -517,17 +517,17 @@
  * Pas de borne globale historique ni de cadence copiee d'un autre AI. */
 function OpexC121AirFleetScanCap(plan, roundTripDays, paxCapacity, mailCapacity)
 {
   if (plan == null || !("c121Demand" in plan) || roundTripDays <= 0 || paxCapacity <= 0) return 1;
   local demand = plan.c121Demand;
-  local paxPerPlaneDirection = paxCapacity * 30.4 / roundTripDays;
+  local paxPerPlaneDirection = paxCapacity * OpexEstimMonthDays(30.4) / roundTripDays;
   local maxPax = demand.paxA > demand.paxB ? demand.paxA : demand.paxB;
   local cap = OpexCeilDiv(maxPax, paxPerPlaneDirection);
   local frequencyPlanes = OpexCeilDiv(roundTripDays, 7.5);
   if (frequencyPlanes > cap) cap = frequencyPlanes;
   if (mailCapacity > 0) {
-    local mailPerPlaneDirection = mailCapacity * 30.4 / roundTripDays;
+    local mailPerPlaneDirection = mailCapacity * OpexEstimMonthDays(30.4) / roundTripDays;
     local maxMail = demand.mailA > demand.mailB ? demand.mailA : demand.mailB;
     local mailPlanes = OpexCeilDiv(maxMail, mailPerPlaneDirection);
     if (mailPlanes > cap) cap = mailPlanes;
   }
   return cap > 0 ? cap : 1;
@@ -711,11 +711,11 @@
     local offeredMailB = stationMailB * routeShareMailB;
     /* La capacite physique doit employer la cadence effectivement admise par
      * les deux pistes, pas la cadence demandee par N avions. Sinon le cap FTA
      * reduit le rating/partage mais laisse encore transporter du cargo sur des
      * rotations qui ne peuvent pas avoir lieu. */
-    local departuresPerDirectionMonth = 30.4 * candidatePickupRate;
+    local departuresPerDirectionMonth = OpexEstimMonthDays(30.4) * candidatePickupRate;
     local paxDirectionCapacity = paxCapacity.tofloat() * departuresPerDirectionMonth;
     local mailDirectionCapacity = useMail ? mailCapacity.tofloat() * departuresPerDirectionMonth : 0.0;
     local carriedPaxA = (offeredPaxA < paxDirectionCapacity ? offeredPaxA : paxDirectionCapacity).tointeger();
     local carriedPaxB = (offeredPaxB < paxDirectionCapacity ? offeredPaxB : paxDirectionCapacity).tointeger();
     local carriedMailA = (offeredMailA < mailDirectionCapacity ? offeredMailA : mailDirectionCapacity).tointeger();
@@ -727,23 +727,23 @@
      * congestion de piste peut aussi reduire leur debit. Comparer le trafic
      * existant avant le candidat a ce qu'il lui reste apres partage, puis
      * valoriser la perte au revenu moyen par unite DES lignes du hub. */
     local existingPaxAfterA = stationPaxA * (1.0 - routeSharePaxA);
     local existingPaxAfterB = stationPaxB * (1.0 - routeSharePaxB);
-    local existingPaxCapacityA = existingPaxRateA * 30.4;
-    local existingPaxCapacityB = existingPaxRateB * 30.4;
+    local existingPaxCapacityA = existingPaxRateA * OpexEstimMonthDays(30.4);
+    local existingPaxCapacityB = existingPaxRateB * OpexEstimMonthDays(30.4);
     if (existingPaxAfterA > existingPaxCapacityA) existingPaxAfterA = existingPaxCapacityA;
     if (existingPaxAfterB > existingPaxCapacityB) existingPaxAfterB = existingPaxCapacityB;
     local lostPaxA = existingPaxBeforeA > existingPaxAfterA ? existingPaxBeforeA - existingPaxAfterA : 0.0;
     local lostPaxB = existingPaxBeforeB > existingPaxAfterB ? existingPaxBeforeB - existingPaxAfterB : 0.0;
     local existingMailAfterA = existingMailBeforeA;
     local existingMailAfterB = existingMailBeforeB;
     if (useMail) {
       existingMailAfterA = stationMailA * (1.0 - routeShareMailA);
       existingMailAfterB = stationMailB * (1.0 - routeShareMailB);
-      local existingMailCapacityA = existingMailRateA * 30.4;
-      local existingMailCapacityB = existingMailRateB * 30.4;
+      local existingMailCapacityA = existingMailRateA * OpexEstimMonthDays(30.4);
+      local existingMailCapacityB = existingMailRateB * OpexEstimMonthDays(30.4);
       if (existingMailAfterA > existingMailCapacityA) existingMailAfterA = existingMailCapacityA;
       if (existingMailAfterB > existingMailCapacityB) existingMailAfterB = existingMailCapacityB;
     }
     local lostMailA = existingMailBeforeA > existingMailAfterA ? existingMailBeforeA - existingMailAfterA : 0.0;
     local lostMailB = existingMailBeforeB > existingMailAfterB ? existingMailBeforeB - existingMailAfterB : 0.0;
@@ -1276,34 +1276,34 @@
       mailRawB, mailRatingPointsB, ("mailCompetitionB" in demand) ? demand.mailCompetitionB : null) : 0.0;
   local offeredPaxA = stationPaxA * routeSharePaxA;
   local offeredPaxB = stationPaxB * routeSharePaxB;
   local offeredMailA = stationMailA * routeShareMailA;
   local offeredMailB = stationMailB * routeShareMailB;
-  local departuresPerDirectionMonth = 30.4 * candidatePickupRate;
+  local departuresPerDirectionMonth = OpexEstimMonthDays(30.4) * candidatePickupRate;
   local paxDirectionCapacity = paxCapacity.tofloat() * departuresPerDirectionMonth;
   local mailDirectionCapacity = useMail ? mailCapacity.tofloat() * departuresPerDirectionMonth : 0.0;
   local carriedPaxA = (offeredPaxA < paxDirectionCapacity ? offeredPaxA : paxDirectionCapacity).tointeger();
   local carriedPaxB = (offeredPaxB < paxDirectionCapacity ? offeredPaxB : paxDirectionCapacity).tointeger();
   local carriedMailA = (offeredMailA < mailDirectionCapacity ? offeredMailA : mailDirectionCapacity).tointeger();
   local carriedMailB = (offeredMailB < mailDirectionCapacity ? offeredMailB : mailDirectionCapacity).tointeger();
   local carriedPax = carriedPaxA + carriedPaxB;
   local carriedMail = carriedMailA + carriedMailB;
   local existingPaxAfterA = stationPaxA * (1.0 - routeSharePaxA);
   local existingPaxAfterB = stationPaxB * (1.0 - routeSharePaxB);
-  local existingPaxCapacityA = existingPaxRateA * 30.4;
-  local existingPaxCapacityB = existingPaxRateB * 30.4;
+  local existingPaxCapacityA = existingPaxRateA * OpexEstimMonthDays(30.4);
+  local existingPaxCapacityB = existingPaxRateB * OpexEstimMonthDays(30.4);
   if (existingPaxAfterA > existingPaxCapacityA) existingPaxAfterA = existingPaxCapacityA;
   if (existingPaxAfterB > existingPaxCapacityB) existingPaxAfterB = existingPaxCapacityB;
   local lostPaxA = existingPaxBeforeA > existingPaxAfterA ? existingPaxBeforeA - existingPaxAfterA : 0.0;
   local lostPaxB = existingPaxBeforeB > existingPaxAfterB ? existingPaxBeforeB - existingPaxAfterB : 0.0;
   local existingMailAfterA = existingMailBeforeA;
   local existingMailAfterB = existingMailBeforeB;
   if (useMail) {
     existingMailAfterA = stationMailA * (1.0 - routeShareMailA);
     existingMailAfterB = stationMailB * (1.0 - routeShareMailB);
-    local existingMailCapacityA = existingMailRateA * 30.4;
-    local existingMailCapacityB = existingMailRateB * 30.4;
+    local existingMailCapacityA = existingMailRateA * OpexEstimMonthDays(30.4);
+    local existingMailCapacityB = existingMailRateB * OpexEstimMonthDays(30.4);
     if (existingMailAfterA > existingMailCapacityA) existingMailAfterA = existingMailCapacityA;
     if (existingMailAfterB > existingMailCapacityB) existingMailAfterB = existingMailCapacityB;
   }
   local lostMailA = existingMailBeforeA > existingMailAfterA ? existingMailBeforeA - existingMailAfterA : 0.0;
   local lostMailB = existingMailBeforeB > existingMailAfterB ? existingMailBeforeB - existingMailAfterB : 0.0;
@@ -1521,11 +1521,11 @@
   }
   if (paxCapacity <= 0) return null;
   local mailIncome = engineContext != null ? engineContext.mailIncome
       : (useMail ? AICargo.GetCargoIncome(catalog.mailCargo, st.paymentDistance, incomeDays) : 0);
   if (useMail && mailIncome < 0) return null;
-  local departuresPerDirectionMonth = 30.4 / trip.roundTripDays;
+  local departuresPerDirectionMonth = OpexEstimMonthDays(30.4) / trip.roundTripDays;
   local paxDirectionCapacity = paxCapacity.tofloat() * departuresPerDirectionMonth;
   local paxUpperA = st.paxRawA.tofloat() < paxDirectionCapacity ? st.paxRawA.tofloat() : paxDirectionCapacity;
   local paxUpperB = st.paxRawB.tofloat() < paxDirectionCapacity ? st.paxRawB.tofloat() : paxDirectionCapacity;
   local mailUpperA = 0.0;
   local mailUpperB = 0.0;
diff --git a/ai/OpexAI/air_engine_choice.nut b/ai/OpexAI/air_engine_choice.nut
--- a/ai/OpexAI/air_engine_choice.nut
+++ b/ai/OpexAI/air_engine_choice.nut
@@ -6,10 +6,18 @@
   if (bestPlan == null) return true;
   local planEconomics = (("decisionEconomics" in plan) && plan.decisionEconomics != null)
       ? plan.decisionEconomics : plan.economics;
   local bestEconomics = (("decisionEconomics" in bestPlan) && bestPlan.decisionEconomics != null)
       ? bestPlan.decisionEconomics : bestPlan.economics;
+  if ((ESTIM_UNIFIE & 8) != 0) {
+    /* Le classement d'un appareil utilise la meme convention de rendement que
+     * le portefeuille; aucune bande de preference ROI de 25 %. */
+    local planScore = OpexProjectScore(planEconomics.profitAnnual, planEconomics.capital);
+    local bestScore = OpexProjectScore(bestEconomics.profitAnnual, bestEconomics.capital);
+    return planScore != bestScore ? planScore > bestScore
+        : planEconomics.profitAnnual > bestEconomics.profitAnnual;
+  }
   /* Arbitrage ROI vs Volume : si un plan offre un ROI significativement superieur (>25% d'ecart),
    * il deploie le capital plus vite et permet de batir plus de lignes. */
   if (planEconomics.roi > (bestEconomics.roi * 1.25).tointeger()) return true;
   if (bestEconomics.roi > (planEconomics.roi * 1.25).tointeger()) return false;
   return planEconomics.profitAnnual > bestEconomics.profitAnnual;
diff --git a/ai/OpexAI/air_fleet.nut b/ai/OpexAI/air_fleet.nut
--- a/ai/OpexAI/air_fleet.nut
+++ b/ai/OpexAI/air_fleet.nut
@@ -119,10 +119,12 @@
   }
 
   local price = AIEngine.GetPrice(targetEngine);
   if (price <= 0) { result.reason = "PRICE"; return result; }
   local need = price + 1000;
+  if ((ESTIM_UNIFIE & 2) != 0)
+    need = OpexEstimFinanceCapital("fleet", price, 0);
   local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
   if (money < need) {
     if (money < need) {
       result.reason = "CASH"; return result;
     }
diff --git a/ai/OpexAI/air_route_economics.nut b/ai/OpexAI/air_route_economics.nut
--- a/ai/OpexAI/air_route_economics.nut
+++ b/ai/OpexAI/air_route_economics.nut
@@ -55,10 +55,11 @@
    * 2026-09-02 (defaut 1) : mesure NEUTRE, adopte pour la justesse -- voir main.nut. */
   local extraMargin = 0;
   if (maxCapital > 0) {
     extraMargin = ((newAirportCount == 2) ? 30000 : (newAirportCount == 1 ? 12000 : 2000)) - 2000;
   }
+  if ((ESTIM_UNIFIE & 2) != 0) extraMargin = 0;
 
   local firstPlanes = fixedPlanes > 0 ? fixedPlanes : 1;
   for (local planes = firstPlanes; planes <= targetPlanes; planes++) {
     local capital = newAirportCount * airport.price + planes * plane.price;
     if (maxCapital > 0 && capital + extraMargin > maxCapital) break;
diff --git a/ai/OpexAI/air_trip.nut b/ai/OpexAI/air_trip.nut
--- a/ai/OpexAI/air_trip.nut
+++ b/ai/OpexAI/air_trip.nut
@@ -62,11 +62,11 @@
     airportDelayDays = OpexC100AirManeuverDays(engineId, airportType, airportType);
   }
   local oneWayDays = flightDays + airportDelayDays;
   if (oneWayDays < 1.0) oneWayDays = 1.0;
   local roundTripDays = 2.0 * oneWayDays;
-  local tripsPerMonth = 30.4 / oneWayDays;
+  local tripsPerMonth = OpexEstimMonthDays(30.4) / oneWayDays;
   return {
     effectiveSpeed = effectiveSpeed, flightDays = flightDays,
     airportDelayDays = airportDelayDays, oneWayDays = oneWayDays,
     roundTripDays = roundTripDays, tripsPerMonth = tripsPerMonth,
     capacityPerPlane = capacity * tripsPerMonth,
diff --git a/ai/OpexAI/candidates.nut b/ai/OpexAI/candidates.nut
--- a/ai/OpexAI/candidates.nut
+++ b/ai/OpexAI/candidates.nut
@@ -1220,10 +1220,13 @@
   }
   local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
   for (local i = 0; i < n; i++) {
     local p = AITown.GetLastMonthProduction(towns[i].id, cargo);
     if (p <= 0 && towns[i].pop > 0) p = (towns[i].pop * 22) / 100;
+    if ((ESTIM_UNIFIE & 8) != 0 && !OpexOriginServed(lines, towns[i].tile, true))
+      p = OpexEstimRivalAvailableMonthly(p,
+          AITown.GetLastMonthTransportedPercentage(towns[i].id, cargo));
     produced.append(p);
     local service = OpexOriginService(lines, towns[i].tile);
     served.append(service);
     if (service != null) stats.townsServed++; else stats.townsUnserved++;
   }
@@ -1232,10 +1235,13 @@
   if (hasMail) {
     mailProduced = [];
     for (local i = 0; i < n; i++) {
       local mp = AITown.GetLastMonthProduction(towns[i].id, catalog.mailCargo);
       if (mp < 0) mp = 0;
+      if ((ESTIM_UNIFIE & 8) != 0 && !OpexOriginServed(lines, towns[i].tile, true))
+        mp = OpexEstimRivalAvailableMonthly(mp,
+            AITown.GetLastMonthTransportedPercentage(towns[i].id, catalog.mailCargo));
       mailProduced.append(mp);
     }
   }
   if (profile != null) profile.paxPreparationOps += OpexOpsMeasureEnd(preparationMark);
   local pairTotalMark = profile != null ? OpexOpsMeasureBegin() : null;
@@ -1399,10 +1405,13 @@
     foreach (si in sources) {
       local source = industries[si];
       if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
       local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
       local ss = served[si];
+      if ((ESTIM_UNIFIE & 8) != 0 && ss == null)
+        monthly = OpexEstimRivalAvailableMonthly(monthly,
+            AIIndustry.GetLastMonthTransportedPercentage(source.id, cargo));
       local longGood = V233_LONG_GOOD > 0 ? OpexV233LSource(source, cargo, lines) : null;
       local others2 = null;
       local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
       for (local k = 0; k < sinks.len(); k++) {
         if (longGood != null) continue;
@@ -1959,10 +1968,13 @@
         continue;
       }
       local source = industries[si];
       if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
       local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
+      if ((ESTIM_UNIFIE & 8) != 0 && !OpexOriginServed(lines, source.tile, true))
+        monthly = OpexEstimRivalAvailableMonthly(monthly,
+            AIIndustry.GetLastMonthTransportedPercentage(source.id, cargo));
       if (monthly <= 0) { stats.noMonthly++; continue; }
 
       local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
       for (local k = 0; k < sinks.len(); k++) {
         local di = sinks[k];
@@ -2183,10 +2195,13 @@
   if (sourceIndex < 0 || sourceIndex >= s.catalog.industries.len()) return;
   local source = s.catalog.industries[sourceIndex];
   if (OpexOriginServed(s.lines, source.tile, true)) return;
   if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) return;
   local monthly = AIIndustry.GetLastMonthProduction(source.id, s.cargo);
+  if ((ESTIM_UNIFIE & 8) != 0)
+    monthly = OpexEstimRivalAvailableMonthly(monthly,
+        AIIndustry.GetLastMonthTransportedPercentage(source.id, s.cargo));
   if (monthly <= 0) { s.stats.noMonthly++; return; }
   local dest = s.destinations[index % s.destinations.len()];
   local dstTile, dstTown = -1, pairKey, isTransformer = false;
   if (dest.kind == "industry") {
     if (dest.industryIndex < 0 || dest.industryIndex >= s.catalog.industries.len()
diff --git a/ai/OpexAI/economy.nut b/ai/OpexAI/economy.nut
--- a/ai/OpexAI/economy.nut
+++ b/ai/OpexAI/economy.nut
@@ -39,10 +39,37 @@
 /* Le constructeur realise une voie simple avec un train, ou deux voies dediees avec deux
  * trains. Le classement ne doit donc pas attribuer du revenu a une flotte qu'il ne construit
  * pas. Les plafonds routiers ont leur propre constante plus bas. */
 const MAX_RAIL_TRAINS = 2;
 
+/* ESTIM-1 lot 4 : primitives physiques communes a tous les modes. Le mois
+ * de planification est une moyenne calendaire; l'ancien 30/30.4 reste sous OFF. */
+function OpexEstimDaysPerMonth()
+{
+  return 365.0 / 12.0;
+}
+
+function OpexEstimMonthDays(legacyDays)
+{
+  return (ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : legacyDays;
+}
+
+function OpexEstimRivalAvailableMonthly(monthly, transportedPercent)
+{
+  if (monthly <= 0) return monthly;
+  if (transportedPercent < 0) return monthly;
+  if (transportedPercent > 100) transportedPercent = 100;
+  return (monthly.tofloat() * (100 - transportedPercent) / 100.0).tointeger();
+}
+
+/* Le chantier ferroviaire realise au plus deux voies dediees. Cette limite
+ * provient du constructeur, et non d'une taille de flotte arbitraire. */
+function OpexEstimRailPhysicalTrainCap()
+{
+  return 2;
+}
+
 /* Duree d'amortissement de l'infrastructure, en annees. Convention deja utilisee par les
  * campagnes (profit_ligne), gardee pour rester comparable. */
 const INFRA_LIFE_YEARS = 30;
 /* D3.2 : Taux d'amortissement de l'infrastructure (100 = defaut historique, 0 = reel OpenTTD, adopte). */
 INFRA_AMORT_PCT <- 0;
@@ -93,11 +120,11 @@
   local legDays = bidirectional ? oneWayDays : roundTripDays;
   if (legDays <= 0) return 0;
   /* 30 / duree, sans plafond : ceil(30 / legDays) etait favorable de 1,20x a 1,63x sur les
    * 155 lignes mesurees (mediane 1,27x). Une fraction est une capacite MENSUELLE moyenne, pas un
    * demi-convoi a construire ; les arrondis ne reviennent qu'au nombre entier de convois. */
-  return 30.0 / legDays;
+  return ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0) / legDays;
 }
 
 /* Le bareme du jeu donne 130 / 95 / 50 / 25 points de ramassage sous 6,8 / 13,5 / 27 / 47 jours
  * (docs/mecanique_jeu.md section 3). STATION_RATING_PCT = 50 a ete calibre sur des lignes dont le
  * headway cible etait 7 jours, donc dans la tranche 95. Les autres facteurs observes a ce regime
@@ -230,11 +257,14 @@
   if (freightSetupDetail) {
     profile.freightEconomicsReferenceOps += OpexOpsMeasureEnd(referenceMark);
     profile.freightEconomicsReferenceCalls++;
   }
   local consistMark = freightSetupDetail ? OpexOpsMeasureBegin() : null;
-  local calibrationOffered = (monthlyUnits * STATION_RATING_PCT) / 100.0;
+  local calibrationRating = STATION_RATING_PCT;
+  if ((ESTIM_UNIFIE & 8) != 0)
+    calibrationRating = OpexStationRatingForHeadway(referenceRoundTripDays / OpexEstimRailPhysicalTrainCap());
+  local calibrationOffered = (monthlyUnits * calibrationRating) / 100.0;
   if (longModel) calibrationOffered /= 2.0; // deux rames partageant le debit observe.
   if (calibrationOffered <= 0) return null;
   local wagons = OpexCeilDiv(calibrationOffered, wagon.capacity * referenceTrips);
   if (wagons < 1) wagons = 1;
   if (wagons > maxWagons) wagons = maxWagons;
@@ -292,11 +322,12 @@
    * Sans place ou sans locomotive pour le total, la ligne reste mono-cargo. */
   local wagon2 = null;
   local wagons2 = 0;
   if (secondary != null && secondary.monthly > 0 && (secondary.cargo in catalog.wagonByCargo)) {
     wagon2 = catalog.wagonByCargo[secondary.cargo];
-    wagons2 = OpexCeilDiv((secondary.monthly * STATION_RATING_PCT) / 100.0, wagon2.capacity * tripsPerMonth);
+    local secondaryRating = (ESTIM_UNIFIE & 8) != 0 ? calibrationRating : STATION_RATING_PCT;
+    wagons2 = OpexCeilDiv((secondary.monthly * secondaryRating) / 100.0, wagon2.capacity * tripsPerMonth);
     if (wagons2 < 1) wagons2 = 1;
     if (wagons + wagons2 > maxWagons) wagons2 = maxWagons - wagons;
     local loco2 = wagons2 > 0 ? choices[wagons + wagons2 - 1] : null;
     if (loco2 == null) {
       wagons2 = 0;
@@ -358,22 +389,23 @@
     }
   }
   local loopMark = profile != null ? OpexOpsMeasureBegin() : null;
   local best = null;
   local startTrains = (longModel || (OpexV190Active() && kind == "freight")) ? 2 : 1;
-  for (local trains = startTrains; trains <= MAX_RAIL_TRAINS; trains++) {
+  local maxTrains = (ESTIM_UNIFIE & 8) != 0 ? OpexEstimRailPhysicalTrainCap() : MAX_RAIL_TRAINS;
+  for (local trains = startTrains; trains <= maxTrains; trains++) {
     local headwayDays = roundTripDays / trains;
     local effectiveHeadway = headwayDays;
     if (kind == "freight") {
       /* D4/D5 (docs/taches.md S0 septentrigesies / S0 quadragesies) :
        * Un convoi de fret charge a 100 % (OF_FULL_LOAD_ANY, builder_rail.nut:1188).
        * Tant que le train charge a quai, time_since_pickup = 0 (130 points de ramassage).
        * La gare n'est vide que pendant le trajet aller-retour moins le temps passe en chargement. */
-      local loadDays = monthlyUnits > 0 ? (perTrain * 30.0) / monthlyUnits : 0;
+      local loadDays = monthlyUnits > 0 ? (perTrain * ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0)) / monthlyUnits : 0;
       /* V163 : OF_FULL_LOAD_ANY part des que l'UN des cargos remplit ses wagons. */
       if (wagon2 != null) {
-        local loadDays2 = (perTrain2 * 30.0) / secondary.monthly;
+        local loadDays2 = (perTrain2 * ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0)) / secondary.monthly;
         if (loadDays2 < loadDays) loadDays = loadDays2;
       }
       local absentDays = roundTripDays - loadDays;
       if (absentDays < 0) absentDays = 0;
       effectiveHeadway = absentDays / trains;
@@ -665,11 +697,14 @@
   local roundTripDays = 2 * oneWayDays;
 
   /* Ce `offered` sert au DIMENSIONNEMENT, comme `calibrationOffered` au rail : la note a plat de
    * calibrage, avant de connaitre la frequence reelle. La demande effective est recalculee plus
    * bas sous pricing_fix, une fois le nombre de vehicules connu. */
-  local offered = (monthlyUnits * STATION_RATING_PCT) / 100;
+  local volumeRating = (ESTIM_UNIFIE & 8) != 0
+      ? OpexStationRatingForHeadway(roundTripDays / OpexRoadPhysicalVehicleCap(1, 1))
+      : STATION_RATING_PCT;
+  local offered = (monthlyUnits * volumeRating) / 100;
   if (offered <= 0) return null;
 
   /* D4 (docs/taches.md S0 quadragesies / S0 trenonagies) :
    * Le dimensionnement routier se fait sur le VOLUME physiquement offert (vehiclesForVolume),
    * et non sur le TARGET_HEADWAY_DAYS ferroviaire (7 jours) qui forcerait 4 a 6 bus sur un
@@ -688,13 +723,15 @@
   local carried = offered < monthlyCapacity ? offered : monthlyCapacity;
   if (kind == "pax" && vehicles > 0 && roundTripDays > 0) {
     /* Flux par rotation : a chaque visite, seulement ce qui s'est accumule pendant le headway,
      * plafonne a la capacite. Deux bus ne doublent pas la demande, ils se partagent le quai. */
     local headwayDays = roundTripDays.tofloat() / vehicles;
-    local waitingOneEnd = (monthlyUnits.tofloat() / 2.0) * headwayDays / 30.0;
+    local waitingOneEnd = (monthlyUnits.tofloat() / 2.0) * headwayDays /
+        ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0);
     local pickup = waitingOneEnd < engine.capacity ? waitingOneEnd : engine.capacity.tofloat();
-    local visitsOneEnd = vehicles.tofloat() * 30.0 / roundTripDays;
+    local visitsOneEnd = vehicles.tofloat() *
+        ((ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0) / roundTripDays;
     local flowCarried = (2.0 * visitsOneEnd * pickup).tointeger();
     if (flowCarried < carried) carried = flowCarried;
   }
   /* OpexLoadedTripsPerMonth est aussi partage par la route. Sa capacite moyenne peut etre
    * fractionnaire depuis la suppression du ceil favorable ; les cargaisons et les panneaux restent
diff --git a/ai/OpexAI/globals_pre.nut b/ai/OpexAI/globals_pre.nut
--- a/ai/OpexAI/globals_pre.nut
+++ b/ai/OpexAI/globals_pre.nut
@@ -362,10 +362,19 @@
 /* C63+C58 : ledger annuel depenses / recettes / occasions. Nul hors sonde. */
 C63_INVEST_PROBE <- false;
 C63_INVEST_LEDGER <- null;
 /* C70 : facteur realise/predit par mode, recalcule au rapport annuel et au rechargement. */
 C70_MODE_FACTOR <- { rail = 1.0, road = 1.0, air = 1.0, water = 1.0 };
+/* ESTIM-1 (estim_unifie, bits par lot, defaut 0). Bit 1 : facteur de realisation de la RECETTE
+ * par mode, applique avant frais et amortissement. A priori = recette realisee / recette brute
+ * predite, annees pleines a flotte de construction, DUEL 40x10 du 21/10
+ * (sweeps/estim_unifie_priors.py ; AIR = moyenne C121 des trois bras) ; WATER sans mesure.
+ * Poids de l'a priori en annees-lignes : Bayes empirique AIR 9, RAIL 36, ROUTE 1 ; une valeur. */
+ESTIM_UNIFIE <- 0;
+ESTIM_K_R_PRIOR <- { rail = 0.92, road = 0.57, air = 0.40, water = 1.0 };
+ESTIM_K_R_PRIOR_WEIGHT <- 10.0;
+ESTIM_K_R <- { rail = 0.92, road = 0.57, air = 0.40, water = 1.0 };
 /* C69 etape 1 : sonde passive goulot de decision P / max(C, F*tau). */
 /* Annee de depart de la compagnie (sauvegardee via _startYear) : base des calculs C69/C75 de F et
  * de tau. 1970 n'est qu'un repli, pose avant Start(). */
 OPEX_START_YEAR <- 1970;
 C69_BOTTLENECK_PROBE <- false;
diff --git a/ai/OpexAI/info.nut b/ai/OpexAI/info.nut
--- a/ai/OpexAI/info.nut
+++ b/ai/OpexAI/info.nut
@@ -208,10 +208,17 @@
       min_value = 0, max_value = 1,
       easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
       default_value = 0, step_size = 1, flags = 0
     });
     AddSetting({
+      name = "estim_unifie",
+      description = "ESTIM-1: unified estimate model; bit 1 = revenue realization, bit 2 = common cash guard, bit 4 = reinforcement/replacement, bit 8 = shared physical primitives; 0 = historical (default)",
+      min_value = 0, max_value = 15,
+      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
+      default_value = 0, step_size = 1, flags = 0
+    });
+    AddSetting({
       name = "dist_bornes_unified",
       description = "DIST-BORNES-1: 1 = one route, passenger rail, freight rail and air candidate distance window shared by all generators, PO01C, V276 and C42; 0 = historical filters (default)",
       min_value = 0, max_value = 1,
       easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
       default_value = 0, step_size = 1, flags = 0
diff --git a/ai/OpexAI/persist.nut b/ai/OpexAI/persist.nut
--- a/ai/OpexAI/persist.nut
+++ b/ai/OpexAI/persist.nut
@@ -965,10 +965,11 @@
   this._pendingLines = null;
   /* C70 : recalcul des facteurs APRES la reconstitution de this._lines. Appele plus haut, il
    * tournait sur la liste encore vide et remettait tous les facteurs a 1 (mesure 2026-09-22). */
   OpexC70RecomputeFactors(this._lines);
   OpexC121RecomputeRealizationFactors(this._lines);
+  if ((ESTIM_UNIFIE & 1) != 0) OpexEstimRecomputeRevenueFactors(this._lines);
 
   local selfComp = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
   foreach (line in this._lines) {
     if (line == null || typeof line != "table") continue;
     if (!("bridges" in line) || line.bridges == null || typeof line.bridges != "array") {
diff --git a/ai/OpexAI/projects_builders.nut b/ai/OpexAI/projects_builders.nut
--- a/ai/OpexAI/projects_builders.nut
+++ b/ai/OpexAI/projects_builders.nut
@@ -67,10 +67,27 @@
""" + " \n" + r"""   local projProfitPerVeh = calibProfit.tofloat() / projVehs.tofloat();
   local modeProfitPerVeh = totalProfit.tofloat() / totalVehs.tofloat();
 
   return projProfitPerVeh < modeProfitPerVeh;
+}
+
+/* ESTIM-1 lot 3 : meme schema comptable pour les lignes neuves et les
+ * operations marginales. L'economie de l'AIR C121 porte deja son propre k_R
+ * sous bit 1, celle des autres modes est corrigee dans OpexEstimProfit. */
+function OpexEstimAttachProjectComponents(project, revenue, running, amort)
+{
+  if (project == null || (ESTIM_UNIFIE & 4) == 0) return;
+  local dR = revenue;
+  if ((ESTIM_UNIFIE & 1) != 0 && project.mode != "air"
+      && project.mode in ESTIM_K_R)
+    dR = (revenue.tofloat() * ESTIM_K_R[project.mode]).tointeger();
+  project.deltaR <- dR;
+  project.deltaE <- running;
+  project.deltaA <- amort;
+  project.deltaC <- project.capital;
+  project.deltaP <- dR - running - amort;
 }
""" + " \n" + r""" function OpexProjectFromCandidate(candidate)
 {
   if (candidate == null || candidate.profitAnnual <= 0 || candidate.revenueAnnual <= 0 ||
@@ -99,10 +116,11 @@
     expectedOps = PROJECT_ROAD_TRANSACTION_OPS;
   } else {
     return null;
   }
   local budgetCapital = candidate.capital + margin;
+  if ((ESTIM_UNIFIE & 2) != 0) budgetCapital = candidate.capital;
   if (("immobilise" in candidate) && candidate.immobilise > 0) {
     budgetCapital += candidate.immobilise;
   }
   local scoreRevenue = candidate.revenueAnnual;
   local project = {
@@ -125,10 +143,12 @@
     project.selectedRoadVehicles <- candidate.trains;
   }
   /* B6 : conserver les composantes de pre-classement comme mesures seulement. */
   project.turnoverBonus <- ("turnoverBonus" in candidate) ? candidate.turnoverBonus : 100;
   project.generationRatio <- ("ratio" in candidate) ? candidate.ratio : 0;
+  OpexEstimAttachProjectComponents(project, candidate.revenueAnnual,
+      candidate.runningAnnual, candidate.amortAnnual);
   return project;
 }
 
 /* C34.2 : un ACHAT D'AVION devient un projet, pour etre arbitre contre les lignes neuves au lieu
  * d'etre servi d'office avant elles (la tache air_fleet passait avant `projects` dans l'ordre de
@@ -140,10 +160,14 @@
  *
  * Sous la cible C121, le score est la marge par avion deja publiee sur la ligne.
  * Sinon le profit realise / avion, puis le repli predRevenue - predRunning. */
 function OpexProjectFromFleet(entry)
 {
+  /* Palier C121 n -> n+1 mesure a la construction ; au-dela, il n'est jamais
+   * recalcule : reprendre alors la marge historique plutot que bloquer la flotte. */
+  if ((ESTIM_UNIFIE & 4) != 0 && OpexEstimFleetStepCurrent(entry))
+    return OpexEstimProjectFromFleet(entry);
   if (entry == null || entry.want <= 0 || entry.planePrice <= 0) return null;
   local line = entry.line;
   local have = ("vehCount" in line && line.vehCount > 0) ? line.vehCount
              : (("vehicles" in line) ? line.vehicles.len() : 0);
   if (have < 1) return null;
@@ -271,10 +295,60 @@
     project.v161Calibrate <- true;
   }
   return project;
 }
 
+/* ESTIM-1 lot 3 : le renfort garde la composante physique n -> n+1 de C121,
+ * recompose sa recette au facteur commun, puis retire exploitation/amortissement.
+ * Un palier devenu perime apres un achat ne peut pas etre rejoue sans nouveau
+ * calcul C121 : on attend alors le prochain chantier physique. */
+function OpexEstimFleetStepCurrent(entry)
+{
+  if (entry == null || entry.line == null) return false;
+  local line = entry.line;
+  local have = ("vehCount" in line) ? line.vehCount
+      : (("vehicles" in line) && line.vehicles != null ? line.vehicles.len() : 0);
+  return have > 0 && ("estimMarginalRawRevenue" in line)
+      && ("estimMarginalBaseVehicles" in line) && line.estimMarginalBaseVehicles == have;
+}
+
+function OpexEstimProjectFromFleet(entry)
+{
+  if (entry == null || entry.line == null || entry.want <= 0 || entry.planePrice <= 0) return null;
+  local line = entry.line;
+  local have = ("vehCount" in line) ? line.vehCount
+      : (("vehicles" in line) && line.vehicles != null ? line.vehicles.len() : 0);
+  if (have <= 0 || !("estimMarginalRawRevenue" in line)
+      || !("estimMarginalRunning" in line) || !("estimMarginalAmort" in line)
+      || !("estimMarginalBaseVehicles" in line)
+      || line.estimMarginalBaseVehicles != have) return null;
+  /* C121 a evalue une unique transition n -> n+1. Ne pas extrapoler la
+   * marge de ce palier a plusieurs avions, car demande et cannibalisation
+   * changent a chaque achat. Le prochain palier sera reevalue apres l'achat. */
+  local tranche = clone entry;
+  tranche.want = 1;
+  local dRaw = line.estimMarginalRawRevenue;
+  local dR = (dRaw.tofloat() * ESTIM_K_R.air).tointeger();
+  local dE = line.estimMarginalRunning;
+  local dA = line.estimMarginalAmort;
+  local dC = entry.planePrice;
+  local dP = dR - dE - dA;
+  if (dR <= 0 || dP <= 0 || dC <= 0) return null;
+  local budget = dC + ((ESTIM_UNIFIE & 2) != 0 ? 0 : 1000);
+  return {
+    mode = "fleet", kind = "fleet", cargo = line.cargo,
+    src = line.stationA, dst = ("stationB" in line) ? line.stationB : line.stationA,
+    payload = tranche, distance = 0, capital = dC, budgetCapital = budget,
+    deltaR = dR, deltaE = dE, deltaA = dA, deltaC = dC, deltaP = dP,
+    revenueAnnual = dR, profitAnnual = dP, estimMarginalModeled = true,
+    roi = (dP * 1000) / dC, expectedOpcodes = PROJECT_ROAD_TRANSACTION_OPS,
+    budgetScore = OpexProjectScore(dR, budget),
+    opcodeScore = OpexProjectScore(dR, PROJECT_ROAD_TRANSACTION_OPS),
+    planningOpcodes = 0, economicsDate = AIDate.GetCurrentDate(),
+  };
+}
+
 /* Marge de caisse AIR selon le nombre d'aeroports neufs. `plan` reste dans la
  * signature : les appelants le passent, il n'est plus lu. */
 function OpexAirRequiredMargin(newAirports, plan = null)
 {
   return (newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000);
@@ -291,14 +365,16 @@
   if (decisionEconomics.profitAnnual <= 0 || decisionEconomics.revenueAnnual <= 0 ||
       decisionEconomics.capital <= 0) return null;
   local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
   local margin = OpexAirRequiredMargin(newAirports, plan);
   local budgetCapital = economics.capital + margin;
+  if ((ESTIM_UNIFIE & 2) != 0) budgetCapital = economics.capital;
   if (("immobilise" in economics) && economics.immobilise > 0) {
     budgetCapital += economics.immobilise;
   }
   local decisionBudgetCapital = decisionEconomics.capital + margin;
+  if ((ESTIM_UNIFIE & 2) != 0) decisionBudgetCapital = decisionEconomics.capital;
   if (("immobilise" in decisionEconomics) && decisionEconomics.immobilise > 0) {
     decisionBudgetCapital += decisionEconomics.immobilise;
   }
   /* La decouverte a deja ete payee pendant l'etape projets. La contrainte d'execution ne porte
    * que sur les opcodes encore necessaires pour construire le projet. */
@@ -315,20 +391,23 @@
     budgetScore = OpexProjectScore(decisionEconomics.revenueAnnual, decisionBudgetCapital),
     opcodeScore = OpexProjectScore(decisionEconomics.revenueAnnual, expectedOps),
     planningOpcodes = planningOps,
     economicsDate = AIDate.GetCurrentDate(),
   };
+  OpexEstimAttachProjectComponents(project, decisionEconomics.revenueAnnual,
+      decisionEconomics.runningAnnual, decisionEconomics.amortAnnual);
   return project;
 }
 
 function OpexProjectFromWater(catalog, plan, planningOps)
 {
   if (plan == null || !("economics" in plan)) return null;
   local economics = plan.economics;
   if (economics.profitAnnual <= 0 || economics.revenueAnnual <= 0 ||
       economics.capital <= 0) return null;
   local budgetCapital = economics.capital + WATER_CAPITAL_MARGIN;
+  if ((ESTIM_UNIFIE & 2) != 0) budgetCapital = economics.capital;
   if (("immobilise" in economics) && economics.immobilise > 0) {
     budgetCapital += economics.immobilise;
   }
   local expectedOps = PROJECT_WATER_TRANSACTION_OPS;
   local project = {
@@ -343,10 +422,12 @@
     planningOpcodes = planningOps,
     /* L'eau est recyclee par OpexIncrementalUpdateProjects : dater son economie
      * permet de mesurer 06.11 au meme titre que rail/route. */
     economicsDate = AIDate.GetCurrentDate(),
   };
+  OpexEstimAttachProjectComponents(project, economics.revenueAnnual,
+      economics.runningAnnual, economics.amortAnnual);
   return project;
 }
 
 /* portfolio_v2 : garde TOUTES les alternatives modales d'un couple origine/destination au lieu
  * d'en elire une avant le test de capital. Motif (docs/taches.md S0 septies, soupcon 1 confirme) :
diff --git a/ai/OpexAI/projects_finance.nut b/ai/OpexAI/projects_finance.nut
--- a/ai/OpexAI/projects_finance.nut
+++ b/ai/OpexAI/projects_finance.nut
@@ -3,13 +3,52 @@
 /* P1 : cout a comparer a la tresorerie mobilisable. budgetCapital reste le
  * cout economique utilise par les scores historiques ; il ne faut pas y injecter
  * un multiplicateur global. Le repli de financabilite applique rail 1,7x et route
  * 1,21x. Si le trace a deja fourni un devis reel, capitalIsActual fait utiliser
  * ce montant. Les marges et le capital immobilise restent inchanges. */
+/* ESTIM-1 M5 : cout de decaissement commun au choix et au chantier, aux facteurs
+ * de financement qualifies du chemin historique. Un devis realise (AITestMode ou plan reel) n'est jamais multiplie de nouveau.
+ * OpexAvailableCapital represente la caisse mobilisable sans reserve. */
+function OpexEstimFinanceCapital(mode, capital, distance, capitalIsActual = false, immobilise = 0)
+{
+  if (capital < 0) capital = 0;
+  if (immobilise < 0) immobilise = 0;
+  local factor = 1.0;
+  if (!capitalIsActual) {
+    /* Facteurs de financement qualifies (decision du 26/09 : rail 100 %, route 121 %).
+     * La majoration de devis rail mesuree n'est pas reintroduite au financement. */
+    if (mode == "rail") factor = RAIL_FINANCE_BIAS_PCT / 100.0;
+    else if (mode == "road") factor = 1.21;
+  }
+  return (capital.tofloat() * factor + 0.999).tointeger() + immobilise;
+}
+
 function OpexProjectFinanceCapital(project)
 {
   if (project == null || !("budgetCapital" in project)) return 0;
+  if ((ESTIM_UNIFIE & 2) != 0) {
+    local mode = ("mode" in project) ? project.mode : "unknown";
+    local capital = ("capital" in project) ? project.capital : project.budgetCapital;
+    if (("deltaC" in project) && project.deltaC > 0) capital = project.deltaC;
+    /* Une ligne AIR doit financer la flotte reellement commandee, pas le devis
+     * a un avion de decisionEconomics. */
+    local immobilise = 0;
+    if (("payload" in project) && project.payload != null) {
+      if (("immobilise" in project.payload)) immobilise = project.payload.immobilise;
+      if (("economics" in project.payload) && project.payload.economics != null
+          && ("immobilise" in project.payload.economics))
+        immobilise = project.payload.economics.immobilise;
+    }
+    local actual = ("capitalIsActual" in project) && project.capitalIsActual;
+    if (!actual && ("payload" in project) && project.payload != null
+        && ("capitalIsActual" in project.payload)) actual = project.payload.capitalIsActual;
+    if (actual && ("payload" in project) && project.payload != null
+        && ("capital" in project.payload) && project.payload.capital > 0)
+      capital = project.payload.capital;
+    local distance = ("distance" in project) ? project.distance : 0;
+    return OpexEstimFinanceCapital(mode, capital, distance, actual, immobilise);
+  }
   local financeCapital = project.budgetCapital;
   if (!("mode" in project)) return financeCapital;
 
   local biasPct = 0;
   if (project.mode == "rail") biasPct = RAIL_FINANCE_BIAS_PCT;
diff --git a/ai/OpexAI/projects_models.nut b/ai/OpexAI/projects_models.nut
--- a/ai/OpexAI/projects_models.nut
+++ b/ai/OpexAI/projects_models.nut
@@ -59,10 +59,13 @@
 /* C121 : le facteur de realisation corrige le revenu brut du modele physique,
  * jamais une prediction deja corrigee. Une pseudo-ligne a 1.0 stabilise les
  * petits echantillons ; sous MIN_LINES on conserve strictement le cold-start. */
 function OpexC121RealizationFactor(plan)
 {
+  /* ESTIM-1 bit 1 : un facteur de recette AIR unique, tous bras, remplace la
+   * realisation directe P0 des hubs et la calibration C70 des paires neuves. */
+  if ((ESTIM_UNIFIE & 1) != 0) return ESTIM_K_R.air;
   /* Les anciens essais r4/r5 appliquaient trop brutalement le facteur appris.
    * Le levier reste separe et ne corrige que les bras reutilisant un hub. */
   if (!C121_AIR_PROJECT_REALIZATION_ADAPTIVE
       || plan == null || !("arm" in plan)) return 1.0;
   local arm = plan.arm;
@@ -157,10 +160,13 @@
 
 /* C70 : profit servant au classement. Le brut reste dans profitAnnual, et donc dans
  * line.predicted : le facteur mesure le modele, jamais sa propre correction. */
 function OpexC70Profit(project)
 {
+  if ((ESTIM_UNIFIE & 4) != 0 && project != null
+      && ("estimMarginalModeled" in project) && project.estimMarginalModeled)
+    return project.profitAnnual;
   /* R2 : une observation n'est pas une prediction a recalibrer. Le marqueur
    * vient de la branche qui a fourni profitAnnual, pas de l'etat actuel de la ligne. */
   if (project != null && ("profitIsObserved" in project) && project.profitIsObserved)
     return project.profitAnnual;
   /* Eviter une seconde calibration C70 apres une correction C121 non neutre. */
@@ -178,11 +184,101 @@
       && OpexC121ProjectHasRealization(project)) return project.profitAnnual;
 
   return project.profitAnnual * OpexC70Factor(project);
 }
 
-/* Profit calibre des scores : OpexC70Profit. */
+/* ESTIM-1 bit 1 : P = P_modele - (1 - k_R) * R. Le facteur corrige la recette, jamais le
+ * profit : un projet a faible marge peut devenir negatif. AIR C121 porte deja k_R dans son
+ * economie (OpexC121RealizationFactor). Flotte et observations : logique historique (lot 3). */
+function OpexEstimProfit(project)
+{
+  if ((ESTIM_UNIFIE & 4) != 0 && project != null
+      && ("estimMarginalModeled" in project) && project.estimMarginalModeled)
+    return project.profitAnnual;
+  if (project == null || !("mode" in project) || !(project.mode in ESTIM_K_R)
+      || (("profitIsObserved" in project) && project.profitIsObserved)
+      || !("revenueAnnual" in project) || project.revenueAnnual <= 0)
+    return OpexC70Profit(project);
+  if (project.mode == "air" && OpexC121ProjectHasRealization(project))
+    return project.profitAnnual;
+  return (project.profitAnnual - (1.0 - ESTIM_K_R[project.mode]) * project.revenueAnnual).tointeger();
+}
+
+/* ESTIM-1 bit 1 : cumul par ligne, annees pleines (age >= 2) a flotte de construction, sans
+ * normalisation par la flotte. Recette predite brute : AIR = recette C121 avant facteur. */
+function OpexEstimAccumulateLine(line, year, vehCount, currentRevenue, sums)
+{
+  local mode = ("mode" in line) ? line.mode : "unknown";
+  if (!(mode in sums)) return;
+  /* Sous bit 1, predRevenue AIR contient deja k_R. Quand le shadow C121 n'a
+   * pas pu fournir la recette brute, ne jamais apprendre sur cette valeur
+   * deja calibree (ce qui ferait artificiellement tendre k_R vers 1). */
+  if (mode == "air" && (!("c121RawRevenueAnnual" in line)
+      || line.c121RawRevenueAnnual <= 0)) return;
+  local age = ("year" in line) ? year - line.year : -1;
+  local n0 = ("trains0" in line) ? line.trains0 : 0;
+  local pred = mode == "air" ? line.c121RawRevenueAnnual
+      : (("predRevenue" in line) ? line.predRevenue : 0);
+  if (age >= 2 && n0 > 0 && vehCount == n0 && pred > 0) {
+    if (!("estimRevPred" in line)) { line.estimRevReal <- 0; line.estimRevPred <- 0; line.estimRevN <- 0; }
+    line.estimRevReal += currentRevenue > 0 ? currentRevenue.tointeger() : 0;
+    line.estimRevPred += pred.tointeger();
+    line.estimRevN++;
+  }
+  if (("estimRevPred" in line) && line.estimRevPred > 0) {
+    sums[mode][0] += line.estimRevReal.tofloat();
+    sums[mode][1] += line.estimRevPred.tofloat();
+    sums[mode][2] += line.estimRevN;
+  }
+}
+
+function OpexEstimRevenueSums()
+{
+  return { rail = [0.0, 0.0, 0], road = [0.0, 0.0, 0], air = [0.0, 0.0, 0], water = [0.0, 0.0, 0] };
+}
+
+/* k = (n * rho + w0 * k0) / (n + w0) : rho rapport des sommes, n annees-lignes. */
+function OpexEstimPublishRevenueFactors(sums, year, phase)
+{
+  local w0 = ESTIM_K_R_PRIOR_WEIGHT;
+  local airChanged = false;
+  foreach (m, acc in sums) {
+    local n = acc[2].tofloat();
+    local k = ESTIM_K_R_PRIOR[m];
+    if (n > 0 && acc[1] > 0) k = (n * acc[0] / acc[1] + w0 * k) / (n + w0);
+    local changed = ESTIM_K_R[m] != k;
+    ESTIM_K_R[m] = k;
+    if (m == "air" && changed) airChanged = true;
+    /* Le catalogue C121 met en cache l'economie par bras : invalider quand k_R AIR change. */
+    if (m == "air" && changed) {
+      foreach (arm in ["newpair", "hubsite", "hubhub"])
+        C121_CATALOG_ARM_LEARN_REV.rawset(arm,
+          (arm in C121_CATALOG_ARM_LEARN_REV ? C121_CATALOG_ARM_LEARN_REV[arm] : 0) + 1);
+    }
+    AILog.Info("ESTIM_KR phase=" + phase + " year=" + year + " mode=" + m
+        + " line_years=" + acc[2] + " real=" + acc[0].tointeger() + " pred=" + acc[1].tointeger()
+        + " k=" + k);
+  }
+  return airChanged;
+}
+
+function OpexEstimRecomputeRevenueFactors(lines)
+{
+  local sums = OpexEstimRevenueSums();
+  if (lines != null) {
+    foreach (line in lines) {
+      if (line == null || !("mode" in line) || !(line.mode in sums)
+          || !("estimRevPred" in line) || line.estimRevPred <= 0) continue;
+      sums[line.mode][0] += line.estimRevReal.tofloat();
+      sums[line.mode][1] += line.estimRevPred.tofloat();
+      sums[line.mode][2] += line.estimRevN;
+    }
+  }
+  OpexEstimPublishRevenueFactors(sums, AIDate.GetYear(AIDate.GetCurrentDate()), "reload");
+}
+
+/* Profit calibre des scores : OpexC70Profit, ou OpexEstimProfit sous estim_unifie bit 1. */
 OpexCalibratedProfit <- OpexC70Profit;
 
 function OpexProjectScore(value, cost)
 {
   if (value <= 0 || cost <= 0) return 0.0;
diff --git a/ai/OpexAI/projects_selection.nut b/ai/OpexAI/projects_selection.nut
--- a/ai/OpexAI/projects_selection.nut
+++ b/ai/OpexAI/projects_selection.nut
@@ -551,10 +551,11 @@
   local line = entry.line;
   if (line == null || (("scrapping" in line) && line.scrapping)) return null;
   local have = ("vehCount" in line) ? line.vehCount : line.vehicles.len();
   if (("baseVehicles" in entry) && have != entry.baseVehicles) return null;
   local purchaseBudget = capitalBudget - 1000; // tampon d'OpexAirAddPlane
+  if ((ESTIM_UNIFIE & 2) != 0) purchaseBudget = capitalBudget;
   if (entry.planePrice <= 0 || entry.want <= 0 || purchaseBudget < entry.planePrice) return null;
   local quantity = (purchaseBudget / entry.planePrice).tointeger();
   if (quantity >= entry.want) return project;
 
   /* Une seule tranche par demande, jamais des +1 concurrents pour la meme ligne.
@@ -564,10 +565,18 @@
   local reduced = clone entry;
   reduced.want = quantity;
   fitted.payload = reduced;
   fitted.capital = quantity * entry.planePrice;
   fitted.budgetCapital = fitted.capital + 1000;
+  if ((ESTIM_UNIFIE & 2) != 0) fitted.budgetCapital = fitted.capital;
+  if ((ESTIM_UNIFIE & 4) != 0 && ("deltaR" in project)) {
+    fitted.deltaR = (project.deltaR / entry.want) * quantity;
+    fitted.deltaE = (project.deltaE / entry.want) * quantity;
+    fitted.deltaA = (project.deltaA / entry.want) * quantity;
+    fitted.deltaC = fitted.capital;
+    fitted.deltaP = fitted.deltaR - fitted.deltaE - fitted.deltaA;
+  }
   fitted.profitAnnual = (project.profitAnnual / entry.want) * quantity;
   fitted.revenueAnnual = (project.revenueAnnual / entry.want) * quantity;
   if (fitted.profitAnnual <= 0) return null;
   fitted.roi = (fitted.profitAnnual * 1000) / fitted.capital;
   fitted.budgetScore = OpexProjectScore(fitted.revenueAnnual, fitted.budgetCapital);
@@ -1364,13 +1373,13 @@
     local cap = OpexProjectFinanceCapital(p);
     if (("mode" in p) && p.mode == "fleet" && ("payload" in p) && p.payload != null
         && ("planePrice" in p.payload) && p.payload.planePrice > 0) {
       local planePrice = p.payload.planePrice;
       local want = ("want" in p.payload) ? p.payload.want : 1;
-      local fitQty = ((capitalBudget - 1000) / planePrice).tointeger();
+      local fitQty = ((capitalBudget - ((ESTIM_UNIFIE & 2) != 0 ? 0 : 1000)) / planePrice).tointeger();
       if (fitQty < 0) fitQty = 0;
-      if (fitQty < want) cap = (fitQty + 1) * planePrice + 1000;
+      if (fitQty < want) cap = (fitQty + 1) * planePrice + ((ESTIM_UNIFIE & 2) != 0 ? 0 : 1000);
     }
     if (cap > capitalBudget && (nextCap < 0 || cap < nextCap)) nextCap = cap;
   }
   stats.nextProjectCapital = nextCap;
   /* minCapital ne sert qu'a expliquer une selection vide. Eviter de
diff --git a/ai/OpexAI/settings.nut b/ai/OpexAI/settings.nut
--- a/ai/OpexAI/settings.nut
+++ b/ai/OpexAI/settings.nut
@@ -97,10 +97,12 @@
   V216A_GHOST_DEMAND = AIController.GetSetting("v216a_ghost_demand");
   V216F_DWELL_PCT = AIController.GetSetting("v216f_dwell_pct");
   local lateRelax = AIController.GetSetting("v269_rail_late_relax");
   DIST_BORNES_V276_FREIGHT = AIController.GetSetting("dist_bornes_v276_freight") == 1;
   DIST_BORNES_UNIFIED = AIController.GetSetting("dist_bornes_unified") == 1;
+  ESTIM_UNIFIE = AIController.GetSetting("estim_unifie");
+  foreach (m, k in ESTIM_K_R_PRIOR) ESTIM_K_R[m] = k;
   local railGrowth = AIController.GetSetting("v284_rail_growth");
   V233_LONG_GOOD = AIController.GetSetting("v233_long_good") == 1 ? 1 : 0;
   V233_SITE_FUNNEL = AIController.GetSetting("v233_site_funnel") == 1 ? 1 : 0;
   V233_FUNNEL_CENTER_TEST = AIController.GetSetting("v233_funnel_center_test") == 0 ? 0 : 1;
   if (railGrowth != null && railGrowth >= 0 && railGrowth <= 10) V284_RAIL_GROWTH = railGrowth;
@@ -303,10 +305,11 @@
     OpexC50ResetNonExpansionLedger();
   }
   C63_INVEST_PROBE = probePort;
   if (C63_INVEST_PROBE) OpexC63ResetLedger();
   ::OpexCalibratedProfit <- OpexC70Profit;
+  if ((ESTIM_UNIFIE & 1) != 0) ::OpexCalibratedProfit <- OpexEstimProfit;
   C69_BOTTLENECK_PROBE = probePort;
   C75_YEAR_LEDGER_SKIP = AIController.GetSetting("c75_year_ledger_skip") == 1;
   C75_BYPASS_LEDGER_SKIP = AIController.GetSetting("c75_bypass_ledger_skip") == 1;
   /* Amorcage plat : sans etapes, chaque regeneration apres chantier prend le
    * chemin incremental C121 au lieu d'un OpexBuildProjects complet synchrone. */
diff --git a/ai/OpexAI/task_air.nut b/ai/OpexAI/task_air.nut
--- a/ai/OpexAI/task_air.nut
+++ b/ai/OpexAI/task_air.nut
@@ -198,10 +198,15 @@
       if (EQUIPMENT_ROI_PROBE) OpexM3ProbeAirEquipment(this._catalog, plan, "portfolio_selected");
       local requiredMargin = OpexAirRequiredMargin(newAirports, buildPlan);
       local capital = ("capital" in buildPlan) ? buildPlan.capital
           : (newAirports * buildPlan.airport.price + buildPlan.plane.price);
       local need = capital + requiredMargin;
+      if ((ESTIM_UNIFIE & 2) != 0) {
+        local immobilise = ("economics" in buildPlan) && buildPlan.economics != null
+            && ("immobilise" in buildPlan.economics) ? buildPlan.economics.immobilise : 0;
+        need = OpexEstimFinanceCapital("air", capital, plan.distance, false, immobilise);
+      }
       if (spCash != null) OpexSpanEnd(spCash);
       if (money < need) {
         if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("air", i, capital, plan.economics.profitAnnual, project.roi, plan.siteA.town.tile, plan.siteB.town.tile, need, money);
         if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
             || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
@@ -649,10 +654,12 @@
     }
     /* Croissance d'une ligne aerienne EXISTANTE : aucun aeroport a batir, donc rien que
      * cette marge doive couvrir. 88 refus insufficient_cash pour 3 acceptations mesures
      * sur 3 parties x 2 ans (results/diag_1v1_decisions.json). */
     local need = planePrice + 2000;
+    if ((ESTIM_UNIFIE & 2) != 0)
+      need = OpexEstimFinanceCapital("fleet", planePrice, 0);
     local addedThisPass = 0;
     local maxAddedPerPass = 4;
     /* C14 : Dimensionnement dynamique de flotte par le stock au sol (AAAHogEx route.nut:2896-2921).
      * Si AIR_FLEET_BUFFER >= 0 : calcule buildNum = (maxWait - bottom) / capacity.
      * Si buildNum < 1 : refus W (pas assez de cargo au sol).
diff --git a/ai/OpexAI/task_rail.nut b/ai/OpexAI/task_rail.nut
--- a/ai/OpexAI/task_rail.nut
+++ b/ai/OpexAI/task_rail.nut
@@ -274,10 +274,14 @@
             || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "rail", src = candidate.src, dst = candidate.dst, reason = "too_close_no_join", extra = "" });
         return { outcome = "rejected", discards = passDiscards };
       }
 
       local need = candidate.capital;
+      if ((ESTIM_UNIFIE & 2) != 0)
+        need = OpexEstimFinanceCapital("rail", candidate.capital, candidate.distance,
+            ("capitalIsActual" in candidate) && candidate.capitalIsActual,
+            ("immobilise" in candidate) ? candidate.immobilise : 0);
       local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
       local lowCash = (money < need);
       /* G3§2 : pour le chemin reprenable sans railPlan, la recherche A* ne coute aucune
        * tresorerie et le cash peut arriver pendant les tranches. On ne saute que le chemin
        * non reprenable (construction immediate). _consumeRailSearch verifiera la caisse a
@@ -1051,10 +1055,14 @@
    * pipeline rail est neutralise (l'echec n'est pas non plus transmis a C22). */
   local planFailed = ("railPlan" in candidate) && candidate.railPlan != null
                      && !candidate.railPlan.ok;
   if (!planFailed) {
     local need = candidate.capital;
+    if ((ESTIM_UNIFIE & 2) != 0)
+      need = OpexEstimFinanceCapital("rail", candidate.capital, candidate.distance,
+          ("capitalIsActual" in candidate) && candidate.capitalIsActual,
+          ("immobilise" in candidate) ? candidate.immobilise : 0);
     local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
     if (money < need) {
       if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("rail", -1, candidate.capital, candidate.profitAnnual, candidate.roi, candidate.src, candidate.dst, need, money);
       /* C41.47 : pendant de la garde G3S1 ci-dessus, applique au motif tresorerie -- des le
        * premier blocage constate, liberer _railSearch pour que _expandRailLines et les AUTRES
@@ -2747,10 +2755,14 @@
 function OpexAI::_revalidateRailStockPlan(candidate, plan)
 {
   if (candidate == null || plan == null) return { ok = false, reason = "null_plan" };
 
   local need = candidate.capital;
+  if ((ESTIM_UNIFIE & 2) != 0)
+    need = OpexEstimFinanceCapital("rail", candidate.capital, candidate.distance,
+        ("capitalIsActual" in candidate) && candidate.capitalIsActual,
+        ("immobilise" in candidate) ? candidate.immobilise : 0);
   local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
   if (money < need) return { ok = false, reason = "cash" };
 
   if (!OpexRailVehicleSlotAvailable()) return { ok = false, reason = "no_vehicle_slot" };
 
diff --git a/ai/OpexAI/task_report.nut b/ai/OpexAI/task_report.nut
--- a/ai/OpexAI/task_report.nut
+++ b/ai/OpexAI/task_report.nut
@@ -211,10 +211,11 @@
 {
   this._purgeUnprofitableStreaks();
   local anchor = AIMap.GetTileIndex(1, 1);
   local c70Sums = { rail = [0.0, 0], road = [0.0, 0], air = [0.0, 0], water = [0.0, 0] };
   local c121RealizationSums = OpexC121RealizationSums();
+  local estimRevSums = (ESTIM_UNIFIE & 1) != 0 ? OpexEstimRevenueSums() : null;
   local c69ProfRatios = C69_BOTTLENECK_PROBE ? { rail = [], road = [], air = [], water = [] } : null;
   local c69RevRatios = C69_BOTTLENECK_PROBE ? { rail = [], road = [], air = [], water = [] } : null;
   local c69LineCounts = C69_BOTTLENECK_PROBE ? { rail = 0, road = 0, air = 0, water = 0 } : null;
   for (local i = 0; i < this._lines.len(); i++) {
     local line = this._lines[i];
@@ -362,10 +363,11 @@
     if (c121RealizationSums != null && ("mode" in line) && line.mode == "air"
         && ("c121Arm" in line) && (line.c121Arm in c121RealizationSums)
         && ("c121RawRevenueAnnual" in line) && line.c121RawRevenueAnnual > 0) {
       OpexC121ObserveLineRealization(line, year, vehCount, currentRevenue, c121RealizationSums);
     }
+    if (estimRevSums != null) OpexEstimAccumulateLine(line, year, vehCount, currentRevenue, estimRevSums);
     if (("mode" in line) && line.mode == "air"
         && ("c121MarginalObserveYear" in line) && year >= line.c121MarginalObserveYear
         && ("c121MarginalBaselineProfit" in line) && ("c121MarginalBaselineRevenue" in line)
         && ("c121MarginalBaselineVehicles" in line) && vehCount > line.c121MarginalBaselineVehicles) {
       OpexC121ObserveLineMarginal(line, year, vehCount, profit, currentRevenue);
@@ -581,10 +583,14 @@
     OpexC70PublishModeFactors(c70Sums, year);
   }
   if (c121RealizationSums != null) {
     OpexC121ApplyRealizationSums(c121RealizationSums, year, "annual");
   }
+  /* Les projets AIR deja construits dans le vivier conservent l'ancien
+   * decisionEconomics : la revision C121 seule ne les recalcule pas. */
+  if (estimRevSums != null && OpexEstimPublishRevenueFactors(estimRevSums, year, "annual"))
+    this._portfolioInvalidated = true;
   if (C69_BOTTLENECK_PROBE && C69_PENDING_FOLLOWUPS != null) {
     foreach (item in C69_PENDING_FOLLOWUPS) {
       OpexC69Log("phase=c3_pending pass=" + item.passId + " passes_waited=" + item.passesWaited
           + " target=" + item.c69Key);
     }
diff --git a/ai/OpexAI/task_road.nut b/ai/OpexAI/task_road.nut
--- a/ai/OpexAI/task_road.nut
+++ b/ai/OpexAI/task_road.nut
@@ -80,10 +80,14 @@
         if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
         return { outcome = "rejected", discards = passDiscards };
       }
 
       local need = candidate.capital + ROAD_CAPITAL_MARGIN;
+      if ((ESTIM_UNIFIE & 2) != 0)
+        need = OpexEstimFinanceCapital("road", candidate.capital, candidate.distance,
+            ("capitalIsActual" in candidate) && candidate.capitalIsActual,
+            ("immobilise" in candidate) ? candidate.immobilise : 0);
       local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
       if (money < need) {
         if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("road", i, candidate.capital, candidate.profitAnnual, candidate.roi, candidate.src, candidate.dst, need, money);
         if (DECISION_LOG || C63_INVEST_PROBE
             || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
diff --git a/ai/OpexAI/task_v249.nut b/ai/OpexAI/task_v249.nut
--- a/ai/OpexAI/task_v249.nut
+++ b/ai/OpexAI/task_v249.nut
@@ -8,10 +8,42 @@
  * gain annuel x horizon (5 ans) > cout mesure. Preservation du meilleur
  * projet admissible et financable et de la flotte V252.
  * Aucun etat sauvegarde. La statue est un bit du monde (AITown.HasStatue). */
 
 const V249_HORIZON_YEARS = 5;
+
+/* ESTIM-1 lot 3 (bit 4) : contrat M1 commun aux investissements sur lignes
+ * existantes. deltaR est une recette BRUTE, deltaE l'entretien annuel,
+ * deltaA l'amortissement annuel des vehicules, deltaC le prix net a payer.
+ * La correction de recette est autonome du bit 1 (apprentissage facultatif).
+ * Une amelioration peut avoir deltaR/deltaE negatifs : garder leurs signes. */
+function OpexEstimVProject(mode, deltaR, deltaE, deltaA, deltaC, kDec = -1, modeRevenues = null)
+{
+  local kR = (mode in ESTIM_K_R) ? ESTIM_K_R[mode] : 1.0;
+  local calibrated = kR * deltaR;
+  if (modeRevenues != null) {
+    calibrated = 0.0;
+    foreach (revenueMode, revenue in modeRevenues)
+      calibrated += revenue * ((revenueMode in ESTIM_K_R) ? ESTIM_K_R[revenueMode] : 1.0);
+  }
+  local deltaP = (calibrated - deltaE - deltaA).tointeger();
+  if (kDec < 0) kDec = OpexC69ComputeKDec().K_dec;
+  local capital = deltaC > 0 ? deltaC : 0;
+  local denominator = capital > kDec ? capital : kDec;
+  return { mode = mode, deltaR = deltaR, deltaE = deltaE, deltaA = deltaA,
+      deltaC = deltaC, deltaP = deltaP, score = OpexProjectScore(deltaP, denominator) };
+}
+
+function OpexEstimVLog(kind, id, project)
+{
+  if (!DECISION_LOG || project == null) return;
+  OpexDecide("ESTIM_VPROJECT", "kind=" + kind + " id=" + id
+      + " mode=" + project.mode + " deltaR=" + project.deltaR
+      + " deltaE=" + project.deltaE + " deltaA=" + project.deltaA
+      + " deltaC=" + project.deltaC + " deltaP=" + project.deltaP
+      + " score=" + project.score);
+}
""" + " \n" + r""" /* Capital du projet le plus cher encore liste : la statue ne doit jamais
  * prendre l'argent d'un projet que le portefeuille veut financer. */
 function OpexV249MaxListedCapital(projects)
 {
@@ -181,10 +213,16 @@
 
   local profit = OpexV249LineProfit(line);
   local unitRevenue = 0.0;
   if (profit > 0 && currentCarried > 0) {
     unitRevenue = profit.tofloat() / currentCarried;
+    if ((ESTIM_UNIFIE & 4) != 0) {
+      local expenses = 0;
+      foreach (vehicle in vehicles)
+        if (AIVehicle.IsValidVehicle(vehicle)) expenses += AIVehicle.GetRunningCost(vehicle);
+      unitRevenue = (profit + expenses).tofloat() / currentCarried;
+    }
   } else if (("predRevenue" in line) && line.predRevenue > 0 && ("predCarried" in line) && line.predCarried > 0) {
     unitRevenue = line.predRevenue.tofloat() / (line.predCarried * 12);
   } else if (("predicted" in line) && line.predicted > 0 && ("predCarried" in line) && line.predCarried > 0) {
     unitRevenue = line.predicted.tofloat() / (line.predCarried * 12);
   }
@@ -239,14 +277,16 @@
   local bestGain = 0;
   local bestStation = -1;
   local bestCargo = -1;
   local bestRating = -1;
   local bestProd = 0;
+  local bestProject = null;
   local found = false;
   local nStatue = 0;
   local nUnavail = 0;
   local nTowns = 0;
+  local kDec = (ESTIM_UNIFIE & 4) != 0 ? OpexC69ComputeKDec().K_dec : -1;
 
   foreach (townId, cargoMap in byTownCargoStation) {
     nTowns++;
     if (AITown.HasStatue(townId)) {
       nStatue++;
@@ -256,10 +296,11 @@
       nUnavail++;
       continue;
     }
 
     local townGain = 0;
+    local townModeRevenues = {};
     local topSt = -1;
     local topCg = -1;
     local topRt = -1;
     local topPr = 0;
     local topStGain = -1;
@@ -289,10 +330,11 @@
       local annualProd = prodMonthly * 12;
       local maxTownExtra = (annualProd * 26) / 256;
 
       local cargoExtraTotal = 0;
       local cargoRevSum = 0.0;
+      local cargoModeRevenues = {};
 
       foreach (stId, linesList in stations) {
         local ratingPct = AIStation.GetCargoRating(stId, cg);
         if (ratingPct < 0) continue;
         local curByte = OpexC121RatingPercentToByteMid(ratingPct);
@@ -325,23 +367,48 @@
           topPr = prodMonthly;
         }
 
         cargoExtraTotal += deliverableStation;
         cargoRevSum += deliverableStation * stationAvgUnitRev;
+        if ((ESTIM_UNIFIE & 4) != 0) {
+          foreach (line in linesList) {
+            local sInfo = OpexV249LineServiceInfo(line, stId, cg);
+            local mode = ("mode" in line) ? line.mode : "unknown";
+            if (!(mode in cargoModeRevenues)) cargoModeRevenues.rawset(mode, 0.0);
+            cargoModeRevenues[mode] += deliverableStation * sInfo.spareCapacity
+                * sInfo.unitRevenue / stationSpareCap;
+          }
+        }
       }
 
       if (cargoExtraTotal <= 0) continue;
       local deliverableCargoTown = cargoExtraTotal < maxTownExtra ? cargoExtraTotal : maxTownExtra;
       local avgCargoUnitRev = cargoRevSum / cargoExtraTotal;
       townGain += (deliverableCargoTown * avgCargoUnitRev).tointeger();
+      if ((ESTIM_UNIFIE & 4) != 0)
+        foreach (mode, revenue in cargoModeRevenues) {
+          if (!(mode in townModeRevenues)) townModeRevenues.rawset(mode, 0.0);
+          townModeRevenues[mode] += revenue * deliverableCargoTown / cargoExtraTotal;
+        }
     }
 
     if (townGain <= 0) continue;
-    if (!found || townGain > bestGain || (townGain == bestGain && townId < bestTown)) {
+    local statueProject = null;
+    if ((ESTIM_UNIFIE & 4) != 0) {
+      local statueCost = OpexV249MeasureStatueCost(townId);
+      statueProject = OpexEstimVProject("mixed", townGain, 0, 0, statueCost,
+          kDec, townModeRevenues);
+      if (statueProject.deltaP <= 0 || statueProject.deltaC <= 0) continue;
+    }
+    if (!found || ((ESTIM_UNIFIE & 4) != 0
+        ? (statueProject.score > bestProject.score
+          || (statueProject.score == bestProject.score && townId < bestTown))
+        : (townGain > bestGain || (townGain == bestGain && townId < bestTown)))) {
       found = true;
       bestTown = townId;
       bestGain = townGain;
+      bestProject = statueProject;
       bestStation = topSt;
       bestCargo = topCg;
       bestRating = topRt;
       bestProd = topPr;
     }
@@ -353,19 +420,31 @@
   }
 
   local cost = OpexV249MeasureStatueCost(bestTown);
   local bestCargoLabel = AICargo.IsValidCargo(bestCargo) ? AICargo.GetCargoLabel(bestCargo) : "unknown";
 
-  if (bestGain * V249_HORIZON_YEARS <= cost) {
+  if ((ESTIM_UNIFIE & 4) != 0) {
+    local project = bestProject;
+    project.deltaC = cost;
+    OpexEstimVLog("V249", bestTown, project);
+    if (project.deltaP <= 0 || project.deltaC <= 0) {
+      if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=estim_margin town=" + bestTown + " deltaP=" + project.deltaP);
+      return true;
+    }
+  }
+
+  if ((ESTIM_UNIFIE & 4) == 0 && bestGain * V249_HORIZON_YEARS <= cost) {
     if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=payback town=" + bestTown + " station=" + bestStation + " cargo=" + bestCargoLabel + " rating=" + bestRating + " prod=" + bestProd + " gain=" + bestGain + " cost=" + cost + " horizon=" + V249_HORIZON_YEARS);
     return true;
   }
 
   local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
   local bestProjCap = OpexV249BestAdmissibleCapital(ai._projects, ai._lines, cash);
   local v252Cost = OpexV249GetPendingV252Cost(ai);
   local threshold = bestProjCap + v252Cost;
+  if ((ESTIM_UNIFIE & 2) != 0)
+    threshold = 0;
 
   if (cost <= 0 || cash - cost < threshold) {
     if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cost town=" + bestTown + " station=" + bestStation + " cargo=" + bestCargoLabel + " rating=" + bestRating + " prod=" + bestProd + " gain=" + bestGain + " cost=" + cost + " cash=" + cash + " threshold=" + threshold + " best_proj=" + bestProjCap + " v252=" + v252Cost);
     return true;
   }
@@ -398,11 +477,11 @@
   if (cashStop) {
     if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cash_stop");
     return true;
   }
 
-  if (V249_STATUE == 2) {
+  if (V249_STATUE == 2 || (ESTIM_UNIFIE & 4) != 0) {
     return OpexV249DispatchMode2(this, ym, year);
   }
 
   local byTown = {};
   local nLines = 0;
@@ -456,10 +535,12 @@
   }
 
   local cost = OpexV249MeasureStatueCost(bestTown);
   local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
   local threshold = OpexV249MaxListedCapital(this._projects);
+  if ((ESTIM_UNIFIE & 2) != 0)
+    threshold = 0;
   if (cost <= 0 || cash - cost < threshold) {
     if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cost cash=" + cash + " cost=" + cost + " threshold=" + threshold + " town=" + bestTown);
     return true;
   }
   local built = AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_BUILD_STATUE);
diff --git a/ai/OpexAI/task_v252.nut b/ai/OpexAI/task_v252.nut
--- a/ai/OpexAI/task_v252.nut
+++ b/ai/OpexAI/task_v252.nut
@@ -1,10 +1,51 @@
 /* V252 : modernisation de la flotte aerienne quand on est riche. Aucun montant fixe.
  * Riche = aucun emprunt, aucune passe projets arretee faute de caisse depuis le mois
  * precedent (V252_CASH_STOP), et apres l'achat la caisse couvre encore
  * le projet le plus cher du portefeuille. Au plus un remplacement par passage.
  * Aucun nombre a 4 chiffres ou plus dans ce fichier. */
+
+/* ESTIM-1 : cout et marge de la substitution d'UN avion a flotte constante.
+ * Les deux appareils passent par le meme modele physique de route ; la
+ * difference entre flottes homogenes est repartie sur les n appareils. */
+function OpexEstimV252Project(line, vehicle, newEngine, catalog, hangar, kDec = -1)
+{
+  local monthly = ("airMonthlyPax" in line && line.airMonthlyPax > 0) ? line.airMonthlyPax
+      : (("monthlyPax" in line) ? line.monthlyPax : 0);
+  if (monthly <= 0 || line.vehicles == null || line.vehicles.len() == 0) return null;
+  local distance = ("distance" in line && line.distance > 0)
+      ? line.distance : AIMap.DistanceManhattan(line.stationA, line.stationB);
+  if (distance <= 0) return null;
+  local cargo = ("cargo" in line) ? line.cargo : catalog.paxCargo;
+  local oldEngine = AIVehicle.GetEngineType(vehicle);
+  local oldCapacity = AIVehicle.GetCapacity(vehicle, cargo);
+  local newCapacity = AIVehicle.GetBuildWithRefitCapacity(hangar, newEngine, cargo);
+  if (oldCapacity <= 0 || newCapacity <= 0) return null;
+  local airport = { type = AIAirport.GetAirportType(line.stationA), price = 0, maintenance = 0 };
+  local oldPlane = { id = oldEngine, speed = AIEngine.GetMaxSpeed(oldEngine),
+      capacity = oldCapacity, price = AIEngine.GetPrice(oldEngine),
+      runningCost = AIEngine.GetRunningCost(oldEngine) };
+  local newPlane = { id = newEngine, speed = AIEngine.GetMaxSpeed(newEngine),
+      capacity = newCapacity, price = AIEngine.GetPrice(newEngine),
+      runningCost = AIEngine.GetRunningCost(newEngine) };
+  local count = line.vehicles.len();
+  local before = OpexAirEconomics(catalog, airport, oldPlane, distance, monthly,
+      false, 0, 0, 0, count);
+  local after = OpexAirEconomics(catalog, airport, newPlane, distance, monthly,
+      false, 0, 0, 0, count);
+  if (before == null || after == null) return null;
+  local price = AIEngine.GetPrice(newEngine);
+  local sale = AIVehicle.GetCurrentValue(vehicle);
+  if (sale < 0) sale = 0;
+  local netCapital = price - sale;
+  if (netCapital < 0) netCapital = 0;
+  local years = AIEngine.GetMaxAge(newEngine).tofloat() / 365.0;
+  if (years <= 0) return null;
+  local deltaR = (after.revenueAnnual - before.revenueAnnual).tofloat() / count;
+  local deltaE = newPlane.runningCost - oldPlane.runningCost;
+  return OpexEstimVProject("air", deltaR, deltaE, netCapital / years, netCapital, kDec);
+}
""" + " \n" + r""" function OpexAI::_dispatchV252AirEngineRefresh(task, year)
 {
   local date = AIDate.GetCurrentDate();
   local ym = year * 12 + AIDate.GetMonth(date);
@@ -36,10 +77,12 @@
   local curEngine = -1;
   local nAirLines = 0;
   local nOutdated = 0;
   local candidates = [];
   local rank = 0;
+  local bestProject = null;
+  local kDec = (ESTIM_UNIFIE & 4) != 0 ? OpexC69ComputeKDec().K_dec : -1;
 
   foreach (line in this._lines) {
     if (line == null) continue;
     if (("mode" in line) && line.mode != "air") continue;
     if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) continue;
@@ -84,28 +127,42 @@
 
     local targetEngine = lineTargetCache[lineKey];
     if (targetEngine == null) continue;
     if (cand.engine == targetEngine) continue;
 
+    local project = null;
+    if ((ESTIM_UNIFIE & 4) != 0) {
+      local airportTile = ("originA" in cand.line) && AIAirport.IsAirportTile(cand.line.originA)
+          ? cand.line.originA : cand.line.stationA;
+      local hangar = AIAirport.GetHangarOfAirport(airportTile);
+      if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) continue;
+      project = OpexEstimV252Project(cand.line, cand.veh, targetEngine, this._catalog, hangar, kDec);
+      if (project == null || project.deltaP <= 0 || project.score <= 0) continue;
+      if (bestProject != null && project.score <= bestProject.score) continue;
+      bestProject = project;
+    }
     nOutdated = 1;
     bestLine = cand.line;
     bestVeh = cand.veh;
     bestAge = cand.age;
     bestProfit = cand.profit;
     bestNewEngine = targetEngine;
     curEngine = cand.engine;
-    break;
+    if ((ESTIM_UNIFIE & 4) == 0) break;
   }
 
   if (bestVeh < 0 || bestLine == null) {
     if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=no_candidate air_lines=" + nAirLines + " outdated=" + nOutdated);
     return true;
   }
 
   local price = AIEngine.GetPrice(bestNewEngine);
+  if ((ESTIM_UNIFIE & 4) != 0) OpexEstimVLog("V252", bestLine.lineId, bestProject);
   local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
   local threshold = OpexV249MaxListedCapital(this._projects);
+  if ((ESTIM_UNIFIE & 2) != 0)
+    threshold = 0;
   if (price <= 0 || cash - price < threshold) {
     if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=cost cash=" + cash + " cost=" + price + " threshold=" + threshold + " line=" + bestLine.lineId);
     return true;
   }
 
diff --git a/ai/OpexAI/task_v257.nut b/ai/OpexAI/task_v257.nut
--- a/ai/OpexAI/task_v257.nut
+++ b/ai/OpexAI/task_v257.nut
@@ -101,10 +101,26 @@
   return { loco = loco, wagon = wagon, wagons = wagons, revenue = revenue,
            running = loco.runningCost + wagons * wagon.runningCost,
            price = loco.price + wagons * wagon.price, speed = speed, days = days };
 }
 
+/* ESTIM-1 : meme modele de trafic avant/apres remplacement, recettes corrigees
+ * via k_R rail, entretien reel des deux compositions et amortissement net du
+ * nouveau vehicule sur sa duree utile. Aucun horizon de retour sur achat. */
+function OpexEstimV257Project(current, target, oldVehicle, sale)
+{
+  if (current == null || target == null || sale == null
+      || current.revenue <= 0) return null;
+  local years = AIEngine.GetMaxAge(target.loco.id).tofloat() / 365.0;
+  if (years <= 0) return null;
+  local netPrice = target.price - sale;
+  if (netPrice < 0) netPrice = 0;
+  return OpexEstimVProject("rail", target.revenue - current.revenue,
+      target.running - AIVehicle.GetRunningCost(oldVehicle),
+      netPrice / years, netPrice);
+}
+
 function OpexV257ReviewLog(line, current, best, gain, cost, decision, reason, profit = 0, waiting = 0, rating = -1, load = 0, delivered = 0)
 {
   if (DECISION_LOG) OpexDecide("V257_REVIEW", "line=" + line.lineId + " current=" + current
       + " best=" + best + " gain=" + gain + " cost=" + cost + " decision=" + decision
       + " reason=" + reason + " line_profit=" + profit + " waiting=" + waiting
@@ -294,10 +310,11 @@
    * La moyenne mesuree et le stock sont partages entre les rames de la ligne. */
   local monthly = (state.annualDelivered * 365.0 / state.annualDays + waiting) / (12 * count);
   local selected = null;
   local selectedVehicle = -1;
   local selectedGain = 0;
+  local selectedScore = 0;
   local selectedCost = 0;
   local selectedCurrent = -1;
   local currentYearStart = AIDate.GetDate(year - 1, 1, 1);
   /* Le choix depend de la last_speed de la rame en service. Une composition
    * non modelisable (automotrice, rame mixte, trop courte) garde l'ancien
@@ -363,15 +380,27 @@
     local cost = best.price - sale;
     local remaining = AIVehicle.GetAgeLeft(vehicle) / 365.0;
     local newLife = AIEngine.GetMaxAge(best.loco.id) / 365.0;
     if (newLife < remaining) remaining = newLife;
     local pays = gain > 0 && remaining > 0 && gain * remaining >= cost;
+    local estimProject = null;
+    if ((ESTIM_UNIFIE & 4) != 0) {
+      estimProject = OpexEstimV257Project(current, best, vehicle, sale);
+      if (estimProject == null) continue;
+      OpexEstimVLog("V257", line.lineId, estimProject);
+      gain = estimProject.deltaP;
+      pays = estimProject.deltaP > 0 && estimProject.score > 0;
+    }
     OpexV257ReviewLog(line, currentEngine, best.loco.id, gain, cost, pays ? "replace" : "keep",
         pays ? "payback" : "payback_failed", lineProfit, waiting, rating, load, state.annualDelivered);
-    if (pays && (selected == null || gain > selectedGain)) {
+    if (pays && (selected == null || ((ESTIM_UNIFIE & 4) != 0
+        ? estimProject.score > selectedScore
+        : gain > selectedGain))) {
       selected = best; selectedVehicle = vehicle; selectedGain = gain;
       selectedCost = cost; selectedCurrent = currentEngine;
+      if ((ESTIM_UNIFIE & 4) != 0)
+        selectedScore = estimProject.score;
     }
   }
   if (selected != null) {
     /* Le depot atteint decide du depot de reconstruction, pas le premier depot
      * de la ligne : important pour les deux voies independantes. */
@@ -437,10 +466,12 @@
    * de prix. Recalculer le gain avec le profit/entretien actuels et le stock
    * maintenant observe, sans figer le gain du jour de l'envoi. */
   local state = (line.lineId in this._v257State) ? this._v257State[line.lineId] : null;
   local number = AIVehicle.GetNumWagons(oldVehicle) - 1;
   local gain = 0.0;
+  local currentPlan = null;
+  local targetPlan = null;
   if (state != null && state.annualDays > 0 && number > 0 && line.vehicles.len() > 0) {
     local wagonEngine = AIVehicle.GetWagonEngineType(oldVehicle, 1);
     local stock = AIStation.GetCargoWaiting(AIStation.GetStationID(line.stationA), line.cargo);
     if (line.kind == "pax") stock += AIStation.GetCargoWaiting(AIStation.GetStationID(line.stationB), line.cargo);
     local monthly = (state.annualDelivered * 365.0 / state.annualDays + stock) / (12 * line.vehicles.len());
@@ -460,22 +491,37 @@
     local serviceLoco = OpexV257Engine(AIVehicle.GetEngineType(oldVehicle), line.cargo, false);
     local serviceWagon = OpexV257Engine(wagonEngine, line.cargo, true);
     local serviceSpeed = OpexV257ConsistLastSpeed(serviceLoco, serviceWagon, wagonLimits);
     local current = OpexV257Plan(line, serviceLoco, serviceWagon, number, monthly, rating, serviceSpeed, wagonLimits);
     local target = OpexV257Plan(line, loco, wagon, pending.wagons, monthly, rating, serviceSpeed, wagonLimits);
+    currentPlan = current;
+    targetPlan = target;
     local realRevenue = AIVehicle.GetProfitLastYear(oldVehicle) + AIVehicle.GetRunningCost(oldVehicle);
     if (current != null && target != null && current.revenue > 0 && realRevenue > 0) {
       gain = realRevenue * (target.revenue.tofloat() / current.revenue - 1.0)
           + AIVehicle.GetRunningCost(oldVehicle) - target.running;
     }
   }
   pending.gain = gain.tointeger();
   local remaining = AIVehicle.GetAgeLeft(oldVehicle) / 365.0;
   local newLife = AIEngine.GetMaxAge(pending.engine) / 365.0;
   if (newLife < remaining) remaining = newLife;
-  if (sale == null || !compatible || remaining <= 0 || pending.gain <= 0 || pending.gain * remaining < cost
-      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price) {
+  local estimPays = false;
+  if ((ESTIM_UNIFIE & 4) != 0) {
+    local refreshed = OpexEstimV257Project(currentPlan, targetPlan, oldVehicle, sale);
+    if (refreshed != null) {
+      pending.gain = refreshed.deltaP;
+      OpexEstimVLog("V257_DEPOT", line.lineId, refreshed);
+      estimPays = refreshed.deltaP > 0 && refreshed.score > 0;
+    }
+  }
+  if (sale == null || !compatible || ((ESTIM_UNIFIE & 4) != 0 ? !estimPays
+      : (remaining <= 0 || pending.gain <= 0 || pending.gain * remaining < cost))
+      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) <
+          ((ESTIM_UNIFIE & 2) != 0
+              ? OpexEstimFinanceCapital("rail", price, 0, true)
+              : price)) {
     pending.phase = "resume";
     local resumed = AIVehicle.StartStopVehicle(oldVehicle);
     OpexV257ReviewLog(line, pending.current, pending.engine, pending.gain, cost, "keep", "depot_recheck",
         lineProfit, waiting, rating, load, delivered);
     if (resumed) { this._v257Pending = null; this._v257PendingLine = null; }
diff --git a/ai/OpexAI/task_v259.nut b/ai/OpexAI/task_v259.nut
--- a/ai/OpexAI/task_v259.nut
+++ b/ai/OpexAI/task_v259.nut
@@ -280,11 +280,26 @@
 
   local cost = OpexV259MeasureBridgeCost(vtype, bestBridgeType, start, end);
   if (cost <= 0) cost = AIBridge.GetPrice(bestBridgeType, len);
 
   local totalGain = gain.tofloat() * remainingYears;
-  if (totalGain < cost.tofloat()) {
+  local estimViable = true;
+  if ((ESTIM_UNIFIE & 4) != 0) {
+    /* Rotation plus courte : recette additionnelle sur la meme ligne, sans
+     * depense courante nouvelle ni amortissement du pont (infrastructure). */
+    local revenue = lineProfit;
+    if (("vehicles" in line) && line.vehicles != null)
+      foreach (vehicle in line.vehicles)
+        if (AIVehicle.IsValidVehicle(vehicle)) revenue += AIVehicle.GetRunningCost(vehicle);
+    local mode = vtype == AIVehicle.VT_RAIL ? "rail" : "road";
+    local project = OpexEstimVProject(mode, cycleFraction * revenue, 0, 0, cost);
+    OpexEstimVLog("V259", lineId, project);
+    gain = project.deltaP;
+    estimViable = project.deltaP > 0 && project.score > 0;
+  }
+  if (((ESTIM_UNIFIE & 4) != 0 && !estimViable)
+      || ((ESTIM_UNIFIE & 4) == 0 && totalGain < cost.tofloat())) {
     if (DECISION_LOG) OpexDecide("V259_BRIDGE", "line=" + lineId + " tiles=" + start + "->" + end
       + " old_type=" + oldBridgeType + " old_speed=" + oldSpeed
       + " new_type=" + bestBridgeType + " new_speed=" + bestSpeed
       + " cost=" + cost + " gain=" + gain + " decision=skip_unprofitable");
     return;
diff --git a/ai/OpexAI/task_v284.nut b/ai/OpexAI/task_v284.nut
--- a/ai/OpexAI/task_v284.nut
+++ b/ai/OpexAI/task_v284.nut
@@ -20,14 +20,65 @@
 function OpexV284Log(action, fields)
 {
   if (DECISION_LOG) OpexDecide("V284", "action=" + action + " " + fields);
 }
 
+/* ESTIM-1 : deux evaluations physiques de la meme ligne. Pour un train en
+ * plus, la demande est partagee entre deux rames et la note utilise la demi-
+ * cadence ; pour des wagons en plus, on conserve la cadence courante. */
+function OpexEstimV284Project(line, vehicle, wagon, number, loco, add, waiting, loopCost, kDec = -1)
+{
+  local oldLoco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
+  local oldNumber = AIVehicle.GetNumWagons(vehicle) - 1;
+  if (oldNumber < 1 || oldLoco == null || loco == null) return null;
+  local wagonLimits = OpexV257WagonSpeedLimits();
+  local serviceSpeed = OpexV257ConsistLastSpeed(oldLoco, wagon, wagonLimits);
+  local station = AIStation.GetStationID(line.stationA);
+  if (!AIStation.IsValidStation(station)) return null;
+  local rating = AIStation.GetCargoRating(station, line.cargo);
+  if (rating < 0) return null;
+  local monthly = ("monthly" in line && line.monthly > 0) ? line.monthly : 0;
+  if (("predCarried" in line) && line.predCarried > monthly) monthly = line.predCarried;
+  monthly += waiting.tofloat() / 12.0; // stock etale sur une annee.
+  if (monthly <= 0) return null;
+  local current = OpexV257Plan(line, oldLoco, wagon, oldNumber, monthly, rating,
+      serviceSpeed, wagonLimits);
+  local targetRating = rating;
+  if (add) {
+    local oneWay = line.distance.tofloat() / (0.036 * loco.speed);
+    local better = OpexStationRatingForHeadway(oneWay);
+    if (better > targetRating) targetRating = better;
+  }
+  local target = OpexV257Plan(line, loco, wagon, number,
+      add ? monthly / 2.0 : monthly, targetRating, serviceSpeed, wagonLimits);
+  if (current == null || target == null) return null;
+  local oldRunning = AIVehicle.GetRunningCost(vehicle);
+  local newRevenue = target.revenue;
+  local newRunning = target.running;
+  if (add) {
+    /* La premiere rame garde son moteur. Le service futur est donc un vieux
+     * train et un nouveau, evalues a la meme demande et au meme headway. */
+    local existing = OpexV257Plan(line, oldLoco, wagon, oldNumber,
+        monthly / 2.0, targetRating, serviceSpeed, wagonLimits);
+    if (existing == null) return null;
+    newRevenue += existing.revenue;
+    newRunning += oldRunning;
+  }
+  local sale = add ? 0 : AIVehicle.GetCurrentValue(vehicle);
+  if (sale < 0) sale = 0;
+  local netVehiclePrice = target.price - sale;
+  if (netVehiclePrice < 0) netVehiclePrice = 0;
+  local years = AIEngine.GetMaxAge(loco.id).tofloat() / 365.0;
+  if (years <= 0) return null;
+  return OpexEstimVProject("rail", newRevenue - current.revenue,
+      newRunning - oldRunning, netVehiclePrice / years, netVehiclePrice + loopCost, kDec);
+}
+
 /* Le modele C41 courant compare les deux compositions sur la meme distance.
  * Garder la vitesse, pas seulement 85 % de la vitesse du passage precedent :
  * aucune erosion multiplicative a chaque ajout. */
-function OpexV284Equipment(line, vehicle, wagon, number)
+function OpexV284Equipment(line, vehicle, wagon, number, add = false, waiting = 0, kDec = -1)
 {
   local current = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
   local oldNumber = AIVehicle.GetNumWagons(vehicle) - 1;
   local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
   local speed = OpexRailEffectiveSpeed(current, wagon, oldNumber, distance);
@@ -44,13 +95,20 @@
     local loco = OpexV257Engine(engine, line.cargo, false);
     local nextSpeed = OpexRailEffectiveSpeed(loco, wagon, number, distance);
     if (nextSpeed < speed || loco.speed < current.speed) continue;
     /* A vitesse suffisante, minimiser achat + cinq ans d'entretien. */
     local cost = loco.price + 5 * loco.runningCost;
-    if (best == null || cost < best.cost) best = {
-      engine = engine, cost = cost, speed = nextSpeed, oldSpeed = speed
-    };
+    local project = null;
+    if ((ESTIM_UNIFIE & 4) != 0) {
+      project = OpexEstimV284Project(line, vehicle, wagon, number, loco, add, waiting, 0, kDec);
+      if (project == null || project.deltaP <= 0 || project.score <= 0) continue;
+    }
+    if (best == null || ((ESTIM_UNIFIE & 4) != 0
+        ? project.score > best.project.score : cost < best.cost)) {
+      best = { engine = engine, cost = cost, speed = nextSpeed, oldSpeed = speed };
+      if ((ESTIM_UNIFIE & 4) != 0) best.project <- project;
+    }
   }
   return best;
 }
 
 function OpexV284Select(owner, year, v233Input = false)
@@ -64,10 +122,11 @@
   local state = owner._v284State;
   local date = AIDate.GetCurrentDate();
   if (!v233Input && date < state.nextDate) return false;
   if (!v233Input) state.nextDate = date + 30; // au plus un choix/mois, pas une recherche de fenetre par tick.
   local best = null;
+  local kDec = (ESTIM_UNIFIE & 4) != 0 ? OpexC69ComputeKDec().K_dec : -1;
   local v233Mark = v233Input ? OpexOpsMeasureBegin() : null;
   foreach (line in owner._lines) {
     if (v233Input && OpexOpsMeasureEnd(v233Mark) >= V233L_SLICE_OPS) break;
     if (v233Input && !OpexV233LInputTarget(line)) continue;
     if (!("mode" in line) || line.mode != "rail" || !("kind" in line) || line.kind != "freight"
@@ -101,20 +160,29 @@
     local atLimit = number >= maxWagons || AIVehicle.GetLength(vehicle) + 8 > length * 16;
     if (v233Input && !OpexV233LBacklog(line, waiting, atLimit ? capacity : wagon.capacity)) continue;
     if (atLimit && (waiting < capacity || !OpexRailVehicleSlotAvailable())) continue;
     if (atLimit && (line.lineId in state.loops)) continue;
     local score = line.distance.tofloat() * waiting / capacity;
-    if (best == null || score > best.score) best = {
-      line = line, vehicle = vehicle, wagon = wagon, number = number,
-      waiting = waiting, capacity = capacity, add = atLimit, score = score
-    };
+    local candidateEquipment = null;
+    if ((ESTIM_UNIFIE & 4) != 0) {
+      candidateEquipment = OpexV284Equipment(line, vehicle, wagon,
+          number + (atLimit ? 0 : 1), atLimit, waiting, kDec);
+      if (candidateEquipment == null) continue;
+      score = candidateEquipment.project.score;
+    }
+    if (best == null || score > best.score) {
+      best = { line = line, vehicle = vehicle, wagon = wagon, number = number,
+        waiting = waiting, capacity = capacity, add = atLimit, score = score };
+      if ((ESTIM_UNIFIE & 4) != 0) best.equipment <- candidateEquipment;
+    }
   }
   if (best == null) return false;
   local line = best.line;
   state.dates.rawset(line.lineId, date + 90); // quota de croissance par ligne.
   local number = best.number + (best.add ? 0 : 1);
-  local equipment = OpexV284Equipment(line, best.vehicle, best.wagon, number);
+  local equipment = ((ESTIM_UNIFIE & 4) != 0) ? best.equipment
+      : OpexV284Equipment(line, best.vehicle, best.wagon, number);
   if (equipment == null) {
     state.dates.rawset(line.lineId, date + 365);
     OpexV284Log("skip", "line=" + line.lineId + " reason=traction");
     return false;
   }
@@ -128,11 +196,21 @@
       state.dates.rawset(line.lineId, date + 365);
       OpexV284Log("skip", "line=" + line.lineId + " reason=geometry waiting=" + best.waiting);
       return false;
     }
   }
-  if (v233Input && !OpexV233LInputMargin(line, best, equipment, number, loopPlan)) return false;
+  if (v233Input && (ESTIM_UNIFIE & 4) == 0
+      && !OpexV233LInputMargin(line, best, equipment, number, loopPlan)) return false;
+  if ((ESTIM_UNIFIE & 4) != 0) {
+    local loopCost = loopPlan == null ? 0 : loopPlan.pieces.len() * AIRail.GetBuildCost(
+        AIRail.GetRailType(line.depot), AIRail.BT_TRACK);
+    local loco = OpexV257Engine(equipment.engine, line.cargo, false);
+    local project = OpexEstimV284Project(line, best.vehicle, best.wagon, number,
+        loco, best.add, best.waiting, loopCost, kDec);
+    if (project == null || project.deltaP <= 0 || project.score <= 0) return false;
+    OpexEstimVLog("V284", line.lineId, project);
+  }
   local oneWay = line.distance.tofloat() / (0.036 * equipment.speed);
   local waitDays = (2 * oneWay).tointeger() + 60;
   if (waitDays < 120) waitDays = 120;
   if (waitDays > 730) waitDays = 730;
   state.pending = {
@@ -429,15 +507,21 @@
   local price = loco.price + pending.wagons * wagon.price;
   local limit = OpexV284Limit(line);
   local station = AIStation.GetStationID(line.stationA);
   local waitingNow = AIStation.IsValidStation(station) ? AIStation.GetCargoWaiting(station, line.cargo) : -1;
   local requiredWaiting = pending.add ? AIVehicle.GetCapacity(oldVehicle, line.cargo) : wagon.capacity;
+  local cashNeed = price + 50000;
+  if ((ESTIM_UNIFIE & 2) != 0) {
+    local loopCost = pending.loopPlan != null ? pending.loopPlan.pieces.len()
+        * AIRail.GetBuildCost(AIRail.GetRailType(pending.depot), AIRail.BT_TRACK) : 0;
+    cashNeed = OpexEstimFinanceCapital("rail", price + loopCost, 0, true);
+  }
   if (waitingNow < requiredWaiting || !AIEngine.IsBuildable(pending.engine) || !AIEngine.IsBuildable(pending.wagon)
       || !AIRail.IsRailDepotTile(pending.depot)
       || !AIEngine.HasPowerOnRail(pending.engine, AIRail.GetRailType(pending.depot))
       || pending.wagons > OpexRailNominalMaxWagons(limit)
-      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + 50000) {
+      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cashNeed) {
     OpexV284Cancel(owner, pending, "depot_recheck"); return;
   }
   pending.cashBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
   pending.before = [];
   local vehicles = AIVehicleList();
diff --git a/ai/OpexAI/task_water.nut b/ai/OpexAI/task_water.nut
--- a/ai/OpexAI/task_water.nut
+++ b/ai/OpexAI/task_water.nut
@@ -25,10 +25,13 @@
             || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "batch_site_unbuildable", extra = "" });
         return { outcome = "rejected", discards = passDiscards };
       }
       local capital = 2 * this._catalog.costDock + this._catalog.costWaterDepot + this._catalog.maxShipPrice;
       local need = capital + WATER_CAPITAL_MARGIN;
+      if ((ESTIM_UNIFIE & 2) != 0)
+        need = OpexEstimFinanceCapital("water", project.capital, project.distance, false,
+            ("immobilise" in plan.economics) ? plan.economics.immobilise : 0);
       local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
       if (money < need) {
         if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("water", i, capital, plan.economics.profitAnnual, project.roi, plan.siteA.town.id, plan.siteB.town.id, need, money);
         if (DECISION_LOG || C63_INVEST_PROBE
             || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "water", src = plan.siteA.town.id, dst = plan.siteB.town.id, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
"""
# END REVIEWED ESTIM-1 SOURCE DIFF

PATCHES = _parse_patches(PATCH_TEXT) if PATCH_TEXT.strip() else {}


if __name__ == "__main__":
    if sys.argv[1:] == ["--refresh"]:
        refresh_reviewed_patch()
    elif sys.argv[1:] == ["--audit"]:
        diff = _working_source_diff()
        for name, added in unmarked_change_groups(diff):
            print(f"CHECK {name}: {added!r}")
    else:
        sys.exit("Usage: python sweeps/estim_unifie_off_lots.py --refresh|--audit")
