# Instructions Copilot — OpenTTD-ML / OpexAI

Lire et appliquer [AGENTS.md](../AGENTS.md), consigne commune à tous les agents.
Lire l'état courant de [docs/taches.md](../docs/taches.md), seule liste autoritaire
du travail restant. Pour le code OpexAI, lire aussi
[ai/OpexAI/CLAUDE.md](../ai/OpexAI/CLAUDE.md). Préserver les modifications locales.

Pour une demande de changement de paramètre par défaut, **piloter les bancs**
selon AGENTS.md §4.1, sans attendre une nouvelle demande de lancement lorsque les
prérequis sont réunis. Préférer `qualify.yml` avec un plan pré-enregistré dans
`qualifications/` : contrats, smoke, diagnostic et adoption après les portes.
`bench.yml` reste le parcours manuel A/B `paired` à profils successifs.
Les seuils, règles opcodes, contrôles de santé, provenance et décisions sont
définis dans AGENTS.md ; ne pas créer une autre règle d'adoption ici.

Ne pas changer le défaut avant qualification ; un job vert ou un pourcentage
OpexAI/AAAHogEx favorable ne suffit pas. Suivre le run exact, lire les artefacts
et consigner le verdict. Sans accès GitHub authentifié, branche publiée ou quota,
signaler **bloqué/non validé** avec les paramètres prêts. Aucun commit/push/merge
implicite ; aucune campagne pour une simple édition documentaire.

Mode d'emploi : [docs/bancs_github.md](../docs/bancs_github.md).