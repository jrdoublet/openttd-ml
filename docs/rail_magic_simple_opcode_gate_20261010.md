# P0 RAIL — ablation bonus et ROI×15 en conservant profit/itérations (10 octobre 2026)

## Hypothèse pré-enregistrée, sans réemploi opportuniste du ROI pur

L'essai `rail_magic_simple_roi=1` a échoué à démontrer une équivalence
économique stricte au 40×5 : +48 985 £/an, IC95 [−18 743 ; +118 178],
malgré des constructions RAIL finales en baisse. Il change l'unité du
classement local en un ROI entier et génère beaucoup d'ex æquo.

On teste séparément **`rail_magic_simple_opcode=1`**, OFF dans les quatre
difficultés. Le score TOP20 local devient le **`opcodeRatio` déjà calculé**
`profitAnnual*1000/iterations`, et ne contient plus les seuils de durée de
rotation 12/25/45 jours, primes 130/115/100/60 % ni `ROI×15`.
Il n'est **pas** un nombre d'opcodes VM mesurés : son dénominateur est le
nombre prédit d'itérations A*. Les admissions 500/200, les plafonds A*,
le TOP64 intermodal financier C69/C70 et les décisions AIR/ROAD/WATER
sont inchangés. Les chaînes V88 suivent la même ablation avec la sentinelle
`V88_CHAIN_FORCE` préservée. `rail_magic_simple_roi=0` des deux côtés.

La formule OFF est historiquement identique, ordre des divisions entières
inclus. L'absence de consommateur métier TOP20 avec C80 et reuse OFF ne
garantit pas la neutralité *temporelle* : le tri et les tours du scheduler
consomment des opcodes, même si leurs résultats ne sont pas investis.

## Qualification définie avant mesure

Smoke Docker 1 graine × 1 an puis A/B figé **40 graines canoniques × 5 ans**
sur le même bundle, 80 parties saines ; **20 graines canoniques × 10 ans**
uniquement si A ne montre ni dégradation économique ni surcoût substantiel
en opcodes mesurés. Décision rigoureuse d'équivalence économique conservée
du premier essai : IC95 bootstrap intégralement à l'intérieur de **±1 %**
du profit terminal moyen OFF, ratio des moyennes de valeur compagnie
supérieur ou égal à **−1 %**, et lecture des pires graines et constructions.
Un IC traversant zéro ne suffit pas. Garder la différence moyenne, médiane,
IC, Wilcoxon, V/D/E, AIR et RAIL physique et annuels dans le rapport.

Les comptages `OP|year|cand_pax|cand_freight` et
`OS|year|cand_rank|util` **déjà créés** par l'IA sont désormais décodés
uniquement côté hôte depuis SIGN dans les sauvegardes, sans coût VM de
sonde nouvelle. On compare les postes candidats/TOP20 disponibles, la
couverture et le nombre de signes, séparément de la somme **partielle**
IG/OB/RB/OA/OM. Neutralité du poste : surcoût moyen de candidatures+Top20
au plus 1 % du coût de ces postes OFF ; pas de signe de régression large
sur les postes partiels. Ces observations NE sont PAS le total des opcodes
VM du moteur et ne justifient aucune assertion de neutralité VM globale.
Une mesure absente/incomplète empêche de qualifier le coût et bloque la B.

Mise en garde : les panneaux de budgets sont des compteurs cumulés de
`OpexBudget` qui peuvent repartir de zéro après un Load ; comparer les
snapshots appariés à même horizon, jamais sommer toutes les années.
Le champ `OS` porte uniquement le TOP20 de génération, pas la formule du
score ni les reclassements de `projects.nut`. Les flags intrusifs
`probe_loop_ops`, `probe_candidates_rail`, `rail_magic_shadow` restent OFF.

## Résultats

Contrats hôte verts : `test_rail_magic_simple_opcode.py` 2/2,
`test_rail_magic_simple_roi.py` 2/2,
`test_rail_budget_signs.py` 3/3,
`test_rail_magic_economics.py` 4/4,
`test_homogeneous_preselect.py` 3/3, soit **14/14** sur le sous-ensemble
concerné. `git diff --check` ciblé OK. La branche OFF garde exactement
les parenthèses et l'ordre de divisions entières de l'historique ; le
léger surcoût des nouveaux tests de flags OFF n'est pas nul en opcodes.

Smoke `rail_magic_simple_opcode_smoke_1x1_20261010_r1` :
bundle `226368a5c6b141daac700569a4165cc2e0205a0394a1156de884ea3c88296e0c`,
2/2 parties saines, seed42 à un an **profit et valeur identiques**.
Résumé `rail_budget_sign_by_year` correctement disponible pour OFF/ON ;
le coût OP/OS est nul en année 1970 et l'exposition n'est donc pas validée
par ce smoke. L'extraction a été vérifiée avec des valeurs non nulles aux
checkpoints des premières parties de cinq ans (année 1972 et ultérieures),
avec présence des deux panneaux et absence de conflits observés.

