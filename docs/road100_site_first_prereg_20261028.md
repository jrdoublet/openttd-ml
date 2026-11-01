# ROAD100-7 — présélection de trajets passagers sur sites physiques (préréservation)

Date : 28/10/2026. Le réglage nouveau `road100_site_first=1` est **opt-in**,
par défaut **0** à toutes les difficultés ; il ne s'applique qu'au mode ROAD seul
et dépend de `road100_solo_pax=1`. Les autres variantes ROAD100 restent à zéro.

## Hypothèse et distinction de l'essai précédent

ROAD100-6 classe d'abord les paires sur la production totale des villes et
recalcule le débit sur le site seulement lors de la construction. Sur la graine
42, le débit initial de 379 pax/mois n'est que 23 pax/mois sur les deux arrêts.
ROAD100-7 doit *classer avant arbitrage* sur des arrêts physiquement éligibles,
une liaison/depot faisable, la production effectivement couverte et le profit
net revalorisé. Le résultat ne doit pas être confondu avec la quantité de lignes.

## Mécanisme borné à éprouver

- Un préfiltre classe les villes non desservies selon leur production ; les
  **18 premières** au maximum sont envisagées. Chaque origine visite **deux**
  destinations admissibles au plus ; **12 plans physiques** au maximum sont
  évalués par génération. Les gardes de distance, de paire abandonnée et de
  ville déjà desservie restent actives.
- Le planiteur existant recherche au maximum quatre sites par extrémité et
  contrôle les stations par `AITestMode`, avec au plus 64 sondes de station
  par extrémité. Pour l'opt-in, les paires de sites sont examinées en priorité
  de captation (`stopA.value + stopB.value`), puis de distance ; on conserve
  les bornes du BFS à 96 nœuds et les replis de tracé déjà en place. Pas de
  `Pathfinder.Road` ni d'exploration illimitée.
- Le capital et le profit de chaque plan viable sont recalculés avec le débit
  réellement couvert et la longueur du tracé, *avant* classement portefeuille.
  Un plan sans débit ou non rentable est rejeté. Le build refait la planification
  et ses validations de distance, débit, profit et finances, car la carte a pu
  changer depuis la génération. Une réserve d'au moins 25 k£ est exigée.
- Tracer plans essayés, construits, refus (site, plan, profit, caisse), volume
  brut et capté, véhicules prescrits, capital/profit et opcodes de présélection.
  Les sondes restent passives et ne doivent pas devenir une condition de succès.

## Qualification pré-enregistrée

1. Tests contractuels : défaut 0, exclusivité ROAD, projection OFF exacte,
   absence de changement du chemin non opt-in ; `git diff --check`.
2. Smoke apparié 1×1 graine 42, année 1970 : aucune erreur NoAI/Squirrel,
   trace d'au moins une recherche site-first valide. Une exposition n'est pas
   une preuve de profit.
3. Diagnostic apparié 5×1 sur 42, 100, 7, 999, 2026 : comparer le profit
   réalisé Opex ON/OFF, flux capté, lignes/gares/bus, garde de trésorerie,
   refus et opcodes. S'il n'y a pas de plan admissible ou si les opcodes sont
   prohibitifs, corriger ou arrêter avant toute porte coûteuse.
4. Si le diagnostic justifie la qualification, 40 graines × 5 ans sur des
   duels OFF/ON du *même bundle* contre AAAHogEx ROAD-only, carte 256² dès
   1970 et `estim_unifie=31`. Mesurer **chaque horizon** 1–5 ans ; ne déclarer
   un objectif atteint que si Opex/AAA >= 100 % à chacun. Pour le progrès
   intermédiaire : gain Opex d'au moins 4 % à l'horizon primaire,
   Wilcoxon bilatéral p<0,05, borne basse IC95 > 0 et valeur entreprise
   >= −5 % selon la règle `gain_short`. Les autres portes V102 d'adoption
   restent applicables : aucune adoption automatique sur la seule 40×5.

La référence 40×5 donne 6,0/4,8/2,6/1,7/1,4 % et la variante cadence
40×5 est `fail_primary`. Ce nouvel essai n'est pas une qualification à ce stade.

## Amendement technique après les smokes (28/10, **avant le 5×1 v3**)

Le premier smoke apparié montre 12/12 échecs `TRACEX` et 10 293 477
opcodes de planification : les paires pré-classées uniquement par villes ont
des sites distants de 86 à 197 cases, au-delà des traces L de 48 cases.
Un deuxième smoke, avec une présélection géographique trop large (64 cases
entre centres), échoue encore sur 4/4 projets, 2 524 890 opcodes et sites
distants de 56 à 63 cases.

Pour l'essai exploratoire suivant, le mécanisme devient : **40 villes**
préfiltrées ; paires de centres à **12–42 cases** ; score économique
approximatif servant à classer les *visites*, sans filtrage de rentabilité
avant mesure physique ; **6 plans maximum**, interrompus au retour d'un
plan dès que le cumul atteint **2 500 000 opcodes mesurés**. Ce dernier
plafond est vérifié *entre* plans : un plan indivisible peut le dépasser.
La variante compare au plus **3 couples de sites physiquement viables**
sur le profit net et la trésorerie. Les contraintes d'origine, de site et de
revalidation au chantier sont conservées.

Cet ajustement d'exposition n'est pas une règle de qualification rétroactive :
chaque smoke a son propre bundle, et le 5×1 ne permet aucun verdict
d'adoption. Les résultats et les motifs figurent dans
`road100_site_first_resultats_20261028.md`.
