# Choix des avions : AAAHogEx et OpexAI (2026-10-02)

Analyse statique. Aucune partie lancée, aucun fichier sous `ai/` modifié. Le
script `sweeps/analyse_air_engine_choice.py` lit la télémétrie de ligne déjà
enregistrée. Il s'applique tel quel à un duel ultérieur C115 contre C121 dès
que son JSON de campagne a le même champ `line_telemetry.snapshots[]`.

**Statut des deux duels mesurés.** **Vérifié** `docs/46_aerien_aaahogex_vs_opexai_20260929.md:15-16` :
ils sont antérieurs au défaut C115. Le manifeste
`results/lineprofit_default_5x6_20260926.manifest.json` fige
`air_route_plane_selection=1`, `c72_plane_choice=0`, `v92_air_service_choice=0`,
`air_full_load=0`, et ne contient pas `c115_air_c100_capital_replay`. Le duel du
27 septembre ajoute seulement `probe_cost=1` sur OpexAI. La compagnie AAAHogEx
de ces parties reste une observation valable. La compagnie OpexAI est
historique : c'est le choix C68 (profit annuel, un avion), pas le défaut C115
du worktree `c68d50a`. Les formules C115 et C121 ci-dessous viennent du code
courant ; leurs flottes réalisées par distance ne sont pas dans ces fichiers.

Carte des deux duels : **Vérifié** dans les deux manifestes,
`configuration.parsed.game_creation`, `map_x=map_y=8` donc 256 tuiles,
`starting_year=1970`, inflation désactivée, `number_towns=3`,
`industry_density=4`, `town_growth_rate=2`, graines 42, 100, 999, 1234, 5678,
six ans. La distance de l'analyseur est le Manhattan des tuiles d'aéroport.
Les deux IA, elles, scorent une distance ajustée de la diagonale
(**Vérifié** `ai/OpexAI/air_coverage.nut:54-61` et
`ai/AAAHogEx-115/air.nut:290-298`).

## Verdict

L'hypothèse « la plus grosse différence est le choix de l'avion » ne tient pas
comme explication principale du profit par avion.

Sur le duel du 26 septembre, lignes aériennes d'au moins un an, la moyenne de
profit par avion pondérée par les appareils est 18 124 £ chez OpexAI et
57 282 £ chez AAAHogEx, soit un écart de 39 158 £. La décomposition comptable
de cet écart (**Vérifié**, identité résiduelle 0 dans la sortie de
`decompose_profit_gap`) se répartit ainsi :

| Partie de l'écart de 39 158 £ | Montant | Part |
|---|---:|---:|
| Même signature de capacité, taux différents | 19 742 £ | 50 % |
| Signatures qu'une seule IA utilise | 13 841 £ | 35 % |
| Mix parmi les signatures communes, valorisé au taux Opex | 5 575 £ | 14 % |

Le duel du 27 septembre donne 40 170 £ d'écart : 43 % à signature égale,
53 % hors support, 4 % de mix commun.

À signature égale et tranche de Manhattan égale, AAAHogEx a la médiane la plus
haute dans 9 cellules sur 10 (26 septembre ; 99,7 % du poids en avions) et
dans 11 sur 11 (27 septembre). La cellule contraire est un Darwin 300 avec un
seul avion AAA. Le choix de l'appareil ne suffit donc pas : le même avion, sur
une distance voisine, rapporte encore beaucoup plus chez AAAHogEx.

Le Manhattan exact, demandé comme test clé, va dans le même sens (7 cellules
sur 7 le 26 septembre, 6 sur 7 le 27) mais ne couvre que 3 à 6 % des avions.
**Vérifié** comme sens, **insuffisant** comme couverture. La tranche est le
comparateur qui couvre 35 à 45 % des avions.

## 1. Ce que mesurent les deux JSON

Règle de l'analyseur : ligne `mode=air`, au moins un véhicule, même
`line_key_local` déjà présent en décembre de l'année précédente, dans le même
`duel_policy_id`, le même bras, la même graine et la même répétition. L'année
1970 n'a donc aucune ligne mûre. Le modèle est `capacité / véhicules` quand
chaque cargo se divise exactement, sinon `mixed`. Le profit par avion d'une
ligne est `profit_this_year_gbp / vehicles`. Une valeur absente reste absente.

