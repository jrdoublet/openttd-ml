# AIR-LOAD-7 — mesure passive du remplissage AIR (22 octobre 2026)

> **ARCHIVE HISTORIQUE — ÉTUDE SUR ARBRE WIP LOCAL NON INTÉGRÉ (22/10/2026).** Cette mesure a été effectuée sur le `master` local au HEAD `41031a7f`, avec du code non commité. La sonde Squirrel expérimentale `air_load7_shadow` et son réglage runtime ne sont **ni intégrés ni adoptés** dans la branche qui archive ce texte ; les analyseurs Python hors-jeu sont, eux, déjà présents dans le dépôt publié. Aucun comportement de renfort n'est adopté. L'exposition **10 graines × 6 ans** décrit le remplissage et la santé des parties, **sans qualification causale ou économique V102** ; activer une sonde consomme des opcodes et peut déplacer les décisions. Les logs, analyses, manifestes et résultats sous `results/` restent **locaux au WIP et ne sont pas archivés ici**. Les commandes et chiffres suivants décrivent uniquement l'expérience historique.

## Protocole pré-enregistré avant exécution

- Dépôt `/openttd-ml`, branche `master`, base `41031a7f24f8a60e8b671c954baeabe14088a145`. Arbre local déjà modifié par d'autres travaux, conservé sans reset. Le lanceur fige le code exécuté et l'identité Docker pour chaque campagne.
- Instrumentation isolée : `air_load7_shadow` (0 par défaut sur easy/medium/hard/custom), sans effet sur les décisions. Source `ai/OpexAI/air_load7_shadow.nut`, journal `AIR_LOAD7` avec `--script-debug`. Aucun réglage de politique, de score ou de priorité n'est changé.
- Cadence : départ au plus une fois tous les sept jours de simulation, un cycle des lignes AIR vivantes. Version finale : index station → lignes vivantes construit par lots de huit lignes, puis au plus deux avions par tour ; un relevé par ligne à la fin de sa tranche. Date enregistrée à l'émission ; les prélèvements des avions peuvent être espacés de plusieurs ticks.
- Population : seuls les avions de `line.vehicles` qui sont valides, de type AIR et dans l'état `VS_RUNNING` avec capacité du cargo de ligne positive contribuent au remplissage. Direction déterminée par le StationID de destination de l'ordre courant, `?` lorsque non attribuable. Stocks et notes sont relevés pour PASS et MAIL si ce cargo est valide.
- Smoke : `air_load7_shadow=0` contre `air_load7_shadow=1`, **1 graine (42) × 1 an**, deux duels, règle `gain_short` enregistrée avec 40×3 requis, mais **diagnostic seulement**. Réussite opérationnelle : compilation, durée complète, état sain, relevés dans le bras ON et aucun dans OFF.
- Exposition : **10 graines (42, 100, 999, 1234, 5678, 111, 222, 333, 444, 555) × 6 ans**, mêmes bras, duel standard OpexAI contre AAAHogEx, une répétition. Même règle `gain_short` 40×3 attendue ; l'échantillon 10×6 n'est pas une porte V102. `--script-debug`, un conteneur à la fois, `--cpus 10 --memory 8g --max-workers 10`, Docker Desktop local, cache `openttd-lab-home`.
- Mesures descriptives préconçues : remplissage moyen par vol et pondéré par capacité, quartiles et sens, classe de nombre d'avions ; corrélations charge, notes et stocks aux stations desservies ; tendance du stock et changements de flotte autour des renforts ; sous-service potentiel = remplissage élevé et stock croissant, sur-service potentiel = remplissage faible et stock stable ou décroissant. Toutes ces classes sont **des hypothèses descriptives**, pas une nouvelle règle de décision.
- Seuils de suggestion, uniquement pour le diagnostic : moyenne pondérée ≥ 80 % et pente positive des stocks pour « sous-desservie », ≤ 35 % et stock non croissant pour « sur-desservie » ; exiger plusieurs relevés dans des semaines distinctes. Contrôler les sens et la couverture, aucune règle de renfort adoptée automatiquement.
- L'analyse statistique portera sur les lignes d'observation et les graines, en rappelant que les semaines d'une ligne sont corrélées. Une différence ON/OFF du duel ne démontre pas la neutralité économique : le coût de sonde peut décaler les décisions.

