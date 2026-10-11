# P0 RAIL — plan de qualification économique et opcodes (10 octobre 2026)

**ARCHIVE INACTIVE (11 octobre 2026) :** l'utilisateur a rejeté
définitivement `simple_roi` et `simple_opcode`. Les étapes prospectives de ce
plan décrivent l'hypothèse antérieure à la clôture et **ne doivent plus être
exécutées**. Les sources des scripts retirés du dossier actif sont conservées
dans `evidence/review/p0_worktree_cleanup_20261011/untracked_scripts.zip`.
Voir `docs/rail_magic_final_qualification_20261010.md` pour les décisions.

**Statut : protocole proposé, pas une nouvelle expérience exécutée.** Aucun
changement des défauts, aucune nouvelle formule, aucune campagne Docker et
aucun commit/push autorisés par ce document.

## Objectif : deux verdicts indépendants par variante

On veut décider **positif, neutre, négatif ou indéterminé**, séparément pour :

1. `rail_magic_simple_roi=1`, avec `rail_magic_simple_opcode=0` ;
2. `rail_magic_simple_opcode=1`, avec `rail_magic_simple_roi=0`.

Le témoin a toujours les **deux flags à zéro**. Ne jamais les activer
simultanément (ROI aurait priorité) ; mêmes autres settings et bundle source
figé OFF/ON ; C80, origin reuse, les autres essais P0, probes intrusives OFF.

Les deux critères ne s'échangent pas : une optimisation d'opcodes avec un
effet économique nuisible reste **rejetée** ; une amélioration de profit qui
coûte trop d'opcodes échoue aussi à la qualification recherchée. Le tableau
final doit comporter **économie 5 ans / économie 10 ans / coût intrinsèque RAIL /
opcodes VM totaux**, même quand une case est `indéterminé`.

## 0. État des preuves déjà disponible : ne rien refaire inutilement

| Variante | Économie 40×5, delta ON−OFF | Opcodes observés | Verdict courant |
|---|---|---|---|
| ROI pur | +48 984,825 £/an ; IC95 [−18 742,9 ; +118 177,6] ; garde valeur +2,0718 % | `observed_opcodes_total` **partiel** +4,288 M ; mesure score/TOP20 **absente** | **Économie indéterminée**, opcodes indéterminés |
| Profit/itérations | **−88 103,8 £/an** ; IC95 [−172 423 ; −6 074] ; valeur **−4,6852 %** | OP/OS partiels −5,88 % ; autres panneaux partiels −8,67 % | **Économie négative et rejetée**, opcodes intrinsèques et VM totaux indéterminés |

Sources : `docs/rail_magic_simple_roi_gate_20261010.md`,
`docs/rail_magic_simple_opcode_gate_20261010.md` et
`docs/rail_magic_opcode_first_divergence_20261010.md`.

**Nuance statistique importante :** le second IC est entièrement sous zéro,
mais sa borne haute −6 074 £/an n'est pas en dessous de la marge de −1 %
(−19 983 £/an). On a donc une **régression directionnelle de la moyenne** et
une violation de garde de valeur ; pas une démonstration par cet IC que la
perte de profit dépasse **au moins** 1 % dans la population. Son rejet
économique ne dépend pas de cette distinction supplémentaire.

Le ROI pur a été testé avec le bundle `fe7c47d5...`, le ratio seul avec
`226368a5...`. Les comparaisons sont valides **à l'intérieur** de chaque A/B,
mais il est interdit de soustraire les deux variantes **entre** ces bundles.

## 1. Définir les jugements AVANT d'examiner de nouveaux résultats

### 1.1 Économie

- Unité d'échantillonnage : **graine**, comparaison OpexAI ON−OFF sur le
  même monde, même horizon. Primaire : `profit_year` terminal.
- Effet relatif `D = 100 × moyenne(ON−OFF) / moyenne(OFF)`.
  Intervalle de confiance bootstrap apparié par **graine** (20 000 tirages,
  graine bootstrap préfixée, convention historique 0), en recalculant le
  ratio sur chaque tirage ; garder aussi la moyenne en £, médiane, dispersion,
  Wilcoxon, V/D/E. Contrôler que la référence est positive.
- **Marge d'effet négligeable : ±1 %** du profit annuel terminal OFF, comme
  dans les deux essais antérieurs (sans changer rétrospectivement leur règle).
- **Positif démontré :** borne basse IC > **+1 %** et garde `company_value`
  non dégradée au-delà de −1 %.
- **Neutre démontré :** IC entier à l'intérieur de **[−1 % ; +1 %]** et
  garde de valeur tenue. Une p-valeur non significative n'est pas une preuve
  de neutralité.
