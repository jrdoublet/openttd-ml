# ESTIM-1 + sites aériens natifs : trois duels 40×5 instrumentés (27 octobre 2026)

**Périmètre.** 40 graines identiques, 256×256, 1970–1974, OpexAI contre AAAHogEx-115 sur une même carte par partie. Les restrictions AIR/RAIL/route/eau sont identiques entre concurrents à l'intérieur de chaque mode. `estim_unifie=31` (bits 1, 2, 4, 8 et 16), `air_site_ranked=1`, `air_site_funnel=1`; les autres réglages demeurent ceux du bundle courant. `probes=67247874` active panneaux, décision, coûts, ordonnanceur, opcodes de boucle, spans, portefeuille et V309. 9 CPU, 9 workers, 8 Gio, une campagne à la fois. Bundle figé commun SHA-256 `8d40648d610ecca1abb31f419749b64228d95e7e0adc0483aa942f3ff438dbd1`; Git `57d5cde9f0af2aecf99268362180f6615d8b4860`, état local déclaré *dirty*.

**Statut : 120/120 parties appariées exploitables**, aucun échec moteur ni erreur Squirrel remontée. Des statuts `stagnation_suspect` existent (AIR 3, RAIL 4, multimodal 1) ; ils ont atteint leur horizon et restent signalés. **Ce ne sont pas des portes d'adoption ESTIM ON/OFF** : les sondes ajoutent du travail en VM et le duel ne comporte pas de référence `estim_unifie=0` sur bundle identique.

## Profit, capital, caisse et réseau fin 1974

| Mode | Opex profit annuel £ | AAA profit annuel £ | Ratio | Victoires Opex | Opex/AAA caisse £ | Opex/AAA véhicules | Opex/AAA gares | Opex/AAA lignes reconstruites |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AIR seul | 2 366 446 | 1 959 071 | **120,8 %** | 31/40 | 608 640 / 1 278 839 | 84,0 / 52,6 | 31,2 / 47,5 | ~39 / ~26 |
| RAIL seul | 1 141 568 | 2 455 277 | **46,5 %** | 2/40 | 206 987 / 1 193 183 | 40,5 / 47,4 | 66,0 / 42,5 | ~35 / ~24 |
| Multimodal | 2 738 911 | 2 926 249 | **93,6 %** | 15/40 | 721 827 / 873 879 | 104,1 / 213,4 | 70,8 / 149,9 | ~60 / ~119 |

Test des signes des profits appariés : AIR `p=0,00068`, RAIL `p<0,00001`, multimodal `p=0,15386` (Wilcoxon multimodal `p≈0,05481`). Le déficit multimodal observé n'est donc pas accompagné d'une majorité de défaites significative au seuil 5 % sur les signes. Cela ne démontre pas une neutralité économique.

En multimodal, OpexAI a une valeur moyenne de **6 325 962 £** contre **5 704 704 £** chez AAAHogEx, malgré un profit annuel de **187 338 £ inférieur**. Ces métriques sont différentes : la valeur ne remplace pas le profit. Les prêts de fin 1974 sont nuls des deux côtés en multimodal ; RAIL seul conserve en moyenne **68 000 £ de prêt OpexAI** contre 500 £ chez AAAHogEx.

Trajectoire du *profit annuel* OpexAI/AAAHogEx en 1970–1974 (k£/an, arrondis) :

| Mode | 1970 | 1971 | 1972 | 1973 | 1974 |
| --- | --- | --- | --- | --- | --- |
| AIR | 344/378 | 1 423/1 693 | 1 995/2 103 | 2 123/1 938 | 2 366/1 959 |
| RAIL | 111/132 | 444/700 | 716/1 380 | 966/1 915 | 1 142/2 455 |
| Multimodal | 360/299 | 1 567/1 329 | 2 395/1 948 | 2 510/2 516 | 2 739/2 926 |

