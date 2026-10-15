# V216 — Estimateurs : décomposer, mesurer, corriger (avant le premier projet rail)

*Plan du 16/10/2026 (Claude), révisé le même jour après vérification des chiffres, du code et des
chantiers d'estimateurs antérieurs (liste des corrections au §9). Rien n'est codé ni lancé.
Numéro V216 : premier libre après V215 (retiré).*

**En bref.**
- En partie complète, la ligne rail voyageurs moyenne réalise **0,18 fois** son revenu prévu, contre **1,37** en rail seul, avec le même code. Le fret ne bouge pas (0,87 / 0,75).
- L'estimateur rail voyageurs prend 22 % de la production des deux villes et ignore nos aéroports qui desservent déjà ces villes : c'est le cas de 21 lignes sur 22.
- Dans le jeu, une gare qui couvre les mêmes maisons que notre aéroport prend surtout à l'aéroport. Le bon objet du score est donc le gain net de la compagnie, pas le revenu de la ligne.
- Trois corrections d'estimateur ont déjà échoué, parce qu'une meilleure prévision ne change pas forcément les achats. Ce plan mesure d'abord, rejoue ensuite les décisions hors ligne, et ne lance un banc qu'à la fin.

## 0. La question

En partie complète, tout ce qui rend le rail voyageurs plus attractif fait reculer l'aérien :

| Banc partie complète (16/10) | Profit | Chantiers AIR |
|---|---|---|
| V207+V212+V214, 20×10 | −904 k£/an à 10 ans | |
| V207+V212, 10×3 | −244 k£/an | 401 → 322 |
| V207 physique seule (arrêts joints + courrier), 10×3 | −157 k£/an | 401 → 380 |
| V207 + part 30 + revenu 110, 10×3 | −103 k£/an | 414 → 379 |

En rail seul, les mêmes réglages passent les deux portes. Le défaut peut se trouver à trois endroits :

1. **l'estimation** : le profit prévu d'une ligne rail voyageurs est faux en partie complète ;
2. **le classement** : profit / max(K_dec, capital) ;
3. **la règle de financement** : on construit ce qui rentre maintenant.

Les mesures du §1 désignent d'abord l'estimation. Mais une meilleure estimation n'améliore le
profit que si elle change des achats (§1.1, §1.8).

## 1. Ce qu'on sait (vérifié le 16/10)

### 1.1 La chaîne de décision : où une estimation peut changer un achat

