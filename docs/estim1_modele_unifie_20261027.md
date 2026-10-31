# ESTIM-1 — modèle d'estimation unifié : plan (27 octobre 2026)

> **Mise à jour du statut au 30/10/2026 : ce document décrit la conception
> expérimentale du 27/10, non le défaut courant.** Les bits intégrés
> `estim_unifie=31` ont été qualifiés **en combinaison AIR/RAIL**, avec
> `eb14_progressive=3` et `probes=2`, puis le gagnant V161 AIR2,00/RAIL0,75
> a été installé et poussé sur `origin/master` (`2429d175`). Les bras
> `estim_unifie=0` ci-dessous restent des **références explicites historiques**.
> Voir [décision](estim31_phase_combinatoire_20261030.md) et
> [reste à faire](taches.md).

**Statut au 27/10 : lots 1–4 implémentés dans l'arbre de travail sous les bits
`1/2/4/8`, `estim_unifie` conserve son défaut `0` ; qualification expérimentale en
cours (§12–16). Lot 5 exclu. Aucun commit ni push.**
Décision utilisateur du 27/10 : les biais sont déjà mesurés ; ESTIM-1 doit **changer
les estimations** pour un modèle cohérent entre modes, nouvelles lignes, renforts et
remplacements, avec moins de nombres magiques et des gardes simplifiées. Pas de nouvelle
campagne de mesure préalable ; le travail n'est pas délégué à CoS. Base de lecture :
[topo des estimations](topo_estimations_20261027.md) (corrigé le 27/10).

## 1. Ce que les mesures disent déjà

Campagnes 40 × 10 SOLO et DUEL du 21/10 ([quartiles](calibration_cout_profit_quartiles_20261021.md),
[composantes RAIL](diag_rail_profit_components_20261021.md)), sauf mention.

| Grandeur | Mesure DUEL | Lecture pour le modèle |
|---|---|---|
| Profit AIR réel/prédit | **0,25 / 0,26 / 0,24 / 0,23** par quartile de distance ; SOLO **0,31** | Biais de **niveau**, stable, présent sans concurrent : surtout le modèle physique C121, la concurrence n'ajoute qu'environ un cinquième. |
| Première ligne AIR (graine 42, flotte ≈ constante) | 0,73 (année partielle) → **0,44** → 0,36 | Dérive dans le temps à flotte égale : la prévision statique ignore la dégradation (concurrence, nos hubs ultérieurs). |
| Profit RAIL réel/prédit | **0,99** (biais +679 £/an, MAE 11,5 k) ; frais courants exacts (MAE 199 £) | En moyenne juste ; **pente** : Q1 0,76 → Q4 1,16 ; quartile ROI prédit Q4 87,6 % → 59,2 % réalisé (régression vers la moyenne). |
| Coût RAIL réel/devis | **1,473** ; Q1–Q4 1,22 / 1,43 / 1,56 / 1,69 | Sous-estimation croissante avec la distance. |
| Dénominateur `K_dec` | domine **99 %** des candidats RAIL, 80 % flotte, 13 % AIR ([V216](est_v216_bilan_20261016.md)) | Le coût RAIL n'agit presque jamais sur le rang ; il agit sur la garde de caisse. Entre RAIL, l'ordre est celui du profit calibré. |
| ROUTE | profit 0,868 ; PASS 0,05–0,38 ; fret 1,1–2,2 ; coût 1,168 | Bus surestimés (générés seulement par C42), fret camion sous-estimé. |
| RAIL GOOD | MAE 61,7 k£ sur 37 lignes, ratios 0,25–0,98 | Cargo le plus mal prédit. |

**Ce qui reste inconnu** : la décomposition causale de l'écart AIR (volume, note, temps,
part captée). Elle n'est pas nécessaire pour recaler le niveau sur la recette ; elle l'est
pour corriger le modèle physique lui-même, ce qui n'est pas l'objet du lot 1.

**Ce que l'historique impose** : une estimation plus exacte n'a pas toujours mieux joué
(RAIL-CAL-1 non qualifié ; financement RAIL 170 → 100 % meilleur ; table V306 `NO-GO`).
Les portes A/B restent donc l'arbitre ; elles remplacent la phase de mesure, pas l'inverse.

**Biais structurels identifiés dans le code** (vérifiés le 27/10) :

1. C70 corrige le **profit** (`projects_models.nut:149-190`) : un facteur sur `P` ne rend
   jamais négatif un projet à faible marge, cas que V306 n'a pas pu traiter.
2. C70 part d'une pseudo-ligne à 1 et n'apprend qu'à l'âge ≥ 2 : jusqu'en 1972–73, AIR est
   classé brut (environ ×3–4) face au RAIL (environ ×1), dans la fenêtre de la porte A.
3. C70 normalise le réalisé par `trains0/vehCount` (`task_report.nut:84`) : hypothèse
   linéaire en flotte, fausse pour AIR (94 % des lignes changent de flotte).
4. Ouverture AIR classée sur la flotte optimale `decisionEconomics`, chantier à un avion
   (`air_economics_c121.nut:1967-1972`) ; C70 apprend sur la flotte construite et s'applique
   à la flotte optimale.
5. Quatre sources de marge pour un renfort AIR (`projects_builders.nut:143-273`) : marginal
   C121 × facteur, marge observée, `lastProfit/vehCount`, a priori V161 13 000 / 2 600 £.
6. Modèle AIR historique `OpexAirEconomics`/`OpexAirTripModel` encore actif pour améliorations,
   remplacements et plafond de cadence (`air_fleet.nut:8-67`, `air_trip.nut:37,155`).
7. Aucun mode ne réduit la demande pour une gare **rivale** : le partage AIR
   (`air_coverage.nut:444-511`) ne voit que les gares d'Opex.
8. Conventions comptables et horizons hétérogènes : profit net d'amortissement (lignes),
   cash-flow + revente (V257), recette × 5 ans (V249), gain × années restantes (V259),
   seuils absolus 1 M£ (V284, V269).
9. Gardes de caisse par mode : marges AIR 30 000 / 12 000 / 2 000 £ (plusieurs copies),
   flotte +1 000, WATER +50 000 et `maxShipPrice`, ROUTE 121 %, RAIL 100 %.
