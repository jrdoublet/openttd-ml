# V217 fret — adoption explicite et audit rail contre rail (16/10/2026)

## Décision utilisateur

Le 16 octobre 2026, après examen de la porte B exploratoire et des pertes spécifiques, l'utilisateur a décidé d'activer **`v217_rail_refill=1` par défaut** (easy, medium, hard, custom). Ce choix relève d'une décision explicite, **pas** d'une prétendue qualification V102 complète : la porte A 40×3 était `fail_primary` et le diagnostic multimodal 40×5 était également `fail_primary`.

La valeur 0 conserve le comportement inerte, 1 active le fret uniquement (à partir de la troisième année, caisse disponible > 100000 et vivier démarrable < 2), 2 inclut voyageurs.

## Preuves disponibles avant décision

- Banc multimodal sans sonde 40×5 `v217_diag_40x5_pc_20261016_r1` : 80/80 jeux, +58 750 £/an, 24V/16D, p=0,135, IC95 bootstrap [−8 983 ; +129 957], valeur −0,25 %, seuil de gain de 4 % non atteint.
- Banc 20×10 multimodal exploratoire `v217_porteB_20x10_pc_20261016_r1` : 20/20 paires, delta `profit_year` −320,4 £/an (11V/9D), IC95 bootstrap [−124 127,8 ; +120 277,85], valeur +1,2193 %, verdict **`non_erosion:pass`**. Aucun gain positif démontré à 10 ans.
- Graine 841478, autopsie `results/v217_autopsy_841478_20261016_report.md` : la baisse du profit Opex de −440 993 £/an s'accompagne de −15 avions et +2 trains en 1974, mais les réseaux AIR étaient déjà différents en 1970–1971, avant tout refill V217 possible. Ne pas en tirer une causalité directe.
- Fret industriel, **capacité tous modes confondus** (cargo distinct de pax=0/courrier=2), à fin 1979 dans les 20 paires : V217=1, Opex 1801,45 unités moyennes (4,40 % de sa capacité totale), AAA 10267,8 (29,92 %). Retard ×5,70. Dans la référence V217=0, Opex 1327,3 (3,25 %) et AAA 13544,5 (35,96 %). Il s'agit de capacités, pas de revenus, pas de tonne-km et pas de fret ferroviaire pur.

## Changement minimal

Le seul changement fonctionnel est la valeur par défaut dans `ai/OpexAI/info.nut` ; `settings.nut`, le scheduler et les algorithmes V217 sont inchangés. Mise à jour du contrat dans `sweeps/test_v217_rail_refill.py`, 15/15 tests V217 + V166 exécutés avec succès, `git diff --check` propre. Aucun changement dans les réglages ou le code d'AAAHogEx.

## Diagnostic demandé ensuite

Banc 40×3 `v217_default_railonly_vs_aaa_40x3_20261016`, rail seul **des deux côtés** : OpexAI `mode_air=0,mode_road=0,mode_water=0` ; AAAHogEx `disable_veh_roadveh/tram/ship/aircraft=1`. 40 graines `SEEDS_40`, 1970–1972, post-traitement des lignes `--line-telemetry` ; cible : quantifier profit, capacité et réseau fret vs pax. Préenregistrement : `results/v217_default_rail_only_40x3_20261016_prereg.md`. Smoke 42 1×3 sain : OpexAI 421768 £/an vs AAAHogEx 1444127 £/an, uniquement des véhicules rail (20 vs 34), 16 vs 22 lignes physiques.

L'ancien fork 841478 a été arrêté (préparation A/A/B conservée et témoin A/A `aa0` sain) pour libérer les 3 CPU réservés ; le 40×3 utilise un seul conteneur plafonné à 10 CPU avec 10 workers.

## Résultat du 40×3 rail seul (terminé)

40/40 jeux en fin 1972, 39 `complete` et seed 613553 `stagnation_suspect` des deux côtés (sensibilité 39/40 quasi identique), 0 erreur moteur, zéro victoire Opex au profit annuel.

- OpexAI 309 802 £/an, AAAHogEx 1 385 558 £/an : ratio **22,36 %** ; trains 16,33 contre 27,43.
- Capacité fret industriel (tous véhicules étant ferroviaires) **1 043 contre 5 297**, AAA ×5,08 ; part du fret dans la capacité totale 77,0 % contre 69,6 %.
- Fret pur : 9,10 contre 14,08 lignes, ~10,25 contre ~20,85 trains, capacité médiane **90 contre 240 par train** ; profit courant médian par ligne 26,4 k£ contre 45,4 k£.
- Les déficits persistent sans AIR/ROAD : priorité à l'analyse de la taille/composition des trains fret et du portefeuille fret, plutôt qu'à la seule concurrence de capital par l'AIR.

Rapport détaillé : `results/v217_default_railonly_vs_aaa_40x3_20261016_report.md` et preuves brutes `.json`, `.jsonl`, `.manifest.json`, `_bundle/`. Aucun défaut autre que V217 n'a été modifié.
