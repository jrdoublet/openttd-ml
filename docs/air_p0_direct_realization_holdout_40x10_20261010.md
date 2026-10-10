# P0 AIR — Extension indépendante 40×10 (10/10/2026)

**Résultat : 80/80 parties saines, 40/40 paires exploitables ; `fail_primary`.**
L'essai `air_p0_direct_realization=1` affiche à dix ans une amélioration
moyenne non concluante sur le profit annuel et moins d'opcodes **partiels**
observés, mais ne démontre ni le gain requis, ni une équivalence économique,
ni la neutralité du CPU total. **Ne pas réintroduire la variante dans le code
actif.** Aucun changement Squirrel, commit ou push dans cette campagne.

## Hypothèse et protocole

La référence `OpexAI[air_p0_direct_realization=0]` conserve le modèle
historique ; `=1` applique aux nouveaux devis `hubsite` et `hubhub` la moyenne
directe des ratios annuels `c121RealizationPm` éligibles, sans seuil de deux
lignes, pseudo-observation ni lissage `0.75 + 0.25 * learned`, avec facteur
à froid 1,0 et garde de double correction C70/C82 lorsque le facteur
est non neutre. Les bras `newpair`, flotte et les autres coefficients
historiques ne sont pas remplacés : notamment, **104 %, MAIL15, 50/50 et
C70 ne disparaissent pas du code livré**. Le prototype ON n'existe plus
que dans le bundle archivé, après retrait du code actif lors du 40×5.

Campagne valide :
`air_p0_direct_realization_holdout_40x10_20261010_r2`, 40 nouvelles graines,
10 années (1970–1979), une répétition, deux bras par graine. Tirage
`random.Random(20261011)` et `randrange(1, 2**31)`, en écartant les graines
des deux précédentes campagnes 40×5 et les doublons : **0 recouvrement sur
les 80 graines antérieures**. Ordre et valeurs des graines dans le manifeste ;
aucun tri sur les résultats. Harnais `frozen_harness.py` exécuté directement
depuis le bundle original ; aucun fichier du bundle n'a été modifié.

| Élément immuable / runtime | Référence |
|---|---|
| Bundle source (SHA-256) | `061096c0b5b7cb90cbb8b0a1a162950e97209188c8783b8dc3ee7287e291c5a6` |
| Manifeste r2 (SHA-256) | `59d341af3eb9676a1353a9fe21572ff0db1ae83357118df92440b8be22d2d7df` |
| Image Docker (ID) | `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` |
| Limites | 10 CPU, 10 workers, RAM et swap à 6 GiB |
| Critère prédéfini | `gain_short`, `required_years=10`, `profit_year` terminal, gain utile +4 %, garde `company_value` −5 % |

**Incident de ressources exclu des statistiques :** le lancement `r1`
avait un plafond de 2 GiB ; Docker a enregistré plusieurs événements OOM,
et le processus a terminé en erreur avec seulement 12 journaux partiels.
Aucune donnée `r1` n'entre dans l'analyse. `r2` reprend les **mêmes graines,
settings, image et bundle** avec seulement 6 GiB de plafond ; sortie 0,
80 journaux et fichier JSON final, indicateurs
`comparison_complete`, `adoption_sample_complete`,
`metric_coverage_complete` tous vrais. Aucune autre campagne simultanée.

## Verdict économique à dix ans

