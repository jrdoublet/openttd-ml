# C122 priorité par régime — 40×3

[Preuves versionnées](../evidence/review/parameter_cleanup_20261012/README.md). Publication ciblée demandée le12/10 ; les mentions de non-publication ci-dessous décrivent les étapes antérieures.

**Décision ultérieure du12/10 : réglage retiré sur demande utilisateur.** [Nettoyage et validation](c122_regime_priority_retrait_20261012.md). Le protocole et les résultats ci-dessous décrivent l'évaluation antérieure, conservée sans réinterprétation.

Demande utilisateur du 12/10 : évaluer `c122_air_regime_priority` sur 40 graines × 3 ans. Évaluation seulement, défaut 0 conservé ; aucune B, adoption, suppression, commit ou push. Cette demande explicite autorise ce diagnostic malgré l'abandon historique ; les interdictions de nouveau 5×6/20×10 C122 restent applicables.

## Pré-enregistrement

Référence `OpexAI[c122_air_regime_priority=0]`, variante `OpexAI[c122_air_regime_priority=1]`, autres réglages aux défauts communs. Priorité comportementale : après verrou `race`, préférer entre projets AIR de même tier C77 celui qui ouvre une ville Opex non desservie. Classifieur et annotations partagés, aucun état persistant exclusif ; `c121Strategy` conservé.

Sources communes de HEAD `f6139d89f299bcd3d2d24bc32bf22fef6df21d8f` plus le retrait local déjà validé de `c121_air_initial_project_economics`. Copie isolée `results/c122_regime_40x3_20261012_r1_source`, liste des fichiers locaux inclus et hashes dans `preregistered.json`. Modifications de sonde parallèles exclues de la copie, préservées dans le dépôt. Aucun réglage changé pour provoquer l'exposition.

40 graines canoniques : 42,100,7,999,2026,1,17,73,314,512,1024,1337,4096,8191,12345,54321,65537,123456,424242,8675309,423960,613553,515222,781335,375172,999533,442018,746035,455216,230185,706990,983759,802204,232037,723002,313707,701256,292001,841478,59527. Une répétition, 80 duels distincts contre la même AAAHogEx figée, mêmes cartes/places/horizon.

Métrique primaire `profit_year` terminal Opex ON−OFF ; `gain_short`, required_seeds 40, required_years 3, seuil relatif 4 %, Wilcoxon exact bilatéral p<0,05, borne basse IC95 bootstrap moyenne >0 ; garde de valeur −5 % par ratio des moyennes. Bootstrap 20 000, graine 0. Santé, horizon, quatre trimestres terminaux et couverture 40/40 requis.

Contrats ciblés puis smoke causal 42×1 ; contrôle d'exposition 42×3 pour atteindre le verrou après deux années observées. `--script-debug` commun aux deux bras pour lire `C121_STRATEGY_LOCK` et les inversions `C122_PROMOTE`, sans sondes activées. Même collecte des logs prévue dans le 40×3. Sans promotion observée au diagnostic, le 40×3 explicitement demandé reste une comparaison globale du toggle et ne qualifie pas un mécanisme non exposé. Aucun sous-ensemble favorable ni relance pour obtenir un meilleur résultat.

Docker `desktop-linux` libre, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, cache `openttd-lab-home`. PC : 10 CPU/8 Go/swap 8 Go/10 workers, budget 2 heures pour l'ensemble. Campagnes uniques : `c122_regime_smoke_20261012_r1`, `c122_regime_exposure_20261012_r1`, `c122_regime_40x3_20261012_r1`.

## Suivi

80 contrats ciblés verts (C122, économie C121, défense C77, persistance R20). Smoke `c122_regime_smoke_20261012_r1`42×1 : 2/2 duels sains, sources inchangées, seule différence effective C1220→1. Absence de verrou à un an attendue ; delta+1 711 £/an et valeur−5,508 %, hors échantillon d'adoption et sans conclusion économique.