### Correction de cadence pré-enregistrée après la première exposition

La campagne initiale `air_load7_exposure_10x6_20261022` est complète et
conservée, mais son cycle de voisins répété par ligne produit une cadence
réelle trop faible (médiane **35 jours** sur 6 387 intervalles) lorsque le réseau
grandit. Ce défaut de couverture a été constaté **avant** la campagne
corrective. Il est lié au coût de la sonde, pas à une règle de jeu.

Correction purement instrumentale : pré-calculer, en tranches de huit lignes,
un index station → lignes AIR une seule fois par cycle ; lire les vols
de deux appareils par tranche et émettre dès la dernière tranche.
Pour éviter un doublon dans les voisines, compter l'union des lineId
présents aux deux aéroports. Le défaut OFF reste intact.

Plan correctif : smoke `air_load7_smoke_v2_1x1_20261022`, puis nouvelle exposition
`air_load7_exposure_v2_10x6_20261022` sur les **mêmes 10 graines**,
avec les mêmes deux bras, durée, seuils descriptifs, ressources Docker,
et ordonnanceur. Les résultats de la première campagne ne seront pas
reclassés comme nouvelle preuve ; les chiffres définitifs de couverture
proviendront du second bundle.

**Échec du smoke optimisé v2 (avant toute exposition)** :
`air_load7_smoke_v2_1x1_20261022` a couvert les deux parties sans erreur,
mais **0 enregistrement AIR_LOAD7**. La mise en place de l'index relançait
son initialisation à chaque tour avant qu'une ligne puisse être relevée.
Un drapeau transitoire `AIR_LOAD7_ACTIVE` corrige ce défaut. Le smoke
indépendant `air_load7_smoke_v3_1x1_20261022` a **réussi** : 2/2 parties
complètes, **280 relevés ON, zéro OFF**, 14 lignes AIR, médiane des
266 intervalles = **7 jours**, maximum 19 jours. Ce bundle est celui
de la campagne d'exposition corrective.

## Données et résultats

### Identité, santé, comparabilité et sources

| Campagne | Bundle SHA256 (préfixe) | Parties saines | Relevés ON | Intervalle médian par ligne |
|---|---|---:|---:|---:|
| `air_load7_smoke_1x1_20261022` | `b6a685d691a4` | 2/2 | 190 (OFF = 0) | 9 j |
| `air_load7_exposure_10x6_20261022` (ancien balayage) | `b6a685d691a4` | 20/20 | 6 830 (OFF = 0) | 35 j |
| `air_load7_smoke_v2_1x1_20261022` (erreur de démarrage, invalidé) | `fdac284bd3d7` | 2/2 | **0** | indisponible |
| `air_load7_smoke_v3_1x1_20261022` (index corrigé) | `1e1cb6ea30f3` | 2/2 | 280 (OFF = 0) | **7 j** |
| **`air_load7_exposure_v2_10x6_20261022`** (analyse retenue) | **`1e1cb6ea30f3`** | **20/20** | **26 437 (OFF = 0)** | **14 j** |

Campagne retenue : dix graines disjointes, dix paires complètes, une répétition
et six ans chacun, **zéro `failed_runs`**, vingt fois
`game_ok=true, game_status=complete`. Manifeste SHA256
`5bb8beefb39a04fec197bfa8095f2bde5b258cdb69d5ba15331dc714ba200b91`.
Image locale `openttd-lab:latest` = SHA256
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Branche `master` sale, **aucun commit, push ou modification de défaut**.

