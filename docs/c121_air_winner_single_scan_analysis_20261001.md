# AIR — analyse de la piste 2 : ouverture et scan du gagnant

## Conclusion et périmètre

Le doublon est réel. À **entrées identiques**, l'ouverture N=1 et le point N=1
du scan complet calculent la même économie. Deux interventions sont possibles :
un raccourci pour `fleetScanCap=1`, puis une fusion générale conservant le
résultat d'ouverture pendant le scan. L'équivalence en VM et le gain net restent
à mesurer ; aucun code de production ni réglage n'est modifié dans cette analyse.

La numérotation « piste 2 » renvoie au tableau de priorités de la réponse dans
le chat. Elle correspond à la section « Mutualiser l'ouverture et la flotte »
de la [revue initiale](c121_air_portfolio_optimizations_20261001.md).
La réduction des grands snapshots, le contexte partagé avec les autres avions,
les hubs et les décisions de profondeur sont des lots distincts.

Arbre relu le 1er octobre : branche `c121-catalog`, HEAD
`52ab55537dcf18a0ded8700bc9ac73833ac369a5`, modifications locales préexistantes.
Empreintes SHA256 des sources étudiées :

- `air_economics_c121.nut` : `0157e8df026bf2490c6d7784a4ae69ff250eaca1fca1be39e6c31d8e39a04e37` ;
- `air_catalog_c121.nut` : `6b734eba774ee7999cb0538d8a4d059256573c8218f3afa9216794770ef62aef` ;
- `projects_builders.nut` : `d35d2b127a78e1d7e672114469469b98a9d0acf010d46b0fcdbf9a97bf54f210`.

Le [suivi courant](taches.md) rejette les variantes decision-depth,
portfolio-depth et portfolio-split. Cette piste conserve les résultats du modèle
et ses départages ; elle n'optimise pas une nouvelle profondeur économique et
ne réactive aucune variante. C115 reste protégé, aucun 20×10 C121.

## Chemin courant et duplication

Après la sélection de l'avion, `OpexC121ChooseRoutePlane` appelle, aux lignes
1181–1182 de la source étudiée :

```squirrel
initialEconomics = OpexC121EngineEconomics(..., C121_AAA_LINE ? 2 : 1, false);
fullBest = OpexC121EngineEconomics(..., 0, false);
```

Le premier appel ne calcule que N_initial. Le second recalcule tous les N de 1
à `fleetScanCap`. Le scan complet n'applique pas l'arrêt sur borne de score :
ce raccourci est conditionné par `decisionOnly` (ligne 906), ici faux.

Chaque appel relit les capacités connues, prépare le cycle et les tarifs,
calcule les bases de rating/coûts, puis traite les N demandés. Pour N=1, le
traitement répété comprend partage de piste, ratings PASS/MAIL, allocation de
production, capacités directionnelles, externalités, revenus, amortissement,
capital, ROI et score. Le corps du scan ne fait pas de lecture directe d'API ;
les helpers appelés emploient les données déjà préparées. Le lot peut conserver
les mêmes opérations et le même ordre des conversions.

**Le scan compact de sélection moteur ne fournit pas un résultat d'ouverture
réutilisable tel quel.** Il manque des champs ; la correction engine-realization
ne s'applique qu'au chemin `decisionOnly`, et les variantes portefeuille peuvent
utiliser un autre score lorsque `decisionOnly=false`.

## Contrat des résultats à préserver

| Résultat | Origine et rôle | Contrainte de la fusion |
|---|---|---|
| `economics` | Appel à N_initial ; achat et budget immédiatement constructibles | Reste à N_initial, avec ses propres champs `decision*` |
| `fullBest` | Meilleur profit sur 1..cap ; égalité départagée au ROI | Même N, mêmes champs, même choix en cas d'égalité |
| `fullBest.decisionEconomics` | Meilleur score sur 1..cap | Même départage profit, ou revenu sous les variantes portefeuille locales |
| `decisionEconomics` du choix | `fullBest` ou sa profondeur interne selon les flags | Conserver le branchement courant |
| `portfolioEconomics` | Profondeur interne exposée par le split local | Conserver le branchement courant, sans activation du split |
| `targetPlanes` du choix | `initialEconomics.planes` | Ne pas le remplacer par la flotte de croisière |

