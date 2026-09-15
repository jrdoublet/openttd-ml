"""C66.3: freeze benchmark inputs and describe them in an immutable manifest.

The benchmark process may keep running while the working tree changes.  A Git SHA
therefore does not identify the program that all games actually executed.  This
module snapshots the local AIs, resolves BaNaNaS AI libraries once, fingerprints
the resulting bundle and returns OpenTTDLab descriptors backed by that bundle.
"""

from __future__ import annotations

import configparser
import contextlib
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import functools
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


MANIFEST_SCHEMA_VERSION = "1.1.0"
CAMPAIGN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SETTING_BLOCK_RE = re.compile(r"AddSetting\s*\(\s*\{(.*?)\}\s*\)\s*;", re.DOTALL)
SETTING_NAME_RE = re.compile(r'\bname\s*=\s*"([^"]+)"')
SETTING_DEFAULT_RE = re.compile(r"\bcustom_value\s*=\s*([^,\n}]+)")


@dataclass(frozen=True)
class FrozenCampaign:
    campaign_id: str
    out_path: Path
    checkpoint_path: Path
    engine_log_dir: Path
    manifest_path: Path
    manifest_sha256: str
    bundle_dir: Path
    bundle_sha256: str
    opex_dir: Path
    aaahogex_dir: Path
    ai_libraries: tuple
    manifest: dict


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_tree(root: Path) -> dict:
    """Return a deterministic path+content fingerprint for one directory."""
    root = Path(root)
    files = []
    digest = hashlib.sha256()
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
        rel = path.relative_to(root).as_posix()
        file_hash = sha256_file(path)
        size = path.stat().st_size
        files.append({"path": rel, "size": size, "sha256": file_hash})
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(file_hash))
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "file_count": len(files), "files": files}


def _copy_tree(source: Path, destination: Path) -> dict:
    source = Path(source)
    if not source.is_dir():
        raise FileNotFoundError(f"source snapshot introuvable: {source}")
    shutil.copytree(source, destination)
    return fingerprint_tree(destination)


def _copy_files(root: Path, relative_paths, destination: Path) -> dict:
    for rel in relative_paths:
        source = Path(root) / rel
        if not source.is_file():
            raise FileNotFoundError(f"fichier de harnais introuvable: {source}")
        target = Path(destination) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return fingerprint_tree(destination)


def git_state(root: Path) -> dict:
    env_sha = os.environ.get("C66_GIT_SHA")
    if env_sha:
        dirty_raw = os.environ.get("C66_GIT_DIRTY", "")
        if dirty_raw not in ("0", "1"):
            raise ValueError("C66_GIT_DIRTY doit valoir 0 ou 1")
        status_b64 = os.environ.get("C66_GIT_STATUS_B64", "")
        try:
            status_text = base64.b64decode(status_b64).decode("utf-8") if status_b64 else ""
        except Exception as error:
            raise ValueError("C66_GIT_STATUS_B64 invalide") from error
        return {
            "sha": env_sha,
            "dirty": dirty_raw == "1",
            "status_porcelain": status_text.splitlines() if status_text else [],
            "source": "host_environment",
        }

    def run(*args):
        proc = subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True,
        )
        return proc.stdout.strip()

    try:
        sha = run("rev-parse", "HEAD")
        status = run("status", "--porcelain=v1", "--untracked-files=all")
    except FileNotFoundError as error:
        raise RuntimeError(
            "git absent du runtime et metadonnees C66_GIT_* non injectees ; "
            "lancer la campagne via sweeps/run_c66_reference.py"
        ) from error
    return {
        "sha": sha,
        "dirty": bool(status),
        "status_porcelain": status.splitlines() if status else [],
        "source": "git_cli",
    }


def parse_ai_settings(info_path: Path) -> dict:
    """Extract custom_value defaults from AIInfo.GetSettings() declarations."""
    text = Path(info_path).read_text(encoding="utf-8")
    defaults = {}
    for block in SETTING_BLOCK_RE.findall(text):
        name_match = SETTING_NAME_RE.search(block)
        value_match = SETTING_DEFAULT_RE.search(block)
        if not name_match or not value_match:
            continue
        name = name_match.group(1)
        raw = value_match.group(1).strip()
        value = int(raw) if re.fullmatch(r"-?\d+", raw) else raw
        if name in defaults and defaults[name] != value:
            raise ValueError(f"reglage {name!r} declare plusieurs fois avec des defauts differents")
        defaults[name] = value
    return dict(sorted(defaults.items()))


