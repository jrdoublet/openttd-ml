# C121 — pistes d'optimisation du calcul du portefeuille AIR

Analyse du 1er octobre 2026, sans modification de production ni lancement de
partie. Arbre lu : branche `c121-catalog`, HEAD
`52ab55537dcf18a0ded8700bc9ac73833ac369a5`, avec modifications locales préexistantes,
dont `c121_air_decision_depth_economics`. Ces modifications ont été préservées.
Les constats ci-dessous portent sur cet arbre ; son identité avec le VPS n'est
pas attestée par un manifeste commun.

Le [suivi courant](taches.md) a été relu après ses mises à jour concurrentes :
la variante de profondeur de décision est rejetée, son défaut reste 0 et C115
reste protégé. Les fixtures OFF/ON proposées ci-dessous vérifient la compatibilité
du calcul ; elles ne constituent pas une proposition de réactiver cette variante.

## Point de départ et portée des chiffres

Mesures **communiquées par l'utilisateur depuis le VPS**, graine 42 × 1 an :

| Poste | Millions d'opcodes | Lecture |
|---|---:|---|
| Catalogue AIR total | 13,9 | Dénominateur AIR, pas toute l'IA |
| Nouvelles paires | ~12 | Contient le choix d'avion |
| Choix d'avion par paire | 9,3 | Contient les sous-postes suivants |
| Demande | 1,3 | Inclut la préparation du service existant dans le code lu |
| Comparaison des avions | 4,3 | Bornes, tri et évaluations exactes |
| Calcul complet du gagnant | 3,2 | Ouverture puis scan de flotte |
| Hubs, graine 42 | 0,25 | Périmètre détaillé non fourni |
| Hubs, graine 100 | 6,4 | Périmètre détaillé non fourni |

Les trois sous-postes du choix totalisent 8,8 M, contre 9,3 M annoncés : le code
mesure aussi `c121_static_ops`, mais les données fournies ne permettent pas
d'attribuer exactement les ~0,5 M restants. Ne pas additionner les périmètres
parents et enfants. Le chiffre hubs ne prouve pas que la seule découverte des
aéroports coûte 6,4 M : elle contient aussi une recherche de nouveaux sites et
le périmètre rapporté peut englober les évaluations hub→site et hub→hub.

Le scan moteur et le calcul complet représentent ensemble **7,5 M, soit ~54 %
du catalogue AIR** sur ces chiffres. C'est le volume des postes à travailler,
pas une économie annoncée. Aucun pourcentage de gain n'est mesuré ici.
L'ancien gain de −5 % sous C115 n'est pas transposé à C121.

Déjà présents : invariants de paire dans `OpexC121PrepareEngineStatic`, cache
d'extrémité PASS/MAIL, choix de paire incrémental, borne optimiste et tri des
avions, index de routes et de paires de hubs. Les correctifs de cohérence du
[lot cache](c121_cache_coherence_20261001.md) sont dans le code lu. Leur ajouter
simplement un deuxième cache identique n'est pas une piste nouvelle.

## 1. Mutualiser l'ouverture et la flotte du gagnant

**Priorité haute ; poste visé : les 3,2 M du gagnant.**

[Analyse détaillée de cette piste](c121_air_winner_single_scan_analysis_20261001.md) :
contrats d'ouverture/croisière, raccourci cap=1, fusion générale, fraîcheur des
tarifs et validation avant intégration. Aucun prototype de production livré.

**Complément moteur :** [fixture 42/100](c121_air_winner_fixture_20261001.md) :
zéro cap=1 sur 2 289 recalculs ; le raccourci seul est sans exposition dans
ce pilote. La fusion générale reste à prototyper et mesurer.

Dans `air_economics_c121.nut`, lignes 1165–1166, le chooser appelle le modèle
complet avec le nombre initial, puis avec `fixedPlanes=0`. Hors expérimentation
`c121_aaa_line`, le premier calcule N=1 et le deuxième recommence par N=1.
Tous deux refont aussi cycle physique, tarifs, bases de rating et préparation
des coûts propres au moteur.

Piste : une évaluation du gagnant qui conserve le résultat d'ouverture et
cherche simultanément le meilleur profit et le meilleur score. Le résultat
d'ouverture reste distinct du résultat de croisière : le chantier construit
toujours N=1, et la cible après construction reste recalculée avec les capacités
PASS/MAIL observées. Pour `c121_aaa_line`, conserver son ouverture N=2 même si
la borne ordinaire de flotte est inférieure à 2.

