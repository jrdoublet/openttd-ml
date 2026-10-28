# ROAD100 — production de bus en route seule, preregistration (27/10/2026)

## Objectif et reference

Demande utilisateur : atteindre le profit annuel d'AAAHogEx en **ROAD seul**
apres **1, 2, 3, 4 et 5 ans**, en traitant chaque horizon dans cet ordre. Les
ratios sont ceux des **moyennes des profits annuels**, entre parties appariées
sur la meme graine, les memes modes des deux IA, carte 256², départ 1970.

Reference descriptive figee : `road100_baseline_40x5_20261027`, 40/40 duels
complets, sans erreur moteur/Squirrel, bundle
`8d40648d610ecca1abb31f419749b64228d95e7e0adc0483aa942f3ff438dbd1`.
Bras OpexAI : `mode_air=0,mode_rail=0,mode_road=1,mode_water=0,estim_unifie=31`.
Bras AAAHogEx : `disable_veh_train=1`, `disable_veh_tram=1`,
`disable_veh_ship=1`, `disable_veh_aircraft=1`. Sondes `67247874`
symetriques entre replays Opex (elles peuvent modifier les dates en jeu).

| Horizon | Profit Opex £/an | Profit AAA £/an | Ratio | Victoires Opex |
|--:|--:|--:|--:|--:|
| 1 | 8 095 | 134 498 | 6,0 % | 0/40 |
| 2 | 26 907 | 555 822 | 4,8 % | 0/40 |
| 3 | 28 913 | 1 108 485 | 2,6 % | 0/40 |
| 4 | 29 110 | 1 704 870 | 1,7 % | 0/40 |
| 5 | 29 753 | 2 161 407 | 1,4 % | 0/40 |

L'IA dispose de 258 k£ moyens a un an, mais ne possede que six vehicules
contre 53 chez AAAHogEx. `OpexBuildRoadCandidates` ne genere plus de candidats
`kind=pax` depuis V231. Le choix utilisateur du 17/10 a retire les anciens bus
interurbains apres pertes en multimodal (cannibalisation AIR, −60 k£/an sur
l'ancien test) : **la variante presente se limite strictement a ROAD seul**.

## Hypothese isolee et garde-fous

`road100_solo_pax=0` par defaut aux quatre difficultes. La valeur `1` ajoute
des projets de bus ville↔ville au vivier ROAD **seulement lorsque ROAD est le
seul mode effectif**. Le fret historique, les autres modes et toutes les
politiques d'investissement restent inchanges. Le controle au depart et au
chantier continue de refuser les villes PAX deja desservies afin de ne pas
multiplier la demande comptee. Chaque candidat conserve le calcul courant
`OpexRoadLineEconomics`, la rentabilite positive, le capital, la selection et
la revalidation du portefeuille commun. La quantite de voyageurs estimee par
arret respecte un budget de captage de maisons, avant de connaitre le site.

L'exposition attendue : des `ROAD100_PAX_GEN` avec `positive>0` en 1970,
suivis de `ROAD_BUILD cargo=PASS` plus frequents, puis hausse du profit annuel
reel par rapport a la reference. Une augmentation du nombre de bus sans profit
ne constitue pas un succes. La comparaison doit conserver le nombre de
stations et de vehicules, la caisse et les erreurs de construction.

## Protocole fixe avant la variante

1. Contrats de configuration et de non-exposition multimodale, puis smoke
   1 graine × 1 an `42`, reference `0` / variante `1`, meme bundle.
2. Si smoke sain et exposé, diagnostic 5 graines × 1 an `42,100,7,999,2026`
   pour inspecter les lignes PAX, finances et estime/reel. Pas de preuve
   economique a cinq graines, ni de seuil adapte apres observation.
3. Si l'economie et la sante justifient de poursuivre, mesurer **les cinq
   horizons** sur 40 graines × 5 ans, une repetition, parite `>=100 %` a chaque
   annee distinctement. Aucun agregat de 1 a 5 ans ne masque une annee perdante.
4. L'adoption par defaut exige separement V102 : A40×3 `gain_short` +4 %,
   Wilcoxon p<0,05, IC95 bas >0, valeur ≥−5 %, puis B20×10 `non_erosion`
   avec autorisation de la porte B et la garde de valeur. La parite AAA n'est
   pas une porte d'adoption en elle-meme. Une nouvelle variante ou un
   ajustement de parametre imposerait une nouvelle campagne et une nouvelle
   specification ; aucun rerun selectif des graines perdantes.

La référence instrumentée garde `estim_unifie=31` pour comparer le chantier
avec le diagnostic du 27/10. La parite du **défaut livré** devra etre
re-mesuree si ESTIM n'est pas adopte au meme réglage. Aucun commit, push ou
changement de défaut autorise au titre du présent essai.
