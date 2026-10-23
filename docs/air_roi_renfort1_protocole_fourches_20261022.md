# AIR-ROI-RENFORT-1 — étape 2a : protocole pré-enregistré des fourches (22/10/2026)

> **ARCHIVE HISTORIQUE — PROTOCOLE WIP NON INTÉGRÉ (22/10/2026).** Ce document conserve les intentions, critères et amendements préenregistrés sur le `master` local HEAD `41031a7f`, avec du Squirrel expérimental non commité. Les fourches transactionnelles initiales ont rencontré un blocage, puis les campagnes ITT ont été examinées séparément et sont restées **non qualifiantes causalement et économiquement**. Aucune méthode, option comportementale ou modification de défaut décrite ici n'est **adoptée** dans la branche d'archive. Les chemins `results/` désignent uniquement les preuves **locales du WIP non archivées ici** ; certains scripts d'analyse Python sont déjà versionnés dans le dépôt.

**Statut : protocole documentaire uniquement, aucune fourche exécutée.** Ce texte fige les unités d'observation, la sélection des épisodes, le témoin AA/AA, les interventions et les mesures **avant** toute collecte contrefactuelle. Il prolonge [l'audit de l'étape 1](air_roi_renfort1_audit_20261022.md) et la tâche [AIR-ROI-RENFORT-1](taches.md). Il ne qualifie aucun coefficient V161/C70, score C69 ou changement de priorité C77. L'étape 3 de calibration reste conditionnée à des fourches valides et à un contrôle hors échantillon.

## 1. Question, unité et limites de l'historique

L'unité causale est **la décision de financer exactement un avion supplémentaire** sur une ligne AIR OpexAI existante, à un instant de transaction identifié (`t0`), dans un monde partagé avec AAAHogEx. L'effet cherché est le changement de résultat **de la compagnie et du voisinage de la ligne**, 24 mois après cette décision. La ligne entière et ses avions déjà présents continuent de produire dans les deux bras ; leur profit complet ne constitue jamais le profit du nouvel avion.

Le panel rétrospectif 5 graines × 6 ans comprend 2 388 tentatives C121, 311 achats de croissance, dont 141 clichés d'achat à tick/caisse stables, mais **aucun** `vehCount` préachat exact, relevé de charge/capacité préachat, coût physique unitaire ou rendement marginal contrefactuel (`air_roi_renfort1_audit_20261022.md`). Les 116 rapprochements C121 à deux ans, la médiane `+3 182,5 £/an` de variation du profit de **ligne**, les `16,73 ‰` médians après V161 et les valeurs pré-V161 ne sont que des diagnostics, non des observations causales. Les logs passés ne fournissent pas automatiquement la sauvegarde exactement avant l'achat : **aucune fourche ne peut être reconstituée en prétendant que ces sauvegardes existent**.

Un renfort C121/V161 est distinct d'un remplacement V252, d'une reconstruction après perte ou d'une nouvelle liaison AIR. Les trois derniers cas sont des **cohortes distinctes, hors critère primaire** de cette étude (`AIR-ROI-RENOUVELLEMENT-1`, `AIR-ROI-LIGNE-1`). `OpexAirAddPlane` peut choisir un moteur différent, effectuer un repli, échouer, ou renvoyer un remplacement ; seule l'issue `added=1`, `replaced=0`, avec un VehicleID réellement vivant et rattaché à la ligne, compte comme renfort exécuté.

## 2. Épisodes et classes figés avant exposition

### 2.1 Registre exhaustif des occasions

Créer, lors d'une **future** collecte dédiée, une ligne de registre pour **toute tentative** `mode=fleet` effectivement arrivée dans `_tryBuildFleetProject`, qu'elle aboutisse ou non : `episode_id = hash(bundle, seed, source_save_sha256, tick_t0, cycle, lineId, tentative_ordinal)`. Garder un numéro de tentative dans la partie ; la même ligne candidate sur dix ticks ne représente pas dix lignes ni dix graines indépendantes. Chaque épisode porte `candidate`, `pretrade_valid`, `checkpoint_exact`, `aa_valid`, `intervention_reached`, `built`, `censor_reason`. Ne pas effacer les échecs ou doublons ; compter séparément épisodes, sauvegardes, lignes, graines et achats. Les mesures répétées d'une même source ou d'une même graine constituent une grappe, jamais des observations indépendantes.

Le registre de classes est fixé par les valeurs **lues avant transaction**, sans utiliser les conséquences du renfort :

