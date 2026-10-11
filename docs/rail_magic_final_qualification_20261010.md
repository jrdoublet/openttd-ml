# P0 RAIL — verdict de qualification du classement local (10 octobre 2026)

## Décision finale — 11 octobre 2026

L'utilisateur a explicitement tranché : **« On a rejeté les 2 paramètres. C'est fini »**.
**REJETER définitivement `rail_magic_simple_roi=1` et `rail_magic_simple_opcode=1`**.
Les deux flags étaient à **0** durant la qualification et ont ensuite été
retirés du code actif lors du nettoyage du 11 octobre ; conserver la formule
historique. Ne plus lancer
de campagnes ou de qualifications pour ces deux variantes. `simple_opcode`
présente une régression économique étayée ; `simple_roi` est rejeté sur
décision utilisateur, **sans preuve de perte économique ni de hausse globale
des opcodes**. Les résultats passés demeurent archivés.

Le fichier final de la campagne `rail_magic_roi_strict_40x10_20261010_r2`
était présent à la clôture et Docker inactif ; **aucune lecture ou validation
statistique de cette sortie n'a été entreprise** après la décision.

## Statut et provenance des décisions (état historique avant clôture)

L'utilisateur a **explicitement abandonné `rail_magic_simple_opcode=1`** :
son rejet économique est définitif et son score ne doit plus être testé ON.
Avant la décision du 11 octobre, `rail_magic_simple_roi=1` relevait d'un
**rejet de qualification provisoire**, sans preuve de perte économique ou de
surcoût VM global. **Ce mandat prospectif est maintenant clos.**
La citation antérieure « On abandonne les 2 solutions. Documente cela. »
n'était pas attestée au moment de la reprise. La **décision explicite du
11 octobre 2026 ci-dessus** tranche désormais la question.

La campagne confirmatoire `rail_magic_roi_strict_40x10_20261010_r1`
(40 nouvelles graines × 10 ans) a démarré mais **n'a produit aucun JSON
final** ; son lanceur s'est terminé avec code 1 et son conteneur était
absent au contrôle. La cause de cette interruption n'est **pas établie**.
Ni arrêt volontaire ni instruction utilisateur de l'arrêter ne sont prouvés.
La campagne `r2` reprend **les mêmes graines, critères et bundle**
`2847a30db049a96d5a65c01117102676c00f3d2de30cb5302903f35a500157f1`
sans réutiliser de résultats partiels. Ces pré-enregistrements sont désormais
**archivés et inactifs** ; aucun changement de comportement par défaut
n'est autorisé.

| Variante | Effet économique connu | Coût opcode connu | Décision |
|---|---|---|---|
| `simple_opcode` | **NÉGATIF**, −88 104 £/an et valeur −4,685 % à 40×5 | Économie locale sur les 6 viviers synthétiques ; VM totale inconnue | **REJETER définitivement** |
| `simple_roi` | **INDÉTERMINÉ pour équivalence ±1 %**, +48 985 £/an et valeur +2,072 % à 40×5 | Selon les viviers : −33,10 % à +16,45 % du coût local score + TOP20 ; VM totale inconnue | **REJETER DÉFINITIVEMENT** — décision utilisateur du 11/10 |

### Trois scores, archivés uniquement pour expliquer les essais

Soit `Q = floor(profitAnnual * 1000 / predictedIterations)` (estimation
£/an par 1 000 itérations A* ; **pas** des opcodes VM réels), et `R = roi`
issu du devis physique. Le bonus historique de rotation vaut **130 %** si
`oneWayDays <= 12`, **115 %** si `<=25`, **100 %** si `<=45` et
**60 %** sinon. Le bonus fret actuel est neutre (100 %). Les divisions
entières successives doivent être préservées dans toute relecture du code.

- **Historique conservé** : `score = Q + 15 * floor(R * rotationBonus / 100)`.
- **Simple ROI rejeté** : `score = R` (sans bonus ni terme `Q`).
- **Simple opcode rejeté** : `score = Q` (sans ROI ni bonus).

En amont, le filtre de vivier historique admet les devis RAIL à profit
annuel positif et `Q >= 500` pour PAX ou `Q >= 200` pour fret lorsque
`VIVIER_RATIO_FILTER` est actif, sauf régime `PAX_NEAR` particulier.
Ce filtre, le TOP20 RAIL local et la sélection du portefeuille intermodal
C69/C70/TOP64 sont **trois étages différents** ; modifier le TOP20 local
ne remplace pas automatiquement une décision de financement intermodal.

## Décision de production : **CONSERVER LES DEUX VARIANTES OFF**

Les deux ablations ont été isolées dans le code, avec défauts toujours à zéro.
La demande était de supprimer les seuils de durée 12/25/45 jours, les primes
130/115/100/60 % et le terme `ROI×15` sans nuire à l'économie **et** sans
surcoût significatif d'opcodes. Aucune des deux variantes n'a franchi toutes
les portes nécessaires à une adoption. **Conserver la formule historique.**

