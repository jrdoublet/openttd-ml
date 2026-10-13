import unittest
from analyse_p0_air_vehicle_cohorts_20261012 import air_vehicles,cohort,analyze


class AirCohortTests(unittest.TestCase):
    def test_survivor_and_new_not_full_year_purchase(self):
        c=cohort({1:200,2:10,3:-20},{1:70,4:5})
        self.assertEqual(1,c["continuing"]["planes"])
        self.assertEqual(200,c["continuing"]["sum_profit_gbp"])
        self.assertEqual(70,c["continuing_same_ids_prior_year"]["sum_profit_gbp"])
        self.assertEqual(130,c["continuing_profit_change_same_ids_gbp"])
        self.assertEqual(-10,c["not_seen_prior_december"]["sum_profit_gbp"])
        self.assertEqual(1,c["prior_december_not_seen_now"])

    def test_duplicate_and_invalid_data_rejected(self):
        a={"mode":"air","vehicle_financials":[{"vehicle_id":5,"profit_this_year_gbp":2.0}]}
        with self.assertRaisesRegex(ValueError,"duplicate"):
            air_vehicles({"ok":True,"unresolved_vehicles":[],"lines":[a,a]})
        with self.assertRaisesRegex(ValueError,"invalid"):
            air_vehicles({"ok":False,"unresolved_vehicles":[],"lines":[]})

    def test_full_three_year_id_survival(self):
        snaps=[]
        for year,vehicle_id in ((1971,1),(1972,1),(1973,2)):
            for arm in ("OpexAI","AAAHogEx"):
                snaps.append({"year":year,"seed":42,"arm":arm,"repeat":0,"ok":True,"unresolved_vehicles":[],
                              "lines":[{"mode":"air","vehicle_financials":[{"vehicle_id":vehicle_id,"profit_this_year_gbp":float(year)}]}]})
        report=analyze({"line_telemetry":{"snapshots":snaps}},seeds=(42,),years=(1972,1973))
        self.assertEqual(1,report["by_seed_arm_year"]["42/OpexAI/1972"]["continuing"]["planes"])
        self.assertEqual(0,report["by_seed_arm_year"]["42/OpexAI/1973"]["continuing"]["planes"])
        self.assertEqual(1,report["by_seed_arm_year"]["42/OpexAI/1973"]["not_seen_prior_december"]["planes"])


if __name__=="__main__": unittest.main()
