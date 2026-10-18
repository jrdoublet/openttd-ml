# V258dead — référence N2, 20 graines × 10 ans (18 octobre 2026)

## Protocole

- Branche `v258dead`, commit exécuté `10111a2e` ; état Git du banc : `dirty=0`.
- Campagne : `v258dead_n2_20x10_pc_20261018` ; gel de sources `ece581cd76e7175cced3f0643da919130b73feca1e44f19d8c5d49f849c4d11c`.
- `OpexAI[opex_difficulty=2]` contre `AAAHogEx-115`, duel en carte partagée ; 20 graines fixées, 10 ans (1970–1979), 1 répétition, 10 workers, 10 CPU et 8 Go, Docker `openttd-lab:latest`.
- Graines : 42, 100, 7, 999, 2026, 1, 17, 73, 314, 512, 1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309.
- Exécution : **20/20 parties complètes, aucun échec**. Un seul Docker à la fois.

## Résultats après 10 ans

| Mesure (moyenne sur 20 graines) | OpexAI | AAAHogEx |
|---|---:|---:|
| Profit annuel | 3 609 917 £ | 7 781 889 £ |
| Valeur d'entreprise | 19 062 517 £ | 28 565 827 £ |
| Score | 887 | 895 |
| Véhicules | 158,2 | 297,2 |
| Gares | 78,8 | 182,3 |

- Profit OpexAI / AAAHogEx (rapport des moyennes) : **46,39 %**, déficit de 53,61 % ; OpexAI gagne 0/20 graines sur le profit.
- Valeur OpexAI / AAAHogEx : **66,73 %**, déficit de 33,27 % ; OpexAI gagne 0/20 graines sur la valeur.
- Ce banc mesure le niveau absolu N2 de cette branche, **pas un effet causal d'une variante**.

## Artefacts

- `results/v258dead_n2_20x10_pc_20261018.json` : résultats structurés des 20 parties.
- `results/v258dead_n2_20x10_pc_20261018.manifest.json` : paramètres et provenance, SHA-256 `8bed508c4d65b623643063757bd8a1237069caf666ac81fcda91a1c83c32c07b`.
- `results/v258dead_n2_20x10_pc_20261018.jsonl.gz` : télémétrie JSONL compressée, décompression vérifiée ; SHA-256 du contenu décompressé : `bc55d9d1e499a7b6b421af8bb85d2795830649768379d02f19cd5b04d61d439b`.
- Les fichiers `.jsonl` non compressés et les logs moteur restent localement hors Git.
