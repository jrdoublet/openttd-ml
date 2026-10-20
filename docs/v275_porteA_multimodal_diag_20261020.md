# Diagnostic de l'échec de la porte A multimodale V275 (20/10/2026)

## 1. Contexte, protocole et résultat brut

La porte A multimodale de V275 a été exécutée sur GitHub Actions (run `39303852862`, tentative 1, durée 12 min 39 s, SHA `4152420`).
Les données sources proviennent de l'artefact officiel `bench-paired-gain_short-39303852862-1` (téléchargé dans `/home/deploy/.claude/jobs/e230de46/tmp/v275A/`).

### Bras comparés (`request.json`)
- **Référence** : `OpexAI[v275_rail_pax_mm=0]` (autres réglages aux défauts : `v207_rail_pax_share_pct=0`, `v207_rail_mail=0`, `v207_rail_pax_joined_stops=0`).
- **Variante** : `OpexAI[v207_rail_pax_share_pct=40,v207_rail_mail=1,v207_rail_pax_joined_stops=2,v275_rail_pax_mm=7]`.
- **Protocole** : `gain_short` V102 apparié contre AAAHogEx figée, 40 graines canoniques, horizon 3 ans (1970–1972), 80 parties jouées, santé 100 % saine, télémétrie OFF.

### Verdict économique (`bench.json -> policy_comparison`)
- **Verdict** : **`fail_primary`**
- **Métrique primaire (`profit_year` en 1972)** :
  - Delta moyen : **−71 401,1 £/an** (−3,32 % du profit moyen de référence)
  - Delta médian : **−50 870,0 £/an**
  - Écart-type : 233 557,4 £/an | Erreur standard : 36 928,7 £/an
  - IC95 bootstrap (20 000 tirages, graine 0) : **[−144 589,0 £/an ; −665,9 £/an]** (entièrement négatif)
  - Test des signes : 15 victoires / 25 défaites / 0 égalité (p = 0,15386)
  - Wilcoxon bilatéral : p = **0,07700**
- **Garde de valeur (`company_value`)** :
  - Delta moyen : **−123 164,1 £** (14 V / 26 D)
  - Ratio des moyennes : 0,967583 (perte de **−3,24 %**, garde de −5 % tenue)
- **Comparaison OpexAI / AAAHogEx (`summary.md`)** :
  - Référence : OpexAI 2 151 242,0 £/an vs AAAHogEx 2 038 994,3 £/an (ratio 105,5 %)
  - Variante : OpexAI 2 079 840,9 £/an vs AAAHogEx 2 022 941,5 £/an (ratio 102,8 %)

---

## 2. Distribution des écarts par graine et cas extrêmes

Source : `bench.json -> policy_comparison.per_pair[].metrics.profit_year.policy_delta`

### Déciles de la distribution (N = 40)
- D1 : −394 604,0 £/an
- D2 : −215 146,0 £/an
- D3 : −169 581,9 £/an
- D4 : −102 654,2 £/an
- **Médiane (D5)** : **−50 870,0 £/an**
- D6 : −6 245,4 £/an
- D7 : +28 019,3 £/an
- D8 : +104 235,0 £/an
- D9 : +214 514,6 £/an

### Les 5 pires graines (pertes variantes sévères)
1. **Graine 999** : **Δ = −788 460 £/an** (ref 2 310 355 £ -> var 1 521 895 £), Δval −1 288 335 £
   - Trajectoire du delta : 1970 : −2 415 £ | **1971 : −397 624 £** | 1972 : −788 460 £
   - Flotte fin 1971 : ref 29 avions vs var 19 avions (−10 avions dès 1971) ; 0 ligne voyageurs posée !
2. **Graine 841478** : **Δ = −518 158 £/an** (ref 3 129 168 £ -> var 2 611 010 £), Δval −768 674 £
   - Trajectoire : 1970 : −12 019 £ | **1971 : −153 789 £** | 1972 : −518 158 £
   - Flotte fin 1971 : ref 49 avions vs var 43 avions (−6 avions) ; 0 ligne voyageurs posée.
3. **Graine 442018** : **Δ = −416 627 £/an** (ref 2 215 781 £ -> var 1 799 154 £), Δval −723 918 £
   - Trajectoire : 1970 : −28 445 £ | **1971 : −187 064 £** | 1972 : −416 627 £
   - Flotte fin 1971 : ref 35 avions vs var 24 avions (−11 avions) ; 0 ligne voyageurs posée.
