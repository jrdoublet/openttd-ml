# MULTI-1 — troisième levier : détour géométrique ROUTE (pré-enregistré le 26/10)

**Pré-enregistré avant code et avant essai ON.** Les deux pilotes de priorité
`multi1_road_priority` et `multi1_air_over_rail` sont définitivement
`NO-GO_NON_EXPOSE` avec seuils intacts. Ce troisième pilote teste **la
constructibilité routière en amont du classement**, comme demandé par H3.

## Données existantes motivant le choix

Les journaux appariés 5×5 de `multi1_airrail_exposure_5x5_20261026_engine`,
bras `reference`, sont une lecture descriptive. De 1971 à 1974, le moteur
émet **66** `PROJECT_DISCARD mode=road reason=plan_failed detail=TRACEX`
sur cinq graines (42 : 12, 100 : 40, 7 : 7, 999 : 7, 2026 : 0), et seulement
**11** `ROAD_BUILD` (42 : 4, 100 : 1, 7 : 2, 999 : 0, 2026 : 4). La médiane
des profits annuels des projets ROUTE élus est de l'ordre de **2 589–5 223 £**
sur les quatre graines qui en élisent, contre des lignes AIR généralement
beaucoup plus rentables. Les classements ne sont donc pas une cause unique.
Ce chiffre de 66 est une **quantité d'essais**, pas de couples distincts
ni une promesse de 66 lignes récupérables. `builder_road.nut` effectue des
trajets Manhattan et `opcode_exact.nut` tente déjà deux L puis quatre
détours ; remplacer le pathfinder par Pathfinder.Road a échoué selon
les essais historiques et n'est pas envisagé.

## Intervention strictement bornée

`multi1_road_detour` **0 OFF défaut** aux quatre profils, **1 shadow**,
**2 ON**. Le moteur n'appelle la nouvelle exploration qu'en multimodal
`MODE_AIR && MODE_RAIL && MODE_ROAD`, pour les années civiles **1971–1973**,
quand le constructeur ROAD a **épuisé ses six variantes historiques** et
que le motif de résultat serait exactement **`TRACEX`** (aucun depot trouvé
ou erreur SITEA/SITEB exclue). Pas de nouveau projet, pas de changement de
ROI/score/capitaux, de source de cargo, de ciblage rival ou de priorités.

Explorer au plus **quatre géométries supplémentaires** par paire de sites
existants : trois segments orthogonaux passant par `xmid=milieu_x−1`,
`xmid=milieu_x−2`, `ymid=milieu_y−1` ou `ymid=milieu_y−2`. Chaque point milieu
doit rester **sur le segment de coordonnées** de ses deux extrémités et sur
la carte, les deux coins doivent être plats. Appliquer exactement les
contrôles historiques : trace non vide et ≤48 tuiles, pas d'arrêt traversé,
chaque liaison réellement constructible en `AITestMode`, dépôt constructible,
et budget de **64 nouvelles tentatives maximum** par projet ; ne construire
que la première alternative validée. **1 shadow** explore et journalise
sans fournir de plan au chantier ; **2 ON** fournit le plan validé au
constructeur ordinaire. Les variantes historiques gardent leur ordre et
leur code. Le nouvel algorithme ne tourne jamais au défaut `0`.

Journal `MULTI1_ROAD_DETOUR` émis seulement lorsqu'un plan supplémentaire
serait admissible : année/date complète, `shadow|rescue`, `src,dst` et sites,
indice de variante et nombre de tuiles. Ce journal prouve qu'un tracé
physique suppléant a été trouvé, **pas** qu'il a été bâti ; le succès réel
doit être recoupé avec le même `ROAD_BUILD src,dst` dans le même log du bras ON.
Le défaut et la persistance Save/Load restent indépendants du levier ; la
liste des candidats est toujours régénérée après reprise.

## Critères irrévocables

- Contrats de limites/modèles, 58 réglages historiques, défaut OFF identique,
  shadow sans mutation, `--probes 0/2/258`, Save/Load réel graine 42 (2 ans
  avant reprise +1 après), smoke 1×1 graine 42 et `git diff --check` ; suite
  complète `python -X utf8 -m unittest discover -s sweeps -p "test_*.py"`.
- Exposition **5 graines 42,100,7,999,2026 ×5 ans** (1970–1974), carte
  256², OFF/ON, sondes **258** symétriques et journaux `--script-debug`.
  Autoriser la porte A **uniquement si** **≥3/5 graines** ont au moins un
  `MULTI1_ROAD_DETOUR action=rescue` ET **≥2/5 graines** ont un
  `ROAD_BUILD` avec le même couple `(src,dst)` sous **90 jours**, et 5/5
  parties appariées complètes. Si l'une échoue : `NO-GO_NON_EXPOSE`, ni A ni B.
- Porte A **40 graines canoniques ×5 ans** 1970, 256², sondes 2 symétriques,
  `profit_year` différence appariée ON−OFF, **gain moyen ≥4 %** de la
  référence, Wilcoxon bilatéral exact **p<0,05**, **borne basse IC95 bootstrap
  >0** (20 000 répétitions, graine 0) et **ratio des valeurs moyennes ≥0,95**,
  40/40 paires saines, quatre trimestres. Ne jamais transformer une simple
  5×5 d'exposition en porte A.
- Porte B conditionnelle seulement si A passe : **20 graines canoniques ×10
  ans**, `non_erosion`, borne supérieure IC95 bootstrap ≥0, garde valeur
  ≥0,95, 20/20 parties saines ; publier aussi Opex/AAA moyenne et médiane,
  cible stratégique distincte ≥75 % ; si B passe, demander une **décision
  utilisateur** sans changer la valeur du défaut.

Un Docker à la fois, image `openttd-lab:latest`, 10 workers, limites
10 CPU/8 Go. Conserver les historiques et ne toucher ni P1/VPS ni P6 ni
LATE-GAME-1.