Artefacts locaux du banc :

- Résultat structuré : `results/air_load7_exposure_v2_10x6_20261022.json`, manifeste adjacent, `*.jsonl`, et dix logs ON/dix logs OFF dans `results/air_load7_exposure_v2_10x6_20261022_engine/`.
- Décodeur reproductible : `sweeps/analyze_air_load_shadow.py`, sortie agrégée `results/air_load7_exposure_v2_10x6_20261022_engine/air_load7_analysis.json` et **tableaux complets par graine/ligne/direction/flotte/station/renfort** dans `air_load7_analysis.md` du même dossier. Les données brutes restent conservées.
- Commande d'analyse : `python -X utf8 sweeps/analyze_air_load_shadow.py 'results/air_load7_exposure_v2_10x6_20261022_engine/*.log' --high-load 0.8 --low-load 0.35 --format markdown --output results/air_load7_exposure_v2_10x6_20261022_engine/air_load7_analysis.md`.
- Tests : `uvx --from 'pytest==8.4.2' pytest -q sweeps/test_air_load7_shadow_contract.py sweeps/test_analyze_air_load_shadow.py sweeps/test_v251_inventory.py sweeps/test_v246_fixed_policies.py` : **32 réussis**. Les inventaires reflètent le 103e `AddSetting`, tous les bras hors sonde restent inchangés.

### Couverture réelle et remplissage

Dans les **26 437** clichés, **459 couples (graine, lineId)**,
**36 781 vols d'avions observés en état `VS_RUNNING`** ;
la médiane de clichés par ligne est **50** (430/459 lignes ont ≥ 20
relevés). Le décodeur ne signale aucune erreur de parsing, doublon en conflit
ou vol malformé. Il conserve les clichés sans avion en vol sans leur
imputer un remplissage nul.

La cadence de 7 jours est une **échéance minimale de relancement du cycle**,
et non une garantie hebdomadaire par ligne : parmi **25 978 intervalles**
entre clichés de la même ligne, médiane **14 j**, p75 **35 j**,
p90 **65 j**, maximum **294 j** ; **5 167 (19,9 %)** dépassent 42 jours.
La correction de l'index a divisé la médiane par 2,5 et multiplié le nombre
de clichés par 3,9 par rapport à l'ancien sondage, mais les longs trous
demeurent, notamment sur les réseaux plus denses et sous tâches coûteuses.
Chaque relevé décrit donc une **photographie**, jamais une moyenne temporelle
du remplissage de la rotation entière.

<table>
<tr><th>Population observée</th><th>Vols</th><th>Remplissage moyen par avion</th><th>Pondéré capacité</th><th>Médiane</th><th>P90</th></tr>
<tr><td>Tous vols</td><td>36 781</td><td>19,3 %</td><td>19,1 %</td><td>11,4 %</td><td>47,3 %</td></tr>
<tr><td>Destination A</td><td>15 429</td><td>—</td><td>16,8 %</td><td>10,0 %</td><td>43,2 %</td></tr>
<tr><td>Destination B</td><td>16 622</td><td>—</td><td>21,0 %</td><td>13,3 %</td><td>51,8 %</td></tr>
<tr><td>Ordre indéterminé (?)</td><td>4 730</td><td>—</td><td>20,0 %</td><td>11,4 %</td><td>49,1 %</td></tr>
</table>

Les **4 730 vols sans destination attribuable** (12,9 % des observations)
contribuent à la mesure globale, mais sont exclus des comparaisons
par gare et des corrélations directionnelles. La différence A/B peut
provenir de l'asymétrie des flux, de l'affectation des gares et du
biais de phase du vol ; elle n'est pas une estimation causale de demande.

| Nombre d'avions de la ligne au relevé | Vols observés | Remplissage pondéré | Médiane | P90 |
|---|---:|---:|---:|---:|
| 1 | 12 057 | 20,8 % | 11,8 % | 56,4 % |
| 2 | 16 721 | 20,7 % | 12,3 % | 49,5 % |
| 3 | 7 528 | **13,1 %** | 10,0 % | 33,5 % |
| 4 | 475 | **14,8 %** | 11,1 % | 34,4 % |

La répartition du remplissage par vol est très dissymétrique :
**27 217/36 781 (74,0 %) de 0 à 24 %**, 6 166 (16,8 %) de
25 à 49 %, 1 783 (4,8 %) de 50 à 74 %, 500 (1,4 %) de
75 à 89 %, 1 115 (3,0 %) de 90 à 100 %. Un avion ponctuellement
plein ne signifie pas qu'une ligne entière manque de capacité.
Sur les dix graines, le remplissage agrégé pondéré va de **14,9 %**
(100) à **22,3 %** (5678) ; moyenne simple des dix moyennes
de graines : **19,0 %**.

Exemples illustratifs, **≥ 35 clichés et ≥ 40 avions observés** :

| Graine / lineId | Clichés | Vols | Remplissage pondéré | Flotte finale | Distance |
|---|---:|---:|---:|---:|---:|
| 5678 / 5 | 107 | 125 | 59,4 % | 2 | 250 |
| 42 / 0 | 115 | 223 | 52,2 % | 3 | 214 |
| 222 / 0 | 120 | 188 | 46,1 % | 2 | 212 |
| 100 / 48 | 42 | 51 | 4,1 % | 2 | 177 |
| 444 / 46 | 42 | 42 | 1,8 % | 1 | 213 |

Les tables exhaustives, ainsi que l'âge et les modèles des avions
(ID du moteur OpenTTD), sont dans le Markdown de l'analyseur.

### Notes et stocks des aéroports (PASS, MAIL) et classification

Le calcul du ratio en vol porte sur `line.cargo`, ici le cargo de la ligne
AIR ; les relevés MAIL aux aéroports décrivent le contexte de demande,
**pas une mesure de remplissage de la soute MAIL**. Pour empêcher
de fausses alertes, seul PASS est classé sous/sur-desservi.
Les corrélations restent descriptives et sont évaluées **séparément
par graine, ligne et gare de destination**, sans fusion naïve des
semaines comme si elles étaient des observations indépendantes.

| Corrélation de Pearson au sein d'un segment PASS, au moins 6 paires valides | Segments | Médiane du coefficient r |
|---|---:|---:|
| Remplissage / note | 880 | +0,005 |
| Remplissage / stock | 882 | +0,016 |
| Note / stock | 902 | −0,165 |

Ces médianes ne suggèrent **aucune relation linéaire homogène
du remplissage avec la note ou le stock** sur l'ensemble des segments.
Une note élevée peut coexister avec des vols partiellement vides,
et le stock est sensible aux productions et aux départs.

Au seuil préenregistré (ratio pondéré ≥ 80 % et stock PASS montant pour
sous-service ; ratio ≤ 35 % et stock stable/descendant pour sur-service,
au moins trois lectures jumelées par station), sur **918 segments
PASS** : **0** « sous-desservi », **734** « sur-desservi possible »,
164 indéterminés et 20 insuffisamment documentés. Les **918 segments
MAIL** restent `pass_load_proxy_only` ; aucune classification MAIL.
Ces 734 alertes sont des **signaux de faible charge en vol**, et non
734 opportunités prouvées de retirer un avion : le gain marginal d'un
achat ou d'un retrait n'est pas observé par cette sonde.

### Évolution à proximité des renforts

La hausse de `fleet` entre deux clichés définit **648 épisodes possibles
de renfort** (y compris remplacement/transfert confondus si le nombre
change). Le suivi comparatif sur **28 jours avant/après** ne dispose
d'au moins deux clichés par fenêtre que pour **89/648 épisodes**
(13,7 %). Parmi ces 89, 83 ont une différence de remplissage
calculable : **59/83** baissent, médiane des deltas **−15,2 points
de pourcentage** ; médiane de variation de stock PASS :
**−13 unités en A**, **0 en B** ; notes PASS : **+1,6 point
en A**, **−1,6 en B**.
Les épisodes restent corrélés à la ligne et à la graine, le renfort
n'est pas assigné au hasard et les stocks changent avec la saison et
le trafic. La couverture de 89 épisodes est un sous-ensemble sélectionné :
**ces chiffres ne constituent ni un ITT, ni un rendement marginal net**.

### Comparaison économique ON/OFF : santé seulement

Le smoke v3 a validé exécution et journalisation. La campagne
corrective 10×6 complète donne sur le profit annuel terminal de
OpexAI, variante sonde ON moins référence sonde OFF :
**−34 318 £/an**, médiane **−51 989 £/an**, V/D/E **5/5/0**,
IC95 bootstrap **[−210 498 ; +122 676] £/an**, test de Wilcoxon
bilatéral **p = 1,0** ; ratio des moyennes de valeur compagnie
**1,004881** (+0,49 %). Le verdict enregistré est
`diagnostic_only` : dix graines à six ans ne sont pas une porte V102
et l'intervalle ne prouve ni équivalence économique ni neutralité
des opcodes. Les 20 parties sont saines. La même comparaison de
la campagne initiale sous sondage trop lent était −82 365 £/an,
IC95 [−218 618 ; +28 876] ; **aucune sélection du meilleur résultat
ni qualification a posteriori**.

## Limites et conséquence sur une éventuelle règle de renfort

La sonde respecte le comportement du moteur : lecture des états,
des ordres, des capacités et des stations, sans achat, vente,
modification du score ou de priorité. Le paramètre est **OFF par défaut**.
Il n'implique toutefois aucun coût nul quand ON : appels NoAI, création
de chaînes et journalisation consomment des opcodes et peuvent modifier
les calendriers des décisions. Le cycle est **étalé dans le temps** :
les avions sont relevés avant les aéroports et les lignes voisines
sur des ticks parfois distincts. `VS_RUNNING` écarte les appareils
à quai, en hangar ou en panne ; les avions en approche peuvent
être encore `VS_RUNNING`, et la phase du parcours influence la
charge instantanée. Le calcul ne reconstruit pas les flux livrés
ou les tours complets, et **19,9 % des intervalles excèdent
42 jours**. La direction de 12,9 % des observations est inconnue.

Les avis de sous/sur-service sont **des hypothèses descriptives** :
le remplissage PASS n'identifie pas la demande marginale qui serait
servie par un avion supplémentaire, le MAIL ne porte qu'un stock
de station, et des voisins partagent la même clientèle et les pistes.
Le seuil de sur-service sur la moyenne actuelle peut aussi masquer
quelques vols pleins d'une ligne jeune ou asymétrique. Un achat
récent ou une ligne en phase de montée de note ne se compare pas
directement à une ligne mature.

**Implication : ne pas fonder maintenant une règle de renfort sur
« charge moyenne > 80 % »**, qui ne s'est jamais accompagnée ici
du second critère de stock croissant au niveau des segments de ligne.
Les données justifient d'étudier les cas exceptionnels
**par sens et sur plusieurs rotations**, en combinant la pente du
stock, la note de la gare, les autres lignes partageant un aéroport,
la disponibilité réelle des vols et le profit marginal net.
Avant une nouvelle politique, obtenir une observation temporelle
plus régulière (ou orientée par livraison/rotation) puis une
validation causale même save ou ITT sur le bénéfice marginal,
avec suivi complet et coûts physiques inclus.

**Verdict : mesure passive et décodage fonctionnels, exposition
observée et chiffrée ; aucune décision ni défaut économique
modifié et aucune règle de renfort adoptée.**