10. Sous V276 (≥1024²), troncature à 20 candidats par unité sur `ratio`
    (profit/opcodes + 15 × ROI × bonus de rotation), clé différente du `fundScore`.

## 2. Principes du modèle unifié

- **M1 — un contrat de valeur pour toute dépense.** Chaque projet fournit `ΔC` (sortie de caisse
  attendue), `ΔR`, `ΔE`, `ΔA` à maturité ; `ΔP = ΔR − ΔE − ΔA` ;
  `score = 1000 × ΔP / max(ΔC_fin, K_dec)`. Lignes neuves, renforts, remplacements, croissance
  RAIL, statues et ponts deviennent des projets du même portefeuille.
- **M2 — une convention comptable.** `ΔA = (prix − valeur de revente) / durée utile restante`
  pour tout véhicule ; amortissement d'infrastructure nul partout (déjà forcé). Les horizons
  propres (5 ans V249, années restantes V259, durée V257) disparaissent au profit de M1.
- **M3 — une calibration.** Facteur de réalisation **sur la recette** `k_R[mode]`, appliqué
  avant de retirer `E` et `A` ; a priori hors ligne issu du corpus du 21/10, mis à jour en
  partie avec un poids fixe d'a priori (au lieu de la pseudo-ligne à 1). Facteur de coût
  `k_C[mode](distance)` (RAIL `1,063 + 0,003 × d` déjà estimé ; ROUTE 1,17 ; AIR sur devis
  `AITestMode`). Recette réalisée reconstruite `R = ΣGetProfitLastYear + ΣGetRunningCost`,
  **sans** retrait d'amortissement, sur les seules années où la flotte égale la flotte prédite.
- **M4 — mêmes primitives physiques.** Temps de trajet, note (ramassage, vitesse, âge, statue),
  part captée et capacité partagées par les modes ; un renfort ou un remplacement est le même
  modèle évalué à `n+1` ou avec un autre moteur, et non une formule à part.
- **M5 — une garde de caisse.** `disponible ≥ k_C × C + réserve` pour tout projet, au choix comme
  au chantier.
- **M6 — taille initiale par le critère du portefeuille**, bornée par la physique (quais, piste,
  arrêts), et non par des plafonds 2 trains / 1–2 avions / 2 camions.

## 3. Lots

| Lot | Contenu | Remplace / supprime | Fichiers principaux |
|---|---|---|---|
| **1 — calibration unique** | `k_R` et `k_C` par mode, a priori + mise à jour ; application sur la recette, puis `P = k_R × R − E − A` | C70 sur profit et pseudo-ligne, réalisation C121 hubs 75/25, réalisation directe P0, garde anti double correction, a priori V161 | `projects_models.nut`, `task_report.nut`, `projects_selection.nut`, `air_economics_c121.nut` |
| **2 — garde unique** | M5 au choix et au chantier | marges AIR 30k/12k/2k et copies, +1 000 flotte, +50 000 et `maxShipPrice` WATER, 121 % ROUTE, gardes propres des chantiers | `projects_finance.nut`, `projects_builders.nut`, `task_air/road/rail/water.nut`, `air_engine_choice.nut`, `air_route_economics.nut` |
| **3 — renforts et remplacements dans le modèle** | marge d'un avion/train/camion de plus = même modèle à `n+1` ; remplacement = même modèle, autre moteur ; V249, V252, V257, V259, V284 publient des projets M1 | quatre sources de marge flotte, `OpexAirEconomics`/`OpexAirTripModel`, horizons 5 ans, seuils 1 M£ | `projects_builders.nut`, `air_fleet.nut`, `air_trip.nut`, `task_v249/v252/v257/v259/v284.nut` |
| **4 — primitives physiques** | dimensionnement RAIL/ROUTE sur la note calculée (et non `STATION_RATING_PCT=50`), une convention de jours par mois, part rivale à la source par `GetLastMonthTransportedPercentage` | `STATION_RATING_PCT`, 30 / 30,4 jours, plafonds `MAX_RAIL_TRAINS` et 2 véhicules route, seuil 1,25 d'`air_engine_choice` | `economy.nut`, `air_economics_c121.nut`, `candidates.nut` |
| **5 — clé de troncature V276** | même clé que le portefeuille | `ratio` composite dans `candidates_v276.nut:402` | **sur décision utilisateur seulement** : `simple_roi` a été rejeté définitivement le 11/10 |

Conservés : constantes de mécanique (0,036, paliers de note, 256/255, acceptation 8),
`K_dec`/`K_pass` (C69), classes C77/C83 qualifiées. Une version continue des classes C83
reste une hypothèse distincte.

## 4. Validation

- Un réglage `estim_unifie` (défaut 0) à bits, un bit par lot ; mêmes sources dans les deux bras.
- Contrats Docker : même structure `ΔR/ΔE/ΔA/ΔC` pour ligne neuve, renfort et remplacement ;
  mise à jour de `k_R` ; garde M5 ; Save/Load des facteurs (`docs/19_rechargement_partie.md`).
- Smoke 1 × 1 par lot, puis **porte A 40 × 3** `gain_short` et **porte B 20 × 10** `non_erosion`,
  garde de valeur 5 %, **à la fois sur chaque lot et sur la variante intégrée** (tous les bits
  livrés, `estim_unifie` = somme des bits). Consigne utilisateur du 27/10 : un lot isolé peut
  être négatif et l'ensemble cohérent positif ; l'échec d'un lot seul n'écarte donc pas ce lot
  tant que la variante intégrée n'est pas jugée. Chaque lot ajouté est rejoué en intégré.
  L'exposition est certaine : toutes les estimations changent ; journaliser quand même les
  changements de premier rang.
- En cas d'échec de la porte A intégrée : ablation par bit (retirer un lot à la fois), lot 1
  d'abord (il porte le plus gros biais et agit dès 1970).
- Risque nommé : abaisser AIR d'un facteur 3–4 dès 1970 peut déplacer le premier capital vers
  le RAIL, alors qu'AIR seul fait 109 % d'AAAHogEx et RAIL seul 77 %. Seule la porte tranche.
- Critère : `profit_year` d'Opex (AGENTS §1), pas l'écart avec AAAHogEx.

