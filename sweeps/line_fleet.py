"""Lecteur des journaux de composition (V257).

Cote OpexAI, `LINE_FLEET` est emis seulement sous `DECISION_LOG`. Le nom du
moteur est le dernier champ, car il contient des espaces et des apostrophes.
Cote AAAHogEx, `BuildTrain` (HgLog, capture `--script-debug`) decrit la rame
achetee : nom, nombre de locomotives, wagons. La puissance et l'EngineID n'y
figurent pas : ils ne sont pas inventes.

Le joint Opex se fait par identifiant de vehicule (VehicleID NoAI = index du
chunk VEHS). Le nom, la vitesse et la puissance ne sont copies que si
l'EngineID du journal est celui encore en service dans la sauvegarde.
"""
import re


_OPEX_FLEET = re.compile(
    r"OPEX (?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2}) LINE_FLEET (?P<body>.*)"
)
_BUILD_TRAIN = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2}) BuildTrain (?P<body>.*)"
)
_FLEET_MARK = re.compile(r"\)x(\d+)\s+")
_ROUTE_SPLIT = re.compile(
    r"^(?P<comp>.*?)(?P<single>\(single\))?(?= (?:T:)?\d{4})"
)
_WAGON_SUFFIX = re.compile(r"-(?P<name>[^-]+?)x(?P<count>\d+)$")
_LOCO_COUNT = re.compile(r"^(?P<name>.+?)x(?P<count>\d+)$")
_CRUISE_SPEED = re.compile(r"\bspeed:(\d+)")
_SNAPSHOT_DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_INT_KEYS = (
    "line", "engine", "vmax", "power", "wagons", "wagon",
    "trains", "wagons2", "wagon2",
)


def _snapshot_stamp(date_text):
    if not date_text:
        return None
    match = _SNAPSHOT_DATE.search(str(date_text))
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _event_stamp(event):
    return (event["year"], event["month"], event["day"])


def parse_opex_line_fleet(text):
    """Evenements LINE_FLEET. Une cle absente vaut None, jamais 0."""
    events = []
    for raw in (text or "").splitlines():
        match = _OPEX_FLEET.search(raw)
        if match is None:
            continue
        body = match.group("body")
        name = None
        if " name=" in body:
            body, name = body.split(" name=", 1)
        fields = {}
        vehicles = None
        for token in body.split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            if key == "mode":
                fields["mode"] = value
                continue
            if key == "vehs":
                vehicles = []
                for part in value.split(","):
                    if part == "":
                        continue
                    try:
                        vehicles.append(int(part))
                    except ValueError:
                        continue
                continue
            if key in _INT_KEYS:
                try:
                    fields[key] = int(value)
                except ValueError:
                    fields[key] = None
        event = {
            "year": int(match.group("year")),
            "month": int(match.group("month")),
            "day": int(match.group("day")),
            "mode": fields.get("mode"),
            "line": fields.get("line"),
            "engine": fields.get("engine"),
            "vmax": fields.get("vmax"),
            "power": fields.get("power"),
            "wagons": fields.get("wagons"),
            "wagon": fields.get("wagon"),
            "trains": fields.get("trains"),
            "vehs": vehicles if vehicles is not None else [],
            "name": name,
        }
        if "wagons2" in fields:
            event["wagons2"] = fields["wagons2"]
        if "wagon2" in fields:
            event["wagon2"] = fields["wagon2"]
        events.append(event)
    return events


def attach_opex_line_fleet(lines, events, up_to=None):
    """Joint le journal sur les lignes deja reconstruites depuis la sauvegarde.

    Les evenements posterieurs a `up_to` sont ignores : le journal capture est
    cumulatif. Le dernier evenement de chaque vehicule l'emporte.
    """
    cutoff = _snapshot_stamp(up_to) if up_to else None
    latest = {}
    for event in events or []:
        stamp = _event_stamp(event)
        if cutoff is not None and stamp > cutoff:
            continue
        for vehicle_id in event.get("vehs") or []:
            previous = latest.get(vehicle_id)
            if previous is None or stamp >= _event_stamp(previous):
                latest[vehicle_id] = event

    for line in lines or []:
        line.setdefault("engine_name", None)
        line.setdefault("max_speed", None)
        line.setdefault("power", None)
        line.setdefault("opex_line_id", None)
        matched = []
        seen = set()
        for vehicle_id in line.get("vehicle_ids") or []:
            event = latest.get(vehicle_id)
            if event is None or id(event) in seen:
                continue
            seen.add(id(event))
            matched.append(event)
        if not matched:
            continue

        line_ids = {event.get("line") for event in matched}
        if len(line_ids) == 1:
            only_line = next(iter(line_ids))
            if only_line is not None:
                line["opex_line_id"] = only_line

        log_engines = {event.get("engine") for event in matched}
        save_engine = line.get("engine_id")
        consists = line.get("consists") or []
        save_engines = [item.get("engine_id") for item in consists]
        save_has_no_engine = (not consists) or all(engine is None for engine in save_engines)
        if save_engine is None and save_has_no_engine and len(log_engines) == 1:
            only_engine = next(iter(log_engines))
            if only_engine is not None:
                line["engine_id"] = only_engine
                if not line.get("engine_ids"):
                    line["engine_ids"] = [only_engine]
                save_engine = only_engine
        if (
            save_engine is None
            or len(log_engines) != 1
            or next(iter(log_engines)) != save_engine
        ):
            continue

        names = {event.get("name") for event in matched}
        if len(names) == 1:
            line["engine_name"] = next(iter(names))
        if all(event.get("vmax") is not None for event in matched):
            speeds = {event.get("vmax") for event in matched}
            if len(speeds) == 1:
                line["max_speed"] = next(iter(speeds))
        if all(event.get("power") is not None for event in matched):
            powers = {event.get("power") for event in matched}
            if len(powers) == 1:
                line["power"] = next(iter(powers))
    return lines


