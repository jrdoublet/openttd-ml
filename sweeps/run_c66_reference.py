"""Host-side launcher for reproducible C66.3 shared 1v1 campaigns.

This launcher intentionally runs outside the container.  It captures the Git state
and the exact Docker image ID immediately before ``docker run`` and injects them into
the benchmark, while enforcing the repository's CPU/RAM/cache-volume limits.
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def docker_workspace(mount_root=None):
    """Allow an isolated worktree inside an already shared Docker parent."""
    root = Path(mount_root).resolve() if mount_root is not None else ROOT
    relative = ROOT.relative_to(root)  # Reject unrelated mounts before Docker.
    workdir = "/work" if relative == Path(".") else "/work/" + relative.as_posix()
    return root, workdir


def container_archive_destination(destination, mount_root, container_workdir, campaign):
    """Place a retained savegame archive outside the immutable source bundle.

    The frozen child runs from `<campaign>_bundle/harness`, so forwarding a
    relative path unchanged silently writes inside the fingerprinted bundle.
    Map the host's requested path to its mounted `/work` path instead.
    """
    requested = Path(destination)
    host_path = (requested if requested.is_absolute() else ROOT / requested).resolve()
    try:
        relative = host_path.relative_to(Path(mount_root).resolve())
    except ValueError as error:
        raise ValueError("--retain-savegames must be under the Docker-mounted repository") from error
    bundle = (ROOT / "results" / (campaign + "_bundle")).resolve()
    if host_path == bundle or bundle in host_path.parents:
        raise ValueError("--retain-savegames must be outside the frozen source bundle")
    return container_workdir.rsplit("/", 1)[0] + "/" + relative.as_posix() if container_workdir != "/work" else "/work/" + relative.as_posix()


def _output(args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--image", default="openttd-lab:latest")
    parser.add_argument("--mount-root", type=Path, help="Shared ancestor containing this worktree; default is the worktree itself")
    parser.add_argument("--container-name", help="Nom optionnel pour nettoyage borné par l'orchestrateur")
    parser.add_argument("--policy-id", default="reference")
    parser.add_argument("--reference")
    parser.add_argument("--variant")
    parser.add_argument("--variant-policy-id")
    parser.add_argument("--primary-metric")
    parser.add_argument("--min-useful-primary-delta", type=float)
    parser.add_argument("--value-guard-max-loss-pct", type=float)
    parser.add_argument("--decision-rule",
                        choices=["signs20", "mean40", "gain_short", "non_erosion"],
                        default="signs20",
                        help="Règle d'adoption C66.4 (défaut 'signs20'). V102 ajoute "
                             "'gain_short' (porte A de gain, court et large) et "
                             "'non_erosion' (porte B, 20x10 unilatérale).")
    parser.add_argument("--min-useful-primary-delta-pct", type=float,
                        help="V102 : seuil de gain en %% du profit de référence de l'année "
                             "terminale, au lieu du seuil absolu. Exactement un des deux "
                             "seuils sous 'gain_short' et 'non_erosion'.")
    parser.add_argument("--required-seeds", type=int,
                        help="V102 : graines exigées par 'gain_short' (défaut 40).")
    parser.add_argument("--required-years", type=int,
                        help="V102 : horizon exigé par 'gain_short' (défaut 3).")
    parser.add_argument("--years", type=int)
    parser.add_argument("--seeds", nargs="+", type=int)
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--max-workers", type=int)
    parser.add_argument("--engine-timeout", type=int)
    parser.add_argument("--line-telemetry", action="store_true")
    parser.add_argument("--station-supply-telemetry", action="store_true")
    parser.add_argument("--retain-savegames", help="Diagnostic: dossier de copie des sauvegardes dans le conteneur")
    parser.add_argument("--line-telemetry-monthly", action="store_true")
    parser.add_argument("--script-debug", action="store_true")
    parser.add_argument("--cpus", type=int, default=3)
    parser.add_argument("--network",
                        help="Mode reseau Docker (ex. 'host'). Non precise = pont Docker par "
                             "defaut. Utile quand bananas-api.openttd.org n'est joignable qu'en "
                             "IPv6 : le pont Docker est IPv4 seul, le gel des bibliotheques "
                             "BaNaNaS part alors en ReadTimeout. Le reseau ne sert qu'a ce "
                             "telechargement de preparation ; la simulation est locale et les "
                             "empreintes des tars restent dans le manifeste, donc la mesure est "
                             "inchangee.")
    parser.add_argument("--memory", default="2g",
                        help="plafond RAM Docker, swap egal (defaut 2g). "
                             "Pic observe sous 800 Mo meme a 10 workers en duel 10 ans ; "
                             "sur le VPS, 3 workers avec 2 Go suffisent.")
    parser.add_argument("--out")
    args = parser.parse_args()

    # V102 : echouer AVANT de demarrer Docker. On ne peut pas importer
    # c66_threshold_specification_error ici (bench_1v1_5y_20seeds tire openttdlab, absent de
    # l'hote), donc la regle est repetee a l'identique ; le banc la revalide dans le conteneur.
    if args.variant is not None:
        _absolute = args.min_useful_primary_delta
        _pct = args.min_useful_primary_delta_pct
        if args.decision_rule in ("signs20", "mean40"):
            if _absolute is None:
                parser.error("--min-useful-primary-delta doit etre fixe avant un banc C66.4")
            if _pct is not None:
                parser.error("--min-useful-primary-delta-pct ne s'applique qu'a gain_short "
                             "et non_erosion")
        else:
            if (_absolute is None) == (_pct is None):
                parser.error("gain_short et non_erosion exigent exactement un seuil : "
                             "--min-useful-primary-delta ou --min-useful-primary-delta-pct")
            if _pct is not None and _pct < 0:
                parser.error("--min-useful-primary-delta-pct doit etre >= 0")

    mount_root, container_workdir = docker_workspace(args.mount_root)

    git_sha = _output(["git", "rev-parse", "HEAD"])
    git_status = _output(["git", "status", "--porcelain=v1", "--untracked-files=all"])
    git_dirty = "1" if git_status else "0"
    git_status_b64 = base64.b64encode(git_status.encode("utf-8")).decode("ascii")
    image_id = _output(["docker", "image", "inspect", args.image, "--format", "{{.Id}}"])

    benchmark = [
        "python3", "sweeps/bench_1v1_5y_20seeds.py",
        "--campaign", args.campaign,
        "--policy-id", args.policy_id,
    ]
    if args.years is not None:
        benchmark += ["--years", str(args.years)]
    if args.seeds is not None:
        benchmark += ["--seeds", *(str(seed) for seed in args.seeds)]
    if args.repeats is not None:
        benchmark += ["--repeats", str(args.repeats)]
    if args.max_workers is not None:
        benchmark += ["--max-workers", str(args.max_workers)]
    if args.engine_timeout is not None:
        benchmark += ["--engine-timeout", str(args.engine_timeout)]
    if args.line_telemetry:
        benchmark += ["--line-telemetry"]
    if args.station_supply_telemetry:
        benchmark += ["--station-supply-telemetry"]
    if args.retain_savegames:
        benchmark += ["--retain-savegames", container_archive_destination(
            args.retain_savegames, mount_root, container_workdir, args.campaign)]
    if args.line_telemetry_monthly:
        benchmark += ["--line-telemetry-monthly"]
    if args.script_debug:
        benchmark += ["--script-debug"]
    if args.variant is not None:
        benchmark += ["--variant", args.variant]
    if args.reference is not None:
        benchmark += ["--reference", args.reference]
    if args.variant_policy_id is not None:
        benchmark += ["--variant-policy-id", args.variant_policy_id]
    if args.primary_metric is not None:
        benchmark += ["--primary-metric", args.primary_metric]
    if args.min_useful_primary_delta is not None:
        benchmark += ["--min-useful-primary-delta", str(args.min_useful_primary_delta)]
    if args.value_guard_max_loss_pct is not None:
        benchmark += ["--value-guard-max-loss-pct", str(args.value_guard_max_loss_pct)]
    if args.decision_rule is not None:
        benchmark += ["--decision-rule", args.decision_rule]
    # V102 : chacune seulement si fournie, pour que la ligne de commande d'une campagne
    # 'signs20' historique reste identique au bit près.
    if args.min_useful_primary_delta_pct is not None:
        benchmark += ["--min-useful-primary-delta-pct", str(args.min_useful_primary_delta_pct)]
    if args.required_seeds is not None:
        benchmark += ["--required-seeds", str(args.required_seeds)]
    if args.required_years is not None:
        benchmark += ["--required-years", str(args.required_years)]
    if args.out is not None:
        benchmark += ["--out", args.out]

    command = [
        "docker", "run", "--rm",
        *(["--name", args.container_name] if args.container_name else []),
        *([f"--network={args.network}"] if args.network else []),
        f"--cpus={args.cpus}", f"--memory={args.memory}", f"--memory-swap={args.memory}",
        "-e", f"C66_DOCKER_NETWORK={args.network or 'bridge'}",
        "-e", f"C66_DOCKER_IMAGE={args.image}",
        "-e", f"C66_DOCKER_IMAGE_ID={image_id}",
        "-e", f"C66_DOCKER_CPUS={args.cpus}",
        "-e", f"C66_DOCKER_MEMORY={args.memory}",
        "-e", f"C66_DOCKER_MEMORY_SWAP={args.memory}",
        "-e", f"C66_GIT_SHA={git_sha}",
        "-e", f"C66_GIT_DIRTY={git_dirty}",
        "-e", f"C66_GIT_STATUS_B64={git_status_b64}",
        "-v", "openttd-lab-home:/home/lab",
        "-v", f"{mount_root}:/work",
        "-w", container_workdir,
        args.image,
        *benchmark,
    ]

    print(f"{'C66.4' if args.variant else 'C66.3'} campaign: {args.campaign}")
    print(f"Git: {git_sha} dirty={git_dirty}")
    print(f"Docker: {args.image} {image_id}")
    completed = subprocess.run(command, cwd=ROOT)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
