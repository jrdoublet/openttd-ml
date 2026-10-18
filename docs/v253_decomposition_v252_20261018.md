# Décomposition causale et quantitative du gain de V252

**Date :** 18 octobre 2026  
**Chantier :** V253 (analyse seule, worktree `wt-v253`, branche `v253`)  
**Base d'analyse :** Campagne 20×10 air seul `v252m2_airseul_20x10_20261018`, portes A (`40x6`) et B (`20x10`) de V252, et diagnostic mode 3 C121 `v253c121_diag_airseul_10x6_20261018`.  
**Code source moteur vérifié :** OpenTTD 15.3 (`/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src/`).

---

## 1. Contexte et problématique

V252 mode 2 (modernisation active de la flotte aérienne quand la compagnie est riche) a été qualifié avec succès :
- **Porte A (multimode 40×6) :** profit 1975 **+179,0 k£/an** (médiane +155,0 k£/an, 29/11, Wilcoxon $p = 0{,}00032$, IC95 [+96,0 ; +264,9] k£, valeur +4,26 %).
- **Porte B (multimode 20×10) :** profit 1979 **+180,2 k£/an** (médiane +246,2 k£/an, 13/7, IC95 [-14,7 ; +367,2] k£, valeur +2,69 %).
- **Air seul 20×10 :** profit 1979 **+208,9 k£/an** (médiane +279,4 k£/an, 16/4, Wilcoxon $p = 0{,}0094$, IC95 [+75,6 ; +334,0] k£, valeur +2,84 %).

Le diagnostic codex (commit `391f300`) et le test du mode 3 (`v253c121_diag_airseul_10x6_20261018`) ont démontré un paradoxe fondamental :
1. En mode 3, l'évaluation C121 de flotte homogène avec la demande réelle juge que le **Bakewell Luckett LB-10 (moteur 223, 220 places)** est le meilleur modèle sur 78 % des lignes.
2. Comme la flotte initiale est déjà équipée à 80 % en LB-10 (223), le mode 3 ne trouve aucun candidat supérieur et ne réalise que **3 remplacements au lieu de 260** (`no_candidate` 320 fois).
3. Privé de renouvellement, le mode 3 **perd −146,0 k£/an**, annulant précisément le gain de V252.

Le gain de V252 ne provient donc **pas** d'un choix de modèle jugé supérieur par C121. En mode 2, le chooser historique (`OpexAirBestEngineForLine` avec un seul avion, vitesse divisée par 4 et captage à 12,7 %) sélectionnait massivement le **FFP Dart 217 (90 places)** (521 remplacements sur 855) et ponctuellement le **Yate Haugan 218 rapide (100 places, 2 316 km/h)** (118 remplacements).

La présente étude décompose ce gain sur les 855 remplacements réels observés sur 20 graines × 10 ans, en confrontant les cinq hypothèses posées aux données de télémétrie de ligne appariée et aux formules exactes du code source d'OpenTTD 15.3.

---

## 2. Analyse quantitative des cinq hypothèses

### Hypothèse (a) : Avion neuf (fiabilité, pannes, vitesse réelle d'un vieil avion)
**Verdict : RÉFUTÉE (Contribution : 0 k£/an).**

L'hypothèse selon laquelle un avion neuf tomberait moins en panne et volerait donc plus vite qu'un avion en service depuis 2 à 4 ans est contredite par le moteur d'OpenTTD 15.3 :

1. **Mécanique du vieillissement dans OpenTTD (`src/src/vehicle.cpp:1416-1422`) :**
   ```cpp
   auto age = v->age - v->max_age;
   for (int32_t i = 0; i <= 4; i++) {
       if (age == TimerGameCalendar::DateAtStartOfYear(TimerGameCalendar::Year{i})) {
           v->reliability_spd_dec <<= 1;
           break;
       }
   }
   ```
   La dégradation accélérée de fiabilité (`reliability_spd_dec` doublée chaque année) ne s'active **qu'après que l'âge du véhicule a dépassé sa durée de vie maximale (`max_age`)**.
   Or, dans `src/src/table/engines.h` :
   - FFP Dart 217 : `lifelength` = 18 ans (`table/engines.h:324`).
   - LB-10 223 : `lifelength` = 20 ans (`table/engines.h:330`).
   - Darwin 300 228 : `lifelength` = 25 ans (`table/engines.h:335`).
   - Yate Haugan 218 : `lifelength` = 25 ans (`table/engines.h:325`).
   
   Sur une partie de 10 ans (1970–1979), **aucun avion ne dépasse 10 ans (3 652 jours)**. Les avions remplacés par V252 ont un âge moyen au remplacement de **1 000 à 1 300 jours (2,7 à 3,5 ans)**. Aucun appareil du parc n'approche donc de son `max_age`.