Médianes de profit par avion, tous modèles confondus, qui retrouvent le
document du 29 septembre (14,8 k£ et 49,2 k£,
**Vérifié** `docs/46_aerien_aaahogex_vs_opexai_20260929.md:28`) :

| Duel | OpexAI, médiane | AAAHogEx, médiane | Lignes mûres |
|---|---:|---:|---:|
| 26 septembre | 14 774 £ (n=962) | 49 206 £ (n=377) | 1 339 |
| 27 septembre | 15 264 £ (n=907) | 50 912 £ (n=389) | 1 296 |

### Répartition des avions, duel du 26 septembre, années 1971-1975 cumulées

Les noms viennent de `results/diag_nuit_air_solo_probe_c82.json`, bloc
`latest_factors` (lignes 245-293 de ce JSON). L'identifiant et la capacité
viennent des mois du JSONL `results/lineprofit_default_5x6_20260926.jsonl` où
un seul `air_engine_counts` augmente et où le delta de
`air_capacities_by_cargo` est divisible par cette augmentation. Recalcul du
2026-10-02. Une seconde signature sans passagers est le même EngineID observé
sur un mois de seul courrier : c'est un refit, pas un second nom inventé.

| Signature | Libellé publié | Avions Opex | Médiane Opex | Avions AAA | Médiane AAA |
|---|---|---:|---:|---:|---:|
| 0:90\|2:10 | 217 FFP_Dart | 634 | 12 050 £ | 0 | — |
| 0:220\|2:40 | 223 Bakewell_Luckett_LB-10 | 228 | 25 054 £ | 272 | 63 545 £ |
| 0:110\|2:15 | 227 Darwin_200 | 147 | 18 131 £ | 77 | 40 400 £ |
| 0:300\|2:50 | 228 Darwin_300 | 60 | 33 985 £ | 53 | 56 921 £ |
| 0:100\|2:20 | 218 Yate_Haugan | 2 | 25 990 £ | 103 | 43 416 £ |
| 0:200\|2:30 | 220, nom non publié | 0 | — | 72 | 82 613 £ |
| 0:170\|2:35 | 226, nom non publié | 0 | — | 67 | 46 238 £ |
| refits sans passagers | courrier seul | 0 | — | 228 | 4 772 à 93 055 £ selon signature |

OpexAI n'a aucune ligne courrier seul dans ces deux duels. AAAHogEx en a 228
avions sur 892 le 26 septembre, soit 26 % de sa flotte aérienne mûre. Le 217
représente 55 % des avions Opex (540 lignes) et zéro ligne mûre AAA.

Même tableau de fond le 27 septembre : 572 avions 217 chez Opex (médiane
12 267 £), 0 chez AAA ; 195 contre 264 avions 223, médianes 26 936 £ et
74 576 £.

### À modèle égal et distance voisine

Tranches de Manhattan : [0,96), [96,128), [128,160), [160,192), [192, ∞).
Duel du 26 septembre, cellules où les deux IA ont le modèle :

| Modèle | Tranche | Avions Opex | Médiane Opex | Avions AAA | Médiane AAA |
|---|---|---:|---:|---:|---:|
| 223 LB-10 | [128,160) | 18 | 23 046 £ | 6 | 57 126 £ |
| 223 LB-10 | [160,192) | 68 | 25 097 £ | 59 | 55 915 £ |
| 223 LB-10 | [192, ∞) | 142 | 25 297 £ | 201 | 76 621 £ |
| 227 Darwin 200 | [160,192) | 34 | 19 443 £ | 19 | 31 525 £ |
| 227 Darwin 200 | [192, ∞) | 113 | 18 131 £ | 45 | 49 684 £ |
| 228 Darwin 300 | [192, ∞) | 25 | 44 051 £ | 52 | 58 484 £ |
| 228 Darwin 300 | [128,160) | 20 | 24 600 £ | 1 | 17 292 £ |
| 218 Yate Haugan | [128,160) | 2 | 25 990 £ | 4 | 62 414 £ |

