# V253b — rendement aérien et stock partagé, 19 octobre 2026

Diagnostic sur des parties existantes, puis **une correction candidate**, `v274_air_growth_stock`, défaut **0**. Aucune qualification économique ni compilation moteur nouvelle. Aucun banc lancé, aucun défaut existant changé.

Le facteur dominant **identifiable comptablement** est le nombre de paires par aéroport : en 1979, 2,68 fois celui d'AAA. Le nombre d'avions par paire ne dépasse celui d'AAA que de 7,4 %. Le code autorise bien des renforts sous cible sans stock observé, et réemploie hors cible le stock complet du hub pour chaque ligne. Cela motive un filtre de renfort sur le stock partagé ; cela ne prouve pas que ce filtre améliorera le profit. **Une attribution causale complète aux neuf facteurs demandés est impossible avec ces enregistrements.** Les champs absents restent inconnus.

## Périmètre et provenance

- Worktree exclusivement `/home/deploy/projects/wt-v253b`, branche `v253b`, base initiale propre `c539a5ab2c540ed59e3c718c4440fa147fb13a06`.
- Campagne lue : `/home/deploy/projects/wt-v273/results/v273_expo_3x10_20261019.json`, son JSONL et les trois journaux `reference_seed{42,7,1234}_r0.log`. **Bras `reference` uniquement**, trois graines, une répétition, horizon 1979, trois `games[].game_ok=true`, compagnies complètes et saines. L'autre bras n'est pas une observation supplémentaire.
- Bundle enregistré : `c91dff13461726e03e3afeebb3320f92d2764be535cb242c45fe04df9d7c67ce`. Les fichiers de base `task_air.nut`, `air_trip.nut`, `air_fleet.nut`, `air_catalog_c121.nut`, `projects_builders.nut` sont identiques octet pour octet à ceux du bundle. Le contrat V273 a été lu dans le bundle, car ce réglage rail n'est pas présent sur la base de cette branche.
- Les SHA-256 des données, journaux et table moteur sont conservés dans [la preuve dérivée](v253b_decomposition_20261019.json), champ `inputs`. Ce JSON conserve tous les résultats par graine, sources des instantanés, lignes JSONL, lignes de journal pertinentes et définitions des moteurs. Le JSON intégral généré est `results/v253b_diagnostic/decomposition.json` (ignoré par Git).
- `docs/v253_decomposition_v252_20261018.md` **absent du worktree** ; non retrouvé sous ce nom dans les archives autorisées. Le rapport de livraison correspondant a été lu : `/home/deploy/projects/openttd-ml/results/rapports_agents_20261018/rapport_v253dec_agy.md`. Il rapporte la baisse des coûts du 217 et le gain des passages au 218. Ses imputations observationnelles et sa réconciliation 189/180 k£ ne sont pas réutilisées comme preuve causale sur la campagne présente.
- Consignes, fiches V252/V253/V254, archives et journaux récents relus. C81 est également relu dans `docs/journaux/20_nuit_2026-09-22.md` : le plein chargement avion avait fortement perdu en solo ; il n'est pas reproposé.

## Décomposition exacte

Notations : `P` = somme du profit des avions présents, `N` = avions primaires attribués aux lignes AIR, `A` = aéroports distincts de ces lignes, `M` = paires de villes distinctes. Les identifiants restent locaux à chaque partie ; les sommes se font ensuite entre graines. On ne moyenne pas les rapports par graine.

```text
P/N = (P/A) × (A/M) × (M/N)
rapport Opex/AAA = rendement par aéroport × inverse des paires par aéroport
                  × inverse des avions par paire
```

`P` provient de `line_telemetry.snapshots[i].lines[j].profit_this_year_gbp`, `N` de `.vehicles` ; `A` de l'union de `.endpoint_cargo_stats[].station_id`, `M` de `.market_key`, après filtre `duel_policy_id=reference`, `arm`, `year`, `mode=air`. Les listes de véhicules sont déjà décodées par le harnais, sans recompter `VEHS`.

**Date : 1er décembre** de chaque année. Le profit est celui de l'année en cours jusqu'à cette date, environ onze mois, sur les véhicules encore présents. Ce n'est ni le `profit_year` terminal compagnie sur quatre trimestres, ni le profit de toute la cohorte (les appareils retirés ont disparu). Aucun réétalonnage sur les chiffres du constat utilisateur n'est effectué.