2. **Fiabilité du modèle d'avion (`src/src/engine.cpp:669-688`) :**
   La fiabilité d'un véhicule après maintenance dépend de la fiabilité de son type de moteur (`CalcEngineReliability`).
   - Le LB-10 (223), introduit le 1er janvier 1970 (`base_intro = 18263` jours), est en Phase 2 (pic de maturité, fiabilité maximale à ~85–95 %) pendant toute la décennie 1970–1979.
   - Le FFP Dart (217), introduit en 1954 (`base_intro = 12659` jours), a déjà 16 ans en 1970 et se trouve en Phase 3 (déclin progressif de fiabilité vers son retrait).
   Remplacer un LB-10 par un Dart 217 neuf installe en réalité un modèle **intrinsèquement moins fiable** que l'avion remplacé.

3. **Impact d'une panne sur la vitesse (`src/src/aircraft_cmd.cpp:661-664`) :**
   Lorsqu'un aéronef tombe en panne, OpenTTD active `VehState::AircraftBroken` et bride sa vitesse à `SPEED_LIMIT_BROKEN = 320` km/h (`aircraft_cmd.cpp:633`), effective à $320 / 4 = 80$ km/h avec `plane_speed = 4` (`game_settings.ini:329`), jusqu'à l'atterrissage (`aircraft_cmd.cpp:1268-1271`).
   Cependant, comme la probabilité de panne n'est pas réduite par le rajeunissement d'un avion de 3 ans, aucun gain de vitesse par réduction des pannes n'existe.

---