## 5. Pistes écartées (rappel)

Multiplicateur « compte double » ×2 (AIR-MONOPOLY-1) ; extension C83 à 24 villes
(20 × 10 : +76,9 k£/an, 13 V / 7 D, p = 0,26, valeur −1,5 %) ; facteur de coût RAIL seul au
score (RAIL-CAL-1, inerte sous `K_dec`) ; table multiplicative de profit (V306) ; options
V307R/V307S, P1, P2. Les sites de gare Goods → ville (rayon, dégagement, gares jointes,
acceptation vérifiée tuile par tuile en 1 × 1 dans `builder_rail.nut:134`) relèvent du
travail utilisateur sur VPS.

## 6. Lot 1 livré (27/10, non commité)

Base : master `6c1481a1` (V233L, entonnoir de site B et spirale hybride AIR actifs par défaut).

**A priori** (`sweeps/estim_unifie_priors.py`, sortie `results/estim_unifie_priors_20261027.json`) :
recette réalisée (`profit + frais courants`) / recette brute prédite, années pleines (âge ≥ 2) à
flotte de construction (`vehs == n0`), rapport des sommes, corpus DUEL 40 × 10 du 21/10 (conditions
des portes). SOLO en contrôle.

| Mode | DUEL | SOLO | Retenu | Poids Bayes empirique (années-lignes) |
|---|---|---|---|---|
| RAIL | 0,918 (4 495 années-lignes) | 1,143 | **0,92** | 36 (DUEL), 72 (SOLO) |
| ROUTE | 0,572 (305) ; médiane 0,98 | 0,406 | **0,57** | ≈ 1 (bus et camions hétérogènes) |
| AIR | paires neuves 0,406 ; moyenne C121 des ratios par bras : hubsite 0,355, hubhub 0,459, newpair 0,409 → **0,40** | 0,48–0,67 | **0,40** | ≈ 9 |
| EAU | pas de mesure | — | **1,0** | — |

Le rapport AIR décroît avec l'âge (DUEL paires neuves 0,48 à 2 ans, 0,28 au-delà) ; il ne dépend
pas de la distance. Poids unique `w0 = 10` années-lignes pour tous les modes.

**Mécanisme** (bit 1) :
- `k_R[mode] = (n·ρ + w0·k0) / (n + w0)`, `ρ` rapport des sommes des cumuls par ligne
  (`estimRevReal`, `estimRevPred`, `estimRevN`, entiers sauvegardés avec la ligne), `n`
  années-lignes ; recalcul au rapport annuel et au rechargement (`persist.nut`, après
  `this._lines = liveLines`) ; facteurs remis à l'a priori au chargement des réglages.
- Recette prédite brute : `predRevenue` ; AIR : `c121RawRevenueAnnual` (avant facteur).
- AIR : `OpexC121RealizationFactor` renvoie `k_R.air` pour **tous** les bras ; le modèle C121
  l'applique à la recette brute et à la perte de cannibalisation, donc au choix de flotte. Cela
  remplace la réalisation directe P0 des hubs et la calibration C70 des paires neuves. Un
  changement de `k_R.air` invalide le cache du catalogue (`C121_CATALOG_ARM_LEARN_REV`).
- Autres modes : `OpexEstimProfit` = `P − (1 − k_R)·R` (un projet à faible marge peut devenir
  négatif). Observations (`profitIsObserved`), projets de flotte et projets sans recette gardent
  `OpexC70Profit` ; C70 continue d'apprendre pour eux (lot 3).
- Journal `ESTIM_KR phase=annual|reload year= mode= line_years= real= pred= k=`.

**Contrats** : `sweeps/test_estim_unifie.py` ; projection OFF exacte `sweeps/estim_unifie_legacy.py`
branchée dans `historical_bytes` (`n75_mc_legacy.py`) et `off_source` (V233L) ; inventaires de
réglages 78 → 79.

## 7. Revue critique du lot 1 (CoS, 27/10)

Deux problèmes reproductibles ont été corrigés sous le bit 1 :

- Quand la recette brute C121 n'était pas attachée à une ligne, l'apprentissage
  réutilisait `predRevenue` déjà multipliée par `k_R.air`. Le retour réel/prédit
  tendait alors artificiellement à 1. Ces observations AIR sont maintenant
  ignorées : seuls les couples comportant `c121RawRevenueAnnual > 0` entrent
  dans le corpus de calibration.
- `OpexEstimPublishRevenueFactors` invalidait les tableaux C121 lors d'une
  modification de `k_R.air`, mais les projets déjà assemblés dans le portefeuille
  retenaient encore leur ancien profit. La fonction renvoie désormais
  `airChanged` et le rapport invalide `_portfolioInvalidated`, ce qui force une
  reconstruction des economics au prochain cycle. Le retour de sauvegarde
  recalcule toujours les facteurs depuis les lignes restaurées.

**Couverture restante du lot 1** : WATER ne publie pas encore le couple
`trains0` / recette brute exploitable par le learner annuel : le mode reste au
prior 1,0. Une ligne AIR sans recette brute n'actualise pas le prior. Les projets
de flotte et les décisions V249/V252/V257/V259/V284 passent désormais par le
contrat du lot 3 lorsque son bit est actif.

## 8. Lot 2 — garde de caisse M5 (bit 2)

`OpexEstimFinanceCapital(mode, C, distance, devisReel, immobilise)` est partagé
par `OpexProjectFinanceCapital` (admission du portefeuille) et
`OpexEstimFinanceCashNeeded` (chantier, une seule `OpexCashReserve`). Le
coefficient est `1.063 + 0.003 × distance` pour RAIL, 1.17 pour ROUTE et 1.0 pour
AIR, EAU et flotte AIR. Le capital certifié par un devis réel est exclu du
second multiplicateur. Le fonds de roulement s'ajoute séparément.

Les tests de trésorerie des chantiers `task_air/road/rail/water.nut`, et de
`air_fleet.nut`, utilisent ce même besoin de caisse sous le bit 2 ; les marges
historique AIR (2k/12k/30k), EAU (+50k et `maxShipPrice`), ROUTE (+21 %), flotte
(+1k) sont neutralisées dans le chemin opt-in. L'arbitrage des quantités
achetables dans `projects_selection.nut` utilise le même budget. Le bit OFF
conserve les anciens tests et les marges de ses scores.