| Année | N Opex / AAA | A Opex / AAA | M Opex / AAA | £ par avion Opex / AAA | Rapport |
|---|---:|---:|---:|---:|---:|
| 1973 | 258 / 110 | 120 / 96 | 154 / 48 | 21 901 / 57 758 | 0,3792 |
| 1976 | 401 / 126 | 120 / 106 | 163 / 53 | 17 699 / 68 311 | 0,2591 |
| 1979 | 455 / 150 | 120 / 114 | 161 / 57 | 20 246 / 75 336 | 0,2687 |

Effectifs = **sommes des trois parties**, pas effectifs d'une partie.

| Année | Facteur rendement/aéroport | Facteur inverse paires/aéroport | Facteur inverse avions/paire | Produit exact |
|---|---:|---:|---:|---:|
| 1973 | 0,7115 | **0,3896** | 1,3679 | 0,3792 |
| 1976 | 0,7284 | **0,3681** | 0,9664 | 0,2591 |
| 1979 | 0,7744 | **0,3727** | 0,9312 | 0,2687 |

En 1979 : 2,683 routes incidentes par aéroport chez nous, 1,000 chez AAA ; 2,826 avions par paire contre 2,632 ; 3,792 avions par aéroport contre 1,316. La dernière densité est différente des « 7 contre 1,4 » du constat initial : il s'agit ici de l'échantillon demandé et de ses aéroports AIR actifs. Les densités d'avions ne doivent pas être remultipliées par le facteur de capacité : celui-ci participe déjà au nombre d'avions nécessaire pour un débit donné.

Les aéroports Opex restent à 120 entre 1973 et 1979 ; les avions passent de 258 à 455 (+76 %), les paires de 154 à 161 (+4,5 %). La croissance tardive se fait surtout sur les lignes existantes, dans un réseau qui partage beaucoup plus ses aéroports. **Ni ce partage, ni les renforts ne sont en eux-mêmes une preuve de surcapacité : leur rendement marginal doit être mesuré.**

## Tous les facteurs demandés, avec leurs limites

Chaque cellule chiffrée ci-dessous est un descripteur de la flotte, pas un multiplicateur causal indépendant à appliquer au tableau précédent.

| Facteur | 1973 Opex / AAA | 1976 Opex / AAA | 1979 Opex / AAA | Source et qualification |
|---|---:|---:|---:|---|
| Distance euclidienne, tuiles, pondérée par avions | 175,61 / 171,50 (×1,024) | 174,14 / 172,57 (×1,009) | 173,73 / 170,21 (×1,021) | `.ordered_station_tiles`, largeur 2^`map_size`=256 ; distance géométrique, pas trajet réel |
| Distance Manhattan de paiement, tuiles | 236,38 / 237,26 (×0,996) | 234,73 / 239,52 (×0,980) | 233,87 / 234,62 (×0,997) | Mêmes tuiles ; le paiement dépend aussi de l'âge du cargo |
| Vitesse nominale moyenne, km-ish/h | 1 069 / 997 (×1,072) | 1 114 / 1 338 (×0,833) | 1 112 / 1 358 (×0,819) | JSONL `air_engine_counts` × table `AVI` de 15.3 ; maximum nominal, pas vitesse réalisée ; NoAI applique `plane_speed` |
| Capacité nominale voyageurs du modèle | 179,09 / 189,55 (×0,945) | 130,57 / 189,05 (×0,691) | 120,84 / 203,33 (×0,594) | Même jointure moteurs ; AAA refitte une partie de ses modèles |
| Capacité réelle cargo 0 par avion | 179,09 / 136,55 | 130,57 / 133,49 | 120,84 / 153,00 | JSONL `air_capacities_by_cargo["0"]` / effectif ; ce n'est pas le remplissage |
| Capacité réelle cargo 2 par avion | 29,50 / 75,32 | 19,34 / 76,98 | 17,38 / 71,17 | JSONL `air_capacities_by_cargo["2"]` ; ne pas additionner aux voyageurs |
| Remplissage au départ A→B | **inconnu** | **inconnu** | **inconnu** | Aucun événement cargo embarqué/départ comparable pour les deux IA |
| Remplissage au départ B→A | **inconnu** | **inconnu** | **inconnu** | Idem ; stock et note ne permettent pas de le reconstituer |
| Avions par paire | 1,675 / 2,292 | 2,460 / 2,377 | 2,826 / 2,632 | `.vehicles`, `.market_key` ; dilution du stock commun surtout entre **paires** |
| Taille des villes desservies | **inconnue** | **inconnue** | **inconnue** | `.town_ids` ne contient que des IDs ; pas de populations annuelles sauvegardées |
| Note brute cargo 0, moyenne par aéroport coté | 143,91 / 141,66 | 158,18 / 162,46 | 150,54 / 156,14 | `.endpoint_cargo_stats[].cargo["0"].rating`, dédoublonné par station et partie ; qualification ci-dessous |
| Temps réellement à quai | **inconnu** | **inconnu** | **inconnu** | Pas de chronologie comparable d'occupation des terminaux |
| Résidu de délai des hubs, Opex seul, jours | 2,51 | 10,08 | 12,91 | `C121_HUB_DELAY days`, dernière valeur par station et année ; 116/120/119 stations observées ; **estimation**, inclut congestion et écarts de modèle |
| Facteur nominal d'entretien du modèle | 197,39 / 215,88 (×0,914) | 170,46 / 227,03 (×0,751) | 161,96 / 233,61 (×0,693) | Champ `AVI.running_cost`, pondéré par `air_engine_counts` ; pas une facture, pas le coût aéroportuaire |
| Entretien réellement payé par avion, aéroport compris | **inconnu** | **inconnu** | **inconnu** | `line_telemetry.unavailable_fields=[revenue,running_cost]` ; coûts d'infrastructure non attribués aux véhicules |
| Amortissement dans le profit véhicule retenu | **aucune charge** | **aucune charge** | **aucune charge** | 15.3 `vehicle.cpp:1270` diminue `value` ; `aircraft_cmd.cpp:468` retire les coûts de marche du profit ; `.vehicle_value` est un stock, pas une charge |

