#!/usr/bin/env python3
"""Decode CARTO-2 shadow experiments: paired free/guided A* and corridor costs.

Expected engine records (an arbitrary OpenTTD prefix before OPEX is accepted):

  OPEX 1970-1-20 CARTO2_START version=1 mapx=1024 mapy=1024
      start_year=1970 years=5 seed=1791467322 bit=24_25_26
  OPEX 1974-12-31 CARTO2_PAIR id=0 key=freight:0:1:2 src=1 dst=2 dist=240
  OPEX 1974-12-31 CARTO2_COST id=0 band_ops=160 line_ops=70
      band_ticks=0 line_ticks=0 band_cells=30 line_cells=10
  OPEX 1974-12-31 CARTO2_SEARCH id=0 mode=free phase=end outcome=OK
      iters=200 ops=4000 ticks=0 ready=1 path_dist=257
  OPEX 1974-12-31 CARTO2_SEARCH id=0 mode=guided phase=end outcome=OK
      iters=100 ops=2200 ticks=0 ready=1 path_dist=259
  OPEX 1974-12-31 CARTO2_SUMMARY phase=done pairs=1 mapped=1
      completed=1 ready=1 full_turns=8 full_turn_ops=70000
      paused_turns=2 year=1974
  OPEX 1974-12-31 CARTO2_TURN phase=full ops=9000 left=1000 year=1974
  OPEX 1974-12-31 CARTO2_COST id=1 map_mode=line line_ops=70
      band_ops=-1 line_cells=10 band_cells=-1

Whitespace above is illustrative; each event is ONE physical log line.
Runtime ready=1 is readiness at SEARCH, not persistence until end 1974:
the runtime cache can expire. End-1974 readiness requires a dated terminal
snapshot. START seed is the RLW sample/reservoir seed, not the game seed.
ops denotes search-only opcodes; ticks denotes crossed scheduler ticks, not
elapsed CPU time. line/band costs must include the same accounting scope.
When map_mode=line, negative band sentinels are unobserved, not negative work.
TURN observations and SUMMARY cumulative V309 counts are not additive.
The runtime may omit TURN logs on low-leftover turns: SUMMARY is authoritative,
and TURN is a logged subset of all full turns.
Use stable id and key, with one end event per mode/pair. No join on src/dst.

By default reporting is descriptive. --require-complete additionally requires
complete records, a done summary and verified healthy game horizon from BOTH
the result JSON and the manifest JSON. An event dated 1974 is not evidence
that a five-year engine game completed.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import json
from pathlib import Path
import re
import statistics


LOG_NAME = re.compile(
    r"^(?P<policy>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$", re.I
)
EVENT = re.compile(
    r"\bOPEX\s+(?P<date>\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(?P<tag>CARTO2_(?:START|PAIR|COST|SEARCH|ASTAR|SUMMARY|SAFETY|TURN))"
    r"(?:\s+(?P<fields>.*))?$"
)
FIELD = re.compile(r"(?<!\S)([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)")
MODES = {"free": "free", "libre": "free", "guided": "guided", "guide": "guided", "guidé": "guided"}
OUTCOMES = {"OK", "ABND", "DEAD", "NOPA", "FAIL", "TIMEOUT", "CANCEL"}
READY_FIELDS = ("ready1974", "ready_1974", "ready")
EXPECTED_YEAR = 1974


def number(value):
    try:
        n = int(value)
    except (ValueError, TypeError):
        return None
    return n if n >= 0 else None


def metric(values):
    values = list(values)
    return {"n": len(values), "sum": sum(values),
            "mean": round(statistics.mean(values), 4) if values else None,
            "median": statistics.median(values) if values else None}


def identity(path):
    match = LOG_NAME.fullmatch(Path(path).name)
    if not match:
        raise ValueError(f"Journal attendu <policy>_seed<N>_r<K>.log[.gz] : {path}")
    return match["policy"], int(match["seed"]), int(match["repeat"])


def decode_line(text):
    match = EVENT.search(text.rstrip())
    if not match:
        return None
    try:
        parts = [int(part) for part in match["date"].split("-")]
        when = date(*parts)
    except ValueError:
        return None
    return when, match["tag"], dict(FIELD.findall(match["fields"] or ""))


def _ready(fields):
    raw = next((fields[name] for name in READY_FIELDS if name in fields), None)
    if raw in ("1", "0"):
        return int(raw)
    return None


def _search(fields, *, when, expected_year=EXPECTED_YEAR):
    outcome = fields.get("outcome", "").upper()
    result = {
        "outcome": outcome,
        "iters": number(fields.get("iters")),
        "ops": number(fields.get("ops", fields.get("search_ops"))),
        "ticks": number(fields.get("ticks", fields.get("overruns"))),
        "ready_at_search": _ready(fields),
        "path_dist": number(fields.get("path_dist", fields.get("path_distance"))),
    }
    # -1 means missing (NOPA, DEAD, CANCEL); absence may also be legitimate.
    explicit = next((fields[name] for name in ("ready1974", "ready_1974")
                     if name in fields), None)
    if explicit is not None:
        result["ready1974"] = int(explicit) if explicit in ("0", "1") else None
    elif when == date(expected_year, 12, 31):
        result["ready1974"] = result["ready_at_search"]
    else:
        result["ready1974"] = None
    errors = []
    for field in ("iters", "ops", "ticks", "ready_at_search"):
        if result[field] is None:
            errors.append(f"SEARCH {field} absent ou invalide")
    if outcome not in OUTCOMES:
        errors.append(f"SEARCH outcome inconnu {outcome!r}")
    if explicit is not None and result["ready1974"] is None:
        errors.append("SEARCH ready1974 invalide")
    if result["ready_at_search"] == 1:
        if outcome != "OK":
            errors.append("SEARCH ready=1 avec outcome différent de OK")
    if outcome != "OK" and result["path_dist"] not in (0, None):
        errors.append("SEARCH échec avec path_dist non nul")
    if result["path_dist"] == 0:
        result["path_dist"] = None  # an unusable or absent length is not a real 0 km route
    return result, errors


def _cost(fields):
    map_mode = fields.get("map_mode", "band")
    result = {"map_mode": map_mode}
    errors = []
    if map_mode not in ("band", "line"):
        errors.append(f"COST map_mode inconnu {map_mode!r}")
    for name in ("line_ops", "line_ticks", "line_cells"):
        result[name] = number(fields.get(name))
        if result[name] is None:
            errors.append(f"COST {name} absent ou invalide")
    for name in ("band_ops", "band_ticks", "band_cells"):
        raw = fields.get(name)
        result[name] = None if map_mode == "line" and raw in (None, "-1") else number(raw)
        if map_mode == "line" and result[name] is not None:
            if name != "band_ticks" or result[name] != 0:
                errors.append(f"COST {name} doit être non mesuré en map_mode=line")
            result[name] = None
        if map_mode != "line" and result[name] is None:
            errors.append(f"COST {name} absent ou invalide")
    for name in ("line_cells", "band_cells"):
        if result[name] == 0:
            errors.append(f"COST {name} zéro")
    if (result["band_cells"] is not None and result["line_cells"] is not None
            and result["band_cells"] < result["line_cells"]):
        errors.append("COST band_cells inférieur à line_cells (bande non englobante)")
    if result["line_ops"] is not None and result["band_ops"] is not None:
        result["extra_ops"] = result["band_ops"] - result["line_ops"]
        result["ops_ratio"] = (round(result["band_ops"] / result["line_ops"], 6)
                               if result["line_ops"] else None)
    else:
        result["extra_ops"] = result["ops_ratio"] = None
    if result["line_cells"] and result["band_cells"] is not None:
        result["cells_ratio"] = round(result["band_cells"] / result["line_cells"], 6)
    else:
        result["cells_ratio"] = None
    return result, errors


def _turn(fields, when):
    """CARTO2_TURN is a whole-turn execution, not a rail pair event."""
    result = {
        "date": when.isoformat(), "phase": fields.get("phase"),
        "ops": number(fields.get("ops")), "left": number(fields.get("left")),
        "year": number(fields.get("year")),
    }
    errors = []
    if result["phase"] != "full":
        errors.append("TURN phase inconnue")
    for name in ("ops", "left"):
        if result[name] is None:
            errors.append(f"TURN {name} absent ou invalide")
        elif result[name] > 10000:
            errors.append(f"TURN {name} hors budget 10000")
    if result["year"] is None or result["year"] != when.year:
        errors.append("TURN year incohérent avec date")
    if fields.get("date") is not None:
        try:
            stamp = date(*(int(part) for part in fields["date"].split("-")))
        except (ValueError, TypeError):
            stamp = None
        if stamp != when:
            errors.append("TURN date incohérente")
    if "count" in fields:
        result["step_count"] = number(fields["count"])
        if result["step_count"] is None:
            errors.append("TURN count absent ou invalide")
    return result, errors


def _classify(free, guided):
    if free["ready_at_search"] and guided["ready_at_search"]:
        return "both_ready"
    if guided["ready_at_search"]:
        return "guided_only_ready"
    if free["ready_at_search"]:
        return "free_only_ready"
    return "neither_ready"


def parse_game(source, lines, *, expected_year=EXPECTED_YEAR):
    """Keep episodes distinct; reject duplicate terminal results and key conflicts."""
    policy, seed, repeat = identity(source)
    errors, counts, pairs = [], Counter(), {}
    start, summary, first, last = None, None, None, None
    last_summary_date = None
    turns = []
    for line_no, line in enumerate(lines, 1):
        parsed = decode_line(line)
        if parsed is None:
            if "OPEX " in line and "CARTO2_" in line:
                errors.append(f"ligne {line_no}: CARTO2 illisible")
            continue
        when, tag, fields = parsed
        counts[tag] += 1
        first = min(first, when) if first else when
        last = max(last, when) if last else when
        if when.year > expected_year:
            errors.append(f"ligne {line_no}: CARTO2 postérieur à {expected_year}")
        if tag == "CARTO2_START":
            if start is not None:
                errors.append(f"ligne {line_no}: START dupliqué")
            else:
                start = fields
            # START seed is the deterministic RLW reservoir seed, not the game's
            # map seed in the filename. Only an explicit game_seed is comparable.
            if (fields.get("game_seed") is not None
                    and number(fields["game_seed"]) != seed):
                errors.append(f"ligne {line_no}: game_seed START différent du fichier")
            continue
        if tag == "CARTO2_SUMMARY":
            summary = fields  # Last snapshot wins, as in CARTO-1.
            last_summary_date = when
            continue
        if tag == "CARTO2_TURN":
            turn, turn_errors = _turn(fields, when)
            for err in turn_errors:
                errors.append(f"ligne {line_no}: {err}")
            if not turn_errors:
                turns.append(turn)
            continue
        if tag == "CARTO2_SAFETY":
            errors.append(f"ligne {line_no}: SAFETY {fields.get('reason', 'unknown')}")
            continue
        pair_id = number(fields.get("id", fields.get("pair")))
        if pair_id is None:
            errors.append(f"ligne {line_no}: {tag} sans id de paire")
            continue
        pair = pairs.setdefault(pair_id, {"id": pair_id, "pair": None,
                                           "cost": None, "search": {}, "dates": []})
        pair["dates"].append(when.isoformat())
        if tag == "CARTO2_PAIR":
            if pair["pair"] is not None:
                errors.append(f"ligne {line_no}: PAIR id={pair_id} dupliqué")
            else:
                pair["pair"] = fields
        elif tag == "CARTO2_COST":
            if pair["cost"] is not None:
                errors.append(f"ligne {line_no}: COST id={pair_id} dupliqué")
            else:
                pair["cost"] = fields
        else:
            if fields.get("phase", "end") == "start":
                continue
            if fields.get("phase", "end") != "end":
                errors.append(f"ligne {line_no}: SEARCH phase inconnue")
                continue
            mode = MODES.get(fields.get("mode", fields.get("arm", "")).lower())
            if mode is None:
                errors.append(f"ligne {line_no}: SEARCH mode absent/inconnu")
                continue
            if mode in pair["search"]:
                errors.append(f"ligne {line_no}: id={pair_id} SEARCH {mode} dupliqué")
            else:
                pair["search"][mode] = (fields, when)

    if start is None:
        errors.append("CARTO2_START absent (provenance de log insuffisante)")
    if summary is None:
        errors.append("CARTO2_SUMMARY absent")
    else:
        if summary.get("phase") != "done":
            errors.append("CARTO2_SUMMARY phase=done absent")
        if number(summary.get("year")) is None:
            errors.append("SUMMARY year absent ou invalide")
        elif last_summary_date and number(summary.get("year")) != last_summary_date.year:
            errors.append("SUMMARY year incohérent avec sa date moteur")
        if number(summary.get("pairs")) != len(pairs):
            errors.append(f"SUMMARY pairs discordant ({len(pairs)} observées)")
        if summary.get("phase") == "done":
            for field, observed in (("mapped", sum(p["cost"] is not None for p in pairs.values())),
                                    ("completed", sum(len(p["search"]) == 2 for p in pairs.values()))):
                if field in summary and number(summary[field]) != observed:
                    errors.append(f"SUMMARY {field} discordant ({observed} observés)")
        v309_fields = ("full_turns", "full_turn_ops", "paused_turns")
        if any(field in summary for field in v309_fields):
            for field in v309_fields:
                if number(summary.get(field)) is None:
                    errors.append(f"SUMMARY {field} absent ou invalide")
            if summary.get("phase") == "done":
                for field, observed in (("full_turns", len(turns)),
                                        ("full_turn_ops", sum(t["ops"] for t in turns))):
                    # CARTO2_TURN may be intentionally omitted for a turn
                    # with <2500 ops left. SUMMARY is the authoritative
                    # cumulative value; event totals are only lower bounds.
                    if number(summary.get(field)) is not None and number(summary[field]) < observed:
                        errors.append(f"SUMMARY {field} inférieur au journal ({observed} observés)")
    records = []
    mapped = []
    search_partial_records = []
    pending = Counter()
    for pair_id, episode in sorted(pairs.items()):
        base = episode["pair"]
        if base is None:
            errors.append(f"id={pair_id}: PAIR absent")
            continue
        key = base.get("key")
        src, dst = number(base.get("src")), number(base.get("dst"))
        dist = number(base.get("dist", base.get("distance")))
        if not key or src is None or dst is None or not dist:
            errors.append(f"id={pair_id}: key/src/dst/dist manquants ou invalides")
            continue
        invalid_key = False
        for slot in (episode["cost"], *(s[0] for s in episode["search"].values())):
            if slot is not None and slot.get("key", key) != key:
                invalid_key = True
        if invalid_key:
            errors.append(f"id={pair_id}: clé discordante entre événements")
            continue
        source_kind = base.get("source", "unknown")
        # Decode every finished SEARCH independently of COST / the opposite
        # mode. A half-completed five-year run can contain valuable work and
        # still fail the strict paired/done completeness gate.
        decoded_search = {}
        invalid_search = False
        for mode, (search_fields, search_date) in sorted(episode["search"].items()):
            decoded, search_errors = _search(
                search_fields, when=search_date, expected_year=expected_year)
            for error in search_errors:
                errors.append(f"id={pair_id}: {mode} {error}")
            if search_errors:
                invalid_search = True
                continue
            decoded_search[mode] = decoded
            search_partial_records.append({
                "id": pair_id, "key": key, "source": source_kind,
                "seed": seed, "repeat": repeat,
                "mode": mode, "date": search_date.isoformat(),
                **decoded,
            })
        if episode["cost"] is not None:
            cost, cost_errors = _cost(episode["cost"])
            for error in cost_errors:
                errors.append(f"id={pair_id}: {error}")
            if not cost_errors:
                mapped.append({"id": pair_id, "key": key, "source": source_kind, **cost})
        if episode["cost"] is None or set(episode["search"]) != {"free", "guided"}:
            errors.append(f"id={pair_id}: COST ou bras free/guided absent")
            if episode["cost"] is None:
                pending["awaiting_cost"] += 1
            elif set(episode["search"]) != {"free", "guided"}:
                pending["awaiting_search"] += 1
            continue
        if cost_errors or invalid_search:
            continue
        free = decoded_search["free"]
        guided = decoded_search["guided"]
        quality = None
        if free["path_dist"] and guided["path_dist"]:
            quality = {
                "free_stretch": round(free["path_dist"] / dist, 6),
                "guided_stretch": round(guided["path_dist"] / dist, 6),
                "guided_minus_free_dist": guided["path_dist"] - free["path_dist"],
                "guided_vs_free_ratio": round(guided["path_dist"] / free["path_dist"], 6),
                "class": ("guided_shorter" if guided["path_dist"] < free["path_dist"]
                          else "guided_longer" if guided["path_dist"] > free["path_dist"]
                          else "equal"),
            }
        records.append({
            "id": pair_id, "key": key, "seed": seed, "repeat": repeat,
            "src": src, "dst": dst, "dist": dist,
            "source_kind": source_kind,
            "free": free, "guided": guided, "cost": cost,
            "class": _classify(free, guided), "quality": quality,
            "saved_iters": free["iters"] - guided["iters"],
            "saved_ops": free["ops"] - guided["ops"],
            "saved_ticks": free["ticks"] - guided["ticks"],
            "both_astar_ok": free["outcome"] == "OK" and guided["outcome"] == "OK"
                              and free["ready_at_search"] == 1
                              and guided["ready_at_search"] == 1,
        })
    if len(records) != len(pairs):
        errors.append(f"paires complètement décodées {len(records)}/{len(pairs)}")
    ready_terminal_snapshot = (
        number(summary.get("ready")) if summary and last_summary_date ==
        date(expected_year, 12, 31) else None
    )
    v309 = summarize_turns(turns, summary)
    return {
        "source": str(source), "policy": policy, "seed": seed, "repeat": repeat,
        "first_event_date": first.isoformat() if first else None,
        "last_event_date": last.isoformat() if last else None,
        "start": start, "summary": summary, "events": dict(counts),
        "last_summary_date": last_summary_date.isoformat() if last_summary_date else None,
        "ready_at_end_snapshot": ready_terminal_snapshot,
        "readiness": {
            "ready_at_end_snapshot": ready_terminal_snapshot,
            "snapshot_on_end_date": last_summary_date == date(expected_year, 12, 31),
            "cache_ttl_days": 180,
            "note": "Une recherche OK peut expirer avant la fin de période ; "
                    "seul un résumé au dernier jour atteste le cache encore prêt.",
        },
        "turn_records": turns, "v309_turns": v309,
        "reservoir_seed": number(start.get("seed")) if start else None,
        "pairs_seen": len(pairs), "pairs_valid": len(records),
        "mapped": mapped, "mapped_count": len(mapped),
        "search_partial_records": search_partial_records,
        "search_partial": summarize_search_partial(search_partial_records),
        "pending": dict(pending),
        "pair_sources": dict(Counter(
            episode["pair"].get("source", "unknown")
            for episode in pairs.values() if episode["pair"] is not None)),
        "rows": records, "errors": errors, "log_complete": not errors,
        "campaign_verified": False, "campaign_errors": ["preuves harnais JSON/manifeste non fournies"],
    }


def summarize(rows):
    classes = Counter(row["class"] for row in rows)
    quality = Counter(row["quality"]["class"] for row in rows if row["quality"])
    final_free = [row["free"]["ready1974"] for row in rows]
    final_guided = [row["guided"]["ready1974"] for row in rows]
    return {
        "pairs": len(rows), "classification": dict(sorted(classes.items())),
        "source_counts": dict(sorted(Counter(row["source_kind"] for row in rows).items())),
        "quality_classification": dict(sorted(quality.items())),
        "free_ready_at_search": sum(row["free"]["ready_at_search"] for row in rows),
        "guided_ready_at_search": sum(row["guided"]["ready_at_search"] for row in rows),
        "free_ready1974": sum(final_free) if final_free and all(
            v is not None for v in final_free) else None,
        "guided_ready1974": sum(final_guided) if final_guided and all(
            v is not None for v in final_guided) else None,
        "free_ready1974_observed": sum(v == 1 for v in final_free),
        "guided_ready1974_observed": sum(v == 1 for v in final_guided),
        "unknown_ready1974": sum(v is None for v in final_free + final_guided),
        "outcomes_free": dict(sorted(Counter(row["free"]["outcome"] for row in rows).items())),
        "outcomes_guided": dict(sorted(Counter(row["guided"]["outcome"] for row in rows).items())),
        "saved_iters": metric(row["saved_iters"] for row in rows),
        "saved_ops": metric(row["saved_ops"] for row in rows),
        "saved_ticks": metric(row["saved_ticks"] for row in rows),
        "free_iters": metric(row["free"]["iters"] for row in rows),
        "guided_iters": metric(row["guided"]["iters"] for row in rows),
        "free_ops": metric(row["free"]["ops"] for row in rows),
        "guided_ops": metric(row["guided"]["ops"] for row in rows),
        "free_ticks_crossed": metric(row["free"]["ticks"] for row in rows),
        "guided_ticks_crossed": metric(row["guided"]["ticks"] for row in rows),
        "map_mode_counts": dict(sorted(Counter(row["cost"]["map_mode"] for row in rows).items())),
        "band_ops": metric(row["cost"]["band_ops"] for row in rows if row["cost"]["band_ops"] is not None),
        "line_ops": metric(row["cost"]["line_ops"] for row in rows),
        "band_extra_ops": metric(row["cost"]["extra_ops"] for row in rows if row["cost"]["extra_ops"] is not None),
        "band_ticks_crossed": metric(row["cost"]["band_ticks"] for row in rows if row["cost"]["band_ticks"] is not None),
        "line_ticks_crossed": metric(row["cost"]["line_ticks"] for row in rows),
        "band_cells": metric(row["cost"]["band_cells"] for row in rows if row["cost"]["band_cells"] is not None),
        "line_cells": metric(row["cost"]["line_cells"] for row in rows),
        "path_distance_delta": metric(row["quality"]["guided_minus_free_dist"]
                                      for row in rows if row["quality"]),
        "guided_path_vs_free": metric(row["quality"]["guided_vs_free_ratio"]
                                      for row in rows if row["quality"]),
    }


def summarize_mapped(mapped):
    return {
        "mapped": len(mapped),
        "by_source": dict(sorted(Counter(row["source"] for row in mapped).items())),
        "by_map_mode": dict(sorted(Counter(row["map_mode"] for row in mapped).items())),
        **{name: metric(row[name] for row in mapped if row[name] is not None)
           for name in ("band_ops", "line_ops", "extra_ops", "band_ticks",
                        "line_ticks", "band_cells", "line_cells")},
    }


def summarize_turns(turns, summary=None):
    """Separate observed TURN subset from authoritative SUMMARY counters."""
    raw = summary or {}
    return {
        "observed_full_turns": len(turns),
        "observed_full_turn_ops": metric(t["ops"] for t in turns),
        "observed_left": metric(t["left"] for t in turns),
        "reported_full_turns": number(raw.get("full_turns")),
        "reported_full_turn_ops": number(raw.get("full_turn_ops")),
        "reported_paused_turns": number(raw.get("paused_turns")),
        "reported_runtime_ticks": number(raw.get("ticks")),
        "unlogged_full_turns": (number(raw.get("full_turns")) - len(turns)
                                if number(raw.get("full_turns")) is not None
                                and number(raw.get("full_turns")) >= len(turns) else None),
        "unlogged_full_turn_ops": (number(raw.get("full_turn_ops")) - sum(t["ops"] for t in turns)
                                   if number(raw.get("full_turn_ops")) is not None
                                   and number(raw.get("full_turn_ops")) >= sum(t["ops"] for t in turns)
                                   else None),
        "summary_phase": raw.get("phase"),
    }


def summarize_ok_pairs(rows):
    """Comparable paired successes ONLY; CANCEL/NOPA/ABND are excluded."""
    ok = [row for row in rows if row["both_astar_ok"]]
    distances = [row for row in ok if row["quality"] is not None]
    return {
        "count": len(ok),
        "with_known_distances": len(distances),
        "free_iters": metric(row["free"]["iters"] for row in ok),
        "guided_iters": metric(row["guided"]["iters"] for row in ok),
        "saved_iters": metric(row["saved_iters"] for row in ok),
        "free_ops": metric(row["free"]["ops"] for row in ok),
        "guided_ops": metric(row["guided"]["ops"] for row in ok),
        "saved_ops": metric(row["saved_ops"] for row in ok),
        "free_ticks": metric(row["free"]["ticks"] for row in ok),
        "guided_ticks": metric(row["guided"]["ticks"] for row in ok),
        "saved_ticks": metric(row["saved_ticks"] for row in ok),
        "free_path_dist": metric(row["free"]["path_dist"] for row in distances),
        "guided_path_dist": metric(row["guided"]["path_dist"] for row in distances),
        "saved_path_dist": metric(-row["quality"]["guided_minus_free_dist"] for row in distances),
        "path_distance_delta": metric(row["quality"]["guided_minus_free_dist"] for row in distances),
        "guided_path_vs_free": metric(row["quality"]["guided_vs_free_ratio"] for row in distances),
        "quality_classification": dict(sorted(Counter(
            row["quality"]["class"] for row in distances).items())),
        "pairs": [{"seed": row["seed"], "repeat": row["repeat"],
                   "id": row["id"], "key": row["key"],
                   "free": row["free"], "guided": row["guided"],
                   "saved_iters": row["saved_iters"], "saved_ops": row["saved_ops"],
                   "saved_ticks": row["saved_ticks"],
                   "quality": row["quality"]} for row in ok],
    }


def summarize_search_partial(records):
    """All valid terminal SEARCH events, including those with no paired row.

    Each event contributes once to totals, even when both modes of an id are
    present and that pair also appears in the strict paired comparison.
    """
    def by_mode(items):
        return {
            "count": len(items),
            "iters": metric(row["iters"] for row in items),
            "ops": metric(row["ops"] for row in items),
            "ticks": metric(row["ticks"] for row in items),
            "outcomes": dict(sorted(Counter(row["outcome"] for row in items).items())),
            "ready_at_search": sum(row["ready_at_search"] for row in items),
            "source_counts": dict(sorted(Counter(row["source"] for row in items).items())),
        }
    return {
        **by_mode(records),
        "modes": {
            mode: by_mode([row for row in records if row["mode"] == mode])
            for mode in ("free", "guided")
        },
        "distinct_pair_ids": len({
            (row["seed"], row["repeat"], row["id"]) for row in records
        }),
    }


def analyze_sources(sources, *, expected_year=EXPECTED_YEAR):
    games = [parse_game(path, lines, expected_year=expected_year) for path, lines in sources]
    skipped = [game["source"] for game in games if not any(
        name.startswith("CARTO2_") for name in game["events"])]
    games = [game for game in games if game["source"] not in skipped]
    if not games:
        raise ValueError("Aucun événement CARTO2_* dans les journaux fournis")
    seen = set()
    for game in games:
        key = (game["policy"], game["seed"], game["repeat"])
        if key in seen:
            game["errors"].append("jeu policy/seed/repeat dupliqué")
            game["log_complete"] = False
        seen.add(key)
    policies = {}
    for name in sorted({g["policy"] for g in games}):
        group = sorted((g for g in games if g["policy"] == name),
                       key=lambda g: (g["seed"], g["repeat"]))
        rows = [row for game in group for row in game["rows"]]
        mapped = [row for game in group for row in game["mapped"]]
        partial_searches = [row for game in group for row in game["search_partial_records"]]
        turns = [t for game in group for t in game["turn_records"]]
        reported_full_turns = [g["v309_turns"]["reported_full_turns"] for g in group]
        reported_full_turn_ops = [g["v309_turns"]["reported_full_turn_ops"] for g in group]
        reported_paused_turns = [g["v309_turns"]["reported_paused_turns"] for g in group]
        reported_runtime_ticks = [g["v309_turns"]["reported_runtime_ticks"] for g in group]
        policies[name] = {
            "games": group, "aggregate": summarize(rows),
            "astar_ok_pairs": summarize_ok_pairs(rows),
            "by_source": {
                source: summarize([r for r in rows if r["source_kind"] == source])
                for source in sorted({r["source_kind"] for r in rows})
            },
            "mapped_partial": summarize_mapped(mapped),
            "search_partial": summarize_search_partial(partial_searches),
            "v309_turns": {
                **summarize_turns(turns),
                "reported_full_turns": sum(v for v in reported_full_turns if v is not None)
                                       if all(v is not None for v in reported_full_turns) else None,
                "reported_full_turn_ops": sum(v for v in reported_full_turn_ops if v is not None)
                                          if all(v is not None for v in reported_full_turn_ops) else None,
                "reported_paused_turns": sum(v for v in reported_paused_turns if v is not None)
                                         if all(v is not None for v in reported_paused_turns) else None,
                "reported_runtime_ticks": sum(v for v in reported_runtime_ticks if v is not None)
                                          if all(v is not None for v in reported_runtime_ticks) else None,
            },
            "log_complete": all(game["log_complete"] for game in group),
            "campaign_verified": False, "complete": False,
            "errors": [f"seed{g['seed']}/r{g['repeat']}: {e}"
                       for g in group for e in g["errors"]],
        }
    return {
        "scope": "CARTO2_shadow_paired_descriptive",
        "expected_end_year": expected_year,
        "ignored_no_carto2_logs": skipped,
        "limitations": [
            "Les deux bras sont mesurés en shadow: aucun gain économique ou constructeur démontré.",
            "Les deltas A* comparables sont limités aux paires de succès OK/OK avec même id/key ; "
            "la stabilité des plans et du monde doit être attestée séparément.",
            "Les mesures incomplètes restent visibles mais ne peuvent pas qualifier la campagne.",
            "ready=1 dans CARTO2_SEARCH exprime la réussite à cette date, pas la présence fin 1974.",
            "Le cache prêt expire 180 jours après insertion ; seul SUMMARY.ready daté du "
            "31 décembre atteste une disponibilité terminale, sinon inconnu.",
            "Les compteurs full_turns/full_turn_ops/paused_turns de SUMMARY sont des cumuls : "
            "ne pas additionner des snapshots intermédiaires.",
            "Les CARTO2_TURN sont échantillonnés lorsque le reliquat est suffisant : "
            "leurs sommes sont des bornes inférieures aux totaux SUMMARY.",
            "band_ops=-1 en map_mode=line signifie bande non mesurée, pas un gain constaté.",
            "La qualité de distance n'est évaluée que lorsque les deux longueurs sont disponibles.",
            "La population source=live est distinguée de source=long.",
            "Seul le JSON de partie et son manifeste prouvent le terme du banc."
        ],
        "policies": policies,
    }


def validate_campaign(report, result_json, manifest_json):
    """Corroborate the game horizon, policy and source provenance; fail closed."""
    config = manifest_json.get("configuration", {})
    opts = manifest_json.get("execution", {}).get("options", {})
    result_games = result_json.get("games", [])
    manifest_games = manifest_json.get("games", [])
    expected = report["expected_end_year"]
    years = result_json.get("years")
    start_year = result_json.get("start_year")
    errs = []
    if not result_json.get("campaign_id") or (
            result_json.get("campaign_id") != manifest_json.get("campaign_id")):
        errs.append("campaign_id JSON/manifeste absent ou discordant")
    if type(years) is not int or years <= 0 or config.get("years") != years:
        errs.append("horizon years absent ou JSON/manifeste discordant")
    if (type(start_year) is not int or type(years) is not int
            or start_year + years - 1 != expected
            or result_json.get("expected_last_year") != expected
            or config.get("starting_year") != start_year):
        errs.append(f"horizon attendu fin {expected} non établi")
    if result_json.get("seeds") != config.get("seeds") or (
            result_json.get("repeats") != config.get("repeats")):
        errs.append("graines/répétitions JSON/manifeste discordantes")
    if result_json.get("map_size") != config.get("map_size"):
        errs.append("taille de carte JSON/manifeste discordante")
    sha = manifest_json.get("git", {}).get("sha")
    if not sha:
        errs.append("SHA source Git absent du manifeste")
    bundle_sha = manifest_json.get("source_bundle", {}).get("sha256")
    if not bundle_sha or result_json.get("source_bundle_sha256") != bundle_sha:
        errs.append("SHA256 bundle source JSON/manifeste absent ou divergent")
    if not opts.get("docker_image_id"):
        errs.append("empreinte de l'image Docker absente du manifeste")
    if opts.get("script_debug") is not True:
        errs.append("script_debug absent du manifeste")
    keys = [(g.get("policy_id"), g.get("seed"), g.get("repeat")) for g in result_games]
    mkeys = [(g.get("policy_id"), g.get("seed"), g.get("repeat")) for g in manifest_games]
    if len(keys) != len(set(keys)) or len(mkeys) != len(set(mkeys)):
        errs.append("jeu dupliqué dans les preuves JSON/manifeste")
    if set(keys) != set(mkeys):
        errs.append("jeux JSON/manifeste différents")
    by_game = {key: game for key, game in zip(keys, result_games)}
    for name, policy in report["policies"].items():
        issues = errs.copy()
        observed = {(g["policy"], g["seed"], g["repeat"]) for g in policy["games"]}
        scope = {key for key in keys if key[0] == name}
        if scope != observed:
            issues.append(f"ensemble des parties de {name} divergent des journaux")
        for game in policy["games"]:
            key = (name, game["seed"], game["repeat"])
            evidence = by_game.get(key)
            if evidence is None:
                issues.append(f"partie {key} absente du JSON")
                continue
            if (evidence.get("game_ok") is not True
                    or evidence.get("game_status") != "complete"
                    or evidence.get("unattributed_errors")
                    or not evidence.get("companies", {}).get("OpexAI", {}).get("horizon_complete")):
                issues.append(f"partie {key} incomplète/non saine")
            expected_log = Path(evidence.get("engine_log_path") or "").name
            if expected_log != Path(game["source"]).name.removesuffix(".gz"):
                issues.append(f"journal déclaré différent pour {key}")
            if game["start"] is not None:
                start_sha = game["start"].get("source_sha", game["start"].get("git_sha"))
                if start_sha and start_sha != sha:
                    issues.append(f"SHA START/manifeste différent pour {key}")
                start_bundle = game["start"].get("bundle_sha")
                if start_bundle and start_bundle != bundle_sha:
                    issues.append(f"SHA bundle START/manifeste différent pour {key}")
                if (game["start"].get("game_seed") is not None
                        and number(game["start"]["game_seed"]) != game["seed"]):
                    issues.append(f"game_seed START/fichier différent pour {key}")
                map_size = result_json.get("map_size")
                for dimension in ("mapx", "mapy"):
                    observed_map = number(game["start"].get(dimension))
                    if (observed_map is not None and type(map_size) is int
                            and observed_map != 2 ** map_size):
                        issues.append(f"START {dimension} différent de la carte harnais pour {key}")
                if (game["start"].get("start_year") is not None
                        and number(game["start"]["start_year"]) != start_year):
                    issues.append(f"START start_year/harnais différent pour {key}")
            for field in ("first_event_date", "last_event_date"):
                stamp = game[field]
                if stamp and type(start_year) is int and not (
                        start_year <= int(stamp[:4]) <= expected):
                    issues.append(f"date {field} hors horizon pour {key}")
            game["campaign_verified"] = False  # updated after evaluating all issues
        policy["campaign_verified"] = not issues
        policy["complete"] = policy["log_complete"] and not issues
        policy["campaign_errors"] = issues
        for game in policy["games"]:
            game["campaign_verified"] = not issues
            game["campaign_errors"] = issues.copy()
    report["provenance"] = {
        "campaign_id": result_json.get("campaign_id"), "git_sha": sha,
        "source_bundle_sha256": bundle_sha,
        "docker_image_id": opts.get("docker_image_id"),
        "start_year": start_year, "years": years,
        "expected_last_year": expected,
        "manifest_years": config.get("years"),
        "game_count": len(result_games),
    }
    return report


def _open(path):
    return (gzip.open(path, "rt", encoding="utf-8", errors="replace")
            if path.name.endswith(".gz")
            else path.open("rt", encoding="utf-8", errors="replace"))


def find_logs(inputs):
    found = {}
    for item in inputs:
        path = Path(item)
        if not path.exists():
            raise FileNotFoundError(path)
        paths = path.iterdir() if path.is_dir() else (path,)
        for candidate in paths:
            if candidate.is_file() and LOG_NAME.fullmatch(candidate.name):
                found[str(candidate.resolve())] = candidate
    if not found:
        raise ValueError("Aucun journal <policy>_seed<N>_r<K>.log[.gz]")
    return [found[key] for key in sorted(found)]


def analyze_paths(inputs, *, result_json=None, manifest=None, expected_year=EXPECTED_YEAR):
    paths = find_logs(inputs)
    def sources():
        for path in paths:
            with _open(path) as handle:
                yield str(path), handle
    report = analyze_sources(sources(), expected_year=expected_year)
    if (result_json is None) != (manifest is None):
        raise ValueError("Fournir --result-json ET --manifest pour vérifier la campagne")
    if result_json is not None:
        result = json.loads(Path(result_json).read_text(encoding="utf-8"))
        manifest_data = json.loads(Path(manifest).read_text(encoding="utf-8"))
        validate_campaign(report, result, manifest_data)
    return report


def render_markdown(report, *, show_pairs=False):
    lines = ["# CARTO-2 — recherche libre/guidée et coût du couloir", "",
             f"Échéance de disponibilité : fin {report['expected_end_year']}.", ""]
    for name, policy in report["policies"].items():
        agg = policy["aggregate"]
        ok = policy["astar_ok_pairs"]
        v309 = policy["v309_turns"]
        lines.extend([
            f"## {name}", "",
            f"Parties : {len(policy['games'])} ; paires décodées : {agg['pairs']} ; "
            f"comparaisons A* OK/OK : {ok['count']} "
            f"(distances connues : {ok['with_known_distances']}) ; "
            f"complet : {policy['complete']} ; provenance vérifiée : {policy['campaign_verified']}.", "",
            "| Prêtes libre lors A* | Prêtes guidé lors A* | Guidé seul | Libre seul | Deux prêts | Aucun prêt |",
            "|---:|---:|---:|---:|---:|---:|",
            f"| {agg['free_ready_at_search']} | {agg['guided_ready_at_search']} | "
            f"{agg['classification'].get('guided_only_ready', 0)} | "
            f"{agg['classification'].get('free_only_ready', 0)} | "
            f"{agg['classification'].get('both_ready', 0)} | "
            f"{agg['classification'].get('neither_ready', 0)} |", "",
            "| Mesure (A* OK/OK uniquement, hors cartographie) | Total / somme | Médiane |",
            "|---|---:|---:|",
        ])
        for key, label in [
                ("free_iters", "Itérations libres"),
                ("guided_iters", "Itérations guidées"),
                ("saved_iters", "Iterations libre − guidé"),
                ("free_ops", "Ops libres"),
                ("guided_ops", "Ops guidés"),
                ("saved_ops", "Ops libre − guidé"),
                ("free_ticks_crossed", "Ticks traversés libres"),
                ("guided_ticks_crossed", "Ticks traversés guidés"),
                ("saved_ticks", "Ticks traversés libre − guidé"),
                ("free_path_dist", "Distance chemin libre (connue)"),
                ("guided_path_dist", "Distance chemin guidé (connue)"),
                ("path_distance_delta", "Distance guidé − libre (deux OK)")]:
            metric_key = ("free_ticks" if key == "free_ticks_crossed" else
                          "guided_ticks" if key == "guided_ticks_crossed" else key)
            row = ok[metric_key]
            lines.append(f"| {label} | {row['sum'] if row['n'] else '—'} | "
                         f"{row['median'] if row['n'] else '—'} |")
        lines += ["", f"Qualité (deux A* OK, distances connues) : {ok['quality_classification']}.",
                  f"Disponibilités observées à l'instant des recherches : "
                  f"libre={agg['free_ready_at_search']} guidée={agg['guided_ready_at_search']}.",
                  f"Disponibilité du cache fin {report['expected_end_year']} : "
                  "voir snapshots par graine ci-dessous (inconnue si pas de résumé "
                  f"au 31/12/{report['expected_end_year']}, TTL=180 jours).",
                  f"Origines des paires comparées : {agg['source_counts']}.",
                  f"Coûts cartographiques observés y compris paires encore incomplètes : "
                  f"{policy['mapped_partial']['mapped']} ; bande="
                  f"{policy['mapped_partial']['band_ops']['sum'] if policy['mapped_partial']['band_ops']['n'] else 'non mesurée'} "
                  f"ops ; ligne={policy['mapped_partial']['line_ops']['sum']} ops ; "
                  f"modes={policy['mapped_partial']['by_map_mode']}.", ""]
        lines += [
            "### V309 — tours entiers (SUMMARY cumulatif, événements TURN partiels)", "",
            f"Tours observés par événements TURN : {v309['observed_full_turns']} ; "
            f"opcodes observés : {v309['observed_full_turn_ops']['sum']} ; "
            f"tours déclarés : {v309['reported_full_turns']} ; "
            f"opcodes déclarés : {v309['reported_full_turn_ops']} ; "
            f"tours en pause déclarés : {v309['reported_paused_turns']}. "
            "Les événements TURN peuvent manquer quand le reliquat est inférieur à 2500.", "",
            "| Graine/rép. | Tours entiers observés | Ops TURN | Ops restants TURN | "
            "Tours déclarés | Ops déclarés | Tours en pause | A* OK/OK | "
            "Ticks SEARCH | Ticks CARTO-2 SUMMARY | Cache prêt au 31/12 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for game in policy["games"]:
            turn = game["v309_turns"]
            game_ok = summarize_ok_pairs(game["rows"])
            ticks = game["search_partial"]["ticks"]["sum"]
            ready = game["ready_at_end_snapshot"]
            lines.append(
                f"| seed{game['seed']}/r{game['repeat']} | {turn['observed_full_turns']} | "
                f"{turn['observed_full_turn_ops']['sum']} | {turn['observed_left']['sum']} | "
                f"{turn['reported_full_turns'] if turn['reported_full_turns'] is not None else '—'} | "
                f"{turn['reported_full_turn_ops'] if turn['reported_full_turn_ops'] is not None else '—'} | "
                f"{turn['reported_paused_turns'] if turn['reported_paused_turns'] is not None else '—'} | "
                f"{game_ok['count']} | {ticks} | "
                f"{turn['reported_runtime_ticks'] if turn['reported_runtime_ticks'] is not None else '—'} | "
                f"{ready if ready is not None else 'inconnu'} |")
        lines.append("")
        lines += ["Tours V309 individuels :", "",
                  "| Graine/rép. | Date | Mode | Ops consommés | Ops restants |",
                  "|---|---|---|---:|---:|"]
        for game in policy["games"]:
            for turn in game["turn_records"]:
                lines.append(
                    f"| seed{game['seed']}/r{game['repeat']} | {turn['date']} | "
                    f"{turn['phase']} | {turn['ops']} | {turn['left']} |")
        if not v309["observed_full_turns"]:
            lines.append("| — | — | aucun TURN | — | — |")
        lines.append("")
        observed = policy["search_partial"]
        lines += [
            "### SEARCH observés (partiels inclus, non additionnels aux paires complètes)", "",
            f"Total : {observed['count']} SEARCH ; "
            f"{observed['iters']['sum']} itérations ; "
            f"{observed['ops']['sum']} opcodes ; "
            f"{observed['ticks']['sum']} ticks ; "
            f"outcomes={observed['outcomes']}.", "",
            "| Graine/rép. | Mode | SEARCH | Itérations | OpCodes | Ticks | Outcomes |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
        for game in policy["games"]:
            for mode in ("free", "guided"):
                part = game["search_partial"]["modes"][mode]
                lines.append(
                    f"| seed{game['seed']}/r{game['repeat']} | {mode} | "
                    f"{part['count']} | {part['iters']['sum']} | {part['ops']['sum']} "
                    f"| {part['ticks']['sum']} | {part['outcomes']} |")
        for mode in ("free", "guided"):
            part = observed["modes"][mode]
            lines.append(
                f"| **Toutes graines** | **{mode}** | **{part['count']}** | "
                f"**{part['iters']['sum']}** | **{part['ops']['sum']}** | "
                f"**{part['ticks']['sum']}** | {part['outcomes']} |")
        lines += ["", "SEARCH individuels :", "",
                  "| Graine/rép. | Paire | Source | Mode | Date | Issue | Itérations | OpCodes | Ticks |",
                  "|---|---:|---|---|---|---|---:|---:|---:|"]
        for game in policy["games"]:
            for event in game["search_partial_records"]:
                lines.append(
                    f"| seed{game['seed']}/r{game['repeat']} | {event['id']} | "
                    f"{event['source']} | {event['mode']} | {event['date']} | "
                    f"{event['outcome']} | {event['iters']} | {event['ops']} "
                    f"| {event['ticks']} |")
        if observed["count"] == 0:
            lines.append("| — | — | — | — | — | aucun SEARCH | — | — | — |")
        lines.append("")
        lines += ["Comparaisons par paire A* **OK/OK uniquement** (même id/key ; "
                  "stabilité des extrémités et de la carte non prouvée par les seuls logs) :", "",
                  "| Graine/rép. | Paire | Itérations L/G | Ops L/G | Ticks L/G | "
                  "Distances L/G | Delta ops L−G | Delta distance G−L |",
                  "|---|---:|---|---|---|---|---:|---:|"]
        for pair in ok["pairs"]:
            quality = pair["quality"]
            lines.append(
                f"| seed{pair['seed']}/r{pair['repeat']} | {pair['id']} | "
                f"{pair['free']['iters']}/{pair['guided']['iters']} | "
                f"{pair['free']['ops']}/{pair['guided']['ops']} | "
                f"{pair['free']['ticks']}/{pair['guided']['ticks']} | "
                f"{pair['free']['path_dist']}/{pair['guided']['path_dist']} | "
                f"{pair['saved_ops']} | "
                f"{quality['guided_minus_free_dist'] if quality else 'inconnu'} |")
        if not ok["pairs"]:
            lines.append("| — | — | — | — | — | — | aucun OK/OK | — |")
        lines.append("")
        for game in policy["games"]:
            lines.append(f"- seed{game['seed']}/r{game['repeat']}: "
                         f"{game['pairs_valid']}/{game['pairs_seen']} paires ; "
                         f"{game['mapped_count']} cartographiées ; "
                         f"source={game['pair_sources']} ; "
                         f"dernier résumé={game['summary'] and game['summary'].get('phase')} "
                         f"({game['last_summary_date']}) ; "
                         f"ready fin {report['expected_end_year']} selon résumé="
                         f"{game['ready_at_end_snapshot']} ; "
                         f"SEARCH observés={game['search_partial']['count']} "
                         f"({game['search_partial']['outcomes']}) ; "
                         f"journal complet : {game['log_complete']}.")
            if show_pairs and game["rows"]:
                lines += ["", "| Paire | Libre prêt | Guidé prêt | OK/OK comparable | Δ itér. L−G | "
                          "Δ ops L−G | Δ ticks L−G | Bande−ligne ops | "
                          "Distance G−L | Classe |",
                          "|---:|---:|---:|---|---:|---:|---:|---:|---:|---|"]
                for row in game["rows"]:
                    quality = row["quality"]
                    comparable = row["both_astar_ok"]
                    lines.append(
                        f"| {row['id']} | {row['free']['ready_at_search']} | "
                        f"{row['guided']['ready_at_search']} | {comparable} | "
                        f"{row['saved_iters'] if comparable else '—'} | "
                        f"{row['saved_ops'] if comparable else '—'} | "
                        f"{row['saved_ticks'] if comparable else '—'} | "
                        f"{row['cost']['extra_ops'] if row['cost']['extra_ops'] is not None else 'non mesuré'} | "
                        f"{quality['guided_minus_free_dist'] if comparable and quality else '—'} | "
                        f"{row['class']} |")
                lines.append("")
        if policy["errors"] or policy.get("campaign_errors"):
            lines += ["", "Écarts détectés :"]
            lines += [f"- {e}" for e in policy["errors"] + policy.get("campaign_errors", [])]
        lines.append("")
    lines += ["Mesures shadow ; la neutralité économique et la construction réelle "
              "restent non démontrées.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path,
                        help="Journaux *.log[.gz] ou dossiers de logs")
    parser.add_argument("--result-json", type=Path, help="Résultat JSON du harnais")
    parser.add_argument("--manifest", type=Path, help="Manifeste JSON du harnais")
    parser.add_argument("--expected-year", type=int, default=EXPECTED_YEAR)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--show-pairs", action="store_true",
                        help="Ajouter les comparaisons individuelles au tableau Markdown")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--require-complete", action="store_true",
                        help="Code 1 si logs/provenance/horizon incomplets")
    args = parser.parse_args(argv)
    try:
        report = analyze_paths(args.inputs, result_json=args.result_json,
                               manifest=args.manifest, expected_year=args.expected_year)
    except (ValueError, FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    output = (json.dumps(report, indent=2, ensure_ascii=False) + "\n"
              if args.format == "json" else render_markdown(report, show_pairs=args.show_pairs))
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 1 if args.require_complete and not all(
        policy["complete"] for policy in report["policies"].values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