Un piège important : même si le meilleur profit final est à N=1, ses champs
`decisionPlanes`, `decisionProfitAnnual`, etc. peuvent décrire N=2 ou davantage.
L'ouverture indépendante doit, elle, conserver sa décision à N=1. Copier le
résultat **après** la finalisation globale ne suffit donc pas au cas général.

La finalisation du modèle ajoute les champs `decision*` et le résultat imbriqué
à partir de `scoreBest` (lignes 932–964). `fleetEvaluated` appartient au résultat
de score imbriqué : il vaut 1 pour l'ouverture fixe, et cap pour ce scan complet.
`fleetBoundPruned` vaut faux dans ces deux chemins complets. Le wrapper ajoute
`engineMailKnown` aux deux niveaux. Ne pas le confondre avec `mailKnown` : une
capacité MAIL exacte connue égale à zéro donne true pour le premier et false
pour le second.

Les objets d'ouverture et de croisière sont actuellement indépendants. Le
cache catalogue conserve le choix entier ; conserver cette indépendance ainsi
que celle des objets imbriqués. Aucun nouveau cache persistant n'est nécessaire.
Le calcul post-build (`OpexC121MeasureBuiltEconomics`) utilise les nouvelles
capacités observées : il reste hors de cette mutualisation.

## Intervention A — raccourci borné, cap égal à 1

Condition minimale : `!C121_AAA_LINE`, ouverture non nulle, `fleetScanCap==1`
et préparation économique toujours valide. À entrées figées, les deux appels
complets évaluent alors exactement N=1 et finalisent avec les mêmes compteurs.

Après l'appel d'ouverture, produire une copie distincte pour `fullBest`, en
copiant aussi sa `decisionEconomics`. Les snapshots du corps ont actuellement
94 champs pour le score, 93 pour le profit ; ils sont scalaires avant cet ajout
imbriqué. Une copie seulement superficielle du résultat final partagerait la
table `decisionEconomics` et ne respecte pas l'indépendance du témoin.

Pour tout autre cap, garder les deux appels courants. Garder également le
chemin courant pour `C121_AAA_LINE` : une ouverture à deux avions avec cap=1
n'est pas l'économie N=1 du scan. Aucun traitement spécial des autres variantes
de score n'est requis mathématiquement dans le cas cap=1 ; leur compatibilité
doit néanmoins être exercée en fixture, sans les activer dans une campagne.

Avantage : intervention étroite, pas de changement du domaine 1..cap et pas
de refactoring du noyau par N. Limite : gain proportionnel à la fréquence des
caps égaux à 1, inconnue dans les chiffres transmis par le VPS.

## Intervention B — un scan complet avec capture de l'ouverture

Pour N_initial=1, préparer l'économie une fois, traiter 1..cap dans le même
ordre, et capturer les deux snapshots locaux du point N=1 **avant** leur
annotation avec les argmax globaux. Finaliser des copies indépendantes comme
un appel fixe : décision à N=1, un point évalué, même connaissance PASS/MAIL.
Continuer le scan avec les mêmes critères et finaliser ses propres résultats.

Une sortie optionnelle passée explicitement au noyau/wrapper permettrait de
récupérer l'ouverture sans ajouter de champ interne au résultat économique
public ou au snapshot du catalogue. Le wrapper doit annoter la connaissance
des capacités dans les deux résultats. Tout helper de finalisation reçoit ses
arguments explicitement, conformément au piège de portée de `docs/methode.md`.

Premier périmètre proposé : conserver le chemin à deux appels pour
`C121_AAA_LINE`. Une extension ultérieure N_initial=2 devra couvrir cap<2 sans
faire participer N=2 aux argmax d'un scan dont le domaine témoin est seulement
1..cap. Élargir silencieusement la borne à 2 changerait le modèle.

Ne pas profiter de cette fusion pour compacter tous les snapshots, ajouter un
élagage ou modifier la sélection moteur : leur coût et leur effet se mesurent
dans des lots séparés. Les sorties nulles et le repli `fullBest=initialEconomics`
doivent garder le comportement du chooser courant.

