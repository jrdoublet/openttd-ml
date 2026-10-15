# V216 — bilan du factoriel et passation vers la sonde

Lecture du plan révisé sur `origin/master` (`9a6b0bce`), après F1 et F2 exécutés sur le PC depuis `master` (`92c86206`). Le bilan suivant utilise uniquement les campagnes terminées ; aucune nouvelle simulation ni modification du comportement. Le plan, §10, attribue l'instrumentation à Claude sur le VPS. La sonde n'a pas été commencée ici ; sa prise en charge reste à coordonner.

## Résultat déterminant

Le changement de contexte accompagne un écart descriptif important : le rapport des sommes de revenus réalisés/prévus du rail voyageurs est environ 4,4 fois plus faible dans notre configuration complète que dans notre configuration rail seule, sous chacun des deux profils adverses. Le premier arrêt du §11 (« le contexte n'explique pas l'écart ») n'est donc pas déclenché par ces observations. Cela justifie la mesure passive prévue, pas une correction ni une adoption.

| Cellule | Nos modes / modes AAA | Lignes rail PASS retenues | Graines représentées sur 40 | Revenu réalisé/prévu, ratio des sommes | Profit réalisé/prévu, ratio des sommes |
|---|---|---:|---:|---:|---:|
| A | complets / complets | 15 | 13 | 0,1823 | 0,0325 |
| B | complets / rail | 10 | 10 | 0,2416 | 0,1470 |
| C | rail / complets | 19 | 13 | 0,8078 | 0,9305 |
| D | rail / rail | 24 | 19 | 1,0588 | 1,3478 |

- Effet descriptif de notre configuration complète sur le ratio voyageurs : A/C = **0,2257**, B/D = **0,2282**.
- Effet descriptif de la configuration complète d'AAA : A/B = **0,7548**, C/D = **0,7629**.
- Le déficit voyageurs existe donc même quand AAA n'a ni bus ni avion (B), tandis que la présence des autres modes adverses accompagne un écart plus modéré du ratio.
- Dans la cohorte de co-localisation (lignes existantes en décembre 1971, différente de la cohorte de ratios), **24/25 lignes en A** et **12/12 en B** desservent au moins une ville possédant notre aéroport. En B, dix lignes sur douze desservent deux telles villes.

## Limites à préserver

1. L'intervention coupe ensemble nos modes AIR, ROAD et WATER, leurs catalogues, leur consommation d'opcodes et leurs achats. Elle n'isole pas l'effet de l'aéroport seul.
2. Les ratios comparent des cohortes de lignes sélectionnées par des trajectoires différentes. Les 40 graines communes ne donnent pas 40 observations appariées de lignes identiques : la cohorte voyageurs ne couvre que 10 à 19 graines selon la cellule. Ces quotients ne sont ni un effet causal de cannibalisation ni un test statistique apparié.
3. Le fret n'est pas un témoin parfaitement invariant dans ce nouveau factoriel : revenu réalisé/prévu **0,865 / 0,804 / 1,064 / 0,735** en A/B/C/D, sur des cohortes différentes. Éviter de reconduire sans nuance l'affirmation historique « le fret ne bouge pas ».
4. L'AIR est sur-prédit dans les deux contextes observés : ratio de revenu **0,575 en A**, **0,697 en B**. Cette différence ne décompose pas l'effet des bus adverses, des aéroports adverses, de la flotte ni des calendriers d'ouverture. Elle n'autorise pas à réarmer la concurrence visible C121 ni une correction AIR rejetée.
5. Le script fourni annualise une première année partielle ; il ne mesure pas le gain net de toute la compagnie. La co-localisation de villes ne prouve pas le recouvrement des maisons effectivement couvertes.

## Suite proposée, dans l'ordre du plan

