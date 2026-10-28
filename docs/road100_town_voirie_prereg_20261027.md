# ROAD100-2b — tracé voirie des bus locaux (pré-enregistré le 27/10)

Le prototype ROAD100-2 (`road100_town_bus=1`) a créé six véhicules de plus
que sa référence sur la graine 42 (+4 753 £/an) mais 5×1 donne −800 £/an
en moyenne, 2V/3D. Des lignes locales de dix tuiles subissent de nombreux
`plan_failed detail=TRACEX`/`DEPOTX`. Le constructeur `OpexRoadPlanForActive`
saute explicitement `OpexRoadPlanPaxVoirie` lorsque `srcTown==dstTown` ; or
ce planiteur cherche des arrêts traversants sur des rues existantes et tente
un BFS court avant les tracés neufs. Le code existe et ne nécessite aucune
nouvelle politique de marge ou de demande.

Le seul changement ROAD100-2b est `road100_town_voirie=1` : dans les jeux
ROUTE seule avec `road100_town_bus=1`, appeler le planiteur voirie également
pour les paires intra-ville et conserver le fallback historique s'il échoue.
`road100_town_voirie=0` aux quatre difficultés ; `road100_solo_pax=0` et
`road100_road_batch=0` pour isoler la géométrie. Les deux bras utilisent le
MEME bundle, `estim_unifie=31` et la même configuration AAAHogEx route seule.

Contrôles : smoke 1×1 graine 42 pour compilation, `VOIRIE_PLAN ok=1`, santé
et reconstruction réelle ; diagnostic 5×1 graines 42,100,7,999,2026 si exposé,
mesure des rejets `TRACEX`, `DEPOTX`, des constructions `ROAD_BUILD`, des
profits Opex et de la valeur. Si gain plausible, porte descriptive 40×5 pour
mesurer chaque année ; sinon arrêter cette variante. Le seul nombre de plans
voirie ne constitue pas un résultat économique. Défaut inchangé, portes V102
requises pour adoption, B uniquement avec autorisation explicite.
