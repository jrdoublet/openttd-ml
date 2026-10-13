# P0 économique — conversion des projets en constructions, diagnostic du 12/10/2026

**Statut : autopsie descriptive renforcée, causes partielles identifiées ; aucune amélioration économique adoptée.** Ce rapport prolonge [`diagnostic_projects_causal_20261012.md`](diagnostic_projects_causal_20261012.md) sans rouvrir TopK, C83, AC04-A, V144/V145 ni les formules RAIL rejetées. HEAD principal contrôlé `f6139d89`, modifications locales de plusieurs agents **préservées**. Pas de commit/push.

## Méthode : trois sources qu'il ne faut PAS fusionner comme une même partie

1. **Économie physique témoin sans sonde**, même carte duel OpexAI/AAAHogEx : `results/diag_opcodes_1970_1973_default_5seeds_20261012.jsonl`, bundle `edd8b31f...`, cinq graines 42/100/999/1234/5678, 1970–73. Reconstitution mensuelle et quatre trimestres valides obligatoire pour une comparaison de profit annualisé ; valeurs et stocks depuis VEHS/STNN.
2. **Historique P2/P5 instrumenté** des cinq graines : bundle `efa38f1...` et archive `evidence/review/opcode_early4_20261012/project_admission_p2.json` et `project_builds_searches.json`. `P2_PASS` mesure un état d'entrée et le nombre de lignes **nettes** après dispatch ; `P5_RAIL_PASS` mesure des alternatives **après** dispatch, pas leur constructibilité ni la dépense initiale. Les sondes changent parfois la trajectoire ; aucun appariement événementiel avec la source 1.
3. **Nouveau diagnostic mécaniste, même partie OpexAI vs AAA**, trois graines × cinq ans, `results/p0_projects_causal_stage_20261012`, bundle `04af9610318c9214da9664b17d9c6326ba17e332c8f3a4bc8d3cec1342e0a59f`. Actifs `probe_scheduler=1,probe_select_reject=1,catalog_cost_probe=1,probe_loop_ops=1`, `--line-telemetry` annuelle (post-traitement des sauvegardes ; pas une sonde IA). OpenTTD 15.3, même image Docker que les profils précédents, 3/3 jeux complets/sains. Le **premier lancement** `p0_projects_conversion_diag3x5_20261012` était INVALIDE : suppression locale non committée des slots C122 mais références depuis des modules HEAD → `noai_error`, zéro résultat exploitable. Dans le stage isolé seulement, les trois fichiers de réglages (`globals_pre.nut`, `info.nut`, `settings.nut`) ont été rétablis au HEAD ; le smoke 42×1 `r2` sain, suivi du diagnostic `p0_projects_conversion_diag3x5_20261012_r2`. Les changements expérimentaux du principal n'ont pas été annulés ni écrasés. Les sondes ne sont **pas économiquement neutres**.

## Première divergence économique Opex−AAA sur le témoin sans sondes

| Graine | Premier mois de déficit **avec quatre trimestres valides** depuis 1971 | Profit Opex−AAA fin 1973 |
|---|---|---:|
| 42 | novembre 1972 | −683 484 £/an |
| 100 | août 1971 | −582 022 £/an |
| 999 | février 1971 | −1 620 252 £/an |

La valeur de compagnie est un stock, pas un profit. Ces mois sont des **premiers franchissements observés**, non la date de première décision différente : deux IA distinctes divergent dès le début et les prix/cargos/prises de parts diffèrent. La graine 999 décroche bien avant son extraordinaire passage de 116 jours de juillet 1973 ; ce dernier ne peut être la cause initiale du déficit.

## Portefeuille / tentatives / constructions sur les parties historiques instrumentées

| Graine/période | P2 passes | `in_best=0` | Lignes AIR nettes P5 | Lignes RAIL nettes P5 | Interprétation restreinte |
|---|---:|---:|---:|---:|---|
| 42 / 1972 | 296 | 276 | 14 | 0 | Requêtes fréquentes alors que l'entrée du vivier est vide ; ce n'est pas 276 rejets de projets constructibles |
| 100 / 1973 | 135 | 72 | 10 | 3 | 24 juin : après dépense, trésorerie 18 657 £ vs devis rail 42 474 £ (déficit 23 817 £) ; pas une preuve de famine CPU |
| 999 / 1973 | 6 | 0 | 3 | 1 | Vivier non vide, alternatives RAIL annoncées finançables *après* dispatch ; cadence et longs passages ; aucun rail physiquement prêt à être construit sans A* injustement évincé prouvé |

