# Retrait C121 — économie du projet initial

[État documentaire et publication demandée le12/10](passation_nettoyage_parametres_20261012.md), [preuves versionnées](../evidence/review/parameter_cleanup_20261012/README.md). Les mentions « aucun commit/push » ci-dessous décrivent la validation avant cette demande.

Décision utilisateur du 12/10 : supprimer `c121_air_initial_project_economics` et nettoyer le code après le [40×5](c121_initial_project_40x5_20261012.md). Ce retrait est une décision de simplification ; le verdict brut `fail_primary` reste conservé, sans transformer l'absence de gain démontré en preuve de perte ou de neutralité.

## Périmètre

Déclaration du réglage, globale et chargement retirés. Les deux constructeurs AIR de `projects_builders.nut` utilisent directement `decisionEconomics` et `decisionBudgetCapital` pour le classement et la décision financière, comme à l'ancien défaut OFF. Les variables et branches exclusives sont supprimées.

Le devis d'ouverture `economics`, le capital réel et le budget de construction restent distincts du devis décisionnel ; financement partagé, C111/C113, apprentissage des devis et champs de persistance conservés. Aucun schéma Save/Load modifié. Les sondes restent présentes : les champs de trace `init` et `initial` sont conservés à 0, et l'analyseur accepte toujours les anciennes traces ON. Le diagnostic temporaire partagé perd uniquement son override du réglage retiré.

Les travaux parallèles AC/CD et d'autopsie opcode, notamment les modifications préexistantes de `probes.nut` et de son test de flux station, sont préservés.

## Validation

**94 contrats ciblés verts** : économie C121 (52), C111 (7), C113 (4), apprentissage du devis capital (8), analyseur de table moteur (13), sonde investissement (3), portefeuille B6 (7). Aucune référence active à la globale retirée ni aux alias exclusifs ne subsiste. `git diff --check` passe.

Smoke du défaut livré `cleanup_initial_project_smoke_20261012_r1`, graine 42 × 1 an : **1/1 duel sain**, OpexAI et AAAHogEx `run_ok=true`, horizon complet, actives, aucune erreur non attribuée. Le réglage retiré est absent du manifeste. Ce smoke valide compilation/exécution, sans mesure causale de rentabilité ni d'opcodes.

Sources figées depuis `master` HEAD `f6139d89f299bcd3d2d24bc32bf22fef6df21d8f`, avec les modifications locales présentes, y compris les sondes parallèles préservées. Docker local `desktop-linux`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, cache `openttd-lab-home`, 10 CPU/8 Go/swap 8 Go/10 workers. Bundle `14e6e838b5da873f9dc317f3644ecb9c935887677e6c34f1e2963ec8bb1dfeb4`, manifeste `7dbc462a003beab35e0388164f9d9d2e1c62b87c70b4b193ef4966d6bfba2adf`.

[JSON du smoke](../results/cleanup_initial_project_smoke_20261012_r1.json), [manifeste](../results/cleanup_initial_project_smoke_20261012_r1.manifest.json). Aucune identité de trajectoire ni qualification économique du cumul des nettoyages revendiquée. Aucun commit ni push demandé ou effectué pour ce retrait.
