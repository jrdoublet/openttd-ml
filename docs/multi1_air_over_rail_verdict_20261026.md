# MULTI-1 — deuxième levier AIR avant RAIL : NO-GO non exposé (26 octobre 2026)

**Statut : `NO-GO_NON_EXPOSE` pré-enregistré, sans porte A/B.** Le pré-enregistrement
[`multi1_air_over_rail_prereg_20261026.md`](multi1_air_over_rail_prereg_20261026.md)
a été publié sous `65c83dfc` avant l'implémentation `f3df60f5`. Le correctif
instrumental `7b917f4e` ajoute la date civile au log de promotion, sans
modifier les seuils. Réglage `multi1_air_over_rail=0` aux quatre profils :
`1=shadow`, `2=ON`, uniquement 1971–1973 et multimodal ; protection C77 et
AIR financé à `fundScore ≥80 %`, `profitAnnual ≥70 %` de la tête RAIL non
préparée (rangs 1–7).

## Validation technique

- Suite complète **2 924 tests OK**, 5 ignorés et 2 échecs attendus, `git diff
  --check` propre après le correctif daté. Les 58 réglages historiques
  restent inchangés, le registre courant contient 71 réglages ; aucun état
  persistant ajouté. Le niveau 0 court-circuite le nouveau sélecteur.
- Smoke source finale `multi1_airrail_smoke_1x1_20261026_r2` : graine 42,
  1970, 1 an, OFF/ON, **2/2 parties complètes**, sans erreurs moteur/Squirrel ;
  Δ profit ON−OFF nul attendu hors fenêtre. Le smoke initial avant ajout de
  la date (`multi1_airrail_smoke_1x1_20261026`) était également sain.
- Save/Load source finale `multi1_airrail_saveload_20261026_r2.json` : graine
  42, 1970–1971 puis reprise de **1971-01-01** pour une année, **25**
  sauvegardes phase A et **13** phase B ; `LOAD_RECONCILE` positif, aucun
  indicateur d'erreur moteur/Squirrel. Le harnais solo rapporte une compagnie
  fantôme inerte après recharge : ceci prouve la reprise, pas une égalité
  économique same-world. Le test initial avant datation est conservé sous
  `multi1_airrail_saveload_20261026.json`.

## Exposition 5×5 et attribution physique

Campagne `results/multi1_airrail_exposure_5x5_20261026.{json,jsonl,manifest.json}`
et journaux sous `results/multi1_airrail_exposure_5x5_20261026_engine/`.
**Cinq graines pré-enregistrées 42,100,7,999,2026 × 1970–1974**, même source
gelée SHA **`21fa41b7…`**, `--probes 258 --script-debug` symétriques, mêmes
autres défauts et AAAHogEx. **10/10 parties, 5/5 paires complètes**, 0 arrêt
moteur ; Docker unique, dix workers, limite 10 CPU/8 Go.

| Graine | Promotions ON | Couples AIR distincts promus | `AIR_BUILD` dans les 90 jours sur même couple | Critère attribuable |
|---|---:|---:|---:|---|
| 42 | 0 | 0 | 0 | non |
| 100 | 3 | 1 | 0 | non |
| 7 | 0 | 0 | 0 | non |
| 999 | 2 | 2 | **2** | **oui** |
| 2026 | 0 | 0 | 0 | non |
| **Total** | **5** | **3** | **2** | **1/5 graines** |

Attributions vérifiables dans `multi1_air_over_rail_seed999_r0.log` :
**19 janvier 1972** promotion AIR `src=58684,dst=36811` → `AIR_BUILD`
**20 janvier** (`line=42`, 1 jour) ; **28 juin 1972** promotion AIR
`src=15901,dst=36811` → `AIR_BUILD` **29 juin** (`line=56`, 1 jour).
La graine 100 a trois promotions successives du même couple
`30443→61075` les **4, 5 et 8 novembre 1972**, sans `AIR_BUILD` de ce
couple dans les 90 jours. Ce décompte est par **graine** : cinq événements
sur deux graines ne valent pas cinq mondes exposés. Il atteste une sélection
modifiée et deux constructions temporellement associées, sans prouver le
profit contrefactuel de ces avions.

Précondition 1 **≥3/5 graines ayant une promotion : seulement 2/5**.
Précondition 2 **≥2/5 graines avec paire AIR construite dans les 90 jours :
seulement 1/5**. Les deux échouent ; **A 40×5 et B 20×10 interdites** pour
ce réglage, sans allègement a posteriori.

Comparaison économique purement descriptive de l'exposition (5 paires) :
**ON−OFF −241 567,6 £/an** à fin 1974 (1 victoire/4 défaites), Wilcoxon
bilatéral **p=0,1875**, IC95 bootstrap **[−443 416,2 ; −35 160,4] £/an** ;
garde `company_value(ON)/company_value(OFF)` **0,940213**, soit **−5,98 %**
et donc en dessous de 0,95. La campagne est un diagnostic d'exposition
avec `probes=258`, **pas la porte A** prévue en `probes=2` ; une
différence de trajectoire non attribuable subsiste sur les graines sans
promotion, donc ne pas convertir ces valeurs en gain/perte causal du levier.

**Verdict définitif de cette variante : `NO-GO_NON_EXPOSE`.** Conserver le
défaut `0`, ne pas rejouer sa porte A/B ni modifier ses seuils, et conserver
les données brutes. H2 n'est pas démontrée comme cause dominante : les
arbitrages AIR contre une tête RAIL admissible sont trop rares dans ces
cinq mondes. Suite MULTI-1 : étudier en amont le vivier ROAD et la concurrence
modale d'AAAHogEx observée dans l'analyse initiale, sous troisième fiche de
pré-enregistrement distincte.
