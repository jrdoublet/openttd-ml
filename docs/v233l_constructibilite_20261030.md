# V233L-CONSTRUCTIBILITE — contre-factuel physique de la seconde voie (30/10/2026)

## État et source de la question

**Prototype opt-in, non qualifié, défaut économique et défauts publics inchangés.**
Sous `estim_unifie=31`, `eb14_progressive=3`, le diagnostic
[POST-1974-ENTONNOIR](post1974_entonnoir_20261030.md) documente des offres
GOOD qui parviennent à un A* primaire sans être transformées en ligne :

| OD dirigée | Observation datée | Profit de l'offre, **prédit**, non réalisé |
|---|---|---:|
| `44972→59980` | 1978 : `NOPLAN2` et `SEARCH_ABND` | 11 819 £/an |
| `50791→7810` | sélection le 05/11/1978 ; `NOPLAN2` le 26/10/1979 | 69 478 £/an, puis 79 663 £/an réestimés |
| `50791→12090` | sélection le 10/11/1979, recherche encore en cours le 21/12/1979 | 67 822 £/an ; **issue censurée** |

Les montants sont des **prévisions**, et les `quote=-1` / `actual=-1`
historiques ne sont ni des devis nuls ni des dépenses prouvées.
Le premier tracé disponible n'établit pas que la gare, la voie, le dépôt,
les trains et les ordres sont constructibles. Aucun fichier de sauvegarde
du jour de refus n'est identifié dans les sources suivies du dépôt ;
**la reprise exacte de la carte du 26/10/1979 n'a pas été démontrée**.

## Intervention indépendante de V233L historique

Nouveau réglage `v233l_constructibilite` : `0` **OFF, défaut** aux quatre
difficultés ; `1` **contre-test passif** ; `2` **repli expérimental monovoie**.
Il n'agit que si la recherche primaire a effectivement produit une route,
que le plan obligatoire de seconde voie a échoué et que V233L marque
réellement la candidate. `ABND/NOPA` de voie 1 restent des échecs :
ce réglage ne les convertit pas en succès.

- Pour la même paire de quais et le tracé primaire, recalculer la capacité,
  la note, le tarif et le profit pour **une rame**, avec production GOOD
  observée, distance tarifaire distincte du parcours physique et amortissement
  monovoie. La formule GOOD d'âge/rétention du cargo reste appliquée ;
  les modèles deux rames historiques restent inchangés pour `v233Single=false`.
- Appeler le devis natif `OpexQuoteRailCapital` / `AITestMode` : emprises
  A/B, rails, ponts/tunnels, dépôt estimé, véhicule. Déduire coût réel
  *estimé physiquement*, capital immobilisé, profit réestimé et capacité
  mensuelle ; vérifier **profit strictement positif**, un seul train,
  trésorerie et capital disponible, slot véhicule.
- En mode 1, journaliser `V233L_CONSTRUCT` (`alternative=single`, `quote`,
  `carried`, `monthly_capacity`, `profit`, `cash`, raison et erreur native)
  **sans** modifier le candidat, la carte ni admettre la ligne :
  `NOPLAN2` reste le verdict de construction.
- En mode 2 seulement, appliquer les paramètres économiques au candidat,
  marquer son plan `v233MonoVerified`, puis **recontrôler** l'offre GOOD,
  les sites, le devis, le slot et la caisse au moment du chantier.
  Utiliser le constructeur transactionnel V190 avec une rame : les échecs
  `STNFAIL/TRKFAIL/DEPFAIL/NOTRAIN/STARTFAIL` reprennent ses chemins de
  rollback. La réussite instrumente `phase=actual outcome=build_ok` et
  le débours véritable ; elle ne garantit pas un bénéfice annuel futur.

Les objets non sérialisables du worker A* ne sont jamais rendus persistants
par le levier. `railPlan` et le marqueur sont bornés par la validité du plan
courant ; après Save/Load, une recherche A* en cours est abandonnée et
relancée conformément au mécanisme existant (`persist.nut`).

## Validation et règles de décision

`sweeps/test_v233l_constructibilite.py` couvre cinq contrats statiques :
défauts et lecture de réglage, déclencheur après A* et seconde voie,
absence de mutation en shadow, garde de rentabilité et de financement,
recalcul de la flotte et rollback/redevis. **5/5 hôtes OK le 30/10** ;
deux autres contrats V233L ciblés ont passé. Ce ne sont **pas** des
tests Squirrel en moteur ou des preuves de carte.

