# V307 1.10 — Nombre de lignes reçues par puits ferroviaire

21 octobre 2026 — mesure hors partie, **aucun nouveau banc**. Source :
`results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine`,
40 journaux `reference_seed*_r0.log`, dix ans chacun. Lecteur reproductible :
`python -X utf8 sweeps/diag_v307_sink_joins.py --per-seed` ; deux tests unitaires
synthetiques : `python -X utf8 -m unittest discover -s sweeps -p test_v307_sink_joins.py`.

## Reconstruction et limites de preuve

- `task_rail.nut` journalise `RAIL_ATTEMPT` (y compris `ok=0`) et `RAIL_BUILD`
  **seulement sur construction reussie**, avec `line`, `src`, `dst`, `cargo`,
  `join_end` et `shared_dest` (`ai/OpexAI/task_rail.nut:1182-1214`).
- On compte par graine et **gare de destination reconstruite**, pas par tentative.
  Une construction initiale `shared_dest=0` ouvre un puits ; une construction
  ulterieure `shared_dest=1,join_end=B` rejoint le puits deja enregistre pour
  `dst`. Une nouvelle gare independante au meme `dst` serait un autre puits.
  L'identifiant de station physique manque dans les logs : c'est un **proxy**
  pour les gares effectivement rejointes, pas un audit de gares sauvegardees.
- Les 40 journaux totalisent **1 889 tentatives**, dont **1 088 `ok=1`** et
  exactement **1 088 `RAIL_BUILD`**. On reconstruit **719 puits**. **18**
  premieres apparitions `shared_dest=1,join_end=B` n'ont pas de premiere
  destination construite dans le meme journal : elles constituent des puits
  a historique incomplet (la gare pouvait exister deja comme gare source).
  Aucune destination n'a deux creations independantes observees.
- La categorie d'industrie est inferee du **cargo livre**, selon les
  destinations standard d'OpenTTD : COAL = centrale, IORE = acierie,
  WOOD = scierie, OIL_ = raffinerie, GRAI/LVST/STEL = usine, GOOD/PASS =
  ville, VALU = banque. Le log ne porte pas l'identifiant d'industrie ;
  pour les villes, on ne compte que l'extremite `dst` et les jointures
  V178/V179, **pas** toutes les gares de passagers partagees autrement.
  Les 18 historiques incomplets et les gares pax sont donc a ne pas utiliser
  pour une decision d'investissement en quais sans preuve complementaire.

## Resultats sur 40 graines

La part est calculee **sur les puits** de chaque categorie, les categories
etant agregees sur les graines. `>=4` signifie quatre lignes ou davantage ;
le delai est mesure de la premiere a la deuxieme ligne recue **dans le journal**.

| Categorie de puits | Puits | 1 ligne | 2 lignes | 3 lignes | >=4 lignes | Delai median 1→2 (jours) |
|---|---:|---:|---:|---:|---:|---:|
| **Tous** | **719** | **64,5 % (464)** | **24,2 % (174)** | **8,2 % (59)** | **3,1 % (22)** | **66** |
| Acierie | 124 | 65,3 % (81) | 26,6 % (33) | 6,5 % (8) | 1,6 % (2) | 43 |
| Banque | 4 | 100 % (4) | 0 % | 0 % | 0 % | — |
| Centrale electrique | 132 | 51,5 % (68) | 31,1 % (41) | 13,6 % (18) | 3,8 % (5) | 384 |
| Raffinerie | 84 | 54,8 % (46) | 34,5 % (29) | 10,7 % (9) | 0 % | 60 |
| Scierie | 107 | 57,9 % (62) | 32,7 % (35) | 7,5 % (8) | 1,9 % (2) | 64 |
| Usine | 138 | 52,9 % (73) | 26,1 % (36) | 11,6 % (16) | 9,4 % (13) | 66 |
| Ville (marchandises) | 39 | 100 % (39) | 0 % | 0 % | 0 % | — |
| Ville (voyageurs) | 91 | 100 % (91) | 0 % | 0 % | 0 % | — |

Les comptes par graine, incluant les classes 1/2/3/>=4, sont reproduits
par la commande `--per-seed` du lecteur (la cle est `(bras, graine, dst)` et
les creations independantes demarrent un nouveau puits). La categorie est
conservee puits par puits ; il n'y a **aucune fusion inter-graines**.

## Decision pour V307 1.9

**Ne pas reserver systematiquement 3 ou 4 quais.** Plus de 88 % des puits
observes restent a une ou deux lignes ; seuls 11,3 % en recoivent au moins 3.

En revanche le seuil de rejet general **80 % de puits a une ligne** n'est
pas rempli : sur les industries de fret frequentes la part a une ligne est
seulement de **51 a 65 %**. Le meilleur candidat a un essai ulterieur est
**2 quais sur les puits fret a demande multi-source**, specialement centrales,
usines, raffineries, scieries ; le surcout initial, l'entretien des quais
vides et la possibilite d'enclavement par la premiere voie restent a mesurer.
Pour les acieries, envisager le meme N=2 seulement sous condition de plusieurs
sources captees. Pour les banques et les destinations de ville, **pas de quai
reserve** sur ces chiffres incomplets. N=3 ou 4 ne se justifierait que par
une prediction de plusieurs affluents et une validation de geometrie, jamais
par la seule frequence de destinations.

Ce diagnostic n'est ni une mesure du nombre de quais effectivement poses,
ni une preuve que les quais reserves accroitraient le profit : attendre le
diagnostic V307 1.7 d'enclavement et un smoke cout/opcodes de V307 1.9.

## ⚠️ Correction du 21/10 au soir (Claude, remarque de l'utilisateur) : la mesure est censurée

Le tableau ne compte que les **jonctions réussies**. Une destination déjà desservie ne reçoit une
deuxième ligne que par jonction stricte V178 : un quai **parallèle** de même longueur, à 1-4 tuiles de
côté (`OpexJoinPlatformPlans`, `JOIN_PARALLEL_MAX_SIDE = 4`), plat, constructible, avec sa tuile
d'entrée libre. Sinon, la tentative échoue en `SITEAB`, sans repli vers une gare séparée
(`strictOriginReuseJoin`). Nos gares sont toutes posées à **1 quai**. La part de puits « à une ligne »
mesure donc aussi l'impossibilité de joindre, pas seulement l'absence de demande.

Journaux 10 ans du VPS, bras référence, `RAIL_ATTEMPT shared_dest=1` :

| Campagne | Tentatives de jonction | OK | SITEAB | ABND | Puits visés | Jamais joints |
|---|---:|---:|---:|---:|---:|---:|
| `v299_diag_3x10_20261021` | 74 | 23 (31 %) | 21 | 26 | 24 (pour 38 lignes neuves) | 9 |
| `v307_autopsy_3x10_20261021` | 40 | 25 (62 %) | 12 | 3 | 19 (pour 50 lignes neuves) | 1 |

Les `SITEAB` de jonction se répartissent selon le nombre de jonctions déjà réussies sur le puits :
- 0 (pas de place pour le 2e quai) : 6 + 4 ;
- 1 (pas de place pour le 3e quai) : 14 + 3 ;
- 2 ou plus : 1 + 5.

On compte 13 + 9 paires distinctes. Entre 38 % et 63 % des puits attirent au moins une tentative de deuxième ligne. La règle « 88 % des puits restent à 1-2 lignes » ne doit donc pas servir à écarter les gares de puits à plusieurs quais. Suite : prompt 5 de [`prompts/lot_21102026_soir.md`](prompts/lot_21102026_soir.md) (emprise réservée et mesure de la censure sur le 40×10 du PC).
