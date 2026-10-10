# P0 — Rendement marginal réel des avions OpexAI (08/10/2026)

**Statut : diagnostic du modèle établi ; exposition comptable 20×5 établie ; mesures événementielles complémentaires et qualification causale consignées ci-dessous. Aucun changement de comportement ni défaut adopté.**

## 1. Sources, protocole et limites

- **Référence descriptive historique** : `results/chrono_opex_aaa_20x5_20261008_r1.{json,jsonl,manifest.json}`, `results/chrono_opex_aaa_20x5_20261008_r1.analysis.json`, `docs/chronologie_opex_aaahogex_20261008.md`. HEAD Git `cb23a172`, arbre historique *dirty*, bundle figé SHA256 `3d159220b53d40b39598fca051b3902f4156f8f0d42a5ab34f5431fc360bad8d`, manifeste SHA256 `362ef84b6d1883722e6c73cf2c3938fec23736a687fdaac6f835a3feaeccb83a`. **20 duels / 40 compagnies complets**, 200 snapshots de lignes en décembre et 2 400 checkpoints mensuels de comptes compagnie ; aucun journal `AILog` exploitable (logs moteur vides). Le rapport reproductible est produit par `python -X utf8 sweeps/analyse_air_marginal_p0.py` dans `results/air_marginal_p0_20x5_20261008_analysis.json`.
- **Lecteur de sauvegardes** : `sweeps/bench_1v1_5y_20seeds.py:853–988`. Une ligne Opex est reconstruite par paire de **stations physiques**, une ligne AAA par `AIGroup` lorsque renseigné. Les clés métier `lineId` NoAI ne sont pas disponibles dans la première télémétrie, mais la signature station + les identifiants de véhicules sont conservés. Il existe **un avion non attribué** (graine 999, décembre 1972, ID 195, ordres inexploitables). Les inventaires de lignes AAA et Opex ne sont donc pas symétriquement comparables.
- **Comptabilité** : `profit_this_year_gbp` est le profit **net des véhicules depuis le 1er janvier de l'année courante**, frais d'exploitation des avions déjà inclus, mais **hors coût d'acquisition, amortissement économique du nouvel avion et maintenance des aéroports**. Il ne s'additionne pas au `profit_year` roulant de compagnie. La recette brute et les dépenses d'exploitation par véhicule ne sont pas exposées par ce décodeur ; les stocks `max_waiting_cargo` et ratings sont des indicateurs instantanés/agrégés, non un débit de passagers transportés. Les checkpoints de décembre n'isolent pas la causalité.
- **Campagnes complémentaires** : `air_marginal_p0_monthly_3x5_20261008_r1` sur les graines 42,512,65537, télémétrie mensuelle passive ; `air_p0_veh3_r1` mêmes graines/code AIR avec par-appareil `vehicle_financials`, résultat terminal identique aux trois cas précédents. Les hashes de bundle des campagnes 3×5 diffèrent du banc historique : les trajectoires ne doivent **pas** être fusionnées comme si le code était identique. Les lignes d'AI et les sources locales contiennent des modifications concurrentes qui restent préservées.

## 2. Tableau annuel de rendement AIR — 20 graines, £ moyens par partie

| Décembre | Avions Opex | Lignes Opex | Profit AIR Opex* | Profit AIR / avion Opex* | Actif avion Opex | Avions AAA | Profit AIR AAA* | Profit AIR / avion AAA* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1970 (partiel) | 10,35 | 6,80 | 497 032 | 48 022 | 393 351 | 12,05 | 493 751 | 40 975 |
| 1971 | 35,15 | 25,30 | 1 371 950 | 39 031 | 1 266 736 | 23,50 | 1 311 892 | 55 825 |
| 1972 | 55,95 | 39,15 | 1 715 674 | 30 664 | 1 834 976 | 31,05 | 1 595 060 | 51 371 |
| **1973** | **75,65** | **45,50** | **1 675 881** | **22 153** | **2 304 501** | **38,25** | **2 030 552** | **53 086** |
| **1974** | **94,55** | **49,55** | **1 757 776** | **18 591** | **2 664 844** | **40,95** | **1 891 428** | **46 189** |

*Profits moteur `profit_this_year` depuis janvier (December YTD). Le ratio sur la flotte totale est une **productivité moyenne de stock à la date du snapshot**, **pas le profit marginal causal** de l'avion acheté. 1970 est partiel. L'« actif avion » est la valeur actuelle comptable, non le coût historique total d'achat. Côté AAA, les véhicules routiers et surtout les trains, ainsi que leurs éventuels rabattements, rendent la comparaison structurelle non expérimentale.*

**Date du décrochage** : décembre 1972→décembre 1973, Opex **+19,7 avions**, profit AIR courant **−39,8 k£**, pendant qu'AAA accroît son profit AIR de **+435,5 k£**. L'écart global `profit_year` Opex−AAA passe de **−65,9 k£** (décembre 1972) à **−728,4 k£** (décembre 1973), puis **−1 302,2 k£** (décembre 1974) ; Opex perd les **20/20** comparaisons finales. On ne dispose pas de points AIR trimestriels sur cette référence pour dater le premier mois précis de divergence de rendement. Le profit annuel de compagnie et le profit AIR YTD ne désignent **pas** la même fenêtre comptable.

