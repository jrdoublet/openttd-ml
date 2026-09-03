# Liste des tâches

Backlog du projet depuis la bascule vers `OpexAI` (2026-08-28). Les tâches faites sortent de cette
liste ; l'historique reste dans les journaux `docs/journal_*.md`.

---

## 🔴 Où en est vraiment OpexAI (mesuré le 2026-09-01) — À LIRE AVANT TOUT LE RESTE

**OpexAI perd contre AAAHogEx, très largement, et ce document contient plusieurs passages plus
anciens qui donnent l'impression inverse.** Mesure de référence actuelle :
`docs/bench_1v1_3y_1aeefe1_20seeds.json` — 20 graines × 3 ans, départ 1970, lecture appariée,
0 échec de script :

| métrique | écart apparié OpexAI vs AAAHogEx | graines gagnées |
|---|---:|---:|
| `company_value` | **−87,8 %** (602 750 £ contre 4 947 586 £) | **0/20** |
| `profit_year` | **−91,5 %** | **0/20** |
| `performance_history` | −71,0 % | 0/20 |
| `median_station_rating` | −12,0 % | 0/20 |

Décomposition : `8,5 % de profit = 12,4 % de volume × 68,6 % de rendement unitaire`. Donc **~85 %
de l'écart vient du volume** (8× moins de véhicules et de gares) et ~15 % du rendement par
véhicule. La note de gare presque au niveau ne veut PAS dire que l'IA est presque au niveau.

Goulot identifié, et ce n'est **pas** la trésorerie : avec ≥300 k£ en caisse, OpexAI ne construit
rien dans **61,2 %** des transitions mensuelles, contre 2,8 % chez AAAHogEx ; 19,2 mois actifs sur
36 contre 32,4 ; 9,6 mois entièrement figés. AAAHogEx passe même *plus* de mois sous 50 k£ que nous
(14,6 contre 13,55). Le goulot est le **débit du contrôleur** — sélection, planification et
exécution des projets.

### 🧭 Où mène la piste au 2026-09-03 au soir

Journée de mesure : `air_hub_fix` adopté (défaut de type, §0 octovicies), `tree_planting` infirmé
une seconde fois (D1), `air_demand_cap` et `air_demand_plan` **tous deux rejetés** (§3 undecies
bis, §0 trigesies), lecture d'AAAHogEx sur le dimensionnement aérien (§0 novemvicies).

**L'item de tête est A1** — le dénominateur du classement dépendant de la ressource rare. Trois
mesures indépendantes y convergent désormais, et l'objection qui le bloquait est tombée : à
**10 ans, 18 graines sur 20 passent le test `_IsRich` d'AAAHogEx**, donc l'argument « nous sommes
pauvres, leur aiguillage ne travaillerait pas chez nous » ne tient plus. Détail dans le tableau A.

### Comment lire les chiffres de ce document sans se tromper

1. **Un banc à 5 graines ne tranche rien**, et un banc **à 1 an** encore moins : AAAHogEx monte en
   puissance lentement, donc le battre à l'an 1 ne dit rien sur 3 ans. Plusieurs sections
   ci-dessous annoncent des victoires sur ce type de banc — elles sont **contredites** par la
   mesure 20 graines × 3 ans ci-dessus. Elles sont conservées comme historique, pas comme preuve.
2. **Plancher de détection du banc à n=20** : ~15 % sur `company_value`, ~12 % sur
   `performance_history`. Sous ça, un résultat non significatif ne prouve **pas** l'absence d'effet.
3. **Contre AAAHogEx, `performance_history` est inutilisable** (saturée chez lui, CV 0,5 %). Seuls
   `company_value` et `profit_year` parlent. Entre deux variantes d'OpexAI, c'est l'inverse.
4. **Une valeur absolue sans l'adversaire sur les mêmes graines ne veut rien dire.** « Valeur
   moyenne 1,40 M£ » n'est pas un résultat tant qu'on ne sait pas ce qu'AAAHogEx fait sur ces
   graines-là (il fait ~4,9 M£ à 3 ans).
5. **« Solvabilité 100 % » n'est pas une performance** : ne pas faire faillite est un plancher, pas
   un objectif. Voir l'ordre des objectifs ci-dessous.

---

## Ordre des objectifs

1. **Maximiser le profit attendu par opcode.**
2. **Maximiser la performance de compagnie.**
3. **Maximiser les notes.**
4. **Maximiser la valeur de compagnie.**

Un objectif inferieur ne justifie jamais de sacrifier un objectif superieur. Les bancs doivent
donc etre lus dans cet ordre, et pas en prenant `company_value` comme arbitre unique.

---

## Fonctionnalités livrées le 2026-09-01 — ⚠️ livrées, PAS validées contre AAAHogEx

⚠️ **Titre corrigé le 2026-09-01.** Cette section s'intitulait « Tâches Récentes Validées au Banc »,
ce qui est faux et trompeur : aucun de ces items n'a été opposé à AAAHogEx en lecture appariée sur
20 graines. Les chiffres cités sont les valeurs **absolues d'OpexAI seul**, sans l'adversaire sur
les mêmes graines. Le banc 1v1 qui a suivi (voir le bloc rouge en tête de document) donne **0/20
graines gagnées et −87,8 %**. Ces fonctionnalités existent et tournent ; elles n'ont pas fermé
l'écart.

✅ **Multiplication des Corridors Longue Distance & Réseau Hub-to-Hub Dès 30 000 £** — Interconnexion directe des aéroports du réseau (Hub-to-Hub à coût marginal d'1 avion seul ~30k £) et extensions étoilées (Hub-and-Spoke à 1 aéroport + 1 avion ~92k £), portant le plafond de routes par grand aéroport à 12.
✅ **Toile de Feeder Buses Satellites Vers les Hubs** — Raccordement systématique des 3 à 5 villages satellites (dès 200 habitants dans un rayon de 40 tuiles) avec ordres de transfert OpenTTD (`AIOrder.OF_TRANSFER | AIOrder.OF_UNLOAD`), saturation des lignes mères et bonus d'évaluation de +60 % ROI.
✅ **Montée en Flotte Agressive & Clonage Fiable** — Algorithme de redimensionnement de flotte mensuel en continu, acquisition automatique d'avions supplémentaires dès rentabilité/fonds disponibles, et fallback résilient `BuildVehicleWithRefit` + `ShareOrders`.
⚠️ **Banc 1v1 Face-à-Face Multi-Graines 5 Ans** — Performance moyenne de **1 135 658 £** de valeur d'entreprise (pics à **1,72 M£** et **1,63 M£**), **331 903 £/an** de bénéfices nets ($+116\%$), flotte moyenne de **42,6 véhicules** ($+255\%$) et solvabilité **100% (5/5 sans faillite)**.
  **Ces chiffres ne comparent rien** : ils décrivent OpexAI seul, sur 5 graines, sans les valeurs
  d'AAAHogEx sur ces mêmes graines, et les pourcentages sont relatifs à une baseline OpexAI
  antérieure — pas à l'adversaire. À 3 ans sur 20 graines, AAAHogEx est à 4,9 M£ contre 0,60 M£
  pour nous. Ne pas citer cette ligne comme une victoire.

---

## 1. À lire et intégrer (demandé le 2026-08-28)

À traiter comme `docs/mecanique_jeu.md` : **pas une copie du wiki, mais règle + conséquence pour la
conception**, avec ce qui est vérifié et ce qui ne l'est pas.

✅ **[Manual/Tips](https://wiki.openttd.org/en/Manual/Tips) lue et intégrée (2026-08-28)** — voir
`docs/mecanique_jeu.md` §9. La plupart des heuristiques utiles étaient déjà couvertes ailleurs dans
le document (note de gare §3, note d'autorité §7, vitesse/virages §2) ; l'apport net : ordres
partagés (`AIOrder.ShareOrders`, non exploité), boucles de gare routière pour le futur mode Route,
et une piste non vérifiée sur les avions qui diffuseraient mieux leur influence que le rail.

✅ **[Manual/Industries](https://wiki.openttd.org/en/Manual/Industries) lue et intégrée
(2026-08-28)** — voir `docs/mecanique_jeu.md` §10. La table des chaînes de production ne change
rien au code : `catalog.nut` interroge déjà l'API dynamiquement plutôt que coder les chaînes en
dur. L'apport net : (1) ✅ croissance d'une primaire = % transporté, relu en
15.3 (`ChangeIndustryProduction`, `mecanique_jeu.md` §4) — pas un terme de
classement, pas de retuning ; l'écart fret ~4-6x est réfuté ; (2)
`difficulty.economy = false` : récession **sans objet** chez nous.

✅ **[transporttycoon.net/rail1](https://www.transporttycoon.net/rail1) … [rail6](https://www.transporttycoon.net/rail6)
et [junctions](https://www.transporttycoon.net/junctions) lus et intégrés (2026-08-30)** — voir
`docs/mecanique_jeu.md` §12. Série TTD + TTDPatch, pas le wiki 15.3. Apport net : OpexAI *est*
le point-à-point que la page moque, et `JOINPATH` doit le rester tant que la jointure ne paie
pas ; `trains > 1` exige une **deuxième voie dédiée** (un convoi par chemin, plafond 2), pas
des PBS sur voie unique ; si `station_join` / `join_place`, PBS sur les approches **simples**
d'une jointure — jamais sur `TracksOverlap` ; quai déjà calé sur la rame ; les jonctions se résument à trois principes (séparer
avant de fusionner, sortie avant entrée, train+2 tuiles) — l'index Junctionairy n'est qu'un
catalogue d'images, on ne copie pas de cloverleaf. Waypoints natifs OpenTTD, utiles seulement
le jour des branches. Pré-signaux TTDPatch = path signals chez nous.

✅ **[Community/Pseudo canals](https://wiki.openttd.org/en/Community/Pseudo%20canals) lue et
intégrée (2026-08-30)** — voir `docs/mecanique_jeu.md` §13. Apport net : ce n'est pas un canal,
c'est une inondation au niveau de la mer (terraform **à sec**, ouvrir en dernier). Le trick ne
monte pas une colline ; un vrai canal existe précisément là où baisser le terrain coûterait
plus. OpexAI eau v1 ne terraform jamais ; une paire sans composante d'eau naturelle reste
ignorée. ❓ Coût opcode/argent de l'inondation vs `BuildCanal` non mesuré. **Pas de canal pour
un bateau pax.**

La liste de lecture demandée le 2026-08-28 est **vide**.

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
3. ✅ **Rendement des jointures — parallèle 1–4, mesuré, défaut 0** (2026-08-30).
   Le colle unique (offset 1) était 658/692 SITE à `nClear=0`. Offset 1–4, même
   orientation : 39 → **71** OK (5,5 % → 15,7 %), SITE 692 → 393, JOINPATH 0.
   Il reste **361** SITE au quai joint à `nClear=0` — c'est le spread, et le
   spread n'est pas la suite. 5/5 plus de véhicules, 4/5 moins de valeur (cinq
   graines, pas un banc). `docs/opex_join_parallel_20y_5seeds.json`.
4. ⚠️ Ne **pas** corriger `monthly` pour une origine servie sur la foi du chiffre brut : c'est le
   piège que cette mesure vient de désamorcer. Le partage de stock **une fois la gare jointe**
   (plusieurs lignes, même `StationID`) est un autre terme, lui encore ouvert (§2.9.3).
5. ✅ **Étape 0 + H1 porte 50 tuiles** (2026-08-30). Population
   (`docs/opex_join_pop.json`) : jointes 63 tuiles / 0,80 vs neuves 43 / 1,19.
   <50 paie (1,12) ; ≥100 : 0,07. `join_max_distance` défaut 0 ; à 50, 5 graines
   (`docs/opex_join_cap50_20y_5seeds.json`) : 29 jointures, dist. 37, D=1035.
   Coupe le vivier (véhicules − vs parallèle). **Ne bat pas `join=0`** (2 graines
   −30 %). Pas de banc n=20.
6. ✅ **H2 joindre au lieu + signaux PBS** (2026-08-30). `join_place` défaut
   **0**. Candidats depuis une gare rail OpexAI vers une origine libre
   (bande 25–75), join attaché à la génération, quai parallèle 1–4,
   `JOINPATH` dédié. PBS devant les quais joints et sur l'aiguillage
   dépôt (1 jonction / jointure : le dépôt). 5 graines
   (`docs/opex_join_place_20y_5seeds.json`) : 50 jointures, dist. 50,
   réel/prédit an 2 **−0,16**. Médiane valeur **−64 %** vs `join=0`
   (5/5, graine 100 −92 %). Le TOP_K se remplit de H2 (43–143 classés,
   7–14 OK), SITEA explose (spread au quai joint). Moins de véhicules
   **et** moins de valeur. ⚠️ **Pas de banc n=20. Pas de spread.**
   Signaux (mesure H2) : 77 OK / 128 fail / 50 junc — le PBS du dépôt passe, le
   front de quai vers la gare refuse souvent. Placement **périmé** le soir même :
   plus de signal sur l'aiguillage (item 9.4).
7. ✅ **Rejeu join + double voie** (2026-08-30). La 2e voie dédiée s'applique
   aussi à une jointure (quai voisin ignoré, `JOINPATH`). 5 graines × 20 ans
   contre `docs/opex_double_track_20y_5seeds.json` (join=0, médiane **5,73 M**) :

   | | médiane | vs join=0 | graines | jointures | DT |
   |---|---:|---:|---:|---:|---:|
   | `station_join=1` | 3,59 M | −2,14 M | 3/5 | 64/427 | 70/122 |
   | + `join_max_distance=50` | 4,43 M | −1,30 M | 1/5 | 21/88 | 52/77 |
   | `join_place=1` | 3,69 M | −2,04 M | 2/5 | 52/266 | 63/109 |

   0 `XC`/`RX`, emprunt 0, pas deux trains sur une voie. Même piège : plus de
   construction, moins de valeur. ⚠️ **Défauts 0.** Pas un banc n=20. Pas de spread.
   Preuves : `docs/opex_join_dt_20y_5seeds.json`,
   `docs/opex_join_cap50_dt_20y_5seeds.json`,
   `docs/opex_join_place_dt_20y_5seeds.json`.

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

---

## 0 ter. Ranking composite Train & Avion — HISTORIQUE, remplacé le 2026-09-01

Répond au mur de trésorerie précoce par un arbitrage multi-critères inspiré des principes d'AAAHogEx (`docs/aaahogex_evaluation.md` §5quinquies) en *clean-room design* :

1. **Ranking composite ROI / Rotation / Opcode** (`candidates.nut`, `economy.nut`) :
   - Le ratio pur `profitAnnual / iterations` favorisait parfois des lignes ferroviaires très coûteuses (200k-250k £) à amortissement lent.
   - Le score intègre désormais le **ROI** ($\text{profitAnnual} / \text{capital}$) modulé par la **vitesse de rotation** (`oneWayDays`), tout en conservant le plancher strict `opcodeRatio >= MIN_RATIO`.
2. **Couples Aéroports et Avions (Grands vs Petits)** (`catalog.nut`, `builder_air.nut`) :
   - Grands aéroports compatibles avec les gros avions (`PT_BIG_PLANE`) et petits avions.
   - Petits aéroports réservés **STRICTEMENT aux petits avions** (`PT_SMALL_PLANE`).
   - Modélisation économique complète de l'avion (facteur de vitesse OpenTTD à 1/4 du catalogue) et arbitrage direct de rentabilité.

**Correction aérienne mesurée le 2026-08-31, graine 42.** Le modèle ajoutait
`24 * AIAirport.GetMonthlyMaintenanceCost(AT_LARGE)`, soit **270 000 £/an** pour deux
aéroports, alors que `economy.infrastructure_maintenance=false` et que le moteur ne débite donc
jamais cette charge. La première paire passait artificiellement de **+63 609 £/an** à
**−206 391 £/an** et tout l'air était rejeté. Le coût n'est désormais compté que lorsque le
réglage est actif. Validation : une ligne aérienne construite dès 1970, profit réel
**42 178 £** en 1971 ; duel partagé 3 ans contre AAAHogEx (diagnostic sur une seule graine,
pas un banc apparié), OpexAI passe de **140 071 à
197 899 £** de profit annuel (+41 %) et de **286 851 à 350 538 £** de valeur (+22 %).
La prochaine limite est distincte : OpexAI n'a encore que **2 avions** fin 1972 contre **40**
pour AAAHogEx ; dimensionner la flotte doit être mesuré séparément, sans confondre ce levier
avec la correction certaine de maintenance.

**Taille de flotte aérienne — implémentée et validée le 2026-08-31.** L'essai naïf « maximiser
le profit prédit de chaque liaison » achetait trois avions dès 1970. Il a été rejeté : sur le duel
partagé graine 42 à trois ans, OpexAI tombait à **43 999 £/an** et **67 504 £** de valeur, contre
**197 899 £/an** et **350 538 £** avec la correction de maintenance seule. Le capital immobilisé
sur une ligne empêchait d'en ouvrir une seconde et les trois appareils ne rapportaient ensemble
que 24 037 £ sur leur dernière année.

La politique retenue sépare maintenant les deux décisions :

1. une nouvelle liaison démarre avec **un avion**, les liaisons restant classées au ROI ;
2. une passe annuelle peut cloner **au plus un avion par ligne**, avec ordres partagés, seulement
   après une année réelle positive et si au moins une capacité complète attend dans les deux
   aéroports ; manque de cash ou absence de demande sont reportés à l'année suivante, jamais
   resondés à chaque tour de file. Plafond de sécurité : huit avions par ligne. `FA` rapporte le
   backlog observé et `FG` toute tentative d'agrandissement.

Validation diagnostique, toujours sur une seule graine : duel partagé trois ans
`docs/head_to_head_seed42_air_fleet_roi_3y.json`, **204 356 £/an**, valeur **352 023 £**, deux
avions sur deux lignes ; soit légèrement au-dessus de la référence maintenance seule, sans
surallocation. Partie seule dix ans `docs/opex_air_fleet_roi_10y_42.json` : six lignes aériennes
d'un avion, aucune `FG` car aucune n'avait une pleine capacité en attente. C'est un
**non-déclenchement correct**, pas encore une preuve statistique de gain de l'expansion : un banc
multi-graines sera nécessaire dès que `FG` fournit un échantillon.
3. **Banc de validation (5 graines × 5 ans)** :
   - Trésorerie moyenne à l'an 5 : **~454 400 £** (déblocage total du mur de trésorerie).
   - Valeur moyenne d'entreprise : **~434 400 £**.
   - Lignes construites : **7,2 lignes/partie** (100 % de rentabilité en exploitation).

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

**Ce qui restait explicitement non établi après traction :**

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

## 0 quater. ✅ Portefeuille ROI → capital → opcodes — FAIT (2026-09-01)

`ai/OpexAI/projects.nut` intègre les alternatives modales dans un portefeuille unifié :
1. génération de toutes les alternatives rentables rail/route/air/eau ;
2. classement et arbitrage par couple origine/destination au meilleur `profitAnnual / capital` (ROI) ;
3. maximisation gloutonne du revenu sous le capital réellement mobilisable ;
4. exécution ordonnancée sous contrainte de capital et d'opcodes (`revenueAnnual / expectedOpcodes`).

Points clés et stabilisations validés :
- Protection contre l'affamement de capital : les petites liaisons routières locales ne saturent plus le budget glouton au détriment des axes structurants fer/air à fort flux de trésorerie ;
- Maintien du précalcul ferroviaire continu (`_tryPreplan`) sur les meilleurs candidats rail (`_ranked.best`) pendant les opcodes dormants pour permettre une construction instantanée dès l'accumulation du capital requis ;
- Télémétrie opérationnelle : `IG` (vivier d'alternatives, couples O/D, projets financés) et `IB` (budget mobilisable vs capital sélectionné).

Résultats sur banc multi-graines 5 ans (`docs/head_to_head_5seeds.json`) :
- Graine 42 : Valeur = 809 379 £, Profit annuel = 299 920 £, Score = 402
- Graine 17 : Valeur = 528 099 £, Profit annuel = 230 813 £, Score = 303
- Graine 123 : Valeur = 880 036 £, Profit annuel = 249 633 £, Score = 413
- Graine 7 : Valeur = 402 865 £, Profit annuel = 146 619 £, Score = 336
- Graine 99 : Valeur = 420 962 £, Profit annuel = 119 865 £, Score = 258

---

## 0 quinquies. ⚠️ Optimisation Multi-Époques (1950, 1970, 1990) & Pistes A, B, C — LIVRÉ, non validé (2026-09-01)

Comparaison face-à-face an 1 contre AAAHogEx sur 3 époques technologiques distinctes :

1. **Piste B (Réajustement dynamique de flotte en temps réel)** :
   - Sondage du profit opérationnel en cours via `AIVehicle.GetProfitThisYear(v) > 2500 £` dans `_resizeAirFleets` pour cloner des appareils dès le 2e trimestre au lieu d'attendre la clôture de fin d'année.
   - Plafonnage de sécurité : max 4 avions sur `AT_SMALL`, jusqu'à 10 avions sur `AT_LARGE`.
2. **Piste C (Maillage combinatoire Hub-à-Hub complet)** :
   - Évaluation et priorisation systématique des corridors Hub-à-Hub ($N \times (N-1)/2$) entre aéroports existants (`reuseA = true, reuseB = true`, coût infrastructure = 0 £, ROI de 120 % à 250 %).
   - Seuil de distance inter-hubs abaissé à 35 tuiles.
4. **Modèle de ROI Véhicule Avancé & Dimensionnement de Flotte Convexe** :
   - Intégration de la cinématique et des temps de manœuvre aéroportuaire ($\tau_{\text{airport}} = 3.0\text{ jours}$).
   - Dimensionnement dynamique de la flotte par liaison ($N^* = \arg\max \Pi(N)$) selon le volume passagers et la note de captage de station `OpexStationRatingForHeadway`.
   - Modélisation exacte de la valeur marginale du capital et de la vitesse de rotation de trésorerie.

⚠️ **Avertissement ajouté le 2026-09-01 — les résultats ci-dessous ne survivent pas au banc.**
Ils viennent de bancs à **5 graines** et, pour le plus flatteur, sur **1 an**. Or l'horizon d'un an
est un régime très particulier : AAAHogEx démarre lentement et n'a pas encore composé. Battre
AAAHogEx à l'an 1 sur 5 graines **ne prédit rien** à 3 ans. Le banc 20 graines × 3 ans
(`docs/bench_1v1_3y_1aeefe1_20seeds.json`) donne **0/20 graines gagnées et −87,8 % de valeur**.
Par ailleurs les valeurs absolues citées ici (« 850 000 £ à 3 ans en 1970 ») ne se reproduisent pas
sur 20 graines : la mesure appariée donne **602 750 £** de moyenne sur le même horizon et la même
année de départ. Historique conservé, **à ne pas citer comme un acquis**.

Résultats du banc comparatif 1 an (5 graines × 1 an) avec le nouveau modèle de ROI :
- **1950 (Vapeur / Hélices)** : OpexAI devance AAAHogEx en valeur d'entreprise moyenne de +69,1 % (**97 998 £ vs 57 963 £**), note des gares **171.1** (vs 163.9 chez AAA), solvabilité **100 %** (0 faillite chez OpexAI vs 2 faillites chez AAAHogEx). ⚠️ **5 graines, 1 an : sous le plancher de détection et hors du régime qui compte.**
- **1970 (Diesel / Jets)** : Valeur d'entreprise moyenne monte à **160 336 £** (+306 % vs baseline), profit annuel an 1 à **137 851 £** (+229 %), score officiel à **143.8** (+97 %).
- **1990 (Électrique / Réacteurs)** : Valeur d'entreprise moyenne monte à **225 095 £** (+426 % vs baseline), profit annuel an 1 à **177 212 £** (+223 %), score officiel à **161.4** (vs 182.4 chez AAAHogEx), note des gares **180.1** (> AAAHogEx 163.3), solvabilité **100 %**.

Résultats du banc comparatif 3 ans (5 graines × 3 ans) :
- **1990** : Valeur moyenne à **1,40 M£** (Peak 1,74 M£), profit annuel à **853 000 £/an** (Peak 1,18 M£/an), score à **420.6**, 106 véhicules, 57 stations, solvabilité **100 %**.
- **1970** : Valeur moyenne à **850 000 £** (Peak 1,22 M£), profit annuel à **433 000 £/an** (Peak 686k £/an), score à **298.8** (Peak 513), 80 véhicules, 50 stations, solvabilité **100 %**.
- **1950** : Valeur moyenne à **205 000 £** (Peak 316k £), profit annuel à **121 000 £/an**, solvabilité **100 %**.

Résultats du banc comparatif 5 ans (5 graines × 5 ans) :
- **1990** : Valeur moyenne à **1,91 M£** (Peak **3,38 M£** sur graine 17), profit annuel moyen à **526 000 £/an** (Peak **943 000 £/an**), 110 véhicules, 36 stations, solvabilité **100 %**.
- **1970** : Valeur moyenne à **1,70 M£** (Peak **2,45 M£** sur graine 7), profit annuel moyen à **615 000 £/an** (Peak **1,03 M£/an**), score à **443.6** (Peak **618**), 109 véhicules, 61 stations, solvabilité **100 %**.

5. **Typage des Aéroports par Strate Urbaine & Chaînes d'Approvisionnement Industrielles** :
   - **Typage des aéroports selon la population** : `AT_SMALL` / `AT_COMMUTER` (4×3) strictement réservés aux villes secondaires (< 2 500 hab), évitant d'implanter des infrastructures 6×6 surdimensionnées et déficitaires dans des villages de 400 habitants.
   - **Modélisation des chaînes de transformation (Ferme $\rightarrow$ Usine $\rightarrow$ Ville)** : Bonus de valeur induite de +30 % sur les liaisons alimentant des industries de transformation (`isTransformer`), et estimation dynamique de production pour la desserte aval des Marchandises vers les villes.
   - **Financement réactif de l'extension de flotte** : Recours à `OpexTryReborrow` dans `OpexAirAddPlane` pour débloquer l'achat d'appareils rentables (>40 000 £/an de profit) dès saturation de ligne sans blocage de trésorerie passager.
   - **Déblocage du réinvestissement An 1 & Scan Hub-to-New** : Correction de l'indice de recherche de sites d'expansion Hub (`i = 0` sur l'ensemble des villes libres au lieu de `i = limit`), diversification du capital initial (2 avions par nouveau corridor), et abaissement du seuil de rentabilité pour l'extension de flotte précoce dès le premier trimestre. La valeur moyenne à 5 ans en face-à-face partagé grimpe à **993 432 £** (Peak **1,35 M£**) et le profit moyen à **328 532 £/an** (Peak **520 755 £/an**).
    - **Distance euclidienne de vol & Compartiment postal en soute** : Remplacement de la distance Manhattan par la distance euclidienne exacte `AIOrder.GetOrderDistance(AIVehicle.VT_AIR, a, b)` (+25 % de rotations/an calculées fidèles au moteur OpenTTD), et intégration de la valorisation automatique du fret postal en soute (`AICargo.CC_MAIL`) offrant +15 % à +20 % de revenus nets supplémentaires sur chaque vol.

6. **Spécification : Système de Transferts et Correspondances (Hub-and-Spoke Cargo Transfers)** :
   - **Mécanique OpenTTD** : Utilisation des ordres combinés `AIOrder.OF_TRANSFER` et `AIOrder.OF_UNLOAD` (`Transfer and Leave Empty`) sur les stations de correspondance.
   - **Architecture Feeder-to-Hub** :
     1. *Liaisons d'apport régional (Feeders)* : Bus urbains, camions de fret ou petits avions régionaux (`AT_SMALL` / `PT_SMALL_PLANE`) collectent les passagers/cargos dans les villes secondaires et les déposent à l'aéroport ou la gare hub métropolitaine la plus proche avec ordre de transfert.
     2. *Liaisons Magistrales Express (Trunk lines)* : Gros jets (`PT_BIG_PLANE`) ou trains express intercités reprennent les flux consolidés pour les acheminer vers les métropoles lointaines.
   - **Règlement financier OpenTTD** : Le moteur de jeu crédite un acompte partiel sur la jambe d'apport et liquide la totalité du tarif kilométrique origin-to-destination au déchargement final dans la métropole d'arrivée, maximisant le profit par opcode.

---

## 1 bis. Mode route : ouvert, mesuré, et ce qui reste (2026-08-29, révisé 2026-08-30)

**✅ Re-baseliné et adopté** (`docs/bench_road_current.json`, 20 graines × 20 ans) :
`performance_history` **+15,3 %, t = 5,65, 18 graines sur 20** ; `company_value`
**+13,5 %, t = 2,24, 13/20**. Ce banc tourne avec traction et
`road_pax_catchment_pct=86` : le mode route est désormais établi sur l'arbre courant.

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

1. ✅ **Le plancher `ROAD_MIN_PROFIT_ANNUAL` : mesuré, pas retuné** (2026-08-30).
   n n'est plus 1. 12 lignes pax (`docs/opex_road_predict_vs_actual.json`) :
   médiane réel/prédit **3,91** sur le profit, **2,29** sur le revenu
   (1,33–7,42 ; le 1,33 est la ligne morte pré-refleet). Fret témoin n = 6 :
   **1,21 / 1,03** — même vitesse, pas de bassin ville. `RY` le confirme :
   pax 0,75 vs catalogue, pas un ×4. Sur l'arbre courant le plancher coupe 76 %
   des paires en bande (406/532), 0 pax sur 5 graines.
   ✅ **Bassin pax route adopté (2026-08-30).** `road_pax_catchment_pct = 86` est le défaut ;
   `0` rétablit le contrôle à 22 %. Banc apparié 20 graines : `performance_history`
   **+4,19 %** (+22,2), t = **2,48**, 14/20 ; `company_value` −1,32 %, nul.
   Voir `docs/bench_road_pax_catchment.json`.
2. ✅ **`SITEA`/`SITEB` : on sondait des maisons — FAIT** (2026-08-30).
   Le cargo est sur le bâtiment ; `BuildRoadStation` n'y marchera pas, et 48 sondes
   y passent avant l'herbe. Filtre `IsBuildable` + plat sur l'arrêt (comme le rail),
   façade plate, constructible sauf route déjà là. 5 graines
   (`docs/opex_road_sitable_20y_5seeds.json`) : SITEA 12→**0**, SITEB 2→**0**,
   OK 2→**6**. TRACEX ensuite, item 2 bis. Pas un nouveau réglage.
2 bis. ✅ **TRACEX : 32 L et façade vers l'autre bout** (2026-08-30).
   Le plafond à 12 coupait après 6 paires (classement cargo, pas géométrie).
   `nLong = 0`. ~½ des L traversaient l'arrêt. 32 essais + bonus de façade
   tournée vers l'autre extrémité : TRACEX 5→**2**, OK 6→**8**, pax 2→**4**
   (`docs/opex_road_tracex_20y_5seeds.json`). Les 2 restants sont `nUnb`.
   Pas Pathfinder.Road.
3. ✅ **Classement inter-modes : mesuré, pas unifié** (2026-08-30).
   Panneau `RB`, campagne TRACEX déjà là, n = 10 (`docs/opex_road_rb_calibrate.json`).
   Plan OK médiane **31 440** opcodes (~11,7 iter) contre modèle `20+d` ≈ 42,5
   (rapport **0,29**). TRACEX 70–107 k. Le build (médiane 287 k) n'est pas le
   dénominateur du rail (A*). Ratio profit/plan de la route **68 k–710 k** contre
   rail médiane 5 040 / `MIN_RATIO` 500 : un classement unique affamerait le rail.
   ⚠️ **Pas de retuning de `BASE`.** Le rail d'abord (`docs/opexai_route.md` §2)
   est une décision de valeur, pas d'opcode.
4. ✅ **Multistop : le mécanisme marche, les 4 véhicules non** (2026-08-30).
   Réglage `road_multistop`, défaut 0. Un arrêt extra par bout, même façade, joint
   par l'identifiant du primaire (pas `STATION_JOIN_ADJACENT` nu). Clones au-delà
   de 2 seulement si les deux bouts ont doublé. 5 graines
   (`docs/opex_road_multistop_20y_5seeds.json` contre TRACEX) : extra A 7/8, extra
   B 8/8, les deux 7/8, 4 véhicules 7/8. La ligne pax appariée (graine 12345, L22,
   1983, 24 tuiles) passe **8 905 → 1 781** à 4 bus. 4096 IORE 5 153 → 3 792, et
   la WOOD disparaît. Le ×5 du wiki n'est pas là. ⚠️ **Défaut 0.** Pas un banc
   n=20 : le pairé dit déjà que les clones extra ne paient pas.
5. ✅ **Reconstitution de flotte routiere : faite, defaut 1** (2026-08-29, nuit).
   Le trou n'était pas n = 1 : sur `docs/opex_road_20y_42.json` la ligne pax 15 passe 2→1→0
   (1985-87, 9 000/an puis notes 54→−1) ; sur `docs/opex_join_20y_42.json` le COAL fait 2→1→0
   et reste vide **huit ans**. Auto-renouvellement ne couvre pas un véhicule détruit (passage à
   niveau) ni un renouvellement refusé faute de cash : une ligne à zéro n'a plus rien à renouveler.

   **Ce que 1 fait.** Après `_reportLines` / `_scrapDeadLines`, une ligne routière sous
   `predTrains` (borné à 2), dépôt et arrêts encore là, pas en rebut, reçoit les véhicules
   manquants. Un restant → clone ; zéro → moteur du catalogue + ordres. Panneau `RF`.
   Réglage `road_refleet`, `OpexAI[road_refleet=0]` rallume l'abandon.

   **Mesure** (`docs/opex_refleet_20y_4seeds.json`, graine 42, 20 ans) : ligne COAL 15 bâtie
   en 1975 à 2 camions. 1982 : 2→1, `RF` ajoute 1, 1983 rating 22→61. 1988 : encore 2→1,
   `RF` ajoute 1, 1989 rating 29→67. **Jamais à zéro.** La ligne WOOD jumelle (jamais de
   perte) n'est pas touchée. Les trois autres graines n'avaient pas de ligne routière.

---

## 2. Le code, par ordre d'impact mesuré

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
2. **Ne pas enfermer la ville dans nos propres voies** — la mesure existe
   (`docs/opex_town_growth.json`, 2026-08-30) : les villes desservies n'estagnent **pas**
   comme classe. Le barème 15.3 accélère avec 1–5 gares actives. ⚠️ **Reste dernier** :
   pas de contrainte de tracé rail. Un effet local (maisons coincées par nos voies) n'est
   pas isolé.
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

7. ✅ **Le biais de sélection du modèle de profit : mesuré, défaut 0** (2026-08-30).
   Réglage `probe_negative` : après `_tryBuild`, au plus une paire rail rejetée pour
   profit prédit ≤ 0 est force-construite sur le cash restant, budget `ATTEMPT_FLOOR`.
   PX marque la ligne ; elle ne contamine pas la calibration des lignes classées.
   5 graines × 20 ans (`docs/opex_probe_negative_20y_5seeds.json`) :

   | | |
   |---|---|
   | paires-années `profit≤0` | 14 001, dont **13 918 pax** et 83 fret |
   | bandes | 2 010 / 1 987 / 1 998 / **8 006 >100 tuiles** |
   | « presque admis » (prédit > −1000) | 5 546 |
   | tentatives | 52 (médiane prédit **−39,5**, médiane **123 tuiles**) |
   | issues | **48 ABND**, 4 OK |
   | OK : distance | 63, 64, 67, 73 (médiane 65,5) — le court du stash |
   | OK : prédit | −146, −143, −16, −39 |
   | OK : profit réel, 2e année | 22 798 / −53 / 20 436 / 13 695 — **3/4 > 0** |
   | OK : profit réel, dernière année | **4/4 > 0**, médiane 18 972 |

   Le 45,2 % de `docs/opexai_plafonnement.md` est **périmé** (avant traction) : en 1989
   sur les 4 graines d'origine, `profit≤0` = 608 / 4 217 = **14,4 %**, toujours presque
   tout du pax. L'origine déjà desservie est devenue le premier filtre (62 %).

   **Ce que ça tranche.** On ne peut plus conclure que les paires rejetées sont
   réellement non rentables. Les 4 qui passent A\* à 2 000 itérations (60–75 tuiles,
   pax) rapportent 10–20 k/an pour un prédit ~−100. **Ce que ça ne tranche pas :**
   48/52 ABND, médiane 123 tuiles — `ATTEMPT_FLOOR` censure le long, qui est le
   volume (57 % des rejets >100 tuiles). n=4 n'est pas un retuning.

   ⚠️ **Défaut 0.** `OpexAI[probe_negative=1]` rallume. Ne pas recalibrer
   `OpexLineEconomics` ni baisser le filtre `profit≤0` sur cet échantillon.

   ✅ **Suite : même sondage, plafond dur 40 000** (2026-08-30, soir).
   `alternativeRatio = 0` → chemin Z, `HARD_ITERATION_CAP`. Aucun paramètre
   ajouté à `OpexBuildLine` : le classement ne change pas d'opcodes.
   5 graines × 20 ans (`docs/opex_probe_negative_hardcap_20y_5seeds.json`) :

   | | plancher 2 000 | plafond 40 000 |
   |---|---:|---:|
   | tentatives | 52 | 29 |
   | OK / ABND | 4 / 48 | **20 / 8** |
   | médiane dist. tentées | 123 | 120 |
   | médiane dist. OK / ABND | 65,5 / 124,5 | **94,5 / 163,5** |

   | bande | n | OK | last year > 0 | médiane last |
   |---|---:|---:|---:|---:|
   | ≤50 | 2 | 2 | **2/2** | 12 737 |
   | 50–75 | 4 | 4 | **4/4** | 17 231 |
   | 75–100 | 6 | 5 | **5/5** | 11 980 |
   | >100 | 17 | 9 | **3/8** | **0** |

   **≤100 tuiles : 11/11 rentables** en dernière année, pax, prédit ~−40. Le n=4
   du plancher se reproduit et s'étend. **>100 tuiles : médiane 0**, 3/8 > 0
   (123, 163, 164 tuiles à +15–28 k ; 109 et une 123 à 0 ; 160 à −2 132).
   Deux 146 tuiles n'ont qu'une année partielle. Les 8 ABND restants sont
   du très long (110–195 tuiles) au plafond.

   ⚠️ **Ne pas lever `profit≤0` globalement** : ce serait réadmettre le long
   qui ne paie pas, le piège du vivier. Défaut `probe_negative` **0**.

   ✅ **Retuning pax borné : écrit, mesuré, défaut 0** (2026-08-30, nuit).
   Réglage `pax_near` : pax, ≤100 tuiles, prédit dans (−200, 0], ratio = 1,
   au plus 1 tentative/an au plafond dur. 5 graines
   (`docs/opex_pax_near_20y_5seeds.json`) : 21 lignes, toutes pax, 38–97 tuiles,
   prédit −197…−13. Le mécanisme est chirurgical.

   Banc apparié 20 graines × 20 ans (`docs/bench_pax_near.json`) :

   | métrique | delta | t | graines | verdict |
   |---|---|---|---|---|
   | `company_value` | +0,6 % | 0,10 | 8/20 | nul |
   | `performance_history` | +4,7 % | 1,42 | 14/20 | sous le plancher (~12 %) |
   | véhicules | +1,3 % | 0,20 | 9/20 | nul |
   | gares | **+10,5 %** | **4,27** | **17/20** | **établi** — plus de construction |

   Même piège que le vivier : on construit plus, pour la même valeur. Variance
   pire (CV 0,25 → 0,33), minimum 1,70 M → 1,56 M, une graine à emprunt
   résiduel. Graine 42 +64 %, 512 −42 %. ⚠️ **Défaut 0.** `OpexAI[pax_near=1]`
   rallume. Ne pas élargir les bornes (distance, −200) sans banc.

9. 🔴 **Les suites de la tranche v1 du raccordement de gare** (commité, défaut `station_join=0`).
   Le quai parallèle joint au même `StationID` avec sa propre entrée est en place et contourne à
   la fois la question des jonctions et le blocage sur voie unique ; note de conception dans
   `docs/opexai_raccordement_gare.md`. Le banc vivier a dit non ; le banc post-traction aussi
   pour la valeur (§0.2), malgré un effet de construction toujours solide. Cinq suites, dans
   cet ordre :

   1. ✅ **Instrumenter le REFUS de jointure — fait (2026-08-30).** `OpexFindStationJoin` rend
      `{ refuse = M|K|R|N|E }` au lieu de `null`. Panneau `OB|R` (multi / kind / role / other),
      gated comme `OB|J`. 5 graines × 20 ans, `station_join=1`
      (`docs/opex_join_refuse_20y_5seeds.json`) :

      | | M | K | R | other | tentatives | OK | JOINPATH |
      |---|---:|---:|---:|---:|---:|---:|---:|
      | total | **196** | **75** | **0** | 41 | **705** | **39** | **0** |

      La jointure n'est **pas** inerte. La « graine 4096, 5 `too_close_far`, 0 tentative » est
      périmée (165 tentatives / 7 OK ; les far sans tentative sont 1970-72, toutes K).
      **R = 0** : `OpexOriginJoinable` a déjà coupé les rôles fret à la génération.
      ⚠️ **Défaut 0.** Pas un changement de classement.
   2. ✅ **`JOINPATH` : mesuré vide.** 0 / 808 tentatives rail. `OpexJoinPathIsDedicated` ne
      rejette rien sur cet arbre ; les 666 échecs de jointure sont SITEA/SITEB, pas un A\*
      payé puis invalidé. Pas de mémoire à ajouter, pas de contrainte à pousser dans le
      pathfinder. Le rendement site a été mesuré ensuite (parallèle 1–4, 39 → 71 OK) :
      JOINPATH reste 0, le reste est le spread, et ce n'est pas la suite.
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
   4. ✅ **PBS capacité + jointure hors `TracksOverlap`** (2026-08-30). Pas un
      changement de classement. Lignes `trains > 1` : PBS tous les 8 slots dès le
      slot 8, `SIGFAIL` avant les convois. Jointure : approches voie simple
      (gares 2–8, deux côtés du dépôt), jamais la tuile d'aiguillage.
      `CmdBuildSingleSignal` refuse tout `TracksOverlap` (erreur 2050). Pont /
      tunnel → `SJ` skip ; commande refusée → `JF` + rollback. Détecteurs `RX`
      (perte annuelle hors rebut) et `XC` (`CRASH_TRAIN`).
      Capacité 5×20 ans (`docs/opex_capacity_signal_fix_20y_5seeds.json` contre
      `docs/opex_capacity_signal_failures_v2_20y_5seeds.json`) : 33 `SF` au slot
      1 → **148/148**, 0 `SF`, 0 `RX`. Jointure `station_join=1`
      (`docs/opex_junction_signal_fix_20y_5seeds.json` contre
      `docs/opex_station_junction_baseline_20y_5seeds.json`) : 5 PBS / 11 refus
      → **9 / 0**, 3 skip, 0 `JF`, 0 `SIGFAIL`, 0 `XC`. ⚠️ **Défaut
      `station_join` 0.** Ce n'est pas une jonction de voie. Pas de spread.
      🔴 **La commande réussit, la valeur non.** 20 graines × 20 ans contre
      `bench_road_current` (`docs/bench_after_pbs.json`) : −94,9 % / t = −20,9 /
      0/20. PBS bidirectionnels sur voie unique dédiée. Ne pas en faire une
      baseline. Remplacé par la double voie (item 9.5).
   5. ✅ **Double voie v1** (2026-08-30). Deux trains sur une voie se rencontrent.
      `OpexTryDoubleTrack` : quai parallèle, A* avec `ignored_tiles`, dépôt
      propre, un convoi par voie, plafond 2. Échec → un train. Pas de PBS de
      capacité. 5 graines × 20 ans
      (`docs/opex_double_track_20y_5seeds.json`) : **64/92** doubles, 128
      trains, 0 ligne à deux convois sur une voie, 0 `XC` / `RX`, emprunt 0.
      Médiane valeur **5,73 M** (5/5 au-dessus de `opex_town_growth_20y_5seeds`).
      Skip : 17 quai, 9 chemin, 2 voie.
      Banc apparié 20×20 vs `bench_road_current`
      (`docs/bench_double_track.json`) : valeur **+55,5 %**, t = 5,27, 17/20 ;
      note **−9,0 %**, t = −2,32, 8/20 ; véhicules −39 %. **Gardé** ; la note
      s'améliorera plus tard.
      ⚠️ Ce banc est pré-correctif : le premier convoi était démarré dans
      `OpexBuildTrains`, puis arrêté par le second `StartStopVehicle` du commit :
      44/44 lignes restées à un train avaient un profit nul.
      ✅ **Banc corrigé** (`docs/bench_double_track_startfix.json`, 20×20 contre
      `bench_road_current`) : valeur **+125,1 %**, t = **13,31**, **20/20** ; note
      **+17,6 %**, t = **6,05**, 18/20 ; revenu dernière année **+49,2 %**,
      t = **7,61**, 19/20 ; véhicules −34,1 %, t = −8,19 ; gares +1,8 %, nul.
      Emprunt et insolvabilité 0/20. C'est la baseline courante. Son smoke 5×20
      (`docs/opex_double_track_startfix_20y_5seeds.json`) a 35/39 lignes à un train
      profitables, 64/93 doubles, 0 `RX` / `XC` / `SIGFAIL`.

**Priorité de fait, révisée le 2026-08-30 (join H2, rejeu DT)** : H1, H2 et
le rejeu avec double voie **aucun ne paie**. Défauts `station_join` /
`join_max_distance` / `join_place` = 0. Pas de spread, pas de jonction de
voie, `JOINPATH` tient. `MIN_SEPARATION` gelé. L'item 2 reste dernier.

*Priorité précédente, conservée pour la trace* : ~~le rendement join~~ (✅ mesuré,
défaut 0) était la tête. ~~l'item **9.1**~~ (✅) était la tête. ~~le retuning pax
borné~~ / ~~l'item **7**~~ / ~~l'item **4**~~.

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
- ✅🔶 **Le modèle de coût A\*** (`candidates.nut`) : préalable distance ✅, recalibrage conjoint
  ✅ mesuré, **défaut `astar_cost=0`**. 5 graines × 20 ans
  (`docs/opex_attempt_distance_20y_5seeds.json`) : **227/227** tentatives avec distance, 101 OK,
  12 ABND, 111 SITEA/B/AB. **Chiffré d'abord sur 52 succès, puis sur 227 tentatives :**

  | bande | n | P(OK) | P(OK\|A\*) | SITE | ABND | itér. amorties / succès | ratio réel/modèle |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | ≤ 35 | 32 | 0,63 | 1,00 | 12 | 0 | **308** | 0,20 |
  | 35-50 | 59 | 0,49 | 0,94 | 28 | 1 | 1 383 | 0,56 |
  | 50-70 | 30 | 0,77 | 0,82 | 2 | 3 | 5 676 | 0,66 |
  | 70-105 | 43 | 0,42 | 1,00 | 25 | 0 | 9 797 | 0,94 |
  | > 105 | 63 | 0,17 | 0,58 | 44 | **8** | **51 900** | 0,69 |

  Profit réel (1re année) / 1000 itérations des succès : 26 027 / 13 760 / 3 241 / 1 209 / **0**.
  L'optimum est au plus court. 8 des 12 ABND sont au-delà de 105 tuiles et font exploser le
  coût amorti (250 900 itérations de succès, 320 000 d'abandons). Le commentaire 13.4 « lignes
  MOYENNES à 48-63 tuiles » est **retiré** de `candidates.nut`.

  ✅ **Biais de censure : le préalable est fait.** `OB|A` porte la distance. 227/227.

  ✅ **Recalibrage conjoint fait, défaut 0** (2026-08-30). Nœuds v2 = itérations amorties
  (+/−12 tuiles) ; `ATTEMPT_MULTIPLIER` **reste 4** (p95/amort ≤ 2,7). Réglage `astar_cost`.

  5 graines × 20 ans (`docs/opex_astar_cost1_20y_5seeds.json`) : 13–20 lignes, médiane 51→47
  tuiles, tentatives 227→149, ABND 12→7. Le piège « budgets 50–400, zéro ligne » est évité.

  **Banc apparié 20 graines post-traction 20 ans** (`docs/bench_astar_cost.json`) :
  - `company_value` : −8,9 % (t = −1,86, 7/20)
  - `gares` : −7,9 % (t = −3,23, 4/20)

  **Ré-évaluation sur architecture continue (2026-08-31, `docs/bench_astar_cost_5y.json`, 20 graines × 5 ans)** :
  
  | métrique | Contrôle (`astar_cost=0`) | Traitement (`astar_cost=1`) | Delta | t | Graines | Verdict |
  |---|---|---|---|---|---|---|
  | `company_value` | 536 000 £ | 522 500 £ | −2,52 % | −0,73 | 8/20 | Défavorable à astar_cost=1 |
  | `profit` (dernier trim.) | 44 800 £ | 42 770 £ | −4,75 % | −0,80 | 9/20 | Défavorable à astar_cost=1 |
  | `profit_year` (annuel) | 174 200 £ | 172 080 £ | −1,23 % | −0,38 | 10/20 | Défavorable à astar_cost=1 |
  | `performance_history` | 260,2 | 261,8 | +0,61 % | +0,21 | 13/20 | Neutre |

  **Conclusion** : Même avec le précalcul continu et la boucle sans sleep, `astar_cost=1` (table v2) sur-pénalise inutilement les corridors à moyenne/longue distance au ranking annuel, retardant la construction de lignes très rentables.
  ⚠️ **Défaut `astar_cost=0` STRICTEMENT MAINTENU.**
- ✅ **Constantes HYPOTHÈSE `SPEED_EFFICIENCY_PCT = 70` et `WAGONS_PER_TRAIN = 5`** : remplacées
  le 2026-08-29 par la traction dimensionnée (`4a8e15e`). Rendement réel mesuré le 2026-08-30
  (§4.3) : 0,96 vs catalogue, 1,18 vs traction — le 70 % était trop pessimiste, pas de
  retuning.
- ✅ **`ROAD_SPEED_EFFICIENCY_PCT = 60` : mesuré, pas retuné** (2026-08-30). Panneau `RY`,
  5 graines × 20 ans (`docs/opex_road_speed_yield_20y_5seeds.json`,
  `docs/opex_road_speed_yield.json`). n = **53** ligne-années en marche (6 lignes,
  0 sur 12345). Fret **1,00** vs catalogue, pax **0,75**. Réel / 60 % :
  **1,27** pax, **1,71** fret. Instantané, pas un temps de trajet. Le 60 % est
  pessimiste en croisière, comme le 70 % rail. ⚠️ **Pas de retuning.** Ce n'est
  pas le 3,91 pax (`TOWN_CATCHMENT_SHARE_PCT`). `docs/opexai_route.md`.
- ✅ **Accélération route 15.3** (2026-08-30). Wiki 37 km-ish/h/jour =
  `AM_ORIGINAL` (`DoUpdateSpeed(256)`, une fois/tick, unité 0,5).
  `vehicle.roadveh_acceleration_model` défaut **1 = réaliste**, absent du
  CFG. Virage d'axe : plafond 3/4. Le 0,75 pax de `RY` est ce plafond sur
  le L, pas un retuning. Pas de modèle de traction route.

---

## 4. Mesures dans le jeu plutôt qu'à citer — closes

Reprend le §8 de `docs/mecanique_jeu.md`, complété. Les six points sont clos.
Le 4 est relu en 15.3 : inchangé.

1. ✅ Le réglage `plane_speed` réellement actif : `4`, le défaut, non surchargé — vérifié dans
   l'`openttdlab.cfg` d'un run `OpexAI` réel du 2026-08-28, pas supposé.
2. ✅ Économie « lisse » (`economy.type = 1` = `ET_SMOOTH`) et **barème de
   production 15.3** (2026-08-30). `ChangeIndustryProduction` : 1/22 par mois,
   seuils 153/204 (≈ 60 / 80 %), table wiki 0/33/67/83 **confirmée**. La note
   de gare n'est pas un terme. Recessions : `difficulty.economy`, autre
   réglage. ⚠️ Pas de facteur « service composé » au classement.
3. ✅ **Rendement de vitesse effectif** (2026-08-30). Panneau `RV`, 5 graines × 20 ans
   (`docs/opex_speed_yield_20y_5seeds.json`, `docs/opex_speed_yield.json`). Instantané
   annuel des trains **en marche** (vitesse > 0) : n = **832** ligne-années.
   Médiane réelle **155** contre catalogue **160** (rapport **0,96**) et contre la
   traction **123** (rapport **1,18**). 20 % des instantanés ont une médiane ≤ 61
   (le plafond d'angle droit existe) ; 53 % sont ≥ 150. L'ancien `SPEED_EFFICIENCY_PCT
   = 70` était trop pessimiste. ⚠️ **Pas de retuning.** Ne pas réintroduire un
   abattement forfaitaire ni inventer une fraction de virages. La route est
   mesurée à part (`RY`, 60 % mesuré, pas retuné).
4. ✅ **Courbe de note de gare, relue en 15.3** (2026-08-30). Tag OpenTTD 15.3 :
   `UpdateStationRating` (`station_cmd.cpp`), `INITIAL_STATION_RATING = 175`
   (`station_base.h`), `Ticks::STATION_RATING_TICKS = 185` /
   `DAY_TICKS = 74` (`timer_game_tick.h`). Inchangée vs 13.4. Départ 175/255,
   cycle 2,5 jours, `Clamp(±2)` une fois `HasRating()`. ~2 mois pour 50
   points. Détail : `docs/mecanique_jeu.md` §8.4. ⚠️ **Pas de retuning** de
   `STATION_RATING_PCT = 50`.
5. ✅ **Barème croissance de ville / gares actives** (2026-08-30). Lu dans OpenTTD 15.3
   (`GetNormalGrowthRate` / `CountActiveStations`, plus `UpdateTownGrowth`). Table
   normale 320/420/300/220/160/100, chez nous `town_growth_rate = 2` → **160/210/150/110/80/50**,
   n = 0 bloque 11/12 du temps. Mesure `TV`, 5 graines
   (`docs/opex_town_growth_20y_5seeds.json`) : les desservies n'estagnent pas comme classe
   (graine 42 ×2,64 malgré la dilution). L'item 2 reste dernier.
6. ✅ **Sonde de catalogue 1950-2000** (2026-08-30). `CatalogProbe`, `starting_year = 1950`,
   51 ans, graine 42, OpenTTD 15.3 / OpenGFX 7.1 (`docs/catalogue_churn_1950_2000.json`,
   harnais `sweeps/opex_catalog_probe.py`). La sonde 1970-1989 reste
   `docs/catalogue_churn.json`.

   Dates d'introduction (vanilla) :

   | | année |
   |---|---:|
   | rail électrique + locos | **1967** |
   | monorail | **2000** |
   | maglev | pas encore en 2000 |
   | aéroport SMALL | 1950 (plus valide dès 1960) |
   | LARGE | 1955 |
   | HELIPORT | 1963 |
   | HELIDEPOT | 1976 |
   | METROPOLITAN / HELISTATION | 1980 |
   | COMMUTER | 1983 |
   | INTERNATIONAL | **1990** |
   | INTERCON | pas encore en 2000 |

   Parc moteurs 1950 → 2000 : rail 14→33, route 11→17, eau 3→4, air 3→19.

   **Conséquence.** Une campagne 1970-1989 **a déjà l'électrique** (1967) ; elle ne
   voit ni INTERNATIONAL ni monorail. L'item « on rate l'électrification » était
   faux pour le départ 1970. `catalog.nut` prend le **dernier** type de rail
   disponible : en 1970 c'est ELECTRIC (voulu) ; en 2000 ce serait MONO, et toutes
   les lignes neuves basculeraient — hors de nos 20 ans. Ne pas allonger une
   campagne au-delà de 1999 sans figer le type de rail.

---

## 5. Banc

- ✅ **Banc multi-graines construit et exécuté (2026-08-29)** — `sweeps/bench_v2.py`,
  résultats dans `docs/bench_v2.json` : 20 graines × 20 ans, OpexAI et AAAHogEx (campagne
  interrompue volontairement avant AdmiralAI et trAIns, jugées obsolètes). Le script apporte la
  notion d'**arm** (une IA OU une variante paramétrée d'OpexAI via `ai_params`, ex.
  `OpexAI[pathfinder_sleep_ticks=1]`), le nettoyage des sauvegardes, un checkpoint `.jsonl`, les
  stats de dispersion et les **comparaisons appariées par graine**. Les deux items ci-dessous
  (20 ans, 20 graines) sont absorbés par lui. Indicateurs de succès : `company_value`,
  `performance_history` (score 0-1000, pas le profit ni la note de gare), **profit** du
  trimestre et de l'année (`income`+`expenses`), **note de gare** médiane (`STNN`, 0-255).

  | arm | company_value | CV | SE | note | CV |
  |---|---:|---:|---:|---:|---:|
  | OpexAI *(arbre courant, `bench_double_track_startfix`, 2026-08-30)* | **7 034 590** | **24,7 %** | 5,5 % | **623** | 12,2 % |
  | OpexAI *(route, `bench_road_current`)* | 3 125 439 | 22,3 % | 5,0 % | 530 | 12,0 % |
  | OpexAI *(re-baseliné le 2026-08-29, `bench_v2`)* | 2 409 531 | 48,8 % | 10,9 % | 396 | 27,6 % |
  | OpexAI *(mesure d'origine, archivée)* | 2 527 171 | 32,6 % | 7,30 % | 408 | 20,4 % |
  | AAAHogEx | 225 430 986 | 16,2 % | 3,62 % | 897 | 0,5 % |

  ✅ **Référence de l'arbre : `docs/bench_double_track_startfix.json`.** Apparié
  20×20 contre `bench_road_current` : `company_value` **+125,1 %**, t = **13,31**,
  **20/20** ; `performance_history` **+17,6 %**, t = **6,05**, 18/20 ; revenu
  dernière année **+49,2 %**, t = **7,61**, 19/20 ; véhicules **−34,1 %**, t =
  **−8,19**, 0/20. Emprunt / insolvabilité 0 / 0. La double voie est gardée ;
  `docs/bench_double_track.json` reste le bras pré-correctif. `docs/bench_v2.json` et
  `docs/opexai_plafonnement_mesure.json` restent historiques.

  ✅ **Contrat rail 1--2 trains aligne (2026-08-31).** Le modele ne cote plus 3--8
  rames que le constructeur ne peut pas poser; `rail_cost_probe` confirme 62/97
  sur-evaluations de flotte avant correction. Banc apparié 20x20
  `bench_rail_cap2.json` : valeur +3,6 % (t=0,97), profit annuel +0,6 % (t=0,18),
  note +0,5 % (t=0,23), note de gare +2,1 % (t=1,10), sans emprunt ni insolvabilité.
  Tous sous le plancher de détection : correctif gardé pour la cohérence, mais baseline
  inchangée (`bench_double_track_startfix`).

  🔴 **HEAD + PBS (`e027037`) n'est pas une baseline.** 20 graines contre
  `bench_road_current` (`docs/bench_after_pbs.json`) : `company_value` **−94,9 %**,
  t = **−20,9**, **0/20** ; `performance_history` **−77,7 %**, t = **−25,0**.
  9 graines à `company_value=1`, 20/20 encore empruntées, 5 insolvables, 0 erreur
  de script. Les campagnes 5 graines « 148/148, 0 SF » mesuraient la commande,
  pas la valeur (graine 42 : 3,24 M → **1**). Ne pas fusionner ça dans `bench_v2`.

  ⚠️ Les deux lignes OpexAI *de 2026-08-29* mesurent le **même comportement** sur les **mêmes
  graines** : seul le profil d'opcodes diffère (§8). L'écart entre elles n'est pas significatif
  en lecture appariée (t = −0,60) — mais il chiffre le **bruit de trajectoire irréductible**, et
  c'est lui qui fixe le plancher de détection du banc : **~15 % sur `company_value`, ~12 % sur
  `performance_history`**. `bench_road_current` n'est plus ce comportement (route, traction,
  bassin 86). `bench_after_pbs` non plus.

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

---

## 6. Modes de transport, dans l'ordre décidé

1. ✅ **Rail** — étage 3 ci-dessus.
2. ✅ **Avion** — une liaison passagers entre deux grandes villes, validée sous OpenTTD 15.3.
   Aucun pathfinding ; son avantage n'est toutefois **pas** la vitesse : il vole au quart de sa
   vitesse affichée.
3. ✅ **Bateau** — une liaison passagers entre deux grandes villes côtières, avec validation
   bornée du graphe d'eau et dépôt construit sur la même composante. Voir
   `docs/opexai_multimodal.md`.
4. ✅ **Route** — adoptée le 2026-08-29, `road_mode` défaut 1. Ce n'est plus la liaison bus
   unique désactivée du 2026-08-28 (notes −1, `ROAD_BUILD_ENABLED = false`) : c'est une phase
   annuelle, bus et **camions**, bande 5–25 tuiles. Banc apparié : `performance_history` **+9,3 %**,
   t = 2,03, 16/20. SITE, TRACEX, classement et multistop sont mesurés (défauts inchangés sauf
   le mode lui-même). Détail : **`docs/opexai_route.md`** et §1 bis ci-dessus.

Ne pas oublier deux composantes gratuites de la note de compagnie : **emprunt à zéro** (5 %) et
**8 types de cargo par trimestre** (5 %) — cette dernière plaide contre une IA 100 % passagers.

---

## 7. Reprises de l'ère `TrainLineAI` encore ouvertes

- **La reprise sur préfixe façon `RetryToBuild`**, en clean-room.
  Les **64 `TRKFAIL` / ~145 M** (453 par itération contre 156) sont **TrainLineAI 13.4**,
  campagne v3 une ligne par compagnie (2026-08-28), pas OpexAI 15.3. Sur l'arbre
  courant, 5 graines × 20 ans : **2/173** (`docs/opex_road_multistop_20y_5seeds.json`),
  **2/175** (TRACEX), **3/227** (distance). `abandon_memory` ne retient que `ABND` :
  graine 4096, 1988, deux tentatives à 69 tuiles (10 000 puis 27 950 itérations).
  Ce n'est plus le meilleur rendement identifié. Ne pas copier AAAHogEx pour deux
  échecs par campagne.
- ✅ **La politique d'abandon** : la forme fermée coupe une recherche lorsque son rendement
  marginal attendu passe sous le rapport du meilleur candidat non essayé. Le trou du dernier rang
  (absence de suivant = budget maximal) est corrigé : son alternative est `MIN_RATIO`, rapport
  minimal déjà acceptable au prochain classement annuel, pas une constante nouvelle. Campagne
  instrumentée graine 42/20 ans : 5 derniers candidats passaient auparavant par le chemin zéro,
  mais 0 tentative ABND ; le vieux ABND à 60 000, antérieur à l'instrumentation, ne peut donc pas
  être attribué rétrospectivement à ce chemin plutôt qu'au plafond. Détail dans
  `docs/opexai_croissance.md` §6.

---

## 0 sexies. 🔴 REVUE DU CONTRÔLEUR (2026-09-01) — la cause du goulot est trouvée

Revue de code ciblée sur `Start()`, `_runNextTask()` et la file de tâches, motivée par le banc 1v1
(61,2 % des mois avec ≥300 k£ et aucune construction). **Les deux trouvailles de tête sont
vérifiées à la main**, pas seulement rapportées.

### 1. 🔴 La boucle principale abandonne l'essentiel du budget d'opcodes (`main.nut:3143`)

```
while (true) { this._processEvents(); this._runNextTask(); AIController.Sleep(1); }
```

**Une seule tâche par tick, puis `Sleep(1)`.** Le budget est de 10 000 opcodes par tick et il n'est
**pas reportable**. Un tick qui tire `catalog` hors de son mois, `report` hors de son année,
`repay` hors de son mois, ou `air_fleet` sans rien à faire, dépense quelques centaines d'opcodes
puis jette les ~9 700 restants. `_runNextTask()` **retourne déjà un booléen** « j'ai fait un travail
utile » — et `Start()` l'ignore.

Sur 3 ans ≈ 81 000 ticks ≈ 810 M d'opcodes, c'est le gisement dont AAAHogEx tire ~150 gares.
**C'est l'explication la plus simple et la plus complète du « 8× moins de gares ».**
Correctif : `while (this._runNextTask()) {}`, ou boucler tant que `GetOpsTillSuspend()` reste haut,
et ne `Sleep(1)` que si la file n'a rien d'utile.

### 2. 🔴 Cinq fonctions ne sont JAMAIS appelées, dont le mécanisme qui aurait sauvé le point 1

Vérifié par recherche exhaustive : aucun site d'appel pour
`_tryBuild` (~400 lignes, tout le chemin rail), `_tryBuildRoads`, `_tryBuildWater`,
`_tryPreplan`, `_tryProbeNegative`. Seuls `_tryBuildAir`, `_tryBuildProjects` et `_tryTownGrowth`
sont dispatchés par `_runNextTask`.

⚠️ **Nuance à ne pas rater** : rail, route et eau sont désormais construits par le portefeuille
(`_tryBuildProjects` → `projects.nut`), donc ces quatre-là sont du code **supplanté**, pas un trou
fonctionnel. Le cinquième, si.

🔴 **`_tryPreplan` est le trou fonctionnel.** Il est documenté comme « précalcule le tracé pendant
les ticks d'opcodes dormants » — exactement le remède au point 1 — et son réglage
`preplan_queue` a pour **défaut 1**. Sa seule utilisation (`main.nut:964`) est à l'intérieur de la
fonction morte : **le réglage est totalement inerte**, il ment sur ce qui tourne.

**Ceci corrige la conclusion de l'étape 1 de la revue** (`info.nut` déclaré sain) : les 31 réglages
sont bien déclarés, lus et cohérents, mais vérifier qu'un réglage est *lu* ne prouve pas que le code
qui l'*utilise* est atteignable. `preplan_queue` est le seul dans ce cas sur les 31 — vérifié un par
un.

### Les autres trouvailles, par gravité

| # | lieu | problème |
|---|---|---|
| 3 | `main.nut:536`/`:550` | `_tryBuildAir` dimensionne les plans sur `maxCapital` mais les accepte sur `capital + reserve + marge` (30 000 £ pour deux aéroports). Tout plan tombant dans cette bande de 28 k£ est **retrouvé puis rejeté à chaque cycle, indéfiniment** : argent présent, rien construit, budget brûlé. |
| 4 | `main.nut:512`/`:521` | La tâche `air` n'a **aucune barrière de cadence** (contrairement à `catalog`, `report`, `repay`) et relance un scan complet `OpexAirPlans` à chaque cycle, jusqu'à 12 fois par invocation — alors que `OpexBuildProjects` fait déjà le même scan mensuellement. |
| 5 | `main.nut:565` | `_tryBuildAir` n'écrit ni ne lit `_abandonedPairs` : une paire qui échoue est replanifiée et retentée **tout le reste de la partie**. Le chemin portefeuille, lui, mémorise. |
| 6 | `main.nut:869` | `_tryTownGrowth` tourne à chaque cycle sans barrière et **précisément quand il y a du cash** (`money < reserve + 25000` en garde). Il paie un plan routier complet par ville servie, sans mémoïsation ni cooldown ; le test `money < need` arrive **après** que le plan a été payé. |
| 7 | `main.nut:3031` | Interblocage latent : `task.dueCycle = this._taskCycle` (au lieu de `+1`) quand `_projects` est null. `_taskCycle` ne peut alors plus avancer et `catalog`, différé à `+1`, ne tourne plus jamais. Inatteignable aujourd'hui, mais un seul `return` ajouté dans `OpexBuildProjects` gèle l'IA. |
| 8 | `main.nut:3045` | `air` précède `projects` et peut consommer le capital **et le plafond d'emprunt** que le sac à dos avait alloués aux autres modes ; le dispatch retourne `true` quoi qu'il arrive. |
| 9 | `main.nut:2937` | `line.lastExpansionYear` est **écrit et jamais lu** — le commentaire promet « au plus UNE expansion par an », rien ne l'applique. Même famille que `MAX_ROAD_VEHICLES` et `_resizeAirFleets`. |
| 10 | `main.nut:514` | La garde air teste `airCombos == null && airport == null`, mais `airCombos` vaut toujours `[]` après `_refreshAir()` : la garde ne peut jamais se déclencher sur « aucun avion disponible ». Et le seul état qu'elle laisse passer fait déréférencer `airCombos.len()` sur null en `:543`, ce qui **tue l'IA**. |
| 11 | `main.nut:290` | `_lastAirFleetMonth` déclaré, initialisé, **jamais lu ni écrit** : `air_fleet` n'a pas de barrière de cadence. |
| 13 | `main.nut:1723` | Télémétrie fausse : `rankPacked = i * TOP_K + this._projects.best.len()` mélange l'indice et la **longueur** du portefeuille — toute analyse qui dépaquette `rankPacked % TOP_K` comme un rang lit la taille de la liste. |

### Ordre d'attaque proposé

1 (budget d'opcodes) et 2 (`_tryPreplan`) d'abord : ils visent directement les ~85 % de l'écart qui
viennent du volume. Puis 3, 4, 6 — trois boucles qui brûlent du budget sans construire, exactement
le profil « cash présent, rien de bâti ». 10 est un risque de mort de l'IA à traiter au passage.

⚠️ Aucun de ces points n'est encore corrigé ni mesuré. **Ne pas supposer un gain avant le banc** :
la seule chose établie ici est le mécanisme, pas son effet.

---

## 0 septies. 🔴 REVUE DU PORTEFEUILLE `projects.nut` (2026-09-01) — les 4 soupçons confirmés

Étape 3 de la revue. Rappel de contexte : `_tryBuild` / `_tryBuildRoads` / `_tryBuildWater` de
`main.nut` étant du **code mort vérifié** (§0 sexies), `OpexBuildProjects` est le SEUL chemin de
construction vivant pour rail, route et eau. Ce fichier porte donc presque toute la décision
d'investissement.

### Les deux qui expliquent la mesure

🔴 **A. Le capital dort jusqu'à la fin du mois** (`main.nut:3018` + `projects.nut:335`).
Le portefeuille n'est régénéré qu'au **changement de mois** ou après une construction **réussie**,
et `capitalBudget` est figé au moment de la génération. Si le mois s'ouvre à 60 k£ et qu'aucun
projet ne rentre, `bestSolution = []`, `best.len() == 0`, et `_tryBuildProjects` sort dès sa
première ligne — **pour tout le reste du mois**, même si la trésorerie monte ensuite à 400 k£.
➜ C'est exactement la mesure « **4,15 mois en moyenne avec ≥100 k£ et aucune croissance** ».

🔴 **B. Un sac à dos entier est calculé, puis jeté sauf un item** (`projects.nut:264` +
`main.nut:1503`). `maxBatch = 1` : un seul projet est construit, puis le portefeuille est
régénéré de zéro. Seul compte donc *quel projet unique arrive en tête de `byOpcodes`* — mais il a
d'abord dû être admis par un empaquetage dont l'objectif est le **revenu total**.
Échec concret : à `capitalBudget` = 300 k£, le solveur préfère {A 100k/rev20k, B 100k/rev20k,
C 100k/rev20k} = 60k à {D 280k/rev55k} = 55k. **D est finançable, meilleur, et jamais construit** —
et ça se rejoue à chaque régénération. La forme correcte ici n'est pas un sac à dos, c'est
« prendre le meilleur projet finançable ».

### Les 4 soupçons, tous CONFIRMÉS

| # | lieu | confirmation |
|---|---|---|
| 1 | `projects.nut:137` | Le vainqueur par couple O/D est élu **avant** toute consultation de `capitalBudget` (calculé :288, utilisé :335). `OpexProjectModeBetter` classe sur `roi`, un **ratio** : une ligne rail à 900 k£ (roi 180) bat une route à 45 k£ (roi 170), puis échoue au test de capital — **le couple ne rapporte alors rien**. Les clés se collisionnent bien entre modes, donc la perte est réelle. |
| 2 | `projects.nut:199`/`:219` | L'objectif est `currentRevenue`, la borne (:179) somme `revenueAnnual`. **`profitAnnual` n'apparaît nulle part** dans l'objectif — seulement comme portillon `> 0`. Un projet à 120k de revenu / 2k de profit **domine** un projet à 60k de revenu / 45k de profit. |
| 3 | `projects.nut:70` (`:95`, `:116`) | `budgetScore = revenu / 1000 £ de capital`, pas profit. C'est la clé primaire d'insertion (:332), **75 % du poids de tri** du sac à dos (:240), et la valeur imprimée dans le panneau `IP|` : **tout chiffre d'investissement montré à l'opérateur est un chiffre d'affaires.** |
| 4 | `projects.nut:213` | Interdit à deux projets financés de partager **l'une ou l'autre** extrémité — donc interdit exactement la topologie en étoile que `builder_air.nut:415-470` s'échine à produire (tous les plans hub réutilisent `hub.town.tile` en `siteA`). Et comme `maxBatch = 1`, cette contrainte **n'apporte rigoureusement rien** tout en faussant quel projet unique sort premier. |

### Le reste

| gravité | lieu | problème |
|---|---|---|
| MOYEN | `:248` | `PROJECT_POOL_K = 128` remplit le vivier, puis `if (n > 64) n = 64` rend les candidats 65→128 **invisibles au solveur** — pendant que `stats.budgetConsidered` rapporte 128. Les 64 slots en trop coûtent des opcodes et n'achètent rien. |
| MOYEN | `:240` | Le tri composite `budgetScore * 75 + opcodeScore * 25` mélange **des unités incommensurables** (revenu/1000 £ contre revenu/1000 opcodes). Sur un projet à 20 k£, `budgetScore` écrase la somme ; sur un projet à 500 k£ les deux termes sont comparables. La pondération réelle **varie avec le coût du projet**, et elle décide de l'ordre de branchement du B&B. |
| MOYEN | `:57` | Commentaire mensonger + erreur d'unité : la route ajoute `candidate.iterations * PROJECT_RAIL_OPS_PER_ITERATION`, alors que `OpexRoadIterations` **n'est pas un compte d'itérations d'A\* rail**. Dimensionnellement faux, et double-compte une planification que le commentaire dit déjà mesurée. `opcodeScore` route sous-estimé. |
| MOYEN | `:212`+`:335` | `ROAD_MAX_NEW_LINES_PER_YEAR = 36` est un **plafond annuel inerte** : le compteur est local à une résolution et se réinitialise à chaque régénération, donc il ne peut jamais atteindre 36 ni contraindre quoi que ce soit. Même famille que `MAX_ROAD_VEHICLES` et `lastExpansionYear`. |
| MOYEN | `:313` | `knapsackNodes`, `knapsackExact`, `budgetRejected`, `modeAlternatives`, `modeReplaced` et `capitalRemaining` sont **écrits et lus nulle part**. Or `maxNodes = 2000` pour `n = 64` fait tronquer la recherche **couramment** : impossible de distinguer « le solveur a prouvé l'optimum » de « le solveur a épuisé son budget de nœuds ». ➜ *C'est cet angle mort qui a permis aux soupçons 1 à 4 de survivre aussi longtemps.* |
| FAIBLE | `:39` | Double division entière (`cost / 1000` puis `value / thousands`) : 14 900 £ et 14 100 £ donnent le même score. Les égalités fabriquées sont départagées par `revenueAnnual` brut — ce qui **renforce** les points 2 et 3. |
| FAIBLE | `:323`/`:326` | `airOps` (une mesure couvrant TOUT le balayage `OpexAirPlans`) est attribué à **chaque** plan comme `planningOpcodes` : surestimation d'un facteur N. Télémétrie seulement, mais ça corrompt la mesure même qui servirait à pricer la découverte aérienne. |
| FAIBLE | `budget.nut:27` | La non-réentrance documentée **n'a aucun détecteur** : `begin()` écrase sans condition, `end()` retourne 0 en silence. ~40 sites d'appel. `OpexBuildProjects` n'est sûr que parce que `OpexAirPlans`/`OpexWaterPlans` ne reçoivent pas `budget` — un accident de signature, pas un invariant. |

### ✅ Vérifié comme n'étant PAS des bugs — ne pas re-litiger à la passe de correction

Le comparateur `:239` ne capture aucune locale (le piège des closures Squirrel ne s'applique pas
ici) ; le backtracking de `originsUsed` est correct ; `OpexProjectInsert` est correct ; les marges
de capital ne sont **pas** double-comptées (le sac à dos exige `capital + marge ≤ cash − réserve`,
soit exactement le `need` de `main.nut`) ; la borne qui ignore `maxRoad`/`maxItems`/`originsUsed`
est une relaxation valide ; les trois formes de plan air portent bien `siteA.town.tile`, donc
`:110-111` ne peut pas déréférencer null ; `plan.capital` et `plan.economics.capital` coïncident.

### Ordre de correction proposé

**A et B d'abord** (remplacer le sac à dos par « meilleur projet finançable » + régénérer le
portefeuille à la demande plutôt qu'au mois) : ils visent le capital dormant. Puis **1, 2, 3**
(différer l'élection modale après le test de capital, et passer l'objectif et `budgetScore` au
`profitAnnual`). **4 tombe gratuitement** une fois B fait.

⚠️ Rien n'est corrigé ni mesuré. Le mécanisme est établi, pas son effet.

---

## 0 octies. 🔴 REVUE DE `economy.nut` (étape 4, 2026-09-01) — le rendement unitaire

Le banc dit que ~15 % de l'écart de profit vient du **rendement par véhicule** (6 332 £/an par
véhicule net ajouté contre 9 229 £, soit **−31,4 %**) et qu'OpexAI met **3,26 véhicules par gare
contre 2,71**. Ce fichier porte ce rendement. **Les trois trouvailles de tête sont vérifiées à la
main.**

### 🔴 1. La variante « 2 trains » est facturée SANS la voie qu'elle exige (`economy.nut:193`)

`infraCost` est calculé **une seule fois, ligne 193, avant la boucle**, puis réutilisé identique
pour `trains = 1` et `trains = 2` (lignes 204 `amortAnnual` et 207 `capital`). Or la variante à
deux trains est une **seconde voie dédiée** : `builder_rail.nut:1257` facture réellement
`tiles2.len() * costTrackPerTile + (planA2.length + planB2.length) * costStation + depotCost`,
soit approximativement une seconde copie de toute la ligne.

Le deuxième train est donc pricé au seul `loco.price + wagons * wagon.price` plus un
`loco.runningCost`. Comme le revenu est croissant en `trains` (palier de note franchi, capacité
doublée), la boucle **choisit 2 trains sur pratiquement toute ligne viable**, alors que le capital
réel est le double de ce que `capital` rapporte.
➜ **C'est le mécanisme direct des 3,26 véhicules par gare.** L'erreur vaut 100 % de `infraCost`,
très au-dessus du plancher de détection.

### 🔴 2. Le nombre de trains maximise le profit ABSOLU, le portefeuille classe au ROI (`:209`)

`if (best == null || profitAnnual > best.profitAnnual)` ne consulte **jamais** `roi` ni `capital`.
Or c'est `roi` que le sac à dos de `projects.nut` trie. Ajouter un train augmente presque toujours
`profitAnnual` **et baisse `roi`** : le modèle livre donc au portefeuille, pour chaque ligne, la
variante **la plus gourmande en capital** de toutes celles qu'il a évaluées. Se compose avec le
point 1.

### 🔴 3. Les seuils de note de ramassage contredisent le source du moteur (`:90-95`)

`docs/mecanique_jeu.md` §8.4 enregistre la lecture du source 15.3 :
`time_since_pickup ≤ 3 / 6 / 12 / 21` **cycles**, à ~2,5 jours le cycle → **7,5 / 15 / 30 / 52,5
jours**. Le code utilise **6,8 / 13,5 / 27 / 47** : chaque palier est **~10 % trop strict**.

Le plus coûteux : `TARGET_HEADWAY_DAYS = 7` tombe **entre 6,8 et 7,5**. Le modèle note donc sa
propre cible de conception à **95 points quand le moteur en accorde 130**.

**Conséquence en cascade sur `:99`** : `otherPoints = 127,5 − 95 = +32,5` suppose que les lignes de
calibration étaient dans la tranche 95. Sous le seuil corrigé, un headway de 7 jours est dans la
tranche **130**, donc `otherPoints = −2,5`. Toute la courbe bascule : 65,7 / 50 / 32,4 / 22,5 %
deviendrait 50 / 36,3 / 18,6 / 8,8 %. Ça change la valeur marginale d'un train **et** le revenu
absolu de tout candidat rail et air. ⚠️ La décomposition utilise le headway *cible* des lignes de
calibration, jamais leur `roundTripDays / trains` mesuré — à refaire proprement avant de corriger.

### Le reste

| gravité | lieu | problème |
|---|---|---|
| HAUT | `:370`, `:376` | La flotte routière est fixée par une cible de fréquence **sans aucun test de profit marginal**, et le commentaire qui la justifie est faux sur **toute** la plage légale : il affirme « sur une ligne courte la contrainte de fréquence rend presque toujours 1 », or entre `ROAD_MIN_DISTANCE = 5` et `ROAD_MAX_DISTANCE = 25` le terme vaut **2 à 6**, jamais 1 — et `max()` en fait un plancher. `builder_road.nut:735` clone ensuite jusqu'à `candidate.trains`. **Toute ligne routière naît sur-dotée.** |
| MOYEN/HAUT | `:363` | La route n'applique **jamais** `OpexStationRatingForHeadway`, que le rail (`:199`) et l'air (`builder_air.nut:175`) utilisent : elle est figée à 50 % à plat. Une ligne de bus courte et fréquente — exactement ce que le mode route construit — vaudrait 65,7 % sous la courbe du modèle lui-même. **Le même mécanisme physique est pricé 31 % moins cher pour la route que pour le rail**, et le sac à dos multimodal les compare sur ce nombre. |
| MOYEN | `:148` vs `:199` | La rame est dimensionnée sur `STATION_RATING_PCT = 50` à plat, mais la demande dans la boucle utilise la courbe (22,5–65,7 %). Sur une ligne longue à un train : ~54 % de wagons de trop par rapport à la demande estimée par le modèle lui-même, donc quai plus long et capital gonflé. Sur une ligne courte à deux trains, l'inverse. |
| MOYEN | `:205` vs `:270` | **Les deux modèles rail se contredisent sur le coût d'entretien des wagons** : `runningAnnual = trains * loco.runningCost` l'ignore, `OpexRailFixedConsist` renvoie `wagonRunningAnnual` que `main.nut:2646` soustrait. L'un des deux a tort. Si les wagons ne coûtent rien, `OpexRailFixedConsist` surcharge chaque wagon marginal et **étouffe silencieusement `_expandRailLines`**. Trancher en lisant `AIEngine.GetRunningCost` sur un vrai wagon. |
| MOYEN | `:204` vs `:404` | Horizons d'amortissement **asymétriques par mode** : rail `vehicleCost/20`, route `vehicleCost/12`, infra /30 des deux côtés. Le capital rail est dominé par l'infra, celui de la route par les véhicules → la route paie ~2,5× l'amortissement annuel par livre de capital. Et `roi` redivise ensuite par `capital` : **le capital est pénalisé deux fois, à un taux dépendant du mode**. Le moteur ne débite rien de tel — c'est une convention de classement, elle doit au minimum être neutre entre modes. |
| MOYEN | `:193` | `infraCost` rail **omet le dépôt**, que la route compte (`:401`) et que `builder_rail.nut:467` et `:1256` paient réellement (deux fois sur le chemin 2 trains). Sous-estime le capital rail et gonfle son `roi` face à la route. |
| MOYEN | `:328` | `ROAD_SPEED_EFFICIENCY_PCT = 60` est justifié **contre une constante rail qui n'existe plus** (les 70 % du rail, remplacés par un vrai modèle de traction). La route est désormais le seul mode portant un abattement forfaitaire non calibré, et sa base de comparaison a disparu. Le document pointe 0,75 (plafond de virage 3/4, `RY` 66/88). ⚠️ `mecanique_jeu.md:159` dit explicitement « pas de retuning du 60 % » : **justification périmée à trancher, pas changement automatique**. |
| FAIBLE/MOYEN | `:193` | Le coût de voie rail est pricé en distance **de Manhattan**, alors que la voie posée est le résultat de l'A\*, toujours ≥ Manhattan (déviations, ponts, Z). Erre en notre faveur. La route documente sa propre approximation, en sens inverse ; le rail non. |
| FAIBLE | `:208`, `:408` | Tout candidat déficitaire est écrasé à `roi = 0` : une ligne à −200 £/an et une à −200 000 £/an sont indiscernables, donc rien en aval ne peut les ordonner ni les diagnostiquer. Division entière également quantifiante. Même forme que le défaut trouvé dans `projects.nut`. |

### ✅ Vérifié comme n'étant PAS un bug — ne pas re-litiger

Asymétrie pax/fret de `OpexLoadedTripsPerMonth` (conforme à `mecanique_jeu.md` §1 ter, et
dimensionnellement cohérente des deux côtés) ; retrait du `ceil` favorable ; `0.036 * speed` comme
tuiles/jour ; `headwayDays = roundTripDays / trains` ; `OpexCeilDiv` (pas d'erreur de bord) ;
`incomeDays` conservateur ; le `>` strict qui garde bien la flotte la plus petite à égalité ;
`MARGINAL_FLEET` lu après `require` (résolution à l'appel, pas à la compilation) ; absence de charge
`infrastructure_maintenance` (le réglage est bien `false` au banc) ; budget d'opcodes (la seule
boucle est bornée à `MAX_RAIL_TRAINS = 2`) ; pas de closure imbriquée ni d'`AIAccounting` ici ;
`roi` mis à l'échelle par 1000 sans risque de débordement (Squirrel 64 bits).

⚠️ Rien n'est corrigé ni mesuré. Le mécanisme est établi, pas son effet.

---

## 0 nonies. 🔴 REVUE FLOTTE ET ENTRETIEN (étape 5, 2026-09-01)

Périmètre : `_reportLines`, `_resizeAirFleets`, `_scrapDeadLines`, `_refleetRoadLines`,
`_expandRailLines`, `_continueRailExpansion`. Ces fonctions décident **combien de véhicules par
ligne** et **quand une ligne meurt ou grandit** : elles portent à la fois le rendement unitaire
(−31,4 %) et une part du volume.

### ✅ La piste léguée par la §0 octies est TRANCHÉE — ce n'était pas un bug

**Les wagons vanilla ne coûtent rien à faire rouler.** Lecture du source du moteur : chaque ligne
wagon de `table/engines.h` porte `running_cost 0, RC_W` avec `RC_W = INVALID_PRICE`, et
`Engine::GetRunningCost()` retourne 0 immédiatement pour `base_price == INVALID_PRICE`.
`catalog.nut:284` remplit `runningCost` depuis cette même API, donc `wagonRunningAnnual` vaut **0**
et `main.nut:2648` soustrait zéro. `economy.nut:205` qui ignore les wagons a **raison**, et
`_expandRailLines` ne surcharge pas ses wagons marginaux.
⚠️ Vrai en vanilla seulement : un jeu de wagons NewGRF donnerait un coût non nul, et c'est alors
`economy.nut:205` qui deviendrait faux. Ce n'est pas la configuration du banc.

### 🔴 1. TOUTE la fonctionnalité `rail_refleet` est du code injoignable (`main.nut:2602`)

Vérifié à la main :

```
main.nut:2602   if (!RAIL_EXPAND || ...) return;        RAIL_EXPAND  <- false  (défaut 0)
main.nut:2668     if (RAIL_REFLEET) { ... }             RAIL_REFLEET <- true   (défaut 1)
main.nut:2690       OpexBuildSecondTrain(...)           ← SEUL site d'appel
main.nut:2712       OpexUpgradeRailLineToDoubleTrack(...) ← SEUL site d'appel
```

Le bloc `RAIL_REFLEET` est **imbriqué derrière un `return` anticipé** commandé par un réglage à 0
par défaut, et `_runNextTask:3054` fait `if (!RAIL_EXPAND) { task.enabled = false; return false; }`
— définitivement. Donc, avec les défauts livrés, **aucune ligne rail ne peut jamais obtenir un
second train ni une seconde voie**, alors que `rail_refleet` vaut 1 et qu'`info.nut:506-509`
l'annonce actif. Toute ligne rail est gelée à un train pour la partie entière.
➜ En plein dans l'écart de volume mesuré, très au-dessus du plancher de détection.

**⚠️ Nuance qui corrige la §0 octies** : la trouvaille n°1 de l'étape 4 citait
`builder_rail.nut:1257` comme le coût réel de la variante 2 trains. Or 1257 est **à l'intérieur de
`OpexUpgradeRailLineToDoubleTrack`** (fonction ouverte en 1180), c'est-à-dire le chemin mort
ci-dessus. La construction *initiale* gère `candidate.trains > 1` par un autre chemin
(`OpexBuildLine`, voir `builder_rail.nut:943`, `:1073`, `:1100`). **Le fond de la trouvaille tient**
— `infraCost` reste constant sur toute la boucle de `economy.nut` — mais la citation de ligne
visait le mauvais chemin : **revérifier le coût réel de la variante 2 trains contre `OpexBuildLine`
avant de corriger.**

### 🔴 2. Une ligne routière voit sa flotte doublée le cycle même où elle est construite (`:2324`)

`have = ("vehCount" in line) ? line.vehCount : 0`, mais les dicts de ligne routière (`:2770-2794`,
`:2943-2955`) ne portent **délibérément pas** `vehCount` : il n'est écrit que par
`_reportLines:2108`, au plus une fois par an. Or la file exécute `projects` (index 5) puis
`refleet` (index 7) **dans le même cycle** : une ligne tout juste bâtie arrive donc avec `have = 0`
alors que `target = max(predTrains, line.trains)` vaut la flotte réelle. `have >= target` est faux,
`OpexRoadRefleet(have=0, target=N)` part — et comme `have > 0` est faux il **saute la reprise de
gabarit** (`builder_road.nut:795`), crée un véhicule avec **sa propre liste d'ordres** au lieu de
partager, puis en clone N−1.
➜ **Toute ligne routière neuve achète immédiatement une seconde flotte complète**, avec des ordres
dupliqués. Cohérent avec les 3,26 véhicules par gare contre 2,71.

### 🔴 3. `isAnyWaiting` prend un véhicule en chargement pour un embouteillage (`:2345`)

`if (AIVehicle.GetCurrentSpeed(v) == 0) isAnyWaiting = true;` se déclenche pour tout véhicule
**arrêté à un arrêt en train de charger** — l'état normal. Les lignes de fret routier sont bâties
avec `AIOrder.OF_FULL_LOAD_ANY` (`builder_road.nut:837`), donc un camion reste à vitesse 0 la
majeure partie de son cycle. Les **trois** heuristiques de croissance (`:2362`, `:2367`, `:2371`)
exigent `!isAnyWaiting` : la situation qui devrait déclencher la croissance — du cargo qui
s'accumule pendant qu'un camion fait le plein — est lue comme « déjà saturé, ne pas grandir ».
**La condition est inversée par rapport à l'intention.** `movingCount` (`:2346`) est calculé et
jamais utilisé, ce qui corrobore que le signal voulu n'a jamais été câblé.
➜ Principal frein de croissance de la route, le mode qui porte le plus de lignes.

### Le reste

| gravité | lieu | problème |
|---|---|---|
| HAUT | `:2002` | Un `continue` sur une gare A devenue invalide **gèle l'état entier de la ligne pour toujours** : `deadStreak`, `vehCount`, `lastProfit` ne sont plus mis à jour, donc `_scrapDeadLines` ne la ferraille jamais. Ses véhicules saignent leur coût d'exploitation toute la partie et ses gares continuent de bloquer `_tooClose`. Même mode d'échec que la ligne `OIL_` documentée en `:2139`, sur un chemin que ce correctif ne couvrait pas. |
| HAUT | `:2211` | La garde de trésorerie air **price le mauvais avion** : `planePrice = catalog.plane.price` (le meilleur du catalogue) alors qu'`OpexAirAddPlane` clone le gabarit **de la ligne**. Une ligne à hélices face à un catalogue passé au gros jet voit `need` plusieurs fois trop grand → `break`, et une ligne rentable ne grandit jamais malgré la trésorerie. La garde interne étant correcte, celle-ci ne produit que des faux négatifs. |
| MOYEN | `:2242-2244` | Le commentaire garantit que la liste de ferraillage vient des véhicules **posés par cette ligne**, « PAS une interrogation par gare qui prendrait les convois du voisin ». Faux pour la route : `OpexLineVehicleIds` (`:381-388`) fait précisément la requête par gare pour `mode == "road"`. Sur un `StationID` partagé, **ferrailler une ligne morte envoie au dépôt et vend les camions de toutes les lignes co-localisées.** |
| MOYEN | `:2280` | Une ligne bloquée en `scrapping` n'est **jamais libérée** : seule sortie `remaining.len() == 0`. Un véhicule qui ne peut plus atteindre un dépôt fige la ligne à vie — elle est re-scannée chaque année, paie son exploitation et bloque `_tooClose`. Aucun plafond d'âge ni de tentatives. |
| MOYEN | `:2912`, `:2802` | **Tout l'état de temporisation de l'expansion rail est en écriture seule** : `expandBlocked` et `expandRetryCycle` ne sont lus que dans `_refleetRoadLines:2320`, une boucle qui a déjà fait `continue` sur `mode != "road"` — or ces champs ne sont posés que sur des lignes **rail**. Une ligne dont la rame dépasse le quai rejoue donc éternellement la séquence perdante : dérouter au dépôt, perdre le trajet, acheter le wagon, constater qu'il ne rentre pas, le revendre. Masqué aujourd'hui par la trouvaille n°1, actif dès qu'on l'allume. |
| MOYEN | `:2312` | `refleet` n'a **aucune limitation de cadence** (contrairement à `air_fleet:3047`) : le scan complet — deux `GetCargoWaiting`, deux `GetCargoRating`, un `AIVehicleList_Station` et un `GetCurrentSpeed` par véhicule, pour chaque ligne routière — est payé à **chaque cycle**, alors que ses entrées ne se rafraîchissent qu'une fois par an. |
| MOYEN | `:2612` | Une ligne ayant gagné un second train **ne peut plus jamais gagner de wagons** : `if (line.trains != 1 || line.vehCount != 1) continue;`. Les deux chemins sont mutuellement exclusifs et à sens unique. Sans effet tant que la trouvaille n°1 tient, plafond réel dès qu'elle est levée. |
| FAIBLE | `:2158-2162` | Les trois garanties du commentaire de `_resizeAirFleets` (âge ≥ 1 an, charge complète en attente, un avion par an) sont **absentes du chemin par défaut** — confirmé : seul le bloc `MARGINAL_FLEET` (à 0) les implémente, et `maxAddedPerPass = 4` contredit « au plus UN avion ». |
| FAIBLE | `:2208` | Gardes dupliquées et **incohérentes** : `deadStreak >= 1` ici contre `>= 2` en `:2171`, ce qui rend la première inatteignable. La politique documentée « deadStreak >= 2 » n'est pas celle qui tourne. |
| FAIBLE | `:2937` | `lastExpansionYear` écrit et jamais lu — confirmé. La garantie « au plus UNE expansion par an » est en fait assurée autrement (`expandStreak` + `RAIL_EXPAND_STREAK = 2`), et donne au plus une expansion **tous les deux ans**, plus strict qu'annoncé. Poids mort, pas défaut vivant. |
| FAIBLE | `:2189-2198` | Le commentaire d'en-tête promet une charge complète dans **les deux** aéroports ; le code implémente un OU (et le commentaire en ligne le dit correctement). Seul l'en-tête ment. |

### ✅ Vérifié comme n'étant PAS un bug — ne pas re-litiger

Coût d'entretien des wagons (voir verdict ci-dessus) ; `OpexRailNominalMaxWagons` et son `2*p−1`
(borne serrée, pas d'erreur de bord, vérifiée contre le test physique `:2907`) ; ordre de retrait
descendant dans `_scrapDeadLines` ; `collapsed` sur une ligne neuve (impossible, `GetRunningCost`
est strictement positif) ; hystérésis de `deadStreak` (2 ans consécutifs **et** `srcSuffering`
**et** revenu implicite nul — pas trop agressif) ; `<-` contre `=` dans `_reportLines` ;
`line.lineId` contre l'indice de boucle pour les panneaux ; `OpexAirAddPlane` qui alimente bien
`line.vehicles` ; le garde `lastExpandCheckYear` contre le double comptage d'une année ; le verrou
définitif de la tâche `expand` (sûr en soi — le problème est ce qui est imbriqué derrière) ; aucune
closure imbriquée ni `AIAccounting` imbriqué dans ce périmètre.

⚠️ Rien n'est corrigé ni mesuré. Le mécanisme est établi, pas son effet.

---

## 3 bis. 🔶 MESURER le headway réel des lignes de calibration de la note de gare (2026-09-02)

**Question ouverte, et il faut la MESURER, pas la deviner.** `OpexStationRatingForHeadway`
(`economy.nut`) décompose la note en `STATION_RATING_PCT * 255/100 − 95`, où le **95** suppose que
les lignes ayant servi au calage empirique (notes mesurées 49–55 en 15.3) étaient dans la tranche
de ramassage 95 points.

Or `economy_fix` corrige les seuils vers les valeurs du source (7,5 / 15 / 30 / 52,5 jours au lieu
de 6,8 / 13,5 / 27 / 47), et `TARGET_HEADWAY_DAYS = 7` bascule alors de la tranche 95 vers la
tranche **130**. Si les lignes de calibration étaient vraiment à 7 jours de headway *réel*, l'ancre
devrait donc devenir 130.

**Essayé le 2026-09-02, et RETIRÉ.** Trois raisons :

1. La décomposition utilise le headway **cible**, jamais le `roundTripDays / trains` réellement
   mesuré de ces lignes. Si leur headway réel dépassait 7,5 jours, elles n'étaient pas dans la
   tranche 130 et **95 est la bonne ancre**.
2. Une ancre à 130 donne `otherPoints = −2,5` : tous les autres facteurs de note du moteur
   (vitesse, âge du matériel, cargo en attente, statue) contribueraient ensemble **~0**. C'est
   invraisemblable au vu du source.
3. Smoke test 3 graines × 1 an avec la ré-dérivation : les trois graines s'effondrent et la graine
   42 sort à **−185 £ de profit**. À n=3 ce n'est pas une preuve, mais un profit négatif est un
   changement qualitatif, pas du bruit de trajectoire.

**Ce qu'il faut pour trancher** : instrumenter le `roundTripDays / trains` effectif des lignes sur
lesquelles la note 49–55 a été relevée, et lire dans quelle tranche elles tombent réellement. Tant
que ce n'est pas fait, l'ancre reste à 95 — y compris sous `economy_fix`, qui ne corrige donc que
les **seuils**, lesquels ne déplacent la courbe qu'au voisinage des bandes-frontières.

⚠️ Ne pas « corriger » l'ancre par cohérence algébrique : les deux hypothèses sont internement
cohérentes, seule la mesure les départage.

---

## 0 nonies bis. 🔴 LES TREIZE CORRECTIONS NE PAIENT PAS — banc du 2026-09-02

`docs/bench_corrections_3y_20seeds.json` : 20 graines x 3 ans, lecture appariée, 0 échec de
script. Bras de contrôle = défauts courants (donc `tree_planting` déjà corrigé) ; bras traité =
`loop_budget=1, portfolio_v2=1, fleet_fix=1, economy_fix=1`.

| métrique | effet des corrections | t | graines |
|---|---:|---:|---:|
| `company_value` | **+2,5 %** | 0,26 | 12/20 |
| `profit_year` | +11,3 % | 1,08 | 11/20 |
| `profit` | +20,7 % | 1,66 | 15/20 |
| `performance_history` | **+12,2 %** | 2,39 | 13/20 |
| `median_station_rating` | **−14,8 %** | 3,63 | 5/20 |
| gares | 21,4 → **20,6** | | |
| véhicules | 58,3 → **58,0** | | |

### 🔴 Ce que ça invalide

**L'hypothèse centrale du diagnostic tombe.** Toute la revue concluait que ~85 % de l'écart vient
du VOLUME, et que le goulot était le débit du contrôleur (61,2 % des mois avec ≥300 k£ et aucune
construction). Les correctifs visaient précisément ça — budget d'opcodes drainé, `Sleep` retiré,
portefeuille régénéré dès que le capital grandit, sélection au profit finançable. **Le volume n'a
pas bougé d'un pouce** : 20,6 gares contre 21,4, véhicules identiques.

Donc : **ce n'est pas le budget d'opcodes ni la sélection de projet qui limitent le volume.** Le
frein est ailleurs, et il faut le chercher ailleurs — vraisemblablement dans ce qui *produit* les
candidats (`candidates.nut`, non encore revu) ou dans le taux d'échec réel des constructions.

### Les deux effets réels, de signes opposés

- **`performance_history` +12,2 % (t = 2,39)** — au niveau du plancher (~12 %), donc juste établi.
- **`median_station_rating` −14,8 % (t = 3,63, 15/20 défavorables)** — nettement établi, et c'est
  une dégradation. **Mécanisme plausible et précis** : `economy_fix` choisit les convois au ROI,
  ce qui pousse vers MOINS de convois, donc un headway plus long, donc un palier de note de
  ramassage inférieur. Le correctif censé améliorer le rendement unitaire dégraderait la captation.

### Ce qu'il faut faire avant de continuer à corriger

1. **Isoler les quatre réglages** — quatre campagnes appariées, une par réglage. Sans ça on ne sait
   pas lequel des quatre porte le +12,2 % et lequel porte le −14,8 %. Soupçon principal :
   `economy_fix` pour la perte de note.
2. **Ne PAS adopter le lot en bloc.** Aucun des quatre n'est établi individuellement, et
   `company_value` — la seule métrique qui parle contre AAAHogEx — est plate.
3. Le seul gain mesuré de la journée reste **`tree_planting`** (+22 %, déjà adopté) : le bras de
   contrôle est passé de 602 750 à 766 552 de valeur moyenne depuis la référence `1aeefe1`.

⚠️ Écart avec AAAHogEx toujours entier : **0,79 M£ contre ~4,95 M£**, facteur ~6.

---

## 0 nonies ter. ✅ ISOLATION DES QUATRE RÉGLAGES — `economy_fix` adopté, `portfolio_v2` est le coupable (2026-09-02)

`docs/bench_isolation_3y_20seeds.json` : **5 bras, 100 parties**, 20 graines x 3 ans, lecture
appariée, 0 échec. Un seul contrôle commun, donc les quatre lectures sont comparables entre elles
(et 60 parties économisées sur quatre campagnes séparées).

| réglage | `company_value` | `profit_year` | `performance_history` | note de gare | gares | véhicules |
|---|---:|---:|---:|---:|---:|---:|
| **`economy_fix`** | **+11,7 %** (t 1,47) | **+21,1 %** (t 2,09) | **+16,1 %** (t 3,01) | −5,9 % (t −1,66) | 22,4 | 62,3 |
| `loop_budget` | +1,6 % (t 0,23) | +2,7 % | +1,1 % | −0,4 % | 21,7 | 61,8 |
| `fleet_fix` | −2,4 % | +2,0 % | −1,2 % | −2,5 % | 22,8 | 57,9 |
| **`portfolio_v2`** | **−24,4 %** (t −1,62) | **−30,7 %** (t −1,54) | +1,2 % | +4,0 % (t 2,21) | **27,2** | **71,9** |

*(contrôle : 21,4 gares, 58,3 véhicules, 766 552 de valeur)*

### ✅ `economy_fix` ADOPTÉ, défaut passé à 1

`profit_year` +21,1 % et `performance_history` +16,1 % dépassent leur plancher de détection, et
**priment sur `company_value` dans l'ordre des objectifs du projet**. Seule ombre, non établie :
note de gare −5,9 % (t = −1,66).

### 🔴 `portfolio_v2` : il TIRE le bon levier et détruit quand même la valeur

**C'est le seul réglage qui bouge le volume** — 21,4 → **27,2 gares (+27 %)**, véhicules +23 %.
Le levier que toute la revue cherchait existe donc bien, et c'est lui qui l'actionne. Mais il coûte
**−24,4 % de valeur et −30,7 % de profit annuel** : en classant au profit par livre de capital, il
privilégie **beaucoup de petites lignes bon marché et médiocres**. C'est exactement le risque que
l'analyse avait nommé (« une politique trop cheap-first peut construire beaucoup de petites lignes
médiocres »), et il s'est réalisé.

➜ **Ne pas jeter le mécanisme, corriger sa règle de tri.** Pistes : plancher de profit ABSOLU par
projet en plus du ratio ; ou classer les projets finançables au profit absolu plutôt qu'au ratio ;
ou n'autoriser le « bon marché » qu'une fois les gros projets rentables financés. C'est
**l'item de tête** : c'est la seule voie identifiée vers le volume.

### 🔴 `loop_budget` est NUL — la trouvaille n°1 de la revue du contrôleur est invalidée

+1,6 % (t = 0,23). **Le budget d'opcodes n'était pas le goulot.** Le raisonnement était pourtant
solide (10 000 opcodes/tick non reportables, une tâche par tick, ~810 M d'opcodes de dotation), et
il est faux : drainer le tick ne produit rien de plus. Corollaire : les « 61,2 % de mois avec
≥300 k£ et aucune construction » étaient un **symptôme, pas la cause** — si le vivier ne contient
rien qui vaille, donner plus de temps de calcul ne change rien.

### Pourquoi le lot groupé paraissait plat

`economy_fix` (+11,7 %) et `portfolio_v2` (−24,4 %) **se sont annulés**. Le banc groupé du même
jour donnait +2,5 % sur `company_value` : c'était la somme de deux effets réels de signes opposés,
pas l'absence d'effet. ⚠️ **Leçon de méthode : ne jamais conclure « sans effet » d'un lot de
correctifs groupés — isoler d'abord.**

### `fleet_fix` : nul au banc, mais garde un correctif de plantage

−2,4 % sur la valeur, rien d'établi. Il contient toutefois la réparation du champ `station_exit`
sans laquelle **l'IA meurt** dès que `rail_refleet` devient atteignable : à conserver le jour où ce
chemin sera réactivé.

---

## 0 nonies quater. ❌ `portfolio_v2` NON ADOPTABLE, même réparé — et pourquoi (2026-09-02)

`docs/bench_floor_3y_20seeds.json` : 5 bras, 100 parties, 20 graines x 3 ans, lecture appariée,
0 échec. Contrôle = défauts courants, **donc `economy_fix` déjà adopté**.

| bras | valeur moy | gares | `company_value` vs contrôle |
|---|---:|---:|---:|
| **contrôle** | **868 151** | **22,4** | — |
| plancher 0 % (v2 pur) | 747 226 | 21,1 | −16,2 % (t −1,92) |
| plancher 25 % | 797 729 | 18,7 | −8,8 % (t −1,87) |
| plancher 50 % | 869 146 | 21,9 | **+0,1 %** (t 0,02) |
| plancher 75 % | 860 782 | 20,2 | −0,9 % (t −0,23), `performance_history` **−12,4 %** (t −2,12) |

### Le plancher marche, et ça ne suffit pas

Le plancher de profit absolu **répare bien** ce qu'il devait réparer : de −16,2 % à l'équilibre
exact en montant à 50 %. Mais il ne produit **aucun gain** — au mieux `portfolio_v2` devient neutre
en ajoutant de la complexité. ❌ **Défaut maintenu à 0.**

### 🔴 L'interaction que l'isolation ne pouvait pas montrer

**Les +27 % de gares de `portfolio_v2` ont disparu.** Dans la campagne d'isolation, le contrôle
était *sans* `economy_fix` : 21,4 gares, contre 27,2 pour `portfolio_v2`. Depuis, `economy_fix` a
été adopté et le contrôle est monté **à 22,4 gares tout seul** — pendant que `portfolio_v2` n'en
tire plus que 21,1, soit **moins** que le contrôle.

➜ **`economy_fix` avait déjà capté le volume que `portfolio_v2` apportait.** Les cumuler est
redondant, voire nuisible. ⚠️ **Leçon de méthode : un effet mesuré contre un contrôle donné n'est
pas transportable une fois le contrôle amélioré.** Il faut re-mesurer contre le contrôle courant,
pas réutiliser le chiffre de la campagne précédente.

### Confirmation indépendante d'`economy_fix`

Le contrôle est passé de **766 552 à 868 151** de valeur moyenne entre les deux campagnes, seul
`economy_fix` ayant changé entre-temps. Son gain se confirme donc sur une campagne indépendante,
avec des graines et un bras de contrôle identiques par ailleurs.

### Où chercher le volume maintenant

Les deux voies testées sont épuisées : le budget d'opcodes est nul, et la sélection de projet ne
fait que déplacer la valeur. **Il reste `candidates.nut`, le seul gros morceau jamais revu** — ce
qui *produit* les candidats, avant toute sélection. Instrumenter d'abord : combien de candidats
générés, combien survivent à chaque filtre, combien échouent à la construction et pourquoi.

---

## 0 decies. 🔴 LE VRAI GOULOT : LA VITESSE DU CAPITAL (diagnostic du 2026-09-02)

`docs/diag_vivier_3y.json` : 5 graines x 3 ans, défauts courants, panneaux `CG`/`CR`/`CD`/`CE`/`CK`
enfin lus — **l'instrumentation existait déjà depuis des semaines et n'avait jamais été exploitée.**

### L'entonnoir du vivier (22 153 paires, 5 parties)

| étape | volume | part |
|---|---:|---:|
| paires générées | 22 153 | 100 % |
| rejet distance trop longue | 4 238 | 19,1 % |
| rejet profit non positif | 2 922 | 13,2 % |
| rejet ratio d'opcodes trop bas | 5 563 | 25,1 % |
| **acceptés** | **1 412** | **6,4 %** |
| dont **jetés par `TOP_K`** | 1 152 | **81,6 % des acceptés** |
| survivants au classement | 260 | |
| **lignes réellement construites** | **4,4 / partie** | |

### 🔴 Trois hypothèses tombent, mesurées

- **Le vivier n'est PAS vide** : 260 candidats classés survivent, ~20 par an et par partie.
- **La trésorerie ne bloque JAMAIS** : `cash_blocks` = **0** sur les 5 parties.
- **La construction ne rate PAS** : 12 tentatives rail sur 13 réussissent (1 seul `TRKFAIL`).

L'IA ne tente tout simplement pas : **2 à 4 tentatives rail en trois ans** face à 260 candidats.

### 🔴 La cause, lue dans les portefeuilles successifs (graine 999)

```
portefeuille  1 : capital 295 000 -> 3 projets, 293 424 depenses
portefeuille  2 : capital   9 933 -> 0 projet
portefeuille  3 : capital  12 078 -> 0 projet
portefeuille  4 : capital  15 101 -> 1 projet
portefeuille  5 : capital  35 223 -> 1 projet
```

Chaque portefeuille propose **250 à 310 projets viables**. Le premier mois, l'IA dépense **la
totalité de son capital** (293 424 sur 295 000) en trois projets. Ensuite elle vit sur **10 à 60 k£**
de bénéfices accumulés pendant trois ans, et ne finance plus que 0 à 2 micro-projets à la fois.

➜ **`cash_blocks` valait 0 parce que le portefeuille ne se fait jamais bloquer : il rabote
silencieusement ses ambitions à ce qu'il peut payer.** Le compteur mesurait un blocage qui, par
construction, ne pouvait pas survenir. ⚠️ **Leçon : un compteur à zéro ne prouve rien tant qu'on n'a
pas vérifié qu'il PEUT s'incrémenter.**

### Pourquoi les trois correctifs de la journée étaient nuls

- **`loop_budget`** : donner plus de cycles à une IA sans un sou ne change rien.
- **`portfolio_v2`** : mieux classer 250 projets quand on peut en payer zéro ne change rien.
- **`fleet_fix`** : même raison.

Tous trois optimisaient **en aval** d'une contrainte située **en amont**. C'est cohérent avec leurs
mesures : +1,6 %, neutre, −2,4 %.

### La vraie question, désormais

Le plafond d'emprunt est le même pour AAAHogEx, qui atteint pourtant 4,95 M£ à 3 ans avec ~3,4 M£
de profit annuel contre nos ~450 k£. **Il ne gagne pas parce qu'il emprunte plus, il gagne parce
que son capital tourne plus vite.** Deux directions à instrumenter avant de coder quoi que ce soit :

1. **Le rendement du premier déploiement.** Les 293 k£ du premier mois décident de toute la partie :
   si ces trois projets rendent mal, tout ce qui suit est affamé. Que rapportent-ils réellement, et
   combien de temps mettent-ils à se rembourser ?
2. **Le délai de retour.** Le classement ne comporte aucune notion de **payback** : un projet qui
   rend 50 k£/an en immobilisant 250 k£ bloque la croissance bien plus qu'un projet à 20 k£/an pour
   40 k£. À capital rare, c'est le temps de retour qui commande, pas le ROI annuel.

⚠️ Ne pas se précipiter sur `reborrow` : `SetLoanAmount(GetMaxLoanAmount())` est déjà appelé au
démarrage, donc `borrowable` vaut **0** tant que l'emprunt n'est pas remboursé. Le levier n'est pas
d'emprunter plus, il est de faire tourner ce qu'on a.

---

## 0 undecies. 🔴 CE QUE FAIT AAAHogEx : LA RUÉE AÉRIENNE (diagnostic mensuel, 2026-09-02)

`sweeps/diag_1v1_monthly.py` → `docs/diag_1v1_monthly.json` : 3 graines × 2 ans, une ligne par mois
et par IA, extraite des **chunks de sauvegarde** (les panneaux sont les nôtres, AAAHogEx n'en émet
aucun).

### La stratégie d'AAAHogEx, lue mois par mois

| mois | AAAHogEx tr/rt/bt/av | gares | OpexAI tr/rt/bt/av | gares |
|---|---|---:|---|---:|
| 1970-03 | **0/0/0/9** | 6,0 | 0/3/0/4 | 2,7 |
| 1970-06 | **0/0/0/13** | 6,7 | 0/4/0/3 | 3,3 |
| 1970-09 | 1/1/0/21 | 10,7 | 0/5/0/3 | 3,3 |
| 1970-12 | 1/1/0/**35** | 17,0 | 2/5/0/5 | 6,0 |
| 1971-05 | 12/18/0/53 | 38,0 | 5/12/0/8 | 10,7 |
| 1971-12 | 31/80/0/65 | 79,7 | 7/19/0/9 | 15,3 |
| 1972-01 | 31/**91**/0/65 | 85,7 | 8/19/0/9 | 16,0 |

**Il fait de l'AVION, exclusivement, pendant toute la première année** — 35 appareils fin 1970,
zéro train et zéro camion jusqu'en janvier 1971. Puis il bascule et convertit ces profits en un
réseau rail+route massif en année 2.

Nous, dès février 1970, nous sommes **déjà éparpillés** (1 route + 4 avions) et nous progressons au
goutte-à-goutte sur tous les modes à la fois.

### 🔴 Il ne construit PAS des lignes plus rentables

Profit par véhicule :

| | OpexAI | AAAHogEx | rapport |
|---|---:|---:|---:|
| 1970-12 | 5 009 326 | 5 436 241 | 1,09 |
| 1971-12 | 2 588 799 | 3 516 375 | 1,36 |

**Nos lignes sont individuellement saines.** Sur toute l'année 1970 son profit par véhicule est du
même ordre que le nôtre, parfois inférieur (avril : −81 020 contre −43 610 chez nous).
➜ **Il ne gagne ni par la qualité des lignes ni par une meilleure exploitation : il gagne par le
NOMBRE.** 5× plus de véhicules.

### Pourquoi l'avion, et pourquoi ça répond au goulot

L'avion est le seul mode dont **le véhicule supplémentaire ne coûte AUCUNE infrastructure** : pas
de tracé, pas de pathfinding, pas de voie, pas de quai à rallonger. Deux aéroports posés, chaque
appareil suivant est du capital pur converti immédiatement en revenu.

C'est donc le mode qui **fait tourner le capital le plus vite** — exactement le goulot mesuré en
§0 decies (44,5 % de notre valeur dort en caisse contre 10,4 % chez lui). Et il l'exploite en
**concentration** : ~2 appareils par gare, sur peu de liaisons.

### Ce que ça dit de notre conception

Notre portefeuille arbitre les modes **au ROI par projet**, ce qui traite un avion supplémentaire
sur une liaison existante comme un projet parmi d'autres. Or ce n'est pas un projet : c'est une
**expansion à coût marginal d'infrastructure nul**, la seule opération qui échappe au plafond de
~1 projet par mois (§0 decies). `_tryBuildAir` a d'ailleurs déjà `maxBatch = 12` là où le
portefeuille est bridé à 1 — mais nous n'atteignons que 5 à 9 appareils là où il en aligne 35.

**Piste de tête, et elle est cohérente avec tout ce qui précède** : traiter l'ajout d'avion sur
liaison existante comme un flux continu prioritaire, pas comme un projet en concurrence avec le
rail. À vérifier avant de coder : pourquoi `_tryBuildAir` plafonne-t-il en pratique à ~9 appareils
alors que son `maxBatch` vaut 12 et que la trésorerie ne bloque jamais ?

## 0 undecies bis. ✅ Rabattage : cause trouvée et CORRIGÉE — croissance aérienne : cause trouvée, PAS un bug (2026-09-02 soir)

Suite directe de §0 undecies (« pourquoi si peu d'avions, pourquoi aucun rabattage »). Deux
instrumentations ajoutées pour trancher : `air_fleet_probe=1` (déjà présent, gate les panneaux
`FR|` de `OpexAirFleetRefusal`) et un nouveau panneau `FZ|` dans `_tryBuildFeeders` détaillant à
quelle garde chaque candidat de rabattage meurt (`served`, `townCount`, `abandoned`, `cash`,
`planNull`, `buildFail`).

### 🔴 Rabattage : bug à 100 % de taux d'échec, trouvé et corrigé

`builder_road.nut:743` construisait l'ordre de destination du rabattage avec
`AIOrder.OF_TRANSFER | AIOrder.OF_UNLOAD` combinés. Or `AIOF_UNLOAD` et `AIOF_TRANSFER` sont
**mutuellement exclusifs** dans l'API OpenTTD (`ai_order.hpp:44-47` : « Cannot be set when
AIOF_TRANSFER is set » et réciproquement — même champ de 3 bits, « type de déchargement »). Les
combiner fait échouer `AreOrderFlagsValid` à coup sûr, donc `AIOrder.AppendOrder` échoue avec
`ERR_PRECONDITION_FAILED` (code 2) — **chaque candidat de rabattage qui atteint ce point échoue à
100 %, sur toutes les graines, à chaque tentative**, depuis toujours (latent tant que
`_tryBuildFeeders` lui-même était mort, donc jamais exercé avant C1).

Mesuré sur 5 graines × 3 ans avant correctif : 305 rejets au total sur le panneau `FZ|`, dont
**226 `abandoned`** (candidats mis en cache après un premier échec et jamais retentés), et parmi
les échecs initiaux (`RA|`) : **18 `ORDERS`** (le bug ci-dessus) et 14 `TRACEX` (échec de tracé,
cause distincte). `n_feeders` : **0 sur les 5 graines**.

**Correctif** : `destFlags = AIOrder.OF_TRANSFER` seul (le comportement voulu — déposer pour
ramassage par une autre ligne, pas livrer définitivement). Trois commentaires obsolètes corrigés
au passage (`builder_road.nut:620`, `candidates.nut:1163`, `main.nut:1452`).

**Vérifié après correctif**, même campagne (5 graines × 3 ans) : **4 graines sur 5 construisent
maintenant des feeders** (0 avant) : seed 42 → 3 feeders, seed 100 → 2, seed 7 → 4, seed 2026 → 3,
profits annuels prédits positifs (148 £ à 16 606 £ selon la ligne). Seed 999 reste à 0, mais pour
une raison différente (`TRACEX`, échec de tracé routier propre à sa géographie) — pas une preuve
d'échec du correctif.

### ✅ Croissance de flotte aérienne : cause trouvée, ce n'est PAS un bug

Contrairement à ce que §0 undecies affirmait (« la trésorerie ne bloque jamais »), le panneau `FR|`
(`air_fleet_probe=1`) montre que **63 refus sur 65 (97 %) sont du cash insuffisant** (code `M`,
*après* tentative de réemprunt via `REBORROW` — le plafond d'emprunt est déjà atteint), et 2
seulement à cause d'un profit négatif (`L`). Aucun refus `Y`/`V`/`D`/`C`/`S`/`X` observé : ni la
capacité de l'aéroport, ni le `deadStreak`, ni un échec technique de `OpexAirAddPlane` ne bloquent
quoi que ce soit sur cet échantillon. **C'est le même mur que §0 decies/`opexai_plafonnement.md` :
la trésorerie 1970-1980 est déjà au plafond d'emprunt.** Ajouter des avions à un hub existant ne
peut donc pas aller plus vite tant que ce mur de trésorerie n'est pas traité — cohérent avec la
piste de tête déjà identifiée (dénominateur/ressource rare, A1) plutôt qu'un correctif de code
supplémentaire à chercher ici.

---

## 0 undecies ter. 🔴 L'IA SE FIGE DES MOIS ENTIERS PENDANT UN A\* RAIL — la vraie cause du plafond aérien (2026-09-03)

Suite de §0 undecies bis. La question posée était : « comment peut-on construire du rail alors
qu'on n'a pas de quoi acheter un avion ? ». Réponse : **le rail ne prend pas l'argent de l'avion,
il prend le TEMPS DE L'IA**.

### La mesure qui tranche

`docs/diag_1v1_monthly_signs.json` (`sweeps/diag_1v1_monthly.py`, désormais avec capture du chunk
`SIGN` et `air_fleet_probe=1`) donne le nombre **cumulé de panneaux, tous types confondus**, mois
par mois. Il ne s'agit plus de la seule télémétrie aérienne :

| graine 100 | 1971-05 | 1971-06 → 1971-12 | 1972-01 |
|---|---:|---:|---:|
| panneaux cumulés | 317 | **317 (+0 pendant 7 mois)** | 330 |

**Sept mois consécutifs sans un seul panneau de quelque type que ce soit.** Ce n'est pas
`_resizeAirFleets` qui se tait : c'est l'IA entière qui ne fait plus rien. Même signature sur la
graine 42 (septembre → novembre 1970, +0). Et dans les deux cas **la reprise coïncide exactement
avec l'apparition de trains neufs** : graine 100 → 5 puis 10 trains en 1972-01 ; graine 42 → 4
trains en 1970-12.

### Le mécanisme

La boucle principale exécute **une tâche par tick puis `Sleep(1)`** (`loop_budget = 0`, défaut).
Une tâche qui part dans un A\* ferroviaire long n'est pas « lente » : le moteur la suspend et la
**reprend au même endroit** au tick suivant, donc **aucune autre tâche ne tourne** tant qu'elle
n'a pas fini. Coût mesuré d'une seule tentative rail réussie
(`docs/diag_airfleet_monthly_5s3y.json`) :

| graine | année | itérations A\* | opcodes |
|---|---:|---:|---:|
| 7 | 1971 | 18 550 | **57 406 250** |
| 100 | 1971 | 15 050 | **46 816 101** |
| 2026 | 1972 | 13 900 | 37 250 868 |

À 10 000 opcodes par tick et 74 ticks par jour, 46,8 M opcodes ≈ **2 mois de jeu pour une seule
tentative**, sans compter les tentatives échouées ni la pose elle-même. Le commentaire de la file
de tâches l'admettait déjà à demi-mot (« même si un A\* a franchi le changement d'année »), et le
retrait d'une ligne morte avait déjà mesuré une famine « jusqu'à un an ».

### 🔴 Ce que ça invalide

- **La lecture « refus pour trésorerie » de §0 undecies bis est incomplète.** Les refus `M` sont
  réels, mais l'essentiel du plafond aérien ne vient pas d'un refus : il vient de mois entiers où
  la croissance **n'est même pas évaluée**. La trésorerie monte à vide pendant ce temps
  (graine 100 : 76 k£ → 179 k£ pendant le gel).
- **Aucun réordonnancement des tâches ne peut corriger ça** : le problème n'est pas l'ordre, c'est
  qu'une seule tâche confisque la file pendant des mois. C'est le même goulot que
  [[pathfinder-budget-contrainte]] et §0 sexies, mais mesuré ici en **mois de jeu perdus**, pas en
  opcodes.

### Piste, non codée

Découper l'A\* rail en tranches reprises d'un **tour de file** à l'autre (comme
`_continueRailExpansion` le fait déjà), pour que les autres tâches tournent pendant la recherche.

⚠️ **Deux fausses pistes à écarter d'emblée, vérifiées dans le code le 2026-09-03 :**

1. **Il n'y a PAS d'A\* « fait maison » à remplacer.** `main.nut:28` fait
   `import("pathfinder.rail", "RailPathFinder", 1)` : on utilise déjà la bibliothèque officielle
   `Pathfinder.Rail`, elle-même bâtie sur `Graph.AyStar`. Seule la fonction de coût est à nous.
   Toute tâche formulée comme « remplacer notre A\* par `Graph.AyStar` » est sans objet.
2. **Le pathfinding segmenté n'est PAS en production** (seulement dans `sweeps/measure_*_segmented.py`,
   hérité de `TrainLineAI`) — mais le porter ne suffirait pas : à 4× moins cher, une tentative à
   57 M opcodes gèle encore ~2 semaines de jeu, et il y en a plusieurs par partie. La segmentation
   **réduit** le gel, la reprise par tranches le **supprime**, quel que soit le coût du pathfinder.
   Les deux se composent ; la reprise passe en premier.

🔴 **Le point délicat du refactor** : `deadlineTick` borne aujourd'hui du temps de jeu *écoulé*.
Étalée sur plusieurs tours, une recherche simplement entrelacée dépasserait cette borne sans être
plus lente. La comptabilité doit passer en **itérations consommées**, pas en ticks, sinon le
correctif tue exactement les recherches qu'il est censé sauver.

## 0 undecies quater. ✅ `air_roi_order` ADOPTÉ — la croissance aérienne servait la ligne la plus VIEILLE (2026-09-03)

Second défaut trouvé en même temps, indépendant du gel ci-dessus, et celui-là est corrigé.

### Le défaut

`_resizeAirFleets` parcourait `this._lines` **dans l'ordre de construction** — pas un choix de
conception, juste l'ordre du tableau. La première ligne aérienne ouverte captait donc la
trésorerie à chaque passage, rentable ou non, et les suivantes ne passaient jamais. Aucun tri par
rendement nulle part.

Conséquence mesurée avant correctif (`docs/diag_airfleet_monthly_5s3y.json`, 5 graines × 3 ans) :
**aucun effet composé nulle part**. Croissances réussies via ce mécanisme sur toute la fenêtre :

| graine | 42 | 100 | 7 | 999 | 2026 |
|---|---|---|---|---|---|
| croissances | 1 (→2 avions) | **0** | **0** | 4→5→6 (+1/an) | **0** |

### Le correctif

Réglage `air_roi_order` (défaut **1**). Les lignes aériennes sont triées avant la boucle par
`OpexAirFleetYield` = **profit par appareil déjà en service** (`lastProfit` mesuré s'il existe,
sinon `predicted`), donc la ligne qui rembourse l'appareil suivant le plus vite est servie la
première. Le tri porte sur une copie de références : `_lines` garde son ordre, dont dépend le
retrait par position de `_scrapDeadLines`.

### ✅ Banc apparié 20 graines × 10 ans (`docs/bench_air_roi_order_10y.json`), 40 parties, 0 échec

| métrique | ordre construction | ordre rendement | écart | t | graines gagnantes | p (signes) |
|---|---:|---:|---:|---:|---:|---:|
| `company_value` | 1 554 230 £ | **1 688 017 £** | **+7,93 %** | 2,29 | **17/20** | **0,0026** |
| `profit_year` | 249 549 £ | **294 378 £** | **+15,23 %** | 3,36 | 16/20 | 0,0118 |
| `performance_history` | 432 | **478** | **+9,54 %** | 3,33 | 16/20 | 0,0118 |
| `profit` | 60 443 £ | 75 407 £ | +19,84 % | 2,27 | 14/20 | 0,115 |
| `median_station_rating` | 170,1 | 170,1 | +0,04 % | 0,23 | 17/20 | — |

Trois métriques sur quatre passent le test des signes, dont `company_value` à p = 0,0026. C'est
le gain le plus net depuis l'adoption du mode route. Défaut mis à 1 ; `air_roi_order=0` rend
l'ordre historique pour re-mesurer.

⚠️ **Ce correctif ne traite PAS le gel de §0 undecies ter** : il répartit mieux la trésorerie
quand l'IA tourne, il ne lui rend pas les mois perdus dans l'A\*. Les deux se cumulent.

---

## 0 undecies quater. ❌ A4 `rail_search_resumable` — REJETÉ, et il renverse le diagnostic de §0 undecies ter (2026-09-03)

Implémentation déléguée à grok (`grok-4.6`), relue et corrigée ici, puis mesurée. Le code est
fusionné et fonctionnel ; c'est la **mesure** qui le rejette.

### Le banc

`docs/bench_rail_search_resumable_10y.json`, banc apparié 20 graines × 10 ans, 40 parties,
0 échec, bras 0 contre bras 1 **de la même branche** :

| métrique | bloquant (`=0`) | reprenable (`=1`) | écart | t | graines | p (signes) |
|---|---:|---:|---:|---:|---:|---:|
| `company_value` | 1 478 949 £ | 1 201 031 £ | **−23,1 %** | −3,48 | perd **16/20** | **0,0118** |
| `performance_history` | 431 | 359 | **−20,0 %** | −3,54 | perd **17/20** | **0,0026** |
| `profit_year` | 247 326 £ | 202 318 £ | −22,3 % | −2,28 | perd 13/20 | 0,26 |
| `profit` | 61 764 £ | 50 485 £ | −22,3 % | −1,61 | perd 13/20 | 0,26 |

### 🔴 Le mécanisme, lisible dans les chiffres

Le bras reprenable construit **moins** : **31,4 gares contre 39,5**, **128 véhicules contre 152,7**.
Dégeler la file **n'a pas créé de capacité** — elle a réparti la même capacité plus mince, en
retardant la mise en service des lignes rail qui rapportent.

### 🔴 Ce que ça renverse dans §0 undecies ter

Le gel de 7 mois est réel et reste mesuré. Mais **il ne coûtait pas ce qu'on croyait** : les tâches
qu'il bloquait étaient **elles-mêmes bloquées par la trésorerie** — 63 refus de croissance aérienne
sur 65 pour cause de cash (§0 undecies bis). Leur rendre du **temps** ne leur donne pas d'**argent**,
alors que retarder le rail coûte directement.

➡️ **Leçon généralisable, à opposer à toute future idée d'ordonnancement** : le budget d'opcodes
est un **stock**, pas un problème d'ordonnancement. On ne gagne pas en redistribuant le temps ; on
gagne en **abaissant le coût total** (A5, pathfinding segmenté) ou en changeant ce qu'on achète (A1).

### Ce qui reste acquis du travail

- Le réglage `rail_search_resumable` (défaut 0) et la machine à états `_railSearch`, rejouables.
- ⚠️ **Le défaut 0 n'est PAS bit-à-bit identique à l'avant-A4** : la recherche est rigoureusement
  la même (8 850 itérations à l'identique sur la graine 42), mais les frames d'appel ajoutées
  coûtent **+9 974 opcodes** (+0,037 %), soit presque un tick entier, ce qui décale l'aval.
  Inhérent : ici le comportement dépend des opcodes consommés. **Tout banc sur ce réglage doit
  donc comparer bras 0 contre bras 1 de la même branche**, jamais contre des chiffres historiques.
- 🔴 **Piège Squirrel qui a failli passer** : `const` n'accepte qu'un **littéral** scalaire.
  `= PATH_CHUNK` et `= 74 * 365 * 2` ne compilent pas (« scalar expected »), et comme c'est une
  erreur de compilation, l'IA meurt au démarrage **sur tous les bras, défaut compris** (4/4 parties
  en erreur fatale NoAI). Détecté par un smoke test 2 graines × 3 ans, pas par la relecture.
  ➡️ **Après toute livraison d'agent touchant du `.nut`, smoke test avant commit.**

---

## 0 undecies quinquies. 🟡 A5 `rail_segmented_search` — le mécanisme MARCHE, la valeur est NEUTRE ; adopté à 1 par décision (2026-09-03)

Portage de `ai/TrainLineAI-segmented/` vers `ai/OpexAI/builder_rail.nut`, délégué à grok
(`grok-4.6`), relu ici, smoke-testé (`docs/smoke_a5.json` : bras 0 **bit-à-bit identique** au
master d'avant, donc le refactor ne décale rien quand le réglage est à 0), puis mesuré.

### Le banc

`docs/bench_rail_segmented_10y.json`, banc apparié 20 graines × 10 ans, 40 parties, 0 échec, les
deux bras **de la même branche** (`feat/rail-segmented-search`) :

| métrique | classique (`=0`) | segmenté (`=1`) | écart | t | graines gagnées | p (signes) |
|---|---:|---:|---:|---:|---:|---:|
| `company_value` | 1 478 949 £ | 1 430 436 £ | −3,4 % | −0,86 | 7/20 | 0,2632 |
| `profit_year` | 247 326 £ | 229 107 £ | −8,0 % | −1,40 | 9/20 | 0,8238 |
| `profit` | 61 764 £ | 56 858 £ | −8,6 % | −1,12 | 9/20 | 0,8238 |
| `performance_history` | 431 | 423 | −1,9 % | −0,50 | 9/20 | 0,8238 |

**Aucune métrique de valeur n'approche la significativité** (tous les $|t| < 1{,}5$, tous les
$p \geq 0{,}26$). C'est un **résultat nul**, pas un rejet : distinctement plus doux que le
−23,1 % franc d'A4 (§0 undecies quater).

⚠️ **Correction d'une erreur de dépouillement** faite en séance : j'ai d'abord annoncé
`median_station_rating` « 15/20 gagnées, $p = 0{,}0414$ ». **Faux — ces 15 sont des ÉGALITÉS.**
Hors égalités le score est **classique 5, segmenté 0** ($n = 5$, $p = 0{,}0625$) : la note de gare
ne monte jamais et baisse sur 5 graines. Règle : le test des signes **exclut** les ex æquo, il ne
les attribue pas.

### 🟢 Le mécanisme visé fonctionne, et c'est le plus gros effet du banc

| | classique | segmenté | écart | t |
|---|---:|---:|---:|---:|
| gares | 39,5 | **44,6** | **+12,9 %** | **+1,94** |
| véhicules | 152,7 | **161,1** | +5,5 % | +1,44 |
| trésorerie | 91 493 £ | 69 964 £ | **−23,5 %** | −2,03 |

La segmentation **convertit réellement les abandons en lignes construites** — c'était exactement
la cible (sonde `docs/probe_abnd.json` : **40 % des tentatives rail meurent en `ABND`**). Le +12,9 %
de gares est le plus fort effet mesuré du banc, plus fort que n'importe quelle métrique de valeur.
Et la trésorerie fond d'autant : **l'IA dépense son cash à construire ce réseau supplémentaire.**

### 🔴 Pourquoi ça ne paie pas — et ça referme une vieille question

Les candidats qui mouraient en `ABND` avaient un budget d'itérations de **5 000**. Or ce budget est
**proportionnel au profit attendu**. Ce sont donc, *par construction*, les lignes que le modèle
juge les **moins rentables**. Le projet avait déjà mesuré et réfuté « relever le budget
d'itérations », avec exactement ce raisonnement : « payer 90 000 itérations pour récupérer les
`PATHLIM`, c'est acheter les lignes les moins rentables au prix fort »
([[pathfinder-budget-contrainte]]).

**A5 obtient le même effet quatre fois moins cher — et retombe sur le même verdict.** Baisser le
prix n'a rien changé, parce que **le problème n'a jamais été le coût de trouver ces chemins, mais
la valeur de ces lignes.**

➡️ **Les trois voies d'attaque du pathfinder sont désormais épuisées et mesurées :**

| voie | tâche | verdict |
|---|---|---|
| **relever** le budget d'itérations | (2026-08-28) | ❌ réfuté — rendement ÷16 entre lignes faciles et difficiles |
| **redistribuer** le temps de recherche | A4 | ❌ −23,1 %, 16/20 graines |
| **abaisser** le coût de recherche | A5 | 🟡 nul (−3,4 %, $p = 0{,}26$) |

🔑 **Le pathfinder n'est pas le goulot.** Trois mesures indépendantes le disent maintenant, chacune
par un angle différent. Toute nouvelle idée de pathfinding doit d'abord expliquer pourquoi elle
échappe à ces trois-là. Le levier restant est **le dénominateur du classement** (A1) et **le volume
de liaisons** (A2), pas la recherche de chemin.

### ✅ Décision : défaut **1** (utilisateur, 2026-09-03)

Contre ma recommandation (« instrument à défaut 0 »), et le raisonnement se tient :

- **Le résultat est nul, pas négatif.** Rien n'est significatif ; on ne renonce à aucun gain établi.
- **Les médianes vont dans l'autre sens que les moyennes** : `company_value` médiane
  1 367 726 £ contre 1 343 685 £, `performance_history` médiane 434,5 contre 413,5. La moyenne est
  tirée par quelques grosses pertes, pas par une dégradation générale.
- **À 10 ans le réseau supplémentaire n'est pas amorti** : +12,9 % de gares payées en trésorerie
  (−23,5 %), pour un revenu encore plat. Un horizon plus long les jugerait différemment.
- **C'est le socle des mesures suivantes** : avec la segmentation active, le gel de §0 undecies ter
  est structurellement plus court. **A4 mérite donc d'être retesté sur ce socle** — sa perte venait
  d'un retard de mise en service du rail, que la segmentation réduit à la source.

`RAIL_SEGMENTED_SEARCH` : repli d'initialisation passé à `true` dans `main.nut` pour qu'il vaille le
défaut du réglage — une partie qui n'aurait pas lu ses réglages doit se comporter comme une partie
normale.

---

## 0 undecies sexies. ❌❌ A4 RETESTÉ sur socle segmenté — REJETÉ UNE SECONDE FOIS, et on comprend enfin le mécanisme (2026-09-03)

L'hypothèse à tester : A4 avait perdu 23 % **parce qu'il retardait la mise en service du rail**. Si
la segmentation (A5, désormais défaut 1) raccourcit assez les recherches, ce retard devrait
s'évaporer et A4 redevenir neutre. **Elle est réfutée.**

Vérifié avant de lancer : audit du chemin combiné A4=1 × A5=1 (agy, recoupé ligne à ligne ici) —
un seul `state.iterations++` par `FindPath(1)`, `state.spent = slice.iterations` en affectation donc
pas de double décompte, `state.pathfinder` remis à `null` seulement en fin de segment réel et jamais
sur la sortie `CONT` de tranche. Puis smoke 2 graines × 3 ans, 4/4 OK, bras divergents. **Le banc
mesure bien A4, pas un bug d'interaction.**

`docs/bench_a4_retest_on_a5_10y.json`, banc apparié 20 graines × 10 ans, 40 parties, 0 échec,
`rail_segmented_search=1` **sur les deux bras** :

| métrique | A4=0 | A4=1 | écart | t | graines | p (signes) |
|---|---:|---:|---:|---:|---:|---:|
| `company_value` | 1 430 436 £ | 1 240 481 £ | **−13,3 %** | −2,79 | 5/20 | **0,0414** |
| `performance_history` | 423 | 370 | **−12,5 %** | −2,38 | 3/20 | **0,0026** |
| `profit` | 56 858 £ | 50 904 £ | −10,5 % | −1,00 | 7/20 | 0,2632 |
| `profit_year` | 229 107 £ | 216 419 £ | −5,5 % | −0,57 | 7/20 | 0,2632 |
| **gares** | **44,6** | **32,4** | **−27,5 %** | **−4,46** | 2/20 | **0,0004** |
| **véhicules** | **161,1** | **134,2** | **−16,7 %** | **−3,92** | 2/20 | **0,0004** |

**Deux socles indépendants, même verdict.** La perte s'atténue (−23,1 % → −13,3 %), ce qui est
cohérent avec « la segmentation réduit bien le retard » — mais **pas du tout assez**.

### 🔑 Le mécanisme, enfin identifié — et ce n'est PAS seulement de la redistribution

L'effet de loin le plus fort et le plus significatif du banc n'est aucune métrique de valeur, c'est
le **nombre de gares : −27,5 %, t = −4,46, 18/20 graines perdantes**. A4 ne réarrange pas la
construction, **il l'empêche**.

La cause est dans `main.nut:2847` (et `:3080`) :

```squirrel
safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS,
```

**L'échéance est absolue et posée une seule fois, en TICKS, alors que le travail se compte en
ITÉRATIONS.** En mode bloquant, la quasi-totalité des ticks de cette fenêtre est consommée *par la
recherche elle-même*. En mode reprenable, **la même fenêtre de ticks est partagée avec toute la file
de tâches** : la recherche n'en reçoit qu'une fraction, son échéance tombe après beaucoup moins
d'itérations, et elle meurt en `DEAD` au lieu d'aboutir.

➡️ **A4 ne redistribue pas le temps : il ampute la fenêtre de recherche.** C'est ce qui explique
quantitativement les −27,5 % de gares, là où « redistribuer » n'expliquait rien de tel.

🔶 **Hypothèse testable, NON mesurée, à ne pas présenter comme un fait** : ce défaut est
*réparable* — rendre l'échéance proportionnelle au travail accompli, ou l'étendre du temps cédé aux
autres tâches. Une A4-bis ainsi corrigée n'a **jamais** été mesurée. Le rejet ci-dessus porte sur
A4 **telle qu'implémentée**, pas sur l'idée d'ordonnancement en général. ⚠️ Mais avant de la
retenter, se rappeler que la leçon du STOCK (§0 undecies quater) tient toujours : les tâches
débloquées étaient bloquées par la **trésorerie**, pas par le temps.

**Décision** : `rail_search_resumable` reste à **défaut 0**, conservé comme instrument.

---

## 0 undecies septies. ❌ SEUILS DE TRÉSORERIE : les deux abaissements sont NEUTRES — et la réserve n'est pas ce qu'on croyait (2026-09-03)

Suite directe du diagnostic 1v1 (§0 undecies sexies bis) : 88 refus `insufficient_cash` pour
3 acceptations sur la croissance aérienne. Deux leviers demandés par l'utilisateur, implémentés en
réglages **séparés** pour que le banc puisse attribuer.

- `reserve_maint_cap` : `OpexCashReserve()` plafonnée à `totalRunning / 12`, soit **un mois**
  d'entretien au lieu de trois. Le plafond prime sur le plancher `CASH_RESERVE_MIN = 5000` et peut
  valoir 0 sur flotte vide — demandé explicitement, aucune marge de sécurité ajoutée.
- `air_margin_v2` : marges exigées **en plus** de la réserve. Refleet 2 000 → 0 ; deux aéroports
  neufs 30 000 → 15 000 ; un aéroport neuf 12 000 → 6 000 ; réutilisation 2 000 → 0.

Vérifié avant de mesurer : les deux réglages à 0 sont **identiques bit à bit** au master d'avant
(36 champs sur 4 parties, `docs/smoke_ident2.json`).

### Le banc — factoriel complet, 4 bras × 20 graines × 10 ans, 80 parties, 0 échec

`docs/bench_tresorerie_10y.json`. Écarts contre le témoin (`0,0`) :

| bras | `company_value` | t | p | gares | véhicules |
|---|---:|---:|---:|---:|---:|
| réserve seule | −5,9 % | −0,89 | 0,50 | −11,7 % | **−9,8 %** (t = −2,18) |
| marges seules | −3,6 % | −1,06 | 1,00 | −7,6 % | −4,5 % (t = −2,46) |
| les deux | −6,2 % | −1,00 | 0,50 | −8,8 % | −7,5 % |

**Aucune métrique de valeur n'est significative**, et les trois bras vont dans le même sens :
légèrement négatif. Verdict : **on n'adopte ni l'un ni l'autre**, défauts laissés à 0.

### 🔑 Trouvaille 1 — abaisser un SEUIL ne libère que la bande entre l'ancienne et la nouvelle valeur

`air_margin_v2` est **strictement identique au témoin sur 7 graines sur 20** (tous champs confondus).
C'est mécanique : baisser une marge de 30 000 à 15 000 ne change le comportement que lorsque la
trésorerie tombe *entre* les deux valeurs. Sur le refleet, cette bande fait **2 000 £**.

➡️ **À opposer à toute future idée de « desserrer un seuil ».** Ce qui change vraiment le
comportement, c'est de changer une **formule** — `reserve_maint_cap` modifie la valeur à chaque
appel et agit sur les 20 graines sur 20. Le seuil, lui, n'agit qu'au bord.

### 🔴 Trouvaille 2 — la réserve n'est pas un plancher de sécurité, c'est le BUDGET DU SAC À DOS

Contre-intuitif et vérifié dans le code : baisser la réserve fait construire **moins**
(−11,7 % de gares, −9,8 % de véhicules). Ce n'est pas de la faillite — **zéro mois de faillite sur
les 80 parties**, trésorerie de fin inchangée (65 925 £ contre 67 123 £).

La chaîne causale est dans `ai/OpexAI/projects.nut:450` :

```squirrel
local capitalBudget = cash + borrowable - OpexCashReserve();
```

puis `:539` → `OpexKnapsackSolve(byBudget, capitalBudget, ...)`, qui **maximise la somme des
`revenueAnnual` sous contrainte de capital**. La réserve n'est donc pas seulement un filet : c'est
la **contrainte du sac à dos**. La baisser augmente le budget, et un sac à dos qui maximise le
revenu — non le rendement — dépense ce budget supplémentaire en projets **plus gros**, donc moins
nombreux.

🔶 **Statut : hypothèse forte, non mesurée directement.** La chaîne de causalité est vérifiée dans
le code et la direction des chiffres y colle, mais je n'ai pas isolé la bascule de mode. Ce qui la
testerait : mesurer la répartition des modes entre les deux bras.

➡️ **Ça pointe directement sur C13** (sac à dos classé par ROI et non par revenu) : tant que
l'objectif du sac à dos est le revenu sous contrainte de capital, *donner plus de capital dégrade le
choix*. C'est le même défaut que celui identifié chez AAAHogEx à l'envers — elle change de
dénominateur selon la ressource rare, nous divisons toujours par le capital.

---

## 0 undecies octies. 🟡 C13 `knapsack_roi` : NEUTRE (+4,1 %, non significatif) — et le premier banc mesurait MON bug (2026-09-03)

Le sac à dos maximisait la somme des `revenueAnnual` (`projects.nut`, `OpexKnapsackSearch`). Le
revenu ignore les frais de roulement : deux projets à revenu égal y sont équivalents même si l'un
paie deux fois plus. `knapsack_roi=1` bascule **trois choses de concert** — l'objectif, la **borne**
du Branch & Bound (elle doit majorer la *même* grandeur, sinon l'élagage coupe des solutions
valides) et l'ordre de branchement (il doit suivre la densité de la grandeur optimisée).

🔑 **Rien de nouveau n'est estimé.** `profitAnnual` et `roi` existaient déjà sur chaque projet,
jamais consultés par l'optimiseur. La vitesse et la distance sont déjà dans le modèle
(`roundTripDays` → `carried`, et `GetCargoIncome` paie la rapidité de livraison), et le capital rail
est déjà corrigé du terrain (`RAIL_TERRAIN_FACTOR = 170`). Le même défaut avait d'ailleurs été
trouvé et corrigé **un étage plus bas** (`economy.nut:261`, choix du nombre de convois) sans que
personne ne remonte d'un cran.

### 🔴 Le premier banc était faux, et c'était mon bug — pas celui du code mesuré

Premier banc : **−8,5 % de valeur, −21,1 % de gares** ($t = -2{,}86$). J'ai relu mon implémentation
avant de conclure et trouvé la cause : le chemin « revenu » applique un **bonus fret** à l'ordre de
branchement (×1,40, jusqu'à ×1,89 pour les transformateurs, `projects.nut`), que mon chemin
« profit » ne reprenait pas. Le réglage mesurait donc **deux changements** : le passage au profit
*et* la suppression silencieuse de la préférence fret.

Banc corrigé, mêmes graines, même durée (`docs/bench_knapsack_roi_v2_10y.json`) :

| métrique | témoin | `knapsack_roi=1` | écart | t | graines | p |
|---|---:|---:|---:|---:|---:|---:|
| `company_value` | 1 458 048 £ | 1 517 816 £ | **+4,1 %** | +0,86 | 11/20 | 0,82 |
| `profit` | 56 935 £ | 58 697 £ | +3,1 % | +0,39 | 8/20 | 0,50 |
| `profit_year` | 245 599 £ | 241 370 £ | −1,7 % | −0,24 | 9/20 | 0,82 |
| `n_stations` | 46 | 41 | −11,0 % | −1,86 | 6/20 | 0,12 |

**De −8,5 % à +4,1 % : le défaut expliquait tout l'effet négatif.**
➡️ **Leçon : avant de conclure au rejet, relire ce que le réglage change VRAIMENT.** Un banc
propre sur une implémentation qui change deux choses mesure la somme des deux, et un rejet est
aussi coûteux qu'une adoption à tort — ici il aurait enterré C13.

### Le verdict, et ce qu'il apprend quand même

**Neutre : rien de significatif** ($p = 0{,}82$), défaut laissé à 0. Mais le comportement est
exactement celui qu'on attend d'un objectif de rendement : **−11 % de gares pour +4,1 % de
valeur** — moins de lignes, mieux choisies. C'est le seul bras de la journée qui penche du bon côté.

### ❌ L'interaction prédite n'est PAS au rendez-vous

Le banc du §0 undecies septies avait produit une prédiction falsifiable : sous un objectif de
profit, desserrer la réserve devrait cesser de dégrader le choix. Mesuré : la réserve reste
négative sous objectif profit (**−4,9 %**, $t = -1{,}05$) contre −6,4 % seule. Marginalement moins
mauvaise, mais toujours mauvaise. ➡️ **« La réserve est le budget du sac à dos » n'explique donc
qu'une petite part de son effet.** Ne pas présenter cette hypothèse comme établie.

### 🔴 Le vrai signal de la journée : un optimum local

**Tous les bras de tous les bancs du 2026-09-03 perdent contre le témoin** — réserve, marges,
objectif du sac à dos, dans toutes les combinaisons, sauf `knapsack_roi` seul qui est neutre. Ça
ressemble moins à une série d'échecs indépendants qu'à une **sélection de portefeuille déjà à un
optimum local**, façonnée par les nombreuses mesures antérieures : toute perturbation à un facteur
en tombe.

➡️ **Déplacer la cible : ce n'est plus un paramètre de la sélection, c'est ce qu'on lui donne à
sélectionner.** Le vivier — 61 candidats classés sur 3 parties contre 855 estimés chez AAAHogEx
(§0 undecies sexies bis). Rejoint [[opexai-plafonnement]], dont le second mur est le vivier.

---

## 0 undecies nonies. 🔴 LE VIVIER N'EST PAS AFFAMÉ : il est PLEIN, et 43 % de ses places sont mortes (2026-09-03)

Première mesure directe du vivier. Instrumentation déléguée à agy sous `decision_log`, vérifiée
**identique bit à bit** réglage éteint. Campagne 3 graines × 16 ans, `docs/mesure_vivier.json`,
10 542 décisions.

⚠️ **Corrige un chiffre que j'avais avancé** : « 61 candidats classés contre 855 chez AAAHogEx »
était un artefact de ma propre journalisation (`OpexLogPortfolioRank` plafonne à 5 entrées par
passage). Ne pas le citer.

### 1. Le vivier déborde — la génération n'est pas le goulot

`PROJECT_POOL_K = 128`, et `considered = 128,0` **toutes les années, toutes les graines**, de 1970
à 1985. Le vivier est **saturé à son plafond en permanence**. La génération rail examine
**1 543 paires par passage** pour en garder 120 (7,8 %).

➡️ **« Produire plus de candidats » est sans objet** : tout ce qui dépasse 128 est déjà jeté.
Cohérent avec les deux bancs qui avaient élargi le vivier sans gain
([[opexai-vivier-jointure]] : +37,2 % de véhicules, −0,3 % de valeur).

### 2. La redondance n'est pas le problème non plus — hypothèse réfutée

**126,4 paires distinctes sur 128** en moyenne. Les origines se répètent (35 origines distinctes,
soit ~3,7 candidats par origine) mais aucune paire n'est dupliquée. L'hypothèse « un vivier de 50
dont 40 desservent le même bassin » est **écartée par la mesure**.

### 3. 🔴 Le vrai défaut : 43 % du vivier est structurellement INFINANÇABLE

| | rail | route | **air** | eau |
|---|---:|---:|---:|---:|
| places dans le vivier (moy./passage) | 60 | 11 | **56** | 0 |
| **fois choisi par le sac à dos en 16 ans** | **20** | **6** | **0** | 0 |
| lignes réellement bâties | — | — | **100** | — |

**L'aérien occupe 43 % d'un vivier plafonné et n'est JAMAIS retenu — zéro fois en 16 ans.** Pendant
ce temps la tâche dédiée `_tryBuildAir`, hors portefeuille, en construit 100.

La cause est arithmétique : un projet aérien coûte ~131 000 £ (`PROJECT_DISCARD … need=131038
cash=15985`) contre un `capitalBudget` moyen de **40 000 £**. `OpexProjectSelectAffordable` et le
sac à dos écartent donc tout projet dont `budgetCapital > capitalBudget` — systématiquement, à
chaque passage.

🔑 **Et le vivier est rempli SANS test de finançabilité** (`projects.nut:638`) :

```squirrel
OpexProjectInsert(byBudget, project, "budgetScore", PROJECT_POOL_K);
```

`budgetScore` est une **densité** (revenu par livre). L'aérien y est bien classé — forte densité —
mais **infinançable en valeur absolue**. Le vivier dépense donc 43 % de ses 128 places, puis le sac
à dos une part de ses 64, sur des candidats qui ne peuvent pas être retenus, **en évinçant les
candidats bon marché qui, eux, le pourraient**. C'est ce qui explique `selected ≈ 1,1` par passage
malgré 128 candidats.

### ➡️ La correction qu'il faut mesurer

**Filtrer sur la finançabilité AVANT de tronquer à `PROJECT_POOL_K`, pas après.** Formulation
mode-agnostique et principielle : *ne pas dépenser une place de vivier pour un candidat qui ne peut
pas être financé ce tour-ci.* Ce n'est pas un seuil à desserrer mais une **structure** à corriger —
et la leçon du §0 undecies septies dit que c'est cette catégorie-là qui agit.

⚠️ Deux réserves à ne pas oublier en l'implémentant :
- le budget varie d'un passage à l'autre (30 k£ à 92 k£) ; un filtre trop strict à un passage pauvre
  viderait le vivier. Prévoir une marge, ou filtrer sur le budget **maximal mobilisable**.
- l'aérien est déjà bâti par sa voie dédiée ; le retirer du vivier ne le supprime pas du jeu.

✅ **Implémenté le 2026-09-03, réglage `pool_financeable` (défaut 0, non mesuré) — pas encore
adopté.** `OpexBuildProjects` (`projects.nut:542`) calcule maintenant `capitalCeiling`, le plus
haut `capitalBudget` jamais observé (jamais décroissant, transmis d'une régénération à l'autre via
`this._projects.capitalBudgetPeak`, les deux points d'appel dans `main.nut`) plutôt que
l'instantané du passage — la seconde réserve ci-dessus, réglée en suivant l'option « budget maximal
mobilisable » plutôt que la marge, précisément parce que la régénération a lieu juste après un
achat (creux de trésorerie du cycle) : filtrer sur l'instant aurait presque toujours appliqué le
seuil le plus strict possible. L'admission au vivier (`byBudget`, ligne ~646) rejette maintenant
tout candidat dont `budgetCapital > capitalCeiling` sous `pool_financeable=1`, compté dans
`stats.poolInfundable` et journalisé dans `VIVIER`. La voie aérienne dédiée (`_tryBuildAir`) n'est
pas touchée (première réserve).

🟡 **Mesuré le 2026-09-03 — NEUTRE, `pool_financeable` PAS adopté.**

D'abord contre AAAHogEx (`docs/bench_pool_financeable_3y_20seeds.json`, 20 graines × 3 ans) :
`OpexAI[pool_financeable=1]` perd 0/20 sur tout, `company_value` −86,7 %. Sans valeur en soi — c'est
le même écart structurel que la référence (`−87,8 %`), et un 1v1 contre un adversaire qui gagne déjà
par ~87 % ne peut isoler l'effet d'un seul réglage.

L'isolation qui compte, `pool_financeable=1` contre `pool_financeable=0`, mêmes graines
(`docs/bench_pool_financeable_iso_3y_20seeds.json`) :

| métrique | delta moyen | t | graines gagnées | test des signes (p) |
|---|---:|---:|---:|---:|
| `company_value` | +8,1 % | 1,48 | 13/20 | 0,26 (NS) |
| `profit` (trimestre) | +8,6 % | 0,77 | **16/20** | **0,012** |
| `profit_year` | +11,7 % | 1,52 | 13/20 | 0,26 (NS) |
| `performance_history` | +3,5 % | 0,88 | 11/20 | 0,82 (NS) |
| `median_station_rating` | **−1,6 %** | −1,00 | **5/20** | **0,041** |

Aucune moyenne ne franchit le plancher de détection (~15 % sur `company_value` à n=20,
[[banc_monograine_insuffisant]]). Le test des signes isole deux effets réels sous le plancher des
moyennes : `profit` du dernier trimestre gagne significativement (16/20, p=0,012) — mais c'est la
métrique la plus bruitée, pas `profit_year` ; et `median_station_rating` **perd** significativement
(seulement 5/20, p=0,041) — un coût réel, pas du bruit, dans l'ordre d'objectifs n°3. `company_value`
et `profit_year`, les métriques qui comptent le plus dans l'ordre d'objectifs, restent NON
significatives (p=0,26).

**Verdict du banc : structure correcte (documentée ci-dessus, aucune régression de mécanisme), mais
le gain de profit ne se traduit pas encore en valeur de compagnie mesurable, et coûte une note de
gare mesurable.**

✅ **Adopté quand même le 2026-09-03, décision utilisateur explicite.** `pool_financeable` passe à
`1` par défaut (`main.nut`, `info.nut`) malgré le verdict neutre ci-dessus — la décision assume le
coût mesuré sur `median_station_rating` (5/20, p=0,041) contre le signal de profit (16/20,
p=0,012) et la tendance positive non significative sur `company_value`/`profit_year`. Piste à
creuser si le sujet est repris : le vivier filtré construit-il des lignes plus courtes/moins bien
desservies (d'où la note en baisse) en échange du peu de profit gagné ?

### 4. `origin_served` n'est PAS le motif de rejet dominant

Motifs à la génération, cumulés sur 3 parties × 16 ans :

| motif | rejets |
|---|---:|
| `ratio_too_low` | **95 243** |
| `distance_long` | 72 230 |
| `profit_non_positive` | 49 962 |
| `origin_served` | 22 249 |

La mémoire du projet attribuait le mur du vivier à `origin_served` (« 213 à 242 paires/an »). Il
rejette bien beaucoup, mais **`ratio_too_low` en rejette 4,3 fois plus**. À corriger dans
[[opexai-plafonnement]].

---

## 3 ter. 🔶 AUDIT DE TOUTES LES CONSTANTES EN DUR (demandé le 2026-09-02)

**46 constantes `const` dans `ai/OpexAI/`, contre 35 réglages exposés.** Aucune revue systématique
n'a jamais été faite. Il faut passer chacune en revue et la classer dans l'une de trois issues :
**exposer** (elle est décisionnelle et le banc doit pouvoir la faire varier), **vérifier** (elle
prétend traduire une règle du jeu, il faut confronter au source), ou **étalonner** (elle a été
posée à vue et jamais mesurée).

⚠️ **Ne PAS toutes exposer.** 46 réglages de plus, ce serait 46 configurations mortes de plus, et
le projet a déjà la leçon inverse (§8, suppression de `tree_planting` et de `preplan_queue`
devenus inutiles). N'exposer que ce qu'un banc peut réellement trancher.

### Pourquoi c'est prioritaire : les preuves déjà accumulées

Ce n'est pas une inquiétude théorique — **six constantes se sont déjà révélées fausses ou inertes**
en une seule journée de revue :

| constante | ce qu'on a découvert |
|---|---|
| `MAX_ROAD_VEHICLES = 8` | son propre commentaire, deux lignes plus haut, affirme « **= 2** est la traduction directe de la règle du jeu » |
| `ROAD_SPEED_EFFICIENCY_PCT = 60` | justifié « plus sévère que les 70 % du rail » — **la constante rail a été supprimée depuis** |
| `PROJECT_TOP_K = 64` | **jette 81,6 % des candidats acceptés** (1 152 sur 1 412, mesuré) |
| `PROJECT_POOL_K = 128` | tronqué à 64 juste après : la moitié du vivier coûte des opcodes et **n'est jamais vue** |
| `TARGET_HEADWAY_DAYS = 7` | tombe **exactement sur une frontière de palier** de note de ramassage |
| `maxBatch = 1` | **même pas une constante — un `local`** — et c'est le plafond structurel de toute la croissance (~1 projet/mois, §0 decies) |

### Les quatre familles, et ce que chacune demande

**1. Plafonds** — la famille que l'utilisateur signale, et la plus suspecte : chacun peut brider
silencieusement la croissance sans jamais lever d'erreur.
`MAX_RAIL_TRAINS` 2, `MAX_ROAD_VEHICLES` 8, `MAX_STATION_PLANS` 12, `PROJECT_TOP_K` 64,
`PROJECT_POOL_K` 128, `LOOP_BUDGET_MAX_TASKS` 8, `PAX_NEAR_MAX_ATTEMPTS_PER_YEAR` 1,
`PAX_NEAR_MAX_DISTANCE` 100, `ROAD_MAX_DISTANCE` 25, `PATHFINDER_MAX_COST` 200000,
`CASH_RESERVE_MAX` 25000, `JOIN_PARALLEL_MAX_SIDE` 4, `RAIL_EXPAND_TIMEOUT_DAYS` 120,
`SCRAP_TIMEOUT_YEARS` 2 — **plus les `maxBatch` locaux** (1 pour le portefeuille, 12 ou 3 pour
l'air), qui échappent même à cette liste parce qu'ils ne sont pas des constantes.

**2. Planchers** — symétriques : ils écartent des candidats sans trace.
`ATTEMPT_FLOOR` 2000, `CASH_RESERVE_MIN` 5000, `ROAD_MIN_DISTANCE` 5,
`ROAD_MIN_PROFIT_ANNUAL` 1000, `ROAD_ACCEPTANCE_MIN` 8, `MIN_SEPARATION` 10,
`ORIGIN_SEPARATION` 3, `LOOP_BUDGET_FLOOR` 2000, `PORTFOLIO_REFRESH_MIN_GAIN` 50000,
`PAX_NEAR_MIN_PROFIT` −200, `PROBE_NEAR_ZERO` −1000, `DEAD_STREAK_THRESHOLD` 2,
`RAIL_EXPAND_STREAK` 2.

**3. Calibrations économiques** — les plus dangereuses : elles entrent dans le modèle de décision,
donc une erreur y fausse **tout le classement** sans jamais lever d'exception.
`STATION_RATING_PCT` 50 (son ancre est déjà la question ouverte du §3 bis),
`TARGET_HEADWAY_DAYS` 7, `TOWN_CATCHMENT_SHARE_PCT` 22, `ROAD_SPEED_EFFICIENCY_PCT` 60,
`INFRA_LIFE_YEARS` 30 (hypothèse assumée, le moteur ne modélise aucune durée de vie
d'infrastructure), `RAIL_EXPAND_UTIL_PERMILLE` 850.

**4. Coûts d'opcodes** — mesurés une fois, et le code a beaucoup bougé depuis.
`PROJECT_RAIL_OPS_PER_ITERATION` 2700, `PROJECT_RAIL_TRANSACTION_OPS` 200000,
`PROJECT_ROAD_TRANSACTION_OPS` 287000, `PROJECT_AIR_TRANSACTION_OPS` 100000,
`PROJECT_WATER_TRANSACTION_OPS` 100000, `ROAD_PLAN_ITERATIONS_BASE` 20, `ATTEMPT_MULTIPLIER` 4,
`PATH_CHUNK` 50, `BUILD_TICK_MARGIN` 3000, `STATION_SEARCH_RADIUS` 30,
`RAIL_PLATFORM_GROWTH_WAGONS` 2.
⚠️ Une erreur de dimension y est déjà avérée : les itérations ROUTE sont facturées au tarif du
pathfinder RAIL (§0 septies).

### Méthode proposée

1. **Instrumenter avant d'étalonner.** Pour chaque plafond et plancher, compter **combien de fois
   il mord réellement** — c'est ainsi que `PROJECT_TOP_K` a été confondu. Un plafond qui ne mord
   jamais ne mérite ni réglage ni mesure ; un plafond qui mord 81 % du temps est un choix de
   conception déguisé en détail d'implémentation.
2. **Confronter au source** tout ce qui prétend traduire une règle du jeu (famille 3) — c'est ainsi
   que les seuils de note ont été corrigés.
3. **N'exposer au banc que ce qui reste décisionnel** après les deux étapes ci-dessus, et
   documenter la mesure à côté de la valeur, comme le fait déjà `loan_repay_floor_k`.

---

## 0 duodecies. ✅ LOT A : les quatre correctifs de robustesse (2026-09-02)

`docs/bench_lotA_3y_20seeds.json` : 20 graines × 3 ans, 0 échec, **20/20 graines identiques au bit
près** au banc précédent. Aucune régression — **et aucun bénéfice mesurable non plus**.

| # | correctif | statut au banc |
|---|---|---|
| 1 | garde air : testait `airCombos == null` alors que `_refreshAir` pose toujours une liste ; le seul état qu'elle laissait passer **déréférençait null et tuait l'IA** | jamais déclenché |
| 2 | `dueCycle = _taskCycle` → `+ 1` : empêchait `_taskCycle` d'avancer et gelait `catalog` à jamais | inatteignable aujourd'hui |
| 3 | ferraillage sans fin : seule sortie « plus aucun véhicule », donc un camion injoignable figeait la ligne à vie. Délai `SCRAP_TIMEOUT_YEARS = 2`, panneau `DL\|…\|4` | **chemin jamais exécuté** |
| 4 | ferraillage du voisin : `AIVehicleList_Station` rend tous les véhicules d'une gare partagée. Filtre par les ordres | **chemin jamais exécuté** |

### 🔴 Ce que le banc ne peut PAS dire, et pourquoi

**Zéro événement de ligne morte sur 5 parties × 3 ans** (`docs/diag_vivier_3y.json`) : à cet
horizon, `_scrapDeadLines` ne ferraille jamais rien. Les correctifs 3 et 4 n'ont donc **pas été
exercés une seule fois**. Le « 20/20 identique » prouve l'absence de régression, **pas** la
justesse du correctif.

Les quatre sont des **assurances** : ils empêchent des modes d'échec qui ne se produisent pas dans
les conditions du banc actuel, mais qui sont catastrophiques quand ils surviennent (mort de l'IA
pour le 1, gel définitif pour le 2 et le 3, vente des camions d'une ligne voisine pour le 4). Leur
justification est la **lecture du code**, pas la mesure — et il faut l'assumer comme telle plutôt
que de faire passer un banc plat pour une validation.

🔶 **À faire pour valider 3 et 4 : un banc à 20 ans**, horizon auquel les lignes mortes existent
réellement (les campagnes 20 ans historiques en montrent). À 3 ans, ces chemins sont hors de portée
du banc.

---

## 0 terdecies. LOT D — un seul des trois correctifs de pricing survit (2026-09-02)

Groupés (`docs/bench_pricing_3y_20seeds.json`) les trois dégradaient nettement : `company_value`
−14,8 %, `profit_year` −22,7 %, `performance_history` −18,7 % (t = −3,82). Isolés
(`docs/bench_pricing_isole_3y.json`, 4 bras, 80 parties) :

| réglage | `company_value` | `profit_year` | `performance_history` | verdict |
|---|---:|---:|---:|---|
| `pricing_road_rating` | **−9,9 %** | **−13,5 %** | **−8,2 %** (t −2,20) | ❌ rejeté |
| `pricing_rail_depot` | −4,8 % (t −0,73) | −6,3 % | −1,2 % | ~ non établi, défaut 0 |
| `pricing_road_ops` | +0,8 % | +0,3 % | −0,3 % | ✅ **adopté** (14-16/20 au signe) |

La somme (−9,9 − 4,8 + 0,8 ≈ −13,9) retrouve le −14,8 % du lot groupé : décomposition cohérente.

### 🔴 LA COHÉRENCE ENTRE MODES N'EST PAS AUTOMATIQUEMENT DE LA JUSTESSE

`pricing_road_rating` appliquait à la route la courbe `OpexStationRatingForHeadway` que le rail et
l'air utilisent, au motif que « le même mécanisme physique doit être pricé pareil ». **C'était une
erreur de raisonnement.** La courbe est ancrée sur `STATION_RATING_PCT = 50`, calibré sur des
lignes **RAIL passagers** (mesuré 49-55). L'appliquer à la route suppose qu'un arrêt de bus se
comporte comme une gare : une ligne routière courte y passe de 50 % à **63,7 %**, le modèle devient
plus optimiste, sélectionne des lignes qui ne tiennent pas, et la valeur baisse de 10 %.

➜ **L'écart entre modes encodait une MESURE, pas un oubli.** Avant d'« harmoniser » deux modes,
vérifier si la différence vient d'un calibrage séparé. Cette leçon s'applique directement aux
autres asymétries de la liste D encore ouvertes (amortissement, dimensionnement de rame).

### 🔶 Le cas `pricing_rail_depot` : un coût RÉEL dont la prise en compte dégrade

Le dépôt rail est payé à chaque ligne par `builder_rail.nut` et n'était pas dans le capital
modélisé — la route et l'eau comptent le leur. C'est donc une omission **indiscutable**, et pourtant
la corriger donne −4,8 % (non établi, t = −0,73).

**Lecture la plus probable : le classement s'appuie sur une erreur qui en compense une autre.** Le
coût de voie rail est calculé en distance de **Manhattan**, alors que la voie posée est le résultat
de l'A\* — donc toujours ≥ Manhattan. Le capital rail est ainsi sous-estimé dans un sens, et le
dépôt manquant l'était dans le même sens : ajouter le dépôt seul ne rapproche pas de la vérité, il
déplace le biais.

➜ **Ne pas corriger l'un sans l'autre.** La mesure du détour réel est l'objet du réglage
`rail_cost_probe`, déjà présent : il émet capital modélisé contre coût de construction réel.
**Le mesurer avant de retoucher le capital rail.**

---

## 0 quaterdecies. ✅ LOT C : la télémétrie ne ment plus (2026-09-02)

`docs/bench_lotC_3y_20seeds.json` : 20 graines × 3 ans, 0 échec. **10/20 graines identiques au bit
près**, les 10 autres légèrement déplacées.

| métrique | avant | après | écart | t |
|---|---:|---:|---:|---:|
| `company_value` | 923 277 | 919 592 | −0,40 % | −0,43 |
| `profit_year` | 483 319 | 479 411 | −0,81 % | −0,76 |
| `performance_history` | 307 | 305 | −0,57 % | −0,82 |

⚠️ **Seules 3 graines sur 20 s'améliorent.** L'ampleur est négligeable et aucun `t` n'approche la
significativité, mais ce déséquilibre de signe n'est pas du hasard : c'est le **coût réel** des deux
champs ajoutés au panneau. **La visibilité se paie**, et il faut le savoir avant d'instrumenter à
la légère.

### Les quatre correctifs

1. **Le champ empaqueté ne ment plus.** `rankPacked` s'appelait « rang » mais valait
   `i × TOP_K + taille du portefeuille`. La **valeur n'a pas été changée** — la taille est le nombre
   de projets FINANCÉS, précisément la grandeur qui compte depuis qu'on sait qu'un seul sera bâti
   (§0 decies). Renommé `posPacked`, avec le dépaquetage documenté : `/ TOP_K` = position,
   `% TOP_K` = **taille**, jamais un rang.
2. **Le coût de découverte est réparti.** `airOps` mesure le balayage COMPLET et était attribué à
   *chaque* plan : surestimation d'un facteur N, qui corrompait la mesure même servant à pricer la
   découverte aérienne. Idem pour l'eau.
3. **La troncature du solveur est visible.** `knapsackExact` n'était lu nulle part alors que
   `maxNodes = 2000` pour `n = 64` fait tronquer couramment — impossible de distinguer « optimum
   prouvé » de « budget de nœuds épuisé ». C'est **l'angle mort qui a laissé survivre les quatre
   défauts du portefeuille**.
4. **`budget.nut` a enfin un détecteur de non-réentrance.** L'en-tête la documentait depuis
   toujours, mais `begin()` écrasait sans condition et `end()` rendait 0 en silence : sur ~40 sites
   d'appel, une imbrication future aurait imputé le coût du bloc interne à la catégorie externe,
   sans exception ni trace.

### Le choix de conception, dicté par un précédent mesuré

Les deux indicateurs sont ajoutés au panneau **`IG` existant**, pas dans un nouveau panneau : un
appel `BuildSign` de plus déplace les frontières de ticks — le dépôt a mesuré qu'un helper
interposé devant 57 appels coûtait **3 lignes rail** (16 → 13). Longueur au pire cas vérifiée :
22 caractères, sous la limite de **31 au-delà de laquelle un panneau est refusé EN SILENCE**.

---

## 0 quindecies. ❌ LOT E : la marge aérienne — correctif ESSAYÉ, MESURÉ, ANNULÉ (2026-09-02)

`docs/bench_lotE_air_marge_3y.json`, 20 graines × 3 ans, 0 échec :

| métrique | avant | après | t |
|---|---:|---:|---:|
| `company_value` | 919 592 | **813 840** (−11,5 %) | **−2,66** |
| `performance_history` | 305 | 275 (−9,8 %) | **−3,25** |
| gares | 23,6 | **20,9** (−11,2 %) | −1,64 |
| véhicules | 66,2 | 61,2 (−7,6 %) | −1,44 |

**Annulé.** Retour à l'identique vérifié sur 5 graines.

### Le défaut est réel, le correctif était faux

`_tryBuildAir` dimensionne son budget avec une marge forfaitaire de **2 000 £**
(`maxCapital = money + borrowable − reserve − 2000`) alors que le test d'acceptation exige
`requiredMargin` — **jusqu'à 30 000** pour deux aéroports neufs. Un plan tombant dans cette bande
de 28 000 est donc trouvé au prix d'un balayage complet de sites, puis rejeté, et le `break` gâche
le cycle. Rejoué à l'identique au cycle suivant. **Ce diagnostic reste valide.**

Le correctif essayé — dimensionner au pire cas (30 000), rendant l'acceptation vraie par
construction — **repose sur une erreur de raisonnement** :

> « Un plan trouvé puis rejeté ne construit rien, donc refuser de le planifier est strictement
> meilleur. »

C'est faux. **`maxCapital` n'est pas qu'un filtre : c'est le budget avec lequel `OpexAirPlans`
CHOISIT le plan à proposer.** Le réduire de 30 000 partout appauvrit la sélection dans *tous* les
cas où l'ancienne marge suffisait — en particulier le hub-à-hub, dont la marge réelle n'est que
2 000 et à qui on retranchait donc 28 000 de trop. On échange une boucle bloquée **rare** contre une
dégradation **systématique** du choix de plan.

### 🔴 La leçon, généralisable

**Avant de resserrer un budget « par sécurité », vérifier s'il sert aussi à CHOISIR.** Un paramètre
qui filtre peut être durci sans dommage ; un paramètre qui alimente une optimisation en amont ne
peut pas — le durcir dégrade la solution retenue, pas seulement les candidats écartés. C'est la
même famille d'erreur que « la cohérence entre modes n'est pas de la justesse » (§0 terdecies) :
un raisonnement local correct, faux dans le système.

### La bonne correction, si on y revient

Passer par le **plan**, pas par le budget : soit transmettre la marge exigée à `OpexAirPlans` pour
qu'il l'applique **par plan** (elle dépend de `newAirports`, que lui seul connaît), soit ne pas
`break` sur rejet et réessayer avec un budget raboté. L'avertissement est écrit à côté du `2000`
dans `main.nut` pour que personne ne « corrige » à nouveau à l'aveugle.

### 🔶 Reprise du 2026-09-02 : `air_margin`, la marge appliquée par plan

Analyse de grok (lecture seule) sur les trois branches de `OpexAirPlans` :

- `maxCapital` **ne filtre pas les sites** (`OpexAirFindSite` ne le reçoit pas). Il plafonne la
  seule boucle de dimensionnement de flotte de `OpexAirEconomics` (`builder_air.nut:171-173`),
  donc il décide **combien d'avions** on met sur un plan déjà trouvé — ce qui change ensuite le
  classement `OpexAirPlanBetter`. Le portefeuille passe `maxCapital = 0`, ce qui neutralise
  complètement ce plafond : **ne pas casser ce cas**.
- `OpexAirEconomics` reçoit déjà `newAirportCount` (2 / 1 / 0 selon la branche). La table
  30 000 / 12 000 / 2 000, elle, n'existe qu'**après** le retour, dupliquée en trois endroits
  (`main.nut:687-693`, `projects.nut:91-93`, `main.nut:1039-1042`).
- Option retenue : appliquer la marge **dans la boucle**, pas côté appelant. La boucle est
  monotone (plus d'avions ⇒ plus de capital), donc serrer le plafond par type de plan revient à
  choisir la plus grande flotte finançable avec la **vraie** marge — même mécanisme que le rabot
  global raté, mais au bon grain, donc le hub-à-hub (marge réelle 2 000) n'est plus pénalisé.
- Option écartée : le retry. `OpexAirPlans` ne renvoie qu'un `bestPlan` ; un retry sans changer
  `maxCapital` retrouve le même plan, et un retry avec `maxCapital` global raboté reproduit
  **exactement** le banc annulé.

⚠️ **Risque à surveiller au banc** : le court-circuit `if (bestPlan != null && bestPlan.airport
.allowBig) break;` (`builder_air.nut:479`). Si aucun combo « grand » n'est finançable, les combos
suivants (jusqu'à 5×) s'exécutent au lieu de s'arrêter tôt — surcoût d'opcodes ponctuel.

### ✅ `air_margin` ADOPTÉ le 2026-09-02 — pour la justesse, pas pour la performance

**Banc apparié 20 graines × 3 ans** (`docs/bench_air_margin_3y.json`), contrôle moins variante :

| métrique | écart apparié | t | graines gagnées par le contrôle |
|---|---:|---:|---:|
| `company_value` | +11 126 £ (+1,3 %) | 0,26 | 8/20 |
| `profit_year` | −7 209 £ (−1,6 %) | −0,28 | 6/20 |
| `performance_history` | +9,3 pts (+3,3 %) | 1,16 | 8/20 |
| `median_station_rating` | +3,8 pts (+2,3 %) | 0,81 | 9/20 |

**Neutre sur toute la ligne.** C'est le résultat qu'il fallait obtenir : le rabot global coûtait
−11,5 % (t = −2,66), le même mécanisme appliqué **par plan** ne coûte rien. Défaut passé à 1 sur le
même motif que `pricing_road_ops` — justesse mesurée non nuisible. **Ne revendiquer aucun gain.**

🔴 **Et ça enseigne quelque chose de plus** : le défaut visé était réel (plan trouvé puis rejeté,
cycle gâché) mais sa correction ne vaut rien. Cohérent avec `loop_budget` nul : le gâchis d'un
cycle d'opcodes ne se paie pas. Troisième confirmation que **les opcodes ne sont pas le goulot** —
arrêter de proposer des pistes qui économisent des cycles.

⚠️ **Repère de bruit utile** : le bras de contrôle vaut 919 592 £ au banc `growth_yields` et
874 603 £ ici, à *code de contrôle identique* — seules deux lignes de déclaration ajoutées entre
les deux décalent les frontières de ticks. **Un écart de 5 % sur `company_value` est du bruit de
trajectoire pur**, ce qui reconfirme indépendamment le plancher de détection à ~15 %.

### 🔶 `air_abandon` : `_tryBuildAir` ne mémorisait pas ses échecs (2026-09-02)

Défaut confirmé en lecture : `_tryBuildAir` (`main.nut:639-746`) ne consulte **ni n'alimente**
`_abandonedPairs`. Sur `!result.ok` il fait un simple `break` — et comme `OpexAirPlans` ne renvoie
qu'un seul `bestPlan`, le cycle suivant re-scanne tous les sites pour reproposer **exactement la
même paire** et échouer pareil. Le chemin portefeuille (`main.nut:1050`, `:1072`), lui, mémorisait
déjà. `OpexAirPlans` reçoit désormais un paramètre `abandoned` optionnel et filtre dans ses trois
boucles, **après** les tests de distance et **avant** `OpexAirEconomics` : les paires écartées pour
distance ne paient pas la concaténation de clé, les autres évitent le calcul cher.

### ✅ `air_abandon` ADOPTÉ le 2026-09-02 — le premier vrai gain depuis l'arbre

**Banc apparié 20 graines × 3 ans** (`docs/bench_air_abandon_3y.json`), variante moins contrôle :

| métrique | écart apparié | t | graines gagnées par la variante | test des signes |
|---|---:|---:|---:|---:|
| `company_value` | **+6,05 %** (+55 005 £) | 1,90 | **18/20** | **p = 0,0004** |
| `profit_year` | **+6,83 %** (+33 214 £) | 1,89 | **19/20** | **p = 0,00004** |
| `profit` | +4,00 % | 1,95 | 19/20 | p = 0,00004 |
| `performance_history` | +1,13 % | 0,83 | 19/20 | p = 0,00004 |

Défaut passé à 1.

### 🔴 CONSÉQUENCE DE MÉTHODE : le plancher à 15 % ne vaut que pour les MOYENNES

C'est la première fois qu'une piste passe alors que son `t` reste **sous 2** (1,90 / 1,89 / 1,95).
Le test des signes, lui, est écrasant : 18/20 et 19/20, soit p = 4·10⁻⁴ et 4·10⁻⁵. Les deux tests
ne mesurent pas la même chose :

- Le **t sur la moyenne** est écrasé par la variance inter-graines (CV ≈ 55 % sur `company_value`).
  De là le plancher de ~15 % noté dans [[banc-monograine-insuffisant]].
- Le **test des signes** ignore l'amplitude et ne regarde que la direction. Il voit donc un effet
  **petit et constant** que la moyenne noie.

⚠️ **L'argument qui rend ça valide ici** : la plateforme est déterministe, donc un changement
neutre ne laisse pas les trajectoires en place — il les **rebat**, et le compte de signes tombe à
~10/20. C'est exactement ce qu'ont donné `air_margin` (8/20, 9/20) et `growth_yields` (9/20, 11/20)
quelques heures plus tôt. **19/20 n'est pas du rebattage.**

👉 **À appliquer désormais à tous les bancs appariés** : lire le compte de signes AVANT de conclure
« sous le plancher, invisible ».

### ✅ Relecture de TOUS les bancs appariés sous le test des signes (2026-09-02)

Faite dans la foulée sur les ~40 comparaisons appariées à n = 20 du dépôt, filtrées sur |t| < 2
(celles à |t| ≥ 2 étaient déjà tranchées par la moyenne). Trois acquis.

**⚠️ 1. Un piège dans le test des signes lui-même.** Le compteur `arm_a_beats_arm_b` range les
**ex æquo** du côté de `b`. Un réglage totalement inerte affiche donc un faux **20/20, p < 10⁻⁵** —
le « signal » le plus fort du lot est un artefact. **Toujours exclure les égalités**, ou vérifier
que l'écart-type des différences n'est pas nul.

**✅ 2. `rail_refleet` et `air_starter` sont prouvés INERTES par la mesure.** Écart-type des
différences = **0,0** sur 20 graines (`bench_rail_refleet_vs_aaahogex_5y.json` et `_v2`) : basculer
le réglage ne change pas un bit. Confirmation indépendante de la revue de code (§0 nonies : « TOUTE
la fonctionnalité `rail_refleet` est du code injoignable »). 👉 **Les ajouter à la tâche de ménage
des réglages inutiles du §8**, à côté de `tree_planting`.

**✅ 3. Aucune piste rejetée cette semaine n'était un gagnant caché** — mais deux verdicts se
précisent :

| bras | métrique | écart variante | `t` | signes | p |
|---|---|---:|---:|---:|---:|
| `pricing_road_ops=1` | `profit_year` | **+0,25 %** | −0,14 | **15/20** | **0,041** |
| `portfolio_v2=1` + plancher | `company_value` | −8,83 % | 1,87 | 5/20 | 0,041 |

`pricing_road_ops` avait été adopté sur la seule **justesse dimensionnelle**, son `t` de −0,14
paraissant sans appel. Le signe dit qu'il gagne réellement, petitement et régulièrement :
**l'adoption était mieux fondée qu'on ne le croyait**. Symétriquement, le rejet de `portfolio_v2`
même réparé se renforce — la variante perd 15/20.

---

## 0 sexdecies. ❌ `growth_yields` : REJETÉ, et il apprend quelque chose (2026-09-02)

**Banc apparié 20 graines × 3 ans** (`docs/bench_growth_yields_3y.json`), contrôle moins variante :

| métrique | écart apparié | t | graines gagnées par le contrôle |
|---|---:|---:|---:|
| `company_value` | +42 052 £ (+4,8 %) | 1,33 | 9/20 |
| `profit_year` | −1 357 £ (−0,3 %) | −0,06 | 6/20 |
| `performance_history` | +14 pts (+4,8 %) | 1,91 | 11/20 |
| **`median_station_rating`** | **+15,9 pts (+10,4 %)** | **2,97** | **15/20** |

L'idée était de reprendre `_tryTownGrowth`, qui bâtit des lignes portant un `profitAnnual = 0`
**explicite** (`main.nut`) tout en dépensant du capital réel, et de lui faire céder le pas au
capital déjà engagé par le portefeuille. Sur la valeur : rien. Sur la note de gare : **la variante
perd nettement**, et la graine 2026 s'effondre à `company_value = 1`.

🔴 **Ce que ça enseigne** : le `profitAnnual = 0` de ces candidats est un **compteur faux, pas une
dépense gâchée**. La ville qui grandit alimente les gares déjà construites, et le rendement se lit
sur la note de gare, pas sur le profit prédit de la ligne elle-même. C'est le troisième cas de la
semaine où un compteur à zéro ne prouve rien (cf. `cash_blocks`, §0 decies).

**Ne pas remettre à 1** sans avoir d'abord donné un profit prédit honnête à ces candidats — c'est
ça, la tâche réelle, et elle rejoint l'audit des constantes en dur (§3 ter).
## 0 septdecies. 🔴 REVUE DE `candidates.nut` (étape 6, 2026-09-02) — le vivier lui-même est bridé

Périmètre : génération et filtrage des candidats rail et route (~1 240 lignes). C'est l'étage qui
décide ce qu'OpexAI envisage même de construire — un filtre trop strict y coûte directement du
volume, et le volume est ~85 % de l'écart mesuré contre AAAHogEx. **Les deux trouvailles de tête
sont vérifiées par archéologie git**, pas seulement par lecture du fichier actuel.

### 🔴 1. `MIN_DISTANCE = 25` est une régression silencieuse : la bande 5-24 tuiles est fermée au rail depuis un commit qui ne l'a jamais annoncé (`candidates.nut:20`)

Le code actuel :

```
candidates.nut:20   MIN_DISTANCE <- 25;
candidates.nut:135   if (distance < MIN_DISTANCE) { stats.distanceShort++; return null; }
```

Mais le commentaire d'en-tête du fichier (`:15-19`) et un second commentaire à `:882-887`
décrivent tous les deux, en détail et au présent, un tout autre comportement :

> « Le rail et la route doivent se chevaucher entre 5 et 25 tuiles [...] Le modèle de capital du
> rail le déclasse normalement dans cette bande ; c'est désormais un résultat du ROI, pas un a
> priori d'orchestration. » (`:15-19`)
>
> « Le créneau route reste borné à 5-25 tuiles, **mais le rail descend maintenant à 5** : ce
> chevauchement est volontaire [...] Les modes se disputent donc bien la même PAIRE, et le gagnant
> est celui au meilleur ROI. » (`:882-887`)

Aucun des deux textes n'est vrai du code livré : avec `MIN_DISTANCE = 25`, aucun candidat rail
n'est jamais généré sous 25 tuiles, donc le rail ne "descend" nulle part et ne dispute jamais la
bande où la route (`ROAD_MIN_DISTANCE = 5`, `ROAD_MAX_DISTANCE = 25`) opère seule. Vérifié par
`grep` : `MIN_DISTANCE` n'est lié à aucun réglage `info.nut` / `AIController.GetSetting` (contrairement
à `STATION_JOIN`, `JOIN_PLACE`, `BASIN_SHARE`, etc., tous lus en `main.nut:3091-3116`) — c'est une
constante fixe, jamais un bras de banc.

**Historique reconstitué (`git log -p`)** :
- `3467851` (« orchestrer les projets par ROI budget et opcodes ») fait passer `MIN_DISTANCE` de
  25 à 5 *délibérément*, en remplaçant l'ancien commentaire (« sous 25 tuiles le profit MEDIAN
  mesuré est négatif [...] Ce n'est pas une précaution, c'est une mesure ») par celui qu'on lit
  encore aujourd'hui à `:15-19`. C'est ce commit qui a aussi réécrit le commentaire de `:882-887`
  pour annoncer le chevauchement 5-25.
- `31b13bad` (« modèle de ROI cinématique véhicule, maillage multi-époques et saturation de
  flotte ») repasse `MIN_DISTANCE` de 5 à 25 **sans toucher un seul mot des deux commentaires**, et
  sans aucune justification dans le message de commit ni dans le diff environnant. Rien n'indique
  une mesure qui aurait motivé ce retour en arrière — le commit mélange par ailleurs des
  changements sans rapport (cinématique véhicule, feeders, flotte), ce qui a très probablement
  masqué la régression.

➜ **Effet** : la bande 5-24 tuiles — celle que le fichier lui-même documente comme un chevauchement
volontaire entre rail et route, jugé nécessaire pour "choisir le meilleur mode pour un même couple
origine/destination" — est aujourd'hui fermée à 100 % au rail, sans arbitrage ROI possible. Le même
`MIN_DISTANCE` ferme aussi cette bande à `OpexPlaceJoinPax`/`OpexPlaceJoinFreight` (`:510`, `:574`,
`:609`, réglage `join_place`, défaut 0). Je ne peux pas chiffrer l'effet sur `company_value` sans
banc — la note `mecanique_jeu.md`/git ne dit pas quelle fraction des paires réelles tombe dans
cette bande — mais c'est un pan entier de l'espace de candidats rail, fermé par accident plutôt que
par conception, exactement le genre d'écart qui coûte du volume. À mesurer avant de trancher :
restaurer `MIN_DISTANCE = 5` et comparer au banc appairé.

### ❌ MESURÉ le 2026-09-02 : rouvrir la bande ne paie PAS — défaut réel, correctif sans effet

Banc apparié 20 graines × 3 ans (`docs/bench_rail_min_distance_3y.json`), `MIN_DISTANCE` devenu le
réglage `rail_min_distance` (commit `8c627d0`), variante = 5 :

| métrique | variante | `t` | signes | p |
|---|---:|---:|---:|---:|
| `company_value` | −0,60 % | 0,12 | 8/20 | 0,50 |
| `profit_year` | −1,00 % | 0,17 | 7/20 | 0,26 |
| `performance_history` | +1,62 % | −0,39 | 9/20 | 0,82 |
| `profit` | −5,75 % | 0,61 | 11/20 | 0,82 |
| `median_station_rating` | +1,52 % | −0,40 | 10/20 | 1,00 |

**8/20, 9/20, 11/20, 7/20, 10/20 : la signature exacte du rebattage de trajectoires.** Le réglage
n'est pas inerte (les valeurs par graine diffèrent, contrairement à `rail_refleet` dont l'écart-type
des différences est nul) — il agit, mais son effet est de signe aléatoire. **Défaut laissé à 25.**

🔴 **Lecture probable — et elle est écrite dans le commentaire d'origine** : « le modèle de capital
du rail le déclasse *normalement* dans cette bande ; c'est désormais un résultat du ROI, pas un a
priori d'orchestration. » L'intention était d'ouvrir la bande **en sachant que le rail y perdrait**
contre la route à l'élection modale (`projects.nut:127`). Le banc dit qu'il perd effectivement : le
filtre supprimait en amont ce que l'élection supprimait en aval. **Filtre REDONDANT, pas nuisible.**
⚠️ Non vérifié — le confirmer demanderait d'instrumenter combien de candidats 5-24 atteignent
l'élection modale et la perdent.

👉 **Conséquence de priorisation** : « un pan entier de l'espace de candidats est fermé » ne suffit
pas à prédire du volume. Ce qui est fermé peut être ce qu'on aurait rejeté ensuite. Les deux autres
trouvailles de la revue (§0 octodecies : aucune ligne rail n'a jamais 2 trains ; `maxBatch = 1`)
touchent le RÉEL construit, pas l'espace envisagé — les traiter en premier.

### 🔴 2. Les bonus de `ratio`/`roi` du fret (monopole +40 %, chaîne +35 %) ne changent RIEN à la construction réelle ; le bonus feeder (+60 %) n'agit qu'à moitié (`candidates.nut:190-199`, `:229`, `:1178-1181`)

`OpexMakeCandidate` calcule un `adjustedRoi` local qui empile trois bonus commentés comme des
signaux de priorisation réels :

```
candidates.nut:183-188  turnoverBonus (rotation de cash)
candidates.nut:190       adjustedRoi = (economics.roi * turnoverBonus) / 100
candidates.nut:192-193   fret : adjustedRoi *= 1.40   // "monopole d'exploitation absolu"
candidates.nut:195-196   transformateur : adjustedRoi *= 1.35   // "bonus de chaîne industrielle"
candidates.nut:199       ratio = opcodeRatio + (adjustedRoi * 15)
```

Mais le champ renvoyé dans l'objet candidat n'est PAS `adjustedRoi` : `candidates.nut:229` écrit
`roi = economics.roi` — le ROI **non bonifié**. Les bonus fret (+40 %, +35 %) ne survivent que dans
`ratio`, un champ que j'ai vérifié par recherche exhaustive (`grep -n "\.ratio\b" ai/OpexAI/projects.nut`,
`ai/OpexAI/main.nut`) : **zéro occurrence dans `projects.nut`**, et les deux seules occurrences dans
`main.nut` (`:990`, `:1213`) sont à l'intérieur de `_tryPreplan`, une des cinq fonctions mortes de
la §0 sexies. `projects.nut` calcule ses propres `budgetScore`/`opcodeScore` (`:70-71`, `:95-96`,
`:116-117`) uniquement à partir de `candidate.revenueAnnual` — jamais de `candidate.ratio` — et
l'élection modale par couple O/D (`:127`, `OpexProjectModeBetter`, confirmée §0 septies) compare
`candidate.roi`, qui reste la valeur non bonifiée. **Les bonus fret +40 % et +35 % sont donc
entièrement cosmétiques pour la décision de construction réelle** : ils ne déplacent que
`OpexTopK`/`.best`, déjà établi ci-dessus comme ne nourrissant que du code mort et de la
signalisation.

Le bonus feeder routier est différent et partiellement vivant : `OpexRoadFeederCandidates`
(`:1178-1181`) écrit directement `candidate.roi = (candidate.roi * 160) / 100` **après**
construction du candidat — donc CE bonus atteint bien `roi` et peut influencer l'élection modale
(`projects.nut:127`). Mais il ne touche ni `revenueAnnual` ni `capital`, donc il n'a aucun effet
sur `budgetScore`/`opcodeScore` ni sur l'objectif du sac à dos (`currentRevenue`, §0 septies) : le
commentaire "Bonus ROI pour la valeur réseau apportée au Hub (+60 %)" décrit un effet plus large
que celui réellement câblé.
➜ Même famille que les sept cas déjà recensés (garantie de commentaire non implémentée), avec un
mécanisme neuf : le bonus vit dans un champ (`ratio`/`adjustedRoi`) que la couche de décision réelle
ne lit jamais, sauf quand — comme pour le feeder — il est aussi écrit directement dans `roi`.

### Le reste

| gravité | lieu | problème |
|---|---|---|
| MOYEN | `:166-170` + `:188` | Une même condition (`distance > 105`) déclenche **deux pénalités indépendantes et non recalibrées** empilées sur une table déjà calibrée (`KNOT_ITERATIONS_V1/V2`) : `iterations *= 2` (`:167`) ET `turnoverBonus` divisé par 2 (`:188`), qui baisse à son tour `adjustedRoi` puis `ratio`. Introduit par `7fbe55e` (« branchement portefeuille ROI multimodal ») sans commentaire ni mesure justifiant le facteur. Comme établi au point 2, cet empilement n'affecte de toute façon que `ratio` (mort pour la décision), mais si les bonus étaient un jour reconnectés (ou pour la lecture diagnostic `OpexBands`), il sur-pénaliserait le long deux fois pour la même raison. |
| FAIBLE | `:455-459` | `OpexShareBasin` : `amount / (n + 1)` est une division entière Squirrel — perte de fraction à chaque partage de bassin. Inactif par défaut (`basin_share = 0`), donc sans effet sur le banc de référence, même famille que les divisions entières déjà trouvées dans `projects.nut`/`economy.nut`. |

### ✅ Vérifié comme n'étant PAS un bug — ne pas re-litiger à la passe de correction

Aucune closure imbriquée dans `candidates.nut` (recherche exhaustive de fonctions anonymes :
zéro résultat) ni `AIAccounting` imbriqué — le piège Squirrel de la consigne ne s'applique pas à ce
fichier. `OpexTopK` (`:335-348`) : logique d'insertion/troncature correcte, pas d'erreur de borne.
`TOP_K`/`ROAD_TOP_K` (`.best`) **ne bornent pas** la construction réelle : `projects.nut:280-282`
puis `:316-319` consomment `rail.candidates`/`road.candidates` (la liste `all`, non tronquée) ;
`.best` n'alimente que les fonctions mortes (`_tryBuild`, `_tryPreplan`) et la signalisation
(`_reportYear`, panneau `OX`) — vérifié par recherche exhaustive des usages de `.best` dans
`main.nut`. `ROAD_MIN_PROFIT_ANNUAL` (`:911`, `:955`) ne rejette plus rien, conforme à son
commentaire — seul `profitAnnual <= 0` rejette (`:951-954`). Le seuil `value >= 8` de
`OpexRailOriginSitable` (`:114`) est cohérent avec la règle des huitièmes d'unité du moteur, déjà
vérifiée ailleurs. Les réglages `station_join`, `join_place`, `origin_sitable`, `basin_share`,
`probe_negative`, `pax_near`, `astar_cost` sont bien tous lus depuis `AIController.GetSetting`
(`main.nut:3091-3116`) et tous à leur défaut mesuré 0 (sauf `complex_cargo` = 1) : le bras par
défaut du banc de référence n'active aucune de ces relaxations, donc leurs propres bugs connus
(déjà couverts par les verdicts de banc cités dans `info.nut`) ne changent rien à la mesure
−87,8 %.

⚠️ Rien n'est corrigé ni mesuré. Le mécanisme est établi, pas son effet.

---

## 0 octodecies. 🔴 REVUE DES CONSTRUCTEURS MODAUX (étape 7, 2026-09-02) — la question des 2 trains tranchée, et c'est pire que prévu

Périmètre : `builder_rail.nut` (~1 340 l.), `builder_road.nut` (~860 l.), `builder_air.nut`
(~625 l.), `builder_water.nut` (~450 l.). Objectif premier : trancher la question laissée ouverte
par la §0 octies/nonies sur la variante « 2 trains ».

### 🔴 1. RÉPONSE À LA QUESTION OUVERTE : `OpexBuildLine` ne pose JAMAIS de seconde voie ni de second train à la construction initiale — le garde-fou interroge une gare qui n'existe pas encore (`builder_rail.nut:426-428`)

**Verdict, avec les lignes à l'appui.** `OpexBuildLine` (`:1154-1173`) ne met jamais deux convois
sur une voie unique — sur ce point précis la §0 octies avait tort de le redouter. Mais il ne pose
pas non plus de seconde voie dédiée : la tentative de doublement est structurellement condamnée à
échouer, pour toute ligne neuve, à cause d'un ordre des opérations.

Chaîne exacte :

```
builder_rail.nut:1154  OpexBuildLine(...)
builder_rail.nut:1160    plan = OpexPlanRailRoute(...)          <- PLANIFIE, ne construit rien
builder_rail.nut:1173    return OpexExecuteRailPlan(...)        <- CONSTRUIT pour de vrai

builder_rail.nut:943    dans OpexPlanRailRoute, si candidate.trains > 1 :
builder_rail.nut:954      dual = OpexTryDoubleTrack(catalog, planA, planB, tiles, null, 0, ...)

builder_rail.nut:426     dans OpexTryDoubleTrack :
builder_rail.nut:426       stationIdA = AIStation.GetStationID(planA.anchor)
builder_rail.nut:427       stationIdB = AIStation.GetStationID(planB.anchor)
builder_rail.nut:428       if (!IsValidStation(stationIdA) || !IsValidStation(stationIdB)) return acc;  // acc.ok reste false
```

`OpexTryDoubleTrack` est appelé depuis `OpexPlanRailRoute` — donc **avant** qu'une seule gare ait
été posée : la construction réelle (`AIRail.BuildRailStation`) n'a lieu que plus tard, dans
`OpexExecuteRailPlan` (`:1015-1018`). Pour une ligne neuve (le cas normal, et le seul avec
`STATION_JOIN = 0` par défaut), `planA.anchor`/`planB.anchor` ne portent encore aucune gare :
`AIStation.GetStationID` y renvoie `STATION_INVALID`, `IsValidStation` renvoie faux des deux côtés,
et `OpexTryDoubleTrack` retourne `acc.ok = false` **à son tout premier test**, avant même de
chercher un tracé. `candidate.railPlan` n'est jamais pré-rempli (`_tryPreplan` est mort, §0 sexies),
donc ce chemin s'exécute à chaque construction réelle, sans exception.

Conséquence tracée jusqu'au bout dans `OpexExecuteRailPlan` :

```
builder_rail.nut:891    plan.doubleTrack = 0            (valeur initiale dans OpexPlanRailRoute)
builder_rail.nut:958-966  if (dual.ok) { plan.doubleTrack = 1; ... }   <- jamais atteint
builder_rail.nut:1050   local want = 1;                 (valeur initiale dans OpexExecuteRailPlan)
builder_rail.nut:1054   if (plan.doubleTrack == 1 && ...) { ... }      <- jamais vrai
builder_rail.nut:1073     want = candidate.trains > 2 ? 2 : candidate.trains;  <- jamais atteint
builder_rail.nut:1100   trains = OpexBuildTrains(..., wanted = 1, ...)
builder_rail.nut:1103   if (... && want == 2 && depot2 != null) { ... }  <- jamais vrai (want=1, depot2=null)
```

**Toute ligne rail construite par OpexAI — quel que soit `candidate.trains` prédit par
`economy.nut` (1 ou 2) — sort de `OpexBuildLine` avec exactement UNE voie et UN train.** Ce n'est
pas juste un défaut de tarification (comme le formulait la §0 octies) : la variante « 2 trains »
**n'existe physiquement jamais** à la construction. Et comme `RAIL_EXPAND`/`RAIL_REFLEET` sont
confirmés injoignables (§0 nonies finding 1), il n'existe **aucun** chemin vivant, ni à la
construction ni après coup, par lequel une ligne rail obtienne un second train.

**Ce que ça change à la lecture de la §0 octies.** `infraCost` constant sur `trains=1/2`
(`economy.nut:193`) n'est donc pas un capital sous-compté pour une ligne réellement doublée : cette
ligne n'existe pas. Le vrai dommage est en amont, sur la PRÉDICTION : `economy.nut` choisit
`trains=2` dès que ça maximise le profit absolu (§0 octies finding 2), ce qui gonfle
`profitAnnual`/`revenueAnnual`/`capital` du candidat retenu par le classement modal (`roi`,
§0 septies) et par le sac à dos (`currentRevenue`) — mais la ligne construite ne livre jamais que la
capacité et le revenu d'UN SEUL train. C'est un écart prédit/réel systématique sur toute ligne où le
modèle a préféré 2 trains, pas une erreur de capital ponctuelle. Je ne peux pas quantifier la part de
`profitAnnual` concernée sans instrumenter combien de candidats retenus ont `trains == 2` — à
mesurer avant de corriger — mais le mécanisme est net et touche potentiellement une majorité des
lignes rail (2 trains maximise presque toujours le profit absolu par construction du modèle).

**Nuance utile pour la correction.** `OpexUpgradeRailLineToDoubleTrack` (`:1180-1317`, la fonction
morte de la §0 nonies) N'A PAS ce défaut : elle tourne sur une ligne **déjà construite**, donc
`AIStation.GetStationID(line.stationA)` (`:1192`) y résout une vraie gare. Si `RAIL_EXPAND` était un
jour réactivé, ce chemin de mise à niveau a priori fonctionnerait pour doubler une ligne existante —
contrairement au chemin de construction initiale, qui resterait cassé indépendamment.

### ✅ MESURÉ le 2026-09-02 : mécanisme CONFIRMÉ, enjeu MARGINAL — ne pas corriger maintenant

Diagnostic de comptage avant d'écrire le moindre correctif (`sweeps/opex_two_trains_diag.py`,
résultat dans `docs/opex_two_trains_diag.json`, 8 graines × 3 ans, `rail_cost_probe=1`). La sonde
existait déjà : `main.nut:1332` émet `DC|idx|capital|actualCost|candidate.trains|result.trains|result.doubleTrack`.
**Aucun code d'IA modifié pour mesurer.**

| grandeur | résultat |
|---|---|
| lignes rail construites (8 parties) | **21** |
| `result.trains` | **1 sur 21/21** |
| `result.doubleTrack` | **0 sur 21/21** |
| `candidate.trains == 2` | **1 sur 21 (4,8 %)** |

✅ **Le mécanisme de la trouvaille n°1 est confirmé par la mesure** : aucune ligne rail ne reçoit
jamais de seconde voie ni de second train. La lecture de code était juste.

🔴 **Mais sa portée annoncée est RÉFUTÉE.** La revue écrivait que « 2 trains maximise presque
toujours le profit absolu par construction du modèle » et que le défaut touchait « potentiellement
une majorité des lignes rail ». La mesure dit **4,8 %**. Explication la plus probable :
`economy_fix` (adopté le 2026-09-02) a changé la sélection du nombre de trains pour comparer le
**ROI** d'abord au lieu du profit absolu (§0 octies trouvaille 2) — et le ROI préfère un train.
**Le correctif de la veille avait déjà neutralisé l'essentiel de ce défaut-ci sans qu'on le sache.**

Sur la seule ligne concernée (graine 7) : capital prédit 66 183 £ pour un coût réel de 45 585 £,
soit **31 % de surestimation** — le mécanisme est bien réel, il est simplement rare.

👉 **Décision : ne pas corriger l'ordre des opérations de `OpexTryDoubleTrack` maintenant.** À
4,8 % des lignes rail, l'effet est très en dessous du plancher de détection et le correctif touche
le chemin de construction le plus délicat du dépôt. Garder la trouvaille documentée pour le jour
où `RAIL_EXPAND` serait réactivé, ou si la sélection du nombre de trains changeait à nouveau.

⚠️ **Datum secondaire, plus inquiétant que la trouvaille elle-même** : **21 lignes rail pour 8
parties de 3 ans**, soit 2,6 par partie — et la graine 1 n'en construit **aucune**. À comparer aux
107-183 gares d'AAAHogEx. Le rail est une part minuscule de notre volume, ce qui recentre l'effort
sur `maxBatch` et sur les modes qui produisent réellement du volume.

### Le reste

| gravité | lieu | problème |
|---|---|---|
| FAIBLE (latent) | `builder_rail.nut:1055` vs `:1083` | Dans le bloc mort ci-dessus, si `plan.doubleTrack == 1` devenait un jour atteignable : `dCosts = AIAccounting()` (`:1055`) n'est fermé par `.GetCosts()` (`:1072`) que dans la branche `okD` réussie. Si `okA2 && okB2` échoue, ou si `conn2`/`depot2` échoue, `dCosts` n'est jamais finalisé avant que `postPathCosts = AIAccounting()` (`:1083`) n'ouvre un second compteur — la consigne « `AIAccounting` ne s'imbrique pas » serait violée. Sans effet aujourd'hui : ce chemin n'est jamais atteint (finding 1). |
| MOYEN | `builder_water.nut:255` | `offered = (monthlyPax * STATION_RATING_PCT) / 100` : le mode eau utilise, comme la route (§0 octies, `economy.nut:363`), le pourcentage **plat** au lieu de `OpexStationRatingForHeadway(headwayDays)` que le rail (`economy.nut:199`) et l'air (`builder_air.nut:175`) appliquent tous les deux. Site distinct de celui déjà trouvé en §0 octies (l'économie de l'eau vit dans `builder_water.nut`, hors du périmètre audité alors) : même famille de bug, nouvel endroit. Effet probablement faible en valeur absolue (le mode eau est rarement construit — un seul bateau par ligne, pas de flotte), donc je ne le classe pas HAUT malgré la parenté avec un bug déjà classé HAUT pour la route. |
| FAIBLE | `builder_air.nut:519`, `:542` | `AITile.LevelTiles` est appelé pour de vrai à la construction (hors `AITestMode`), sans que son coût soit reflété dans `capital`/`amortAnnual` calculés par `OpexAirEconomics` (`:172`, qui ne compte que `newAirportCount * airport.price + planes * plane.price`). Sous-estimation de capital du même ordre que celle déjà connue pour le dépôt rail (§0 octies, `economy.nut:193`) ou l'infrastructure eau — jamais le tracé complet, donc pas quantifié ici. |

### ✅ Vérifié comme n'étant PAS un bug — ne pas re-litiger à la passe de correction

Aucune closure imbriquée ni usage imbriqué d'`AIAccounting` dans `builder_road.nut`,
`builder_air.nut`, `builder_water.nut` (recherche exhaustive : zéro fonction anonyme, zéro
`AIAccounting` dans les trois fichiers). Les usages séquentiels d'`AIAccounting` dans
`builder_rail.nut` (`:475`, `:1006`→`:1043`, `:1265`) sont correctement fermés avant le suivant sur
le chemin réellement atteint. Les corrections déjà en place dans `builder_road.nut`, vérifiées
contre le source du moteur (`road_cmd.cpp:1151`, `script_road.cpp:524`) pour le bit de route manquant
sur `front` avant `BuildRoadDepot`/`BuildRoadStation`, et le remplacement du prédicat de succès API
par `AreRoadTilesConnected` (vérifié correct sur les tuiles `MP_STATION`/dépôt dans `road_map.cpp`),
sont saines et n'ont révélé aucune régression à la relecture. `OpexRoadTraceBuildable`,
`OpexRoadFindDepot`, `OpexRoadTryJoinStop` valident chaque arête sous `AITestMode` puis la
reconfirment par connectivité réelle après pose — aucun cas où un retour API est pris pour argent
comptant. `OpexWaterFindDockAccess` relit les fronts d'accès après construction réelle plutôt que de
faire confiance au plan initial — correct. `OpexUpgradeRailLineToDoubleTrack` (`:1180`, code mort)
n'est pas affectée par le défaut du finding 1 : elle interroge une gare qui existe déjà.

⚠️ Rien n'est corrigé ni mesuré. Le mécanisme est établi, pas son effet. Le finding 1 répond à la
question posée pour l'étape 6-9 : ce n'est pas un écart de capital ponctuel, c'est une variante « 2
trains » qui n'a jamais existé dans aucune partie jouée avec les défauts livrés.

---

## 0 novemdecies. REVUE DE `catalog.nut` (étape 8, 2026-09-02) — fichier le moins prioritaire, peu de décisions, deux défauts mineurs confirmés

Périmètre : `catalog.nut` (~740 l.), étage 0 (matériel roulant, terrain, cargos). Comme annoncé dans
le brief, ce fichier interroge l'API dynamiquement plutôt que d'encoder des décisions, et c'est ce
qu'on observe : les formules physiques (`OpexRailForce`, `OpexRailResistance`,
`OpexRailCruiseSpeed`) sont **vérifiées ligne à ligne contre leur duplication en boucle serrée**
(`:363-389`, la version « déroulée sans fermeture » pour l'étage 1) — les deux versions calculent
rigoureusement la même chose, aucune dérive trouvée entre elles. L'indexation
`choices[maxWagons - 1]` côté consommateur (`economy.nut:138`) correspond exactement à
`choices.append(best)` pour `wagons = 1..maxWagons` côté catalogue (`:350-404`) : pas d'erreur
d'un cran. Aucun filtre ici ne coûte de volume au sens de la §0 decies — ce fichier ne rejette pas
de candidats, il prépare seulement les données que `candidates.nut`/`economy.nut` utilisent.

### Le reste

| gravité | lieu | problème |
|---|---|---|
| FAIBLE | `:702-720` + `:651` | `OpexCatalog::refresh()` appelle `_refreshTowns()` (`:711`) **avant** `_refreshRail()` (`:719`), mais `_refreshTowns()` lit `this.railCoverage` (`:651`) pour dimensionner le test d'acceptation des cargos urbains complexes — un champ que seul `_refreshRail()` renseigne. Chaque année, `_refreshTowns` utilise donc la valeur de `railCoverage` laissée par l'année **précédente** (ou le défaut de constructeur 0 → repli `: 4` la toute première année), pas celle de l'année courante. Effet probablement nul en pratique : `AIStation.GetCoverageRadius(AIStation.STATION_TRAIN)` est un rayon fixé par les réglages de partie, pas une grandeur qui évolue avec le parc — donc la valeur « en retard d'un an » est presque toujours identique à la valeur courante. Reste un ordre d'exécution fragile : si un futur réglage ou NewGRF faisait varier ce rayon en cours de partie, ce serait silencieux. |
| FAIBLE | `:651` | `AITile.GetCargoAcceptance(tile, cargo, 2, 2, ...)` teste l'acceptation urbaine avec une empreinte fixe **2×2**, alors que les tests d'acceptation équivalents ailleurs dans le dépôt (`candidates.nut:1117` pour la route, `OpexRailOriginSitable` pour le rail) utilisent **1×1**. Aucun commentaire ne justifie ce choix précis. `AITile.GetCargoAcceptance` dépend surtout du rayon, peu de l'empreinte, donc l'effet est probablement marginal — mais l'incohérence n'est pas expliquée et vaut la peine d'être alignée par cohérence si `complex_cargo` est un jour retravaillé. |

### ✅ Vérifié comme n'étant PAS un bug — ne pas re-litiger à la passe de correction

Aucune closure imbriquée ni `AIAccounting` dans `catalog.nut` (recherche exhaustive : zéro
résultat). Le piège `CanRunOnRail`/`HasPowerOnRail` (`:290-298`) et son équivalent routier
`CanRunOnRoad`/`HasPowerOnRoad` (`:588-589`) sont correctement appliqués — les deux prédicats sont
exigés, pas un seul. L'optimisation « le plus rapide sature son plafond, donc les moteurs à
plafond inférieur sont sautés » (`:329-334`, `:356-358`, `:381`) est mathématiquement saine : elle
ne s'active qu'après preuve que `railLocos[0]` atteint son propre plafond, et les ex æquo de
plafond restent tous évalués — vérifié par relecture de la condition de saut. `OpexRailNominalMaxWagons`/`OpexRailPlatformLengthForWagons` sont bien des inverses entiers l'un de
l'autre sur le domaine testé. La dichotomie de `OpexRailCruiseSpeed` (et sa version déroulée) est
une recherche binaire standard sur prédicat monotone, sans boucle infinie possible. Le
rafraîchissement conditionnel du catalogue routier à `road_mode = 0` (`:733-737`) préserve bien le
chemin d'opcodes de la baseline rail, conforme au commentaire.

⚠️ Rien n'est corrigé ni mesuré. Bloc traité par exhaustivité de méthode, pas parce qu'il portait un
enjeu de l'ordre du plancher de détection du banc : aucune des deux trouvailles FAIBLES ci-dessus
n'est présentée comme un gain probable.

---

## 0 vicies. ❌ `maxBatch = 1` : MESURÉ, REJETÉ — et le plafond ne retenait rien (2026-09-02)

L'item de tête du backlog (« le seul candidat restant qui touche le volume global »). Mesuré avant
d'être levé, puis levé, puis mesuré. Réglage `portfolio_max_batch` (`info.nut`), défaut **1**.

### 1. Ce que coûtait le plafond, lu dans les données existantes

`docs/diag_vivier_3y.json` contenait déjà les 105 panneaux `IG|` et les 43 `IP|` : **aucune
campagne nouvelle n'était nécessaire** pour chiffrer le plafond. Même angle mort qu'en §0 decies.

| graine | portefeuilles | Σ projets financés | tentatives | ratio |
|---:|---:|---:|---:|---:|
| 42 | 16 | 25 | 8 | 3,1 |
| 100 | 18 | 22 | 7 | 3,1 |
| 7 | 23 | 80 | 12 | 6,7 |
| 999 | 22 | 54 | 10 | 5,4 |
| 2026 | 26 | 22 | 6 | 3,7 |
| **total** | **105** | **203** | **43** | **4,7** |

Distribution de `budget_selected` : `{0:21, 1:35, 2:22, 3:12, 4:6, 5:3, 6:2, 7:1, 8:2, 14:1}`.
**La médiane est 1** : sur 56 générations sur 105, le plafond ne coûte rigoureusement rien. Il ne
mord que sur les 49 qui financent ≥ 2. Par année, tentatives **19 → 16 → 8** : la construction
décélère pendant que le capital croît.

### 2. 🔴 Le banc : rejeté (20 graines × 3 ans, `docs/bench_portfolio_max_batch_3y.json`)

| métrique | écart (4 contre 1) | t | test des signes |
|---|---:|---:|---|
| `company_value` | **−3,8 %** | −1,77 | 3 gagnantes / 6 perdantes / **11 nulles** (p = 0,51) |
| `profit_year` | −4,8 % | −1,54 | 3 / 6 / 11 |
| `n_stations` | −7,9 % | −2,04 | 2 / 8 / 10 (p = 0,11) |
| `n_vehicles` | −9,5 % | **−2,94** | 2 / 8 / 10 (p = 0,11) |

**11 graines sur 20 sont des nuls EXACTS** : chez elles le batch ne se déclenche jamais. Le reste
est défavorable, et significativement sur le volume.

### 3. 🔴 POURQUOI c'est nul — le mécanisme, vérifié aux panneaux

Instrumentation ajoutée : `IB|` reçoit un champ terminal `|B<n>` = projets réellement bâtis dans le
passage (aucun `BuildSign` supplémentaire ; 30 caractères sur 31).

**a) Le batch fusionne des cycles, il n'en ajoute pas.** Un passage RÉUSSI régénère lui-même le
portefeuille (`main.nut:1520`). Bâtir 2 projets dans un passage remplace donc deux cycles par un.
Mesure : le nombre de tentatives **baisse** (0/5 graines en hausse à `batch=8`).

**b) Le batch ne dépasse jamais DEUX, même réglé à 8** (`docs/diag_batch8_5seeds.json`, 14 passages
avec chantier : `{1: 10, 2: 4}`), alors que la graine 7 a un portefeuille qui finance 17 projets.

**c) La cause : la caisse est vidée entre deux passages par les tâches concurrentes.** Graine 42,
janvier 1970 :

```
portefeuille #0 : capital mobilisable 295 000 -> 5 projets finances (282 578)
   chantier unique du passage : une ligne de bus a 26 589 £
portefeuille #1 : capital mobilisable  24 013 -> 1 projet finance
```

245 000 £ ont disparu sans passer par le portefeuille : `_tryBuildAir` est une **tâche séparée**,
avec son propre `maxBatch = 3` (12 en starter), et elle a posé une liaison aérienne la même année
(`air_attempts`, `reason OK`, distance 161) — **aucun panneau `IP|`**, donc hors portefeuille. Plus
deux lignes rail de 96 et 63 tuiles. L'emprunt est au plafond dès février.

👉 **Le vrai goulot n'est pas le plafond de batch, c'est la CONCURRENCE POUR LA CAISSE** entre le
portefeuille et les tâches qui dépensent en parallèle. Le sac à dos planifie contre 295 k£ qu'il
croit siens et n'en retrouve que 24 k£ au passage suivant. C'est le prolongement direct de
§0 decies (vitesse du capital) et de §0 undecies (la ruée aérienne d'AAAHogEx).

### 4. 🔴 Défaut trouvé en chemin : le parseur ne lisait PLUS les portefeuilles

`RE_IG` (`sweeps/opex_full_campaign.py:49`) est ancré par `$` et attend 4 champs. Le commit
`1b7c6d7` (« lot C : la télémétrie ne ment plus », 2026-09-02 09:35) en a ajouté deux **sans
toucher au motif**. Depuis ce commit, **aucun panneau `IG|` ne matchait** : toute campagne lancée
après 09h35 aurait rendu `project_portfolios = []` en silence — y compris celle-ci. Les mesures
ci-dessus n'existent que parce que le motif a été réparé d'abord. `RE_IG` et `RE_IB` acceptent
désormais l'ancien et le nouveau format, et capturent `knapsack_truncated`, `budget_nested`, `built`.

**Leçon de méthode, à ajouter à celle de `tree_planting`** : quand on enrichit un panneau, le
parseur ancré par `$` échoue en SILENCE — pas d'erreur, juste une liste vide. Toute modification de
format de panneau doit être suivie d'un test du motif sur la chaîne réellement émise.

### 5. Ce qui reste vrai, et ce qu'on garde

- Le réglage `portfolio_max_batch` reste **exposé, défaut 1** : c'est le seul instrument pour
  remesurer ce plafond le jour où la concurrence pour la trésorerie serait corrigée.
- Les revalidations de batch (préflight air `AITestMode` + recomptage vivant des routes de hub,
  préflight dock eau, invalidation de `candidate.railPlan`) sont **inertes au défaut** : elles sont
  toutes gardées par `builtCount > 0`.
- ⚠️ **Risque résiduel connu, non corrigé** : `OpexJoinPathIsDedicated` n'est armé que si
  `join != null` (`builder_rail.nut:937`), donc un A\* rail peut traverser du rail existant dans le
  cas courant. Ce n'est PAS un risque né du batch (il existe déjà entre passages successifs) ;
  le rendre inconditionnel modifierait le bras de contrôle, ce qui a été refusé pour garder la
  comparaison lisible.
- ➜ **Suite logique** : instrumenter qui dépense la caisse entre deux passages du portefeuille, et
  décider si `_tryBuildAir` doit continuer à court-circuiter l'arbitrage du portefeuille.

---

## 7 bis. Dimensionnement marginal de flotte (`marginal_fleet`) — MESURÉ, défaut 0, mais le mécanisme est bon (2026-09-01)

**Banc apparié 20 graines × 3 ans** (`docs/bench_marginal_fleet_3y_20seeds.json`, les deux bras
portant déjà `tree_planting=0`) :

| métrique | `marginal_fleet=1` contre le défaut | t | graines |
|---|---:|---:|---:|
| `company_value` | **−27,2 %** | 2,02 | 14/20 défavorables |
| `median_station_rating` | **−29,4 %** | 6,90 | **20/20 défavorables** |
| `profit_year` | −13,8 % | 1,06 | 12/20 défavorables |
| `performance_history` | +9,8 % | 1,52 | 14/20 favorables |
| gares | **19,6 → 31,8 (+62 %)** | | ✅ |
| véhicules | 58,0 → 41,5 (−28 %) | | ✅ |

⚠️ **Défaut maintenu à 0.** La dégradation de valeur dépasse le plancher de détection (~15 %), ce
n'est pas du bruit.

**Mais ne pas jeter le mécanisme — il fait ce qu'on lui demandait.** Le capital libéré se convertit
bel et bien en réseau : **+62 % de gares**, exactement le levier de volume qui manque (le banc 1v1
dit que ~85 % de l'écart avec AAAHogEx vient du volume). Ce qui tue le résultat est le **démarrage
à un seul véhicule** : la ligne est sous-desservie, le cargo s'accumule, et la note de gare chute de
29 % sur **20 graines sur 20** — signal net et non ambigu, pas une fluctuation.

**Ce que ça dit pour la suite** : le bon réglage n'est ni 1 (sous-service) ni le clonage immédiat à
`candidate.trains` (immobilisation). Piste à tester : démarrer à **2** véhicules, ou garder le
démarrage minimal mais rendre la croissance **beaucoup plus réactive** (trimestrielle plutôt
qu'annuelle, dès que du cargo attend) au lieu d'un avion par ligne et par an.

**Deux dérives code/commentaire trouvées en l'implémentant, et toujours présentes sous le défaut 0 :**
1. `economy.nut` : le commentaire dit « `MAX_ROAD_VEHICLES = 2` est la traduction directe de la
   règle du jeu » **juste au-dessus d'une constante qui vaut 8**.
2. `_resizeAirFleets` (`main.nut`) : son commentaire promet âge ≥ 1 an, charge complète en attente
   et un avion par an — **aucune des trois n'était vérifiée**, et la boucle montait à 4 avions par
   passage.

Même famille que la régression `tree_planting` : **le code a divergé de sa propre justification
écrite**. Ne jamais faire confiance à un commentaire de constante sans lire la constante.

---

## 8. Hygiène

- 🔶 **Workflow GitHub avec OpenTTDLab : smoke test à chaque PR, banc à la demande (demandé le
  2026-09-02).** Le dépôt est désormais sur GitHub (`jrdoublet/openttd-ml`, privé), donc
  l'intégration continue devient possible. Deux étages, et **surtout pas un seul** :

  **Étage 1 — porte de PR, obligatoire, ~2 à 5 min.** Smoke test 3 graines × **2 ans**, échec du
  job si une partie remonte `run_ok = false` ou un marqueur fatal NoAI (`Your script made an
  error`, `The script died unexpectedly`).

  ⚠️ **Deux ans, pas un.** Paramètre payé le 2026-09-02 : le plantage `station_exit` de
  `OpexUpgradeRailLineToDoubleTrack` **passe le smoke à 1 an** et ne tue l'IA qu'à 2 ans, quand le
  refleet rail se déclenche pour la première fois. Un smoke d'un an aurait laissé passer une IA qui
  meurt en cours de partie.

  ⚠️ **La porte doit aussi vérifier un PLANCHER DE PLAUSIBILITÉ**, pas seulement l'absence
  d'erreur : au moins une gare et un profit non nul sur chaque graine. Sans ça, une IA qui ne
  construit RIEN passe le test en silence — c'est la règle du projet, *une IA morte ressemble
  exactement à une IA nulle*, et un job vert la maquillerait.

  **Étage 2 — banc apparié, manuel ou nocturne, PAS une porte de PR.** 20 graines × 3 ans contre le
  bras de contrôle courant, JSON publié en artefact. Il ne peut pas être bloquant, pour deux
  raisons de fond :
  1. il dure ~20 min sur 3 cœurs, et bien plus sur un runner GitHub à 2 vCPU ;
  2. son **plancher de détection est de ~15 % sur `company_value`** — il est structurellement
     incapable de valider un petit changement, donc l'utiliser comme porte produirait surtout des
     échecs et des succès aléatoires.

  **Points de mise en œuvre à ne pas redécouvrir :**
  - OpenTTD **15.3 obligatoire** (AAAHogEx exige ≥ 14, OpenTTDLab ne supporte pas 14.x) ;
  - l'image exige `libgomp1` et `libglib2.0-0`, sinon `exit 127` silencieux — c'est déjà dans le
    `Dockerfile` du dépôt, le réutiliser plutôt que d'en écrire un autre ;
  - **mettre en cache les téléchargements OpenTTDLab** (binaire OpenTTD + OpenGFX), sinon chaque
    job les retélécharge ; clé de cache = version d'OpenTTD ;
  - le dépôt est **privé** : les minutes Actions sont facturées, ce qui plaide pour un étage 1
    court et un étage 2 déclenché à la main.


- 🔶 **Supprimer aussi `rail_refleet` et `air_starter`, PROUVÉS INERTES par la mesure
  (2026-09-02).** Écart-type des différences appariées = **0,0** sur 20 graines : basculer l'un ou
  l'autre ne change pas un bit du résultat (`bench_rail_refleet_vs_aaahogex_5y.json` et `_v2`).
  C'est la confirmation indépendante de la revue de code (§0 nonies : « TOUTE la fonctionnalité
  `rail_refleet` est du code injoignable »). Même traitement que `tree_planting` ci-dessous :
  retirer le code gardé, la constante, sa relecture dans `Start()`, l'entrée `info.nut` et la
  liste blanche de `bench_v2.py`. ⚠️ Retirer le code **mort** ne décale pas les trajectoires
  (vérifié le 2026-09-02 : 20/20 graines bit-identiques après suppression de 766 lignes) — mais
  retirer une **lecture de réglage** en décale, donc prévoir un banc de non-régression.

- 🔶 **Supprimer le réglage `tree_planting` et le chemin préventif qu'il garde (demandé le
  2026-09-01).** La question est **tranchée**, le réglage n'a donc plus de raison d'exister : la
  plantation ne doit avoir lieu **que** quand une ville nous refuse un aéroport. Laisser un
  paramètre inutile encombre `info.nut` et la liste blanche du banc.

  Ce qu'il faut retirer :
  1. les **sept sites préventifs** gardés par `TREE_PLANTING` dans `main.nut`
     (`542`, `707`, `864`, `1204`, `1518`, `1594`, `1699` au 2026-09-01) — ils appellent
     `OpexBoostTownRating` *avant* toute tentative de construction ;
  2. la constante `TREE_PLANTING` (`main.nut:68`) et sa relecture (`main.nut:3050`) ;
  3. la déclaration `AddSetting` dans `info.nut` ;
  4. l'entrée `"tree_planting"` de la liste blanche de `sweeps/bench_v2.py` (~ligne 141).

  ✅ **Débloqué le 2026-09-03.** La seule raison de garder le réglage était que le −22,1 % qui l'avait condamné portait sur un garde mort (`AITown.GetRating` est un enum 0-8). Le garde réparé, D1 a refait la mesure : `tree_planting=1` reste **négatif** (−12,1 % de `company_value`, −13,4 % de `profit_year`, 13/20 graines perdantes, `docs/bench_tree_planting_recalibrated_3y.json`). La question est tranchée deux fois, par deux mesures indépendantes dont l'une sur un mécanisme réparé : **le chemin préventif part, la plantation au refus municipal reste**. Suivi en E8.

  ⚠️ **Ne PAS toucher** au recours réactif de `builder_air.nut` (`517` et `540`) : il n'est pas
  derrière le drapeau, il ne se déclenche qu'après un vrai `ERR_LOCAL_AUTHORITY_REFUSES` renvoyé
  par `BuildAirport`, et c'est le seul comportement qu'on garde. `OpexBoostTownRating`
  (`candidates.nut`) reste donc en place, seul son usage préventif disparaît.

  ⚠️ Suppression **sans effet attendu sur le comportement** : le défaut est déjà à 0 depuis le
  banc ci-dessous. Mais toute perturbation du rythme d'opcodes décale les frontières de ticks
  (voir §5) — donc si le banc bouge après ce nettoyage, ce n'est pas une régression de décision,
  c'est une divergence de trajectoire. Ne pas re-mesurer pour « valider » la suppression.

  Motivation mesurée : banc apparié 20 graines × 3 ans
  (`docs/bench_treeplanting_3y_20seeds.json`), couper la plantation préventive vaut
  `company_value` **+22,1 %** (t = 2,42, 17/20 graines), `profit` +26,8 % (t = 2,09),
  `profit_year` +20,1 %, et resserre la dispersion (CV 63,8 % → 50,7 %).

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

- ✅ **Re-baseliner les durcissements inconditionnels du raccordement** (2026-08-30).
  `AreTilesConnected` après chaque `BuildRail` et `StartStopVehicle` reporté s'appliquent
  aussi à `station_join=0`. Ils sont dans `docs/bench_road_current.json`, puis
  dans l'arbre courant `docs/bench_double_track.json` (20×20, défauts, double voie).
  `docs/bench_v2.json` (vs AAAHogEx) et `docs/opexai_plafonnement_mesure.json`
  restent historiques. ⚠️ **Ne pas prendre `docs/bench_after_pbs.json` pour
  successeur** : c'est le banc HEAD+PBS, 20/20 sous `bench_road_current`, voir §5.

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
  peuvent pas partager une gare. Pertinent aussi dès qu'`OpexAI` a plusieurs lignes qui se croisent.
  Lecture faite : `docs/mecanique_jeu.md` §12 — trois principes, pas un cloverleaf ; `JOINPATH`
  tient tant que la jointure ne paie pas. PBS de capacité et de jointure posés (item 9.4) :
  hors gorge, hors aiguillage, fail-closed, `RX`/`XC`. Ce n'est **pas** une fusion de flux.

**Périmètre de mode, vérifié le 2026-08-29, à jour le 2026-08-30** : `_tooClose` ne filtre
**que le rail**. L'avion et le bateau ne le subissent pas (une liaison unique chacun) mais
**l'alimentent** : ils rejoignent `_lines`, un aéroport ou un quai bloque le rail sur 10 tuiles.
Les lignes **routières** sont dans `_lines` (rapport, rebut, `RF`) mais
`OpexOriginServed(..., includeRoad = false)` et `_tooClose` les ignorent : une desserte de
12 tuiles n'épuise pas une ville. Le plafond v1 « une seule liaison bus » est levé (jusqu'à
3/an). Le non-chargement de la v1 était la façade du dépôt, pas le type d'arrêt. Rentabilité
mesurée : `docs/opexai_route.md`, banc PH **+9,3 %**.
- ✅ **Gérer des voies aller-retour** (double voie v1, 2026-08-30). Voir item 9.5.
  Banc 20×20 vs `bench_road_current` : valeur +55 %, note −9 %. **Gardé.**
  Jointure aussi (item 0.7) : ne paie pas, défauts 0.
- 🔴 **File dynamique `catalogue -> lignes rentables -> reste de la file` rejetee en l'etat**
  (2026-08-31). Le premier essai round-robin payait toutes les taches tous les dix jours et perdait
  11,1 % de valeur (`docs/bench_continuous_queue.json`). La correction `dueYear`/`enabled` reporte
  bien les taches inutiles au cycle futur, mais son banc 5 graines x 20 ans baisse l'utilisation
  mesuree des opcodes de 9,6 % **et** le profit d'exploitation de 7,2 %, la performance de 9,6 %
  (0/5) et la valeur de 18,3 % (0/5) : ne pas l'adopter sur ce seul argument
  (`docs/opex_queue_deferred_20y_5seeds.json`).

  L'idee inspiree d'AAAHogEx a ensuite ete testee directement : catalogue, classement rentable,
  construction sans pause de la ligne 1 puis 2 puis 3, file circulaire, et conservation du
  classement lorsque la premiere ligne manque de cash. Banc apparie 5 graines x 5 ans :
  **profit attendu/Gopcode rail +28,9 %**, mais seulement 4/5 et `t = 1,29` (non etabli) ; en
  contrepartie **lignes -27,2 %**, revenu brut -26,7 %, performance -14,8 % et valeur -33,5 %.
  Le blocage strict sur une ligne bien classee mais chere immobilise le capital et casse la
  croissance composee.

  ✅ **Pipeline de précalcul sans blocage financier — FAIT (2026-08-31)** : découplage du calcul de tracé
  (`OpexPlanRailRoute`) et de l'exécution financière (`OpexExecuteRailPlan`). Pendant les périodes
  d'accumulation de cash (où 87 % des opcodes étaient dormants), l'IA précalcule les tracés A*, les quais
  et la double voie des meilleurs candidats. Dès que la trésorerie atteint le capital requis, la construction
  s'effectue instantanément.
  **Banc apparié 5 graines × 5 ans (`docs/bench_preplan_queue_5y.json`)** :
  - Valeur d'entreprise : **+3,63 %** (+11 374 £), **5/5 graines gagnantes**
  - Profit annuel : **+4,86 %** (+5 194 £), **5/5 graines gagnantes**
  - Profit dernier trimestre : **+4,85 %** (+1 293 £), **5/5 graines gagnantes**
  - Réglage `preplan_queue`, défaut 1.
- ✅ **Contribuer à la croissance d'une ville via des stations de bus/camions — FAIT (2026-08-31)** :
  Tâche basse priorité `town_growth` intégrée en fin de file annuelle (juste avant `repay`). Pour chaque
  ville desservie comptant $n$ gares ferroviaires/aéroports ($n < 5$), l'IA construit $5 - n$ stations de
  bus intra-urbaines pour atteindre le plafond maximal de 5 stations actives d'OpenTTD (`CountActiveStations = 5`)
  et maximiser l'accélération de croissance démographique sans pénaliser les investissements lourds.
  Réglage `town_growth`, défaut 1. Signe diagnostic `TG|year|townId|nBefore|nAfter`.
- ✅ **Réserve de trésorerie dynamique (`dynamic_cash_reserve`) et déploiement du cash — FAIT (2026-08-31)** :
  Remplacement de la constante statique `CASH_RESERVE = 50 000` par la fonction `OpexCashReserve()` :
  - **Dimensionnement dynamique** : calculé sur 3 mois de coûts d'exploitation de la flotte active, borné entre 15 000 £ (au démarrage) et 50 000 £ (en régime de croisière). Libère jusqu'à 35 000 £ de capital dès l'an 1.
  - **Déploiement du cash excédentaire** : levée du plafond mono-avion (`AIR_MAX_LINES_PER_YEAR = 1`, jusqu'à 5 liaisons aéroportuaires rentables) et remboursement de la dette via `_tryRepayLoan` quand la trésorerie dépasse `LOAN_REPAY_FLOOR` (300 000 £).
  - Réglage `dynamic_cash_reserve` (défaut 1) dans `info.nut`.
- ✅ **Limite d'opcodes de pathfinding dynamique (`dynamic_pathfinder_cap`) — FAIT (2026-08-31)** :
  Calibrage automatique du plafond d'itérations A* selon l'état de la compagnie :
  - **Démarrage / Réseau jeune** : Plafond modéré à **30 000 itérations** pour éviter d'épuiser des opcodes sur des tracés complexes quand des corridors directs faciles existent.
  - **Précalcul & Attente de trésorerie** : Plafond ouvert à **60 000 itérations** pour exploiter les opcodes dormants.
  - **Maturité du réseau** : Échelle de 30 000 à 60 000 itérations proportionnelle au nombre de lignes pour contourner les obstacles.
  - Réglage `dynamic_pathfinder_cap`, défaut 1 dans `info.nut`.
- ✅ **Exécution continue sans blocage (Suppression du Sleep(10 jours)) — FAIT (2026-08-31)** :
  Remplacement du `AIController.Sleep(74 * 10)` inconditionnel de la boucle principale par `AIController.Sleep(1)` (1 tick NoAI).
  - Élimine les latences de 10 à 130 jours in-game entre les tâches.
  - Cadencement annuel de `catalog` et `report`, et mensuel de `repay`.
  - **Banc 20 graines × 5 ans** : Valeur d'entreprise moyenne en hausse de **+17,5 %** (**298 631 £** vs **254 040 £**).
- ⚪ **Planter des arbres pour augmenter la réputation municipale (`tree_planting`) — ÉCARTÉ (2026-08-31)** :
  Implémentation du module `OpexBoostTownRating` (plantant des arbres pour relever la note locale au-dessus de 100).
  **Banc apparié 20 graines × 5 ans (`docs/bench_tree_planting_5y.json`)** :
  - `company_value` : **−17,05 %** (−84 572 £), $t = −6,62$, **0/20 graines gagnantes** (20/20 défavorables).
  - `profit` : **−31,57 %** (−12 490 £), $t = −7,19$, **0/20 graines gagnantes**.
  - `profit_year` : **−25,94 %** (−40 051 £), $t = −6,57$, **0/20 graines gagnantes**.
  
  **Cause de l'échec** : La note d'autorité locale initiale dans OpenTTD est déjà suffisante ($\ge -200$) pour construire des gares et arrêts sans refus. Planter des arbres de façon préventive draine inutilement la trésorerie au démarrage sans débloquer aucun nouveau corridor.
  ⚠️ **Réglage `tree_planting`, défaut 0 (ÉCARTÉ).**

  🔴 **RÉGRESSION : ce défaut a été perdu, puis remesuré et rétabli le 2026-09-01.** Entre le
  2026-08-31 et le 2026-09-01, le code est repassé à `TREE_PLANTING <- true` (`main.nut:68`) et
  `custom_value = 1` (`info.nut`) — **ce document disait 0 pendant que le code faisait 1**, et
  personne ne l'a vu pendant une journée entière de travail bâti sur cette base. Remesuré à
  3 ans, la perte est confirmée (`docs/bench_treeplanting_3y_20seeds.json`, 20 graines) :
  `company_value` **+22,1 %** en coupant (t = 2,42, **17/20 graines**), `profit` +26,8 %
  (t = 2,09), `profit_year` +20,1 %, et la dispersion se resserre (CV 63,8 % → 50,7 %). Défaut
  remis à **0** partout.

  **Leçon de méthode** : un défaut « adopté » dans ce document n'est PAS une garantie que le code
  l'applique. Avant de bâtir sur un réglage, **lire sa valeur dans `info.nut` et `main.nut`**, pas
  seulement ici. Une régression de défaut est invisible au banc si on ne mesure que des variantes
  entre elles.

  **Ce qui reste vivant, et qui n'est pas derrière ce réglage** : le recours **réactif** de
  `builder_air.nut` (`517` et `540`), qui appelle `OpexBoostTownRating` puis réessaie l'aéroport
  uniquement après un vrai `ERR_LOCAL_AUTHORITY_REFUSES`. C'est la règle voulue : **on ne plante
  que si une ville nous refuse un aéroport**. Le nettoyage du réglage devenu inutile est en §8.
- ⚪ **Ordre de chargement passagers rail (`pax_full_load`) — MAINTENU PAR DÉFAUT (2026-08-31)** :
  Comparaison entre le plein chargement forcé aux deux bouts (`pax_full_load=1`, `OF_FULL_LOAD_ANY`) et le départ partiel rapide (`pax_full_load=0`, `OF_NONE`).
  **Banc apparié 20 graines × 5 ans (`docs/bench_pax_full_load_5y.json`)** :
  - `company_value` : **+0,21 %** (+1 055 £), $t = +0,61$, 8/20 wins pour A, 8/20 wins pour B, 4 nuls.
  - `performance_history` : **+0,31 %** (+0,8 pt), $t = +0,63$.
  - `profit` : **−0,16 %**, $t = −0,06$.
  
  **Conclusion** : Le dimensionnement de la longueur des convois par OpexAI (`trainsForVolume` / `OpexRailNominalMaxWagons`) est déjà ajusté au tonnage mensuel des villes reliées. Le départ partiel immédiat fait rouler des convois à demi-vides dont les coûts de fonctionnement fixes absorbent le léger gain de rotation.
  ⚠️ **Défaut `pax_full_load=1` strictement maintenu.**
- ✅ **Gestion des marchandises complexes et chaînes de transformation secondaire (`complex_cargo`) — ADOPTÉ (2026-08-31)** :
  Indexation au catalogue des villes acceptatrices pour les marchandises transformées (`Goods`, `Food`, `Water`, `Mail`) et génération des corridors Industrie $\rightarrow$ Ville dans `OpexFreightCandidates`.
  Permet d'alimenter les industries secondaires (Aciérie, Scierie, Raffinerie, Usine) et d'évacuer les marchandises à haute valeur ajoutée vers les centres urbains.
  **Banc apparié 20 graines × 5 ans (`docs/bench_complex_cargo_5y.json`)** :
  - `company_value` : **+4,27 %** (+21 181 £), **$t = +2,29$** ($p < 0,05$), 12/20 graines gagnantes.
  - `performance_history` : **+5,38 %** (+13,6 points), **$t = +3,10$** ($p < 0,01$), **16/20 graines gagnantes**.
  - `profit` : **+4,85 %** (+1 853 £), $t = +1,71$, 12/20 graines gagnantes.
  - `profit_year` : **+3,81 %** (+5 863 £), $t = +1,90$, 14/20 graines gagnantes.
  
  ⚠️ **Réglage `complex_cargo = 1` activé par défaut.**

---

## 0 unvicies. 🔴 LE RAIL COÛTE 1,8× SON PRIX MODÉLISÉ — mesuré (2026-09-02)

Dernier angle mort de l'attribution de trésorerie de §0 vicies : le rail n'émettait aucun panneau
de coût. `rail_cost_probe = 1` l'ouvre (`DC|idx|capitalModèle|coûtRéel|trainsPrévus|trainsBâtis|doubleVoie`,
`main.nut:1430` en succès et `:1476` en échec). Campagne 5 graines × 3 ans archivée dans
`docs/opex_campaign_5seeds_rail_cost_probe.json`.

### 1. Le résultat : le modèle sous-facture le rail de 21 %

15 lignes ferroviaires mises en service. Sur les **14 dont la flotte bâtie est conforme au plan**
(la 15ᵉ prévoyait 2 convois et n'en a bâti qu'un, ce qui inverse artificiellement l'écart) :

| | capital modèle | coût réel | écart |
|---|---:|---:|---:|
| **14 lignes** | 470 713 £ | **561 395 £** | **+90 682 £ — +19,3 %** |

> **Chiffres corrigés le 2026-09-02 au soir.** La première lecture donnait +98 406 £ (+20,9 %) :
> elle comptait 552 £ de trop par ligne. `AIAccounting` additionne aussi le coût **simulé** des
> commandes jouées en `AITestMode` (`script_object.cpp:299-302`), et `OpexBuildDepot` sonde le
> dépôt en mode test à l'intérieur de la fenêtre comptable. Corrigé par un `AIAccounting`
> imbriqué qui jette ces coûts (voir §0 duovicies). Le trajet des parties est identique — mêmes
> lignes, même capital modèle — seule la mesure change.

Et l'erreur **croît avec la distance**, ce qui la localise :

| distance | n | modèle | réel | écart |
|---|---:|---:|---:|---:|
| < 75 tuiles | 6 | 184 696 | 207 700 | +12,5 % |
| 75-100 | 3 | 102 396 | 126 687 | +23,7 % |
| 100-130 | 5 | 183 621 | 227 008 | +23,6 % |

Régression du surcoût sur la distance : **+103 £/tuile, ordonnée à l'origine −2 563 £**
($R^2 = 0{,}44$).

L'ordonnée à l'origine de la régression est nulle aux erreurs près : **toute l'erreur est dans le
seul terme qui dépend de la distance**, `distance * catalog.costTrackPerTile` (`economy.nut:231`).
Les gares, le dépôt et les véhicules sont correctement facturés.

### 2. Le facteur exact

`costTrackPerTile` vaut **75 £/tuile** (identifié par différence sur les paires de lignes de même
quai / même rame / même loco : 12 paires sur 18 donnent exactement 75,0 ; et le prix de base
`PR_BUILD_RAIL` = 100 de `src/table/pricebase.h` confirme un multiplicateur de 0,75). Le prix
réellement facturé par tuile de distance **à vol d'oiseau** est de **151 £** — détours du tracé,
nivellement, ponts et tunnels, dont §0 « Ponts et tunnels (v3) » disait déjà qu'aucun n'est *pricé*.

Le facteur qui annule le biais médian est **×1,70** (75 → 128 £/tuile) :

| ratio modèle/réel | min | médiane | max |
|---|---:|---:|---:|
| avant | 0,70 | **0,88** | 0,93 |
| après ×1,70 | ~0,85 | **1,00** | ~1,04 |

C'est une correction de **biais pur** : la dispersion ne bouge pas (écart-type 7,1 → 7,0 points).
Le modèle passe de « sous-estime toujours, de 8 à 30 % » à « juste, à ±16 % dans le pire cas ».

### 3. Pourquoi ça compte pour le portefeuille

`roi = profitAnnual * 1000 / capital` (`economy.nut:247`) et `OpexProjectModeBetter` élit le mode
sur `roi` (`projects.nut:136`). Un capital rail sous-facturé de 21 % **gonfle mécaniquement le ROI
du rail face à la route et à l'avion**, dans le seul nombre qui les départage — exactement le
défaut que `pricing_fix` (dépôt manquant, §0 octies) avait déjà corrigé, mais d'une ampleur bien
supérieure. Et le sac à dos finance ensuite sur un budget faux : il croit acheter 5 projets, en
paie 4.

➡️ **Candidat de tête** : réglage `rail_terrain_factor` (pour mille, défaut 100 = neutre) appliqué
à `costTrackPerTile`, banc apparié 20 graines à 100 contre 170. Sens de l'effet **non acquis** :
corriger le prix rend le plan honnête mais peut aussi tuer des lignes rentables — c'est la mesure
qui tranche, pas l'argument.

### 3 bis. ✅ D1 — Vérifié en conditions réelles après C2/C3/C7 (2026-09-02 soir)

Rejeu de la même campagne (mêmes 5 graines, 3 ans, `rail_cost_probe=1`,
`docs/opex_campaign_5seeds_rail_cost_probe_postfix.json`), avec `rail_terrain_factor` calibré à
170 % (C2), `PROJECT_RAIL_OPS_PER_ITERATION = 3105` (C3) et le devis réel `AITestMode`+`AIAccounting`
(C7) tous actifs par défaut — pas une simple recalibration rétrospective du même jeu de données
comme la ligne « après ×1,70 » ci-dessus, une **nouvelle mesure**.

| ratio modèle/réel | min | médiane | max |
|---|---:|---:|---:|
| avant (référence ci-dessus) | 0,70 | 0,88 | 0,93 |
| **après, mesuré (D1)** | **0,998** | **1,025** | **1,038** |

8 lignes rail exploitables (flotte bâtie conforme au plan) sur les 5 graines. Le biais de
sous-facturation est refermé : le modèle passe de « toujours trop bas de 7 à 30 % » à « neutre à
légèrement prudent (+0 à +3,8 %) » — dans le sens qui protège le portefeuille (surestimer le
capital rail est sans risque pour le ROI, le sous-estimer gonflait artificiellement sa place face
à la route et l'avion). `n_rail_attempts_failed = 0` sur les 5 graines : toujours aucun chantier
rail avorté, confirmé inchangé.

### 4. Chantiers avortés : le rail est innocent, l'avion coupable

**`n_rail_attempts_failed = 0` sur les 5 graines et les 3 ans.** Aucun rollback ferroviaire, donc
aucun capital gaspillé de ce côté. Le trou de 150 475 £ de la graine 42 (§0 vicies) n'est pas rail.

Il est aérien. Sur **20 tentatives aériennes : 12 OK, 4 `AFAIL`, 4 `BFAIL`** — **40 % d'échec**.

`builder_air.nut:535-580` nivelle le site A, y **bâtit** l'aéroport, puis nivelle B, tente B, et
sur échec **démolit A** (`OpexAirRollback`). Un `BFAIL` brûle donc un nivellement, un aéroport
complet et une démolition, **sans qu'aucun panneau ne chiffre quoi que ce soit**. La graine 42 a
exactement un `BFAIL` en 1970 (distance 223) — le trou de 150 475 £ a son coupable.

Et **4 graines sur 5 encaissent leur `BFAIL` dès la première année**, quand la trésorerie est au
plus juste (§0 « plafonnement — trésorerie 1970-1980 »).

Signature nette : **tous les échecs sont les tentatives longues.**

| | distances |
|---|---|
| `OK` (12) | 140, 146, 157, 161, 163, 173, 190, 195, 195, 197, 200, 212 |
| `BFAIL` (4) | **189, 191, 214, 223** |
| `AFAIL` (4) | **178, 240, 243, 245** |

Deux pistes, la première quasi gratuite :

1. **Tester B avant de payer A.** L'ordre actuel paie A puis découvre que B est impossible.
   Un `AITestMode` sur le site B avant d'engager A ne coûte que des opcodes et récupère
   l'intégralité du capital des 4 `BFAIL`. À vérifier : le mode test intercepte-t-il bien
   `ERR_LOCAL_AUTHORITY_REFUSES` ?
2. **Plafonner la distance des tentatives aériennes.** Aucun succès au-delà de 212 tuiles,
   aucun échec en deçà de 178. Un plafond est un réglage d'une ligne — mais il coupe aussi la
   queue haute du profit, donc il se mesure.

### 5. ✅ L'avion rendu lisible, et l'attribution enfin complète

`AH|idx|reuseA|capital|hubRoutes` (`main.nut:773`) et `AF|idx|avions|profitAnnuel` (`:771`)
portaient déjà le capital aérien **et le parseur les ignorait** — aucun `RE_AH`/`RE_AF` dans
`sweeps/opex_full_campaign.py`. Ajoutés, et **vérifiés contre les chaînes réellement émises**
(12/12 panneaux appariés dans l'archive) avant toute exploitation — la leçon de §0 vicies sur
`RE_IG` cassé pendant deux jours.

Attribution complète de la campagne, 5 graines × 3 ans :

| mode | lignes | capital | source | part |
|---|---:|---:|---|---:|
| **avion** | 12 | **1 434 691 £** | `AH` — *modèle* | **64,5 %** |
| **rail** | 15 | **614 704 £** | `DC` — **réel** | 27,6 % |
| **route** | 7 | **176 119 £** | `RC` — **réel** | 7,9 % |
| total | 34 | 2 225 514 £ | | |

**L'avion prend les deux tiers du capital avec un tiers des lignes**, et ces 64,5 % sont un
**plancher** : le chiffre aérien est le modèle, il ignore le nivellement des sites et ne compte
aucune des 8 tentatives avortées. §0 vicies mesurait déjà que 11 des 12 lignes aériennes sont
bâties **hors** du portefeuille, par la tâche `air` qui passe avant lui dans la file
(`main.nut:429-440`). Les deux mesures se recoupent : **le portefeuille arbitre le tiers restant.**

Reste aveugle : le coût réel de l'aéroport (nivellement compris) et celui des `AFAIL`/`BFAIL`.
Un panneau de coût aérien symétrique de `DC|` les fermerait.

---

## 0 duovicies. ✅ AVION : sonder avant de payer, chiffrer le gaspillage, et deux bugs au passage (2026-09-02)

Items 2 et 3 de §0 unvicies. Réglages `air_presite` et `air_cost_probe` (`info.nut`), défauts **0**.
Campagnes 5 graines × 3 ans : `docs/air_cost_ctrl_v2.json`, `docs/air_cost_presite_v2.json`.

### 1. Le coût réel de l'avion, enfin lisible — et le modèle est juste

Panneau `AC|idx|capitalModèle|coûtRéel|avionsPrévus|avionsBâtis`, émis **aussi sur échec**
(`main.nut:750` et `:1207`), alimenté par un `AIAccounting` qui couvre toute `OpexBuildAirRoute`,
nivellement et démolitions de repli compris.

| | n | modèle | réel | écart |
|---|---:|---:|---:|---:|
| lignes en service | 15 | 1 839 506 £ | 1 887 627 £ | **+2,6 %** |

**Contraste net avec le rail (+19,3 %)** : le modèle aérien est juste. Il n'y a pas de terrain à
traverser — deux rectangles nivelés, et le prix de l'aéroport est un forfait.

### 2. Ce que coûtent les chantiers avortés, et ce que `air_presite` en récupère

Les 7 abandons du témoin se lisent en deux paquets nets :

| | n | coût par tentative |
|---|---:|---|
| `AFAIL` — le site A refuse, rien n'est bâti | 3 | 7 326 / 7 744 / 7 918 £ (nivellement seul) |
| `BFAIL` — A est **bâti**, B refuse, A est **rasé** | 4 | 23 847 / 24 573 / 25 105 / 28 646 £ |

`air_presite` nivelle les deux sites, les sonde en `AITestMode`, et n'engage l'aéroport A que si B
passe. Résultat sur les mêmes graines :

| | tentatives avortées | capital brûlé |
|---|---:|---:|
| témoin | 7 (3 `AFAIL` + 4 `BFAIL`) | **125 159 £** |
| `air_presite` | 8 (4 `PREA` + 4 `PREB`) | **57 961 £** |

**−67 198 £, soit −53,7 % du gaspillage**, et le paquet cher a **entièrement disparu** : les 8
abandons coûtent tous entre 6 285 et 7 918 £, le prix du seul nivellement. Le mécanisme fait
exactement ce qu'on lui demande.

Valeur d'entreprise à 3 ans : 2 graines montent, 2 descendent, 1 nulle. **n = 5 ne tranche rien**
(§ « Banc mono-graine insuffisant ») — le banc apparié 20 graines est lancé, défaut à 0 d'ici là.

### 3. ⚠️ Piège majeur : `AIAccounting` compte le coût SIMULÉ d'`AITestMode`

Le premier jet d'`air_presite` mesurait un coût réel **+30,8 %** au-dessus du modèle, contre
+2,6 % au témoin. Ce n'était pas une dépense : c'était l'instrument.

```cpp
/* src/script/api/script_object.cpp:299-302 */
/* Estimates, update the cost for the estimate and be done */
if (estimate_only) {
    IncreaseDoCommandCosts(res.GetCost());
    return true;
}
```

**Une commande jouée en `AITestMode` ajoute son prix simulé au compteur d'`AIAccounting` sans
qu'une livre ne sorte.** Deux sondages d'aéroport = **+35 000 £ fantômes par ligne**.

Le correctif tient en une ligne, et il utilise le piège documenté « `AIAccounting` ne s'imbrique
pas » **à l'endroit** : le destructeur d'un `AIAccounting` imbriqué **restaure** le total du
niveau supérieur (`src/script/api/script_accounting.cpp`), donc tout ce qui entre dans le compteur
imbriqué est jeté. Un `local shield = AIAccounting();` autour du sondage suffit
(`builder_air.nut:530`). Après correction, les deux bras mesurent +2,6 % et +2,7 % : identiques,
comme ils doivent l'être.

**Le rail était contaminé par le même défaut** : `OpexBuildDepot` sonde le dépôt en `AITestMode`
dans la fenêtre comptable (`builder_rail.nut:589`), ce qui facturait un dépôt fantôme de 552 £ à
chaque ligne. §0 unvicies est corrigé : **+19,3 % et non +20,9 %**, facteur **×1,70** et non
×1,81. La pente par tuile, elle, ne bouge pas — une constante n'entre pas dans une pente.

➡️ **Règle générale** : tout `AITestMode` situé dans une fenêtre `AIAccounting` fausse la mesure.
Les autres sondages du code (`builder_road.nut`, `builder_water.nut`, `OpexAirFindSite`,
`OpexStationPlans`) sont hors de toute fenêtre comptable — vérifié, rien d'autre à corriger.

### 4. La plantation d'arbres au refus municipal : le mécanisme est bon, **le garde est mort**

Question posée : plante-t-on bien des arbres quand l'autorité refuse ?

**Le recours réactif existe et n'est pas bridé** — `builder_air.nut` appelle `OpexBoostTownRating`
puis retente l'aéroport dès que `BuildAirport` rend `ERR_LOCAL_AUTHORITY_REFUSES`, sur le site A
comme sur le site B, **hors du drapeau `TREE_PLANTING`** (qui ne commande que la plantation
préventive, à 0 depuis le banc). `air_presite` conserve ce recours dans son sondage.

Trois faits vérifiés dans le source de 15.3 :

- Le refus n'arrive que si la note brute est **≤ RATING_VERYPOOR = −200** (`town_cmd.cpp:3930`).
- Un arbre vaut **+7**, plafonné à **RATING_TREE_MAXIMUM = 220** (`tree_cmd.cpp:591`). Depuis un
  refus, **un seul arbre suffit** à repasser au-dessus du seuil ; 40 est largement assez.
- `ERR_LOCAL_AUTHORITY_REFUSES` recouvre **aussi** le refus pour **bruit** (`script_error.hpp`),
  que les arbres ne réparent pas. Le re-sondage d'`air_presite` tranche entre les deux au lieu de
  le deviner.

**Mais le recours ne se déclenche jamais**, et ce n'est pas un défaut : les 8 abandons mesurés sont
**7 × `ERR_FLAT_LAND_REQUIRED` (263) et 1 × `ERR_AREA_NOT_CLEAR` (260)**, **zéro refus municipal**.
Le mur aérien est le terrain, pas la mairie.

> ⚠️ Corrige une lecture fautive de §0 vicies : le panneau `OE|A|263` de la graine 42 y était lu
> comme un « refus municipal ». **263 = `ERR_FLAT_LAND_REQUIRED`.** Le refus municipal est 258.

### 5. 🔴 Bug : `OpexBoostTownRating` compare un enum 0-8 à 700

```nut
local currentRating = AITown.GetRating(townId, AICompany.COMPANY_SELF);
if (currentRating >= targetRating && currentRating != AITown.TOWN_RATING_NONE) return;
```

`AITown.GetRating` **ne rend pas la note brute −1000..1000** : elle rend un `TownRating`, un enum
de **0 à 8** (`script_town.hpp:83` — `NONE, APPALLING, VERY_POOR, POOR, MEDIOCRE, GOOD, VERY_GOOD,
EXCELLENT, OUTSTANDING`). Les appelants passent `targetRating` = 100, 700 ou 800.

**La condition est donc toujours fausse : le garde n'a jamais rien coupé.** La fonction plantait
`maxTrees` arbres à chaque appel, quelle que soit la note déjà acquise — y compris très au-dessus
du plafond de 220 où un arbre ne rapporte **rien**.

C'est l'explication mécanique du **−22,1 % de valeur** mesuré sur la plantation préventive
(`info.nut`, `tree_planting`) : ce n'était pas « planter tôt coûte cher », c'était « planter
**toujours**, y compris quand c'est sans effet ».

Corrigé (`candidates.nut:1239`) : plafond à `TOWN_RATING_MEDIOCRE`, l'échelon juste sous les 220 de
`RATING_TREE_MAXIMUM`. **Effet au réglage par défaut : aucun** — la plantation préventive est
coupée et le seul appel vivant est le recours réactif, où la ville vient de refuser (note ≤ −200),
donc très en dessous du plafond. Le correctif répare `tree_planting` pour le jour où on le
remesure : **la mesure du −22,1 % portait sur du code cassé et ne vaut plus.**

### 6. Banc apparié 20 graines × 3 ans : le gain de capital ne se convertit pas

`docs/bench_air_presite_3y.json`, `OpexAI` contre `OpexAI[air_presite=1]`.

| métrique | écart moyen | $t$ | graines gagnées |
|---|---:|---:|---|
| `company_value` | **+0,18 %** | +0,06 | 6/20 (9 nulles) |
| `performance_history` | +1,13 % | +0,27 | 5/20 (9 nulles) |
| `profit_year` | −1,81 % | −0,41 | 5/20 (9 nulles) |
| `profit` | −1,83 % | −0,42 | 4/20 (9 nulles) |

**9 graines sur 20 sont rigoureusement identiques** : aucun `BFAIL` n'y survient, le mécanisme
n'a rien à faire. Sur les **11 graines où il agit : 6 gains, 5 pertes.** Test des signes 6/11,
$p \approx 1$. Les deux mouvements dominants sont la graine 42 (+85,8 %) et la graine 999
(−38,9 %) — la signature exacte du **remaniement de trajectoire** de §0 vicies : la trésorerie
libérée change l'ordre des chantiers, et la chance de carte reprend la main.

**Même verdict de forme que `maxBatch`** : le mécanisme fait exactement ce qu'on lui demande
(−53,7 % de capital brûlé, mesuré et non déduit), et **ça ne se convertit en rien** à 3 ans.

⚠️ **Une différence avec `maxBatch`, toutefois** : ici l'économie est réelle, datée et située —
67 198 £ récupérés dont l'essentiel tombe en **première année**, au moment précis où le mur de
trésorerie 1970-1980 mord le plus. Trois ans est peut-être un horizon trop court pour qu'un
capital rendu tôt compose. Banc 10 ans lancé (`docs/bench_air_presite_10y.json`) : **c'est lui
qui tranche**, pas celui-ci. Défaut à 0 en attendant.

---

## 0 tervicies. 🔴 CE QUE FAIT AAAHogEx : L'OBJECTIF CHANGE DE DÉNOMINATEUR (lecture de code, 2026-09-02)

Lecture des 37 531 lignes de `ai/AAAHogEx-115/`, sur deux sujets précis : la construction
d'aéroport et le devis du rail. **Toutes les citations ci-dessous ont été relues et vérifiées
ligne à ligne dans le source.**

### 1. 🔴 LA TROUVAILLE : `CalculateProfitModel` bascule l'objectif selon la ressource rare (`main.nut:781-836`)

```squirrel
main.nut:781  function CalculateProfitModel() {
main.nut:782    if(!IsRich() || IsInflation()) {
main.nut:783      roiBase = true;              // pauvre -> maximiser le profit PAR LIVRE
...
main.nut:795      if(room >= 100 && current < max * 7 / 10) {
main.nut:798        buildingTimeBase = true;   // riche, places de vehicules libres -> profit PAR TEMPS DE CHANTIER
...
main.nut:805      vehicleProfibitBase = true; // riche et plafonne en vehicules -> profit PAR VEHICULE
```

```squirrel
main.nut:828  function GetValue(roi, incomePerBuildingTime, incomePerVehicle) {
main.nut:829    if(roiBase) return roi;
main.nut:832    if(buildingTimeBase) return incomePerBuildingTime;
main.nut:835    return incomePerVehicle;
```

**AAAHogEx ne classe pas ses projets sur un critère fixe.** Elle identifie la ressource qui la
contraint à cet instant — l'argent, le temps de chantier, ou le plafond de véhicules — et
**change le dénominateur** de son classement en conséquence.

`incomePerBuildingTime = routeIncome / buildingTime` (`estimator.nut:90`) **est exactement la
métrique « profit par itération »** que ce projet s'est donnée comme objectif. Elle est déjà dans
sa fonction objectif, et elle s'active précisément quand l'argent cesse de mordre.

➡️ **OpexAI divise TOUJOURS par le capital.** En 1970 c'est le bon dénominateur ; dès que la
trésorerie n'est plus le mur, on continue d'optimiser une contrainte qui ne lie plus. C'est, de
loin, la différence la plus importante trouvée — bien avant le prix du rail.

### 2. 🔴 Le ROI porte le capital IMMOBILISÉ EN TRANSIT au dénominateur (`estimator.nut:78-88`)

```squirrel
estimator.nut:85   lostOpportunity = routeIncome * (cruiseDays + waitingInStationTime) / 365;
estimator.nut:87   local cost = max(1, price * vehiclesPerRoute + buildingCost + lostOpportunity);
estimator.nut:88   roi = routeIncome * 1000 / cost;
```

Le dénominateur n'est pas le capital construit : c'est le capital construit **plus le revenu
renoncé pendant que la marchandise voyage et attend en gare**. Une ligne longue et lente est
pénalisée même à coût de construction identique.

C'est la correction **flux contre stock** de la philosophie du projet, appliquée à l'argent et au
temps. Nous ne l'avons nulle part : `roi = profitAnnual * 1000 / capital` (`economy.nut:247`)
ignore entièrement la durée d'immobilisation.

### 3. La validation bilatérale est STRUCTURELLE, pas un correctif (`route.nut:3761` → `:3860`)

```squirrel
route.nut:3761   local testMode = AITestMode();
route.nut:3785     destHgStation = destStationFactory.CreateBest(dest, cargo, src.GetLocation());
route.nut:3800     if(destHgStation == null) return null;
route.nut:3803     HogeAI.notBuildableList.AddList(list);   // reserve les tuiles de dest
route.nut:3823     srcHgStation = srcStationFactory.CreateBest(src, cargo, destHgStation.platformTile);
route.nut:3837     if(srcHgStation == null) return null;
...
route.nut:3860   { local execMode = AIExecMode();  ... BuildExec() ... }
```

Toute la recherche des **deux** stations se fait sous une seule fenêtre `AITestMode`, et la
bascule en `AIExecMode` n'a lieu qu'après. **Aucune livre n'est engagée tant que les deux
extrémités ne sont pas prouvées**, et ce pour **tous les modes**, pas seulement l'avion.

Notre `air_presite` (§0 duovicies) est la version locale et tardive de cette idée. La leur est
l'architecture : `CreateBest()` (sonde) et `BuildExec()` (pose) sont deux méthodes distinctes de
toute classe de station.

Détail à voler : `notBuildableList.AddList` (`:3803`) réserve les tuiles de la première station
pendant la recherche de la seconde, ce qui empêche les deux extrémités de se disputer un site.

### 4. Le devis du rail : ils ne pricent PAS le terrain non plus — ils **surbudgètent** (`estimator.nut:555-561`)

```squirrel
estimator.nut:557   local demolishFarm = HogeAI.GetInflatedMoney(540) * 40 / 100;      // 216 £
estimator.nut:558   local cost = (AIRail.GetBuildCost(type, BT_TRACK)*2 + demolishFarm) * 2 * distance;
estimator.nut:559   cost += AIRail.GetBuildCost(type, BT_TRACK) * 220 + Route.GetPaxMailTransferBuildingCost(cargo);
```

Terme par terme :

| terme | valeur | ce qu'il représente |
|---|---|---|
| `GetBuildCost(BT_TRACK) * 2` | 150 £ | **double voie**, posée par défaut |
| `+ demolishFarm` | **216 £/tuile** | forfait de défrichage : 40 % de 540, une espérance |
| `* 2` | **×2** | **coefficient de détour** sur la distance à vol d'oiseau |
| `* distance` | | distance droite |
| `+ GetBuildCost * 220` | 16 500 £ | forfait gares + aiguillages + dépôt |

Soit **732 £ par tuile de distance droite**, contre **75 £** chez nous. Même en ramenant à la voie
simple, ils budgètent ~366 £/tuile là où le réel mesuré est de 151 £.

**Deux enseignements, et le second contredit notre plan :**

1. **Le coefficient de détour ×2 corrobore notre mesure de façon indépendante.** Nous avons mesuré
   un rapport réel/modèle de 2,02 par tuile (§0 unvicies) sans jamais regarder leur code ; ils ont
   codé ×2 en dur. Le facteur `rail_terrain_factor` n'est donc pas un bricolage : c'est le terme
   que tout le monde a, sauf nous.
2. **Ils ne pricent le terrain nulle part** — aucun terme de pente, d'eau, de pont ou de tunnel
   dans le devis (le relief n'entre que dans le calcul du temps de trajet). Leur réponse au
   terrain n'est pas de le mesurer : c'est de **surbudgéter et de refuser les mauvais sites**
   (point 5). Aérien : `airportTraints.cost * 2 * 2 /* 整地とかの分 */` (`:589`) — le coût de
   l'aéroport doublé « pour le terrassement etc. », soit **100 % de marge**, là où notre mesure
   d'aujourd'hui montre un écart réel de +2,6 %.

### 5. Filtre de platitude éliminatoire : ≥ 2 niveaux d'écart et le site est refusé (`tile.nut:1269-1274`)

```squirrel
tile.nut:1269   if(!force) {
tile.nut:1270     foreach(tile,level in tileList) { // 山岳マップは失敗する事が多いので、先にはじく
tile.nut:1271       if(abs(average - level) >= 2) {
tile.nut:1272         return false;
```

Le commentaire japonais dit : « sur les cartes montagneuses ça échoue souvent, on rejette
d'abord ». **C'est ce qui rend leurs échecs `FLAT_LAND` rares** — nos 7 échecs sur 8 sont
exactement ce que ce filtre aurait écarté sans dépenser un sou.

### 6. L'aéroport orphelin n'est PAS rasé (`air.nut:368`)

```squirrel
air.nut:368   isNotRemoveStation = HogeAI.Get().IsInfrastructureMaintenance() == false;
```

Quand l'entretien d'infrastructure est désactivé (le défaut), un échec de liaison **ne démolit pas**
l'aéroport déjà posé : il ne coûte rien à garder et servira une autre liaison. Nous le rasons.

### 7. Leur plantation d'arbres est la version correcte de la nôtre (`utils.nut:984-1026`, `station.nut:2102-2114`)

```squirrel
utils.nut:1021    if( AITown.GetRating(town, AICompany.COMPANY_SELF) >= goalRating ) return true;
station.nut:2113  BuildUtils.Get().PlantTreeTown(town, AITown.TOWN_RATING_POOR);
```

Ils comparent **l'enum à l'enum** (`TOWN_RATING_POOR`), **re-testent après chaque rectangle** et
s'arrêtent dès l'objectif atteint, avec un **verrou de 90 jours** par ville quand il n'y a plus
de place où planter (`:985-989`). Ils plantent par rectangle (`PlantTreeRectangleSafe`), pas tuile
à tuile. C'est la confirmation externe du bug de §0 duovicies §5.

### 8. ⚠️ Le « piège » `AITestMode` + `AIAccounting` est chez eux un OUTIL (`utils.nut:718-732`)

```squirrel
utils.nut:718   static function WaitForMoney(func) {
utils.nut:720     {
utils.nut:721       local testMode = AITestMode();
utils.nut:722       local accounting = AIAccounting();
utils.nut:723       if(!func()) { ... }
utils.nut:728       cost = accounting.GetCosts();
utils.nut:729     }
utils.nut:730     if(HogeAI.Get().IsTooExpensive(cost)) { ... return false; }
```

Ils exploitent délibérément ce que nous avons traité comme un défaut (§0 duovicies §3) :
`AIAccounting` sous `AITestMode` **rend un devis exact**. Le bloc lexical joue le même rôle de
bouclier que le nôtre — l'accounting imbriqué est détruit à la sortie et ne pollue rien.

➡️ **Conséquence directe pour §0 unvicies** : nous n'avons pas forcément besoin d'un facteur
correctif sur `costTrackPerTile`. Une fois le tracé A\* connu, **un devis exact est disponible
pour le prix de quelques opcodes**. Le facteur reste utile au *classement* (avant le pathfinding) ;
le devis, lui, doit décider de l'*engagement*.

### 9. Ce qu'il faut en retirer, dans l'ordre

1. **Rendre le dénominateur du classement dépendant de la ressource rare** (point 1). C'est
   structurel et c'est probablement là qu'est le facteur de vitesse.
2. **Ajouter le capital immobilisé en transit au dénominateur du ROI** (point 2).
3. **Devis réel par `AITestMode` + `AIAccounting` avant engagement** (point 8), en complément du
   facteur de détour pour le classement (point 4).
4. **Filtre de platitude préalable sur les sites d'aéroport** (point 5) — plus radical et moins
   cher que notre sondage `air_presite`, qui nivelle avant de tester.
5. **Ne plus raser l'aéroport orphelin** (point 6).

---

## 0 quatervicies. ❌ `air_presite` : MESURÉ À 10 ANS, NON ADOPTÉ — le gaspillage supprimé ne se convertit pas (2026-09-02)

`docs/bench_air_presite_10y.json`, banc apparié 20 graines × **10 ans**, `OpexAI` contre
`OpexAI[air_presite=1]`. C'est le banc qui devait trancher (§0 duovicies §6) : le capital rendu en
première année a eu dix ans pour composer.

| métrique | écart moyen | $t$ | signes |
|---|---:|---:|---|
| `company_value` | **−1,76 %** | −0,38 | 11 gains / 8 pertes (1 nulle) — **$p = 0{,}65$** |
| `performance_history` | +4,11 % | +1,24 | 10 / 9 — $p = 1{,}00$ |
| `profit_year` | −2,64 % | −0,43 | 8 / 11 |
| `profit` | −1,13 % | −0,21 | 9 / 10 |

**Aucun effet.** La moyenne est négative pendant que le compte des signes est légèrement positif :
c'est la signature d'une poignée de grosses pertes qui écrasent la moyenne. Les mouvements
individuels le disent — graine 1 **+66,7 %**, graine 42 **−31,0 %**, graine 123456 **+33,2 %**,
graine 7 **−27,8 %**. Le remaniement de trajectoire, amplifié par dix ans.

**Verdict : `air_presite` reste à 0.** Le mécanisme fait pourtant exactement ce qu'on lui demande
— **−53,7 % du capital brûlé par les abandons, mesuré et non déduit** (§0 duovicies §2). Troisième
fois de suite qu'un mécanisme vérifié ne se convertit en rien : après `maxBatch` (§0 vicies) et
les treize corrections (§0 nonies bis). **Le volume de capital n'est pas le mur.**

### Ce qu'il faut faire à la place, et §0 tervicies le dit

Notre sondage **nivelle les deux sites avant de tester** — c'est ce qui explique le plancher
résiduel de 57 961 £ : les 8 abandons coûtent chacun le prix d'un nivellement.

AAAHogEx ne nivelle pas pour savoir. Elle **refuse le site d'emblée** si une seule tuile s'écarte
de ≥ 2 niveaux de la moyenne (`tile.nut:1269-1274`), sans dépenser un sou. Nos 7 échecs
`FLAT_LAND` sur 8 tombent exactement dans ce filtre.

➡️ **Le successeur d'`air_presite` n'est pas un re-banc : c'est le filtre de platitude préalable.**
Il supprime le résidu que le sondage laisse, et il coûte moins cher que lui. Mais il ne faut pas
en attendre de la performance non plus — ce banc-ci vient de montrer que l'économie de capital,
seule, ne paie pas. La vraie piste reste §0 tervicies point 1 : **le dénominateur du classement.**

---

## 0 quinvicies. 🔴 SATURATION AÉRIENNE ET BUS DE RABATTAGE : deux réponses mesurées (2026-09-02)

Priorité fixée par l'utilisateur. Réglage `air_fleet_probe` (`info.nut`, défaut 0) : panneau `FR|`
pour la cause du refus de croissance d'une flotte aérienne, `FE|` pour une ligne routière de
rabattage réellement mise en service, `FN|` pour ce que la génération de rabattage produit.
Campagnes `docs/diag_air_fleet_feeder.json` et `docs/diag_feeder_gen.json`, 5 graines × 3 ans.

### 1. La flotte aérienne ne sature pas — et c'est la TRÉSORERIE, à 31 refus sur 32

`_resizeAirFleets` n'émettait que ses succès (`FG|`). Le premier refus rencontré est désormais
tracé, une fois par ligne et par an :

| cause | code | n |
|---|---|---:|
| **trésorerie insuffisante** (`money < prix + réserve + 2 000`) | `M` | **31** |
| profit négatif | `L` | 1 |
| plafond de l'aéroport atteint | `C` | **0** |
| déjà grandie cette année / ligne morte / achat échoué | `Y`/`D`/`X` | **0** |

**Le plafond n'est jamais atteint.** 17 lignes aériennes, **28 avions, 1,6 par ligne**, pour un
plafond de 16 (4 sur petit aéroport). Ce n'est ni le dimensionnement, ni le rythme annuel, ni la
santé des lignes : **il n'y a pas d'argent au moment où la tâche `air_fleet` passe.**

Et l'ordre de la file explique pourquoi (`main.nut:429-440`) :

```
catalog → report → scrap → air → air_fleet → projects → …
             tâche `air` : NOUVELLES lignes      ↑ croissance des lignes EXISTANTES
```

**On finance des lignes neuves avant de saturer celles qui marchent déjà.** Un avion de plus sur
une ligne rentable n'exige aucune infrastructure : c'est le capital le mieux employé du jeu, et
c'est le dernier servi. Recoupe §0 unvicies (l'avion prend 64,5 % du capital, presque tout en
aéroports neufs) et le mur de trésorerie 1970-1980.

➡️ **Candidat** : inverser `air` et `air_fleet` dans la file, ou réserver une part du capital à la
croissance avant toute nouvelle liaison. À mesurer, comme le reste.

### 2. 🔴 Les bus de rabattage : 651 candidats générés, **ZÉRO bâti**

Le mécanisme est câblé de bout en bout et il est correct : `OpexRoadFeederCandidates`
(`candidates.nut:1156-1207`) cherche les villes non desservies de 200 habitants et plus à 5-40
tuiles d'un hub **rail ou aérien** existant, et `builder_road.nut:712` pose bien l'ordre
`OF_TRANSFER | OF_UNLOAD` au hub.

| | mesuré sur 105 cycles de portefeuille |
|---|---:|
| hubs vus (cumul) | 504 |
| **candidats de rabattage générés** | **651** |
| **lignes de rabattage bâties** | **0** |

**La génération marche parfaitement. C'est l'élection qui les écarte, 100 % du temps.**

**Cause identifiée, une jambe vérifiée** : le bonus de rabattage écrit `roi`, `ratio` et
`profitAnnual` (`candidates.nut:1200-1203`), **jamais `revenueAnnual`**. Or le sac à dos trie sur
`budgetScore * 75 + opcodeScore * 25` (`projects.nut:332`) et **les deux scores sont calculés à
partir de `candidate.revenueAnnual`** (`:79-80`), puis le re-tri final `byOpcodes` refait le même
calcul. **Le +60 % tombe donc entièrement dans des champs que la sélection ne lit jamais.**

C'est **exactement le défaut de §0 septdecies point 2** pour les bonus fret (+40 %, +35 %), à un
endroit de plus : le bonus vit dans `ratio`/`roi`, la décision vit dans `revenueAnnual`.

⚠️ Ce qui reste à mesurer : un feeder est-il seulement *financé* par le sac à dos avant d'être
écarté au re-tri, ou est-il éliminé dès le premier tri ? Un compteur sur le jeu financé le dira.
Ne pas coder le correctif avant.

### 3. Le compteur d'opcodes route existe déjà — et la constante n'est pas si mauvaise

Demandé : un compteur d'opcodes pour la route. **Il est déjà là** : `RB|yy|idx|1|planOps|buildOps`
(`main.nut:1284`) porte la planification et la construction de chaque tentative, et le parseur les
expose en `plan_ops` / `build_ops` par tentative.

Mesuré, 5 graines × 3 ans, 21 tentatives :

| | plan | construction | total |
|---|---:|---:|---:|
| tentative réussie | 45 000 - 94 000 | 230 000 - 375 000 | **~350 000** |
| tentative échouée | 38 000 - 212 000 | 0 | **~150 000** |

Contre `PROJECT_ROAD_TRANSACTION_OPS = 287 000`, constante actuelle : **l'ordre de grandeur est
bon** (facteur 1,2 sur les succès, 1,9 sur les échecs). Ce qui manque n'est donc pas la mesure
mais **la variabilité** : la constante ignore qu'un échec coûte le tiers d'un succès, et la route
échoue 2 fois sur 3 (21 tentatives → 7 lignes).

⚠️ Un estimateur dépendant de la distance ne peut PAS être calibré sur ces données : toutes les
lignes routières bâties font 20 à 25 tuiles (`ROAD_MAX_DISTANCE = 25`), il n'y a aucun levier.

### 4. Temps de voyage et de chargement, valable pour tous les modes

Les ingrédients existent déjà dans les quatre modes : `oneWayDays` est calculé partout
(`economy.nut:69`, `builder_air.nut:139`, `builder_water.nut:251`, et porté par le candidat
routier), `roundTripDays` et `headwayDays` en plus pour le rail et l'air.

Ce qui manque est le branchement : ajouter au **dénominateur** du ROI le revenu immobilisé pendant
le trajet et l'attente, à la manière de `lostOpportunity` (§0 tervicies point 2). Réglage
`transit_cost` (pour mille, défaut 0 = neutre), appliqué uniformément dans `OpexEconomics` et ses
trois homologues modaux. **C'est un changement de classement : il se banche.**

---

## 3 quater. 🔶 `transit_cost` : le temps de voyage et de chargement au dénominateur du ROI (demandé le 2026-09-02)

**Non commencé.** Placé au backlog derrière les trois chantiers en cours (budget actualisé du
portefeuille, refleet aérien dans le portefeuille, branchement du bonus feeder).

### Ce que c'est

Notre ROI est `profitAnnual * 1000 / capital` (`economy.nut:247`) : le dénominateur ne contient que
le capital **construit**. Il ignore entièrement la durée pendant laquelle la marchandise est
immobilisée en transit et en attente — donc, à coût de construction égal, une liaison longue et
lente vaut autant qu'une liaison courte et rapide.

AAAHogEx porte ce terme explicitement (§0 tervicies point 2, `estimator.nut:78-88`) :

```squirrel
lostOpportunity = routeIncome * (cruiseDays + waitingInStationTime) / 365;
cost = max(1, price * vehiclesPerRoute + buildingCost + lostOpportunity);
roi = routeIncome * 1000 / cost;
```

### Pourquoi c'est faisable tout de suite

**Les ingrédients existent déjà dans les quatre modes** — c'est du branchement, pas du calcul neuf :

| mode | ce qui est déjà calculé | où |
|---|---|---|
| rail | `oneWayDays`, `roundTripDays`, `headwayDays` | `economy.nut:69`, `:95` |
| air | `oneWayDays`, `roundTripDays`, `headwayDays` | `builder_air.nut:139-141`, `:187` |
| eau | `oneWayDays` | `builder_water.nut:251` |
| route | `oneWayDays` porté par le candidat | panneau `OT|`, `main.nut:1295` |

### Forme proposée

Réglage `transit_cost` en **pour mille**, défaut **0** (neutre, chemin actuel bit-à-bit), appliqué
uniformément dans les quatre calculs d'économie :

```
transitDays = ("roundTripDays" in eco) ? eco.roundTripDays : 2 * oneWayDays
immobilise  = revenueAnnual * transitDays * TRANSIT_COST_PERMILLE / (365 * 1000)
roi         = profitAnnual * 1000 / (capital + immobilise)
```

⚠️ **C'est un changement de CLASSEMENT, pas une correction** : il se banche en apparié 20 graines
avant toute adoption, comme `rail_terrain_factor` et `air_presite`.

⚠️ **Le chargement n'est pas modélisé aujourd'hui.** Seul le fret rail et le fret routier posent
`OF_FULL_LOAD_ANY` à la source ; l'attente qui en résulte n'apparaît nulle part. Première version :
ne compter que le voyage. Le chargement demande sa propre mesure et ne doit pas être deviné.

⚠️ **Interaction connue** : `roi` est le champ sur lequel `OpexProjectModeBetter` élit le mode d'un
couple O/D (`projects.nut:136`), mais le sac à dos, lui, trie sur `budgetScore`/`opcodeScore`
calculés depuis `revenueAnnual` (`:79-80`). Un terme ajouté au seul `roi` n'atteindra donc que
l'élection modale — le même piège que les bonus fret (§0 septdecies point 2) et que le bonus feeder
(§0 quinvicies point 2). Décider explicitement des DEUX branchements, ou constater qu'on n'en veut
qu'un.

---

## 0 sexvicies. 🔴 POURQUOI ZÉRO FEEDER : six verrous, dont deux tuent indépendamment (2026-09-02)

Suite de §0 quinvicies point 2 (651 candidats générés, 0 bâti). Tracé complet du chemin d'un
candidat de rabattage. **Les deux verrous de tête ont été relus et vérifiés dans le source.**

### 🔴 1. L'arrêt de bus n'est JAMAIS rattaché au hub — le mécanisme est inopérant de bout en bout

```squirrel
builder_road.nut:590   local okA = stubConnectedA && AIRoad.BuildRoadStation(plan.stopA.tile,
                              plan.stopA.front, plan.vehType, AIStation.STATION_NEW);
builder_road.nut:607   local okB = stubConnectedB && AIRoad.BuildRoadStation(plan.stopB.tile,
                              plan.stopB.front, plan.vehType, AIStation.STATION_NEW);
```

`candidate.hubStationId`, que `OpexRoadFeederCandidates` prend soin de renseigner
(`candidates.nut:1198`), **n'est lu nulle part**. Les deux arrêts sont posés en `STATION_NEW`.

Conséquence : l'arrêt de bus au pied de l'aéroport est une **gare distincte** de l'aéroport.
L'ordre `OF_TRANSFER | OF_UNLOAD` (`builder_road.nut:712`) y dépose les passagers, et **aucun avion
ne dessert cette gare-là**. Les passagers resteraient bloqués sur le quai pour toujours.

➡️ **Même si tous les autres verrous sautaient, la fonctionnalité ne marcherait pas.** C'est le
correctif à faire en premier, et il conditionne tous les autres : passer `candidate.hubStationId`
à `BuildRoadStation` pour l'extrémité hub.

### 🔴 2. Le planificateur exige que le hub PRODUISE des passagers — un feeder y décharge

```squirrel
builder_road.nut:382   local radiusB = candidate.dstTown >= 0 ? ROAD_TOWN_SEARCH_RADIUS
                                                              : ROAD_INDUSTRY_SEARCH_RADIUS;
builder_road.nut:383   local dstWantsProduction = candidate.kind == "pax";
...
builder_road.nut:160   if (wantProduction ? (value <= 0) : (value < ROAD_ACCEPTANCE_MIN)) continue;
```

Un feeder est créé avec `kind = "pax"` et `dstTown = -1`. Donc `dstWantsProduction = true` et
`radiusB = ROAD_INDUSTRY_SEARCH_RADIUS = 5` : le planificateur cherche, **à 5 tuiles de la tuile de
gare**, un emplacement qui *produit* des passagers. Or un aéroport est posé hors du centre-ville
(couronnes d'`OpexAirFindSite`), et **un feeder ne charge pas au hub, il y décharge**.

C'est une erreur de sémantique, pas seulement de calibrage. L'échec rend `SITEB`, et
`main.nut:1278` inscrit alors le couple dans `_abandonedPairs` : **la paire est bannie
définitivement**.

### 3. Le bonus de +60 % est invisible pour le sac à dos (confirmé)

Le bonus écrit `roi`, `ratio` et `profitAnnual` (`candidates.nut:1200-1203`), jamais
`revenueAnnual`. Le pré-tri du sac à dos classe sur `budgetScore * 75 + opcodeScore * 25`
(`projects.nut:332`) et sa fonction objectif **maximise la somme des `revenueAnnual`** : le bonus
n'entre ni dans l'un ni dans l'autre.

Un bus satellite pèse quelques milliers de livres de revenu annuel face aux dizaines de milliers
d'un train ou d'un avion. Sans le bonus, il est éliminé au tri, souvent avant même le solveur
(plafond des 64 meilleurs).

### 4. Le re-tri par `opcodeScore`, combiné à `maxBatch = 1`

Le jeu financé est re-trié sur `opcodeScore` (`projects.nut:494-500`, `PORTFOLIO_V2 = 0`), calculé
lui aussi sur `revenueAnnual`. Un seul projet est construit par cycle : un feeder en fond de
classement n'est jamais atteint.

> ⚠️ **Correction d'une estimation du rapport d'analyse** : il avançait `opcodeScore` ≈ 140-300
> pour le rail et 400-900 pour l'avion. Ce sont des estimations. **La mesure** (§0 tervicies, sur
> les panneaux `IP|` réels) donne des médianes de **1037 pour l'air, 62 pour la route et 0 pour le
> rail** — la division entière écrase le rail. La conclusion d'ordre tient ; les nombres non.

### 5. La garde `isFeeder` de `_tryBuildProjects` est du code mort

`main.nut:1254` place l'exemption `isFeeder` dans la branche **fret** (`else`), alors qu'un feeder
a `kind = "pax"` et tombe donc toujours dans la branche pax. Déjà constaté en §0 quinvicies.

### 6. La mémoire d'abandon ne distingue pas un feeder d'une liaison interurbaine

La clé d'abandon associe la ville satellite et la ville du hub : un échec interurbain antérieur
entre ces deux villes bannit aussi le feeder. À confirmer par lecture de `OpexAbandonedPairKey`.

### Ordre de correction

1. **Rattacher l'arrêt au hub** (`hubStationId` → `BuildRoadStation`) — sans lui, rien d'autre ne sert.
2. **`dstWantsProduction = false` pour un feeder** — sinon le plan échoue et la paire est bannie.
3. **Rendre le bonus visible à la sélection** — porter la valeur réseau sur ce que lisent
   `budgetScore`/`opcodeScore`, pas sur `roi` seul. Même famille que les bonus fret
   (§0 septdecies point 2) et que le futur `transit_cost` (§3 quater).
4. Nettoyer la garde morte, et vérifier la clé d'abandon.

⚠️ **Ne pas mesurer avant les points 1 et 2** : un banc sur le seul point 3 mesurerait un
mécanisme encore cassé, et rendrait « sans effet » pour la mauvaise raison.

---

## 3 quinquies. 🔶 RÉPARER LES BUS DE RABATTAGE — quatre correctifs, dans cet ordre (demandé le 2026-09-02)

**Non commencé.** Diagnostic complet en §0 sexvicies : 651 candidats générés, 0 bâti, six verrous
dont deux tuent indépendamment. Le mécanisme entier est déjà écrit ; il n'y a rien à concevoir,
seulement à réparer.

⚠️ **L'ordre n'est pas négociable.** Mesurer un correctif isolé rendrait « sans effet » pour la
mauvaise raison, comme la plantation préventive dont le −22,1 % portait sur du code cassé.

### Étape 1 — rattacher l'arrêt au hub (sans elle, rien d'autre ne sert)

`builder_road.nut:590` et `:607` posent les deux arrêts en `AIStation.STATION_NEW`, alors que
`candidate.hubStationId` est renseigné et jamais lu. Passer cet identifiant à `BuildRoadStation`
pour l'extrémité hub. **Sans ça, `OF_TRANSFER | OF_UNLOAD` dépose les passagers dans une gare
qu'aucun avion ni train ne dessert : la fonctionnalité ne peut pas marcher.**

À vérifier en même temps : l'écart de gare (`station_spread`) autorise-t-il le rattachement à la
distance où l'arrêt est posé ? Et le rattachement passe-t-il par `join_max_distance`, déjà utilisé
côté rail ?

### Étape 2 — un feeder décharge, il ne charge pas

`builder_road.nut:383` : `dstWantsProduction = candidate.kind == "pax"`. Un feeder est `pax`, donc
le planificateur exige que la tuile de hub **produise** des passagers dans un rayon de 5
(`dstTown = -1` → `ROAD_INDUSTRY_SEARCH_RADIUS`). Forcer `false` quand `candidate.isFeeder`.
Sans ça le plan rend `SITEB` et `main.nut:1278` **bannit la paire définitivement**.

### Étape 3 — rendre la valeur réseau visible à la sélection

Le bonus de +60 % écrit `roi`, `ratio` et `profitAnnual` (`candidates.nut:1200-1203`), jamais
`revenueAnnual` — le seul champ que lisent `budgetScore` et `opcodeScore`, donc le tri du sac à
dos, sa fonction objectif et le re-tri final. **Décider explicitement où porter la valeur réseau**,
et ne pas se contenter d'un bonus sur `roi` qui serait cosmétique. Même famille que les bonus fret
(§0 septdecies point 2), que `transit_cost` (§3 quater) et que le refleet aérien (§0 septvicies).

### Étape 4 — hygiène

- `main.nut:1254` : la garde `isFeeder` est dans la branche **fret**, alors qu'un feeder est `pax`.
  Code mort.
- Vérifier `OpexAbandonedPairKey` : la clé ne distingue pas un feeder d'une liaison interurbaine
  entre les deux mêmes villes, donc un échec antérieur peut bannir le feeder par ricochet.

### Ce qui se mesure ensuite

Une fois 1 et 2 faits, un simple diagnostic 5 graines suffit à savoir si un feeder se bâtit **et
si les passagers embarquent réellement** (note de gare du hub, cargo en attente à l'arrêt de bus).
Le banc apparié ne vient qu'après, sur l'étape 3.

---

## 0 septvicies. 📐 PRINCIPE : régler l'existant avant de construire du neuf (décidé le 2026-09-02)

**Décision de l'utilisateur, qui vaut au-dessus des mécanismes particuliers.**

> La note de gare est un multiplicateur, pas un bonus. **Il ne faut construire de nouvelles lignes
> qu'après avoir bien réglé celles qui sont déjà construites.**

C'est un principe d'**ordonnancement**, pas d'arbitrage. Une ligne mal servie ne perd pas
seulement le trafic qu'elle ne transporte pas : sa note de gare s'effondre, et la note multiplie
tout le reste (`docs/mecanique_jeu.md` §3 — 51 % de la note vient du délai depuis le dernier
ramassage). Une deuxième ligne médiocre à côté d'une première mal réglée dégrade les deux.

Conséquence opérationnelle : la croissance de flotte, l'allongement de rame, la seconde voie, les
arrêts supplémentaires — tout ce qui **densifie l'existant** — doit passer **avant** ce qui ajoute
une liaison, et doit être servi sur la trésorerie en premier. Ce n'est pas une compétition à
arbitrer dans un portefeuille : c'est un ordre.

### Ce que ça tranche, et ce que ça abandonne

**Abandonné : faire concourir le refleet aérien DANS le portefeuille** (§0 quinvicies point 1
proposait les deux voies ; la voie « portefeuille » est écartée par cette décision). Le mécanisme
a été écrit, mesuré, puis retiré du dépôt — l'historique le garde (`f23e1e4`, révoqué).

Le banc apparié 20 graines × 3 ans, pour mémoire :

| métrique | écart | $t$ | signes |
|---|---:|---:|---|
| `company_value` | +4,94 % | +1,18 | 10/10, $p = 1{,}00$ |
| `profit_year` | +5,20 % | +1,15 | 12/8, $p = 0{,}50$ |
| `profit` | +4,17 % | +0,51 | 10/10 |
| `performance_history` | +1,16 % | +0,54 | 11/7 |

**Les quatre métriques penchent du bon côté, aucune ne conclut** — sous le plancher de détection du
banc. À retenir : contrairement à `portfolio_fresh_budget`, ce mécanisme n'était pas nocif. Il est
retiré par **décision de conception**, pas par verdict de mesure, et c'est une distinction qui
compte si on y revient.

### Ce qui reste à faire sous ce principe

1. **Ordonnancer, pas arbitrer** : servir `air_fleet` (et les équivalents rail/route) **avant**
   `air` et `projects` dans la file (`main.nut:429-440`), ou leur réserver une part de la caisse.
   La mesure dit que le blocage est la trésorerie à 31 refus sur 32 — c'est donc l'ordre de
   service qui décide, pas le classement.
2. Étendre le principe aux autres modes : `rail_refleet` (second train, double voie) et
   `road_refleet` existent déjà et sont servis, eux aussi, après la construction neuve.

### Appliqué : `fleet_before_new`, défaut **1** (2026-09-02)

L'échange est fait : la tâche `air_fleet` passe **avant** `air` dans la file. Réglage
`fleet_before_new`, **défaut 1** — adopté sur décision de conception, le banc vient valider et non
autoriser ; 0 rejoue l'ordre historique pour que la comparaison reste possible.

⚠️ **Piège évité, à ne pas réintroduire** : `this._taskQueue` est bâtie dans le **constructeur**,
qui s'exécute AVANT `Start()` et donc avant toute lecture de réglage. Un `FLEET_BEFORE_NEW ? … : …`
dans la liste littérale aurait figé le repli et rendu le réglage inopérant. L'échange a lieu dans
`Start()`, une fois la valeur connue.

### 🔶 Reste ouvert : intégrer la CONSTRUCTION de lignes aériennes au portefeuille

Demandé le 2026-09-02, non commencé. La tâche `air` bâtit des lignes neuves **hors** de tout
arbitrage : §0 unvicies a mesuré que **11 des 12 lignes aériennes sont bâties hors portefeuille**,
pour 64,5 % du capital. Passer `air_fleet` devant règle l'ordre de service, **pas** le
court-circuit : `air` continue de choisir seule ce qu'elle construit et de le payer avant que le
portefeuille n'arbitre quoi que ce soit.

L'intégration devra donc, à terme, supprimer la tâche `air` au profit du seul chemin
`_tryBuildProjects` (qui sait déjà bâtir de l'aérien, `mode == "air"`). Deux obstacles connus
avant d'y toucher :

1. `_tryBuildAir` porte des plafonds et une logique de hub (`AIR_STARTER`, `AIR_HUB`,
   `maxPerYear`/`maxTotal`) que le chemin portefeuille ne réplique pas entièrement.
2. §0 undecies dit qu'AAAHogEx gagne par la **ruée aérienne** et que nous sommes déjà loin derrière
   en nombre d'appareils. Subordonner l'aérien à un arbitrage qui l'a jusqu'ici peu élu est un
   risque réel — c'est précisément pour ça que ça se mesure au lieu de se décréter.

### ⚠️ Banc 3 ans de `fleet_before_new` : NÉGATIF, et significativement

`docs/bench_fleet_before_new_3y.json`, 20 graines, bras 0 (ordre historique) contre 1 (flotte servie en premier).

| métrique | écart | $t$ | signes |
|---|---:|---:|---|
| `profit_year` | **−20,40 %** | **−3,53** | 4/16, $p = 0{,}012$ |
| `profit` | **−23,71 %** | **−3,28** | 5/15, $p = 0{,}041$ |
| `company_value` | −7,44 % | −1,63 | 7/13, $p = 0{,}26$ |
| `performance_history` | −3,70 % | −0,77 | 8/11 |

**Le principe, appliqué à l'aérien sur 3 ans, coûte du profit — et le signal est net**, bien
au-dessus du bruit habituel du banc.

Hypothèse à tester avant d'en conclure quoi que ce soit : **3 ans est la phase de RUÉE**. §0
undecies a mesuré qu'AAAHogEx gagne en posant des liaisons vite et en nombre ; retarder une
liaison neuve pour densifier une ligne existante est peut-être exactement le mauvais arbitrage
tant que les sites sont libres, et le bon une fois la carte prise. **Banc 10 ans lancé**
(`docs/bench_fleet_before_new_10y.json`) : c'est lui qui dit si le principe vaut à l'horizon où
il devrait payer.

⚠️ **Le défaut est à 1, donc la ligne de base du banc a bougé.** Toute comparaison ultérieure doit
en tenir compte. Si le banc 10 ans confirme le 3 ans, remettre le défaut à 0 et conserver le
réglage comme instrument.

---

## 3 sexies. 🔶 PORTEFEUILLE INCRÉMENTAL : découper l'évaluation en petites tâches et rafraîchir en continu (idée du 2026-09-02)

**Non commencé. Refonte, pas correctif** — à traiter comme telle : elle remplace plusieurs items
ouverts au lieu de s'ajouter à eux.

### L'idée

Le portefeuille cesse d'être un calcul monolithique mensuel. Il devient une **chaîne de petites
tâches**, chacune tenant dans un tour de file, et l'état vit entre les passages :

1. **Recensement par mode, revenu seulement.** Une tâche par mode — aérien, puis rail, puis eau,
   puis route — qui énumère les projets possibles et calcule leur **chiffre d'affaires potentiel**.
   **Pas le coût.**
2. **Évaluation du coût à la demande, et seulement quand il reste du temps de calcul.** On part du
   projet au plus fort chiffre d'affaires potentiel et on descend. Chaque évaluation rend un coût
   réel, donc un **ROI — opcodes compris**.
3. **Insertion continue.** Le projet évalué entre au portefeuille, trié par ROI.
4. **La sélection devient triviale** : prendre le meilleur projet **compte tenu de la trésorerie
   disponible à cet instant**.

### Pourquoi c'est la bonne forme, mesures à l'appui

**a) Ça met l'opcode là où il coûte vraiment.** Le recensement est bon marché ; c'est
l'**évaluation du coût** qui est chère, et de façon très inégale : un projet rail coûte
**23,4 M d'opcodes** en médiane (8 600 itérations d'A\* × 2 700) contre **100 000** pour un
aéroport et **~211 000** pour une tentative routière (§0 tervicies, §0 quinvicies point 3).
Aujourd'hui on paie ce prix pour **tous** les candidats, puis on n'en construit **qu'un** :
§0 vicies a mesuré 203 projets financés pour 43 tentatives, **ratio 4,7:1**. Évaluer le coût
uniquement en descendant depuis le meilleur revenu, c'est appliquer au portefeuille lui-même le
principe fondateur du projet — l'opcode est une ressource.

**b) Ça résout le budget périmé SANS l'effet mesuré.** `portfolio_fresh_budget` (§0 unvicies suite,
banc `docs/bench_fresh_budget_3y.json`) rejouait le sac à dos contre la caisse du moment :
**profit −19,25 %, $t = -2{,}12$, $p = 0{,}041$**. La cause probable est que le sac à dos rend
l'ensemble **vide** dans 127 cas sur 201 quand la caisse est petite et les projets indivisibles.
« Prendre le meilleur projet finançable maintenant » est une règle **différente** — et c'est
justement celle que l'ancien comportement approchait en parcourant une liste périmée en sautant
les inabordables. Cette refonte fait donc *bien* ce que `portfolio_fresh_budget` faisait *mal*.

**c) Ça supprime la falaise mensuelle.** Aujourd'hui `catalog` regénère une fois par mois
(`main.nut`, garde `_lastCatalogMonth == ym`) et tout est figé entre-temps. Le rafraîchissement
continu supprime la notion même de portefeuille périmé.

**d) 🔑 Ça rend enfin vivants tous les bonus qui sont aujourd'hui cosmétiques.** C'est
l'argument le plus fort et il n'est pas évident. Le classement se fait aujourd'hui sur
`budgetScore`/`opcodeScore`, **tous deux calculés sur `revenueAnnual`** : tout ce qui est écrit
dans `roi` n'est jamais lu par la sélection. C'est la cause commune de trois défauts déjà mesurés :

- les bonus fret monopole +40 % et chaîne +35 % (§0 septdecies point 2) ;
- le bonus de rabattage +60 % (§0 sexvicies verrou 3) ;
- et le futur `transit_cost` (§3 quater), dont la note d'ouverture signalait déjà qu'il faudrait
  choisir entre deux branchements.

**Si le ROI devient l'unique nombre de classement, les trois se branchent d'eux-mêmes.** La
question « où porter la valeur réseau ? » disparaît.

**e) Le sac à dos n'a jamais servi à grand-chose.** Il sélectionne un *ensemble* sous contrainte de
capital, alors qu'**un seul projet est bâti par cycle** — et §0 vicies a mesuré que lever ce
plafond ne retient rien (`portfolio_max_batch` rejeté, 11/20 graines strictement identiques).
Remplacer un sac à dos borné par « le meilleur projet finançable » est une simplification qui
colle au régime réel.

### Ce qu'il faut trancher avant d'écrire une ligne

1. **Le classement provisoire par chiffre d'affaires est un pari.** Un projet à fort revenu peut
   avoir un ROI catastrophique : c'est exactement ce que le rail nous fait déjà, avec un capital
   sous-facturé de 19 % (§0 unvicies). L'ordre d'évaluation n'est qu'une **heuristique de priorité
   d'attention** — à documenter comme telle, et à mesurer : combien de projets faut-il évaluer
   avant que le meilleur ROI réel soit dans le lot ?
2. **Où placer le coût du recensement lui-même ?** Le rail paie déjà sa planification pendant la
   génération des candidats. Il faut séparer nettement « estimer un revenu » (bon marché) de
   « trouver un tracé » (cher), ce que `candidates.nut` ne distingue pas aujourd'hui.
3. **Invalidation.** Un état qui vit entre les passages doit savoir mourir : ville qui grossit,
   site pris par un concurrent, industrie qui ferme, ligne construite qui change les origines
   servies. Les revalidations de batch de §0 vicies donnent déjà le patron.
4. **Le ROI doit inclure les opcodes**, comme demandé — donc `expectedOpcodes` doit devenir une
   mesure et non une constante. Elle l'est déjà pour le rail (itérations × 2 700) ; elle est une
   **constante** pour l'air, l'eau et la route (§0 quinvicies point 3), et la route dispose déjà
   de la mesure réelle par tentative (panneau `RB|`).
5. **Ordre de service.** §0 septvicies (régler l'existant avant de construire) reste au-dessus :
   les tâches de densification gardent leur place devant, quel que soit le portefeuille.

### Ce que ça remplace

- `portfolio_fresh_budget` — mesuré négatif, **cette refonte est la bonne réponse au même
  problème**. Le réglage reste comme instrument, le défaut reste 0.
- `portfolio_v2` — jugé non adoptable même réparé (§0 nonies quater) ; sa raison d'être (garder les
  alternatives modales jusqu'au test de capital) est absorbée par l'évaluation à la demande.
- L'élection modale par couple O/D (`OpexProjectModeBetter`) : si chaque projet entre au
  portefeuille avec son propre ROI réel, il n'y a plus besoin d'élire un mode *avant* de connaître
  les coûts.

### ❌ Banc 10 ans : `fleet_before_new` REJETÉ, défaut remis à 0 (2026-09-02)

| métrique | 3 ans | 10 ans |
|---|---:|---:|
| `company_value` | −7,44 % ($t = -1{,}63$) | **−18,33 %** ($t = -3{,}81$, 5/15, $p = 0{,}041$) |
| `profit_year` | **−20,40 %** ($t = -3{,}53$) | **−11,54 %** ($t = -2{,}70$, 3/17, **$p = 0{,}003$**) |
| `profit` | −23,71 % ($t = -3{,}28$) | −10,06 % ($t = -1{,}91$) |

**L'hypothèse « 3 ans est la phase de ruée, ça paiera à 10 » est RÉFUTÉE** : c'est pire à 10 ans,
et le signal y est plus fort. Deux horizons, deux bancs appariés de 20 graines, même verdict.

**Lecture : pour l'aérien, la LARGEUR bat la PROFONDEUR.** Une liaison neuve ouvre un flux entier
et un capital de ~94 000 £ qui travaille ; un appareil de plus n'ajoute qu'une tranche marginale
d'une ligne déjà servie. Le raisonnement sur la note de gare reste juste — il est simplement
**dominé**. Ça recoupe §0 undecies : AAAHogEx gagne en posant beaucoup de liaisons, pas en
saturant les siennes.

⚠️ **Ce qui n'est PAS réfuté** : le principe de §0 septvicies pourrait rester vrai pour les modes
où une ligne neuve coûte cher et rapporte peu vite (le rail, dont le capital est sous-facturé de
19 %), ou plus tard dans la partie quand les sites libres manquent. C'est exactement l'argument de
la file dynamique de §3 septies : un ordre FIXE est faux dans un sens ou dans l'autre.
Le réglage reste exposé comme instrument, défaut 0.

---

## 3 septies. 🔶 FILE DE TÂCHES DYNAMIQUE : des priorités qui dépendent de la phase de partie (idée du 2026-09-02)

**Non commencé.** Complément direct de §3 sexies (portefeuille incrémental) et réponse à ce que le
banc de `fleet_before_new` vient de montrer.

### L'idée

L'ordonnanceur (`main.nut`, `this._taskQueue`) joue aujourd'hui une **liste figée**, écrite dans le
constructeur : `catalog → report → scrap → air → air_fleet → projects → expand → refleet →
town_growth → repay`. Chaque tâche porte déjà `dueCycle` et `enabled` — le squelette est donc
dynamique, **c'est la politique qui manque**. Il faut que l'ordre et l'activation dépendent de la
**phase de partie**.

### Ce qui prouve qu'un ordre fixe est faux

`fleet_before_new` a échangé deux tâches et mesuré **−18,3 % de valeur à 10 ans**. L'ordre inverse
est donc meilleur *aujourd'hui*. Mais le raisonnement qui motivait l'échange — la note de gare est
un multiplicateur — n'est pas faux pour autant : il est dominé **tant que des sites restent
libres**. Un ordre fixe se trompe forcément dans l'une des deux phases. **C'est la définition d'un
problème d'ordonnancement dépendant de l'état.**

### Le précédent vérifié : AAAHogEx le fait, sur l'objectif

§0 tervicies point 1 : `CalculateProfitModel` (`main.nut:781-836`) bascule le **dénominateur du
classement** selon la ressource rare — profit par livre quand elle est pauvre, profit par temps de
chantier quand les places de véhicules sont libres, profit par véhicule quand elle plafonne. Ils
appliquent à l'objectif ce que cette idée applique à la file. Les deux sont complémentaires.

### Signaux de phase déjà mesurables, sans code neuf

| signal | ce qu'il dit | mesure déjà au dossier |
|---|---|---|
| emprunt saturé | phase de contrainte de trésorerie | maxé de 1970 à 1980, 412 relevés à emprunt max |
| vivier de candidats qui s'épuise | phase de carte prise | mur mesuré **à partir de 1982** |
| places de véhicules restantes | plafond de flotte | test exact d'AAAHogEx (`room >= 100 && current < max*7/10`) |
| refus de croissance pour trésorerie | l'argent est le mur | **31 sur 32**, panneau `FR|` |
| nombre de lignes et de gares | densité atteinte | déjà dans les campagnes |

### Ce qu'il faut trancher

1. **Combien de phases, et définies par quoi ?** Deux (ruée / consolidation) suffisent peut-être.
   Ne pas inventer une machine à états avant d'avoir mesuré que deux régimes se distinguent.
2. **La politique se mesure comme un réglage**, pas comme une évidence : chaque règle de bascule
   est un bras de banc. La leçon de `fleet_before_new` est précisément qu'un raisonnement juste
   peut donner un ordre faux.
3. **Le coût de la décision.** Réévaluer la phase à chaque tour de file coûte des opcodes ;
   la recalculer une fois par mois suffit probablement.
4. **Interaction avec §3 sexies** : si le portefeuille devient incrémental, une partie des tâches
   deviennent des étages d'évaluation. La politique de phase doit alors arbitrer **le temps de
   calcul** entre recensement, évaluation de coût et construction — pas seulement l'ordre.

---

## 3 octies. 🔶 ESTIMATEUR D'OPCODES APPRIS, sur la longueur ET le terrain (idée du 2026-09-02)

**Non commencé.** Demandé explicitement : sortir des constantes tirées de moyennes, et apprendre
le coût en opcodes en fonction de la longueur de la route et du terrain.

### Verdict : ça a du sens, et les données disent pourquoi — mais sous deux conditions strictes

**Ce qui justifie l'idée, mesuré sur les 15 tentatives rail de `docs/rail_cost_shielded_v2.json` :**

```
iterations ~ distance  :  R2 = 0,20        (pente 110 iterations/tuile)
iterations             :  min 950, mediane 8 600, max 20 850
opcodes / iteration    :  mediane 3 105     (la constante du code dit 2 700)
```

**$R^2 = 0{,}20$.** La distance n'explique quasiment rien. Les exemples le crient : 63 tuiles →
9 350 itérations, mais 96 tuiles → 7 950 ; 84 tuiles → 20 850, mais 125 tuiles → 13 800. **Le
prédicteur actuel est une table de nœuds sur la seule distance** (`KNOT_ITERATIONS_V1/V2`,
`candidates.nut:91-92`) : il ne peut pas faire mieux que ce $R^2$.

Ce qui manque est **le terrain**, et le dossier a déjà mesuré que c'est là que ça se joue —
`ponts_tunnels_v3` : le taux de `PATHLIM` passe de **1,9 %** sans eau sur le corridor à **60,7 %**
au-delà de 21 tuiles d'eau, et les AUC univariées des features de corridor valent 0,76 (eau),
0,75 (inconstructible), 0,72 (dénivelé).

Au passage : la constante `PROJECT_RAIL_OPS_PER_ITERATION = 2 700` est **15 % trop basse**
(médiane réelle 3 105) — un correctif d'une ligne, indépendant du reste.

### Condition 1 — le coût des features doit être inférieur à ce que la prédiction rapporte

C'est **le** point qui peut tuer l'idée, et il se mesure avant d'écrire le modèle. Échantillonner
un corridor coûte des opcodes ; si ce scan coûte une fraction notable des 23,4 M d'un A\* rail,
on n'a rien gagné. À mesurer d'abord : **prix d'un scan de corridor en opcodes**, contre
**opcodes économisés** en n'engageant pas les A\* voués à `PATHLIM`.

Le calcul est favorable *a priori* — éviter un seul abandon rail économise des millions
d'opcodes — mais « a priori » n'est pas une mesure.

### Condition 2 — le modèle doit tenir en Squirrel

Pas de numpy à l'exécution. **On apprend hors ligne, on embarque des coefficients.** Formes
acceptables : une régression linéaire sur 3-4 features, ou une table de nœuds à deux entrées
(distance × eau du corridor) — c'est-à-dire exactement ce que `KNOT_ITERATIONS_V*` est déjà, en
une dimension. **Ce n'est donc pas un changement de paradigme : c'est le même artefact, mieux
ajusté et mieux nourri.**

### Cible à apprendre : deux problèmes, pas un

L'itération d'A\* n'est pas une grandeur lisse — elle est dominée par « le chemin est-il bloqué ».
Le bon estimateur est donc composite :

```
opcodesAttendus = P(abandon) * plafondIterations + (1 - P(abandon)) * E[iterations | succes]
                  puis x opcodes_par_iteration
```

- **une classification** — la tentative va-t-elle rendre `PATHLIM`/`ABND` ? C'est là que les
  features d'eau et d'inconstructible ont leurs AUC de 0,75 ;
- **une régression** sur les itérations des tentatives réussies.

### Ce qui existe déjà et ce qui manque

| | état |
|---|---|
| vérité terrain rail | ✅ `rail_attempts` porte `distance`, `iterations`, `opcodes`, `reason`, `iteration_budget` |
| vérité terrain route | ✅ panneau `RB|` : `plan_ops` et `build_ops` par tentative |
| features de terrain | 🔶 mesurées en campagne v3 (`corridor_water/unbuildable/slope`) mais **pas calculées en jeu par OpexAI** |
| protocole d'apprentissage | ✅ `GroupKFold` par graine, déjà rodé (`docs/phase3_ml.md`) |
| volume | 🔴 **15 tentatives rail sur 5 graines × 3 ans** — très insuffisant. Une campagne dédiée est nécessaire |

⚠️ **Pour la route, il n'y a aucun levier sur la distance** : toutes les lignes bâties font 20 à
25 tuiles (`ROAD_MAX_DISTANCE = 25`). Un modèle routier dépendant de la longueur exige d'abord
une campagne à bande élargie, sinon on ajustera du bruit.

### Ce que l'estimateur sert vraiment — et pourquoi une précision modeste suffit

Dans le portefeuille incrémental de §3 sexies, `expectedOpcodes` entre dans le ROI et décide
**l'ordre d'évaluation**, c'est-à-dire à quoi on consacre son attention. Une erreur y coûte de
l'attention, **pas de l'argent** : la fonction de perte est indulgente. Un modèle grossier mais
non biaisé vaut donc déjà beaucoup, et il n'est pas nécessaire d'attendre un modèle fin pour
gagner. À dire explicitement dans la mesure, pour ne pas sur-investir.

---

## 3 nonies. 🔶 DOCTRINE DE PARTIE EN SIX PHASES, et le bonus d'occupation qui la déclenche (2026-09-02)

**Idée de l'utilisateur.** C'est la **politique** qui manquait à la file dynamique de §3 septies :
celle-ci disait « il faut des priorités dépendantes de la phase », celle-ci dit **lesquelles**.

### La doctrine

1. **Début de partie : construire un maximum d'aéroports.**
2. **Saturer ces aéroports** (flotte).
3. **Construire des lignes de passagers vers ces aéroports** (rabattage).
4. **Acheter encore plus d'avions dès que le budget le permet.**
5. **Se positionner sur les industries non occupées** — l'argent rentre, on passe au fret.
6. **Concurrencer les autres sur leur propre terrain.**

### Le mécanisme qui la déclenche : mesurer l'OCCUPATION, pas seulement la nôtre

Aujourd'hui, `OpexOriginServed` (`candidates.nut:396-404`) ne regarde **que nos propres lignes** :
un concurrent installé sur une ville est parfaitement invisible pour nous. C'est le trou que cette
idée comble.

Le jeu donne la réponse directement, et **OpexAI n'utilise ces deux appels nulle part** :

```
AITown.GetLastMonthTransportedPercentage(town, cargo)          // script_town.hpp:228
AIIndustry.GetLastMonthTransportedPercentage(industry, cargo)  // script_industry.hpp:160
```

🔑 **C'est un signal très bon marché** : un appel par ville ou par industrie, aucun balayage de
carte — à comparer au scan de corridor de §3 octies, dont le coût est justement le point qui peut
tuer l'idée. Ici, la question du coût ne se pose pas.

Sémantique exacte, à ne pas confondre : le pourcentage compte **tout transport, le nôtre inclus**.
Donc **0 % = personne ne la dessert** (ni nous ni un concurrent), ce qui est précisément le
critère voulu pour les phases 1 et 5 ; et un pourcentage **élevé** désigne le terrain d'un
concurrent, ce qui est le critère de la phase 6. **Le même nombre sert aux deux bouts de la
doctrine, avec le signe inversé.**

⚠️ **Où porter le bonus** : surtout pas dans `roi` seul. Le classement actuel se fait sur
`budgetScore`/`opcodeScore`, calculés sur `revenueAnnual` — c'est le piège commun aux bonus fret,
au bonus de rabattage et à `transit_cost` (§0 sexvicies verrou 3). Sous le portefeuille incrémental
de §3 sexies, où le ROI devient l'unique nombre de classement, la question disparaît.

### Phase par phase : ce qui existe, ce qui est mesuré, ce qui manque

| phase | état | ce que la mesure dit déjà |
|---|---|---|
| **1. max d'aéroports** | partiellement fait | La direction est **confirmée deux fois** : `fleet_before_new` rejeté à 3 et 10 ans — la largeur bat la profondeur. Mais on ne pose que **2,4 lignes aériennes par partie** (5 graines × 3 ans) contre 35 appareils chez AAAHogEx (§0 undecies). Plafonds réels : la trésorerie, et **40 % d'échec** des tentatives aériennes (§0 duovicies) |
| **2. saturer** | mécanisme là, inerte | Refusé **31 fois sur 32 pour trésorerie**, jamais pour le plafond d'aéroport ; 1,6 avion par ligne pour un plafond de 16 (§0 quinvicies) |
| **3. rabattage** | 2 verrous levés le 2026-09-02, 1 reste | 651 candidats générés, **0 bâti**. La jointure au hub et le critère de site sont réparés ; le verrou restant est l'**élection** (§0 sexvicies, §3 quinquies) |
| **4. plus d'avions** | = phase 2 avec du budget | Même mécanisme, même blocage : la caisse |
| **5. industries libres** | **rien** | Le fret existe (rail et route) mais **aucun critère d'occupation** n'entre dans le classement |
| **6. concurrencer** | **rien, et c'est le plus risqué** | Voir ci-dessous |

### Les trois tensions à ne pas balayer

1. **Phase 2 après phase 1 n'est pas ce qui a été mesuré.** `fleet_before_new` a mesuré « saturer
   **avant** de construire » : −18,3 % de valeur à 10 ans. La doctrine dit « saturer **après** avoir
   construit le maximum ». C'est une règle **différente**, non testée — et elle n'est réalisable
   que si la bascule de phase est réelle et détectable. C'est exactement l'objet de §3 septies.
2. **La phase 6 contredit toute la conception actuelle**, qui écarte les origines déjà servies. Et
   se poser sur le terrain d'un concurrent **divise le cargo entre les deux gares** : les deux
   notes de gare baissent. C'est peut-être un jeu à somme négative — à mesurer avant de croire que
   « concurrencer » est un gain. Sa place en dernier est justifiée.
3. **La doctrine est une hypothèse, pas un résultat.** Elle est cohérente avec tout ce qu'on a
   mesuré, ce qui est déjà beaucoup, mais chaque bascule reste un bras de banc. La leçon du jour
   est qu'un raisonnement juste — la note de gare est un multiplicateur — a produit un ordre qui
   coûte 18 % de valeur.

### Le plus petit pas utile

Ne pas construire la machine à six états d'un coup. **Un seul bras mesurable, et il est petit** :
ajouter le pourcentage transporté comme critère au classement aérien, pour préférer une ville que
personne ne dessert. Ça teste la phase 1 et le mécanisme d'occupation **en même temps**, sans
toucher à l'ordonnanceur.

---

## 3 decies. 📋 TÂCHES RESTANTES au soir du 2026-09-02 — liste consolidée

Récapitulatif de tout ce qui est ouvert, y compris ce qui a été identifié en passant aujourd'hui et
qui n'avait pas encore sa ligne. Journal de la journée : `docs/journal_2026-09-02.md`.

### A. Les pistes de fond (tout le reste est secondaire)

| # | tâche | pourquoi elle est en tête |
|---|---|---|
| **A1** | 🔴 **Dénominateur du classement dépendant de la ressource rare** (§0 tervicies point 1, §3 septies) — **ITEM DE TÊTE au 2026-09-03 soir** | Sept mécanismes de capital mesurés, sept non adoptés : **le capital n'est pas le mur**. AAAHogEx bascule son dénominateur, nous jamais. ➡️ **Troisième confirmation indépendante le 2026-09-03** : le signe de l'effet d'`air_demand_plan` suit la RICHESSE (Spearman −0,725, 7/8 gagnantes chez les pauvres, 0/11 chez les riches — §0 trigesies). ➡️ Et **l'objection qui bloquait A1 tombe** : « dans notre régime, pauvre, AAAHogEx divise par le capital comme nous » reposait sur un horizon de 3 ans ; **à 10 ans, 18 graines sur 20 passent son test `_IsRich`** (valeur médiane 3,99 M£, revenu mensuel médian 73 k£). Nous SOMMES riches, et nous optimisons encore une contrainte qui ne lie plus |
| **A2** | **Volume de liaisons** — largeur contre profondeur (§3 nonies phase 1) | Confirmé deux fois aujourd'hui. On pose 2,4 lignes aériennes par partie contre 35 appareils chez l'adversaire |
| **A3** | **Sonde : plafonner `iterationBudget`** à ~10 000 au lieu de 50 000, banc apparié (§0 undecies ter) | ✅ Fait (`pathfinder_hard_cap_k` = 10, bornes dynamiques à 10k max) |
| **A4** | ❌ **FAIT, MESURÉ, REJETÉ** — recherche reprenable d'un tour de file à l'autre (§0 undecies quater) | **−23,1 % de valeur, 16/20 graines perdantes** ($p = 0{,}0118$). Le gel de 7 mois est réel, mais il ne coûtait pas ce qu'on croyait. Réglage `rail_search_resumable` conservé comme instrument, défaut 0 — ❌ **RETEST FAIT sur socle segmenté (§0 undecies sexies) : REJETÉ UNE SECONDE FOIS**, −13,3 % de valeur (5/20, $p = 0{,}0414$) et surtout **−27,5 % de gares** ($t = -4{,}46$, $p = 0{,}0004$). Mécanisme identifié : `safetyDeadline` est une échéance en TICKS posée une fois (`main.nut:2847`), donc en mode reprenable la fenêtre est partagée avec la file et la recherche meurt avant d'aboutir — **A4 ampute la recherche, il ne la redistribue pas**. Défaut 0 |
| **A5** | 🟡 **FAIT, MESURÉ, RÉSULTAT NUL — adopté à 1 par décision** (§0 undecies quinquies) | Le mécanisme marche : **+12,9 % de gares** (t = +1,94), +5,5 % de véhicules, −23,5 % de trésorerie — il convertit bien les 40 % d'`ABND` en lignes. Mais la valeur est **neutre** : −3,4 %, t = −0,86, 7/20, $p = 0{,}26$ — rien de significatif. `docs/bench_rail_segmented_10y.json`. **Défaut `rail_segmented_search` = 1** : résultat nul et non négatif, médianes en hausse, réseau non amorti à 10 ans, et surtout **socle du retest d'A4**. ➡️ Referme les trois voies du pathfinder : relever ❌, redistribuer ❌, abaisser 🟡. **Le pathfinder n'est pas le goulot** |

| **A6** | 🔑 **Vecteur de tension (loi de Liebig) — le dénominateur composé, sans constantes** (§3 terdecies) | La forme qu'A1 doit prendre : on ne compare plus à un seuil, on compare des ressources entre elles. **Premier pas purement instrumental** : journaliser le vecteur, ne changer aucune décision, et répondre à « la contrainte dominante varie-t-elle au cours d'une partie ? ». Si c'est l'argent 100 % du temps, il n'y a rien à coder. ➡️ **Absorbe B2 et B4**, qui étaient des automates à états |

| **A7** | 🟢 **Architecture par ÉVÉNEMENTS au lieu du sondage périodique** (`AIEventController`) — vérifié dans la source 15.3 : `AIEventVehicleLost`, `VehicleUnprofitable`, `IndustryClose`, `TownFounded` existent, **plus quatre événements de subvention** (`SubsidyOffer`, `OfferExpired`, `Awarded`, `Expired`), `script_event_types.hpp` | Attaque **directement le goulot mesuré** : 61,2 % des transitions mensuelles sans construction avec ≥ 300 k£ en caisse. Un événement remplace un rescan complet — c'est du débit de contrôleur rendu gratuitement. `docs/cible.md` §8 |

⚠️ **A2 n'est PAS « remplacer notre A\* par `Graph.AyStar` »** — cette formulation, qui circule
encore, est sans objet : `main.nut:28` importe déjà `Pathfinder.Rail`, bâti sur `Graph.AyStar`.
Il n'y a pas d'A\* fait maison. Seule la fonction de coût est à nous.

### B. Refontes notées aujourd'hui, prêtes à être planifiées

| # | tâche | section |
|---|---|---|
| B1 | Portefeuille incrémental, découpé en petites tâches, rafraîchi en continu | §3 sexies |
| B2 | ⛔ **ABSORBÉ par A6** — file de tâches dynamique à priorités par phase : c'est un automate à états, forme écartée par l'utilisateur le 2026-09-03 | §3 septies, §3 terdecies |
| B3 | Estimateur d'opcodes appris sur longueur **et** terrain | §3 octies |
| B4 | ⛔ **ABSORBÉ par A6** — doctrine en six phases : même motif, un automate à états. Le bonus d'occupation, lui, reste une mesure utile | §3 nonies, §3 terdecies |
| B5 | Intégrer la **construction** aérienne au portefeuille (aujourd'hui hors arbitrage : 11 lignes sur 12) | §0 septvicies |

### C. Correctifs identifiés, non faits, chiffrés

| # | tâche | chiffre | où |
|---|---|---|---|
| C1 | **Débloquer l'élection des feeders** — tâche dédiée `feeders` dans l'ordonnanceur | 651 candidats → construction active | ⚠️ Fait mais restait mort jusqu'au correctif du 2026-09-02 soir (§3 quinquies + §0 undecies bis) |
| C2 | **`rail_terrain_factor`** : facteur ×1,70 sur `costTrackPerTile` | modèle 19 % sous le réel | ✅ Fait (calibré à 170 %, §0 unvicies) |
| C3 | **`PROJECT_RAIL_OPS_PER_ITERATION = 2 700` est 15 % trop bas** — médiane réelle **3 105**. ✅ Fait (calibré à 3 105) | 15 % | §3 octies |
| C4 | **Filtre de platitude préalable** sur les sites d'aéroport (rejet à ≥ 2 niveaux d'écart, à la AAAHogEx) — plus radical et moins cher qu'`air_presite`, qui nivelle avant de tester | écarterait 7 échecs sur 8 | ✅ Fait (§0 tervicies point 5) |
| C5 | **Ne plus raser l'aéroport orphelin** quand l'entretien d'infrastructure est coupé | ~25 000 £ par `BFAIL` | ✅ Fait (§0 tervicies point 6) |
| C6 | **Plafonner la distance des tentatives aériennes** — aucun succès au-delà de 212 tuiles, aucun échec en deçà de 178 | 8 échecs sur 20 | ✅ Fait (plafonné à 212 tuiles, §0 unvicies point 4) |
| C7 | **Devis réel par `AITestMode` + `AIAccounting`** avant engagement, au lieu d'un facteur correctif | devis exact gares/voie avant pose | ✅ Fait (§0 tervicies point 8) |
| C8 | **Câbler les bonus fret** (+40 % monopole, +35 % chaîne) sur ce que la sélection lit | ✅ Fait (§0 septdecies point 2) | §0 septdecies point 2 |
| C9 | **`transit_cost`** : temps de voyage au dénominateur du ROI | réglage pour mille (défaut 0), 4 modes câblés | ✅ Fait (§3 quater) |
| C10 | **`builder_water.nut:255`** : note de gare plate au lieu de `OpexStationRatingForHeadway` | ✅ Fait (§0 octodecies) | §0 octodecies |
| C11 | **`candidates.nut:166-170` + `:188`** : double pénalité empilée sur `distance > 105`, non recalibrée | ✅ Fait (§0 septdecies) | §0 septdecies |
| C12 | **La division entière écrase le rail dans `opcodeScore`** : médianes mesurées air 1037, route 62, **rail 0** | éliminé par division flottante continue | ✅ Fait (§0 tervicies) |
| C14 | 🔶 **Desserrer le GAIN de la boucle de croissance aérienne** — AAAHogEx achète `(attente − 50) / capacité` appareils, jusqu'à 4 par passage ; nous exigeons une **pleine** capacité en attente et n'ajoutons **qu'un** avion. Le mécanisme est le même, le réglage ne l'est pas | tampon 50 contre 1 pleine capacité | §0 novemvicies point 6 |
| C15 | 🔶 **Relever la CADENCE de `_resizeAirFleets`** — une croissance par ligne et par an (`lastAirFleetYear`, refus `Y`) contre un passage d'entretien chez eux. Deux réglages séparés de C14, à ne pas grouper | 1/an contre n/cycle | §0 novemvicies point 6 |
| C21 | **`expectedOpcodes` ignore `HARD_ITERATION_CAP`** : `expectedOps = candidate.iterations × PROJECT_RAIL_OPS_PER_ITERATION` (`projects.nut:122`) utilise un nombre d'itérations prédit sans borner à `HARD_ITERATION_CAP` (10 000) — ✅ Fait (`projects.nut` borne désormais à `HARD_ITERATION_CAP`) | tension opcode 1,2-1,8 mesurée au lieu de ~0,28 | §0 duotrigesies, A3 |
| C19 | **Convertir les boucles `Begin()/Next()` chaudes en pipeline `Valuate` + `Keep*`** — ✅ Fait (`catalog.nut`, `main.nut`, `tension.nut` convertis aux pipelines natifs `Valuate`/`Keep*`) | 5 opcodes/élément contre le corps entier d'une boucle Squirrel | `docs/cible.md` §8.3 |
| C20 | 🔴 **Échéance PAR MICRO-ÉTAPE, jamais globale** — prérequis de toute exécution incrémentale. `safetyDeadline` est aujourd'hui une échéance en ticks posée **une fois** (`main.nut:2847`) ; c'est elle qui a fait rejeter A4 **deux fois** (−23,1 % puis −13,3 % et −27,5 % de gares) : en mode reprenable la fenêtre est partagée et la recherche meurt avant d'aboutir | ampute au lieu de redistribuer | §0 undecies sexies, `docs/cible.md` §2.1 |
| C18 | 🔶 **Financement / prospection d'industrie** (`AIIndustryType.BuildIndustry` / `ProspectIndustry`, soumis à `economy.fund_buildings`) — créer un **débouché** là où il n'y en a pas, pour une source déjà desservie mais sous-exploitée faute d'accepteur proche. Plus spéculatif que C17 : à ne prendre qu'après lui | AAAHogEx : **0 occurrence**, comme pour les subventions | `docs/mecanique_jeu.md` §14 et §10 |
| C17 | 🔶 **Sonde subventions, en lecture seule** — combien d'offres par partie, combien portent sur une paire déjà dans notre vivier, combien expirent sans preneur, et quel multiplicateur la partie applique (`AIGameSettings`, pas une constante). Zéro construction. ➡️ **Reformulé le 2026-09-03 après lecture du source** : ne PAS scruter `AISubsidyList` en boucle — `AIEventSubsidyOffer` prévient à la publication, et `SubsidyAwarded` / `Expired` ferment le suivi. Une opportunité datée se **signale**, elle ne se sonde pas | AAAHogEx : **0 occurrence** d'`AISubsidy` sur 37 531 lignes ; AdmiralAI s'en sert | `docs/mecanique_jeu.md` §14, `docs/cible.md` §8 |
| C16 | 🔶 **Si le plafond aérien revient, le dériver de la CADENCE et non de la demande** — `jours d'aller-retour / créneau d'absorption`, divisé par le nombre de lignes qui partagent la piste (`EstimateMaxVehicles`, `route.nut:2374-2380`). L'ingrédient manquant est le `stationDateSpan` par type d'aéroport, jamais lu | remplace un plafond rejeté deux fois | §0 novemvicies points 1-2 |
| C13 | **Le sac à dos (knapsack) n'utilise pas le ROI bonifié fret de C8** — `OpexKnapsackComputeBound`/`OpexKnapsackSearch` (`projects.nut:283-286`, `:323`) additionnent encore `p.revenueAnnual` brut comme objectif, pas le ROI bonifié (monopole +40 %, chaîne +35 %). Le bonus C8 pèse donc sur le tri/seuil de sélection en amont, pas sur l'optimum retenu quand plusieurs candidats se disputent le même capital | trouvé en revue croisée agy/codex/grok du 2026-09-02, en vérifiant C8 | §C8, `projects.nut` |

### D. Mesures à refaire, parce que les anciennes ne valent plus

| # | tâche | pourquoi |
|---|---|---|
| D1 | **Remesurer `tree_planting`** | ✅ Fait (`docs/bench_tree_planting_recalibrated_3y.json`, 20 graines × 3 ans) : même après correction du bug d'enum, `tree_planting=1` dégrade `company_value` (−12,1 %, t = 1,77, 12/20 graines) et `profit_year` (−13,4 %, t = 1,88, 13/20 graines). La plantation préventive reste néfaste. **Défaut confirmé à 0**. |
| D2 | Volume de données pour B3 | 15 tentatives rail seulement ; et **aucun levier de distance côté route** (toutes les lignes font 20-25 tuiles) |

### E. Hygiène et outillage, inchangés

| # | tâche | où |
|---|---|---|
| E1 | CI GitHub : smoke 3 graines × **2 ans** avec plancher de plausibilité — ✅ Fait (`.github/workflows/ci.yml` + `sweeps/smoke_test.py`) | §8 |
| E2 | Supprimer `rail_refleet` et `air_starter`, prouvés inertes | §8 |
| E3 | Audit des 46 constantes en dur | §3 ter |
| E4 | Mesurer le headway réel des lignes de calibration de la note de gare (le −95) | §3 bis |
| E5 | `builder_rail.nut` : `AIAccounting` imbriqué non finalisé sur les branches d'échec (latent, chemin mort) | §0 octodecies |
| E6 | `catalog.nut:702-720` : `railCoverage` lu avec un an de retard — ✅ Fait (`_refreshRail` appelé avant `_refreshTowns`) | §0 novemdecies |
| E7 | `OpexJoinPathIsDedicated` armé seulement si `join != null` — un A\* peut traverser du rail existant | §0 vicies |
| E8 | 🔶 **NETTOYAGE DE CODE — débloqué le 2026-09-03 par D1** : sortir les trois mécanismes prouvés morts ou infirmés (`tree_planting` + les sept sites préventifs qu'il garde, `rail_refleet`, `air_starter`) — code gardé, constante, relecture dans `Start()`, entrée `info.nut`, liste blanche de `bench_v2.py`. ⚠️ Retirer du code **mort** ne décale pas les trajectoires (20/20 graines bit-identiques après 766 lignes supprimées le 2026-09-02) ; retirer une **lecture de réglage** en décale → banc de non-régression obligatoire, et un seul mécanisme par commit | §8, §0 nonies, D1 |
| E9 | 🔶 **`Save()` / `Load()` : OpexAI n'en a AUCUN** — vérifié, zéro occurrence dans `ai/OpexAI/`. Un rechargement de partie perd donc tout l'état (`_lines`, mémoire d'abandon, compteurs) et l'IA repart à zéro sur un réseau existant. Sans objet au banc, réel en partie humaine. Forme correcte : **états plats** (tableaux d'IDs, énumérations d'étapes), jamais d'objets ni de curseurs | `docs/cible.md` §8.3 |

### Réglages laissés comme instruments, défaut 0, mesurés et non adoptés

`portfolio_max_batch` · `air_presite` · `air_cost_probe` · `air_fleet_probe` ·
`portfolio_fresh_budget` · `fleet_before_new` · `rail_cost_probe` · `portfolio_v2` ·
`tree_planting` · `marginal_fleet` · `transit_cost` · `rail_search_resumable`

### D2. ❌ `transit_cost` — banc apparié 20 graines × 10 ans, RIEN ne bouge (2026-09-02 soir)

`docs/bench_transit_cost_10y.json`, `OpexAI` contre `OpexAI[transit_cost=1000]` (coût complet, la
valeur la plus agressive permise). Un diagnostic à 5 graines × 3 ans avait montré que le réglage
n'est pas structurellement mort : à graines égales (parties déterministes), il change bien quelles
lignes se construisent (rail 8→10, route 6→5 sur les mêmes 5 graines). Mais ce réarbitrage ne se
traduit par rien à 20 graines × 10 ans :

| métrique | témoin | `transit_cost=1000` | écart | t |
|---|---:|---:|---:|---:|
| `company_value` | 1 333 997 £ | 1 342 066 £ | +0,6 % | 0,07 |
| `profit` | 46 430 £ | 46 359 £ | −0,2 % | 0,01 |
| `profit_year` | 199 256 £ | 202 678 £ | +1,7 % | 0,17 |
| `performance_history` | 348,5 | 345,6 | −0,8 % | 0,12 |
| `median_station_rating` | 171,6 | 170,8 | −0,5 % | 1,40 |

Tous les $|t| < 1,5$ (seuil habituel de ce projet ~2), et le partage gagnant/perdant reste ~11-12/20
sur toutes les métriques de valeur — un pile ou face statistique. Le réarbitrage rail/route que le
réglage produit à la construction ne favorise donc ni l'un ni l'autre mode en moyenne : il déplace
le problème sans le résoudre. **Défaut gardé à 0.**

Note d'outillage : `sweeps/bench_v2.py` ne reconnaissait pas encore `transit_cost` (ajouté à
`info.nut` par C9 après l'écriture du validateur) — corrigé au passage (bornes 0-2000, pas 50,
identiques à `info.nut`), non commité.

---

## 3 undecies. 🔶 PLAFOND AÉRIEN DÉRIVÉ DE LA DEMANDE, et le tri des pistes issues d'AAAHogEx (2026-09-03)

Origine : la trace par avion de l'année 1 (graine 42, `docs/diag_air_vehicles.json`,
`sweeps/diag_air_vehicles.py`) et la lecture du classement d'AAAHogEx déléguée à agy le même jour.

### 1. 🔑 L'IDÉE PRINCIPALE (utilisateur) : le plafond de duplication se CALCULE, il ne se décrète pas

**On ne peut pas trancher sur les routes dupliquées sans plus de données.** La bonne forme n'est
pas un plafond posé à vue (« pas plus de N liaisons par paire ») mais une grandeur estimée :

> **cargo attendu par aller-retour dans chaque aéroport ÷ capacité totale des avions = le plafond.**

⚠️ **C'est volontairement la version naïve, et il faut la garder telle quelle au premier jet** :
elle ne tient compte ni des **aéroports futurs**, ni des **lignes futures**, qui détourneront une
part de ce cargo. C'est donc une **borne haute** du nombre d'appareils que la paire peut nourrir,
à raffiner seulement une fois mesurée.

**Pourquoi ça mord alors que le plafond actuel ne mord jamais.** Le plafond en vigueur est
*physique* (`maxPlanesForAirport` = `AIR_MAX_PLANES_PER_ROUTE`, ou 4 sur petit aéroport,
`main.nut:2320-2326`). §0 quinvicies l'a mesuré : cause `C` (plafond atteint) = **0 refus sur 32**,
pour 28 avions sur 17 lignes, soit 1,6 par ligne contre un plafond de 16. Le plafond existant ne
retient donc **rien**. Un plafond dérivé de la demande, lui, retiendrait quelque chose.

**Ce que la mesure du 2026-09-03 dit, et surtout ce qu'elle NE dit PAS.** Graine 42, une seule
paire de villes (tuiles 59980 ↔ 48086), **9 liaisons aériennes bâties dessus** entre 1970 et 1972.
Profit et revenu réels par ligne, année civile 1971 complète (panneaux `OZ`/`OO` posés par
`_reportLines`) :

| avion | ligne | bâti | coût | profit 1971 | revenu 1971 | flotte | ROI |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 0 | 1970-02-13 | 93 923 | 22 743 | 29 858 | 1 | **24,2 %** |
| 2 | 1 | 1970-02-26 | 61 523 | 90 377 | 97 492 | 1 | **146,9 %** |
| 3 | 2 | 1970-03-11 | 61 523 | 38 339 | 52 569 | 2 | 62,3 %* |
| 4 | 3 | 1970-03-24 | 61 523 | 4 010 | 11 125 | 1 | **6,5 %** |
| 5 | 6 | 1970-12-08 | 61 523 | 64 723 | 71 838 | 1 | **105,2 %** |
| 6 | 9 | 1971-02-11 | 61 523 | 26 281 | 40 511 | 2 | 42,7 %* |

\* deux appareils sur la ligne (croissance de flotte en 1971) : le chiffre agrège, il n'est pas
comparable aux lignes à un seul avion.

🔴 **Le ROI ne décroît PAS avec le rang de construction** — 24 %, 147 %, 62 %, 6,5 %, 105 %, 43 %.
L'hypothèse intuitive « chaque avion suivant capte moins » **n'est pas vérifiée sur cette graine**.
Le ROI faible de l'avion 1 s'explique par son **capital** (93 923 £, deux aéroports neufs) et non
par la demande ; tous les suivants réutilisent ces aéroports à 61 523 £. Les notes de gare
tiennent dans les 70 tout du long. **Donc : rien ne prouve aujourd'hui que les doublons soient du
gaspillage** — c'est exactement pourquoi le plafond doit être calculé avant d'être imposé.

**Ingrédients déjà disponibles pour le calculer** : `TOWN_CATCHMENT_SHARE_PCT` (part captée,
`candidates.nut:492`), la production mensuelle des deux villes déjà lue par le catalogue,
`line.planeCapacity` (déjà porté par la ligne, `main.nut:2308`), `AIStation.GetCargoWaiting`
(déjà appelé sous `MARGINAL_FLEET`, `main.nut:2315-2317`) et la durée d'aller-retour, qu'il faudra
dériver de la distance et de la vitesse catalogue.

⚠️ Rappel de §5 : **`_resizeAirFleets` ne consulte AUCUN signal de saturation** aujourd'hui — ni
part desservie, ni cargo en attente hors `MARGINAL_FLEET` (éteint par défaut). Le seul garde-fou
est `lastProfit >= 0` et la trésorerie. Le plafond calculé serait le **premier** signal de demande
du chemin de croissance aérienne.

### 2. Pistes issues de la lecture d'AAAHogEx (agy, citations vérifiées par sondage)

1. **🔶 Plancher de ROI ABSOLU.** AAAHogEx refuse tout candidat sous **20 %** de ROI
   (`main.nut:1054-1057`, `value < 200`) et met l'expansion routière en pause **365 jours** sous
   10 % (`main.nut:1048-1052`). Notre plancher est **relatif** (`PORTFOLIO_FLOOR_PCT` d'une
   fraction du meilleur profit finançable, `projects.nut:231-234`) : quand tout est mauvais, on
   bâtit quand même le moins mauvais. C'est ainsi que l'avion 4 a été acheté à **6,5 %** de ROI.
   Un plancher absolu est une **barre de rejet**, pas un changement de classement : il est
   compatible avec le plancher relatif existant et ne rejoue pas le banc du 2026-09-02.
2. **🔶 Garde de finançabilité ANTICIPÉE.** AAAHogEx vérifie que la caisse couvre les véhicules
   restants de la route en cours **plus le coût complet de la suivante**, et **diffère jusqu'à
   180 jours plutôt que de bâtir à moitié** (`main.nut:1024-1047`). Nous n'avons aucun équivalent :
   la trace de 1970 montre une caisse vidée puis huit mois de refus `insufficient_cash`.
3. **Dénominateur variable** — voir §0 tervicies, et le point 3 ci-dessous : **à ne pas copier
   maintenant.**

### 3. ⛔ Ce qui est DÉJÀ RÉFUTÉ — ne pas reproposer

Ces trois pistes ont été suggérées à l'oral le 2026-09-03 avant relecture du présent document.
Elles sont **déjà mesurées et négatives ou nulles** ; le rappel est ici pour que le prochain
passage ne les re-propose pas :

| piste | verdict déjà au dossier |
|---|---|
| Servir la flotte avant la construction neuve (`fleet_before_new`) | ❌ **−20,4 % de `profit_year`** ($t = -3{,}53$, signes $p = 0{,}012$) à 3 ans — §0 septvicies |
| Lever le plafond d'un projet par passage (`portfolio_max_batch`) | ❌ rejeté : −3,8 % de valeur, et **11 graines sur 20 sont des nuls exacts** (le lot ne se déclenche jamais) |
| Mettre le temps de voyage/chargement au dénominateur (`transit_cost`) | ❌ nul à 20 graines × 10 ans, tous les $\|t\| < 1{,}5$ — §3 quater / D2 |
| Plafonner la flotte aérienne par la demande de la ville (`air_demand_cap`) | ❌ mord fort (24/75/43 refus `Q`) mais rabote : −31 % / +7 % / nul — §3 undecies bis |
| Dimensionner le plan aérien sur la production réelle (`air_demand_plan`) | ❌ **−51,5 % de `profit_year`** ($t = -3{,}96$, 5/20, signes $p = 0{,}041$) — §0 trigesies |
| Pathfinding hiérarchique (HPA\*, découpage macro/micro) | ⛔ **répond à un problème que nous n'avons pas** : les trois voies du pathfinder sont fermées (relever ❌, redistribuer ❌ −23 %, abaisser 🟡 nul) et le segmenté A5 donne +12,9 % de gares pour une valeur **neutre** |
| « Verrouiller un corridor » en achetant du terrain (`BuyLandArea`) | ⛔ **impossible** : aucune méthode d'achat de terrain dans l'API 15.3 (ni `AITile`, ni `AICompany`). Réserver un corridor exige d'y poser du rail, au prix fort — `docs/cible.md` §8 |
| Interroger le `LinkGraph` / optimiser les correspondances CargoDist | ⛔ **doublement sans objet** : pas de `script_linkgraph.hpp` dans l'API, **et** CargoDist est désactivé par défaut (`linkgraph.distribution_pax = DT_MANUAL`), notre config ne l'active pas |
| `AIController.GetOpsLimit()` / `GetOps()` / `Break()` comme rendu de main | ⛔ **n'existent pas** : seuls `GetOpsTillSuspend()` et `Sleep()`. `Break` est un point d'arrêt de débogueur (`script_controller.hpp:175-184`) |

**Et le dénominateur adaptatif d'AAAHogEx n'est PAS la pièce à copier en premier.** Son
`CalculateProfitModel()` (`main.nut:781-806`) ne quitte le régime `roiBase` que si la compagnie est
**riche** (`_IsRich`, `main.nut:4324` : > 500 k£ *et* 100 k£/mois de revenu, ou > 2 M£) **et** hors
inflation. Dans le régime où nous perdons — pauvre, contraint par la trésorerie, très loin des
plafonds de véhicules — **AAAHogEx divise par le capital, exactement comme nous**. Copier
l'aiguillage reviendrait à copier la partie qui ne travaille pas à 3 ans. À reprendre le jour où
l'IA est effectivement riche.

### 4. Ce qui reste réellement ouvert, dans l'ordre

⚠️ **Révisé le 2026-09-03 au soir.** Le point 1 a été câblé, sondé et **banché : REJETÉ dans ses
deux formes** — `air_demand_cap` rabote sans payer (§3 undecies bis), `air_demand_plan` perd
51,5 % de `profit_year` (§0 trigesies). Ce qui reste ouvert est donc **le 2 et le 3**, et une
piste neuve issue de la lecture d'AAAHogEx : le plafond de **cadence** (§0 novemvicies), qui n'a
rien à voir avec la demande de la ville.

1. ❌ Le **plafond dérivé de la demande** (point 1) — **FAIT, MESURÉ, REJETÉ** deux fois.
2. Le **plancher de ROI absolu** (point 2.1) — le moins cher à câbler et à mesurer.
3. La **garde de finançabilité anticipée** (point 2.2).
4. Subordonner la **construction** aérienne au portefeuille — déjà ouvert en §0 septvicies, avec
   ses deux obstacles connus, et à lire avec l'avertissement de §0 undecies (AAAHogEx gagne par la
   ruée aérienne : subordonner l'aérien à un arbitrage qui l'élit peu est un risque réel).

---

## 0 octovicies. ✅ CORRIGÉ : les liaisons aériennes en double venaient d'une TUILE lue comme un StationID (2026-09-03)

Suite directe de §3 undecies. L'utilisateur avait raison sur le comportement — « `_tryBuildAir`
crée des lignes neuves entre les 2 mêmes aéroports, ça devrait être le boulot du refleet » — mais
la cause n'était ni celle qu'il supposait ni celle que j'avais avancée.

### La cause : un seul défaut de type, trois conséquences

`OpexBuildAirRoute` calcule bien les `StationID` (`builder_air.nut:831-832`) puis **rend les
TUILES** (`:898-899`, `result.stationA = airportA`). Tout `main.nut` lit correctement ces champs
comme des tuiles (`GetStationID(line.stationA)` en `:1046`, `:1319`, `:2034`) : la convention
« tuile » est la bonne. **Seul le code de hub de `builder_air.nut` les prenait pour des StationID
déjà résolus.** D'où :

1. **La garde `alreadyConnected` comparait un StationID à une tuile → structurellement TOUJOURS
   fausse.** C'est elle, et elle seule, qui devait interdire de reconnecter une paire déjà servie.
2. **La découverte de hub testait `IsAirportTile()` sur un CENTRE-VILLE** (`line.originA`) → jamais
   vraie → tous les aéroports tombaient dans le repli « orphelins », qui code `routes = 0` en dur.
3. `routes = 0` en permanence → le plafond `maxRoutes` (12) **inopérant**, et la décote de
   saturation `hubMonthly / (routes + 1)` **divisait toujours par 1**. Le ROI de chaque doublon
   était donc calculé sur le bassin ENTIER des deux villes, comme si personne ne les desservait.

⚠️ **Deux hypothèses fausses écartées en route, à ne pas resservir** : (a) `OpexAirTownServed`
fonctionne parfaitement — la sonde le montre évincer les villes 26 et 30 dès la ligne 0 (`sites`
16 → 14, aucune fausse-négative sur 926 appels) ; (b) l'arm coupable n'est pas `hubsite` (déduit à
tort de l'ordre `src`/`dst`) mais **`hubhub`**, celui qui portait pourtant la garde.

### La preuve, avant / après (graine 42, 3 ans, `docs/diag_airserved_probe.json` → `docs/diag_airfix_verify.json`)

| | lignes aériennes | arms | paires distinctes |
|---|---:|---|---:|
| avant | **9** | `newpair` 1, `hubhub` 8 | **1** (48086 ↔ 59980, neuf fois) |
| après | 6 | `newpair` 2, `hubsite` 2, `hubhub` 2 | **6** |

`hubsite` ne s'était **jamais déclenché** avant le correctif : la découverte de hub ne rendait
jamais rien d'exploitable.

### Le banc : positif sur les moyennes, MAIS porté par quelques graines

`docs/bench_air_hub_fix_3y_20seeds.json`, 20 graines × 3 ans, `air_hub_fix=1` contre `=0`, 0 échec :

| métrique | écart | t | graines gagnées | test des signes |
|---|---:|---:|---:|---:|
| `profit_year` | **+35,7 %** | **2,53** | 14/20 | 0,115 |
| `profit` | **+46,3 %** | **2,40** | 11/20 | 0,82 |
| `company_value` | **+15,8 %** | **2,06** | 11/20 | 0,82 |
| `performance_history` | +13,0 % | 1,98 | 13/20 | 0,26 |
| `median_station_rating` | −2,8 % | −1,67 | 7/20 | 0,26 |

**Lecture honnête.** C'est le premier réglage de la journée dont les moyennes franchissent à la
fois le plancher de détection (~15 % sur `company_value`) et $t = 2$ sur trois métriques de valeur.
Mais **aucun test des signes n'est significatif**, la médiane n'est que +53 k£, et **les 3
meilleures graines apportent 72 % du gain total**. C'est un gain à forte variance, pas un gain
large : 11 graines gagnent, 9 perdent.

🔴 **Et une graine s'effondre** : 12345 tombe à `company_value = 1` (contre 157 646 sous `=0`),
score 119 → 58, 48 → 34 véhicules — pas un plantage de script (`run_ok = true`), une quasi-faillite.
Le correctif retire une croissance **bon marché** (un avion seul sur une paire déjà équipée) et
pousse le capital vers des aéroports neufs à ~32 k£ de plus pièce ; sur une graine pauvre, ça
suffit à basculer dans la dette.

**Défaut posé à `air_hub_fix = 1`** — c'est une correction de défaut, pas un arbitrage de
conception, et les trois métriques de l'ordre d'objectifs montent. `0` rejoue exactement le
comportement cassé pour que l'écart reste chiffrable.

➡️ Suite naturelle, **pas encore faite** : maintenant que `routes` est enfin correct, la décote
`/(routes+1)` et le plafond `maxRoutes` sont vivants pour la première fois — ce sont eux que le
plafond dérivé de la demande (§3 undecies point 1) doit remplacer ou calibrer.

---

## 3 undecies bis. 🧪 PLAFOND AÉRIEN DE DEMANDE CÂBLÉ, à sonder avant banc (2026-09-03)

Deux instruments indépendants, tous deux à défaut 0, sont maintenant exposés :
`air_demand_cap` borne la croissance de `_resizeAirFleets`, tandis que `air_demand_plan` remplace
le dimensionnement fixe et le proxy de population dans les trois bras du plan (`newpair`,
`hubsite`, `hubhub`). Les quatre combinaisons 0/0, 1/0, 0/1 et 1/1 restent donc mesurables.

La production mensuelle réelle de chaque ville est multipliée par
`TOWN_CATCHMENT_SHARE_PCT = 22 %`, puis divisée par le nombre de lignes aériennes vivantes qui
desservent l'aéroport, comptées après résolution de sa **tuile** en `StationID` (diviseur 1 si
l'aéroport n'a encore aucune ligne). Les deux parts sont additionnées. La capacité mensuelle d'un
avion est `capacité × 30,4 / oneWayDays`, avec le même modèle de vol que l'économie aérienne ; la
vitesse vient du premier avion vivant de la ligne, ou de l'avion du catalogue pour un plan. Le
plafond est `ceil(demande mensuelle / capacité mensuelle)`, avec un plancher de 1. En croissance,
il est combiné par `min` avec le plafond physique 4/16 ; un refus de demande porte le code `Q`,
distinct du code physique `C`, et `DECISION_LOG` publie les deux ingrédients du calcul.

Cette première version est volontairement une borne haute : elle ignore les aéroports et lignes
futurs qui détourneront ensuite une part du flux. Elle ne consulte jamais le stock
`AIStation.GetCargoWaiting`, réservé au mécanisme `marginal_fleet`.

Avant tout banc, une sonde 1 graine × 3 ans doit montrer le nombre de refus `Q`, la distribution
du plafond calculé, et la marge entre flotte courante et plafond. Si `Q = 0`, le mécanisme ne mord
pas et aucun banc n'est justifié. Sinon seulement, lancer un banc apparié 20 graines × 10 ans sur
les quatre bras factoriels, lire `profit_year` avant `company_value`, puis vérifier le test des
signes en plus du test t.

### 🧪 SONDE FAITE le 2026-09-03 — `docs/diag_air_demand_cap.json` (`sweeps/diag_air_demand_cap.py`)

4 bras factoriels × 3 graines × 3 ans, `decision_log=1`. ⚠️ **Ce n'est pas un banc** : 3 graines ne
tranchent rien, et rien ici n'est un résultat significatif. La sonde sert à décider s'il y a
quelque chose à mesurer.

| bras | valeur (42 / 999 / 12345) | avions | lignes air | refus `Q` |
|---|---:|---:|---:|---:|
| base | 601 568 / 882 581 / **1** | 14 / 26 / 6 | 5 / 8 / 3 | 0 / 0 / 0 |
| `cap` | 416 188 / 945 495 / **1** | 8 / 22 / 6 | 4 / 10 / 3 | **24 / 75 / 43** |
| `plan` | **865 314 / 1 556 737 / 242 451** | 18 / 36 / 10 | 3 / 5 / 2 | 0 / 0 / 0 |
| `cap+plan` | 725 322 / 982 669 / 316 681 | 6 / 10 / 4 | 3 / 4 / 2 | 23 / 30 / 20 |

**1. `air_demand_cap` MORD — et c'est justement le problème.** 24, 75 et 43 refus `Q` contre
**0 refus `C`** : le plafond de demande se déclenche là où le plafond physique n'a jamais rien
retenu (§0 quinvicies, 0 refus sur 32). Marge médiane **0**, souvent négative — la ligne 0 de la
graine 42 tourne à 2 avions pour un plafond de 1, le plafond n'arrivant qu'après la croissance et
ne vendant jamais. Les ingrédients bruts : demande captée **70 à 280 pax/mois**, capacité d'un
avion **90 à 132 pax/mois**, donc un plafond de **1 à 3 appareils**. Et il se resserre seul : la
demande de la ligne 0 tombe de 193 à 76 quand `routes_a` passe de 1 à 2, le bassin étant partagé.
Effet sur la valeur : −31 % / +7 % / nul. **Ça rabote, ça ne paie pas.**

**2. `air_demand_plan` n'affame PAS le bras aérien — il le concentre.** C'était la crainte
explicite avant la sonde ; elle est démentie. **Moins de lignes** (3/5/2 contre 5/8/3) mais **plus
d'avions** (18/36/10 contre 14/26/6), et la valeur monte sur **3 graines sur 3** : +44 %, +76 %, et
**1 → 242 451** sur la graine 12345, celle qui s'effondrait déjà sous `air_hub_fix`. Mécanisme
cohérent : avec une assiette de demande vraie — donc bien plus basse — `OpexAirEconomics` cesse de
surestimer le revenu de chaque paire, moins de plans passent `profitAnnual > 0`, et le capital se
concentre sur les paires réellement bonnes que la croissance remplit ensuite. C'est la
largeur-contre-profondeur d'A2 prise par l'autre bout.

**3. Les deux ensemble s'annulent.** `cap+plan` est sous `plan` seul sur 2 graines sur 3, avec 3 à
4 fois moins d'avions : le plafond étrangle la croissance que la meilleure sélection venait
d'ouvrir. ➡️ Confirme après coup qu'il fallait **deux réglages séparés** : en un seul, ce résultat
était illisible.

**4. 🔴 Le suspect n°1 du plafond : les 22 % sont calibrés sur des gares RAIL.**
`TOWN_CATCHMENT_SHARE_PCT` a été mesuré le 2026-08-28 comme le résidu
« production atteignant la gare ÷ `AITown.GetLastMonthProduction` » sur **9 lignes pax rail**
(8-37 %, moyenne 22 %, `candidates.nut:485-492`) — l'avertissement était déjà écrit dans
`docs/mecanique_jeu.md` §. Un aéroport ne couvre pas le même rayon qu'une gare ferroviaire. Un
plafond à 1-3 avions sur une paire qui en nourrit visiblement 6 est donc plus probablement un
**coefficient faux** qu'une vérité économique. À recalibrer par le même résidu, sur des lignes
aériennes, avant de rejuger le plafond de croissance.

**Décision de l'utilisateur (2026-09-03) : pas de banc sur `air_demand_plan`.** Défauts laissés à
0 des deux côtés en attendant. Piste ouverte à la place : lire comment AAAHogEx estime, lui, la
demande qui justifie ses ~35 appareils (délégué à agy le même jour).

---

## 0 novemvicies. 🔑 CE QUE FAIT AAAHogEx : IL N'A PAS DE PLAFOND DE DEMANDE, IL A UN PLAFOND DE CADENCE (lecture de code, 2026-09-03)

Question posée après la sonde de §3 undecies bis : notre plafond dérivé de la demande tombe à
**1-3 appareils** quand AAAHogEx en fait voler ~35. Lecture de `ai/AAAHogEx-115/` déléguée à agy,
**toutes les citations ci-dessous relues et vérifiées ligne à ligne dans le source**.

### 1. 🔑 LA TROUVAILLE : `EstimateMaxVehicles` borne la flotte par la ROTATION, pas par le cargo (`route.nut:2374-2380`)

```squirrel
route.nut:2374  function EstimateMaxVehicles(self, distance, speed, vehicleLength = 0) {
route.nut:2378    local days = distance * 664 / speed / 24;
route.nut:2379    return min( days * 2 / self.GetStationDateSpan(self) + 1,
route.nut:2379                (distance + 4) * 16 / vehicleLength) + 2;
```

Jours d'aller-retour ÷ cadence d'absorption de l'aéroport. **Ni production, ni population, ni
note de gare n'entrent dans ce plafond** — c'est une question de débit physique : combien
d'appareils tiennent sur la ligne si la gare n'en absorbe qu'un tous les `stationDateSpan` jours.

➡️ **Notre `air_demand_cap` répond à une question qu'AAAHogEx ne pose jamais.** Ce n'est donc pas
seulement le coefficient de 22 % qui est mal calibré (§3 undecies bis point 4) : **la grandeur
elle-même n'est pas celle qui borne une flotte aérienne**. Un aéroport ne sature pas parce que la
ville manque de passagers ; il sature parce qu'il n'absorbe qu'un appareil par créneau.

### 2. Le partage entre lignes est au dénominateur de la CADENCE, pas du bassin (`air.nut:330-336`)

```squirrel
air.nut:331  local srcUsings  = ArrayUtils.Without(srcHgStation.GetUsingRoutes(),this).len()+1;
air.nut:332  local destUsings = ArrayUtils.Without(destHgStation.GetUsingRoutes(),this).len()+1;
air.nut:334  return max( Air.Get().GetAiportTraits(srcHgStation.airportType).stationDateSpan * srcUsings,
air.nut:335              Air.Get().GetAiportTraits(destHgStation.airportType).stationDateSpan * destUsings );
```

Deux routes sur un aéroport ⇒ chacune attend deux fois plus son créneau. **Nous divisons le cargo
disponible, eux divisent le droit d'atterrir.** Le partage existe donc des deux côtés, mais il ne
porte pas sur la même grandeur.

### 3. L'achat marginal est piloté par le STOCK, avec une bande morte (`route.nut:2896-2921`)

```squirrel
route.nut:2903    } else if(CargoUtils.IsPaxOrMail(cargo)) {
route.nut:2904      bottom = min(50, capacity);            // on laisse 50 unites au sol
route.nut:2906    buildNum = (cargoWaiting-bottom) / capacity;
route.nut:2918    buildNum = min(buildNum, 4);             // 4 par passage
route.nut:2921    buildNum = min(maxVehicles - vehicles.Count(), buildNum) - firstBuild;
```

Un avion par pleine capacité de cargo **effectivement au sol**, moins un tampon. C'est une boucle
de régulation à bande morte : si la flotte dépasse, la file se vide et `buildNum` passe à zéro
tout seul. Deux surcharges vérifiées forcent `buildNum = max(1, buildNum)` quand la **note de
gare** est mauvaise malgré du cargo en attente (`:2908` et `:2913`) — la note de gare sert de
signal d'urgence, pas de terme de classement.

🔴 **Et ça renverse une lecture que j'avais faite le 2026-09-03.** Ici le stock n'est pas une
prédiction, c'est une **observation**. L'argument flux-vs-stock qui a chassé le stock de notre
*classement* (philosophie de l'opcode) ne s'applique pas à la **croissance d'une ligne déjà
construite** : à ce moment-là, la file au sol est la mesure la plus directe de ce qui manque.

### 4. Aucun coefficient de captation : ils étendent physiquement la couverture (`place.nut:2948`)

```squirrel
place.nut:2948    production = production * 2 / 3;   // ce qui deborde de l'arret de bus
```

Pas d'équivalent de nos 22 %. Là où nous **décotons** la production d'une ville, ils **vont la
chercher** : `distant_join_stations` et bus d'apport, avec une perte assumée d'un tiers. La
production estimée est ensuite bornée par des plafonds durs par mode (`:2950-2952`).

Et le doublon passagers est **interdit par construction** (`air.nut:729-746`) : `CanShareByMultiRoute`
refuse dès qu'une route bidirectionnelle du même cargo existe sur l'aéroport, refuse si
`usingRoutes >= terminals - 1`, et refuse si les arrivées annuelles cumulées dépassent la moitié
de la capacité de l'aéroport (`:747-750`, commentaire japonais explicite : n'accepter une route
neuve que si l'aéroport est libre à plus de moitié).

### 5. La sanction est a posteriori, pas a priori (`route.nut:2484-2498`)

```squirrel
route.nut:2486  local notProfitable = age > checkAge && AIVehicle.GetProfitLastYear(vehicle)
route.nut:2486                        + AIVehicle.GetProfitThisYear(vehicle) < 0;
route.nut:2488  AppendRemoveOrder(vehicle);
```

`checkAge = 800` jours. Ils achètent tant qu'il y a du cargo au sol et de la place physique, puis
retirent ce qui perd. **Aucun arbitrage de profit marginal avant l'achat.**

### 6. Ce qui est réellement actionnable chez nous

**Le mécanisme de stock, nous l'avons déjà** : `MARGINAL_FLEET` exige une pleine capacité en
attente (`main.nut:2315-2325`), et il a été **mesuré nul, défaut 0** (§7 bis). Mais il est
beaucoup plus timide que le leur, sur deux axes indépendants :

| | AAAHogEx | OpexAI sous `marginal_fleet` |
|---|---|---|
| quantité par passage | `(attente − 50) / capacité`, jusqu'à **4** | **1** |
| cadence | à chaque passage d'entretien de route (fréquence exacte **non vérifiée**) | **une fois par an et par ligne** (`lastAirFleetYear`, refus `Y`) |
| bande morte | tampon de 50 unités | une **pleine** capacité d'avion |

➡️ La différence n'est pas le mécanisme, c'est le **gain et la cadence de la boucle**. C'est
mesurable sans rien réécrire : desserrer le tampon et relever la cadence de `_resizeAirFleets`
sont deux réglages, pas une refonte. **À faire avant de retoucher le plafond.**

➡️ Et si le plafond doit revenir un jour, la forme à essayer n'est **pas** le bassin de la ville
mais la **cadence de l'aéroport** : `jours d'aller-retour / créneau d'absorption`, divisée par le
nombre de lignes qui se partagent la piste. Notre `OpexStationRatingForHeadway` calcule déjà un
headway ; l'ingrédient manquant est le `stationDateSpan` de chaque type d'aéroport.

### ⚠️ Non vérifié, à ne pas surinterpréter

- La **fréquence** réelle de leur boucle d'achat (« à chaque cycle » vient d'agy, non recoupé).
- Les **valeurs numériques** de `stationDateSpan` par type d'aéroport, jamais lues.
- L'estimation « ~21 à ~33 appareils » est un calcul d'agy sur la formule, **pas** une mesure en
  partie ; le chiffre observé de ~35 appareils, lui, vient de nos propres bancs.

---

## 3 duodecies. 💡 UNE « PERSONNALITÉ » D'OPEXAI À LA PLACE DES RÉGLAGES (idée de l'utilisateur, 2026-09-03)

**L'idée, telle qu'énoncée** : quand tout sera stabilisé, remplacer la plupart des paramètres
d'`info.nut` par une **personnalité** — agressive, pacifique, perfectionniste, etc. — au lieu d'une
liste de commutateurs.

⚠️ **Explicitement datée « quand tout sera stabilisé »** : ce n'est pas un item à prendre avant que
les instruments en cours aient rendu leur verdict.

### Le crochet existe déjà, et il est inutilisé

`AddSetting` porte `easy_value` / `medium_value` / `hard_value` / `custom_value`. Sur les
**64 réglages** d'`info.nut`, **les quatre valeurs sont identiques partout** : 35 booléens à 0,
23 à 1, 6 numériques. Le mécanisme de profil prévu par l'API NoAI est donc entièrement disponible,
et n'a jamais servi. Une personnalité peut se câbler comme un réglage entier `personality` lu dans
`Start()`, qui écrase les constantes globales avant la première itération — quelques lignes, aucun
coût d'opcode en régime.

### 🔴 La contrainte qui décide de la forme : une personnalité est un LOT

Ce projet s'est déjà fait piéger **deux fois** par des lots :

1. **Les treize corrections du 2026-09-02** (§0 nonies bis), benchées ensemble : le lot paraissait
   plat parce qu'il contenait des effets **de signes opposés** — `economy_fix` positif et
   `portfolio_v2` destructeur s'annulaient. Il a fallu les isoler pour voir quoi que ce soit.
2. **Un seuil de trésorerie** dont l'implémentation changeait deux choses à la fois, et qui a
   failli être rejeté à tort.

Et le 2026-09-03, `air_demand_cap` + `air_demand_plan` ont dû être livrés en **deux réglages
séparés** précisément pour cette raison : ensemble, ils s'annulent (§3 undecies bis point 3), et en
un seul commutateur le résultat aurait été illisible.

➡️ **Conséquence non négociable : la personnalité est une COUCHE DE PRÉRÉGLAGES au-dessus des
instruments, jamais leur remplacement.** Chaque constante doit rester adressable seule, sinon le
banc perd son seul outil de discrimination. Ce qui disparaît, c'est l'obligation de choisir 64
valeurs à la main — pas la possibilité de le faire.

### Ce qui est réellement matière à personnalité, et ce qui ne l'est pas

La majorité des 64 réglages actuels ne sont **pas** des choix de tempérament : ce sont des
**verdicts de mesure**. `air_hub_fix` à 1 corrige un défaut de type ; `fleet_before_new` à 0 est
rejeté à −20,4 %. Une IA « agressive » n'a aucune raison de rejouer un bug ou une régression
mesurée. Ceux-là doivent **sortir du fichier** (voir E8) plutôt que devenir des traits de caractère.

Sont matière à personnalité les paramètres dont la bonne valeur dépend du goût, de la carte ou de
l'adversaire — essentiellement des **nombres**, pas des booléens : réserve de trésorerie, plancher
de ROI, plafonds de distance, marges de sécurité, `TOP_K` / `MIN_RATIO`, headway visé,
`MIN_SEPARATION`. ➡️ **E3 (audit des 46 constantes en dur) est donc le prérequis** : on ne compose
pas des personnalités à partir d'un inventaire qu'on n'a pas fait.

### 🔴 La tension à ne pas balayer : une personnalité est FIXE, l'adversaire est ADAPTATIF

§0 tervicies l'a établi en lisant le source : AAAHogEx **change de dénominateur d'objectif** selon
la ressource qui le contraint à l'instant — argent, temps de chantier, ou places de véhicules. §3
nonies propose la même chose sous forme de doctrine en six phases. Une personnalité figée risque
donc de **geler un choix que la mesure dit devoir varier** au cours de la partie.

La forme qui survit à cette objection n'est pas « un jeu de constantes » mais **un a priori sur la
doctrine de phase** : la personnalité dit *avec quel biais* on arbitre quand deux phases se
disputent la ressource, pas *quelle valeur* prend chaque constante pour toute la partie.

### Ce que ça apporterait vraiment, au-delà du confort

1. **Bancher des stratégies cohérentes entre elles**, et plus seulement des commutateurs isolés :
   un portefeuille de personnalités opposées sur les mêmes graines dirait quelque chose qu'aucun
   banc à un réglage ne peut dire.
2. **Cohérent avec « armes égales »** ([[philosophie_armes_egales]]) : une IA qui joue
   différemment selon la carte et l'adversaire, plutôt qu'un unique réglage moyen.
3. Un `info.nut` lisible par un humain qui n'a pas suivi les 30 bancs.

### Le plus petit pas utile, le jour venu

Ne pas commencer par écrire trois personnalités. Commencer par **une** — la doctrine par défaut
actuelle, nommée et rendue explicite — et vérifier qu'elle rejoue le comportement courant **au bit
près** sur 20 graines. Tant que ce contrôle de non-régression n'est pas vert, aucune seconde
personnalité n'a de sens.

---

## 0 trigesies. ❌ `air_demand_plan` : REJETÉ au banc 20 graines × 10 ans — et l'effet DÉPEND DE LA RICHESSE (2026-09-03)

Banc apparié `docs/bench_air_demand_plan_10y.json`, 20 graines × 10 ans, `air_demand_cap` à 0 des
deux côtés, 40 parties, **0 échec de script**.

| métrique | écart de `air_demand_plan=1` | t | graines gagnées | test des signes |
|---|---:|---:|---:|---:|
| `profit` | **−60,7 %** | **−4,36** | 4/20 | **0,012** |
| `profit_year` | **−51,5 %** | **−3,96** | 5/20 | **0,041** |
| `company_value` | −24,9 % | −1,70 | 8/20 | 0,50 |
| `performance_history` | −4,9 % | −0,96 | 10/20 | 1,00 |
| `median_station_rating` | +3,0 % | +1,23 | **19/20** | **0,0002** |

**Verdict : rejeté, sans ambiguïté.** L'ordre des objectifs met le profit en tête, et c'est
précisément là que le réglage s'effondre — avec le test des signes significatif, pas seulement le
$t$. Défaut confirmé à **0**.

Le réglage **fait exactement ce qu'il promettait** : il concentre le réseau, et la note de gare
monte sur **19 graines sur 20**. Mais il échange du profit contre de la note — le troisième
objectif contre le premier. C'est un mauvais troc, mesuré.

### 🔴 Ce que ça invalide dans ma propre lecture de la sonde

La sonde de §3 undecies bis annonçait +44 %, +76 % et un sauvetage de graine. Deux défauts, dont
le second est le mien et compte davantage :

1. **3 graines ne tranchent rien** — c'était écrit dans la sonde elle-même, et c'est le rappel de
   [[banc_monograine_insuffisant]]. Le sauvetage de la graine 12345 (« 1 → 242 451 ») ne survit
   pas à l'horizon : à 10 ans, **les deux bras** y sont à `company_value = 1`.
2. 🔴 **Ma sonde relevait `company_value`, que l'ordre des objectifs classe DERNIER.** Elle ne
   relevait pas le profit du tout. Or sur ses propres 3 graines, à 10 ans, `air_demand_plan` gagne
   encore en valeur (42 : +15 %, 999 : +64 %) mais **perd en profit** (−31,5 % et −12,3 %). Le
   signal contraire était déjà là, invisible parce que je ne l'avais pas instrumenté.
   ➡️ **Corrigé** : `sweeps/diag_air_demand_cap.py` relève désormais `profit` et `profit_year`, et
   son tableau les affiche **avant** la valeur. Toute sonde future doit suivre l'ordre des
   objectifs, pas l'inverse.

### 🔑 La trouvaille qui vaut plus que le verdict : le signe de l'effet suit la RICHESSE

En triant les 20 graines par la valeur de compagnie du bras de base :

| régime de la partie de base | graines | `air_demand_plan` gagne |
|---|---:|---:|
| pauvre (`company_value` < 3,4 M£) | 8 | **7** |
| riche (≥ 3,4 M£) | 11 | **0** |

Corrélation de rang, **sans seuil choisi à la main** : Spearman entre la valeur de base et l'écart
du réglage = **−0,725** ($t = -4{,}33$, $n = 19$ ; la graine 12345, à 1 £ dans les deux bras, est
écartée). Amplitudes extrêmes : **+104,5 %** sur la graine 123456, **−80,2 %** sur la 100.

⚠️ **Le seuil de 3,4 M£ est ajusté APRÈS coup sur ces 20 graines** : c'est une hypothèse produite
par les données, pas un résultat validé. La corrélation de rang, elle, ne dépend d'aucun seuil.

**Et ça rejoint exactement §0 tervicies.** AAAHogEx ne quitte le régime `roiBase` que s'il est
**riche** (`_IsRich`, `main.nut:4324`). Ici, une estimation de demande honnête — donc
conservatrice — aide quand la compagnie est pauvre et coûte cher quand elle est riche : pauvre, on
gagne à ne pas gaspiller sur des paires surestimées ; riche, le facteur qui lie n'est plus la
justesse de l'estimation mais le **volume**, et brider la sélection ampute la croissance.

➡️ Ce n'est donc **pas** « `air_demand_plan` est mauvais ». C'est **« un réglage constant sur toute
la partie est le mauvais objet »** — troisième mesure indépendante qui pointe vers A1 (dénominateur
dépendant de la ressource rare) et B4 (doctrine de phase). Le réglage reste comme instrument à 0 ;
s'il revient, c'est **conditionné à la richesse**, pas en dur.

---

## 3 terdecies. 🔑 A1 SANS CONSTANTES : loi de Liebig + théorie des contraintes (proposition de l'utilisateur, 2026-09-03)

**Consigne explicite : éviter à tout prix les constantes en dur.** Pas d'automate à états rigide
(`EarlyGame` / `MidGame`), mais un **indice de tension** calculé, et une contrainte dominante qui
est simplement celle dont la marge opérationnelle est la plus faible face à l'action projetée.

Forme proposée, pour chaque ressource `r` et une action projetée :

```
tension(r) = cout_r(action) / (disponible_r - marge_r  +  max(0, flux_r) * tau)
contrainte_dominante = argmax_r tension(r)
```

### Pourquoi c'est la bonne forme

1. **Ça supprime la comparaison à un seuil.** On ne teste plus `cash < 50 000` : on compare des
   **ressources entre elles**. La tension est un rapport sans dimension, donc comparable entre des
   unités hétérogènes — c'est cette propriété qui rend l'`argmax` licite.
2. **C'est ce que la mesure réclame.** Tous les seuils mesurés cette semaine sont neutres ou
   négatifs, et §0 undecies septies a montré pourquoi : **abaisser un seuil ne libère que la bande
   entre l'ancienne et la nouvelle valeur**. Un seuil est un objet local ; la contrainte est
   globale.
3. **C'est la généralisation continue de l'aiguillage d'AAAHogEx.** Son `_IsRich` est une bascule
   à deux états ; la tension est la même idée sans marche d'escalier. Et §0 trigesies dit que le
   régime varie **continûment** : le signe de l'effet d'`air_demand_plan` suit la richesse avec un
   Spearman de −0,725, pas un saut.

### 🔴 1. La formule proposée réintroduit deux constantes en douce

`marge_r` (safety margin) et `tau` (horizon) **sont exactement les nombres magiques qu'on veut
bannir**, renommés. Deux des trois termes du dénominateur sont des paramètres libres.

Et dans ce projet, la marge n'est pas neutre : §0 undecies septies a mesuré que
notre réserve de trésorerie **n'est pas un plancher de sécurité, c'est le BUDGET DU SAC À DOS**.
Poser `marge_r` comme une constante de confort revient à re-régler le budget de sélection sans le
dire.

➡️ **Les deux doivent être endogènes** :
- `tau` = **l'horizon d'amortissement de l'action elle-même** (sa propre durée de retour), pas un
  horizon de confort choisi à la main. Chaque action porte alors son propre horizon, ce qui est
  précisément ce qu'on veut : une ligne de bus courte et un aéroport ne s'évaluent pas sur la même
  fenêtre.
- `marge_r` = **les engagements déjà pris et non encore payés** pour cette ressource (coûts de
  fonctionnement jusqu'à la prochaine rentrée, véhicules commandés, chantiers engagés). C'est une
  grandeur **mesurable**, pas un choix.

### 🔴 2. `max(0, flux)` supprime le cas le plus urgent

Une ressource qui **se vide** (flux négatif) est la plus contraignante de toutes ; avec
`max(0, flux)`, une compagnie qui perd de l'argent est indiscernable d'une compagnie à revenu
plat. Le **Time-to-Exhaustion** est nommé dans la proposition mais pas implémenté par cette ligne.

➡️ Garder `disponible + flux * tau` **signé**, et laisser la tension diverger quand le
dénominateur passe sous zéro. C'est le seul cas où l'infini a un sens.

### 🔴 3. L'`argmax` oscille, et ce projet y est mesurablement sensible

Deux tensions à 0,98 et 0,97 font basculer la doctrine sur du bruit d'estimation, d'un mois à
l'autre. Ajouter une hystérésis rétablirait une constante.

➡️ **La forme que je propose à la place : ne pas basculer, pondérer.** Au lieu de choisir un
dénominateur, en composer un :

```
denominateur(action) = somme_r [ tension(r) * cout_r(action) ]
classement = profit_attendu / denominateur(action)
```

Propriétés, et c'est pour ça que je la préfère :
- **Continue** : aucun basculement, donc aucune oscillation, donc aucune hystérésis à régler.
- **Elle dégénère correctement** : quand une ressource domine largement, la somme se réduit à
  cette ressource et on retrouve exactement l'aiguillage d'AAAHogEx.
- **Elle contient l'existant comme cas particulier** : aujourd'hui nous faisons
  `tension(capital) = 1` et toutes les autres à 0. Le passage est donc mesurable en continu, et
  non comme un remplacement en bloc — ce qui compte, vu que `portfolio_v2`, la dernière refonte
  du classement livrée d'un coup, **détruisait la valeur** (§0 nonies quater).

### Les ressources candidates, et ce que le dossier dit DÉJÀ de chacune

| ressource | état au dossier | verdict pour ce modèle |
|---|---|---|
| **Argent** | la seule que nous mettons au dénominateur aujourd'hui | ✅ à garder, mais elle cesse d'être seule |
| **Emprise foncière** | 🔴 **mur mesuré** : `MIN_SEPARATION` tue **18 des 19 derniers candidats** de la graine 999, avec 37-39 villes encore non desservies (`docs/opexai_plafonnement.md`) | 🔴 **la plus prometteuse après l'argent** — c'est déjà un mur constaté, pas une hypothèse |
| **Budget d'opcodes** | ⚠️ **mesuré NON goulot** : les trois voies sont fermées — relever ❌, redistribuer ❌ (−23 %), abaisser 🟡 nul (A3/A4/A5) | ✅ à inclure comme ressource, ❌ **ne pas en attendre la domination** ; la traiter comme une tension parmi d'autres |
| **Slots de véhicules** | ❓ **jamais lu** : aucun appel au plafond de véhicules dans tout `ai/OpexAI/` | 🔶 mesure préalable **triviale** — et c'est le régime où AAAHogEx bascule sur `profit par véhicule` |
| **Note municipale** | ⚠️ c'est un **enum 0-8**, pas un score continu ; et notre seul levier (`tree_planting`) est **rejeté deux fois** (D1) | 🔶 ressource réelle, levier mesuré nul : à modéliser en lecture, pas en action |
| **Saturation de tronçon** | ⚠️ quasi **sans objet dans notre topologie** : point-à-point, voie unique, 1-2 convois (`docs/mecanique_jeu.md` §12) | ⏳ n'aura de sens qu'après un changement de topologie |
| **Fenêtre de subvention** | ❓ **ZÉRO occurrence** dans tout le dépôt — jamais lue, jamais exploitée | 🔶 **ressource réellement neuve**, et la seule du lot qui soit une *opportunité* datée plutôt qu'un stock |

### 🔑 Le premier pas, et il ne change aucune décision

Ne pas câbler l'arbitrage. **Calculer et journaliser le VECTEUR de tension à chaque cycle, en
laissant le classement actuel intact.** La question à laquelle il faut répondre avant d'écrire une
ligne d'arbitrage est : **la contrainte dominante varie-t-elle réellement au cours d'une partie ?**

Si c'est « argent » 100 % du temps, le modèle se réduit à ce que nous faisons déjà et il n'y a
rien à coder. Ce contrôle est exactement celui qui manquait à `portfolio_max_batch` (rejeté, **11
graines sur 20 en nuls exacts** : le mécanisme ne se déclenchait jamais) et au plafond `maxRoutes`
(**0 refus sur 32**). **Vérifier que le mécanisme mord avant de l'armer** est devenu la règle de
ce projet, et elle s'applique ici plus qu'ailleurs.

### A6 — instrumentation du vecteur de tension

La sonde `tension_probe` (défaut `0`) ne participe à aucune décision. Quand elle vaut `1`, elle
calcule `OpexTensionVector` dans l'unique parcours qui publie déjà `PORTFOLIO_RANK`, puis impute
son coût au `OpexBudget` sous la catégorie `tension`. Chaque projet journalisé produit une seule
ligne `TENSION` avec `cost`, `available`, `commitments`, `flow`, `tau` et `tension` pour les quatre
ressources, suivis de la dominante et de l'écart relatif entre les deux premières tensions. La
valeur entière `-1` représente une tension infinie lorsque le dénominateur est nul ou négatif.

| ressource | coût de l'action | disponible | engagements | flux |
|---|---|---|---|---|
| argent | `project.capital` | `GetBankBalance` + `GetMaxLoanAmount` − `GetLoanAmount` | dépenses récurrentes du dernier trimestre clos, mensualisées | revenu moins dépenses du même trimestre, mensualisé et signé |
| slots de véhicules | flotte projetée (`trains`, `planes` ou le navire du plan) | plafond `vehicle.max_*` lu par `AIGameSettings` moins la flotte primaire actuelle du mode | `0` | `0` |
| opcodes | `project.expectedOpcodes`, qui réutilise notamment `PROJECT_RAIL_OPS_PER_ITERATION` pour le rail | `0`, car le budget est un débit | `0` | `OPS_PER_TICK` multiplié par les ticks mensuels mesurés au runtime |
| foncier | `1` site | nombre de candidats multimodaux retenus dans le vivier après les rejets de séparation | `0` | `0` |

`tau` est toujours l'horizon propre à l'action, en mois :
`12 × project.capital / project.profitAnnual`. Le produit `flow × tau` conserve donc le signe du
flux. Pour les opcodes,
les ticks par jour sont observés entre deux dates de jeu au lieu d'être fixés dans le code ; avant
la première observation, le flux vaut `0` et la sentinelle rend explicitement ce manque de mesure.
`OpexCashReserve()` n'intervient jamais dans ce calcul : la sonde mesure la ressource, pas le budget
du sac à dos.

La mesure humaine attendue reste trois graines sur dix ans avec `tension_probe=1`. Il faut tracer,
mois par mois, la ressource dominante et l'écart entre la première et la deuxième tension. La
sonde doit montrer à la fois si la dominante quitte réellement l'argent et si les deux premières
restent assez séparées pour qu'un futur `argmax` ne soit pas une oscillation de bruit. Si l'argent
domine 100 % du temps, aucune refonte du classement ne sera armée.

### Ce que ça absorbe

Cette proposition **remplace** B2 (file de tâches dynamique à priorités par phase) et B4 (doctrine
de partie en six phases) : toutes deux étaient des automates à états, c'est-à-dire la forme que
l'utilisateur écarte explicitement. Elle donne aussi sa forme correcte à §3 duodecies : une
**personnalité** n'est plus un jeu de constantes, mais un **a priori sur la pondération des
tensions** — ce qui est le seul objet qui survit à l'objection « une personnalité est fixe, le jeu
ne l'est pas ».

---

## 9 bis. 💡 Idées conditionnées à un changement de topologie (2026-09-03)

Issues du second lot de conseils, vérifiées contre la source 15.3. Elles sont **justes**, mais
elles supposent un réseau que nous n'avons pas encore : aujourd'hui nos lignes rail sont
point-à-point, à voie unique, avec 1 à 2 convois.

- 🔶 **Gares traversantes (Ro-Ro) plutôt que terminus en cul-de-sac.** Supprime le croisement à
  l'entrée de gare, donc double le débit d'un axe sans toucher aux signaux. ⏳ N'a de sens qu'une
  fois qu'un axe porte assez de convois pour que le croisement morde — ce qui n'arrive pas à
  1-2 trains. À rouvrir avec la seconde voie dédiée (`docs/mecanique_jeu.md` §12).
- 🔶 **Signalisation PBS exclusive** (`AIRail.SIGNALTYPE_PBS` — ⚠️ dans `AIRail`, il n'existe pas
  de classe `AISignal`). Deux convois peuvent franchir une même intersection si leurs
  réservations ne se croisent pas. ⚠️ §12 de `mecanique_jeu.md` dit déjà l'essentiel : PBS sur les
  approches **simples** d'une jointure, **jamais** sur `TracksOverlap`, et `trains > 1` exige une
  **seconde voie dédiée** — pas des PBS sur voie unique. Le « divise par trois les blocages » du
  conseil est **invérifiable**, à ne pas citer comme un fait.
- 🔶 **Rapport poids/puissance selon la déclivité du tracé.** Notre dimensionnement de traction
  (quai, wagons, loco) est calculé, mais il **ignore la pente** : un convoi correctement dimensionné
  en plaine peut tomber à vitesse ridicule en côte et saturer son canton. Le tracé est connu après
  le pathfinder, donc la déclivité maximale est calculable (`AITile.GetMaxHeight` /
  `GetCornerHeight` le long du chemin). ⚠️ À pondérer : le banc de traction a donné de la
  **robustesse**, pas de la performance, et le rail coûte déjà ×1,70 son prix modèle.

---

## 3 terdecies bis. ✅ A6 CÂBLÉ et validé en jeu — la sonde de tension tourne (2026-09-03)

`ai/OpexAI/tension.nut` + réglage `tension_probe` (défaut 0, aucun calcul exécuté sous 0, logger
historique conservé mot pour mot). Implémentation déléguée à Codex, **trois défauts corrigés à la
relecture avant tout run** :

1. 🔴 **Les engagements valaient `−dépenses du trimestre / 3`, donc chantiers compris.** La
   tension argent aurait réagi à la construction **passée** au lieu des obligations à venir — et
   les dépenses étaient comptées **deux fois**, puisqu'elles sont déjà dans le flux net.
   Remplacés par l'entretien réellement dû : `Σ GetRunningCost / 12` (la valeur est annuelle,
   vérifié dans `script_engine.hpp` : *« per economy-year »*) plus
   `AIInfrastructure.GetMonthlyInfrastructureCosts` sur les six catégories — la doc précise
   qu'`INFRASTRUCTURE_RAIL` et `_ROAD` rendent le total **tous types confondus**, donc six appels
   suffisent.
2. 🔴 **Le comptage de flotte parcourait toute la flotte pour chaque projet** : la sonde
   perturbait précisément la ressource qu'elle mesure. Tout ce qui ne dépend pas du projet est
   désormais calculé **une fois par cycle** (`OpexTensionContext`), en un seul parcours qui rend à
   la fois les effectifs par type et le coût de fonctionnement.
3. 🔴 **Le foncier sommait les candidats des quatre modes**, comptant deux fois une paire proposée
   en rail et en route, et ne disant rien de l'espace disponible pour l'action évaluée. Désormais :
   candidats survivants du **même mode**, plus `separation_rejected` (`stats.pairsOriginServed`)
   journalisé comme contexte.

Plus trois points de relecture : garde sur `tau` (division par `profitAnnual`), suppression des
paramètres et globales morts, et **un seul bloc de budget par cycle** au lieu d'un par projet —
`probe_ops` mesure donc le coût réel de la sonde, pas une fraction de lui-même.

### Validation en jeu — 1 graine × 2 ans, `tension_probe=1`

**0 erreur de script**, 24 lignes `TENSION`, coût **3 474 opcodes** pour 5 projets au premier
cycle puis ~1 290 pour un projet seul : négligeable devant les 10 000 opcodes par tick.

🟢 **Premier signal, à confirmer** : sur ces 24 évaluations, la contrainte dominante se répartit en
**argent 7, foncier 11, opcodes 6**. Ce n'est donc **pas « l'argent 100 % du temps »**, et le
critère d'arrêt d'A6 — « si c'est toujours l'argent, il n'y a rien à coder » — **n'est pas
déclenché**.

⚠️ **Une graine et deux ans ne tranchent rien.** Et le proxy de foncier (1 site divisé par le
nombre de candidats du mode) est le moins solide des quatre : quand le vivier d'un mode est petit,
sa tension monte mécaniquement. À lire comme un instrument, pas comme un verdict. **La sonde
réelle reste 3 graines × 10 ans**, avec le tracé de la dominante mois par mois et de l'écart
entre la première et la deuxième tension — c'est cet écart qui dira si un `argmax` oscillerait,
donc si le dénominateur pondéré est nécessaire.

---

## 0 untrigesies. 🔑 SONDE A6 : LA CONTRAINTE DOMINANTE VARIE — et elle a une structure temporelle (2026-09-03)

`sweeps/diag_tension.py`, 3 graines × 10 ans, `tension_probe=1`, `docs/diag_tension.json`.
215 évaluations, 121 cycles, **0 erreur de script**. Le classement n'est pas touché : la sonde
journalise, elle ne décide pas.

### 1. ✅ Le critère d'arrêt d'A6 n'est PAS déclenché

| dominante | part |
|---|---:|
| **foncier** | 98 / 215 (**46 %**) |
| **argent** | 69 / 215 (**32 %**) |
| **opcodes** | 48 / 215 (**22 %**) |

L'argent domine **un tiers du temps**. La règle « si c'est l'argent 100 % du temps, il n'y a rien
à coder » ne s'applique donc pas : le classement au ROI capital optimise une contrainte qui, deux
fois sur trois, **n'est pas celle qui lie**. C'est la confirmation directe et interne de ce que
sept mécanismes de capital non adoptés laissaient supposer.

### 2. 🔑 Et surtout : elle varie AU COURS de la partie

Graine 42, dominante par année :

| 1970 | 1971 | 1972 | 1973 | 1974 | 1975 | 1976 | 1977 | 1978 | 1979 |
|---|---|---|---|---|---|---|---|---|---|
| argent 50 % | foncier 67 % | foncier 50 % | foncier 67 % | foncier 56 % | foncier 50 % | foncier 57 % | foncier 70 % | foncier 75 % | **foncier 82 %** |

L'argent domine **la première année** — c'est le mur de trésorerie 1970-1980 déjà mesuré — puis
s'efface, et le foncier monte régulièrement jusqu'à 82 %. Les opcodes occupent le milieu de
partie (25 à 50 % selon l'année). Graine 999 : argent **92 %** en 1970, puis alternance
argent/foncier, opcodes à 44 % en 1976.

➡️ **C'est la doctrine de phase, mesurée au lieu d'être décrétée.** B2 et B4 voulaient la poser à
la main ; la tension la fait émerger. Aucun seuil, aucune date, aucune constante.

### 3. 🔴 Ce résultat contredit ma propre recommandation sur la forme

**L'écart entre la première et la deuxième tension est LARGE** : médiane **0,577**, et seulement
**7 %** des évaluations sous 0,10.

J'avais proposé un dénominateur **pondéré** (`Σ tension × coût`) plutôt qu'un `argmax`, au motif
qu'un `argmax` basculerait sur du bruit d'estimation. **La mesure dit que non** : dans 93 % des
cas la dominante est nette. Une **bascule discrète**, à la `_IsRich` d'AAAHogEx, serait donc
stable — et elle est beaucoup moins risquée à livrer qu'une refonte du dénominateur, ce qui compte
vu que `portfolio_v2`, dernière refonte du classement livrée d'un coup, détruisait la valeur.

Le dénominateur pondéré reste plus élégant ; il n'est plus **justifié par les données**.

### 4. ⚠️ La réserve qui pèse le plus : le foncier est le proxy le plus faible

`foncier` domine 46 % du temps, or sa mesure est `1 / nombre de candidats du mode`. Elle dit
« le vivier de ce mode est étroit », **pas** « l'espace constructible est épuisé ». Quand un mode
n'a que deux candidats, sa tension vaut 0,5 et écrase mécaniquement les autres.

➡️ **Le résultat de tête repose donc sur la mesure la moins solide des quatre.** Avant tout
arbitrage, c'est elle qu'il faut rendre réelle : le bon dénominateur est l'espace admissible
restant — `separation_rejected` (`stats.pairsOriginServed`) est déjà journalisé à côté et donne
la matière. `docs/opexai_plafonnement.md` a déjà mesuré ce mur : 18 des 19 derniers candidats de
la graine 999 tués par `MIN_SEPARATION`, avec 37-39 villes non desservies.

### 5. Coût de la sonde

Médiane **3 200 opcodes par cycle**, maximum 8 546 — sous un tick, mais **pas négligeable** si un
jour l'arbitrage tourne à chaque cycle. À reconsidérer si le vecteur passe en production.

### ➡️ Ordre qui en découle

1. **Rendre la tension foncière réelle** (espace admissible, pas taille du vivier). Sans ça,
   46 % du résultat n'est pas interprétable.
2. **Puis** une bascule discrète du dénominateur, pas le dénominateur pondéré : les données ne
   justifient pas le second, et le premier est bien moins risqué.
3. La graine 12345 s'arrête de construire en 1972 (19 évaluations contre ~100) — cohérent avec son
   effondrement connu. Ne pas la lire comme les deux autres.

---

## 0 duotrigesies. 🔑 LA TENSION FONCIÈRE NE MORD PAS — et ce qui mord, ce sont les OPCODES (2026-09-03)

Suite directe de §0 untrigesies, qui laissait le foncier dominant à 46 % sur le proxy le plus
faible. Trois sondes successives, `sweeps/diag_tension.py`, 10 ans.

### 1. Le proxy foncier faussait bien le résultat de tête

Le dénominateur est passé de « taille du vivier du mode » au **stock d'origines libres** —
`townsUnserved + industriesUnserved`, déjà calculé chaque cycle par le générateur et **jamais lu**
(`candidates.nut:671`, `:741`). C'est la grandeur du mur de `docs/opexai_plafonnement.md` : chaque
gare bâtie interdit un disque autour d'elle. Le coût passe de 1 à **2** : une liaison neuve
consomme une origine à chaque bout.

| dominante | proxy « taille du vivier » | stock d'origines libres |
|---|---:|---:|
| foncier | **46 %** | **20 %** |
| argent | 32 % | **53 %** |
| opcodes | 22 % | 27 % |

### 2. 🔴 Et le foncier ne se contracte PAS en dix ans

Trajectoire médiane, mesurée :

| | 1970 | 1979 | pression de séparation |
|---|---:|---:|---:|
| graine 42 | 87 origines libres | **83** | 1 à 4 % |
| graine 999 | 99 origines libres | **93** | 0 à 1 % |

**Six origines consommées en dix ans sur une centaine.** Le mur de
`docs/opexai_plafonnement.md` — 18 des 19 derniers candidats tués — est daté « à partir de 1982 »
et mesuré sur une partie de **20 ans en mode route** : il est **hors de notre fenêtre**. Le
foncier est une contrainte réelle, mais pas à cet horizon.

### 3. 🔑 LA TROUVAILLE : l'`argmax` désigne une dominante qui ne contraint rien

En relevant non plus l'identité de la dominante mais son **amplitude** :

| graine | amplitude médiane | ≥ 0,50 (ça mord) | < 0,10 (rien ne contraint) |
|---|---:|---:|---:|
| 42 | **0,063** | 12 % | 58 % |
| 999 | **0,048** | 11 % | 76 % |
| 12345 (pauvre) | **0,268** | **28 %** | 22 % |

Une tension de 0,05 signifie que l'action consomme **5 %** de la ressource disponible. Dans
**76 %** des évaluations de la graine 999, la « contrainte dominante » est la moins abondante de
quatre ressources abondantes. L'identité est un artefact ; seule l'amplitude dit s'il y a
contrainte. Et la graine **12345, la pauvre**, est la seule où ça mord souvent (28 %) — cohérent.

⚠️ **Ce que l'écart 1re/2e ne pouvait pas voir.** Il vaut 0,6 en médiane, ce qui semblait dire
« la dominante est nette ». Mais un écart de 0,6 entre **0,05 et 0,02** est relativement large et
absolument nul. **Deux indicateurs de forme opposée ; c'est l'amplitude qui a raison.**

### 4. 🔴 CONSÉQUENCE : la bascule discrète est la MAUVAISE forme — je m'étais trompé

§0 untrigesies concluait qu'une bascule discrète à la `_IsRich` suffirait, l'écart étant large.
**L'amplitude renverse cette conclusion** : une bascule changerait de dénominateur sur une
différence entre deux tensions négligeables, trois fois sur quatre. Elle serait *stable* et
*vide de sens*.

Le **dénominateur pondéré** `Σ_r tension(r,a) × coût_r(a)` n'a pas ce défaut : quand toutes les
tensions sont petites, il tend continûment vers un coût pondéré — donc vers un ROI généralisé,
c'est-à-dire vers le comportement actuel — et il ne se met à mordre que lorsqu'une tension
devient réellement grande. ➡️ **La forme choisie par l'utilisateur (« la solution élégante »)
est désormais soutenue par la mesure, et non plus seulement par l'élégance.** C'est ma
recommandation précédente qui était fausse, faute d'avoir relevé l'amplitude.

### 5. 🔑 Et quand ça mord, c'est l'OPCODE

Parmi les évaluations où la dominante dépasse 0,50 :

| graine | opcodes | argent | foncier |
|---|---:|---:|---:|
| 42 | **80 %** | 20 % | 0 |
| 999 | **70 %** | 30 % | 0 |
| 12345 | **60 %** | 40 % | 0 |

**Le foncier ne mord jamais. L'opcode mord 70 à 80 % du temps.**

C'est la confirmation, depuis l'intérieur du modèle, du goulot mesuré de l'extérieur : **61,2 %
des transitions mensuelles sans construction alors qu'il y a ≥ 300 k£ en caisse**. Deux mesures
indépendantes, la même conclusion.

⚠️ **Et ça ne contredit pas « le pathfinder n'est pas le goulot ».** Les trois voies fermées
(A3/A4/A5) portaient sur le **budget d'itérations** du pathfinder : lui en donner plus, le
redistribuer, l'abaisser. Ce qui mord n'est pas le réglage du pathfinder, c'est **l'opcode
lui-même**. Le levier n'est donc pas d'en donner plus à la recherche, mais d'en **dépenser moins
par projet** — ce qui désigne C19 (pipelines `Valuate` au lieu de boucles Squirrel) et A7
(événements au lieu de sondage) comme les deux tâches qui attaquent la contrainte réellement
active.

### ⚠️ Correction du point 5 de §0 duotrigesies (même jour, après vérification des termes bruts)

La conclusion « quand ça mord, c'est l'opcode » **tient dans sa direction**, mais son amplitude
était gonflée. Vidage des cas contraignants (graine 42, 5 ans) :

```
mode=rail dominant=opcodes  opcodes_tension=1.20  opcodes_cost=111 722 285  opcodes_flow=5 626 663/mois  tau=16,5
mode=rail dominant=opcodes  opcodes_tension=1.82  opcodes_cost=233 450 705  opcodes_flow=5 628 752/mois  tau=22,7
```

`111 722 285 / 3 105 = 35 980` et `233 450 705 / 3 105 = 75 185` **itérations prédites** — alors
que `HARD_ITERATION_CAP` vaut **10 000** depuis A3. Le devis facture donc 4 à 7 fois un travail
que le plafond interdit. Tension réelle attendue : **~0,28**, ce qui reste la plus grande des
quatre (argent 0,11-0,15) : **l'opcode demeure la contrainte qui mord, mais il ne consomme pas
« deux ans de calcul »**. ➡️ C21.

🔑 **Au passage, le débit réel est mesuré pour la première fois** : `opcodes_flow ≈ 5,63 M/mois`,
soit **18,5 ticks de jeu par jour** et non les 74 souvent supposés. À 67 M d'opcodes par an, un
seul chantier rail au plafond de 10 000 itérations en consomme **31 M, soit 46 % de l'année**.
C'est le chiffre qui manquait pour situer le pathfinder à l'échelle du reste.

---

## 0 tertrigesies. 🔴 APRÈS C21 : PLUS RIEN NE MORD — et l'opcode n'était qu'un coût fantôme (2026-09-03)

Même sonde, même graines, même horizon, sur l'arbre corrigé par C21
(`docs/diag_tension_c21.json`).

| | avant C21 | après C21 |
|---|---:|---:|
| « ça mord » (tension ≥ 0,50) | 11-12 % | **2-3 %** (11 % sur la graine pauvre) |
| amplitude médiane de la dominante | 0,048-0,063 | **0,043-0,054** |
| **quand ça mord, c'est…** | **opcodes 70-80 %** | **argent 100 %, sur les trois graines** |

### 1. 🔴 Ma conclusion n°5 était entièrement un artefact

« Quand ça mord, c'est l'opcode » ne survit pas au correctif : une fois `expectedOpcodes` borné au
plafond réel du pathfinder, **l'opcode ne mord plus jamais**. Les 70-80 % venaient du devis
fantôme de 4 à 7 fois trop cher, pas du jeu. La leçon de méthode est la même que celle déjà au
dossier pour le premier banc de `knapsack_roi` : **une mesure faite sur un code défectueux mesure
le défaut, pas le phénomène.**

### 2. 🔑 Le vrai résultat : AUCUNE des quatre ressources n'est le mur

Dans **97 à 98 %** des évaluations, la ressource la plus tendue n'est consommée qu'à ~5 % par
l'action envisagée. Et dans les 2-3 % restants, c'est **toujours l'argent** — c'est-à-dire
exactement la ressource que le classement actuel met déjà au dénominateur.

➡️ **Le modèle de tension a fait son travail, et sa réponse est négative** : ni le capital, ni les
opcodes, ni les slots de véhicules, ni le foncier n'expliquent l'inaction. Un dénominateur composé
réallouerait entre quatre ressources dont aucune n'est rare. **A1 tel qu'il était posé n'est donc
pas le levier**, et ce n'est pas une déception : c'est la première réponse *négative propre* à une
question qui traînait depuis le 2026-09-01.

⚠️ Nuance à ne pas perdre : la graine **12345, la pauvre**, mord encore 11 % du temps, et
toujours sur l'argent. La trésorerie reste le mur **des parties pauvres** — ce qui est cohérent
avec le mur mesuré de 1970-1980 — mais pas des parties normales à 10 ans.

### 3. 🔴 Ce que la sonde montre en creux : le contrôleur ne REGARDE presque jamais

Chaque ligne `TENSION_COST` correspond à une reconstruction du portefeuille. Comptage sur 10 ans :

| graine | cycles de portefeuille | soit |
|---|---:|---|
| 42 | 52 | **5,2 par an** |
| 999 | 54 | 5,4 par an |
| 12345 | 15 | 1,5 par an |

**Le portefeuille est reclassé environ cinq fois par an.** Rapproché du goulot mesuré — 61,2 % des
transitions mensuelles sans construction alors qu'il y a ≥ 300 k£ en caisse — l'explication ne
serait pas que l'IA est **empêchée**, mais qu'elle ne **regarde pas** : rien ne la contraint, et
elle n'agit pas non plus.

⚠️ **Hypothèse, pas encore un fait.** Le portefeuille est mis en cache et peut être consulté entre
deux reconstructions ; le nombre de cycles n'est donc pas le nombre de décisions. Ce qu'il faut
vérifier avant d'y croire : compter, sur le même journal, les entrées `TASK`, `PROJECT_CHOSEN`,
`PROJECT_DISCARD` et `PORTFOLIO_EMPTY` par mois, et voir combien de mois ne portent **aucune** de
ces traces. La donnée est déjà produite ; il n'y a qu'à la lire.

### ➡️ Conséquence sur l'ordre des travaux

1. **Ne pas câbler le dénominateur pondéré maintenant.** Il n'a rien à réallouer : sa condition
   d'utilité — qu'une ressource soit réellement rare — n'est pas remplie 97 % du temps. Le garder
   comme instrument, pas comme chantier.
2. **Compter les mois sans aucune trace de décision** (ci-dessus). C'est gratuit et ça tranche
   entre « empêchée » et « inactive ».
3. Si c'est bien l'inaction : **A7 (événements) et C15 (cadence)** deviennent les items de tête,
   non plus comme « offre d'une ressource rare » mais comme **fréquence de décision** — ce qui est
   un tout autre mécanisme, et le seul que la mesure désigne encore.

---

## 0 quattuortrigesies. ⚪ C19 VALIDÉ : sans régression, mais SANS GAIN — et le vrai budget d'opcodes est enfin chiffré (2026-09-03)

Validation appariée `avant`/`après` sur le même arbre, 3 graines × 3 ans, l'arm `avant` étant une
copie de `ai/OpexAI` à `HEAD` (`sweeps`-hors-dépôt, supprimée après mesure).

### 1. ✅ Aucune régression : 3 graines sur 3 **bit-identiques**

| graine | valeur avant | valeur après | véhicules | gares |
|---|---:|---:|---:|---:|
| 42 | 617 922 | 617 922 | 59 → 59 | 17 → 17 |
| 999 | 720 386 | 720 386 | 49 → 49 | 10 → 10 |
| 7 | 2 742 574 | 2 742 574 | 137 → 137 | 32 → 32 |

⚠️ **Le risque d'ordre existait pourtant, et il n'a pas été levé — il n'a pas été rencontré.** Le
tri par défaut d'une `AIList` est **`SORT_BY_VALUE` DESCENDANT** (`script_list.cpp:397-403`), donc
`Valuate` **change l'ordre d'itération**. L'idiome « le dernier gagne » de `_refreshRail`
(`chosen = t` sans comparaison) y est sensible par construction. À 3 ans depuis 1970 il n'y a
qu'un ou deux types de rail disponibles, donc l'ambiguïté ne se présente jamais. ➡️ **Durcir
quand même** : `if (t > chosen) chosen = t`, ou `KeepTop(1)`. Une ligne, et le résultat cesse de
dépendre du tri.

### 2. ⚪ Et aucun gain : **toutes** les catégories sont identiques au millier d'opcodes près

`cat_rail` 2 577k → 2 577k, `cat_towns` 188k → 188k, `cat_road` 37k → 37k… sur les trois graines.

C'était prévisible une fois le bon modèle de coût en tête : `Valuate` facture **5 opcodes par
élément** plus l'appel du valuateur (`script_list.cpp:910`), c'est-à-dire à peu près ce que
coûtait le `if` qu'il remplace. Sur des listes de **4 types de rail** et de quelques dizaines de
moteurs, le gain est nul par construction. **Le pipeline `AIList` n'est pas un accélérateur
magique : il paie quand la liste est GRANDE et que le corps de boucle est CHER.**

### 3. 🔑 Le vrai budget d'opcodes, mesuré pour la première fois

C'est le sous-produit qui vaut la manœuvre. Par catégorie, sur 3 ans (milliers d'opcodes,
graines 42 / 999 / 7) :

| catégorie | 42 | 999 | 7 |
|---|---:|---:|---:|
| **`project_air`** | **40 777** | 39 169 | 31 721 |
| **`build_air_plans`** | 36 542 | 39 962 | **41 622** |
| **`cand_pax`** | 21 827 | **29 512** | 27 199 |
| `build_search` (rail) | 13 771 | — | — |
| `cand_freight` | 5 051 | 8 934 | 7 078 |
| `cand_road` | 2 788 | 3 424 | 4 607 |
| `cat_rail` | 2 577 | 3 972 | 3 089 |
| `project_water` | 1 787 | 2 148 | 1 818 |
| tout le reste (`cat_*`, `build_*`) | < 500 chacun | | |

➡️ **Trois catégories concentrent l'essentiel : la planification aérienne (`project_air` +
`build_air_plans`, ~75 M à elles deux) et la génération de candidats passagers (~25 M).** Le
catalogue, cible initiale de C19, pèse **moins de 4 M** — moins de 5 % du total. C19 a été appliqué
au mauvais endroit, ce que personne ne pouvait savoir avant d'avoir ce tableau.

⚠️ Rappel de §0 tertrigesies : **l'opcode ne mord plus** une fois `expectedOpcodes` corrigé. Ce
tableau dit où part le budget, **pas** qu'il manque. À utiliser pour rendre la planification
aérienne moins chère si on y touche, pas comme une urgence.