Pour 999, `projects` passe du 30/12/1972 au 13/07/1973 (~195 jours entre les dates), puis le 13/07 occupe 116 jours et **21 300 656 unités de fenêtre** : build 17 546 253, fleet 89 706, regen 3 642 995 ; 3 projets achevés au sens du registre `PROJECTS_COST`, mais **une seule nouvelle ligne rail nette** P5. Zéro tranche positive `P5_RAIL_SEARCH` pendant 1973 sur cette graine ; ne pas imputer les 17,5 M à un A* mesuré ni appeler 21,3 M de véritables instructions CPU utiles/inutiles.

Le coût des resélections est hétérogène, sur le profil initial : en 1973, 42 et 100 ont de nombreux passages avec peu ou zéro candidature, tandis que 999 a 6 sélections incrémentales (2 601 alternatives considérées au total / ~6,716 M de fenêtres), 7 resélections (~7,878 M), **pas un vivier vide**. Le faux état `air_fleet_no_work` n'exclut pas ces resélections car `_projects` est muté *in-place*. Aucun skip global de revalidation justifié ; C76, V141, plan AIR, financement et slots évoluent à travers les ticks.

## Services actifs réellement reconstruits dans le nouveau duel instrumenté

**Clôture 1973**, services avec véhicule/ordres résolus. OpexAI et AAAHogEx proviennent des **mêmes parties** par graine, pas du profil initial :

| Graine | AIR Opex / AAA | RAIL Opex / AAA | ROAD Opex / AAA |
|---|---:|---:|---:|
| 42 | 56 / 13 | 5 / 13 | 2 / 79 |
| 100 | 46 / 13 | 6 / 7 | 0 / 67 |
| 999 | 42 / 19 | 4 / 19 | 1 / 101 |

**Observation déterminante :** l'avance OpexAI en *services AIR actifs* coexiste avec une croissance multimodale AAAHogEx très supérieure sur ROAD et RAIL. Cela n'explique pas à lui seul l'écart de profit marginal par projet ni ne prouve l'existence de ROAD rentable et constructible refusée. Le nombre de services actifs peut fusionner deux routes aux mêmes stations et ignore les constructions inoccupées : ne pas le présenter comme créations physiques brutes.

### Pourquoi l'écart ROAD n'est pas un bug démontré du constructeur

L'audit `candidates.nut:2822-2825` et `info.nut:1384-1390` confirme
`road_pax_build=0` au défaut : **OpexRoadPaxCandidates n'est pas appelé**,
alors que la décomposition des 247 services ROAD AAA observés à fin 1973
sur ces trois graines attribue **246 services à PASS/MAIL** (y compris
les mixtes). La politique d'activation ROAD PAX a déjà échoué sur la
porte économique historique (−4,22 % de profit, IC95 négatif) ; aucune
réactivation ni variante sous un autre nom n'est autorisée ici.

Un autre verrou de *génération* existe : `projects.nut:274-343` choisit
`freightCargo` via le premier cargo RAIL éligible, puis génère le fret ROAD
**sur ce seul cargo** ; la régénération modale reproduit ce couplage
(`projects_generation.nut:13-19,79-89` et `candidates.nut:2648-2649`).
Il peut théoriquement laisser de côté une OD camion sur un autre cargo,
mais **ni son existence ni la constructibilité/finançabilité d'un chantier
perdu ne sont démontrées** : le diagnostic existant n'expose pas les
compteurs candidats par cargo ROAD. Les trois lignes ROAD P5 construites
dans la sonde 3×5 (deux sur seed42 et une sur seed999) indiquent que le
constructeur peut fonctionner. La piste d'un fallback cargo ROAD indépendant
reste **NON DÉMONTRÉE** tant que cette exposition n'est pas mesurée,
sans A40×3 déclenchée.

