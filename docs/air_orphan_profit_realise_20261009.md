# AIR — actifs orphelins, résultat réel des premières lignes (09/10/2026)

## Hypothèse testable et limites

Après l'identification exacte de cinq aéroports A réutilisés après BFAIL
(`docs/air_orphan_reuse_20261009.md`), on cherche le bénéfice net de leurs
**lignes réellement exploitées**, ainsi que la présence physique à la fin de
trois ans des trois aéroports sans service observé. Le profit des véhicules
est un résultat comptable observé après construction, et ne mesure pas la
différence contrefactuelle avec un autre itinéraire ou avec un rollback de A.
Les revenus et les dépenses d'exploitation ne sont pas séparés dans les
snapshots actuels, seuls leurs profits nets par véhicule le sont.

## Protocole fixé avant la nouvelle campagne

- Profil NoAI observationnel conservé :
  `OpexAI[air_site_cost_quote=1,air_site_quote_keep_legacy_margin=1,probe_air_finance_margin=1]`,
  mêmes paramètres que `air_orphan_reuse_6x3_20261009_r1`. Aucun toggle de
  comportement AIR supplémentaire ni réglage par défaut modifié.
- `master`, SHA Git `cb23a172fa6f7b79e50d0392e526a061c130259b`, arbre
  partagé dirty. Le fichier `task_air.nut` live possède au contrôle initial
  le même SHA256 que dans le bundle du premier 6×3 :
  `5c36319c5d67efd8d4236c3d994a920900925840449eb61c678a699eb0aaa3b9`.
  Contrôler le nouveau manifeste et les hashes de source plutôt que présumer
  des tracés bit identiques.
- Six graines `42,100,999,1234,5678,2026`, trois années 1970–72, une
  répétition. Nouvelle collecte après incident technique :
  `air_orphan_profit_6x3_20261009_r2`. `--script-debug` pour les deux traces
  AIR et `--line-telemetry --line-telemetry-monthly` pour les profits issus des
  sauvegardes aux checkpoints mensuels. `--retain-savegames` dans un dossier
  neuf de `results/` pour inspecter indépendamment les stations à l'horizon.
  Pas de second bras ni de test d'adoption économique A/B.
- Docker Desktop `desktop-linux`, image `openttd-lab:latest`, volume
  `openttd-lab-home`, sur PC local 10 CPU / 8 Go / 10 workers. Vérifier
  `docker ps` avant exécution. Une seule campagne OpenTTD à la fois.
- Correspondance des cinq cas (ancienne campagne, à réétablir dans la nouvelle) :
  seed1234 ligne18 ; seed2026 lignes7 et18 ; seed5678 lignes41 et43.
  Retenir **seulement** les lignes dont les deux stations physiques et la
  première construction correspondent aux événements du **même run**.
  Toute divergence doit être explicitée ; aucune jointure par ville ni
  report automatique des profits de l'ancienne campagne.
- Pour chaque ligne confirmée : dates d'ouverture, premier revenu (si logué),
  bénéfices nets cumulés par avions aux checkpoints disponibles, temps
  d'exploitation, avions présents, coût initial de la nouvelle ligne et
  coût historique de A. Indiquer « inconnu » si manque le début de ligne,
  un avion a été vendu ou le profit a été réinitialisé sans réconciliation.
  Mesurer séparément le nombre de lignes avec résultat négatif/positif.
- Pour les trois stations initialement censurées : inspection de STNN et de
  l'emprise aéroport dans les sauvegardes terminales du **même run**. Elles
  ne sont pas supposées présentes tant que les données ne l'établissent pas.
- Critère d'arrêt : six parties complètes, télémétrie décodée sainement et
  station/ligne attribuée sans ambiguïté ; sinon diagnostic technique.

Les dépenses historiques d'un aéroport réemployé ne sont pas remboursées au
premier vol. Sans contrefactuel apparié où A a été liquidé puis éventuellement
reconstruit, aucune rentabilité causale du choix « garder A » ne peut être
inférée de la somme des profits. Il s'agit d'une mesure observationnelle.

