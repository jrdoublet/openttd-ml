# Mécanique du jeu — référence de conception

**Source** : [wiki OpenTTD, *Manual/Game Mechanics*](https://wiki.openttd.org/en/Manual/Game%20Mechanics/)
et [*Manual/Towns*](https://wiki.openttd.org/en/Manual/Towns), lues le 2026-08-28. Série rail
[transporttycoon.net](https://www.transporttycoon.net/rail1) lue le 2026-08-30 (§12).
[*Community/Pseudo canals*](https://wiki.openttd.org/en/Community/Pseudo%20canals) lu le 2026-08-30 (§13).

Ce document n'est pas une copie du wiki : c'est ce qui **change la conception d'`OpexAI`**. Chaque
section donne la règle, puis ce qu'on en fait. Les valeurs marquées ⚙️ sont des **paramètres de
partie** vérifiables dans le jeu plutôt que des constantes ; les points marqués ❓ n'ont pas été
vérifiés indépendamment du wiki.

---

## 1. Le paiement d'une livraison

Quatre facteurs : quantité, valeur du cargo, **distance**, **délai**.

- Les valeurs de base sont pour **100 unités livrées sur 1 tuile**, et **montent avec l'inflation**
  (⚙️ notre config gelée a `inflation = false`, donc ce terme est neutralisé chez nous).
- La **distance est Manhattan entre les tuiles-noms des deux gares** — c'est exactement ce que
  calcule notre `AIMap.DistanceManhattan`, donc l'estimateur est cohérent avec le moteur.
- Le **temps compte uniquement le cargo à bord d'un véhicule** (pas l'attente en gare).

**Pénalités de retard**, cumulatives :

| étape | pénalité |
|---|---|
| après le délai « livraison rapide » | −0,4 % par jour |
| après le délai « livraison tardive » | −0,4 % par jour **de plus** |
| plafond | **−88 %** |
| au-delà du plafond | facteur supplémentaire `31 / (x + 32)`, `x` = jours après saturation |

Chaque cargo a ses deux délais. Exemples cités : **passagers = 0 jour rapide / 24 jours tardif** ;
**courrier = 20 / 90**.

> **Conséquence pour OpexAI.** Les passagers n'ont **aucune fenêtre de grâce** : la pénalité court
> dès le premier jour de transport. Sur une ligne longue et lente, le revenu unitaire s'effondre
> avant même le seuil tardif. C'est le vrai mécanisme derrière l'effondrement du rendement à longue
> distance qu'on mesure dans `docs/opex_cost_model.json` — ce n'est pas seulement le coût de
> recherche qui explose, c'est aussi le revenu unitaire qui fond. **Les deux jouent dans le même
> sens**, ce qui renforce le choix de lignes moyennes.
>
> `AICargo.GetCargoIncome(cargo, distance, days)` implémente déjà toute cette formule : on n'a pas
> à la réimplémenter, mais on doit lui passer un `days` réaliste — voir §2.

### 1 bis. La formule exacte, vérifiée dans le source (2026-08-29)

**Source consultée** : [smart-calculators.net / OpenTTD cargo income
calculator](https://smart-calculators.net/en-US/tools/openttd-cargo-income-calculator), lue le
2026-08-29. ✅ **Recoupée ligne à ligne avec le code du jeu** (`src/economy.cpp:977-1023`,
`GetTransportedGoodsIncome`, et `src/script/api/script_cargo.cpp:73-77`) : la page est **exacte**.
C'est la première source du projet qui donne la formule sous forme fermée plutôt qu'en prose.

```
I = ⌊ D · T · A · P / 2²¹ ⌋

D  distance de Manhattan entre les tuiles-noms des deux gares
A  quantité livrée
P  cs->current_payment du cargo (3 185 passagers, 5 916 charbon, 6 144 biens, tempéré)
T  facteur de temps, entier de 31 à 255 :

      tp = clamp(jours_calendaires · 2 / 5, 0, 255)     (1 « jour wiki » = 2,5 jours de jeu)
      a  = max(tp − d₁, 0)
      T  = max(255 − a − max(a − d₂, 0), 31)
```

`2²¹` vient du `BigMulS(..., 21)` du source. Les deux pentes de §1 sont donc **−1 puis −2 points sur
255**, soit −0,39 % puis −0,78 % par « jour wiki » — le « −0,4 % » du wiki est cette pente-là, et le
plancher `T = 31` est le plafond de **−88 %**.

⚠️ **Le facteur additionnel `31 / (x + 32)` mentionné en §1 n'existe pas dans le source de la 15.3.**
Le plancher est un simple `max(..., 31)`. Ce point du wiki est soit périmé, soit une lecture fautive.

Seuils par cargo (tempéré), `d₁` / `d₂` : passagers **0 / 24**, charbon 7 / 255, biens — / 33,
grain — / 44, courrier — / 110, bétail — / 22, valeurs 1 / 32, bois 5 005 — / 255, acier — / 255,
pétrole — / 255. Un `d₂ = 255` veut dire qu'un cargo lourd ne franchit en pratique jamais la seconde
pente.

**Trois réserves que la page énonce et que nous devons garder en tête :**

1. **Les NewGRF de cargo (FIRS, ECS, YETI) remplacent tout.** Le source confirme : un cargo qui
   déclare `CBM_CARGO_PROFIT_CALC` court-circuite la formule entière. Sans objet dans notre config
   gelée, mais toute campagne sous NewGRF invaliderait l'étage 1.
2. **`P` est `current_payment`, donc indexé sur l'inflation.** ⚙️ Notre config a `inflation = false`,
   le terme est neutralisé — la page donne les valeurs de base 1950.
3. **`D` est la distance entre les GARES BÂTIES**, pas entre la ville et l'industrie visées.
   OpexAI passe à `GetCargoIncome` la distance entre les tuiles du CATALOGUE. Pour la route l'écart
   est petit (l'arrêt reste dans le rayon de recherche : 16 tuiles en ville, 5 sur une industrie),
   mais pour le rail `STATION_SEARCH_RADIUS = 30` autorise un écart bien plus grand. **Biais connu,
   non mesuré**, et il joue dans les deux sens.

> **Ce que la formule confirme de nos choix.** Le revenu est **linéaire en distance** et
> **décroissant en temps** : à vitesse donnée, `D · T(D/v)` monte puis retombe, ce qui donne bien un
> optimum de distance intermédiaire — le même que celui mesuré empiriquement à 48-63 tuiles
> (`docs/opex_cost_model.json`). Les deux lectures, l'analytique et la mesure, concordent.
>
> Et pour les passagers, `d₁ = 0` veut dire qu'**il n'y a pas de palier plat** : chaque tranche de
> 2,5 jours coûte un point de `T` dès le départ. C'est pourquoi une desserte routière **courte** de
> passagers est bonne alors qu'une longue serait mauvaise.

### 1 ter. 🔴 Aller ET retour pour les passagers, retour à vide pour le fret

La page ne traite que d'**une livraison** : elle ne dit rien du cycle d'un véhicule. C'est à nous de
le modéliser, et **nous le faisions à moitié** (corrigé le 2026-08-29, `economy.nut`).

|  | sens du flux | trajets **chargés** par aller-retour |
|---|---|---|
| passagers, ville ↔ ville | **bidirectionnel** — chaque ville produit pour l'autre | **2** |
| fret, producteur → accepteur | **une seule direction** — l'accepteur ne produit pas ce cargo | **1** |

Le fret est structurellement à sens unique dans OpexAI : `OpexFreightCandidates` et
`OpexRoadFreightCandidates` n'apparient qu'un producteur à un accepteur du **même** cargo. C'est
déjà la raison pour laquelle le puits reçoit `OF_NONE` et non `OF_FULL_LOAD_ANY` — un convoi qui
attend un chargement de retour inexistant reste bloqué pour toujours (mesuré le 2026-08-28).

**Le défaut** : le modèle comptait la demande des **deux** villes pour le passager
(`monthly = production_A + production_B`) mais ne lui accordait qu'**un seul trajet chargé par
aller-retour**, exactement comme au fret. Les deux côtés de l'équation étaient donc incohérents.

Conséquences, et il faut être précis sur laquelle mord quand :

- **Toujours** : `trainsForVolume` demande **deux fois trop de véhicules** pour une ligne passagers.
  Coût de fonctionnement et capital immobilisé sont surestimés d'autant, donc le profit attendu est
  sous-estimé et de bons candidats passagers sont écartés avant même d'être tentés.
- **Seulement si la ligne est limitée par la CAPACITÉ** (`carried = monthlyCapacity < offered`) :
  le tonnage transporté, donc le revenu, est sous-estimé d'un facteur 2.

⚠️ **Ce défaut n'explique PAS l'écart ×10 observé sur la ligne bus passagers** de
`docs/opexai_route.md` §6 : cette ligne était limitée par la **demande** (`carried = offered = 33`),
pas par la capacité, donc le facteur 2 n'y mordait pas. Son écart vient d'ailleurs — très
probablement de `TOWN_CATCHMENT_SHARE_PCT = 22`, calibré sur des **gares rail**. Les deux problèmes
sont réels et distincts ; ne pas créditer le second au premier.

**Le correctif** (`economy.nut`, rail et route) : la grandeur qui compte n'est pas « aller-retours
par mois » mais **trajets chargés par mois**. Elle vaut `30 / oneWayDays` pour une ligne
bidirectionnelle et `30 / roundTripDays` pour une ligne à sens unique. Le fret est inchangé au bit
près ; seul le passager voit sa capacité doubler.

---

## 2. Vitesses et conversion tuiles/jour — **corrige un placeholder d'OpexAI**

- L'unité interne est le **km-ish/h**. Conversion : `1 km-ish/h = 1,00584 km/h` (et `× 1,6` pour
  les mph). En pratique on peut lire les vitesses de l'API comme des km/h.
- Une tuile vaut **664,2 km-ish** de long pour le calcul de vitesse.
- **⇒ 100 km/h ≈ 3,6 tuiles par jour** (1,8 tuile/seconde de temps réel).
- **Avions : ils volent au quart de leur vitesse affichée** (⚙️ réglable, `plane_speed`, défaut 4).
- **Trains : la vitesse est bridée par les courbes.** À courbure 0 (virage à 90°) : rail 61 km/h,
  monorail 91, maglev 121. À courbure 2 : 111 / 166 / 221 km/h.
- Véhicules routiers : accélération de 37 km-ish/h par jour. ❓

> **Conséquence, déjà appliquée.** `TILES_PER_DAY = 2` (PLACEHOLDER dans `candidates.nut`)
> a été remplacé : le trajet utilise **`0,036 × effectiveSpeed`** (traction, §2 bis).
> 100 km/h ≈ 3,6 tuiles/jour reste la conversion ; un train 1970 à ~160 km/h catalogue
> ferait ~5,8 tuiles/jour. L'ancien 2 sous-estimait le revenu, surtout sur le long.
> ⚠️ L'hypothèse « cela repoussera l'optimum 34-36 vers 48-63 » n'est **pas** tenue :
> le coût A\* amorti dit l'inverse (le court). Rendement mesuré §2 bis / §8.3 :
> médiane réelle / catalogue **0,96**, pas de retuning.
>
> **Et l'avantage de l'avion n'est PAS la vitesse.** Au quart de la vitesse affichée, un avion de
> 1970 n'écrase pas un train. Son avantage est ailleurs et il est exactement celui de notre
> philosophie : **zéro pathfinding, zéro infrastructure linéaire**. À dire précisément, sinon on
> justifie la bonne décision par la mauvaise raison.

### 2 bis. Traction réaliste du train — modèle retenu pour OpexAI (2026-08-29)

**Source vérifiée** : OpenTTD 15.3, `src/ground_vehicle.cpp` et `src/train_cmd.cpp`, avec les
unités publiques de `AIEngine.GetPower` (hp), `GetWeight` (tonnes),
`GetMaxTractiveEffort` (kN) et `AICargo.GetWeight` (tonnes). Le moteur agrège bien la puissance et
la masse de **tout le convoi chargé** avant de calculer son accélération ; une locomotive n'est donc
pas une vitesse catalogue indépendante de ses wagons.

Sur rail normal et plat, pour une vitesse `v` en km/h-ish, le moteur calcule :

```
F(v) = min(TE * 1000, puissance_hp * 746 * 18 / (5 * v))
R(v) = masse * (10 + 15 * (512 + v) / 512) + trainee(v)
a(v) = (F(v) - R(v)) / (masse * 4)
```

`10` est la résistance des essieux et `15` le roulement ; ce sont les deux termes du source. La
traînée dépend aussi du nombre d'éléments. Pour les véhicules de base (notre partie gelée, sans
NewGRF), le jeu dérive son coefficient de la vitesse maximale ; OpexAI reproduit cette branche.
Pour un cargo fret, le moteur multiplie en plus le poids du cargo par le réglage
`vehicle.freight_trains` ; l'IA le lit également. Les wagons sont donc évalués à
`poids à vide + AICargo.GetWeight(capacité)`, pas à vide.

OpexAI cherche la vitesse de croisière où `F > R`, puis intègre l'accélération depuis et vers les
deux gares. Il en résulte une vitesse moyenne de trajet utilisée pour les jours, les passages par
mois et le revenu. Ce remplacement supprime le précédent facteur fixe de 70 % : puissance, effort
de traction, masse du wagon plein, nombre de wagons, vitesse du wagon et distance changent tous le
résultat.

**Ce que ce modèle ne sait pas avant A*.** La géométrie du futur tracé n'existe pas encore : on ne
peut donc pas compter les pentes, ponts, tunnels ou virages sans faire fuiter le résultat du
pathfinding dans le classement. Les plafonds du moteur restent 61 km/h pour un angle droit et
111 km/h pour une courbure 2 ; OpexAI n'invente pas une proportion de virages.

✅ **Mesure 2026-08-30** (`docs/opex_speed_yield.json`, panneau `RV`, n = 832) : médiane
réelle / catalogue **0,96**, réelle / traction **1,18**. 20 % des instantanés ≤ 61 km/h,
53 % ≥ 150. L'hypothèse « pas de fraction de virages » tient en médiane. L'ancien 70 %
était trop pessimiste. ⚠️ Pas de retuning.

---

## 3. La note de gare — le multiplicateur oublié de notre estimateur

**« S'il n'y a qu'une gare autour, un pourcentage des marchandises disponibles égal à la note de la
gare lui est distribué toutes les 2,5 journées. »** Autrement dit :

> **cargo réellement capté = production × note_de_gare.**

Notre étage 1 suppose implicitement une note de 100 %. C'est le **défaut le plus important** relevé
dans cette lecture.

Facteurs, calculés **par type de cargo** :

| facteur | condition | points | % |
|---|---|---|---|
| vitesse du véhicule (÷2 route, ÷12,8 avion, plafond 255) | > 85 km/h | `(v−85)/4` | 0-17 % |
| âge du véhicule | 2 ans / 1 an / neuf | 10 / 20 / 33 | 4 / 8 / **13 %** |
| **temps depuis le dernier ramassage** | 60-105 s | 25 | 10 % |
| | 30-60 s | 50 | 20 % |
| | 15-30 s | 95 | 37 % |
| | **< 15 s** | **130** | **51 %** |
| cargo en attente | > 1500 | −90 | **−35 %** |
| | 1001-1500 | −35 | −14 % |
| | 601-1000 | 0 | 0 |
| | 301-600 | 10 | 4 % |
| | 101-300 | 30 | 12 % |
| | < 100 | 40 | 16 % |
| statue en ville | construite | 26 | 10 % |

*Le temps depuis le dernier ramassage est **multiplié par 4 si le dernier véhicule était un
bateau**.* Événements ponctuels : publicité petite/moyenne/grande +64/+112/+160 ; accident −160 ;
pot-de-vin raté −255 (et, en avion, vide la gare).

La note est recalculée **toutes les 2,5 journées** et ne peut bouger que de **2 points (0,78 %) par
cycle**, sauf événement.

**Les secondes du wiki sont du temps réel.** À 74 ticks/jour et ~33,3 ticks/seconde, **1 jour ≈
2,22 s**. Le tableau se relit donc :

| seuil du wiki | ≈ en jours de jeu | bonus |
|---|---|---|
| < 15 s | **< 6,8 jours** | +51 % |
| 15-30 s | 6,8 - 13,5 jours | +37 % |
| 30-60 s | 13,5 - 27 jours | +20 % |
| 60-105 s | 27 - 47 jours | +10 % |

> **Conséquences pour OpexAI**, et elles sont structurantes :
> 1. **La fréquence bat la capacité.** Le plus gros facteur (51 %) est le délai entre deux
>    ramassages. Beaucoup de petits convois passant souvent valent mieux que peu de gros. Cela
>    contredit l'intuition « un train long = plus de capacité ».
> 2. **Sous-servir est doublement puni** : le cargo s'accumule (jusqu'à −35 %) *et* le délai de
>    ramassage s'allonge. La dégradation est auto-renforçante.
> 3. **La note monte (ou descend) lentement** (2 points / 2,5 jours). Relu en 15.3 (§8.4) : une
>    gare neuve démarre à **175/255 (~69 %)**, pas à 0 — `HasRating()` (cargo arrivé) n'a
>    donc rien à rattraper depuis zéro, seulement l'écart entre 175 et sa cible réelle (souvent en
>    dessous, d'où une note qui *descend* au début plutôt que monte). Un écart de 50 points prend
>    ~2 mois à se résorber, dans un sens comme dans l'autre. Le revenu attendu doit quand même être
>    escompté au démarrage, mais depuis 69 %, pas depuis 0. `STATION_RATING_PCT = 50` tient.
> 4. **Renouveler les véhicules a une valeur mesurable** : 13 % pour du neuf contre 4 % à 2 ans.
> 5. La note plafonne bien en dessous de 100 % sans statue et sans vitesse : c'est un plafond
>    structurel à modéliser, pas un détail.

---

## 4. Production des industries — le rendement composé du bon service

✅ **Relu en 15.3** (`industry_cmd.cpp` `ChangeIndustryProduction`, tag
[OpenTTD 15.3](https://github.com/OpenTTD/OpenTTD/tree/15.3)). Notre config
est `economy.type = 1` = `ET_SMOOTH`. Vanilla, pas de callback NewGRF :
`UsesOriginalEconomy()` est faux, donc **seul l'appel mensuel** change la
production (l'appel quotidien « random » `monthly=false` sort tout de suite).

- Production **toutes les `INDUSTRY_PRODUCE_TICKS = 256` ticks**, soit 8 ou 9
  fois par mois. `GetLastMonthProduction` est un signal complet.
- **4,5 % de chance de changement par mois** et par cargo produit :
  `Chance16I(1, 22)` ≈ 1/22. Amplitude **3,9–23 %**
  (`(RandomRange(50)+10) * rate >> 8`, plancher 1 unité).
- Seuils en 256e : `PERCENT_TRANSPORTED_60 = 153` (≈ 59,8 %),
  `PERCENT_TRANSPORTED_80 = 204` (≈ 79,7 %). Le wiki arrondit à 60 / 80.

Probabilités de **sens**, *conditionnellement à un changement* :

| service | hausse | baisse |
|---|---|---|
| `DontIncrProd` tempéré (puits de pétrole) | 0 % | 100 % |
| faible (≤ 153/256 transporté) | 33 % | 67 % |
| bon (154–204) | 67 % | 33 % |
| **excellent (> 204/256)** | **83 %** | 17 % |

⚠️ Le commentaire du source 15.3 dit « *very high station ratings (over 80 %)* ».
C'est **faux** : le test est `PctTransported() > 204`, pas la note de gare.
La note n'entre que **indirectement** : `MoveGoodsToStation` capte
`production × (rating+1)`, ce qui peut monter le % transporté.

`INDUSTRYLIFE_BLACK_HOLE` (banques tempérées, centrales) : **aucun**
changement. Secondaires (`Processing`) : pas ce barème ; fermeture possible
après des années sans production. Plateforme pétrolière : passagers plafonnés
à 16. Wiki 100 ans ×10,35 / ×106,62 : cité, pas recalculé ici. Sur 20 ans
ça resterait de l'ordre de ×1,6 / ×2,5.

> **Conséquence pour OpexAI.** Bien servir une primaire **fait croître sa
> production**, via le % transporté, pas via la note. L'étage 1 prend un
> instantané `GetLastMonthProduction` : on n'y met **pas** un facteur de
> croissance. L'écart fret ~4-6x est réfuté (0,98). ⚠️ **Pas de retuning.**
> Ne pas ajouter un terme « service composé » au classement sans banc,
> défaut 0.

---

## 5. Croissance des villes

*Source complémentaire : [Manual/Towns](https://wiki.openttd.org/en/Manual/Towns).*

Une ville grandit de deux façons : en **démolissant un bâtiment pour en poser un plus grand**, ou
en **bâtissant sur une tuile vide adjacente à une route de la ville**.

### La condition d'accélération, et son plafond

> « La croissance peut être accélérée en **chargeant ou déchargeant au moins UNE unité de cargo**,
> dans **jusqu'à CINQ gares** de l'aire d'influence de la ville, sur une fenêtre de **50 jours**. »

Trois chiffres qui décident, et qui sont tous étonnamment bon marché :

1. **Une seule unité de cargo suffit.** Le volume ne joue pas. C'est une condition de *présence*,
   pas de débit.
2. **Le compte plafonne à 5 gares.** Au-delà, aucun gain de croissance supplémentaire.
3. La fenêtre est de **50 jours** — la même que celle de la note d'autorité locale (§7).

Autres règles :

- **Les villes (*cities*) croissent deux fois plus vite** que les *towns*, et démarrent plus
  grandes. ⚙️ Deux réglages contrôlent la proportion de cities et leur taille initiale.
- **Livrer des marchandises (*goods*) n'apporte AUCUN bonus de croissance** en tempéré : seule
  compte la condition d'activité ci-dessus.
- Conditions climatiques supplémentaires : sub-arctique au-dessus de la neige = **1 t de nourriture
  par mois** ; sub-tropical en désert = **1 t de nourriture et 1 000 L d'eau par mois** (l'eau doit
  atteindre un château d'eau). Dans les deux cas la **quantité au-delà du seuil n'apporte rien**.
  ⚙️ Sans objet dans notre config gelée (climat tempéré).
- **Un réseau routier préexistant accélère la croissance** : la ville pose des maisons au lieu de
  passer son tour à construire des routes. Les villes créent d'elles-mêmes un carrefour toutes les
  2-3 tuiles ; une grille posée par le joueur tous les 3 tuiles est l'optimum cité.
- Ordre de grandeur : une ville d'un million d'habitants occupe **150 à 200 tuiles de diamètre**.
- **Une banque apparaît dans les villes tempérées au-delà de 1 200 habitants** — donc une source de
  cargo *nouvelle* naît de la croissance qu'on provoque (à rapprocher de la churn du catalogue).

### ⚠️ Le piège wiki : notre propre rail peut étrangler la ville

> « La croissance exige que la ville ne soit **pas enfermée par des voies diagonales ou des voies
> signalisées**. »

C'est le point le plus dangereux de la page pour une IA ferroviaire : **une ligne mal placée autour
d'une ville tuerait la croissance de la ville qui nous nourrit.** Le dommage serait différé,
invisible dans l'immédiat, et frapperait précisément la source qu'on a payé cher à raccorder.

⚠️ **Mesure 2026-08-30** (`docs/opex_town_growth.json`) : les villes desservies n'estagnent
**pas** comme classe. Un effet local (maisons coincées par nos voies) n'est pas isolé.
L'item 2 du backlog **reste dernier** — pas de contrainte de tracé.

### Génération de passagers

À chaque cycle de 256 ticks et **par tuile de maison**, un tirage `0 ≤ X ≤ 255` ; si
`X ≥ population de la tuile`, rien ; sinon **`X/8 + 1` passagers** (arrondi inférieur). En
récession, la production est divisée par deux (arrondi supérieur).
Siège social : `256 / 4 tuiles / (6 − niveau)` passagers, `196 / 4 tuiles / (6 − niveau)` courrier.

> **Conséquences pour OpexAI.**
> 1. **La croissance s'achète très bon marché.** Une unité de cargo par 50 jours et par gare, cinq
>    gares au plus : il n'y a aucun besoin d'un gros débit pour déclencher l'effet. C'est un levier
>    presque gratuit sur une variable qui compose (§4) — et cela fait des **véhicules routiers un
>    activateur de croissance** autant qu'un moyen de transport, pour un coût en opcodes sans commune
>    mesure avec le rail.
> 2. **Le plafond à 5 gares borne l'investissement** : au-delà, on paie sans rien acheter en
>    croissance. Un chiffre dur à mettre dans la règle d'allocation.
> 3. **La production suit le nombre de tuiles de maisons**, pas la population affichée. Et desservir
>    une ville la fait croître : **la ligne fait grossir sa propre demande**. Comme en §4, cela
>    récompense la concentration plutôt que la dispersion.
> 4. **Poser de la route autour d'une ville desservie est un investissement de croissance** — bon
>    marché en opcodes, sans pathfinding long.
> 5. **Éviter d'enfermer la ville** : la page le dit, la mesure 2026-08-30 ne voit **pas**
>    de stagnation de classe (`docs/opex_town_growth.json`). L'item 2 du backlog reste
>    dernier — pas de contrainte de tracé tant qu'un effet local n'est pas isolé.
>
> ⚠️ **Piège opérationnel** : une gare **sans transfert depuis 50 jours** coûte **−15 par mois** de
> note d'autorité locale (contre +12 par gare active). Une ligne morte n'est donc pas seulement
> improductive, elle **dégrade activement** la capacité à construire dans cette ville. Cela rejoint
> la surveillance des lignes possédées déjà identifiée (industrie fermée).

✅ **Barème 15.3** (`GetNormalGrowthRate` / `CountActiveStations`, plus `UpdateTownGrowth`). Gare *active* :
`time_since_load ≤ 20` ou `time_since_unload ≤ 20` (~50 jours wiki). Table normale, n = 0…5+
gares actives : **320, 420, 300, 220, 160, 100** ticks ville. Notre `town_growth_rate = 2`
fait `m >>= 1` : **160, 210, 150, 110, 80, 50**, puis `/ (num_houses/50 + 1)`, encore `/2`
si city. n = 0 : **11/12** du temps la ville ne grandit pas (`Chance16(1,12)`) — le 320 n'est
donc pas plus rapide que le 420.

✅ **Mesure 2026-08-30** (`docs/opex_town_growth.json`, panneau `TV`, 5 graines × 20 ans).
Ville desservie = `GetClosestTown` d'une de nos gares. Le set desservi passe de ~5 à 25–34
villes : la médiane est **diluée** par les petites qu'on ajoute. Graine 42 : 424 → 1118
(×2,64) malgré +20 villes — elles ne stagnent pas. Les libres baissent (0,58–0,87) surtout
par composition. ⚠️ L'item 2 (ne pas enfermer le rail) **reste dernier** : pas de contrainte
de tracé. Le barème dit qu'1 à 5 gares actives accélèrent ; 0 gare bloque presque toujours.

---

## 6. Note de compagnie — ce que mesure `performance_history` du banc

Neuf composantes, 1 000 points au total. « Atteindre 50 % de la cible d'une composante donne 50 %
de ses points. »

| composante | cible | points | part |
|---|---|---|---|
| véhicules rentables | ≥ 120 véhicules | 100 | 10 % |
| gares desservies | ≥ 80 | 100 | 10 % |
| profit des véhicules de 2 ans et + | ≥ 10 000 £ | 100 | 10 % |
| plus faible revenu trimestriel | ≥ 50 k£ | 50 | 5 % |
| plus fort revenu trimestriel | ≥ 100 k£ | 100 | 10 % |
| **cargo livré** | **≥ 40 000 unités/an** | **400** | **40 %** |
| variété de cargos | ≥ 8 types/trimestre | 50 | 5 % |
| trésorerie | ≥ 10 M£ | 50 | 5 % |
| **emprunt** | **0** | 50 | 5 % |

> **Conséquence pour le banc.** Les cibles sont **basses** : 120 véhicules, 80 gares, 40 000 unités
> de cargo. AAAHogEx en construit 245 gares et 1 200 véhicules — il sature donc toutes les
> composantes, et AdmiralAI aussi presque. **Cela explique la saturation observée** (870 contre 896
> pour une valeur d'entreprise 3,7× supérieure) et **confirme que `company_value` est la bonne
> métrique** de comparaison, pas la note. Voir `docs/bench_v1.json`.
>
> Deux composantes gratuites à ne pas oublier quand même : **rembourser l'emprunt** (5 %) et
> **livrer 8 types de cargo** (5 %) — cette dernière plaide pour ne pas faire que du passager.

---

## 7. Note d'autorité locale

Barème des actions : détruire une route en bordure −18 à −100 ; à l'intérieur −50 à −100 ; un
tunnel ou pont −250 à 0 ; un bâtiment −40 à −300 ; **détruire une rivière −200** ; planter un arbre
**+7 (jusqu'à 220)** ; couper des arbres −35 ; pot-de-vin réussi +200 (jusqu'à 800), raté −50.
Construire une gare exige une note de seulement **−200** (donc quasi toujours permis).

**Évolution mensuelle automatique** : **+5** si la note est sous 200 ; **+12 par gare active**
(transfert dans les 50 derniers jours) ; **−15 par gare inactive**.

> **Conséquence pour OpexAI.** La construction de gares n'est pratiquement jamais bloquée, donc
> **pas besoin de gérer la note d'autorité au démarrage**. Elle ne devient un sujet que si l'IA
> démolit beaucoup (terrassement, destruction de bâtiments) ou laisse des gares mortes. Planter des
> arbres est le levier de rattrapage bon marché s'il en faut un un jour.

---

## 8. Vérifié dans le jeu plutôt que sur le wiki

Les six points sont clos. Le 4 est relu en 15.3 : inchangé.

1. ✅ Le réglage `plane_speed` réellement actif dans notre config : `4` (le défaut, non surchargé),
   vérifié dans l'`openttdlab.cfg` généré par un run `OpexAI` réel du 2026-08-28
   (`starting_year = 1970`, config figée) — pas supposé.
2. ✅ Économie lisse : `economy.type = 1` = `ET_SMOOTH`, et le barème wiki de §4
   **est** la formule 15.3 (`ChangeIndustryProduction`, `Chance16I(1,22)`,
   seuils 153/204). Pas de recalibrage empirique à faire. Recessions :
   `difficulty.economy = false`, distinct malgré le nom.
3. ✅ **Rendement de vitesse effectif** (2026-08-30, `docs/opex_speed_yield.json`) :
   médiane réelle / catalogue **0,96** (n = 832), réelle / traction **1,18**.
   Le plafond 61 km/h apparaît (20 % des instantanés) mais n'est pas le régime
   médian. `TILES_PER_DAY = 2` a déjà été remplacé par `0,036 × effectiveSpeed`.
   Pas de retuning.
4. ✅ **Courbe de note de gare, relue en 15.3** (2026-08-30). Tag
   [OpenTTD 15.3](https://github.com/OpenTTD/OpenTTD/tree/15.3) :
   `station_cmd.cpp` `UpdateStationRating`, `station_base.h`,
   `timer/timer_game_tick.h`. Inchangée par rapport à la lecture 13.4.
   - `INITIAL_STATION_RATING = 175` (sur 255, ~69 %), `MAX_STATION_RATING = 255`.
     Une gare **démarre à 175, pas à 0**. Tant que `HasRating()` est faux
     (aucun cargo encore arrivé sur ce type), la cible n'est pas calculée :
     si la note est sous 175 (pot-de-vin raté), elle remonte de **+1 par
     cycle** vers 175.
   - `Ticks::STATION_RATING_TICKS = 185`, `Ticks::DAY_TICKS = 74` →
     `185/74 ≈ 2,5 jours`. `StationHandleSmallTick` n'appelle
     `UpdateStationRating` que lorsque `delete_ctr` revient à 0.
   - Une fois `HasRating()` vrai (cargo arrivé à la gare, pas forcément
     un ramassage), chaque cycle recalcule une cible (vitesse
     `last_speed − 85` puis `>> 2` ; `time_since_pickup` ≤ 3 / 6 / 12 / 21
     cycles ; `max_waiting_cargo` ; statue +26 ; âge < 3 / 2 / 1 an) puis
     `Clamp(cible − note, −2, 2)`. Bornée à [0, 255].
   - Un écart de ~50 points prend `50/2 × 2,5 ≈ 62,5 jours ≈ 2 mois`.
     `STATION_RATING_PCT = 50` reste le calage empirique 15.3 (notes
     mesurées 49–55). ⚠️ Pas de retuning. Vanilla : le callback NewGRF
     `StationRatingCalc` n'existe pas chez nous.
5. ✅ Barème de croissance / gares actives, lu dans le source 15.3 et mesuré
   (`docs/opex_town_growth.json`, 2026-08-30).
6. ✅ **Sonde de catalogue 1950-2000** (2026-08-30, `docs/catalogue_churn_1950_2000.json`) :
   électrique 1967, INTERNATIONAL 1990, monorail 2000, maglev pas encore. Une
   campagne 1970-1989 a déjà l'électrique. `catalog.nut` prend le dernier type de
   rail : MONO en 2000 serait un piège, hors de nos 20 ans.

---

## 9. Tips de joueur — ce qui transpose à une IA

**Source** : [wiki OpenTTD, *Manual/Tips*](https://wiki.openttd.org/en/Manual/Tips), lu le
2026-08-28 (lecture demandée en section 1 du backlog). La page mélange raccourcis UI pour un
joueur humain (sans objet pour une IA NoAI) et heuristiques de conception transposables. Seules
ces dernières sont détaillées ici ; les raccourcis purement UI sont listés en fin de section pour
mémoire, sans développement.

- **Ordres partagés (`Ctrl`+clic)** — un groupe de véhicules peut partager le même jeu d'ordres, une
  modification s'appliquant à tous à la fois. Côté API NoAI : `AIOrder.ShareOrders(vehicle_id,
  main_vehicle_id)`. ❓ Non exploité par `OpexAI` aujourd'hui — chaque véhicule reçoit ses ordres
  individuellement à la construction. Pertinent surtout si l'IA doit un jour *modifier* les ordres
  d'une ligne existante (ex. ajouter un arrêt) : partager les ordres évite de reparcourir chaque
  véhicule un par un.
- **Boucles de gare routière** — une gare routière en ville fonctionne mieux insérée dans une
  boucle (le véhicule peut refaire un tour plutôt que s'égarer si la gare est pleine). Le mode
  **Route** est adopté (`docs/opexai_route.md`) ; TRACEX pose déjà une façade. Les boucles
  ne sont pas dessinées.
- **Mise à niveau des ponts** — remplacer un pont ancien par un modèle plus résistant/rapide évite
  de brider un train rapide. ❓ Pas mesuré : `OpexAI` ne revisite pas l'infrastructure existante
  après construction (voir [[ponts_tunnels_v3]] — `estimated_cost` gardé pour plus tard). À
  reconsidérer si des trains plus rapides sont introduits en cours de partie sur une ligne déjà
  construite avec un pont ancien.
- **Équilibre entre gares desservant une même industrie** — éviter d'assécher une industrie avec
  plusieurs types de transport si cela retire du volume à une route longue-distance plus rentable.
  Même logique que l'item 2 du backlog (« ne pas enfermer la ville »), appliquée à une
  industrie plutôt qu'à une ville : deux lignes d'`OpexAI` desservant la même source
  peuvent se cannibaliser plutôt que s'additionner. L'item 2 reste dernier (mesure
  villes : pas de stagnation de classe) ; la cannibalisation inter-lignes n'est pas
  mesurée.
- **Distance et vitesse comme leviers de profit** — déjà couvert en détail sections 1 et 2 de ce
  document ; la page tips ne fait que confirmer, sans détail chiffré supplémentaire.
- **Relations avec la ville** et **plantation d'arbres pour la note** — déjà couverts section 7
  (barème exact de la note d'autorité locale) ; la tip confirme l'idée déjà notée dans le backlog
  (section 9, « planter des arbres pour augmenter la réputation »), sans rien y ajouter.
- **Virages larges plutôt qu'à 90°** — déjà couvert section 2 : un virage à 90° bride un train rail
  à 61 km/h contre 111 km/h à courbure 2. La tip confirme sans nouveau chiffre. La série
  transporttycoon.net (§12) ajoute trois principes de jonction ; pas de cloverleaf tant que
  `JOINPATH` tient.
- **Canaux pseudo** — lus et intégrés §13. La tip les signale comme « peu coûteux » sans
  chiffrer opcodes ni argent : ce n'est pas un plan pour OpexAI. Le trick n'est pas un canal,
  c'est une inondation au niveau de la mer.
- **Un aéroport diffuse mieux son influence qu'une gare ferroviaire pour la génération de
  passagers/courrier.** ❓ Affirmation du wiki, pas vérifiée dans le code ni mesurée en jeu. Si
  confirmée, argument de plus (au-delà du gain d'`opexai_multimodal`) pour préférer l'avion sur les
  liaisons visant la croissance d'une ville plutôt que le rail seul — à croiser avec l'idée
  « contribuer à la croissance d'une ville avec des stations de bus/camions » (section 9 du
  backlog). Le mode Route est adopté ; la mesure `TV` 2026-08-30 ne distingue pas le
  mode d'activation.
- **Maintenance d'infrastructure** — pertinente seulement si `infrastructure_maintenance` est actif.
  ✅ Vérifié : `infrastructure_maintenance = false` dans notre `openttdlab.cfg` (2026-08-28) — donc
  **sans objet pour `OpexAI`** aujourd'hui. À reconsidérer seulement si la config gelée change.
- **Note de gare : véhicules rapides, ramassages fréquents, peu de cargo en attente, statue en
  ville.** Déjà couvert en détail et de façon chiffrée section 3 — la tip ajoute une précision
  absente de notre lecture initiale : une bonne note **augmenterait aussi la production de
  l'industrie** desservie. ✅ Relu en 15.3 : **faux comme terme direct**.
  `ChangeIndustryProduction` teste `PctTransported`, pas `ge.rating`. La note
  n'agit que via le cargo capté (`MoveGoodsToStation`). Le commentaire du
  source (« station ratings over 80 % ») est le même piège. Pas un levier
  ouvert ; l'écart fret ~4-6x est réfuté.

**Raccourcis UI sans objet pour une IA** (mentionnés pour mémoire, non développés) : aperçu de coût
avant construction (`Shift`), transparence des arbres/bâtiments (`x`), pose de signaux par glisser
(`Ctrl`+glisser court).

---

## 10. Industries — ce qui nourrit l'étage 1 fret

**Source** : [wiki OpenTTD, *Manual/Industries*](https://wiki.openttd.org/en/Manual/Industries), lu
le 2026-08-28 (lecture demandée en section 1 du backlog).

Notre config gelée est en climat **`temperate`** (vérifié dans l'`openttdlab.cfg`, cohérent avec
`landscape = temperate`) : seules les **13 industries tempérées** s'appliquent — Coal Mine, Forest,
Iron Ore Mine, Oil Wells, Oil Rig, Farm, Factory, Steel Mill, Sawmill, Oil Refinery, Power Station,
Bank. Les listes sub-arctique/tropicale/toyland du wiki ne nous concernent pas.

**Chaînes tempérées** (primaire → cargo → secondaire → cargo…) :

| primaire | cargo | secondaire | cargo | tertiaire |
|---|---|---|---|---|
| Coal Mine | Coal | Power Station | — | — |
| Forest | Wood | Sawmill | Goods | — |
| Iron Ore Mine | Iron Ore | Steel Mill | Steel | Factory → Goods |
| Farm | Grain, Livestock | Factory | Goods | — |
| Oil Wells / Oil Rig | Oil | Oil Refinery | Goods | — |
| — | Valuables | Bank | Valuables | — |

> **Ce qui ne change rien pour OpexAI.** `catalog.nut:230-231` interroge déjà
> `AIIndustryType.GetProducedCargo`/`GetAcceptedCargo` **dynamiquement** au lieu de coder cette
> table en dur — donc `OpexFreightCandidates` (`candidates.nut:158-174`) apparie déjà tout couple
> producteur/accepteur du même cargo sans avoir besoin de connaître la topologie ci-dessus. Cette
> table sert surtout à **comprendre** ce que le code découvre au runtime, pas à changer le code.

> **Ce qui est nouveau et potentiellement actionnable.**
> 1. ✅ **Croissance d'une primaire = % transporté, relu en 15.3** (`ChangeIndustryProduction`,
>    §4). Distinct de la croissance des villes. `OpexFreightCandidates` reste un
>    instantané `GetLastMonthProduction` : on n'y ajoute **pas** un facteur de
>    service. L'écart fret ~4-6x est réfuté (0,98). ⚠️ Pas de retuning.
> 2. **« Pendant une récession, la production primaire est réduite de moitié. »** ✅ Sans objet chez
>    nous : `difficulty.economy = false` (recessions désactivées), déjà vérifié section 8.2. Ce
>    n'est donc pas une source de variance à modéliser dans notre config gelée.
> 3. **Financement d'industries secondaires/tertiaires et prospection d'industries primaires** —
>    deux leviers de jeu qu'`OpexAI` n'utilise pas du tout aujourd'hui (aucune trace de
>    `AIIndustry.BuildIndustry` ou équivalent dans le code). Financer une usine pourrait créer
>    artificiellement un débouché pour une source déjà desservie mais sous-exploitée faute
>    d'accepteur proche. Non chiffré, non priorisé — à ajouter aux idées de fonctionnalités
>    (section 9 du backlog) si jugé pertinent.

---

## 11. Véhicules routiers, arrêts de bus et aires de chargement

**Sources** : [Manual/Tutorial/Buses](https://wiki.openttd.org/en/Manual/Tutorial/Buses),
[Manual/Building stations and loading bays](https://wiki.openttd.org/en/Manual/Building%20stations%20and%20loading%20bays),
[Manual/Road vehicles](https://wiki.openttd.org/en/Manual/Road%20vehicles), lues le 2026-08-28.

⚠️ **Ces trois pages sont décevantes** : essentiellement du tutoriel d'interface (« cliquez ici,
puis là »). Elles ne donnent **ni** taille d'aire de couverture d'un arrêt, **ni** règle
d'étalement de gare, **ni** condition d'acceptation de cargo, **ni** vitesse ou fiabilité chiffrée,
**ni** restriction sur les véhicules articulés, **ni** rien sur les sens uniques ou les types de
route. La page « Building stations and loading bays » ne distingue même pas les arrêts traversants
des arrêts en cul-de-sac. Tout cela reste donc à mesurer dans le jeu, pas à citer.

### La seule règle dure, et elle innocente notre code

> « Les bus ont besoin d'**arrêts de bus**, pas d'aires de chargement. » Les camions, l'inverse.

C'est une contrainte de type, pas une préférence : un bus ne chargera jamais sur une aire de
chargement pour camions. ✅ **Vérifié dans notre code** : `builder_road.nut` appelle bien
`AIRoad.BuildRoadStation(..., AIRoad.ROADVEHTYPE_BUS, ...)` aux deux extrémités
(type imposé par le cargo). **Cette piste est écartée** comme cause du non-chargement de la
v1 (notes −1) : c'était la façade du dépôt, 2026-08-28. Voir `docs/opexai_route.md`.

### Ce que les pages apprennent quand même

- **Six orientations d'arrêt** : quatre culs-de-sac posés *à côté* d'une route, et deux
  traversants posés *sur* une route existante. L'entrée doit faire face à la route ; quand
  l'orientation est bonne, le jeu prolonge lui-même la route jusqu'à l'arrêt. ❓ La page ne dit pas
  ce qui se passe si l'orientation est mauvaise (échec de construction, ou arrêt construit mais
  inaccessible — la seconde hypothèse serait exactement notre symptôme).
- **Un véhicule neuf démarre à l'arrêt** (`Stopped`) : le tutoriel insiste sur le fait qu'il faut
  cliquer la barre d'état pour le lancer. ❓ À vérifier côté API : `AIVehicle.BuildVehicle` suivi
  de `AIVehicle.StartStopVehicle` — un convoi jamais démarré produirait exactement une note à −1 et
  zéro recette.
- **Ordres** : `Go To` gare A puis `Go To` gare B, la boucle se referme d'elle-même.
- **Le dépôt** doit être proche d'un arrêt mais n'a aucune contrainte de voisinage de maisons.
- **Le wiki lui-même prévient qu'une courte liaison bus « ne sera probablement pas très
  rentable »**. Les recettes nulles de la v1 étaient un bug de façade. Le mode adopté a un
  profit réel (pax médiane 3,91× le prédit) et un plancher `ROAD_MIN_PROFIT_ANNUAL = 1000`.
- **Regrouper plusieurs arrêts en UNE gare** (`Ctrl`+clic) : le wiki cite ×5 de volume.
  Testé (`road_multistop`, 2026-08-30) : le second arrêt se pose, les 4 véhicules ne
  paient pas (ligne pax appariée 8 905 → 1 781). ⚠️ Défaut 0.

### Le plafond de deux véhicules par arrêt — la contrainte que les autres pages taisaient

**Source complémentaire** : [Manual/Loading Bays](https://wiki.openttd.org/en/Manual/Loading%20Bays),
lue le 2026-08-28. Nettement plus substantielle que les trois précédentes.

> **Un arrêt de bus n'accueille au plus que DEUX bus à la fois.** Idem pour une aire de chargement
> camions : deux camions au maximum.

Les véhicules excédentaires **font la queue sur la route** devant l'arrêt, ce que le wiki reconnaît
comme une source de blocages de circulation « quasi inévitables ». Rien ne limite en revanche le
nombre de véhicules *affectés* à un arrêt : le jeu laisse donc volontiers construire une flotte qui
s'auto-congestionne.

Le **multistop** est la réponse prévue : plusieurs arrêts partageant le même nom et le même cargo
forment une seule gare logique, et les véhicules se répartissent entre les emplacements au lieu de
s'entasser. L'extension est bornée par l'**étalement maximal de gare** (⚙️ réglage de partie), avec
un message d'erreur au-delà. Les **arrêts traversants** sont cités comme la disposition la plus
efficace, sans que la page en détaille la mécanique. ❓

> **Conséquences pour OpexAI.**
> - **Le dimensionnement d'une ligne bus n'est pas libre** : au-delà de 2 bus par arrêt, ajouter un
>   véhicule dégrade la ligne au lieu de l'améliorer. `MAX_ROAD_VEHICLES = 2` est cette règle.
>   Le multistop relâche le plafond seulement si les deux bouts ont doublé, et ce n'est pas
>   adopté (défaut 0).
> - **La congestion est un mode d'échec propre à la route**, absent du rail dans notre code (une
>   ligne rail à voie unique a ses propres blocages, mais pas ce plafond de deux). Un bus coincé
>   dans une file n'est pas détecté par notre surveillance de lignes mortes, qui ne couvre que le
>   fret.
> - **Le multistop a été testé** (`road_multistop`, défaut 0) : le second arrêt se pose, ajouter
>   les véhicules jusqu'aux quais extra ne paie pas. Voir `docs/opexai_route.md` §7 item 4.
- **Les véhicules routiers ne se percutent jamais entre eux** ; le seul risque de destruction est
  un train à un passage à niveau. Une IA routière n'a donc pas à gérer de conflit de circulation,
  contrairement au rail — un argument de coût en opcodes en faveur de la route.

> **Conséquences pour OpexAI.**
> 1. **Le type d'arrêt n'était pas la cause du non-chargement v1** — écarté. C'était la
>    façade du dépôt (bit de route perpendiculaire, 2026-08-28). `StartStopVehicle` est
>    appelé. Le mode route est adopté.
> 2. **Le regroupement d'arrêts a été testé** (`road_multistop`, 2026-08-30) : le second
>    arrêt se pose (7/8 et 8/8), les 4 véhicules ne paient pas (ligne pax appariée
>    8 905 → 1 781). ⚠️ Défaut 0. Voir `docs/opexai_route.md` §7 item 4.
> 3. **Ne pas attendre du bus un profit de ligne** : le wiki l'annonce lui-même. Sa valeur est
>    ailleurs — croissance de ville (§5) et cargos supplémentaires pour la note de compagnie (§6).

---

## 12. Construction ferroviaire — série transporttycoon.net

**Source** : [Owen's Transport Tycoon Station](https://www.transporttycoon.net/rail1),
*Rail Building* parts 1–6 et l'index [*Rail Junctions*](https://www.transporttycoon.net/junctions)
(l'ancien « Junctionairy »), lus le 2026-08-30. Demandé en section 1 du backlog.

⚠️ **Ce n'est pas le wiki OpenTTD 15.3.** Les pages visent TTD + [TTDPatch](http://www.ttdpatch.net/)
(pré-signaux, `non-stop` modifié, construction sur pente). Chez nous : **path signals** et
**waypoints** sont natifs, `vehicle_breakdowns` n'est pas figé dans le `CFG` des campagnes OpexAI
(❓ défaut du moteur, pas le `0` de la campagne historique 13.4). On ne recopie **aucun** dessin
de cloverleaf. Seulement les règles qui changent une décision d'IA, et ce qu'OpexAI en fait déjà.

### 12.1 Point-à-point contre réseau

Deux layouts. **Point-à-point** : une ligne dédiée par paire de gares. C'est « the style used by
the AI with extremely limited success ». **Réseau** : la plupart des gares se rejoignent, un train
peut aller n'importe où. Coût initial plus haut, économie de voie ensuite ; trains perdus aux
jonctions (U-turn, « tourner à gauche pour aller à droite ») ; bouchons.

> **Conséquence pour OpexAI.** Nous *sommes* ce point-à-point. `JOINPATH` refuse tout chemin qui
> touche un rail déjà posé ; chaque ligne a sa voie et son dépôt. Le banc join a mesuré plus de
> construction, pas plus de valeur (`station_join` défaut 0). Un réseau (spread, jonctions, voies
> partagées) recréerait ce banc. **Ne pas « améliorer » OpexAI en réseau tant que la v1 ne paie
> pas.** Les problèmes de trains perdus et de cloverleafs ne s'appliquent pas tant que
> `JOINPATH` tient.

### 12.2 Signaux

Deux familles, deux règles :

| type | le train choisit | où le poser |
|---|---|---|
| **bidirectionnel** | la voie **libre** (même si ce n'est pas la bonne direction) | devant chaque quai d'une gare multi-voies |
| **sens unique** | la voie qui **pointe vers la destination** ; s'il est rouge, il attend | aux jonctions, pour forcer une branche |

Un sens unique **dos au train** : le train ne prend pas cette voie ; s'il y arrive, il s'arrête,
fait demi-tour, revient. Utile pour forcer un dépôt.

Les **pré-signaux** TTDPatch (entrée / sortie / combo) : rouges si *toutes* les sorties suivantes
sont rouges, donc un train n'entre pas dans une gare pleine pour se coller au premier quai. En
OpenTTD 15, l'équivalent est le **path signal** (PBS), pas ce trio TTDPatch. ❓ Non posé par
OpexAI.

> **Conséquence.** `builder_rail.nut` ne pose **aucun** signal (`BuildSignal` absent). Sur une
> ligne dédiée à un seul train, c'est inoffensif. Dès que `trains > 1` sur la même voie unique
> (le modèle peut aller jusqu'à 8), deux convois se partagent un bloc sans réservation — ❓
> collisions ou file à la gare, **non mesuré**. Premier signal à poser, si on en pose : un
> bidirectionnel par quai, pas un sens unique au milieu de la ligne.

### 12.3 Gares — hors de la ligne principale

La gare doit être **à l'écart** de la ligne de transit, sinon le trafic de passage s'arrête
dedans. Deux géométries :

- **Terminus** : on entre et on sort par le même bout. Un train qui sort bloque celui qui entre.
  À réserver aux villes / montagnes (manque de place).
- **Ro-Ro** (roll-on / roll-off) : on traverse. Pas d'attente entrée/sortie. Un Ro-Ro mal signalé
  + ordre *full load* sur un quai occupé = gridlock (le train attend le quai le plus proche,
  jamais l'autre).

Le train **ne doit pas dépasser le quai** : la queue sort, le signal reste rouge, le chargement
est beaucoup plus long. « Make all stations the same length. » **Overflow** (boucle, dépôt-refuge,
pré-signaux) : seulement si un troisième train arrive alors que les quais sont pleins.
**Sortie longue** : longueur du plus long train **+ 2 tuiles**, pour que le convoi dégage le quai
avant le signal de fusion.

> **Conséquence.** OpexAI dimensionne déjà le quai sur la rame (`platformLength`, traction,
> `trainLengthLimit = platformLength * 16`) : la règle « pas plus long que le quai » est tenue.
> Une ligne = un quai dédié, terminus de fait, `OF_FULL_LOAD_ANY` à la source et `OF_NONE` au
> puits — le deadlock Ro-Ro + full load ne se pose pas. La sortie +2 tuiles, le Ro-Ro et
> l'overflow ne deviennent des leviers que le jour où plusieurs lignes **partagent** une gare
> et que des trains s'y croisent. Ce n'est pas le cas de la jointure v1 (quai parallèle, voie
> dédiée). Ne pas les construire « en prévention ».

### 12.4 Jonctions — trois principes, zéro cloverleaf

rail3 / rail4 : les 3-voies et 4-voies « basic » (un train à la fois) sont à éviter. Ce qui
survit indépendamment du dessin :

1. **Séparer avant de fusionner** (le CRAB le dit : split before merge → moins de rouges).
2. **La sortie de la ligne principale est *avant* l'entrée**, sinon un train qui se rabat
   bloque celui qui veut sortir.
3. **Distance entrée–sortie = plus long train + 2 tuiles** (comme la sortie de gare) : un train
   à l'arrêt au rouge ne barre pas l'autre branche.

Aussi : un **tunnel n'a pas de plafond de vitesse**, un pont si. Les virages à 90° tuent la
vitesse — déjà chiffré §2 (61 km/h). Un cloverleaf oblige à « tourner à gauche pour aller à
droite » → trains perdus, d'où les checkpoints.

L'index [*junctions*](https://www.transporttycoon.net/junctions) est un **catalogue d'images**
(Junctionairy, TTDPatch, pas de 90° « pour le réalisme »). Les sous-pages `junctions1`–`7` n'ont
pas de règle supplémentaire : on ne les recopie pas.

> **Conséquence.** OpexAI n'a aucune jonction. `JOINPATH` l'interdit. Le spread n'est pas la
> suite (banc join). **Quand** on dégelera les jonctions, ces trois principes + waypoints
> (§12.6) + signaux sens unique, pas un cloverleaf de 40 tuiles. Recopier un CRAB serait du
> TTDPatch, pas de la 15.3, et un gouffre d'opcodes.

### 12.5 Dépôts

Les pannes ralentissent tout le réseau ; un train qui *cherche* un dépôt peut s'engager dans
une branche et n'en plus sortir. Deux réponses de la page : (1) **forcer** le passage au dépôt
par un sens unique dos à la voie de contournement ; (2) un ordre **Go to depot**, natif
OpenTTD (`AIOrder.OF_SERVICE_IF_NEEDED` / dépôt dans la liste d'ordres), plus un intervalle
de service long.

⚠️ Un dépôt posé **en coupure** de la voie (le rail s'arrête, le dépôt, le rail reprend) : le
pathfinder ne « voit » pas au-delà. Les deux premiers dessins (dépôt en baie, voie continue)
passent ; le troisième non.

> **Conséquence.** OpexAI pose un dépôt **sur** la ligne dédiée, pas en coupure, et y construit
> les trains. Tant qu'il n'y a pas de réseau, un train ne se « perd » pas en cherchant un
> dépôt. Les pannes : ❓ `vehicle_breakdowns` n'est **pas** dans le `CFG` gelé des campagnes
> 15.3 (seulement dans `docs/methode.md` pour la 13.4). Si le défaut du moteur n'est pas 0,
> des pannes existent déjà sur nos lignes sans signaux — non mesuré. Ne pas ajouter d'ordres
> dépôt « pour faire réseau ».

### 12.6 Waypoints (ex-checkpoints)

En TTDPatch, un checkpoint est une gare d'une tuile + ordre *non-stop* au sémantique patché.
**OpenTTD a un outil waypoint dédié** : ordre « aller au waypoint », le train traverse sans
s'arrêter. C'est la réponse au cloverleaf et aux trains perdus.

> **Conséquence.** Inutile tant que `JOINPATH` tient (pas de branche à se tromper). Le jour des
> jonctions, un waypoint sur la bonne branche est plus cheap en opcodes qu'un cloverleaf
> « qui marche tout seul ». API : `AIRail.BuildRailWaypoint` / `AIOrder` vers un waypoint —
> ❓ non appelé aujourd'hui, à relire dans les en-têtes 15 le jour venu.

---

## 13. Pseudo-canaux — inonder plutôt que `BuildCanal`

**Source** : [wiki OpenTTD, *Community/Pseudo canals*](https://wiki.openttd.org/en/Community/Pseudo%20canals),
lu le 2026-08-30 (lecture demandée en section 1 du backlog). Complété par
[*Manual/Landscaping*](https://wiki.openttd.org/en/Manual/Landscaping) (inondation au niveau de
la mer, coût de rehausser depuis l'eau) et [*Manual/Water Transport Tiles*](https://wiki.openttd.org/en/Manual/Water%20Transport%20Tiles)
(canal, écluse, bouée). Page Community : technique de joueur, pas une spec d'API.

Les tuiles de canal officielles sont chères. La page imagine deux nappes d'eau à relier et
propose, faute d'argent pour un vrai canal :

1. **Abaisser tout le terrain entre les deux nappes, sauf un point sur chaque rive.** C'est le
   même geste que pour une jonction ferroviaire, dit la page — donc « ça ne coûte pas cher ».
2. **Abaisser les deux points restants.** L'eau envahit le sillon.
3. **Avoir le tracé exact (moins l'eau) avant d'ouvrir.** Terraformer **à sec** est bien moins
   cher que terraformer sous l'eau. Revenir en arrière — combler — coûte autant que d'avoir
   construit le vrai canal dès le départ.

On peut le faire plus large. C'est tout. Aucun chiffre d'argent, aucun opcode.

Deux règles qui ne sont **pas** dans cette page, et qui en bornent la portée :

- [*Landscaping*](https://wiki.openttd.org/en/Manual/Landscaping) : le terrain au niveau de la mer
  **inonde**, et toutes les tuiles sont emportées. Rehausser depuis la mer est extrêmement cher
  (volume, pas hauteur) et peut couler une compagnie jeune. Le trick n'est donc pas un canal
  posé sur la terre : c'est une **inondation contrôlée**, qui produit de la mer (tuile eau
  naturelle, sans propriétaire), pas une tuile `BuildCanal` (possédée, n'importe quelle altitude,
  écluses pour changer de niveau).
- [*Water Transport Tiles*](https://wiki.openttd.org/en/Manual/Water%20Transport%20Tiles) : un
  canal existe précisément **là où baisser ou hausser le terrain serait trop cher**. Une écluse
  est cotée £13 125, dont deux tuiles de canal à £3 750 (wiki, ❓ non recoupé dans le source 15.3).
  Un bateau ne gravit pas une rivière : sans écluse, le trick **ne monte pas une colline**. Il ne
  relie que deux nappes déjà au niveau 0, à travers une bande de terre qu'on est prêt à noyer.

> **Conséquence pour OpexAI.** `builder_water.nut` ne terraform jamais, ne pose ni canal, ni
> écluse, ni bouée. Le BFS ne suit que l'eau naturelle (`AreWaterTilesConnected`). Une paire
> sans composante commune est ignorée — ce n'est pas un oubli du trick, c'est le contrat de
> la v1 (une liaison pax entre deux villes côtières). **Ne pas ajouter de canal, vrai ou
> pseudo, pour un bateau passagers.**
>
> Le coût opcode + argent de N×`AITile.LowerTile` puis inondation, contre N×`AIMarine.BuildCanal`,
> n'est **pas mesuré** (❓). AdmiralAI terraform déjà pour le rail ; OpexAI n'appelle pas
> `LowerTile`. « Peu coûteux » est une phrase de joueur à la souris, pas un budget NoAI.
>
> La note d'autorité (§7) : détruire une rivière −200, un bâtiment −40 à −300. Noyer une ville
> n'est pas une économie, c'est une catastrophe de note — et de carte.
>
> Si un jour on relie deux lacs : (1) mesurer d'abord ; (2) terraform à sec, inonder en
> dernier ; (3) ne jamais `LowerTile` une tuile déjà eau ; (4) ne jamais rehausser depuis la
> mer ; (5) rester au niveau 0 — sinon ce n'est plus le trick, c'est `BuildCanal` + écluse.
