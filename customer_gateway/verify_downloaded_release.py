"""Offline, read-only verification of a downloaded, pinned TEC EPR release.

Never accepts a signed URL or storage credentials. SHA-256 verification does not
establish the authenticity of the publisher's detached signature.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path

try:
    from .download_policy import CLINIC_1_0_0
except ImportError:
    from download_policy import CLINIC_1_0_0


CHUNK_BYTES = 1024 * 1024


def inspect_archive(path, *, release=None):
    """Stream a local archive; return reproducible, non-sensitive check evidence."""
    release = CLINIC_1_0_0 if release is None else release
    local_file = Path(path)
    if not local_file.is_file():
        raise ValueError('A readable local archive file is required (not a URL)')
    sha = hashlib.sha256()
    byte_count = 0
    with local_file.open('rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b''):
            sha.update(chunk)
            byte_count += len(chunk)
    observed = sha.hexdigest()
    same_size = byte_count == release.bytes
    same_digest = hmac.compare_digest(observed, release.sha256.lower())
    return {
        'schema': 'tcl-gateway-download-verification-v1',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'release_id': release.id,
        'file_name': local_file.name,  # Never persist the full local path.
        'observed_bytes': byte_count,
        'expected_bytes': release.bytes,
        'observed_sha256': observed,
        'expected_sha256': release.sha256,
        'size_matches': same_size,
        'sha256_matches': same_digest,
        'verified': same_size and same_digest,
        'publisher_signature_verified': False,
        'verification_scope': 'Local archive bytes and SHA-256 only; detached publisher signature requires separate verification.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Verify an existing local TEC EPR Clinic Edition 1.0.0 download.')
    parser.add_argument('--file', required=True, type=Path, help='Path to the already-downloaded local archive, not a signed URL.')
    parser.add_argument('--evidence-json', type=Path, help='Optional NEW JSON evidence file (never overwrites an existing file).')
    args = parser.parse_args(argv)
    try:
        evidence = inspect_archive(args.file)
    except (OSError, ValueError):
        print('FAIL: Cannot read a local archive. No network request or gateway modification made.')
        return 2
    if args.evidence_json is not None:
        try:
            # Exclusive creation avoids overwriting an earlier verification record.
            with args.evidence_json.open('x', encoding='utf-8') as out:
                json.dump(evidence, out, indent=2, sort_keys=True)
                out.write('\n')
        except OSError:
            print('FAIL: Evidence report must be a new, writable file; existing evidence was not overwritten.')
            return 2
    if not evidence['verified']:
        print('FAIL: Downloaded file does not match the pinned release size and SHA-256. Do not install or distribute it.')
        print('Observed SHA-256:', evidence['observed_sha256'])
        print('Observed bytes:', evidence['observed_bytes'])
        return 1
    print('PASS: Downloaded archive matches the pinned release size and SHA-256.')
    print('SHA-256:', evidence['observed_sha256'])
    print('Bytes:', evidence['observed_bytes'])
    print('PUBLISHER SIGNATURE: NOT CHECKED. Validate the detached signature using a separately trusted publisher key.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
