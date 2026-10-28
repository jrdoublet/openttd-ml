# ROAD100-13 — déviation constructible bornée entre arrêts voyageurs

Préréservation du 28 octobre 2026. Réglage `road100_detour=1`, **défaut 0**
aux quatre difficultés, valide uniquement sous `road100_site_first=1`
(donc jeu ROUTE seul). Ni ROAD100-8/9/10/11/12 ni les défauts historiques
ne sont activés automatiquement.

## Cause et hypothèse

Dans le smoke ROAD100-12 graine42, 16/16 préplans ne trouvent aucun
trajet (`VOIRIE_PLAN fail=NO_PATH nBfs=0 nL=0`) avant décision économique.
Le planiteur essaie la voirie préexistante et seulement deux traces en L.
Une route à un ou deux détours constructibles peut exister sans être
un L direct ni une connexion préexistante. C'est un obstacle **physique**,
indépendant de la caisse et de C75, qui justifie un essai de recherche
nouvelle, mais certainement pas un A* illimité.

## Intervention délimitée

**Phase 1 choisie avant banc :** après les méthodes BFS routier existant
et les deux L historiques, essayer pour **deux couples d'arrêts maximum
par candidat** les variantes 2–9 de `OpexRoadTraceMulti` déjà présentes
dans OpexAI mais non explorées en site-first. Au plus huit formes par
couple, 48 arêtes par forme et 250 k opcodes supplémentaires mesurés
par candidat (borne souple entre appels NoAI). L'axe d'entrée ET de
sortie des arrêts traversants et la platitude des deux virages sont
obligatoires ; chaque arête non déjà connectée doit passer
`AIRoad.BuildRoad` en AITestMode. Cette voie teste deux coudes
géométriques, **pas une recherche A*** ni une BFS de nouvelles routes.
Une recherche dirigée plus générale avec 96 nœuds d'expansion pourra
faire l'objet d'une phase distincte **seulement** si les formes existantes
échouent, sans modifier rétroactivement le périmètre de la phase 1.
Le plan reste soumis à `OpexRoadFindDepot`, à la revalidation complète
au chantier et aux finances historiques. En cas d'échec, refus inchangé,
aucune suppression de garde. Sondes : couples examinés, variantes testées,
opcodes, trajet obtenu et motif d'échec.

## Validation préenregistrée

Projection OFF exacte, tests ciblés, smoke 1×3 graine42 en duel carte
partagée et vérification de **plans réellement admis et construits**.
Diagnostic 5×5 apparié 42/100/7/999/2026 uniquement si le code compile
et expose la recherche, en gardant 1–5 ans, bénéfice annuel, caisse,
valeur, bus, sites et opcodes. Porte A 40×5 uniquement après signal
économique favorable et garde de valeur ≥−5 %, Wilcoxon p<0,05,
delta moyen ≥4 %, IC95 bootstrap bas >0. Ne pas extrapoler une
admission à une construction ni un devis à un profit réel.
