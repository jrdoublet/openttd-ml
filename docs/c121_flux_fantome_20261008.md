# Flux PASS par station — mesure fantôme

Autorisation utilisateur « Vas y », reprise « Retente » le 08/10. L'accès local
fonctionne à nouveau. Intervention isolée : `c121_station_flux_probe=0` par défaut,
à 1 collecte seulement. Aucun consommateur dans la cible ou le scoring.

La sonde lit les stocks et les augmentations nettes de charge entre observations
au même aéroport. Elle scanne tous les véhicules primaires propres ayant une
capacité PASS, indépendamment des listes de lignes et des ordres courants virtuels.
Les pertes ne sont pas observables : `losses=-1`, `exact_pm=-1` toujours.
Les visites ou déchargements manqués sous-comptent les embarquements. Le bilan
donne une borne basse seulement si les snapshots sont cohérents, distribution
manuelle, absence de transfert/déchargement forcé et services AIR simples.
Les gares avec services PASS non AIR sont signalées non qualifiées à ce stade ;
les arrêts joints sans circulation PASS non AIR ne sont pas des transferts (r3).

Le premier chargement aperçu n'est pas compté comme embarquement : il peut
contenir des passagers arrivants. Le stock qui croît entre snapshots contribue
au bilan ; stock vidé ne devient pas une nouvelle demande. Les intervalles
à risque sont inconnus, et une borne zéro ne signifie jamais demande zéro.
Fenêtres de 30 jours réels ou plus, cadence minimale deux jours ; écart maximal,
ratings, décalage de tick et risques conservés. État transitoire reconstruit après
chargement ; jamais ajouté aux lignes ni aux sauvegardes. Nettoyage des gares retirées.

## Pré-enregistrement avant parties

Arbre local basé sur `36fa8c7`, modifications utilisateur préservées. Contrats
Python pertinents puis smoke causal **42 x 1 an**, deux duels distincts contre
AAAHogEx figée, même bundle. Référence `OpexAI[c121_station_flux_probe=0]`, variante
`OpexAI[c121_station_flux_probe=1]`. Autres réglages aux défauts locaux courants,
C121 économie/catalogue=1/1, plafond=0. Pas de C98 ni decision_log : audit statique
confirme que C98 reste sous decision_log, contrairement au seul flag C98.

Campagne `c121_station_flux_smoke_20261008`, sortie neuve
`results/c121_station_flux_20261008/smoke/bench.json`. Docker desktop-linux,
image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
cache openttd-lab-home, montage /work, 10 CPU / 8g RAM et swap / 10 workers.
Aucun conteneur concurrent au contrôle initial. `gain_short` explicitement,
seuil 4 %, garde 5 %, required_seeds=40/required_years=3, years réellement=1.
Verdict statistique attendu hors échantillon : diagnostic_only, pas adoption.

Critères : deux parties saines complètes, sonde absente OFF, présente ON,
compteurs non négatifs et contrats du bilan cohérents ; mesurer l'exposition
positive sans imposer artificiellement une demande exacte. Budget de cette étape :
deux années-parties. Pas de relance favorable ni de nouveau long banc avant
audit de la qualité. Les opcodes de la sonde peuvent décaler les trajectoires.

Source moteur contrôlée : pertes aléatoires à rating <=127/255 et troncature
des stocks importants (`station_cmd.cpp` 15.3). `GetCargoPlanned*` lit les
FlowStatMap du routage : ne pas le confondre avec un compteur des arrivées réelles.
`AICargo.GetDistributionType`, pas GetCargoDistributionType, est l'API réelle.

## Réparation technique du smoke, avant relance

Première campagne conservée : référence saine, variante `noai_error` car le
nom VS_LOADING n'existe pas dans l'API. Bundle
`656e0ce614c59b85d3c9d5cc505455f1b780edfd2ad9d6c9545e39d08bd464d5`, manifeste
`01d39be1103c733a5c79bb15a0af6c05cd6cbccd7005bd785a2888d5649768e9`, verdict
brut `incomplete`. Aucun résultat économique interprétable.
Correction ciblée : VS_AT_STATION, vérifiée dans script_vehicle.hpp 15.3,
qui inclut chargement et déchargement. Le helper ne compte que les hausses
nettes positives, sans confondre les baisses de déchargement avec des arrivées.
Nouvelle campagne `c121_station_flux_smoke_20261008_r2`, sortie
`results/c121_station_flux_20261008/smoke_r2/bench.json`, mêmes bras/protocole.
Extension technique du budget : deux années-parties supplémentaires, sans
changement de seuil ni de sélection sur résultat économique.

## Audit du rejet des gares multimodales, avant r3

