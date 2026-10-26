# P5 — GOOD source cargo qualify : pré-enregistrement expérimental

**26 octobre 2026 — avant tout code ou banc P5.** Branche
`p5_good_source_cargo_20261026`, base `848f5474`. Ce levier est indépendant
de P2, clôturé `NO-GO` sans occasion de classement réellement finançable.
Objectif stratégique : OpexAI/AAAHogEx **≥75 %** des profits annuels sur les
**20 mêmes graines × 10 ans** ; ni le nombre de candidats ni la porte A/B ne
remplacent cette mesure.

## Hypothèse et exclusion des pistes réfutées

Les archives descriptives 3×10 signalent 33 usines distinctes et 32 sans
sortie GOOD bâtie, mais les 53 496 rejets `origin_served` sont des passages
répétés. Quatre lignes GOOD d'AAAHogEx produisent une part importante du
profit ferroviaire observé, sans garantir qu'OpexAI puisse en financer et
construire autant. Les variantes GOOD simple (A 40×5 −40,7 k£/an), V233,
V294, N75-CAP et les greffes de chaîne restent **rejetées**. Ne pas remettre
en service leurs chemins ni élargir globalement le fret.

La première hypothèse P5 examine **la sortie GOOD nouvelle d'une industrie
déjà desservie en RAIL pour un autre cargo**, et uniquement si le fret GOOD
existe maintenant, si la gare source appartient à OpexAI, si une destination
accepte GOOD, et si une extension de quai/voie peut rester cohérente avec le
chantier existant. Une gare AIR, ROAD, adverse ou un deuxième quai indépendant
à portée de séparation n'est pas une source réutilisable. La gare réutilisée
doit être rattachée à l'extrémité **A** productrice, pas à B destinataire ;
ne jamais inverser source et destination pour faire passer les gardes.

## Réglage opt-in et contrat d'intervention

`good_source_cargo_qualify` : **0 OFF** identique historiquement, **défaut 0**
sur les quatre difficultés ; **1 SHADOW** passif et sans modification du
vivier, des stations, de la trésorerie, du cache ni d'`AITestMode` ; **2 ON**
conservateur avec **une seule nouvelle route GOOD éligible au plus par scan
complet**. Limiter la nouveauté au générateur de fret existant
`OpexFreightCandidates` : pas de deuxième génération globale de cargo, pas de
nouveau filtre de distance global ni de priorité forcée. N75, C77, `K_dec`,
V252, C121 et les politiques monomodales restent identiques hors ce dossier.

Règles conservatrices avant proposition ON :

1. Cargo `AICargo.GetCargoLabel(cargo)=="GOOD"`, ID résolu via API et
   `AIIndustry.GetLastMonthProduction(industry, cargo)>0`, origine industrielle
   propre, quai RAIL valide, station Opex non ambiguë, service existant sur
   **autre** cargo, jamais une sortie GOOD déjà bâtie. Une gare multiple ou
   une ligne avec `scrapping`/renouvellement en cours : **rejet**.
2. Destination industrielle ou urbaine acceptant GOOD dans le catalogue réel,
   non déjà desservie pour ce cargo, paire ni abandonnée ni dupliquée, revenu
   prévu `profitAnnual>0` et capital prévu fini, strictement positif et
   inférieur au budget disponible **après réserves** ; pas de veto AIR/V252
   par estimation inventée.
3. Extension de **l'exact quai source** avec type/ID de gare physique vérifiés
   et `joinEnd=A` ; pas de nouvelle gare indépendante à proximité. Les plans
   de voie/site passent les gardes et tests moteur existants ; une source
   `origin_served` ne reçoit aucune exemption large qui relâcherait aussi la
   destination B. En cas d'ambiguïté, fail-closed, sans nouvelle liaison.
4. Classement normal par profit/coût et classes C77, sans bonus ni déplacement
   artificiel du rang. Un seul dossier supplémentaire par scan, ordre stable
   des ex aequo. Aucun état persistant ajouté au Save/Load ; le dossier est
   reconstruit après chargement.
