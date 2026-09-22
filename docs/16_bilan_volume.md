# Bilan : pourquoi OpexAI fait 16 % du profit d'AAAHogEx, et quelles pistes dépendent du moteur de décision

**2026-09-21.** Inventaire préparé par agy à partir des docs, puis vérifié et corrigé ; les
chiffres ci-dessous ont été relus dans leur source. Deux affirmations d'agy sont retirées : le
« rendement par véhicule à 93 % » (retiré par `taches.md`, comptes non qualifiés) et la
recommandation de débrider les lots de flotte (testé aujourd'hui, inerte 10/10,
`14_suites_c69.md`, résultat du cas B).

## 1. L'écart, décomposé

Références des bancs C69 et C72 (20 graines × 10 ans en duel, comptes qualifiés C66.1) :

| | OpexAI | AAAHogEx | rapport |
|---|---:|---:|---:|
| profit annuel | — | — | **0,16** |
| véhicules pilotables | 98 | 365 | **0,27** |
| profit par véhicule | ~16 k£ | ~27 k£ | **0,60** |

L'écart vient **des deux** facteurs : le volume (×3,7) et le rendement par véhicule (×1,7). La
moyenne par véhicule mélange les modes ; la décomposition par mode ci-dessous est plus sûre.

**Par mode** (`08_opex_vs_aaahogex_same_markets.md`, duel 10 ans, 20 graines, 1979) :

- **AIR, le cœur de l'écart.** OpexAI ouvre presque **deux fois plus** de marchés (44,65 contre
  23,75) mais reste à **1,02 avion par marché** contre **3,00**. Sur les 30 marchés strictement
  communs, AAAHogEx gagne 28 fois sur 30 en profit (11,2 M£ contre 1,2 M£).
- **ROUTE : OpexAI est meilleur** sur les marchés comparables (93 victoires sur 108).
- **RAIL** : 4 marchés comparables seulement, pas de conclusion.

**La profondeur aérienne n'est pas un problème de fréquence** (`taches.md`, diagnostics du
2026-09-15) : sur les mêmes villes, OpexAI a un meilleur temps de collecte (4,6 contre 10,1 jours)
mais **60,5 £ de profit par place contre 322,6 £**. Ajouter des avions ne l'a jamais corrigé :

| forcer la profondeur | résultat |
|---|---|
| supprimer la réserve d'attente (C50b, 40×10) | valeur détruite 20/20 |
| seuil d'attente à 50 % | −240 k£/an, −32 % de valeur (graine 42) |
| 2e avion au palier de fréquence (5×6) | −124 k£/an, 0/5 |
| lots de renfort sans plafond (aujourd'hui) | inerte, 10/10 identiques |

Le verrou est **en amont** : les aéroports d'OpexAI voient passer beaucoup moins de passagers.
Constat descriptif, non causal (B9) : ceux d'AAAHogEx sont plus centraux (distance au centre 6,06
contre 7,47 ; centre couvert 37,9 % contre 20 %).

**Chronologie** : l'écart s'ouvre en **1971** (gares nettes créées sur 5 graines : 148 contre 72 en
1970, puis 57 contre 241 en 1971). La trésorerie bloque jusqu'en 1972-1973 ; ensuite la cause
dominante des non-chantiers devient la **décision** (92-94 %), et le rythme des passes du
portefeuille tombe de 168 à 18 pour 100 jours entre 1971 et 1975 (fiche 11 §1).

## 2. Les pistes de volume testées, et leur lien au moteur de décision

« Moteur » = le classement du portefeuille (P/C) et son débit (1 projet par passe).
⚠️ = mesure d'avant le 2026-09-09, archivée, à re-mesurer avant d'être citée comme preuve.

