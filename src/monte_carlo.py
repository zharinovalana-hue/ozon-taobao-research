"""Paired Monte Carlo propagation of explicitly assumed input distributions.

Vectorized equations match ozon_model.evaluate; no measured causal effects implied.
"""
import copy
import math

import numpy as np
import pandas as pd

from cart_stock import bounds

IDS=['H1','H2','H3','H4','H5','H6.1']
FIELDS=['uplift','reach_multiplier','behavior_penalty','product_penalty','loss_c','loss_f','income_delta']
PROFILES=['triangular','uniform','low_effect']


def _triplet(spec):
    if len(spec)!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in spec):
        raise ValueError('Expected three finite numeric assumption values')
    a,m,b=spec
    if not a<=m<=b:raise ValueError('Require minimum <= mode <= maximum')
    return a,m,b


def _draw(rng,spec,n,profile):
    a,m,b=_triplet(spec)
    if a==b:return np.full(n,a,dtype=float)
    u=rng.random(n)
    if profile=='uniform':return a+(b-a)*u
    pivot=(m-a)/(b-a)
    return np.where(u<pivot,a+np.sqrt(u*(b-a)*(m-a)),b-np.sqrt((1-u)*(b-a)*(b-m)))


def sample_worlds(inputs,config,n,seed,profile='triangular'):
    if not isinstance(n,int) or isinstance(n,bool) or n<=0:raise ValueError('draws must be a positive integer')
    if profile not in PROFILES:raise ValueError('Unknown assumption profile')
    cfg=copy.deepcopy(config)
    for spec in cfg['common'].values():_triplet(spec)
    for spec in cfg['hypothesis_defaults'].values():_triplet(spec)
    for override in cfg['hypothesis_overrides'].values():
        for spec in override.values():_triplet(spec)
    a,_,b=cfg['common']['large_share'];limit=bounds()
    if a<limit['lower_necessary'] or b>limit['upper_necessary']:raise ValueError('Cart share outside case stock bounds')
    fa,_,fb=cfg['common']['fav_large_share']
    if not 0<=fa<=fb<1:raise ValueError('Favorite share must lie in [0,1)')
    rng=np.random.default_rng(seed);chunks={};accepted=attempted=rejected=0
    while accepted<n:
        size=min(n-accepted,20000)
        if attempted>=20*n:raise ValueError('Assumptions produce too few feasible worlds; inspect bounds')
        w={key:_draw(rng,spec,size,profile) for key,spec in cfg['common'].items()}
        w['owners_small']=(.7-w['fav_large_share'])/(1-w['fav_large_share'])
        for key in FIELDS:
            columns=[]
            for hid in IDS:
                spec=cfg['hypothesis_overrides'].get(hid,{}).get(key,cfg['hypothesis_defaults'][key])
                if profile=='low_effect' and key=='uplift':spec=[spec[0],min(spec[2],max(spec[0],.03)),spec[2]]
                columns.append(_draw(rng,spec,size,profile))
            w[key]=np.column_stack(columns)
        valid=evaluate_worlds(inputs,w,strict=False)['valid']
        count=int(valid.sum());attempted+=size;rejected+=size-count;accepted+=count
        for key,value in w.items():chunks.setdefault(key,[]).append(value[valid])
    return {k:np.concatenate(v,axis=0) for k,v in chunks.items()},dict(
        accepted=n,attempted=attempted,rejected_infeasible=rejected,acceptance_rate=n/attempted,
        conditioning='Reported distributions describe accepted feasible worlds, not unconditional input priors')