| Axe | Classes pré-enregistrées | Provenance et règle |
|---|---|---|
| Canal d'exécution | renfort C121 réussi ; refus initial (stale, scrapping, caisse) ; constructeur échoué ; `REPLACE`/rééquipement ; V252 | verdict du hook et retour constructeur ; les échecs restent dans le dénominateur d'exposition |
| Branche du profit | sous `targetAirPlanes` avec `c121MarginalSamples=0` (cold-start) ; sous cible avec ≥1 échantillon ; repli `lastProfit/have` ; repli prédictif | `projects_builders.nut:143-206` ; publier branche effective, pas une branche déduite du ROI |
| Source V161 et C70 | `prior` / `model` ; C70 applicable / exempté | `v161Source`, `profitIsObserved`, `v161Calibrate`, provenance du score contemporain |
| Flotte vivante avant `t0` | 1 ; 2 ; 3–4 ; ≥5 avions ; inconnue | compter les VehicleID vivants, puis recouper `line.vehCount` et `entry.baseVehicles` ; un ancien compteur de renforts n'est **pas** ce nombre |
| Âge de la ligne | <24 mois ; ≥24 mois ; inconnu | date de construction antérieure à `t0`, sans âge reconstruit après coup |
| Architecture | `newpair` ; `hubsite` ; `hubhub` ; autre/inconnue | `c121Arm` conservé avant le choix, stations et cargo |
| Voisinage concurrent | `v161Neighbours=0` ; ≥1 ; inconnu | compte avant achat ; distinguer voisins propres des avions AAAHogEx présents |
| Charge et besoin de capacité | taux historique d'occupation <70 % ; 70–<90 % ; ≥90 % ; inconnu ; attente aux stations nulle/positive/inconnue | fenêtre historique close avant `t0` (définition, unités, capacité et couverture publiées), jamais statistique construite avec les 24 mois futurs ; pas d'occupation inventée si données absentes |
| Financement/portefeuille | finançable après réserve ; insuffisant ; inconnue ; tier C77 et rang effectif | caisse, emprunt, réserve, `finance`, `K_dec` **avec tick de sélection** ; ne pas confondre score stocké et re-sélection instantanée |
| Exposition au contrefactuel | même-save validé ; sauvegarde non fidèle ; AA instable ; achat non exécuté ; commande exécutée | raisons exclusives avec horodatage et preuve ; garder les nombres par graine |

Les cases `inconnu` sont obligatoires si la mesure préachat manque. Une saturation estimée **après** construction, un nombre d'appareils déduit des achats du log, ou un ROI issu d'un rapport annuel futur ne deviennent pas des covariables prétraitement. Les interactions nombreuses (type × âge × charge × flotte × voisins) resteront descriptives tant que leurs effectifs par **graine** ne permettent pas un test fiable.

### 2.2 Critères d'exposition et choix des sauvegardes

Le **registre d'exposition** retient tous les candidats rencontrés ; un épisode devient **éligible à la fourche primaire** si et seulement si, avant de connaître les résultats à 24 mois :

1. ligne AIR déjà exploitée, au moins un avion vivant avant `t0`, sans liquidation ; `entry.want=1`, `baseVehicles` égal à la flotte active, `targetAirPlanes` et branche du profit renseignés ; candidat valide dans le portefeuille courant et tiers/rang identifiés ; transaction et financement autorisés au même tick ; aucun autre chantier en cours sur cette ligne au point de coupure ;
2. sauvegarde **du monde et de l'IA** disponible au plus près de l'instant précédant **cette** commande, avec date, tick, état de la ligne, des sociétés, des véhicules, de la caisse et état décisionnel reconstituable ; la reprise témoin doit reproduire la même tentative, le même lineId, le même moteur candidat et le même résultat **sans intervention** ;
3. le mécanisme de comparaison peut agir **une seule fois** au point transactionnel précis avant `OpexAirAddPlane` (sans déplacer la sélection) ; preuve de l'achat effectif dans le bras `RENFORT` et de l'absence de cet achat dans `SANS_RENFORT` ; pas de repli non expliqué vers un remplacement, ni de changement d'autres commandes au tick antérieur ;
4. contrôle AA/AA économique intégralement validé selon le §3. Un échec sur l'un des points est journalisé dans la cohorte des **non qualifiables**, sans remplacer l'épisode par une graine favorable.

L'ordre d'inscription est déterministe : graines prospectives **42, 100, 999, 1234, 5678** dans cet ordre ; au sein de chacune, première tentative admissible chronologiquement sur chaque `lineId`, **deux sauvegardes au maximum par graine** (maximum **10 épisodes**), en évitant deux checkpoints d'une même ligne sur une même graine. En cas de zéro événement, enregistrer `not_exposed` ; **ne pas élargir après consultation des deltas**. Tout nouvel échantillon exige un protocole daté distinct, avec graines disjointes pour la validation. Les 311 succès historiques servent à connaître la fréquence possible, pas à choisir après coup un gagnant. Les classes restent figées même si elles ont peu d'épisodes ; elles peuvent rester `insufficient_data`.

