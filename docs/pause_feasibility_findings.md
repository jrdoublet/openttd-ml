# Faisabilite : pause, construction IA et reproductibilite temporelle

Probe isole realise le 2026-08-26 contre le binaire officiel OpenTTD **13.4** (`openttd-13.4-linux-generic-amd64`), avec le meme mode que le projet : `-g -G 42 -snull -mnull -vnull:ticks=...`, `openttdlab.cfg` et `scripts/game_start.scr`. Tous les fichiers IA et runs de la probe etaient sous `/tmp/pausecheck-42afeed-*`; aucun fichier de production n'a ete modifie.

## Conclusion

La strategie « une IA met le jeu en pause, construit tout, puis relance » est **impossible dans ce setup**. Une pause normale demandee avant `start_ai` empeche meme `Start()` de s'executer; elle empeche donc a fortiori `BuildRail`, `BuildRailStation`, `BuildRailDepot` et `BuildVehicle`. L'API NoAI ne donne pas a une IA une primitive de lot de commandes dans un seul tick.

La meilleure alternative est de preparer selection, pathfinding et plans de gares avant la premiere mutation, puis d'emettre les commandes de construction consecutivement sans `Sleep` supplementaire. Le moteur impose deja un yield d'au moins un tick apres chaque commande reelle. Dans le controle historique (seed 42, 1950, carte 256x256, `number_towns=2`, 2 trains x 2 wagons, `engine_rank=1`, `pair_rank=0`, `line_index=0`), TrainLineAI consomme **38 ticks** entre sa premiere et sa derniere commande de construction; la valeur est identique sur trois repetitions.

## (a) Construction pendant une pause

**Non.** Une IA `PauseProbe` a journalise dans `Start()` puis appele deux commandes NoAI reelles (`AISign.BuildSign`, puis `AISign.RemoveSign`). Sans pause :

```
Start tick=1
BuildSign ... tick=2
RemoveSign ... tick=3
```

Avec ce `game_start.scr` :

```
pause
start_ai PauseProbe
```

un run de 1 000 `-vnull` ticks n'a produit aucune ligne `PROBE` : `Start()` n'a pas ete planifie, et aucune commande ne pouvait etre emise. Le `pause` de console est donc atteignable dans le harness, mais fige aussi le scheduler IA. `pause` puis `unpause` avant `start_ai` redonne le cas normal.

`gui.pause_on_newgame=true` n'est pas un contournement : dans ce headless run, le script de demarrage est execute avant que cette pause d'interface ne prenne effet; la sonde a deja execute ses commandes. Les autres bits de pause (erreur, join/min-active-clients, game-script, link graph) ne sont pas exposes a une IA NoAI comme batching. Une GameScript a `Game.Pause()`, mais ce n'est pas l'API IA et, une fois la partie pausee, les AI ne sont pas executees non plus.

## (b) API NoAI : cadence et substitut

La sonde montre qu'une commande qui modifie le jeu suspend le script : la suivante reprend exactement au tick IA suivant. Il ne faut donc pas ajouter `AIController.Sleep(1)` entre constructions : il est deja impose. Une boucle Squirrel ne peut pas faire deux `DoCommand` reelles dans le meme tick.

`AIController.SetCommandDelay(n)` ne peut qu'augmenter le delai minimal; `SetCommandDelay(0)` est ignore. `AITestMode` ne construit pas (estimation seule) et `AIExecMode` remet l'execution normale : aucun ne batch ni ne change la pause. L'API IA expose `GetTick`, `GetOpsTillSuspend`, `SetCommandDelay`, `Sleep`, etc., mais pas `PauseGame`/`UnpauseGame`. `AIController.Break()` est un outil de developpement qui suspend l'IA; il ne permet pas de construire en pause.

Le budget Squirrel par reprise est `script.script_max_opcode_till_suspend` : **10 000 opcodes par defaut** dans 13.4 (configurable 500--250 000 a la creation). Il limite le calcul pur/pathfinding, pas le batching : les `DoCommand` reelles gagnantes imposent elles-memes le yield d'un tick.

Conseil praticable : ordre de commandes fixe, aucun sleep entre elles. Une barriere `Sleep` apres tout le preflight peut aligner le **debut** de construction sur une cible suffisamment tardive, mais ne peut ni raccourcir ni egaliser le nombre de commandes de rail/depot/vehicules. Ajouter du padding ferait avancer la simulation et va contre le but.

## (c) Mesure TrainLineAI courant

La copie scratch exacte de `42afeed:ai/TrainLineAI` a recu seulement deux `AILog.Info` : juste avant le premier `AITile.DemolishTile` de l'etape 4 et juste avant `AIVehicle.StartStopVehicle` du dernier train de l'etape 7. Les bibliotheques BaNaNaS transitives reelles etaient Pathfinder.Rail 1, Graph.AyStar 4 et Queue.BinaryHeap 1.

| repetition (meme graine/configuration) | premiere commande | derniere commande | ecart |
|---:|---:|---:|---:|
| 1 | 392 | 430 | 38 ticks |
| 2 | 392 | 430 | 38 ticks |
| 3 | 392 | 430 | 38 ticks |

Les trois runs ont selectionne T6--T2 et fini `success 2/2`, cout 41535, cout vehicules 36256. Pour cette configuration, le span est deja court et constant; il n'explique donc pas une variance intra-run. Il ne faut pas extrapoler 38 a toutes les configurations : tuiles, ponts/tunnels, essais depot et vehicules varient avec la ligne demandee.

La premiere commande est au tick 392, apres le preflight : `Start()` -> premiere mutation est bien plus long que les 38 ticks de construction. Fixer seulement le span de build ne fixe donc pas le moment de la premiere mutation si le preflight varie.

## (d) Tick absolu de demarrage

**Oui, pour le demarrage de l'IA.** `game_start.scr` avec un unique `start_ai TrainLineAI ...` est execute pendant la creation de partie, avant le premier game loop. La sonde observe `Start()` au tick IA **1** dans trois configurations differentes : carte 256x256/2 villes; 512x512/50 villes custom; 1024x1024/annee 1970/75 villes custom, meme graine. Il n'existe pas de reglage « AI start delay » pertinent dans 13.4; `-vnull:ticks=` fixe le budget d'arret, pas le moment de `Start()`.

Pour le figer : conserver `start_ai` dans `scripts/game_start.scr`, graine et cfg explicites, `gui.pause_on_newgame=false`, et aucune pause console. Cela fixe le debut de `Start()` a la premiere iteration IA (tick 1).

Nuance importante : `AIController.GetTick()` est un compteur de scheduling IA, pas une API de tick global. Si le vrai objectif est la **premiere construction** au meme tick, il faut une barriere apres preflight et une cible au-dela du pire temps de preparation. Fixer `Start()` seul ne le garantit pas si le pathfinding differe.

## (e) Correction du cadrage initial

L'intuition principale etait correcte : pause => pas de scheduler IA => pas de construction. Deux precisions :

- Ce n'est pas `Sleep(1)` conventionnel qui espace les actions : OpenTTD le fait implicitement apres chaque `DoCommand` reelle.
- Dans le controle mesure, le build phase est deja exactement reproductible (38 ticks), alors que le preflight prend 391 ticks avant la premiere mutation. La priorite, si l'on veut normaliser un moment d'action, est donc le debut de construction apres preflight, pas une pause interne impossible.
