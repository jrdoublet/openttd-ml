# V233 — livraison « vraie chaîne », 18/10/2026

Implémentation sur `/home/deploy/projects/wt-v233b`, branche `v233b`, base
propre `835bd96`. Aucun push, Docker ou lancement OpenTTD. Les deux rapports
externes demandés ont été lus ; seul le rapport de job explicitement demandé
est écrit hors du worktree. Les pertes antérieures restent des échecs ; les
−113 k£/an du mode 4 en 40×10 sont un résultat communiqué par l'utilisateur,
non une mesure de cette livraison.

## Conception et comportement livré

[Conception écrite avant le code](v233_chaine_20261018.md), commit `ace2eae`.
Code et contrats : **`868674e`**, « V233 : alimenter les usines avant de choisir
la ville des biens ». Même réglage public, nouvelle valeur **5**, défaut 0 ;
`v233_pending_continue=1` reste une dépendance explicite. Aucun nouveau réglage.

Les usines sont découvertes par leurs listes API de produits/intrants et le
label GOOD, sans ID de cargo fixé et sans condition de production préalable.
Le générateur fret existant reçoit une tranche source/cargo/usine ; une seule
paire est chiffrée par invocation. Son économie multicargo permet à une rame
de livrer céréales et bétail depuis la même ferme, même lorsque le réglage
V163 global reste éteint. Des fermes distinctes et la jointure de destination
V178 restent possibles. Ces mécanismes sont bornés aux offres du mode 5.
En tempéré, le plan doit couvrir GRAI et LVST ; l'acier est facultatif.

Le ratio **1 unité livrée → 1 unité de biens** est vérifié dans OpenTTD 15.3 :
[Factory native, multiplicateurs 256](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/table/build_industry.h),
[TriggerIndustryProduction, division par 256](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/economy.cpp).
Les apports s'additionnent. La prévision utilise le volume **transportable**
`carried + carried2`, pas la production brute de toutes les fermes.

Pour chaque usine, les apports retenus et la meilleure économie aval donnent
`(P_amont + P_biens)/(K_amont + K_biens)`, profits calibrés et capitaux
finançables, immobilisation comprise. Ce rendement borne le score des
propositions amont. Leur profit de ligne reste leur profit propre ; seul
un représentant peut recevoir l'option approuvée : p=25 %, délai 2 ans,
taux 10 %, horizon 5 ans, capital aval soustrait de sa valeur et conservé
au dénominateur, plafond 10 % du score propre. La calibration et les devis
actualisés sont pris en compte sans ajouter le profit aval aux comptes amont.

La réduction à une offre par intrant et à une source par ferme est une
heuristique bornée ; elle ne résout pas toutes les combinaisons possibles.
Le classement conserve les contraintes du portefeuille : il ne promet pas
de financer successivement tous les maillons, ni d'élire systématiquement
l'usine au plus grand rendement total lorsque son amont est moins compétitif.
Cela respecte la borne d'option et l'absence de priorité forcée.

Le seuil mesuré `OpexV233AirYieldAllows` compare d'abord **toute** la chaîne
à l'alternative AIR. À l'exercice, il compare aussi l'aval marginal à AIR :
le profit amont déjà acquis ne finance pas artificiellement une mauvaise
sortie. Un rendement AIR inconnu fait attendre, notamment dans une compagnie
sans avions ou avant une année civile complète. Aucun taux de remplacement
arbitraire n'est ajouté et aucune famille V252 n'est modifiée.

La greffe existante exige nos alimentations vivantes, trois vrais mois
consécutifs de production, et un volume capté permettant de remplir au moins
la rame dimensionnée par rotation. Les mois nuls restent dans la moyenne.
L'observateur continue pendant le balayage des villes. Toutes les économies
urbaines jusqu'à la borne V168 courante (160 au défaut) sont comparées sur
un même volume de référence ; les sites sont ensuite cherchés par rendement
décroissant, un candidat par invocation. La première ville faisable dans cet
ordre remplace la ville voisine des modes antérieurs. Le devis réel, la
validation avant dépense et le réarbitrage des plans aval restent en place.

