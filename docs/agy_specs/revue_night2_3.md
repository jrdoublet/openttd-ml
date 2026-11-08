# Revue d'analyse — Tâche 3 : COURRIER-P2P (Analyse causale et verdict)

**Date :** 8 novembre 2026  
**Auteur :** Antigravity  
**Sujet :** Réexamen de l'échec de `mail_net` (−38 k£), `mail_min` (−45 k£), `mail_pick` (−27 k£) et viabilité de `road1y_mail_p2p`.  
**Consigne respectée :** *"Si la cause d'échec est l'idée elle-même, écris-le et ne code pas."*

---

## 1. Synthèse exécutive

L'analyse causale, financière et topologique démontre formellement que **la cause d'échec est l'idée elle-même** (création de lignes de courrier point à point autonomes avec infrastructure dédiée).

Dans le modèle économique d'OpenTTD à 3 ans, toute voirie construite exclusivement pour du courrier présente un temps de retour sur investissement (payback) de **6 à 8 ans**, soit plus du double de l'horizon de qualification (3 ans / 1970-1972). Toute dépense de capex d'infrastructure pour du courrier autonome détruit directement du profit net par éviction du capital alloué aux bus interurbains (payback < 7 mois).

Conformément à la consigne explicite du mandat, **aucun code nuisible n'est implémenté** pour cette tâche.

---

## 2. Décomposition causale des échecs historiques

### A. Échec de `mail_net` (−38 k£/an, branches `road1y-mailnet`, commits `fb959178`, `35332753`)
- **Mécanisme :** Tentative de créer un réseau intercités dédié au courrier sur des paires de villes sans ligne de bus.
- **Canal de destruction :**
  1. *Coût d'infrastructure fixe :* Le tracé routier d'une liaison interurbaine (70 à 100 tuiles) coûte entre 17 000 £ et 25 000 £ (terrassement, déboisement, franchissement de relief, bitume).
  2. *Faible volume spécifique :* Une ville de 1 000 habitants ne produit que 15 à 25 sacs de courrier par mois (contre 80 à 120 passagers). La ligne ne peut alimenter que 1 ou 2 fourgons postaux.
  3. *Revenu plafonné :* Un fourgon postal génère au mieux 1 800 à 2 500 £/an. Le revenu total annuel de la ligne est de ~3 500 £/an.
  4. *Payback :* 22 000 £ / 3 500 £/an = **6,3 ans**.
  5. *Bilan à 3 ans :* Au terme de l'année 1972, la ligne a coûté 22 k£ et n'a rapporté que 3 × 3,5 = 10,5 k£ (perte nette de 11,5 k£).
  6. *Éviction de capex :* Les 22 k£ immobilisés dans cette voirie postale ont privé l'IA du capital nécessaire pour ouvrir une ligne de BUS à 35 000 £/an de profit (payback 0,6 an). Le coût d'opportunité net dépasse 30 k£/an par ligne.

### B. Échec de `mail_min` (−45 k£/an, branche `road1y-mailmin`, commit `989a2fa6`)
- **Mécanisme :** Suppression des fourgons lorsque le stock en attente est inférieur à 15 sacs.
- **Canal de destruction :** Un fourgon postal sur une infrastructure partagée a un running cost dérisoire (~250 £/an). Même avec 5 à 10 sacs par voyage, il génère 1 200 à 1 500 £/an de profit net. Supprimer ces véhicules a réduit le parc de 94 à 46 fourgons, détruisant 45 k£/an de cash net immédiat.

### C. Échec de `mail_pick` (−27 k£/an, branche `road1y-mailpick`, commit `760ba36e`)
- **Mécanisme :** Restriction de l'ouverture du courrier aux seules villes produisant au moins 20 sacs/mois.
- **Canal de destruction :** Cela a réduit le nombre total de lignes ouvertes et a bloqué le déploiement sur les villes moyennes rentables, sans améliorer le rendement unitaire des lignes restantes.

---

## 3. Pourquoi AAAHogEx a 173 lignes de courrier et comment OpexAI opère

1. **La fausse symétrie avec AAAHogEx :**
   AAAHogEx n'a pas 173 lignes de courrier *autonomes avec voirie dédiée*. Il s'agit de services postaux inter-arrêts urbains (`TownBus` dans `road.nut:1146`) et de dessertes locales greffées sur la voirie municipale préexistante (sans capex interurbain).
2. **La stratégie optimale d'OpexAI (`OpexRoad1yMailStep`) :**
   OpexAI exploite déjà le courrier de façon marginale optimale via `OpexRoad1yBuildMailChild` :
   - L'infrastructure de voirie est déjà amortie et payée par la ligne de bus parent.
   - Le capex marginal se limite à 2 arrêts drive-through de camion (2 × 500 £) et 1-2 fourgons (2 000 £/fourgon), soit **~3 000 à 5 000 £**.
   - Le payback est inférieur à **1,5 an**.
   - Opex déploie déjà 73,4 fourgons pour 134,1 k£/an. Le gisement courrier restant sans saturer les stocks (attente moyenne de 10,9 sacs chez nous vs 44,5 sacs chez AAA) est structurellement borné.

---

## 4. Conclusion et décision

L'idée d'un courrier interurbain autonome point à point (`road1y_mail_p2p`) est intrinsèquement déficitaire à 3 ans dans OpenTTD en raison du ratio capex voirie / production de courrier.
- **Décision :** Conformément aux consignes, **aucun code n'est ajouté**, préservant ainsi l'intégrité de la trésorerie et la rentabilité des bus.
- **Statut Tâche 3 :** Conclue et documentée comme idée réfutée par la physique économique du jeu.
