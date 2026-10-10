# RAIL P0 — ablation minimale du classement arbitraire, essai apparié 10/10/2026

## Hypothèse et isolement pré-enregistrés avant les jeux

Le flag `rail_magic_simple_roi=1` (le défaut historique reste `0` sur les quatre difficultés)
substitue, uniquement pour le classement TOP20 RAIL local, le `roi` déjà
calculé par le modèle physique au score `opcodeRatio + adjustedRoi * 15`.
Il court-circuite en ON les frontières de rotation 12/25/45 jours et les primes
130/115/100/60 %. La chaîne RAIL est harmonisée, avec maintien de la
sentinelle expérimentale V88 ; PAX_NEAR garde son exception. Le filtre d'admission
PAX 500/fret 200, les budgets A*, le vivier intermodal complet, le classement
capital/profit de C69/C70 et AIR/ROAD/WATER restent inchangés.
La branche OFF garde la formule historique ; aucun devis financier, objet projet,
reclassement OpexTopKFund ou recherche A* supplémentaire n'est ajouté en ON.

Au défaut `C80_RAIL_STOCK_WORKER/GATE=0` et `rail_origin_reuse=0`, le TOP20
n'est pas lu pour choisir les investissements intermodaux ; la prévision est
donc neutralité économique avec de petites différences possibles liées aux
opcodes et à la cadence de scheduler. Le gain attendu est une suppression de
complexité heuristique et non une amélioration économique.

## Critères de qualification avant lecture des résultats

1. Tests hôte de contrats puis smoke Docker 1×1 apparié, même source gelée.
2. Porte A **40 graines canoniques × 5 ans**, une répétition, deux bras sur
   même bundle, 80/80 parties complètes et saines. Seule la valeur du flag
   `rail_magic_simple_roi` varie, 0/1 ; autres P0 RAIL à zéro.
