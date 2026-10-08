# C121 — producteurs couverts et partage intercompagnies

## Intervention et pré-enregistrement

Diagnostic externe uniquement, aucun changement de décision ni de défaut.
Lecteur supplémentaire des chunks MAPT/MAP2/MAPE/M3LO/MAP8, format de sauvegarde
362 (OpenTTD 15.3), maisons et aéroports originaux sans NewGRF. Géométrie : union
des expansions de chaque tuile d'installation, rayon propre à son type, arrêts
joints inclus, sans remplir les trous du rectangle englobant.

L'éligibilité PASS suit MoveGoodsToStation : rating positif, last_speed non nul
si selectgoods, exclusion truck-stop seul, exclusivités de la ville de station
et du producteur. HasRating n'est pas exigé par cette allocation. Pondération des
maisons achevées par ceil(population/8), génération binomiale à échelle100.
Le partage continu ignore les arrondis moteur et constitue un audit de snapshot,
**pas une prévision annuelle** ni une donnée accessible à NoAI.

Sources primaires : [carte](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/saveload/map_sl.cpp),
[couverture](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station.cpp),
[allocation et éligibilité](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station_cmd.cpp),
[maisons](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/table/town_land.h).
Table originale téléchargée dans results uniquement, en-tête conservé,
SHA256 e8d6962f0212613fa354929c628fc2ce4d377c634690f9983a5c0e6548460679.

Contrôles initiaux : cinq tests carte/maisons/couverture/partage/éligibilité,
deux tests conservation des sauvegardes et onze contrats du gel verts.
Lecture réelle d'une ancienne sauvegarde solo : sept stations éligibles,
ratio de partage1 partout (aucun rival). Cela vérifie l'intégration du lecteur,
pas l'effet économique ni la concurrence. CITY ne sauvegarde généralement pas
son cache de population : aucune prétention de checksum indépendant.

Campagne préparée avant lancement : `c121_source_map_smoke42_20261008`, un duel
OpexAI aux défauts courants contre AAAHogEx figée, graine42, un an, une répétition.
Dépôt courant, HEAD36fa8c79a740a54632d34ce86aecd2f5639e9493, arbre local modifié
(état complet et bundle à conserver par le lanceur). Aucun bras causal.
Profil desktop-linux : dix CPU, 8g RAM, 8g swap plafond, dix workers maximum,
volume openttd-lab-home ; image
sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659.
Aucun conteneur en cours au contrôle avant lancement.

Collecte : line-telemetry mensuelle, station-supply-telemetry et script-debug,
sonde NoAI station_flux aux défauts OFF ; rétention brute optionnelle via le
nettoyage existant, copies séparées par index de partie et SHA256 par fichier.
Sortie `results/c121_source_map_20261008/smoke42/bench.json`, sauvegardes
`results/c121_source_map_20261008/smoke42/saves`. Budget : un duel un an pour
l'intégration ; si sain, un duel42 six ans maximum pour exposer la concurrence.
Pas de relance pour améliorer un résultat économique. Santé/horizon/empreintes
et présence des deux compagnies à vérifier avant interprétation ; toute erreur
technique est conservée et diagnostiquée. Pas de porte A/B ni adoption.

## Contrôle d'intégration et suite six ans

Smoke terminé : deux compagnies complètes/saines,13 sauvegardes qualifiées,
86 observations d'aéroports Opex éligibles avec producteurs,69 avec producteurs
partagés. Ce sont des snapshots répétés, pas86 essais indépendants.
Bundle3b227ec9da63da375ff76550c9c0514493e11dce36c05fcab3fac8c69e7729e9,
manifeste7c48da779570f26433fbcb80432edec4286f316caf4b58db186735130900c96e.
Analyse `results/c121_source_map_20261008/smoke42/source_analysis.json` ; PASS
résolu par le log runtime, empreintes du bundle et de chaque sauvegarde vérifiées.

Lancement de l'extension pré-enregistrée : `c121_source_map_diag42_6y_20261008`,
un duel42 six ans, mêmes bras/défauts/collecte/profil. Sortie
`results/c121_source_map_20261008/diag42_6y/bench.json`, rétention `saves` adjacente.
Un seul duel : exposition et trajectoires, sans généralisation aux graines ni
qualification économique. Suite : séparer évolution de densité des producteurs,
partage intra-compagnie et partage intercompagnies, comparer les périodes LGRP
exactes sans imputer de demande absente ni transformer un poids instantané en
prévision annuelle.

## Résultat du diagnostic six ans

Duel sain/complet pour les deux compagnies ;72 sauvegardes conservées et
vérifiées. Même bundle que le smoke, manifeste
b4b542f70fbf0f94c0ca9a74650df49b5a60e2afa1b134a1b26a406ee8add79c,
archive1cedbdd7c3c2d9af683e3fb832f6b574dd3c88683234a403468e2e7be33aac4e.
Analyse finale `results/c121_source_map_20261008/diag42_6y/source_analysis_r2.json`.
Script `sweeps/analyse_station_sources.py`.

1 407 observations d'aéroports Opex alimentés,958 avec maisons partagées.
Au dernier snapshot :24 aéroports alimentés,17 partagent leurs producteurs ;
ratio du total des poids all-companies / own-only =0,6878, médiane des ratios
par aéroport0,6767. Aucun facteur uniforme proposé : sept aéroports ne subissent
pas ce partage au snapshot terminal.

Prévision au début de chaque intervalle : production municipale LAST_MONTH
uniquement, répartition entre maisons par ceil(population/8) des maisons achevées
actuelles, puis allocation par ratings initiaux. Témoin et variante analytique
partagent absolument les mêmes données et normalisation, seule l'allocation
intercompagnies diffère. Étiquette : arrivées LGRP nouvelles de l'intervalle
suivant, ramenées à30,4 jours ; compression/membership/identité inchangées.

| Calcul externe | Intervalles / stations / graines | WAPE | Biais |
|---|---:|---:|---:|
| Allocation limitée à Opex | 978 / 24 / 1 | 66,00 % | +64,37 % |
| Allocation toutes compagnies | 978 / 24 / 1 | 19,54 % | +14,02 % |

Exclusions sur tous cargos :1 082 compression/merge/identité,80 nœuds absents ;
430 intervalles PASS exacts sans prévision AIR initiale éligible/municipale.
Aucune imputation. Snapshots/intervalles répétés ne sont pas des graines
indépendantes. Aucun coefficient ajusté aux étiquettes, aucun test statistique
de gain économique. La prévision utilise les maisons et ratings adverses cachés :
**oracle mécaniste externe**, pas estimateur livré à NoAI, pas validation du
flux annuel futur ni correction adoptée de targetAirPlanes.

Dénominateur B9 terminal : certaines fenêtres omettent des producteurs de la
ville, d'autres contiennent ceux d'une autre ville ; par exemple town34 compte
41 producteurs dans la fenêtre contre50 dans toute sa ville, town10 compte56
contre39. La densité des maisons couvertes diffère aussi de la moyenne municipale.
Ces mécanismes doivent rester séparés : remplacer aveuglément la fenêtre par
la population de toute la ville ne suffit pas.

Suite : vérifier la réplication sur des graines distinctes, puis mesurer un
apprentissage local NoAI de la capture et sa prévision annuelle hors période
d'apprentissage, avec capacité et pertes explicitement distinguées. Aucun accès
caché à la sauvegarde dans l'IA. Aucun comportement ni défaut modifié.
Validation livrée :25 tests ciblés verts (carte5, archive2, supply7, gel11),
smoke réel et duel six ans sains, diff-check vert.
