# C121 initial project economics — 40×5

[Preuves versionnées](../evidence/review/parameter_cleanup_20261012/README.md). Publication ciblée demandée le12/10 ; les mentions de non-publication ci-dessous décrivent les étapes antérieures.

**Décision ultérieure du 12/10 : réglage retiré sur demande utilisateur.** [Périmètre et validation du nettoyage](c121_initial_project_retrait_20261012.md). Le protocole et le résultat brut ci-dessous décrivent l'évaluation antérieure et restent inchangés.

Demande utilisateur du 12/10 : évaluer `c121_air_initial_project_economics` sur40 graines ×5 ans. Évaluation seulement, sans adoption ni suppression, B, commit ou push implicites. Le défaut reste0.

## Pré-enregistrement avant mesure

Intervention comportementale économique : référence `OpexAI[c121_air_initial_project_economics=0]`, variante `OpexAI[c121_air_initial_project_economics=1]`. Sources communes figées à partir de HEAD `f6139d8`, branche master. Modifications locales en cours dans `probes.nut` et tests de sonde exclues de la copie exécutée ; travaux parallèles préservés. Autres réglages aux défauts de cette référence, notamment C121 economics/catalogue=1. Déclarations/chargement et deux sites de construction de projets inspectés ; aucun état Save/Load exclusif.

Copie `results/c121_initial_40x5_20261012_r1_source`, plan machine `preregistered.json` (SHA complet, état original, seeds, paramètres et empreintes NoAI). Docker local `desktop-linux` libre avant préparation, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, cache `openttd-lab-home`, dépôt monté à `/work`. 10 CPU/8 Go/swap8 Go/10 workers ; budget2 heures pour smoke/exposition et mesure. Aucun doublon ni rejeu favorable.

40 graines canoniques : 42,100,7,999,2026,1,17,73,314,512,1024,1337,4096,8191,12345,54321,65537,123456,424242,8675309,423960,613553,515222,781335,375172,999533,442018,746035,455216,230185,706990,983759,802204,232037,723002,313707,701256,292001,841478,59527. Une répétition, 80 duels distincts contre la même AAAHogEx figée. Horizon5 ans décidé avant les résultats ; le précédent40×3 exploratoire reste conservé séparément.

Métrique primaire : profit annuel terminal Opex variante−référence. `gain_short`, required_seeds40/required_years5, seuil relatif4 %, Wilcoxon exact bilatéral p<0,05, borne basse IC95 bootstrap de la moyenne>0 ; garde−5 % du ratio des moyennes de valeur. Bootstrap20 000/graine0. Santé, horizon complet, quatre trimestres terminaux et couverture40/40 paires requis. Aucun critère fondé sur la seule baisse d'AAAHogEx.

Préalables : contrats ciblés, puis smoke causal42×1 avec `probe_c121_engine_table=1` identique dans les deux bras et script-debug. Exposition recherchée dans les plans effectivement générés : économie d'ouverture P/C différente du devis décisionnel, et flag `init` correspondant à chaque bras. La sonde existante peut déplacer la cadence ; ce smoke ne produit pas de conclusion économique. Après santé/exposition établies, campagne `c121_initial_40x5_20261012_r1` avec cette sonde OFF et tous les autres réglages aux défauts. Aucun nouveau code de sonde ajouté, aucune sonde supprimée.

## Suivi

Mesure terminée ; les étapes et limites d'exposition ci-dessous sont conservées.

Contrats62/62 verts. Smoke causal instrumenté `c121_initial_exposure_smoke_20261012_r1`42×1 :2/2 duels sains, delta nul, 358 plans par bras, **aucun devis ouverture/décision différent**. Flags init0/1 vérifiés. Bundle `7215d05fa3c6430df2989a0e414a1892881a13ca8750f0cce8bc61cfaf140e9d`. Aucun effet économique attribué à la sonde.

Avant les résultats suivants, contrôle d'exposition complémentaire arrêté sur la même graine42 jusqu'à l'horizon demandé5 ans, mêmes bras instrumentés et même source, campagne `c121_initial_exposure_1x5_20261012_r1`. Aucune recherche de graine favorable ; il s'agit uniquement de voir si les devis divergent plus tard. Le40×5 propre reste conditionné à cette preuve, sans interprétation économique du diagnostic.

