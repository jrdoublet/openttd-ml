# Liste des tâches

Backlog du projet depuis la bascule vers `OpexAI` (2026-08-28). Les tâches faites sortent de cette
liste ; l'historique reste dans les journaux `docs/journal_*.md`.

---

## 1. À lire et intégrer (demandé le 2026-08-28)

À traiter comme `docs/mecanique_jeu.md` : **pas une copie du wiki, mais règle + conséquence pour la
conception**, avec ce qui est vérifié et ce qui ne l'est pas.

| page | ce qu'on espère en tirer |
|---|---|
| [Community/Pseudo canals](https://wiki.openttd.org/en/Community/Pseudo%20canals) | technique de terrain sur l'eau ; à évaluer surtout pour son coût en opcodes |
| [transporttycoon.net/rail1](https://www.transporttycoon.net/rail1) … [rail6](https://www.transporttycoon.net/rail6) | série sur la construction ferroviaire : signalisation, débit, tracés |
| [transporttycoon.net/junctions](https://www.transporttycoon.net/junctions) | conception de jonctions — pertinent dès qu'`OpexAI` aura plusieurs lignes qui se croisent |

✅ **[Manual/Tips](https://wiki.openttd.org/en/Manual/Tips) lue et intégrée (2026-08-28)** — voir
`docs/mecanique_jeu.md` §9. La plupart des heuristiques utiles étaient déjà couvertes ailleurs dans
le document (note de gare §3, note d'autorité §7, vitesse/virages §2) ; l'apport net : ordres
partagés (`AIOrder.ShareOrders`, non exploité), boucles de gare routière pour le futur mode Route,
et une piste non vérifiée sur les avions qui diffuseraient mieux leur influence que le rail.

✅ **[Manual/Industries](https://wiki.openttd.org/en/Manual/Industries) lue et intégrée
(2026-08-28)** — voir `docs/mecanique_jeu.md` §10. La table des chaînes de production ne change
rien au code : `catalog.nut` interroge déjà l'API dynamiquement plutôt que coder les chaînes en
dur. L'apport net, deux pistes non vérifiées : (1) la croissance d'une industrie source dépend du
% de sa production transportée — mécanisme jamais modélisé, et **toujours pas mesuré** (la mention
d'un « écart fret ~4-6x » qui figurait ici était périmée : cet écart a été réfuté le même jour,
voir §3) ; (2) `difficulty.economy = false` confirme que la réduction de moitié de la production
primaire en récession est **sans objet** chez nous.

⚠️ Le contenu des pages restantes n'a **pas** été lu : les colonnes « ce qu'on espère » sont des
hypothèses de pertinence, pas des résumés.

---

## 0. Le vivier de candidats : rouvert, mesuré, et **il ne paie pas** (2026-08-29, seconde tranche)

**Fait, et le mécanisme marche.** La règle « un seul raccordement par origine » n'est plus une
guillotine à la génération : une paire dont **une seule** extrémité est servie passe désormais, et
c'est `_tooClose` / `OpexFindStationJoin` qui tranche — quai joint, ou rejet. Les deux extrémités
servies restent coupées sans appel. La règle de fond est intacte : **jamais deux gares à nous sur
la même origine**. Toute la relaxation est commandée par le réglage `station_join`, donc `0`
reproduit exactement le comportement d'avant.

Graine 42, 20 ans (`docs/opex_join_20y_42.json` contre `docs/opex_road_20y_42.json`) :

| | avant | après |
|---|---|---|
| candidats classés 1984-89 | 0 à 3 | **4 à 28** |
| lignes rail | 15 | 23 |
| `station_join` tentatives / réussies | 0 / 0 | 82 / 10 |
| `company_value` | 2 391 044 | 3 385 161 |
| utilisation du budget d'opcodes | ~29 % | ~46,5 % |

**Et le banc apparié, 20 graines × 20 ans** (`docs/bench_v2_vivier.json`, bras
`OpexAI[station_join=0]` contre `OpexAI`) **dit non** :

| métrique | delta | t | graines gagnées | verdict |
|---|---|---|---|---|
| `n_vehicles` | **+37,2 %** | **5,94** | **18/20** | l'IA bâtit massivement plus |
| `company_value` | −0,3 % | −0,03 | 9/20 | nul |
| `performance_history` | +6,5 % | 1,45 | 11/20 | sous le plancher (~12 %) |
| emprunt non remboursé | 2 → 4 graines | | | dégradé |

La variance explose : de −54,8 % (graine 12345) à +330,5 % (graine 100). **On construit beaucoup
plus pour la même valeur, en immobilisant plus de capital.** C'est exactement le piège que la
graine 42 seule aurait fait manquer (cf. « banc mono-graine insuffisant »).

⚠️ **Défaut `station_join` repassé à 0.** Le code, l'instrumentation et la mesure restent ; le
comportement par défaut ne change pas tant que la cause ci-dessous n'est pas corrigée.

**La cause supposée a été mesurée, et ce n'est pas elle** (2026-08-29,
`sweeps/opex_join_bias.py`, 10 graines × 20 ans, 155 lignes rail,
`docs/opex_join_factor_20y_10seeds.json` → `docs/opex_join_bias.json`).

Le rapport brut *revenu réel / revenu prédit* semblait donner **×1,53** en défaveur des lignes à
origine servie (IC 95 % [1,23 ; 2,02]), soit exactement le facteur cherché. C'est une illusion de
composition : ces lignes sont aussi **plus longues** (distance médiane **84 tuiles contre 47**) et
**plus tardives** (1981 contre 1975). Une fois type, distance et époque neutralisés **ensemble** :

| terme | effet | IC 95 % |
|---|---|---|
| `log(distance)` | ×0,76 | [0,53 ; 1,13] |
| `origine_servie` | **×0,81** | **[0,63 ; 1,03]** |
| type `freight` | ×0,97 | [0,70 ; 1,31] |
| époque (par décennie) | ×0,98 | [0,77 ; 1,22] |

L'intervalle de `origine_servie` **contient 1**. Le double comptage de `monthly` existe peut-être,
mais il ne dépasse pas le bruit à cet effectif et **n'explique pas le verdict du banc**. Corriger
`monthly` serait traiter le mauvais terme.

### 🔴 Ce que la mesure désigne à la place : l'étage 1 s'effondre avec la DISTANCE

`profit réel / profit prédit`, première année pleine, toutes lignes confondues :

| distance | rapport médian | n |
|---|---|---|
| < 50 tuiles | **1,47** | 62 |
| 50-75 | 0,41 | 37 |
| 75-100 | 0,44 | 40 |
| > 100 | **0,00** | 16 |

Au-delà de 100 tuiles, **la ligne médiane ne dégage aucun profit** — le modèle en promettait un.
Croisé avec l'époque, les deux effets s'ajoutent : sous 50 tuiles on passe de 1,51 (avant 1980) à
0,58 (1980+) ; au-delà de 100 tuiles on est à 0,00 dans les deux cas.

**Et c'est l'explication du banc.** Rouvrir le vivier ne fournit pas des jointures courtes et
rentables : il fournit des lignes **longues**, parce que les extrémités encore libres sont loin.
La population construite passe d'une médiane de 47 tuiles à 84. L'IA bâtit donc +37 % de véhicules
sur exactement le segment où `OpexLineEconomics` se trompe le plus — d'où « plus de construction,
pas plus de valeur ».

**Ce qu'il faut faire, dans l'ordre :**

1. ✅ **Recalibrer `OpexLineEconomics` en distance** — fait par la traction (§0 bis, `4a8e15e`) :
   quai, wagons, loco et vitesse réelle, plus le `ceil` des trajets. Ce n'est pas un facteur
   empirique en distance (écarté). Sur la graine 42 après traction, `profit réel / prédit` (année
   2) ne tombe plus à 0,00 au-delà de 100 tuiles (médianes 2,40 / 1,49 / 0,89 / 0,72, n petit).
   Le classement n'est plus celui du banc vivier.
2. ✅ **Rejouer le banc apparié `station_join` sur cet étage 1** — fait
   (`docs/bench_join_after_traction.json`, paire
   `docs/bench_join_after_traction_paired.json`). Même v1, `origin_sitable=0`.

   | métrique | delta | t | graines | verdict |
   |---|---|---|---|---|
   | `n_vehicles` | **+23,6 %** | **3,50** | **17/20** | l'IA bâtit encore plus |
   | `n_stations` | **−11,9 %** | **−3,61** | 4/20 | moins de gares (réemploi) |
   | `company_value` | +5,9 % | 0,96 | 11/20 | sous le plancher (~15 %) |
   | `performance_history` | +4,3 % | 1,34 | 12/20 | sous le plancher (~12 %) |
   | emprunt résiduel | 1 → 0 | | | petit plus |
   | minimum | 1,68 M → 1,27 M | | | le plancher recule |
   | CV | 0,31 → 0,36 | | | plus dispersé |

   L'effet de construction **survit à la traction** (un peu plus petit qu'à +37,2 %, t = 5,94,
   mais toujours massif). Moins de gares pour plus de véhicules : c'est le mécanisme de la
   jointure, pas un bug. **La valeur ne passe toujours pas le plancher.** La graine 42 recule
   de 18 %. ⚠️ **Défaut `station_join` reste 0.** Le partage de bassin (§2.9.3) est mesuré et
   ne paie pas davantage. Le spread n'est pas la suite.
3. Seulement ensuite, le **rendement des jointures** : `NOPLAN` en tue 68 sur 82, mais à
   32 280 opcodes et zéro itération d'A\*, soit 0,4 % du budget — c'est un levier de rendement,
   pas d'économie. AAAHogEx cherche dans l'enveloppe `station_spread` du groupe, pas un parallèle
   collé ; 68/82 `NOPLAN` est exactement « pas de parallèle libre ».
4. ⚠️ Ne **pas** corriger `monthly` pour une origine servie sur la foi du chiffre brut : c'est le
   piège que cette mesure vient de désamorcer. Le partage de stock **une fois la gare jointe**
   (plusieurs lignes, même `StationID`) est un autre terme, lui encore ouvert (§2.9.3).

⚠️ **Effet de bord à ne pas attribuer au mode route :** le rail affamé reprend la trésorerie, et
les lignes routières passent de 6 à 3 sur la graine 42. Le +9,3 % du mode route a été mesuré avec
`station_join` inerte ; il faudra le revérifier si ce réglage repasse à 1.

⚠️ **Ce que ce diagnostic dit AUSSI, et qu'il ne faut pas confondre avec l'item ci-dessus.** Le mur
de trésorerie des onze premières années n'est **pas** l'absence de réemprunt notée dans `info.nut` :
sur ces onze années **l'emprunt est déjà au maximum**. C'est le plafond d'emprunt lui-même face au
prix d'une ligne rail (82 000 à 240 000 pour 87 000 à 264 000 en caisse). La croissance précoce est
donc fixée par les bénéfices non distribués, et le seul levier est **la ligne bon marché** — ce qui
explique après coup pourquoi le mode route gagne au banc. Une hypothèse s'en déduit, **non
mesurée** : `_tryBuild` fait `break` sur la trésorerie en invoquant le « classement décroissant »,
or le classement est sur le **rapport**, pas sur le capital — un candidat moins bien classé mais
abordable n'est jamais examiné. Le préalable est d'instrumenter `candidate.capital` du `TOP_K` au
moment du `break` ; le correctif (`continue` borné plutôt que `break`) ne vaut d'être écrit
qu'ensuite.

---

## 0 bis. ✅ Traction dimensionnée — FAIT et fusionné (2026-08-29, `4a8e15e`)

Répond à l'item ci-dessus (« l'étage 1 s'effondre avec la distance ») par la cause structurelle :
la locomotive était **toujours la plus rapide** sans égard à ce qu'elle tracte, `WAGONS_PER_TRAIN`
était **figé à 5**, et le nombre de wagons n'était jamais dimensionné sur production × temps de
cycle. Les trois décisions sont maintenant calculées, et `SPEED_EFFICIENCY_PCT = 70` — abattement
forfaitaire jamais calibré — est remplacé par un modèle de vitesse réellement atteinte
(puissance, poids, effort de traction).

**Deux bugs mesurés corrigés au passage :**
- `OpexCeilDiv(30, legDays)` surestimait les trajets par mois de **1,27× en médiane** (155 lignes) ;
- `_tryBuild` faisait `break` sur la trésorerie alors que le classement porte sur le **rapport**,
  pas sur le **capital** — un candidat abordable moins bien classé n'était jamais examiné.

**Banc apparié 20 graines × 20 ans** (`docs/bench_traction_new.json` contre
`docs/bench_traction_base.json`) :

| | résultat |
|---|---|
| `company_value` | +7,7 %, t = 0,98, 14/20 — **sous le plancher, non établi** |
| `performance_history` | +10,9 %, t = 2,13, 12/20 — **non établi** |
| véhicules | **−44,8 %**, t = −8,41, p < 0,0001 |
| gares | **+31,1 %**, t = 6,08, p = 0,0001 |
| minimum sur 20 graines | 280 081 → **1 787 268 (×6,4)** |
| coefficient de variation | 0,41 → **0,28** |
| médiane | 2 569 706 → 2 234 065 (**−13 %**) |

⚠️ **Fusionné sur la correction de bugs et la robustesse, pas sur un gain de performance.** Ne pas
citer le +7,7 % comme un résultat acquis.

**Ce qui reste explicitement non établi, et devient le prochain travail :**

1. 🔶 **`NOPLAN` : cause nommée, filtre derrière `origin_sitable`, défaut 0.** Graine 42 / 20 ans
   (`docs/opex_traction_v3_20y_42.json` → `docs/opex_noplan_sitable_20y_42.json`) : 23 `NOPLAN`
   sur 46 tentatives → **0** avec le filtre allumé. Le seau a été éclaté (`SITEA`/`SITEB`/`SITEAB`/
   `ECON`, panneau `PS`). La pente et la démolition ont été mesurées **inertes** (`nCargo=0`) et
   retirées. `OpexRailOriginSitable` écarte une source fret sans tuile de terre voyant le cargo.

   **Banc apparié 20 graines × 20 ans** (`docs/bench_noplan_sitable.json` contre
   `docs/bench_traction_new.json`, paire `docs/bench_noplan_sitable_paired.json`) :

   | métrique | delta | t | graines | verdict |
   |---|---|---|---|---|
   | `company_value` | +4,0 % | 0,50 | 11/20 | sous le plancher (~15 %) |
   | `performance_history` | +1,9 % | 0,85 | 11/20 | sous le plancher (~12 %) |
   | véhicules | −1,1 % | −0,26 | 8/20 | nul |
   | emprunt résiduel | 1 → **0** graine | | | petit plus |
   | minimum | 1 787 268 → 1 184 388 | | | le plancher recule |
   | CV | 0,28 → 0,34 | | | plus dispersé |

   La graine 42 seule recule de 28 %. L'éventail va de −52 % (424242) à +108 % (12345). **Pas un
   gain de valeur, pas un gain de robustesse.** ⚠️ **Défaut `origin_sitable` = 0.** Le code et la
   mesure restent ; `OpexAI[origin_sitable=1]` rallume le filtre. Le classement à 0 est celui
   d'avant. Le mécanisme (ne plus brûler ~14 M d'opcodes) n'est établi que sur la graine 42 ;
   `bench_v2` ne lit pas les `NOPLAN`.
2. **Le repli sur quai plus court n'a été exercé par aucune construction réussie** (`PD` : 0 repli
   observé, traction v3 et sitable, 20+19 lignes). Les quais voulus sont déjà 2 ou 3 tuiles ;
   les échecs restants après `origin_sitable` sont `ABND`/`TRKFAIL` (site trouvé). Ce n'est pas
   un levier de croissance — laisser jusqu'à ce qu'un `PD` montre un raccourcissement.
3. ✅ **`station_join` : v1 en place, défaut 0.** Banc post-traction : construction sans
   valeur. `basin_share` mesuré ensuite : véhicules nuls, gares +12,9 %, valeur sous le
   plancher. Les deux défauts restent 0. Note AAAHogEx : `docs/aaahogex_rail_join.md`.

---

## 1 bis. Mode route : ouvert, mesuré, et ce qui reste (2026-08-29)

**✅ Adopté au banc apparié** (`docs/bench_v2_road.json`, 20 graines × 20 ans) :
`performance_history` **+9,3 %, t = 2,03, 16 graines sur 20, test des signes p = 0,012**.
`company_value` +9,6 % mais t = 1,50 seulement, et otage d'une graine — voir le point 0 ci-dessous.

**Fait.** Le mode route n'est plus une liaison bus unique et désactivée : c'est une phase annuelle
qui bâtit jusqu'à 3 petites lignes courtes, dont du **fret par camion** (industrie → industrie et
industrie → ville). Réglage `road_mode`, défaut 1. Tout le détail — les trois familles de
candidats, les trois décisions d'allocation, les **quatre bugs** que la mise en service a révélés,
et la mesure — est dans **`docs/opexai_route.md`**.

⚠️ **Deux correctifs embarqués ne sont PAS du mode route** et ne doivent pas lui être attribués au
banc : le **renouvellement automatique** des véhicules, et la **détection de ligne morte** qui
exigeait à tort `ratingA <= 0` (une gare conserve sa dernière note quand plus rien n'y passe — une
ligne a roulé onze ans à perte sans être ferraillée). Les deux touchent aussi le rail.

**Ce qui reste, par impact estimé** (détail et justification dans `docs/opexai_route.md` §7) :

0. ✅ **La graine qui coulait ne coule plus** (2026-08-29, nuit). Sur `docs/bench_v2_road.json`
   (pré-traction), 8675309 était la **seule** insolvabilité : 1 460 136 → **1**, divergence 1974-75,
   cash collé à `CASH_RESERVE` de 1984 à 1989. Sur l'arbre courant (`docs/bench_road_8675309.json`,
   même graine, 20 ans, `OpexAI` contre `OpexAI[road_mode=0]`) :

   | | route ON | route OFF |
   |---|---:|---:|
   | `company_value` | **2 368 267** | 2 282 217 |
   | `performance_history` | 429 | 446 |
   | emprunt | 0 | 0 |
   | `months_of_bankruptcy` | 0 | 0 |

   Les deux bras sont **identiques au 1er janvier 1971**, puis divergent par opcodes, et
   **composent tous les deux**. Aucune insolvabilité dans les bancs post-traction (join, sitable,
   traction, basin_share). Campagne `docs/opex_reborrow_20y_4seeds.json` : 0 ligne routière, 0
   tentative — des candidats sont classés (2 à 4/an en 1970-75) mais le `break` cash les coupe,
   et après le remboursement de 1976 le plancher `ROAD_MIN_PROFIT_ANNUAL` prend le relais.
   L'hypothèse « la route mange le cash du prochain rail » décrivait le `break` d'avant traction
   sur le classement rail ; le `continue` borné a fermé le trou. **Pas de garde-fou à écrire.**