## Fraîcheur des entrées et portée de l'équivalence

Les invariants de paire sont déjà préparés, mais les deux appels relisent des
tarifs au moteur. OpenTTD 15.3 fait appeler `GetTransportedGoodsIncome` par
`GetCargoIncome`, et le calcul standard dépend de `CargoSpec::current_payment`.
Son horloge mensuelle applique l'inflation et relance `RecomputePrices` quand
elle est active. Une suspension traversant cette frontière peut donc rendre
les deux préparations différentes : l'équivalence à entrées figées ne prouve
pas qu'elles étaient toujours identiques en jeu.
[API cargo 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_cargo.cpp#L64),
[économie 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/economy.cpp#L892),
[mise à jour mensuelle](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/economy.cpp#L1809).

Le prototype doit tester cette frontière et prévoir la relecture/repli quand
la préparation a vieilli ; un simple cache global par moteur serait inadéquat.
Le profil de carte réellement figé dira aussi si l'inflation y est active.
Les autres gardes couvrent la configuration de cinématique et les capacités
connues. Même avec ces gardes, moins d'opcodes change le calendrier de jeu :
la neutralité économique ne découle pas de l'équivalence des formules.

## Gain à mesurer et portes de validation

Pour une ouverture N=1 et cap=m, le témoin traite m+1 points de flotte, la
fusion m. La réduction suivante concerne **le nombre de traitements par N**,
pas le total des opcodes ; elle exclut préparation, allocations et copies :

| cap | Témoin | Fusion | Un traitement supprimé |
|---:|---:|---:|---:|
| 1 | 2 | 1 | 50 % |
| 2 | 3 | 2 | 33,3 % |
| 5 | 6 | 5 | 16,7 % |
| 10 | 11 | 10 | 9,1 % |

La fusion supprime aussi une préparation complète du gagnant, mais conserve
le scan moteur compact et tous les N utiles de croisière. Les **3,2 M** cités
sur le VPS sont le coût du poste entier, pas le coût supprimable par ce lot.
Les copies et gardes doivent être déduites du gain brut.

Ordre proposé pour la suite :

1. **Exposition** : distribution de `fleetScanCap` des gagnants effectivement
   recalculés, séparée newpair/hubsite/hubhub et PASS-only/PASS+MAIL. Ne pas la
   déduire seulement des builds : ce sont des candidats sélectionnés et leurs
   capacités post-build peuvent différer. Choisir A ou B après cette mesure.
2. **Fixture NoAI** : ancien double appel contre candidat, mêmes entrées,
   comparaison récursive des clés, types et valeurs de l'ouverture, du résultat
   complet et de leurs objets de décision. Caps 1/2/élevé, optimum initial ou
   tardif, égalités, demande asymétrique, concurrence/piste, MAIL inconnu/connu
   nul/positif, facteurs de réalisation, flags depth/split et repli nul.
   Tester les mutations entre objets, AAA_LINE et la frontière tarifaire.
3. **Coût VM** : comparer préparation, traitement N=1, reste du scan et
   copies/gardes ; mêmes entrées et instrumentation, mesure hors initialisation
   des fixtures. Les tests Python textuels des deux appels devront être adaptés
   au contrat de sortie ; ils ne mesurent ni Squirrel ni ses opcodes.
4. **Intégration** : smoke 1×1 de la seule optimisation, puis comparaison avec
   les compteurs existants `c121_winner_ops` sur les graines 42/100. Sources et
   bras figés, conditions Docker du dépôt. Un chemin témoin isolé reste requis.
   Aucune partie n'a été lancée pour cette analyse ; aucun défaut n'est adopté.

**Complément moteur :** [fixture et exposition](c121_air_winner_fixture_20261001.md)
exécutées sur 42/100 × 1 an. 72 cas dirigés validés par graine pour le
raccourci cap=1, mais zéro cap=1 parmi 2 289 recalculs naturels : ne pas
intégrer ce raccourci seul. La prochaine livraison est la fixture de fusion
générale aux caps naturels, avant toute intégration. Aucun gain catalogue ni
code de production n'est qualifié.