**Smoke en moteur obtenu** : `OpexAI[v233l_constructibilite=1]`, graine 42,
256², 1970, 1 an, OpenTTD 15.3, `run_ok`, valeur 262 389 £,
`profit_year` 341 965 £, 14 véhicules et 19 gares. Un an ne peut exposer
les `NOPLAN2` GOOD de 1978–1979 ; **aucune comparaison de profit causal**.
Le smoke a dévoilé deux anomalies du harnais Windows/Python 3.14 :
le worker `spawn` ne retrouvait pas les helpers d'un `__main__` et ne
recevait pas le chemin de checkpoint. `sweeps/bench_v2.py` importe désormais
son module canonique sur Windows et passe ce seul chemin par environnement,
sans modifier les règles du banc, les autres OS ou les simulations.

La suite V233L historique complète n'est **pas verte sur `origin/master`**
avec les défauts ESTIM31 : la fixture d'empreinte compare à des versions
antérieures, `info.nut` y est attendu à 83 réglages alors que la base
en a déjà 85, et d'autres scripts de transformation ESTIM-1 échouent.
Les divergences nouvelles et anciennes doivent être distinguées avant
toute publication économique ; ne pas réécrire les empreintes historiques.

### Protocole de qualification **à réaliser avant adoption**

1. Rejouer les trois OD dirigées **sur la même sauvegarde et à la même date**,
   avec V233L défaut double et `v233l_constructibilite=1`, confronter
   `planA/B`, chemin primaire, motif précis de voie 2, devis monovoie et
   obstacles d'AAAHogEx. La troisième OD peut rester censurée.
2. Pour chaque `quote>0`, lancer un vrai chantier mode 2 sur une **copie**,
   vérifier `RAIL_BUILD`, achat de **1** train, stations/sites/voie/ordres,
   absence d'orphelins après échec et caisse nette. Mesurer les profits
   **réalisés** après au moins un exercice complet, sans attribuer aux lignes
   nouvelles la croissance globale de compagnie.
3. Si au moins une OD perdue et profitable est réellement sauvée, figer
   **avant le banc** un protocole multi-graines 40×5 multimodal `gain_short`
   puis, seulement en cas de passe, 20×10 `non_erosion`. Relever `profit_year`
   Opex/AAAHogEx, opcodes, coût/OD unique, Wilcoxon, IC95 et capital.

**Verdict actuel : `UNQUALIFIED`**, ni GO ni NO-GO physique sur les OD
historiques. Aucune permutation du défaut, aucun profit causal revendiqué.

### Duel exploratoire terminé — une graine, 10 ans

Deux bras **complets et sains** sur la carte partagée graine 42, 256²,
1970–1979, chacun contre AAAHogEx-115, configuration par défaut hors
`v233l_constructibilite=1` (référence passif) ou `=2` (repli autorisé) :

| Mesure OpexAI, 1979 | Mode 1 passif | Mode 2 repli |
|---|---:|---:|
| `profit_year` | 3 730 271 £ | 3 300 691 £ |
| Valeur de compagnie | 16 146 874 £ | 14 460 937 £ |
| Trains et véhicules tous modes | 106 | 105 |
| Gares | 75 | 75 |

**Différence appareillée variante − référence : `−429 580 £/an`
(`profit_year`), valeur `−10,44 %`.** La garde de valeur −5 % échoue,
et la règle de profit primaire échoue aussi ; `0V/1D`, Wilcoxon `p=1`
non informatif à `n=1`, aucune IC exploitable pour une décision.
Résultats gelés :
`results/v233l_construct_seed42_1x10_20261030b.json` et manifeste associé
(résultats locaux ignorés par Git).

**Limite causale capitale :** ce banc compare deux parties issues d'une
même graine, **pas la même sauvegarde à l'instant NOPLAN2**. Les traces
disponibles ne prouvent pas qu'une monovoie supplémentaire ait été posée
ni que l'écart de profit provienne spécifiquement des trois OD ciblées.
La variante **n'est pas adoptable** au vu de ce signal négatif ; les
expériences historiques requises restent ouvertes.
