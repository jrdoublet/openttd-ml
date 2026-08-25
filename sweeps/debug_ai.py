"""Lance le binaire OpenTTD directement (hors OpenTTDLab) avec le debug script/AI active,
pour voir la sortie AILog en direct. OpenTTDLab capture bien `row['output']`, mais OpenTTD ne
produit AUCUNE sortie console en mode headless sans le flag -d, qu'il n'existe aucun moyen de
passer via run_experiments. C'est le seul moyen trouve de deboguer un script Squirrel qui
echoue silencieusement (utilise pour trouver et corriger 5 bugs de ai/TrainLineAI/, voir
docs/methode.md).

Usage :
    python sweeps/debug_ai.py <dossier_ia> <nom_ia> "<ligne start_ai>" [ticks] [seed] [cfg_extra] [libs]

Exemple :
    python sweeps/debug_ai.py ai/TrainLineAI TrainLineAI \\
        "start_ai TrainLineAI num_trains=2,wagons_per_train=2" \\
        8000 42 "[difficulty]\\nnumber_towns = 2\\n" "ai-library/5046524c"

`ticks` : 74 ticks/jour. En dessous d'un certain seuil (~200 ticks/2.7 jours, mesure) l'IA n'a
pas encore demarre et ne produit aucune sortie -- ne pas confondre avec un vrai echec silencieux.
`libs` : identifiants BaNaNaS separes par des virgules, ex. "ai-library/5046524c" pour
Pathfinder.Rail (voir README pour les IDs deja utilises dans ce projet).
"""
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

OPENTTD_VERSION = "13.4"
OPENGFX_VERSION = "7.1"
OPENTTDLAB_VERSION = "0.0.75"  # doit matcher requirements.txt

RUN_ROOT = "/tmp/openttd-ml-debug_ai"


def main():
    ai_dir = os.path.abspath(sys.argv[1])
    ai_name = sys.argv[2]
    start_line = sys.argv[3]
    ticks = sys.argv[4] if len(sys.argv) > 4 else "8000"
    seed = sys.argv[5] if len(sys.argv) > 5 else "1"
    extra_cfg = sys.argv[6] if len(sys.argv) > 6 else ""
    libraries = sys.argv[7].split(",") if len(sys.argv) > 7 and sys.argv[7] else []

    run = os.path.join(RUN_ROOT, "rundir")
    shutil.rmtree(RUN_ROOT, ignore_errors=True)
    os.makedirs(os.path.join(run, "baseset"), exist_ok=True)
    os.makedirs(os.path.join(run, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(run, "ai"), exist_ok=True)

    cache = os.path.expanduser(f"~/.cache/OpenTTDLab/{OPENTTDLAB_VERSION}")
    openttd_tar = os.path.join(cache, f"openttd-{OPENTTD_VERSION}-linux-generic-amd64.tar.xz")
    opengfx_zip = os.path.join(cache, f"opengfx-{OPENGFX_VERSION}-all.zip")
    if not os.path.exists(openttd_tar) or not os.path.exists(opengfx_zip):
        sys.exit(
            f"Cache introuvable ({openttd_tar} / {opengfx_zip}).\n"
            "Lancez d'abord un run_experiments normal (ex. sweeps/phase0_timing.py) pour "
            "peupler le cache OpenTTDLab, ou ajustez OPENTTD_VERSION/OPENGFX_VERSION/"
            "OPENTTDLAB_VERSION en tete de ce script."
        )

    with tarfile.open(openttd_tar, "r:xz") as t:
        t.extractall(RUN_ROOT)
    with zipfile.ZipFile(opengfx_zip) as z:
        z.extractall(os.path.join(run, "baseset"))

    with tarfile.open(os.path.join(run, "ai", ai_name + ".tar"), "w") as t:
        t.add(ai_dir, arcname=ai_name)
    print("tar:", tarfile.open(os.path.join(run, "ai", ai_name + ".tar")).getnames())

    if libraries:
        from openttdlab import download_from_bananas
        os.makedirs(os.path.join(run, "ai", "library"), exist_ok=True)
        for content_id in libraries:
            with download_from_bananas(content_id) as filenames:
                for cid, filename, license_, md5, get_data in filenames:
                    with get_data() as chunks:
                        data = b"".join(chunks)
                    out = os.path.join(run, "ai", "library", filename)
                    open(out, "wb").write(data)
                    print("library:", out)

    with open(os.path.join(run, "openttdlab.cfg"), "w") as f:
        f.write(extra_cfg.replace("\\n", "\n") + "\n[gui]\nthreaded_saves = false\nautosave = off\n")

    with open(os.path.join(run, "scripts", "game_start.scr"), "w") as f:
        f.write(start_line + "\n")

    binary = os.path.join(RUN_ROOT, f"openttd-{OPENTTD_VERSION}-linux-generic-amd64", "openttd")
    cmd = [binary, "-g", "-G", seed, "-snull", "-mnull", f"-vnull:ticks={ticks}",
           "-c", "openttdlab.cfg", "-d", "script=4"]
    print("running:", cmd)
    result = subprocess.run(cmd, cwd=run, capture_output=True, text=True, timeout=60)
    print("=== STDOUT+STDERR ===")
    print(result.stdout)
    print(result.stderr)
    print("exit code:", result.returncode)


if __name__ == "__main__":
    main()
