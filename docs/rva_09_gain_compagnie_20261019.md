# RVA-09 — gain compagnie séparé et comparabilité

19/10/2026, base `11c859f`. **Contrat calculable à blanc et audit livrés ;
estimateur réseau non établi**. Aucun score ni achat modifié.

## Calcul indépendant de la mesure

`sweeps/rva_company_gain.py:11` reçoit recettes finales de la ligne, exploitation,
amortissement et effets **après − avant prévus** sur chaque desserte propre.
Identité du contrat RVA-02 (`docs/rva_01_03_20261018.md:160`) et du plan §1 :

```text
profit_ligne = recettes_finales - exploitation - amortissement
effet_desserte = variation_recettes - variation_coûts_évitables
gain_compagnie = profit_ligne + somme(effets_desserte)
```

Le capital reste séparé ; la demande physique n'est pas réduite par l'effet
réseau. Une baisse de clientèle d'un avion conservé ne fait pas disparaître
ses coûts fixes : leur variation est nulle, sauf variation évitable explicitement
prévue. Aucun facteur de perte forfaitaire ni coefficient de recalage ajouté.

Chaque effet exige source, même contexte, horizon, monnaie et année économique.
Sans inventaire complet des dessertes affectées ou avec un seul effet inconnu,
le gain compagnie reste inconnu, même si le profit de ligne est connu. Un zéro
exige une hypothèse explicite d'inventaire complet, pas une liste vide accidentelle.
Le calcul conserve `causal_measurement=false` : des prévisions fournies ne
deviennent pas une mesure causale. Les recettes de transfert sont refusées ;
seules les recettes finales compagnie peuvent entrer dans la ligne de revenu.

Les corrections portent un champ cible ; une double correction du même champ
est refusée. Une demande déjà réduite en « incrément compagnie V216a » ne peut
pas être réutilisée comme demande physique puis repénalisée par les externalités.
Le helper ne supprime aucune correction active et n'est pas branché au jeu.

`sweeps/rva_company_gain.py:62` contrôle que **toutes** les alternatives portent
un gain compagnie connu au même horizon/unité/contexte. Il refuse rail net contre
AIR brut, sans inventer un score, une admission ou un achat. RVA-14 reste distinct.

## Audit du portefeuille courant

| Chemin | Contrat effectivement lu | Conséquence pour une activation future |
|---|---|---|
| Rail voyageurs | `ai/OpexAI/economy.nut:401` : revenu − exploitation − amortissement ; `:478` : V212 après dimensionnement | Ce profit ne porte pas un effet réseau séparé. Les facteurs V212 restent neutres. |
| Demande rail V216a | `ai/OpexAI/candidates.nut:701`, `probe_v216.nut:419`, `:437`, `:451` | Le mode 1 réduit déjà la demande par un proxy de gain. Il faut substituer ce rôle **pour le seul chemin expérimental**, sans réduire la fréquentation physique ni appliquer deux pénalités. Aucun changement ici. |
| AIR C121 | `ai/OpexAI/air_economics_c121.nut:724`, `:750`, `:760` | `revenueAnnual` soustrait déjà `cannibalLossAnnual`. Le lire comme revenu de ligne brut puis soustraire une perte RVA doublerait l'effet. |
| Corrections C70 | `ai/OpexAI/projects_models.nut:160` | `profitAnnual` brut reste distinct de son profit calibré ; exemptions observation/réalisation/flotte à respecter. Un nouveau gain net n'hérite pas automatiquement d'une calibration apprise sur un profit de ligne. |
| Classement | `ai/OpexAI/projects_selection.nut:614`, `:786` | `fundScore` consomme `OpexProjectFundProfit` et un dénominateur C69/financement. Modifier une valeur de revenu ne rejoue pas ce classement complet. |
| Financement | `ai/OpexAI/projects_finance.nut:8` | `budgetCapital`, devis réel et contraintes de caisse restent séparés du profit annuel. |

Le fret, la route et les renforts gardent leurs contrats courants. Le présent
audit ne prouve pas que tous leurs profits sont des incréments compagnie au
même horizon, et ne leur applique aucune pénalité nouvelle. Aucune famille
protégée modifiée, aucun AddSetting ajouté.

## Validation, blocage et MESURE REQUISE

Six contrats dans `sweeps/test_rva_company_gain.py:7` : cannibalisation, coûts
réellement évitables, capital/demande séparés, effet absent/inventaire incomplet,
transfert/double correction refusés, contextes/dessertes dupliquées, comparaison
rail net/AIR brut. Fixtures synthétiques, pas preuve de performance.
Suite complète depuis la racine, commande demandée :
`python3 -m unittest discover -s sweeps -p "test_*.py"` :
**2 058 tests OK**, 3 ignorés, 8 échecs attendus ; `git diff --check` vert.
Les tests Python ne valident ni compilation Squirrel ni exécution du moteur.

Les journaux RVA existants relus et hashés dans le rapport RVA-08 ne contiennent
pas les emprises locales ni les effets réseau contrefactuels. Le bilan V216 et
ses totaux ville ne fournissent pas ces entrées par projet. On ne peut donc pas
annoncer RVA-08/09 achevés en modèle vivant, ni lancer RVA-16 sur un gain net connu.
RVA-05 reste aussi non validé sur des ressources NewGRF réelles. **Arrêt des
étapes dépendantes : RVA-10 exige 05/08/09, puis 11→12→13→14→15→16.**
Le plan interdit lui-même de transformer une donnée absente en zéro ou de
consommer un modèle insuffisamment couvert (`plan_rail_voyageurs_adaptatif_20261017.md`, §4.7).

Commande diagnostic VPS exacte, préparée **sans exécution**, sur le code courant :

```bash
python3 sweeps/run_c66_reference.py --campaign rva09_observables_complet_3x3_20261019 --reference 'OpexAI[probes=258]' --rva-profile qualifications/profiles/rva_vanilla.json --start-year 1970 --years 3 --seeds 42 7 100 --repeats 1 --cpus 3 --memory 2g --max-workers 3 --script-debug --line-telemetry --line-telemetry-monthly --station-supply-telemetry --retain-savegames results/rva09_observables_complet_3x3_20261019_saves
```

Cette commande collecte les observables **actuels** et les sauvegardes pour
auditer sites/compositions/services ; elle ne collecte pas magiquement une
demande contrefactuelle et ne résout pas seule le blocage. Aucune porte économique.
Avant une mesure dédiée des volumes locaux, il faut définir puis implémenter
une collecte/estimation accessible en NoAI, par profil, avec provenance et
incertitude. Les futures mesures ne doivent pas être présentées comme déjà faites.

Prochaine action : terminer la couverture RVA-05 et l'estimation locale RVA-08,
puis établir l'effet réseau RVA-09 avant les dépendances aval. Ne pas activer
un paquet fixe V207/V212 ni choisir une correction RVA-16 à partir du seul cycle
historique proche du modèle. RVA-17/18 restent hors mission.
