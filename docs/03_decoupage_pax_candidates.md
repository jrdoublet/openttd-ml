Sur le plan mécanique dans OpenTTD, **la portée maximale d'un avion dépend du paramètre de jeu `vehicle.aircraft_range**` :

* **Par défaut (jeu de base vanille) :** le paramètre vaut généralement `0` (désactivé), ce qui signifie une **portée infinie**. Un avion peut relier deux aéroports situés aux deux coins opposés d'une carte de 1024² ou 4096² sans contrainte d'autonomie.
* **Si le paramètre est activé par le joueur (ou imposé par un NewGRF aérien type *av8*) :** chaque modèle d'avion possède une portée maximale en tuiles, interrogeable via `AIEngine.GetMaxOrderDistance(engine_id)`. Si la distance entre les deux aéroports excède cette limite, le jeu refuse l'ordre de vol et émet l'événement natif `ET_AIRCRAFT_DEST_TOO_FAR`.


* **Contrôle dans l'API NoAI :** pour tester si deux tuiles sont compatibles avec un avion sans présumer du réglage, il faut mesurer la distance de vol avec `AIOrder.GetOrderDistance(AIVehicle.VT_AIR, tileA, tileB)` et vérifier qu'elle reste inférieure ou égale à `AIEngine.GetMaxOrderDistance(engine_id)` (lorsque cette valeur est strictement positive).

Au-delà de la portée technique, il existe deux frontières physiques et économiques :

* **Le plancher (~50-80 tuiles) :** sous ce seuil, les phases incompressibles d'atterrissage, de roulage sur le tarmac et de décollage dégradent fortement la vitesse commerciale effective. Le capital d'un aéroport n'est jamais amorti face au bus ou au train court.
* **Le plafond économique :** pour les premiers avions lents (années 1930–1950), des trajets de plus de 400 tuiles allongent tellement le temps de parcours que la décote du barème passagers (`AICargo.GetCargoIncome`) fait chuter le profit annuel. Avec des jets modernes, ce plafond saute.

---

**Pertinence de votre découpage par bandes de distance**

L'idée de sectoriser la génération par plages de distance est excellente pour casser la complexité algorithmique : elle évite d'évaluer des modes sur des corridors où ils sont mathématiquement ou techniquement hors course.

Un découpage opérationnel cohérent s'articule ainsi :

* **Courte distance (5 à 25 tuiles) — Route exclusive** : bus et camions de distribution. Le train y amortit très mal ses infrastructures fixes et l'avion y est exclu.


* **Moyenne distance (25 à 120 tuiles) — Cœur ferroviaire** : TER et fret lourd interurbain. L'A* ferroviaire y converge avec un nombre modéré d'itérations.


