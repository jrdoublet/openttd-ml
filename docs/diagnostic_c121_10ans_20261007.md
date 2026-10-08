# C121 contre C115 : diagnostic de la perte à dix ans

Analyse hors ligne du 07/10/2026, sur les **vingt graines complètes de B**, sans
nouvelle partie ni changement de politique. Campagne
`c121_vs_c115_current_B_20261007`, bundle
`dc306cb2804c2d77fd6ea40a4a71a555864eff1924048ac5bace7a34242acfff`.
Le [bilan de qualification](resultats_c121_vs_c115_20261007.md) conserve les
verdicts : A passe, B échoue au profit et à la garde de valeur. C115 reste le défaut.

## 1. Explication comptable vérifiée

Moyennes par partie sur les quatre trimestres clos du checkpoint terminal :

| £/an | C115 | C121 | C121 − C115 |
|---|---:|---:|---:|
| Recettes | 2 639 974,45 | 2 916 683,10 | +276 708,65 |
| Dépenses, en valeur positive | 354 114,85 | 881 990,00 | +527 875,15 |
| Profit | 2 285 859,60 | 2 034 693,10 | **−251 166,50** |

Les recettes augmentent de 10,5 %, mais les dépenses de 149,1 %. Le supplément
de dépenses absorbe tout le supplément de recettes, puis 251 k£ de profit.
Ce résultat concerne la compagnie entière : la ventilation des dépenses par
mode, infrastructure, achats et exploitation n'est pas collectée ici.
Il serait abusif de nommer les 528 k£ « coûts de fonctionnement des avions ».

Attention au schéma : `income_last_year` et `expenses_last_year` contiennent en
réalité **le dernier trimestre clos** (`old_economy[0]`, extracteur du harnais).
L'analyse prend une observation par trimestre aux checkpoints février, mai,
août et novembre ; elle vérifie exactement recettes + dépenses signées =
`profit_year` terminal pour chaque bras et chaque graine. Même contrôle pour
les années 2 à 10, soit 360 identités comptables. Aucun trimestre mensuel répété
n'est compté plusieurs fois. L'année 1 reste partielle, sans annualisation.

| Année de partie | Recettes supplémentaires, k£ | Dépenses supplémentaires, k£ | Delta profit, k£ |
|---|---:|---:|---:|
| 2 | +402,3 | +51,4 | +350,9 |
| 3 | +392,6 | +113,2 | +279,4 |
| 4 | +240,7 | +170,6 | +70,0 |
| 5 | +390,8 | +267,7 | +123,1 |
| 6 | +393,0 | +347,5 | +45,5 |
| 7 | +438,1 | +415,0 | +23,2 |
| 8 | +415,5 | +468,2 | −52,7 |
| 9 | +312,8 | +503,1 | −190,3 |
| 10 | +276,7 | +527,9 | −251,2 |

La hausse des dépenses est progressive ; le retournement ne vient pas d'un
seul checkpoint défaillant. Ce sont des trajectoires corrélées des mêmes graines,
pas neuf qualifications indépendantes. La ligne « année 3 » est le sous-ensemble
de B, distinct des quarante graines de la porte A.

## 2. Flotte et implantation : ce qui est observé

| Moyenne terminale | C115 | C121 |
|---|---:|---:|
| Avions principaux | 79,70 | 154,55 |
| Capacité passagers aérienne simultanée | 9 216,5 | 35 126,25 |
| Aéroports | 27,30 | 24,30 |
| Villes avec aéroport Opex | 26,40 | 24,10 |
| Gares physiques, tous modes | 61,55 | 45,80 |
| Véhicules ferroviaires principaux | 12,25 | 9,50 |
| Véhicules routiers principaux | 10,95 | 5,75 |
| Trésorerie, M£ | 10,257 | 7,898 |

C121 a **1,94 fois plus d'avions et 3,81 fois plus de places**, sur un réseau
aéroportuaire moins étendu. La capacité moyenne par avion passe d'environ
116 à 227 places (ratio des totaux). Les avions par aéroport passent de 2,92
à 6,36 ; ce ratio décrit la densité globale, pas une file d'attente mesurée.
Les modèles changent aussi : l'ID moteur 223 représente 2 407/3 091 avions C121
contre 261/1 594 côté C115 ; aucune hypothèse sur leurs noms ou performances
n'est nécessaire pour constater cette concentration.

Les logs C121 propriétaire 0 contiennent 1 387 événements `C121_BUILD` :
997 `hubhub` (71,9 %), 302 `hubsite` et 88 `newpair`. Ce sont des constructions
cumulées, pas 1 387 lignes survivantes. 1 225 événements construisent un seul
avion ; tous indiquent une cible supérieure à la flotte construite. **L'accumulation
ne s'explique donc pas simplement par des achats massifs à chaque ouverture.**
Les champs `actual_profit` de ces événements restent des prévisions du modèle,
pas du profit réalisé.

