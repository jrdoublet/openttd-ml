# DIST-BORNES-1 — chemins AIR et diagnostic des journaux

Lecture du 23 octobre 2026, branche `dist-bornes-1-diag`, code de départ
`5790506fd48475d65570e2c7de02c5da5ac2c0d7`. Aucun `.nut` modifié.
Les références fichier:ligne ci-dessous sont relatives à `ai/OpexAI/` et ont
été vérifiées dans cet arbre. Le journal historique n'est pas une preuve que
son bundle exécutait exactement cet arbre ; aucune qualification économique.

## Pourquoi 154 peut être inférieur à airMin=200

L'hypothèse de l'inventaire (« les hubs ne filtrent peut-être pas la bande »)
ne se confirme pas dans le code courant. **Les trois chemins filtrent la bande,
mais `dist` journalisé et le minimum de la bande AIR ne mesurent pas la même chose.**

- `candidates.nut:472` définit `OpexAirPairInBand` : ALL impose Manhattan
  ≥ `airMin` ; AIR_ONLY impose Manhattan > `railMax` ; AIR_RAIL impose
  `railAirOverlapMin` ≤ Manhattan ≤ `railMax`. La borne haute `airMax` porte
  sur `flightDistance`, et 0 la désactive (`candidates.nut:482`).
- Le calcul central rabat `railAir` sur `railMax` (`candidates.nut:410`) puis
  définit `airMin` avec ces mêmes valeurs (`candidates.nut:420`). Dans l'époque
  observée, AIR_RAIL autorise donc Manhattan **exactement 200**, pas 154.
  Cette bande n'explique pas à elle seule une distance Manhattan sous 200.
- `OpexFlightDistance`, `air_coverage.nut:147`, calcule entre **ancres d'aéroports**
  `max(dx,dy) + floor(414*min(dx,dy)/1000)`, avec minimum 1. C'est une approximation
  de la distance euclidienne, malgré le mot « exacte » dans le commentaire.
  Le filtre minimum utilise, lui, Manhattan entre **centres des villes**.
- Les plans stockent `distance = flightDistance` (`air_planning.nut:705`,
  `:1329`, `:1502`). `task_air.nut:312` et `:313` écrivent `plan.distance`
  dans `PROJECT_CHOSEN` et `AIR_BUILD`, mais `src`/`dst` sont les tuiles des villes.
  Une distance journalisée inférieure à 200 est donc compatible avec le filtre.

Cas concret du bras `reference` : le 1971-06-04, `src=49565 dst=22586 dist=154`,
suivi de `AIR_BUILD arm=hubsite line=25`. Sur la carte 256² indiquée dans
l'inventaire, les centres sont (157,193) et (58,88) : Manhattan = 99+105 = **204**.
Le filtre ALL et le filtre AIR_ONLY peuvent l'accepter ; AIR_RAIL, limité ici
à 200, le refuserait. La distance de vol 154 concerne les ancres, absentes de ces
deux événements : elle ne se recalcule pas exactement à partir des seuls centres.
Le journal ne donne pas le `paxBand` ni l'appel générateur du plan : attribution
exacte à un appel non établie, mais ce cas ne démontre aucun contournement.

## Appels et propagation de paxBand

| Appel vérifié | Bande et contexte |
| --- | --- |
| `projects.nut:348` | `airBand`, défini `:150` : AIR_ONLY au stade AIR_ONLY, AIR_RAIL au stade AIR_RAIL, ALL sinon. Un override complet peut fournir les plans au lieu de cet appel (`:336`). |
| `projects.nut:377` | AIR_RAIL en repli du stade initial AIR_ONLY lorsque la liste AIR est vide et sans override complet. |
| `projects_generation.nut:92` | ALL, régénération éventuellement ciblée sur une ville. |
| `projects_generation.nut:210` | ALL, régénération découpée avec curseur, éventuellement ciblée. |
| `scheduler_tasks.nut:275` | `s.band`, initialisé depuis le stade (`:40`), puis basculé vers AIR_RAIL pour le repli (`:305`). |
| `po01c_regen.nut:132` | Appelle `OpexPO01CAirPlans`, et non directement `OpexAirPlans` ; ALL explicite `:133`. |
| `projects_update.nut:155` | Argument omis, donc ALL ; appel dans `else if (airBuilt)` après `if (airBuilt)` (`:147`, `:151`), branche actuellement inaccessible. Ne pas la compter comme chemin actif. |

