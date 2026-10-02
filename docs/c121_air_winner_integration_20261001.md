# C121 — intégration isolée de la fusion du gagnant

## Intervention

Suite à « vas y » après le [prototype](c121_air_winner_fusion_20261001.md),
intégration derrière **`c121_air_winner_fusion=0`**, défaut OFF aux quatre
difficultés, chargé seulement si C121 économie ON. C115 reste protégé à1.
Le témoin0 et le candidat1 utilisent le même arbre et les mêmes autres défauts.

`OpexC121AirEconomics` accepte une sortie d'ouverture optionnelle, capturée
à N=1 dans le chemin complet. Les snapshots profit et score sont copiés
séparément et finalisés comme fixedN=1 ; toutes les valeurs/annotations sont
conservées. Le scan continue sans changer son domaine ni ses départages.
Le wrapper conserve la connaissance MAIL exacte sur les deux objets.

Le chooser utilise `OpexC121WinnerEconomics`, double résultat `{initial,full}`.
OFF et AAA_LINE utilisent les deux appels témoins. ON conserve l'ouverture
capturée. Si le scan franchit un mois, la flotte complète est recalculée aux
tarifs courants ; l'ouverture capturée est conservée. Si l'ouverture manque,
l'appel fixedN=1 sert de repli. Aucun cache persistant, aucune donnée Save/Load
nouvelle ; les sorties ont le même contrat que les snapshots du catalogue.

La garde mensuelle est conservatrice : elle agit aussi quand l'inflation est
OFF. Elle assure un recalcul de la flotte après changement d'époque, pas une
identité du calendrier avec la trajectoire de l'IA témoin.

## Contrôles réalisés

- 101 tests Python ciblés réussis (économie, contrats, fixtures, cache,
  catalogue incrémental, sonde et nouveau lecteur).
- Fixture NoAI sur42 ×1 an : 72 cas dirigés caps1/6/13, trois états MAIL,
  quatre modes de score et AAA0/1 ; **633 comparaisons naturelles exactes**,
  cinq routages dirigés réussis : mois stable, nouveau mois (12→13), OFF,
  AAA_LINE et ouverture absente. Objets indépendants, fonctions restaurées.
- Smoke42 ×1 an avec le vrai chooser ON, sans fixture ni sonde : sain,
  receipt fusion1/probe0 attesté, aucune erreur NoAI.

Les frontières tarifaires sont exercées par des doubles explicites de l'époque
et du modèle, restaurés avant les routes réelles. C'est une preuve de routage
du repli, pas une calibration d'inflation réelle. Les comparaisons naturelles
restent à date stable ; facteurs variés et égalités d'argmax dirigées non exhaustifs.

La première fixture a brièvement chevauché une campagne préexistante lancée
par une autre tâche entre le contrôle et notre lancement. Tentative d'arrêt
du seul conteneur fixture identifié ; il avait déjà terminé sainement.
Le chevauchement est conservé et exclut cet essai d'une preuve de cadence.
Les contrôles fonctionnels sont retenus, sans gain annuel déduit de cet essai.
Les lancements suivants vérifient Docker séparément avant chaque partie.

## Protocole de mesure

[Lanceur](../sweeps/run_c121_winner_integration.py), mêmes extracteurs et
`save_load_roundtrip.run_phase_a`, lecteur actuel `parallel_latency_audit`.
Quatre solos distincts42/100 × OFF/ON ×1 an, successifs ; `catalog_cost_probe=1`
identique, autres défauts courants, C121 économie1. Receipts de chargement
du toggle et de la sonde dans les copies. Métriques définies avant lancement :
`c121_winner_ops`, `air_ops`, `total_ops`, plus `c121_calls` et volumes de paires.
Les coûts annuels ne sont pas normalisés comme si les trajectoires étaient
identiques : comparaison annuelle brute et coût gagnant/appel distincts.

Configuration `bench_v2.make_cfg(1970)` 256×256, inflation OFF,
OpenTTD15.3/OpenGFX7.1/OpenTTDLab0.0.75, worker1. Docker `desktop-linux`, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
3 CPU/2 Go/swap interdit, volume `openttd-lab-home`, dépôt monté `/work`.
Bibliothèques locales et dépendances transitives vérifiées par SHA256.
Pas d'adversaire, pas de 5×6/20×10 ni de verdict économique.

