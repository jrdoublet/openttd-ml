# Ordre de clôture des tâches encore ouvertes — 26 octobre 2026

Classement **par effort restant**, puis dépendances, preuve existante,
besoin de moteur/porte et risque pour les contrats de l'IA. Il ne
requalifie aucun résultat historique. Source autoritaire pour les cases :
[taches.md](taches.md). Un chantier bloqué est annoté puis sauté ;
aucune décision de défaut ou adoption n'est implicite. P1 est repris
sur le VPS, P6 abandonné et P3 est poursuivi uniquement via AIR-LOAD-1 :
ces trois parcours sont exclus des lots à lancer.

Au début du reclassement, **39 cases ouvertes** (dont quatre sous-cases
indentées). Les lots successifs du 26/10 ont déjà clos V304, V309,
V224, V290, V241, FRONT-PAX-1, V303, V308, PCAL-03 et AIR-FLOTTE-1 et RAIL-CAPEX-1 et AIR-MONOPOLY-1 et V250, soit **treize cases**.
Le reste comporte **26 cases** : 23 dossiers actionnables, trois
avec dépendance bloquante. Les estimations restent des **ordres de
grandeur relatifs**, pas une promesse de calendrier. Pour tout code
comportemental, OFF par défaut, tests/smoke/exposition et portes
pré-enregistrées restent obligatoires.

## C2 — les mesures et correctifs ciblés, risque limité à moyen

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 1 | AIR-ROI-RENOUVELLEMENT-1 | Moyen ; V252 et rendement après remplacement | Hors ligne puis expérience | Moyen |
| 2 | AIR-ROI-LIGNE-1 | Moyen ; site, flotte, capital et revenu mûr | Hors ligne puis expérience | Moyen |
| 3 | OPCODE-AILIST-2 | Moyen ; L1/L2 retirés, inventaire d'éléments et coût de création | Mesure 1024² années 8–10 | Moyen |
| 4 | V306 | Moyen ; modèle revenu cellule éprouvé hors graines, pas ROI causal | Ablation au choix / A-B ultérieure | Moyen à élevé |
| 5 | DIST-BORNES-1 | Moyen à élevé ; contrats ROUTE/PASS/FRET, V276 et V269 | Relecture, smoke, porte si modification | Élevé |
| 6 | V249a | Moyen à élevé ; demande supplémentaire captable par gare/cargo | Shadow puis expérience | Moyen à élevé |

## C3 — prototypes bornés nécessitant intégration et qualification

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 7 | PCAL-01 | Moyen ; V289, pré-calcul utile et consommation d'un plan | 3×3 de preuve, puis porte | Moyen |
| 8 | V294k | Moyen ; tunnels sous plateau/eau, géométrie et budgets A* | Smoke puis A rail | Élevé |
| 9 | PO-01 | Moyen ; PO-01c, reconstructions partielles et invalidation | Traces de publication, puis A/B | Élevé |
| 10 | Mode fair_play explicite | Moyen ; décisions V261 par niveau, compatibilité avec les profils | Contrats niveaux et smoke, banc si comportement | Moyen à élevé |

## C4 — chantiers lourds dépendants de constructions ou de séquences

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 11 | IDLE-1 | Élevé ; fusion V308/V309, réserve, carte invalidable et consommateur concret | 3×10 puis A/B si exposé | Élevé |
| 12 | V294 | Élevé ; A*, paramètres physiques et itérations | Porte RAIL, puis B | Élevé |
| 13 | PO-02 | Élevé ; PO-01, publication/expiration de viviers | Exposition, A/B | Élevé |
| 14 | Croissance des lignes RAIL (19/10 nuit) | Élevé ; fins de projets, garde de financement, V269/V284 | Portes rail dédiées | Élevé |
| 15 | V240 | Élevé ; croissance urbaine retirée, devis géométrique nouveau | Démontrer activité puis A/B | Élevé |
| 16 | V242 | Élevé ; feeders et transport multimodal | Chaînes physiques, A/B | Élevé |
| 17 | V233 | Très élevé ; marchandises transformées, sources/débouchés et rivalité | Exposition causale, A/B | Élevé |
| 18 | V226 | Très élevé ; réseau ferroviaire en araignée | Architecture, Save/Load, A/B | Très élevé |
| 19 | V249b | Élevé ; marges réelles V249a et achats marginaux | A/B finance | Très élevé |
| 20 | V249c | Élevé ; surplus durable après V249b et choix intermodaux | A/B finance | Très élevé |
| 21 | V253 | Très élevé ; choix global d'avions, V252 et cycles de renouvellement | A/B AIR | Très élevé |
| 22 | V251 | Très élevé ; construction d'industries et contrat économique de l'API | Exposition puis A/B | Très élevé |
| 23 | V291 | Très élevé ; terrassement/canaux uniquement au niveau permissif | Garde de sécurité, exposition, A/B | Très élevé |

## Bloquées : annoter et passer sans nouvelle expérience

| Case | Blocage concret | Reprise possible |
|---|---|---|
| V281 | V269 déjà intégré, V270 absent du master et voie V284 adoptée | Décision utilisateur : remplacer V270 ou définir une nouvelle variante |
| V261 | Audit/forum et tests déjà livrés, liste publique hébergée sur un tiers | Publication par le gestionnaire de tipsyfox.net/ottd/ |
| Désactiver les sondes non essentielles en partie normale | Le réglage `probes=0` existe ; imposer un **nouveau défaut** contredirait l'interdiction de modifier les défauts | Décision explicite sur les réglages de publication et la compatibilité des harnais |

Les dossiers d'un niveau ne sont pas interchangeables : une mesure
hors moteur n'autorise jamais à écrire une politique ON. Une tâche
sans données suffisantes reçoit un verdict documenté (« non exposée »,
« bloquée » ou « non qualifiée ») puis cède la priorité au dossier
suivant. Ne pas relancer les campagnes historiques exclues ni créer
de scripts de diagnostic pour simplement remplir une case.
