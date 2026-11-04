# Leviers route seule déjà testés (notes de travail, 02-04/11/2026)

## road1y_astar_porte_a

02/11/2026, diagnostic (3 graines, probes=258) : les candidats bus-quartier de 96 à 192 tuiles sont les plus nombreux (≈600-800/graine) et les mieux estimés (profit médian 6-10 k£), mais 0 n'est construit au-delà de 128 : tous meurent en `plan_failed:TRACEX`. OpexRoadPlanPaxVoirie ne connaît que le BFS sur voirie existante et le L ; pas d'A* routier.
Les candidats bus-quartier (`road1yBusSite`) n'ont PAS `road100SiteFirst` : une garde sur siteFirst rend tout levier inerte (piège du 1er smoke).
`road1y_astar` (branche road1y-astar, wt-astar, 6bc9e42b, `road1y_astar.nut`) : A* sans AITestMode par voisin, validation du tracé complet, bannissement + 3 relances, budget = N×1000 nœuds, à la construction seulement.
Porte A 40×3 `astar=4` vs master : +59,2 k£/an, médiane +54,7 k, 32/8, p=4e-6, IC95 [38 k ; 82 k], valeur +39 %. Smoke astar=16 : plus de lignes longues mais pas plus de profit (3 graines).
Porte B 20×10 PASSE : +58,9 k£/an, médiane +35,8 k, 12/8, p=0,03, IC95 [18,6 k ; 103,8 k], valeur +22 %. QUALIFIÉ ; 02/11 matin : défaut 4, fusionné en local sur master 3c863206 (validé par l’utilisateur), poussé. Tests recalés par grok (8ee22abf).
02/11 : astar=8 vs 4 porte A ÉCHEC −15,0 k, 12/28, valeur −7,3 % ⇒ budget plus large nuisible ; astar=2 vs 4 en mesure.
02/11 : astar=2 vs 4 porte A fail_primary +14,3 k, 23/17, p=0,094, valeur +6 % (tendance : petit budget mieux).
02/11 : astar=1 vs 4 ÉCHEC −26,5 k, 12/28, p=0,006 ⇒ optimum 2-4, garder 4.

## road1y_bridge
03/11/2026, agy (wt-bridge, f8023aec sur e728be6a). Mesure préalable : 58 ROAD1Y_ASTAR ok=0 sur 108 (BUDGET 43, NO_PATH 14 tous avec eau).
Smoke 3 graines × 3 ans : +47 k£/an, 36 ponts, ok=0 58 → 27. Porte A 40×3 vs master : +0,4 k£/an, médiane +5,1 k, 22/18, p=0,90, IC95 [−21 k ; +22 k], valeur +0,4 % ⇒ fail_primary.
Leçon : débloquer des tracés ne paie pas ; le smoke 3 graines duel (+15 %) était du bruit ([[duel-non-deterministe]]). Ne pas raffiner sans autre preuve.

## road1y_bus_quartiers_qualifie

Branche `road1y-s17` (35224c42, poussée) : `road1y_pax_sites=1,road1y_extra_stops=2` par défaut, contre étape A (bus entre villes seuls).
Porte A 40×3 : +59,8 k£/an, 37/3, p=2,4e-8. Porte B 20×10 : +87,8 k£/an, 20/0, IC95 [62,7 ; 114,4] k, valeur +33 %.
Mais à 10 ans Opex = 8 % du profit d'AAA (211 k vs 2,71 M ; 106 vs 491 véhicules). Graine 17 régresse (61 → 20 k) sans cause trouvée ; correctifs a/c (road1y_bus_fixes) et repli baie réfutés.
**Why:** étape A (`road100_solo_pax=1`, filtre 42 levé) = +72 % à 1 an ; AAA route seule = 100 % bus entre villes.
**How to apply:** prochain levier = croissance après l'an 1 (AAA ×4,6 en véhicules), pas la graine 17. Voir [[ecart-10ans-croissance-lignes]].