## 3. Décomposition vérifiable de la variation 1972→1974

Partition exacte des snapshots de décembre par même paire de stations Opex :

| Catégorie Opex (moyenne/partie) | Δ profit AIR YTD décembre 1974 − décembre 1972 |
|---|---:|
| Lignes absentes en 1972 et présentes en 1974 | **+145,9 k£** |
| Lignes anciennes qui subsistent | **−93,9 k£** |
| Lignes anciennes disparues (profit initial retranché) | **−9,9 k£** |
| **Total** | **+42,1 k£** |

Pour les lignes anciennes demeurées présentes : **27,3 lignes renforcées**, +**27,55 avions nets** sur ces lignes, mais variation de profit agrégée de seulement **+17,2 k£** ; **13,05** de ces lignes par graine voient individuellement leur profit diminuer. Les **11,1 lignes restées à effectif constant** perdent **−101,5 k£** au total, **6,4** d'entre elles diminuant. Les lignes ayant moins d'avions complètent le bilan. Parmi les **218 lignes nouvelles** présentes en décembre 1974 à travers 20 graines, **32** sont à profit YTD négatif ; beaucoup peuvent être trop jeunes pour avoir atteint leur régime de croisière.

Pour AAA sur la même fenêtre : **+9,9 avions** et **+296,4 k£** de profit AIR YTD, décomposés en **+168,1 k£** pour les nouvelles lignes et **+128,3 k£** sur les anciennes restantes. Les nouvelles lignes Opex n'ont donc pas créé un surplus suffisant pour compenser l'érosion des anciennes, tandis qu'AAA combine nettement mieux rétention de revenu sur lignes existantes et nouvelles capacités. La valeur comptable de la flotte AIR Opex passe de **1,835 M£ à 2,665 M£** (**+830 k£**, sans compter les aéroports).

**Attention** : aucun des termes précédents n'est une estimation identifiée de l'effet de l'achat. Âge, concurrence, variations de demande et additions simultanées varient ; une ligne à effectif constant peut perdre du revenu sans que son concurrent soit une nouvelle ligne Opex.

### 3.1. Renforts isolés dans les snapshots mensuels, par graine, ligne et N

La seconde collecte 3×5 (`results/air_p0_veh3_r1.jsonl`) extrait les **profits par identifiant d'avion** sans code Squirrel supplémentaire ; `results/air_marginal_p0_vehicle3_20261008_analysis.json` contient les détails des avions survivants, des nouveaux et **tous les événements** analysables. Une fenêtre est qualifiée « renfort isolé » si un unique nouvel ID arrive sur une paire de stations inchangée, avec trois mois de profit avant et trois mois après dans **la même année**, sans autre changement de flotte sur cette ligne. Il ne s'agit **pas** d'un contrôle sur la demande globale ni sur les autres lignes, et le bénéfice du nouvel appareil observé inclut éventuellement du trafic repris aux anciens.

| Graine | Renforts isolés qualifiés | Ancien(s) avion(s) : Δ profit 3 mois négatif | Ligne entière : Δ profit 3 mois négatif |
|---|---:|---:|---:|
| 42 | 24 | 12 | 8 |
| 512 | 10 | 7 | 4 |
| 65537 | 14 | 10 | 7 |
| **Opex** | **48** | **29 / 48** | **19 / 48** |

En regroupant ces 48 événements, la variation *observée* de profit des anciens appareils est **−508 £ de médiane par fenêtre** mais **+2 862 £ de moyenne** (fortes valeurs extrêmes) ; le changement total anciens + nouvel avion a une **médiane +1 582 £** et une **moyenne +6 541 £**. Ces nombres portent sur des **fenêtres de trois mois**, **pas sur un profit annuel marginal net d'amortissement**, et aucune décomposition de revenu brut/dépense moteur n'est possible sur ces seuls checkpoints. AAA n'offre que **cinq événements** selon le même filtre, insuffisants pour inférer une différence de politique.

Exemples exacts de lignes du JSON événementiel :

| Graine | Première apparition | Paire de gares (clé locale) | Passage N | ID neuf | Δ profit anciens 3 mois | Profit du neuf 3 mois | Δ profit ligne 3 mois |
|---|---|---|---|---:|---:|---:|---:|
| 42 | 1973-08-01 | `air\|43,44` | 2→3 | 175 | −4 140 £ | +3 571 £ | **−568 £** |
| 42 | 1973-08-01 | `air\|25,26` | 2→3 | 353 | −8 046 £ | +17 793 £ | +9 747 £ |
| 42 | 1974-06-01 | `air\|25,65` | 1→2 | 632 | −19 248 £ | +1 211 £ | **−18 038 £** |
| 42 | 1974-08-01 | `air\|51,64` | 1→2 | 796 | −867 £ | −708 £ | **−1 575 £** |