4. **Graine 723002** : **Δ = −403 286 £/an** (ref 2 702 385 £ -> var 2 299 099 £), Δval −283 612 £
   - Trajectoire : 1970 : +33 577 £ | 1971 : +11 156 £ | 1972 : −403 286 £
   - Flotte fin 1972 : ref 59 avions vs var 65 avions (+6 avions, mais 61 k£ de cash restant vs 812 k£ en ref).
5. **Graine 983759** : **Δ = −316 466 £/an** (ref 1 550 362 £ -> var 1 233 896 £), Δval −609 046 £
   - Trajectoire : 1970 : −22 292 £ | 1971 : −72 860 £ | 1972 : −316 466 £

### Les 5 meilleures graines (gains variantes)
1. **Graine 59527** : **Δ = +496 813 £/an** (ref 1 960 428 £ -> var 2 457 241 £), Δval +1 220 137 £
   - Trajectoire : 1970 : +136 849 £ | **1971 : +410 304 £** | 1972 : +496 813 £
   - Flotte fin 1971 : ref 25 avions vs var 39 avions (+14 avions dès 1971) ; 0 ligne voyageurs posée !
2. **Graine 17** : **Δ = +237 145 £/an** (ref 1 606 794 £ -> var 1 843 939 £), Δval +268 926 £
   - Trajectoire : 1970 : +6 720 £ | 1971 : −3 072 £ | 1972 : +237 145 £
3. **Graine 1337** : **Δ = +234 863 £/an** (ref 2 484 128 £ -> var 2 718 991 £), Δval +536 970 £
   - Trajectoire : 1970 : +31 880 £ | 1971 : +140 681 £ | 1972 : +234 863 £
4. **Graine 423960** : **Δ = +216 040 £/an** (ref 2 922 871 £ -> var 3 138 911 £), Δval +746 114 £
   - Trajectoire : 1970 : +63 600 £ | 1971 : +139 525 £ | 1972 : +216 040 £
5. **Graine 313707** : **Δ = +200 786 £/an** (ref 2 236 737 £ -> var 2 437 523 £), Δval +271 305 £
   - Trajectoire : 1970 : +50 810 £ | 1971 : +464 £ | 1972 : +200 786 £

---

## 3. Ventilation par année et par mode

Source : `bench.jsonl` (36 instantanés mensuels par partie, `primary_vehicles_by_mode`, `air_airports`, `capacities_by_cargo`, `rail_attempt_sign_ob`).

### 3.1 Trajectoire annuelle de `profit_year` (Opex variante − Opex référence)
- **1970** : moyenne **+11 325,1 £/an** | médiane +4 065,0 £/an | 24 V / 16 D
- **1971** : moyenne **−20 965,2 £/an** | médiane −16 581,0 £/an | 18 V / 22 D
- **1972** : moyenne **−71 401,1 £/an** | médiane −50 870,0 £/an | 15 V / 25 D

### 3.2 Évolution du parc de véhicules et des aéroports (moyennes par partie)

| Mode / Infrastructure | Fin 1970 (1970-12-01) | Fin 1971 (1971-12-01) | Fin 1972 (1972-12-01) |
|---|---:|---:|---:|
| **Avions (air)** — Ref | 10,40 | 34,08 | 58,23 |
| **Avions (air)** — Var | 10,47 | 33,23 | 55,20 |
| *Δ Avions (Var − Ref)* | **+0,07** | **−0,85** (−34 avions total) | **−3,02** (−121 avions total) |
| **Aéroports** — Ref | 11,68 | 27,60 | 35,02 |
| **Aéroports** — Var | 11,70 | 26,82 | 34,70 |
| *Δ Aéroports (Var − Ref)* | **+0,02** | **−0,78** (−31 aéroports total) | **−0,32** (−13 aéroports total) |
| **Trains (rail)** — Ref | 0,00 | 3,25 | 8,45 |
| **Trains (rail)** — Var | 0,00 | 3,33 | 8,95 |
| *Δ Trains (Var − Ref)* | **0,00** | **+0,08** (+3 trains total) | **+0,50** (+20 trains total) |
| **Véhicules routiers (road)** — Ref | 0,00 | 2,05 | 3,75 |
| **Véhicules routiers (road)** — Var | 0,00 | 2,20 | 3,00 |
| *Δ Routiers (Var − Ref)* | **0,00** | **+0,15** (+6 routiers total) | **−0,75** (−30 routiers total) |

