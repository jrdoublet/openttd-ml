# ESTIM-31 — priorités déduites des trois derniers duels 20×10 (30 octobre 2026)

**Statut : analyse documentaire du nouveau défaut publié, sans nouvelle simulation.**
La sélection du gagnant est **définitive** et inchangée ; ce document cherche
les prochains leviers plausibles, **pas** une justification rétrospective de
relancer les autres variantes. [Tâches et ordonnancement](taches.md),
[résultats qualifiés](estim31_top3_20x10_20261030.json),
[trajectoires annuelles](estim31_top3_decade_trajectory_20261030.json),
[rapport de qualification](estim31_phase_combinatoire_20261030.md).

## 1. Campagnes comparables et validité

Les trois variantes ont chacune **20 paires, 40/40 parties saines**, mêmes
20 graines, année 1970–1979, observation au **1er décembre** de chaque
année, image et provenance contrôlées, `estim_unifie=31`, `eb14_progressive=3`,
`probes=2`. Le rapport de classement calcule **100 × moyenne des 20 profits
OpexAI / moyenne des 20 profits AAAHogEx du propre duel** ; il ne calcule
ni la moyenne des ratios individuels ni un effet causal par permutation.

| Rang à 10 ans | Variante | Ratio Opex / AAA fin 1974 de son 20×10 | Ratio fin 1979 | Profit Opex 1979 | Profit AAA 1979 |
|---|---|---:|---:|---:|---:|
| **1** | **V161 AIR2,00 / RAIL0,75 / poids15 / pente — défaut élu** | **103,24 %** | **66,557726 %** | **4,256 M£** | **6,394 M£** |
| 2 | V161 AIR2,50 / RAIL0,75 / poids15 | 102,92 % | 65,921947 % | 4,226 M£ | 6,410 M£ |
| 3 | V161 × C121 N1/N2, AIR2,00 / RAIL0,75 | 106,37 % | 65,188575 % | 4,291 M£ | 6,582 M£ |

Le top3 historique à **40×5** était 106,062929 %, 105,171758 % et
103,798667 % dans l'ordre **inverse entre le premier et le troisième à
dix ans**. Le changement de rang ne signifie pas que le moteur N1/N2
dégrade causalement le profit : les AAAHogEx adverses diffèrent dans les
trois duels. Le gagnant n'a que **+0,636 point** sur le deuxième et
**+1,369 point** sur le troisième au score décennal observé. **Aucune
inférence de significativité entre les trois politiques** n'est fondée
sur leur seul écart de ratio. La règle utilisateur élisait bien le rang
mesuré à dix ans, sans garde de valeur ou p-valeur supplémentaire.

## 2. Le décrochage tardif, quantifié

Trajectoire du **gagnant à dix ans**, bras variant de la même cohorte :

| Année | Profit Opex / AAA | Trains Opex / AAA | Avions Opex / AAA | Aéroports Opex / AAA | Caisse Opex |
|---|---:|---:|---:|---:|---:|
| 1972 | **131,56 %** | 19,8 / 10,9 | 52,9 / 29,0 | 31,0 / 26,4 | 0,263 M£ |
| 1974 | **103,24 %** | 24,5 / 26,3 | 78,5 / 40,1 | 33,3 / 34,0 | 1,039 M£ |
| 1975 | **88,88 %** | 25,9 / 31,5 | 81,7 / 40,6 | 33,7 / 34,6 | 2,128 M£ |
| 1977 | **73,62 %** | 28,4 / 44,4 | 84,7 / 44,9 | 34,2 / 35,7 | 7,256 M£ |
| 1979 | **66,56 %** | 29,6 / 56,3 | 84,3 / 48,0 | 34,3 / 36,2 | **14,743 M£** |

Entre décembre 1974 et décembre 1979 :

- **AAAHogEx :** profit **+3,572 M£/an** (+126,6 %), trains **+30,0**,
  avions +7,9, aéroports +2,2.