| piste | résultat | lien au moteur |
|---|---|---|
| `portfolio_max_batch` 4 ou 8 (⚠️ 3 ans) | valeur −3,8 %, véhicules −9,5 % | **direct**. Échec expliqué par la phase pauvre : le 1er chantier vide la caisse, un succès régénère le vivier et fusionne deux cycles. **Jamais testé en phase riche.** |
| `portfolio_floor_pct` (20×10) | 4 V / 16 D | direct : filtre dur contre le biais « bon marché d'abord » |
| C49 dénominateur variable (20×10) | 9 V / 11 D | direct |
| C69 / C69 bis (20×10) | +88 / +111 k£, 12 / 20 | direct |
| C72 choix d'avion (20×10) | neutre, 11 / 20 | direct (variante entrant au vivier) |
| `station_join` / vivier rouvert (⚠️ 20×20) | véhicules +37 %, valeur 0 % ; après traction +24 % / +6 % | possible : candidats ajoutés, classés P/C ; mais la cause retenue était la prédiction de l'étage 1 |
| C55 filtre d'origine fret (20×10) | neutre ; 86 % des rejets récupérés ne paient rien | faible : les candidats récupérés sont mauvais, quel que soit le classement |
| A5 rail segmenté (⚠️ 20×10) | gares +12,9 %, valeur −3,4 % | faible : candidats en plus qui ne paient pas |
| `fleet_before_new` (⚠️ 3 ans) | profit −20,4 % | ordre des tâches ; l'arbitrage flotte/ligne neuve a été testé sous C69 bis, sans succès |
| plafonds C50b route / rail / cadence (40×10) | route 27/40 perdues ; rail inerte (`NOSPOT`) ; cadence 21/40 | non : physique |
| profondeur AIR forcée (voir §1) | toujours négatif | non : la demande manque |
| `feeder_candidates` (5×6) | 1 V / 4 D, −105 k£ | non : concurrence avec `air_joined_stops` |
| `air_demand_plan` (20×10) | −51,5 %, 5/20 | non |

## 3. Ce qui dépend vraiment du moteur, et n'a pas été essayé

### 3.1 Plusieurs chantiers par passe, en phase riche seulement — piste n° 1

C'est la seule piste directement liée au moteur dont l'échec s'explique par les conditions du
test, pas par le mécanisme : le lot de 4 ou 8 projets a été rejeté **en 3 ans**, pendant la phase
où la caisse bloque. En 1974-1975, la caisse dort (1,3 à 3,3 M£) et les décisions sont 9 fois plus
rares qu'en 1971.

La théorie de C69 donne la règle **sans constante** : un projet moins cher que K_dec ne consomme
pas de capital mais une décision. On peut donc, dans une même passe, continuer à construire tant
que le projet suivant coûte moins que K_dec (et reste finançable). En phase pauvre (K_dec < C),
la règle reste 1 projet par passe, comme aujourd'hui, et le démarrage est intact par construction.

Risques connus : la régénération du vivier après un succès (le diagnostic du batch 8 montre qu'un
succès fusionne deux cycles) et le coût en opcodes (~38 k par ligne possédée et par
régénération).

### 3.2 La course aux aérodromes contre AAAHogEx — observation à creuser

OpenTTD 15.3 limite à 2 aéroports par ville ; 1 396 des 1 590 échecs de chantier aérien sont des
refus 771, dans des villes dont AAAHogEx tient déjà les deux places. Dans les deux bancs C69,
OpexAI ouvre ~5 aéroports de plus et réduit le nombre de villes où AAAHogEx a les deux places et
OpexAI aucune : −2,1 (15 graines sur 20) sous C69, −3,25 (16 sur 20) sous C69 bis. Le débit de décision est un levier de cette course, que le profit
prédit d'un projet ne voit pas. Non mesuré au-delà de ce constat.

## 4. Ce qui ne dépend pas du moteur, mais pèse le plus

**Le rendement aérien par place** : ×5 en faveur d'AAAHogEx sur les mêmes villes. Sa cause est en
amont (captage, placement, taille d'aéroport), pas dans le classement. La priorité « catchment /
placement AIR » de `taches.md` (2026-09-15) n'a donné qu'un constat descriptif (B9) ; aucune
mesure causale sur le placement ou le type d'aéroport n'a été faite.

## 5. Recommandation

1. **Batch sous K_dec** (§3.1) : un réglage, défaut 0, puis directement un 20×10 en duel après
   un smoke (le 5×6 solo ne prédit pas le duel).
2. En parallèle, et c'est le plus gros levier mesurable : **mesurer pourquoi un aéroport
   d'AAAHogEx capte 5 fois plus de passagers par place** sur la même ville (type, taille, position,
   couverture de la production), avant toute politique de placement.

Inventaire d'agy, non corrigé ligne à ligne : conservé hors dépôt dans le scratchpad de la session.

## 6. Mesure : pourquoi la caisse dort (C73, 2026-09-21)

