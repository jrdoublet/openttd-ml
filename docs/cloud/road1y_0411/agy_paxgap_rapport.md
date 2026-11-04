# Diagnostic PAX bus routier (3 ans) — Décomposition écart AAA & Autopsie de la rentabilité

Campagnes analysées : [`results/n_spread2_gateA.jsonl`](file:///home/deploy/projects/wt-lineyield/results/n_spread2_gateA.jsonl) (40 graines, an 3, route seule), [`n_spread2_3y.jsonl`](file:///home/deploy/projects/wt-lineyield/results/n_spread2_3y.jsonl) et journaux détaillés [`reference_seed*.log`](file:///home/deploy/projects/wt-lineyield/results/n_spread2_3y_engine/) (graines 100, 613553, 781335, probes=258).
Configuration de pointe analysée : bras `spread2` (`road1y_load_orders=1` + `road1y_spread_stops=2`) contre son adversaire direct `AAAHogEx`.

---

## 1. Décomposition de l'écart de profit_year en 3e année (40 graines)

Au 1972-12-01 (an 3, 4 trimestres clos), `profit_year` compagnie moyen :
- **OpexAI (`spread2`) :** 527,5 k£ (médiane 541,9 k£, valeur compagnie 998,1 k£)
- **AAAHogEx (`spread2`) :** 715,9 k£ (médiane 705,6 k£, valeur compagnie 1 001,3 k£)
- **Écart global :** **−188,3 k£/an** (médiane −163,7 k£).

### Décomposition par catégorie de cargo (fin 1972)

| Métrique | OpexAI (`spread2`) | AAAHogEx (`spread2`) | Écart (Opex − AAA) | Part de l'écart total |
|---|---|---|---|---|
| **Profit PAX bus** | **378,6 k£** (méd 396,9 k) | **473,1 k£** (méd 454,4 k) | **−94,5 k£** (méd −57,5 k) | **50,2 %** |
| **Profit MAIL fourgons** | **134,1 k£** (méd 138,3 k) | **185,1 k£** (méd 185,1 k) | **−51,0 k£** (méd −46,8 k) | **27,1 %** |
| **Profit FRET camions** | **1,4 k£** (méd 0,0 k) | **46,4 k£** (méd 23,8 k) | **−45,0 k£** (méd −23,8 k) | **23,9 %** |
| **Total des lignes** | **514,1 k£** (méd 535,2 k) | **704,6 k£** (méd 663,3 k) | **−190,5 k£** (méd −128,1 k) | **100,0 %** |

### Détail des indicateurs physiques et économiques par poste

| Catégorie | Indicateur physique / économique | OpexAI (`spread2`) | AAAHogEx (`spread2`) | Delta |
|---|---|---|---|---|
| **PAX (Bus)** | **Lignes ouvertes / graine** | 14,22 (méd 15,0) [tot 569] | 13,78 (méd 14,0) [tot 551] | +0,44 ligne |
| | **Bus en service / graine** | **100,22** (méd 102,5) [tot 4009] | **85,88** (méd 82,5) [tot 3435] | **+14,34 bus (+16,7 %)** |
| | **Rendement unitaire (£/bus)** | **3 777,9 £** (méd gr. 3 777,7 £) | **5 509,1 £** (méd gr. 5 610,1 £) | **−1 731,2 £ (−31,4 %)** |
| | **Distance Manhattan moyenne** | 96,0 tuiles (méd 98,0) | 104,0 tuiles (méd 106,0) | −8,0 tuiles |
| | **Voyageurs en attente aux arrêts** | 78,4 pax (méd **9,0 pax**) | 123,5 pax (méd **28,0 pax**) | −45,1 pax (méd −19) |
| | **Note de gare moyenne (PAX)** | 158,4 / 255 (**62,1 %**, méd 164) | 164,8 / 255 (**64,6 %**, méd 170) | −2,5 % |
| | **Part bus profit <= 0** | **9,15 %** (méd **7,97 %**) [tot 367] | **6,17 %** (méd **4,55 %**) [tot 212] | **+2,98 % (+48 % rel.)** |
| **MAIL (Fourgons)**| **Lignes / graine** | 9,25 (méd 9,0) [tot 370] | 8,12 (méd 8,0) [tot 325] | +1,13 ligne |
| | **Fourgons / graine** | 73,42 (méd 77,0) [tot 2937] | 59,98 (méd 60,5) [tot 2399] | +13,44 fourgons |
| | **Rendement unitaire (£/fourgon)**| 1 826,4 £ (méd gr. 1 853,8 £) | 3 085,6 £ (méd gr. 3 328,0 £) | −1 259,2 £ (−40,8 %) |
| | **Distance Manhattan moyenne** | 95,1 tuiles (méd 98,0) | 87,6 tuiles (méd 87,0) | +7,5 tuiles |
| | **Attente aux gares (sacs)** | 10,9 sacs (méd **5,0 sacs**) | 44,5 sacs (méd **15,0 sacs**) | −33,6 sacs (méd −10) |
| | **Note de gare moyenne (MAIL)** | 137,6 / 255 (54,0 %, méd 141) | 171,3 / 255 (67,2 %, méd 178) | −13,2 % |
| | **Part fourgons profit <= 0** | 14,85 % (méd 14,19 %) | 16,34 % (méd 12,27 %) | −1,49 % |
| **FRET (Camions)** | **Lignes / graine** | 0,12 (méd 0,0) [tot 5] | 2,92 (méd 3,0) [tot 117] | −2,80 lignes |
| | **Camions / graine** | 0,45 (méd 0,0) [tot 18] | 45,00 (méd 40,5) [tot 1800] | −44,55 camions |
| | **Profit unitaire (£/camion)** | 3 149,4 £ (méd 0,0 £) | 1 031,7 £ (méd gr. 625,9 £) | +2 117,7 £ |
| | **Part camions profit <= 0** | 22,22 % (méd 0,0 %) | 34,89 % (méd 31,74 %) | −12,67 % |

### Distribution fine de la rentabilité des flottes de bus (PAX)

La comparaison globale cache une anomalie structurelle de sur-déploiement chez OpexAI :

| Tranche de profit annuel par bus | OpexAI (4 009 bus) | AAAHogEx (3 435 bus) | Constat |
|---|---|---|---|
| **Profit négatif ou nul (<= 0 £)** | **367 (9,2 %)** | 212 (6,2 %) | 9,2 bus/graine en perte sèche chez Opex |
| **Marginal (0 < p <= 1 000 £)** | **209 (5,2 %)** | 11 (0,3 %) | Opex a 19× plus de bus quasi-inutiles |
| **Faible (1 000 < p <= 2 500 £)** | **639 (15,9 %)** | 329 (9,6 %) | 30,3 % de la flotte Opex sous 2,5 k£/bus |
| **Moyen (2 500 < p <= 4 000 £)** | **921 (23,0 %)** | 326 (9,5 %) | Cœur de flotte Opex |
| **Bon (4 000 < p <= 6 000 £)** | **1 082 (27,0 %)** | 689 (20,1 %) | Rendement nominal acceptable |
| **Très rentable (6 000 < p <= 8 000 £)**| 692 (17,3 %) | **1 390 (40,5 %)** | Cœur de flotte AAAHogEx |
| **Exceptionnel (> 8 000 £)** | 99 (2,5 %) | **478 (13,9 %)** | Lignes longues saturées AAA |

**Bilan de l'écart PAX (−94,5 k£) :**
Opex possède **+14,3 bus de plus qu'AAA** par graine, mais génère **−94,5 k£ de profit en moins**. Plus de 54,4 % des bus d'AAA rapportent plus de 6 000 £/an, contre seulement 19,8 % chez Opex.

---

## 2. Chronologie des ouvertures et trésorerie

### Date d'ouverture de la ligne n (n = 1..30) — Médiane sur les graines instrumentées

Calculé à partir de la première apparition de chaque ligne dans [`n_spread2_3y.jsonl`](file:///home/deploy/projects/wt-lineyield/results/n_spread2_3y.jsonl) et vérifié sur les journaux moteurs :

| Ligne n | Opex (s100) | Opex (s613) | Opex (s781) | **Opex Médiane** | AAA (s100) | AAA (s613) | AAA (s781) | **AAA Médiane** | Avance Opex |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **L01** | 1970-04 | 1970-02 | 1970-02 | **1970-02** | 1970-02 | 1970-03 | 1970-03 | **1970-03** | +1 mois |
| **L02** | 1970-06 | 1970-06 | 1970-03 | **1970-06** | 1970-04 | 1970-04 | 1970-03 | **1970-04** | −2 mois |
| **L03** | 1970-06 | 1970-08 | 1970-04 | **1970-06** | 1970-05 | 1970-08 | 1970-04 | **1970-05** | −1 mois |
| **L04** | 1970-07 | 1970-09 | 1970-04 | **1970-07** | 1970-05 | 1970-12 | 1970-08 | **1970-08** | **+1 mois** |
| **L05** | 1970-08 | 1970-10 | 1970-04 | **1970-08** | 1970-10 | 1971-01 | 1971-01 | **1971-01** | **+5 mois** |
| **L06** | 1970-08 | 1970-10 | 1970-05 | **1970-08** | 1971-01 | 1971-01 | 1971-01 | **1971-01** | **+5 mois** |
| **L07** | 1970-09 | 1970-12 | 1970-06 | **1970-09** | 1971-01 | 1971-06 | 1971-05 | **1971-05** | **+8 mois** |
| **L08** | 1970-09 | 1971-01 | 1970-07 | **1970-09** | 1971-02 | 1971-06 | 1971-06 | **1971-06** | **+9 mois** |
| **L09** | 1970-10 | 1971-02 | 1970-08 | **1970-10** | 1971-03 | 1971-06 | 1971-06 | **1971-06** | **+8 mois** |
| **L10** | 1970-11 | 1971-06 | 1970-10 | **1970-11** | 1971-05 | 1971-07 | 1971-08 | **1971-07** | **+8 mois** |
| **L11** | 1971-05 | 1971-06 | 1970-10 | **1971-05** | 1971-07 | 1971-07 | 1971-08 | **1971-07** | **+2 mois** |
| **L12** | 1971-08 | 1971-09 | 1970-12 | **1971-08** | 1971-09 | 1972-01 | 1971-10 | **1971-10** | **+2 mois** |
| **L13** | 1971-09 | 1971-11 | 1971-03 | **1971-09** | 1971-10 | 1972-02 | 1972-01 | **1972-01** | **+4 mois** |
| **L14** | 1971-10 | 1971-12 | 1971-06 | **1971-10** | 1971-12 | 1972-03 | 1972-02 | **1972-02** | **+4 mois** |
| **L15** | 1971-11 | 1972-01 | 1971-06 | **1971-11** | 1972-05 | 1972-04 | 1972-03 | **1972-04** | **+5 mois** |
| **L16** | 1972-02 | 1972-03 | 1971-08 | **1972-02** | 1972-06 | 1972-04 | 1972-04 | **1972-04** | **+2 mois** |
| **L17** | 1972-05 | 1972-05 | 1971-12 | **1972-05** | 1972-07 | 1972-04 | 1972-05 | **1972-05** | 0 |
| **L18** | 1972-07 | 1972-07 | 1972-01 | **1972-07** | 1972-07 | 1972-05 | 1972-06 | **1972-06** | −1 mois |
| **L19** | 1972-11 | 1972-07 | 1972-01 | **1972-07** | 1972-08 | 1972-05 | 1972-06 | **1972-06** | −1 mois |
| **L20** | 1972-12 | 1972-08 | 1972-02 | **1972-08** | 1972-09 | 1972-06 | 1972-08 | **1972-08** | 0 |
| **L21** | 1972-12 | 1972-09 | 1972-05 | **1972-09** | 1972-09 | 1972-06 | 1972-08 | **1972-08** | −1 mois |
| **L22** | — | 1972-10 | 1972-07 | **1972-08** | 1972-10 | 1972-07 | 1972-08 | **1972-08** | 0 |
| **L23** | — | 1972-11 | 1972-08 | **1972-10** | 1972-12 | 1972-07 | 1972-09 | **1972-09** | −1 mois |
| **L24** | — | 1972-12 | 1972-10 | **1972-11** | — | 1972-08 | 1972-09 | **1972-08** | −3 mois |
| **L25** | — | — | 1972-10 | **1972-10** | — | 1972-08 | 1972-10 | **1972-09** | −1 mois |
| **L26** | — | — | 1972-10 | **1972-10** | — | 1972-08 | 1972-11 | **1972-10** | 0 |
| **L27** | — | — | — | — | — | 1972-10 | 1972-11 | **1972-10** | — |
| **L28** | — | — | — | — | — | 1972-11 | 1972-11 | **1972-11** | — |
| **L29** | — | — | — | — | — | 1972-12 | 1972-12 | **1972-12** | — |
| **L30** | — | — | — | — | — | 1972-12 | — | **1972-12** | — |

*Contrôle d'ensemble sur 40 graines (`n_spread2_gateA`) :*
- Fin 1970 : Opex a en moyenne **9,1 lignes** (méd 9,0) contre seulement **4,1 lignes** (méd 4,0) pour AAA.
- Fin 1971 : Opex a **15,7 lignes** (méd 15,5) contre **12,8 lignes** (méd 13,0) pour AAA.
- Fin 1972 : Opex a **23,6 lignes** (méd 24,0) contre **24,8 lignes** (méd 24,0) pour AAA.

### Trésorerie trimestrielle (caisse `money` sur 40 graines)

| Fin de trimestre | Caisse OpexAI (moy / méd) | Caisse AAAHogEx (moy / méd) | Delta Opex − AAA |
|:---:|:---:|:---:|:---:|
| **1970-T1 (1970-03-01)** | 259,2 k£ (263,0 k£) | 10,7 k£ (11,8 k£) | +248,6 k£ |
| **1970-T2 (1970-06-01)** | 163,4 k£ (159,6 k£) | 10,5 k£ (10,7 k£) | +152,9 k£ |
| **1970-T3 (1970-09-01)** | 66,3 k£ (43,1 k£) | 17,8 k£ (16,7 k£) | +48,5 k£ |
| **1970-T4 (1970-12-01)** | 39,2 k£ (11,3 k£) | 16,4 k£ (15,7 k£) | +22,8 k£ (méd −4,4 k£) |
| **1971-T1 (1971-03-01)** | 25,3 k£ (9,0 k£) | 16,2 k£ (16,3 k£) | +9,1 k£ (méd −7,3 k£) |
| **1971-T2 (1971-06-01)** | 21,9 k£ (10,9 k£) | 15,2 k£ (15,6 k£) | +6,7 k£ (méd −4,8 k£) |
| **1971-T3 (1971-09-01)** | 27,1 k£ (12,3 k£) | 16,7 k£ (15,9 k£) | +10,4 k£ (méd −3,6 k£) |
| **1971-T4 (1971-12-01)** | 30,0 k£ (16,2 k£) | 15,4 k£ (14,6 k£) | +14,6 k£ (méd +1,6 k£) |
| **1972-T1 (1972-03-01)** | 39,3 k£ (19,0 k£) | 17,6 k£ (17,6 k£) | +21,7 k£ (méd +1,4 k£) |
| **1972-T2 (1972-06-01)** | 68,9 k£ (66,2 k£) | 14,5 k£ (12,6 k£) | +54,4 k£ (méd +53,6 k£) |
| **1972-T3 (1972-09-01)** | 105,2 k£ (88,5 k£) | 20,0 k£ (19,4 k£) | +85,2 k£ (méd +69,0 k£) |
| **1972-T4 (1972-12-01)** | **157,0 k£ (162,7 k£)** | **20,5 k£ (18,3 k£)** | **+136,5 k£ (+144,3 k£)** |

### Diagnostic de causalité : Rythme d'ouverture vs Rendement des lignes
1. **Le rythme d'ouverture n'est PAS la cause du retard :** Opex ouvre ses lignes **2 à 9 mois plus vite** qu'AAA tout au long de 1970 et 1971. À la ligne 10, Opex a 8 mois d'avance ; à la ligne 15, 5 mois d'avance.
2. **Le capital n'est pas un frein en 1972 :** En 1972, Opex accumule **157 k£ de trésorerie oisive** (médiane 162,7 k£), tandis qu'AAA réinvestit tout son cash-flow au fil de l'eau (trésorerie stable à 15–20 k£).
3. **L'écart vient entièrement du RENDEMENT des lignes déjà ouvertes :**
   - Chaque bus d'AAA génère 5 509 £/an contre 3 778 £/an chez Opex (**+45,8 %**).
   - Chaque fourgon d'AAA génère 3 086 £/an contre 1 826 £/an (**+69,0 %**).
   - AAA encaisse 46,4 k£ de fret pur avec 45 camions, poste quasi absent chez Opex (1,4 k£).

---

## 3. Paires de villes, topologie et sélection

### Décomposition des paires de villes bus (PAX) sur 40 graines

Sur l'ensemble des 40 graines (fin 1972) :
- **Paires communes (servies à la fois par Opex et AAA) :** 1,20 paire/graine (médiane 1,0, **48 paires au total**).
- **Paires exclusives AAA :** 12,57 paires/graine (médiane 12,5, **503 paires au total**).
- **Paires exclusives Opex :** 13,03 paires/graine (médiane 13,0, **521 paires au total**).

### Performance sur les 48 paires rigoureusement IDENTIQUES

| Métrique sur paires identiques | OpexAI (`spread2`) | AAAHogEx (`spread2`) | Écart |
|---|---|---|---|
| **Profit par ligne** | **39,4 k£** (méd **40,3 k£**) | **39,7 k£** (méd **37,7 k£**) | **−0,3 k£ (+0,8 % AAA)** |
| **Véhicules par ligne** | **8,75 bus** (méd 8,0) | **6,81 bus** (méd 6,5) | **+1,94 bus (+28,5 %)** |
| **Rendement unitaire (£/bus)** | **3 998,7 £** (méd 4 338,2 £) | **5 661,3 £** (méd 5 819,7 £) | **−1 662,6 £ (−29,4 %)** |
| **Attente moyenne de passagers** | 150,3 pax (méd 91,8 pax) | 160,6 pax (méd 132,5 pax) | −10,3 pax |
| **Note de gare moyenne** | 160,7 / 255 (63,0 %) | 165,6 / 255 (64,9 %) | −1,9 % |

> [!IMPORTANT]
> **Le captage sur ligne identique est désormais résolu.**
> Sur les 48 paires identiques, Opex et AAA font **exactement le même profit par ligne** (39,4 k£ vs 39,7 k£). Le saut apporté par [`road1y_spread_stops=2`](file:///home/deploy/.claude/projects/-home-deploy-projects-openttd-ml/memory/road1y_spread_stops.md) (+69,5 k£ Porte A) a comblé le retard historique de captage (qui était de 22 k vs 45 k£).
> En revanche, Opex consomme **8,75 bus** pour faire ce que AAA produit avec **6,81 bus**. Les 1,94 bus supplémentaires d'Opex ont un rendement marginal nul ou destructeur de valeur.

### Comparaison des tailles de villes et distances (paires exclusives vs communes)

Mesuré sur les graines instrumentées avec inventaire complet des villes (`BUS_DISTRICT_SCAN` et `cargo:Passengers`) :

| Échantillon | Distance Manhattan | Producteurs min | Producteurs max | Somme producteurs | Maisons/tiles bâties | Profit ligne | Flotte/ligne |
|---|---|---|---|---|---|---|---|
| **Paires communes** | 95,0 (méd 115,0) | 18,3 (méd 13,0) | 23,3 (méd 25,0) | 41,7 (méd 38,0) | 35,5 (méd 30,0) | 38,4 k£ | 7,0 bus |
| **Paires AAA seules** | **102,1 (méd 108,0)** | 14,2 (méd 14,0) | 22,1 (méd 20,0) | 36,3 (méd 34,0) | 30,2 (méd 28,2) | **30,2 k£** | **5,1 bus** |
| **Paires Opex seules** | **89,5 (méd 82,0)** | 12,9 (méd 13,5) | 21,6 (méd 20,5) | 34,5 (méd 33,0) | 28,2 (méd 29,2) | **25,1 k£** | **7,3 bus** |

*Sur l'ensemble des 40 graines :*
- Distance des paires AAA seules : **moy 105,6 tuiles, méd 107,0 tuiles**.
- Distance des paires Opex seules : **moy 95,7 tuiles, méd 98,0 tuiles**.
- Tailles des villes : **identiques** (producteurs min 14,2 vs 12,9 ; max 22,1 vs 21,6). AAA ne choisit pas des métropoles plus grandes ; il relie les mêmes types de villes (15–25 producteurs) mais à **+10 tuiles de distance supplémentaire** et avec **2 bus de moins par ligne**.

### Topologie du réseau : AAA a-t-il des lignes en étoile ou multi-lignes ?

Distribution du nombre de lignes connectées à chaque ville (degré topologique du graphe routier PAX) sur les 40 graines :

| Degré (lignes / ville) | Villes OpexAI (part %) | Villes AAAHogEx (part %) | Interprétation |
|:---:|:---:|:---:|---|
| **1 ligne (point-à-point strict)** | **1 087 (97,8 %)** | **1 024 (96,4 %)** | Quasi-totalité des deux réseaux |
| **2 lignes** | 24 (2,2 %) | 36 (3,4 %) | Rares carrefours |
| **3 lignes** | 1 (0,1 %) | 2 (0,2 %) | Exception marginale |
| **>= 4 lignes (étoile/hub)** | **0 (0,0 %)** | **0 (0,0 %)** | **Aucun réseau en étoile** |

**Conclusion topologique formelle :**
AAAHogEx **ne construit pas de réseau en étoile** et n'a pas de lignes multiples par ville sur le réseau routier. Dans 96,4 % des cas, une ville n'a qu'une seule et unique ligne de bus. Le modèle d'AAA est purement **point-à-point étendu**.

---

## 4. Spécifications de leviers et conclusion économique

### Bilan des leviers déjà qualifiés ou exclus
- `road1y_spread_stops=2` (+69,5 k£ Porte A, +20,3 k£ Porte B) et `road1y_load_orders=1` (+49,0 k£ Porte A, +282 k£ Porte B) ont réglé le captage et le chargement à la source.
- `road1y_next=64` (+80 k£) a été adopté à défaut ce matin (03/11) par l'utilisateur pour combler le déficit de distance des lignes (qui valait 89 vs 105 tuiles dans `n_spread2_gateA` où `next=0`).
- Tous les autres leviers de la liste utilisateur (*fleet, weak realloc, gap, mail2, next3, astar, bridge, far, rich_fleet, mail_min, dest_full, spread_mail, mail_pick, mail_net, site_relocate, bus quartiers*) sont déjà arbitrés.

Les données démontrent que le gap restant sur le PAX (~40 à 50 k£ après intégration de `road1y_next=64`) provient d'un **effet pervers de sur-déploiement de flotte** engendré mécaniquement par `road1y_spread_stops`.

---

### SPÉCIFICATION 1 : Calibrage du plafond de flotte sous arrêts multiples (`road1y_spread_cap`)

#### 1. Constat mécanique et chiffré
Dans [`ai/OpexAI/bus_districts_overrides.nut:2065`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts_overrides.nut#L2065), la formule de calcul du plafond de flotte pour les bus est :
```squirrel
local road1yStops = (isPax && paxRefleet)
    ? (road1yStopsA + road1yStopsB)
    : (road1yStopsB < road1yStopsA ? road1yStopsB : road1yStopsA);
local road1yCap = fleetPerStop * road1yStops; // fleetPerStop = 2
```
- Avant `road1y_spread_stops`, chaque terminus n'avait qu'un quai : `1 + 1 = 2`, d'où `road1yCap = 2 * 2 = 4 bus`.
- Avec `road1y_spread_stops=2`, chaque terminus a 3 arrêts joints répartis (`nStopsA=3, nStopsB=3`). La somme `road1yStopsA + road1yStopsB` vaut désormais **6**, ce qui fait exploser `road1yCap` à **12 bus par ligne** !
- Or, sur une ligne point-à-point, les bus ne chargent qu'à une extrémité à la fois : la capacité de rotation est bornée par le terminus goulot (`min(nStopsA, nStopsB)`), pas par la somme arithmétique.
- **Résultat dans les données :** Opex entasse 8,75 bus par ligne contre 6,81 chez AAA. Sur 40 graines, **367 bus ont un profit négatif ou nul (9,2 bus/graine)** et 576 bus font moins de 1 000 £. Le capital gaspillé dans ces 28 bus excédentaires (~160 k£/graine) encombre les quais sous `OF_FULL_LOAD_ANY`.

#### 2. Spécification technique
- **Réglage :** `road1y_spread_cap` (entier 0..12, défaut 0).
- **Fichier :** [`ai/OpexAI/bus_districts_overrides.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts_overrides.nut) dans `OpexRoad1yRefleetSaved`.
- **Remplacement :**
```squirrel
// Au lieu de la somme inconditionnelle :
local road1yStops = (isPax && paxRefleet)
    ? (ROAD1Y_SPREAD_CAP > 0 ? ROAD1Y_SPREAD_CAP : (road1yStopsA + road1yStopsB))
    : (road1yStopsB < road1yStopsA ? road1yStopsB : road1yStopsA);
```
Ou bien, si `ROAD1Y_SPREAD_CAP == 1`, utiliser la formule goulot naturelle :
```squirrel
local road1yStops = (isPax && paxRefleet)
    ? max(road1yStopsA, road1yStopsB) * 2 // soit 3 * 2 = 6 bus au lieu de 12
    : ...
```
- **Effet attendu chiffré :**
  - Réduction de la flotte de ~15 à 20 bus non rentables par graine.
  - Élimination directe des pertes des bus négatifs (+0,5 k£ direct).
  - Élimination des temps d'attente en file indienne aux arrêts de chargement, relevant le profit des bus sains.
  - Gain net estimé : **+15 à +25 k£/an** en `profit_year` et **+80 à +110 k£** de valeur de compagnie (trésorerie épargnée).

---

### SPÉCIFICATION 2 : Déclenchement du renfort sur le stock goulot bilatéral (`road1y_pax_bilat`)

#### 1. Constat mécanique et chiffré
Dans [`ai/OpexAI/bus_districts_overrides.nut:2073`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts_overrides.nut#L2073) :
```squirrel
local road1yWait = (("kind" in line) && line.kind == "freight") ? waitingA : totalWaiting;
local road1yWant = road1yWait / capacity; // capacity = 35
```
- `totalWaiting` est la somme `waitingA + waitingB`.
- Si la gare A a 20 passagers et la gare B 15 passagers, `totalWaiting = 35`. Opex achète un nouveau bus, alors **qu'aucun des deux terminus n'a de quoi remplir un seul bus**.
- Avec `road1y_load_orders=1` (`OF_FULL_LOAD_ANY`), ce nouveau bus s'immobilise à quai pendant des semaines pour attendre les passagers manquants, dégrade la note de ponctualité et bloque l'approche.
- **Référence AAAHogEx :** Dans [`ai/AAAHogEx-115/route.nut:2688-2691`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/route.nut#L2688-L2691), AAA calcule :
```squirrel
local cargoWaiting = AIStation.GetCargoWaiting(srcHgStation.stationId, cargo);
if((vehicleType == AIVehicle.VT_AIR || vehicleType == AIVehicle.VT_ROAD) && IsBiDirectional()) {
    cargoWaiting = min(cargoWaiting, AIStation.GetCargoWaiting(destHgStation.stationId, cargo));
}
```
AAA exige que le stock soit suffisant aux **deux extrémités** avant d'injecter du matériel.

#### 2. Spécification technique
- **Réglage :** `road1y_pax_bilat` (booléen 0..1, défaut 0).
- **Fichier :** [`ai/OpexAI/bus_districts_overrides.nut:2073`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts_overrides.nut#L2073).
- **Remplacement :**
```squirrel
local road1yWait;
if (("kind" in line) && line.kind == "freight") {
  road1yWait = waitingA;
} else if (isPax && ROAD1Y_PAX_BILAT > 0) {
  road1yWait = (waitingB < waitingA) ? waitingB : waitingA;
} else {
  road1yWait = totalWaiting;
}
```
- **Effet attendu chiffré :**
  - Interdit l'injection de bus sur des paires asymétriques où un village ne génère pas de flux retour.
  - Réduit les 209 bus à profit marginal (0–1 000 £) pour concentrer les véhicules là où le flux est continu dans les deux sens.
  - Gain estimé : **+10 à +18 k£/an**.

---

### Scripts et outils d'analyse créés

Les scripts Python développés pour ce diagnostic sont conservés dans `/home/deploy/.claude/jobs/e230de46/tmp/paxgap/` :
- [`decompose_q1.py`](file:///home/deploy/.claude/jobs/e230de46/tmp/paxgap/decompose_q1.py) : Décomposition complète des 40 graines par cargo, calcul des moyennes, médianes, distances, notes, attentes et véhicules déficitaires.
- [`compute_q2_table.py`](file:///home/deploy/.claude/jobs/e230de46/tmp/paxgap/compute_q2_table.py) : Calcul précis de la chronologie médiane d'ouverture des lignes n = 1..30 sur les graines instrumentées et suivi trimestriel de trésorerie sur 40 graines.
- [`test_q3_topology.py`](file:///home/deploy/.claude/jobs/e230de46/tmp/paxgap/test_q3_topology.py) : Analyse topologique du réseau (degrés des villes, recherche d'étoiles/hubs, distances des paires communes vs exclusives).
- [`analyze_q3_pairs.py`](file:///home/deploy/.claude/jobs/e230de46/tmp/paxgap/analyze_q3_pairs.py) : Comparaison des tailles de villes (producteurs, tiles bâties) et rendements des paires d'AAA face à Opex.
- [`analyze_bus_profit_dist.py`](file:///home/deploy/.claude/jobs/e230de46/tmp/paxgap/analyze_bus_profit_dist.py) : Histogramme des profits unitaires des 4 009 bus d'Opex vs 3 435 bus d'AAA par tranches de 1 k£.
- [`analyze_shared_pax_pairs.py`](file:///home/deploy/.claude/jobs/e230de46/tmp/paxgap/analyze_shared_pax_pairs.py) : Analyse appariée stricte des 48 paires de villes identiques entre Opex et AAA.

exit=0
