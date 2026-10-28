# ROAD100-16 — liaisons express entre grandes villes à forte captation

## Contrôle capacitaire V28 et PAX heldout — 28/10/2026

V28a a réellement ajouté deux quais sur des lignes PAX déjà
2/1 ou 1/2 (4/4 jeux sains, H3 ON−OFF +2 904 £/an,
p=1), sans démontrer l'hypothèse de départ 1/1.
Après correction, V28b n'admet que la première pose depuis
1/1 et la seconde sur preuve physique sauvegardée.
Le pilote ROAD-only `road100_v28b_pax_double_from11_roadonly_2x3_20261028`
est sain (4/4), mais **zéro pose** : deux lignes
PAX d'âge2 déjà 2/1 ou 1/2, une seule 1/1 rentable
avec 26 PASS en attente pour un seuil 105.
H3 : Opex ON **83 699 £/an** contre AAA routier
**1 032 465 £/an**, soit **8,11 %**, ON−OFF
**−1 179,5 £/an**, Wilcoxon p=1. Aucune A40×5,
défaut V28=0, ROAD100 **0/5 parités**. Une première
pose en 1972 exigerait au moins 1973 pour finir 2/2 :
le pilote trois ans ne démontre pas cette séquence.

Le diagnostic mature heldout (`diag_road100_pax_heldout_20261028.py`)
sur V24 ON mesure des facteurs train réel/prédit
revenu **6,454** et profit **18,809**, améliorant
la MALE sur deux graines test, mais seed999 régresse ;
seules les lignes construites et survivantes sont
observables, seed2026 domine le gain. Il ne justifie
ni une multiplication des prédictions de nouveaux
projets ni la baisse des filtres ROI/C75. La priorité
structurelle reste la preuve *ex ante* de bassins
interurbains physiques et leur vraie desserte, jamais
le waiting post-construction d'AAA.

Contrôle V28c après la réparation des marqueurs de quais :
3 184 tests verts, projection OFF et V262 intacts ;
smoke ROUTE seule `road100_v28c_recovery_compile_roadonly_1x1_20261028`
2/2 sain et neutre à H1. Ce résultat démontre la
compilation, pas la démolition ou deux poses successives.

**Prérequis de marché ROAD100-29 (audit V26)** :
SITE_FIRST a dépensé 106,14 millions d'opcodes en
205 préplans, dont 181 TRACEX et seulement
24 admissions. Captation médiane 28 PASS/mois,
profit prévu médian290£/an, ROI médian3,2 %.
Le filtre des centres12..42 interdit toute admission
d43..80 par ce générateur ; les autres chemins
ne démontrent qu'une ligne réelle d47 dans V26.
Les 37 refus supplémentaires C75 sont tous des
ROI<25 %, non un blocage de trésorerie.
Pour combler les 2,038 M£/an de déficit H5,
même +25k£/an net par ligne supposerait environ
82 nouvelles lignes ; ce revenu marginal n'est
pas prouvé par les survivantes existantes.
V29 commence donc par un **SHADOW opt-in défaut0**
de demande PAX marginale et de vrais sites BUS sur
distances43..80 : aucun projet, score, gare ou revenu
réel ajouté sans chantier. Interdire l'oracle de
waiting AAA, compter les opcodes et ne poursuivre
vers un vrai constructeur qu'après preuve préalable
de marché, de coût et de ROI suffisants.

**Pilotes V29 SHADOW, 28/10/2026**, bundle
`42e53b9f8099894cf180ac957700023f58c1cca592067ad2bb6d953e6dbfe55c`.
Sur cinq graines ×1 an, Opex ON−OFF **+3 325£/an**
(p=0,0625), Opex ON/AAA **15,31 %**, 0/5
parités. Sur deux graines ×2 ans, H2
ON−OFF **−4 966£/an** (p=0,5, valeur −9,24 %),
ON/AAA **12,28 %**, 0/2 parités.
La sonde consomme 21k..24k opcodes/an,
mais n'émet **aucun projet** : ces deltas
sont des dérives d'exécution à investiguer,
non un profit supplémentaire de marché.
Sur les seuls couples ayant des façades
physiquement plausibles, 7..12 PASS/mois
produits à l'origine, revenu aller plafonné
à **2 016..3 312£/an** en supposant
une livraison sans délai, sans devis
de route (`cost_quote=-1`, ROI réel -1).
**V29 NO-GO pour adoption**, défaut0 ;
aucune Gate A40×5. Un nouveau mécanisme
doit mesurer une capture multi-sites plus
importante et un devis avant tout chantier.

## Résultat complémentaire ROAD100-27b — 28/10/2026

Pour éviter l'ancien A* LONG, V27b a cherché des corridors MAIL
séparés de 43..80 tuiles **uniquement sur route préexistante
réellement connectée dans les deux sens**, sans remise de coût ou
recette fictive de retour. Pilote
`road100_v27b_mail_existing_long_roadonly_2x2_20261028`,
bundle `33e0a87857550a6e69467419826274d2deb7e97a4f3b1b7c4ac7bc688bad8220` :
4/4 parties saines ROUTE seule, 8 préplans tentés, **0 admis,
0 nouvelle ligne MAIL longue**. Générations 166k..375k
opcodes ; profit annuel de société H2 **−6 081,5£**
ON−OFF (0V/2D), valeur −11,16 %. **V27b NO-GO,
défaut0, aucune porte A40×5.** Cette absence d'exposition
ne prouve pas qu'aucun corridor n'existe sur la carte.
L'objectif ROAD100 reste **0/5 parités**.

Contrôle physique V27b2 : les sites préférés du scanner fret
générique n'avaient pas de vraie façade routière. Le filtre
`existingOnly` (uniquement V27b) répare ce contrat, mais expose
alors **4/4 échecs BFS** sur chacun des premiers couples de
villes seed42 et seed2026 ; aucun corridor produit. À 256 nœuds
de recherche, `null` ne distingue pas absence de route complète
et dépassement du budget BFS. Deux préplans consomment chacun
plus de 538k opcodes, sans admission. Ne pas grossir aveuglément
le BFS ou réutiliser l'A* LONG ; tester d'abord les composantes,
le coût marginal de route et les bassins PASS réellement libres.

## Mise à jour de priorité — 28/10/2026

LONG v19b ne construit toujours aucun corridor sur seed42 et son audit
de demande physique plafonne les deux couples préférés à 35/31 PASS/mois
en hypothèse très favorable. Le MVP ROAD100-20 PAX_PORTFOLIO a ensuite
construit de vrais satellites joints sur cinq graines et produit des
`LINE_REVENUE`, **mais son V20e reste à 0/5 parités** : ratio Opex/AAA
11,8/6,5/4,0/2,9/2,3 % après 1–5 ans. Il ne faut ni extrapoler le
gain fictif d'un LONG non bâti, ni multiplier les balayages de cartes
ou les opcodes sans construction rentable.

