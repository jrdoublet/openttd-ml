# INVEST-STALL — point 1, attribution passive des refus (04/11/2026)

## Mandat et invariants

À la demande de l'utilisateur, réaliser **le point 1** de
[`invest_stall_obstacles_20261104.md`](invest_stall_obstacles_20261104.md) :
ventiler les raisons exactes de `invest_stall_recheck` et
`unsafe_or_busy` sur les graines 17 et 65537, sans modifier
aucune décision, aucune sécurité, ni le défaut `invest_stall=0`.

Arbre : `/openttd-ml/.wt_sibling_20261102`, branche
`exp/rail-sibling-20261102`, HEAD au lancement
`99f29d9c858f390de6193978a4f12d3fbdb48127`.
Les modifications préexistantes sont conservées. Aucun commit, push,
merge, reset ou nettoyage.

## Sonde livrée

- `invest_stall_fleet.nut` : identifiant corrélable
  `txn=ligne_vehicule_date` ; diagnostic indépendant de toutes
  les clauses `unsafe_or_busy` : transaction concurrente,
  recherche ferroviaire, état de ligne, gare partagée, cohérence
  des plans A/B. Lors d'un rejet V284, une liste de tous les
  prédicats échoués et une raison principale déterministe sont
  conservées. Le miroir économique de la marge est seulement
  consulté en cas de marge refusée et **n'autorise jamais un achat**.
- `task_v284.nut` : mêmes conditions originales de revalidation ;
  télémétrie additionnelle sous `DECISION_LOG` avant le `cancel`,
  `txn` aux étapes `pick`, `approach`, `depot`,
  `skip`, `done`, `rolled_back`. Le nouveau
  `traceStart` est un entier facultatif dans la transaction
  persistée, utilisé **uniquement** pour la corrélation et la
  durée ; les sauvegardes historiques sans ce champ restent admises.
- Après le premier essai, la sonde de `mixed_wagons` a été
  affinée en deux mesures : `loco_capacity` (capacité renvoyée
  par `AIEngine.GetCapacity`), et
  `wagon_mismatches` + index/ID du premier wagon différent.
  La sous-classification a finalement été **observée en moteur**
  dans deux nouveaux smokes 1×6 (voir les résultats plus bas).
- `sweeps/invest_stall_diagnostic_off.py` enlève la nouvelle
  couche de télémétrie *avant* les projections déjà gelées.
  `sweeps/invest_stall_platform_off.py` tient également
  compte d'une réservation RAIL-LONG v3 récemment intégrée
  par un autre agent, sans réécrire le fixture.
  `sweeps/test_invest_stall_platform.py` et
  `sweeps/test_invest_stall_diagnostic_20261104.py`
  vérifient les empreintes byte-pour-byte, l'inversion,
  les appels uniquement sur rejet et le décodage de traces.
- `sweeps/analyse_invest_stall_diagnostic.py` transforme
  les journaux moteur en CSV de chaque refus et JSON des
  causes principales/simultanées et identifiants de
  transactions, avec refus d'écraser les sorties. Le lecteur
  fournit aussi `mixed_wagons_subcauses` : `loco_capacity_only`,
  `wagon_ids_only`, `both`, `unmeasured`, ou mesure incohérente.
  Il ne présume jamais que les anciens logs contiennent les
  nouveaux champs. La note JSON n'impose plus abusivement `2×8`
  à toutes les campagnes.

## Reproduction réelle complète (avant la sous-sonde locomotive/wagon)

Campagne **`invest_stall_probe_2x8_20261104_a`** :
OpenTTD 15.3, NoAI 15, OpenGFX 7.1, 256×256, départ 1970,
graines **17 et 65537**, huit ans, OpexAI rail seul avec
`rail_sibling=1,rail_open=1,invest_stall=1` et AAAHogEx
ROAD/TRAM/SHIP/AIR désactivés, `--probes 6 --script-debug`,
9 CPU, 8 GiB, un seul conteneur. Image Docker
`sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31`.
Bundle source gelé :
`071e51b440cc105aab5adf3fcd56415d9e02fbd2d575aab487b224488227b12c`.

