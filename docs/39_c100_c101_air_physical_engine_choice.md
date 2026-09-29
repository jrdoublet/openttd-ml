# C100/C101 — physique AIR et choix moteur

## Objet

Fermer la piste ouverte par C98 : `AIEngine.GetMaxSpeed()` est deja exprime avec
`vehicle.plane_speed`, donc l'ancien `/4` d'Opex n'est pas physiquement correct.
L'objectif etait de voir si une cinematique AIR plus realiste permettait de
mieux classer les moteurs sans revenir aux seuils de richesse fixes d'AAAHogEx.

Les reglages restent tous a **0 par defaut** : `c99_air_speed_api_fix`,
`c100_air_trip_physical`, `c101_air_physical_engine_choice` et
`c103_air_c100_rank_replay`.

## C100.1 — cinematique physique corrigee

Sur le diagnostic C98 3 graines x 4 ans : profit reel/predit par avion median
**0,777x**, revenu **0,773x** ; `newpair` ~**0,77x**, `hubsite` ~**0,79x**,
`hubhub` ~**0,82x**. A **1 avion**, le modele est presque calibre (~**0,99x**),
mais a **3 avions** il tombe a ~**0,53x** : le residu dominant est donc la
congestion / demande / rating sur les hubs partages.

Le causal 5x6 `c100_1b_air_trip_physical_vs_default_5x6_20260926` rejette la
variante : `profit_year` **-184,4 k£/an** moyen, median **-244,7 k£**, **1/4**,
`p=0,375`; `company_value` **-11,17 %**. Le premier C100, plus pessimiste sur le
temps aeroport, avait au contraire donne environ **+233 k£/an**. L'analyse du
bundle fige ci-dessous montre que ce signal ne doit pas etre reduit a « moins de
projets » : il modifiait surtout la valeur marginale de la vitesse, le mix moteur
et, simultanement, l'economie retournee au portefeuille.

## C101 — physique uniquement pour choisir le moteur

C101 exige que chaque moteur reste viable sous l'economie historique, classe
les moteurs avec C100.1, puis retourne l'economie historique du moteur gagnant.
Admission, capital et score projet gardent donc leur semantique historique.

### C101a — profit physique maximal

Smoke seed 42, 3 ans : **-751,9 k£/an**, valeur **-56,23 %**, flotte AIR
**51 -> 25 avions**, aeroports **22 -> 12**.

Sonde sur 2 957 bascules C68 -> C101 : prix median **3,95x**, capital **2,61x**,
**73,99 %** des bascules prennent plus de capital, profit historique median
**0,845x**, et **100 %** des bascules reduisent le profit historique. Transition
dominante : **LB-10 (223) -> Yate Haugan (218)**.

### C101b — ROI relatif >25 %, sinon profit

Pour eviter les seuils absolus de caisse, le comparateur a repris un arbitrage
relatif ROI/profit. Il sur-corrige vers les petits appareils : 4 470 bascules,
prix median **0,633x**, capital **0,716x**, profit historique **0,529x** ; seules
**0,72 %** des bascules prennent plus de capital, mais **100 %** reduisent encore
le profit historique. Transitions dominantes : `218 -> 217`, `223 -> 217`, puis
`217 -> 216`.

Smoke seed 42, 3 ans : **-492,2 k£/an**, valeur **-40,91 %**, flotte AIR
**51 -> 41 avions**, aeroports **22 -> 18**. L'amplitude suffit a ne pas lancer
de 5x6.

## Premier C100 positif vs C100.1 — difference mathematique exacte

Les bundles figes sont ceux de
`c100_air_trip_physical_vs_default_5x6_20260926` et
`c100_1b_air_trip_physical_vs_default_5x6_20260926`. Le chooser C68 est le meme
dans les deux : **argmax `profitAnnual`**, puis `roi` uniquement en departage.
`OpexAirEconomics` conserve aussi la meme chaine : temps de trajet -> rotations
et capacite mensuelle -> headway/rating -> revenu -> running/amortissement ->
profit, avec immobilisation seulement dans le ROI. La bascule 216/217 vers
218/219 ne vient donc pas d'un nouveau comparateur ROI/capital.

La difference est le cout de manoeuvre passe a `OpexAirTripModel` :

- premier C100 : `OpexAirManeuverDays`, roulage borne a `min(v,150)` puis encore
  divise par `vehicle.plane_speed`, et proxy sol egal a tout `W+H` des deux
  aeroports ;
