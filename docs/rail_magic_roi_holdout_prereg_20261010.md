# P0 RAIL — pré-enregistrement prospectif du ROI pur (10/10/2026)

**CLÔTURÉ le 11 octobre 2026 :** décision utilisateur de **REJETER
DÉFINITIVEMENT les deux variantes** (`simple_roi` et `simple_opcode`).
Ce pré-enregistrement est archivé, **non actif** ; aucun essai ou prolongation.
Le fichier final `r2` est présent, non analysé après clôture.

**État historique du protocole avant clôture :** la campagne `r1`
du 40×10 a été lancée mais n'a produit aucun résultat final ; l'attribution
de cet échec à un arrêt volontaire demandé par l'utilisateur n'est pas
étayée. La nouvelle exécution `r2` conserve les graines et le bundle `r1`.
Le protocole bilatéral strict de
`docs/rail_magic_roi_strict_40x10_prereg_20261010.md` prend le pas sur les
critères unilatéraux exploratoires décrits ci-dessous. Le présent document
reste l'enregistrement de la sélection initiale de graines.

Statut lors du pré-enregistrement initial : **aucun nouveau 40×10 lancé**.
Cette feuille complète le plan exploratoire
`docs/rail_magic_qualification_plan_20261010.md` avec le **contrat utilisateur
plus récent** de `docs/experimental_acceptance_policy_20261010.md` :
non-infériorité économique **unilatérale 95 %**, seuil −1 % sur profit et
valeur de compagnie ; **surcoût marginal opcodes <+1 %** à charge égale.
Elle ne modifie **pas rétroactivement** la décision de l'ancien 40×5.

## Déclencheur

Le 40×5 historique `simple_roi` n'a pas démontré l'équivalence stricte ±1 %, mais
un retraitement **exploratoire** à seuil unilatéral −1 % passe (profit et
company_value). Ne lancer ce holdout que si le microbench VM détaché valide le
coût de score+TOP20, avec garde de non-perturbation, ou si la mesure intrinsic
échoue et l'on renonce explicitement à adopter le résultat économique seul.
`simple_opcode` reste rejeté économiquement et n'est pas retesté.

Réanalyse reproductible côté hôte (20 000 rééchantillonnages appariés,
bootstrap `random.Random(0)` par indice, ratio de moyennes recalculé à chaque
tirage ; `sweeps/rail_roi_decision_power.py`) : sur le ROI pur historique,
**borne inférieure unilatérale 95 % profit −0,411126 % et valeur −0,638229 %**.
Ces bornes franchiraient le futur seuil de −1 % mais **restent exploratoires** :
le protocole historique d'équivalence bilatérale a échoué et l'horizon de
confirmation à dix ans n'a pas encore été évalué.

## Jeu confirmatoire indépendant et régime fixe

- 40 graines **nouvelles** ; 1970–1979 (10 ans), une répétition, OFF/ON sur le
  même bundle et la même image Docker, adversaire AAAHogEx constant.
- Paramètres : OFF `OpexAI[rail_magic_simple_roi=0,rail_magic_simple_opcode=0]` ;
  ON `OpexAI[rail_magic_simple_roi=1,rail_magic_simple_opcode=0]`.
  Toutes les autres expériences sont au même réglage des deux côtés, comme
  configurées dans le bundle. Pas de sondes `decision_log` ni de debug intrusif.
- Sélection déterministe le 10/10/2026, **avant le résultat**, par
  `System.Random(20261010).Next(1,1000000)` sous PowerShell/.NET en excluant
  les 40 graines du `results/rail_magic_simple_roi_A40x5_20261010_r1.json`
  et les doublons, jusqu'à 40 distinctes. Ordre enregistré :

```
241283 362504 432969 909182 294279 759058 136434 144455
281806 950544 885833 648244 410594 682528 953281 155378
186126 560786 45679 309017 120531 130502 196770 387114
440715 933128 462993 755117 820912 802040 102192 710265
2484 142113 226649 751224 606161 746501 983013 810908
```

- Une campagne Docker seulement, max 10 CPU/10 workers, mémoire cohérente
  avec le 40×10, aucune suppression/modification du travail concurrent.
- Le `gain_short` du harnais, si employé pour produire ce 40×10, est **une
  autre règle** : son verdict ne décide **pas** la non-infériorité. Le
  `non_erosion` historique ne convient pas davantage : il ne rejette qu'une
  perte avec borne haute CI sous zéro. Décision exclusivement **hôte** à partir
  des 40 `policy_comparison.per_pair` et des états sains.

## Calcul et arrêt définitifs

- Métriques primaires/gardes : `profit_year` terminal Opex et `company_value`.
  Pour chaque graine, stocker `ref`, `ON`, `delta`. Pour chaque métrique,
  bootstrap par **graine appariée**, 20 000 rééchantillonnages de 40 indices
  avec remise, graine bootstrap **0**. Pour chaque tirage, recalculer
  `100*sum(ON−OFF)/sum(OFF)` ; la borne 5e percentile est la borne
  inférieure **unilatérale à 95 %**. Exiger les deux bornes **strictement >−1 %**.
- Pour opcodes, mesure Squirrel sur **mêmes entrées et nombre d'appels** :
  upper unilatérale95 du surcoût `(ON−OFF)/OFF < +1 %`, A/A sain.
  Les compteurs OP/OS réels du jeu sont publiés avec couverture mais ne sont
  **pas** la mesure causale du score ni du CPU VM total.
- Santé obligatoire 80/80 parties et toutes les 40 paires complètes ; tout
  manque => **non qualifié donc OFF**, pas zéro rempli à la place.
- Réexaminer RAIL/AIR et les pires graines. Un effet secondaire destructeur
  avéré (Save/Load, crash, altération du portefeuille de production) empêche
  adoption malgré les statistiques.
- **Décision au seul point final (N=40)** : si les deux non-infériorités
  passent, opcode marginal passe et tous contrôles sains, **adoption
  candidate** ; sinon **rejet de l'adoption** et maintien des flags OFF.
  Un échec de non-infériorité ne veut **pas** dire perte économique prouvée :
  si IC recouvre −1 %, statut d'effet « indéterminé », rejet *pour preuve
  insuffisante*, distinction explicite dans le rapport.
- Pas de sélection de nouvelles graines après examen, pas de `40×10` additionnel
  opportuniste, pas de reclassification au seul Wilcoxon p>0,05. Une étude
  supplémentaire éventuelle serait un **nouveau mandat/protocole**.

Le microbench est une qualification d'opcodes **intrinsèques** ; la preuve de
neutralité **VM totale** exige un compteur exhaustif moteur/VM qui n'existe
pas dans le JSONL et qui doit rester marquée « indéterminée » si indisponible.
