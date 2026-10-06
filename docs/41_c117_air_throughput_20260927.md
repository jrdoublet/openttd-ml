# C117 — débit AIR réel par ligne — 2026-09-27

Révision documentaire statique : **2026-09-30**, sans test ni partie.

## Objet et provenance

C117 observe la chaîne demande projet → trafic → capacité/fréquence → revenu/profit.
La sonde C117 ne modifie ni classement, ni admission, ni moteur, ni flotte,
ni construction, ni ordres. Une sonde passive peut néanmoins perturber les
trajectoires par son coût en opcodes ; ce diagnostic ne qualifie pas un traitement.
C115 reste le témoin ; C116 n'est pas activé par ce diagnostic.

L'[original corrompu](archives/c117_original_corrompu_non_exploitable_2026-09-30.md)
est conservé comme archive **non autoritaire, non source exploitable**. Aucun
tableau chiffré ni signe n'a été reconstruit depuis la partie illisible.

Sources de méthode lues dans l'arbre local :

- `ai/OpexAI/probes.nut` : `OpexC117AirThroughputStep`,
  `OpexC117NewLineState`, `OpexC117FlushLine` ; le fichier demandé sous le nom
  `air_throughput_probe.nut` est **absent de cet arbre**, la sonde se trouve ici ;
- `sweeps/diag_c117_air_throughput.py` : déduplication et unités des événements ;
- `sweeps/analyse_c117_aggregate.py` : agrégation anti-aliasing.

Cette lecture décrit le code actuel, enrichi ensuite pour C119/C121 ; elle ne
certifie pas l'identité du bundle C117 initial. Les résultats locaux C117 et
leur index de preuves sont absents : les références suivantes restent des
**références historiques rapportées, non revalidées** :

- campagne : `results/c117_air_throughput_5x6_20260927_r2.json` ;
- agrégation : `results/c117_air_throughput_5x6_20260927_r2_aggregate.json` ;
- smoke : `results/smoke_c117_air_throughput_1x2_20260927_r2.json`.

L'ancien compte rendu rapporte **5/5 runs sains, 483 lignes AIR et 14 175
fenêtres brutes**, sur 42/100/999/1234/5678 × 6 ans. Ces effectifs ne sont pas
recalculés ici. Il signale aussi que la première sortie sans suffixe `_r2`
(`c117_air_throughput_5x6_20260927.json`) était inutilisable après filtrage
calendaire du runner ; elle ne doit pas remplacer la référence r2.

## Mesure : legs observés, pas compteur de livraisons NoAI

Une ligne AIR Opex a deux ordres A↔B ; les clones partagent ces ordres.
L'échantillonnage annoncé est tous les deux jours de jeu. Le code exclut les
ordres hors liste (notamment les ordres manuels de hangar) de la résolution
des positions A/B et suit les échantillons invalides séparément.

Pour chaque avion, tant que son état est `AIVehicle.VS_RUNNING`, la sonde
mémorise le **maximum de charge passagers** du leg et sa capacité. Au changement
d'index d'ordre A→B ou B→A, elle clôt le leg précédent :

- s'il a été observé en mouvement (`legMoving`), elle cumule sa charge maximale
  dans `pax`, sa capacité dans `seat_legs`, et incrémente `trips` ;
- sinon elle incrémente `unobserved_transitions`, sans inventer de charge ;
- le chargement au quai n'est pas pris comme une livraison supplémentaire.

Il s'agit donc d'un **débit reconstruit sur les legs observés**, pas d'un
compteur exhaustif de passagers livrés fourni par NoAI. Des transitions peuvent
être manquées entre deux échantillons ; leur taux ne peut pas être recalculé
sans les événements bruts.

## Définitions et unités

Sur une durée `days > 0`, soit `observed_pax = sum(pax)` et
`seats = sum(seat_legs)` sur les mêmes legs terminés (ce n'est pas la capacité
instantanée de la flotte). La convention explicite **sur 30 jours** donne :

- `carried = 30 * observed_pax / days` : passagers transportés observés / 30 j ;
- `offered = 30 * seats / days` : sièges offerts sur ces legs / 30 j ;
- `load_factor = observed_pax / seats`, si `seats > 0` ;
- `trips = legs` observés terminés, **pas des allers-retours** ;
- `headway = 2 * days / legs`, si `legs > 0`, intervalle moyen par sens
  reconstruit à partir des deux directions.

**Attention à la convention du code courant :** `OpexC117FlushLine` et
`analyse_c117_aggregate.py` utilisent **30,4**, et non 30, dans `pax_pm` et
`seats_pm`. Les formules sur 30 jours ci-dessus définissent une unité distincte ;
elles ne doivent pas être présentées comme la sortie exacte de ces champs.
Les comparaisons avec le modèle doivent garder la même base temporelle.
Le load factor et le headway ne dépendent pas de cette conversion mensuelle.
Un dénominateur nul signifie mesure indisponible, pas zéro trafic prouvé.

Le profit est la variation des profits véhicule, avec raccord de l'année
précédente lors du changement d'année. Le revenu est **estimé** en y ajoutant
les coûts de fonctionnement véhicule proratisés ; il inclut PASS et MAIL.
Le profit véhicule n'inclut pas le même périmètre que le profit net du modèle
(infrastructure/amortissement). L'attente et le rating sont ceux des stations :
dans un hub partagé, ils ne sont pas propres à une seule ligne.

## Agrégation anti-aliasing

Les fenêtres suivent des tranches d'âge de 30 jours depuis le build, pas les
mois calendaires. Une fenêtre peut ne contenir aucun leg terminé malgré une
ligne active : ne pas moyenner naïvement ses ratios.

Le diagnostic conserve un événement final par `(seed, line, age_bucket)`
car les checkpoints sont cumulatifs. L'analyseur agrégé :

1. retient les fenêtres avec **`period_days >= 20`** ;
2. groupe par `(seed, line, age_band)` ou par `(seed, line)` pour la vie entière ;
3. définit le sous-ensemble **mature par `age_bucket >= 6`** (buckets indexés
   à zéro, donc à partir du septième mois d'âge conventionnel) ;
4. **somme jours, passagers, sièges-legs et legs avant de calculer les ratios** ;
5. pondère les moyennes station/flotte par la durée et distingue les
   distributions par ligne des ratios réseau pondérés par exposition.

Un ratio réseau, une médiane par ligne et une moyenne de fenêtres ne décrivent
pas le même objet. Aucun de leurs résultats numériques n'est recréé ici.

## C117 initial et rerun pour C119 : deux diagnostics distincts

Les 483 lignes / 14 175 fenêtres rapportées ci-dessus appartiennent au
**C117 initial r2**. Le **rerun enrichi pour C119** ajoute notamment la distance
Manhattan de paiement et les informations d'aéroport ; ses effectifs matures et
ratios de revenu relèvent de la [fiche C119](42_c119_air_income_model_20260928.md),
pas d'un remplacement des résultats initiaux C117.

La méthode permet de séparer débit observé, capacité offerte et revenu unitaire.
Elle ne suffit pas à déduire une correction active de `monthlyPax`, des moteurs,
de la flotte ou des ordres. **Aucun nouveau test, tableau de résultats, verdict
économique ou changement de défaut n'est produit par cette remise en état.**