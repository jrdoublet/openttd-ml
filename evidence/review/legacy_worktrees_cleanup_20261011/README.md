# Archives des trois worktrees expérimentaux retirés le 11 octobre 2026

Ces archives ont été construites **avant tout retrait de worktree**, à partir de
leur propre HEAD et de leur état non commité. Les trois HEAD sont déjà ancêtres
de `master` ; il n'y avait aucun commit exclusif à fusionner.

Chaque ZIP contient `git/tracked_changes.patch` (`git diff --binary HEAD`),
`git/staged_changes.patch`, `git/status_porcelain_z.bin`, `manifest.json` et
`files/<chemin>` pour **tous les fichiers non suivis et ignorés** du worktree.
Les fichiers ignorés incluent, notamment, bundles IA figés, JSONL, rapports,
traces moteur et sources adverses locales. Aucun résultat n'a été recalculé.

La provenance (HEAD, branche ou HEAD détachée, patch, statut), la taille et
l'empreinte SHA-256 de chaque fichier figurent dans le manifeste interne ;
`index.json` donne SHA-256 et taille du ZIP lui-même. Les trois archives ont
été testées via CRC ZIP et relecture/empreinte de chaque élément. Refaire le
contrôle avec `python evidence/review/legacy_worktrees_cleanup_20261011/verify.py`.

| ZIP | État avant nettoyage | Fichiers hors Git | Décision |
| --- | --- | ---: | --- |
| `c83_local_20261002.zip` | `b2334d7` détaché, 12 fichiers suivis marqués modifiés (11 différences substantielles), 9 non suivis, 599 ignorés | 608 | C83 réparation locale : **rejet économique**, `fail_primary` au 20×10 et au retest V102 40×3 ; production publiée ultérieurement, prototype OFF |
| `c121_air_productivity.zip` | `79497c7`, 4 suivis, 6 non suivis, 114 ignorés | 120 | Diagnostic seulement, aucun effet causal démontré ; harnais actuel déjà modernisé |
| `c61_air_rotations.zip` | `52ab555`, 1 suivi, 8 non suivis, 3 ignorés | 11 | Échec de couverture temporelle de la sonde ; aucun changement comportemental justifié |

## Déjà conservé dans `master`

- C83 : rapports de réaction aux créneaux, réparation locale, 5×6, 20×10,
  retest 40×3 et archives condensées dans `docs/`, `docs/journaux/` et
  `evidence/review/c83_*`.
- AIR productivity : télémétrie mensuelle et données financières par avion
  déjà présentes sous une interface plus récente ; les champs historiques
  supplémentaires restent dans le patch archivé.
- C61 : preuve de la limitation de la sonde ; aucune intervention économique
  ouverte sur la seule base de cette mesure. Le document, les lecteurs,
  les tests et les trois résultats JSON restent récupérables dans son ZIP.

Ne **pas** remettre les anciens fichiers Squirrel dans `master` : C83
`c83_slot_reaction` a été volontairement retiré, `c83_local_repair` n'a pas
été qualifié pour passer ON et le reste du harnais a évolué depuis ces clones.
Les deux formules de score RAIL définitivement rejetées sont hors périmètre et
n'ont fait l'objet d'aucune nouvelle évaluation.

## Worktree V102 : conservation séparée

`codex/github-v102` contient trois commits propres absents de `master` :
`1870375` (migration de qualification GitHub V102), `a27ca28` (User-Agent du
téléchargement adverse) et `f6f9ffe` (preuve du smoke Actions). La branche est
publiée séparément avec la PR draft #18 ; des contrats et un smoke GitHub sont
verts, mais le parcours complet A/B de `qualify.yml` sur Actions n'est pas
encore prouvé. Cette modification d'infrastructure est utile, mais touche de
nombreux fichiers du harnais et de la documentation évolués depuis. **Pas de
fusion automatique** ni de retrait de ce worktree propre : sa réconciliation
sur `master` mérite un chantier dédié, sans changer les défauts de l'IA.