## 9. Lot 3 — renforts et remplacements M1/M2 (bit 4)

Les ouvertures RAIL, ROUTE, AIR et EAU ajoutent dans leur projet les quatre
composantes `deltaR`, `deltaE`, `deltaA`, `deltaC` et leur marge `deltaP`. Les
renforts AIR C121 enregistrent à la construction le différentiel physique
`n → n+1` : recette **brute** avant réalisation, entretien et amortissement
véhicule. Le classement de leur marge applique une seule fois `k_R.air`, puis
soustrait `deltaE` et `deltaA` ; les chemins historiques `v161Calibrate`,
facteur C121 / facteur de build, profit moyen de la flotte sont contournés sous
ce bit. Un instantané physique n'est valable qu'à sa profondeur de flotte
initiale : un nouveau palier requiert une nouvelle évaluation.

Les rénovations V249 (statue), V252 (avion), V257 (composition ferroviaire),
V259 (pont) et V284 (croissance ferroviaire) publient des dossiers
`deltaR/deltaE/deltaA/deltaC/deltaP` via `OpexEstimVProject`, avec score M1
commun basé sur `K_dec` et capital net, une fois la recette multipliée par son
facteur de mode. Les comparaisons d'horizons 5 ans, vie restante ou seuils
forfaitaires sont neutralisées uniquement sous bit 4 ; hors opt-in, les chemins
historiques restent accessibles. Les remplacements AIR V252 s'appuient à ce
stade sur la physique `OpexAirEconomics` des deux moteurs ; la migration de ce
type de chantier vers l'intégralité de C121 est une limite de la présente
implémentation.

## 10. Lot 4 — primitives partagées M4 (bit 8)

`OpexEstimMonthDays` unifie 365/12 jours par mois dans le débit des lignes AIR,
des calculs C121 et des estimations RAIL/ROUTE ; le chemin historique conserve
30 ou 30,4 selon l'appel. L'offre RAIL/ROUTE tient compte d'une note calculée
depuis la fréquence de visite, la place des véhicules et la physique de leurs
chantiers. `OpexEstimRivalAvailableMonthly` réduit le volume des sources sans
ligne locale à l'aide du pourcentage réellement transporté par une autre
entreprise, en gardant le pourcentage dans [0,100]. Le comparateur AIR des
moteurs utilise sous bit 8 le score du portefeuille et supprime la bande
préférentielle de ROI 1,25. Le nombre de trains reste physiquement limité à la
capacité de deux voies du constructeur existant ; le changer sans capacité de
quais correspondante serait un élargissement de lot distinct.

## 11. Qualification et artefacts

Bras de référence `OpexAI[estim_unifie=0]` contre les bras isolés 1/2/4/8 ;
intégrations successives 3, 7, 15. Carte et bundle identiques au sein de chaque
duel. Critère économique unique : `profit_year` d'OpexAI (pas son écart à AAA),
garde de valeur 5 %, `gain_short` 40×3 seuil +4 %, puis `non_erosion` 20×10
après porte A positive ; une intégration A négative exige ablation d'un bit à
la fois. Des campagnes qui échouent ou n'ont pas été exécutées ne constituent
aucun résultat économique exploitable. Les preuves et chemins exacts seront
renseignés ici à mesure de leur validation.

### 11.1 Pré-enregistrement des portes (avant la porte A)

Source locale : `master` à `6c1481a137938a45564d6273c62f094855fe0853`, arbre de
travail non commité avec lots 1–4, image `openttd-lab:latest` ID
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Le gel des smokes produit le bundle
`5e6c287cae517f69cb777dc2d5145a2ed57044bdc7ef109e3a6c92561f0ba483` ;
le bundle et chaque manifeste sont recalculés/contrôlés par le lanceur avant
chaque porte. Comparaison comportementale du **même code** :
`OpexAI[estim_unifie=0]` contre `OpexAI[estim_unifie=<bits>]`, toutes les autres
options à leur défaut courant. `probes=2` pour les panneaux usuels sur les deux
bras, `decision_log` inactif, map 256², départ 1970. Un seul conteneur à la fois ;
PC : `--cpus 10 --memory 8g --max-workers 10`.

Plan prédéfini des comparaisons à exécuter dans cet ordre :

| Étape | Bits seuls ou intégrés | ID politique | Préfixe de campagne |
|---|---:|---|---|
| Lot 1 | 1 | `estim1_lot1` | `estim1_lot1` |
| Lot 2 | 2 | `estim1_lot2` | `estim1_lot2` |
| Intégré 1+2 | 3 | `estim1_integ12` | `estim1_integ12` |
| Lot 3 | 4 | `estim1_lot3` | `estim1_lot3` |
| Intégré 1+2+3 | 7 | `estim1_integ123` | `estim1_integ123` |
| Lot 4 | 8 | `estim1_lot4` | `estim1_lot4` |
| Intégré 1+2+3+4 | 15 | `estim1_integ1234` | `estim1_integ1234` |

Pour chaque préfixe : `_smoke_1x1_20261027` (graine 42, horizon 1, santé),
`_porteA_40x3_20261027` (40 graines canoniques, 3 ans, `gain_short`,
`--required-seeds 40 --required-years 3 --min-useful-primary-delta-pct 4`,
Wilcoxon bilatéral p < 0,05, borne de gain +4 %, garde valeur −5 %), puis
`_porteB_20x10_20261027` **uniquement si A passe** (`non_erosion`, 20 graines,
10 ans, seuil 4 % enregistré mais non utilisé pour B). Un échec d'un lot seul
ne retire pas celui-ci des intégrations suivantes. Si les intégrés 3/7/15
échouent, ablations préfixées `estim1_ablation<15-4,15-2,15-1>` pour les
combinaisons non déjà mesurées, sans rechercher une graine favorable. Aucune
promotion de défaut selon un résultat partiel ou hors échantillon.

## 12. Reprise de revue du 27/10 — correctifs et vérifications

