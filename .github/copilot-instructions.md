# Instructions Copilot — OpenTTD-ML / OpexAI

Lire et appliquer [AGENTS.md](../AGENTS.md), consigne commune à tous les agents.
Lire l'état courant de [docs/taches.md](../docs/taches.md), seule liste autoritaire
du travail restant. Pour le code OpexAI, lire aussi
[ai/OpexAI/CLAUDE.md](../ai/OpexAI/CLAUDE.md). Préserver les modifications locales.

Pour une demande de changement de paramètre par défaut, **piloter les bancs**
selon AGENTS.md §4.1, sans attendre une nouvelle demande de lancement lorsque les
prérequis sont réunis. Depuis le 03/10/2026, le protocole comportemental V102 est
contrats → smoke 1×1 → porte A `gain_short` 40×3 → porte B `non_erosion` 20×10.
Le 5×6 n'est plus obligatoire. Utiliser `run_c66_reference.py` avec les options
explicites du §4.1 ; le défaut CLI reste `signs20` pour compatibilité.
`qualify.yml` et `bench.yml` appliquent encore l'ancien protocole et ne permettent
pas cette qualification V102 ; ne pas les recommander comme équivalents.
Les seuils, règles opcodes, contrôles de santé, provenance et décisions sont
définis dans AGENTS.md ; ne pas créer une autre règle d'adoption ici.

Ne pas changer le défaut avant qualification ; un job vert ou un pourcentage
OpexAI/AAAHogEx favorable ne suffit pas. Suivre le run exact, lire les artefacts
et consigner le verdict. Pour un parcours GitHub, sans accès authentifié, branche publiée ou quota,
signaler **bloqué/non validé** avec les paramètres prêts. Aucun commit/push/merge
implicite ; aucune campagne pour une simple édition documentaire.

Mode d'emploi : [docs/bancs_github.md](../docs/bancs_github.md).
