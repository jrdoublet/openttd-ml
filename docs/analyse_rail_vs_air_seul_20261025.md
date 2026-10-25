# Références RAIL SEUL et AIR SEUL — OpexAI contre AAAHogEx (25/10/2026)

## Décision et périmètre

**Deux références descriptives C66.3 terminées, sans porte A/B ni décision d'adoption.** Sur le `master` **`85c88c8a52d11a77e577a12c05456a5192355cff`**, OpenTTD 15.3 / OpenGFX 7.1, carte tempérée **256²**, départ 1970, **40 graines appariées × 5 ans** (1970–1974) pour chaque mode ; OpexAI et AAAHogEx jouent le même monde dans chaque partie. Graine 73 écartée au protocole existant et remplacée par **373684** ; les 40 graines figurent dans `sweeps/run_modal_defaults_40x5_pc.sh`. Une politique OpexAI et un seul duel partagé par graine : **pas de variante, pas de comparaison ON/OFF, pas de règle `gain_short` ou `non_erosion`**.

| Banc | OpexAI (`--reference`, autres politiques au défaut master) | Réglages AAAHogEx forcés à 1 |
|---|---|---|
| RAIL SEUL | `OpexAI[mode_air=0,mode_road=0,mode_water=0]` | `disable_veh_aircraft`, `disable_veh_roadveh`, `disable_veh_tram`, `disable_veh_ship` |
| AIR SEUL | `OpexAI[mode_rail=0,mode_road=0,mode_water=0]` | `disable_veh_train`, `disable_veh_roadveh`, `disable_veh_tram`, `disable_veh_ship` |

Les interrupteurs de mode sont **la seule dérogation stratégique** aux défauts du master ; notamment **multicargo=2, V275/V294/V295/V301 et FIN-PARTIE** restent aux défauts existants. Le harnais injecte son `probes=2` habituel (panneaux uniquement ; **pas** `decision_log=1`) et `--script-debug`. `--line-telemetry --line-telemetry-monthly --station-supply-telemetry` lisent passivement les sauvegardes, sans commandes supplémentaires de l'IA. **9 workers, 9 CPU, 8 Gio**, conteneur Docker unique : RAIL terminé puis AIR démarré après vérification de Docker vide. Même bundle SHA256 pour les deux : **`0bde1bde0de7a437c4365432d5c45be6d2becae0318b84dbb57e17376dae1c7d`**.

| Santé | RAIL SEUL | AIR SEUL |
|---|---:|---:|
| Duels / entreprises / paires de graines | 40 / 80 / 40 | 40 / 80 / 40 |
| `failed_runs` / erreurs Squirrel dans 40 journaux | **0 / 0** | **0 / 0** |
| Statuts de jeu | 25 `complete`, **15 `stagnation_suspect`** (diagnostiques, horizon atteint, pas un `failed_run`) | 40 `complete` |
| Décembres valides dans JSONL (5 ans × 40 graines × 2 IA) | 400/400 | 400/400 |
| Véhicules attribués à une ligne en décembre 1974 | 100 % dans les deux IA | 100 % dans les deux IA |
| Snapshots mensuels de ligne invalides | 0 | 0 |
| Durée manifeste → résultat JSON (approximation) | **7,25 min** | **7,30 min** |

> Attention : `stagnation_suspect` signale une trajectoire Opex/AAA à examiner, **pas** une erreur de script ou une partie tronquée ici. Les 40 mondes rail demeurent dans le bilan descriptif, sans sélection a posteriori de graines favorables.

## 1. Résultat économique : deux comportements opposés

Tous les profits sont en **£ par an**. `profit_year` est le résultat société calculé sur les quatre derniers trimestres clos, tandis que `profit_this_year_gbp` des lignes est le cumul net des véhicules **encore présents** dans la sauvegarde (deux concepts non identiques).

