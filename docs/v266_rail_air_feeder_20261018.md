# V266 — voyageurs rail en transfert vers un aéroport existant

Analyse et implémentation expérimentale du 18 octobre 2026, branche `v266`,
base `2c4efe86c56546882118e430e91237ac77601369`. Arbre initial propre.
Le master local a ensuite reçu des modifications documentaires ; aucune fusion,
aucun reset. Un seul nouveau réglage : `v266_rail_air_feeder`, défaut **0**
aux quatre difficultés. Aucune modification de `docs/taches.md`.

## Décision, preuves et hypothèse

La demande utilisateur définit une navette de voyageurs vers **notre** aéroport,
avec gare jointe et transfert sans chargement au terminus. Les diagnostics lus sont
`origin/v226:docs/v226_reseau_araignee_20261018.md` et
`origin/v242diag:docs/v242_rabattement_diag_20261018.md`.
Le modèle d'ordres adverse est vérifié dans
`ai/AAAHogEx-115/trainroute.nut:1334` ; aucun code adverse copié.

V242 distingue correctement le stock en gare du chargement des avions :
8–11 voyageurs pour environ 230 sièges **ne prouvent pas** des sièges vides.
Les pertes V139/V216 et V207+V212+V214 rappelées dans la demande motivent
les gardes ci-dessous ; elles ne qualifient pas V266.

Le paiement de transfert est virtuel : source locale OpenTTD **15.3** sous
`/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src`,
`economy.cpp:1219` (livraison finale), `economy.cpp:1235` (transfert),
`economy.cpp:1245` (part de transfert). Le billet complet n'est compté
qu'une fois dans le gain compagnie estimé ; pas de seconde soustraction de 75 %.

Hypothèse à exposer : des places effectivement restées vides peuvent être vendues
à des voyageurs d'une autre ville, sans acheter d'avion supplémentaire. Le flux
nouveau, le temps de correspondance et le gain compagnie restent **non mesurés**.

## Insertion et données

Références dans le code livré :

| Point | Insertion et contrat |
|---|---|
| `info.nut:16`, `settings.nut:60`, `globals_pre.nut:694` | Booléen 0/1, quatre défauts 0, une seule lecture de réglage. |
| `scheduler.nut:9` | Observation protégée avant dispatch ; une ligne et au plus un avion par appel, sans liste globale de véhicules. |
| `rail_air_v266.nut:30` | Avion appartenant à une ligne AIR existante, deux ordres correspondant aux deux gares, en marche, vitesse positive, ordre courant de gare. |
| `task_projects.nut:1147` | Une recherche feeder terminée dépose son plan ; elle ne dépense rien avant la passe AIR normale et n'entre pas dans K_pass/C69. |
| `task_projects.nut:1992` | Recherche/pose seulement à la fin d'une passe normale sans construction. |
| `rail_air_v266.nut`, `_v266Reserve` | Tous les groupes de projets existants, nouvelles lignes AIR et renforts AIR ; capital du meilleur finançable réservé en plus de `OpexCashReserve`. |
| `builder_rail.nut:493` | Recherche de quais spécifique : `stationId` de l'aéroport obligatoire à B, aucun repli en gare indépendante. |
| `economy.nut:543` | Revalorisation après chaque économie recalculée sur quai/tracé réel. |
| `builder_rail.nut:2645` | Ordre B `OF_NON_STOP_INTERMEDIATE | OF_TRANSFER | OF_NO_LOAD`, source plein chargement. |
| `builder_rail.nut:3431` | Devis réel, réserve de cash, puis garde de valeur/jointure avant première dépense. |
| `task_rail.nut:392`, `task_rail.nut:1244` | Pas de renfort rail automatique ; identité AIR/StationID sauvegardée ; revenu compagnie exclu de la calibration rail. |
| `persist.nut:722` | Observations, offre et plan en attente reconstructibles, abandonnés au chargement ; identité des lignes conservée par le sérialiseur courant. |