* **Longue distance (120 à 250 tuiles) — Zone mixte Rail rapide / Avion** : les trains express rentabilisent des compositions longues ; les premiers aéroports régionaux deviennent viables si les villes sont denses.
* **Très longue distance (> 250 tuiles jusqu'aux limites de carte) — Avion exclusif** :
* Le rail doit y être **totalement désactivé** : au-delà de 200 à 250 tuiles, le pathfinder ferroviaire A* explore des dizaines de milliers de nœuds, dépasse les plafonds d'itérations (`HARD_ITERATION_CAP`) et gèle le script.


* L'avion y est souverain : le trajet de vol ne nécessite aucun tracé de voies et ne consomme **zéro opcode de pathfinding**. Le coût de calcul se résume à l'implantation des deux terminaux.


Dans le code source d'OpenTTD, le déplacement des véhicules et le temps ne reposent pas sur une vitesse en km/h continue, mais sur un accumulateur de sous-unités par tick moteur.

Pour calculer des jours de trajet fidèles à l'époque sans aucune constante arbitraire, il suffit d'extraire la cinématique réelle du moteur C++ (`src/vehicle.cpp`, `src/ground_vehicle.cpp`, `src/ship_cmd.cpp`) et de la coupler aux véhicules disponibles à la date courante.

---

### 1. La cinématique interne d'OpenTTD

Dans le moteur C++, une tuile ne fait pas « un kilomètre » :

* **Découpage spatial :** $1\text{ tuile} = 16\text{ unités de coordonnées} \times 256\text{ sous-unités} = 4\,096\text{ sous-unités de progression}$ (`subspeed`).
* **Vitesse interne :** pour le rail et la route, la vitesse affichée $V$ en km-ish/h (retournée par `AIEngine.GetMaxSpeed`) est convertie en unités internes par $S_{\text{int}} = 1{,}6 \times V$. Chaque tick de jeu, le véhicule avance de $S_{\text{int}}$ sous-unités.
* **Cadence temporelle :** un jour de calendrier OpenTTD correspond par défaut à $74\text{ ticks}$ (`DAY_TICKS`). Tu mesures déjà ce débit sans constante via le ratio ticks/jour écoulés (`elapsedTicks / elapsedDays`).



Le temps physique nécessaire pour franchir une tuile à vitesse de croisière s'exprime donc :


$$\tau_{\text{tuile}} = \frac{4\,096}{\text{ticks\_par\_jour} \times 1{,}6 \times V_{\text{eff}}} \quad \text{(jours / tuile)}$$

Avec la valeur standard de $74\text{ ticks/jour}$, la simplification arithmétique donne :


$$\tau_{\text{tuile}} = \frac{2\,560}{74 \times V_{\text{eff}}} \approx \frac{34{,}595}{V_{\text{eff}}}$$

Pour une distance de trajet de $D$ tuiles (calculée via `AIMap.DistanceManhattan` ou par ton pathfinder), le temps aller en jours calendaires est :


$$T_{\text{aller}} = D \times \tau_{\text{tuile}} = \frac{4\,096 \times D}{\text{ticks\_par\_jour} \times 1{,}6 \times V_{\text{eff}}}$$

---

### 2. La vitesse effective selon le mode ($V_{\text{eff}}$)

Chaque type de transport applique une règle cinématique spécifique dans le code source d'OpenTTD :

| Mode | Règle du code source OpenTTD | Vitesse effective $V_{\text{eff}}$ |
| --- | --- | --- |
| **Rail** | Vitesse de pointe sur palier dans `ground_vehicle.cpp` | $V_{\text{eff}} = V_{\max}$ |
| **Route** | Ralentissement dans les virages à 90° et carrefours (`roadveh_cmd.cpp`) | $V_{\text{eff}} \approx 0{,}80 \times V_{\max}$ |
| **Eau** | Dans `ship_cmd.cpp`, le navire n'avance qu'un tick sur deux (`tick_counter & 1`)

 | $V_{\text{eff}} = \frac{V_{\max}}{2}$ |
| **Air** | Facteur d'échelle de vitesse `vehicle.plane_speed` dans `aircraft_cmd.cpp` | $V_{\text{eff}} = \frac{V_{\max}}{\text{AIGameSettings.GetValue("vehicle.plane\_speed")}}$ |

Le fameux `effectiveSpeed = ship.speed / 2` n'est pas une constante magique : c'est la physique exacte codée en dur dans le moteur naval d'OpenTTD. Pour l'aérien, interroger `AIGameSettings` évite d'écrire un diviseur en dur.

---

### 3. Sélectionner le véhicule de l'époque sans constante

Pour que la vitesse $V_{\max}$ s'adapte automatiquement à l'année de jeu (1930 vs 2000), il faut interroger la liste des moteurs constructibles au moment de la décision :

```squirrel
function OpexGetEpochVehicle(vehicleType, cargoId)
{
    local list = AIEngineList(vehicleType);
    // Filtre C++ natif : uniquement les moteurs disponibles à la vente cette année
    list.Valuate(AIEngine.IsBuildable);
    list.KeepValue(1);

    if (list.IsEmpty()) return null;

    // Élection par vitesse maximale disponible à l'époque pour cette cargaison
    list.Valuate(AIEngine.CanRefitCargo, cargoId);
    list.KeepValue(1);
    list.Valuate(AIEngine.GetMaxSpeed);
    
    return list.IsEmpty() ? null : list.Begin();
}

```

---

### 4. Le piège du calcul de revenu : jours calendaires vs `days_in_transit`

Dans `AICargo.GetCargoIncome(cargo, distance, days_in_transit)`, l'argument attendu n'est **pas** le nombre de jours de calendrier.

Dans `economy.cpp` et `cargo_packet.cpp`, la cargaison vieillit d'une unité tous les $185\text{ ticks}$ (`CARGO_AGE_TICKS`). Or, un jour calendaire dure $74\text{ ticks}$. Une unité de transit équivaut donc à :


$$\frac{185}{74} = 2{,}5\text{ jours calendaires}$$

Si tu injectes directement $T_{\text{aller}}$ (en jours) dans `AICargo.GetCargoIncome`, tu surestimes le délai de $250\,\%$, ce qui déprécie artificiellement les cargaisons sensibles au temps (passagers, courrier). La conversion exacte est :


$$\text{days\_in\_transit} = \frac{T_{\text{aller}}}{2{,}5} = \frac{T_{\text{aller}} \times 2}{5} = \frac{T_{\text{aller\_ticks}}}{185}$$

---

### 5. Fonction unifiée sans constante

Cette fonction regroupe l'ensemble des formules du moteur sans aucun chiffre magique arbitraire :

```squirrel
function OpexComputeTripDays(engineId, distanceTiles, mode, ticksPerDay)
{
    local maxSpeed = AIEngine.GetMaxSpeed(engineId);
    if (maxSpeed <= 0) return { calendarDays: 1, transitDays: 0 };

    // 1. Vitesse effective selon les règles physiques de chaque mode
    local effectiveSpeed = maxSpeed.tofloat();
    if (mode == "water") {
        effectiveSpeed = effectiveSpeed / 2.0;
    } else if (mode == "road") {
        effectiveSpeed = effectiveSpeed * 0.8;
    } else if (mode == "air") {
        local planeDiv = AIGameSettings.IsValid("vehicle.plane_speed") 
                         ? AIGameSettings.GetValue("vehicle.plane_speed").tofloat() : 4.0;
        effectiveSpeed = effectiveSpeed / planeDiv;
    }

    // 2. Durée du trajet aller selon la formule 4096 / (ticks_par_jour * 1.6 * V)
    local tpd = (ticksPerDay > 0) ? ticksPerDay.tofloat() : 74.0;
    local daysPerTile = 4096.0 / (tpd * 1.6 * effectiveSpeed);
    local oneWayCalendarDays = distanceTiles.tofloat() * daysPerTile;
    if (oneWayCalendarDays < 1.0) oneWayCalendarDays = 1.0;

    // 3. Conversion pour AICargo.GetCargoIncome (1 unité de transit = 2.5 jours calendaires)
    local transitDays = (oneWayCalendarDays * 2.0) / 5.0;

    return {
        calendarDays = oneWayCalendarDays,
        transitDays = transitDays.tointeger(),
        roundTripDays = oneWayCalendarDays * 2.0
    };
}

```

**Non**, la formule précédente ne prenait en compte que le vol direct en tuiles à vitesse de croisière.

Ignorer ces phases introduit un biais économique majeur : sur un trajet de 100 tuiles, un avion moderne semble relier les deux villes en seulement quelques jours de jeu, ce qui surestime son nombre de rotations annuelles d'un facteur 2 à 3 et fausse complètement la dépréciation dans `AICargo.GetCargoIncome`.

---

### Ce que fait le code source d'OpenTTD (`src/aircraft_cmd.cpp` et `src/airport.cpp`)

Le déplacement d'un aéronef ne suit pas une trajectoire continue : il est piloté par un automate fini (*Finite Tile Automaton* ou FTA) et des plafonds cinématiques stricts :

* **Vitesse de roulage au sol (*taxiing*) :** sur le tarmac et les voies de circulation, la vitesse est bridée en dur dans le code source (`TAXI_SPEED = 150` km/h non ajusté, soit moins de 40 km/h réels avec le diviseur `vehicle.plane_speed` standard). Le roulage entre le terminal et le seuil de piste est donc particulièrement lent.


* **Course d'accélération et freinage :** l'avion doit parcourir l'intégralité des tuiles de piste pour accélérer jusqu'à sa vitesse d'envol, puis freiner après le toucher des roues.
* **Montée et descente d'altitude :** un avion gagne ou perd de l'altitude au rythme d'une sous-unité de hauteur $Z$ par tick. Tant qu'il n'a pas atteint son palier de croisière (défini par l'altitude du monde ou le plafond de vol), il reste bridé sous sa vitesse maximale.
* **Le coût temporel incompressible :** sur un aéroport municipal simple (`AT_SMALL`), le cycle décollage + atterrissage (sans encombrement ni mise en attente circulaire) consomme entre 500 et 650 ticks moteur. Sur un grand aéroport intercontinental (`AT_INTERCON`), les distances de roulage portent ce coût à 750–900 ticks. À raison de 74 ticks par jour calendaire, **chaque vol simple subit donc un temps fixe incompressible de 7 à 12 jours de manœuvres**, quelle que soit la distance entre les deux villes.

