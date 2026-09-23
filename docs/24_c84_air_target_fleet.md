# C84 — choix d'avion et profondeur de flotte AIR

État au 2026-09-23 : **non adopté**, défaut `0`. Le premier 5×6 a exposé une erreur de scoring
marginal des renforts. Le correctif live-marginal a été implémenté, smoke puis 5×6 proprement
mesurés ; il améliore le défaut architectural mais reste économiquement défavorable.

## 1. Problème observé

Le chemin AIR courant prend deux décisions successives sur le même service :

1. `OpexAirChooseRoutePlaneFull` choisit l'avion de la route avec `OpexAirEconomics` ; sous
   `FLEET_PORTFOLIO`, cette économie est volontairement bornée à **un avion initial**.
2. `_resizeAirFleets` décide ensuite la profondeur réelle à partir de l'attente en gare, du profit
   observé, de la cadence physique, de la trésorerie et de l'état de la ligne.

Le point fragile est la transition entre les deux. Une ligne créée avec un avion peut avoir un
premier exercice négatif alors que le même avion serait profitable à une fréquence supérieure.
Le garde `lastProfit < 0` interdit alors précisément l'achat qui permettrait d'atteindre cette
fréquence, même si une pleine capacité d'avion attend réellement en gare.

Les alternatives déjà mesurées ne justifient pas de complexifier davantage le choix du moteur :
C72 au ROI et au score C69 ont terminé leur 20×10 respectivement à −1,9 k£/an et −4,5 k£/an face
au profit maximal courant ; C82 (calibration réalisé/prédit par moteur) a donné +39,4 k£/an,
12/8, sous le seuil utile de +50 k£/an. C84 conserve donc volontairement le choix moteur C68.

Les antériorités ferment deux raccourcis : supprimer le garde d'attente `W` détruit le capital, et
supprimer le plafond de lot de quatre avions (`c69_fleet_demand_batch`) a été strictement inerte sur
5 graines × 6 ans. C84 ne touche donc ni au garde `W` ni au plafond physique de cadence.

## 2. Contrat retenu

Le réglage expérimental `c84_air_target_fleet` reste à `0` par défaut.

Sous `1` :

- le choix d'avion reste **exactement** celui de `OpexAirChooseRoutePlaneFull` ;
- une seconde évaluation du **même avion** calcule la profondeur la plus profitable avec le modèle
  `OpexAirEconomics`, en réutilisant les bornes déjà présentes avant la mise à un avion du
  portefeuille : 3 appareils pour une nouvelle paire à deux aéroports, 4 pour un petit aéroport
  réutilisé, 6 sinon ;
- le chantier initial reste **strictement à un avion** ; C84 ne crée aucune variante initiale
  multi-avions dans le portefeuille ;
- la profondeur est mémorisée dans `targetAirPlanes` pour les renforcements ultérieurs, ainsi que
  `airMonthlyPax`, la demande réconciliée après chantier et arrêts joints ;
- tant que `have < targetAirPlanes`, le premier garde de santé (`deadStreak == 1` ou
  `lastProfit < 0`) peut être franchi ; `deadStreak >= 2` reste bloquant ;
- le renfort doit toujours passer le stock réel en gare `W`, le plafond `OpexAirCadenceCap`, le
  cash et le chemin transactionnel `OpexAirAddPlane` ;
- le lot est en plus borné par `targetAirPlanes - have`. Une fois la cible atteinte, toute croissance
  ultérieure reprend strictement le comportement historique.

La croissance portefeuille n'est pas limitée à un avion : `_resizeAirFleets` produit déjà un
`entry.want` pouvant valoir plusieurs appareils et `_tryBuildFleetProject` boucle jusqu'à ce nombre,
sous réserve du cash à chaque achat. Le refleet après crash reste, lui, un remplacement unitaire d'un
appareil effectivement perdu ; il ne constitue pas le mécanisme normal de montée en flotte.

Les champs `targetAirPlanes` et `airMonthlyPax` sont des scalaires de ligne ; la projection
générique de `persist.nut` les sauvegarde et les restaure sans format spécial. Une ancienne
sauvegarde C84 pouvant posséder la cible sans `airMonthlyPax` échoue volontairement fermé pour
le scoring marginal : elle ne retombe jamais sur la prédiction linéaire à un avion.

