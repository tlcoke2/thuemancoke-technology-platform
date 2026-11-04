"""Offline end-to-end provenance check for the *downloaded* TEC EPR 1.0.0 tar.gz.

Read-only: checks the pinned archive bytes, independently verifies the detached
publisher-signed manifest, and streams every declared payload member from the
archive without extracting files. No private keys, network access, or DB writes.

A separately approved entitlement/revocation test remains necessary.
"""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import re
import tarfile

try:
    from .download_policy import CLINIC_1_0_0
    from .verify_release_manifest import verify_manifest, VerificationError
    from .verify_downloaded_release import inspect_archive, CHUNK_BYTES
except ImportError:
    from download_policy import CLINIC_1_0_0
    from verify_release_manifest import verify_manifest, VerificationError
    from verify_downloaded_release import inspect_archive, CHUNK_BYTES


# Previously independently observed, correctly signed 1.0.0 manifest bytes.
PINNED_SIGNED_MANIFEST_SHA256 = '1b05f4adc8e2e78ed11a4de89b00fce33392fa048c9410fc8b77818bb5f6f275'
RELEASE_STATUS = 'APPROVED CLINICAL RELEASE 1.0.0'
CONTROL_FILES = {'manifest.json', 'manifest.sig', 'manifest.signer.json'}


def _safe_name(value):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise VerificationError('Unsafe or missing archive/manifest pathname')
    while value.startswith('./'):
        value = value[2:]
    if not value or value.startswith('/') or ':' in value or any(
            part in ('', '.', '..') for part in value.split('/')):
        raise VerificationError('Unsafe archive/manifest pathname')
    return value


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError('Duplicate JSON member in signed manifest')
        result[key] = value
    return result


def _manifest_records(path, expected_manifest_sha):
    manifest_bytes = Path(path).read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if not hmac.compare_digest(manifest_hash, expected_manifest_sha):
        raise VerificationError('Signed manifest bytes differ from the pinned release manifest')
    try:
        manifest = json.loads(manifest_bytes, object_pairs_hook=_no_duplicate_keys)
    except (UnicodeError, ValueError):
        raise VerificationError('Signed manifest cannot be parsed as JSON') from None
    if not isinstance(manifest, dict) or (manifest.get('releaseVersion') != '1.0.0'
            or manifest.get('status') != RELEASE_STATUS):
        raise VerificationError('Unexpected signed manifest release version or approval status')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise VerificationError('Signed manifest has no file records')
    records = {}
    for name, info in files.items():
        checked = _safe_name(name)
        if name != checked or checked in CONTROL_FILES or checked in records:
            raise VerificationError('Unexpected or duplicate manifest file name')
        if (not isinstance(info, dict) or
                not isinstance(info.get('sha256'), str) or
                not re.fullmatch(r'[a-f0-9]{64}', info['sha256']) or
                type(info.get('bytes')) is not int or info['bytes'] < 0):
            raise VerificationError('Incomplete or invalid signed file metadata')
        records[checked] = (info['sha256'], info['bytes'])
    return manifest_hash, records


