# Retrait de c121_air_engine_realization

Décision utilisateur du 12/10/2026 : supprimer le réglage et nettoyer son code exclusif. Aucun commit ni push demandé.

## Historique conservé

Comparaison exploratoire `c121_nuit10_20261003_210612_air_engine_realization_exploration`, référence isolée `a848df8`, 40 graines ×3 ans, ON−OFF, chaque bras contre AAAHogEx en carte partagée, C121 economics/catalogue à1. 40/40 paires complètes/saines, échantillon et métriques complets. Profit annuel terminal moyen −33 066,8 £/an (−2,314733 %), médiane0, IC95 bootstrap [−79 181,6 ; +15 347,725], Wilcoxon p=0,133758062, 16 victoires /18 défaites /6 égalités. Valeur −2,672345 %, garde−5 % tenue. `gain_short`, seuil+4 %, bootstrap20 000/graine0 : **`fail_primary`**. Ni gain ni perte significative établis, aucune B ; caractère exploratoire sans qualification automatique de l'exposition. [JSON original](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_engine_realization_exploration.json), [bilan](resultats_retests_c121_nuit_20261004.md).

L'ancien signal5×6 de gap AAA ne démontrait pas un effet causal du choix moteur, celui-ci restant presque identique. Le retrait relève d'une décision de simplification ; aucun ancien résultat n'est requalifié.

## Périmètre

- Déclaration, globale et chargement supprimés.
- Helper exclusif `OpexC121EngineDecisionRealizationFactor` et correction revenue/profit/capital/score du devis moteur retirés.
- Borne supérieure `OpexC121InitialEngineUpperScore` simplifiée : revenu physique entier utilisé directement, suppression du facteur exclusif et de l'intermédiaire redondant.
- Learner partagé par bras, observations, caches de réalisation et `c121_air_project_realization_adaptive=1` préservés. Aucun champ Save/Load ni schéma modifié ; les facteurs partagés restent reconstruits depuis les lignes.
- Assertions exclusives retirées ; délimiteurs des tests réalisation/C122 et liste des calculs de borne V96 adaptés. L'ancien module de bras live perd seulement l'override explicite du réglage supprimé ; son consommateur shadow K_pass est conservé.

Retraits précédents K_pass/K_dec et travaux parallèles AC/CD préservés. Aucun gain économique/opcodes ni identité de trajectoire revendiqués : enlever du code et des appels peut modifier la cadence du scheduler.

## Validation

**83 contrats verts** : économie C12152, C12211, shortcut V96 5, game-engine7, replay2, cohérence cache6. Recherche sans occurrence résiduelle du réglage, globale, helper ou champ exclusifs dans le code NoAI, les tests et les pilotes courants. `git diff --check` sans erreur.

Smoke `cleanup_engine_realization_smoke_20261012_r1`, défauts chargés, graine42 ×1 an, un duel contre AAAHogEx : complet/sain, deux compagnies `run_ok=true` et `horizon_complete=true`, aucun fatal non attribué. Contexte `desktop-linux`, daemon libre avant lancement, cache `openttd-lab-home`, 10 CPU/8 Go/swap8 Go/10 workers. Image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`. Arbre `a09a7b2` avec changements locaux, bundle `a6c29c380bcf458561c2bfe72699239a4cb13f8cb758c66f9f8cf9e30318a6f0`, manifeste `9cf0d275e478bf6bafcc1e40e0aa8efdfcc58ff1dd7ec26f9ec1b8e98894b4b8`. Le manifeste conserve réalisation projet adaptative et AC04-A v3 à1.

[JSON smoke](../results/cleanup_engine_realization_smoke_20261012_r1.json), [manifeste](../results/cleanup_engine_realization_smoke_20261012_r1.manifest.json). Validation compilation/exécution uniquement ; le duel ne mesure pas un effet causal avant/après ni une rentabilité qualifiée du retrait. Aucun commit ni push.
