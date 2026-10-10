# P0 AIR — Essai isolé de réalisation directe (10/10/2026)

**Statut définitif : NON DÉMONTRÉ, mécanisme expérimental retiré du code actif.**
La présente fiche décrit un bundle de campagne figé, et non un réglage
encore disponible dans la copie courante. Aucun des nombres magiques
visés n'a été supprimé du comportement livré.

## Contexte et décision initiale

L'essai `air_p0_learned_revenue=1` du 09/10 a échoué à la porte A appariée 40×5
(−20 488,4 £/an, IC95 bootstrap [−109 677 ; +73 409], valeur −0,44 %).
Il ajoutait des époques de flotte, une recotation à chaque changement et une
validation leave-one-out. Il ne permettait pas de séparer les effets du revenu,
du forfait MAIL et de la déduplication C70. Voir
`docs/air_p0_learned_revenue_20261009.md` et son bundle `6f19f9fb…`.

## Hypothèse isolée, pré-enregistrée avant le banc

`air_p0_direct_realization=0` au défaut pour les quatre difficultés. Le bras
`=1` réutilise **uniquement** les observations que C121 recueille déjà au
rapport annuel : une ligne AIR à flotte initiale inchangée, âgée d'au moins
deux ans (premier exercice civil annuel complet), porte son ratio de recettes
observées/prédites en millièmes dans `c121RealizationPm` et son année de mesure
dans `c121RealizationYear`. Les observations anciennes sont filtrées comme au
défaut (année courante − 1). Les mêmes scalaires de ligne sont persistés et
rejoués à `Load` ; aucun nouvel état n'est sauvegardé, aucun scan ajouté.
Cette variante est désactivée si `air_p0_learned_revenue=1` est simultanément
sélectionné : les accumulateurs des deux prototypes ne partagent pas la même
unité de mesure.

Pour `hubsite` et `hubhub`, utiliser la moyenne de ces ratios par bras dès la
première observation éligible, strictement 1,0 avant la première. Le bras
`newpair` conserve son comportement historique. Les achats de flotte continuent
de lire le facteur historique : seuls les nouveaux devis des deux bras hub
lisent les deux facteurs directs, reconstruits après `Load`. Éliminer, dans
ces devis et sous ON seulement, le seuil de deux lignes, la pseudo-ligne de 1 et le lissage arbitraire
`0.75 + 0.25 * learned`. La branche expérimentale ON évite de recalibrer le
profit AIR une deuxième fois par C70/C82 si la cotation C121 porte déjà un
facteur de réalisation différent de 1. La conservation de C70 avant toute
observation préserve son score historique à froid.

Les tarifs principaux C121 utilisent déjà PASS et MAIL physiques : les 104 %
et MAIL15 appartiennent à des chemins historiques/hubs particuliers, et ne
sont **pas supprimés** dans cet essai. Le lissage `0.5 + 0.5 * learned` du
levier engine-only OFF reste lui aussi inchangé. Ne pas attribuer leur retrait
à un éventuel résultat de cette variante.

## Protocole et critères éliminatoires

- Référence `OpexAI[air_p0_direct_realization=0]`, variante `OpexAI[air_p0_direct_realization=1]`, *même arbre figé*, tous autres défauts courants (en particulier `air_p0_learned_revenue=0`). Comparer annuellement revenus, lignes AIR, `profit_year` et `company_value` par graine, et les opcodes total observés, sélection et planification AIR, à charge comparable si les trajectoires changent.
- Vérifier contrats, compilation et Save/Load. Smoke apparié 1×1 puis, seulement si exposition et coût admissibles, diagnostic 1×5. L'observation ne peut devenir effective qu'après un rapport annuel complet ; le smoke ne juge pas la rentabilité.
- Porte économique **40 graines × 5 ans**, 80 duels, mêmes graines canoniques, règle `gain_short`, seuil relatif +4 %, Wilcoxon p<0,05, IC95 bootstrap inférieur >0, garde `company_value` −5 %. Les conditions utilisateur sont plus strictes : neutralité économique **positivement démontrée** et aucun coût opcode durable. Un test non significatif n'établit pas l'équivalence.
- Arrêt et maintien du défaut OFF si une perte économique/une hausse durable d'opcodes est établie, ou si la neutralité reste non démontrée. Aucune modification du défaut, aucun commit/push.