Le nouveau `SELECT_REJECT` montre, en 1973 : seed42 `topk=20`, seed100 `cash=424`, seed999 `topk=2 888`. En 1972 : seed42 `topk=1 333`, seed100 `cash=188, topk=2 301`, seed999 `cash=602,topk=4 395`. Ces journaux comptent des **visites de candidats AIR**, très répétées, pas des projets uniques sacrifiés. Ils ne doivent pas être additionnés à `P2_PASS` ni interprétés comme autant de pertes économiques évitables.

### Deuxième diagnostic : rejets de chantier effectivement tracés

Sur le **même code/bundle source** mais une **autre trajectoire instrumentée**
(`p0_projects_funnel_probe3x5_20261012`, flags `probe_portfolio=1`,
`decision_log=1`, `probe_scheduler=1`, 3/3 jeux sains), le nouvel analyseur
`analyse_p0_funnel_reasons_20261012.py` relève les comptabilités des
passes, refus par mode et lignes nettes P5 :

| Graine/1973 | Passages `MONTHLY_FUNNEL` enregistrés | Refus principaux observés | Nouvelles lignes nettes P5 |
|---|---:|---|---|
| 42 | 29 | 1 `rail/search_in_progress`, 1 AIR `build_failed` | AIR 3, RAIL 1 |
| 100 | 28 | 3 `rail/search_in_progress`, 1 `rail/ABND`, 1 ROAD `plan_failed`, 4 flotte `fleet_grow_failed` | AIR 12, RAIL 1 |
| 999 | **4** | **78 AIR `batch_plan_dead`**, **30 RAIL `search_in_progress`**, 2 AIR `build_failed` | AIR **14**, RAIL **0** |

Les **78 et 30** sont des comptages de refus à travers candidats et
balayages, **pas 108 projets différents**. La graine999 montre une
interaction matérielle « lots AIR périmés / recherche RAIL occupée » :
le 27/06 plusieurs dizaines de rangs (dont des AIR `batch_plan_dead` et
RAIL `search_in_progress`) sont contournés, puis des AIR encore valides
sont sélectionnés et **six nouvelles lignes AIR nettes** apparaissent
le 20/07 dans la même passe P2. En fin d'année, neuf RAIL aux rangs
0–8 sont signalés `search_in_progress` avant une construction AIR au
rang9. **Le passage n'est donc pas totalement bloqué** : le flux
retombe sur AIR tout en peinant à conclure les recherches RAIL.

`B6_PORTFOLIO` sur seed999 affiche au cours de 1973 un RAIL sélectionné
et finançable (`actual_cap≈52 529 £`, profit nominal ≈112 673 £/an),
mais ce devis n'est **ni une route A* terminée ni une construction RAIL
physiquement réalisable**. Les registres `C41_MONTH_BUSY` documentent
la consommation de fenêtres par `rail_search` jusque tard dans l'année,
sans délivrer la preuve transactionnelle d'une alternative immédiatement
constructible. On ne peut en déduire qu'il suffirait d'augmenter le
budget A* ou de purger des AIR ; les variantes rail N2 et V144 ont
déjà été rejetées.

**Verdict de cette seconde campagne : `diagnostic_only`**, mécanisme
combiné de revalidation AIR et de recherche RAIL **exposé**, mais effet
sur profit contrefactuel et correction rentable **NON DÉMONTRÉS**. Le
libellé `MONTHLY_FUNNEL` est trompeur : c'est un résumé **par passe**, pas
un échantillon indépendant par mois. Ne pas sommer ses `considered` comme
autant d'opportunités distinctes.

## Causes vérifiables, contre-exemples et décisions

### Addendum RAIL : slot A* unique et constructibilité 1972–1974

L'audit de la **campagne FUNNEL instrumentée** (à ne pas joindre événementiellement à r2 malgré le SHA du bundle commun) prouve l'occupation exclusive de `_railSearch` pour de longues périodes. Graine100 : primaire `37055→35961` choisie le **23/03/1972**, recherchée jusqu'au **19/09/1973**, soit **535 jours et 10 000 itérations**, clôturée `ABND cap` (11 861 691 fenêtres de tranche), refus `search_in_progress` sur d'autres candidats pendant ce temps ; deuxième OD `50491→58979` réussie en octobre 1973 (915 itérations/22 jours, chantier 46 040 £, ligne nette ensuite). Graine999 : A* commencée le **01/12/1972**, 30 occurrences de `search_in_progress` en 1973 et **zéro tentative RAIL terminée cette année** dans FUNNEL ; la recherche ne finit `OK` qu'au **27/07/1974** après 602 jours, suivie d'un chantier réussi en août. Graine42 : recherche RAIL OK (639 itérations/18 jours) et chantier 47 953 £ en mai 1973, une ligne nette début juin. Aucun `RAIL_ATTEMPT SITEA/TRKFAIL` exposé dans ces trois parties, ce qui ne renseigne pas sur les OD jamais tentées.