Une sauvegarde seulement mensuelle, déjà **après** la commande, ou qui déclenche au rechargement une régénération modifiant le portefeuille avant l'épisode n'est pas une preuve « même instant ». Une fourche à partir d'un tel point est classée `coarse_checkpoint_diagnostic` et **exclue** du résultat marginal primaire. Le besoin d'instrumenter un point d'arrêt exact est un prérequis technique, **pas une fonctionnalité déjà disponible**.

## 3. Source identique et contrôle AA/AA obligatoire

Pour chaque épisode, figer un unique `.sav` original, son SHA256, son manifeste et un bundle de code strictement identique pour les **quatre reprises** (`AA0`, `AA1`, `RENFORT`, `SANS_RENFORT`). Enregistrer SHA/branche/état local, identité et hachage du dossier `ai/`, versions OpenTTD/OpenTTDLab/NoAI, NewGRF/OpenGFX, carte, graine, paramètres économiques, adversaire, ordre des compagnies, options serveur et `AIController`/réglages effectifs. Copier **octet pour octet** la même sauvegarde dans les quatre environnements, sans modifier son contenu. La configuration d'AI doit comporter uniquement les écarts réels aux défauts (limite `openttd.cfg` d'environ 1 024 caractères pour `[ai_players]`). Le retour de `Load()` (`LOAD_RECONCILE`), C69/C75, C70, le vivier régénéré et la recherche rail reprise doivent être vérifiés avant le point d'achat.

Le moteur historique `-vnull` a créé une **compagnie fantôme**, perturbé RNG et économie dans d'anciennes fourches C77. Utiliser le **mode serveur dédié** avec les deux compagnies effectives OpexAI/AAAHogEx, config de clients compatible et sans troisième compagnie ; vérifier la liste des sociétés et les prêts dès le tick de reprise. L'outillage historique `results/v217_autopsy_841478_fork_stage_20261016/sweeps/c77_savefork_host_20261013.py` fournit une piste technique de reprise, **pas une garantie** de point d'arrêt exact ou de comparabilité AIR : auditer et adapter avant tout run, sans le réemployer comme test « déjà validé ».

Les bras `AA0` et `AA1` rechargent la **même source**, la **même version de l'IA** et la **même instrumentation**. Ils passent par le même crochet de décision en mode neutre (aucun achat forcé, aucune commande évitée). L'instrumentation de mesure ne doit pas écrire des logs qui provoquent une suspension **avant** le constructeur ; utiliser des captures préachat en mémoire et publier après l'exécution, avec `tick_before`, `tick_ready`, `cash_before`, `cash_ready`. Toute différence d'opcodes ou d'activation de sonde entre bras rend le test invalide. `decision_log` et probes lourdes sont désactivés pour la comparaison économique sauf preuve préalable d'identité AA/AA avec leur configuration exactement symétrique.

**Garde AA/AA à tolérance zéro** : comparer au tick source, juste avant intervention, immédiatement après la tentative et à **chaque checkpoint mensuel jusqu'à +24 mois** : date/tick, état/RNG moteur s'il est accessible, sociétés et places, cash/prêts, `company_value`, cumul et `profit_year`, avions et autres véhicules par mode et leurs identifiants/ordres, lignes/stations, réalisations et investissements, état des gares adverses. Les **deux** traces doivent être complètes, sans crash/erreur Squirrel ni épisode de compagnie fantôme, et **économiquement identiques à chacun de ces points** (valeurs numériques exactes, même inventaire et mêmes ordres, pas une simple proximité statistique). Comparer aussi hashes des sauvegardes et premières décisions/commandes si disponibles. Si l'état RNG n'est pas exportable, le noter `not_observed` et exiger la symétrie décisionnelle et économique observée ; **ne pas affirmer une égalité de RNG non mesurée**.

Une différence AA0/AA1 de 1 £, une date ou un véhicule différent, un état initial différent, un saut de tick introduit par le crochet, un `LOAD_RECONCILE` asymétrique, un tiers C77 divergent **avant** l'achat ou une branche AA manquante entraîne `aa_fail` : **arrêt des fourches causales pour cet épisode**, conservation des traces et localisation du premier écart. Une réussite AA sur une autre sauvegarde/graine ne sauve pas l'épisode fautif. Répéter le contrôle après toute modification de code, du harnais ou des paramètres.

## 4. Fourches RENFORT / SANS_RENFORT, 24 mois

Les deux bras partent du **même `.sav`** que AA0/AA1, avec même adversaire, environnement, horloge, ordre des compagnies et journalisation. Un seul dispositif d'override local au tick `t0`, dans le même code, est paramétré par le manifeste immuable (`episode_id`, `lineId`, ordinal, signature du candidat, tick source, action). **RENFORT** autorise la commande native `OpexAirAddPlane` ; **SANS_RENFORT** neutralise uniquement **cette** commande et poursuit le même cycle de tâche. Vérifier que le crochet a trouvé l'épisode attendu **une fois et une seule** ; aucune action silencieuse si la signature n'est plus admissible (refuser `trigger_mismatch`). Aucun `force` de résultat constructeur, de `VehicleID`, de trésorerie ou de projet RAIL.