def effective_ai_settings(info_path: Path, explicit=()) -> dict:
    defaults = parse_ai_settings(info_path)
    explicit_dict = dict(explicit or ())
    unknown = sorted(set(explicit_dict) - set(defaults))
    if unknown:
        raise ValueError(f"reglages explicites absents de info.nut: {unknown}")
    effective = dict(defaults)
    effective.update(explicit_dict)
    return {
        "defaults": defaults,
        "explicit": dict(sorted(explicit_dict.items())),
        "effective": dict(sorted(effective.items())),
    }


def validate_policy_settings(reference: dict, candidate: dict, intervention_settings=()) -> dict:
    """Fail closed if two effective policies differ outside the announced settings."""
    allowed = set(intervention_settings or ())
    keys = set(reference) | set(candidate)
    differences = {
        key: {"reference": reference.get(key), "candidate": candidate.get(key)}
        for key in sorted(keys)
        if reference.get(key) != candidate.get(key)
    }
    unexpected = sorted(set(differences) - allowed)
    if unexpected:
        raise ValueError(f"comparaison invalide: differences non annoncees {unexpected}")
    return differences


def _parse_config(config_text: str) -> dict:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(config_text)
    return {
        section: dict(sorted(parser.items(section)))
        for section in parser.sections()
    }


@contextlib.contextmanager
def _file_contents(path: Path):
    with Path(path).open("rb") as handle:
        yield iter(lambda: handle.read(65536), b"")


def _frozen_library_descriptor(name: str, entries: list[dict], library_dir: Path):
    """Build the (name, copy_func) pair expected by OpenTTDLab."""
    @contextlib.contextmanager
    def copy_func(get_http_client=None, get_cache_dir=None):
        del get_http_client, get_cache_dir
        yield tuple(
            (
                entry["content_id"],
                entry["filename"],
                entry.get("license"),
                entry.get("public_md5"),
                functools.partial(_file_contents, library_dir / entry["filename"]),
            )
            for entry in entries
        )

    return name, copy_func


def freeze_bananas_libraries(specs, destination: Path):
    """Resolve BaNaNaS once, copy exact tars, and return local descriptors + metadata."""
    from openttdlab import bananas_ai_library

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    frozen_descriptors = []
    manifest_groups = []
    known_files = {}

    for spec in specs:
        unique_id = spec["unique_id"]
        name = spec["name"]
        requested = bananas_ai_library(unique_id, name, md5=spec.get("md5"))
        copy_func = requested[1]
        entries = []
        with copy_func() as resolved:
            for content_id, filename, license_name, public_md5, get_data in resolved:
                target = destination / filename
                temp = destination / (filename + ".partial")
                digest = hashlib.sha256()
                size = 0
                with get_data() as chunks, temp.open("wb") as handle:
                    for chunk in chunks:
                        handle.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                sha256 = digest.hexdigest()
                if target.exists():
                    if sha256_file(target) != sha256:
                        temp.unlink(missing_ok=True)
                        raise RuntimeError(f"collision de bibliotheque avec contenu different: {filename}")
                    temp.unlink()
                else:
                    temp.replace(target)

                previous = known_files.get(filename)
                if previous is not None and previous != sha256:
                    raise RuntimeError(f"empreinte instable pour {filename}")
                known_files[filename] = sha256
                version = Path(filename).stem.rsplit("-", 1)[-1]
                entries.append({
                    "content_id": content_id,
                    "filename": filename,
                    "version": version,
                    "license": license_name,
                    "public_md5": public_md5,
                    "sha256": sha256,
                    "size": size,
                })
        manifest_groups.append({
            "requested_name": name,
            "requested_unique_id": unique_id,
            "requested_md5": spec.get("md5"),
            "resolved": entries,
        })
        frozen_descriptors.append(_frozen_library_descriptor(name, entries, destination))

    return tuple(frozen_descriptors), manifest_groups


