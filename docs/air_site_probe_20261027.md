# Recherche AIR sans construction — pré-enregistrement du 27/10/2026

## Protocole courant V2 — correction utilisateur après le smoke V1

**Ce protocole remplace la comparaison intra-partie décrite plus bas.** Le smoke
V1 a dérivé de 137 jours et de 35 092 à 38 871 habitants. Ses résultats ne font
pas preuve d'une comparaison à carte commune.

Une partie solo par graine **et méthode**, aucune construction, mêmes dates de
départ de passe : 02/01/1970, 01/01/1972, 01/01/1975. `air_site_probe` :

| Valeur | Méthode |
|---:|---|
| 0 | OFF, défaut conservé |
| 1 | spirale historique |
| 2 | spirale hybride |
| 3 | entonnoir initial `8010b084` |
| 4 | bandes de `ff419e15`, coût/bord désactivés |
| 5 | bandes + rejet du bord, pénalité de pente nulle |
| 6 | combinaison `ff419e15`, pénalité 4 |
| 7 | bandes + BuildAirport strict, coût/bord désactivés |
| 8 | domaine complet + BuildAirport strict, coût/bord désactivés |
| 9 | oracle exhaustif |

Les variantes 3–8 conservent le prédicat historique d'emprise. Le mode 2 seul
utilise le prédicat natif de la spirale hybride. Les caches et budgets sont ceux
recensés plus bas. Les villes/types éligibles sont recensés avant le premier
appel de méthode ; l'ordre des cas est commun aux parties.

**Validation pré-enregistrée :** smoke 42 × 1 an × 9 méthodes, puis diagnostic
42, 100, 7 × 9 méthodes. Pour terminer les calculs déclenchés au 01/01/1975,
l'utilisateur autorise explicitement **`--years 6`**, sans nouvelle date de
mesure, construction ou activité économique. Toute passe sans fin est marquée
`truncated=1` par le lecteur et exclue. Il ne s'agit ni d'une porte A ni B.

Les neuf empreintes de **début** doivent être égales, pour chaque graine/date ;
la lecture de l'empreinte doit avoir lieu à la date cible. Fin de passe et dates
effectives de chaque méthode restent journalisées, sans exiger la stabilité
début/fin. Destruction/construction/emprunt restent interdits. Les neuf listes
ville/type doivent être complètes et identiques. Une incohérence invalide tout
le groupe graine/date, sans conserver un sous-ensemble favorable.

L'oracle provient d'une autre partie : ses champs sont `null` dans les journaux
bruts des méthodes, puis joints par le lecteur avec provenance source/ligne.
Le lecteur apparie par graine, date cible, ville et type, jamais par source de
journal. Les statistiques comprennent aussi les deltas appariés à la spirale.
Les ratios supérieurs à un et les refus 263 restent visibles.

**Limite conservée :** l'égalité de l'empreinte initiale échantillonnée ne signifie
pas que chaque ville est évaluée au même instant. Les différences de durée après
le début de passe restent une limite de ce protocole accepté ; les dates réelles
permettent de la quantifier. Aucun gel de carte implicite.

Lanceur hôte : `sweeps/run_air_site_probe.py --docker --years 1 --seeds 42 --out
<chemin absolu neuf dans results/>`, puis `--years 6 --seeds 42 100 7
--smoke-result <JSON du smoke sain>`. Profil VPS 3 CPU, 2 Go RAM/swap, **3 workers**,
cache `openttd-lab-home`. Un seul lot Docker à la fois. Le diagnostic exige le
même hash d'IA que le smoke. Le gel du code/harnais/bibliothèques et les journaux
par `seed<m>_<méthode>.log` précèdent l'analyse.

## Protocole V1 historique — conservé pour expliquer les premiers smokes

Branche `air-site-probe`, base `6c1481a137938a45564d6273c62f094855fe0853`.
Un seul réglage neuf `air_site_probe=1`, défaut 0 aux quatre difficultés.
Les défauts existants, les méthodes de production et le générateur PO01C ne changent pas.
Commits locaux autorisés ; aucune publication ni fusion. Aucun banc économique.

## Protocole avant mesure

Smoke solo graine 42, un an, puis seulement si sain diagnostics solo 42, 100, 7,
cinq ans maximum (autorisation utilisateur explicite dans la session).
Docker local VPS `openttd-lab`, image
`sha256:a0e0a0727f5003532764eeaeee6b83e9ab96a7470df3c76208c6446d10b88c8c`,
3 CPU, 2 Go RAM/swap, un worker, volume `openttd-lab-home:/home/lab`.
Le lanceur `sweeps/run_air_site_probe.py` fige avant lancement code, harnais,
bibliothèques, réglages et configuration avec les helpers de `campaign_freeze.py`.
Il exécute les copies figées, réutilise `bench_v2.keep`, le nettoyage existant et
`game_health.assess_game`. Le manifeste est solo ; AAAHogEx n'est pas chargé.