Le LB-10 à plus de 192 tuiles est la cellule lourde : 142 avions Opex et 201
avions AAA, médianes 25 297 £ et 76 621 £. Le choix du 223 ne produit pas le
profit AAA.

Manhattan exact, mêmes duels, cellules de au moins un avion de chaque côté.
Sept cellules le 26 septembre, toutes à l'avantage d'AAA, écart médian des
écarts de médianes 17 204 £. La plus grosse en avions est le 223 à 185 tuiles
(14 contre 6, 28 821 £ contre 35 172 £) et le 223 à 268 tuiles (4 contre 16,
16 851 £ contre 97 306 £). Le 27 septembre, six cellules sur sept à
l'avantage d'AAA ; la cellule inverse est le 223 à 232 tuiles (4 avions Opex,
médiane 47 549 £, contre 9 avions AAA, 26 066 £).

### Les autres différences, mêmes lignes mûres

Moyenne des instantanés graine × année, puis l'année 1975 seule. Une ligne
compte pour chacun de ses deux aéroports : le 26 septembre 1975, 392 lignes
Opex et 23,2 aéroports par partie donnent 2 × 392 / (5 × 23,2) ≈ 6,8 lignes
par aéroport. C'est le 6,79 calculé. Le maximum observé est 12. AAAHogEx est
à 1,0 chaque année, maximum 1.

| 1975, duel du 26 septembre | OpexAI | AAAHogEx |
|---|---:|---:|
| Avions par ligne (moyenne) | 1,16 | 2,45 |
| Lignes par aéroport (moyenne / max) | 6,79 / 12 | 1,0 / 1 |
| Aéroports par ville | 1,03 | 1,20 |
| Villes desservies par partie | 22,6 | 32,2 |
| Aéroports par partie | 23,2 | 38,8 |
| Note passagers, minimum des deux bouts (médiane) | 162 | 103 |
| Attente passagers, maximum des deux bouts (médiane) | 9 | 149 |
| Avions courrier seul | 0 | 47 |

Cumul 1971-1975 : 1,20 avion par ligne Opex contre 2,37 AAA (26 septembre) et
1,13 contre 2,42 (27 septembre). **Vérifié** comme proche de 1,2 contre 2,4
dans `docs/46_aerien_aaahogex_vs_opexai_20260929.md:29`. Le document du 29
septembre donne 7,8 lignes par aéroport en 1975 : même phénomène de hub, agrégat
légèrement différent du 6,79 ci-dessus.

En 1971 les deux flottes sont encore des avions de 110 à 300 places et le
profit médian Opex est 54 432 £. En 1975, 70 % des avions Opex sont des 217
et la médiane est tombée à 12 169 £. AAA reste entre 41 000 et 88 000 £ de
médiane selon l'année, avec un mix qui passe du 223 et du 220 (1971) au 218
(66 avions en 1975, 28 %).

## 2. Formules de choix

### AAAHogEx

**Vérifié**, sources dans `ai/AAAHogEx-115/` de l'arbre principal (absent du
worktree, lu sur place).

Entrées gardées pour chaque moteur aérien qui peut être refitté au cargo
(`estimator.nut:661-663`) :

- gros avion retiré si l'un des deux aéroports de la route existante ne le
  porte pas (`estimator.nut:682-691`, traits `supportBigPlane` dans
  `air.nut:10-72`) ;
- autonomie : `GetMaximumOrderDistance == 0` signifie illimitée, sinon la
  distance d'ordre doit être strictement inférieure (`estimator.nut:726-734`) ;
- capacité : refit réel si un dépôt de la classe existe, sinon
  `GetCapacity × 115/100` pour les passagers et `GetCapacity / 2` sinon
  (`route.nut:1543-1598`) ;
- vitesse de croisière = vitesse maximale, sans malus de fiabilité hors
  pannes (`estimator.nut:779-780`) ;
- distance de vol d'une route existante = diagonale ajustée
  (`air.nut:290-298`), plus 30 tuiles d'atterrissage, plus 50 si les pannes
  sont actives (`estimator.nut:844-848`) ;
- jours = `max(1, distance × 664 / vitesse / 24 / facteur de jour)`
  (`utils.nut:1225-1227`) ;
- chargement aérien 74 unités par temps, moitié pour le courrier
  (`estimator.nut:819-834`) ;