La fourche mesure prioritairement l'**effet de la décision immédiate** : une commande renfort exécutée maintenant contre sa suppression ponctuelle, suivies de **24 mois d'évolution naturelle** et de concurrence avec les autres investissements. Si SANS_RENFORT rachète ultérieurement un avion sur la même ligne, conserver l'épisode et la date de rattrapage : c'est une réponse endogène à la décision initiale, pas un motif d'exclusion postérieur. La différence finale est alors un **effet de politique ponctuelle (intention de traiter)**, qui peut se diluer ; ne pas la présenter comme le rendement physique isolé d'un appareil présent 24 mois contre zéro appareil. Une éventuelle expérience de *plafond maintenu 24 mois* exige un **autre** protocole et des bras distincts, car elle intervient sur plusieurs décisions.

Le traitement valide exige `added=1`, `replaced=0`, VehicleID valide, moteur/refit, ordres et démarrage contrôlés, unité payée et rattachée au `lineId`. Si le RENFORT tombe sur `CLONE`, `ORDER`, `START`, `CASH`, un remplacement ou une absence de commande, conserver `treatment_not_delivered` et le premier motif ; ne pas attribuer un gain/perte au renfort non construit. Rapporter **deux estimands** pré-spécifiés : (i) intention de traiter sur **toutes les sources éligibles au moment du choix**, avec échecs distincts et taux de réalisation ; (ii) effet local conditionnel **parmi les renforts effectivement livrés**, explicitement sujet à sélection/validité de livraison et impropre à généraliser seul. Une divergence d'AAA **après `t0`** peut faire partie de l'effet total sur carte partagée ; toute divergence du monde **avant l'intervention validée** invalide l'attribution.

À `t0`, conserver caisse et prêts, coûts physiques, flotte et marché des deux compagnies, stations/gares, commandes, même tier C77 et `K_dec` daté, canal C121 → V161 → C70 → C69, rang, prédiction `model`/`prior`, réserve et décisions qui auraient été prises. Jusqu'à `t0 + 24 mois`, garder événements de construction/vente/perte/remplacement par `lineId`/VehicleID, prix **réels** achat/cession, carburant/maintenance/charges, revenus, amortissements, charge et capacité, commandes échouées, avances/retards, autres projets financés ou reportés (AIR, rail, route, eau), flux de caisse, dette et valeur résiduelle. Ne pas assimiler `cash_before − cash_after` à la facture sans ventilation (autres flux, prêts et ticks).

Calculer les deltas **RENFORT − SANS_RENFORT** à dates identiques :

| Endpoint | Définition pré-enregistrée et portée |
|---|---|
| **Principal, économique à +24 mois** | `Δprofit_year_Opex` à l'année terminale, calculé sur les quatre trimestres comptables complets effectivement disponibles, avec dates de trimestres conservées ; si l'année de reporting ne couvre pas la période attendue, `missing`, sans substituer le profit de ligne |
| Résultat causal de réseau | différence de profit net annualisé sur les **12 derniers mois complets** de la fenêtre de 24 mois, OpexAI **toutes lignes/modes**, ainsi que les bénéfices et dépenses sur les 24 mois ; distinguer ce résultat du seul endpoint `profit_year` |
| Attribution mécaniste | deltas de profit/revenu/coûts de la ligne cible **et** des lignes voisines partageant les aéroports à `t0`, puis autres lignes et AAAHogEx ; suivre avions réellement présents, capacité vendue, passagers/courrier transportés, délais, entretien, amortissement et interruptions |
| Capital et valeur | débours réellement attribués aux avions, ventes et remplacements, variation de caisse **et de dette**, actifs aériens résiduels aux deux dates, `company_value` et ratio des moyennes ; ne pas additionner cash, valeur des véhicules et `company_value` comme s'ils étaient indépendants |
| Coût d'opportunité | identité et rang des autres projets sélectionnés/financés/différés dans chaque bras, coût payé et profits ultérieurs ; un RAIL classé, mais non physiquement exécutable (`too_close_no_join`, A* ou constructeur), n'est **jamais** compté comme investissement évincé prouvé |
| Rendement marginal descriptif | `Δprofit_net_12m / prix_physique_avion_t0` (annualisé, unité et amortissement explicités) **uniquement** si transaction livrée, facture unitaire et marge comparables disponibles ; effet **réseau** du choix ponctuel, sensible aux achats compensatoires ; publier aussi l'effet sans division en £/an |

Les métriques de trésorerie nette sur 24 mois doivent distinguer achat de capital, exploitation, prêts, cessions et actif restant afin d'éviter un double comptage. Pour un projet qui n'est pas encore mature à +24 mois, indiquer `immature`, garder la mesure complète et **ne pas sélectionner un nouvel horizon après résultat**. Décrire le coût en opcodes et d'éventuelles pauses de l'IA dans chaque bras ; ces écarts peuvent eux-mêmes provoquer des choix concurrents.