Porte A figée `rail_magic_simple_opcode_A40x5_20261010_r1` :
**même SHA de bundle** que le smoke, manifeste
`171b3752079d74c784586b727ca336462583c206543d00738f7018b1c93d7927`,
10 CPU / 8 Go / 10 workers, 40 graines canoniques appariées sur 5 ans.

### Porte A terminée : rejet économique

**80/80 parties saines, 40/40 paires, couverture complète des métriques** ;
aucun `failed_run`, année terminale 1974. Profit annuel OpexAI ON−OFF :

| Indicateur | Mesure |
|---|---:|
| Moyenne du delta de profit annuel | **−88 103,8 £/an** |
| Médiane | **−64 072 £/an** |
| V/D/E | 14 / 25 / 1 |
| Wilcoxon bilatéral | p = 0,066098 |
| IC95 bootstrap de la moyenne, 20 000 tirages seed 0 | **[−172 423,05 ; −6 073,775] £/an** |
| Profit annuel moyen OFF | 1 998 288,1 £/an |
| Intervalle d'équivalence ±1 % pré-enregistré | [−19 982,881 ; +19 982,881] £/an |
| Ratio des moyennes de valeur de compagnie | **−4,685203 %** (garde −1 % échouée) |
| Verdict brut du harnais `gain_short` | `fail_primary_and_value_guard` |

**La dégradation de la moyenne est étayée par l'IC bootstrap entièrement
négatif**. La valeur de la compagnie échoue aussi à sa garde explicite.
Le Wilcoxon p=0,066 ne suffit pas à contredire ces deux constats : il teste
une autre statistique. L'équivalence économique est clairement rejetée.

Par année, différence de `profit_year` moyen : 1970 **−5 152**, 1971
**−33 497**, 1972 **−76 674**, 1973 **−91 228**, 1974 **−88 104 £/an**.
Pires graines 1974 : **802204 −798 429**, **73 −651 976**,
**781335 −478 994**, **423960 −441 721**, **841478 −433 215 £/an**.
Ces cinq graines ont respectivement **28, 20, 38, 21, 31 avions de moins**
dans l'état final ON. Sur les 40 paires : **−5,75 avions**, −0,125 train,
−0,675 véhicule routier, **−0,825 installation ferroviaire** en moyenne.
Ce sont des états terminaux, pas des décomptes exhaustifs de constructions,
et le changement de trajectoire n'est pas mécaniquement attribuable à la
seule différence du tri TOP20 ; le coût du scheduler change aussi.

### Mesure d'opcodes : économie sur postes couverts, pas VM totale

Le nouveau parseur d'**anciennes traces** `rail_budget_signs.py` est présent
dans le bundle figé et dans le décodeur JSON/JSONL. Aux 40 paires à 1974,
les **80 relevés OP/OS sont complets**, zéro signe invalide ou conflictuel.

| Coût OpexBudget cumulé par partie, horizon 1974 (moyenne) | OFF | ON | ON−OFF |
|---|---:|---:|---:|
| `cand_pax` | 1 738 920 | 1 646 136 | −92 784 |
| `cand_freight` | 455 354 | 420 281 | −35 073 |
| `cand_rank` | 27 644 | 24 847 | −2 797 |
| **Total de ces trois postes mesurés** | **2 221 918** | **2 091 263** | **−130 655 (−5,88 %)** |

Le harnais déclare `observed_opcodes_total` partiel (IG/OB/RB/OA/OM)
**47 161 631 OFF** contre **43 073 182 ON** : −4 088 449 (−8,67 %),
mais ces panneaux ne couvrent pas `cand_rank`/génération, les trajectoires
et le nombre de signes retenus varient, et
`observed_opcode_complete_cpu=false`. **Ne pas appeler ceci un gain VM
total prouvé**, ni confondre la baisse due à moins de projets financés avec
une optimisation pure du code. Les mesures OP/OS confirment seulement que
les postes explicitement instrumentés coûtent moins au terme de ces parties.

**Décision : REJET.** La simplification du classement local vers le ratio
profit/itérations économise une part de calcul déjà mesuré, mais n'est
pas neutre économiquement et respecte encore moins l'intervalle strict
pré-enregistré. Aucune porte B **20×10**, aucune adoption par défaut,
aucun commit ou push. Le résultat du ROI pur est sur un bundle/HEAD
distinct et ne sert pas de bras témoin causal pour cette campagne.