Les chiffres comparent **ON − OFF dans OpexAI**, pas OpexAI contre
AAAHogEx (qui participe aux parties mais n'est pas le bras de ce test).

| Indicateur, fin 1979 | ON − OFF |
|---|---:|
| Profit annuel, delta moyen | **+74 488,8 £/an** |
| Médiane | +69 366 £/an |
| Gains / pertes / égalités | 22 / 18 / 0 |
| Écart type inter-graines | 319 521,5 £/an |
| IC95 bootstrap de la moyenne, 20 000 tirages | **[−21 695,825 ; +173 259,4] £/an** |
| Wilcoxon exact bilatéral | **p = 0,149902** |
| Valeur de compagnie, ratio des moyennes | **+0,625302 %** |
| Gain annuel minimal +4 % exigé | **+127 135,818 £/an** |
| Harnais | **`fail_primary`** |

La moyenne augmente, mais elle n'atteint pas les +4 % utiles ; le test
statistique n'est pas concluant et l'intervalle contient zéro. La garde
de valeur n'est pas déclenchée. L'absence de perte statistiquement
établie ne suffit pas à prouver une **équivalence** : aucun intervalle
d'équivalence ni marge bilatérale n'a été validé pour cela.

### Profil annuel du même panel 40×10

| Année | Delta moyen `profit_year` (£/an) | Médiane (£/an) | Gains / pertes / égalités | Profit AIR annuel, delta moyen (£) | Lignes AIR OFF / ON |
|---|---:|---:|---:|---:|---:|
| 1970 | +516,075 | 0 | 1 / 0 / 39 | +80,80 | 6,150 / 6,150 |
| 1971 | +3 849,825 | 0 | 2 / 0 / 38 | +6 856,56 | 20,775 / 20,850 |
| 1972 | −803,475 | 0 | 5 / 5 / 30 | −1 985,41 | 34,650 / 34,125 |
| 1973 | −10 882,7 | −535 | 19 / 21 / 0 | −11 250,12 | 41,750 / 41,600 |
| 1974 | +1 896,825 | −6 597,5 | 19 / 21 / 0 | +6 809,55 | 46,875 / 46,975 |
| 1975 | −21 423,55 | −60 265,5 | 15 / 25 / 0 | −12 984,90 | 48,975 / 49,850 |
| 1976 | +14 974,1 | +12 821,5 | 21 / 19 / 0 | +23 373,09 | 50,250 / 51,825 |
| 1977 | +23 304,925 | +62 881,5 | 23 / 17 / 0 | +23 810,45 | 51,300 / 53,000 |
| 1978 | +63 680 | +54 578 | 22 / 18 / 0 | +59 631,01 | 51,975 / 53,325 |
| 1979 | +74 488,8 | +69 366 | 22 / 18 / 0 | +64 445,29 | 52,425 / 53,450 |

Le résultat favorable tardif coïncide avec des portefeuilles AIR différents :
il ne démontre pas que la formule directe économise du calcul ou apporte
une amélioration économique causale isolée. Les IC annuels, distributions
et valeurs par graine figurent dans les fichiers machine ci-dessous.

**Anomalie précoce à garder visible :** la graine `796219007` diverge
déjà en mai 1970 de **+2 £ de `profit_year`** (ON−OFF), puis de +20 643 £
en décembre 1970, alors qu'aucune cohorte AIR de deux ans ne devrait encore
avoir fourni d'observation mature. Le contrôle direct des checkpoints
mensuels établit le fait, mais pas sa cause (aléas d'exécution,
ordonnancement ou garde non neutre). Il est incorrect de traiter les
trajectoires comme strictement identiques avant apprentissage sur les
40 graines ; cet écart précoce limite l'attribution causale.

## Réplication et cumul exploratoire à cinq ans

| Panel indépendant | Graines | Delta moyen du profit annuel à 5 ans | Gains / pertes | Verdict |
|---|---:|---:|---:|---|
| Premier 40×5 `gateA` | 40 | −7 522,20 £/an | 18 / 22 | `fail_primary` |
| Deuxième 40×5 `holdout` | 40 | −21 757,15 £/an | 20 / 20 | `fail_primary` |
| Nouveau 40×10, checkpoint **1974** | 40 | +1 896,825 £/an | 19 / 21 | observation intermédiaire |
| **Cumul 120 graines à 5 ans, exploratoire** | **120** | **−9 127,508 £/an** | **57 / 63** | non préenregistré |

Sur les 120 graines : médiane −3 241 £/an ; Wilcoxon exact p=0,538736 ;
IC95 bootstrap [−34 245,117 ; +15 256,525] £/an. Le cumul ne constitue
**ni une quatrième porte**, ni une preuve d'équivalence. Les trois panels
restent indépendants, avec même bundle, même référence et même variante.

## Opcodes observés : aucun surcoût structurel démontré

Le harnais collecte des compteurs **SIGN partiels**, pas tous les opcodes
exécutés par l'IA ; ils intègrent les changements de nombre et de type
de travaux planifiés, notamment RAIL. Moyenne par partie de **10 ans** :

| Compteurs | OFF | ON | Delta moyen ON − OFF |
|---|---:|---:|---:|
| Total des postes observables | 126 699 195 | 120 378 984,15 | **−6 320 210,85 (−4,988 %)** |
| Sélection projets | 144,400 appels | 143,875 appels | −1 689 475 opcodes |
| Planification AIR | 62,925 appels | 65,300 appels | **−1 681,025 opcodes** |
| Tentatives RAIL | 12,850 appels | 12,850 appels | −5 070 926,5 opcodes |
| Planification ROAD | 15,975 appels | 18,925 appels | +481 072,9 opcodes |
| Construction ROAD | 15,975 appels | 18,925 appels | −39 213,45 opcodes |
| Planification WATER | 0,075 appel | 0,075 appel | +12,225 opcodes |

17/40 graines ont **davantage** d'opcodes partiels sous ON. Aucune paire
ne présente exactement le même nombre d'appels dans **tous** les postes
instrumentés. Comparaisons historiques, de durées différentes :
premier 40×5 **+8,05 %**, second 40×5 **−1,82 %**, nouveau 40×10
**−4,99 %**. Leur changement de signe et la dominance de RAIL
empêchent d'imputer le delta au seul remplacement de `75/25` :
**aucun gain, surcoût marginal ou neutralité CPU globale n'est démontré.**
La variante ne nécessite pas un nouveau scan ou une nouvelle collecte
annuelle, mais l'absence de calcul supplémentaire significatif ne se
déduit pas de ces totaux à charges différentes.

## Artefacts, contrôles et décision

- `results/air_p0_direct_realization_holdout_40x10_20261010_r2.manifest.json` : protocole figé, graines, provenance, empreinte.
- `results/air_p0_direct_realization_holdout_40x10_20261010_r2.json` : synthèse 80 parties, 40 comparaisons, verdict et télémétrie.
- `results/air_p0_direct_realization_holdout_40x10_20261010_r2.jsonl` : checkpoints mensuels 1970–1979.
- `results/air_p0_direct_realization_holdout_40x10_20261010_r2_engine/` : 80 journaux de partie (fichiers vides acceptables).
- `results/air_p0_direct_realization_holdout_40x10_20261010_r2_annual.csv` : 400 lignes annuelles appariées.
- `results/air_p0_direct_realization_holdout_40x10_20261010_r2_opcodes.csv` : 40 paires de compteurs et d'appels par composant.
- `results/air_p0_direct_realization_holdout_40x10_20261010_r2_analysis.json` : profil annuel, IC, opcodes partiels, cumul exploratoire et extrêmes.
- `results/analyze_air_p0_40x10.py` : extraction reproductible ; compilé et exécuté avec sortie 0 et validations d'exhaustivité.
- `results/inspect_air_p0_cold.py` : vérification ciblée des checkpoints de la divergence précoce.

**Décision : maintenir OFF dans l'arbre actif.** La direction moyenne
est favorable à dix ans, mais les critères de gain, de neutralité
économique démontrée **et** d'absence de surcoût en opcodes ne sont pas
tous remplis. **Nombres magiques supprimés du code livré : zéro.**
Le bundle expérimental demeure archivé pour audit ; les travaux git
concurrents sont conservés et aucun commit/push n'est réalisé.