- **OpexAI :** profit **+1,343 M£/an** (+46,1 %), trains **+5,1**,
  avions +5,8, aéroports +1,0. Le gain de profit AAA sur cinq ans
  dépasse celui d'Opex de **2,229 M£/an**. La situation de 1974
  (Opex +0,091 M£) devient celle de 1979 (Opex **−2,138 M£**).
- Le gagnant a **0 £ de prêt** et **14,743 M£** de caisse en 1979.
  Une pénurie générale d'argent disponible ne suffit donc pas à
  expliquer le blocage tardif ; **il reste à prouver qu'un chantier
  rentable et constructible était effectivement proposé**.
- Sur **19 graines sur 20**, OpexAI termine derrière AAA ; le score
  global ne résulte pas simplement d'une graine perdante isolée.

Le point d'inflexion est commun aux trois variantes : première année
sous 100 % en **1975** (88,88 / 87,64 / 94,26 %) et forte croissance
ferroviaire de l'adversaire à partir de cette date. Ce constat ne
justifie **pas** de choisir un coefficient AIR/RAIL en fonction de
1974 au détriment des années 1975–1979.

## 3. Comptabilité réelle 1979 : RAIL puis AIR

Les trois [archives PLYR](estim31_ten_v161_accounts_1979_20261030.json)
([AIR2,50](estim31_ten_v161a250_accounts_1979_20261030.json),
[C121 N1/N2](estim31_ten_motorcap_accounts_1979_20261030.json)) relèvent
les postes **nets cumulés sur l'année comptable jusqu'au 1er décembre
1979**, pas les achats individuels ni un profit marginal par mode.

| Poste, dans le duel du gagnant (1979) | OpexAI | AAAHogEx | Retard des **recettes** Opex |
|---|---:|---:|---:|
| **Revenu ferroviaire** | **0,799 M£** | **1,967 M£** | **1,168 M£** |
| **Revenu aérien** | **3,578 M£** | **4,436 M£** | **0,857 M£** |
| Revenu routier | 0,0005 M£ | 0,0092 M£ | 0,009 M£ |

**Les déficits de recettes RAIL + AIR valent 2,025 M£**, soit un montant
du même ordre que le déficit **global** de profit annuel (**2,138 M£**),
mais **ils n'en sont pas une décomposition causale** : dépenses, prix des
véhicules nets des ventes, stations, liquidations et calendrier diffèrent.
Le rail explique **58 % du déficit combiné de recettes AIR+RAIL** du
gagnant ; chez les autres finalistes, le déficit de recettes ferroviaires
vaut **1,348–1,384 M£**, contre **0,831–0,868 M£** pour l'aérien.

En 1979, le gagnant possède **84,25 avions** contre **48,0** chez AAA,
mais ne collecte que **81 %** de ses recettes aériennes. Rapport descriptif
**recettes YTD / stock d'avions au checkpoint** : ~**42,5 k£** chez
Opex contre ~**92,4 k£** chez AAA (×2,18). Ce ratio **n'est pas une
mesure annuelle par avion survivant ni une preuve de sous-chargement** :
le stock à une date diffère de la flotte exposée toute l'année, les
modèles, âges, parcours et conditions de demande sont hétérogènes.
Il rend néanmoins **prioritaire un audit de rendement AIR par ligne et
par avion**, plutôt que l'achat de davantage d'appareils.

En 1979, les dépenses PLYR de **construction toutes modes** valent
**60,7 k£** chez Opex contre **213,0 k£** chez AAA ; les postes
**véhicules neufs moins ventes toutes modes** sont **167,3 k£** contre
**719,5 k£**. Ces postes sont **nets**, ne distinguent pas les achats
bruts ni les modes, et ne permettent pas d'attribuer mécaniquement un
« manque de trains achetés » ; ils confirment une **faible activité
d'investissement comptabilisée** chez Opex malgré la trésorerie.