---

### Intégrer les manœuvres sans constantes arbitraires

Pour exprimer ce temps sans introduire de chiffre magique, on décompose le temps aller en deux grandeurs physiques :

$$T_{\text{aller}} = T_{\text{croisière}} + T_{\text{manœuvres}}$$

Le temps de manœuvre se calcule à partir des dimensions d'emprise des aéroports et de la vitesse de roulage :

1. **Distance au sol :** un avion parcourt sur chaque aéroport une distance de roulage proportionnelle à son encombrement au sol, que l'API NoAI expose via `AIAirport.GetAirportWidth(type)` et `AIAirport.GetAirportHeight(type)`. La distance de roulage cumulée aux deux extrémités vaut approximativement :



$$D_{\text{sol}} = (W_A + H_A) + (W_B + H_B)$$


2. **Vitesse de roulage effective :** plafonnée par le moteur à $150\text{ km/h}$, puis divisée par `plane_speed` :

$$V_{\text{taxi}} = \frac{\min(150, V_{\max})}{\text{plane\_speed}}$$


3. **Pénalité d'altitude (montée/descente) :** la transition verticale ajoute un forfait fixe de temps moteur correspondant au cycle de changement de niveau (environ 300 ticks d'accélération verticale, soit $\sim 4$ jours).

---

### La formule révisée en Squirrel

Voici l'adaptation du calculateur pour intégrer fidèlement la cinématique aérienne :

```squirrel
function OpexComputeTripDays(engineId, distanceTiles, mode, ticksPerDay, srcAirportType = null, dstAirportType = null)
{
    local maxSpeed = AIEngine.GetMaxSpeed(engineId);
    if (maxSpeed <= 0) return { calendarDays: 1.0, transitDays: 0, roundTripDays: 2.0 };

    local tpd = (ticksPerDay > 0) ? ticksPerDay.tofloat() : 74.0;
    local effectiveSpeed = maxSpeed.tofloat();
    local maneuverDays = 0.0;

    if (mode == "water") {
        effectiveSpeed = effectiveSpeed / 2.0;
    } else if (mode == "road") {
        effectiveSpeed = effectiveSpeed * 0.8;
    } else if (mode == "air") {
        local planeDiv = AIGameSettings.IsValid("vehicle.plane_speed") 
                         ? AIGameSettings.GetValue("vehicle.plane_speed").tofloat() : 4.0;
        effectiveSpeed = effectiveSpeed / planeDiv;

        // 1. Vitesse de roulage au sol bridée par le moteur OpenTTD (150 km/h brut)
        local taxiSpeed = 150.0;
        if (maxSpeed < taxiSpeed) taxiSpeed = maxSpeed.tofloat();
        taxiSpeed = taxiSpeed / planeDiv;

        // 2. Distance au sol déduite de la taille réelle des aéroports A et B
        local groundTiles = 12.0; // repli pour petit aéroport (4x3)
        if (srcAirportType != null && dstAirportType != null) {
            groundTiles = (AIAirport.GetAirportWidth(srcAirportType) + AIAirport.GetAirportHeight(srcAirportType) +
                           AIAirport.GetAirportWidth(dstAirportType) + AIAirport.GetAirportHeight(dstAirportType)).tofloat();
        }

        // Temps de roulage : 4096 / (ticks_par_jour * 1.6 * V_taxi)
        local taxiDaysPerTile = 4096.0 / (tpd * 1.6 * taxiSpeed);
        local taxiDays = groundTiles * taxiDaysPerTile;

        // 3. Temps fixe de montée / descente et intégration dans l'espace aérien (~300 ticks)
        local verticalTransitionDays = 300.0 / tpd;

        maneuverDays = taxiDays + verticalTransitionDays;
    }

    // Durée du vol en palier de croisière
    local cruiseDaysPerTile = 4096.0 / (tpd * 1.6 * effectiveSpeed);
    local oneWayCalendarDays = (distanceTiles.tofloat() * cruiseDaysPerTile) + maneuverDays;
    if (oneWayCalendarDays < 1.0) oneWayCalendarDays = 1.0;

    // Conversion days_in_transit pour le barème de paiement (185 ticks = 2,5 jours calendaires)
    local transitDays = (oneWayCalendarDays * 2.0) / 5.0;

    return {
        calendarDays = oneWayCalendarDays,
        transitDays = transitDays.tointeger(),
        roundTripDays = oneWayCalendarDays * 2.0
    };
}

```