- **Négatif substantiel démontré :** borne haute IC < **−1 %** ; **régression
  directionnelle démontrée :** borne haute < 0 (même si on ne peut pas certifier
  une ampleur >1 %). Une détérioration de valeur dépassant la garde de −1 %
  motive un **rejet de sûreté**, noté séparément de la preuve sur le profit.
- **Indéterminé :** tous les autres cas, y compris un IC traversant 0 et
  débordant ±1 %, une couverture insuffisante ou des résultats profit/valeur
  contradictoires. Ne jamais forcer une étiquette parmi trois seulement.
- `company_value` : ratio des moyennes ON/OFF, comparé à la garde −1 % déjà
  préenregistrée. Fournir en complément son IC apparié, les trajectoires AIR,
  RAIL, ROAD, les infrastructures, les pires graines et l'évolution annuelle.
  Cette lecture secondaire ne sert pas à choisir a posteriori une statistique
  favorable.

Si plusieurs analyses d'IC décisionnelles sont faites sur le **même** jeu
de graines à des tailles intermédiaires, employer une règle séquentielle
préenregistrée (p. ex. Bonferroni sur deux regards) ; sinon analyser **une
seule fois à l'effectif fixé**. Les 20×10 sont un nouvel horizon et demandent
leur propre jugement, pas un pooling avec les 5 ans.

### 1.2 Opcodes : ne pas mélanger trois grandeurs

Mesurer et publier **trois colonnes**, de précision croissante :

1. **Coût intrinsèque** du chemin modifié : génération du score `ratio`,
   TOP20 `OpexTopK` et bandes `OpexBands`, sur **exactement le même pool** de
   candidats. C'est le coût qu'on peut attribuer à la substitution.
2. **Postes instrumentés des parties** : `cand_pax`, `cand_freight`,
   `cand_rank` via OP/OS, plus IG/OB/RB/OA/OM ; valeurs cumulées qui changent
   aussi lorsqu'il y a moins de projets et de nouveaux viviers. Ce sont des
   **diagnostics de trajectoire**, pas la mesure du coût propre ni des VM totaux.
3. **Total VM réellement exécuté par OpexAI**, à même durée de jeu, obtenu
   seulement si un compteur moteur/VM exhaustif **par IA** est disponible ou
   implémenté dans un moteur de diagnostic validé. Les `GetTick` × 10 000
   incluent potentiellement du budget inutilisé (Sleep/suspension) et **ne
   remplacent pas** ce compteur.

Pour (1) et, si mesurable, (3), prendre `C = 100 × (coûtOFF−coûtON)/coûtOFF`.
Marge **±1 %** fixée à l'avance, avec IC95 calculé **par graine/pool indépendant**,
pas par les répétitions internes d'un même pool :

| Libellé opcodes | Condition sur IC de C | Sens |
|---|---|---|
| Positif | borne basse > +1 % | baisse d'opcodes démontrée et utile |
| Neutre | IC entièrement dans [−1 % ; +1 %] | coût additionnel négligeable démontré |
| Négatif | borne haute < −1 % | hausse d'opcodes démontrée et substantielle |
| Indéterminé | sinon ou compteur absent/incomplet | ne pas conclure |

Un IC sous 0 mais recouvrant −1 % sera rapporté « surcoût directionnel » ;
un IC au-dessus de 0 mais recouvrant +1 % « économie directionnelle ».
Le jugement du **total VM** doit rester `indéterminé` en l'absence de la
mesure (3), même si (1) est prouvé positif ou neutre.

## 2. Mesurer d'abord le coût propre, à travail strictement constant

Créer un **petit banc Squirrel détaché**, dans `sweeps/`/fixtures, **sans
changer les chemins de production** ni les flags par défaut. Il n'exécute
aucun investissement ni ne participe à une campagne économique.

1. Geler les **mêmes pools réels de candidats RAIL**, ordre inclus :
   `(kind, cargo, src, dst, oneWayDays, roi, profitAnnual, iterations)` et les
   champs nécessaires aux chaînes V88. Prendre des pools de périodes et
   tailles différentes (TOP20 peu rempli et saturé ; cas 20/64/200/687
   candidats), dont les graines défavorables **et des graines non sélectionnées**.
   Conserver une empreinte du contenu de chaque pool.
2. Rejouer sur chaque pool **trois formules** : OFF historique, ROI pur,
   profit/itérations. Respecter exactement les divisions **entières Squirrel**,
   les ex æquo et l'ordre original, `TOP_K=20`, `V88_CHAIN_FORCE`.
