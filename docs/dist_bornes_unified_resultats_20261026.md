# DIST-BORNES-1 — qualification de l'opt-in unifié, 26 octobre 2026

**Verdict : NO-GO_NON_EXPOSE (0/5 graines exposées ; seuil préenregistré 2/5).**
La borne fret peut être modifiée derrière `dist_bornes_unified=1`, mais les parties
de l'échantillon n'ont construit **aucune** liaison fret hors de la bande
V276 antérieure. La porte A 40×5, puis la porte B 20×10, ne sont **pas lancées**.
Défaut **0 aux quatre difficultés**, aucune adoption, aucun autre chantier touché.

## Contrat et code

- Inventaire : [dist_bornes_inventaire_20261026.md](dist_bornes_inventaire_20261026.md).
- Préréglage figé **avant** l'implémentation :
  [dist_bornes_unified_prereg_20261026.md](dist_bornes_unified_prereg_20261026.md)
  au commit `34ca5d57`.
- Implémentation publiée au commit `d5825506` : un prédicat `OpexDistBornesWindow`
  et un prédicat `OpexDistBornesAllows`, consommateurs ROUTE/C42, RAIL direct,
  RAIL PO01C, RAIL/ROUTE V276 et AIR. Mode OFF conservé par garde explicite.
  V269, V168, V294 et le correctif autonome `dist_bornes_v276_freight`
  restent distincts. Aucun champ permanent Save/Load ajouté.

## Validation de fonctionnement

| Contrôle | Constat |
|---|---|
| Suite hôte avant moteur | 2 939 tests OK, 5 skips, 2 expected failures ; vérification PO01D octet par octet via retrait **exact** des ajouts opt-in ; `git diff --check` OK |
| Revue indépendante du diff | Aucun défaut concret résiduel démontré en Squirrel, C42, PO01C, V269/V276, grille ni OFF ; compilation réelle ensuite vérifiée par smoke |
| Save/Load, `save_full_state=1` | Graine 42, 1970 : sauvegarde du 1/7 avec 9 gares et 22 véhicules, rechargement 1 an, 47 gares et 91 véhicules ; `LOAD_RECONCILE` vu, aucun motif d'erreur Save/Load |
| Save/Load, `save_full_state=0` | Même graine : sauvegarde du 1/7 avec 9 gares et 22 véhicules, rechargement 1 an, 48 gares et 102 véhicules ; `LOAD_RECONCILE` vu, aucun motif d'erreur Save/Load |
| Réserve Save/Load | Dans les **deux** rechargements, une compagnie fantôme supplémentaire signalée par le runner ; les métriques OpexAI concernent la compagnie 0. Ces reprises établissent la résistance de Save/Load, pas la neutralité d'une bifurcation de monde |
| Smoke 1024² 42×1 | Deux parties OFF/ON complètes et actives, aucune erreur de script enregistrée. Delta ON−OFF `profit_year` **−88 547 £/an** et ratio valeur **0,346** ; un seul monde et un an : simple diagnostic, pas porte économique |

Artefacts locaux (hors Git, campagne gelée) :
`results/dist_bornes_unified_saveload_full_42_20261026.json`,
`results/dist_bornes_unified_saveload_short_42_20261026.json`,
`results/dist_bornes_unified_smoke_1024_42x1_20261026_r2.json`.
La première tentative de smoke a été refusée **avant** la simulation parce que
`policy-id` et `variant-policy-id` étaient identiques ; le smoke qualifiant
est la campagne suffixée `_r2`. Pas de réutilisation du nom initial.

## Exposition appariée : 1024², 1970–1974, 5×5