**Effet de structure multimodal.** Fin 1974, OpexAI exploite en moyenne **78,7 avions, 22,0 trains et 3,3 véhicules routiers**, contre **40,6 avions, 27,1 trains et 145,2 véhicules routiers** chez AAAHogEx. La majorité du déficit en taille du parc concurrent se situe sur la route, pas sur l'aviation. Les comptes de gares physiques sont décodés à partir des sauvegardes ; les installations d'une même gare multimodale ne doivent pas être additionnées comme des gares distinctes. Les lignes sont groupées *à partir des ordres des véhicules*, non un registre certain de chaque projet construit.

## Où va l'argent ?

- **Charges d'exploitation annualisées observées à fin 1974** : AIR Opex −111 k£ contre AAA −67 k£ ; RAIL Opex −25 k£ contre AAA −24 k£ ; multimodal Opex −117 k£ contre AAA −89 k£. `expenses_last_year` est une valeur signée, **pas le total des constructions**. La trésorerie `money` est la caisse de fin d'année ; l'encours `current_loan` est relevé séparément.
- **RAIL : tentatives de construction** : somme du champ `RAIL_ATTEMPT.actual` connu sur 40 parties RAIL seul ≈ **99,46 M£ sur cinq ans**, soit **2,49 M£ par partie** ; en multimodal ≈ **74,70 M£** sur les quatre années observées où existent ces tentatives, avec montants inconnus distincts. Ces dépenses comprennent les essais enregistrés, potentiellement partiels/échoués ; elles **ne constituent pas une ventilation exhaustive des flux de caisse**.
- **AIR : coûts initiaux** : le champ `AIR_BUILD.cost` est le **devis** `buildPlan.capital`, pas une transaction de caisse. `ESTIM_SPEND.actual_paid` est le débit constructeur observé sur 1973–1974 seulement, à ne pas additionner aux devis. Les achats/renouvellements de véhicules, remboursements d'emprunts, recettes et dépenses courantes ne sont pas reconstituables transaction par transaction par ce seul jeu de logs. `paid_accounting=-1` signifie inconnu, jamais zéro.

**Chronologie des ouvertures et montants, multimodal, cumul des 40 parties :**

| Année | Ouvertures `AIR_BUILD` | Devis AIR de ces ouvertures (M£) | `RAIL_ATTEMPT.actual` connu (M£) |
| --- | ---: | ---: | ---: |
| 1970 | 340 | 27,87 | 0,00 (aucune tentative enregistrée) |
| 1971 | 825 | 47,10 | 4,86 |
| 1972 | 246 | 11,86 | 35,67 |
| 1973 | 54 | 2,45 | 18,47 |
| 1974 | 33 | 1,54 | 15,70 |

**Ne pas sommer les colonnes comme flux de caisse comparables.** Les devis AIR sont des coûts projetés, les montants RAIL sont des comptabilités d'essais effectivement observés, parfois partiels. En 1974 multimodal, les seuls `ESTIM_SPEND` RAIL connus totalisent **17,62 M£** contre **15,70 M£** dans `RAIL_ATTEMPT.actual` ; cette discordance demande une réconciliation par identifiant de tentative avant toute affirmation sur le coût physique *total* des chantiers.

## Pourquoi ne construit-on pas davantage ?

**AIR seul.** La sonde V309 mesure `cash_below/loops` : environ **72 % (1970), 51 % (1971), 15 % (1972), 19 % (1973), 8 % (1974)**. Le mécanisme change de nature : en 1974, 322 arrêts `k_pass`, 89 `list_end`, 1 `cash` ; le C63 relève aussi 366 `cache_exhausted` et 116 `all_unaffordable`. Les compteurs décrivent des passages/décisions répétés, pas 366 opportunités économiquement indépendantes. Le fort profit AIR résulte d'un réseau de lignes plus nombreuses que les gares, avec réemploi d'aéroports.

Les **ouvertures aériennes réussies** (`AIR_BUILD`) passent de **329 en 1970 et 853 en 1971** à **304 en 1972, 51 en 1973 et 34 en 1974** (totaux 40 parties). En multimodal la séquence correspondante est **340, 825, 246, 54, 33**. Cela prouve le ralentissement des *ouvertures* malgré la hausse de la trésorerie, indépendamment de la croissance de flotte sur les lignes existantes. Les refus répétés `AIR_FLEET` en 1974 sont notamment `already_grown_this_year` (AIR seul 12 183 passages, multi 8 914 passages), avec des codes `W` et `O` à documenter ; **ce ne sont pas autant de lignes ou d'avions refusés uniques**.

