# Correction C121 dans les trois états — plan du 07/10

Demande utilisateur : activer la correction adaptative dans les trois états
`observe`, `race`, `efficiency`, et expliquer C122 désactivé. « Trois modes » est
interprété selon l'échange précédent comme ces états, pas comme newpair/hubsite/hubhub.
Le facteur appris reste distinct par type de ligne ; correction des hubs à 25 %
de l'écart appris, minimum d'observations inchangé, aucune pénalité sans données.

## Intervention et validation pré-enregistrées

Arbre local master, HEAD 208792eb8c7ddd315108e1d1fca6ad1df76408a8, modifications
locales préexistantes conservées ; sources et harnais figés avant chaque étape.
La garde de régime dans `OpexC121RealizationFactor` est levée directement ; le
réglage adaptatif existant reste le seul interrupteur et son défaut reste 1.
Pas de nouvel état durable : configuration relue par OpexLoadSettings,
facteurs reconstruits par OpexC121RecomputeRealizationFactors depuis les champs
de lignes persistants existants ; verrou de régime et sérialisation inchangés.
La correction ne change ni la formule ni les types de lignes couverts.

La comparaison causale et la qualification économique sont différées : aucune
nouvelle campagne n'est lancée dans cette finition. C115=1 reste commun ; aucun
passage global à C121 n'est effectué par ce changement.

Le smoke technique préparé avant cette simplification est conservé dans les
résultats ignorés ; il ne constitue pas une qualification de cette version finale.

## Pourquoi C122 priorité reste à zéro

Le journal du 29/09 documente les versions dégradantes initiales, puis un contrôle
à instrumentation comparable : zéro promotion réelle après verrouillage, confirmé
par le shadow exact. Ce n'est pas un oubli de réglage. Les sources historiques
manquantes signalées dans taches.md limitent toute revalidation des chiffres ;
on conserve la décision documentée, sans présenter ces smokes comme qualification
économique. C122 ne forme aucune paire nouvelle et n'agit qu'entre candidats AIR
de même tier C77 ; il ne répond donc pas au défaut de génération décrit ici.

## Rapport fourni sur les paires AAA : piste distincte

L'utilisateur apporte des comparaisons à 5 ans et un croisement à 3 ans entre
campagnes différentes : conserver leur limite de causalité. Les parts de motifs
fournies totalisent 104 % ; les catégories ne doivent pas être présentées comme
une partition exclusive sans retour aux identifiants de lignes et dénominateurs.
Les chiffres sont du contexte fourni, pas de nouvelles mesures sur notre B.

Le code courant filtre effectivement pax_band puis AIR_MAX_DISTANCE pour newpair,
hubsite et hubhub. La prochaine mesure utile est le suivi de la même paire depuis
vivier→distance→économie→portefeuille→construction, avec identifiants des villes,
distance utilisée par chaque filtre et degré de chaque aéroport. Une limite par
aéroport et des paires longues entre villes non hubs sont des interventions
distinctes à isoler, sans changer population, courrier ou élargir globalement le
vivier. V93 ne réfute pas universellement tout nouvel aéroport : il réfute les
interventions mesurées, notamment l'élargissement via la population. Aucune
activation simultanée de ces pistes ne contaminerait la comparaison ci-dessus.
