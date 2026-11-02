# Instructions communes

Lire et appliquer [AGENTS.md](AGENTS.md), notamment **§4/§4.1 — validation V102
et pilotage automatique des bancs**, actualisés le 03/10/2026.
L'état courant et les interdictions de chantier sont dans [docs/taches.md](docs/taches.md).
Le contexte métier est dans [ai/OpexAI/CLAUDE.md](ai/OpexAI/CLAUDE.md).

Ne pas se limiter à proposer un banc : le déclencher et le suivre lorsque les
prérequis du §4.1 sont réunis. Aucun changement de défaut avant qualification,
aucun commit/merge implicite ; le push vers `origin master` est autorisé
sans demande (règle `Bash(git push origin master*)` de `.claude/settings.json`). Si le parcours retenu est GitHub et que l'accès
ou la publication du candidat manque, signaler le blocage et conserver le défaut. Ne pas confondre succès du
workflow, ratio Opex/AAAHogEx et qualification causale A/B.

Guide GitHub : [docs/bancs_github.md](docs/bancs_github.md).

Rappels du 02/11 (détail : AGENTS.md §4.1 « Décisions du 02/11 » et §9) :
- déléguer le maximum à agy et grok, lancés directement ; ne prendre une partie
  complexe soi-même qu'après leur échec ;
- codex au plus une fois par nuit sur autorisation, sujet complexe et borné, code
  seul, **par le plugin** (agent `codex:codex-rescue`), jamais `codex exec` en Bash ;
- delta positif proche du seuil (p≈0,07-0,15) : rebanc sur 40 graines disjointes,
  agrégation par `sweeps/aggregate_paired_gates.py` ;
- nuit autorisée : porte B après A sans redemander, aucun défaut ni fusion avant le
  point du matin ;
- GitHub utilisable pour les bancs route seule (`aaahogex_settings=road_only`) ;
- vérifier que codex, grok, agy et leurs plugins sont à jour quand ils sont libres.

Pour une qualification comportementale : contrats → smoke 1×1 → porte A
`gain_short` 40×3 (Wilcoxon, IC95 bootstrap, gain relatif 4 %) → porte B
`non_erosion` 20×10, garde de valeur 5 % aux deux portes. Le 5×6 n'est plus
obligatoire. La règle particulière aux optimisations d'opcodes reste distincte.
Utiliser le lanceur et les options explicites du §4.1 : `signs20` reste le défaut
CLI historique. Les workflows migrés le 07/10 exposent V102 (plans de schéma 2) ;
confirmation du nouveau parcours sur Actions après publication encore requise.
