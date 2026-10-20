# V294c (A* 400 %) — porte A rail seul — 20 octobre 2026

- **Code fige** : `e009ebf6f0dd71d5e42a9c97c81d43b256fe2b29`, worktree `v294c-adapt`, clean; bundle SHA256 `50d8a10731aeee7ea1fdf111c3330c52cb137bc18a81aa87fd53edd3a06ec562`.
- **Source** : `evidence/review/v294c_a400_20261020/gateA_40x3.json`; manifeste `evidence/review/v294c_a400_20261020/gateA_40x3.manifest.json`.
- **Protocole** : deux duels separes apparies par graine, 40 graines distinctes x 3 ans x 1 repetition, 80 parties, carte 256x256, adversaire AAAHogEx configure trains uniquement (`disable_veh_roadveh/tram/ship/aircraft=1`).
- **Temoin** : `OpexAI[mode_air=0,mode_road=0,mode_water=0,v294_rail_weight_adapt=0]`.
- **Variante** : `OpexAI[mode_air=0,mode_road=0,mode_water=0,v294_rail_weight_adapt=400]`.
- **Metr. primaire** : `profit_year`, regle `gain_short`, gain minimal >= 4 % de la moyenne de reference, Wilcoxon bilat. p<0.05, borne basse bootstrap IC95 >0, garde company_value >=-5 %; 20 000 resamplings bootstrap, seed 0. Porte B non lancee si echec.
- **Smoke de diagnostic** : graine 42 x 3 ans, `probes=6` (panneaux et journal), +46 425 GBP/an, valeur +4,62 %, 2/2 sains, 59 evenements V294C dont 1 baisse 400->200, aucune conclusion economique.
- **Porte A** : 40/40 paires saines, toutes metriques presentes, 0 run manquant/erreur ; sans `decision_log` pour eviter un effet observateur. Profit/an moyen reference 1 006 835,3 GBP, variante 983 957,3 GBP; delta moyen -22 878 GBP/an (mediane +21 471,5), 22V/18D/0E, Wilcoxon p=0,6850159, bootstrap IC95 [-86 876,225 ; +40 409,65] GBP/an. Seuil minimum requis +40 273,412 GBP/an. Company_value ratio des moyennes -12,993935 %, garde -5 % non tenue.
- **Verdict** : `fail_primary_and_value_guard` ; REJET. Defaut 0 inchange; aucune porte B, aucune adoption ni fusion dans master ; publication des preuves sur la branche v294c-adapt.
- **Pires graines delta profit_year variante - reference** :
  - 2026: -551,065 GBP/an, valeur -889,062 GBP.
  - 512: -353,225 GBP/an, valeur -568,574 GBP.
  - 59527: -351,424 GBP/an, valeur -690,680 GBP.
  - 802204: -345,802 GBP/an, valeur -485,346 GBP.
  - 54321: -281,810 GBP/an, valeur -492,596 GBP.
- **Limites** : ce verdict concerne le profil rail seul, pas une mesure multimodale ni une qualification sur 10 ans. Les tests Python ne remplacent pas les parties moteur ; ici les 80 jeux moteur ont ete completes.

## Données et reproductibilité

Les JSON et manifestes sont des copies byte-à-byte des artefacts du moteur ; `smoke_variant_engine.log.gz` est le journal moteur compressé du smoke contenant les 59 événements V294C. `preregistration.txt.gz` conserve les paramètres annoncés. Le SHA256 des `.gz` est celui du journal **décompressé**.

| Fichier | Octets originaux | SHA256 |
| --- | ---: | --- |
| `gateA_40x3.json` | 1664522 | `943c1b4add8c6bf7b76e619ed23ec28f52764f3caea1ca0d521efc3872b9475e` |
| `gateA_40x3.manifest.json` | 76582 | `2e888ad557d09085de425b86e7e8c715455dbfd5e078c50637f2210ba3be6196` |
| `smoke_42x3.json` | 79182 | `b3c4cf773259603dd8418e76d4ca3fcbf34f92275ac027fca63023161dd93d96` |
| `smoke_42x3.manifest.json` | 46093 | `5083e0f939256f81da2d275a4cf2a75b2db34cd623f32036dca0fa15465cb67c` |
| `preregistration.txt.gz` | 710 | `65f0ea54393d54e2704545939dd41dbbdea5b618ba3032c866fc68b4562570a9` |
| `smoke_variant_engine.log.gz` | 2258801 | `2d4d7dec829ac6ce4e1dabd74919740322a23674b0aa438db7389e9b9f416471` |
