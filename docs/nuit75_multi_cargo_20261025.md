# N75-MC — recharge ferroviaire d'un cargo supplémentaire (25/10/2026)

## But et état

Objectif utilisateur : +4 % de profit OpexAI **dès fin 1972** en porte A V102
40×3 (et amplification jusqu'à la cible Opex/AAAHogEx 75 % en 20×10 ou 40×10).
Travail **expérimental et non qualifié** sur le worktree
`.worktrees/nuit75-early-multicargo-v1`, base immuable `83e436cc`.
Ni défaut, ni commit, push, merge, ni AGENTS.md modifié.

## Faits vérifiés

- Référence master 20×10 1970/256² : Opex 4 122 708,10 £/an, AAA
  7 290 134,25 £/an en 1979 ; ratio des moyennes **56,5519 %**,
  médiane des ratios appariés **58,9112 %**. Manque théorique
  Opex **+1 344 892,59 £/an** si AAA constant.
- En 1972 la moyenne master Opex est 2 104 034 £/an :
  prérequis +4 % = **+84 161 £/an**.
- `v217_rail_refill=1` est **déjà le défaut des quatre difficultés**,
  depuis le 17/10. Son chemin `orchestrator.nut:801-890` régénère
  mensuellement le rail fret si capital >100k£ et moins de deux projets
  physiquement non bloqués, sans vérifier leur devis.
- `v276_cand_slices=3` auto résout à 0 sur 256² ; à 1024² il résout
  à 2 et la variante se désactive volontairement.
- `projects_generation.nut:29-65` balaie **déjà** d'autres cargos si
  le premier n'offre aucun candidat fret. Le seul gisement propre à
  N75-MC est une catégorie donnant des candidats **non finançables**
  alors que la suivante en fournirait de vraiment sélectionnables.
- Archive non identique au master `rail_cal4_40x10_multimodal_pc_20261021_engine` :
  474 mois V217 journalisés en 1972 ; 240 `skip cash`,
  142 `skip pool`, 92 `refill`, dont 75 avec `startable=0`.
  234/474 mois au-dessus de 100k£ ; 75/234 = **32,05 %** sans
  candidat *non bloqué* **avant recharge**, pas sans projet finançable.
  **Ne pas transposer cette fréquence au master 83e436cc.**
- Archive diagnostic `v217m2_diag_3x10_20261024_engine` :
  36 mois 1972, 22 `skip cash`, 6 `skip pool`, 8 `refill`
  dont 7 démarrant sans candidat. Chaque recharge publie 4–40
  candidats, sans preuve de financement. 33/42 tentatives RAIL
  sur ces trois graines réussissent physiquement, mais cela inclut
  les constructions de V217 **déjà par défaut** : gain N75 inconnu.
- Audit fenêtre AIR 1971 : 59 RAIL suivis d'un AIR en 30 jours dans
  32/40 mondes, profit AIR prédit médian 146 120 £/an ;
  **AIR finalement construit dans la référence** : plafond
  descriptif ≠ nouveau gain. Audit 1972 AIR non construites derrière
  RAIL : plafond optimiste pondéré ~70,7 k£/monde, sous +4 %.
- AIR_GROW corrigé 5×3 −99,3 k£/an et valeur −8,39 % ; N75 AIR
  true quote 10×3 +32,2 k£ (+1,4 %), mais leurs effets de devis
  V252 sont partiellement redondants. **Pas de cumul qualifiable**.

## Prototype technique opt-in

`n75_multi_cargo=0` OFF, `1` SHADOW, `2` ON ; **0 aux quatre
difficultés**. Modules modifiés `globals_pre.nut`, `info.nut`,
`settings.nut`, `scheduler.nut`, `persist.nut` ; `main.nut`,
`orchestrator.nut`, `projects_generation.nut` historiques intacts.

Après V217 au plus une fois par mois, dès 1972 et hors recherche/worker
actif, vérifie le pool RAIL : profit prévu >0, coût de financement <=
capital réel après réserve, non abandonné et pas trop proche. Ce
**filtre préliminaire n'est ni un visa C80/Kpass ni une garantie de
gare ou A\***. En ON tente **un** cargo supplémentaire lorsque V217
est actif ; sans V217, deux tentatives. Le générateur interne peut
lui-même parcourir davantage de cargos en fallback. La génération
s'effectue sur un brouillon `clone ai._projects` ; `OpexApplyGeneratedModeProjects`
ne publie un nouveau vivier que si au moins un nouveau projet est
budgétairement admissible. **Sans admissibilité, aucun état portefeuille
ni statistique C77 du live n'est remplacé.** SHADOW ne régénère pas.
Instrumentation `N75_MC phase=refill|unapplied|shadow_budget_empty`
avec coût opcodes.
Save/Load stocke `n75McLastMonth` uniquement quand le réglage est
actif, et restaure la cadence après chargement des réglages.

**Limites :** même un `budget_eligible=1` n'est pas une construction
nouvelle ; l'unique preuve physique sera une différence appariée des
`RAIL_BUILD` et de leur marge réelle, avec suivi des projets AIR/V252
déplacés et de la charge d'opcodes (historique V217 ~0,29 M opcodes
par recharge, sans garantie de comparabilité).

