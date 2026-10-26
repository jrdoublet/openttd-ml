# V253 — moteur initial AIR évalué à N=1 puis N=2

**Préenregistrement du 26 octobre 2026, avant tout code V253.** Worktree
`results/v253_initial_engine_two_plane_stage_20261026`, branche
`v253_initial_engine_two_plane_20261026`, base `f40e4a5b`, propre au départ.
Hypothèse comportementale isolée, non requalification de V252, P3 ni V96.

## Hypothèse, bras et limites

C121 présélectionne aujourd'hui le moteur du projet à **un avion** par
`OpexC121EngineEconomics(..., fixedPlanes=1, decisionOnly=true)` dans
`OpexC121ChooseRoutePlane` ; puis seul le gagnant bénéficie du calcul
`OpexC121WinnerEconomics` (choix N=1/N=2). Un des moteurs concurrents
**déjà évalués effectivement à N=1** pourrait produire davantage de profit
annuel net à N=2, sans sacrifier le lancement et le capital. Le remplacement
du meilleur N=1 n'est jamais une preuve de gain en soi.

- **0 OFF historique** et défaut 0 dans easy, medium, hard et custom :
  scanner, tri, arrêt par `upperScore`, raccourci `C121_GE`, économie du
  gagnant et sortie de fonction rigoureusement inchangés.
- **1 SHADOW passif** : relevé de **maximum deux** moteurs proches parmi
  ceux **déjà effectivement évalués** dans le scan standard à N=1. Aucun
  calcul N=2 supplémentaire si celui-ci risque un AITestMode, une mutation
  de cache, un nouveau scan moteur, un autre choix ou une altération du
  comportement. N'écrire aucun champ décisionnel du plan, pas de sélection,
  pas de cache nouveau ; logs uniquement sous `DECISION_LOG`.
- **2 ON conservateur** : au plus **deux** moteurs alternatifs de la shortlist
  de N=1 ; pour chacun, économie C121 N=2 à données inchangées et finance
  initiale complète. Interdire nouvelle énumération/scanne de moteurs ;
  ne pas relancer une évaluation N=1 rejetée ni contourner le pruning
  `upperScore`. Un moteur alternatif ne passe que si
  `P2_alt >= 1,10 * P2_initial` (profit annuel NET de N=2),
  `P1_alt >= 0,95 * P1_initial`,
  `C_initial_alt <= 1,05 * C_initial_initial`, mêmes prix, mêmes
  réserves et trésorerie réelle suffisante. Profit et coût doivent être
  strictement positifs et les quatre résultats de profondeur valides.
  Classer les admissibles de façon déterministe par marge N=2
  descendante, puis profit N=1, puis ID moteur croissant ; une égalité au
  seuil ne force jamais un moteur ex aequo avec le témoin.
- Budget supplémentaire ON **20 000 opcodes maximum par choix**, avec
  départage et contrôle du budget à chaque étape. Une mesure *après*
  un appel N=2 ne constitue **pas** un plafond dur : l'appel peut avoir
  déjà dépensé plus de 20 000 opcodes ou suspendu le tick avant de
  rendre le contrôle. Une preuve de coût pré-borné ou un algorithme
  volontairement interruptible serait indispensable. Tout dépassement,
  changement de date/mois ou disponibilité moteur, profondeur N=2 non
  faisable, passage à un autre tick, données MAIL/route non connues,
  invalide ou ambigu : **retour au gagnant N=1 historique** sans nouvelle
  action. Aucun AITestMode ni scan géométrique, aucune nouvelle route,
  croissance de flotte, politique V252, C77, K_dec, coût, site ou seuil
  financier changé. Aucun `V96`/`C121_GE` modifié ni contourné.
- État strictement transitoire au sein d'un choix C121 : aucune persistance,
  écriture dans `Save`, cache inter-scan ou `Load` supplémentaire. Les
  données de préselection sont jetées dès le retour, y compris sur
  échec/opcodes. Respecter le contrat d'invalidation C121 existant.

## État de l'architecture et garde d'arrêt technique

1. `air_economics_c121.nut:1886-1944` évalue N=1 pour le classement ;
   il ne conserve que `best` et abandonne chaque concurrent. Une
   shortlist nouvelle serait possible **uniquement pendant ce scan déjà
   engagé**, jamais en le répétant.
2. `:1834-1877` active le raccourci `C121_GE` si moteur établi. En
   `geMode=1`, `best` est construit sans `economics`, il y a
   explicitement **zéro** évaluation des moteurs concurrents (`:1852-1860`),
   et le scan de N=1 est entièrement sauté. Le protocole impose de
   **ne pas modifier ni contourner ce raccourci** : P253 est strictement
   inactif sur ces sélections. Il existe un scan seulement avant
   établissement et lors de ses vérifications espacées de 32 choix.
