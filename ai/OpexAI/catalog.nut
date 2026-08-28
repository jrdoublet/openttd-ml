/* Etage 0 : le catalogue.
 *
 * Mesure faite le 2026-08-28 (ai/CatalogProbe, docs/catalogue_churn.json) : un rafraichissement
 * complet coute ~21 500 opcodes, soit 0,008 % du budget d'une partie si on le refait chaque
 * annee. Il n'y a donc AUCUNE raison de l'optimiser -- pas de rafraichissement incrementiel, pas
 * de planification sur les dates d'introduction connues. On refait tout, tous les ans.
 *
 * Ce qui bouge reellement en 20 ans : le nombre de villes ne change pas, les industries subissent
 * ~2,6 % de churn par an, et le parc de moteurs route/avion croit fortement (+83 % / +38 %).
 */

class OpexCatalog {
  towns = null;        // [{id, tile, pop}]
  industries = null;   // [{id, tile, type}]
  producers = null;    // cargo -> [index dans industries]
  acceptors = null;    // cargo -> [index dans industries]
  cargos = null;       // [cargo_id]
  paxCargo = -1;
  year = 0;

  railType = -1;       // type de rail courant
  loco = null;         // {id, speed, price, runningCost, ageYears} ou null
  wagonByCargo = null; // cargo -> {id, capacity, price}
  costTrackPerTile = 0;
  costStation = 0;

  constructor()
  {
    this.towns = [];
    this.industries = [];
    this.producers = {};
    this.acceptors = {};
    this.cargos = [];
    this.wagonByCargo = {};
  }

  function refresh(budget, year);
  function _refreshCargos();
  function _refreshTowns();
  function _refreshIndustries();
  function _refreshRail();
  function _cargoArray(list);
}

/* Le materiel roulant disponible AUJOURD'HUI, et ce que coute la voie.
 *
 * Necessaire a l'etage 1 : sans la vitesse du convoi on ne sait pas estimer le temps de trajet,
 * donc pas les penalites de retard, qui sont la moitie du revenu (docs/mecanique_jeu.md §1-2).
 * Le parc evolue reellement : sur 20 ans le nombre de moteurs routiers passe de 12 a 22 et les
 * avions de 13 a 18 (docs/catalogue_churn.json) -- d'ou le rafraichissement annuel. */
function OpexCatalog::_refreshRail()
{
  this.loco = null;
  this.wagonByCargo = {};

  local types = AIRailTypeList();
  local chosen = -1;
  for (local t = types.Begin(); !types.IsEnd(); t = types.Next()) {
    if (AIRail.IsRailTypeAvailable(t)) chosen = t;
  }
  if (chosen < 0) return;
  this.railType = chosen;
  AIRail.SetCurrentRailType(chosen);
  this.costTrackPerTile = AIRail.GetBuildCost(chosen, AIRail.BT_TRACK);
  this.costStation = AIRail.GetBuildCost(chosen, AIRail.BT_STATION);

  local engines = AIEngineList(AIVehicle.VT_RAIL);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    if (!AIEngine.IsBuildable(e)) continue;
    if (AIEngine.IsWagon(e)) {
      local cargo = AIEngine.GetCargoType(e);
      local capacity = AIEngine.GetCapacity(e);
      if (capacity <= 0) continue;
      /* Un seul wagon retenu par cargo : le plus capacitaire. */
      if (!(cargo in this.wagonByCargo) || capacity > this.wagonByCargo[cargo].capacity) {
        local entry = { id = e, capacity = capacity, price = AIEngine.GetPrice(e) };
        if (cargo in this.wagonByCargo) this.wagonByCargo[cargo] = entry;
        else this.wagonByCargo.rawset(cargo, entry);
      }
    } else {
      /* ⚠️ PIEGE D'API, verifie le 2026-08-28. CanRunOnRail() ne suffit PAS : une locomotive
       * ELECTRIQUE "peut rouler" sur une voie non electrifiee (elle peut y etre tractee), mais
       * elle n'y a AUCUNE PUISSANCE. Symptome observe : AIEngine.IsBuildable et CanRunOnRail
       * rendaient tous deux vrai, le depot etait valide, la tresorerie suffisante -- et
       * AIVehicle.BuildVehicle echouait avec ERR_UNKNOWN sur les 100 tentatives. Le diagnostic
       * qui a tranche : engine_rail = 1 (electrifie) contre depot_rail = 0.
       * HasPowerOnRail() est le bon predicat. */
      if (!AIEngine.CanRunOnRail(e, chosen)) continue;
      if (!AIEngine.HasPowerOnRail(e, chosen)) continue;
      local speed = AIEngine.GetMaxSpeed(e);
      /* La locomotive la plus rapide. Choix volontairement simple : le classement des candidats
       * ne depend que faiblement de la loco, alors qu'il depend fortement de la vitesse. */
      if (this.loco == null || speed > this.loco.speed) {
        this.loco = {
          id = e, speed = speed, price = AIEngine.GetPrice(e),
          runningCost = AIEngine.GetRunningCost(e),
          ageYears = AIEngine.GetMaxAge(e) / 365,
        };
      }
    }
  }
}

function OpexCatalog::_refreshCargos()
{
  this.cargos = [];
  this.paxCargo = -1;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    this.cargos.append(c);
    if (this.paxCargo < 0 && AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) this.paxCargo = c;
  }
}

function OpexCatalog::_refreshTowns()
{
  this.towns = [];
  local list = AITownList();
  for (local t = list.Begin(); !list.IsEnd(); t = list.Next()) {
    this.towns.append({
      id = t,
      tile = AITown.GetLocation(t),
      pop = AITown.GetPopulation(t),
    });
  }
}

function OpexCatalog::_refreshIndustries()
{
  this.industries = [];
  this.producers = {};
  this.acceptors = {};

  local list = AIIndustryList();
  for (local i = list.Begin(); !list.IsEnd(); i = list.Next()) {
    this.industries.append({ id = i, tile = AIIndustry.GetLocation(i), type = AIIndustry.GetIndustryType(i) });
  }

  /* Les cargos produits/acceptes se lisent sur le TYPE d'industrie, pas sur l'instance
   * (AIIndustry.IsCargoProduced n'existe pas). On memorise par type : il y a une poignee de
   * types pour des dizaines d'industries, donc les listes ne sont lues qu'une fois chacune. */
  local producedByType = {};
  local acceptedByType = {};
  for (local k = 0; k < this.industries.len(); k++) {
    local type = this.industries[k].type;
    if (!(type in producedByType)) {
      producedByType.rawset(type, this._cargoArray(AIIndustryType.GetProducedCargo(type)));
      acceptedByType.rawset(type, this._cargoArray(AIIndustryType.GetAcceptedCargo(type)));
    }
    foreach (cargo in producedByType[type]) {
      if (!(cargo in this.producers)) this.producers.rawset(cargo, []);
      this.producers[cargo].append(k);
    }
    foreach (cargo in acceptedByType[type]) {
      if (!(cargo in this.acceptors)) this.acceptors.rawset(cargo, []);
      this.acceptors[cargo].append(k);
    }
  }
}

function OpexCatalog::_cargoArray(list)
{
  local out = [];
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) out.append(c);
  return out;
}

function OpexCatalog::refresh(budget, year)
{
  this.year = year;

  budget.begin();
  this._refreshCargos();
  budget.end("cat_cargos");

  budget.begin();
  this._refreshTowns();
  budget.end("cat_towns");

  budget.begin();
  this._refreshIndustries();
  budget.end("cat_industries");

  budget.begin();
  this._refreshRail();
  budget.end("cat_rail");
}