## 4. Vérification au code et diagnostic indépendant

- **Expansion RAIL V284 :** [`task_v284.nut`](../ai/OpexAI/task_v284.nut)
  `OpexV284Select`, actif dès **1973** si caisse disponible ≥1 M£,
  écarte les lignes non fret, à plusieurs trains, mixtes, en double voie,
  sans attente d'au moins **un wagon**, sans note de quai ou sans
  marge positive sous ESTIM bit 4 ; lorsqu'il faut un second train,
  une **boucle physiquement faisable** est requise. Le contrôle périodique
  n'examine les opportunités admissibles qu'au plus mensuellement.
  **Hypothèse testable :** une seule rame donne une fréquence de
  ramassage médiocre, qui diminue la note et le volume capté et donc
  le backlog utilisé comme signal ; un renfort potentiellement utile
  pourrait être censuré **avant** son devis. Ne pas conclure que la
  solution est « deux trains partout », anciennement testée sans succès.
- **Expansion nouvelle :** [`task_rail.nut`](../ai/OpexAI/task_rail.nut)
  `_expandRailLines` et `task_projects.nut` distinguent expansion,
  recherche A*, financement et sélection ; les projets doivent survivre
  à une série de gardes. Un nombre de trains faible **n'indique pas à lui
  seul** si l'obstacle est la génération, les sites, A*, la valeur
  estimée, le classement ou la saturation.
- **Ancien C63, 26/10 :** [autopsie 5×11](multi1_retard_1975_1979_resultats_20261026.md)
  de **code antérieur au gagnant** : en 1975–1979, moyenne par carte
  **1,2 lignes AIR neuves, 4,2 RAIL**, 39,6 interventions de flotte,
  **836 jours** classés `invalid`, **273** `absent`, **134**
  `waiting_compute`, **6** `unaffordable` sur cinq années, 16,27 M£
  de caisse en 1979. **Attention :** `invalid` est le reliquat d'une
  classification C63, **pas** 836 jours de site impossible. Les profits
  matures 1979 du code précédent atteignaient AIR 3,561 M£ pour
  4,668 M£ prévus à la construction, RAIL 0,924 M£ réalisés pour
  0,822 M£ prédits. Ces valeurs **ne sont pas** les estimations de la
  nouvelle source ESTIM31/V161 ; ne pas mélanger les cohortes.
- **Observabilité disponible :** `task_report.nut` émet `LINE_REVENUE`
  avec profits prédits/réalisés, flotte, note, attente ; V284 ajoute
  source produite/transportée, wagons, capacité et longueur. Le
  `DECISION_LOG` expose `PROJECT_CHOSEN`, `RAIL_ATTEMPT`, `V284`
  et les motifs de rejet. **`probes=2` n'inclut pas automatiquement
  tout ce diagnostic**. Les comptes PLYR n'identifient pas le nombre
  de transactions brutes ou leur ligne ; des opcodes partiels ne sont
  pas le CPU total.

## 5. Priorisation recommandée (aucune adoption à ce stade)