Campagne `dist_bornes_unified_exposure_1024_5x5_20261026`, cinq graines
**42, 100, 7, 999, 2026**, une répétition, dix parties (deux bras par graine)
**toutes complètes et saines**, OpenTTD 15.3 / OpenGFX 7.1, `probes=258`,
`max_workers=10`, 10 CPU / 8 GiB, **un seul Docker**. Référence
`dist_bornes_unified=0`, variante `=1`, autres défauts identiques.
Bundle gelé SHA256 `3645ef2207ecff495d6b385e3b4e65bd3a6606a24bd80e814b319f744facd786`,
manifeste `6d19fd07e5505bc4f2ed988305b2b34bdc1d2bc25fe8005779fa1c6c0527b0e3`,
Git `d5825506` propre, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.

| Graine | Constructions RAIL OFF | RAIL ON | RAIL ON hors 7…200 | Delta `profit_year` ON−OFF |
|---|---:|---:|---:|---:|
| 42 | 31 | 25 | **0** | +69 598 £ |
| 100 | 22 | 4 | **0** | −3 575 141 £ |
| 7 | 8 | 8 | **0** | +1 100 424 £ |
| 999 | 1 | 2 | **0** | +1 461 064 £ |
| 2026 | 28 | 37 | **0** | −385 849 £ |
| **Total** | **90** | **76** | **0** | moyenne **−265 981 £/an** |

La distance `RAIL_BUILD.dist` varie de **93 à 200** sur les dix journaux ;
aucune construction RAIL, toutes familles confondues, n'est sous le minimum 7
ou au-dessus du maximum 200 de cette époque. Contrôle indépendant sur **tous**
les `RAIL_BUILD`, y compris ceux dont l'enchaînement individuel n'est pas
reconstituable. Les publications `V276_PUBLISH` sont présentes dans les
dix journaux ; le mécanisme différé est bien actif, mais il ne publie pas
l'identité des paires individuellement. Le rapprochement `PROJECT_CHOSEN`
→ `RAIL_ATTEMPT kind=freight ok=1` → `RAIL_BUILD` ne révèle **aucune**
construction hors bande. Le nouveau plancher fret zéro n'a ainsi produit
aucune construction physique hors de la bande ancienne. À 1970–1974, le
V269 tardif de défaut +5 ans ne peut pas davantage être exposé.

L'audit automatisé conservateur est reproductible depuis :

```powershell
python -X utf8 sweeps/analyse_dist_bornes_unified_exposition.py --engine-dir results/dist_bornes_unified_exposure_1024_5x5_20261026_engine --seeds 42 100 7 999 2026 --out results/dist_bornes_unified_exposition_audit_REPRO_NOUVEAU.json
```

Résultat local figé :
`results/dist_bornes_unified_exposition_audit_1024_5x5_20261026_r2.json`.
Ce programme classe tout RAIL_BUILD hors bande sans provenance V276
individuelle comme **inconclusif** ; pour cette campagne, aucune
construction n'est hors bande. Les journaux restent dans
`results/dist_bornes_unified_exposure_1024_5x5_20261026_engine/`.

## Métriques descriptives, sans interprétation causale

Comparaison ON−OFF : `profit_year` moyen **−265 980,8 £/an**,
**3/2/0** victoires/défaites/égalités, Wilcoxon bilatéral **p=1**,
IC95 bootstrap **[−2 002 169,6 ; +1 038 514,8] £/an**. Le ratio des
moyennes de `company_value` vaut **0,821287**, soit **−17,87 %**.
Les différences du portefeuille et des profits existent mais aucune paire
fret nouvellement admissible n'a été démontrée comme construite ; elles
ne qualifient donc **pas** l'intervention. Des compteurs
`observed_opcodes_total` sont visibles mais
`observed_opcode_complete_cpu=false` sur l'échantillon : pas de conclusion
sur l'absence de surcoût CPU.

**Décision verrouillée :** `NO_GO_NON_EXPOSE`, porte A **non lancée**,
porte B **non lancée**, réglage opt-in disponible à 1 pour de futurs
diagnostics, tous les défauts restent à 0 pour DIST-BORNES-1. Pour réexaminer
l'effet du fret tardif, un nouveau protocole devrait être préenregistré avec
un horizon couvrant réellement V269 ; ce diagnostic ne modifie pas le
préréglage ni les verdicts historiques.
