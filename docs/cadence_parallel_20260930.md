# Reprise des lots de cadence — 30 septembre 2026

## Périmètre et état initial

Demande : reprendre les travaux pour rattraper AAAHogEx, avec un plafond autorisé
de **12 CPU / 12 workers au total**. Docker Desktop local : 16 CPU, environ 4 Go
de RAM. Un seul conteneur de parties à la fois, **2 Go sans swap** ; pas de
modification des limites du VPS. Intégration sans délégation : inspections
parallèles, intégration séquentielle, parties parallèles. Lors de la clôture,
un agent a effectué un audit indépendant en lecture seule des résultats et logs ;
aucune implémentation supplémentaire déléguée n'est revendiquée.

Trois prototypes et leurs tests étaient déjà présents, mais les flags globaux,
les réglages et les raccords de `main.nut` manquaient. Intégration de l'existant,
pas revendication de trois implémentations nouvelles. Le lot flotte évoqué dans
le contexte (`test_parallel_fleet_profit_contract.py`) n'est pas présent.
Git absent et copie sans `.git` : aucun diff historique fiable, commit ou push.

## Lots indépendants, tous OFF par défaut

| Réglage | Hypothèse | Limites conservées |
|---|---|---|
| `exp_c83_watch_daily` | Détecter un créneau menacé au premier contrôle disponible de chaque journée, avant arbitrage | Même top-six et même politique C83 ; pas de scan carte/site, pas de retry C122 ni de réserve financière ; un appel synchrone long peut toujours retarder le contrôle |
| `exp_scheduler_skip_not_due` | Sauter dans le même scan les rapports/remboursements déjà traités | Un tour borné de file ; **catalogue exclu**, ses gardes ont des effets ; pas de priorité flotte ni hausse du batch |
| `exp_air_hub_pair_prefilter` | Ne pas évaluer coûteusement les paires de centres urbains déjà reliées en AIR | Index local au contexte, symétrique, même rejet final ; pas de déduplication des variantes de projets libres ; aucun cache persisté |

C115 et tous les autres défauts conservés. C121/C122 et les politiques territoriales
rejetées ne sont pas réactivés. Les observations/horloges P4 sont transitoires,
réinitialisées après la réconciliation au chargement.

## Corrections et tests

- `globals_pre.nut`, `settings.nut`, `info.nut`, `main.nut` : raccordements des
  trois prototypes, quatre difficultés à zéro pour chaque réglage.
- Test P7 réparé : `cls.run` écrasait `unittest.TestCase.run` par une chaîne ;
  renommé `run_source`, sans suppression d'assertion.
- **95 tests ciblés OK** : prototypes, C83/C77, R3/R5 et nouveau collecteur.
- Contrat historique `test_sched_idle` réconcilié : la sonde V95 reste passive,
  le nouveau sélecteur exige son propre réglage OFF. Suite complète finale :
  **898 tests, 896 réussites, 1 erreur Git absent, 1 skip**. L'erreur restante
  est `test_c80_rail_stock_worker` (`git show 6895781:...`), non masquée.
- Smoke solo 4 bras × 1 graine × 1 an, sondes identiques : **4/4 sains**,
  `results/smoke_exp_parallel_20260930_r2.json`. Le premier lancement r1 a été
  refusé avant partie faute d'autorisation explicite du socle commun de sondes.
- Smoke duel 4 bras × 1 graine × 1 an : collecteur exécuté,
  `results/diag_cadence_smoke_20260930_r1.json`. Les deltas économiques courts
  ne constituent pas un gain ; le diagnostic long doit conserver le témoin courant.

## Protocole fixé avant le diagnostic 5×6

`sweeps/diag_cadence_duel.py` compare **quatre bras** : défaut courant, puis chacun
des trois réglages isolément à 1, toujours contre AAAHogEx-115. Graines
42/100/999/1234/5678, 1970–1975 ; arrêt au 1er février 1976 pour lire les 24
trimestres clos. **Aucune pile combinée à cette étape.**