1. **Le plancher `ROAD_MIN_PROFIT_ANNUAL` coupe des lignes pax qui rapportent dix fois la
   prédiction.** La seule ligne pax bâtie était prédite à 1 031 et a rendu 7 000 à 11 700 par an.
   Cause probable : `TOWN_CATCHMENT_SHARE_PCT = 22` est calibré sur des **gares rail**. Se mesure
   exactement comme le premier calibrage (`sweeps/opex_predict_vs_actual.py`). C'est n = 1 : à
   mesurer, pas à recalibrer sur ce seul cas.
2. **`SITEA`/`SITEB` dominent les échecs de plan** (36 sur 40) : aucun site d'arrêt valide autour de
   l'extrémité. Le rayon n'est pas le levier ; les suspects sont l'exigence de platitude de la
   façade et `ROAD_MAX_SITE_PROBES`.
3. **Un seul classement pour tous les modes.** `ROAD_PLAN_ITERATIONS_BASE` est non calibré et ne
   sert qu'à ordonner les candidats routiers entre eux. Le panneau `RB` mesure désormais le coût
   réel de chaque tentative — la calibration qui rendrait la comparaison inter-modes possible est
   donc à portée, et c'est ce que la philosophie du projet demande.
4. **Multistop** (`AIStation.STATION_JOIN_ADJACENT`) : seul levier de volume par ligne, le plafond
   de deux véhicules par arrêt étant une règle du jeu.