r2 : deux parties complètes/saines, `diagnostic_only`. Bundle
`9f0081b5e8d0073e31980085d4fcd9efe180cb1a0c7d777135349efdddd1d19a`, manifeste
`ab672c20760b9667bb46c0a3229fa972a14ed624f3c775a8e59254c7bfeeea35`.
77 fenêtres, 76 inconnues, une borne zéro qualifiée, 1 892 embarquements
observés hors qualification. Le décodeur conserve ces exclusions.
Cause vérifiée dans le dernier snapshot : 14 aéroports, 13 gares avec bus-stop,
22 avions, aucun véhicule routier/rail/eau. Les stops joints étendent le
catchment, mais aucune circulation bus/rail n'y apporte de passagers.

Correction du contrat, pas sélection économique : conserver l'indicateur
multimodal, qualifier les arrêts joints inactifs si aucun service PASS non AIR
n'existe dans la compagnie. S'il en existe, exclure conservativement les
gares multimodales (notamment les appels ferroviaires intermédiaires absents
des ordres explicites). Les transferts/déchargements forcés restent exclus.
Cette règle vérifie l'absence d'apports externes, plutôt que la seule présence
d'une installation. Aucun passage de pertes inconnues à zéro.

Nouvelle campagne `c121_station_flux_smoke_20261008_r3`, mêmes bras/graine/horizon,
sortie `results/c121_station_flux_20261008/smoke_r3/bench.json`. Deux années-parties
supplémentaires pour exposition après correction. r2 conservé, aucun gain
économique tiré de ces smokes ni banc long lancé.

## Résultat final r3

Deux duels complets/sains, Opex et AAA actifs, aucune erreur NoAI ; une paire
complète, verdict brut **diagnostic_only**, attendu hors protocole d'adoption.
Bundle `952e376eec2c7db81107b92b1939d38d2dbec26de5381e3ae9437052009fe157`,
manifeste `8304c7f56bf94b8889fa6facf1f5f0bf5995807949cd995b6cb0414a92564e5f`.
Référence OFF : zéro événement. Variante ON : **77 fenêtres sur 11 gares**,
toutes qualifiées comme bornes basses, **47 bornes positives**, **1 972 passagers
embarqués observés au minimum** sur les fenêtres clôturées. 76 fenêtres incluent
des installations bus jointes ; zéro risque et zéro snapshot décalé sur ce smoke.
Les aéroports ouverts tard n'ont pas forcément de fenêtre mensuelle clôturée.

**Zéro observation exacte de demande.** La borne zéro ne signifie pas zéro
demande ; les pertes inconnues et embarquements manqués restent non identifiés.
Les ratings sont en pourcentage, 101/-1 indique aucun rating observé pour min/max,
pas une station notée 101 %. Ne pas agréger les minima inconnus comme des notes.
L'augmentation de chargement initialement aperçue n'est pas créditée comme
embarquement pour éviter de compter des passagers arrivants.

Analyse reproductible :

```text
python -X utf8 sweeps/analyse_c121_station_flux.py results/c121_station_flux_20261008/smoke_r3/bench.json --out <nouveau_fichier.json>
```

Sortie conservée `results/c121_station_flux_20261008/smoke_r3/flux_analysis.json`,
avec hash des logs, manifeste, bundle et toutes les fenêtres. Les résultats
r1/r2 restent dans leurs répertoires ; aucune reconstruction ni réécriture.
90 tests ciblés verts : décodeur/contrats sonde 4, estimateur 6, prévision 7,
C121 économie 73 ; selftest du harnais vert, diff --check vert. La compilation
et l'exécution Squirrel sont validées par les smokes, pas par les tests Python.

Livré : mesure fantôme désactivée par défaut, aucun consommateur comportemental,
état hors Save/Load reconstruit, décodeur et provenance. **La collecte est exposée,
pas le meilleur estimateur qualifié.** Aucune A/B économique, modification de
targetAirPlanes, commit ou push. Les différences de profit des smokes ne sont
pas interprétées : instrumenter peut déplacer la trajectoire via les opcodes.

Prochaine porte : rendre le flux identifiable (compteur complet d'embarquements
ou intervalles contrôlés et pertes bornées), puis validation temporelle sur
graines réservées. Le calibrateur exact du prototype refuse ces bornes : ne pas
alimenter k_station avec une estimation minimale traitée comme une demande exacte.
Un autre diagnostic dix ans de simples bornes n'établirait pas à lui seul une
surestimation et ne justifie pas une campagne coûteuse automatique à ce stade.

Suite du 08/10 : le [compteur moteur LGRP](c121_flux_moteur_20261008.md) permet
une validation externe sans compter les embarquements/pertes. Pilote et
diagnostic dix graines × dix ans terminés ; compteur inaccessible à NoAI,
aucun branchement comportemental. La mesure des simples bornes reste distincte.
