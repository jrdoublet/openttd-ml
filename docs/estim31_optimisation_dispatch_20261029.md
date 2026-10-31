# ESTIM-31 : optimisation conjointe AIR × RAIL avec correctif C121 neutre OFF

## Critère et méthode

Critère **unique de sélection économique** :
`100 × mean(profit_year OpexAI en variante) / mean(profit_year AAAHogEx-115
dans les duels de cette variante)`, au checkpoint **01/12/1974**.
La société AAAHogEx réagit à son concurrent : analyser séparément ses profits,
ne pas attribuer mécaniquement les écarts de ratio à OpexAI. La valeur de
société, la trésorerie, le nombre d'aéroports, les opcodes et les tests de
significativité ne sont **pas des motifs indépendants de rejet économique**.
L'intégrité du chemin OFF, l'absence de crash et la complétude des duels
restent des **préconditions techniques**, pas des critères de rentabilité.

Racine identique des nouvelles variantes :
`results/estim31_engine_dispatch_air15_root_20261029` et son code C121
`FullScan` choisi uniquement quand `ESTIM_UNIFIE & 1`. Graines exploratoires
42, 100, 7, 999, 2026, cinq ans 1970–1974, cartes 256² multimodales, EB14=3,
`probes=2`, un Docker (10 CPU, 8 Gio, au plus 8 workers) à la fois.
Références complètes des campagnes, snapshots et hashes sous
`results/estim31_joint_dispatch20261029/<configuration>/results/`.
Lecteur : `results/estim31_dispatch_joint_analyse_20261029.py` ; il vérifie
pour chaque configuration le bras OFF contre la référence historique
sur **5 dates × 5 graines × 2 compagnies × 7 métriques (350 contrôles)**.
Une série additionnelle teste des coefficients **appliqués seulement dans la
branche ESTIM** lors de `OpexLoadSettings`, avant la réinitialisation des
facteurs appris : les constantes globales historiques restent inchangées.

### Base C121 à ne pas confondre avec les anciennes tentatives

Le banc sûr **40×5** `estim31_engine_dispatch_air15_40x5_20261029` donne
**90,879 %** du profit AAA (Opex 2,628 M£, AAA 2,891 M£) pour les coefficients
initiaux AIR1,50, RAIL1,00, poids15 avec profil distance RAIL incliné.
L'OFF du **même** banc donne **95,156 %** (Opex 2,856 M£, AAA 3,002 M£).
Le delta de ratio est −4,277 points, bootstrap95 [−10,797 ; +2,051].
Le correctif d'élagage est une réparation mathématique **du scan** et non
une garantie de meilleure performance économique de l'ensemble ESTIM-31.

L'ancien `results/estim31_joint20261029/ranking_5y.json` annonçait jusqu'à
**96,819 %** pour AIR1,50/RAIL1,00/w15 RAIL plat sur cinq graines, mais son
élagage numérique C121 n'était pas neutre OFF sur seed999 `probes=2`.
**Ces ratios ne sont pas transférables au nouveau code** ; les nouvelles
comparaisons partent du dispatch C121 préservant strictement l'historique.

## Criblage initial sur le même moteur (5×5)

| AIR | RAIL | Poids | Profil RAIL | Garde charge AIR | Ratio Opex/AAA | Profit Opex | Profit AAA | Divergences OFF / 350 |
|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 1,00 | 1,00 | 15 | plat | 0 | **82,790 %** | 2 523 450 | 3 047 999 | 0 |
| 1,50 | 1,00 | 5 | plat | 25 % | **82,085 %** | 2 462 186 | 2 999 545 | 0 |
| 1,25 | 1,25 | 15 | plat | 0 | 80,099 % | 2 519 811 | 3 145 877 | 0 |
| 1,50 | 1,25 | 15 | plat | 0 | 79,733 % | 2 499 638 | 3 134 995 | **5** (seed999 1974) |
| 1,50 | 1,00 | 15 | plat | 0 | 78,397 % | 2 542 586 | 3 243 239 | 0 |
| 1,50 | 1,00 | 5 | plat | 0 | 74,425 % | 2 411 414 | 3 240 068 | 0 |

Unités : `profit_year` moyen en £/an, OpexAI et AAAHogEx-115 dans le **bras
variante**, checkpoint 01/12/1974. Tous les résultats sont **diagnostiques**
avec cinq graines. AIR1,50/RAIL1,25/w15 plat n'est **pas techniquement
promouvable** : cinq écarts OFF, notamment cash/opcodes de Opex et profit/valeur
de AAA seed999 en décembre 1974. Il reste un résultat descriptif historique.