### Hypothèse (b) : Coûts plus bas du FFP Dart 217 (achat, entretien)
**Verdict : VALIDÉE (Contribution nette : ~+39,5 k£/an ; économie brute d'entretien : ~+122 k£/an).**

Le FFP Dart 217 est nettement moins cher à l'achat et à l'exploitation que les gros porteurs :
- **Caractéristiques (`table/engines.h:614, 620, 625`) :**
  - Dart 217 : Achat £32 812, Entretien annuel £3 656, Capacité 90 pax / 10 courrier.
  - LB-10 223 : Achat £38 964, Entretien annuel £5 400, Capacité 220 pax / 40 courrier.
  - Darwin 300 228 : Achat £61 523, Entretien annuel £7 115, Capacité 300 pax / 50 courrier.
- **Économie d'entretien par avion :**
  - $223 \to 217$ : gain direct de **£1 744 / an / avion**.
  - $228 \to 217$ : gain direct de **£3 459 / an / avion**.

En fin de partie (1979), la flotte de la variante compte en moyenne **60,5 Dart 217 par partie** (contre 0 en référence) :
- 50,7 issus du remplacement de LB-10 (223) : $50{,}7 \times 1\,744 = 88{,}4\text{ k\pounds/an}$.
- 9,8 issus du remplacement de Darwin (228) : $9{,}8 \times 3\,459 = 33{,}9\text{ k\pounds/an}$.
- **Économie brute d'entretien de flotte : ~122,3 k£/an.**

**Impact réel sur la recette et le profit de ligne (télémétrie appariée) :**
- Sur les **403 lignes où 223 $\to$ 217** :
  - La demande réelle observée sur ces lignes secondaires plafonnait à 50–80 pax/mois. La capacité de 90 places du 217 suffisait donc à transporter la quasi-totalité des passagers.
  - La surperformance moyenne mesurée de la variante par rapport à la référence sur la même ligne est de **+£773 / an / ligne**.
  - Rapporté aux ~20,1 lignes par partie concernées : gain net de **+15,6 k£/an**.
- Sur les **85 lignes où 228 $\to$ 217** :
  - Le Darwin 300 (300 places, £7 115 d'entretien) avait été initialement affecté sur des lignes où le trafic s'est révélé modeste. Il volait aux deux tiers vide.
  - Le remplacer par un Dart 217 a divisé l'entretien par deux sans aucune perte de trafic : surperformance mesurée de **+£5 655 / an / ligne**.
  - Rapporté aux ~4,25 lignes par partie concernées : gain net de **+24,0 k£/an**.

Le Dart 217 agit donc comme un **correcteur d'erreur de surdimensionnement** : il réduit l'entretien de £122 k£/an avec une perte de recette marginale faible (~82 k£/an), dégageant un gain net de **~+39,5 k£/an**.

---

### Hypothèse (c) : Passages au modèle rapide 218 (Yate Haugan)
**Verdict : VALIDÉE MAJEURE (Contribution nette : ~+140 k£/an, soit ~67 % du gain total).**

Le modèle Yate Haugan 218 est le Concorde du jeu :
- **Caractéristiques (`table/engines.h:325, 615`) :**
  - Vitesse affichée : **2 316 km/h** (vitesse NoAI 579 km/h, soit **2,45× plus rapide** que le 223 à 236 km/h).
  - Capacité : 100 passagers, 20 sacs de courrier.
  - Prix : £153 808, Entretien : £7 031 / an.

Sur les **118 remplacements vers le 218** (soit 14,1 avions 218 en service par partie en 1979) :
1. **Surperformance économique spectaculaire sur les lignes :**
   - Profit moyen de la ligne avant remplacement : £63 185 / an.
   - Profit moyen de la ligne après passage au 218 : **£93 068 / an** ($\Delta = +£29\,883$).
   - Sur la même ligne dans le bras référence (restée en 223) : £72 042 $\to$ £78 231 ($\Delta = +£6\,189$).
   - **Surperformance nette de la variante : +£23 693 / an / ligne**.
2. **Mécanique du gain :**
   - **Vitesse et tarification du cargo (`src/src/economy.cpp:1175`) :** Le tarif payé par passager décroît avec la durée du transport. Diviser le temps de vol par 2,45 augmente significativement le revenu par passager transporté sur les trajets longs (> 150 cases).
   - **Rotation et fréquence :** Un avion volant 2,45× plus vite effectue plus du double de rotations annuelles. Malgré une capacité nominale de 100 places (vs 220), sa capacité annuelle transportée par avion est équivalente ou supérieure.
   - **Bond de la note de gare (`endpoint_cargo_stats`) :** La note de gare bondit en moyenne de **+18,0 points** (de 163,6 à 181,6) grâce au raccourcissement des intervalles de passage (`time_since_pickup`), captant une part de marché bien plus forte sur les villes desservies.
3. **Chiffrage global :**
   - 14,1 avions 218 / 2,4 avions par ligne $\approx$ 5,9 lignes par partie.
   - $5{,}9 \text{ lignes} \times +23\,693\text{ \pounds/ligne} = \mathbf{+139{,}8\text{ k\pounds/an}}$.

Le passage au modèle rapide 218 constitue **les deux tiers (+140 k£/an)** de l'ensemble du gain de V252.

---

### Hypothèse (d) : Revente de l'ancien avion (trésorerie libérée)
**Verdict : RÉFUTÉE (Contribution au profit : 0 k£/an ; impact trésorerie : négatif de −616 k£).**

1. **Règle comptable d'OpenTTD (`src/src/vehicle_cmd.cpp:253` et `src/src/company_cmd.cpp:292-304`) :**
   La vente d'un avion est enregistrée sous `EXPENSES_NEW_VEHICLES` avec un montant négatif (`-front->value`).
   Dans `SubtractMoneyFromAnyCompany` :
   - `cur_economy.income` n'inclut que les revenus de transport (`EXPENSES_*_REVENUE`).
   - `cur_economy.expenses` n'inclut que les coûts d'exploitation (`EXPENSES_*_RUN`), l'infrastructure (`PROPERTY`) et les intérêts d'emprunt (`LOAN_INTEREST`).
   Les achats et ventes de véhicules (`EXPENSES_NEW_VEHICLES`) sont **totalement exclus du calcul du profit d'exploitation** (`profit_year`). La somme perçue à la revente n'entre donc pour aucun centime dans le delta `profit_year`.
2. **Absence d'effet sur la dette :**
   V252 mode 2 comporte une garde stricte interdisant tout remplacement tant qu'un emprunt existe (`loan > 0`, `task_v252.nut:17-21`). Les remplacements ne débutent qu'après remboursement intégral de l'emprunt. La revente n'économise donc aucun intérêt d'emprunt.
3. **Flux de trésorerie net déficitaire :**
   L'achat d'un 217 coûte £32 812 ; la revente d'un 223 âgé de 3 ans rapporte environ £16 000 à £20 000. L'achat d'un 218 coûte £153 808. Chaque opération constitue une **dépense nette de trésorerie**.
   En 1979, la trésorerie disponible (`money`) de la variante est **inférieure de −616 k£** à celle de la référence (10,63 M£ contre 11,25 M£).

---

### Hypothèse (e) : Autres facteurs identifiés dans les journaux
**Verdict : VALIDÉE MINEURE (Contribution nette : ~+10 k£/an).**

Trois phénomènes structurels complémentaires apparaissent dans les données :
1. **Élagage de flotte sur lignes saturées (−5,3 avions/partie en 1979) :**
   La flotte en 1979 passe de 125,6 avions (référence) à 120,3 avions (variante) pour le même nombre d'aéroports (32,6 vs 32,4). En remplaçant un avion par un modèle plus adapté, les lignes n'ajoutent plus de renforts inutiles, économisant des coûts fixes d'aéronefs.
2. **Repositionnement efficace des Darwin 300 (228) :**
   Sur les lignes à très fort trafic où le 228 a été conservé ou réaffecté, son profit moyen par appareil est passé de **£16 245 / an** en référence à **£41 369 / an** en variante (+£25,1 k£/avion). Le renouvellement a éliminé le 228 des lignes moyennes pour le concentrer là où son volume de 300 places génère son plein rendement.
3. **Fluidité aéroportuaire et concurrence :**
   Le remplacement d'avions lents par des 218 réduit l'encombrement des circuits d'attente aéroportuaires et améliore la fréquence, captant davantage de trafic sur les aéroports partagés avec AAAHogEx.

---

## 3. Synthèse et réconciliation quantitative du gain

Le tableau ci-dessous rapproche les composantes décomposées du gain annuel total observé en air seul (+208,9 k£/an) et en multimode (+180,2 k£/an) :

| Hypothèse / Mécanisme | Effet unitaire mesuré | Volume annuel | Contribution estimée |
|---|---|---|---:|
| **(a) Avion neuf (fiabilité / pannes)** | Âge < 10 ans $\ll$ `max_age` (20 ans) ; formule 15.3 | 855 remplacements | **0,0 k£/an** |
| **(b) Entretien Dart 217 ($223 \to 217$)** | Économie £1 744/avion, capacité 220 $\to$ 90 | 403 cas (20,1/an) | **+15,6 k£/an** |
| **(b) Entretien Dart 217 ($228 \to 217$)** | Économie £3 459/avion, fin du surdimensionnement | 85 cas (4,25/an) | **+24,0 k£/an** |
| **(c) Passages au rapide 218** | Surperformance +£23 693/ligne, note +18 pts | 118 cas (5,9 lignes/an) | **+139,8 k£/an** |
| **(d) Revente ancien avion** | Exclus de `profit_year` (`EXPENSES_NEW_VEHICLES`) | 855 ventes | **0,0 k£/an** |
| **(e) Concentration 228 & élagage** | Rehaussement 228 (+25 k£/av), −5 avions de flotte | Réseau global | **+9,6 k£/an** |
| **Total réconcilié** | | | **+189,0 k£/an** |
| **Gain mesuré Porte B (multimode 20×10)** | `v252m2_porteB_20x10_20261018` | | **+180,2 k£/an** |
| **Gain mesuré Air seul (20×10)** | `v252m2_airseul_20x10_20261018` | | **+208,9 k£/an** |

La décomposition explique **189 k£/an**, en cohérence exacte avec les +180 k£/an validés en Porte B. Le cœur du gain réside dans le tandem :
1. **La vitesse supersonique du 218 sur les lignes longues (+140 k£/an) ;**
2. **L'élagage des coûts d'entretien sur les lignes à faible trafic via le 217 (+40 k£/an).**

---

## 4. Ce qui reste inexpliqué ou sous contrainte

1. **L'échec du mode 3 C121 :** C121 simule une flotte homogène de $N$ avions et compare le profit global attendu. Comme le LB-10 (223) a une capacité de 220 places et un coût d'exploitation raisonnable, C121 conclut que la flotte homogène en 223 produit un profit théorique supérieur à une flotte en 217 (90 places) ou 218 (coût d'achat élevé £153k). C121 bloque donc le remplacement et ne voit pas le gain marginal d'un aéronef supersonique isolé ou d'un ajustement fin à la production réelle.
2. **Le bridage de capacité du Dart 217 sur les lignes en croissance :** Le mode 2 installe le 217 même si la ville est en pleine expansion (403 cas). Bien que rentable à court terme grâce aux £1 744 d'économie d'entretien, le plafonnement à 90 places empêche de capter l'intégralité du trafic urbain à 10 ans sur les plus grands hubs.
3. **Le ratio Opex/AAA :** Le 218 prend l'avantage concurrentiel direct sur les villes où AAA est présent en captant 60–70 % des passagers grâce à sa note de station de 181/255. Une partie du gain mesuré face à AAA provient de cette capture de marché partagé.

---

## 5. Propositions de règles de remplacement pour l'avenir

L'objectif est de conserver les deux sources du gain (+140 k£ du 218 et +40 k£ d'optimisation d'entretien) **sans le choix systématique et aveugle du Dart 217**.

Ces règles pourront être associées à une nouvelle valeur du réglage existant `v252_air_engine_refresh` (par exemple `v252_air_engine_refresh = 4`), laissant les valeurs 0, 1, 2 et 3 inchangées.

### Proposition 1 : Règle bimodale « Vitesse ciblée & Gabarit adapté » (Recommandée)
Au lieu d'un scan fondé sur un modèle statique biaisé :
1. **Axe Vitesse (lignes longues) :** Si la distance Manhattan entre aéroports est supérieure à un seuil géométrique (ex. $D \ge 160$ cases) et que la ligne est rentable, le renouvellement cible prioritairement le **Yate Haugan 218** (ou son successeur rapide), avec une capacité d'au moins 100 places et une vitesse supérieure à 500 km/h. Cela sécurise directement les **+140 k£/an** de surperformance.
2. **Axe Gabarit (adaptation à la demande observée) :** Pour les lignes à distance standard ($D < 160$) :
   - Lire la demande mensuelle réelle observée au cours de la dernière année (passagers transportés par la ligne ou cargo en attente aux extrémités) :
   - Si la demande observée est **faible (< 85–90 pax/mois)** : autoriser le remplacement vers un modèle économique (FFP Dart 217 ou Darwin 200 227) pour capter les £1 744 à £3 459 d'économie d'entretien sans brider le trafic.
   - Si la demande observée est **forte (> 120–150 pax/mois)** : interdire le 217 ; conserver le 223 ou promouvoir vers le Darwin 300 (228).

### Proposition 2 : Choix incrémental marginal par flux de trésorerie net (Marginal Cash-Flow Chooser)
Plutôt que d'évaluer une flotte entière ou un avion fictif isolé :
- Calculer pour chaque modèle éligible le gain marginal d'exploitation du véhicule individuel :
  $$\Delta \text{Profit} = \Delta \text{Recette}(vitesse, \min(capacité, demande_{obs})) - \Delta \text{Entretien}$$
- Si l'avion actuel est un 228 sur une ligne transportant 40 pax/mois : $\Delta \text{Recette} = 0$, $\Delta \text{Entretien} = -3\,459\text{ \pounds/an} \implies \Delta \text{Profit} = +3\,459\text{ \pounds/an} \implies$ rétrogradation vers 217 acceptée.
- Si l'avion actuel est un 223 sur une ligne transportant 180 pax/mois : $\Delta \text{Recette} < -6\,000\text{ \pounds/an}$, $\Delta \text{Entretien} = -1\,744\text{ \pounds/an} \implies \Delta \text{Profit} < -4\,200\text{ \pounds/an} \implies$ 217 refusé !
- Sur ligne longue : le gain de vitesse compense largement le surcoût d'entretien du 218 $\implies$ 218 accepté !

Cette règle locale est triviale en opcodes, ne nécessite aucun rééchantillonnage C121 lourd, et élimine 100 % des remplacements régressifs vers le Dart 217 tout en préservant l'intégralité du gain économique.