## Résultats

Les 4/4 contrats ciblés dans Docker et le selftest du harnais 1v1 passent.
La sonde hôte réutilise les panneaux de jeu pour les opcodes déjà publiés ;
elle ne couvre pas tous les opcodes du moteur ni la construction AIR.

Le smoke définitif seed42 × 1 an (campagne
air_p0_direct_realization_smoke_1x1_20261010_r4,
bundle 8cadc0e611d3ff27edbe25573fa54dae9a8886eb1217f3719be7c3d72bf02900)
termine deux parties saines, avec profit et valeur strictement identiques
entre OFF et ON en 1970. Les essais r1/r2/r3 du smoke représentent des
versions intermédiaires du correctif.

Le Save/Load ON (results/air_p0_direct_realization_save_load_20261010_r1.json)
termine 60 sauvegardes initiales, puis recharge le 01/01/1974 et produit
25 sauvegardes de reprise sans erreur fatale ; LOAD_RECONCILE est observé.
Les facteurs historiques rapportés en 1973 sont rétablis au chargement :
hubhub 0,7783333 sur 14 lignes, hubsite 0,45957142 sur 6 lignes.
Le harnais signale une compagnie fantôme distincte au reload, sans effet
attribué aux métriques OpexAI.

Le diagnostic opcode apparié seed42 × 5 ans
(air_p0_direct_realization_opcode_diag_1x5_20261010_r1,
bundle 2d3886980da8c7fa318654e6fb1d59219a0b482aa24996242a8cd2e1c8ab8a2d)
active probe_loop_ops et probe_span_trace dans les deux bras.
De 1970 à 1972, les postes C121 cache, demand, engine, scan, static et
winner présentent des opcodes mesurés exactement identiques (respectivement
275814, 10849895, 650294, 1081088, 1252118, 5662303) et les mêmes
nombres d'appels (1155, 1112, 319, 1112, 1112, 1112). Les agrégats
annuels de boucle sont aussi strictement égaux pendant ces trois années.
En 1973, la correction devient exposée (hubhub : 3 lignes éligibles ;
hubsite : 7), puis les trajectoires divergent. Sur cinq ans,
air.c121.scan a 1669 appels ON contre 1632 OFF, coût moyen 985 contre
987 opcodes/appel ; winner 5086 contre 5081 opcodes/appel. Les mesures
LOOP_OPS imputent 10000 opcodes par tick traversé, et les deux profils
perturbent le chemin normal. La neutralité **totale** en opcodes
reste donc à prouver et ne doit pas être inférée de ce diagnostic.

La campagne 40 × 5 appariée finale est
air_p0_direct_realization_gateA_40x5_20261010_r1, bundle
061096c0b5b7cb90cbb8b0a1a162950e97209188c8783b8dc3ee7287e291c5a6,
manifest f4d65ad8fb76489d44a0a2d04b4a72836e6da10b32bcc5c2abfd5dc34172b282.
Ses résultats complets et le verdict conditionneront toute décision.
Le défaut reste OFF ; aucun commit ni push.

## Résultat de la porte économique 40 × 5

La campagne finale a exécuté **80/80 parties**, **40/40 paires** saines et
complètes. Les contrôles du harnais valident
comparison_complete, adoption_sample_complete et metric_coverage_complete.
Le verdict brut est **fail_primary** (économie). Delta du profit annuel
terminal ON−OFF : **−7 522,2 £/an** de moyenne, **−3 241 £/an** de
médiane, **18 victoires / 22 défaites / 0 égalité** ; Wilcoxon exact
bilatéral **p=0,878507**, IC95 bootstrap (20 000 rééchantillonnages,
graine 0) **[−48 340,275 ; +32 905,85] £/an**. Le seuil de gain
prédéclaré de +4 % équivaut à +79 397,528 £/an. La valeur de compagnie
se dégrade de **0,394318 %** (ratio des moyennes 0,996057), sous la garde
de 5 %, sans démonstration positive de neutralité.

