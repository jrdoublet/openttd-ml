# RVA — réanalyses du 19 octobre 2026

Les quatre archives sont des réanalyses hors moteur, pas des campagnes neuves
ni des qualifications économiques. `index.json` conserve SHA du JSON brut et
du gzip déterministe (mtime=0) ; chaque JSON contient les SHA des journaux lus.
Aucune sauvegarde, cache ou copie du code adverse ajoutée.

- `calibration.json.gz` : 80 journaux V216, séparation par graines, 34 lignes
  avec recette réalisée annualisée ; erreur de projection, pas erreur locale
  de livraisons (absente des anciens logs).
- `network.json.gz` : paquet V207/V212 apparié, 20 logs et synthèse ; projection
  rétrospective du coût des achats évincés, contrôle défavorable conservé.
- `learning.json.gz` : 12 journaux RVA, séparation temporelle ; séjour observé,
  contrôle défavorable conservé, coût de l'ancienne sonde seulement.
- `replay.json.gz` : 80 logs V216, 6 925 clichés ; 1 488 entrées entièrement
  rejouables, les autres explicitement incomplètes. Aucun achat de variante
  exécuté ou mesuré.
- `default_inert.json` : égalité statique du builder après retrait de la seule
  garde RVA OFF, contre b229674. Aucun moteur invoqué.

Reproduction : scripts `calibrate_rva.py`, `validate_rva_network.py`,
`validate_rva_learning.py`, `replay_rva_logs.py` ; arguments et unités dans
les documents `docs/rva_08_estimateur_20261019.md` à
`docs/rva_16_intervention_20261019.md`. Sources sous
`/home/deploy/projects/openttd-ml/results/`, dont
`worktrees_archives_20261018/wt-v216-probe/results` et `wt-rva/results`.
Les archives historiques, bundles et manifestes restent intacts.
