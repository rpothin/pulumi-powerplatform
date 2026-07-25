#!/usr/bin/env python3
"""Swap the generated Java SDK's Maven Central publish plugin for a Central
Portal-native one.

pulumi-java-gen emits `io.github.gradle-nexus.publish-plugin`, which talks to
the legacy OSSRH Nexus2 "staging profile" API. Sonatype fully sunset OSSRH on
2025-06-30 and the compatibility shim at ossrh-staging-api.central.sonatype.com
does not reliably support staging-profile lookups anymore (see
https://github.com/gradle-nexus/publish-plugin/issues/379), causing
`initializeSonatypeStagingRepository` to fail with:

    Failed to find staging profile for package group: io.github.rpothin

This script replaces that plugin with `com.gradleup.nmcp` (+ its aggregation
plugin), which publishes existing `maven-publish` publications straight
through the new Central Portal Publisher API and has no staging-profile
concept. It is idempotent: if the swap has already been applied, it is a
no-op. Any unexpected state causes a hard failure.

Usage:
    python3 scripts/patch-java-nexus-plugin.py [--gradle-path PATH]
"""

import argparse
import sys
from pathlib import Path

NMCP_VERSION = "1.6.1"

OLD_PLUGIN_LINE = '    id("io.github.gradle-nexus.publish-plugin") version "2.0.0"\n'
NEW_PLUGIN_LINES = (
    f'    id("com.gradleup.nmcp") version "{NMCP_VERSION}"\n'
    f'    id("com.gradleup.nmcp.aggregation") version "{NMCP_VERSION}"\n'
)

OLD_URL_VARS = (
    'def publishRepoURL = System.getenv("PUBLISH_REPO_URL") ?: '
    '"https://central.sonatype.com/repository/maven-snapshots/"\n'
    'def publishStagingURL = System.getenv("PUBLISH_STAGING_URL") ?: '
    '"https://ossrh-staging-api.central.sonatype.com/service/local/"\n'
)

OLD_NEXUS_BLOCK = """if (publishRepoUsername) {
    nexusPublishing {
        repositories {
            sonatype {
                nexusUrl.set(uri(publishStagingURL))
                snapshotRepositoryUrl.set(uri(publishRepoURL))
                username = publishRepoUsername
                password = publishRepoPassword
            }
        }
    }
}
"""

NEW_NMCP_BLOCK = """if (publishRepoUsername) {
    nmcpAggregation {
        centralPortal {
            username = publishRepoUsername
            password = publishRepoPassword
            // AUTOMATIC is nmcp's default: auto-publish once Central Portal
            // validation passes, matching the previous
            // closeAndReleaseSonatypeStagingRepository behavior.
            publishingType = "AUTOMATIC"
        }
    }

    // Single-module project: aggregate this project's own publication.
    dependencies {
        nmcpAggregation(project(":"))
    }
}
"""


def require_single(content: str, needle: str, description: str) -> int:
    count = content.count(needle)
    if count > 1:
        print(f"ERROR: {description}: expected at most 1 occurrence, found {count}", file=sys.stderr)
        sys.exit(1)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gradle-path", default="sdk/java/build.gradle",
                        help="Path to build.gradle (default: sdk/java/build.gradle)")
    args = parser.parse_args()

    gradle_path = Path(args.gradle_path)
    if not gradle_path.exists():
        print(f"ERROR: gradle file not found: {gradle_path}", file=sys.stderr)
        sys.exit(1)

    content = gradle_path.read_text(encoding="utf-8")
    original = content

    already_patched = "com.gradleup.nmcp" in content
    still_legacy = "io.github.gradle-nexus.publish-plugin" in content

    if already_patched and still_legacy:
        print("ERROR: build.gradle has both the old and new publish plugins configured", file=sys.stderr)
        sys.exit(1)

    if not already_patched and not still_legacy:
        print("ERROR: neither the legacy nexus plugin nor com.gradleup.nmcp found in build.gradle", file=sys.stderr)
        sys.exit(1)

    if still_legacy:
        if require_single(content, OLD_PLUGIN_LINE, "legacy publish-plugin declaration") != 1:
            print("ERROR: legacy publish-plugin declaration not found in expected form", file=sys.stderr)
            sys.exit(1)
        content = content.replace(OLD_PLUGIN_LINE, NEW_PLUGIN_LINES, 1)

        if require_single(content, OLD_URL_VARS, "legacy staging/snapshot URL vars") == 1:
            content = content.replace(OLD_URL_VARS, "", 1)

        if require_single(content, OLD_NEXUS_BLOCK, "nexusPublishing block") != 1:
            print("ERROR: nexusPublishing block not found in expected form", file=sys.stderr)
            sys.exit(1)
        content = content.replace(OLD_NEXUS_BLOCK, NEW_NMCP_BLOCK, 1)

    if content != original:
        gradle_path.write_text(content, encoding="utf-8")
        print(f"Patched Java publish plugin (nexus -> nmcp) in {gradle_path}")
    else:
        print(f"Java publish plugin already up to date (nmcp) in {gradle_path}")


if __name__ == "__main__":
    main()