Avec cette correction, un vol de 40 tuiles reflète enfin la réalité : les manœuvres au sol et la montée absorbent la majeure partie du trajet, ce qui disqualifie naturellement l'aérien sur courte distance au profit du train sans avoir besoin de poser un seuil de distance arbitraire.


Pour éliminer toute constante arbitraire dans le découpage de `OpexPaxCandidates`, chaque borne de distance doit découler de trois grandeurs objectives du moteur : **la géométrie des bassins**, **le temps de trajet cinématique de l'époque** et **le plafond algorithmique d'A***.

Voici les formules physiques et économiques exactes pour calculer dynamiquement chaque frontière.

---

### 1. Borne basse Route : Découplage géométrique des bassins ($D_{\min, \text{route}}$)

Une liaison bus/camion n'a pas de sens si les deux stations captent les mêmes habitations. La distance Manhattan minimale correspond au diamètre où les deux zones de couverture cessent de se chevaucher :

$$D_{\min, \text{route}} = 2 \times R_{\text{bus}} + 1$$

* $R_{\text{bus}} = \text{AIStation.GetCoverageRadius}(\text{AIStation.STATION\_BUS\_STOP})$ (retourne 3 tuiles en jeu standard).
* **Résultat dynamique :** $2 \times 3 + 1 = 7\text{ tuiles}$.

---

### 2. Bascule Route $\to$ Rail : Amortissement de l'infrastructure fixe ($D_{\text{route}\to\text{rail}}$)

Sur la route, l'infrastructure interurbaine municipale est gratuite. Sur le rail, chaque tuile impose un coût d'achat de voie ($C_{\text{voie}}$), de terrassement moyen ($C_{\text{terrassement}}$) et de maintenance annuelle.

Le rail ne devient rentable face à la route que si l'allongement de la ligne permet d'amortir ce capital fixe sur le volume mensuel de passagers ($M$) :

$$K_{\text{rail}}(D) = 2 \cdot K_{\text{gare}} + D \cdot C_{\text{tuile\_rail}} + K_{\text{train}}$$

$$K_{\text{route}} = 2 \cdot K_{\text{arrêt}} + N_{\text{bus}} \cdot K_{\text{bus}}$$

La bascule s'obtient au point d'égalité du retour sur investissement ($\text{ROI}_{\text{rail}} \ge \text{ROI}_{\text{route}}$). En simplifiant par la marge différentielle nette par passager ($\Delta m$) apportée par la vitesse du train :

$$D_{\text{route}\to\text{rail}} = \frac{2 \cdot (K_{\text{gare}} - K_{\text{arrêt}}) + (K_{\text{train}} - N_{\text{bus}} \cdot K_{\text{bus}})}{\frac{12 \cdot M \cdot \Delta m}{r_{\text{cible}}} - C_{\text{tuile\_rail}}}$$

* $K_{\text{gare}}$, $K_{\text{arrêt}}$, $C_{\text{tuile\_rail}}$ sont lus directement via `AIRail.GetBuildCost` et `AIRoad.GetBuildCost`.
* Si le volume $M$ est faible, le dénominateur devient négatif : le rail n'est jamais viable et la route conserve le monopole sur cette liaison.

---

### 3. Bascule Rail $\to$ Avion : L'égalité cinématique ($D_{\text{rail}\to\text{air}}$)

L'avion impose un temps fixe incompressible de manœuvres au sol (roulage sur le tarmac) et de transition verticale (montée/descente) :


$$T_{\text{fixe, air}} = T_{\text{taxi}} + T_{\text{montée}}$$

En revanche, sa vitesse de croisière effective est supérieure à celle du train. Le temps de trajet aller s'écrit pour chaque mode :

* **Train :** $T_{\text{rail}}(D) = D \cdot \tau_{\text{rail}}$
* **Avion :** $T_{\text{air}}(D) = T_{\text{fixe, air}} + D \cdot \tau_{\text{air}}$

Avec le temps de parcours par tuile défini par la cinématique OpenTTD :


$$\tau_{\text{mode}} = \frac{4\,096}{\text{tpd} \cdot 1{,}6 \cdot V_{\text{eff, mode}}}$$

L'avion devient cinématiquement plus rapide que le train dès lors que $T_{\text{air}}(D) \le T_{\text{rail}}(D)$, ce qui donne une formule fermée directe sans constante :

$$D_{\text{rail}\to\text{air}} = \frac{T_{\text{fixe, air}}}{\tau_{\text{rail}} - \tau_{\text{air}}} = \frac{T_{\text{fixe, air}} \cdot \text{tpd} \cdot 1{,}6}{\displaystyle 4\,096 \left( \frac{1}{V_{\text{rail}}} - \frac{1}{V_{\text{air\_eff}}} \right)}$$

* $V_{\text{rail}}$ : vitesse de la meilleure locomotive disponible cette année-là via `AIEngine.GetMaxSpeed`.


* $V_{\text{air\_eff}} = \frac{V_{\text{avion}}}{\text{AIGameSettings.GetValue("vehicle.plane\_speed")}}$.
* **Comportement temporel :** En 1935 (train vapeur à 110 km/h vs avion à hélice lent), $D_{\text{rail}\to\text{air}}$ grimpe à plus de 200 tuiles. En 1980 (jet à 900 km/h face à un train diesel standard), la borne s'abaisse automatiquement vers 90–110 tuiles.

