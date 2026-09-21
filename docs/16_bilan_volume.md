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
