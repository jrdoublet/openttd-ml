# P0 / Top-K stable : qualification isolée du 12 octobre 2026

## Périmètre et décision

**Statut : admissibilité économique C66 franchie ; adoption par défaut encore NON DÉMONTRÉE pour l'ensemble des garde-fous P0.** Aucun code Top-K n'est intégré au `master` ni activé par défaut. La branche expérimentale reste le worktree détaché `results/p0_topk_binary_stage_20261012`, au HEAD `f6139d89f299bcd3d2d24bc32bf22fef6df21d8f`. Le seul fichier existant copié initialement depuis le principal était `probes.nut`, pour préserver la parité du profileur non commité. La présente analyse n'autorise aucun commit ni push.

Objectif isolé : remplacer **deux** appels d'insertion du portefeuille finançable dans `OpexProjectSelectAffordable`, à classement inchangé, par une recherche binaire stable (`O(log K)` comparaisons au lieu de `O(K)`, mais insertion dans le tableau toujours `O(K)`). Les flags `p0_topk_binary=0` et `p0_topk_binary_check=0` sont OFF aux quatre difficultés. Les chemins C118 actif, C122 priorité/shadow, dedupe et rejet instrumenté restent sur l'insertion historique ; les autres callsites C69 et les diagnostiques ne sont pas remplacés. Aucune donnée persistante nouvelle, score, devis, cadence ou politique de flotte modifiée.

## Contrôle intrinsèque sur mêmes entrées

Campagne shadow `p0_topk_check5_5y_20261012`, cinq graines `42,100,999,1234,5678`, exercices 1970–1973 clos ; bundle gelé `def46d6313e572fa4b4067b383b64e841009cec22c8d03c855ea563f33cb8d80` : **57 859 insertions** ancien/nouveau confrontées dans la VM Squirrel, **zéro différence d'identité, d'ordre ou de taille** des tableaux après insertion. Fenêtres locales attribuées : **103 690 025** historique contre **34 584 049** binaire, soit **−66,65 %**. Ce différentiel inclut le coût de mesure propre à deux appels en shadow et ne se transpose pas linéairement au budget global. L'A/B économique du shadow est seulement `diagnostic_only`.

Les tests hôte initiaux (2) et renforcés (9) passent ; oracle indépendant par insertion historique droite→gauche et tri stable, égalités revenu/score, classes défensives C77, chaîne V88, prime early-slot, tailles 1/8/20/64/128, flux longs et champs négatifs. Limites prouvées par les tests adversariaux : un score `NaN` ou une **mutation des clés déjà insérées via alias** peut casser l'équivalence de recherche binaire sur un tableau qui n'est plus trié. Aucun de ces cas n'apparaît dans les 57 859 vérifications observées ; l'équivalence est **conditionnelle au chemin et aux préconditions testées**, jamais universelle aux futurs comparateurs.

## Qualification C66 — deux campagnes appariées, même bundle

