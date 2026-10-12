# Autopsie causale du cap de routes par hub AIR (air_hub_max_routes)

**Date d'analyse :** 12 octobre 2026  
**Auteur :** Antigravity (mode lecture seule — aucune modification de code, aucun banc, aucun commit)  
**Données sources :**
- Campagne Cap 2 : `results/hubcap_autopsie_cap2_4x3_20261012.json` / `.jsonl` et logs moteur `results/hubcap_autopsie_cap2_4x3_20261012_engine/`
- Campagne Cap 4 : `results/hubcap_autopsie_cap4_4x3_20261012.json` / `.jsonl` et logs moteur `results/hubcap_autopsie_cap4_4x3_20261012_engine/`
- Profil : 3 ans (1970–1972), duels 1v1 contre AAAHogEx figée (v115), OpenTTD 15.3 / OpenGFX 7.1, SHA bundle `f474a251f05e21c80b864ef1cfa43ff7365573c8da989179d1c7910b8fa66981` (arbre `461b8224bcceb2895eac7a8f2cffe02a5d37fc11 dirty=0`).

---

## 1. Profits/an terminaux OpexAI et reproductibilité du classement du 07/10

### 1.1 Tableau comparatif des profits/an terminaux (1972)

Les profits annuels OpexAI (`profit_year` à l'année terminale 1972) extraits des deux campagnes d'autopsie du 12/10 sont synthétisés ci-dessous :

| Graine | Cap 2 (variante) | Cap 3 (réf. camp. Cap 2) | Cap 3 (réf. camp. Cap 4) | Différence réf. | Cap 4 (variante) | Classement 12/10 | Optimum 07/10 documenté |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **17** | 1 299 175 £/an | 1 421 918 £/an | 1 421 918 £/an | **0 £** | 1 403 504 £/an | **Cap 3 > Cap 4 > Cap 2** | Cap 2 (rejeté/inversé) |
| **781335** | 1 816 536 £/an | 1 658 508 £/an | 1 658 508 £/an | **0 £** | 1 648 081 £/an | **Cap 2 > Cap 3 > Cap 4** | Cap 2 (**Confirmé**) |
| **1** | 2 406 622 £/an | 2 861 836 £/an | 2 861 836 £/an | **0 £** | 2 737 699 £/an | **Cap 3 > Cap 4 > Cap 2** | Cap 4 (non reproduit) |
| **802204** | 2 869 040 £/an | 2 758 108 £/an | 2 758 108 £/an | **0 £** | 2 671 298 £/an | **Cap 2 > Cap 3 > Cap 4** | Cap 4 (inversé : Cap 2 1er, Cap 4 pire) |

### 1.2 Contrôle d'identité de la référence (Cap 3)

Pour les 4 graines, la référence Cap 3 (`reference_*`) dans la campagne Cap 2 et dans la campagne Cap 4 donne **exactement le même profit/an au centime près (différence = 0 £)**, la même valeur d'entreprise (`company_value`), le même nombre de véhicules et la même trésorerie :
- Graine 17 : 1 421 918 £/an (CV: 2 962 488 £, 41 véhicules, 27 aéroports, trésorerie: 190 018 £)
- Graine 781335 : 1 658 508 £/an (CV: 2 832 873 £, 43 véhicules, 31 aéroports, trésorerie: 992 067 £)
- Graine 1 : 2 861 836 £/an (CV: 5 365 609 £, 83 véhicules, 37 aéroports, trésorerie: 1 759 609 £)
- Graine 802204 : 2 758 108 £/an (CV: 4 907 842 £, 88 véhicules, 40 aéroports, trésorerie: 965 680 £)

L'audit textuel des journaux moteur OpexAI (`[script:4] [0]`) confirme une identité stricte événement par événement. Seuls les pointeurs mémoire internes d'instances et micro-profilages d'opcodes de l'adversaire AAAHogEx (`[script:4] [1]`) présentent des variations de logging négligeables.

### 1.3 Analyse de la reproductibilité par rapport au 07/10

Sur les 4 graines sélectionnées le 07/10 comme cas discriminants :
1. **Graine 781335 : Le classement SE REPRODUIT fidèlement.**  
   Le Cap 2 bat très nettement le Cap 3 (+158 028 £/an, +9,5 %) et le Cap 4 (+168 455 £/an).
2. **Graine 17 : Le classement NE SE REPRODUIT PAS (inversion complète).**  
   Identifiée le 07/10 comme favorable au Cap 2, elle voit le Cap 2 s'effondrer à la dernière place (-122 743 £/an par rapport au Cap 3). Le Cap 3 est l'optimum.
3. **Graine 1 : Le classement NE SE REPRODUIT PAS.**  
   Classée favorable au Cap 4 le 07/10, elle est ici largement dominée par le Cap 3 (+124 137 £/an d'avance sur le Cap 4, et +455 214 £/an sur le Cap 2). Le Cap 4 n'est que second.
4. **Graine 802204 : Le classement NE SE REPRODUIT PAS (inversion spectaculaire).**  
   Classée favorable au Cap 4 le 07/10, elle voit le Cap 4 terminer dernier (2 671 298 £/an), tandis que le Cap 2 devient le grand vainqueur (2 869 040 £/an, soit +110 932 £/an vs Cap 3 et +197 742 £/an vs Cap 4).

**Pourquoi ce décalage entre le 07/10 et le 12/10 ?**  
Entre le commit d'adoption du Cap 3 (`662c5f7`, 7 octobre au soir) et le code testé le 12 octobre (`461b822`), plusieurs changements substantiels ont été intégrés par défaut sur `master` :
- `92f9b6e` : Adoption de `v93_airport_no_pop_floor` par défaut (suppression du seuil plancher de population pour les sites d'aéroports).
- `aebacdb` : Adoption des jours de paiement physiques AIR (`v138`), modifiant les temps de vol modélisés et l'évaluation des revenus.
- `95a6ad2` : Activation par défaut de la réalisation directe de hub C121.
- `016fdbf` : Incrémentation catalogue `v141`.
- `978d098` : Adoption du catalogue AIR AC04-B, AC05 et AC06 v2.

Ces modifications ont déplacé les équilibres d'évaluation économique et les chemins décisionnels de construction des aéroports, modifiant la hiérarchie locale des caps pour 3 graines sur 4.

---

## 2. Analyse causale détaillée et première divergence par graine

Le mécanisme de cap s'exécute à trois endroits centraux du code :
- [`OpexAirAirportMaxRoutes(airportType)`](../ai/OpexAI/air_trip.nut#L174-L181) dans [ai/OpexAI/air_trip.nut](../ai/OpexAI/air_trip.nut#L174) : applique `min(defaultCap, AIR_HUB_MAX_ROUTES)`. En 1970–1972, seuls les aéroports petits (`AT_SMALL`) et navettes (`AT_COMMUTER`) existent (`defaultCap = 4`). Donc `air_hub_max_routes = 2` plafonne à 2 routes, `3` à 3 routes, et `4` à 4 routes.
- [`OpexAirDiscoverHubs`](../ai/OpexAI/air_planning.nut#L1342-L1343) et [`OpexAir0310RestoredHubUsable`](../ai/OpexAI/air_planning.nut#L1084) dans [ai/OpexAI/air_planning.nut](../ai/OpexAI/air_planning.nut#L1084) : `if (hub.routes >= maxRoutes) continue;` exclut le hub saturé de la liste des têtes de lignes admissibles.
- [`OpexAirBatchAirportUnderCap`](../ai/OpexAI/task_air.nut#L566-L567) dans [ai/OpexAI/task_air.nut](../ai/OpexAI/task_air.nut#L566) : valide le respect du cap avant exécution du batch.

---

### 2.1 Graine 17

#### Première divergence
- **Cap 3 vs Cap 2 : 22 avril 1971** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 8).
  - En Cap 3 : raccordement `hubsite` depuis le hub principal station 0 (ville 25, pop. 3 493) vers la ville 28 (`stb=35`, nouvel aéroport). C'est la **3e route** de la station 0 (après la ligne 0 en newpair et la ligne 2 en hubsite).
  - En Cap 2 : la station 0 a déjà 2 routes. Ayant atteint son plafond (`routes = 2 >= 2`), elle est exclue des hubs. OpexAI est forcée de se rabattre le 7 mai 1971 sur la station 1 (ville 37) vers la ville 28 (`stb=34`).
- **Cap 3 vs Cap 4 : 14 mai 1971** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 9).
  - En Cap 3 : la station 0 ayant 3 routes est saturée ; Cap 3 se tourne vers la station 2 (ville 21).
  - En Cap 4 : la station 0 a 3 routes mais n'est pas saturée (`3 < 4`) ; elle reste dans le catalogue de hubs, ce qui réordonne la sélection du lot (Cap 4 choisira la station 1 vers ville 17, puis donnera une 4e route à la station 0 le 28 juin 1971).

#### Chaîne causale menant à l'écart de profit
- **Cap 2 (Le piège du vivier restreint) :**
  - La graine 17 possède le vivier de villes le plus restreint de l'échantillon : seulement 39 villes viables avec site d'aéroport au jour 0, et seulement 20 villes avec pop. ≥ 500.
  - En bloquant les deux grands hubs (ville 25, pop. 3 493 et ville 21, pop. 2 882) à 2 routes, Cap 2 interdit de réutiliser leur fort gisement de passagers.
  - OpexAI est contrainte d'ouvrir des aéroports dans des hameaux à très faible demande (pop. < 400).
  - Résultat terminal : Cap 2 ouvre 30 aéroports (contre 27 en Cap 3), mais les lignes périphériques génèrent trop peu de recettes. La trésorerie s'assèche (69 782 £), la dette explose à **290 000 £** (contre 80 000 £ en Cap 3), et OpexAI tente de compenser en fin de partie par du transport alternatif (4 véhicules routiers, 4 trains). Profit terminal : **1 299 175 £/an** (-122,7 k£ vs Cap 3).
- **Cap 3 (L'équilibre optimal) :**
  - Permet aux hubs majeurs de concentrer 3 liaisons radiales rentables, évitant de gaspiller du capital sur les plus petites villes. 27 aéroports suffisent, dette réduite à 80 000 £, profit : **1 421 918 £/an**.
- **Cap 4 :**
  - Ajoute une 4e route sur la station 0 le 28 juin 1971 (`sta=0 stb=42`). Légère baisse d'efficacité due au partage de la piste unique du petit aéroport, terminant à **1 403 504 £/an**.

---

### 2.2 Graine 781335

#### Première divergence
- **Cap 3 vs Cap 2 : 5–16 novembre 1970** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 5).
  - Avant novembre 1970, OpexAI a construit les lignes 0, 1, 2, 3. Les deux seuls hubs initiaux, station 0 (ville 41, pop. 3 227) et station 2 (ville 25, pop. 1 870), ont chacun exactement 2 routes.
  - En Cap 3 : la station 0 peut accueillir une 3e route. OpexAI prépare l'extension vers la ville 45 (construite le 28 décembre 1970, `sta=0 stb=27`).
  - En Cap 2 : station 0 et station 2 sont toutes deux saturées dès l'été 1970. Dès le 16 novembre 1970, Cap 2 est **forcée de changer de stratégie** : elle construit une nouvelle paire indépendante point-à-point `newpair` (`sta=20 stb=21`, ville 38 -> ville 21), ouvrant 2 nouveaux aéroports d'un coup.
- **Cap 3 vs Cap 4 : 29 juin 1971** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 11).
  - Cap 4 ajoute une **4e route** sur la station 0 (`sta=0 stb=55`, ville 41 -> ville 34), alors que Cap 3 bifurque sur la station 2.

#### Chaîne causale menant à l'écart de profit
- **Cap 2 (Le triomphe du maillage horizontal décentralisé) :**
  - La graine 781335 a une géographie particulière : **une seule très grande ville** (ville 41, pop. 3 227) et un immense vivier de 46 villes moyennes/petites (47 villes au total, dont 26 avec pop. ≥ 500).
  - En Cap 3 et Cap 4, OpexAI concentre 3 puis 4 routes sur la ville 41. Mais les liaisons supplémentaires relient de minuscules bourgs (villes 45, 34) et saturent la piste unique sans apport massif de passagers.
  - En Cap 2, le blocage à 2 routes contraint OpexAI à bâtir des `newpair` partout sur la carte : elle ouvre 7 paires point-à-point successives en 1970–1971.
  - Fin 1972, Cap 2 a ouvert 34 aéroports et exploite **50 avions** (contre 38 avions et 31 aéroports en Cap 3).
  - Sa flotte génère un volume d'affaires bien supérieur, la dette est intégralement remboursée (0 £), et la trésorerie s'élève à 613 801 £. Profit terminal : **1 816 536 £/an** (+158,0 k£ vs Cap 3).

---

### 2.3 Graine 1

#### Première divergence
- **Cap 3 vs Cap 2 : 18–19 avril 1971** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 13).
  - La station 0 (ville 40, métropole de pop. 3 946) avait 2 routes (lignes 0 et 12).
  - En Cap 3 : OpexAI lui accorde sa 3e route le 18 avril (`sta=0 stb=57`, ville 40 -> ville 3, nouvel aéroport `stb=57`).
  - En Cap 2 : la station 0 étant saturée à 2 routes, Cap 2 bascule sur la station 1 (ville 32, pop. 2 334) vers la ville 26.
- **Cap 3 vs Cap 4 : 19–24 avril 1971** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 14).
  - En Cap 3 : la station 0 est désormais saturée à 3 routes (`routes = 3 >= 3`). OpexAI bascule sur la station 1 (`sta=1 stb=60`).
  - En Cap 4 : la station 0 peut accepter une **4e route** (`3 < 4`). Cap 4 raccordera immédiatement la ville 40 à la ville 38 (`sta=0 stb=58`).

#### Chaîne causale menant à l'écart de profit
- **Cap 3 (L'optimum de connectivité des grandes métropoles) :**
  - La graine 1 dispose d'une démographie exceptionnellement dense : 5 villes avec pop. ≥ 2 000 (dont deux métropoles à 3 946 et 3 338), 16 villes ≥ 1 000 hab.
  - Le Cap 2 bride prématurément ces métropoles capables de fournir du trafic passager pour 3 lignes à haut coefficient de remplissage. Privée de cette concentration profitable, Cap 2 ne peut faire voler que 56 avions et s'effondre à **2 406 622 £/an** (-455,2 k£ vs Cap 3).
  - Le Cap 4 pousse le bouchon trop loin en plaçant 4 routes sur la même piste unique d'aérodrome. Les avions commencent à subir des attentes à l'atterrissage ([`C121_HUB_DELAY`](../ai/OpexAI/probes.nut#L180) moyen de 3,93 j, pic à 32,3 j). Cap 4 déploie 82 avions mais dégage **2 737 699 £/an**, soit -124,1 k£ par rapport au Cap 3.
  - Cap 3 réalise le compromis idéal : 79 avions, 37 aéroports, des petits aéroports exploités à pleine capacité sans bouchon, et un profit record de **2 861 836 £/an**.

---

### 2.4 Graine 802204

#### Première divergence
- **Cap 3 vs Cap 2 : 24 mai 1971** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 14).
  - La station 0 (ville 38, métropole pop. 3 702) a 2 routes (lignes 0 et 3).
  - En Cap 3 : Cap 3 construit sa 3e route (`sta=0 stb=59`, ville 38 -> ville 45).
  - En Cap 2 : la station 0 est bloquée. Cap 2 utilise la station 2 (ville 10, pop. 3 141) vers la ville 36.
- **Cap 3 vs Cap 4 : 30 juin 1971** (décision [`C121_BUILD`](../ai/OpexAI/air_catalog_c121.nut#L415) index n° 16).
  - La station 1 (ville 34, pop. 2 589) a déjà 3 routes.
  - En Cap 3 : la station 1 est saturée (`routes = 3 >= 3`). Cap 3 utilise la station 2.
  - En Cap 4 : Cap 4 greffe une **4e route** sur la station 1 (`sta=1 stb=65`, ville 34 -> ville 13).

#### Chaîne causale menant à l'écart de profit
- **Cap 4 (La catastrophe de congestion physique) :**
  - La graine 802204 est la plus peuplée de l'échantillon (47 312 hab., 5 villes > 2 000, 36 villes > 500).
  - En autorisant 4 routes par hub, Cap 4 concentre les avions sur les mêmes petits aérodromes (`AT_SMALL`). Les logs moteur de Cap 4 révèlent une congestion aiguë : le marqueur [`C121_HUB_DELAY`](../ai/OpexAI/probes.nut#L180) ([ai/OpexAI/probes.nut](../ai/OpexAI/probes.nut#L180)) atteint un **retard moyen de 13,64 jours** par vol (contre 2,81 j en Cap 3) et un **pic catastrophique à 119,95 jours d'attente** !
  - Les avions tournent en boucle dans le ciel, les cadences s'effondrent, les notes de station plongent et les recettes fondent. Cap 4 finit dernière à **2 671 298 £/an**.
- **Cap 3 (Surflotte et coûts d'amortissement) :**
  - Cap 3 achète 84 avions pour 40 aéroports. Bien que moins congestionnée que Cap 4, elle souffre de surcapacité et de coûts de maintenance élevés par rapport à son cash généré. Profit : **2 758 108 £/an**.
- **Cap 2 (Régularité et rotation optimale) :**
  - Cap 2 maintient un maillage équilibré de 64 avions sur 40 aéroports (environ 1,6 avion par aéroport, 2 routes max). Aucun engorgement sur les pistes, d'excellentes rotations, un cash résiduel de 1 789 541 £ et un profit maximal de **2 869 040 £/an** (+110,9 k£ vs Cap 3).

---

## 3. Signaux observables avant décision : cause du cap vs conséquence de la trajectoire

### 3.1 Tableau des métriques observables AVANT la première divergence

Toutes les métriques ci-dessous sont observées soit au **Jour 0 (1er janvier 1970)** via la découverte initiale des sites [`C96_SITE`](../ai/OpexAI/air_sites.nut#L417) ([ai/OpexAI/air_sites.nut#L417](../ai/OpexAI/air_sites.nut#L417)), soit au bilan de la **première année (1er janvier 1971)** avant toute divergence de cap :

| Signal observable AVANT divergence | Graine 17 | Graine 781335 | Graine 1 | Graine 802204 |
|---|:---:|:---:|:---:|:---:|
| **Population totale des sites viables (J0)** | 33 557 hab. | 33 193 hab. | 42 350 hab. | 47 312 hab. |
| **Nombre total de villes viables avec site AIR** | **39 villes** (restreint) | 47 villes | 44 villes | 49 villes |
| **Villes pop. ≥ 2 000 hab. (J0)** | 3 | **1 seule** (monopolaire) | **5** (multipolaire) | **5** (multipolaire) |
| **Villes pop. ≥ 1 000 hab. (J0)** | 12 | 8 | 16 | 16 |
| **Villes pop. ≥ 500 hab. (J0)** | **20** | 26 | 28 | **36** |
| **Ratio pop. top 1 / pop. top 2** | 1,19 (3 493 / 2 931) | **1,72** (3 227 / 1 870) | 1,18 (3 946 / 3 338) | 1,19 (3 702 / 3 102) |
| **Profit/an AIR en fin d'année 1 (1970)** | 430 598 £ | 288 188 £ | 457 766 £ | 482 758 £ |
| **Trésorerie / Dette fin d'année 1 (1970)** | 56 k£ / 300 k£ | 88 k£ / 300 k£ | 112 k£ / 300 k£ | 97 k£ / 300 k£ |
| **Aéroports déjà ouverts au 1er janv. 1971** | 12 | 13 | 16 | 14 |
| **Vivier de villes restantes pop. ≥ 500** | **8 villes restantes** | 13 villes restantes | 12 villes restantes | 22 villes restantes |

---

### 3.2 Distinction stricte : cause structurelle vs conséquence de trajectoire

Pour éviter le piège méthodologique consistant à transformer des métriques terminales en faux prédicteurs :

1. **Ce qui est une conséquence de trajectoire (non utilisable comme critère amont) :**
   - Le profit terminal 1972 (`profit_year`).
   - Le nombre final d'avions (37 vs 50 vs 79 vs 84).
   - Les retards moyens observés en vol (`C121_HUB_DELAY` terminal).
   - L'activation tardive de routes ou de lignes de train en 1972 pour occuper le cash résiduel.
2. **Ce qui constitue un signal causal observable AMONT :**
   - **La profondeur du vivier urbain résiduel :**  
     Si le nombre de villes viables restantes avec pop. ≥ 500 est très faible (graine 17, seulement 8 villes non desservies au début de 1971), brider les hubs à 2 routes condamne l'IA à ouvrir des aéroports dans des villages non viables.
   - **La polarité urbaine (monopolaire vs multipolaire) :**  
     Dans une carte monopolaire comme 781335 (une seule ville au-dessus de 2 000 hab., ratio top1/top2 = 1,72), le cap 2 empêche le hub principal d'aspirer tout le capital pour des spokes marginaux et force le développement d'un réseau secondaire.
   - **La contrainte physique de l'infrastructure disponible en 1970 :**  
     En 1970–1972, l'API NoAI ne dispose que de l'aérodrome de base (`AT_SMALL`) à piste unique et 2 postes de stationnement. Un cap à 4 routes sur une piste unique engendre mathématiquement un risque de congestion critique si les routes sont fortement fréquentées.

---

### 3.3 Lucidité méthodologique : ce qui est anecdotique sur un échantillon de 4 graines

> [!WARNING]
> **Aucun classifieur prédictif ne peut être validé scientifiquement sur 4 graines.**

L'analyse montre sans ambiguïté :
- **L'instabilité temporelle des classements :** Sur ces 4 graines, 3 ont changé d'optimum entre le test du 07/10 et le rejeu du 12/10 en raison des évolutions du code AIR (`v93`, `v138`, `AC04-B/AC05/AC06 v2`). Ce fait prouve que l'optimum de cap n'est pas une constante physique pure de la graine, mais une résultante chaotique couplée au code de planification.
- **Le danger du surapprentissage (overfitting) :** Avec N=4, on peut corréler n'importe quelle métrique (population médiane, ratio de drainage, trésorerie) avec un classement donné. Cette corrélation serait un artefact statistique.
- **La robustesse du défaut actuel (`air_hub_max_routes = 3`) :**  
  Sur la graine 17, Cap 3 est 1er.  
  Sur la graine 1, Cap 3 est 1er.  
  Sur la graine 802204, Cap 3 est 2e très proche du 1er et évite le désastre de Cap 4.  
  Sur la graine 781335, Cap 3 assure un profit très solide (1,65 M£/an).  
  Le compromis `air_hub_max_routes = 3` adopté le 07/10 évite à la fois le tarissement précoce du Cap 2 dans les petits viviers (graine 17, graine 1) et l'engorgement dévastateur du Cap 4 sur les pistes uniques (graine 802204).

---

## 4. Synthèse et recommandations

1. **Conservation absolue du défaut `air_hub_max_routes = 3` :**  
   Aucune modification statique du cap par défaut n'est justifiée. Le Cap 3 reste le meilleur compromis robuste en l'état actuel du jeu en 1970–1972.
2. **Rejet de toute heuristique dynamique basée sur ces 4 graines :**  
   Ne pas introduire de sélecteur dynamique de cap basé sur les seuils de population ou de vivier sans un protocole pré-enregistré complet à 40 graines × 3 ans.
3. **Respect strict des périmètres :**  
   Aucun composant touchant au catalogue AIR ([ai/OpexAI/air_catalog_c121.nut](../ai/OpexAI/air_catalog_c121.nut)), à l'économie AIR ([ai/OpexAI/air_economics_c121.nut](../ai/OpexAI/air_economics_c121.nut)) ou à la découverte des hubs dans [ai/OpexAI/air_planning.nut](../ai/OpexAI/air_planning.nut) n'a été altéré ou proposé à la modification.

---

## Note de relecture (Claude, 12/10)

- La référence cap 3 est identique au bit près dans les deux campagnes : sur ce code, le rejeu est déterministe. Les inversions de classement par rapport au 07/10 viennent donc du **code** (V93, V138, C121 hub direct, V141, AC04-B/05/06 v2), pas du bruit.
- Agrégé sur 4 graines : cap 2 −77 k£/an (2 V/2 D), cap 4 −60 k£/an (**0 V/4 D**). Le cap 4 retrouve la congestion de piste (`C121_HUB_DELAY` moyen 13,6 j contre 2,8 j sur 802204).
- **Décision : piste close.** Cap 3 maintenu ; pas de cap dynamique, l'optimum par graine n'est pas stable d'un code à l'autre et 4 graines ne fondent aucun signal amont.
