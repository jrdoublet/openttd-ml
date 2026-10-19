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
- **Éléments d'API utilisés** : **466 / 1 167** (39.93 %)
- **Nombre total d'appels / références d'API** : **5 682**

### Ventilation par catégorie d'API

| Catégorie | Utilisés | Total API | Couverture (%) | Appels | Part des appels (%) |
|---|---:|---:|---:|---:|---:|
| Méthodes statiques | 274 | 528 | 51.89 % | 4 387 | 77.21 % |
| Méthodes d'instance | 33 | 91 | 36.26 % | 339 | 5.97 % |
| Constantes & Enums | 133 | 434 | 30.65 % | 769 | 13.53 % |
| Classes (constructeurs/refs) | 26 | 114 | 22.81 % | 187 | 3.29 % |
| **Total** | **466** | **1 167** | **39.93 %** | **5 682** | **100.00 %** |

### 20 classes NoAI les plus utilisées

| Rang | Classe | Appels | Part des appels (%) | Éléments utilisés | Couverture classe (%) |
|---:|---|---:|---:|---:|---:|
| 1 | `AIMap` | 896 | 15.77 % | 7 / 13 | 53.8 % |
| 2 | `AIDate` | 544 | 9.57 % | 7 / 8 | 87.5 % |
| 3 | `AIVehicle` | 481 | 8.47 % | 36 / 74 | 48.6 % |
| 4 | `AITile` | 387 | 6.81 % | 39 / 90 | 43.3 % |
| 5 | `AIRail` | 348 | 6.12 % | 36 / 63 | 57.1 % |
| 6 | `AIStation` | 340 | 5.98 % | 17 / 33 | 51.5 % |
| 7 | `AICompany` | 293 | 5.16 % | 22 / 83 | 26.5 % |
| 8 | `AIController` | 272 | 4.79 % | 7 / 10 | 70.0 % |
| 9 | `AIList` | 263 | 4.63 % | 15 / 37 | 40.5 % |
| 10 | `AIAirport` | 197 | 3.47 % | 22 / 33 | 66.7 % |
| 11 | `AITown` | 169 | 2.97 % | 22 / 58 | 37.9 % |
| 12 | `AIEngine` | 163 | 2.87 % | 22 / 29 | 75.9 % |
| 13 | `AIRoad` | 136 | 2.39 % | 24 / 54 | 44.4 % |
| 14 | `AILog` | 132 | 2.32 % | 3 / 4 | 75.0 % |
| 15 | `AIOrder` | 122 | 2.15 % | 22 / 84 | 26.2 % |
| 16 | `AIError` | 111 | 1.95 % | 10 / 38 | 26.3 % |
| 17 | `AICargo` | 102 | 1.80 % | 11 / 39 | 28.2 % |
| 18 | `AIAccounting` | 89 | 1.57 % | 2 / 3 | 66.7 % |
| 19 | `AIIndustry` | 76 | 1.34 % | 10 / 25 | 40.0 % |
| 20 | `AIEvent` | 64 | 1.13 % | 19 / 37 | 51.4 % |

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
