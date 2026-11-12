# Mesure OPCODES / AIList — L1, L2 et gisements hors rail

**Date :** 12 novembre 2026. **Arbre :** `grok12-nov12`, HEAD de lecture `6e11bc31`. **Périmètre :** lecture du code courant et des journaux déjà écrits. Aucun Docker, aucun banc, aucun réglage, aucun fichier rail.

Les JSON de sonde `results/opcode_ailist_L1_filter_probe_20261023.json` et `results/opcode_ailist_L2_road_probe_2x3_20261023.json` sont absents de ce worktree. Les comptes ci-dessous sont ceux du journal [opcode_ailist_lots_20261023.md](../opcode_ailist_lots_20261023.md), relus contre le source actuel. La télémétrie de ligne (`profit_this_year` / `profit_last_year` des véhicules) ne compte pas les appels `AIList` ni les opcodes VM : elle ne fournit pas de série L1/L2.

## 1. Appels AIList L1 et L2 rejetés

Les deux lots ont été mesurés le 23 octobre 2026 sur OpenTTD 15.3, carte 256², sonde `OpexOpsMeasureBegin/End` dans le même processus. Les variantes natives ont été retirées après mesure. Le source courant est le parcours qui avait coûté moins cher.

### L1 — notes de cargaison, bassins AIR B9

Site courant : `OpexC121StationCompetitionBuckets`, `ai/OpexAI/air_coverage.nut:413`. La liste est `AIStationList(AIStation.STATION_ANY)` à la ligne 445, puis `AIStation.HasCargoRating` par gare à la ligne 447. Le lot essayé remplaçait cet appel par `Valuate(AIStation.HasCargoRating, cargo)` et `KeepValue(1)`.

| Observation | Valeur |
|---|---|
| Exposition | 16 appels, graine 42, année 1970, `probes=1048578` |
| Membres | même ensemble de gares, 0 divergence |
| Parcours conservé | 288 opcodes |
| Parcours `AIList.Valuate` | 432 opcodes |
| Écart | +144 opcodes, +50 % |

Le journal borne lui-même la mesure : 16 appels du monde de départ, pas un réseau de gares dense, pas une moyenne annuelle. La régression sur les appels exposés suffit à laisser le parcours Squirrel. Aucun 20×10 n'a été lancé pour L1. Relancer `Valuate` sur ce filtre reproduirait le surcoût déjà mesuré.

### L2 — villes réceptrices ROAD C41.20

Site courant : `OpexRoadFreightAcceptedTowns`, `ai/OpexAI/candidates.nut:1226`. La boucle 1229–1233 saute les villes déjà servies et appelle `AITile.GetCargoAcceptance` sur la tuile centrale. L'ordre des indices est celui du catalogue. Le lot essayé préévaluait ces tuiles par `AITileList.Valuate(AITile.GetCargoAcceptance, …)` puis `KeepAboveValue`.

| Observation | Valeur |
|---|---|
| Exposition | 1 appel, graine 42, année 1972 ; graine 100 sans appel dans le même parcours |
| Liste | indices identiques et dans le même ordre, 0 divergence |
| Parcours conservé | 879 opcodes |
| Parcours natif | 1 485 opcodes |
| Écart | +606 opcodes, +68,9 % |

La préindexation C41.20 existe déjà : un gain compté une seconde fois sur le même filtre serait un double compte. Un seul appel ne donne pas une moyenne sur d'autres tailles de carte. La régression arrête le lot. Le source n'a pas réintroduit le `Valuate`.

L3 à L6 (rail max, filtre moteur V257, refit AIR, exclusion des wagons V284) ont été adoptés dans le WIP du 23 octobre après gain ciblé et neutralité 20×10. Ils sont hors du présent relevé : L3, L4 et L6 sont du rail, et L5 est un gain déjà retiré de son réglage temporaire. Les lots rejetés L1 et L2 ne sont pas rouverts.

## 2. `sleep_slack` et CPU consommé

Trois mesures déjà publiées, d'époques différentes, ne décrivent pas le même poste.

| Source | Ce qui est compté | Chiffre |
|---|---|---|
| Profil C121 du 02/10, `docs/opcode_profile_c121_20261002.md` | reliquat laissé au `Sleep(1)`, IA saturée, ~67,5 M opcodes/an | 0,9 à 2 M/an, soit 1,5 à 3 % du budget ; 7,8 M sur 6 ans dans le tableau de postes |
| V309 corrigé le 25/10, journal de transfert | boucles stables sans projet finançable, sonde | 7 409 / 27 111 boucles et 231,46 M opcodes sur 3×10, plus 165,61 M laissés au Sleep ; l'autopsie du même jour retire la lecture « caisse suffisante » |
| Spans exclusifs 40×5 du 27/10, `docs/analyse_estim_sites_40x5_20261027.md` | `LOOP_OPS.sleep_left` / sommeil instrumenté, sondes lourdes | 1,13 G (AIR), 0,97 G (RAIL), 0,70 G (multimodal) sur 40 parties et 5 ans |

