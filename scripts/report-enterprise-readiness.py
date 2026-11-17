"""Read-only evidence report; never certifies a product or changes deployment flags."""
import json
from pathlib import Path

def assess(data):
    if data.get('format') != 'tec-enterprise-readiness/v1':
        raise ValueError('Unknown readiness record')
    controls=data.get('controls')
    if not isinstance(controls,list) or not controls:
        raise ValueError('Control inventory required')
    seen=set()
    implemented=[]
    outstanding=[]
    allowed={'implemented','owner_reported','open','owner_review','external_review','deployment_review'}
    for item in controls:
        key=item.get('id')
        if not isinstance(key,str) or not key or key in seen:
            raise ValueError('Unique control identifiers required')
        seen.add(key)
        if item.get('status') not in allowed or not isinstance(item.get('evidence'),list) or not item.get('scope'):
            raise ValueError('Control status, evidence list and scope required')
        if item['status']=='implemented':
            if not item['evidence'] or any(not isinstance(e,str) or not e.strip() for e in item['evidence']):
                raise ValueError('Implemented control requires evidence')
            implemented.append(key)
        else:
            outstanding.append({'id':key,'status':item['status'],'scope':item['scope']})
    return {'implementedControls':implemented,'outstandingControls':outstanding,
            'unattendedCommercialisationReady':False,
            'regulatoryCertification':'Not established by this engineering evidence report'}

if __name__=='__main__':
    source=Path(__file__).resolve().parents[1]/'docs/assurance/enterprise-readiness.json'
    print(json.dumps(assess(json.loads(source.read_text())),indent=2))
