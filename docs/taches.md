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
