"""Fail-closed TEC EPR 1.0.1 fresh-install private R2 release selection.

Requires BOTH an owner-produced signed-release evidence summary and an independent
full publisher signature/payload readback report. Neither input grants access:
separate human-approved gateway and customer grants remain mandatory.
"""
import json
import re
from pathlib import PurePosixPath
try:
    from .download_policy import Release, CLINIC_1_0_0
except ImportError:
    from download_policy import Release, CLINIC_1_0_0

SOURCE_BACKEND='91b848bfccb0951e010be8f566b4146a53b6a586'
SOURCE_FRONTEND='345384515c70dd7f6569e96f5c38b749b4ff986d'
SOURCE_MANIFEST_SHA256='66907861e79d59a463dbb3b0d178bfe5fba3dfb85c8c8347c152e0cbf8f58218'
FINGERPRINT='6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733'
SHA=re.compile(r'^[0-9a-f]{64}$')
ETAG=re.compile(r'^[0-9a-f]{32}(?:-[1-9][0-9]*)?$')
NAME=re.compile(r'^TEC-EPR-Clinic-Edition-1\.0\.1-[A-Za-z0-9][A-Za-z0-9._-]{0,100}\.tar\.gz$')


def _no_duplicates(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:
            raise ValueError('Duplicate authenticated release metadata field')
        obj[k]=v
    return obj


def _read(value):
    if not isinstance(value,str) or not 10<len(value)<65536:
        raise ValueError('Missing or oversized signed release evidence')
    try:
        parsed=json.loads(value,object_pairs_hook=_no_duplicates)
    except (TypeError,ValueError,UnicodeError) as exc:
        raise ValueError('Invalid signed release verification evidence') from exc
    if not isinstance(parsed,dict):
        raise ValueError('Signed release evidence must be an object')
    return parsed


def approved_release_101(environ):
    """Returns an exact Release + expected ETag; NEVER returns R2 credentials.

    Fails closed unless the owner actually signed and independently verified a
    1.0.1 fresh-only release, a private R2 readback matches and commercial
    activation has an explicit human approval reference.
    """
    if (environ.get('GATEWAY_DOWNLOADS_ENABLED')!='true' or
        environ.get('GATEWAY_RELEASE_APPROVED')!='true' or
        environ.get('GATEWAY_RELEASE_ID')!='tec-epr-clinic-1.0.1'):
        raise ValueError('TEC EPR 1.0.1 private distribution is not authorised')
    evidence=_read(environ.get('GATEWAY_SIGNED_101_RELEASE_EVIDENCE_JSON'))
    report=_read(environ.get('GATEWAY_VERIFIED_101_REPORT_JSON'))
    fname=evidence.get('archiveFilename')
    if (not isinstance(fname,str) or not NAME.fullmatch(fname) or
        PurePosixPath(fname).name!=fname):
        raise ValueError('Unsupported fresh-only archive name')
    sha=evidence.get('archiveSha256')
    if (not isinstance(sha,str) or not SHA.fullmatch(sha) or
        evidence.get('status')!='SIGNED_PENDING_COMMERCIAL_GATEWAY_APPROVAL' or
        evidence.get('releaseVersion')!='1.0.1' or
        evidence.get('releaseScope')!='FRESH_INSTALLATIONS_ONLY' or
        evidence.get('upgradeSupported') is not False or
        evidence.get('gatewayActivated') is not False or
        evidence.get('publisherSpkiSha256')!=FINGERPRINT or
        type(evidence.get('archiveBytes')) is not int or
        evidence['archiveBytes']<=10000 or
        not isinstance(evidence.get('signedManifestSha256'),str) or
        not SHA.fullmatch(evidence['signedManifestSha256']) or
        evidence.get('source')!={'backendRevision':SOURCE_BACKEND,'frontendRevision':SOURCE_FRONTEND}):
        raise ValueError('Invalid signed 1.0.1 fresh-install release metadata')
    if (report.get('assessment')!='VERIFIED_1_0_1_ARCHIVE_PENDING_HUMAN_GATEWAY_APPROVAL' or
        report.get('releaseVersion')!='1.0.1' or
        report.get('releaseScope')!='FRESH_INSTALLATIONS_ONLY' or
        report.get('upgradeSupported') is not False or
        report.get('verifiedArchiveSha256')!=sha or
        report.get('archiveBytes')!=evidence['archiveBytes'] or
        report.get('signedManifestSha256')!=evidence['signedManifestSha256'] or
        report.get('publisherSpkiSha256')!=FINGERPRINT or
        report.get('backendRevision')!=SOURCE_BACKEND or
        report.get('frontendRevision')!=SOURCE_FRONTEND or
        report.get('allArchiveMembersVerified') is not True or
        report.get('publisherSignatureVerified') is not True or
        report.get('commercialReleaseApproved') is not False or
        report.get('releaseGrantIssued') is not False or
        report.get('customerLicenseIssued') is not False or
        report.get('reviewedImageIds')!=evidence.get('imageIds')):
        raise ValueError('Independent RSA-4096 release evidence mismatch')
    if (not isinstance(report.get('candidateManifestSha256'),str) or
        report['candidateManifestSha256']!=SOURCE_MANIFEST_SHA256):
        raise ValueError('Frozen 1.0.1 candidate source manifest mismatch')
    etag=environ.get('GATEWAY_R2_101_EXPECTED_ETAG','')
    if not ETAG.fullmatch(etag):
        raise ValueError('Missing immutable private R2 object ETag')
    if environ.get('GATEWAY_R2_101_READBACK_SHA256')!=sha:
        raise ValueError('R2 private object has not been independently read back')
    for key in ('GATEWAY_OWNER_COMMERCIAL_APPROVAL_REF',
                'GATEWAY_MEDICAL_RELEASE_APPROVAL_REF'):
        value=environ.get(key,'')
        if (not isinstance(value,str) or len(value.strip())<12 or len(value)>240 or
            value.strip().lower().startswith(('synthetic','test','pending','todo'))):
            raise ValueError('Missing independently recorded human sign-off')
    obj=Release(id='tec-epr-clinic-1.0.1',bucket='tec-epr-private-releases',
        object_key='tec-epr/clinic-edition/1.0.1/'+fname,
        sha256=sha,bytes=evidence['archiveBytes'],publisher_spki_sha256=FINGERPRINT)
    if obj.publisher_spki_sha256!=CLINIC_1_0_0.publisher_spki_sha256:
        raise ValueError('Unexpected publisher key change')
    return obj,etag