def evaluate_worlds(inputs,w,strict=True):
    p,f=w['large_share'],w['fav_large_share'];n=len(p)
    if n==0:raise ValueError('No worlds to evaluate')
    q=np.column_stack([(1-p)*f,p*f,p*(1-f),(1-p)*(1-f)])
    gaps=np.asarray(inputs['case_cr_gaps']);whale=w['global_cr']-q@gaps
    traffic=np.asarray(inputs['traffic']);weights=np.asarray(inputs['weights'])
    if traffic.shape!=(4,3) or weights.shape!=(4,4):raise ValueError('Require four traffic and weight rows')
    cart=q@traffic[:,0];fav=q@traffic[:,1]
    valid=np.isfinite(q).all(axis=1)&(q.min(axis=1)>=0)&(w['global_cr']>0)
    valid &= np.isfinite(w['owners_small'])&(w['owners_small']>=0)&(w['owners_small']<=1)
    valid &= np.isclose(cart,inputs['case_daily_cart'],atol=1e-10,rtol=0)
    valid &= np.isclose(fav,inputs['case_daily_fav'],atol=1e-10,rtol=0)&(cart>0)&(fav>0)
    valid &= np.isclose(f+w['owners_small']*(1-f),.7,atol=1e-10,rtol=0)
    out={k:np.zeros((n,len(IDS))) for k in ['delta_pp','cr1','relative_cr','arpu_delta_index_pp']}
    out.update({k:np.ones((n,len(IDS)),dtype=bool) for k in ['guard_c','guard_f','guard_arpu']})
    definitions={h['id']:h for h in inputs['hypotheses']}
    for h,hid in enumerate(IDS):
        if hid not in definitions:raise ValueError('Missing hypothesis: '+hid)
        retention=(1-w['behavior_penalty'][:,h])*(1-w['product_penalty'][:,h])
        for key in ['uplift','behavior_penalty','product_penalty','loss_c','loss_f']:
            valid &= np.isfinite(w[key][:,h])&(w[key][:,h]>=0)&(w[key][:,h]<=1)
        valid &= np.isfinite(w['income_delta'][:,h])&(np.abs(w['income_delta'][:,h])<=1)
        valid &= np.isfinite(w['reach_multiplier'][:,h])&(w['reach_multiplier'][:,h]>=0)
        b0=np.zeros(n);b1=b0.copy();c0=b0.copy();c1=b0.copy();f0=b0.copy();f1=b0.copy();rev1=b0.copy()
        for k in range(4):
            pc,pf=traffic[k,:2];both=pf*w['overlap']
            states=np.column_stack([pc-both,pf-both,both,1-pc-pf+both])
            norm=states@weights[k];cohort_cr=whale+gaps[k]
            owner=np.ones(n) if k<2 else w['owners_small']
            valid &= np.isfinite(states).all(axis=1)&(states.min(axis=1)>=-1e-12)&(norm>0)
            valid &= (cohort_cr>=0)&(cohort_cr<=1)&(pf<=owner+1e-12)&(both<=pc*owner+1e-12)
            valid &= (cohort_cr*weights[k].max()/norm<=1+1e-12)
            reach=np.broadcast_to(np.array(definitions[hid]['reach'][k],dtype=float),(n,3)).copy()
            if hid=='H1' and k in [1,2]:reach[:,0]=w['h1_need']
            reach*=w['reach_multiplier'][:,h,None]
            ec,ef,inter=reach.T
            valid &= np.isfinite(reach).all(axis=1)&(reach.min(axis=1)>=0)&(np.maximum(ec,ef)<=1)
            valid &= (inter>=np.maximum(0,ec+ef-1)-1e-12)&(inter<=np.minimum(ec,ef)+1e-12)
            for t,(vc,vf) in enumerate([(1,0),(0,1),(1,1),(0,0)]):
                population=q[:,k]*states[:,t]
                cr=cohort_cr*weights[k,t]/norm
                target=ec*vc+ef*vf-inter*vc*vf
                before=population*cr
                keep=(1-w['loss_c'][:,h]*vc)*(1-w['loss_f'][:,h]*vf)
                after=before*keep*(1+w['uplift'][:,h]*target*retention)
                valid &= np.isfinite(after)&(after>=-1e-12)&(after<=population+1e-12)
                b0+=before;b1+=after;c0+=before*vc;c1+=after*vc;f0+=before*vf;f1+=after*vf
                rev1+=after*(1+w['income_delta'][:,h]*target)
        out['delta_pp'][:,h]=100*(b1-b0)
        out['cr1'][:,h]=b1
        out['relative_cr'][:,h]=(b1-b0)/b0
        out['arpu_delta_index_pp'][:,h]=100*(rev1/b0-1)
        out['guard_c'][:,h]=c1/cart+1e-12>=c0/cart
        out['guard_f'][:,h]=f1/fav+1e-12>=f0/fav
        out['guard_arpu'][:,h]=rev1+1e-12>=b0
    out['positive_and_safe']=(out['delta_pp']>1e-10)&out['guard_c']&out['guard_f']&out['guard_arpu']
    out['valid']=valid
    if strict and not valid.all():raise ValueError(f'{int((~valid).sum())} infeasible worlds')
    return out