**29/10 suite (3 ans, road1y-s17)** : `road1y_fleet_unlock` (e32fac22) NÉGATIF (bit 4 −20 %, bits 1/2 inertes, somme d'arrêts au lieu du min = bug) ; `road1y_long_band=2` (9f6c5f4b) porte A 40×3 **fail_primary** (−2,0 k£/an, 19/21, p=0,84). Moyenne 40 graines : Opex 216 k vs AAA 941 k (23 %), 80 vs 247 véhicules. Écart = courrier (AAA ~300 k£/an) + rendement par bus, pas la borne de distance ni le nombre de bus par ligne.

## road1y_defauts_0311
Décision utilisateur 03/11 (« Oui et oui ») : défauts route seule road1y_gap=12, road1y_weak=15, road1y_mail2=5 + road1y_mail2_years=3 (qualifiés), et road1y_next=64, road1y_next3=56 malgré l'échec de la garde de valeur 5 % en porte B (profit +80 k / +37 k, valeur −8,8 % / −9,3 %).
**Why:** la valeur n'est pas un objectif (cf. [[objectif-rattraper-aaahogex]]) ; l'objectif est 100 % du profit d'AAA à 3 ans en route seule.
**How to apply:** branche road1y-defaults (commit e728be6a = fusion mail2y + next3 + défauts dans info.nut, fixture et tests), A/A local avant fusion master. Tous forcés à 0 hors route seule.
Rejetés de la nuit : mail_full, next2, retry, freight (plafond camions et ×2 profit), weak 8/25, gap 6/24, next 48/80/96, next3 28/80, mail2=2.

## road1y_ecart_pax_0311

03/11/2026, agy, n_spread2_gateA (40 graines, an 3). Rapport : jobs/e230de46/tmp/agy_paxgap_rapport.md.
- Opex 527 k, AAA 716 k : écart −188 k£/an. Répartition : bus PAX −94 k, courrier −51 k, camions fret −45 k (AAA a 3 lignes de fret et 45 camions, nous presque rien).
- Bus : 100 chez nous contre 86, à 3,8 k£/bus contre 5,5 k ; 9 % de nos bus ont un profit ≤ 0.
- Sur les 48 paires communes, profit par ligne identique (39,4 k contre 39,7 k), mais 8,75 bus chez nous contre 6,8. Le captage est résolu par spread_stops.
- Les paires d'AAA sont 10 tuiles plus longues, avec des villes de même taille. Aucun réseau en étoile, ni chez l'un ni chez l'autre.
- Rythme d'ouverture : Opex a jusqu'à 9 mois d'avance en 1970-71. En 1972, la caisse oisive monte à 157 k£ alors qu'AAA reste à 15-20 k£ ⇒ diagnostic de la caisse 1972 confié à agy (cash72).
- Le rapport affirmait « next=0 dans ce banc » : FAUX, la base e728be6a avait déjà next=64 par défaut.
- Spécification 2 (renfort sur min(attente A, B)×2, comme AAA) confiée à agy : road1y_pax_bilat, branche road1y-paxbilat.
- Caisse 1972 (agy cash72, rapport jobs/e230de46/tmp/agy_cash72_rapport.md) : ce n'est pas un blocage. Les graines riches en caisse (> 300 k£, n=8) sont celles qui font le plus de profit (619 k contre 410 k). Au-dessus de 50 k£, les refus viennent de SITE_LOST (paire bannie 365 j), du plafond de 4 lignes par ville, et de insufficient_cash au sein d'une même passe. Une ligne ouverte au 4e trimestre ne rapporte rien en 1972.
- Seule piste chiffrée : LOAN_REPAY_FLOOR 300 k → 50 k (globals_post.nut:17), pour ≤ 12 k£/an d'intérêts économisés. C'est sous le seuil de 4 % de la porte A : non lancée.
- road1y_pax_bilat (agy, 00e64762, branche road1y-paxbilat) : smoke +0,8 k (−71/+59/+15), −7,7 bus/graine. Porte A lancée le 03/11 contre load_orders+spread2.
- road1y_pax_bilat porte A 40×3 (03/11) : +9,7 k£/an, médiane +4,2 k, 20/20, p=0,55, IC95 [−9,5 ; 29,6 k], valeur −1,1 % ⇒ fail_primary, défaut 0.

## road1y_far
03/11/2026, agy (wt-far, 988fea38 sur e728be6a). Mesure : paires >128 bien générées (1 300-1 900/graine) ; pertes = found<12 par ville, classement ROI (médian 340-424 vs 465-532 sous 128), 70 % de tracés en échec.
Smoke 3 graines +12 k (porté par 781335 seule). Porte A 40×3 vs master : +8,8 k£/an, médiane +8,2 k, 25/15, p=0,23, IC95 [−7,2 ; +24,7 k], valeur +2,2 % ⇒ fail_primary. p hors fenêtre 0,07-0,15 : pas de rebanc.
Avec [[road1y-bridge]] : élargir l'accès aux lignes longues ne paie pas sous les défauts actuels.

## road1y_flotte_portes_a_0211

02/11/2026, portes A 40×3 route seule contre master 3c863206 (astar=4) :
- `road1y_mail_next=7` (agy, wt-mailnext dc72a253) : +6,4 k£/an, 21/18/1, p=0,50 ⇒ 0.
- `road1y_berth_fleet=3` (grok, wt-berth d525c1f4, arrêt sans réserve 50 k + renfort AAA) : +11,5 k, 21/19, p=0,11, IC95 [−2,7 ; 25,7] ⇒ 0 (tendance).
- `road1y_rich_fleet=10` (agy, wt-richfleet 0a16d948, renfort si caisse >100 k) : −9,8 k, 14/26, p=0,07 ⇒ 0.
Confirme [[road1y-astar-porte-a]] : empiler des bus PAX ne paie pas. Suite : `road1y_gap` (grok, wt-gap 325ee6d0) = plafond fourgons MAIL 2→N (écart MAIL ~190 k£ : AAA 53-92 fourgons, nous 2-9).

**Why:** éviter de rebancer ces leviers.
**How to apply:** ne plus proposer de renfort PAX ; le gisement est le MAIL.
02/11 nuit, répliques GitHub sur 40 graines disjointes (seeds_b40, LCG 20261102) agrégées à 80 paires :
- berth_fleet=3 : +8,9 k (2,8 %), 42/38, p=0,10, IC95 [−1,7 ; 19,2] ⇒ rejeté.
- astar=2 vs 4 : +12,0 k (3,8 %), 49/31, p=0,041 mais IC95 [−1,0 ; 24,7] et <4 % ⇒ garder 4.
Cumul gap=12+weak=15 (branche road1y-gapweak 648e4fc6) porte A GitHub run 41536324545.

## road1y_gap_mail_cap

02/11/2026, grok (wt-gap, branche road1y-gap, 325ee6d0 sur master 3c863206). Diagnostic : écart MAIL ≈190 k£ à 3 ans (AAA 53-92 fourgons sur 9-12 lignes, nous 2-9) ; plafond `mailCap = 2*stops` (bus_districts.nut:500) et parent unique bloqué en NO_SITE_A.
`road1y_gap=N` : plafond N fourgons/ligne MAIL, ≤2 ajouts/mois, essaie jusqu'à 4 parents en sautant ceux sans site.
Porte A 40×3 vs master : +16,4 k£/an, médiane +10,7 k, 28/12, p=0,012, IC95 [2,0 ; 30,5], valeur +5,5 %. PASSE. Porte B 20×10 en file (chainD). Défaut 0 en attendant l'utilisateur.
Suite prévue : vrai réseau MAIL autonome à la AAA (spécification grok_aaamail_rapport.md, code codex). Voir [[road1y-flotte-portes-a-0211]].
02/11 nuit : `road1y_mail_net=12` (grok fb959178 + mon correctif 396c95d3 originA/B + repli A*, wt-mailnet) smoke NÉGATIF 138/317/189 vs master 177/364/322 : 7 ouvertures, 23 NO_TRACE, et N>0 coupe les filles mail_on_pax. Pas de porte A. Piste : le faire coexister avec les filles et tracer comme les bus (site→site).
02/11 23:15 : porte B 20×10 PASSE largement : +201,1 k£/an, médiane +192,3 k, 20/0, p=1,9e-6, IC95 [168,6 ; 237,2], valeur +50,5 % (VPS, campagne road1y_gap12_gateB_20x10). QUALIFIÉ ; défaut 0 jusqu'au point du matin.
Cumul gap=12+weak=15 (road1y-gapweak 648e4fc6) porte A GitHub 41536324545 PASSE : +23,2 k (7,5 %), 29/11, p=0,0037, IC95 [9,2 ; 37,0], valeur +12,4 % ; porte B VPS en file.
mail_net v2 (grok 35332753, filles conservées + tracé bus) smoke GitHub 41538472644 : 166/292/233 vs 177/364/322, 16 ouvertures ⇒ toujours négatif, abandonné pour la nuit.
03/11 : gap=24 vs 12 porte A GitHub 41539368150 : −0,2 k, 0/3 (37 ex æquo) ⇒ au-delà de 12 inerte (plafond 2 ajouts/mois lie) ; garder 12.
03/11 : gap=6 vs 12 porte A GitHub 41542170471 : +2,4 k, 11/9 (20 ex æquo), p=0,73 ⇒ neutre ; plateau 6-24, garder 12.
03/11 : porte B cumul gap12+weak15 (VPS road1y_gapweak_gateB_20x10, 648e4fc6) PASSE : +430,5 k£/an, médiane +444 k, 20/0, p=1,9e-6, IC95 [372 ; 491 k], valeur +94,5 % ⇒ cumul QUALIFIÉ ; décision défaut au point du matin.
03/11 road1y_mail_full (agy ca83c0a7, chargement complet fourgons MAIL fils) porte A : =3 −4,5 k 19/20 ; =1 −8,2 k 16/23 ⇒ ÉCHEC, le chargement complet ne débloque pas le MAIL.

## road1y_load_orders
03/11/2026 : diagnostic agy (busyield_e728, 3 graines) : mêmes bus qu'AAA ; AAA pose OF_FULL_LOAD_ANY à la source PAX (route.nut:2137), nous OF_NONE. `road1y_load_orders` (546f41bc, 28/10, défaut 0) n'avait jamais été mesuré.
Porte A 40×3 vs master e728be6a : +49,0 k£/an, médiane +62,3 k, 34/6, p=8,7e-7, IC95 [33,9 k ; 63,3 k], valeur +7,6 %. Meilleure graine 89 % d'AAA (313707). Moyenne Opex 407 k vs AAA 869 k.
Contraste : le chargement complet a échoué en avion (−37 à −54 %) et sur les fourgons MAIL (road1y_mail_full, [[road1y-gap-mail-cap]]).
Porte B 20×10 : en attente d'accord utilisateur.
03/11 soir : rich_fleet=10 sur load_orders=1 (wt-richfleet2 48e27039) porte A vs load_orders=1 seul : −1,3 k, 20/20, p=0,87 ⇒ neutre ; ajouter des bus ne paie toujours pas, même sous chargement complet.
03/11 20:30 : porte B 20×10 (VPS road1y_loadord_gateB_20x10, master e728be6a) PASSE : +281,9 k£/an, médiane +333,3 k, 18/2, p=1,9e-5, IC95 [201,6 ; 361,7 k], valeur +10,0 % ⇒ QUALIFIÉ. Défaut 0 jusqu'au point du matin (décision utilisateur).
03/11 : road1y_dest_full=1 (chargement complet AUSSI à destination, comme AAA ; agy wt-destfull 537c3d44) smoke 3 graines vs bras loadord : −29 k£/an, 3/3 négatives ⇒ pas de porte A ; source seule = optimum.
04/11 : défaut 1 (route seule) sur master 558f5bd8, poussé, validé par l'utilisateur.

## road1y_mail2_reserve
Diagnostic grok (e881ac3e, branche road1y-mail2) : OpexRoad1yMailStep et OpexRoad1yRefleetMailLine (bus_districts.nut:508/739) sortent en silence sous ~30 k£ de caisse ; en 1971-72 presque tous les appels sont sous ce seuil ⇒ 2-5 lignes MAIL contre 10-13 chez AAA.
Porte A GitHub vs gap12+weak15+next64 : mail2=5 (41556631607) +30,8 k (8,6 %), 29/10, p=1e-4, IC95 [17,9 ; 43,5 k], valeur +27 % ; mail2=10 (41556634317) +21,1 k, 28/11, p=0,01, valeur +20 %.
Porte B VPS mail2=5 (road1y_mail2_5_gateB_20x10) lancée ; GitHub mail2=2 vs 5 et mail2=5 sans next vs gapweak lancés.
03/11 mail2=2 vs 5 : −10,0 k, 13/26, p=0,056 ⇒ garder 5. Piège GitHub : un seul run EN ATTENTE par ref (concurrency), un 3e lancé sur la même branche annule le précédent en file.
03/11 porte B mail2=5 (VPS, réf gap12+weak15+next64) : verdict pass (non-érosion) MAIS Δ −49,9 k£/an, médiane −71,6 k, 8/12, p=0,35, IC95 [−135 ; +34,5 k], valeur −1,6 % ⇒ qualifié au protocole, tendance négative à 10 ans : à signaler.
03/11 mail2=5 SANS next vs gap12+weak15 porte A GitHub 41562315138 PASSE : +23,8 k (7,3 %), 26/14, p=0,0047, IC95 [8,3 ; 39,0 k], valeur +23,5 %. Porte B VPS en file après nextmail.
03/11 porte B next64+mail2=5 vs gap12+weak15 (VPS road1y_next64mail5_gateB_20x10) : pass (non-érosion) +41,7 k, médiane +18 k, 10/10, p=0,70, IC95 [−82 ; +165 k], valeur −4,6 % (sous la garde 5 %).
03/11 porte B mail2=5 SEUL vs gap12+weak15 (VPS road1y_mail5only_gateB_20x10) : ÉCHEC −89,5 k£/an, médiane −67 k, 7/13, p=0,048, IC95 [−165 ; −20,5 k], valeur −6,5 % ⇒ gain à 3 ans, perte à 10 ans ; piste : limiter mail2 aux premières années.
03/11 road1y_freight (agy 28b62b3a, plafond camions de l'estimation fret) porte A : =12 et =20 IDENTIQUES +5,9 k 20/20 ; capacité charbon variante 360 vs réf 1220 ⇒ le plafond ne lie pas, le fret reste non construit pour une autre raison. Smoke instrumenté lancé pour diagnostic agy.
03/11 porte B mail2=5 + mail2_years=3 (agy 6e1a8b2f, VPS road1y_mail2y3_gateB_20x10) vs gap12+weak15 : PASSE (non-érosion) +1,6 k, médiane +23,6 k, 11/9, p=0,87, IC95 [−58 ; +64 k], valeur −1,8 %. Porte A = celle de mail2=5 seul (identique à 3 ans, +23,8 k, p=0,0047) ⇒ QUALIFIÉ ; décision défaut au point du matin.
03/11 agy af087da9 : vraie cause fret = troncature PROJECT_TOP_K=64 remplie de bus ; correctif ×2 profit fret sous road1y_freight ; estimation 640 £/camion vs AAA réel ~2 000 £. Porte A relancée.
03/11 road1y_freight v2 (af087da9, ×2 profit fret) porte A 41581614765 : +5,4 k, 17/23, p=0,91 ⇒ NEUTRE ; capacité charbon 1220→4240 (AAA 573 200) : du fret est posé mais ne paie pas plus que les bus évincés. Rejeté.

## road1y_mail_gisement

03/11/2026, agy, diagnostic de n_spread2_gateA (40 graines, an 3, route seule). Rapport : `$T/agy_mailgap_rapport.md` du job e230de46.
- Courrier par graine : Opex a 84 fourgons pour 151 k£, AAA 66 fourgons pour 213 k£. Rendement 1,8 k£ contre 3,2 k£ par fourgon. Attente médiane 4 sacs contre 17. Note de gare 56 % contre 66 %. AAA livre 65 % de courrier en plus.
- 78 % des lignes courrier d'AAA desservent des paires sans bus AAA. Chez Opex, 0 % : chaque ligne courrier est une fille d'une ligne bus.
- road1y_mail_net (grok, branche road1y-mailnet) RÉFUTÉ. La voirie dédiée coûte 15-25 k£ et se rembourse en 6-8 ans ; elle prend la trésorerie des bus (graine 781335 : bus −147 k£, courrier +53 k£). S'y ajoutent le chargement complet aux deux bouts et un renfort trop lent.
- Verdict : pas de gisement autonome à 3 ans. Seul levier encore ouvert : le captage sur les gares existantes (road1y_spread_mail, [[road1y-spread-stops]]).
- Piste non testée : choisir les parents des filles courrier selon la production de courrier de la ville, pas seulement selon le profit des bus (AAA filtre à prod ≥ 27 sacs/mois).
- road1y_spread_mail=2 (agy, 9bfc0bda, branche road1y-spreadmail, réf load_orders=1+spread_stops=2) : smoke +4,7 k (25 arrêts), porte A 40×3 NEUTRE 03/11 : −0,0 k£/an, médiane −2,4 k, 19/21, p=0,93, valeur −1,8 % ⇒ fail_primary, défaut 0. Le captage joint ne paie pas sur le courrier.
- road1y_mail_pick=20 (agy, 760ba36e, branche road1y-mailpick) : smoke 03/11 −27,0 k£/an, 0/3 (−4, −63, −14 k) ; moins de fourgons mais moins de profit courrier ⇒ REJETÉ, défaut 0. Fil courrier route à 3 ans CLOS.

## road1y_mail_min
03/11/2026, agy (wt-mailmin, 989a2fa6 sur e728be6a), sur load_orders=1. Smoke 3 graines vs variante n_loadord_gateA : 323→268, 435→367, 533→521 k£/an (moyenne −45 k). Fourgons 94→46/graine, £/fourgon 1 424→1 894.
Leçon : un fourgon à 1,4 k£/an reste rentable ; maximiser le £/véhicule réduit le profit total. Ne pas juger un levier sur le rendement par véhicule (piège du diagnostic agy_gap40).

## road1y_mail_on_pax_qualifie

31/10/2026, branche `road1y-mail` code `a5577e3d` (route seule, estim_unifie=31) :
- porte A 40×3 : +39,7 k£/an, 34/6, p=2e-5 ;
- porte B 20×10 : +105,1 k£/an, 19/1, p=3,8e-6, IC95 [74,5 k ; 137,1 k] ;
- défaut toujours 0 : adoption/fusion = décision utilisateur.
Fusion avec master 481e7c08 prête en local : `road1y-mail-rebased` (wt-road1y-rb, ec1f660f), jamais jouée.
Suite : `road1y_mail_v2` (agy, af3b4749, wt-mail2) = sites vérifiés, 2 fourgons au départ, plafond 6-8/arrêt, réserve 10 k.
Contre : `road1y_bus_yield` porte A fail_primary (+10,7 k, p=0,089). Voir [[road1y-bus-quartiers-qualifie]].
01/11 : `road1y_mail_v2` porte A fail_primary (+17,1 k, 23/17, p=0,068) ⇒ 0.
01/11 : `road1y_long_v3` (grok, e7840fc9, wt-long3 ; tracé 192 sans réordonner les bandes fret — long_band=2 tuait le fret 64-95 par le `break` de bande candidates.nut:3739) porte A vs mail_on_pax=1 PASSE : +15,2 k, médiane +20,0 k, 29/11, p=0,017. Porte B non lancée (accord requis).
01/11 : long_v3 porte B 20×10 PASSE (non_erosion) : +27,4 k, 12/8, p=0,22, IC95 [−7,6 k ; +62,8 k]. long_fleet (agy e73c54b3, wt-longfleet) en mesure.
01/11 : long_fleet porte A NÉGATIVE : −27,8 k, 6/26/8, p=1e-5, valeur −7,3 % ⇒ 0 ; flotte initiale >4 sur lignes longues = même échec que les renforts (caisse).
01/11 : FUSIONNÉ sur master 86296771 et poussé (accord utilisateur « si tu penses… fais le ») : mail_on_pax=1 et long_v3=1 par défaut, tous ROAD1Y_* gardés route seule (multimodal identique à master à la livre, 1 an 3 graines). Piège : ma résolution de conflit info.nut avait perdu un `AddSetting({` ⇒ OpexAI ne compilait plus, AAA jouait seul ; les tests sources ne compilent pas le Squirrel — toujours un smoke en jeu après un merge.

## road1y_next_plancher_pax
Diagnostic grok 03/11 (smoke cumul gap12+weak15, GitHub 41541014735) : écart moyen ~393 k£, PAX ~227 k, MAIL ~169 k, fret ~28 k.
Volume PAX livré proche d'AAA, mais 16 £/pax chez nous contre 26-35 £ : nos lignes 0-44 tuiles = 1,4 k£/bus ; AAA 96+ = 6,2 k£/bus, 75 % de son PAX.
Le vivier 96-192 existe (700-1100 candidats) mais perd au fundScore = profit*1000/cost.
Levier `road1y_next` (bus_districts_overrides.nut:376, ignore les paires < N), défaut 0. Portes A GitHub next=96 (41545104156) et next=64 (41545124222) lancées vs cumul.
MAIL : filles OF_NONE ⇒ attente faible ⇒ refleet bloqué (bus_districts.nut:505) ; AAA charge à plein aux deux bouts (road.nut:250).
03/11 porte A next=96 ÉCHEC : −19,1 k, 17/23, valeur −27 %. next=64 PASSE : +39,2 k (12,1 %), 29/11, p=8e-4, IC95 [20,1 ; 58,5 k], valeur −0,8 %.
Porte B next=64 lancée VPS (road1y_next64_gateB_20x10, wt-next) ; GitHub next=48 (41547792511) et 80 (41547795972) vs 64.
03/11 vs next=64 : next=48 −1,6 k 16/24 p=0,60 (valeur +4,9 %) ; next=80 −14,3 k 16/24 valeur −5,8 % ⇒ garder 64 (plateau 48-64).
03/11 porte B next=64 (VPS road1y_next64_gateB_20x10, db131bc9) : profit +80,3 k£/an, médiane +88 k, 14/6, p=0,09, IC95 [−20 ; 179 k] MAIS valeur −8,8 % ⇒ fail_value_guard ; à signaler à l'utilisateur (garde de valeur en tension, cf. objectif_rattraper_aaahogex).
03/11 road1y_next2 (grok a67f0f7f, bonus fundScore ×distance/N pour PAX >N) porte A : =64 −303 k, =96 −295 k, 0/40 ; pas de plantage mais ~31 véhicules et 263 k£ oisifs en 1972 ⇒ les longs choisis échouent (TRACEX) et bloquent le créneau. ABANDONNÉ.
03/11 road1y_next3 (grok 9191d955, crédit de N tuiles de voirie aux PAX 96-127) porte A vs gap+weak+next64+mail2=5 : =56 PASSE +30,2 k (8 %), 28/12, p=0,010, IC95 [7,0 ; 52,8 k], valeur −4,3 % ; =28 neutre +5,7 k 20/20.
03/11 road1y_retry (grok 7cacb7ed, réessais dans le même créneau après échec PAX) porte A : =2 −0,0 k 18/20 ; =4 +3,9 k 18/21 ⇒ NEUTRE, rejeté. next3=80 vs 56 : −27,2 k, 15/25, p=0,028 ⇒ garder 56.
03/11 porte B next3=56 (VPS, réf gap+weak+next64+mail2=5) : fail_value_guard ; profit +36,8 k, médiane +9 k, 11/9, p=0,67, IC95 [−39 ; 119 k], valeur −9,3 %.

## road1y_site_relocate_rejete
02/11/2026, branche road1y-site-lost (wt-sitelost, 52a7e0ec, agy) : quand le site d'arrêt bus-quartier est perdu à la construction (SITE_LOST, ~35-50 sur 3 graines × 3 ans), chercher un site ≤ 6 tuiles dans le même quartier. Smoke : 14 relocalisations réussies sur 67, +18,9 k en moyenne (bruit).
Porte A 40×3 vs master 3c863206 : −4,2 k£/an, médiane −9,1 k, 14/26, p=0,29 ⇒ fail_primary, défaut 0. Ne pas raffiner : les paires perdues ne sont pas un gisement.
Diagnostic flotte de grok (02/11) : `/home/deploy/.claude/jobs/e230de46/tmp/grok_flotte_diag_rapport.md` ; leviers berth_fleet (grok) et mail_next (agy) en cours. Voir [[road1y-astar-porte-a]].

## road1y_spread_stops
03/11/2026, diagnostic agy (agy_lineyield_rapport.md, porte A n_loadord_gateA 40 graines) : à paire de villes identique, AAA fait 37-54 k£/ligne contre 18-22 k£ ; attente 164-174 pax contre 51-98 ; note 65-67 % contre 48-59 %. Pas le choix des villes.
AAA : station.nut:2172 BuildSpreadPieceStations à l'ouverture (route.nut:1393, :4060) puis tous les 5 ans : arrêts joints sur toute route à ≤12 tuiles, espacés de 5, triés par acceptance. Nous : 1 arrêt ; ROAD1Y_EXTRA_STOPS ne cherche qu'en adjacent (NO_SITE).
Codex (plugin, nuit du 03/11) : branche road1y-lineyield (wt-lineyield), réglage road1y_spread_stops 0..4, ouverture + rattrapage mensuel, nStopsA/B mis à jour pour le plafond de flotte. Mission : jobs/e230de46/tmp/codex_lineyield.md. Smoke puis porte A à faire.
Correctif Claude c41cbe91 : réserve 50 k→5 k et reprise mensuelle des lignes refusées pour caisse (sinon marquées faites ⇒ inertes 5 ans).
Smoke 3 graines (load_orders=1 + spread=2) : 474/555/373 vs 435/533/323, 114 arrêts posés, 0 noai_error.
Porte A 40×3 (wt-lineyield c41cbe91, réf load_orders=1) PASSE : +69,5 k£/an, médiane +58,3 k, 33/7, p=1,1e-4, IC95 [36,2 ; 101,6 k], valeur +17,0 %. Porte B 20×10 PASSE (non_erosion, 03/11) : +20,3 k£/an, médiane −9,5 k, 9/11, p=0,90, IC95 [−50,9 ; 98,6 k], valeur +3,9 %. QUALIFIÉ ; 04/11 défaut 2 (route seule) sur master 558f5bd8, poussé, validé par l’utilisateur.

## road1y_weak_realloc

02/11/2026, agy (wt-weak, branche road1y-weak, 5363f2ab sur master 3c863206). 31 % de nos lignes PAX font <1,5 k£/bus (courtes 21-34 tuiles, petites villes, attente ≈0) ; les fortes (60-94 tuiles) saturent à 4 bus.
`road1y_weak=N` : seuil N×100 £/bus ; un mois envoi au dépôt d'un bus d'une ligne faible (garder ≥2, attente ≤20), le mois suivant vente + clone sur la ligne forte la plus en attente (<8 bus). Smoke : 103 transferts.
Porte A 40×3 vs master : +22,6 k£/an, médiane +19,7 k, 27/13, p=0,0098, IC95 [8,6 ; 36,7], valeur +9,3 %. PASSE. Porte B en file (chainF). Défaut 0 jusqu'à l'utilisateur.
Voir [[road1y-gap-mail-cap]] (passé aussi, cumul à mesurer).
02/11 23:50 : porte B 20×10 PASSE : +210,5 k£/an, médiane +208,4 k, 18/2, p=1,3e-5, IC95 [148,8 ; 270,6], valeur +45,6 % (VPS road1y_weak15_gateB_20x10). QUALIFIÉ ; défaut 0 jusqu'au point du matin. Porte B du cumul gap+weak en cours (VPS).
03/11 : weak=25 vs 15 porte A GitHub 41541010810 : −11,2 k (−3,4 %), 14/24, p=0,043 ⇒ seuil plus haut nuisible ; weak=8 vs 15 lancé.
03/11 : weak=8 vs 15 porte A GitHub 41543293632 : −6,6 k, 17/22, p=0,28, valeur −5,5 % ⇒ échec ; optimum ≈15, garder 15.

## objectif_rattraper_aaahogex

Objectif du projet (utilisateur, 2026-09-29) : **rattraper AAAHogEx**. La `company_value` n'est pas
un objectif et le `profit_year` d'OpexAI n'est qu'un moyen parmi d'autres.

**Why:** des variantes (C121 soft25 : écart avec AAA +342 k£/an ; defeff : +579 k£/an) ont été
rejetées sur la garde de valeur −5 % ou le profit OpexAI, donc sur des critères que l'utilisateur ne
considère pas comme l'objectif.

**How to apply:** avant de juger une variante, demander ou fixer la métrique « rattrapage » (écart
avec AAA, créneaux/villes, monopoles AAA 2-0…) ; ne pas rejeter sur la seule valeur. AGENTS.md
dit encore « ne pas se contenter de la baisse de l'adversaire » : signaler la tension plutôt que
trancher.

**20/10 (utilisateur), renforcé** : « garder de la trésorerie n'est pas important » ; prendre en compte la valeur d'entreprise « paraît incohérent avec la philosophie d'OpexAI : s'il s'agit d'avoir des milliards en trésorerie ça ne sert à rien ». Conséquences : pas de réserve de caisse exigée pour les dépenses rentables (V249 mode 2) ; la garde de valeur 5 % des portes (AGENTS.md/CLAUDE.md) est en tension avec cet avis — la signaler à chaque verdict, ne pas la retirer sans décision écrite de l'utilisateur. Lié : [[banc-aaahogex-openttd15]], [[duel-non-deterministe]].

## duel_non_deterministe

Mesuré le 2026-09-21 (C69, `docs/11_goulot_decision.md` §13.4 et §16.1) :

- **Solo** : deux lancements séparés de `master` → mêmes chiffres au bit près. Deux `--repeats` dans un run aussi.
- **Duel contre AAAHogEx** : même code relancé → seulement 2 profits de 1975 identiques sur 10, écart jusqu'à 18 % (graine 7 : 1,046 → 1,234 M£).
- Tout ajout d'opcodes (même un test de drapeau inerte) déplace aussi une partie solo de quelques % : trajectoire chaotique.

**Why:** un verdict de duel 5×6 a failli être lu comme un effet réel alors qu'il était dans le bruit.

**How to apply:** ne jamais comparer une seule graine ni conclure d'un 5×6 en duel ; pour un duel, compter sur le 20×10 et le test des signes, ou répéter les parties. Voir aussi [[banc-monograine-insuffisant]] et [[banc-wins-exaequo]].

**Ajout du 2026-09-21 (soir) : le 5×6 solo ne prédit pas le 20×10 duel.** Trois fois le même jour, un 5×6 solo positif s'est effondré au 20×10 duel : C69 (+18 %, 4/5 → 12/20), C69 bis (4/5 → 12/20), C72 (ROI +292 k£ 4/5, C69 +145 k£ 4/5 → −2 à −4 k£, 11/9). Ne pas présenter un 5×6 solo comme un signal ; c'est au mieux un smoke et un contrôle de mécanisme (ex. « construit-il d'autres avions ? »).

## protocole_adoption_sans_puissance

**À LIRE AVANT DE LANCER OU D'INTERPRÉTER UN BANC D'ADOPTION.** Audit du 2026-10-03 sur les
**23 campagnes 20×10 appariées complètes** du dépôt (`results/*10y_20seeds*.json` +
`results/*20x10*.json`), en rejouant `annual_trajectory[].policy_delta` à chaque horizon 1..10.

**1. La porte ne passe jamais, et son unique passage est du bruit.** 1 verdict `pass` sur 23
(`opcode_exact_savefix_c121`, 15/20 pile, p=0,041). Le taux de faux passage sous H0 est de
**2,07 % par campagne**, soit **0,48 faux passage attendu sur 23** : le rendement de la porte est
indiscernable du bruit. Et ce passage est contredit par les amplitudes (Wilcoxon p=0,189,
CI95 bootstrap [−108 k, +240 k]) — il avait d'ailleurs été abandonné pour d'autres raisons
([[c121-opcodes-rythme-trajectoire]]).

**2. Puissance : 12 %.** L'effet typique que nous produisons vaut **d ≈ 0,18-0,28 par graine à tous
les horizons**. Le test des signes sur 20 graines a **12 % de puissance** à d=0,25 ; il faudrait
**201 graines** pour 80 %. Un 13/20 ou un 14/20 est le visage normal d'un effet réel sous ce
protocole, pas celui d'un effet absent.

**3. Dix ans est le PIRE horizon de la plage.** `sd/profit` monte de 0,11 (an 1) à 0,17 (an 10)
alors que `d` est plat ou plus faible à 10 ans (0,18) qu'à 3-8 ans (0,20-0,25). Allonger l'horizon
n'achète pas de qualité statistique, il en coûte.

**4. Le seuil de 50 000 £ est scale-blind** : 2,8 % du profit de référence à 10 ans, 4,0 % à 6 ans,
**22,7 % à 1 an**. Raccourcir l'horizon sans passer le seuil en pourcentage rend la porte
mécaniquement infranchissable.

**5. Coût : les 6 premières années ne pèsent que 40,5 % du travail de simulation** (intégrale
véhicules + ½ gares sur les 40 parties de `flat_20x10_20261003`). À budget constant d'un 20×10
(48 min, 3 workers, 72 s/partie) : **36 graines × 6 ans**, 63 × 3, ou 78 × 1. MDE à 80 % de
puissance : **10,5 % du profit à 20×10 → 7,5 % à 36×6 → 5,4 % à 63×3 → 3,6 % à 78×1**. Monotone :
**court et large domine strictement**.

**6. Wilcoxon + bootstrap changent le verdict de 5 campagnes sur 23, à coût de calcul NUL.** Ils
détectent 3 nuisances sous-estimées (`c86_marginal` p=0,040 / −153 k£ ; `nuit23_floor` p=0,024 / CI
entièrement négatif ; `small_towns` p=0,040 / −162 k£), rattrapent un gain rejeté à tort
(`nuit23_c77fix_vs_default` p=0,044, +147 k£, CI bootstrap > 0) et rejettent le faux positif du §1.
**Le test des signes jette les amplitudes : il est strictement dominé.**

**Why:** ça explique les tours en rond. Ce n'est pas que les idées ne valent rien ; c'est que
l'instrument ne distingue pas un gain de 4 % du bruit, et qu'il a laissé passer des nuisances. Voir
[[banc-wins-exaequo]] (recompter les ex æquo) et [[banc-monograine-insuffisant]] (le plancher de
~15 % annoncé pour les moyennes était optimiste).

**How to apply:** ⚠️ **rien n'a été changé** : `AGENTS.md` §4 et `policy_adoption_eligibility`
(« exactement dix ans ») restent en vigueur, aucun défaut touché, la proposition attend une
décision utilisateur. Proposition à **pré-enregistrer avant toute mesure** : porte A de gain en
**40 graines × 3 ans** (Wilcoxon p < 0,05 + CI95 bootstrap > 0 + moyenne ≥ 4 % du profit de
référence, ≈ 30 min), porte B de **non-érosion seulement** en 20×10 unilatéral sur les survivants,
suppression du diagnostic 5×6 (n=5, puissance nulle). ⚠️ **Risque de sélection post hoc à écrire
explicitement** : la règle est proposée après l'échec de `flat` ([[flat-bootstrap-seul-positif]]) ;
la justification repose sur 23 campagnes et un calcul de puissance indépendants de `flat`, et la
validation doit être une **nouvelle** mesure, pas une relecture du 20×10 existant. Limite à ne pas
cacher : la corrélation des moyennes de campagne vaut **0,60 (3a/10a)** et **0,63 (6a/10a)** — un
horizon court change l'objectif mesuré, et seule la porte B garde contre ça. Fiche `docs/taches.md` :
**V102**. Scripts du scratchpad : `an_horizon_multi.py`, `an_protocole.py`, `an_wilcoxon.py`.