- Critère principal descriptif : moyenne des ratios annuels Opex/AAA par graine,
  avec deltas appariés en points et détail par graine à l'horizon.
- Garde économique : publier profit Opex, profit AAA, écart O−A et valeur Opex.
  Effet utile propre fixé à **+50 k£/an**, garde de valeur **−5 %** ; ne pas
  sélectionner un candidat sur la seule baisse du concurrent.
- Exposition : smoke séparé `--probe` (decision_log et probe_portfolio symétriques,
  niveau script=4). Duel économique sans ces sondes.
- Réutilisation de `extract_company_record`, `assess_game`, capture des échecs
  moteur et des décodeurs actuels. Logs et checkpoints mensuels par partie.
- Refus d'agrégats si partie absente/dupliquée/invalide, année incomplète,
  ratio indéfini, dernier checkpoint mal aligné ou sources modifiées en cours.
- Empreintes avant/après et réglages effectifs conservés, mais **pas de bundle
  immuable ni de SHA Git** : diagnostic local, pas qualification d'adoption.

## Résultats du diagnostic complet

`results/diag_cadence_5x6_20260930_r1.json` et son dossier `.artifacts` :
**20/20 parties saines**, `complete=true`, `sources_unchanged=true`, sortie 0,
sans OOM. Conteneur `opex-cadence-5x6-r1`, 12 CPU / 12 workers, environ 4 minutes.
Image : `sha256:69d7e57aad5d3036f16655e8af23f36aa9fbb7c82c61ea325192c56b50e48e47`.

Moyenne des ratios annuels par graine, en pourcentage :

| Année | Référence courante | Watcher | Scheduler | Préfiltre hubs |
|---|---:|---:|---:|---:|
| 1970 | 57,78 | 63,48 | 57,71 | 54,54 |
| 1971 | 49,72 | 51,12 | 56,50 | 55,30 |
| 1972 | 53,72 | 49,99 | 56,00 | 53,90 |
| 1973 | 44,86 | 39,41 | 44,88 | 48,12 |
| 1974 | 37,37 | 32,29 | 44,05 | 41,40 |
| 1975 | 30,73 | 28,57 | 31,82 | 32,46 |

Comparaison appariée variante moins référence, **profit de 1975**, pas cumul :

| Variante | Δ profit Opex moyen / médian (k£/an) | Victoires profit Opex | Δ profit AAA moyen (k£/an) | Δ ratio moyen / médian (pts) | Δ valeur Opex |
|---|---:|---:|---:|---:|---:|
| Watcher | −114,33 / −44,97 | 1/5 | +224,65 | −2,16 / −1,89 | −8,16 % |
| Scheduler | −17,18 / −11,97 | 2/5 | −241,84 | +1,08 / +1,38 | +4,85 % |
| Préfiltre hubs | −25,23 / +64,05 | 4/5 | −255,58 | +1,73 / −0,50 | +4,66 % |

La valeur est comparée sur les sommes des cinq compagnies Opex. Victoires :
contre Opex dans la référence appariée, pas contre AAA. Aucun bras ne dépasse
AAA en profit 1975 sur une graine. Le témoin courant n'est pas le précédent
C115 à 32,6 % : utiliser exclusivement le témoin de ce même diagnostic.

Deltas profit Opex par graine (k£/an) :

| Graine | Watcher | Scheduler | Préfiltre hubs |
|---|---:|---:|---:|
| 42 | −36,92 | −200,73 | −545,22 |
| 100 | +53,45 | +98,06 | +13,37 |
| 999 | −472,02 | +176,73 | +254,42 |
| 1234 | −44,97 | −148,01 | +64,05 |
| 5678 | −71,19 | −11,97 | +87,23 |

Comptes physiques moyens au **01/02/1976**, Opex / AAA :