- C100.1 : roulage borne a `min(v,50)` **sans** seconde division, et proxy sol
  reduit a **2/3** de `W+H`.

Avec `vehicle.plane_speed=4`, 74 ticks/jour et deux grands aeroports 6x6, pour un
jet assez rapide : le premier C100 donne environ **22,14 j** de roulage +
**4,05 j** vertical = **26,19 j par sens** ; C100.1 donne **11,07 + 4,05 =
15,13 j**. Le premier C100 ajoute donc ~**11,1 j fixes par sens**. Cet overhead
commun reduit l'elasticite du temps total a la vitesse de croisiere : le surcroit
de vitesse de 218/219 rapporte moins de rotations/rating/revenu relativement a
leur capital, ce qui maintient davantage 216/217.

Ce mecanisme cadre avec les flottes 1975 deja mesurees : premier C100 ~**85 %**
de 216/217 et ~**102,8 avions**, contre ~**62 %** de 216/217 et ~**80,8 avions**
pour C100.1. Le premier C100 conserve presque autant de lignes que le defaut et
meme davantage d'aeroports ; le signal ne vient donc pas d'une simple coupure de
l'expansion.

## C103 — replay du classement du premier C100 uniquement

Pour isoler causalement ce signal sans presenter l'ancien temps de manoeuvre
comme une physique correcte, `c103_air_c100_rank_replay` (defaut **0**) rejoue
exactement le classement du premier C100 : vitesse NoAI directe + ancien helper
de manoeuvre pessimiste. Seul ce score sert a choisir le moteur ; l'objet
economique retourne au portefeuille est l'economie **legacy** du moteur choisi.
Aucun seuil de richesse/caisse, aucun EngineID et aucun filtre capital absolu ne
sont ajoutes.

Tests cibles + campaign freeze : **24 tests OK, 1 skip** en Docker ;
`git diff --check` propre.

Smoke causal seed 42 x 3 ans : **rejet net**, donc aucun 5x6 lance :

- `profit_year` : **1 110 296 -> 720 540 £/an**, soit **-389 756 £/an** ;
- `company_value` : **2 123 173 -> 1 548 896 £**, soit **-27,05 %** ;
- avions AIR : **46 -> 42**, aeroports **19 -> 13** ;
- flotte totale : **75 -> 51**, constructions tracees **58 -> 44** ;
- mix 216/217 : **22/46 = 47,8 % -> 32/42 = 76,2 %**.

C103 atteint donc bien la direction de mix recherchee, mais **sans reproduire le
gain economique** : le chooser seul contracte fortement l'expansion. Le +233 k£
du premier C100 depend donc du **couplage** entre son classement moteur et
l'economie C100 utilisee pour scorer/admettre les routes, pas du seul argmax
moteur.

Le diagnostic C98 3x4 utilise les memes graines `42/100/999` dans les deux
bundles et montre aussi une divergence de structure : le premier C100 compte
**90** observations de lignes matures (`26 hubhub / 43 hubsite / 21 newpair`),
contre seulement **48** sous C100.1 (`4 / 26 / 18`). Ce n'est pas une mesure
causale de rendement par type de plan, mais cela confirme que la difference de
timing modifie fortement la propagation du reseau, surtout les extensions de
hubs, et pas uniquement le moteur choisi sur une route fixe.

## C114 — replay complet du premier C100

Le replay complet est expose sous `c114_air_c100_full_replay` (defaut **0**).
Il rejoue l'ancien timing dans toute `OpexAirEconomics` : **choix moteur,
admission/scoring, capital et flotte**. C'est un outil causal uniquement ; le
timing historique de ~26 j/sens reste physiquement faux et ne doit pas etre adopte.

Resultats : smoke seed42 x3 **+333,2 k£/an**, valeur **+37,8 %** ; 5x6
**+170,9 k£/an**, median **+187,6 k£**, **4/1**, `p=0,375` ; 20x10
`c114_c100_full_replay_20x10_20260927` : **+194 978 £/an** moyen, median
**+223 009 £**, **12/8**, `p=0,503445`, IC95 **[-11 797 ; +401 753] £/an**,
valeur **+22,70 %**, verdict **`fail_primary`**.

