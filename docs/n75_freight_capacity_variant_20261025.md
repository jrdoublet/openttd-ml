# N75-CAP — renfort fret durablement surcharge, 25 octobre 2026

## Provenance et perimetre

- Worktree exclusif : `.worktrees/nuit75-freight-capacity-variant`.
- Base avant intervention : `83e436cc3db35ff18efb685ace4f97eb569f77b1` ; arbre initial propre.
- Intervention comportementale **opt-in** : `n75_freight_capacity=0` aux quatre difficultes,
  `1` pour l'essai. **`v284_rail_growth=3` conserve aux quatre niveaux.**
- Aucune modification de `candidates.nut` ou du generateur PO01C ; aucune regeneration requise.
- Pas de Docker, banc, commit, push ou fusion dans ce worktree.

## Ce que fait le levier

V284 sait allonger un train d'un wagon si le stock instantane contient une capacite de wagon ;
il ne choisit une **deuxieme rame** que lorsque le premier train atteint le plafond du quai
et qu'une rame de stock est presente. N75-CAP ajoute un autre motif pour un second train :
**un seul train fret rentable, encore sous le plafond physique, avec au moins deux capacites de
train en attente a trois releves espaces d'au moins 60 jours, sur au moins 120 jours**.
Le moteur V284 ne fait qu'un balayage de selection par mois et sert de chemin de selection
commun ; N75-CAP y conserve des observations par `lineId`, `vehicle` et nombre de wagons.
Un stock retombant sous le seuil, un changement de rame ou plus de 120 jours sans releve
reinitialise la serie. Les observations sont des instantanes repetes, **pas une estimation de
production annuelle** ; une saturation entre deux releves peut rester invisible.

Une nouvelle rame entiere offre une capacite supplementaire meme avant le plafond du quai :
c'est une option qui **n'existe pas dans V284 au defaut** pour cette situation, et pas seulement
un filtre de priorite des wagons. Le choix N75 passe devant le candidat V284 ordinaire seulement
si tous les controles reussissent ; sinon le meilleur candidat V284 garde son chemin.

Le plafond de prix est conservateur : achat de **toute la nouvelle rame** (`loco.price +
wagons * wagon.price`) ; revenu marginal hypothetique **50 % du revenu annuel reel precedent**
de la ligne ; entretien marginal **locomotive + tous les wagons**. Le gain net attendu doit etre
strictement positif, avec une duree de remboursement brute **au plus trois ans**. Aucune valeur
de revente et aucune hausse garantie de rendement ne sont ajoutees au modele. La caisse
disponible doit payer ce cout plus 50 k£ de marge, puis la transaction existante V284
recontrole avant construction `price + OpexCashReserve() + 50 k£`. Le seuil deja en place de
**1 M£ de capital mobilisable** reste imperatif.

Le renfort reste reserve a une ligne fret a **exactement un train**, profitable, wagons
homogenes, sans rame fret secondaire V163 ni double voie, sans retrait en cours. Le choix de
locomotive preserve la vitesse de croisiere effective, la vitesse nominale et la compatibilite
avec la voie. Il exige une place de vehicule libre, un tracé V284 sans ambiguite, une boucle
de depassement validee en mode test, puis le recontrole du stock (deux capacites de rame)
et de la rentabilite avant achat. Le constructeur V284 conserve sa verification de longueur
mesuree contre le quai et `vehicle.max_train_length`. L'ancienne rame circule jusqu'a
l'adoption ; aucun retrait anticipe. `OpexV284BuildLoop`, `RollbackLoop`, `Adopt` et
`Reconcile` restent les seules transactions.

Le journal de decisions `N75CAP` expose `action=screen` (traction, marge et possibilite
de boucle), `action=pick kind=train` et **`action=done` uniquement apres le lancement
physique du train**. Les anciens `V284 action=pick/done` restent lisibles pour comparer
le bras a defaut au bras N75, en tenant compte de la provenance `N75CAP` des picks.
Le champ `n75` du pending et le suivi d'observations (`samples`, entiers uniquement)
sont sauvegardes et recharges avant `OpexLoadSettings`; le reconcile et le tick
V284 restent actifs tant qu'une transaction chargee est en cours.

## Exposition et risques de qualification

**Aucune exposition moteur n'est encore mesuree.** Le precedent diagnostic
`docs/v299_ecart_10ans_20261021.md` porte sur des parties differentes :
en 1979, **56/58** lignes fret de reference et **64/69** d'un bras de diagnostic avaient
moins d'une rame entiere en attente au releve annuel. V284 totalisait **0/0 seconds
trains termines**, et **72/87** refus de traction. N75 demande **deux** rames en attente
sur trois releves : l'exposition peut etre nulle, meme a dix ans. Il faudra compter
les couples distincts graine/ligne et les `screen`, `pick`, `done`, ainsi que la capacite
en plus, sans additionner les memes logs repetes.

