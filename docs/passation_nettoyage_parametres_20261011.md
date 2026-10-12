# Passation — nettoyage des paramètres OpexAI

**Suite réconciliée au12/10 :** [paramètres examinés, décisions et nouveau prompt](passation_nettoyage_parametres_20261012.md). `edac183` a depuis été publié ; les états Git ci-dessous décrivent la fin de session du11/10, pas le statut courant.

État vérifié le 11 octobre 2026. Ce document résume cette session ; `docs/taches.md` reste la seule liste autoritaire du travail restant. Les rapports liés conservent protocoles, graines, bundles et résultats. Leurs paragraphes « défaut conservé » ou « aucun commit » décrivent parfois une étape antérieure : les décisions finales ci-dessous prévalent.

## Méthode retenue

Traiter les paramètres un par un : usages, dépendances, historique, complexité, puis décision utilisateur. Un réglage OFF n'est pas du code mort. Ne pas supprimer ni lancer un banc à la seule demande « paramètre suivant ». Les bancs demandés comparent ON−OFF sur les mêmes sources figées, chaque bras contre AAAHogEx en carte partagée. Profit primaire : profit annuel terminal Opex, pas le profit cumulé ou le seul écart contre l'adversaire. Ne pas confondre gain non démontré, neutralité prouvée, rejet utilisateur et perte étayée.

PC Windows : 10 CPU, 8 Go RAM et swap plafonné à 8 Go, 10 workers ; cache `openttd-lab-home`. VPS seulement : 3 CPU/3 workers/2 Go. Vérifier le daemon, les campagnes concurrentes et les montages avant lancement. Utiliser les harnais existants et des noms uniques. Aucun rejeu favorable ni changement implicite de défaut. Lire AGENTS.md et RTK.md ; préfixer les commandes shell par `rtk`, généralement `rtk proxy`.

## Décisions et mesures

| Paramètre | Mesure de cette session | Décision finale |
|---|---|---|
| `rail_upgrade_failure_memory` | 40×10 : +43 436 £/an (+1,41 %), IC95 [−36 025 ; +129 681], p=0,6143, valeur +1,31 %, `fail_primary` | Adopté explicitement à 1 par l'utilisateur ; équivalence non démontrée. |
| `air_c121_physical_payment_days` | 100×3 : −37 302 £/an (−1,94 %), IC95 [−82 285 ; +7 779], p=0,2111, valeur −1,38 %, `fail_primary` ; non-infériorité −1 % non démontrée | Adopté explicitement à 1 pour cohérence et simplicité. |
| `v126_air_served_town_reuse` | Audit puis retrait demandé après synchronisation Git ; 18 contrats et smoke sains | Supprimé ; ne pas confondre avec V126 devis de coût AIR. |
| `c121_air_target_limit` | Audit puis retrait demandé ; 102 contrats, smoke et fixture VM/Save-Load | Supprimé ; helpers de cible partagés avec concurrence visible et garde finale d'achat préservés. |
| `c121_fleet_stock_growth` | Audit puis retrait demandé ; 91 contrats et smoke | Supprimé ; renfort unique sous cible, dates et champs partagés conservés. |
| `c121_territory_first` | 40×3 : +17 782 £/an (+0,91 %), IC95 [−45 573 ; +79 401], p=0,4125, 24V/16D, valeur +0,75 %. Puis 40×5 sur 40 autres graines : −28 478 £/an (−1,45 %), IC95 [−104 950 ; +50 744], p=0,3974, 18V/22D, valeur −2,13 %. Deux `fail_primary` | Rejet utilisateur et suppression ; dette UR-16d close. 78 contrats et smoke. |
| `c121_aaa_line` | 10×3 : −614 610 £/an (−32,97 %), IC95 [−875 851 ; −334 577], p=0,00586, 1V/9D, valeur −33,85 %. Verdict formel `diagnostic_only`, échantillon inférieur à 40 | Rejet utilisateur et suppression ; choix un/deux avions et départ opposé partagés préservés. 109 contrats et smoke. |
| `c121_air_observation_growth` | 100×3 : −50 966 £/an (−2,83 %), IC95 [−88 785 ; −12 279], p=0,00669, 38V/62D, valeur −5,142 %. `fail_primary_and_value_guard` | Supprimé ; 80 contrats et smoke. `c121GrowthReportYear` n'est plus écrit ni lu ; une ancienne clé restaurée reste inerte, Save/Load générique inchangé. |
| `c121_air_first_observation_growth` | 100×3 : +3 024 £/an (+0,17 %), IC95 [−15 683 ; +21 918], p=0,3875, 47V/38D/15E, valeur +0,20 %. `fail_primary` | Supprimé avec ses quatre sous-paramètres exclusifs ; 75 contrats et smoke. Variante live préservée. |

Les campagnes terminées ci-dessus étaient saines et complètes : 80 duels pour chaque 40 graines, 200 pour chaque 100 graines, 20 pour le 10×3. Les IC cités sont ceux du bootstrap de la moyenne. Pour le dernier test, l'utilisateur n'autorisait les essais numériques que si le principal était concluant : aucun essai séparé de `c121_air_first_growth_min_days`, `phase_years`, `late_days` ou `min_wait_pct` n'a été lancé. Leur retrait découle de l'abandon du parent, pas d'une réfutation mesurée individuellement.

Ces politiques de cadence sont comportementales à objectif économique, pas des optimisations d'opcodes. Aucun gain opcode n'a été mesuré pour justifier leur adoption.