**Causalité établie :** recherche sérielle, latence et blocage de l'accès de *nouvelles* OD à l'unique slot A*. **Causalité économique non établie :** aucune alternative bloquée n'a été certifiée simultanément finançable, admissible, achevable géométriquement et profitable en construction réelle ; 9 rangs RAIL 999 de décembre 1973 partagent une même origine, pas 9 routes indépendantes. Une ligne annoncée `rail_aff` par P5 après dispatch ou un devis B6 ne vaut pas un build réussi. Sans ce contrefactuel, aucun changement N=2, cap/daycap, score, priorité ou abandon de l'A* n'est autorisé ; ces familles incluent des variantes déjà rejetées. Suite probante : sonde passive d'exposition des OD réellement bloquées, capture d'état gelé au blocage, replay géométrique de l'alternative et du coût d'opportunité, puis **seulement si exposé** une variante OFF et portes A40×3/B20×10. Ce diagnostic ne déplace pas le premier déficit de profit observé, dès **02/1971** pour la graine999 sur le témoin sans sonde.

La qualification séparée de la double vérification d'abandon dans `projects` donne également **NON DÉMONTRÉ, OFF** après 20×10 : [rapport](p0_abandon_second_check_qualification_20261012.md). La vitesse locale du contrôle ne peut expliquer la stagnation de 1973.

### Addendum 20×10 : contributions observées des véhicules actifs par mode

Un dépouillement indépendant des 20 graines appariées C66 `p0_abandon_skip_b20x10_20261012`, **seul bras OFF** et même partie Opex/AAA par graine, ajoute une séparation financière descriptive. La valeur est la **somme des profits depuis le début de l'année des véhicules actifs reconnus par leur service dans la sauvegarde de décembre**, **pas** le `profit_year` comptable sur les quatre derniers trimestres ; gares, intérêts, infrastructures et effets indirects des feeders n'y sont pas attribués. Analyseur `sweeps/analyse_p0_active_mode_profit_20261012.py`, quatre tests unitaires verts, [résultat archivé](../evidence/review/p0_projects_conversion_20261012/p0_abandon_ref_active_mode_profit_20261012.json). En 1973, la graine12345 est exclue des deux compagnies faute de résolution complète chez AAA (19 paires conservées).

| Profit véhicule actif moyen depuis janvier, bras OFF | Opex AIR | AAA AIR | Opex RAIL | AAA RAIL | Opex ROAD | AAA ROAD |
|---|---:|---:|---:|---:|---:|---:|
| 1971, 20 paires | 1 339 645 £ | 1 337 839 £ | 48 220 £ | 45 101 £ | 2 892 £ | 3 878 £ |
| 1972, 20 paires | 1 696 845 £ | 1 499 150 £ | 62 429 £ | 265 348 £ | 4 187 £ | −1 797 £ |
| 1973, **19 paires** | **1 684 989 £** | **1 916 189 £** | **73 303 £** | **425 147 £** | **4 568 £** | **−12 219 £** |

Pour **les mêmes 19 graines** présentes en 1972 et 1973, variation de cette somme des profits des véhicules actifs : Opex AIR **−32 299 £**, RAIL **+10 958 £**, ROAD **+161 £** ; AAA AIR **+410 613 £**, RAIL **+152 172 £**, ROAD **−10 584 £**. La divergence 1973 comporte donc une **accélération des profits des véhicules AIR et RAIL d'AAA**, alors que la contribution AIR observée d'Opex plafonne. La multiplication des services ROAD AAA ne correspond pas à un profit direct positif de ses véhicules ROAD dans ce périmètre ; ils peuvent toutefois alimenter des services ou des villes et créer des effets indirects. **Cela renforce le diagnostic descriptif de stagnation de rendement AIR/RAIL, sans identifier le projet physique alternatif constructible ni prouver la cause unique de l'écart comptable.**