**Interactions et limites causales :** le passage poids15→5 est défavorable
avec AIR1,50/RAIL1,00 et RAIL plat (ratio 78,397→74,425 %). **Mais** en
croisant ce faible poids avec `air_load_min_pct=25`, le ratio remonte
74,425→82,085 %, Opex n'améliorant son profit propre que de **+50 773 £/an**,
contre une baisse de **−240 523 £/an** du profit AAA dans son duel. Le ratio
s'améliore principalement par la réaction de l'adversaire ; ne pas dire
qu'Opex gagne 7,66 % de profit absolu. Une interaction négative isolément
peut donc être favorable pour le critère relatif en combinaison, à qualifier
sur 40 graines avant recommandation.

## Origine du vivier RAIL vide et rôle de la calibration par distance

`OpexBuildProjects` inhibait le RAIL pendant l'année de départ AIR-first ;
EB14 bloquait également le PO01C incrémental jusqu'au premier changement
d'année. Le mode opt-in `eb14_progressive=3` autorise après le premier AIR
une tranche de prospection RAIL tous les 64 ticks en 1970 et publie de vrais
candidats, mais les essais déjà consignés dans
`docs/eb3_vivier_rail_1970_20261029.md` n'ont construit **aucun train en
1970** : c'est une défaillance de transformation du vivier en investissements
effectifs, pas nécessairement de rentabilité intrinsèque des paires. L'effet
AIR/RAIL doit être évalué via les coûts d'opcodes et la caisse disponible.

Profil de recette sous ESTIM bit16 :
`k_R(d) = k_R_appris × (0,5722990662 + 0,00258519378 × clamp(d,15,250))/0,92`.
Le **0,92 est le niveau de normalisation** du profil calibré, pas une
distance de 92 tuiles ; il croise sa valeur 0,92 vers **134,5 tuiles**.
Passer à `A=0,92, B=0` donne un profil plat, donc `k_R(d)=k_R_appris`
sur toute la plage. L'apprentissage ne ré-estime pas la pente :
`k = (n×recette_réelle/recette_prédite + poids×prior)/(n+poids)` et conserve
un seul facteur de niveau par mode. Le coefficient modifie le score du
candidat (recettes avant amortissement/dépenses), mais les achats effectifs
passent également par financement, carte, file de projets et raccourci moteur
`C121_GE`. Ne pas inférer directement les acquisitions des coefficients.

## Hubs, moteurs, renforts, renouvellements et flux de caisse

L'ablation ancienne des deux canaux `hubsite` et `hubhub` entraînait
**−854 408 £/an** de profit propre Opex sur cinq graines : les hubs sont
importants. Cependant le patch test inconditionnel modifiait également OFF ;
il est conservé comme diagnostic, **pas comme comparaison techniquement
qualifiée**. Le facteur ancien `fleet0` était inopérant : modifier
`AIR_FLEET_BUFFER` dans `globals_pre` ne change rien, car `settings.nut`
force déjà le tampon à zéro à l'initialisation. Il ne constitue donc pas
une preuve d'effet économique de flotte.

Le 40×5 montre environ **314 avions Opex de moins** sur les 40 cartes
fin 1974 sous ESTIM31+dispatch, malgré **29 appareils 223 de plus** et
**68 appareils 228 de moins** ; les stocks 217 et 218 changent aussi
massivement. Les raccourcis GE ont effectivement `causal_engine_evals=0`
sur certaines lignes, et une variante sans GE à coefficient AIR1,50 était
moins bonne en ratio et plus coûteuse en opcodes observés. Le nouveau
croisement noGE × autres coefficients est exploratoire et ne doit pas
affecter les fonctions historiques OFF.

Le résidu financier 1974 du 40×5 est précis mais **non ventilé** : Opex
`profit_year + Δloan − Δcash` vaut 1,294 M£ en OFF et 1,935 M£ en ESTIM,
soit +641 k£ de flux nets hors résultat qui peuvent inclure CAPEX, ventes,
crédits et autres mouvements non observés. Les journaux du 40×5 sont vides ;
ne pas remplacer ce résidu par des devis de chantiers ni attribuer le surcoût
aux statues par analogie au 40×5 ESTIM31+EB2+load25 d'un autre bundle.
Rapport moteur/couverture et limites :
[qualification C121](estim31_c121_dispatch_20261029.md).

## Étapes en cours

### Deuxième criblage : pente RAIL, coefficient AIR et raccourci moteurs

