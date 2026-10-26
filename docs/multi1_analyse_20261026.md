# MULTI-1 — autopsie chiffrée des trois références, 26 octobre 2026

**Statut : étape 1, analyse descriptive sans nouvelle simulation.** Script reproductible :
`python -X utf8 sweeps/analyse_multi1_existing.py --out results/multi1_20261026_existing_analysis.json`
(la sortie locale est déjà produite, ne pas l'écraser ; sinon choisir un autre nom).

## Sources et précautions

- **RAIL seul** : `modal_rail_defaults_master85c88_40x5_20261025.{json,jsonl,manifest.json}` ; **AIR seul** : même préfixe avec `air`. Ces deux simulations 40×5 utilisent exactement les mêmes 40 graines, commit `85c88c8a`, bundle `0bde1bde…`, 1970–1974, carte 256², mode désactivé pour **les deux IA**, `probes=2` et télémétrie passive des lignes mensuelle.
- **MULTI** : bras **`reference`** de `p6_win_porteA_40x5_20261026.{json,jsonl,manifest.json}` (40 graines × cinq ans, sans P6, `p6_air_firstline_window=0`, `probes=2`, bundle `094e7d15…`). Les 40 graines sont les mêmes que pour les monomodes, mais **le code et le bundle sont différents** ; cette série sert à l'autopsie modale, **pas à une estimation causale inter-campagnes**. Les autres bras P6 ne sont pas inclus. Un témoin multimodal daté du 25/10, `nuit75_multicargo_porteA_40x5_20261025` bras `reference`, donne **2 809 235 £/an Opex contre 3 055 470 £/an AAA, soit 91,94 %** (autre bundle `ae6b948c…`, journaux JSONL et logs moteur absents localement). Le bras P6 témoin donne **92,67 %**.
- Le **≈56 %** du brief correspond au **décrochage à dix ans**, notamment au contrôle 1970–1979 décrit dans `docs/taches.md` (ancienne baseline 20×10 **56,5519 %**, puis contrôle multicargo **58,9786 % OFF** et **58,4889 % ON**). Il ne faut pas attribuer ce ratio aux campagnes **40×5** : l'écart à 75 % est observé **tardivement**, non à fin 1974. À cinq ans, les moyennes multimodales dépassent déjà 75 %.
- Les `primary_vehicles_by_mode` viennent des véhicules moteurs dédupliqués ; un wagon/rotor n'est pas un véhicule supplémentaire. `profit_year` société = jusqu'à quatre trimestres clos à chaque décembre. La valeur comptable des véhicules encore actifs **n'est pas le CAPEX cumulé**, qui n'est pas observé de manière symétrique. Le bras MULTI P6 n'a pas de télémétrie `line_telemetry` : on ne peut y attribuer ni capital réel du rail ni profit par ligne, ni dater directement la **première ligne** ; première apparition de véhicule actif constitue seulement une borne mensuelle.

## 1970–1974 : profits, flottes et adversaire

| Situation, décembre 1974 | OpexAI profit £/an | AAA profit £/an | Opex/AAA | Avions Opex / AAA | Trains Opex / AAA | Route Opex / AAA |
|---|---:|---:|---:|---:|---:|---:|
| RAIL seul | 1 586 931 | 2 049 181 | **77,44 %** | 0 / 0 | 49,83 / 42,33 | 0 / 0 |
| AIR seul | 2 197 271 | 2 014 252 | **109,09 %** | 89,25 / 53,30 | 0 / 0 | 0 / 0 |
| MULTI (P6 OFF) | **2 867 118** | **3 094 032** | **92,67 %** | **84,20 / 41,30** | **27,35 / 27,60** | **4,15 / 147,12** |

| Année | Opex AIR seul | Opex MULTI | AAA AIR seul | AAA MULTI | Ratio Opex/AAA MULTI |
|---|---:|---:|---:|---:|---:|
| 1970 | 344 484 | 348 447 | 380 144 | 313 302 | 111,22 % |
| 1971 | 1 383 650 | 1 453 829 | 1 682 323 | 1 390 268 | 104,57 % |
| 1972 | 1 941 879 | 2 232 271 | 2 093 833 | 1 978 110 | 112,85 % |
| 1973 | 2 051 746 | 2 568 698 | 1 995 844 | 2 569 697 | 99,96 % |
| 1974 | 2 197 271 | 2 867 118 | 2 014 252 | 3 094 032 | 92,67 % |

Fin 1974, le multimodal Opex est **+669 847 £/an** au-dessus d'AIR seul, mais AAA est **+1 079 779 £/an** au-dessus de son AIR seul ; l'écart de progrès concurrent est **≈409 932 £/an**. Comparaison descriptive entre bundles, **non une décomposition causale du déficit**. Contrairement à l'idée d'un effondrement d'Opex par le rail, les deux entreprises progressent en profit absolu. À fin 1972, AAA exploite déjà **107,47 véhicules routiers** en multimodal contre **3,75 chez Opex** ; fin 1974, **147,12 vs 4,15**. La route AAA domine donc la différence modale en volume de véhicules, **sans preuve que la marge marginale d'un véhicule routier AAA ou Opex soit supérieure**.

## Première ligne AIR, financement et pression d'opcodes

En AIR seul, la première **ligne active** Opex est observée en **février 1970 sur 40/40 graines**. En RAIL seul, première ligne rail Opex **février 1970 sur 39/40**, mars sur une, tandis que le premier **véhicule rail** est vu en février pour 40/40. En MULTI, le **premier avion** apparaît en **février 1970 sur 40/40**, avant le premier train Opex en **février 1971 (29/40), mars (6), avril (3), mai (2)**. Le JSONL MULTI n'expose pas d'identité de ligne : ces dates sont des premières présences de véhicules, avec résolution mensuelle. **Aucun train Opex en décembre 1970** : H1 « le rail prend le premier capital AIR dès 1970 » ne correspond pas à cette référence.

| Décembre, moyenne Opex | AIR solo avions | MULTI avions / trains / route | Valeur comptable avions AIR solo / MULTI | Trésorerie AIR solo / MULTI | Prêt AIR solo / MULTI |
|---|---:|---:|---:|---:|---:|
| 1970 | 11,82 | 11,47 / 0 / 0 | 459 449 / 445 753 £ | 62 092 / 67 255 £ | 300 000 / 300 000 £ |
| 1971 | 39,00 | 35,90 / 3,58 / 2,83 | 1 418 628 / 1 317 301 £ | 109 193 / 114 092 £ | 300 000 / 299 500 £ |
| 1972 | 57,40 | 52,90 / 15,53 / 3,75 | 2 336 435 / 2 080 135 £ | 438 388 / 200 307 £ | 146 500 / 201 750 £ |
| 1974 | 89,25 | 84,20 / 27,35 / 4,15 | 3 680 889 / 3 578 951 £ | 1 731 240 / 1 348 123 £ | 12 750 / 26 750 £ |

Sous RAIL seul, la valeur comptable des **véhicules ferroviaires actifs** progresse de **281 700 £ (1970)** à **549 111 £ (1971)**, **888 907 £ (1972)**, **1 111 705 £ (1974)** ; elle ne décrit pas les voies et quais. La valeur comptable rail MULTI **et la part rail du CAPEX investi par année ne sont pas mesurées** : les champs de devis `capital_quote_by_mode` ne représentent ni une dépense effective ni une comptabilité exhaustive. Même limite pour la répartition du capital infrastructure entre les modes et les commandes rejetées.

Les compteurs H5 ci-dessous sont les **opcodes de panneaux conservés au décembre 1974**, moyennes par jeu Opex ; la couverture de CPU est explicitement incomplète (`observed_opcode_complete_cpu=false`). Ce sont des **échantillons de sélection / planification / tentative**, sans total des ticks moteur par mode ni journal exhaustif des allocations :

| Famille de panneaux | RAIL seul (M opcodes / échantillons) | AIR seul | MULTI P6 OFF |
|---|---:|---:|---:|
| Sélection `IG` | 6,785 / 118,20 | 2,370 / 116,62 | 3,154 / 115,35 |
| Tentatives rail `OB` | 61,213 / 53,08 | 0 / 0 | 30,414 / 31,35 |
| Plan AIR `OA` | 0 / 0 | 5,710 / 48,45 | 5,244 / 45,80 |
| Plan route `RB` | 0 / 0 | 0 / 0 | 4,943 / 14,75 |
| Construction route `RB` | 0 / 0 | 0 / 0 | 0,909 / 14,75 |

Le MULTI consacre **30,4 M opcodes observés à des tentatives rail**, contre **5,24 M à des plans AIR**, et **5,85 M à la route**, mais un opcode `OB` de construction peut inclure une recherche A* très coûteuse. Ces valeurs ne permettent pas d'affirmer que 30,4 M ont été pris **à la place** d'une construction AIR qui aurait été finançable. `decision_log` est éteint (`probes=2`), les classements précis par tick sont donc absents. Les 40 journaux de chaque monomode montrent les constructions `C121_BUILD` AIR ; une comparaison exhaustive des tick-IDs entre les trois politiques demanderait un autre instrumenteur et modifierait leur trajet. Le rapport ne prétend pas mesurer ces ticks manquants.

## Verdict des trois hypothèses et direction du premier essai

**H1 (rail prive l'AIR du capital au début) : faible** pour 1970 : tous les mondes MULTI démarrent AIR et aucune locomotive n'apparaît avant 1971. Écart de flotte AIR en 1972 **−4,5 avions** et trésorerie **−238 k£** en MULTI vs AIR solo : compatibilité possible avec une pression de capital à partir de 1971, mais pas de trajectoire même-save, de CAPEX total ou de candidats AIR empêchés ; ne pas déclarer H1 démontrée.

**H2 (opcodes multimodaux) : plausible mais non tranchée.** Sélection `IG` 3,15 M vs 2,37 M solo AIR et tentatives rail 30,4 M ; toutefois le MULTI construit 84 avions et produit davantage de profit privé. Les panneaux H5 ne mesurent ni tout le CPU ni l'écart de délai contrefactuel. Les 40 journaux de chaque mono n'établissent pas la priorité du scheduler MULTI actuel.

**H3 (AAAHogEx beaucoup plus polyvalent en multimodal) : hypothèse dominante observée sur cinq ans.** Le ratio passe de 109,09 % en AIR solo à 92,67 % en MULTI, en présence de la flotte routière AAA **147 vs 4** et d'un avantage multimodal AAA en bénéfice absolu supérieur de ≈410 k£/an. Cela suggère de **tester le goulot de promotion de candidats ROUTE propres et finançables**, avec garde forte pour ne pas sacrifier un AIR productif. Il faut une exposition d'opportunités ROAD *réelles* et un effet sur les véhicules construits ; le nombre de véhicules AAA seul ne mesure pas les profits ou la possibilité d'en capturer les marchés.

**Suite :** pré-enregistrer un unique `multi1_road_priority` OFF/shadow/ON qui ne regarde ni les fonds ni les décisions d'AAAHogEx, conserve C77 AIR défensif, et n'avance une route finançable que si son rendement est voisin de l'alternative courante. Avant toute porte A 40×5, exiger des projets ROUTE effectivement promus et construits sur les cinq graines d'exposition. Déclaration, bornes, Save/Load, contrat OFF, smoke 1×1, puis gate A ; B 20×10 uniquement si A passe. Objectif stratégique à 10 ans distinct des seuils d'adoption du levier.
