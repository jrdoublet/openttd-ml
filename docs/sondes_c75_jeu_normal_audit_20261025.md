# C75 — audit de la télémétrie résiduelle en jeu normal

**25 octobre 2026 — lecture des sources du master, aucun code IA modifié.**

L'état C75 n'est pas entièrement une sonde : les dates de passes
`C75_PASS_DATES` sont enregistrées et élaguées par
`OpexC75RecordPassDate` (`probes.nut:1904-1925`), puis utilisées par
`OpexC75ComputeKPass` (`:1927-1969`) pour calculer `K_pass`, qui sert
à la décision de construire. `task_projects.nut:1023-1027` appelle ces
fonctions même avec `probes=0`. **Ne pas les désactiver.**

À l'inverse, `C75_YEAR_LEDGER` ne stocke que `passes`, `builds` et
`multi_passes` (`probes.nut:1971-1979`). Il est initialisé par
`settings.nut:345-347` et `main.nut:716-719` et incrémenté dans
`task_projects.nut:1027` et `OpexC75RecordPassOutcome`
(`probes.nut:2117-2125`). Ses consommateurs observés sont la
publication `phase=c75_year` dans `OpexC75FlushYear` (`:2157-2175`,
déjà gardée par `C69_BOTTLENECK_PROBE`) et le panneau `UB|` de
`scheduler_tasks.nut:852-855` (appelé sous `C49_SCARCITY_LEDGER`).
Il n'est pas consulté pour calculer `K_pass`, choisir ou construire un
projet. Les incréments et initialisations subsistent ainsi en mode
`probes=0`, avec un coût a priori petit mais **non mesuré**.

Une optimisation future pourrait supprimer ces seuls compteurs lorsque
les deux consommateurs sont inactifs. Préalables : prouver la garde exacte
à la source, préserver les modes de diagnostic C69/C49 et Save/Load,
mesurer les opcodes consommés, la neutralité des décisions et le smoke,
puis obtenir le **20×10 `non_erosion`** requis pour les optimisations
d'opcodes selon AGENTS.md §4.1 avant adoption. Les gardes déjà qualifiées
VS/VL, RV et `_reportYear` restent indépendantes de ce chantier.
