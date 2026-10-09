# Chronologie OpexAI contre AAAHogEx — cinq premières années, 08/10/2026

## Protocole et provenance

- **Nouvelle mesure descriptive C66.3** : `chrono_opex_aaa_20x5_20261008_r1`, 20 graines canoniques, une répétition, **20 duels partagés** (OpexAI slot 0, AAAHogEx slot 1) de **1970 à 1974**, réglages du code courant par défaut, aucune variante. **Ce diagnostic n'est pas une porte V102 de qualification.**
- Dépôt `master`, HEAD `cb23a172fa6f7b79e50d0392e526a061c130259b`, arbre local **dirty** au lancement (sondes rail/documentation d'autres travaux, à préserver). Le harnais a figé le contenu réellement utilisé : bundle SHA256 `3d159220b53d40b39598fca051b3902f4156f8f0d42a5ab34f5431fc360bad8d`, manifeste SHA256 `362ef84b6d1883722e6c73cf2c3938fec23736a687fdaac6f835a3feaeccb83a`.
- Runtime Docker local `desktop-linux`, image `openttd-lab:latest` `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, **10 CPU, 8 Go, 10 workers**, volume `openttd-lab-home`. OpenTTD 15.3 / OpenGFX 7.1. Télémétrie passive des lignes à chaque checkpoint annuel de décembre.
- Commande exécutée : `python -X utf8 sweeps/run_c66_reference.py --campaign chrono_opex_aaa_20x5_20261008_r1 --policy-id chrono_default_20261008 --years 5 --repeats 1 --line-telemetry --cpus 10 --memory 8g --max-workers 10 --out results/chrono_opex_aaa_20x5_20261008_r1.json`.
- Preuves : `results/chrono_opex_aaa_20x5_20261008_r1.json`, `.jsonl`, `.manifest.json`, dossier `_bundle`, `_engine`, `results/chrono_opex_aaa_20x5_20261008_r1.analysis.json`, `.annual.csv`. Décodeur reproductible `sweeps/analyse_chronologie_c66.py`.
- **Santé** : 20/20 duels, compagnies `complete/complete`, aucune partie échouée ; 20 checkpoints appariés par année et par bras, 20/20 snapshots de lignes valides pour chacun des cinq points et des deux compagnies ; l'analyseur retourne `warnings=[]`. La première année n'a pas encore quatre trimestres clos ; le profit `profit_year` est une somme des quatre derniers trimestres clos *disponibles*, sans annualisation. Les quatre années suivantes ont une fenêtre roulante de trimestres clos ; un checkpoint de décembre ne correspond donc pas exactement au résultat comptable de l'année civile.

## Trajectoire économique

Moyennes des 20 graines, valeurs en **k£** sauf indication. L'écart est toujours OpexAI − AAAHogEx ; V désigne les graines où Opex est devant AAA sur le profit annuel.

| Checkpoint | Profit Opex | Profit AAA | Écart profit | V/20 | Valeur Opex | Valeur AAA | Cash Opex | Cash AAA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1970-12-01 *(partiel)* | 357 | 321 | +36 | 12 | 310 | 304 | 78 | 45 |
| 1971-12-01 | 1 340 | 1 375 | −35 | 9 | 1 599 | 1 493 | 78 | 54 |
| 1972-12-01 | 1 942 | 2 008 | −66 | 8 | 3 500 | 3 023 | 713 | 214 |
| **1973-12-01** | **1 902** | **2 630** | **−728** | **0** | 5 195 | 4 287 | 1 651 | 519 |
| **1974-12-01** | **1 992** | **3 294** | **−1 302** | **0** | 6 888 | 6 022 | 2 735 | 1 035 |

Au point terminal : `profit_year` Opex **1 991 898 £** contre AAA **3 294 132 £**, soit **−39,53 %** du profit de l'adversaire, Opex devant dans **0/20** graines. Valeur Opex **6 887 653 £** contre AAA **6 022 339 £**, soit **+14,37 %** sur le ratio des moyennes, **15/20** graines où Opex est devant en valeur. L'écart apparaît nettement au checkpoint de **décembre 1973**, à partir duquel AAA gagne le profit dans toutes les graines de ce banc. L'écart entre la valeur et le profit est central : les actifs accumulés n'apportent pas la même rentabilité.

## Trajectoire physique et géographique

Compteurs de véhicules **primaires** (`physical_counters.py`, sans confusion avec wagons/rotors), aéroports physiques et gares physiques, en moyennes par partie.

| Décembre | Aéroports O/A | Avions O/A | Trains O/A | Véhicules routiers O/A | Gares O/A |
|---|---:|---:|---:|---:|---:|
| 1970 | 12,8 / 12,6 | 10,4 / 12,1 | 0,0 / 0,4 | 0,0 / 0,2 | 12,8 / 13,1 |
| 1971 | 29,5 / 24,7 | 35,2 / 23,5 | 2,6 / 6,0 | 0,8 / 36,3 | 35,5 / 54,3 |
| 1972 | 34,3 / 28,2 | 56,0 / 31,1 | 4,2 / 12,3 | 1,3 / 102,6 | 41,5 / 104,7 |
| **1973** | **36,8 / 32,1** | **75,7 / 38,3** | **4,9 / 21,8** | **1,8 / 136,0** | **45,4 / 138,7** |
| **1974** | **37,8 / 33,7** | **94,6 / 41,0** | **5,8 / 33,2** | **2,4 / 136,7** | **48,9 / 153,0** |

Sur ce **nouveau profil incluant C121 corrigé et V93bis adopté**, Opex a déjà plus d'aéroports que AAA dès 1971. Les comparaisons anciennes sur le manque absolu d'aéroports doivent donc être réévaluées. Opex investit surtout en avions : **94,6 avions** pour **37,8 aéroports** en 1974, contre **41,0 avions** et **33,7 aéroports** chez AAA ; le déficit de trains est beaucoup plus marqué (5,8 contre 33,2). La grande flotte routière AAA ne prouve pas que ses lignes routières directes sont profitables : elle peut contribuer indirectement au réseau par les transferts. La route reste dépriorisée par décision utilisateur.

### Profits observés des véhicules par mode

Sommes de `profit_this_year_gbp` issues des sauvegardes de décembre, puis moyenne entre les 20 parties. Ces montants sont **en cours d'année civile** et ne forment pas une décomposition additive du `profit_year` roulant de l'entreprise ; des coûts et opérations hors véhicules s'y ajoutent. Les lignes reconstituées ne sont pas non plus regroupées symétriquement (Opex par gares desservies, AAA principalement par `AIGroup`) ; leur nombre est un ordre de grandeur, pas un décompte comparable d'objets métier.

| Décembre | Profit avions O/A | Profit trains O/A | Trains exploités O/A |
|---|---:|---:|---:|
| 1971 | 1 372 / 1 312 k£ | 47 / 46 k£ | 2,6 / 6,0 |
| 1972 | 1 716 / 1 595 k£ | 56 / 286 k£ | 4,2 / 12,3 |
| **1973** | **1 676 / 2 031 k£** | **65 / 463 k£** | **4,9 / 21,8** |
| **1974** | **1 758 / 1 891 k£** | **72 / 871 k£** | **5,8 / 33,2** |

Entre 1972 et 1974, Opex ajoute **38,6 avions**, pour environ **42 k£** de profit aérien courant supplémentaire sur ces snapshots (+2,5 %), tandis que AAA ajoute **9,9 avions**, pour environ **296 k£** (+18,6 %). Ce contraste **n'est pas un rendement marginal causal** : les routes, âges et trafics changent simultanément. Il justifie de mesurer par ligne les achats marginaux, la capture passagers, l'imputation des pertes aux autres lignes et le profit réseau réellement gagné. Pour le rail, les 799 k£ de différence de profit courant des véhicules en 1974 signalent un gisement de rattrapage, mais les corrections déjà essayées ont souvent ajouté des tentatives ou des lignes sans gain économique ; viser les projets **profitables**.

## Tableau des tâches restantes, classées d'après ce banc

**Classement prospectif**, pas nouvelle décision d'adoption. P0 : enquête ou intervention prioritaire au regard du décrochage 1973 ; P1 : chantier potentiellement important avec dépendance ; P2 : travail ciblé ou support ; P3 : conditionné, faible urgence. **S** : quelques heures à un jour ; **M** : 2–4 jours ; **L** : environ 1–2 semaines ; **XL** : recherche / plusieurs itérations et campagnes. Estimations relatives, hors temps des portes V102. Les numéros renvoient à `docs/taches.md` ; les pistes fermées ne figurent pas comme nouvelles tâches.

| Sujet encore ouvert | Priorité | Complexité | Justification mesurée / prochaine vérification |
|---|---|---|---|
| **AIR — profit marginal réseau de chaque avion, saturation et cannibalisation (`C61`, C121, V134)** | **P0** | **L** | 95 avions Opex mais profit aérien inférieur à AAA (41 avions). Réconcilier recette marginale propre, pertes des anciennes lignes, coûts et choix `newpair`/renfort ; ne pas modifier le plafond à l'aveugle. `docs/diagnostic_v133_v134_air_20261008.md`. |
| **Rail fret — généré→TOPK→finançable→élu→A*→posé→profit, par cargo/destination** | **P0** | **L/XL** | 5,8 trains Opex contre 33,2 AAA en 1974, profits véhicules rail 72 contre 871 k£. Distinguer absence de projets rentables, rejets physiques et occupation du créneau ; les seuils A*, la mémoire TRKFAIL et la proximité cache déjà essayés n'ont pas passé leur porte. `docs/diag_fret_ferroviaire_20261008.md`, `docs/taches.md` §3/§4. |
| **Trésorerie non convertie en projets en 1972–74** *(nouvelle piste de mesure)* | **P0** | **S/M** | Cash Opex 713 k£ → 1,65 M£ → 2,73 M£, tandis que profit plafonne. Comparer à dates fixes top candidats, seuils cash réellement franchis, scores, `search_in_progress`, projets nouveaux contre flotte ; identifier la première décision de non-investissement profitable. **Ne prouve pas** un bug de financement. |
| **C121 — estimateur PASS utilisable depuis NoAI, capture intercompagnies** | **P1** | **XL** | Faible productivité AIR ; mesure physique du flux meilleure que proxy mais inaccessible telle quelle à NoAI. Historique d'embarquement, stock/pertes, concurrence, fenêtres contemporaines et rating projeté ; validation temporelle avant A/B. `docs/taches.md` 53–149. |
| **AIR — coût réel terrain, arrêts joints et marge financière adaptative** | **P1** | **M/L** | Le code figé du présent banc omettait des coûts physiques ; p90 réel/prévu 1,15 et échecs coûteux, mais exposition du simple abaissement de marge bornée à ~1,6 %/an au plus. **Depuis le lancement, prototype `air_site_cost_quote=0` / `air_site_cost_margin_pct=0` livré en concurrent dans l'arbre partagé** : reste smoke, calibration du résidu, mesures opcodes/Save-Load puis portes V102, sans adoption. Voir `docs/air_cout_reel_marge_risque_20261008.md` et l'état courant de `docs/taches.md`. |
| **V130 — poser un tracé préparé dès sa disponibilité en année 1** | **P1 conditionnelle** | **M/L** | Toujours **non implémenté** : `rail_prep_held` retient la pose malgré préparation. Mesurer âge, constructibilité et coût d'opportunité AIR avant correctif ; V128/V131 n'en constituent pas un test. `docs/v130_early_rail_build_20261008.md`. |
| **Cap de routes d'un hub AIR adaptatif** | **P1** | **M/L** | Cap 3 adopté, optimum hétérogène selon les graines ; autopsie des cas 17/781335 et 1/802204 sur signal pré-décision, sans classifieur post hoc. `docs/taches.md` 578–589. |
| **Phase 3 — fret transformé/biens, après fret ferroviaire de base rentable** | **P1 conditionnelle** | **L/XL** | AAA développe des trains et cargos variés ; n'aborder la chaîne de production que lorsque les lignes simples sont sélectionnées, posées et rentables. Doctrine V106, `docs/taches.md` 665–667. |
| **R2 — relier devis à l'élection, achat et profit réel par ligne** | **P1/P2** | **M/L** | Nécessaire pour attribuer l'écart de revenu à des décisions précises ; instrumenter sans tri diagnostique coûteux, `docs/taches.md` 638 et §2. |
| **C76/C77 — invalidation, vivier, Save/Load et subventions** | **P2** | **M** | Reliquat explicite ; mesurer les invalidations et décisions perdues avant toute modification. `docs/taches.md` 631. |
| **V133/V134 — autopsie passive des faux blocages et du profit réseau** | **P2** | **S/M** | Deux variantes déjà rejetées au gain ; vérifier fréquence de quarantaine de ville qui masque un hub, C83 non additif et coût réseau sous-estimé. Ne pas relancer des portes identiques. `docs/taches.md` 10–42. |
| **Catalogue C121/C76 — reconstructions complètes et opcodes** | **P2** | **M** | Cadence annuelle, invalidation événement, caisse, Load ; identifier le poste dominant via `PROBE_SPAN_TRACE` avant optimisation à décisions constantes. `docs/taches.md` 621. |
| **F-EVENT-BACKLOG-01 — délai événement→handler** | **P2** | **S/M** | La sonde existe ; 16 fenêtres anormales, horloge mêlant commandes et calcul. Attribution `event.*` avant correction. `docs/taches.md` 570. |
| **C67 / C80 / scheduler — exactitude et allocation d'opcodes** | **P2** | **S/M** | Fixtures C67, bilan des vrais postes C80 et délais d'ordonnancement ; aucune économie présumée sans exposition. `docs/taches.md` 635–637. |
| **R5/R20, R11–R17 et UR-15b/16d/16e — robustesse, duplication, Save/Load** | **P2** | **M/L** | Dette de qualité et de fiabilité, mais effet sur le profit non établi. Conserver les sondes OFF, tests adaptés et statuts déjà clos. `docs/taches.md` §2. |
| **Rail — devis complet voie + dépôt/raccord + terrain** | **P2 différée** | **L** | Terrain 100→170 et dépôt seul n'ont pas apporté de gain ; recalibration physique cohérente et exposition avant variante. `docs/taches.md` 281–305. |
| **C85 puis C84 — frontière équipement / flotte aérienne** | **P3 conditionnelle** | **L** | Suite permise seulement par les critères spécifiques C85 ; pas de 20×10 anticipé. `docs/taches.md` 640. |
| **A* worker parallèle, nouveaux créneaux rail** | **P3 conditionnelle** | **L/XL** | Reprendre seulement si des passes portefeuille retardées par `pending` et du profit non-rail en attente sont mesurés ; réallocations simples déjà décevantes. `docs/taches.md` 620 et 659–660. |
| **Mer / eau (phase 4), réseau ferré partagé** | **P3 conditionnelle** | **XL** | Après industrie et réseau rentable, sans nouveaux transports prématurés. Doctrine V106 et `docs/taches.md` 695–697. |
| **Route d'appoint / feeder, notes de gare, MAIL dédié** | **P3** | **L** | Route explicitement dépriorisée ; note de gare V132 secondaire, `air_mail_fleet` smoke défavorable. Étudier l'effet indirect des transferts AAA sans réintroduire des feeders par défaut. `docs/taches.md` 281–305, 677, 691. |

**À exclure de cette file** : C88 clos (API NoAI 15.3 sans distinction humain/IA), V93bis adopté, C121 économie/catalogue corrigés adoptés, UR-15a/16b clos, V133/V134 non adoptés, V128/V131 en pause, V137/V138 rejetés, requalification des anciens seuils A*/V100, `rail_cached_proximity_gate`, mémoire TRKFAIL et candidats C83 rejetés. Les résultats anciens de C121 0/0 contre C115 et de V93 précèdent les correctifs désormais présents ; ils expliquent l'historique et ne servent pas de baseline actuelle.

## Nouvelles hypothèses falsifiables, dans cet ordre

1. **1973 est l'année de blocage de l'investissement rentable** : dans les graines au cash suffisant, des plans à profit réseau réel positif restent financés mais non élus/terminés, à cause de la file A* ou du scoring flotte. Falsification : tous les plans réellement constructibles auraient un profit marginal réseau inférieur à celui des ajouts réalisés.
2. **AIR : les derniers avions cannibalisent les lignes existantes** : le `profit_this_year` par ligne, le flux de stations et les pertes des autres lignes diminuent après renfort, même si le modèle classe l'achat positif. Falsification : le renfort accroît le profit réseau global au niveau prévu.
3. **Rail : la rareté est celle des lignes fret rentables livrées** : la ventilation par cargo et destination identifiera une étape de perte majeure entre validation/élection et construction, sans changement de seuil A* déjà rejeté. Falsification : les projets supplémentaires auraient un profit négatif, même en cas de pose réussie.

Chaque diagnostic doit identifier les *projets distincts* et leurs tentatives séparément des revisites répétées de TOPK/portefeuille ; `probe_select_reject` (~50 000 rejets cash par partie) mesure des visites, pas 50 000 opportunités indépendantes. Pour tout nouveau comportement : réglage OFF, preuve de mécanisme, contrats/smoke puis **A 40×3 et B 20×10 selon V102**, avec seuil 4 % et garde de valeur 5 %, en respectant les décisions locales de `docs/taches.md`. Aucun changement de défaut, commit ou push sur la base de ce diagnostic seul.
