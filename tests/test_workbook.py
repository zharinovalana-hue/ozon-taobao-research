import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from workbook_io import FormulaBook

class FormulaTests(unittest.TestCase):
    def test_lazy_if_and_choose_do_not_evaluate_inactive_division_by_zero(self):
        b=FormulaBook.from_cells({'S':{'A1':0,'A2':'=IF(A1=0,"n.a.",1/A1)','A3':'=CHOOSE(2,1/0,12)'}})
        self.assertEqual(b.get('S','A2'),'n.a.')
        self.assertEqual(b.get('S','A3'),12)

    def test_ranges_blank_zero_and_sumproduct(self):
        b=FormulaBook.from_cells({'S':{'A1':2,'A2':3,'B1':4,'B2':5,'D1':'=SUMPRODUCT(A1:A2,B1:B2)','D2':'=COUNT(A1:A3)','D3':'=ISNUMBER(A3)'}})
        self.assertEqual(b.get('S','D1'),23)
        self.assertEqual(b.get('S','D2'),2)
        self.assertFalse(b.get('S','D3'))

    def test_unsupported_formula_and_cycle_fail_visibly(self):
        b=FormulaBook.from_cells({'S':{'A1':'=MAGIC(1)','A2':'=A3','A3':'=A2'}})
        with self.assertRaises(ValueError):b.get('S','A1')
        with self.assertRaises(ValueError):b.get('S','A2')

    def test_all_original_formula_caches_match_recalculation(self):
        p=Path(__file__).resolve().parents[1]/'models/Ozon_модель_кейса_исходная.xlsx'
        b=FormulaBook(p)
        mismatches=b.compare_caches()
        self.assertEqual(mismatches,[])

    def test_export_preserves_formulas_and_refreshes_caches(self):
        p=Path(__file__).resolve().parents[1]/'models/Ozon_модель_кейса_исходная.xlsx'
        b=FormulaBook(p);b.set('Параметры','B8',200000)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'test.xlsx';b.save(out);after=FormulaBook(out)
            self.assertEqual(after.get('Итоги','E5'),200000)
            self.assertAlmostEqual(after.get('Итоги','E8'),2*157.97396138092518,places=7)
            self.assertEqual(after.compare_caches(),[])

if __name__=='__main__':unittest.main()
