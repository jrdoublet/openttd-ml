# C87 — Bus de croissance urbaine déficitaires ; lignes qu'AAAHogEx exploite et pas OpexAI

2026-09-24. Deux demandes utilisateur : (1) comprendre quelles lignes AAAHogEx exploite, en
particulier les chaînes complètes avec les goods et les bateaux, et comment ; (2) arrêter les
lignes de bus déficitaires. Pour les bus de croissance urbaine, la construction est désormais
conditionnée à un ROI positif.

## 1. La partie de l'utilisateur

Sauvegarde : `OpenTTD/save/autosave/autosave1.sav` (24/09 08:12), carte 256², 18 villes,
38 industries, datée du **24 avril 1979**. AAAHogEx y a été fondée en 1978 (compagnie 2) :
6 véhicules (charbon ×2, minerai et passagers par rail, 1 bateau à passagers), **aucune ligne de
goods**. La phase où AAAHogEx dépasse OpexAI n'est donc pas dans ce fichier : il faut une
sauvegarde ultérieure pour analyser ses chaînes goods et bateaux sur cette carte.

Dans ce même fichier, OpexAI (compagnie 1) n'a livré **aucune unité de goods en neuf ans**
(`delivered_cargo[5] = 0` sur tous les trimestres). Recettes du trimestre : ~530 k£ pour OpexAI,
~60 k£ pour AAAHogEx. Côté bus : 11 lignes intra-ville, 19 bus, **+6,6 k£ au total** l'année
précédente, dont 4 lignes en perte (−100 à −850 £ chacune).

⚠️ Le décodeur partagé (`extract_line_telemetry`) regroupe les lignes par groupe `AIGroup` pour
la compagnie **1**, en supposant qu'il s'agit d'AAAHogEx. Dans une partie où OpexAI est la
compagnie 1, il fusionne toutes ses lignes en une seule. L'analyse ci-dessus fixe le propriétaire
AAAHogEx à 2 ; le harnais n'a pas été modifié.

## 2. Mesure : duel 5 graines × 6 ans, télémétrie de lignes

