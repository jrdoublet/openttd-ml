# PO-01i — plancher de publication, option B

Audit du 22 octobre 2026, base `4e31e47e1afde583ad9aee0f2102e7dfff5013e4`,
worktree `wt_po01d`, branche `po01d`. Aucun changement Squirrel, de réglage,
de sélection ni de projets publiés. Sources historiques et chemin
`po01c_regen_split=0` conservés octet pour octet. Aucun moteur lancé.

## Ventilation des huit pics

Sources : `results/po01h_expo_2x4_20261022_engine/po01h_seed{7,1234}_r0.log`.
Les numéros de ligne ci-dessous identifient les `PO01C_SLICE phase=publish`.
**Correction du résumé d'exposition : cinq pics graine 7 et trois graine 1234**,
et non trois et cinq. Treize publications au total : cinq et huit ; les cinq
autres tranches de la graine 1234 valent 71 298, 83 761, 67 396, 43 059 et
41 374 opcodes. Aucune sélection des seuls lots rail.

Toutes les valeurs sont en opcodes, sans arrondi. U = `PO01C_UNIT`, S = `SPAN`.
F = flotte, R = resélection, L = `pub.select.log`, V = `pub.select.vivier`.
L et V sont **inclus dans R**, les unités F/R dans whole : ne pas les additionner.
Le résidu est `slice − S(F) − S(R)` ; il comprend fusion/conversion,
acquittement/catalogue et instrumentation extérieure aux deux spans.

| Graine/date 1973 | Ligne | Slice | U(whole) | U(F) | U(R) | S(F) | S(R) | L | V | Résidu | Slice−L−V |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 / 03-29 | 120980 | 250146 | 249986 | 72740 | 152259 | 72344 | 150342 | 67894 | 3857 | 27460 | 178395 |
| 7 / 06-01 | 122466 | 195163 | 195027 | 72949 | 101870 | 72553 | 99892 | 45662 | 2734 | 22718 | 146767 |
| 7 / 08-11 | 124283 | 189613 | 189453 | 70717 | 98880 | 70321 | 96855 | 44371 | 2653 | 22437 | 142589 |
| 7 / 10-12 | 126220 | 143481 | 143321 | 61082 | 67156 | 60673 | 65020 | 30174 | 1860 | 17788 | 111447 |
| 7 / 10-13 | 126307 | 139591 | 139431 | 61069 | 67145 | 60673 | 65023 | 30180 | 1859 | 13895 | 107552 |
| 1234 / 03-21 | 123871 | 116942 | 116782 | 42378 | 60645 | 41982 | 59070 | 27143 | 1680 | 15890 | 88119 |
| 1234 / 05-09 | 125683 | 132052 | 131892 | 44680 | 72277 | 44284 | 70666 | 32394 | 1975 | 17102 | 97683 |
| 1234 / 07-02 | 128510 | 110108 | 109948 | absent | 57965 | 39034 | 56282 | 25965 | 1599 | 14792 | 82544 |

L'absence de U(F) sur la dernière ligne signifie seuil de 40 000 non franchi,
pas flotte gratuite. Rattachement : lignes de notre compagnie `[0] [I] OPEX`
entre deux SLICE successifs ; F/R racines `par=0` de la publication et enfants
`par=id(R)` pour L/V. Les autres appels du sélecteur dans la boucle ne sont pas
des publications PO01C. Les dates sont celles de fin de tranche (le premier
pic commence le 27 mars). Les mesures imbriquées portent sur des intervalles
différents : U(R) inclut notamment l'évaluation du capital avant l'appel.

## Ce qui reste sans journaux

`projects_diagnostics.nut:7` sort immédiatement si DECISION_LOG est faux.
Son appel `:20` recopie les alternatives puis **rejoue le sélecteur** pour B6.
Il ne constitue pas la sélection publiée. Dans ces pics, L vaut 25 965–67 894,
V vaut 1 599–3 857 : ces deux intervalles représentent 22,3–28,7 % des tranches.
`projects_selection.nut:1454` encadre aussi V216 dans L ; ce n'est donc pas une
mesure isolée du seul B6. Le vivier est conditionné par DECISION_LOG.
Les UNIT/WHERE sont conditionnés par DECISION_LOG, les SPAN/SPAN_AGG par
PROBE_SPAN_TRACE ; C50/C69/AIR_FLEET_PROBE ajoutent leurs propres diagnostics.
`fleet.refusal` mêle gardes et journal conditionnel : 580–13 204 dans ces pics,
**ne pas soustraire intégralement ce span comme du journal**.

