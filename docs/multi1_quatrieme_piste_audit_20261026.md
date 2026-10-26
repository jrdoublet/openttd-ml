# MULTI-1 — audit du quatrième mécanisme avant expérimentation (26 octobre 2026)

**Décision : quatrième intervention NON CODÉE, faute d'un gisement économique et
physique établi.** Ce document ne constitue **ni** un quatrième pré-enregistrement
de politique ON **ni** un verdict de porte A/B. Après les trois
`NO-GO_NON_EXPOSE` (voir `docs/taches.md`), créer immédiatement un autre toggle
serait répéter une optimisation dont on ne sait pas démontrer l'exposition.
L'objectif de **75 % d'AAAHogEx en 20×10** reste **non atteint**, et MULTI-1
reste **ouvert**.

## Ce que les données autorisent et n'autorisent pas

- [Analyse multimodale initiale](multi1_analyse_20261026.md) : à cinq ans,
  Opex possède environ 4 véhicules ROUTE contre 147 AAA, mais réalise déjà
  92,67 % du profit AAA sur la référence P6 OFF ; ce ratio n'est pas celui
  des anciennes campagnes à dix ans.
- [Même cohorte sur dix ans](multi1_horizon_10ans_20261026.md) : la cible de
  75 % est franchie **vers le bas en 1975** (74,48 %), et le ratio termine
  à 56,55 % en 1979, malgré environ 14,9 M£ de caisse Opex. Il faudrait
  ~1,345 M£/an de profit supplémentaire à AAA constant.
- Dans les cinq journaux de référence instrumentés du troisième pilote,
  seules 12 constructions ROAD portent au total **65 702 £/an de profit
  prédit** (pas réalisé). Aucun des détours ROUTE n'a trouvé de rescue. Les
  rejets ROAD visibles ne sont pas un portefeuille de lignes rattrapables.
- Les **95–97 % de bus AAA rattachés à une gare air/rail** sont surtout du
  rabattement, à profit routier autonome de −8 à +3 k£/an
  (`docs/taches.md`, V242, autour des lignes 789–790). La copie V139 des
  feeders perd **154,3 k£/an en A40×5**, tandis que V266 rail→air perd
  **83,2 k£/an en diagnostic 3×3** (ibid. V266, lignes 889–893).
  **Ne pas présenter le nombre de bus AAA comme une marge marginale.**
- Libérer uniquement le créneau d'A* RAIL a déjà recyclé le travail vers
  d'autres échecs ; V100 et V100bis possèdent des verdicts documentés.
  V254 (second aéroport) et V255 (escales) ont également été écartés pour
  les raisons détaillées dans `docs/taches.md`. Ces tentatives ne doivent
  pas être renommées en MULTI-1 pour les rejouer.

## Seul quatrième mécanisme structurellement distinct à instruire

**Hypothèse non testée : la génération de fret ROUTE s'arrête trop tôt à un
seul cargo tournant**, alors que d'autres marchandises avec moteur, source,
puits et marché pourraient produire une route rentable. Elle porte sur
l'**entrée du vivier** et non sur le classement TOP-K, la promotion d'une
route, ou sa géométrie après `TRACEX` :

- `ai/OpexAI/projects_generation.nut:13-19` récupère `freightCargo` ;
  `:22-67` autorise plusieurs cargos en *repli RAIL* si le premier vivier
  n'a pas de fret ; `:75-85` demande **une seule fois** les candidats ROAD
  avec ce cargo. Le chemin de génération complète emploie lui aussi ce
  seul argument (`ai/OpexAI/projects.nut:297-307`).
- `ai/OpexAI/candidates.nut:1827-1832` exclut tous les cargos autres que
  `freightCargo` lorsque celui-ci est renseigné ; la génération ROUTE
  appelle ce filtre (`:1971-2000`). Il existe donc un emplacement technique
  pour un *deuxième cargo*, **pas une preuve** que celui-ci offre un projet
  finançable et physiquement bâtissable.
- Assouplir le verrou des industries d'origine servies n'est **pas** ce
  mécanisme : le C55 historique récupérait 86,1 % des rejets mesurés, mais
  a dégradé le profit annuel de 2,3 % sur 20×10 (6 victoires/13 défaites,
  une égalité). Voir
  `docs/journaux/journal_2026-09-13.md:748-784` ; ne pas le répéter.

### Condition préalable avant toute implémentation ON

Les journaux disponibles montrent `VIVIER_GEN mode=road`, `ROAD_BUILD` et
des raisons de rejet, **pas** la population des cargos secondaires qui ont
été délibérément exclus. Les snapshots du 20×10 historique n'incluent pas de
`line_telemetry` ni de logs métier. Impossible donc de calculer, sans
observation nouvelle, le nombre de projets alternatifs *uniques* qui sont
simultanément : source/puits admissibles, projet au profit prédit positif,
cash disponible après réserve, chantier routier possible sous `AITestMode`,
et potentiel de revenu **additionnel** (sans cannibaliser AIR/RAIL).

**Étape de qualification méthodologique suivante** : une observation isolée,
symétrique et à budget d'opcodes borné de la *deuxième* marchandise lorsque
la génération ROUTE ordinaire n'a pas de projet finançable. Compter par
graine/cargo/pair `(src,dst)` les candidats réellement admissibles, leurs
devis et leur gain marginal maximal plausible, sur la fenêtre 1971–1973.
Faire le bilan de rentabilité **avant** d'écrire une politique capable de
construire. Aucun nouveau banc de cette nature n'a été autorisé par les
données anciennes comme **porte économique**.

Si cette préqualification démontre un véritable vivier, publier un
**quatrième pré-enregistrement distinct AVANT code ON**, par exemple :

- opt-in **0 OFF aux quatre difficultés**, 1 shadow, 2 ON, multimodal
  1971–1973, **un cargo alternatif au maximum**, sans modifier économie,
  capital, score, priorités AIR/RAIL ou constructeur ; bornes explicites
  d'opcodes et de Save/Load dans la fiche finale ;
- exposition de **≥3/5 graines** avec candidats alternatifs profitables,
  finançables et physiquement testés, **et ≥2/5** avec `ROAD_BUILD` de même
  `(src,dst,cargo)` en ≤90 jours après sa sélection effective ;
- si et seulement si exposition validée : A **40×5 `gain_short`**, sondes 2,
  Δ profit ≥4 %, Wilcoxon p<0,05, IC95 bootstrap bas>0, garde valeur ≥0,95 ;
  B **20×10 `non_erosion`** uniquement après A `pass`, objectif ≥75 %
  publié séparément ; **aucune adoption automatique**.

Ces seuils sont ici une **proposition à confirmer dans la fiche future**,
et ne prétendent pas être des critères irrévocables d'un pilote lancé.
Sans vivier observable ni ampleur économique plausible, rendre
`NO-GO_GISEMENT_INSUFFISANT` **pour la piste envisagée avant code**, sans
confondre cette décision méthodologique avec les trois verdicts
pré-enregistrés `NO-GO_NON_EXPOSE`.

**Périmètre strict :** aucun paramètre par défaut, aucune IA, aucun banc,
aucun Docker, aucun seuil antérieur ni tâche P1/VPS, P6 ou LATE-GAME-1
modifiés par cet audit. Conserver la priorité à la capacité d'expliquer le
profit marginal, plutôt qu'à l'augmentation brute du nombre de lignes.
