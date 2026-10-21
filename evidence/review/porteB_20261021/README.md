# Campagnes du 21 octobre 2026 — publication des résultats achevés (6 campagnes)

## Première série (V294all, adapt400 et V297)

Trois campagnes OpenTTD 15.3 / OpenGFX 7.1, démarrées en 1970, carte 256×256, sur dix ans (dernier relevé **1979-12-01**). Chaque graine donne un duel partagé indépendant `OpexAI` contre `AAAHogEx` pour la référence puis pour la variante. La métrique primaire est le `profit_year` terminal **OpexAI variante − OpexAI référence**, en £/an ; il ne s'agit ni du profit cumulé ni de l'écart de score face à AAAHogEx.

| Campagne | Paires / parties terminées | Profit annuel Opex réf. → variante (£/an) | Δ profit_year moyen (£/an) | V/D/E | IC95 bootstrap du Δ (£/an) | Valeur Opex, ratio des moyennes | Verdict enregistré |
|---|---:|---:|---:|---:|---:|---:|---|
| `v294all_adapt400_complet_1970_40x10_pc_20261021` (multimodal) | 40/40 ; 80/80 | 3 997 245,925 → 4 066 519,000 | **+69 273,075** | 23/17/0 | [−56 437,175 ; +196 136,675] | **+3,710800 %** | `diagnostic_only` |
| `adapt400_porteB_20x10_pc_20261021` (multimodal) | 20/20 ; 40/40 | 3 754 205,350 → 3 812 560,650 | **+58 355,300** | 11/9/0 | [−99 117,800 ; +228 421,250] | **+1,162796 %** | `pass` (non-érosion) |
| `v297_porteB_20x10_pc_20261021` (rail seul) | 20/20 ; 40/40 | 1 419 715,650 → 1 375 373,300 | **−44 342,350** | 10/10/0 | [−139 668,850 ; +51 858,700] | **+2,829611 %** | `pass` (non-érosion) |

La valeur est mesurée par `company_value` et sa variation est celle du **ratio des moyennes** OpexAI. Les trois campagnes ont `failed_runs=[]`, toutes les parties sont `complete`, la couverture terminale est complète et 0 dénominateur de valeur est écarté. IC bootstrap : 20 000 tirages, graine 0. Aucun nouveau banc n'a été lancé pour cette publication.

**Portée des verdicts.** Les deux portes B passent la règle `non_erosion` : la borne haute de l'IC95 du Δ `profit_year` reste au moins nulle, et la garde de valeur de −5 % tient. Cela n'établit pas un gain à dix ans. V297 en particulier a un delta moyen négatif. Le 40×10 V294all, malgré 40 paires complètes, est marqué `diagnostic_only` par le harnais car la qualification de porte B exige exactement 20 graines indépendantes. Ne pas convertir ce résultat en verdict `pass` ni attribuer isolément le gain à l'un de ses huit réglages.

Les modes diffèrent : V294all et adapt400 utilisent rail, route et air, alors que V297 désactive air/route/eau sur OpexAI et AAAHogEx. Leurs niveaux absolus de profits ne constituent donc pas une comparaison de variantes sur protocole identique. L'écart `profit_year` OpexAI − AAAHogEx au terminal est de **−3 329 427,350 £/an** pour V294all, **−3 385 934,600 £/an** pour adapt400, et **−3 033 255,800 £/an** pour V297 (chacun sur les duels de sa variante).

| Campagne | Réglages de la variante par rapport à sa référence | Git source figé | SHA256 du bundle |
|---|---|---|---|
| V294all | `v294_rail_aaa_costs=1`, `v294_rail_bridge_len=20`, `v294_rail_dist_decouple=200`, `v294_rail_reverse_probe=300`, `v294_rail_slope_engine=1`, `v294_rail_weight_adapt=400`, `v294_rail_weight_pct=200`, `v295_astar_fast=1` | `a4e7fcf957e602a2def6b72311e65a4464ecc29d` | `2e320aa6980f155a86ae3aa06568d1858cefe793c157468468f54265cb9e43c6` |
| adapt400 | `v294_rail_weight_adapt=0` → `400` | `59024aad2899d295b5ce4c81513625dfd959410f` | `2e320aa6980f155a86ae3aa06568d1858cefe793c157468468f54265cb9e43c6` |
| V297 | `v297_rail_roi_floor=400`, modes hors rail désactivés sur les deux bras | `b5bf3ac2900143d454ca3999366ec9fb92c89616` | `40dd4e11dfb90cb6711d31289ffc57b3497b65fe596a6362a8389612ebd32a9e` |

Les fichiers `.json` sont les rapports détaillés originaux avec les 40 ou 20 lignes de comparaison appariée et les résultats par graine ; les `.manifest.json` sont les manifestes originaux. Les fichiers `.jsonl.gz` (si présents) sont les checkpoints JSONL originaux compressés sans transformation. Les chemins `/work/results/...` inscrits dans les sources identifient leur emplacement lors de l'exécution ; le répertoire de cette publication est leur archive autonome. Le fichier `SHA256SUMS.json` donne la taille et l'empreinte SHA-256 des originaux et des copies archivées pour vérification.