**RAIL seul.** `cash_below/loops` ≈ **41 %, 48 %, 41 %, 30 %, 14 %** sur 1970–1974. OpexAI aboutit à ~35 lignes avec seulement 40,5 trains/engins principaux, contre ~24 lignes et 47,4 véhicules chez AAA. En 1974, `RAIL_ATTEMPT` compte 224 succès, **58 `SITEAB`**, 32 `ABND`, 16 `TRKFAIL` (plus autres erreurs) ; 129 arrêts `k_pass`, 49 `cash`, 18 `marginal_floor`. La rentabilité moyenne *observée par ligne* à fin 1974 est de ~**29,5 k£ chez Opex** contre **87,4 k£ chez AAA** : la dispersion du parc et le rendement sont plus inquiétants que le seul nombre de gares. La sonde de site VPS antérieure suggère que `SITEAB` provient souvent d'un rattachement forcé, mais **ce corpus local ne prouve pas que chaque `SITEAB` a cette cause**.

**Multimodal.** V309 passe de **66 % des boucles sous coût minimal en 1970** à seulement **4,3 % en 1974**. Sur 1974 : 234 arrêts au plancher marginal `C80`, 175 `k_pass`, 57 `cash` ; 114 tentatives RAIL réussies contre **78 `SITEAB`**, 22 `ABND` et autres échecs. Les 40 parties montrent que le profit Opex dominait AAA en 1972 (+447 k£/an) mais perdait l'avantage en 1974 (−187 k£/an). En RAIL multimodal, le déficit d'ouverture/ravitaillement coexiste avec des sites physiquement refusés.

**Démarrage, route et vivier.** Sur le journal multimodal seed 42, `BOOTSTRAP_STAGE stage=4 freight=0 pax_rail=0 road=0 air=1` en janvier 1970 : malgré les modes disponibles, la phase d'initialisation autorise **AIR uniquement**, ce qui explique une part du démarrage retardé du rail/route. Les bilans `phase=vivier_year` du même jeu révèlent pour la route `produced=0` sur 1970–1973 (avec pourtant des candidats évalués certaines années). En décembre 1973, un essai rejette 42 villes à la précondition d'acceptation. Ce sont des raisons de non-production à investiguer ; augmenter artificiellement les constructions sans rendement serait contre-productif.

**Extension aux 40 graines par `C69_BOTTLENECK phase=vivier_year` :** en multimodal, le vivier ROAD compte `examined=0/0/812/2 836` et `produced=0/0/17/17` sur **1970/1971/1972/1973**. En 1973, les principaux rejets ROAD sont `origin_served=1 365` et `town_rejected=767`. Les totaux de sélection (`to_select`, `selected`) cumulent les *réévaluations du portefeuille* et peuvent être non nuls même quand la génération neuve `produced=0` ; ils ne prouvent pas autant de projets différents. En 1970, le vivier RAIL multimodal a bien produit 18 414 entrées comptabilisées mais seules 337 sélections de passage sont enregistrées, face à 16 723 sélections de passage AIR : l'activation AIR favorise largement le mode aérien. Le bilan annuel **1974** n'est pas publié avant janvier 1975, hors horizon ; **ne pas le remplacer par zéro**.

La sonde dédiée `early_build_probe` documentée sur la branche VPS `early-blocker-probe` (`525857cf`) **n'est pas disponible dans l'arbre Windows**, et ses compteurs launch/ok/fail ont un défaut de cohérence constaté antérieurement. Les constatations présentes proviennent de C63/C69, V309, ESTIM, RAIL_ATTEMPT, sauvegardes et SPAN, et non de cette sonde absente.

## Où vont les opcodes ?

