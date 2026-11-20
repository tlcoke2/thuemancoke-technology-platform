"""Read selected Cloudflare zone settings. Never modifies account configuration.
Token is prompted without echo. Reports contain configuration, never credentials.
"""
import argparse
import getpass
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def collect(zone, token):
    if not re.fullmatch(r'[a-f0-9]{32}', zone):
        raise ValueError('Expected a Cloudflare zone ID')
    opener = urllib.request.build_opener(NoRedirect)
    output = {'format':'tec-cloudflare-readback/v1','collectedAt':datetime.now(timezone.utc).isoformat(),'zoneId':zone,'checks':{},'effectiveBlockingVerified':False,'alertDeliveryVerified':False}
    targets = {'zone':'', 'ssl':'/settings/ssl', 'minimum_tls':'/settings/min_tls_version', 'always_https':'/settings/always_use_https', 'browser_check':'/settings/browser_check', 'rulesets':'/rulesets'}
    for name, suffix in targets.items():
        request = urllib.request.Request('https://api.cloudflare.com/client/v4/zones/'+zone+suffix, headers={'Authorization':'Bearer '+token,'Accept':'application/json'}, method='GET')
        try:
            with opener.open(request, timeout=20) as response:
                raw = response.read(2_000_001)
            if len(raw)>2_000_000:
                raise ValueError('Response too large')
            data = json.loads(raw)
            if data.get('success') is not True:
                raise ValueError('API did not confirm success')
            result = data.get('result')
            if name == 'zone':
                result={k: result.get(k) for k in ('id','name','status','paused')}
            elif name == 'rulesets':
                result=[{k:r.get(k) for k in ('id','name','kind','phase','version')} for r in result]
            else:
                result={k:result.get(k) for k in ('id','value','editable','modified_on')}
            output['checks'][name]={'status':'observed','result':result}
        except urllib.error.HTTPError as error:
            output['checks'][name]={'status':'unverified','httpStatus':error.code}
        except (OSError, ValueError, TypeError, AttributeError):
            output['checks'][name]={'status':'unverified','reason':'Read failed; no provider response body or credential recorded'}
    output['allReadsSucceeded']=all(x['status']=='observed' for x in output['checks'].values())
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zone', required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new evidence output path')
    result=collect(args.zone,getpass.getpass('Cloudflare read-only API token: '))
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print('Readback saved. WAF rule detail, bot effectiveness, origin protection and alert delivery still require operator verification.')
    raise SystemExit(0 if result['allReadsSucceeded'] else 2)
