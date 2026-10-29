"""Reproducible aggregation of unique additions, not list stock or daily section visits."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib,math
import json
import sqlite3
import zipfile
import pandas as pd

def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def read_users(path):
    d=pd.read_csv(path,dtype={'user_id':'int64','cart_count':'int64','fav_count':'int64'})
    required=['user_id','cart_count','fav_count','purchased']
    if list(d.columns)!=required or d.isna().any().any():raise ValueError('Invalid user aggregate schema/missing values')
    if d.user_id.duplicated().any() or (d[['cart_count','fav_count']]<0).any().any():raise ValueError('Duplicate user or negative count')
    if d.purchased.dtype!=bool:
        mapping={'true':True,'false':False,'1':True,'0':False}
        b=d.purchased.astype(str).str.lower().map(mapping)
        if b.isna().any():raise ValueError('Invalid purchased boolean')
        d['purchased']=b.astype(bool)
    return d

def summarize(path):
    d=read_users(path);n=len(d)
    if not n:raise ValueError('Empty aggregate')
    thresholds=[]
    for p in [.75,.9,.95,.99]:
        # Counts are discrete: count >= interpolated percentile means >= ceil(q).
        ct=math.ceil(d.cart_count.quantile(p));ft=math.ceil(d.fav_count.quantile(p))
        masks=[(d.cart_count<ct)&(d.fav_count>=ft),(d.cart_count>=ct)&(d.fav_count>=ft),
               (d.cart_count>=ct)&(d.fav_count<ft),(d.cart_count<ct)&(d.fav_count<ft)]
        rows=[dict(id=f'S{k+1}',users=int(m.sum()),share=float(m.mean()),buyers=int(d.loc[m,'purchased'].sum()),
                   purchase_rate=float(d.loc[m,'purchased'].mean()) if m.any() else None) for k,m in enumerate(masks)]
        thresholds.append(dict(quantile=p,cart_threshold=ct,fav_threshold=ft,shares=[r['share'] for r in rows],cohorts=rows))
    return dict(schema_version=1,origin='Provided existing user aggregate; raw archive not rerun in this publication',
        file_sha256=sha256_file(path),users=n,
        cart_users=int((d.cart_count>0).sum()),fav_users=int((d.fav_count>0).sum()),
        both_users=int(((d.cart_count>0)&(d.fav_count>0)).sum()),buyers=int(d.purchased.sum()),
        means={c:float(d[c].mean()) for c in ['cart_count','fav_count']},
        quantiles={c:{str(p):float(d[c].quantile(p)) for p in [.5,.75,.9,.95,.99]} for c in ['cart_count','fav_count']},
        cohorts=next(t['cohorts'] for t in thresholds if t['quantile']==.9),thresholds=thresholds,
        limitations=['Unique additions over source window, not list stock','Purchased is any buy in same window, not necessarily after cart/fav',
                      'No daily DAU/CR or purchase-lag estimates can be recovered from this aggregate'])

def aggregate_events(archive,output,chunksize=500000):
    """Deduplicate across chunks using SQLite; bounded memory; no archive extraction.

    Retain all source events to reproduce the original notebook. Record timestamps
    and expected-window outliers instead of silently applying a new time filter.
    """
    archive=Path(archive);output=Path(output);total=outside=0;tmin=tmax=None
    start=int(pd.Timestamp('2017-11-25',tz='Asia/Shanghai').timestamp())
    end=int(pd.Timestamp('2017-12-04',tz='Asia/Shanghai').timestamp())
    with TemporaryDirectory(prefix='taobao_') as temp,zipfile.ZipFile(archive) as z:
        matches=[x for x in z.namelist() if Path(x).name=='UserBehavior.csv']
        if len(matches)!=1:raise ValueError('Archive must contain one UserBehavior.csv')
        db=sqlite3.connect(str(Path(temp)/'distinct.sqlite'))
        try:
            db.executescript('CREATE TABLE users(user_id INTEGER PRIMARY KEY, purchased INTEGER NOT NULL DEFAULT 0); CREATE TABLE additions(behavior TEXT,user_id INTEGER,item_id INTEGER,PRIMARY KEY(behavior,user_id,item_id)) WITHOUT ROWID;')
            with z.open(matches[0]) as stream:
                for c in pd.read_csv(stream,header=None,names=['user_id','item_id','category_id','behavior','timestamp'],chunksize=chunksize):
                    if c.isna().any().any() or not c.behavior.isin(['pv','cart','fav','buy']).all():raise ValueError('Invalid source event')
                    stamps=pd.to_numeric(c.timestamp,errors='raise')
                    total+=len(c);outside+=int(((stamps<start)|(stamps>=end)).sum())
                    tmin=int(stamps.min()) if tmin is None else min(tmin,int(stamps.min()))
                    tmax=int(stamps.max()) if tmax is None else max(tmax,int(stamps.max()))
                    db.executemany('INSERT OR IGNORE INTO users(user_id) VALUES (?)',[(int(u),) for u in c.user_id.unique()])
                    db.executemany('UPDATE users SET purchased=1 WHERE user_id=?',[(int(u),) for u in c.loc[c.behavior=='buy','user_id'].unique()])
                    additions=c.loc[c.behavior.isin(['cart','fav']),['behavior','user_id','item_id']].drop_duplicates()
                    db.executemany('INSERT OR IGNORE INTO additions VALUES(?,?,?)',[(b,int(u),int(i)) for b,u,i in additions.itertuples(index=False,name=None)])
                    db.commit()
            query="""SELECT u.user_id, COALESCE(c.n,0) AS cart_count, COALESCE(f.n,0) AS fav_count, u.purchased
                FROM users u LEFT JOIN (SELECT user_id,COUNT(*) n FROM additions WHERE behavior='cart' GROUP BY user_id) c ON c.user_id=u.user_id
                LEFT JOIN (SELECT user_id,COUNT(*) n FROM additions WHERE behavior='fav' GROUP BY user_id) f ON f.user_id=u.user_id ORDER BY u.user_id"""
            output.parent.mkdir(parents=True,exist_ok=True)
            first=True
            for block in pd.read_sql_query(query,db,chunksize=chunksize):
                block['purchased']=block.purchased.astype(bool)
                block.to_csv(output,index=False,mode='w' if first else 'a',header=first)
                first=False
            if first:raise ValueError('Empty event archive')
        finally:db.close()
    metadata=dict(events=total,timestamp_min=tmin,timestamp_max=tmax,expected_timezone='Asia/Shanghai',
                  expected_start='2017-11-25',expected_end_exclusive='2017-12-04',outside_expected_window=outside,
                  time_filter_applied=False,archive_sha256=sha256_file(archive))
    output.with_suffix('.metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return metadata
