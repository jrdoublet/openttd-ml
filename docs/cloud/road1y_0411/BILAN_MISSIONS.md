# Bilan des missions cloud et des bancs du 04/11 (route seule, 3 ans)

Toutes les portes A : 40 graines × 3 ans, `gain_short`, seuil 4 % (≈ +20,7 k£/an), garde de valeur 5 %, contre la configuration route seule de master (`load_orders=1`, `spread_stops=2`, `astar=4`, `gap=12`, `weak=15`, `next=64`, `next3=56`, `mail2=5`).

| Levier | Origine | Résultat | Verdict |
|---|---|---|---|
| `road1y_pax_min=100` (paires estimées vers 2×min(A,B)) | mission 1, `RAPPORT_CLOUD.md` | −11,6 k£/an, 15/25, p=0,38, IC95 [−48,6 ; 24,7] | fail_primary |
| `road1y_pax_min=50` | idem | −2,9 k£/an, 21/19, p=0,97, IC95 [−36,0 ; 29,9] | fail_primary |
| `road1y_alt_load=33` (1/3 des bus pleins au bout B) | mission 2, `RAPPORT_CLOUD2.md` | +14,7 k£/an, 25/15, p=0,23, IC95 [−10,5 ; 39,9] | fail_primary |
| `road1y_alt_load=50` | idem | +12,5 k£/an, 25/15, p=0,18, IC95 [−11,8 ; 35,9] | fail_primary |
| `road1y_aaa_fleet=1` (flotte bus d'AAA d'un bloc) | mission 3, `RAPPORT_CLOUD3.md` | −22,7 k£/an, 16/24, p=0,14, IC95 [−51,9 ; 6,4], valeur −9,4 % | fail_primary_and_value_guard |
| `road1y_abandon_days=60` | agy | smoke −22 k | rejeté |
| `road1y_pax_bilat` | agy | +9,7 k£/an, p=0,55 | fail_primary |

Diagnostics :
- `agy_new72_rapport.md` : lignes ouvertes en 1972 = −38 k£/graine, moitié calendrier (caisse < 10 k£ de février à mai absorbée par les renforts, 31 % des ouvertures au 4e trimestre), moitié rendement mensuel ; aucun levier calendrier au-dessus du seuil.
- `agy_cash72_rapport.md` : la caisse oisive fin 1972 n'est pas un blocage.
- Flotte : 5 échecs (`rich_fleet`, `berth_fleet`, `pax_bilat`, `alt_load`, `aaa_fleet`) ⇒ fil clos. Nos renforts « sans demande » rapportent.
- Courrier : clos (`agy_mailgap_rapport.md`).
