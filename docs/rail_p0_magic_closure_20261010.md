# P0 RAIL — clôture des « nombres magiques », admission / TOP20 / A*

**Clôture utilisateur du 11 octobre 2026 :** les deux variantes
`simple_opcode` et `simple_roi` sont **REJETÉES DÉFINITIVEMENT**, sans
nouvelle qualification. Leurs flags étaient OFF dans les campagnes et leurs
branches sont désormais archivées hors du code actif. Les paragraphes de
qualification prospective ci-dessous sont archivés, non des actions ouvertes.

**Date : 10 octobre 2026.** Sources :
`docs/rail_magic_filter_p0_20261009.md`,
`docs/rail_magic_neutralite_20261010.md`,
`docs/rail_magic_simple_roi_gate_20261010.md`,
`docs/rail_magic_simple_opcode_gate_20261010.md`,
`docs/rail_magic_opcode_microbench_20261010.md`,
`docs/rail_magic_roi_strict_40x10_prereg_20261010.md`.
Les anciennes expériences ont des **bundles distincts** du HEAD local très
modifié par des chantiers AIR/Capital parallèles. Ne pas agréger leurs bras
entre campagnes. Les décisions de rejet d'adoption ne doivent pas être
rapportées comme des preuves de pertes statistiques systématiques.

## Méthode et séparation des coûts

