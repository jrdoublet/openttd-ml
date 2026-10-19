/* V262 T10/T15 : releve passif des infrastructures encore a nous apres le retrait
 * d'une ligne (task_report.nut::_scrapDeadLines retire _lines, pas les ouvrages).
 * Sous DECISION_LOG seulement, une fois par an au 1er decembre : les bancs
 * s'arretent a cette date (sweeps/game_health.py expected_last_checkpoint), donc
 * le releve de janvier (_dispatchReport / _lastReportYear) manque la derniere
 * annee. Aucune decision ne lit ces lignes. Aucune demolition.
 *
 * Dates : mois et jour 1-based (script_date.hpp:20-21, script_date.cpp:36-49).
 * GetCurrentDate est le temps economique (script_date.cpp:23-25). L'age n'est
 * calcule que si economy.timekeeping_units vaut TKU_CALENDAR = 0
 * (settings_type.h:75-79, economy_settings.ini def TKU_CALENDAR) : build_date
 * est calendaire (base_station_base.h:74) et avance a chaque installation
 * ajoutee (station.cpp:238, AddFacility), pas la date d'origine. Hors ce mode,
 * age=-1 et built=-1.
 *
 * AIStationList(type) : gares a nous (script_stationlist.cpp:19-28).
 * AIVehicleList_Station : vehicules qui ont un ordre vers la gare
 * (script_vehiclelist.hpp:55-66, script_vehiclelist.cpp:65-68), pas l'occupation.
 * Liste vide => Count()==0 (script_list.hpp:222-226).
 * GetStationID : tuile invalide ou non gare => StationID invalide
 * (script_station.cpp:29-33), puis IsValidStation.
 * AIDepotList(TRANSPORT_AIR) rend les tuiles de hangar, pas des depots
 * (script_depotlist.cpp:28-39). AIVehicleList_Depot : ordres OT_GOTO_DEPOT
 * (script_vehiclelist.cpp:87-130).
 * Entretien : six categories (script_infrastructure.hpp:23-30). Le cout mensuel
 * vaut 0 si economy.infrastructure_maintenance est faux
 * (script_infrastructure.cpp:85-88, economy_settings.ini def false). Aucun champ
 * de cout « orphelin » : l'API ne le separe pas.
 *
 * V262_ORPHAN_YEAR et V262_ORPHAN_DATE ne sont pas sauvegardes. Un rechargement
 * un 1er decembre peut journaliser une seconde fois. */

function OpexV262NoteStationTile(into, line, field)
{
  if (!(field in line)) return;
  local tile = line[field];
  if (tile == null || typeof tile != "integer") return;
  if (!AIMap.IsValidTile(tile)) return;
  local sid = AIStation.GetStationID(tile);
  if (!AIStation.IsValidStation(sid)) return;
  if (!(sid in into)) into[sid] <- true;
}

function OpexV262NoteLineStations(into, lines)
{
  if (lines == null) return;
  for (local i = 0; i < lines.len(); i++) {
    local line = lines[i];
    if (line == null || typeof line != "table") continue;
    OpexV262NoteStationTile(into, line, "stationA");
    OpexV262NoteStationTile(into, line, "stationB");
    OpexV262NoteStationTile(into, line, "stationA2");
    OpexV262NoteStationTile(into, line, "stationB2");
  }
}

function OpexV262StationAge(station, now, timekeeping)
{
  local built = AIBaseStation.GetConstructionDate(station);
  if (timekeeping != 0 || !AIDate.IsValidDate(built)) return [-1, -1];
  if (now < built) return [-1, built];
  return [now - built, built];
}

function OpexV262CountDepots(transport)
{
  local list = AIDepotList(transport);
  local total = list.Count();
  local empty = 0;
  foreach (tile, _ in list) {
    if (AIVehicleList_Depot(tile).Count() == 0) empty++;
  }
  return [empty, total];
}

