# P0 AIR — Réplication 40×5 sur graines inédites (10/10/2026)

**Verdict : fail_primary, non-adoption.** L'essai reste révoqué dans le
code courant. Aucun coefficient n'a été retiré du code livré.

## Comparaison strictement identique

À la demande de l'utilisateur, nouvelle campagne
`air_p0_direct_realization_holdout_40x5_20261010_r1` à **40 nouvelles
graines × 5 ans × deux bras**, 80 parties, OpenTTD 15.3, 10 CPU / 10
workers et télémétrie des lignes AIR annuelle.

La campagne a **réutilisé sans copie ni modification le bundle figé
originel** `061096c0b5b7cb90cbb8b0a1a162950e97209188c8783b8dc3ee7287e291c5a6`
de `air_p0_direct_realization_gateA_40x5_20261010_r1`, avec le
même harnais, les mêmes bibliothèques, la même image Docker
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
les mêmes paramètres (sauf les graines) et les deux politiques :
`OpexAI[air_p0_direct_realization=0]` référence,
`OpexAI[air_p0_direct_realization=1]` variante.
Le toggle ON n'a pas été réintroduit dans l'arbre courant : il n'existe
que dans le bundle original. Le nouveau manifeste, vérifié par le bootstrap
isolé, est `results/air_p0_direct_realization_holdout_40x5_20261010_r1.manifest.json`
(SHA-256 `def952a0f74a2755905492ac0a95d16243ed65a257f0d80bfae580d0aa1951b1`).

Les 40 graines ont été prédéterminées avec `random.Random(20261010)` :
tirages successifs `randrange(1,2**31)`, en rejetant les 40 graines
originales et les doublons ; **intersection 0/40**. Les graines exactes
figurent dans la section `configuration.seeds` du manifeste ; le
champ `replay_provenance` documente cette méthode. Aucun filtrage
sur les résultats obtenus.

Le protocole est le même : règle `gain_short`, métrique primaire
`profit_year` terminal, gain minimal +4 %, Wilcoxon p<0,05,
IC95 bootstrap inférieur >0, garde de valeur compagnie -5 % ;
critères utilisateur supplémentaires de neutralité économique positive
et absence de surcoût opcode durable.

## Résultat économique

**80/80 parties terminées**, **40/40 paires valides** ;
`comparison_complete`, `adoption_sample_complete`,
`metric_coverage_complete` tous vrais. **`fail_primary`.**

| Métrique ON − OFF | Première campagne 40×5 | Holdout 40×5 |
|---|---:|---:|
| Profit annuel terminal moyen | −7 522,20 £/an | **−21 757,15 £/an** |
| Médiane | −3 241 £/an | **−2 714 £/an** |
| Victoires / défaites / égalités | 18 / 22 / 0 | **20 / 20 / 0** |
| Wilcoxon bilatéral | p=0,878507 | **p=0,397424** |
| IC95 bootstrap de la moyenne | [−48 340,275 ; +32 905,85] | **[−66 194,9 ; +23 587,175] £/an** |
| Valeur de compagnie, ratio des moyennes | −0,394318 % | **−0,608767 %** |

Seuil de gain +4 % dans le holdout : **+78 334,531 £/an** ;
le gain moyen est négatif. Une absence de significativité n'établit
**pas** une équivalence économique. Le verdict ne change donc pas.

Évolution du delta moyen de profit annuel par année :

| Année | Écart moyen ON − OFF (£/an) |
|---|---:|
| 1970 | 0 |
| 1971 | 0 |
| 1972 | +37,725 |
| 1973 | −8 750,75 |
| 1974 | −21 757,15 |

En 1974, la télémétrie annuelle des lignes AIR donne un delta moyen
du profit cumulé AIR de **−11 664,04 £**, pour **47,375 lignes AIR
OFF contre 47,65 ON** ; ce n'est pas un isolat causal de recettes.

En cumulant **à titre exploratoire seulement** les deux échantillons
disjoints, 80 graines ont un delta terminal moyen de
**−14 639,675 £/an**, médiane −3 241 £/an, 38 victoires,
42 défaites, 0 égalité. Ce cumul n'est pas une nouvelle porte
statistique préenregistrée.

## Coût d'opcodes

Les compteurs SIGN existants du harnais ne couvrent **pas tout le CPU
de l'IA**, ni toutes les constructions AIR. Les parcours et projets
effectivement choisis changent : comparer des sommes de postes ne
mesure pas un surcoût marginal de la formule.

| Compteurs observés | Première campagne | Holdout |
|---|---:|---:|
| OFF, moyenne par partie | 42 957 846,95 | 47 753 303,30 |
| ON, moyenne par partie | 46 414 785,425 | 46 885 836,825 |
| Delta ON − OFF | **+3 456 938,475 (+8,05 %)** | **−867 466,475 (−1,82 %)** |

Pour le holdout, répartition des deltas moyens :
**RAIL tentatives −941 694,8**, sélection −147 775,
planification AIR **+41 059,95**, planification ROAD +158 165,025,
construction ROAD +44 310,1, WATER −21 531,75 opcodes par graine.
Les appels de planification AIR passent de 56,625 OFF à 57,7 ON ;
les tentatives RAIL de 5,725 OFF à 5,4 ON. Seulement **une**
graine a le même nombre d'appels dans tous les postes observés.
Ces changements de charge interdisent d'attribuer les différences
globales d'opcodes au remplacement du lissage 75/25.

Le premier 40×5 voyait +8,05 % et le second −1,82 %
**sur les postes partiels**, ce qui confirme la dépendance aux
trajectoires plutôt qu'un effet CPU structurel démontré. La
neutralité totale des opcodes demeure **non établie**.

## Preuves et état du dépôt

- `results/air_p0_direct_realization_holdout_40x5_20261010_r1.json` :
  80 parties, 40 comparaisons appariées, statistiques et verdict.
- `results/air_p0_direct_realization_holdout_40x5_20261010_r1.jsonl` :
  checkpoints des parties.
- `results/air_p0_direct_realization_holdout_40x5_20261010_r1.manifest.json` :
  graines, politiques, SHA du bundle, runtime, provenance de réplication.
- `results/air_p0_direct_realization_holdout_40x5_20261010_r1_annual.csv` :
  200 deltas annuels appariés avec télémétrie AIR.
- `results/air_p0_direct_realization_holdout_40x5_20261010_r1_opcodes.csv` :
  40 comparaisons des compteurs partiels et appels par poste.
- `results/air_p0_direct_realization_holdout_40x5_20261010_r1_analysis.json` :
  agrégats et cumuls exploratoires.
- `results/analyze_air_p0_holdout.py` : extraction reproductible des
  CSV et des agrégats à partir du JSON de campagne et des checkpoints.

**Décision inchangée** : ne pas adopter ce remplacement du lissage
75/25 par la moyenne directe sans preuve d'amélioration ou de
neutralité économique **et** en opcodes. Aucun edit Squirrel, aucun
commit ou push lors de la réplication.
