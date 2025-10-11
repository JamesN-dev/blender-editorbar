#!/usr/bin/env python3
"""Release helper script."""

import subprocess
import tomllib
from pathlib import Path


def get_current_version():
    """Get version from blender_manifest.toml."""
    manifest_path = Path("blender_manifest.toml")
    with open(manifest_path, "rb") as f:
        data = tomllib.load(f)
    return data["version"]

def create_release():
    """Create git tag and push for release."""
    version = get_current_version()
    tag = f"v{version}"

    print(f"Creating release for version {version}")

    # Create tag
    subprocess.run(["git", "tag", tag], check=True)

    # Push tag
    subprocess.run(["git", "push", "origin", tag], check=True)

    print(f"✓ Released {tag}")

if __name__ == "__main__":
    create_release()