La table moteurs est résolue par les noms `MA`/`AVI`, sans offset d'EngineID imposé : `table/engines.h:322` et `:613`, macro `:602` ; `engine.cpp:357`, `script/api/script_engine.cpp:114` pour les vitesses. L'usage des modèles d'origine suppose ici l'absence de propriétés NewGRF remplaçantes ; les données ne fournissent pas les vitesses effectives individuelles.

**Notes et stock :** le harnais **figé** de cette campagne teste encore `status & 1` (Acceptance) dans `_station_route_index` (`..._bundle/harness/sweeps/bench_1v1_5y_20seeds.py:800`), défaut historique corrigé par V270 ensuite. Les notes ci-dessus décrivent les extrémités retenues par ce prédicat, pas toutes les sources cotées. On ne leur attribue aucun effet causal. `max_waiting_cargo` est un maximum/statistique du recalcul de note (`station_base.h:222`, `station_cmd.cpp:3965`), **pas le stock instantané** de `AIStation.GetCargoWaiting`. Il ne sert pas à estimer rétrospectivement combien de refus V274 auraient eu lieu.

**Composition des services :** AAA exploite aussi courrier seul et cargo 5. En 1979, ses lignes aux mêmes cargos `{0,2}` regroupent 111 avions à **75 993 £/avion**, contre nos 455 à 20 246 £. Les lignes courrier seul : 29 à 83 054 £ ; cargo 5 : 10 à 45 665 £. Le mélange de cargos ne supprime donc pas l'écart. Le script produit `cargo_services` sans imposer de numéro de cargo.

**Sources exactes supplémentaires :** les recensements moteurs/capacités de décembre sont aux lignes JSONL Opex/AAA **169/170, 335/336, 1055/1056** (1973), **425/426, 539/540, 1257/1258** (1976), **669/670, 719/720, 1439/1440** (1979). Les pointeurs des instantanés annuels et les lignes de chacun des journaux figurent dans le JSON dérivé.

Exemples graine 42, `reference_seed42_r0.log` :

- `:25343` : `LINE_REVENUE line=0 year=1973 real_rev=165683 real_prof=144338 real_run=21345 vehs=3` ; `:37850` en 1976 : 219950/191490/28460/4 ; `:49820` en 1979 : 208912/180452/28460/4. **Ces rapports de janvier portent sur l'année précédente** (`task_report.nut:258`). `real_run` est `GetRunningCost()` nominal annualisé et `real_rev=profit+runCost`, pas une facture et une recette observées séparément (`:260`, `:357`). Ils ne complètent pas les cellules inconnues du tableau.
- `:49730` : `C121_HUB_DELAY station=0 days=4.7231307` ; ce n'est pas une mesure de quai.
- `:49938` : `C121_FLEET_MARGINAL line=28 year=1979 added=1 obs_profit=-35346 obs_revenue=-27998 avg_profit=8873 samples=3`. C'est une différence annuelle avant/après renfort, après amortissement prévu, pas un effet causal isolé (modèles, villes et concurrence changent).

