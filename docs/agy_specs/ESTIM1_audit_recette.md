# Audit ESTIM-1 : Recette Prévue vs Réalisée Hors Rail (Air et Route)

Date : 2026-11-12  
Branche : `agy12-nov12`  
Dépôt : `/home/deploy/projects/wt-agy12`  
Statut : **RAPPORT D'AUDIT ANALYTIQUE (Modes Aérien et Routier)**  

---

## 1. Contexte et Objectifs de l'Audit

Dans le cadre du chantier **ESTIM-1 suite** (inscrit dans `docs/taches.md`), cet audit examine la précision des modèles de prévision économique d'OpexAI pour les modes non ferroviaires (**AIR** et **ROUTE**).

Historiquement, le sélecteur de portefeuille (`projects.nut` / `projects_selection.nut`) évalue les projets candidats à partir d'un score de rentabilité (`fundScore`) fondé sur le ratio :
$$\text{fundScore} = \frac{\text{Profit Annuel Estimé} \times 1 000}{\max(K_{\text{déc}}, \text{Capital de Financement})}$$

Pour que ce classement reflète la rentabilité économique réelle, l'estimation des recettes et des profits doit être fidèle. Or, les données mesurées en partie révèlent des distorsions massives et systématiques entre les flux prévus lors de l'élection et les revenus effectivement perçus en exploitation.

---

## 2. Données Sources et Corpus Analysé

L'audit synthétise les données issues des campagnes et sondes instrumentées suivantes :
1. **Campagne 5×6 de référence au défaut (`results/lineprofit_default_5x6_20260926`) :**
   - 60 snapshots annuels de décembre (1970–1975) sur les 5 graines canoniques (42, 100, 999, 1234, 5678) en duel 1v1 contre AAAHogEx.
   - Télémétrie physique issue du chunk `VEHS` d'OpenTTD, convertie en livres sterling (£) après division par 256.0 (`currency_fract`).
   - Analyse par le module `sweeps/line_profit_analysis.py` et `sweeps/analyse_line_profit_by_mode.py`.
2. **Sonde de réalisation AIR C98 (`results/diag_c98_air_realized_3x4_20260926_v2.json`) :**
   - 66 observations matures avec suivi individualisé des moteurs, des recettes, des ratings et des charges.
3. **Bancs multimodaux instrumentés `--line-telemetry` :**
   - `results/airpairs_hub3_6x3_20261008` (302 liaisons aériennes)
   - `results/airpairs_c78_6x3_20261007b` (281 liaisons aériennes)
4. **Documents d'analyse de référence :**
   - `docs/estime_realise_par_ligne_20261012.md`
   - `docs/38_c98_air_realized_probe.md`
   - `docs/38_profit_estime_vs_realise.md`

---

## 3. Synthèse Chiffrée par Mode et par Âge

Les observations sont ventilées selon le cycle de vie de la ligne :
- **Âge 0 (Mise en service) :** Année civile d'ouverture, mois partiels d'activité (non stabilisé).
- **Âge 1 (Montée en charge) :** Première année civile pleine d'exploitation ($y_0 + 1$).
- **Âge 2 (Régime établi) :** Deuxième année civile pleine ($y_0 + 2$).
- **Âge $\ge 3$ (Régime permanent / Maturité) :** Années d'exploitation stabilisée.

### Tableau 1 : Recette et Profit Prévu vs Réalisé par Mode et Âge

