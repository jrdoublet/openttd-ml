# DIST-BORNES-1 — inventaire statique des bornes appliquées

25 octobre 2026. **Lecture seule du comportement**, master `2be46925` ; aucune
réparation de frontière n'est qualifiée par ce document. Une différence de
distance peut modifier la constitution du catalogue et exige alors exposition
et protocole V102 multimodal avant activation.

## Producteurs et filtres actifs

| Site | Distance/borne | Précision |
|---|---|---|
| `candidates.nut:265-313,349-426` | `roadMin`, `roadMax` : rayon de couverture bus et seuil de ROI comparé rail ; `roadGenMax` : horizon du bus, plafonné par `railMax` | `roadMax` n'est pas le plafond du générateur ROUTE |
| `candidates.nut:367-374` | `railMax` issu des itérations A*, remplacé si présents par V168 puis V294 | Le **dernier** V294 l'emporte ; la limite brute d'itérations n'est pas nécessairement appliquée |
| `candidates.nut:392-426` | `railAirOverlapMin`, `airMin`, `airMax` : seuil rail/avion par temps de vol et horizon avion | `airMax` est aussi borné par la portée moteur et la carte |
| `candidates.nut:457-469` | `roadMin…roadGenMax` | Filtre de distance ROUTE, **Manhattan** entre extrémités |
| `candidates.nut:472-494` | AIR : bande via **Manhattan des villes**, maximum par distance de vol ; RAIL voyageurs : `railMin…railMax` | Ne pas assimiler `AIR_BUILD.dist` à Manhattan des villes |
| `candidates.nut:628-642` | RAIL fret : distance **Manhattan** jusqu'à `V269_RAIL_MAX_DIST` si `V269_RELAXED` et cette borne dépasse `railMax` | Exception fret tardive, non applicable au rail voyageurs |
| `candidates.nut:2061-2064` | Subventions C42 ROUTE : `roadMin…roadGenMax` | La subvention suit la fenêtre du générateur, pas `roadMax` |
| `candidates_v276.nut:126-148` | Grille spatiale V276 : max `roadGenMax` en ROUTE ; `railMax` en RAIL | Préfiltre placé **avant** la vérification finale de la paire |
| `candidates_v276.nut:78-86,259-280` | V276 donne au fret `PAX_BAND_ALL`, puis applique **aussi** `OpexRailPaxPairInBand` à tout mode `rail` après la grille | Second plafond `railMax` indépendant de la grille : élargir uniquement la grille ne suffirait pas pour le fret V269 tardif |

## Données économiques déjà publiées et limites

L'[étude du 21/10](etude_roi_bornes_distance_neutralite_20261021.md)
observe 2 109 `EPOCH_BOUNDS` sur 256² : `roadMin=roadMax=railMin=7`,
`roadGenMax=200`, `railAirOverlapMin=railMax=airMin=200`, `airMax=512`.
Une seule bande AIR/RAIL voyageurs de largeur nulle (Manhattan=200) est donc
présente ; la ROUTE explore néanmoins au-delà de 7. Sur les duels historiques,
ajouter les sous-bandes au modèle ne réduit pratiquement pas la MAE du ROI AIR
(13,891 → 13,889 points) ou RAIL (12,614 → 12,687) : cela ne motive **aucun
changement de score ou de frontière**.

**Deux écrans conditionnels identifiés, non corrigés :** sur 1024², V276 est activé
automatiquement ; `OpexV276PrepareUnit` indexe la grille fret RAIL jusqu'à
`catalog.bounds.railMax` (200 dans les traces 256²). Lorsqu'en aval
`V269_RELAXED` permet `V269_RAIL_MAX_DIST` supérieur (250), la génération
directe `OpexRailCandidate` tolérerait 201–250, mais les paires hors de la
grille ne sont pas soumises à ce filtre : elles risquent d'être invisibles.
**Même si la grille s'étendait à 250,** `OpexV276Enumerate` applique ensuite
`OpexRailPaxPairInBand(..., PAX_BAND_ALL)` à toutes les paires `rail`,
y compris fret, et cette garde retient seulement `railMin…railMax`.
Les **deux** plafonds doivent donc être distingués dans une éventuelle
correction opt-in. Deux contrats hôte ajoutés le 25/10 valident ce parcours
source et le cas synthétique 201/249/250 : ils ne sont pas une exposition moteur.
Le seuil 200 sur 1024² **doit être relevé dans un log `EPOCH_BOUNDS` du même
monde**, et l'exposition de V269 tardif vérifiée, avant de conclure à un effet
réel ou de coder un élargissement. Un déblocage ferait apparaître de nouvelles
paires, avec consommation d'opcodes et trafic différent ; pas une correction
neutre démontrée.

## Suite pré-enregistrable

1. Sur les traces existantes, rapprocher par date `EPOCH_BOUNDS`,
   `V269_RELAXED`, fenêtres du slicer V276 et refus de distance ; séparer
   256²/1024², PAX/fret, ROUTE/RAIL/AIR et C42.
2. Pour un correctif : opt-in à défaut **0**, univers du filtre unique,
   invariants entre générateur et slicer, tests d'identité **OFF** et de
   classement **ON**, conservation de Save/Load et du budget d'opcodes.
3. Smoke 1×1 puis exposition de paires 201–250 réellement examinées ;
   porte A V102 multimodale 40×3 et B 20×10 seulement si A passe.

Tâche conservée ouverte : ni les nouveaux profits captables, ni le coût des
nouveaux trajets ne sont connus avant leur étude appariée.
