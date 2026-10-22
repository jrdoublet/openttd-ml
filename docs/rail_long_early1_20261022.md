# RAIL-LONG-EARLY-1 — ouverture anticipée des liaisons longues RAIL

Date : 22 octobre 2026. Statut : **expérience exploratoire ; non qualifiée, réglages de production inchangés**.

## Objet et hypothèses distinctes

Le plafond normal des candidats RAIL est `v294_rail_dist_decouple=200` (avec
priorité sur V168=160). La recharge V217, activée dès 1972, propose dans le code
de référence du fret à 250 tuiles **seulement** quand le vivier RAIL contient moins
de deux projets démarrables, que la caisse disponible dépasse 1 M£ et que
`v269_rail_late_relax=5` autorise la génération à partir de 1975.

L'expérience découple les trois effets :

1. **Initial**, plafonner RAIL normal à 250 au lieu de 200 ; cela affecte les
   passagers, le fret et les bandes RAIL/AIR, mais ne modifie pas les coefficients
   de ROI (le réglage `rail_cal` reste à **0 dans les deux bras**).
2. **Secondaire**, conserver 250 initial, autoriser jusqu'à 400 tuiles **pour le
   fret V269 seulement**, sans modifier les bandes passagers/AIR. Nouveau réglage
   opt-in `v269_rail_long_max=400`, **défaut 0** (historique V269=250).
3. **Date**, à plafond initial 250 et secondaire 400 identiques, comparer N=5
   (1975) à N=2 (1972, première année possible car V217 attend deux ans).

Le bras `joint` combine initial 250 / secondaire 400 / N=2 contre le code de
référence initial 200 / secondaire historique 250 / N=5. Une comparaison jointe
ne suffit pas à identifier la cause d'un gain ou d'une perte.

## Audit du parcours et interventions

| Point de passage | Constat et traitement |
|---|---|
| `OpexRefreshEpochBounds`, `OpexCatalogBounds` | `railMax` provient de V294i ; réglage initial 250 possible sans nouveau code. Le plafond normal s'applique aux voyageurs et affecte la frontière AIR_ONLY. |
| `OpexMakeCandidate` | Le fret, uniquement pendant V269, peut franchir `bounds.railMax` jusqu'à `v269_rail_long_max`; passagers restent limités par `bounds.railMax`. Les autres filtres économiques sont conservés. |
| `OpexV276PrepareUnit` / `OpexV276Enumerate` | Sur carte >=1024², V276 est activé par défaut et bloquait les longues distances à la fois par la grille et le filtre pax appliqué par erreur au fret. Sous l'option 400, ces deux passages utilisent le plafond fret approprié pour le seul cargo de recharge. |
| `OpexV276Evaluate` | Le tri actuel privilégie les longues distances et n'évalue que 500 couples par unité. Le passage de 250 à 400 peut donc évincer des couples plus courts **avant** l'évaluation économique ; il s'agit d'un effet d'opportunité à mesurer, pas d'un gain supposé. |
| `OpexV276Request` / `OpexV276Start` | V276 étant asynchrone, les conditions temporaires `V269_RELAXED` et le cargo de recharge sont capturés dans la demande afin que l'extension ne soit pas perdue après l'appel du générateur. |
| `V217` / `V269` | Préserve les critères « vivier faible », caisse >=1 M£, délai N et recharge fret. `v269_rail_late_relax=0` reste désactivant. |
| Chemin A* | Les limites de recherche et de budgets d'itérations restent **inchangées** ; permettre une distance de 400 n'assure pas de trouver/financer/poser une ligne. |
| `OpexRailIterations` et ratio profit/opcodes | Aucun recalibrage du score. Le modèle quadratique historique prévoit environ 150 k itérations à 250 tuiles, 384 k à 400 ; au seuil fret 200, cela exige respectivement près de 30 k£/an et 77 k£/an de profit théorique pour franchir le filtre. Les `SQInteger` OpenTTD sont 64 bits : pas de débordement à ces distances. |
| V233 goods graft / mécanismes hors V217 | Conservés à leurs plafonds historiques : cette expérience ne valide pas les grafts longs ni une ouverture universelle du rail. |

Les journaux déjà existants (`V217_RAIL_REFILL`, `PORTFOLIO_RANK`,
`PROJECT_CHOSEN`, `RAIL_ATTEMPT`, `RAIL_BUILD`, `RAIL_BUILD_FAIL`, `AIR_BUILD`)
sont complétés, uniquement avec `decision_log` et l'option secondaire active,
par `RAIL_LONG_SCREEN` (admission/rejet de chaque candidat >200 par cargo,
distance, raison) et `RAIL_LONG_CANDIDATE` (ROI, profit, plafond).

## Protocole reproductible

Harnais `sweeps/run_rail_long_early1_20261022.py` (sur
`sweeps/run_c66_reference.py`), image `openttd-lab:latest`, un seul conteneur,
10 CPU, 10 workers, RAM 8 Go ; toutes les comparaisons appariées utilisent
la même carte/graine, `rail_cal=0`, même horizon et même bundle C66.

