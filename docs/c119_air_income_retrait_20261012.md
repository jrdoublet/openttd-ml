# Retrait du traitement autonome c119_air_income_model

**Suite :** commit ciblé et préparation de fusion demandés le12/10 après validation. [Archive versionnée des preuves techniques](../evidence/review/c118_c119_cleanup_20261012/README.md). Les mentions « aucun commit/push » ci-dessous décrivent l'étape de retrait ; aucune qualification économique du cumul avec V157/V158/V160 n'en découle.

Décision utilisateur du 12/10/2026 : « supprime le, on a adopté définitivement c121 ». Retirer le réglage C119 autonome et son code exclusif ; conserver les composants partagés avec C121, les sondes et les travaux P0/AC. Cette décision confirme l'adoption de C121 ; elle ne transforme aucun verdict historique en qualification économique. Aucun commit ni push demandé.

## Historique conservé

Le [rapport C119 du 28/09](42_c119_air_income_model_20260928.md) décrit un traitement préconstruction : distance de paiement Manhattan et temps de livraison séparé du cycle AIR, sans modification des formules de demande/flotte. Le 20×10 contre C115 rapporte +70,9 k£/an, 11 victoires/9 défaites, IC95 Student [−59,6 ; +201,5] k£/an, valeur +4,45 %, verdict brut **fail_primary**. Gain non qualifié, ni perte ni neutralité démontrées. Ce résultat ne mesure pas le retrait sur l'arbre courant.

## Périmètre du retrait

- Déclaration dans `info.nut`, globale et chargement supprimés ; ancien défaut OFF conservé dans l'économie historique.
- Branches exclusives de recettes et dimensions C119 des clés de cache retirées de `OpexAirEconomics`. Les caches restent reconstructibles, avec leurs invalidations existantes.
- Argument `paymentDistance` devenu inutile retiré de l'économie historique et de sa propagation dans les choix moteur C104/C115/C116/V92 et les générateurs newpair/hubsite/hubhub. L'appel de la sonde V95 est adapté sans retirer la sonde.
- `OpexC119AirIncomeDays` **conservé** : cinq sites C121 l'utilisent comme repli quand `air_c121_physical_payment_days=0`. Corps du helper inchangé ; commentaire clarifié. Paiement physique adopté à1 et devis C121 inchangés.
- Aucun champ ni schéma Save/Load modifié. C115 et les autres configurations historiques ne sont pas retirés par cette intervention.
- Contrats adaptés ; analyseurs C119, fixtures API et télémétrie passive conservés. Deux lanceurs exclusifs du traitement supprimé retirés après copie intégrale et vérification SHA-256 : [archive locale et manifeste](../results/cleanup_c119_launchers_backup_20261012/manifest.json). Les anciens rapports/artefacts restent historiques, leurs commandes ne s'appliquent plus au code courant.

## Validation technique

**94 contrats ciblés verts** : `test_c119_air_income_model`, `test_c119_air_income_shadow`, `test_c115_air_c100_capital_replay`, `test_v92_air_service`, `test_air_c121_physical_payment_days`, `test_c121_air_economics`, `test_air0310_3a_v96_shortcut`, `test_air0310_3b_one_two_fused`. Les assertions du traitement retiré sont supprimées ou adaptées ; les contrats du helper partagé, de C115, de V92 et de C121 sont conservés. Les tests Python ne compilent pas Squirrel.

Smoke **`cleanup_c119_defaults_smoke_20261012_r2`**, défauts courants, graine42 ×1 an, un duel OpexAI/AAAHogEx en carte partagée : **1/1 jeu complet et sain**, deux compagnies actives, `run_ok=true`, `horizon_complete=true`, aucune erreur non attribuée ni erreur de script. Dernier snapshot 01/01/1971, trois trimestres valides par compagnie : couverture initiale partielle attendue, pas preuve économique.

Source `master` HEAD `0988bbad0cda87f2335169cbade53c6af6e1ecda`, arbre local dirty incluant les retraits et modifications de sondes préexistantes. Bundle gelé `9e414e5ee6caa41e1ab8bb6bb7202990dc8042f1823c85885d3081907ef2dcfa`, manifeste `6b1a830361f5744b1f789299c9bd364d639a8344aa4b5eb3ca4a7baf895a5fa5`. Docker `desktop-linux`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, 10 CPU/8 Go/swap8 Go/10 workers et cache `openttd-lab-home`. Campagne P0 C117 active au contrôle initial : attente de sa fin, sans interruption, puis daemon libre avant lancement.

[JSON final](../results/cleanup_c119_defaults_smoke_20261012_r2.json), [manifeste](../results/cleanup_c119_defaults_smoke_20261012_r2.manifest.json), [log moteur](../results/cleanup_c119_defaults_smoke_20261012_r2_engine/reference_seed42_r0.log). Audit des défauts figés : `c119_air_income_model` absent ; `c121_air_economics=1`, `c121_catalog_incremental=1`, `air_c121_physical_payment_days=1`. Première tentative r1 refusée par le CLI avant toute partie (`--reference OpexAI` au format incorrect) ; r2 corrige seulement la commande de lancement, aucune relance favorable.

Recherche sans occurrence du réglage/globale retirés dans les sources NoAI et `git diff --check` sans erreur. Les travaux locaux P0 et leur test de sonde restent préservés. Aucune mesure de gain économique/opcodes ou d'identité de trajectoire revendiquée ; aucun A/B, commit ni push.
