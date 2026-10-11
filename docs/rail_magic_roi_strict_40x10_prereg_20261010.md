# P0 RAIL / `simple_roi` — addendum de qualification économique (10 octobre 2026)

**CLÔTURÉ le 11 octobre 2026 sur décision explicite de l'utilisateur :**
`simple_roi` et `simple_opcode` sont tous deux **REJETÉS DÉFINITIVEMENT**.
Le protocole ci-dessous est **historique et inactif** : ne pas relancer
de campagne ni utiliser ses résultats pour rouvrir l'adoption. Le fichier
final `r2` existait déjà à la clôture mais n'a pas été analysé.

**État historique avant clôture :** une première tentative
`rail_magic_roi_strict_40x10_20261010_r1` s'est achevée sans résultat JSON
final ; sa cause d'interruption reste indéterminée. La relance `r2` garde
exactement **les mêmes 40 graines, paramètres statistiques et bundle SHA256**
`2847a30db049a96d5a65c01117102676c00f3d2de30cb5302903f35a500157f1`.
Ne pas exploiter de données partielles ni regarder les résultats avant les
40 paires complètes. `simple_opcode` demeure définitivement abandonné ;
`simple_roi` reste OFF tant que toutes les gardes ne sont pas qualifiées.

## Avant toute nouvelle partie

L'audit du banc Squirrel (`docs/rail_magic_opcode_microbench_20261010.md`)
confirme des surcoûts locaux reproductibles de +12,85 % et +16,45 % sur
deux viviers **synthétiques**, mais ne démontre **pas** une régression
structurelle **sur la distribution réelle** des viviers RAIL ou sur les
opcodes VM totaux. Le TOP20 peut coûter moins dans quatre autres viviers
et ses entrées sont très sensibles à l'ordre. Le coût calcul n'est donc
**pas** une preuve éliminatoire de perte économique : le nouvel ordre de
travail utilisateur impose de continuer l'évaluation économique, sans
présumer une adoption opcode.

`simple_opcode` demeure **abandonné définitivement**, jamais testé ON dans
ce plan. Ne pas toucher aux réglages historiques, à AIR/Capital ou aux
autres modifications en cours. Laisser les deux flags à zéro par défaut.

## Population et méthode pré-enregistrées

Les **40 nouvelles graines indépendantes, déjà fixées AVANT les résultats**
dans `docs/rail_magic_roi_holdout_prereg_20261010.md`, sont conservées
**exactement et dans cet ordre**. Exécuter une seule campagne A/B sur
1970–1979, un seul repeat, duel contre AAAHogEx, même source/bundle/jeu et
les mêmes réglages ON/OFF, seul `rail_magic_simple_roi` 0 contre 1 ;
`rail_magic_simple_opcode=0` **dans les deux bras**. Tous drapeaux de
debug intrusif OFF. Au plus 10 CPU/10 workers, un Docker à la fois.

Les mesures principales sont les ratios des moyennes de
`profit_year` **terminal** et `company_value` **terminale**, ON−OFF, par
40 graines appariées. Pour chaque métrique : 20 000 bootstrap par graine
appariée, RNG `random.Random(0)`, indices `floor(random()*n)`, recalcul
du ratio `100 × sum(ON−OFF) / sum(OFF)` **dans chaque tirage**.
L'intervalle **bilatéral 95 %**, bornes percentiles 2,5 % et 97,5 %, ne
doit pas être remplacé par une seule borne unilatérale.

**Marges et classes fixées ici avant lecture :**

- **POSITIF économique** si borne inférieure de l'IC95 **> +1 %** ;
- **NEUTRE / équivalent** si l'IC95 ENTIER se situe entre **−1 % et +1 %** ;
- **NÉGATIF économique** si borne supérieure de l'IC95 **< −1 %** ;
- **INDÉTERMINÉ** sinon (y compris un CI contenant zéro, ou une borne
  inférieure >−1 % sans borne supérieure <+1 %).

Ces règles s'appliquent **séparément** au profit annuel et à la valeur.
Un signal strictement au-dessus de zéro mais inférieur à +1 % peut être
décrit dans l'analyse, sans le transformer en neutralité ou en gain utile
qualifié. Une simple non-infériorité à −1 % est insuffisante pour neutralité.
Santé complète 80/80 parties, 40/40 paires, absence de doublons, stabilité
physique et contrôle des investissements AIR/RAIL sont obligatoires.
Les résultats annuels servent aux trajectoires et aux pires graines ; la
classification principale ne varie pas selon l'année la plus favorable.

**Point de lecture unique à 40 paires**. Les analyses exploratoires 40×5
historiques ne sont pas regroupées avec ce nouveau bundle. Si l'IC demeure
large, classer indéterminé et **REJETER l'adoption** faute de preuve ; aucune
prolongation post-hoc opportuniste. Une extension statistique peut être
conçue sur des graines vraiment nouvelles avec contrôle explicite des
lectures multiples, mais n'est pas implicitement autorisée par une sélection
des mauvaises/meilleures graines. La porte **20×10** historique n'est
pertinente qu'après passage de la porte économique et de la garde opcode.

## Qualification opcode et décision

Le microbench Squirrel mesure le **bloc intrinsèque score+TOP20** sur
entrées identiques ; les panneaux `OP/OS`, les A* estimés et les postes
partiels `observed_opcodes_total` de parties divergent avec les décisions
et ne mesurent pas le CPU total. Il reste nécessaire de démontrer une
borne supérieure unilatérale 95 % **<+1 %** sur une population
représentative de viviers/états réels appariés, en plus de la santé du
portefeuille et du contexte Save/Load.

**ADOPTER** requiert *simultanément* économie positive ou neutre **sur les
deux indicateurs**, opcode au moins neutre selon la garde +1 %, et aucun
risque structurel. Dans tous les autres cas, **REJETER l'adoption** et
garder le comportement historique OFF, en distinguant l'incertitude d'une
régression effectivement prouvée.
