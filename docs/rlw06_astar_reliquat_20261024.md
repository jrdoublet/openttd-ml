# RLW-06 — A* au reliquat d'opcodes (24 octobre 2026)

**Verdict : non qualifié.** La sonde OFF par défaut a été implémentée et testée en OpenTTD, mais le banc final 3 graines × 3 ans ne contient aucun plan prêt. La chaîne complète paire → A* → plan stocké → réutilisation shadow n'est donc pas démontrée. Aucun commit ni push.

## Portage et périmètre

Base master **eec5db81**, worktree **.worktrees/rlw06**. Portage de RLW-04b depuis **.worktrees/rlw04b**, anciennement basé sur c03fce93, en préservant R01–R12. Témoin propre **.worktrees/rlw06_reference** sur eec5db81. La sonde RLW-04b demeure bit24 (= 16 777 216) ; RLW-06 utilise **probes bit25 (= 33 554 432)**, qui active automatiquement l'énumérateur. ON = **probes 33554434**, OFF = **probes 2**. Aucun AddSetting ni changement de défaut.

Le nouveau module **ai/OpexAI/rail_long_window_astar.nut** classe au plus 24 paires provisoires par production mensuelle source × revenu unitaire lent du cargo, sans grille Squirrel, puis crée un candidat purement shadow. Ses étapes économiques, recherches de sites (une base par tranche, commandes de station seulement sous AITestMode), initialisation, A* reprenable et finalisation de voie simple sont instrumentées. Le budget d'opcodes restants est revérifié à chaque expansion native ; un seul job RLW-06 peut être en vol. La priorité va au fonctionnement normal de l'orchestrateur, puis aux transactions, recherches et tâches AIR finançables ; le shadow ne construit ni station, ni rail, ni véhicule. Les plans réussis seraient stockés dans un dictionnaire privé expirant après 365 jours, avec une lecture fictive unique pour vérifier la réutilisation ; ce comportement n'a pas eu d'exposition effective dans le panel.

Les points d'entrée dans **main.nut** et **probes.nut** sont après la tranche du moteur de production et avant Sleep(1). Le contrôle conditionnel reste commun avec RLW-04b afin de minimiser le chemin OFF. Aucun état RLW-06 n'est persisté ni injecté dans les projets ou le stock C80.

## Harnais et validation

Harnais **sweeps/run_c66_reference.py**, adversaire AAAHogEx-115 identique, début 1970, carte partagée, une répétition. Image Docker **openttd-lab:latest**, sha256 f4b2b9b3b7399cbfecacfe03b8dda49bff2921de36a61fed4e9441e5d44659 ; un seul Docker à la fois ; 4 à 6 CPU, 3 workers et 8 Go au maximum. Les bancs ON ont l'option **--script-debug**, sans laquelle les journaux RLW du moteur restent vides.

Contrats RLW et V261/V262 : **85 tests réussis**, dont **2 échecs attendus** ; contrôles statiques du bit OFF, des deux boucles, du stock privé, des commandes sous AITestMode. **git diff --check** passe.

| Banc | Carte | Graines × années | Santé | Remarques |
|---|---|---|---|---|
| rlw06_on256_wrapper_20261024 | 256² | 42 × 1 | complete | 18 paires RLW-04b ; aucune preuve READY |
| rlw06_on1024_wrapper_20261024 | 1024² | 42 × 1 | complete | 1 A* démarré, 43 expansions, 127 819 opcodes, 1 tick franchi, zéro READY |
| rlw06_on1024_3x3_wrapper_20261024 | 1024² | 42, 100, 999 × 3 | 3/3 complete | 4 paires admises, 3 A*, zéro READY / REUSE |
| rlw06_reference256_20261024 et rlw06_off256_20261024 | 256² | 42 × 1 | 2/2 complete | OFF identique au témoin, y compris adversaire |
| rlw06_reference1024_20261024 et rlw06_off1024_20261024 | 1024² | 42 × 1 | 2/2 complete | OpexAI identique, mais 1 véhicule et 1 gare d'écart chez l'adversaire ; comparaison intégrale échouée |
| rlw06_off1024_wrapper_20261024 | 1024² | 42 × 1 | complete | Dernier OFF : compteurs terminaux des deux compagnies alignés sur le témoin ; écarts de checkpoints persistants |
| rlw06_off256_wrapper_20261024 | 256² | 42 × 1 | complete | Dernier OFF : **26/26 checkpoints identiques** au témoin hors métadonnées de campagne |

