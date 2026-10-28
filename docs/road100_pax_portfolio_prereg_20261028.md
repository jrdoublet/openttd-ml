# ROAD100-20 — Portefeuille de quartiers PAX, pré-enregistrement (28/10/2026)

## Hypothèse et nature de la mesure

Après LONG v19b, les deux axes interurbains testés sur seed 42 ne
captent au mieux que 35 et 31 PASS/mois au total sur leurs quais
racines. Leur profit projeté favorable (~1 322 / ~746 £/an) ne
représente pas une preuve d'exploitation ; les deux corridors ont
0 construction et 0 recette réelle. Le rival AAA utilise un nombre
très supérieur de véhicules et plusieurs tuiles de station par
StationID. Hypothèse : une politique **distincte** qui choisit les
arrêts sur l'union de quartiers physiquement raccordables, puis
construit les satellites et ajuste ultérieurement la flotte à la
demande *effectivement produite*, peut accroître les recettes
ROUTE mesurées, sans répéter le seul joint-stops post-construction
ROAD100-8 rejeté.

## Expérience opt-in et protocole

- Réglage `road100_pax_portfolio=0` par défaut, activable en 1
  uniquement si ROAD100-7 `road100_site_first=1` et ROUTE seule ;
  ne pas combiner avec `road100_joined_stops` ni LONG BUILD.
- Référence : OpexAI `estim_unifie=31`, route seule,
  `road100_site_first=1`, `road100_solo_pax=1`, autres variantes
  ROAD100 à 0. Variante : **seul** `road100_pax_portfolio=1`.
- AAAHogEx-115 : désactiver train, tram, bateau et avion via ses
  quatre réglages `disable_veh_*`. Même carte, même bundle, même
  graine et mêmes règles simulées, 1v1 apparié.
- Prévision uniquement **avant** chantier : production native de
  chaque tuile productrice, union sans chevauchement des zones
  racines/satellites/autres gares Opex, terrain et voirie déjà
  raccordée, station_spread et géométrie DT, cash et coûts réels.
  Le stock `waiting` ou le profit après construction ne servent
  jamais à noter un projet encore non bâti.
- Maximum 12 sites géographiques examinés par extrémité, 4 AITest
  stations au total, 2 satellites par extrémité ; recherche bornée
  à 85k opcodes par prévisualisation. AITest `STATION_NEW` prouve
  le terrain mais **pas** la jonction à un StationID qui n'existe
  pas encore ; la jonction est refaite au chantier.
- Le bonus de classement éventuel se limite à la moitié du gain
  économique projeté sur l'union ; il n'alimente jamais la caisse,
  le `profit_year`, `candidate.monthly`, le nombre de bus achetés
  sur les quais racines ou une garantie de recettes.
- Après pose des racines : revalidation des tuiles, vrais StationID,
  connectivité aller-retour, coût payé et couverture réellement
  marginale. Ne conserver aucun satellite invalide ni aucune
  station orpheline après rollback. Dépôt, bus et ordres A0/B0
  restent soumis aux gardes historiques.

## Portes et critères de sortie

1. Tests Squirrel réels (pas seulement regex), tests ciblés,
   suite complète, projection OFF exacte, `git diff --check`.
2. Smoke 1×1 ROAD-only apparié : parties saines, au moins un
   satellite correctement joint et connecté, production marginale
   positive, aucun cash/StationID orphelin. Aucun verdict de gain
   statistique sur une seule graine.
3. Seulement si exposition physique : **5 graines × 5 ans**,
   mêmes bundles OFF/ON. Mesurer stations/satellites effectivement
   construits, véhicules, voyageurs livrés, `LINE_REVENUE` réelle,
   `profit_year`/caisse/valeur, dépenses d'opcodes, refus et congestion.
   Exposition robuste souhaitée : satellites effectivement joints
   sur au moins 3 graines sur 5, avec recettes PAX observées.
4. Porte **A40×5** uniquement si signal crédible et non-érosion :
   gain moyen `profit_year` ≥ +4 %, Wilcoxon p < 0,05,
   perte de valeur ≤5 %, et profits annuels antérieurs non érodés.
   Une éventuelle porte B est distincte et après A. Ne jamais
   adopter uniquement au vu du score proxy ou d'un smoke sain.

Le but final reste la parité cumulative de profits réels avec AAA
sur les cinq horizons **1, 2, 3, 4, 5 ans**. Statut au lancement :
**0/5 horizons démontrés atteints**, chantier ROAD100 ouvert.

## Observations de moteur du 28/10/2026

- **V20** `road100_pax_portfolio_v20_seed42_roadonly_1x1_20261028` :
  2/2 parties saines, mais `NO_SATELLITE` (33 producteurs, 0 site,
  0 AITest, aucune construction satellite) ; `profit_year` Opex
  18 881 contre AAA ROAD seule 93 624 £/an ; ON−OFF −3 642 £/an.
- **V20b** `road100_pax_portfolio_v20b_ring_roadonly_seed42_1x1_20261028` :
  2/2 parties saines, balayage script coûteux (`OPCAP` ~74k opcodes),
  0 satellite ; ON−OFF −1 436 £/an.
