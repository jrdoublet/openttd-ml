# Retrait de c121_kdec_cold_exempt

Décision utilisateur du 12/10/2026 : supprimer le paramètre et nettoyer. Aucun commit ni push demandé.

## Historique conservé

La porte A `c121_nuit10_20261003_210612_kdec_cold_exempt_A`, référence isolée `a848df8`, compare ON−OFF sur 40 graines ×3 ans, chaque bras contre AAAHogEx en carte partagée, C121 economics/catalogue à 1. 40/40 paires complètes/saines, échantillon et métriques complets. Profit annuel terminal moyen −9 131,475 £/an (−0,638459 %), médiane −1 263, IC95 bootstrap [−18 088,1 ; −294,175], Wilcoxon p=0,049769386, 12 victoires /20 défaites /8 égalités. Valeur −0,769228 %, garde −5 % tenue. `gain_short`, seuil +4 %, bootstrap 20 000 rééchantillonnages/graine0 : **`fail_primary`**, aucune B. Perte statistiquement étayée dans ce profil ; ce résultat ne mesure pas le nettoyage courant.

[JSON original](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_kdec_cold_exempt_A.json), [bilan de la série](resultats_retests_c121_nuit_20261004.md). Le 20×10 historique du 02/10 (+22,4 k£/an, IC95 Student [−63,2 ; +108,0] k£, `fail_primary` sous `signs20`) est conservé séparément et n'est pas requalifié.

## Périmètre

- Déclaration, globale et chargement retirés, ainsi que la condition exclusive dans `OpexC121ProjectHasRealization`.
- Argument `requireObservedMarginal` devenu sans effet supprimé. Les quatre appels C70/C82 utilisent la signature simple ; leur ancien chemin `false` demeure le comportement de la fonction, fondé sur la présence de `c121MarginalProfit/Revenue` pour les flottes. Branche AIR et gardes de calibration conservées.
- Shadow K_dec, décodeur et compteurs `c121MarginalSamples` conservés ; aucun champ Save/Load ni schéma modifié.
- Test exclusif du toggle retiré. Contrats partagés économie, calibration et réalisation directe adaptés à la signature.
- Fixture VM conservée pour comparer le chemin restant aux helpers historiques `c68d50a` : 16 combinaisons sample/présence/marge, requête de réalisation et numérateurs C70/C82, plus AIR/null/C121 désactivé. Pilote adapté aux seuls réglages encore déclarés. Les 138 assertions de l'ancienne fixture restent un résultat historique distinct des 53 assertions de la nouvelle version.

Ancien test, pilote et fixture sauvegardés avec SHA256 vérifiés avant nettoyage : `results/cleanup_kdec_contracts_backup_20261012/manifest.json`. Les preuves économiques et copies figées sont conservées. Travaux parallèles AC/CD et précédent retrait K_pass préservés. Aucun gain économique/opcodes revendiqué.

## Validation finale

**100 contrats verts** : économie C12152, calibration flotte R2 6, réalisation directe AIR4, shadow/décodeur23, causalité portefeuille B6 7, flotte partielle R1 8. Recherche sans référence résiduelle au réglage, globale, argument supprimé ou ancien appel à deux arguments dans le code courant, les tests et les pilotes. `git diff --check` sans erreur.

**Blocage sandbox levé par l'utilisateur le 12/10, validations moteur terminées.** Contexte `desktop-linux`, daemon libre, image exacte et cache vérifiés avant exécution. Les commandes utilisent 10 CPU/8 Go/swap8 Go, cache `openttd-lab-home` et montage du dépôt à `/work`. Image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.

Smoke commun K_pass/K_dec `cleanup_kpass_kdec_defaults_smoke_20261012_r1`, graine42 ×1 an, défauts chargés : un duel complet/sain, aucune erreur NoAI, deux compagnies `run_ok=true` et `horizon_complete=true`. Code figé sur `a09a7b2` avec changements locaux ; bundle `b933b7033840706114d8fe26f50f45ed18c3732d6ba069fb6a7dd638bc07c803`. Le manifeste confirme l'absence des deux réglages retirés, shadow OFF, AC04-A v3 à1. [JSON](../results/cleanup_kpass_kdec_defaults_smoke_20261012_r1.json), [manifeste](../results/cleanup_kpass_kdec_defaults_smoke_20261012_r1.manifest.json). Aucune attribution économique au nettoyage ni requalification des AC.

Fixture `results/c121_kdec_cold_contracts/cleanup_20261012_r2` : **53/53 assertions VM réussies**, un an/graine42, intégrité mensuelle et santé moteur valides, aucun échec d'assertion. Sources et copie inchangées pendant l'exécution. Le fichier témoin `results/c121_kdec_cold_legacy_c68d50a.nut` est identique au `projects_models.nut` de `c68d50a` après normalisation des fins de ligne ; SHA256 `4246d8d006992af2a363b9a5c5e7643b687fb2d82063f11ffb2daee3a8c3d761`. [Rapport](../results/c121_kdec_cold_contracts/cleanup_20261012_r2/report.json), [plan et hashes](../results/c121_kdec_cold_contracts/cleanup_20261012_r2/plan.json). La tentative r1 a été refusée avant toute partie parce que le dossier de sortie n'était pas un enfant du dossier autorisé ; r2 corrige uniquement ce chemin.

Validation technique terminée, aucun commit ni push demandé ou effectué. Save/Load inchangé ; cette fixture n'est pas un round-trip de persistance.
