# F-EVENT-BACKLOG-01 — diagnostic d'exposition

## Pré-enregistrement du 8 octobre 2026

Demande : vérifier l'exposition de la sonde existante, sans développer une
nouvelle sonde ni ajouter arbitrairement un quota d'événements.

- Base `master`, HEAD `45df803` ; code de production inchangé. Travaux locaux
  concurrents dans le harnais fret et ses analyseurs conservés. Le lanceur
  fige l'arbre réellement exécuté, y compris ce harnais local.
- Sonde `events.nut::_processEvents`, `probe_event_backlog=0` livré aux quatre
  difficultés, chargement et compteurs vérifiés. ON conserve le dispatch mais
  ajoute un coût de mesure qui peut décaler l'exécution.
- Contrats existants exécutés : sonde 7/7, ordonnanceur 3/3 verts.
- Campagne neuve `event_backlog_exposure_3x3_20261008`, référence seule
  `OpexAI[probe_event_backlog=1]` contre AAAHogEx figée, graines 42/100/999,
  trois ans, une répétition : trois parties, neuf années de jeu. Aucun A/B.
- `--script-debug` pour capturer AILog.Info ; autres réglages aux défauts,
  notamment `decision_log=0`. Aucune conclusion économique sur la sonde ON.
- Contexte Docker local `desktop-linux`, daemon libre ; image
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
  cache `openttd-lab-home`, montage du dépôt, 10 CPU /8 Go /swap8 Go,
  max-workers10. Aucun banc long ni rejeu favorable.

Mesurer les fenêtres mensuelles `EVENT_BACKLOG` : calls/events/max_burst,
ops_total/ops_max, couverture et santé. `max_burst` est le nombre d'événements
non nuls traités dans un appel, pas une longueur instantanée de file.
Le coût inclut les handlers et la mesure de sonde ; un maximum d'opcodes peut
correspondre à un autre appel que le maximum de rafale dans le même mois.

Signal pré-enregistré à instruire : un `ops_max >= 10000` (budget d'un tick
dans `budget.nut`) ou un incident technique/de couverture. Ce seuil ne prouve
ni retard ni famine et ne constitue pas un quota. Sans ce signal et avec une
couverture saine, clôture du chantier sur ce périmètre court, réouverture
seulement sur exposition nouvelle. Une file vide n'est pas une preuve de
latence nulle ; le dernier intervalle non vidé doit rester une limite.

La règle du harnais est explicitée (`gain_short`) mais ce petit diagnostic à un seul bras ne
constitue aucune porte d'adoption. Aucun défaut changé, commit ou push implicite.
Premier appel refusé avant gel/partie : un seuil relatif fourni sans variante
est refusé par le CLI. Seuil retiré pour ce diagnostic à référence seule ;
graines/horizon/budget et critère d'exposition inchangés.

## Résultat et décision

Campagne complète : **3/3 parties saines**, deux compagnies actives par partie,
36 checkpoints jusqu'au 1/12/1972, aucune erreur NoAI ni erreur non attribuée.
Contrats réexécutés : **7/7 + 3/3 verts**. Aucun code de production modifié.

| Graine | Fenêtres émises | Appels | Événements | Rafale maximale | `ops_max` maximal | Fenêtres ≥ 10 000 |
|---|---:|---:|---:|---:|---:|---:|
| 42 | 35 | 2 696 | 56 | 5 | 97 609 | 4 |
| 100 | 35 | 3 134 | 56 | 5 | 128 811 | 5 |
| 999 | 35 | 2 076 | 73 | 5 | 728 067 | 7 |

Total : **105 fenêtres, 7 906 appels, 185 événements**, 16 fenêtres franchissant
le signal pré-enregistré. Les logs vont du flush du 1/2/1970 à celui du
1/12/1972. La date désigne le jour du flush de l'accumulation précédente,
parfois retardé ; décembre 1972 n'est pas flushé à la fin du diagnostic.
Les comptes ne mesurent ni attente dans la file ni backlog instantané.

Le maximum apparaît dans `reference_seed999_r0.log`, ligne 5869 :
`date=1972-03-04 calls=10 events=1 max_burst=1 ops_total=728202 ops_max=728067`.
Cette fenêtre ne contient qu'un événement ; une rafale nombreuse n'explique
donc pas ce maximum. **Aucun quota ajouté.**

`budget.nut::OpexOpsMeasureEnd` reconstruit un compteur avec les ticks écoulés
et `OPS_PER_TICK=10000`. Il inclut les ticks d'attente de commandes, comme le
documente aussi `probes.nut` : ce n'est pas une mesure exacte de CPU consommé,
ni une preuve de famine. Les handlers peuvent envoyer un véhicule au dépôt
ou poser un panneau. `_c77RemoveSubsidy` peut également refaire synchronement
la sélection des projets. Ces chemins sont des hypothèses à départager ;
les logs présents ne donnent pas le type de l'événement du maximum.

**Développement de la sonde terminé ; mesure initiale réalisée ; chantier
global conservé ouvert pour attribution du signal.** Prochaine intervention
isolée : exploiter les spans existants `probe_span_trace` et leurs noms
`event.*`, ticks et compteurs pour attribuer les appels longs, puis distinguer
calcul et attente de commande avant toute correction. Une trace plus lourde
peut perturber la trajectoire ; aucun gain économique ni équivalence ON/OFF
n'est déduit de ce diagnostic. `probe_event_backlog` reste à **0** par défaut.

## Provenance

Commande exécutée depuis la racine (profil PC local) :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign event_backlog_exposure_3x3_20261008 --reference "OpexAI[probe_event_backlog=1]" --decision-rule gain_short --years 3 --seeds 42 100 999 --repeats 1 --script-debug --cpus 10 --memory 8g --max-workers 10
```

- Rapport : `results/event_backlog_exposure_3x3_20261008.json`.
- Manifeste SHA-256 : `e4a5689bc736f47cb16b5963a34d51dcd8d045dd7d0b68b72b5b7b1672e52241`.
- Bundle SHA-256 : `d159a45b9a5d3a89d73c19111f5787c44ddb7ed40fd894f45fb15dc1067f72f8`.
- [Preuve compacte](../evidence/review/event_backlog_20261008/README.md) :
  rapport, manifeste, trois logs et extraction détaillée, hashes vérifiés.
