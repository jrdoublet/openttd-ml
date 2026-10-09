# P0 RAIL — gate de dominance intermodale pour le second A* (09/10/2026)

## Hypothese et protocole avant banc

Le prototype `rail_cooperative_n2=1` permanent a echoue a la porte V102
40 graines x 3 ans (`rail_n2_gain_short_40x3_20261009_r6`, -47 870 GBP/an,
`fail_primary`). Le diagnostic 3 x 5 est positif mais non qualifiant.

Hypothese nouvelle et *distincte* : N=2 n'est utile que si **deux projets rail
independants** ont effectivement priorite sur la meilleure alternative
non-rail finançable, alors qu'un seul A* peut avancer a la fois. Un second
A* lance hors de cette fenetre peut consommer des opcodes et decaler AIR sans
preparer un chantier competitif.

## Intervention isolee, OFF par defaut

- `rail_cooperative_n2` : 0 au defaut, inchangé ; N=2 experimental.
- `rail_n2_opportunity_gate` : **0** par defaut, n'a d'effet que sous N=2.
  A chaque tentative de depart de B, verifier le classement `this._projects.best`
  deja actualise par `OpexPromoteLiveDefensiveAir`. A (la recherche en cours)
  et B doivent y etre identifies, avoir un `fundScore` positif, un capital
  `OpexProjectFinanceCapital` payable avec `OpexAvailableCapital`, etre **avant**
  le premier projet non-rail eligible et surclasser en `fundScore` (bonus
  early-slot inclus pour AIR) **toutes** les alternatives non-rail retenues.
  Le classement effectif garde les tiers C77, et les reordonnancements C120.
  Si le topK **complet** est occupe par au moins deux OD rail distinctes et
  finançables, l'absence de concurrent non-rail est interpretee comme un
  portefeuille sature de rail : admettre B, meme si le score AIR du projet
  exclu du topK reste censure. Si le topK n'est pas plein ou si A/B ne sont
  plus visibles et finançables, rester a N=1. Pas d'annulation d'une recherche deja
  demarree si le classement change ulterieurement.
- `rail_air_breakpoint_shadow` : **0** par defaut, independant ; relit les
  donnees de `OpexProjectSelectAffordable` *apres* le tri final, sur une
  selection reelle, et logue les scores / rangs AIR, RAIL et autres ainsi que
  le nombre d'OD rail distinctes en tete. Ne change aucun classement.

Limites conscientes : `best` est tronque a `PROJECT_TOP_K`, l'absence d'AIR
dans ce tableau n'est pas une preuve de non-existence (le cas sature est une
**hypothese comportementale a tester**, non une preuve de ROI) ; `fundScore` est un
devis economique calibre et peut etre date, pas du profit realise ; la
finançabilite n'est pas une simulation de constructibilite ; le budget global
V89 est **partage** entre les A* et n'augmente pas avec N. Les achats hors
portefeuille demeurent une limite deja documentee dans
`portefeuille_classement_unifie_cible_20261009.md`.

## Validations pre-enregistrees

1. Contrats Squirrel N2 / B5 / C121 / C80, plus compile/smoke moteur.
2. Exposition sous `decision_log=1` (diagnostic, non qualifiant) :
   `RAIL_N2_GATE admit=0/1`, `RAIL_N2 second_start`, logs de bascule,
   verification FIFO, construction A d'abord, revalidation de B.
3. A/B economique avec bundle OFF/ON identique, reference
   `rail_cooperative_n2=0,rail_n2_opportunity_gate=0` contre variante
   `rail_cooperative_n2=1,rail_n2_opportunity_gate=1` ; autres reglages
   identiques, `decision_log=0`, protocole V102 `gain_short` 40 x 3,
   seuil moyen +4 %, Wilcoxon p<0,05, IC95 bootstrap borne basse >0,
   garde valeur >= -5 %. Pas de B 20 x 10 si A echoue.

Statut initial : intervention implementee localement, pas adoptee, aucun
commit/push autorise implicitement. Les resultats moteur et economiques
seront renseignes apres une campagne realisee, pas extrapoles de scores.

## Validation et premier diagnostic figé

Les contrats host N2 14/14, C80 18/18, B5 11/11, C121 9/9 et decodeur
breakpoint 2/2 sont verts (**54/54**). Smoke moteur 1x1 seed42
`results/rail_n2_gate_smoke_42x1_20261009.json` : partie OK, profit_year
500 509 GBP/an, company_value 434 741 GBP ; un an ne qualifie pas la garde
car l'exposition ferroviaire survient ensuite.

Diagnostic observationnel `rail_n2_gate_diag_3x5_20261009_r1`, bundle
`e48f533d7f2616eff108f998edc036faf98e5f89360476c2a0d6550e0ff61c4b`,
manifest `eb254456000bfb0fa1152b9b674237ad47a3f71b41d316c53bc5434bc8288566`.
Reference N1 vs N2 gate, **memes** reglages `decision_log=1` et
`rail_air_breakpoint_shadow=1`, trois graines 42/100/999 sur 1970–1974,
6/6 parties saines. **Une seule victoire / deux defaites**, delta terminal
Opex +21 303 GBP/an en moyenne mais mediana -94 349 GBP/an ; ecarts
seed42 **-94 349**, seed100 **-94 594**, seed999 **+252 852 GBP/an**.
Ratio des valeurs des compagnies **-2,85 %**. Verdict `diagnostic_only` ;
aucune qualification economique.

