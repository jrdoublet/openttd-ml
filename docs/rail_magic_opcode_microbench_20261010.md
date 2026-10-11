# P0 RAIL — microbench Squirrel détaché score + TOP20 (10 octobre 2026)

## Objet et isolement

Qualifier le **coût intrinsèque du calcul du score RAIL et du TOP20 local**
à charge *strictement identique*, pour les trois scores :

- **OFF** : `opcodeRatio + adjustedRoi * 15`, bonus de rotation historiques.
- **simple_roi** : `effectiveRoi`.
- **simple_opcode** : `opcodeRatio` (profit annuel / itérations A* prévues,
  **pas** un compteur d'opcodes VM).

Le code de production `ai/OpexAI/` n'a subi aucune modification. Le moteur
OpenTTD 15.3 a chargé **une IA NoAI de test autonome**, dans
`sweeps/fixtures/RailMagicOpcodeProbe/`. Le lanceur est
`sweeps/rail_magic_opcode_microbench.py`, et les contrôles indépendants sont
dans `tests/test_rail_magic_opcode_microbench.py`.

Les pools sont **synthétiques** et déterministes : `mixed20`, `mixed64`,
`mixed200`, `mixed687`, les **mêmes 687 candidats en ordre permuté**
`shuffle687`, et `ties64` (64 scores entièrement ex æquo).
Ce ne sont pas des tirages représentatifs des pools réels en production.
Le banc reproduit les divisions entières des trois formules et le TOP20
historique `OpexTopK(k=20)`. Quatre répétitions par pool, chacune avec
`OFFA` et `OFFB` entourant, en alternance, les variantes ROI et OPCODE.
Chaque bras reprend **exactement les mêmes candidats dans le même ordre**.

Les mesures d'opcodes sont réalisées directement sous NoAI/Squirrel par
`GetTick()` et `GetOpsTillSuspend()` selon `OpexOpsMeasureEnd` ; les
marqueurs encadrent **séparément** le calcul des scores et le TOP20.
Les journaux `AILog.Info`, les vérifications de sommes et la fabrication du
pool ne sont pas dans les blocs chronométrés. Le `Sleep` final est hors mesure.
Cette méthode rapporte les coûts des blocs du moteur **mais pas les opcodes VM
totaux d'une partie**, et compte 10 000 unités par tick traversé : un bloc qui
attendrait une commande produirait une surestimation. Les blocs de ce test ne
lancent ni commande de construction ni `Sleep`.

## Exécution et intégrité

- Précontrôle `docker ps` **vide** ; aucune campagne concurrente lancée.
- Exécution d'un seul microbench bref, au plus **2 CPU**, 2 Go, OpenTTD 15.3
  via le cache OpenTTDLab et `-d script=4`. Aucune campagne économique longue.
- `96/96` résultats (6 cas × 4 répétitions × 4 bras), marqueur `RMOP_DONE`
  présent, sorties Squirrel **identiques à l'oracle indépendant Python**
  pour les scores agrégés, la signature TOP20 et le nombre de candidats
  sélectionnés, sans duplication ni résultat manquant.
- Contrôle **A/A OFFA contre OFFB** : mêmes scores et mêmes TOP20 sur tous
  les cas et répétitions. La mesure instrumentée diffère au maximum de
  **1 opcode** entre OFFA et OFFB (et exactement zéro pour `ties64`).
  En conséquence `a_a_exact_all_cases=false` au sens de l'égalité stricte
  d'opcodes, mais `a_a_within_one_opcode_all_cases=true` et les résultats
  fonctionnels sont strictement identiques. Ces ±1 sont compatibles avec le
  coût et le placement des lectures de l'horloge ; la cause précise du
  dernier opcode n'est pas isolée. Ce résidu minime ne doit pas être
  interprété comme un signal de performance.
- Vérifications hôte : **5/5 tests réussis**, dont parité statique des
  formules/TopK avec `ai/OpexAI/candidates.nut`, frontières de bonus,
  troncatures, égalités, erreurs de parsing et A/A.

**Preuve sérialisée** : `results/rail_magic_opcode_microbench_20261010.json`
(30 719 octets), SHA256
`98bc6d768b22cedd4567e5f0470b19afb36c799ebbe36316255df4953f723aa3`.
Les valeurs suivantes sont les moyennes de quatre répétitions NoAI par cas,
la référence OFF étant la moyenne de OFFA et OFFB à chaque répétition.

## Mesure réelle NoAI : opcodes Squirrel par appel score + TOP20

| Pool fixe | OFF score | OFF TOP20 | OFF total | ROI score | ROI TOP20 | ROI total (Δ total) | OPCODE score | OPCODE TOP20 | OPCODE total (Δ total) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mixed20 | 1 064 | 2 597,25 | 3 661,25 | 535 | 2 994,5 | 3 529,5 (**−3,60 %**) | 635 | 897 | 1 532 (**−58,16 %**) |
| mixed64 | 3 368,38 | 12 101,25 | 15 469,62 | 1 679 | 15 777,75 | 17 456,75 (**+12,85 %**) | 1 999,5 | 1 427 | 3 426,5 (**−77,85 %**) |
| mixed200 | 10 519 | 23 040,25 | 33 559,25 | 5 215,5 | 33 863 | 39 078,5 (**+16,45 %**) | 6 215,5 | 6 306 | 12 521,5 (**−62,69 %**) |
| mixed687 | 36 110,62 | 34 029,25 | 70 139,88 | 17 879 | 41 833 | 59 712 (**−14,87 %**) | 21 314,25 | 17 334,75 | 38 649 (**−44,90 %**) |
| shuffle687 | 36 110,62 | 21 657,12 | 57 767,75 | 17 878,75 | 20 768 | 38 646,75 (**−33,10 %**) | 21 314 | 22 203 | 43 517 (**−24,67 %**) |
| ties64 | 3 535 | 1 141,25 | 4 676,25 | 1 679 | 1 141 | 2 820 (**−39,70 %**) | 1 999 | 1 141 | 3 140 (**−32,85 %**) |

À charge identique, les deux simplifications réduisent le coût du **calcul
du score** dans chacun des six cas ; mais modifier les scores change
le nombre de comparaisons, insertions et déplacements du TOP20.
Ainsi, pour `mixed200`, le TOP20 passe de 23 040 à **33 863**
opcodes sous ROI (+46,97 %), ce qui dépasse les économies de score
et produit un **surcoût total +16,45 %**. Sur `mixed687`, ROI augmente
le TOP20 de +22,93 %, mais économise assez de score pour réduire
le total de 14,87 %.

La permutation des **mêmes** 687 lignes suffit à inverser des conclusions
sur le classement seul : `mixed687` TOP20 OPCODE −49,06 % et ROI
+22,93 %, contre `shuffle687` OPCODE +2,52 % et ROI −4,11 %.
Cette dépendance à l'ordre interdit de convertir les six profils
en un « coût global moyen par partie » ou en IC95 par graine.
Quatre répétitions d'un pool unique ne sont pas quatre échantillons
indépendants d'une distribution de cartes ou de parties.

## Verdicts et portée de l'adoption

**`simple_roi` : REJET pour adoption par défaut.**
Le 40×5 économique déjà terminé n'avait **pas** établi l'équivalence
±1 % (Δprofit moyen +48 985 £/an, IC95 [−18 743 ; +118 178], référence
1 939 557 £/an). Le microbench démontre en outre un **risque concret**
de surcoût de +12,85 % et +16,45 % sur des charges appariées ;
sur d'autres charges il est moins cher. Impossible de prouver une
borne supérieure 95 % de surcoût global inférieure à +1 % avec
ces pools synthétiques. On ne classe donc pas les opcodes globaux
comme « négatifs prouvés pour toutes les parties », ni comme « neutres ».
Verdict coût intrinsèque **dépend du pool / indéterminé en population** ;
verdict qualification **FAIL (non-adoption)**.

**`simple_opcode` : REJET économique malgré le gain intrinsèque
dans les six pools.** Le 40×5 économique montre Δprofit moyen
**−88 104 £/an**, IC95 [−172 423 ; −6 074], valeur compagnie
**−4,685 %** et −5,75 avions en moyenne. Les résultats moteur confirment
des **économies locales score+TOP20 dans 6/6 pools** (−24,67 % à
−77,85 %), mais ne démontrent ni neutralité économique ni gain
d'opcodes **VM global par partie**. Un calcul moins cher pouvant
modifier le calendrier de l'IA ne peut être adopté malgré la
dégradation observée.

**Décision commune : aucun des deux flags ON par défaut, aucune
campagne 40×10 ou 20×10 de qualification supplémentaire à ce stade,
aucun commit ni push.** Les verdicts ne confondent pas coûts
intrinsèques à charge égale, postes `OP/OS` cumulés après divergence
et opcodes VM totaux. L'absence d'un compteur moteur total et d'une
distribution réelle de pools empêche d'affirmer un gain total VM.

## Commandes vérifiables

À la racine du dépôt, sur hôte :

```powershell
python -m unittest discover -s tests -p test_rail_magic_opcode_microbench.py -v
python sweeps/rail_magic_opcode_microbench.py --offline
```

Seulement lorsque Docker est **libre**, sous coordination (syntaxe
PowerShell : utiliser `${PWD}`, non `"$PWD":/work` qui produit
`docker: invalid reference format`) :

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}"
docker run --rm --cpus=2 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python sweeps/rail_magic_opcode_microbench.py --engine --out /work/results/rail_magic_opcode_microbench_20261010.json
```

Ce banc est un **diagnostic de coût local**, et non un nouveau jeu de
performance économique : il ne construit aucun projet et ne modifie
aucun fichier de production.