## Tests et garde de décision

Tests Python de contrats ciblés : **170/170 verts**, dont
`test_n75_multi_cargo`, V217, V276, PO01C, C77, C80, V252,
C121, Save/Load et plafond de paramètres ; `git diff --check` OK.
`sweeps/n75_mc_legacy.py` retire strictement et uniquement les
octets du nouveau paramètre pour **préserver le SHA historique**
`info.nut`/`settings.nut` : aucune rebaseline des hachages.
Ces tests **ne compilent pas Squirrel**.

### Smoke technique pré-enregistré (sans qualification)

Campagne `nuit75_mc_smoke_1x1_20261025`, base
`83e436cc` avec **un seul bundle de code expérimental** pour les bras
`OpexAI[n75_multi_cargo=0]` et `OpexAI[n75_multi_cargo=2]`.
Graine 42, départ 1970, **1 an**, carte 256² (`--map-size 8`),
une répétition, AAAHogEx-115, `probes=258` symétriques,
`--script-debug`, 10 CPU, 8 GiB, 2 workers.
CLI V102 : `gain_short`, seuil utile 4 %, garde valeur 5 %,
`--required-seeds 40 --required-years 3 --years 1 --seeds 42`.
Ce smoke **ne peut pas exposer N75**, qui attend 1972 : seuls la
compilation, les erreurs runtime et les deux duels complets comptent.
Avant lancement : `docker ps` vide obligatoire, zéro autre Docker.

**Smoke r1 effectué** sur le bundle `542e1c346d44ae042a5d67713dc8c68be5c34dd1a71a46955e804265a5b5f359`,
manifest `92de2b98ab771b5437df4a215928e41fbb8f6a844c260e68822d3035cbd27baf`.
**2/2 duels complets**, compilation/exécution saines sur graine42/1970,
`diagnostic_only`. ON−OFF `profit_year=+15 316 £/an` dans une année
où N75 ne peut pas agir : **non causal**, pas de preuve de gain.
Le code a ensuite évolué pour ne jamais modifier le vivier si la
recherche ne produit aucun candidat éligible. **Le smoke r1 ne valide
donc pas la nouvelle version** ; smoke r2 sur nouveau bundle requis
avant un quelconque diagnostic 1972.

**Smoke r2 pré-enregistré** : campagne distincte
`nuit75_mc_smoke_r2_1x1_20261025`, même protocole/bras/graine
que r1, nouveau bundle contenant la génération sur brouillon,
sans interprétation économique du changement r1→r2.
Exécution r2 : bundle `ae6b948c9b14e394055e6a4befded72346697fdda5c7737a462f262200450fe2`,
manifest `6627896e19e65049149ea77bc49ab9068124d7c6fbb1c686dffe3fe07c163d67`,
**2/2 sains**, `diagnostic_only`; ON−OFF `+15 316 £/an` dès
1970, identique à r1, mais N75 inactif en 1970 : **aucune attribution**.

### Exposition appariée exploratoire pré-enregistrée, pas porte A

`nuit75_mc_expo_5x3_20261025` : cinq graines 42,100,7,999,2026 ;
référence 0 et variante 2 **issues du même nouveau bundle**, 1970–1972,
256², 1 répétition, 10 parties. Même configuration V102
`gain_short` (seuil4% et garde5% enregistrés, `required-seeds=40`
et `required-years=3`), résultat **diagnostic_only** et non V102 A.
`probes=258`, `--script-debug`, `--max-workers=9 --cpus=10
--memory=8g`. Première preuve exigée avant porte :
`N75_MC phase=refill` daté en 1972, puis **nouvelles OD
RAIL_BUILD réellement achevées ON−OFF** avec âge, profit net observé,
capital, absence d'éviction AIR/V252 et ops. Une variation du total
de profit sans liens physiques n'autorise pas A.

### Résultats effectifs : 5×3, revue des constructions, décision

La campagne exploratoire **s'est achevée : 10/10 parties saines**,
source bundle `ae6b948c9b14e394055e6a4befded72346697fdda5c7737a462f262200450fe2`,
manifest `5367b44a64ab214da6c3a052d4b69ee7450bccfb848130bbb10e61d5ba0e3203`.
Fin 1972, ON−OFF `profit_year` moyen **+126 548,8 £/an**
sur cinq graines, médiane +170 252, 3V/2D, Wilcoxon
exact p=0,3125, IC95 bootstrap [−43 954 ; +297 051,6] £/an,
garde de valeur **+0,47035 %**. Référence de cette cohorte
2 166 576,2 £/an, soit seuil descriptif +4 % = **86 663,05 £/an**.
**Diagnostic uniquement**, 5 graines ne sont pas la porte A40×3.

