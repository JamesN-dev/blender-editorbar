#!/usr/bin/env python3
"""Build script for EditorBar Blender addon."""

import zipfile
from pathlib import Path

# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent
ADDON_NAME = "editorbar"

# Files and directories to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    ".venv",
    ".ruff_cache",
    ".python-version",
    ".gitignore",
    "*.pyc",
    "*.lock",
    "*.zip",
    "pyproject.toml",
    "pyrightconfig.json",
    "ruff.toml",
    "build.py",
    "dist",
]


def should_exclude(path: Path) -> bool:
    """Check if a path should be excluded from the build."""
    path_str = str(path)
    name = path.name

    # Check exact matches
    if name in EXCLUDE_PATTERNS:
        return True

    # Check pattern matches
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*.") and name.endswith(pattern[1:]):
            return True
        if pattern in path_str:
            return True

    return False


def create_addon_zip():
    """Create a zip file of the addon."""
    # Create dist directory
    dist_dir = SCRIPT_DIR / "dist"
    dist_dir.mkdir(exist_ok=True)

    zip_path = dist_dir / f"{ADDON_NAME}.zip"

    # Remove existing zip if it exists
    if zip_path.exists():
        zip_path.unlink()
        print(f"Removed existing {zip_path.name}")

    print(f"Creating {zip_path.name}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add all files in the addon directory
        for item in SCRIPT_DIR.rglob("*"):
            if item.is_file() and not should_exclude(item):
                # Calculate the archive name (relative path within addon folder)
                arcname = ADDON_NAME / item.relative_to(SCRIPT_DIR)
                zipf.write(item, arcname)
                print(f"  Added: {arcname}")

    print(f"\n✓ Built successfully: {zip_path}")
    print(f"  Size: {zip_path.stat().st_size / 1024:.1f} KB")
    return zip_path


if __name__ == "__main__":
    create_addon_zip()
