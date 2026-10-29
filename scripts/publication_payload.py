"""Read verified repository files for connected GitHub blob publication.

Does not access credentials or send network requests. --manifest lists explicit
project directories and excludes temporary files, user aggregates and caches.
"""
import base64,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIRECTORIES=['data','docs','models','notebooks','results','scripts','src','tests','.github']
ROOT_FILES=['README.md','requirements.txt','.gitignore']
def files():
    result=[ROOT/x for x in ROOT_FILES]
    for directory in DIRECTORIES:
        result.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and
                      p.suffix not in ['.pyc','.png'] and '.inspect.' not in p.name and p.name not in ['publication_manifest.json','publication_remote.json'])
    return sorted(result,key=lambda p:p.relative_to(ROOT).as_posix())
if sys.argv[1]=='--manifest':
    rows=[]
    for p in files():
        b=p.read_bytes();rel=p.relative_to(ROOT).as_posix()
        if rel.endswith('taobao_users.csv') or rel.endswith('.zip'):raise ValueError('Raw data must not be published')
        rows.append(dict(path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),git_blob_sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),base64_length=4*((len(b)+2)//3)))
    print(json.dumps(rows,ensure_ascii=False))
else:
    p=(ROOT/sys.argv[1]).resolve()
    if p not in files() or not p.is_relative_to(ROOT):raise ValueError('File not approved for publication')
    print(base64.b64encode(p.read_bytes()).decode('ascii'))
