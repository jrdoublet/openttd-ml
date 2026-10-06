# Journaux — décisions, mesures et provenance

[Documentation](../README.md) · [Travail restant](../taches.md)

Les journaux conservent la chronologie, **pas les instructions courantes**. Un statut
« ouvert » dans une section ancienne peut être remplacé plus loin ou dans un journal
ultérieur. Pour agir, lire `taches.md` ; pour comprendre une décision, partir de la
[synthèse au 30 septembre](synthese_decisions_2026-09-30.md), puis de ses sources.
Les mesures antérieures au **9 septembre 2026** ne font plus preuve actuelle.
Les autres mesures exigent toujours bundle, protocole et santé vérifiables.

## Derniers comptes rendus

| Journal | Contenu / portée |
|---|---|
| [5 octobre](journal_2026-10-05.md) | Workflow de régression réparé ; piste AIR 6 close : 0 challenger meilleur sur 172 décisions (6 graines × 3 ans) |
| [4 octobre](journal_2026-10-04.md) | File C121 nocturne : 27 comparaisons saines sans passage A ; trois B passent, adoption explicite utilisateur, analyse des graines perdantes et validation technique |
| [3 octobre](journal_2026-10-03.md) | V96 « avion de la partie » (C121) adopté sous règle opcodes ; synchronisation des consignes LLM avec V102 (portes 40×3 puis 20×10), workflows GitHub encore historiques |
| [2 octobre](journal_2026-10-02.md) | Fusion du gagnant AIR adoptée sous règle de neutralité après 20×10 sain ; contexte paire/avion non retenu (+9,88 % d'opcodes, garde valeur échouée en 5×6) ; blocage/reprise Docker ; lot cadence/K_pass distinct, aucun modèle C121 adopté |
| [1er octobre](journal_2026-10-01.md) | Audits/intégrations puis défaut5×6 contre AAA ; huit fixtures dirigées R1/R3, VM48+9 et frontières Save/Load validées ; 1124 tests complets puis136 contrats finaux réussis, aucune adoption |
| [30 septembre](journal_2026-09-30.md) | Correctifs R et bancs GitHub : lire les groupes successifs ; implémentation locale ≠ validation par exécution |
| [Réorganisation documentaire](reorganisation_documentation_2026-09-30.md) | Périmètre du rangement, contrôles statiques et limites ; distinct des livraisons IA |
| [29 septembre](journal_2026-09-29.md) | C121 AIR causal, dernières décisions ; C122 détaillé dans sa fiche |
| [24 septembre](journal_2026-09-24.md) | Mémo urbain, régénération par mode, renvois aux bancs nocturnes |
| [23 septembre](journal_2026-09-23.md) | C67 et intégrations ; lire aussi la nuit du 23 |
| [22 septembre](journal_2026-09-22.md) | C76/C77, cartographie et réconciliation |
| [21 septembre](journal_2026-09-21.md) | Défauts C69/C70/C75, retrait Lakes/feeders |
| [20 septembre](journal_2026-09-20.md) | C68 et état de référence historique |

## Bancs de nuit et transferts

- [Nuit du 24](24_nuit_2026-09-24.md) : V86, dépôt rail, index hub, C83, mémo et modes.
- [Nuit du 23](23_nuit_2026-09-23.md) : C77, filtre marginal, planification AIR.
- [Nuit du 22](20_nuit_2026-09-22.md) : C81/C82. Le préfixe `20_` est historique,
  la date de contenu fait foi ; aucun renommage des références de campagne.
- [Transfert du 22](journal_2026-09-22_transfert_historique.md) : ancien registre
  conservé intégralement, **pas un journal de nouvelles mesures du 22**.
- [Synthèse du 30](synthese_decisions_2026-09-30.md) : condensation sourcée du
  backlog, **pas copie intégrale** ; conserve décisions, rejets et limites.
- [Archives](../archives/README.md) : ancien backlog et sources corrompues conservées.

## Journaux précédents

Septembre : [17](journal_2026-09-17.md), [16](journal_2026-09-16.md),
[15](journal_2026-09-15.md), [14](journal_2026-09-14.md),
[13](journal_2026-09-13.md), [12](journal_2026-09-12.md),
[11](journal_2026-09-11.md), [10](journal_2026-09-10.md).

Historique antérieur au seuil de preuve : septembre
[8](journal_2026-09-08.md), [7](journal_2026-09-07.md), [6](journal_2026-09-06.md),
[5](journal_2026-09-05.md), [4](journal_2026-09-04.md), [3](journal_2026-09-03.md),
[2](journal_2026-09-02.md), [1](journal_2026-09-01.md) ; août
[31](journal_2026-08-31.md), [30](journal_2026-08-30.md), [29](journal_2026-08-29.md),
[28](journal_2026-08-28.md), [27](journal_2026-08-27.md).

## Format pour les prochains lots

Une section datée par lot : demande et périmètre ; code/branche/SHA ou absence de
Git ; fichiers ; changement ; tests **exécutés** séparés des tests préparés ;
campagne/run exact, artefacts et verdict ; limites ; décision ; lien vers le reliquat
dans `taches.md`. Une correction ultérieure cite la section remplacée ; ne pas
réécrire rétroactivement le résultat d'une campagne. Pas de nouvelle copie du backlog.
