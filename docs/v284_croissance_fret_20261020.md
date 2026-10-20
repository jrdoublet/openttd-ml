# V284 — croissance du fret existant, 20 octobre 2026

## Diagnostic préalable au code

Base propre `a9437f8`, branche `v284`. Lecture d'AGENTS, CLAUDE, des entrées
V267/V269/V270/V271/V272/V280/V281/V282 et V180 §4. La fiche V280 est
sur `origin/v280`, absente de master ; elle a été lue avec `git show`.
Le constat V267 fourni par l'utilisateur n'est pas rejoué.

Sources locales : préfixes (et non répertoires nus)
`../wt-v265fix/results/v265fix_expo_complete_3x10_20261019`,
`../wt-v270/results/v270_expo_3x10_20261019`,
`../wt-v271/results/v271_expo_3x10_20261019`.
JSON, télémétrie annuelle, JSONL et journaux moteur existants uniquement.
Bundle V265fix : `c461897dfd33a747f6d941958d6911feb1315785e6b71d821d8d97335a337053`.
Aucune sortie locale V281 trouvée ; résultats GitHub fournis par l'utilisateur
et consignés dans `docs/taches.md`, pas téléchargés ni requalifiés.

Au 1 décembre 1979, somme des trois graines 42/7/1234 ; fret = lignes rail
sans capacité voyageurs/courrier, capacités de cargos différents additionnées
uniquement comme **places physiques**, pas comme tonnes interchangeables :

| Campagne / bras / compagnie | Lignes fret | Trains | Trains/ligne | Places/train | Profit fret depuis janvier (£) |
|---|---:|---:|---:|---:|---:|
| V265fix référence Opex | 49 | 56 | 1,14 | 92,14 | 1 288 969 |
| V265fix référence AAA | 38 | 96 | 2,53 | 266,39 | 5 475 066 |
| V270 référence Opex | 47 | 59 | 1,26 | 83,90 | 1 189 667 |
| V270 actif Opex | 48 | 59 | 1,23 | 117,29 | 1 382 004 |
| V271 référence Opex | 49 | 60 | 1,22 | 80,92 | 1 158 482 |
| V271 actif Opex | 46 | 60 | 1,30 | 78,50 | 953 862 |

Ce profit des véhicules au 1/12 n'est ni le `profit_year` compagnie à quatre
trimestres clos ni une preuve causale par ligne. Les trajectoires divergent ;
ne pas attribuer tout l'écart au mécanisme. Le bit de note de gare erroné de
V265fix interdit de réutiliser sa note fret ; les nombres de trains/capacités
ne dépendent pas de ce bit.

V270, journaux : **45 `wagon`, 45 `done`, 0 `fail`, 4 refus vitesse** :
141→109, 110→85, 144→111 et 128→104 km/h modélisés. Au rapport janvier
1979 du témoin : **47 lignes fret, 15 avec au moins un wagon en attente,
7 avec au moins une rame** ; quais 2 tuiles : 2, 3 : 27, 4 : 14, 5 : 1,
6 : 1, 7 : 2 ; distance médiane 105. Les 29 petits quais limitent la réserve
de croissance. V272 a montré une hausse de capacité mais échoué économiquement :
pas de quais allongés dès la construction dans V284.

V265fix référence, caisse au 1/12/1979 : **14 534 946 / 20 888 478 /
13 839 681 £** (42/7/1234). Journaux : **16 `RAIL_EXPAND
action=double_track` (6/5/5), aucun `second_train`**. Il s'agit de deux
voies indépendantes avec une rame chacune, pas d'un réseau permettant
librement d'injecter un train sur la voie unique. L'ajout nu d'un train
ne fournit aucun lieu de croisement ; calculer un délai nominal d'aller-retour
ne garantit pas l'absence de rencontre (chargement, pannes, réservations).

Lecture AAAHogEx-115 (sans copie de code) : `trainroute.nut::CheckCloneTrain`
retourne immédiatement si `IsSingle()` ; sinon stock > demi-capacité
(`IsWaitingCargoForCloneTrain`), absence de train à la source/au dépôt,
et construction sur le réseau `TwoWayStationRailBuilder`. AAA ne prouve donc
pas qu'une deuxième rame fonctionne sur notre voie unique. V271 a réellement
fait monter la note mais pas le débit/profit. V202k a posé 35 évitements et
35 clones, résultat négatif : réutiliser sa géométrie ne qualifie pas sa politique.

## Intervention retenue avant implémentation

Levier plausible : acheter tardivement du débit sur les lignes **déjà
rentables et en attente**, sans financer les quais de V272 dès 1970.
Un seul réglage `v284_rail_growth` : **0 = master (défaut)** ;
**N=1…10 = ouverture après N ans et caisse disponible ≥1 M£**. Essai N=3.

Porter le déclencheur V270 de `c71b707`, adapté au fret seul, priorité
`distance × attente / capacité`, lecture du stock réel, cadence bornée.
Pour un wagon de plus, conserver au moins la vitesse effective actuelle :
choisir une locomotive compatible plus puissante si nécessaire. Réutiliser
le modèle d'accélération C41 et le constructeur mesurant les longueurs,
limité au minimum du quai et de `vehicle.max_train_length`. La rame ancienne
reste disponible jusqu'à réussite de l'assemblage et des ordres.