3. `:1427-1464` dispose de `OpexC121OneOrTwoFused` et
   `OpexC121OneOrTwoDepth(inv, 2)`, déjà utilisés pour le seul gagnant.
   Cela **ne prouve pas** que recalculer N=2 pour deux concurrents donne
   un résultat fiable et borné à 20k : les invariants, la capacité de
   flotte, la validité des coûts et l'exécution sans suspension doivent
   être vérifiés. Le `fleetScanCap` est disponible mais n'est pas testé
   directement au début de `OpexC121OneOrTwoDepth` ; une protection
   explicite `fleetScanCap >= 2` serait indispensable avant usage P253.
4. `:1945-1963` met à jour l'état `C121_GE` après le scan et
   `:1973-2036` reconstruit N=1/N=2 pour le gagnant, puis propage un
   seul moteur. Il ne faut pas que le diagnostic ou le choix V253 modifie
   l'empreinte du raccourci, son état global ou son historique `establish`.
5. Diagnostic indépendant communiqué par le prime : sur cinq mondes
   `42/100/7/999/2026` observés pendant 5 ans, **203/203 AIR_BUILD
   utilisent le moteur 223** (44/30/42/44/43), chaque monde possédant
   un établissement C121_GE et environ 10–15 `check_ok`. Ces journaux
   **ne prouvent aucune alternative N=2 admissible** ni aucun basculement,
   sans toutefois exclure une alternative cachée dans les rares scans.

**Condition STOP avant code** : si une mesure non-mutatrice et la revue
du modèle ne peuvent garantir simultanément (i) existence d'au moins
deux moteurs *déjà évalués N=1* dans un scan normal, (ii) N=2 fiable et
finançable pour au moins un autre moteur, (iii) calcul ≤20k sans nouveau
scan ni saut du `C121_GE`, il faut rendre **NO-GO technique**, laisser
ce document seul, et ne pas écrire d'opt-in inerte ou fausse économie.

**Verdict de cette revue : NO-GO technique avant code.** Les trois
conditions ne sont pas établies sur l'architecture actuelle :
la majorité des choix dès établissement de C121_GE ne contient
**aucune** évaluation N=1 d'alternatives ; les scans intermédiaires
peuvent en contenir mais ne livrent actuellement aucune shortlist
persistée et aucune alternative N=2 viable prouvée. Même en ajoutant
une shortlist locale, `OpexC121OneOrTwoInvariants` et
`OpexC121OneOrTwoDepth(inv,2)` restent des fonctions synchrones non
interruptibles, sans plafond d'opcodes *avant l'appel* ; mesurer leurs
opcodes après retour ne garantit pas ≤20k. `OpexC121OneOrTwoDepth`
ne rejette pas non plus explicitement une profondeur 2 au-dessus du
`fleetScanCap` disponible. L'outil N=2 du gagnant historique est
réutilisable conceptuellement, mais cela **ne démontre pas** l'exposition
ni les bornes du recalcul de deux alternatives. Le 203/203 moteur 223
est descriptif et ne prouve pas qu'aucune autre motorisation pourrait
jamais gagner. Sans instrumenteur pré-borné et preuve indépendante
d'alternatives économiques admissibles issues des scans existants,
forcer l'opt-in simulerait une exposition inexistante ou casserait
C121_GE. **Aucun réglage nouveau, fichier IA ou test de comportement
modifié ; aucun smoke/banc/porte lancé**. Le défaut V252 reste inchangé.

## Exposition et portes préfixées

Après tests hôtes OFF exact, SHADOW passif, égalités, opcodes, Save/Load,
inventaires et smoke réel **1×1** sain, exposition appariée
**5 graines × 5 ans** (42, 100, 7, 999, 2026), mêmes cartes/AAAHogEx
et autres défauts. Tracer une identité stable
`AIR_ENGINE_N2_CANDIDATE` → `PROJECT_CHOSEN` → `AIR_BUILD`
(id moteur réel, N=1 et N=2, prix, marge, concurrence finançable).
**Au moins deux mondes distincts** doivent bâtir un AIR initial avec
**un autre moteur effectivement causé par ON** ; pas seulement évaluer,
mettre en shortlist ou remplacer plus tard par V252. La **somme
conservatrice des marges nettes** des projets attribuables
(`P2_alt - max(P2_baseline, meilleure option AIR/RAIL finançable)`,
tronquée à zéro) divisée par la somme des profits annuels terminaux
OFF des cinq mondes doit atteindre **4 %**. Sinon stop NO-GO exposition.

**A40×5** (40 graines, cinq ans, gain_short, 40 paires / 80 parties)
seulement après
exposition : moyenne ON−OFF `profit_year` terminal ≥ **+4 %** du
profit OFF moyen, Wilcoxon exact bilatéral p<0,05,
borne basse IC95 bootstrap (20k tirages, graine 0) **>0** et
ratio de moyennes `company_value` **≥0,95**, parties saines.
L'horizon 5 ans est choisi avant mesure pour ce comportement d'ouverture.
**B20×10** (20 graines, dix ans, non_erosion, 20 paires / 40 parties) uniquement après
A réussi : borne haute IC95 bootstrap de delta `profit_year` ≥0,
ratio de valeur ≥0,95, parties complètes et saines. Aucun réglage
ON adopté par défaut sans décision utilisateur explicite.
