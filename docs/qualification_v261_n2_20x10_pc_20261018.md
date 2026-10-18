# V261 — référence N2, 20 graines × 10 ans (18 octobre 2026)

## Protocole

- Branche `v261`, commit exécuté `d83de3d9` ; état Git du banc : `dirty=0`.
- Campagne : `v261_n2_20x10_pc_20261018` ; gel de sources `351e94217e8c612e34cdebec2fe6ca8e9d64e10c7a22ee3e94eb7b870fc52c3b`.
- `OpexAI[opex_difficulty=2]` contre `AAAHogEx-115`, duel en carte partagée ; les mêmes 20 graines, 10 ans (1970–1979), 1 répétition, 10 workers, 10 CPU et 8 Go, Docker `openttd-lab:latest`.
- Graines : 42, 100, 7, 999, 2026, 1, 17, 73, 314, 512, 1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309.
- Exécution : **20/20 parties complètes, aucun échec** ; démarrée après la fin de V258dead, sans Docker concurrent.

## Résultats après 10 ans

| Mesure (moyenne sur 20 graines) | OpexAI | AAAHogEx |
|---|---:|---:|
| Profit annuel | 3 784 726 £ | 7 771 618 £ |
| Valeur d'entreprise | 19 935 694 £ | 28 825 409 £ |
| Score | 891 | 895 |
| Véhicules | 160,3 | 303,1 |
| Gares | 75,7 | 183,5 |

- Profit OpexAI / AAAHogEx (rapport des moyennes) : **48,70 %**, déficit de 51,30 % ; OpexAI gagne 0/20 graines sur le profit.
- Valeur OpexAI / AAAHogEx : **69,16 %**, déficit de 30,84 % ; OpexAI gagne 0/20 graines sur la valeur.

## Lecture comparative (V261 versus V258dead)

- Profit annuel moyen OpexAI : `3 784 726,05 − 3 609 917,40 = +174 808,65 £/an`, soit **+4,84 %**.
- Valeur moyenne OpexAI : `19 935 694,30 − 19 062 517,20 = +873 177,10 £`, soit **+4,58 %**.
- Le profit moyen AAAHogEx diffère aussi entre les bancs (`7 771 617,95` contre `7 781 888,75 £/an`). Malgré les graines identiques, ce sont deux duels indépendants avec adversaire actif ; il ne faut **pas** lire ces écarts comme un essai contrefactuel à monde identique ou une qualification causale de V261.

## Artefacts

- `results/v261_n2_20x10_pc_20261018.json` : résultats structurés des 20 parties.
- `results/v261_n2_20x10_pc_20261018.manifest.json` : paramètres et provenance, SHA-256 `13d39e31ae69ebf96ac944210d43a0fef91ce54fdb0240000f09cb5fa24a7872`.
- `results/v261_n2_20x10_pc_20261018.jsonl.gz` : télémétrie JSONL compressée, décompression vérifiée ; SHA-256 du contenu décompressé : `dcf3c7cbdd46725934fd44ce541ef5c5ac115903309e83f94ff4623b22f4db1e`.
- Les fichiers `.jsonl` non compressés et les logs moteur restent localement hors Git.