3. Chronométrer en **opcodes VM**, avec le marqueur déjà existant
   `OpexOpsMeasureBegin/End` (`budget.nut:19-30`), séparément :
   **formule**, **TOP20**, **bandes**, puis total des trois. Alternance
   ABBA/BAAB et répétitions identiques ; soustraire/calibrer le coût des
   marqueurs sur bloc vide, loguer **après** la mesure, ne pas mettre de
   `Sleep` ni commandes de construction dans le bloc.
4. Contrôle **A/A**, avec double exécution de la même formule sur le même
   tableau, des coûts compatibles au bruit de mesure et classement identique.
   Confronter les résultats d'un calcul Python de référence pour vérifier la
   justesse, sans qualifier Python de mesure d'opcodes VM.
5. Résultats : coût absolu moyen/median **par candidat, par génération**, IC
   de l'effet relatif par graine, nombre de comparaisons/insertions TOP20,
   fréquence des ex æquo et recouvrement des meilleurs candidats.
   Les répétitions d'une même entrée ne sont **pas** des graines indépendantes.

**Porte d'arrêt économique :** si ROI pur augmente significativement le coût
propre >1 %, et qu'aucun gain économique n'est démontré, arrêter sans lancer
de très gros A/B ; les gains d'opcodes intrinsèques des deux variantes
restent toutefois publiés, même quand elles sont rejetées économiquement.

**Mesure VM totale :** effectuer d'abord un audit de faisabilité moteur, puis
si nécessaire instrumenter le **compteur natif du moteur/interpréteur par
société** dans un exécutable Docker dédié et identique pour OFF/ON, en
distinguant opcodes VM réellement exécutés et ticks/suspensions inutilisés.
Contrôler en OFF/OFF que cette instrumentation ne crée pas de divergence
économique, comparer aussi le OFF natif non instrumenté. Si la faisabilité
ou la non-perturbation échoue, ne pas annoncer une économie CPU globale.

À proscrire pour des campagnes de qualification : `decision_log=1`,
`probe_loop_ops`, `probe_candidates_rail`, `probe_scheduler`,
`probe_events`, `rail_magic_shadow`. L'autopsie a montré que
`decision_log=1` change lui-même les trajectoires. `--script-debug` sans
`decision_log` a reproduit les checkpoints sur quatre graines, mais cela ne
vaut pas preuve générale d'absence de coût/opcodes ajoutés.

## 3. Séquence économique, minimale et conditionnelle

### 3.1 `simple_opcode` : économie déjà tranchée

**Pas de nouveau 40×5 et pas de 20×10.** Le 40×5 existant démontre une
régression directionnelle du profit et échoue à la garde de valeur. Classer
le coût intrinsèque via le banc (section 2) seulement ; mesurer la VM totale
uniquement si cela apporte un enseignement méthodologique réutilisable.
Ne pas réactiver en production même si le microbench prouve une économie
d'opcodes.

### 3.2 `simple_roi` : économie réellement indéterminée

**Avant de lancer des centaines de parties**, effectuer une estimation
de puissance sur les 40 deltas appariés existants. À 5 ans, l'écart-type
observé des différences est ~**228 053 £/an**, pour une marge ±**19 396 £**.
À titre d'**ordre de grandeur**, si cette dispersion et le profit OFF restent
similaires :

- ~170 graines à alpha 5 %, puissance 80 %, pour détecter un **effet non nul**
  de +49 k£ si l'effet historique demeure : ce n'est **pas** la preuve d'un
  effet utile >1 % ;
- ~450 graines pour démontrer avec une puissance voisine de 80 % un **gain
  supérieur à +1 %** si le véritable effet reste près de +49 k£ ;
- ~1 100 graines pour démontrer avec une puissance voisine de 80 % une
  **équivalence ±1 %** si l'effet véritable était exactement zéro.

Ces nombres reposent sur une approximation normale et **ne sont ni des
prévisions garanties, ni des tailles automatiquement autorisées**. Les
graines nouvelles, la variance et le nouveau bundle peuvent changer l'ordre
de grandeur ; une simulation bootstrap de puissance par graine est préférable
avant de figer le N. Un simple autre 40×5 ou un 20×10 risque fort de rester
indéterminé sur la neutralité ; il serait trompeur de l'annoncer suffisant.

Arbre de décision **proposé** :

1. Si le coût intrinsèque ROI est **négatif**, suspendre l'approfondissement
   économique en l'absence de gain démontré : **non-adoption**.
2. Si le coût intrinsèque est neutre ou positif, fixer **avant tout nouveau
   banc** un budget statistique maximal acceptable ; exemple concret :
   `N=480` **graines nouvelles appariées × 5 ans** comme plafond prospectif,
   et *un seul regard inférentiel final*. Estimer d'abord si ce N donne une
   chance crédible de conclure sur le seuil +1 %. Si le coût est jugé excessif,
   arrêter **indéterminé** sans chercher une troisième formule opportuniste.
