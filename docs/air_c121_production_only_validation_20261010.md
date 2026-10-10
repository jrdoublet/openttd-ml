# AIR C121 — validation Docker du replay de production (10 octobre 2026)

## Périmètre et provenance

Prototype `c121_production_only_replay_shadow`, **OFF par défaut**. Dans les
deux bras, `c121_exact_prod_invalidation=1`; seule l'observation par replay
à moteur et nombre d'avions fixes diffère. L'exact-invalidation est une
politique de comparaison expérimentale, **pas** une recommandation d'adoption
(portes historiques A40×3 et A40×5 échouées).

- Smoke : `air_c121_prod_only_smoke_seed42_3y_20261010_r1`, graine 42,
  3 ans, deux parties complètes, 3 CPU / 2 workers.
- Diagnostic : `air_c121_prod_only_exposure_8x5_20261010_r1`, graines
  42, 100, 7, 999, 2026, 4096, 65537, 1337, 5 ans, 16/16 parties complètes,
  10 CPU / 8 workers.
- Même source exacte dans les deux campagnes, bundle SHA-256
  `ec62e7523b882f6eb6355b2f2f7e0cce0f085ac5075e0892da23d9554f8e1833`.
  Image Docker `openttd-lab:latest` id
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
- Rapports moteur et métriques dans `results/air_c121_prod_only_smoke_seed42_3y_20261010_r1*`
  et `results/air_c121_prod_only_exposure_8x5_20261010_r1*` ; résumé du replay
  `results/air_c121_prod_only_exposure_8x5_20261010_r1_probe.json`.

Le worktree `master` partagé était très modifié. Les manifests enregistrent
HEAD `3a68c6efc` avec `dirty=1` **et les sources figées dans le bundle** :
pour une comparaison, employer le bundle SHA et non supposer que HEAD seul
représente la version exécutée.

## Smoke : témoin de parité et isolation PASS/MAIL

Seed 42×3 : 2/2 parties complètes, sans erreur Squirrel repérée. Même
profit annuel (`2 135 251 £`) et valeur entreprise (`4 126 981 £`) avec
sonde OFF/ON. **Une** comparaison `status=compared`, zéro rejet témoin :

- Avion id 223 et N=1 identiques, capital `38 964 £` invariant.
- Cargaison transportée par mois : PASS `25 → 20`, MAIL `9 → 11`, anciens
  volumes sources contre volumes actuels.
- Recette annuelle `43 428 → 41 172 £` ; profit `36 080 → 33 824 £`,
  soit effet physique isolé `−2 256 £/an`.
- Le devis naturellement rafraîchi lors du même miss montrait auparavant
  `59 768 → 35 516 £/an` (écart `−24 252 £/an`), **non attribuable** à la
  seule production ; la différence entre les deux constats justifie le
  replay contrôlé plutôt que la comparaison de deux devis historiques.

## Diagnostic élargi : exposition, mais pas de décision changée prouvée

8×5 : 16/16 parties complètes, aucune défaillance signalée. Le profit
annuel de la sonde ON par rapport à OFF varie de `+28 764,625 £/an`
en moyenne (4 victoires / 4 défaites, Wilcoxon `p=1`, IC95 bootstrap
`[−66 819,375 ; +132 631,5] £/an`) ; **ce chiffre ne mesure pas un
gain de politique**, la sonde ajoute des évaluations/opcodes et peut
déplacer le calendrier moteur.

Analyse passive des **8 logs variante** :

| Événement | Nombre |
| --- | ---: |
| Recotations physiques valides après contrôle exact | 729 |
| Contrôles de parité rejetés | 119 |
| Cotations avec profit et score différents | 705 |
| Cotations de profit inchangé | 24 |
| Profit montant avec production courante | 277 |
| Profit descendant avec production courante | 428 |
| Basculement signe du profit | **0** |
| Capital changé | **0** |

Les 729 observations se répartissent entre `newpair=91`, `hubsite=104`,
`hubhub=534`. Elles couvrent 720 couples (graine, clé de devis) distincts,
mais ne forment **pas** 729 expériences indépendantes ; la graine 1337
en contribue 497, soit environ 68 %. L'âge médian du devis concerné est
194 jours et le maximum observé 686 jours. Le delta local de profit
(production courante moins source ancienne) a une médiane de `−912 £/an`,
une moyenne arithmétique de `−2 386,98 £/an`, et un éventail de
`−79 308` à `+47 664 £/an`.

Ces chiffres sont **la sensibilité du devis à la seule production source**,
pas un résultat de construction : moteur, N, distance, couverture actuelle,
concurrence, rating et capital sont conservés. Les 119 cas `control_mismatch`
ne doivent jamais être interprétés comme des effets causaux. Le replay
peut perturber le simulateur (temps/opcodes), d'où la distinction stricte
entre écart de cotation locale et performance terminale d'une politique.

## Verdict et suite de recherche

