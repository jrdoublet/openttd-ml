# Étape 17 — Harnais — duel 1v1 et contrôle de santé

- **SHA revu** : `c74a123` (à corriger si la session revoit un autre commit)
- **Modèle / effort prévus** : Opus 5 / xhigh
- **Périmètre** : `sweeps/bench_1v1_5y_20seeds.py`, `game_health.py`, `smoke_test.py` — 2 238 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Comptage `VEHS` non qualifié (composants non filtrés) ; 4 faux positifs de santé rouverts le
09-14 ; `expected_last_year` non renseigné. Toute conclusion économique du projet passe par là.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

<!-- ### 17.1 — <titre>        [gravité : P1 | P2 | P3]
`fichier:ligne` — ce que le code fait · ce qu'il prétend faire · conséquence observable. -->

*(à remplir)*

## Vérifié, n'est PAS un bug

*(à remplir — ce qui est écrit ici ne sera pas relitigé à la passe de correction)*

## Hors périmètre, à relire ailleurs

*(à remplir — renvoyer vers le numéro d'étape concerné)*