## 5. Exports proposés (schéma à implémenter, non existant)

Format recommandé : `manifest.json` immuable, `episodes.jsonl`, `events/{aa0,aa1,renfort,sans_renfort}.jsonl`, `checkpoints/{bras}.jsonl`, `comparison.json`. Champs numériques typés, dates ISO jeu + tick, `null` si absent et raisons dans `missing_reason`, unités `GBP`, `GBP_per_year`, `per_mille`, `months`, `opcodes`. Schéma minimal :

| Objet | Champs minimaux requis |
|---|---|
| `manifest` | `schema_version`, `protocol_id`, `bundle_sha256`, `git_sha`, `git_dirty`, `source_save`, `source_save_sha256`, `seed`, `episode_id`, `OpenTTD_version`, `NoAI_version`, `AI_config_sha256`, `rival_sha256`, `map_config`, `company_ids`, `start_date`, `t0_tick`, `horizon_months=24`, `branch_action`, `probe_config`, `host_mode`, `rng_state_hash_or_null` |
| `episode_pre` | `episode_id`, `channel`, `lineId`, `stations`, `cargo`, `c121Arm`, `candidate_key`, `select_tick`, `select_date`, `execution_tick`, `tier`, `rank`, `K_dec`, `cash`, `available`, `reserve`, `finance`, `estimated_spend`, `unit_price`, `have_actual`, `have_line`, `baseVehicles`, `want`, `targetAirPlanes`, `c121MarginalSamples`, `marginal_source`, `predicted_revenue/profit`, `v161_model`, `v161_prior`, `v161_source`, `profit_post_v161`, `profit_c70`, `fundScore`, `neighbors`, `historical_capacity/load`, `age`, `availability_timestamp` de chaque variable |
| `decision/event` | `event_id`, `episode_id`, `arm`, `date`, `tick`, `phase` (`select`, `ready`, `override`, `attempt`, `constructor`, `after`, `deferred`), `action`, `outcome`, `reason`, `added`, `replaced`, `lineId`, `VehicleID`, `engine`, `cargo_refit`, `transaction_id`, `actual_cost`, `sales`, `cash_before/after`, `loan_before/after`, `other_command_ids`, `first_divergence_tick` |
| `checkpoint` | `arm`, `episode_id`, `month_offset` (0..24), `date`, `tick`, `is_complete`, `rng_hash_or_null`, `company_hash`, `AI_state_hash_or_null`, `cash`, `loan`, `company_value`, `profit_year`, `profit_year_period`, `quarterly_profit`, `fleet_by_mode`, `line_stats`, `network_neighbours`, `AAAHogEx_stats`, `physical_cashflows`, `other_project_events`, `vehicle_residual_values`, `opcode_counts`, `script_errors` |
| `comparison` | `episode_id`, `aa_complete`, `aa_equal`, `aa_first_mismatch`, `source_replay_exact`, `arm_source_equal`, `hook_hit_count`, `treatment_delivered`, `control_avoided`, `contamination_catchup_date_or_null`, `complete_24m`, `health`, `primary_delta_profit_year_or_null`, `network_delta_12m_or_null`, `net_cashflow_delta_24m_or_null`, `residual_delta`, `displaced_investments`, `qualify_status`, `reasons`, `hashes_of_all_exports` |

L'`episode_id` est l'identifiant de **source** commun à chaque bras, sans dépendre d'une séquence de logs pouvant diverger. Pour les identifiants de stations/villes issus des sauvegardes, conserver le système de référence et la transformation appliquée : les identifiants de villes décodés par le harnais des sauvegardes sont décalés de **+1** par rapport à l'API NoAI (`ai/OpexAI/CLAUDE.md`). Pour chaque champ historique, exposer le **temps de disponibilité** avant `t0` : une copie d'une statistique calculée au dernier rapport n'est pas une mesure contemporaine brute.

**Provenance :** tous les fichiers portent hash, chemins relatifs, horodatages, configuration identique et références vers les journaux originaux ; aucune jointure inter-parties par simple date + lineId. Le journal `AIRF1_*` existant (`air_flotte1_shadow.nut`) reste une source d'exposition, non un export de factures exactes. Les nouveaux exports demandent de l'outillage et des essais spécifiques qui **n'ont pas été réalisés**.

## 6. Critères d'arrêt, de validité et de qualification