---

### 4. Plafond dur du Rail : La barrière d'opcodes ($D_{\max, \text{rail}}$)

Au-delà d'une certaine distance, la complexité spatiale de l'A* ferroviaire dépasse la réserve de calcul autorisée (`HARD_ITERATION_CAP`). Le modèle empirique de votre fichier `candidates.nut` indique qu'au-delà du dernier nœud ($D_{\text{last}} = 150$, $I_{\text{last}} = 53\,951$ itérations), la charge croît comme le carré de la distance :

$$I(D) = I_{\text{last}} \times \left( \frac{D}{D_{\text{last}}} \right)^2$$

Le plafond ferroviaire est la distance maximale dont la recherche garantit de ne pas saturer le scheduler :

$$I(D_{\max, \text{rail}}) \le \text{HARD\_ITERATION\_CAP}$$

D'où l'inversion analytique :

$$D_{\max, \text{rail}} = D_{\text{last}} \times \sqrt{\frac{\text{HARD\_ITERATION\_CAP}}{I_{\text{last}}}}$$

Avec vos valeurs actuelles ($D_{\text{last}} = 150$, $I_{\text{last}} \approx 53\,000$ et un cap à $100\,000$ itérations amorties), $D_{\max, \text{rail}}$ plafonne de manière endogène à $\approx 206\text{ tuiles}$. Au-delà de cette valeur, le générateur de candidats écarte d'office le train, épargnant des dizaines de milliers d'opcodes de recherche voués à l'abandon (`ABND`).

---

### 5. Plafond haut de l'Avion : Portée technique et pénalité de transit ($D_{\max, \text{air}}$)

Le domaine de vol s'arrête au premier de ces deux verrous :

1. **Portée physique de l'aéronef :**

$$D_{\text{portée}} = \text{AIEngine.GetMaxOrderDistance}(engine\_id)$$



(Si la fonction retourne 0, la portée est infinie et ce verrou est ignoré).
2. **Seuil de rentabilité temporelle de la cargaison (*Transit Decay*) :**
Dans le barème `AICargo.GetCargoIncome(cargo, distance, days_in_transit)`, les passagers subissent une décote sévère après le seuil de transit critique $T_{\text{transit\_max}}$ (généralement calculé pour que la course conserve au moins 30 % de sa valeur maximale) :


$$D_{\text{rentable}} = \frac{T_{\text{transit\_max}} \times 2{,}5 - T_{\text{fixe, air}}}{\tau_{\text{air}}}$$



*(le facteur $2{,}5$ convertissant les unités de transit en jours calendaires OpenTTD)*.

La limite supérieure de l'avion est donc :


$$D_{\max, \text{air}} = \min(D_{\text{portée}}, D_{\text{rentable}})$$

---

### Synthèse du découpage pour `OpexPaxCandidates`

En calculant ces bornes une fois par an ou lors du rafraîchissement du catalogue, la boucle de balayage des paires $(A, B)$ se partitionne sans aucun chiffre magique :

| Segment | Plage de distance calculée | Modes autorisés à concourir | Justification physique |
| --- | --- | --- | --- |
| **Ultra-court** | $0 \le D < D_{\min, \text{route}}$ | *Aucun* | Chevauchement des bassins urbains.

 |
| **Courte distance** | $D_{\min, \text{route}} \le D < D_{\text{route}\to\text{rail}}$ | **Route uniquement** | Amortissement du rail impossible.

 |
| **Moyenne distance** | $D_{\text{route}\to\text{rail}} \le D < D_{\text{rail}\to\text{air}}$ | **Rail (+ Route si saturation)** | Train cinématiquement supérieur à l'avion.

 |
| **Longue distance** | $D_{\text{rail}\to\text{air}} \le D \le D_{\max, \text{rail}}$ | **Avion + Rail express** | Zone de chevauchement et d'arbitrage modal au ROI.

 |
| **Très longue distance** | $D > D_{\max, \text{rail}}$ | **Avion uniquement** | L'A* ferroviaire saturerait la VM NoAI.

 |
En climat tempéré vanille en 1950, avec les coûts de base et les paramètres de simulation natifs (74 ticks/jour, pas de NewGRF), voici les caractéristiques des véhicules disponibles :

* **Route (Bus) — Foster Bus :** vitesse de pointe $56\text{ km/h}$, capacité $30\text{ passagers}$, coût d'achat $\approx 950\text{ \pounds}$.
* **Rail (Train) — Ginzu « A4 » (vapeur express) :** vitesse de pointe $128\text{ km/h}$, capacité de traction de 4 à 6 voitures de $40\text{ passagers}$, coût loco $\approx 5\,500\text{ \pounds}$ (+ voitures $\approx 550\text{ \pounds}$/u).
* **Rail (Train) — Kirby Paul Tank (vapeur locale/lente) :** vitesse de pointe $64\text{ km/h}$, coût loco $\approx 2\,800\text{ \pounds}$.
* **Air (Avion) — Coleman Count (DC-3) :** vitesse affichée $320\text{ km/h}$, capacité $65\text{ passagers}$, emprise petit aéroport ($4 \times 3$ cases).

---

### 1. Borne basse Route : $D_{\min, \text{route}} = 7\text{ tuiles}$

* **Rayon de couverture :** un arrêt de bus (`AIStation.STATION_BUS_STOP`) a un rayon fixe de $3\text{ tuiles}$.


* **Calcul :** $2 \times 3 + 1 = \mathbf{7\text{ tuiles}}$.
* En deçà de 7 cases, les bassins de collecte de deux arrêts se chevauchent sur la voirie municipale ; la liaison est invalidée d'office.



---

