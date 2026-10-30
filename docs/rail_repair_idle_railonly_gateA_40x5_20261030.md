# Porte A RAIL seul 40×5 — réparations après six mois sans construire

## Préenregistrement — 30 octobre 2026, avant le calcul

Demande : « Porte à rail seul 40x5 ». Une seule qualification contre le
comportement de référence, non une comparaison RAIL contre AAAHogEx.

- Code figé au départ : `origin/master` `4b70b0e2162e7a00b08181319c14581f6095de74`,
  qui introduit le garde `RAIL_REPAIR_IDLE` sans changer les défauts.
- **Référence :** `OpexAI[mode_air=0,mode_road=0,mode_water=0,mode_rail=1]`.
- **Variante :** exactement ces modes, plus `rail_repair_join_site=1`,
  `rail_repair_v131_focus=1`, `rail_repair_astar_pair=1`,
  `rail_repair_pose_order=1`. Les quatre secours ne sont exécutables
  qu'après six mois calendaires sans nouvelle ligne construite.
- **V233L** `v233l_constructibilite=2` n'est **pas** qualifié dans ce
  paquet, du fait de son duel individuel 1×10 négatif et de l'absence
  de preuve d'OD physique sauvée. Les deux bras restent au défaut 0 ;
  aucun diagnostic V233L mode 1 dans le duel primaire.
- Jeux `SEEDS_40` de `sweeps/bench_v2.py`, 40 graines communes ;
  1970–1974, 256², 1 répétition, OpenTTD 15.3/OpenGFX 7.1,
  inflation OFF ; 80 parties, 40 paires, budget huit workers maximum
  pour 10 CPU/8 Gio RAM ; seulement le rail autorisé.
- Bibliothèques NoAI BaNaNaS figées depuis la campagne rail du 30/10,
  archives et empreintes SHA256 vérifiées **avant** exécution par le
  lanceur `sweeps/run_rail_repair_idle_railonly_40x5_20261030.py`.
- **Mesure primaire :** `profit_year` au dernier cliché de 1974,
  variantes moins référence, en GBP/an, par graine. Une partie avec
  erreur de script ou couverture écourtée ne peut pas être déclarée
  saine. 40 paires saines et complètes obligatoires.
- **Porte `gain_short` :** amélioration moyenne au moins **+4 %**
  de la moyenne de référence ; **Wilcoxon bilatéral p<0,05** ;
  borne inférieure IC95 bootstrap apparié de la différence **>0** ;
  ratio des moyennes `company_value` ≥ **0,95**.
  Si un critère échoue : **NO-GO**, ne pas activer les défauts et ne
  pas lancer de porte B.
- Analyse secondaire descriptive : gains/médianes/victoires, évolution
  annuelle des profits et nombre de trains/gares. La branche de secours
  étant conditionnelle, un résultat global positif ne suffit pas à
  attribuer le gain à une réparation physique sans les traces
  `RAIL_REPAIR_IDLE`/`RAIL_*_REPAIR` et les OD sauvées. Ce banc
  primaire utilise les réglages de journalisation par défaut
  (`probes=2`), pour éviter une perturbation de l'ordonnancement
  par les logs ; une exposition instrumentée éventuelle doit être
  distincte et déclarée descriptive.

Les résultats seront ajoutés après la fin des 80 parties ; les données
brutes (JSON/JSONL) restent sous `results/`, avec hash documenté.
