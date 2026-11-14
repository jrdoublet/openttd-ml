# STAGNATION-1975 — diagnostic chiffré AIR/ROUTE et levier `air_late_slot_town`

Diagnostic hors rail, archives 10 ans déjà présentes. Aucun banc Docker.
Levier opt-in défaut 0. MULTI-1 reste suspendu ; LATE-GAME-1 reste conditionné à
la parité 48 cellules ; C83 6→24, V126, V134 et V240 ne sont pas rejoués.

## 1. Question et sources

À 10 ans le multimodal élu ESTIM-31 est à **66,56 %** d'AAAHogEx
(4 255 528 £/an contre 6 393 740 £/an). OpexAI a **14,74 M£** de caisse sans
prêt en 1979 pendant qu'AAAHogEx continue d'ajouter des aéroports et des
trains. Ce document répond à trois questions, hors rail :

- **(a)** quel prédicat arrête les ouvertures AIR/ROUTE après ~1975 malgré la caisse ;
- **(b)** quel gisement (k£/an) d'ouvrir des lignes AIR/ROUTE sur les villes
  restantes, estimé avec les lignes tardives d'AAA et les AIR tardives d'Opex ;
- **(c)** un levier local jamais testé, spécifié et, s'il est sûr, codé à défaut 0.

Sources figées :

| Source | Usage |
|---|---|
| `docs/estim31_top3_decade_trajectory_20261030.json` campagne `estim31ten_estim31v161_mix_a200_r075_w15_slope_20x10_20261030` bras **variant** | Trajectoire 20 graines, stocks, caisse, aéroports |
| `docs/estim31_ten_v161_accounts_1979_20261030.json` même campagne | PLYR 1979 YTD net |
| `docs/post1974_entonnoir_20261030.md` + `docs/post1974_entonnoir_seed42_1x10_20261030.json` | Entonnoir graine 42, C78, C63 lignes |
| `docs/estim31_priorites_20x10_20261030.md` | Agrégats 1974→1979 |
| `docs/agy_specs/OPCODES_AILIST_mesure.md` | `AIR_BUILD` 40×5 multimodal 1970–1974 |
| `docs/multi1_retard_1975_1979_resultats_20261026.md` | C63 5×11 code **antérieur** (1,2 AIR / 0,2 ROUTE) |
| `docs/multi1_rejets_1974_20261026.md` | `ROAD_BUILD` 1970–1974, 5 graines |
| `docs/methode.md` l.169–170 | 46–52 villes sur 256², `number_towns=3` |
| `docs/22_c78_lignes_vs_aaa.md` §10 | C83.1 : `OpexAirTownServed` ≠ slot physique |

Le C63 26/10 n'est **pas** le défaut ESTIM-31 ; il sert seulement de
contrôle croisé d'ordre de grandeur pour les ouvertures tardives.

## 2. Trajectoire 1973–1979 (élu ESTIM-31, 20 graines)

Calculs : différences de moyennes du JSON trajectoire, bras variant.
`airport_towns` est identique Opex/AAA chaque année : c'est le nombre de
villes de la **carte** qui portent au moins un aéroport, pas un stock
par compagnie.

| Année | Profit Opex | Profit AAA | Ratio | Caisse Opex | Aéroports Opex/AAA | Avions Opex/AAA | Trains Opex/AAA |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1973 | 2 757 099 | 2 420 683 | 113,90 % | 0,530 M£ | 32,45 / 31,40 | 67,65 / 36,90 | 23,05 / 18,30 |
| 1974 | 2 912 643 | 2 821 334 | 103,24 % | 1,039 M£ | 33,25 / 33,95 | 78,45 / 40,05 | 24,50 / 26,25 |
| 1975 | 3 135 782 | 3 528 207 | 88,88 % | 2,128 M£ | 33,70 / 34,55 | 81,70 / 40,55 | 25,90 / 31,50 |
| 1976 | 3 414 755 | 4 226 156 | 80,80 % | 4,141 M£ | 33,80 / 35,35 | 84,60 / 42,30 | 27,20 / 39,75 |
| 1977 | 3 695 688 | 5 020 181 | 73,62 % | 7,256 M£ | 34,15 / 35,70 | 84,65 / 44,90 | 28,35 / 44,35 |
| 1978 | 3 962 027 | 5 622 585 | 70,47 % | 10,781 M£ | 34,20 / 35,95 | 84,80 / 45,70 | 29,10 / 51,60 |
| 1979 | 4 255 528 | 6 393 740 | 66,56 % | **14,743 M£** | 34,30 / 36,20 | 84,25 / 48,00 | 29,55 / 56,25 |

