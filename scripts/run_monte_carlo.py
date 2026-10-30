"""Reproducible uncertainty analysis; does not change the original workbook."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ozon_model import load_inputs
from monte_carlo import IDS,PROFILES,sample_worlds,evaluate_worlds,summarize,spearman_sensitivity,factor_columns


def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run_profile(root,config,n,seed,profile,output,save_draws=False):
    inputs=load_inputs(root/'data/model_inputs.json')
    worlds,diagnostics=sample_worlds(inputs,config,n,seed,profile)
    out=evaluate_worlds(inputs,worlds);rows,extra=summarize(out)
    delta=out['delta_pp'];factors=factor_columns(worlds)
    summary=dict(profile=profile,draws=n,seed=seed,measured_effects=False,
        input_sha256=hashlib.sha256((root/'data/model_inputs.json').read_bytes()).hexdigest(),
        assumptions_sha256=hashlib.sha256((root/'data/monte_carlo_assumptions.json').read_bytes()).hexdigest(),
        engine_sha256=hashlib.sha256((root/'src/monte_carlo.py').read_bytes()).hexdigest(),
        numpy_version=np.__version__,sampling=diagnostics,hypotheses=rows,**extra)
    pairwise=[]
    for i,left in enumerate(IDS):
        for j,right in enumerate(IDS):
            d=delta[:,i]-delta[:,j]
            lo,median,hi=np.quantile(d,[.025,.5,.975])
            pairwise.append(dict(left=left,right=right,win_share=float(((d>1e-10)+.5*(np.abs(d)<=1e-10)).mean()),
                p025_difference_pp=float(lo),median_difference_pp=float(median),p975_difference_pp=float(hi)))
    convergence=[]
    for m in sorted(set([min(n,1000),min(n,10000),min(n,50000),n])):
        subset={k:v[:m] for k,v in out.items()}
        for row in summarize(subset)[0]:convergence.append(dict(draws=m,**row))
    sensitivity=spearman_sensitivity(factors,delta)
    margin=spearman_sensitivity(factors,(delta[:,3]-delta[:,1])[:,None])
    for row in margin:row['hypothesis']='H4_minus_H2'
    output.mkdir(parents=True,exist_ok=True)
    write_json(output/'summary.json',summary);write_csv(output/'summary.csv',rows)
    write_csv(output/'sensitivity.csv',sensitivity);write_csv(output/'pairwise.csv',pairwise)
    write_csv(output/'sensitivity_margin.csv',margin)
    write_csv(output/'convergence.csv',convergence)
    accepted=[dict(factor=k,min=float(v.min()),mean=float(v.mean()),p025=float(np.quantile(v,.025)),
        p50=float(np.median(v)),p975=float(np.quantile(v,.975)),max=float(v.max())) for k,v in factors.items()]
    write_csv(output/'accepted_inputs.csv',accepted)
    if save_draws:np.savez_compressed(output/'draws.npz',**worlds,delta_pp=delta)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draws',type=int,default=None)
    parser.add_argument('--seed',type=int,default=None)
    parser.add_argument('--profiles',nargs='+',choices=PROFILES,default=None)
    parser.add_argument('--output',type=Path,default=ROOT/'results/monte_carlo')
    parser.add_argument('--save-draws',action='store_true')
    args=parser.parse_args();config=load_inputs(ROOT/'data/monte_carlo_assumptions.json')
    n=args.draws if args.draws is not None else config['draws']
    seed=args.seed if args.seed is not None else config['seed']
    args.output.mkdir(parents=True,exist_ok=True)
    runs=[]
    for profile in args.profiles or config['profiles']:
        report=run_profile(ROOT,config,n,seed,profile,args.output/profile,args.save_draws)
        runs.append(report)
        print(f'{profile}: {n:,} accepted worlds; acceptance {report["sampling"]["acceptance_rate"]:.2%}',flush=True)
    write_json(args.output/'assumptions_used.json',config)
    write_json(args.output/'profiles.json',runs)


if __name__=='__main__':main()
