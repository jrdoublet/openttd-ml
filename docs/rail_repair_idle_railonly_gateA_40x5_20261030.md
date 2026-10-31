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

## Résultats — 80/80 parties saines, NO-GO

Le lanceur a terminé avec un code de sortie 0 : **40/40 paires**, 80
enregistrements finaux `run_ok`, date `1974-12-01`, 60 sauvegardes
mensuelles par partie, couverture `profit_year=complete`, aucun échec
physique ou script, aucun run manquant.

| Mesure finale 1974 | Référence rail seul | Réparations conditionnelles |
|---|---:|---:|
| Profit annuel moyen (`profit_year`) | **1 770 915,975 £/an** | **1 772 915,750 £/an** |
| Valeur de société moyenne | ratio de référence 100 % | **100,9631 %** de référence |
| Trains moyens | 49,15 | 49,45 |
| Gares moyennes | 74,2 | 74,4 |

- **Delta moyen apparié : +1 999,775 £/an (+0,112923 %).**
- Delta médian : **0 £/an** ; **15 victoires, 15 défaites, 10 égalités**.
- Wilcoxon bilatéral **exact p=0,823576944** : échec `p<0,05`.
- IC95 bootstrap percentile apparié, 20 000 rééchantillonnages,
  graine interne 0 : **[−37 210,425 ; +41 626,900] £/an** ;
  borne basse non positive.
- Seuil d'utilité **+4 %**, soit **+70 836,639 £/an** sur le témoin ;
  gain observé ~2 000 £/an, seuil non atteint.
- Garde `company_value` ≥95 % : **passe** à 100,9631 %.
- **Verdict de la porte `gain_short` : `NO_GO`** (3 critères
  primaires échoués sur 4). Pas d'activation des réglages par défaut,
  pas de porte B 20×10.

Évolution du delta annuel moyen (descriptive, clichés de décembre,
les années ne sont pas des observations indépendantes) :

| Année | Delta variante − témoin |
|---|---:|
| 1970 | −301,025 £/an |
| 1971 | +83,525 £/an |
| 1972 | +1 158,925 £/an |
| 1973 | +4 399,675 £/an |
| 1974 | +1 999,775 £/an |

La répartition est **hétérogène** : graine 2026 +456 470 £/an,
graine 723002 −476 965 £/an. Les dix égalités montrent que le
traitement ne modifie pas la métrique finale dans une partie des
mondes, mais ne suffisent pas à prouver l'absence d'activation :
le banc de décision était volontairement à `probes=2`. De même,
les +0,30 train et +0,20 gare moyens ne prouvent ni qu'une OD
initialement perdue a été sauvée, ni que son profit marginal est
positif. Les traces ciblées resteraient nécessaires pour une
future hypothèse distincte.

**Reproductibilité.** Sources :
`results/rail_repair_idle_railonly_gateA_40x5_20261030.json`
(SHA-256
`d6a0d3980e2a5f2c5177e3fb92a8aadf64a678e7ce1a7ed54abf3700c24f25ae`),
checkpoint mensuel `*.jsonl` du même préfixe, analyse
`results/rail_repair_idle_railonly_gateA_40x5_20261030_analysis.json`.
Ces fichiers bruts sont ignorés par Git mais présents sur la
machine de test ; le résumé vérifiable et les **40 deltas par graine**
sont archivés dans
`docs/rail_repair_idle_railonly_gateA_40x5_20261030_analysis.json`.
Scripts reproductibles :
`sweeps/run_rail_repair_idle_railonly_40x5_20261030.py` et
`sweeps/analyse_rail_repair_idle_railonly_40x5_20261030.py`.
Le premier lancement avant toute mesure a refusé les trois
switches `mode_*=0` communs aux deux bras : ajout explicite de
`--allow-shared-nondefault` en commit `da1423dc`, puis **une
seule** campagne 80/80 ; cela n'a changé ni les bras ni les graines.