Campagne `diag_c86_town_roi_5x6_20260924` (préfixe `c86` d'avant la renumérotation en C87) (`run_c66_reference.py --line-telemetry`,
graines 42, 100, 999, 1234, 5678 ; Docker 9 CPU / 9 Go, image `f4b2b9b3…`, arbre de travail
**sale** : il contient aussi le travail C83 non commité d'une autre session, commun aux deux bras).
10/10 parties complètes. Profits de lignes relevés en décembre 1975 (donc exercice 1974), moyennes
par graine, bras de référence.

| AAAHogEx | lignes | véhicules | profit/an | part | profit/véhicule | distance médiane |
|---|---:|---:|---:|---:|---:|---:|
| air PASS+MAIL | 15,2 | 39,2 | 1 304 k£ | 61,5 % | 33,3 k£ | 245 |
| **air MAIL seul** | 4,8 | 10,0 | 267 k£ | 12,6 % | 26,7 k£ | 254 |
| rail COAL | 3,2 | 6,0 | 214 k£ | 10,1 % | 35,6 k£ | 109 |
| **rail GRAI+LVST (train mixte)** | 4,6 | 9,8 | 132 k£ | 6,2 % | 13,4 k£ | 136 |
| rail GOOD | 1,2 | 6,8 | 70 k£ | 3,3 % | 10,3 k£ | 268 |
| rail WOOD / MAIL / IORE / PASS / OIL | — | 21,8 | 155 k£ | 7,3 % | — | 38-186 |
| route PASS / MAIL (≈ 180 bus et camions) | 105 | 174 | **−21 k£** | −1,0 % | — | 11-12 |

OpexAI, même bras : air PASS+MAIL **97,6 %** (81 avions, 14,0 k£/avion), rail 0,6 train
(charbon), route ~25 véhicules. **Rail fret : ~570 k£/an chez AAAHogEx contre 15 k£ chez OpexAI.**
Le 20×10 C83 témoin (`diag_c83_slot_control_20x10_20260924.json`, fin 1979) confirme l'ordre de
grandeur : rail = 32 % du profit d'AAAHogEx (74,5 trains en moyenne), goods transportés sur
20/20 graines ; OpexAI = 0,5 train.

Lectures (5 graines, ordres de grandeur, pas un verdict) :

1. **L'avion reste l'écart principal** : même volume de lignes AIR PASS+MAIL, mais 33 k£ contre
   14 k£ par avion. AAAHogEx exploite en plus des **lignes aériennes de courrier seul** (≈ 13 % de
   son profit), qu'OpexAI ne génère pas.
2. **Fret ferroviaire longue distance** (109 à 268 tuiles), dont des **trains mixtes
   céréales + bétail** vers l'usine : le candidat OpexAI est mono-cargo.
3. **Chaînes goods** : sur 3 graines sur 5, une ligne goods d'AAAHogEx part à moins de 10 tuiles du
   terminus d'une de ses propres lignes d'intrants (céréales, bétail, acier). C'est un indice
   de chaîne alimentée, pas une preuve industrie par industrie.
4. **Bateaux** : négligeables sur les cartes du banc (0,2 ligne de pétrole par graine). Leur rôle
   dans la partie de l'utilisateur dépend de sa carte et reste à mesurer sur sa sauvegarde.
5. AAAHogEx garde lui-même ~180 bus et camions déficitaires : ce sont des rabatteurs de son
   réseau, pas des lignes jugées sur leur propre bilan.

## 3. Pourquoi OpexAI refuse les chaînes (lecture du code, non mesuré)

`OpexFreightCandidates` (`candidates.nut`) :

- le volume d'un candidat est `AIIndustry.GetLastMonthProduction(source, cargo)`. Une usine non
  approvisionnée produit 0 goods, donc le tronçon aval n'a jamais de valeur ;
- si l'une des deux industries est déjà desservie (`OpexOriginService` : extrémité d'une ligne rail
  à moins d'`ORIGIN_SEPARATION`), la paire est écartée (`pairsOriginServed`). Une usine qu'OpexAI
  alimenterait serait donc exclue comme source de goods ;
- un candidat porte un seul cargo : le train mixte céréales + bétail n'existe pas.

Une chaîne n'est donc pas « mal classée » : elle est structurellement invisible. Rouvrir ce point
demande un chantier dédié (valeur du tronçon aval conditionnée à l'alimentation, réemploi d'une gare
d'usine, trains mixtes), à mesurer contre AAAHogEx ; il n'est pas lancé ici.

## 4. C87 — garde-fou ROI des bus de croissance urbaine

Constat de code : `_tryTownGrowthCity` construisait avec `revenueAnnual = 0` explicite, et le
retrait des véhicules déficitaires (C52, `policy_vehicle_events`) est à 0 par défaut (jugé
destructeur en couperet aveugle). Rien n'arrêtait donc une ligne de bus en perte.

Réglage `town_growth_roi_gate` (défaut 0) :

- après planification, passagers captés par les deux arrêts réels
  (`AITile.GetCargoProduction` × production par maison de la ville, recouvrement retiré par
  `OpexRoadPaxUniqueMonthly`), puis `OpexRoadLineEconomics` : construction seulement si le profit
  annuel prédit est > 0. C'est le même modèle et le même seuil que le rejet
  `unprofitable_after_siting` des lignes route de profit ;
- au rapport annuel, une ligne `purpose = "town_growth"` en perte deux années pleines consécutives
  est fermée par `_scrapDeadLines` (même seuil que l'air, G10) ;
- la ville refusée ou fermée est mémorisée dans `_abandonedPairs` (clé `town_growth|<townId>`,
  sauvegardée, délai 365 j × nombre de refus, plafonné à 5 ans), sans passer par
  `_markPairAbandoned` pour ne pas relancer la réélection du portefeuille. La ville n'est pas
  replanifiée pendant ce délai.

Limite : en sauvegarde courte (`SAVE_FULL_STATE=0`), les lignes rechargées perdent `purpose` :
une ligne de croissance antérieure au chargement n'est alors plus candidate à la fermeture.

### Validation

- Smoke Docker 2 graines × 3 ans (`results/smoke_c86_town_roi_2x3_20260924.json`) : 4/4 OK.
- Duel apparié 5 × 6 ci-dessus. Bras C87 : lignes de bus **12,2 → 7,6** par graine, bus
  **22,8 → 14,0**, lignes de bus en perte **5,6 → 3,4**. Économie : `profit_year` **−16,3 k£/an**
  (médiane −33,2 k£, 1/4, p=0,375, IC95 [−214 ; +181] k£), valeur **−0,76 %** ;
  verdict `diagnostic_only`.

Lecture : le mécanisme agit (−40 % de bus, −40 % de lignes en perte), mais l'enjeu économique
direct est minime : toutes les lignes de bus d'OpexAI ensemble pèsent entre −1,4 et +3,5 k£/an par
partie, pour ~1,3 M£ de profit. L'écart de −16 k£ est dans le bruit du duel. Le gain d'opcodes et
de durée de tour (`town_growth` ≈ 28 % du tour, `16_bilan_volume.md` §7) n'a pas été mesuré.
**Décision utilisateur du 2026-09-24 : défaut passé à 1 sans 20×10**, au motif que les bus
déficitaires pèsent sur la note de performance. Ce n'est pas une adoption fondée sur un gain de
profit mesuré ; le bras `town_growth_roi_gate=0` sert désormais de témoin historique.

## 5. Qualification 20×10 sur le défaut courant — 2026-09-25

Campagne `results/c87_town_growth_roi_gate_vs_current_default_20x10_20260925.json`,
20 graines canoniques × 10 ans, 10 workers / 10 CPU, télémétrie de lignes activée.
Contraste causal unique :

- référence : `OpexAI[town_growth_roi_gate=0]` ;
- variante : `OpexAI[town_growth_roi_gate=1]`.

Les **20/20 paires sont complètes**. Variante − référence :

- `profit_year` moyen **−8,5 k£/an** ;
- médiane **+5,3 k£/an** ;
- **10 victoires / 10 défaites**, test des signes p=**1,0** ;
- IC95 normal **[−132,1 ; +115,1] k£/an** ;
- valeur d'entreprise : ratio des moyennes **+0,86 %** ;
- verdict brut du harnais : `fail_primary` parce que le seuil de gain utile reste fixé à
  **+50 k£/an**.

Lecture : le 20×10 ne met en évidence **ni gain ni perte économique** du garde-fou. La garde de
valeur est tenue et l'intervalle de confiance est centré autour de zéro. Le 5×6 avait déjà montré
que le mécanisme réduit fortement le nombre de bus et de lignes déficitaires ; le 20×10 confirme
qu'on peut conserver ce comportement sans coût économique mesurable. Le réglage reste donc
**à 1 par défaut**, conformément à la décision utilisateur du 2026-09-24 motivée par la note de
performance plutôt que par un gain direct de profit.
