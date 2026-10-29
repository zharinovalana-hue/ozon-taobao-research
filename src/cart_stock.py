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
    from ozon_model import scenarios,evaluate
    import copy
    template=next(c for c in scenarios(inputs,None) if c['id']=='ozon_stock_base')
    def diff(p):
        c=copy.deepcopy(template);c.update(shares=joint(p),large_share=p,h1_need=need,h4_reach_multiplier=h4_scale,
                                         global_cr=global_cr,whale_cr=global_cr+.09*(.6+p))
        rr=evaluate(inputs,c)
        return rr[0]['delta_pp']-rr[3]['delta_pp']
    lo=max(.000001,(.18-global_cr-.054)/.09+1e-8);hi=.999999
    root=None
    if diff(lo)>=0:root=lo
    elif diff(hi)>0:
        for _ in range(60):
            mid=(lo+hi)/2
            if diff(mid)>0:hi=mid
            else:lo=mid
        root=(lo+hi)/2
    b=bounds()
    return dict(h1_conditional_need=need,global_cr=global_cr,h4_reach_multiplier=h4_scale,threshold=root,
                within_case_bounds=root is not None and b['lower_necessary']<=root<=b['upper_necessary'],
                h1_minus_h4_at_50_pp=diff(.5),
                interpretation='H1 wins strictly above root with all other inputs fixed; outside bounds is infeasible for case stock.')