Le nouveau ROAD100-21 porte donc temporairement la priorité sur la
**diversification des lignes fret** issues de production et acceptation
ex ante, avec jusqu'à trois cargos par passe et garde de chantier
physique, un seul TopK et un seul générateur PAX. L'option ROAD_BATCH
garde ROI ≥25 %, capital +50k£ et quatre lignes au plus par passe.
Les pilotes ne justifient pas de changement de défaut ; LONG et
PAX_PORTFOLIO restent documentés comme résultats négatifs en profits
de société, pas comme victoires. L'objectif 5/5 est toujours ouvert.

La qualification exploratoire V21 5×5 a depuis confirmé 10/10 duels
sains et une amélioration descriptive ON−OFF de **+14 976 £/an** à cinq
ans (3V/2D, Wilcoxon p=0,4375), mais seulement **3,0 % du profit annuel
réalisé d'AAA** et aucune parité à 1–5 ans (13,4/10,2/5,4/3,4/3,0 %).
V21 reste donc un **levier physique non qualifié**, pas une résolution de
ROAD100 ; ni LONG ni V21 ne doivent être adoptés sur cette base.

Essais de désenclavement après V21 : ROAD100-22 distingue les origines
fret par cargo (sans source réutilisée pour le même cargo), mais le
diagnostic isolé 5×1 atteint seulement +199 £/an, quatre égalités.
ROAD100-23 essaie ROI de second chantier 15 % au lieu de 25 % avec
réserve de 50 k£ inchangée ; le 5×1 gagne +585 £/an en moyenne mais
perd 29,62 % de valeur. **Aucun de ces essais ne qualifie une adoption**
et le déficit de réseau et de véhicules par rapport à AAA reste la
priorité structurelle ; les options restent défaut 0.

Nouveau contrôle capacitaire V24 : contrairement aux essais LONG et aux
plafonds virtuels de flotte, deux véritables quais camion ont été joints
en moteur sur seed42 avec 300£ payés et refleet 2→4. Ce chantier existe,
mais à 2 ans le delta économique moyen sur seed42/2026 est −8 693£/an.
L'exploration 5×5 a ensuite confirmé 11 doubles quais sur les cinq graines
et 22 camions achetés : H5 Opex/AAA **3,2 %**, ON−OFF +8 887£/an
(5V/0D, p=0,0625) mais H2 −1 412£/an, aucune parité. V24 reste opt-in.
ROAD100-25 cible maintenant les 1 301 refus PAX répétés de V21 :
revalidation à la sélection commune synchrone/PO01C des villes déjà
desservies LIVE, sans altération de la demande ou du classement des
projets encore constructibles. Opt-in défaut0 ; préenregistré avant smoke
seed100/2026 sous ROAD seul sur le même cumul V21+V24, puis 5×5 si
exposition. Tests de profit annuel effectivement réalisé, non-érosion,
valeur −5 %, Wilcoxon p<0,05 avant A40×5. Les deux mécanismes restent
insuffisants sans meilleure captation et bien davantage de lignes.

Postscriptum après pilotes V25a/V25b sur deux graines ×3 ans : le filtre
réduit bien les rejets de projets périmés, mais `profit_year` ON−OFF à
trois ans est respectivement **−10 443£/an** et **−10 246£/an** ;
valeur −13,87 % puis −11,48 %. Aucun prolongement 5×5, aucune adoption.

Préréservation V26 (sans LONG) : étendre physiquement seulement le quai
limitant d'une ligne PAX déjà rentable, deux ans après sa création selon
le compteur d'exercice, vrai StationID/caisse/bus, pas de bonus recette.
Pilote strict ROAD-only 2×3 : trois quais et refleet 2→4 observés,
profit société H3 ON−OFF +14 862,5£/an (1V/1D), ratio ON/AAA 10,4%,
0/2 parités. Le signal est exploratoire, le test p=1 ; diagnostic 5×5
préenregistré sur les graines 42,100,7,999,2026 et même bundle source.
Résultat définitif exploratoire V26 5×5 : 10/10 sains, H5 ON−OFF
+9 121£/an mais 3V/2D, p=0,625 et IC95 recouvrant zéro ; H5 ON/AAA
seulement 3,7 %, **0/5** horizons. Pas de A40×5, pas d'adoption.

ROAD100-27 MAIL, pilote 2×2 : seulement une nouvelle ligne de courrier
ville→ville, source/sink camion physiques, 1 fourgon, profit prédit
273£/an pour 6 292£ de chantier. H2 ON−OFF −10 259,5£/an,
valeur −22,45 %, aucun seuil AAA. Le court centre 12–42 ne reproduit
pas les corridors MAIL AAA médians 88–107 ; V27a reste opt-in0 et
doit être repensé pour marchés interurbains réellement rémunérateurs.


Préréservation du 28 octobre 2026, avant code ou banc ROAD100-16.
Objectif cumulatif : profit annuel réalisé OpexAI / AAAHogEx-115 >=100 %
aux horizons 1, 2, 3, 4 et 5 ans en 1v1 ROAD seul, sans érosion.

## Constat avant intervention

Dans la référence graine 42 de ROAD100-10, AAA ouvre dès mars 1970
Danville–Little Sintburg, distance centre-centre 158, 134 tuiles entre
arrêts. Projet initial : 327 PASS, 27 bus de 35 places, investissement
prévu 210 574 £. Au 1er décembre : 28 bus et 119 082 £ de profit cumulé
des véhicules sur cette ligne (ni revenu brut ni profit société net).
Opex possède une ligne PAX distance32, captation site ~27 PASS/mois,
deux bus et 8 179 £ de profit véhicules. La trésorerie disponible
ne suffit pas à expliquer cette différence de clientèle et capacité.

Le générateur site-first dans candidates.nut:1995 limite les paires de
centres à 12–42. Dans builder_road.nut:558/580, les couples et traces
sont bloqués à 48 tuiles ; OpexRoadBfsPath 96 explore des noeuds de
route EXISTANTE et ne construit pas la liaison. Dans economy.nut:718–725
le modèle ordinaire plafonne à 2 bus sauf override, et le coût prédit
valorise même les arêtes routières déjà présentes comme nouvelles.
Lever seulement 48 ne crée ni connexion physique ni profit réalisé.

## Intervention séparée

Créer un nouvel opt-in à défaut 0 dépendant de ROAD100_SOLO_PAX
et ROAD100_SITE_FIRST ; OFF et variantes rejetées restent inchangés.

1. Avant chantier, au plus deux paires de grandes villes à distance
   80–170 par passe coopérative ; sélectionner deux vrais sites de bus
   traversants avec captation marginale vérifiée (cible >=80 PASS/mois
   à chaque extrémité, >=200 ensemble), exclure les chevauchements.
   Montrer un tracé physiquement réalisable sur routes existantes,
   raccords et ouvrages testés, avec garde explicite sur les opcodes.
   Coûts des arêtes déjà routières et manquantes distingués.
