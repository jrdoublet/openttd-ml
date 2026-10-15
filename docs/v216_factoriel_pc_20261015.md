# V216 — diagnostic factoriel PC du 15 octobre 2026

[Preuves compactées et vérification](../evidence/review/v216_factoriel_pc_20261015/README.md) ; [bilan et passation](v216_factoriel_pc_20261015_suite.md).

Exécution depuis master à la demande utilisateur, SHA `92c86206bcc37086626415f0805f0d4512524111`. Au lancement, diff `3ad94b5..HEAD` nul pour `ai/`, `sweeps/` et `requirements.txt` ; seul fichier local non suivi : `docs/journaux/journal_2026-10-14_transfert_taches.md`.

Contrats exécutés au commit prescrit : 2 235 tests, OK, 3 ignorés. Première tentative limitée par les droits du bac à sable ; réexécution avec accès approprié verte. Le premier lancement dans le worktree a été arrêté sans partie ni artefact moteur V216 observés. Reprise sur master, conformément à la nouvelle instruction utilisateur.

F1 puis F2, chacun précédé d’un smoke 1×3. Profil 10 CPU, 8 Go et 10 workers ; campagnes principales 40 graines canoniques × 3 ans, une répétition. Diagnostic uniquement : aucune interprétation du verdict du lanceur et aucun défaut modifié.

Profit annuel terminal en £/an, décembre 1972. Les ratios suivent exactement le script fourni : lignes construites en 1971 avec au moins 180 jours d’activité avant 1972, revenus annualisés, rail ramené au nombre initial de trains. Les nombres de constructions sont les totaux sur les journaux du bras, dans l’ordre 1970 / 1971 / 1972.

| Cellule | Configuration | OpexAI moyen (£/an ; n) | AAAHogEx moyen (£/an ; n) | Rail PASS recette réel/prévu (n ; médiane ; ratio sommes) | Rail PASS profit réel/prévu (médiane ; ratio sommes) | Rail fret recette réel/prévu (n ; ratio sommes) | AIR recette réel/prévu (n ; ratio sommes) | RAIL_BUILD PASS 1970/71/72 | RAIL_BUILD fret 1970/71/72 | AIR_BUILD 1970/71/72 |
|---|---|---:|---:|---|---|---|---|---|---|---|
| A | Opex complet / AAA complet | 2,097,865 ; 40 | 2,006,044 ; 40 | n=15 ; méd. 0.16 ; Σ 0.18 | méd. 0.04 ; Σ 0.03 | n=81 ; Σ 0.87 | n=298 ; Σ 0.58 | 0 / 33 / 79 | 0 / 93 / 67 | 329 / 809 / 516 |
| B | Opex complet / AAA rail | 3,265,310 ; 40 | 1,508,463 ; 40 | n=10 ; méd. 0.27 ; Σ 0.24 | méd. 0.19 ; Σ 0.15 | n=60 ; Σ 0.80 | n=451 ; Σ 0.70 | 0 / 13 / 33 | 0 / 61 / 44 | 381 / 1089 / 501 |
| C | Opex rail / AAA complet | 389,237 ; 40 | 3,058,666 ; 40 | n=19 ; méd. 0.78 ; Σ 0.81 | méd. 0.81 ; Σ 0.93 | n=51 ; Σ 1.06 | — | 107 / 41 / 50 | 178 / 110 / 129 | 0 / 0 / 0 |
| D | Opex rail / AAA rail | 298,281 ; 40 | 1,361,172 ; 40 | n=24 ; méd. 1.04 ; Σ 1.06 | méd. 1.59 ; Σ 1.35 | n=50 ; Σ 0.73 | — | 97 / 43 / 32 | 182 / 100 / 104 | 0 / 0 / 0 |

Moyennes sur les parties saines de chaque bras. Les ratios et constructions incluent tous les journaux, conformément au script fourni ; n désigne ici des lignes, pas des graines indépendantes. Co-localisation observationnelle, sans attribution causale.

## Co-localisation — cellule A

| Nombre de villes de la ligne rail PASS avec notre aéroport | Lignes présentes en décembre 1971 | Profit 1972/train médian (£/an) | Moyen (£/an) |
|---:|---:|---:|---:|
| 0 | 1 | -2509 | -2509 |
| 1 | 9 | 2640 | 2103 |
| 2 | 15 | 3510 | 3840 |

## Co-localisation — cellule B

| Nombre de villes de la ligne rail PASS avec notre aéroport | Lignes présentes en décembre 1971 | Profit 1972/train médian (£/an) | Moyen (£/an) |
|---:|---:|---:|---:|
| 1 | 2 | 2656 | 2656 |
| 2 | 10 | 1144 | 2010 |

## Santé et exclusions — v216_facto_aaarail_40x3_pc_20261015

80/80 parties saines ; 40/40 paires complètes.

Aucune graine exclue ou plantée.

Rapport détaillé : [v216_facto_aaarail_40x3_pc_20261015.summary.md](../evidence/review/v216_factoriel_pc_20261015/artifacts/v216_facto_aaarail_40x3_pc_20261015.summary.md.gz).

## Santé et exclusions — v216_facto_aaacomplet_40x3_pc_20261015

80/80 parties saines ; 40/40 paires complètes.

Aucune graine exclue ou plantée.

Rapport détaillé : [v216_facto_aaacomplet_40x3_pc_20261015.summary.md](../evidence/review/v216_factoriel_pc_20261015/artifacts/v216_facto_aaacomplet_40x3_pc_20261015.summary.md.gz).

## Statistiques brutes des campagnes

Ces comparaisons opposent des configurations de modes ; leurs verdicts sont sans interprétation d’adoption dans ce diagnostic.

### v216_facto_aaarail_40x3_pc_20261015

```text
profit_year: delta moyen=2967028.7 median=2965043.0 V/D/E=40/0/0 p_wilcoxon=1.8189894035458565e-12 CI95_bootstrap=[2765050.525, 3167651.0] seuil=11931.256000000001 (pct=4.0)
company_value: ratio des moyennes=12.166974 (1116.697407%), moyenne des ratios=14.181493
paires=40/40 verdict=pass
```

### v216_facto_aaacomplet_40x3_pc_20261015

```text
profit_year: delta moyen=-1708628.25 median=-1770299.0 V/D/E=0/40/0 p_wilcoxon=1.8189894035458565e-12 CI95_bootstrap=[-1890747.15, -1526694.3] seuil=83914.602 (pct=4.0)
company_value: ratio des moyennes=0.151115 (-84.888507%), moyenne des ratios=0.160529
paires=40/40 verdict=fail_primary_and_value_guard
```