- **V20c** `road100_pax_portfolio_v20c_exposure_5x1_20261028` :
  5 graines appariées, Opex 16 002 contre AAA 134 020 £/an à un an
  (11,94 % en ratio de moyennes, 0/5 victoires), ON−OFF moyen
  −1 599 £/an (1 V, 3 D, 1 E ; p=0,625) ; aucun satellite construit.
  Seed100 preview positif mais chantier des racines rejeté `BSTOP` ;
  seed999/2026 refus `OPCAP` ; seed42 aucun axe routier à 6–9 cases.
- **V20d** `road100_pax_portfolio_v20d_native_roadonly_seed100_1x1_20261028` :
  premier satellite physiquement joint : `phase=build reason=OK
  joined=2 marginal_a=6 marginal_b=0 cash_cost=300 monthly=37
  ops=30511` ; la prévisualisation emploie une valuation native de la
  voirie, `spread=12 coverage=3`, 46–55k opcodes sur ce pilote.
  La ligne PAX racine a été construite avec deux satellites du même
  StationID ; `profit_year` Opex 12 171 contre AAA 96 352 £/an
  (12,63 %), ON−OFF +206 £/an sur une graine, statut moteur
  `stagnation_suspect`. Ce résultat ne prouve pas un gain économique.

Les cinq appels `Valuate` ROAD100 antérieurs et le nouvel appel natif
`roads.Valuate(AIRoad.IsRoadTile)` sont inventoriés dans le test V262,
sans modifier l'inventaire historique suivi. Les tests ciblés ROAD100,
V262 et la projection OFF exacte passent. Les échecs de contrat rencontrés
dans la suite complète ont été corrigés sans baisser les assertions :
quatre comptages `AddSetting` mis à 100 (18 options ROAD100 OFF), et
rollback étendu aux satellites tout en conservant l'ordre arrêt/vente.

### V20d : qualification diagnostique 5 graines × 5 ans terminée

Campagne `road100_pax_portfolio_v20d_exposure_5x5_20261028`, bundle
`09ec8219b2db7bb0b692b1be3ef4e15edec52fa6f4a45121a15b51b669820c24`,
10/10 parties saines (mêmes cartes/graines, AAA strictement ROUTE seule).
Rapports annuels appariés séparés :
`results/road100_pax_portfolio_v20d_exposure_5x5_summary.md` (ON)
et `results/road100_pax_portfolio_v20d_reference_5x5_summary.md` (OFF).

| Horizon | `profit_year` Opex ON £/an | AAA ON £/an | ratio agrégé ON | Opex OFF £/an | ON − OFF £/an | Victoires Opex/AAA |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 14 428 | 138 096 | 10,4 % | 16 002 | −1 574 | 0/5 |
| 2 | 36 370 | 590 097 | 6,2 % | 40 304 | −3 934 | 0/5 |
| 3 | 35 856 | 1 155 780 | 3,1 % | 47 428 | −11 572 | 0/5 |
| 4 | 44 617 | 1 829 337 | 2,4 % | 48 015 | −3 398 | 0/5 |
| 5 | 41 241 | 2 141 502 | 1,9 % | 52 917 | −11 676 | 0/5 |

L'exposition **réelle** est établie sur les cinq graines : au moins
une ligne PAX possède des quais joints `reason=OK joined>=1`, et
des `LINE_REVENUE` suivantes (âge 1 ou 2) déclarent `n_stops_a/b>1`.
Exemples : seed100 (1970, deux satellites, +6 PASS/mois, 300 £ payés,
ligne0 `real_rev=11191` pour l'exercice déclaré 1971), seed42 (un
satellite, +5 PASS/mois, 150 £, `real_rev=10236` déclaré 1971),
seed999 (un satellite, +15 PASS/mois, 150 £), seed7 (1971, un
satellite, +10 PASS/mois) et seed2026 (1971, un satellite,
+2 PASS/mois). Les recettes totales de ligne ne peuvent pas être
attribuées causalement au seul satellite sans contrôle physique
comparatif OFF ; le seul critère de décision reste `profit_year`.

À cinq ans ON : ~19 véhicules routiers, ~19 gares, ~9 lignes,
283 252 £ en caisse, contre AAA ~489 véhicules, ~94 gares,
~51 lignes et 2 053 936 £ en caisse (moyennes appariées).
Le bilan V20d est négatif : −22,1 % du `profit_year` d'Opex par
rapport à OFF à cinq ans, 1/5 victoires ON−OFF, Wilcoxon p=0,1875,
valeur compagnie ON/OFF −18,6 %. **Pas de porte A40×5**, aucun
changement de défaut, ROAD100 toujours 0/5.

### V20e : itération protectrice à mesurer

Le code en cours retire le bonus de rang accordé au bénéfice marginal
non construit (le `candidate.ratio` des racines ne change plus),
et n'évite un deuxième preview coûteux qu'en cas d'identité exacte
des sites, fronts et du type de route entre génération et chantier.
La construction revalide toujours en moteur les StationIDs, AITest,
couvertures marginales, connexions et coûts avant de créditer le
moindre satellite. Réglage maintenu à zéro par défaut. L'objectif
de cette variante est de supprimer l'érosion du classement et les
opcodes redondants, **pas** d'inventer des profits.