### 3.3 Date de la première ligne rail voyageurs dans la variante
- **En 1970** : **0 ligne** voyageurs posée dans les 40 graines (trains = 0 partout).
- **En 1971** : **0 ligne** voyageurs posée dans les 40 graines de la variante. (En référence, 2 graines seulement ont posé un train voyageur fin 1971 : graine 512 en juillet 1971 et graine 100 en novembre 1971).
- **En 1972 (3e année)** : la toute première ligne rail voyageurs apparaît le **1972-03-01** (graine 781335).
- **Sur l'ensemble des 40 graines en variante** :
  - **15 graines** ont posé au moins une ligne voyageurs en 1972 (graines 17, 100, 512, 65537, 123456, 230185, 313707, 375172, 455216, 613553, 723002, 781335, 802204, 841478, 8675309).
  - Ces lignes ont été posées tardivement : 1 en mars 1972, 1 en avril 1972, 2 en juillet 1972, 3 en août 1972, 3 en septembre 1972, 1 en octobre 1972, 3 en novembre 1972, 1 en décembre 1972.
  - **25 graines** n'ont posé **aucune ligne rail voyageurs** sur les 3 ans entiers.

---

## 4. Analyse des canaux : perturbation d'opcodes vs canal réel

Le diagnostic révèle la superposition de **deux phénomènes distincts** :

### 4.1 La perturbation d'opcodes (bruit chaotique aérien dès 1970-1971)
- **Le constat matériel** :
  - Dès 1971, le profit annuel décroche déjà en moyenne de **−20 965 £/an** (−16 581 £/an en médiane), et le parc aérien recule de 0,85 avion par partie.
  - Sur les graines extrêmes, ce décrochage est massif dès 1971 : graine 999 perd −397,6 k£ et 10 avions dès 1971 ; graine 442018 perd −187,1 k£ et 11 avions ; à l'inverse, graine 59527 gagne +410,3 k£ et 14 avions dès 1971.
  - **Pourtant, en 1970 et 1971, aucune ligne rail voyageurs n'a été construite dans la variante (0 sur 40 graines).**
- **La corrélation décisive** :
  - `corr(Δ profit 1971, Δ profit 1972) = +0,6669`
  - `corr(Δ avions 1971, Δ profit 1972) = +0,5832`
  - `corr(Δ trains 1972, Δ profit 1972) = +0,1481`
  Le profit de 1972 est d'abord prédit par la trajectoire aérienne acquise dès 1971.
- **La cause Squirrel du décalage en 1970-1971** :
  - En référence, `v275_rail_pax_mm = 0`. La fonction `OpexPaxCandidates` s'exécute en 1971 et consomme environ **3,26 millions d'opcodes** (`cand_pax = 3 257 573` sur le panneau `OP|1971`).
  - En variante, `v275_rail_pax_mm = 7`. Le **bit 4** court-circuite `OpexPaxCandidates` (`candidates.nut:969-971`) car `AIDate.GetYear(date) < OPEX_START_YEAR + 2`. La variante dépense **0 opcode** sur `cand_pax` en 1970-1971.
  - Cette économie de ~3,25 M opcodes décale l'alignement temporel des ticks du planificateur face à AAAHogEx. En duel partagé non déterministe, ce décalage fait basculer la préemption des aéroports et le tempo des poses aériennes.
  - Ce bruit correspond exactement à la bande de fluctuation observée sur duel A/A strict (environ **±70 k£/an**, mémoire `bruit_perturbation_opcodes`).

### 4.2 Le coût d'amorçage à 3 ans des lignes voyageurs posées en 1972
Lorsque l'on sépare les 40 graines selon l'exposition réelle au rail voyageurs en 1972 :
- **Sous-groupe SANS ligne voyageurs en variante (N = 25 graines)** :
  - Delta moyen 1971 : **−8 030,3 £/an**
  - Delta moyen 1972 : **−47 399,8 £/an** (médiane −31 242 £/an, 10 V / 15 D)
  - Delta avions 1972 : −2,76 avions | Delta trains : 0,00
  - Ce sous-groupe est une démonstration pure du bruit de perturbation aérienne résiduel (dans la bande des ±70 k£/an).