Sonde passive (écrite par agy, relue : restructurations des filtres équivalentes à l'original,
tout est gardé par `probe_portfolio`), 3 graines × 10 ans, solo :
`results/diag_c73_vivier_10y_3seeds.json`, analyse `sweeps/analyse_c73_vivier.py`.

**Le vivier n'est pas vide, le capital n'est pas en cause.** À partir de 1971, aucune passe du
portefeuille ne trouve de vivier vide, tous les candidats sont finançables, et **chaque passe
construit**. Mais il n'y a que **4 à 9 passes qui construisent par an et par partie** :

| année | chantiers par partie (moyenne) | dont lignes aériennes / renforts de flotte | caisse moyenne |
|---|---:|---|---:|
| 1970 | 11,7 | 18 / 10 (3 graines) | 83 k£ |
| 1972 | 8,7 | 11 / 15 | 1,0 M£ |
| 1975 | 7,7 | 8 / 15 | 5,5 M£ |
| 1978 | 6,0 | 6 / 11 | 11,5 M£ |
| 1979 | 5,3 | 2 / 10 | — |

🔑 **C'est le goulot du volume.** OpexAI fait ~6 à 9 actions de construction par an, une par
passe, et **chaque renfort d'avion en consomme une** (`FLEET_PORTFOLIO` : la flotte passe par le
même portefeuille). Le rythme baisse d'année en année pendant que la caisse monte à 11,5 M£ :
la passe de régénération coûte de plus en plus cher (~38 k opcodes par ligne possédée, fiche 11
§1). Ce n'est pas un bug d'une ligne de code, c'est une limite de débit structurelle.

