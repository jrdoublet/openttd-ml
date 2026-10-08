# C121 : estimateur du flux passagers durable

Demande utilisateur du 07/10 : trouver un meilleur estimateur du flux passagers
a long terme, soupconne de surestimer la cible de flotte. Analyse et prototype
de prediction hors decisions avant toute modification comportementale.

## Audit et hypotheses

Reference adoptee `36fa8c7` : C121 economie/catalogue=1, dernier marginal
non positif interdit. Arbre local modifie preserve, dont correction adaptative
tous regimes et plafond additionnel OFF. Les anciennes qualifications sont
attachees a leur code et ne qualifient pas un nouvel estimateur.

Le flux actuel suit production mensuelle de ville x fraction de producteurs
couverts, allocation selon rating des stations Opex, partage des lignes selon
capacite/frequence, puis capacite physique. Le nombre de producteurs ne mesure
pas leur population. La production et les concurrents sont photographies a la
construction ; targetAirPlanes n'est pas un pronostic dynamique a dix ans.
La correction de realisation applique un facteur de RECETTES, incluant MAIL,
et non une estimation directe des passagers. L'adaptatif utilise seulement
25 % de l'ecart appris et ne corrige que hubsite/hubhub.

Sources moteur 15.3 verifiees : AIStationList ne voit que les gares propres et
AIStation.GetCargoRating ne peut pas lire les gares adverses. MoveGoodsToStation
alloue pourtant entre compagnies selon leurs meilleurs ratings, puis entre
gares d'une compagnie. L'absence d'AAA dans les buckets est donc une limite
structurelle ; son importance effective reste a mesurer. L'API compte des
producteurs, pas un volume mensuel par batiment.

- https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station_cmd.cpp
- https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_stationlist.cpp
- https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_station.cpp
- https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_tile.hpp

## Diagnostic pre-enregistre avant nouvelles parties

Une campagne passive, dix graines x dix ans, dix duels contre AAAHogEx, aucun
A/B comportemental. Graines fixes 42,100,7,999,2026,1,17,73,314,512. C121
economie/catalogue=1 et target_limit=0 ; autres defauts locaux courants. Sondes
existantes C117 throughput=1 et C98 realized=1 ; reconstruction mensuelle des
lignes depuis les saves. Aucun changement Squirrel pour cette collecte. La
sonde peut perturber le budget d'opcodes ; aucun resultat economique d'adoption
ne sera tire de ce diagnostic instrumente.

Campagne `c121_pax_flux_diag_10x10_20261007`, sortie neuve
`results/c121_pax_flux_20261007/diag/bench.json`. Docker desktop-linux local,
10 CPU/8g RAM+swap/10 workers, cache openttd-lab-home, montage /work. Image
attendue f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659.
Verifier absence de campagne concurrente et conserver manifestes/bundle/logs.
Budget maximum de cette etape : dix duels, 100 annees-parties, pas de relance
pour favoriser un resultat. Defauts inchanges, aucun commit/push.

Flux de validation : passagers transportes par C117 (somme des deux directions),
distinct de la demande non satisfaite. Les mois sans depart ne sont pas des
preuves de demande nulle. Exclure transitions non observees, ordres invalides,
moteurs melanges et changements de flotte pour les comparaisons stables.
Une ligne pleine donne une borne basse de demande, jamais une observation
complete du flux potentiel. Les populations de lignes sans renfort sont aussi
selectionnees : ne pas generaliser leurs ratios aux lignes saturees.

Prototypes hors ligne predefinis : modele de construction, dernier debit
observe sur 90/180/360 jours, et combinaison modele/observation par bras.
Pas de remise au gout du jour d'un facteur uniforme rejete. Fenetres de
prediction strictement passees, evaluation sur douze mois futurs, age>=2 ans,
flotte/moteur stables ; separer hubs stables et hubs ayant grandi.
Apprentissage sur 42,100,7,999,2026 ; validation tenue a part sur
1,17,73,314,512. Comparer erreur absolue ponderee par flux (WAPE), biais et
erreur par ligne et graine, couverture et censure. Les mois ne sont pas des
graines independantes. Un candidat sera seulement retenu pour une experience
si son erreur baisse sur validation et si le sens du biais ne s'inverse pas
fortement ; aucune qualification economique ou adoption par cette seule mesure.

Livrable : estimateur explicite, code de prediction hors ligne reproductible,
table actuelle/candidat sur validation et limites d'identification du flux
potentiel. Ensuite seulement envisager integration fantome et qualification
causale distincte si l'exposition est etablie.

## Résultats et décision

Dix duels complets et sains, Opex/AAA actifs au checkpoint 1979-12-01,
aucun failed_run. Bundle `1c08c84fb0b658eb997573fdd0f3347ab5cd78b0bcb1f1e4a2def0e1ad2704ff`,
manifeste `7be8f626e24df234a3eb38ddc1a3c29927aade0e6194606c9ce1e0aedf4d0fd1`.
La santé des parties ne qualifie pas automatiquement la mesure de flux.

