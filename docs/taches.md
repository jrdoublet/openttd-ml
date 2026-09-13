# Tâches — réduire l'écart avec AAAHogEx

Revue du **2026-09-13**. Ce fichier contient les décisions actuelles et le prochain travail
utile. Les travaux terminés et leurs dossiers, y compris C65 (`19609f8`), sont transférés
dans [le journal du 13 septembre](journal_2026-09-13.md). Les développements antérieurs y sont
conservés intégralement pour la traçabilité ; seul ce fichier prescrit le travail restant.

Avant de rouvrir une piste, rechercher son nom et ses réglages dans ce journal **et** dans
[l'archive du 9 septembre](taches_archive_2026-09-09.md). L'archive sert à retrouver les
implémentations et les raisons des décisions ; **aucun résultat antérieur au 09/09 ne prouve
la performance actuelle**. Les journaux quotidiens conservent le détail des expériences.

## Où nous en sommes

**Le retard économique est établi ; sa cause dominante ne l'est pas encore.** Le duel partagé
20 graines × 5 ans du 13 septembre donne les résultats suivants, recalculés depuis les
20 paires de [la référence](../results/bench_1v1_5y_20seeds_reference.json) :

| Dernier checkpoint : 1974-12-01 | OpexAI, moyenne | AAAHogEx, moyenne | Écart des moyennes Opex/AAAHogEx | Victoires Opex |
|---|---:|---:|---:|---:|
| Valeur de compagnie | 2,189 M£ | 7,698 M£ | −71,56 % | 0/20 |
| Profit annuel | 676 k£ | 4 000 k£ | −83,09 % | 0/20 |
| Score de performance | 483 | 807 | −40,09 % | 0/20 |
| Moyenne des notes médianes de gare | 167,6 | 186,8 | −10,28 % | 0/20 |
| Gares possédées | 64,5 | 177,6 | −63,68 % | — |
| Caisse | 364 k£ | 1 650 k£ | — | — |
| Emprunt restant | 223,5 k£ | 0 £ | — | — |

Ces pourcentages sont des **rapports de moyennes**, pas la moyenne des pourcentages par graine.
Le harnais annonce zéro échec et les 40 lignes finales atteignent bien décembre 1974.
Il ne renseigne toutefois pas `expected_last_year` et ne transmet pas la sortie du moteur au
contrôle d'échec d'AAAHogEx : sa validation automatique reste à compléter (P0).

**Retrait du diagnostic « 93 % de rendement par véhicule, donc presque uniquement du volume ».**
Le harnais [du duel](../sweeps/bench_1v1_5y_20seeds.py), dans `extract_company_record`, compte
les entrées `VEHS` par propriétaire sans filtrer les composants. Les 102,4 contre 564,35 sont
ces entrées ; C54 a déjà identifié le piège wagons/ombres/rotors. Les décodeurs
`vehicle_breakdown` et `physical_telemetry`, malgré le nom `primary_vehicles_by_mode` de ce dernier,
ne filtrent eux aussi que type et propriétaire. Leur comptage demande la même qualification.
Même avec de vrais véhicules, une moyenne mélangeant bus, avions et trains ne prouverait pas
une équivalence de rendement. **Ne pas dériver de productivité ni de cible de flotte de ces comptes.**

L'emprunt nul d'AAAHogEx **à l'arrivée** ne veut pas dire qu'elle n'a jamais emprunté.
La dette élevée et la caisse positive d'OpexAI ne suffisent pas non plus à désigner le capital
ou le contrôleur comme goulot : il faut observer les occasions réellement disponibles et leur
financement au moment du refus. Les relevés économiques restent utiles malgré le problème de flotte.

La [chronologie C50](../results/diag_1v1_chronology_6y_5seeds.json) situe une rupture à examiner
dès **1971** : sur cinq graines, les créations nettes de gares passent de 148 contre 72 en 1970
à 57 contre 241 en 1971. Ce sont des sommes sur cinq parties, et des variations nettes de stock,
pas un comptage des chantiers. Le volet véhicules reste soumis à la réserve ci-dessus.

## Pourquoi le travail donne une impression de surplace

1. **La mesure du progrès a glissé vers le volume et les opcodes.** C51 augmente le nombre de
   gares sans gain économique démontré ; C50b augmente la flotte routière et dégrade la valeur.
   Une optimisation locale ou un réseau plus gros n'est pas encore un rattrapage.
2. **Les essais sont surtout arbitrés en solo.** Une victoire contre notre propre référence
   sur une carte séparée ne démontre pas une meilleure résistance à AAAHogEx sur carte partagée.
   Nous n'avons pas ici une série homogène de duels entre versions permettant de mesurer une
   vitesse de rattrapage. Le duel récent établit le retard, pas l'absence de tout progrès passé.
3. **Les mêmes hypothèses réapparaissent après leur réfutation.** Exemples : supprimer les
   plafonds après C50b ; proposer P1.1 comme inédit en C63 ; expliquer le rail improductif avec
   le comptage invalidé de C54 ; conserver le « facteur 15 inexpliqué » après sa correction C39.6.
4. **Les statuts confondaient livré, adopté et rentable.** C56 a corrigé un gel réel ; C65 facilite
   le développement. Ce sont des acquis. C60 n'a qu'un smoke de son filtre ; C53 non-stop est
   adopté mais son gain économique n'est pas établi statistiquement par le banc cité.

**Objectif de la prochaine séquence : augmenter le profit et la valeur en duel, en expliquant
le mécanisme qui permet de réinvestir.** Le nombre de véhicules, les gares et les opcodes restent
les instruments de diagnostic. Ils ne remplacent pas cet objectif.

## Ordre de travail

| Rang | Chantier | Question qui doit être tranchée | Livrable / condition de passage |
|---|---|---|---|
| **P0** | C64 : référence et mesure fiables | Quelle est la trajectoire économique actuelle face à AAAHogEx, avec une flotte correctement comptée ? | Harnais qualifié, référence figée ; réutiliser les données valides avant de relancer |
| **P1** | **C63 + C58 : investissement et réinvestissement** | Où se perd la croissance à partir de 1971 : coût, revenu capté, occasions absentes ou décisions lentes ? | Un diagnostic commun 5×6, attribution par mode/âge de ligne, puis **un seul** correctif causal |
| **P2** | C61 + C59 : exploitation des infrastructures rentables | Quelles lignes profitables disposent de demande non servie et d'une capacité réellement disponible ? | Cibler le mode exposé par P1 ; un levier isolé, sans rejouer la suppression brute des plafonds |
| **P2 conditionnelle** | C39/C41 : coût des décisions utiles | Reste-t-il des projets valides et finançables que le contrôleur traite trop tard ? | Montrer un délai et une occasion perdue sur l'arbre courant avant de modifier la cadence ou les caches |
| **P3** | C52/C60, eau/C57, autres | Quel effet matériel subsiste hors des priorités ci-dessus ? | Remontée seulement sur exposition mesurée ou défaut bloquant reproductible |

La première action est P0, puis le diagnostic commun C63/C58. **Ne pas lancer simultanément
une nouvelle famille de plafonds, un nouveau score et un orchestrateur général.** Les rangs P2
restent des suites conditionnelles ; rien ne prouve encore que l'un d'eux est le meilleur levier.

<a id="c64"></a>
## P0 — C64 : consolider la référence, fermer la recherche de seuil de carte

**Déjà fait.** Duel 20×5 disponible ; banc adaptatif `< 50 industries` exécuté.
Recomptage de [ce banc](../results/bench_air_cadence_adaptive_10y_20seeds.json) : valeur +3,43 %,
profit +4,70 %, **9 victoires / 2 défaites / 9 égalités**, p bilatéral = **0,06543** sur les
11 paires non nulles. Le `p < 0,001` du titre de commit est erroné. Défaut adaptatif 0 confirmé.
Les graines du banc adaptatif sont celles déjà explorées pour découvrir le seuil : ce n'est
**pas une validation indépendante**, même si le contrôleur exécute maintenant la règle.

**À faire, borné à la fiabilité de la prochaine campagne :**

- Qualifier un compteur de véhicules de tête par mode contre `AIVehicleList`, sur un cas
  contenant train à wagons et avion ; séparer pool, unités pilotables et capacités transportées.
  Ne pas simplement renommer `physical_telemetry` ni traiter le discriminant de mode comme un
  filtre de véhicule primaire. Les JSONL du duel ne gardent pas les chunks nécessaires au recomptage.
- Compléter le contrôle des deux compagnies : horizon attendu explicite, erreurs de script
  attribuées à la bonne compagnie, présence et continuité du service. Une sauvegarde du monde
  à la bonne date ne démontre pas à elle seule que l'IA a continué à décider.
- Figer le **contenu exact de l'arbre**, les réglages, versions, configuration de carte, graines
  et places des compagnies. C65 est dans `19609f8` (après `559cc83`) : un SHA seul
  ne décrit donc pas le code courant. Aucun mélange entre référence de ce commit et variante
  du nouvel arbre ; conserver une copie isolée ou une empreinte des sources avec le manifeste.
- Réutiliser le harnais du duel et les décodeurs existants après correction ; la comparaison
  d'une variante exige de pouvoir configurer OpexAI dans ce harnais. Les deux bras du duel sont
  actuellement les noms des compagnies, pas deux politiques OpexAI concurrentes.
- Prévoir pour le prochain levier un témoin OpexAI courant et sa variante, **chacun contre
  AAAHogEx**, avec les mêmes graines, horizon et positions. Lire les deltas de valeur/profit
  d'OpexAI et l'évolution de l'écart avec l'adversaire. Ajouter le solo seulement pour attribuer
  un effet de concurrence, pas pour remplacer le verdict partagé.

**En attente :** politique adaptative selon la pression du vivier. Pas de nouvelle campagne
40×3 pour chercher le meilleur seuil sur les mêmes 40 graines. Toute reprise demandera un
mécanisme identifié par P1, une règle figée avant mesure et des graines nouvelles. Le score
primaire doit porter sur toutes les graines prévues ; les seules graines déclenchées sont
une analyse secondaire, surtout si le déclenchement dépend de l'état produit par la politique.

**Fin de P0 :** mesure qualifiée et protocole prêt. Pas besoin de multiplier les rebaselines
20×10 sans levier à comparer : le diagnostic P1 peut fournir la première trajectoire corrigée.

<a id="c63"></a>
<a id="c58"></a>
## P1 — C63 + C58 : comprendre le rendement de l'investissement

**Hypothèse ouverte :** l'expansion rentable ne s'auto-entretient pas assez vite face à la
concurrence. Le coût de construction n'est qu'une explication possible ; une recette trop
optimiste, un mauvais captage ou une occasion non traitée peuvent produire le même symptôme.

**Correction de C63.** Le devis anticipé rail existe :
[`OpexPrequoteRailCandidates`](../ai/OpexAI/projects.nut), `rail_prequote` et
`rail_prequote_keep_plan`, tous deux à défaut 0 dans `info.nut` et lus dans `settings.nut`.
P1.1/P1.3 ont été implémentés et rejetés avant le 09/09 ; leur histoire est dans l'archive,
**leurs anciens chiffres ne sont pas une preuve actuelle**. Ne pas réécrire ce mécanisme ni
réactiver son coût à chaque rebuild en le présentant comme une nouveauté. Les facteurs rail
170 % / route 121 % sont toujours dans le code ; leur justesse actuelle reste à mesurer.

**Un seul diagnostic commun, 5 graines × 6 ans, sur carte partagée**, en examinant d'abord
1970–1972 puis la suite. Réutiliser les sondes coût `RC|`, `AC|`, les événements de construction,
les sauvegardes et les prédictions enregistrées sur les lignes. Vérifier leur couverture
avant de supposer qu'elles suffisent : les succès seuls ne donnent pas les dépenses d'échec.
Ne pas activer aveuglément `decision_log` partout.

Sortie attendue : **un tableau par mode, année et cohorte de lignes**, contenant :

- coût prévu, coût engagé, dépenses d'échec/rollback et capital immobilisé jusqu'au premier
  revenu ; couverture et montants non attribués explicités ;
- revenu/profit attendu contre profit observé à périmètre comparable, âge depuis la mise en
  service, rotations/remplissage lorsque mesurables ; distinguer résultat d'exploitation
  d'une ligne et résultat de compagnie, qui n'ont pas les mêmes charges ;
- nouvelles lignes et renforts, demande effectivement captée, partage de gares/bassins et
  présence concurrente ; un stock à quai est un symptôme, pas une preuve de revenu récupérable ;
- trésorerie **mobilisable selon `OpexAvailableCapital`** : caisse + emprunt effectivement
  accessible − réserve, face au besoin réel du projet ;
- sur les occasions où une décision peut être prise : candidat absent, invalide/site refusé,
  non finançable, demande/capacité insuffisante, en attente de calcul ou effectivement lancé.
  Rapporter séparément occurrences et **jours de jeu** ; aucune double attribution silencieuse.

**Deux corrections de méthode indispensables :**

- « Caisse ≥ 300 k£ et rien construit » ne prouve pas un manque de débit. Il faut un projet
  rentable, réalisable et finançable qui attend. Réciproquement, un surcoût modèle de 30 % ne
  prouve pas qu'une baisse du coût résoudrait le problème. Le bilan peut rester mixte ou inconclusif.
- C58 ne doit pas observer seulement `ET_VEHICLE_UNPROFITABLE` : cela sélectionne les perdants
  et rate les lignes positives qui rapportent bien moins que prévu. Comparer aussi des lignes
  profitables du même mode et du même âge. Pas de ferraillage automatique dans cet audit.

Les deltas de solde bancaire peuvent inclure revenus, entretien ou emprunts pendant un chantier :
ne pas les appeler coûts purs sans réconciliation. Deux smokes identiques sondes ON/OFF sont
un contrôle préliminaire, **pas une preuve de neutralité sur six ans**. Privilégier l'extraction
hors jeu ; si une instrumentation est nécessaire, mesurer sa perturbation et séparer son
résultat du banc économique final, exécuté sans instrumentation lourde.

**Décision à la sortie, avant tout autre diagnostic :**

| Fait observé sur des lignes/occasions identifiées | Suite autorisée par le diagnostic |
|---|---|
| Dépenses d'infrastructure/échecs immobilisant matériellement le capital | Un correctif de placement, réutilisation ou estimation sur le mode concerné ; pas de devis rail synchrone généralisé |
| Lignes positives mais recettes très inférieures au modèle | Corriger une hypothèse de demande, captage ou rotation ; C58/C59 |
| Demande non servie sur une infrastructure rentable ayant de la capacité | C61 ciblée, avec dépense et congestion observées |
| Projets valides finançables retardés pendant un coût de calcul identifié | C39/C41 ciblée |
| Pas de cause dominante ou données insuffisantes | Publier les limites et nommer la seule donnée manquante ; ne pas déclarer arbitrairement « capital » ou « CPU » |

**Fin de P1 :** choisir un levier avec mécanisme, périmètre, effet attendu et critère d'arrêt
écrits ; ou clore explicitement l'hypothèse testée. Le succès du travail n'est pas le nombre
supplémentaire de sondes créées.

<a id="c61"></a>
<a id="c59"></a>
## P2 — C61/C59 : mieux exploiter les lignes, si P1 le justifie

**Acquis causal C50b**, [banc consolidé](../results/bench_c50b_levers_10y_40seeds.json) :
supprimer la réserve de demande aérienne détruit de la valeur sur 20/20 graines ; relever le
plafond routier perd 27 paires sur 40 en valeur ; supprimer le cap de cadence aérien est
inconclusif à 21/40. Ajouter des véhicules n'est donc pas en soi le chantier prioritaire.

- **Air :** mesurer rotations, attente, demande et occupation aux deux aéroports avant de
  remplacer le partage égal de cadence entre lignes. `airportDelayDays = 3` et la table par
  type sont des modèles à qualifier, pas des capacités mesurées. Le modèle mutualisé proposé
  dans le dossier C61 reste un candidat, pas une spécification validée.
- **Route :** séparer fret, feeders et passagers interurbains. **`road_pax_build=0` au défaut** :
  une réforme visant les bus interurbains ne résoudra pas le duel courant. Le fret en chargement
  complet demande une mesure d'attente distincte du dwell passagers ; ne pas diviser par son
  `dwellDays=0`. La cible est du trafic rentable supplémentaire, pas le passage de 2 à 8 véhicules.
- **Rail :** la relaxation du seuil de backlog a déjà été inerte. C50b rapporte 39 `NOSPOT`
  pour 28 `OK` et 2 `TRACKFAIL` sur les références d'extension : inspecter les échecs de géométrie
  **si** les lignes concernées sont profitables et demandent réellement un second train.
  Cela ne justifie pas encore un chantier global de jonctions et gares partagées.
- **Ordres C59 :** corréler chargement, attente et profit avant une politique contextuelle.
  Retirer la prémisse « longue distance ⇒ full load mathématiquement supérieur » : attente,
  demande, prix du transport et congestion doivent entrer dans la comparaison. Une photographie
  de `cargo_count` ne mesure pas à elle seule le remplissage au départ ni une rotation.

<a id="c39"></a>
<a id="c41"></a>
<a id="c44"></a>
## P2 conditionnelle — C39/C41/C44 : traiter une occasion perdue, pas une lenteur abstraite

Les profils C39/C48 du 10 septembre montrent une augmentation du coût de génération avec
la maturité du réseau. Ils ne prouvent pas à eux seuls le gain d'une optimisation aujourd'hui.
Le [banc C48 final](../results/bench_c48_indexed_regeneration_10y_20seeds.json) donne
**10 victoires / 10 défaites en valeur**, +0,53 % en moyenne : gain économique non démontré,
`c48_indexed_regeneration=0` conservé. C46 reste également à 0 malgré un coût fret réduit en 1024².

Reste utile : critère de fraîcheur par couche, invalidation et recomputations évitables,
**sur le chemin où P1 aura montré des occasions finançables retardées**. Les modules actuels
sont `scheduler_tasks.nut`, `task_projects.nut`, `projects.nut` et `catalog.nut` ; les anciens
numéros de ligne de `main.nut` sont périmés après C65.

Ne pas relancer `portfolio_max_batch`/`portfolio_dynamic_batch`, un prix d'opcode ajouté au
score, ni un orchestrateur général sur la seule foi d'anciens profils. La fiche C39.5 est
close sur son levier testé ; « construit au premier tour » ne signifie cependant pas qu'un
intervalle entre tours est gratuit. Mesurer en jours, à âge de partie comparable, et vérifier
ce qui devient effectivement constructible. **Le titre catégorique de C44 (« ni capital ni
opcodes : le tour ») est retiré**, tout comme le « facteur 15 inexpliqué » déjà corrigé par C39.6.

## Autres tâches ouvertes, hors séquence prioritaire

Les travaux clos C45/C46/C47/C48/C49/C50/C51/C53/C54/C55/C56/C62/C65 et les étapes déjà
livrées des autres fiches sont consignés dans [le journal du jour](journal_2026-09-13.md).
Ne pas les remettre dans la file active sans fait nouveau.

| Fiche | Travail restant | Condition de reprise |
|---|---|---|
| C52 | Revalider les corrections crash/non rentable postérieures au banc ; exploiter la sonde de première arrivée si nécessaire | Défaut de service observé ; pas un objectif de nombre d'événements branchés |
| C60 | Exposition actuelle route/rail puis diagnostic 5×6 du filtre, encore à 0 après son smoke | Refus municipaux matériellement coûteux ; ne pas inférer cette exposition des seuls refus air, qui incluent le bruit |
| C57 | Calibrer les 50 000 opcodes de Lakes | Distribution des recherches eau et coût des paires perdues ; conserver la protection contre le gel |
| C43 / E3 | Constantes non tranchées : réserve, `loop_budget`, `pax_near`, seuils de mise au rebut | Constante impliquée par le diagnostic ; pas de balayage général |
| C45, reliquat | Décider de la persistance des compteurs de subventions | Besoin au rechargement ; secondaire pour des parties neuves |
| C42 bis | Filtrage/rendement des subventions | Exposition rentable démontrée ; les subventions brutes restent à 0 |
| C55, reliquat | Partage de demande et sur-service des bassins | Flux concurrents observés par P1 ; ne pas rouvrir le filtre d'origine |

## Eau, bibliothèques et robustesse — conservés, différés

Le code utilise déjà la transcription MinchinWeb dans `lib_water.nut`, avec budget en opcodes.
Ne pas proposer de recommencer son intégration. La bibliothèque n'apporte pas à elle seule des
lignes rentables ; le catalogue de sites intégré aux rebuilds a été testé sans justifier son adoption.
L'ancien essai Lakes du 09/09 précède le correctif de gel C56 : il ne tranche pas à lui seul
le défaut combiné actuel. Aucune modification de défaut eau n'est décidée par cette revue.

Le dossier eau conserve : découverte de sites séparée du portefeuille, distance navigable au
lieu du minorant Manhattan, revalidation des fronts réels sans réintroduire le faux négatif du
BFS borné, rotations fractionnaires et qualification mémoire sur grandes cartes. **Réexaminer
ces points dans le code au moment de la reprise**. Leur poids dans le retard courant n'est pas
mesuré ; un gel reproductible reprendrait immédiatement la priorité. C57 conserve le calibrage
du budget, pas un retour au budget en itérations. La consigne existante d'accord explicite avant
un nouveau diagnostic de découverte maritime est conservée ; aucun n'est lancé ici.

Les autres sujets restent disponibles : catchment réel des gares, placement/bruit d'aéroport,
jonctions/agrandissement de gare, `station_join`, coût A*, réglages de partie avec mode désactivé,
RAM Squirrel et automatisation GitHub. Ils remontent sur un besoin démontré, pas parce qu'une
bibliothèque propose une fonction. Le temps de trajet rail reste hors périmètre de SuperLib
(cf. C41 et `AGENTS.md`). `origin_sitable` et `complex_cargo` conservent leurs défauts ; ne pas
présenter leur conservation comme un nouveau gain mesuré.

## Règles pour la prochaine expérience

- **Une hypothèse, une intervention, une décision attendue.** Écrire le coût d'essai et le critère
  d'arrêt avant de coder. Ne pas prolonger un résultat nul en explorant des seuils jusqu'à gagner.
- Smoke 1×1, diagnostic physique **5×6**, puis **20×10 apparié avant adoption**. Pour revendiquer
  un rattrapage, le banc doit comparer les deux politiques OpexAI **face au même AAAHogEx**.
  Le 20×5 actuel est une référence descriptive, pas une exception à la règle d'adoption.
- Pré-enregistrer la métrique économique primaire, l'effet minimal utile et les garde-fous
  sur l'autre métrique économique, les échecs et le service. Publier les deltas par graine,
  moyenne et médiane appariées, incertitude et V/D/égalités. Exclure les égalités du test des
  signes ; un résultat non significatif n'est ni une preuve d'équivalence ni une adoption.
- Garder les graines d'échec dans les résultats avec leur statut. Distinguer validation d'un
  correctif fonctionnel, maintien d'un défaut et démonstration d'un gain économique.
- Exploiter les résultats déjà présents avant de lancer une campagne. Après verdict, remplacer
  la fiche active par sa décision et archiver le détail : ne pas empiler les conclusions opposées.
- Docker : toujours `--cpus=3 --memory=2g --memory-swap=2g`, cache
  `-v openttd-lab-home:/home/lab`, source montée dans `/work`. Une seule campagne consommatrice
  à la fois sur le VPS ; ces limites par conteneur ne bornent pas leur consommation cumulée.

**Portée de cette revue :** lecture du code courant et des archives, recomptage hors ligne des
JSON récents, réorganisation documentaire. Aucun changement de comportement IA, aucun défaut
modifié, aucun nouveau banc lancé. L'[architecture après C65](architecture_opexai.md) donne les
nouveaux emplacements des fonctions.
