# V180 — porte A sur les nouveaux défauts (16 octobre 2026)

## Pré-enregistrement, avant exécution

Demande utilisateur : « fais une porte A du nouveau défaut contre v180 actif ».
Interprétation vérifiée dans `ai/OpexAI/info.nut` : V180 est
`v180_rail_wagon_boost_pct`, par défaut 0, variante **50** (majoration de
l'offre de dimensionnement des rames de 50 %), valeur testée précédemment en
rail seul. Les autres valeurs V180 plus grandes ont déjà été défavorables.

- Arbre : `origin/master` **`62e33c27634739a7189cb91244116dcf3c611e02`**,
  worktree `results/v214_v216af_A_stage_20261016`; code IA non modifié.
  Nouveaux défauts communs : V214 (coût virage 300, coude serré 1500),
  V216a=1, V216f=100, autres réglages inchangés.
- Référence `OpexAI[v180_rail_wagon_boost_pct=0]`.
  Variante `OpexAI[v180_rail_wagon_boost_pct=50]`.
- AAAHogEx-115 complet, tous modes actifs des deux côtés, même monde et
  mêmes graines. Aucun changement de défaut V180 à la suite du test.
- Smoke préalable : `v180_v214default_smoke_1x1_20261016`, 1 graine
  (42), 1 an, deux duels, état/compilation à vérifier (pas d'inférence).
- Porte A V102 : `v180_v214default_porteA_40x3_20261016`, 40 graines
  canoniques, 3 ans, 1 répétition, **80 parties** et **40 paires**.
  `--decision-rule gain_short --primary-metric profit_year`,
  `--min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5`,
  `--required-seeds 40 --required-years 3 --years 3 --repeats 1`.
  Critères : delta moyen OpexAI `profit_year` variante−référence ≥ 4 %
  du moyen OpexAI de référence, Wilcoxon exact bilatéral p < 0,05,
  borne basse de l'IC95 bootstrap strictement > 0 (20 000 rééchantillonnages,
  graine 0), ratio des moyennes de `company_value` ≥ 0,95,
  40/40 paires complètes et valides, 4 trimestres terminaux couverts.
- Hôte PC, `openttd-lab:latest`, 10 CPU, 8 Gio RAM, 10 workers,
  une seule campagne Docker à la fois. Ne pas lancer B si A échoue.

Le R2 rail seul du 15/10 avec V180=50, rapporté dans `docs/taches.md`,
avait un verdict `incomplete` à cause de paires malsaines. Il n'est
pas une qualification en partie complète du défaut actuel.

## Résultat

**`fail_primary`** — la porte A V102 ne passe pas. V180 demeure
**0 par défaut** sur toutes les difficultés. Aucun passage B.

Le smoke `v180_v214default_smoke_1x1_20261016` : les deux duels
et quatre compagnies terminent sans erreur ni échec ; horizon un an
et trois trimestres de `profit_year` valides. Le smoke ne prouve
aucun gain et n'entre pas dans les 40 paires de la porte A.

La campagne `v180_v214default_porteA_40x3_20261016` est complète :
**80/80 parties, 40/40 paires, 160/160 compagnies** en état `complete`,
`run_ok=true`, `game_ok=true`, `horizon_complete=true`, avec
**quatre trimestres valides** de l'année terminale 1972. Zéro
`failed_runs`, zéro erreur Squirrel, zéro paire exclue.
`comparison_complete`, `adoption_sample_complete` et
`metric_coverage_complete` sont `true`.

| Critère de V102 (`profit_year` variante − référence) | Résultat |
|---|---:|
| Gain moyen | **+11 895,05 £/an** |
| Gain moyen relatif | **+0,5307 %** |
| Gain médian | **+2 052,5 £/an** |
| Victoires / défaites / égalités | **20 / 20 / 0** |
| Wilcoxon exact bilatéral | **p = 0,60850582** (seuil < 0,05 : échoué) |
| IC95 bootstrap de la moyenne (20 000, seed 0) | **[−58 351,05 ; +80 305,3] £/an** (borne basse < 0) |
| Seuil de gain à 4 % | **+89 660,871 £/an** (non atteint) |
| `company_value` (ratio des moyennes) | **1,003355 (+0,335503 %)** (garde passée) |
| `ci_pass` / `primary_pass` / `value_guard_pass` | **false / false / true** |
| `policy_comparison.verdict` | **`fail_primary`** |

### Moyennes des profits terminaux

| Entreprise | Référence V180=0 | Variante V180=50 |
|---|---:|---:|
| OpexAI | **2 241 521,77 £/an** | **2 253 416,83 £/an** |
| AAAHogEx | 1 940 585,98 £/an | 1 973 687,70 £/an |

Attention, l'écart OpexAI/AAAHogEx au sein d'un bras n'est pas
le delta causal de V180 : ce dernier vaut **+11 895,05 £/an**.
Les intervalles et la répartition 20/20 ne fournissent aucune preuve
de gain. La garde de valeur n'est pas le problème.

### Deltas terminaux par graine (£/an)

| Graine | Δ | Graine | Δ |
|---:|---:|---:|---:|
| 1 | −190 073 | 232037 | −173 251 |
| 7 | +76 188 | 292001 | −52 668 |
| 17 | −163 048 | 313707 | +269 536 |
| 42 | −174 339 | 375172 | +90 819 |
| 73 | +156 471 | 423960 | −2 865 |
| 100 | −42 968 | 424242 | +188 827 |
| 314 | −62 877 | 442018 | −250 696 |
| 512 | +118 602 | 455216 | −71 993 |
| 999 | +314 401 | 515222 | −440 713 |
| 1024 | −185 757 | 613553 | −186 684 |
| 1337 | +144 159 | 701256 | +124 540 |
| 2026 | −41 177 | 706990 | +172 483 |
| 4096 | +59 670 | 723002 | −110 867 |
| 8191 | +6 970 | 746035 | +295 975 |
| 12345 | −48 842 | 781335 | −65 319 |
| 54321 | +406 447 | 802204 | +248 130 |
| 59527 | +168 416 | 841478 | +274 900 |
| 65537 | −229 910 | 983759 | +298 929 |
| 123456 | +97 161 | 999533 | +391 174 |
| 230185 | −298 870 | 8675309 | −635 079 |

### Provenance et suite

- Code de départ Git : `62e33c27634739a7189cb91244116dcf3c611e02` ;
  `dirty=1` au lancement **uniquement à cause du présent document
  pré-enregistré** (aucun fichier IA ou harnais modifié). Référence et
  variante sont issues du même snapshot figé.
- Bundle : `f84cb30250442a341fd8edde808131aa37c3700d55d2fde3e2d326f631239d9a`,
  manifeste : `99e5e5b0be571f56cc03746cda8053c9b24f7aa86fd85a87a813a9cbef2c1474`,
  Docker `openttd-lab:latest`,
  image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
- Artefacts locaux ignorés par Git : `results/v180_v214default_porteA_40x3_20261016.json`,
  `.jsonl`, `.manifest.json`, `.out`, `_bundle/` et `_engine/`.
  Le smoke utilise le préfixe `v180_v214default_smoke_1x1_20261016`.
- Contrats : `test_v214_rail_turn_costs.py` 15/15 verts ;
  aucun module de contrat `test_v180_rail_wagon_boost.py` n'existe sur
  ce master (exécuter sa découverte donne zéro test) ; la compilation
  et le chargement effectif V180 ont été vérifiés par le smoke.

**Décision :** V180 reste à `v180_rail_wagon_boost_pct=0`,
V214 (300/1500) et V216a=1/V216f=100 restent les défauts.
Le rail seul ancien et cette porte complète sont des contextes
différents ; pas de porte B sans nouvelle dérogation explicite.
