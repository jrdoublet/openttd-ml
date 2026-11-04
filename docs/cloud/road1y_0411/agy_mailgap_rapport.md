# Diagnostic MAIL routier (3 ans) — Décomposition écart AAA & Autopsie mail_net

Campagnes analysées : [`results/n_spread2_gateA`](file:///home/deploy/projects/wt-lineyield/results/n_spread2_gateA.jsonl) (40 graines, an 3), [`gha-41538472644-1`](file:///home/deploy/.claude/jobs/e230de46/tmp/gha/41538472644/summary.md) et [`n_mailnet12b_3y`](file:///home/deploy/projects/wt-mailnet/results/n_mailnet12b_3y.jsonl) (3 graines).

## 1. Décomposition de l'écart MAIL avec AAA (`n_spread2_gateA`, 40 graines, an 3)

Réf = `road1y_load_orders=1` ; Var (`spread2`) = `load_orders=1` + `road1y_spread_stops=2`. AAA adverse apparié.

| Métrique MAIL (fin 1972) | Opex Réf (`reference`) | AAA vs Réf (`AAAHogEx`) | Opex Var (`spread2`) | AAA vs Var (`AAAHogEx`) |
|---|---|---|---|---|
| **Lignes MAIL / graine** | 10,53 (méd 10,5) [tot 421] | 9,45 (méd 9,5) [tot 378] | 9,25 (méd 9,0) [tot 370] | 8,12 (méd 8,0) [tot 325] |
| **Fourgons MAIL / graine** | **84,30** (méd 84,0) [tot 3372] | **65,67** (méd 64,5) [tot 2627] | 73,42 (méd 77,0) [tot 2937] | 59,98 (méd 60,5) [tot 2399] |
| **Profit MAIL total / gr.** | **150,9 k£** (méd 144,7 k) | **213,0 k£** (méd 201,4 k) | 134,1 k£ (méd 138,3 k) | 185,1 k£ (méd 185,1 k) |
| **Rendement global £/fourgon** | **1 790 £/f** (méd gr. 1 753 £) | **3 243 £/f** (méd gr. 3 240 £) | 1 826 £/f (méd gr. 1 854 £) | 3 086 £/f (méd gr. 3 328 £) |
| **Distance Manhattan moy.** | 95,9 tuiles (méd 98) | 87,1 tuiles (méd 89) | 95,1 tuiles (méd 98) | 87,6 tuiles (méd 87) |
| **Attente aux gares (sacs)** | **7,45 sacs** (méd **4,0 sacs**) | **44,99 sacs** (méd **17,0 sacs**) | 10,87 sacs (méd 5,0 sacs) | 44,50 sacs (méd 15,0 sacs) |
| **Note de gare moyenne** | 143,2 / 255 (**56,2 %**, méd 147) | 169,0 / 255 (**66,3 %**, méd 175) | 137,6 / 255 (54,0 %, méd 141) | 171,3 / 255 (67,2 %, méd 178) |
| **Courrier livré T4 (sacs/gr)**| 989,0 sacs | 1 632,6 sacs (+65 %) | 892,1 sacs | 1 420,9 sacs (+59 %) |
| **Lignes MAIL sans bus** | **0 / 421 (0,0 %)** | **294 / 378 (77,8 %)** | **0 / 370 (0,0 %)** | **250 / 325 (76,9 %)** |

**Facteurs explicatifs de l'écart MAIL (+62,1 k£/an pour AAA, 15,7 % du retard total) :**
- **Suroccupation à vide chez Opex** : Opex déploie +18,6 fourgons (+28 %) mais son attente médiane est de seulement 4 sacs (fourgons aux 4/5 vides). AAA a 17 sacs en attente médiane et livre +65 % de courrier avec −22 % de véhicules.
- **Sélection des villes** : AAA choisit des paires intercités dédiées au courrier à forte production (`prod >= 27` sacs/m, souvent 50–115 sacs : Nonningstone, Sefingbridge, Trunbourne). Opex greffe ses filles [`mail_pax`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts.nut#L749) sur les lignes bus selon le profit bus, sans filtrer la production courrier du quartier.
- **Réseau autonome AAA** : 77,8 % des lignes MAIL d'AAA relient des paires de villes **sans aucun bus AAA**, contre 0 % pour Opex dont le MAIL est 100 % parasitaire des bus existants.

## 2. Pourquoi `road1y_mail_net` a échoué (138/317/189 puis 166/292/233 vs 177/364/322 k£/an)

Deux tentatives de réseau autonome intercités par grok :
1. Commit [`fb959178`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts.nut) / [`396c95d3`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts.nut) (`n_mailnet12b_3y`) : 7 ouvertures, 23 échecs `NO_TRACE` (tracé direct rigide), filles coupées par `ROAD1Y_MAIL_NET > 0`. Perte sèche.
2. Commit [`35332753`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts.nut) (`gha-41538472644-1`) : filles conservées, tracé voirie bus [`OpexRoadPlanPaxVoirie`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts.nut#L930). 16 lignes ouvertes sur 3 graines. Échecs restants : 16 `NO_TRACE`, 6 `NO_SITE_B`, 4 `TRACE`, 1 `BUILD_STOP_A`. Perte : 230 k£/an moy. vs 288 k£/an master.

### Causes structurelles et bugs :
1. **Éviction massive du capital bus (cause n°1)** :
   - Construire une route intercité isolée de 60–100 tuiles + dépôt + 2 arrêts coûte **15 à 25 k£ de capex**.
   - À 3 ans, un fourgon MAIL rapporte 2,5 k£/an : le payback de la voirie seule est de **6 à 8 ans**. À l'inverse, une ligne bus avec 4–6 bus rapporte 15–25 k£/an (payback **< 1 an**).
   - En ouvrant 6 à 8 lignes `mail_net` dès 1970, la trésorerie est siphonnée :
     - Graine `781335` : bus réduits de **25 lignes (101 bus, 299 k£)** à **16 lignes (61 bus, 152 k£)**. Perte bus = **−147 k£**, pour seulement +53 k£ de courrier. Solde net : **−94 k£** !
     - Graine `613553` : bus réduits de 28 à 24 lignes ; profit bus tombe de 319 k£ à 216 k£ (**−103 k£**) pour +50 k£ de courrier. Solde net : **−53 k£** !
   - Chronologie : les ouvertures des lignes bus 4, 5, 6 en 1970 sont retardées de **2 à 4 mois** (ex. s100 ligne 4 décalée de mai à juillet 1970, ligne 5 de juin à août).
2. **Ordres `OF_FULL_LOAD_ANY` bilatéraux (bug / défaut conceptuel)** :
   - [`bus_districts.nut:1045`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts.nut#L1045) et [`builder_road.nut:6488`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_road.nut#L6488) imposent le chargement complet aux deux bouts.
   - Or, sur les paires à production modérée, un fourgon de 22 sacs attend 2 à 4 mois pour se remplir. La marchandise vieillit, la note s'effondre et le véhicule immobilisé ne produit rien. Le chargement complet sur le MAIL a d'ailleurs été **formellement réfuté** par [`road1y_mail_full`](file:///home/deploy/.claude/projects/-home-deploy-projects-openttd-ml/memory/road1y_gap_mail_cap.md) (Porte A = −4,5 k à −8,2 k£/an).
3. **Plafond et cadence de renfort trop stricts** :
   - [`OpexRoad1yRefleetMailNet`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/bus_districts.nut#L1133) exige `minWait > 30` **aux deux bouts** simultanément et n'évalue qu'une fois par mois, contre un contrôle hebdomadaire à 4 véhicules/lot chez AAA. La flotte ne monte pas assez vite là où la demande existe.

## 3. Conclusion & État du gisement MAIL à 3 ans

### Bilan des réfutés & qualifiés sur le courrier :
- `road1y_gap=12` : **QUALIFIÉ** (+16,4 k£ Porte A, +201 k£ Porte B). Plateau 6–24 mesuré : `gap=6` neutre (+2,4 k), `gap=24` inerte (−0,2 k) car la cadence de 2 ajouts/mois lie.
- `road1y_mail2=5` + `mail2_years=3` : **QUALIFIÉ** (+23,8 k£ Porte A, +1,6 k£ Porte B sans érosion). `mail2=2` réfuté (−10,0 k£).
- `road1y_mail_full` : **RÉFUTÉ** (−4,5 k à −8,2 k£ en Porte A, attente paralysante).
- `road1y_mail_min=15` : **RÉFUTÉ** (−45 k£/an en smoke, un fourgon à 1,4 k£ reste rentable, le supprimer détruit du cash net).
- `road1y_mail_net` : **RÉFUTÉ** (perte de 39 à 57 k£/an par éviction de trésorerie sur les bus).

### Verdict sur le gisement MAIL à 3 ans :
Il n'existe **aucun gisement MAIL intercités autonome exploitable à 3 ans** : le capital dépensé en infrastructure routière dédiée a un TRI trop faible face au bus PAX et détruit la croissance initiale de la compagnie.

Le seul angle mécanique encore ouvert (qui ne dépense aucune voirie neuve) est d'**augmenter le captage sur les gares existantes des lignes filles** par arrêts camion multiples répartis (`BuildSpreadPieceStations`), afin de faire passer l'attente médiane de 4 sacs vers les 17 sacs d'AAA et relever la note de 56 % à 66 %. Cette piste précise ([`road1y_spread_mail`](file:///home/deploy/.claude/jobs/e230de46/tmp/agy_spreadmail.md), 0..4 arrêts `ROADVEHTYPE_TRUCK` joints) est déjà en cours de développement dans [`wt-spreadmail`](file:///home/deploy/projects/wt-spreadmail). En dehors de ce levier de captage joint, le potentiel MAIL à 3 ans est **saturé**.

exit=0
