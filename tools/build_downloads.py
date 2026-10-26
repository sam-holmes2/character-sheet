#!/usr/bin/env python3
"""Rebuild the qualified public downloads from this release snapshot."""
from pathlib import Path
import argparse,hashlib,io,json,zipfile

def build(root,check_only=False):
    recipes=json.loads((root/'tools/download-recipes.json').read_text())
    pinsraw=(root/'release-pins.json').read_bytes()
    sha=lambda value:hashlib.sha256(value).hexdigest()
    if recipes.get('format')!='cs-public-download-recipes-v1' or sha(pinsraw)!=recipes['sourceManifestSha256']:raise RuntimeError('Release manifest differs')
    pins=json.loads(pinsraw)
    for name,pin in pins.items():
        if name in {r['path']for r in recipes['recipes']}:continue
        raw=(root/'public'/name).read_bytes()
        if len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']:raise RuntimeError('Release input differs: '+name)
    stocks=sorted(name for name in pins if name.startswith('assets/stock/'))
    result=[]
    for recipe in recipes['recipes']:
        raw=(root/'public'/recipe['base']).read_bytes()
        if sha(raw)!=recipe['baseSha256']:raise RuntimeError('App template changed')
        app=raw.decode()
        for edit in recipe['operations']:
            if not edit['before'] or app.count(edit['before'])!=1:raise RuntimeError('App export seam changed')
            app=app.replace(edit['before'],edit['after'])
        app=app.encode()
        if sha(app)!=recipe['appSha256'] or len(stocks)!=recipe['stockCount']:raise RuntimeError('Export payload differs')
        entries=[{'name':recipe['stockPrefix']+name,'source':name}for name in stocks]+recipe['extraEntries']
        output=io.BytesIO();metadata=recipe['zipEntry']
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as archive:
            for entry in sorted(entries,key=lambda e:e['name']):
                body=app if entry['source']=='@app'else(root/'public'/entry['source']).read_bytes()
                info=zipfile.ZipInfo(entry['name'],tuple(metadata['dateTime']));info.compress_type=metadata['compression'];info.create_system=metadata['system'];info.external_attr=metadata['mode'];archive.writestr(info,body)
        body=output.getvalue()
        if len(body)!=recipe['bytes']or sha(body)!=recipe['sha256']:raise RuntimeError('Download archive differs: '+recipe['path'])
        destination=root/'public'/recipe['path']
        if destination.exists()and destination.read_bytes()!=body:raise RuntimeError('Existing different download retained: '+recipe['path'])
        if not check_only and not destination.exists():destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(body)
        result.append({'path':recipe['path'],'sha256':sha(body),'bytes':len(body)})
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');args=parser.parse_args();print(json.dumps(build(Path(__file__).resolve().parents[1],args.check_only),indent=2))