5. **Une ligne routière peut perdre toute sa flotte et rester debout.** Observé une fois (graine 42,
   20 ans) : une ligne bus passe de 2 à 1 puis 0 véhicule en deux ans, notes de gare s'effondrant de
   54 à −1, et elle ne se reconstitue jamais — alors que son infrastructure est payée et que la
   ligne rendait 9 000/an. Le renouvellement automatique n'a pas repris la main. **Cause non
   établie, n = 1** ; le suspect nommé par `docs/mecanique_jeu.md` §11 est le **passage à niveau**
   (un train est le seul objet qui détruise un véhicule routier), et nos tracés routiers croisent
   nos propres voies. Le correctif qui couvre toutes les causes est le même : détecter une ligne à
   zéro véhicule et rebâtir sa flotte, l'infrastructure étant déjà là.

---

## 2. Le prochain morceau de code

**✅ Étage 3 fait** (`ai/OpexAI/builder_rail.nut`, 2026-08-28) : 3 lignes sur 3 construites en
10 ans, 56 véhicules. Comptabilité d'opcodes branchée, rollback sur échec, réserve de trésorerie.

**Tout l'ancien blocage capital est résolu (session du 2026-08-28)** : pax (`b09f23e`), fret
(`abd641b`), `MIN_SEPARATION`/`ORIGIN_SEPARATION` (`5433518`), remboursement d'emprunt (`44e0b14`),
détection et vente des lignes fret mortes (`e884358`), exclusion d'origine + plancher de ratio
(`candidates.nut`, ce jour). Graine 42/20 ans : 3 lignes bloquées → **17 lignes**, `company_value`
1 → **2 716 098**, emprunt à **0**. Détail dans [[opexai_squelette]] et
`docs/opexai_croissance.md` §6.

**Ce qui reste, par ordre d'impact mesuré :**

1. ✅ **Écart prédit/réel du fret : retiré, c'était une fausse alerte (2026-08-28).** L'affirmation
   « ~4-6x » n'était appuyée par aucune donnée citée dans `docs/opexai_croissance.md`. En creusant :
   la mesure existait déjà, commise dans `abd641b` en même temps que le correctif du puits fret
   (`docs/opex_predict_vs_actual_postfix_freight_v2.json`), simplement jamais recroisée avec
   l'affirmation écrite ensuite. Sur les 5 lignes fret à ≥3 ans de données stables : ratio
   prédit/réel moyen **0,98** (0,79-1,30) — `STATION_RATING_PCT = 50` calibré sur le pax tient
   aussi pour le fret, sans facteur correctif propre. Les 2 ratios à 1,8-2,4x observés sont des
   lignes à 1 an de données (ligne neuve ou industrie en fin de vie), pas un biais de modèle.
   Détail dans `docs/opexai_croissance.md` §2 et §8.
2. **Ne pas enfermer la ville dans nos propres voies** — reporté faute de mesure : vérifier
   d'abord si la croissance des villes desservies stagne réellement (`docs/mecanique_jeu.md` §5).
3. ✅ **Origines épuisées dans la fenêtre `TOP_K` : résolu (2026-08-28), en deux temps.** Exclusion
   des origines déjà servies à la génération (`OpexOriginServed` dans `candidates.nut`) plutôt
   qu'au filtrage — mais **seule, cette exclusion dégradait le résultat** (`company_value`
   2 067 089 contre 2 413 587 avant, emprunt non remboursé) : une fois les bonnes origines
   épuisées, l'IA s'engageait sur des candidats marginaux qu'un `TOP_K` engorgé bloquait
   *accidentellement* avant. Ajout d'un plancher `MIN_RATIO = 500` (profit/1000 itérations) qui
   corrige : **17 lignes** (contre 15), `company_value` **2 716 098** (+12,5 % vs avant tout
   correctif), emprunt remboursé. Détail dans `docs/opexai_croissance.md` §6, y compris le
   rattrapage du cycle annuel qui remplace la fausse piste du plafond `AISign`.