N75-CAP exige **deux annees depuis le depart** et au moins un bilan annuel
profitable : avec une partie demarree en 1970, il est inerte en 1970-1971,
mais peut commencer a enregistrer une penurie en janvier 1972, et construire
au plus tot apres environ 120 jours, en 1972. V284 conserve independamment
son retard configure de trois ans. Le smoke 1×1 teste la compilation mais
ne peut pas observer la politique. Une porte A standard **40×3** peut exposer
N75 pendant la derniere annee si les sources produisent reellement deux rames
de stock repetes et que toutes les gardes passent. Si la porte A ne contient
aucun `N75CAP action=pick` ou `done`, il faut la qualifier **non exposee**,
quel que soit le bruit de trajectoire des opcodes. Le protocole `AGENTS.md`
§4 propose une porte A personnalisee **40×10** pour une politique dont
l'exposition commence trop tard ; ne pas la substituer automatiquement a la
porte A **40×3** demandee. La porte B **20×10** reste indispensable apres
une porte A admissible et valide.

Il reste un risque de couts d'opcodes : a flag 1, chaque balayage mensuel V284 relit un
petit etat de stock par ligne fret eligible ; selection de locomotive et essai de boucle
ne s'executent qu'apres trois observations positives. Le cout reel et une eventuelle
suspension moteur sont **non mesures**. L'argument de rentabilite est une heuristique
conservatrice soumise au duel, aucun benefice de profits n'est prouve.

## Validation de code et commandes de banc pour le prime

Les contrats Python controles portent sur quatre difficultes a 0, lecture unique,
ordre de chargement, delai et cadence des echantillons, chemin de deuxieme train
avant plafond de quai, relecture financiere au depot, Save/Load de la transaction
et ordonnanceur partagé avec les profils normal et sondes. Les tests statiques
ne remplacent pas un smoke NoAI ni un vrai Save/Load en jeu.

Préenregistrement propose sur 256², départ 1970, même base dans les deux bras :
référence `OpexAI[n75_freight_capacity=0]`, variante
`OpexAI[n75_freight_capacity=1]`, réglage `v284_rail_growth=3` au défaut des
deux côtés, `variant-policy-id n75cap`. Règle économique `profit_year`, garde
`company_value` de −5 %, 40×3 `gain_short` puis 20×10 `non_erosion`, avec
préenregistrement et séquence imposés par §4.1. Utiliser les 20 graines standard
de la porte B ; la porte A comprend 40 graines. Le smoke doit activer N75=1
sur une année et peut être suivi d'une exposition diagnostique prolongée
si la porte A ne permet pas de déclencher le mécanisme.


## Résultats moteur du prime — 25/10/2026

Après freeze du code : smoke graine42 1x1 sain, delta ON-OFF 0, bundle SHA256 7814fbdcfcc9a93a8dffc2b0a5b4e996ae238d134d69945f0f3dc69913c2ddcc. Diagnostic 1x10 seed100 : 0 `N75CAP screen/pick/done`, delta économique -190 538 £/an mais un seul monde ; aucune nouvelle rame N75 démontrée. Porte A `nuit75_freightcap_porteA_40x3_20261025` 40/40 paires saines, delta Opex +6 794,725 £/an, p=0,5016458, IC95 [-8 269,775 ; +23 215,575] £/an, seuil 4 % +90 301,657 £/an, company_value -1,3688 %, V/D/E 21/16/3 : verdict `fail_primary`. Manifeste A c260fe921f630a772703e3a35894d8c3900b3d280c47b948f0a9a4fe32325e9c. Aucune porte B, défaut OFF et aucun commit.

## Porte A tardive approuvée — 40×5 multimodal

Accord utilisateur du 25/10 pour A40×10 tardive puis **alternative
explicite rail 40×5 rail seul ou multimodal**. Pour N75-CAP, choix
pré-enregistré **40×5 multimodal**, sur 1970–1974 (l'amélioration
peut démarrer en 1972), afin de conserver les arbitrages de trésorerie
avec AIR/ROAD. `gain_short` : +4 % `profit_year`, p Wilcoxon exact
bilatéral <0,05, IC95 bootstrap bas >0, garde company_value −5 %.
Puis B `non_erosion` 20×10 **uniquement si A complète passe**.
Campagne lancée `nuit75_freightcap_porteA_40x5_20261025`,
bundle `7814fbdcfcc9a93a8dffc2b0a5b4e996ae238d134d69945f0f3dc69913c2ddcc`,
manifest `dd7a2c7b464079f7ca7caf87c5a8e4fa96ba81b3627e6ca5bdeec81b5585539f`,
40 graines, 80 duels, 256², 9 workers, 10 CPU/8 GiB, `probes=2`,
0/1 issu d'un même bundle, défaut 0 inchangé. Résultat non encore consolidé.