Sur 256² OFF et référence ont chacun **426 161 £/an de profit OpexAI**, **390 284 £ de valeur**, **18 véhicules**, **18 gares**, mêmes scores et chiffres adverses. Le dernier OFF sur le bundle final est **identique aux 26 checkpoints** hors métadonnées de campagne. Sur 1024², OpexAI reste à **23 647 £/an**, valeur **1 £**, **5 véhicules** et **8 gares** des deux côtés, mais AAAHogEx finit à **11 véhicules / 13 gares** dans le témoin contre **10 / 14** dans le premier OFF. La garde RLW-06 a donc été réintégrée dans le même branchement que RLW-04b. Avec ce dernier bundle, AAAHogEx retrouve ses **11 véhicules / 13 gares** terminaux. **Cependant, l'égalité stricte des 26 checkpoints échoue encore : 5 écarts de trésorerie, 1 de note médiane des gares, ainsi que des compteurs secondaires.** Neutralité des bilans terminaux observée ; **identité de trajectoire 1024² non prouvée**.

## Exposition mesurée sur 1024²

Le tableau suivant concerne exactement la campagne **rlw06_on1024_3x3_wrapper_20261024**, bundle **c700a994e01da95d589b7f2404abea38adffecb44010fbaa46f37852956a2a05**. C'est aussi le bundle du dernier smoke OFF 1024². Les compteurs proviennent du dernier RLW06_SUMMARY par partie (qui peut précéder la fin). Une tranche STEP n'est journalisée qu'occasionnellement en recherche ; les totaux du dernier SUMMARY font foi.

| Graine | Sources RLW-04b | Paires énumérées | Durée scan (jours) | Paires choisies | A* débutés | Expansions | READY / REUSE | RLW-06 opcodes init / A* / total | Ticks traversés |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 751 | 3 136 | 193 | 2 | 2 | 61 | 0 / 0 | 21 981 / 158 462 / 180 443 | 1 |
| 100 | 763 | 3 036 | 255 | 1 | 1 | 109 | 0 / 0 | 12 383 / 197 672 / 210 055 | 0 |
| 999 | 754 | 2 647 | 180 | 1 | 0 | 0 | 0 / 0 | 10 622 / 0 / 10 622 | 0 |
| **Total** | **2 268** | **8 819** | — | **4** | **3** | **170** | **0 / 0** | **44 986 / 356 134 / 401 120** | **1** |

Le nombre de reports de tranche est **1 393 / 1 864 / 1 962** (total **5 219**), pour les graines 42/100/999. Une paire s'est achevée en échec sur 42 ; les autres étaient encore en cours au dernier relevé. Le coût maximal d'un appel RLW-06 était **12 412 / 6 956 / 4 022 opcodes** par graine ; pas de gel moteur, mais **un franchissement d'un tick**.

**Attention à RLW-04b avec bit25 actif :** l'admission assouplie sur le coût de la dernière source achève les trois passes mais franchit des ticks : **23/13/7 dépassements** (43 en tout) et **22/12/7 franchissements** (41 en tout), pour 42/100/999. Ce comportement est incompatible avec le critère strict de zéro dépassement de RLW-04b et ne doit pas être qualifié sans correction. Le portage RLW-04b bit24 seul garde son admission d'origine.

Les résultats économiques ON (profit OpexAI **3 801 546 / 586 740 / 827 983 £/an** sur les graines 42/100/999) sont indicatifs ; l'instrumentation peut modifier le calendrier de simulation. Ils ne constituent pas une qualification de gain économique, et aucun projet n'est construit sur la décision de RLW-06.

## Verdict et points ouverts

**Non adopté** : 0 plan prêt et 0 réutilisation observés, un franchissement de tick dans RLW-06, 43 dépassements pendant l'énumération accélérée bit25 et des divergences secondaires OFF/OFF. Le reliquat après l'orchestrateur est insuffisant pour une recherche longue complète au débit actuel. Pour aller vers RLW-07/09, il faut corriger les dépassements, conserver la priorité au fonctionnement normal, accroître le nombre d'expansions réellement admises puis observer sur les mêmes 3 graines une chaîne effective PAIR → ASTAR → READY → REUSE, avec expiration et absence de doublon. Les défauts et le constructeur restent inchangés.