Commande exécutée, en ajoutant `--mount-root` vers le parent Windows
du worktree :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign invest_stall_probe_2x8_20261104_a --policy-id invest_stall_probe --reference 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,invest_stall=1]' --years 8 --seeds 17 65537 --start-year 1970 --map-size 8 --probes 6 --script-debug --aaahogex-setting disable_veh_roadveh=1 --aaahogex-setting disable_veh_tram=1 --aaahogex-setting disable_veh_aircraft=1 --aaahogex-setting disable_veh_ship=1 --cpus 9 --memory 8g --max-workers 9 --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --out results/invest_stall_probe_2x8_20261104_a.json
```

**2/2 parties complètes**, 1977 atteint, aucun marqueur fatal
Squirrel/NoAI. Ceci est un **diagnostic de fonctionnement**, pas un
duel ON/OFF de qualification ; les écarts Opex/AAA ne constituent
pas une preuve d'amélioration INVEST-STALL.

Les traces sont dans
`results/invest_stall_probe_2x8_20261104_a_engine/`,
le résumé et la table détaillée dans
`results/invest_stall_probe_reasons_2x8_20261104_a.json`
et `.csv`.

### Attribution

| Refus générique | Graine 17 | Graine 65537 | Total |
| --- | ---: | ---: | ---: |
| `invest_stall_recheck`, diagnostic `mixed_wagons` | **17** | **14** | **31** |
| `unsafe_or_busy`, primaire `rail_search` | 2 | 8 | 10 |
| `unsafe_or_busy`, primaire `unsafe_shared_station_a/b` | 8 | 2 | 10 |
| **Total** | **27** | **24** | **51** |

**Couverture des refus : 51/51 = 100 %**, avec exactement un
`event=diagnostic` correspondant à chaque refus générique.
**Aucun `unclassified`**. Ce chiffre mesure l'attribution de
chaque refus à une garde identifiable, **pas** l'identification
du mécanisme qui rend éventuellement la garde erronée.

Sur les 31 revalidations `mixed_wagons` :

- La marge recalculée reste **positive dans 31/31 cas**
  (`margin_detail=positive`) : perte de rentabilité,
  insuffisance de caisse et changement de production ne
  déclenchent pas ces 31 annulations.
- Aucun autre prédicat de revalidation n'a été enregistré
  comme échoué simultanément.
- La condition en cause regroupe encore deux sous-conditions
  `AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle)) == 0`
  et identité du type de **chaque wagon**. La nouvelle
  télémétrie `loco_capacity` / `wagon_mismatches`
  ne figurait **pas dans ce premier bundle**. À cette étape,
  la valeur API `-1` n'était qu'une hypothèse ; elle a depuis
  été mesurée dans les deux nouveaux smokes décrits ci-dessous.

Sur les 20 refus de quais :

- **20/20** présentent un partage de gare,
  **10/20** simultanément une recherche rail active ;
  les événements primaires `rail_search` sont donc des
  cas de *deux* causes simultanées, non des gares sûres.
- Graine **17**, ligne **27** : partage de la **gare B**
  (`unsafe_shared_station_b`), 10/10.
- Graine **65537**, ligne **18** : partage de la
  **gare A** (`unsafe_shared_station_a`), 10/10.
  Elle a aussi 8 tuiles de quai contre une cible maximale
  de 7 : le planificateur ne peut de toute façon pas
  l'agrandir dans cette version. Ce plafond reste un
  problème distinct qui n'a pas provoqué directement
  `unsafe_or_busy`.

La campagne instrumentée n'a pas reproduit exactement
les **54** refus agrégés (30+24) de l'ancien 2×8 :
elle en compte **51** (31+20). Les sondes activées
changent le coût en opcodes/les ordonnancements possibles ;
les pourcentages présentés concernent **ce nouveau bundle**,
pas une attribution rétroactive certaine des anciennes
occurrences. Les deux graines demeurent identiques.

## Reprise du 04/11 : sous-classification prête, banc concurrent

Le décodeur a été complété pour distinguer les sous-conditions à
partir des champs existants, **sans changement du code de décision**.
Son application en lecture seule aux anciens journaux attribue
`unmeasured` aux **17** cas de la graine 17 et aux **14** de la
graine 65537 : aucun ancien événement ne possède les deux champs
nécessaires. Cette sortie ne prouve donc aucune des sous-causes.

Un nouveau smoke rail seul **1×6**, graine 17, 1970–1975, était
préparé sous le nom inédit
`invest_stall_mixed_subprobe_seed17_1x6_20261104_b`.
Le précontrôle juste avant le lanceur a détecté un conteneur
`openttd-lab:latest` nommé `great_bohr` appartenant à un autre
banc : **exécution refusée**, aucun résultat ni bundle de cette
nouvelle campagne créé. Un contrôle ultérieur l'a retrouvé actif.
Il faut lancer ce seul smoke lorsque Docker sera libre pour
observer `loco_capacity` et `wagon_mismatches` en moteur.

Après l'ajout d'un test de décodeur à cas absents/incohérents,
**57 tests INVEST-STALL**, 12 tests V284 et 21 tests v3 passent,
`py_compile` et `git diff --check` sont propres. Aucun défaut,
garde ni fixture modifié.

## Validation finale de la sous-sonde : 2 × 1 graine × 6 ans

Le 04/11, Docker étant libre, deux nouvelles campagnes consécutives,
**1970–1975**, ont été exécutées avec le **même bundle**
`dd1fb8e341486444bf2afd07fa4c86368c02b84e12e65660bd7bca1f9893cc3d` :

- `invest_stall_mixed_subprobe_seed17_1x6_20261104_b` ;
- `invest_stall_mixed_subprobe_seed65537_1x6_20261104_b`.

OpexAI `mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,invest_stall=1`
face à AAAHogEx avec ROAD/TRAM/AIR/SHIP désactivés ; carte 256²,
`--probes 6 --script-debug`, 9 CPU, 8 GiB et au maximum 9 workers.
OpenTTD 15.3 / NoAI 15 / OpenGFX 7.1 ; image Docker
`sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31`.
**2/2 parties `complete/complete`**, `exit_code=0` et aucun marqueur
fatal trouvé dans les journaux.

| Mesure sur ces nouveaux smokes | Graine 17 | Graine 65537 | Total |
| --- | ---: | ---: | ---: |
| Refus `invest_stall_recheck` | 5 | 5 | **10** |
| `loco_capacity=-1`, `wagon_mismatches=0` | 5 | 5 | **10** |
| `margin_detail=positive` | 5 | 5 | **10** |
| Refus `unsafe_or_busy` avec gare partagée | 5 | 5 | 10 |
| Dont recherche rail simultanée | 2 | 3 | 5 |
| Refus génériques associés à un diagnostic | 10/10 | 10/10 | **20/20** |

Les dix rejets sont en phase `depot` après `pick` et `approach` ;
les dix ont un `rolled_back`. Au total, **13** sélections de wagon,
**3** `approach_timeout`, **10** réévaluations et **0** `done`.
Chaque revalidation échoue sur la **seule** clause `mixed_wagons`,
alors que la marge reste positive, la composition contient uniquement
le type de wagon attendu (`wagon_mismatches=0`), et le retour de
`AIEngine.GetCapacity(AIVehicle.GetEngineType(oldVehicle))` vaut
**`-1`** au lieu des **`0`** exigés par la garde dans `task_v284.nut`.
Les durées entre sélection et refus observées sont de **13 à 68 jours**.

Il s'agit donc, sur **les dix événements de ce bundle**, d'un refus
causé exclusivement par le test `GetCapacity(...) == 0`, et **non**
par une divergence de type des wagons, un changement de flotte ou un
déficit économique. Ce résultat ne prouve pas que `-1` peut être accepté
pour *tout* engin : une correction P1 devra certifier l'engin comme
locomotive adaptée et préserver la comparaison individuelle des wagons.
Il ne faut pas attribuer rétrospectivement ces valeurs aux 31 rejets
du bundle 2×8 antérieur qui ne disposait pas de cette sous-sonde.

Les sorties sont conservées sous :

- `results/invest_stall_mixed_subprobe_seed17_1x6_20261104_b*` et
  `results/invest_stall_mixed_subprobe_seed65537_1x6_20261104_b*` ;
- `results/invest_stall_mixed_subprobe_reasons_seed17_1x6_20261104_b.csv/.json` ;
- `results/invest_stall_mixed_subprobe_reasons_seed65537_1x6_20261104_b.csv/.json`.

Les profits annuels OpexAI/AAAHogEx à fin 1975 sont respectivement
**1 150 707 / 1 603 957 £** (graine 17) et
**1 778 044 / 2 798 688 £** (graine 65537).
Ce sont des **duels descriptifs entre IA**, pas une mesure causale
`invest_stall=1` contre `invest_stall=0`.

## Validation et limites

- **57 tests INVEST-STALL**, **12 tests V284** et
  **21 tests RAIL-LONG v3** passent après instrumentation,
  et `git diff --check` est propre.
- La projection OFF du nouveau diagnostic retrouve les hashes
  historiques des fichiers INVEST-STALL quai, puis leur état
  pré-extension, sans modifier les fixtures gelées.
- L'ancien Save/Load générique de 1975 reste une preuve
  d'amorçage, **pas** d'une transaction de quai interrompue.
- Le blocage initial par un autre conteneur `openttd-lab` a été
  surmonté : les **deux smokes finaux** ont été exécutés
  séquentiellement et sans concurrence constatée.
- Aucun achat `INVEST_STALL kind=wagon done` ni
  `kind=platform done` n'a été ajouté par ces modifications
  de télémétrie.

## Décision

**Point 1 réalisé** pour la ventilation des deux grands refus,
objectif ≥90 % dépassé (**100 % sur le nouveau 2×8**).
Cause dominante vérifiée : contrôle `mixed_wagons`
sur les achats, avec marge toujours positive.
Cause quai vérifiée : **gare partagée sur toutes les occurrences**,
avec chevauchement fréquent d'une recherche rail.

La distinction `loco_capacity`/`wagon_mismatches` est désormais
**prouvée en moteur pour 10/10 refus sur les deux graines**.
La prochaine étape, **P1 distincte de la mission P0**, est de
concevoir et vérifier une garde de locomotive conforme à l'API,
sans lever l'exigence d'homogénéité réelle des wagons ; elle devra
obtenir des achats `done` et des preuves physiques avant toute
qualification économique. Les extensions de quais, rollback et
Save/Load en cours de transaction restent également non qualifiés.
**Ne pas assouplir** les autres contrôles de sécurité/rentabilité.
Conserver `invest_stall=0`, aucun commit ni publication.
