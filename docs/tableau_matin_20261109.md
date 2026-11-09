# Tableau du matin — nuit du 08→09/11/2026 (leviers agy)

Portes A 40×3, gain_short, seuil 4 %, garde de valeur 5 %. Tous les réglages sont à **0 par défaut** sauf mention. Rien n'est fusionné sur master (code sur branches locales). Les chiffres de rendement et de causes viennent de rapports d'agy, non tous revérifiés.

## Multimodal (branche `agy-easy`)

| Sujet | Commit | Réglage | Tests hôte | Verdict porte A |
|---|---|---|---|---|
| EB-10 garde clé de paire | e66c523b + 1a063f97 (mon correctif) | `eb10_guards` | verts (suites ciblées) | +3,7 k£, fail |
| AIR-COVERAGE-STOP | ae6fe7d1 | `air_coverage_stop` | verts | +2,4 k£, fail |
| IDLE-1 (worker de reliquat) | c507113f | `idle1_slack_worker` | verts | +17,3 k£ (21/13/6, p=0,21), fail |
| PO-02 échéance indépendante | bd681e94 | `po02_independent_expiry` | verts | +3,3 k£, fail |
| EB-4 arbitrage AIR/ROUTE | 032642db | `eb4_air_road_arbitrage` | verts | −18,0 k£ (17/23), fail |
| EB-7 comptabilité fine | 33df971a | `eb7_detailed_accounting` | verts | +32,3 k£ (22/13/5, p=0,23), fail |
| LATE-GAME-1 | 4f7cc595 | `late_game_policy` | verts | −0,1 k£, fail |
| MULTI-1 relance | d5bb0461 | `multi1_relance` | verts | +0,2 k£, fail |
| EB-7 + IDLE-1 ensemble | branche `nuit-defaults` (31a33dda + ~10 réparations de tests) | les deux à **1 par défaut** (décision utilisateur) | 24 échecs + 1 erreur restants sur la suite complète | +57,8 k£ (24/15/1, p=0,08, IC95 [−6,8 ; +125,8] k) : meilleur, limite ; non fusionné |
| Fair-play parties normales | e2a2b513 + 6cd17911 | — | — | non banc |

Suite complète sur `agy-easy` : 24 échecs + 1 erreur (vs 156 après les 8 leviers, 26 avant) ; revue des diffs `.nut` des 8 leviers **non faite**.

## Route seule, 3 ans (branche `road1y-night`, objectif 100 % d'AAA, état ≈ 74 %)

| Sujet | Commit | Réglage | Tests | Verdict |
|---|---|---|---|---|
| Combo de 8 leviers route neutres | branche `road1y-combo` (875b52a3) | 8 réglages | verts | −11,7 k£ (17/23), fail |
| LOAN-1 | 78918abd | `road1y_loan_floor` | verts | −268 k£, mort (la dette de 300 k£ sert de capital) |
| FRET-ADMISSION | e19d65ad, correctif 50d2c132 (profitAnnual) | `road1y_freight_adm=15` | verts | +12,2 k£ (20/20, p=0,48), neutre |
| ALT-COND | 8bc24a28 | `road1y_alt_load_cond=20` | verts | −115,2 k£ (5/35), nuisible, rejeté |
| Courrier p2p initial | 63b6c2aa | `road1y_mail_p2p=10` | verts (8 tests dédiés) | +3,9 k£ ; 0 ligne ouverte (boucle sans curseur) |
| Courrier p2p, correctif curseur | 5ff4f241 | + `road1y_mail_p2p_missing` | verts | +6,9 k£ (23/14/3, p=0,15) ; 4 lignes/13 fourgons, toutes en 1972 |
| Courrier p2p, voirie | idem | `missing=30` / `45` | — | +7,0 k£ / +7,0 k£, identiques |
| Courrier p2p, caisse et 1970 | 1fbd7532 | `_cash=20` ; `_cash=20,_start=7` | verts | +4,3 k£ ; +1,2 k£ ; piste close |

Seuil de porte A route seule : +20,5 k£.

## À décider / vérifier par le modèle fort
- Fusionner ou non `nuit-defaults` (idle1 + eb7 à 1) ; rebench possible sur 40 graines disjointes (p=0,08).
- ~55 commits agy de `agy-easy` jamais relus ; relire les `.nut` des 8 leviers et du combo (34 fichiers), et les affirmations de DECOMP_ROUTE_3ANS / H3 (task_road.nut:1344, contradiction avec cash72).
- Divergence EB-14 vs C77/PO01C (`orchestrator.nut:649-653`, options dans `defauts_decouverts.md`).
- Critère de porte à formaliser dans le lanceur : IC95 hors 0 + ≥26/40 victoires + garde de valeur 5 %.
- Courrier p2p : cause du faible nombre de paires ouvertes inexpliquée (parties à relancer avec `decision_log=1`).
- Écart de rendement par véhicule (bus ×1,46, fourgons ×1,69 vs AAA, chargement complet à la source) : hypothèse, non testée.
