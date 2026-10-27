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

## Résultats V2 — 27 octobre 2026

**Mesure achevée ; aucun défaut adopté.** Smoke 9/9 parties (42 × 1 an), puis 27/27 diagnostics (42, 100, 7 × 9 méthodes, durée technique six ans). Les 81 passes sont complètes, les neuf groupes graine/date ont chacun neuf empreintes de début identiques. Zéro erreur NoAI, aucune passe tronquée. 3 402 observations, soit 378 par méthode ; 1 944 sauvegardes avec zéro véhicule et zéro station. Emprunt initial 100 000, inchangé.

La santé générique signale `inactive_company`, attendu ici ; le verdict dédié `engine_script_horizon_ok=true` conserve ce verdict brut et vérifie indépendamment moteur, script, horizon et couverture. Le smoke V2 initial avait une erreur de correspondance méthode/nom de compagnie dans le contrôle Python ; réanalyse séparée des mêmes journaux après correction, sans rejouer les parties.

### Scores et coût

Ratios sur **357** observations à oracle strictement positif ; 21 dénominateurs absents ou nuls exclus. Les parts constructibles utilisent les **378** observations, site absent compris. Les valeurs >1 décrivent souvent une ancre qui réclame un terrassement : elles ne battent pas l’oracle des sites immédiatement constructibles.

| Méthode | Score/oracle médian | p10 | Part = 1 | Constructible sans terrassement | Erreurs 263 | Sans site / oracle trouve | Opcodes médian | Total M | Écart total spirale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| spiral | 1.000 | 0.588 | 27.5 % | 34.9 % | 237 | 9 | 21,135.0 | 14.374 | +0.0 % |
| hybrid | 1.000 | 0.588 | 27.5 % | 34.9 % | 237 | 9 | 17,579.0 | 12.981 | -9.7 % |
| initial | 1.056 | 1.000 | 44.8 % | 34.1 % | 246 | 3 | 32,053.0 | 12.308 | -14.4 % |
| bands | 1.056 | 1.000 | 44.3 % | 33.3 % | 249 | 3 | 18,887.5 | 8.231 | -42.7 % |
| border | 1.000 | 0.848 | 38.7 % | 38.4 % | 218 | 15 | 26,524.0 | 12.317 | -14.3 % |
| funnel | 1.000 | 0.759 | 39.8 % | 46.6 % | 187 | 15 | 37,594.0 | 14.503 | +0.9 % |
| strict | 1.000 | 1.000 | 93.3 % | 92.9 % | 0 | 24 | 29,339.0 | 17.210 | +19.7 % |
| strict_full | 1.000 | 1.000 | 94.1 % | 92.9 % | 0 | 24 | 38,718.5 | 20.973 | +45.9 % |
| oracle | 1.000 | 1.000 | 100.0 % | 99.2 % | 0 | 0 | 285,937.5 | 107.790 | +649.9 % |

L’oracle trouve un site dans 375/378 cas, dont 18 à score nul. `strict` et `strict_full` manquent 24 cas avec site oracle, dont **6 à score positif**, dans deux villes : graine 42/ville 20 et graine 100/ville 17, aux trois dates. Les 24 cas correspondent à huit villes distinctes graine×ville ; ce ne sont pas 24 villes indépendantes.

La médiane du ratio réalisable (zéro pour site absent ou refusé) vaut **0** pour les spirales et les quatre entonnoirs non stricts ; **1** pour les stricts et l’oracle. `strict` atteint l’égalité 333/357 fois, `strict_full` 336/357. Aucune variante ne démontre sur l’ensemble à la fois cette proximité réalisable de l’oracle et moins d’opcodes que la spirale.

### Coût apparié par graine, trois dates réunies