| Année terminale observée | Delta moyen ON−OFF (GBP/an) | Médiane | V/D/E |
|---|---:|---:|---:|
| 1970 | 0 | 0 | 0/0/40 |
| 1971 | −4 933,73 | 0 | 0/1/39 |
| 1972 | −5 027,20 | 0 | 3/7/30 |
| 1973 | −199,22 | +2 302 | 21/19/0 |
| 1974 | −7 522,20 | −3 241 | 18/22/0 |

Les 200 observations économiques détaillées des **40 graines × 5 ans**
figurent dans
results/air_p0_direct_realization_gateA_40x5_20261010_r1_annual.csv,
avec profit annuel, profit des avions AIR en année courante, nombre de
lignes AIR et valeur de compagnie finale pour chaque graine. Ce sont des
mesures appariées de chaque bras, jamais des moyennes des parties AAA.

## Coût d'opcodes : échec de preuve de neutralité

Le décodeur hôte du harnais 1v1 mesure les compteurs déjà présents dans
les panneaux SIGN, sans sonde NoAI supplémentaire dans cette porte.
Sa couverture de CPU total est explicitement incomplète. Pour les
**40/40 paires**, la somme des postes observables vaut en moyenne
**42 957 847 opcodes OFF** contre **46 414 785 ON**, delta **+3 456 938
(+8,05 %)**, médiane des deltas **+1 440 479,5**, et 23 graines ont
un compteur partiel supérieur sous ON. L'essentiel vient des tentatives
RAIL : **+3 375 502** opcodes/graines (5,65 tentatives OFF,
6,03 ON), conséquence possible d'une charge différente ; les postes
AIR planification représentent **+15 089** opcodes/graines avec
53,27 appels OFF contre 53,88 ON. Sur les onze graines avec le même
nombre d'appels AIR mesurés, le delta moyen est d'environ
**−10,63 opcodes par appel** ; cela ne démontre pas un surcoût
structurel mais ne couvre pas l'intégralité des calculs AIR ni des
constructions. Détails par graine et composant :
results/air_p0_direct_realization_gateA_40x5_20261010_r1_opcodes.csv.
Rapport machine synthétique :
results/air_p0_direct_realization_gateA_40x5_20261010_r1_analysis.json.

Les trajectoires deviennent différentes après les premières cohortes,
donc les +8,05 % des postes observés **ne peuvent pas être entièrement
attribués** à la formule de recette. Cela ne prouve surtout pas une
neutralité du CPU total. Les sondes d'égalité C121 jusqu'en 1972,
mentionnées plus haut, donnent seulement une preuve locale.

## Décision et bilan de simplicité

**NON DÉMONTRÉ** selon les critères utilisateur : absence de preuve
positive de neutralité économique, échec de la porte de gain, absence
de preuve de neutralité globale en opcodes. Ne pas ouvrir la porte B,
ni adopter une correction en prétendant que p>0,05 établirait
l'équivalence. Le correctif expérimenté avait ajouté un booléen de
réglage, un indicateur d'exposition, une table de deux ratios
reconstructibles, des gardes dans les devis et dans C70/C82. Comme
aucun avantage n'est démontré, **tous ces ajouts ont été retirés
chirurgicalement après la campagne**, sans modifier les travaux
concurrents. La référence garde les pourcentages et les lissages
historiques, y compris leur cold-start et leur Save/Load.

**Coefficients éliminés du code livré : zéro.** Le lissage 75/25
avait été remplacé uniquement dans le bundle expérimental (avec
facteur strictement 1,0 avant observation), et a été rétabli.
Le 104 %, MAIL 15 %, le 50/50 dormant, le seuil de deux lignes
et C70 restent en place. Le décodeur hôte générique d'opcodes
partiels, sans surcoût en jeu, est le seul petit apport conservé.
Aucun commit ni push n'a été créé pour ce chantier.
