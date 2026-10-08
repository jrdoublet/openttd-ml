# Plans GitHub V102 — schéma 2

Le workflow `qualify.yml` exécute les contrats pré-enregistrés, puis **smoke
1×1 → gain_short 40×3 → non_erosion 20×10** pour un plan comportemental.
Maximum : **122 parties**, une répétition, arrêt à la première porte échouée,
preuve absente ou budget dépassé. Aucun défaut, commit, push ou merge automatique.
La migration du 07/10 est validée localement ; le premier run Actions du nouveau
parcours reste à confirmer après publication autorisée.

Les plans de schéma 1 et leurs verdicts restent historiques. Ils sont refusés
par le parcours courant : remplacer le numéro seul ne requalifie aucune mesure.

## Pré-enregistrement

Créer `qualifications/<chantier>.json`, publié sur la branche testée.
Ce modèle contient des placeholders et n'autorise aucune campagne :

```json
{
  "schema_version": 2,
  "category": "behavior",
  "reference": "OpexAI[reglage_reel=0]",
  "variant": "OpexAI[reglage_reel=1]",
  "exposure": {
    "field": "compteur_reel_du_resume",
    "minimum": 1,
    "meaning": "Lien entre ce compteur et le mécanisme modifié"
  },
  "opcode_component": null,
  "contract_tests": ["test_contrat_reel_du_chantier"],
  "budget_minutes": 270,
  "rationale": "Intervention isolée, autorisation, protocole et journal du chantier"
}
```

Les bras explicitent les mêmes clés d'intervention, avec des valeurs différentes.
La référence conserve les défauts publiés ; déclaration, bornes et pas sont
vérifiés. Les autres réglages restent aux défauts, C115 protégé compris.
Le plan, SHA, dépôt, ref, run/attempt, graines et commandes sont figés avant jeu.
Le schéma 2 fixe A à trois ans, seuil relatif 4 %, garde de valeur 5 % : aucune
variation d'horizon ou de seuil n'est proposée par ce parcours automatique.

`exposure.field` désigne un compteur numérique fini réellement collecté dans
chaque résumé OpexAI candidat et son checkpoint terminal. Il doit atteindre
`minimum > 0` au smoke puis sur toutes les graines des portes. Une métrique
économique, un booléen ou une activité générique ne démontre pas l'exposition
à une branche particulière. Justifier le lien dans `meaning`. Sans extracteur
courant pertinent, la séquence reste NON_VALIDÉE ; instrumenter séparément avant
mesure et vérifier la perturbation. Télémétrie par ligne OFF.

`contract_tests` est une liste non vide de modules `test_*` existants, pertinents
pour le chantier. `budget_minutes` est un entier de 1 à 270 : budget mural total
des étapes moteur, pas par étape. Image et contrats ont des délais séparés ;
job plafonné à six heures. Un dépassement donne NON_VALIDÉ, sans réduire les graines.

## Portes comportementales

| Étape | Critères |
|---|---|
| Smoke | Deux duels sains, horizon complet, provenance et exposition ; trois trimestres clos possibles la première année ; hors échantillon d'adoption |
| A `gain_short` | 40/40 paires à trois ans, Wilcoxon exact bilatéral p<0,05, borne basse IC95 bootstrap >0, gain moyen ≥4 % du profit terminal moyen de référence ; garde valeur −5 % |
| B `non_erosion` | Après passage de A : 20/20 paires à dix ans, borne haute IC95 bootstrap ≥0 ; garde valeur −5 % ; aucun gain positif minimal ni quota de victoires |

Profit primaire : `profit_year` Opex variante − Opex référence terminal,
quatre trimestres valides. Bootstrap percentile : 20 000 tirages, graine 0.
Le validateur recalcule moyenne, Wilcoxon et IC95 depuis les compagnies finales,
avec les mêmes fonctions statistiques que le harnais figé ; il vérifie aussi
les agrégats, paramètres et verdict brut. Chaque porte exige santé, horizon,
comparaison, admissibilité et couverture complets. Garde : ratio des moyennes
`company_value`, tous les dénominateurs de référence strictement positifs.
Un IC traversant zéro en B ne démontre ni gain ni équivalence.

## Optimisations d'opcodes : parcours distinct

`category=opcodes` fixe **smoke → non_erosion 20×10**, sans porte A économique.
`opcode_component` doit être l'un des composants H5 observés : `selection`,
`rail_attempt`, `road_planning`, `road_build`, `air_planning`, `water_planning`.
Avant le 20×10, le smoke doit déjà montrer un gain moyen d'opcodes par échantillon.
Les deux bras doivent avoir des échantillons positifs en nombre égal, une même
couverture non vide, des opcodes finis non négatifs, schéma `h5.observed-v1`.
La pertinence et la comparabilité du travail sont à contrôler dans le plan :
même nombre d'échantillons ne prouve pas une même difficulté.

Au 20×10, gain opcodes positif et critères dédiés conservés : IC95 Student du
delta de profit non entièrement négatif, pas de défaite significative au test
des signes (p≥0,05 ou majorité de victoires), garde valeur −5 %. Le verdict
brut `non_erosion` est contrôlé et conservé séparément ; son passage seul ne
qualifie pas la neutralité opcodes. Aucun reclassement après résultats.

## Preuves et décision

`results/qualification-<run>-<attempt>/` contient requête, reçu de contrats,
identités runner/image/adversaire, sous-dossiers `smoke/`, `gain_short/`,
`non_erosion/` seulement s'ils ont été tentés, JSON/JSONL, logs, manifeste,
bundle, ratios descriptifs, décisions et résumé. Les preuves sont vérifiées
après chaque étape ; sources, adversaire, réglages, bibliothèques, configuration
et image doivent rester identiques. Seuls campagne, graines, horizon et règle
de porte changent. Empreintes = cohérence, pas signature contre un auteur malveillant.

POURSUIVRE est intermédiaire ; la décision globale reste NON_VALIDÉ jusqu'à
la dernière porte. ACCEPTÉ signifie « qualifié selon le plan », sans adoption
automatique. REFUSÉ (code 2) conserve un échec économique ; NON_VALIDÉ (code 1)
conserve erreur technique, absence de preuve ou interruption. Aucun rejeu favorable.

Les artefacts Actions expirent après 30 jours : conserver les preuves durables
selon AGENTS §6 avec le run exact. La concurrence est partagée avec `bench.yml`
par branche, sans déduplication entre branches. Vérifier autorisation, restrictions
de `docs/taches.md`, quota et absence de doublon avant dispatch. Les changements
locaux non publiés ne sont pas exécutés par Actions.