Le contrôle final porte sur `master` `6c1481a1` avec les lots 1–4 non
commités. L'inventaire des 26 fichiers `.nut` ESTIM et la projection OFF
`sweeps/estim_unifie_off_lots.py` ont été synchronisés **après revue** : le
contrat `test_off_projection_restores_head_bytes` vérifie pour chacun la
reconstitution octet par octet du fichier `HEAD` sous OFF, tout en conservant
`dist_bornes_unified` déjà présent dans `HEAD`.

Trois erreurs avérées de la reprise ont été corrigées avant le nouveau gel :

- **Lot 3, marginal de flotte AIR.** Le C121 attaché au dernier chantier
  représente la transition physique `n → n+1`. Multiplier cette marge par
  `entry.want` (jusqu'à quatre avions) extrapolait à tort le même supplément
  de demande et de cannibalisation à `n+2`, `n+3`, etc. Le projet opte
  désormais pour **un seul avion**, avec `payload.want = 1`, et publie
  `deltaP = deltaR − deltaE − deltaA`. Le prochain palier doit être réévalué
  depuis la flotte effectivement construite.
- **Lot 3, financement partiel de flotte.** Le redimensionnement d'un projet
  cloné utilisait `rawslot <- ...` pour modifier des champs `deltaR/E/A/C`
  déjà existants, alors que l'affectation Squirrel est `=`. Les champs
  sont maintenant affectés et `deltaP` est recalculé après ajustement.
- **Lot 2, dernier garde du chantier AIR.** Le montant requis était fondé
  sur `project.capital` du portefeuille. Il utilise désormais le `capital`
  du plan de construction effectivement choisi, avec la réserve unique.

Après ces corrections, la **suite complète**
`python -X utf8 -m unittest discover -s . -p "test_*.py"`
depuis `sweeps/` passe : **3 054 tests, 5 ignorés, 2 échecs attendus**.
Les contrats ciblés `test_estim_unifie.py`, `test_estim_unifie_lots24.py`
et `test_estim_unifie_vprojects.py` passent aussi ; `git diff --check` OK.
La couverture des renforts physiques reste limitée aux lignes où le C121
dispose du calcul marginal correspondant exactement à la flotte existante.

### 12.1 Smokes et sauvegarde après correctifs

Campagnes neuves `estim1_review_{2,4,8,15}_smoke_1x1_20261027`,
fichiers JSON, JSONL et manifestes sous `results/` : chaque variante a
**2/2 parties complètes**, sans erreur moteur, sur la graine 42, un an.
Bundle source commun
`aad38b5d539db89943617003d491db8f99b1587f72da2b7a9360edc54b751d0c` ;
image Docker
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` ;
PC `10 CPU / 8g / 10 workers` séquentiels. Les deltas de profit annuel à
**un an seulement** (informatifs, verdict moteur `diagnostic_only`) sont,
dans l'ordre 2, 4, 8, 15 : **−14 196 £, −6 082 £, +2 862 £, −116 594 £**.
Ils ne constituent aucun verdict d'adoption.

La sauvegarde intégrée `estim_unifie=15` utilise
`results/estim1_review_15_save_load_20261027.json` : phase initiale
3 ans (36 sauvegardes), sauvegarde rechargée datée **1971-07-01**,
phase de reprise 2 ans (24 sauvegardes). La trace `LOAD_RECONCILE`
prouve l'appel de `Load()` ; aucun motif de défaillance Save/Load n'a
été détecté. Limite du harnais : le rechargement crée une seconde compagnie
humaine fantôme, sans activité observée, distincte d'OpexAI.

La porte A 40×3 sur le **même code corrigé** est distincte des premiers
smokes et de l'ancienne porte A isolée du bit 1. Les verdicts définitifs
figurent dans la section de qualification suivante.

## 13. Porte A intégrée sur le code corrigé

La campagne `results/estim1_review_15_porteA_40x3_20261027.json`
compare `estim_unifie=0` à `estim_unifie=15` sur le bundle
`aad38b5d539db89943617003d491db8f99b1587f72da2b7a9360edc54b751d0c`.
Elle couvre **40/40 paires de parties complètes** (40 graines × 3 ans),
avec `gain_short` et le seuil relatif pré-enregistré de 4 %.

| Mesure | Résultat |
|---|---:|
| Delta moyen `profit_year` (variante − référence) | **+40 078,6 £/an** |
| Seuil +4 % du témoin | +91 477,8 £/an |
| Médiane appariée | +14 387 £/an |
| Victoires/défaites/égalités | 23/17/0 |
| Wilcoxon bilatéral exact | p = 0,4598 |
| IC95 bootstrap (20 000 tirages, graine 0) | [−52 965,7 ; +134 773,8] £/an |
| Garde de valeur (ratio des moyennes) | **+4,57 % : passe** |
| Verdict V102 | **`fail_primary`** |

Le point estimé est positif, mais il manque le seuil +4 %, la significativité
et une borne inférieure de l'IC95 strictement positive. Ce verdict
**n'autorise pas la porte B de l'intégré** ni une promotion des défauts.
L'échec appelle les ablations de chacun des quatre bits après les portes A
isolées, conformément au protocole.

## 14. Portes A isolées des lots 2–4

Les campagnes `estim1_review_{2,4,8}_porteA_40x3_20261027`
(JSON, JSONL, manifestes et logs sous `results/`) ont les mêmes bornes
statistiques, 40 graines et trois années que la campagne intégrée :

| Lot, bit actif | Paires | Delta moyen `profit_year` | Médiane | V/D/E | p Wilcoxon | IC95 bootstrap du delta | Valeur, ratio des moyennes | Verdict |
|---|---:|---:|---:|---|---:|---|---:|---|
| 2, `2` (caisse) | 40/40 | −20 074 £/an | −71 218 £/an | 16/24/0 | 0,4280 | [−94 121,6 ; +59 058,6] £ | +1,22 % | `fail_primary` |
| 3, `4` (renforts) | 40/40 | −48 038 £/an | −49 699,5 £/an | 16/24/0 | 0,0682 | [−107 849,8 ; +14 541,4] £ | +0,96 % | `fail_primary` |
| 4, `8` (physique) | 40/40 | −20 435 £/an | −18 449,5 £/an | 17/23/0 | 0,5360 | [−80 917,4 ; +41 254,2] £ | +0,25 % | `fail_primary` |

Pour tous les lots, la garde de valeur (perte maximum −5 %) passe mais
**aucun gain court significatif n'est démontré**. La porte A du lot 1
isolé, exécutée avant les correctifs de revue et publiée sous
`results/estim1_lot1_porteA_40x3_20261027.json`, est aussi `fail_primary`
(+12,3 k£/an, IC95 [−67,8 ; +98,5] k£, p = 0,83, garde de valeur
+0,02 %) ; son bundle antérieur empêche de la présenter comme un comparatif
sur le gel source `aad38b5d`.

Les portes A échouées ne justifiaient pas de porte B dans le protocole initial.
La décision utilisateur ultérieure (« code plus propre et cohérent, sans perte »)
a motivé une porte B de **non-érosion** de l'intégré 15, lancée séparément
par Claude sous `estim1_integ15_porteB_20x10_r2_20261027`. **En cours à la
présente revue ; aucun résultat ni verdict B présumé.** Les ablations du paquet
`15 − {1, 2, 4, 8}` sont également documentées : 14 +36,9 k£, 13
−40,3 k£, 11 −18,3 k£, 7 +36 k£ par an, toutes `fail_primary`.

## 16. Revue finale de code pendant la porte B — 27/10

La revue porte sur les quatre bits et leurs consommateurs ; le source `.nut`
reste gelé pendant le duel B. La projection OFF octet pour octet sur les 26
fichiers modifiés apporte une garantie forte sur le réglage 0 ; les tests
statiques et les smokes 1×1 vérifient les branches opt-in. Le rechargement
reconstruit `ESTIM_K_R` à partir des cumuls de lignes, et l'invalidation du
portefeuille suit la modification du facteur AIR. Ces vérifications ne
démontrent pas à elles seules l'équivalence de toutes les décisions en jeu.

**Bilan de propreté sous bit 15 :** le calcul de recette corrigée a un
point d'entrée `OpexEstimProfit`, les investissements sur lignes existantes
partagent `OpexEstimVProject` et les contrôles de financement utilisent
`OpexEstimFinanceCapital/CashNeeded`. Le remplacement du mois 30/30,4,
la note de service et les débits rivaux ont des primitives communes.
La simplification reste **partielle** : `OpexEstimAttachProjectComponents`
publie les composantes des ouvertures, mais les décisions de portefeuille
utilisent encore `profitAnnual` et plusieurs adaptateurs spécifiques. V252
repose toujours sur `OpexAirEconomics` plutôt que sur un différentiel C121.
Les anciennes branches C70, V161, les marges par mode et les horizons V249/
V257/V259 demeurent nécessaires au défaut 0 ; elles pourraient être retirées
seulement après adoption explicite du défaut 15 et nouvelle revue de leurs
appelants. Le code n'est donc pas encore un modèle physique unique intégral.

**Réserves de revue, sans correctif `.nut` pendant B :**

- **Moyenne, V252** (`ai/OpexAI/task_v252.nut`, fonction
  `OpexEstimV252Project`, lignes 30–45) : le différentiel entre deux flottes
  *homogènes* est divisé par le nombre de véhicules, alors que le remplacement
  réel ne touche qu'un appareil et que la flotte peut être hétérogène. Une
  différence de cadence, de capacité ou de cannibalisation peut donc changer
  la recette marginale effective. Correctif proposé après B : modéliser
  explicitement la flotte mixte avant/après (ou refuser le score homogène si
  ses hypothèses ne sont pas satisfaites), puis ajouter un contrat de recette
  marginale et relancer les validations gelées. Ce défaut de modèle est
  antérieur au banc et le patch n'est pas appliqué.
- **Moyenne, contrat M1** (`ai/OpexAI/projects_builders.nut`, fonction
  `OpexEstimAttachProjectComponents`, lignes 74–90, et
  `projects_models.nut`, `OpexEstimProfit`) : les `deltaP` attachés aux
  ouvertures sont descriptifs tandis que le portefeuille peut employer une
  autre voie de calcul de `profitAnnual` (notamment C121 AIR et C70). La
  cohérence des valeurs de classement n'est donc pas vérifiée par la seule
  présence de `deltaR/E/A/C`. Correctif proposé : tester et imposer
  l'identité entre profit de décision et composantes calibrées, avec un
  indicateur explicite de recette déjà corrigée pour éviter une deuxième
  application de `k_R`. Aucun changement du chemin de classement en cours.

Les deux réserves sont des **limites de qualification** de la cohérence,
pas des régressions démontrées du défaut 0. Le jugement d'absence de perte
appartient à la porte B en cours ; la propreté est améliorée sur les contrats
et gardes, mais les anciennes voies restent présentes et les deux réserves
empêchent d'affirmer une unification complète.

## 17. Lot 5 — calibration RAIL par distance (bit 16, 27/10)

**Réouverture limitée autorisée par l'utilisateur.** Malgré la clôture de
`RAIL-CAL-1` aux portes du 21/10, une nouvelle formulation sous `estim_unifie=16`
est autorisée pour ce lot seulement : les deux corrections portent ensemble sur
la **recette** et le **coût pré-A***. `rail_cal=1` demeure non qualifié.

**Échantillon hors ligne.** Le corpus DUEL 40 × 10 du 21/10 comprend
4 495 années-lignes RAIL mûres (`âge ≥ 2`) dont la flotte égale la flotte
de construction. Comme le prior du bit 1, la recette réalisée est
`Σ GetProfitLastYear + Σ GetRunningCost`, rapportée à la recette prédite brute.
Les quartiles fixes de distance sont ≤90, 91–127, 128–172 et ≥173 tuiles.
Après recentrage à une moyenne **pondérée par recette prédite de 0,92**,
les rapports par quartile sont **0,7341 / 0,8527 / 0,9728 / 1,0652**
(effectifs **1 227 / 1 156 / 1 109 / 1 003**, IC95 respectifs
[0,6779 ; 0,7977], [0,7977 ; 0,9157], [0,9033 ; 1,0427],
[1,0071 ; 1,1238]).

La droite retenue est `k_R0(d)=0,5722990662 + 0,00258519378 × d`, avec
distance en tuiles. La pente est positive (IC95 bootstrap par partie,
3 000 tirages : **[0,001874 ; 0,003255]**) ; le centre pondéré se situe
à **134,497** tuiles. La validation croisée par partie réduit la MAE annuelle
de recette **13 559 £ (prior plat) à 12 949 £ (droite)** ; les quatre paliers
donnent **13 008 £**. La droite possède moins de degrés de liberté et gagne
sur 32/40 parties : elle est préférée aux paliers.

Le devis **avant recherche A*** de 1 014 constructions DUEL exploitables
donne `k_C(d)=1,0778667894 + 0,00324189259 × d` ; pente IC95 bootstrap
**[0,002986 ; 0,003488]**. Pour un devis déjà physique obtenu après A*,
**`k_C=1`**. Le coût recalé n'agit que dans le dénominateur du classement
`1000 × P / max(C_score, K_dec)` des candidats RAIL **non tracés**.
`OpexProjectFinanceCapital` et toutes les gardes restent à leur financement
RAIL **100 %**, conformément à la décision du 26/09.

**Comportement des bits.** Le bit 16 **seul** corrige la recette RAIL dès le
classement, sans nécessiter le bit 1 ; les autres modes restent sur C70/C121.
Le bit 31 combine toutes les corrections 1/2/4/8/16. Le niveau RAIL
`ESTIM_K_R.rail` est appris en partie à partir du ratio de sommes, avec
le même rétrécissement `(n × ρ + 10 × 0,92)/(n + 10)` qu'au lot 1.
La pente reste figée : le facteur utilisé est
`k_R(d)=ESTIM_K_R.rail × k_R0(d)/0,92`. La flotte et les années exigées
par l'observateur sont inchangées. Le même profil s'applique aux `ΔR`
des renforts et remplacements RAIL sous bit 4 ; il n'est pas réappliqué
aux profits déjà observés. Les coûts physiques de ces interventions ne
sont pas majorés.

**Validation et traçabilité.** Le réglage `estim_unifie` garde `default_value=0`
pour les quatre difficultés et `max_value=31`, sans réglage supplémentaire.
`sweeps/estim_unifie_priors.py` et
`docs/estim1_bit16_calibration_20261027.md` détaillent le corpus, les IC
et le contrôle SOLO. La table de projection OFF
`sweeps/estim_unifie_off_lots.py` est figée en comparant les sources courantes
aux sources historiques déjà revues, sans `--refresh` contre HEAD qui
contient ESTIM-1. Les preuves de campagnes sont ajoutées ci-dessous au fur
et à mesure des mesures ; la sonde `probes=258` (panneaux + journal de
décisions, sans nouveau réglage) permet de tracer au plus 32
`ESTIM16_RAIL_SCORE` sans surcharger les journaux ordinaires.

### Premier smoke et porte A isolée

Le smoke `estim1_bit16_smoke_1x1_20261027` (graine 42, un an,
`--probes 258` équilibré entre bras) a terminé ses deux parties, sans erreur
Squirrel. Delta final de profit **−23 368 £/an**, garde de valeur **−6,58 %** ;
le verdict `diagnostic_only` découle du format 1×1, qui n'est pas une porte.
Les premières traces ne contiennent **aucun** `ESTIM16_RAIL_SCORE` ; ce monde
court n'apporte pas de preuve d'exposition du classement RAIL.

La campagne `estim1_bit16_porteA_40x3_20261027` est complète sur le bundle
`1d920f47d10c947ccc5e7368a23b7b2909017e9283ab3842a8b9471498b44d2c` :
**40/40 paires**, `profit_year` delta moyen **+18 019,4 £/an**, médiane
**+5 152 £/an**, **20V/20D/0E**, Wilcoxon **p=0,58081**, IC95 bootstrap
**[−60 718,95 ; +92 745,38] £**, valeur (ratio des moyennes) **+3,2678 %**.
Seuil de gain +4 % : **+92 361,6 £/an**. Verdict **`fail_primary`** : seuil
et significativité non atteints, même si la garde de valeur passe. La porte B
de non-érosion de ce lot isolé est maintenue par décision utilisateur.

### Gel corrigé pour les quatre portes définitives

La revue Squirrel a repéré puis fait corriger un appel V257 dont la nouvelle
expression de distance lisait `line` hors de sa portée : le paramètre est
désormais explicitement transmis aux deux appels (sélection, dépôt). V257/V284
emploient maintenant la même distance du candidat que le corpus RAIL ; les
droites recette et coût sont bornées aux distances observées **15–250** tuiles.
La projection OFF sur **26 sources** a été reconstruite et revérifiée, sans
relancer `--refresh` contre HEAD. Suite complète finale : **3 060 tests OK**,
5 ignorés, 2 échecs attendus ; `git diff --check` passe.

Les campagnes corrigées `r2` pour le bit 16 et `r3` pour l'intégré 31 ont
le **même bundle** `ec515a3a68af52666bf1080da1ab313b7ccfa7906fdae99b3ecf5ace8f9851cb`.
Les campagnes antérieures restent archivées, sans être utilisées pour juger
ce gel. Chaque porte A compte 40 paires complètes sur 1970–1972,
avec gain minimal +4 %, Wilcoxon exact p<0,05, IC95 bootstrap positif et
garde de valeur −5 %.

| Porte A (bits) | Δ moyen `profit_year` | Médiane | V/D/E | Wilcoxon p | IC95 bootstrap du Δ (£/an) | Δ valeur | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| [`16`, isolé](../results/estim1_bit16_porteA_40x3_r2_20261027.json) | **+29 544,2 £/an** | +73 695 £/an | 21/19/0 | 0,40494 | [−59 333,7 ; +113 407,2] | **+5,1163 %** | `fail_primary` |
| [`31`, intégré](../results/estim1_bit31_porteA_40x3_r3_20261027.json) | **−87 018,7 £/an** | −135 798 £/an | 15/25/0 | 0,03813 | [−184 354,8 ; +20 496,0] | **−1,3650 %** | `fail_primary` |

La garde de valeur passe dans les deux bras. La hausse ponctuelle de valeur
ou un p de Wilcoxon inférieur à 0,05 ne suffisent pas : aucun IC95 ne prouve
le gain +4 % demandé. Les portes B 20×10 sont néanmoins requises par la
décision utilisateur de ce lot, y compris pour l'intégré négatif à trois ans.

### Porte B — non-érosion isolée à dix ans

`estim1_bit16_porteB_20x10_r2_20261027` utilise le même bundle que les
portes A. Les **20/20 paires** sont complètes (1970–1979), sans échec moteur.
Le delta `profit_year` est **−18 828,65 £/an** en moyenne, médiane
**+70 686 £/an**, **12V/8D/0E**, Wilcoxon descriptif **p=0,84082**,
IC95 bootstrap **[−179 467,6 ; +140 725,5] £/an** et changement de valeur
(ratio des moyennes) **+1,73687 %**. Verdict natif `non_erosion` : **`pass`**
(borne haute de l'IC95 ≥ 0 et garde de valeur −5 % respectée).
Ce résultat accepte la **non-érosion** du lot isolé à dix ans, sans établir
un gain significatif ni renverser le verdict A de gain (`fail_primary`).

### Porte B — intégré 31 à dix ans et décision croisée

`estim1_bit31_porteB_20x10_r2_20261027` partage le **même bundle source**
`ec515a3a68af52666bf1080da1ab313b7ccfa7906fdae99b3ecf5ace8f9851cb`
avec A16, A31 et B16 : **20/20 paires** complètes en 1970–1979,
`failed_runs=[]`. Le `profit_year` de la variante moins la référence est
**+60 609,65 £/an** en moyenne, **+10 467 £/an** en médiane,
**10V/10D/0E**, Wilcoxon descriptif **p=0,43043**, IC95 bootstrap
**[−90 700,5 ; +207 463,4] £/an**. Cependant la valeur d'entreprise
(ratio des moyennes) chute de **−18,933477 %**, très au-delà de la garde
de −5 % : verdict natif **`fail_value_guard`**. Le signe ponctuellement
positif du profit n'annule ni cette forte érosion de valeur ni l'absence
de gain statistiquement établi.

| Profil | Porte A 40×3 `gain_short` | Porte B 20×10 `non_erosion` | Conclusion |
|---|---|---|---|
| Bit 16 seul | `fail_primary` (+29,5 k£/an ; IC95 traversant zéro) | `pass` (−18,8 k£/an ; valeur +1,74 %) | **Non-érosion B** selon sa règle, **pas de gain A démontré** |
| Bits 31 intégrés | `fail_primary` (−87,0 k£/an) | **`fail_value_guard`** (+60,6 k£/an ; valeur −18,93 %) | **Échec de qualification**, pas d'adoption |

La règle B de non-érosion exige seulement une borne haute de l'IC95 du
profit non négative et une garde de valeur respectée : un `pass` B16 n'est
donc **pas une preuve de rentabilité accrue**. Dans ces conditions, aucun
passage de `estim_unifie` à 16 ou 31 **par défaut** n'est qualifié ; le
réglage reste **0**. Aucun commit ni push n'est effectué dans ce lot.

### Exposition du score RAIL (diagnostic distinct des portes)

Le premier smoke 42 × 1 an n'avait produit aucune trace du score RAIL.
Après B31, un diagnostic **RAIL seul** (AIR/ROAD/WATER désactivés **dans
les deux bras**) a été exécuté sur la graine 1337, trois années,
`probes=258`, référence 0 contre variante 16 :
`results/estim1_bit16_railscore_exposure_seed1337_3y_20261027.json`.
Deux parties complètes, zéro échec moteur, bundle source **identique**
`ec515a3a68af52666bf1080da1ab313b7ccfa7906fdae99b3ecf5ace8f9851cb`.
Le verdict natif est `diagnostic_only` (une seule paire, non une porte).

Dans le journal moteur de la variante, **32/32 événements**
`ESTIM16_RAIL_SCORE` (plafond de sonde atteint), tous le **16/01/1970** :
distances **29–186** tuiles, `actual=0`, et dans tous les cas
`finance=capital` tandis que `score_capital > finance`, avec rapport
`score_capital/finance` allant de **1,17188 à 1,68085**. Les facteurs de
recette `kR` enregistrés varient effectivement selon la distance.

Exemple **d=179** : `capital=finance=82 693 £`,
`score_capital=137 119 £`, `kR=1,0350487`, score effectif **414,8732**.
Le premier chantier RAIL n'est choisi que le 22/01 et construit le 26/01 ;
le 16/01, `C69_BUILD_DATES` est encore vide et `K_dec=0` selon
`OpexC69ComputeKDec`. **À profit calibré fixé**, si le dénominateur était
resté au capital financier, le score de ce candidat aurait été
`414,8732 × 137119 / 82693 = 687,93` : la correction de coût infléchit
donc bien un **score effectivement utilisé** (−273,06 points dans cette
comparaison à numérateur fixé), **sans renchérir la garde financière**.
La recette est, elle aussi, calibrée : le score réel complet n'est pas
identique à ce contrefactuel qui ne retire que le facteur de coût.

Les premiers projets choisis sont identiques entre bras, puis la séquence
des choix et leurs dates divergent (le troisième projet est choisi le
13/02 dans la référence et le 14/03 dans la variante). Ce constat est
**descriptif**, pas une attribution causale isolée de chaque construction :
les mondes évoluent ensuite séparément. Le diagnostic montre la **prise
d'effet du classement**, pas un gain de profit ; les quatre portes
multimodales ci-dessus restent seules décisionnelles.

**Réserves de portée.** Les traces sont plafonnées aux 32 premières
alternatives RAIL admissibles et l'indicateur `actual` du journal ne regarde
que `project.capitalIsActual`, alors que le calcul de score vérifie aussi
le payload. Le cas post-A* `capitalIsActual` (`k_C=1`) est couvert par les
tests statiques, pas par ces 32 observations (`actual=0`). Les projets mixtes
V249 avec `modeRevenues` continuent d'utiliser un scalaire RAIL par revenu,
sans distance propre à chaque composante ; l'hypothèse ne s'applique donc
pas à toutes les recettes RAIL possibles. Enfin un `railPlan` préparé C121
peut disposer d'un devis A* avant le marquage `capitalIsActual` : vérifier
un éventuel double redressement sur ce chemin avant toute promotion.
**Aucune correction comportementale supplémentaire** n'est introduite
après le gel des quatre portes.