`OpexAirPlans` a ALL comme défaut (`air_planning.nut:1814`) et transmet
`paxBand` à `ctx` (`:1826`). La copie PO-01c a le même défaut
(`po01c_generators.nut:1628`) et propage aussi cette valeur au contexte (`:1640`).
Les anciens plans peuvent être conservés entre étapes (`projects.nut:353`, `:362`) :
la comparaison diagnostique avec l'époque de **sélection** ne prouve pas quelle
époque a servi à leur **génération**.

## Les trois chemins de génération

| Chemin | Distances, filtre et plan |
| --- | --- |
| Nouvelle paire | Manhattan villes `air_planning.nut:654`, distance de vol ancres `:658`, minimum secondaire `:659`, `OpexAirPairInBand` `:664`, distance du plan `:705`. `minDist` vaut 32 ou 30 selon la vitesse (`:1869`). |
| Hub → site | Manhattan villes `:1292`, minimum secondaire 20 `:1293`, vol ancres `:1300`, filtre de bande **présent** `:1301`, plan `:1329`. |
| Hub → hub | Manhattan villes `:1468`, minimum secondaire 20 `:1469`, vol ancres `:1475`, filtre de bande **présent** `:1476`, plan `:1502`. |

L'orchestrateur appelle les nouvelles paires (`air_planning.nut:1878`), la phase
hub→site (`:1892`, délégation effective `:1802`) et `OpexAirPlansHubToHub`
(`:1903`). PO-01c réutilise ces phases (`po01c_generators.nut:1700`, `:1721`,
`:1732`), avec son minimum 30/32 (`:1685`). Le chemin lazy des nouvelles paires
revient également au filtre commun via `OpexAirPlansNewPairs`
(`air_lazy_sites.nut:273`). Les minima 20/30/32 ne remplacent pas la bande.

## Événements, couverture et interprétation

L'analyseur reprend la grammaire OPEX, la lecture gzip et la convention de noms
de `sweeps/diag_v307r_exposition.py`, sans importer ses éléments spécifiques V307.
Il lit uniquement les fichiers directement dans `--logs`, refuse les doublons
`.log`/`.log.gz` d'une même partie et conserve les répétitions séparément pour
les époques. Les distributions agrégées regroupent les événements, sans moyenne
de quantiles et sans prétendre à des observations indépendantes par projet.

`ROAD_BUILD` existe (`task_road.nut:212`), AIR à `task_air.nut:313`, RAIL à
`task_rail.nut:1212`. Choix et constructions sont comptés séparément, sans
appariement artificiel : dans l'exemple référence, 1 choix RAIL est exposé contre
3 constructions. Les événements seuls ne suffisent pas à expliquer cette couverture.
L'analyseur ne transforme ni une distance manquante en zéro, ni un échec de
construction en construction.

Les rejets de distance sont exposés dans `VIVIER_REJECT` :
`candidates.nut:1391`/`:1394` (rail), `:1890`/`:1893` (route).
Le champ mode manque dans ces événements ; le tableau le dit explicitement.
Les diagnostics AIR peuvent exposer `outcome=distance_short`, `distance_long`,
`max_order_distance` ou `pax_band` (`air_planning.nut:659` et suivantes), sous
sondes additionnelles. Leur absence avec `decision_log=1` n'est pas zéro rejet AIR.
Les compteurs sont des tentatives possiblement répétées, pas des paires uniques ;
les canaux restent séparés pour éviter de sommer aveuglément des sondes redondantes.
Pour la route, dépasser `roadMax` n'est pas franchir son filtre de génération :
celui-ci utilise `roadGenMax` (`candidates.nut:456`).

## Validation et observation du dossier fourni

