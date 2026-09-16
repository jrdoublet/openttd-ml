# AIR — variante comportementale de fréquence de collecte

**Date : 2026-09-15.**
**Statut : test terminé, variante rejetée et comportement de référence restauré.**

Cette expérience part de la base early_slot, définitivement adoptée. Elle ne
réouvre ni son choix ni les diagnostics précédents.

## 1. Hypothèse testée

Le diagnostic STNN.goods avait montré que le verrou principal n'était pas un
mauvais rating général : Opex passe même souvent plus récemment qu'AAAHogEx,
mais capte beaucoup moins de cargo.

La demande utilisateur était néanmoins de tester une première variante
comportementale minimale visant explicitement la **fréquence de collecte**.

L'hypothèse testée était :

> certaines lignes AIR à un avion gagneraient à recevoir un deuxième appareil
> plus tôt, avant d'atteindre une capacité complète de cargo en attente, si ce
> deuxième avion améliore réellement le palier de fréquence/rating.

## 2. Mécanisme expérimental

Un bras air_frequency_boost=1 a été ajouté temporairement, avec défaut à 0.

Le garde-fou W n'était **pas supprimé**. L'exception ne pouvait s'appliquer que
si toutes les conditions suivantes étaient vraies :

- exactement **1 avion** sur la ligne ;
- profit réalisé strictement positif ;
- cargo réellement présent dans au moins un endpoint ;
- place physique pour un deuxième avion ;
- le passage de 1 à 2 avions améliore un palier de
  OpexPickupRatingPoints(headwayDays).

Le headway était calculé avec le modèle AIR existant OpexAirTripModel, à partir
du modèle d'avion déjà exploité sur la ligne.

Même lorsqu'elle était éligible, l'exception ne pouvait proposer qu'**un seul
avion supplémentaire**. Le projet restait ensuite soumis au portefeuille ROI,
au cap physique d'aéroport, au prix réel de l'avion de la ligne et aux gardes
de trésorerie existantes.

Le code expérimental n'est plus dans le comportement livré. Il reste
reproductible dans le bundle gelé de la campagne :

results/diag_air_frequency_boost_5x6_v1_bundle/

## 3. Neutralité du défaut

Avant le test, le nouveau flag à 0 a été vérifié sur seed 42 × 3 ans.

Le résultat reproduit exactement la référence early_slot :

- company value : **1 563 115 £** ;
- profit annuel : **753 646 £/an**.

## 4. Smoke apparié seed 42 × 3 ans

Critères fixés avant résultat :

- métrique primaire : profit_year ;
- gain utile minimal : **+50 k£/an** ;
- garde-fou company value : **pas plus de −5 %**.

Résultat du smoke :

- profit annuel : **+26,9 k£/an** ;
- company value : **+2,89 %** ;
- verdict C66 : fail_primary.

Le smoke était donc légèrement positif mais sous le seuil utile. Il justifiait
le passage au diagnostic 5×6 demandé, pas une adoption.

## 5. Diagnostic apparié 5 seeds × 6 ans

Seeds : 42, 100, 999, 1234, 5678.

Résultat économique :

- delta moyen de profit annuel : **−123,7 k£/an** ;
- delta médian : **−126,2 k£/an** ;
- victoires/défaites : **0/5** ;
- intervalle 95 % du delta : **[−218,8 k£ ; −28,6 k£]** ;
- ratio des moyennes de company value : **0,9288**, soit **−7,12 %** ;
- verdict C66 : **fail_primary_and_value_guard**.

Le signal est donc négatif et cohérent sur les cinq seeds. Conformément au
protocole, **aucun 20×10 n'a été lancé**.

## 6. La variante améliore bien la fréquence physique

La défaite économique ne vient pas d'une variante inactive.

En 1975, télémétrie AIR Opex :

| Métrique | Référence early_slot | Variante fréquence |
|---|---:|---:|
| lignes AIR | 158 | 156 |
| avions / ligne | 1,013 | **1,058** |
| rating moyen | 139,2 | **144,3** |
| time_since_pickup moyen | 5,84 j | **4,51 j** |
| max_waiting_cargo moyen | 9,46 | **6,23** |
| profit / capacité | **66,3 £** | **53,1 £** |

La variante obtient donc exactement l'effet recherché : davantage d'avions par
ligne, collecte plus fréquente, rating légèrement meilleur et moins de cargo
accumulé entre deux passages. Mais le **profit par unité de capacité baisse
d'environ 20 %**.

Au niveau seed, le profit/capacité 1975 baisse sur **5/5 seeds**.

## 7. Refus W et achats

Un probe C50 a été lancé sur les mêmes 5 seeds × 6 ans, référence et variante.

Cumuls 1970–1975 :

| Mesure | Référence | Variante |
|---|---:|---:|
| refus W | 4 806 | **4 566** |
| avions AIR ajoutés | 20 | **28** |

La variante réduit donc les refus W d'environ **5 %** et augmente les achats AIR
de **40 %**.

Ces chiffres sont des diagnostics C50 séparés et servent à confirmer le
mécanisme physique ; l'arbitrage économique repose sur le banc C66 apparié.

## 8. Conclusion

La piste « fréquence de collecte » est **écartée comme levier économique**.

Opex peut effectivement augmenter sa fréquence et son rating en renforçant plus
tôt ses lignes à un avion, mais cette capacité supplémentaire rapporte moins
qu'elle ne coûte en opportunité de capital.

W protège donc en grande partie une allocation de capital qui reste meilleure
que le renforcement anticipé.

## 9. Prochaine priorité

La priorité revient au mécanisme situé **en amont de W** :

**catchment / placement AIR**.

Les diagnostics établis auparavant restent valides :

- à même TownID et mêmes cargos, AAA voit beaucoup plus de max_waiting_cargo
  par unité de capacité ;
- cet écart persiste à un seul avion et à distance comparable ;
- le rating et la fréquence ne ferment pas l'écart ;
- renforcer artificiellement la fréquence dégrade la valeur.

Le prochain diagnostic doit donc comparer passivement le type et la taille
d'aéroport, le rayon/catchment réel, la position dans la ville, la population
ou production passagers-courrier couverte et, si possible, l'écart entre
production locale disponible et cargo réellement attribué à la station.

early_slot reste la base définitive et ne doit pas être rouvert.
