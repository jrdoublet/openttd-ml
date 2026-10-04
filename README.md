# openttd-ml / OpexAI

OpexAI est une IA OpenTTD multimodale (rail, route, air, eau). Le projet mesure
ses décisions économiques face à AAAHogEx sur carte partagée. La prédiction du
profit d'une ligne et TrainLineAI sont les origines du projet, pas son backlog actuel.

## Lire et contribuer

| Besoin | Document |
|---|---|
| État courant, priorités, blocages | [Tâches](docs/taches.md) — seule liste autoritaire du travail restant |
| Consignes et protocole | [AGENTS.md](AGENTS.md) — invariants, validation, preuves, bancs pilotés par agents |
| Navigation de tout le corpus | [Index documentaire](docs/README.md) |
| Comprendre le code | [Architecture courante](docs/architecture_courante.md) |
| Comprendre une décision | [Synthèse historique](docs/journaux/synthese_decisions_2026-09-30.md), [journaux](docs/journaux/README.md) |
| Vérifier une preuve | [Archives de résultats](evidence/review/README.md) |

**Cible : OpenTTD 15.3 / API NoAI 15 / OpenGFX 7.1 / OpenTTDLab 0.0.75.**
Les correctifs locaux non exécutés sont signalés dans les tâches. Une documentation
réconciliée ne constitue ni un nouveau résultat économique ni une adoption.

## Fonctionnement

`ai/OpexAI/main.nut` assemble les modules. Le catalogue alimente un portefeuille
commun ; `projects.nut` sélectionne selon le profit attendu/calibré, le capital
et les priorités, avec le dénominateur C69. `fundScore` reste une heuristique,
pas une preuve de rentabilité. Les tâches exécutent et entretiennent les lignes ;
`persist.nut` gère Save/Load et leur réconciliation.

Les défauts et expériences protégés sont suivis dans `docs/taches.md` ; vérifier
ensemble `info.nut`, `settings.nut` et les usages avant toute modification.

## Validation et bancs GitHub

Depuis le 03/10/2026, la qualification comportementale suit **V102** : contrats,
smoke 1×1, porte A **40×3 `gain_short`**, puis porte B **20×10 `non_erosion`**.
Le 5×6 n'est plus obligatoire ; la règle opcodes reste distincte.
[AGENTS.md §4/§4.1](AGENTS.md#4-validation-proportionnée-puis-adoption) définit
les critères et les options explicites de `sweeps/run_c66_reference.py`.

**Les workflows GitHub ne sont pas encore migrés vers V102.** `qualify.yml`
et son [plan de schéma 1](qualifications/README.md) conservent l'ancien parcours
smoke→5×6→20×10 sous `signs20`. Ne pas les utiliser comme substitut aux deux portes.

**Actions → Bancs OpenTTD → Run workflow** : choisir branche, mode (`solo`, `duel`,
`paired`) et profil (`smoke`, `diagnostic`, `adoption`, `custom`). Pour vérifier
l'installation : `solo/smoke`. Les profils actuels restent disponibles pour les
diagnostics et protocoles historiques ; `paired/adoption` applique encore `signs20`.

Le workflow doit être publié ; **seul le code de la branche choisie est exécuté**,
pas les fichiers locaux non envoyés. Aucun commit/push implicite. Lire santé,
horizon, couverture et verdict dans les artefacts, pas seulement la couleur du job.
[Guide complet](docs/bancs_github.md).

## Environnement local et VPS

Docker : [Dockerfile](Dockerfile), dépendances [simulation](requirements.txt)
et [ML](requirements-ml.txt). La cible `simulation` prépare les bancs, la cible
finale `ml` ajoute la modélisation. Python réside dans `/opt/venv`, hors du cache
persistant `/home/lab` ; les anciens paquets utilisateur ne masquent plus l'image.
Reconstruire après changement des requirements, sans supprimer le volume de cache.

Sur le VPS : **3 CPU, 2 Go, aucun swap, trois workers maximum, une campagne à la fois** ;
volume `openttd-lab-home:/home/lab` et dépôt réellement monté dans `/work`.
Commandes et contrôles préalables : [AGENTS.md §3](AGENTS.md#3-outils-édition-et-environnement).
Git/RTK/Python/Docker manquants doivent être signalés ; aucune installation implicite.

## Historique

[Phase 0 / TrainLineAI — synthèse](docs/archives/phase0_trainline_synthese.md) :
anciennes versions, calibration, métriques, bugs et ruptures de campagne.
[Méthode détaillée](docs/methode.md), [ML](docs/phase3_ml.md) et anciennes fiches
restent consultables depuis l'index. Leurs anciens « à faire » ne sont pas actifs.
Les résultats antérieurs au **9 septembre 2026** ne font plus preuve actuelle ;
les plus récents exigent aussi des sources et un protocole vérifiables.
