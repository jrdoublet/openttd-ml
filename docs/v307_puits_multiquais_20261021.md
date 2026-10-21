# V307 1.9b — censure des puits fret, étape 0 (21/10/2026)

**Mesure hors partie**, sur les 40 journaux du bras `reference` de
`results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine`.
Commande reproductible :

```powershell
python -X utf8 sweeps/diag_v307_sink_censure.py
python -X utf8 sweeps/diag_v307_sink_censure.py --json
```

Le script lit les `RAIL_ATTEMPT shared_dest=1 join_end=B` et les `RAIL_BUILD` ;
il ne lance aucune partie. Il identifie les puits par `(graine, dst)` et ne
compte comme puits initialement ouvert que ceux ayant une première construction
`shared_dest=0`. Les 18 puits reconstruits auparavant dans le rapport 1.10
sans première construction observable sont écartés du dénominateur. L'absence
d'identifiant physique de gare impose cette approximation.

## Demande observée, tentatives et censure

| Mesure | Valeur |
|---|---:|
| Journaux référence, dix ans | 40 |
| Puits initialement ouverts et observés | **701** |
| Puits ayant fait l'objet d'au moins une tentative de nouvelle jonction | **306 / 701 = 43,7 %** |
| Puits ayant reçu plusieurs lignes | **248 / 701 = 35,4 %** |
| Puits visés, mais jamais rejoints | **58 / 306 = 19,0 %** |
| Destinations de tentatives sans première construction observée | 26 |
| Tentatives `shared_dest=1`, total | **986** |
| `OK` | 387 (39,2 %) |
| `SITEAB` | **491 (49,8 %)** |
| `ABND` | 69 (7,0 %) |
| `SITEA` / `TRKFAIL` / `STNFAIL` | 12 / 20 / 7 |

**La demande révélée est supérieure au nombre de puits effectivement
rejoints.** L'indicateur précédent « 64,5 % de puits à une ligne » mélange
les puits sans tentative et ceux dont la tentative échoue. La demande
observée (43,7 %) reste une borne inférieure de la demande potentielle :
les projets jamais proposés ou jamais tentés n'apparaissent pas dans le journal.
Cette correction ne prouve pas qu'un quai supplémentaire convertirait chacune
des tentatives en nouvelle ligne : les sites ou les voies peuvent aussi être
physiquement impraticables.

Les `SITEAB` sont décomposés d'après les **jonctions réussies précédemment sur
la même destination**, au moment de l'échec :

| Jonctions précédentes | `SITEAB` |
|---:|---:|
| 0 (tentative de deuxième ligne) | **244** |
| 1 (troisième ligne) | 110 |
| 2 | 58 |
| 3 | 18 |
| 4 | 58 |
| 5 | 3 |

Les 69 `ABND` ont toutes `iters=5000` (médiane = p90 = maximum = 5 000),
ce qui indique ici l'épuisement du budget de recherche enregistré. **Le côté
disponible pour un quai parallèle est impossible à reconstruire** : ni la
géométrie de la voie initiale ni le sens `left/right` des emprises candidates
ne figurent dans ces `RAIL_ATTEMPT`. Les champs `startx`/`endx` sont des codes
de statut (0 ou −1), pas les coordonnées du quai.

## Par catégorie de destination

Le dénominateur est la première ouverture observée (701 puits), par catégorie
inférée du cargo livré ; la proportion « multi » porte sur les constructions
réussies, comme le tableau 1.10, mais sur une population explicitement
restreinte aux puits dont l'ouverture est connue.

| Catégorie | Puits ouverts | Au moins une tentative de nouvelle ligne | Tentés, jamais joints | Plusieurs lignes effectivement reçues |
|---|---:|---:|---:|---:|
| Aciérie | 121 | 51 (42,1 %) | 9 | 42 (34,7 %) |
| Centrale électrique | 131 | 78 (59,5 %) | 14 | 64 (48,9 %) |
| Raffinerie | 80 | 40 (50,0 %) | 6 | 34 (42,5 %) |
| Scierie | 103 | 52 (50,5 %) | 7 | 45 (43,7 %) |
| Usine | 132 | 85 (64,4 %) | 22 | 63 (47,7 %) |
| Banque | 4 | 0 | 0 | 0 |
| Ville, marchandises | 39 | 0 | 0 | 0 |
| Ville, voyageurs | 91 | 0 | 0 | 0 |

Les industries de fret montrent de **42 à 64 % de puits sollicités**. Les
usines et les centrales sont les plus exposées aux tentatives : 85/132 et
78/131. Les 0 des catégories ville/banque ne décrivent que les tentatives
`shared_dest=1 join_end=B`, pas l'intégralité des autres formes de connexion.

## Suite à tester (étape 1 du prompt 5)

Le signal justifie de tester les deux options enregistrées dans
[`lot_21102026_soir.md`](prompts/lot_21102026_soir.md) : réserver l'emprise
d'un second quai parallèle sans surcoût initial (bit 1), ou construire d'emblée
deux quais dans les destinations fret à plusieurs sources (bit 2). Mesurer
pour chaque option les jonctions réussies, `SITEAB`/`ABND`, les lignes neuves,
le coût et les opcodes en conditions identiques. Aucune qualification
économique ni changement de défaut n'est tiré de cette étape 0.
