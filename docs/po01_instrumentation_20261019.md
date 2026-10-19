# PO-01 — instrumentation et dépendances (19 octobre 2026)

Analyse du code de la branche `po01`, base `535b5bd`. Les mesures 5–12 M et
72 % viennent du diagnostic du 12/10, pas d’une nouvelle mesure. Aucune partie
n’est lancée pour cette mission. PO-02 reste distinct, sans expiration ajoutée.

## Déclenchement et invalidation

`orchestrator.nut::_dispatchReactiveIntention` consomme l’intention coalescée
`regen`. `_c80ModeRegenModes` rend `null` si les révisions C76 ou leurs
acquittements manquent, ou si `towns`, `lines`, `engines.air` dépassent
l’acquittement. Sans portefeuille, le dispatch prend aussi le chemin complet.
Les industries et moteurs terrestres/eau seuls donnent une liste C80.

| Couche | Générateurs concernés selon `_c76GetModeDeps` | Précision |
|---|---|---|
| towns | AIR, rail, route, eau | rail/route regroupent pax et fret ; l’acceptation urbaine du fret lit aussi les villes |
| lines | AIR, rail, route, eau, flotte | exclusions des origines, gares, dessertes et opportunités de flotte |
| engines.air | AIR, flotte | aucune dépendance rail/route/eau ; le commentaire C80 « tous les modes » est trop large |
| industries | rail, route | l’eau ne transporte ici que des voyageurs |
| engines.rail/road/water | mode correspondant et flotte | flotte C76 conservatrice ; les opportunités actuelles sont aériennes |

Les sous-modes C76 sont une matrice déclarative ; les unités réellement
régénérables par `OpexRegenerateModeProjects` sont `rail/road/air/water`.
La flotte s’injecte via `OpexInjectFleetProjects`, elle ne passe pas par ce générateur.
`ET_TOWN_FOUNDED` et `ET_ENGINE_AVAILABLE` passent par `_markDirty`, qui
incrémente les révisions. Attention à l’audit du 12/10 : dans cette base,
`_markPairAbandoned` incrémente `lines` avec `false`, donc sans enfiler lui-même
une intention ; cette révision peut être coalescée avec une intention ultérieure.

## Sonde livrée

`probes=8` (groupe opcodes/catalogue), `probes=4` (journal), ou tout groupe
activant `DECISION_LOG` : `PO01_REACTIVE cause=... modes=...` décrit toutes
les couches en retard et leur union de modes, sans choisir artificiellement
une cause unique. `PO01_COST phase=layer unit=... ops=...` mesure les sept
rafraîchissements du catalogue ; `phase=mode` mesure rail, route, AIR, eau et
l’assemblage/sélection/flotte/subventions. Les intervalles sont disjoints dans
chaque famille, mais les niveaux imbriqués ne doivent pas être additionnés.
Le coût des lignes est surtout porté par les générateurs : il n’existe pas de
rafraîchissement de catalogue `lines` à chronométrer séparément. Une couche qui
invalide plusieurs modes n’a pas de coût causal exclusif : aucune division
arbitraire des opcodes n’est faite entre causes simultanées.

Hors sonde : aucune mesure, allocation de diagnostic ou émission nouvelle.
Les gardes de branche ont néanmoins un coût VM ; « coût nul » désigne ici
l’absence de travail de sonde, pas une identité opcode bit à bit.

## Références vérifiées (code livré, chemins relatifs à `ai/OpexAI/`)

| Chemin | Point vérifié |
|---|---|
| `orchestrator.nut:595` | dispatch réactif, branche OFF historique conservée |
| `orchestrator.nut:1036` | incréments de couches et intention coalescée |
| `orchestrator.nut:1075` | matrice `_c76GetModeDeps` |
| `orchestrator.nut:1287` | conditions exactes du retour `null` C80 |
| `orchestrator.nut:1209` | reconstruction complète et mesure flotte |
| `events.nut:40` | passage événements → révisions C76 |
| `event_handlers.nut:414` et `event_handlers.nut:440` | fondation de ville / disponibilité moteur |
| `lines.nut:277` | abandon : révision `lines`, notification `false` |
| `catalog.nut:987` | intervalles par couche du refresh complet |
| `projects.nut:118` | drapeaux réellement exécutés `PO01_EXEC`, coût des modes et assemblage |
| `po01_reactive.nut:2` | diagnostic par union des dépendances |
| `projects_generation.nut:120` | remplacement d’un seul mode, conservation des autres candidats et des projets spéciaux |

Les numéros sont ceux de la livraison PO-01, pas ceux de l’ancien audit du 12/10.
