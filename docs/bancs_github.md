# Bancs OpenTTD directement sur GitHub

## Premier lancement depuis le navigateur

1. Publier le workflow **et ses scripts** sur GitHub. Le fichier
   `.github/workflows/bench.yml` doit être présent sur la **branche par défaut**
   pour que GitHub propose le déclenchement manuel. Cette copie locale provient
   d'une archive sans Git : rien n'a été publié automatiquement.
2. Ouvrir le dépôt → **Actions** → **Bancs OpenTTD** → **Run workflow**.
3. Choisir la branche à tester (elle doit également contenir ces fichiers).
4. Pour le premier essai, garder **mode = solo**, **profile = smoke**,
   **reference = OpexAI**, les champs facultatifs vides et la télémétrie décochée.
5. Lancer, suivre le job, puis télécharger le ZIP sous **Artifacts** dans la page
   du run. Le résumé indique le protocole et le statut disponible.

Il faut les droits permettant de déclencher Actions, et Actions doit être activé
dans le dépôt. Aucun secret spécifique, OpenTTDLab, Python ou Docker n'est requis
sur le PC. **Les changements locaux non publiés ne sont pas testés.**

## Protocole courant et limite des workflows (03/10/2026)

La validation comportementale courante suit **V102**, définie dans
[AGENTS.md §4/§4.1](../AGENTS.md#4-validation-proportionnée-puis-adoption) : contrats,
smoke 1×1, porte A `gain_short` **40×3** (Wilcoxon exact p<0,05, borne basse
IC95 bootstrap >0, gain moyen ≥4 % du profit de référence terminal), puis porte B
`non_erosion` **20×10** (borne haute IC95 bootstrap ≥0). Garde de valeur −5 %
aux deux portes ; le 5×6 n'est plus obligatoire. La règle opcodes reste distincte.

**`bench.yml` et `qualify.yml` ne sont pas encore compatibles avec V102.**
`github_bench.py` impose `signs20` et au plus 20 graines ; `qualification.py`
vérifie l'ancienne règle +50 k£/15 victoires après un diagnostic 5×6. Ni un profil
`custom` trois ans, ni `paired/adoption`, ni un plan JSON de schéma 1 ne suffisent.
Utiliser `sweeps/run_c66_reference.py` avec les options explicites du §4.1 ; si
ce runtime manque, signaler l'absence de chemin V102 disponible. La migration est
suivie dans `taches.md`, sans substitution silencieuse de l'ancien protocole.

Les modes, champs et commandes GitHub ci-dessous décrivent leurs capacités
actuelles pour les smokes, diagnostics et protocoles historiques.

## Modes et profils

| Mode | Parties exécutées |
|---|---|
| `solo` | OpexAI seule, via `smoke_test.py`, avec contrôles de plausibilité |
| `duel` | OpexAI contre AAAHogEx sur chaque carte partagée |
| `paired` | Deux parties par graine : référence contre AAA, puis variante contre le même AAA |

| Profil | Graines / durée | Usage |
|---|---|---|
| `smoke` | 42 × 1 an | Compilation/exécution et premier test du workflow |
| `diagnostic` | 42, 100, 999, 1234, 5678 × 6 ans | Diagnostic, pas adoption |
| `adoption` | 20 graines canoniques du harnais × 10 ans | `paired` obligatoire ; 40 parties |
| `custom` | Champs `years` et `seeds` obligatoires | 1–10 ans, 1–20 graines uniques |

Les champs `years` et `seeds` restent **vides** hors profil `custom` ; ils ne sont
pas ignorés silencieusement. `seeds` accepte espaces ou virgules. Les graines
doivent être des entiers non signés sur 32 bits. La règle statistique reste
`signs20` ; ce workflow ne propose ni `mean40`, ni `gain_short`, ni `non_erosion`.

Le solo utilise toujours le harnais de smoke : même en 5×6, il ne constitue
ni un duel, ni une preuve causale comparative, ni un bundle C66 gelé.

## Exemple : duel de trois ans et pourcentage de profit

Dans **Run workflow**, saisir :

| Champ | Valeur |
|---|---|
| `mode` | `duel` |
| `profile` | `custom` |
| `reference` | `OpexAI` |
| `variant` | vide |
| `years` | `3` |
| `seeds` | `42 100 999 1234 5678` (ou `42` pour une seule partie) |

Le résumé GitHub et `summary.md` présentent les profits annuels des deux IA,
le **% OpexAI / AAAHogEx par graine**, puis le **ratio global des sommes** :
`100 × somme(profit OpexAI) / somme(profit AAAHogEx)`. Ce n'est pas la moyenne
des pourcentages. **80 %** signifie 20 % de profit de moins qu'AAAHogEx ;
**120 %** signifie 20 % de plus. Les données figurent aussi dans `profit-ratios.json`.

Il s'agit de `profit_year` au dernier checkpoint : **les quatre derniers trimestres
clos**, pas du profit cumulé sur les trois ans. Le rapport ne somme pas les
photographies mensuelles (elles se recouvrent). Une partie absente, un doublon,
une santé invalide ou une couverture annuelle incomplète donne `n/d`, pas zéro.
Un profit AAA nul/négatif ne reçoit pas de pourcentage ; une perte Opex reste
visible. Le ratio global n'est publié que si toutes les graines sont exploitables
et sans échec de campagne, jamais sur le seul sous-ensemble favorable.
En A/B, chaque politique reçoit son tableau séparé. Ce duel 3 ans via le workflow
reste diagnostique ; il ne constitue pas la porte A V102 du lanceur hôte.

## Paramètres A/B

- **reference** : `OpexAI` (défauts de la branche), ou une politique explicite
  de la forme `OpexAI[reglage=0,autre=1]`.
- **variant** : obligatoire uniquement pour `paired`, avec réglages explicites
  `OpexAI[reglage=1]`. Pas d'espace dans le bloc. Le harnais valide noms, bornes
  et différences effectives ; changer un réglage déjà au défaut n'est pas une
  variante. Aucun défaut de l'IA n'est modifié par le workflow.
- **min_delta** : effet minimal utile de `profit_year`, défaut **50 000 £/an**.
- **value_guard** : perte maximale de valeur acceptée, défaut **5 %**.
- **line_telemetry** : uniquement duel/paired ; ajoute la télémétrie annuelle
  par ligne, avec davantage de données et de temps de traitement.

Exemple de syntaxe, **pas recommandation d'adoption** : mode `paired`, profil
`smoke`, référence `OpexAI`, variante `OpexAI[c80_worker_rail=1]` si ce réglage
est bien expérimental à 0 sur la branche étudiée. Choisir le levier effectivement
autorisé avant de passer au diagnostic. Respecter les décisions de `docs/taches.md`.

Les deux politiques partagent le **même code publié** et diffèrent par leurs
réglages ; ce formulaire ne compare pas deux commits. Les seuils sont enregistrés
avant les parties. Un smoke ou un diagnostic favorable ne devient pas une adoption.

## Runtime et provenance

- Runner GitHub hébergé **Ubuntu 24.04**, Python **3.12** ; cible Docker
  `simulation`, sans dépendances ML. Le build Docker habituel sans cible conserve ML.
- OpenTTD **15.3**, OpenGFX **7.1**, OpenTTDLab **0.0.75**, fournis sur GitHub.
- AAAHogEx **115**, archive officielle BaNaNaS immuable, SHA-256 vérifié avant
  extraction ; sources et licence GPLv3 conservées. Aucun dossier VPS nécessaire.
  L'identité avec une éventuelle copie VPS modifiée n'est pas présumée.
- Duels via `run_c66_reference.py` : manifeste, copies figées, empreintes, Git
  et ID exact de l'image. Bibliothèques résolues puis conservées dans le bundle.
- Deux workers ; Docker plafonné à **3 CPU, 2 Go, sans swap**, volume
  `openttd-lab-home:/home/lab`, montage du dépôt sous `/work`.
- Cache des couches de construction GitHub ; volume `/home/lab` neuf par job.
  Pas de restauration des paquets Python d'une ancienne image depuis ce volume.
  Les téléchargements moteur/contenus ne sont pas mis en cache entre ces jobs.

## Lire et conserver les résultats

Chaque tentative écrit dans `results/gha-<run_id>-<run_attempt>/`, sans écrasement.
Le ZIP, conservé **30 jours** sous réserve de la politique du dépôt, contient :

- `request.json`, `summary.md`, `console.log`, logs de préparation et identité Git/runner/image ;
- `bench.json` : rapport final ; `bench.jsonl` : checkpoints collectés ;
- en duel/paired : `opponent.json`, `bench.manifest.json`, `bench_bundle/`,
  `bench_engine/` (journaux moteur par partie).

Un échec conserve les fichiers disponibles. Une interruption brutale du runner
peut empêcher l'upload ; un ZIP partiel n'est pas un banc complet. Les `.sav`
ne sont pas conservés. Télécharger les preuves avant expiration ; leur promotion
dans `evidence/review/` reste explicite.

**Job vert ≠ adoption.** Le job transmet les erreurs techniques du harnais.
Un verdict économique `fail_primary` ou `fail_value_guard` peut laisser le job
vert : la simulation a réussi, pas le traitement. Lire `policy_comparison.verdict`,
la couverture, la santé, les deltas et garde-fous dans `bench.json`.
`diagnostic_only` ne permet pas l'adoption ; aucun réglage n'est promu automatiquement.

## Temps, coût et limites

Simulation limitée à **300 minutes**, job à **360 minutes**, pour laisser du
temps aux artefacts. Aucun engagement de durée pour un 20×10 : commencer par
un smoke avant les campagnes autorisées. Timeout moteur duel : 1 800 secondes par partie.
Coûts et quotas dépendent du dépôt et du runner. Aucune reprise automatique.

Un lancement sur la même branche attend le banc en cours au lieu de l'annuler.
GitHub peut remplacer un run encore en attente par un nouveau run : ce n'est
pas une file durable de campagnes. Éviter les lancements répétés.

L'ancien bouton CI `run_full_bench` (solo 20×3, adversaire local manquant) est
remplacé. La **CI** automatique garde son smoke 3×2, teste l'orchestration et
publie désormais JSON, JSONL et log console pendant 14 jours.

## Pilotage par un agent LLM

La consigne commune est **AGENTS.md §4.1**, relayée dans `CLAUDE.md`,
`ai/OpexAI/CLAUDE.md` et `.github/copilot-instructions.md`. Pour une demande de
changement de défaut, l'agent enchaîne les étapes autorisées sans nouvelle demande
de lancement. Sur GitHub, cela exige candidat publié, accès/quota disponibles et
workflow compatible avec le protocole demandé ; V102 reste à migrer.
Il ne publie pas le code implicitement et ne déclenche rien pour une édition documentaire.

Avec GitHub CLI authentifié, les opérations à utiliser sont `gh auth status`,
`gh workflow run bench.yml --repo <owner/repo> --ref <branche>` avec tous les inputs
du plan via `--json` (ou arguments `-f` séparés), puis identification du run par
workflow/branche/SHA/heure/acteur et vérification de `request.json`. En cas d'ambiguïté,
ne pas choisir arbitrairement le run le plus récent et ne pas relancer en double.
Suivre l'ID exact avec `gh run watch <run-id> --repo <owner/repo> --exit-status`,
puis récupérer les artefacts avec `gh run download <run-id> --repo <owner/repo> --dir <dossier-neuf>`.
Un outil/API GitHub authentifié équivalent convient. Ne pas insérer des paramètres
libres dans une commande shell évaluée ; ne jamais afficher les credentials.

Le code 0 de `gh run watch` ne prouve pas l'adoption : analyser ensuite `bench.json`
selon le §4.1. Conserver SHA, ID, URL, tentative et inputs de chaque étape dans le
journal. Aucune boucle de relances sur résultat économique négatif. Les arrêts ou
quotas dépassés donnent « non validé », pas un défaut promu sans preuve.

### Enchaînement autonome historique après déclenchement (hors V102)

Le workflow distinct **Qualification de défaut OpenTTD** (`qualify.yml`) prend
un seul input `plan=qualifications/<chantier>.json`, publié sur la branche testée.
Il exécute les contrats pré-enregistrés, puis **smoke → diagnostic → adoption**,
avec arrêt à la première porte échouée, preuve manquante ou budget dépassé.
Le même run relie toutes les étapes, sur un SHA et une image uniques.

Le validateur publie `ACCEPTÉ`, `REFUSÉ` ou `NON_VALIDÉ`, conserve le verdict brut,
recalcule les critères économiques et traite séparément la neutralité opcodes.
Un `POURSUIVRE` intermédiaire ne vaut pas acceptation. Ni modification de défaut,
ni commit/push/merge ne sont effectués. Le ratio Opex/AAA reste descriptif.

Préparation du JSON, contrat de preuve d'exposition/opcodes, budget total
1..270 minutes et limites : **[guide des plans](../qualifications/README.md)**.
Pas de compteur d'exposition disponible → non validé, sans inventer une preuve.
Le workflow n'interprète pas les interdictions métier de `docs/taches.md` : elles
doivent être contrôlées avant le dispatch, ainsi que les doublons et le quota.

Le formulaire `bench.yml` reste inchangé pour les bancs isolés et les duels 3 ans ;
il n'enchaîne pas les étapes et n'encode pas la neutralité opcodes. Le nouveau
workflow ne s'auto-déclenche pas sur chaque push. La publication et les premiers
contrôles sont pris comme prérequis supposés satisfaits pour poursuivre ce lot,
conformément à la demande utilisateur ; aucune exécution économique n'en est déduite.

## Validation de cette livraison

Workflows vérifiés avec **actionlint 1.7.12**, sans ShellCheck/Pyflakes locaux ;
diagnostics éditeur sans erreur. Archive officielle téléchargée et vérifiée
(SHA-256, structure, version, licence). **42 tests unittest** ajoutés (dont six
sur les ratios de profits), programmés
dans les workflows avant les parties, mais **non exécutés sur ce PC** faute
d'environnement Python utilisable. Aucun run Actions ni smoke moteur lancé :
les premiers `solo / smoke`, puis `duel / smoke`, restent à réussir sur GitHub
après publication pour valider l'intégration réelle.

**Lot suivant — qualification automatique :** validateur et fixtures synthétiques
dans `sweeps/qualification.py` / `sweeps/test_qualification.py`, séquence dans
`sweeps/github_qualification.py`, workflow `qualify.yml`. Les contrôles du paragraphe
précédent concernent la première livraison, pas une exécution de cette séquence.
Les deux workflows modifiés de ce lot passent **actionlint 1.7.12** (sans
ShellCheck/Pyflakes). **27 méthodes de test synthétiques** ajoutées, également
programmées dans `benchmark-regressions.yml`. Tests Python et parties de ce nouveau lot non exécutés localement (aucun Python
de base utilisable). Aucun défaut IA modifié et aucune campagne lancée.
