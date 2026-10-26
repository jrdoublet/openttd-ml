# FRONT-PAX-2 — pré-enregistrement du candidat PASS à recouvrement borné

**26 octobre 2026, avant implémentation exposée ou banc du candidat.** Base
`458a08a8`, branche isolée `front_pax2_behavior_20261026`. La sonde
historique `nuit75-front-pax2` ne qualifie aucune baisse de frontière : ses
13 370 visites de couples sous 200 tuiles sur cinq graines et dix ans sont
des évaluations géométriques répétées, sans validation économique, financière
ou construction. Parmi elles, seuls 900 passages ont été comptés dans des
scans commencés après 1974, sur des fins de scan concernant la seule graine 100.

## Intervention et garde de neutralité

Réglage expérimental `front_pax2_bounded_air_overlap` : **0 OFF par défaut aux
quatre profils**, **1 shadow**, **2 ON pilote**. Sur OFF, `catalog.bounds`,
`OpexAirPairInBand`, scores, nouvelles routes, fret et dépenses conservent
leurs chemins habituels. Shadow enregistre seulement une shortlist de paires
PASS rencontrées dans les **boucles déjà parcourues** ; aucun appel C121,
`AITestMode`, recherche de site, A* ou projet supplémentaire. ON ouvre au plus
**un candidat AIR par bras** (`newpair`, `hubsite`, `hubhub`) et par **scan AIR
complet**, après les gardes existantes et les modèles C121 : trois dossiers
économiques maximum par scan ; aucun changement de `railMax` ou de frontière
du fret. Lorsqu'une observation est incomplète ou un cycle est censuré, aucune
paire supplémentaire ne devient éligible. Les candidats ordinaires restent
traités par le pipeline historique.

La présélection de chaque paire respecte d'abord `minDist`, les limites
`airMax`, `AIR_MAX_DISTANCE` et `plane.maxOrderDistance`, les phases
`PAX_BAND_*` et les paires existantes/abandonnées. Les dossiers sont
dédupliqués par bras, extrémités, ancrages, type d'aéroport et combinaison
inspectée, avec classement reproductible par un proxy bon marché de demande
et de distance ; au plus un gagnant conservé par bras et par scan complet.
Le pilote ON concerne initialement **`PAX_BAND_ALL` seulement**, et les bandes
segmentées font l'objet de diagnostics distincts, sans ouverture supplémentaire.

## Croisement des temps présélectif

Le seuil temporel n'est **pas** fixé d'après les résultats de ce banc. Sous
une vitesse RAIL observable `vRail` et une vitesse API avion `vAir` positive :

`tauRail = 1/(0.036 × vRail)` ; `tauAir = 1/(0.036 × vAir)` ;
`D* = (TsolAIR + TchargeAIR − TstopRAIL)/(tauRail − tauAir)`.

`TsolAIR` reprend **une seule fois** les manœuvres physiques C100.1/C121 :
taxi limité à vitesse 50, emprise de l'aéroport ramenée aux 2/3, transition
verticale `300/ticksPerDay`. `TstopRAIL` reprend si connu le séjour de gare
`OpexRailStationDwellDays` (V216f). Une charge AIR propre à la paire est
inconnue avant C121 : préfiltre optimiste `TchargeAIR=0`, jamais traité comme
une observation réelle ; une vérification postérieure doit la mesurer sans
doubler le résidu appris des hubs. `tauRail <= tauAir`, vitesse manquante,
dénominateur non fini, type d'aéroport inconnu ou modèle physique invalide :
**pas d'ouverture**, jamais de borne arbitraire. Sinon seuil entier par
`ceil(D*)`, clamp entre les limites PASS basse et RAIL haute déjà calculées.
L'exemple documentaire 115/570 ne constitue **pas** un seuil opérationnel.

La durée RAIL issue d'une vitesse calibrée à 20 tuiles reste une
approximation. La frontière cinématique ne suffit jamais à conclure au ROI :
les vrais profits, coûts, durées, décisions C121, capital, réserves, scores de
portefeuille et construction doivent être enregistrés **après** la shortlist.

## Qualification fixée avant exposition

1. Contrats OFF et Save/Load (cache de scan temporaire, aucune persistance),
   tests des bornes/dénominateurs, trois bras, phases, reprise C78, cap de
   trois dossiers, économie C121, site, finance et neutralité historique ;
   suite hôte complète, `git diff --check`, smoke 1 graine × 1 an.