3. La neutralité économique requiert une moyenne et une médiane du delta
   `profit_year` terminal au voisinage de zéro ; qualification stricte :
   IC95 bootstrap de la moyenne entièrement dans une marge de ±1 % du profit
   terminal moyen de référence (intervalle d'équivalence), et ratio des
   moyennes `company_value` au moins −1 %, avec revue des pires graines.
   L'absence de significativité seule ne suffit pas.
4. Coût `cand_rank` mesuré par les compteurs natifs de `OpexBudget` (`OS|` et
   `BC|cand_rank`) des deux bras : moyenne du surcoût au plus 1 % de la
   dépense totale instrumentée `BT|` du bras OFF ; si disponible, vérifier aussi
   la borne haute IC95 du surcoût à 1 %. Les `IG/OB/RB/OA/OM` ne donnent qu'une
   somme PARTIELLE et ne peuvent être appelés « opcodes VM totaux ».
   Si le classement coûte davantage que le budget admissible, rejet.
5. Seulement si A satisfait santé, équivalence économique et opcodes
   négligeables, lancer porte B **20 graines canoniques × 10 ans**, 40/40
   parties complètes/saines, même conditions, mêmes marges, aucune chute
   structurelle RAIL/AIR. Dans les deux portes, étudier les constructions et
   l'évolution annuelle, pas seulement le dernier profit.
6. Un défaut ON nécessite les deux portes ; si la couverture d'opcodes est
   insuffisante pour statuer, laisser OFF et déclarer « non qualifié ».

Le harnais `gain_short` existe pour 40 graines et est paramétré avec
`--required-years 5 --min-useful-primary-delta-pct 0` afin de produire les
résultats et IC. Son verdict de **gain strict** ne fait pas office de verdict
d'**équivalence** ci-dessus : zéro delta aurait `fail_primary` au gain, mais
passerait le test d'équivalence. Aucun flag de profilage intrusif ajouté à un
seul bras (`probe_loop_ops`, `rail_magic_shadow`, etc.).

## Résultats

### Validation préalable

Tests hôte hors Docker : `test_rail_magic_simple_roi.py` 2/2,
`test_rail_magic_economics.py` 4/4, `test_homogeneous_preselect.py` 3/3,
`test_rail_origin_reuse.py` 56/56 et `test_c80_rail_stock_worker.py`
18/18, **83/83 tests verts**. Ces contrats ne remplacent pas un test du coût
réel des opcodes. Le smoke 1 graine × 1 an, campagne
`rail_magic_simple_roi_smoke_1x1_20261010_r1`, est sain 2/2 ; graine 42,
delta profit annuel +19 872 £ et valeur +7,20 %, **diagnostic uniquement**.

### Porte A : 40 graines × 5 ans, terminée

Campagne `rail_magic_simple_roi_A40x5_20261010_r1` : bundle commun figé
`fe7c47d5348589ed608417922c12af0b69730e854665c3a6abb7155cc8902429`,
manifeste
`2537a7ae4494d0553bb819dde3d665bb6366c42f73bf82a8516875d4c7df77e6`,
OpenTTD Lab image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
PC local Docker 10 CPU / 8 Go / 10 workers, une campagne.
Référence `OpexAI[rail_magic_simple_roi=0]`, variante
`OpexAI[rail_magic_simple_roi=1]` ; aucun autre réglage de politique différent.
**80/80 parties complètes et saines, 40/40 duels appariés**,
`comparison_complete=metric_coverage_complete=adoption_sample_complete=true`,
aucun failed_run ; année terminale 1974.

| Profit annuel terminal (variante − référence) | Valeur |
|---|---:|
| Moyenne | **+48 984,825 £/an** |
| Médiane | +49 901,5 £/an |
| Victoires / défaites / égalités | 24 / 16 / 0 |
| Wilcoxon bilatéral | p = 0,1831174 |
| IC95 bootstrap, 20 000 rééchantillonnages seed 0 | **[−18 742,9 ; +118 177,575] £/an** |
| Profit moyen référence | 1 939 557,3 £/an |
| Intervalle d'équivalence pré-enregistré ±1 % | **[−19 395,573 ; +19 395,573] £/an** |
| Valeur compagnie, ratio des moyennes | **+2,071772 %**, garde −1 % tenue |

**ÉQUIVALENCE NON DÉMONTRÉE** : l'IC95 de la moyenne ne rentre pas dans
l'intervalle d'équivalence ±1 % ; en particulier la borne supérieure
118 178 excède largement +19 396. Le résultat favorable en moyenne ne prouve
ni un gain ni la stricte neutralité. `fail_primary` du harnais signifie que
la porte de **gain** `gain_short` échoue ; c'est une autre règle que la porte
d'**équivalence** explicitement pré-enregistrée ici. La garde de valeur passe.

Delta moyen du profit par fin d'année : **1970 −1 290**, **1971 +22 387**,
**1972 +30 249**, **1973 +58 916**, **1974 +48 985 £/an**.
Pires graines en 1974 : **12345 −366 663**, **701256 −365 813**,
**841478 −325 041**, **781335 −314 720 £/an** ; meilleures :
**999533 +443 142**, **313707 +420 119**, **706990 +415 459 £/an**.
Les disparités rendent une qualification sur moyenne seule inappropriée.

Différences moyennes d'**état final** en 1974 (pas nombre d'achats ni
preuves de causalité chantier) : **−1,425 véhicule RAIL**,
**−3,300 avions**, **+0,250 véhicule ROAD** ; **−1,675 installations RAIL**,
**+0,400 installations aéroport**, **−4,450 véhicules tous modes** et
**−0,975 stations** par partie. Aucune amélioration structurelle RAIL
n'est démontrée.

### Opcodes et décision sur la porte B

Le décodeur du harnais rapporte `observed_opcodes_total` : en moyenne
**44 666 270** en référence et **48 954 106** en variante, delta
**+4 287 836 opcodes instrumentés partiels** par partie en dernière
observation ; `observed_opcode_complete_cpu=false` pour les **80** bras
OpexAI. Ce compteur additionne IG/OB/RB/OA/OM : il **n'inclut ni les
opcodes du calcul de ratio RAIL, ni `cand_rank` TOP20**, donc cette hausse
ne constitue PAS une mesure du surcoût de la variante et ne peut servir de
test d'opcodes VM total. Le nombre d'échantillons reconnus varie lui-même
(moyenne 171,425 OFF contre 158,800 ON), rendant le delta dépendant de
trajectoires et de signes conservés. Les panneaux OS/OP/BT sont produits
dans les sauvegardes mais le bundle d'essai ne les a pas extraits, et
`--retain-savegames` était désactivé : **coût spécifique et VM totale non
mesurés**. Ne pas déduire « négligeable » du fait qu'aucun devis n'a été ajouté.

**Verdict : PAS D'ADOPTION et pas de 20×10.** La porte A n'établit pas
l'équivalence économique pré-enregistrée, et la condition opcode est
également indécidable. Conserver `rail_magic_simple_roi=0` dans toutes les
difficultés et les autres flags P0 inchangés. Tout futur essai devra capturer
la mesure `cand_rank` et du calcul de ratio sur les deux bras de façon
symétrique, avec contrôle explicite du coût de la sonde et de sa neutralité ;
un diagnostic neuf ne transforme pas rétroactivement ce 40×5 en qualification
économique/opcodes. Aucune campagne B ni changement de défaut, commit ou push.
