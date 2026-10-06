"""R26: launch a fresh interpreter using only the fingerprinted local harness.

The bootstrap intentionally imports only the standard library until verification.
Installed third-party packages remain available; the live checkout and PYTHONPATH
do not. This is source provenance, not a sandbox against hostile bundle writers.
"""

import hashlib
import json
from pathlib import Path
import site
import subprocess
import sys


def verify_manifest_bundle(manifest_path, expected_sha256):
    raw = Path(manifest_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("frozen manifest fingerprint mismatch")
    manifest = json.loads(raw)
    bundle = Path(manifest["source_bundle"]["path"])
    if not bundle.is_absolute() or not bundle.is_dir():
        raise ValueError("frozen bundle must be an existing absolute directory")
    # Same path+content algorithm as campaign_freeze.fingerprint_tree, without
    # importing project code before checking it. No bytecode files are ignored.
    digest = hashlib.sha256()
    files = sorted((p for p in bundle.rglob("*") if p.is_file()), key=lambda p: p.as_posix())
    for path in files:
        file_digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                file_digest.update(chunk)
        digest.update(path.relative_to(bundle).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest.digest())
        digest.update(b"\0")
    if (digest.hexdigest() != manifest["source_bundle"]["sha256"]
            or len(files) != manifest["source_bundle"]["file_count"]):
        raise ValueError("frozen bundle fingerprint mismatch")
    if (manifest.get("execution") or {}).get("mode") != "frozen-subprocess":
        raise ValueError("manifest does not declare frozen execution")
    return manifest


def restore_installed_user_site():
    """Re-expose third-party packages installed in the mounted user site under ``-I``.

    The frozen child intentionally ignores cwd and PYTHONPATH, but the Docker runtime
    installs OpenTTDLab in ``/home/lab/.local``.  Python ``-I`` disables that user site
    entirely, contradicting this module's contract that installed third-party packages
    remain available.  Add only Python's own resolved user-site directory after the
    manifest/bundle verification; frozen harness paths still stay ahead of it.
    """
    locations = site.getusersitepackages()
    if isinstance(locations, str):
        locations = [locations]
    added = []
    for location in locations:
        path = Path(location)
        text = str(path)
        if path.is_dir() and text not in sys.path:
            sys.path.append(text)
            added.append(text)
    return added


def frozen_command(campaign):
    """No shell, inherited module cache, live cwd, or PYTHONPATH in the child."""
    bootstrap = campaign.bundle_dir / "harness" / "sweeps" / "frozen_harness.py"
    return [sys.executable, "-I", "-B", "-X", "utf8", str(bootstrap),
            str(campaign.manifest_path), campaign.manifest_sha256]


def launch_frozen_campaign(campaign):
    verify_manifest_bundle(campaign.manifest_path, campaign.manifest_sha256)
    # Keep stdout/stderr attached: engine progress and failures remain visible.
    return subprocess.run(
        frozen_command(campaign), cwd=campaign.bundle_dir / "harness", check=False,
    ).returncode


def restore_campaign(manifest_path, expected_sha256, manifest):
    """Rebuild local library callbacks, without Git, network, or a second freeze."""
    from campaign_freeze import FrozenCampaign, _frozen_library_descriptor

    bundle = Path(manifest["source_bundle"]["path"])
    artifacts = manifest["artifacts"]
    return FrozenCampaign(
        campaign_id=manifest["campaign_id"],
        out_path=Path(artifacts["result"]),
        checkpoint_path=Path(artifacts["checkpoints"]),
        engine_log_dir=Path(artifacts["engine_logs"]),
        manifest_path=Path(manifest_path),
        manifest_sha256=expected_sha256,
        bundle_dir=bundle,
        bundle_sha256=manifest["source_bundle"]["sha256"],
        opex_dir=bundle / "ai" / "OpexAI",
        aaahogex_dir=bundle / "ai" / "AAAHogEx-115",
        ai_libraries=tuple(
            _frozen_library_descriptor(group["requested_name"], group["resolved"],
                                       bundle / "ai_libraries")
            for group in manifest["libraries"]
        ),
        manifest=manifest,
    )


def main():
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("frozen bootstrap requires Python -I -B")
    if len(sys.argv) != 3:
        raise ValueError("expected manifest path and SHA256")
    manifest_path, expected_sha256 = sys.argv[1:]
    manifest = verify_manifest_bundle(manifest_path, expected_sha256)
    restore_installed_user_site()
    harness = Path(manifest["source_bundle"]["path"]) / "harness" / "sweeps"
    if Path(__file__).resolve() != (harness / "frozen_harness.py").resolve():
        raise ValueError("bootstrap is not inside the declared frozen bundle")
    sys.path.insert(0, str(harness))
    campaign = restore_campaign(manifest_path, expected_sha256, manifest)
    if campaign.out_path.exists() or campaign.checkpoint_path.exists():
        raise FileExistsError("refusing to replay a campaign with existing results/checkpoints")
    if any(campaign.engine_log_dir.iterdir()):
        raise FileExistsError("refusing to replay a campaign with existing engine logs")
    # Import by name once so multiprocessing can resolve the same frozen module.
    from bench_1v1_5y_20seeds import execute_frozen_campaign
    execute_frozen_campaign(campaign)


if __name__ == "__main__":
    main()