Les archives de checkpoints contiennent **19 200 lignes JSONL** pour V294all, **9 600** pour adapt400 et **9 600** pour V297. Leurs originaux mesurent respectivement 165 975 116, 82 134 057 et 94 020 034 octets ; les archives gzip mesurent 13 873 030, 6 921 798 et 7 414 768 octets. Les empreintes de tous les originaux sont enregistrées dans l'index. Pour vérifier les copies et leur décompression, sans lancer OpenTTD :

```sh
python -X utf8 evidence/review/porteB_20261021/verify_publication.py
```

La campagne V296a est **hors périmètre**. Le script de lancement de la deuxième série est maintenant inclus dans la branche de publication, avec les références explicites et les arrêts sur erreur corrigés.

## Deuxième série (finpartie, V296clean, V301) — publication complémentaire

Les trois autres campagnes du **21 octobre 2026** sont achevées, en **1970–1979**, carte 256×256, 20 graines et 10 années, 40 parties par campagne. Aucun échec (`failed_runs=[]`), couverture terminale complète, 20 paires appariées sur 20, aucune partie manquante. La métrique et la convention de delta sont les mêmes que dans la première série.

| Campagne et mode | Δ profit_year moyen (£/an) | Δ % du ratio des moyennes | V/D/E | IC95 bootstrap (£/an) | p Wilcoxon | Valeur Opex, ratio des moyennes | Verdict harnais |
|---|---:|---:|---:|---:|---:|---:|---|
| `finpartie_porteB_20x10_pc_20261021` (partie complète) | **+407 477,75** | **+10,833921 %** | 17/3/0 | [+247 585,85 ; +567 803,95] | **0,000168** | +1,286376 % | `pass` |
| `v296clean_porteB_20x10_pc_20261021` (partie complète) | +144 329,10 | +3,824396 % | 12/8/0 | [−40 733,75 ; +324 727,50] | 0,142906 | +2,636097 % | `pass` |
| `v301_porteB_20x10_pc_20261021` (multimodal, sous adapt400) | +42 401,45 | +1,119791 % | 10/10/0 | [−115 608,80 ; +205 500,00] | 0,756166 | +0,551597 % | `pass` |

**Portée :** `pass` ne signifie **pas** gain significatif sous `non_erosion`. Cette porte B rejette un candidat uniquement si la borne haute de l'IC95 bootstrap du delta de profit tombe sous zéro ou si la garde de valeur (−5 %) échoue. `finpartie` possède un gain positif avec IC95 entièrement positif ; V296clean et V301 restent incertains à dix ans, même si la règle accepte leur absence d'érosion démontrée. Le seuil indicatif de +4 % du profit de référence est reporté, pas une condition de réussite de cette porte.

| Campagne | Intervention de la variante | Git de l'IA figé | SHA256 du bundle |
|---|---|---|---|
| finpartie | `v249_statue=0` → `2` et `v292_hq_hub=0` → `1` | `7352ba3693c7727425ece77be8809633acd3ecb8` | `fbc05626b98e0f0b241fcff95391d893380b31a911f1983d3a605f94be0730e0` |
| V296clean | `v296_rail_batch_build=0` → `1` et `v296_astar_native=0` → `1` | `46afe330666b40b68e9bc0c1219b844e7ac0d527` | `eacc85e178333d749da1babf33751b5c540fd2eadd59bb39be7e772134fe9e77` |
| V301 | `v301_notrain_fix=0` → `15`, avec `v294_rail_weight_adapt=400` sur les deux bras | `7353241aa3bbb13ab66f2a95c35e1983ac035b9a` | `a2f8a16d579c30687a9df1f7d264a0051d0a170ce855ecd52b60c74a6201e831` |

**Reproductibilité et incident BaNaNaS :** finpartie a tourné avec Git propre. Les deux autres campagnes ont été exécutées sur leur IA non modifiée, mais le fichier de préparation `sweeps/campaign_freeze.py` était modifié localement (Git `dirty=1`) pour contourner une réponse HTTP 502 de BaNaNaS. Ce contournement récupère les quatre archives de bibliothèques depuis la campagne finpartie déjà figée et vérifie pour chacune le nom, la taille et l'empreinte SHA-256 attendue ; il ne change aucune règle d'IA ni aucune partie OpenTTD. Le diff exact `offline_bananas_cache_patch.diff` est joint. Les bundles et manifestes originaux identifient les sources effectivement employées ; leur empreinte ne doit pas être substituée par celle d'un checkout Git propre.

Les rapports `.json`, manifestes `.manifest.json` et checkpoints compressés `.jsonl.gz` de cette deuxième série sont conservés dans ce même dossier, avec empreintes de chaque copie, empreintes des fichiers JSONL originaux et comptes de lignes dans `SHA256SUMS.json` (9 600 lignes JSONL par campagne). L'outil de vérification couvre désormais **six campagnes : 140 paires complètes, 280 parties** :

```sh
python -X utf8 evidence/review/porteB_20261021/verify_publication.py
```

Les profits absolus et différences OpexAI − AAAHogEx sont dans les rapports originaux ; les deltas du tableau sont **variante OpexAI − référence OpexAI**, pas une comparaison directe à AAAHogEx. Les campagnes finpartie et V296clean ont des références différentes des campagnes précédentes, et V301 réutilise adapt400 comme référence : ne pas interpréter la différence entre leurs niveaux de profit comme un duel entre candidats.
