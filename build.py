#!/usr/bin/env python3
"""Build script for EditorBar Blender addon."""

import zipfile
from pathlib import Path

# Get the project root and source directory
PROJECT_ROOT: Path = Path(__file__).parent
ADDON_NAME = 'editorbar'

# Files to include in build zip
INCLUDE_FILES: list[str] = [
    'blender_manifest.toml',
    'LICENSE',
    'README.md',
    'src/editorbar/editorbar.py',
    'src/editorbar/version_adapter.py',
    'src/editorbar/__init__.py',
]


def create_addon_zip() -> Path:
    """Create a zip file containing only the required addon files."""
    dist_dir = PROJECT_ROOT / 'dist'
    dist_dir.mkdir(exist_ok=True)

    zip_path = dist_dir / f'{ADDON_NAME}.zip'

    if zip_path.is_file():
        zip_path.unlink()
        print(f'Removed existing {zip_path.name}')

    print(f'Creating {zip_path.name}...')

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for fname in INCLUDE_FILES:
            fpath: Path = PROJECT_ROOT / fname
            if fpath.is_file():
                arcname = ADDON_NAME + '/' + Path(fname).name
                zipf.write(fpath, arcname)
                print(f'  Added: {arcname}')
            else:
                print(f'  WARNING: {fname} not found!')

    print(f'\n✓ Built successfully: {zip_path}')
    print(f'  Size: {zip_path.stat().st_size / 1024:.1f} KB')
    return zip_path


if __name__ == '__main__':
    create_addon_zip()