- note de gare = `max((min(255, vitesse) − 85) / 4, 0)` plus 26 si la
  compagnie est riche, puis +170 dans l'estimation (`utils.nut:1267-1271`,
  `estimator.nut:755`) ;
- courrier : capacité réelle mesurée en construisant l'avion, ou
  `GetCapacity / 8` si la mesure échoue (`air.nut:136-146`), ajoutée dans les
  deux sens (`estimator.nut:298-306`) ;
- coût d'infrastructure nul sans maintenance d'infrastructure
  (`air.nut:275-279`) ;
- temps de chantier aérien fixe de 300 jours plus 3 jours par véhicule
  (`estimator.nut:512-513` et `estimator.nut:318`,
  `buildingTimePerVehicle = 3` à `estimator.nut:483`) ;
- coût de construction = prix de trait d'aéroport gonflé × 2 × 2, plus le
  bâtiment passagers/courrier (`estimator.nut:587-589`).

Critère (`estimator.nut:264-315` puis `CalculateIncome` `estimator.nut:54-65`
et `GetValue` `estimator.nut:77-95`). Production notée plafonnée par la
capacité de route. Nombre de véhicules déduit de cette production, borné par
la place de flotte et par `EstimateMaxVehicles` (`route.nut:2374-2379`).
Temps d'attente pour remplir l'avion ajouté au cycle. Revenu d'un voyage
passagers aller-retour = tarif × capacité dans les deux sens, plus la soute
courrier × tarif courrier dans les deux sens. Revenu annualisé, multiplié par
`futureIncomeRate/100` (100 hors inflation, `main.nut:4470-4472`), moins le
coût d'exploitation. L'amortissement n'entre que si les pannes sont actives
(`estimator.nut:42-51`). La valeur dépend de la ressource rare
(`main.nut:781-806` et `main.nut:828-836`) : compagnie pauvre ou inflation →
ROI, avec le manque à gagner du premier voyage ajouté au capital
(`estimator.nut:81-88`) ; compagnie riche et un mode avec au moins 100 places
libres et moins de 70 % du plafond → revenu par temps de chantier ; sinon
revenu par véhicule. Tri décroissant sur cette valeur (`estimator.nut:948-950`).
Pas de départage explicite en cas d'égalité.

Moments où le choix est refait. `ChooseEngineSet` (`route.nut:2295-2324`) à
chaque `_CheckBuildVehicle` (`route.nut:2668-2674`) si le dernier jeu manque,
est invalide, a plus de 1 500 jours, ou si le moteur n'est plus constructible.
`CheckReduce` invalide en plus un jeu de plus de 10 ans lorsqu'un dessin a
moins de 2 ans (`route.nut:1700-1703`). Un changement de moteur pose
`markSendDepot` et envoie au dépôt les véhicules qui ne portent plus ce moteur
(`route.nut:2319` et `route.nut:2729-2746`).

Ouverture et renfort, distincts du choix du moteur. `BuildVehicleFirst`
construit un avion puis le clone (`route.nut:2990-2997`). Pour une route
aérienne aller-retour, le clone dont le compte est impair part du hangar
opposé (`route.nut:2232-2236`). Le chemin qui appelle `BuildVehicleFirst`
lorsque aucun véhicule du moteur choisi n'existe clone encore une fois si la
route n'est pas un transfert de ville (`route.nut:2859-2871`). Le code peut
donc poser trois avions à l'ouverture ; la télémétrie ne dit pas combien
partent réellement. Ensuite, des clones supplémentaires suivent l'attente et
la note, au plus 4 hors transfert de ville (`route.nut:2906-2915`).
Chargement complet aux deux bouts : `air.nut:201`, `route.nut:1871`,
`route.nut:2137`, `route.nut:2163`. Un aéroport ne prend pas une seconde ligne
aller-retour du même cargo (`air.nut:742-745`). La production estimée ne
divise pas par le nombre de compagnies adverses : `otherCompanies` vaut
toujours 0 (`place.nut:1942-1950`).

### OpexAI, défaut livré C115

