# C121 territoire : nouveau 40×5 du 11/10

Demande explicite utilisateur après le 40×3 fail_primary : 40 nouvelles graines ×5 ans. Nouvelle mesure séparée ; ne remplace pas le verdict 40×3 et ne sélectionne pas un meilleur horizon après coup. Pas de changement de défaut, commit, push ou B automatique.

## Pré-enregistrement

Référence OpexAI[c121_territory_first=0], variante OpexAI[c121_territory_first=1], autres défauts actuels identiques, télémétrie OFF. Même code que le 40×3 et smoke déjà sain/exposé, bundle attendu cf065a29e3a660107adaf09e20c78c0f97e4aec49e7b96b746ed1bf2efedb2de. Arbre modifié uniquement en documentation, aucune modification IA.

Horizon5 ans, 40 graines distinctes, une répétition, 80 duels/400 années de jeu. Règle gain_short explicitement pré-enregistrée à5 ans : profit_year Opex variante moins référence terminal ; Wilcoxon exact bilatéral p<0,05, borne basse IC95 bootstrap moyenne>0 et gain moyen au moins4 % ; garde valeur ratio des moyennes>=0,95. Bootstrap20 000, graine0. Quatre trimestres valides, santé80/80 et couverture40/40 requises. Aucune relance favorable.

Graines tirées sans remise par random.Random(202610115).sample(range(10000000,99999999),40), sans intersection avec les40 précédentes :

53644953, 56556710, 48327219, 74783501, 11523575, 83478077, 33406951, 93402396, 60996924, 94675334, 55993009, 17854251, 51245262, 91580657, 85919927, 27995534, 96596405, 51993964, 45101861, 42852319, 21131181, 98518150, 81717286, 98621834, 29680987, 56178512, 18239050, 76801160, 45100677, 19396440, 67973430, 19910979, 38782380, 11549050, 64749635, 91246535, 43910499, 87850257, 36473740, 12429505

Campagne c121_territory_A40x5_holdout_20261011_r1, sortie results/c121_territory_A40x5_holdout_20261011_r1.json. Docker local, image attendue sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659, 10 CPU/8 Go RAM/swap8 Go/10 workers, cache openttd-lab-home. Aucun conteneur concurrent lors du contrôle préalable.

## Suivi

Lancé sur SHA bfdb2b91d4b2cc58d2f29ea6ef9d2389367ff2f3. Bundle et image identiques au 40×3 ; manifest SHA256 c1d49898482af8fc62cf6e71493277fcbef0ed0163227f066f0f2849d1d74185. Terminé : fail_primary.

## Résultats

80/80 duels complets et sains, 40/40 paires, aucune partie échouée ; comparison_complete, adoption_sample_complete et metric_coverage_complete vrais. Les80 observations Opex terminales ont quatre trimestres valides. Les40 graines n'ont aucun recouvrement avec le 40×3.

- Profit annuel ON−OFF : −28 478,425 £/an (−1,4477 %), médiane −11 783 £/an ; 18 victoires, 22 défaites, aucune égalité.
- IC95 bootstrap moyenne [−104 950,375 ; +50 743,525] £/an ; Wilcoxon exact bilatéral p=0,397424. Bootstrap20 000, graine0.
- Seuil requis +78 686,232 £/an (+4 %). Moyenne sous seuil, IC traversant zéro et p supérieur à0,05 : verdict brut fail_primary.
- Valeur : ratio des moyennes 0,978702, soit −2,1298 % ; garde −5 % tenue.

Ni gain utile ni équivalence démontrés ; cette mesure ne montre pas une perte statistiquement significative. Le verdict du 40×3 reste conservé, sans fusion des échantillons ni sélection du meilleur horizon. Défaut0 inchangé, pas de B/adoption/commit/push.

Sources brutes : results/c121_territory_A40x5_holdout_20261011_r1.json, .jsonl, manifest, bundle et logs. JSON SHA256 3e5674dd689a1c6bbcdb41555cd817e07e08038000512a75d50c0f328772c1c2. Manifest SHA256 c1d49898482af8fc62cf6e71493277fcbef0ed0163227f066f0f2849d1d74185. [Deltas par graine](archives/c121_territory_first_A40x5_20261011.csv).

## Clôture utilisateur après les deux essais

Le11/10, rejet explicite puis suppression du réglage et de son code exclusif. Les verdicts et bundles ci-dessus restent historiques, intacts. Comportement de l'ancien défaut0 conservé ; 78 contrats verts et smoke du nettoyage42×1 sain. Voir [journal du retrait](journaux/journal_2026-10-11.md#rejet-et-retrait-c121--territoire-dabord). Aucun commit/push.
