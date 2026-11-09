# Tâches — registre actif OpexAI

**Mise à jour : 4 novembre 2026 — ajout du diagnostic INVEST-STALL quais ; état historique du 27 octobre conservé. Seule liste autoritaire des actions ouvertes.**
Les décisions et résultats terminés sont dans la [synthèse historique](journaux/synthese_decisions_2026-09-30.md)
et les [journaux](journaux/README.md). Les anciennes mentions « à faire » des fiches
ne créent pas une tâche. Protocole et pilotage des bancs : [AGENTS.md](../AGENTS.md), §4/§4.1.
Classement des cases encore ouvertes (effort, dépendances, besoin de banc,
risque) : [ordre de clôture du 26/10](classement_taches_20261026.md).

### 04/11 — RAIL-SIBLING + RAIL-OPEN : adoption explicite utilisateur

Décision utilisateur du 04/11 : adopter sur `master` **`rail_sibling=1` et
`rail_open=1`** aux quatre difficultés. Les autres prototypes ferroviaires
RAIL-LONG v2/v3, INVEST-STALL et DOUBLE-GROW restent absents de cette intégration
et désactivés. Origine du comportement : bundle figé
`rail_open_railseul_40x5_20261102` (`c440c5cc327742daa91d3c4febcb5f3e431e5767712e587531905a4e08287bd8`),
intégré avec le code courant de `master` en conservant les réparations de quai
déjà présentes. Sous rail seul contre AAAHogEx rail seul, 40×5 : 1 597 978
contre 1 980 131 £/an (80,70 %) ; 20×10 : 1 787 861 contre 3 772 393 £/an
(47,39 %). Ce sont des résultats de l'ancien arbre expérimental, **pas** une
qualification économique du défaut nouveau sur le `master` actualisé : la porte
A 40×5 échouait (`fail_primary`, p = 0,468), la porte B 20×10 passait seulement
`non_erosion`, garde de valeur neutralisée. L'adoption intervient donc **sur
instruction explicite**, malgré l'absence de preuve statistique de gain propre.
Rapports repris dans ce dépôt : [RAIL-OPEN](rail_open_20261102.md) et
[RAIL-SIBLING](rail_sibling_lot1_bancs_20261102.md). Conserver les JSON/manifestes
et le SHA du bundle d'origine.

Validation de l'intégration sur la base `558f5bd8` (master du 04/11) : 29 tests
ciblés réussis ; smoke réel 1 graine × 1 an `rail_sibopen_promoted_smoke_20261104_r2`
2/2 jeux sains, défauts effectifs `rail_sibling=1`/`rail_open=1`, zéro erreur
NoAI, bundle `347f93985dad41161d4b920ed6a6d30b4a8e3b7c319b8454cf756e7b4113ae8b`.
**Contrats historiques à réconcilier :** la suite complète donne 3 563 tests,
129 échecs et 17 erreurs dans le worktree intégré (AAAHogEx installé localement),
contre 3 541 tests, 118 échecs et 29 erreurs sur le master témoin propre sans
AAAHogEx local ; 12 échecs supplémentaires correspondent à des attentes de bytes
ou de projections historiques incompatibles avec la nouvelle insertion du code.
Ne pas réécrire les anciennes fixtures pour les masquer. La validation globale
reste en échec ; le smoke ne démontre pas la rentabilité économique.

**État réconcilié le 30 octobre 2026, depuis `origin/master` (`7ae0cc05`).** Cette page est **l'unique liste d'actions ouvertes**. Une case cochée signifie que l'**étape est close**, pas nécessairement qu'un prototype est adopté. Une expérience rejetée ou suspendue n'est pas un chantier automatiquement réactivable, **sauf nouvelle instruction explicite** comme la réouverture des réparations RAIL ci-dessous.

L'ancien registre intégral (2 874 lignes, y compris hypothèses, essais, décisions et anciennes instructions) est conservé dans le [journal de transfert du 30/10](journaux/journal_2026-10-30_transfert_taches.md), avec une empreinte SHA-256 et les numéros de ligne d'origine. Le [bilan de réconciliation du 30/10](journaux/journal_2026-10-30_mise_a_jour.md) indique pourquoi les items ont été clos, séparés ou maintenus. Les fiches expérimentales restent des **photographies de leur date**, pas des consignes courantes. Pour les procédures, suivre [AGENTS.md](../AGENTS.md).

### 04/11 — ROAD1Y route seule : bilan des 02-04/11

Synthèse des travaux route seule menés du 02 au 04/11/2026 pour réduire l'écart avec AAAHogEx à 3 ans.