**Vérifié** dans le worktree. Défauts : `c115_air_c100_capital_replay=1` aux
quatre difficultés (`ai/OpexAI/info.nut:464-469`),
`air_route_plane_selection=1` (`info.nut:947-951`), chargés
`settings.nut:284` et par `policy_air` (`settings.nut:53-55`).
`v92_air_service_choice=0` (`info.nut:275-279`). `FLEET_PORTFOLIO` suit
`policy_air`, donc le plafond d'avions du calcul économique de création est 1
(`air_route_economics.nut:94-98`).

`OpexAirChooseRoutePlane` (`air_engine_choice.nut:438-492`) saute le mémo
lorsque C115 est actif et que `c116_air_marginal_capital` est inactif, puis
appelle `OpexAirChooseRoutePlaneFull`. La garde `air_engine_choice.nut:1871-1882`
délègue à `OpexC115ChooseRoutePlane` si C72, C82, C85, C99-C114 et C116 sont
inactifs. C'est le chemin du défaut.

`OpexC115ChooseRoutePlane` (`air_engine_choice.nut:1417-1459`) :

1. recalcule l'argmax C68 par `OpexC104BestAirEngine` en mode 0, économie
   historique (`air_engine_choice.nut:638-668`) ;
2. si `K_dec` est au moins égal au capital de cette décision, garde cet avion
   et cette économie C68 ;
3. sinon prend l'argmax en mode 1 (`forceC100RankReplay`) et retourne
   l'économie replay, pas seulement le classement ;
4. si le replay est vide, revient au C68.

Critère des deux argmax : `profitAnnual`, puis ROI en cas d'égalité
(`air_engine_choice.nut:661-664`). Pas de départage par identifiant. Filtre
d'autonomie : `maxOrderDistance > 0` et distance supérieure
(`air_engine_choice.nut:645`). La liste est celle du type d'aéroport
(`catalog.nut:656-686`) : grands aéroports acceptent petit et gros avion,
petits aéroports le petit avion seulement, hélicoptères exclus. La capacité
stockée est `AIEngine.GetCapacity`, la soute reste −1 tant qu'elle n'est pas
observée (`catalog.nut:676-680`).

Économie historique (`air_route_economics.nut:121-135`) : transporté =
`min(demande mensuelle × note(intervalle) / 100, avions × capacité)`. Revenu
= 12 × transporté × tarif. Le tarif (`air_economics_c121.nut:4-17`) est le
revenu passager plus 15 % du revenu courrier, fois
`air_pax_revenue_calibration_pct` (défaut 104, `info.nut:1194-1198`), sauf si
V92 connaît la soute. Coûts : exploitation × avions, entretien d'aéroport si
la maintenance d'infrastructure est active, amortissement prix/20 ans plus
aéroport. La distance passée au choix est `OpexFlightDistance` des ancres,
pas le Manhattan des centres-ville (`air_planning.nut:771-782` et
`air_coverage.nut:54-61`).

Création : `air_planning.nut:839-848` appelle `OpexAirChooseRoutePlane` tant
que `C121_AIR_ECONOMICS` est faux. Les autres bras de planification (lignes
1261, 1532, 1711) ont le même aiguillage. Renfort : `OpexAirAddPlane`
(`air_fleet.nut:299-302`) clone le moteur déjà en ligne. Il ne refait le choix
que si V92 est actif (`air_fleet.nut:326`). Le remplacement après crash
réutilise `refleetEngine` mémorisé (`air_fleet.nut:365-372`). `air_full_load`
vaut 0 (`info.nut:876-882`, lu `settings.nut:414`) ; C121_AAA_LINE le forcerait
à 1 seulement si ce drapeau est lui-même actif (`settings.nut:416`).

Ce que C115 choisit selon la distance : **non mesuré** sur une flotte C115.
Le code ne contient pas de seuil de distance autre que l'autonomie et le
modèle de trajet. **Hypothèse**, reprise de
`docs/46_aerien_aaahogex_vs_opexai_20260929.md:69-73` et non revérifiée ici :
le replay allonge les trajets, la capacité devient limitante, et le 223 peut
battre le 217. Le duel historique, lui, montre le résultat C68 : le 217 finit
à 70 % de la flotte 1975.

### OpexAI, socle C121