Le 20x10 retrouve donc l'ordre de grandeur historique des ~**+233 k£/an**, mais
avec une heterogeneite trop forte pour adopter C114 tel quel. Le mix 216/217 passe
d'environ **76,1 % a 83,1 %**, la flotte AIR moyenne **119,6 -> 117,1** et les
aeroports **24,3 -> 26,8**.

`sweeps/analyse_c114_seed_split.py` montre que les **12 gagnants** partent d'un
reseau plus petit (**1,67 M£/an, 116 avions, 22,7 aeroports**) et C114 leur ajoute
~**3,9 aeroports**, pour **+485,7 k£/an** final moyen. Les **8 perdants** partent
deja a **2,25 M£/an, 125 avions, 26,8 aeroports** ; C114 n'ajoute que **+0,4
aeroport**, reduit la flotte a **114,8 avions** et la capacite pax d'environ
**13 879 -> 9 973** (~**-28 %**), pour **-241,1 k£/an**.

Interpretation : le vieux timing agit comme un **regulariseur de capital** utile
pendant l'expansion, nuisible quand le reseau est deja mur.

## C104 — cout marginal des gros moteurs

La comparaison route par route confirme ce mecanisme. `217 -> 218` (776 cas) prend
un capital median **2,86x** pour ~**18,2 k£/an** de profit physique median en plus,
avec un rendement marginal ≈**29,3 %** du ROI du 217. `223 -> 218` prend **2,61x**
de capital pour ~**28,9 k£/an**, rendement marginal ≈**26,3 %** du ROI de base.
`216 -> 218` monte typiquement a ~**5x** de capital pour ~**3,5 k£/an** de gain.

## C115 — replay conditionne par le goulot de capital

`c115_air_c100_capital_replay` est passe a **1 par defaut temporairement** par
decision utilisateur du 2026-09-27, en attendant une regle marginale C116 plus
propre. Il reutilise
`K_dec = flux operationnel F × temps moyen tau entre decisions/constructions` de C69.
Pour chaque route : calculer le vrai gagnant C68 ; si `K_dec >= capital_C68`, garder
C68 ; si `K_dec < capital_C68`, utiliser le replay C100. Aucune constante de richesse,
aucun seuil de caisse, d'annee ou d'EngineID.

L'audit avant banc a trouve un branchement incorrect : la premiere implementation
comparait `K_dec` au `selectedEconomics.capital` de l'appareil d'entree de
`OpexAirChooseRoutePlaneFull`, avant la boucle C68. C115 recalcule desormais
explicitement l'argmax C68 via `OpexC104BestAirEngine(..., mode=0)` avant le test.
Les tests C115, C100, C104, C114 et le selftest C66.4 passent.

Mesures corrigees du 2026-09-27 :

- smoke seed42 ×3 : **+262,6 k£/an**, valeur **+25,4 %** ;
- 5×6 : **+167,5 k£/an**, mediane **+129,2 k£**, **4/1**, valeur **+13,6 %** ;
- 20×10 canonique `c115_c100_capital_replay_20x10_20260927_corrected` :
  **+154,9 k£/an** moyen, mediane **+141,8 k£**, **13/7**, `p=0,263176`,
  IC95 normale **[-92,2 ; +402,0] k£/an**, valeur **+18,29 %**. C66.4 rend
  `fail_primary` : le seuil moyen utile et la garde valeur passent, pas le test de signes.

C115 ameliore nettement le principal defaut de C114. Sur les huit graines que C114
faisait toutes perdre (`100, 7, 17, 314, 1024, 12345, 424242, 8675309`), le delta
moyen passe de **-241,1** a **-57,8 k£/an**, avec **4/4** au lieu de 0/8. La flotte
AIR devient en moyenne **+4 avions** au lieu d'etre sous-dimensionnee et la capacite
pax moyenne ne baisse plus que d'environ **7 %** (`15 361 -> 14 257`), contre ~28 %
sous C114. Les pertes residuelles fortes sont surtout `314`, `424242` et `8675309`.

En contrepartie, sur les douze anciennes graines gagnantes de C114, C115 conserve
**+296,7 k£/an** en moyenne, soit environ **61 %** des +485,7 k£/an de C114, avec
9/3 et +3,58 aeroports. Conclusion : le gate sur le capital total est un vrai pas
vers le mecanisme recherche, mais il reste trop grossier et C115 ne doit pas etre
adopte. Analyse reproductible : `sweeps/analyse_c115_seed_split.py`.