Le vrai score publié (`pub.select.score`, hors rejeu B6) coûte encore
68 794 / 44 566 / 43 053 / 27 919 / 27 923 / 25 376 / 30 749 / 23 904
dans l'ordre du tableau. Flatten, merge, filter et stats sont aussi métier.
La flotte conserve parcours/tri des lignes, cadence/capacité, prix et réserve
de caisse. Exemple premier pic : cadence 12 924, tri 3 668, first_live 600,
`pub.cash` 37 638 (24 appels) **déjà compris dans F**. Ces lectures de caisse
ne sont pas supprimées avec B6 ; seul son propre appel cash disparaît avec L.

Le plancher **structurel** reste un appel atomique de publication : flotte,
fusion et resélection, sans restitution à la boucle principale. Son ordre de
grandeur après retrait des deux intervalles de journal identifiés est
**82 544–178 395 opcodes** sur ces huit observations ; R−L−V =
28 718–78 591, F = 39 034–72 553, plus résidu 13 895–27 460.
Ce sont des **proxies instrumentés**, ni un minimum mathématique ni une mesure
de partie normale. Les allocations/émissions SPAN, leurs enfants et les sondes
restent mêlés au métier et au résidu ; le coût log=0/probes=0 exact est
**non identifiable dans ces journaux**. Même retirer L/V change le temps moteur
et potentiellement les lectures API. Aucun plafond normal de 80 k ou 100 k
n'est démontré ; soustraire tous les enfants SPAN retirerait aussi le métier.

## Pourquoi ne pas séparer flotte et resélection ici

`po01c_regen.nut:347` clone le portefeuille **courant**, puis `:354` appelle
la flotte et `:367` sélectionne avec caisse, abandons et lignes courants.
Le clone est superficiel : groupes/projets restent référencés. Conserver ce
clone une passe de plus pourrait écraser une publication concurrente, une
alternative spéciale ou un retrait. Refaire la fusion au dernier moment
préserverait les autres producteurs mais ne rafraîchirait pas le plan flotte.

Entre deux appels Step (`main.nut:821`, `probes.nut:2701`), événements et tâches
peuvent construire, acheter, liquider, rapporter une ligne ou remplacer le
portefeuille ; caisse, véhicules, cadence, catalogue et C78 peuvent changer.
Les projets flotte conservent `line`, `baseVehicles`, `want`, prix et voisinage
(`task_air.nut:724` et suivantes). Une nouvelle sélection financière ne refait
pas toutes les treize gardes de génération : même liste publiée non garantie.
Un nouvel instant de lecture du capital peut aussi changer l'ordre retenu.

Plus grave, le « mode à blanc » n'est pas intégralement pur :
`task_air.nut:519` appelle `OpexAirRefleetCrashedPlane` avant le traitement
`plan != null`, puis modifie véhicule/compteurs/needsRefleet ; `:689` peut
mettre en cache planeCapacity. Abandonner ou rejouer une étape flotte n'est
donc pas une simple invalidation de résultat. Cette branche est un risque
statique identifié, pas une attribution causale des huit pics à un crash.

Geler toutes les entrées ne gèle pas le moteur ; revalider/recalculer la flotte
ramène son coût dans la tranche finale. Retarder B6 déplacerait le sens de son
contre-factuel « live » et imposerait copies/horodatage explicites ; le résumer
perdrait la comparaison exacte. Sans modification historique, il faudrait
une nouvelle copie spécialisée et de nouveaux contrats, sans preuve moteur
autorisée ici. L'option A n'offre donc pas la garantie demandée des mêmes
projets ; **option B retenue, aucun comportement modifié**. Atomique signifie
sans reprise de notre boucle, pas monde moteur figé : le pic actuel dure déjà
deux jours, et B6 y observe budget_delta=−410.

## Validation et portée

27 contrats PO01C ; suite complète demandée exécutée sur `4e31e47e` avant
édition et après : 2 397 tests, mêmes deux échecs V246/V284 de comptage
AddSetting, zéro erreur, sept skips et deux échecs attendus. Journaux locaux :
`results/po01i_checks/{baseline_4e31e47e,final,contracts}.log` ; ventilation
intermédiaire dans `results/po01i_checks/ventilation.json`.
Les tests Python ne compilent pas Squirrel. Aucun nouveau test nécessaire
pour cette analyse documentaire ; aucun Docker, partie ni push. Ce constat
ne qualifie pas économiquement PO01 et ne clôt pas son chantier de bornage.
