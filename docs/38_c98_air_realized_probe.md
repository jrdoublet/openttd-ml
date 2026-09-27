# C98 — biais du modèle AIR : prédit contre réalisé par moteur

**Date : 2026-09-26.**  
**Statut : sonde passive terminée ; aucune modification comportementale adoptée.**

## But

C97 a montré qu'un nouveau critère de classement ne suffit pas : C68 maximise déjà le profit
**prédit** à un avion, alors que le symptôme est un profit **réalisé** par avion inférieur à
AAAHogEx. C98 mesure donc le biais du modèle lui-même avant toute nouvelle règle de choix moteur.

La sonde `c98_air_realized_probe` est à défaut `0`. Elle est exécutée au rapport annuel existant
et ne participe ni au choix d'aéroport, ni au choix d'avion, ni au portefeuille. Elle relève par
ligne AIR : moteur, distance, flotte prédite/réelle, profit et revenu prédits/réalisés, coûts,
ratings, charge pax/mail, vitesse instantanée et caractéristiques du moteur.

`profit_last_year` est une mesure annuelle. Charge, vitesse et état du véhicule sont des
instantanés au jour du rapport ; ils ne sont pas interprétés comme une cadence annuelle. NoAI
n'expose pas directement le nombre annuel de rotations par ligne.

## Diagnostic principal — défaut courant, 3 graines × 4 ans

Artefact : `results/diag_c98_air_realized_3x4_20260926_v2.json`.

Base d'analyse : **66 observations matures**, dont la capacité du moteur courant correspond encore
à celle mémorisée à la construction.

- profit réalisé / profit prédit par avion : médiane **1,376×** ;
- revenu réalisé / revenu prédit par avion : médiane **1,282×** ;
- profit réalisé − prédit : médiane **+16,1 k£/an/avion** ;
- rating prédit : **12,75 %** sur toutes les observations ;
- rating réel : médiane **57 %** ;
- charge pax instantanée : médiane **14,7 %** ;
- charge mail instantanée : médiane **65 %** ;
- capacité mail / capacité pax : médiane **18,18 %**.

Le biais n'est pas uniforme selon le moteur. Sur les moteurs suffisamment exposés :

| Moteur | n | médiane réalisé/prédit, profit/avion |
|---|---:|---:|
| FFP Dart (217) | 4 | **2,15×** |
| Bakewell Luckett LB-10 (223) | 34 | **1,66×** |
| Darwin 200 (227) | 5 | **1,34×** |
| Darwin 300 (228) | 22 | **1,16×** |

Cela explique pourquoi un simple argmax C68 peut favoriser différemment les moteurs : le modèle
ne leur applique pas le même biais effectif une fois en service.

## Erreur de vitesse confirmée

`OpexAirTripModel` historique redivise `AIEngine.GetMaxSpeed()` par `4`. Or le diagnostic physique
`diag_airport_delay_engine` montre que NoAI 15.3 expose déjà la vitesse avec
`vehicle.plane_speed` appliqué.

Vérification indépendante 2 graines × 3 ans : **200 trajets observés**,
`results/diag_airport_delay_engine_c98check_2x3_20260926.json`.

- avec la vitesse API directe, le résidu temps observé − temps de vol reste positif, typiquement
  **~12–16 jours** selon le moteur ;
- avec la division historique `/4`, le résidu médian devient **−33 à −63 jours** selon le moteur,
  ce qui est physiquement impossible.

La vitesse historique est donc bien fausse. Mais elle compense d'autres erreurs du modèle.

## Pourquoi le correctif de vitesse seul n'est pas adoptable

Le bras expérimental C99 présent localement (`c99_air_speed_api_fix=1`, défaut `0`) a été mesuré
avec la même sonde C98, 3 graines × 4 ans :
`results/diag_c98_air_realized_c99_3x4_20260926.json`.

Sur **40 observations matures** :

- profit réalisé / prédit par avion : médiane **0,425×** ;
- revenu réalisé / prédit par avion : médiane **0,442×** ;
- biais médian de profit : **−64,8 k£/an/avion** ;
- rating prédit : médiane **32,35 %**, rating réel **53 %**.

Donc corriger seulement la vitesse fait passer le modèle d'une sous-prévision modérée à une
**sur-prévision massive**. C99 seul ne doit pas devenir le défaut.

Le contre-factuel hors comportement confirme aussi que la vitesse ne suffit pas : sur les lignes
du défaut, vitesse API directe + délai historique de 3 jours ne donne qu'un rating théorique médian
de **22,55 %**, toujours très loin des **57 %** observés. L'ancre de rating utilisée par
`OpexStationRatingForHeadway` est donc elle aussi trop pessimiste pour ces lignes.

## Courrier : écart structurel avec AAAHogEx

Le 5×6 historique `results/diag_air_engine_mix_vs_aaa_5x6_20260924.json` contient les capacités
réelles par moteur. L'analyseur `sweeps/analyse_air_engine_stats.py` montre deux différences utiles :

- Opex concentrait **73,3 %** de ses avions sur l'engine 217 dans ce relevé, contre un mix AAAHogEx
  beaucoup plus distribué ;
- AAAHogEx alloue souvent beaucoup plus de capacité au courrier. Sur l'engine 228, le snapshot
  agrégé est d'environ **221 pax + 129 mail** par avion chez AAAHogEx, contre **300 pax + 50 mail**
  chez Opex, soit ~58 % de mail relativement aux sièges pax chez AAAHogEx contre ~17 % chez Opex.

Ce signal concorde avec C98 : les sièges pax sont souvent peu occupés alors que la soute mail est
souvent proche de la saturation. Le forfait historique de revenu mail de C68 (15 %) et l'absence
d'un choix explicite de répartition pax/mail sont donc des suspects de premier rang.

## Conclusion et suite

Ne pas créer une nouvelle règle de choix moteur à partir du modèle actuel et ne pas adopter C99
isolément. Le prochain modèle AIR doit être cohérent **en bloc** :

1. vitesse `AIEngine.GetMaxSpeed()` utilisée à l'échelle NoAI, sans second `/4` ;
2. temps de rotation/d'aéroport calibré sur les trajets réellement observés ;
3. rating recalibré sur les lignes réelles au lieu de l'ancre fixe actuelle ;
4. capacité et revenu mail explicitement liés au refit/capacité réelle, pas à un forfait unique ;
5. seulement ensuite, refaire le choix moteur sur profit calibré et vérifier le profit réalisé par
   avion avant un 5×6 causal.

La priorité n'est donc plus « trouver un autre argmax », mais **corriger la fonction économique que
C68 optimise**.