`sleep_left` et `V309.sleep_ops` sont un budget non consommé. Les spans `select.full`, `air.sites` et `fleet.resize` sont du CPU exécuté. Depuis le 10 novembre, `idle1_slack_worker=1` est le défaut : `_idle1SlackStep` (`scheduler.nut`) écrit `t.pop` du catalogue vivant, lu par `air_towns.nut`. Ce remplissage de reliquat change des décisions. Il ne reste pas un gisement d'opcodes purs à récupérer par un second worker.

## 3. Les trois plus gros gisements d'opcodes inutiles hors rail

Classement sur le CPU exécuté, multimodal compris, rail exclu (la recherche A* du profil du 02/10, 116,4 M sur 6 ans, 29 % du budget, n'entre pas). « Inutile » signifie : le travail se répète alors que la décision observable ne change pas, ou le substitut `AIList` a déjà coûté plus cher. Les totaux de catégorie du 27/10 sont des opcodes exclusifs sur 40 parties ; ils mélangent le travail utile et la répétition. La part strictement inutile n'est isolée que là où une sonde l'a séparée.

### 1. Resélection d'un portefeuille stable — `projects_selection.nut:1141`

`OpexProjectSelectAffordable` ouvre le span `select.full` à la ligne 1144. Sur le 40×5 du 27/10, la catégorie « sélection des projets » vaut **3,95 milliards d'opcodes exclusifs** en multimodal (4,86 en rail seul, 2,77 en air seul), le plus gros poste consommé hors construction de tracé rail.

La sonde corrigée `OpexV309IdleTick` (`probes.nut:3003`) sépare ce poste. Sur le smoke graine 42 × 1970 du 25/10 : 839 boucles stables, **35,43 M opcodes**, dont **12 boucles et 0,591 M opcodes** seulement étaient couvertes par le devis après réserve de 5 à 25 k£. Le reste de ces 35,43 M reclasse un snapshot non financé. Le chiffre historique 231,46 M / 7 409 boucles sur 3×10 compte la même famille de boucles avant cette correction de réserve : ce n'est pas un stock de chantiers finançables. Aucune boucle stable n'est observée après 1974 dans cet échantillon.

La tâche `town_growth` (`main.nut:478`) est désactivée (`enabled = false`). Le gisement « 95 % de plans routiers non construits » du profil du 02/10 (62,7 M sur 6 ans, `OpexRoadPlanFor`) n'est plus une tâche de file. `OpexRoadPlanFor` (`builder_road.nut:4262`) reste appelé par la génération route, sous `exp_opcode_exact` déjà au défaut.

### 2. Recherche de sites AIR qui continue après la chute des ouvertures — `air_planning.nut:511` et `:2006`

`OpexAirPlansFindSites` (`air_planning.nut:511`) appelle `OpexAirFindSite` pour chaque ville du bassin (ligne 581). Avec `air_site_ranked=1`, ce symbole est `OpexAirRankedListed` (`air_site_ranked.nut:386`), installé dans `settings.nut:675-678`.

Spans exclusifs 40×5 du 27/10, déjà sous `air_site_ranked=1` et `air_site_funnel=1` :

| Poste | AIR seul | Multimodal |
|---|---:|---:|
| Génération de candidats et plans AIR | 1,94 G | 1,64 G |
| Recherche explicite de sites | 0,54 G | 0,44 G |

Ouvertures `AIR_BUILD` cumulées sur 40 parties multimodales : 340 (1970), 825 (1971), 246 (1972), 54 (1973), 33 (1974). La recherche de sites reste dans la boucle tant que `AIR_COVERAGE_STOP` vaut 0. La garde qui dort se trouve dans `OpexAirPlans` à `air_planning.nut:2006` et ne s'arme qu'avec ce réglage. Le profil du 02/10, antérieur au classement et au snapshot de hubs, attribuait 36 M d'opcodes sur 6 ans aux bras hub contre 15,6 M aux paires neuves (`AIR_LIGHT` 55,2 M). Ce découpage n'est pas rejoué sur le HEAD courant.

`AIR_COVERAGE_STOP` existe, défaut 0 aux quatre difficultés (`info.nut`, `settings.nut:76`). Le coder une seconde fois dupliquerait un levier non qualifié en multimodal.

### 3. Passages de flotte AIR qui refusent avant tout achat — `task_air.nut:515`

`OpexAI::_resizeAirFleets` ouvre `fleet.resize` à la ligne 517. Le 40×5 du 27/10 attribue **0,70 G** d'opcodes exclusifs à la gestion de flotte en multimodal (1,28 G en air seul) sur 40 parties et 5 ans. En 1974, la même campagne compte **8 914 passages** `already_grown_this_year` en multimodal et **12 183** en air seul : ce sont des passages de refus, pas des avions écartés un par un.

Le refus de cadence est à `task_air.nut:595-600` (code `Y`), avant le plafond physique (`OpexAirCadenceCapIndexed`, ligne 688) et avant le marginal V161 (ligne 798). Le refus « O » de l'observation annuelle est aux lignes 646-651. L'ancien `OpexC121RefreshVisibleFleet`, cité le 12 octobre devant ces gardes (`docs/v151d_revue_opcodes_scan_air_orchestrateur_20261012.md`), n'est plus dans le source : le surcoût « rafraîchir la demande puis refuser » de cette fiche n'est plus le chemin courant. Le poste qui reste est la visite de chaque ligne à chaque passage de la tâche `air_fleet`, y compris celles déjà verrouillées par la date.

## 4. Sous-tâches sans valeur, déjà isolées ou trop petites

- **Registre C75 bypass** (`probes.nut:2317`, `OpexC75BypassResetYearLedger`). Le 26 octobre, le registre n'est lu que par ses propres émetteurs, pas par la décision `K_pass`. L'option `c75_bypass_ledger_skip` est à 0. L'exposition graine 42 × 3 ans montre 41 lignes `C75_BYPASS` à 0 et zéro à 1, avec un delta de profit de −72 712 £/an sur une seule graine (`diagnostic_only`). Le coût en opcodes de ce registre **n'a pas été mesuré**. `c75_year_ledger_skip` est dans le même état. Les restitutions `n75_c75_refund` du 25 octobre n'ont construit aucune ligne : piste close, pas un gisement à rouvrir.
- **L1 et L2 natifs.** Les réintroduire augmenterait le poste visé (+50 % et +68,9 % sur les appels exposés).
- **Bilan `_reportYear` sous `probes=0`.** Le 25 octobre, la garde signes fait passer `_reportYear` de 9 306 à 20 opcodes en 1970 sur la graine 42. Le défaut compétitif reste `probes=2`, qui continue d'émettre les panneaux. Aucun de ces deux défauts n'est modifié ici.
- **Scans `AIStationList(STATION_AIRPORT)` répétés** du profil du 02/10 : environ 30 opcodes par aéroport et par appel. Sous le poste des trois gisements ci-dessus.

## 5. Spécification — aucun correctif codé

Aucun des trois gisements n'a, sur les preuves déjà écrites, un correctif à la fois local, neutre pour les décisions, et absent du dépôt.

1. **L1 / L2.** Spécification : conserver `HasCargoRating` unitaire (`air_coverage.nut:447`) et `GetCargoAcceptance` unitaire (`candidates.nut:1231`). Un réglage `opcode_ailist_l1` ou `opcode_ailist_l2` qui rappellerait `Valuate` rejouerait un lot rejeté. Condition pour rouvrir : une nouvelle mesure, même graine et même densité de gares ou de villes, où le natif coûte strictement moins que 288 opcodes (L1, 16 appels) ou 879 opcodes (L2, 1 appel), avec les mêmes membres dans le même ordre. Cette mesure n'existe pas dans les archives présentes.
2. **Resélection stable.** Sauter `OpexProjectSelectAffordable` tant que le snapshot est non financé changerait l'instant où un projet devient achetable. Le smoke du 25 octobre ne qualifie pas cette coupe : 12 boucles y étaient financées, et le devis publié peut être périmé (`probes.nut:3020-3022`). Spécification : laisser la sélection ; ne pas ajouter de worker de slack par-dessus `idle1_slack_worker=1`.
3. **Sites AIR après saturation.** Le levier existe : `air_coverage_stop`, défaut 0. L'armer, ou restreindre `OpexAirPlansFindSites` à la ville de `ET_TOWN_FOUNDED` sans cache des sites déjà admis, retire des partenaires à la ville nouvelle (la boucle de paires à `air_planning.nut:766` a besoin des autres sites). Cette restriction appartient au suivi EB-9 et reste non codée tant que le stop n'isole pas la ville fondée. Voir [EB9_suivi.md](EB9_suivi.md).
4. **Flotte.** Un retour avant la ligne 595 sur les lignes déjà en cadence économiserait le corps de `_resizeAirFleets` pour ces lignes seulement. Le code le fait déjà pour la cadence et pour la garde O. Aller plus loin (mémo de refus entre deux dates) change le tick auquel une ligne redevenue éligible est vue. Spécification : pas de nouveau réglage ; la prochaine mesure utile est un compteur d'opcodes autour des seuls `continue` de refus, deux bras identiques, sondes off, sans toucher au rail.

Aucun `AddSetting`, aucune globale, aucun test de plafond. Le défaut courant, y compris `idle1_slack_worker=1`, `air_site_ranked=1` et `probes=2`, est inchangé.