| Bras | Aéroports | Avions principaux |
|---|---:|---:|
| Référence | 25,2 / 40,8 | 100,2 / 50,6 |
| Watcher | 24,0 / 42,4 | 99,8 / 48,6 |
| Scheduler | 26,0 / 38,8 | 106,6 / 42,2 |
| Préfiltre hubs | 25,0 / 40,4 | 107,2 / 46,4 |

Ces comptes ne prouvent ni capacité utile, ni rentabilité marginale ; le profit
publié couvre tous les modes. Ils n'autorisent pas un plafond arbitraire de flotte.

## Exposition séparée

`results/diag_cadence_exposure_20260930_r1.json` : quatre duels, graine 42,
un an, sondes symétriques, complets et sains. Logs conservés dans `.artifacts`.

- **Watcher** : dernier résumé, 33 contrôles, 198 villes observées cumulées,
  15 changements, **0 enqueue**, 98 419 opcodes cumulés et intervalle maximal
  **38 jours**. Détection ville 18 avancée du 17 mars au 18 février, mais
  `already_funded` : aucune régénération ajoutée. Ce coût n'est pas un gain net.
- **Scheduler** : 7 sauts exposés (6 rapports, 1 remboursement), économie nette
  d'opcodes non mesurée.
- **Hubs** : 9 constructions d'index ; bilan `C69_BOTTLENECK` 1970 :
  **12 rejets hub-site et 43 hub-hub**. La recherche des seuls événements
  `C78_AIRPAIR outcome=...` n'en trouvait pas : les compteurs agrégés prouvent
  néanmoins l'exposition. Coût net index/consultations/évaluations évitées inconnu.

L'exposition un an ne prouve pas l'intensité du mécanisme sur les cinq graines
du diagnostic long. Sources IA identiques ; un contrat Python de test a été
réconcilié entre les deux campagnes, sans modification du code de jeu.

## Sauvegarde/rechargement technique

`results/save_load_exp_cadence_20260930_r2.json` : graine 42, phase A deux ans,
reprise du 01/01/1971 pendant un an, **trois options ensemble**, avec
`decision_log=1,probe_portfolio=1`, script=4. Combinaison technique uniquement,
aucune comparaison économique de cette pile.

- 25 sauvegardes A, 13 B ; sortie 0, sans OOM, aucun marqueur fatal/échec Save/Load.
- `LOAD_RECONCILE saved=11 kept=11 dropped=0`, puis progression au 01/01/1972.
- Après chargement : 9 résumés watcher, 3 sauts scheduler, 6 index hubs.
  Premier résumé watcher : `polls=1 towns=6`, état transitoire réinitialisé.
- 17→33 entrées stations et 28→85 entrées véhicules selon le harnais historique
  (pas les compteurs physiques qualifiés du duel). Une compagnie humaine fantôme
  apparaît au reload : limite connue, pas validation de tous les scénarios métier.
- Le lancement r1 a échoué **avant simulation** sur les droits du nouveau volume.
  Droits corrigés sur ce volume seulement, puis r2 ; anciennes sauvegardes hôte
  préservées. Sauvegardes nouvelles dans le volume `opex-cadence-saveload-r1`,
  monté sur `/work/.scratch_saveload`, cache existant réutilisé séparément.

## Décision et travail restant

**Aucun changement de défaut, aucune adoption, aucun 20×10 lancé.** C115 conservé.
Les trois options restent OFF. Cinq graines donnent un signal diagnostique, pas
une preuve statistique de gain ou de neutralité.

- Watcher : formulation diagnostique défavorable, garde de valeur dépassée ;
  étudier les longs blocages et détection→action avant toute nouvelle variante.
- Scheduler : ratio meilleur mais profit propre moindre ; mesurer coût net et
  délai jusqu'à une tâche utile, sans famine ni admission du catalogue.
- Hubs : quatre victoires profit mais forte perte sur 42 ; expliquer les
  trajectoires 42/999 et mesurer l'économie nette avant de poursuivre.

Pas de relance identique jusqu'à résultat favorable ; pas de bundle immuable,
SHA Git, commit, push ou exécution GitHub revendiqués.