def summarize(out):
    delta=out['delta_pp'];n,h=delta.shape
    best=delta.max(axis=1,keepdims=True)
    top=np.isclose(delta,best,atol=1e-10,rtol=0);top_credit=top/top.sum(axis=1,keepdims=True)
    eligible=out['positive_and_safe'];safe_values=np.where(eligible,delta,-np.inf)
    safe_best=safe_values.max(axis=1,keepdims=True)
    safe_top=eligible&np.isclose(safe_values,safe_best,atol=1e-10,rtol=0)
    safe_count=safe_top.sum(axis=1,keepdims=True)
    safe_credit=np.divide(safe_top,safe_count,out=np.zeros_like(delta),where=safe_count>0)
    rows=[]
    for j in range(h):
        lo,median,hi=np.quantile(delta[:,j],[.025,.5,.975])
        rows.append(dict(hypothesis=IDS[j],p025_delta_pp=float(lo),median_delta_pp=float(median),p975_delta_pp=float(hi),
            top_share=float(top_credit[:,j].mean()),positive_share=float((delta[:,j]>1e-10).mean()),
            positive_and_safe_share=float(eligible[:,j].mean()),safe_choice_share=float(safe_credit[:,j].mean()),
            guard_c_fail_share=float((~out['guard_c'][:,j]).mean()),guard_f_fail_share=float((~out['guard_f'][:,j]).mean()),
            guard_arpu_fail_share=float((~out['guard_arpu'][:,j]).mean()),
            expected_regret_pp=float((np.maximum(best[:,0],0)-delta[:,j]).mean()),
            top_share_mc_se=float(top_credit[:,j].std(ddof=1)/math.sqrt(n)) if n>1 else 0.))
    return rows,dict(no_safe_positive_choice_share=float((safe_count[:,0]==0).mean()),
        intervals='Central 95% simulation ranges, conditional on assumed distributions; not confidence intervals for real effects',
        ties='Equal fractional credit, H6 variants represented once',
        regret='Mean best-minus-selected delta CR, including no-change baseline zero and ignoring guardrails; see separate safety metrics',
        mc_se='Monte Carlo integration error only; not business uncertainty')


def spearman_sensitivity(factors,delta):
    """Rank-correlation screening, not causal effects or Sobol indices."""
    x=pd.DataFrame(factors).rank(method='average').to_numpy(dtype=float,copy=True)
    y=pd.DataFrame(delta).rank(method='average').to_numpy(dtype=float,copy=True)
    x-=x.mean(axis=0);y-=y.mean(axis=0)
    denominator=np.sqrt((x*x).sum(axis=0)[:,None]*(y*y).sum(axis=0)[None,:])
    rho=np.divide(x.T@y,denominator,out=np.zeros_like(denominator),where=denominator>0)
    return [dict(factor=name,hypothesis=IDS[h],spearman_rho=float(rho[j,h]))
        for j,name in enumerate(factors) for h in range(delta.shape[1])]


def factor_columns(w):
    out={k:v for k,v in w.items() if v.ndim==1 and k!='owners_small'}
    for key in FIELDS:
        for j,hid in enumerate(IDS):out[hid+'.'+key]=w[key][:,j]
    return out