| Indicateur au bilan 1974 | RAIL Opex | RAIL AAA | AIR Opex | AIR AAA |
|---|---:|---:|---:|---:|
| Profit annuel **moyen** | **1 586 931** | **2 049 181** | **2 197 271** | **2 014 252** |
| Profit annuel **médian des 40 graines** | 1 570 244 | 1 961 593 | 2 279 100 | 1 985 784 |
| Ratio Opex/AAA **des moyennes** (par mode) | **77,44 %** | — | **109,09 %** | — |
| Moyenne des 40 ratios Opex/AAA (par mode) | 89,26 % | — | 114,52 % | — |
| Médiane des 40 ratios appariés (par mode) | **80,64 %** | — | **106,38 %** | — |
| Delta Opex − AAA moyen (par mode) | **−462 250** | — | **+183 019** | — |
| Delta apparié médian (par mode) | −330 124 | — | +135 168 | — |
| Mondes où Opex gagne / perd en `profit_year` | **6 / 34** | — | **24 / 16** | — |
| Valeur de compagnie moyenne | 2 283 291 | 2 221 244 | 7 153 692 | 5 247 091 |

### Trajectoire 1970–1974 — moyennes des 40 mondes

| Année | RAIL Opex | RAIL AAA | Ratio rail | AIR Opex | AIR AAA | Ratio air |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | 197 892 | 115 953 | **170,67 %** | 344 484 | 380 144 | **90,62 %** |
| 1971 | 648 419 | 638 703 | **101,52 %** | 1 383 650 | 1 682 323 | **82,25 %** |
| 1972 | 1 025 193 | 1 190 410 | **86,12 %** | 1 941 879 | 2 093 833 | **92,74 %** |
| 1973 | 1 396 821 | 1 635 043 | **85,43 %** | 2 051 746 | 1 995 844 | **102,80 %** |
| 1974 | 1 586 931 | 2 049 181 | **77,44 %** | 2 197 271 | 2 014 252 | **109,09 %** |

**Quand se creuse l'écart ?** Le rail Opex domine au départ (40/40 victoires en 1970), rejoint AAA en 1971 (22/40), **passe derrière dès 1972 (13/40)** et perd sur **34/40 mondes en 1974**. À l'inverse, l'air Opex est en retard en 1970–1972 (15, 8, 15 victoires) puis rejoint/dépasse AAA en **1973–1974** (22, puis 24 victoires). Le mode air est plus rentable en solo, mais **on ne peut ni additionner ces deux profits ni en extrapoler un ratio multimodal ou 1979**, car les politiques, concurrence et budgets changent avec les modes actifs.

## 2. Flottes, lignes et capital — bilan 1974

Les « lignes » sont des **groupes reconstruits passivement** par les ordres de véhicules : Opex regroupé par mode et ensemble de gares, AAA prioritairement par `AIGroup`. Les identités ne coïncident pas entre politiques et ne constituent pas des projets historiquement terminés, mais les véhicules de décembre 1974 sont tous attribués.

| Moyenne par monde en décembre 1974 | RAIL Opex | RAIL AAA | AIR Opex | AIR AAA |
|---|---:|---:|---:|---:|
| Véhicules primaires | **49,8** | 42,3 | **89,3** | 53,3 |
| Gares / aéroports exploités | **72,7** | 40,7 | 30,8 | **48,6** |
| Groupes de lignes actives | **40,2** | 22,6 | **40,4** | 25,9 |
| Profit net *véhicules présents* par ligne, moyenne | **35,3 k£** | **78,2 k£** | **47,9 k£** | **51,8 k£** |
| Profit net 1974 par **véhicule encore présent**, moyenne VEHS | **28,4 k£** | **41,8 k£** | **21,7 k£** | **25,2 k£** |
| Profit net 1974 par **véhicule encore présent**, médiane VEHS | 23,9 k£ | 35,7 k£ | 16,9 k£ | 16,0 k£ |
| Distance directe médiane entre deux gares (tuiles) | 84,1 | **93,4** | **183,2** | 152,1 |
| Valeur comptable de la flotte active regroupée | 1,112 M£ | 1,021 M£ | **3,681 M£** | 2,528 M£ |
| Trésorerie en fin d'année | 366 636 £ | **799 769 £** | **1 731 240 £** | 1 267 246 £ |
| Prêt restant en fin d'année | 750 £ | 0 £ | 12 750 £ | 0 £ |
| Notation médiane de gare, moyenne sur graines | 131,8 | **193,6** | **164,3** | 141,2 |

