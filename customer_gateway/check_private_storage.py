"""Operator-only staging HEAD check; never signs a URL or changes cloud state."""
import os
try:
    from .downloads import R2Signer
except ImportError:
    from downloads import R2Signer


def check(environ, signer_factory=R2Signer):
    if environ.get('APP_ENV') != 'staging':
        raise ValueError('Staging required')
    for flag in ('GATEWAY_DOWNLOADS_ENABLED', 'GATEWAY_RELEASE_APPROVED'):
        if environ.get(flag, '').lower() not in ('', 'false'):
            raise ValueError('Download and release controls must remain disabled')
    key=environ.get('R2_ACCESS_KEY_ID', '')
    secret=environ.get('R2_SECRET_ACCESS_KEY', '')
    if not key.strip() or not secret.strip():
        raise ValueError('Private R2 credentials are missing')
    signer_factory(key,secret).check()


def main():
    try:
        check(os.environ)
    except Exception:
        raise SystemExit('FAIL: Check staging, disabled download/release flags, bucket-scoped read credentials and pinned object metadata. No URL generated; no credentials displayed.') from None
    print('PASS: Private R2 HEAD check matches the recorded release size and ETag.')
    print('No download link generated; no database, object or permission changes made.')
    print('This does not prove credential scope, bucket privacy or cryptographic integrity; retain the separate verification evidence.')


if __name__ == '__main__':
    main()
