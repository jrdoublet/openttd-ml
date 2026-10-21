# Tâches de Claude sur le VPS en attendant codex (22/10) — préparées, pas lancées

Aucune de ces tâches ne lance de banc de 10 ans, de porte B, de changement de défaut ni de fusion.
Toutes travaillent hors partie sur des journaux déjà présents sur le VPS, ou à la lecture du code.
Elles ne touchent pas aux fichiers des files A, B et C du PC (`OpexStationPlans`, `OpexV307SinkRoom*`, PO-01c).

| N° | Tâche | Données | Docker | Durée estimée | Livrable |
|---|---|---|---|---|---|
| C1 ✅ | Lire les deux portes A 40×3 GitHub déjà lancées (**fait le 22/10 : les deux `fail_primary`**) | runs 39678322047 (`rail_cal`), 39678326050 (`po01c`) | non | 15 min | verdicts dans `taches.md` ; commande de la porte B écrite, **non lancée** |
| C2 | Décomposer l'écart du départ 1925 (30,9 % d'AAA à 10 ans) | `wt-v293/results/v293_v259_1925_20x10_20261020*` (20×10, JSONL mensuel par mode) | non | 1-2 h | année où l'écart s'ouvre, part rail/air/route, véhicules et capacité par mode, comparaison au départ 1970 |
| C3 | Pourquoi nos lignes rail existantes ne grandissent pas (P1 « second train ») — **découpée en 9 sous-tâches : [c3_croissance_lignes_rail.md](c3_croissance_lignes_rail.md)** | code V284/V270, journaux `v299_diag_3x10` et `v265fix_expo_complete_3x10` | non | 2 h | cause chiffrée (condition qui bloque, par ligne et par année) et plan de correctif découpé ; la sous-étape complexe éventuelle est réservée à codex |
| C4 | PCAL-03 : classer les postes d'opcodes réutilisables | journaux `LOOP_OPS` et spans déjà archivés ; exposition PO-01c du 21/10 | non | 1-2 h | tableau opcodes/an par poste, part rendue par PO-01c, 2-3 cibles avec gain plafond |
| C5 | Préparer la publication (`probes`, panneaux, `fair_play`, niveaux) | `info.nut`, harnais `sweeps/` | non | 1 h | liste des harnais à adapter pour passer `probes` explicitement, avant le passage de `probes` à 0 ; décision à l'utilisateur |
| C6 | V233 chaînes industrielles : note de conception | code des candidats fret, `docs/taches.md` V233/V88 | non | 2-3 h | conception à valider par l'utilisateur ; pas de code tant qu'elle n'est pas validée |

Ordre proposé : C2 et C3 (les deux écarts les plus gros), puis C4, C5 et C6.
