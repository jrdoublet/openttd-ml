# RVA — sonde passive du cycle reel

18 octobre 2026. Worktree `/home/deploy/projects/wt-rva`, branche `rva`,
base `2761c824d4bdc9b7b09594fc7761a3e9143ebc0f`, arbre initial propre.
Intervention demandee apres RVA-01 a RVA-03 : observation, sans score,
apprentissage, renouvellement, modification d'ordre ou construction supplementaire.

## Fichiers, fonctions et points d'entree

| Fichier | Ligne / fonction | Intervention |
|---|---|---|
| `ai/OpexAI/globals_pre.nut` | 127 | `RVA_CYCLE_PROBE`, initialise faux |
| `ai/OpexAI/settings.nut` | 70, `OpexLoadSettings` | activation par masque, sans nouvelle lecture de reglage |
| `ai/OpexAI/info.nut` | 32 | description du bit libre 256 ; bornes et defauts inchanges |
| `ai/OpexAI/main.nut` | 651 | chargement du module apres declaration de classe |
| `ai/OpexAI/scheduler.nut` | 9, `_runNextTaskWithSlackLedger` | seule garde recurrente ajoutee au defaut |
| `ai/OpexAI/task_rail.nut` | 1132, `_recordRailAttempt` | prediction apres construction reussie, dans le bloc `DECISION_LOG` existant |
| `ai/OpexAI/probe_rva_cycle.nut` | 11, `OpexRvaCycleValue` | absence encodee `na` |
| meme fichier | 18, `OpexRvaCycleModel` | photographie du modele effectivement execute |
| meme fichier | 37, `OpexRvaCycleSample` | un vehicule et un element de composition par visite |
| meme fichier | 94, `OpexRvaCycleStep` | curseurs reprenables, reliquat, cout |
| `sweeps/analyze_rva_cycle.py` | 17 `value`, 26 `records`, 33 `duration`, 38 `number`, 42 `analyze`, 229 `main` | lecture du journal, reconstruction et JSON |
| `sweeps/fixtures/rva_cycle.log` | 1 | journal synthetique de rotation avec deux cargos |
| `sweeps/test_rva_cycle_probe.py` | 17 `ProbeContract`, 64 `Reader` | 13 contrats/fixtures sans moteur |
| `sweeps/test_v167_probes.py` | 43, 189 | commentaires actualises : 256 a une garde dediee |
| `docs/taches.md` | Etat courant | livraison et validation moteur restante |

## Activation et inertie

Le bit **256** etait vide depuis V239. `probes=258` active la sonde et conserve
les panneaux ; `256` seul active aussi le journal, mais retire les panneaux
necessaires aux bancs usuels. Employer **258** dans les harnais. `probes=2`
reste le defaut aux quatre difficultes. `probes=1` exclut toujours 256 ;
`decision_log=1` seul n'active pas cette sonde. Le bit libre isole mieux cette
collecte temporelle du journal general, deja tres utilise. Aucun `AddSetting`
ajoute ; plafond de 76 verifie par le contrat V246 existant.

Au defaut, le point recurrent ajoute seulement `if (RVA_CYCLE_PROBE)` : aucun
appel de sonde, getter de vehicule, allocation de travail ou journal RVA.
Le crochet de construction se trouve dans un bloc `DECISION_LOG` deja saute au
defaut. Il reste le chargement initial du module et l'affectation initiale du bit :
ce n'est pas une preuve d'identite binaire/opcodes du demarrage avec master.
La lecture/garde recurrente autorisee est la seule difference du chemin de jeu
au defaut. L'identite de trajectoire n'a pas ete mesuree et ne peut pas etre
deduite de contrats Python. ON consomme des opcodes et peut decaler la trajectoire.

Aucune famille protegee modifiee. V207 lu uniquement, sans changement de code,
de defaut ou d'activation. Aucun etat ajoute aux lignes ni a Save/Load : la
telemetrie est transitoire et repart avec `RVA_BEGIN` apres chargement/redepart.
Les lignes rechargees sans photographie `RVA_MODEL` ont des durees observables,
mais leurs residus de modele restent non couverts.

## Decoupage et cout

Le crochet commun aux boucles normale et profilee de l'ordonnanceur visite
l'inventaire existant `_lines` / `line.vehicles` par curseurs. Une visite traite
un cargo d'initialisation, un saut de ligne, un vehicule, ou une fin de tour.
Aucun inventaire mondial, boucle de flotte par tick, nouveau Sleep ou file
prioritaire. Le numero d'element de composition est `sweep % GetNumWagons` :
la lecture des moteurs de tous les elements s'etale sur plusieurs tours.
La composition est donc echantillonnee, pas une photographie atomique.

Le plancher `C67_SLACK_MIN` et la reserve `C67_SLACK_RESERVE` sont reutilises
en lecture seule (4000/3000 dans `task_terrain.nut:10-11`). Aucun budget numerique
nouveau choisi sans mesure. Une visite est differee si le reliquat est inferieur
au pic de cout observe plus la reserve. Une unite de travail reste indivisible ;
la borne temporelle stricte doit etre confirmee en moteur. `tick_end` expose un
eventuel franchissement de tick. Un pic trop grand peut empecher les visites
suivantes : absence de couverture a diagnostiquer, jamais mesure nulle.

