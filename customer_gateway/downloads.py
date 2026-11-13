"""Private GET issuance. URL signing is disabled unless both release flags are explicit."""
from datetime import datetime, timezone
from urllib.parse import urlsplit
from sqlalchemy import select, func
try:
    from .entitlements import tenants, memberships, grants, admins, elevations, events
    from .download_policy import (authorize_download, Principal, Membership, Grant, Role, Denied, CLINIC_1_0_0, PUBLISHER_101_SPKI_SHA256)
except ImportError:
    from entitlements import tenants, memberships, grants, admins, elevations, events
    from download_policy import (authorize_download, Principal, Membership, Grant, Role, Denied, CLINIC_1_0_0, PUBLISHER_101_SPKI_SHA256)

R2_ENDPOINT='https://d0ad5986fca56c661b92988f2ea1c1f7.r2.cloudflarestorage.com'
EXPECTED_ETAG='fdb7dffbf9039a6e85a3bd30802b77dd'


class R2Signer:
    def __init__(self, key_id, secret, release=CLINIC_1_0_0, expected_etag=EXPECTED_ETAG):
        if not key_id or not secret:
            raise ValueError('Dedicated R2 read credentials required')
        if (release.id not in ('tec-epr-clinic-1.0.0','tec-epr-clinic-1.0.1')
                or release.publisher_spki_sha256 != (
                    CLINIC_1_0_0.publisher_spki_sha256 if release.id == 'tec-epr-clinic-1.0.0'
                    else PUBLISHER_101_SPKI_SHA256)
                or not expected_etag or len(expected_etag)>128):
            raise ValueError('Unapproved private release object identity')
        self.release, self.expected_etag = release, expected_etag
        import boto3
        from botocore.config import Config
        self.client=boto3.client('s3',endpoint_url=R2_ENDPOINT,region_name='auto',
            aws_access_key_id=key_id,aws_secret_access_key=secret,
            config=Config(signature_version='s3v4',s3={'addressing_style':'path'},
                          connect_timeout=3,read_timeout=5,retries={'total_max_attempts':1}))

    def check(self):
        release=self.release
        obj=self.client.head_object(Bucket=release.bucket,Key=release.object_key)
        if obj.get('ContentLength')!=release.bytes or obj.get('ETag','').strip('"')!=self.expected_etag:
            raise ValueError('Private object differs from verified read-back evidence')
        # Size/ETag are change detection, not signature verification. Installer trust
        # still requires full SHA-256 and the independently authenticated publisher key.

    def sign(self, decision):
        release=decision.release
        if release!=self.release or not 1 <= decision.ttl_seconds <= 300:
            raise ValueError('Unsupported signing request')
        url=self.client.generate_presigned_url('get_object',Params={
            'Bucket':release.bucket,'Key':release.object_key,
            'ResponseCacheControl':'no-store',
            'ResponseContentDisposition':'attachment; filename="'+release.object_key.rsplit('/',1)[1]+'"'},
            ExpiresIn=decision.ttl_seconds,HttpMethod='GET')
        parsed=urlsplit(url)
        if (parsed.scheme!='https' or parsed.netloc!=urlsplit(R2_ENDPOINT).netloc or
            parsed.path!='/'+release.bucket+'/'+release.object_key):
            raise ValueError('Unexpected signing destination')
        return url


class Downloads:
    def __init__(self, access, signer, enabled=False, release_approved=False,
                 release=CLINIC_1_0_0):
        self.access,self.signer=access,signer
        self.enabled,self.release_approved=enabled,release_approved
        self.release=release

    def issue(self, session_hash, grant_id):
        if self.enabled is not True or self.release_approved is not True or not self.signer:
            raise Denied('Downloads are not enabled')
        with self.access.engine.begin() as c:
            now=int(self.access.clock())
            s=self.access.sessions
            session=c.execute(select(s).where(s.c.token_hash==session_hash,s.c.expires>now)
                              .with_for_update()).mappings().first()
            if not session: raise Denied('Sign in required')
            staff=c.execute(select(admins).where(admins.c.subject==session['subject']).with_for_update()).mappings().first()
            if staff and not staff['active']: raise Denied('Administrator access is inactive')
            evidence=c.execute(select(elevations).where(elevations.c.session_hash==session_hash,
                    elevations.c.subject==session['subject'],elevations.c.expires>now,
                    elevations.c.verified_at<=now,elevations.c.verified_at>now-300)
                    .with_for_update()).mappings().first()
            g=c.execute(select(grants).where(grants.c.id==grant_id).with_for_update()).mappings().first()
            if not g: raise Denied('Download access denied')
            tenant=c.execute(select(tenants).where(tenants.c.id==g['tenant_id']).with_for_update()).mappings().first()
            member=c.execute(select(memberships).where(memberships.c.tenant_id==g['tenant_id'],
                    memberships.c.subject==session['subject']).with_for_update()).mappings().first()
            if not tenant or not tenant['active'] or not member: raise Denied('Download access denied')
            dt=lambda value:datetime.fromtimestamp(value,timezone.utc)
            def decision():
                checked_at=self.access.clock()
                fresh_evidence=bool(evidence and evidence["provider_reference"].strip()
                    and evidence["verified_at"] <= checked_at < evidence["expires"]
                    and evidence["verified_at"] > checked_at-300)
                return authorize_download(enabled=self.enabled,trusted_issuer='https://api.workos.com',
                    principal=Principal('https://api.workos.com',session['subject'],True,dt(session['expires']),
                        Role.ADMIN if staff else Role.CUSTOMER,fresh_evidence),
                    membership=Membership('https://api.workos.com',session['subject'],member['tenant_id'],member['active']),
                    grant=Grant(g['id'],g['tenant_id'],g['release_id'],g['state'],dt(g['starts']),dt(g['expires']),
                                g['approval_reference'],g['contract_reference']),
                    requested_tenant=g['tenant_id'],requested_release=g['release_id'],
                    now=dt(checked_at),release_withdrawn=not self.release_approved,
                    release=self.release)
            decision()  # Reject before touching R2.
            count=c.scalar(select(func.count()).select_from(events).where(events.c.event=='download_link_issued',
                events.c.actor==session['subject'],events.c.grant_id==grant_id,events.c.created>now-900))
            if count>=10: raise Denied('Download request limit reached; try again later')
            self.signer.check()
            allowed=decision()  # Recheck expiry after the bounded HEAD request.
            url=self.signer.sign(allowed)
            self.access._event(c,'download_link_issued',session['subject'],grant_id,int(self.access.clock()))
        # Do not return the bearer URL until the audit transaction has committed.
        return url,allowed
