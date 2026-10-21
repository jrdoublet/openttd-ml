# V303 — sonde inverse découpable ou alternée

## Pré-enregistrement (21 octobre 2026)

Worktree `/home/deploy/projects/wt-v303`, branche `v303`, HEAD initial
`71aff200f42650f64a8d628cd97e92c1e99003ae` (arbre propre, descendant de
`d50d1d7a`). Aucun apport de V304. Aucun défaut modifié, aucun push ni banc GitHub.

Avant implémentation : référence instrumentée sous `decision_log=1`,
3 graines 42/7/100 × 10 ans, carte 256², duel AAAHogEx, campagne
`v303_before_3x10_20261021`. Mesurer les appels effectifs de la sonde :
itérations consommées, ticks et opcodes, réussite et sens inverse retenu.
Le succès de sonde signifie sélection inverse ; cela ne mesure pas le résultat
contrefactuel d'une recherche aller non exécutée.

Intervention : nouveau `v303_reverse_mode`, défaut 0 aux quatre niveaux ;
1 = sonde identique en tranches puis recherche historique ; 2 = A* aller et
retour alternés, premier succès, budget cumulé borné par aller + sonde.
L'état vivant reste dans `_railSearch`, abandonné au rechargement.

Validation : contrats `test_v303_*.py`, suite Python entière, délimiteurs,
puis diagnostics locaux successifs `v303_mech_m1_3x10_20261021` et
`v303_mech_m2_3x10_20261021`, référence `OpexAI[decision_log=1]`, variante
`OpexAI[v303_reverse_mode=N,decision_log=1]`, policy `v303mN`.
Graines 42/7/100, 10 ans, une répétition, carte 8, script-debug,
`gain_short`, métrique `profit_year`, seuil relatif 4 %, garde valeur 5 %.
Trois graines constituent uniquement un diagnostic, sans adoption économique.
Budget : 3 parties avant, puis 6 par mode, séquentiellement ; Docker local
3 CPU, 2 Go RAM et swap plafonné à 2 Go, 3 workers, réseau host,
volume `openttd-lab-home`. Image contrôlée :
`sha256:a0e0a0727f5003532764eeaeee6b83e9ab96a7470df3c76208c6446d10b88c8c`.
Pas de conteneur OpenTTD concurrent lors du contrôle initial.

Les échecs et réussites seront regroupés par distance <60, 60–99, 100–159,
≥160, via le parseur existant `diag_railech_abnd.py`. Les ticks actifs de
chaque tranche seront distingués du délai écoulé entre tranches.

## Mesure avant

Référence instrumentée seule, bundle
`b09c3c896490f3bbc62dd75605ef04918c8871ce75d47901b75271b28b8e19d0` :
3 parties complètes, 121 tentatives rail, 76 OK, 8 ABND, aucune erreur script Opex.
86 sondes, 32 trouvées et retenues (37,2 %). Itérations médianes 300 ;
ticks médians **45**, moyenne 44,36, maximum 75 ; opcodes médians **451 030**,
total 38 110 230. La mesure confirme donc les ~45 ticks du ticket.
Mesure `FindPath` seul, hors création du pathfinder et conversion du chemin.

| Distance | Tentatives | OK | ABND | Sondes | Trouvées |
|---|---:|---:|---:|---:|---:|
| <60 | 9 | 9 | 0 | 4 | 4 |
| 60–99 | 27 | 20 | 1 | 21 | 13 |
| 100–159 | 38 | 21 | 3 | 26 | 12 |
| ≥160 | 47 | 26 | 4 | 35 | 3 |

Le mode 1 conserve l'aller segmenté et les paramètres exacts de la sonde.
L'équivalence de décision porte sur un terrain inchangé : rendre la main permet
à l'adversaire et à la simulation de modifier la carte entre tranches.
Le mode 2 garde le poids initial de l'aller actuel (400 au défaut segmenté)
et celui de la sonde (200), mais utilise deux A* continus ; il ne conserve pas
les reprises/adaptations de poids par segment. Premier créneau inverse, puis
alternance ; un tas vide est retiré, l'autre utilise le budget restant.
Les deux directions peuvent dépasser 300 individuellement en mode 2,
sans dépasser ensemble `iterationBudget + v294_rail_reverse_probe`.

Validation Save/Load supplémentaire prévue après les diagnostics : le harnais
`save_load_roundtrip.py`, graine 42, un an initial puis un an après chargement,
mode 1 puis mode 2, mêmes limites Docker. Le test statique couvre aussi un
Load sans ancien marqueur `railSearchPending`. Un rechargement sans recherche
active observée ne prouvera pas à lui seul l'abandon d'une sonde vivante.