| Graine | N75 `refill` | `budget_eligible=1` | Δ profit Opex ON−OFF £/an |
|---|---:|---:|---:|
| 42 | 3 | 2 | −151 189 |
| 100 | **0** | **0** | **+301 814** |
| 7 | 2 | 1 | +355 689 |
| 999 | 1 | 1 | +170 252 |
| 2026 | 1 | 1 | −43 822 |

**Attention déterminante :** la graine **100 sans aucun
déclenchement N75** affiche +301 814 £/an de fluctuation OFF/ON.
Sur les **quatre graines réellement exposées**, la moyenne tombe
à **+82 732,5 £/an**, pour une référence ~2 434 607,5 £/an,
soit **+3,399 %**, sous les +4 % requis. Le smoke 1970 montrait
déjà +15 316 £/an entre politiques N75 inactives.
La statistique favorable tous mondes n'est donc pas une preuve
de +4 % causal.

Lecture stricte des 10 journaux via
`sweeps/analyse_n75_mc_expo.py`, dédoublonnant les
`RAIL_BUILD` par (graine,cargo,src,dst), et les
`AIR_BUILD` par paire non orientée :

- **7** déclenchements actifs N75 en 1972, **5** ayant au moins
  un candidat `budget_eligible`, **2** `phase=unapplied`.
  Somme des coûts mesurés dans les 7 `refill` :
  **1 654 407 opcodes**, soit ~236 344/refill, **hors tous
  coûts de préparation et déplacements de calendrier**.
- En 1972 sur l'ensemble des 5 mondes : **51 RAIL_BUILD de
  couples nouveaux dans ON et 30 couples propres à OFF**,
  **29 AIR_BUILD propres à ON contre 20 propres à OFF**.
  Ces différentiels multi-cargo et multi-mode reflètent des
  trajectoires divergentes (y compris graine100 **sans activation**)
  : **ne pas les attribuer entièrement à N75**, ni sommer leurs
  profits prédits comme des profits incrémentaux réalisés.

Réduction du canal physique par
`sweeps/analyse_n75_mc_window.py` : pour chaque recharge
finançable N75, prendre seulement les `RAIL_BUILD` du
**même cargo dans les 45 jours suivants**, puis soustraire
les constructions de la même source/cargo présentes dans OFF
sur toute l'année 1972, même si un autre terminus est utilisé.
Ce rapprochement est **une compatibilité temporelle et cargo,
pas une preuve que le candidat est causé par N75** :

| Graine, recharge | Cargaison | Builds ON ≤45 jours | Builds OFF mêmes sources en 1972 | Δ profit **prédit** £/an |
|---|---|---:|---:|---:|
| 7, 7/11 | OIL_ | 2 | 0 | +69 918 |
| 42, 11/03 | GOOD | 1 | 0 | +21 008 |
| 42, 02/10 | GRAI | 2 | 2 | −12 925 |
| 999, 23/08 | WOOD | 4 | 3 | +5 918 |
| 2026, 07/05 | GOOD | 1 | 1 | −14 255 |
| **Total cinq mondes** | | **10** | **6** | **+69 664** |

Moyenne de ce **proxy nominal** : **+13 932,8 £/an par monde**
et seulement ~**0,64 %** de la référence de cette cohorte,
loin de +4 %. Ce n'est ni une borne mathématique sur toutes les
externalités, ni une estimation de profit réalisé. Certaines
poses sont seulement avancées (GRAI graine42) ou remplacent
la destination d'une même usine (GOOD graine2026),
avec prédiction inférieure. Les AIR déplacés et le coût total
des parcours restent incertains.

Fichiers résultat : `results/nuit75_mc_expo_5x3_20261025.json`,
`.manifest.json`, `_engine/`,
`results/nuit75_mc_expo_5x3_20261025_physical.json`,
`results/nuit75_mc_expo_5x3_20261025_window.json`.

**Verdict final de cette variante : NO-GO pour porte A 40×3,
aucune porte B, aucun défaut changé.** Bien que le signal moyen
des 5 graines soit >4 % descriptivement, il est
statistiquement incertain, et son canal de constructions
additionnelles ne soutient pas ce potentiel. Ne pas relancer
N75-MC ou combiner naïvement AIR_GROW+N75 sans un nouveau
fait causal, idéalement une identité candidate N75 → chantier
et profit réalisé, avec coût AIR/V252 contre-factuel.
Le prototype reste non committé dans son worktree.
