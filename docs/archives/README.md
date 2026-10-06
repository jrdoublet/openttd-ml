# Archives — sources anciennes et code non intégré

[Index documentaire](../README.md) · [Tâches courantes](../taches.md)

Ces documents ne sont pas des consignes courantes. Les originaux corrompus restent
intacts : ne pas reconstruire un signe, chiffre ou identifiant par supposition.

| Document | Nature |
|---|---|
| [Ancien backlog du 9](taches_archive_2026-09-09.md) | Source historique, pas travail actif |
| [Phase 0 / TrainLineAI](phase0_trainline_synthese.md) | Synthèse sourcée de l'ancien README, pas copie intégrale |
| [C116](c116_extraits_originaux_non_autoritaires_2026-09-30.md) | Extraits non autoritaires ; capacités et chiffres à réconcilier sur preuve |
| [C117](c117_original_corrompu_non_exploitable_2026-09-30.md) | Original corrompu non exploitable, conservé pour récupération |

## Code expérimental

Travail expérimental conservé sous forme de patch quand il n'a pas pu être fusionné proprement
dans `master` et que sa mesure l'a écarté. Ces patchs ne sont pas une file de travail.

| Fichier | Base | Contenu | Pourquoi pas dans `master` |
|---|---|---|---|
| `v92_1_v92_2_non_retenus_base_6c18ef0.patch` | `6c18ef0` | V92.1 (`v92_reequip`, rééquipement de flotte, garde d'opportunité `OpexV92UpdateBestPending`), V92.2 (`v92_engine_criterion`, amortissement 20 ans, courrier 15 %), sondes `V92_ROUTE/BUILD/REPLACE/ANNUAL`, `test_v92_hardening.py` — ancien worktree `.wt_agy_v92fix`, jamais commité | 5×6 du 2026-09-24 non retenus (V92.1 −865 k£/an, V92.2 −627 k / −86 k ; [synthèse des décisions](../journaux/synthese_decisions_2026-09-30.md)). Écrit en parallèle du commit V92 `d543e39` (`V92_CLOSED_PAIRS`) : la fusion textuelle passe mais mélange les deux logiques (`test_v92_air_service` échoue). À réappliquer avec `git apply -3` sur `6c18ef0` puis à reporter à la main si la piste est rouverte. |