3. Rejouer ROI OFF/ON sur **un nouveau bundle identique entre les bras**,
   sans sondes intrusives, compteur OP/OS présent et mêmes politiques tierces.
   Graines tirées **avant** l'expérience, différentes des anciennes graines
   exploratoires, et analysées **une seule fois** à l'effectif enregistré.
   Le 40×5 historique ne doit pas être combiné comme s'il avait le même bundle
   ou la même population d'étude.
4. **Seulement** si le 5 ans démontre positif ou neutre, que les gardes de
   valeur/physique passent **et** qu'aucun surcoût intrinsèque significatif
   n'est constaté : porte de généralisation **20 graines indépendantes ×
   10 ans** (minimum historique). Estimer **séparément** la puissance à
   10 ans ; augmenter le N *avant la campagne* si 20 ne peuvent répondre au
   critère, ou déclarer indéterminé. Réévaluer profit et valeur à 10 ans,
   AIR/RAIL, et coût VM total si disponible.
5. Si résultat 5 ans ou 10 ans négatif : **rejet**. Si 5 ans ou 10 ans est
   encore indéterminé à la limite de budget : **non qualifié et OFF**, pas
   « neutre ».

L'option plafonnée `N=480` n'est pas une autorisation de lancer 960 parties ;
elle illustre le coût possible d'une preuve stricte. Confirmer sa faisabilité
avant tout financement de calcul. Si deux regards adaptatifs sont préférés,
préenregistrer un contrôle d'erreur multiple/IC ajustés (pas celui par défaut
de `gain_short`) et **ne pas** s'arrêter sur des IC95 non ajustés favorables.

## 4. Contrôles communs aux campagnes de qualification

- Même bundle SHA, image/digest Docker, libs, settings et code des deux bras
  **à l'intérieur** de chaque A/B. Flags simples exclusifs, autres chantiers
  OFF, aucune modification concurrente dans le bundle gelé. Garder les
  manifests et `.jsonl`; pas de mélange de campagnes/bundles.
- Un seul Docker à la fois, jusqu'à **10 CPU / 10 workers**, tests Python hôte
  libres. Santé obligatoire de 100 % des jeux, `failed_runs=[]`, métriques
  complètes, checks de Save/Load et signes OP/OS valides ; un manque de
  couverture invalide **la mesure concernée**, pas une conversion vers zéro.
- Témoin OFF/OFF avec `--repeats 2` en C66.3, car le C66.4 rejette deux bras
  aux réglages identiques. Contrôler checkpoints économiques, véhicules,
  OP/OS et, si ajout moteur, VM natif. Séparer le contrôle de reproductibilité
  de l'échantillon économique indépendant.
- `rail_budget_sign_by_year` : snapshots annuels **cumulés**, ne jamais
  sommer les checkpoints ni soustraire à travers un Load sans détecter la
  remise à zéro. Exposer clairement les compteurs manquants et la part de
  travail différente ; ne pas appeler `observed_opcodes_total` « VM total ».
- Comparer les trajectoires par année et la première divergence via
  `sweeps/analyse_rail_opcode_first_divergence.py`, mais les dates mensuelles
  et logs ne sont **pas** des ticks VM ni une preuve de coût intrinsèque.
- Aucun seuil, score, choix de graines, horizon ou règle statistique corrigé
  **après** lecture du résultat.

## 5. Matrice de décision et ordre de priorité

| Économie | Opcodes intrinsèques | Total VM | Décision de production |
|---|---|---|---|
| Négative | Peu importe | Peu importe | **Rejet** (cas `simple_opcode`) |
| Neutre/positive | Négatifs | Peu importe | **Rejet**, surcoût propre sans justification prévue |
| Neutre/positive aux deux horizons | Neutres/positifs | Neutre/positif mesuré | **Candidat à l'adoption**, avec les gardes physiques |
| Neutre/positive | Neutre/positif | Inconnu | **Qualification VM totale incomplète** ; OFF par prudence |
| Indéterminée | Peu importe | Peu importe | **Non qualifié**, OFF ; coût de calcul supplémentaire soumis à décision |

**Ordre proposé :** (1) conserver le rejet économique de `simple_opcode`,
(2) mesurer le coût propre des **deux** variantes sur le même pool,
(3) vérifier si un vrai total VM est mesurable à coût raisonnable,
(4) estimer la puissance/effort pour qualifier `simple_roi`,
(5) seulement ensuite autoriser un gros A/B économique et son contrôle 10 ans.

Le résultat doit afficher les **nombres absolus, pourcentages, IC, couverture,
SHA et statut** de chaque axe, même si l'issue finale est `indéterminé`.