Delta annuel d'aéroports Opex 1974→1979 : +0,45 / +0,10 / +0,35 / +0,05 / +0,10
= **+1,05**. AAA : +0,60 / +0,80 / +0,35 / +0,25 / +0,25 = **+2,25**.
Écart d'expansion aéroportuaire : **1,20 aéroport/monde**.

Aéroports « en trop » vs villes équipées (`airport_count − airport_towns`) :

| Année | Opex | AAA | Villes carte |
|---|---:|---:|---:|
| 1974 | 0,45 | 1,15 | 32,80 |
| 1979 | 0,55 | 2,45 | 33,75 |

AAA pose **~1,90 second aéroport** de plus qu'Opex en 1979. Opex stagne à
un demi second aéroport dès 1974.

Avions par aéroport 1979 : Opex 84,25 / 34,30 = **2,46** ; AAA 48,00 / 36,20
= **1,33**. Graine 42 C63 1978 : 71 avions / 38 lignes = **1,87 avion/ligne**.

Ouvertures `AIR_BUILD` cumulées, 40 parties multimodales 40×5
(`docs/agy_specs/OPCODES_AILIST_mesure.md`) : 340 (1970), 825 (1971),
246 (1972), 54 (1973), 33 (1974) soit **8,50 / 20,63 / 6,15 / 1,35 / 0,83**
par partie. La chute est antérieure à 1975 ; 1975–1979 n'ajoute plus
qu'un filet.

C63 5×11 (code 26/10, 5 mondes) 1975–1979 cumulés par monde :
**1,2 AIR, 4,2 RAIL, 0,2 ROUTE** ; `unaffordable = 0` ; caisse 16,27 M£.
Graine 42 ESTIM-31 : 3 `AIR_BUILD` (1976, 1977, 1979) pour 2 OD.

ROUTE 1979 PLYR (élu) : recettes 538 £ Opex vs 9 244 £ AAA ; running
93 £ vs 73 541 £. AAA **perd** 9 244 − 73 541 = **−64 297 £/an** sur la
route. Opex n'a plus de réseau routier multimodal.

## 3. (a) Pourquoi plus d'ouvertures après ~1975 malgré la caisse

Ce n'est pas la trésorerie. Preuves :

- ESTIM-31 1979 : caisse 14 742 507 £, prêt 0
  (`estim31_top3_decade_trajectory_20261030.json` 1979-12-01 variant.opex).
- Graine 42, 1978 : 92/92 passes `C78_SLOT phase=projects_pass` ont
  `air_candidates=0` avec cash disponible 5 808 112 … 7 957 934 £
  (`post1974_entonnoir_seed42_1x10_20261030.json` année 1978
  `c78_limited_trace`, `post1974_entonnoir_20261030.md` §7.2).