2. Admission seulement si corridor bidirectionnel, arrêts et dépôt
   vérifiés et budget total gares+voirie+bus laisse >=50k £ en caisse.
   Même plan entre classement, admission et chantier ; pas de repli
   L historique changeant les sites. Financement et rendement nets
   prudents, sans inventer le revenu des PASS non transportables.
3. Après construction, deux StationIDs, ordres partagés [A,B],
   2–4 bus initiaux réellement financés. Extension graduelle à 20–30
   seulement selon attente, fréquence, capacités, profit effectivement
   réalisé et cash, sans surcharge d'un seul quai. Préserver refleet,
   Save/Load et rollback ; aucune adoption du défaut sans preuves.

La recherche doit rester bornée en couples, sites, arêtes et opcodes,
sans extrapoler un simple Manhattan. Ne pas modifier ESTIM31 ni
introduire de facteur artificiel de revenu ou profit ROAD100-15.

## Décision expérimentale

Projection OFF, tests statiques puis un diagnostic graine42 ×1 an
pour vérifier sites, chemin, coûts et budget sans qualifier un shadow.
Si une construction réelle sûre est démontrée : 5 graines fixées
42,100,7,999,2026 ×5 ans en duels appariés OFF/ON, bundle commun,
mesurer cinq profits annuels réalisés, bénéfice de ligne, voyageurs
livrés, stations, bus, cash, valeur et opcodes. Garde valeur −5 % ;
non-érosion horizons 1–4. Seulement après signal favorable : porte
A 40×5, Δmean>=+4 %, p Wilcoxon<0,05, borne basse IC95>0,
valeur>=−5 % ; contrôler cinq ratios Opex/AAA >=100 % séparément.
Aucune porte B avant A favorable et protocole autorisé.

## Tranche diagnostique v2 du 28 octobre (avant smoke)

Le premier shadow (graine42 ×1 an, 2/2 parties saines) a refusé en
`OPCAP` dès le premier couple de villes 129 tuiles : 482 759 opcodes
dans le helper et 527 141 dans la préqualification totale, sans tester
de deuxième site ni connexion, malgré le cap 250k *soft*. Le résultat
économique apparié de ce shadow sans construction est −9 438 £/an,
valeur −28,93 % ; il n'est pas un effet de nouveau réseau, mais un
signal de pression sur la planification/ordonnancement.

**v2 préinscrite** : remplacer exclusivement, dans la sonde LONG,
la recherche de sites voirie rayon16 par une recherche physique
rayon8, ≤48 tuiles routières éligibles et ≤8 AITestMode par extrémité,
garde locale 110k ops ; classement des quatre vrais arrêts admissibles
par leur production native (et distance en départage). Conserver le
chemin site-first OFF et la voie ON courte sans modification.
Journaliser le maximum de production de chaque arrêt, le nombre de
sites et le meilleur couple ; critère 80/80/200 inchangé pour
`SHADOW_OK`, mais considéré comme hypothèse forte à éprouver, et
non preuve de besoin AAA à un stop unique. Une seule préqualification
LONG par an malgré les régénérations PO01C. Refaire projection OFF,
tests et smoke même graine42 1×1 sur un nouveau bundle ; ne lancer ni
5×5 ni construction si tous les arrêts demeurent très en dessous
de l'objectif physique.

## Shadow v3 : union physique exacte (préréservation avant code)

La v2 graine42 1×1 est saine (2/2 parties). Deux paires de centres
129/84 ont été préqualifiées en 63 675 opcodes au total. Les meilleurs
arrêts isolés par ville captent 11/11 (total 22) et 11/17 (total 28)
PASS/mois, aucun BFS, aucun chantier. Delta −9 532 £/an, valeur
−18,45 % dans ce seul smoke : NO_EXPOSURE, non qualifié.

L'audit de 746 admissions site-first historiques donne seulement 21–38
PASS/mois pour les deux arrêts simples réunis. AAA exploite cinq tuiles
d'arrêts (deux StationIDs, satellites joints) ; les LGRP supply bruts
138/182 ne sont pas des volumes mensuels. Les intervalles avril–mai
compatibles indiquent ~213/268 PASS/mois, oracle inaccessible à l'IA.

Intervention v3 uniquement diagnostique : sélectionner une racine
d'arrêt physiquement testée puis jusqu'à deux satellites par ville,
dans station_spread ; produire la somme EXACTE des maisons sur l'union
des carrés de couverture, sans double compte, en retranchant toute
maison déjà couverte par une gare Opex distincte. Un Valuate natif 1×1
par extrémité, quatre sites préfiltrés au maximum, budget LONG 250k
soft, et aucun monde modifié. Journaliser meilleur arrêt simple, union,
delta, satellites, rejets de géométrie et coût des arrêts.
Les seuils physiques 80/80/200 sont conservés comme hypothèse de
marché ; l'AITest de satellites isolés ne prouve PAS leur construction
jointe au StationID. Aucun projet LONG admis au portefeuille sur le
seul proxy.

Prochain smoke apparié graine42 ×1 an sur nouveau bundle v3, puis
approfondir géométrie et connectivité seulement si le bassin union
présente une réelle demande suffisante ; pas de 5×5 économique ou
porte A sur un shadow sans construction.

### Résultat et décision d'extension du diagnostic v3

Le smoke v3 graine42 x1 est sain. Deux couples : unions exactement
11/12 PASS/mois (satellite +1 sur la deuxième extrémité), et
11/17 (aucun gain de satellite) ; 95 821 opcodes au total,
aucun test de corridor, ni projet, ni construction. Delta Opex
−10 681 £/an et valeur −41,64 % sur ce seul duel shadow ;
ce delta de planification n'est pas attribuable à un chantier.

Avant toute adaptation supplémentaire, vérifier à protocole identique
les **quatre graines prédéfinies restantes** 100,7,999,2026, chacune
1 an, même réglage ROAD seul et même code de shadow v3 (bundle
nouveau si les sources ont changé, sans interpréter les résultats
comme comparables à des effets économiques). Hypothèse à falsifier :
les meilleurs bassins union réellement constructibles peuvent-ils
dépasser 80/80/200 sans changer la sélection des quartiers ?
Si aucun ne le fait, priorité à la sélection urbaine/racines satellites
sur plusieurs quartiers et, si cela échoue encore, à une autre
architecture de desserte; jamais de faux profit pour forcer une porte.

### Résultats v3 sur les quatre autres graines fixées