Il faut distinguer le **rejet de l'adoption** de la démonstration d'une
régression sur chaque métrique : une variante non qualifiée peut être rejetée
de production sans qu'on affirme faussement que son effet économique est
négatif ou que son coût VM total a augmenté.

| Variante | Économie 40×5 appariée | Coût propre score + TOP20, travail égal | Verdict d'adoption |
|---|---|---|---|
| `rail_magic_simple_opcode=1` | **Négatif** : Δprofit −88 104 £/an, IC95 [−172 423 ; −6 074], valeur −4,685 %, 80/80 saines | **Positif sur six profils synthétiques** : −24,7 à −77,8 % d'opcodes | **REJET — perte économique** |
| `rail_magic_simple_roi=1` | **Indéterminé** au critère historique d'équivalence stricte ±1 % : Δprofit +48 985 £/an, IC95 [−18 743 ; +118 178], 80/80 saines | **Hétérogène** : économies sur quatre profils et **surcoûts +12,85 % et +16,45 %** sur deux profils | **REJET DE QUALIFICATION — neutralité économique historique non démontrée et garde opcode +1 % non démontrée** |

Les intervalles économiques et les nombres d'opcodes sont issus de
**expériences différentes** : les premiers sont des parties A/B en économie,
les seconds des microbenchmarks Squirrel sur **mêmes candidats de synthèse**.
Le microbenchmark démontre une sensibilité de l'algorithme à la distribution
et à l'ordre des candidats, et **ne représente pas** la distribution complète
des viviers RAIL du simulateur. Ses six profils ne permettent pas d'estimer
un IC représentatif de la population ni le total VM de l'IA. Ainsi les labels
positif/hétérogène ne concernent que **le coût intrinsèque sur les profils
effectivement mesurés** ; le coût VM total reste **indéterminé**.

## 1. Économie — anciens 40×5, leurs critères et les limites

Le rapport `docs/rail_magic_simple_roi_gate_20261010.md` montre que ROI pur
ne satisfait pas la **condition d'équivalence** pré-enregistrée de la porte A :
son IC95 bootstrap déborde ±19 396 £/an. La valeur compagnie moyenne gagne
+2,07 %, mais cela ne suffit pas pour une preuve de neutralité du profit.
La porte B20×10 ne s'ouvre pas selon ce protocole.

Le rapport `docs/rail_magic_simple_opcode_gate_20261010.md` montre une
régression moyenne avec IC95 sous zéro et une garde de valeur échouée ; il
est inutile de le relancer pour tenter de sauver sa qualification économique.

**Contrat utilisateur plus récent** dans
`docs/experimental_acceptance_policy_20261010.md` : les FUTURS essais peuvent
qualifier une **non-infériorité unilatérale 95 %** à −1 % du profit et −1 % de
valeur, et un surcoût opcode au plus +1 % à charge identique.
`sweeps/rail_roi_decision_power.py` a réanalysé **exploratoirement** l'ancien
40×5 avec ces bornes : ROI pur L95 profit **−0,411126 %**, L95 compagnie
**−0,638229 %**, compatibles avec cette future politique. Ce retraitement
ne **rétroqualifie pas** un essai mené sous une autre règle, ni ne remplace
un holdout 40×10 sur des graines inédites.

Les 40 graines inédites du holdout et son test hôte à couverture
fermée sont **pré-enregistrés** sous
`docs/rail_magic_roi_holdout_prereg_20261010.md` et
`sweeps/rail_roi_holdout_decision.py` (8 tests). Le mandat prospectif plus
récent demande néanmoins d'exécuter ce 40×10 si les deux surcoûts
synthétiques ne suffisent pas à prouver une régression structurelle
globale, ce qui a été vérifié. Son résultat économique ne pourra jamais
tenir lieu de garde opcode +1 % sur le travail réel.

### Extrêmes observés de `simple_roi` (ne pas mélanger leurs dénominateurs)

- **Pire baisse de profit annuel par graine du 40×5 : `12345`**,
  `profit_year` terminal OFF **1 794 457 £/an**, ON **1 427 794 £/an**,
  soit **−366 663 £/an (−20,43 %)**. Valeur compagnie OFF **5 405 830 £**,
  ON **4 566 733 £** (−839 097 £). Ensuite viennent 701256
  (−365 813 £/an), 841478 (−325 041 £/an) et 781335
  (−314 720 £/an). Ces cas ne modifient pas le verdict statistique
  des 40 paires : la moyenne reste positive et l'effet économique en
  population indéterminé pour l'ancienne équivalence.
- **Plus forte augmentation d'opcodes du bloc `score + TOP20` à charge
  strictement identique : `mixed200`**, 33 559,25 OFF contre 39 078,50
  ON, soit **+5 519,25 opcodes (+16,45 %)**. Dans ce même bloc, le
  classement TOP20 seul passe de 23 040,25 à 33 863,00 opcodes
  (**+46,97 %**), même si la formule ROI seule est moins coûteuse.
  `mixed200` est un pool **synthétique**, pas une graine de carte.
