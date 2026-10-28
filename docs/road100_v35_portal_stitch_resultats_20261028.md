# ROAD100-35 — qualification moteur Portal-Stitch, verdict NO-EXPOSURE

Date : 28 octobre 2026. Préenregistrement figé :
[`road100_v35_portal_stitch_prereg_20261028.md`](road100_v35_portal_stitch_prereg_20261028.md).
Ce rapport ne revendique **aucune parité** contre AAAHogEx-115.

## Validation, sources et santé

- Traceur autonome `OpexRoad100PortalStitchTrace` ajouté à
  `ai/OpexAI/road100_sparse_corridor.nut`, sans modifier les entrées V33.
  Départ/arrivée sur vrais sites DT testés, voies existantes reliées dans
  les deux sens aux deux bouts, 16 expansions par bout, trois portails,
  douze bandes et trois alternatives locales maximum, trace de 80 à 190 arêtes.
  La vérification d'arêtes et le devis restent la responsabilité du builder.
- Projection de source OFF avec fixture V35 indépendante, fixtures historiques
  V262/V31/V32/V33/V34 inchangées. `git diff --check` OK. Suite complète
  **3 234 tests OK, 5 skipped, 2 expected failures** après correction.
- Le premier essai `road100_v35_portal_stitch_roadonly_seed42_1x1_20261028`
  est **INVALIDÉ** : `noai_error` dans les deux bras, parse Squirrel
  `road100_sparse_corridor.nut:418 expected IDENTIFIER` sur le nom réservé
  `parent`. Renommé `prevIndex` ; aucun profit de ce run n'est utilisable.
- Campagne moteur valide :
  `results/road100_v35_portal_stitch_roadonly_seed42_1x1_syntaxfix_20261028`.
  Bundle commun SHA256
  `a4a32e47498fa4b7b796da1f3059650a9a05080f639f5bf8852bbdc9c130a5ac`,
  `complete/complete`, graine 42, 1970, une année, 256². Seule différence
  effective des politiques : `road100_portal_stitch` **0→1** ; V33 sparse,
  V34 market probe et les autres options ROAD sont identiques. AAAHogEx-115
  désactive train, tram, bateau et avion ; Opex désactive AIR/RAIL/WATER.
  Détails, `profit_year` société, JSONL et santé dans les JSON, manifeste
  et logs `_engine` de cette campagne ; il ne s'agit pas d'une Gate A.

## Exposition et mécanismes observés

| Marché LONG | PASS/mois potentiels V34 ex ante | Résultat V35 | Traceur | Opérations par couple, admission incluse |
|---|---:|---|---:|---:|
| Villes 18→2, centres d158, sites 32418→25381 | 258 | `NO_CORRIDOR`, `BAND_1_EDGE_OCCUPIED`, premier refus `EDGE_OCCUPIED`, 3/3 portails, 0 bande aboutie | 21 085 | 131 922 / 180 000 |
| Villes 26→10, centres d154, sites 60234→28973 | 175 | `NO_CORRIDOR`, `BAND_10_GAP_TURN`, premier refus `EDGE_OCCUPIED`, 3/1 portails, 9 bandes franchies | 42 107 | 131 504 / 180 000 |

Le fallback obstacle a ensuite atteint `OPCAP` sans plan, après 81 275 puis
60 585 opcodes dans les recherches d'obstacles. Les devis, gares, dépôts,
flottes et revenus LONG ne sont **jamais construits** ; les **258/175** sont
des PASS/mois estimés *avant chantier*, pas des PASS transportés. Aucun
événement de construction LONG n'est imputable à V35. Budget annuel LONG
mesuré : environ 324 411 opcodes pour V35, sous le plafond de 400 000.

## Effet économique réel H1 (société, non lignes)

| Mesure | Opex V35 ON | AAAHogEx-115 |
|---|---:|---:|
| `profit_year` 1970 | **19 103 £** | **97 693 £** |
| Véhicules | 16 | 55 |
| Gares | 16 | 8 |

