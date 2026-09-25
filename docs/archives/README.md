# Archives de code non intégré

Travail expérimental conservé sous forme de patch quand il n'a pas pu être fusionné proprement
dans `master` et que sa mesure l'a écarté. Ces patchs ne sont pas une file de travail.

| Fichier | Base | Contenu | Pourquoi pas dans `master` |
|---|---|---|---|
| `v92_1_v92_2_non_retenus_base_6c18ef0.patch` | `6c18ef0` | V92.1 (`v92_reequip`, rééquipement de flotte, garde d'opportunité `OpexV92UpdateBestPending`), V92.2 (`v92_engine_criterion`, amortissement 20 ans, courrier 15 %), sondes `V92_ROUTE/BUILD/REPLACE/ANNUAL`, `test_v92_hardening.py` — ancien worktree `.wt_agy_v92fix`, jamais commité | 5×6 du 2026-09-24 non retenus (V92.1 −865 k£/an, V92.2 −627 k / −86 k ; `docs/taches.md`, ligne V92). Écrit en parallèle du commit V92 `d543e39` (`V92_CLOSED_PAIRS`) : la fusion textuelle passe mais mélange les deux logiques (`test_v92_air_service` échoue). À réappliquer avec `git apply -3` sur `6c18ef0` puis à reporter à la main si la piste est rouverte. |
