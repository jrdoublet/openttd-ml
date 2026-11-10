# Revue EB-14 vs C77/PO01C (09/11/2026)

## Décision
Option 2 : **conserver** `ai/OpexAI/orchestrator.nut:645-653` (exception EB-14) et
adapter les deux tests de contrat en les renforçant. Aucun `.nut` modifié.

## Vérifications
- Défaut actif : `info.nut` `eb14_progressive` easy/medium/hard/custom/default = **3** ;
  `settings.nut:706-707` `EB14_PROGRESSIVE = eb14Mode >= 1` ; `globals_pre.nut:123`
  ne fait que déclarer (`false`) avant chargement.
- Origine : l'exception et le lancement `EB14_START` (`_runOrchestratorTick`) entrent
  tous deux dans `7160c6f5` (`git log -S`), seul commit qui les touche.
- Qualification : `docs/estim31_default_validation_20261030.md` — vainqueur
  `v161/mix_a200_r075_w15_slope`, **66,557726256 %** après 20 graines × 10 ans,
  40/40 parties saines ; « tous les fichiers OpexAI installés sont ceux du bundle
  qualifié » (SHA recalculée par `estim31_promote_default_20261030.py`).
  `docs/taches.md:1178-1179` (défaut publié le 30/10). **Limite :** il s'agit d'une
  sélection entre trois finalistes ESTIM-31 qui contenaient tous ce code, pas d'une
  porte V102 A/B isolant l'exception. Elle est qualifiée comme partie du bundle, pas seule.
- Chiffres de `wt-agyeasy/docs/agy_specs/defauts_decouverts.md` (+45 à +90 j, 180-360 j,
  5 000-12 000 £/an, 15-25 % de subventions, regret 5-8 %) : **aucune source mesurée**
  (aucune citation, aucun résultat dans `results/` ou `docs/`). Non repris.

## Changements de tests
- `sweeps/test_c77_intent_defer.py::test_po01c_stale_portfolio_blocks_mode_2_c77_build` :
  regex multi-ligne, présence exacte de la clause EB-14, table de vérité étendue à
  13 cas : les 5 historiques (EB-14 OFF) inchangés, exception c77_build débloquée,
  blocage maintenu pour `c77_subsidy`, `_projects == null`, worker actif ; aucun
  déblocage quand PO01C est inactif ou modes off.
- `sweeps/test_po01c_regen_split.py::test_po01d_synchronous_path_bytes_unchanged` :
  neutralise les **deux** fragments EB-14 exacts (garde et `EB14_START`, chacun présent
  une fois, chacun dans sa fonction) ; le reste retombe sur le SHA PO03 historique
  **inchangé** `1600953e…` (pas de rebaseline).

## Tests
Avant/après (c77*, po01c*, road1y*, road100*, v251*) : 2 échecs en moins, aucun nouveau.
road1y 74 OK, road100 236 OK (3 skip), v251 7 OK. Restent préexistants (hors périmètre,
non liés à la garde) : `test_c77_intent_defer` `test_modes_0_1_orchestrator_bytes...`
(SHA 8c9c9e1a déjà faux avant `7160c6f5`) et `test_setting` (hunk V233L settings) ;
`test_po01c_regen_split` po01d sous-tests air_planning/candidates/main/settings/info et
`test_po01f_historical_dependencies_unchanged` (dérives ESTIM-31 hors orchestrator).
`git diff --check` propre.

## Risques résiduels
Gain économique de l'exception seule non mesuré ; à isoler par A/B dédié si contesté.
