# Fusion du nettoyage C118/C119/C120 avec master — 13 octobre 2026

Demande utilisateur : « Fusionne la branche avec master ». Intégration dans le
checkout isolé `results/c118_c119_merge_stage_20261012` pour préserver le checkout
principal dirty et ses diagnostics P0. Branche publiée avant fusion :
`codex/c118-c119-merge-20261012`, HEAD `68759f5`. Distant intégré :
`origin/master` au `c309272`, 14 commits supplémentaires depuis la préparation.
Les nouveaux défauts V159 (`c117_lean_sampling=1`) et V161
(`v161_fleet_net_marginal=1`) sont conservés avec V157/V158/V160 à 1.
Leurs décisions et verdicts historiques restent ceux de master.

## Résolution et contrats

Un seul conflit : empreinte globale du builder dans
`sweeps/test_parallel_fleet_amort_shadow.py`. Helper de sonde identique aux deux
parents ; builder fusionné exactement égal à celui de master privé de la seule
annotation C118 retirée. Empreinte recalculée après cette vérification.
Deux espaces finaux hérités du document V159 retirés.

287 contrats ciblés verts, zéro erreur/échec/skip, dont V159 et V161 ; autres
spécifications de réglages identiques à master, C118/C119/C120 absents des chemins
actifs. Pas de modification supplémentaire de politique, ni requalification
économique du cumul. [Audit et contrats](../results/cleanup_master_merge_contracts_20261013.json).

## Smoke pré-enregistré

`cleanup_master_merge_defaults_smoke_20261013_r1`, graine42, un an, un duel
Opex/AAAHogEx, défauts effectivement livrés, aucune variante économique.
Harnais `run_c66_reference.py`, code fusionné committé avant exécution, contexte
Docker `desktop-linux`, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
10 CPU/8 Go RAM/swap 8 Go/10 workers, volume `openttd-lab-home`.
Montage racine avec répertoire d'exécution dans le checkout isolé ; Docker libre
vérifié. Compilation/exécution, santé et horizon attendu à un an ; trois
trimestres valides possibles la première année. Pas de preuve économique.

Après smoke sain et audit des manifestes : publication normale vers master et
actualisation de la branche, sans force-push, sans toucher aux fichiers locaux P0.
Si master avance avant le push, intégrer et revalider les changements pertinents.
