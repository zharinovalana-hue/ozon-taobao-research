"""Constructed stock distributions, NOT observed Ozon or Taobao estimates."""
import math

def bounds():
    # P(X<=24)>=1/2, X<40 implies integer X<=39, X<=300.
    # E[X] <= .5*24 + (.5-p)*39 + p*300 =31.5+261p.
    return dict(lower_necessary=(60-31.5)/261,upper_necessary=.5,
                interpretation='Necessary bounds, not a confidence interval; endpoint depends on median convention.')

def distributions():
    out=[]
    for p in [.11,.20,.30,.40,.49]:
        n=10000;large=round(n*p);middle=4900-large
        remaining=60*n-5100*24-middle*39-300
        low,extra=divmod(remaining,large-1)
        hist={24:5100,39:middle,low:large-1-extra}
        hist[low+1]=hist.get(low+1,0)+extra
        hist[300]=hist.get(300,0)+1
        hist=[dict(sku=x,users=k) for x,k in sorted(hist.items()) if k]
        assert all(x['sku']>=40 for x in hist if x['sku'] not in [24,39])
        out.append(dict(id='stock_'+str(round(p*100)),large_share=p,mean=60,median=24,maximum=300,
                        synthetic_users=n,large_conditional_mean=(60*n-5100*24-middle*39)/large,
                        histogram=hist,status='Constructed example, not fitted or observed'))
    return out

def joint(p,f=.4):
    return [(1-p)*f,p*f,p*(1-f),(1-p)*(1-f)]

def crossover(inputs,need=.4,global_cr=.15,h4_scale=1.):
    """Counterfactual root; feasibility reported separately, no truncated root."""
    from ozon_model import scenarios,evaluate,scenario_reach
    import copy
    template=next(c for c in scenarios(inputs,None) if c['id']=='ozon_stock_base')
    gaps=inputs['case_cr_gaps']
    gap0=sum(s*g for s,g in zip(joint(0),gaps))
    gap1=sum(s*g for s,g in zip(joint(1),gaps))
    slope=gap0-gap1
    def diff(p):
        c=copy.deepcopy(template);c.update(shares=joint(p),large_share=p,h1_need=need,h4_reach_multiplier=h4_scale,
                                         global_cr=global_cr,whale_cr=global_cr-sum(s*g for s,g in zip(joint(p),gaps)))
        rr=evaluate(inputs,c)
        by_id={r['hypothesis']:r for r in rr}
        return by_id['H1']['delta_pp']-by_id['H4']['delta_pp']
    # CR_cohort(p) is affine. Intersect its feasible interval for all
    # cohorts, including normalized state CR and the post-uplift bound.
    lo=0.;hi=1.
    probe=dict(template,h1_need=need,h4_reach_multiplier=h4_scale)
    retention=(1-probe['behavior_penalty'])*(1-probe['product_penalty'])
    for k,(pc,pf,_) in enumerate(probe.get('traffic',inputs['traffic'])):
        both=pf*probe['overlap'];states=[pc-both,pf-both,both,1-pc-pf+both]
        weights=probe.get('weights',inputs['weights'])[k]
        norm=sum(s*w for s,w in zip(states,weights))
        cap=min(1.,norm/max(weights))
        for h in inputs['hypotheses']:
            ec,ef,inter=[v*probe['reach_scale'] for v in scenario_reach(h,probe)[k]]
            for t,(vc,vf) in enumerate([(1,0),(0,1),(1,1),(0,0)]):
                reach=ec*vc+ef*vf-inter*vc*vf
                multiplier=weights[t]*(1-probe['loss_c']*vc)*(1-probe['loss_f']*vf)*(1+inputs['uplift']*reach*retention)
                if multiplier>0:cap=min(cap,norm/multiplier)
        intercept=global_cr-gap0+gaps[k]
        if abs(slope)<1e-15:
            if not 0<=intercept<=cap:raise ValueError('No feasible CR interval for crossover')
        else:
            a,b=sorted([-intercept/slope,(cap-intercept)/slope])
            lo=max(lo,a);hi=min(hi,b)
    lo=max(.000001,lo+1e-8);hi=min(.999999,hi-1e-8)
    if lo>=hi:raise ValueError('No feasible CR interval for crossover')
    feasible_lo,feasible_hi=lo,hi
    dlo,dhi=diff(lo),diff(hi)
    root=None;status='no_crossing'
    if abs(dlo)<1e-10 and abs(dhi)<1e-10:status='equal'
    elif dlo>0:status='h1_already_ahead'
    elif dhi>0:
        status='crossing'
        for _ in range(60):
            mid=(lo+hi)/2
            if diff(mid)>0:hi=mid
            else:lo=mid
        root=(lo+hi)/2
    b=bounds()
    return dict(h1_conditional_need=need,global_cr=global_cr,h4_reach_multiplier=h4_scale,threshold=root,
                within_case_bounds=root is not None and b['lower_necessary']<=root<=b['upper_necessary'],
                h1_minus_h4_at_50_pp=diff(.5) if feasible_lo<=.5<=feasible_hi else None,
                status=status,
                interpretation={'crossing':'H1 wins strictly above root with all other inputs fixed; outside bounds is infeasible for case stock.',
                                'equal':'Equal effects across the feasible CR interval; no winning threshold.',
                                'h1_already_ahead':'H1 is already ahead at the lower feasible CR boundary; no crossing in the interval.',
                                'no_crossing':'No H1 winning crossover in the feasible CR interval.'}[status])
