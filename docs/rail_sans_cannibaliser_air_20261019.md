# Rail voyageurs et aérien : par où passe l'éviction (19/10/2026)

Question de l'utilisateur : comment augmenter le rail en partie complète sans
cannibaliser l'aérien. Analyse sur des données existantes, sans partie nouvelle,
puis expositions de la correction.

Scripts jetables du job : `canal.py` (appariement par graine et par paire de
villes), `dose.py` (dose-effet par graine), `overlap.py` (recouvrement gare /
aéroport).

## Données

- `v207v212seuls_complet_10x3_20261016` : bras `off` contre `pax`
  (V207 part 40 + courrier + 2 arrêts joints, V212 150/85), 10 graines, 3 ans.
- Branche `v275` : `v275_expo_mm2_10x3_20261019` (paquet + V212, sans garde),
  `v275_expo_mm7_10x3_20261019` (gardes de ville et d'année),
  `v275_expo_railseul_10x3_20261019`, `v275_expo_mm7_3x10_20261019`.

## Ce qui n'est PAS le canal

- **La caisse, après 1971.** Fin 1972, le bras `pax` a *plus* d'argent que `off`
  (1 070 contre 832 k£, emprunt 37 contre 120 k£), mais 44 avions contre 55.
  En 1971 l'emprunt est au plafond dans les deux bras : la caisse ne joue
  qu'un rôle mineur (−0,3 à −1,2 aéroport).
- **Le créneau rail pris au fret à 10 ans** (mon hypothèse sur le 3×10 V275=7) :
  pas de gonflement du vivier dans ces parties, et deux paires seulement,
  dans le bruit de perturbation d'opcodes à 10 ans (±560 k£). Non démontré.

## Canal 1 — le vivier rail gonflé affame l'aérien en opcodes (code du 16/10)

- Ablation du 16/10 : avec le paquet voyageurs, la génération rail **garde ~300
  candidats** contre ~20 (`VIVIER_GEN mode=rail produced=427 kept=309`, graine
  100). Un seul créneau de recherche rail : ils ne se construisent pas et le
  vivier ne se vide plus (`VIVIER_MIX rail=269 air=1` d'avril 1971 à fin 1972).
- La resélection parcourt tout le vivier : 335 k opcodes par passe contre 46 k.
  En 1972, par partie : **13,4 M opcodes de sélection contre 3,7 M** (≈ 20 %
  contre 6 % du budget annuel, 18,5 tours × 10 000 opcodes par jour). Tâches
  63 contre 114 par partie, catalogue 0,8 contre 2,2, scans aériens 1,5 contre
  4,9 ; AIR_BUILD 52 contre 120 et renforts 16 contre 63 (10 graines). Chaque
  mois, `projects` écarte trois paires voyageurs `search_in_progress` et ne
  construit rien d'autre.
- Dose-effet par graine : corr(Δ opcodes de sélection, Δ profit 1972) = −0,61.
- **Sur le code actuel ce canal est secondaire** : `mm2` (19/10) gonfle moins
  (vivier 93 contre 50) et sa perte ne suit pas les opcodes (corr +0,09).
  Plafonner le vivier (bit 8 testé, 20 voyageurs + 20 fret) ne sauve pas le
  multimodal (−188,6 k£/an, 2/8, p = 0,01) et **coûte ~200 k£ en rail seul**
  (+410 k contre +609 k, références identiques au centime) : un vivier large y
  sert à mieux choisir. Rejeté.

## Canal 2 — partage des voyageurs dans nos villes à aéroport (dominant)

- Sans DistCargo (`distribution_pax = DT_MANUAL`), une maison couverte par notre
  gare et notre aéroport partage ses voyageurs entre les deux ; le voyageur vaut
  bien plus en avion (distance × vitesse).
- Le rail voyageurs vise les grandes villes, qui sont nos meilleures villes
  aériennes (81 k£ par aéroport contre 51 k£ ailleurs).
- Exposition sans garde avec plafond (`v275cap_expo_mm10_10x3_20261019`, 1972) :
  aéroports des villes où nous posons une gare voyageurs **81,5 → 53,7 k£
  (−34 %)**, 2,2 → 1,9 avions ; ailleurs −8 %. Le rail voyageurs y gagne
  **+41 k£**, l'aérien perd **−234 k£**, le fret −24 k£ (6,3 → 4,6 lignes : le
  rail voyageurs lui prend le créneau rail).
- **Les arrêts joints V207 en font plus de la moitié** : sans eux
  (`v275_expo_mm2nojoin_10x3_20261019`), aéroports concernés −15 % au lieu de
  −34 %, aérien −83 k£ ; mais le rail voyageurs ne rapporte plus que ~5 k£ par
  ligne (30 k£ au total) et le fret perd encore 2 lignes : **−83,9 k£/an, 3/7,
  IC95 [−154 k ; −11 k]**.

## Canal 3 — la caisse de 1971

- Emprunt au plafond dans les deux bras en 1971 ; −1,2 à −1,8 aéroport. Petit,
  traité par le bit 4 (aérien d'abord 2 ans).

## Avec les gardes (bits 1 et 4)

- `mm7` et `mm15` multimodal : −39,7 k et −28,7 k£/an, bruit. Le rail voyageurs
  est presque absent (0,5 à 0,8 ligne) : hors de nos villes aériennes, les
  villes sont trop petites pour qu'une ligne voyageurs passe le filtre.
- Rail seul, porte A PC (`v275_railseul_porteA_40x3_pc_20261019`, mm=7) :
  **+635,4 k£/an, 40/0**, 75,5 % d'AAA.

## Ce qui augmenterait le rail sans cannibaliser l'aérien

1. **Rail voyageurs autonome en multimodal : plafond bas.** Un voyageur de
   nos villes aériennes rapporte environ 5 fois plus en avion qu'en train
   (+41 k£ de rail contre −234 k£ d'aérien). Hors de ces villes, presque rien
   ne passe. AAA lui-même n'en tire que 131 k£ en 1979.
2. **Rail voyageurs en rabattement (feeder) vers nos aéroports** : des villes
   sans aéroport vers notre aéroport, ordres de transfert à l'aéroport. Le
   voyageur, payé à l'arrivée sur la distance totale depuis sa gare d'origine,
   remplit nos avions au lieu de leur prendre des passagers. OpexAI n'a aucun
   ordre de transfert aujourd'hui (aucun `OF_TRANSFER`). Prérequis à mesurer
   d'abord : le remplissage de nos avions (attente 10-15 voyageurs, note
   ~52 % ; s'ils partent pleins, le rabattement ne rapporte rien sans renforts).
   Cohérent avec l'usage de la route par AAA (décision du 07/10).
3. **Le fret** : il ne partage aucun voyageur avec l'aérien ; à 10 ans, c'est là
   qu'est l'écart multimodal (1 913 contre 417 k£ en 1979, trains par ligne
   3,07 contre 1,18). En multimodal, le rail voyageurs lui retire des lignes ;
   il faut lui laisser le créneau rail.
4. **Pour RVA** : le gain d'une ligne rail voyageurs doit être net de ce
   qu'elle retire à nos propres lignes (aérien : −34 % du profit de l'aéroport
   de la ville avec arrêts joints, −15 % sans), et pas seulement du partage avec
   AAA (−10 %). C'est ce terme d'auto-cannibalisation qui manquait au contrat
   économique RVA-02.
