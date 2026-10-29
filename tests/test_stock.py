import sys, unittest, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from cart_stock import distributions, bounds, crossover
from ozon_model import load_inputs, scenarios, evaluate

class StockTests(unittest.TestCase):
    def test_histograms_obey_all_case_moments(self):
        for d in distributions():
            xs=[x['sku'] for x in d['histogram'] for _ in range(x['users'])]
            self.assertEqual(len(xs),10000)
            self.assertEqual(sum(xs)/len(xs),60)
            self.assertEqual((xs[4999]+xs[5000])/2,24)
            self.assertEqual(max(xs),300)
            self.assertAlmostEqual(sum(x>=40 for x in xs)/len(xs),d['large_share'])

    def test_bound_and_taobao_independence(self):
        self.assertAlmostEqual(bounds()['lower_necessary'],19/174)
        self.assertEqual(bounds()['upper_necessary'],.5)
        i=load_inputs(ROOT/'data/model_inputs.json')
        self.assertEqual(scenarios(i,ROOT/'does-not-exist.json'),scenarios(i,None))
        self.assertFalse(any('taobao' in c['id'] for c in scenarios(i,None)))

    def test_h1_reach_counts_large_cart_once(self):
        i=load_inputs(ROOT/'data/model_inputs.json')
        for c in scenarios(i,None):
            if c['kind']=='stock':
                h=evaluate(i,c)[0]
                self.assertAlmostEqual(h['target_users']/c['dau'],.65*c['large_share']*.4)

    def test_crossover_depends_on_conditional_need(self):
        i=load_inputs(ROOT/'data/model_inputs.json')
        a=crossover(i,.4);b=crossover(i,1.)
        self.assertGreater(a['threshold'],.5)
        self.assertFalse(a['within_case_bounds'])
        self.assertTrue(b['within_case_bounds'])

    def test_crossover_uses_configured_cr_gaps(self):
        from cart_stock import joint
        i=load_inputs(ROOT/'data/model_inputs.json')
        i['case_cr_gaps']=[0,-.08,-.16,-.08]
        root=crossover(i,.8)['threshold']
        self.assertIsNotNone(root)
        c=next(c for c in scenarios(i) if c['id']=='ozon_stock_base')
        for p,sign in [(root-1e-5,-1),(root+1e-5,1)]:
            c.update(shares=joint(p),large_share=p,h1_need=.8)
            c['whale_cr']=c['global_cr']-sum(s*g for s,g in zip(c['shares'],i['case_cr_gaps']))
            rows=evaluate(i,c)
            self.assertGreater(sign*(rows[0]['delta_pp']-rows[3]['delta_pp']),0)

    def test_zero_uplift_does_not_invent_a_crossover(self):
        i=load_inputs(ROOT/'data/model_inputs.json');i['uplift']=0
        self.assertIsNone(crossover(i)['threshold'])
