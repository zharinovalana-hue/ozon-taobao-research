"""Scenario engine reproducing the existing Ozon workbook's unique-user equations.

Revenue is an illustrative index, never inferred from GMV or claimed as measured ARPU.
"""
import copy
import json
import math
from pathlib import Path

def load_inputs(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def _finite(values):
    return all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in values)

def validate(inputs,c):
    if not _finite([inputs['uplift']]) or not 0<=inputs['uplift']<=1:raise ValueError('Uplift must be finite and within [0,1]')
    shares=c['shares']
    if len(shares)!=4 or not _finite(shares) or min(shares)<0 or abs(sum(shares)-1)>1e-9:
        raise ValueError('Four nonnegative cohort shares must sum to one')
    scalar=['dau','mau','whale_cr','global_cr','owners_small','overlap','reach_scale','behavior_penalty','product_penalty','loss_c','loss_f','income_delta','revenue_per_buyer']
    if not _finite([c[k] for k in scalar]): raise ValueError('Missing or nonfinite scenario input')
    if c['dau']<=0 or c['mau']<c['dau']: raise ValueError('Require 0 < DAU <= MAU')
    for key in ['owners_small','overlap','behavior_penalty','product_penalty','loss_c','loss_f']:
        if not 0<=c[key]<=1: raise ValueError('Probability outside [0,1]: '+key)
    if c['reach_scale']<0 or not -1<=c['income_delta']<=1 or c['revenue_per_buyer']<0: raise ValueError('Invalid reach/revenue input')
    owner=shares[0]+shares[1]+c['owners_small']*(shares[2]+shares[3])
    if c['enforce_ozon'] and not .6-1e-9<=owner<=.8+1e-9: raise ValueError('Ozon owner constraint not met')
    crs=[c['whale_cr']+g for g in inputs['case_cr_gaps']]
    if min(crs)<0 or max(crs)>1: raise ValueError('Cohort CR outside [0,1]; anchor incompatible with case gaps')
    if abs(sum(s*r for s,r in zip(shares,crs))-c['global_cr'])>1e-9: raise ValueError('CR anchors do not reconcile')
    if abs(sum(s*t[0] for s,t in zip(shares,inputs['traffic']))-inputs['case_daily_cart'])>1e-9 or abs(sum(s*t[1] for s,t in zip(shares,inputs['traffic']))-inputs['case_daily_fav'])>1e-9:
        raise ValueError('Weighted daily section visits must preserve case 65%/13% totals')
    for k,(pC,pF,_) in enumerate(inputs['traffic']):
        both=pF*c['overlap']; states=[pC-both,pF-both,both,1-pC-pF+both]
        owners=1 if k<2 else c['owners_small']
        if min(states)<-1e-12 or pF>owners+1e-12 or both>pC*owners+1e-12: raise ValueError('Infeasible daily/ownership intersections')
        weights=c.get('weights',inputs['weights'])[k]
        if len(weights)!=4 or not _finite(weights) or min(weights)<0: raise ValueError('Invalid state weights')
        norm=sum(s*v for s,v in zip(states,weights))
        if norm<=0 or crs[k]*max(weights)/norm>1+1e-12: raise ValueError('Invalid normalized state CR')
    for h in inputs['hypotheses']:
        for eC,eF,eCF in h['reach']:
            a,b,d=[x*c['reach_scale'] for x in [eC,eF,eCF]]
            if min(a,b,d)<0 or max(a,b)>1 or d<max(0,a+b-1)-1e-12 or d>min(a,b)+1e-12:
                raise ValueError('Infeasible target intersection')

