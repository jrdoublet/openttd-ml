# V263 — résultats PC du 19 octobre 2026

Archive des deux campagnes C66.3 N2 **20 graines × 10 ans** et de leurs smokes.
Le [rapport](../../../docs/qualification_v263_n2_cross_tree_20x10_pc_20261019.md)
conserve les résultats et leurs limites : **comparaison descriptive, qualification non établie**.
La publication de ces preuves ne modifie aucun défaut et ne vaut pas adoption.

| Campagne | Git exécuté | Duels sains | Checkpoints JSONL |
|---|---|---:|---:|
| `v263_master_n2_20x10_pc_20261019` | `1b76124233869bc2050389f3b000ac7e63ffd509` | 20/20 | 4 800 |
| `v263_branch_n2_20x10_pc_20261019` | `8dbf8c136a706a30cd5cb8406232851ce0a1f59c` | 20/20 | 4 800 |
| `v263_master_n2_20x10_pc_20261019_smoke` | `1b76124233869bc2050389f3b000ac7e63ffd509` | 1/1 | 26 |
| `v263_branch_n2_20x10_pc_20261019_smoke` | `8dbf8c136a706a30cd5cb8406232851ce0a1f59c` | 1/1 | 26 |

Les campagnes complètes atteignent décembre 1979 ; leurs profits terminaux couvrent
quatre trimestres valides. Les smokes (graine 1024) comprennent 13 relevés par compagnie,
de janvier 1970 à janvier 1971 ; leur couverture annuelle reste `partial`, comme prévu
pour cette vérification d'exécution. Les JSONL n'ont aucun doublon de compagnie/graine/date.

Le delta moyen de profit annuel OpexAI **V263 − master = +48 883,05 £/an (+1,34 %)**
reste descriptif. Le comparateur refuse les différences de réglages : `v178`/`v179`
valent 1 sur master et 0 sur V263 ; `v252`, `v257`, `v259`, `v264` sont absents du
manifeste V263. Aucun verdict causal de neutralité ni gain d'opcodes n'est établi.

## Contenu et provenance

Les **54 archives gzip déterministes** contiennent les 12 fichiers JSON/JSONL/manifeste
des quatre campagnes et leurs 42 journaux moteur. Taille compressée totale :
**6 254 917 octets**. Les 40 journaux des campagnes complètes sont vides
(`script_debug=false`) ; seuls les deux journaux des smokes contiennent des traces.
La santé rapportée provient des résultats du harnais, avec vérification de leur
complétude et de leur cohérence avec les checkpoints.

[index.json](index.json) conserve, pour chaque fichier, le chemin `results/` d'origine,
le worktree source, les tailles et les SHA-256 brut/compressé. Les originaux sont
inchangés : master dans `../v263-master-tree/results/`, variante dans `results/`
du checkout de lancement. L'index global historique `evidence/review/index.json`
reste inchangé.

Les **quatre bundles locaux** ont été vérifiés intégralement contre leur manifeste
avant archivage (114 fichiers pour chacun des deux bundles master, 111 pour chacun
des deux bundles V263). Les manifestes et leurs empreintes sont archivés ici ; les
bundles complets, dont le code tiers AAAHogEx et les bibliothèques, restent locaux.
Cette archive de résultats n'est donc pas un paquet autonome permettant de relancer
le moteur sans récupérer ces dépendances.

## Vérification sans moteur

Depuis la racine du dépôt :

```text
python -X utf8 evidence/review/v263_pc_20261019/verify.py
```

Le vérificateur contrôle les 54 archives après décompression, les liens résultat/manifeste,
la santé et l'horizon des 42 duels, l'unicité des **9 652 checkpoints**, la cohérence
des métriques terminales et les différences de réglages qui bloquent la qualification.
Il ne lance aucune partie et ne transforme pas ces résultats en preuve d'adoption.