`python3 -X utf8 -m unittest sweeps.test_diag_dist_bornes` : **7 tests verts**.
Fixtures en chaînes : événements, distributions, égalités aux bornes, dates
non rembourrées et même jour, changements d'époque, valeurs absentes/invalides,
rejets pondérés, gzip, doublons, séparation bras/répétitions et agrégation.

Commande exécutée, dossier externe lu uniquement à la demande explicite :

```bash
python3 -X utf8 sweeps/diag_dist_bornes.py --logs /home/deploy/.claude/jobs/e230de46/tmp/wt_c77defer/results/po03_c77defer_smoke_1x1_20261022_engine
```

Le dossier contient deux bras, une graine 42 et une répétition chacun. Malgré
`smoke_1x1` dans le nom, les événements vont jusqu'à décembre **1971** ; aucun
horizon n'est déduit du nom. Une seule époque exposée par bras, sans changement
observable. Référence : **38** choix AIR (154–278), dont **17** sous airMin
numériquement ; c77defer : **41** (151–278), dont **17** sous airMin. La référence
complète lue ici donne 38, pas les 34 annoncés dans l'inventaire ; la fenêtre
exacte de ce décompte antérieur n'est pas établie. Rejets référence : 94
`distance_long`, 2 `road_distance_long` ; c77defer : 90 `distance_long`.
Aucune conclusion de gain, de santé ou de défaut comportemental sur cette graine.

Empreintes SHA-256 des journaux lus :

```text
c77defer_seed42_r0.log  4d13cea50a60d8f43c6c7e0fb3b82cd760d833132022c6a9b8283e26a0eb5a0e
reference_seed42_r0.log  4d99b02019117252714516e1292750fd630d218679385a9417cfb5417a460e48
```

La sortie intégrale de la commande suit.

---

# Diagnostic des bornes de distance

Distances `dist` telles que journalisées ; quantiles par interpolation linéaire (n−1)p. AIR : dist est la distance de vol, airMin porte sur Manhattan entre villes : « hors bande » est numérique, pas une preuve de contournement. Route : roadMax est la frontière économique ; roadGen est le plafond de génération. Bornes inclusives pour ce diagnostic, airMax=0 sans plafond. Époque = dernier EPOCH_BOUNDS à la date du projet, ordre des lignes le même jour. Aucune borne empruntée à une autre répétition. — = inconnu. n=0 signifie aucun événement observé. Agrégats pondérés par événement, pas par graine. Rejets : sommes par événement/raison, susceptibles de recompter une paire ; pax_band ne distingue pas court/long. Aucun contrôle de santé ni verdict économique.

## Bras c77defer

### Graine 42

#### Répétition 0

| date | ligne | roadMin | roadMax | roadGen | railMin | railAir | railMax | airMin | airMax | évolution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1970-01-02 | 109 | 7 | 7 | 200 | 7 | 200 | 200 | 200 | 512 | initial |