def evaluate(inputs,case):
    validate(inputs,case)
    q=case['shares']; D=case['dau']; result=[]
    retention=(1-case['behavior_penalty'])*(1-case['product_penalty'])
    cart_users=D*sum(s*t[0] for s,t in zip(q,inputs['traffic']))
    fav_users=D*sum(s*t[1] for s,t in zip(q,inputs['traffic']))
    for h in inputs['hypotheses']:
        b0=b1=rev0=rev1=c0=c1=f0=f1=target=population=0.
        for k in range(4):
            pC,pF,_=inputs['traffic'][k];both=pF*case['overlap']
            states=[pC-both,pF-both,both,1-pC-pF+both]
            weights=case.get('weights',inputs['weights'])[k]
            norm=sum(s*v for s,v in zip(states,weights))
            ec,ef,inter=[v*case['reach_scale'] for v in h['reach'][k]]
            for t,(visitC,visitF) in enumerate([(1,0),(0,1),(1,1),(0,0)]):
                n=D*q[k]*states[t]
                cr=(case['whale_cr']+inputs['case_cr_gaps'][k])*weights[t]/norm
                reach=ec*visitC+ef*visitF-inter*visitC*visitF
                before=n*cr
                keep=(1-case['loss_c']*visitC)*(1-case['loss_f']*visitF)
                after=before*keep*(1+inputs['uplift']*reach*retention)
                if after < -1e-7 or after>n+1e-7: raise ValueError('Result outside unique-user probability bounds')
                b0+=before;b1+=after;population+=n;target+=n*reach
                c0+=before*visitC;c1+=after*visitC;f0+=before*visitF;f1+=after*visitF
                rev0+=before*case['revenue_per_buyer']
                rev1+=after*case['revenue_per_buyer']*(1+case['income_delta']*reach)
        guardC=c1/cart_users+1e-12>=c0/cart_users
        guardF=f1/fav_users+1e-12>=f0/fav_users
        guardR=rev1/D+1e-12>=rev0/D
        result.append(dict(scenario=case['id'],scenario_name=case['name'],kind=case['kind'],hypothesis=h['id'],name=h['name'],
            population=population,target_users=target,buyers0=b0,buyers1=b1,delta_buyers=b1-b0,cr0=b0/D,cr1=b1/D,
            delta_pp=(b1-b0)/D*100,relative_cr=(b1-b0)/b0 if b0 else None,
            cart_cr0=c0/cart_users,cart_cr1=c1/cart_users,fav_cr0=f0/fav_users,fav_cr1=f1/fav_users,
            arpu0=rev0/D,arpu1=rev1/D,arpu_index1=100*rev1/rev0 if rev0 else None,
            guard_c=guardC,guard_f=guardF,guard_arpu=guardR,
            positive_and_safe=b1>b0+1e-8 and guardC and guardF and guardR,
            ozon_calibrated=case['enforce_ozon'],effective_uplift=inputs['uplift']*retention))
    return result