| Ordre | Action distincte et falsifiable | Mesure minimale / critère de sortie |
|---|---|---|
| **P0 — diagnostic** | **Identifier pourquoi les nouveaux investissements cessent après 1974**, séparément AIR/RAIL et réseau existant. Réunifier les causes **sans catégorie C63 résiduelle** : absence de candidats, projet non admissible, faible ROI prévu, devis, gare, A*, coût/opcodes, attente de travail, limite de flotte et projet réellement construit. | Lire d'abord les traces existantes de la **source élue**. Sinon sonde passive bornée avec identités et compteurs uniques `1974–1979`, même source, sans changer les décisions. Publier un entonnoir par année, mode et graine, et **au moins un exemple de projet rentable/physique et injustement écarté avant de coder ON**. |
| **P1 — RAIL volume rentable** | Séparer **nouvelles lignes** et **capacité des lignes existantes**. Auditer `V284` : rames uniques, cadence, note/source, attente, wagons, seuil `waiting`, projet ESTIM, géométrie boucle, échecs et occasions d'une seconde rame ; examiner `SITEAB` seulement s'il est réellement dominant dans le nouvel entonnoir. | Table année/ligne de **production → note → captage → capacité → profit marginal**, histogramme des motifs de non-sélection ; un contre-factuel SHADOW cohérent et constructible avant porte A. Le constat 29,6 trains vs 56,3 AAA n'est **pas** une consigne « acheter 27 trains ». |
| **P1 — AIR rendement plutôt que flotte** | Décomposer les **84 avions / 34 aéroports** : recettes/running réels par ligne, véhicules, cycles de charge, vitesse, distance, hubs et cannibalisation ; auditer les décisions V161, V252 et moteurs C121 sous les vrais effets cumulés. | Identifier des avions/lignes à **marge marginale faible ou négative**, avec réallocation plausible et preuve de capacité/villes desservies. Garder le gagnant AIR2,00 et l'exhaustivité C121 tant qu'aucun essai propre n'a gagné à 10 ans. |
| **P2 — nouveaux marchés AIR/RAIL** | Comparer les **aéroports encore libres**, la couverture, les monopoles et les opportunités à finance abondante ; puis EB-10/EB-13 sur les coûts et recettes réellement captables. | Liste de couples OD non desservis **avec acceptation, disponibilité des sites, devis et profit marginal** ; aucun bonus uniforme « monopole ×2 » sans observation causale. |
| **P2 — arbitrage du capital** | Après avoir identifié des projets exécutables, établir pourquoi **14,7 M£** de caisse sont conservés : score, seuils, garde C69/ESTIM, projet inapproprié, éviction par flotte, latence. | Métriques d'occasions écartées et délai jusqu'à construction ; **pas** de nouvelle manipulation de marge AIR ou d'emprunt fondée seulement sur la caisse haute. |
| **P0 technique parallèle** | Corriger les contrats de la **grande suite** après l'adoption des nouveaux défauts, sans modifier le comportement économique élu. | Séparer les tests du défaut public de la reproduction OFF historique ; test ciblé et suite complète verte ou limites caractérisées (état initial 3 175 : 84 échecs / 16 erreurs ; ancien master déjà non vert). |

**Arbitrage de coût :** les rapports annuels 20×10 des trois finalistes,
les snapshots PLYR et les diagnostics historiques disponibles suffisent
pour **classer** les tâches. Un nouveau **1×10 avec logs** serait utile
plus tard **uniquement** si l'analyse des journaux de la source élue ne
permet pas de calculer l'entonnoir des rejets après 1974. Il ne serait
ni une quatrième qualification du top3, ni une mesure causale d'effet
de politique ; prévoir une seule graine déclarée à l'avance, même
source et carte, source de vérité des fonds et journal, budget d'opcodes
borné et aucune modification de défaut. **Aucun banc supplémentaire
n'a été lancé pour ce rapport.**

## 6. Ce que ces données ne permettent pas d'affirmer

Les différences de recettes et de flottes **ne prouvent pas** qu'il faut
réduire la flotte AIR ou augmenter le plafond des trains. Les 20×10
permettent de comparer le **résultat global**, non la valeur d'une
intervention unitaire, et les périodes de PLYR ne sont pas des
transactions par ligne. La baisse du ratio ne vient pas d'un accident
isolé, mais la cause précise du pipeline n'est pas déduite du seul
nombre de véhicules. Les anciennes variantes `NO-GO` (EB2, P4,
MULTI-1, RAIL-CAPEX, FRONT-PAX, bons cargos) restent closes ; les
actions proposées exigent **une hypothèse nouvelle et une exposition
prouvée** avant tout test comportemental.