## Référence et incident Docker

Après les trois premiers nettoyages, référence `cleanup_reference_10x5_20261011_1227` : 10 graines ×5 ans, 10 duels sains, sans variante. Profit Opex 1 875 417 £/an contre AAAHogEx 3 441 328 (−45,50 %, 0V/10D) ; valeur 6 570 172 contre 6 201 304 (+5,95 %). Ce n'est pas une mesure causale avant/après nettoyage.

Docker a été bloqué au démarrage par le renommage du socket AF_UNIX vsock1999 dans `C:\Users\jr\AppData\Local\Docker\vm-data`. Deux sockets transitoires ont été retirés après arrêt vérifié ; le problème a récidivé, puis Docker a été rétabli avant les campagnes. Le disque DockerDesktop.vhdx, images et volumes ont été préservés. Ne jamais supprimer/réinitialiser vm-data pour reproduire cette réparation. Toutes les campagnes C121 décrites ici sont terminées ; des campagnes AC indépendantes peuvent tourner, à vérifier.

## Rapports et preuves

- [Mémoire upgrade RAIL](rail_upgrade_failure_memory_40x10_20261010.md)
- [Paiement physique AIR](air_payment_100x3_20261010.md)
- [Référence 10×5](cleanup_reference_10x5_20261011.md)
- [Territoire 40×3](c121_territory_first_40x3_20261011.md) et [40×5](c121_territory_first_40x5_20261011.md)
- [AAA line 10×3](c121_aaa_line_10x3_20261011.md)
- [Croissance annuelle 100×3](c121_observation_growth_100x3_20261011.md)
- [Premier renfort annuel 100×3](c121_first_observation_100x3_20261011.md)
- [Journal détaillé](journaux/journal_2026-10-11.md)

Les JSON/JSONL, manifests, bundles et logs restent dans `results/` (principalement ignoré). Les rapports donnent les campagnes exactes ; ne pas choisir arbitrairement le dernier fichier. Les CSV des deux essais territoire sont dans `docs/archives/`.

## Git et travaux concurrents

Branche `master`, HEAD vérifié `edac183`. La référence locale `origin/master` est `436e1b5`, dernier push confirmé de cette session ; ce constat n'est pas un nouveau fetch distant.

- `5b05be9` : retrait réadmission AIR, plafond et stock-growth C121.
- `9168404` : bilan de référence 10×5.
- `bfdb2b9` : fusion documentaire préexistante.
- `3bccc8b` : retrait territoire et AAA line.
- `436e1b5` : retrait croissance annuelle ; poussé avec les commits précédents.
- `edac183` : retrait premier renfort annuel et quatre sous-réglages ; **committé, non poussé**, conformément à la dernière demande.

Les études AC-01 à AC-08, preuves AC04/05, correctifs catalogue, leurs scripts/tests et des passages de `docs/taches.md`/journal sont des travaux parallèles laissés locaux. Ne pas les ajouter globalement à un commit de nettoyage. Des correctifs isolés existent sous `results/ac_fixes_worktree_20261011` selon le backlog courant ; recontrôler leur état et les conteneurs sans les interrompre. Leurs critères économiques/opcodes particuliers ne doivent pas être transposés automatiquement aux paramètres de cette session.

La présente passation est documentaire, non committée ni poussée automatiquement.

## Prompt prêt à copier

```text
Nous poursuivons le nettoyage des paramètres obsolètes d'OpexAI dans
C:\Users\jr\vscode\openttd-ml\openttd-ml.

Lis AGENTS.md, C:\Users\jr\.codex\RTK.md, l'État courant de docs/taches.md et
docs/passation_nettoyage_parametres_20261011.md. Vérifie git status/diff avant
toute édition et préserve les études parallèles du catalogue AIR.

Dernier commit de ce chantier : edac183, non poussé. Le dernier push confirmé
était 436e1b5. Ne pousse rien sans nouvelle instruction. Les campagnes C121
de cette passation sont terminées ; aucun test de sous-paramètre n'est attendu.

Présente maintenant le prochain paramètre candidat au nettoyage : rôle réel,
défaut, usages, interactions, état Save/Load, historique et complexité du retrait.
Cette étape est une analyse uniquement : ne supprime rien et ne lance pas de banc.
Ne considère pas un drapeau OFF comme une preuve de code mort. Vérifie notamment
les défauts courants des variantes live avant d'en proposer le retrait : elles
ont été préservées intentionnellement et certaines sont actives/adoptées.

Les défauts rail_upgrade_failure_memory=1 et air_c121_physical_payment_days=1
ont été adoptés explicitement malgré des essais non concluants ; ne les annule pas.
Les politiques territoire, AAA line, croissance annuelle et premier renfort annuel
ont été retirées. Conserve les verdicts historiques et distingue perte significative,
gain non démontré et décision de simplification. Pas de réouverture implicite.

Si je demande ensuite un banc, utilise les harnais figés existants, pré-enregistre
bras/graines/critères, contrôle Docker et les campagnes AC concurrentes. PC local :
10 CPU/8 Go RAM/swap8 Go/10 workers ; VPS :3 CPU/3 workers/2 Go.
Si je demande un retrait, préserve les consommateurs partagés, adapte les contrats,
valide par smoke1×1 et documente le résultat. Commit/push seulement sur demande,
avec staging ciblé. Réponds en français.
```
