"""Read-only verification of the detached TEC EPR Clinic Edition 1.0.0 manifest.

This tool NEVER writes to release files, exports private keys, makes network
requests, or modifies the clinical master. Requires a locally installed OpenSSL.

Security boundaries: the public key MUST match the previously authenticated
publisher SPKI fingerprint pinned in download_policy.py. Signer metadata alone
is not trusted to establish the publisher's identity. Manifest signature
validation alone does not prove the archive is listed inside the manifest.
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

try:
    from .download_policy import CLINIC_1_0_0
except ImportError:
    from download_policy import CLINIC_1_0_0


class VerificationError(Exception):
    """A release-verification precondition or cryptographic check failed."""


def find_openssl():
    # Prefer a command already on PATH; Git for Windows also bundles OpenSSL.
    candidates = [shutil.which('openssl')]
    for root in (os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')):
        if root:
            candidates.extend([
                os.path.join(root, 'Git', 'usr', 'bin', 'openssl.exe'),
                os.path.join(root, 'Git', 'mingw64', 'bin', 'openssl.exe'),
            ])
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise VerificationError('OpenSSL unavailable. Install a trusted OpenSSL or use a trusted Git-for-Windows copy.')


def _run(openssl, args, *, timeout=20):
    try:
        proc = subprocess.run([openssl, *args], check=False, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise VerificationError('OpenSSL could not complete the local cryptographic check') from None
    if proc.returncode:
        # Never echo raw crypto-tool error output: it may contain sensitive paths.
        raise VerificationError('OpenSSL rejected the key or manifest signature')
    return proc.stdout


def verify_manifest(release_dir, public_key, *, expected_fingerprint=None,
                    expected_version='1.0.0', expected_sig_bytes=512, openssl=None):
    """Verify signer metadata, pinned public SPKI and signature over exact manifest bytes.

    Override arguments exist for synthetic tests; the CLI pins production values.
    Returns evidence only after completing ALL checks; never verifies installer content.
    """
    release_dir = Path(release_dir)
    public_key = Path(public_key)
    manifest = release_dir / 'manifest.json'
    signer_file = release_dir / 'manifest.signer.json'
    signature_file = release_dir / 'manifest.sig'
    for candidate in (manifest, signer_file, signature_file, public_key):
        if not candidate.is_file():
            raise VerificationError('Required manifest, signature, signer metadata or public key not found')
    expected = (expected_fingerprint or CLINIC_1_0_0.publisher_spki_sha256).lower()
    if not re.fullmatch('[a-f0-9]{64}', expected):
        raise VerificationError('Invalid trusted publisher fingerprint')
    try:
        signer = json.loads(signer_file.read_text(encoding='utf-8'))
    except (UnicodeError, ValueError):
        raise VerificationError('Signer metadata is not valid JSON') from None
    if (not isinstance(signer, dict) or
            signer.get('kind') != 'TEC EPR clinical distribution release manifest' or
            signer.get('algorithm') != 'RSA-SHA256' or
            signer.get('releaseVersion') != expected_version):
        raise VerificationError('Unrecognised manifest signature algorithm or release version')
    recorded = signer.get('publicKeySpkiSha256', '')
    if not isinstance(recorded, str) or recorded.lower() != expected:
        raise VerificationError('Signer metadata fingerprint differs from the trusted publisher fingerprint')
    openssl = openssl or find_openssl()
    # -pubin requires a public key. -pubout -outform DER exports SubjectPublicKeyInfo,
    # not the PKCS#1 raw public key, so SHA-256 must match the pinned SPKI fingerprint.
    spki_der = _run(openssl, ['pkey', '-pubin', '-in', str(public_key), '-pubout', '-outform', 'DER'])
    key_fingerprint = hashlib.sha256(spki_der).hexdigest()
    if key_fingerprint != expected:
        raise VerificationError('PUBLIC KEY MISMATCH: this key is not the trusted TEC EPR release signer')
    try:
        encoded = b''.join(signature_file.read_bytes().split())
        sig_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise VerificationError('Detached signature is not valid base64') from None
    if len(sig_bytes) != expected_sig_bytes:
        raise VerificationError('Detached signature length does not match the expected RSA key size')
    manifest_bytes = manifest.read_bytes()
    with TemporaryDirectory(prefix='tec-epr-manifest-check-') as temp:
        signature_bin = Path(temp) / 'detached-signature.bin'
        manifest_copy = Path(temp) / 'manifest-copy.json'
        signature_bin.write_bytes(sig_bytes)
        manifest_copy.write_bytes(manifest_bytes)
        # RSA-SHA256 PKCS#1 v1.5: the manifest is the SIGNED PAYLOAD, not the
        # archive. If the publisher used PSS, verify using its documented mode.
        _run(openssl, ['dgst', '-sha256', '-verify', str(public_key),
                       '-sigopt', 'rsa_padding_mode:pkcs1', '-signature',
                       str(signature_bin), str(manifest_copy)])
    return {
        'result': 'PASS',
        'signature_algorithm': 'RSA-SHA256 / PKCS#1 v1.5',
        'release_version': expected_version,
        'publisher_spki_sha256': key_fingerprint,
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'detached_signature_bytes': len(sig_bytes),
        'archive_manifest_binding_checked': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Verify an existing signed TEC EPR 1.0.0 manifest (read-only).')
    parser.add_argument('--release-dir', required=True, type=Path, help='Directory with manifest.json, manifest.sig, manifest.signer.json')
    parser.add_argument('--public-key', required=True, type=Path, help='Trusted publisher PUBLIC key only, in PEM format')
    args = parser.parse_args(argv)
    try:
        result = verify_manifest(args.release_dir, args.public_key)
    except (VerificationError, OSError) as error:
        print('FAIL:', error)
        print('No release files or databases were changed. Do not claim publisher verification.')
        return 1
    print('PASS: Exact manifest bytes verified against the detached RSA-SHA256 publisher signature.')
    print('PASS: Public-key SPKI SHA-256 matches the independently recorded publisher fingerprint.')
    print('Publisher SPKI SHA-256:', result['publisher_spki_sha256'])
    print('Manifest SHA-256:', result['manifest_sha256'])
    print('Signature bytes:', result['detached_signature_bytes'])
    print('ARCHIVE BINDING: NOT YET CHECKED. Inspect signed manifest entries separately.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
