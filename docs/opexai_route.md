# Le mode route d'OpexAI

État au **2026-08-30**. Ce document décrit ce que le mode route fait, ce qui a été mesuré, et ce
qui reste ouvert. Il remplace la note historique sur la « liaison bus v1 », qui décrivait une
transaction unique et désactivée.

---

## 1. Ce que le mode fait

Une **phase annuelle** (`OpexAI::_tryBuildRoads`, `main.nut`) qui bâtit jusqu'à
`ROAD_MAX_NEW_LINES_PER_YEAR = 3` petites lignes routières, dans la bande **5 à 25 tuiles** — celle
que le rail refuse structurellement (`MIN_DISTANCE = 25` dans `candidates.nut`, une mesure : sous
25 tuiles le profit médian d'une ligne **rail** est négatif).

Trois familles de candidats (`OpexBuildRoadCandidates`, `candidates.nut`) :

| famille | véhicule | arrêt | sens |
|---|---|---|---|
| ville ↔ ville, passagers | bus | arrêt de bus | bidirectionnel |
| industrie → industrie | camion | aire de chargement | **une seule direction** |
| industrie → ville | camion | aire de chargement | **une seule direction** |

Le type d'arrêt est **imposé par le cargo**, jamais choisi : un bus ne chargera jamais sur une aire
de chargement camion (`docs/mecanique_jeu.md` §11). `OpexRoadStopKind` est le seul endroit qui en
décide.

Réglage de partie **`road_mode`** (défaut 1). À 0, la baseline rail retrouve *exactement* son
chemin d'opcodes antérieur : le catalogue routier n'est même pas rafraîchi.

## 2. Les trois décisions d'allocation

1. **Le rail choisit en premier.** `_tryBuildRoads` tourne **après** `_tryBuild`. Les deux modes ne
   se disputent jamais la même *paire* (bandes de distance disjointes) mais bien les mêmes
   *origines* et la même trésorerie ; le rail vaut un ordre de grandeur de plus par ligne, donc il
   sert d'abord et la route prend ce qui reste.
2. **Une ligne routière ne verrouille rien pour le rail.** Elle vit dans `_lines` (pour être
   rapportée et mise au rebut par le même code) mais `OpexOriginServed(..., includeRoad = false)` et
   `_tooClose` l'ignorent. Une desserte de bus de 12 tuiles n'épuise pas une ville, et un arrêt de
   rayon 3 ne cannibalise pas le bassin d'une gare rail.
3. **Deux plafonds annuels**, tous deux arbitraires : 3 lignes neuves, 6 tentatives. Le second
   existe parce qu'un plan qui échoue coûte quand même ses sondes de site.

## 3. Le modèle économique (`OpexRoadLineEconomics`, `economy.nut`)

Repris du rail, avec trois écarts, chacun justifié :

- **`MAX_ROAD_VEHICLES = 2`.** Un arrêt n'accueille que deux véhicules à la fois ; au-delà ils font
  la queue sur la route et se bloquent (`docs/mecanique_jeu.md` §11). Ce n'est pas une précaution,
  c'est la règle du jeu. Le levier de volume est le **multistop** (`road_multistop`, défaut 0) :
  mesuré, le second arrêt se pose, les 4 véhicules ne paient pas (§7 item 4).
- **`ROAD_SPEED_EFFICIENCY_PCT = 60`.** Mesuré le 2026-08-30, **pas retuné**.
  Panneau `RY`, n = 53 (`docs/opex_road_speed_yield.json`). Fret en marche =
  catalogue (1,00) ; pax 0,75. Réel / 60 % : 1,27 pax, 1,71 fret. Instantané,
  pas un temps de trajet. Le 60 % est pessimiste en croisière. Le **0,75 pax**
  est le plafond 3/4 du modèle réaliste sur un L d'axes (`mecanique_jeu.md` §2),
  pas une raison de retuner. Wiki 37 km-ish/h/jour = modèle original, défaut
  15.3 = réaliste. Pas de modèle de traction route.
- **La durée de trajet suit le tracé**, et ici tracé et distance Manhattan coïncident (le tracé est
  un L de Manhattan), ce qui autorise la même formule sans facteur de détour.

Les ordres appliquent la leçon du fret rail du 2026-08-28 : une ligne de fret est à sens unique,
donc `OF_FULL_LOAD_ANY` à la source et **`OF_NONE` au puits**. Le pax fait l'inverse du rail et ne
charge jamais à plein : sur une ligne courte, la note de gare dépend à 51 % du délai depuis le
dernier ramassage — un bus qui attend d'être plein détruit ce que la ligne a de bon.

## 4. 🔴 Les quatre bugs que la mise en service a révélés

Tous mesurés sur la campagne graine 42 (`docs/opex_road_20y_42.json`), tous corrigés.

1. **`clone` est un mot réservé de Squirrel.** `local clone = ...` fait échouer la compilation du
   fichier entier. L'échec est presque muet : une ligne dans la sortie OpenTTD, aucun panneau, une
   compagnie qui existe sans rien construire. Symptôme au dépouillement : `company_value = 1`.
2. **`ERR_LAND_SLOPED_WRONG` sur la pose du tracé** (≈ la moitié de 21 échecs sur 21 tentatives).
   `AITestMode` valide chaque arête **isolément**, sur la carte d'avant la pose. Or une tuile qui
   reçoit des bits de route sur **deux axes** — le coin du L, la façade d'un arrêt, la façade du
   dépôt — n'est constructible en deux axes que si elle est **plate**. Chaque arête passait son test
   isolé et la pose réelle échouait dès que la deuxième direction arrivait. Correctif :
   `OpexRoadIsFlat` sur ces seules tuiles de jonction (une longue portion droite en pente reste
   acceptée, elle ne porte qu'un axe).
3. **`ERR_AREA_NOT_CLEAR` sur le dépôt** (l'autre moitié). Même dissymétrie plan/pose : les quatre
   voisins d'une façade sont testés avant la pose du tracé, et les deux qui sont dans l'axe **sont**
   le tracé. Vides au test, ils portent une route au moment de bâtir le dépôt. Correctif : le tracé
   est indexé et ses tuiles sont exclues des sites de dépôt.
4. **La liste de véhicules figée à la construction est fausse dès qu'un véhicule est remplacé.** Le
   renouvellement détruit l'ancien identifiant et OpenTTD **recycle** les identifiants libérés — une
   liste figée finit par ne plus rien désigner, ou par désigner le véhicule d'une autre ligne.
   Symptôme : trois lignes sur quatre finissant à `vehCount = 0` avec une note de gare de 48 à 60,
   et l'une repassant de 0 à 1 véhicule d'une année sur l'autre. Correctif : une ligne routière
   interroge sa gare (`AIVehicleList_Station`), ce qui est exact ici parce qu'un arrêt routier est
   toujours posé en `STATION_NEW` et n'est jamais joint.

## 5. Deux correctifs qui ne sont PAS du mode route

Découverts en mesurant la route, mais valables pour toute la compagnie. **Ne pas les attribuer au
mode route au banc.**

- **Renouvellement automatique** (`SetAutoRenewStatus(true)`, `-6` mois, plancher `CASH_RESERVE`).
  Un camion vit ~12 ans quand une locomotive en vit 20 à 30 : le mode d'échec ne se voyait pas tant
  que l'IA ne roulait qu'en rail sur 20 ans.
- **Détection de ligne morte** : la condition exigeait `ratingA <= 0`, et cette clause était fausse
  — **une gare conserve sa dernière note quand plus rien n'y passe**. La ligne OIL_ a roulé **onze
  ans à −842 par an** sans être mise au rebut, note figée à 67. Le revenu implicite suffit et ne
  ment pas. La prudence reste assurée par l'industrie source en souffrance et par
  `DEAD_STREAK_THRESHOLD` années consécutives.

## 6. Ce que la mesure donne (graine 42, 20 ans, `docs/opex_road_20y_42.json`)

**4 lignes routières, dont 3 de fret**, toutes vivantes à la dernière année avec leurs 2 véhicules :

| ligne | dist. | profit prédit | profit réel (dernier exercice) |
|---|---|---|---|
| COAL, industrie → industrie | 22 | 4 974 | 4 779 |
| OIL_, industrie → industrie | 24 | 4 238 | 917 (production source tombée à 18) |
| WOOD, industrie → industrie | 16 | 2 773 | 3 298 |
| PASS, ville ↔ ville | 23 | 1 031 | 10 715 |

> ⚠️ **Mesure antérieure au correctif « trajets chargés » du 2026-08-29**
> (`docs/mecanique_jeu.md` §1 ter). Depuis, la même graine donne **6 lignes routières (4 fret,
> 2 pax)** au lieu de 4 : le modèle passagers ne demande plus deux fois trop de véhicules, donc des
> candidats bus qui tombaient sous `ROAD_MIN_PROFIT_ANNUAL` passent désormais. Les chiffres du
> tableau ci-dessus restent valables comme illustration du comportement d'une ligne, pas comme
> décompte.

**Le modèle de fret est bien calibré** (rapport prédit/réel de 0,84 à 1,20 sur les années à
production stable) : `STATION_RATING_PCT = 50`, calibré sur le rail, tient aussi pour le camion.
**Le modèle pax sous-estime** : n = 12, médiane réel/prédit **3,91** (revenu 2,29), voir §7.1.
Pas un retuning : le 22 % de bassin est aussi le rail.

Coût : ~15 000 opcodes par plan, ~300 000 par construction, ~60 000 par an pour la génération de
candidats. Négligeable devant les ~270 M d'opcodes annuels.

## 6 bis. Le verdict du banc apparié

**Re-baseline courant (2026-08-30, `docs/bench_road_current.json`) :** 20 graines × 20 ans,
route active contre `road_mode=0`, avec traction et `road_pax_catchment_pct=86`.
`performance_history` **+15,3 %** (+70,35), t = **5,65**, 18/20 ; `company_value`
**+13,5 %**, t = **2,24**, 13/20. Le mode route est reconfirmé.

### Mesure historique (`docs/bench_v2_road.json`)

20 graines × 20 ans, `OpexAI` contre `OpexAI[road_mode=0]`. Les deux bras portent le
renouvellement automatique et le correctif de ligne morte : le banc isole donc **le mode route
seul**.

| métrique | écart apparié | t | graines gagnées | test des signes |
|---|---|---|---|---|
| `performance_history` | **+36,6 pts (+9,3 %)** | **2,03** | **16 / 20** | **p = 0,012** |
| `company_value` | +232 433 (+9,6 %) | 1,50 | 13 / 20 | p = 0,26 |

**Adopté**, sur `performance_history` — la métrique que le projet a désignée comme la bonne entre
variantes d'OpexAI, parce qu'elle est moins bruitée que `company_value` chez nous (CV 31 % contre
45 % sur ce banc). Le test des signes est ici la lecture la plus solide : 16 sur 20 ne s'obtient par
hasard qu'une fois sur cent.

`company_value` va dans le même sens (+9,6 %) mais ne tranche pas, et pour une raison identifiable
plutôt que par bruit diffus :

> 🔴 **Une graine sur vingt payait très cher — et ça ne survit pas à la traction.** Sur
> `docs/bench_v2_road.json`, 8675309 tombait de 1 460 136 à **1**. C'était la seule insolvabilité
> du banc. Divergence 1974 (165 793) → 1975 (104 677) pendant que le bras sans route restait à
> 155 000, puis érosion jusqu'à `company_value = 1` en 1985, cash collé à `CASH_RESERVE`.
>
> Sur l'arbre courant (`docs/bench_road_8675309.json`, 20 ans, même graine) : **2 368 267** avec
> la route contre **2 282 217** sans, emprunt 0, `months_of_bankruptcy` 0. Identiques au
> 1er janvier 1971. Campagne parallèle : **0 tentative routière** — des candidats sont classés
> (2 à 4/an en 1970-75) mais le `break` cash de `_tryBuildRoads` les coupe, et après le
> remboursement de 1976 `ROAD_MIN_PROFIT_ANNUAL` prend le relais. L'hypothèse « la route mange
> le cash du prochain rail » décrivait le `break` d'avant traction sur le classement rail ; le
> `continue` borné a fermé le trou. **Pas de garde-fou à écrire.** Le +9,3 % d'adoption n'a pas
> été rejoué après traction.

## 7. Ce qui reste ouvert, par impact estimé

✅ **Bassin pax route adopté (2026-08-30).** `road_pax_catchment_pct=86` devient le défaut :
`performance_history` +4,19 % (+22,2 points), t = 2,48, 14/20 graines ; `company_value`
−1,32 %, sans effet établi. `0` reconstitue le contrôle historique à 22 %. Le réglage ne
touche ni le rail ni le fret. Résultats : `docs/bench_road_pax_catchment.json`.

Items **fermés** : 0 (graine qui coulait, §6 bis), 1 (plancher pax, mesuré pas retuné),
2 (SITEA/B, sondes sur des maisons), 2 bis (TRACEX, 32 L + façade), 3 (classement
inter-modes, mesuré pas unifié), 4 (multistop, mécanisme oui, 4 véhicules non),
5 (`road_refleet=1`), 6 (`ROAD_SPEED_EFFICIENCY_PCT=60`, mesuré pas retuné).
**Ouverts** : plus rien de ce côté (`ROAD_SPEED_EFFICIENCY_PCT` mesuré, pas
retuné). L'item 2 du backlog général (villes enfermées) reste dernier.

1. ✅ **Le plancher `ROAD_MIN_PROFIT_ANNUAL = 1000` : mesuré, pas retuné** (2026-08-30).
   12 lignes pax, médiane réel/prédit **3,91** (revenu 2,29). Fret n = 6 : **1,21 / 1,03**.
   `docs/opex_road_predict_vs_actual.json`. Ce n'est pas la vitesse (le fret la partage).
   Ce n'est pas `ROAD_SPEED_EFFICIENCY_PCT` : `RY` donne pax 0,75 vs catalogue
   (1,27 vs 60 %), pas un ×4. C'est `TOWN_CATCHMENT_SHARE_PCT = 22` calé sur le
   rail, appliqué à un arrêt dans la ville.
   Le plancher coupe 76 % des paires en bande sur l'arbre courant. Ne pas le baisser ni
   monter le 22 — le 22 est aussi le rail. Une part de bassin route, si elle vient, est une
   constante propre, défaut 0, banc apparié.
2. ✅ **`SITEA` / `SITEB` : on sondait des maisons** (2026-08-30).
   `GetCargoProduction` est vrai sur le bâtiment, `IsBuildable` non. 48 sondes y passent.
   Filtre `IsBuildable` + plat, comme `OpexStationPlans`. 5 graines :
   SITE 14/18 → **0/11**, OK 2 → 6 (`docs/opex_road_sitable_20y_5seeds.json`).
   TRACEX ensuite (2 bis). Le rayon et le plafond de sondes n'étaient pas le levier.
2 bis. ✅ **TRACEX** (2026-08-30). 32 L (plus le plafond à 12) et façade tournée
   vers l'autre extrémité. `nLong = 0`. TRACEX 5→2, OK 6→8, pax 2→4
   (`docs/opex_road_tracex_20y_5seeds.json`). Les 2 restants sont un L à travers
   un bâtiment. Pas Pathfinder.Road.
3. ✅ **Le classement routier et le classement rail ne sont pas à unifier**
   (2026-08-30). Panneau `RB`, n = 10, `docs/opex_road_rb_calibrate.json`.
   Plan OK médiane 31 440 opcodes contre `20+d` ≈ 42,5 iter (rapport 0,29).
   Un ratio route sur le plan réel (68 k–710 k) écrase le rail (médiane 5 040,
   `MIN_RATIO` 500). ⚠️ Pas de retuning de `BASE`. Le rail d'abord (§2) tient.
4. ✅ **Le multistop : le second arrêt se pose, les 4 véhicules ne paient pas**
   (2026-08-30). Réglage `road_multistop`, défaut 0. Identifiant du primaire, pas
   `STATION_JOIN_ADJACENT` nu. 5 graines contre TRACEX
   (`docs/opex_road_multistop_20y_5seeds.json`) : extra A 7/8, extra B 8/8, les
   deux 7/8. La ligne pax appariée (12345 L22) **8 905 → 1 781** à 4 bus. ⚠️
   Défaut 0. Le ×5 du wiki n'est pas là.
5. ✅ **Rebâtir la flotte d'une ligne tombée à zéro véhicule.** Réglage `road_refleet`, défaut 1.
   Le trou n'était pas n = 1 (pax 15 de `opex_road_20y_42.json` : 2→1→0, 9 000/an ; COAL de
   `opex_join_20y_42.json` : vide huit ans). Sur l'arbre courant (`docs/opex_refleet_20y_4seeds.json`,
   graine 42) la ligne COAL 15 passe 2→1 en 1982 et 1988 : `RF` ajoute 1 chaque fois, la note
   revient à 67, **jamais à zéro**. Auto-renouvellement ne suffit pas : il ne remplace pas un
   véhicule détruit. `OpexAI[road_refleet=0]` rallume l'abandon.
6. ✅ **`ROAD_SPEED_EFFICIENCY_PCT = 60` : mesuré, pas retuné** (2026-08-30).
   Panneau `RY`, 5 graines (`docs/opex_road_speed_yield.json`). n = 53
   (6 lignes, 0 sur 12345). Fret **1,00** vs catalogue, pax **0,75**.
   Réel / 60 % : **1,27** pax, **1,71** fret. Instantané, pas un temps de
   trajet. ⚠️ Pas de retuning. Le 3,91 pax n'est pas ceci.

## 8. Les pistes déjà écartées par la mesure — ne pas les reproposer

- Retuner `ROAD_SPEED_EFFICIENCY_PCT` sur un instantané de croisière : le 60 %
  est pessimiste (pax 0,75 / fret 1,00 vs catalogue) mais ce n'est pas un
  temps de trajet. Pas de modèle de traction route.
- `Pathfinder.Road` : 696 794 opcodes contre 171 356 pour le tracé Manhattan borné.
- Quatre véhicules via multistop : le second arrêt se pose (7/8), le profit de la
  ligne pax appariée s'effondre (8 905 → 1 781). Défaut 0.
- Arrêts traversants (`BuildDriveThroughRoadStation`) : 912 232 opcodes, aucun gain. C'est cette
  disposition en cul-de-sac qui impose d'écarter les **véhicules articulés** au catalogue.
- Distance du dépôt aux arrêts, testée de 1 à 4 tuiles : la variable pertinente était la
  **connexité**, pas la distance.
- `GetRoadDepotFrontTile` / `GetRoadStationFrontTile` ne prouvent **jamais** un raccordement : ils
  rendent la géométrie déclarée. Le seul prédicat est `AIRoad.AreRoadTilesConnected`.
