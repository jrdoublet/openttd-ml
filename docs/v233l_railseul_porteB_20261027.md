# 27 octobre 2026 — V233L, smoke puis porte B rail seul à dix ans

**Verdict : `pass` pour la porte B `non_erosion`, sans preuve d'un gain positif à dix ans.** La variante GOOD longue en double voie gagne en moyenne **38 078,7 £/an** (+2,19 %) au terme de 1979, mais son IC95 bootstrap chevauche zéro et le test de Wilcoxon est non significatif. La porte A rail seul 40×3 précédente a échoué : le mécanisme demeure non qualifié pour une adoption par défaut. Les deux réglages restent à 0.

## Protocole et provenance

- Travail réalisé dans le worktree interne `.wt_v233l`, branche `v233-long`, commit source **`8e668fad9d6d0ad0646b34576232eab8178b3488`** ; aucun changement de code pendant les parties.
- Référence : `OpexAI[mode_air=0,mode_road=0,mode_water=0,v233_long_good=0,v233_site_funnel=0]` ; variante : les mêmes trois modes à 0 et `v233_long_good=1,v233_site_funnel=1`. Le lanceur a injecté `probes=2` symétriquement.
- AAAHogEx-115 copié sans changement depuis le dépôt principal ; `disable_veh_aircraft=1`, `disable_veh_roadveh=1`, `disable_veh_ship=1`, `disable_veh_tram=1` sur les duels. Carte 256², départ 1970, une répétition par graine, comparateur figé.
- Graines canoniques de porte B : `42, 100, 7, 999, 2026, 1, 17, 73, 314, 512, 1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309`.
- Harnais : `sweeps/run_c66_reference.py`, `--decision-rule non_erosion --required-seeds 20 --required-years 10 --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --years 10 --repeats 1 --cpus 10 --memory 8g --max-workers 10 --mount-root ..`. Le seuil de 4 % est obligatoire pour l'enregistrement par le lanceur, **mais n'est pas un critère de passage de la porte B**.
- Image Docker `openttd-lab:latest`, identifiant `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` ; bundle commun au smoke et à la porte B `afc104ca2f836817a1e16e4b8842b692ba58c437c18f6f908821466f3ac23b3d`.

## Résultats et santé

| Indicateur à l'année terminale | Résultat |
| --- | ---: |
| Paires / parties complètes | 20/20 ; 40/40 |
| `profit_year` moyen Opex référence | 1 735 354,5 £/an |
| `profit_year` moyen Opex variante | 1 773 433,2 £/an |
| Delta moyen (variante − référence) | **+38 078,7 £/an (+2,1943 %)** |
| Delta médian | **+58 544,5 £/an** |
| Victoires / défaites / égalités | **12 / 8 / 0** |
| Wilcoxon exact bilatéral | **p = 0,5216732025** |
| IC95 bootstrap du delta moyen | **[−54 255,1 ; +130 906,15] £/an** |
| Bootstrap | 20 000 rééchantillonnages, graine 0 |
| Ratio des moyennes de `company_value` | **1,057407, soit +5,740743 %** |
| Dénominateurs de valeur strictement positifs | 20/20 |
| Critère IC95 non-érosion / garde valeur −5 % | **pass / pass** |
| Verdict du harnais | **`pass`** |

Le smoke `v233l_railseul_smoke_1x1_20261027` (graine 42 × un an, mêmes deux bras, règles, seuil et options Docker) termine ses 2/2 duels ; `failed_runs=[]`, `diagnostic_only`, delta descriptif +9 273 £/an. Le contrôle de la porte B rapporte `failed_runs=[]`, 40 statuts `complete`, 0 partie défaillante, 0 erreur non attribuée et aucune erreur de script signalée par le harnais. Les 40 journaux moteur sont vides sans `--script-debug` : les éventuelles erreurs non fatales non remontées ne peuvent pas être auditées dans ces journaux.

Sorties conservées localement : `results/v233l_railseul_smoke_1x1_20261027{.json,.jsonl,.manifest.json,_bundle/,_engine/}` et `results/v233l_railseul_porteB_20x10_20261027{.json,.jsonl,.manifest.json,_bundle/,_engine/}`. Les résultats sont sous le worktree et ne font pas partie du commit documentaire.

## Interprétation

Le gain moyen à dix ans est positif, mais **il n'est pas établi statistiquement** (`p=0,522`, IC95 incluant zéro). Le critère B conclut seulement à une non-érosion observée avec la garde de valeur respectée. Les deux examens rail seul à cinq ans suggéraient +4,55 à +4,6 % sans seuil Wilcoxon franchi ; la porte A 40×3 était également `fail_primary`. Ainsi, le résultat de B n'efface pas les échecs de A et n'autorise aucun changement de défaut.