**1. Réglages adoptés par défaut (route seule) et leurs portes :**
- `road1y_astar=4` (02/11, commit `3c863206`) : A* routier pour liaisons bus-quartier 96–192 tuiles. Porte A 40×3 : +59,2 k£/an (32/8, p=4e-6, IC95 [38 ; 82] k, valeur +39 %) ; Porte B 20×10 : +58,9 k£/an (12/8, p=0,03, IC95 [18,6 ; 103,8] k, valeur +22 %). Optimum 2–4 confirmé par bancs (astar=8 : −15,0 k£ ; astar=2 : +14,3 k£, p=0,094 ; astar=1 : −26,5 k£).
- `road1y_gap=12` (03/11, commit `e728be6a`) : relèvement du plafond de fourgons courrier à 12 (au lieu de 2×arrêts) et saut de parent sans site. Porte A 40×3 : +16,4 k£/an (28/12, p=0,012, IC95 [2,0 ; 30,5] k, valeur +5,5 %) ; Porte B 20×10 : +201,1 k£/an (20/0, p=1,9e-6, IC95 [168,6 ; 237,2] k, valeur +50,5 %). Plateau 6–24 vérifié (gap=6 : +2,4 k£ ; gap=24 : −0,2 k£).
- `road1y_weak=15` (03/11, commit `e728be6a`) : réallocation mensuelle des bus des lignes faibles (<1,5 k£/bus) vers les lignes saturées. Porte A 40×3 : +22,6 k£/an (27/13, p=0,0098, IC95 [8,6 ; 36,7] k, valeur +9,3 %) ; Porte B 20×10 : +210,5 k£/an (18/2, p=1,3e-5, IC95 [148,8 ; 270,6] k, valeur +45,6 %). Cumul `gap=12 + weak=15` : Porte A +23,2 k£ (29/11, p=0,0037, IC95 [9,2 ; 37,0] k) ; Porte B +430,5 k£/an (20/0, p=1,9e-6, IC95 [372 ; 491] k, valeur +94,5 %).
- `road1y_mail2=5` et `road1y_mail2_years=3` (03/11, commit `e728be6a`) : baisse de la réserve de caisse courrier de 25 k£ à 5 k£ pendant les 3 premières années (pour éviter l'érosion à 10 ans observée avec mail2 seul à −89,5 k£). Porte A 40×3 : +23,8 k£/an (26/14, p=0,0047, IC95 [8,3 ; 39,0] k, valeur +23,5 %) ; Porte B 20×10 : +1,6 k£/an (11/9, p=0,87, IC95 [−58 ; +64] k, valeur −1,8 %, non-érosion tenue).
- `road1y_next=64` (03/11, commit `e728be6a`) : plancher de distance interurbaine à 64 tuiles pour privilégier les lignes longues à fort rendement. Porte A 40×3 : +39,2 k£/an (29/11, p=8e-4, IC95 [20,1 ; 58,5] k, valeur −0,8 %) ; Porte B 20×10 : profit +80,3 k£/an (14/6, p=0,09, IC95 [−20 ; 179] k), valeur −8,8 %. Adopté sur dérogation utilisateur de la garde de valeur 5 % (profit +80 k£, objectif rattraper AAA).
- `road1y_next3=56` (03/11, commit `e728be6a`) : crédit de 56 tuiles de voirie pour les paires PAX 96–127 tuiles. Porte A 40×3 : +30,2 k£/an (28/12, p=0,010, IC95 [7,0 ; 52,8] k, valeur −4,3 %) ; Porte B 20×10 : profit +36,8 k£/an (11/9, p=0,67, IC95 [−39 ; 119] k), valeur −9,3 %. Adopté sur dérogation utilisateur de la garde de valeur 5 %.
- `road1y_load_orders=1` (04/11, commit `558f5bd8`) : ordre `OF_FULL_LOAD_ANY` à la source PAX (comme AAA). Porte A 40×3 : +49,0 k£/an (34/6, p=8,7e-7, IC95 [33,9 ; 63,3] k, valeur +7,6 %) ; Porte B 20×10 : +281,9 k£/an (18/2, p=1,9e-5, IC95 [201,6 ; 361,7] k, valeur +10,0 %).
- `road1y_spread_stops=2` (04/11, commit `558f5bd8`) : arrêts bus joints répartis dans un rayon ≤12 tuiles pour étendre la zone de captage (style AAA). Porte A 40×3 : +69,5 k£/an (33/7, p=1,1e-4, IC95 [36,2 ; 101,6] k, valeur +17,0 %) ; Porte B 20×10 : +20,3 k£/an (9/11, p=0,90, IC95 [−50,9 ; 98,6] k, valeur +3,9 %).

**2. Leviers testés et rejetés :**
- `road1y_bridge` (wt-bridge, `f8023aec`) : ponts routiers pour débloquer les tracés A*. Porte A 40×3 : +0,4 k£/an (22/18, p=0,90, IC95 [−21 ; +22] k) ⇒ `fail_primary`.
- `road1y_far` (wt-far, `988fea38`) : ouverture des paires interurbaines >128 tuiles. Porte A 40×3 : +8,8 k£/an (25/15, p=0,23, IC95 [−7,2 ; +24,7] k) ⇒ `fail_primary`.
- `road1y_rich_fleet=10` (wt-richfleet, `0a16d948` sur astar=4 : Porte A −9,8 k£/an, 14/26, p=0,07 ; wt-richfleet2, `48e27039` sur load_orders=1 : Porte A −1,3 k£/an, 20/20, p=0,87) ⇒ neutre/négatif.
- `road1y_berth_fleet=3` (wt-berth, `d525c1f4`) : arrêt sans réserve 50 k et renfort style AAA. Porte A 40×3 : +11,5 k£/an (21/19, p=0,11) ; réplique 80 paires : +8,9 k£/an (2,8 %, p=0,10) ⇒ rejeté.
- `road1y_mail_next=7` (wt-mailnext, `dc72a253`) : Porte A 40×3 : +6,4 k£/an (21/18/1, p=0,50) ⇒ rejeté.
- `road1y_mail_min=15` (wt-mailmin, `989a2fa6`) : suppression des fourgons sous 15 sacs d'attente. Smoke 3 graines : −45 k£/an (fourgons 94→46, détruit du cash net car un fourgon à 1,4 k£/an reste rentable) ⇒ rejeté.
- `road1y_mail_full` (`ca83c0a7`) : chargement complet des fourgons courrier. Porte A 40×3 : mail_full=3 −4,5 k£ (19/20) ; mail_full=1 −8,2 k£ (16/23) ⇒ échec (attente paralysante).
- `road1y_dest_full=1` (wt-destfull, `537c3d44`) : chargement complet également à destination. Smoke 3 graines : −29 k£/an (3/3 négatives) ⇒ rejeté (source seule = optimum).
- `road1y_spread_mail=2` (wt-spreadmail, `9bfc0bda`) : arrêts courrier joints multiples répartis. Porte A 40×3 : −0,0 k£/an (19/21, p=0,93, valeur −1,8 %) ⇒ `fail_primary`.
- `road1y_mail_pick=20` (wt-mailpick, `760ba36e`) : sélection des parents courrier par production de courrier (≥20 sacs). Smoke 3 graines : −27,0 k£/an (0/3) ⇒ rejeté.
- `road1y_pax_bilat` (wt-paxbilat, `00e64762`) : renfort de bus conditionné au min d'attente bilatéral. Porte A 40×3 : +9,7 k£/an (20/20, p=0,55, IC95 [−9,5 ; 29,6] k) ⇒ `fail_primary`.
- `road1y_site_relocate` (wt-sitelost, `52a7e0ec`) : relocalisation de site bus perdu à ≤6 tuiles. Porte A 40×3 : −4,2 k£/an (14/26, p=0,29) ⇒ `fail_primary`.
- `road1y_mail_net=12` (wt-mailnet, `fb959178` + `396c95d3`) : réseau intercités courrier autonome v1 (smoke 138/317/189 vs 177/364/322 k£/an, 23 NO_TRACE) ; mail_net v2 (`35332753`, tracé voirie bus) smoke 166/292/233 vs 177/364/322 k£/an ⇒ rejeté (éviction de capex : voirie dédiée 15–25 k£ à payback 6–8 ans siphonne la caisse des bus à payback <1 an).
- `road1y_next2` (`a67f0f7f`) : bonus fundScore pour paires >N tuiles. Porte A 40×3 : =64 −303 k£, =96 −295 k£ (TRACEX bloque le créneau) ⇒ abandonné.
- `road1y_retry` (`7cacb7ed`) : réessais dans le même créneau après échec PAX. Porte A 40×3 : =2 −0,0 k£ ; =4 +3,9 k£ ⇒ neutre, rejeté.
- `road1y_freight` (`28b62b3a` et `af087da9`) : relèvement plafond camions et ×2 profit estimé fret. Porte A 40×3 : +5,4 k£/an (17/23, p=0,91) ⇒ neutre, rejeté.
- `road1y_abandon_days=60` (wt-abandon, `2e1b131e`) : bannissement de paire ramené de 365 à 60 j. Smoke 3 graines : −22,0 k£/an (1/3) ⇒ rejeté.
- `road1y_pax_min` (cloud, `ac4a78b2`, branche `cloud/road1y-paxmin`) : paires PAX estimées vers 2×min(captage A, B) comme AAA. Porte A 40×3 : =100 −11,6 k£/an (15/25, p=0,38, IC95 [−48,6 ; 24,7] k) ; =50 −2,9 k£/an (21/19, p=0,97, IC95 [−36,0 ; 29,9] k) ⇒ `fail_primary`, fil clos.
- `road1y_alt_load` (cloud, `a3246a97`, branche `cloud/road1y-altload`) : une part des bus PAX charge à plein au bout B. Smoke VPS sain (23/66 bus inversés, 3,0 contre 3,2 k£/bus). Porte A 40×3 : =33 +14,7 k£/an (25/15, p=0,23, IC95 [−10,5 ; 39,9] k) ; =50 +12,5 k£/an (25/15, p=0,18, IC95 [−11,8 ; 35,9] k) ⇒ `fail_primary`, sous le seuil de 20,7 k.
- `road1y_aaa_fleet=1` (cloud, `813f5c2a`, branche `cloud/road1y-aaafleet`) : gestion de flotte bus d'AAA portée d'un bloc (plafond par temps de trajet, ajout sur min(attente A, B), garde de 2 bus arrêtés, retrait). Smoke GitHub +9,7 k (4,7 bus/ligne contre 7,4). Porte A 40×3 : −22,7 k£/an (16/24, p=0,14, IC95 [−51,9 ; 6,4] k, valeur −9,4 %) ⇒ `fail_primary_and_value_guard`. Nos renforts « sans demande » rapportent ; fil flotte clos.
- `road1y_truck_fleet=1` + `road1y_freight=12` (cloud, `c4bb20bd`, branche `cloud/road1y-freightyield`) : flotte camions gérée comme AAA. Porte A 40×3 : +16,9 k£/an, médiane −6,7 k (19/21, p=0,38, IC95 [−9,9 ; 44,1] k) ⇒ `fail_primary`.
- `road1y_pair_fleet=8` (cloud, `2f9a4ffd`, branche `cloud/road1y-pairfleet`) : paires bus classées sur l'estimation à flotte mûre. Porte A 40×3 : +18,6 k£/an, médiane −5,6 k (19/21, p=0,63, IC95 [−16,6 ; 55,5] k) ⇒ `fail_primary`.
- `road1y_town_reuse=1` (codex, `caa68552`, branche locale `road1y-town-reuse`) : nouvelles paires bus dans des villes déjà desservies (arrêt joint, ≤ 3 lignes par ville). Smoke : 21 lignes de ce type construites. Porte A 40×3 : −38,3 k£/an, médiane −39,6 k (16/24, p=0,0098, IC95 [−65,3 ; −11,8] k, valeur −6,0 %) ⇒ nuisible, rejeté.
- `road1y_freight_adm=15` (agy, `50d2c132`, branche locale `road1y-night`) : admission fret. Porte A 40×3 : +12,2 k£/an, 20V/20D, p=0,48, IC95 [−10,3 ; +35,2] k ⇒ fail_primary, neutre ; défaut 0.
- `road1y_alt_load_cond=20` (agy, `8bc24a28`) : chargement complet conditionnel B. Porte A 40×3 : −115,2 k£/an, 5V/35D, p=1,6e-9, valeur −23,3 % ⇒ nuisible, rejeté.
- `road1y_loan_floor` (LOAN-1, `78918abd`) : −268 k£/an ⇒ mort (l'IA dépend de la dette de 300 k£ comme capital).
- `road1y_mail_p2p=10` (agy, `63b6c2aa`/`5ff4f241`/`1fbd7532`, branche locale `road1y-night`) : lignes courrier point à point autonomes. Version initiale : 0 ligne ouverte (boucle sans curseur, `attempts>4`) ⇒ banc nul. Après curseur : 4 lignes/13 fourgons sur 40 parties, toutes en 1972, 774 £/fourgon. Portes A 40×3 : défaut +6,9 k (23/14/3, p=0,15) ; `missing=30` +7,0 k ; `missing=45` +7,0 k ; `cash=20` +4,3 k ; `cash=20,start=7` +1,2 k (seuil +20,5 k) ⇒ fail_primary partout, aucune des gardes voirie/caisse/1970 n'est le goulot ; piste close, défaut 0. Reste inexpliqué : pourquoi si peu de paires s'ouvrent (sites, paires éligibles), journaux sous `decision_log=1` non faits.
- `road1y_mail_p2p` réécrit par codex (`ecd97b17` : sites multiples, curseur de paires, A* local, plein à la source, renfort sur capacité engagée) puis corrigé par agy (`c84d0500` : dépôt côté source, arrêts connectés, réglages `_cap`, `_maxdist`, `_noload`), branche locale `road1y-night`. Le levier ouvre enfin 121 lignes / 305 fourgons sur 25 graines (courrier +105,6 k£ en 1972, ~346 £/fourgon) mais les bus perdent 254 k£ (−24 lignes) : net +0,9 k£. Portes A 40×3 (seuil +20,5 k) : codex +0,9 k (21/16/3, p=0,85) ; + corrections dépôt/connexion +0,3 k (18/19/3) ; cap=1,maxdist=120 +2,9 k (20/17/3) ; noload=1 −3,3 k (18/19/3) ⇒ fail_primary, piste close, défaut 0. Non résolu : l'éviction des bus ne dépend ni de la cadence ni de la distance ; lignes ouvertes dans les trois dernières campagnes non comptées.
- Diagnostic lignes 1972 (agy, 04/11) : −38 k£/graine, moitié calendrier (caisse < 10 k£ de février à mai absorbée par les renforts, 31 % des ouvertures au T4), moitié rendement mensuel (864 contre 1 578 £/ligne) ; aucun levier calendrier au-dessus du seuil.
- Réglages fins testés et non retenus : `astar=8` (−15,0 k£) et `astar=1` (−26,5 k£) vs 4 ; `gap=24` (−0,2 k£) et `gap=6` (+2,4 k£) vs 12 ; `weak=25` (−11,2 k£) et `weak=8` (−6,6 k£) vs 15 ; `next=96` (−19,1 k£), `next=48` (−1,6 k£) et `next=80` (−14,3 k£) vs 64 ; `next3=28` (+5,7 k£) et `next3=80` (−27,2 k£) vs 56 ; `mail2=2` (−10,0 k£) vs 5.

**3. État de l'écart à 3 ans et diagnostics :**
- Profit terminal an 3 (campagne 40 graines `n_spread2_gateA` sous `load_orders=1` + `spread_stops=2`) : OpexAI 527,5 k£/an (médiane 541,9 k£) vs AAAHogEx 715,9 k£/an (médiane 705,6 k£), soit un ratio de 73,7 % (≈ 74 %). Écart résiduel moyen : −188,3 k£/an.
- Décomposition de l'écart total (−188,3 k£) :
  - **Bus PAX (−94,5 k£, 50,2 % du retard) :** 378,6 k£ vs 473,1 k£. Opex possède plus de bus qu'AAA (100,2 vs 85,9 bus/graine), mais un rendement unitaire inférieur (3 778 £ vs 5 509 £/bus) ; 9,2 % des bus d'Opex ont un profit annuel nul ou négatif.
  - **Courrier MAIL (−51,0 k£, 27,1 % du retard) :** 134,1 k£ vs 185,1 k£. Opex déploie 73,4 fourgons (1 826 £/f) contre 60,0 chez AAA (3 086 £/f) ; attente moyenne de 10,9 sacs (médiane 5) vs 44,5 sacs (médiane 15) ; AAA livre +59 à 65 % de courrier en plus.
  - **Camions Fret (−45,0 k£, 23,9 % du retard) :** 1,4 k£ vs 46,4 k£. Opex a 0,45 camion/graine contre 45,0 camions chez AAA (3 lignes charbon/bois par graine).
- Enseignements des diagnostics :
  - *Paires communes à parité :* sur les 48 paires de villes communes (1,2 paire/graine), le profit par ligne est strictement identique (39,4 k£ Opex vs 39,7 k£ AAA). Le retard historique de captage est comblé par `spread_stops=2`. En revanche, Opex y consomme 8,75 bus contre 6,81 chez AAA (flotte excédentaire).
  - *Topologie :* AAA ne construit aucun réseau en étoile (96,4 % de villes à 1 seule ligne, 0 ville ≥ 4 lignes). Ses paires sont simplement 10 tuiles plus longues en moyenne (105,6 vs 95,7 tuiles) entre villes de taille comparable.
  - *Caisse 1972 non bloquante :* les 157 k£ de trésorerie oisive fin 1972 (vs 15–20 k£ chez AAA) ne traduisent pas un blocage du capital. Les graines les plus riches (>300 k£ de caisse, n=8) sont les plus rentables (profit moyen 619 k£ vs 410 k£ pour les graines <15 k£). Les refus par caisse >50 k£ proviennent d'artefacts intra-cycle après constructions multiples, de `SITE_LOST` (365 j de bannissement) et du plafond de 4 lignes par ville. Piste identifiée mais sous seuil 4 % : `LOAN_REPAY_FLOOR` 300 k → 50 k (gain intérêts d'emprunt ≤ 12 k£/an).
  - *Courrier clos :* 78 % des lignes courrier d'AAA sont sans bus (dédiées). Mais tenter un réseau autonome dédié (`mail_net`) détruit du profit par éviction du capex bus. Le chargement complet (`mail_full`) paralyse les fourgons, le captage joint (`spread_mail=2`) est neutre, et les filtres de stock/rendement (`mail_min`, `mail_pick`) réduisent le cash net. Le gisement courrier à 3 ans est saturé et clos.

**4. Pistes encore ouvertes :**
- Rendement des paires exclusives d'AAA : les paires exclusives d'AAA rapportent 30,2 k£ (5,1 bus) contre 25,1 k£ chez Opex (7,3 bus). Piste `road1y_spread_cap` (plafond de flotte sous arrêts multiples) non lancée : le plafond large explique peut-être une part du gain de `spread_stops=2`, et retirer des bus à profit nul ne libère que de la caisse déjà oisive. Analyse comparative du code d'AAA confiée à une session cloud (branche `cloud/road1y-pack-0411`, `docs/cloud/road1y_0411/PROMPT.md`).
- Fret routier AAA : AAA déploie 45 camions (charbon, bois) pour 46,4 k£/an, quasiment absent chez Opex (écart de 45 k£/an).
- Durée de bannissement des paires : réduction du cooldown `ABANDON_COOLDOWN_DAYS` (actuellement 365 jours après `SITE_LOST`) pour réévaluer plus rapidement les paires viables (en cours d'exploration).

### 03/11 — `road1y_mail2` codé, défaut 0, mesuré et qualifié (03/11)

Diagnostic route seule (run GitHub 41550787847, graines 100 / 613553 / 781335,
`road1y_gap=12`, `weak=15`, `next=64`) : le poste MAIL au 1972-12-01 est
~234 k£ de `profit_this_year` (179 / 297 / 225). La réserve 25 000 £ de
`OpexRoad1yMailStep` et `OpexRoad1yRefleetMailLine` (`bus_districts.nut`)
bloque créations et renforts dès que la caisse résiduelle passe sous ~30 k£.
`road1y_mail2` (0..25, défaut 0, forcé à 0 hors route seule) peut seulement
abaisser cette réserve. Valeur conseillée 5, aucun banc. Pas d'adoption,
pas de push. Rapport hors dépôt.
**Mesure et qualification (03/11) :** `mail2=5` seul Porte A +23,8 k£ (p=0,0047),
mais échec Porte B à 10 ans (−89,5 k£) ; qualifié en combinaison avec
`road1y_mail2_years=3` (Porte A +23,8 k£, Porte B +1,6 k£ sans érosion) ;
adopté par défaut (mail2=5, mail2_years=3) sur `road1y-defaults` (commit `e728be6a`).

### 02/11 — `road1y_gap` codé, défaut 0, mesuré et qualifié (02-03/11)

Diagnostic route seule, master `3c863206`, `profit_year` au 1972-12-01
(4 trimestres) : graines 100 / 613553 / 781335, Opex 177 / 364 / 322 k£
contre AAAHogEx 532 / 792 / 599. Le levier non réfuté le plus large est
le MAIL (plafond 2 fourgons, parent sans site). `road1y_gap` (0..30, défaut 0,
forcé à 0 hors route seule) lève ce plafond et saute un parent sans site.
Valeur conseillée 12, aucun banc ici (un banc tournait déjà). Pas d'adoption,
pas de push. Rapport hors dépôt : diagnostic de cette session.
**Mesure et qualification (02-03/11) :** Porte A 40×3 +16,4 k£/an (p=0,012),
Porte B 20×10 +201,1 k£/an (p=1,9e-6) ; cumul `gap=12 + weak=15` qualifié
(Porte A +23,2 k£, Porte B +430,5 k£) ; adopté par défaut à 12 sur `road1y-defaults` (commit `e728be6a`).

### 01/11 — `road1y_long_v3` codé, défaut 0, non qualifié

`road1y_long_band=2` (porte A 40×3, `fail_primary`, profit_year moyen
−2 014 £, 19/21) a bien produit des lignes ≥96, mais en remplaçant la
bande fret 64-128 : le `break` de la première bande non vide
(`candidates.nut`, `po01c_regen.nut`) saute le fret 64-95 (132 → 5 lignes).
Le PAX 128+ créé par le tracé 192 est rentable à 4 bus et ouvert dès 1970.
`road1y_long_v3=1` ne fait que porter `ROAD_MAX_TRACE_TILES` à 192 en
gardant les bandes 64-128, 32-63, 7-31. Intégré sur `road1y-mail-rebased` :
défauts `road1y_mail_on_pax=1` et `road1y_long_v3=1` aux quatre difficultés,
avec garde route seule (comme `ROAD100_SOLO_PAX`) : hors `mode_road` seul,
chaque `ROAD1Y_*` reprend la valeur master. Aucun banc. Pas de push.

### 29/10 — corrections de revue B2 et diagnostic des variantes a/c

Partie 1 `8ff35570` : projection Save reconstruite hors Save, maintenance des
marqueurs après reprise OFF, exclusion pending, exception LIVE et ordres du
refleet sans modèle. Échec du lancement précédent identifié : affectation de
méthode Squirrel par `=` au lieu de `<-` ; campagne corrigée saine.
Nouveau masque `road1y_bus_fixes=0` : 1 quais passagers, 4 distance ≥30,
8 deux quartiers par ville. **Aucune adoption, objectif économique non atteint** :
meilleure combinaison essayée sur 17 = 29 914 £, mais moyenne des quatre autres
77 249 £ contre 81 701 £ au JOINED témoin final. Le repli baie demandé sous
condition n'est pas codé : diagnostic de couverture contraire à la cause supposée.
OFF final identique sur 130 observations hors provenance ; 230 contrats ROAD100
OK (3 ignorés), 7 V251 OK, Save/Load court OK. ON→OFF effectif et projection ≥64
lignes restent non exposés au moteur. Bancs limités à un an, aucun push.
[Rapport et tableau par graine](road1y_busB2_fix_20261029.md).

### 29/10 — ROAD1Y-B2, reprise bus explicitement demandée, limitée à un an

Branche `road1y-bus-sites`, parent `4354cafa`. Refonte des quartiers bus et
quais joints derrière `road1y_pax_sites=0` / `road1y_extra_stops=0` ; C/D restent
OFF. Cinq graines 17/2026/12345/1337/100, aucune porte A/B : moyenne terminale
du harnais **58 369 £ sites seuls**, **69 430 £ sites + deux quais joints**,
contre seuil historique A **54 031 £** et témoin du même arbre **51 193 £**.
Les quinze parties finales sont saines ; OFF reproduit le parent sur les cinq
graines. Forte régression sur 17 (**19 631 £** avec quais) : résultat descriptif,
aucune adoption. Les profits de cette première année couvrent trois trimestres
clos. Save/Load court sain ; le cas projection ≥64 lignes reste vérifié par
contrat, non exposé au moteur. [Diagnostic, preuves et limites](road1y_busB_20261029.md).
La demande présente n'autorise aucune poursuite au-delà d'un an ni changement
des défauts ; elle ne rouvre pas les autres travaux ROAD100 arrêtés.

### 28/10 — ROAD100 arrêté sur demande utilisateur ; bilan consolidé

**ROAD100 arrêté : 0/5 parités H1–H5.** Ne pas reprendre de travaux ROUTE,
de smokes ni de Gate A sans nouvelle instruction explicite. Les améliorations
techniques n'ont pas fermé l'écart de `profit_year` réel avec AAAHogEx.
Résumé de toutes les familles, mesures et erreurs corrigées :
[bilan d'arrêt ROAD100](road100_bilan_arret_20261028.md).
Le prototype V37 est non intégré et non testé dans OpenTTD ; aucun défaut
n'a changé. L'archive est publiée sur la branche `archive/road100-20261028`,
sans adoption de mécanisme ; les preuves historiques restent conservées.

### 28/10 — ROAD100-36 sites AIR/RAIL et tracé local : NO-GO 0/5

- [ ] **ROAD100-36 reste 0/5, aucun LONG physique supplémentaire.**
  Dernières améliorations de `origin/master 12e4d39f` lues après
  `git fetch` **sans merge** : classement natif des sites AIR, repli
  ferroviaire EB-2, gorge V233L et recherche RAIL multi-sources
  reprenable. Principes du routage AAAHogEx étudiés **sans copier son
  code** ; AAAHogNet absent du dossier `ai/` inspecté.
  Sous le même opt-in GRAPH défaut0, un classement de voies réellement
  connectées sur deux arêtes intervient **avant** le Top-3 de couples
  de sites. Le smoke
  `road100_v36_railair_site_rank_axis_roadonly_seed42_1x1_20261028`
  (bundle `bebee153bfbe68066be40589039c5e877aeabfdcc7d95d90f5bcf7f6c34bf143`)
  produit scores 8/4 et modifie les sites, mais la vérification OpenTTD
  refuse d63 index21/5 `error260`, d68 index18 `error1281`.
  Le détour A* local RAIL-style, après correction d'une compilation
  invalide (`parent` réservé), est validé par 3 260 tests et trois
  smokes moteur sains. Le dernier
  `road100_v36_rail_local_repair_arith_roadonly_seed42_1x1_20261028`
  (bundle `cf675df6682af97d0d663550e42c8c28c5668703b59dd16e2879c5b9c2b21bc7`)
  explore **14 nœuds / 36 états / 18 209 opcodes**, puis
  `REPAIR_OPCAP` sans alternative ni LONG. `profit_year` H1 réel :
  Opex OFF/ON **20 797/19 106 £/an**, AAA OFF/ON
  **94 472/93 008 £/an** ; **NO-EXPOSURE / NO-GO, 0/5**.
  Les micros détours locaux sont clos. Priorité ouverte : **routage
  routier reprenable en tranches comme RAIL**, sites alternatifs
  physiquement accessibles, état PO01C/Save-Load, devis complet,
  C75/C78/TopK et construction réelle avant 5×5/Gate A40×5.
  Tous bundles/dirty tree préservés, aucune publication Git.
  [Preuves et préenregistrements](road100_graph_bridge_prereg_20261028.md).

### 28/10 — ROAD100-36 Graph-Bridge, premier smoke NO-EXPOSURE

- [ ] **ROAD100 0/5**, poursuite structurelle après V21 et V35. Une unique
  famille opt-in `road100_pax_graph_bridge` (défaut `0` aux quatre difficultés,
  strictement ROUTE seule) relie les vrais sites PAX des villes d43..170 par
  segments routiers existants et raccordements locaux bornés. Le traceur ne
  crédite aucune arête hypothétique : préflight complet des voies/quais/dépôt,
  coût de route/fleet et caisse puis revalidation et chantier transactionnel.
  Candidats, PO01C/synchrone, calcul de PASS/mois et C75/C78/TopK partagent
  l'admission standard. Préenregistrement :
  [ROAD100-36](road100_graph_bridge_prereg_20261028.md).
  **Premier smoke apparié validé techniquement mais NO-EXPOSURE/NO-GO** :
  `road100_v36_graph_bridge_roadonly_seed42_1x1_20261028`, même bundle
  `2ad6cc3310e0bfe3adc07e1a87f0fc2e30aeec78283f50ec6226ff9642b13be4`,
  deux parties `complete`, six tentatives GRAPH, aucune trace candidate ni
  ligne LONG admise, huit `ROAD_BUILD` dans chaque bras. Échecs du traceur
  `GAP_LOCAL_NODE_CAP`, `GAP_OPCAP`, `COUPLE_OPCAP` ; c'est l'exploration
  physique sous budget, non la demande, qui bloque AVANT devis/admission.
  H1 `profit_year` Opex référence **20 797 £/an**, V36 **19 106 £/an**,
  AAA référence **94 472 £/an**, AAA dans la partie variante
  **93 008 £/an** ; ON−OFF **−1 691 £/an**, **0/5**.
  Suite intégrale **3 251 OK** (5 skipped, 2 expected failures), contrats
  V36 17 OK, projection OFF 2 OK, V262 33 OK, `git diff --check` OK.
  Le premier V36 ne justifie ni 5×5 ni Gate A. Une correction causale
  **dans la même famille GRAPH-BRIDGE**, sous le même opt-in, vise le coût
  par expansion locale et les faux rejets de graphe ; nouveau bundle/smoke
  apparié requis après nouveaux tests, sans prétendre 5/5.
  **Deuxième smoke suite au cache directionnel** : campagne
  `road100_v36_graph_bridge_gapcache_roadonly_seed42_1x1_20261028`, bundle
  `43347b47fb0aa2ea1b3b9cc031940b41269fec5641c2cf6e9add3ae34aed9d3b`,
  suite **3 253 OK**, 19 contrats GRAPH, OFF préservé. Deux parties
  `complete`, six recherches GRAPH, **zéro trace complète**, zéro LONG.
  `GAP_LOCAL_NODE_CAP` 7 expansions/27 532 opcodes,
  `GAP_OPCAP`, `SLEEVE_*_OPCAP` et `COUPLE_OPCAP`. H1 Opex ON
  **19 072 £/an** contre OFF **20 797 £/an**, AAA ON **98 965 £/an** ;
  delta **−1 725 £/an**. Deuxième **NO-EXPOSURE/NO-GO**, 0/5.
  La prochaine correction préenregistrée est une liaison géométrique
  orthogonale sleeve-to-sleeve à faible coût, toujours revalidée par les
  mêmes tests physiques et financiers ; aucun 5×5/40×5 tant que zéro
  nouvelle ligne productive.
  **Troisième puis quatrième smoke V36, tous deux NO-EXPOSURE/NO-GO** :
  `road100_v36_fastbridge_roadonly_seed42_1x1_20261028` (bundle
  `6c0bb06556c6b2178311a38cf7fa11499c48b077c23bf39ef8520f8e79729e52`)
  et `road100_v36_fastbridge_lowops_roadonly_seed42_1x1_20261028`
  (bundle `f2b03291e4a3665f8b04c961b26b0b901b9e5398e4e142ba2647a81826b456f9`).
  Les deux : 2 parties `complete`, 0 trace et 0 corridor LONG, Opex OFF
  **20 797**, ON **19 072** £/an, AAA OFF **94 472**, ON **98 965**
  £/an, delta **−1 725 £/an**. Troisième : 3 254 tests OK ; quatrième :
  3 254 tests OK, `fast_ops=6346/6103` et `FAST_OPCAP` après 2–3
  géométries malgré la suppression des sondes natives par case.
  Aucun gain de société ni 5×5 autorisé. **ROAD100 = 0/5**.
  Le cinquième diagnostic V36 est préenregistré pour révéler le motif de
  rejet par géométrie et le premier éventuel `AITEST_BUILD_ROAD`,
  sans élargir aucun budget ni contourner le vérificateur.
  **Cinquième–septième smokes V36** :
  `road100_v36_fastbridge_variant_diag_roadonly_seed42_1x1_20261028`
  (bundle `39b87b2e101b8389f2c29eeecbb8a97c2f09fe1cdd6ed88d1ae5c77bea987998`),
  `road100_v36_fastbridge_prefilter_roadonly_seed42_1x1_20261028`
  (bundle `6111b49632f5727b1653556bab657fa033eac6f9cad08620670ecfccc1bea069`)
  et `road100_v36_fastbridge_monotone_roadonly_seed42_1x1_20261028`
  (bundle `a410bc6752c2059d5f8fbc13372f22fc1a2c521f85c7f9aa940abfcd72c08791`) :
  toutes parties `complete`, **0 trace validée / 0 LONG**, profit ON
  **19 072 £/an** contre AAA **98 965 £/an**. Diagnostics causaux :
  collisions de sleeves, virages non admissibles et matérialisation
  à `8588` opcodes au-delà du cap FAST 8k. Tests intégraux 3 255
  puis 3 256 OK, projection OFF conservée.
  **Huitième smoke single-pass** :
  `road100_v36_fastbridge_singlepass_roadonly_seed42_1x1_20261028`,
  bundle `4978f8b99392233a4e0dfd627fd3156efe2c4b47dee7e5b18dde0de3d10483d7`,
  3 256 tests OK et duel `complete/complete` : **première trace
  FAST de 154 arêtes, 6 534 opcodes**, mais validation moteur
  `AITEST_BUILD_ROAD index=1 from=32674 to=32673 error=260`
  (`ERR_AREA_NOT_CLEAR`) ; aucun quai/dépôt/ligne LONG construit.
  H1 Opex OFF/ON **20 797/19 072**, AAA OFF/ON
  **94 472/98 965 £/an** ; Δ **−1 725 £/an**, **ROAD100 0/5**.
  Suite causale en cours dans la même famille V36 : dogleg court autour
  de la première arête refusée, chaque alternative repasse le
  vérificateur entier, devis et chantier inchangés. Ni 5×5 ni Gate A
  avant construction rentable démontrée.
  **Neuvième–dixième smokes FrontDogleg** :
  `road100_v36_graph_frontdogleg_roadonly_seed42_1x1_20261028`
  (bundle `22f5e6440de0d2eb9215723a425b7534cf17d917e161d21a3083dc206986ba07`)
  puis `road100_v36_graph_frontdogleg_widefirst_roadonly_seed42_1x1_20261028`
  (bundle `327fa2b932bede175f655c89df0ed4e3f99e2cbb735a515d815da9a7081e3b78`).
  Suites intégrales **3 257 OK**, OFF exact, V262 inchangée et
  parties `complete/complete` ; les détours 1..3 échouent tous à
  `AITEST_BUILD_ROAD error260` au départ (largeur3 index4, largeur2
  index3), sous la réserve de 50k. Aucune route LONG admise/construite,
  d63 `GRAPH_NO_TRACE`, aucun PASS LONG supplémentaire.
  H1 OFF/ON Opex **20 797/19 106**, AAA **94 472/93 008 £/an**,
  delta Opex **−1 691 £/an** : **NO-GO, 0/5**.
  Priorité suivante : accès physique réel des sites, plusieurs marchés
  d43..80 et d80..160, corridors économiquement finançables sous
  42k/180k/400k opcodes, sans A* LONG ni nouveau défaut.
  **Onzième smoke access-priority** :
  `road100_v36_access_priority_roadonly_seed42_1x1_20261028`,
  bundle `515d788d497f5b5c2be3716ad7f6c0e23452dc87bcf3c7b5784796c9de24d71a`,
  3 258 tests OK, deux duels `complete`. Le classement choisit réellement
  deux marchés intermédiaires d63 et d68, sorties de quais prouvées ;
  FAST trace 77 puis 71 arêtes sous 8k opcodes, mais vérification physique
  rejette index8 `59976→59720 error260` et index18 `38564→38820
  error1281` (type exact à identifier ; code municipal réel 2307).
  Zéro LONG admis ou construit.
  Opex H1 OFF/ON **20 797/19 103 £/an**, AAA OFF/ON
  **94 472/97 693 £/an**, delta **−1 694 £/an** ; **NO-GO 0/5**.
  Prochaine correction préenregistrée : détour Graph-only borné autour
  d'obstacles locaux au-delà des trois premières arêtes, vérifié par
  OpenTTD sans détruire de voies municipales et sans élever les caps.
  **Douzième smoke** `road100_v36_midtrace_dogleg_roadonly_seed42_1x1_20261028`
  bundle `859768f99ffc1c813fd696c649f53f685a7ea6e0cda2ce7c32762a256d1f55b0`,
  suite 3 258 OK, deux jeux complets, un seul réglage 0→1 : malgré
  les traces FAST 77/71, index8 error260 et index18 error1281 restent
  bloqués, et le helper étendu produit **0 détour admissible**.
  Aucune admission/construction LONG. Opex H1 OFF/ON 20 797/19 106,
  AAA OFF/ON 94 472/93 008 £/an : **NO-GO, ROAD100 0/5**.
  Priorité diagnostic : expliquer chaque refus géométrique du helper
  sous caps stricts, sans hausse de budget ni admission présumée.
  **Treizième–quinzième smokes** : géométrie instrumentée puis recul
  sur quatre arêtes planes, suites **3 258 OK**, bundles
  `fc4f3a4532496bb6b18c4a798f6c764647ca52f9fe6182efc89c25489d8e9b8d`,
  `ccce484adf2c60fe046d3c811e5a59a257ea6b51736551b28d46993d5331159d`,
  `e7cb66636924180e547bc134e87b3b9d348ff91f5ca2cb8758c9f8696d603cbf`.
  Le d63 révélait `NONFLAT_FIRST` pour six largeurs/côtés ; après
  recul d'ancre, cinq détours réels sont soumis à AITest complet,
  **tous refusés index4 depuis 61000 erreur260**, puis plafond
  partagé/reserve 50k. Le d68 reste bloqué index18/error1281,
  **distinct du vrai code municipal 2307**. Aucun LONG admis ni
  construit, pas de nouvelle livraison LONG, H1 dernier OFF/ON Opex
  **20 797/19 103**, AAA **94 472/97 693 £/an**, **NO-GO 0/5**.
  Poursuite structurelle nécessaire : nouveaux sites de sorties routières
  physiquement traversables, vraies routes existantes prioritaires,
  génération de plusieurs marchés rentables d43..80/d80..160, puis
  flottes et caisse sous devis et opcodes ; ne pas multiplier les
  mini-détours qui échouent sur la même première arête.

### 28/10 — ROAD100-35 Portal-Stitch : NO-EXPOSURE / NO-GO

- [ ] **ROAD100 0/5** : V35 `road100_portal_stitch=1` (défaut 0,
  garde ROAD-only + LONG + sparse) compilé et exécuté en moteur OpenTTD,
  après correction d'un identifiant Squirrel réservé `parent`.
  Suite complète **3 234 tests OK** ; duel valide seed42 1×1
  `road100_v35_portal_stitch_roadonly_seed42_1x1_syntaxfix_20261028`
  `complete/complete`, unique différence effective 0→1, source figée.
  Les deux vrais marchés ex ante 258/175 PASS/mois échouent en
  `NO_CORRIDOR` (`BAND_1_EDGE_OCCUPIED` et `BAND_10_GAP_TURN`) :
  **aucun LONG construit**, pas de PASS LONG livrés. H1 `profit_year` de
  société Opex **19 103 £** vs AAA **97 693 £**, ON−OFF **−31 £**,
  16 contre 55 véhicules. V35 **NO-EXPOSURE / NO-GO**, sans 5×5 ni Gate A,
  aucun défaut changé. Sources et limites :
  [rapport V35](road100_v35_portal_stitch_resultats_20261028.md).

### 28/10 — ROAD100-20/21 : exposition physique, puis levier fret multi-cargo

- [ ] **ROAD100 demeure 0/5**, aucune parité démontrée. V20d et V20e
  construisent de vrais satellites PAX (5 graines exposées avec
  `ROAD100_PAX_PORTFOLIO phase=build joined>=1` et `LINE_REVENUE`), mais
  V20e 5×5 affiche des ratios agrégés Opex/AAA **11,8 %, 6,5 %,
  4,0 %, 2,9 %, 2,3 %** aux horizons 1–5, 0/5 victoires chaque année.
  En 1974, seulement ~10 lignes et ~21 véhicules Opex contre ~52 lignes
  et ~493 véhicules AAA ; caisse Opex ~283 k£. V20d ON−OFF
  −11,7 k£/an et V20e −3,1 k£/an à cinq ans (aucune A40×5).
- [ ] **ROAD100-21 fret diversifié, défaut 0**, même sélection sur les
  chemins synchrone/PO01C (max 3 cargos fret par passe, sans scanner
  plusieurs fois PAX ou TopK), isolé à ROUTE seule et V276 désactivé.
  Combiné expérimentalement avec `road100_road_batch=1` (garde ROI 25 %,
  marge cash 50 k£, max 4 chantiers/passe). Smoke apparié
  `road100_v21_multifreight_batch_roadonly_2x1_20261028` sain 4/4 :
  plusieurs lignes `COAL`, `IORE`, `WOOD` construites, mais ON−OFF
  −5 105 £/an moyen à 1 an, 1V/1D et 0/2 parités contre AAA.
  Campagne 5×5 `road100_v21_multifreight_batch_roadonly_5x5_20261028`
  terminée 10/10 jeux sains, même bundle `918125aefc35ef2a8f` :
  ratios de profits annuels réalisés Opex ON/AAA de **13,4 %, 10,2 %,
  5,4 %, 3,4 %, 3,0 %** à 1–5 ans, **0/5 victoires** à chaque horizon.
  Le gain ON−OFF à cinq ans est **+14 976 £/an** (3V/2D,
  Wilcoxon p=0,4375, IC95 [−3 838 ; +34 422] £/an) ; valeur d'entreprise
  +29,3 % par rapport à OFF. Aucun A40×5 justifié. À cinq ans, environ
  **13 lignes et 28 véhicules** ON, contre **10 lignes et 21 véhicules** OFF
  et **49 lignes et 497 véhicules** AAA. Les 3 166 contrats Python sont
  verts (5 ignorés, 2 échecs attendus), fixture V262 historique intacte.
  Rapports `results/road100_v21_multifreight_batch_{5x5,reference_5x5}_summary.md`.
  Préserver les défauts OFF et poursuivre d'autres leviers sur profits
  *réellement réalisés*.
- [ ] **ROAD100-22 : origines fret indépendantes par cargo**
  (`road100_freight_cargo_origin=1`, défaut 0, ROAD seul, V276 inactif).
  Filtrage cohérent du vivier sync/PO01C et dernier contrôle de chantier ;
  une gare d'un autre cargo ne bloque plus l'origine mais le même cargo
  reste protégé. Smoke 1×1 sain. Diagnostic isolé 5×1
  `road100_v22_cargo_origin_isolated_roadonly_5x1_20261028` : **+199 £/an**
  de `profit_year`, **1V/0D/4E**, Wilcoxon p=1, valeur **−2,36 %**, 0/5
  victoires Opex/AAA. Quatre graines construisent les mêmes lignes que
  l'OFF ; aucune indication pour 5×5 ni A40×5. Les changements de ports
  demeurent opt-in et les tests de projection OFF restent stricts.
- [ ] **ROAD100-23 : second chantier ROI 15 %**
  (`road100_batch_roi_15=1`, défaut 0, nécessite `road100_road_batch=1`).
  Préenregistrement fondé sur V21 : parmi 41 refus de second chantier,
  ROI estimé médian 16,3 %, maximal 23,6 %, aucun refus dû au cash.
  Garde ROI historique 25 % conservée à défaut, fonds `projCap+50k£`,
  cap quatre chantiers, prix réel et constructeur inchangés. Smoke seed42
  +1 572 £/an mais valeur −12,18 %. Sur cinq graines ×1 an appariées,
  `road100_v23_batch_roi15_isolated_roadonly_5x1_20261028` :
  **+585 £/an**, **3V/1D/1E**, p=0,875, IC95 [−1 841 ; +2 566] £,
  **valeur −29,62 %**, 0/5 victoires contre AAA. Pas de 5×5 ni de porte A
  sans signal de valeur crédible. Les deux mécanismes sont des pistes
  expérimentales, non des parités acquises : **ROAD100 reste 0/5**.
- [ ] **ROAD100-24 : double quai fret physique sur ligne mature.** Nouveau
  réglage `road100_freight_berths=1`, défaut 0, ROUTE seule. Dans V21,
  41/41 constructions fret sont limitées à deux camions et 82/86
  observations fret matures montrent du stock ; 56/86 ont une demande
  de flotte brute supérieure à deux. V24 ne modifie **aucun candidat**
  ni score : exclusivement après une année bénéficiaire (profit réel
  >=3 k£/an, 2 camions circulants, stock source >=3 capacités), il
  recherche sur voirie existante un vrai quai de camion joint à chacun
  des deux StationIDs, AITest limité à 4, <=12 sites par bout, budget
  60 k opcodes, connectivité dans les deux sens, rollback des deux
  ajouts en cas d'échec, trésorerie >=50 k£, remise en cohérence des
  quais au refleet après Save/Load. Le renfort au plus +2 véhicules
  est borné par capacité et attente **post-construction**, prix réel,
  slots et trésorerie, aucun revenu présumé n'est ajouté.
  Premier smoke ROAD-only seed42/2026 2×2 sain : seed42 ligne0
  deux quais vrais (tiles19566/26737, même StationID que racines),
  prix réel **300£**, 16 670 opcodes, flotte **2→4**;
  seed2026 `NO_SITE`, 4 AITest/4 952 opcodes, zéro nouvelle gare.
  Sur ces deux graines à deux ans, ON−OFF **−8 693 £/an**, 0V/2D,
  valeur −4,44 %, Opex/AAA 13,58 %. Exploration appariée 5×5 terminée
  `road100_v24_freight_physical_berths_roadonly_5x5_20261028`, bundle
  `7c9097cc8a56d6dc3e` : 10/10 parties saines, **11 doubles quais construits**
  sur 5/5 graines, **22 camions** ajoutés physiquement. Profits annuels
  ON/AAA à H1–H5 : **13,5/9,8/5,4/3,7/3,2 %**, 0/5 victoires chaque année.
  Différence Opex ON−OFF H1–H5 : **+62/−1 412/−6/+6 672/+8 887 £/an** ;
  H5 **5V/0D**, Wilcoxon **p=0,0625**, IC95 [1 882 ; 16 362] £,
  valeur +7,39 % ratio des moyennes mais 2V/3D. 21 observations de lignes-
  années fret post-renfort appariées : différence agrégée de profit des
  véhicules **+82 159£** sur plusieurs exercices (non assimilable au
  gain annuel de société). Non-érosion H2/H3 non démontrée ; **aucune porte A**.
  Rapports `results/road100_v24_freight_berths_{5x5,reference_5x5}_summary.md`.
  Ne pas confondre stocks en gare et livraisons ; 0/5 reste ouvert.
- [ ] **ROAD100-25 : filtrage LIVE des projets bus périmés au classement.**
  Sur V21, **1 301/1 896** tentatives C78_BUILD répètent
  `town_already_bus_served`, dont >340 fois le même candidat seed100/1972.
  Les générateurs et `OpexCandidateStillValid` filtrent déjà les lignes
  présentes à l'instantané, mais la sélection PO01C republie parfois des
  projets de snapshots anciens : `OpexReselectProjects` ne revalide que l'AIR.
  Nouveau réglage `road100_pax_live_filter=1`, **défaut0, ROUTE seule** :
  au point commun sync/PO01C, retire les projets ROAD PAX dont les villes
  sont désormais servies, avant score/topK, sans toucher fret, rail,
  extension, exception `ROAD100_MULTICATCHMENT`, revenu, devis, valeur ou
  table des abandons. La garde du chantier demeure. Préenregistrement :
  comparer avec le même cumul ROAD100-21+24 (toutes autres options identiques),
  smoke apparié seed100/2026 puis diagnostic 5×5 si exposition, 40×5 uniquement
  si gain `profit_year` >=4 %, p<0,05, valeur >=−5 %, sans érosion H1–H4.
  Mesurer `ROAD100_PAX_LIVE dropped`, rejets C78 évités, PO01C/opcodes,
  lignes réellement construites, profits H1–H5 et AAA. Aucune conclusion
  économique ni adoption sans moteur. Premier pilote V25a 2 graines ×3 ans
  `road100_v25_pax_live_filter_roadonly_2x3_20261028` : 4/4 sains,
  ON−OFF H3 **−10 443£/an** (0V/2D), valeur −13,87 %, 0/2 parités.
  Le filtre retire des projets périmés (seed2026 : 1 252 mentions
  `town_already_bus_served` OFF contre 42 ON), mais ne déclenchait pas
  une réélection si le veto avait déjà lieu dans le constructeur.
  **V25b préenregistré avant replay** : après ce seul veto sous option ON,
  poser `_hadAbandonsThisPass=true` pour réélire au terme de la passe ;
  aucune clé abandonnée, aucun bump `lines`, pas de modification physique.
  Replay neuf `road100_v25b_pax_live_reselect_roadonly_2x3_20261028`
  terminé 4/4 sain sur bundle `5dd461e0c99b74a01b95` : ON−OFF H3
  **−10 246£/an**, 0V/2D, valeur **−11,48 %**, 0/2 parités AAA.
  Ni V25a ni V25b ne justifient une campagne 5×5 ou une adoption ;
  opt-in défaut0 conservé, priorité à des recettes et chantiers physiques.
- [ ] **ROAD100-26 : équilibrer le quai limitant de bus déjà rentables.**
  Préenregistrement avant code et moteur : V24/`LINE_REVENUE` montre des
  lignes PAX avec `nStopsA>=2`, `nStopsB=1`, **2 bus**, stock PAX réel
  (p.ex. seed2026 line8 : 1091/378 PASS, profit de ligne réalisé
  12 189£/an, stations A46533/B43738 ; seed100 line0 : 578/14 PASS,
  profit 9 206£/an, 3/1 arrêts). Aucune tuile additionnelle présumée
  constructible. Essayer sous `road100_pax_berth_balance=1`, défaut0,
  ROUTE seule, **au moins deux ans après ouverture, après exercice clos
  rentable**, et sur
  ligne physiquement existante : chercher dans le spread un arrêt bus
  traversant joint au StationID du côté unique, sur route déjà présente,
  AITest, connexion bilatérale, coût de caisse mesuré, rollback. Garder
  origine/destination, dépôt, ordres et stations d'origine ; préserver
  Save/Load, démolition externe, cap antérieur et réversibilité.
  Renforcer au plus +2 bus uniquement sous attente réelle de la ligne,
  prix moteur, cash restant >=50k, slots et cap **physique** désormais 4 ;
  aucun projet nouveau ni revenu de nouveau quartier crédité. Budget
  scanner <=12 sites, <=4 AITest, soft <=40k opcodes, <=2 tentatives
  par année et 1 seule réussite. Comparer apparié OFF/ON avec V21+V24
  identiques, premier smoke 2 graines×3 ans, puis 5×5 si vraies poses,
  et Gate A40×5 seulement gain >=4%, p<0,05, valeur >=−5%, sans
  érosion H1–H4. Mesurer `ROAD100_PAX_BERTH`, `ROAD_REFLEET`, `LINE_REVENUE`,
  transferts, profits de société et parités AAA. Premier smoke apparié
  `road100_v26_pax_berth_balance_roadonly_2x3_20261028` bundle
  `3235308a12c22e436d5a81d7d013a390c5fca92714bf0eac490735be155b8fab` :
  4/4 parties saines, vrais bus quais ajoutés seed100 line0 (tile31947,
  150£, 6708 ops, 2 bus→4), seed2026 lines6/8 (tiles39557/43226,
  152/151£, 7837/5084 ops, 2→4), `ROAD_REFLEET` réel. H3
  Opex ON **84 073£** contre OFF **69 210£**, delta **+14 862,5£/an**,
  1V/1D, p=1, valeur ON/OFF +25,35% des moyennes ; Opex/AAA
  **10,4 %**, zéro parité. H1 stable, H2 ON 65 087 vs OFF 55 730£.
  Puisque la construction est effective et qu'il existe un signal réel,
  poursuivre sans changer le code en diagnostic **5 graines ×5 ans**,
  NO-GO A40×5 jusqu'à examen de la non-érosion/statistique. Ce diagnostic
  `road100_v26_pax_berth_balance_roadonly_5x5_20261028` est **terminé**,
  bundle **identique** `3235308a12c22e436d5a81d7d013a390c5fca92714bf0eac490735be155b8fab`,
  10/10 sains : profits V26 ON 18 198/61 852/70 318/77 132/78 437£/an
  H1–H5, ratios Opex/AAA **13,5/11,2/6,5/4,6/3,7 %**, toujours
  **0/5 parités**. ON−OFF H5 **+9 121£/an**, 3V/2D,
  Wilcoxon **p=0,625**, IC95 [−9 505;+29 871]£, valeur moyenne
  +15,62 %. Signal vrai mais non significatif, **aucune porte A40×5**, option
  0 conservée. Rapports `results/road100_v26_pax_berth_balance_{5x5,reference_5x5}_summary.md`.
- [ ] **ROAD100-27 MAIL ville↔ville — nouveau marché route, préenregistré AVANT code.**
  Audit AAA strict ROAD-only V24 5×5 : **77 lignes autonomes MAIL** et
  99 PAX, surtout longues (MAIL distance médiane par graine ~88–107 cases) ;
  Opex V21 n'a construit qu'une ligne MAIL (fret d'industrie, pas un
  couple de villes), V24 ON aucune. Le catalogue connaît `mailCargo` et
  les fourgons (`roadEngineByCargo`), mais `catalog.producers` n'indexe
  que les industries : le trajet **town MAIL → town MAIL** est absent.
  Variante `road100_mail_intertown=1`, défaut0, ROUTE seule et
  `ROAD100_SITE_FIRST=1` ; génération **séparée** MAIL camion, sans
  toucher aux bus PAX, ni au fret industrie, ni à la politique OFF.
  Préfiltrer 16 villes selon production MAIL mensuelle observée et
  couples centre 12..42 (limite physique du planner court), puis
  **au plus 3 vrais plans avant admission**, <=200k soft opcodes : source
  qui PRODUIT du MAIL dans la couverture réelle du truck stop A,
  destinataire B qui l'ACCEPTE (>=8 unités de huitième) à son vrai site,
  `OpexRoadPlanFor` vérifiant tuiles de station, route et dépôt.
  Calculer le revenu uniquement sur `plan.stopA.value`, jamais sur la
  production totale de la ville ni l'acceptation B ; recontrôler ce
  volume et la finance au chantier après tout changement de plan,
  abandon/rollback existants, 1-2 véritables fourgons, deux StationIDs
  distincts et ordres fonte→destination, Save/Load standard. Le marché
  est d'abord un transport A→B **unidirectionnel** ; pas de bonus de
  retour B→A sans construction/ordres livrant effectivement dans ce sens.
  Mesurer candidats vus/préplans/admis, `ROAD_BUILD cargo=MAIL`, vrais
  profits `LINE_REVENUE` matures, cash/opcodes et `profit_year` 1–5 ans
  face à AAA. Smoke strict 2 graines (42,2026) ×2 ans ; 5×5 si
  construction exposée, A40×5 seulement si delta mean>=4%, p<0,05,
  valeur>=−5%, non-érosion. Pas de gain fictif ni nouveau défaut.
  **Premier pilote V27a** `road100_v27_mail_intertown_roadonly_2x2_20261028`
  bundle `acce5ffbc5213387cb44e49dab2981542f8999c89488f3dea26a80845d082d25` :
  4/4 sains, une nouvelle ligne MAIL réellement bâtie seulement sur
  seed2026, le 16/10/1971, d26, 1 fourgon, coût physique 6 292£,
  `profitAnnual` prédit **273£/an**. Seed42 construit aussi une ligne MAIL
  d44 issue du fret habituel, pas du nouveau générateur ; ne pas lui
  attribuer ce profit. Le premier générateur V27a consomme 266–490k
  opcodes en diagnostic, au-dessus du soft cap200k en raison du plan
  atomique. H2 V27 ON−OFF **−10 259,5£/an**, 0V/2D, p=0,5,
  valeur **−22,45 %**, Opex/AAA **12,0 %**, 0/2 victoires AAA.
  V27a **NO-GO** pour 5×5/A40×5 ; option0 conservée. Priorité
  au marché de longue distance réellement rentable plutôt qu'à une
  ligne MAIL de 273£/an qui détourne le capital.
  **V27b distinct préenregistré avant code :** étendre le même réglage à
  `road100_mail_intertown=2` (0 reste défaut, 1 pilote court intact)
  pour explorer **uniquement 43–80 cases sur voirie déjà CONNECTÉE**,
  sans nouveau routeur A* et sans acheter de route interurbaine
  hypothétique. Rechercher deux stations TRUCK dans des villes
  distinctes, source MAIL réellement produite non captée, destination
  acceptant >=8, `OpexRoadBfsPath` en deux sens sur les fronts de la route
  EXISTANTE (<=256 noeuds par sens), au plus 4 couples de vrais sites,
  <=200k opcodes soft/regen. Un vrai dépôt adjacent au chemin et une
  station à chaque bout, StationIDs distincts, deux ordres et roulage
  attesté. Un plan non connecté est refusé avant frais, jamais
  extrapolé. Exiger après devis réel conservateur **profit prédit
  >=3 000£/an et ROI>=25%**, y compris pour V27b court/long, éviter
  que les 273£/an supplantent les autres cargos. Comparer 0→2 sous
  mêmes autres options, smoke 42/2026×2 ans, puis 5×5 seulement si
  construction réellement exploitable et signal de profit non érodé.
  **V27b mesuré le 28/10 : NO-GO.** Pilote
  `road100_v27b_mail_existing_long_roadonly_2x2_20261028`,
  bundle `33e0a87857550a6e69467419826274d2deb7e97a4f3b1b7c4ac7bc688bad8220`,
  4/4 parties saines, AAA route seule, mêmes graines et carte pour
  OFF et ON. H2 profit Opex ON 62 603£/an, OFF 68 684,5£/an,
  delta **−6 081,5£/an**, 0V/2D, p=0,5, valeur **−11,16%**,
  Opex/AAA ON **11,53%**, 0/2 victoires.
  Huit préplans testés (seed42 1+1, seed2026 3+3),
  **0 admission/0 chantier MAIL long** ; ils échouent tous avant
  un devis viable, sans prouver l'absence universelle de corridors.
  Génération 166k..375k opcodes malgré plafond soft 200k.
  L'économie conserve le coût intégral de voirie par prudence.
  Pas de 5×5 ni A40×5, défaut0, **ROAD100 toujours 0/5**.
  **Diagnostic supplémentaire V27b2**, sans qualifier la variante :
  première sonde : les quatre sites favoris de chaque côté ont une
  façade constructible mais non routière (`no_road=4..7`,
  aucun couple BFS). Filtrage opt-in des façades déjà routières :
  seed42 villes26→32, quatre couples, **4 `no_conn`** ;
  seed2026 villes45→33, quatre couples, **4 `no_conn`**.
  Deux pilotes appariés 2 graines×1 an sains, chacun sans
  nouvelle MAIL longue, dernière variante `road100_v27b_fronts_roadonly_2x1_20261028`
  bundle `87dafd3ce36f7d912faeea75c7bc80c6ef743440008487096633d4d5fb1674ac`.
  Un BFS `null` peut signifier composante vraiment disjointe
  **ou** dépassement de 256 nœuds. Un seul préplan >540k opcodes
  par graine après filtrage rend une augmentation brute de BFS
  non viable. Prochaine hypothèse à tester : identifier les
  composants routiers, distinguer SEARCH_CAP de NO_COMPONENT,
  filtrer par marché de voyageurs réel avant le plan physique.
  **V28 enregistre avant code : double quai PAX par côtés, capital
  séquentiel, indépendant du V26 (expérimental, défaut0)**.
  Hypothèse alternative aux lignes nouvelles : pour les PAX déjà
  rentables avec deux vrais arrêts racines 1/1 et deux bus,
  ajouter **un vrai quai BUS joint à chacun des deux StationIDs**,
  en deux étapes/an maximum, une seule pose réussie par année ;
  après le premier quai le plafond reste 2, après les deux passe
  à 4, puis acheter ≤2 bus sur demande Opex réellement en attente,
  profit de ligne ≥5k£/an, réserve ≥50k£ et circulation observée.
  Aucun revenue PAX additionnel de zone, jamais waiting AAA.
  V28 doit réutiliser le constructeur traversant V26 sur vrai
  réseau, ≤12 sites/4 AITest/40k opcodes *par quai*, sauvegarder
  deux tuiles physiques et les revalider après Save/Load/démolition.
  En cas d'échec, aucune seconde construction ni revenu.
  Le premier smoke 42/2026 ×3 ans strict ROUTE seule mesure
  lignes éligibles, poses bilatérales, bus réellement livrants,
  `profit_year`, cash et horizons. Gate A40×5 seulement
  H5 ON−OFF ≥4 %, p<0,05, valeur ≥−5 %, sans érosion H1–H4.
  La voie PAX interurbaine **nouvelle** reste également à
  résoudre : la double capacité ne suffit pas seule à la parité.
  **Résultats V28a/V28b (28/10)** : premier pilote
  `road100_v28_pax_double_berths_roadonly_2x3_20261028` sain
  (4/4), deux vrais quais et un refleet, mais sur des lignes
  déjà à 2/1 ou 1/2 : l'effet H3 +2 904 £/an ON−OFF
  (p=1) reproduit essentiellement V26, sans tester 1/1.
  Éligibilité corrigée : première pose seulement depuis 1/1,
  deuxième seulement sur marqueur physique V28 sauvegardé.
  Après correction : **3 184 tests OK** (5 skipped, 2 xfail),
  V262 33 OK, projection OFF et diff check OK, fixture intacte.
  Pilote neuf `road100_v28b_pax_double_from11_roadonly_2x3_20261028`,
  bundle `8661118e742bccf91ac83d0d3820ffe314b240153a368df3051a85a7aeb20551` :
  4/4 sains, **zéro quai V28, zéro renfort attribuable**.
  Opex ON / AAA ON H1 : 20 125 / 116 853 £/an (17,22 %) ;
  H2 : 71 767 / 549 894 (13,05 %) ;
  H3 : 83 699 / 1 032 465 (8,11 %). ON−OFF :
  0 / −1 563 / −1 179,5 £/an ; H3 1V/1D, p=1,
  IC95 bootstrap [−8 805 ; +6 446] £/an, valeur +5,01 %.
  Les trois lignes PAX âge2 du pilote : deux déjà 2/1 ou 1/2 ;
  seule ligne 1/1 rentable avec 26 PASS en attente, sous
  seuil 3×35=105. **NO_EXPOSURE, pas d'A40×5, défaut 0.**
  Le premier quai au plus tôt en 1972 exigerait un quatrième
  exercice pour la deuxième pose ; H3 ne teste pas la séquence.
  Le diagnostic PAX mature `diag_road100_pax_heldout_20261028.py`
  utilise seulement V24 ON : train 7/42/100 (19 observations,
  9 lignes), heldout 999/2026 (17, 7 lignes), facteurs train
  réel/prédit revenu 6,454 et profit 18,809. MALE heldout
  revenu 1,788→0,589 et profit 2,652→0,915, mais seed999
  régresse et seed2026 domine le gain ; biais de sélection
  et seulement deux graines de test. **Aucune calibration
  intégrée au runtime ni rentabilité ex ante validée.**
  Après V28b, un correctif de récupération remet les compteurs
  à 1/1 si le marqueur des quais est mal formé ; si les deux
  quais V28 ont disparu, il libère la première étape suivante.
  **3 184 tests** (5 ignorés, 2 échecs attendus), V262, projection
  OFF et diff check OK. Le smoke moteur distinct
  `road100_v28c_recovery_compile_roadonly_1x1_20261028`
  est sain 2/2, H1 ON−OFF nul : compilation validée, **pas**
  de démolition externe ni de pose bilatérale démontrée.
  **Audit ROAD100-29** : sur V26, 205 préplans SITE_FIRST,
  181 TRACEX (88,3 %), 24 admissions physiques pour
  106,14 M d'opcodes (518k/préplan). Captation médiane
  28 PASS/mois contre proxy-ville 115 ; profit prévu médian
  290£/an, ROI médian 3,2 %. Ce générateur ne propose
  que d12..42, zéro admission d43..80. C75 refuse
  37/37 chantiers additionnels pour ROI<25 %, non faute
  de cash ; TopK=48 est un indicateur de diagnostic.
  À H5, déficit de `profit_year` de société de
  **2 037 540£/an** face à AAA. Même en supposant +25k£
  net par ligne supplémentaire, il en faudrait ~82.
  Prochain levier **V29 SHADOW de marché interurbain**,
  opt-in défaut0, sites physiques et demande marginale
  ex ante sur d43..80, opcodes bornés, sans chantier,
  rendement inventé ni usage du waiting AAA.
  **Résultats V29 (bundle**
  `42e53b9f8099894cf180ac957700023f58c1cca592067ad2bb6d953e6dbfe55c`) :
  sur cinq graines × H1, 10/10 parties exécutées,
  Opex ON 20 725£/an contre OFF 17 400£/an,
  +3 325£/an (5V/0D, Wilcoxon p=0,0625), AAA
  ON 135 384£/an : **15,31 %, 0/5 parités**.
  Deux graines marquées `stagnation_suspect`
  dans le résumé de référence. Sur deux graines
  × H2, Opex ON 68 364£/an contre OFF 73 330£/an,
  **−4 966£/an** (0V/2D, p=0,5, valeur
  ON−OFF −9,24 %), AAA ON 556 663£/an :
  **12,28 %, 0/2 parités**. Sonde annuelle
  à 21k..24k opcodes sous plafond200k ;
  aucun candidat, voie ou station construits,
  ROI réel `-1` car devis de route absent.
  Les trois paires avec deux vraies façades
  dénombrent **7..12 producteurs** à l'origine,
  et NON 7..12 PASS/mois. Le précédent calcul
  de **2 016..3 312£ de recette annuelle
  maximale était faux (erreur d'unité)**.
  **V29 NO-GO comme SHADOW sans chantier**,
  défaut0, pas d'A40×5 ; le rejet économique
  basé sur ce faux plafond est retiré.
  Les écarts ON−OFF sur un SHADOW sans projet
  ne constituent pas des gains de marché ;
  investiguer perturbation d'opcodes/calendrier.
- [ ] **28/10 — ROAD100 PAX, contre-audit baseline 40 graines** :
  [rapport et script reproductible](road100_calibration_pax_40graines_20261028.md).
  Sur 108 observations matures, 47 lignes dans 28/40 mondes :
  ratio de sommes réalisé/prédit **0,818 recette / 0,797 profit**.
  Les 0,864/0,882 sont des médianes **tous âges** (164 lignes-âges)
  et V24 6,454/18,809 de petites médianes train ON à flotte accrue,
  non transportables comme coefficient ex ante. V29 SHADOW décale
  PO01C : H2 seed42 −6 131£/an, seed2026 −3 801£/an ; le bras
  seed2026 perd deux lignes PAX sans aucune construction V29.
  **ROAD100-30 à concevoir sur une offre réelle de plusieurs quartiers
  hors `station_spread`, pas un bonus de rendement ni un nouveau
  scanner V16/V29.** Préqualifier demande marginale, deux vraies
  StationIDs + feeders construits et connexes, route/dépôt, coûts
  et opcodes avant ON ; ne pas lancer Gate A sans chantier rentable
  et gain primaire. **0/5**, aucune adoption ni défaut changé.
  Pré-enregistrement de falsification
  [ROAD100-30 multi-quartiers](road100_v30_multidistrict_prereg_20261028.md)
  établi sans réglage ni campagne V30, en excluant explicitement les
  feeders V139 réfutés et les décalages PO01C des SHADOW.
  **Rectificatif d'unité 28/10 : AITile.GetCargoProduction compte
  des producteurs, PAS des PASS/mois.** V29 7..12, LONG 31..35
  et V20 +2..15 ne plafonnent donc aucun revenu en £ ;
  l'ancienne qualification économique NO-GO sur ces chiffres
  doit être réexaminée. V30a préenregistre un modèle
  producteurs locaux / producteurs ville × vraie production
  mensuelle AITown, seulement sur sites PAX construisibles,
  opt-in défaut0, sans oracle AAA ; V30b multi-StationID
  seulement après ce test dimensionnel. **0/5 inchangé.**
  **V30a diagnostic 5×5 terminé, bundle figé**
  e39edc170152411978049d578501e6618d83d2484c0d7e8b7c0e821c2a6d4f98,
  AAA ROAD-only : profit_year ON / AAA
  H1 17,84 %, H2 11,64 %, H3 6,28 %, H4 3,96 %, H5 3,57 % ;
  ON−OFF en £/an +6 597/+14 912/+10 699/+8 847/+5 500.
  H5 p=0,625, IC95 [−4 568 ; +16 598], **NON QUALIFIÉ**.
  V30a 31 lignes PASS et 52 bus initiaux (OFF 26/26),
  20 quais supplémentaires sur 12 routes, seulement quatre
  avec nouvelles stations aux deux bouts, flotte initiale
  PORTFOLIO bloquée à deux bus. Étudier capacité physique
  initiale V31 si deux StationIDs réellement équipés
  et devis/ROI/cash/rollback vérifiés. Suite complète
  **3 198 tests OK**, cinq skipped et deux expected failures,
  git diff --check OK ; **0/5** et défaut0.
  **V31 en qualification** : flotte initiale PASS étendue
  seulement après construction des quais doubles
  physiques, avec marge économique incrémentale
  (ROI annuel ≥25 % sur prix réel des bus additionnels),
  50k£ de caisse, stations/ordres/refit/slots
  revérifiés et revenu des seules racines V30a.
  Réglage road100_pax_initial_berth_fleet défaut0,
  [pré-enregistrement](road100_v31_initial_berth_fleet_20261028.md).
  Destruction externe : plafond de flotte récupéré
  après Save/Load, sans liquidation automatique
  des bus déjà en service. **Toujours 0/5.**
- [ ] **ROAD100-32 : corridor LONG segmenté à tester en moteur, défaut 0.**
  L'audit AAA 40×5 confirme 602/754 lignes PASS à distance de gares
  81–160 contre zéro Opex ; les versions LONG v5–v19b n'ont bâti
  aucun corridor. Intervention isolée `road100_segmented_corridor=1`
  (requiert `road100_long_build=1` et mode ROAD seul) : un trajet
  80–190 arêtes par au plus 12 ancres et mini-gaps locaux ≤80
  expansions, puis vérification AITest complète de chaque arête,
  préflight dépôt/quais, devis des seules arêtes absentes, cash
  +25 % +50 k£, mêmes lieux/hash/devis à la construction. Production
  PAX estimée à partir de vrais producteurs couverts par les deux
  racines et de `AITown.GetLastMonthProduction`, jamais du nombre de
  producteurs brut assimilé à PASS/mois ni du waiting AAA.
  Préenregistrement
  [ROAD100-32](road100_express_corridor_prereg_20261028.md),
  tests et fixture V32 séparée pour l'exacte projection OFF, sans
  toucher V262. **Implémentation initiale en validation, aucune
  construction ou rentabilité démontrée, 0/5 inchangé**. Reste :
  suite complète, contrôle Squirrel, smoke ROAD-only OFF/ON sur
  bundle identique, 5×5 seulement si vraie ligne livrant des PASS,
  puis Gate A40×5 sous critères stricts.
  Résultats 1×1 H1 : V32 bundle `ab882674885c04374468d999b13a0e95e5a022bb53d3a5e8b394ba9886307f8e`,
  V32b pondéré bundle `70e220e56e0aa8a901081efb58f5c2149ddb27cbaa77819e91f080e772d634c6` :
  **0 corridor LONG**, `OPCAP` 47–80 k opcodes sur le premier gap,
  `profit_year` OFF/ON **19 103 £**, AAA **97 693 £** ;
  **NO-EXPOSURE/NO-GO**. Pas de 5×5 ni de Gate A.
  V31b correction unités + fréquence, smoke H2 graine100 :
  vrais 3 bus initiaux vs 1, mais Δ `profit_year` H1 −2 186 £,
  H2 −7 736 £, PASS livré Q4 H2 761→461, valeur H2 −95,1 %.
  **NO-GO V31b** malgré exposition physique. Voir
  [preuve V31b](road100_v31_initial_berth_fleet_20261028.md).
  V33 `road100_sparse_corridor=1` : suite 3 217 tests OK, exact OFF
  V31b/V32/V33, smoke H1 seed42 2/2 sain (bundle `98ee5732...`,
  strict ROUTE seule) : profit société OFF 22 491 £, ON 20 797 £,
  AAA 94 472 £ ; delta −1 694 £, valeur −33,58 %. `ROAD100_SPARSE`
  d'abord `OPCAP` après 37 015 opcodes, ensuite `NO_CORRIDOR` et
  `OPCAP`, 0 route sparse réellement admise ou construite.
  **NO-EXPOSURE / NO-GO V33**, aucune 5×5/A40×5 :
  [preuves V33](road100_express_corridor_prereg_20261028.md).
  Prochaine priorité : marchés avec plusieurs quais réellement captants
  avant toute recherche LONG, et vérification économique ex ante.
  **V34 sonde prétrace terminée**, option `road100_long_market_probe`
  défaut0 : 3 222 tests OK, exact OFF, smoke strict ROAD seule
  seed42 H1 2/2 sans erreurs (bundle `da7671fed4...`).
  Conversion correcte : 18→2 d158 = **258 PASS/mois estimés**
  (138+120 sur 18+17 producteurs) ; 26→10 d154 = **175 PASS/mois**
  (115+60 sur 17+13 producteurs), mesures 1 726/1 661 opcodes.
  `profit_year` OFF=ON 19 103 £ vs AAA 97 693 £, **aucun plan LONG**.
  V34 purement SHADOW, **pas de 5×5/Gate A/adoption**, prochain
  chantier : vraie flotte/gares et route physiquement chiffrées.
  [Préenregistrement et preuves V34](road100_v34_long_market_prereg_20261028.md).
  **Toujours 0/5**, aucun défaut changé.
- [ ] **Goulets prouvés** : `OpexRoad100SiteFirstGenerator` teste 5–6
  préplans coûteux par an, souvent 0 admis (`TRACEX`, 2,8–3,1 M opcodes
  seed42). `OpexRoadFreightCandidates` bloque les origines déjà servies
  sans nuance de cargo ; `OpexRoadLineEconomics`/refleet plafonne
  ordinairement à 2 camions ou bus par paire de quais. C75 `K_pass`
  arrête des chantiers supplémentaires malgré >200 k£ de caisse.
  Toute extension doit garder vraie capture, chantier, coût, trésorerie,
  transports et garde anti-congestion ; ne pas utiliser `waiting`
  post-construction pour une admission ex ante.

### 27/10 — ROAD100 : viser 100 % du profit AAAHogEx en ROUTE seule, à 1, 2, 3, 4 et 5 ans

- [ ] **ROAD100 — objectif ouvert à chaque horizon.** Baseline 40×5
  `road100_baseline_40x5_20261027`, 40/40 duels sains : **6,0 %, 4,8 %,
  2,6 %, 1,7 %, 1,4 %**, **0/40 victoire** à chaque année. Code de base
  `estim_unifie=31`, modes Opex `air=0 rail=0 road=1 water=0`, AAA routes
  seules (`disable_veh_train/tram/ship/aircraft=1`). En 1970 seulement
  6 véhicules Opex contre 53 AAA, alors qu'Opex conserve 258 k£ de caisse.
  Rapport reproductible `sweeps/analyse_road100.py`,
  `results/road100_baseline_report_20261027.md` et preregistration
  [ROAD100-1](road100_solo_pax_prereg_20261027.md).
- **Variantes opt-in, défaut 0, jamais adoptées** : bus interurbains
  `road100_solo_pax=1` 5×1, **−410 £/an**, 3V/2D ; bus intra-ville
  `road100_town_bus=1` 5×1, **−800 £/an**, 2V/3D ; ni l'une ni l'autre
  ne rapproche significativement la cible. Le tracé intra-ville existant
  rejette beaucoup de `TRACEX` : `road100_town_voirie=1`,
  [preregistration](road100_town_voirie_prereg_20261027.md), a été exposé et
  donne **−924 £/an**, 3V/2D (5×1). `road100_pax_fleet_cap=8`
  [preregistration](road100_pax_fleet_prereg_20261027.md) est inerte au smoke
  (tous les plans ne demandent qu'un ou deux véhicules).
- **Troisième essai : cadence** `road100_road_batch=1` (quatre
  constructions au plus par passe, ROI >=25 % et 50 k£ de capital restant) :
  smoke 1×1 +4 860 £/an, diagnostic 5×1 **+3 291 £/an**,
  2V/1D/2E, IC95 traversant zéro. **40×5 terminé `fail_primary`** :
  **−194 £/an** à cinq ans, 15V/23D/2E, p=0,852, valeur +2,72 %.
  Tous les horizons encore <7 % du profit AAA ;
  [preregistration](road100_build_batch_prereg_20261027.md).
  Lot 5 : `road100_town_roi_post=1`, [preregistration](road100_post_siting_roi_prereg_20261027.md),
  **−3 508 £/an** sur 5×1, 1V/4D. Lot 6 :
  `road100_intercity_site_fleet=1`, [preregistration](road100_intercity_site_fleet_prereg_20261027.md),
  **−8 049 £/an** sur 5×1, 0V/5D : le site capte 23 voyageurs/mois
  quand le préclassement en annonce 379 (graine 42). Tous ces leviers
  restent non qualifiés au défaut.
  [Rapport analytique](road100_etapes_20261027.md).
  **Goulot désormais démontré :** la plus grande ligne ROAD d'AAAHogEx
  emploie **22,7 véhicules en moyenne à un an** (jusqu'à 29 sur la graine 42),
  contre 2,0 chez Opex ; les emplacements de bus Opex observés sur la même
  graine captent **23 voyageurs/mois** alors que le préclassement voit une
  production totale des deux villes de **379 voyageurs/mois**. Les `TRACEX`
  écartent aussi des paires initialement prometteuses. **Suite prioritaire
  ROAD100-7 : classer les candidats voyageurs à partir de sites constructibles
  et de leur production locale effective, avant la sélection, puis d'une
  connectivité routière bornée sur voirie existante.** Préserver la garde de
  rendement réel et les ressources en opcodes ; ne pas relâcher simplement
  `origin_served`, augmenter la flotte sur des sites vides ni supprimer
  `k_pass`. Comparaison exigée : mêmes 40 graines, 1–5 ans, 40 duels 1v1
  contre AAA ROUTE seule, et ≥100 % de profit annuel à chacun des horizons.
  Contrats des réglages et non-exposition multimodale dans
  `sweeps/test_road100_solo_pax.py` ; analyse de constructions, rejets,
  finance et opcodes par `sweeps/road100_log_metrics.py`. Aucun changement
  de défaut/commit/push sans instruction explicite. Les cinq objectifs
  restent distincts, et aucune simple augmentation de réseau ne remplace
  les tests économiques appariés.
- **28/10 — ROAD100-7 site-first, opt-in non qualifié.** Le code classe les
  projets ROAD PAX après mesure sur des arrêts et un trajet physiquement
  réalisables, sur une sélection géographique bornée. La régénération
  coopérative PO01C conserve ces projets ; garde financière et projection
  historique OFF exacte. Les smokes graine 42 ont montré d'abord 12/12
  `TRACEX` et 10,29 M opcodes, puis 4/4 échecs, puis 3 plans admis et
  2 lignes passagers construites avec ~2,54 M opcodes de planification.
  **5×1 v3 complet mais NO-GO :** profit Opex +1 695 £/an, 3V/2D,
  p=0,8125, IC95 [−9 819 ; +11 810] £, **valeur entreprise −50,39 %**.
  Ratio Opex/AAA ON **13,72 % à 1 an**, loin de 100 % ; aucune porte
  40×5 ni adoption du défaut n'est justifiée. Les sites ne captent que
  ~20–30 pax/mois ; prochaine étude : plusieurs arrêts complémentaires
  et transferts, plutôt qu'augmenter la flotte sur un arrêt quasi vide.
  [Préréservation](road100_site_first_prereg_20261028.md) et
  [analyse des résultats](road100_site_first_resultats_20261028.md).
- **28/10 — ROAD100-7 v4 causal et ROAD100-8.** L'audit détaillé réconcilie
  les 12 `TRACEX` du préflight v1, les deux lignes passagers bâties v3,
  et les trois erreurs de pose v3 : le planiteur sur voirie basculait
  dans le fallback historique, puis classait ses sites différents comme
  site-first. Ce repli n'est désormais plus accepté par le seul opt-in ;
  les sites génération/replan sont journalisés. **V4 5×1** :
  +37,2 £/an, 3V/2D, p=1,0, IC95 [−12 404 ; +11 215] £,
  valeur **−61,22 %**, Opex/AAA ON **11,94 % à un an** : NO-GO, aucune
  40×5 et aucun changement de défaut. L'expérience suivante
  [ROAD100-8, satellites joints](road100_joined_stops_prereg_20261028.md)
  vise un captage marginal supplémentaire sur les mêmes StationID,
  sans gonfler la flotte. Journal : [ROAD100-7 causal](road100_etapes_20261027.md).
- **28/10 — ROAD100-8 et ROAD100-9 écartés.** Satellites joints ROAD100-8 :
  smoke physique (+5 pax/mois, 150 £) mais 5×5 −5 002 £/an, p=0,8125,
  valeur −6,24 %, Opex/AAA 2,33 % à cinq ans. Multi-bassins non
  chevauchants ROAD100-9 : smoke graine42 1×5 +9 160 £/an mais
  5×5 +994 £/an seulement, 2V/3D, p=1,0, valeur +3,43 %,
  Opex/AAA ~2,2 % à cinq ans. **Aucun 40×5 justifié**, aucun
  défaut modifié. [Protocoles 8](road100_joined_stops_prereg_20261028.md)
  et [9](road100_multicatchment_prereg_20261028.md).
- **28/10 — ROAD100-10, renfort sur profit et attente réelle.**
  Le constat `LINE_REVENUE` graine42 : une ligne passagers
  prévue à 170 £/an réalise 9 318 £/an après un an et présente
  140 passagers en attente. Le nouveau pilote
  `road100_wait_fleet=1` (défaut 0) autorise des bus supplémentaires
  sur les seules lignes passagers matures rentables, en fonction
  des stocks réellement mesurés, des véhicules circulants, du
  cycle de route et d'une garde de 50 k£. Smoke 1×3 graine42 :
  passage de 2 à 3 bus, **+2 880 £/an** et valeur **+12,95 %** ;
  pilote 5×5 terminé : **+3 498,8 £/an**, 2V/2D/1E,
  **p=0,625**, IC95 [−6 336 ; +13 802] £, valeur +15,44 %.
  Renfort réellement exposé : **21 bus au-delà de deux** en 12 achats,
  mais le gain n'est pas robuste et aucune 40×5 n'est justifiée.
  Profits Opex/AAA aux horizons 1–5 : **11,9 / 8,1 / 4,6 / 2,8 / 2,5 %**,
  **0/5 victoire à chaque horizon**, aucun seuil fermé.
  [Préréservation](road100_wait_fleet_prereg_20261028.md) et
  [analyse annuelle](road100_etapes_20261027.md).
- [ ] **28/10 — ROAD100-11, diversification des préplans site-first.**
  164/187 préplans du 5×5 précédent refusés, 92 répétitions de couples ;
  l'exploration de rangs secondaires est bridée par le budget d'opcodes.
  Nouvelle fenêtre tournante déterministe opt-in `road100_site_window=1`,
  garde la meilleure paire et le même budget, **défaut 0**. Smoke graine42
  1×3 +19 389 £/an, mais vrai pilote 5×5 **−5 432 £/an**,
  2V/3D, **p=0,4375**, IC95 [−13 268 ; +3 589] £,
  valeur +2,23 % ; **NO-GO**, pas de 40×5. Les cinq ratios annuels
  restent à 11,9 / 6,5 / 4,8 / 2,7 / 2,2 %.
  [Préréservation](road100_site_window_prereg_20261028.md).
- [ ] **28/10 — ROAD100-12, trier par proximité constructible.**
  Le coût des `TRACEX` suggère d'étudier les paires les plus courtes
  parmi celles de proxy positif. Nouveau switch `road100_site_near=1`,
  défaut 0 et limites opcodes inchangées. Smoke 1×3 +15 792 £/an
  mais **0/16 admission site-first**, signal indirect ; diagnostic 5×5
  **−23 710 £/an, 0V/5D, p=0,0625, IC95 entièrement négatif**,
  valeur **−33,86 %** (garde violée), NO-GO, aucune 40×5.
  Checkpoints 1–5 ans : 11,0 / 6,2 / 2,6 / 1,7 / 1,3 % de AAA.
  [Préréservation](road100_site_near_prereg_20261028.md).
- [ ] **28/10 — ROAD100-13, détour physique à deux coudes.**
  Une nouvelle ligne PAX graine42 a réellement été construite en
  février 1971 après échec BFS/L, mais le diagnostic apparié **5×5**
  `road100_detour_v1_expo_5x5_20261028` donne **−6 231 £/an**,
  2V/3D, p=0,625, IC95 [−19 491 ; +5 202] £, **valeur −8,83 %**.
  La garde −5 % est violée, **NO-GO**, aucune 40×5 ni adoption.
  Opex/AAA 1–5 ans : 11,8 / 7,0 / 4,5 / 2,7 / 2,2 %.
  [Préréservation](road100_detour_prereg_20261028.md).
- [ ] **28/10 — ROAD100-14, réseau multi-gare / multi-ordres.**
  Prototype opt-in `road100_tour=1` (défaut 0) : réutiliser une ligne
  PAX existante pour une gare bus `STATION_NEW` indépendante et circuit
  quatre ordres `[A0,B0,A1,B0]`, sans ajouter une nouvelle ligne ni
  confondre avec les satellites ROAD100-8. **Aucune station A1 construite
  en moteur à ce jour.** V1 `OPCAP`, v2 `NO_MARGINAL` ; v3 sur cinq
  graines ×3 ans : 7 `OPCAP`, 2 `NO_MARGINAL`, aucun `AITestMode`.
  V4 somme préfixe dense : graine 42 2 `OPCAP` vers 100k, aucun A1,
  +701 £/an apparié mais sans exposition. V5 index clairsemé (un
  `Valuate`) : graine 42 2 `NO_MARGINAL` à ~87k ops et −2 760 £/an,
  valeur −12,33 % ; graine 100 2 `ROI` avec prédiction marginale
  négative et ~108k ops (cap soft dépassé), −10 302 £/an, valeur −74,30 %.
  **NO-GO économie, pas de 5×5 ni 40×5** pour v5. Les variations de
  profit alors qu'aucun A1 n'a été construit peuvent refléter la
  concurrence pour les opcodes et le calendrier des décisions : elles
  ne prouvent pas l'efficacité d'une tournée. Save/Load et refleet
  n'ont pas été validés sur un vrai circuit 4 ordres.
  [Préréservation principale](road100_tour_prereg_20261028.md),
  [v3](road100_tour_v3_prereg_20261028.md),
  [v4](road100_tour_v4_prereg_20261028.md),
  [v5](road100_tour_v5_prereg_20261028.md),
  [journal](road100_etapes_20261027.md).
- [ ] **28/10 — ROAD100-15, calibration économique après ESTIM31.**
  Audit lecture seule de 50 `LINE_REVENUE` PAX sur cinq graines :
  fortes discordances prédit/réalisé mais changements de flotte
  et bases comptables différentes ; aucune justification d'un bonus
  brut de score. Étudier un shadow opt-in sur cohortes matures à
  flotte stable, puis heldout seed-balanced et Score-only sous garde,
  sans inventer des recettes. [Journal](road100_etapes_20261027.md).
- [ ] **28/10 — ROAD100-16, marché interurbain dominant AAA.**
  Comparaison graine42 : AAA dessert 134 cases entre arrêts,
  avec 28 bus et 119 082 £ de profit véhicules cumulé au 01/12/1970,
  contre deux bus et 8 179 £ sur le PAX Opex ; longueur maximale de
  trace Opex **48** et captation observée ~27 PASS/mois sur le site.
  Étudier un nouveau corridor express à **vraie forte captation**
  et tracé physiquement admissible, financé au coût réel, avec flotte
  adaptée aux réalisations (pas simple relèvement de plafond).
  Shadow coopératif opt-in défaut 0 intégré, au plus deux couples LONG
  80–170, une fois par année PO01C, sans aucun candidat dans le
  portefeuille. **v1 seed42 1×1** : 527 141 opcodes, refus OPCAP
  avant deuxième bout, −9 438 £/an Opex et valeur −28,93 %;
  **v2 seed42 1×1** : scan physique borné, deux couples 129/84
  en 63 675 opcodes, mais captation max par arrêt 11/11 puis
  11/17 PASS/mois, aucune connexion testée ni construction ;
  −9 532 £/an Opex, valeur −18,45 %. Ces deltas ne sont pas des
  effets d'un réseau LONG (zéro exposition), mais le surcoût du
  shadow déplace les décisions. **v3 union exacte des maisons**
  sur 1+2 arrêts / StationID, cinq graines fixées, dix couples :
  max 10–21 PASS/mois/ville, bonus satellite 0–2, zéro chemin,
  zéro construction, NO_EXPOSURE. **v4** élargit la recherche
  rayon16 / ≤160 routes / ≤16 AITest, bonus maximal +5
  PASS/mois mais consomme 335 452 ops au lieu de 250k.
  **v4b** corrige le budget résiduel par paire, 210 948 ops
  mesurés sur graine42, mais toujours LOW_DEMAND / OPCAP,
  zéro ligne. Pas de 5×5 économique sur ces shadows ;
  chantier de captation et chemin long toujours ouvert.
  **v5** diversifie le second couple (38–23, distinct de 22–28),
  mais PATH_ONLY était empêché par le budget après union.
  **v5b** place PATH_ONLY avant union : 42 nœuds explorés
  (17/25), aucun chemin routier continu dans les deux sens,
  6 361 opcodes PATH_ONLY et 211 463 opcodes LONG cumulés
  sur graine42, 2/2 parties saines, zéro construction.
  Delta −7 268 £/an et valeur −15,41 % sans exposition :
  **ni adoption ni 5×5 économique**.
  **v6–v8 en qualification** : nouvel opt-in `road100_long_build=1`
  séparé (défaut 0), plan long multi-coudes, préflight des
  arêtes absentes, prix et finances, site/tracé identiques au
  chantier et deux StationID sans satellite fictif.
  **v6 42×1 an** : zéro candidat construit, premier plan
  `UNBUILDABLE` (192 149 opcodes), second `OPCAP` (115 384).
  **v7** : crash Squirrel du comparateur de grandes villes
  (booléen au lieu de −1/0/+1), corrigé avant **v7b**.
  **v7b 42×1 an, AAA ROUTE seule** : villes 18–2 puis 26–10,
  zéro préflight admis ; premier `AITEST_BUILD_ROAD` erreur 260
  (`ERR_AREA_NOT_CLEAR`), 293 399 opcodes, second sans budget.
  **v8 spatial 42×1 an, AAA ROUTE seule** : deux parties saines,
  projection OFF exacte et 35 tests ROAD100 + 51 V262 OK,
  zéro plan physique admis : première paire `GEOMETRY`
  (4 sites A, 1 B ; 17 essais, 175 388 opcodes, obstacle 260),
  seconde `BUILD_SITE_B_OPCAP` après 73 372 opcodes.
  Opex ON `profit_year` 18 881 £ contre AAA 93 624 £,
  mais **aucun effet LONG démontré** ; diagnostic sur une graine,
  pas une porte économique. Itérer sur contournement réellement
  constructible, allocation des opcodes, admission financière,
  puis stations, circulation, livraisons et profit encaissé.
  **v9** : premier moteur invalide (`parent` mot réservé Squirrel),
  réparé en **v9b** sans changer le chemin OFF. **v9b seed42 1×1
  ROAD-only** : 2/2 parties saines, aucun LONG ; 2 recherches A*
  explorent 90 nœuds pour 171 054 opcodes, plafonnées localement
  `SEARCH_CAP`, puis formes historiques non bâtissables.
  **v10** (A* sans AITest par voisin, validation différée sur
  trace complète avec arêtes refusées mémorisées) : 2/2 parties
  saines, encore zéro LONG ; 91 nœuds, 0 AITest de trace et
  171 021 opcodes avant `SEARCH_CAP` : **l'exploration, pas
  les AITest, concentre le coût**. Ne pas relever les caps sans
  action sur le coût unitaire ni confondre une recherche avec une
  ligne bâtie. Les deux variantes ON donnent 18 881 £/an contre
  93 624 £/an AAA (même graine), mais le delta ON−OFF v10
  de −6 115 £/an est sans exposition LONG, non qualifiable.
  **v11** : cache tuile/arête, voisinage dirigé et heuristique
  plus gloutonne ; smoke 42×1 an strict ROAD 2/2 saines,
  **toujours 0 LONG**. A* : 116 états, 270 cases évaluées,
  177 008 opcodes sur deux recherches, meilleur progrès 55
  cases sur ~158, `SEARCH_CAP`, `AITest`=0 ; le coût par état
  rend le solveur synchrone actuel structurellement inadapté.
  Comparaison source AAAHogEx-115 `road.nut:852-927` :
  `RoadPathFinder` fondé sur AyStar, relancé en tranches de
  100 explorations jusqu'à 100 tranches en régime ROI ;
  `roadpathfinder.nut` sait envisager ponts et tunnels, puis
  `road.nut:941-1000` réessaie des arêtes réelles avec traitement
  d'`ERR_AREA_NOT_CLEAR`. Opex dispose déjà d'un AyStar/heap
  dans `pathfinder_v90/v129.nut` mais **pas de route LONG
  incrémentale comparable**. Ne pas simuler le profit AAA par
  un bonus fixe ni confondre stock `waiting` et production/mois.
  **v12 ROAD-only 42×1 an** : A* optimiste, 104 nœuds,
  176 441 opcodes, progrès 50/158, `SEARCH_CAP`, zéro LONG.
  **v13 ROAD-only 42×1 an** : polylignes complètes puis
  163 arêtes sous AITest, 79 375 opcodes de génération/validation,
  premier refus sur voirie urbaine `1281`, suivant `260`,
  3 contournements tentés/0 admissible, zéro LONG.
  **v14 ROAD-only 42×1 an** : réserve maximum 180k au premier
  couple sans hausse du cap 400k, diagnostic urbain dédié :
  premier couple `OPCAP` après 137 133 opcodes, deuxième
  **effectivement préqualifié** après 77 723 opcodes mais
  `SITE_B/NO_TESTABLE` (0 arrêt admissible sur 6 AITest),
  aucun chantier LONG. Toutes les parties OFF/ON saines,
  `profit_year` ON 18 881 £ contre AAA 93 624 £, sans
  nouveau LONG : ni résultat économique attribuable ni 5×5.
  Priorité suivante : sites effectivement constructibles dans
  les villes productives, compatibilité du front DT et des
  rues municipales, puis itinéraires/ouvrages réels ; si la
  demande physiquement captable reste <20 PASS/mois par bout,
  préqualifier une politique multi-quartiers distincte
  (défaut 0) plutôt que surdimensionner la flotte.
  **v15 ROAD-only 42×1 an** : scanner DT réversible sur la
  même arête routière, 12 AITest maximum/scanner toujours ;
  côté B du second marché **3 stations physiquement testables**
  contre 0 en v14. Les deux couples atteignent maintenant
  `VerifyTrace`, mais des arêtes urbaines rendent les tracés
  `UNBUILDABLE` / `OPCAP`, aucun chantier LONG.
  **v16** : chemin LONG contraint à traverser les véritables
  `front` connectés des deux stations, avec hash et chantier
  inchangés ; smokes sains mais `CORNER_SLOPE`, `CYCLE`,
  arêtes urbaines 260, zéro admission.
  **v17** : classement des fronts DT vers la ville opposée
  avant AITest, sans oracle AAA ni hausse d'opcodes. Les deux
  marchés sont examinés, échecs `OPCAP`/`GEOMETRY` et pente
  ou aire non libre au départ ; 0 corridor et 0/5 parités.
  **v18**, campagne ROAD-only appariée
  `road100_long_build_v18_road_sleeve_roadonly_seed42_1x1_20261028`,
  bundle `836a7731` : deux parties saines, manchons de voirie
  physiquement connectée explorés (12 puis 14 pas cumulés entre
  variantes de tracé), mais refus erreur 260 dès les sorties
  urbaines `162,127→161,127` et `72,234→71,234`.
  Deux plans en `OPCAP`, **0 admission, 0 construction LONG**.
  Opex 18 881 £/an / AAA 93 624 £/an, ratio 20,17 %,
  aucune amélioration attribuable à LONG, **0/5**. La
  calibration supplémentaire doit viser les sorties praticables
  de quartiers, pas seulement le prolongement rectiligne.
  **v19** : expansion locale BFS de la voirie avec sorties urbaines
  testées statiquement, mais 1×1 seed42 invalide : erreur de syntaxe
  Squirrel `parent` réservé. **v19b** corrige en `prev_index` :
  2/2 duels ROAD-only sains, bundle `26c0d014`, première
  obstruction plus tardive (index 17, voie municipale 1281),
  seconde erreur 260 puis `CITY_EXIT_A_NO_VIABLE_EXIT` ;
  toujours **0 LONG construit, 0/5 parités**. Audit de prix :
  villes 18–2 ≤35 et 26–10 ≤31 PASS/mois des sites testés ;
  prédiction favorable environ **1 322 £/an** et **746 £/an**
  de profit respectivement contre dizaines de milliers d'écart.
  Le prochain levier distinct `road100_pax_portfolio` (défaut 0)
  doit accroître la captation physique multi-quartiers et mesurer
  les bus utiles, non simplement relever le plafond LONG.
  [Pré-enregistrement du portefeuille PAX](road100_pax_portfolio_prereg_20261028.md)
  (mécanisme distinct, sélection avant construction, cible 5/5,
  aucune preuve économique avant smoke et 5×5 exposés).
  Le gel du chantier exige maintenant une recherche routière
  reprenable ou un autre réseau physique de quartiers ;
  aucune augmentation aveugle de cap ni `fallback` court.
  ROAD100-16 exige une nouvelle architecture de quartier
  et de réseau avant de dépenser sur 20–30 bus.
  Preuve d'exposition, opcodes, cinq horizons et garde de valeur
  exigées avant tout défaut ou porte 40×5.
  [Préréservation LONG](road100_express_corridor_prereg_20261028.md),
  [journal](road100_etapes_20261027.md).

- [x] **04/11 — RAIL-LONG v3, qualification économique après R6 TERMINÉE : NO-GO pour adoption.** Les quatre portes demandées sont complètes, saines et appariées, référence `rail_long=0` contre `3`. **A rail 40×3 : −7,39 k£/an**, IC95 [−65,55 ; +52,72] k£ ; **A multimodal 40×3 : −64,46 k£/an**, IC95 [−128,44 ; −1,23] k£ ; deux `fail_primary`. **B rail 20×10 : +47,15 k£/an**, IC95 [−77,91 ; +154,97] k£, valeur +1,51 %, `pass non_erosion` ; **B multimodal 20×10 : +99,74 k£/an**, IC95 [−60,77 ; +262,41] k£, valeur +1,76 %, `pass non_erosion`. Les deux B sont **diagnostiques**, sans preuve de gain ni adoption puisque les A ont échoué. Docker redevenu fonctionnel, B multimodale `…_r2` (40/40 parties) exécutée après l'échec pré-lancement r1 ; bundle `dd1fb8…` identique à A multimodal et B rail, A rail `071e51b4…` différant seulement par journal INVEST-STALL OFF ; anciennes campagnes `4087fdfa…` non cumulées. **Défaut `rail_long=0` maintenu ; aucun commit/push.** [Rapport et audit](rail_long_v3_gates_post_r6_20261104.md).

- [x] **04/11 — INVEST-STALL P0 : diagnostic passif et sous-cause moteur vérifiés.** Le premier rail seul 2×8 (17/65537, bundle `071e51b4`) attribue **51/51 refus**, dont 31 `mixed_wagons` avec marge positive et 20 `unsafe_or_busy` tous avec gare partagée. **Deux nouveaux smokes 1×6 sains, même bundle `dd1fb8e3`** : 10/10 annulations wagon en dépôt avec `loco_capacity=-1`, `wagon_mismatches=0`, marge positive ; la garde `GetCapacity(...) == 0` est la **seule cause échouée**, 20/20 refus détaillés, 0 achat `done`. Ancien 2×8 sans sous-sonde : ne pas extrapoler ses 31 événements. **57 tests INVEST-STALL + 12 V284 + 21 v3 verts**, projection OFF inchangée, aucun défaut/commit/publication. [Rapport P0 et preuves](invest_stall_diagnostic_p0_20261104.md).
- [x] **04/11 — RAIL-LONG v3, correction transactionnelle EXISTANT : validation technique terminee, non adoptee.** Sur `exp/rail-sibling-20261102`, attentes de quai bornees, ordre temporaire vers le depot exact, restauration des deux ordres et reservation face a V284. Diagnostic R3 rail seul 4×6 : 4 parties saines, 4 modernisations de 8/9/8/11 wagons (240/270/240/330 unites) et verifications physiques. L'alerte `stagnation_suspect` sur 8191 concerne l'activite economique (horizon complet, pas d'erreur NoAI). **Defaut de reprise Save/Load identifie et corrige** : catalogue wagon vide au premier tick apres Load ; attente et rafraichissement bornes. Nouveau bundle R6 : trois anciennes sauvegardes reprises, 3/3 `upgrade_done`, 3/3 compositions/quais/ordres confirmes sur sauvegardes, aucune erreur moteur ; 21 contrats v3 et 11 v2, projections OFF OK. [Rapport et preuves](rail_long_v3_upgrade_20261104.md). **Aucune porte economique nouvelle, aucun defaut modifie, aucun commit/push/merge.** Une qualification economique nouvelle serait un chantier distinct a pre-enregistrer.
- [ ] **04/11 — INVEST-STALL, achats de wagons et extension transactionnelle des quais 7→6 : NON QUALIFIÉS.** Sur `exp/rail-sibling-20261102`, diagnostic rail seul 4×6 : +42,6 k£/an (3 V / 1 D, IC95 recouvrant zéro), 2 nouvelles lignes et **0 extension** ; prolongation 17/65537 à 8 ans : −103,1 k£/an, 24 refus `unsafe_or_busy`, aucune extension. Autopsie ancienne : 37 sélections wagon, 30 refus de revalidation, 6 délais d'approche, **0 achat terminé** ; gares partagées et quai 8 tuiles hors cible 7/6. **P0 approfondi clos :** 2×1×6 ans supplémentaires, **10/10 `mixed_wagons` expliqués par `GetCapacity(...)=-1` (au lieu de 0) et `wagon_mismatches=0`** ; aucune marge négative. **P1 restant :** vérifier le contrat API et corriger seulement la garde locomotive défectueuse sans autoriser des wagons hétérogènes, prouver au moins un achat `done` et sa capacité/profit physiques ; puis constructibilité, rollback, Save/Load à mi-transaction et portes économiques ON/OFF. Save/Load générique 1975 sain mais non probant pour une extension interrompue. **Défaut `invest_stall=0` maintenu, aucune adoption ni porte formelle.** [Rapport P0](invest_stall_diagnostic_p0_20261104.md), [qualification](invest_stall_platform_qualification_20261104.md), [pistes](invest_stall_obstacles_20261104.md).
- [ ] **29/10 — Renforts AIR V161 : rendement marginal net (implémenté, duels descriptifs sains, NON QUALIFIÉ en A/B).** Les constantes et replis V161 sont retirés ; chaque renfort représente un seul avion et utilise `ΔP = ΔR_net − ΔE − ΔA`, avec cannibalisation C121 quand estimable, prix moteur réel, contrôle du palier de flotte et revalidation avant achat. Sans marge exploitable : refus explicite, aucun profit moyen de repli. Smokes défaut sains, Save/Load défaut et ESTIM=31 avec `LOAD_RECONCILE` positif ; 10 renforts C121 observés en 3 ans plus 2 sur reprise partiellement chevauchante. Les huit ancres historiques ESTIM OFF et les deux empreintes AIR/V233L ont été réconciliées sans mise à jour aveugle ; **suite finale 3 232 tests OK (5 skips, 2 attendus)**. **AIR seul contre AAA, bundle b21f99c8, ESTIM=0 et EB2=0** : 40×3 complet, profit 1,977 M£ vs 2,008 M£ (98,43 %) ; 20×10 complet, profit 1979 2,358 M£ vs 2,494 M£ (94,53 %), valeur +45,95 % ; 0 échec. **Ce ne sont pas des portes A/B V161** : la référence historique du même code n'a pas été comparée, et le bundle gelé provient d'un arbre local comportant d'autres opt-in OFF. Risques non tranchés : hubs C121 sans re-devis et transitions moteur V252 refusées sans modèle mixte ; mesurer refus, expositions `physical`, opcodes et profits appariés. Voir [rapport V161](v161_rendement_marginal_net_20261029.md) et [duels AIR 40×3 / 20×10](v161_aironly_duels_20261029.md). Aucun changement de défaut ni adoption décidée.
- [ ] **29/10 — AIR seul : expliquer le déficit d'aéroports face à AAAHogEx (demande utilisateur, à traiter plus tard).** Partir des mêmes duels 40×3 et 20×10 V161, sur cartes et graines appariées : ventiler les aéroports OpexAI/AAAHogEx construits et actifs, les villes ou zones où AAAHogEx détient un **monopole de desserte aérienne** (définir explicitement la proximité, la couverture et l'absence d'aéroport concurrent ; compter par graine et par année), et les villes encore libres chez OpexAI. Reconstituer pour chaque opportunité manquée le catalogue AIR, les seuils de demande/ROI, la trésorerie, le foncier, la concurrence, les délais de scan et les échecs de construction. Auditer les **distances minimale et maximale** applicables aux vols OpexAI (bornes du catalogue, filtres de candidats, portée du moteur, cartes et modes), puis les comparer aux distances effectivement exploitées par AAAHogEx. Quantifier l'effet sur les passagers, la flotte, les recettes et le profit réel ; d'abord diagnostics sur archives, nouveau banc seulement si les données sont insuffisantes. Aucune modification de comportement ou de défaut sans validation.

### 27/10 — Débloquer la construction précoce pour rattraper AAAHogEx à 5 ans (air seul, rail seul, multimodal)
## Priorités actualisées après POST-1974 et décision du 30/10

**Sources : [analyse décennale et priorités](estim31_priorites_20x10_20261030.md) ; [résultats intégraux des trois variantes 20×10](estim31_trois_variantes_20x10_detail_20261030.md).** Le défaut élu passe de **103,24 % AAA en 1974 à 66,56 % en 1979** ; le profit AAA augmente de **3,572 M£/an** sur cette période contre **1,343 M£/an pour Opex**. En 1979, Opex a **29,6 trains contre 56,3**, **84,3 avions contre 48,0**, et **14,74 M£ de caisse sans prêt**. Les recettes réelles PLYR du gagnant sont en retrait de **1,168 M£ sur le RAIL** et **0,857 M£ sur l'AIR** (postes YTD jusqu'au 1er décembre, pas profits marginaux). **Ce sont des symptômes observés, pas encore les causes.**

| Rang | Action prioritaire | Suite et critère de clôture |
|---|---|---|
| **P0 diagnostic : clos, NO-GO levier** | **POST-1974-ENTONNOIR** : trois 20×10 et un 1×10 sondé réconciliés, entonnoirs AIR/RAIL/flottes et dépenses vérifiés | [Clôture factuelle](post1974_entonnoir_20261030.md#7-réconciliation-finale-preuve-physique-et-clôture-du-diagnostic) ; absence de preuve de projet injustement écarté interdit de changer le défaut |
| **P0 opcodes : 1** | **AIR-COVERAGE-STOP / EB-1** : cesser de chercher de nouvelles villes quand le vivier est épuisé | Un scan initial, puis veille ; réveil des **nouvelles recherches de villes uniquement sur `ET_TOWN_FOUNDED`**, sans boucles ni starvation |
| **P1 physique : 2** | **V233L-CONSTRUCTIBILITE** : comparer deuxième voie obligatoire et alternative réalisable | Contre-factuel physique sur les OD bloquées, coût et profit réel avant levier |
| **P1 réparation : 3** | **RAIL-REPAIR-SITE / EB-2 / EB-6 / P4** : échec de quai/gare/jonction | Tester **une alternative réellement constructible** à `SITEA/B/AB` ou `STNFAIL`, avec coût et repli transactionnel |
| **P1 réparation : 4** | **RAIL-REPAIR-V131** : tracé pré-calculé devenu bloqué | Réparer uniquement le segment ou le quai invalidé et mesurer le gain de lignes rentables |
| **P1 réparation : 5** | **RAIL-REPAIR-ASTAR / RAIL-REPAIR-POSE** : A* échoué ou pose partielle échouée | Distinguer `ABND/NOPA` de `TRKFAIL/LOOPFAIL`, reprise bornée et rollback sûr |
| **P2 économique : 6** | **RAIL-RENDEMENT-TARDIF** : production, note de gare et renforts V284 | N'acheter que des capacités supplémentaires dont la recette marginale et la géométrie sont démontrées |
| **P2 économique conditionnelle** | **PORTFOLIO-CAPITAL / EB-4 / ESTIM-1** : capital non réinvesti | Après preuve de projets rentables et constructibles perdus ; pas de correction arbitraire |
| **P0 technique parallèle** | **QUALITÉ-TESTS-ESTIM31** : grand harnais et assertions restés sur les vieux défauts | Corriger la suite sans toucher au code économique élu ; anciens résultats et erreurs documentés |

- [ ] **V233L-CONSTRUCTIBILITE — test physique contre-factuel, suite ciblée du diagnostic clos POST-1974-ENTONNOIR.** Sous le défaut `estim_unifie=31`, `eb14_progressive=3`, reprendre sur la **même carte/sauvegarde** les OD fret dirigées **44972→59980** (`NOPLAN2/SEARCH_ABND`, 1978), **50791→7810** (`NOPLAN2`, 1979) et **50791→12090** (recherche non terminée en décembre 1979). Comparer plan A* primaire, gare A/B, double voie V233L obligatoire et **vrai test ou construction monovoie**, sans supposer que la présence d'un plan primaire rend la ligne bâtissable. Mesurer coût effectif, cadence/capacité, recette annuelle et profit réel/marginal, en distinguant temps de recherche, limite d'itérations, terrains et conflits avec AAAHogEx. **GO seulement** si au moins une OD perdue est `profit > 0`, financée, effectivement constructible dans un contre-factuel et qu'une option opt-in gagne sur un protocole préenregistré multi-graines ; sinon **NO-GO** documenté. Ne pas changer le défaut sans preuve. [Dossier source](post1974_entonnoir_20261030.md#7-réconciliation-finale-preuve-physique-et-clôture-du-diagnostic).

  **Avancement 30/10 :** instrument `v233l_constructibilite=0/1/2` prêt en worktree isolé (OFF / devis physique passif / repli mono gardé par profit, financement et re-devis), 16 tests hôtes verts et smoke 1×1 sain. **Duel exploratoire 1×10 graine 42 : repli mono −429 580 £/an de `profit_year` et −10,44 % de valeur face au mode diagnostic, `fail_primary_and_value_guard` ; aucune adoption.** **Tâche toujours ouverte** tant que les trois OD n'ont pas été rejouées sur sauvegarde identique avec constat de construction et profit réalisé. [Rapport et protocole](v233l_constructibilite_20261030.md).
- [ ] **RAIL-RENDEMENT-TARDIF — volume supplémentaire réellement profitable après 1974 (EB-3, V284, V286, ESTIM-1).** Auditer production, note des gares sources, fréquence de ramassage, attente, wagons, coût/ROI marginal d'une rame supplémentaire et géométrie de sa boucle. Sous ESTIM31, `OpexV284Select` exige notamment une ligne fret à **un seul train**, de l'attente ≥ capacité d'un wagon et un gain marginal positif. **Sortie :** capacité additionnelle réellement vendable et plan physique. La **réparation en cas d'échec** des nouvelles lignes est un chantier distinct réactivé ci-dessous, et non une sous-tâche de V284. [Analyse](estim31_priorites_20x10_20261030.md#5-priorisation-recommandée-aucune-adoption-à-ce-stade).

## Livré ou clos — résultats vérifiés

- [x] **POST-1974-ENTONNOIR — diagnostic complet, verdict `DIAGNOSTIC_NO_GO` (30/10).** 3×20×10 archivés (sources et empreintes), 1×10 graine 42 `probes=2/131330` **2/2 complet**, déduplication dirigée de **9 OD RAIL sélectionnées : 3 construites, 5 tentatives en échec, 1 en cours** ; **3 chantiers AIR** pour **2 OD**. Les trois `RAIL_BUILD` 1977 totalisent **411 212 £ payés**, en accord avec C63 ; deux lignes fret construites ont un profit réel positif en 1978 (**30 843 £**, **25 294 £**). Les **92 passes AIR de 1978 instrumentées** n'exposent aucun nouveau candidat malgré **5,81–7,96 M£** disponibles. Refus/attente/site/budget physique/flotte séparés ; C63 1979 **censuré**, coûts prédits distincts des débours. **Aucune preuve d'un projet rentable, bâtissable et injustement rejeté : NO-GO pour toute modification**, pas une preuve d'absence de tels projets. Reste uniquement le **contre-factuel physique séparé V233L-CONSTRUCTIBILITE** ci-dessus. [Rapport et clôture](post1974_entonnoir_20261030.md), [journal diagnostique agrégé](post1974_entonnoir_seed42_1x10_20261030.json), [archives comparées](post1974_archives_20261030.json).
- [x] **ESTIM-31 AIR × RAIL : optimisation combinatoire et élection terminées, trois variantes intégralement documentées.** Top 3 40×5 figé : **106,062928693 %**, **105,171758309 %** et **103,798667198 %** ; trois vrais duels 20×10 sur 20 graines communes, 40/40 parties saines chacun, empreintes validées. À dix ans, ratio des **deux profits moyens du même duel** (pas moyenne des ratios individuels) : **V161 AIR2,00 / RAIL0,75 : 66,557726256 %** (Opex **4 255 528 £**, AAA **6 393 740,05 £**), V161 AIR2,50 : **65,921947052 %** ; V161 × C121 N1/N2 : **65,188575006 %**. Aucun veto économique fondé sur Wilcoxon, IC95, `gain_short` ou valeur de société. [Analyse finale](estim31_phase_combinatoire_20261030.md), [rapport détaillé des trois résultats (années, graines, PLYR, paramètres, SHA)](estim31_trois_variantes_20x10_detail_20261030.md), [classement JSON](estim31_top3_20x10_20261030.json).
- [x] **Nouveau défaut OpexAI installé et publié sur `origin/master` le 30/10.** Commit de production `7160c6f5`, complété par la documentation `2429d175` ; push fast-forward normal confirmé, `master` local sale non modifié. Source exacte du bundle gagnant, quatre bibliothèques NoAI vérifiées, options publiques `estim_unifie=31`, `eb14_progressive=3`, `probes=2`, prior AIR **2,00**, RAIL **0,75**, poids **15**, pente RAIL, V161 marginal same-engine, scan C121 exhaustif N1, V249=2, EB2=0, charge AIR min=0. Anciens paramètres sélectionnables **explicitement**. Deux vrais Save/Load seed999, défaut sans options et configuration explicite : `LOAD_RECONCILE` positif ; tests ciblés et suites CI verts. [Validation / limites](estim31_default_validation_20261030.md), [manifeste](estim31_default_promotion_20261030.json).
- [x] **C121 : bornes d'élagage et choix moteur sous ESTIM sécurisés.** Les fonctions OFF historiques sont identiques octet pour octet à la base ; les raccourcis économiques non prouvés ne tronquent plus le FullScan sous ESTIM. Les moteurs 223/228/220 sont suivis comme **stocks survivants**, pas achats bruts. [Contrat](estim31_default_c121_verified_20261030.json).
- [x] **V161 : rendement marginal net du renfort AIR livré** dans la configuration gagnante, avec garde d'achat et Save/Load. Les calculs particuliers aux nouveaux aéroports et aux remplacements V252 restent des chantiers différents. [Rapport](v161_rendement_marginal_net_20261029.md).
- [x] **EB-2 : repli de gare neuve sur échec V178 étudié puis non adopté.** Porte A rail seul 40×3 défavorable (−19,1 k£/an), diagnostic à cinq ans descriptif, `eb2_new_station_fallback=0` conservé dans le gagnant. [Diagnostic](eb2_maturation_20261028.md).
- [x] **EB-7 : première ventilation opcodes et investissements par sous-tâche livrée.** Échantillon 3 graines × 5 ans sur AIR/RAIL/multimodal ; la comptabilité transactionnelle exhaustive est un sujet séparé ouvert ci-dessous. [Archive](journaux/journal_2026-10-30_transfert_taches.md).
- [x] **EB-8 : correction de l'analyse GOOD dédoublonnée livrée** (`f7cff8b3`) : 614 paires fictives → 56 liaisons exploitables. La correction des acceptations de **production** reste **EB-10**.
- [x] **EB-9 : mesure de sites AIR puis `air_site_ranked` qualifié et fusionné**, choix `1` (`fef644a8`) après porte A 40×3 et porte B 20×10 AIR seul. Le cas multimodal n'a pas une qualification causale propre et reste à examiner.
- [x] **EB-11 : classement des sites de gare façon AIR réfuté** à la sonde, davantage d'opcodes, `SITEAB` lié à la jointure plutôt qu'à l'ordre des quais ; pas de porte A.
- [x] **EB-12 : bilan du 27–28/10 établi**, suites reportées dans les chantiers ci-dessous ; pas de tâche autonome de bilan.
- [x] **Sous-lots historiques P1–P6, RAIL-CAPEX-1, FRONT-PAX-1/2, AIR-FLOTTE-1, AIR-MONOPOLY-1, RLW et V303/V304/V308/V309 : clôtures/verdicts documentés**, aucune nouvelle adoption implicite. P6 abandonné ; P3 ne se reprend que par AIR-LOAD-1. Les travaux ultérieurs de ce domaine ont leur propre item ouvert quand justifiés. [Historique intégral](journaux/journal_2026-10-30_transfert_taches.md).
- [x] **V167 : réglage explicite `probes=0` coupe les panneaux et sondes associées.** **Correction de statut : `probes=2` est le nouveau défaut public**, car il fait partie de la configuration gagnante ; la réduction du travail résiduel des sondes reste ouverte.

## Priorités ouvertes — actions avec critères de sortie

- [ ] **QUALITÉ-TESTS-ESTIM31 — moderniser la suite de régression sans toucher au gagnant.** La découverte générale historique affiche **3 175 tests, 84 échecs, 16 erreurs** sous le nouveau défaut, dont des attentes `estim_unifie=0` et des instantanés obsolètes ; avant promotion elle avait déjà **3 124 tests, 2 échecs et 12 erreurs**. Les tests dédiés et la CI **53 + 38 + 4** passent. Distinguer ancien comportement **explicitement OFF** du défaut public, adapter assertions et fixtures, supprimer les erreurs d'import / effets de bord, prouver une fullsuite appropriée verte. [Preuves](estim31_default_validation_20261030.md).
- [ ] **AIR-COVERAGE-STOP / EB-1 — STOPPER les recherches répétées de nouvelles villes AIR quand il n'en reste aucune disponible.** **Périmètre volontairement limité** par décision utilisateur : une énumération initiale des villes potentiellement équipables puis, une fois le vivier **épuisé**, mise en veille de la *recherche de nouvelles villes et de nouveaux sites AIR* ; ne plus refaire périodiquement les passes « zéro candidat », ni les réactiver par TTL, croissance urbaine, caisse, disponibilité des moteurs ou simple passage du temps. **Seul `AIEvent.ET_TOWN_FOUNDED` réveille une nouvelle recherche de villes** (nouvelle ville seulement, ou mise à jour incrémentale du vivier), événement déjà traité dans `events.nut`/`event_handlers.nut::_onTownFounded` : préserver le rafraîchissement du catalogue et coalescer les événements. Un projet AIR **déjà calculé** et les opérations sur les lignes/aéroports existants (flotte, maintenance, achèvement) ne sont **pas** une nouvelle recherche de villes : les laisser fonctionner normalement. Spécifier précisément « ville disponible » selon les gardes actuelles et persister le mode veille/cursor après Save/Load, sans perdre l'initialisation au premier lancement. **Sortie :** 0 nouvelle passe de découverte hors `ET_TOWN_FOUNDED` après saturation, réaction à 1 puis plusieurs créations, OFF strictement identique (option défaut 0 avant qualification), coûts en opcodes et tests Save/Load/partie réelle ; pas de nouveaux bonus monopole, ni d'étude de rendement AIR. [Décision et indices](journaux/journal_2026-10-30_repriorisation_air_rail.md).
- [ ] **EB-3 — vivier RAIL absent en multimodal en 1970 : expliquer précisément les étapes.** Le diagnostic early_build montre zéro chantier rail financé ; ESTIM-31/EB14=3 a modifié le préchargement, donc refaire d'abord la lecture des événements et de `projects.nut` **au nouveau défaut**, sans conclure que le vivier est vide si une priorité AIR bloque seulement son financement. Puis test ciblé si le problème persiste.
- [ ] **EB-4 — caisse / arbitrage d'investissements 1970–1972.** Reconstituer les vrais refus de financement, investissements et délais, puis tester un arbitrage AIR/RAIL qui n'évince pas les nouveaux projets rentables ; ne pas refaire les seuils historiques déjà refusés sans hypothèse distincte.
- [ ] **EB-5 — débouchés GOOD précoces et chaîne industrielle.** Étudier les usines avec 2–5 villes réellement acceptantes par carte, sources actives et `origin_served`. Distinguer l'analyse dédupliquée EB-8 du bug de production EB-10, puis qualifier uniquement des projets constructibles.
- [ ] **RAIL-REPAIR-SITE / EB-6 (réactivé : EB-2 + P4 + V178/V307) — réparation à l'échec de gare/quai/jonction.** Déclencheurs `SITEA`, `SITEB`, `SITEAB`, `STNFAIL`, y compris jonction partagée `shared_dest=1`. Après échec, **réexaminer les options physiques** : quai différent/plus court, jonction par un autre accès, gare neuve ou autre station adjacente, avec devis réels ; conserver `src/dst/cargo`, ne pas relancer indéfiniment la même option déjà échouée. Journaliser nombre d'OD distinctes converties en `RAIL_BUILD`, itérations/opcodes et profit/marge finale. **Prototype isolé 30/10 :** `rail_repair_join_site=1` essaie un quai joint orienté dans deux anneaux après échec de parallèle V178 (`shared_dest=1`), avec devis AITest et ID existant ; hôtes verts, smoke/SaveLoad/exposition/constructibilité moteur restent à faire, les autres cas SITE/STNFAIL restent ouverts. **Historique préservé** : ancien EB-2 (40×3 : −19,1 k£/an, non adopté), P4 inerte/NO-GO, V307S/R non adopté ; la nouvelle tâche **ne qualifie pas** ces prototypes. [Prototype et protocole](rail_repair_site_v131_focus_20261030.md), [réactivation](journaux/journal_2026-10-30_repriorisation_air_rail.md).
- [ ] **RAIL-REPAIR-V131 (réactivé) — réparation de tracés préparés devenus invalides avant pose.** Déclencheurs `track_blocked`/`station_blocked` ou blocage ponctuel pendant la revalidation après changement de carte (gare/aéroport concurrent, route, maison, rail, obstacle). Réutiliser la partie saine du tracé, contourner localement par A* borné et déplacer si besoin un quai ; préserver les emprises propres, ne pas abandonner tout un itinéraire à la première tuile obstruée. Prendre la base actuelle ESTIM31, mesurer OD uniques récupérées, coût réel, temps et profit. **Prototype isolé 30/10 :** `rail_repair_v131_focus=1` réutilise l'état V131 avec un seul groupe d'obstacles de ≤4 tuiles, 1 splice, quai déplacé ≤4 tuiles, A* ≤900 itérations. Contrats hôtes verts ; smoke/SaveLoad moteur, cause physique, opcodes et revenu réel à mesurer. **V131c historique** : porte A 40×5 **−31,55 k£/an**, `fail_primary`, défaut 0 ; **ne pas recycler son verdict comme un GO**. Protections anti-doublon, rollback et Save/Load obligatoires. [Prototype et protocole](rail_repair_site_v131_focus_20261030.md), [historique](journaux/journal_2026-10-30_transfert_taches.md).
- [ ] **RAIL-REPAIR-ASTAR (réactivé) — seconde chance ciblée après `ABND`/`NOPA` d'une recherche primaire.** Une recherche échouée ne doit pas condamner sans examen toute OD rentable : distinguer plafond d'itérations, gares enclavées, direction de recherche, couloirs et obstacles réellement infranchissables. Après échec, tester **au plus un jeu borné d'alternatives nouvelles et physiquement justifiées** (extrémité/quai, sens inverse, couloir ou reprise du plan) ; mémoriser l'échec par OD et configuration pour éviter les re-tentatives stériles. Conserver les résultats négatifs du simple relèvement de plafond, des variantes V307 inverse, V303 et V304 : ne pas ressusciter ces options à l'identique. **Prototype 30/10 :** `rail_repair_astar_pair=1` choisit une autre paire de quais déjà testés après ABND/NOPA et reprend un A* unidirectionnel borné à 900 itérations ; aucun GO physique, Save/Load ni économie mesuré. **Sortie :** `ABND/NOPA` convertis en lignes construites avec marge positive sans gonflement non borné des opcodes. [Prototype et limites](rail_repair_astar_pose_20261030.md), [RAIL-ECH/V307](journaux/journal_2026-10-30_transfert_taches.md).
- [ ] **RAIL-REPAIR-POSE (réactivé) — récupérer un chantier `TRKFAIL`/`STNFAIL`/`TRACK_FAIL`/`LOOPFAIL` après pose partielle.** Identifier la **commande et la tuile** réellement refusées, essayer un contournement local / un autre ordre de pose / une connexion de quai compatible, puis revalider rails, ponts, tunnels, aiguillages et trains. Surtout **ne pas laisser des stations, voies ou véhicules orphelins** : rollback transactionnel, vérification d'ownership et interopérabilité Save/Load. Réutiliser l'analyse V233L `TRACK8–10` (défaut 0 en expérimental) sans prétendre que ses réparations sont qualifiées sur le défaut ESTIM31 ; ne pas additionner les achats annulés au coût final. **Prototype 30/10 :** `rail_repair_pose_order=1` tente une inversion d'ordre de deux commandes `BuildRail` sur tuiles vierges et garde l'annulation transactionnelle en échec ; `STNFAIL` et `LOOPFAIL` gardent leurs diagnostics, réparation conditionnée à une comptabilité d'ownership et un test moteur sûr. **Sortie :** reprise réussie d'une OD condamnée rentable, suppression des débris, puis gate multimodale. Distinct de **V233L-CONSTRUCTIBILITE**. [Prototype/limites](rail_repair_astar_pose_20261030.md), [V233L](v233_long_good_20261025.md).

  **Qualification intégrée 30/10 — tâches rail toujours ouvertes :** quatre réparateurs rail opt-in défaut 0 ; après correction d'une erreur Squirrel `astarRepairTried` sur le stock C121, **79 tests hôtes verts, OFF/ON 1×1 sain et identique, Save/Load réel 13+13 autosaves avec `LOAD_RECONCILE`**. Le 5×5 OFF/ON est sain (10/10) et montre `+94 894 £/an` en moyenne, **4 victoires/1 défaite, Wilcoxon p=0,4375, IC95 incluant 0**, avec une grosse perte graine 999. **Signal exploratoire non qualifié, pas de porte A** : manque preuve par OD que les réparations ont sauvé des chantiers réellement rentables ; `STNFAIL/LOOPFAIL` attendent un ledger d'ownership transactionnel. [Rapport intégré et données](rail_repairs_integration_validation_20261030.md).
  **RAIL-REPAIR-IDLE-6M - politique conditionnelle (30/10) :** les quatre reparateurs SITE/V131/A*/POSE opt-in et le repli construit V233L `=2` ne peuvent intervenir qu'apres **six mois calendaires sans nouvelle ligne AIR/RAIL/ROAD/WATER** ; chaque nouvelle ligne reussie remet le compteur a zero. Le diagnostic passif V233L `=1` reste libre. Les Save/Load compact et complet (13+13) conservent la date ; 96 tests hotes et smoke OFF/ON 1x1 sains. **Defauts inchanges et qualification economique ouverte**. [Contrat et preuves](rail_repair_idle_sixmonths_20261030.md).
  **Porte A RAIL seul 40×5 terminée le 30/10 — NO-GO (nouveau profil IDLE-6M) :** 80/80 parties saines, `profit_year` moyen de 1974 **1 770 916 → 1 772 916 £/an**, delta apparié **+1 999,775 £/an (+0,113 %)** ; **15 victoires, 15 défaites, 10 égalités**, Wilcoxon exact `p=0,82358`, IC95 bootstrap **[−37 210 ; +41 627] £/an**, ratio valeur **100,963 %**. Le seuil +4 %, le test de significativité et la borne basse échouent : **pas de porte B, aucun défaut activé**, chantiers rail non clos (manquent exposition physique et preuve d'OD rentables). Le contre-factuel V233L `=2` est hors de ce paquet. [Préenregistrement, résultats, graines et SHA](rail_repair_idle_railonly_gateA_40x5_20261030.md).
  **Exposition RAIL-IDLE-6M 40x5 verifiee (30/10) :** replay diagnostique separe avec `probes=258`, 40/40 jeux sains. La garde six mois est effectivement positive sur **26/40 graines** (30 activations). **6 tentatives SITE, dont 5 vraies constructions `RAIL_BUILD site_repair=1`** sur graines 100, 512, 12345, 54321, 65537 ; trois reprises A* toutes `ABND` ; 0 trace POSE et V131. Les cinq lignes ont ete construites en 1974 et leurs profits sont seulement **predits**, pas encore mesures a maturite. Les traces et la decision economique `NO-GO` sont distinctes : aucun defaut active. [Preuve et 40 graines](rail_repair_idle_exposure_40x5_20261030.md).
  **Maturation + B RAIL-IDLE-6M (31/10, conclu) :** pilote 5x10 sur les 5 graines avec RAIL_BUILD site_repair=1 : 10/10 jeux sains, 5/5 OD physiquement retrouvees et benefices VEHS observes a maturite ; delta societes en 1979 **+104 971 GBP/an** (+5,46 %), mais graines selectionnees et sonde probes=258. Escalade autorisee : B exploratoire 20x10 RAIL seul, 40/40 jeux sains, **-10 466 GBP/an (-0,498 %)**, 8V/12D, Wilcoxon p=0,571, IC95 bootstrap [-53 506 ; +34 582], valeur 99,62 %. **B non-erosion PASS**, mais **gain non demontre, A 40x5 NO-GO inchangee, defauts 0**, aucun GO production. Cible future : SITE seul, rentabilite physique realisee et selectivite ; A* 3/3 ABND, V131/POSE non observes. [Rapport 10 ans et preuves](rail_repair_idle_maturation_10y_20261031.md).
- [ ] **EB-7 phase 2 — dépenses réellement payées, par objet et par mode.** L'analyse agrégée est close ; reste la comptabilité fine chantier, stations, dépôts, véhicules **achats bruts vs ventes**, et dépenses PLYR/`AIAccounting` vs devis/test mode, rapprochées des soldes ; recenser les opcodes incomplets. Sortie : lecteur testé, réconciliation Save/Load et preuves d'absence de double comptage.
- [ ] **EB-9 suivi — `air_site_ranked` en multimodal, conditionnel au STOP AIR.** Tester le comportement du classement sur l'énumération initiale ou lors d'un **vrai `ET_TOWN_FOUNDED`** ; ne pas réactiver des scans cycliques après saturation pour comparer des rangs. Examiner les archives et l'exposition d'abord, sans modification tant que `AIR-COVERAGE-STOP` n'est pas isolé.
- [ ] **EB-10 — destinataires express fictifs GOOD/MAIL et sentinelle `INVALID_INDUSTRY=65535`.** `catalog.nut` inclut des villes sans acceptation réelle ; `lines.nut:OpexAbandonedPairKey` peut confondre INVALID avec une industrie légitime. Vérifier usages dans le HEAD élu, puis corriger séparément derrière gardes testées et qualificatifs de santé. Le correctif analytique EB-8 ne résout pas ces problèmes de production.
- [ ] **EB-13 — prévision RAIL passagers/courrier sous-estimée.** Comparer âge 1, 2 et 5, consommation de MAIL, croissance des villes et note de gare ; sur 39 graines, prédit moyen 34,7 k£ contre réalisé 61,0 k£ à âge 2, mais cette cohorte n'établit pas une amélioration causale. Modèle à calibrer sur échantillon indépendant et alternatives financièrement constructibles.
- [ ] **ESTIM-1 suite — prévisions et valeur marginale hors échantillon.** Le code bits 1/2/4/8/16 et le défaut 31 sont **déjà livrés** ; ne plus demander de créer `estim_unifie` ni de refaire les trois 20×10. Reste l'audit des erreurs de recette, coûts physiques pré-A*, amortissement et ROI marginal AIR/RAIL en fonction de distance ; réévaluer des variantes seulement sous nouvel objectif pré-enregistré. [Plan historique](estim1_modele_unifie_20261027.md).
- [ ] **FLOTTE-EQUILIBRE / V286 / V253 — rapport de capacité multimodale.** Mesurer par ligne, cargo et horizon trains, wagons, avions, production, attente et saturation, au nouveau défaut. Ne pas prendre les stocks 223/228/220 pour des achats ni les opcodes partiels pour CPU global. L'hypothèse d'optimisation combinatoire moteur n'est pas équivalente à « acheter plus de trains ».
- [ ] **DIST-BORNES-1 — cohérence des bornes route/rail/air.** Audit et variante unifiée `NO_GO_NON_EXPOSE` sur 5×5 1024² (0/5 nouvelles longues lignes, pas de A/B), correctif 201–250 fret V276/V269 opt-in sans exposition tardive 1024². Ne pas relancer les campagnes qualifiées ; mesurer les conditions de déclenchement V269 et pré-enregistrer un horizon qui couvre l'année +5 avant tout nouveau comportement.
- [ ] **PO-02 — échéance de publication propre à chaque vivier.** PO-01c est livré ; conserver les scans en cours et les candidats sains, coalescer les invalidations, mesurer révisions/cadence/opcodes et vérifier absence de starvation. Ne pas réintroduire V142/V143 réfutés.
- [ ] **MULTI-1 — suspendu par décision du 26/10, pas de relance automatique.** Trois leviers ROUTE/AIR non exposés, SHADOW fret routier sans projet physique qualifié et autopsie tardive C63 conservés aux journaux. Objectif historique 75 % AAA à 10 ans non atteint même sous nouveau défaut (66,56 % en 1979) ; étude de constructibilité et rentabilité tardive seulement après réautorisation explicite de la reprise.
- [ ] **OPCODES / IDLE-1 / AIList — travail utile dans les tours libres.** Distinguer `sleep_slack` de CPU consommé, mesurer les appels `AIList` L1/L2 rejetés et sous-tâches sans valeur ; revisiter C75 et les sondes non essentielles, sans réactiver les variantes vides ou les vieux benchmarks. Test d'équivalence des choix et du coût total avant adoption.
- [ ] **LATE-GAME-1 / V249a–c / V291 — excédent de caisse et actions tardives.** La version élue compte ~14,74 M£ de trésorerie en 1979. Étudier surplus durable, ROI marginal des statues, croissance urbaine et industries après saturation des lignes ; modes de difficulté et décisions humaines respectés. Ne pas confondre les dépenses « Autres » de PLYR avec les statues seules.
- [ ] **V233 chaînes transformées / V242 feeders / V226 réseau ferré en araignée.** Ce sont des programmes distincts de l'optimisation ESTIM31 ; ne pas réactiver les mécanismes V139/V266 ou les relectures V264/V265 déjà négatives. Nouvelle hypothèse exigeant marge par ligne et constructibilité démontrées avant banc.
- [ ] **V249a/b/c et V253 approfondissement.** Les statues V249=2 sont déjà dans le défaut, le choix C121 N1/N2 est **perdant sur 10 ans** dans le top3 ; restent la valeur d'une couverture additionnelle, prix marginal des équipements et choix du moteur sous flotte hétérogène, sans réutiliser comme promesse le gain +600k sur cinq graines.
- [ ] **Fair-play / parties humaines et sondes normales.** Audit V261/V262 et niveaux de difficulté déjà livrés ; définir explicitement une option de courtoisie testée, réduire journaux/panneaux inutiles en partie normale sans changer furtivement `probes=2` du défaut compétitif validé.

## Réserve et interventions conditionnelles — pas de lancement automatique

- [ ] **V163 grand banc multicargo, V164 oracle de classement, V150 cartographie eau, V208–V211 stratégies, V229 calibration distance, V242 route/rail feeders, V266 variantes et V286 mesures** : idées encore distinctes non démontrées. Évaluer d'abord doublons avec la voie ESTIM31 ou des tentatives rejetées. Les descriptions d'origine et les protocoles datés sont dans le journal de transfert ; un ancien « à lancer » n'autorise pas un nouveau Docker.
- [ ] **V291 cartographie/nivellement/canaux au niveau de difficulté très gênant, NewGRF et eau.** Nécessite les règles de terrain et de fair-play, une carte et un régime réellement exposés, puis qualification propre ; pas d'effet sur le défaut actuel.
- [ ] **V102 / GitHub Actions et vieux protocoles.** Les benchmarks historiques 40×3 et 20×10 restent reproductibles, mais la **sélection spéciale des finalistes ESTIM31** est déjà close par une autre règle explicite (ratio à 1979). Vérifier l'état réel des workflows avant mise à jour ; ne pas considérer les mentions « publication en attente » du 7/10 comme preuve actuelle.
- [ ] **Archives et diagnostics antérieurs :** R1/R19, R22, C116/C122, UR, V99–V112, V197–V216, V269/V270/V281, V276 grande carte, V228, V290 et autres dossiers historiques nécessitent un nouveau périmètre, sources mesurées et validation de pertinence. Les conclusions « non adopté » et « sans suite » restent closes. [Journal intégral](journaux/journal_2026-10-30_transfert_taches.md).

## Discipline de clôture

1. Une nouvelle tâche porte un **périmètre**, une **prochaine expérience ou action vérifiable**, son **statut**, ses **références** et un **critère de sortie**. Ne pas transformer un compte rendu en nouvelle action.
2. À la fin d'un lot, cocher la tâche et inscrire les résultats complets dans le journal du jour ; supprimer de cette page les anciennes consignes d'exécution qui ne correspondent plus au code.
3. Préserver les verdicts négatifs, les sources immuables et l'historique ; tester le **code actuel** et non les anciens défauts. Aucune campagne ne doit être relancée parce qu'une fiche datée porte encore le mot « en cours ».
4. Validation : santé des parties, même cohorte et source attestée, comparaisons dans le propre duel, fichiers Save/Load, `git diff --check`, commit de chemins explicites et push normal. Ne pas mélanger métriques PLYR réellement payées, factures nettes, stocks et devis.
