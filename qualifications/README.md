# Plans GitHub de schéma 1 — protocole historique

**Mise à jour du 03/10/2026 : ce workflow n'implémente pas V102.** La consigne
courante est [AGENTS.md §4/§4.1](../AGENTS.md#4-validation-proportionnée-puis-adoption) :
smoke, porte A `gain_short` 40×3, puis porte B `non_erosion` 20×10 ; le filtre
5×6 n'est plus obligatoire. Utiliser le lanceur hôte et les options de ce guide
commun tant que les workflows ne sont pas migrés. La règle opcodes reste distincte.

Ce document décrit les capacités **actuelles de `qualify.yml`**, conservées pour
les protocoles historiques : `signs20`, seuil absolu 50 k£ et séquence 1×1→5×6→20×10.
Ajouter des champs V102 à un plan de schéma 1 ne rend pas le workflow compatible.
Un statut `ACCEPTÉ` de ce workflow n'atteste pas le passage des deux portes V102.

Le workflow **Qualification de défaut OpenTTD** (`.github/workflows/qualify.yml`)
reçoit un seul input : `plan`, chemin d'un JSON **publié sur la branche testée**,
dans ce dossier. Il exécute les contrats choisis, puis automatiquement le smoke
apparié 1×1, le diagnostic 5×6 et, uniquement après passage des portes, le 20×10.
Maximum : **52 parties** ; aucune relance automatique, modification de défaut ou fusion.

## Préparer un plan historique de schéma 1

Créer un fichier `<chantier>.json` avec les champs suivants. Les noms de réglage,
compteur et contrat ci-dessous sont **des placeholders, pas un essai autorisé**.
Ne pas publier ce modèle tel quel comme plan exploitable.

```json
{
  "schema_version": 1,
  "category": "behavior",
  "reference": "OpexAI[reglage_reel=0]",
  "variant": "OpexAI[reglage_reel=1]",
  "exposure": {
    "field": "compteur_reel_du_resume",
    "minimum": 1,
    "meaning": "Pourquoi ce compteur démontre l'exécution du mécanisme modifié"
  },
  "opcode_component": null,
  "contract_tests": ["test_contrat_reel_du_chantier"],
  "budget_minutes": 270,
  "rationale": "Intervention isolée, chemin témoin, autorisation et référence au journal"
}
```

- Le plan est copié dans `request.json`, avec son SHA-256, SHA Git du run, dépôt,
  ref, ID/tentative et les trois protocoles. Aucun seuil modifiable après mesure.
- Les deux bras explicitent les **mêmes clés d'intervention**, toutes différentes.
  La référence doit représenter les défauts encore présents dans `info.nut` ; pas
  de réglages optimisés communs hors défaut. Déclaration, bornes et pas sont vérifiés.
  L'agent vérifie aussi chargement, usages et, si applicable, persistance.
- `category` vaut `behavior` ou `opcodes`, fixé avant les résultats.
- `exposure.field` est un chemin dans chaque ligne OpexAI candidate de `summary`
  (notation pointée pour un objet imbriqué). Il doit être **réellement collecté**,
  numérique, fini, et atteindre `minimum > 0` sur **toutes** les graines du
  diagnostic puis de l'adoption. Exemple de chemin disponible dans le schéma H5 :
  `observed_opcode_components.selection.samples`, seulement si l'intervention
  concerne réellement cette opération. Une activité générique ne suffit pas à
  exposer une branche particulière ; justifier le choix dans `meaning`.
- Pas de compteur inventé, de booléen « exposé », ni de fichier de preuve ajouté
  après lecture du résultat. Si aucun extracteur courant ne publie le compteur
  nécessaire, instrumenter et tester ce contrat dans un chantier séparé, **avant**
  qualification. Compteur absent/ambigu → `NON_VALIDÉ`.
- `contract_tests` contient des noms de modules `test_...` présents dans `sweeps`.
  Ils sont exécutés sans shell dynamique, dans la même image que les parties.
  Choisir les contrats du changement ; les tests d'orchestration ne les remplacent
  pas. Une déclaration de module ne garantit pas sa pertinence métier : revue préalable.
- `budget_minutes` : entier **1 à 270**, budget mural total des trois étapes moteur,
  pas par étape. Compilation de l'image et contrats ont des délais séparés
  (30 et 10 minutes). Le job est plafonné à six heures, avec marge pour les artefacts.
  Un 20×10 peut dépasser le budget : arrêt `NON_VALIDÉ`, jamais réduction des graines.
  Ce plafond n'est ni une estimation de coût ni une garantie de finir sur runner partagé.

## Portes déterministes historiques (hors V102)

| Étape | Passage |
|---|---|
| Smoke | Deux parties saines, horizon complet et provenance vérifiée ; pas d'inférence économique ni exigence de quatre trimestres à la première année |
| Diagnostic comportement | Toutes les paires saines, quatre trimestres valides, exposition, delta moyen Opex variante−référence ≥50 000 £/an, garde de valeur −5 % |
| Adoption comportement | Même validité, 20 graines canoniques ×10 ans ×1 répétition, ≥15 victoires, test exact bilatéral p<0,05, delta moyen ≥50 000, garde −5 %, verdict brut `pass` |

Le garde-fou est le **ratio des moyennes** de valeur, avec tous les dénominateurs
de référence strictement positifs. Pas une moyenne de ratios ni le seul écart à AAAHogEx.
Le validateur recalcule les statistiques à partir des compagnies finales.

### Cas opcodes

Pour `category=opcodes`, renseigner `opcode_component` : `selection`, `rail_attempt`,
`road_planning`, `road_build`, `air_planning` ou `water_planning` (schéma existant
`h5.observed-v1`). La mesure concerne **ce poste observé**, pas tout le CPU.

Pour chaque graine et les deux politiques : couverture textuelle identique,
échantillons strictement positifs et **même nombre d'échantillons**, opcodes finis
non négatifs. Le gain moyen apparié d'opcodes **par échantillon** doit être positif.
Cette restriction volontaire peut bloquer un essai valide scientifiquement mais
non comparable automatiquement : ne pas la contourner en supprimant des graines.
La nature du travail/du poste et les biais de publication des sondes (notamment
succès seulement pour `water_planning`) nécessitent une revue du plan et des traces.
Même nombre d'échantillons ne prouve pas à lui seul la même difficulté du travail.

Au diagnostic comme au 20×10, exiger aussi IC95 Student du delta de profit non
entièrement négatif, absence de défaite significative au test des signes
(p≥0,05 ou plus de victoires que de défaites) et garde de valeur tenue.
Tous les ex æquo donnent p=1 dans ce contrôle dédié (le harnais peut publier null).
Ni +50 k£ ni 15 victoires ne sont exigés pour cette catégorie. Le verdict brut,
souvent `fail_primary`, est conservé séparément ; pas de reclassement après coup.

## Décision et preuves

Sous `results/qualification-<run>-<attempt>/` :

- `request.json`, `contracts.json`/`contracts.log`, identité runner/image/adversaire ;
- `smoke/`, `diagnostic/`, `adoption/` uniquement lorsqu'une étape est tentée ;
- par étape : plan, rapport, checkpoints, logs, manifeste, bundle, ratios de profits,
  résumé et `decision.json` ;
- à la racine : `decision.json` consolidé et `summary.md`.

`POURSUIVRE` désigne uniquement une porte intermédiaire. La décision globale reste
`NON_VALIDÉ` jusqu'à la fin. Le verdict final est **ACCEPTÉ**, **REFUSÉ** ou
**NON_VALIDÉ**, avec motifs, statistiques, verdict brut et empreintes des preuves.
`REFUSÉ` arrête aussi le job (code 2) ; incident technique/incomplétude : code 1.
Lire la décision, pas simplement la couleur Actions. `ACCEPTÉ` signifie « candidat
qualifié selon le plan », **pas « défaut déjà adopté »**.

Sources, bibliothèques, politiques effectives, configuration, versions et image
sont comparées entre les trois étapes. Le manifeste et le bundle sont vérifiés
après chaque exécution ; les chemins `/work` des manifestes restent inchangés lors
d'un téléchargement des artefacts. Les empreintes établissent la cohérence,
pas une signature contre un auteur malveillant capable de réécrire toutes les preuves.

Les artefacts Actions sont conservés **30 jours**. Après décision, archiver les
preuves durables selon `AGENTS.md` §6 avec lien du run exact. Une interruption dure
du runner peut empêcher le résumé/l'upload malgré `always()` : absence d'artefact
final = non validé, pas acceptation par défaut.

La concurrence est partagée avec `bench.yml` par branche. Elle ne déduplique pas
les dispatchs successifs ni plusieurs branches du même chantier ; l'agent doit
vérifier les runs existants et l'autorisation/budget avant le déclenchement.
Les restrictions de `docs/taches.md` restent applicables et ne sont pas interprétées
automatiquement à partir de prose. Les différences entre deux commits ne sont pas
prises en charge. Aucun plan concret ni banc métier n'est autorisé par ce modèle.