La valeur comptable de flotte **n'est pas le capital cumulé investi** : aucune mesure complète du coût initial des voies, quais, aéroports, terrains vendus/démolis et véhicules disparus n'est disponible pour les deux IA de façon symétrique. Les prêts et trésoreries sont des **stocks de fin de mois**, pas les flux bruts intra-mensuels. Ne pas expliquer une différence de profit par un montant de CAPEX inventé.

### RAIL : multiplicité de petits services, mais productivité fret inférieure

- À fin 1974, Opex exploite **19,13 groupes pax/courrier et 21,05 groupes fret** par monde ; AAA en a **3,85 pax/courrier et 18,75 fret**. Profit net moyen par groupe pax/courrier : **47,3 k£ Opex contre 73,5 k£ AAA** ; par groupe fret : **24,3 k£ Opex contre 79,2 k£ AAA**. Le désavantage principal est **la rentabilité du fret**, pas le nombre brut de constructions.
- Pour les **trajets directs ≥160 tuiles**, on observe **42 groupes fret Opex contre 166 AAA** sur les 40 mondes (1,05 contre 4,15 par monde). Profit véhicule net moyen **29,8 k£/groupe Opex contre 166,8 k£/groupe AAA**. Les médianes de distance rail globale, 84 contre 93 tuiles, masquent donc une **queue de fret long très profitable chez AAA**. Ces profits de lignes **ne mesurent pas le rendement du capital ni des candidats que l'IA Opex pourrait réellement construire**.
- Au **dernier trimestre clos de 1974**, livraisons moyennes de la société : **fret 2 408 unités Opex contre 4 266 AAA** (Opex ≈56 %), **passagers 4 870 contre 1 654**, **courrier 2 372 contre 719**. Cela confirme un portefeuille Opex beaucoup plus voyageurs/courrier, tandis que AAA transporte davantage de fret. Ce sont des volumes livrés au niveau société, **pas une mesure par ligne ou du taux de chargement**.
- Le décrochage devient visible dès 1972, lorsque le prêt Opex reste à **273 k£** en moyenne contre **28 k£** chez AAA, et la trésorerie à **117 k£ contre 225 k£**. En 1974, Opex a davantage de flotte comptable (1,112 contre 1,021 M£) et moins de cash (367 contre 800 k£), mais produit 462 k£/an de moins. Hypothèse compatible : **capital/temps de construction engagés sur des lignes nombreuses et faiblement productives**, tandis qu'AAA sélectionne du fret plus long et à meilleure contribution. L'hypothèse reste non causale sans devis, rentabilité et état de site par candidat.
- Les **signes de tentative rail Opex observés** sur 1970–1974 totalisent **105 `ABND`, 305 `SITEAB`, 1 `SITEA`, 13 `SITEB`, 65 `TRKFAIL` et 20 `STNFAIL`**, face à 1 608 signes `OK`. Sur 1973–1974 seuls, **234 `SITEAB` et 71 `ABND`**. Ce sont des signes de panneaux historiques, pas un journal exhaustif d'objets uniques : possibles limites de taille/rémanence, clé de tentative incomplète. **Aucun dénominateur comparable AAA** ; ne pas annoncer qu'AAA a zéro échec.

### AIR : meilleur profit total, mais avions potentiellement surdimensionnés