def verify_release_payload(release_dir, public_key, archive, *, archive_prefix='',
                           release=None, expected_manifest_sha=None,
                           expected_fingerprint=None, expected_sig_bytes=512,
                           openssl=None):
    """Verify all signed file records against the pinned, downloaded tarball.

    Alternate expected values are test-fixture injection only; production CLI
    always uses the recorded Clinic 1.0.0 constants and RSA-4096 settings.
    """
    release = CLINIC_1_0_0 if release is None else release
    expected_manifest_sha = expected_manifest_sha or PINNED_SIGNED_MANIFEST_SHA256
    if not re.fullmatch(r'[a-f0-9]{64}', expected_manifest_sha):
        raise VerificationError('Invalid expected manifest digest')
    if archive_prefix:
        prefix = _safe_name(archive_prefix.rstrip('/'))
        if prefix != archive_prefix.rstrip('/'):
            raise VerificationError('Noncanonical archive prefix')
    else:
        prefix = ''
    # Trust anchor first: verify detached signature and pinned public-key SPKI.
    signature = verify_manifest(
        release_dir, public_key, expected_fingerprint=expected_fingerprint,
        expected_sig_bytes=expected_sig_bytes, openssl=openssl)
    manifest_hash, records = _manifest_records(
        Path(release_dir) / 'manifest.json', expected_manifest_sha)
    if not hmac.compare_digest(signature['manifest_sha256'], manifest_hash):
        raise VerificationError('Signature was checked against different manifest bytes')

    # SHA256 of the *outer* downloaded distribution, not just tar entry digests.
    archive_result = inspect_archive(archive, release=release)
    if not archive_result['verified']:
        raise VerificationError('Downloaded archive differs from pinned size/SHA-256')
    expected_control = {
        filename: (Path(release_dir) / filename).read_bytes()
        for filename in CONTROL_FILES
    }
    observed = set()
    controls_seen = set()
    try:
        with tarfile.open(archive, mode='r:gz') as tf:
            for member in tf:
                name = member.name
                while name.startswith('./'):
                    name = name[2:]
                if name in ('', '.'):
                    if not member.isdir():
                        raise VerificationError('Invalid root tar member')
                    continue
                checked = _safe_name(name.rstrip('/') if member.isdir() else name)
                if prefix:
                    if checked == prefix and member.isdir():
                        continue
                    if not checked.startswith(prefix + '/'):
                        raise VerificationError('Archive contains entries outside declared prefix')
                    checked = checked[len(prefix) + 1:]
                    if not checked:
                        continue
                    checked = _safe_name(checked)
                if member.isdir():
                    continue
                if not member.isfile():
                    raise VerificationError('Archive contains a link or unsupported member type')
                if checked in observed or checked in controls_seen:
                    raise VerificationError('Duplicate file path in distribution archive')
                if checked in records:
                    digest, expected_size = records[checked]
                    if member.size != expected_size:
                        raise VerificationError('Archive member size differs from signed manifest')
                elif checked in CONTROL_FILES:
                    expected_size = len(expected_control[checked])
                    digest = hashlib.sha256(expected_control[checked]).hexdigest()
                    if member.size != expected_size:
                        raise VerificationError('Bundled signing metadata differs from verified copy')
                else:
                    raise VerificationError('Unexpected unsigned file present in archive')
                stream = tf.extractfile(member)
                if stream is None:
                    raise VerificationError('Unable to read regular file from archive')
                sha = hashlib.sha256()
                size = 0
                with stream:
                    for block in iter(lambda: stream.read(CHUNK_BYTES), b''):
                        sha.update(block)
                        size += len(block)
                if size != expected_size or not hmac.compare_digest(sha.hexdigest(), digest):
                    raise VerificationError('Archive member content differs from signed manifest')
                if checked in records:
                    observed.add(checked)
                else:
                    controls_seen.add(checked)
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise VerificationError('Unable to read the downloaded tar.gz payload safely') from None
    missing = set(records) - observed
    if missing:
        raise VerificationError('Archive is missing one or more signed manifest files')
    return {
        'result': 'PASS',
        'release_id': release.id,
        'signed_manifest_sha256': manifest_hash,
        'publisher_spki_sha256': signature['publisher_spki_sha256'],
        'archive_sha256': archive_result['observed_sha256'],
        'archive_bytes': archive_result['observed_bytes'],
        'manifest_files_verified': len(observed),
        'bundled_signing_metadata_files_verified': len(controls_seen),
        'archive_prefix': prefix,
        'all_declared_payload_files_matched': True,
        'independent_publisher_manifest_signature_verified': True,
        'local_revocation_tested': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Offline verification of customer-downloaded TEC EPR 1.0.0 tar.gz and signed manifest.')
    parser.add_argument('--release-dir', type=Path, required=True,
                        help='Existing signed release directory containing manifest/signature metadata.')
    parser.add_argument('--public-key', type=Path, required=True,
                        help='Trusted TEC EPR publisher PUBLIC key, never a private key.')
    parser.add_argument('--archive', type=Path, required=True,
                        help='Existing customer-downloaded tar.gz archive.')
    parser.add_argument('--archive-prefix', default='',
                        help='Optional explicit top-level tar folder name; default requires root-relative layout.')
    parser.add_argument('--evidence-json', type=Path,
                        help='Optional NEW local JSON evidence file; existing files are not overwritten.')
    args = parser.parse_args(argv)
    try:
        evidence = verify_release_payload(
            args.release_dir, args.public_key, args.archive,
            archive_prefix=args.archive_prefix)
        if args.evidence_json is not None:
            with args.evidence_json.open('x', encoding='utf-8') as output:
                json.dump(evidence, output, sort_keys=True, indent=2)
                output.write('\n')
    except (VerificationError, OSError, ValueError) as error:
        print('FAIL:', str(error))
        print('No release files, clinical databases or permissions were modified.')
        return 1
    print('PASS: Pinned publisher public key and detached RSA-SHA256 manifest signature verified.')
    print('PASS: Downloaded archive SHA-256 and byte count match the recorded release.')
    print('PASS: Every declared signed manifest file matched archived content and size.')
    print('Manifest files verified:', evidence['manifest_files_verified'])
    print('Bundled signing metadata verified:', evidence['bundled_signing_metadata_files_verified'])
    print('SIGNED RELEASE INTEGRITY: PASS. Licence and live entitlement revocation are separate gates.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