Pas de chaîne active exclusive, réserve de caisse, nouveau `Sleep`, nouvel
ordre de transfert ou priorité rail. La continuation V233 et ses vrais
compteurs de construction restent utilisés. Les apports joints réutilisent
les protections de jointure et l'identité de gare partagée.

## Fichiers et traces

- `goods_v233chain.nut` : calcul reprenable, contrats économiques, option,
  admission amont/aval, publication sans doublon rail d'une même paire.
- `candidates.nut` : tranche du générateur fret ; `goods_v233e.nut` : observation
  et choix économique de ville ; `goods_v233.nut` : publication et garde aval.
- `projects_selection.nut` : supplément et borne de score uniquement en mode 5.
- `task_rail.nut`, `builder_rail.nut`, `lines.nut` : contrôle avant toute
  dépense, usine réellement couverte, jointure et enregistrement central
  des apports réussis, y compris après A* reprenable.
- `info.nut`, `settings.nut`, `globals_pre.nut`, `main.nut`, `scheduler.nut` :
  borne, chargement et branchements du mode ; respect de `mode_rail=0`.
- `persist.nut` : caches d'offres et curseurs vidés au Load/réconciliation ;
  les faits de ligne restent des scalaires du codec existant. Aucun candidat,
  promesse, plan ou objet API nouveau n'est sauvegardé.
- `task_report.nut` : réalisé annuel par ligne, relié à l'usine.
- `sweeps/test_v233chain.py` et contrats V233/V163/V166/V178 existants :
  gardes explicites du mode 5, ancien comportement contrôlé hors de ces gardes.
  Le hash historique de la transaction rail retire exactement la nouvelle
  garde, puis continue de vérifier tous les autres tokens.

Sous DECISION_LOG : `V233_CHAIN state=candidate` contient les profits/capitaux
amont, aval et totaux, volume et admission ; `state=input_built` contient ligne,
cargos, distance, wagons et coût réel. `V233_OBS policy=5` donne les mois,
production **globale** et fenêtre. `V233_BUILD policy=5` ajoute ville, distance
économique du candidat et wagons réellement posés. `V233_DELIVERY` conserve son témoin de déchargement.
`V233_CHAIN state=realized` donne profit/revenu annuel et identifiant de ligne,
en complément de `LINE_REVENUE`. La production globale n'est pas présentée
comme une mesure causale de notre contribution.

## Vérifications et limites

Commande exécutée depuis ce worktree :

```bash
PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"
```

**1 977 tests, OK, 3 ignorés, 22,301 s**, sortie 0. Journal :
`results/v233chain_tests_delivery_final.log`. Les premiers passages ont trouvé
des contrats statiques à actualiser pour les nouveaux branchements ; ils ne
sont pas présentés comme verts. Les messages de smoke des fixtures Python
ne sont pas des parties exécutées.

`git diff --check` propre. `campaign_freeze.parse_ai_settings` confirme les
**76 mêmes noms et défauts** qu'à `835bd96`, dont V233 0/0 ; la seule borne
modifiée est 0..5. Les lignes ajoutées/retirées du diff IA ne contiennent
aucun réglage des familles protégées. Tous les helpers Opex appelés dans
le nouveau module sont définis dans l'arbre courant.

**Non validés :** compilation Squirrel, exécution/Save-Load moteur, exposition,
opcodes et économie. Les contrats Python sont statiques. Les recettes
NewGRF ne sont pas modélisées : NoAI 15 n'expose ni leur ratio ni une liste
des GRF chargés. Il faut vérifier le protocole natif sans NewGRF dans le
manifeste ; il n'existe pas de garde automatique prétendant le détecter.
Les recherches de sites réutilisées peuvent encore coûter plusieurs ticks ;
une invocation bornée n'est pas une mesure d'opcodes. Aucun gain ni adoption
n'est annoncé et aucun défaut n'est changé.

