# RAIL-REPAIR-IDLE-6M — réparations uniquement après stagnation

**Décision du 30 octobre 2026 :** les réparateurs ferroviaires sont des
recours de stagnation et non une stratégie lancée systématiquement. Une
inactivité de **six mois calendaires sans nouvelle ligne construite**
constitue le premier déclencheur. Le prototype est livré sans modifier
les défauts des variantes historiquement non qualifiées.

## Contrat d'activation

- `rail_repair_join_site=1` : chercher un quai alternatif seulement si
  l'option est explicitement activée, qu'un rattachement partagé échoue et
  que la stagnation dure au moins six mois.
- `rail_repair_v131_focus=1` : ne démarrer le moteur ciblé de réparation
  d'un plan stocké qu'après ces six mois. L'option historique
  `v131_rail_repair=1` reste indépendante de cette nouvelle politique.
- `rail_repair_astar_pair=1` : une seconde recherche A* de paire de quais
  après `ABND/NOPA` seulement pendant la stagnation ; la recherche primaire
  normale n'est jamais gelée.
- `rail_repair_pose_order=1` : n'autoriser la reprise bornée et
  transactionnelle de pose que pendant la stagnation.
- `v233l_constructibilite=2` : repli **constructif** monovoie seulement
  pendant la stagnation. Le mode `1` reste un **diagnostic passif**, et le
  mode `0` historique reste le défaut.

Le compteur est remis à la date courante **uniquement après une nouvelle
ligne effectivement construite** et inscrite dans `this._lines`, quel que
soit le mode (AIR, RAIL, ROAD, WATER). Les appels ratés, les recherches et
devis AITestMode, achats de flotte de renfort, renouvellements et actes
immobiliers ne sont pas comptés comme de nouvelles lignes. Une construction
AIR ou ROAD interrompt donc aussi la période de stagnation RAIL.

Le calcul est calendaire : ajout de six mois au jour de la dernière
construction, avec adaptation à la fin du mois d'arrivée (`31 août` →
`28/29 février`), et **pas** un délai approximatif de 180 ou 183 jours.
Une nouvelle partie démarre avec un délai entier de six mois avant toute
réparation, même si aucune ligne n'a encore été bâtie. Une construction
ultérieure remet ce délai à zéro ; les interventions déjà commencées
conservent leurs protections et leur rollback historiques.

## Save/Load et conservation du défaut

Le scalaire entier `railRepairLastConstructionDate` est enregistré dans
les **deux** formats Save (`save_full_state=0` et `=1`) quand au moins
un des recours est sélectionné. `Load` le restaure avant `Start`, puis
`Start` ne réinitialise pas une date valide. Si le champ est absent
(ancienne sauvegarde) ou futur, la politique adopte un délai conservateur
de six mois à partir du chargement. Aucun champ supplémentaire n'est
écrit lorsque toutes les nouvelles variantes sont à OFF.

Journaux seulement lorsque `DECISION_LOG` est actif et qu'une option
expérimentale est demandée :
`RAIL_REPAIR_IDLE phase=start last=... ready=...`,
`phase=reset reason=new_line`, et `phase=enabled reason=six_calendar_months`
(une fois par période de stagnation). Cela permet de distinguer les
recherches normales des secours effectivement déclenchés.

## Validation technique du 30 octobre

- **96/96 tests hôtes** ciblés réussis, y compris tests de dates de fin
  de mois / années bissextiles, présence des gardes sur SITE/V131/A*/POSE/
  V233L, 4 modes de construction et deux formats de sauvegarde.
- **Smoke moteur OFF/ON 1×1**, seed42, 1970, 256², OpenTTD 15.3 :
  les deux bras sont sains et rigoureusement identiques sur les mesures
  finales (valeur 262 389 £, `profit_year` 341 965 £, 14 véhicules,
  19 gares). Aucun gain revendiqué à un an.
- **Save/Load moteur réellement effectué avec toutes les réparations ON**,
  seed42, phases 1970 puis reprise depuis le 1er juillet :
  `save_full_state=0` **13+13 sauvegardes, OK**, et
  `save_full_state=1` **13+13 sauvegardes, OK**. `LOAD_RECONCILE` présent
  dans les deux cas, aucun marqueur d'erreur. La phase B compacte
  journalise `phase=start last=719666 ready=719850`, preuve que la
  dernière construction du 19 mai a traversé le rechargement du 1er juillet.
  La phase B complète restaure également sa dernière construction
  antérieure à la sauvegarde (`last=719703`). Le harnais fait apparaître
  la compagnie humaine fantôme déjà connue ; ne pas tirer de résultat
  économique global d'un banc Save/Load.

La connexion distante à BaNaNaS ayant renvoyé HTTP 502 au chantier
précédent, les bibliothèques de test utilisées proviennent du bundle
local déjà gelé ; leurs empreintes SHA-256 ont été vérifiées par les
lanceurs conservés localement sous `results/` (ignorés par Git).

**Verdict : implémentation et tests techniques réussis, adoption économique
non qualifiée.** Les anciennes performances 5×5 « toujours ON » ne sont
pas celles de cette stratégie avec condition d'inactivité ; mesurer les
déclenchements effectivement exposés et les OD construites rentables avant
toute porte A40×5 / B20×10. Garder tous les défauts publics inchangés.