- **Plus grand écart du panneau d'opcodes PARTIELS parmi les 40 parties :
  graine `65537`**, `observed_opcodes_total` OFF **32 685 375** contre ON
  **65 220 600**, soit **+32 535 225 (+99,54 %)**. Les échantillons
  reconnus sont 182 OFF et 166 ON, et
  `observed_opcode_complete_cpu=false` dans les deux bras. Ce sont
  des postes couverts dépendants de la trajectoire, **pas** les opcodes VM
  totaux et **pas** le surcoût attribuable du score. La graine 65537
  **n'est pas** la pire perte de profit (son profit augmente de
  1 414 266 à 1 502 895 £/an).

Ces extrêmes sont archivés sans modifier les fichiers JSON des campagnes ;
la comparaison à charge identique et l'analyse de trajectoire sont deux
expériences distinctes.

## 2. Opcodes — mesure effective et limites de généralisation

Le banc autonome `sweeps/rail_magic_opcode_microbench.py` avec
`sweeps/fixtures/RailMagicOpcodeProbe` copie les deux calculs effectivement
modifiés (`score` + `OpexTopK`, K=20) sans toucher à l'IA de production. Il
mesure les opcodes Squirrel consommés d'après les ticks et le reliquat
`AIController.GetOpsTillSuspend`, à charge identique sur chaque pool. Les
comparaisons A/A `OFFA/OFFB` sont stables à **un opcode près**, et les
signatures des classements vérifiées contre un oracle hôte. Les petits
franchissements de tick sont tracés ; aucun compteur de CPU VM *global*
n'est revendiqué.

| Cas | OFF, score+TOP20 (opcodes) | ROI pur | Profit/itérations |
|---|---:|---:|---:|
| 20 candidats mixtes | 3 661 | −3,60 % | −58,16 % |
| 64 candidats mixtes | 15 470 | **+12,85 %** | −77,85 % |
| 200 candidats mixtes | 33 559 | **+16,45 %** | −62,69 % |
| 687 candidats mixtes | 70 140 | −14,87 % | −44,90 % |
| 687 identiques permutés | 57 768 | −33,10 % | −24,67 % |
| 64 candidats ex æquo | 4 676 | −39,70 % | −32,85 % |

Valeurs OFF arrondies dans le tableau ; conserver le JSON brut du banc pour
les valeurs exactes, les coûts de `score` et `rank` séparés, les 96 mesures
individuelles et les signatures d'oracle. Les répétitions d'une même
configuration **ne sont pas des graines indépendantes**. Ne pas interpoler
ces six scénarios comme une estimation de l'effet opcode moyen en production.

**Mécanisme démontré :** le ROI pur économise des instructions dans la
formule mais peut provoquer plus de déplacements/comparaisons dans le TOP20.
Sur 687 candidats dans l'ordre initial : 2 496 comparaisons de classement
OFF contre 3 055 ROI (+22 %) et 1 319 ratio profit/itérations ; le même pool
permuté renverse partiellement les écarts. Le signe du gain de la formule
seule ne prédit donc pas le signe du coût **formule + classement**.

Les OP/OS du 40×5 `simple_opcode` étaient en baisse de 5,88 % sur les postes
instrumentés mais n'étaient pas à travail égal : moins de projets ont été
construits sur ON, ce qui contribue à la baisse. Les IG/OB/RB/OA/OM sont
également des diagnostics partiels, jamais un compteur exhaustif VM par IA.

## 3. Verdict, sûreté du code et prochaines actions

**Simple_opcode : rejet économique ferme**, même si le microbenchmark montre
un coût de classement inférieur pour les six profils. **Simple_roi : rejet
de qualification**, et non une régression économique démontrée : le 40×5
historique ne prouve pas la neutralité stricte et le coût d'opcodes n'a pas
de borne supérieure établie <+1 % sur les viviers représentatifs.

Les deux flags restent **0 dans toutes les difficultés** ; admission PAX/fret,
budgets A*, TOP64, AIR/ROAD/WATER, C80 et autres politiques inchangés dans
ce chantier. Aucun commit, push ou modification du code de production n'est
requis ou effectué. Après cette première décision de qualification,
une campagne supplémentaire 40×10 a été lancée sous un protocole distinct.
La première tentative n'a pas livré de résultat complet ; une seconde
tentative sur le même bundle a produit un fichier final, **non analysé**
à la clôture utilisateur. Aucun nouveau test ne doit être lancé.

Si une nouvelle proposition change le classement effectivement utile, elle
constituera une **nouvelle intervention** à évaluer, pas un changement du
verdict a posteriori. Pour les deux variantes testées, **décision : conserver
OFF**.
