import sys,copy
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ozon_model import load_inputs, evaluate, scenarios,public_scale

class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=load_inputs(ROOT/'data/model_inputs.json')
        cls.cases=scenarios(cls.inputs,ROOT/'data/taobao_summary.json')

    def test_original_reproduces_all_eight_results(self):
        expected=[157.97396138092518,222.17762580456474,220.25215769455826,260.3232884727913,42.41164423639566,24.260898186072154,24.260898186072154,24.260898186072154]
        for result,value in zip(evaluate(self.inputs,self.cases[1]),expected):
            self.assertAlmostEqual(result['delta_buyers'],value,places=7)

    def test_unique_population_and_probability_conservation(self):
        for case in self.cases:
            for r in evaluate(self.inputs,case):
                self.assertAlmostEqual(r['population'],case['dau'])
                self.assertGreaterEqual(r['cr1'],0)
                self.assertLessEqual(r['cr1'],1)
                self.assertLessEqual(r['target_users'],case['dau'])

    def test_zero_effect_means_zero_increment(self):
        case=next(c for c in self.cases if c['id']=='zero')
        for r in evaluate(self.inputs,case):
            self.assertAlmostEqual(r['delta_buyers'],0)
            self.assertTrue(r['guard_c'] and r['guard_f'] and r['guard_arpu'])

    def test_negative_stresses_can_fail_guardrails(self):
        results=[r for c in self.cases if c['kind']=='negative' for r in evaluate(self.inputs,c)]
        self.assertTrue(any(r['delta_buyers']<0 for r in results))
        for guard in ['guard_c','guard_f','guard_arpu']:
            self.assertTrue(any(not r[guard] for r in results))

    def test_invalid_shares_rejected(self):
        case=dict(self.cases[1],shares=[.5,.5,.5,.5])
        with self.assertRaises(ValueError): evaluate(self.inputs,case)

    def test_external_case_not_mislabeled_ozon_calibrated(self):
        external=next(c for c in self.cases if c['id']=='taobao_external')
        self.assertFalse(external['enforce_ozon'])
        calibrated=next(c for c in self.cases if c['id']=='taobao_calibrated')
        self.assertTrue(calibrated['enforce_ozon'])
        self.assertNotEqual(calibrated['global_cr'],.201)

    def test_h6_alternatives_never_summed(self):
        r=evaluate(self.inputs,self.cases[1])
        self.assertEqual([x['hypothesis'] for x in r][-3:],['H6.1','H6.2','H6.3'])
        self.assertEqual(len(r),8)

    def test_order_intensity_is_not_forced_cr(self):
        case=next(c for c in self.cases if c['id']=='taobao_calibrated')
        self.assertEqual(case['dau'],44_000_000)
        self.assertEqual(case['mau'],84_000_000)
        self.assertEqual(case['global_cr'],.15)

    def test_invalid_uplift_is_rejected(self):
        for value in [-100,float('nan'),float('inf')]:
            changed=dict(self.inputs,uplift=value)
            with self.assertRaises(ValueError):evaluate(changed,self.cases[5])

    def test_public_scale_updates_from_single_configuration(self):
        changed=copy.deepcopy(self.inputs)
        changed['public_ozon'].update(dau_march_2026=40_000_000,mau_march_2026=80_000_000,q1_days=90)
        cases=scenarios(changed,ROOT/'data/taobao_summary.json')
        base=next(c for c in cases if c['id']=='taobao_calibrated')
        self.assertEqual(base['dau'],40_000_000)
        self.assertEqual(base['mau'],80_000_000)
        scale=public_scale(changed,cases)
        self.assertEqual(scale['daily_cart_scaled'],26_000_000)
        self.assertAlmostEqual(scale['orders_per_assumed_active_user_day'],807700000/(90*40_000_000))

if __name__=='__main__': unittest.main()
