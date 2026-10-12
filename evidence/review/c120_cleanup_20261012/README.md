# Preuves techniques du retrait C120

39 artefacts compressés : sauvegardes des sources/lanceurs/contrats avant retrait,
manifest des 27 sauvegardes, script d'édition, audit reproductible, 269 contrats,
audit des smokes, deux JSON/manifestes/logs moteur. Les sources de Save/Load et C121
sont présentes dans les sauvegardes pour vérifier leur identité.

Chaque entrée de [l'index](index.json) enregistre le chemin original, la taille et
le SHA-256 des octets bruts ainsi que du gzip. Compression déterministe issue de
`sweeps/package_review_evidence.py`. Tous les octets ont été vérifiés après
décompression. Le package global historique n'est pas modifié.

Campagnes `cleanup_c120_defaults_smoke_20261012_r1` et
`cleanup_c120_coverage_smoke_20261012_r1`, même bundle `be3ab6b8`, graine 42,
un an, un duel chacune. Compilation/exécution et santé seulement : aucun A/B
économique ni gain/équivalence du retrait. JSONL, sauvegardes et bundles complets
restent dans `results/` ignoré. [Compte rendu](../../../docs/c120_territorial_retrait_20261012.md).