| date | ligne | mode | src | dst | dist | époque | position numérique |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1970-01-17 | 603 | air | 24869 | 48086 | 214 | 1970-01-02 | dans la bande |
| 1970-01-19 | 674 | air | 59980 | 10926 | 227 | 1970-01-02 | dans la bande |
| 1970-04-08 | 2425 | air | 6457 | 51421 | 244 | 1970-01-02 | dans la bande |
| 1970-05-28 | 3465 | air | 14422 | 40153 | 170 | 1970-01-02 | sous airMin |
| 1970-06-24 | 3905 | air | 24869 | 49565 | 159 | 1970-01-02 | sous airMin |
| 1970-07-10 | 4153 | air | 48086 | 12057 | 244 | 1970-01-02 | dans la bande |
| 1970-08-13 | 4746 | air | 10926 | 54044 | 221 | 1970-01-02 | dans la bande |
| 1970-08-22 | 4913 | air | 51421 | 5900 | 278 | 1970-01-02 | dans la bande |
| 1970-09-08 | 5241 | air | 59980 | 34012 | 182 | 1970-01-02 | sous airMin |
| 1970-10-15 | 5929 | air | 40153 | 12090 | 205 | 1970-01-02 | dans la bande |
| 1970-11-10 | 6485 | air | 48086 | 3094 | 263 | 1970-01-02 | dans la bande |
| 1970-11-23 | 6705 | air | 6457 | 59635 | 272 | 1970-01-02 | dans la bande |
| 1970-11-28 | 6784 | air | 12057 | 54641 | 200 | 1970-01-02 | dans la bande |
| 1970-12-23 | 7403 | air | 54044 | 9157 | 255 | 1970-01-02 | dans la bande |
| 1971-01-14 | 7930 | air | 51421 | 20041 | 204 | 1970-01-02 | dans la bande |
| 1971-01-15 | 7938 | air | 5900 | 42610 | 185 | 1970-01-02 | sous airMin |
| 1971-01-27 | 8299 | rail | 45472 | 51600 | 40 | 1970-01-02 | dans la bande |
| 1971-03-09 | 9291 | air | 24869 | 59635 | 247 | 1970-01-02 | dans la bande |
| 1971-03-13 | 9370 | air | 59980 | 9157 | 260 | 1970-01-02 | dans la bande |
| 1971-03-24 | 9619 | air | 14422 | 39666 | 180 | 1970-01-02 | sous airMin |
| 1971-04-03 | 9971 | air | 12090 | 56708 | 212 | 1970-01-02 | dans la bande |
| 1971-04-10 | 10045 | road | 22586 | 24869 | 29 | 1970-01-02 | au-dessus de roadMax |
| 1971-04-20 | 10362 | air | 3094 | 33405 | 160 | 1970-01-02 | sous airMin |
| 1971-05-04 | 10907 | air | 54641 | 5200 | 212 | 1970-01-02 | dans la bande |
| 1971-05-20 | 11292 | air | 49565 | 22586 | 154 | 1970-01-02 | sous airMin |
| 1971-05-22 | 11342 | air | 39666 | 28461 | 197 | 1970-01-02 | sous airMin |
| 1971-06-06 | 11987 | air | 34012 | 54860 | 165 | 1970-01-02 | sous airMin |
| 1971-06-19 | 12401 | air | 38955 | 7810 | 156 | 1970-01-02 | sous airMin |
| 1971-07-01 | 12801 | air | 39666 | 40461 | 211 | 1970-01-02 | dans la bande |
| 1971-07-16 | 13357 | air | 5200 | 32963 | 161 | 1970-01-02 | sous airMin |
| 1971-08-02 | 13896 | air | 6457 | 40153 | 213 | 1970-01-02 | dans la bande |
| 1971-08-16 | 14408 | air | 14422 | 54044 | 182 | 1970-01-02 | sous airMin |
| 1971-08-17 | 14419 | air | 10926 | 54860 | 197 | 1970-01-02 | sous airMin |
| 1971-08-29 | 14810 | air | 49565 | 12057 | 200 | 1970-01-02 | dans la bande |
| 1971-08-31 | 14853 | air | 40461 | 21394 | 151 | 1970-01-02 | sous airMin |
| 1971-09-09 | 15124 | air | 5900 | 34012 | 241 | 1970-01-02 | dans la bande |
| 1971-09-18 | 15395 | air | 12090 | 59635 | 257 | 1970-01-02 | dans la bande |
| 1971-09-27 | 15680 | air | 3094 | 42610 | 189 | 1970-01-02 | sous airMin |
| 1971-10-05 | 15946 | air | 54641 | 9157 | 224 | 1970-01-02 | dans la bande |
| 1971-10-12 | 16125 | air | 20041 | 56708 | 169 | 1970-01-02 | sous airMin |
| 1971-10-26 | 16592 | air | 56708 | 5200 | 228 | 1970-01-02 | dans la bande |
| 1971-11-27 | 17522 | air | 54860 | 7810 | 200 | 1970-01-02 | dans la bande |
| 1971-12-26 | 18475 | air | 7810 | 40461 | 172 | 1970-01-02 | sous airMin |

| population | mode | n | min | q25 | médiane | q75 | max | dist absente/invalide |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| choisis | air | 41 | 151 | 180 | 204 | 228 | 278 | 0 |
| choisis | rail | 1 | 40 | 40 | 40 | 40 | 40 | 0 |
| choisis | road | 1 | 29 | 29 | 29 | 29 | 29 | 0 |
| construits | air | 41 | 151 | 180 | 204 | 228 | 278 | 0 |
| construits | rail | 2 | 36 | 37 | 38 | 39 | 40 | 0 |
| construits | road | 1 | 29 | 29 | 29 | 29 | 29 | 0 |

