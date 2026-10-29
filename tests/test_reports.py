import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run import generate


class ReportTests(unittest.TestCase):
    def render(self,h4_scale=1.,uplift=.1):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['data','scripts','docs','archive/taobao_projection_2026-10-29']:
                (root/name).mkdir(parents=True,exist_ok=True)
            for name in ['data/model_inputs.json','data/taobao_summary.json','data/sources.json',
                         'scripts/write_reports.py','archive/taobao_projection_2026-10-29/model_results.json']:
                shutil.copyfile(ROOT/name,root/name)
            inputs=json.loads((root/'data/model_inputs.json').read_text(encoding='utf8'))
            inputs['uplift']=uplift
            for row in inputs['hypotheses'][3]['reach']:
                row[:]=[v*h4_scale for v in row]
            (root/'data/model_inputs.json').write_text(json.dumps(inputs),encoding='utf8')
            generate(root)
            p=subprocess.run([sys.executable,'-X','utf8',str(root/'scripts/write_reports.py')],capture_output=True,text=True,encoding='utf8')
            self.assertEqual(p.returncode,0,p.stderr)
            return (root/'docs/findings.md').read_text(encoding='utf8')

    def test_report_updates_winner_and_threshold_after_h4_reach_edit(self):
        report=self.render(h4_scale=.1)
        self.assertIn('Лидер базового сценария: H2',report)
        self.assertIn('11,63%',report)
        self.assertNotIn('82,40%',report)
        self.assertNotIn('H4 лидирует среди всех H',report)

    def test_report_handles_no_crossover(self):
        report=self.render(h4_scale=1.3)
        self.assertIn('Нет пересечения',report)

    def test_report_handles_equal_effects(self):
        report=self.render(uplift=0)
        self.assertIn('Равенство эффектов',report)
        self.assertNotIn('H4 выше H1 во всех',report)