1. **Avant fourche :** documenter exposition réelle et couverture des covariables **préachat** par graine, prouver Save/Load/reprise fidèle au point de transaction, mêmes compagnies, même bundle, même branche de sélection/constructeur et état financier. En l'absence de `t0` exact, classer `not_identifiable` ; une sauvegarde mensuelle est seulement descriptive.
2. **AA/AA :** deux replays complets des 24 mois, source identique, contrôle économique exact à tous les checkpoints, premier écart absent et santé identique. Si AA échoue, ne pas lancer/interpréter RENFORT/SANS_RENFORT pour cet épisode.
3. **Intervention :** vérifier une occurrence du déclencheur, une action symétrique du hook jusqu'à la transaction, renfort réel dans RENFORT, absence de commande ciblée dans SANS_RENFORT, dates/états égaux **avant** l'intervention. `trigger_mismatch`, construction échouée et `REPLACE` restent publiés dans l'exposition ; pas de « succès » attribué.
4. **Complétude :** 24 mois entiers par bras, aucune erreur moteur/Squirrel, chiffres de coût réel, achats ultérieurs, autres dépenses et actif résiduel contrôlés. Si des données manquent, laisser l'endpoint en `null` ou qualifier la mesure de partielle. Un scénario tronqué ne se transforme pas en échantillon sain.
5. **Analyse :** deltas appariés source × graine, répartition V/D/E, médiane et moyenne, intervalle de confiance par **bootstrap de grappes de graines** si effectif suffisant ; publier effectif de sources et de graines, pertes et causes ; pas de test naïf par nombre de ticks, achats ou snapshots. Ces **10 fourches au maximum** sont un diagnostic local ; faible exposition ou intervalles larges donnent `inconclusive`, jamais un coefficient calibré.
6. **Interdits :** aucun coefficient V161/C70, correction AIR/RAIL, réserve, ordre C77, score, défaut ou politique adopté sur ce diagnostic ; aucune inférence d'éviction RAIL à partir d'un classement, d'un franchissement financier ou d'un candidat `too_close_no_join` ; aucune exclusion postérieure des épisodes perdants ou avec rattrapage ; aucun `AA` manquant tenu pour validé ; aucun relancement d'anciens bancs fermés. Ne pas confondre un effet conditionnel de sauvegarde avec un gain général.

**Suite éventuelle, distincte de l'étape 2a :** si l'exposition et la fidélité sont vérifiées, utiliser une cohorte de graines **indépendantes** de la calibration pour évaluer un estimateur shadow par classe, notamment le rendement marginal selon **1 / 2 / 3–4 / ≥5** avions. Comparer prédiction C121 brute, profit V161/C70 classé et effet contrefactuel à 24 mois, avec erreurs et incertitudes ; conserver l'absence de coefficient s'il n'y a pas de signal hors échantillon. Toute **modification comportementale** ultérieure réclame son propre pré-enregistrement, smoke et **portes V102** (`AGENTS.md` §4/4.1 : A 40×3 `gain_short`, B 20×10 `non_erosion` avec garde de valeur −5 %), en duel multimodal sans sonde perturbatrice. La fourche 24 mois ne remplace aucune de ces portes.

**Contraintes d'exécution si le protocole est autorisé plus tard :** une seule campagne Docker à la fois, plafond PC 10 CPU / 10 workers, aucun commit/push implicite, aucune simulation pendant la présente étape documentaire.

## 7. Amendement prospectif 22/10/2026 — ITT par assignation intra-partie

**Préenregistrement fait avant les résultats de ce dispositif.** Les §§2–6 ci-dessus restent
la référence historique de la fourche même sauvegarde, dont le prérequis est bloqué
(`air_roi_renfort1_etape2b_fourches_20261022.md`). L'expérience ci-dessous a un autre
estimand et ne prétend pas résoudre la sauvegarde atomique `t0`. Elle randomise la décision
d'intervenir **dans la partie vivante**, au lieu de recréer deux univers identiques.

**Unité et éligibilité.** Au dernier point financeable après gardes `scrapping`, flotte
caduc et caisse de `_tryBuildFleetProject` (ou sa voie ancienne directe), un renfort AIR
existant est assigné avant appel `OpexAirAddPlane`. Une même ligne a au plus une
**nouvelle assignation** par tranche de 732 jours ; ses renforts naturels ultérieurs
restent possibles dans l'état `treatment`. Les réparations de crash `needsRefleet`,
le V252 `REPLACE`, les nouvelles lignes et les candidats refusés avant ce point sont
séparés du dénominateur ITT éligible. Un traitement peut échouer, être remplacé ou
ajouter plusieurs avions : aucun de ces cas n'est exclu a posteriori.

