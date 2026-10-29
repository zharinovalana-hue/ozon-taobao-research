import sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from taobao import aggregate_events,read_users,summarize

class TaobaoTests(unittest.TestCase):
    def test_unique_items_deduplicated_across_chunks_and_zero_users_retained(self):
        rows=['1,11,1,cart,1511539200','2,12,1,pv,1511539200','1,11,1,cart,1511539201',
              '1,11,1,fav,1511539202','1,13,1,cart,1511539203','1,13,1,buy,1511539204']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);archive=path/'events.zip';out=path/'users.csv'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('UserBehavior.csv','\n'.join(rows))
            metadata=aggregate_events(archive,out,chunksize=2);d=read_users(out)
            self.assertEqual(d.user_id.tolist(),[1,2])
            self.assertEqual(d.cart_count.tolist(),[2,0])
            self.assertEqual(d.fav_count.tolist(),[1,0])
            self.assertEqual(d.purchased.tolist(),[True,False])
            self.assertEqual(metadata['events'],6)

    def test_string_false_does_not_become_true(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'x.csv';p.write_text('user_id,cart_count,fav_count,purchased\n1,0,0,False\n2,1,0,True\n')
            self.assertEqual(read_users(p).purchased.tolist(),[False,True])

    def test_duplicate_users_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'x.csv';p.write_text('user_id,cart_count,fav_count,purchased\n1,0,0,False\n1,1,0,True\n')
            with self.assertRaises(ValueError):summarize(p)

    def test_published_counts_reconcile(self):
        import json
        p=Path(__file__).resolve().parents[1]/'data/taobao_summary.json';s=json.loads(p.read_text(encoding='utf-8'))
        self.assertEqual(sum(c['users'] for c in s['cohorts']),s['users'])
        self.assertEqual(sum(c['buyers'] for c in s['cohorts']),s['buyers'])
        self.assertEqual([c['users'] for c in s['cohorts']],[90851,11747,98635,786761])

    def test_interpolated_percentile_threshold_is_not_rounded_down(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'x.csv';p.write_text('user_id,cart_count,fav_count,purchased\n1,0,0,False\n2,1,1,True\n3,2,2,True\n4,3,3,True\n')
            summary=summarize(p)
            p90=next(t for t in summary['thresholds'] if t['quantile']==.9)
            self.assertEqual(p90['cart_threshold'],3)
            self.assertEqual(p90['fav_threshold'],3)

if __name__=='__main__':unittest.main()
