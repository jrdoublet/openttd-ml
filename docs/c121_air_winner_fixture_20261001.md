# C121 — exposition et fixture du gagnant AIR

## Résultat

**Le raccourci limité à `fleetScanCap=1` n'est pas une optimisation utile dans
ce pilote : aucun des 2 289 recalculs observés n'y est éligible.** Ne pas
l'intégrer seul. La prochaine intervention à prototyper est la fusion générale
qui conserve l'ouverture N=1 pendant le scan complet, sans modifier ses argmax.

La demande « fais la prochaine étape » a été traitée par une fixture NoAI et
deux parties instrumentées de 1 an, graines 42/100, exécutées successivement.
Aucun fichier de production, défaut ou politique n'a été modifié par ce lot.
Les variantes depth/split rejetées sont exercées seulement dans la matrice de
compatibilité puis restaurées ; elles restent désarmées en activité naturelle.

## Exposition naturelle

| Graine | Topologie | Recalculs du gagnant | Cap min–max | Cap médian |
|---:|---|---:|---:|---:|
| 42 | newpair | 892 | 7–13 | 9 |
| 42 | hubsite | 340 | 7–13 | 10 |
| 42 | hubhub | 28 | 9–12 | 10 |
| 100 | newpair | 559 | 7–13 | 9 |
| 100 | hubsite | 420 | 6–12 | 9 |
| 100 | hubhub | 50 | 7–11 | 10 |

Comptage des appels complets du gagnant à l'intérieur du chooser, pas des
constructions ni des paires uniques. Une même paire peut être recalculée.
Les hits de catalogue sans appel au chooser ne sont pas comptés ; les calculs
post-build sont exclus. Les partitions MAIL restent distinctes dans les JSON :
178/95 appels newpair à MAIL inconnu, 714/464 à MAIL positif sur 42/100 ; tous
les hubs observés sont à MAIL positif. MAIL connu nul n'est pas exposé en
activité naturelle, mais est testé dans la matrice.

Ce résultat s'explique par `OpexC121AirFleetScanCap` : le cap inclut une borne
de fréquence `ceil(roundTripDays / 7.5)`, en plus des besoins directionnels de
PASS/MAIL. Une faible demande n'implique donc pas un cap=1. La fusion générale
éliminerait un point N=1 et une préparation, même quand le cap vaut 6–13 ; son
gain net **n'a pas été mesuré** ici. Les 3,2 M d'opcodes rapportés sur le VPS
restent le coût du poste entier, sans identité de protocole attestée.

## Contrat vérifié en VM

Fixture [c121_winner_vm.nut](../tests/mechanisms/c121_winner_vm.nut), lanceur
[run_c121_winner_fixtures.py](../sweeps/run_c121_winner_fixtures.py).
Le prototype compare les deux appels courants à : appel d'ouverture, puis
copie indépendante de l'objet extérieur et de `decisionEconomics` si cap=1,
ouverture N=1 et date inchangée ; double appel courant dans les autres cas.
Pendant la partie naturelle, le wrapper retourne toujours le résultat courant.

Chaque graine exerce **72 cas** sur les entrées d'une vraie route :
caps forcés 1/2/4 × MAIL inconnu/connu nul/connu positif × quatre modes de score
(normal, portfolio-depth, split, decision-depth) × AAA_LINE 0/1. Les capacités
MAIL positives dirigées sont un input de test, pas une observation d'avion.
Comparaison récursive stricte des clés, types et valeurs : ouverture, résultat
complet et objets de décision. Les mutations testent l'indépendance des deux
objets copiés. Les cas AAA_LINE ouvrent N=2 et conservent les deux appels.
Les fonctions, capacités observées et flags remplacés sont restaurés.

Des suspensions peuvent franchir une date : chaque comparaison dirigée est
retenue seulement si les deux chemins finissent le même jour qu'ils commencent.
Le lecteur exige les 72 cas et leur stabilité. Les mesures qui franchissent
un jour sont écartées puis le cas est rejoué, au plus huit tentatives ; six
cas ont nécessité une reprise sur chaque graine. Ce sont des reprises de
fixtures, sans recherche d'un résultat économique favorable.

Pour les douze cas éligibles dirigés par graine, coût cumulé des **deux appels**
avec la même instrumentation, gardes et copies incluses, comparaison exclue :

