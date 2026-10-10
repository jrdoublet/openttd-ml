# P0 RAIL — admission, rotation et classement : contrôle de neutralité (10/10/2026)

## Décision

**REJETER l'adoption des trois modifications comportementales déjà testées** (lot
combiné, admission seule, A* seul) ; **NON DÉMONTRÉ** pour la suppression du
classement empirique au défaut. Aucun nouveau réglage, seuil, bonus, politique,
recherche A* ou défaut n'est introduit par ce contrôle. Il ne constitue ni
un nouveau banc ni une qualification économique 40×5.

Le mandat exige simultanément une absence de dégradation économique démontrée,
une absence de surcoût structurel en opcodes et un mécanisme économique plus
simple. Ces trois conditions **ne sont pas établies ensemble** par les données
existantes. L'absence de significativité statistique n'établit pas l'équivalence.
Répéter les variantes rejetées à cinq ans, sans nouvelle preuve causale, ne
répondrait pas à la contrainte de ne pas relancer un essai opportuniste.

## Inventaire et parcours de décision (code courant, défaut des réglages)

| Constante | Localisation | Effet démontré / portée |
|---|---|---|
| 500 PAX, 200 fret | `candidates.nut:25-26,745-755,819-825` | `profitAnnual * 1000 / iterations` est mesuré en £/an pour 1 000 itérations **prédites**, pas en opcodes VM. `VIVIER_RATIO_FILTER` (activé par `policy_portfolio`) écarte les candidats sous le seuil **avant** leur insertion au portefeuille. Les deux seuils ne constituent pas un prix observé de la recherche. |
| `VIVIER_RATIO_FILTER` | `candidates.nut:72,749-755` ; `settings.nut:82-89` | Filtre d'admission réellement actif au défaut. Le réglage isolé `rail_magic_admission_only` laisse passer un devis strictement positif sans changer les autres étages. |
| 12/25/45 jours ; rotation 130/115/100/60 % | `candidates.nut:757-763` | Détermine `turnoverBonus` à partir de `oneWayDays`. Modifie le classement `ratio`, sans changer `profitAnnual` ou `roi` publié. |
| `opcodeRatio + adjustedRoi * 15` | `candidates.nut:768-816` | Additionne des unités différentes pour classer le TOP20 local `OpexTopK` ; ne décide pas directement de l'ordre du portefeuille intermodal. |
| Plancher A* terminal `MIN_RATIO=500` | `builder_rail.nut::OpexIterationBudget`, `task_rail.nut:336,468,687,2217` | Limite l'effort permis face aux autres recherches sous un plafond physique qui reste en place. Le réglage `rail_magic_astar_only` peut le désactiver sans changer le filtre de génération. |

Le TOP20 local est calculé dans `candidates.nut:2355-2361`, puis éventuellement
recalculé dans `projects.nut:263,273`. Le classement intermodal reçoit les
`rail.candidates` **complets** (`projects.nut:497-503`) et classe les alternatives
par `OpexProjectSelectAffordable` (`:559-581`) avec profit C70, financement
et C69 `K_dec`, puis priorités C77/C118/C120. La seule lecture métier de
`_projects.rail.best` trouvée dans `task_rail.nut:2133-2145` est gardée par
`C80_RAIL_STOCK_WORKER && C80_RAIL_STOCK_GATE`, tous deux OFF par défaut
(`info.nut:1768-1780`). Le chemin d'extension d'origine
`OpexRailOriginReuseFallback` trie aussi ses candidats par ce TOP20, mais
`rail_origin_reuse=0` au défaut (`info.nut:1369-1375`).

Les trois noms souvent cités `RAIL_MAGIC_SHADOW`,
`RAIL_MAGIC_ADMISSION_ONLY` et `RAIL_ECONOMIC_PRESELECT` sont des
**interrupteurs Squirrel** déclarés/chargés, non des branches Git distinctes.
`rail_magic_rank_only` existe aussi et appelle déjà `OpexTopKFund`
(`candidates.nut:882-906`), mais sa recotation ne reproduit pas exactement
le coût C69 `max(financeCapital, K_dec)` du sélecteur final et ajoute du travail
de classement.

