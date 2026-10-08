"""Conservative compression bounds, separate from the exact-interval decoder."""
from station_supply import supply_intervals


def bounded_intervals(previous, current, *, surviving_growth=False):
    exact = supply_intervals(previous, current)
    if not previous.get("ok") or not current.get("ok"):
        return exact
    start, end = previous["economy_date"], current["economy_date"]
    if not 0 < end-start <= 32:
        return exact
    old = {(n["station"], n["cargo"]): n for n in previous["nodes"]}
    new = {(n["station"], n["cargo"]): n for n in current["nodes"]}
    result = []
    for row in exact:
        row = dict(row)
        a, b = old.get((row.get("station"), row.get("cargo"))), new.get((row.get("station"), row.get("cargo")))
        growth = False
        if surviving_growth and a is not None and b is not None:
            old_members = {tuple(member) for member in a["membership"]}
            new_members = {tuple(member) for member in b["membership"]}
            growth = old_members < new_members and all(a[k] == b[k] for k in
                        ("graph", "xy", "build_date"))
            # Merge rescales imported nodes only. AddNode never alters an
            # existing node. No graph transfer, removal or moved member allowed.
            if (growth and a["compression"] == b["compression"]
                    and b["supply"] >= a["supply"] and b["last_update"] >= a["last_update"]
                    and (b["supply"] == a["supply"] or b["last_update"] > start)):
                arrivals = b["supply"]-a["supply"]
                row.update(exact=True, reason=None, arrivals=arrivals,
                           monthly_captured=arrivals*30.4/(end-start),
                           continuity="surviving_graph_growth")
        if row["exact"]:
            row.update(bounded=True, lower=row["arrivals"], upper=row["arrivals"])
        else:
            row.update(bounded=False, lower=None, upper=None)
            identity = a is not None and b is not None and all(a[k] == b[k] for k in
                    ("graph", "xy", "build_date")) and (a["membership"] == b["membership"] or growth)
            if identity and b["compression"] > a["compression"]:
                # c' = floor((compression_day+c)/2). Bound the latest age
                # even for a first compression just after the initial save.
                times = (2*b["compression"]-a["compression"],
                         2*b["compression"]-a["compression"]+1)
                possible = any(start < t <= end and t-a["compression"] > 256 for t in times)
                min_after_first = (start+1+a["compression"])//2
                if (possible and end-min_after_first <= 256
                        and b["last_update"] >= a["last_update"]
                        and a["supply"] < 0x80000000 and b["supply"] < 0x80000000):
                    # b=floor((a+u)/2)+v, arrivals=u+v, u/v nonnegative.
                    lower = max(0, b["supply"]-a["supply"]//2)
                    upper = 2*b["supply"]+1-a["supply"]
                    if upper >= lower:
                        row.update(bounded=True, lower=lower, upper=upper,
                                   reason="single_compression_bounds")
                        if growth:
                            row["continuity"] = "surviving_graph_growth"
        result.append(row)
    return result
