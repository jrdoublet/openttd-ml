# Retrait de c121_kpass_air_continue

Décision utilisateur du 12/10/2026 : supprimer le paramètre et nettoyer le code. Aucun commit ni push demandé pour cette étape.

## Historique conservé

La porte A `c121_nuit10_20261003_210612_kpass_air_continue_A`, référence isolée `a848df8`, compare ON−OFF sur 40 graines ×3 ans, chaque bras contre AAAHogEx en carte partagée, C121 economics/catalogue à 1. Elle est complète et saine, avec 40/40 paires, échantillon et couverture complets. Profit annuel terminal moyen +1 693,175 £/an (+0,118392 %), médiane 0, IC95 bootstrap [−3 547,525 ; +6 841,7], Wilcoxon p=0,243896484375, 9 victoires /4 défaites /27 égalités. Valeur +0,123702 %, garde −5 % tenue. `gain_short`, seuil +4 %, bootstrap 20 000 rééchantillonnages/graine0 : **`fail_primary`**, aucune B. Gain requis non démontré ; ni perte significative ni neutralité démontrée.

[JSON original](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_kpass_air_continue_A.json), [bilan de la série](resultats_retests_c121_nuit_20261004.md). Le 5×6 antérieur à +42,2 k£/an demeure diagnostique. Ces résultats ne mesurent pas le retrait sur le code courant.

## Périmètre du nettoyage

- Déclaration, globale et chargement du réglage supprimés.
- Helper exclusif `OpexC121KPassFundableAirAhead`, recherche de l'AIR suivant et branche `continue` retirés de `task_projects.nut`.
- Sonde `c121_kpass_shadow` et `OpexC121KPassShadow` conservées, avec leur aperçu des cinq rangs suivants. Le calcul du capital disponible appartient désormais à la seule garde shadow. La recherche causale dont le résultat n'était pas consommé par la sonde disparaît.
- Règles C75, bypass et arrêt normal de passe conservés. Aucun champ Save/Load ni schéma modifié.
- Trois contrats exclusifs retirés ; contrat de passivité du shadow étendu au site d'appel jusqu'au `break`.
- Deux anciens lanceurs exclusifs 2×3/5×6 retirés, sans consommateur Python identifié. Copies intégrales et SHA256 vérifiés avant suppression dans `results/cleanup_kpass_launchers_backup_20261012/manifest.json`. Rapports et preuves historiques conservés. Le décodeur générique `run_c121_night_queue.py` conserve la reconnaissance des anciennes traces pour les résultats/copies historiques.

Les modifications parallèles AC04/CD et leurs réglages sont préservés. Aucun gain économique ou d'opcodes revendiqué.

## Validation et suite technique

**72 contrats verts** : économie C121 52, investissement 3, cohérence cache 6, bypass C75 11. Recherche sans occurrence du paramètre, globale ou helper retirés dans le code NoAI courant. `git diff --check` sans erreur.

**Validation moteur terminée après ouverture de l'accès complet le 12/10.** Le refus initial venait du sandbox ; contexte `desktop-linux`, daemon libre, image et cache vérifiés avant lancement.

Smoke commun K_pass/K_dec `cleanup_kpass_kdec_defaults_smoke_20261012_r1`, défauts chargés, graine42 ×1 an : un duel complet/sain contre AAAHogEx, deux compagnies `run_ok=true` et `horizon_complete=true`, aucune erreur non attribuée. Arbre `a09a7b2` avec les retraits locaux et travaux AC courants, bundle `b933b7033840706114d8fe26f50f45ed18c3732d6ba069fb6a7dd638bc07c803`, manifeste `e370d103de9617f5413f762e79807e292c63348ccff2ef63506396e882fb40fa`. Image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, 10 CPU/8 Go/swap8 Go/10 workers, cache `openttd-lab-home`. [JSON](../results/cleanup_kpass_kdec_defaults_smoke_20261012_r1.json), [manifeste](../results/cleanup_kpass_kdec_defaults_smoke_20261012_r1.manifest.json). Validation technique du code livré localement, aucun effet économique causal du retrait mesuré. Aucun commit ni push.