Ne pas remplacer le meilleur profit par le meilleur score : le flag local
`c121_air_decision_depth_economics` décide lequel est propagé au portefeuille.
Conserver les deux résultats et leurs départages, ainsi que les métadonnées
distinctes d'ouverture et de scan. Aucun partage mutateur des objets renvoyés.

## 2. Construire les grands snapshots seulement à la fin

**Priorité haute ; même poste que le lot 1, économies non additives.**

Dans `OpexC121AirEconomics`, lignes 793 et 843, chaque amélioration du meilleur
score ou du meilleur profit alloue un snapshot de plus de 80 champs. Pour un
même N, les deux peuvent être alloués et contenir presque les mêmes valeurs.
Le test R15 confirme l'égalité des champs communs. Le scan `decisionOnly` est
déjà compact ; c'est surtout le scan complet du gagnant qui reste concerné.

Piste : suivre les argmax avec des résultats compacts, puis matérialiser les
snapshots complets de l'ouverture et des deux profondeurs retenues. Si deux
profondeurs coïncident, mutualiser le calcul, puis produire les objets distincts
requis par les consommateurs. Une reconstruction finale de quelques N peut
être nécessaire ; mesurer son coût net, surtout lorsque `fleetScanCap` vaut 1
ou 2, pour ne pas déplacer simplement la dépense.

Les champs de télémétrie, les résultats PASS/MAIL, les externalités et les
départages restent identiques. Supprimer les snapshots des seuls perdants ne
doit pas supprimer des sorties publiques des gagnants.

## 3. Préparer un contexte propre à chaque paire et avion

**Priorité haute ; postes visés : comparaison 4,3 M et début du gagnant.**

`OpexC121InitialEngineUpperScore` calcule les tarifs et le cycle physique
(lignes 1020–1035). `OpexC121AirEconomics` les recalcule pour chaque avion qui
passe cette borne (lignes 555–563), puis lors des deux appels complets du gagnant.
Le cache actuel porte sur les invariants indépendants de l'avion ; ce travail
reste dépendant du moteur.

Piste : conserver avec chaque candidat le cycle, le temps de paiement, les
tarifs, les capacités PASS/MAIL connues, l'amortissement et les points de vitesse
déjà calculés. Les réutiliser dans l'évaluation exacte et celle du gagnant.
Étendre un contexte compact existant plutôt qu'allouer un gros objet pour tous
les avions qui seront éliminés par la borne.

Portée courte : une évaluation de paire, avec abandon à une révision des
capacités, des prix, du calendrier tarifaire ou des paramètres de cinématique.
Pas de cache global persistant par seul ID moteur. Le cold start PASS-only,
la réalisation appliquée aux différents chemins et l'ordre des conversions
entier/flottant restent ceux du modèle actuel. Conserver le tri et le départage
score→profit→ID ; l'élagage exact existe déjà.

## 4. Réutiliser l'allocation de demande pour un rating déjà rencontré

**Priorité moyenne ; concerne les évaluations exactes et le scan complet.**

`OpexC121StationAllocatedMonthly` (`air_coverage.nut:531`) parcourt les buckets
de concurrence à chaque appel. Le scan flotte l'appelle à chaque N pour les
deux extrémités et, lorsque sa capacité est connue, MAIL. Pour un snapshot
d'extrémité/cargo fixé, seule la note entière 0..255 varie.

Piste : un mémo paresseux `rating → allocation`, rattaché au snapshot immuable
de production et de concurrence. Il réutilise exactement la fonction actuelle,
sans nouvelle approximation. Ne pas pré-calculer systématiquement 256 entrées.
Mesurer répétitions des notes, taille des buckets et coût du hash : avec peu
de répétitions ou de concurrence, le mémo peut coûter davantage que le calcul.
Abandonner ce dérivé quand le snapshot parent change et au rechargement.

Petit complément isolable : dans `OpexC121RatingTarget`, lignes 511–514,
`offered` et `waitingUpper` sont recalculés avant le retour `pointsOnly` qui
ne les utilise pas. Déplacer ce retour avant ces deux calculs est une piste
simple mais de portée modeste ; elle ne supprime pas l'itération du rating.

## 5. Mutualiser le service des hubs et isoler le coût de découverte

**Priorité à décider après ventilation de la graine 100.**

Deux répétitions distinctes apparaissent dans le code :

