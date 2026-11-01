# ROAD100-3 — exploitation du portefeuille routier dans la meme passe

Pre-enregistrement du 27/10/2026, avant toute mesure de ROAD100-3.

## Fait motivant

Reference ROAD seule `road100_baseline_40x5_20261027` : 6 % du profit
AAAHogEx à un an, 1,4 % à cinq ans, 0/40 victoires sur chaque horizon,
40/40 parties saines. Des projets fret existent et des constructions ROAD
sont reussies : graine 42, `VIVIER_GEN` 26 candidats le 03/01/1970, mais
seulement quatre ouvertures en 1970, des pauses `stop=k_pass` dans les logs.
Dans `task_projects.nut`, dès qu'une ligne a ete bâtie, le seuil dynamique
`K_pass=F×tau_pass` peut interrompre la passe si le capital du projet suivant
le dépasse. Au depart `F=0` et le `K_pass` vaut 0, de sorte que les ouvertures
utiles sont ajournées malgre une caisse > coût du projet suivant.

Les expériences ROAD100-1 (bus interurbains) et ROAD100-2 (bus de quartier)
n'ont pas montre de gain moyen sur cinq graines à un an. Ce lot restaure
uniquement la capacite d'executer les projets rentables DEJA selectionnes.

## Intervention unique

`road100_road_batch=0` quatre difficultes. `1` autorise jusqu'à QUATRE
constructions dans une passe lorsque ROAD est le seul mode actif, uniquement
pour une **nouvelle ligne route**. Les projets restent ordonnes, rentables
apres revalidation, uniques et soumis aux filtres ordinaires. Pour chaque
construction supplementaire, verifier AVANT l'opération : profit annuel
prevu positif, profit/capital >= 25 % annuel, fonds disponibles >= coût
finance du projet + 50 000 £. Le chantier recalcule la géométrie et les
coûts, applique ses propres gardes financières. Les modifications de cadence
ne touchent pas aux modes AIR, RAIL ou WATER.

Instrumentation `ROAD100_BATCH year=... rank=... built=... k_pass=...`
sur chaque bypass et refus quantifiable. Le contrôle de budget reste basé sur
`OpexAvailableCapital`; ce n'est pas une garantie de non-cannibalisation
économique, qui devra etre mesuree au banc.

## Contrôle économique

Smoke graine 42 1 an, puis diagnostic 5×1 sur 42,100,7,999,2026. Si
accroissement Opex visible et santé totale, prolonger par 40 graines × 5 ans
avec reference et variante sur le meme bundle et adversaire ROAD seul. Cible
100 % AAA a 1 an puis 2,3,4,5 ans sans degradation annuelle. Les valeurs
`road100_solo_pax` et `road100_town_bus` restent à zéro pour isoler la
cadence. Mesurer profits, flux de caisse, lignes/vehicules/gares, opcodes et
refus; présence de projets et nombre de bypass ne suffisent pas.

Pour adoption au défaut, les portes comportement V102 restent nécessaires,
avec la porte B spécifique autorisée séparément. Aucun commit ou push.
