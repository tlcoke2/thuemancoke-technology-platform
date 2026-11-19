"""Validate release-bound evidence. Local records are attestations, not certificates."""
import argparse
import hashlib
import json
from pathlib import Path

ARCHIVE_SHA = 'c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059'
MANIFEST_SHA = 'cd66121ca8dfdbec30899be998cfb30d8ee13570e93cab967effcb9d83c3bf1b'
REQUIRED = {'clinical', 'regulatory', 'privacy', 'legal', 'independent_pentest', 'cloudflare', 'recovery', 'manual_acceptance', 'licence_signer'}

def assess(record, evidence_root):
    if record.get('format') != 'tec-closeout-evidence/v1':
        raise ValueError('Unsupported evidence format')
    if record.get('archiveSha256') != ARCHIVE_SHA or record.get('manifestSha256') != MANIFEST_SHA:
        raise ValueError('Evidence refers to another release')
    root = Path(evidence_root).resolve()
    seen = set()
    accepted, outstanding = [], []
    for item in record.get('decisions', []):
        key = item.get('control')
        if key not in REQUIRED or key in seen:
            raise ValueError('Unknown or duplicate control')
        seen.add(key)
        errors = []
        for field in ('reviewer', 'role', 'decidedAt', 'scope', 'limitations'):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append('Missing ' + field)
        if item.get('decision') != 'accepted':
            errors.append('No accepted decision')
        if item.get('template') is not False:
            errors.append('Template status unresolved')
        if key == 'independent_pentest' and item.get('independentOfImplementation') is not True:
            errors.append('Independent assessment not attested')
        refs = item.get('evidence', [])
        if not isinstance(refs, list) or not refs:
            errors.append('No evidence files')
            refs = []
        for ref in refs:
            try:
                if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
                    raise ValueError()
                path = (root / ref['path']).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError()
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if ref.get('sha256') != actual:
                    raise ValueError()
            except (ValueError, OSError):
                errors.append('Evidence missing, outside root or hash mismatch')
        if errors:
            outstanding.append({'control': key, 'reasons': errors})
        else:
            accepted.append(key)
    outstanding.extend({'control': key, 'reasons': ['No decision supplied']} for key in sorted(REQUIRED - seen))
    return {'acceptedAttestations': accepted, 'outstanding': outstanding,
            'allEvidencePresent': not outstanding,
            'meaning': 'Checks completeness and local hashes only; reviewer identity, qualifications and conclusions require verification. No deployment or certification is performed.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    parser.add_argument('--evidence-root', required=True, type=Path)
    args = parser.parse_args()
    result = assess(json.loads(args.record.read_text(encoding='utf-8')), args.evidence_root)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['allEvidencePresent'] else 2)
