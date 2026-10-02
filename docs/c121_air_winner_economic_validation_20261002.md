# C121 gagnant AIR : validation économique de la fusion

## Plan enregistré avant lancement

Demande utilisateur : « lance la validation économique dès que possible ».
Intervention isolée d'opcodes : `c121_air_winner_fusion` 0→1, ancien défaut
conservé pendant la qualification. Cette autorisation porte sur cette fusion,
y compris sa séquence de neutralité ; elle ne rouvre pas les politiques C121
rejetées ni l'adoption de l'économie C121.

Les deux bras utilisent `c121_air_economics=1,catalog_cost_probe=0`.
C121 étant désactivé au défaut, ce profil expérimental est indispensable pour
exposer la fusion. Le résultat vaudra pour cette optimisation dans ce profil,
pas pour le passage de l'économie C115 à C121. Le workflow ordinaire exigeant
les défauts courants ne convient donc pas ; le harnais causal C66 courant est
réutilisé localement, avec un contrôle séparé de neutralité déclaré avant mesure.

- Référence : `OpexAI[c121_air_economics=1,catalog_cost_probe=0,c121_air_winner_fusion=0]`.
- Variante : `OpexAI[c121_air_economics=1,catalog_cost_probe=0,c121_air_winner_fusion=1]`.
- Métrique : `profit_year` Opex variante − Opex référence.
- Critères économiques : borne supérieure IC95 Student du delta ≥0 ; pas de
  défaite significative aux signes (p≥0,05 ou victoires>défaites) ; garde de
  valeur, ratio des moyennes, ≥−5 %. Pas d'exigence de gain économique positif.
- Verdict brut `signs20`, seuil 50 000 £/an, conservé séparément ; il ne tranche
  pas la neutralité. Un `fail_primary` n'est pas transformé en `pass` ordinaire.
- Portes : smoke apparié 42 ×1 an, diagnostic 42/100/999/1234/5678 ×6 ans,
  puis 20 graines canoniques ×10 ans seulement si le diagnostic est complet,
  sain et respecte les critères de neutralité. Arrêt sur erreur/incomplétude.
- Docker : image exacte du pilote, 3 CPU, 2 Go RAM, swap plafonné à 2 Go,
  volume `openttd-lab-home`, au plus trois workers ; aucune autre campagne
  active au lancement. Aucun lancement direct d'OpenTTD.

Entrées figées depuis le pilote d'opcodes :
`results/c121_winner_integration/20261001_measure_on42_r1/ai/OpexAI`.
Les défauts sont ceux de cette copie, pas les modifications concurrentes du
workspace. Même arbre dans les deux bras, une seule différence de réglage.
Le reçu de démarrage est identique et indique les gates effectivement chargées ;
la sonde coûteuse du catalogue est désactivée. Sources, adversaire, harnais,
bibliothèques et runtime sont enregistrés et figés avant les parties.
Les bibliothèques du cache sont vérifiées par leurs hashes avant copie et servies
par les descripteurs figés existants. Aucun extracteur/moteur n'est remplacé.

Preuve d'opcodes antérieure distincte :
`results/c121_winner_integration/20261001_summary_r2/report.json`.
Les fixtures prouvent l'équivalence des sorties à entrées identiques ; elles ne
prouvent pas la neutralité du calendrier économique. Le plan, les manifestes et
les résultats économiques seront conservés sous
`results/c121_winner_economics/20261002_neutrality_r1/`.

Lancement/suivi : `sweeps/run_c121_winner_economic_validation.py` réutilise le
lanceur hôte et le harnais figé C66. Il enchaîne les portes, conserve le verdict
brut et écrit les critères séparés. Il ne modifie aucun défaut.

## Suivi du lancement

Dépôt hôte : `C:/Users/jr/vscode/openttd-ml/openttd-ml`, branche
`c121-catalog`, HEAD `52ab55537dcf18a0ded8700bc9ac73833ac369a5`, arbre sale.
Les fichiers réellement exécutés sont ceux du bundle figé, pas tous les
changements du checkout. Hash commun smoke/diagnostic :
`036d783bce8b9f9a0957621a4aba730f57864bf0de76a940db19730b4fdbe8b2`.

Après attente de Docker, smoke lancé puis terminé : 2/2 parties, santé OK,
comparaison et couverture complètes. Verdict brut `diagnostic_only`, aucun
verdict de neutralité sur une graine. Diagnostic démarré ensuite :
`20261002_neutrality_r1_diagnostic`, dix duels attendus sur cinq graines ×6 ans.
Manifestes contrôlés : même bundle, mêmes politiques, seule différence
effective `c121_air_winner_fusion` 0→1. Inspect Docker : 3 CPU,
2 147 483 648 octets RAM et memory-swap, volume de cache et copie isolée
du dépôt montée en `/work`. Aucun défaut changé.

Rapports et manifestes :
`results/c121_winner_economics/20261002_neutrality_r1/inputs/results/`.
Le lanceur enchaîne le 20×10 seulement si le diagnostic respecte la règle
pré-enregistrée. Aucun verdict final annoncé pendant son exécution.

### Diagnostic terminé et ressources locales autorisées

Diagnostic : 10/10 duels complets et sains, 5/5 paires, couverture métrique
complète. Opex ON−OFF : profit moyen −77 880,4 £/an, médiane −193 439 £/an,
IC95 Student [−444 536,5 ; +288 775,7] £/an, 2 victoires/3 défaites,
p exact bilatéral=1. Valeur, ratio des moyennes : +0,843149 %.
Verdict brut `diagnostic_only`. Le contrôle de neutralité pré-enregistré permet
le passage au 20×10 ; cinq graines ne prouvent pas encore la neutralité.