`OpexOpsMeasureBegin/End` reutilise le compteur existant, y compris lors d'un
franchissement de tick. `RVA_COST` publie prefixe courant, total de la visite
precedente, cumul des appels termines (y compris ceux differes), appels et
reports, ainsi que le cumul du crochet modele. Le total d'une visite inclut son
emission comptable, publiee avec un retard d'une visite. Le lecteur donne un
total mesure et des opcodes par observation lorsque la couverture le permet.
Ces nombres couvrent les intervalles entre marqueurs : entree/sortie des
marqueurs, derniers compteurs/retour et derniere queue non publiee ne sont pas
couverts. Ce n'est pas un total exact du surcout VM complet. Aucun cout moteur
reel n'est revendique avant execution par l'utilisateur.

## Evenements et format

Canal existant `OpexDecide` : `OPEX AAAA-M-J RVA_TYPE cle=valeur ...`.
Valeur absente `na`, convertie en JSON `null`, jamais remplacee par zero.
Le lecteur accepte le prefixe moteur qui precede `OPEX`. Un fichier d'entree
doit concerner une seule partie et une seule compagnie OpexAI.

| Evenement | Champs et sens |
|---|---|
| `RVA_BEGIN` | version, horloges, `timekeeping`, `model_ticks_day=74`, `model_days_month=30`, unite de longueur, reset |
| `RVA_CARGOS` | premier cargo de classe courrier trouve via API, nombre de cargos courrier, perimetre explicite |
| `RVA_MODEL` | `line`, `model_date` de photographie apres succes, StationIDs A/B, trajet, frequence, headway, age tarifaire, capacites prevues par rame, nombre de rames, capacite mensuelle totale, dwell V216f, cargos et pourcentage V216f |
| `RVA_MODEL_COST` | ligne et cout du prefixe du crochet de construction |
| `RVA_SAMPLE` | sequence/tour, ligne/vehicule/date de construction, ticks debut/fin, date calendaire, phase, etat API, tuile, StationIDs A/B, moteur, age, longueur en 1/16 de tuile, nombre et index d'elements, moteur d'element, cargos, capacites et charges, destination de l'ordre courant |
| `RVA_LOST` | identite et instant d'un vehicule devenu invalide dans l'inventaire |
| `RVA_SWEEP` | tour termine, taille de l'inventaire, lignes admissibles visitees, observations et pertes ; compte de parcours, pas recensement atomique |
| `RVA_COST` | sequence, `ops_prefix`, `previous_total`, `completed_ops`, `calls`, `skipped`, `model_completed_ops` |

Phases : `A`/`B` = chargement/dechargement a la gare correspondante,
`R` = hors sejour observe (etat API conserve, pannes et arrets inclus),
`D` = depot, `X` = autre gare/crash/etat invalide. Les deux extremites ne sont
jamais confondues par proximite geographique. Les API de lecture sont celles du
[vehicule OpenTTD 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_vehicle.hpp)
et des [ordres 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_order.hpp).

Le lecteur exige la suite observee A→R→B→R→A→R pour compter une rotation.
Chaque transition appartient a l'intervalle entre derniere observation de
l'ancien etat et fin de la premiere observation du nouvel etat. Les differences
d'intervalles donnent aller, retour, sejours et cycle. Le JSON conserve
`sampled_complete` et `exhaustive_coverage=not_covered` : une rotation entiere
cachee entre deux visites ne peut pas etre exclue. Les transitions impossibles,
detours, changements d'ordre non observes en gare, changements de composition,
pertes, debuts tronques, fin de journal et reprise sont explicites dans `missing`.
Les frequences de passage manquantes ne sont pas extrapolees.

Les causes des sejours restent inconnues : ni plein chargement ni attente de
production deduits d'une charge stable. Capacites et charges sont celles de la
rame effective. Second cargo declare prioritaire ; sinon observation du premier
cargo courrier accessible, meme avec V207 a zero. Plusieurs cargos courrier
NewGRF sont signales par `mail_classes` : couverture additionnelle non acquise.
Les moteurs d'elements ne pretendent pas decrire des parties internes non
exposees par l'API NoAI. Aucun refit ou depot virtuel.

Residus couverts uniquement avec photographie de construction correspondante,
horloge calendaire connue (`timekeeping=0`) et duree de cycle strictement
positive. Les 74 ticks/jour et 30 jours/mois sont les hypotheses existantes du
modele V216f, journalisees comme telles, pas de nouvelles constantes physiques
universelles. `dwell_model_days = 30/trips_month - one_way_days` restitue le
terme effectivement utilise pour le debit ; le headway brut et l'age tarifaire
restent exposes separement. Le lecteur donne residus trajet/sejour/cycle et
debit de capacite par rame/cargo, avec intervalles. La somme des charges au
depart donne seulement un proxy de charge transportee, **pas des livraisons**,
ni un revenu ou gain compagnie. Aucun melange des capacites voyageurs/courrier.