5. Mesurer et borner les opcodes d'éligibilité GOOD supplémentaires à
   **50 000 par scan complet**, en excluant explicitement l'A* de construction
   déjà facturé dans sa catégorie historique. Si le budget supplémentaire
   est dépassé, ne pas publier le projet ON. Les éventuelles erreurs moteur,
   sites ou économies inconnues sont des échecs et non des succès implicites.

Un **pré-requis d'architecture** reste à vérifier dans le code :
`OpexAI::_tooClose` exclut une ligne entière quand `joinLineId` est présent,
alors que ce levier ne peut exempter que l'**extrémité source A**. La mise en
œuvre doit conserver les contrôles de B et vérifier `OpexRailPlatformPlans`
(`joinEnd=A`), sans utiliser `joinLineId` comme passe-droit général. Si aucun
chemin physique sûr n'existe, rester au shadow et documenter `NO-GO` : ne pas
fabriquer une prétendue construction GOOD.

## Traçabilité et portes pré-fixées

Le journal expérimental `P5_GOOD_SOURCE` devra fournir au minimum :
`sourceIndustry`, `sourceStationId`, `sourceLineId`, `cargo`, destination
industrie/ville, `src`, `dst`, version de scan, statut GOOD réel, devis et
capital après réserves, cause d'échec et budget d'opcodes. Une clé stable
`industrie|cargo|destination` compte une seule route malgré les rescans.
Rattacher cette clé à `PROJECT_CHOSEN`, à `RAIL_ATTEMPT` et à `RAIL_BUILD`
avec `lineId`, coûts réels et date, sans considérer un plan prêt, un journal
ou une tentative comme une ligne bâtie.

**Validation** : tests ciblés fail-closed, budget, ex aequo, séparation A/B,
gare jointe, origine déjà desservie GOOD, cargo climatique absent, Save/Load,
OFF identique, shadow sans `AITestMode` et inventaires historiques ; suite
complète, `git diff --check`, smoke OpenTTD **1×1** et Save/Load moteur
`save_full_state=0`/`1` sans erreur script.

**Exposition** : appariée OFF `0` / SHADOW `1`, **graines
42,100,7,999,2026**, années **1970–1974 (5×5)** ; minimum **trois graines**
avec une **industrie GOOD distincte, raccordement/source et destination
physiquement plausibles** et un budget admissible. Ne compter ni les scans
répétés ni les dossiers rejetés. Sinon **NO-GO**, sans pilote ON ni porte A.

**Pilote ON 5×5** seulement après exposition admissible. Exiger **trois
lignes GOOD effectivement construites**, sur **au moins deux graines**,
rattachées causalement à cette exception de source, sans brèche de réserve,
collision de gare ou surcharge de 50 000 opcodes. Sinon **NO-GO**.

**Porte A** ensuite uniquement : multimodale **40 graines × 5 ans**
`gain_short`, profit annuel moyen ON−OFF **≥4 %** du témoin,
Wilcoxon bilatéral **p<0,05**, borne basse de l'IC95 bootstrap **>0**,
ratio des moyennes `company_value` **≥0,95** et **40/40 paires saines et
complètes**. **Porte B** **20 graines × 10 ans**, `non_erosion`, uniquement
si A passe ; comparer le rapport OpexAI/AAAHogEx sur les mêmes vingt mondes.
Même un passage A/B ne change pas le défaut sans décision explicite de
l'utilisateur. Un autre horizon ou une modification de seuil après exposition
est interdite ; publier un `NO-GO` et passer à la piste suivante en cas
d'exposition insuffisante.

## Verdict de l'exposition initiale — 26 octobre 2026

**`NO-GO` : la preuve physique pré-enregistrée n'est pas satisfaite.** Ne pas
faire passer cette issue pour l'échec d'une ligne GOOD construite : aucune
construction P5 ON n'a été qualifiée, et les étapes pilote ON, A40×5 et B20×10
**n'ont pas été lancées**. Les règles, graines et seuils ci-dessus restent figés.