## Exposition observée : traces descriptives, pas chantiers financés

Source : `results/rail_magic_probe_debug_5x6_20261009.analysis.json` et
`docs/rail_magic_filter_p0_20261009.md` (bundle
`6421111a5edd0076f1e3a244a94001e4f56633e1d66747fdbd7071245fa917bf`).
La sonde est **intrusive** : différence moyenne de profit −89 693 £/an entre
shadow ON et OFF, si bien que ces comptages caractérisent le vivier sous
sonde et ne mesurent pas l'effet économique d'une politique. En plus du
surcoût et du décalage possibles du scheduler, `candidates.nut:937-963`
réutilise les objets réels `rail.candidates` dans `OpexTopKFund`, qui écrit
`candidate.fundScore` en place (`:892-899`) : une mutation indirecte des
payloads est **possible** et ne doit pas être attribuée à tort à la seule
cadence. La sonde était OFF des deux côtés des trois A40×3.

| Mesure | Valeur |
|---|---:|
| Reconstructions complètes / couples graine-année | 15 / 14 |
| Visites écartées par ratio | **796**, toutes PAX ; fret **0** |
| Visites finançables sur devis | **746** |
| Profit prévu total des visites | 1 050 723 £/an **non additif** |
| Visites comparables avec AIR coté, tier C77=0 | **571** ; **0** mieux classée |
| Autres visites : AIR prioritaire / AIR non coté | **175 / 50** |
| Places TOP20 modifiées en omettant bonus rotation | **5** en visites |
| Places TOP20 modifiées par recotation économique | **104** en visites |

Les 796 sont des **visites de génération**, pas 796 OD indépendantes ; le
profit cumulé ne doit donc pas être lu comme un gain potentiel. Les 571
comparaisons examinent des scores sur papier, et les 225 autres restent
incomparables. Aucune trace ne montre qu'un candidat exclu est réellement
constructible sur la carte du même instant, ni qu'il dépasserait un projet
AIR **effectivement financé et construit** à cette date. Les cinq déplacements
liés au bonus concernent le TOP20 local ; au défaut ils n'impliquent aucun
déplacement démontré dans le portefeuille intermodal TOP64.

## Résultats appariés des variantes existantes

Source : manifests, JSON finaux et extraits annuels sous
`results/rail_magic_*_A40x3_20261009*` et
`docs/rail_magic_filter_p0_20261009.md`. Chaque essai comprend 40 graines
canoniques, une répétition, 40/40 paires et 80/80 parties déclarées saines,
horizon 1970–1972. Règle pré-enregistrée `gain_short` V102 (profit annuel
terminal, Wilcoxon bilatéral p<0,05, IC95 bootstrap bas>0, gain ≥4 %,
valeur moyenne −5 % maximum).

| Modification isolée | Δ profit 1972 moyen ; médiane | IC95 bootstrap ; V/D/E ; p Wilcoxon | Δ valeur ; verdict |
|---|---|---|---|
| `rail_economic_preselect=1` : admission + TOP20 + A* | −31 949 ; −54 603 £/an | [−107 724 ; +44 992] ; 17/23/0 ; 0,3754 | −1,345 % ; `fail_primary` |
| `rail_magic_admission_only=1` | +8 256 ; +7 437 £/an | [−54 163 ; +71 922] ; 21/18/1 ; 0,8848 | +0,412 % ; `fail_primary` |
| `rail_magic_astar_only=1` | −864 ; 0 £/an | [−2 560 ; +77] ; 1/2/37 ; 0,5000 | −0,0098 % ; `fail_primary` |
| `rail_magic_rank_only=1` | non mesuré | pas de porte A | voie métier inactive au défaut |

