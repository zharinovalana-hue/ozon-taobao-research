import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ozon_model import load_inputs,evaluate,scenarios
from monte_carlo import sample_worlds,evaluate_worlds,summarize,spearman_sensitivity


class MonteCarloTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=load_inputs(ROOT/'data/model_inputs.json')
        cls.config=load_inputs(ROOT/'data/monte_carlo_assumptions.json')

    def test_seed_reproduces_draws_without_modifying_inputs(self):
        before=copy.deepcopy(self.inputs)
        a,da=sample_worlds(self.inputs,self.config,300,123,'triangular')
        b,db=sample_worlds(self.inputs,self.config,300,123,'triangular')
        c,_=sample_worlds(self.inputs,self.config,300,124,'triangular')
        for key in a:np.testing.assert_array_equal(a[key],b[key])
        self.assertFalse(np.array_equal(a['large_share'],c['large_share']))
        self.assertEqual(self.inputs,before)
        self.assertEqual(da,db)

    def test_generated_worlds_preserve_case_constraints_and_scalar_results(self):
        w,diagnostics=sample_worlds(self.inputs,self.config,100,4,'uniform')
        out=evaluate_worlds(self.inputs,w)
        base=next(c for c in scenarios(self.inputs) if c['id']=='ozon_stock_base')
        ids=['H1','H2','H3','H4','H5','H6.1']
        self.assertEqual(diagnostics['accepted'],100)
        self.assertGreaterEqual(diagnostics['attempted'],100)
        for index in range(12):
            p,f=w['large_share'][index],w['fav_large_share'][index]
            shares=[(1-p)*f,p*f,p*(1-f),(1-p)*(1-f)]
            self.assertAlmostEqual(sum(shares),1)
            self.assertAlmostEqual(f+w['owners_small'][index]*(1-f),.7)
            for h,hid in enumerate(ids):
                inputs=copy.deepcopy(self.inputs)
                inputs['hypotheses']=[next(x for x in inputs['hypotheses'] if x['id']==hid)]
                inputs['uplift']=float(w['uplift'][index,h])
                case=copy.deepcopy(base)
                case.update(shares=shares,global_cr=float(w['global_cr'][index]),
                    whale_cr=float(w['global_cr'][index]-sum(s*g for s,g in zip(shares,inputs['case_cr_gaps']))),
                    owners_small=float(w['owners_small'][index]),overlap=float(w['overlap'][index]),
                    h1_need=float(w['h1_need'][index]),h4_reach_multiplier=1.)
                for key in ['behavior_penalty','product_penalty','loss_c','loss_f','income_delta']:
                    case[key]=float(w[key][index,h])
                case['reach_scale']=float(w['reach_multiplier'][index,h])
                scalar=evaluate(inputs,case)[0]
                for key in ['delta_pp','cr1','relative_cr']:
                    self.assertAlmostEqual(out[key][index,h],scalar[key],places=10,msg=key)
                for key in ['guard_c','guard_f','guard_arpu']:
                    self.assertEqual(bool(out[key][index,h]),scalar[key],key)
        self.assertTrue(np.all((out['cr1']>=0)&(out['cr1']<=1)))

    def test_zero_effect_has_ties_and_selects_no_change(self):
        w,_=sample_worlds(self.inputs,self.config,120,8,'triangular')
        for key in ['uplift','loss_c','loss_f','income_delta']:w[key][:]=0
        out=evaluate_worlds(self.inputs,w)
        rows,extra=summarize(out)
        for row in rows:
            self.assertAlmostEqual(row['median_delta_pp'],0)
            self.assertAlmostEqual(row['top_share'],1/6)
            self.assertEqual(row['positive_and_safe_share'],0)
            self.assertEqual(row['safe_choice_share'],0)
        self.assertEqual(extra['no_safe_positive_choice_share'],1)
        self.assertAlmostEqual(sum(r['top_share'] for r in rows),1)

    def test_spearman_reports_direction_and_ignores_constants(self):
        x=np.arange(20,dtype=float)
        rows=spearman_sensitivity({'factor':x,'constant':np.ones(20)},np.column_stack([x,-x]))
        values={(r['factor'],r['hypothesis']):r['spearman_rho'] for r in rows}
        self.assertAlmostEqual(values[('factor','H1')],1)
        self.assertAlmostEqual(values[('factor','H2')],-1)
        self.assertEqual(values[('constant','H1')],0)

    def test_regret_includes_option_to_leave_product_unchanged(self):
        out={'delta_pp':np.tile(-np.arange(1,7,dtype=float)/10,(10,1))}
        for key in ['guard_c','guard_f','guard_arpu','positive_and_safe']:
            out[key]=np.zeros((10,6),dtype=bool)
        rows,extra=summarize(out)
        self.assertAlmostEqual(rows[0]['expected_regret_pp'],.1)
        self.assertAlmostEqual(rows[5]['expected_regret_pp'],.6)
        self.assertEqual(extra['no_safe_positive_choice_share'],1)

    def test_invalid_specs_and_empty_runs_fail(self):
        for n in [0,-1]:
            with self.assertRaises(ValueError):sample_worlds(self.inputs,self.config,n,1,'triangular')
        bad=copy.deepcopy(self.config);bad['common']['large_share']=[.4,.3,.2]
        with self.assertRaises(ValueError):sample_worlds(self.inputs,bad,20,1,'triangular')
        with self.assertRaises(ValueError):sample_worlds(self.inputs,self.config,20,1,'unknown')

    def test_cli_exports_auditable_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            p=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/run_monte_carlo.py'),
                '--draws','400','--profiles','triangular','--output',folder],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(p.returncode,0,p.stderr)
            report=json.loads((Path(folder)/'triangular/summary.json').read_text(encoding='utf8'))
            self.assertEqual(report['draws'],400)
            self.assertEqual(len(report['hypotheses']),6)
            self.assertFalse(report['measured_effects'])
            self.assertIn('input_sha256',report)
            self.assertIn('assumptions_sha256',report)
            self.assertAlmostEqual(sum(r['top_share'] for r in report['hypotheses']),1)
            self.assertTrue((Path(folder)/'triangular/sensitivity.csv').exists())


if __name__=='__main__':unittest.main()
