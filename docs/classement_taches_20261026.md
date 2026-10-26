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
V224, V290, V241, FRONT-PAX-1, V303, V308, PCAL-03, AIR-FLOTTE-1, RAIL-CAPEX-1, AIR-MONOPOLY-1, V250, PO-01 (suite PO-01c non qualifiée) et programme historique de croissance RAIL (sous-lots clos), soit **quinze cases**.
Le reste comporte **24 cases** : 22 dossiers actionnables, deux
avec dépendance bloquante. Les estimations restent des **ordres de
grandeur relatifs**, pas une promesse de calendrier. Pour tout code
comportemental, OFF par défaut, tests/smoke/exposition et portes
pré-enregistrées restent obligatoires.

## C2 — études ciblées et sondes, effort modéré

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 1 | V306 | Moyen ; ablation hors graines faite, modèle revenu ≠ classement financier | Validation au choix, puis A/B si politique | Moyen à élevé |
| 2 | OPCODE-AILIST-2 | Moyen ; L1/L2 retirés, coût de création et cache | Mesure 1024² années 8–10 | Moyen |
| 3 | Désactiver les sondes non essentielles | Moyen ; `probes=0` déjà par défaut, C75_YEAR_LEDGER résiduel | Mesure opcodes puis neutralité B si optimisé | Moyen à élevé |
| 4 | AIR-ROI-LIGNE-1 | Moyen à élevé ; coûts réels, flotte modifiée et témoin | Hors ligne puis expérience même-save | Moyen à élevé |
| 5 | AIR-ROI-RENOUVELLEMENT-1 | Moyen à élevé ; V252, revente et contrefactuel | Hors ligne puis expérience même-save | Moyen à élevé |
| 6 | DIST-BORNES-1 | Moyen à élevé ; double écran V276/V269 sur 201–250 | Exposition 1024², puis porte si choix | Élevé |
| 7 | V249a | Moyen à élevé ; demande supplémentaire captable par gare/cargo | Shadow puis expérience | Moyen à élevé |

## C3 — prototypes et validations dépendantes

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 8 | PCAL-01 | Moyen ; V289, pré-calcul utile et consommation d'un plan | 3×3 de preuve, puis porte | Moyen |
| 9 | Mode fair_play explicite | Moyen à élevé ; audit existant, choix des comportements | Contrats niveaux et smoke, banc si comportement | Moyen à élevé |

## C4 — chantiers lourds dépendants de constructions ou de séquences

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 10 | V294 | Élevé ; A*, paramètres physiques et itérations | Porte RAIL, puis B | Élevé |
| 11 | IDLE-1 | Élevé ; fusion V308/V309, réserve, carte invalidable et consommateur concret | 3×10 puis A/B si exposé | Élevé |
| 12 | PO-02 | Élevé ; PO-01c livré, publication/expiration de viviers | Exposition, A/B | Élevé |
| 13 | V240 | Élevé ; croissance urbaine retirée, devis géométrique nouveau | Démontrer activité puis A/B | Élevé |
| 14 | V242 | Élevé ; feeders et transport multimodal | Chaînes physiques, A/B | Élevé |
| 15 | V249b | Élevé ; marges réelles V249a et achats marginaux | A/B finance | Très élevé |
| 16 | V249c | Élevé ; surplus durable après V249b et choix intermodaux | A/B finance | Très élevé |
| 17 | V294k | Très élevé ; voisin A*, terrassement, tunnel/eau après V294a-e | Smoke puis A rail | Très élevé |
| 18 | V253 | Très élevé ; choix global d'avions, V252 et cycles de renouvellement | A/B AIR | Très élevé |
| 19 | V233 | Très élevé ; marchandises transformées, sources/débouchés et rivalité | Exposition causale, A/B | Très élevé |
| 20 | V226 | Très élevé ; réseau ferroviaire en araignée | Architecture, Save/Load, A/B | Très élevé |
| 21 | V251 | Très élevé ; construction d'industries et contrat économique de l'API | Exposition puis A/B | Très élevé |
| 22 | V291 | Très élevé ; terrassement/canaux uniquement au niveau permissif | Garde de sécurité, exposition, A/B | Très élevé |

## Bloquées : annoter et passer sans nouvelle expérience

| Case | Blocage concret | Reprise possible |
|---|---|---|
| V281 | V269 déjà intégré, V270 absent du master et voie V284 adoptée | Décision utilisateur : remplacer V270 ou définir une nouvelle variante |
| V261 | Audit/forum et tests déjà livrés, liste publique hébergée sur un tiers | Publication par le gestionnaire de tipsyfox.net/ottd/ |

Les dossiers d'un niveau ne sont pas interchangeables : une mesure
hors moteur n'autorise jamais à écrire une politique ON. Une tâche
sans données suffisantes reçoit un verdict documenté (« non exposée »,
« bloquée » ou « non qualifiée ») puis cède la priorité au dossier
suivant. Ne pas relancer les campagnes historiques exclues ni créer
de scripts de diagnostic pour simplement remplir une case.
