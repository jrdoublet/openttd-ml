# ESTIM-31 : nouvelle recherche combinatoire AIR × RAIL (30 octobre 2026)

## Objectif, source et sélection

L'utilisateur demande de **tester d'autres combinaisons** après trois 40×5
infructueux. Le critère économique reste **uniquement** le ratio des
**moyennes** de `profit_year` OpexAI / AAAHogEx-115 au 01/12/1974.
La valeur de société, les p, les IC95, le seuil historique +4 % et les
opcodes restent descriptifs et ne sont pas des veto économiques. Le profit
propre de chaque concurrent est toujours présenté séparément. Santé des
duels et invariance OFF sont des préconditions techniques. Les premiers
résultats sur cinq graines ne sont que du **criblage**, jamais un 40×5.

Source exacte : bundle figé
`results/estim31_engine_dispatch_air15_root_20261029` contenant le correctif
C121 FullScan sous `estim_unifie & 1`, avec son `C121_GE` historique et ses
deux scans OFF conservés. Les nouveaux bundles sont sous
`results/estim31_joint_newgrid20261030/<configuration>`.
Ils sont copiés sans écraser un résultat précédent : `globals_pre.nut`,
`air_economics_c121.nut` et les deux scans historiques sont strictement
inchangés ; seuls les réglages des a priori existants changent **dans** la
branche ESTIM du `settings.nut` figé. Aucun défaut de production n'est
modifié, aucun nouveau réglage ni paramètre magique embarqué n'est introduit.

Protocole multimodal : OpenTTD 15.3, AAAHogEx-115, 256², années 1970–1974,
`eb14_progressive=3`, `estim_unifie=31`, `probes=2` ; jamais `probes=770`.
Un seul Docker simultanément, `--cpus=10 --memory=8g --memory-swap=8g`,
8 workers maximum ; bench `sweeps/bench_1v1_5y_20seeds.py`.
Les mêmes graines 42, 100, 7, 999, 2026 sont appariées par bras en 5×5 ;
les meilleurs finalistes seulement seront qualifiés sur les 40 graines
historiques. La mesure est le ratio des profits des deux sociétés dans
**le duel variant**, pas le tableau console du contrôle OFF.

## Combinaisons distinctes des campagnes antérieures

| Scénario | AIR | RAIL | Poids | RAIL distance | Garde AIR |
|---|---:|---:|---:|---|---|
| a200_r075_w15_slope | 2,00 | 0,75 | 15 | Incliné | Défaut |
| a175_r100_w30_slope | 1,75 | 1,00 | 30 | Incliné | Défaut |
| a175_r075_w05_slope | 1,75 | 0,75 | 5 | Incliné | Défaut |
| a100_r150_w05_flat | 1,00 | 1,50 | 5 | Plat | Défaut |
| a125_r150_w30_flat | 1,25 | 1,50 | 30 | Plat | Défaut |
| a175_r125_w30_flat | 1,75 | 1,25 | 30 | Plat | Défaut |
| a200_r150_w05_flat_load25 | 2,00 | 1,50 | 5 | Plat | 25 % |
| a075_r075_w30_slope | 0,75 | 0,75 | 30 | Incliné | Défaut |
| a125_r075_w05_slope | 1,25 | 0,75 | 5 | Incliné | Défaut |
| a100_r150_w15_slope | 1,00 | 1,50 | 15 | Incliné | Défaut |

Outils reproductibles, versionnés dans la branche expérimentale :
`sweeps/estim31_joint_newgrid_prepare_20261030.py`,
`sweeps/run_estim31_joint_newgrid_20261030.ps1`,
`sweeps/estim31_joint_newgrid_analyse_20261030.py`,
`sweeps/test_estim31_joint_newgrid_20261030.py`.

## Résultats et décisions

À remplir exclusivement d'après les JSON et JSONL terminés. Les résultats
5×5 ne suffisent pas à inférer la performance sur 40 cartes ; une variation
du profit AAA dans le dénominateur sera explicitée et aucun résultat
en cours d'écriture ne sera compté comme finalisé.