**Allocation figée.** Réglage `air_roi_renfort1_itt=0` désactivé aux quatre
difficultés ; `1` est un témoin **p=0** instrumenté ; `2` est **p=50 %**. L'IA obtient
une graine du monde via `AIGameSettings` si le réglage est accessible, sinon effectue
une unique lecture `AIBase.RandRange` au premier épisode et publie `seed_src`.
Hash arithmétique borné modulo 1 000 003 de `(seed, lineId, numéro d'épisode)`,
seuil `hash < 500001` pour assigner `deferred` ; les autres sont `treatment`.
Un report saute le batch courant et toutes les croissances ciblées de cette ligne
pendant **732 jours** (au moins 24 mois civils), y compris lors d'un Save/Load.
Le témoin `p=0` traverse le même code d'instrumentation sans report. Les tirages,
les refus constructeur, les achats de remplacement, le nombre d'avions ajoutés,
le coût capté par `AIAccounting` et le report sont journalisés ; les assignations
et événements doivent être vérifiés dans les logs avant de conclure à l'exposition.

**Mesures et estimands pré-spécifiés.** Sur le bras `p=50`, différence de moyennes
des résultats à 24 mois des **lignes assignées** `treatment` moins `deferred`,
incluant succès/échecs et rattrapages. La comparabilité est prospective par tirage,
avec variation et interdépendance dans une même partie ; ce n'est pas une paire
de lignes identiques issue d'une même sauvegarde. Un nouvel épisode est tronqué
s'il ne reste pas 24 mois de suivi, sans suppression de son assignation du registre.
Comparer séparément le `profit_year` terminal de la **compagnie** entre
`p=50` et `p=0` en duel AAAHogEx de mêmes graines/configuration/années ; ce
contraste de politiques, avec effets d'éviction/trésorerie inclus, ne représente
pas l'effet local d'un avion. Rapporter la différence du nombre **réellement ajouté**
par assignation en premier étage. Un ratio ITT / premier étage n'est présenté
que descriptivement, sous réserve de la multiplicité des avions et des hypothèses
d'exclusion/monotonie ; il ne constitue pas une rentabilité physique certifiée.
Ni `lastProfit` de ligne mis en cache ni les finances agrégées des avions ne sont
une preuve de profit marginal. La télémétrie mensuelle `VEHS` contient un profit
des véhicules et des ordres; ses clés par station ne sont pas `lineId` NoAI.
Toute jointure ambiguë ou un suivi incomplet donne un endpoint `null`.

**Sous-groupes fixés avant résultats** : nombre d'avions préachat `1`, `2`,
`3–4`, `>=5`, saturation binaire `vehCount >= targetAirPlanes` vs non saturé
(métrique différente de l'occupation réelle de l'aéroport, non disponible),
type de ligne C121, source V161 connue/inconnue. Ne comparer que des observations
prétraitement, publier les cellules sans effectif. Résultats primaires en £/an
avec bootstrap **20 000 réplications de grappes par graine**, RNG analyse `0`,
IC95 percentile et effectifs des deux affectations ; afficher coûts et bénéfices
avec leur provenance, sans attribuer un bénéfice à `added=0`. Les chocs de concurrence
dans les mêmes parties, sélection des lignes éligibles, biais d'appariement VEHS,
multi-renfort et instrumentations sont des limites explicites.

**Budget préenregistré** : smoke 1 graine `42` × 1 an (p=0 et p=50,
avec journaux moteur, santé et au moins un renfort construit pour certifier
`added` et coût comptable). Si 1 an n'expose aucun succès, diagnostiquer une
fenêtre plus longue, sans tenir le premier smoke pour valide. Exposition à
**20 graines × 6 ans**, une répétition/bras : `42, 100, 999, 1234, 5678,
314159, 271828, 161803, 123457, 987653, 2026, 1337, 1024, 111, 222,
333, 444, 555, 666, 777`. Les épisodes après année 4 sont censurés à +24 mois ;
ne pas allonger la fenêtre a posteriori en fonction du signe de l'effet. Utiliser
les deux bras `OpexAI[air_roi_renfort1_itt=1]` / `=2` et la télémétrie mensuelle
dans le lanceur §4.1, `--script-debug`, même arbre de code et AAAHogEx.
Le seuil d'information prévu est au moins **30 épisodes évaluables à 24 mois
et 10 graines contributrices avec les deux bras internes** ; en dessous,
`inconclusive`, sans changement de score/défaut. La porte A V102 reste une
qualification ultérieure indépendante si une politique utile apparaît.

## 8. Amendement prospectif du 22/10/2026, 16 h (Europe/Paris) — campagne ITT 2

**Figé avant tout résultat de la campagne 2.** La campagne 20×6 du §7 est close,
`inconclusive`. Ses séries et ses critères restent inchangés : 1 291 assignations,
43 suivis stricts valides, dont 13 traités et 30 différés, 9 graines avec les deux
affectations. Diagnostic de la perte de suivi (les catégories sont exclusives) :
510 assignations trop tardives pour +24 mois avant 1976, un suivi interrompu
malgré un horizon suffisant, 737 séries possédant 24 relevés mais invalidées
(43 autres séries à 24 relevés valides). Parmi les premières ruptures, 913
relevés dépassent sept jours de retard et 159 ruptures ont une autre cause
ou une cause non observée. Ces dernières classes se recoupent avec la censure
administrative et ne sont pas additionnées aux 1 248 manquants.