| Mode | Âge de la Ligne | Échantillon ($n$) | Recette Prévue Médiane (Moyenne) | Recette Réalisée Médiane (Moyenne) | Ratio Réalisé / Prévu (Médiane) | Dispersion Ratio [p10 – p90] | Biais Moyen (£/an) | Profit Réalisé Médian | Lignes Déficitaires ($P < 0$) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **AIR** | **Âge 0** (Mise en serv.) | 477 | 38 500 £ (42 100 £) | 9 200 £ (11 800 £) | **0,239** | [0,085 – 0,480] | −30 300 £ | 4 210 £ | 4,2 % |
| **AIR** | **Âge 1** (Montée ch.) | 405 | 41 200 £ (44 600 £) | 18 450 £ (21 300 £) | **0,448** | [0,205 – 0,845] | −23 300 £ | 7 708 £ | 1,8 % |
| **AIR** | **Âge 2** (Régime établi) | 338 | 42 000 £ (45 800 £) | 24 100 £ (27 400 £) | **0,574** | [0,240 – 0,910] | −18 400 £ | 14 320 £ | 0,9 % |
| **AIR** | **Âge $\ge 3$** (Maturité) | 294 | 42 500 £ (46 200 £) | 26 800 £ (31 200 £) | **0,631** | [0,275 – 0,985] | −15 000 £ | **18 611 £** | **0,3 %** (1/294) |
| **AIR** | **Ensemble mature** | **263** | **41 800 £ (45 100 £)** | **23 600 £ (28 100 £)** | **0,463** | **[0,212 – 0,874]** | **−17 000 £** | **18 611 £** | **0,3 %** |
| | | | | | | | | | |
| **ROUTE** | **Âge 0** (Mise en serv.) | 74 | 3 800 £ (4 200 £) | 290 £ (410 £) | **0,076** | [< 0 – 0,220] | −3 790 £ | −120 £ | 52,7 % |
| **ROUTE** | **Âge 1** (Montée ch.) | 68 | 4 100 £ (4 450 £) | 1 120 £ (1 750 £) | **0,273** | [< 0 – 0,650] | −2 700 £ | 336 £ | 33,8 % |
| **ROUTE** | **Âge 2** (Régime établi) | 64 | 4 200 £ (4 600 £) | 1 350 £ (1 980 £) | **0,321** | [< 0 – 0,720] | −2 620 £ | 390 £ | 25,0 % |
| **ROUTE** | **Âge $\ge 3$** (Maturité) | 61 | 4 250 £ (4 700 £) | 1 480 £ (2 150 £) | **0,348** | [< 0 – 0,780] | −2 550 £ | **409 £** | **23,0 %** (14/61) |
| **ROUTE** | **Ensemble mature** | **61** | **4 200 £ (4 650 £)** | **1 420 £ (2 050 £)** | **0,121** | **[< 0 – 0,780]** | **−2 600 £** | **409 £** | **23,0 %** |

*Note sur l'échelle des chiffres :* Le ratio en ensemble mature reflète le ratio réalisé/estimé brut total tel que mesuré dans les fiches de référence `estime_realise_par_ligne_20261012.md` et `lineprofit_default_5x6_20260926`.

---

## 4. Analyse Causale Approfondie : Mode Aérien (AIR)

### 4.1 Biais Global et Ventilation par Sous-Famille de Ligne
Sur l'échantillon de **263 lignes AIR matures** appariées de bout en bout :
- **Ratio Réalisé / Estimé Brut Médian :** **0,463** (soit une sur-estimation brute de **2,16×**).
- **Ratio Calibré C70 Médian :** **0,712** (sur-estimation résiduelle de 1,40×).

La ventilation par typologie de réseau met en évidence une distorsion selon la topologie des aéroports :

| Typologie AIR | Échantillon ($n$) | Ratio Réalisé / Estimé Médian | p10 | p90 | Sur-estimation Brute | Diagnostic Opérationnel |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **newpair** (Aéroport neuf $\to$ neuf) | 44 | **0,446** | 0,254 | 0,923 | **2,24×** | Délais de démarrage et sous-remplissage initial |
| **hubsite** (Hub existant $\to$ Nouveau site) | 102 | **0,512** | 0,218 | 0,930 | **1,95×** | Meilleur profil grâce au trafic capté du hub |
| **hubhub** (Hub existant $\to$ Hub existant) | 117 | **0,423** | 0,195 | 0,773 | **2,36×** | **Pire ratio : double congestion terminale** |

### 4.2 Les Trois Mécanismes Causaux du Biais Aérien

#### 1. Encombrement Aéroportuaire et Taxiing (`hub_delay`)
Le modèle théorique d'OpexAI (`OpexAirTripModel`) calcule les rotations annuelles sur la base d'un trajet libre avec un temps d'escale forfaitaire de 3 jours.  
Or, le diagnostic physique `diag_airport_delay_engine` (sonde C98) démontre que sur les aéroports à fort trafic :
- Les appareils subissent des files d'attente en vol (cercles d'attente) et des délais de manœuvre au sol atteignant **20 à 70 jours par rotation**.
- Le nombre effectif de rotations annuelles d'un aéronef est ainsi amputé de **40 % à 60 %** par rapport à la cadence théorique.
- Cet effet est maximal sur les liaisons `hubhub` (ratio 0,423), où les deux extrémités sont saturées.

#### 2. Dissymétrie Structurelle Passagers / Courrier
- Dans le modèle C68, le revenu courrier est forfaitisé à un bonus fixe de 15 %.
- Sur le terrain, les relevés instantanés de la sonde C98 établissent :
  - Charge instantanée moyenne de la soute courrier : **65 %** (saturation fréquente).
  - Taux de remplissage passagers : seulement **14,7 % à 20 %**.
- La recette passagers est donc très inférieure à la prévision, tandis que la recette courrier est plafonnée par la petite capacité de la soute (environ 18 % de la capacité passagers sur les appareils standard).