## Résultats

Première tentative `air_orphan_profit_6x3_20261009_r1` : les six parties se
sont exécutées et les sauvegardes existent, mais le rapport final a échoué à
`verify_manifest_bundle` (`frozen bundle fingerprint mismatch`). Cause
technique démontrée : l'option `--retain-savegames` relative était interprétée
depuis `..._bundle/harness` et a ajouté `harness/results/...` **au bundle déjà
figé**. Ce run n'est **pas qualifié** et ne reçoit aucun verdict de santé ni
de bénéfice. Il reste traçable avec ses logs, manifeste, JSONL et archives.
Correctif ciblé du lanceur `sweeps/run_c66_reference.py` : convertir la
destination hôte dans `/work/results/...` et refuser les chemins hors montage
ou sous le bundle ; trois tests de destination et dix-sept tests de gel verts.
Le nouveau nom `r2` est préenregistré avec le même profil et les mêmes graines,
sans aucun changement de politique IA ni sélection de résultat favorable.

**Réexécution `r2` saine et figée :** 6/6 parties `complete` sur 1970–72,
rapport final écrit après vérification de l'empreinte du bundle.
`source_bundle_sha256=d85053ddcd41e57aa5a9f325ed5e783432643a45b227f1f0d8948a077da5cd7a`,
image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Les `profit_year` et `company_value` terminaux sont identiques dans les six
graines à la précédente campagne `air_orphan_reuse_6x3_20261009_r1`.
Huit `AIR_ORPHAN_RETAIN`, cinq premiers `AIR_HUB_REUSE` physiquement joints,
trois censures de service et zéro warning, comme le diagnostic précédent.
Les données et leurs sources complètes figurent dans
`results/air_orphan_profit_6x3_20261009_r2.json`,
`results/air_orphan_profit_6x3_20261009_r2_orphans.json`,
`results/air_orphan_profit_6x3_20261009_r2_financial.json` et
`results/air_orphan_profit_6x3_20261009_r2_savegames/`.