L'hypothèse principale est une densification dont les recettes marginales ne
couvrent plus les dépenses marginales, associée à une moindre expansion et à
moins de diversification. Congestion, partage de demande entre lignes et choix
d'appareils sont des explications possibles, non départagées : la campagne n'a
pas collecté la télémétrie par ligne, le remplissage ou les attentes d'aéroport.
La trésorerie terminale élevée exclut une pénurie globale de liquidités à cette
date ; elle ne prouve pas l'absence de blocages de portefeuille antérieurs.

## 3. Lecture du code et hétérogénéité

Le profil contient la réalisation adaptative et le premier renfort live limité
aux quatre premières années (`info.nut`, `task_air.nut`). Le classifieur de
`projects_selection.nut` verrouille le régime une fois pour toutes : les logs
montrent **18 graines en race et 2 en efficiency**, toutes classées sur 1971.
`projects_models.nut::OpexC121RealizationFactor` conserve le facteur 1 en race ;
la correction adaptative des projets réutilisant des hubs ne s'y applique donc
pas, même plus tard. C'est une piste pour expliquer une correction tardive
insuffisante, **pas la preuve que changer le classifieur améliorerait le résultat**.
Les précédentes ablations du 04/10 restent valables pour leurs profils ; aucune
variante rejetée n'est réactivée et aucune relance n'est engagée.

Les dépenses augmentent sur **20/20 graines** ; les recettes augmentent sur
17/20, mais le profit ne progresse que sur 6/20. Les pertes 999 (−1 709 k£) et
17 (−1 188 k£) combinent recul des recettes et surcoût. Elles représentent 57,7 %
du déficit net agrégé. À titre de sensibilité descriptive, enlever ces deux
graines laisserait encore −118 k£/an sur les dix-huit autres : le verdict officiel
reste celui des vingt graines, sans exclusion ni nouvelle inférence statistique.

## 4. Écart avec AAAHogEx

Écart signé = profit Opex − profit AAAHogEx. Une valeur plus négative signifie
un retard plus grand. Moyennes en M£/an ; mêmes vingt graines de B :

| Année | Écart sous C115 | Écart sous C121 | Amélioration de l'écart par C121 |
|---|---:|---:|---:|
| 1, partielle | −0,071 | +0,065 | +0,136 |
| 2 | −0,451 | −0,040 | +0,411 |
| 3 | −0,669 | −0,254 | +0,415 |
| 4 | −1,275 | −1,150 | +0,125 |
| 5 | −1,974 | −1,767 | +0,207 |
| 6 | −2,961 | −2,998 | −0,037 |
| 7 | −4,016 | −4,046 | −0,031 |
| 8 | −5,009 | −5,247 | −0,239 |
| 9 | −5,740 | −6,064 | −0,324 |
| 10 | **−6,482** | **−6,880** | **−0,398** |

Le retard face à AAAHogEx se creuse fortement sous les deux politiques. C121
améliore d'abord l'écart, puis cet avantage disparaît dès l'année 6, avant même
le retournement du profit propre à l'année 8. À dix ans, AAAHogEx gagne en moyenne
8,768 M£ avec C115 en face et 8,915 M£ avec C121. La dégradation de l'écart se
décompose donc en **−251,2 k£ pour Opex et +147,3 k£ pour AAAHogEx**.

La dégradation moyenne de l'écart de 398,4 k£ n'est toutefois **pas statistiquement
établie** : IC95 bootstrap [−1 160,4 ; +340,5] k£, Wilcoxon p=0,4980,
9 améliorations/11 dégradations. Opex reste derrière AAAHogEx dans les vingt
graines terminales des deux bras. Ces métriques descriptives ne remplacent pas
le critère primaire V102, qui porte sur le profit propre d'Opex.

## Preuves et suite

Script reproductible local :
`results/c121_vs_c115_current_20261007/diagnostic_b.py` ; sortie détaillée
`diagnostic_B.json` dans le même dossier. Entrées : `bench.json`, `bench.jsonl`
et `bench_engine/*.log` de B, inchangées. Hash du rapport source :
`d8d60749a2da1cbcf407daf60e3015ddaaac47a62aada87f92f2338c1fda12b9`.

Le prochain diagnostic utile serait une mesure passive, stratifiée par
premier avion/renfort et newpair/hubsite/hubhub, des recettes, coûts, remplissage,
rotations et attentes, en conservant les chemins C115 et C121. Ce besoin reste
distinct d'une correction et d'une nouvelle qualification ; aucune partie
supplémentaire n'a été lancée dans cette analyse.