Dans les journaux des années de rapport 1973/1976/1979, les marges C121 non positives sont respectivement **0/7, 27/62, 6/24**. Le filtre existant `projects_builders.nut:170` refuse déjà une croissance sous cible lorsque la dernière marge observée est négative : **il n'est pas absent**. V274 agit avant de devoir attendre cette mesure après achat.

## Cause dans notre code et intervention unique

Chemins vérifiés sur la base identique au bundle :

1. `air_trip.nut:222`, `globals_pre.nut:668` : jusqu'à trois routes par aéroport. Ce partage correspond au facteur topologique mesuré ; il n'est pas changé par V274.
2. `task_air.nut:579`, `:605`, `:699` : sous `targetAirPlanes`, une ligne positive après observation peut recevoir un renfort ; la branche C121 contourne le test de stock C14. La positivité totale d'une ligne ne démontre pas la rentabilité du prochain avion.
3. `task_air.nut:720` : hors cible, `max(waitA,waitB)` lit le stock **entier** des stations. Chaque route d'un hub peut présenter le même stock comme son propre besoin. Une seule extrémité chargée suffit au test historique.
4. `air_trip.nut:155` et `:193`, appelé `task_air.nut:653` : le plafond de cadence limite la congestion physique à partir du cycle et du nombre de routes. C'est un plafond de piste, pas une preuve de demande ; il n'est ni retiré ni remplacé.
5. `air_construction.nut:381`, `air_fleet.nut:252` : ordres `OF_NONE` aux deux bouts. AAA force bien `isDestFullLoadOrder=true` dans son `air.nut:201`. La correction ne modifie pas les ordres.

**Correction :** `v274_air_growth_stock` entier 0/1, quatre difficultés à 0, globale entière à 0 et lecture unique dans `settings.nut:104` ; déclaration `info.nut:696`. Aux deux entrées, un seul test entier `==1` ouvre le chemin ; à 0 aucun auxiliaire, lecture API, index ni journal V274 n'est exécuté. Il y a deux sites nécessaires : publication du renfort (`task_air.nut:575`) et achat (`air_fleet.nut:111`).

`OpexV274AirGrowthStock` (`air_fleet.nut:77`) relève la plus grande capacité **vivante** de la ligne pour son cargo principal, le stock actuel de chaque station et ses routes AIR vivantes. Il impose :

```text
cap > 0 ; routesA > 0 ; routesB > 0
waitA >= cap × routesA ET waitB >= cap × routesB
```

Exemple : 90 passagers au hub et trois routes ne constituent plus une capacité disponible de 90 pour chacune ; il faut 270 au hub et 90 à l'autre extrémité si elle n'a qu'une route. C'est une allocation **prudente à parts égales**, pas une estimation des préférences des voyageurs. Elle pourrait sous-servir une route très productive : raison de garder le défaut à 0.

Le contrôle intervient sous cible comme hors cible, réutilise l'index de routes de la passe, puis recompte au dernier moment avant chaque achat, y compris un projet de portefeuille devenu caduc. Un achat précédent peut donc rendre le suivant inéligible. Les avions initiaux, la modernisation V252 et la reconstitution après crash suivent leurs chemins existants. Aucun nouvel état de décision n'est ajouté à une ligne ni au Save/Load : le réglage est relu au démarrage comme les autres réglages, les observations sont reconstruites depuis le jeu.

Journal sous `DECISION_LOG` uniquement : `OpexDecide("V274", ...)`, champs `phase=plan|buy action=allow|block line stationA stationB cargo cap waitA waitB routesA routesB`. Un `allow` est une permission locale, pas une preuve d'achat : il faut ensuite `FLEET_PROJECT action=grow` ou `AIR_FLEET action=grow` sur cette ligne.

Ce changement ne choisit aucun moteur, ne construit pas un second aéroport, ne préempte pas un créneau et n'ajoute aucune escale. Il ne remet pas en service C81 : aucun plein chargement imposé. Il ne rétablit pas l'ancien plafond de demande théorique : il contrôle du stock **observé, partagé et relu avant dépense**, sans toucher au plafond physique. Il ne change pas la distribution des cargaisons. Le nombre de routes reste libre jusqu'aux limites actuelles ; seule leur croissance de flotte est filtrée.