| Étape | Code | Rôle de l'estimation |
|---|---|---|
| Génération du candidat | `OpexMakeCandidate` (`candidates.nut` ~l. 760-790) | **Admission** : rejet si profit annuel ≤ 0, ou si profit × 1000 / itérations A* prévues < 500 (voyageurs) ou 200 (fret) (`VIVIER_RATIO_FILTER`, actif par défaut). Seuil voyageurs ≈ 290 £ à 30 tuiles, 3,2 k£ à 75, 27 k£ à 150. |
| Vivier → finançables | `OpexProjectSelectAffordable` | **Aucun rôle** : le filtre de caisse porte sur le capital de financement, avant le tri (AIR : capital + marge 30/12/2 k£ ; rail : capital, puis devis réel après l'A*). |
| Tri | `OpexProjectInsertDefensive` (`projects_selection.nut` l. 1527) | Palier C77 d'abord (AIR défensif : 2 ou 1 ; tout le reste : 0), puis score `fundScore = profit calibré × 1000 / max(K_dec, capital)` (l. 1240, avec le créneau précoce AIR), puis revenu. |
| Calibration | `OpexC70Profit` | k_mode = 1 tant qu'aucune ligne n'a 2 ans, c'est-à-dire toute l'année 1970-71. |
| Achat | B6, `PORTFOLIO_MAX_BATCH` = 1, plancher relatif 0 | Le premier finançable est construit ; un projet qui ne rentre pas est sauté. |
| Dimensionnement | `OpexLineEconomics` (rames, wagons), C121 (avions) | Taille de la rame ou de la flotte. |

**Conséquence.** Une correction de l'estimateur ne change un achat que de trois façons :

- par l'admission : le candidat passe sous 0 ou sous le seuil d'opcodes ;
- par l'ordre entre les projets finançables d'un même palier ;
- par le dimensionnement.

Elle ne change jamais « ce qui rentre ». Quand l'AIR ne rentre pas, retirer un rail voyageurs
surestimé fait acheter le finançable suivant (fret, route, flotte). S'il n'y en a pas, rien n'est
acheté : la caisse monte et l'AIR arrive plus tôt, sans règle de réservation.

### 1.2 Deux estimateurs de demande très différents

| | Rail voyageurs (`OpexPaxCandidates`, `candidates.nut` l. 1654) | AIR (`OpexC121StationCompetitionBuckets` et `…AllocatedMonthly`, `air_coverage.nut` l. 458 et 544) |
|---|---|---|
| Demande | `(production A + production B) × 22 %` : production du mois dernier de toute la ville | production des tuiles réellement couvertes (comptage des maisons) |
| Note | prévue selon la cadence (ancrage 50 %) | prévue selon la cadence |
| Nos autres gares | **ignorées** (`OpexOriginService` ne lit que les lignes rail) | **toutes comptées**, tous modes (gares rail, arrêts de bus), avec leur note |
| Gares adverses | ignorées | ignorées par défaut : `c121_air_visible_competition`, limité aux aéroports adverses, est resté à 0 après la porte 40×6 |
| Courrier (V207) | même part de 22 % | modèle séparé |

La part de 22 % (`TOWN_CATCHMENT_SHARE_PCT`) a été calibrée le 28/08 sur 9 lignes. Ce résultat
date d'avant le 09/09 : il ne fait plus foi.

### 1.3 Ce que fait le jeu (OpenTTD 15.3, `MoveGoodsToStation`)

Pour une tuile qui produit des voyageurs et que plusieurs gares couvrent, le jeu :

1. déplace `production × meilleure note` ;
2. partage ce volume entre compagnies selon la meilleure note de chacune ;
3. partage la part d'une compagnie entre ses gares selon leurs notes.

**Conséquence.** Sur les maisons que couvre déjà notre aéroport, une nouvelle gare rail n'ajoute
presque rien à la compagnie, sauf si sa note dépasse celle de l'aéroport : elle prend surtout à
l'aéroport.

Le score devrait donc viser le **gain net de la compagnie** : demande des tuiles nouvellement
couvertes, plus l'effet d'une meilleure note, moins ce que perdent nos autres lignes. Ce n'est pas
le revenu propre de la ligne. En partie complète, le réalisé par ligne du §1.4 **surestime** donc
déjà le gain du rail voyageurs.

### 1.4 Réalisé / prévu : mesure propre sur 40 graines, même code (`1675dd2`)

Méthode :
- lignes construites en 1971, avec au moins 180 jours d'exploitation ;
- profit ou revenu annualisé, ramené à la rame ou à la flotte initiale ;
- bras de référence des deux portes V172, `v172_complet_porteA_40x3_20261016` et `v172_railseul_porteA_40x3_20261016` ;
- script `v216_facto_analyse.py` (joint au prompt PC du §4.1, à verser dans `sweeps/` avec tests), qui reproduit exactement ces chiffres.

| Mode et cargo | Contexte | n | Revenu : médiane / somme | Profit : médiane / somme |
|---|---|---|---|---|
| Rail voyageurs | partie complète | 15 | 0,16 / 0,18 | 0,04 / 0,03 |
| Rail voyageurs | rail seul | 11 | 1,30 / 1,37 | 1,60 / 1,66 |
| Rail fret | partie complète | 80 | 0,80 / 0,87 | 0,83 / 0,91 |
| Rail fret | rail seul | 43 | 0,89 / 0,75 | 0,92 / 0,76 |
| AIR | partie complète | 296 | 0,57 / 0,57 | 0,53 / 0,54 |

- **Le contexte divise le revenu rail voyageurs par 7 à 8**, avec le même estimateur. Sur le profit, les coûts fixes amplifient l'écart (effet de levier).
- **Le fret ne bouge pas** : c'est le témoin.
- **L'AIR réalise 0,57 de son revenu prévu**, à l'échelle de la ligne entière. Ramené à l'avion unique acheté à la construction, c'est 0,40. On ne sait pas encore à quelle profondeur de flotte correspond la prévision C121 : l'analyse F devra le trancher.
- Limites de la mesure :
  - n est petit en rail voyageurs ;
  - les lignes construites sont celles que l'estimateur surestime le plus (malédiction du vainqueur), ce qui tire tous les ratios vers le bas sans expliquer un facteur 8 ni le changement de signe de l'erreur ;
  - une première année partielle annualisée reste approximative.
- Les ratios 0,02 et 0,33 de la première version de ce plan sont retirés : ils venaient de `LINE_REVENUE` non annualisé sur 10 graines et mélangeaient dates de construction et années partielles.

**Un coefficient constant ne peut pas corriger une erreur qui change de signe selon le contexte.**
La part de 22 % est trop haute en partie complète et trop basse en rail seul. V212 (revenu ×1,5)
corrigeait le rail seul et aggravait la partie complète.

### 1.5 Les lignes rail voyageurs partagent leurs villes avec nos aéroports

Source : télémétrie de ligne (`line_telemetry`, relevés de décembre, villes de chaque ligne), bras
de référence de la partie complète, lignes existantes en décembre 1971 (même script).

| Lignes rail voyageurs | Nombre |
|---|---|
| avec notre aéroport dans au moins une des villes desservies | 21 sur 22 |
| … dans les deux villes | 11 |
| … dans aucune | 1 (profit −2,5 k£) |

Profit 1972 par train : médiane de 0,9 à 2,3 k£ en partie complète, contre 13,4 k£ en rail seul
(62 lignes).

Ces données ne séparent pas l'effet de nos aéroports de celui des bus et des aéroports
d'AAAHogEx, puisque les deux sont présents ensemble. Le plan factoriel du §4.1 sert à les séparer.

### 1.6 Le courrier sous V207

`RAIL_BUILD` du bras physique (`v207phys_complet_10x3_20261016`), 31 lignes voyageurs sur 10 graines :

- profit prévu moyen 14,9 k£, revenu courrier prévu moyen 7,2 k£ : le courrier équivaut à 49 % du profit prévu ;
- sur les 18 lignes qui ont un `LINE_REVENUE`, le courrier fait 38,5 % du revenu prévu ;
- le revenu courrier prévu dépasse le profit total prévu sur **2 lignes sur 31** ;
- ce sont des lignes courtes : 22 à 34 tuiles, 1 wagon voyageurs + 1 wagon courrier, ~37-40 k£.

Le courrier est le flux où l'aérien gagne le plus : les avions courrier seuls rapportent 651 k£ en
1974 (fiche ventilation 5 ans).

### 1.7 La perte se concentre en 1971

Chantiers par année, 10 graines (`v207phys_complet_10x3_20261016`), référence → physique :

| Année | AIR | Rail voyageurs | Fret |
|---|---|---|---|
| 1970 | 84 → 86 | — | — |
| 1971 | 197 → 173 | 10 → 18 | 20 → 17 |
| 1972 | 120 → 121 | 17 → 13 | 6 → 6 |

Sélections B6 non incrémentales de 1971 (nombre de sélections, et entre parenthèses le nombre
moyen de finançables) :

| Bras | Aucune | AIR | Rail | Flotte | Route |
|---|---|---|---|---|---|
| Référence | 811 | 238 (26,2) | 215 (10,1) | 55 | 30 |
| Physique | 738 | 187 (38,5) | 191 (20,3) | 57 | 25 |

Avec le courrier, plus de candidats rail entrent dans le budget et sont achetés plus tôt, donc on
attend moins (811 → 738 sélections vides). L'AIR perd 24 chantiers en 1971 et ne les rattrape pas
en 1972.

### 1.8 Ce qu'ont appris les chantiers d'estimateurs précédents

| Chantier | Erreur de prévision | Profit |
|---|---|---|
| C121, concurrence visible des aéroports adverses (08/10) | biais mensuel de capture +36,6 % → +11,8 % (3 graines réservées), meilleure sur toutes les bornes annuelles | porte A 40×6 : −15,5 k£/an (−0,9 %), 21/19, p = 0,85, `fail_primary` |
| P2, a priori froid par famille (rejeu LOSO, 14/10) | — | 3 inversions admissibles sur 202 décisions, **0 construction alternative** |
| H2, `k_revenue` AIR appris | — | −16,9 k£/an (5×5) |
| `air_p0_learned_revenue` | — | −20,5 k£/an |
| `capital_quote_learning` | — | −106,8 k£/an (40×3) |

**Trois leçons :**

1. **Une prévision plus juste ne garantit pas un meilleur profit.** Avant tout banc, il faut compter les achats qui changent et regarder ce qui les remplace (§6).
2. **Un facteur par mode ou par famille déplace le niveau sans changer l'ordre** (P2). Ici l'erreur dépend du contexte, pas du mode : seule une correction de structure peut la traiter.
3. **Corriger le revenu AIR n'a jamais payé.** L'AIR est sur-prédit (0,57), mais trois corrections de son revenu ont été neutres ou négatives. On le mesure ici, sans nouvelle correction AIR tant que le rejeu ne montre pas qu'elle change des achats.

### 1.8 bis Ce qu'apportent les diagnostics EST-01 à EST-16 (Codex, publiés le 16/10)

Source : [`scores_estimateurs_plan_20261014.md`](scores_estimateurs_plan_20261014.md).

Ces diagnostics sont l'autopsie d'une seule ligne de fret : ligne 16, charbon, 36 tuiles, un train
et deux wagons. Ils portent sur une partie (graine 42, ancien code `36ef545`), reconstruite à partir
des sauvegardes mensuelles. Il n'y a eu aucun banc ni aucun changement de code.

| Lot | Résultat |
|---|---|
| EST-05 | En 1972, à flotte stable, le profit réalisé est inférieur de 25 % au prévu |
| EST-13 | Avant tout concurrent, la gare capte 1 158 à 1 247 t sur 11 mois, pour 946 t prévues (+22 à +32 %). Sa note est de 72-74 % au lieu des 63 % prévus |
| EST-14 | Les arrivées (900 à 1 021 t) correspondent au prévu ; le stock monte à la gare source (0 → 245 t) |
| EST-15/16 | Le cycle du modèle (≈ 15 j) ignore le séjour en gare. Charger 2 wagons de 30 t, par tranches de 5 unités tous les 40 ticks, prend ≈ 3,2 j par gare. Le cycle réel est de 21-22 j, soit une capacité de ~84 t/mois au lieu de 120 |
| EST-10 à 12 | En janvier 1972, AAA construit une gare sur la même mine et prend 44 à 47 % du charbon alloué : notre capture tombe à 54-64 % du prévu |
| EST-04 | Une ligne doublée en cours d'année fausse l'entrée C70 : 57 % au lieu de 73 % rapporté au train initial |

**Conséquences pour V216 :**

1. **Deux erreurs se compensent.** La note prévue est trop basse, donc l'offre est sous-estimée. Le séjour en gare est oublié, donc la capacité est surestimée. Le volume tombe juste par hasard. Ces deux erreurs doivent être mesurées séparément (§3.1, §5 B) et corrigées ensemble (V216f), sinon le fret se dégrade.
2. **La concurrence arrive après la construction.** Le partage observé suit exactement la mécanique du §1.3. Un estimateur qui ne regarde que les gares existantes ne voit pas ce risque. On mesure donc le taux d'arrivée d'AAA après notre construction (§5 G).
3. **EST n'explique pas l'écart du rail voyageurs en partie complète.** Il ne dit rien des voyageurs, du courrier, de l'AIR ni de nos aéroports. Le constat du §1.4 reste entier.
4. **La méthode par sauvegardes ne passe pas à l'échelle** : 16 micro-tâches pour une seule ligne. Les helpers `sweeps/station_supply.py` et `station_supply_bounds.py` servent à valider la sonde sur quelques lignes ; la mesure de masse vient de la sonde.
5. **Une seule ligne ne donne aucune constante** : ni le séjour de 7 j, ni le partage de 45 %. C'est cohérent avec le test d'invariance (§5 D).

### 1.9 Déjà réfuté : ne pas reproposer tel quel

- `c121_territory_first` : réserver la caisse du prochain aéroport (supprimé le 11/10).
- `RAIL_TERRAIN_FACTOR` = 170.
- V126 : capital AIR exact + marge 2 k£.
- Bonus fret dans le score (annulé le 13/10).
- Scores rail `simple_roi` et `simple_opcode`.
- `air_p0_learned_revenue`.
- P2, P3, P4 et ses variantes, H1 à H3.
- Concurrence visible C121 (40×6 neutre).
- V176 : classer le rail par profit absolu.
- **P1, attente courte : retirée à la clôture du fil V165** (13/10 ; fil des seuils clos sans banc).

## 2. Ce qui manque pour juger

- **La décomposition au moment du choix.**
  - `PORTFOLIO_RANK` ne sort que le profit brut, le score, le coût et le ROI d'un top réduit.
  - `B6_PORTFOLIO` ne décrit que le projet choisi et le meilleur finançable. Le meilleur non finançable, l'AIR qu'on attend, n'y figure pas.
- **Les candidats rejetés à la génération** (profit ≤ 0, sous le seuil d'opcodes). Ils ne sont pas journalisés, donc on ne peut pas rejouer une correction qui relève une estimation, comme en rail seul.
- **Les flux réalisés par ville et par compagnie.**
  - La télémétrie relie les lignes aux villes, mais en décembre seulement et sans les flux.
  - `AICargoMonitor` donne voyageurs et courrier pris en charge par ville, et fret par industrie, pour une compagnie donnée. OpexAI ne l'utilise pas.
  - AAAHogEx-115 ne l'utilise pas non plus (vérifié par grep) : interroger ses compteurs ne perturbe pas ses décisions.
- **Le gain net de la compagnie.** Rien ne mesure ce que perd notre aéroport quand une gare rail ouvre dans la même ville.
- **Le réalisé par composante.** `LINE_REVENUE` ne sépare voyageurs et courrier que pour les lignes V207, et la première année est partielle.

## 3. Étape 1 — instrumentation (code, défaut 0, purement passive)

Un réglage `v216_probe` (défaut 0, inerte) commande les blocs ci-dessous. Aucun ne modifie un tri,
une admission, un financement ou un dimensionnement.

### 3.1 `SCORE_DECOMP` : la décomposition au moment du choix

**Quand**
- À chaque sélection réelle (chemins `build`, `reselect` et `incremental` de B6), du 1/1/1970 jusqu'au premier `RAIL_BUILD` voyageurs + 180 jours.
- Puis une sélection par mois jusqu'à la fin de 1972.
- À chaque premier `RAIL_BUILD` fret.

**Pour qui** : tous les finançables, les 10 meilleurs non finançables de chaque mode, et le choisi.

**Quoi.** Une décomposition commune à tous les modes, cargo par cargo, lue sur les objets déjà
présents. Il n'y a **aucun recalcul d'économie** : si un champ manque, la sonde écrit `na`.

| Bloc | Champs |
|---|---|
| Identité | mode, kind, bras AIR, cargo(s), src, dst, distance, clé |
| Demande | production A/B, part appliquée (22 % ou part C121), note prévue, offre mensuelle |
| Offre | véhicules, wagons et capacité unitaire par cargo, durée de trajet, **séjour en gare calculé** (tranches de chargement par wagon) et séjour utilisé par le modèle (aujourd'hui nul), allers-retours par mois, cadence, `loadDays` |
| Volume | transporté = min(offre, capacité) |
| Prix | revenu par unité (distance, jours de transit) |
| Revenu | revenu annuel par cargo, facteur de réalisation C121 |
| Coûts | exploitation, amortissement, capital véhicules, capital infrastructure, marge, capital de financement (modèle ou devis) |
| Score | profit brut, k_mode, profit calibré, K_dec, dénominateur retenu, fundScore, palier C77, créneau précoce, finançable |
| Contexte | caisse, réserve, budget, nombre de finançables, meilleur non finançable (score, capital, mode) |

### 3.2 Estimateur fantôme V216a : calculé et journalisé, jamais utilisé

Pour chaque candidat rail voyageurs et chaque projet AIR journalisé, la sonde calcule à côté du
modèle courant :

- **la couverture propre** : la part de la production de la zone de la future gare déjà couverte par nos autres gares (autre mode ou autre ligne) ;
- **la couverture adverse** : la même part pour les gares adverses de tous types. On les détecte par le propriétaire des tuiles de gare ; leur note est illisible, on suppose donc une note égale ;
- **la part de la ligne** : le partage façon `MoveGoodsToStation` (§1.3), avec les notes connues ou supposées ;
- **le gain net de la compagnie** : tuiles nouvellement couvertes, plus le gain de note, moins le prélèvement sur nos autres gares.

La gare rail n'est pas encore placée quand le candidat est généré. La sonde prend donc une zone
autour du point de ville retenu par le candidat, puis refait le calcul au `RAIL_BUILD` avec les
vraies tuiles de gare, pour valider l'approximation.

Le calcul est mis en cache par ville et par mois, et son coût est mesuré au smoke. Comme il coûte
des opcodes, il doit être actif dans les deux bras.

### 3.3 `TOWN_FLOW` : les flux réalisés par ville et par compagnie

Une fois par mois, pour chaque ville où une compagnie a une gare :

- production et total transporté de la ville (`AITown.GetLastMonthProduction`, `GetLastMonthSupplied`) ;
- voyageurs et courrier pris en charge **par nous** et **par AAA** (`AICargoMonitor.GetTownPickupAmount`, suivi continu) ;
- pour le fret, la prise en charge par industrie desservie (`GetIndustryPickupAmount`).

À vérifier au smoke :
- le premier appel démarre le compteur et renvoie 0 ;
- la compagnie adverse est acceptée (sinon l'appel renvoie −1). D'après la source 15.3, seul un identifiant hors bornes serait refusé.

### 3.4 Rejets à la génération

Pour le rail voyageurs, à chaque génération :
- le nombre de candidats rejetés, par motif (profit ≤ 0, seuil d'opcodes) ;
- les 5 meilleurs rejetés, avec leur décomposition.

### 3.5 Contrats (`sweeps/test_v216_probe.py`)

- Réglage déclaré 4 fois à 0, lu une seule fois dans `OpexLoadSettings`.
- Aucun appel hors `if (V216_PROBE)`.
- Empreinte des fonctions de sélection inchangée une fois les blocs de sonde retirés.
- Smoke 1×1 sur 3 ans :
  - pas de « Your script made an error » ;
  - opcodes de la sonde mesurés ;
  - compteurs AAA non nuls.

## 4. Étape 2 — campagnes de mesure

### 4.1 Plan factoriel 2×2 avec les réglages existants (PC, peut partir tout de suite)

**Mise à jour PC du 15/10 : F1 et F2 terminés.** [Résultats et statistiques brutes](v216_factoriel_pc_20261015.md), [bilan et passation](v216_factoriel_pc_20261015_suite.md), [preuves compactées](../evidence/review/v216_factoriel_pc_20261015/README.md). 160/160 parties saines, 80/80 paires complètes, aucune exclusion ; même code et bundle dans les quatre cellules. Revenu voyageurs réalisé/prévu A/B/C/D : 0,182 / 0,242 / 0,808 / 1,059. Écart de contexte descriptif confirmé, sans isolation causale de l'effet de nos aéroports. Le pré-enregistrement ci-dessous est conservé comme historique ; aucune relance F1/F2 à faire.

Le bras de contraste « rail seul » de la première version de ce plan était invalide : le lanceur
applique `--aaahogex-setting` à AAA dans les deux bras. On croise donc deux facteurs, nos modes et
ceux d'AAA :

| | AAA complet | AAA rail seul |
|---|---|---|
| **Nous complet** | A (existe, 40 graines) | **B, à lancer** |
| **Nous rail seul** | **C, à lancer** | D (existe, 40 graines) |

Deux campagnes 40×3 sur master `517372b`. Chacune refait une cellule existante comme référence,
pour que tout soit mesuré sur le même code :

- **F1, AAA restreint au rail** : référence D (nous rail seul), variante B (nous complet) ;
- **F2, AAA complet** : référence A (nous complet), variante C (nous rail seul).

Lecture des comparaisons :

| Comparaison | Ce qu'elle isole |
|---|---|
| B contre A | effet des bus et aéroports d'AAA, nos aéroports présents |
| C contre D | effet des bus et aéroports d'AAA, sans nos aéroports |
| A contre C, B contre D | effet de nos propres aéroports |

On mesure le réalisé/prévu par mode et cargo (§1.4) et la co-localisation (§1.5), avec les deux
scripts joints au prompt PC. Le verdict du lanceur est sans objet : ce sont des diagnostics.

### 4.2 Campagnes sondées (VPS, après l'étape 1)

**À résoudre avant lancement :** le test D du §5 exige le fantôme dans A/B/C/D ; les deux diagnostics ci-dessous ne couvrent que A et D. Les données F1/F2 actuelles n'ont pas le fantôme. Préciser la collecte nécessaire pour B/C ou conserver le test D explicitement incomplet, sans ajouter implicitement une campagne ni déclarer le critère satisfait. La sonde reste à coordonner selon le §10.

Deux 20×3, sonde active dans tous les bras (`decision_log=1,probes=6,v216_probe=1`,
`--script-debug --line-telemetry`), bras `ref` contre `phys` (V207 arrêts 2 + courrier) :

- une en partie complète ;
- une en rail seul, avec AAA restreint.

Le bras `phys` multiplie les lignes rail voyageurs observées. On ne tire aucun verdict économique
du profit de ces bancs.

## 5. Étape 3 — analyses (`sweeps/analyze_v216.py`, avec tests)

**A. Pourquoi le premier rail passe**, graine par graine.
- Pour le rail choisi : palier, finançabilité et composantes du score.
- Les mêmes éléments pour le meilleur AIR finançable et pour le meilleur AIR non finançable.
- L'écart décomposé : revenu voyageurs, courrier, capital, K_dec, marge.

**B. D'où vient l'erreur.** Par mode, cargo et contexte, on décompose le logarithme du rapport
réalisé/prévu :

- revenu = volume × prix ;
- volume = min(offre, capacité) ;
- offre = production × part × note ;
- capacité = véhicules × capacité unitaire × 30 / (trajet + séjour en gare).

L'offre et la capacité se mesurent séparément, parce que leurs erreurs se compensent (§1.8 bis).
Le stock en attente à la gare source sert de témoin : un stock qui monte signale une ligne limitée
par la capacité, même quand le modèle la croyait limitée par l'offre.

Côté réalisé : la note vient de la télémétrie, le volume de revenu / prix et de `TOWN_FLOW`, la
part des prises en charge par ville rapportées à la production. On sait ainsi si l'écart vient de
la part captée, de la note, de la capacité ou du prix.

**C. Gain net de la compagnie.** Étude d'événement autour de chaque ouverture rail voyageurs (et
AIR), dans les villes desservies :
- prises en charge de la compagnie 3 mois avant l'ouverture contre 3 à 6 mois après ;
- comparées au volume propre de la ligne : on obtient la part cannibalisée ;
- confrontées au gain net prévu par le fantôme.

**D. Test d'invariance : le critère principal, gelé avant les données.** Pour l'estimateur
courant et pour le fantôme, on calcule le réalisé/prévu du revenu rail voyageurs dans les quatre
cellules A à D. Le fantôme est retenu si :

- son rapport est compris entre 0,7 et 1,4 dans chaque cellule ;
- l'écart max/min entre cellules est au plus de 1,5 (aujourd'hui 1,37 / 0,18 ≈ 7,6) ;
- le fret reste inchangé.

**E. K_dec et dénominateur.** Combien de fois K_dec l'emporte sur le capital, par mode. C'est un
recalcul hors ligne de l'ordre.

**G. Arrivée tardive de la concurrence.** Avec `TOWN_FLOW` et les prises en charge par industrie
d'AAA, on mesure la part de nos sources (villes et industries) qu'AAA vient partager dans les 12 mois
qui suivent notre construction, par mode et par cargo, et la perte de capture associée. Si ce taux
est stable, il peut devenir un terme de risque estimé, et non un coefficient arbitraire.

**H. Validation de la sonde.** Sur 3 à 5 lignes, la capture et les arrivées mesurées par la sonde
sont comparées aux bornes tirées des sauvegardes avec les helpers EST (`sweeps/station_supply.py`,
`station_supply_bounds.py`).

**F. AIR.** La même attribution qu'en B, pour comprendre le 0,57. C'est une mesure, pas une
proposition (§1.8).

## 6. Étape 4 — rejeu des décisions hors ligne

Sur les clichés `SCORE_DECOMP`, on rejoue chaque sélection avec l'estimateur fantôme, dans
l'ordre de la chaîne réelle : admission (≤ 0, seuil d'opcodes), palier C77, finançables, ordre.

Pour chaque sélection qui change, on note :

- **ce qui remplace le choix** : un autre projet, avec son mode. Les renforts sont signalés, car ils ne doivent pas passer devant le rail ;
- **ou rien** : on note alors les jours d'avance de l'AIR suivant (14 à 20 jours par achat évité selon V165) ;
- **la valeur estimée du changement** : prévu × ratio réalisé du mode, du cargo et du contexte (§1.4, §4).

**Critère pour passer au banc**, à remplir entièrement :
- dans le bras `phys`, au moins un achat changé par partie en moyenne en 1971-72 ;
- une valeur estimée positive sur au moins 70 % des graines où un achat change ;
- le test D réussi.

Sinon, on s'arrête et on consigne le constat. Pas de banc « pour voir » : c'est la leçon de P2 et H1.

## 7. Étape 5 — corrections candidates, chacune derrière un réglage à défaut 0

**V216a — demande rail voyageurs structurelle.** C'est la candidate principale.
- Elle remplace la part fixe de 22 % par le fantôme du §3.2 : production réellement couverte, partagée façon OpenTTD.
- La part de la ligne dimensionne la rame ; le gain net de la compagnie entre dans le score.
- Deux niveaux, que l'analyse B départage :
  - **a1** : nos gares seulement ;
  - **a2** : nos gares et les gares adverses.
- L'objectif est un estimateur juste dans les deux contextes, qui remplace V212 (×1,5) et la constante de 22 %.
- Ce n'est ni une marge, ni une réserve, ni un bonus : rien à voir avec les rejets du §1.9.

**V216b — courrier rail seulement hors de nos villes à aéroport.** C'est le repli bon marché si
V216a coûte trop d'opcodes.

**V216c — l'AIR voit-il nos gares rail ? Oui (vérifié).**
- `OpexC121StationCompetitionBuckets` parcourt toutes nos gares, tous modes : rien à faire.
- Par défaut, l'AIR ne voit en revanche aucune gare adverse. On ne rouvre ce point que si l'analyse F montre que les bus d'AAA expliquent le 0,57, et après le rejeu.

**V216d — coût d'attente explicite (règle de financement).**
- C'est proche de P1, retirée à la clôture de V165 : on ne le rouvre qu'avec l'accord de l'utilisateur.
- Il faut aussi que le rejeu montre une perte d'au moins ~80 k£/an une fois V216a en place.

**V216f — cycle rail avec séjour en gare, couplé à la note** (issu d'EST-15/16)
- Ajouter au cycle de capacité un séjour calculé à partir des wagons : tranches de 5 unités tous les 40 ticks, aux deux gares.
- Corriger en même temps la note prévue (63 % prévus contre 72-80 % observés sur la ligne 16), selon l'analyse B. Corriger le séjour seul baisserait la capacité sans relever l'offre, et dégraderait le fret.
- Contrat : pas de double comptage avec `loadDays` (`economy.nut` l. 365), qui agit déjà sur la note et la capture.
- Valeurs vérifiées par l'API NoAI (capacité des wagons, chargement progressif) ; aucune constante de 7 j.
- Elle touche tous les modes rail, fret compris. Le critère passe donc aussi par le test d'invariance du fret, puis par le rejeu et les portes.

**V216e — a priori de calibration 1970-71 : abandonnée.** C'est une redite de P2 (0 construction
changée).

## 8. Étape 6 — bancs de qualification (AGENTS.md §4.1)

À la sortie du rejeu, une candidate à la fois :

1. Contrats, puis smoke 1×1 sur 3 ans.
2. **V216a seule, partie complète** : porte A 40×3.
   - L'exposition attendue est faible au défaut actuel : environ un rail voyageurs par partie en 1971, effet probablement sous le seuil de 82,6 k£.
   - On relève donc l'exposition : moins de rails voyageurs déficitaires, AIR non réduit.
3. **V216a + V207 physique, rail seul** : portes A puis B contre V207 seul, pour vérifier que les gains du rail seul se conservent. Si a2 est retenue, V216a agit aussi en rail seul.
4. **V216a + V207, partie complète** : porte A contre master. On cherche au minimum la non-érosion, sur le schéma de V172 : portes rail seul passées, partie complète neutre, défaut décidé par l'utilisateur.

Ensuite seulement : retrait ou remplacement de V212, et nouveau test de V214 seul en partie complète.

## 9. Corrections apportées à la première version (vérifications du 16/10)

| Première version | Vérification |
|---|---|
| Ratios 0,02 et 0,33 en partie complète | Non annualisés, brouillés par les dates de construction : remplacés par la mesure propre du §1.4 |
| « Une dizaine de lignes où le courrier dépasse le profit » | 2 sur 31 |
| « Courrier = 49 % du profit prévu » | Exact par rapport au profit ; c'est 38,5 % du revenu prévu |
| « Rien ne relie une ligne rail voyageurs à l'aéroport » | La télémétrie donne les villes de chaque ligne : 21 lignes sur 22 sont co-localisées |
| Bras de contraste `railseul` | Invalide (AAA restreint dans les deux bras) : remplacé par le factoriel |
| V216c « à vérifier » | Vérifié : l'AIR compte nos gares de tous modes, et aucune gare adverse par défaut |
| Tri « par score » | Le palier C77 passe avant ; l'admission à la génération est ajoutée (§1.1) |
| V216d, V216e | V216d soumise à l'accord de l'utilisateur (P1 retirée) ; V216e abandonnée (redite de P2) |
| Seule la concurrence est en cause | La vraie grandeur du score est le gain net de la compagnie, cannibalisation comprise (§1.3) |
| Critère : « 5 % des choix changés » | Remplacé par : achats changés, ce qui les remplace, valeur estimée, invariance (§5 D, §6) |

## 10. Coordination avec Codex (items « EST »)

Sur le VPS, aucun item EST n'est visible : rien dans `docs/taches.md`, aucune branche ni aucun
commit de ce nom. Les seuls travaux de score visibles sont `codex/scores-p0…p4` (13/10) et
`codex/p2-p4-bilan-suspension-20261014` (14/10, suspendu).

Partage proposé :
- Claude prend l'instrumentation (§3), les mesures (§4) et le rejeu (§6) ;
- toute formule EST peut entrer dans le rejeu comme un fantôme de plus.

Fichiers touchés : `candidates.nut`, `economy.nut`, `projects_selection.nut` (sonde seulement),
`air_coverage.nut` (lecture seule), `projects_diagnostics.nut`, `settings.nut`, `info.nut`,
`globals_pre.nut`. Il faut la branche ou le document EST avant de coder V216a.

## 11. Ordre, coût, arrêts

| Étape | Travail | Durée | Sortie |
|---|---|---|---|
| 4.1 | Factoriel F1 + F2 (PC) | ~3 h de PC | attribution nos aéroports / AAA |
| 1 | Sonde, contrats, smoke | ~1 jour de code | branche `v216-probe` |
| 4.2 | 2 campagnes 20×3 sondées | ~4 h de VPS | journaux |
| 3-4 | Analyses A à F, rejeu | ~1 jour | `docs/v216_autopsie_estimateurs_<date>.md` |
| 5-6 | V216a, puis portes | ~1 jour + bancs | verdicts |

**Arrêts**
- Le factoriel montre que le contexte n'explique pas l'écart : V216a abandonnée sans code.
- Le fantôme échoue au test D : V216a abandonnée.
- L'analyse B ne montre pas, sur la masse des lignes, la compensation note/séjour vue sur la ligne 16 : V216f abandonnée.
- Le rejeu ne change aucun achat, ou les change avec une valeur négative : arrêt, constat consigné.
- Défauts, fusions et commits restent des décisions de l'utilisateur.