1. **Coût intrinsèque du score + TOP20** : mesure Squirrel NoAI
   `GetOpsTillSuspend` sur 6 viviers synthétiques *appariés* entre OFF/ON,
   96 mesures et oracle/A-A validés (max 1 opcode d'écart OFFA/OFFB).
   Un changement de score peut rendre `OpexTopK` plus ou moins cher.
2. **Coût du portefeuille intermodal** : la création de projets vient des
   **candidats `rail.candidates` complets** et du sélecteur commun TOP64,
   où comptent profit C70, capital finançable, `K_dec` C69 et priorités
   C77/C118/C120. Au défaut, `rail.best`/TOP20 n'est consommé par un
   constructeur que lorsque C80 stock (OFF) ou origin-reuse (OFF) l'activent.
   Un déplacement dans le TOP20 local n'est donc pas une preuve d'éviction
   AIR dans le portefeuille.
3. **Opcodes VM totaux / effets économiques** : les panneaux OP/OS/BT,
   IG/OB/RB/OA/OM et `observed_opcodes_total` couvrent des postes variables
   et parfois incomplets. Des décisions AIR/RAIL et des trajets différents
   modifient la charge de simulation ; un écart dans les compteurs partiels
   *n'est pas* le surcoût causal du score. Les itérations A* prédites et les
   devis `×3105 + transaction` ne sont pas des opcodes moteur observés.

Le microbenchmark du ROI pur a mesuré **+12,85 %** (`mixed64`) et
**+16,45 %** (`mixed200`) d'opcodes **locaux complets score+TOP20** dans deux
états synthétiques, tandis que quatre autres ont vu une baisse de −3,60 %
à −39,70 %. Cela **réfute une neutralité universelle pour toutes les
entrées**, mais ne prouve **pas une régression structurelle globale** de la
population de vrais viviers. Une ancienne observation C41 de 3568 profils
RAIL (autre bundle/sonde) a un nombre médian de 90–92 candidats,
maximal de 196–197 ; le TOP20 ne représente alors que 0,42 à 0,63 % du coût
de génération selon le bras. Cette observation n'est **pas** une mesure
appariée des parties ROI actuelles et ne permet pas de qualifier la borne
supérieure U95 +1 % exigée. Comme les surcoûts synthétiques ne suffisent
pas à eux seuls à un rejet **structurel universel**, un nouvel essai
économique prospectif a été demandé, distinct de la garde opcode.

## Admission 500/200, bonus rotation et portée réelle

`ai/OpexAI/candidates.nut` calcule `opcodeRatio = profitAnnual×1000 /
predictedIterations` : ses unités sont une prévision de £/an pour 1000
itérations A*, **pas** des opcodes VM. Avec `policy_portfolio=1` au défaut,
`VIVIER_RATIO_FILTER` supprime les positifs sous **500** en PAX et **200**
en fret avant le portefeuille. Ces seuils ne sont pas un coût d'opportunité
observé de l'algorithme. Les candidats à profit non positif sont déjà
écartés, avec l'exception documentée `PAX_NEAR`.

Le bonus de rotation 130/115/100/60 % suivant 12/25/45 jours et le
`roi×15` forment le score TOP20 composite historique. Ils changent la
**priorité locale** et non le `profitAnnual` / `roi` économique physique.
Sonde `RAIL_MAGIC_SHADOW` sur 15 snapshots complets/14 graine-années :
**796 visites de rejets**, toutes PAX (0 fret), 746 finançables sur devis,
profit prévu cumulatif 1 050 723 £/an **non additif** (doublons OD),
**0 des 571 comparables** ne domine le meilleur AIR coté tier C77=0 ;
175 visites avec AIR prioritaire et 50 sans cote AIR restent inconnues.
Retirer la rotation déplace **5 visites du TOP20**, recoter sur des grandeurs
financières en déplace 104 ; aucune domination financière et
**constructibilité effective** des projets supplémentaires n'est prouvée.
La sonde est elle-même intrusive : shadow ON/OFF 5×6, −89 693 £/an moyen
et −3,65 % de valeur, différences de trajectoire **non attribuables** à
une politique qui construirait ces rejets ; elle peut modifier en place
`candidate.fundScore` durant le contrefactuel. Conserver la sonde OFF.

## Expériences déjà terminées, verdicts par proposition

**Légende :** Éco = profit annuel en fin de partie et valeur de compagnie ;
**positif/neutre/négatif** exige un IC apparié permettant de qualifier
l'effet selon des marges annoncées *avant* résultat. Les autres écarts de
moyenne ne deviennent pas des gains ou pertes prouvés. Les opcodes « locaux »
décrivent uniquement le banc score+TOP20, jamais la VM totale.

| Proposition | Données économiques (ON−OFF) | Qualification économique | Qualification opcodes | Décision |
|---|---|---|---|---|
| `RAIL_MAGIC_SHADOW=1` | Diagnostic 5×6 : −89 693 £/an, valeur −3,65 %, sonde intrusive | **INDÉTERMINÉ** (aucun traitement économique causal) | **INDÉTERMINÉ**, surcoût de la sonde non isolé | **REJETER** (ON productif) |
| `RAIL_MAGIC_ADMISSION_ONLY=1` | 40×3 : +8 256 £/an ; IC95 [−54 163;+71 922], valeur +0,412 % | **INDÉTERMINÉ** | **INDÉTERMINÉ**, plus de candidats/devis possibles | **REJETER** |
| `RAIL_ECONOMIC_PRESELECT=1` (admission + TOP20 financier + plancher A*) | 40×3 : −31 949 £/an ; IC95 [−107 724;+44 992], valeur −1,345 % | **INDÉTERMINÉ** | **INDÉTERMINÉ**, sondes OB incomplètes | **REJETER** |
| `RAIL_MAGIC_ASTAR_ONLY=1` | 40×3 : −864 £/an ; IC95 [−2 560;+77], 37 égalités/40, valeur −0,010 % | **INDÉTERMINÉ** (pas d'IC d'équivalence préalable complet) | **INDÉTERMINÉ**, travail A* partiellement vu | **REJETER** |
| `RAIL_MAGIC_RANK_ONLY=1` | Aucun A/B, TOP20 sans consommateur métier au défaut | **INDÉTERMINÉ** | **INDÉTERMINÉ** (recotation additionnelle non isolée) | **REJETER** l'adoption |
| Supprimer `VIVIER_RATIO_FILTER` / seuils PAX 500, fret 200 | Exposition shadow, ablation admission seule et lot combiné ; aucun gain utile qualifié, constructibilité non prouvée | **INDÉTERMINÉ** pour une suppression isolée | **INDÉTERMINÉ**, davantage de candidats possibles | **REJETER** la suppression, conserver historique |
| Supprimer le bonus rotation 12/25/45 j (130/115/100/60 %) | Contrefactuel TOP20 : 5 visites déplacées ; aucune domination intermodale effective démontrée | **INDÉTERMINÉ** | **INDÉTERMINÉ**, aucun coût propre isolé sur pools réels | **REJETER** la suppression non qualifiée |
| `simple_opcode=1` | 40×5 : −88 104 £/an ; IC95 [−172 423;−6 074], valeur −4,685 % | **NÉGATIF** | **POSITIF LOCAL** sur 6/6 profils Squirrel ; VM totale indéterminée | **REJETER DÉFINITIVEMENT** |
| `simple_roi=1` | 40×5 antérieur : +48 985 £/an ; IC95 [−18 743;+118 178], valeur +2,072 % | **INDÉTERMINÉ** pour neutralité stricte | **INDÉTERMINÉ** en population ; deux surcoûts locaux confirmés, VM totale inconnue | **REJETER DÉFINITIVEMENT** — utilisateur, 11/10 |

Les trois variantes avec A40×3 complet ont **80/80 parties et 40/40 paires
saines chacune**. Les règles `gain_short` initiales exigeaient un gain ≥4 %
du profit, borne basse du CI>0 et Wilcoxon<0,05. Toutes ont obtenu
`fail_primary` et n'ont donc pas de porte B ; cela justifie le **rejet de
l'adoption selon le protocole**, pas une régression prouvée. Les couvertures
des tentatives A* réelles sous sonde OB sont seulement 2/40 (lot),
6/40 (admission) et 10/40 (A* seul) : impossible de conclure sur le coût
VM global. Les pires graines de ces bras ont déjà été examinées dans
`docs/rail_magic_neutralite_20261010.md`, ne pas réexécuter les autopsies.

## Pas de nouvelle substitution arbitraire

Le portefeuille commun C69/C70 classe déjà avec des grandeurs financières
mesurables : profit annuel calibré, capital à financer, `K_dec` et priorités
structurées. Répliquer un tri local financier TOP20 qui **ne commande pas de
construction** ne résout pas un goulot métier et ajoute du calcul ; de plus
`OpexTopKFund` ignore une partie de `K_dec`. La base factuelle n'isole ni
une OD/cargo sous seuil réellement constructible qui évincerait un AIR
finançable, ni le coût marginal en opcodes d'une recherche supplémentaire.
**Aucune substitution nouvelle de 500/200, du bonus de rotation, de ROI×15
ou du plancher A* ne possède donc une hypothèse causale justifiant du code.**
Pas de nouveaux coefficients, ni A* N=2 / budget 40k sans preuve.

Les seuils et la formule historiques restent OFF/ON **exactement comme
avant** ; cela ne signifie pas qu'ils sont statistiquement optimaux.
Le cas `simple_opcode` est définitivement archivé avec son rejet dans
`docs/rail_magic_simple_opcode_gate_20261010.md` et jamais réactivé.

## ROI : ancien protocole prospectif, désormais clos

L'essai sur les 40 graines **inédites et pré-enregistrées** du document
`docs/rail_magic_roi_holdout_prereg_20261010.md` suit désormais le contrat
**strict à deux IC95 bilatéraux** défini AVANT son lancement :
`docs/rail_magic_roi_strict_40x10_prereg_20261010.md`. Le script hôte
`sweeps/rail_roi_strict_decision.py` classe profit annuel et valeur comme
POSITIF (CI entièrement au-dessus de +1 %), NEUTRE (CI entièrement dans ±1 %),
NÉGATIF (CI entièrement en dessous de −1 %), ou INDÉTERMINÉ.
Une non-infériorité −1 % ne suffit jamais à déclarer une neutralité.
La garde opcode +1 % à charge réelle identique et l'intégrité physique
restent des portes indépendantes, même si l'économie progresse.

**Décision : aucune analyse supplémentaire demandée.** Un fichier final
`r2` existait au contrôle de clôture mais n'a pas été interprété. Les deux
variantes sont rejetées et les protocoles prospectifs sont clos.

## Validation

Sous-ensemble hôte déjà vérifié : `test_rail_magic_economics` 4/4,
`test_rail_magic_simple_roi` 2/2,
`test_analyse_rail_magic_filter_p0` 1/1,
`test_rail_magic_opcode_microbench` 5/5,
`test_rail_roi_holdout_decision` 8/8,
`test_rail_roi_strict_decision` 6/6 (contrats sur données synthétiques).
Tous les flags expérimentaux restent à **0 par défaut** ; aucun code
de production, AIR/Capital, Docker concurrent, commit ou push modifié.
