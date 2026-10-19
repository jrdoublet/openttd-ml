# V268 : 3 ans, 5 ans et porte B exploratoire — 19 octobre 2026

Provenance : branche `v268`, source du banc `ebbe92e9`, bundle commun `663097c5a4575a9a87a495fa0e8c759f7a7e4eb68466a1869195fe38127be3eb`. Même code et mêmes 40 graines (73 remplacée par 373684), en partie complète : `OpexAI[v268_c70_early=0]` contre `OpexAI[v268_c70_early=2]` avec AAAHogEx dans chaque duel. Campagnes 40/40 paires, 80/80 parties complètes et saines, 0 échec.

| Mesure de variante moins référence | 40×3 (1972) | 40×5 (1974) |
|---|---:|---:|
| Profit/an moyen | +45 608,55 £ | +59 344,975 £ |
| Delta médian | +41 672 £ | +65 766,5 £ |
| Victoires / défaites | 22 / 18 | 25 / 15 |
| Wilcoxon exact | p=0,25914 | p=0,149902 |
| IC95 bootstrap | [−26 802,775 ; +118 086,85] £ | [−34 530,175 ; +150 481,5] £ |
| Gain relatif / seuil 4 % | +2,17 % / +83 958 £ | +2,3501 % / +101 009 £ |
| Valeur compagnie, ratio des moyennes | +3,65945 % | +2,473201 % |
| Verdict | `fail_primary` | `fail_primary` |

Sur cinq ans : OpexAI référence 2 525 229,85 £/an, variante 2 584 574,825 £/an ; AAAHogEx du bras variante 3 121 749,525 £/an. Ni gain utile démontré, ni qualification. Valeur protégée. Le mode 2 reste OFF. Le banc 5 ans réutilise le même panel après l'échec à 3 ans, donc l'extension est exploratoire.

L'hypothèse d'une activation quasi nulle sur 3 ans n'est pas vérifiable dans les logs de ces bancs : `decision_log=1` n'était pas actif. L'usage des profits précoces par C70 exige notamment une ligne de moins de deux ans, une estimation/prédiction valide et au moins 180 jours d'observation d'un véhicule. Absence de trace ne signifie pas absence d'activation.

## Porte B commandée par dérogation

Malgré les échecs A, demande expresse de réaliser B dès que Docker est libre : 20×10, `non_erosion`, garde de valeur −5 %, 10 CPU / 8 Go / 10 workers, un seul conteneur. Les 20 graines canoniques sont les 20 premières de A (pas un holdout indépendant), 73 remplacée par 373684. Campagne `v268m2_porteB_20x10_pc_20261019`. Les deux bras ajoutent `decision_log=1` pour compter `V268_C70` et `V268_EST` et investiguer l'exposition : ce paramètre peut ajouter un coût d'opcodes par rapport à A. Script `sweeps/run_v268_porteB_pc.sh`. Les résultats B devront être considérés exploratoires, sans adoption automatique.

Archives publiées : JSON terminaux et manifests A40×3 (+smoke) et extension 40×5. Journaux moteur et JSONL volumineux conservés localement uniquement.

## R?sultat porte B 20?10 (fin 1979) ? ex?cut?e le 19 octobre 2026

Campagne `v268m2_porteB_20x10_pc_20261019` : 20/20 paires compl?tes (40/40 parties), `failed_runs=0`, source bundle `b417b8e607fbaee655d54fff70dccd17c25ee36380c9b9c390ce30116fe30d70`, manifeste `faba2932d066034588c5ca320858f6379df8206b4b9d2d9250d8c8a175c8cdd4`. JSON terminal cr?? le **19/10 ? 18:18:57, heure de Paris**.

| Mesure B, variante moins r?f?rence | R?sultat |
|---|---:|
| Profit annuel OpexAI r?f?rence | 3 717 409,75 ?/an |
| Profit annuel OpexAI mode 2 | 3 672 932,95 ?/an |
| Delta moyen `profit_year` | **?44 476,80 ?/an (?1,1964 %)** |
| Delta m?dian, victoires/d?faites | +14 726 ?/an ; **11/9** |
| Wilcoxon bilat?ral | **p = 0,756166** |
| IC95 bootstrap moyen (20 000 r??chantillonnages) | [?226 662,25 ; +136 893,35] ?/an |
| Valeur d'entreprise : ratio des moyennes | **?2,621713 %** |
| Verdict `non_erosion` | **`pass`** (`primary_pass=true`, `value_guard_pass=true`) |

La porte B **passe le crit?re de non-?rosion**, car la borne sup?rieure de l'IC95 bootstrap est positive et la garde de valeur ? ?5 % tient. Elle **ne d?montre pas de gain ?conomique**, avec une moyenne l?g?rement n?gative et un IC95 englobant z?ro. Les deux portes A (`gain_short`) ont ?chou? : le m?canisme n'est **pas qualifi? pour adoption**, reste d?sactiv? par d?faut, et aucune fusion n'est d?cid?e ici. B est une d?rogation exploratoire, sur des graines r?utilis?es et avec le journal d?cisionnel activ? dans les deux bras ; son bundle diff?re de ceux de A.

### Exposition mesur?e dans les journaux moteur de B

Comptage des occurrences de `V268_C70` et `V268_EST` dans les **20 journaux `v268_c70_early_seed*_r0.log`** (bras mode 2), sans traiter les logs AAA comme des activations OpexAI :

- `V268_C70` : **817 ?v?nements, 20/20 graines touch?es** ; 1971 : 76, 1972 : 255, 1973 : 209, 1974 : 162, 1975 : 40, 1976 : 24, 1977 : 24, 1978 : 15, 1979 : 12.
- **331 ?v?nements entre 1971 et fin 1972**, soit pendant les trois premi?res ann?es ; l'hypoth?se d'une activation *quasi nulle* ? 3 ans n'est pas ?tay?e par ces traces, sans garantir la m?me fr?quence dans les 40 graines de A.
- R?partition des ?v?nements C70 : **AIR 602, RAIL 215** ; `V268_EST` : **17 163 ?v?nements** (paliers de 3, 6, 12 et 24 mois, plusieurs v?hicules).
- Les logs du bras r?f?rence n'ont pas d'?v?nement V268, conform?ment ? son mode 0.

**Limite causale** : une publication C70 ou une estimation ne prouve pas une modification du classement, une s?lection diff?rente ni un investissement construit. Les journaux moteur et JSONL complets (volumineux, g?n?r?s localement) ne sont pas commit?s ; conserver la synth?se des ?v?nements avec le JSON et le manifeste B pour audit.