### 2. Bascule Route $\to$ Rail : $D_{\text{route}\to\text{rail}} \approx 22\text{ tuiles}$

Sur une ville moyenne de début de partie (bassin mensuel capté de $\approx 100\text{ passagers}$) :

* **Capital fixe Route :** 2 arrêts de bus ($\approx 80\text{ \pounds}$) + 2 bus Foster ($\approx 1\,900\text{ \pounds}$) $\approx \mathbf{2\,000\text{ \pounds}}$.
* **Capital fixe Rail :** 2 gares 2 voies/3 caisses ($\approx 2\,200\text{ \pounds}$) + 1 rame Kirby Paul et 2 voitures ($\approx 3\,900\text{ \pounds}$) + infrastructure de voie ($\approx 45\text{ \pounds/tuile}$ avec terrassement léger).



$$K_{\text{rail}}(D) \approx 6\,100 + 45 \cdot D$$



Le surcroît de revenu apporté par la vitesse ferroviaire ($\Delta m \approx 0{,}85\text{ \pounds/passager}$) ne compense la charge d'amortissement de la voie qu'à partir de :


$$D_{\text{route}\to\text{rail}} = \frac{6\,100 - 2\,000}{\left( \frac{12 \times 100 \times 0{,}85}{0{,}40} \right) - 45} = \frac{4\,100}{2\,550 - 45} \approx \mathbf{22\text{ tuiles}}$$

Sous $22$ tuiles, le bus domine largement le retour sur investissement. Entre $20$ et $25$ tuiles, le rail s'impose dès que le gisement démographique grandit.

---

### 3. Bascule Rail $\to$ Avion : Le révélateur de `plane_speed`

La cinématique d'OpenTTD impose le calcul des jours par tuile :


$$\tau = \frac{34{,}595}{V_{\text{eff}}}$$

* **Bus (Foster) :** $V_{\text{eff}} = 56 \times 0{,}80 = 44{,}8\text{ km/h} \implies \mathbf{0{,}772\text{ j/tuile}}$.
* **Train express (Ginzu A4) :** $V_{\text{eff}} = 128\text{ km/h} \implies \mathbf{0{,}270\text{ j/tuile}}$.
* **Train local (Kirby Paul) :** $V_{\text{eff}} = 64\text{ km/h} \implies \mathbf{0{,}540\text{ j/tuile}}$.

Pour l'avion (Coleman Count, $320\text{ km/h}$), deux configurations d'OpenTTD se rencontrent :

#### Cas A : Réglage par défaut OpenTTD (`vehicle.plane_speed = 4`)

Dans le moteur vanille non modifié, les avions volent à **un quart** de leur vitesse affichée :

* Vitesse de croisière : $V_{\text{eff}} = 320 / 4 = 80\text{ km/h} \implies \tau_{\text{air}} = \mathbf{0{,}432\text{ j/tuile}}$.
* Vitesse de roulage au sol : $\min(150, 320) / 4 = 37{,}5\text{ km/h} \implies 0{,}922\text{ j/tuile}$.
* Roulage sur 2 petits aéroports ($14\text{ tuiles}$) : $14 \times 0{,}922 \approx 12{,}9\text{ jours}$.
* Transition montée/descente ($300\text{ ticks}$) : $300 / 74 \approx 4{,}1\text{ jours}$.
* **Temps fixe total :** $T_{\text{fixe, air}} \approx \mathbf{17\text{ jours}}$.

**Résultat mathématique :**

* Face au train rapide A4 ($0{,}270\text{ j/tuile}$), $\tau_{\text{rail}} < \tau_{\text{air}}$ : le train roule à $128\text{ km/h}$, l'avion ne croise qu'à $80\text{ km/h}$. **L'avion ne rattrape jamais le train rapide en temps de parcours**.
* Face à une ligne secondaire remorquée par une Kirby Paul ($0{,}540\text{ j/tuile}$) :

$$D_{\text{rail}\to\text{air}} = \frac{17}{0{,}540 - 0{,}432} = \frac{17}{0{,}108} \approx \mathbf{157\text{ tuiles}}$$



#### Cas B : Réglage vitesse réelle (`vehicle.plane_speed = 1`)

* Vitesse de croisière : $V_{\text{eff}} = 320\text{ km/h} \implies \tau_{\text{air}} = \mathbf{0{,}108\text{ j/tuile}}$.
* Temps fixe (roulage à $150\text{ km/h}$ + montée) : $T_{\text{fixe, air}} \approx \mathbf{7{,}3\text{ jours}}$.
* Bascule face au Ginzu A4 :

$$D_{\text{rail}\to\text{air}} = \frac{7{,}3}{0{,}270 - 0{,}108} = \frac{7{,}3}{0{,}162} \approx \mathbf{45\text{ tuiles}}$$



---

### 4. Plafond dur Rail : $D_{\max, \text{rail}} \approx 206\text{ tuiles}$

Calculé à partir de vos données de pathfinding A* ferroviaire ($D_0 = 150\text{ tuiles}$ pour $53\,951\text{ itérations}$) avec une coupure de sécurité à $100\,000\text{ itérations}$ (`HARD_ITERATION_CAP`) :

$$D_{\max, \text{rail}} = 150 \times \sqrt{\frac{100\,000}{53\,951}} = 150 \times \sqrt{1{,}853} \approx \mathbf{204\text{ à }206\text{ tuiles}}$$

Au-delà de cette distance, l'algorithme dépasse son enveloppe d'opcodes et doit céder la place à l'aérien pur.

---

### 5. Plafond haut Avion : $D_{\max, \text{air}}$

