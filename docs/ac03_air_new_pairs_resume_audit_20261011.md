# AC-03 — reprise des paires AIR neuves (11 octobre 2026)

**Verdict : audit terminé, sans correctif de production.** Dans
`OpexAirPlansNewPairs`, le curseur `(a,b)` est déplacé **sur la prochaine paire
avant l'évaluation de la paire courante**. Les suspensions au budget ne
réévaluent donc pas une paire déjà traitée, même si elle coûte plus que la
tranche et même si son traitement se termine par `continue`.

La fixture `sweeps/test_ac03_air_new_pairs_resume.py` vérifie les transitions
du code courant et compare un parcours non interrompu à des parcours découpés
sur des **données synthétiques figées**. Elle n'exécute ni Squirrel, ni NoAI,
ni les formules économiques effectives : sa réussite ne prouve pas une
neutralité économique, opcode, Save/Load ou un comportement identique quand
la carte change entre deux tranches.

## 1. Déroulement vérifié dans le code

| Étape | Point de code | Constat |
|---|---|---|
| Initialisation | `air_planning.nut:211–215`, `:650–659`, `:2489–2505` | Pour chaque combo, `(a,b)` commence à `(0,1)` ; `sites` et les curseurs sont réinitialisés lors du passage au combo suivant, pas après chaque suspension |
| Début de tranche | `:714–731` | `startA` relit `resumeState.a` pour le même combo, puis `startB` relit `resumeState.b` pour la première ligne reprise seulement ; les lignes suivantes repartent à `a+1` |
| Garde de suspension | `:732–753` | Contrôle avant la prochaine paire **seulement si `pairProgress`** ; au moins une paire est consommée par appel actif, même avec un budget dépassé |
| Checkpoint | `:754–764` | `(nextA,nextB)=(a,b+1)` ou `(a+1,a+2)` à la fin d'une ligne ; sauvegarde avant validation de sites, quarantaine, filtres, choix de l'avion et admission |
| Décisions | `:765–958` | Revalidation des sites sur une reprise ; politiques V133/C83, bande et distance, abandons, économie et admission sont exécutées dans l'ordre historique, **après** le checkpoint |
| Fin du parcours | `:960–990` | Curseurs fixés à `(sites.len(),sites.len())` ; si le budget a été atteint sur la toute dernière paire, le rappel suivant termine sans la rejouer |

**Ciblage de ville C83** (`:709–725`, `:787–788`) : si la cible est le
premier site, seul `a=0` est exploré (soit `n−1` paires) ; si elle est ailleurs,
le parcours triangulaire reste entier, mais seules les paires touchant cette
cible passent le filtre. Si la cible ne figure pas dans les sites, aucune paire
n'est examinée. Sur un même jeu de sites, l'ordre des paires ciblées est le
même que dans le parcours général filtré sur cette cible.

## 2. Fixture et résultats

La fixture contient six tests, dont une matrice de **2 520 comparaisons** :

- **7 tailles** de vivier : 0, 1, 2, 3, 5, 9 et 15 sites ;
- **5 positions de cible** : aucune, première, médiane, dernière, absente ;
- **4 profils de coût synthétique** : uniforme, variable, une paire très
  coûteuse, toutes les paires très coûteuses ;
- **3 filtres synthétiques d'admission** : tous, alternance, sélection clairsemée ;
- **6 budgets de tranche** : 1, 2, 7, 29, 100, 1 000 unités.

Pour chaque cas, l'algorithme de reprise et le parcours non interrompu ont
**les mêmes couples d'indices visités, les mêmes paires admises, dans le même
ordre**, et le même coût synthétique cumulé. La comparaison porte sur les
identités des paires `(a,b)` et le filtre d'admission prédéterminé, **pas**
sur une estimation réelle du profit de la liaison.

Les cas dédiés vérifient aussi :

1. `n=8`, **28/28** paires parcourues une seule fois, **0 admission** malgré
   un coût de **500 unités par paire** et un budget de 1. On obtient 29
   invocations (28 paires puis le constat de fin), sans livelock.
2. `n=4`, suspension **après la dernière paire de la première ligne** :
   les trois paires `(0,1),(0,2),(0,3)` sont suivies de `(1,2)` au rappel,
   sans duplication. Nouvelle suspension en fin de parcours, suivie d'un
   rappel vide.
3. `n=4`, dernière paire `(2,3)` coûte 20 unités, les cinq premières
   coûtent 1. Avec un budget de 25, le rappel après la dernière paire garde
   **6 admissions, 25 unités cumulées**, sans recalcul.
4. Cible présente en première/milieu/fin : **3 paires éligibles** sur quatre
   sites, identiques au parcours général filtré ; cible absente : zéro.

Commandes exécutées sur le dépôt Windows local (aucun Docker) :

| Contrôle | Verdict |
|---|---|
| `python -X utf8 -m unittest -v sweeps.test_ac03_air_new_pairs_resume` | **6/6 tests OK** ; matrice 2 520 cas |
| `python -X utf8 -m unittest -q sweeps.test_ac02_air_site_resume sweeps.test_c78_air_candidate_hygiene sweeps.test_c83_fixes sweeps.test_v93_small_airport sweeps.test_v133_air_build_retry sweeps.test_v134_air_p2p_saturated_hub sweeps.test_c120_air_territorial_ranking` | **51/51 tests OK** |
| `python -X utf8 -m unittest discover -s sweeps -p 'test_c83_local_repair.py' -q` | **6/6 tests OK** |
| Ensemble | **63/63 tests OK**, sans Squirrel/Docker |

## 3. Limites importantes et décision

- **Coût de paire supérieur au budget : oui, volontairement.** La garde
  `pairProgress` assure la progression au prix d'un dépassement ponctuel :
  elle n'impose pas un plafond dur à la planification économique d'une paire.
  Un découpage *intra-paire* changerait le protocole et serait une autre tâche.
- **Revalidation en cas de carte mouvante : oui.** Dès la deuxième invocation
  sur le même combo, `resumingCombo` déclenche
  `OpexAirSiteStillBuildable(...)` pour chaque extrémité. Un site devenu
  invalide peut supprimer des admissions ; ce n'est pas un saut de curseur.
  Un scénario non figé ne peut donc être présenté comme strictement paritaire.
- **Doublons métier : hors portée.** La fixture prouve l'unicité de l'indice
  `(a,b)` au sein d'un combo. Elle ne garantit pas que deux combos matériel
  ou deux sites logiquement équivalents produisent des plans économiques
  distincts : la déduplication inter-combos relève d'un autre périmètre.
- **Exécution runtime non vérifiée.** Sans modification `.nut`, aucun smoke
  OpenTTD ni campagne V102 A/B n'a été lancé. Toute optimisation future
  du calcul, de son ordre ou de sa politique exigera les tests et portes
  habituels de neutralité économique et d'opcodes.

**Clore AC-03 sans code de production modifié.** Préserver le curseur
actuel et le test de non-régression, sans relancer V142/V143 ni modifier
le scoring, les seuils de distance, le budget de tranche C78 ou la
publication du portefeuille. AC-04 (hub→site) et AC-05 (hub→hub) restent
indépendants. Aucun commit/push effectué.