def scenarios(inputs,summary_path):
    summary=load_inputs(summary_path)
    q=[x['share'] for x in summary['cohorts']]
    events_owner=summary['fav_users']/summary['users']
    small_proxy=(events_owner-q[0]-q[1])/(q[2]+q[3])
    def make(id,name,kind,shares=q,global_cr=.15,anchor=2,whale=.3,owners=None,dau=None,mau=None,**kw):
        if dau is None:dau=inputs['public_ozon']['dau_march_2026']
        if mau is None:mau=inputs['public_ozon']['mau_march_2026']
        owner=(.7-shares[0]-shares[1])/(shares[2]+shares[3]) if owners is None else owners
        gap=sum(s*g for s,g in zip(shares,inputs['case_cr_gaps']))
        if anchor==1: global_cr=whale+gap
        else: whale=global_cr-gap
        c=dict(id=id,name=name,kind=kind,shares=list(shares),global_cr=global_cr,global_cr_input=global_cr,
               whale_cr=whale,anchor=anchor,owners_small=owner,dau=dau,mau=mau,overlap=.8,reach_scale=1.,
               behavior_penalty=.25,product_penalty=.25,loss_c=0.,loss_f=0.,income_delta=0.,
               revenue_per_buyer=1.,enforce_ozon=True,threshold='P90',platform_note='No platform mix data; aggregate stress only')
        c.update(kw);return c
    cases=[]
    for k,x in enumerate(inputs['legacy_cases']):
        c=make(['legacy_low','original','legacy_high'][k],x['name'],'control',shares=x['shares'],anchor=1,whale=x['whale_cr'],
               owners=x['owners_small'],dau=100000,mau=400000,revenue_per_buyer=1000.,threshold='Ozon thresholds unknown')
        c['global_cr_input']=x['global_cr_input'];cases.append(c)
    cases.extend([
        make('taobao_external','Taobao: внешний без калибровки','external',anchor=1,owners=small_proxy,enforce_ozon=False,dau=100000,mau=400000),
        make('taobao_control_201','Taobao + контроль CR 20,1%','control',global_cr=.201,dau=100000,mau=400000),
        make('taobao_calibrated','Taobao / Ozon: базовый','base'),
        make('cautious','Осторожный','cautious',global_cr=.12,reach_scale=.6,behavior_penalty=.5,product_penalty=.5,loss_c=.001,loss_f=.002,income_delta=-.005),
        make('favorable','Благоприятный','favorable',global_cr=.18,reach_scale=1.25,behavior_penalty=0.,product_penalty=0.),
        make('zero','Нулевая польза','zero',behavior_penalty=1.),
        make('negative_cart','Ущерб CR Корзины 0,5%','negative',loss_c=.005),
        make('negative_fav','Ущерб CR Избранного 3%','negative',loss_f=.03),
        make('negative_revenue','Ущерб доходу покупателя 10%','negative',income_delta=-.10),
        make('negative_combined','Совместный негативный','negative',loss_c=.005,loss_f=.01,income_delta=-.02)])
    thresholds=summary.get('thresholds',[])
    for x in thresholds:
        if x['quantile']==.9:continue
        label='P'+str(round(x['quantile']*100))
        cases.append(make('threshold_'+label.lower(),'Пороги Taobao '+label,'threshold',shares=x['shares'],threshold=label))
    for cr in [.10,.12,.18,.201]:
        cases.append(make('cr_'+str(round(cr*1000)),'Чувствительность CR '+str(cr*100)+'%','cr',global_cr=cr))
    for overlap in [0,.5,1.]:
        cases.append(make('overlap_'+str(round(overlap*100)),'Пересечение визитов '+str(round(overlap*100))+'%','overlap',overlap=overlap))
    for scale in [.5,1.5]:
        cases.append(make('reach_'+str(scale),'Охват ×'+str(scale),'reach',reach_scale=scale))
    # Qualitative platform facts cannot identify platform weights. These are explicit stress cases.
    cases.append(make('platform_mix_stress','Сдвиг состава визитов: стресс','platform',overlap=.5,
        weights=[[1.2,.4,1.,.5] for _ in range(4)]))
    for c in cases:validate(inputs,c)
    return cases

def public_scale(inputs,cases):
    p=inputs['public_ozon'];base=next(c for c in cases if c['id']=='taobao_calibrated')
    intensity=p['q1_orders']/(p['q1_days']*p['dau_march_2026'])
    return dict(orders_per_day_q1=p['q1_orders']/p['q1_days'],orders_per_assumed_active_user_day=intensity,
        assumption='March DAU used as proxy for Q1 average; audience/product scopes may differ. Not observed unique-buyer CR or a hard bound.',
        daily_cart_scaled=p['dau_march_2026']*inputs['case_daily_cart'],daily_fav_scaled=p['dau_march_2026']*inputs['case_daily_fav'],
        monthly_cart_scaled=p['mau_march_2026']*inputs['case_monthly_cart'],monthly_fav_scaled=p['mau_march_2026']*inputs['case_monthly_fav'],
        base_global_cr_assumed=base['global_cr'],implied_orders_per_buying_user_day_at_base_cr=intensity/base['global_cr'])