| Graine | Villes/type par date | Spirale M | Hybride Δ | Bandes Δ | Combinaison Δ | Strict Δ | Strict complet Δ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 42 | 4.332 | -8.9 % | -34.9 % | +13.6 % | +53.0 % | +81.4 % |
| 100 | 38 | 5.939 | -2.9 % | -61.3 % | -31.6 % | -10.3 % | +8.4 % |
| 7 | 46 | 4.103 | -20.4 % | -24.1 % | +34.5 % | +28.1 % | +62.7 % |

`strict` est moins coûteux sur 100, mais ce sous-ensemble ne remplace pas le résultat complet. Globalement, les deltas d’opcodes appariés médians sont −3 325 pour l’hybride, −2 948 pour les bandes, +6 764,5 pour strict et +18 280 pour strict complet. Le lecteur livre chaque delta ville/type/date dans `valid.paired`, ainsi que les agrégats par ville et par date.

### Cas recoupés dans les journaux

Tous les exemples suivants concernent la passe cible du 02/01/1970, type 1 (grand aéroport) :

- **Graine 100, ville 6, ligne 34** : `initial` et `bands` reprennent exactement l’ancre **21013**, score **29**, centre couvert, mais `BuildAirport` renvoie **263** ; oracle **19**. `funnel` choisit 20757, score 24, également 263. `strict` et l’oracle choisissent **21018**, score 19, constructible, centre non couvert. Cela mesure une constructibilité sans terrassement, pas le succès d’un chantier de nivellement réel.

- **Graine 42, ville 20, ligne 24** : `strict` retourne null après 17 tests et 210 390 opcodes ; oracle 40168, score 10, centre couvert, 229 024 opcodes. Le score oracle est repris des lignes de l’autre partie ; la cause exacte du rejet préalable n’est pas instrumentée.

- **Graine 100, ville 17, ligne 23** : `funnel` ne trouve rien, zéro test moteur ; `strict` ne trouve rien après un test ; l’oracle trouve 43740, score 1, centre non couvert. Les filtres amont et l’écart temporel doivent être distingués avant d’attribuer le manque à un filtre précis.

- **Graine 100, ville 11, ligne 29** : `funnel` trouve 44429, score 24, constructible, **centre non couvert**, score oracle 24. La couverture du centre n’est donc pas une conséquence automatique d’un bon score C96. L’oracle lui-même laisse le centre hors couverture dans 99 observations.

Le recoupement indépendant relit les 27 fichiers bruts, compare les 3 402 lignes et 3 402 deltas à la spirale (référence comprise), recalcule médianes, p10, totaux, parts =1, refus 263 et parts constructibles : tous égaux au lecteur. `air_site_probe_v2_crosscheck.json` conserve les échantillons bruts et SHA-256 des 27 journaux.

### Corrections proposées, non implémentées dans les modes existants

1. **Séparer « constructible maintenant » de « admis avec nivellement ».** Le succès de `LevelTiles` sous AITestMode ne change pas la carte. Un score >oracle suivi de 263 ne prouve donc pas une meilleure ancre, ni à lui seul un chantier réel impossible. Pour cette sonde, le test strict résout l’ambiguïté ; pour la production, conserver explicitement le statut et le devis de terrassement plutôt que remplacer silencieusement l’admission.

2. **Conserver les bandes comme organisation du travail, puis étudier un contrôle strict moins coûteux.** Bandes seules : −42,7 % d’opcodes, mais 249 refus 263/378 observations. Strict par bandes : 93,3 % d’égalité au score oracle positif, aucun refus final 263, mais +19,7 % d’opcodes. Le prédicat natif de l’hybride est une piste ciblée à associer au strict ; son économie observée seule (−9,7 %) ne garantit pas d’effacer les +19,7 %. Ce cumul n’a pas été testé.

3. **Ne pas employer la couverture du centre comme borne du score.** Le domaine complet strict ne gagne que trois égalités sur 357 par rapport aux bandes, en coûtant 21,9 % de plus que strict par bandes. Réserver un élargissement aux cas encore sous la cible de qualité est une hypothèse ; la seule couverture centrale ne prouve pas qu’une bande externe ne peut mieux scorer.