**Cohortes d'avions réellement présents aux deux clôtures annuelles :** analyse indépendante `sweeps/analyse_p0_air_cohort_20x10_20261012.py` (4 contrats hôte, dont refus des doublons et contrôle des OD), rapports [1971→1972](../evidence/review/p0_projects_conversion_20261012/p0_abandon_ref_air_cohort_1972_20261012.json) et [1972→1973 avec stabilité des liaisons](../evidence/review/p0_projects_conversion_20261012/p0_abandon_ref_air_cohort_1973_v2_20261012.json). Sur les 19 graines comparables en 1973, les **mêmes identifiants d'avions** survivants de décembre 1972 montrent **−254 318 £/graine** de résultat véhicule YTD pour Opex contre **+346 266 £** pour AAA. **18/19 graines** Opex présentent une baisse, 18/19 AAA une hausse. Ce n'est **pas** uniquement la dilution de l'agrégat par de nouveaux véhicules moins mûrs : 29,13 % des avions Opex de décembre 1973 n'étaient pas observés l'année précédente, contre 28,73 % chez AAA.

La quasi-totalité des survivants conserve aussi **la même paire de gares et de villes**, donc la baisse ne provient presque pas de réaffectations : en moyenne, **55,000/55,053 avions Opex (99,9 %)** et **26,579/26,632 AAA (99,8 %)** conservent leur marché et leur paire de StationID. Le résultat des seuls avions Opex demeurés sur ces gares recule de **252 998 £/graine**, contre **+350 178 £** chez AAA, avec respectivement 18/19 baisses et 18/19 hausses. **En 1972** (20 paires), les cohortes d'Opex encore présentes depuis 1971 gagnaient **+55 951 £/graine**, AAA **+192 666 £** ; le recul des survivants Opex constitue donc une **rupture du régime 1973** sur ce banc. Ces observations sont sélectionnées sur la survie des identifiants et ne prouvent pas *pourquoi* les routes se dégradent (croissance de flottes au même OD, quantité de cargo, recettes tarifaires, concurrence, etc.). Les `max_waiting_cargo` STNN sont le **maximum depuis le dernier calcul de note**, pas le cargo en attente instantané, et ne mesurent pas directement les passagers transportés.

**Regroupement par augmentation nette de flotte sur la même liaison, 19/19 graines :** nouvel analyseur `sweeps/analyse_p0_air_fleet_net_growth_n19_20261012.py` et trois tests hôte verts, [résultat apparié N19](../evidence/review/p0_projects_conversion_20261012/p0_abandon_ref_air_net_growth_n19_1973_20261012.json). Sur le **seul bras OFF du B20×10**, avec même paire StationID entre décembre1972 et décembre1973 et mêmes identifiants d'avions *déjà présents* des deux côtés, Opex compte **310 liaisons dont la flotte active NETTE a augmenté** / **434 vieux avions survivants** : ils perdent au total **−5 104 900 £ de profit véhicule YTD**, soit **−11 762 £ par ancien avion** et **19/19 graines** avec total négatif dans ce groupe. Sur **416 liaisons à flotte inchangée** / **599 anciens avions**, gain global **+449 784 £**, soit **+751 £/ancien avion** (10 graines positives, 9 négatives). AAA : 50 liaisons agrandies / 76 avions survivants **+15 498 £ par avion** ; 182 stables / 422 anciens **+12 788 £ par avion**. Les contractions Opex sont seulement 8 services/12 survivants, échantillon trop limité.

Ce résultat élargit considérablement l'exposition d'une **association entre renfort de flotte AIR et rendement affaibli des appareils historiques Opex**, mais **ne démontre toujours pas que le renfort a *causé* la perte** : les acquisitions répondent elles-mêmes à une demande variable, la concurrence et les ratings changent, les dates exactes d'achat entre décembre et décembre sont inconnues, les services fermés sont exclus et aucun débit PASS réel n'est mesuré dans le B. Ne pas prescrire de plafond de renfort arbitraire. Une piste économique indépendante **déjà codée mais OFF** est `c121_air_visible_competition` : son estimation NoAI de capture adverse améliore la prédiction mensuelle sur des graines réservées (octobre8), mais ses effets de projet neuf/hub empêchent d'en attribuer un résultat économique au seul `air_fleet`. Une qualification C66 comportementale distincte, pré-enregistrée dans `results/p0_visible_competition_stage_20261012/docs/p0_visible_competition_gateA_20261012.md`, est nécessaire avant tout usage et ne rouvre pas le flag différent `c121_visible_flux`, rejeté.