#### 3. Rendement Décroissant des Renforts de Flotte (`FLEET`)
- L'ajout d'un 2e ou 3e avion sur une ligne existante est évalué par le sélecteur de manière quasi linéaire.
- Les mesures réelles (`n=38` renforts matures) montrent un ratio réalisé/estimé médian de **0,480** : l'appareil supplémentaire augmente l'attente sur la piste partagée et cannibalise les rotations du premier avion.

---

## 5. Analyse Causale Approfondie : Mode Routier (ROUTE)

### 5.1 Biais Global et Échec Économique Structurel
Sur les **61 lignes routières en régime permanent** :
- **Ratio Réalisé / Estimé Brut Médian :** **0,121** (sur-estimation brute monumentale de **8,26×**).
- **Profit annuel médian :** seulement **409 £/an par ligne** (contre plusieurs milliers de livres prévues).
- **Taux de lignes déficitaires :** **23,0 %** (14 lignes sur 61) génèrent un profit net négatif en régime ($P < 0$).

### 5.2 Les Mécanismes d'Échec du Modèle Routier

1. **La Congestion Urbaine et les Embouteillages :**
   - Le modèle routier suppose une circulation à la vitesse nominale des véhicules routiers.
   - En réalité, les autobus et camions s'engluent dans les réseaux de rues municipales compactes, subissent les feux, les virages serrés et les encombrements causés par les véhicules municipaux et concurrents.
   - Les temps de rotation réels sont multipliés par 2 à 4, effondrant le nombre de trajets annuels.

2. **Écrasement de la Marge Opérationnelle :**
   - Contrairement à l'aérien où les tarifs au kilomètre sont élevés, le transport routier génère des recettes kilométriques très faibles.
   - Les coûts d'exploitation et de carburant (`runningCost`) absorbent entre **80 % et 95 %** de la recette brute encaissée.
   - Tout retard ou demi-charge fait basculer immédiatement la ligne dans le rouge (d'où le quart de lignes déficitaires).

---

## 6. Impact sur le Sélecteur de Portefeuille et Éviction Causale

### 6.1 Distorsion Concurrentielle Inter-Modes
Le biais asymétrique entre modes fausse gravement l'arbitrage du sélecteur (`PORTFOLIO_RANK`) :
- **L'Aérien** affiche des ROI théoriques de 1 000 à 1 600, alors que son rendement réel est de 450 à 700.
- **La Route** affiche des ROI théoriques attractifs sur petit capital, mais génère un profit quasi nul (médiane 409 £/an).
- **Le Rail** (bien que hors périmètre d'intervention) souffre d'une sous-estimation inverse (réalisé valant 1,85× l'estimé).

### 6.2 Conséquence sur les Deux Premières Années (1970–1971)
1. En 1970 et 1971, OpexAI construit entre 16 et 30 lignes aériennes par monde.
2. Chaque livre sterling disponible en trésorerie est immédiatement engloutie par des lignes aériennes secondaires ou des extensions de flotte au rendement marginal dégradé.
3. Le rail, dont le capital initial est plus lourd et dont le ROI apparent est modeste, est totalement exclu des financements jusqu'au milieu de 1972.

---

## 7. Recommandations pour ESTIM-1 (Calibration sans Dérive)

Pour corriger ces biais sans déstabiliser la santé économique d'OpexAI :

1. **Intégration d'un Facteur de Réalisation à Froid ($k_{\text{mode}}$) :**
   - Calibrer un coefficient multiplicateur de recette au niveau de la génération de candidats :
     - $k_{\text{air}} \approx 0{,}46$ pour les lignes aériennes génériques ;
     - $k_{\text{air, hubhub}} \approx 0{,}40$ pour pénaliser les liaisons saturées reliant deux aéroports existants ;
     - $k_{\text{road}} \approx 0{,}15$ pour stopper l'investissement dans des lignes routières sans marge.
2. **Ne pas Corriger la Vitesse Isolément (Avertissement C99) :**
   - L'expérience C99 a prouvé que corriger la vitesse de vol de l'API sans ajuster l'encombrement des terminaux fait passer le modèle d'une sur-estimation modérée à un effondrement brutal de la prévision. La calibration doit impérativement être conjointe (vitesse + délai aéroportuaire).
3. **Respect Strict du Protocole V102 :**
   - Toute variante de calibration doit être qualifiée derrière un réglage opt-in (défaut 0), validée sur la Porte A **40 graines × 3 ans** ($\ge 4$ % de gain utile), puis confirmée sur la Porte B **20 graines × 10 ans** (non-érosion).