Cela relie plusieurs constats : 1,02 avion par marché (un avion de plus coûte une des ~8 décisions
de l'année) ; `portfolio_max_batch` rejeté en 3 ans, pendant la phase où la caisse bloque ; C69,
qui ne change que l'ordre, pas le nombre, de ces ~8 décisions.

## 7. Mesure : où passe le temps entre deux chantiers (C74, 2026-09-21)

Horloge de passe C39.6 (`probe_scheduler=1`, sonde existante), 3 graines × 10 ans, solo :
`results/diag_c74_passclock_10y_3seeds.json` (lignes brutes non versionnées, 328 lignes
`C39_PASS_CLOCK`). Jours de jeu par tâche de la file, moyenne par partie :

| tâche | 1971 | 1975 | 1979 | Mops par passe (1979) |
|---|---:|---:|---:|---:|
| tours de file par an | **31** | **8** | **7** | |
| `catalog` (catalogue + régénération complète du vivier + plan de flotte) | 111 j (32 %) | 108 j (31 %) | 110 j (30 %) | 2,76 |
| `town_growth` | 60 j (17 %) | 93 j (27 %) | 103 j (28 %) | 2,73 |
| `projects` (mise à jour incrémentale + sélection + **1 chantier**) | 95 j (27 %) | 81 j (23 %) | 83 j (23 %) | 2,21 |
| `air_fleet` | 45 j (13 %) | 46 j (13 %) | 45 j (12 %) | 1,18 |
| autres (report, expand, refleet, scrap, repay) | 39 j | 22 j | 22 j | |

**Lecture.** Un tour complet de la file prend **~45 à 52 jours de jeu** à partir de 1975, et
`projects` n'y construit qu'**un** projet. D'où ~7 à 8 chantiers par an (§6). Trois tâches de 2,2 à
2,8 M opcodes chacune remplissent le tour : `catalog`, `town_growth` et `projects`. Le vivier est
régénéré deux fois par tour (complètement dans `catalog`, incrémentalement dans `projects`).

⚠️ **Contradiction avec une clôture antérieure.** C39.5 (journal du 2026-09-13, mesure du
2026-09-10) a fermé les leviers de cadence parce que le vivier était **vide dans 58,6 % des tours** :
accélérer `projects` ne pouvait alors rien construire de plus. La sonde C73 (§6) mesure au contraire
un vivier **jamais vide après 1970** et un chantier à **chaque** passe. Le code a changé depuis
(C68, `early_slot`, retrait des feeders…) et les définitions de « vide » diffèrent peut-être ; la
prémisse de cette clôture ne tient plus sur le code courant.

**Leviers qui en découlent** (non testés sur le code courant) :

1. **plusieurs chantiers par passe en phase riche**, en construisant dans la liste déjà classée sans
   régénérer entre deux chantiers (c'est la régénération après succès qui avait fait échouer
   `portfolio_max_batch` en 2026-09-02, en plus de la caisse vide) ;
2. **raccourcir le tour** : `town_growth` prend 28 % du temps pour des lignes à profit nul par
   construction ; `catalog` et `projects` régénèrent chacun le vivier.

## 8. C75 — plusieurs chantiers par passe : smoke et mécanisme (2026-09-21)

Réglage `c75_multi_build` (défaut 0 ; implémenté par agy, relu, code C75 remis derrière son
drapeau). K_pass = F × τ_pass, τ_pass = durée réelle moyenne entre deux passes `projects`
(décision utilisateur). Après le 1er chantier, la passe continue dans la liste classée tant que le
projet suivant coûte moins que K_pass et reste finançable. 3 graines × 10 ans, solo, sonde :
`results/diag_c75_multibuild_10y_3seeds.json`, analyse `sweeps/analyse_c75_multibuild.py`.

| année | passes (3 graines) | chantiers | par passe | τ_pass médian | arrêt dominant |
|---|---:|---:|---:|---:|---|
| 1971 | 26 | 66 | 2,5 | 30 j | K_pass |
| 1972 | 18 | 89 | 4,9 | 46 j | fin de liste |
| 1973 | 15 | 81 | 5,4 | 73 j | fin de liste |
| 1975 | 11 | 43 | 3,9 | 91 j | fin de liste |
| 1977 | 11 | 18 | 1,6 | 91 j | fin de liste |
| 1979 | 5 | 14 | 2,8 | 122 j | fin de liste |

Sans le levier (§6) : 26 chantiers en 1972 et ~25 en 1975 pour les 3 graines.

- **Le mécanisme marche** : ×3 à ×3,5 chantiers en 1972-1973. Démarrage intact (1970 : K_pass = 0).
- **Mais le tour de file s'allonge** : τ_pass passe de 30 à 91-122 jours, parce que chaque ligne
  possédée renchérit la régénération. À partir de 1976, il n'y a plus que 1 à 4 passes par an et
  par partie, et **la liste s'épuise** à chaque passe : le vivier classé ne contient plus assez de
  projets constructibles. Les chantiers annuels retombent sous leur niveau sans levier.
- Profit final solo : 2 graines sur 3 en baisse (−3 % et −8 %), 1 en hausse (+8 %). Ce n'est pas un
  verdict (le solo ne prédit pas le duel), mais aucun gain évident.

**Lecture** : construire plus par passe déplace le goulot vers **la durée du tour** (régénération
complète à chaque passe, §7) et vers **la profondeur du vivier**. C'est un argument direct pour C76
(régénération pilotée par les événements) avant ou avec C75.

## 9. C75 au banc d'autorité 20×10 en duel (2026-09-21)

`results/c75_multibuild_vs_default_10y_20seeds.json` (PC de l'utilisateur), 20/20 paires.

| `c75` − défaut | moyenne | V / D | lecture |
|---|---:|---|---|
| **véhicules** | **+42 (+45 %)** | **19 / 0** (p = 4·10⁻⁶) | le volume monte massivement |
| note de gare médiane | +6 | 14 / 4 (p = 0,03) | le service s'améliore |
| aéroports | +2,45 | 13 / 4 | |
| **`profit_year`** | **+23 k£/an (+1,5 %)** | **10 / 10** (p = 1) | aucun gain |
| `company_value` | +1,8 % | 9 / 11 | aucun gain |
| rapport au profit d'AAAHogEx | +0,7 pt | 9 / 11 | dans le bruit (~3 pt) |

**Verdict : `fail_primary`.** `c75_multi_build` reste à 0.

🔑 **Le résultat le plus instructif de la journée : combler une partie de l'écart de volume ne
rapporte rien.** 42 véhicules de plus (19/0) pour +23 k£/an, soit ~550 £ par véhicule ajouté et par
an, contre ~16 k£ en moyenne. Les projets supplémentaires (ceux qui coûtent moins que K_pass, plus
bas dans la liste) ont une valeur marginale quasi nulle. `taches.md` l'avait écrit : « un réseau
plus gros n'est pas encore un rattrapage ». Le goulot n'est donc pas seulement le nombre de
décisions, mais **la valeur de ce qui est proposé au vivier** : la liste classée, sous le premier
rang, ne contient presque rien qui paie.

## 10. C75 + C69 bis : banc d'autorité et ADOPTION (2026-09-21)

`results/c75_c69bis_vs_default_10y_20seeds.json` (PC de l'utilisateur), 20/20 paires. Variante :
`c75_multi_build=1, c69_decision_bottleneck=1, c69_fleet_exempt=1, c70_mode_calibration=1`.

| variante − défaut | moyenne | V / D |
|---|---:|---|
| **`profit_year`** | **+96,4 k£/an (+6,3 %)** | **14 / 6** (p = 0,12) |
| **`company_value`** | **+490 k£ (+6,1 %)** | **14 / 6** |
| véhicules | +40 (+44 %) | 20 / 0 |
| note de gare médiane | +8 | 16 / 3 (p = 0,004) |
| rapport au profit d'AAAHogEx | +1,15 pt | 11 / 9 |

Verdict du harnais : `fail_primary` (14/20 contre 15/20 requis). Écart moyen au-dessus du seuil de
+50 k£, garde de valeur tenue (+6,1 %).

🔑 **Décision utilisateur du 2026-09-21 : adopté malgré 14/20.** Premier levier du jour où profit,
valeur et volume montent ensemble. Les quatre réglages passent à **1 par défaut** dans `info.nut`.
Contrôle : le nouveau défaut reproduit au bit près le smoke de la combinaison (graines 42 et 100,
3 ans : 3 440 770 et 2 078 509 £), `results/adopted_c75_c69bis_default_smoke_2x3.json`.

⚠️ À garder en tête : p = 0,12 au test des signes ; face à AAAHogEx l'écart reste dans le bruit
(+1,15 pt pour ~3 pt d'écart-type). Tout banc futur compare désormais à ce nouveau défaut.

## 11. `town_growth` : 97 % d'échecs répétés, et le mémo (2026-09-21)

**Diagnostic** (journal de décision, graine 42 × 6 ans, `results/tg.json`) : **407 échecs de
planification pour 14 lignes construites**. Les échecs sont géométriques (`TRACEX` 258, aucun
tracé ; `DEPOTX` 147, aucun dépôt) et portent toujours sur les **mêmes 20 villes**, replanifiées
jusqu'à 41 fois chacune. Une passe qui ne construit rien replanifie toutes les villes : d'où ses
2,7 à 5 M opcodes. Le journal du 2026-09-13 l'avait noté sans le traiter.

**Levier** `town_growth_plan_memo` (défaut 0) : une ville dont la planification a échoué n'est
replanifiée que si son nombre de maisons a changé (sa croissance est ce qui peut rendre un tracé
possible ; aucune constante).

**Incident de mesure trouvé en route** : `bench_v2` passait toutes les valeurs effectives à
OpenTTD, dont la ligne `[ai_players]` est lue sur ~1 024 caractères ; les réglages de fin d'ordre
alphabétique étaient ignorés (la première mesure du mémo comparait deux bras identiques). Corrigé
(`615cdf8`) ; bancs antérieurs non touchés (935 caractères sur `master`).

**Mesure** 3 graines × 10 ans, solo, défaut adopté, horloge C39.6 (`results/tgmemo_off.json`,
`results/tgmemo_on.json`) :

| année | jours `town_growth` / partie | M opcodes / passe | passes `projects` / an | jours par tour |
|---|---|---|---|---|
| 1971 | 62 → 20 | 0,37 → 0,07 | **31 → 57** | 11 → 6 |
| 1973 | 108 → 36 | 2,73 → 0,73 | 7,3 → 9,3 | 51 → 42 |
| 1975 | 118 → 25 | 4,69 → 1,03 | 5,3 → 5,0 | 79 → 76 |
| 1979 | 62 → 23 | 4,30 → 1,60 | 3,3 → 3,0 | 135 → 119 |

Coût de `town_growth` −70 à −80 %. Le tour ne raccourcit nettement qu'en 1971 ; ensuite la
régénération du vivier domine (sous le nouveau défaut, un tour dure 76 à 135 jours). Pas de signal
économique en solo sur 3 graines. Le levier prend tout son sens combiné à C76 (54 % de
régénérations évitées) : c'est la pile à bancer.