## Plan de banc demandé — préparé, non lancé

Même arbre figé entre bras, configuration native, adversaire identique,
autres réglages aux défauts courants. Ce contraste évalue le paquet mode 5
avec continuation, pas séparément l'option, le multicargo ou le seuil AIR.
Avant lancement : vérifier branche/arbre réellement transporté, contexte
Docker, image exacte, montage, cache, absence de campagne concurrente sur
VPS et disponibilité des ressources. Le lanceur conserve le bundle et
plafonne le swap à la RAM. Utiliser des identifiants neufs s'ils existent déjà.

**1. Exposition VPS : 10 graines canoniques × 10 ans, 20 duels**, journaux
identiques aux deux bras, profil 3 CPU / 2 Go / 3 workers :

```bash
python3 sweeps/run_c66_reference.py \
  --campaign v233chain_expo_10x10_20261018 \
  --reference 'OpexAI[decision_log=1,v233_pending_continue=0,v233_goods_graft=0]' \
  --variant 'OpexAI[decision_log=1,v233_pending_continue=1,v233_goods_graft=5]' \
  --variant-policy-id v233chain_mode5 --script-debug \
  --years 10 --repeats 1 --seeds 42 100 7 999 2026 1 17 73 314 512 \
  --decision-rule gain_short --required-seeds 40 --required-years 10 \
  --primary-metric profit_year --min-useful-primary-delta-pct 4 \
  --value-guard-max-loss-pct 5 --cpus 3 --memory 2g --max-workers 3
```

Verdict d'adoption `diagnostic_only` attendu avec dix graines. Relier par
usine et ligne : candidatures → apports GRAI **et** LVST (éventuellement rame
mixte) → production mensuelle → biens → première livraison → réalisé.
Rapporter chaînes complètes par graine, délais entre étapes, distributions
de distances et de wagons, y compris seconds cargos, charge/attente et coût
total prévu/réel. Vérifier qu'il ne s'agit pas seulement de nouvelles greffes
sur des usines alimentées par d'autres. Comparer aussi AIR et dates des
investissements Opex/AAA, erreurs, cash et refus. En cas d'absence de chaînes
complètes ou de collecte ambiguë : diagnostiquer, ne pas passer à la porte A
en prétendant l'exposition acquise. Aucun verdict économique tiré du 10×10.

**2. Porte A PC : 40 graines canoniques × 10 ans, 80 duels**, sans sonde :

```bash
python3 sweeps/run_c66_reference.py \
  --campaign v233chain_porteA_40x10_20261018 \
  --reference 'OpexAI[v233_pending_continue=0,v233_goods_graft=0]' \
  --variant 'OpexAI[v233_pending_continue=1,v233_goods_graft=5]' \
  --variant-policy-id v233chain_mode5 --years 10 --repeats 1 \
  --decision-rule gain_short --required-seeds 40 --required-years 10 \
  --primary-metric profit_year --min-useful-primary-delta-pct 4 \
  --value-guard-max-loss-pct 5 --cpus 10 --memory 8g --max-workers 10
```

Horizon dix ans fixé ici avant toute mesure du mode 5. Exiger 40/40 paires
saines et complètes, quatre trimestres valides en année terminale, les trois
indicateurs de complétude vrais, règle attendue et verdict `pass` : Wilcoxon
exact bilatéral p<0,05, borne basse IC95 bootstrap >0, delta moyen Opex variante
− référence ≥4 % du profit moyen de référence, garde de valeur −5 % par ratio
des moyennes. Bootstrap : 20 000 tirages, graine 0. Un échec arrête la
séquence ; aucune recherche d'un horizon plus favorable. La porte B 20×10
`non_erosion` restera nécessaire avant une éventuelle adoption demandée.

FIN
