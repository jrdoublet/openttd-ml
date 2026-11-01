# Corrections B2 — reprise du 29 octobre 2026

## État de reprise
Partie 1 commitée : `8ff35570`. Partie 2 implémentée et mesurée, défauts zéro. Aucun push ni git config.
Les 227 tests ROAD100 passent (3 ignorés). Campagne JOINED corrigée : cinq jeux sains.

Échec précédent `busB2_fix_joined_20261029` : arrêt des cinq IA au chargement,
`bus_districts_overrides.nut:2101`, affectation de méthode de classe par `=`.
Correction par création/remplacement de slot `<-` avant instanciation ; vérifiée au moteur.
Ce résultat en erreur est conservé, jamais interprété économiquement.

B2-1 : reconstruction des projections hors Save après maintenance/construction.
B2-2 : définitions chargées même OFF et sélection du refleet de maintenance au Load
si marqueurs présents ; aucune création lorsque extra_stops=0.
B2-3 : exclusion des tuiles pending du décompte.
B2-4 : exception des projets road1yBusSite au filtre LIVE.
M3 : politique ROAD1Y_LOAD_ORDERS réappliquée sans véhicule modèle.
Cas ≥64 lignes et rollback refusé : contrats seulement.

## Protocole
Route seule, estim_unifie=31, adversaire AAAHogEx-115 limité à la route,
5 graines 17/2026/12345/1337/100, un an, probes=2, script-debug et line-telemetry,
3 CPU, 2 Go RAM sans swap, 3 workers. Une campagne à la fois.
Image sha256:7e2f9057c5783fa1ee7ac3d275b293a6f9ae3c228353e1e9cefedeec8b57b984.
Aucune porte A/B, aucun changement de défaut. Profit terminal = trois trimestres clos.
Diagnostic préalable séparé : graine 17, probes=6, mesure de couverture traversant/baie
et composition du top40 ; sa trajectoire ne sera pas assimilée au banc probes=2.
Budget partie 2 : a, b et c isolés, puis combinaison retenue, 5×1 chacun.
C sera séparé en distance minimale 30 et plafond 2 quartiers si justifié.
Aucune promesse de gain tirée du rapport fourni : causalités à vérifier.

## Résultats disponibles (livres)
| Variante | 17 | 2026 | 12345 | 1337 | 100 | Moyenne |
|---|---:|---:|---:|---:|---:|---:|
| OFF historique | 61 358 | 62 352 | 51 211 | 46 602 | 34 440 | 51 192,6 |
| OFF partie 1 (passe précédente) | 61 358 | 62 352 | 51 211 | 46 602 | 34 440 | 51 192,6 |
| JOINED historique | 19 631 | 95 347 | 79 530 | 63 943 | 88 701 | 69 430,4 |
| JOINED partie 1 | 19 837 | 95 347 | 79 530 | 64 832 | 88 701 | 69 649,4 |

Artefacts : results/busB2_fix_off_20261029 et busB2_fix_joined_r2_20261029,
JSON/JSONL, manifests, bundles et engine logs conservés. Delta JOINED : +219 £
en moyenne ; 17 +206, 1337 +889, autres identiques. Les changements de coût/opcodes
et le remplacement du corps de méthode peuvent déplacer le calendrier ; ne pas
attribuer ce petit delta à un gain économique du correctif de sauvegarde.