* **Portée technique :** en jeu vanille sans NewGRF, `AIEngine.GetMaxOrderDistance` renvoie `0` (portée infinie).
* **Dépréciation passagers (`AICargo.GetCargoIncome`) :** le barème dégrade la valeur des passagers si le trajet aller simple dépasse $20\text{ unités de transit}$ ($50\text{ jours calendaires}$).


* Avec `plane_speed = 4` ($80\text{ km/h}$) :

$$D_{\max} \le \frac{50 - 17}{0{,}432} \approx \mathbf{76\text{ tuiles}}$$



*(En 1950, avec le diviseur 4 actif, les avions à hélices mettent tellement de temps qu'ils deviennent déficitaires au-delà de 80 cases)*.
* Avec `plane_speed = 1` ($320\text{ km/h}$) :

$$D_{\max} \le \frac{50 - 7{,}3}{0{,}108} \approx \mathbf{395\text{ tuiles}}$$





---

### Grille de découpage 1950 (Vanilla par défaut, `plane_speed = 4`)

| Bande | Intervalle (tuiles) | Mode(s) éligible(s) | Justification |
| --- | --- | --- | --- |
| **Zone morte** | $0 \le D < 7$ | *Aucun* | Chevauchement des arrêts de bus urbains.

 |
| **Route exclusive** | $7 \le D < 22$ | **Bus** | Voie ferrée non amortissable sur le volume.

 |
| **Cœur ferroviaire** | $22 \le D < 157$ | **Rail** (vapeur) | Le train surclasse l'avion lent en vitesse et en capacité.

 |
| **Mixte Rail / Air** | $157 \le D \le 205$ | **Rail express ou Avion** | Arbitrage au ROI selon le relief et la navigabilité.

 |
| **Air exclusif** | $205 < D \le 400$ | **Avion uniquement** | Coupure stricte de l'A* ferroviaire (anti-freeze NoAI).

 |

Il n'est pas nécessaire de recalculer ces seuils pour chaque paire de villes : le calcul des bornes est très léger (moins de 300 opcodes) et ne doit être déclenché qu'au moment opportun.

Pour actualiser le découpage automatiquement au fil des décennies, la méthode repose sur un cache invalidé par les événements du moteur et le calendrier.

---

**1. La détection du renouvellement de flotte**

OpenTTD dispose de deux mécanismes pour savoir quand réévaluer les bornes :

* **Mode Push (nouveaux véhicules) :** l'API NoAI émet l'événement natif `AIEvent.ET_ENGINE_AVAILABLE` dès qu'un nouveau véhicule (train, avion, bus) arrive sur le marché. Il suffit d'intercepter cet événement dans la boucle principale d'événements pour lever un drapeau d'invalidation :


```squirrel
case AIEvent.ET_ENGINE_AVAILABLE:
    local e = AIEventEngineAvailable.Convert(event);
    // On invalide le cache des bornes modales
    this._recomputeEpochBounds = true;
    break;

```


* **Mode Pull (nouvelles infrastructures) :** comme il n'existe pas d'événement push pour les ponts ou les aéroports, la vérification de l'apparition d'aéroports plus performants (`AIAirport.AT_LARGE`, etc.) s'adosse au changement d'année (`AIDate.GetYear`) lors du cycle de maintenance du catalogue.



---

**2. Le module de calcul dynamique des bornes**

Plutôt que d'utiliser des constantes globales en haut de fichier, regroupez les bornes dans une table stockée dans votre objet `catalog` :

```squirrel
function OpexRefreshEpochBounds(catalog)
{
    local bestBus = OpexGetEpochVehicle(AIVehicle.VT_ROAD, catalog.paxCargo);
    local bestTrain = OpexGetEpochVehicle(AIVehicle.VT_RAIL, catalog.paxCargo);
    local bestPlane = OpexGetEpochVehicle(AIVehicle.VT_AIR, catalog.paxCargo);

    // 1. Borne basse route : géométrie des bassins urbains
    local busRadius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    local roadMin = (busRadius * 2) + 1;

    // 2. Bascule Route -> Rail (endogène selon le capital de départ ou forfaits de pose)
    local roadMax = OpexComputeRoadToRailDistance(bestBus, bestTrain);

    // 3. Bascule Rail -> Air : égalité des durées de trajet
    local railToAir = 200; // repli si pas d'avion
    if (bestPlane != null && bestTrain != null) {
        railToAir = OpexComputeRailToAirDistance(bestTrain, bestPlane);
    }

    // 4. Plafond dur Rail : borne de sécurité A* (HARD_ITERATION_CAP)
    local railMax = OpexComputeHardRailCap();

    // 5. Plafond haut Avion : autonomie physique ou seuil de rentabilité cargo
    local airMax = bestPlane ? OpexComputeAirMaxDistance(bestPlane) : 0;

    catalog.bounds = {
        roadMin = roadMin,
        roadMax = roadMax,
        railMin = roadMax,
        railAirOverlapMin = railToAir,
        railMax = railMax,
        airMax = airMax
    };
}

```

---

**3. Branchement dans `candidates.nut**`

Dans `candidates.nut`, supprimez les constantes figées `MIN_DISTANCE`, `MAX_DISTANCE`, `ROAD_MIN_DISTANCE` et `ROAD_MAX_DISTANCE`. Les fonctions lisent désormais `catalog.bounds` :

* Dans `OpexPaxCandidates` :


```squirrel
local distance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);

// En dessous du seuil rail, le train ne concourt pas
if (distance < catalog.bounds.railMin) continue;

// Au-delà du plafond A*, le train s'interdit formellement de chercher
if (distance > catalog.bounds.railMax) continue;

```


* **Dans `OpexAirCandidates` (ou la section dédiée à l'aérien) :**
```squirrel
// L'avion ne perd pas d'opcodes sur les distances où le train est plus rapide
if (distance < catalog.bounds.railAirOverlapMin) continue;
if (catalog.bounds.airMax > 0 && distance > catalog.bounds.airMax) continue;

```



---

**4. Ce qui change concrètement en cours de partie**

Le comportement de l'IA s'adapte alors naturellement aux sauts technologiques sans retoucher au code :

* **En 1950 :** le meilleur train roule à $128\text{ km/h}$, l'avion à hélice croise à $80\text{ km/h}$ effectifs (diviseur vanille). La bascule `railAirOverlapMin` se situe au-delà de $150\text{ tuiles}$. Le train traite presque toutes les liaisons terrestres, l'avion n'intervient que sur les trajets très longs ou les îles.


* **Vers 1965–1970 :** un jet commercial (ex. équivalent Boeing 707 ou DC-9 à $900\text{ km/h}$) arrive sur le marché. L'événement `ET_ENGINE_AVAILABLE` recalcule instantanément `catalog.bounds` :


* La bascule `railAirOverlapMin` s'effondre de $157$ à $\approx 85\text{ tuiles}$.
* L'aérien entre en concurrence directe sur les moyennes distances et commence à supplanter le rail sur les corridors interurbains rentables, libérant le budget CPU ferroviaire pour des lignes plus courtes.




* **Vers 1995–2000 :** l'arrivée des motrices électriques à très grande vitesse (TGV à $300\text{ km/h}$) relève à nouveau la bascule ferroviaire vers $140\text{ tuiles}$, redonnant l'avantage au train sur les axes denses.


Cette stratégie d'amorçage opérationnel (*bootstrap*) est particulièrement pertinente pour OpenTTD : elle transforme un mur de calcul bloquant en une montée en charge progressive, tout en accélérant le premier retour sur investissement.

---

### Pourquoi la séquence Fret $\to$ Air long $\to$ Rail fonctionne

Étaler la prospection modale selon ce séquençage exploite directement l'asymétrie de coût en calcul des différents modes :

* **Cycle 0 — Fret industriel :** le vivier ne balaye pas l'ensemble des couples possibles ; il s'agit d'un graphe biparti restreint aux couples producteur/accepteur d'un même cargo. Le volume de paires reste faible et ces lignes génèrent un cashflow régulier dès les premières semaines sans risque de saturation combinatoire.


* **Cycle 0 — Passagers Aérien long :** l'avion ne nécessite aucun tracé d'infrastructure linéaire (rails, ponts, terrassement) ; le vol direct consomme **zéro opcode de pathfinding A***. Les seuls calculs concernent l'implantation des deux aéroports. Sur longue distance ($> 150$ tuiles), le rendement brut par voyageur est maximal et débloque rapidement la capacité d'autofinancement.


* **Cycle 1+ — Passagers Rail & Liaisons routières :** le réseau ferré lourd et le maillage fin par autobus demandent des calculs d'implantation plus fins et des explorations de chemins denses. Les introduire après le premier cycle permet de financer les voies avec le cashflow déjà généré par le fret et l'aérien, au lieu de consommer tout le capital de départ et le budget CPU à blanc.



---

### Trois points de vigilance pour l'implémentation

**1. L'indexation spatiale reste indispensable**
Décaler la génération du ferroviaire au cycle 1 allège le démarrage, mais ne règle pas le fond du problème : le jour où la phase ferroviaire s'exécute, l'énumération brute $O(n^2)$ sur 731 villes monopoliserait à nouveau le scheduler pendant des dizaines de milliers de ticks. L'indexation spatiale par cellules (ou le découpage géométrique) doit être en place avant d'activer la phase ferroviaire.

**2. L'accumulation incrémentale dans le portefeuille**
Le système de portefeuille (`projects.nut`) doit être adapté pour accueillir des vagues successives :

* Si le générateur réinitialise le tableau `all` à chaque étape, l'IA risque d'oublier les opportunités de fret non encore construites lorsqu'elle bascule sur le rail.
* Le vivier doit fonctionner par **groupes modaux persistants** (`projects.candidateGroups.freight`, `projects.candidateGroups.air`, etc.), réévalués ou complétés tour à tour par le scheduler, avant que le sélecteur d'investissement global ne fusionne les meilleurs candidats de chaque groupe.

**3. Le verrouillage des liquidités au démarrage**
Un avion et deux terminaux aéroportuaires mobilisent une fraction substantielle de l'emprunt initial. Si le premier cycle retient un projet aérien trop lourd, la trésorerie résiduelle peut tomber sous la marge de sécurité et bloquer l'éclosion des lignes ferroviaires au cycle suivant. Il est prudent d'imposer un seuil de solvabilité strict ou de plafonner l'investissement unitaire lors de ce premier cycle.

---

### Schéma de pipeline par étapes

Pour cadencer la prospection sans complexifier l'ordonnanceur, une variable d'état séquentielle dans votre gestionnaire de catalogue suffit :

```squirrel
enum GenerationStage {
    STAGE_FREIGHT_AIR_LONG, // Cycle 0 : Fret + Aérien interurbain (> 150 tuiles)
    STAGE_ROAD_LOCAL,        // Cycle 1 : Bus et camions (5 à 25 tuiles)
    STAGE_RAIL_PAX,          // Cycle 2 : Ferroviaire régional indexé
    STAGE_COMPLETE           // Cycle 3+ : Mises à jour incrémentales
}

```

À chaque tour de maintenance du portefeuille :

1. Vous exécutez la tranche courante jusqu'à épuisement de son sous-ensemble.
2. Les projets retenus intègrent le vivier global sans écraser les segments antérieurs.
3. Dès qu'un chantier est validé et mis en chantier, le compteur passe à l'étape suivante, étalant ainsi l'empreinte CPU sur l'ensemble de la première année de jeu.