Les deux campagnes sont 20 graines canoniques ×10 ans, une répétition, 40 parties chacune, **20/20 paires complètes et saines**, OpenTTD 15.3 / image `openttd-lab:latest` digest `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, PC 10 CPU / 8 Go, 10 workers maximum, sans chevauchement Docker. Le bundle source identique est `def46d6313e572fa4b4067b383b64e841009cec22c8d03c855ea563f33cb8d80`. Les deux bras d'une même campagne ne diffèrent que par `p0_topk_binary=0/1` ; `p0_topk_binary_check=0` commun.

| Mesure variante − référence | B 20×10 avec `probe_loop_ops=1` | B 20×10 sans sonde (`probe_loop_ops=0`) |
|---|---:|---:|
| Profit annuel terminal moyen | **+97 898,55 £/an** | **−8 341,25 £/an** |
| Profit médian | +61 433,5 £/an | −20 896,5 £/an |
| Victoires / défaites | 11 / 9 | 9 / 11 |
| IC95 bootstrap du delta | [−44 485 ; +253 698] £/an | [−159 373 ; +141 663] £/an |
| Valeur de compagnie, ratio des moyennes | **+1,73 %** | **−0,71 %** |
| Verdict harnais C66 `non_erosion` | `pass` | `pass` |

Sur le **B non sondé**, IC95 Student `profit_year` [−174 612 ; +157 929] £/an et `p_signes=0,824` ; les règles spéciales d'absence de perte de `AGENTS.md` §4 sont franchies. **Aucun gain de profit n'est démontré**. Le décalage entre les deux campagnes illustre précisément l'effet possible d'ordonnancement et interdit de déduire une trajectoire identique d'un même classement local.

### Budget global non confondu avec la mesure locale

Sur le B **sondé**, seules les catégories top-level disjointes de `LOOP_OPS` sont additionnées (jamais les C39, `SPAN`, sous-postes ou `sleep_left`). Delta moyen d'occupation variante−référence par graine :

- **1970–1973 : −1 114 499** fenêtres d'opcodes, IC95 bootstrap **[−3 645 648 ; +1 296 171]**, 11/20 graines économes.
- **1970–1978 : −1 043 760** fenêtres, IC95 bootstrap **[−3 849 968 ; +1 770 812]**, 10/20 graines économes.

Le gain global **n'est pas statistiquement établi** ; aucune hausse structurelle démontrée non plus. Ces montants sont des fenêtres de budget avec franchissements de ticks et commandes, **pas des instructions VM pures** ni des opcodes récupérés par des workers. La clôture de 1979 nécessite une simulation en 1980 et n'est pas incluse dans les neuf clôtures d'une campagne de dix ans.

### Santé, croissance physique et limite de la non-famine

L'analyseur indépendant `analyse_p0_topk_construction.py` retrouve **20/20 paires valides et 120 checkpoints mensuels par bras et par graine** dans les deux B, aucune faillite et aucune alerte générale de stagnation. Dans le B non sondé, stocks physiques finaux moyens variante−référence : **+2,00 avions, +1,45 véhicules ferroviaires, 0 aéroport, +2,50 gares rail, +1,75 gare tous modes** ; le proxy de projets aboutis porté par les panneaux `IB` retenus augmente en moyenne de **+3,85**. Les stocks et les hausses mensuelles ne sont **pas** des compteurs de lignes construites ; les panneaux `IB` couvrent des projets tous modes, dont flotte, et peuvent être remplacés. Les comptes exacts de constructions/survies **AIR et RAIL restent inconnus** : `line_telemetry=null` et `P5_BUILD_LINE` absent dans ces campagnes. L'outil enregistre explicitement `strict_non_famine_certified=false` ; ne pas le convertir en `true` sous prétexte que les moyennes physiques sont positives.

Le round-trip **Save/Load du bras ON**, graine 42, 2 ans + chargement + 1 an, a réussi : 25 sauvegardes en phase A, 13 en phase B et `LOAD_RECONCILE` observé, 22→62 gares et 44→167 véhicules après reprise. La compagnie fantôme connue est signalée par le harnais et ne perturbe pas les statistiques OpexAI de ce test.

## Conclusion / arbitrage restant

Le coût **intrinsèque de la recherche de position Top-K** est effectivement réduit, et les **deux portes économiques C66 passent** avec valeur gardée. Il serait incorrect de présenter cette réduction locale comme un gain global certain, comme une réallocation déjà observée aux workers, ou comme une preuve complète du débit de nouvelles lignes AIR/RAIL. **Le flag reste OFF et le code reste dans son stage tant que l'exigence explicite de non-famine/constructions du P0 n'a pas été arbitrée sur une mesure adéquate.** Le modèle courant de télémétrie C66 reconstruit les services *actifs*, pas une suite événementielle de créations physiques, et les deux B n'ont pas conservé leurs sauvegardes ; ne pas requalifier leurs stocks en créations ni relancer aveuglément les deux campagnes conclues.

### Preuves et reproduction

- Archive compacte : [`evidence/review/opcode_early4_20261012/topk_binary/`](../evidence/review/opcode_early4_20261012/topk_binary/README.md), contenant les résultats JSON complets, leurs manifestes C66, le différentiel local, les analyses physiques, les scripts de décodage et le patch stage. Les journaux bruts et bundles gelés restent sous `results/p0_topk_binary_stage_20261012/results/` (ignorés par Git).
- `python -B -X utf8 -m unittest discover -s sweeps -p test_p0_topk_binary_adversarial.py -v` et `test_analyse_p0_topk_construction.py` depuis le stage.
- `python -B -X utf8 sweeps/analyse_p0_topk_global.py results/p0_topk_binary_b20x10_20261012_engine --out results/p0_topk_binary_b20x10_20261012_global.json`.
- `python -B -X utf8 sweeps/analyse_p0_topk_construction.py results/p0_topk_binary_noprobe_b20x10_20261012.json --out results/p0_topk_binary_noprobe_b20x10_construction.json --fail-on-qa`.

**Interdictions maintenues :** ne pas réintroduire `air_fleet_dirty_sched`, `simple_opcode`, `simple_roi`, V142/V143 ; aucune nouvelle politique de classement ni rerun sélectif pour chercher un résultat positif. Aucun commit/push pour ce chantier.
