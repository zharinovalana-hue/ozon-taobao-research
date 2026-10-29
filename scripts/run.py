"""Regenerate small aggregates, scenarios, results and an existing workbook."""
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ozon_model import load_inputs,evaluate,scenarios,public_scale

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def generate(root=ROOT):
    inputs=load_inputs(root/'data/model_inputs.json');summary=load_inputs(root/'data/taobao_summary.json')
    cases=scenarios(inputs,root/'data/taobao_summary.json')
    results=[r for c in cases for r in evaluate(inputs,c)]
    public=public_scale(inputs,cases);intensity=public['orders_per_assumed_active_user_day']
    rows=[]
    for c in cases:
        rows.append({**{k:v for k,v in c.items() if k not in ['shares','weights']},
                     **{f'S{k+1}':v for k,v in enumerate(c['shares'])},
                     'orders_per_buying_user_day_proxy':intensity/c['global_cr'],
                     'intensity_caution':c['global_cr']>intensity})
    eligible=[c['id'] for c in cases if c['kind'] in ['base','cautious','favorable','threshold','cr','overlap','reach','platform']]
    robust=[]
    for h in inputs['hypotheses']:
        rr=[r for r in results if r['scenario'] in eligible and r['hypothesis']==h['id']]
        ranks=[]
        for r in rr:
            alternatives=[x for x in results if x['scenario']==r['scenario'] and x['hypothesis'] in ['H1','H2','H3','H4','H5','H6.1']]
            ranks.append(1+sum(x['delta_pp']>r['delta_pp']+1e-12 for x in alternatives))
        robust.append(dict(hypothesis=h['id'],scenario_count=len(rr),min_delta_pp=min(r['delta_pp'] for r in rr),
            max_delta_pp=max(r['delta_pp'] for r in rr),rank_min=min(ranks),rank_max=max(ranks),
            all_positive=all(r['delta_pp']>0 for r in rr),all_guardrails_pass=all(r['guard_c'] and r['guard_f'] and r['guard_arpu'] for r in rr),
            wins=sum(x==1 for x in ranks)))
    root.joinpath('results').mkdir(exist_ok=True)
    write_json(root/'data/scenarios.json',cases)
    write_csv(root/'results/scenario_results.csv',results)
    write_csv(root/'results/scenario_inputs.csv',rows)
    write_csv(root/'results/robustness.csv',robust)
    write_json(root/'results/public_scale.json',public)
    write_json(root/'results/model_results.json',dict(cases=cases,results=results,robustness=robust,public_scale=public))
    cohort_rows=[]
    for t in summary['thresholds']:
        for c in t['cohorts']:cohort_rows.append(dict(quantile=t['quantile'],cart_threshold=t['cart_threshold'],fav_threshold=t['fav_threshold'],**c))
    write_csv(root/'data/taobao_cohorts.csv',cohort_rows)
    return inputs,cases,results

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--users',type=Path,help='Existing taobao_users.csv; no raw archive needed')
    p.add_argument('--no-excel',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'models/Ozon_модель_кейса.xlsx')
    a=p.parse_args()
    if a.users:
        from taobao import summarize
        write_json(ROOT/'data/taobao_summary.json',summarize(a.users))
    inputs,cases,results=generate()
    if not a.no_excel:
        from refresh_excel import refresh
        refresh(ROOT,inputs,cases,results,a.output)
    print(f'Recalculated {len(cases)} scenarios × 8 alternatives; sources and assumptions remain separate.')

if __name__=='__main__':main()