**Correctif avant collecte.** La sonde quotidienne est appelée au début des deux
boucles principales IA, avant l'ordonnanceur qui peut ne pas rendre la main à
temps. Elle conserve un seul relevé par date et par échéance, le `lineId`, les
VehicleID et les dates effectives. Un intervalle est valide si le relevé existe,
si la dernière échéance n'a pas plus de **14 jours** de retard, si sa durée
réelle est comprise entre **18 et 42 jours**, si la continuité des compteurs
NoAI à la frontière d'année est vérifiable et si aucune vente, perte ou
réaffectation de véhicule n'empêche l'attribution du profit. Publier la
`fail_reason` de chaque intervalle ; une rupture reste absente de tout endpoint
qui la traverse, mais **n'invalide plus irréversiblement les intervalles futurs**.
Ne pas interpoler de profit manquant ni remplacer la maintenance, l'infrastructure
ou la dépréciation par la recette reconstruite. Si la ligne disparaît avant
un endpoint, censurer et signaler `line_missing`, sans lui imputer zéro.

**Endpoints fixés avant mesure :** à +12 mois, profit d'exploitation de **tous
les avions de la ligne** sur les 12 intervalles 1–12 valides ; à +24 mois,
profit d'exploitation sur les 12 intervalles 13–24 valides. Chacun est
annualisé par `somme_profit × 365,25 / somme_jours_observés`. Exiger pour
chaque fenêtre une durée totale de **337 à 393 jours**, 12 décalages uniques,
identité épisode/grappe/ligne et tous les intervalles valides. La fenêtre
13–24 peut être analysable malgré un incident ancien dans les mois 1–12.
Rapporter séparément profit, coût de roulage estimé, recette reconstituée ;
le net de ligne complète demeure `null`. Les taux de suivi de +12 et +24
incluent **toutes les assignations**, y compris échecs constructeur et
traitements reportés ; distinguer le taux brut et le taux parmi les épisodes
dont l'échéance est antérieure à la fin de la partie. Publier l'attrition par
bras et graine, les motifs initiaux, les lignes perdues et les cas impossibles
à trancher. Ne jamais utiliser un sous-échantillon ayant survécu pour annoncer
un rendement physique de l'avion.

**Campagne 2 fixée :** `airr1_itt_month_20x10_20261022_b`, 20 graines identiques
au §7, 10 ans, 1 répétition, mêmes bras `OpexAI[air_roi_renfort1_itt=1]`
et `=2`, `--script-debug --line-telemetry --line-telemetry-monthly`, même
bundle figé pour les 40 jeux et AAAHogEx inchangé. Sur le PC Docker local,
**5 CPU, mémoire 8 Gio, 4 workers maximum** ; ne pas interrompre RLW-04.
Ce budget de 40 jeux × 10 ans, contre 40 × 6 auparavant, donne huit ans
d'occasions éligibles à +24 mois contre quatre ; il réduit la fraction
administrativement censurée en retenant 20 grappes, avec un coût moteur
estimé 10/6 fois celui de la campagne précédente. Aucun autre horizon n'est
choisi selon le signe des résultats.

**Règle d'information et d'interprétation de la campagne 2 :** au moins **30
épisodes évaluables à +24 mois**, **10 graines avec les deux affectations
évaluables à +24 mois**, et un taux de suivi à +24 mois parmi les assignations
administrativement éligibles **≥70 % dans chaque bras**, avec différence
absolue de taux **≤10 points de pourcentage**. À +12 mois, rapporter
les mêmes seuils et effectifs, sans faire du résultat à +12 mois un remplacement
de celui à +24 mois. Le point ITT est le contraste des moyennes d'assignations
observables `treatment − deferred`, avec 20 000 bootstrap **par grappe graine**
RNG 0, et IC95 percentile à chaque horizon ; ne pas interpréter un IC nominal
si la censure dépend du bras. Si le seuil d'information/attrition échoue,
`inconclusive` quelle que soit la borne de l'IC. Publier aussi le premier étage
sur toutes les assignations et le contraste compagnie apparié p50−p0 en
`profit_year` terminal, IC95 et garde descriptive de valeur −5 %. La politique
20×10 est **diagnostique**, pas une porte V102.

**ÉTAPE 3 conditionnelle :** uniquement si l'ITT 24 mois satisfait ces
conditions et permet une interprétation économique, confronter shadow le
ROI brut et V161/C70 à un *rendement marginal net* réellement mesuré,
avec cohorte d'effectif avant achat et séparation de graines apprentissage/test.
Le profit d'exploitation de toute la ligne ne démontre pas à lui seul
un ROI marginal net par appareil. Ne proposer de variante et ses portes A/B
V102 qu'après preuve **indépendante** d'un biais et d'un gain de compagnie.