def _runtime_metadata(root: Path, docker_image: str | None, docker_image_id: str | None) -> dict:
    runtime_files = ["Dockerfile", "requirements.txt", "requirements-ml.txt"]
    context = {}
    for rel in runtime_files:
        path = Path(root) / rel
        if path.is_file():
            context[rel] = sha256_file(path)
    try:
        openttdlab_version = importlib.metadata.version("OpenTTDLab")
    except importlib.metadata.PackageNotFoundError:
        openttdlab_version = None
    payload = {
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "openttdlab": openttdlab_version,
        "container_detected": Path("/.dockerenv").exists(),
        "docker_image": docker_image,
        "docker_image_id": docker_image_id,
        "docker_image_id_verified": bool(docker_image_id),
        "docker_cpus": int(os.environ["C66_DOCKER_CPUS"]) if os.environ.get("C66_DOCKER_CPUS") else None,
        "docker_memory": os.environ.get("C66_DOCKER_MEMORY"),
        "docker_memory_swap": os.environ.get("C66_DOCKER_MEMORY_SWAP"),
        "build_context_files": context,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["runtime_fingerprint_sha256"] = _sha256_bytes(canonical)
    return payload


def _write_json_atomically(path: Path, payload: dict):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    temp.replace(path)


def default_campaign_id(prefix="c66-reference") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


def prepare_frozen_campaign(
    *,
    root: Path,
    out_path: Path,
    campaign_id: str,
    policy_id: str,
    seeds,
    years: int,
    repeats: int,
    starting_year: int,
    config_text: str,
    opex_explicit_settings=(),
    library_specs=(),
    harness_files=(),
    openttd_version: str,
    opengfx_version: str,
    docker_image: str | None = None,
    docker_image_id: str | None = None,
    policy_definitions=None,
    intervention_settings=(),
    decision_rule=None,
) -> FrozenCampaign:
    """Create every immutable campaign input before the first OpenTTD process starts."""
    root = Path(root).resolve()
    out_path = Path(out_path)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()
    if not CAMPAIGN_ID_RE.fullmatch(campaign_id):
        raise ValueError(f"campaign_id invalide: {campaign_id!r}")
    if repeats < 1:
        raise ValueError("repeats doit etre >= 1")

    manifest_path = out_path.with_suffix(".manifest.json")
    checkpoint_path = out_path.with_suffix(".jsonl")
    bundle_dir = out_path.with_name(out_path.stem + "_bundle")
    engine_log_dir = out_path.with_name(out_path.stem + "_engine")
    protected = (out_path, manifest_path, checkpoint_path, bundle_dir, engine_log_dir)
    existing = [str(path) for path in protected if path.exists()]
    if existing:
        raise FileExistsError("C66.3 refuse d'ecraser une campagne existante: " + ", ".join(existing))

    # Capture Git state before creating any campaign artifact inside the repository.
    git = git_state(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=False, exist_ok=False)

    ai_root = bundle_dir / "ai"
    ai_root.mkdir()
    opex_dir = ai_root / "OpexAI"
    aaahogex_dir = ai_root / "AAAHogEx-115"
    opex_fingerprint = _copy_tree(root / "ai" / "OpexAI", opex_dir)
    aaahogex_fingerprint = _copy_tree(root / "ai" / "AAAHogEx-115", aaahogex_dir)

    harness_root = bundle_dir / "harness"
    harness_root.mkdir()
    harness_fingerprint = _copy_files(root, harness_files, harness_root)

    libraries_dir = bundle_dir / "ai_libraries"
    ai_libraries, library_manifest = freeze_bananas_libraries(library_specs, libraries_dir)
    libraries_fingerprint = fingerprint_tree(libraries_dir)

    bundle_fingerprint = fingerprint_tree(bundle_dir)
    if policy_definitions is None:
        policy_definitions = ({
            "id": policy_id,
            "role": "reference",
            "explicit_settings": tuple(opex_explicit_settings),
        },)
    else:
        policy_definitions = tuple(policy_definitions)
        if not policy_definitions:
            raise ValueError("policy_definitions ne peut pas etre vide")

    policies = []
    seen_policy_ids = set()
    for definition in policy_definitions:
        current_id = str(definition["id"])
        if not CAMPAIGN_ID_RE.fullmatch(current_id):
            raise ValueError(f"policy_id invalide: {current_id!r}")
        if current_id in seen_policy_ids:
            raise ValueError(f"policy_id duplique: {current_id}")
        seen_policy_ids.add(current_id)
        explicit = tuple(tuple(item) for item in definition.get("explicit_settings", ()))
        policies.append({
            "id": current_id,
            "role": definition.get("role", "policy"),
            "ai": "OpexAI",
            "company_slot": 0,
            "settings": effective_ai_settings(opex_dir / "info.nut", explicit),
        })

    reference_policies = [item for item in policies if item["role"] == "reference"]
    if len(reference_policies) != 1:
        raise ValueError("exactement une politique de role 'reference' est requise")
    reference_policy = reference_policies[0]
    comparison = None
    if len(policies) > 1:
        variant_policies = [item for item in policies if item["role"] == "variant"]
        if len(policies) != 2 or len(variant_policies) != 1:
            raise ValueError("C66.4 exige exactement une reference et une variante")
        variant_policy = variant_policies[0]
        declared = tuple(intervention_settings)
        if not declared:
            raise ValueError("C66.4 exige au moins un reglage d'intervention annonce")
        differences = validate_policy_settings(
            reference_policy["settings"]["effective"],
            variant_policy["settings"]["effective"],
            intervention_settings=declared,
        )
        if set(differences) != set(declared):
            missing = sorted(set(declared) - set(differences))
            raise ValueError(f"intervention C66.4 sans effet effectif sur: {missing}")
        comparison = {
            "reference_policy_id": reference_policy["id"],
            "variant_policy_id": variant_policy["id"],
            "intervention_settings": list(declared),
            "effective_differences": differences,
            "decision_rule": decision_rule,
        }

    opex_settings = reference_policy["settings"]
    aaahogex_settings = effective_ai_settings(aaahogex_dir / "info.nut", ())
    runtime = _runtime_metadata(root, docker_image, docker_image_id)

    games = []
    for repeat in range(repeats):
        for seed in seeds:
            for current_policy in policies:
                games.append({
                    "game_id": f"{campaign_id}:policy={current_policy['id']}:s{seed}:r{repeat}",
                    "policy_id": current_policy["id"],
                    "seed": int(seed),
                    "repeat": repeat,
                    "company_slots": {
                        "0": {"ai": "OpexAI", "policy_id": current_policy["id"]},
                        "1": {"ai": "AAAHogEx", "policy_id": "AAAHogEx"},
                    },
                })

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git": git,
        "versions": {
            "openttd": openttd_version,
            "opengfx": opengfx_version,
            "openttdlab": runtime["openttdlab"],
        },
        "runtime": runtime,
        "configuration": {
            "raw": config_text,
            "sha256": _sha256_bytes(config_text.encode("utf-8")),
            "parsed": _parse_config(config_text),
            "starting_year": starting_year,
            "years": years,
            "seeds": [int(seed) for seed in seeds],
            "repeats": repeats,
        },
        "policy": {
            "id": reference_policy["id"],
            "ai": "OpexAI",
            "company_slot": 0,
            "settings": opex_settings,
        },
        "policies": policies,
        "comparison": comparison,
        "adversary": {
            "id": "AAAHogEx",
            "ai": "AAAHogEx",
            "company_slot": 1,
            "settings": aaahogex_settings,
        },
        "company_slots": {
            "0": {
                "ai": "OpexAI",
                "policy_id": reference_policy["id"] if len(policies) == 1 else "per-game",
            },
            "1": {"ai": "AAAHogEx", "policy_id": "AAAHogEx"},
        },
        "games": games,
        "sources": {
            "OpexAI": opex_fingerprint,
            "AAAHogEx": aaahogex_fingerprint,
            "harness": harness_fingerprint,
            "ai_libraries": libraries_fingerprint,
        },
        "libraries": library_manifest,
        "source_bundle": {
            "path": str(bundle_dir),
            "sha256": bundle_fingerprint["sha256"],
            "file_count": bundle_fingerprint["file_count"],
        },
        "artifacts": {
            "result": str(out_path),
            "checkpoints": str(checkpoint_path),
            "engine_logs": str(engine_log_dir),
            "manifest": str(manifest_path),
            "bundle": str(bundle_dir),
        },
    }
    _write_json_atomically(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)
    engine_log_dir.mkdir(parents=False, exist_ok=False)

    return FrozenCampaign(
        campaign_id=campaign_id,
        out_path=out_path,
        checkpoint_path=checkpoint_path,
        engine_log_dir=engine_log_dir,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        bundle_dir=bundle_dir,
        bundle_sha256=bundle_fingerprint["sha256"],
        opex_dir=opex_dir,
        aaahogex_dir=aaahogex_dir,
        ai_libraries=ai_libraries,
        manifest=manifest,
    )