function OpexV262OrphanSurvey(lines)
{
  if (!DECISION_LOG) return;
  local now = AIDate.GetCurrentDate();
  if (now == V262_ORPHAN_DATE) return;
  V262_ORPHAN_DATE = now;
  if (AIDate.GetMonth(now) != 12 || AIDate.GetDayOfMonth(now) != 1) return;
  local year = AIDate.GetYear(now);
  if (year == V262_ORPHAN_YEAR) return;
  V262_ORPHAN_YEAR = year;

  local timekeeping = AIGameSettings.IsValid("economy.timekeeping_units")
      ? AIGameSettings.GetValue("economy.timekeeping_units") : -1;
  local maint = AIGameSettings.IsValid("economy.infrastructure_maintenance")
      ? AIGameSettings.GetValue("economy.infrastructure_maintenance") : -1;

  local referenced = {};
  OpexV262NoteLineStations(referenced, lines);

  local kinds = [
    ["train", AIStation.STATION_TRAIN],
    ["truck", AIStation.STATION_TRUCK_STOP],
    ["bus", AIStation.STATION_BUS_STOP],
    ["airport", AIStation.STATION_AIRPORT],
    ["dock", AIStation.STATION_DOCK]
  ];
  local flags = {};
  foreach (kind in kinds) {
    local list = AIStationList(kind[1]);
    foreach (st, _ in list) {
      if (!AIStation.IsValidStation(st)) continue;
      if (st in flags) flags[st] = flags[st] | kind[1];
      else flags[st] <- kind[1];
    }
  }

  local counts = {};
  local orphans = {};
  foreach (kind in kinds) {
    counts[kind[0]] <- 0;
    orphans[kind[0]] <- 0;
  }
  local orphanN = 0;
  foreach (st, bits in flags) {
    local empty = AIVehicleList_Station(st).Count() == 0;
    foreach (kind in kinds) {
      if ((bits & kind[1]) == 0) continue;
      counts[kind[0]] = counts[kind[0]] + 1;
      if (empty) orphans[kind[0]] = orphans[kind[0]] + 1;
    }
    if (!empty) continue;
    orphanN++;
    local age = OpexV262StationAge(st, now, timekeeping);
    local fields = "station=" + st;
    foreach (kind in kinds) {
      fields += " " + kind[0] + "=" + (((bits & kind[1]) != 0) ? 1 : 0);
    }
    fields += " age=" + age[0] + " built=" + age[1];
    fields += " in_lines=" + ((st in referenced) ? 1 : 0);
    OpexDecide("V262_ORPHAN_STATION", fields);
  }

  local railDep = OpexV262CountDepots(AITile.TRANSPORT_RAIL);
  local roadDep = OpexV262CountDepots(AITile.TRANSPORT_ROAD);
  local waterDep = OpexV262CountDepots(AITile.TRANSPORT_WATER);
  local hangars = OpexV262CountDepots(AITile.TRANSPORT_AIR);
  local infra = [
    ["rail", AIInfrastructure.INFRASTRUCTURE_RAIL],
    ["signals", AIInfrastructure.INFRASTRUCTURE_SIGNALS],
    ["road", AIInfrastructure.INFRASTRUCTURE_ROAD],
    ["canal", AIInfrastructure.INFRASTRUCTURE_CANAL],
    ["station", AIInfrastructure.INFRASTRUCTURE_STATION],
    ["airport", AIInfrastructure.INFRASTRUCTURE_AIRPORT]
  ];
  local company = AICompany.COMPANY_SELF;
  local sum = "year=" + year + " timekeeping=" + timekeeping + " maint=" + maint;
  foreach (kind in kinds) sum += " stations_" + kind[0] + "=" + counts[kind[0]];
  foreach (kind in kinds) sum += " orphan_" + kind[0] + "=" + orphans[kind[0]];
  sum += " orphan_n=" + orphanN;
  sum += " depot_rail_empty=" + railDep[0] + " depot_rail_n=" + railDep[1];
  sum += " depot_road_empty=" + roadDep[0] + " depot_road_n=" + roadDep[1];
  sum += " depot_water_empty=" + waterDep[0] + " depot_water_n=" + waterDep[1];
  sum += " hangar_empty=" + hangars[0] + " hangar_n=" + hangars[1];
  sum += " depot_empty=" + (railDep[0] + roadDep[0] + waterDep[0]);
  sum += " depot_n=" + (railDep[1] + roadDep[1] + waterDep[1]);
  foreach (row in infra) {
    sum += " pieces_" + row[0] + "=" + AIInfrastructure.GetInfrastructurePieceCount(company, row[1]);
    sum += " cost_" + row[0] + "=" + AIInfrastructure.GetMonthlyInfrastructureCosts(company, row[1]);
  }
  OpexDecide("V262_ORPHAN_SUM", sum);
}