## Verification executee

Commande demandee :

```bash
PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"
```

1 933 tests, verts, 3 ignores par leurs gardes existantes. Les 13 nouveaux tests
couvrent garde/defaut, nombre de reglages, appels API uniquement en lecture,
absence de consommateur metier et de boucle de flotte, unites, rotation mixte,
bornes temporelles, journal tronque, gare sautee, depot, perte, refit, reprise,
horloge inconnue/wallclock, modele absent, courrier absent, horloge incoherente,
ordre change entre observations, identite incomplete et comptabilite.
Les messages de smoke/qualification apparaissant dans la sortie de unittest
proviennent de fixtures : aucune vraie partie n'a ete lancee.

Lecteur exerce aussi en CLI :

```bash
python3 sweeps/analyze_rva_cycle.py sweeps/fixtures/rva_cycle.log --out results/rva_cycle_fixture_20261018.json
```

`git diff --check` vert. Aucun Docker, OpenTTD ou smoke ; Squirrel non compile
dans le moteur, Save/Load reel non execute. Resultats Python locaux dans
`results/rva_cycle_unittest_final_20261018.log` et JSON de fixture ; pas de preuve
economique ni d'adoption.

## Plan propose a executer par l'utilisateur

1. Smoke technique 42 × 1 an, avec les harnais existants, code fige et journaux
   moteur captures (`--script-debug` ; `--probes 258` dans le lanceur peut aussi
   l'activer automatiquement). Comparer le defaut livre `OpexAI[probes=2]` a la
   reference master correspondante pour compilation/sante et inertie. L'absence
   de voyageur a un an rend le smoke insuffisant pour l'exposition du cycle.
2. Diagnostic d'exposition **rail seul**, graines predeclarees 42/100/999,
   **3 ans** : bras OFF `OpexAI[mode_air=0,mode_road=0,mode_water=0,probes=2]`,
   bras ON `OpexAI[mode_air=0,mode_road=0,mode_water=0,probes=258]`. Meme arbre,
   carte, difficulte, autres defauts et AAA figee ; conserver les panneaux.
   Il s'agit d'exposition et de perturbation instrumentale, pas d'un A/B economique
   d'adoption. Ne pas utiliser `--probes` commun pour cette comparaison ON/OFF :
   les masques sont dans les bras ; passer `--script-debug` explicitement.
3. Verifier **avant d'interpreter les residus** : une construction OpexAI reussie
   avec `kind=pax` (jointure `RAIL_BUILD`, `RVA_MODEL`, `line`, date, stations),
   `RVA_SAMPLE` avec capacite voyageurs positive, moteurs/longueur compares a
   une sauvegarde, composition complete, puis rotations A→R→B→R→A→R. Comparer
   dates, etats, charges et ordres aux sauvegardes disponibles. Examiner taux
   de transitions manquantes, intervalles et cout/pic ; aucune cadence nominale
   n'est declaree valide avant cette mesure.
4. **V207=0 ne desactive pas le rail voyageurs de base.** Dans
   `candidates.nut:1031`, la part nulle retombe sur `TOWN_CATCHMENT_SHARE_PCT` ;
   `OpexMakeCandidate(..., "pax", ...)` demeure appele. V207 a zero retire ses
   options, dont le courrier ajoute (`hasMail`, ligne 981), pas la production
   des candidats voyageurs. Le rail seul retire la concurrence des achats AIR,
   route et eau dans notre portefeuille sans changer V207, V177 ou V217.
   Cela ne garantit pas qu'une graine construise du voyageur : si les traces ne
   prouvent aucune rame, resultat **non couvert**. Ne pas forcer une construction
   ou rallumer V207 pour obtenir des observations. Une sauvegarde identifiee ou
   une graine deja documentee avec une rame construite par OpexAI peut servir
   de fixture technique distincte ; elle ne remplace pas les preuves au defaut.
   Une capacite courrier nulle observee est un vrai zero ; sans rame mixte,
   le cycle de courrier a capacite positive reste non couvert.
5. Apres resolution satisfaisante, diagnostic **complet** sur les memes graines
   et **3 ans**, `OpexAI[probes=2]` / `OpexAI[probes=258]`, tous modes aux defauts.
   Sans voyageurs, conserver le constat ; ne pas generaliser le rail seul.
   Prevoir aussi un chargement de sauvegarde avec le harnais existant : verifier
   `RVA_BEGIN`, aucune rotation traverse le reset, residus absents sans modele
   de construction dans la nouvelle session. Le profil VPS reste 3 CPU/2 Go/3
   workers, sans campagnes concurrentes ; verifier contexte/cache/montage avant
   les lancements. Aucun de ces lancements n'a ete execute ici.

Le cout collecte ne prouve pas une neutralite economique, et la sonde n'adopte
aucune nouvelle politique. Les portes V102 ne sont pas declenchees pour cette
livraison de mesure seule. Prochain travail : validation moteur et resolution
effective, puis attribution d'une erreur observable avant tout nouveau score.

FIN