| Graine | Témoin | Prototype cap=1 | Réduction |
|---:|---:|---:|---:|
| 42 | 62 653 opcodes | 31 903 opcodes | 49,08 % |
| 100 | 62 677 opcodes | 31 917 opcodes | 49,08 % |

Ces chiffres concernent des caps **forcés**, sur une route par graine. Ils ne
prouvent aucun gain naturel : zéro cas naturel éligible, aucune économie du
catalogue démontrée. L'instrumentation et la matrice modifient le calendrier
du jeu ; les différences de trajectoire entre essais ne sont pas économiques.

## Exécution et preuves

Arbre `c121-catalog`, HEAD `52ab55537dcf18a0ded8700bc9ac73833ac369a5`, dirty
préexistant préservé. La provenance exécutée repose sur les empreintes de tous
les fichiers locaux AI/harnais, de la copie instrumentée et des bibliothèques
dans chaque `plan.json`, pas sur le SHA seul. Un seul bras par lancement.

Image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
contexte `desktop-linux`, limites 3 CPU/2 Go/swap interdit, volume
`openttd-lab-home`, montage vérifié `/work`. Runtime du harnais : OpenTTD 15.3,
OpenGFX 7.1, OpenTTDLab 0.0.75 ; configuration 256×256, départ 1970,
inflation OFF, profil solo courant de `bench_v2.make_cfg`. Un worker,
`c121_air_economics=1`, autres réglages aux défauts de la copie courante.

Le pilote 42 initial `20261001_seed42_pilot01` a échoué avant jeu sur timeout
BaNaNaS. Les relances utilisent les quatre tars présents au cache, vérifiés
par les empreintes des groupes transitifs de `_tmp_smoke_test.manifest.json`,
copiés dans chaque sortie et servis par le descripteur local du harnais figé.
Ce manifeste sert uniquement à identifier les bibliothèques, pas de preuve
économique. Le pilote02 a conservé un verdict **non validé** : quatre mesures
de matrice traversaient un jour. Aucune preuve de cet essai n'a été écrasée.

Preuves retenues, `plan.json`, `report.json`, `engine.log`, sauvegardes mensuelles,
copies AI et bibliothèques sous :

- `results/c121_winner_single_scan/20261001_seed42_pilot03/`
- `results/c121_winner_single_scan/20261001_seed100_pilot01/`

Deux rapports `pass=true`, santé `game_ok=true`, aucune erreur NoAI,
13 sauvegardes exactes du 1970-01-01 au 1971-01-01, sources/copies/fixture
inchangées pendant chaque exécution. Empreinte commune de la fixture :
`99229a14d76365f4c38b409b7d0414e674159425f618d1bd0056a811ae439bc0`.
La vérification finale constate des éditions concurrentes **après** les pilotes
dans `globals_pre.nut`, `info.nut`, `settings.nut`, `task_air.nut` et
`task_projects.nut`. Elles sont préservées. Les résultats portent sur les
copies/empreintes retenues, pas automatiquement sur ces nouvelles sources.
Huit tests Python ciblés réussis ; ils vérifient staging, lecture des preuves
et refus des bibliothèques mal identifiées,
la compilation/exécution Squirrel est attestée par les deux parties.

## Limites et prochaine porte

**Suite exécutée :** [prototype de fusion générale](c121_air_winner_fusion_20261001.md),
1 230 comparaisons naturelles exactes sur42/100 et 144 cas dirigés ; baisse
du coût du gagnant14,44 %/14,85 %. Intégration et gain catalogue non qualifiés.

Ce lot valide le contrat du raccourci et conclut à son absence d'exposition dans
ce profil ; il ne valide pas une fusion générale. Pas de matrice explicite
d'égalités d'argmax, de retour nul, de changement de tarif mensuel, ni de
facteurs de réalisation variés. Les routes asymétriques/concurrentes ne sont
pas une matrice dirigée exhaustive. La garde de date est conservatrice et
l'inflation OFF ne qualifie pas la frontière tarifaire.

Prochain lot : ajouter **dans une copie** une sortie d'ouverture du scan général,
capturée à N=1 avant annotations globales, puis finalisée comme le fixedN=1
courant avec des objets indépendants. Garder tous les N et départages, repli
AAA_LINE et chemin témoin ; comparer les deux résultats récursivement aux caps
naturels 6–13 et mesurer le coût net. Ne pas mélanger réduction des snapshots,
nouveau contexte moteur ou changement de score. Aucun 5×6/20×10 ni adoption
n'est déclenché par ce lot technique.