- Opex possède **89,25 avions contre 53,3**, pour **40,4 contre 25,9 lignes**, mais utilise **30,8 aéroports contre 48,6**. Il exploite davantage de lignes sur une infrastructure moins dispersée, avec une distance directe médiane **183 contre 152 tuiles**. En 1974, les lignes directes **≥160** représentent 32,38 groupes par monde chez Opex, 11,45 chez AAA ; profits des véhicules présents **50,1 k£ contre 71,3 k£ par groupe** sur cette tranche. Opex gagne **en volume de réseau/flotte** malgré un profit moyen par ligne inférieur.
- Capacités installées passagers (`cargo 0`) des avions actifs, **14 554 places par monde Opex contre 5 282 AAA**, mais passagers livrés au dernier trimestre : **4 417 contre 5 597** ; courrier : **1 910 contre 1 569**. Un indicateur purement descriptif est donc **0,30 vs 1,06 livraison de passager par place installée sur ce trimestre**. **Ce n'est PAS un taux de remplissage** : il ignore les vols/trajets, leurs fréquences et les rotations ; il illustre seulement le contraste parc/flux. L'offre installée ne prouve pas qu'enlever des avions améliorerait le profit.
- En air seul, Opex passe de 82,2 % du profit AAA en 1971 à **109,1 % en 1974** ; la valeur société est de **7,154 M£ contre 5,247 M£**, la trésorerie **1,731 M£ contre 1,267 M£**. Le programme AIR n'est donc **pas le déficit principal de cette comparaison monomodale**, mais son rendement par avion reste à documenter avant de financer davantage de capacité.
- Les sauvegardes n'offrent **ni taux de remplissage réel des avions, ni recettes et coûts séparés par ligne, ni une chronologie exhaustive des abandons/site errors AIR**. Les 40 journaux moteur ne comportent **aucune erreur Squirrel** ; cela **n'implique pas** zéro échec de construction AIR. Ne pas interpréter les `max_waiting_cargo` des gares comme stocks actuels ou taux de charge (ce sont des maxima historiques de note).

## 3. Dates, chantiers et qualité de mesure

- **Première ligne active observée** : rail Opex **février 1970 dans 39/40 mondes**, mars dans 1 ; rail AAA **mars dans 27**, avril dans 12, septembre dans 1. Air Opex **février dans 40/40**, AAA février dans 33, mars dans 7. Les snapshots étant mensuels, il ne s'agit que de la **première apparition dans les ordres sauvegardés** (résolution ~1 mois), **pas du délai sélection → construction → mise en service**. Les autres lignes peuvent apparaître et disparaître entre deux mois ; les infrastructures sans véhicule ne sont pas identifiées comme ligne active.
- `profit_year` société inclut des postes que le profit présent des véhicules ne représente pas ; **ne jamais égaler** somme des `profit_this_year_gbp` des véhicules et résultat annuel compagnie. La reconstruction Opex par gare et AAA par AIGroup rend aussi les ratios « profit par ligne » **descriptifs, non strictement équivalents à un nombre de projets**.
- **Taux de chargement et capital investi cumulatif : non observables** dans la configuration C66.3 choisie. Un futur instrumenteur passif symétrique devrait suivre cargo livré et cargo transporté par véhicule/trajet, capacité par trajet, nouvelles dépenses réelles des infrastructures et dates de projet. `--station-supply-telemetry` montre l'offre captée par station, pas le remplissage. Ne pas remplacer ces absences par de fausses estimations.
- **Échecs de construction** : les OR/OB/PS codés des panneaux Opex donnent des indices `ABND`, `SITE*`, `TRKFAIL`, mais peuvent être tronqués/dupliqués ; AAA n'expose pas la même clé structurée. Les sondes C50 (`probes=131072`) et C56 (`1048576`) pourraient dater `project_built`, `RAIL_COMMISSION` et dépenses, mais **n'ont pas été activées** pour ne pas modifier le profil de cette référence aux défauts. Leur utilisation imposerait un diagnostic distinct, sans modifier opportunément ces deux cohortes.

## 4. Pistes expérimentales, par potentiel de gain relatif au coût

Il n'existe **pas d'estimation causale en £/an du gain attendu** à partir de deux références sans variante. Le classement désigne **l'opportunité plausible** par rapport à l'écart observé (et non une promesse de +4 %). Chaque mécanisme nouveau demanderait un **nouveau réglage opt-in à défaut 0**, tests et exposition physique avant toute qualification. Coût estimé sur cinq (complexité développement/validation).