Les 5 graines de l'écran complémentaire donnent :

| Configuration | Ratio Opex/AAA | Opex £/an | AAA £/an | Discordances OFF |
|---|---:|---:|---:|---:|
| AIR1,50 / RAIL1,00 / poids5, **profil incliné** | **84,078 %** | 2 453 610 | 2 918 250 | **0/350** |
| AIR1,25 / RAIL1,00 / poids15, injectés dans les réglages | 87,218 % | 2 651 122 | 3 039 635 | **15/350** |
| AIR0,75 / RAIL1,25 / poids15, injectés dans les réglages | 84,860 % | 2 505 886 | 2 952 950 | **32/350** |
| AIR1,50 / RAIL1,25 / poids5, profil plat | 79,641 % | 2 554 999 | 3 208 141 | **0/350** |
| AIR1,25 / RAIL1,25 / poids15, profil plat, raccourci GE neutralisé | 86,941 % | 2 474 433 | 2 846 116 | **15/350** |

**Important :** une injection de coefficient protégée par le test ESTIM,
ou une modification de la fonction expérimentale non appelée OFF, **ne
garantit pas la parité de la simulation à opcodes sensibles**. Les lignes
non neutres sont des résultats diagnostiques et ne sont pas sélectionnées.
L'écart positif de GE désactivé provient surtout de la baisse du profit AAA,
avec 15 discordances OFF : aucune justification de son adoption.

Une tentative additionnelle de module moteur séparé, chargé par `require()`
uniquement sous ESTIM, restaure le contenu littéral du fichier historique,
mais **ne reproduit pas non plus tous les checkpoints OFF** : le contrôle
AIR1,50/RAIL1,00/poids15 donne 80,665 % du profit AAA sur cinq graines
avec **5 écarts OFF** ; AIR1,25/RAIL1,00/poids15 donne 82,363 % avec
**22 écarts OFF**. Ce module expérimental est donc non promouvable ;
ne pas prétendre qu'isoler un fichier source prouve automatiquement la
neutralité temporelle dans OpenTTD. Les modules restants ont été suspendus
avant lancement, sans interrompre un jeu actif, et les dossiers restaurés.

Les variantes admissibles du criblage ont été promues à une vraie
qualification **40×5**, dans l'ordre AIR1,50/RAIL1,00/poids5 incliné,
AIR1,00/RAIL1,00/poids15 plat, puis AIR1,50/RAIL1,00/poids5 plat avec
`air_load_min_pct=25`. Trois copies séparées, chaque scénario avec les mêmes
40 graines, ses propres duels AAA et le même choix C121 avec GE conservé.
La qualification vérifie 2 800 indicateurs OFF par scénario (40 graines ×
5 dates × 2 compagnies × 7 indicateurs), et classe exclusivement le ratio
de `profit_year` en décembre 1974.

## Vérification de reproductibilité 40×5 (30 octobre)

**Premier finaliste `a150_r100_w05` : 40/40 graines terminées**, ratio
**87,8014 %**, `profit_year` Opex **2 547 658 £/an**, AAA
**2 901 613 £/an**, IC95 bootstrap du ratio **[82,672 ; 93,196] %**.
L'OFF de **ce même bundle** est à 96,2442 %, alors que le contrôle OFF
historique du 40×5 C121 précédent était à 95,1563 %. **Il y a 318
discordances sur 2 800 champs OFF** en comparaison inter-campagnes (16
graines concernées, 1972 : 27 écarts ; 1973 : 118 ; 1974 : 173).
Ce 40×5 est **économiquement descriptif mais non qualifié OFF** ; ne pas
promouvoir ses coefficients sur la seule foi des 350/350 vérifications du
premier criblage à cinq graines.
En comparaison **descriptive** avec le 40×5 ESTIM31/poids15/pente incliné,
le ratio baisse de **90,8789 à 87,8014 %** (−3,0775 points) : Opex
**−80 053 £/an**, AAA **+10 171 £/an**, donc le changement de dénominateur
n'explique pas une amélioration fictive du ratio. Le parc fin 1974 est de
59,5 avions, 32,05 aéroports et 25,575 trains Opex par carte, contre
58,675 / 32,425 / 25,7 sur le précédent 40×5 ; caisse moyenne
1,171 M£ contre 1,242 M£. Ces évolutions ne sont **pas des effets causaux
isolés du poids** puisque la neutralité OFF inter-campagnes échoue.