Contrôle1×5 terminé sain : 828 plans référence /852 variante, **0 différence P/C ouverture−décision**. Le chemin courant `OpexC121OneOrTwoWinner`, actif par défaut, retourne le même objet `chosen` dans `initial` et `full`. Delta instrumenté−24 318 £/an, non interprété économiquement ; trajectoires différentes malgré devis identiques, coût/cadence de code ou de sonde non attribué.

**Portée précisée avant le40×5 :** la demande utilisateur est maintenue comme comparaison globale du toggle au défaut, sans sonde, et non comme qualification de l'hypothèse d'économie d'ouverture. L'exposition économique directe initialement recherchée est absente ; aucun autre réglage n'est désactivé pour la créer. Les paramètres/statistiques pré-enregistrés restent identiques et le verdict brut sera conservé, mais un résultat numérique ne qualifie pas ce mécanisme non exposé. Aucune B ni adoption automatique. Le40×5 diagnostique demandé est lancé une seule fois sur40 graines, sans sous-ensemble ni sélection favorable.

## Résultat final

Campagne `c121_initial_40x5_20261012_r1` terminée : **80/80 duels sains,40/40 paires complètes**, aucun failed_run ; `comparison_complete`, `adoption_sample_complete`, `metric_coverage_complete` vrais. Les160 enregistrements de compagnies au01/12/1974 ont chacun quatre trimestres disponibles et valides. Sources NoAI de la copie inchangées par rapport au pré-enregistrement. Manifeste : une seule différence effective, `c121_air_initial_project_economics`0→1, aucune sonde activée.

| Indicateur ON−OFF | Résultat |
|---|---:|
| Profit annuel terminal référence moyen | 2 028 203,775 £/an |
| Profit annuel terminal variante moyen | 2 031 196,975 £/an |
| Delta moyen | **+2 993,2 £/an (+0,147579 %)** |
| Médiane du delta | **0 £/an** |
| IC95 bootstrap de la moyenne | **[−45 732,45 ; +55 222,825] £/an** |
| Wilcoxon exact bilatéral | **p=0,971725702** |
| Victoires/défaites/égalités de profit | **14/13/13** |
| Variation de valeur, ratio des moyennes | **+0,66115 %**, garde−5 % tenue |
| Seuil de gain requis | +81 128,151 £/an (+4 %) |
| Verdict brut | **`fail_primary`** |

Gain requis non démontré, ni gain ni perte significative établis ; neutralité/équivalence non prouvées. Aucun changement de défaut, aucune B, adoption, suppression, commit ou push. Le résultat porte sur le toggle global dans les défauts courants, sans démonstration d'un effet de modèle d'ouverture : sous `c121_air_one_or_two_planes=1`, ouverture et décision reçoivent le même devis. Des trajectoires différentes peuvent provenir de cadence/code, sans attribution opcode mesurée ici.

Bundle commun aux trois étapes `7215d05fa3c6430df2989a0e414a1892881a13ca8750f0cce8bc61cfaf140e9d`, manifeste final `e46b6ba0fd803a660626eaf94fef14154af0a047796a3f6663766cd6705aa8b1`. [JSON final](../results/c121_initial_40x5_20261012_r1_source/results/c121_initial_40x5_20261012_r1.json), [JSONL](../results/c121_initial_40x5_20261012_r1_source/results/c121_initial_40x5_20261012_r1.jsonl), [manifeste](../results/c121_initial_40x5_20261012_r1_source/results/c121_initial_40x5_20261012_r1.manifest.json), [synthèse auditée](../results/c121_initial_40x5_20261012_r1_source/results/c121_initial_40x5_20261012_r1.summary.json), [deltas par graine](../results/c121_initial_40x5_20261012_r1_source/results/c121_initial_40x5_20261012_r1.per_seed.csv), [exposition42×5](../results/c121_initial_40x5_20261012_r1_source/results/c121_initial_exposure_1x5_20261012_r1.exposure.json).