Cas économiquement les plus défavorables à l'admission seule en 1972 :
`746035 −414 140`, `232037 −316 286`, `781335 −310 114` £/an.
Pour le lot combiné : `54321 −543 831`, `375172 −427 298`,
`123456 −356 560` £/an. Ces pires graines caractérisent les risques
observés ; sélectionner ensuite les meilleures serait un biais.

Les observations physiques à 1972 pour l'admission seule sont des différences
**d'état final**, pas des comptes d'achats : moyenne −0,350 train,
−1,150 avion, −0,425 installation RAIL et −1,675 signe de chantier.
Les données ne prouvent ni davantage de lignes RAIL opérationnelles ni
un transfert profitable de capital depuis AIR. À partir de 1973, le recul
ou gain économique du retrait isolé des seuils reste **non mesuré par un
40×5 apparié**.

## Budget d'opcodes : critère éliminatoire non rempli

`projects_builders.nut:74-101` calcule le **devis**
`min(predictedIterations,HARD_ITERATION_CAP) * 3105 + transaction`
pour un projet RAIL. Le ratio de génération divise par des
**itérations A*** prédites ; aucune de ces deux grandeurs n'est une mesure
des opcodes VM réellement consommés. Les compteurs de tentatives conservés
dans les panneaux ne couvrent, en 1972, que **6/40** paires admission,
**10/40** A* seul et **2/40** lot combiné. Impossible d'en inférer les opcodes
totaux, la distribution d'itérations réelles ou le nombre global de recherches
supplémentaires. La sonde shadow ajoute elle-même des calculs, donc son
coût ne doit pas être imputé à l'admission seule.

Un candidat supplémentaire entraîne du travail d'assemblage et de sélection,
même lorsque `HARD_ITERATION_CAP` empêche un dépassement des itérations
d'une recherche. Ôter un filtre ne garantit ni un nombre fixe d'A* lancés
ni une économie en opcodes. Surcoût structurel : **NON EXCLU**.

Vérification sans nouvelle partie : tests hôte
`test_rail_magic_economics.py` (4), `test_analyse_rail_magic_filter_p0.py`
(1), `test_analyse_rail_magic_ab_annual.py` (1) et
`test_homogeneous_preselect.py` (3) : **9/9 verts**. Ils contrôlent les
contrats et les décodeurs, pas les opcodes ni la neutralité des duels.

## Remplacement minimal envisageable et règle d'arrêt

Les grandeurs économiques réutilisables existent déjà :
`OpexProjectFundProfit(project)` (profit annuel calibré),
`OpexProjectFinanceCapital(project)` (capital à engager),
`OpexProjectScore(profit,max(capital,K_dec))` dans la sélection C69/C70.
Le budget pathfinding se mesure séparément en itérations A* réelles et
opcodes VM, sans les convertir en un tarif £/opcode non étayé.
Recalculer un second classement local qui ne commande aucun financement
serait une complexité et un coût injustifiés.

Une future proposition devrait partir d'une **identité OD/cargo
contrefactuelle**, d'une place effective face à un AIR payable, d'une preuve
de constructibilité sur le **même état de jeu** et d'un coût additionnel
mesuré par poste. Sa modification serait limitée à l'étage effectivement
responsable : admission **ou** Top20 **ou** lancement A*. Elle devrait
conserver un seul créneau de recherche, les plafonds A* et un bras OFF
historique ; avant tout défaut ON, tests de contrat, smoke et A/B apparié
**40 graines × 5 ans** pré-enregistré, avec comparaison économique,
physique et opcodes complets, puis prolongation si l'incertitude reste
significative. Un résultat incertain laisse OFF.

**Décision opérationnelle au 10/10 :** conserver les cinq interrupteurs
`rail_economic_preselect`, `rail_magic_shadow`,
`rail_magic_admission_only`, `rail_magic_rank_only`,
`rail_magic_astar_only` à zéro. Aucun nouveau banc 40×5 n'est déclenché
pour ces variantes déjà évaluées sans nouvelle hypothèse causale.