## 3. Variante écartée pendant le prototypage

Le premier prototype utilisait aussi l'économie multi-avions pour choisir le moteur. Une
décomposition causale sur la graine 42 × 1 an l'a rejeté immédiatement :

| variante de développement | profit annuel | valeur | lecture |
|---|---:|---:|---|
| défaut | 269 731 £ | 282 125 £ | référence du smoke |
| choix moteur sur flotte cible seul | 132 480 £ | 148 813 £ | fortement défavorable |
| cible de flotte avec choix moteur courant | **307 943 £** | **380 637 £** | signal favorable |
| combinaison des deux | 104 713 £ | 121 046 £ | fortement défavorable |

Ces smokes ne constituent pas une preuve économique. Ils servent uniquement à isoler le mécanisme
à conserver avant le diagnostic plus coûteux. La branche de choix moteur sur flotte cible a été
retirée du code final C84.

Sur le smoke retenu, la différence physique va dans le sens recherché : **8 avions sur 8 aéroports**
contre **6 avions sur 9 aéroports** au défaut, avec capacité passagers AIR **2 240 contre 1 720**.
Le levier densifie donc les lignes existantes au lieu d'augmenter simplement le nombre d'aéroports.

## 4. Premier diagnostic 5×6 : signal défavorable, mais instructif

Campagne `results/diag_c84_air_target_fleet_5x6_20260923.json`, graines
`100 12345 42 7 999`, 6 ans, 10/10 parties complètes. Les seuils avaient été fixés avant lecture :
`profit_year` primaire, effet utile +50 k£/an, garde valeur −5 %.

Le prototype initial échoue :

- `profit_year` C84 − défaut : **−84,5 k£/an** en moyenne, médiane **−141,0 k£/an**, 2/3 ;
- valeur : **−321,6 k£** en moyenne, ratio des moyennes **−5,66 %** ;
- véhicules primaires : **−9,8** en moyenne ;
- note de gare médiane : **+1,1 point**.

Le signal temporel est plus utile que la moyenne seule : C84 passe de **+85,4 k£/an en 1972** à
**−134,5 k£/an en 1974**. La graine 100 finit avec 27 avions AIR de moins, 4 aéroports de moins et
une valeur inférieure de 1,42 M£. Ce n'est donc pas simplement « trop d'avions » : le capital bifurque
vers un portefeuille globalement plus petit après quelques renforcements.

Les métriques territoriales ne désignent pas C77/C83 comme cause directe : les builds/claims de
second créneau ne régressent pas matériellement et les monopoles AAA `(2,0)` baissent même en moyenne.
La campagne n'avait pas de `line_telemetry`, donc elle ne permet pas d'attribuer chaque achat à une
ligne précise.

Réserve protocolaire : `c67_matrix_bounded` tournait en parallèle sur le Docker partagé. Les 10/10
parties sont saines et le résultat est utile comme diagnostic, mais **pas comme qualification propre**.

## 5. Cause identifiée : le modèle qui ouvre le renfort n'était pas celui qui le classait

`task_report.nut` confirme que `lastProfit` est la somme réelle de `AIVehicle.GetProfitLastYear`
des appareils de la ligne. Les champs `predRevenue`, `predRunning` et `predTrains`, eux, sont copiés
du plan initial, donc de l'économie à **un avion** sous `FLEET_PORTFOLIO`.

Sous C84, `_resizeAirFleets` peut volontairement franchir un premier `lastProfit < 0` tant que la
ligne est sous `targetAirPlanes`. Mais `OpexProjectFromFleet` retombait alors sur :

```text
(predRevenue - predRunning) / predTrains
```

Ce nombre n'est pas le profit marginal du deuxième ou troisième avion. `OpexAirEconomics` est
non linéaire : `planes -> headway -> stationRating -> offered -> carried -> revenue`, puis retranche
les coûts d'exploitation **et l'amortissement**. Le fallback linéaire omettait en plus `predAmort`.
Le portefeuille pouvait donc surclasser artificiellement un renfort, consommer le capital et évincer
des lignes neuves pourtant plus créatrices de valeur.

