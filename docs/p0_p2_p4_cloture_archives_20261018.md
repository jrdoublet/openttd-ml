# P0, P2, P4 et C77 — archivage et clôture documentaire du 18 octobre 2026

## Décision

**Aucun prototype ancien P2/P4 ne doit être intégré comme politique de
production.** Les preuves qualitatives et quantitatives sont regroupées
dans `evidence/review/p0_p2_p4_20261018/`, indexées par un manifeste SHA-256.
Les réglages P0 et les prototypes de C77 ne sont pas réactivés. Le dépôt
conserve les optimisations **déjà** adoptées (dont V154 et V159), sans
rejouer les expériences d'octobre ni chercher des graines favorables.

Les ZIP, tests, analyseurs et patches sont des **archives de recherche**,
pas de nouvelles variantes livrées. Aucun banc, Docker, merge de worktree
ou suppression n'a été effectué lors de ce gel documentaire.

## Résultats à ne pas oublier

| Sujet | Preuve dominante | Verdict conservé |
|---|---|---|
| P0 Top-K dichotomie | 57 859 insertions identiques, −66,65 % en coût *local* ; deux 20×10, +97 899 £/an avec sonde et −8 341 £/an sans sonde, IC95 traversant zéro | Bonne idée opcode historique, **redondante avec V154/V157** déjà fusionné. Ni nouvel effet global ni bénéfice économique établi |
| P0 abandon second-check | 20×10, −67 847 £/an, 11V/9D, IC95 [−247 234 ; +97 158], valeur −1,03 % | `non_erosion=pass` n'est **pas** un gain ; ne pas promouvoir l'ancien correctif |
| P0 concurrence visible | 40×3, −48 485 £/an, 15V/25D, valeur −3,52 % | Porte A échouée ; pas de B ni d'adoption |
| P0 sonde AIR veto | 46 visites 1973 échantillonnées, dominées par la capacité du premier aéroport ; sonde intrusive | Ne démontre aucune alternative finançable/constructible perdue |
| P0 rail A* et queue opcode | 3×5 de diagnostic RAIL ; 7,23 M opcodes de plafond théorique en fin de boucle, zéro récupérable prouvé | **Diagnostics seulement**, pas de modification de scheduling |
| P0 C117 | Sonde historique peu concluante ; V159 lean C117 20×10 non-érosion ensuite adopté | Garder **V159 actif**, non le vieux probe P0 |
| P2 froid | 281 AIR construites ; 102 en 1970–71, 43 strictement comparables ; trois flips LOSO sans construction de l'alternative | Pas de `score_cold_prior` calculable de manière causalement défendable |
| P3 / P4 stable-cohort | 40×5, Δ profit annuel −58 916 et −43 730 £/an | Rejets acquis ; ne pas répéter |
| P4 garde AIR | Pilote 5×5 +68 192 £/an, mais holdout 40×5 −52 352 £/an, IC95 [−96 110 ; −15 267] | **Rejet indépendant**, vérifiable depuis JSONL et reçu externe |
| P4 crash-only | Une reconstitution physique après crash prouvée ; 5×5 −5 292 £/an, 1V/4D | Intervention exposée mais non gagnante |
| H1 flotte AIR | 0 `P2_FLEET_AIR_DEFER` en 3×5 | Hypothèse **non exposée** : delta terminal apparent non causal |
| H2 revenu net | Précontrôle A/A et 5×5 final −16 913 £/an, 2V/3D | Non qualifié ; dispersion et différence d'opcodes à surveiller |
| H3 hub signé | 9 475 cotations positives/18 148 ; 5×5 −109 433 £/an, 3V/2D | Pas de gain prouvé ; une cotation ne garantit ni chantier ni profit réseau |
| C77 same-save | Serveur dédié : contrôles A/A identiques et alternative physiquement bâtie, sans profit cinq ans apparié | **Outillage causal à garder**, mais ne pas adopter le choix alternatif |

Les montants sont des différences *variante moins témoin* sur le profit
annuel terminal de la campagne indiquée, **pas** des gains récurrents
garantis. Les échantillons, instruments et versions source diffèrent entre
les familles. Les détails de H1/H2/H3, P3/P4, du replay incomplet et du
vivier H3 figurent dans le bilan historique déjà suivi :
`docs/p2_p4_bilan_final_et_suspension_20261014.md`.

## Fichiers stratégiques préservés

**Priorité P4/C77** : `verify_p4_guard_gate_20261013.py`, ses tests et son
reçu indépendant ; `c77_savefork_host_20261013.py`, l'outil de comparaison
A/A et les états de replay/sauvegardes du serveur dédié. Les forks à
troisième compagnie fantôme ne servent que d'avertissement méthodologique.

**Priorité P2** : `analyse_score_cold_p2.py`,
`analyse_score_cold_execution_p2.py`, l'audit de population P2 et le
vérificateur `qualify_p2_p4_evidence_20261014.py` avec ses tests. Ils
établissent quelles observations manquent à un vrai rendement marginal.

**Priorité P0** : `analyse_p0_topk_check.py`, analyses d'opcodes et de
construction, campagnes avec et sans profilage, JSONL et bundles figés.
Les tests de parité restent instructifs même lorsque la politique de
production est depuis passée à V154.

La compilation documentaire ne change pas le contrat d'adoption : une
politique de classement doit établir une différence de décision au même
état, construire l'alternative, mesurer son effet sur l'ensemble du réseau
et qualifier `profit_year` et `company_value`. À défaut, aucune règle
arbitraire de score, de cash ou de filtrage n'est introduite.

## Consultation et contrôle

Voir le [README des archives](../evidence/review/p0_p2_p4_20261018/README.md)
pour la correspondance des six paquets, l'intégrité, les limites et les
chemins des scripts. Contrôle entièrement hors moteur :

```powershell
python3 -X utf8 sweeps/verify_p0_p2_p4_archive_20261018.py
```

Les archives sont volontairement **sélectives** (preuves de décision,
sources gelées et scripts de validation), pas une copie des répertoires
`results/` de tous les worktrees. Ceux-ci restent inchangés, avec leurs
matériaux non publiés. Les patches d'expérience ne doivent jamais être
appliqués directement au `master` courant.
