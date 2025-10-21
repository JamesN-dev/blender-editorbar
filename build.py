#!/usr/bin/env python3
"""Build script for EditorBar Blender addon."""

import zipfile
from pathlib import Path

# Get the directory containing this script
SCRIPT_DIR = Path(__file__).parent
ADDON_NAME = 'editorbar'

# Files and directories to exclude
INCLUDE_FILES = [
    'editorbar.py',
    'version_adapter.py',
    'blender_manifest.toml',
    'LICENSE',
    '__init__.py',
    'README.md',
]


# No need for exclusion logic; we will only include files explicitly listed in INCLUDE_FILES.


def create_addon_zip():
    """Create a zip file containing only the required addon files."""
    dist_dir = SCRIPT_DIR / 'dist'
    dist_dir.mkdir(exist_ok=True)

    zip_path = dist_dir / f'{ADDON_NAME}.zip'

    # Remove existing zip if it exists
    if zip_path.exists():
        zip_path.unlink()
        print(f'Removed existing {zip_path.name}')

    print(f'Creating {zip_path.name}...')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for fname in INCLUDE_FILES:
            fpath = SCRIPT_DIR / fname
            if fpath.exists():
                arcname = ADDON_NAME + '/' + fname
                zipf.write(fpath, arcname)
                print(f'  Added: {arcname}')
            else:
                print(f'  WARNING: {fname} not found!')

    print(f'\n✓ Built successfully: {zip_path}')
    print(f'  Size: {zip_path.stat().st_size / 1024:.1f} KB')
    return zip_path


if __name__ == '__main__':
    create_addon_zip()