Le replay prouve que les révisions de production peuvent modifier matériellement
la cotation et le score économique d'un AIR sur le même état physique.
**Aucun basculement direct profit positif/négatif n'a été observé.** Il
n'identifie toutefois ni changement d'ordre entre AIR/RAIL, ni franchissement
de la limite de liquidité, ni investissement effectué ou perdu.

**Ne pas adopter l'invalidation exacte ; ne pas lancer de porte B.** Conserver
`c121_exact_prod_invalidation=0` et
`c121_production_only_replay_shadow=0` au défaut. Une étude de la frontière
de classement et de financement AIR/RAIL serait nécessaire **seulement si**
de nouveaux indices d'un effet économique significatif apparaissent ; elle
n'est pas une étape à lancer automatiquement à la suite de ce diagnostic.

## Mesure additionnelle d'opcodes (10 octobre 2026)

Le diagnostic initial n'avait **aucun compteur global d'opcodes OpexAI**
dans ses résultats (champs observed_opcodes_total et
observed_opcode_samples absents). Le delta économique entre deux politiques
identiques à la sonde près n'est pas une mesure d'opcodes.

Le replay a ensuite été muni d'une mesure transitoire avec
`AIController.GetOpsTillSuspend`, `AIController.GetTick` et le helper
`OpexAirCalcDeltaOps`. Elle ne s'exécute que lorsque le toggle expérimental
est ON. La valeur `replay_ops` est relevée au moment d'émettre le log
de comparaison ou de rejet de contrôle, **avant** l'émission du log.

Banc `air_c121_prod_replay_opcodes_2x5_20261010_r1` :

- Graines **100 et 1337**, 5 ans, **4/4 parties complètes**, 4 CPU /
  4 workers, même politique `c121_exact_prod_invalidation=1` OFF/ON
  de la seule sonde ; SHA bundle instrumenté
  `a3397f6e998d88e8fedb5b07c582c72d31b58a211baa05d3d28f07e56faa4c6c`.
- 715 événements mesurés (613 `compared` et 102 `control_mismatch`),
  **4 877 798 opcodes** au total : 952 081 sur graine 100 (141 événements)
  et 3 925 717 sur graine 1337 (574 événements).
- Événements `compared` : **4 544 497 opcodes**, moyenne **7 414**
  par événement, médiane **7 427**, p95 **7 725**, maximum **8 041**.
- Contrôles échoués : **333 301 opcodes**,
  moyenne **3 268** par événement, médiane **3 248**, p95 **3 374**.
- Tous événements avec log : moyenne **6 822**, médiane **7 409**,
  p95 **7 724**, minimum **3 040**.

**Limites de coût :** cette mesure porte sur les passages qui génèrent
un log ; elle ne compte pas directement les contrôles très bon marché
qui retournent sans log, l'émission finale des journaux, ni la politique
d'invalidation exacte présente **dans les deux bras**. Le coût total du
programme ne peut pas être déduit de ces compteurs sans profils globaux
et sans éliminer les effets sur le calendrier. Les coûts `replay_ops`
incluent les deux évaluations C121 à moteur/N fixes, ainsi que les
clones et la reprojection géométrique de demande, mais aucun scan
général de moteurs.

**Nombres magiques : aucun seuil supprimé.** Les seuils historiques
de production AIR restent `abs(delta)>=10` **et**
`abs(delta)*100 >= ancienneProduction*20` (catalog.nut).
Le replay montre un effet possible sur le score, non qu'un nouveau
seuil ou l'invalidation systématique augmenterait le profit réalisé.

## Décision de clôture : privilégier la simplicité (10 octobre 2026)

**Priorité P3, sujet clos sans modification de comportement.** Les bancs
montrent une sensibilité des devis PASS/MAIL mais **pas de bénéfice économique
significatif démontré** à rafraîchir davantage le cache. Le coût mesuré de
la sonde (7 414 opcodes en moyenne par comparaison valide) est un coût
de diagnostic, **pas** une justification pour conserver cette sonde active.

- **Conserver les seuils historiques** de `catalog.nut` : variation absolue
  d'au moins **10 unités ET** variation relative d'au moins **20 %**.
- **Ne pas introduire** moyenne mobile, variance, écart-type, filtre de
  Kalman, intervalles de confiance ou chaîne de décision statistique pour
  cette invalidation : complexité et maintenance disproportionnées par
  rapport à l'effet économique non démontré.
- **Ne pas remplacer** les deux seuils par un seuil de type `2σ`, qui
  serait un nouveau paramètre arbitraire, ni par l'invalidation à chaque
  variation, déjà non concluante économiquement.
- **Aucune nouvelle campagne ni aucun correctif planifié** sur ce point.
  Réouvrir uniquement en présence d'une preuve concrète de perte de profit
  due à un devis périmé ayant changé une décision de classement,
  de financement ou de construction.

Ce maintien de deux constantes existantes est **volontaire et documenté** ;
il ne signifie pas qu'elles possèdent une justification statistique.
La réduction des nombres magiques doit être concentrée sur les mécanismes
ayant un impact économique démontré, plutôt que sur ce cache AIR marginal.
