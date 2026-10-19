# V228 — duels 20 × 10 sur carte 256 × 256, départs 1970 / 1950 / 1990

## Exécution et santé (PC Windows, 19/10/2026)

Le lanceur `bash sweeps/run_v228_pc.sh ref1970 y1950 y1990` a exécuté successivement les **trois conditions** restantes de V228, après le banc indépendant sur carte 1024² [archivé ici](../v228_map1024_20261019/README.md). Le suffixe `_r2` a été utilisé pour ne pas écraser le `ref1970` incomplet de 18 h 59.

Pour chaque condition : OpenTTD 15.3 / OpenGFX 7.1, **carte 256 × 256** (`--map-size 8`), duel sur une carte partagée OpexAI (`OpexAI[v264_convergent_freight=1]`) contre AAAHogEx-115, 20 graines communes, 10 ans, 1 répétition, 10 CPU / 8 Go RAM / 10 workers / Docker `--network host`. La graine 73 est remplacée par 373684 selon la convention du script. Chaque smoke (graine 42 × 1 an) a réussi.

**60/60 parties saines**, 20 `complete` par condition, **aucun échec de santé**, horizon atteint en décembre de la neuvième année après le départ (1979, 1959, 1999). Chaque JSONL comprend **4 800 lignes**, soit 20 graines × 2 compagnies × 120 checkpoints mensuels ; les trois résultats finaux JSON et les trois manifestes existent.

Révision Git au lancement : `4503521a1a1993d1aa8aa24f3835bfcac10bd5b8`, `dirty=0`. Même bundle de sources économiques et harnais que le 1024² : `196764d40f2b8ca5588518859669270c154c3b4ea933b6ed1e99590dd7af471f` (l'IA AAAHogEx tierce reste archivée seulement dans les bundles locaux non versionnés). Manifeste spécifique par condition, conservé ici.

## Résultats au terme de dix ans

| Condition | Opex profit annuel moyen | AAAHogEx profit annuel moyen | Opex / AAA profit | Opex valeur moyenne | AAA valeur moyenne | Opex / AAA valeur |
|---|---:|---:|---:|---:|---:|---:|
| 1970, 256² | 3 659 060 £ | 7 516 037 £ | **48,68 %** | 19 371 563 £ | 28 252 418 £ | 68,57 % |
| 1950, 256² | 2 419 499 £ | 6 102 477 £ | **39,65 %** | 11 173 756 £ | 21 147 077 £ | 52,84 % |
| 1990, 256² | 4 257 360 £ | 8 308 451 £ | **51,24 %** | 23 668 644 £ | 32 151 974 £ | 73,61 % |

Véhicules moyens finaux OpexAI / AAAHogEx : **167,65 / 285,1** (1970), **216,65 / 309,2** (1950), **163,4 / 285,05** (1990). Ces trois duels sont valides et montrent un retard économique d'OpexAI sur la carte normale ; le départ 1950 est le moins favorable en ratio de profit, 1990 le moins défavorable. Il ne s'agit **pas d'un test A/B de modification de politique**.

Sur 1024², en revanche, le banc a été déclaré invalide en raison de l'inactivité d'OpexAI sur la graine 8191 ; la flotte moyenne des 19 parties saines n'atteint qu'environ deux véhicules face à plusieurs centaines chez AAAHogEx. Le contraste est massif, mais **sa cause technique précise reste à diagnostiquer**. Ne pas confondre la dimension 1024² avec la graine 1024, commune à toutes les conditions.

## Chronologie et durées (heure de Paris)

Durées observées entre la dernière modification du manifeste de la campagne complète et le JSON final :

| Condition | Début approximatif | Fin du résultat | Durée du 20 × 10 |
|---|---|---|---|
| 1970 | 21:36:07 | 21:50:07 | **14 min 00 s** |
| 1950 | 21:50:25 | 22:04:20 | **13 min 55 s** |
| 1990 | 22:04:35 | 22:19:20 | **14 min 45 s** |

Durée totale des trois conditions, *smokes et préparation inclus* : environ **43 min 32 s** (`stdout` créé à 21:35:48 ; résultat final à 22:19:20). Les durées sont fondées sur les horodatages des fichiers, et ne sont pas des temps moteur chronométrés au milliseconde près.

## Preuves

Les **20 fichiers** de la campagne (six fichiers par condition : JSON final, JSONL complet, manifeste final, JSON smoke, JSONL smoke, manifeste smoke ; plus stdout et stderr partagés) figurent ici en `.gz` déterministe. `index.json` relie leurs chemins `results/` originaux aux tailles/empreintes SHA-256 des versions brutes et compressées ; chaque archive a été vérifiée octet par octet après décompression. Cet index autonome n'altère pas le registre historique global `evidence/review/index.json`.

Les bundles gelés, les journaux moteur et les originaux bruts restent intacts dans le worktree local `results/v228_pc_stage_20261019/`, sans incorporer le code AAAHogEx non versionné dans Git.
