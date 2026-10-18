"""RVA-05: explicit local resources, no downloads or replacement GRFs.

OpenTTD 15.3 settings.cpp:1059-1148 reads ordered filenames and parameters.
Use filename-only entries: GRFID lookup may otherwise replace missing files.
OpenTTDLab 0.0.75 CONTENT_TYPES and _run_experiment supply the copy protocol.
"""
import configparser
import contextlib
import functools
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil


def load_profile(path, root):
    """Require every input below the mounted checkout; preserve resource order."""
    root = Path(root).resolve()
    path = Path(path).resolve()
    path.relative_to(root)
    raw = path.read_bytes()
    profile = json.loads(raw)
    if set(profile) != {"schema", "settings", "newgrfs"} or profile["schema"] != 1:
        raise ValueError("RVA profile requires schema=1, settings, newgrfs")
    settings = profile["settings"]
    allowed = {"vehicle", "economy", "station", "construction", "linkgraph"}
    if not isinstance(settings, dict) or set(settings) - allowed:
        raise ValueError("RVA settings section unsupported (runtime/map/AI kept by harness)")
    for section, entries in settings.items():
        if not isinstance(entries, dict):
            raise ValueError("RVA settings must be section/key mappings")
        for key, value in entries.items():
            if (not re.fullmatch(r"[a-z][a-z0-9_]*", key)
                    or not isinstance(value, str) or not value or any(c in value for c in "\r\n")):
                raise ValueError("RVA setting must be a single explicit string value")
    if not isinstance(profile["newgrfs"], list):
        raise ValueError("RVA newgrfs must be an ordered array")
    resources, seen = [], set()
    for entry in profile["newgrfs"]:
        if set(entry) != {"file", "sha256", "version", "parameters"}:
            raise ValueError("RVA GRF requires file, sha256, version (nullable), parameters")
        source = (path.parent / entry["file"]).resolve()
        source.relative_to(root)
        if source.suffix.lower() != ".grf" or not source.is_file():
            raise ValueError(f"RVA GRF missing: {source}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if entry["sha256"] != digest or digest in seen:
            raise ValueError(f"RVA GRF hash mismatch or duplicate: {source}")
        seen.add(digest)
        if entry["version"] is not None and not isinstance(entry["version"], str):
            raise ValueError("RVA version must be a declared string or unknown/null")
        params = entry["parameters"]
        # settings.cpp:247-266 reads uint32_t; newgrf_config.h:159 caps at 0x80.
        if (not isinstance(params, list) or len(params) > 0x80
                or any(type(v) is not int or not 0 <= v <= (1 << 32) - 1 for v in params)):
            raise ValueError("RVA parameters must be at most 128 explicit uint32 values")
        resources.append(dict(entry, source=str(source), filename=f"rva_{digest}.grf"))
    return {"profile_sha256": hashlib.sha256(raw).hexdigest(), "settings": settings,
            "resources": resources, "raw": raw.decode("utf-8")}


def freeze_profile(profile, destination, config_text):
    destination = Path(destination)
    destination.mkdir()
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(config_text)
    if parser.has_section("newgrf") or parser.has_section("newgrf-static"):
        raise ValueError("RVA profile must be the only source of GRFs")
    for section, entries in profile["settings"].items():
        if not parser.has_section(section):
            parser.add_section(section)
        for key, value in entries.items():
            parser.set(section, key, value)
    resources = []
    for entry in profile["resources"]:
        target = destination / entry["filename"]
        shutil.copyfile(entry["source"], target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("RVA resource changed during freeze")
        resources.append({k: v for k, v in entry.items() if k not in ("source", "file")})
    import io
    output = io.StringIO()
    parser.write(output)
    # ConfigParser lowercases keys; filenames/hash are deliberately lowercase.
    config = output.getvalue()
    if resources:
        config += "\n[newgrf]\n" + "".join(
            entry["filename"] + " = " + " ".join(map(str, entry["parameters"])) + "\n"
            for entry in resources)
    (destination / "profile.json").write_text(profile["raw"], encoding="utf-8")
    return config, {"profile_sha256": profile["profile_sha256"],
                    "settings": profile["settings"], "resources": resources,
                    "effective_engine_loading": "requires_smoke"}


@contextlib.contextmanager
def _resource_bytes(path):
    yield (Path(path).read_bytes(),)


def resource_descriptor(bundle, entries):
    @contextlib.contextmanager
    def copy_resources(get_http_client=None, get_cache_dir=None):
        del get_http_client, get_cache_dir
        records = []
        for entry in entries:
            path = Path(bundle) / "simulation_profile" / entry["filename"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError("RVA frozen resource fingerprint mismatch")
            records.append(("newgrf/" + entry["sha256"], entry["filename"], None, None,
                            functools.partial(_resource_bytes, path)))
        yield tuple(records)
    return "RVA frozen NewGRFs", copy_resources


def resource_directory_wrapper(original):
    """Compose with health/archive wrappers; create only the standard GRF folder."""
    signature = inspect.signature(original)
    @functools.wraps(original)
    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        (Path(bound.arguments["run_dir"]) / str(bound.arguments["i"]) / "newgrf").mkdir(
            parents=True, exist_ok=True)
        return original(*args, **kwargs)
    wrapped.__signature__ = signature
    return wrapped