2. Exposition sur les cinq graines `42 100 7 999 2026`, horizon 1970–1979
   si nécessaire pour qualifier l'apparition tardive, avec mêmes politiques,
   cartes et sondes. Exiger une mesure des opcodes/ticks supplémentaires,
   nombre de scans complets/censurés, clés de paires uniques, shortlist,
   constructibilité physique, profits et CAPEX prévus, ROI, coût de réserve,
   classement top-K, achats réels et alternative évincée. Une émission
   `FRONT_PAX2` seule **n'est pas** une ligne bâtie.
3. Condition GO exploratoire avant porte A : **au moins cinq paires-mondes
   PASS uniques** faisables, rentables et finançables sur **au moins trois
   graines** ; au moins une occasion après 1974 dans **deux graines**, au
   moins **deux** entrants distincts effectivement classés top-K finançables
   et **une** route AIR supplémentaire réellement construite dans le pilote
   ON sous exposition contrôlée. Pas de nouvelle A si ces preuves manquent,
   si le surcoût en opcodes devient déraisonnable, si la garde OFF échoue ou
   si la provenance des bras est ambiguë. Aucun ajustement rétrospectif des
   bornes après observation de ces graines.
4. Après GO seulement : **porte A multimodale 40 graines × 5 ans**,
   `profit_year` apparié, `gain_short` : delta moyen ≥ **4 %** du témoin,
   Wilcoxon exact bilatéral **p < 0,05**, borne basse IC95 bootstrap **> 0**,
   `company_value` variant/référence **≥ 0,95**, 40/40 paires complètes.
   **B 20 graines × 10 ans** en `non_erosion` **uniquement si A passe**.
   Mesurer dans B le rapport Opex/AAAHogEx des moyennes et la médiane des
   ratios par graine ; cible externe **75 %** sans la substituer aux portes.

Toute mesure de shadow, toute construction ON en pilote et toute comparaison
économique gardent leur provenance et leurs verdicts distincts. **Aucun
changement de défaut ni adoption** sans décision explicite de l'utilisateur.

## Validation mécanique (26/10/2026)

Code fixé sur la branche `front_pax2_behavior_20261026` au commit `cbd998c1`,
défaut `front_pax2_bounded_overlap=0` confirmé pour les quatre difficultés.
La suite hôte complète a passé **2 887 tests** (six ignorés, deux échecs
attendus). Les 13 tests FRONT-PAX-2 sont verts, de même que PO01C (27) et V278
(19) ; les empreintes figées PO01D `air_planning.nut` et `candidates.nut`
restent identiques après retrait contrôlé des ajouts FRONT-PAX-2. Le chemin
PO01C généré a été actualisé mécaniquement ; `git diff --check` est conforme.

Smoke moteur `frontpax2_bounded_smoke_42x1_20261026_r1` : bras OFF `0` et
pilote ON `2`, graine 42, 1970, **1/1 paire complète et saine**, aucune
exécution invalide, bundle SHA256
`bc7ef57c3c7b7eb1ca635a054c6841808b27f103931f0cbcc7f284553ea3a367`,
manifeste SHA256
`d1ce23d06fc195aa6c9c22090ce6bf77cbeacd1ad8da9710111214bc3af666b7`
vérifié. Le journal `FRONT_PAX2_BOUNDED` prouve que le mode `2` a examiné un
hubsite viable cinématiquement et économiquement (`profit=351688`,
`finance=106128`) puis l'a exclu faute de trésorerie (`result=cash`).
Le bras ON présente `profit_year` −11 583 £ face à OFF sur ce seul monde,
valeur **diagnostique**, sans conclusion économique ni preuve de construction
supplémentaire.

Save/Load réel du mode `2` sur la graine 42 :
`results/frontpax2_bounded_saveload_short_42_20261026.json` avec
`save_full_state=0`, et
`results/frontpax2_bounded_saveload_full_42_20261026.json` avec
`save_full_state=1`. Dans chaque test, 13 sauvegardes en phase A et 13 en
phase B, rechargement de `000000005.sav` datée du 01/07/1970,
`LOAD_RECONCILE` observé et aucune erreur script. Une compagnie fantôme du
harnais apparaît à la reprise ; cette validation concerne la reprise du
script, jamais une égalité de trajectoire ou de profit.

Les conditions de GO économique définies ci-dessus ne sont pas encore
remplies par ces essais mécaniques. Aucun réglage par défaut n'est modifié.
