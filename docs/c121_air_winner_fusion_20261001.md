# C121 — prototype de fusion générale du gagnant

**Résultats strictement identiques dans ce pilote ; réduction de 14,44 % /
14,85 % du coût du gagnant sur les graines42/100.** Aucun changement de
production ni adoption. Le gain concerne ouverture + calcul complet du
gagnant, pas le catalogue entier.

## Intervention isolée

Suite au [pilote cap=1](c121_air_winner_fixture_20261001.md), demande utilisateur
« fais la prochaine étape ». Le [lanceur](../sweeps/run_c121_fusion_fixtures.py)
génère une fonction candidate depuis le corps exact du modèle copié. Les
fonctions originales restent intactes et servent de témoin dans la même VM.

Le scan conserve tous les N et les comparaisons d'argmax. À N=1, avant les
annotations globales, il clone séparément les snapshots profit et score.
Une finalisation issue du bloc courant les annote comme l'appel fixedN=1 :
`fleetEvaluated=1`, décision N=1, mêmes types/clés/valeurs. Le wrapper ajoute
`engineMailKnown` à l'ouverture et à son objet de décision. Le scan poursuit
sa recherche complète. AAA_LINE conserve les deux appels pour son ouverture N=2.

La [fixture](../tests/mechanisms/c121_fusion_vm.nut) retourne toujours les
résultats témoins pendant l'activité naturelle ; la fusion est recalculée à
côté. Aucun projet ni score du portefeuille n'utilise la sortie candidate.
Les tests de mutation vérifient que l'ouverture ne partage ni objet extérieur
ni `decisionEconomics` avec le résultat complet. Leur coût et celui de la
comparaison récursive sont exclus du chronométrage.

## Mesures sur entrées naturelles

Deux solos successifs, graines42/100 ×1 an, C121 économie ON, autres réglages
aux défauts de l'arbre copié. Comparaison stricte des clés, types et valeurs
de l'ouverture, du résultat complet et de leurs objets de décision. Un
échantillon est retenu seulement si les deux chemins, y compris l'ouverture
témoin, s'exécutent le même jour.

| Graine | Recalculs observés | Comparaisons stables | Op. témoin | Op. fusion | Réduction |
|---:|---:|---:|---:|---:|---:|
| 42 | 778 | 621 | 11 533 431 | 9 867 969 | 14,44 % |
| 100 | 778 | 609 | 11 481 486 | 9 776 123 | 14,85 % |

Op. = opcodes cumulés sur les seules comparaisons stables, préparation, scan
et copies inclus. Le témoin mesure ses deux appels indépendamment ; le
candidat inclut aussi son petit wrapper et son objet de sortie. Ces derniers
sont donc facturés au candidat. Compteurs : `OpexAirCalcDeltaOps`, tick/opcodes
avant chaque chemin. Ce n'est pas un A/B de parties ni le compteur annuel
d'une IA sans fixture. Les 157/169 comparaisons traversant une date sont
exclues des sommes et du verdict d'équivalence, conservées dans les logs.

| Topologie | Comparaisons42 / 100 | Réduction42 / 100 |
|---|---:|---:|
| newpair | 481 / 406 | 14,70 % / 14,93 % |
| hubsite | 131 / 189 | 13,72 % / 14,80 % |
| hubhub | 9 / 14 | 13,43 % / 13,64 % |

Caps observés : 7–13 sur42, 6–13 sur100. Parmi les comparaisons stables,
MAIL inconnu156/81 et MAIL positif465/528. MAIL connu nul est exercé seulement
en matrice. Comptage des recalculs, pas de paires uniques ou de builds ; hits
sans chooser et post-build exclus. Peu de cas hubhub, portée limitée.

## Cas dirigés et contrôles

**72 cas par graine, tous réussis** : caps forcés1/6/13 × MAIL inconnu/connu
nul/connu positif × quatre modes de score × AAA_LINE0/1. Les modes rejetés
depth/split sont exercés seulement pour compatibilité, puis restaurés.
Le lecteur exige le domaine cartésien complet, les identifiants1–72, les dates
stables et la restauration. Les mesures traversant une date sont rejouées au
plus huit fois : onze cas ont eu une reprise sur42, neuf sur100. Contrôles de
VM, pas relances économiques. Contrat nul testé avec avion nul ; les cas
AAA_LINE sont des replis vers le témoin, pas des cas de fusion.

**14 tests Python ciblés réussis** : six nouveaux couvrent staging, témoin,
anchors du générateur, argmax/scan, domaine de preuve et exclusion des mesures
instables ; huit réutilisés couvrent l'ancien lanceur et les bibliothèques.
La compilation Squirrel est attestée par les deux parties, pas par Python.

## Provenance et santé

Branche `c121-catalog`, HEAD `52ab55537dcf18a0ded8700bc9ac73833ac369a5`, arbre
dirty préexistant conservé. Chaque plan porte les empreintes des sources,
de la copie témoin+candidat et des bibliothèques transitives. Le générateur
exécuté est conservé dans `executed_runner.py`. Modèle original :
`0157e8df026bf2490c6d7784a4ae69ff250eaca1fca1be39e6c31d8e39a04e37`.
Fixture fusion :
`ebfdeca86690d3743b8563df728a87b9428e0fca9d6a88c585316adfc46d38d6`.

Docker `desktop-linux`, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
3 CPU/2 Go/swap interdit, volume `openttd-lab-home`, montage `/work`, un worker.
La campagne préexistante a été attendue avant lancement. Harnais courant
`save_load_roundtrip.run_phase_a`, configuration `bench_v2.make_cfg(1970)` :
256×256, inflation OFF, moteur15.3/OpenGFX7.1/OpenTTDLab0.0.75. Quatre tars
transitifs du cache vérifiés par SHA256, descripteur local du harnais figé.

Preuves, plans/rapports/logs/JSONL/sauvegardes/copies/bibliothèques :

- `results/c121_winner_fusion/20261001_seed42_pilot01/`
- `results/c121_winner_fusion/20261001_seed100_pilot01/`

Deux rapports `pass=true`, santé `game_ok=true`, aucune erreur NoAI,
13 sauvegardes exactes du1970-01-01 au1971-01-01, sources/copies/fixtures
inchangées pendant chaque exécution. Résultats des copies retenues, sans
identité attestée avec le VPS. Aucune mesure économique d'adoption.

## Porte suivante

**Suite livrée :** [intégration OFF et pilote annuel](c121_air_winner_integration_20261001.md)
avec repli mensuel, témoin explicite et OFF/ON figés. Catalogue AIR observé
−5,93 %/−6,61 % sur42/100 ; mix de travail variable, aucune adoption.

**Prototype technique prometteur, intégration non réalisée.** Gain du
catalogue entier et neutralité du calendrier/profit non démontrés. Les
comparaisons stables excluent les frontières tarifaires ; inflation OFF ne
qualifie pas un changement mensuel. Pas de matrice dirigée d'égalités d'argmax
ni de facteurs de réalisation variés. Scan moteur et post-build non optimisés.

Prochaine intervention : contrat de double sortie du gagnant avec chemin
témoin isolé, définir fraîcheur/repli aux frontières tarifaires, smoke puis
mesure `c121_winner_ops`/catalogue sur42/100. C115 protégé et défauts conservés.
L'interdiction20×10 C121 reste applicable ; aucun réarmement des politiques
rejetées ni adoption économique autorisé par ce lot technique.