### Précisions AIR et contrefactuel RAIL

Dans la campagne FUNNEL seed999, les 78 refus `batch_plan_dead` de 1973 sont concentrés en janvier et juin, mais les mêmes passages produisent ensuite **13 lignes AIR nettes** (7 puis 6). Le toggle **`ac04_hub_usage_gate=1` déjà adopté** y est actif : les anciens hubs saturés « orphelins » exposés avant AC04-A v3 ne peuvent donc pas être présumés responsables de ces 78 refus. `OpexAirBatchPlanStillLive` mélange recovery, extrémités désormais servies, second slot, hub réutilisé sans capacité et OD déjà réalisée ; chaque refus est **avant** devis cash/constructeur. Un shadow des sous-motifs est requis avant tout nouveau correctif économique ; ne pas recycler AC04 v1/v2 ni la purge V144 rejetés.

Pour RAIL, la sauvegarde `.sav` annuelle/mensuelle ne reconstitue **pas** le moment de blocage A* : `persist.nut` persiste `railSearchPending`, **ni pathfinder, ni projet primaire ni portefeuille**, puis `Load` met `_railSearch=null` et régénère le portefeuille. Les campagnes r2/FUNNEL n'ont conservé aucune sauvegarde brute. Un replay contrefactuel du même tick nécessiterait une capture/injection expérimentale beaucoup plus fine ; **ne pas présenter un nouveau `-g save.sav` comme une branche équivalente de l'A* initial**. Cette limite rend la causalité économique encore **NON DÉMONTRÉE** malgré la réalité du blocage sériel.

- **Trésorerie/entrée vide** : au moins un passage graine100 1973 oppose un devis de fret RAIL plus élevé que le budget ; aucune preuve que plus d'opcodes permettrait de bâtir cette ligne. La graine42 1972 est dominée par l'entrée de vivier vide et les scans `air_fleet`, pas par la sous-fonction `select.incremental` : 22 appels/87 alternatives/~0,120 M dans le profil antérieur.
- **Occupation de l'ordonnanceur / latence** : graine999 1973 est l'extrême opposé : portefeuille visible, très peu de passages, une tentative très longue, nouvelles lignes nettes rares. Le résumé `stop=marginal_floor` est calculé *après* passage ; il ne prouve pas que le projet classé premier ait été bloqué par un seuil. Le délai et l'attente incluse sont réels, mais pas attribués à un seul appel Squirrel éliminable.
- **Hub saturé AIR recyclé** : autopsie historique de `batch_plan_dead` = hub déjà 3/3 réintroduit comme orphelin et repris en `rank0`. **Mécanisme avéré**, mais correction amont AC04-A v2 et purge aval V144 **déjà rejetées**. Ne pas les relancer sous un nouveau nom. Toute proposition distincte (filtre temporaire de sélection de hub réutilisé saturé sans purger le cache) exige d'abord preuve d'exposition sur le chemin courant, contrôle d'une alternative réellement réalisable, puis porte A40×3 et B20×10 suivant `AGENTS.md`.
- **Redondance CPU strictement établie** : double `OpexCandidateIsAbandoned(p,abandonedPairs)` consécutif lors de l'actualisation incrémentale (`projects_update.nut:115` puis `projects_generation.nut:357` via `:505`). Ses deux entrées ne changent pas entre les deux appels. Candidat mécanique sûr à tester sous flag OFF si le coût intrinsèque est visible ; **pas une cause démontrée de stagnation**. Les contrôles constructibilité AIR, K_dec, C76, V141 et `OpexFilterAirAlternativesStillValid` ne peuvent pas être court-circuités sans preuve de même état vivant.

### Diagnostic AIR des vetos en moteur — sous-motifs identifiés