- `OpexC121PrepareDemandShadow` appelle deux fois
  `OpexC121ExistingStationService` (`air_coverage.nut:817–818`). Chaque appel
  parcourt les lignes puis les véhicules de la gare (`air_economics_c121.nut:298`).
  Un même hub touché par plusieurs paires répète ces lectures ; le cache de
  demande d'extrémité ne contient pas ce service. Premier candidat : index des
  lignes par gare et snapshot de service une fois par gare dans une invocation,
  avec les mêmes règles de filtrage et la même somme pondérée. Une conservation
  entre tranches demanderait en plus révisions flotte, capacités, délais appris,
  stations et tarifs ; la seule révision de connectivité ne suffit pas.
- `OpexAirPlansDiscoverHubs` est appelé avant les phases hubs à chaque reprise
  (`air_planning.nut:2113`), même lorsqu'un curseur hub existe. `ctx.hubs` n'est
  pas restauré. `OpexAirPlansPrepare` reconstruit également `hubIndex`. La
  découverte refait deux recherches linéaires dans `towns` (lignes 1070/1091),
  parcourt les aéroports orphelins et peut chercher des sites supplémentaires.
  Un index `town.id → town` est une première intervention limitée. Réutiliser
  ensuite la structure de découverte exige une génération et des revalidations
  explicites ; préserver l'identité et l'ordre du tableau associé aux curseurs.

Ne pas présenter l'index des routes comme absent : `c80_air_hub_index=1` est
déjà le défaut. Pour décider le lot, séparer les phases existantes
`hub_discover`, `hub_site`, `hub_hub`, puis ventiler la découverte entre sites
supplémentaires, lignes/aéroports et revalidation des sites.

Une autre dépense est **conditionnelle** : `hubAvgIncome` est préparé lorsque
`AIR_HUBHUB_MARGINAL` est actif (`air_planning.nut:1353`), mais ses deux
consommateurs sont exclus sous C121 (lignes 1540/1558). Éviter cette préparation
sous C121 est exact pour ce chemin. Le réglage vaut toutefois 0 par défaut :
ce point n'explique pas les 6,4 M sans preuve de son activation sur le VPS.

## Intervention et validation proposées

Ordre proposé : **contexte paire/avion**, puis **ouverture et snapshots du
gagnant**, chacun mesuré séparément ; le mémo de rating suit seulement si ses
répétitions sont exposées. La graine 100 sert d'abord à choisir le lot hubs.
Ce document propose les interventions, il ne les active pas.

1. Comparer les deux chemins dans des fixtures NoAI sur les mêmes entrées
   figées : `newpair`/`hubsite`/`hubhub`, PASS-only/PASS+MAIL, gare saturée,
   asymétrie A/B, égalités score/profit/ID, scan cap 1/2/élevé, ouverture 1/2,
   profondeur de décision OFF/ON et conversions aux frontières d'arrondi.
   Vérifier les résultats complets et l'absence d'alias mutateur. Les contrats
   Python textuels existants devront évoluer ; ils ne prouvent pas seuls
   l'équivalence de l'algorithme Squirrel.
2. Smoke réel 1×1 avec les protections Docker du dépôt, puis mesure appariée
   du **même C121 contre le même C121 optimisé** sur les graines 42 et 100,
   avec mêmes options et instrumentation. Reprendre les compteurs
   `c121_demand_ops`, `c121_static_ops`, `c121_scan_ops`, `c121_winner_ops`,
   évaluations moteur et hits/misses. Distinguer invocations, paires nouvelles,
   hits catalogue, N de flotte et phase hubs ; mesurer gain par paire et gain
   annuel. Ajouter seulement les compteurs agrégés qui manquent.
3. Contrôler la perturbation des sondes ; les témoins post-chantier contaminés
   et les trajectoires instrumentées d'investissement ne constituent pas un
   témoin économique. À entrées identiques, vérifier les mêmes décisions ;
   en jeu, moins d'opcodes peut changer le calendrier et donc les trajectoires.
4. Les décisions courantes interdisent le 20×10 C121 et protègent C115.
   Aucune qualification par défaut n'est lancée pour cette analyse. Une future
   adoption d'optimisation d'opcodes nécessiterait une décision de reprise et
   la preuve de neutralité prévue par AGENTS.md §4, distincte d'une adoption
   du modèle économique C121.

À ne pas faire dans ces lots : diminuer arbitrairement le nombre d'avions ou
de paires, ne classer les projets que sur N=1, réintroduire le préfiltre hubs
rejeté, changer une constante de manœuvre ou retarder le renouvellement des
caches pour gagner artificiellement des opcodes. Ce sont des changements de
décision ou de fraîcheur, pas la suppression des répétitions identifiées ici.
