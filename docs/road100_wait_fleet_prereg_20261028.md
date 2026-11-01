# ROAD100-10 — renfort de flotte sur attente réellement observée

Préréservation du 28/10/2026, avant les campagnes de ROAD100-10.

## Problème mesuré

ROAD100-7/8/9 découvrent et bâtissent des dessertes passagers mais le
modèle économique initial des arrêts prédit seulement 21–34 voyageurs
par mois. L'analyse annuelle des sauvegardes de ROAD100-8 montre
néanmoins qu'une ligne OpexAI à deux bus peut enregistrer plusieurs
milliers de livres de bénéfice annuel réel : la demande initiale
n'est pas un plafond fiable de l'activité future. AAAHogEx amplifie
ses flottes à partir de l'attente réelle, tandis que
`OpexAI::_refleetRoadLines` plafonne toujours à deux véhicules pour
une station à un quai, indépendamment du temps de trajet.

## Opt-in et mécanique isolée

- `road100_wait_fleet=1` par défaut **0** sur quatre difficultés,
  uniquement en ROAD seul avec `road100_site_first=1`. Les autres
  variantes ROAD100-8/9 restent à zéro dans le premier duel.
- Ne modifier **que le renouvellement de lignes passagers existantes
  et rentables**, jamais leur création initiale ni les lignes fret.
  Mesurer (W_A+W_B), la capacité réelle d'un véhicule, les notes des
  stations, le nombre de véhicules qui circulent et le bénéfice de
  l'année précédente.
- Candidat à un renfort seulement après un exercice révolu,
  bénéfice réel >2 000 £/an, au moins un bus qui circule, demande
  en attente (W_A+W_B >= capacité × (bus+1)).
  Le supplément reste borné à **deux véhicules par mois** et au
  nombre réellement finançable, avec ≥50 k£ en caisse après achat.
- Le nouveau plafond d'essai dépend du temps aller-retour (trop de bus
  sur une route courte produiraient un embouteillage) : ne dépasser
  jamais 16 bus/ligne, ni un bus tous les trois jours de rotation.
  Ce n'est pas une permission universelle de densifier les quais.
- Tracer `ROAD100_WAIT_FLEET` : ligne, âge, bénéfice réel, attente,
  note station, bus circulants, véhicules avant/cible/après, coût
  unitaire, cash, refus et nombre acheté. Les recettes annuelles
  réellement enregistrées sur des sauvegardes ont priorité sur
  le nombre de bus construit.

## Qualification

Smoke 1×2/1×5 graine42, puis 5×5 apparié à la même source figée
OFF/ON, mêmes lignes initiales et même AAAHogEx ROAD-only ; refuser
toute variante qui achète des bus sans charge réelle ou érode la
valeur >5 %. Si résultats plausibles, porte 40×5 appariée avec
un gain utile ≥4 %, p<0,05 et IC95 positif, tout en testant les cinq
horizons et les vrais profits Opex/AAA. Ce pilote ne valide
pas la compatibilité avec ROAD100-9 sans essai combiné distinct.
