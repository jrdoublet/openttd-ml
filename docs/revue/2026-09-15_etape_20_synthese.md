# Étape 20 — Synthèse et priorisation des correctifs

- **SHA revu** : `c74a123` (à corriger si la session revoit un autre commit)
- **Modèle / effort prévus** : Opus 5 / high
- **Périmètre** : Les 19 fichiers de constats de `docs/revue/`
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Regrouper par mécanisme, trancher gravité et ordre, produire
`docs/revue_code_2026-09-15_correctifs.md`, et solder les groupes G0–G12 du 09-06.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

Le livrable de cette étape n'est pas un fichier de constats supplémentaire : c'est le regroupement
**par mécanisme** de tous les constats des 19 étapes précédentes, produit dans
`docs/revue_code_2026-09-15_correctifs.md` (5 tiers, groupes H1-H5/B1-B9/M1-M7, statut des groupes
G0-G12 du 09-06, ordre d'exécution recommandé, greffes opportunistes vers `docs/taches.md`) —
conformément à la sortie attendue décrite dans le tableau « Clôture » de
`docs/revue_code_2026-09-15_plan.md`, qui diffère du squelette générique ci-dessous.

Un trou de couverture a été identifié au passage (fichiers de harnais de campagne jamais lus par
aucune étape) et a donné lieu à l'ouverture de l'étape 21, tenue le 2026-09-16 :
`docs/revue/2026-09-15_etape_21_harnais_campagne.md`.

## Vérifié, n'est PAS un bug

Voir `docs/revue_code_2026-09-15_correctifs.md`, section « Tier « ne pas toucher maintenant » » et
le tableau de statut des groupes G0-G12.

## Hors périmètre, à relire ailleurs

Voir `docs/revue_code_2026-09-15_correctifs.md`, section « Deux questions que les étapes ont
explicitement renvoyées à celle-ci » (durée du smoke test ; fichiers de harnais non couverts →
étape 21).