- Version testée : branche `p5_good_source_cargo_20261026`, pré-enregistrement
  `8c816bc9`, bundle expérimental
  `16688d6b60d1cfd2b9ea2f0cf228b437448bd22846a94d610a674b10811aba44` ;
  l'archive figée conserve l'état sale, hors commit moteur à cette date.
- 2 906 tests hôtes complets **OK** (6 skipped, 2 expected failures), PO01C
  régénéré mécaniquement et octets historiques déduits sans changer leurs SHA ;
  11 tests dédiés P5. `git diff --check` : 0.
- Smoke OFF/ON réel `p5_good_smoke_42x1_20261026_r1` : 1/1 paire complète et
  saine, delta ON−OFF **0 £/an**, verdict **diagnostic_only**.
- Save/Load moteur ON graine 42 : `save_full_state=0` et `=1`, **13+13**
  sauvegardes chacun, `LOAD_RECONCILE` positif, zéro script error. La compagnie
  fantôme connue du harnais interdit de conclure à l'égalité parfaite des
  trajectoires. Le premier essai full et sa relance ont échoué **avant la
  simulation**, sur `httpx.ReadTimeout` du service BaNaNaS ; l'essai `r3`
  a réussi grâce à la réutilisation du cache déjà présent, sans changer le code.
- Exposition OFF/SHADOW `p5_good_shadow_5x5_20261026_r1` : cinq graines
  `42,100,7,999,2026`, années 1970–1974, **5/5 paires complètes et saines**,
  zéro run échoué, manifest SHA256
  `a2e6815265375724ca65546c5bae4c07aa98292a657382ed9b43f2857e110b2b`.
  Les journaux *shadow* comptent respectivement **13/14/36/1/7** événements
  `P5_GOOD_SOURCE action=shadow`, soit **71 occurrences**, pour **2/2/4/1/2**
  clés source/cargo/destination uniques, soit **11 clés** distinctes. Nombre
  maximal de `extra_ops` observé **6 838** ; ces nombres ne représentent pas
  une consommation totale de l'algorithme ni un chantier.
- Toutes les occurrences sont annotées
  **`stage=budget_plausible_site_unproven`** : cargo GOOD produit et source RAIL
  jointe à une station possédée vérifiés, rentabilité et trésorerie de l'instant
  selon devis prudent, destination acceptante au catalogue ; **aucune vérification
  physique complète des quais B / du tracé / du financement au chantier**.
  Le prérequis de **trois graines avec raccordement et destination
  physiquement plausibles** n'est donc **pas démontré** par ces 71 journaux.
  Un comptage optimiste de cinq graines serait abusif ; zéro occasion complète
  qualifiée est documentée, et l'issue reste `NO-GO`.
- Descriptif SHADOW−OFF uniquement : delta moyen `profit_year` **−73 163,6 £/an**,
  médiane **0**, **2V/2D/1E**, Wilcoxon bilatéral **p=0,625**,
  IC95 bootstrap **[−194 073,2 ; +16 147,2] £/an**, ratio de moyennes
  `company_value` **0,990114**. Aucune amélioration causale du comportement :
  shadow ne publie ni ne construit de projet supplémentaire.

**Limites du prototype archivé :** les fragments d'IA ont été exécutés dans
le worktree P5, mais l'exception de jointure source n'a jamais débouché sur une
construction démontrée. Le journal initial n'expose pas tous les champs
`src`/`dst`/version de scan du contrat ci-dessus, et le filtrage des gares
multi-services et du fret secondaire `cargo2` est incomplet. La voie V276
découpée est volontairement fail-closed (`P5` inactif pour cette voie) afin de
ne pas permettre un candidat par sous-paire. **Ne pas adopter ni promouvoir ce
prototype comme solution prête** sans qualification physique supplémentaire.
Le paramètre conserve le défaut **0** ; aucun seuil n'a été retouché.