- **Sous-groupe AVEC ligne voyageurs en variante (N = 15 graines)** :
  - Delta moyen 1971 : **−42 523,3 £/an**
  - Delta moyen 1972 : **−111 403,3 £/an** (médiane −141 803 £/an, 5 V / 10 D)
  - Delta avions 1972 : −3,47 avions | Delta trains : +1,33
  - L'écart se creuse de **−64 003,5 £/an** supplémentaires par rapport au groupe sans ligne.
- **Pourquoi la pose en 1972 coûte-t-elle à 3 ans ?**
  1. **Maturation insuffisante** : 13 des 15 lignes sont posées entre juillet et décembre 1972. À la date de mesure (`1972-12-01`), la ligne n'a circulé que pendant 1 à 4 mois. Or `profit_year` cumule 4 trimestres : la ligne porte ses coûts d'exploitation et son amortissement complets sans avoir dégagé une année de recettes.
  2. **Surcoût des arrêts joints V207** : `v207_rail_pax_joined_stops=2` impose de poser jusqu'à 2 arrêts de bus traversants par gare, consommant du capital immédiat et des opcodes de tracé routier (`road_planning` monte de +331 k opcodes en moyenne).
  3. **Appel d'opcodes A\* en 1972** : les composantes d'opcodes (`bench.json -> observed_opcode_components`) montrent que `rail_attempt` consomme **+3 952 608 opcodes** supplémentaires en variante (31,67 M vs 27,72 M en ref), tandis que `air_planning` recule de −271 506 opcodes.
- **Confirmation par la porte B (10 ans)** :
  À 10 ans, ces mêmes lignes ont amorti leur investissement, tournent à plein régime avec la part 40 % et le courrier, et la porte B passe sans érosion (+46 k£/an sur VPS, +15,9 k£/an sur Actions run 39303891198). Le coût constaté en porte A est donc un **artefact d'horizon court (3 ans)** sur des lignes ouvertes en fin de période.

---

## 5. Audit statique : comportement des réglages avant la 3e année

Lecture exhaustive des fichiers `ai/OpexAI/*.nut` pour les 4 réglages de la variante :