Hors bande numériques : air sous airMin = 17, road au-dessus de roadMax = 1

| événement de rejet | mode déclaré | raison | somme n | n invalide |
| --- | --- | --- | --- | --- |
| VIVIER_REJECT | non indiqué | distance_long | 90 | 0 |

### Agrégat du bras c77defer

| population | mode | n | min | q25 | médiane | q75 | max | dist absente/invalide |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| choisis | air | 41 | 151 | 180 | 204 | 228 | 278 | 0 |
| choisis | rail | 1 | 40 | 40 | 40 | 40 | 40 | 0 |
| choisis | road | 1 | 29 | 29 | 29 | 29 | 29 | 0 |
| construits | air | 41 | 151 | 180 | 204 | 228 | 278 | 0 |
| construits | rail | 2 | 36 | 37 | 38 | 39 | 40 | 0 |
| construits | road | 1 | 29 | 29 | 29 | 29 | 29 | 0 |

Hors bande numériques : air sous airMin = 17, road au-dessus de roadMax = 1

| événement de rejet | mode déclaré | raison | somme n | n invalide |
| --- | --- | --- | --- | --- |
| VIVIER_REJECT | non indiqué | distance_long | 90 | 0 |

## Bras reference

### Graine 42

#### Répétition 0

| date | ligne | roadMin | roadMax | roadGen | railMin | railAir | railMax | airMin | airMax | évolution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1970-01-02 | 109 | 7 | 7 | 200 | 7 | 200 | 200 | 200 | 512 | initial |

| date | ligne | mode | src | dst | dist | époque | position numérique |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1970-01-17 | 603 | air | 24869 | 48086 | 214 | 1970-01-02 | dans la bande |
| 1970-01-19 | 674 | air | 59980 | 10926 | 227 | 1970-01-02 | dans la bande |
| 1970-04-08 | 2425 | air | 6457 | 51421 | 244 | 1970-01-02 | dans la bande |
| 1970-05-28 | 3463 | air | 40153 | 12057 | 235 | 1970-01-02 | dans la bande |
| 1970-06-23 | 3908 | air | 24869 | 49565 | 159 | 1970-01-02 | sous airMin |
| 1970-07-07 | 4107 | air | 48086 | 12090 | 214 | 1970-01-02 | dans la bande |
| 1970-08-06 | 4683 | air | 59980 | 24291 | 211 | 1970-01-02 | dans la bande |
| 1970-08-19 | 4903 | air | 51421 | 5900 | 278 | 1970-01-02 | dans la bande |
| 1970-09-21 | 5547 | air | 40153 | 54044 | 213 | 1970-01-02 | dans la bande |
| 1970-10-05 | 5858 | air | 51421 | 3094 | 276 | 1970-01-02 | dans la bande |
| 1970-10-17 | 6142 | air | 6457 | 59635 | 272 | 1970-01-02 | dans la bande |
| 1970-11-05 | 6620 | air | 5900 | 54641 | 232 | 1970-01-02 | dans la bande |
| 1970-12-07 | 7200 | air | 54044 | 9157 | 255 | 1970-01-02 | dans la bande |
| 1970-12-17 | 7426 | air | 10926 | 44107 | 169 | 1970-01-02 | sous airMin |
| 1970-12-27 | 7729 | air | 12057 | 34012 | 220 | 1970-01-02 | dans la bande |
| 1971-02-28 | 9133 | air | 24869 | 40153 | 205 | 1970-01-02 | dans la bande |
| 1971-03-07 | 9371 | air | 3094 | 42610 | 189 | 1970-01-02 | sous airMin |
| 1971-03-13 | 9487 | air | 59635 | 16485 | 215 | 1970-01-02 | dans la bande |
| 1971-03-28 | 9941 | air | 48086 | 7810 | 185 | 1970-01-02 | sous airMin |
| 1971-04-15 | 10606 | air | 5900 | 33405 | 156 | 1970-01-02 | sous airMin |
| 1971-04-27 | 10997 | air | 12090 | 56708 | 212 | 1970-01-02 | dans la bande |
| 1971-05-16 | 11587 | air | 59980 | 12057 | 206 | 1970-01-02 | dans la bande |
| 1971-05-24 | 11816 | air | 54044 | 32963 | 196 | 1970-01-02 | sous airMin |
| 1971-06-04 | 12177 | air | 49565 | 22586 | 154 | 1970-01-02 | sous airMin |
| 1971-06-24 | 12858 | air | 6457 | 34012 | 198 | 1970-01-02 | sous airMin |
| 1971-06-29 | 13009 | air | 10926 | 54641 | 191 | 1970-01-02 | sous airMin |
| 1971-07-05 | 13191 | air | 49565 | 12090 | 195 | 1970-01-02 | sous airMin |
| 1971-07-16 | 13479 | air | 16485 | 39666 | 171 | 1970-01-02 | sous airMin |
| 1971-08-09 | 14353 | air | 24291 | 54641 | 167 | 1970-01-02 | sous airMin |
| 1971-08-12 | 14459 | air | 3094 | 33405 | 160 | 1970-01-02 | sous airMin |
| 1971-08-25 | 14915 | air | 59635 | 22586 | 231 | 1970-01-02 | dans la bande |
| 1971-08-27 | 14948 | air | 9157 | 44107 | 203 | 1970-01-02 | dans la bande |
| 1971-09-10 | 15489 | air | 9157 | 56708 | 224 | 1970-01-02 | dans la bande |
| 1971-09-21 | 15816 | air | 7810 | 38955 | 156 | 1970-01-02 | sous airMin |
| 1971-10-07 | 16328 | air | 24291 | 38955 | 203 | 1970-01-02 | dans la bande |
| 1971-10-21 | 16902 | air | 39666 | 28461 | 197 | 1970-01-02 | sous airMin |
| 1971-10-25 | 16991 | air | 34012 | 22586 | 174 | 1970-01-02 | sous airMin |
| 1971-11-10 | 17462 | air | 39666 | 38955 | 185 | 1970-01-02 | sous airMin |
| 1971-12-23 | 18611 | rail | 9815 | 26996 | 96 | 1970-01-02 | dans la bande |