- `--case initial|secondary|timing|joint` identifie le seul facteur modifié ;
  `--stage smoke|three|one-ten|ten|a|b` pilote l'horizon/l'effectif (`one-ten`
  = 1 graine / 10 ans, diagnostic événementiel). Le smoke dure **3 ans**
  pour rendre possible la première ouverture N=2.
- Cartes 256² (`--map-size 8`) pour diagnostic initial ; une validation du chemin
  asynchrone V276 en 1024² (`--map-size 10`) ou V276 explicitement forcé
  (`--v276-slices 2`, mêmes réglages sur les deux bras) reste impérative avant
  toute activation de la seconde tranche en production. En grande carte, isoler
  les bornes par **250 opt-in contre 400 opt-in** : le réglage 0 conservait
  le vieux bug V276 de perte de V269 asynchrone et confondrait correctif et borne.
- `--probes 6` produit les journaux de décision des **deux bras** ; les
  performances économiques doivent être mesurées **sans sondes** pour ne pas
  perturber les budgets d'opcodes.
- Porte A éventuelle : 40 graines × 3 ans, seuil de gain relatif 4 %, garde de
  valeur 5 %. Porte B (seulement si A et exposition probante) : 20 × 10 ans avec
  la règle `non_erosion`. Aucune petite comparaison diagnostique n'autorise une
  adoption.

## Résultats exploratoires

| Essai et campagne sous `results/` | Graines/horizon | Δ profit/an variante-référence | V/D/E | Δ valeur agrégée | Verdict |
|---|---|---:|---:|---:|---|
| `rail_long_early1_joint_smoke_1x3_20261022` | 1 × 3 ans, graine 42 | **−252 052 £** | 0/1/0 | −17,89 % | Diagnostic uniquement |
| `rail_long_early1_initial_3x3_20261022` | 3 × 3 ans, 42/100/7 | **−255 517 £** | 1/2/0 | −15,49 % | Diagnostic défavorable, IC95 [−708 031 ; +198 042] |
| `rail_long_early1_secondary_3x3_20261022` | 3 × 3 ans, 42/100/7 | **0 £** | 0/0/3 | 0 % | Aucune différence avant 1973 (N=5) |
| `rail_long_early1_timing_3x3_20261022` | 3 × 3 ans, 42/100/7 | **0 £** | 0/0/3 | 0 % | Aucune différence visible entre N=5 et N=2 sur ces graines |
| `rail_long_early1_timing_3x10_20261022` | 3 × 10 ans, 42/100/7 | **+76 510 £** | 2/1/0 | +3,52 % | Diagnostic uniquement, IC95 [−166 821 ; +352 036] |
| `rail_long_early1_secondary_3x10_20261022` | 3 × 10 ans, 42/100/7 | **+115 559 £** | 2/0/1 | +1,17 % | Diagnostic uniquement, IC95 [0 ; +217 467] ; ref **250 opt-in** contre 400 |

**Limite du facteur initial à 10 ans :** les campagnes
`rail_long_early1_initial_3x10_20261022` et
`rail_long_early1_initial_3x10_retry1_20261022` ont toutes deux échoué **avant
la première partie** pendant le gel des bibliothèques par C66 : HTTP **502 Bad
Gateway** du serveur BaNaNaS sur `ai-library/51554648`. Aucun profit à dix ans
pour le seul passage initial 200→250 n'est donc mesuré ici. Ce résultat reste
manquant, et il ne faut ni l'inférer des autres campagnes ni transformer ces
échecs d'infrastructure en échecs économiques. Les 3×3 à trois ans restent
valides et les deux 3×10 portant sur la tranche secondaire/date sont complets.

Les comparaisons n'incluent pas de `decision_log` ; des égalités de profit et
valeur ne prouvent **pas** à elles seules que le plafond a été matériellement
franchi. Vérifier l'exposition dans les journaux dédiés : événement V269,
distances >250 réellement admises, statut d'A*, construction effective et
éventuelles occasions AIR évincées.

Les bundles C66 sont figés **dans chaque duel**. Certains correctifs de garde
ont été réalisés entre campagnes exploratoires : les statistiques par couple
référence/variante restent utilisables, mais il ne faut pas comparer les niveaux
absolus de deux campagnes distinctes comme s'ils provenaient d'un unique bundle.
Pour le test `secondary` court sur carte 256², le bras de référence utilisait le
réglage historique `v269_rail_long_max=0` ; dans les futurs tests de grande carte,
la référence doit explicitement utiliser **250** pour avoir le même correctif
de capture asynchrone et isoler le seul changement 250→400.

### Sonde de mécanisme à 10 ans : `secondary_trace_1x10`, graine 42