Campagne road100_long_shadow_v3_union_other4_1x1_20261028, huit
parties (4×OFF/ON) saines à l'horizon; graine100 marquée
stagnation_suspect mais partie complète. Tous les huit couples LONG
refusés LOW_DEMAND, zéro test de chemin, de station jointe ou chantier.
La meilleure union par ville parmi les paires fixées est 10–21
PASS/mois, le bonus de satellite maximum +2 seulement ; 88–98k ops
par graine. Delta primaire à l'année terminale −3 002,5 £/an sur
quatre graines et valeur −29,76 % des moyennes, diagnostic sans
construction. Avec seed42, 0/10 paires préqualifiées.

### V4 préinscrite : diversification géographique des sites et chemin témoin

Le cap radius8/48 roads/8 AITest de v2 s'arrête trop tôt dans
le centre-ville et choisit quatre sites aux bassins presque
identiques, ce que les faibles deltas union prouvent. Nouvelle
tranche uniquement LONG shadow : rayon étendu jusqu'à 16 mais
**échantillonnage géographique déterministe** de routes existantes
(au plus 160 examinées, 16 AITest, 4 arrêts diversifiés),
privilégiant un site meilleur en production native ET des satellites
spatialement distincts dans station_spread ; borne d'opcodes
par scanner et globale soft250k inchangée. Ne pas augmenter le
nombre de stations achetées ni créditer une maison plusieurs fois.

Si tous les bassins union restent faibles, effectuer au plus UN
contrôle séparé de chemin existant entre les racines les mieux
classées, même sans demande ; journaliser PATH_ONLY, jamais
ROI ni projet. Aucune confusion entre chemin BFS observé et
possibilité de bâtir les routes manquantes.
Prévoir smoke v4 seed42 1×1 nouveau bundle; pas de campagne 5×5
sans preuve de marché et d'itinéraire physique.

### Rectificatif v4b (budget mesuré avant nouvelle partie)

Le smoke v4 seed42 a montré une union maximale de 12/9 puis
12/20 PASS/mois, plus de diversité mais toujours aucun marché
rentable. Le budget total LONG de 250k soft a été dépassé :
184 735 puis 150 717 opcodes sur deux paires, soit 335 452
au total. Le cap externe empêchait le second appel seulement
si la borne avait déjà été atteinte ; le helper reprenait son
propre budget neuf de 250k pour chaque paire.

Correction v4b isolée : transmettre au helper le reliquat
250000 − longOps, le faire respecter par ses deux scanners,
les deux Valuate d'union et les éventuels BFS/ROI. Le cap
reste soft pour la commande native indivisible ; ne pas
écrêter le journal ni attribuer du profit aux projets absents.
Rejouer uniquement un smoke v4b graine42 x1 sur nouveau bundle
pour vérifier le refus OPCAP et la limite mesurée cumulée,
sans porte 5x5 ni nouveau défaut.

### V5 préinscrite : diversification des couples et témoin de connectivité

Le smoke v4b est sain (2/2), mais les deux couples examinés partagent la
ville 22 (`22-28`, `22-23`) et leurs bassins sont très faibles : `12/9`,
puis second examen interrompu par le budget, 210 948 opcodes au total.
Le diagnostic ne teste aucune route (`tested=0`). Deux couples voisins
ne représentent pas toutes les grandes villes.

V5, sous `road100_long_intercity=1` strictement shadow : garder le
meilleur couple selon le proxy urbain, puis chercher le meilleur couple
**sans ville commune** ; à défaut seulement conserver le second meilleur.
Comparaison déterministe, un balayage des paires de villes, pas de
nouvelle valuation native, toujours au plus deux couples et 250 000
opcodes cumulés. Cette diversification sert à mesurer le champ
géographique ; elle n'autorise ni chantier, ni bonus de profit, ni
modification du choix des lignes normales.

À l'intérieur du helper, un unique essai `PATH_ONLY` indépendant du
seuil 80/80/200 peut utiliser les racines admissibles de la première
paire, sous réserve d'un reliquat d'opcodes explicite. Journaliser le
résultat séparément (route existante, longueur, motif, coût mesuré)
même si le refus économique reste `LOW_DEMAND`. L'existence d'un chemin
sur route publique n'est **pas** une preuve de stations cumulativement
jointes, de nouvelles routes constructibles, de financement ni de
revenu. Si le budget manque, journaliser `PATH_SKIPPED_OPCAP` sans
contourner le cap. Smoke neuf graine42 x1, projection OFF et tests
avant essai économique ; aucun 5x5 sans construction exposée.

### V5b préinscrite : priorité au témoin PATH_ONLY avant unions

Le premier smoke v5 graine42 x1 est sain (2/2) ; la seconde paire
devient bien `38-23` au lieu de `22-23`. La première conserve ses
unions `12/9`. Le PATH_ONLY n'effectue cependant aucun BFS : le
premier helper atteint ~140,7k opcodes et garde moins de 60k de marge
avant la sonde placée *après* les unions. `PATH_SKIPPED_OPCAP` est
correct mais ne renseigne pas la connectivité. Le deuxième helper
refuse OPCAP, total 212 427 opcodes, zéro chantier, delta −7 268 £/an
et valeur −15,41 % sur ce seul smoke, sans exposition économique.

Correction v5b isolée : appeler **une seule fois** PATH_ONLY dès que
les deux listes de sites sont disponibles, avant le travail coûteux
d'union, et conserver exactement les mêmes marges, borne 512 nœuds
par sens et cap global 250k. Garder les champs path_* et la raison
principale distincts. Si le diagnostic consomme le reliquat, refuser
l'union `OPCAP` sans construire ni fabriquer un score économique.
Projection OFF et smoke nouveau bundle sur graine42, pas de 5x5.

### V6 préinscrite : premier plan LONG susceptible d'être construit

Le smoke v5b graine42 x1 est sain (2/2), permet de mesurer pour la
première paire 17 nœuds de route connectée depuis A et 25 depuis B,
**aucun chemin continu aller ou retour**, 6 361 opcodes PATH_ONLY et
211 463 opcodes LONG cumulés. Deuxième paire `38-23` non qualifiée
faute de budget. Les unions restent `12/9` PASS/mois ; aucun profit
nouveau n'est exposé, delta −7 268 £/an et valeur −15,41 % sur ce
diagnostic (pas une campagne économique). Le témoin négatif confirme
qu'un projet LONG exige des arêtes à construire, pas seulement un BFS.

