# P0 RAIL — coût VM des gardes inéligibles, 11 octobre 2026

**Mesure obtenue : ON ajoute 15, 25 ou 40 opcodes par appel face au
court-circuit OFF, selon les trois états ci-dessous.** Cela établit un coût
local ; aucun goulot global ni effet économique sur l'AIR n'est démontré.
C69/C70 et les défauts restent inchangés ; réadmission OFF, rejet historique
maintenu. Aucun correctif de production, Docker, duel économique ou publication.

| État fixé avant mesure | Retour anticipé dans la garde | Surcoût ON−OFF par appel |
|---|---|---:|
| Pas de recherche RAIL (`_railSearch == null`) | Absence de recherche | 15 ops |
| Recherche primaire en phase `search` | Phase différente de `build` | 25 ops |
| Recherche primaire `build`, candidat présent, `isC121RailPrep=true` | Préparation C121 exclue | 40 ops |

La troisième ligne ne mesure pas l'A*, la pose ou la réadmission d'un RAIL
éligible. Un marqueur `build` dans cette fixture ne prouve aucune
constructibilité. Les états sont synthétiques ; leurs fréquences en partie
ne sont pas mesurées.

## Intervention isolée et provenance

Demande utilisateur : poursuivre la prochaine mesure proposée par
[l'autopsie historique](rail_ready_autopsy_20261011.md), puis reprendre après
clarification sur le script de test détaché. Ce script exécute uniquement
la garde copiée, sans importer OpexAI ou AAAHogEx, modèle économique,
scheduler ou commande de construction. Les appels économiques après la
garde sont remplacés par des fonctions qui lèvent une erreur s'ils sont atteints.

Source : bundle A2 du 40×5 historique
`rail_ready_readmission_diag_40x5_20261010_r1`, SHA256
`250223deaebfb849cde5717888fd2b16942de22798c1385158d4a5ad51757ff8`.
Corps complet de `task_projects.nut::_railReadyReadmissionShouldDefer`,
lignes 1562–1596 : seule la classe devient `RRGuardOwner`, corps inchangé.
SHA256 du corps original normalisé :
`42a1649f9363206713320e66e1d83b2cf563e1dc58c0c1ffbbd3bb7ec18604d9`.
Le helper du working tree est identique. L'appel ON à chaque passe projects
est aux lignes 1817–1818 ; OFF court-circuite l'appel. Les
[extraits gelés](../evidence/review/rail_ready_guard_vm_20261011/source_excerpts.json)
préservent ces références indépendamment des chantiers locaux.

Runtime natif **OpenTTD 15.3 / API NoAI 15 / OpenGFX 7.1**, archives Windows
déjà dans le cache OpenTTDLab 0.0.75, sans téléchargement. Adaptation locale
du harnais `sweeps/rail_magic_opcode_microbench.py` : empaquetage de la
fixture, répertoire/configuration temporaires, pilotes null et collecte.
Les variantes de score rejetées de ce harnais ne sont pas exécutées.
HEAD `1033239960e90064666326e92065038d22061ac8`, working tree sale préservé.

## Validité et coût mesuré

Préinscription avant chaque lancement : trois états, lots de 1/8/32 appels,
quatre répétitions avec rotation des bras EMPTY/OFFA/ON/OFFB ; **144 lignes,
36 groupes complets**. Mesure par différence de `GetOpsTillSuspend`.
Les quatre bras de chaque groupe sont sur le même tick ; aucun bloc mesuré
ne traverse un tick. Le contrôle OFFA/OFFB est exactement égal dans tous
les groupes, les retours sont tous faux et la sérialisation de l'état est
identique avant/après. Les logs sont émis après les quatre mesures.
Les répétitions ne sont pas des graines ou parties indépendantes.

L'enveloppe EMPTY et OFF coûtent exactement `12 + 10n` opcodes pour `n`
appels. ON coûte cette enveloppe plus `15n`, `25n` ou `40n` selon l'état.
Le surcoût par appel est donc constant sur les trois tailles de lot et les
quatre ordres. La marge locale préinscrite de zéro opcode n'est pas tenue :
**la garde ON inéligible n'est pas gratuite**. Cela ne teste ni une marge
d'équivalence opcode globale ni une marge économique.

Premier lancement `rail_ready_guard_vm_20261011_r1` invalide : code retour
0 mais flux capturés vides, aucune ligne RRG/DONE ; aucune valeur conservée
comme mesure. Reprise technique `r2` avec fixture, critères et tailles de lot
identiques : journalisation console native `script` et relais `developer=2`.
Les options `-x/-X` isolent configuration et recherche de fichiers. Le
[code officiel Windows](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/os/windows/win32.cpp#L101-L147)
réouvre les flux sur la console lors de `-d` ; la
[commande native de journalisation](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/console_cmds.cpp#L1167-L1186)
et le [relais debug](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/debug.cpp#L216-L248)
permettent la collecte dans un fichier. L'essai invalide est conservé ;
aucune sélection favorable de résultat ni relance économique.

Six tests ciblés du parseur passent : complétude, doublons, ticks,
contrôle A/A, mutation et cohérence du compteur. Ils ne compilent pas
Squirrel ; l'exécution NoAI complète est établie séparément par les
144 enregistrements et le marqueur final du lancement r2.

## Décision et limite causale

Le premier maillon de l'hypothèse « ON peut modifier la cadence avant une
réadmission effective » est mesuré : un appel qui ne diffère rien consomme
des opcodes supplémentaires. Pour ces seuls états, un total serait
`15 N_absent + 25 N_search + 40 N_prep` ; les trois nombres de visites
restent inconnus. Les autres chemins ne sont pas couverts par cette formule.

Ni les opcodes disponibles à l'instant de l'appel, ni le franchissement
d'une suspension par la passe réelle, ni un retard de catalogue/achat AIR
ne sont établis. Le résultat ne permet donc pas d'attribuer les divergences
AIR de 1970 ou les pertes du 40×5 à cette garde, de proposer une priorité RAIL,
de refaire le score intermodal, ou de réactiver la politique rejetée.

**Recherche dans les traces existantes terminée :** l'[audit de couverture](rail_ready_guard_exposure_20261011.md)
des 80 logs et 4 800 checkpoints ne retrouve ni les fréquences par état ni
les reliquats nécessaires. Les registres disponibles ne couvrent que les
passes productives ; aucune sauvegarde de ce corpus n'est conservée. Le
mécanisme de cadence reste non démontré. Ne pas remplacer ces données
absentes par un benchmark économique de la variante rejetée.

[Preuves, préinscriptions et vérification](../evidence/review/rail_ready_guard_vm_20261011/README.md).
Les mesures et leurs preuves sont incluses dans le commit documentaire demandé, sans push.
