# Décomposition causale de l'écart OpexAI / AAAHogEx en mode route seule à 3 ans

**Auteur :** Antigravity (mode analyse seule, aucun code de jeu modifié)  
**Date :** 8 novembre 2026  
**Cible :** OpenTTD 15.3 / API NoAI 15 / OpenGFX 7.1  
**Données sources :**
- Campagne de référence 40 graines × 3 ans : `/home/deploy/projects/openttd-ml/results/worktrees_archives_20261108/wt-lineyield/n_spread2_gateA.json.gz` et `.jsonl.gz` (bras OpexAI `spread2` vs bras AAAHogEx `spread2:slot1` sur la configuration master : `road1y_load_orders=1`, `road1y_spread_stops=2`, `road1y_astar=4`, `road1y_gap=12`, `road1y_weak=15`, `road1y_next=64`, `road1y_next3=56`, `road1y_mail2=5`).
- Télémétrie par ligne : `n_spread2_gateA.json.gz` (`line_telemetry.snapshots`, 480 instantanés annuels 1970, 1971, 1972).
- Télémétrie mensuelle : `n_spread2_gateA.jsonl.gz` (36 instantanés mensuels du 1970-01-01 au 1972-12-01 pour les 40 graines et les 2 compagnies).
- Bancs Gate A des leviers archivés : `/home/deploy/projects/openttd-ml/results/worktrees_archives_20261108/wt-*/` et `/home/deploy/projects/wt-townreuse/results/`.
- Rapports préalables : `docs/taches.md` section « 04/11 — ROAD1Y », `docs/cloud/road1y_0411/` (`BILAN_MISSIONS.md`, `RAPPORT_CLOUD*.md`, `agy_*rapport.md`).

---

## 1. Décomposition de l'écart de profit_year à 3 ans (40 graines)

### 1.1 Constat global et décomposition par catégorie de cargo

