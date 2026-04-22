#!/usr/bin/env python3
"""Patch empty POM metadata placeholders in the generated Java SDK build.gradle.

pulumi-java-gen generates several required Maven Central POM fields as empty
strings. This script fills them in from schema.json and is idempotent: if a
field already has the correct value, it is left unchanged. Any unexpected state
causes a hard failure.

Usage:
    python3 scripts/patch-java-pom-metadata.py [--gradle-path PATH] [--schema-path PATH]
"""

import argparse
import json
import re
import sys
from pathlib import Path


def load_schema(schema_path: Path) -> dict:
    with schema_path.open() as f:
        return json.load(f)


def patch(content: str, pattern: str, replacement: str, description: str) -> str:
    """Apply a single regex substitution, asserting exactly one match."""
    matches = re.findall(pattern, content, flags=re.MULTILINE)
    if len(matches) == 0:
        # Field is already patched — verify the replacement is present.
        check = re.sub(r"\\1", r"", replacement).replace("\\1", "")
        # Re-derive the expected literal from replacement (best-effort check).
        return content
    if len(matches) > 1:
        print(f"ERROR: {description}: expected exactly 1 match, found {len(matches)}", file=sys.stderr)
        sys.exit(1)
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if new_content == content:
        print(f"ERROR: {description}: substitution produced no change", file=sys.stderr)
        sys.exit(1)
    return new_content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gradle-path", default="sdk/java/build.gradle",
                        help="Path to build.gradle (default: sdk/java/build.gradle)")
    parser.add_argument("--schema-path", default="schema.json",
                        help="Path to schema.json (default: schema.json)")
    args = parser.parse_args()

    gradle_path = Path(args.gradle_path)
    schema_path = Path(args.schema_path)

    if not gradle_path.exists():
        print(f"ERROR: gradle file not found: {gradle_path}", file=sys.stderr)
        sys.exit(1)
    if not schema_path.exists():
        print(f"ERROR: schema file not found: {schema_path}", file=sys.stderr)
        sys.exit(1)

    schema = load_schema(schema_path)
    display_name = schema.get("displayName", "")
    license_id = schema.get("license", "")
    publisher = schema.get("publisher", "")

    if not display_name or not license_id or not publisher:
        print("ERROR: schema.json is missing displayName, license, or publisher", file=sys.stderr)
        sys.exit(1)

    pom_name = f"Pulumi {display_name} Provider"
    license_url = f"https://opensource.org/licenses/{license_id}"

    content = gradle_path.read_text(encoding="utf-8")
    original = content

    # --- Project name (pom { name = "" }, distinct from license/developer name fields) ---
    # Match name = "" that is immediately followed by a packaging line.
    pattern_proj_name = r'name = ""\n(\s+packaging)'
    expected_proj_name = f'name = "{pom_name}"\n\\1'
    if re.search(pattern_proj_name, content, flags=re.MULTILINE):
        content = patch(content, pattern_proj_name, expected_proj_name, "project name")
    elif f'name = "{pom_name}"' not in content:
        print(f'ERROR: project name field not found and "{pom_name}" not present', file=sys.stderr)
        sys.exit(1)

    # --- License block: name and url together ---
    pattern_license = r'(license \{\n\s+)name = ""\n(\s+)url = ""'
    expected_license = f'\\1name = "{license_id}"\n\\2url = "{license_url}"'
    if re.search(pattern_license, content, flags=re.MULTILINE):
        content = patch(content, pattern_license, expected_license, "license block")
    elif f'name = "{license_id}"' not in content:
        print(f'ERROR: license name field not found and "{license_id}" not present', file=sys.stderr)
        sys.exit(1)

    # --- Developer id ---
    pattern_dev_id = r'\bid = ""'
    expected_dev_id = f'id = "{publisher}"'
    if re.search(pattern_dev_id, content, flags=re.MULTILINE):
        content = patch(content, pattern_dev_id, expected_dev_id, "developer id")
    elif f'id = "{publisher}"' not in content:
        print(f'ERROR: developer id field not found and "{publisher}" not present', file=sys.stderr)
        sys.exit(1)

    # --- Developer name (comes after the id line) ---
    pattern_dev_name = r'(id = "[^"]*"\n\s+)name = ""'
    expected_dev_name = f'\\1name = "{publisher}"'
    if re.search(pattern_dev_name, content, flags=re.MULTILINE):
        content = patch(content, pattern_dev_name, expected_dev_name, "developer name")
    elif re.search(rf'id = "{re.escape(publisher)}"\n\s+name = "{re.escape(publisher)}"', content, flags=re.MULTILINE):
        pass  # already patched
    else:
        print(f'ERROR: developer name field not found and correct value not present', file=sys.stderr)
        sys.exit(1)

    if content != original:
        gradle_path.write_text(content, encoding="utf-8")
        print(f"Patched Java POM metadata in {gradle_path}")
    else:
        print(f"Java POM metadata already up to date in {gradle_path}")


if __name__ == "__main__":
    main()