Preuves sous `results/c121_winner_integration/` : plans (réglages résolus,
empreintes des sources/copies/bibliothèques), générateur exécuté, rapports,
logs, JSONL et 13 sauvegardes mensuelles par partie du1970-01-01 au1971-01-01.

## Mesures

Les quatre parties figées sont complètes et saines. Le smoke et la fixture sont sous
`20261001_smoke_on42_r1` et `20261001_fixture42_pilot01`.

La première paire42 (`20261001_measure_off42_r1` / `20261001_measure_on42_r1`)
est **non comparable** : un changement concurrent de
`c121_air_first_live_growth_phase_years` fait différer deux réglages au lieu
du seul toggle de fusion. Les sources diffèrent également. Ses deltas ne
constituent pas une preuve de cette optimisation. Le témoin100 initial
(`20261001_measure_off100_r1`) est conservé, sans paire qualifiée.

Correction avant nouvelle comparaison : même copie AI immuable, celle du
premier ON42 (`20261001_measure_on42_r1/ai/OpexAI`), pour les quatre parties,
option explicite `--source-copy`. Empreintes des modules de harnais et de l'AI
réellement chargée séparées des empreintes brutes du workspace (aussi retenues).
Les scripts temporaires/tests d'autres tâches ne sont pas assimilés à des
sources exécutées. Le lecteur impose mêmes sources/configuration/bibliothèques/
image et une seule différence effective de réglage. Aucun artefact initial
écrasé ; aucun verdict économique favorable recherché par ces reprises.

### Résultats figés retenus

Chaque comparaison est auditée : mêmes sources réellement exécutées,
configuration, bibliothèques et image ; une seule différence effective,
`c121_air_winner_fusion` 0→1. Tous les rapports de partie passent, santé OK,
sources/copies/fixtures inchangées, mêmes treize dates de sauvegarde complètes.

| Graine | Poste annuel | OFF opcodes | ON opcodes | Variation |
|---:|---|---:|---:|---:|
| 42 | Gagnant C121 | 16 439 011 | 14 148 443 | −13,93 % |
| 42 | Catalogue AIR | 36 204 826 | 34 056 097 | −5,93 % |
| 42 | Catalogue tous modes | 41 262 483 | 39 325 940 | −4,69 % |
| 100 | Gagnant C121 | 12 537 161 | 10 251 553 | −18,23 % |
| 100 | Catalogue AIR | 28 231 652 | 26 364 162 | −6,61 % |
| 100 | Catalogue tous modes | 34 247 272 | 32 296 805 | −5,70 % |

Appels C121 : 859→863 sur42, 659→640 sur100. Coût gagnant par appel :
19 137→16 394 (−14,33 %) et19 025→16 018 (−15,80 %). Le mix change aussi :
newpair/hubsite/hubhub783/282/30→783/288/30 sur42 et529/306/45→465/327/66
sur100. Ces volumes de paires ne sont pas assimilés aux seuls appels C121.
Le gain annuel brut comprend la variation du travail réalisé ; le coût moyen
par appel reste influencé par le mix de routes. Ne pas transformer ces chiffres
en gain pur à entrées identiques ni en gain économique. La preuve à entrées
identiques demeure celle des fixtures.

Parties retenues : `20261001_frozen_off42_r2`, `20261001_frozen_on42_r2`,
`20261001_frozen_off100_r2`, `20261001_frozen_on100_r2`. Comparaisons exactes
assemblées sous `results/c121_winner_integration/20261001_summary_r2/report.json`.
Le lecteur préserve inconnus/absences ; seuls les `CATALOG_COST` owner0,
session0 et dates1970 sont sommés, sans additionner les slices au coût parent.

### Décision et limites

**Intégré OFF, contrôles techniques et pilote d'opcodes réussis ; aucune
adoption.** Aucune neutralité du profit démontrée, aucun duel de qualification.
La sonde modifie le calendrier ; deux solos instrumentés ne remplacent pas un
diagnostic causal ni le protocole d'adoption. Les chiffres fournis depuis le
VPS n'ont pas le même manifeste/profil et ne sont pas utilisés comme témoin.
La source figée conserve les défauts de sa date de capture ; les modifications
concurrentes ultérieures du workspace sont préservées et ne bénéficient pas
de ces preuves. C115 et l'interdiction20×10 C121 restent inchangés.
