# Étape 18 — Harnais — banc officiel et diagnostic P1

- **SHA revu** : `c74a123` (à corriger si la session revoit un autre commit)
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `sweeps/bench_v2.py`, `bench.py`, `head_to_head.py`, `diag_c63_c58.py` — 2 159 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Appariement par graine, test des signes, et G0 : épinglage explicite des réglages dans CHAQUE
bras, contrôle inclus. G0bis : aucun coût d'opcodes dans les JSON de banc.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

<!-- ### 18.1 — <titre>        [gravité : P1 | P2 | P3]
`fichier:ligne` — ce que le code fait · ce qu'il prétend faire · conséquence observable. -->

*(à remplir)*

## Vérifié, n'est PAS un bug

*(à remplir — ce qui est écrit ici ne sera pas relitigé à la passe de correction)*

## Hors périmètre, à relire ailleurs

*(à remplir — renvoyer vers le numéro d'étape concerné)*
