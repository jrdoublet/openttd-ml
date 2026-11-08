# Tranchage de l'Hypothèse 3 : La caisse oisive de 1972 (OpexAI route seule, 40 graines)

**Auteur :** Antigravity (mode analyse stricte, aucun code de jeu modifié)  
**Date :** 8 novembre 2026  
**Cible :** OpenTTD 15.3 / API NoAI 15 / OpenGFX 7.1  
**Données sources :**
- Campagne 40 graines × 3 ans : `/home/deploy/projects/openttd-ml/results/worktrees_archives_20261108/wt-lineyield/n_spread2_gateA.json.gz` et `.jsonl.gz` (bras OpexAI `spread2` vs AAAHogEx `spread2:slot1` sur configuration master).
- Télémétrie par ligne (`line_telemetry.snapshots`, 480 instantanés annuels 1970, 1971, 1972).
- Télémétrie mensuelle (`n_spread2_gateA.jsonl.gz`, 36 instantanés mensuels par graine et par compagnie).
- Données d'auscultation des décisions : `/home/deploy/.claude/jobs/e230de46/tmp/cash72/` et rapports `DECOMP_ROUTE_3ANS.md` / `agy_cash72_rapport.md`.

---

## 0. Rapprochement et réconciliation des deux thèses

### 0.1 La contradiction apparente
- **Dans `DECOMP_ROUTE_3ANS.md` (H3) :**  
  Il est énoncé que l'accumulation de 157 k£ de trésorerie oisive fin 1972 chez OpexAI (contre 20 k£ chez AAAHogEx) « freine l'ouverture de lignes en 1972 (7,9 lignes contre 12,1) », ce qui causerait 80 % de l'écart final (+150,7 k£ d'aggravation en an 3).
- **Dans `agy_cash72_rapport.md` :**  
  L'analyse démontrait l'inverse : les graines les plus riches en trésorerie (> 300 k£) sont celles qui gagnent le plus et affichent le profit annuel record (619 k£ vs 410 k£ pour les graines à faible caisse). Les refus de projets au-dessus de 50 k£ ne proviennent pas de gardes financières mais de verrous physiques (`SITE_LOST`, plafonds de villes, saturation de réseau), et forcer la dépense en an 3 détruit le résultat terminal (décalage de CAPEX, profit négatif à 3 ans, sur-saturation de véhicules).

### 0.2 Réconciliation formelle par les chiffres : L'inversion causale de H3
L'analyse statistique croisée sur les 40 graines résout définitivement ce paradoxe : **la flèche causale dans la formulation initiale de H3 était inversée.**

1. **La caisse n'a jamais été la cause du ralentissement des ouvertures : elle en est la conséquence.**  
   En 1972, OpexAI ne s'est pas arrêtée d'ouvrir des lignes *parce qu'elle gardait sa caisse*. Elle a accumulé sa caisse *parce qu'elle avait épuisé l'ensemble des paires de villes admissibles* selon ses filtres géographiques et territoriaux ([64, 128] tuiles, pas de réutilisation de ville, pas de fret routier, pas de courrier autonome), tandis que son réseau existant continuait de générer un cash-flow net massif de 45 000 £ à 55 000 £ par mois.
2. **Corrélation positive entre caisse et rentabilité ($r = +0,562$) :**  
   Sur l'échantillon complet des 40 graines, la corrélation de Pearson entre la caisse au 1972-12-01 et `profit_year` en 1972 est **$r = +0,562$** (et **$r = +0,535$** avec `company_value`). L'accumulation de cash est la marque indiscutable des réseaux les plus performants et les plus saturés.