Audit croisé reproductible : `sweeps/estim31_dispatch_off_audit.py`, avec
les mêmes sept métriques sur les cinq dates. `original_5` vs `new_5` :
**0/350 écart** ; `new_5` vs `new_40` sur les cinq graines communes :
**0/350 écart** ; `original_5` vs `original_40` : **5 écarts** propres à la
graine 999 en 1974 ; `original_40` vs `new_40` : **318 écarts**.
Une différence de reproductibilité entre deux campagnes existe donc même
à source historique identique sur seed999 : la provenance des écarts ne
peut pas être attribuée intégralement au correctif.

La différence des fichiers IA des deux bundles 40×5 ne porte que sur
`globals_pre.nut` (`ESTIM_K_R_PRIOR_WEIGHT` 15→5) et sur un commentaire
de `settings.nut`. Le poids global est lu par la calibration RAIL
(`projects_models.nut:289`), mais les deux chemins connus qui publient ou
recalculent ce facteur sont gardés par `estim_unifie & 17`. **Aucune preuve
ne permet d'imputer les 318 divergences à cette lecture en OFF** ; un
effet d'ordonnancement ou de reproductibilité du banc reste possible,
comme le prouvent les cinq écarts seed999 entre deux tailles d'échantillon
de la même source. Le poids devrait néanmoins être isolé **strictement
sous ESTIM**, et la neutralité inter-campagnes vérifiée sur les 40 graines :
un test limité à cinq graines ne suffit pas à couvrir ces interactions.
Le résultat n'est pas rejeté pour sa valeur de société ni pour un test
de significativité : il échoue uniquement à la précondition technique
de neutralité.

Les qualifications suivantes ont été achevées dans le lanceur séquentiel
préparé, sans Docker concurrent ni `probes=770`. L'analyse définitive appartient au lecteur versionné
`sweeps/estim31_dispatch_finalists_40x5_analyse.py`.

## Conclusion des trois qualifications 40×5 — 30 octobre 2026

**Les trois qualifications se sont achevées séquentiellement, sans échec de
partie ni interruption, le 30 octobre à 00:13, 00:31 et 00:46 (heure de
Paris).** Les trois résumés finaux portent chacun sur 80 jeux complets,
40/40 graines appariées, 400 snapshots OFF et 400 snapshots expérimentaux
aux cinq dates de décembre 1970 à 1974. Chaque JSONL conserve une empreinte
de bundle unique et cohérente entre référence et variante. Les JSONL de
campagne ne sont pas recopiés dans Git.

| ESTIM-31, EB14=3, `probes=2` | Ratio Opex/AAA (%) | Opex `profit_year` (£/an) | AAA `profit_year` (£/an) | OFF différent / 2 800 | IC95 ratio (%) |
|---|---:|---:|---:|---:|---|
| **AIR1,00 / RAIL1,00 / poids15 / profil plat** | **89,7763** | 2 585 673 | 2 880 130 | 401 | [84,476 ; 95,777] |
| AIR1,50 / RAIL1,00 / poids5 / plat / `air_load_min_pct=25` | 88,1498 | 2 571 105 | 2 916 744 | 440 | [82,670 ; 94,275] |
| AIR1,50 / RAIL1,00 / poids5 / profil incliné | 87,8014 | 2 547 658 | 2 901 613 | 318 | [82,672 ; 93,196] |
| **ESTIM31 précédent qualifié : AIR1,50 / RAIL1,00 / poids15 / incliné** | **90,8789** | 2 627 711 | 2 891 442 | 0/350 en 5×5, source de contrôle 40×5 | — |
| OFF historique du banc précédent (sans ESTIM) | 95,1563 | 2 856 233 | 3 001 621 | référence | — |

**Classement économique brut :** aucun des trois finalistes supplémentaires
ne surpasse le précédent **90,8789 %** du rapport C121. Le plus proche,
AIR1,00/RAIL1,00/poids15/profil plat, perd **1,1026 point** de ratio,
**42 037 £/an de profit propre Opex** et **11 312 £/an de profit AAA**
par rapport à cette référence. IC95 bootstrap apparié de l'écart de ratio
**[−6,823 ; +4,738] points** : indication d'incertitude, **pas veto**.
Comparée à OFF, la variante plate perd **270 559 £/an de profit Opex**
mais fait aussi baisser le profit concurrent d'environ **121 491 £/an**.
Cette réaction d'AAA masque donc une partie de la perte propre d'Opex.