## Coût et validation

- Défaut 0 : un test entier par ligne arrivant à ce point de la passe de redimensionnement, et un par appel à `OpexAirAddPlane`. Pas de scan supplémentaire. Cela ne garantit pas une trajectoire au bit près par rapport à l'ancien arbre : tout ajout peut décaler les opcodes.
- Activé : scan des appareils de la ligne pour leur capacité ; deux lectures de stock ; index des routes construit une fois par passe et réutilisé par la cadence ; à l'achat, deux scans bornés par les lignes/avions déjà présents via `OpexAirLiveRoutesAtAirport`. Pas de recherche de site, A*, sommeil, ni état persistant. Le journal produit des chaînes uniquement avec `decision_log`. **Nombre d'opcodes réel non mesuré** ; aucune valeur numérique inventée.
- Tests de décomposition : sélection exclusive de référence, ratios pondérés, IDs locaux par graine, données absentes, doublons/santé, rapprochement du recensement et résolution des moteurs par nom. Tests V274 : déclaration/chargement/défauts, gardes et ordre avant achat, bornes du prédicat partagé extrait du code, capacités vivantes, absence de mutation/ordres et raccord des auxiliaires.
- Contrôles statiques : délimiteurs des cinq fichiers `.nut` modifiés ; identifiants locaux et externes de la nouvelle fonction ; aucun identifiant réservé `clone`/`base`/`parent`, aucune closure/capture, aucune méthode `array.find/map/filter/reduce` ajoutée ; définition et deux sites d'appel de l'auxiliaire, module déjà chargé par `builder_air.nut`. Relecture du diff et `git diff --check`.
- Suite complète demandée : **2 096 tests, OK**, trois tests ignorés et trois échecs attendus. Journal : `results/v253b_diagnostic/unittest.log`. Les tests Python ne compilent pas Squirrel. Smoke et mesures économiques **non exécutés par interdiction utilisateur**.

Reproduction du diagnostic, sans partie :

```bash
python3 -X utf8 sweeps/v274_air_decomposition.py \
  /home/deploy/projects/wt-v273/results/v273_expo_3x10_20261019.json \
  --openttd-src /home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src \
  > results/v253b_diagnostic/decomposition.json
python3 -X utf8 -m unittest discover -s sweeps -p 'test_*.py'
```

## Exposition proposée, non lancée

Intervention comportementale 0→1, **même arbre** pour les deux bras ; autres réglages aux défauts courants, V252=2. Référence `OpexAI[decision_log=1,v274_air_growth_stock=0]`, variante `OpexAI[decision_log=1,v274_air_growth_stock=1]`, chacun contre la même AAA figée. `--script-debug --line-telemetry`, graines **42, 7, 1234**, **10 ans**, une répétition, multimode. Ce 3×10 est un diagnostic de mécanisme, sans verdict d'adoption ; il est proposé parce que le problème de densité est tardif, pas comme nouvelle porte économique.

Avant ce diagnostic, smoke causal 42 × 1 an pour compilation et santé. Manifestes, bundle et sorties neufs à figer après autorisation de banc ; aucun lancement depuis cette mission. Budget proposé : deux duels de smoke puis six duels de diagnostic ; plafond VPS 3 CPU / 2 Go / 3 workers si c'est le poste choisi. Arrêter sur erreur ou collecte incomplète.

Attendus pré-enregistrables : zéro `V274` en référence ; en variante, `block` avec `routesA>1` ou `routesB>1` et stocks insuffisants par route ; quelques `allow` quand **les deux** seuils sont atteints ; `buy` avant croissance effective et aucun achat refusé par le helper ; nombre de renforts et densité d'avions/aéroport plus bas à 1976/1979. Décompter par graine, année, phase et ligne ; ne pas compter les refus mensuels comme des observations indépendantes. Un `block phase=buy` doit empêcher l'achat, et non être suivi d'un `grow` issu de ce même appel.

Contreparties à suivre : aéroports/paires construits, stock réel et notes, remplissage **au départ par sens** à instrumenter séparément pour les deux IA (absent de la télémétrie actuelle), revenu/temps de vol/temps à quai réels, profit et valeur **Opex**. Une hausse du profit moyen par avion due à moins d'avions ne suffit pas si le profit compagnie baisse. Si le mécanisme s'expose et reste prometteur, décider avant résultats du protocole de qualification tardive et appliquer les portes autorisées ; aucune adoption sur ce 3×10.

FIN
