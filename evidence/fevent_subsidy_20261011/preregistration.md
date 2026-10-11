# F-EVENT-BACKLOG-01 — pré-enregistrement 20×10 (11/10/2026)
Base master 25d26c6 + diff agy (worktree wt-fevent-subsidy, non commité). Réglage neuf subsidy_reselect_if_purged, ancien défaut 0, candidat 1.
Catégorie : optimisation d'opcodes (règle AGENTS §4 : gain d'opcodes + 20×10 neutre ⇒ adopter).
Exposition : solo 3 graines×3 ans, spans event.subsidy* 13,66 M → 16 k opcodes ; fenêtres ≥10 000 : 15/97 → 0/104.
Smoke 1×1 fevent_subsidy_smoke_1x1_20261011_r1 sain (delta 0 à 1 an).
Porte : non_erosion 20×10, profit_year, seuil relatif 4 % (enregistré, non porte), garde de valeur 5 %, 20 graines canoniques, VPS 3 CPU/2 Go/3 workers, réseau host.
Complément du 11/10 : graine 73 rejouée seule (AAAHogEx noai_error), mêmes options, campagne fevent_subsidy_nonerosion_20x10_20261011_r1_s73 ; verdict recalculé sur les 20 paires, même règle.