Au plafond et avec au moins une rame en attente : **un seul évitement court
et un second train**, pas une double voie complète ni un simple tandem.
Fenêtre droite plate recherchée seulement pour un candidat saturé, caisse
oisive et après délai ; essai borné et mémorisé, pas de scan répété à chaque
tick comme l'ancien V202. Géométrie Opex V202 à reprendre et auditer :
branches de sens opposés, capacité d'accueil de la rame entière, PBS aux
approches ; refus si la sécurité des signaux ou le raccord n'est pas prouvée.
Pas de troisième train. Aucun code AAA copié. Le chargement complet reste
inchangé. Refuser une géométrie impossible est préférable à un clone bloqué.

Transactions persistées, exclusion avec V257 et les expansions historiques,
nettoyage des constructions partielles et reprise de l'ancien service.
À 0, aucun appel au nouveau mécanisme ; pas de changement des fonctions
historiques de choix, construction ou expansion hors gardes explicites.

## Validation pré-enregistrée

Contrats source V284, suite complète comparée à master, undecl/delim comparés
à la base, `git diff --check`. Plafond des trois tests AddSetting : 72→73.
Base undecl : seulement `AICONFIG_BOOLEAN`, `CONFIG_BOOLEAN` ; delim : vide.
Vérifier la persistance par contrats et réconciliation des étapes interrompues.

Budget utilisateur : **un smoke 42×6 actif**, `decision_log=1`, carte 8,
script-debug et télémétrie ; si sain, **au plus une exposition appariée
42/7/1234 ×10**, 0 contre 3, mêmes sondes. VPS : **2 CPU, 2 Go sans swap,
un worker et une seule partie à la fois**, réseau host, cache nommé.
L'exposition est diagnostique : règle explicite `gain_short`, 40 graines
requises ×10, seuil relatif 4 %, garde valeur 5 %, donc `diagnostic_only`
attendu sur trois paires ; aucun verdict d'adoption.
Mesurer trains/ligne fret, places/train, vitesses modélisées et disponibles
dans les sondes, profit rail en 1979 et caisse. Aucun défaut changé, aucun push.
Une proposition 40×10 GitHub sera fournie sans lancement.

## Implémentation et contrôles avant le smoke

Déclencheur et sonde V270 portés manuellement depuis `c71b707` : les points
d'insertion existent sur `a9437f8`, mais le réglage V270 séparé n'est pas
réintroduit. `task_v284.nut` porte la transaction adaptée au remplacement
complet, avec le constructeur commun intact. Un choix/mois et une croissance
par ligne tous les 90 jours au plus ; refus traction/géométrie mémorisé un an.
Priorité distance × attente / capacité ; fret homogène mono-rame seulement.
Deux trains maximum, un seul évitement, 32 fenêtres testées au plus.
Avant l'ouverture effective (âge et caisse), l'expansion historique demeure ;
après, V284 remplace le doublement historique du fret. Le pax reste inchangé.

Le prix de la locomotive départage les matériels qui maintiennent la vitesse,
avec cinq ans d'entretien ; aucune conversion du type de rail. La rame complète
est reconstruite même lorsque le moteur choisi est identique : coût brut et
revente sont distincts, c'est un coût possible de ce premier prototype.
Attente recontrôlée au dépôt, détournement à vide seulement. Les formes
mixtes V163 sont exclues. Quai limité à sa longueur déjà construite.

État entier sauvegardé hors projection mensuelle ; récupération du train
démarré par son identité, suppression des constructions non démarrées et
retour arrière limité aux pièces ajoutées. `Load` lit l'état avant les réglages ;
la réconciliation attend `liveLines`. Aucun round-trip moteur supplémentaire
autorisé dans le budget : cette partie est vérifiée par contrats, pas mesurée
en partie rechargée. Point d'avancement commun aux boucles normale et profilée
dans `_runOrchestratorTick`.

Contrats : 11 V284 ; **suite 2 137 tests OK**, 3 ignorés, 3 échecs attendus
(base 2 126, mêmes exceptions). Les empreintes des fonctions historiques
expansion/constructeur et du corps orchestrateur après retrait des gardes
correspondent à `a9437f8`. Plafond AddSetting **72→73** dans V246/V251/V259.
`undecl` : seulement `AICONFIG_BOOLEAN`/`CONFIG_BOOLEAN`, comme master ;
`delim` et `git diff --check` propres.

API de signalisation vérifiée sur le
[code OpenTTD 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_rail.cpp) :
`AreTilesConnected` ne traverse pas une tête d'ouvrage ; la trace V284
traite donc explicitement l'entrée et la sortie dans l'axe.

Prévol : Docker `default`, socket local `/var/run/docker.sock`, image
`sha256:a0e0a0727f5003532764eeaeee6b83e9ab96a7470df3c76208c6446d10b88c8c`,
volume `openttd-lab-home` présent, aucune campagne moteur en cours.
Montage : `/home/deploy/projects/wt-v284:/work`. Harnais `--help` vérifié,
plafond swap égal aux 2 Go de RAM. Campagne prévue :
`v284_smoke_42x6_20261020`, N=3, un bras actif contre AAA, sans règle A/B.
