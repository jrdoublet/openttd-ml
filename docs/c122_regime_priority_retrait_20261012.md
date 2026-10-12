# Retrait C122 — priorité AIR par régime

[État documentaire et publication demandée le12/10](passation_nettoyage_parametres_20261012.md), [preuves versionnées](../evidence/review/parameter_cleanup_20261012/README.md). Les mentions « aucun commit/push » ci-dessous décrivent la validation avant cette demande.

Décision utilisateur du 12/10 : supprimer `c122_air_regime_priority` et nettoyer après le [40×3](c122_regime_priority_40x3_20261012.md). Le verdict brut `fail_primary` est conservé : gain non démontré, aucune perte significative ni neutralité prouvée. Le retrait est une décision utilisateur de simplification.

## Périmètre

Déclaration, globale et chargement du réglage supprimés, ainsi que le helper exclusif `OpexC122AirRegimePriority`, les branches qui réordonnaient les projets AIR et leur trace exclusive `C122_PROMOTE`/compteurs. Le classement conserve les tiers C77 puis les scores économiques de l'ancien défaut OFF.

Le shadow `c122_air_regime_shadow`, `OpexC122AirRegimeTier` et `OpexC122TraceShadow` restent disponibles sans réordonnancement. La sonde d'exposition et les annotations `defensiveNewTownClaims` sont conservées ; le champ de trace `promotions=0` conserve la compatibilité du format. Les sondes de menace et le retry C122.4 sont indépendants et restent présents. Aucun réglage de sonde supprimé.

Classifieur C121, pression partagée et réalisation adaptative conservés. Seules les conditions d'activation perdent le drapeau retiré ; le bloc persistant `c121Strategy`, son schéma et son chargement sont inchangés. Trois diagnostics perdent leur override désormais invalide. Travaux parallèles AC/CD/P0, `probes.nut` et son test de flux station préservés.

## Validation

**106 tests ciblés verts** : C122/shadow/menace (10), persistance R20 (10), économie C121 (52), défense C77 (7), sonde d'amortissement flotte (27). Une empreinte de constructeur était périmée depuis le retrait précédent de `c121_air_initial_project_economics` : actualisée à `7e9493026ebb9e0fdc4408a2ae934eb12c0e4a0082c23cbe973f50d4d910b29a`, vérifiée identique dans la copie figée du40×3 C122. Ce retrait C122 ne modifie ni le constructeur ni le helper de sonde. L'assertion d'intégrité reste active.

Smoke du défaut `cleanup_c122_regime_smoke_20261012_r1`, graine42 ×1 an : **1/1 duel sain**, OpexAI et AAAHogEx complètes, actives, `run_ok=true`, horizon complet, aucune erreur non attribuée. Réglage absent des défauts effectifs du manifeste. Validation compilation/exécution uniquement ; aucune identité de trajectoire ni économie d'opcodes revendiquée. Save/Load validé par les contrats ciblés de l'état partagé ; aucun nouveau roundtrip moteur, schéma inchangé.

Sources figées depuis HEAD `f6139d89f299bcd3d2d24bc32bf22fef6df21d8f`, avec modifications locales présentes et sondes parallèles préservées. Docker local `desktop-linux`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, cache `openttd-lab-home`,10 CPU/8 Go/swap8 Go/10 workers. Bundle `9598517e0d0b3e2de36bb0dbecff11b7ff5fe1d2416e705843312a38cc64a917`, manifeste `d89dc4b4a83be21d94d0dd9554cd686692b7b8d161f765e88a76e43c23281ac2`.

[JSON du smoke](../results/cleanup_c122_regime_smoke_20261012_r1.json), [manifeste](../results/cleanup_c122_regime_smoke_20261012_r1.manifest.json). Recherche des références actives et `git diff --check` effectués. Aucun banc économique supplémentaire, commit ni push.