4. ✅ **RÉSOLU le 2026-08-29 : `LOAN_REPAY_FLOOR` abaissé de 1 000 000 à 300 000 après banc
   apparié — voir le verdict en fin d'item.** L'emprunt n'était pas remboursé sur 3 graines / 20 — mode d'échec découvert le 2026-08-29
   par le banc multi-graines, invisible sur la graine 42.** Les graines 100 et 4096 finissent
   20 ans au plafond de **300 000** d'emprunt, la graine 8675309 à 90 000 — et ce sont exactement
   les trois pires parties de la campagne (`company_value` 719 619 / 933 323 / 1 372 258, notes
   **194-206** contre ~430 ailleurs). Ce n'est pas une nuance mais un régime d'échec qualitatif.
   Le remboursement avait été déclaré corrigé par `44e0b14` sur la seule graine 42, où il tombe
   bien à zéro : c'est précisément le biais que le banc mono-graine masquait.

   🔴 **Reformulé le 2026-08-29 par le re-baselinage (§8), et c'est plus grave que décrit
   ci-dessus.** En rejouant les mêmes 20 graines sur un arbre dont **aucune décision ne change**
   (seul le profil d'opcodes bouge), l'échec passe de **3 graines à 6**, et surtout **la liste
   change presque entièrement** :

   | | graines à emprunt non remboursé à 20 ans |
   |---|---|
   | avant | 100 (300 k), 4096 (300 k), 8675309 (90 k) |
   | après | 1 (300 k), 100 (80 k), 1024 (300 k), 65537 (180 k), 123456 (300 k), 8675309 (300 k) |

   La graine 4096 s'en échappe complètement (300 k → 0) pendant que quatre autres y tombent. **Ce
   n'est donc pas une propriété de la carte mais une instabilité latente de la trajectoire** : il
   n'y a pas « trois mauvaises graines » à diagnostiquer, il y a un régime dans lequel *n'importe
   quelle* partie peut basculer, et qui touche 15 à 30 % d'entre elles. Toute analyse qui part des
   graines nommément (« qu'y a-t-il de particulier sur 100 et 4096 ? ») est donc une impasse : la
   cause est dans la règle, pas dans la carte. `LOAN_REPAY_FLOOR = 1 000 000` reste le suspect —
   une compagnie qui ne franchit jamais le seuil ne rembourse jamais — mais il faut le tester comme
   une règle, pas expliquer trois cas.

   Ce résultat pèse aussi sur le §5 : les graines en échec portent une grande part de la
   dispersion (moyenne 1 248 532 contre 2 907 102 pour les saines), donc **corriger l'emprunt
   resserrerait le banc lui-même** et abaisserait le plancher de détection de tout ce qui vient
   après. Données dans `docs/bench_v2.json`.

   ### Diagnostic (`docs/opexai_emprunt.json`, 6 graines × 20 ans, panneaux `LB`/`LF`)

   ❌ **Une hypothèse réfutée d'abord.** `_tryRepayLoan` est appelé à `main.nut:828`, juste après
   `_tryBuild`, donc au creux annuel de trésorerie — on pouvait croire que la construction lui
   volait son argent. **Faux** : `blocked_by_floor_only = 0` sur les six graines, pas une seule
   année où le sommet passait le plancher mais pas le creux. L'ordre n'est pas en cause.

   ✅ **La cause est le seuil, seul.** La trésorerie d'OpexAI reste entre 50 000 et 400 000 pendant
   **dix à quatorze ans** : le million n'est atteignable à aucun moment de la phase de croissance.
   La règle, elle, est saine — dès que la trésorerie franchit le seuil, le remboursement part
   immédiatement et solde tout (graine 65537 : 1 751 216 en 1981 → zéro). Deux illustrations : la
   graine 123456 est restée entre 954 017 et 956 875 **cinq années consécutives**, 4,5 % sous le
   seuil (et ces cinq années sont des années *franchies*, ce qui la relie à l'item 6) ; la graine
   100 a passé vingt ans à 300 000 d'emprunt sans jamais dépasser 774 797 à un contrôle annuel.

   **Pourquoi 300 000**, sur deux mesures indépendantes : le plus gros candidat jamais bloqué faute
   de trésorerie coûte **248 106** (médiane 136 760), et la construction annuelle draine 95 172 en
   médiane, 183 101 au 90e centile. La courbe de déblocage est **plate entre 300 et 500** (même
   année sur 4 graines / 6) et descendre à 200 passerait sous le prix de la plus grosse ligne :
   300 est le genou.

   ### Verdict du banc apparié (`docs/bench_v2_emprunt.json`, 20 graines × 20 ans)

   | | plancher 1 M | plancher 300 k |
   |---|---:|---:|
   | graines à emprunt résiduel | 3 / 20 | **1 / 20** |
   | emprunt total résiduel | 900 000 | **230 000** |
   | `company_value` appariée | — | −0,17 %, t = −0,12 |
   | `performance_history` appariée | — | +1,91 %, t = +1,18 |

   Les graines 100 et 4096 passent de 300 000 à zéro et leur **note** bondit (170 → 245, 269 → 309)
   pendant que leur valeur d'entreprise ne bouge quasiment pas — exactement le comportement prévu,
   rembourser avec du cash étant neutre en valeur et ne gagnant que l'intérêt plus la composante
   « emprunt à zéro ». Les deux métriques globales restent sous le plancher de détection (~15 % et
   ~12 %) : **c'était prévu**, d'où la lecture sur `current_loan`.

   🔶 **Preuve que le changement est chirurgical** : sur 4 graines (17, 999, 2026, 8675309) les deux
   bras sont **bit à bit identiques**. Là où la trésorerie franchissait le million d'un coup,
   abaisser le plancher ne change littéralement rien — le correctif ne touche que les parties qu'il
   vise.

   ⚠️ **Reste 1 graine (42) à 230 000 SUR CE BANC.** Sur l'arbre courant elle solde tout en 1975
   (`docs/opex_reborrow_20y_42.json`). Descendre le plancher sous 300 passerait sous le coût de
   la plus grosse ligne ; l'item 8 (réemprunt) ne paie pas : le trou est vide.

8. ✅ **Réemprunt à la demande : écrit, mesuré, défaut 0 — le trou est vide** (2026-08-29, nuit).
   `OpexTryReborrow` tire le palier manquant aux quatre portes de cash, derrière `reborrow`.
   5 graines × 20 ans (`docs/opex_reborrow_20y_42.json`, `docs/opex_reborrow_20y_4seeds.json`) :
   **412 `GC`, 0 tirage `GL`, 0 `GC` avec de l'emprunt encore disponible.** Tous les blocages
   cash sont des années où l'emprunt est déjà au plafond 300 000. Dès que le remboursement
   commence, plus aucun `GC`. Le mur n'est pas l'absence de réemprunt, c'est le plafond
   d'emprunt lui-même (mur n° 1). Pas de banc apparié n=20 : ce serait mesurer un mécanisme
   inerte. Le code reste ; `OpexAI[reborrow=1]` rallume. La graine 42 à 230 000 d'emprunt
   résiduel du banc `loan_repay_floor` est **périmée** sur cet arbre : elle solde tout en 1975.

5. ⚪ **Régler `MIN_SEPARATION` : piste ÉCARTÉE le 2026-08-29, alors même que la mesure la
   désigne comme le verrou.** L'investigation de plafonnement (`docs/opexai_plafonnement.md`) a
   établi que le vivier ne meurt pas au classement mais à `_tooClose` : sur la graine 999, arrêtée
   en 1981, **les 19 candidats de 1989 sont tous rejetés — 1 par réutilisation d'origine et 18 par
   le filet physique seul**. La carte n'est pourtant pas épuisée (37 à 39 villes non desservies sur
   39 à 45). `MIN_RATIO` n'écarte que 2,7 % des paires et `TOP_K` n'en écarte aucune : les deux
   suspects initiaux sont faux.

   **Pourquoi on ne règle pas le seuil pour autant.** `MIN_SEPARATION` ne garde pas contre une
   collision de voies mais contre la **cannibalisation de bassin** (`main.nut:50`) : deux gares trop
   proches partagent leur zone de captation. L'agrandissement de gare et les jonctions (§9) ne
   suppriment pas ce recouvrement — il reste physiquement là — mais ils changent **l'action
   disponible face à lui**. Aujourd'hui « trop proche » n'a qu'une sortie possible : renoncer. Avec
   le raccordement, la même détection devient un aiguillage — se brancher sur la gare existante
   plutôt que d'en poser une seconde. Le test survit, sa branche de sortie change : `return null`
   devient `join`.

   Calibrer le seuil maintenant serait donc régler une constante dont la sémantique va changer :
   travail perdu, et pire, un seuil relâché à l'avance **masquerait** le gain de l'agrandissement en
   ayant déjà ouvert le vivier par un autre moyen. Ne pas passer de banc apparié `MIN_SEPARATION`
   avant que §9 ne soit tranché.

6. ✅ **IMPLÉMENTÉE le 2026-08-29, non commitée. Banc appairé 3 bras × 20 graines : NON CONCLUANT, voir le verdict en fin d'item.**
   **La politique d'abandon coûtait plus que tout le reste de la construction.** Mesure du
   2026-08-29 sur 4 graines : 52 lignes bâties en 57 tentatives, mais les **5 abandons absorbent
   56,5 % des opcodes de construction** — 182 M chacun contre 13,5 M pour une réussite, soit
   **13,5×**, tous au plafond dur de 60 000 itérations. Ceci ne contredit pas le §7 (la forme
   fermée du rendement marginal est bien en place) : c'est le **plafond dur** qui mord, pas la règle
   d'arrêt anticipé. À traiter avec l'item 4 — les deux sont indépendants de l'architecture de §9,
   donc ni l'un ni l'autre ne sera invalidé par l'agrandissement de gare.

   **Correctif livré**, en deux réglages indépendants pour que le banc attribue le gain à chacun :
   `pathfinder_hard_cap_k` (défaut **40**, `60` = bras de contrôle) remplace le `const
   HARD_ITERATION_CAP` de `builder_rail.nut` ; `abandon_memory` (défaut **1**) mémorise les paires
   qui ont rendu `ABND` pour ne pas repayer le plafond deux fois. Le second domine le premier :
   **3 des 5 abandons mesurés étaient le même échec rejoué** (graine 4096, 1978 puis 1981/1983/1986,
   rang 0 sur `ranked_len` 1), donc la mémoire enlève 60 % des abandons **sans perdre une ligne**,
   là où aucun réglage du plafond n'y arrive.

   **Le plafond à 40 000 vient de la mesure** : sur les 52 réussites, la plus longue a coûté 36 600
   itérations et seules 3 dépassent 20 000 (134-168 tuiles, profits prédits 23,8k / 46k / 54k). À
   40 000 on ne perd aucune réussite in-sample et on coupe ~20 % des itérations ; à 20 000 on
   économise 48 % mais on perd ces 3 lignes.

   🔴 **Piste ÉCARTÉE — et attention, la première raison publiée était FAUSSE.** Un plafond relatif
   à la distance (`α × OpexRailIterations(distance)`) est écarté **parce que la dispersion du modèle
   est trop grande**, pas parce qu'il ne mordrait pas. `KNOT_DISTANCE` vaut `[23, 33, 48, 63, 81,
   105, 150]`, PAS `[10..70]` — lire `KNOT_ITERATIONS` sans lire `KNOT_DISTANCE` juste à côté fait
   surestimer le modèle d'un facteur 5 à 10 et mène à la conclusion inverse. Chiffres corrects sur
   les 52 réussites : ratio réel/modèle **médian 0,41**, étalé de **0,016 à 3,40** (facteur 200). Le
   modèle prédit un coût moyen amorti, pas la queue d'une tentative isolée : à `α = 2` on perd
   encore 4 réussites, contre **0 pour le plafond plat à 40 000**.

   ⚠️ **Interaction non anticipée entre les deux réglages, à surveiller au banc.** Le plafond
   abaissé **crée** des abandons chez les paires qui aboutissaient entre 40 000 et 60 000
   itérations, et la mémoire rend chacun de ces abandons **définitif** : une paire qui réussissait à
   45 000 est désormais bannie pour la partie. Si le bras `station_join=0` ressort sous le bras de
   contrôle, c'est la première suspecte — la réponse serait de ne mémoriser que les abandons
   atteints à l'ancien plafond, ou de n'interdire qu'une seule re-tentative au lieu de toutes.

   **Validation graine 4096 / 20 ans** (une graine, donc aucune conclusion de valeur) : abandons
   **4 → 1**, itérations gaspillées **240 000 → 40 000**, années franchies **7 → 0**, 7 candidats
   écartés par la mémoire. La cadence annuelle est entièrement récupérée, ce qui était l'objet.

   **Verdict du banc (`docs/bench_v2_join.json`, 3 bras × 20 graines × 20 ans, ~25 min) : AUCUN
   EFFET DÉCELABLE, dans aucune comparaison.** Bras A = contrôle `[60,0,0]`, B = `[40,1,0]`,
   C = défauts `[40,1,1]`.

   | comparaison | `company_value` | `performance_history` |
   |---|---|---|
   | A − B (plafond + mémoire) | +2,06 % · t=+0,31 · 10/20 | +3,62 % · t=+0,80 · 12/20 |
   | B − C (raccordement) | −2,94 % · t=−0,47 · 11/20 | −1,79 % · t=−0,39 · 12/20 |
   | A − C (les deux) | −0,94 % · t=−0,16 · 10/20 | +1,77 % · t=+0,49 · 12/20 |

   **C'était le résultat attendu**, pas une infirmation : le plancher de détection est de ~15 % sur
   `company_value` et ~12 % sur `performance_history` (§8), et les effets observés valent 0,2 à
   3,6 %. Le banc établit **l'absence de dégât mesurable**, et rien de plus. La justification du
   correctif repose donc entièrement sur les métriques directes ci-dessus, comme `current_loan`
   l'avait fait pour l'item 4.

   ⚠️ **Un point aberrant à ne pas surinterpréter, mais à ne pas oublier** : graine 100, bras B,
   `company_value = 1` avec 121 véhicules, 18 gares, emprunt au plafond de 300 000 et un revenu
   annuel de 14 207 contre 56 032 au contrôle — une compagnie qui a beaucoup bâti et rien gagné,
   pas une compagnie inerte. Elle porte à elle seule le CV du bras B (42 % contre 26 % pour A). Le
   bras C, qui a pourtant le même plafond ET la même mémoire, s'en sort à 919 065 : ce n'est donc
   pas un effet systématique des deux réglages mais, très probablement, la divergence de
   trajectoire déjà documentée. **Retirer cette graine ne change pas la conclusion** — tous les
   |t| tombent alors sous 0,54.

7. 🔵 **Le biais de sélection du modèle de profit** (relevé le 2026-08-29, non mesuré). 45,2 % des
   4 216 paires sont rejetées pour « profit prédit ≤ 0 », mais le modèle qui rend ce verdict n'a été
   calibré que sur les lignes **qui ont passé le filtre** (`docs/opex_predict_vs_actual.json`,
   `..._postfix_freight_v2.json`). Si le modèle sous-estime systématiquement une famille de paires,
   elles sont rejetées et n'entrent jamais dans la calibration qui l'aurait révélé. On ne peut donc
   **pas** conclure que ces 1 905 paires sont réellement non rentables. Vérifiable à coût borné :
   forcer la construction d'un échantillon de paires rejetées et comparer prédit/réel sur elles.

9. 🔴 **Les suites de la tranche v1 du raccordement de gare** (commité, défaut `station_join=0`).
   Le quai parallèle joint au même `StationID` avec sa propre entrée est en place et contourne à
   la fois la question des jonctions et le blocage sur voie unique ; note de conception dans
   `docs/opexai_raccordement_gare.md`. Le banc vivier a dit non ; le banc post-traction aussi
   pour la valeur (§0.2), malgré un effet de construction toujours solide. Trois suites, dans
   cet ordre :

   1. 🔴 **Instrumenter le REFUS de jointure — le plus urgent.** `OpexFindStationJoin` rend `null`
      sans dire laquelle des trois conditions a tué le candidat : gare logique unique (plusieurs
      gares dans le disque), même `kind` et même cargo, ou même rôle fret (source avec source,
      puits avec puits). **Sur la graine 4096, `too_close_far` se déclenche 5 fois (1980, 1981,
      1983, 1984, 1985) pour 0 tentative de jointure** : le chemin est inerte et on ne sait pas
      pourquoi. Aucune décision sur §9 n'est informée tant que ce compteur n'existe pas. Et le banc
      ne peut pas y répondre — il ne lit que les sauvegardes, seul `sweeps/opex_full_campaign.py`
      décode `OB|J|`.
   2. **`JOINPATH` brûle l'A\* entier pour rien.** `OpexJoinPathIsDedicated` rejette *après coup*
      tout chemin dont une case intermédiaire touche un rail existant, mais le pathfinder n'est pas
      informé de la contrainte — il peut donc router à travers la voie voisine et se faire rejeter
      une fois la recherche entièrement payée. Et contrairement à `ABND`, `JOINPATH` n'entre pas
      dans la mémoire des paires : le candidat revient l'année suivante repayer la même recherche.
      Hypothèse, pas un fait mesuré : le compteur `OB|J|` et le code de raison `J` la trancheront
      dès la première campagne.
   3. ✅ **Le profit prédit d'une ligne jointe — `basin_share` mesuré, défaut 0.** La production
      de l'extrémité jointe est divisée par (n+1). Banc apparié 20 graines × 20 ans
      (`docs/bench_basin_share.json`, paire `docs/bench_basin_share_paired.json`), les deux
      bras à `station_join=1` :

      | métrique | delta | t | graines | verdict |
      |---|---|---|---|---|
      | `company_value` | +5,5 % | 0,89 | 11/20 | sous le plancher (~15 %) |
      | `performance_history` | +3,8 % | 1,11 | 11/20 | sous le plancher (~12 %) |
      | véhicules | +0,2 % | 0,04 | 12/20 | **nul** — pas moins de trains |
      | gares | **+12,9 %** | **3,67** | **15/20** | les jointures sont déclassées |

      Ce n'est pas « moins de trains sur un bassin partagé ». C'est un **autre classement** :
      les candidats à jointure reculent, l'IA repose des gares neuves, les véhicules du bras
      join restent. Graine 42 : tentatives 228 → 40, véhicules 221 → 238. ⚠️ **Défaut 0.**
      Le spread n'est **pas** débloqué : joindre plus, sur un terme qui ne paie pas, recréerait
      le banc vivier.

**Priorité de fait, révisée le 2026-08-29 (nuit)** : `station_join`, `basin_share`, `reborrow`
et le mode route **item 0** sont ✅ mesurés. Les trois premiers ne paient pas (défauts 0) ; la
graine qui coulait ne coule plus (pas de garde-fou). Le **spread** n'est pas la suite. 9.1 et
9.2 n'informent qu'un réglage éteint. La tête passe au mode route **item 5** — une ligne
routière à zéro véhicule qui ne se reconstitue jamais (n = 1, cause non établie, l'infrastructure
est déjà payée). `origin_sitable`, `station_join`, `basin_share` et `reborrow` restent à 0.

*Priorité précédente, conservée pour la trace* : ~~l'item **4**~~ (✅ fait) et l'item **6**
(plafond d'abandon) passaient devant — ce sont deux échecs mesurés, et surtout les deux seuls
qui soient **orthogonaux à l'architecture de §9** : leur gain survivra à l'arrivée de
l'agrandissement de gare et des jonctions. L'item 5 (`MIN_SEPARATION`) est explicitement gelé
derrière §9. L'item 7 (biais de sélection) est une mesure, pas un changement de code, et peut
s'intercaler. L'item 2 (verrouillage de ville) reste dernier — il exige lui aussi d'abord une
mesure (la croissance des villes desservies stagne-t-elle réellement ?).

---

## 3. Calibrations en attente

- ✅ **Le modèle économique, volet PASSAGERS** (`economy.nut`/`candidates.nut`) : mesuré et corrigé
  le 2026-08-28 sur 9 lignes pax réelles (2 campagnes de 10 ans, graine 42, 15.3) — voir
  `docs/opex_predict_vs_actual.json` et `sweeps/opex_predict_vs_actual.py`. Le gap ~10x se
  décompose en `STATION_RATING_PCT` trop optimiste (75 supposé contre ~53 mesuré, facteur ~1,4x
  seulement) ET, dominant, `AITown.GetLastMonthProduction` compté sur la ville ENTIÈRE alors
  qu'une gare n'en capte qu'un rayon local (facteur ~4,5x résiduel, mesuré 8-37 % selon la ligne).
  Corrigé par `STATION_RATING_PCT = 50` et un nouveau `TOWN_CATCHMENT_SHARE_PCT = 22` appliqué
  uniquement aux paires de villes dans `OpexPaxCandidates`. Vérification in-sample sur les 9
  lignes : ratio prédit/réel resserré de 3,75-17,3x à 0,55-2,54x (moyenne ~1,18x contre ~8x avant).
- ✅ **Note de gare fret à -1 : résolu, DEUX causes distinctes démêlées.**
  1. **Train coincé** (`abd641b`, 2026-08-28) : `OF_FULL_LOAD_ANY` aux deux arrêts bloquait le
     convoi au puits fret (structurellement à sens unique) sur une gare à une voie. Corrigé par
     `OF_NONE` au puits.
  2. **Fermeture d'industrie source** (`e884358`, 2026-08-28) : confirmée réelle sur certaines
     lignes (via `AIIndustry.IsValidIndustry`, pas déduite), mais PAS systématique — une gare peut
     rester rentable via une industrie voisine du même cargo (`srcAlive=0` n'implique pas la mort).
     Détection sur performance réelle (note + revenu, 2 ans consécutifs) puis vente des convois une
     fois le seuil confirmé.
- ✅ **Le modèle économique, volet FRET** : le « reste ouvert ~4-6x » précédemment noté ici est
  **retiré (2026-08-28)**, faute de fondement — `docs/opex_predict_vs_actual_postfix_freight_v2.json`
  (commis dans `abd641b`, jamais recroisé avec l'affirmation avant cette relecture) donne un ratio
  prédit/réel moyen de **0,98** sur les 5 lignes fret à ≥3 ans de données stables.
  `STATION_RATING_PCT = 50` (calibré sur le pax) tient donc aussi pour le fret, sans facteur
  correctif propre à identifier. Détail dans `docs/opexai_croissance.md` §2 et §8.
- 🔴 **Le modèle de coût A\*** (`candidates.nut`, table de nœuds) : ajusté sous OpenTTD 13.4 avec
  le pathfinder de `TrainLineAI`. La forme se transporte, les coefficients doivent être réajustés
  sur `OpexAI` sous 15.3. **Chiffré le 2026-08-29 sur les 52 lignes rail de la campagne 4 graines,
  et le désaccord porte sur la FORME, pas seulement sur l'échelle** :

  | bande de distance | n | ratio réel/modèle (médian) | profit réel par 1000 itérations |
  |---|---:|---:|---:|
  | ≤ 35 tuiles | 13 | 0,49 | **17 693** |
  | 35-50 | 17 | 0,42 | 5 003 |
  | 50-70 | 10 | 0,31 | 5 958 |
  | 70-105 | 7 | 0,41 | 4 225 |
  | 105-200 | 5 | 0,79 | 1 257 |

  **L'optimum mesuré est au plus court**, d'un facteur 3, alors que le commentaire de
  `candidates.nut` code un optimum à 48-63 tuiles hérité de la campagne 13.4 — c'est ce commentaire
  qui justifie « le classement par rapport choisit donc des lignes MOYENNES ».

  ⚠️ **Deux pièges avant de refaire l'ajustement :**
  1. **Biais de censure.** La grandeur du modèle est « itérations par ligne RÉUSSIE » =
     itérations_moyennes / P(construite). Or **les tentatives abandonnées n'enregistrent pas leur
     distance** : `rail_attempts` ne porte que `iterations`, et seul le tableau `lines` (donc les
     réussites) a `distance`. P(construite | distance) est donc incalculable sur les données
     actuelles, et un ajustement sur les seules réussites reproduirait exactement le biais du §2.7.
     **Instrumenter la distance sur CHAQUE tentative est un préalable**, pas une option.
  2. **`ATTEMPT_MULTIPLIER = 4` a été calibré contre le modèle actuel.** Le budget vaut
     `4 × profit × 1000 / ratio_alternatif` ; diviser le modèle par ~2,4 multiplie tous les ratios
     d'autant et divise donc tous les budgets d'autant. Sans re-dérivation conjointe du
     multiplicateur, on reproduit l'échec mesuré du 2026-08-28 : « 60 tentatives sur 5 ans, budgets
     de 50 à 400 itérations, zéro ligne construite ».
- ✅ **Constantes HYPOTHÈSE `SPEED_EFFICIENCY_PCT = 70` et `WAGONS_PER_TRAIN = 5`** : remplacées
  le 2026-08-29 par la traction dimensionnée (`4a8e15e`). `ROAD_SPEED_EFFICIENCY_PCT = 60` reste
  une hypothèse du mode route (`docs/opexai_route.md`).

---

## 4. Mesures à faire dans le jeu plutôt qu'à citer

Reprend le §8 de `docs/mecanique_jeu.md`, complété.

1. ✅ Le réglage `plane_speed` réellement actif : `4`, le défaut, non surchargé — vérifié dans
   l'`openttdlab.cfg` d'un run `OpexAI` réel du 2026-08-28, pas supposé.
2. ✅ Économie « lisse » (`economy.type = 1` = `ET_SMOOTH`) confirmée dans notre config gelée, le
   défaut, non surchargé — vérifié dans l'`openttdlab.cfg` du 2026-08-28. À distinguer de
   `difficulty.economy` (recessions, réglage différent malgré le nom). Les probabilités de
   changement de production restent à recalibrer sur ce régime précis.
3. Le **rendement de vitesse effectif** d'un train (vitesse réelle / vitesse catalogue), sachant
   que le bridage en courbe descend à 61 km/h sur un virage à 90°.
4. ✅🔶 La **courbe de montée de la note d'une gare neuve**, dérivée de la source 13.4
   (`UpdateStationRating` dans `station_cmd.cpp`) — départ à `175/255` (pas 0), mise à jour tous
   les 2,5 jours (`185/74` ticks), pas de ±2 points vers la cible calculée une fois le premier
   ramassage enregistré ; ~2 mois pour résorber un écart de 50 points. Détail dans
   `docs/mecanique_jeu.md` §8.4. **Pas encore confirmé inchangé en 15.3** — lu sur la seule source
   locale disponible (13.4).
5. Le **barème croissance de ville / nombre de gares actives** : absent du wiki, présent dans le
   source (`town_cmd.cpp`, `UpdateTownGrowRate`) — à mesurer, pas à recopier de mémoire.
6. **Sonde de catalogue de 1950 à 2000** (`ai/CatalogProbe/`, changer `starting_year` et la durée) :
   les chiffres actuels ne couvrent que 1970-1989 et ratent l'électrification, l'aéroport
   INTERNATIONAL (1990) et le début du parc.

---

## 5. Banc

- ✅ **Banc multi-graines construit et exécuté (2026-08-29)** — `sweeps/bench_v2.py`,
  résultats dans `docs/bench_v2.json` : 20 graines × 20 ans, OpexAI et AAAHogEx (campagne
  interrompue volontairement avant AdmiralAI et trAIns, jugées obsolètes). Le script apporte la
  notion d'**arm** (une IA OU une variante paramétrée d'OpexAI via `ai_params`, ex.
  `OpexAI[pathfinder_sleep_ticks=1]`), le nettoyage des sauvegardes, un checkpoint `.jsonl`, les
  stats de dispersion et les **comparaisons appariées par graine**. Les deux items ci-dessous
  (20 ans, 20 graines) sont absorbés par lui.

  | arm | company_value | CV | SE | note | CV |
  |---|---:|---:|---:|---:|---:|
  | OpexAI *(re-baseliné le 2026-08-29)* | 2 409 531 | 48,8 % | 10,9 % | 396 | 27,6 % |
  | OpexAI *(mesure d'origine, archivée)* | 2 527 171 | 32,6 % | 7,30 % | 408 | 20,4 % |
  | AAAHogEx | 225 430 986 | 16,2 % | 3,62 % | 897 | 0,5 % |

  ⚠️ Les deux lignes OpexAI mesurent le **même comportement** sur les **mêmes graines** : seul le
  profil d'opcodes diffère (§8). L'écart entre elles n'est pas significatif en lecture appariée
  (t = −0,60) — mais il chiffre le **bruit de trajectoire irréductible**, et c'est lui qui fixe le
  plancher de détection du banc : **~15 % sur `company_value`, ~12 % sur `performance_history`**.

  **Quatre acquis, dont trois corrigent ce qui était écrit ici :**
  1. ❌ **Le n=20 ne donne PAS 5,9 %.** Cette projection supposait un CV de 26 % ; le CV mesuré
     d'OpexAI était **32,6 %** (48,8 % après re-baselinage), donc 7,30 % à 10,9 % d'erreur-type.
     La différence de deux moyennes indépendantes porte ~10,3 % à ~13,1 % de SE : il faudrait un
     effet de **~21 % à ~26 %** pour trancher à 2σ.
     **La lecture appariée n'est donc pas un raffinement mais le seul chemin praticable.**
     🔶 **Précisé le 2026-08-29 par le re-baselinage** : l'appariement marche, mais ne divise la SE
     que par ~1,7 (13,1 % → 7,70 %). Il ne rend pas le banc sensible, il le rend *praticable* — le
     plus petit effet décelable reste ~15 % sur `company_value`, ~12 % sur `performance_history`.
     Un correctif qui gagne 8 % restera invisible à n=20.
  2. **Deux métriques, deux usages.** `performance_history` est **saturée chez AAAHogEx**
     (897, CV 0,5 %) : inutilisable pour se comparer à lui, où seule `company_value` parle. Mais
     elle est **moins bruitée que `company_value` chez nous** (20,4 % contre 32,6 %) : c'est la
     bonne métrique pour opposer deux variantes d'OpexAI entre elles.
  3. ❌ **Porter le banc à 20 ans nous dessert**, contrairement à l'argument ci-dessous. L'écart
     avec AAAHogEx passe de ~19× à 10 ans (banc v1) à **88× à 20 ans**. L'allongement ne révèle pas
     notre multimodalité, il révèle notre plafonnement pendant qu'il compose. On garde 20 ans (la
     mesure est plus honnête), mais sans en attendre un avantage.
  4. **La graine 42 est 14e sur 20** (2 336 785 pour une médiane de 2 740 070) ; l'écart
     meilleure/pire graine est de **5,5×**. Toutes les décisions antérieures ont été prises sur une
     graine sous la médiane.

  ⚪ **`pathfinder_sleep_ticks` ne sera PAS mesuré au banc — décision arrêtée le 2026-08-29, ne pas
  rouvrir.** Le défaut reste 0. Le banc sait pourtant l'opposer (`OpexAI[pathfinder_sleep_ticks=1]`),
  mais le Sleep est **strictement dominé** : le moteur suspend déjà le script dès qu'il épuise son
  budget d'opcodes du tick, donc `Sleep(n)` n'achète aucun opcode supplémentaire plus tard — il
  fait seulement qu'OpexAI ne fait rien pendant n ticks pendant qu'un adversaire continue. Il n'y a
  aucun mécanisme par lequel il puisse aider ; le 13-contre-13 de la graine 42 était du bruit de
  trajectoire. Raisonnement écrit à côté du réglage dans `ai/OpexAI/info.nut`.

- ⚪ *(absorbé par le banc v2)* **Porter le banc de 10 à 20 ans.** Toute l'évolution multimodale
  arrive après 1980 : aéroport METROPOLITAN (1980), COMMUTER (1983), parc routier +83 %, parc
  avion +38 %. Un banc à 10 ans mesure une partie où le rail est presque le seul mode qui
  progresse. ⚠️ Argument **retourné par la mesure**, voir le point 3 ci-dessus.
- ⚪ *(absorbé par le banc v2)* **Augmenter le nombre de graines, pas les répétitions.**
  Bruit intra-graine 4,1 % contre dispersion inter-graines de 26 %. Erreur-type de la moyenne à
  n=5 : 11,8 % ; à n=20 : 5,9 % — ⚠️ **chiffre réfuté**, la vraie SE à n=20 est 7,30 %.

  **Pourquoi c'est désormais un préalable et plus une amélioration.** Trois changements *sans aucun
  effet décisionnel* ont produit le même jour des écarts pluri-lignes sur la graine 42 :
  1. la liaison route, qui coûte 0,04 % des opcodes de la campagne (§6.4) ;
  2. le franchissement d'une année de calendrier (`docs/opexai_croissance.md` §6) ;
  3. le simple fait d'interposer un appel de fonction (`OpexSign`) devant les 57 panneaux —
     **3 lignes rail perdues, 16 → 13**, alors qu'aucune décision de l'IA ne change.

  Toute perturbation du rythme d'opcodes déplace les frontières de ticks, donc *quand* les choses
  arrivent, et la trajectoire entière diverge. **Une graine unique ne distingue donc pas un vrai
  gain d'un déplacement de trajectoire**, y compris pour des écarts de 16 %. Conséquence pratique :
  tant que le banc multi-graines n'existe pas, aucune décision de conception ne peut être tranchée
  par la campagne graine 42 seule — ni le défaut de `pathfinder_sleep_ticks`, ni la réactivation du
  mode route, ni le coût réel du mode route pour le rail (§6.4).
  ⚠️ Corollaire de méthode : « reproduit deux fois à l'identique » ne prouve rien ici — la
  plateforme est déterministe, donc même graine ⇒ même résultat.
- Le **face à face** dans une partie partagée, aux jalons seulement (décidé le 2026-08-28).
- ✅ **Hypothèse d'un plafond `AISign` réfutée (2026-08-28).** Ni la tuile `(1,1)` ni le nombre
  de signs de la campagne ne sont en cause : `CmdPlaceSign` ne peut échouer ici que par nom de
  32 caractères ou plus, ou par pool global de 64 000 entrées, très au-dessus des ~2 000 signs.
  Le trou non monotone (1984 absent, 1985-1989 présents) vient du cycle annuel de `Start()` qui
  franchit une année pendant `_tryBuild` puis fixe directement `lastYear` à l'année courante.
  Ce n'était pas une perte d'observabilité : les tâches annuelles ne s'exécutaient pas (seul le
  `_tryBuild` déjà lancé pouvait continuer). Le rattrapage exécute désormais rapport des lignes,
  traitement des lignes mortes et remboursement pour chaque année franchie ; détail et mesure
  directe dans `docs/opexai_croissance.md` §6.
- Élucider le **non-déterminisme propre à AAAHogEx** (la plateforme, elle, est déterministe).
  🔶 Mécanisme confirmé par lecture de source (pas encore de test A/B, donc la causalité sur le
  non-déterminisme reste ouverte) :
  - `openttdlab.py:376-393` (mode `console-script`, celui utilisé en 15.3) programme un `save`
    console à chaque mois de jeu via des scripts `.scr` — ce n'est pas l'autosave du moteur
    (`autosave = off` dans notre `openttdlab.cfg`), mais un déclenchement externe mensuel.
  - Chaque `save` console appelle `Save()` d'AAAHogEx (`main.nut:4032-4105`), qui sérialise des
    caches volumineux (`landConnectedCache`, `cargoVtDistanceValues`, `estimateTable`, toutes les
    statics de route) ET s'auto-instrumente : un `AIController.GetOpsTillSuspend()` avant/après
    chaque sous-`Save()` plus un `HgLog.Info(...)` de concaténation de chaîne à chaque étape.
  - Donc l'hypothèse est confirmée **mécaniquement plausible** (travail réel et non trivial
    déclenché chaque mois, hors du chemin de décision normal de l'IA) mais pas encore **prouvée
    causale** : reste à faire tourner deux campagnes identiques avec/sans le `save` mensuel
    (ou avec logging désactivé) et comparer la dispersion.

---

## 6. Modes de transport, dans l'ordre décidé

1. ✅ **Rail** — étage 3 ci-dessus.
2. ✅ **Avion** — une liaison passagers entre deux grandes villes, validée sous OpenTTD 15.3.
   Aucun pathfinding ; son avantage n'est toutefois **pas** la vitesse : il vole au quart de sa
   vitesse affichée.
3. ✅ **Bateau** — une liaison passagers entre deux grandes villes côtières, avec validation
   bornée du graphe d'eau et dépôt construit sur la même composante. Voir
   `docs/opexai_multimodal.md`.
4. ✅🔶 **Route** — constructeur transactionnel (deux arrêts, dépôt, bus, rollback, garde
   anti-doublon) ajouté le 2026-08-28, mais **désactivé** après mesure. Le trace Manhattan borné
   évite `Pathfinder.Road` (171 356 opcodes contre 696 794 mesurés pour l'A* sur la sonde courte),
   et la liaison 27–33 (23 tuiles) construit bien pour 10 092. **Elle ne charge pourtant personne** :
   profit −588 puis −599/−601 par an, notes d'arrêt à **−1** — la signature d'un cargo jamais
   ramassé, exactement comme le bug fret d'`abd641b`. C'est LE symptôme à expliquer.
   ⚠️ **La campagne route active finit à 1 749 226 contre 2 787 970, mais cet écart n'est PAS
   attribuable à la liaison** (vérifié le 2026-08-28) : elle coûte 171 356 opcodes, soit **0,04 %**
   des 436 M de la campagne, et 10 092 d'argent — et le run avec route consomme au total *moins*
   d'opcodes (231 M contre 436 M), il construit moins, il n'est pas étranglé. C'est une divergence
   de trajectoire sur graine unique : deux arrêts de bus changent l'état du monde dès 1972 et tout
   diverge ensuite. On ne peut pas séparer « le bus nuit » de « cette trajectoire est moins bonne ».
   `ROAD_BUILD_ENABLED = false` conserve le code sans sacrifier le banc.
   La croissance (une unité / 50 jours / cinq gares) reste un effet de bord non mesuré et non
   poursuivi ici ; avant toute réactivation, expliquer le non-chargement et mesurer plusieurs
   paires avec une économie routière propre.
   **Suspects du non-chargement, par vraisemblance** (voir `docs/mecanique_jeu.md` §11) : (1) bus
   jamais démarré — un véhicule neuf naît `Stopped`, il faut `AIVehicle.StartStopVehicle` ;
   (2) arrêt mal orienté donc non raccordé à la route. Le type d'arrêt est **écarté** : le code
   passe bien `ROADVEHTYPE_BUS`. À vérifier aussi avant de dimensionner : **un arrêt n'accueille
   que 2 bus**, au-delà ils font la queue sur la route — `economy.nut` ignore ce plafond.

Ne pas oublier deux composantes gratuites de la note de compagnie : **emprunt à zéro** (5 %) et
**8 types de cargo par trimestre** (5 %) — cette dernière plaide contre une IA 100 % passagers.

---

## 7. Reprises de l'ère `TrainLineAI` encore ouvertes

- **La reprise sur préfixe façon `RetryToBuild`**, en clean-room : 64 `TRKFAIL` dont la recherche
  était déjà payée pour zéro profit ; ~145 M récupérables estimés, soit 453 par itération contre
  156 en moyenne.
- ✅ **La politique d'abandon** : la forme fermée coupe une recherche lorsque son rendement
  marginal attendu passe sous le rapport du meilleur candidat non essayé. Le trou du dernier rang
  (absence de suivant = budget maximal) est corrigé : son alternative est `MIN_RATIO`, rapport
  minimal déjà acceptable au prochain classement annuel, pas une constante nouvelle. Campagne
  instrumentée graine 42/20 ans : 5 derniers candidats passaient auparavant par le chemin zéro,
  mais 0 tentative ABND ; le vieux ABND à 60 000, antérieur à l'instrumentation, ne peut donc pas
  être attribué rétrospectivement à ce chemin plutôt qu'au plafond. Détail dans
  `docs/opexai_croissance.md` §6.

---

## 8. Hygiène

- ✅ **Session du 2026-08-28 committée** en 5 commits (`a227281` banc/15.3, `f6095de` sonde de
  catalogue, `212c532` mécanique du jeu, `826a6fa` OpexAI, `ee3e370` cette liste). Historique local
  uniquement : le dépôt n'a **aucun remote**.
- ✅ `README.md` mentionnait déjà OpexAI/15.3 ; `docs/methode.md` a reçu une note en tête renvoyant
  vers le `README.md` (2026-08-28) — le corps du document reste volontairement celui de la
  campagne 13.4, il décrit un protocole historique.
- ✅ **Re-baseliner le bras `OpexAI` du banc après l'instrumentation de plafonnement — FAIT le
  2026-08-29** (résultat en fin d'item). Le diff non commité dans `ai/OpexAI/` — celui qui a produit
  `docs/opexai_plafonnement.md` — contient trois choses :
  1. les **compteurs de rejet** (`candidates.nut`, table `stats` passée en paramètre à travers
     `OpexMakeCandidate`/`OpexPaxCandidates`/`OpexFreightCandidates`, ressortie par
     `OpexBuildCandidates`, déversée dans les panneaux annuels `CG`/`CR`/`CD`/`CE`/`CK`) — sans
     eux, `ranked.all` dit combien de candidats survivent mais pas pourquoi les autres meurent ;
  2. trois **panneaux** dans `main.nut` : `PM|` pour les lignes avion/bateau (elles n'en avaient
     aucun), `PC|` pour le label cargo, et `OB|A|` qui porte le coût réel en opcodes d'une
     tentative — `OR` est déjà à 31 caractères pile, d'où le panneau compagnon ;
  3. une **vraie correction de bug** dans `_reportLines` : la boucle sur les véhicules filtrait en
     dur sur `AIVehicle.VT_RAIL`, donc les lignes avion et bateau rapportaient un profit de **0**
     depuis leur création (2026-08-28). Le `vehicleType` est maintenant déduit de `line.mode`.
     Aucune décision n'en dépend : `deadStreak` est le seul retour de `_reportLines` vers le
     comportement, et il est verrouillé derrière `isFreight`.

  **Le jeu de candidats produit est identique** (vérifié ligne à ligne : `served[a] || served[b]`
  est équivalent aux deux `continue` d'origine, et le `if (monthly <= 0) continue;` du fret est
  compensé à l'intérieur d'`OpexMakeCandidate`). **Mais le profil d'opcodes ne l'est pas**, et de
  signe inconnu : côté pax `OpexOriginServed` est sorti des boucles imbriquées (O(n²) → O(n),
  ~1 000 appels → 45, une économie), côté fret toutes les industries sont évaluées d'avance et
  `OpexMakeCandidate` est appelée même à `monthly = 0` (un surcoût) ; les compteurs eux-mêmes sont
  du bruit (~8 400 incréments/an, ~0,02 % du budget annuel). Comme un décalage d'opcodes déplace
  les frontières de tick, la trajectoire diverge : **`docs/bench_v2.json` n'est plus la baseline de
  l'arbre courant.**

  **Fait** : 20 graines × 20 ans rejouées sur le seul bras `OpexAI`
  (`docs/bench_v2_opex_rebaseline.json`), fusionnées dans `docs/bench_v2.json` — `AAAHogEx` est
  conservé tel quel, il n'a pas bougé. Statistiques et comparaisons appariées recalculées par les
  fonctions de `sweeps/bench_v2.py` elles-mêmes. L'ancien bras est archivé dans le bloc
  `rebaseline.previous_opexai` du même fichier (stats + les 20 valeurs par graine).

  **Trois résultats, dont deux inattendus :**

  1. ✅ **L'instrumentation est bien neutre en décision.** Différence appariée sur `company_value`
     **−117 640** pour une SE de **194 709**, soit **t = −0,60** — non significatif ; 9 graines sur
     20 s'améliorent. Sur `performance_history`, t = −0,50. Rien ne permet de dire que le diff
     dégrade l'IA, ce qui était l'hypothèse à écarter.
  2. **L'appariement fonctionne, mais le plancher de détection reste haut.** La différence de deux
     moyennes indépendantes porterait ici ~13,1 % de SE ; l'appariement la ramène à **7,70 %** sur
     `company_value` — un facteur 1,7, pas davantage. Conséquence chiffrée : **le plus petit effet
     décelable à 2σ est ~15 % sur `company_value` et ~12 % sur `performance_history`**
     (SE appariée 5,79 %). Ceci confirme le point 2 du §5 par une seconde voie :
     `performance_history` est la bonne métrique pour opposer deux variantes d'OpexAI.
  3. 🔴 **La dispersion a doublé et le mode d'échec s'est déplacé** — voir §2.4, que ce résultat
     reformule entièrement. CV de `company_value` **32,6 % → 48,8 %** (~2σ, l'erreur-type d'un CV
     à n=20 valant ~7,9 points : suggestif, pas concluant à lui seul).

- ✅ **Committer la session du 2026-08-29 (seconde moitié)** — le plafond d'abandon et le
  raccordement v1 sont dans `154409b` / `e39685a` / `8b50f12`. Join après traction,
  `basin_share` et `reborrow` suivent : trois mesures, trois défauts à 0.

- 🔴 **Re-baseliner à nouveau : deux durcissements sont INCONDITIONNELS.** La passe du raccordement
  a introduit deux changements qui s'appliquent à toutes les lignes, y compris avec
  `station_join=0` :
  1. `AIRail.AreTilesConnected` est vérifié après **chaque** `BuildRail` dans `OpexBuildTrack`, et
     `OpexBuildLine` exige `trackFailed == 0` — une ligne auparavant déclarée construite peut donc
     finir en `TRKFAIL` ;
  2. `StartStopVehicle` est reporté après toute la boucle de construction, pour qu'un rollback
     puisse encore vendre une transaction incomplète.

  Les deux sont défendables et cohérents avec la doctrine du projet (« un appel de construction qui
  renvoie réussi ne prouve PAS que le résultat est fonctionnellement raccordé »). Comme les deux
  bras du banc les portent, la comparaison appariée reste valide. **Mais `docs/bench_v2.json` et
  `docs/opexai_plafonnement_mesure.json` ne sont plus des références** pour l'arbre courant.

- ✅ **Chemin d'API dans `docs/opexai_raccordement_gare.md`** : la note citait
  `src/script/api/script_rail.hpp` comme s'il était dans ce dépôt. Corrigé : le `src/` d'ici
  n'est que du Python ; les `@pre` restent ceux des en-têtes NoAI 15.

---

## 9. Idées de fonctionnalités à évaluer (notées le 2026-08-28)

🔴 **Les deux premières ne sont plus des idées : la mesure du 2026-08-29 les a chiffrées, et elles
commandent désormais §2.5.** Le plafonnement d'OpexAI n'est pas un défaut de classement, c'est un
**mur géométrique** : l'IA se mure elle-même. Chaque gare bâtie interdit un disque de
`MIN_SEPARATION = 10` tuiles autour d'elle, et comme les villes et industries sont exactement là où
elle a déjà bâti, elle épuise l'espace admissible bien avant d'épuiser la carte — sur la graine 999,
**18 des 19 derniers candidats sont tués par ce seul filet**, avec 37 à 39 villes encore non
desservies. Détail dans `docs/opexai_plafonnement.md`.

Ces candidats-là ne sont pas du rebut à filtrer plus finement : ce sont **les meilleurs candidats
qui restent**. Ils sont proches d'une infrastructure déjà payée, donc leur coût marginal de
construction est le plus bas de tout le vivier — un raccordement sur gare existante coûte une
fraction du pathfinding d'une ligne neuve. Sous le principe « l'opcode est une ressource »
([[philosophie_opcodes_ressource]]), c'est exactement ce qu'on veut acheter. D'où l'ordre : ces deux
items d'abord, le réglage de `MIN_SEPARATION` jamais (§2.5).

- 🔴 **Agrandir une gare existante** — deux motifs désormais, dont le second est le plus lourd :
  (a) le motif d'origine, le stock d'un cargo déjà exploité qui dépasse la capacité captée ;
  (b) **le raccordement** — transformer le rejet `_tooClose` en jonction sur la gare voisine.
  C'est (b) qui débloque le vivier chiffré ci-dessus.
- 🔴 **Gérer les jonctions de rails** — condition technique de (b) : sans jonction, deux lignes ne
  peuvent pas partager une gare. Pertinent aussi dès qu'`OpexAI` a plusieurs lignes qui se croisent ;
  voir la lecture en attente sur les jonctions en §1.

**Périmètre de mode, vérifié le 2026-08-29** : `_tooClose` n'est appelé qu'à `main.nut:374`, dans
`_tryBuild` — **le filet ne filtre que le rail**. L'avion et le bateau ne le subissent pas (une
liaison unique chacun, gardée par `_airBuilt`/`_waterBuilt`) mais **l'alimentent** : ils rejoignent
`_lines` avec `originA = originB = ` la gare bâtie (`main.nut:194`, `232`), donc un aéroport ou un
quai bloque bel et bien le rail sur 10 tuiles. Le bus, lui, est délibérément tenu **hors** de
`_lines` (`main.nut:284`) : totalement transparent au filet, dans les deux sens.

**Corollaire** : un mode qui ne consomme pas d'espace admissible ferroviaire contourne le mur par
construction. Lever le plafond « une seule liaison » du mode route rendrait les villes murées pour
le rail à nouveau desservables. À traiter comme une hypothèse et non comme un plan — le bus roule
depuis le 2026-08-28 mais son non-chargement n'est toujours pas expliqué (§6.4) et sa rentabilité
n'a jamais été mesurée sur une partie complète.
- **Gérer des voies aller-retour** (double voie) pour permettre plusieurs trains simultanés sur le
  même parcours, plutôt qu'une seule voie à sens unique par ligne.
- **Gérer une file d'attente de tâches** (queue) plutôt que le déroulement actuel, pour ordonnancer
  les constructions/décisions.
- **Contribuer à la croissance d'une ville via des stations de bus/camions** (jusqu'à 5 gares,
  une unité de cargo par 50 jours) — recoupe le mode Route déjà prévu en section 6, mais posé ici
  comme objectif de croissance plutôt que comme mode de transport en soi.
- **Planter des arbres pour augmenter la réputation** (note de compagnie) — déjà identifié dans
  `docs/mecanique_jeu.md` comme le levier de rattrapage bon marché si la note stagne à cause du
  terrassement/destruction de bâtiments.
- **Budget de construction d'une ligne proportionnel au cash** (idée notée le 2026-08-28) : plafonner
  à ~90 % de la trésorerie disponible plutôt qu'à une valeur fixe, pour que le plafond suive la
  compagnie au lieu de la brider quand elle est riche.
  ⚠️ **Vérification faite : la valeur fixe de 200 000 soupçonnée existe bien, mais ce n'est pas un
  budget en argent.** C'est `PATHFINDER_MAX_COST` (`builder_rail.nut:24`), un plafond de *coût A\**
  (unités de pathfinding), sans rapport avec la trésorerie. Côté argent, `_tryBuild`
  (`main.nut:255`) compare déjà `GetBankBalance` au `candidate.capital` calculé par ligne, moins
  `CASH_RESERVE = 50 000` — donc déjà proportionnel au cash, pas un plafond fixe. L'idée reste
  évaluable, mais sur les bons paramètres : soit rendre `CASH_RESERVE` proportionnel (au lieu de
  50 000 fixes), soit revoir `PATHFINDER_MAX_COST` — deux choses distinctes, à ne pas confondre.
