# OpexAI — archives scientifiques P0, P2, P4 et C77 (18 octobre 2026)

## Portée et règle de conservation

Cette archive **ne contient aucune modification à adopter dans `ai/OpexAI`**.
Elle fige les vérifications importantes du cycle d'octobre 2026 afin de
préserver des essais déjà terminés, des contrôles de reproductibilité et des
contre-exemples utiles. Les sources des worktrees et les originaux non suivis
restent à leurs emplacements respectifs ; rien n'a été supprimé ou relancé.

**La décision de suspension P2/P4 reste en vigueur.** Ne pas transformer les
prototypes de cette archive en réglages par défaut. Le bilan faisant autorité
sur la période est `docs/p2_p4_bilan_final_et_suspension_20261014.md`, avec
les précisions de `docs/p0_p2_p4_cloture_archives_20261018.md`.

## Archives et portée des preuves

| Archive | Ce qui est conservé | Interprétation autorisée |
|---|---|---|
| `p4_guard_independent.zip` | Développement 5×5, porte indépendante 40×5, JSONL complets, manifestes, source du bundle 40×5, reçu indépendant, vérificateur, tests, rapport et delta de code | **Rejet robuste** P4 AIR uplift : −52 352,375 £/an sur 40 graines, IC95 [−96 109,525 ; −15 266,975] ; le pilote favorable n'est pas une adoption |
| `c77_same_save.zip` | Harnais serveur dédié et vérifications A/A, cas de forks corrigés, sauvegardes/replays, sources de scripts, delta Squirrel et rapports de rang 2 | Fork valide jusqu'à la construction physique ; **pas de preuve de profit terminal causal à cinq ans**. Les vieux forks `-vnull` ne sont pas qualifiants |
| `p2_cold_calibration.zip` | Population P2 et recalage, 5×5 source figée, scripts de jointure, tests, JSONL, analyses, documents et historiques P3 sélectionnés | 43 lignes strictes / 102 AIR précoces, trois flips de tête sans alternative bâtie : **aucun coefficient froid qualifié** |
| `p2_p4_hypotheses_closure.zip` | H1/H2/H3 (campagnes, manifestes, bundles figés, scripts/tests), autopsie du vivier vide, bilan final, crash-only et overlays | H1 **non exposé** ; H2 −16 913 £/an et H3 −109 433 £/an en 5×5 non qualifiés ; ne pas confondre cotations de hub et profits réalisés |
| `p0_topk_equivalence.zip` | Contrôle de 57 859 insertions sans mismatch, deux 20×10, JSONL, analyses de construction/opcodes, bundle figé, tests et source du prototype | Gain local de −66,65 % à l'insertion ; variante économiquement non dégradante sans preuve de gain ; **V154/V157 déjà adopté sur master** |
| `p0_negative_diagnostics_frozen.zip` | Abandon second-check 20×10, concurrence visible 40×3, vetos AIR, blocage RAIL, reliquat opcode, C117, ROAD, conversion du portefeuille ; sources, logs disponibles, analyses, bundles clés | **Diagnostics/échecs ou hypothèses non causales**. Ne jamais présenter une sonde comme une politique gagnante |

Un archive ZIP comprend une arborescence de chemins relatifs à la racine du
dépôt de travail d'origine. Les répertoires `source_overlays/` contiennent les
patches **non intégrés** des fichiers suivis sous `ai/OpexAI` et le SHA de leur
base Git ; un fichier Squirrel non suivi y est inclus avec son chemin original.
La présence de ces fichiers ne confère pas de qualification économique.

## Contrôle indépendant d'intégrité

À la racine du dépôt :

```powershell
python3 -X utf8 sweeps/verify_p0_p2_p4_archive_20261018.py
```

Le vérificateur inspecte les **six ZIP**, leur taille et SHA-256, l'absence
de chemins dangereux ou de doublons, puis **chaque membre décompressé** :
nom, longueur et SHA-256 sont comparés au registre `MANIFEST.json`. Ce
registre indique aussi le commit de `master` avant le gel. Le contrôle ne
lance pas OpenTTD, n'utilise pas Docker, et n'édite aucune archive.

Pour reconstruire une arborescence de campagne depuis un bundle figé,
décompresser dans un nouveau répertoire, et **ne pas écraser le checkout
actif**. Certains outils historiques citent d'anciens chemins de `results/` :
ils devront être relancés en environnement historique reconstitué si besoin.
La présence du bundle ne garantit pas à elle seule l'identité de la VM, de
l'image Docker, du hasard concurrent ou des sauvegardes futures.

## Limites explicites

- Les campagnes JSON/JSONL et les bundles sélectionnés sont figés, mais **pas
  l'intégralité des centaines de vieux bancs hérités de chaque worktree**.
  Les originaux demeurent localement dans les dossiers d'expérience.
- Les trois forks C77 retenus sont ceux du serveur dédié. Les campagnes
  historiques avec compagnie fantôme sont documentées, mais ne constituent
  pas une preuve économique. Les replays mensuels ne remplacent pas un fork
  `same-tick` au moment de la décision C77.
- P0 ROAD : le répertoire source fournit le `jsonl` et le manifeste du
  diagnostic 3×5, **pas son JSON récapitulatif** ; l'archive ne le fabrique
  pas. Une absence de preuve n'est ni un succès ni un échec quantifié.
- Les sources `source_overlays/*.patch` sont **historiques et non adoptées** ;
  plusieurs stades utilisent une base V166 ou `f6139d8`, pas le master actuel.
  Il faut comparer ces bases avant tout usage éventuel, sans écraser les
  défauts V154, V159, V165 ou les évolutions suivantes.
- L'intégrité SHA-256 garantit l'identité de l'archive, **pas** la causalité
  de ses expériences. Contrôles A/A, mêmes bundles, même état au tick,
  constructibilité et profit marginal global restent des exigences séparées.

## Génération

Script sélectif conservé :

```powershell
python3 -X utf8 sweeps/archive_p0_p2_p4_20261018.py
```

Il lit les fichiers historiques et reconstruit les ZIP/`MANIFEST.json` dans
ce dossier seulement. **Ne pas le relancer inutilement** : le registre
actuel atteste le gel du 18 octobre 2026. Une nouvelle capture nécessite
une nouvelle version du dossier et un nouveau contrôle des résultats.
