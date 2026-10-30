# RAIL-REPAIR-IDLE — maturation à 10 ans des 5 lignes SITE sauvées

## Préenregistrement, 31 octobre 2026, avant toute simulation

Demande utilisateur : poursuivre les cinq lignes effectivement construites
avec `RAIL_BUILD site_repair=1` jusqu'en **1979**, et « enchaîner sur une
porte B si c'est prometteur ».

### Origine des lignes et limites de sélection

Dans le replay diagnostique **40×5**, `probes=258` / `-d script=4`,
cinq lignes SITE se sont construites sur cinq graines :

| Graine | OD des événements SITE / BUILD | Cargo | Date en 1974 |
|---|---|---|---|
| 100 | 46958→29140 | COAL | 18 août |
| 512 | 31408→39017 | IORE | 16 décembre |
| 12345 | 46126→50747 | GRAI | 13 novembre |
| 54321 | 12108→23443 | GRAI | 17 octobre |
| 65537 | 42142→29270 | GRAI | 18 février |

Les cinq graines sont **sélectionnées après exposition positive** : leur
résultat ne peut pas être projeté sur les 40 graines ni considéré comme
une nouvelle porte A. Le 40×5 économique initial demeure **NO-GO**
(+0,113 %, p=0,824, intervalle englobant 0).

### Étape 1 — cinq duels à 10 ans (diagnostic, pas porte A)

- Source IA sans modification, `origin/master=b4bbc4a3`.
- Même OpenTTD 15.3, OpenGFX 7.1, carte 256², inflation OFF,
  `1970–1979`, **5 graines** pré-sélectionnées, 1 répétition.
- RAIL seul ; témoin `mode_air=0,mode_road=0,mode_water=0,mode_rail=1`,
  quatre réparateurs OFF ; variante : mêmes modes, avec SITE, V131,
  A* et POSE `=1`, conditionnés aux six mois sans nouvelle ligne.
  `v233l_constructibilite=0` dans les deux bras.
- Pour maximiser la comparabilité **intra-duel instrumenté**, le témoin
  et la variante utilisent tous deux `probes=258`, journal moteur
  `script=4`. Conserver tous les `RAIL_BUILD`, `RAIL_SITE_REPAIR`,
  `RAIL_REPAIR_IDLE` et les erreurs. Le code de l'IA n'est pas édité.
  L'instrumentation change les opcodes par rapport au 40×5 économique.
- Parcourir les sauvegardes mensuelles ; lors de chaque décembre
  (1974–1979), lire les véhicules `VEHS`, les ordres `ORDL/ORDR`
  et les gares `STNN` via le décodeur existant
  `extract_line_telemetry`. Les profits de flotte
  `profit_this_year/256` sont **observés**, sans les convertir en
  profit net après CAPEX, gare, station ou dette. La mesure d'année
  entière à décembre reflète les mois écoulés et doit être distinguée
  du `profit_last_year` historique de flotte.
- Association **sans attribution forcée** des OD loguées aux services
  de gares et trains (carte 256², stations/cargo/ordres) ; éliminer
  les associations ambiguës. Documenter chaque ligne sauvée :
  existe-t-elle de nouveau en replay 10 ans avant fin 1974 ?
  Dispose-t-elle de trains attribuables univoquement en 1975–1979 ?
  Le profit de flotte à maturité est-il positif ? Distinguer prévision,
  profit d'exploitation réel, capital et profit causal.
- Vérifier **10/10 parties saines**, tous les clichés 1970–1979 et
  trajectoires appariées `profit_year` et `company_value` ;
  des lignes de même OD construites dans le témoin interdisent de
  prétendre à un effet causal exclusif.

**Règle préalable d'escalade vers la B**, seulement un *signal
exploratoire*, choisie avant calcul :

1. Au moins **3/5 OD** reproduites en `RAIL_BUILD site_repair=1`
   avant la fin 1974 dans le nouveau replay et associées sans
   ambiguïté à un service physique.
2. Au moins **3/5 lignes** avec un profit de flotte réalisé **>0**
   sur au moins un cliché mature 1976–1979, et aucune erreur de
   qualification dans les dix parties.
3. Delta moyen apparié `profit_year` terminal 1979 **>0**,
   ratio des valeurs moyennes **≥0,95** sur les cinq duels.

Si l'un de ces points est manquant/ambigu/négatif : **pas de B**,
rapport du blocage, aucune activation des défauts. Ce criblage
sur cinq graines sélectionnées est volontairement faible :
une B ne pourra jamais effacer un échec A préexistant.

### Étape 2 — B conditionnelle, 20 graines × 10 ans

Si les trois conditions précédentes passent, lancer **sans demander
une nouvelle autorisation** un duel RAIL seul `OFF` contre
`SITE/V131/A*/POSE=1`, les **20 graines initiales canoniques**
`bench_v2.SEEDS`, 1970–1979, 256², un seul worker pool
8 workers maximum, aucune concurrence Docker.

La B sera **une étude de non-érosion distincte**, car la vraie A 40×5
est déjà NO-GO : ne pas en déduire une adoption.
Contrairement au suivi diagnostic, la B est sans journal moteur et
`probes=2`, identique à l'instrumentation de l'A échouée.
Critères **préenregistrés** : 20/20 paires saines, delta
`profit_year` 1979 (ON−OFF), borne supérieure de l'IC95
bootstrap apparié **≥0**, ratio de moyennes
`company_value` **≥0,95**. Reporter aussi Wilcoxon, ratio de profit,
victoires/défaites et dispersion. Si B échoue, conclure NO-GO
non-érosion. Si B passe, documenter « B exploration non-érosion »
sans changer les défauts tant qu'une nouvelle A complète n'a pas
qualifié les réparations.

### Exécution et intégrité

Lanceur : `sweeps/run_rail_repair_idle_maturation_10y_20261031.py`,
analyseur : `sweeps/analyse_rail_repair_idle_maturation_10y_20261031.py`.
Sources NoAI tar SHA256 **figées** depuis le 30 octobre.
Les fichiers de résultats moteur restent dans `results/` (ignorés
par Git). Les conclusions et les agrégats individuels seront publiés
dans ce rapport et dans un petit JSON de preuve versionné.

**Aucun réglage IA par défaut n'est modifié.**