Intervention distincte `road100_long_build=1`, **défaut zéro** et
dépendante de `road100_long_intercity=1` + `road100_site_first=1` :
produire au plus deux candidats PAX 80–170 entre villes sélectionnées
de manière diversifiée, avec sites sur routes publiques et trajet LONG
composé de plusieurs coudes plats. La fonction de planification
vérifie les axes d'arrêt traversant, toutes les arêtes manquantes sous
AITestMode, le dépôt, les coûts des arêtes encore à poser et l'ensemble
des arrêts/véhicules. L'admission utilise la **production physique
locale des deux sites**, une économie nette positive (jamais la
demande totale théorique des villes) et le capital disponible avec
garde de 50k £. Les mêmes sites/tracé doivent être retrouvés au
chantier ; en cas de divergence refuser, jamais reprendre un plan
court sans signaler le changement. Deux StationID seulement dans
cette tranche : aucun satellite joint fictif. Flotte initiale limitée
au financement réel, aucun bonus de revenu. Période exploratoire :
un smoke apparié graine42 ×1 an sur bundle identique OFF/ON, puis
mesurer StationID, rails inexistants, construction de vraies arêtes,
paiements, opcodes, ordres A/B, véhicules circulants et passagers
livrés. Les règles 5×5 et 40×5 restent bloquées sans exposition
physique **et** signal économique favorable. Les anciens chemins OFF,
ROAD100-8 à 15 et estim_unifie=31 restent inchangés.

### V7 préinscrite : ne pas exclure les grandes villes avant le préflight

Le premier smoke v6 (graine42 ×1, bundle
`ddc1272ee12c7920d2e96fc17e7b4b3fe5f11f81b1b7f0e6eb0174a4d4044dce`)
est sain (2/2), mais zéro admission : 12 traces sur 2 paires de
sites refusées `UNBUILDABLE` pour villes 22–28, puis `OPCAP`
pour villes 38–23, total 362 913 opcodes. Delta Opex
−10 097 £/an et valeur −36,40 % ; sans exposition LONG ces
écarts ne prouvent pas l'efficacité économique du constructeur.

Problème de préclassement indépendant : le bassin LONG réutilise
les **40 meilleures villes selon une fraction de ~10 maisons**,
ce qui peut éliminer les villes de forte production mensuelle
totale avant même de tester un arrêt physique. En v7, et
**uniquement si `road100_long_build=1`**, construire une liste
LONG de 40 villes triées sur `AITown.GetLastMonthProduction`
déjà en cache de classement, avec départage stable par ID ;
classer les paires sur somme de ces productions totales comme
signal de recherche, sans jamais l'utiliser pour calculer le
profit ou l'admission. Tous les vrais revenus restent calculés
avec `stopA.value+stopB.value` et quote physique complète.
Même taille de pool 40, deux paires géographiquement distinctes,
cap 400k cumulatif, 0 nouvelle Valuate, zéro modification OFF.
Un smoke frais seed42 ×1 teste les ID de villes, tracés,
exposition et opcodes, avant une quelconque porte économique.

**Correction de protocole (28/10, avant le prochain smoke) :**
les manifests des diagnostics v5, v5b et v6 montrent AAAHogEx
avec `disable_veh_train=0`, `disable_veh_tram=0`,
`disable_veh_ship=0`, `disable_veh_aircraft=0`, donc **AAAHogEx
multimodal** malgré Opex ROAD seul. Les chiffres Opex−référence
de ces pilotes décrivent les effets d'exposition et d'opcodes,
mais leurs ratios Opex/AAA ne prouvent **aucune parité ROAD seule**.
Les conserver comme diagnostics physiques, ne pas les présenter
comme résultats de l'objectif. Toutes les nouvelles campagnes
doivent fournir explicitement au harness les quatre paramètres
`--aaahogex-setting disable_veh_train=1`,
`--aaahogex-setting disable_veh_tram=1`,
`--aaahogex-setting disable_veh_ship=1`,
`--aaahogex-setting disable_veh_aircraft=1` ; roadveh reste 0.
Contrôler les *deux bras du manifeste*, le bundle partagé et
la télémétrie de mode AAA avant d'interpréter les profits.

### V7b moteur et v8 préinscrite : sites larges, budget par paire

Premier smoke v7 ROAD seul `road100_long_build_v7_bigcity_dogleg_roadonly_seed42_1x1_20261028`
: **incomplet** à cause d'une erreur Squirrel dans `array.sort` :
`OpexRoad100LongSortTownTotal` renvoyait un booléen au lieu du
comparateur numérique −1/0/+1. Ne calculer ni victoire, ni ROI,
ni delta sur cette campagne. v7b corrige le comparateur, conserve
les paramètres AAA désactivant train/tram/navire/avion et vérifie
à nouveau projection OFF et tests.

`road100_long_build_v7b_cmpnum_roadonly_seed42_1x1_20261028`
(bundle `4475b95461d7a020c0083e4e6e0dcdac29522410897d3a7e9a305f2ac7ff5d45`)
: **2/2 parties saines**, classement grandes villes effectif,
paires `18–2` (centres 158), puis `26–10` (154). Premier
plan : 13 essais incl. six doglegs, première arête manquante
refusée `from=30852,to=30851,error=260`, motif `AITEST_BUILD_ROAD`,
limite opératoire atteinte après 293 399 opcodes plan ; second
plan refusé faute de reliquat, total 354 623, zéro ligne LONG.
Opex a 18 881 £/an, AAA ROAD seul 93 624 £/an,
soit 20,17 % sur **une seule graine** ; comparaison ON−OFF
+3 825 £/an mais SANS exposition LONG (c'est une dérive du
calendrier et des opcodes, pas un gain de nouvelle liaison).
La caisse/stations/flux du nouveau corridor restent N/A.

V8, changement isolé toujours `road100_long_build=1` défaut0 :
préserver le tri V7 de grandes villes sur production brute comme
priorité de recherche, mais scanner des **quartiers répartis sur
plusieurs couronnes et quadrants**, au lieu de s'épuiser sur les
premières tuiles au nord-ouest du centre. Scorer la production
**locale** sur tuiles routières visitées, retenir au plus quatre
sites passant AITest STATION_NEW par ville, sans nouveau Valuate.
Budget cumulé 400k par année ; répartir le reliquat du préclassement
entre les deux paires géographiquement distinctes, maximum 180k
opcodes par paire, afin d'en préqualifier réellement deux et de
ne pas permettre au premier corridor de dévorer tout le budget.
Le devis, la rentabilité positive et la garde de cash portent
toujours sur les arrêts physiques et les arêtes à construire,
jamais sur la production totale des villes. Refaire tests OFF,
V262 et smoke graine42 avec AAA ROAD seul, sans porte économique
si aucun nouveau chantier n'est observé.

### Vérifications ROAD-only v8–v12 et axe v13 (28/10)

Toutes les campagnes récentes ont désactivé chez AAA les quatre
types de véhicule non routiers, y compris TRAM, et ont conservé
le même bundle figé pour la référence OFF et la variante ON.
Les smokes successifs n'autorisent **aucune** affirmation de parité :

