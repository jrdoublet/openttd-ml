# Étape 01 — Réglages et globales

- **SHA revu** : `c74a123` (à corriger si la session revoit un autre commit)
- **Modèle / effort prévus** : Opus 5 / high
- **Périmètre** : `ai/OpexAI/info.nut` (lecture déclarative : grep sur les `AddSetting`, pas ligne à ligne), `settings.nut`, `globals_pre.nut`, `globals_post.nut` — 3 809 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Volet A : cohérence déclaration → lecture → repli, et les 8 globales définies en double/triple.
Volet B : audit d'adoption des 82 défauts actifs contre le banc officiel (20×10, ≥15/20, p<0,05).

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

<!-- ### 01.1 — <titre>        [gravité : P1 | P2 | P3]
`fichier:ligne` — ce que le code fait · ce qu'il prétend faire · conséquence observable. -->

*(à remplir)*

## Vérifié, n'est PAS un bug

*(à remplir — ce qui est écrit ici ne sera pas relitigé à la passe de correction)*

## Hors périmètre, à relire ailleurs

*(à remplir — renvoyer vers le numéro d'étape concerné)*
