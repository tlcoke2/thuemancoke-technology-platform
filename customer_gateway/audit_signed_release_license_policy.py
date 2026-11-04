"""Read-only comparison of the *signed* TEC EPR 1.0.0 package license policy.

Verifies the pinned archive + independently authenticated publisher signature
and every signed member before inspecting exactly the packaged middleware source.
Does not extract, execute, re-sign, upload, or change a release/clinical DB.
Cannot examine code hidden inside images.tar; reports INCONCLUSIVE in that case.
"""
import argparse
import re
import tarfile
from pathlib import Path

try:
    from .verify_release_payload import verify_release_payload
    from .verify_release_manifest import VerificationError
except ImportError:
    from verify_release_payload import verify_release_payload
    from verify_release_manifest import VerificationError

POLICY_PATH = "backend/src/middleware/checkLicense.js"
MAX_POLICY_BYTES = 128 * 1024


def review_policy_source(source):
    """Return known licensing bypass findings, without exposing code contents."""
    admin_role = bool(re.search(
        r"req\.user\s*\?\.\s*role\s*===\s*['\"]Admin['\"]"
        r"|req\.user\.role\s*===\s*['\"]Admin['\"]",
        source,
    ))
    admin_bypass = bool(re.search(
        r"adminBypass\s*:\s*true|X-License-Bypass['\"],\s*['\"]admin['\"]",
        source,
    ))
    env_bypass = bool(
        re.search(r"\bLICENSE_DISABLE\b", source)
        and re.search(r"X-License-Bypass['\"],\s*['\"]env['\"]", source)
    )
    return {
        "admin_bypass_signature": admin_role and admin_bypass,
        "global_env_bypass_signature": env_bypass,
    }


def read_packaged_source(archive):
    """Read just one fixed package member; reject ambiguity and unsafe types."""
    found = []
    try:
        with tarfile.open(archive, "r:gz") as listing:
            for member in listing:
                name = member.name
                while name.startswith("./"):
                    name = name[2:]
                if name == POLICY_PATH or name.endswith("/" + POLICY_PATH):
                    if not member.isfile() or member.size > MAX_POLICY_BYTES:
                        raise VerificationError("Expected a small regular middleware file")
                    found.append(member)
            if len(found) > 1:
                raise VerificationError("Ambiguous duplicate middleware paths in archive")
            if not found:
                return None
            item = listing.extractfile(found[0])
            if item is None:
                raise VerificationError("Unable to read expected signed middleware")
            with item:
                raw = item.read(MAX_POLICY_BYTES + 1)
            if len(raw) > MAX_POLICY_BYTES:
                raise VerificationError("Unexpected oversized middleware source")
            return raw.decode("utf-8")
    except (tarfile.TarError, OSError, UnicodeError):
        raise VerificationError("Cannot safely inspect middleware inside pinned archive") from None


def main(argv=None):
    cli = argparse.ArgumentParser(description="Review known licence bypasses in immutable signed TEC EPR 1.0.0 without modifying it.")
    cli.add_argument("--release-dir", type=Path, required=True,
                     help="Existing signed release manifest+signature directory")
    cli.add_argument("--public-key", type=Path, required=True,
                     help="Previously authenticated PUBLIC publisher key only")
    cli.add_argument("--archive", type=Path, required=True,
                     help="Original immutable 1.0.0 tar.gz archive")
    cli.add_argument("--archive-prefix", default="")
    args = cli.parse_args(argv)
    try:
        result = verify_release_payload(
            args.release_dir, args.public_key, args.archive,
            archive_prefix=args.archive_prefix,
        )
        source = read_packaged_source(args.archive)
    except (VerificationError, ValueError, OSError):
        print("FAIL: Could not verify the publisher-signed release and its pinned bytes; no policy assertion made.")
        print("No archive files, publisher keys or databases were modified.")
        return 2
    print("PASS: Pinned release archive, publisher signature and all signed payload members verified.")
    if source is None:
        print("INCONCLUSIVE: The packaged backend middleware source was not an exposed signed archive member.")
        print("An application inside images.tar must be audited separately; do not assume this release is safe.")
        return 1
    findings = review_policy_source(source)
    print("Packaged middleware located and inspected without extraction or execution.")
    for name, found in findings.items():
        print(name + ": " + ("DETECTED" if found else "NOT DETECTED BY SIGNATURE"))
    if any(findings.values()):
        print("BLOCK: A known commercial licence bypass pattern exists in signed package source.")
        print("Do not alter this immutable signed 1.0.0 release. Use a separately versioned and signed fix.")
        return 1
    print("NO KNOWN BYPASS PATTERN DETECTED in this one source file.")
    print("LIMITATION: Not a complete licensing security review, image audit or customer activation test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
