# Statistiques du dépôt OpexAI (V260)

Rapport automatisé et reproductible généré par `sweeps/repo_stats_opexai.py`.

## 1. Tableau par langage

Périmètre : fichiers suivis sous `ai/OpexAI/` (répertoires de tests exclus s'il en existe).

| Langage | Fichiers | Lignes vides | Commentaires | Code | Total |
|---|---:|---:|---:|---:|---:|
| Squirrel | 76 | 2 860 | 5 802 | 44 853 | 53 515 |
| Markdown | 1 | 14 | 0 | 155 | 169 |
| **SUM** | **77** | **2 874** | **5 802** | **45 008** | **53 684** |

## 2. Couverture de l'API NoAI (OpenTTD 15)

- **Source officielle de l'API 15** :
  - Liaisons Squirrel générées d'OpenTTD 15.3 (`SquirrelExport.cmake`, APIUC=AI, `ai_*.sq.hpp` et `ai_controller.sq.hpp`), répertoriées dans `docs/noai_api_15.3.tsv` (1 167 éléments).
  - En-têtes C++ officiels `src/script/api/script_*.hpp` du tag `15.0` / `15.3` (https://github.com/OpenTTD/OpenTTD/tree/15.3) archivés dans `results/api15/`.
- **Éléments d'API utilisés** : **488 / 1 167** (41.82 %)
- **Nombre total d'appels / références d'API** : **6 439**

### Ventilation par catégorie d'API

| Catégorie | Utilisés | Total API | Couverture (%) | Appels | Part des appels (%) |
|---|---:|---:|---:|---:|---:|
| Méthodes statiques | 274 | 528 | 51.89 % | 4 387 | 68.13 % |
| Méthodes d'instance | 55 | 91 | 60.44 % | 1 096 | 17.02 % |
| Constantes & Enums | 133 | 434 | 30.65 % | 769 | 11.94 % |
| Classes (constructeurs/refs) | 26 | 114 | 22.81 % | 187 | 2.90 % |
| **Total** | **488** | **1 167** | **41.82 %** | **6 439** | **100.00 %** |

### 20 classes NoAI les plus utilisées

| Rang | Classe | Appels | Part des appels (%) | Éléments utilisés | Couverture classe (%) |
|---:|---|---:|---:|---:|---:|
| 1 | `AIMap` | 896 | 13.92 % | 7 / 13 | 53.8 % |
| 2 | `AIDate` | 544 | 8.45 % | 7 / 8 | 87.5 % |
| 3 | `AIVehicle` | 481 | 7.47 % | 36 / 74 | 48.6 % |
| 4 | `AIList` | 411 | 6.38 % | 18 / 37 | 48.6 % |
| 5 | `AITile` | 387 | 6.01 % | 39 / 90 | 43.3 % |
| 6 | `AIRail` | 348 | 5.40 % | 36 / 63 | 57.1 % |
| 7 | `AIStation` | 340 | 5.28 % | 17 / 33 | 51.5 % |
| 8 | `AICompany` | 293 | 4.55 % | 22 / 83 | 26.5 % |
| 9 | `AIController` | 272 | 4.22 % | 7 / 10 | 70.0 % |
| 10 | `AIAirport` | 197 | 3.06 % | 22 / 33 | 66.7 % |
| 11 | `AITown` | 169 | 2.62 % | 22 / 58 | 37.9 % |
| 12 | `AIEngine` | 163 | 2.53 % | 22 / 29 | 75.9 % |
| 13 | `AIRoad` | 136 | 2.11 % | 24 / 54 | 44.4 % |
| 14 | `AILog` | 132 | 2.05 % | 3 / 4 | 75.0 % |
| 15 | `AIEventEnginePreview` | 126 | 1.96 % | 7 / 10 | 70.0 % |
| 16 | `AIOrder` | 122 | 1.89 % | 22 / 84 | 26.2 % |
| 17 | `AIError` | 111 | 1.72 % | 10 / 38 | 26.3 % |
| 18 | `AICargo` | 102 | 1.58 % | 11 / 39 | 28.2 % |
| 19 | `AIEventStationFirstVehicle` | 97 | 1.51 % | 3 / 4 | 75.0 % |
| 20 | `AIEventDisasterZeppelinerCleared` | 91 | 1.41 % | 1 / 3 | 33.3 % |

## 3. Méthodologie et limites de l'analyse

1. **Nettoyage préalable** :
   - Les blocs de commentaires `/* ... */`, les commentaires de fin de ligne `//` et `#`, ainsi que les chaînes littérales `"..."` et `'...'` sont purgés avant l'analyse statique des symboles afin d'éliminer tout faux positif.
2. **Motifs d'appels identifiés** :
   - Appels statiques et constantes : motif `AIXxx.Yyy`.
   - Instanciations directes : motif `AIXxx(` ou référence de classe seule sans point.
   - Méthodes d'instance : motif `.Methode(` (ex: `.Valuate(`, `.Count(`).
   - Fonctions `AIController` : motif sans préfixe (`Sleep(`, `import(`).
3. **Limites assumées** :
   - En Squirrel (langage dynamiquement typé), une méthode d'instance comme `.Valuate(` est comptabilisée sans inférence de type complète de l'objet hôte.
   - Les déclarations du fichier `info.nut` (métadonnées `AIInfo`) ne font pas partie de l'API NoAI runtime et ne sont pas incluses dans les 1 167 éléments.

---
*Régénération : `python3 sweeps/repo_stats_opexai.py`*
