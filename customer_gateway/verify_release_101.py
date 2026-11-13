"""Read-only review of a NEW, offline RSA-4096 signed Clinic Edition 1.0.1 archive.

This does not add 1.0.1 to the production download allowlist. The existing
1.0.0 release remains blocked and immutable. Requires an independently trusted
publisher public key and the owner-reviewed, locally supplied release evidence.
It never accesses R2, Railway, customer records, clinical data or private keys.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    from .download_policy import Release, CLINIC_1_0_0, PUBLISHER_101_SPKI_SHA256
    from .verify_release_payload import verify_release_payload, VerificationError
except ImportError:
    from download_policy import Release, CLINIC_1_0_0, PUBLISHER_101_SPKI_SHA256
    from verify_release_payload import verify_release_payload, VerificationError

VERSION='1.0.1'
APPROVED='APPROVED CLINICAL RELEASE 1.0.1'
GATES=('medicalDirector','security','existingCustomerUpgrade','offHostDR','publisher','gateway')
SHA256=re.compile(r'^[0-9a-f]{64}$')
COMMIT=re.compile(r'^[0-9a-f]{40}$')


def _object_without_duplicates(pairs):
    value={}
    for key,item in pairs:
        if key in value:
            raise VerificationError('Duplicate signed metadata key')
        value[key]=item
    return value


def _json_file(path):
    try:
        return json.loads(Path(path).read_bytes(),object_pairs_hook=_object_without_duplicates)
    except (ValueError,UnicodeError,TypeError):
        raise VerificationError('Invalid release metadata JSON') from None


def review_new_release(release_dir, public_key, archive, evidence_file,
                       *, expected_fingerprint=None, expected_sig_bytes=512):
    """Authenticates archive and all signed members; NO customer grant is created.

    Verification of a publisher-signed manifest proves integrity/authenticity,
    not that the stated human approvals actually happened. Those must be
    independently reviewed before pinning a release in the production gateway.
    """
    evidence=_json_file(evidence_file)
    trusted=PUBLISHER_101_SPKI_SHA256
    if expected_fingerprint is not None:
        trusted=expected_fingerprint  # Synthetic unit fixture only; CLI never exposes.
    if (not SHA256.fullmatch(trusted) or not isinstance(evidence,dict) or
        evidence.get('status')!='SIGNED_PENDING_COMMERCIAL_GATEWAY_APPROVAL' or
        evidence.get('releaseVersion')!=VERSION or
        evidence.get('releaseScope')!='FRESH_INSTALLATIONS_ONLY' or
        evidence.get('upgradeSupported') is not False or
        evidence.get('gatewayActivated') is not False or
        evidence.get('publisherSpkiSha256')!=trusted or
        evidence.get('previousPublisherSpkiSha256')!=CLINIC_1_0_0.publisher_spki_sha256 or
        not SHA256.fullmatch(str(evidence.get('publisherTrustRotationApprovalSha256',''))) or
        not SHA256.fullmatch(str(evidence.get('archiveSha256',''))) or
        not SHA256.fullmatch(str(evidence.get('signedManifestSha256',''))) or
        type(evidence.get('archiveBytes')) is not int or evidence['archiveBytes']<10000):
        raise VerificationError('Unsigned, unpinned or unsupported 1.0.1 release metadata')
    if (evidence.get('archiveFilename')!=Path(archive).name or
        not evidence['archiveFilename'].startswith('TEC-EPR-Clinic-Edition-1.0.1-') or
        not evidence['archiveFilename'].endswith('.tar.gz')):
        raise VerificationError('Release filename differs from owner review evidence')
    source=evidence.get('source')
    if (not isinstance(source,dict) or
        not COMMIT.fullmatch(str(source.get('backendRevision',''))) or
        not COMMIT.fullmatch(str(source.get('frontendRevision','')))):
        raise VerificationError('Missing exact reviewed backend and private frontend source identities')
    release=Release(
        id='tec-epr-clinic-1.0.1',
        bucket='tec-epr-private-releases',
        object_key='tec-epr/clinic-edition/1.0.1/'+evidence['archiveFilename'],
        sha256=evidence['archiveSha256'],
        bytes=evidence['archiveBytes'],
        publisher_spki_sha256=trusted,
    )
    # This method independently checks the trusted publisher public key,
    # detached RSA signature, pinned manifest bytes, every tar member,
    # archive SHA/byte count and absence of unsigned/symlink entries.
    check=verify_release_payload(
        release_dir,public_key,archive,release=release,
        expected_manifest_sha=evidence['signedManifestSha256'],
        expected_fingerprint=trusted,expected_sig_bytes=expected_sig_bytes,
        expected_version=VERSION,expected_status=APPROVED)
    manifest=_json_file(Path(release_dir)/'manifest.json')
    if (manifest.get('releaseVersion')!=VERSION or
        manifest.get('releaseScope')!='FRESH_INSTALLATIONS_ONLY' or
        manifest.get('upgradeSupported') is not False or
        manifest.get('status')!=APPROVED or
        manifest.get('targetReleaseVersion')!=VERSION or
        manifest.get('source')!=source or
        manifest.get('approvalEvidenceSha256')!=evidence.get('approvalEvidenceSha256') or
        manifest.get('scanEvidenceSha256')!=evidence.get('scanEvidenceSha256') or
        manifest.get('publisherSpkiSha256')!=trusted or
        manifest.get('previousPublisherSpkiSha256')!=CLINIC_1_0_0.publisher_spki_sha256 or
        manifest.get('publisherTrustRotationApprovalSha256')!=evidence.get('publisherTrustRotationApprovalSha256') or
        not SHA256.fullmatch(str(manifest.get('scanEvidenceSha256',''))) or
        manifest.get('reviewedImageIds')!=evidence.get('imageIds') or
        not isinstance(manifest.get('reviewedImageIds'),dict) or
        any(not re.fullmatch(r'sha256:[a-f0-9]{64}',
                str(manifest['reviewedImageIds'].get(k,'')))
            for k in ('backend','frontend','database')) or
        not SHA256.fullmatch(str(manifest.get('candidateManifestSha256',''))) or
        not SHA256.fullmatch(str(evidence.get('approvalEvidenceSha256',''))) or
        not isinstance(manifest.get('offline'),dict) or
        not all(x in manifest.get('files',{}) for x in ('images.tar','compose.images.yaml'))):
        raise VerificationError('Signed 1.0.1 customer source, approval or offline image manifest drift')
    refs=manifest.get('approvalReferences')
    if (not isinstance(refs,dict) or
        any(not isinstance(refs.get(k),str) or len(refs[k].strip())<6
            for k in GATES)):
        raise VerificationError('Commercial and clinical approval references are incomplete')
    return {
        'assessment':'VERIFIED_1_0_1_ARCHIVE_PENDING_HUMAN_GATEWAY_APPROVAL',
        'releaseVersion':VERSION,
        'releaseScope':'FRESH_INSTALLATIONS_ONLY',
        'upgradeSupported':False,
        'candidateManifestSha256':manifest['candidateManifestSha256'],
        'releaseId':release.id,
        'verifiedArchiveSha256':check['archive_sha256'],
        'archiveBytes':evidence['archiveBytes'],
        'signedManifestSha256':evidence['signedManifestSha256'],
        'publisherSpkiSha256':trusted,
        'previousPublisherSpkiSha256':CLINIC_1_0_0.publisher_spki_sha256,
        'publisherTrustRotationApprovalSha256':evidence['publisherTrustRotationApprovalSha256'],
        'scanEvidenceSha256':manifest['scanEvidenceSha256'],
        'reviewedImageIds':manifest['reviewedImageIds'],
        'backendRevision':source['backendRevision'],
        'frontendRevision':source['frontendRevision'],
        'allArchiveMembersVerified':check['all_declared_payload_files_matched'],
        'publisherSignatureVerified':check['independent_publisher_manifest_signature_verified'],
        'releaseGrantIssued':False,
        'customerLicenseIssued':False,
        'downloadsEnabled':False,
        'commercialReleaseApproved':False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only detached publisher signature and full 1.0.1 archive verification. Does not publish.')
    parser.add_argument('--release-dir',required=True,type=Path)
    parser.add_argument('--public-key',required=True,type=Path)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--release-evidence',required=True,type=Path)
    parser.add_argument('--report-json',type=Path)
    args=parser.parse_args(argv)
    try:
        result=review_new_release(args.release_dir,args.public_key,args.archive,args.release_evidence)
        if args.report_json:
            with args.report_json.open('x',encoding='utf-8') as f:
                json.dump(result,f,indent=2,sort_keys=True)
                f.write('\n')
    except (VerificationError,OSError,KeyError,ValueError) as e:
        print('HOLD: 1.0.1 publisher/package evidence failed:',str(e))
        print('No downloads, licences, customer projects or private release objects were modified.')
        return 2
    print('PASS: Independently pinned publisher RSA signature, manifest and every archive payload member.')
    print('PASS: Full unsigned content, backend/frontend source revisions, release SHA256 and approval references match.')
    print('HOLD: Medical/governance approvals and private R2 distribution require explicit independent production review.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
