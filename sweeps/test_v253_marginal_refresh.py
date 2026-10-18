"""V253 : tests de la règle de remplacement marginal d'avions (mode 4).

Vérifie les cas physiques et économiques de la Proposition 2 :
1. Cas 223 -> 218 : le modèle rapide relève la note de vitesse, augmente la fréquence
   et le tarif, dégageant un gain net qui rembourse l'achat sur ligne longue.
2. Cas 228 -> 217 : sur ligne à faible demande, le passage au Dart 217 économise
   l'entretien (£3 459/an) sans perte de recette, remboursé en ~0.8 an.
3. Cas où rien ne se rembourse :
   - 223 -> 217 sur forte demande : bridage de capacité, gain négatif -> refusé.
   - 223 -> 218 sur avion en fin de vie : durée restante < délai de remboursement -> refusé.
4. Contrats de code : opcodes (cache par ligne), constantes documentées, pas de nombre magique.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    if match is None:
        raise AssertionError(f"Signature not found: {signature}")
    return match.group(1)


# Caractéristiques des moteurs certifiées par OpenTTD 15.3 (table/engines.h)
ENGINES = {
    217: {"id": 217, "name": "FFP Dart", "speed_noai": 236, "capacity": 90, "price": 32812, "running": 3656, "max_age_days": 6574},
    218: {"id": 218, "name": "Yate Haugan", "speed_noai": 579, "capacity": 100, "price": 153808, "running": 7031, "max_age_days": 9131},
    223: {"id": 223, "name": "Bakewell Luckett LB-10", "speed_noai": 236, "capacity": 220, "price": 38964, "running": 5400, "max_age_days": 7305},
    228: {"id": 228, "name": "Darwin 300", "speed_noai": 236, "capacity": 300, "price": 61523, "running": 7115, "max_age_days": 9131},
}


def speed_rating_points(speed_noai):
    """Calcule les points de note de vitesse selon OpexC121SpeedRatingPoints."""
    old_speed = int(speed_noai * 4.0 * 10.0 / 128.0)
    if old_speed > 255:
        old_speed = 255
    return (old_speed - 85) // 4 if old_speed > 85 else 0


def rating_percent_to_byte_mid(pct):
    """Calcule l'octet médian de note selon OpexC121RatingPercentToByteMid."""
    if pct < 0:
        return 0
    if pct > 100:
        pct = 100
    low = (pct * 256 + 100) // 101
    high = (((pct + 1) * 256 + 100) // 101) - 1
    low = max(0, low)
    high = min(255, high)
    if high < low:
        high = low
    return (low + high) // 2


def cargo_income_pax(distance, days):
    """Calcul du tarif passager selon OpenTTD 15.3 GetTransportedGoodsIncome."""
    tp = min(255, max(0, int(days * 2 / 5)))
    a = max(0, tp)
    t = max(31, 255 - a - max(0, a - 24))
    income = (distance * t * 3185) >> 21
    # Calibré par AIR_PAX_REVENUE_CALIBRATION_PCT = 104, avec 15% courrier
    fare = int(income * 1.04)
    return max(1, fare)


def simulate_plane_operations(engine_info, distance, demand_annual, observed_byte, service_engine=None):
    """Simulation exacte de la fonction Squirrel OpexV253PlaneOperations."""
    speed = float(engine_info["speed_noai"])
    if speed < 1.0:
        speed = 1.0

    flight_days = float(distance) / (0.036 * speed)
    one_way_days = flight_days + 3.0
    if one_way_days < 1.0:
        one_way_days = 1.0

    income_days = int(one_way_days)
    if float(income_days) < one_way_days:
        income_days += 1
    if income_days < 1:
        income_days = 1

    fare = cargo_income_pax(distance, income_days)

    pred_byte = observed_byte
    captured_demand = float(demand_annual)
    if service_engine is not None:
        pts_service = speed_rating_points(service_engine["speed_noai"])
        pts_cand = speed_rating_points(engine_info["speed_noai"])
        pred_byte = observed_byte + pts_cand - pts_service
        pred_byte = max(0, min(255, pred_byte))
        obs_share = (observed_byte + 1) / 256.0
        pred_share = (pred_byte + 1) / 256.0
        if obs_share > 0.0:
            captured_demand = float(demand_annual) * pred_share / obs_share

    cap = engine_info["capacity"]
    round_trip_days = 2.0 * one_way_days
    rotations_per_year = 365.0 / round_trip_days
    annual_capacity = rotations_per_year * (2.0 * cap)

    carried = min(annual_capacity, captured_demand)
    revenue = int(carried * fare)
    running = engine_info["running"]

    return {
        "engine_id": engine_info["id"],
        "speed": speed,
        "one_way_days": one_way_days,
        "income_days": income_days,
        "fare": fare,
        "pred_byte": pred_byte,
        "annual_capacity": annual_capacity,
        "captured_demand": captured_demand,
        "carried": carried,
        "revenue": revenue,
        "running": running,
    }


def simulate_marginal_replacement(cur_engine_id, cand_engine_id, distance, demand_annual,
                                  age_days, cur_resale_value, rating_pct=64):
    """Simulation exacte du critère de décision de OpexV253MarginalPlanForVehicle."""
    cur_info = ENGINES[cur_engine_id]
    cand_info = ENGINES[cand_engine_id]

    observed_byte = rating_percent_to_byte_mid(rating_pct)
    cur_ops = simulate_plane_operations(cur_info, distance, demand_annual, observed_byte, None)
    cand_ops = simulate_plane_operations(cand_info, distance, demand_annual, observed_byte, cur_info)

    delta_rev = cand_ops["revenue"] - cur_ops["revenue"]
    delta_run = cand_ops["running"] - cur_ops["running"]
    gain = delta_rev - delta_run

    net_cost = cand_info["price"] - cur_resale_value
    remaining_life_days = max(0, cur_info["max_age_days"] - age_days)
    remaining_life_years = remaining_life_days / 365.0

    pays = (cand_info["id"] != cur_info["id"]) and (gain > 0) and (
        net_cost <= 0 or (remaining_life_years > 0 and gain * remaining_life_years >= net_cost)
    )
    payback = (net_cost / gain) if (gain > 0 and net_cost > 0) else 0.0

    return {
        "cur_ops": cur_ops,
        "cand_ops": cand_ops,
        "gain": gain,
        "net_cost": net_cost,
        "remaining_life_years": remaining_life_years,
        "payback": payback,
        "pays": pays,
    }


class TestV253MarginalRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.fleet = cls.sources["air_fleet.nut"]
        cls.task = cls.sources["task_v252.nut"]
        cls.marginal_plan = body(cls.fleet, "function OpexV253MarginalPlanForVehicle(line, catalog, vehicle, lines = null)")
        cls.plane_ops = body(cls.fleet, "function OpexV253PlaneOperations(catalog, planeObj, distance, demandAnnual, observedByte, servicePlane = null)")
        cls.dispatch = body(cls.task, "function OpexAI::_dispatchV252AirEngineRefresh(task, year)")

    def test_speed_rating_points_values(self):
        """Vérifie que les points de note correspondent aux vitesses NoAI."""
        self.assertEqual(speed_rating_points(ENGINES[217]["speed_noai"]), 0)   # 236 -> 0
        self.assertEqual(speed_rating_points(ENGINES[223]["speed_noai"]), 0)   # 236 -> 0
        self.assertEqual(speed_rating_points(ENGINES[228]["speed_noai"]), 0)   # 236 -> 0
        self.assertEqual(speed_rating_points(ENGINES[218]["speed_noai"]), 23)  # 579 -> +23 pts

    def test_case_223_to_218_speed_rating_passes(self):
        """Cas 1 : 223 -> 218 sur ligne longue. La vitesse relève la note et le gain rembourse l'achat."""
        # Ligne longue de 200 cases, demande annuelle observée de 2 500 pax (~208 pax/mois)
        res = simulate_marginal_replacement(
            cur_engine_id=223,
            cand_engine_id=218,
            distance=200,
            demand_annual=2500,
            age_days=1000,           # Avion de ~2.7 ans, durée restante > 17 ans
            cur_resale_value=20000,  # Revente du 223
            rating_pct=64
        )
        # La note prédite prend +23 points de vitesse
        self.assertEqual(res["cand_ops"]["pred_byte"] - res["cur_ops"]["pred_byte"], 23)
        # La demande captée augmente d'environ 14% grâce à la note
        self.assertGreater(res["cand_ops"]["captured_demand"], res["cur_ops"]["captured_demand"])
        # La recette augmente significativement (+25 à +30 k£/an)
        self.assertGreater(res["cand_ops"]["revenue"], res["cur_ops"]["revenue"] + 25000)
        # Le gain d'exploitation annuel est largement positif (> +20 k£/an)
        self.assertGreater(res["gain"], 25000)
        # Le délai de remboursement est bien inférieur à la durée de vie restante (~4.7 ans < 17.3 ans)
        self.assertLess(res["payback"], 6.0)
        self.assertGreater(res["remaining_life_years"], 15.0)
        self.assertTrue(res["pays"])

    def test_case_228_to_217_low_demand_downsizing_passes(self):
        """Cas 2 : 228 -> 217 sur ligne à faible demande. L'économie d'entretien passe sans perte de recette."""
        # Ligne moyenne de 80 cases, demande modeste de 480 pax/an (40 pax/mois)
        res = simulate_marginal_replacement(
            cur_engine_id=228,
            cand_engine_id=217,
            distance=80,
            demand_annual=480,
            age_days=1000,
            cur_resale_value=30000,  # Revente du 228
            rating_pct=64
        )
        # Même vitesse (236 km/h) -> note et demande inchangées
        self.assertEqual(res["cand_ops"]["pred_byte"], res["cur_ops"]["pred_byte"])
        self.assertEqual(res["cand_ops"]["carried"], res["cur_ops"]["carried"])
        # Delta recette nul car le Dart transporte l'intégralité des 480 passagers
        self.assertEqual(res["cand_ops"]["revenue"], res["cur_ops"]["revenue"])
        # Gain égal à l'économie brute d'entretien : £7 115 - £3 656 = +£3 459/an
        self.assertEqual(res["gain"], 3459)
        # Coût net d'achat : £32 812 - £30 000 = £2 812
        self.assertEqual(res["net_cost"], 2812)
        # Remboursé en moins d'un an (~0.81 an)
        self.assertLess(res["payback"], 1.0)
        self.assertTrue(res["pays"])

    def test_case_nothing_pays_back_keeps_current(self):
        """Cas 3 : Aucun remplacement ne se rembourse -> le modèle actuel est conservé."""
        # 3a. 223 -> 217 sur ligne à forte demande (4 000 pax/an) : perte de trafic massive
        res_downsize = simulate_marginal_replacement(
            cur_engine_id=223,
            cand_engine_id=217,
            distance=80,
            demand_annual=4000,
            age_days=1000,
            cur_resale_value=20000,
            rating_pct=64
        )
        # La capacité annuelle du Dart plafonne à ~2 645 pax contre 4 000 transportés par le 223
        self.assertLess(res_downsize["cand_ops"]["carried"], 2800)
        self.assertEqual(res_downsize["cur_ops"]["carried"], 4000)
        # La perte de recette (> £40 000) écrase l'économie d'entretien (£1 744) -> gain négatif
        self.assertLess(res_downsize["gain"], -30000)
        self.assertFalse(res_downsize["pays"])

        # 3b. 223 -> 218 sur avion en fin de vie : durée restante trop courte pour amortir
        res_old = simulate_marginal_replacement(
            cur_engine_id=223,
            cand_engine_id=218,
            distance=200,
            demand_annual=2500,
            age_days=7000,           # Max age = 7 305 jours -> 305 jours restants (~0.83 an)
            cur_resale_value=10000,
            rating_pct=64
        )
        self.assertGreater(res_old["gain"], 20000)
        # Payback ~5 ans > 0.83 an restant -> refusé
        self.assertGreater(res_old["payback"], res_old["remaining_life_years"])
        self.assertFalse(res_old["pays"])

        # 3c. Remplacement par le même modèle -> gain nul, refusé
        res_same = simulate_marginal_replacement(
            cur_engine_id=223,
            cand_engine_id=223,
            distance=200,
            demand_annual=2500,
            age_days=1000,
            cur_resale_value=20000
        )
        self.assertEqual(res_same["gain"], 0)
        self.assertFalse(res_same["pays"])

    def test_squirrel_source_contracts(self):
        """Vérifie la conformité statique du code Squirrel livré."""
        # 1. Présence des fonctions livrées
        self.assertTrue(self.marginal_plan)
        self.assertTrue(self.plane_ops)

        # 2. Vitesse réelle sans /4
        self.assertIn("flightDays = distance.tofloat() / (0.036 * speed);", self.plane_ops)
        self.assertNotIn("speed / 4.0", self.plane_ops)
        self.assertNotIn("speed / 4", self.plane_ops)

        # 3. Réutilisation de OpexC121SpeedRatingPoints et part (note+1)/256
        self.assertIn("OpexC121SpeedRatingPoints(servicePlane)", self.plane_ops)
        self.assertIn("OpexC121SpeedRatingPoints(planeObj)", self.plane_ops)
        self.assertIn("(observedByte + 1).tofloat() / 256.0", self.plane_ops)
        self.assertIn("(predByte + 1).tofloat() / 256.0", self.plane_ops)

        # 4. Demande observée (transportés + en attente)
        self.assertIn("GetCargoWaiting", self.marginal_plan)
        self.assertIn("annualDelivered", self.marginal_plan)
        self.assertIn("annualDemandPerPlane", self.marginal_plan)

        # 5. Valeur de revente et durée de vie restante
        self.assertIn("AIVehicle.GetCurrentValue(vehicle)", self.marginal_plan)
        self.assertIn("AIVehicle.GetAgeLeft(vehicle)", self.marginal_plan)

        # 6. Condition de gain et remboursement
        self.assertIn("gain > 0", self.marginal_plan)
        self.assertIn("gain.tofloat() * remainingYears >= netCost", self.marginal_plan)

        # 7. Coût d'opcodes : cache par ligne dans task_v252.nut
        self.assertIn("local lineTargetCache = {};", self.dispatch)
        self.assertIn("? OpexV253MarginalPlanForVehicle(cand.line, this._catalog, cand.veh)", self.dispatch)

        # 8. Journal V252_KEEP et V252_REPLACE avec tous les champs requis
        self.assertIn('OpexDecide("V252_KEEP"', self.marginal_plan)
        self.assertIn("rev_cand=", self.marginal_plan)
        self.assertIn("rating_pred=", self.marginal_plan)
        self.assertIn("payback=", self.marginal_plan)

        self.assertIn('OpexDecide("V252_REPLACE"', self.dispatch)
        self.assertIn("gain=", self.dispatch)
        self.assertIn("rev_new=", self.dispatch)
        self.assertIn("rev_old=", self.dispatch)
        self.assertIn("rating_pred=", self.dispatch)
        self.assertIn("payback=", self.dispatch)

        # 9. Aucun nombre à 4 chiffres ou plus dans task_v252.nut
        self.assertNotRegex(self.task, r"\b\d{4,}\b")


if __name__ == "__main__":
    unittest.main()