def _parse_build_train_body(body, year, month, day):
    cut = body.split(" maxVehicles:", 1)[0]
    marks = list(_FLEET_MARK.finditer(cut))
    if not marks:
        return None
    last = marks[-1]
    tail = cut[last.end():]
    route = _ROUTE_SPLIT.match(tail)
    if route is None:
        return None
    composition = route.group("comp")
    wagons = []
    while True:
        wagon = _WAGON_SUFFIX.search(composition)
        if wagon is None:
            break
        wagons.append({"name": wagon.group("name"), "count": int(wagon.group("count"))})
        composition = composition[:wagon.start()]
    wagons.reverse()
    composition = composition.strip()
    if composition == "":
        return None
    loco = _LOCO_COUNT.match(composition)
    if loco is not None:
        loco_name = loco.group("name")
        locos = int(loco.group("count"))
    else:
        loco_name = composition
        locos = 1
    if loco_name == "":
        return None
    speed = _CRUISE_SPEED.search(body)
    return {
        "year": year,
        "month": month,
        "day": day,
        "date": "%d-%d-%d" % (year, month, day),
        "name": loco_name,
        "locos": locos,
        "wagons": sum(item["count"] for item in wagons),
        "wagons_by_name": wagons,
        "single": route.group("single") is not None,
        "vehicles_per_route": int(last.group(1)),
        "cruise_speed": int(speed.group(1)) if speed is not None else None,
    }


def parse_aaahogex_build_trains(text):
    """Achats BuildTrain. Les lignes en echec ou sans route lisible sont ignorees."""
    purchases = []
    for raw in (text or "").splitlines():
        if "BuildTrain failed" in raw or "BuildTrain HasVehicleEngineSet" in raw:
            continue
        match = _BUILD_TRAIN.search(raw)
        if match is None:
            continue
        purchase = _parse_build_train_body(
            match.group("body"),
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )
        if purchase is not None:
            purchases.append(purchase)
    return purchases


def summarize_build_trains_by_year(purchases, up_to=None):
    """Achats dont la date est <= up_to, groupes par annee civile."""
    cutoff = _snapshot_stamp(up_to) if up_to else None
    by_year = {}
    for purchase in purchases or []:
        if cutoff is not None and _event_stamp(purchase) > cutoff:
            continue
        year = str(purchase["year"])
        by_year.setdefault(year, []).append({
            "name": purchase["name"],
            "wagons": purchase["wagons"],
            "wagons_by_name": purchase["wagons_by_name"],
            "locos": purchase["locos"],
            "single": purchase["single"],
            "vehicles_per_route": purchase["vehicles_per_route"],
            "cruise_speed": purchase["cruise_speed"],
            "date": purchase["date"],
        })
    return by_year


def annotate_line_telemetry_logs(rec_opex, rec_aaa, output, date):
    """Complete la telemetrie deja extraite. Ne touche pas aux decisions."""
    text = output or ""
    opex_tel = (rec_opex or {}).get("line_telemetry")
    if isinstance(opex_tel, dict):
        attach_opex_line_fleet(
            opex_tel.get("lines") or [],
            parse_opex_line_fleet(text),
            up_to=date,
        )
    aaa_tel = (rec_aaa or {}).get("line_telemetry")
    if isinstance(aaa_tel, dict):
        aaa_tel["build_trains_by_year"] = summarize_build_trains_by_year(
            parse_aaahogex_build_trains(text),
            up_to=date,
        )
