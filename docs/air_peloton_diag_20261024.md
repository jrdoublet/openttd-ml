# AIR-PELOTON-1 — diagnostic des départs AIR (24 octobre 2026)

## Verdict

**Surcapacité dominante, avec un effet « peloton » secondaire mais mesurable.** Après un départ rapproché depuis la même gare, les avions de lignes à deux appareils ont une charge médiane de **5,0 %**, contre **16,6 %** après un intervalle long. Mais le supposé « meneur » n'est généralement **pas plein** : même les départs espacés chargent peu. Il ne s'agit donc ni de départs parfaitement réguliers, ni d'un simple enchaînement avion plein → avion vide : les lignes sont déjà peu remplies, et le rapprochement des départs aggrave le problème.

## Source et protocole

- Travail isolé dans `../wt_peloton`, checkout détaché de `origin/air-peloton-1`, commit `34f3eff8b00b29b5568406cbcecff91310355fee`. Arbre Git propre au départ (`dirty=0`) ; `ai/AAAHogEx-115` copié depuis le dépôt principal car absent. Aucun réglage métier ni code modifié.
- Banc de référence seule `peloton_diag_5x5_20261024` : `OpexAI[probes=258]`, graines **42, 100, 7, 999, 2026**, 1 répétition, cinq ans (1970–1974), carte 256×256, duel contre AAAHogEx-115, journal `--script-debug` ; Docker local 10 CPU, 8 Gio, 5 workers, un seul conteneur.
- Commande : `python3 -X utf8 sweeps/run_c66_reference.py --campaign peloton_diag_5x5_20261024 --reference "OpexAI[probes=258]" --years 5 --repeats 1 --seeds 42 100 7 999 2026 --script-debug --cpus 10 --max-workers 5 --memory 8g`.
- Image `openttd-lab:latest`, SHA `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`. Source bundle SHA `4118fe455cea36a617888f26d0844d68a90324c7478b872a846d9237318ab98b`, manifeste SHA `c0e3f6c1a0a424e398f322c7490b1c371956f744a0f455d8c1414fc05c5f20ee`.
- **5/5 parties terminées, zéro run échoué et zéro erreur Squirrel détectée** : aucun message d'erreur du canal script ni trace de crash. Les `error=` dans les journaux sont des échecs de construction pris en charge. Tests `python3 -X utf8 -m unittest sweeps/test_air_peloton.py` : **11/11 OK**.
- Sources : `results/peloton_diag_5x5_20261024.json`, son manifeste, `results/peloton_diag_5x5_20261024_engine/reference_seed*_r0.log`. Analyse : `python3 -X utf8 sweeps/diag_air_peloton.py results/peloton_diag_5x5_20261024_engine --out results/peloton_diag_5x5_20261024_analysis.json`.

## Départs, écarts entre avions et charge

**10 497 départs**, dont **6 791 avec écart défini** depuis un autre avion de la même ligne au départ de la même gare. Charge = `load_pm/10` en pourcentage de capacité passagers, mesurée au premier échantillon C117 après départ (cadence deux jours). Le CV « groupé » est l'écart-type divisé par la moyenne des écarts de tous les départs du groupe ; le CV « annuel » est la médiane des CV calculés ligne par ligne et année par année.

| Avions dans la ligne | Départs | Écarts valides | Écart médian (jours) | CV groupé | CV annuel médian (lignes-années) | Charge médiane |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 3 762 | 177* | 171* | 0,786* | 0,383 (10)* | **9,0 %** |
| 2 | 4 818 | 4 697 | **37** | 0,933 | **0,558** (203) | **12,2 %** |
| 3 | 1 821 | 1 821 | **24** | 0,780 | **0,695** (46) | **10,9 %** |
| 4+ | 96 | 96 | **19** | 0,792 | non disponible (0) | **9,0 %** |

*Les 177 écarts de la catégorie « 1 avion » correspondent à des traces historiques possibles après réduction d'une flotte autrefois multiple : avec un seul avion, on ne peut pas mesurer le départ d'un suiveur. Ne pas interpréter le CV/écart de cette catégorie comme du peloton. La catégorie 4+ correspond uniquement à quatre avions (aucun 5+ observé) et n'a aucun résumé annuel achevé de cette taille.*

## Charge après écart court ou long

Les seuils sont calculés sur la **médiane des écarts de chaque graine et ligne**, toutes années confondues, avec rang reconstitué par gare : **court < ¼ médiane**, **long ≥ médiane**. Les écarts intermédiaires ne sont pas dans cette comparaison.

| Avions | Courts (n) | Charge médiane après court | Longs (n) | Charge médiane après long |
|---|---:|---:|---:|---:|
| 1 (historique, non pertinent) | 9 | 14,4 % | 117 | 20,0 % |
| **2** | **443** | **5,0 %** | **2 558** | **16,6 %** |
| **3** | **242** | **4,8 %** | **764** | **13,6 %** |
| 4+ | 15 | 4,3 % | 34 | 13,45 % |

**Robustesse :** parmi 105 groupes graine–ligne–gare ayant chacun ≥3 départs courts et ≥3 longs, **100** ont une charge médiane supérieure après un intervalle long ; différence médiane *intragroupe* **+8,2 points**. Le constat se retrouve sur les cinq graines (court/long en pourcentage, flottes ≥2) : 42 = **5,9 / 14,0**, 100 = **5,4 / 13,1**, 7 = **5,3 / 20,0**, 999 = **4,0 / 13,2**, 2026 = **4,0 / 18,6**.

## Départs chargés à moins de 10 %, par rang de peloton

Rang 1 = départ après intervalle non court ; rang 2 = premier départ après un intervalle court ; rang 3+ = suite de départs rapprochés. Les nombres entre parenthèses sont les effectifs observés, uniquement parmi les départs ayant un écart mesuré.

| Taille de flotte | Rang 1 | Rang 2 | Rang 3+ |
|---|---:|---:|---:|
| Ensemble (inclut résidus à 1 avion) | **39,1 %** (6 082) | **71,0 %** (689) | **75,0 %** (20) |
| 2 avions | 38,2 % (4 254) | 68,8 % (442) | 100 % (1) |
| 3 avions | 42,0 % (1 579) | 75,9 % (224) | 72,2 % (18) |
| 4+ avions | 50,6 % (81) | 85,7 % (14) | 100 % (1) |

Les rares cas de rang 3+ et les 96 départs en flotte de quatre avions sont insuffisants pour établir une loi robuste propre à ces catégories.

## Interprétation, limites et suites

- **Verdict imposé « peloton ou surcapacité » : surcapacité**, avec effet peloton réel et quantifié. Un suiveur court transporte significativement moins de passagers que le même type de départ après un long délai ; mais le premier ne remplit généralement pas son avion non plus. Une politique qui ne ferait qu'écarter les départs pourrait ne pas résoudre le dimensionnement excessif.
- Le chronométrage C117 est échantillonné tous les deux jours et observe les changements d'ordres, pas les instants exacts de décollage ou l'espacement spatial des avions ; la charge est elle aussi un proxy post-départ.
- Les tailles de flotte changent au fil des cinq ans. Les médianes par ligne et CV groupés mélangent des phases hétérogènes ; les lignes de 1 avion ont des écarts résiduels, les lignes 4+ un faible effectif. Il s'agit d'une corrélation descriptive, pas d'une preuve causale d'une régulation de cadence.
- **Aucune comparaison économique ON/OFF**, aucun changement de défaut ni adoption proposée. Toute correction de cadence ou de flotte devra être testée séparément et qualifiée selon V102. Aucun commit ni push sur master.