| Code | 1×1 seed42 | Exposition LONG et défaut causal |
| --- | --- | --- |
| v8 spatial | 2/2 saines | 0 chantier, `GEOMETRY`/`AITEST_BUILD_ROAD 260` puis deuxième scanner `OPCAP` |
| v9 | Invalide | Compilation Squirrel `parent` (nom réservé), exclu des ratios |
| v9b | 2/2 saines | 0 chantier, A* 90 états / 171 054 opcodes, `SEARCH_CAP` |
| v10 | 2/2 saines | 0 chantier, suppression des AITest par voisin, 91 états / 171 021 opcodes |
| v11 | 2/2 saines | 0 chantier, cache tuiles/arêtes, 116 états / 177 008 opcodes, progrès 55/158 |
| v12 | 2/2 saines | 0 chantier, A* optimiste à tests différés, 104 états / 176 441 opcodes, progrès 50/158 |

Le pipeline est bien branché : LONG dans le générateur, candidat
uniquement si `OpexRoad100LongConstructPlan` fournit un trajet physique,
`road100LongBuild` vérifié par dispatcher `OpexRoadPlanForActive` avec
sites, fronts, dépôt, longueur, devis et hash, puis chantier
transactionnel `OpexBuildRoadRoute`. Son absence d'exposition tient
encore aux échecs de tracé avant le devis ; les garde-fous ne doivent
pas être court-circuités.

**Préréservation v13** : nouvelle géométrie déterministe multi-segments
avec précontrôle du chemin entier à coût faible, puis `VerifyTrace`
physique arête par arête sous AITest ; contourner le premier obstacle
par un détour local ou bannissement explicite sans augmenter les caps
**85k/search, 400k/an, 80..190 arêtes**. Les anciens templates restent
des diagnostics, jamais un repli vers le constructeur court si les
stations diffèrent. Conserver le même chemin avant classement,
portefeuille et chantier. Un trajet préflighté n'est pas encore un
chantier ; un chantier ne prouve pas les voyageurs livrés.

La captation isolée des sites v8–v12 (maxima 21 et 17 PASS/mois)
ne rejoint pas le bassin d'AAAHogEx composé de cinq tuiles d'arrêt
pour deux StationIDs. `waiting=190` est un stock constaté après
construction, ni une production mensuelle ni un oracle admissible.
Après obtention du premier corridor réellement constructible, la
prochaine étape de préqualification devra vérifier l'union de
producteurs avant construction, sans double compte, et des flotte/ROI
finançables ; si l'économie rejette LONG, tester un nouvel opt-in
distinct de ROAD100-8, -14 et -15 plutôt qu'inventer le revenu.

Pour les smokes v9b/v10/v11/v12, Opex ON réalise 18 881 £/an
contre AAA 93 624 £/an en seed42 ; **aucun résultat n'est attribuable
au LONG**. Aucun 5×5 économique ni porte 40×5 avant exposition
physique et livraison observées. Objectif cumulatif : **0/5**.

### Rectificatif après moteur v13–v17 : site DT et coût partagé

La v13 dessine des polylignes complètes 80–190 et les vérifie
sous AITest : refus explicites erreur 1281 (voie municipale) et
260 (aire occupée), malgré 163 arêtes effectivement testées.
**V14** limite la première tentative de paire à 180k opcodes
sans relever le cap annuel 400k : la seconde paire est alors
scannée mais ne comporte aucun arrêt B admissible sur 6 tests.
**V15** réessaie sur la même arête routière le quai traversant
au tile `front`, avec production native de cette seule tuile et
un AITest STATION_NEW indépendant. Le second bout passe alors
de 0 à **3 quais admissibles**, toujours sans dépassement des
12 AITest/scanner. **V16** fixe les arêtes initiale et finale
sur les `front` réels connectés ; **v17** examine d'abord les
fronts orientés vers la destination. Ces deux derniers pilotes
rencontrent encore pentes, maisons et raccords urbains bloquants.

Les cinq pilotes v13 à v17 sont des duels 1×1 seed42 sains,
Opex ROUTE seule contre AAA ROUTE seule ; **zéro LONG admis,
zéro LONG construit, zéro nouvelle livraison démontrée**.
Ils ne permettent pas d'estimer l'effet économique d'un corridor.
Ne pas lancer 5×5 ou A40×5 sur ces variantes sans exposition.

**Précision d'audit v17 (28/10).** Sur l'arête
`31904→31903` (`160,124→159,124`), `AreRoadTilesConnected` était faux
et `BuildRoad` sous AITest a échoué avec le code 260. Le journal ne
contient **ni** `IsRoadTile`, `IsBuildable`, pente, propriétaire ou
composantes routières de ces deux tuiles, **ni** sauvegarde de carte.
On ne peut donc pas qualifier cette arête de maison ou route municipale
non raccordée avec certitude. `obstacle_area_probes=0` : le diagnostic
d'obstacle du traceur n'avait pas été exécuté sur cette arête.
Le prochain pilote doit instrumenter uniquement le premier refus et
vérifier les liaisons existantes avant de tenter de les reconstruire.

**Pilote v18, 28/10** — route longue par deux manchons de voirie
existante bidirectionnellement connectée (six pas maximum depuis
chaque quai), jonction centrale à coudes plats et AITest complet.
Campagne ROAD-only appariée
`road100_long_build_v18_road_sleeve_roadonly_seed42_1x1_20261028`,
bundle `836a773198c18ea5bc2257693aeb12ad960d178dfbde470075e38e7038f3690c`,
2/2 parties saines. Sur les couples 18–2 et 26–10,
les sondes suivent 12 et 14 pas existants cumulés entre les
variantes de tracé, mais échouent respectivement sur des
arêtes 260 `(162,127)→(161,127)` et
`(72,234)→(71,234)`, puis `OPCAP`.
**0 ligne physiquement construite, 0 LONG admise, aucune
recette LONG.** Opex `profit_year=18881`, AAA 93624,
ratio 20,17 % ; le delta ON−OFF +3825 £/an ne peut pas
être attribué au mécanisme non construit. Prochain essai :
adapter les *sorties urbaines*, sans relever les caps ni
recycler ces simulations isolées comme preuve de gain.

**Pilote v19b et décision de priorisation (28/10)** — v19
invalide par identifiant Squirrel réservé `parent`, corrigé
en `prev_index` avant v19b. Bundle v19b
`26c0d0145f29d47634ecae9405f786eea932df0b9ecc6204d1f6c642be657594`,
2/2 duels ROUTE seule sains mais **0 LONG construit** :
premier refus 18–2 à l'index 17 sur route de ville (1281),
26–10 sur code 260 puis absence de sortie acceptable.
Un audit ex ante conservateur estime, pour les seuls sites
testables constatés, au maximum ~35/31 PASS/mois bruts,
soit ~4/3 transportables et environ +1 322 / +746 £/an de
profit projeté avec le moteur routier du profil (non réalisé).
Face à AAA, cette exposition physique même réussie ne serait
pas suffisante pour l'objectif 100 % ; priorité au mécanisme
distinct de captation multiquartiers, sans relever 85k/400k.

