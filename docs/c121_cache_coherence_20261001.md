# C121 — cohérence des caches, lot 1 (01/10/2026)

## Plan avant modification / exécution

Demande : commencer le premier lot de viabilisation C121. Intervention limitée
au contrat des snapshots et aux caches de demande imbriqués. Aucun changement
de modèle, de seuil économique, de cadence, de choix moteur ou de défaut ;
C115 reste à 1, C121 et ses variantes restent OFF. Le découplage catalogue /
économie est un lot ultérieur, pas inclus dans ce correctif.

Constats relus dans `air_catalog_c121.nut` et `air_coverage.nut` :

- un hit catalogue restaure demande et invariants moteur, mais pas les deux
  services ni `b9ShadowMonthly` ; le constructeur peut alors refaire la demande
  en gardant les anciens invariants moteur ;
- un miss sur un plan déjà préparé conserve ses champs dérivés ;
- le cache d'extrémité survit aux tranches sans révision, y compris après une
  invalidation ville/station du catalogue parent.

Contrat visé : snapshot complet sur hit ; suppression des champs dérivés avant
recalcul ; révisions locales de ville/station et invalidation de géométrie /
concurrence propagées au cache enfant. Âge maximal enfant identique au filet
parent de 365 jours. Les changements d'entrées non décrits par les révisions
forcent la relecture des extrémités du plan concerné. Pas de scan supplémentaire
de la carte pour détecter des événements actuellement non observés.

Validation prévue : contrats Python, fixtures des fonctions Squirrel dans une
copie de l'IA (entrées synthétiques déclarées), smoke réel graine42 ×1 an au
défaut puis C121 incrémental seul. Rechargement à une frontière de scan suspendu
si attestée ; absence d'exposition = non validé, pas succès présumé.
Pas de 5×6 ni de 20×10 économique pour ce premier lot de fiabilité.

Environnement vérifié : Git absent, donc pas de diff/SHA historique ; Docker
Desktop `desktop-linux`, image
`sha256:69d7e57aad5d3036f16655e8af23f36aa9fbb7c82c61ea325192c56b50e48e47`,
cache `openttd-lab-home`, aucun conteneur actif avant intervention. Un seul
conteneur, 3 CPU /2 Go sans swap, un worker pour les fixtures et le reload.
Sorties neuves sous `results/c121_cache_coherence/`. Aucun commit/publication.

Les tests de cohérence ne prouvent ni neutralité d'opcodes ni gain économique.
Les snapshots déjà publiés ne sont pas réévalués rétroactivement par ce lot.

## Livraison et résultats

Trois fichiers de production modifiés :

- `air_catalog_c121.nut` : snapshot demande/services A-B/invariants moteur/volume
  B9 restauré intégralement sur hit ; champs dérivés et ancienne télémétrie
  supprimés avant recalcul (y compris hit négatif), nettoyage du flag temporaire
  même sur exception. Les services et la demande du choix ne sont plus rescannés
  à la préparation du build à cause d'un hit incomplet.
- `air_coverage.nut` : métadonnées ville/station/génération de géométrie/date
  sur chaque résultat d'extrémité. La clé physique ne contient pas les révisions :
  un résultat périmé est remplacé, sans accumulation par version. Une modification
  des lignes de station invalide aussi la géométrie et la concurrence des caches
  enfants (une autre gare peut couvrir les mêmes tuiles). Le catalogue parent
  conserve ses invalidations locales existantes. Expiration/changement d'entrée
  forcent une relecture et invalident également la géométrie enfant.
- `settings.nut` : abandon explicite du cache enfant au chargement C121
  incrémental. Aucun défaut modifié, aucun nouvel état sauvegardé.

Nouveaux `sweeps/run_c121_cache_fixtures.py`, `test_c121_cache_coherence.py` et
`tests/mechanisms/c121_cache_vm.nut`. Le lanceur réutilise le driver Save/Load,
les décodeurs physiques, la santé et le contrôle d'intervalle des fixtures
existantes. Les hooks vivent seulement dans une copie de `main.nut`/`persist.nut`.

### Contrôles effectués

- **61/61 tests Python ciblés** : cohérence, catalogue incrémental, économie,
  délai de hub et replay moteur C121. Suite complète non exécutée : demande
  d'exécution annulée, aucun résultat global revendiqué. Diagnostics éditeur OK.
- **Smoke défaut `default_20261001_r2`** : 13 sauvegardes, 1970-01-01 →
  1971-01-01, aucune erreur script, activité et santé complètes. Copie strictement
  identique aux sources OpexAI, sans fixture et sans activation C121.
- **Fixtures `cache_20261001_r2`** : 32 assertions VM réussies (chooser et union
  synthétiques explicitement substitués, puis restaurés). Hits complets,
  nettoyage avant miss, révisions, expiration, entrées modifiées, hit négatif,
  exception, remplacement d'entrée, géométrie, absence de version/date future.
  Ce n'est pas une validation de l'exactitude du modèle physique.
- **Hits réels** : `newpair` avant rechargement ; `newpair` et `hubsite` après.
  Identité du choix et du snapshot conservée, préparation de demande sans second
  modèle. `hubhub` non exposé dans cette fenêtre.
- **Frontière Save/Load réellement exposée** : sauvegarde **1970-02-01**,
  curseur non terminé, huit entrées d'extrémité ; hash
  `e23e867fc19bceaa59a5164b759ff7aaed52a8f9476cdeab93837e2939eb1dd0`.
  Au reload : caches parent/enfant vides, `LOAD_RECONCILE saved=0 kept=0`,
  nouvelles générations puis hits valides. 13 sauvegardes dans chaque phase,
  intervalles mensuels exacts et aucune erreur script. **Reconstruction** du
  travail dérivé, pas sérialisation/reprise du même curseur. Frontière précoce,
  avant lignes persistées : pas validation d'un réseau mature/apprentissages.

Le rapport annuel standard du reload réclame janvier 1970, antérieur au
checkpoint, et conserve `missing_data`. Le contrôle technique valide séparément
l'intervalle réel 1970-02-01 → 1971-02-01 ; aucun verdict économique sain n'est
déduit de cette phase. Sources/harnais et copies inchangés durant les runs et
recontrôlés après. Git absent ; pas de nouvelle référence économique qualifiée.

### Incidents conservés

- `default_20261001_r1` : échec TLS avant moteur. Relance r2 avec le bundle de
  confiance local existant `SSL_CERT_FILE=/work/.ca_bundle.pem`, vérification
  TLS maintenue. Une tentative redondante r2 a été refusée avant exécution par
  la protection contre l'écrasement ; aucun artefact remplacé.
- `cache_20261001_r1` : `getroottable` non exposé par NoAI. Correction limitée
  à la fixture (sauvegarde/restauration explicites), puis r2 sain techniquement.

Preuves locales : `results/c121_cache_coherence/`, plans, rapports, logs, copies
et sauvegardes hachées. Référence de fichiers antérieurs sous `before_20261001/`.
Le contrôle final confirme seulement trois sources de production modifiées,
`info.nut` inchangé et aucun conteneur actif. Aucun 5×6, 20×10, commit/push.

## Limites et suite

Premier correctif de cohérence livré et exercé, **non qualifié économiquement**.
Pas de garantie de fraîcheur absolue du monde entre ticks : événements non
détectés, invalidations du catalogue parent, observations sous seuil et snapshots
déjà publiés conservent leurs limites antérieures. Ni coût net des invalidations
enfants ni débit économique mesurés. La prochaine intervention reste isolée :
mesurer les blocages post-chantier et le délai vers un investissement utile,
sans empiler les variantes C121/C122 ni toucher à C115.