Le croisement `poids5 + profil plat + garde 25 %` ne démontre pas une
synergie gagnante sur 40 cartes : il atteint **88,1498 %** contre
**87,8014 %** pour `poids5 + profil incliné` (+0,3484 point, effet
combiné du profil ET de la garde, impossible à attribuer à un seul).
La différence de ratio coexiste avec **+23 447 £/an de profit Opex** et
**+15 132 £/an de profit AAA**. Les interactions détectées sur cinq
graines restent une exploration, non un signe fiable de gain à 40.

**Conformité technique :** dans les trois cas, la comparaison stricte
avec l'OFF du 40×5 C121 ancien échoue à 318, 401 ou 440 champs sur
2 800. L'audit `sweeps/estim31_dispatch_off_audit.py` montre par ailleurs
que les deux répétitions du contrôle OFF **à source identique** mais avec
5 et 40 graines se distinguaient sur cinq champs de seed999 ; la
reproductibilité exacte inter-campagnes n'est donc pas assurée même sans
changement de source. Les variantes 40×5 ne sont **pas promouvables
techniquement** ; la cause de toutes les divergences reste ouverte.
Une divergence du contrôle n'est ni un test de profit ni une preuve
formelle que la modification des facteurs est exécutée sous OFF.

**Diagnostics physiques 1974 (moyennes par carte) :**

| Politique | Avions Opex | Trains Opex | Aéroports Opex | Villes avec aéroport Opex | Caisse Opex (£) | Opcodes Opex observés, partiels |
|---|---:|---:|---:|---:|---:|---:|
| OFF | 66,525 | 23,900 | 33,675 | 33,000 | 2 394 976 | 54,05 M |
| ESTIM31 initial | 58,675 | 25,700 | 32,425 | 31,975 | 1 242 470 | 47,21 M |
| AIR1,00/RAIL1,00/poids15 plat | 59,575 | 24,600 | 32,475 | 31,900 | 1 393 303 | 44,06 M |
| AIR1,50/RAIL1,00/poids5 plat/charge25 | 53,425 | 25,300 | 33,375 | 32,825 | 1 511 333 | 46,85 M |
| AIR1,50/RAIL1,00/poids5 incliné | 59,500 | 25,575 | 32,050 | 31,650 | 1 170 786 | 48,36 M |

Les opcodes ont `observed_opcode_complete_cpu=false` : leur somme est
**incomplète**, pas une consommation totale de CPU ; le stock des moteurs
223 et 228 et les décomptes de véhicules ne prouvent pas à eux seuls
les acquisitions, les renforts ou les renouvellements. Exemples de stocks
AIR sur 40 cartes : 223/228 = **879/360** en ESTIM initial,
**824/333** en variante plate à poids15, **835/334** en variante
plate+charge25, **801/350** en variante inclinée poids5. Le résidu
financier 1974 `profit_year + Δloan − Δcash` moyen pour Opex est
**1,935 M£** pour ESTIM initial, **1,972 M£** pour la variante plate,
**1,736 M£** pour plat+charge25 et **2,064 M£** pour poids5 incliné.
Ce résidu n'est **pas une dépense brute par catégorie** ; les devis,
`AIAccounting`, achats, reventes, statues, rollbacks et flux de trésorerie
réels doivent rester distincts. Le banc non intrusif ne permet pas leur
ventilation exhaustive.

**Vérifications logicielles :** 3 131 tests de non-régression du worktree
passés (6 ignorés, 2 échecs attendus), plus 7 contrats ciblés
C121/lecteur ; `git diff --check` sans erreur. Le Save/Load réel précédent
seed999 / `probes=258` a été validé pour le correctif C121, avec réserve
documentée de trajectoire différente après chargement ; aucun nouveau
Save/Load par combinaison n'est revendiqué. Les nouvelles variantes ne
modifient pas les défauts du dépôt ; aucun code comportemental n'a été
ajouté à `master` par la présente clôture.

**Décision de cette campagne :** conserver comme meilleur **ESTIM-31
techniquement qualifié et mesuré** le profil AIR1,50 / RAIL1,00 /
poids15 / RAIL incliné, `estim_unifie=31`, `eb14_progressive=3`, avec
FullScan C121 et `C121_GE` conservé : **90,8789 %**. Ne pas l'adopter
automatiquement à la place du comportement OFF, lequel atteint
**95,1563 %** dans le même protocole de référence. L'objectif de
maximisation du profit relatif reste ouvert pour de futurs leviers,
mais les trois qualifications demandées et leur analyse sont complètes.
Le protocole d'analyse versionné et toutes les mesures chiffrées :
`sweeps/estim31_dispatch_finalists_40x5_analyse.py` et
`docs/estim31_dispatch_finalists_ranking_20261030.json`.