Prochaine intervention structurelle, à isoler dans un nouvel opt-in
à défaut 0 si elle se distingue de LONG : une sélection de
bassins **préconstruction** par union exacte de producteurs sur
plusieurs quais d'une même StationID, suivie de tracés qui
réutilisent les routes réellement connectées, puis de la flotte
progressive dimensionnée sur les passagers **transportables**.
Le modèle garde les coûts complets de sites, route, dépôt, bus,
cash >=50k et les garde-fous de circulation. N'utiliser ni le
stock AAA `waiting`, ni les profits réalisés d'AAA comme variables
prédictives propres à Opex. Aucune activation automatique de
ROAD100-8..13 rejetés, ROAD100-14 ou ROAD100-15 sans preuves.

## ROAD100-32 — corridor segmenté, préenregistré avant modification et banc

**Constat mesuré préalable** : baseline ROUTE seule 40×5, ratio de profits
annuels de société H1..H5 6,02 / 4,84 / 2,61 / 1,71 / 1,38 %.
AAA exploite 602/754 lignes PASS à distance de gares 81..160 fin 1974,
Opex zéro ; LONG v19b ne construit aucun corridor, ses sites seuls ne
suffisent pas. V30a a construit 31 nouvelles lignes PAX sur cinq graines,
mais reste à 0/5, H5 +5 500£ ON−OFF, p=0,625. Aucun chiffre de profits
de ligne AAA n'est introduit dans la décision Opex.

**Intervention strictement opt-in** `road100_segmented_corridor=1`, défaut
0 aux quatre difficultés, ROUTE seule et `road100_long_build=1` requis.
Au lieu de relancer uniquement le constructeur LONG monolithique, tenter
une seule trace déterministe de **80..190 arêtes** par couple de quais
réels, répartie en segments locaux de 12..20 tuiles. Les ancres suivent
le vecteur entre les vraies stations, avec petite recherche sur voirie
existante ou terrain clair. Dans chaque fenêtre locale, utiliser une
recherche bornée (au plus 80 expansions, déplacement cardinal, coût plus
favorable aux arêtes routières déjà connectées), sans cheminement global
non borné. Respecter l'axe des quais DT et exclure cycles, maisons,
stations tierces et tuiles non constructibles. Ce n'est qu'un **projet de
trace** : revalider chaque arête par `OpexRoad100LongVerifyTrace`/AITest,
le dépôt, les vrais quais, les frais de nouveaux bits ×3 et la caisse
(capital +25 % +50 k£) avant admission ; la construction réexécute le
préflight, impose le même hash de trace, pose en jeu et rollback en cas
d'échec. Ne pas compter de passagers supplémentaires, satellites, retours
ou véhicules non construits : cap physique habituel, profit net conservateur.

**Bornes et garde-fous** : au maximum deux couples par année et 400k
opcodes souples partagés par le générateur, 180k pour le premier si deux
couples ; au plus 3 paires de sites et une tentative segmentée par paire,
une fenêtre locale ≤80 expansions, maximum 12 ancres ; si dépassement,
refuser sans publier de candidat. Aucune augmentation des caps de BUS,
aucune nouvelle mémoire persistée, ni modification des voies OFF,
PO01C ou multimodales. Journaliser `ROAD100_SEGMENTED` : ancres,
expansions, longueur, raisons, opcodes, résultat de VerifyTrace et coût
quote. Les routines de sélection et génération existantes émettent
`yield` et la revalidation synchrone reprend le même plan.

**Prédictions falsifiables** : ≥1 ligne longue vraiment construite et
transportant des PASS sur un pilote apparié ROAD-only, sans violation
de station/dépôt/route, et marge positive en `profit_year` société.
Projection OFF exacte, contrat V262 inchangé, tests Squirrel/PO01C et
suite Python complète avant smoke. Si aucun projet réellement rentable
construit, NO-EXPOSURE/NO-GO, ne pas passer en 5×5. Sinon comparer cinq
graines 42,100,7,999,2026 sur cinq ans ; Gate A40×5 seulement si H5
ON−OFF ≥4 %, Wilcoxon exact bilatéral p<0,05, IC95 basse >0, garde
valeur ≥−5 % et non-érosion H1..H4. La seule victoire ROAD100 est 5/5
`profit_year` Opex ≥ AAA, jamais le gain ON−OFF isolé.

### Résultat pilote v32 initial et correctif v32b préenregistré

Smoke apparié `road100_v32_segmented_smoke_roadonly_seed42_1x1_20261028`
sur bundle `ab882674885c04374468d999b13a0e95e5a022bb53d3a5e8b394ba9886307f8e` :
2/2 parties saines, flags AAA strict ROUTE seule, Opex ON `profit_year`
19 103 £ contre AAA 97 693 £ ; OFF et ON Opex égaux. Aucun corridor
LONG publié. Au 19 et 20 janvier, le premier gap segmenté est abandonné
à `OPCAP` après respectivement **52 nœuds/47 091 opcodes** et
**69 nœuds/80 742 opcodes**, avec zéro ancre ; les scanners de quais
ont consommé chacun environ 77k opcodes. Le premier gap est dominé
par les déplacements favorisant la voirie au détriment de la distance.

**V32b avant son smoke** : modifier exclusivement l'heuristique de
recherche locale du micro-gap en A* pondéré `5×Manhattan` (contre `1×`
initial), afin de privilégier un progrès direct, tout en gardant la
préférence aux tronçons routiers connectés (coût 1 contre 5) lorsque
cela ne crée pas de grand détour. **Ne pas** changer 80 expansions/gap,
12 ancres, 180k pour le premier couple, 400k annuel, vérifications,
revenus, flotte ni contraintes de cash. Refaire **seulement** le smoke
seed42 1×1 sur un nouveau bundle, puis classer NO-EXPOSURE si zéro
itinéraire admissible ou manque de profit net. Ne pas extrapoler une
différence de `profit_year` sans ligne effectivement posée.

**V32b smoke obtenu** : bundle figé
`70e220e56e0aa8a901081efb58f5c2149ddb27cbaa77819e91f080e772d634c6`,
`road100_v32b_weighted_smoke_roadonly_seed42_1x1_20261028` :
deux duels sains, OFF/ON `profit_year` égaux 19 103 £ H1 contre AAA
97 693 £, 0 LONG. Premier micro-gap 46 nœuds et 47 192 opcodes
avec 0 ancre, second 70 nœuds et 79 837 opcodes, une seule ancre :
encore `OPCAP`, pas de devise de corridor ni construction. **NO-EXPOSURE**,
aucun 5×5 ni A40×5 ; l'heuristique ne résout pas la contrainte physique
ni la borne d'opcodes. Conserver l'option défaut 0 sans adoption.

### ROAD100-33 sparse corridor — protocole avant implémentation