| Priorité | Hypothèse opt-in et preuve de la référence | Potentiel *hypothétique* | Coût | Garde contre un échec antérieur |
|---|---|---|---|---|
| **1** | **`rail_long_value_rank=0/1`** : autoriser **sélectivement** des couples fret 160–300 tuiles si devis de voie/site vérifiable et meilleur profit annuel marginal après capital/réserve ; comparer au meilleur court rail et à AIR plutôt que relever globalement une borne. **42 vs 166** groupes fret ≥160 et **29,8 vs 166,8 k£/ligne**, rail Opex/AAA **77,44 %** alors que AIR seul **109,09 %**. | **Fort mais très incertain** : déficit observable 462 k£/an en rail, non récupérable intégralement | **4/5** | **Pas V280** (extension temporelle 350 déjà `fail_primary`) ni **V294c** (A* à 400 `fail_primary_and_value_guard`). Une ouverture large/moins chère sans filtrage est précisément la politique rejetée. |
| **2** | **`rail_cargo_opportunity_rank=0/1`** : classement inter-cargos en **profit réalisé prudent par livre mobilisée et service physique utile** ; réserver la décision à un conflit réel entre un projet pax/courrier et un fret constructible, sans plancher ROI universel. Rail Opex **19,1 groupes pax** contre AAA **3,9**, mais fret livré **2 408 vs 4 266** ; en air seul Opex sait déjà faire croître ses profits à **2,197 M£**, donc l'arbitrage doit respecter les débouchés AIR en multimodal. | **Moyen/fort** si suffisamment de projets fret effectivement exécutables ; non mesuré | **3/5** | **Pas V297** « rejeter le bas ROI » (B neutre −44 k, prémisse de pente ROI invalidée par V298), ni désactivation de **V275** (déjà adopté après A/B rail seul). |
| **3** | **`air_fleet_yield_rightsize=0/1`** : sur lignes mûres, ajouter/supprimer une fréquence ou une réserve d'avion **seulement** après débit livré, marge nette de flotte et délai de service vérifiés ; ne rien changer aux premiers avions et conserver un intervalle maximal. Air Opex **89,3 avions vs 53,3**, places passagers installées **14 554 vs 5 282**, passagers livrés **4 417 vs 5 597**, mais profit **109,09 %** d'AAA ; rail à **77,44 %** souligne qu'il ne faut pas perturber l'essor AIR. | **Moyen, direction même incertaine** sans charge/rotation réelles | **3/5** | **Pas C81 full-load, AIR-GROW, N75-CAP ou AIR-LOAD-1** : ces variantes ont échoué ou n'ont pas démontré de gain. Il s'agit de capacité marginale prouvée, **sans attente forcée au dépôt**. |
| **4** | **`rail_site_fail_avoid=0/1`** : après un `SITEAB`, conserver dans une petite cache datée **la cause et les emplacements réellement refusés**, puis demander un devis de site alternatif constructible *avant* A* et sans élargir la spirale. Rail : **305 `SITEAB`** observés, **234 sur 1973–74**, en air seul aucune preuve d'un goulot équivalent ; la valeur potentielle est un coût d'opportunité rail. | **Moyen/faible** ; aucun dénombrement de lignes additionnelles physiques | **2–3/5** | **Pas V307S/R** (spirales/octants élargis et sites supplémentaires déjà négatifs), ni V294c (moins d'ABND n'a pas payé) ; prouver la réduction de refus et une ligne profitable. |
| **5** | **`good_source_cargo_qualify=0/1`** : sur fret transformé seulement, tester **un cargo GOOD distinct** d'une industrie à fort volume même si sa source possède déjà une autre gare cargo, mais uniquement sous réserve de quai, livraison acceptée et profit marginal privé supérieur à l'alternative. Les 40×5 montrent le fret Opex **2 408 unités contre 4 266 AAA**, et l'air Opex domine déjà ; les archives 20×10 comptent **33 usines distinctes** dans cinq mondes, **32 sans sortie GOOD**, mais pas 53 496 opportunités distinctes (occurrences de rejets répétées). | **Conditionnel, très incertain** ; préqualification physique nécessaire | **4/5** | **Pas GOOD simple, V233 greffes, GSP déjà prototypé, C75-REFUND ni N75 multicargo** ; éviter de réexécuter les six A40×5 nocturnes toutes `fail_primary`. |

