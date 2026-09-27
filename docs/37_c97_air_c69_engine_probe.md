# C97 — choix moteur AIR par score C69 sur moteur × profondeur

État au 2026-09-26 : **sonde passive implémentée ; traitement causal non ouvert**.
Le réglage `c97_air_c69_engine_probe` reste à `0` par défaut. Aucun
`c97_air_c69_engine_choice` n'est créé à ce stade.

## Question testée

C97 ne répète ni C72 ni V92.2. Pour chaque moteur compatible `e` et chaque
profondeur plausible `n`, il évalue directement :

```text
score(e,n) = P_calibre(e,n) * 1000 / max(C_portefeuille(e,n), K_dec)
```

L'argmax est donc fait sur **chaque couple `(e,n)`**. En particulier C97 ne fait
pas : « choisir pour chaque moteur le `n` qui maximise le profit, puis appliquer
le score C69 » ; ce dernier mécanisme correspond à V92.2 et a déjà été rejeté.

Le point exact `(e,n)` est obtenu avec `OpexAirEconomics(... fixedPlanes=n,
serviceScan=false)`. Le capital et le profit calibré ne sont pas redéfinis : un
plan virtuel est envoyé dans `OpexProjectFromAir`, puis dans
`OpexProjectFinanceCapital` et `OpexCalibratedProfit`. C97 réutilise ainsi
exactement la marge AIR, `immobilise` et la calibration C70/C82 du portefeuille.

La sonde est appelée seulement sur les plans AIR positifs déjà produits par le
comportement courant. Sa valeur de retour n'alimente ni
`OpexAirChooseRoutePlane*`, ni le plan, ni le portefeuille. Elle journalise
`C97_ENGINE` avec le moteur C68 réel, le meilleur couple C97, `K_dec`, profits,
capital, score, prix et capacité.

## Validation déterministe

- `sweeps.test_c97_air_c69_engine` : **6/6** ;
- régressions C84/C85/M3 + gel campagne : suite ciblée **39/39** ;
- `git diff --check` : propre.

Le test anti-régression V92 construit explicitement un cas où la réduction
« meilleur profit par moteur puis score » choisit A, alors que l'argmax direct
sur tous les `(e,n)` choisit B ; C97 est contraint au second comportement.

## Diagnostic passif

Smoke Docker graine 42 × 1 an :
`results/smoke_c97_probe_1x1_20260926.json`.

Diagnostic retenu : 3 graines (`42, 100, 999`) × 1 an, 3 workers / 3 CPU :
`results/diag_c97_air_c69_engine_3x1_20260926.json`.

- événements uniques : **3 587** ;
- désaccords C68/C97 : **2 570 / 3 587 = 71,65 %** ;
- `n*` tous cas : 1 = 2 161, 2 = 487, 3 = 916, 4 = 19, 5 = 4 ;
- delta profit prédit C97 − C68 : moyenne **+9,27 k£/an**, médiane **+1,32 k£/an** ;
- delta capital portefeuille : moyenne **−53,6 k£**, médiane **−55,4 k£** ;
- delta score C69 : moyenne **+165,5**, médiane **+152,0** ;
- moteur moins cher : **2 568 / 2 570 = 99,92 %** ; moteur plus cher : **0** ;
- capacité plus petite : **65,10 %** des désaccords ; plus grande : **34,36 %** ;
- delta de profit prédit **par avion** : moyenne **−14,66 k£/an**, médiane
  **−13,46 k£/an**, maximum **−15 £/an** ; donc **0/2 570** désaccords améliorent
  le profit prédit par avion.

Le signal suit la transition attendue du score C69 : quand `K_dec < 0,5 × C_defaut`,
le taux de désaccord est **79,87 %** ; entre `0,5C` et `C`, il tombe à **29,47 %** ;
dès que `K_dec >= C`, il devient très faible (3/59 entre `C` et `2C`, 0/5 au-delà).

Un 3×3 a été tenté puis arrêté : le volume de télémétrie du scan complet
moteur×n rendait le post-traitement disproportionné pour une sonde courte. Le
3×1 couvre trois graines et suffit à établir l'exposition.

## Décision

L'exposition est **substantielle**, mais le second garde demandé pour ouvrir une
expérience causale n'est pas satisfait. Le problème de départ est le faible
profit AIR par avion face à AAAHogEx ; or C97 choisit presque toujours un moteur
moins cher et **n'améliore le profit prédit par avion dans aucun désaccord**.

À un avion, C68 maximise déjà le profit prédit, donc une autre sélection à
`n=1` ne peut pas améliorer ce même profit unitaire sans corriger le modèle.
C97 expose surtout une préférence capital/ROI, pas une erreur de productivité
par moteur.

Conséquence : ne pas implémenter `c97_air_c69_engine_choice` sous cette forme et
ne pas lancer de 5×6. La prochaine analyse doit chercher pourquoi le **profit
réalisé par moteur/avion** diverge de la prédiction (calibration, charge,
vitesse/cadence, courrier, utilisation réelle), plutôt que réordonner une
nouvelle fois les moteurs avec le même modèle prédit.
