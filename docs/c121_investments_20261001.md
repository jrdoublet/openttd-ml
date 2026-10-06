# C121 — rectification des témoins et autre piste (01/10/2026)

Demandes : « essaie autre chose », puis analyser le blocage « Reading changed
files in openttd-ml » et reprendre. Aucun changement économique ni de défaut.

## Lecture globale des changements

Git non disponible dans la session, `.git` absent à la racine examinée. Le
dossier se trouve sous OneDrive ; ses entrées portent l'attribut `ReparsePoint`.
Ce sont des facteurs possibles de lenteur, pas une mesure de la cause interne
du blocage VS Code. Aucun réglage global ni synchronisation modifiés.
Contournement appliqué : lectures de fichiers explicites et contrôles ciblés,
pas de lecture globale des changements ni de parcours récursif de `results/`.

## Défaut d'isolation confirmé

Dans OpenTTDLab installé, `run_experiments` construit `ai_copy_functions` avec
`ai_name: ai_copy` (autour des lignes251–255). Quatre appels `local_folder`
portant tous le nom `OpexAI` au sein d'une même invocation ne chargent donc pas
quatre versions distinctes. Les paramètres par expérience restent séparés,
mais la dernière source de ce nom remplace les précédentes.

Les dix témoins théoriques contiennent réellement la sonde :

| Graine | Événements POSTBUILD dans `c115` | Dans `c121` |
|---|---:|---:|
| 42 | 921 | 2 067 |
| 100 | 1 715 | 1 719 |
| 999 | 1 004 | 2 944 |
| 1234 | 721 | 2 447 |
| 5678 | 887 | 4 830 |

Le filtre de perturbation annoncé est retiré. Les nombres de profit restent
ceux des parties instrumentées, pas des témoins sans sonde. Un hash identique
des copies préparées ne certifie pas que le moteur les a chargées distinctement.

**Preuves préservées :** `recovery_report_r1.json` n'est ni modifié ni remplacé.
`results/c121_postbuild_latency/exposure_20261001_r1/identity_investments_correction_r1.json`
contient le reçu correctif, le SHA256 de l'ancien rapport et les hashes vérifiés
des40 artefacts originaux. Aucun rejeu.

**Correction :** `diag_c121_postbuild.py` exécute désormais une invocation de
chargement par bras (graines parallèles, au plus trois workers). Contrôle
positif et négatif de la sonde attribuée à Opex dans chaque log. Le lecteur
de récupération refuse également les comparaisons si ses contrôles échouent.
Tests du regroupement et de contamination/manque/mauvais propriétaire ajoutés.
Validation moteur **non exécutée** : aucun nouveau budget de campagne consommé.

## Autre piste : service valorisé contre service effectivement acheté

`inspect_c121_investments.py` relit le groupe nommé `c121` sur les cinq graines,
sans doubler les observations avec `c121_trace`, ni sélectionner un résultat
favorable. Cohorte instrumentée, portée descriptive uniquement.

| Graine | Événements C121_BUILD | Achat à N=1 | `decision_n > actual_n` | `target_n > actual_n` |
|---|---:|---:|---:|---:|
| 42 | 26 | 26 | 1 | 26 |
| 100 | 19 | 19 | 0 | 19 |
| 999 | 20 | 20 | 1 | 20 |
| 1234 | 18 | 18 | 0 | 18 |
| 5678 | 12 | 12 | 4 | 12 |
| Total descriptif | 95 | 95 | 6 | 95 |

Pas de données manquantes sur ces trois compteurs. `target_n` vaut2–12 : c'est
une cible du modèle, **pas une preuve de demande non servie**. Seulement6/95
événements présentent un écart entre taille de décision et achat initial.
Cela ne démontre ni classement erroné dans les89 autres cas ni manque de caisse.

### Trois niveaux à ne pas confondre

1. `OpexC121MeasureBuiltEconomics` mesure bien les capacités du véhicule et N
   construit, mais appelle ensuite `OpexC121AirEconomics` pour calculer
   `actual_revenue`/`actual_profit`. Ce sont des **prévisions avec le matériel
   construit**, pas des revenus/profits observés ultérieurement.
2. `_resizeAirFleets`, lorsque C121 est sous cible et stock-growth OFF, exige
   âge≥2, `lastProfit > 0`, puis deux années de différence après un renfort.
   Ce verrou est constaté dans le code ; les95 logs d'achat ne prouvent pas
   que95 lignes attendaient continuellement un renfort rentable/finançable.
3. `OpexC121ObserveLineMarginal` calcule une différence de profit/revenu avant
   et après renfort, par avion ajouté. Ce n'est pas un contrefactuel causal :
   concurrence, demande et note des gares peuvent changer simultanément.

### Suite utile, sans réarmer une stratégie rejetée

Le bootstrap reste de côté. La piste retenue est la **cohérence du service
valorisé à l'élection avec N réellement construit et le délai de croissance**.
Avant de changer un score : relier une même ligne à son élection, son achat,
ses renforts et une année réalisée complète ; mesurer les refus de croissance
et l'état de demande/financement au même moment. Les checkpoints agrégés actuels
ne permettent pas cette attribution par ligne. Ne pas ajuster un coefficient
global à partir des profits société ni acheter automatiquement la cible2–12.
Stock-growth, two-aircraft et priorité territoriale rejetés restent désarmés.

Validation de cette reprise : **25 tests ciblés réussis** (lecteurs, isolation,
collecteur), pas une suite complète ni un smoke moteur. Aucun gain économique
revendiqué, C115 protégé et C121 OFF par défaut.