import unittest
from analyse_p0_air_fleet_incumbents_20261012 import pair_services, air_services


class IncumbentAirTests(unittest.TestCase):
    def test_expanded_vs_unchanged_compare_same_planes_only(self):
        prior={(1,2):{1:100,2:60},(3,4):{3:80},(5,6):{5:30}}
        now={(1,2):{1:70,2:50,9:0},(3,4):{3:90},(5,6):{5:50,7:20}}
        result=pair_services(prior,now)
        self.assertEqual(2,result["aggregates"]["expanded"]["matched_services"])
        self.assertEqual(3,result["aggregates"]["expanded"]["surviving_aircraft"])
        self.assertEqual(-6.67,result["aggregates"]["expanded"]["mean_change_per_survivor_gbp"])
        self.assertEqual(10,result["aggregates"]["unchanged"]["mean_change_per_survivor_gbp"])

    def test_missing_prior_and_zero_survivor_excluded(self):
        prior={(1,2):{1:10},(3,4):{3:20}}
        now={(1,2):{4:10},(5,6):{5:10}}
        result=pair_services(prior,now)
        self.assertEqual(0,len(result["paired_services"]))
        self.assertEqual(1,result["unpaired_prior"])
        self.assertEqual(1,result["unpaired_current"])

    def test_station_collision_rejected(self):
        a={"station_ids":[2,1],"mode":"air","vehicle_financials":[]}
        b={"station_ids":[1,2],"mode":"air","vehicle_financials":[]}
        with self.assertRaisesRegex(ValueError,"duplicate"):
            air_services({"ok":True,"unresolved_vehicles":[],"lines":[a,b]})


if __name__=="__main__":unittest.main()
