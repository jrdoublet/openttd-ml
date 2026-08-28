# Mécanique du jeu — référence de conception

**Source** : [wiki OpenTTD, *Manual/Game Mechanics*](https://wiki.openttd.org/en/Manual/Game%20Mechanics/)
et [*Manual/Towns*](https://wiki.openttd.org/en/Manual/Towns), lues le 2026-08-28.

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

> **Conséquence directe, à corriger.** `candidates.nut` porte `TILES_PER_DAY = 2` marqué
> « PLACEHOLDER ». La bonne valeur est **`0,036 × vitesse_km/h`**. Un train de 1970 à ~160 km/h
> donne **5,8 tuiles/jour**, soit près de **3× notre valeur actuelle**. Nous surestimons donc le
> temps de trajet, donc les pénalités de retard, donc nous **sous-estimons le revenu — et d'autant
> plus que la ligne est longue**. Combiné au modèle de coût, la distance est aujourd'hui pénalisée
> deux fois. Corriger cela devrait repousser l'optimum choisi (34-36 tuiles) vers l'optimum mesuré
> (48-63).
>
> ⚠️ Mais la vitesse *maximale* n'est pas la vitesse *effective* : virages, accélération, arrêts.
> Et la table des courbes dit que le bridage est sévère (61 km/h sur un virage serré). Il faut donc
> un **rendement de vitesse** calibré empiriquement, pas la vitesse catalogue brute.
>
> **Et l'avantage de l'avion n'est PAS la vitesse.** Au quart de la vitesse affichée, un avion de
> 1970 n'écrase pas un train. Son avantage est ailleurs et il est exactement celui de notre
> philosophie : **zéro pathfinding, zéro infrastructure linéaire**. À dire précisément, sinon on
> justifie la bonne décision par la mauvaise raison.

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
> 3. **La note monte lentement** (2 points / 2,5 jours ⇒ il faut ~2 mois pour aller de 0 à 100 %).
>    Une ligne neuve ne capte donc pas sa production nominale avant plusieurs mois — le revenu
>    attendu doit être escompté au démarrage.
> 4. **Renouveler les véhicules a une valeur mesurable** : 13 % pour du neuf contre 4 % à 2 ans.
> 5. La note plafonne bien en dessous de 100 % sans statue et sans vitesse : c'est un plafond
>    structurel à modéliser, pas un détail.

---

## 4. Production des industries — le rendement composé du bon service

- Production **toutes les 256 ticks, soit 8 ou 9 fois par mois**. `GetLastMonthProduction` est donc
  un signal solide et complet.
- ⚙️ **Économie « lisse »** (*smooth economy*) : **4,5 % de chance de changement par mois** et par
  industrie productrice. En économie TTD classique sur une carte 256×256, une seule industrie
  change par mois, par paliers de −50 % ou +100 %.

Probabilités de sens du changement, selon le **pourcentage transporté** :

| service | hausse | baisse |
|---|---|---|
| industrie « décroissante uniquement » (ex. puits de pétrole tempérés) | 0 % | 100 % |
| faible (< 60 % transporté) | 33 % | 67 % |
| bon (60-80 %) | 67 % | 33 % |
| **excellent (> 80 %)** | **83 %** | 17 % |

**Effet cumulé sur 100 ans** cité par le wiki : **×10,35** à ~70 % de service, **×106,62** au-delà
de 80 %. Les industries décroissantes perdent −6,8 % par an (demi-vie 9,84 ans).

Cas particuliers : les plateformes pétrolières plafonnent à 16 passagers par événement de
production ; les scieries ne produisent pas vraiment (elles cherchent des arbres 4-5 fois par mois,
max 225 t/mois) ; **les banques tempérées ne changent jamais de production**.

> **Conséquence pour OpexAI.** Bien servir une industrie **fait croître sa production de façon
> composée**. Sur notre banc de 20 ans, ×10,35 sur 100 ans ≈ **×1,6**, et ×106,62 ≈ **×2,5**. Ce
> n'est pas marginal : cela **récompense la concentration** (peu de lignes bien servies) plutôt que
> la dispersion, et cela rend la production de l'étage 1 **dynamique et endogène** — la valeur d'une
> ligne dépend de la qualité du service qu'on lui donnera. À intégrer comme facteur de croissance,
> pas comme constante.

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

### ⚠️ Le piège : notre propre rail peut étrangler la ville

> « La croissance exige que la ville ne soit **pas enfermée par des voies diagonales ou des voies
> signalisées**. »

C'est le point le plus dangereux de la page pour une IA ferroviaire : **une ligne mal placée autour
d'une ville tue la croissance de la ville qui nous nourrit.** Le dommage est différé, invisible dans
l'immédiat, et il frappe précisément la source qu'on a payé cher à raccorder.

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
> 5. **Éviter d'enfermer la ville** doit être une contrainte du constructeur rail, pas une
>    remarque : c'est un auto-sabotage différé.
>
> ⚠️ **Piège opérationnel** : une gare **sans transfert depuis 50 jours** coûte **−15 par mois** de
> note d'autorité locale (contre +12 par gare active). Une ligne morte n'est donc pas seulement
> improductive, elle **dégrade activement** la capacité à construire dans cette ville. Cela rejoint
> la surveillance des lignes possédées déjà identifiée (industrie fermée).

❓ **Ce que la page ne donne pas** : aucune formule chiffrée du taux de croissance, ni le barème
reliant le nombre de gares actives à l'intervalle entre deux constructions de maison. Cette table
existe dans le code source (`town_cmd.cpp`, `UpdateTownGrowRate`) mais **n'a pas été vérifiée ici**
— à mesurer chez nous plutôt qu'à citer de mémoire, une fois qu'un constructeur existe.

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

## 8. Ce qui reste à vérifier dans le jeu plutôt que sur le wiki

1. ⚙️ Le réglage `plane_speed` réellement actif dans notre config (le quart est le défaut).
2. ⚙️ Économie lisse ou TTD classique dans notre config gelée — les probabilités de §4 en dépendent.
3. Le **rendement de vitesse effectif** d'un train (vitesse réelle / vitesse catalogue), à mesurer :
   c'est ce qui rend `TILES_PER_DAY` honnête.
4. La **courbe de montée de la note de gare** sur une ligne neuve, pour escompter correctement le
   revenu des premiers mois.
5. ❓ La formule chiffrée de croissance des villes, absente du wiki.