## Diagnostic vérifié et décision avant variantes
Les inventaires de lignes du rapport fourni sont reproduits à partir des snapshots
originaux de décembre (ce sont des profits véhicules courants, pas des profits nets
annuels de ligne). Les marges ne permettent pas d’attribuer les achats non réalisés.
La campagne diagnostic `busB2_fix_diag_s17_20261029` (probes=6) est saine.
Le premier top40 compte **33 villes distinctes**, dont une à quatre sites et une à trois,
non une poignée de villes occupant tout le classement. Un plafond deux reste testable,
mais sa justification est trois places libérées, pas une exclusion massive prouvée.
La correspondance des tuiles indique un décalage +1 entre les références town des
stations décodées et les TownID NoAI (inférence ; le décodeur conserve la référence
brute `base.town`). Pour les villes 18/26/10/35 du rapport (NoAI 17/25/9/34),
meilleur site / producteurs / meilleure baie : **17/27/15 ; 22/49/13 ; 9/7/5 ; 12/16/9**.
Tous dépassent 40 %, et les baies testées sont moins couvrantes. Les sites NoAI
17/25/9/34 figurent au top40. La boîte de production peut sous-compter (9/7),
limite déjà documentée. Même avec les identifiants pris littéralement, les couvertures
18/26/10/35 sont 20/33, 17/23, 15/15, 5/5 et ne corroborent pas l’hypothèse.
**b non implémenté** : aucun fait ne justifie ce repli comme cause de l’abandon
sur 17 ; pas de campagne économique pour un correctif non justifié.
Le diagnostic instrumenté n’est pas une reproduction exacte de la trajectoire probes=2.

Réglage nouveau `road1y_bus_fixes=0` aux quatre difficultés, bits indépendants :
1 = ajouts de quais passagers seulement (maintenance fret conservée),
4 = distance Manhattan minimale 30 avant devis pax, 8 = deux meilleurs quartiers
par ville après tri et avant top40. Bit 2 réservé/non utilisé (hypothèse b non étayée).
Mesures prévues : 1, 4, 8 et 12 isolant les deux composantes de c ; combinaison 13
si les mesures rendent plausible l’objectif. Contrôles OFF et JOINED masque zéro
sur l’arbre livré. Aucun réglage de défaut modifié.

Premier résultat a : 18 975 / 93 972 / 79 530 / 64 832 / 88 701 £, cinq jeux sains.
Le bois revient bien à quatre camions (profit décembre 3 341 £), mais le charbon
**ne réapparaît pas**. L’explication « six camions ont empêché le charbon » et le gain
annoncé +10–15 k£ ne sont donc pas confirmés par cette intervention isolée.

## Tableau final — toutes les variantes mesurées

| Variante | 17 | 2026 | 12345 | 1337 | 100 | Moyenne | Moyenne 4 autres |
|---|---:|---:|---:|---:|---:|---:|---:|
| OFF historique | 61 358 | 62 352 | 51 211 | 46 602 | 34 440 | 51 192.6 | 48 651.2 |
| OFF partie 1 | 61 358 | 62 352 | 51 211 | 46 602 | 34 440 | 51 192.6 | 48 651.2 |
| OFF final | 61 358 | 62 352 | 51 211 | 46 602 | 34 440 | 51 192.6 | 48 651.2 |
| JOINED historique | 19 631 | 95 347 | 79 530 | 63 943 | 88 701 | 69 430.4 | 81 880.2 |
| JOINED partie 1 | 19 837 | 95 347 | 79 530 | 64 832 | 88 701 | 69 649.4 | 82 102.5 |
| JOINED final, masque 0 | 19 859 | 93 739 | 79 530 | 64 832 | 88 701 | 69 332.2 | 81 700.5 |
| a, masque 1 | 18 975 | 93 972 | 79 530 | 64 832 | 88 701 | 69 202 | 81 758.8 |
| c distance, masque 4 | 15 181 | 68 134 | 75 807 | 58 541 | 77 814 | 59 095.4 | 70 074 |
| c quartiers, masque 8 | 29 883 | 93 739 | 69 444 | 56 880 | 88 701 | 67 729.4 | 77 191 |
| c complet, masque 12 | 18 014 | 68 134 | 89 093 | 59 775 | 77 814 | 62 566 | 73 704 |
| a + quartiers, masque 9 | 29 914 | 93 972 | 69 444 | 56 880 | 88 701 | 67 782.2 | 77 249.2 |

