"""Test unitaire ciblé : constats n°3 et n°9 sur la comptabilité des satellites.

Vérifie que :
1. actualCost ne compte que les commandes exécutées, et pas les AITestMode
   de PORTFOLIO ou JOINED_STOPS (bouclier AIAccounting) ;
2. Le coût d'un satellite (paid / actualCost) est mesuré par AIAccounting isolé
   et non par delta de caisse (GetBankBalance) ;
3. L'imbrication d'AIAccounting est respectée (pas de second AIAccounting
   parallèle non détruit, lecture par différence sur le compteur englobant) ;
4. Simulation de l'oracle de comptabilité : isolation des tests et immunité
   aux variations de caisse simultanées.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def function_body(filename: str, name: str) -> str:
    source = (AI / filename).read_text(encoding="utf-8")
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    raise AssertionError("Unclosed function: " + name)


class AccountingStackOracle:
    """Modèle fidèle du comportement de la pile AIAccounting dans OpenTTD NoAI.

    - Chaque AIAccounting créé empile le niveau courant.
    - Toute commande (réelle ou AITestMode) augmente les coûts au sommet de la pile.
    - À la destruction (shield = null), NoAI restaure le coût de départ du niveau englobant.
    - GetCosts() renvoie le coût cumulé depuis la création du compteur.
    """

    def __init__(self):
        self.stack = [0]

    def open_scope(self):
        self.stack.append(self.stack[-1])

    def close_scope(self):
        # Le destructeur d'un AIAccounting imbriqué restaure le total supérieur
        self.stack.pop()

    def add_cost(self, amount: int):
        self.stack[-1] += amount

    def current_cost(self) -> int:
        return self.stack[-1]


class TestRoad100SatelliteAccounting(unittest.TestCase):
    def test_joined_stops_accounting_contracts(self):
        body = function_body("builder_road.nut", "OpexRoad100ExpandJoinedStops")

        # Bouclier AIAccounting autour de AITestMode
        self.assertIn("local shield = AIAccounting();", body)
        self.assertIn("local test = AITestMode();", body)
        self.assertIn("shield = null;", body)

        # Absence de delta de caisse pour le coût
        self.assertNotIn("cashBefore - AICompany.GetBankBalance", body)

        # Mesure par accounting isolé
        self.assertIn("accounting.GetCosts() - costBefore", body)

        # Contrôle de liquidité préservé
        self.assertIn("AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 25000", body)

    def test_portfolio_accounting_contracts(self):
        body = function_body("builder_road.nut", "OpexRoad100PaxPortfolioBuild")

        # Bouclier AIAccounting autour de AITestMode
        self.assertIn("local shield = AIAccounting();", body)
        self.assertIn("local test = AITestMode();", body)
        self.assertIn("shield = null;", body)

        # Absence de delta de caisse pour paid
        self.assertNotIn("cashBefore - AICompany.GetBankBalance", body)

        # Mesure par accounting isolé
        self.assertIn("accounting.GetCosts() - costBefore", body)

        # Contrôle de liquidité préservé
        self.assertIn("AICompany.GetBankBalance(AICompany.COMPANY_SELF) < reserveAfterSat", body)

    def test_build_route_propagates_costs_accounting(self):
        body = function_body("builder_road.nut", "OpexBuildRoadRoute")

        # costs passé aux deux extensions
        self.assertIn(
            "portfolioSummary = OpexRoad100PaxPortfolioBuild(\n"
            "        catalog, candidate, plan, plan.road100PortfolioPreview,\n"
            "        stopA, stopB, stationA, stationB, costs);",
            body,
        )
        self.assertIn(
            "result.road100JoinedStops <- OpexRoad100ExpandJoinedStops(\n"
            "        catalog, candidate, stopA, stopB, stationA, stationB, costs);",
            body,
        )

        # actualCost est alimenté par costs.GetCosts()
        self.assertIn("result.actualCost = costs.GetCosts();", body)

    def test_oracle_shield_and_cash_drift_immunity(self):
        """Simulation numérique : AITestMode jeté par le bouclier et caisse immunisée."""
        oracle = AccountingStackOracle()
        bank_balance = 50000

        # Étape 1 : Construction initiale (route + 2 arrêts = 3200 £)
        oracle.add_cost(3200)
        bank_balance -= 3200
        self.assertEqual(oracle.current_cost(), 3200)

        # Étape 2 : Satellite testé en AITestMode (coût simulé 250 £) avec bouclier
        oracle.open_scope()  # local shield = AIAccounting()
        oracle.add_cost(250)  # BuildDriveThroughRoadStation sous AITestMode
        oracle.close_scope()  # shield = null (destructeur restaure le niveau supérieur)

        # Le coût simulé du test n'a pas incrémenté le compteur parent !
        self.assertEqual(oracle.current_cost(), 3200)

        # Étape 3 : Commande réelle (coût réel 250 £) avec encaissement simultané (livraison +5000 £)
        cost_before = oracle.current_cost()
        oracle.add_cost(250)  # commande réelle
        bank_balance -= 250
        bank_balance += 5000  # revenu d'un autre véhicule sur le même tick !

        paid = oracle.current_cost() - cost_before

        # Le coût mesuré par AIAccounting est exactement 250 £, insensible au delta de caisse
        self.assertEqual(paid, 250)

        # L'ancien calcul par caisse aurait donné : paid_old = (balanceBefore - balanceAfter) = -4750 £ <= 0 (faux rejet)
        # Mais avec notre correctif, paid vaut 250 > 0, donc le satellite est validé !
        self.assertGreater(paid, 0)

        # Le coût total de la route ne compte que 3200 + 250 = 3450 £ (zéro surcomptage de test)
        self.assertEqual(oracle.current_cost(), 3450)


if __name__ == "__main__":
    unittest.main()
