"""Passive checks of fixed, owner-authorised production endpoints. No sign-in or mutation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

BASE='https://customers.thuemancokelimited.com'
CHECKS=(('/health','GET',200),('/ready','GET',200),('/start','GET',200),
        ('/payments','GET',200),('/help','GET',200),('/help/customer-guide.txt','GET',200),
        ('/customer/billing','GET',401),('/customer/requests/export','GET',401),
        ('/admin/software-requests','GET',401),('/admin/billing','GET',401),
        ('/api/downloads','POST',401))

def inspect(fetch):
    checks=[]
    for path,method,expected in CHECKS:
        code,headers,body=fetch(BASE+path,method)
        reasons=[]
        if code!=expected:reasons.append('Unexpected HTTP status')
        for key,value in [('cache-control','no-store'),('x-content-type-options','nosniff'),('x-frame-options','DENY')]:
            if value.lower() not in headers.get(key,'').lower():reasons.append('Missing '+key)
        csp=headers.get('content-security-policy','')
        if "frame-ancestors 'none'" not in csp or "default-src 'none'" not in csp:reasons.append('Missing restrictive CSP')
        if 'max-age=' not in headers.get('strict-transport-security',''):reasons.append('Missing HSTS')
        if code==200 and path=='/help' and 'c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059' not in body:reasons.append('Wrong help release')
        if code==200 and path=='/help/customer-guide.txt' and 'attachment;' not in headers.get('content-disposition',''):reasons.append('Guide not downloadable')
        if code==200 and path=='/payments' and 'Request a payment link' not in body:reasons.append('Missing payment request route')
        checks.append({'path':path,'method':method,'http':code,'expected':expected,'pass':not reasons,'issues':reasons})
    return {'format':'tec-passive-gateway-check/v1','checkedAtUtc':datetime.now(timezone.utc).isoformat(),
            'origin':BASE,'checks':checks,'pass':all(c['pass'] for c in checks),
            'scope':'Passive public pages, security headers and unauthenticated denial only. Not a penetration test, authenticated UAT, archive readback or clinical assessment.'}

def fetch(url,method):
    run=subprocess.run(['curl','--silent','--show-error','--max-time','20','--max-filesize','131072',
        '--request',method,'--dump-header','-',url],capture_output=True,timeout=25)
    if run.returncode:raise RuntimeError('Public endpoint request failed; no credentials used')
    raw=run.stdout.replace(b'\r\n',b'\n')
    # A proxy may prepend its CONNECT headers; retain the last HTTP response.
    parts=raw.split(b'\n\n');headers=None;body=b''
    for index,part in enumerate(parts):
        if part.startswith(b'HTTP/'):
            lines=part.decode('iso-8859-1').splitlines()
            code=int(lines[0].split()[1]);headers={}
            for line in lines[1:]:
                if ':' in line:
                    key,value=line.split(':',1);headers[key.strip().lower()]=value.strip()
            body=b'\n\n'.join(parts[index+1:])
    if headers is None:raise RuntimeError('No HTTP response headers')
    return code,headers,body.decode('utf-8',errors='replace')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,help='Create a NEW report; never overwrite an earlier record')
    args=parser.parse_args()
    try:
        report=inspect(fetch)
        rendered=json.dumps(report,indent=2)+'\n'
        if args.evidence:
            with args.evidence.open('x') as out:out.write(rendered)
        print(rendered)
        return 0 if report['pass'] else 1
    except (RuntimeError,OSError,subprocess.SubprocessError):
        print('FAIL public endpoint checks unavailable or evidence path already exists')
        return 2

if __name__=='__main__':raise SystemExit(main())
