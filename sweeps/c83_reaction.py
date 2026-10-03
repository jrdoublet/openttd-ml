"""Rare C83 enqueue/suppression events from the final cumulative engine log.

No events means unknown exposure, never a measured zero. These counts describe
the reactive regeneration branch, not airport losses or recalculation duration.
"""

from datetime import date
import re


def parse_c83_repairs(output):
    """Rare completed C83 jobs only; absence/invalid data remain unknown."""
    if not isinstance(output, str) or "C83_LOCAL_REPAIR" not in output:
        return None
    events = []
    fields = ("enabled", "town", "local", "fallback", "kept", "searched", "partners", "ops", "ticks")
    pattern = re.compile(r"C83_LOCAL_REPAIR " + " ".join(f"{name}=(\\d+)" for name in fields) + r"(?:\s|$)")
    for line in output.splitlines():
        if "C83_LOCAL_REPAIR" not in line:
            continue
        match = pattern.search(line)
        if match is None:
            return None
        event = dict(zip(fields, map(int, match.groups())))
        if event["enabled"] not in (0, 1) or (not event["enabled"] and any(event[key] for key in fields[2:7])):
            return None
        events.append(event)
    if not events or len({event["enabled"] for event in events}) != 1:
        return None
    return {"enabled": events[0]["enabled"], "completed": len(events),
            **{key: sum(event[key] for event in events) for key in fields[2:]}, "events": events}


EVENT = re.compile(
    r"OPEX (\d+)-(\d+)-(\d+) C83_REACTION enabled=([01]) "
    r"town=(\d+) action=(suppressed|enqueued|enqueue_failed)(?:\s|$)"
)


def parse_c83_reactions(output):
    """Return complete observed events and counts, or None if absent/malformed."""
    if not isinstance(output, str):
        return None
    events = []
    for line in output.splitlines():
        if " C83_REACTION " not in line:
            continue
        match = EVENT.search(line)
        if match is None:
            return None
        year, month, day, enabled, town, action = match.groups()
        try:
            stamp = date(int(year), int(month), int(day)).isoformat()
        except ValueError:
            return None
        enabled = int(enabled)
        if (action == "suppressed") != (enabled == 0):
            return None
        events.append({"date": stamp, "enabled": enabled,
                       "town": int(town), "action": action})
    if not events or len({event["enabled"] for event in events}) != 1:
        return None
    return {
        "enabled": events[0]["enabled"],
        "opportunities": len(events),
        "suppressed": sum(event["action"] == "suppressed" for event in events),
        "enqueued": sum(event["action"] == "enqueued" for event in events),
        "enqueue_failed": sum(event["action"] == "enqueue_failed" for event in events),
        "events": events,
    }