| Lot | Complexité | Dépendance | Livrable | Validation et arrêt |
|---|---|---|---|---|
| Coordination et contrat de données | 2/5 | Propriétaire de l'instrumentation clarifié | Schéma des événements, champs connus/`na`, identités des décisions/lignes et bornes temporelles | Vérifier les entrées NoAI et les champs déjà calculés ; aucune formule d'EST extrapolée d'une ligne |
| Sonde `v216_probe` et analyseur | 4/5 | Contrat de données | `SCORE_DECOMP`, fantôme de couverture, `TOWN_FLOW`, rejets ; réglage OFF sur quatre difficultés | Aucun effet sur admission/tri/financement/dimensionnement ; contrats ciblés, état transitoire et Save/Load explicités |
| Smoke de la sonde OFF/ON, 1 graine × 3 ans | 3/5 | Contrats verts | Santé, exposition des compteurs, coût en opcodes et perturbation de trajectoire | Compteurs adverses réellement lus, pas de `-1` assimilé à zéro ; distinguer instrumentation passive et neutralité mesurée |
| Deux diagnostics sondés 20×3 sur le VPS | 3/5 | Smoke sain et budget disponible | Complet et rail seul, `ref`/`phys`, sonde identique dans les bras | Pré-enregistrement, 3 CPU/2 Go/3 workers, une campagne à la fois ; pas de verdict économique d'adoption |
| Attribution, invariance, rejeu | 4/5 | Données complètes et sonde validée | Analyses A–H, comparaison aux bornes EST, achats réellement remplacés et valeur estimée | Fantôme : chaque ratio dans [0,7 ; 1,4], max/min ≤ 1,5 ; ≥1 achat changé/partie en moyenne et valeur positive sur ≥70 % des graines concernées ; sinon arrêt |

**Point à résoudre avant pré-enregistrement des campagnes sondées :** le test D du §5 demande le fantôme dans les quatre cellules A/B/C/D, mais les deux campagnes du §4.2 ne couvrent que les contextes A et D (`ref`/`phys`). Le factoriel actuel n'a pas de `v216_probe` et ne fournit donc aucune prévision fantôme en B/C. Il faudra préciser une collecte appropriée ou conserver explicitement le test D comme incomplet ; les mesures actuelles ne le valident pas.

Le présent lot s'arrête au bilan et à la passation. Sonde non commencée, aucun nouveau banc lancé. V216d/P1 et V216e/P2 restent fermées selon le plan. Toute correction candidate reste conditionnée à l'invariance et au rejeu.

## Fichiers et prompt de reprise

- Synthèse complète : [v216_facto_pc_20261015.summary.md](v216_factoriel_pc_20261015.md).
- Contrôles de santé, manifeste et couverture : [v216_facto_pc_20261015.audit.json](../evidence/review/v216_factoriel_pc_20261015/artifacts/v216_facto_pc_20261015.audit.json.gz).
- Cohortes et contrastes non arrondis : [v216_facto_pc_20261015.contrasts.json](../evidence/review/v216_factoriel_pc_20261015/artifacts/v216_facto_pc_20261015.contrasts.json.gz), produits par [v216_facto_contrasts.py](../evidence/review/v216_factoriel_pc_20261015/artifacts/v216_facto_contrasts.py.gz) qui réutilise le parseur fourni.

```text
Reprendre V216 après le factoriel PC, sans refaire F1/F2. Lire le plan révisé
docs/plan_v216_scores_avant_premier_rail_20261016.md et les rapports
docs/v216_factoriel_pc_20261015.md et docs/v216_factoriel_pc_20261015_suite.md. F1/F2 : même bundle
af92af4176593a1eea498162794d51545dfd6726d607ac3933c2a5c7f62aaf5f,
160/160 parties saines, 80/80 paires complètes, code ai/sweeps identique au
commit prescrit 3ad94b5. Revenu rail PASS réalisé/prévu A/B/C/D :
0,1823 / 0,2416 / 0,8078 / 1,0588. Ce constat conserve l'intérêt de la sonde,
sans isoler causalement nos aéroports ni mesurer la cannibalisation nette.
Coordonner le propriétaire de la sonde pour éviter deux implémentations.
Avant toute campagne sondée, résoudre la couverture B/C du test d'invariance D,
absente des deux diagnostics sondés actuellement prévus au §4.2.
Puis suivre instrumentation passive OFF → contrats → smoke 1×3 et mesure du coût
→ diagnostics sondés → invariance/rejeu. Aucun défaut, commit, push ou fusion implicite.
```

[Preuves compactées et vérification](../evidence/review/v216_factoriel_pc_20261015/README.md). Publication documentaire autorisée par la demande « Commit et pousse » ; aucun nouveau lancement ni code IA ajouté.