Mecanisme et source de donnees :
`results/rail_n2_gate_diag_3x5_20261009_r1_n2_trace.json`,
`results/rail_n2_gate_diag_3x5_20261009_r1_breakpoint.json`.
Le gate a lance **8 B** (seed100 1, seed42 3, seed999 4), sans
`second_ready` duplique et sans chantier B avant consommation A dans les
evenements disponibles. Seed100 le 27/05/1972 :
`RAIL_N2_GATE admit=1 rail_rank=1 primary_rank=0 other_rank=5` ; scores
RAIL B **1 074,65**, RAIL A **1 174,61**, alternative FLEET **1 020,46** ;
B demarre effectivement le 09/06/1972. Ce n'est pas une preuve que B est
ensuite construite : le cas finit en `second_discard`.

Premieres dominances **dans les snapshots observes**, par graine :
N1 seed100 05/04/1972, seed42 04/07/1972, seed999 02/07/1973 ;
N2 gate seed100 17/04/1972, seed42 03/09/1973, seed999 06/03/1973.
Ces dates ne sont ni universelles ni directement comparables entre bras :
la politique modifie le portefeuille et le shadow ne journalise que des
signatures qui changent. Dans les variantes, AIR est absent de respectivement
450/604, 474/789 et 542/660 snapshots : **censure du topK importante**.

Protocole V102 ensuite lance : `rail_n2_gate_gain_short_40x3_20261009_r2`,
reference N1 vs candidat gate, 40 graines canoniques x 3 ans, 10 CPU/10 workers,
sans `decision_log` ni shadow, plus 4 % de seuil de gain et garde -5 %.

## Verdict V102 — 09/10/2026 (porte A terminee)

Resultat : `results/rail_n2_gate_gain_short_40x3_20261009_r2.json` ;
manifeste figé `results/rail_n2_gate_gain_short_40x3_20261009_r2.manifest.json`.
Bundle SHA256 `e48f533d7f2616eff108f998edc036faf98e5f89360476c2a0d6550e0ff61c4b` ;
image `openttd-lab:latest` ID `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` ;
OpenTTD 15.3. Comparaison isolee : `rail_cooperative_n2` 0->1 et
`rail_n2_opportunity_gate` 0->1 ; shadow et decision_log OFF des deux cotes.
80/80 parties terminees, 40/40 paires completes, 0 run en erreur.

| Indicateur a la fin de 1972 | Variante gate - reference N1 |
| --- | ---: |
| Profit annuel moyen | **-60 078,425 GBP/an** |
| Profit annuel median | -43 203,5 GBP/an |
| Victoires/defaites/egalites | 13/26/1 |
| Wilcoxon bilatéral | p=0,0142852 |
| IC95 bootstrap de la moyenne | [-108 864,55 ; -13 815,825] GBP/an |
| Valeur de compagnie, ratio des moyennes | **-2,81297 %** |
| Regle V102 | **`fail_primary`** ; seuil +4 % non atteint |

Chronologie des snapshots apparies, 40 graines, differences de **moyennes**
de `profit_year` en decembre : **1970 -5 516,77**, **1971 -27 338,35**,
**1972 -60 078,43 GBP/an**. Deltas du nombre moyen de vehicules AIR :
respectivement **+0,05**, **-0,90**, **-0,85** ; RAIL : **0**, **0**, **-0,45**.
Les valeurs de 1970/1971 ne prouvent pas une admission B : le flag N2
active egalement un chemin de scheduler, meme sans secondaire ; aucune
chronologie causale fine ne peut etre extraite des 80 logs r2 **vides**
(`decision_log=0`). Ne pas attribuer toute la perte a des B construits.

Le diagnostic distinct 3x5 sous logs, **non qualifiant**, atteste 8 B demarres
(seed100=1, seed42=3, seed999=4), **0 construction B confirmee a l'horizon**.
Quatre B termines sont abandonnes : seed100 `quote_STNFAIL` (794 436 opcodes
de tranches A*), seed42 `too_close` (2 601 767), seed999 `quote_TRKFAIL`
(7 006 240) et `quote_STNFAIL` (4 198 966) ; **14 601 409 opcodes**
cumules sur ces quatre recherches finalement inutilisees. Les quatre autres B
n'ont pas de chantier abouti prouve dans l'horizon. Ce constat est un mecanisme
plausible de cout d'opportunite, **pas** une attribution causale des pertes
40x3 aux quatre cas d'un autre echantillon/horizon.

La branche `railOnlyFull` (topK entierement RAIL) est une hypothese censuree,
non une preuve de superiorite sur AIR ; aucune des 52 admissions positives
**journalisees** dans le diagnostic 3x5 ne passait par `rail_only_full=1`
(admissions repetees, pas 52 projets independants). Le critere de score/rang
ne capte ni probabilite de pose reussie, ni vieillissement du devis, ni cout
des opcodes de B. Sans ces informations, augmenter le nombre de A* est premature.

**Decision : rejet pour adoption, reglages OFF, aucune porte B 20x10,
aucun commit/push.** Suite recommandee, sans nombre magique : mesurer sur
un meme etat de jeu le gain marginal attendu *apres constructibilite*
et le cout d'opportunite de la recherche B (temps/opcodes et projets AIR
retardes), puis comparer aux projets alternatifs effectivement finances.