- Même graine 1974 : 62/62 passes sans candidat AIR, cash max 919 971 £
  (la caisse n'est pas encore le 14 M£, le vivier AIR est **déjà vide**).
- C63 historique : 5,8 jours `unaffordable` sur cinq ans, 0 en 1976–1979.

### 3.1 Prédicat AIR n°1 — `origin_served` 15 tuiles

`OpexAirTownServed` (`ai/OpexAI/air_towns.nut:31-40`) : une ville est
servie si `DistanceManhattan(town.tile, line.originA/B) < 15` pour une
ligne AIR d'Opex. Ce n'est **pas** « cette ville a un aéroport Opex ».

Consommateurs qui sautent alors le site :

- `air_planning.nut:565-571` `OpexAirPlansFindSites` :
  `skipServed = isServed && !c83OwnSecondSlot` → rejet `origin_served`.
- `air_planning.nut:1234-1237` `OpexAirPlansDiscoverHubs` : même skip.
- `po01c_generators.nut:1938-1944` et `:2157-2160` : copies du générateur
  reprenable.
- Revalidation chantier `task_air.nut:39-45` `OpexAirBatchPlanStillLive`
  et index `OpexAirTownServedIndexed` `:65-79` (même rayon 15).

Le watcher C83.1 (`task_projects.nut:663-675`) utilise **déjà**
`AITile.GetClosestTown(GetLocation(aéroport))` pour le slot physique.
L'audit du 24/09 (`docs/22_c78_lignes_vs_aaa.md:280-282`) enregistre
l'écart : `OpexAirTownServed` masque des villes sans aéroport propre
dès qu'une origine commerciale voisine est à moins de 15 tuiles.

Exception actuelle : second créneau C83 seulement pour les
`AIR_C83_TARGET_TOWNS=6` plus grandes (`air_towns.nut:159-177`,
`air_planning.nut:412-420`) **et** `GetAllowedNoise == 1`
(`OpexAirC83SecondSlotOpen`, `air_towns.nut:117-123`).

### 3.2 Prédicats AIR n°2 et n°3 — distance et bande

- Hubsite : `distance < 20` → `distance_short` (`air_planning.nut:1418-1422`).
- Newpair : `minDist` 30 ou 32 selon `plane.speed` (`air_planning.nut:2032, 828`).
- `OpexAirPairInBand` / `bounds.airMin` (bascule rail/avion,
  `candidates.nut:521`, `air_planning.nut:69, 833, 1427`) : une ville
  restante à 20–airMin tuiles d'un hub est refusée `pax_band`. Relâcher
  `airMin` est le levier MULTI-1 (`OpexMulti1PrepareAirBand`,
  `projects_selection.nut:997-1009`) **suspendu** le 26/10.

### 3.3 Prédicat AIR n°4 — pas de site

`V93_AIRPORT_MIN_POP = 100` (`globals_pre.nut:517`). En dessous :
`town_pop_v93`. Sinon `OpexAirFindSite` → `no_site` / `no_site_slot`
(`air_planning.nut:594-604`). Ce n'est pas un manque de caisse.

### 3.4 ROUTE

`OpexRoadPairServed` saute les paires déjà ouvertes
(`task_road.nut:72-73`, `bus_districts_overrides.nut:768-769`).
En 1973 multimodal, le vivier ROAD compte `origin_served=1 365` et
`town_rejected=767` (`docs/analyse_estim_sites_40x5_20261027.md`).
`VIVIER_GEN mode=road` : `kept` 41 / 16 / 5 / **0** en 1971–1974
(`docs/multi1_rejets_1974_20261026.md`). 12 `ROAD_BUILD` sur 5 mondes,
profit prédit agrégé **65 702 £** soit 5 475 £/ligne. 1975–1979 :
0,2 ligne/monde (C63 26/10).

Les `road1y_*` sont forcés à 0 hors route seule
(`settings.nut` `OpexLoadBusDistrictSettings`). En multimodal le
vivier route meurt dès 1974 ; ce n'est pas un gisement tardif
rentable (voir §4).

### 3.5 Ce qui n'est pas la cause

- Flotte V161 : 5 `FLEET_PROJECT grow` en 1974 et 5 en 1975, **0** de
  1976 à 1979 sur la graine 42. Les 84 avions sont un stock mûr, pas
  un siphon de caisse tardif.
- V249 statues (défaut 2) : dépenses PLYR `other_including_town_actions`
  77 715 £ Opex vs 139 546 £ AAA en 1979. Ce n'est pas 14 M£.
- `air_coverage_stop` défaut 0 : les scans continuent et rendent 0
  candidat. Le STOP opcodes n'explique pas le vivier vide.

## 4. (b) Gisement chiffré des villes restantes

Carte 256², `number_towns=3` : **46–52 villes** (`docs/methode.md:169-170`).
Villes avec aéroport (toute compagnie) en 1979 : **33,75**. Reste
**~12–18 villes sans aéroport**. Pool AIR spatial 256/32 = 64 cellules
(`OpexAirTownPoolLimit`, `air_towns.nut:18-28`) : toutes les villes
entrent dans le scan. Le refus est le prédicat §3, pas un plafond de pool.

### 4.1 AIR — proxy lignes tardives

AAA ajoute 2,25 aéroports de 1974 à 1979, Opex 1,05, delta **1,20**.

Lignes AIR tardives **Opex** graine 42 (C63 / `PROJECT_CHOSEN`) :

| Date | OD | Profit prédit | Coût devis | Réalisé âge 1–2 |
|---|---|---:|---:|---|
| 1976-11-14 | 32963→40461 | **41 420** | 38 964 | 1976 âge 1 : **−389** ; 1977 âge 2 : **−45** ; 1978 âge 2 : **0** |
| 1977-09-04 | 40461→21394 | **24 411** | 38 964 | 1977 âge 1 : **−955** |
| 1979-10-27 | 32963→40461 (reprise) | 48 854 | 38 964 | C63 1979 non vidangé |

Les AIR ouvertes après 1975 sur cette graine sont **faibles ou négatives**
les deux premières années. Le profit mûr de **toutes** les lignes AIR
(C63 26/10, 43,4 lignes, 3,561 M£) = 82 051 £/ligne décrit le réseau
ancien, pas une ville restante.

Gisement AIR des **1,20 aéroport AAA de plus** :

- Plancher (prédit 1977) : 1,20 × 24 411 = **29 k£/an**.
- Central (prédit 1976) : 1,20 × 41 420 = **50 k£/an**.
- Plafond (tous les +2,25 AAA) : 2,25 × 41 420 = **93 k£/an**.

Ces montants sont des **prédictions de construction**, pas le réalisé
(§ tableau : réalisé ~0 à deux ans). Ils restent **sous le seuil V102
4 %** de 4 255 528 £ (170 k£). Le retard de recettes AIR 1979
(3,578 M£ Opex vs 4,436 M£ AAA = **857 k£**,
`docs/estim31_priorites_20x10_20261030.md` §3) est un écart de
**rendement par avion** (42,5 k£ vs 92,4 k£ descriptif), pas le
gisement des villes restantes.

### 4.2 ROUTE — proxy AAA tardif

Recettes route 1979 : AAA 9 244 − Opex 538 = **+8,7 k£** de chiffre.
Running AAA 73 541 £ → **marge route AAA = −64,3 k£/an**.
12 `ROAD_BUILD` 1971–1973, 5 475 £ prédits/ligne, puis 0 en 1974.
Copier les lignes route tardives d'AAA **détruit** du profit. Gisement
ROUTE des villes restantes : **≤ 0 k£/an** (borne haute descriptive
+8,7 k£ de recettes, marge négative).

### 4.3 Synthèse du gisement

| Mode | Proxy | k£/an | Lecture |
|---|---|---:|---|
| AIR villes restantes | 1,20 aéroport × prédit tardif 24–41 k | **29–50** (plafond 93) | Sous le seuil 4 % ; réalisé tardif ~0 à 2 ans |
| ROUTE villes restantes | P&L AAA 1979 | **négatif** | Ne pas ouvrir de feeders multimodaux |
| Écart total 1979 | 4,256 vs 6,394 M£ | **2 138** | Dont recettes RAIL 1 168 + AIR 857 |

Le 10 ans se joue sur le **rail** (interdit ici) et le **rendement AIR
des lignes déjà ouvertes** (FLOTTE-EQUILIBRE, hors périmètre de ce
levier). Les villes restantes AIR/ROUTE ne comblent pas l'écart.

## 5. (c) Levier `air_late_slot_town` — jamais testé

### 5.1 Ce qui est fermé (ne pas rejouer)

| Piste | Verdict | Fichier |
|---|---|---|
| MULTI-1 relance (airMin 60, feeders 20–50, COMMUTER) | Suspendu 26/10 | `docs/taches.md` MULTI-1 ; `MULTI1_CONDITIONS_RELANCE.md` |
| LATE-GAME-1 statues/industries | Bloqué tant que parité 48 cellules | `LATE_GAME_1.md` ; `docs/taches.md` |
| V126 `v126_air_served_town_reuse` | Retiré sur demande utilisateur | `docs/journaux/journal_2026-10-11.md` |
| C83 `AIR_C83_TARGET_TOWNS` 6→24 | 20×10 +77 k£, 13/7, p=0,26, valeur −1,54 % ; défaut resté 6 | `docs/22_c78_lignes_vs_aaa.md:310-323` |
| V134 second aéroport newpair hub saturé | Porte A −28,6 k£ | `docs/inventaire_parametres_20261022.md` |
| V240 croissance urbaine | NO-GO | `docs/taches.md` LATE-GAME-1 |
| `road1y_town_reuse` | Porte A −38,3 k£ | `docs/taches.md` 04/11 |
| `air_coverage_stop` | Opcode, déjà spécifié, défaut 0 | `AIR_COVERAGE_STOP.md` |

Grep `air_late_slot`, `late_slot_town`, `AIR_LATE_SLOT` : **aucun**
réglage, test ni journal. Le mismatch C83.1 « 15 tuiles vs slot
ClosestTown » est documenté, **jamais exposé en génération**.

### 5.2 Mécanisme

Après 1975, si caisse ≥ 2 000 000 £ et prêt = 0, une ville est « servie »
pour la **génération et la revalidation** AIR seulement si Opex y
possède un aéroport dont `GetClosestTown(location) == town.id`
(`OpexAirOwnSlotTownCounts`, déjà livré `air_towns.nut:135-146`).
Le rayon commercial 15 tuiles reste le défaut (mode 0).

Effet : une ville **sans aéroport propre**, même à 8–14 tuiles d'une
origine voisine, redevient un site `newpair`/`hubsite`. Ce n'est pas
un second créneau C83 (top 6, `GetAllowedNoise==1`). Ce n'est pas
V126 (réadmission sans garde d'année ni de caisse). Ce n'est pas
MULTI-1 (pas de baisse d'`airMin`, pas de feeder route).

### 5.3 Réglage

- Nom : `air_late_slot_town`
- `info.nut` : min 0, max 2, **easy/medium/hard/custom = 0**
- 0 = OFF, chemin 15 tuiles inchangé
- 1 = SHADOW : calcule le slot, journalise `AIR_LATE_SLOT` sous
  `DECISION_LOG`, **conserve** le skip 15 tuiles
- 2 = ON : `OpexAirTownServed` et `OpexAirTownServedIndexed` utilisent
  le slot physique quand le prédicat tardif est vrai
- Globale : `AIR_LATE_SLOT_TOWN <- 0;` dans `globals_pre.nut`
- Chargeur : `OpexLoadSettings` dans `settings.nut` (même unique
  lecture que `late_game_policy` / `multi1_relance`). Pas de lecture
  dans `OpexLoadBusDistrictSettings` (réglage AIR, `MODE_*` encore
  non posés à cet appel).

```squirrel
function OpexAirLateSlotTownActive()
{
  if (AIR_LATE_SLOT_TOWN == 0) return false;
  if (AIDate.GetYear(AIDate.GetCurrentDate()) < 1975) return false;
  if (AICompany.GetLoanAmount() > 0) return false;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 2000000) return false;
  return true;
}
```

Cache de tick pour `GetAllowed`/comptage d'aéroports : un passage de
scan ne paie `OpexAirOwnSlotTownCounts` qu'une fois. À 0, le cache
n'est jamais rempli (`AIR_LATE_SLOT_TOWN == 0` court-circuite).

### 5.4 Sites de code

| Fichier | Rôle |
|---|---|
| `air_towns.nut` | `OpexAirLateSlotTownActive`, cache slot, branche en tête de `OpexAirTownServed` si mode ≥ 2 et actif |
| `task_air.nut` | Même garde dans `OpexAirTownServedIndexed` (revalidation V156) |
| `air_planning.nut` | Mode 1 : log `AIR_LATE_SLOT` prox vs slot dans FindSites / DiscoverHubs, sans changer `isServed` |
| `po01c_generators.nut` | Identique mode 1 (le mode 2 passe par `OpexAirTownServed`) |
| `persist.nut` | **Aucun champ neuf** : le prédicat se recalcule (date, caisse, prêt, liste d'aéroports) |
| `info.nut` / `globals_pre.nut` / `settings.nut` | Déclaration / globale / chargeur |

`OpexDecide("AIR_LATE_SLOT", "town=… pop=… prox=… slot=… year=… cash=…")`
uniquement si `DECISION_LOG`.

### 5.5 Save/Load

Pas d'état comportemental sérialisé. Après Load, `OpexLoadSettings`
relit le réglage ; le cache de tick est vide. Une sauvegarde ancienne
sans le champ de réglage : `GetSetting` rend 0.

### 5.6 Portes (pré-enregistrées, non lancées ici)

Le mécanisme est **inerte à 3 ans** (garde année 1975). Protocole V102
§4 pour levier tardif :

- Contrats hôte + smoke 1×1 (compilation, OFF identique).
- Porte A `gain_short` **40×10** (`profile=custom`) : Wilcoxon p < 0,05,
  IC95 bootstrap bas > 0, delta moyen ≥ 4 % du profit de référence 1979,
  garde de valeur −5 %.
- Porte B `non_erosion` 20×10 après A `pass`.
- Exposition attendue : `AIR_LATE_SLOT` avec `prox=1 slot=0` puis
  `AIR_BUILD` hubsite/newpair sur cette ville en 1975–1979.
- Seuil économique **non promis** : gisement 29–50 k£ < 170 k£ (4 %).
  Un `fail_primary` sous 4 % reste un résultat ; le levier reste à 0.

## 6. Pièges

1. **V126** : ne pas réadmettre une ville qui **a** déjà un aéroport Opex.
   Le mode 2 ne change que l'identité « servie ».
2. **C83 6→24** : ne pas élargir `AIR_C83_TARGET_TOWNS`. Les seconds
   créneaux des villes 7–24 ont déjà perdu la valeur.
3. **MULTI-1** : ne pas baisser `airMin`, ne pas ouvrir de feeder route.
4. **Cannibalisation** : un aéroport à 10 tuiles d'un hub existant partage
   le captage. C121 reste le devis. Le réalisé tardif graine 42 (~0 à
   2 ans) impose la porte 40×10, pas un changement de défaut.
5. **Opcodes** : `OpexAirOwnSlotTownCounts` seulement si mode ≥ 1 **et**
   prédicat tardif vrai ; cache par tick.
6. **`OpexAirTownServedIndexed`** : si on ne le branche pas, un plan
   généré en mode 2 meurt en `batch_plan_dead` (`task_air.nut:43-44`).

## 7. Tests

`sweeps/test_air_late_slot_town.py` :

- AddSetting 0/0/0/0, min 0 max 2.
- Globale 0, chargeur unique `OpexLoadSettings`.
- Mode 0 : le corps 15 tuiles de `OpexAirTownServed` est intact
  (présence du `< 15`, garde `AIR_LATE_SLOT_TOWN >= 2` avant).
- Mode 2 : `OpexAirTownServed` et `OpexAirTownServedIndexed` lisent le slot.
- `year < 1975`, `loan > 0`, `cash < 2000000` → inactif.
- Pas de `.find(`, pas de `function(` anonyme, pas de rail.
- `n75_mc_legacy` retire le bloc `air_late_slot_town` (compte historique 68).
- Témoins `test_v233_merge_guards` OVERNIGHT_* et SHA merge rail alignés.

## 8. Difficulté et effet attendu

- Difficulté : **2 / 5** (identité de slot déjà calculée, 2 fonctions
  d'entrée, pas de persistance).
- Effet attendu : **+29 à +50 k£/an** à 10 ans si les 1,20 aéroport AAA
  sont des villes `prox=1 slot=0` effectivement constructibles. Réalisé
  tardif observé proche de 0 → risque de `fail_primary`. Défaut **0**.