La sonde P0 `p0_air_live_veto_reason_shadow=0|1` a été isolée dans
`results/p0_air_veto_shadow_stage_20261012`, avec trois overlays C121
byte-identiques au stage causal. La garde `OpexAirBatchPlanStillLive` reste
strictement identique ; le code diagnostique ON s'exécute *après* un retour
`false`, jamais pour modifier une décision. 149/149 tests hôte verts, puis
smoke OFF/ON **2/2 sain** (graine42×1) et diagnostic OFF/ON **6/6 sains**
(graines42,100,999 ×5 ans), 0 erreur Squirrel, bundle C66 gelé
`c80f601f86e0836a0e435fcd4934c04776e2f8dd95f2eb345b1f93d2af0b3161`.
Les motifs sous ON capturés en 1973 sont :

| Seed | Refus AIR capturés | OD+type d'arm distincts | Premier motif de veto |
|---|---:|---:|---|
| 42 | **0** | **0** | aucun motif échantillonné |
| 100 | **26** | **14** | 24 `capA`, 2 `capB` ; `linkedOD` simultané 12 fois |
| 999 | **20** | **20** | 18 `capA`, 2 `capB` |

Ces refus sont des **hubs à leur limite physique de routes au moment du
recontrôle**, non des faux refus établis. L'échantillon est **limité à
12 logs/passe et aux rangs 0–11** : zéro sur la graine42 ne prouve
pas zéro veto global. Dans un lot où un chantier AIR vient d'aboutir,
un hub nouvellement saturé peut légitimement invalider les projets suivants.
Aucun rejet ne prouve que l'OD était encore finançable, physiquement
constructible et rentable en alternative. **Aucun nouveau seuil de capacité,
purge ou changement de priorité ne se justifie** par ces faits.

La sonde ON est elle-même **intrusive et économiquement non neutre** : sur
trois graines, profit final 1974 ON−OFF **−148 490 £/an** (n=3),
`diagnostic_only`, sans prétention de test de politique. On n'apparie ni
événements ON/OFF, ni avec le FUNNEL historique `04af961`. Résultat source
avec premier motif et raisons simultanées
`evidence/review/p0_projects_conversion_20261012/p0_air_live_veto_shadow_diag3x5_analysis.json`
(SHA256 `ce4656e5bda09b3617c03d6caa0e8ecd8712a697830a0725e7740ef4ffb690cf`) ;
analyseur `sweeps/analyse_p0_air_veto_shadow_20261012.py` quatre tests PASS,
manifeste et logs moteur archivés dans le stage. Flag OFF et aucun portage.

**Verdict actuel de l'autopsie :** mécanismes **partiels prouvés** (cash insuffisant sur certains épisodes, attente longue et cadence, hub fantôme historique corrigé par AC04-A v3, contraintes de capacité actuelles réelles, domination AAA multimodale et recul de rendement des avions Opex sur les mêmes OD). **Cause transactionnelle unique du déficit 1973 non démontrée** et aucun correctif adopté. Les suites doivent privilégier une preuve qu'un projet concurrent était simultanément *finançable, valide, constructible* et écarté avant d'en changer la sélection ou le scheduler. TopK demeure OFF et classé NON DÉMONTRÉ ; `air_fleet_dirty_sched`, les formules RAIL simples et V142/V143 restent clos.

## Fichiers et reproduction

Scripts indépendants et tests hôte : `sweeps/analyse_p0_conversion_funnel_20261012.py`, `test_analyse_p0_conversion_funnel_20261012.py` (6 verts), `sweeps/analyse_p0_live_trace_20261012.py`, `test_analyse_p0_live_trace_20261012.py` (3 verts). Archive : `evidence/review/p0_projects_conversion_20261012/` avec JSON C66 de 3,7 Mo, manifeste, reconstructions descriptives, diff source du stage. Logs complets et bundle figé dans le worktree `results/p0_projects_causal_stage_20261012/results/` (ignorés Git). L'annexe `live_trace_3x5.json` garde les rejets par mois/graines ; `historical_funnel_5seeds.json` garde cinq graines, trois ans et les limitations de source.

Les coûts d'une nouvelle campagne qualifiante seront engagés **seulement après exposition et correctif isolé**, une campagne Docker à la fois, au plus 10 CPU/10 workers. Aucun commit/push.