Opex atteint **19,55 %** du `profit_year` AAA sur cette seule graine ; écart
de société **−78 590 £/an**. Comparaison causale V35 ON−OFF : **−31 £/an**
en H1 (0 victoire/1 défaite, une seule paire, aucun test statistique de gain
possible), valeur de compagnie **−1,22 %**. La construction LONG étant nulle,
ce delta ne peut pas être interprété comme un effet de liaison longue.

## Décision

**V35 = NO-EXPOSURE / NO-GO** selon la porte prédéclarée. **Ne pas lancer de
5×5 ni Gate A 40×5. ROAD100 reste à 0/5 parités** ; les horizons H2–H5 ne
sont pas testés pour V35. Ne changer aucun réglage par défaut. Ne pas
commit/push/merge/reset/clean sans ordre utilisateur. Préserver les bundles,
logs, résultats et les autres travaux concurrents.

Le déficit est structurel en H1 même avec le moteur sain : 16 véhicules Opex
contre 55 AAA, et le LONG plafonne à deux bus par quai racine dans ce
mécanisme. Une nouvelle piste ne sera recevable qu'après diagnostic de
capacité/rotations, PASS **livrés**, caisse, StationIDs et revenu net sur
des lignes Opex effectivement construites — ou preuve nouvelle de corridor
complet, devis et capacité financés. Ne pas inventer un revenu de retour,
de satellite non construit ou de `waiting` AAA après construction.

## Audit causal des refus et du manque H1 (lecture seule des logs)

Le `NO_CORRIDOR` ne prouve pas que le terrain est absolument infranchissable :
le module V35 refuse les trois couples de portails *avant* le vérificateur
physique. Dans le premier cas, `road100_sparse_corridor.nut:697–709`
réserve les deux manches routières ; le calcul de bande aux lignes 563–566
refuse le chevauchement (`EDGE_OCCUPIED`), sans essayer une géométrie mieux
séparée. Dans le second cas, la bande 10 échoue au pivot de pente
(`GAP_TURN`, lignes 575–587) après neuf bandes acceptées, car les
alternatives sont gloutonnes et les bandes précédentes ne sont pas révisées
(`:731–780`). Il s'agit de limites de la recherche bornée, **pas de preuves
de corridor constructible**. Une autre géométrie devrait encore passer le
vrai `LongVerifyTrace` et les devis sans dépasser les limites préenregistrées.

Sur la même année, OFF et ON mettent en service les six mêmes premières
lignes fret (3 COAL, 2 IORE, 1 WOOD), soit douze véhicules initiaux, puis
le même premier bus PAX d32 le 3 avril (`monthly=26`, un bus,
`pred_profit=170£/an`). OFF construit un deuxième petit service PAX d50
le 7 décembre, absent en ON après divergence de scheduling et `TRACEX` ;
le déficit ON−OFF H1 de 31£ ne démontre pas la causalité de cet écart.
La caisse ON à fin 1970 est d'environ **195 k£** ; aucun devis LONG
(`road_quote`, `cash_need`) n'ayant été atteint, on ne peut attribuer
les refus LONG à un manque de trésorerie. Les logs `C63_INVEST` signalent
également des marchés abandonnés (`abandon_filtered`, paires 23→27), à
auditer avant de supposer une saturation de bus.

**Critère d'un éventuel correctif ciblé (pas une nouvelle variante aveugle)** :
la même paire de quais doit produire une trace continue et vérifiée,
un nombre exact de routes manquantes, un devis et besoin de caisse, puis
des gares/dépôts/véhicules réels et des PASS livrés. Le débit avec un seul
quai par bout impose toujours un cap de deux bus. Sans mesure de débit et
profit annuels de société, aucun élargissement de flotte ni Gate A n'est
justifié.