La **présence de gains sur d'autres lignes ainsi que de pertes sans renfort** empêche d'imputer automatiquement les 19 baisses à l'achat. Sur le même 3×5, le profit annuel courant des appareils survivants entre fin 1972 et fin 1974 se dégrade aussi lorsque leur **ligne n'a pas été renforcée** : seed42 **−229,1 k£**, seed512 **+33,3 k£**, seed65537 **−84,7 k£** (groupes non renforcés, agrégés par graine) ; sur lignes renforcées, respectivement **−326,8 / −222,6 / −174,0 k£** pour les anciens appareils survivants. Cela renforce le besoin d'un contrôle explicite sur le marché.

**Écart « profit marginal prédit − réalisé »** : les 48 événements ci-dessus viennent du **bras sans sonde** et ne doivent pas être rapprochés des devis d'une autre trajectoire. En revanche, un second diagnostic ci-dessous **apparie les logs et les sauvegardes du même bras ON** avec station-pair, identifiant de véhicule et fenêtre mensuelle exacte. Il fournit une comparaison observationnelle prévue/réalisée qui n'était pas possible avec le seul banc annuel.

### 3.2. Même exécution : devis AIR_P0_BUY contre profit moteur des mêmes avions

Analyse reproductible `results/air_marginal_p0_buy_3x5_20261008.json`, 117 `AIR_P0_BUY` réels du bras sondé, 115/117 appariés à une paire **exacte de tuiles d'aéroports** dans le snapshot mensuel ; 2/117 ne le sont pas. En exigeant en plus **un unique nouvel identifiant d'avion**, une ligne station-pair stable, aucune autre entrée/sortie de flotte **sur cette ligne** pendant une fenêtre de **trois mois avant et trois mois après**, et une comparaison sans franchissement d'année, il reste **54 achats isolés**.

| Graine ou période | Cas isolés | Profit de ligne observé moins élevé après renfort | Réalisé inférieur au prédit ramené à 3 mois |
|---|---:|---:|---:|
| 1972 | 10 | 4 | 9 |
| 1973 | 29 | 11 | 18 |
| 1974 | 15 | 2 | 5 |
| **Total** | **54** | **17 / 54** | **32 / 54** |

Le devis `project.profitAnnual` était positif pour tous ces achats. Sa prévision ramenée à trois mois (`profitAnnual / 4`, **hypothèse simplificatrice de saisonnalité uniforme**) est **7 062 £ de médiane** pour un changement observé de ligne de **3 533 £ de médiane** ; **32/54** changements observés sont inférieurs au devis proratisé. En **moyenne**, l'observé (**13 541 £**) dépasse néanmoins le prédit (**8 730 £**) à cause de cas extrêmes : **il n'y a donc pas de biais d'optimisme positif homogène démontré par une moyenne**. L'événement suivi peut transporter des passagers gagnés par augmentation du rating et profiter de changements exogènes ; la comparaison n'est pas une estimation causale de Δ profit.

| Graine, date | Ligne Squirrel / passage | Prévu annuel | Prévu sur 3 mois | Δ ancien(s) avions | Profit nouvel avion sur 3 mois | Δ ligne observé sur 3 mois | Écart observé – prévu 3 mois |
|---|---|---:|---:|---:|---:|---:|---:|
| 42, 08/06/1972 | `2`, 2→3 | +71 516 £ | +17 879 £ | −7 063 £ | −911 £ | **−7 974 £** | **−25 853 £** |
| 42, 20/06/1972 | `4`, 2→3 | +63 940 £ | +15 985 £ | −8 175 £ | −719 £ | **−8 894 £** | **−24 879 £** |
| 65537, 05/05/1972 | `1`, 2→3 | +87 836 £ | +21 959 £ | −17 551 £ | +4 639 £ | **−12 912 £** | **−34 871 £** |
| 42, 23/05/1973 | `30`, 1→2 | +39 312 £ | +9 828 £ | −25 044 £ | +7 414 £ | **−17 630 £** | **−27 458 £** |
| 42, 15/07/1972 | `0`, 2→3 | +51 977 £ | +12 994 £ | +10 130 £ | +2 448 £ | +12 578 £ | −416 £ |
| 42, 14/05/1974 | `50`, 1→2 | +1 688 £ | +422 £ | voir JSON | voir JSON | **−1 371 £** | **−1 793 £** |

Les quatre premiers cas démontrent **la possibilité effective de choisir un renfort rentable selon C121 mais suivi d'un changement net de ligne négatif**, y compris un **1→2 pendant 1973**, le début du décrochage. Ils ne prouvent pas que l'avion en est seul responsable. Les identifiants des appareils, les tuiles d'aéroports et toutes les autres observations sont dans le JSON et les CSV `results/air_marginal_p0_buy_3x5_20261008.csv` (117 décisions) et `results/air_marginal_p0_logged54_20261008.csv` (54 cas isolés). Aucune des 54 fenêtres n'écarte les modifications de flotte sur **d'autres lignes**, les changements concurrentiels ou les tendances intrinsèques du marché : d'où le qualificatif **observationnel**.

## 4. Autopsie du chemin réel AIR dans le code courant

