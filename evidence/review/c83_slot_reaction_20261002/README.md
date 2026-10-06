# C83 — suppression de la régénération réactive

Deux campagnes locales du 2 octobre 2026, sur le même bundle figé, SHA
`b2334d7` dirty : smoke apparié 1×1 et diagnostic apparié 5×6,
`OpexAI[c83_slot_reaction=0]` contre `=1`, chacun face à AAAHogEx figée.

**Ablation non retenue :** delta profit moyen −96,9 k£/an, valeur −9,13 %,
garde −5 % échouée. Dix suppressions réelles sur quatre graines ; 42 sans
événement. Aucun 20×10, défaut 1 conservé. Les intervalles de confiance restent
larges : ce diagnostic n'est pas une preuve de perte générale significative.

[Plan et bilan](../../../docs/c83_slot_reaction_20261002.md),
[résumé](summary.json), [index](index.json).

Le paquet réutilise les fonctions gzip déterministe et SHA-256 de
`sweeps/package_review_evidence.py` dans un périmètre dédié. Chaque entrée
d'index conserve le chemin de source, les tailles et SHA-256 bruts/gzip.
Le résumé conserve les empreintes des bundles, manifests, JSONL et logs complets
restés sous `results/`. L'index historique global reste intact.