Dates visées : 02/01/1970, 01/01/1972, 01/01/1975. Une passe contient toutes les
villes de population au moins `V93_AIRPORT_MIN_POP`, admises par la difficulté,
et tous les types disponibles d'aéroport terrestre à piste. Pas de filtre de
portefeuille, avion ou population maximale des petits aéroports ; héliports exclus.
Pour chaque ville/type : spirale, hybride, initial `8010b084`, bandes seules,
bord sans pénalité, combinaison `ff419e15`, strict par bandes, strict domaine
entier, oracle. Chaque recherche reçoit 1 500 sondes et une ville restante,
indépendamment de l'ordre du planificateur. L'oracle ne reçoit pas de plafond.

Les copies historiques sont renommées et chargées exclusivement ON ; leurs
wrappers d'installation sont retirés, traces remplacées par une sortie canonique,
compteur d'ancres ajouté. La spirale appelle l'original conservé ; seul son
constructeur de liste est remplacé ON par une copie avec compteur. C96 est muet
dans toutes les méthodes. `tiles` compte les ancres présentées aux filtres natifs
(oracle : domaine géométrique et ville propriétaire) ; `tested` compte les sondes
BuildAirport dans la méthode. Ces deux compteurs ne sont pas interchangeables.

Caches vidés avant chaque méthode : `AIR_SITE_CACHE`,
`AIR_STATION_COVERAGE_TOWN_CACHE`, `AIR_C121_STATION_COVERAGE_CACHE`,
`C121_AIR_ENDPOINT_CACHE`, `AIR_DEMAND_PAX_CARGO`, marques/cumuls AIR_SITE_SEARCH ;
DEAD/LIST/RAW/PEN et mois de l'entonnoir récupéré ; job/pending/lineState PO01C.
La sonde n'entre jamais dans le scheduler et ne crée aucun générateur PO01C.
Pas de Save/Load : reprise refusée ; nouvelle partie solo obligatoire.

L'oracle énumère les ancres jouables du domaine historique, Chebyshev 4..25,
distance Manhattan au rectangle ≤25, `GetNearestTown` identique, sans filtre
CheapOk ni supposition de nivellement. Il maximise C96 parmi les BuildAirport
réellement réussis sous AITestMode. Il peut retourner un score nul. Score absent
et oracle nul ne deviennent pas des dénominateurs artificiels.

Une portée AITestMode englobe toute la sonde, avant le chargement des réglages,
avant SetName, tout emprunt, le scheduler et les véhicules. Chaque test de
constructibilité final journalise immédiatement le code natif (dont 263) et le
devis AIAccounting si réussi ; un devis refusé reste null. Un LevelTiles en test
ne transforme pas la carte : l'oracle strict ne promet pas une construction après
terrassement. L'emprunt initial imposé par le moteur est enregistré, jamais changé.

## Validité et limites pré-enregistrées

Empreintes début/fin de passe et de groupe ville/type : nombre de villes, somme
des populations, nombre d'industries, 64 échantillons déterministes de classes
de tuile et hauteurs. Cette empreinte échantillonnée n'est pas une preuve de carte
entière identique. Les dates réelles début/fin sont aussi conservées.
Une empreinte différente, date dérivée, méthode absente, ligne dupliquée, horizon
incomplet ou compteur de construction/emprunt changé interdit les tableaux valides.
Les données invalides restent consultables séparément, sans conclusion comparative.

La VM peut suspendre automatiquement et la carte continuer d'évoluer. Aucun gel
du moteur n'est supposé. Si le smoke révèle cette dérive, ne pas lancer 3×5 en
espérant une stabilité statistique : il faut un protocole de snapshot moteur.
De plus `365*5` jours du harnais ne garantit pas l'achèvement de la passe du
01/01/1975 : ne pas prolonger silencieusement au-delà de l'horizon autorisé.

Opérations mesurées entre OpexOpsMeasureBegin/End pour chaque méthode, y compris
les suspensions automatiques, convention AIR_SITE_SEARCH à 10 000 opcodes/tick.
Pas de Sleep dans la mesure. Réinitialisations, empreintes, score final et
publication exclus. Ce sont des opcodes VM estimés, pas un chronométrage CPU natif.
Le coût du compteur de candidats est inclus et documenté.

OFF ajoute seulement la lecture unique du nouveau réglage au démarrage et sa
branche ; aucune API de sonde, require de sonde ou modification de boucle chaude.
L'absence absolue de lecture API serait incompatible avec un réglage NoAI.
Les hashes des fichiers historiques sont conservés ; la projection OFF des quatre
fichiers d'intégration est figée dans `air_site_probe_off_hashes.json`.

Lecteur : médiane/p10 score-oracle, part égale à un, constructibilité, villes sans
site avec oracle, médiane/total opcodes, deltas appariés par source/date/ville/type.
Un site absent vaut zéro en ratio si l'oracle est strictement positif ; un score
supérieur à l'oracle reste visible et ne prouve pas un meilleur site s'il est
inconstructible. Un ratio réalisable complémentaire met ces refus à zéro.

Les corrections proposées devront être appuyées par des passes valides, couverture
complète et moins d'opcodes. Sinon, elles restent des hypothèses, sans adoption.
