# RVA-08 — emprises et production par extrémité

19/10/2026, base `12f4ebf`. **Calcul à blanc et contrats livrés ; demande future
de ligne non couverte**, sans collecte nouvelle ni décision IA modifiée.

## Livrable et sources

`sweeps/rva_demand.py:13` construit l'union des carrés autour des tuiles réelles
de gare, rayon fourni explicitement et bords de carte respectés. Aucun rayon
NewGRF supposé. Source OpenTTD 15.3, racine
`/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src` :
`station.cpp:309` choisit le rayon par installation ; `station.cpp:494` à `:506`
construit l'union réelle. Le rectangle englobant d'une gare jointe n'est pas une
emprise remplie. Les gares neutres ont un contrat distinct (`station.cpp:476`),
non revendiqué par ce helper pour les futures gares rail voyageurs.

`sweeps/rva_demand.py:31` reçoit un inventaire explicite de producteurs et volumes
par cargo. Il déduplique les identités (une industrie multi-tuile conserve une
identité), sépare voyageurs/courrier et extrémités, refuse les doublons et ne
convertit jamais un compte de producteurs en unités/mois. Un inventaire
incomplet donne un compte total et un volume inconnus, avec sous-total observé
distinct. Un producteur partagé par les deux extrémités interdit leur somme
naïve (`sweeps/rva_demand.py:88`).

Les services propres affectés sont décrits séparément : producteurs couverts,
intersection d'emprise et capacité libre du **même cargo**, quand capacité et
débit sont connus/cohérents. Une desserte saturée conserve sa production ;
aucune pénalité V216a supplémentaire n'est appliquée. Perte de clientèle,
demande future et incrément compagnie restent `None` sans modèle identifié.

**Piège API confirmé** : `script/api/script_tile.hpp:389` décrit un compte de
producteurs ; `script/api/script_tile.cpp:242` à `:247` force `CA_UNMODIFIED`
quand la couverture modifiée est coupée, même si l'appel demande rayon zéro.
`station_type.h:120` donne `CA_UNMODIFIED=4`. Sommer des appels « une tuile,
rayon zéro » ne serait donc pas une collecte dédupliquée dans ce profil.
`station_cmd.cpp:533` à `:558` déduplique les industries par ID et compte
des producteurs, pas leurs volumes. Aucun facteur population→demande ajouté.

## Données existantes et limites

Les trois journaux sont retrouvés sous
`/home/deploy/projects/openttd-ml/results/worktrees_archives_20261018/wt-rva/results/`.
Le lecteur courant `analyze_rva_cycle.records` a été réutilisé, avec décompression
gzip, sans nouvelle partie ni nouvelle instrumentation.

Campagne `rva_cycle_railseul_3x3_20261018`, dossier suffixé `_engine` :

| Fichier | SHA-256 du gzip | RVA_SAMPLE / RVA_MODEL |
|---|---|---:|
| `rva_cycle_rail_seed100_r0.log.gz` | `d2f73925063924cf0af11a2d415a995595094a44ffcf86483f8504f0ec1ec003` | 2278 / 4 |
| `rva_cycle_rail_seed42_r0.log.gz` | `5f15ecb6b5c4092c952388e7e22d5fdba42f4b2cb9c218aa719d9b62d49cf555` | 865 / 5 |
| `rva_cycle_rail_seed7_r0.log.gz` | `98bd164dd2615d71bd9ced1e34ff5a7c217b41564c37d19ead8317b686fd2b54` | 172 / 7 |

Les événements portent gares, positions du véhicule, capacités/charges, cycle,
composition et coût de sonde. Ils ne portent **ni emprise de gare, ni inventaire
de producteurs, ni volume local par producteur**. Une position du véhicule ne
remplace pas l'emprise ; les totaux ville V216 ne remplacent pas les volumes
locaux. Ces données ne permettent pas de valider une demande sur emprise réelle.

Le helper attend ces entrées explicitement ; il ne les présente pas comme
disponibles à l'IA, ne lit aucune sauvegarde dans l'IA et n'est consommé par
aucun score. Il s'agit de la partie de RVA-08 indépendante de la mesure et de
la future collecte RVA-12, pas d'un estimateur complet désormais qualifié.

## Validation et suite

`sweeps/test_rva_demand.py:8` : cinq contrats couvrent emprise disjointe/jointe,
recouvrement partiel, saturation, volumes inconnus, zéro réellement observé,
inventaire incomplet, producteurs communs et cargos distincts. Valeurs des
fixtures synthétiques, jamais constantes du modèle. Tests ciblés verts.

Aucune partie, aucun AddSetting, aucune modification Squirrel. Au défaut comme
avec les réglages expérimentaux existants, aucune nouvelle décision exécutée.
RVA-09 peut préparer le contrat du gain séparé ; les prévisions de fréquentation,
répartition et gain causal restent à établir avant de consommer ce calcul.