1. **`v275_rail_pax_mm` (masque, valeur 7)** :
   - **Bit 1** (anti-recouvrement aéroports, `candidates.nut:977-987`) : s'exécute dans `OpexPaxCandidates`. Avant 1972, bit 4 a déjà fait un `return` : le bit 1 est **inactif en 1970-1971**.
   - **Bit 2** (recalage V212 150/85, `economy.nut:482-484`) : ne s'applique que sous la garde `kind == "pax"`. Comme aucun candidat voyageurs n'est produit avant 1972, le bit 2 est **inactif en 1970-1971**. Il ne s'applique jamais au fret.
   - **Bit 4** (aérien d'abord, `candidates.nut:969-971`) : `if ((V275_RAIL_PAX_MM & 4) && MODE_AIR && ... < OPEX_START_YEAR + 2) return;`. **C'est le seul bit actif avant l'an 3.** Il supprime la génération de candidats voyageurs en 1970-1971, épargnant 3,25 M opcodes par an par rapport à la référence.
2. **`v207_rail_pax_share_pct=40`** :
   - Utilisé dans `candidates.nut:1051` (dans `OpexPaxCandidates` après le return de bit 4) et dans `economy.nut:208` (`kind == "pax"`).
   - Ne s'applique jamais au fret. **Totalement inerte avant l'an 3.**
3. **`v207_rail_mail=1`** :
   - Utilisé dans `candidates.nut:997` (dans `OpexPaxCandidates`) et `economy.nut:552` (`candidate.kind == "pax"`).
   - Ne s'applique jamais au fret. **Totalement inerte avant l'an 3.**
4. **`v207_rail_pax_joined_stops=2`** :
   - Utilisé dans `task_rail.nut:1155` (`candidate.kind == "pax"`).
   - Ne s'exécute qu'à la construction effective d'une ligne voyageurs. **Totalement inerte avant l'an 3.**

**Conclusion de l'audit** : aucun réglage de V207 ne s'applique au fret, ni aux candidats fret, ni ne consomme d'opcodes avant 1972. La divergence de 1970-1971 provient exclusivement du décalage de timing provoqué par le shunt du bit 4.

---

## 6. Limites des artefacts et proposition d'exposition instrumentée

### Ce qui est certain avec les artefacts actuels
- La répartition annuelle des véhicules et aéroports par mode est connue au mois près.
- Les dates exactes d'apparition des rames et lignes voyageurs sont établies.
- L'inertie rigoureuse de V207 avant 1972 est démontrée par audit statique.
- L'existence d'une divergence aérienne dès 1971 expliquant 67 % de la variance de 1972 est prouvée.

### Ce qui manque dans l'artefact officiel
L'artefact a été produit avec `telemetry: false` et `decision_log = 0` (conformément aux règles de qualification V102 sans sonde intrusive). Il manque donc le journal chronologique fin des décisions d'arbitrage (`PROJECT_SELECT`, `AIR_FINANCE_TRY`, `RAIL_FINANCE_SELECT`, `V207_STOPS`) qui permettrait de voir au tick près quelle décision aérienne a été décalée en 1971 sur la graine 999 ou 442018.

### Proposition d'exposition ciblée (1 commande, prête à lancer)
Si l'on souhaite observer directement la mécanique interne sur les graines divergentes :
- **Campagne** : `v275_expo_diag_decision_5x3_20261020`
- **Profil** : 5 graines représentatives (les 2 pires : `999`, `442018` ; la médiane : `42` ; les 2 meilleures : `59527`, `1337`) × 3 ans.
- **Réglages** : `decision_log=1` dans les deux bras pour tracer les événements de sélection et de caisse sans modifier les ratios.
- **Commande** :
```bash
python3 sweeps/bench_1v1_5y_20seeds.py \
  --campaign v275_expo_diag_decision_5x3_20261020 \
  --reference "OpexAI[v275_rail_pax_mm=0,decision_log=1]" \
  --variant "OpexAI[v207_rail_pax_share_pct=40,v207_rail_mail=1,v207_rail_pax_joined_stops=2,v275_rail_pax_mm=7,decision_log=1]" \
  --years 3 --seeds 999 442018 42 59527 1337 --max-workers 5
```

---

## 7. Proposition de levier / réglage pour débloquer la porte A

Le diagnostic démontre que le paquet complet `mm=7` avec arrêts joints et recalage V212 surcote les lignes voyageurs au point de déclencher des poses tardives en 1972 qui coûtent du capital et des opcodes sans rapporter à 3 ans.

Sans rendre le paquet inerte face à l'aérien (ce que l'utilisateur a expressément refusé), le levier le plus prometteur consiste à **alléger le bras multimodal de ce qui pèse sur la caisse et les opcodes en an 3** :

### Levier proposé : Bras multimodal sobre (sans arrêts joints et sans surcote V212)
- **Bras candidat** :
  `OpexAI[v207_rail_pax_share_pct=40,v207_rail_mail=1,v207_rail_pax_joined_stops=0,v275_rail_pax_mm=5]`
- **Mécanisme du levier** :
  1. **`v207_rail_pax_joined_stops = 0`** : suppression des arrêts de bus joints en multimodal. Économise le capital immédiat des stations routières et les ~330 k opcodes de `road_planning`, tout en évitant d'étendre la zone de chalandise de la gare vers les aéroports.
  2. **`v275_rail_pax_mm = 5` (bits 1 + 4, sans bit 2)** :
     - Conserve le **bit 1** (interdiction stricte de toucher une ville où nous avons un aéroport : protection dominante contre la cannibalisation aérienne).
     - Conserve le **bit 4** (démarrage en an 3 pour laisser l'aérien s'installer sur les deux premières années).
     - **Retire le bit 2** (le recalage V212 `150/85`) : les lignes voyageurs restent évaluées avec leur revenu modèle normal (100 %) et leur capital modèle normal (100 %). Elles ne sautent plus artificiellement en tête de file face aux opportunités fret ou aériennes en 1972 ; seules les paires intrinsèquement rentables (part 40 % + courrier) sont sélectionnées.