| population | mode | n | min | q25 | médiane | q75 | max | dist absente/invalide |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| choisis | air | 38 | 154 | 185 | 204 | 223 | 278 | 0 |
| choisis | rail | 1 | 96 | 96 | 96 | 96 | 96 | 0 |
| choisis | road | 0 | — | — | — | — | — | 0 |
| construits | air | 38 | 154 | 185 | 204 | 223 | 278 | 0 |
| construits | rail | 3 | 36 | 38 | 40 | 68 | 96 | 0 |
| construits | road | 0 | — | — | — | — | — | 0 |

Hors bande numériques : air sous airMin = 17

| événement de rejet | mode déclaré | raison | somme n | n invalide |
| --- | --- | --- | --- | --- |
| VIVIER_REJECT | non indiqué | distance_long | 94 | 0 |
| VIVIER_REJECT | non indiqué | road_distance_long | 2 | 0 |

### Agrégat du bras reference

| population | mode | n | min | q25 | médiane | q75 | max | dist absente/invalide |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| choisis | air | 38 | 154 | 185 | 204 | 223 | 278 | 0 |
| choisis | rail | 1 | 96 | 96 | 96 | 96 | 96 | 0 |
| choisis | road | 0 | — | — | — | — | — | 0 |
| construits | air | 38 | 154 | 185 | 204 | 223 | 278 | 0 |
| construits | rail | 3 | 36 | 38 | 40 | 68 | 96 | 0 |
| construits | road | 0 | — | — | — | — | — | 0 |

Hors bande numériques : air sous airMin = 17

| événement de rejet | mode déclaré | raison | somme n | n invalide |
| --- | --- | --- | --- | --- |
| VIVIER_REJECT | non indiqué | distance_long | 94 | 0 |
| VIVIER_REJECT | non indiqué | road_distance_long | 2 | 0 |