4. **Examiner les six absences à oracle positif avant d’élargir les filtres.** Oracle teste directement toutes les ancres du domaine ; l’entonnoir conserve CheapOk, acceptation ≥8 et production positive. Ces contrats sont plus restrictifs que « BuildAirport réussit ». La sonde situe le manque, sans prouver quel filtre en est la cause. Aucun filtre historique n’est retiré dans cette livraison.

### Limites et validation

La comparaison est valide **au sens du protocole V2 demandé** : états initiaux échantillonnés égaux. Les passes durent 4–14 jours pour les recherches et **59–70 jours pour l’oracle**. La dernière finit le **12/03/1975**, dans la marge technique autorisée. Les villes ne sont donc pas évaluées au même instant après le début ; les 64 tuiles échantillonnées ne constituent pas un hash exhaustif de la carte. Les 378 observations ne sont ni 378 graines ni une preuve économique. Un seul type disponible a été exposé (type 1) aux trois dates.

Les neuf hashes OFF restent ceux de la base 6c1481a1 après retrait exact des ajouts de démarrage ; aucun ancien hash n’a été rebasé. OFF ajoute la lecture unique obligatoire de `air_site_probe` et sa branche, puis aucun appel de sonde. Aucune équivalence temporelle absolue de la VM n’est revendiquée.

- Tests ciblés : **282 OK**, dont deux échecs attendus préexistants ; lecteur et contrats dédiés : **15 OK**. Délimiteurs, identifiants réservés, absence de closures et références API contrôlés ; compilation/exécution confirmées par les parties.

- Suite complète : **3 028 tests**, 9 ignorés, 2 échecs attendus, **19 erreurs + 1 échec** : 7 erreurs exigent NumPy absent ; 12 erreurs et 1 échec exigent `ai/AAAHogEx-115/info.nut`, absent du worktree. Modules concernés : `test_demo_frontieres_temps_20261025` et `test_v166_aaahogex_settings`. Aucun ajout de dépendance ni d’adversaire.

- `git diff --check` passe. L’IA figée des deux campagnes est byte-identique à celle du commit de livraison.

### Provenance et chemins

Racine des artefacts : `/home/deploy/projects/openttd-ml/.worktrees/air-site-probe/results`.

- Smoke V2 : `air_site_probe_v2_smoke01_20261027.json` (verdict Python initial conservé), `air_site_probe_v2_smoke01_reanalysed.json` (correspondance de compagnie corrigée), manifeste, bundle, `.host.log` et dossier `_engine/` de neuf journaux.

- Diagnostic : `air_site_probe_v2_diag_3seeds_20261027.json`, `.jsonl`, `.manifest.json`, `.host.log`, `_bundle/`, `_engine/seed<42|100|7>_<méthode>.log`.

- Lecteur final : `air_site_probe_v2_reader_final.json` ; recoupement : `air_site_probe_v2_crosscheck.json`. Tests : `air_site_probe_v2_targeted_final.txt`, `air_site_probe_v2_full_tests.txt`.

- Smokes V1 : `air_site_probe_smoke02_20261027_engine/` et `air_site_probe_smoke03_20261027_engine/`, invalidés par la dérive intra-partie ; première tentative arrêtée avant moteur faute d’injection Git dans Docker. Ils ne sont pas agrégés au V2.

- Hash arbre IA : `26b3754a2041aedbd3390a659845dfdf69cbdc5d2ba5989c8b40f23d5cda8a69`.

- Hash bundle diagnostic : `12377d1d306babcc15036be89704a20c45b4f42c29b3212d132b0bb0303fb7cf`.

- Lancement sur arbre non commité de base 6c1481a1, état local et contenu exact conservés dans les manifestes. Le SHA Git seul n’est pas la provenance de ce qui a tourné. Aucun push, merge, changement de défaut ou porte économique.