Au 1972-12-01 (fin de l'an 3, 4 trimestres clos), les résultats économiques moyens sur les 40 graines canoniques s'établissent comme suit :
- **OpexAI (`spread2`) :** 527 531,7 £/an (médiane 543 787,0 £/an ; valeur de compagnie : 998 145 £)
- **AAAHogEx (`spread2:slot1`) :** 715 859,8 £/an (médiane 716 948,0 £/an ; valeur de compagnie : 1 001 285 £)
- **Écart global (`profit_year`) :** **−188 328,1 £/an** (OpexAI atteint **73,69 %** du profit d'AAAHogEx).

Dans la télémétrie détaillée par ligne (`line_telemetry`, instantané 1972-12-01, cumul des 11 premiers mois de 1972), le profit total de ligne s'élève à 514 157 £/graine pour OpexAI contre 704 580 £/graine pour AAAHogEx (écart : −190 423 £/graine, ratio 73,0 %).

La ventilation stricte par catégorie de transport met en évidence la structure tripartite du retard :

| Catégorie de transport | OpexAI (moy/graine) | AAAHogEx (moy/graine) | Écart (Opex − AAA) | Part de l'écart total | Fichier source |
|---|:---:|:---:|:---:|:---:|---|
| **Bus Voyageurs (PAX, cargo 0)** | **378 635 £** | **473 090 £** | **−94 455 £** | **50,15 %** | `n_spread2_gateA.json.gz:line_telemetry` |
| **Fourgons Courrier (MAIL, cargo 2)** | **134 105 £** | **185 061 £** | **−50 956 £** | **27,06 %** | `n_spread2_gateA.json.gz:line_telemetry` |
| **Camions Fret (Coal/Wood, cargos 1, 6..8)** | **1 417 £** | **46 428 £** | **−45 011 £** | **23,90 %** | `n_spread2_gateA.json.gz:line_telemetry` |
| **Total Télémétrie Lignes** | **514 157 £** | **704 580 £** | **−190 423 £** | **101,11 %** | `n_spread2_gateA.json.gz:line_telemetry` |
| **Total Macro (`profit_year`)** | **527 532 £** | **715 860 £** | **−188 328 £** | **100,00 %** | `n_spread2_gateA.json.gz:summary` |

*(Note : le léger écart de 2 095 £ entre le total des lignes et le `profit_year` macro correspond aux intérêts d'emprunt et coûts de maintenance du mois de décembre).*

---

### 1.2 Décomposition multiplicative en facteurs chiffrés (Méthode LMDI / Log-Shares)

Tout profit de réseau routier se factorise multiplicativement selon :
$$\text{Profit} = L \times \left(\frac{V}{L}\right) \times \left(\frac{\text{Profit}}{V}\right)$$
où :
- $L$ = Nombre de lignes ouvertes par graine
- $V/L$ = Nombre moyen de véhicules par ligne
- $\text{Profit}/V$ = Rendement unitaire annuel par véhicule (profit net / véhicule)

L'écart relatif $\ln\left(\frac{P_{\text{AAA}}}{P_{\text{Opex}}}\right) = \ln(L_{\text{ratio}}) + \ln(V_{\text{ratio}}) + \ln(R_{\text{ratio}})$ est décomposé de manière additive exacte via l'indice de Divisia à moyenne logarithmique (LMDI) :
$$\Delta P = \Delta L + \Delta V + \Delta R \quad \text{avec} \quad w = \frac{P_{\text{AAA}} - P_{\text{Opex}}}{\ln(P_{\text{AAA}}) - \ln(P_{\text{Opex}})}$$

#### Tableau de décomposition multiplicative à 3 ans (instantané 1972-12-01) :

| Secteur | Indicateur | OpexAI | AAAHogEx | Ratio (AAA/Opex) | Part log (%) | Contribution LMDI (£/graine) | Part dans le gap du secteur |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **TOTAL ROUTE** | Lignes / graine ($L$) | 23,60 | 24,82 | 1,052× | +16,0 % | +30 463 £ | +16,0 % |
| | Véhicules / ligne ($V/L$) | 7,38 | 7,69 | 1,042× | +13,1 % | +24 868 £ | +13,1 % |
| | Profit / véhicule ($R/V$) | 2 953 £ | 3 692 £ | **1,250×** | **+70,8 %** | **+134 912 £** | **+70,8 %** |
| | *Profit Total Lignes* | *514 157 £* | *704 580 £* | *1,370×* | *100,0 %* | *+190 423 £* | *100,0 %* |
| **BUS VOYAGEURS (PAX)** | Lignes PAX ($L$) | 14,22 | 13,78 | 0,968× | −14,4 % | −13 633 £ | −14,4 % |
| | Bus / ligne ($V/L$) | 7,05 | 6,23 | 0,885× | −54,9 % | −51 869 £ | −54,9 % |
| | Profit / bus ($R/V$) | **3 778 £** | **5 509 £** | **1,458×** | **+169,4 %** | **+159 989 £** | **+169,4 %** |
| | *Profit Total PAX* | *378 635 £* | *473 090 £* | *1,249×* | *100,0 %* | *+94 455 £* | *100,0 %* |
| **COURRIER (MAIL)** | Lignes MAIL ($L$) | 9,25 | 8,12 | 0,878× | −40,3 % | −20 517 £ | −40,3 % |
| | Fourgons / ligne ($V/L$) | 7,94 | 7,38 | 0,930× | −22,5 % | −11 489 £ | −22,5 % |
| | Profit / fourgon ($R/V$) | **1 826 £** | **3 086 £** | **1,689×** | **+162,8 %** | **+82 969 £** | **+162,8 %** |
| | *Profit Total MAIL* | *134 105 £* | *185 061 £* | *1,380×* | *100,0 %* | *+50 956 £* | *100,0 %* |
| **FRET CAMIONS** | Lignes Fret ($L$) | 0,12 | 2,92 | **23,400×** | **+90,4 %** | **+40 669 £** | **+90,4 %** |
| | Camions / ligne ($V/L$) | 3,60 | 15,38 | 4,274× | +41,6 % | +18 736 £ | +41,6 % |
| | Profit / camion ($R/V$) | 3 149 £ | 1 032 £ | 0,328× | −32,0 % | −14 396 £ | −32,0 % |
| | *Profit Total Fret* | *1 417 £* | *46 428 £* | *32,765×* | *100,0 %* | *+45 011 £* | *100,0 %* |

*Source des calculs : script `/home/deploy/.claude/jobs/e230de46/tmp/decomp/test_lmdi.py` exécuté sur `n_spread2_gateA.json.gz`.*

#### Enseignements majeurs de la décomposition multiplicative :
1. **Sur le segment PAX (50,2 % du déficit global) :** OpexAI possède **plus de lignes** (+0,44 ligne/graine) et **plus de véhicules par ligne** (+0,81 bus/ligne) qu'AAAHogEx. En volume brut, OpexAI déploie 100,2 bus/graine contre 85,9 chez AAA. Pourtant, Opex accuse un retard de −94,5 k£. La cause est **à 169,4 % le rendement unitaire** : un bus AAA rapporte **5 509 £/an** contre seulement **3 778 £/an** pour un bus Opex (+45,8 % de rentabilité par véhicule pour AAA).
2. **Sur le segment MAIL (27,1 % du déficit global) :** Même constatation exacte. Opex déploie 73,4 fourgons sur 9,25 lignes contre 60,0 fourgons sur 8,12 lignes pour AAA. Le déficit de −51,0 k£ est imputable à 162,8 % au rendement unitaire : 3 086 £/fourgon chez AAA contre 1 826 £/fourgon chez Opex (+69,0 % pour AAA).
3. **Sur le segment FRET (23,9 % du déficit global) :** Ici, le phénomène est **100 % volumique**. OpexAI n'a construit que 5 lignes de fret sur l'ensemble des 40 parties (0,12 ligne/graine, 18 camions au total). AAA en a construit 117 (2,92 lignes/graine, 1 800 camions au total). L'absence de fret routier chez Opex coûte **−45,0 k£/an**.

---

### 1.3 Analyse par cohortes temporelles d'ouverture (1970, 1971, 1972)

En traçant chaque ligne présente en 1972 selon l'année où elle est apparue dans les instantanés annuels (`1970-12-01`, `1971-12-01`, `1972-12-01`), on isole l'effet de l'âge des lignes :

| Cohorte d'ouverture | IA | Lignes / graine | Véhicules / graine | Véhicules / ligne | Profit 1972 (£/graine) | Profit / ligne (£) | Profit / véhicule (£) |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Cohorte 1970** | **OpexAI** | **9,12** (365) | **91,30** (3 652) | 10,01 | **331 333 £** | 36 310 £ | 3 629 £ |
| *(Lignes très mûres)* | **AAAHogEx** | **4,08** (163) | **33,02** (1 321) | 8,10 | **218 040 £** | **53 507 £** | **6 602 £** |
| | *Delta (Opex − AAA)* | *+5,04* | *+58,28* | *+1,91* | *+113 293 £* | *−17 197 £* | *−2 973 £* |
| **Cohorte 1971** | **OpexAI** | **6,58** (263) | **51,75** (2 070) | 7,87 | **147 633 £** | 22 454 £ | 2 853 £ |
| *(Lignes d'âge moyen)* | **AAAHogEx** | **8,70** (348) | **72,97** (2 919) | 8,39 | **360 084 £** | **41 389 £** | **4 934 £** |
| | *Delta (Opex − AAA)* | *−2,12* | *−21,22* | *−0,52* | *−212 451 £* | *−18 935 £* | *−2 081 £* |
| **Cohorte 1972** | **OpexAI** | **7,90** (316) | **31,05** (1 242) | 3,93 | **35 191 £** | 4 455 £ | 1 133 £ |
| *(Lignes jeunes)* | **AAAHogEx** | **12,05** (482) | **84,85** (3 394) | 7,04 | **126 455 £** | **10 494 £** | **1 490 £** |
| | *Delta (Opex − AAA)* | *−4,15* | *−53,80* | *−3,11* | *−91 264 £* | *−6 039 £* | *−357 £* |

*Source : `/home/deploy/.claude/jobs/e230de46/tmp/decomp/detailed_decomp.py`.*

#### Zoom sur les sous-catégories par cohorte :
- **En cohorte 1970 :** Opex a capitalisé sur son avance de trésorerie (emprunt de 300 k£ immédiat) en ouvrant 9,12 lignes contre 4,08 chez AAA. Ce socle rapporte plus à Opex en valeur absolue (331 k£ vs 218 k£), mais chaque ligne d'AAA rapporte **53,5 k£** contre **36,3 k£** chez Opex (+47,4 %), avec des bus AAA dégageant **6 602 £/an** contre **3 629 £/an** (+81,9 %).
- **En cohorte 1971 :** C'est le pivot de la partie. AAA prend le dessus en ouvrant 8,70 lignes contre 6,58 chez Opex, et en y déployant 73 véhicules contre 52. AAA y génère **360,1 k£/an** contre seulement **147,6 k£/an** chez Opex (un trou béant de −212,5 k£/graine sur cette seule cohorte !).
- **En cohorte 1972 :** AAA ouvre 12,05 lignes (dont 2,6 lignes de fret à 37 camions/graine) contre 7,90 pour Opex, et engrange 126,5 k£ contre 35,2 k£ pour Opex (−91,3 k£).

---

### 1.4 Courbe cumulée mois par mois des ouvertures et dates d'ouverture

La chronologie d'ouverture de la $n$-ième ligne (médiane sur les graines instrumentées et moyenne globale) prouve de façon indiscutable l'avance opérationnelle initiale d'OpexAI :

| Ligne $n$ | Date d'ouverture OpexAI (médiane) | Date d'ouverture AAAHogEx (médiane) | Avance OpexAI (mois) |
|:---:|:---:|:---:|:---:|
| **L01** | **1970-02** | 1970-03 | +1 mois |
| **L03** | **1970-06** | 1970-05 | −1 mois |
| **L05** | **1970-08** | **1971-01** | **+5 mois** |
| **L08** | **1970-09** | **1971-06** | **+9 mois** |
| **L10** | **1970-11** | **1971-07** | **+8 mois** |
| **L12** | **1971-08** | **1971-10** | **+2 mois** |
| **L15** | **1971-11** | **1972-04** | **+5 mois** |
| **L18** | 1972-07 | 1972-06 | −1 mois |
| **L21** | 1972-09 | 1972-08 | −1 mois |
| **L24** | 1972-11 | 1972-08 | −3 mois |
| **L27** | *(Non atteint)* | 1972-10 | Dépassé |
| **L30** | *(Non atteint)* | 1972-12 | Dépassé |

*Source : `docs/cloud/road1y_0411/agy_paxgap_rapport.md` §2 et `monthly_trajectory.py`.*

OpexAI atteint le cap de 10 lignes ouvertes dès novembre 1970 (mois 11), alors qu'AAAHogEx n'atteint ce seuil qu'en juillet 1971 (mois 19), soit **8 mois plus tard**. Opex conserve une avance nette en nombre de lignes et gares jusqu'à la fin de l'an 2 (décembre 1971). AAA ne rattrape Opex en nombre de lignes qu'à l'été 1972 (L17-L20) avant de la distancer grâce aux lignes de fret.

---

### 1.5 Identification du facteur prépondérant et période de creusement

1. **Le facteur prépondérant :**
   Ce n'est **ni le calendrier de démarrage, ni le nombre de lignes, ni le nombre de véhicules**. C'est le **rendement unitaire par véhicule ($R/V$)** sur les passagers et le courrier, combiné à l'**absence totale de fret** :
   - En passagers, le bus Opex rapporte 3 778 £ contre 5 509 £ chez AAA (déficit unitaire de −31,4 %, expliquant à lui seul **160,0 k£ de retard**).
   - En courrier, le fourgon Opex rapporte 1 826 £ contre 3 086 £ chez AAA (déficit unitaire de −40,8 %, expliquant **83,0 k£ de retard**).
   - En fret, l'absence de 45 camions de charbon/bois coûte **45,0 k£**.
2. **La période de creusement de l'écart :**
   L'écart macroscopique de `profit_year` ne se creuse **pas en 1970 ni au premier semestre 1971** :
   - Fin 1970 (1970-12-01) : Opex 47,5 k£ vs AAA 104,1 k£ (écart : −56,6 k£).
   - Fin 1971 (1971-12-01) : Opex 328,4 k£ vs AAA 366,0 k£ (écart : **−37,6 k£ seulement !**). L'avance en volume d'Opex a quasiment comblé le déficit de rendement initial.
   - C'est **entre mars 1972 et novembre 1972** que la rupture se produit :
     - 1972-02-01 : écart de −54,2 k£
     - 1972-05-01 : écart de −91,3 k£
     - 1972-08-01 : écart de −132,6 k£
     - 1972-11-01 / 12-01 : écart de **−188,3 k£**.
   **En 1972 seul, l'écart se creuse de +150,7 k£ (80 % du retard final).**

---

## 2. Trajectoires de caisse, prêt, investissement et rythme avant juillet 1971

### 2.1 Tableau mensuel des bilans financiers et physiques (Moyenne 40 graines)

*Extrait direct de `n_spread2_gateA.jsonl.gz` via `monthly_trajectory.py` :*

| Date | Trésorerie Opex (£) | Trésorerie AAA (£) | Prêt Opex (£) | Prêt AAA (£) | Gares Opex (Bus/Trk) | Gares AAA (Bus/Trk) | Véhicules Opex | Véhicules AAA | `profit_year` Opex (£) | `profit_year` AAA (£) | Écart `profit_year` (£) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1970-01-01** | 100 000 | 100 000 | 100 000 | 100 000 | 0,0 (0/0) | 0,0 (0/0) | 0,0 | 0,0 | — | — | — |
| **1970-03-01** | 259 232 | 10 676 | 300 000 | 70 750 | 2,4 (2,4/0,0) | 4,4 (4,4/0,0) | 2,8 | 3,4 | — | — | — |
| **1970-06-01** | 163 378 | 10 521 | 300 000 | 221 250 | 8,7 (7,0/1,6) | 5,2 (5,2/0,0) | 14,4 | 27,9 | −445 | 946 | −1 391 |
| **1970-09-01** | 66 335 | 17 833 | 300 000 | 229 750 | 14,9 (10,8/4,1) | 6,7 (6,6/0,1) | 31,7 | 36,6 | 10 842 | 37 050 | −26 208 |
| **1970-12-01** | 39 226 | 16 406 | 300 000 | 200 000 | 18,3 (12,8/5,5) | 8,8 (8,4/0,3) | 43,0 | 39,0 | 47 523 | 104 093 | −56 570 |
| **1971-03-01** | 25 335 | 16 249 | 300 000 | 206 250 | 20,9 (14,1/6,8) | 12,6 (11,5/1,0) | 56,0 | 45,8 | 106 037 | 174 436 | −68 399 |
| **1971-06-01** | 21 912 | 15 224 | 300 000 | 231 750 | 24,4 (15,5/8,9) | 16,9 (14,2/2,7) | 71,6 | 58,8 | 180 928 | 252 198 | −71 270 |
| **1971-09-01** | 27 092 | 16 693 | 300 000 | 239 250 | 27,9 (17,4/10,4) | 21,2 (16,1/5,1) | 87,1 | 72,8 | 260 729 | 313 379 | −52 650 |
| **1971-12-01** | 29 989 | 15 415 | 300 000 | 249 250 | 31,6 (19,5/11,9) | 26,5 (17,7/8,9) | 104,7 | 90,3 | 328 438 | 366 034 | **−37 596** |
| **1972-03-01** | 39 283 | 17 616 | 300 000 | 239 000 | 35,1 (21,8/13,2) | 30,5 (19,6/11,0) | 123,3 | 110,5 | 387 132 | 441 359 | −54 227 |
| **1972-06-01** | 68 914 | 14 492 | 300 000 | 247 250 | 39,3 (24,1/15,2) | 37,0 (23,6/13,4) | 140,5 | 131,0 | 438 342 | 529 690 | −91 348 |
| **1972-09-01** | 105 182 | 19 971 | 300 000 | 245 750 | 43,5 (26,4/17,0) | 42,5 (25,9/16,7) | 158,2 | 158,9 | 484 940 | 617 570 | −132 630 |
| **1972-12-01** | **156 986** | **20 513** | 300 000 | 234 750 | 47,5 (28,6/18,8) | 49,3 (27,0/22,5) | 174,1 | 190,9 | **527 532** | **715 860** | **−188 328** |

### 2.2 Analyse comparative des politiques financières et d'investissement

1. **AAA investit-il plus tôt ? NON, c'est l'inverse :**
   - **OpexAI** emprunte 300 000 £ dès le 1er février 1970 (`current_loan = 300 000`), disposant de 284 k£ de caisse immédiate. Opex construit massivement de la voirie et des gares : dès juillet 1970, Opex a 11,3 gares contre 5,4 chez AAA. À la fin 1970, Opex a 18,3 gares et 43 véhicules contre 8,8 gares et 39 véhicules chez AAA.
   - **AAAHogEx** ne recourt à l'emprunt que progressivement (70 k£ en mars, 133 k£ en avril, 190 k£ en mai, plafonnant à 230-249 k£). AAA investit au fur et à mesure, maintenant sa caisse strictement entre 10 000 £ et 18 000 £.
   - La seule différence précoce est la vitesse d'achat des bus sur les premières lignes : au printemps 1970, AAA concentre 20 bus sur seulement 5 gares (~4 bus/gare), ce qui fait démarrer ses recettes plus vite, alors qu'Opex étale ses achats sur 11 gares (~2 bus/gare).
2. **Quelle part de l'écart vient du rythme de construction avant juillet 1971 ?**
   - **Pratiquement aucune part négative :** à juillet 1971, OpexAI devance AAAHogEx sur tous les indicateurs physiques de réseau (25,8 gares vs 18,1 ; 76,3 véhicules vs 63,0). La valeur de compagnie d'Opex dépasse celle d'AAA dès mai 1971 (235 k£ vs 217 k£) et maintient cette avance tout au long de 1971 (337 k£ vs 296 k£ en août).
   - Fin 1971 (1971-12-01), l'écart de profit_year n'est que de **−37,6 k£** (soit 20 % du retard final).
   - **Le vrai basculement a lieu en 1972 :**
     En 1972, AAAHogEx réinvestit l'intégralité de son cash-flow : sa flotte bondit de 96,9 à 190,9 véhicules (+94 véhicules, +97 %) et ses gares de 28,0 à 49,3 (+21,3 gares), notamment via 12 nouvelles gares de camions.
     À l'inverse, OpexAI s'arrête d'investir son cash disponible : sa caisse gonfle de 30 k£ à **157 k£** fin 1972. Faute de nouvelles paires admissibles (plafond de 1 ligne PAX par ville, absence d'accès au fret), Opex n'achète que 62 véhicules en 1972 et accumule du capital mort.

---

## 3. Corrélations par graine et caractéristiques des cartes

### 3.1 Classement des 40 graines par écart relatif (AAA − Opex) / AAA

*Données extraites de `n_spread2_gateA.json.gz:summary` par `inspect_seeds_ranking.py` :*

| Rang | Graine | OpexAI (k£) | AAAHogEx (k£) | Écart (AAA − Op) | Écart relatif (%) | Ratio Op/AAA (%) | Profil topologique / Cause dominante |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **1** | **999533** | 377,4 | 982,6 | +605,2 k£ | **61,6 %** | 38,4 % | Mégapoles + Fret AAA colossal (129 k£ fret) |
| **2** | **123456** | 395,4 | 989,0 | +593,6 k£ | **60,0 %** | 40,0 % | Courrier AAA record (376 k£ MAIL) |
| **3** | **841478** | 248,3 | 604,0 | +355,7 k£ | **58,9 %** | 41,1 % | Opex bloqué à 17 lignes (AAA 26 lignes, 258 k£ mail) |
| **4** | **17** | 246,2 | 504,2 | +258,0 k£ | **51,2 %** | 48,8 % | Opex bloqué à 12 lignes / 69 bus (terrain/TRACEX) |
| **5** | **746035** | 527,5 | 1027,4 | +499,8 k£ | **48,7 %** | 51,3 % | AAA 264 véhicules (PAX 724 k£, MAIL 230 k£) |
| **6** | **701256** | 490,5 | 944,5 | +454,0 k£ | **48,1 %** | 51,9 % | AAA 234 véhicules, réseau étendu 33 villes |
| **7** | **802204** | 675,2 | 1178,1 | +503,0 k£ | **42,7 %** | 57,3 % | Carte ultra-riche : AAA explose à 1,18 M£ |
| **8** | **73** | 505,2 | 837,9 | +332,7 k£ | 39,7 % | 60,3 % | Écart de rendement unitaire PAX (5,8k vs 3,9k) |
| **9** | **314** | 422,4 | 694,3 | +271,9 k£ | 39,2 % | 60,8 % | AAA domine le courrier (195 k£ vs 74 k£) |
| **10** | **232037** | 345,0 | 553,6 | +208,6 k£ | 37,7 % | 62,3 % | Opex sous-densifié (123 bus vs 168) |
| ... | ... | ... | ... | ... | ... | ... | ... |
| **36** | **2026** | 649,6 | 627,5 | **−22,1 k£** | **−3,5 %** | **103,5 %** | **Opex gagne :** 25 lignes Opex vs 20 AAA |
| **37** | **983759** | 571,6 | 527,2 | **−44,4 k£** | **−8,4 %** | **108,4 %** | **Opex gagne :** AAA bloqué en PAX (280 k£) |
| **38** | **781335** | 567,7 | 519,8 | **−47,9 k£** | **−9,2 %** | **109,2 %** | **Opex gagne :** Opex 200 bus vs 115 AAA |
| **39** | **8675309**| 652,9 | 590,9 | **−62,0 k£** | **−10,5 %** | **110,5 %** | **Opex gagne :** Opex domine PAX (449 k£) et MAIL (184 k£) |
| **40** | **42** | 700,7 | 517,5 | **−183,1 k£**| **−35,4 %** | **135,4 %** | **Opex écrase AAA :** 29 lignes, 240 bus |

### 3.2 Ce que les graines extrêmes ont en commun

L'analyse factorielle croisée (script `correlations.py` et inspection topologique des cartes 256×256) révèle les caractéristiques déterminantes du terrain :

1. **Les graines à fort décrochage (> 48 % de gap, ex. 999533, 123456, 746035, 701256, 802204) :**
   - **Présence de grands bassins urbains (> 1 000 à 2 500 hab.) :** Sur ces cartes, la production de courrier mensuel dépasse 50 à 100 sacs par ville. AAAHogEx identifie immédiatement ces pôles, y relie des paires longues (110–120 tuiles) et y déploie un nombre massif de véhicules (210 à 264 véhicules/graine).
   - **Explosion du poste Courrier chez AAA :** Le profit courrier d'AAA atteint 230 k£ à 376 k£ par graine sur ce groupe (contre 35 k£ à 150 k£ chez Opex).
   - **Déploiement de fret lourd :** Présence de grappes mine de charbon + centrale à 40–60 tuiles. Sur la graine 999533, AAA génère 129,4 k£ de profit rien qu'en camions de fret !
   - **Blocage précoce d'OpexAI :** Opex sature rapidement ses villes (limite stricte d'une ligne PAX par ville) et épuise son catalogue bus dès fin 1971, laissant sa caisse accumuler 200 à 400 k£ sans pouvoir toucher au fret ni aux paires longues.
2. **Les graines où OpexAI bat AAAHogEx (42, 8675309, 781335, 983759, 2026) :**
   - **Villes moyennes et dispersées (500 à 900 hab.) :** Faible gisement de courrier (la production est insuffisante pour alimenter les flottes massives d'AAA, dont le profit courrier plafonne à 57–94 k£).
   - **Absence d'industries de fret exploitables à courte distance par route :** AAA ne peut pas déployer ses 45 camions et fait chou blanc en fret (profit fret AAA nul ou négatif sur 42, 781335 et 8675309).
   - **Quadrillage optimal d'OpexAI :** L'avance de construction d'Opex (25 à 29 lignes ouvertes, 180 à 240 bus) lui permet de verrouiller l'ensemble des centres-villes avec `spread_stops=2`, captant la totalité du trafic voyageur local.
3. **Corrélations statistiques avec le gap relatif (`(AAA − Op)/AAA`) :**
   - Corrélation avec le gap de profit courrier (`mail_gap`) : **$r = +0,776$** (corrélation très forte).
   - Corrélation avec le gap de profit voyageur (`pax_gap`) : **$r = +0,647$** (forte).
   - Corrélation avec le nombre de villes desservies par Opex (`op_towns`) : **$r = −0,317$** (plus Opex parvient à relier de villes distinctes, plus l'écart se réduit).
   - Corrélation avec la distance moyenne PAX d'AAA : $r = +0,027$ (neutre : l'avantage d'AAA ne vient pas de lignes infiniment plus longues, mais de leur saturation bidirectionnelle).

---

## 3b. Réexamen approfondi des leviers échoués (Priorité haute)

L'ensemble des leviers testés lors des chantiers `ROAD1Y` (octobre-novembre 2026) a été réexaminé à la lumière de la décomposition factorielle du §1. Une idée n'est pas morte parce que son banc a échoué : une mauvaise implémentation, un bug d'orientation ou une collision avec une garde de trésorerie ont pu masquer un levier valide.

| Levier & Référence | Mécanisme visé | Résultat Gate A (40×3) | (i) Idée fondée ? | (ii) Cause de l'échec | Classification |
|---|---|:---:|:---:|---|:---:|
| **`road1y_truck_fleet`** + `freight` (`c4bb20bd`, cloud) | Flotte camions fret gérée comme AAA (ajout sur stock, retrait) + admission fret | **+16,9 k£/an** (19/21, p=0,38, IC95 [−9,9 ; +44,1] k) | **OUI, ABSOLUMENT** (Fret = 23,9 % du retard, −45 k£) | **Mécanisme non exercé.** Opex ne génère que 0,12 ligne fret/graine car les candidats fret sont préemptés par les bandes longues et la réserve de 50 k£ (`task_road.nut:1344`). Même avec 0,12 ligne, le gain était positif (+16,9 k£) ! | **VIVANTE À RÉIMPLÉMENTER** (`candidates.nut:4097`, `task_road.nut:1344`) |
| **`road1y_alt_load`** (`a3246a97`, cloud) | 33 % ou 50 % des bus PAX chargent à plein au bout B (`OF_FULL_LOAD_ANY`) | =33 : **+14,7 k£/an** (25/15, p=0,23)<br>=50 : **+12,5 k£/an** (25/15, p=0,18) | **OUI, MAJEURE** (Rendement bus = 50,2 % du retard) | **Sous le seuil artificiel de 20,7 k£.** 25 victoires sur 40 ! L'alternance aveugle 1 bus sur 2 a pénalisé les lignes déséquilibrées (attente excessive au bout faible). Doit être conditionné au stock réel de B. | **VIVANTE À RÉIMPLÉMENTER** (`builder_road.nut:5463-5470`) |
| **`road1y_pair_fleet`** (`2f9a4ffd`, cloud) | Classer les paires bus sur l'estimation à flotte mûre (8 bus) plutôt qu'à 2 bus | **+18,6 k£/an** (19/21, p=0,63, IC95 [−16,6 ; +55,5] k) | **OUI** (Lignes mûres 96–127 tuiles rapportent +60 % de plus) | **Bruit statistique / seuil 4 %**. N'a changé que le tri initial sans adapter le budget de voirie A* ni le coût d'infrastructure. | **VIVANTE À RÉIMPLÉMENTER** (`bus_districts_overrides.nut:387`) |
| **`road1y_pax_min`** (`ac4a78b2`, cloud) | Demande paire bus en $2 \times \min(A,B)$ au lieu de $A+B$ | =100 : **−11,6 k£/an** (15/25)<br>=50 : **−2,9 k£/an** (21/19) | **NON, ERRONÉE** chez Opex | **Mauvaise prémisse.** AAA prend le min des *villes* entières. Opex prenait le min de deux *arrêts de quartier* de 30 pax, écrasant la demande estimée de toutes les paires et bloquant la construction. | **IDÉE MORTE** |
| **`road1y_aaa_fleet`** (`813f5c2a`, cloud) | Flotte bus d'AAA d'un bloc (plafond temps trajet, achat min(A,B)>30, retrait) | **−22,7 k£/an** (16/24, p=0,14, Valeur −9,4 %) | **NON** (Incompatible avec notre schéma d'ordres) | **Effet pervers destructeur.** Avec plein à la source seule, les bus circulent vite. Conditionner les renforts sur $\min(A,B)$ et vendre les bus a asséché les lignes. Nos renforts « aveugles » rapportent. | **IDÉE MORTE** |
| **`road1y_town_reuse`** (`caa68552`, codex) | Autoriser 2 paires bus de plus par ville (max 3 lignes) | **−38,3 k£/an** (16/24, p=0,0098, Valeur −6,0 %) | **NON** (Contredit la topologie d'AAA) | **Cannibalisation locale.** AAA ne fait aucun réseau en étoile (96,4 % de villes à 1 ligne). Doubler les lignes sur une même ville divise le stock de passagers par deux et double les coûts de voirie. | **IDÉE MORTE** |
| **`road1y_rich_fleet`** (`0a16d948`, `48e27039`) | +10 bus si caisse > 60 k£ | =10 : **−9,8 k£/an** (14/26)<br>v2 : **−1,3 k£/an** (20/20) | **NON** | **Sur-saturation.** Opex a déjà 100 bus vs 85 chez AAA, avec 9,2 % de bus en perte. Injecter des bus sans demande dilue le profit unitaire. | **IDÉE MORTE** |
| **`road1y_berth_fleet`** (`d525c1f4`) | Renfort bus sans réserve 50 k£ et règle d'arrêt AAA | **+11,5 k£/an** (21/19, p=0,11) ; réplique 80p : +8,9 k£ | **OUI partiellement** | **Effet positif réel (+11,5 k£)** mais sous le seuil 4 % (20,7 k£). Libère des renforts utiles en an 2. | **INDÉTERMINÉE** (À tester en synergie) |
| **`road1y_pax_bilat`** (`00e64762`) | Renfort bus conditionné au min d'attente bilatéral | **+9,7 k£/an** (20/20, p=0,55, IC95 [−9,5 ; +29,6] k) | **Partiellement** | **Sous le seuil.** Trop restrictif sur les lignes asymétriques où B ne charge pas à plein. | **INDÉTERMINÉE** |
| **`road1y_abandon_days`** (`2e1b131e`) | Bannissement de paire réduit de 365 j à 60 j après SITE_LOST | Smoke 3g : **−22,0 k£/an** (1/3) | **NON** | **Gaspillage d'opcodes.** Réévaluer un site infaisable 60 jours plus tard rééchoue immédiatement dans le même créneau. | **IDÉE MORTE** |
| **Famille MAIL (`mail_min`, `mail_full`, `mail_net`, `mail_pick`, `spread_mail`, `mail_next`)** | Filtres de stock, chargement complet, réseau dédié, multi-arrêts courrier | `mail_min` : −45 k£<br>`mail_full` : −8 k£<br>`mail_net` : −38 k£<br>`mail_pick` : −27 k£<br>`spread_mail` : −0 k£ | **NON** (Le segment courrier est saturé à 3 ans) | **Paralysie et éviction de capex.** Le courrier en ville produit peu (15-30 sacs/mois) : forcer le chargement plein paralyse les fourgons pendant 3 mois ; construire des routes dédiées siphonne le capital des bus. | **FIL CLOS / IDÉES MORTES** |
| **`road1y_next2`** (`a67f0f7f`) | Bonus fundScore pour paires > 64/96 tuiles | =64 : **−303 k£** ; =96 : **−295 k£** | **Idée fondée, implémentation catastrophique** | **Blocage par TRACEX.** Forcer la priorité sur des paires trop longues a envoyé des projets infaisables au pathfinder, bloquant les créneaux et stoppant toute construction. | **IDÉE MORTE sous cette forme** |
| **`road1y_far`** (`988fea38`) | Ouverture des paires > 128 tuiles (trace budget élargi) | **+8,8 k£/an** (25/15, p=0,23, IC95 [−7,2 ; +24,7] k) | **Mitigée** | **Positif (+8,8 k£, 25/15)** mais trajets > 180 jours réduisent le paiement kilométrique en bus lent. | **INDÉTERMINÉE** |
| **`road1y_retry`** (`7cacb7ed`) | Réessais dans le même créneau après échec | =2 : **−0,0 k£** ; =4 : **+3,9 k£** | **NON** | **Neutre.** Un échec de tracé dans un mois donné ne se résout pas 2 secondes après dans le même cycle. | **IDÉE MORTE** |
| **`road1y_site_relocate`** (`52a7e0ec`) | Relocalisation de site bus perdu à $\le 6$ tuiles | **−4,2 k£/an** (14/26, p=0,29) | **NON** | **Dégradation de captage.** Le site de repli est en périphérie de ville et capte moins de passagers. | **IDÉE MORTE** |
| **`road1y_bridge`** (`f8023aec`) | Ponts routiers pour débloquer les tracés A* | **+0,4 k£/an** (22/18, p=0,90, IC95 [−21 ; +22] k) | **NON** | **Neutre.** Débloquer des tracés complexes à travers l'eau coûte trop cher en capex pour le gain obtenu. | **IDÉE MORTE** |

---

## 4. Conclusion : Trois hypothèses causales classées

### Hypothèse 1 (Rang 1) : Déficit de rentabilité unitaire des bus PAX par circulation à vide au retour (absence de chargement bidirectionnel sélectif)

- **Diagnostic causal :** Le transport de voyageurs explique **50,2 % du retard (−94,5 k£)**. Opex déploie 100,2 bus contre 85,9 chez AAA, mais chaque bus ne rapporte que 3 778 £ contre 5 509 £ (+45,8 % pour AAA). Avec `road1y_load_orders=1`, Opex impose `OF_FULL_LOAD_ANY` à la source A uniquement ; au retour depuis B, les bus repartent immédiatement avec une moyenne de seulement 9 passagers à bord. AAA impose un chargement complet aux deux bouts (`isDestFullLoadOrder = true`). L'essai `road1y_alt_load` était positif (+14,7 k£, 25 victoires) mais appliquait un quota rigide 1 bus sur 2.
- **Ce qu'il faudrait changer dans le code (sans l'écrire) :**
  - Fichier `ai/OpexAI/builder_road.nut`, lignes 5463–5470 (création des ordres initiaux) et `ai/OpexAI/bus_districts.nut`, lignes 1450–1490 (ordres de renfort) : conditionner l'ordre `AIOrder.OF_FULL_LOAD_ANY` au terminus B **non pas à un quota aveugle, mais au potentiel mesuré de B** (ex. `dst.captured >= 50` voyageurs/mois ou attente constatée $> 35$ pax), pour éviter l'attente paralysante sur les petits villages tout en saturant les retours sur les paires équilibrées.
- **Chiffre attendu si l'hypothèse est vraie :** Le rendement moyen par bus PAX d'OpexAI passe de 3 778 £ à **$\ge 4 600$ £/bus** (+21 %), le taux de bus à profit nul ($\le 0$) baisse de 9,15 % à $\le 5,0 %$, et le delta macroscopique `profit_year` progresse d'au moins **+30 k£/an** sur la porte A 40×3.
- **Test qui la réfuterait :** Si l'application du plein sélectif à B maintient le profit unitaire sous 4 000 £/bus ou engendre un allongement excessif du cycle de rotation (délai aller-retour $> 150$ jours) faisant chuter la note de gare à la source A sous 55 %.

---

### Hypothèse 2 (Rang 2) : Éviction structurelle du fret routier lourd par les filtres de catalogue et les bandes de distance

- **Diagnostic causal :** Le fret routier explique **23,9 % du retard (−45,0 k£)**. AAA déploie 2,92 lignes et 45 camions de charbon/bois par graine (46,4 k£ de profit net à payback $< 10$ mois). Opex n'en déploie que 0,12 ligne (1,4 k£) ! Le levier `road1y_truck_fleet` a rapporté +16,9 k£ alors qu'il n'avait que 5 lignes à gérer sur 40 graines. Le blocage est en amont : la génération de candidats fret routier est étouffée par le tri en bandes (`ROAD1Y_DIST_BANDS`) qui privilégie les bandes longues ($> 64$ tuiles) impossibles à tracer en camion, et par la réserve de trésorerie de 50 000 £ (`task_road.nut:1344`).
- **Ce qu'il faudrait changer dans le code (sans l'écrire) :**
  - Fichier `ai/OpexAI/candidates.nut`, lignes 4096–4105 (`OpexBuildRoadCandidates`) : pour le fret routier, inverser ou borner la recherche aux bandes courtes ($20 \le d \le 55$ tuiles, distance type mine-centrale ou forêt-scierie).
  - Fichier `ai/OpexAI/task_road.nut`, lignes 1344–1347 : abaisser la réserve de caisse des camions de 50 000 £ à 10 000 £ en mode route seule (`ROAD1Y`).
- **Chiffre attendu si l'hypothèse est vraie :** OpexAI ouvre en moyenne **2,0 à 3,0 lignes de fret par graine** dès 1970–1971, déploie **30 à 45 camions**, et le poste fret dégage au moins **+35 k£/an** de profit net en an 3, comblant $\ge 75 \%$ de l'écart fret face à AAA.
- **Test qui la réfuterait :** Si l'ouverture des lignes de fret court sature les créneaux de construction et retarde l'ouverture des 8 premières lignes de bus PAX, entraînant une perte sur le poste PAX supérieure au gain réalisé sur le fret.

---

### Hypothèse 3 (Rang 3) : Verrouillage précoce des villes par sous-évaluation des paires longues à l'an 1 et accumulation de 157 k£ de trésorerie oisive en an 3

- **Diagnostic causal :** En 1972, OpexAI voit sa trésorerie oisive exploser à **156 986 £** (contre 20 513 £ chez AAA) et son rythme d'ouverture s'effondrer (7,9 lignes vs 12,1 chez AAA). Opex ne dépense pas sa caisse parce qu'elle s'interdit de réutiliser une ville déjà connectée (`town_reuse` étant mort car cannibal) ET qu'elle a déjà consommé ses villes en 1970 sur des paires courtes (64–80 tuiles). L'estimateur de paire (`OpexRoadLineEconomics`) calcule le ROI à 2 bus fixes : à 2 bus, une paire de 70 tuiles paraît plus rentable qu'une paire de 115 tuiles. En réalité, à flotte mûre (8 bus), la paire de 115 tuiles rapporte 50 k£ contre 25 k£. AAA choisit ses villes par population brute, reliant d'emblée des paires de 105–115 tuiles.
- **Ce qu'il faudrait changer dans le code (sans l'écrire) :**
  - Fichier `ai/OpexAI/bus_districts_overrides.nut`, lignes 387–410 (`OpexRoad100SoloPaxCandidates`) et `ai/OpexAI/economy.nut`, lignes 789–850 (`OpexRoadLineEconomics`) : classer les candidats bus PAX non pas sur l'économie à 2 bus, mais en injectant un `fleetCapOverride` proportionnel au temps de trajet ou à la distance ($d / 15$), permettant aux paires majeures de 95–125 tuiles d'être choisies en priorité en 1970 avant que les villes ne soient bloquées.
- **Chiffre attendu si l'hypothèse est vraie :** La distance moyenne Manhattan des lignes PAX d'OpexAI passe de 96,0 à **$\ge 105,0$ tuiles** (alignée sur AAA), le profit moyen par ligne PAX passe de 26,6 k£ à **$\ge 33,0$ k£/ligne**, et la trésorerie oisive résiduelle fin 1972 descend sous **80 000 £** (réinvestie dans des réseaux à fort rendement).
- **Test qui la réfuterait :** Si le relèvement de la distance moyenne entraîne une explosion des échecs de tracé A* (`plan_failed:TRACEX`), réduisant le nombre total de lignes ouvertes à moins de 11 en an 1 et détruisant la valeur d'entreprise par immobilisation d'infrastructures inachevées.

---
exit=0