1. **Demande** : `air_coverage.nut` reconstitue production potentielle PASS/MAIL des extrémités, puis station/catchment et parts de rating. Le chemin V93 de production mensuelle est distinct et **désactivé par défaut** (`v93_air_demand_production=0`) ; `C121_AIR_ECONOMICS=1` prend la main sur l'ancien replay C115.
2. **Revenu, cadence et N cible** : `air_economics_c121.nut:695–825` calcule pour chaque N le débit réellement possible à chaque piste, la capacité selon les deux sens, le rating, la part de cargo attribuée et le revenu PASS/MAIL, puis enlève coût d'exploitation et amortissement des avions. `:915–961` choisit **N qui maximise le profit annuel prédit**, avec ROI en départage. Le capital propre d'acquisition est inclus dans `capital`, celui des aéroports intervient dans le budget et ROI, mais l'amortissement infrastructure est désactivé dans le profil courant (`INFRA_AMORT_PCT=0`). Le modèle intègre les pertes d'autres lignes partageant les **mêmes stations**.
3. **Après construction** : `air_catalog_c121.nut:296–385` mémorise la cible `targetAirPlanes` et le profit marginal théorique exact `P(N+1)−P(N)` pour le palier courant, ainsi que l'échantillonnage réalisé à zéro.
4. **Admission des renforts** : `_resizeAirFleets` (`task_air.nut:951–1358`) impose cadence, observation initiale, état de flotte, restrictions de piste, trésorerie et parfois stock. Sous la cible, C121 peut admettre un +1 sur flux prévu sans avion entier en attente. `c121_air_first_live_growth=1` par défaut accélère le premier **1→2** sur un signal live équilibré 90 jours dans les **quatre premières années** de partie ; ce signal n'est pas une mesure de la marge économique N+1. À partir de 1974, le premier 1→2 peut également passer par la cadence annuelle historique C121, et garder `samples=0`. **Lorsque N atteint la cible, `c121BelowTarget` devient faux et le chemin historique redevient accessible** ; le réglage expérimental `c121_air_target_limit` est à **0**.
5. **Profit utilisé et rang** : `OpexProjectFromFleet` (`projects_builders.nut:156–258`) emploie le **profit marginal** C121 avec apprentissage tant que `N<target`. **À `N>=target`**, repli sur le profit **moyen** déjà observé `lastProfit/N` (ou une prédiction moyenne historique si l'observation manque). Ce terme, positif pour une ligne saine, peut être strictement supérieur à `P(N+1)−P(N)`, **non positif par définition de la cible maximisante du même modèle à ce point**. Le `profitAnnual` sert ensuite au filtre et au `fundScore` C69/C70, et la comparaison des nouveaux projets AIR se fait dans le TOPK du portefeuille. Les scores capital/opcodes encouragent par ailleurs les renforts bon marché à faible coût de planification ; le projet effectivement élu n'est pas nécessairement celui au profit **réseau** maximum.
6. **Achat** : `task_projects.nut:194–323` revalide l'effectif de la ligne et le cash, puis `OpexAirAddPlane` (`air_fleet.nut:397–473`) clone l'appareil. Au profil courant, ce dernier ne rebloque la cible que si `C121_AIR_TARGET_LIMIT` **ou** la compétition visible sont activés ; leurs défauts sont à 0. Les remplacements V92, reconstructions après crash et ouvertures de ligne doivent être **comptés séparément** de N→N+1. Une nouvelle ligne a des coûts d'aéroports, et ne se confond pas avec un renfort.
7. **Apprentissage** : `task_projects.nut:240–245,297–305` ne pose un baseline de profit/revenu marginal réalisé **que pour les renforts sous la cible**. `task_report.nut:36–76,387–397` calcule à l'année +2 la variation de revenu/profit de la **ligne entière**, retranche l'amortissement de l'avion, puis tient une moyenne et interdit le dernier palier observé négatif. Cette mesure est utile pour le score, **mais contaminée par les autres changements** ; elle n'est pas un contrefactuel. Les achats passés par le repli historique **ne bénéficient pas de ce suivi marginal**.

| Composante économique requise pour N→N+1 | Modèle C121 froid | Apprentissage après achat | Score/choix effectivement employé |
|---|---|---|---|
| Recette supplémentaire PASS et MAIL | **Oui**, différence de la recette totale attendue à N+1 et N | Revenu annuel de la ligne entière, observé après délai | Marge C121 tant que N<cible ; sinon possible profit moyen |
| Coûts d'exploitation + prix du nouvel avion | **Oui**, coût annuel appareil et amortissement ; `plane.price` au capital/ROI | Coûts moteurs inclus dans `lastProfit` ; amortissement économique rajouté par le learner | Capital et score de portefeuille ; coût aéroports séparé des seuls renforts |
| Revenu auparavant perçu par les autres appareils de la **même** ligne | **Implicitement oui** : demande plafonnée, P(N+1)−P(N) sur **tout** le service | Profits individuels non sauvegardés dans la ligne Squirrel ; ligne entière seulement | Aucun recalcul réseau causal après achat |
| Autres lignes de la **même station** | **Approximé** via parts de trafic et perte de débit à la piste | Non isolé des autres événements | Externalité intégrée au devis nouvelle ligne C121, pas garantie sur toute réévaluation fleet |
| Autres stations Opex recouvrant le **même marché** | **Incomplet** lorsque le nouveau projet ne réutilise pas le même StationID | Pas de baseline des autres lignes | Score potentiellement trop optimiste pour nouvelle station |
| Contraintes physiques, attentes, congestion, concurrence | **Oui partiellement** : temps rotation, cadence des pistes, rating, stocks et répartition observable | Signaux annuels et C117 ; observation retardée, concurrence changeante | Gardes de cadence/stock et TOPK, certains signaux froids permettent 1→2 |
| Capital immobilisé et meilleure liaison non construite | Capital et `immobilise` dans le ROI, budgétisation C69 | Aucune réalisation contrefactuelle du projet évincé | **Non optimisé en profit réseau**, rang selon `fundScore` ; candidat suivant n'est pas garanti finançable |

La distinction **devis physique brut → facteur de réalisation C121/C70 → `project.profitAnnual` → `fundScore`** est indispensable : les nombres de `AIR_P0_BUY` sont les **valeurs finales du projet admis**, pas les revenus bruts du premier calcul. Le modèle de flotte calculé à la construction et la marge utilisée par le portefeuille peuvent différer lorsque le facteur arm évolue, même sans changement de matériel.

**Défaillance décisionnelle établie** : un palier que C121 estime déjà au-delà de sa profondeur optimale peut encore recevoir un avion s'il satisfait les conditions historiques de stock et de profit **moyen**. Cela n'affirme pas que tous les nouveaux avions proviennent de ce chemin : **son exposition effective doit être mesurée**. Ne pas confondre existence du bug logique et poids économique prouvé.

### Vérification d'exposition : le repli historique n'explique PAS les achats sondés

Le diagnostic événementiel `air_p0_probe_3x5_r1`, mêmes graines 42/512/65537 avec le réglage `air_p0_margin_probe` activé dans la variante, a enregistré **117 succès N→N+1**, **117/117 sous leur cible C121**, **0/117** dans le régime `legacy_at_or_above` ; **107/117** n'avaient encore aucun échantillon marginal observé (`marginal_samples=0`). Le nombre de renforts dans l'année est **8 / 16 / 15 / 45 / 33** en 1970/71/72/73/74, soit **78/117 en 1973–1974**. Dans le lot 1974, **31/33** sont encore sans échantillon marginal, bien que l'année soit très avancée. **Le repli au profit moyen est une faiblesse source vraie mais n'a aucune exposition constatée dans ce petit lot**, et ne doit donc pas être vendu comme cause dominante des 95 avions.

Par profondeur : **1973 : 30 achats 1→2 et 15 achats 2→3** ; **1974 : 29 achats 1→2 et 4 achats 2→3**. C'est donc bien surtout **le premier renfort** qui se multiplie au moment du décrochage. Le signal `first_live` ne permet pas d'affirmer qu'il a accéléré tous ces achats : l'exposition requiert ses propres traces de garde. Il a été appliqué par défaut pendant les années 1970–1973, pas en 1974 lorsque sa phase de quatre ans est terminée.

| Graine | Renforts 1970–1974 | En 1973 | En 1974 | Marges sans échantillon | Candidats AIR classés ensuite observés* |
|---|---:|---:|---:|---:|---:|
| 42 | 65 | 31 | 14 | 61 | 53 |
| 512 | 20 | 5 | 8 | 18 | 13 |
| 65537 | 32 | 9 | 11 | 28 | 25 |
| **Total** | **117** | **45** | **33** | **107** | **91** |

*Un `next_air_rank>=0` est un **snapshot d'un candidat classé derrière la flotte**, pas un projet distinct sacrifié, ni une preuve qu'il était finançable/constructible. Les revisites du même projet ne peuvent pas être additionnées comme opportunités économiques indépendantes.*

| Année | Achats renforts du lot 3 graines | Capital déboursé | Somme des profits marginaux annuels **prédits** |
|---|---:|---:|---:|
| 1970 | 8 | 356 849 £ | 677 595 £/an |
| 1971 | 16 | 669 529 £ | 988 974 £/an |
| 1972 | 15 | 647 127 £ | 1 015 717 £/an |
| **1973** | **45** | **1 838 174 £** | **1 332 355 £/an** |
| **1974** | **33** | **1 460 515 £** | **515 577 £/an** |

Il s'agit de devis **à dates différentes**, non cumulables comme profit acquis. Parmi les achats 1974, **5/33** affichent un ROI prédit sous **10 %/an** et **2/33** sous **5 %/an** ; l'exemple extrême `seed=42, 1974-05-29, line=42, 1→2` déclare **296 £/an pour ~38 448 £ déboursés**, seulement **0,7 %/an prédit**, malgré un `target=2`, sans aucune marge réelle déjà observée. Cela établit **un achat très faiblement prometteur même selon les propres chiffres du portefeuille**, pas encore sa perte causale après exploitation. Le profit marginal **observé** et sa différence au profit **prévu** ne sont pas déductibles de ces seules lignes moteur : on doit recouper les identifiants et profits individuels des snapshots mensuels, et conserver l'avertissement sur les événements concurrents.

**Sensibilité** : sur le 1×1 smoke graine 42, OFF et ON ont les mêmes métriques ; sur le 3×5, OFF/ON **divergent** malgré un code de décision identique : `profit_year` variante − référence **+58 319 £/an en moyenne**, V/D/E=2/1/0 et intervalle large, **pas un gain du mécanisme**, mais un artefact de cadence/opcodes de journalisation. Les deux bras sont sains (6/6), bundle identique `a199cca49...`, logs gardés. Aucune comparaison événement par événement ne doit transférer ses résultats ON à la trajectoire OFF comme un contrefactuel.

## 5. Cannibalisation : ce qui est inclus et ce qui manque

- **Correctement approximée dans le modèle pour les mêmes gares** : `OpexC121ExistingStationService` collecte les services existants d'un `stationId` exact ; `air_economics_c121.nut:785–820` soustrait leur revenu détourné et la perte éventuelle de débit aux pistes.
- **Angle mort potentiel pour les nouvelles gares** : `air_economics_c121.nut:175–193` met `existingPaxBefore`/`existingMailBefore` à zéro si `reuse=false`. Un nouveau site couvrant des producteurs déjà desservis par une station Opex **distincte** reçoit du trafic projeté mais la perte de rentabilité de cette ancienne station n'est pas soustraite au profit **réseau** du projet neuf. Cela peut surclasser certaines extensions C83/newpair. Le modèle ne double-compte donc **pas systématiquement tout le nouveau trafic**, mais il ne comptabilise pas exhaustivement l'externalité réseau.
- **Test grossier de ville commune** : sur 1972→1974, les lignes anciennes partageant au moins une ville avec une nouvelle ligne n'expliquent pas, à elles seules, la baisse : variation agrégée de **+0,4 k£/seed** pour les lignes ainsi classées, contre **−94,4 k£/seed** pour les autres. Ce proxy **n'est pas** un test précis du recouvrement physique des aires de captage, des correspondances ni des destinations ; un jeu de marchés issus des tuiles/catchments est nécessaire avant d'attribuer ces pertes.
- **Estimation prudente** : perte de profit ancienne *associée* observée **−93,9 k£/seed**, perte **causalement attribuable à la cannibalisation : non identifiée**, et certainement **pas automatiquement 93,9 k£**. Une borne basse positive de destruction de valeur n'est **pas** démontrée à partir des snapshots annuels.

## 6. Départager les hypothèses et les alternatives

| Hypothèse | Exposition et preuves favorables | Contre-preuve / donnée manquante | Statut |
|---|---|---|---|
| **H1. Trop de renforts pour la demande** | 38,6 avions nets supplémentaires ; productivité moyenne AIR en baisse ; certaines lignes renforcées régressent | 11,1 lignes anciennes **non renforcées** chutent également ; besoin des achats N→N+1, du transport par appareil et du vrai Δ réseau | Probable, poids non identifié |
| **H2. Marge prévue trop optimiste ou trop froide** | **107/117** achats sans observation marginale au choix, **32/54** réalisent moins que le devis trimestrialisé et **17/54** des baisses de ligne ; repli `lastProfit/N` à N≥cible existe aussi | Moyenne réalisée > moyenne prévue sur les 54 cas, saisonnalité/activité exogène ; **0/117 achat** suit le repli historique dans ce lot | **Principal mécanisme de décision exposé**, biais moyen causal non établi |
| **H3. Cannibalisation de réseau** | Perte des anciennes lignes de 93,9 k£/seed ; absence d'imputation de certains nouveaux catchments non joints | Proxy ville commune n'étaye pas l'attribution simple ; marchés exacts, contrefactuel et trafic manquants | Plausible, non quantifiée causalement |
| **H4. Renforts moins bons que nouvelles lignes** | Arbitrage par `fundScore` orienté rentabilité capital/opcodes ; faible gain de profit sur 27,55 avions supplémentaires nets des lignes renforcées ; **91/117** achats sondés ont un candidat AIR suivant visible | Ce rang ne prouve ni financement, ni faisabilité, ni unicité de l'occasion ; caisse Opex croît beaucoup ; comparer des projets **à la date de l'achat** | Exposition au classement mesurée, éviction causale non prouvée |
| **H5. Limite physique ou commerciale** | Modèle cadence pistes et parts de marché ; vieillissement/competition possibles | Aucun nombre de refus de cadence ni délai aéroport récent extrait du moteur | Pas établi |
| **H6. Achats immobilisant le capital** | Actif flotte +830 k£ de valeur en 2 ans et autres dépenses aéroports ; choix à coût/opcode faible | Cash 0,71→2,73 M£, donc une **pénurie durable générale de cash n'est pas démontrée** ; une contention ponctuelle par projet reste possible | Secondaire/à mesurer |

**Hiérarchie de travail par poids probable (pas par fréquence des logs)** : (1) sous-performance de lignes anciennes, un phénomène réseau/demande à élucider (**−93,9 k£/seed associés**), (2) rendement trop faible et choix de renforts **sous la cible C121 en phase sans apprentissage** (**+17,2 k£ observés pour +27,55 avions nets sur lignes renforcées** ; **107/117** achats sondés sans échantillon marginal), (3) coûts d'opportunité multimodaux et absence de profit ferroviaire (**72 k£ Opex contre 871 k£ AAA sur les véhicules rail en décembre 1974**, différence structurelle **799 k£**, sans attribution à AIR). Cette hiérarchie **n'est pas une décomposition causale** : les trois postes peuvent se recouper. **Le repli historique au-dessus de la cible ne figure plus dans le trio principal** après son exposition nulle dans le lot sondé.

## 7. Instrumentation, validation, correctif minimal envisagé

**Lecture hors moteur** : extension passive de `sweeps/bench_1v1_5y_20seeds.py` avec `vehicle_financials` (`vehicle_id`, profits YTD/année précédente et valeur comptable), depuis les mêmes données VEHS, sans toucher au comportement NoAI. Les deux exécutions mensuelles successives sur 42/512/65537 ont les mêmes résultats de fin de partie. Contrat `--selftest` dans Docker : réussi.

**Sonde moteur** : réglage `air_p0_margin_probe=0` dans `info.nut/settings.nut/globals_pre.nut` ; uniquement sous `1`, `task_projects.nut` émet `AIR_P0_BUY` (ligne, date, N, cible, `c121_below` vs `legacy_at_or_above`, dépenses cash, profit/prix/score, baselines observées, stock/capacité, meilleure alternative AIR derrière) et `AIR_P0_ROUTE` (nouvelle ligne, réemploi d'aéroports, devis et rang). La sonde est post-élection, **n'entre jamais dans les choix** ; elle n'enregistre pas les remplacements/crashes comme renforts. Les logs `script-debug` et l'analyse mensuelle des mêmes graines doivent être croisés avec prudence, car activer les logs peut déplacer les opcodes/trajectoires.

**Hypothèse de correctif minimal pré-enregistrable, PAS adoptée** : le problème prioritaire est maintenant la **première décision de renforcement C121 sans apprentissage**, pas l'exception au-dessus de la cible. La prochaine expérimentation doit évaluer, au moment d'un achat `samples=0`, un **devis marginal frais** et confronter demande/production réellement reçue, ancien profit des mêmes véhicules, capacité et revenu prévu ; les scores froids doivent être *shadow-comparés* aux scores du portefeuille et aux nouvelles lignes réellement finançables. Selon l'exposition mesurée, branche candidate 0 par défaut dans `OpexProjectFromFleet` (`projects_builders.nut`) appliquant une **calibration de la marge fraîche basée sur des observations accessibles**, sans seuil inventé et sans suppression automatique des 1→2 rentables. En complément seulement, une garde marginale actuelle tous N dans cette même fonction éviterait le repli historique ; son **poids observé aujourd'hui est nul** dans le 3×5 et ne justifie pas une porte V102 isolée. Ne pas réactiver directement `c121_air_target_limit=1` : essais A40×3 et 40×6 déjà `fail_primary`.

**Critères de passage** : (i) couverture exacte de tous les chemins de renforcement réussis, y compris au-dessus de cible ; (ii) quantité et capital de renforts à Δ marginal prédit ≤0 ainsi que pertes des anciens appareils ; (iii) identité OFF et reproductibilité moteur sur plusieurs graines avec sondes ; (iv) coût en opcodes mesuré, comparé au gain d'éviter une décision dégradante ; (v) scénario alternatif de nouvelles liaisons distinctes vraiment admissibles. **Après** ces critères seulement : branche de comportement isolée 0→1, contrats VM/Save-Load et smoke moteur, puis **V102 A40×3, B20×10 uniquement si A passe**, profit annuel principal seuil +4 % avec garde de valeur −5 %. Jamais de défaut, commit, push ni merge sans preuve et demande explicite.

## 8. Question centrale et verdict provisoire

OpexAI possède ~95 avions en 1974 alors que C121 calcule déjà une cible optimale par profit et une marge avec coûts de flotte. La **voie effectivement exposée** dans les trois graines est celle des **renforts sous cible encore sélectionnés sur une marge principalement prédite à froid** ; en 1974, certains ont une rentabilité attendue très faible, tandis que les lignes anciennes stagnent ou perdent du revenu. Le retour réalisé par ligne arrive tard et n'isole pas la concurrence. Il existe aussi un **angle mort réseau** pour les nouveaux aéroports qui recouvrent le catchment d'une station Opex distincte, et un **repli historique mauvais au-dessus de la cible mais non exposé** dans ce lot. Voilà les mécanismes décisionnels identifiés, **pas encore leurs pertes causales séparées**. La prochaine décision ne doit pas être un paramètre de taille de flotte, mais une preuve liée aux achats froids 1→2 et aux débits réellement disponibles.

## 9. Poursuite du 09/10 — mécanisme exact de la seconde marche et témoins réseau

**Incohérence économique du modèle entre deux achats démontrée :** `air_catalog_c121.nut` ne mémorisait à la construction que `P(N0+1)−P(N0)` ; tant que `c121MarginalSamples=0`, `projects_builders.nut` pouvait réutiliser ce même nombre pour `N0+1→N0+2`. Dans les trois graines 42,512,65537, **17 achats 2→3** portant encore `samples=0` et un 1→2 antérieur identifiable réutilisent sans exception la **même marge brute** de profondeur. Cela prouve **une erreur de variable dans la règle de score**, et pas sa valeur économique causale. Le remplacement de ce devis par le vrai `P(3)−P(2)` est documenté, OFF par défaut, dans [l'expérience séparée](air_p0_second_step_20261009.md) ; le correctif ne suppose aucun seuil arbitraire de nombre d'avions, ne touche pas au 1→2 et n'est **pas adopté**.

**Contrôle observationnel indépendant des autres lignes** : `results/air_p0_nearest_observational_20261009.{json}` et son [rapport détaillé](../results/air_p0_nearest_observational_20261009_report.md) analysent les 54 achats avec voisins à effectif stable et témoin contemporain par graine/mois. Ancien profit net après retrait de tendance témoin : **médiane −1 442 £/3 mois**, **32/54** négatifs ; Δ de la ligne complète corrigé **médiane +167 £**, **25/54** négatifs. Parmi les voisins à effectif stable, **66/145** partagent exactement la station et baissent, seulement **4/4** partagent une ville sans gare commune (petit échantillon), et **594/1 490** ont des villes disjointes et baissent. Aucune autre ligne stable Opex à la fois de même **paire OD** et avec des **aéroports distincts** n'apparaît dans ces 54 fenêtres : l'angle mort inter-catchments ne peut être chiffré sur ce lot.

**Contamination** : les 54 fenêtres d'achats présentent toutes d'autres mouvements ; **466 occurrences achat×fenêtre**, dont 38 achats à station partagée dans 28 fenêtres. Elles ne sont **pas des achats indépendants**. Trois voisins AAA seulement ont le même marché OD sur des stations distinctes ; aucun estimateur robuste de cannibalisation contre AAA n'en ressort. Les 54 achats représentent **2 227 371 £ de décaissements observés**, dont **674 452 £** dans les 17 fenêtres à baisse de profit total de ligne ; ce sont des **montants exposés**, pas des capitaux économiquement perdus. Les baisses cumulées de ces 17 fenêtres se chevauchent, ne sauraient être additionnées et n'identifient **aucune perte causale minimale positive**. Une intervention appariée est indispensable avant un prétendu effet réseau.

**Validation du modèle expérimental** : les quatre contrats ciblés du réglage `air_p0_second_step_marginal=0` ont passé Docker, ainsi que le smoke graine42×1 OFF/ON (deux parties saines, résultats Opex identiques). Le premier diagnostic ciblé 3×5 `air_p0_second_step_3x5_20261009_r1` a six parties saines, `profit_year` variante−référence **−18 258 £/an moyen**, **1 victoire / 2 défaites**, `company_value` **−3,25 %**, **35 contre 31** renforts 2→3 ; **aucun gain admissible**. Sur graine512 un écart minime antérieur à l'action souligne la sensibilité à la capture d'opcodes. Une version corrigée avec capture et vérification d'éligibilité symétriques entre bras sondés est testée séparément ; **ne pas mélanger les bundles** ni promouvoir r1 au rang de porte V102.

### Résultat final du prolongement : la correction de profondeur n'est pas le levier économique attendu

Le deuxième essai `air_p0_second_step_parity_3x5_20261009_r2`, **6/6 sains**, avec captures C121 et sondes symétriques, donne variante − référence **−68 425 £/an** de `profit_year` à décembre 1974 (**0 victoire / 3 défaites**), ratio de valeur moyenne **−5,55 %**. Le correctif manque donc même la garde de valeur V102. Les premières divergences sont toutes liées à des renforts **2→3** : graine42 une autre ligne 2→3 est sélectionnée, graine512 la même ligne 2→3 reçoit un `pred_profit` recalé de **92 725 à 55 825 £/an**, graine65537 une nouvelle liaison remplace le renfort qui aurait été acheté. Les différences de profit AIR courant en 1974 sont toutes **négatives** (environ −209, −11 et −28 k£ par graine). Le nombre total de 2→3 achetés varie même de **32 en référence à 33 en variante**, soit aucune réduction mécanique garantie.

**Conséquence décisionnelle prouvée :** l'erreur de profondeur change réellement le choix du portefeuille et donc la trajectoire quand on la corrige. **Conséquence économique prouvée sur cet échantillon :** sa correction isolée **dégrade** les résultats. Cela ne rend pas l'ancien devis *correct*, mais réfute l'hypothèse qu'une valeur P3−P2 plus précise suffit à rattraper AAAHogEx. Le modèle d'opportunité, la fraîcheur de demande et les effets indirects de réseau restent la cible de l'enquête, sans seuil de flotte arbitraire. L'expérience demeure **OFF**, aucun défaut adopté, aucune porte V102 A/B ; données, méthode et limites : [fiche de qualification P0](air_p0_second_step_20261009.md) et `results/air_p0_second_step_parity_3x5_20261009_r2_analysis.json`.
