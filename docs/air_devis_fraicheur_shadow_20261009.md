# V126 — fraîcheur du devis AIR au lancement d'un chantier

## Protocole pré-enregistré — lecture seulement, avant mesure

Risque statique : `OpexC121PrepareEngineStatic` conserve le devis dans
`plan.c121EngineStatic` jusqu'au prochain calcul ; `projects_update.nut`
recycle les candidats AIR, et `task_air.nut` finance sur `buildPlan.capital`
sans recalculer le nivellement au dernier garde. La revalidation du cache
C121 ne concerne que ses *nouvelles* consultations, pas les candidats déjà
présents dans le portefeuille. Un terrain changé entre création et achat
pourrait donc rendre le besoin `cash` obsolète. **C'est une hypothèse,
pas une exposition démontrée.**

Ajout du seul commutateur `air_site_stale_shadow=1`, **OFF aux quatre
difficultés**, sans aucune branche de rejet ni modification de capital.
Sous `air_site_cost_quote=1`, au dernier contrôle de trésorerie des chemins
portfolio et legacy, lire directement `OpexAirV95LevelCost` pour les seuls
nouveaux sites, hors du cache quotidien (terrain pouvant changer le jour
même). Journal `AIR_SITE_STALE` : phase, date jeu, `economicsDate`/âge de projet,
OD/ancres, niveaux d'origine et frais, impossibilité, changement, hausse du
besoin (`shift` incluant le supplément de marge le cas échéant), cash,
`flip` d'admissibilité. Les codes négatifs sont traités comme incapacité,
jamais comme des crédits. Ces calculs sont **observationnels** et ne
modifient aucune décision ; overhead opcode et calendrier moteur possibles
quand la sonde est activée, à vérifier avant toute adoption.

Profil prévu : branche `master` HEAD de base `cb23a17`, Git dirty conservé,
Docker local `desktop-linux`, image `openttd-lab`, 10 CPU/8 Gio/10 workers,
**une seule campagne à la fois** ; vérification `docker ps` avant chaque
exécution. Smoke apparié 1×1 seed42 : témoin devis ON + marge historique,
`probe_air_finance_margin=1`, versus même bras avec
`air_site_stale_shadow=1` pour compiler et vérifier absence de mutation de
la décision. Identifiant `air_site_stale_shadow_smoke_1x1_20261009_r1`.
Ensuite mono-bras
**6 graines × 3 ans**, graines fixées 42,100,999,1234,5678,2026, même
profil `OpexAI[air_site_cost_quote=1,air_site_quote_keep_legacy_margin=1,air_site_stale_shadow=1]`,
`--script-debug`, une répétition, sortie
`results/air_site_stale_shadow_6x3_20261009_r1*`. Ce n'est ni une porte A
ni une qualification de marge. Compter séparément les projets avec
ancien devis différent, quote impossible, `flip` de finançabilité ;
regrouper par graine/âge et ne pas appeler les observations des projets
uniques si les mêmes tentatives se répètent. Ne pas tester un nouveau
paramètre numérique ni changer le défaut sur absence d'exposition.

## Résultats et verdict

**Smokes appariés seed42×1 an : 2/2 complets et sains**, bundle
`aec3a7237ce89d3686d7d3fc40067046d7b3a6b26658265ec169f5ce0604311a`,
rapport `results/air_site_stale_shadow_smoke_1x1_20261009_r1.json` et
`_breakdown.json`. L'armement de la sonde produit **11 observations**, dont
8 projets déjà âgés et **4 devis différents** ; pas de devis impossible,
**0 inversion de garde cash**. À noter : profit variante−référence
**+35 082 £/an** et valeur **+3,26 %** sur la graine 42 à 1 an, bien que la
sonde ne modifie aucune donnée décisionnelle : **les opcodes additionnels
changent le calendrier du moteur et peuvent faire bifurquer la partie**.
Ce delta n'est pas un gain de politique ni une preuve de neutralité temporelle.

**Diagnostic principal 6 graines × 3 ans : 6/6 parties complètes/saines**,
même bundle `aec3a7237ce89d3686d7d3fc40067046d7b3a6b26658265ec169f5ce0604311a`,
manifestes moteur/JSONL et rapports
`results/air_site_stale_shadow_6x3_20261009_r1.json`,
`results/air_site_stale_shadow_6x3_20261009_r1_breakdown.json`.

| Graine | Contrôles observés | Projet avec âge affiché >0 jour | Devis changés | Cas inversant la garde cash | Âge maximal du projet affiché (jours) |
|---|---:|---:|---:|---:|---:|
| 42 | 29 | 22 | 9 | 0 | 225 |
| 100 | 26 | 20 | 5 | 0 | 78 |
| 999 | 84 | 82 | 34 | 0 | 10 |
| 1234 | 31 | 27 | 9 | 0 | 155 |
| 5678 | 61 | 48 | 11 | 0 | 59 |
| 2026 | 82 | 81 | 43 | **1** | 193 |
| **Total** | **313** | **280** | **111** | **1** | 225 |

**Limite de la colonne âge :** `AIDate.GetCurrentDate() - project.economicsDate`
mesure l'âge d'un objet candidat, **pas nécessairement l'âge du devis**.
Une reconversion incrémentale peut réécrire `economicsDate` tout en conservant
`plan.c121EngineStatic` et sa quote antérieure. Donc `age=0` ne prouve pas
qu'un devis a été fait aujourd'hui ; le compte de 280 ne dénombre pas
exhaustivement les devis réellement anciens. La comparaison des montants
par ancre, qui ne dépend pas de cette date, reste valable.

Sur les 111 écarts, **67 renchérissent** le devis, 43 le réduisent et
1 est compensé entre les extrémités (écart net nul). Les différences absolues
ont médiane **45 £**, p90 empirique **135 £**. Hausse maximale observée
**+344 £**, baisse maximale **−12 780 £** (événement extrême).
**107/111** différences ont un âge de projet affiché ≥1 jour,
**4/111** ont un âge affiché nul, sans garantie d'une quote du jour ;
contourner le cache de devis journalier reste nécessaire.
Aucun `v126Quoted`
manquant et aucune quote passée à `-1` dans ces essais.

**Le seul renversement cash** : graine 2026, jour jeu 720117, rang 63,
villes 43→11, deux aéroports neufs, ancres 18980 et 10340,
`economicsDate` vieux de 7 jours. Ancien nivellement A=12 780 £,
nouveau=0 £ ; B inchangé 1 325 £. Cash disponible 156 463 £,
besoin mémorisé 167 437 £, besoin frais **154 657 £**. Le calcul ancien
refuse une construction qui aurait franchi le seul contrôle de trésorerie
avec devis actualisé. Cela ne prouve pas que la ligne aurait été
construite ou profitable : le budget/score, l'ordre des choix et les
autres gardes resteraient à reprendre. **Aucun cas symétrique de cash
surévalué et construction pourtant acceptée** n'a été observé.

**Verdict : mécanisme d'obsolescence démontré, dommages de financement
rares sur cet échantillon (1 événement/313).** Ne pas introduire pour
l'instant de garde qui rejette/reclasse des projets AIR : elle aurait un
coût opcode élevé et un risque de modification économique non étayés par
une amélioration mesurée. L'opportunité négative de la graine 2026 est
réelle au stade de la garde, mais insuffisante pour quantifier l'avantage
net d'une remise à jour du capital et du classement au sein du portefeuille.
Le coût de ce recalcul doit être mesuré à charge égale avant toute adoption.
Le toggle **reste OFF**, le devis reste OFF par défaut, la marge ne change
pas et aucune porte V102 A/B n'est engagée.