Motif causal : les smokes V32/V32b ont dépensé 47–80k opcodes à
explorer le **premier** micro-gap et jamais atteint un devis, malgré
deux vrais sites PAX positifs. Ne PAS relever la limite générale en
doublant l'A*. La prochaine hypothèse falsifiable consiste à remplacer
la recherche locale dense de 80 expansions par une **petite famille
déterministe de chaînages rectilignes** entre points d'étape (éventuellement
rejoints par des arêtes de voirie existante), avec détours courts autour
des blocages. L'algorithme doit se limiter à des tests géométriques
cardinaux et opérations en temps linéaire sur la longueur du corridor,
éviter le coût `frontier × 80` et un A* global; maximum 12 ancres et
190 arêtes, aucune boucle/tile occupée. Le simple coût linéaire est une
hypothèse à **mesurer** avec `OpexOpsMeasureEnd`, pas un acquis.

Nouveau réglage `road100_sparse_corridor=1`, défaut **0** aux quatre
difficultés, isolé ROUTE seule, dépend de `road100_long_build=1`.
V32 `road100_segmented_corridor` demeure indépendant : un test V33
active seulement SPARSE, n'autorise pas les deux variantes en même temps.
Le projet doit réutiliser les vrais sites A/B, sortie/entrée DT, la
préqualification `OpexRoad100LongVerifyTrace`, dépôt physique et devis
`missing*costRoadPerTile*3`, caisse `capital+25%+50k`, 2 StationIDs,
préflight et hash identique au chantier. Aucun passager ajouté sans
preuve de captation marginale des racines; même conversion V30a
`townMonthly * siteProducers / townProducers` (estimative ex ante).
Pas de revenu satellites/retour/waiting AAA, pas de hausse du nombre
de bus hors capacité **réellement construite**. Conserver le budget
de génération LONG annuel 400k et premier couple 180k, au plus 2 paires
par année. Log `ROAD100_SPARSE` avec étape/erreur/ancres/opcodes,
`VerifyTrace` (missing/existing/error), devis et refus économique.

Avant smoke : tests nouveaux et régression OFF exacte (fixture source
**nouvelle** contre le bundle V31 figé, sans changer V262), suite Python,
`git diff --check`. Smoke 1 graine ×1 an seed42 1v1 strict ROAD-only,
deux politiques et même bundle ; ne lancer 5×5 que si un corridor
*effectivement posé* est rentable dans la partie et livre des PASS.
Si le premier smoke reste à 0 corridor, arrêter ce levier, déclarer
NO-EXPOSURE, sans Gate A. Si 5×5 présente gain H5 moyen >=4 %,
Wilcoxon bilatéral exact p<0,05, IC95 basse positive, valeur >=−5 %,
non-érosion H1..H4, alors et alors seulement envisager Gate A40×5.
La preuve de parité demeure le `profit_year` société aux cinq horizons.

### ROAD100-33 — qualification et verdict (28/10/2026)

Le traceur `ai/OpexAI/road100_sparse_corridor.nut` est intégré sous
`road100_sparse_corridor=1` uniquement : trace `{from,to}` sans aucun
chantier spéculatif, vérification physique et financement par le builder
historique. Bug du budget global corrigé avant smoke : les sites avaient
déjà consommé des opcodes à l'entrée ; plafond local désormais relatif
à l'entrée (100k maximum), avec réserve de 65k pour VerifyTrace, dépôt
et devis. Plafonds 180k/premier couple et 400k/an inchangés.

La projection OFF a été restaurée exactement jusqu'au `HEAD` historique
par trois fixtures séparées : V33 sparse (8 hunks builder), V31b flotte
(4), V32 segmenté (8), puis V31/V30a/site-first/ancien ROAD100. Les
fixtures historiques et `v262_valuate_inventory.json` restent intactes ;
les anciennes versions des deux nouvelles fixtures sont sauvegardées
dans `results/road100_v33_sparse_source_before_20261028/fixture_backups`.
Projection idempotente, tests ESTIM/V262 et V33 8/8 verts, suite complète
**3 217 tests OK** (5 skipped, 2 expected failures), `git diff --check` OK.

Smoke OpenTTD apparié seed42 H1, strict ROUTE seule : campagne
`road100_v33_sparse_smoke_roadonly_seed42_1x1_20261028`, SHA bundle
`98ee573204d350316c9dc2c0d4a6ecc872d313f4df8116138f8aa0d429b58280`.
Deux parties complètes, AAA sans trains/trams/navires/avions ; manifeste :
**seule différence effective** `road100_sparse_corridor=0→1`.
`profit_year` société OFF **22 491 £**, ON **20 797 £**,
AAA **94 472 £** ; ON−OFF **−1 694 £/an**, valeur ON/OFF
**−33,58 %**, Opex ON/AAA H1 **21,99 %**.

Exposition du corridor **nulle** : premier couple 18→2
`ROAD100_SPARSE reason=OPCAP route=-1 ops=37015 total_ops=115408`
(réserve vérification 180k−65k), second 26→10 `NO_CORRIDOR`
(1 342 opcodes) puis `OPCAP` (248 opcodes après fallback historique).
Dans les deux cas **0 trace, 0 devis, 0 admission, 0 construction LONG** ;
les 8 `ROAD_BUILD` ON sont des routes classiques, et aucun passager
n'a été livré par une nouvelle ligne sparse. La dérive négative ON−OFF
n'est **pas** un rendement mesuré d'une ligne LONG inexistante.

L'audit des journaux donne aussi **10 623 959 → 12 146 141**
opcodes observés au total côté Opex (OFF→ON), et
**6 608 978 → 8 395 335** en planification ROAD, instrumentation
partielle. Les deux politiques bâtissent chacune huit lignes classiques
et possèdent chacune 16 véhicules/16 gares fin H1. La huitième ligne
PASS change de marché et de date : OFF 5 août, d26, profit prévu
6 330 £/an ; ON 7 décembre, d50, profit prévu 2 927 £/an.
Cela confirme un déplacement de calendrier/candidats et un coût de
recherche, **pas** un profit attribuable au traceur sparse.

**V33 : NO-EXPOSURE / NO-GO**, pas de 5×5 ni Gate A40×5.
Le besoin reste structurel, mais **attention à la dimension** : les
maxima `max_tested=14..18` de V33 et les `31..35` observés dans
LONG v19b sont des **producteurs couverts**, *pas* des PASS/mois.
Le contre-audit V30a (`road100_calibration_pax_40graines_20261028.md`)
réfute explicitement cette confusion et rapporte un autre marché à
26 producteurs correspondant à **152 PASS/mois estimés** après
conversion de production de ville. Cette conversion n'a pas été
effectuée pour les sites V33, faute de plan complet : il est donc
**impossible de conclure sur leur demande ou leur ROI** à ce stade.
Priorité : mesurer ex ante les vrais PASS/mois des racines LONG
avant de consacrer le budget au tracé, puis prouver plusieurs sites
effectivement jointables, avec devis/construction/flotte et PASS livrés.
**0/5 parités démontrées**, tous réglages expérimentaux restent à 0.