31 334 fenêtres C117 uniques, 8 910 conformes aux critères de mesure.
**Aucune prévision annuelle complète** : 1 448 comparaisons exclues pour
mesure non qualifiée, 883 pour mois manquants. Les ordres virtuels/dépôt
produisent notamment des invalid_order_samples. Ne pas supprimer ces exclusions.
Les scalaires PASS C117 valent -1 sans shadow : l'analyseur joint le
`C121_BUILD` original par graine/lineId, qui porte actual_pax/actual_n.
Les événements C98 attendus sont absents des logs : partage des hubs inconnu,
malgré le réglage déclaré. L'audit de cette activation reste à faire.

Description exploratoire, **pas une validation de prévision** : 17 lignes matures
sur sept graines, flotte/moteur initiaux conservés, au moins 180 jours qualifiés
éventuellement discontinus. Somme des flux mensuels moyens par ligne : prévision /
débit observé = **3,801**, biais +280,1 %. Toutes sont classées demand_limited
par l'heuristique C117. La sélection des mois fiables et des flottes survivantes,
ainsi que les hubs non renseignés, interdisent d'en déduire un facteur global
0,263 ou un biais de toutes les lignes. Un mois sans départ ne prouve pas une
demande nulle ; le débit est aussi limité par le service réellement effectué.

Exploration séparée : au moins six mois qualifiés dans chaque année, flotte
inchangée dans toute la fenêtre. 18 cas d'apprentissage, sept de validation ;
seulement **trois cas / deux lignes / une graine** comparables au modèle initial.
WAPE construction 37,5 %, observation annuelle partielle 81,0 % ; biais +22,4 %
et +4,7 %. Poids observation appris pour hubhub=1, mais le mélange ne réduit pas
l'erreur sur validation. Aucun apprentissage comparable pour les autres bras.
**Aucun substitut par simple moyenne passée n'est validé.**

Preuves : `results/c121_pax_flux_20261007/diag/bench.json`, JSONL, manifestes,
bundle et logs ; `analysis_strict_final.json`, `analysis_exploratory.json`.
Cette première sortie exploratoire utilise les derniers mois qualifiés pour
90/180, potentiellement discontinus ; la version finale de l'analyseur corrige
ce point et retourne inconnu si la vraie fenêtre récente n'est pas qualifiée.
Conserver cette première sortie, ne pas présenter ces deux colonnes comme
une comparaison temporelle validée. Treize tests analyseur/prototype verts.
La sortie corrigée est `analysis_exploratory_final.json` ; ses colonnes 90/180
sont inconnues faute de fenêtres récentes entièrement qualifiées.

## Estimateur candidat : flux capté de station, puis partage conservatif

La grandeur utile est le **flux PASS capté durablement par aéroport**, distinct
du MAIL et partagé entre toutes ses lignes. Sur une fenêtre de durée T :

`arrivées captées = embarquements tous services + stock_fin - stock_début + pertes - apports externes`.

Un stock qui grossit révèle un flux supérieur au débit ; vider un ancien stock
ne prouve pas une hausse de demande. Inclure tous les services de la gare,
pas seulement une ligne AIR. Des pertes inconnues donnent une **borne basse**,
pas une observation exacte. C117 seul ne mesure ni ces pertes ni tous les
embarquement d'une gare multimodale.

Pour une station connue, apprendre un résidu de capture local sur un an de
fenêtres mensuelles non superposées, qualifiées et non censurées :

`k_station = médiane(flux_capté_observé / modèle_station_au_même_moment)`

`flux_station_prévu = modèle_station_courant × k_station`.

Le modèle courant reprend production et rating actuels. Ce résidu corrige
ensemble concurrence invisible et biais de couverture sans les identifier
séparément. Ne pas utiliser des recettes PASS+MAIL comme observation PASS.
Le prototype exige 330 jours observés : contrat exploratoire, pas seuil
économiquement qualifié. Une station nouvelle reste non calibrée, sans facteur
uniforme inventé. Les coefficients peuvent dépasser 1.

Distribuer un seul total entre lignes selon des poids de service normalisés :
leur somme doit conserver le total de station. Traiter séparément les deux
extrémités et leur asymétrie, puis réévaluer le gain marginal d'un avion.
C121 possède déjà un partage selon capacité/cadence ; le candidat améliore
le flux de station qui l'alimente.

Prototype : `sweeps/c121_station_flux_estimator.py`, six tests de bilan,
calibration et conservation ; sept tests analyseur verts.
**Candidat structurel explicite, algèbre testée, performance non validée.**
Restant : observation fantôme du bilan de station et des pertes/embarquement,
réconciliation des ordres virtuels C117 et audit C98, validation temporelle
sur graines réservées, puis A/B si amélioration de prévision établie.
Aucune modification Squirrel, de défaut, commit/push ou campagne supplémentaire.
