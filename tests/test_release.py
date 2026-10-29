import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbook_io import FormulaBook
from ozon_model import load_inputs,scenarios,evaluate

class ReleaseTests(unittest.TestCase):
    def test_immutable_original_hash(self):
        expected=load_inputs(ROOT/'data/model_inputs.json')['baseline_sha256']
        self.assertEqual(hashlib.sha256((ROOT/'models/Ozon_модель_кейса_исходная.xlsx').read_bytes()).hexdigest(),expected)

    def test_all_original_calculation_formulas_preserved(self):
        original=FormulaBook(ROOT/'models/Ozon_модель_кейса_исходная.xlsx')
        current=FormulaBook(ROOT/'models/Ozon_модель_кейса.xlsx')
        for address,value in original.cells['Расчёт'].items():
            if isinstance(value,str) and value.startswith('='):
                self.assertEqual(current.cells['Расчёт'][address],value,address)

    def test_all_exported_formula_caches_are_current(self):
        current=FormulaBook(ROOT/'models/Ozon_модель_кейса.xlsx')
        self.assertEqual(current.compare_caches(),[])
        self.assertEqual(current.get('Сравнение','B3'),'Актуально')

    def test_selector_changes_results_and_stale_warning_detects_driver_edit(self):
        b=FormulaBook(ROOT/'models/Ozon_модель_кейса.xlsx')
        b.set('Параметры','B3',2)
        self.assertAlmostEqual(b.get('Итоги','E8'),157.97396138092518,places=7)
        self.assertEqual(b.get('Сравнение','B3'),'Актуально')
        b.set('Входы H','C6',.41)
        self.assertIn('устарели',b.get('Сравнение','B3'))

    def test_uplift_change_marks_comparison_stale(self):
        b=FormulaBook(ROOT/'models/Ozon_модель_кейса.xlsx')
        b.set('Параметры','B10',.2)
        self.assertIn('устарели',b.get('Сравнение','B3'))

    def test_per_cohort_weights_can_be_refreshed(self):
        import copy
        from refresh_excel import refresh
        inputs=copy.deepcopy(load_inputs(ROOT/'data/model_inputs.json'))
        inputs['weights'][2]=[1.,.2,1.,.3]
        cases=scenarios(inputs,ROOT/'data/taobao_summary.json')
        results=[r for c in cases for r in evaluate(inputs,c)]
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'weights.xlsx';refresh(ROOT,inputs,cases,results,output)
            book=FormulaBook(output)
            self.assertEqual(book.get('Когорты','O7'),1.)
            from cart_stock import crossover
            self.assertAlmostEqual(book.get('Порог H1 H4','D25'),crossover(inputs,.4,.15,1.)['threshold'],places=8)
            self.assertEqual(book.get('Порог H1 H4','B3'),'Актуально')
            x=next(r for r in results if r['scenario']=='ozon_stock_base' and r['hypothesis']=='H1')
            self.assertAlmostEqual(book.get('Итоги','F8'),x['delta_pp'],places=8)

    def test_all_scenarios_match_live_excel_formulas(self):
        inputs=load_inputs(ROOT/'data/model_inputs.json');cases=scenarios(inputs,ROOT/'data/taobao_summary.json')
        b=FormulaBook(ROOT/'models/Ozon_модель_кейса.xlsx')
        for i,c in enumerate(cases,1):
            b.set('Параметры','B3',i)
            self.assertEqual(b.get('Когорты','X10'),1,c['id'])
            for r,x in zip([8,9,10,11,12,14,15,16],evaluate(inputs,c)):
                self.assertAlmostEqual(b.get('Итоги','F'+str(r)),x['delta_pp'],places=8,msg=c['id'])

    def test_refresh_keeps_asymmetric_h1_reach_in_controls(self):
        from refresh_excel import refresh
        inputs=load_inputs(ROOT/'data/model_inputs.json')
        inputs['hypotheses'][0]['reach'][1][0]=.5
        inputs['hypotheses'][0]['reach'][2][0]=.35
        cases=scenarios(inputs)
        results=[r for c in cases for r in evaluate(inputs,c)]
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'h1.xlsx'
            refresh(ROOT,inputs,cases,results,output)
            book=FormulaBook(output)
            self.assertEqual(book.get('Сравнение','B3'),'Актуально')
            for i,c in enumerate(cases,1):
                book.set('Параметры','B3',i)
                expected=next(r for r in results if r['scenario']==c['id'] and r['hypothesis']=='H1')
                self.assertAlmostEqual(book.get('Итоги','E8'),expected['delta_buyers'],places=7,msg=c['id'])

    def test_recorded_original_45_checks_were_executed(self):
        result=load_inputs(ROOT/'results/excel_verification.json')
        self.assertEqual(len(result['original_tests']),45)
        self.assertEqual(len(result['scenario_parity']),len(scenarios(load_inputs(ROOT/'data/model_inputs.json'),None)))
        self.assertTrue(result['stale_warning_verified'])

    def test_refresh_matches_all_scenarios_after_cr_gap_edit(self):
        from refresh_excel import refresh
        inputs=load_inputs(ROOT/'data/model_inputs.json')
        inputs['case_cr_gaps']=[0,-.08,-.16,-.08]
        cases=scenarios(inputs)
        results=[r for c in cases for r in evaluate(inputs,c)]
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'gaps.xlsx';refresh(ROOT,inputs,cases,results,output)
            book=FormulaBook(output)
            for i,c in enumerate(cases,1):
                book.set('Параметры','B3',i)
                self.assertEqual(book.get('Параметры','B28'),1,c['id'])
                for row,x in zip([8,9,10,11,12,14,15,16],evaluate(inputs,c)):
                    self.assertAlmostEqual(book.get('Итоги','F'+str(row)),x['delta_pp'],places=8,msg=c['id'])

    def test_reproducible_refresh_without_raw_data(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'reproduced.xlsx'
            p=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/run.py'),'--output',str(output)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(p.returncode,0,p.stderr)
            book=FormulaBook(output)
            self.assertEqual(book.get('Параметры','B3'),6)
            self.assertEqual(book.compare_caches(),[])

if __name__=='__main__':unittest.main()