**Vérifié**, et ce n'est pas le défaut. `C121_AIR_ECONOMICS` doit être actif.
`OpexC121CatalogChoice` (`air_catalog_c121.nut:109-213`) renvoie le cache tant
que ni le moteur, ni les villes, ni les gares, ni l'apprentissage, ni l'âge
(365 jours), ni les entrées (distance, demande V93, prix et entretien
d'aéroport) n'ont changé. Sinon il appelle `OpexC121ChooseRoutePlane`
(`air_economics_c121.nut:1244-1392`).

Filtres : moteur valide et constructible, `OpexC118EngineFitsPlan`,
`OpexAirPlaneInRange`. Élagage par un score plafond à un avion, puis évaluation
de la flotte d'ouverture N = 2 si `c121_aaa_line`, sinon N = 1
(`air_economics_c121.nut:1305`). Critère : `decisionScore`, puis
`decisionProfitAnnual`, puis plus petit `plane.id`
(`air_economics_c121.nut:1323-1329`). Le score est
`profitAnnual × 1000 / capital réellement immobilisé`
(`air_economics_c121.nut:777-798`). `K_dec` n'élargit pas ce capital pendant le
scan moteur, sauf si un drapeau portfolio-depth ou portfolio-split est actif.
Ces drapeaux sont rejetés (`docs/taches.md:149`) et ne changent pas l'avion
déjà choisi, seulement l'économie envoyée au portefeuille. Après le gagnant,
une croisière au profit maximum sert au classement ; l'économie construite
reste celle de N avions d'ouverture (`air_economics_c121.nut:1348-1392`).

Entrées du score, au-delà de C115 : demande brute des deux villes, soute
observée (démarrage à froid passagers seuls), revenu cargo à la distance de
paiement, temps de trajet C121, note de vitesse, statue, partage de piste,
part de route face au service déjà en hub, cannibalisation, facteur de
réalisation, prix, exploitation, âge maximum, prix et entretien d'aéroport.
Appel : `air_planning.nut:839-842` lorsque l'économie C121 est active.

Ce que C121 choisit selon la distance : **non mesuré**. Le duel en cours n'est
pas lu ici ; son JSON final passera dans le même analyseur.

## 3. Modèles de 1970 à 1980

**Vérifié** comme comptage, pas comme fiche technique.
`results/catalogue_churn.json`, sonde CatalogProbe, graine 42, note en tête de
fichier : 13 moteurs aériens en 1970, aéroports LARGE et HELIPORT ; 12 ou 13
jusqu'en 1979 ; 14 en 1980, avec METROPOLITAN en plus des héliports. Cette
sonde n'est pas le manifeste des duels 5×6. **Hypothèse** que le nombre de
moteurs constructibles y est le même. Les caractéristiques absentes de cette
sonde, et absentes des journaux relus : vitesse, coût d'exploitation, autonomie,
date d'introduction, prix sauf deux.

Prix publiés et non re-extraits d'une sauvegarde dans cette session :
**Vérifié** comme affirmation de
`docs/46_aerien_aaahogex_vs_opexai_20260929.md:40-41` : 223, 220 places,
39 k£ ; 217, 90 places, 33 k£. Les places concordent avec les signatures
0:220|2:40 et 0:90|2:10.

Noms et capacités observées dans les duels, sources ci-dessus. Identifiants
sans nom publié : 216 (0:65|2:8), 220 (0:200|2:30 et courrier 2:230), 226
(0:170|2:35 et courrier 2:205). Le 233 est décrit comme gros avion,
`plane_type=3`, capacité 260, toujours dominé
(**Vérifié** `docs/journaux/journal_2026-09-08.md:148-156`) ; le JSONL ne lui
associe qu'un mois courrier 2:290. La signature rare 0:260|2:30 (3 avions AAA)
n'est pas identifiée à ce moteur. **Hypothèse** si on les confondait.

Le texte Coleman Count de `docs/03_decoupage_pax_candidates.md` est une
synthèse générique de 1950, pas un catalogue 1970 mesuré. Il n'est pas utilisé
comme source de vitesse ou de prix.

## 4. Contrefactuel statique

`aaa_rank_bidirectional_passenger` et `aaa_formula_counterfactual` dans
`sweeps/analyse_air_engine_choice.py` transcrivent la branche aller-retour
passagers d'AAAHogEx : filtre gros avion, autonomie stricte, note de vitesse,
distance diagonale plus 30, jours, chargement 74, attente de la branche
`intervalle <= 10`, revenu cabine et soute dans les deux sens, ROI ou temps de
chantier ou revenu par véhicule. **Estimation de modèle.** Le test unitaire
verrouille un moteur fictif (vitesse 400, 80 places, production 255, distance
48) : 5 jours de croisière, attente 4, 2 véhicules, revenu de ligne 730 000,
valeur « par véhicule » 365 000, ROI 27 037. Un coût d'exploitation qui rend
le revenu négatif, un gros avion sur un petit aéroport, et une autonomie trop
courte sont refusés. La branche d'intervalle supérieur à 10 n'est pas
réécrite.

Sur les routes réelles d'OpexAI, la fonction retourne `incomplete` : 962 routes
avec distance le 26 septembre, 907 le 27. Aucun gagnant n'est calculé. Il
manque, et ces manques sont la raison de ne pas inventer un avion :

- vitesse, coût d'exploitation, autonomie, gros ou petit avion, pour tout le
  catalogue ; prix seulement pour 217 et 223, et encore comme citation du
  document du 29 septembre ;
- `AICargo.GetCargoIncome` selon la distance et les jours ;
- la production mensuelle au moment du choix, absente de l'instantané de
  décembre ;
- lequel des trois dénominateurs AAA était actif (ROI, chantier, véhicule) :
  l'inflation du manifeste est fausse, la richesse de la compagnie au moment
  de chaque choix ne l'est pas.

**Hypothèse** interdite ici : désigner le 223, le 220 ou le 218 comme
l'avion qu'AAAHogEx aurait acheté sur une route Opex. Le code de la formule
est vérifié ; son application numérique à ces routes ne l'est pas.

## 5. Part attribuable au choix de l'avion

Comptage **Vérifié** sur les deux JSON. Lecture causale **Hypothèse** : ce
sont des lignes déjà construites, pas un A/B, et les grandes villes portent
plus de lignes.

Le choix de l'avion, au sens « quelles signatures chaque IA aligne », se voit
dans deux lignes de la décomposition :

- le mix des signatures présentes des deux côtés, valorisé avec le profit
  qu'Opex obtient déjà sur chacune : 14 % le 26 septembre (5 575 £), 4 % le
  27 (1 660 £) ;
- les signatures exclusives : 35 % puis 53 %. Côté Opex, c'est surtout le 217
  (634 avions, moyenne pondérée 12 451 £ le 26 septembre), plus le 225, le
  216 et le 232. Côté AAA, 370 avions absents de la flotte Opex, moyenne
  pondérée 52 280 £ : le 220, le 226, et les refits courrier.

Le reste, 50 % puis 43 %, est le profit par avion à signature identique. Sur
le seul LB-10, la médiane Opex est 25 054 £ et celle d'AAA 63 545 £, sans
même tenir compte de la distance. À plus de 192 tuiles de Manhattan l'écart
de médianes est 51 325 £ pour 142 et 201 avions. Cette part-là ne vient pas
du modèle d'avion.

Ce qui accompagne cette part, sans qu'on puisse la leur attribuer au pourcent
près (**Hypothèse** de mécanisme, **Vérifié** comme co-occurrence) :

- avions par ligne, 1,16 contre 2,45 en 1975 ;
- point à point contre hubs, 1 ligne par aéroport contre 6,8 en moyenne et 12
  au maximum ;
- villes desservies, 32 contre 23 en 1975 ;
- attente et note : 149 passagers et note 103 chez AAA, 9 passagers et note
  162 chez Opex. L'attente élevée avec une seule ligne par aéroport est le
  motif attendu du chargement complet. Le chargement complet lui-même n'est
  pas un champ de la télémétrie.

`air_full_load` a déjà été mesuré en solo à −37 à −54 %
(**Vérifié** `docs/46_aerien_aaahogex_vs_opexai_20260929.md:79-81`).
`docs/taches.md:178` le laisse en examen, pas en duel. Il n'est pas reproposé
ci-dessous : avec 7 à 12 lignes sur le même aéroport, attendre le plein partage
les passagers entre les lignes. Le document du 29 septembre formule déjà cette
hypothèse.

## 6. Interventions

Au plus trois, chacune derrière un réglage nouveau, défaut 0, sans édition de
`OpexC115ChooseRoutePlane` ni d'`OpexAirChooseRoutePlaneFull`. C115 reste
protégé (**Vérifié** `docs/taches.md:19`). Formulations déjà fermées, relues
dans `docs/taches.md` et `info.nut`, et non reprises : `air_full_load` (C81),
`c106_air_marginal_physical_engine_choice` (défaut 0, `info.nut:401-404` ;
descentes 223→217 citées avec C123 dans
`docs/46_aerien_aaahogex_vs_opexai_20260929.md:72-73` ; `docs/taches.md` ne
nomme pas C123), C116 et C118 rejetées, C120 gelé (`docs/taches.md:175`),
C119 non adopté (`docs/taches.md:19`), variantes C121 decision-depth,
portfolio-depth, portfolio-split, stock-growth, two-aircraft, territoire et
bootstrap (`docs/taches.md:149`). `c121_aaa_line` (`info.nut:599-603`) couple
déjà deux avions et le chargement complet sous C121 : ce n'est pas un levier
isolé. `air_hub_max_routes` existe et plafonne à 4 ou 12 (`info.nut:1379-1386`) :
ce n'est pas l'exclusivité à une ligne.

La troisième place reste vide. Un nouveau classeur de moteurs serait le
chantier que la décomposition ne met pas en tête, et le duel C115 contre C121
en cours doit d'abord dire si le défaut actuel quitte le 217. Le greffer dans
C115 est exclu.

### 1. `air_one_passenger_route`, défaut 0

Une seule ligne aérienne passagers aller-retour par aéroport. Refuser la
seconde, sans changer le choix du moteur, sans chargement complet, sans second
avion à l'ouverture. Chemin nouveau, sélectionné seulement si le réglage vaut
1, à l'endroit où une paire d'aéroports est acceptée. Le code C115 n'est pas
édité.

Exposition attendue, lue par cet analyseur : lignes par aéroport du bras
variante vers 1, maximum bien en dessous de 12 ; villes et aéroports en hausse
si la construction se déplace ; signatures d'avions inchangées par rapport au
défaut du même arbre. Si les signatures bougent, l'essai n'est plus isolé.

Mesure : smoke 1 graine × 1 an, puis 5×6, puis 20×10 apparié contre le défaut
C115=1 du même arbre. Métrique primaire `profit_year`, effet utile 50 000 £/an,
garde de valeur 5 %, règle du dépôt. Rapporter en plus l'écart de `profit_year`
avec AAAHogEx et, sur la télémétrie, le profit par avion à signature égale.
Le ratio Opex/AAA n'adopte pas le réglage.

### 2. `air_mail_only_vehicle`, défaut 0

Sur une ligne passagers déjà ouverte, autoriser un véhicule supplémentaire
refitté courrier seul, du moteur déjà choisi, lorsque l'attente courrier le
justifie. Le classeur passager reste celui du défaut, C115 compris. Pas de
changement de `OpexAirFarePerPax`, donc pas une variante de C119.

Exposition : apparition de signatures sans cargo 0 (2:… ) sur le seul bras
variante. Le bras défaut de ces duels historiques en a zéro ; AAAHogEx en a
environ un quart de ses avions.

Même séquence smoke, 5×6, 20×10, même métrique `profit_year` et même écart
avec AAAHogEx en lecture secondaire. Arrêter après le 5×6 si aucune signature
courrier n'apparaît : le mécanisme n'est pas exposé.

## Fichiers

Analyseur et tests : `sweeps/analyse_air_engine_choice.py`,
`sweeps/test_analyse_air_engine_choice.py`. Commande, depuis la racine du
worktree : `PYTHONPATH=.:sweeps python3 -m unittest sweeps.test_analyse_air_engine_choice`.
Les deux JSON lus :
`results/lineprofit_default_5x6_20260926.json` et
`results/lineprofit_costprobe_5x6_20260927.json`, avec leurs manifestes pour
la taille de carte.