Campagne `results/rail_long_early1_secondary_trace_1x10_20261022` : une paire
1970–1979, **`--probes 6` symétrique**, référence secondaire 250 contre 400,
plafond normal 250 et N=5 des deux côtés. Profit terminal variant−référence
**+38 768 £/an**, valeur +0,19 % ; ces montants **avec** `decision_log` ne sont
pas interchangeables avec ceux des campagnes économiques sans sonde.

Décodeur : `sweeps/analyze_rail_long_early1.py`, rapport de données
`results/rail_long_early1_secondary_trace_1x10_20261022_funnel.json`.

- Variante : **37 appels de recharge V217** portent effectivement
  `freight_cap=400` à partir de 1975. La référence reste à 250.
- Sur la variante après 1975, le journal des paires dans 251–350 tuiles
  indique **283 rejets distance_long** et **1 rejet ratio_floor** ; dans
  351–400, **87 rejets distance_long**. Ce sont des **occurrences**, pas des
  paires distinctes. Il n'y a **aucun candidat admis >250**, ni tentative ni
  construction ferroviaire >250 dans ce duel.
- L'unique paire au-dessus du plafond précédent ayant atteint le filtre de
  rentabilité est une liaison **WOOD de 263 tuiles le 1er décembre 1976** :
  `iter_pred=165854`, `profit=10666`, `ratio=64`, contre le seuil fret 200.
  Elle échoue à ce filtre sans lancer de construction.
- Les deux politiques ont **36 événements AIR_BUILD** ; la variante a
  **26 RAIL_BUILD** et la référence **25**, mais tous leurs tracés restent au
  plus à 250 tuiles. Les projets AIR peuvent néanmoins être décalés dans le
  temps sans modifier leur nombre final.

**Conséquence : le +38,8 k£/an de ce duel ne prouve aucun retour d'une liaison
251–400.** L'ouverture expose bien le contrôle de distance, mais pas une
construction longue supplémentaire. Les différences de sélection, d'opcodes
et de calendrier suffisent à produire des dérives économiques sans ligne >250.
La prochaine question scientifique serait d'isoler le **filtre profit/opcodes**
de la constructibilité A*, sans modifier automatiquement les deux à la fois.

### Test du générateur V276 en exécution asynchrone

Carte 256², `v276_cand_slices=2` forcé **sur les deux bras** afin de traverser le
même code utilisé automatiquement sur cartes >=1024². Le premier banc
`rail_long_early1_v276_trace_1x10_20261022` a été **invalidé** : deux erreurs
Squirrel `class instances do not support the new slot operator`, dans
`OpexV276Start` lors de la capture de la borne. La cause était l'écriture par
`<-` de champs inconnus sur l'instance `catalog` ; fix appliqué : stocker les
deux champs temporaires dans la **table** clonée `catalog.bounds`.

La répétition `rail_long_early1_v276_trace_fixed_1x10_20261022` est saine :
**2/2 parties complètes**, aucun `noai_error`, 10 ans, graine 42. Variante
secondaire 400 contre référence 250, toutes autres conditions identiques,
`--probes 6`. Écart de profit terminal **+204 608 £/an**, valeur +5,33 % ;
diagnostic d'une seule graine **avec sondes**, jamais une qualification.

Analyse détaillée `results/rail_long_early1_v276_trace_fixed_1x10_20261022_funnel.json` :
60 recharges V217 ont signalé `freight_cap=400` dans la variante, zéro dans
la référence. Le générateur asynchrone a effectivement fait passer des paires
de plus de 250 tuiles jusqu'au filtre d'origine constructible : **4** événements
`unsitable` dans la bande 251–350 et **1** dans 351–400, mais **0 candidat
admis, 0 tentative et 0 construction >250**. Chaque bras a 23 événements
`RAIL_BUILD` et 26 `AIR_BUILD`, sans que cela permette d'attribuer le gain.

Le correctif asynchrone est donc validé sur le **parcours V276 forcé**, non sur
les coûts et contraintes d'une véritable carte 1024² (test de scalabilité
encore ouvert). Le mécanisme n'est pas qualifié économiquement.

## Critères de suite et verdict

Le mécanisme doit prouver, avant adoption, une chaîne causale sur au moins une
graine : `vivier V217 insuffisant` → `caisse >=1 M£` → `borne 400` →
`fret 251–400 produit` → `choisi` → `A* réussi` → `construit`, puis un
profit durable à 3 et 10 ans. Un décalage des achats AIR ne constitue pas une
éviction causale démontrée sans comparaison de l'éligibilité/finançabilité à
la même date et des projets effectivement construits.

**Provisoire :** les résultats courts ne montrent pas de bénéfice et le passage
initial 200→250 est défavorable sur le petit échantillon. À dix ans,
le 400 secondaire (+115,6 k£/an) et son ouverture dès 1972 (+76,5 k£/an)
présentent des signes positifs sur trois graines, **insuffisants pour qualifier**
le mécanisme sans preuve d'exposition et portes complètes. Maintenir les valeurs
de production à 200 / 250 en 1975 et `rail_cal=0` tant que les portes ne sont
pas passées. Le code 400 reste expérimental et désactivé par défaut.
