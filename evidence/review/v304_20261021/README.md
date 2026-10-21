# V304 — diagnostic local du 21/10/2026

Voir docs/v304_segmentation_memoire_20261021.md pour le protocole et les limites.
Les JSON finaux et manifestes sont conservés intégralement en gzip déterministe.
Les fichiers *.v304.log.gz sont des extraits : lignes Opex [0] contenant V304_
ou une erreur de script. Ils ne prouvent pas seuls toute la santé moteur.
Les JSON finaux portent les contrôles du harnais.
Les *_segments.json sont produits par sweeps/diag_v304_segments.py.
L'index local préserve les hashes des journaux complets d'origine, des extraits
décompressés et des archives. Les bundles et journaux complets restent locaux.
Aucune qualification ni adoption : verdict 3×10 diagnostic_only.
