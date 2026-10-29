# TEC EPR Clinic Edition 1.0.0: private R2 distribution COPY only.
# This script NEVER modifies the original signed master and NEVER uploads keys/databases.
# Default is verify + print plan. -Upload requires explicit private-bucket acknowledgement.
[CmdletBinding()]
param(
    [string]$SourceArchive = 'C:\My_Applications\TEC-EPR-Commercial-Releases\TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz',
    [Parameter(Mandatory=$true)][string]$VerifiedReleaseDirectory,
    [Parameter(Mandatory=$true)][string]$TrustedPublisherPublicKey,
    [Parameter(Mandatory=$true)][string]$VerifierScript,
    [string]$R2AccountId = '',
    [string]$R2Bucket = '',
    [switch]$Upload,
    [switch]$PrivateBucketConfirmed
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$expected = 'E1C75BB867627CB60F0F5FF9737B602661550A15DF75F5DF52BF8C43835C8C0E'
$expectedPublicFingerprint = '6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733'
$expectedName = 'TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz'
if ((Split-Path -Leaf $SourceArchive) -cne $expectedName) {
    throw 'Unexpected release filename; signed 1.0.0 identity mismatch.'
}
foreach ($file in @($SourceArchive, $TrustedPublisherPublicKey, $VerifierScript)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Required file not found: $file" }
}
if (-not (Test-Path -LiteralPath $VerifiedReleaseDirectory -PathType Container)) {
    throw 'A separately extracted, verified release directory must be supplied. Never extract into the master.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js 22+ is required to verify the independent publisher trust anchor.'
}
$source = (Resolve-Path -LiteralPath $SourceArchive).Path
$actual = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToUpperInvariant()
if ($actual -cne $expected) { throw "STOP: release SHA-256 mismatch. Do NOT upload." }
Write-Host '[PASS] Immutable source archive SHA-256 and expected release filename.'

$trustedPublicKey = (Resolve-Path -LiteralPath $TrustedPublisherPublicKey).Path
$publicHashJs = 'const fs=require("fs"),c=require("crypto");const key=c.createPublicKey(fs.readFileSync(process.argv[1]));console.log(c.createHash("sha256").update(key.export({type:"spki",format:"der"})).digest("hex"))'
$fingerprint = (& node -e $publicHashJs $trustedPublicKey | Out-String).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0 -or $fingerprint -cne $expectedPublicFingerprint) {
    throw 'STOP: independently supplied publisher RSA public-key fingerprint mismatch.'
}
Write-Host '[PASS] Independently trusted TEC EPR publisher SPKI fingerprint.'

$release = (Resolve-Path -LiteralPath $VerifiedReleaseDirectory).Path
$verifier = (Resolve-Path -LiteralPath $VerifierScript).Path
$verified = & node $verifier $release $trustedPublicKey 2>&1
if ($LASTEXITCODE -ne 0) {
    $verified | ForEach-Object { Write-Warning ([string]$_) }
    throw 'STOP: signed-release directory manifest, exact images or trust verification failed.'
}
$verified | ForEach-Object { Write-Host ([string]$_) }
Write-Host '[PASS] Separate release directory passed signed manifest verification.'

$key = "tec-epr/clinic-edition/1.0.0/$expectedName"
Write-Host ('Private destination key: ' + $key)
Write-Host ('Source SHA-256: ' + $actual)
if (-not $Upload) {
    Write-Host '[DRY RUN] No upload performed. Use -Upload -PrivateBucketConfirmed only after reviewing the private R2 bucket.'
    exit 0
}
if (-not $PrivateBucketConfirmed) {
    throw 'STOP: explicitly verify private bucket has NO public R2.dev access, public custom domain or anonymous read policy before upload.'
}
if ($R2AccountId -notmatch '^[a-fA-F0-9]{32}$' -or
    $R2Bucket -notmatch '^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$') {
    throw 'R2 account ID (32 hex chars) and approved private bucket name are required.'
}
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw 'AWS CLI is required for S3-compatible R2 upload. Credentials must be supplied securely by the operator, not in source.'
}
$endpoint = "https://$R2AccountId.r2.cloudflarestorage.com"
$existing = (& aws s3 ls "s3://$R2Bucket/$key" --endpoint-url $endpoint 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify private object existence; check bucket credentials. No upload attempted.' }
if ($existing) { throw 'STOP: immutable release object already exists; refusing overwrite.' }
Write-Host '[UPLOAD] Copying verified signed archive into private object storage. Source will not be modified.'
& aws s3 cp $source "s3://$R2Bucket/$key" --endpoint-url $endpoint --no-progress --only-show-errors --content-type 'application/gzip' --metadata "sha256=$($actual.ToLowerInvariant()),publisher-spki-sha256=$expectedPublicFingerprint"
if ($LASTEXITCODE -ne 0) { throw 'Upload failed: verify storage object before any distribution.' }
$head = & aws s3api head-object --bucket $R2Bucket --key $key --endpoint-url $endpoint --output json
if ($LASTEXITCODE -ne 0) { throw 'Upload could not be read back as metadata; distribution blocked.' }
$info = ($head | Out-String) | ConvertFrom-Json
if ([long]$info.ContentLength -ne [long](Get-Item -LiteralPath $source).Length -or
    $info.Metadata.sha256 -cne $actual.ToLowerInvariant()) {
    throw 'R2 object size / metadata failed validation. Distribution blocked.'
}
Write-Host '[PASS] Verified private R2 distribution copy and metadata.'
Write-Host 'IMPORTANT: Do not create a public bucket URL. Downloads require authenticated short-lived grants and their own acceptance gate.'