Tous ces duels sont sains (5/5 jeux complets par campagne). Le contrôle OFF final
compare **130 observations** des deux compagnies : seules engine_log_path,
campaign_id, game_id et source_bundle_sha256 diffèrent. Tous les autres champs,
économie, flotte et compteurs compris, sont identiques au OFF historique.

Le témoin JOINED final diffère légèrement de la partie 1 après ajout des gardes
inactives des bits : 17 +22 £, 2026 −1 608 £, autres identiques. Le masque zéro
ne modifie pas les décisions logiques, mais ses tests coûtent des opcodes dans le
chemin ON ; cette dérive de calendrier est observée et conservée. Les variantes
partie 2 partagent ce code et se comparent donc aussi au JOINED **final** (69 332,2 £).
La restriction a n’a pas rétabli le charbon ; les gains annoncés par le diagnostic
initial n’étaient pas des mesures causales. Le plafond distance perd 10 236,8 £
de moyenne face au JOINED final. Le plafond de quartiers seul récupère environ
10 k£ sur 17 mais perd sur 2026/12345/1337 ; ce compromis ne satisfait pas la demande.
La combinaison retenue **pour essai**, 9, exclut la distance réfutée ; aucune
combinaison n’est retenue pour adoption. Pas de campagne masque 13 après l’échec
clair du plancher, ni de relance cherchant un résultat favorable.

## Décision et limites
**Objectif économique non atteint** : meilleur résultat demandé sur 17 = 29 914 £,
contre environ 60 k£ visés et 61 358 £ OFF. Moyenne des quatre autres 77 249,25 £,
contre 81 700,5 £ JOINED final (−4 451,25 £). Défauts B2 et bus_fixes à zéro.
Les pistes a/c sont livrées isolables, sans prétention de qualification. b n’est
pas codé faute de justification du mécanisme demandé ; le diagnostic du scan
contredit l’abandon supposé pour faible couverture. La cause complète de substitution
(classement économique, géométrie de trajet et calendrier) reste non isolée ;
aucune nouvelle politique hors demande n’a été introduite.

Code : bus_districts.nut:274/296 (pending, cargo),
bus_districts_overrides.nut:337/367 (diversité, distance), :1576/:1798 (projection),
:2112/:2119 (installation, reprise), task_road.nut:574 (maintenance OFF),
builder_road.nut:6475 (ordres), projects_selection.nut:1624 (LIVE),
info.nut:405 et settings.nut:612 (masque). Aucun yield dans try ni closure ajoutée.
230 tests ROAD100 réussis (3 ignorés), 7 tests V251 réussis, diff --check propre.
La projection ≥64 lignes et le rollback moteur refusé restent validés par contrats,
non exposés au moteur. Le test de reprise ON→OFF avec changement effectif du
réglage stocké dans la sauvegarde n’est pas exécuté par le harnais actuel.

## Save/Load et conservation des preuves
`busB2_fix_roundtrip_20261029.json` : **OK**, graine 2026, code final,
masque 9, save_full_state=1, probes=6. Phase A 330 jours ; reprise du 1er juin
1970 pour 120 jours (aucune trajectoire au-delà d’un an). Onze sauvegardes A,
quatre B, `LOAD_RECONCILE saved=7 kept=7 dropped=0`, aucune erreur moteur.
Le harnais signale sa compagnie fantôme à la reprise ; ce smoke est une preuve
de chargement/exécution, pas un duel économique. Il ne prouve ni une grosse flotte,
ni l’exposition d’un quai pending, ni le changement de réglage ON→OFF.

Preuve compacte versionnée : `evidence/review/road1y_busB2_fix_20261029.json.gz`,
avec hashes des JSON/JSONL, bundles, santé, profits, télémétrie 17 et traces du diagnostic.
Résultats bruts, bundles figés, manifests et logs conservés sous `results/`.
La sonde temporaire couverture/top40 ne subsiste que dans son bundle diagnostic ;
elle n’a pas été livrée dans les campagnes économiques ou le code final.
Aucune campagne encore en cours. Aucun push ; aucun git config.