Une première correction intermédiaire conservait une courbe cumulative calculée lors du sizing cible.
La revue a montré qu'elle pouvait déjà être obsolète : `OpexAirReconcileActualBuild` ajoute ensuite
la demande réellement captée par les arrêts joints et remplace l'économie du chantier.

La correction finale ne persiste donc aucune courbe. Après les gardes cadence, santé, plafond et
stock réel `W`, quand `_resizeAirFleets` connaît `want`, elle reprend **le même moteur vivant que
`OpexAirAddPlane`** et calcule deux points exacts :

```text
before = OpexAirEconomics(... fixedPlanes=have)
after  = OpexAirEconomics(... fixedPlanes=have+want)
profit_marginal  = after.profitAnnual  - before.profitAnnual
revenue_marginal = after.revenueAnnual - before.revenueAnnual
```

avec `newAirportCount=0`, donc uniquement l'économie incrémentale des avions. Chaque appel
`fixedPlanes` n'évalue qu'une profondeur et il n'y a ni scan d'équipement, ni pathfinder, ni
recherche de site. Le projet est rejeté si le marginal manque ou vaut `<= 0`. Hors de ce chemin,
le contrat historique reste inchangé.

## 6. Validation et mesures après correction

Validation finale : contrat C84 **6/6**, gel campagne **11/11**, M3 équipement **7/7**, B8 cycle de
vie **6/6**, `git diff --check` propre.

Smoke final, graine 42 × 1 an :
`results/smoke_c84_live_marginal_1x1_20260923.json` — sain, `profit_year=265 087 £/an`,
valeur `289 719 £`, 12 véhicules et 14 gares.

Un 5×6 intermédiaire, `diag_c84_marginal_5x6_20260923`, a été **écarté du diagnostic causal** :
une modification concurrente avait réintroduit un projet initial directement à `targetPlanes`.
Cette variante mélangeait deux interventions et donnait −191,9 k£/an, valeur −8,94 %. Le chemin
initial multi-avions a ensuite été retiré.

Le 5×6 final propre est
`results/diag_c84_live_marginal_5x6_20260923.json`, mêmes graines `100 12345 42 7 999`, 6 ans,
3 workers / 3 CPU / 2 Go, aucun conteneur concurrent au lancement, 10/10 parties complètes :

- `profit_year` : **−69,6 k£/an** en moyenne, médiane **−73,5 k£**, 2/3,
  p signes 1,0, IC95 **[−216,5 ; +77,3] k£/an** ;
- valeur : **−124,1 k£** en moyenne ; ratio des moyennes **−2,29 %**, donc garde −5 % respectée ;
- véhicules primaires : **−6,4** en moyenne ;
- note de gare médiane : **−1,0 point** en moyenne ;
- territorialement : slots Opex **+0,6**, villes Opex présentes **+0,6**, monopoles AAA `(2,0)`
  **−1,6**, villes partagées `(1,1)` **+1,2** en moyenne.

Par graine, les deltas `profit_year` sont : 100 **−73,5 k£**, 12345 **+47,1 k£**,
42 **−94,0 k£**, 7 **−330,8 k£**, 999 **+103,3 k£**. Le correctif architectural réduit donc la
perte moyenne du premier prototype (−84,5 → −69,6 k£/an) et remet la valeur dans la garde, mais
**ne transforme pas C84 en levier économique positif**.

## 7. Décision

C84 reste à **défaut 0** et aucun 20×10 n'est lancé : le diagnostic 5×6 propre échoue déjà le seuil
primaire de +50 k£/an. Cela ne démontre pas qu'une ligne AIR ne doit jamais recevoir plusieurs
avions ; cela montre que **forcer le franchissement du premier signal de mauvaise santé jusqu'à une
cible théorique** n'est pas un bon levier global, même lorsque chaque renfort est classé avec un
marginal cohérent.

Le prochain chantier avion doit être séparé de C84 : réduire le coût du **choix d'équipement par
route** (short-list dynamique / champions non dominés calculés au refresh catalogue), sans réouvrir
C72/C82 ni coder en dur des IDs ou seuils vanilla non vérifiés.
