# CARTO-1 long — commandes utilisateur à lancer manuellement

État préparé le 24 octobre 2026, **sans exécution de Docker par l'agent**.
Racine du dépôt `/openttd-ml`, travail isolé dans `.worktrees/carto1`.
Le manifeste **pré-enregistré, non exécuté** est
`docs/carto1_long_prelaunch_20261024.json`. Les noms de campagnes ci-dessous
étaient libres lors de la préparation. Chaque commande lance un unique
conteneur via `sweeps/run_c66_reference.py` : les exécuter
**séquentiellement**, après la fin des autres bancs du PC.

## Avant les commandes de jeu

Dans PowerShell à la racine du dépôt :

```powershell
Set-Location .worktrees/carto1
python -X utf8 -m unittest sweeps.test_carto1 sweeps.test_carto1_runtime sweeps.test_carto1_long_rlw sweeps.test_carto1_long_analysis sweeps.test_v308_quinconce -q
git diff --check
```

Vérifier le contenu du worktree et conserver ses modifications locales.
Le profil cible est OpenTTD 15.3, OpenGFX 7.1, image `openttd-lab:latest`,
un Docker à la fois, **10 CPU maximum, 8 Gio maximum**. Le lanceur gèle les
fichiers source et produit `.manifest.json`, `.json`, `.jsonl`, `_engine/`
et `_bundle/` sous `results/`. `probes=50331650` allume les bits 24 et 25
et conserve le bit 2 des panneaux ; les défauts de l'IA restent OFF.

## 1. Smoke de sécurité (1 graine, 1 an, 1024²)

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign carto1_long_user_smoke1024_s42_1x1_20261024 --reference "OpexAI[probes=50331650]" --years 1 --seeds 42 --repeats 1 --map-size 10 --start-year 1970 --script-debug --cpus 10 --memory 8g --max-workers 1 --engine-timeout 3600
```

Inspecter `results/carto1_long_user_smoke1024_s42_1x1_20261024_engine/reference_seed42_r0.log` :
`RLW04B_ENUM phase=done` doit montrer `overruns=0 ticks=0 stock=30`.
Rechercher aussi `CARTO1_LONG_SAFETY phase=abort` et
`CARTO1_LONG_SUMMARY phase=unsafe`. **Si l'un apparaît, arrêter ici :
ne pas lancer les bancs 3×3 ou 3×10.** Une opération `FindPath(1)`
peut franchir un tick même avec la plus grande réserve, et le nouveau
disjoncteur stoppe ensuite définitivement la sonde dans la partie.
Il ne transforme pas cet incident en résultat A* exploitable.

## 2. Exposition diagnostique (3 graines × 3 ans, 1024²)

Seulement si le smoke compile, termine sainement et ne signale
aucun franchissement :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign carto1_long_user_diag1024_3x3_20261024 --reference "OpexAI[probes=50331650]" --years 3 --seeds 42 100 999 --repeats 1 --map-size 10 --start-year 1970 --script-debug --cpus 10 --memory 8g --max-workers 3 --engine-timeout 3600
```

Analyse hors Docker de la campagne après sa fin :

```powershell
python -X utf8 sweeps/analyze_carto1_long.py results/carto1_long_user_diag1024_3x3_20261024_engine --years 3 --format json --out results/carto1_long_user_diag1024_3x3_20261024_analysis.json --require-complete
```

Le retour 1 du comparateur signifie que la qualification est **refusée** :
échantillons manquants, franchissement d'un tick, moins de 20 échecs,
ou autre condition du protocole. Lire les raisons dans le JSON.

## 3. Extension diagnostique distincte (3 graines × 10 ans, 1024²)

Uniquement si la sonde passe le contrôle de sécurité de **toutes** les
graines à trois ans, sans erreur ni dépassement :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign carto1_long_user_extended1024_3x10_20261024 --reference "OpexAI[probes=50331650]" --years 10 --seeds 42 100 999 --repeats 1 --map-size 10 --start-year 1970 --script-debug --cpus 10 --memory 8g --max-workers 3 --engine-timeout 3600
```

Analyse correspondante, toujours hors Docker :

```powershell
python -X utf8 sweeps/analyze_carto1_long.py results/carto1_long_user_extended1024_3x10_20261024_engine --years 10 --format json --out results/carto1_long_user_extended1024_3x10_20261024_analysis.json --require-complete
```

**Ce troisième banc est une extension diagnostique, et non une nouvelle
preuve prédictive attendue :** les anciens 83 A* terminés sur les mêmes
graines étaient tous `OK`. Avec les extrémités virtuelles actuelles,
le panel n'a toujours aucune raison démontrée de contenir les 20 échecs
nécessaires. Une nouvelle hypothèse de sélection de vrais cas difficiles
devra être définie **avant** toute tentative de qualification du seuil.

Les trois campagnes conservent les graines 42, 100 et 999 du protocole
original ; chaque graine contient un réservoir déterministe figé de 30
paires entre 224 et 288 tuiles Manhattan. Le seuil éventuel doit être
entraîné sur deux graines et testé sur la troisième. Aucun seuil ne
sera appris tant qu'un incident de sécurité ou une absence de classe
positive invalide les observations.

En cas de `httpx.ReadTimeout` pendant le gel de BaNaNaS **avant le
premier jeu**, reprendre dans une **nouvelle campagne** et ajouter
`--network host` au lanceur, selon `AGENTS.md`. Ne jamais réutiliser
un nom de campagne ou effacer un ancien bundle pour contourner un conflit.

## Contrôle historique hors Docker

L'analyse de sécurité de l'ancienne campagne 3×10 est déjà disponible dans
`results/carto1_long_shadow1024_3x10_20261024_safety_audit.json`.
Elle relève **204 franchissements sur 83 A***, **0 échec A***, et une
incomplétude de 7 résultats. Cette preuve appartient au code antérieur
au disjoncteur ; les campagnes nouvelles doivent recevoir d'autres noms
et leurs propres manifestes.
