# ROAD100-6 : flotte interurbaine à demande vérifiée sur les arrêts

Pré-enregistrement du 27/10/2026 avant code et duels ROAD100-6.

Le banc ROAD seul à un an montre, graine 42, **trois lignes AAAHogEx**
à 29, 19 et 6 bus. La plus grande rapporte 127 099 £/an observés ; deux
stations de villes distinctes sont utilisées. Dans le pilote OpexAI
`road100_solo_pax`, cinq lignes interurbaines sont construites mais toutes
ont `raw_vehs=1` au panneau `PROJECT_CHOSEN` : la seule suppression du cap
physique 2 serait sans effet. Il faut simultanément faire apparaître la
demande capable de justifier plusieurs bus et en vérifier la réalité.

Le **mécanisme unique** `road100_intercity_site_fleet=1` (défaut 0 partout)
ne s'active que si le générateur `road100_solo_pax=1` est ON en **ROAD seul**.
Pour classer le candidat, utiliser la production mensuelle totale des deux
villes avec cap pré-enregistré de 30 bus par ligne. L'estimation initiale
sert seulement à identifier des candidats potentiels. Après recherche de
sites et AVANT achat, remplacer la demande par **la somme de la production
de passagers couverte par chaque arrêt effectivement prévu**, telle que
la calculent déjà les recherches `OpexRoadPaxVoirieSites` et le repli
`OpexRoadSites` (`site.value`). Réestimer recettes, dépenses de fonctionnement,
capital, flotte, capacité et profit sur le tracé réel. Refuser une paire
si le site ne publie pas sa production, ou si le profit annuel recalculé
est non positif. Revalider finances et slots avec la flotte finale ; aucune
obligation de construire 30 véhicules ni d'épuiser l'argent. Le constructeur
réutilise les ordres partagés et ses contrôles existants. Aucun changement de
`OpexRoadPhysicalVehicleCap` pour le fret ou pour d'autres bus.

Instrumentation `ROAD100_SITE_FLEET`: demande initiale et vérifiée,
`vehiclesForVolume`, flotte plafonnée, profit, capital, motif de refus,
coût du site si disponible. Le cap 30 et le mode de calcul sont fixés avant
les mesures ; les 29 bus AAA ne prouvent pas qu'un arrêt Opex identique
tolérera ce trafic, les congestions seront évaluées via télémétrie de ligne.

Bras comparés, même arbre fige et même sonde : `road100_solo_pax=1` dans
les deux, `road100_town_bus=0`, `road100_road_batch=0`, `road100_town_voirie=0`,
`road100_pax_fleet_cap=0`, `road100_town_roi_post=0`, `estim_unifie=31` ;
référence `road100_intercity_site_fleet=0` et variante `=1` seulement.
Adversaire AAAHogEx en ROUTE seule (disable rail/tram/ship/aircraft=1).

Smoke causal graine 42 sur un an avec `--line-telemetry --script-debug`,
puis diagnostic 5×1 sur 42,100,7,999,2026 si sonde exposée et partie saine.
Lancer un 40×5 apparié descriptif uniquement avec gain de profit Opex
plausible et sans dégradation catastrophique aux premiers essais. La cible
100 % AAA s'applique à chacun des cinq horizons, en sus des portes V102 pour
adoption. Pas de changement de défaut/commit/push.