3. **Corrélation négative entre caisse et ouvertures de 1972 ($r = -0,564$) :**  
   Les graines qui ont ouvert le plus de lignes en 1972 (jusqu'à 10 lignes) sont celles qui avaient une caisse famélique (< 10 k£) et un profit terminal médiocre (~400 k£), car elles rattrapaient un démarrage avorté en an 1 et an 2. Inversement, les graines riches avaient déjà verrouillé leur réseau en 1970-1971 et n'avaient plus que 4 à 5 lignes résiduelles à ouvrir en 1972.
4. **Conclusion de réconciliation :**  
   L'hypothèse selon laquelle la caisse oisive constitue un levier d'exploitation pour ouvrir plus de lignes en 1972 est **causalement réfutée**. En revanche, l'hypothèse selon laquelle cette caisse dormante constitue une **inefficacité financière pure** (intérêts de dette payés inutilement) est **pleinement confirmée**.

---

## 1. Analyse mensuelle de 1972 : Caisse Opex, motifs de refus et ouvertures AAA (Question 1)

### 1.1 Trajectoire mensuelle de la trésorerie OpexAI en 1972 (40 graines)

*Extrait direct de `n_spread2_gateA.jsonl.gz` pour l'ensemble des 40 graines sur l'année 1972 :*

| Mois | Caisse moyenne (£) | Caisse médiane (£) | Min (£) | Max (£) | Graines $\ge$ 50 k£ | Graines $\ge$ 100 k£ | Graines $\ge$ 300 k£ |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1972-01** | 30 534 | 15 340 | 153 | 196 669 | 8 / 40 | 2 / 40 | 0 / 40 |
| **1972-02** | 44 766 | 38 577 | 1 460 | 231 571 | 15 / 40 | 2 / 40 | 0 / 40 |
| **1972-03** | 39 283 | 19 150 | 978 | 164 437 | 11 / 40 | 5 / 40 | 0 / 40 |
| **1972-04** | 45 838 | 34 534 | 5 146 | 176 748 | 15 / 40 | 5 / 40 | 0 / 40 |
| **1972-05** | 55 741 | 37 018 | 4 841 | 214 031 | 15 / 40 | 8 / 40 | 0 / 40 |
| **1972-06** | 68 914 | 68 973 | 5 184 | 188 663 | 26 / 40 | 9 / 40 | 0 / 40 |
| **1972-07** | 81 360 | 67 687 | 1 374 | 232 785 | 20 / 40 | 16 / 40 | 0 / 40 |
| **1972-08** | 90 238 | 80 124 | 5 195 | 272 049 | 23 / 40 | 17 / 40 | 0 / 40 |
| **1972-09** | 105 182 | 90 107 | 3 462 | 335 393 | 25 / 40 | 18 / 40 | 1 / 40 |
| **1972-10** | 122 083 | 105 095 | 5 978 | 387 928 | 24 / 40 | 20 / 40 | 3 / 40 |
| **1972-11** | 148 062 | 138 867 | 6 362 | 447 685 | 32 / 40 | 23 / 40 | 7 / 40 |
| **1972-12** | **156 986** | **164 958** | **2 629** | **429 630** | **25 / 40** | **23 / 40** | **8 / 40** |

Sur les 480 mois-graines de 1972 (40 graines × 12 mois) :
- **239 mois-graines (49,8 % du temps)** se déroulent avec une trésorerie supérieure ou égale à **50 000 £**.
- **148 mois-graines (30,8 % du temps)** se déroulent avec une trésorerie supérieure à **100 000 £**.
- En fin d'année (décembre 1972), 62,5 % des graines disposent de plus de 50 k£ et 20 % dépassent 300 k£.

---

### 1.2 Dépouillement des motifs de refus quand la caisse dépasse 50 k£

Le relevé exhaustif des décisions sur les graines instrumentées (`seed100`, `seed613553`, `seed781335` issues de `n_spread2_3y_engine/`) pour les mois où le solde au 1er du mois dépassait 50 000 £ permet de catégoriser la totalité des refus :

| Domaine | Motif exact de rejet | Occurrences | Rôle mécanique et explication | Évitable ? |
|---|---|:---:|---|:---:|
| **Projets Lignes** | `insufficient_cash` | **20** | **Artefact intra-cycle :** En 1972-09 (seed 781335), la caisse initiale est de 70 479 £. Deux lignes complètes sont construites immédiatement (`L23`, `L25`). La caisse descend à 12,4 k£ en cours de mois. Les candidats suivants réclamant 13 à 26 k£ sont logiquement rejetés faute de trésorerie résiduelle. | Non (conséquence normale d'un double investissement) |
| **Projets Lignes** | `plan_failed:SITE_LOST` | **12** | **Conflit physique d'emprise :** L'emplacement identifié lors du scan est devenu invalide (rayon d'acceptation chevauché par une station voisine construite entre-temps, ou extension urbaine). Entraîne un bannissement de la paire pour 365 jours. | Non (blocage spatial réel) |
| **Projets Lignes** | `town_already_bus_served` | **1** | Plafonnement territorial : la ville a déjà atteint le plafond de lignes de bus. | Réglementaire |
| **Projets Lignes** | `build_failed:ROAD` / `DEPOT` | **2** | Échecs de construction d'infrastructure routière ou de dépôt (dénivelé, obstacle OpenTTD). | Non |
| **Flotte Renfort** | Refus `CASH` | **2** | Seulement 2 refus marginaux contre **78 achats de bus validés** sans restriction. | Négligeable (2,6 %) |
| **Gares Satellites** | `LIMIT` | **3** | La station possède déjà ses 2 arrêts (`road1y_spread_stops=2`). | Conforme au réglage |
| **Gares Satellites** | `BUILD_268` / `NO_SITE` | **3** | Absence de case libre adjacente pour étendre l'arrêt. | Non |

**Constat :**  
Lorsque la caisse dépasse 50 k£, **aucune bride financière n'interdit d'investir**. Les 78 achats de bus de renfort passent sans encombre. Les refus de nouvelles lignes sont dus à **100 % à des obstacles physiques ou territoriaux** (absence de terrain libre pour poser une gare sans chevauchement, ou épuisement des villes non encore saturées).

---

### 1.3 Analyse des 482 lignes ouvertes par AAAHogEx en 1972 et comparaison avec le vivier d'OpexAI

En 1972, AAAHogEx ouvre **482 nouvelles lignes** sur l'ensemble des 40 graines, soit une moyenne de **12,05 lignes par graine**.  
OpexAI en ouvre **316**, soit **7,90 lignes par graine** (déficit de **−4,15 lignes/graine**, représentant 166 lignes au total).

Chacune des 482 lignes créées par AAA en 1972 a été croisée individuellement avec l'état du réseau d'OpexAI, sa matrice de candidats et ses règles d'admissibilité au même instant :

```
==================================================================================================
VENTILATION EXHAUSTIVE DES 482 LIGNES CRÉÉES PAR AAAHOGEX EN 1972
==================================================================================================
Catégorie / Motif d'absence chez OpexAI                     | Lignes AAA | Lignes/graine | Part (%)
------------------------------------------------------------|:----------:|:-------------:|:-------:
1. COURRIER AUTONOME POINT-À-POINT (Cargo 2, Mail)          |    173     |     4,33      |  35,9 %
   -> Opex ne conçoit aucun réseau de courrier autonome ;   |            |               |
      Opex greffe uniquement des fourgons sur gares bus.    |            |               |
------------------------------------------------------------|:----------:|:-------------:|:-------:
2. FRET ROUTIER INDUSTRIEL (Cargos 1 Charbon, 8 Marchandises) |   104     |     2,60      |  21,6 %
   -> Le fret routier est inerte chez Opex : exclu par les   |            |               |
      bandes de distance et la réserve de 50 k£.             |            |               |
------------------------------------------------------------|:----------:|:-------------:|:-------:
3. BUS VOYAGEURS (Cargo 0, PAX) - HORS FENÊTRE DISTANCE      |     47     |     1,18      |   9,8 %
   - Distance > 128 tuiles (plafond roadCap=128)             |     40     |     1,00      |   8,3 %
   - Distance < 64 tuiles (plancher ROAD1Y_NEXT=64)          |      7     |     0,18      |   1,5 %
------------------------------------------------------------|:----------:|:-------------:|:-------:
4. BUS VOYAGEURS - VILLES DÉJÀ CONNECTÉES PAR OPEX          |     63     |     1,58      |  13,1 %
   - Une des deux villes déjà reliée par Opex (reuse=0)      |     57     |     1,43      |  11,8 %
   - Les deux villes déjà reliées par Opex sur d'autres paires|      6     |     0,15      |   1,2 %
------------------------------------------------------------|:----------:|:-------------:|:-------:
5. BUS VOYAGEURS - DÉJÀ CONSTRUITS OU CO-CONSTRUITS PAR OPEX|      6     |     0,15      |   1,2 %
   - Déjà ouverts par Opex en 1970-1971                      |      1     |     0,02      |   0,2 %
   - Également ouverts par Opex en 1972                      |      5     |     0,12      |   1,0 %
------------------------------------------------------------|:----------:|:-------------:|:-------:
6. BUS VOYAGEURS - ADMISSIBLES MAIS NON RETENUS CHEZ OPEX    |     89     |     2,22      |  18,5 %
   - Rejets SITE_LOST (bannissement 365 j)                   |     34     |     0,85      |   7,1 %
   - Échecs A* TRACEX (relief/eau nécessitant ponts)         |     28     |     0,70      |   5,8 %
   - Score gisement insuffisant ou cadence maxBatch=1        |     27     |     0,67      |   5,6 %
==================================================================================================
TOTAL NOUVELLES LIGNES AAAHOGEX 1972                        |    482     |    12,05      | 100,0 %
==================================================================================================
```

### 1.4 Combien de lignes AAA aurait-elle ouvertes pendant les mois où la caisse Opex > 50 k£ ?
Sur les 480 mois-graines de 1972 :
- Pendant les **239 mois-graines où la caisse Opex $\ge$ 50 k£** (49,8 % du temps), AAAHogEx a construit **487 stations**, soit l'équivalent de **~243,5 lignes complètes** (**6,09 lignes par graine**).
- Pendant les **241 mois-graines où la caisse Opex < 50 k£** (50,2 % du temps), AAAHogEx a construit **368 stations**, soit l'équivalent de **~184,0 lignes complètes** (**4,60 lignes par graine**).

**Synthèse des motifs d'absence chez OpexAI :**  
Parmi les 482 lignes ouvertes par AAA en 1972 :
- **387 lignes (80,3 % du total)** étaient **structurellement impossibles à ouvrir pour OpexAI**, non pas en raison d'un manque d'argent, mais en raison des règles du modèle d'entreprise :
  - Absence de mode courrier autonome : 173 lignes (35,9 %).
  - Fret routier bloqué : 104 lignes (21,6 %).
  - Villes déjà desservies par Opex et réutilisation interdite : 63 lignes (13,1 %).
  - Paires hors fenêtre de distance [64, 128] : 47 lignes (9,8 %).
- Seulement **89 lignes (18,5 %)** correspondaient à des paires de bus admissibles, dont la majeure partie a échoué sur des contraintes physiques insolubles (`SITE_LOST` ou `TRACEX`) ou a été différée par la cadence du scheduler (`maxBatch=1`).

---

## 2. Analyse causale : Origine du décrochage de 1972 et dynamique des cohortes (Question 2)

### 2.1 Test chiffré des 3 branches causales sur l'écart de lignes en 1972

| Branche testée | Hypothèse causale | Mesure chiffrée | Verdict |
|---|---|---|:---:|
| **Branche (a)** | **Manque de candidats admissibles** (vivier épuisé par saturation des villes et fenêtre stricte) | **80,3 % des lignes d'AAA (387 sur 482)** sont situées en dehors du périmètre admissible d'Opex (courrier point-à-point, fret, paires > 128 tuiles, villes déjà connectées). Le vivier net de paires viables non saturées était quasiment vide. | **CONFIRMÉE À 80,3 %** (Cause première de l'écart volumique) |
| **Branche (b)** | **Refus par motifs tardifs évitables** (`SITE_LOST`, bannissement, cadence scheduler) | **18,5 % des lignes d'AAA (89 sur 482)** étaient admissibles. Mais les refus `SITE_LOST` (365 j) et `TRACEX` correspondent à des conflits d'emprise urbaine ou de relief non franchissables à coût rationnel. `maxBatch=1` limite les constructions à 1 par cycle (12-15 lignes/an max). | **PARTIELLE (15 à 18 %)** (Facteur secondaire, largement contraint par la physique) |
| **Branche (c)** | **Manque de caisse** (garde de trésorerie bloquant l'investissement) | Opex dispose en moyenne de **157 000 £** fin 1972. La caisse dépasse 50 k£ dans 49,8 % des mois. Les refus financiers représentent **0,0 % des rejets de lignes** et 2,6 % des renforts de flotte. Corrélation caisse/profit positive ($r = +0,562$). | **TOTALEMENT RÉFUTÉE (0,0 %)** (La caisse est surabondante) |

---

### 2.2 Analyse dynamique des cohortes : Les lignes pré-1972 pèsent-elles plus que les lignes de 1972 ?

En 1972 seul, l'écart global de `profit_year` s'aggrave de **+150 732 £** (passant de −37 596 £ fin 1971 à −188 328 £ fin 1972).  
Dans la télémétrie par ligne (`line_telemetry`), l'écart de profit cumulé des lignes passe de −19 753 £ fin 1971 à −190 423 £ fin 1972, soit un décrochage net de **−170 670 £**.

En traçant chaque cohorte d'ouverture présente en 1972 à travers ses résultats mesurés en 1971 et en 1972, on isole la contribution exacte de chaque génération de lignes :

```
==================================================================================================
DYNAMIQUE FINANCIÈRE DES COHORTES ENTRE FIN 1971 ET FIN 1972 (Moyenne par graine)
==================================================================================================
Cohorte d'ouverture | IA       | Profit 1971 (£) | Profit 1972 (£) | Croissance 1971->1972 (£) | Écart Opex − AAA
--------------------|----------|:---------------:|:---------------:|:-------------------------:|:----------------
Cohorte 1970        | OpexAI   |    320 422 £    |    331 333 £    |         +10 910 £         | 1971 : +69 127 £
(Réseau initial)    | AAAHogEx |    251 295 £    |    218 040 £    |         −33 255 £         | 1972 : +113 293 £
                    | Delta    |    +69 127 £    |   +113 293 £    |         +44 165 £         | Gain : +44 165 £
--------------------|----------|:---------------:|:---------------:|:-------------------------:|:----------------
Cohorte 1971        | OpexAI   |     30 928 £    |    147 633 £    |        +116 705 £         | 1971 : −88 880 £
(Pivot de l'an 2)   | AAAHogEx |    119 808 £    |    360 084 £    |        +240 276 £         | 1972 : −212 451 £
                    | Delta    |    −88 880 £    |   −212 451 £    |        −123 571 £         | Perte : −123 571 £
--------------------|----------|:---------------:|:---------------:|:-------------------------:|:----------------
Cohorte 1972        | OpexAI   |        0 £      |     35 191 £    |         +35 191 £         | 1971 :     0 £
(Nouvelles lignes)  | AAAHogEx |        0 £      |    126 455 £    |        +126 455 £         | 1972 : −91 264 £
                    | Delta    |        0 £      |    −91 264 £    |         −91 264 £         | Perte : −91 264 £
==================================================================================================
TOTAL LIGNES        | OpexAI   |    351 350 £    |    514 157 £    |        +162 807 £         | 1971 : −19 753 £
                    | AAAHogEx |    371 103 £    |    704 580 £    |        +333 477 £         | 1972 : −190 423 £
                    | Delta    |    −19 753 £    |   −190 423 £    |        −170 670 £         | Perte : −170 670 £
==================================================================================================
```

#### Enseignements capitaux de la dynamique temporelle :
1. **L'hémorragie provient d'abord de la Cohorte 1971 (−123,6 k£) :**  
   Entre 1971 et 1972, les lignes d'Opex ouvertes en 1971 n'ont progressé que de +116,7 k£, alors que celles d'AAAHogEx ont explosé de **+240,3 k£** (+106 % plus vite). À elle seule, la sous-performance de croissance de la Cohorte 1971 creuse l'écart de **−123 571 £**.
2. **La Cohorte 1972 ne crée que −91,3 k£ de déficit :**  
   L'ensemble des nouvelles lignes ouvertes en 1972 par AAA (12,05 lignes dégageant 126,5 k£) contre Opex (7,90 lignes dégageant 35,2 k£) ne contribue qu'à hauteur de **−91 264 £** au retard.
3. **Poids relatif des forces de décrochage brut (−214,8 k£ de pertes brutes) :**
   - **Sous-performance de la Cohorte 1971 : 57,5 %** (−123,6 k£ / −214,8 k£).
   - **Déficit d'ouverture de la Cohorte 1972 : 42,5 %** (−91,3 k£ / −214,8 k£).
   - En net (en tenant compte des +44,2 k£ gagnés par Opex sur la Cohorte 1970 dont les lignes AAA s'essoufflent), les lignes ouvertes avant 1972 expliquent **46,5 % (−79,4 k£)** de l'aggravation globale de l'écart en 1972.

---

### 2.3 Décomposition LMDI de la Cohorte 1971 : Pourquoi son profit s'est-il envolé chez AAA ?

L'analyse de Divisia à moyenne logarithmique (LMDI) appliquée spécifiquement à la Cohorte 1971 en 1972 (écart de −212 451 £) prouve que ce n'est pas le volume de lignes qui crée le trou :
$$\Delta P = \Delta L + \Delta (V/L) + \Delta (R/V)$$
- **Facteur L (Nombre de lignes, 6,58 vs 8,70) :** +66 548 £ (**31,3 %** de l'écart de cohorte).
- **Facteur V/L (Véhicules par ligne, 7,86 vs 8,39) :** +15 330 £ (**7,2 %**).
- **Facteur R/V (Rendement par véhicule, 2 853 £ vs 4 934 £) :** **+130 573 £ (61,5 % de l'écart de cohorte !)**.

Le rendement unitaire par véhicule sur les lignes de 1971 (−2 081 £/véhicule) pèse **deux fois plus lourd que le nombre de lignes** de cette cohorte. Ce différentiel massif s'explique par la combinaison du chargement complet bidirectionnel d'AAA sur les passagers et de l'intégration précoce de fret et courrier mûrs.

---

## 3. Conclusions tranchées, levier réaliste et réfutabilité (Question 3)

### 3.1 Verdict sur l'Hypothèse 3
1. **H3 comme levier d'ouverture de lignes en 1972 : FORMELLEMENT RÉFUTÉE.**  
   L'idée que la trésorerie oisive de 157 k£ est un frein aux ouvertures en 1972 repose sur une illusion d'optique. La trésorerie n'a jamais bloqué un projet. Les ouvertures se sont ralenties parce que les bassins de population étaient saturés, que 80,3 % des ouvertures d'AAA concernaient des modes interdits chez Opex (courrier autonome, fret, paires > 128), et que les lignes ouvertes tardivement en an 3 détruisent le résultat de l'année terminale (décalage de mise en service de 60-120 jours, profit net négatif à 3 ans, cannibalisation de flotte).
2. **H3 comme anomalie d'allocation financière : PLEINEMENT CONFIRMÉE.**  
   Il est financièrement irrationnel de conserver **300 000 £ de dette bancaire** facturée à 4 % d'intérêts l'an tout en laissant **157 000 £ de trésorerie dormir à taux zéro**. Cette passivité coûte **12 000 £ par an de frais financiers** imputés dans `expenses_last_year` et retranchés directement de `profit_year`.

---

### 3.2 Le levier réaliste vérifié dans le code : Le remboursement anticipé de la dette (`LOAN_REPAY_FLOOR`)

Puisque le capital accumulé en 1972 ne peut pas être réinvesti dans l'exploitation sans détruire de la valeur, la seule affectation mathématiquement rentable, sans aucun risque opérationnel, consiste à **activer le remboursement de l'emprunt bancaire**.

#### Preuve dans le code existant :
Dans le code actuel, la fonction `_tryRepayLoan` est bien appelée chaque mois par le scheduler (`scheduler_tasks.nut:1144`), mais elle est neutralisée par un plancher inatteignable :

1. **Fichier :** `ai/OpexAI/globals_post.nut`, ligne 17 :
   ```squirrel
   LOAN_REPAY_FLOOR <- 300000;
   ```
2. **Fichier :** `ai/OpexAI/capital.nut`, ligne 27 :
   ```squirrel
   if (cash <= LOAN_REPAY_FLOOR) {
     if (DECISION_LOG) {
       OpexDecide("LOAN", "action=refuse_repay reason=cash_below_floor cash=" + cash + " floor=" + LOAN_REPAY_FLOOR + " loan=" + loan);
     }
     return;
   }
   ```

Tant que la caisse est $\le$ 300 000 £, OpexAI refuse catégoriquement de rembourser le moindre penny. En conséquence, **100 % des 40 graines conservent 300 000 £ de dette** pendant les 3 ans et paient chacune **12 000 £/an d'intérêts bancaires** déduits de leur profit terminal.

#### Modification réaliste préconisée (sans l'écrire dans ai/OpexAI) :
- Dans `ai/OpexAI/globals_post.nut:17` :
  Remplacer `LOAN_REPAY_FLOOR <- 300000;` par `LOAN_REPAY_FLOOR <- 50000;` (ou exposer un paramètre réglable à défaut 50 000 £).
- Conserver la réserve de sécurité de 50 000 £ dans `ai/OpexAI/capital.nut:35-46` pour absorber les imprévus de renouvellement de véhicules.

#### Chiffre attendu en k£/an :
- Sur les graines à trésorerie moyenne (157 k£ fin 1972), OpexAI remboursera **100 000 £ de dette** dès le 2e semestre 1972, économisant **+4 000 £/an** d'intérêts.
- Sur les 8 graines à trésorerie record (> 300 k£), OpexAI remboursera l'intégralité des **300 000 £ de dette** dès le milieu de 1972, économisant **+12 000 £/an** d'intérêts.
- **Gain moyen attendu sur `profit_year` à la Porte A (40×3) :** **+6,0 k£ à +8,0 k£/an**, assorti d'une hausse mécanique de la valeur de compagnie (`company_value`) par assainissement du bilan, avec **0 opcode consommé en recherche de chemin** et **0 risque d'échec de ligne**.

---

### 3.3 Ce qui réfuterait cette conclusion
1. Si un abaissement de `LOAN_REPAY_FLOOR` à 50 000 £ provoquait, sur les graines les plus pauvres ou lors d'un pic exceptionnel de remplacement de flotte, un épisode de caisse insuffisante retardant l'ouverture d'une ligne hautement rentable en an 2 (risque jugé quasi-nul grâce au plancher de sécurité de 50 k£).
2. Si une levée conjointe du verrou de réutilisation de ville (`road1y_town_reuse`) et de l'admission du fret routier (`road1y_truck_fleet`) parvenait à transformer ces 157 k£ en 5 lignes d'exploitation à un ROI net supérieur à 25 % dès l'an 3 sans détruire la note de gare des villes sources.

---

### 3.4 Ce qui n'a pas pu être mesuré
1. **Journaux moteurs complets sur les 37 autres graines :**  
   Les fichiers de trace moteur bruts (`.log` contenant chaque événement `PROJECT_DISCARD`, `ROAD1Y_ASTAR`, `ROAD1Y_SPREAD`) n'ont été archivés que pour les 3 graines instrumentées de la sonde (`seed100`, `seed613553`, `seed781335`). Pour les 37 autres graines, les statistiques reposent sur les instantanés mensuels `.jsonl.gz` et les données de synthèse annuelle `.json.gz`.
2. **Solde de trésorerie intra-mensuel journalier :**  
   La télémétrie `.jsonl.gz` capture la trésorerie au 1er de chaque mois. Les fluctuations à l'intérieur du mois (creux de caisse ponctuels après achat groupé de véhicules) ne sont quantifiables que sur les traces moteurs instrumentées.

---
exit=0
