#!/usr/bin/env python3
"""Observation hors moteur des aeroports A censures apres BFAIL.

Archive `savegame_archive.py`: <dir>/<experiment_index>/archive.json et `save/*.sav`.
Le lien index -> partie provient uniquement de l'ordre du plan figé (repetition,
graine, politique), verifie contre manifest.games, jamais du nom d'un .sav.
Un aeroport n'est dit present qu'a la date exacte du checkpoint decode.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MONTHLY_SAVE = re.compile(r"save/(\d{9})\.sav\Z")
LOG_NAME = re.compile(r"(reference|variant)_seed(\d+)_r(\d+)\.log\Z")


class EvidenceError(ValueError):
    """Preuve manquante, alteree ou non appariable : refuser le verdict."""


def require(condition, reason):
    if not condition:
        raise EvidenceError(reason)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise EvidenceError(f"JSON illisible: {path}: {exc}") from exc


def plan_from_manifest(manifest):
    """Meme ordre que campaign_freeze et make_experiments_plan, verifie champ a champ."""
    cfg = manifest.get("configuration") or {}
    seeds, repeats = cfg.get("seeds"), cfg.get("repeats")
    policies = manifest.get("policies") or []
    actual = manifest.get("games")
    campaign = manifest.get("campaign_id")
    require(isinstance(campaign, str) and campaign, "campaign_id absent")
    require(isinstance(seeds, list) and seeds and all(type(s) is int for s in seeds)
            and len(set(seeds)) == len(seeds), "graines de configuration absentes/dupliquees")
    require(type(repeats) is int and repeats > 0, "repetitions invalides")
    ids = [p.get("id") for p in policies if isinstance(p, dict)]
    require(ids and len(ids) == len(policies) and all(isinstance(p, str) and p for p in ids)
            and len(set(ids)) == len(ids), "politiques ambiguës")
    require(isinstance(actual, list), "manifest.games absent")
    expected = [(r, seed, pid) for r in range(repeats) for seed in seeds for pid in ids]
    require(len(actual) == len(expected), "nombre de jeux different du plan")
    for index, ((repeat, seed, pid), game) in enumerate(zip(expected, actual)):
        require(isinstance(game, dict), f"game[{index}] invalide")
        game_id = f"{campaign}:policy={pid}:s{seed}:r{repeat}"
        require(game.get("game_id") == game_id and game.get("seed") == seed
                and game.get("repeat") == repeat and game.get("policy_id") == pid,
                f"index {index}: association archive/seed/bras incompatible avec le plan")
        slots = game.get("company_slots") or {}
        require((slots.get("0") or {}).get("ai") == "OpexAI"
                and (slots.get("0") or {}).get("policy_id") == pid,
                f"game[{index}]: propriétaire OpexAI/politique incorrect")
    return [dict(index=i, **g) for i, g in enumerate(actual)]


def targets_from_orphans(orphans, manifest, plan, expected_count=3):
    """Uniquement evenements BFAIL censures du meme campaign, bras et repetition."""
    plan_keys = {(g["seed"], g["repeat"], g["policy_id"]) for g in plan}
    seen_runs, targets, identities = set(), [], set()
    runs = orphans.get("runs")
    require(isinstance(runs, list), "rapport orphelins sans runs")
    for run in runs:
        require(isinstance(run, dict), "run orphelin invalide")
        key = (run.get("seed"), run.get("repeat"), run.get("arm"))
        require(key in plan_keys and key not in seen_runs, f"run orphelin non appariable: {key}")
        seen_runs.add(key)
        logfile = Path(run.get("file") or "").name
        match = LOG_NAME.fullmatch(logfile)
        require(match is not None and (match.group(1), int(match.group(2)), int(match.group(3)))
                == (key[2], key[0], key[1]), f"nom log incompatible: {logfile}")
        require(manifest["campaign_id"] + "_engine" in str(run.get("file")),
                f"journal hors campagne: {logfile}")
        for orphan in run.get("orphans") or []:
            if orphan.get("status") != "censored":
                continue
            require(orphan.get("reason") == "BFAIL" and key[2] == "reference",
                    f"origine censuree hors BFAIL/reference: {key}")
            sid, anchor, origin_day = (orphan.get(k) for k in ("station", "anchor", "date"))
            require(all(type(x) is int and x >= 0 for x in (sid, anchor, origin_day)),
                    f"identite physique incomplete: {key}")
            identity = (key, sid, anchor)
            require(identity not in identities, f"origine repetee: {identity}")
            identities.add(identity)
            targets.append({"seed": key[0], "repeat": key[1], "policy_id": key[2],
                            "station": sid, "anchor": anchor, "origin_day": origin_day,
                            "cost_a_gbp": orphan.get("cost_a_gbp"),
                            "origin_status": "censored"})
    require(len(targets) == expected_count,
            f"attendu {expected_count} orphelins censures, obtenu {len(targets)}")
    return targets


def checked_archive(root, index):
    """Integrite de chaque fichier ET egalite inventaire physique / archive.json."""
    folder = Path(root) / str(index)
    require(folder.is_dir(), f"archive absente: {folder}")
    catalog = folder / "archive.json"
    require(catalog.is_file(), f"archive.json absent: {catalog}")
    raw_catalog = catalog.read_bytes()
    archive = read_json(catalog)
    require(archive.get("experiment_index") == index and type(archive.get("experiment_index")) is int,
            f"index non concordant dans {catalog}")
    records = archive.get("savegames")
    require(isinstance(records, list) and records, f"archive vide: {catalog}")
    listed = set()
    for record in records:
        require(isinstance(record, dict), f"entree invalide {catalog}")
        raw = record.get("path")
        require(isinstance(raw, str), "chemin archive absent")
        name = PurePosixPath(raw)
        require(not name.is_absolute() and name.parts and all(p not in ("..", ".") for p in name.parts)
                and name.suffix == ".sav" and "\\" not in raw and raw == name.as_posix(),
                f"chemin hors archive: {raw}")
        require(raw not in listed, f"entree .sav dupliquee: {raw}")
        listed.add(raw)
        require(type(record.get("bytes")) is int and record["bytes"] > 0
                and isinstance(record.get("sha256"), str)
                and SHA256.fullmatch(record["sha256"]), f"hash/taille absents: {raw}")
        path = folder.joinpath(*name.parts)
        require(path.is_file() and not path.is_symlink(), f"fichier archive absent/lien: {path}")
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        require(size == record["bytes"] and digest.hexdigest() == record["sha256"],
                f"hash/taille invalide: {path}")
    present = {p.relative_to(folder).as_posix() for p in folder.rglob("*.sav")}
    require(listed == present, f"inventaire incomplet ou fichiers .sav non listes: {folder}")
    numbered = []
    for raw in listed:
        m = MONTHLY_SAVE.fullmatch(raw)
        if m:
            numbered.append((int(m.group(1)), raw))
        else:
            require(raw == "save/0.sav", f"nom de sauvegarde inconnu: {raw}")
    require(numbered, f"aucune sauvegarde mensuelle: {folder}")
    indexes = sorted(num for num, _ in numbered)
    require(indexes == list(range(indexes[-1] + 1)),
            f"sauvegardes mensuelles manquantes/dupliquees: {folder}")
    latest_name = max(numbered)[1]
    record = next(r for r in records if r["path"] == latest_name)
    return {"path": folder / latest_name, "record": record,
            "archive_json": str(catalog),
            "archive_json_sha256": hashlib.sha256(raw_catalog).hexdigest(),
            "verified_savegames": len(listed), "latest_save_index": indexes[-1]}


def _single(raw):
    """OpenTTDLab STNN: normal et base peuvent etre des listes singleton."""
    return raw[0] if isinstance(raw, list) and len(raw) == 1 else raw


def _station(stnn, station_id):
    require(isinstance(stnn, (dict, list)), "chunk STNN manquant/invalide")
    if isinstance(stnn, list):
        return stnn[station_id] if station_id < len(stnn) else None
    matches = [value for key, value in stnn.items()
               if str(key) == str(station_id)]
    require(len(matches) <= 1, f"StationID {station_id} duplique dans STNN")
    return matches[0] if matches else None


def inspect_station(chunks, station_id, anchor):
    record = _station(chunks.get("STNN"), station_id)
    if record is None:
        return {"status": "station_missing", "owner": None, "facilities": None,
                "airport_tile": None}
    require(isinstance(record, dict), f"station {station_id}: format inconnu")
    normal = _single(record.get("normal"))
    require(isinstance(normal, dict), f"station {station_id}: normal absent (waypoint?)")
    base = _single(normal.get("base"))
    require(isinstance(base, dict), f"station {station_id}: normal.base absent")
    owner, facilities = base.get("owner"), base.get("facilities")
    require(type(owner) is int and type(facilities) is int,
            f"station {station_id}: owner/facilities non decodables")
    tile = normal.get("airport.tile")
    require(tile is None or type(tile) is int,
            f"station {station_id}: airport.tile malforme")
    status = ("different_owner" if owner != 0 else
              "not_an_airport" if not (facilities & 8) else
              "unknown_airport_tile" if tile is None else
              "different_anchor" if tile != anchor else "present_same_airport")
    return {"status": status, "owner": owner, "facilities": facilities,
            "airport_tile": tile}


def decode_latest(path, parse_savegame=None):
    if parse_savegame is None:
        import openttdlab  # uniquement en execution reelle, pas necessaire aux fixtures
        parse_savegame = openttdlab.parse_savegame
    with Path(path).open("rb") as stream:
        game = parse_savegame(iter(lambda: stream.read(65536), b""))
    require(isinstance(game, dict) and isinstance(game.get("chunks"), dict),
            f"savegame decode invalide: {path}")
    chunks = {}
    for key, raw in game["chunks"].items():
        require(isinstance(raw, dict) and "records" in raw, f"chunk {key} sans records")
        chunks[key] = raw["records"]
    dates = chunks.get("DATE")
    require(isinstance(dates, dict), "chunk DATE absent")
    stamp = dates.get("0", dates.get(0))
    require(isinstance(stamp, dict) and type(stamp.get("date")) is int,
            "DATE[0].date absent ou invalide")
    day = stamp["date"]
    try:
        calendar_date = date(1, 1, 1) + timedelta(days=day - 366)
    except (OverflowError, ValueError) as exc:
        raise EvidenceError(f"date jeu invalide: {day}") from exc
    return chunks, day, calendar_date.isoformat()


def analyse(manifest_path, archive_root, orphans_path, *, expected_count=3, parse_savegame=None):
    manifest_path, archive_root, orphans_path = map(Path, (manifest_path, archive_root, orphans_path))
    manifest, orphans = read_json(manifest_path), read_json(orphans_path)
    plan = plan_from_manifest(manifest)
    targets = targets_from_orphans(orphans, manifest, plan, expected_count)
    expected_directories = {str(i) for i in range(len(plan))}
    existing = {p.name for p in archive_root.iterdir() if p.is_dir()} if archive_root.is_dir() else set()
    require(existing == expected_directories, "sous-dossiers archive indexes manquants/inattendus")
    target_groups = {}
    for target in targets:
        key = (target["seed"], target["repeat"], target["policy_id"])
        target_groups.setdefault(key, []).append(target)
    parsed = []
    expected_last = date(int(manifest["configuration"]["starting_year"])
                         + int(manifest["configuration"]["years"]), 1, 1)
    first_date = date(int(manifest["configuration"]["starting_year"]), 1, 1)
    for game in plan:
        archived = checked_archive(archive_root, game["index"])
        key = (game["seed"], game["repeat"], game["policy_id"])
        # Il faut verifier l'inventaire de TOUS les indexes, meme sans orphelin.
        if key not in target_groups:
            continue
        chunks, day, stamp = decode_latest(archived["path"], parse_savegame)
        require(first_date <= date.fromisoformat(stamp) < expected_last,
                f"checkpoint hors horizon: {archived['path']} date={stamp}")
        for target in target_groups[key]:
            require(day >= target["origin_day"],
                    f"checkpoint anterieur a BFAIL: {archived['path']}")
            station = inspect_station(chunks, target["station"], target["anchor"])
            parsed.append({**target, "game_id": game["game_id"],
                           "archive_index": game["index"],
                           "archive_json": archived["archive_json"],
                           "archive_json_sha256": archived["archive_json_sha256"],
                           "archive_saves_verified": archived["verified_savegames"],
                           "savegame": str(archived["path"]),
                           "savegame_sha256": archived["record"]["sha256"],
                           "latest_save_index": archived["latest_save_index"],
                           "snapshot_day": day, "snapshot_date": stamp,
                           "observation_scope": "at_snapshot_only", **station})
    require(len(parsed) == len(targets), "cibles non toutes examinees")
    return {"campaign_id": manifest["campaign_id"],
            "manifest": str(manifest_path),
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "archives": str(archive_root),
            "expected_horizon_exclusive": expected_last.isoformat(),
            "mapping": [{"archive_index": g["index"], "seed": g["seed"],
                         "repeat": g["repeat"], "policy_id": g["policy_id"],
                         "game_id": g["game_id"]} for g in plan],
            "cases": sorted(parsed, key=lambda p: p["seed"]),
            "counts": {status: sum(p["status"] == status for p in parsed)
                       for status in sorted(set(p["status"] for p in parsed))},
            "limitations": ["Observation physique uniquement au checkpoint exact indique",
                            "STNN ne donne pas une valeur liquidable de l'aeroport",
                            "Aucun contrefactuel de liquidation ni profit impute"],
            }


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--archives", type=Path, required=True)
    cli.add_argument("--orphans", type=Path, required=True,
                     help="Rapport analyse_air_orphan_reuse du MEME run")
    cli.add_argument("--json", type=Path, help="Sortie fichier JSON (sinon stdout)")
    args = cli.parse_args(argv)
    try:
        report = analyse(args.manifest, args.archives, args.orphans)
        if args.json is not None:
            require(not args.json.exists(), f"sortie deja existante: {args.json}")
    except (EvidenceError, OSError, ImportError, KeyError, TypeError) as exc:
        print(f"NON_VERIFIABLE: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.json is not None:
        args.json.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
