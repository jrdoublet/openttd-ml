# Instructions communes

Lire et appliquer [AGENTS.md](AGENTS.md), notamment **§4/§4.1 — validation V102
et pilotage automatique des bancs**, actualisés le 03/10/2026.
L'état courant et les interdictions de chantier sont dans [docs/taches.md](docs/taches.md).
Le contexte métier est dans [ai/OpexAI/CLAUDE.md](ai/OpexAI/CLAUDE.md).

Ne pas se limiter à proposer un banc : le déclencher et le suivre lorsque les
prérequis du §4.1 sont réunis. Aucun changement de défaut avant qualification,
aucun commit/push/merge implicite. Si le parcours retenu est GitHub et que l'accès
ou la publication du candidat manque, signaler le blocage et conserver le défaut. Ne pas confondre succès du
workflow, ratio Opex/AAAHogEx et qualification causale A/B.

Guide GitHub : [docs/bancs_github.md](docs/bancs_github.md).

Pour une qualification comportementale : contrats → smoke 1×1 → porte A
`gain_short` 40×3 (Wilcoxon, IC95 bootstrap, gain relatif 4 %) → porte B
`non_erosion` 20×10, garde de valeur 5 % aux deux portes. Le 5×6 n'est plus
obligatoire. La règle particulière aux optimisations d'opcodes reste distincte.
Utiliser le lanceur et les options explicites du §4.1 : `signs20` reste le défaut
CLI historique. Les workflows migrés le 07/10 exposent V102 (plans de schéma 2) ;
confirmation du nouveau parcours sur Actions après publication encore requise.
