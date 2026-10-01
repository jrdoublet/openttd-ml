# Réorganisation documentaire — 30 septembre 2026

[Index documentaire](../README.md) · [Journaux](README.md) · [Travail restant](../taches.md)

## Demande et périmètre

Suite à la revue ciblée, demande d'actualiser et d'alléger le corpus, de clarifier
les journaux et de conserver une seule liste de tâches. Ce lot porte sur la
documentation du projet, pas sur les bibliothèques tierces, leurs licences ou les
artefacts générés. Il est distinct de la
[correction documentaire ciblée](../revue_documentation_2026-09-30.md), qui décrit
notamment les changements antérieurs de Docker et de l'audit de preuves.

Checkout issu d'une archive, sans `.git` ni commande Git disponible : aucun SHA
local établi, aucun diff Git ni `git diff --check`. D'autres sessions ont livré
du code simultanément ; leurs changements ont été relus pour le suivi, pas
attribués à cette réorganisation.

## Structure livrée

- `docs/README.md` : navigation du corpus, rôle et statut des fiches.
- `docs/taches.md` : seule file active, séparant validation, implémentation,
  intervention bornée et reprise conditionnelle. Chaque ligne donne une sortie
  attendue ; les travaux terminés ne sont plus un backlog parallèle.
- `architecture_courante.md` : modules et chargement, y compris la dépendance
  transitive `air_recovery.nut`. Les anciens schémas restent des références datées.
- Index des journaux, des 21 lots de revue et des archives ; racine `walkthrough.md`
  reliée à la navigation, sans dupliquer son contenu historique.
- [Synthèse des décisions](synthese_decisions_2026-09-30.md) et
  [synthèse Phase 0](../archives/phase0_trainline_synthese.md) : condensations
  sourcées, **pas copies intégrales** des anciens guides.
- Instructions communes et guides courts réconciliés ; qualification enchaînée
  `qualify.yml` reliée à son [contrat](../../qualifications/README.md), sans
  prétendre qu'elle a été exécutée.

### Allègement des points d'entrée

Comptages de lignes physiques, instantané du lot ; les fichiers restent modifiables.

| Fichier | Avant réorganisation | Après consolidation |
|---|---:|---:|
| `README.md` | 503 | 70 |
| `docs/taches.md` | 988 avant ajouts concurrents | 117 |
| `ai/OpexAI/CLAUDE.md` | 219 | 165 |

Les fiches détaillées et journaux sont conservés pour la traçabilité, pas comprimés
au prix de la disparition des protocoles et limites. Leur statut daté prime sur
une ancienne formulation au présent ; seules les tâches fixent le travail actuel.

## Réconciliation et limites conservées

- V89/V91, C115, C67 et les anciens plans ont un statut explicite. L'ancien ratio
  de rendement par véhicule « 93 % » est retiré comme preuve dans C80 ; les comptes
  `VEHS` bruts ne permettent pas cette conclusion.
- Quatorze findings R implémentés localement restent **non validés par exécution**,
  dont R1/R19 désormais journalisés. R6–R17 restent à implémenter ou décider.
  Catalogue R4 : seuil `>2 000` et garde de tick locaux, pas gain mesuré.
- C115 protégé, pistes rejetées et interdictions de campagne préservés. Aucune
  activation, adoption économique ou autorisation de publication ajoutée.
- Liens absolus locaux et anciennes ancres de lignes Markdown remplacés par des
  références portables. Les références de lignes Squirrel historiques restent
  datées : elles ne garantissent pas la position actuelle d'un symbole.
- Les quatre liens vers des résultats absents dans C80 et le journal du 13 sont
  devenus des citations explicites `results/...json` avec l'absence signalée.
  Cela répare la navigation, **pas la preuve**. Récupération C116/C117/C122 et audit
  des autres sources manquantes restent dans les tâches.

## Incident de conservation et restauration

Une édition de liens a tronqué involontairement le transfert historique du 22 :
2 086 → 1 323 lignes. L'incident a été détecté par recomptage et comparaison des
titres. Après autorisation explicite de l'utilisateur, restauration par copie de
la version complète `2BMu.md` de l'historique local VS Code.

- Copie de protection du fichier précédent :
  `journal_2026-09-22_transfert_historique.avant-restauration-20260930-143756.bak`.
- Au moment de la restauration : **2 086 lignes**, copie octet pour octet vérifiée
  par SHA-256 : `F434F653F6D09B14E778E57F69E36BCB4B0FB5620053F45BD319CE26B439606E`.
- Ensuite, seules les notes de lecture en tête ont été actualisées : **2 089 lignes**.
  Le corps à partir de « Tâches — réduire l'écart avec AAAHogEx » a été comparé
  intégralement à la sauvegarde, avec normalisation CRLF/LF : **identique**.
- Le journal du 13 conserve ses **3 021 lignes** après les corrections ciblées.

## Contrôles et portée de la clôture

Vérifications PowerShell en lecture seule : destinations des liens Markdown
locaux, couverture de navigation, références au backlog raccourci, titres et corps
de l'archive restaurée, absence de marqueurs de conflit ou de contenu omis artificiel.
Contrôle final : **156 documents**, **740 liens locaux**, **0 destination manquante**,
**6 ancres Markdown vérifiées sans anomalie**, aucun document du périmètre sans
lien entrant, aucun marqueur de conflit ou placeholder d'omission détecté.
Périmètre : Markdown racine, `docs/`, `.github/`, `qualifications/`,
`evidence/review/`, `sweeps/archive/`, `sweeps/fixtures/` et contexte OpexAI.
Les chiffres historiques ne sont pas recalculés et les URL externes ne sont pas
validées par ces contrôles. Une destination existante ne prouve pas sa provenance.

Aucun test Python, build Docker, compilation Squirrel, Save/Load, smoke ou campagne
n'a été exécuté par ce lot documentaire. Aucun code IA ni défaut modifié ici,
aucun commit, push ou publication. Les validations runtime et preuves manquantes
restent explicitement ouvertes dans [taches.md](../taches.md).