Les `SPAN` sont inclusifs et imbriqués. Le lecteur attribue des **opcodes exclusifs** en retranchant les enfants immédiats ; les résidus négatifs sont tracés comme anomalies (AIR 1 275 sur 5 000 200 spans, RAIL 104 sur 1 862 581, multi 764 sur 2 828 189). Ces chiffres sont des **comptages instrumentés sur les 40 parties**, non des pourcentages exhaustifs du budget machine, et les catégories sont indicatives. Les gros postes :

| Catégorie, milliards d'opcodes exclusifs mesurés sur 40 parties | AIR | RAIL | Multimodal |
| --- | ---: | ---: | ---: |
| Sélection des projets | 2,77 | **4,86** | **3,95** |
| Orchestration diverses tâches | **3,20** | 3,85 | 3,22 |
| Génération candidats, plans AIR | 1,94 | 0,14 | 1,64 |
| Gestion / redimensionnement des flottes | 1,28 | 0,04 | 0,70 |
| Sleep / reliquat de boucle instrumenté | 1,13 | 0,97 | 0,70 |
| Construction | 0,15 | 0,94 | 0,15 |
| A* / tracés rail | 0,03 | 0,56 | 0,41 |
| Recherche explicite de sites | 0,54 | ND | 0,44 |

`AIR_SITE_SEARCH.ops/calls` est un compteur **cumulatif** par partie, jamais un poste à sommer ligne par ligne. `LOOP_OPS.sleep_left` et `V309.sleep_ops` sont des budgets non consommés, pas automatiquement du CPU inutile ; `stable_unfunded_ops` est une mesure des revérifications en attente de financement. Les sondes elles-mêmes peuvent déplacer les décisions en modifiant les délais/opcodes.

## Suites à tester, sans changement de défaut

1. **Route / phases de génération** : séparer `mode_road=1` (autorisé) de `doRoad=0` durant `C121_CATALOG_FIRST_YEAR_ACTIVE` et du défaut de production 1971–1974 ; décomposer rejets par mode, concurrence avec AIR, score/ROI, distance, acceptation des villes. C'est la piste la plus importante pour l'écart de flotte multimodal.
2. **Rail : rentabilité et construction** : instrumenter source du capital net *et* profit réellement réalisé par ligne/âge, coût de gare neuve versus partage, refus SITEAB et A*, taux d'équipement de lignes en locomotives, sans confondre lignes/gares/véhicules ; le coût observé en 1974 n'explique pas à lui seul le déficit annuel de profit.
3. **AIR : vivier et renfort** : mesurer la différence entre projets possibles, disponibles, filtrés et effectivement construits après 1972 ; conserver le premier classement ESTIM mensuel (1973–1974 seulement) distinct des passages complets C63/C69, et les refus de flotte cumulés distincts des lignes uniques.
4. **Expériences isolées** : changer au plus un mécanisme à la fois, défaut 0, comparer `estim_unifie=0/31` sur bundle fixé et budget de sondes symétrique, puis portes A 40×3 / B 20×10 selon le protocole si l'on souhaite adopter. Les bancs présents sont diagnostiques, pas des qualifications de ces changements.

## Reproductibilité et fichiers

- Lanceur : `sweeps/run_estim1_sites_40x5_pc.ps1` (ne pas relancer avec le même suffixe sans destination neuve).
- Lecteur et tests : `sweeps/analyse_estim_sites_40x5.py`, `sweeps/test_analyse_estim_sites_40x5.py`.
- Campagnes : `results/estim1_sites_diag_{air,rail,multi}_40x5_20261027.{json,jsonl,manifest.json}`, logs dans les répertoires de même nom suffixés `_engine` ; bilan `results/estim1_sites_diag_summary_20261027.{json,md}`.
- Particularités : les modes ont même bundle, mêmes 40 graines, mais **modes et AAAHogEx différents** ; le différentiel entre campagnes ne constitue pas à lui seul un effet causal d'ESTIM ou des sites aériens. La sonde de décison `ESTIM_PASS` couvre 1973–1974 uniquement. Les résultats bruts restent locaux sous `results/`.