**Survie physique à checkpoint daté :** six archives d'expérience ont un
inventaire complet (36 `.sav` chacune, hash et taille contrôlés). La dernière
save de chaque seed ciblée est datée **1972-12-01 (AIDate=720593)**. Les trois
stations non desservies à trois ans sont **toutes présentes et détenues par
OpexAI** (`STNN.normal.base.owner=0`, `facilities & 8`, `airport.tile` identique
à l'ancre initiale) : seed999 station58/tuile34929/20 960 £ ; seed2026
station106/tuile31166/17 100 £ ; seed5678 station164/tuile53072/26 893 £.
Capital A historique associé **64 953 £**, sans valeur liquidable mesurée.
La présence au 1972-12-31 n'est pas directement observée par cette sauvegarde.
`sweeps/analyse_air_orphan_station_survival.py` et
`results/air_orphan_profit_6x3_20261009_r2_station_survival.json` portent
dates, identités et hashes opposables.

**Profits de ligne sur trois ans :** le décodeur
`sweeps/analyse_air_orphan_profit.py` fait correspondre événements de
conservation/réemploi, `C121_BUILD` (les deux StationID exacts) et groupe
physique `VEHS/ORDL/STNN`. Sur les cinq premières lignes, quatre disposent de
checkpoints après construction ; la cinquième (2026/18) est construite
après le dernier checkpoint du 1972-12-01. Il en résulte 23 intervalles
mensuels complets, un partiel dû à ajout d'avion, et aucun avertissement de
jointure. Les deltas comptables validés valent +15 727,953125 £ sur
1234/18, +93 142,414063 £ sur 2026/7, +1 896,210938 £ sur 5678/41 et
+78,210937 £ sur 5678/43. Ces sommes ne sont **pas** un profit complet depuis
la date de construction : début/fins des fenêtres, changements de flotte
et bénéfices en dehors des snapshots demeurent exclus. `profit_last_year`
montre une bascule annuelle différée (janvier 1972 n'a pas encore reporté
1971, février oui) ; le décodeur évite de la traiter comme une perte du mois.

## Extension de maturité pré-enregistrée après le constat de censure

Les cinq premières lignes de réemploi sont construites entre 1971-05 et
1972-12. La dernière (graine 2026, ligne 18) naît **après** le dernier
checkpoint mensuel du 01/12/1972 ; les deux lignes de 5678 sont construites
en octobre 1972 et ont moins de deux mois observables. Le diagnostic 6×3
ne fournit donc pas une fenêtre de maturité suffisante pour juger de leur
profitabilité.

**Extension observationnelle ciblée fixée avant lancement :** campagne
`air_orphan_profit_maturity_3x5_20261009_r1`, graines **1234, 5678, 2026**
uniquement (les trois graines ayant effectivement conservé puis réutilisé
un aéroport dans le 6×3 initial), **cinq années 1970–74**, une répétition.
Politique `OpexAI[air_site_cost_quote=1,air_site_quote_keep_legacy_margin=1,probe_air_finance_margin=1]`
inchangée ; `--script-debug --line-telemetry --line-telemetry-monthly`,
sans archive physique supplémentaire car r2 conserve déjà les .sav jusqu'à
1972-12. Même image Docker/opengfx et limite locale 10 CPU / 8 Go / 10 workers.
Vérifier avant interprétation la première divergence de trajectoire et le
matching exact des 5 premières utilisations par ancre/StationID, sans les
recoller arbitrairement entre parties. Un changement de position/ligne
entraîne une censure d'attribution pour le cas concerné.

Mesures : profit net comptabilisé sur les avions des lignes jusqu'au
checkpoint de décembre 1974, par année calendaire et cumul des années
observées avec couverture documentée, coût déjà investi dans A et coût du
nouveau chantier ; comparer seulement à titre **descriptif** les coûts
historiques aux profits nets observés, sans actualisation, sans inférer un
retour sur investissement incrémental ou une préférence causale pour garder A.
Les trois graines sont choisies pour exposition observée, **pas un
échantillon aléatoire de qualification**. Aucun seuil numérique de gain,
aucune porte V102 et aucun changement par défaut.

## Maturité 1970–74 : constats moteur

La campagne `air_orphan_profit_maturity_3x5_20261009_r1` est **3/3 complète
et saine**, même bundle SHA que le `r2` précédent, sur les seules graines
1234/5678/2026. Les sept `BFAIL` ayant conservé A dans ces trois graines
ont **tous** été suivis d'une première ligne bâtie avec **même ancre et
StationID**, 0 avertissement : cinq jusqu'en 1972 et deux plus tard,
seed2026 station106 → ligne24 le 28/09/1973 (**516 jours**, coût A 17 100 £),
seed5678 station164 → ligne55 le 19/12/1974 (**885 jours**, coût A 26 893 £).
Le capital A historique finalement réemployé dans ces trois trajectoires
est **147 572 £**. La graine999 n'appartient pas à ce suivi de cinq ans ;
l'avenir de sa station58 après 1972 reste **inconnu**.

Contrôle de reproductibilité : **216/216 snapshots mensuels des deux
compagnies**, sur ces trois graines jusqu'au 01/12/1972, sont strictement
identiques entre `r2` 6×3 et la campagne prolongée 3×5 ; les cinq premières
constructions et leur identité physique sont aussi identiques. Cette
égalité permet d'interpréter les années 1973–74 comme une continuation
des mêmes trajectoires mesurées, dans ces trois graines.

| Seed / ligne | Groupe STNN | Coût A historique | Nouveau chantier : coût réel | Intervalles complets / partiels | Profit net VEHS, seuls intervalles complets |
|---|---|---:|---:|---:|---:|
| 1234 / 18 | `air|34,92` | 17 415 £ | 66 083 £ | 28 / 0 | +92 850,656249 £ |
| 2026 / 7 | `air|17,39` | 17 219 £ | 86 221 £ | 38 / 4 | +136 239,054688 £ |
| 2026 / 18 | `air|45,52` | 25 560 £ | 61 523 £ | 22 / 1 | +39 165,148436 £ |
| 2026 / 24 | `air|64,106` | 17 100 £ | 61 523 £ | 13 / 1 | +18 556,585938 £ |
| 5678 / 41 | `air|2,91` | 26 009 £ | 38 964 £ | 24 / 1 | +92 343,437500 £ |
| 5678 / 43 | `air|32,74` | 17 376 £ | 38 964 £ | 23 / 2 | +42 158,507813 £ |
| 5678 / 55 | Station164, groupe non encore visible | 26 893 £ | 38 964 £ | 0 / 0 | **indisponible** |

Le décodeur constate donc **six groupes physiques réconciliés**, 163
checkpoints sur des lignes actives, **148 intervalles mensuels complets et
9 partiels**. L'addition des six sommes d'intervalles complets est
**+421 313,390624 £**, mais ne forme aucun résultat de cohorte exhaustif :
les mois initiaux, intervalles partiels, éventuelles ventes d'avions et
mois après le dernier snapshot ne sont pas extrapolés. Le groupe de la
ligne55 n'a pas de checkpoint après sa construction du 19 décembre 1974.
Tous les **7/7 coûts des nouveaux chantiers** sont appariés sans ambiguïté
depuis `AIR_FINANCE_TRY outcome=built reason=OK`, **392 242 £ au total**.
Ajoutés analytiquement aux **147 572 £** de coût historique d'A, ils
représentent **539 814 £ de dépenses de construction et de conservation
attribuables à ces sept premières lignes**. La somme est descriptive : les
coûts d'A ont été engagés à une date antérieure, le calcul n'est ni un solde
de caisse après remboursement ni un ROI ou un profit de réseau. La sous-cohorte
des cinq lignes initiales coûte 291 755 £ de nouveaux chantiers, plus
103 579 £ d'A historiques, soit 395 334 £ de capital déjà dépensé.
Les modèles `C121_BUILD.actual_profit` et `actual_revenue` représentent
encore des **prévisions ex ante** calculées au nombre d'avions réellement
achetés, et ne sont jamais confondus avec ces profits VEHS.

Artefacts : `results/air_orphan_profit_maturity_3x5_20261009_r1.json`,
`results/air_orphan_profit_maturity_3x5_20261009_r1_orphans.json`,
`results/air_orphan_profit_maturity_3x5_20261009_r1_line_profit.json`,
et, pour le 6×3, `results/air_orphan_profit_6x3_20261009_r2_line_profit.json`.
Les décodeurs et leurs fixtures indépendantes sont
`sweeps/analyse_air_orphan_profit.py`, `sweeps/test_analyse_air_orphan_profit.py`,
`sweeps/analyse_air_orphan_station_survival.py`,
`sweeps/test_analyse_air_orphan_station_survival.py`. La suite ciblée complète
est contrôlée avant clôture avec `git diff --check`.

**Interprétation :** la conservation après BFAIL préserve bien des actifs
physiques, dont plusieurs alimentent plus tard des lignes avec bénéfices
d'exploitation observés sur des périodes admissibles. Ces bénéfices ne
remboursent pas automatiquement les anciens chantiers, ne donnent pas une
valeur de liquidation et ne prouvent pas que conserver A batte l'option
de le démolir, d'utiliser un autre hub ou d'investir ailleurs au même moment.
Les trois graines sont sélectionnées pour leur exposition, ne représentent
pas une qualification économique. Aucun réglage ni seuil de marge modifié,
aucune porte A/B V102 ouverte. Piste économique suivante : contrefactuel
de coût d'opportunité d'une conservation d'aéroport A au point de décision,
avec suivi du coût réel de la nouvelle ligne et profit de réseau apparié.
