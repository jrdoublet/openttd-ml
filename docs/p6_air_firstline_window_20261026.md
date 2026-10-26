# P6 — fenêtre du premier catalogue AIR (pré-enregistrement)

État : **pré-enregistré, non qualifié**. Base d'étude : `master` à partir de
`8a7cded9` (26/10/2026). Le commit et l'empreinte du bundle exécuté seront
reportés sur chaque campagne avant son lancement. Aucun défaut n'est adopté.

## Intervention isolée

- Réglage `p6_air_firstline_window`, témoin `0` et candidat `1`, **défaut 0**
  dans les quatre difficultés. Même code, mêmes autres réglages de `master`.
- Agir seulement au premier chantier AIR, après publication partielle du
  catalogue C78/C121 ; utiliser les projets déjà calculés, réellement valides
  et finançables. Réserver une courte fenêtre bornée de publication du scan
  déjà engagé, puis relancer la sélection normale. Aucun scan géométrique
  supplémentaire ni modification de la frontière des paires.
- Critères d'exposition : première ligne potentiellement différée, durée et
  opcodes consommés avant l'exécution, nouvelles publications, meilleur projet
  retenu, construction effective. Signaler aussi les cas sans fenêtre utile.
  L'exposition instrumentée reste **descriptive** ; le banc économique retire
  le journal de décisions.

## Séquence figée avant le premier moteur

1. Tests ciblés sur option OFF, sélection ON, bornage de l'attente, cas
   non-finançable, et reprise Save/Load court et complet ; suite Python complète,
   puis `git diff --check`.
2. Smoke **1 graine × 1 an**, graine `42`, deux duels appariés, carte `256²`,
   année initiale `1970`, mêmes réglages hors P6, santé et absence d'erreur Squirrel.
3. Exposition mécaniste d'au moins **5 graines prédéfinies** :
   `42 100 7 999 2026`, sans choix après lecture des résultats ; mesurer
   effectivement les fenêtres, constructions et coût par graine. Le journal
   éventuel est identique dans les bras et absent de la porte économique.
4. Porte **A 40 graines canoniques × 5 ans**, multimodale, `1970–1974`,
   `gain_short`, une répétition, 80 parties, `profit_year` Opex candidat moins
   Opex témoin à l'année terminale. Conditions **conjointes** : delta moyen
   ≥ `4 %` du profit moyen témoin, Wilcoxon exact bilatéral `p < 0,05`,
   borne basse de l'IC95 bootstrap de la moyenne `> 0` (20 000 tirages,
   graine bootstrap `0`), ratio des moyennes de valeur de compagnie `≥ 0,95`
   et parties saines. Horizon déclaré **5 ans avant lancement** ; ne pas
   sélectionner a posteriori un horizon ou un sous-groupe plus favorable.
5. **Uniquement si A passe** : porte **B 20 graines canoniques × 10 ans**,
   multimodale, `1970–1979`, `non_erosion`, une répétition, 40 parties ;
   borne haute de l'IC95 bootstrap ≥ 0, garde de valeur 5 %, santé complète.
   B ne prouve pas à elle seule un gain de long terme.

Le lanceur hôte est `sweeps/run_c66_reference.py` ; un seul conteneur Docker
à la fois, sur le PC `desktop-linux`, `--cpus 10 --memory 8g` et jusqu'à
`--max-workers 10` (9 si une autre charge est active). Préciser explicitement
`--required-seeds 40 --required-years 5 --years 5` sous `gain_short`.
Les noms de campagnes seront uniques, la publication et le verdict ajoutés
ici après vérification des archives complètes. Un échec de porte laisse le
réglage OFF et arrête la séquence P6.

## Objectif externe

Se rapprocher de **75 % des profits d'AAAHogEx à dix ans** (ratio des profits
moyens ou médiane des ratios de parties appariées, valeurs toutes rapportées
séparément). Ce ratio est descriptif ; le critère primaire des portes reste
le delta de `profit_year` d'OpexAI entre ON et OFF.