Diagnostic `c122_regime_exposure_20261012_r1`42×3 : 2/2 duels sains, verrou `race` dans les deux bras, **aucune trace `C122_PROMOTE`**. Delta+195 983 £/an et valeur+7,561 %, non interprétés comme effet métier sur une graine sans promotion. Bundle commun `9af5c12c24f659cc2bd4ad3b1190cc40f82ac860b31972a3600136ba6ddb1d96` ; manifests smoke `b1fd754a9ce10fe1f7736664774b9d40fcaad6514bf0774baf5b895d27522aa5`, exposition `cfa8e89823802313711bd3512b6c4683024483cbee7f8da92a0d53ef662c4db2`.

**Portée arrêtée avant le 40×3 :** absence de promotion sur42×3 ; exécuter la demande comme diagnostic global du toggle, sans qualification du mécanisme sur ce préalable. Les traces du40×3 permettront de vérifier son exposition sur les autres graines, sans altérer les bras ni sélectionner un sous-ensemble favorable. Aucun verdict anticipé, aucune B ou adoption automatique.

## Résultat final

Campagne `c122_regime_40x3_20261012_r1` terminée : **80/80 duels sains, 40/40 paires complètes**, aucun failed_run ni erreur non attribuée. `comparison_complete`, `adoption_sample_complete`, `metric_coverage_complete` vrais ; 160 enregistrements terminaux au01/12/1972, chacun avec quatre trimestres disponibles et valides. Sources de la copie inchangées ; seule différence effective du manifeste : `c122_air_regime_priority`0→1. Aucune sonde activée, collecte script-debug commune.

| Indicateur Opex ON−OFF | Résultat |
|---|---:|
| Profit annuel terminal référence moyen | 2 013 038,625 £/an |
| Profit annuel terminal variante moyen | 1 992 994,025 £/an |
| Delta moyen | **−20 044,6 £/an (−0,995738 %)** |
| Médiane du delta | −16 238 £/an |
| IC95 bootstrap de la moyenne | **[−86 843,725 ; +45 174,9] £/an** |
| Wilcoxon exact bilatéral | **p=0,617864972** |
| Victoires/défaites/égalités | **18/22/0** |
| Variation de valeur, ratio des moyennes | **−1,451809 %**, garde−5 % tenue |
| Seuil de gain requis | +80 521,545 £/an (+4 %) |
| Verdict brut | **`fail_primary`** |

Gain utile non démontré ; aucune perte significative ni neutralité/équivalence prouvée. **Défaut0 conservé, aucune B/adoption/suppression/commit/push.** Le résultat s'applique au toggle global au défaut courant, incluant ses effets éventuels de cadence, sans les attribuer exclusivement à la priorité territoriale.

Contrairement au préalable42×3, le mécanisme est exposé dans le40×3 : **13/40 graines ON** émettent des inversions `C122_PROMOTE` : 1,314,512,1024,2026,12345,423960,455216,515222,59527,701256,706990,232037. **104 lignes de promotion**, huit par partie concernée : le plafond de log est atteint, donc au moins104 comparaisons inversées, pas un nombre exact de projets construits ni de décisions finales. Aucune promotion dans les bras OFF. 76/80 parties ont un verrou `race`. Aucun recalcul favorable sur le sous-ensemble exposé ; les statistiques restent celles des40 graines pré-enregistrées.

Bundle commun aux trois étapes `9af5c12c24f659cc2bd4ad3b1190cc40f82ac860b31972a3600136ba6ddb1d96`, manifeste final `65d69cad53644673883724c10b050ff7ae8dc190da529c51cc9e2e9e0831737a`. [JSON final](../results/c122_regime_40x3_20261012_r1_source/results/c122_regime_40x3_20261012_r1.json), [JSONL](../results/c122_regime_40x3_20261012_r1_source/results/c122_regime_40x3_20261012_r1.jsonl), [manifeste](../results/c122_regime_40x3_20261012_r1_source/results/c122_regime_40x3_20261012_r1.manifest.json), [synthèse auditée et exposition par graine](../results/c122_regime_40x3_20261012_r1_source/results/c122_regime_40x3_20261012_r1.summary.json), [deltas par graine](../results/c122_regime_40x3_20261012_r1_source/results/c122_regime_40x3_20261012_r1.per_seed.csv), [plan machine](../results/c122_regime_40x3_20261012_r1_source/preregistered.json). Les preuves historiques rapportées du29/09 restent distinctes et ne sont pas requalifiées.