`GetCapacity` et `GetCargoLoad` sont lus réellement par cargo, pas estimés depuis
le moteur : `script/api/script_vehicle.cpp:415` et `:428`.
`GetState` distingue le chargement (`script_vehicle.cpp:362`). L'ordre courant
et les deux ordres permanents sont recoupés avec les StationID de la ligne ;
le changement de destination déduplique les relevés d'un même vol.

Deux départs du même avion depuis le même aéroport fournissent un cycle en dates
calendaires et le minimum des deux nombres de sièges vides. Le débit annuel
est ce minimum × 365 / cycle. Pas de conversion des ticks du contrôleur en jours.
Un avion remplacé/recyclé avec âge décroissant ou ligne différente repart sans
historique. Une offre expire après son propre cycle observé. Un seul feeder
par aéroport empêche plusieurs chantiers de vendre les mêmes places.

La ville source doit avoir une production passagers positive, ne pas être une
ville de l'une de nos lignes AIR ni déjà servir d'origine rail. Les filtres
de proximité rail existants restent appliqués. CargoDist est explicitement
refusé : sans demande par destination, les places ne sont pas vendables selon
ce modèle (`script/api/script_cargo.hpp:71`, `:162`).

## Valeur et financement

`OpexLineEconomics(..., "feeder")` réutilise matériel, accélération, devis,
amortissement et quai du modèle courant. Le type distinct utilise **un seul sens
chargé** (`economy.nut:91`, `:258`). La construction livre une seule rame sur voie
dédiée. La capacité vendue est le minimum de : débit de sièges vides observé,
capacité d'une rame dans le sens chargé, production mensuelle source × note
modélisée × 12. Si le modèle avait choisi plusieurs rames, ses coûts sont
conservés : cela sous-estime le gain, sans inventer une économie de coûts.

Valeur annuelle = places vendables × `AICargo.GetCargoIncome` − marche −
amortissement du train et de l'infrastructure. La distance est source →
destination finale, **pas** la somme des tronçons (`economy.cpp:1221`).
Le délai inclut remplissage du train (capacité / production), marche rail et
un cycle aérien observé, provision prudente pour attente + vol. L'API convertit
les jours en périodes cargo (`script/api/script_cargo.cpp:72`).

Cette valeur est une estimation marginale compagnie, jamais un revenu rail
admis dans les groupes `candidateGroups`, ni dans `affordable`, ni dans
`fundScore`. `roi=0`. Les prédictions de profit/revenu de la ligne rail livrée
sont à zéro pour ne pas enseigner le billet complet à C70 ; la vraie dépense et
les profits de véhicules restent collectés normalement.

La réserve AIR est calculée avant l'A* et **recalculée** avant pose, depuis
les projets existants encore valides et la caisse réelle, sans emprunt nouveau
pour le feeder. Le score est recalculé sur une copie, avec le dénominateur courant
de `projects_selection.nut:773`, car un projet auparavant trop cher peut ne pas
avoir de `fundScore`. Le devis physique remplace ensuite le capital estimé ;
`capital réel + réserve AIR + réserve ordinaire` doit tenir dans la caisse.
Le créneau de construction normal est laissé à AIR. Cela protège contre le
mécanisme de caisse V149 et le classement gonflé V139 ; cela ne démontre pas
l'absence de coût d'ordonnancement V139d.

Le résultat propre du train n'est pas un critère de rebut. Si la ligne AIR
parente disparaît ou cesse de servir cet aéroport, la navette est retirée par
`_triggerScrapLine`, qui conserve l'infrastructure partagée.

## Seuils et coût en opcodes

Supprimés de la conception : 80 tuiles, 30–60 tuiles, 150 000 £, année de
démarrage forcée, remplissage 90 %, 1–3 satellites et « ~60 % d'opcodes ».
Ce ne sont ni des mesures V266 ni des mécanismes physiques établis.
Les seuls facteurs nouveaux sont des unités (12 mois, 365 jours), des identités
et des contraintes physiques (une rame dédiée, deux extrémités, une offre par
aéroport). Les bornes existantes de recherche de sites sont réutilisées avec
leur source (`builder_rail.nut:22`, `:23`) ; elles ne sont pas présentées comme
des optima économiques. La commande native de jointure tranche le spread et
l'autorisation de jointure distante.