L'utilisateur autorise ensuite **10 CPU et 10 workers sur ce PC**. Le diagnostic
terminé reste conservé, sans relance. L'ancien contrôleur, alors uniquement
en attente de Docker, est arrêté ; aucun moteur de partie n'est arrêté.
Reprise avec `--resume --local-fast` : smoke et diagnostic retenus, seul le
20×10 restant passe à 10 CPU/10 workers. Limite mémoire conservée à 2 Go,
volume cache conservé, context Docker `desktop-linux` vérifié. Le profil VPS
reste 3 CPU/3 workers. Une seule campagne de ce chantier au lancement.

Amendement, déclaré avant lancement du 20×10 :
`results/c121_winner_economics/20261002_neutrality_r1/local_resource_amendment.json`.
Sources IA/harnais et critères économiques restent inchangés. Le lanceur
attend automatiquement la fin des autres conteneurs avant le 20×10.

## Validation terminée et adoption de la fusion

Campagne exacte : `20261002_neutrality_r1_adoption`, 20 graines ×10 ans,
40 duels distincts attendus et obtenus, 20/20 paires. Santé OK, aucun échec,
comparaison, échantillon d'adoption et couverture complets ; quatre trimestres
valides dans toutes les mesures annuelles finales, dix points annuels par paire.
10 CPU/10 workers effectivement enregistrés ; image exacte et mémoire 2 Go.
Même bundle smoke/diagnostic/adoption, hash intact ; seule différence effective
de réglage fusion0→1. SHA Git hôte inchangé, arbre sale décrit dans le manifeste.

| Critère pré-enregistré | Résultat final | Contrôle |
|---|---:|---|
| Profit annuel moyen ON−OFF | −68 492,1 £/an | Pas de seuil de gain positif pour une optimisation d'opcodes |
| Médiane du delta | −107 808 £/an | Descriptif |
| IC95 Student du delta moyen | [−243 588,6 ; +106 604,4] £/an | Non entièrement négatif |
| Victoires / défaites / égalités | 7 / 13 / 0 | Défaite non significative |
| Test exact des signes, bilatéral | p=0,263176 | p≥0,05 |
| Valeur : ratio des moyennes ON/OFF | −3,521728 % | Garde −5 % tenue |

**Accepté selon la règle de neutralité des optimisations d'opcodes définie avant
mesure.** Cela ne prouve pas une égalité des profits : le point estimé est négatif
et l'incertitude est large. Le verdict brut ordinaire reste `fail_primary` ; il
n'est pas réécrit en `pass`, et aucune qualification de l'économie C121 elle-même
n'en découle. Le gain d'opcodes provient du pilote séparé, avec ses limites de mix.

| Graine | Delta profit £/an | Delta valeur £ |
|---:|---:|---:|
| 42 | 220 566 | 1 023 714 |
| 100 | 83 311 | −291 345 |
| 7 | −355 060 | −1 416 497 |
| 999 | −78 770 | −455 393 |
| 2026 | −387 070 | −874 036 |
| 1 | 267 961 | 1 158 771 |
| 17 | −456 798 | −1 391 776 |
| 73 | −328 667 | −692 496 |
| 314 | 804 332 | 3 960 727 |
| 512 | −154 844 | −1 250 807 |
| 1024 | −462 383 | −2 344 990 |
| 1337 | 481 193 | 2 547 020 |
| 4096 | 298 113 | 808 442 |
| 8191 | −60 620 | −906 499 |
| 12345 | −124 413 | −125 126 |
| 54321 | −96 171 | −205 031 |
| 65537 | −659 961 | −3 526 745 |
| 123456 | −517 206 | −2 554 299 |
| 424242 | −119 445 | −1 040 104 |
| 8675309 | 276 090 | 1 109 790 |

Conformément à la demande utilisateur « si ça fait gagner des opcodes et que
c'est neutre on valide », seul le défaut `c121_air_winner_fusion` passe à **1**,
aux quatre difficultés. `c121_air_economics` reste **0**, C115 reste protégé,
les autres gates ne changent pas. Le chargement conserve la dépendance à C121 ;
au défaut livré, la fusion est donc inactive tant que ce profil n'est pas utilisé.
La fusion ne crée aucun état persistant : réglage rechargé dans `Start()` avant
réconciliation, sorties locales et caches reconstructibles inchangés.

Core livré identique au core testé (`8c4a84fbc637…`). 109 contrats ciblés réussis
après adoption. Les deux anciennes fixtures fixent désormais explicitement
fusion=0 pour conserver leur témoin après le changement de défaut.
Smoke solo du défaut livré, sans overrides de réglages :
`results/c121_winner_integration/20261002_default_smoke42_r1/report.json`,
pass, santé OK, treize dates mensuelles exactes, reçu fusion=0/probe=0 conforme
à la gate C121 désactivée, sources/copie inchangées. Pas de commit/push/merge.

Preuves brutes immuables :
`results/c121_winner_economics/20261002_neutrality_r1/inputs/results/20261002_neutrality_r1_adoption.json`,
son manifeste, JSONL, bundle et logs. Manifest SHA256
`b0c3aa700db8b10e2661455ae62b9f42635a2e6dc1e75549bcf1243926e4e879`.
[Audit compact, hashes et deltas par graine](../evidence/review/c121_winner_fusion_20261002/summary.json).
Cet audit dérivé ne remplace pas les campagnes brutes ni l'index historique.
La validation est limitée à la fusion dans le profil figé testé ; elle ne
qualifie pas les autres modifications concurrentes du dépôt.