**Aucun de ces mécanismes n'est adopté ou codé dans cette mission.** Ordre de vérification : d'abord mesure hors ligne des **routes uniques et physiquement finançables** (y compris collision des gares, secours AIR/rail, dépenses et service) ; puis code OFF/SHADOW/ON isolé, tests host et smoke 1×1 ; exposition 5×3 ou 5×5 seulement pour confirmer une ligne/avion différent, charge et dépenses réelles ; **porte A pré-enregistrée 40×5 multimodale** si gain attendu avant 1974, ou **40×3 rail seul** pour un mécanisme rail effectivement précoce, en maintenant le même code OFF/ON, les 40 graines, +4 % profit référence, Wilcoxon bilatéral p<0,05, borne basse IC95 bootstrap >0, garde valeur −5 %. **Porte B 20×10 uniquement après A `pass`**. Ne pas déplacer l'horizon après résultats ; ne pas confondre `non_erosion=pass` avec hausse significative.

### Échecs historiques explicitement contrôlés

- `docs/taches.md` et `docs/journaux/journal_2026-10-24_nuit_75pct.md` : **six A40×5 nocturnes `fail_primary`** (N75-CAP −9,14 k£/an ; GOOD −40,73 k ; AIR-GROW corrigé −23,43 k ; C75-REFUND −11,12 k ; AIR TRUE QUOTE +6,86 k ; multicargo +91,19 k, p=0,139). Multicargo a été adopté plus tard par décision explicite utilisateur, **sans requalification de A**.
- **V282** sur branche rebasée : A40×10 −15,30 k, erreur 525 **0/0** sous V301 bit2 déjà actif ; **V294c long250** : A40×3 −86,79 k, valeur −12,63 %, **B interdite**. **V280** et **V305b** n'ont pas validé les longs rails. Ne pas proposer « plus long/plus rapide » sans nouvelle logique de sélection.
- **V275 rail voyageurs** : A rail seul +635,4 k et B +791,3 k **déjà passées/adoptées dans le mode prévu** ; en multimodal, cannibalisation AIR, ne pas multiplier les passagers rail sans nouvelle preuve. **V297** (plancher ROI) B neutre, prémisse de biais corrigée par V298. **V303, V307S/R** : recherches/sites plus agressifs non qualifiés. **AIR-MONOPOLY ×2**, **C81 full-load** et **AIR-GROW** ont déjà une histoire négative ou non concluante ; pas de relance automatique.

## 5. Pièces et reproductibilité

- Script préparé **pour les deux modes** : `sweeps/run_modal_defaults_40x5_pc.sh` (`MODE=rail` puis `MODE=air`, refus de lancement lorsque Docker est occupé ou campagne déjà figée). **Aucun changement de défaut, commit, push ni merge**.
- Référence rail : `results/modal_rail_defaults_master85c88_40x5_20261025.json`, `.jsonl`, `.manifest.json`, `_engine/`, `_analysis.json`.
- Référence air : `results/modal_air_defaults_master85c88_40x5_20261025.json`, `.jsonl`, `.manifest.json`, `_engine/`, `_analysis.json`.
- Extracteur descriptif hors jeu **versionné** : `sweeps/analyse_modal_defaults_20261025.py` (lancer `python -X utf8 sweeps/analyse_modal_defaults_20261025.py` depuis la racine ou un autre répertoire ; il résout `results/` relativement au dépôt). JSON d'analyse par mode : moyennes, médianes, ratios appariés, trajectoires annuelles, lignes et véhicules par cargo/distance, trésorerie, prêts, livraisons au trimestre et signes Opex. **Les fichiers sous `results/` sont ignorés de Git et conservés localement** ; ne pas les faire passer pour un suivi de décisions causalement mesurées.