Sans réglage : uniquement gardes booléennes, déclaration/chargement du réglage
et chargement des définitions ; aucun scan, modèle économique, allocation d'offre,
mesure d'opcodes ou nouvelle sélection. Les chemins historiques restent inchangés
derrière ces gardes. L'identité de trajectoire bit à bit avec un ancien binaire
n'est pas affirmée : ajouter une garde peut décaler les opcodes.

Avec réglage : observation O(1) hors traitement d'une ligne feeder (recherche de
sa parente en O(lignes)), examen d'une ville par passe inactive, réserve
O(projets + revalidations moteur), recherche de quais et A* bornées par les
constructeurs existants. Aucune économie d'opcodes chiffrée n'est revendiquée.
Sous `DECISION_LOG`, `V266_OPS` cumule mensuellement appels/opcodes d'observation
et de préparation/pose ; le coût des tranches A* reste dans `RAIL_ATTEMPT`
(`search_ops`, `ops`). Les autres journaux sont `V266_SEATS`, `V266_VALUE`,
`V266_RESIDUAL`, `V266_SEARCH` et `V266_BUILD`.

## Risques, validation et banc proposé

La production d'une ville est un plafond, pas une mesure de captage du quai.
La note et la capacité rail restent modélisées. Deux vols ne prouvent pas un
remplissage stable ; une correspondance peut perdre du temps ou concurrencer
une desserte routière. La recherche de quais conserve un filtre d'acceptation
locale à B, plus restrictif que le transfert ne l'exigerait. Le délai d'A* peut
faire expirer les mesures ; la pose est alors refusée. La réserve ne prédit pas
un projet AIR absent du vivier. Les plans/observations en cours ne survivent pas
à Save/Load, contrairement aux ordres de transfert et à l'identité des lignes.
Le suivi spécifique exige le réglage actif après rechargement ; éteindre le
réglage sur une sauvegarde expérimentale n'est pas une procédure de migration.

Contrats dans `sweeps/test_v266_rail_air_feeder.py` : garde OFF, réglage unique,
chargement réel, direction/déduplication, expiration, réservation AIR et renforts,
jointure stricte, ordres, devis avant dépense, reprise sans insertion au
portefeuille, sérialisation et cycle de vie. Le contrat historique de capture/
rollback retire **exactement** la nouvelle garde V266 avant comparaison à son
empreinte antérieure ; l'empreinte n'est pas remplacée.

Tests Python seulement : ils ne compilent pas Squirrel. Aucun Docker,
`run_c66_reference.py`, moteur OpenTTD ou push exécuté, conformément à la demande.
Validation économique et Save/Load réel **non exécutés**.

Suite complète demandée exécutée :
`PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"` :
**2 007 tests, OK**, 3 ignorés et 8 échecs attendus préexistants, 24,462 s.
`git diff --check` passe. Les messages de smoke/refus/timeout imprimés par
les tests sont ceux de leurs fixtures simulées ; aucune partie n'a été lancée.

Plan proposé, non lancé : exposition en partie complète avec deux bras du même
arbre `OpexAI[v266_rail_air_feeder=0]` / `OpexAI[v266_rail_air_feeder=1]`, sondes
identiques via `probes=6`. D'abord compilation/santé 1×1, puis diagnostic
d'exposition 3 graines (42, 100, 999) × 3 ans : vols effectivement relevés,
plans joints, transfert réel, hausse des embarquements de la parente, caisse
réservée respectée, coût `V266_OPS`, retrait/rechargement sans destruction
d'aéroport. Cet échantillon ne qualifie aucun gain ; absence de feeder ou de
hausse d'embarquement impose un diagnostic, pas une porte économique aveugle.
Après exposition, pré-enregistrer porte A **40×3 `gain_short`**, métrique
`profit_year`, seuil relatif **4 %**, Wilcoxon exact bilatéral p < 0,05,
IC95 bootstrap moyenne bas > 0, garde valeur **5 %**, 20 000 bootstrap, graine 0.
Une porte A saine et pass ouvre seulement la porte B **20×10 `non_erosion`**.
Défaut 0 maintenu ; aucune adoption n'est demandée dans cette tâche.
