#!/usr/bin/env python3
"""Release helper script."""

import re
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path


def get_current_version():
    """Get version from pyproject.toml."""
    manifest_path = Path('pyproject.toml')
    with open(manifest_path, 'rb') as f:
        data = tomllib.load(f)
    return data['project']['version']


def get_last_tag():
    """Get the last git tag."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits_since_tag(tag):
    """Get commit messages since the last tag."""
    if tag:
        cmd = ['git', 'log', f'{tag}..HEAD', '--pretty=format:%s']
    else:
        cmd = ['git', 'log', '--pretty=format:%s']

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout.strip() else []


def update_changelog(version):
    """Update CHANGELOG.md with new version."""
    changelog_path = Path('CHANGELOG.md')

    # Get commits since last tag
    last_tag = get_last_tag()
    commits = get_commits_since_tag(last_tag)

    if not commits or commits == ['']:
        print('No new commits found')
        return ''

    # Create new entry
    date = datetime.now().strftime('%Y-%m-%d')
    new_entry = f'## [{version}] - {date}\n\n'

    for commit in commits:
        if commit.strip():
            new_entry += f'- {commit.strip()}\n'

    new_entry += '\n'

    # Read existing changelog or create new one
    if changelog_path.exists():
        content = changelog_path.read_text()
        # Insert after the first line (# Changelog)
        lines = content.split('\n')
        if lines and lines[0].startswith('# '):
            lines.insert(2, new_entry)
            updated_content = '\n'.join(lines)
        else:
            updated_content = new_entry + content
    else:
        updated_content = f'# Changelog\n\n{new_entry}'

    changelog_path.write_text(updated_content)
    print(f'Updated CHANGELOG.md with {len(commits)} commits')
    return new_entry


def update_blend_manifest_version(version):
    """Update version in blender_manifest.toml."""
    blend_manifest_path = Path('blender_manifest.toml')
    content = blend_manifest_path.read_text()
    updated = re.sub(r'version = "[^"]+"', f'version = "{version}"', content)
    blend_manifest_path.write_text(updated)
    print(f'Updated blender_manifest.toml to {version}')


def update_init_version(version):
    """Update version tuple in __init__.py."""
    init_path = Path('__init__.py')
    content = init_path.read_text()

    # Convert version string to tuple (e.g., "0.3.2" -> (0, 3, 2))
    parts = version.split('.')
    version_tuple = f'({", ".join(parts)})'

    updated = re.sub(r"'version': \([^)]+\)", f"'version': {version_tuple}", content)
    init_path.write_text(updated)
    print(f'Updated __init__.py to {version_tuple}')


def create_release():
    """Sync versions and create git tag."""
    version = get_current_version()
    tag = f'v{version}'

    print(f'Syncing all files to version {version}')

    # Update other version files
    update_blend_manifest_version(version)
    update_init_version(version)
    changelog_content = update_changelog(version)

    # Build the addon zip (this updates uv.lock)
    print('Building the addon zip')
    subprocess.run(['uv', 'run', 'build.py'], check=True)

    # Commit the changelog and version updates
    subprocess.run(['git', 'add', '.'], check=True)
    if changelog_content:
        commit_message = f'Release {version}\n\n{changelog_content}'
    else:
        commit_message = f'Release {version}'
    subprocess.run(
        ['git', 'commit', '-m', commit_message],
        check=True,
    )

    print(f'Creating release for version {version}')

    # Push commits first
    subprocess.run(['git', 'push'], check=True)

    # Create tag
    subprocess.run(['git', 'tag', tag], check=True)

    # Push tag
    subprocess.run(['git', 'push', 'origin', tag], check=True)

    print(f'✓ Released {tag}')
    print('✓ GitHub Action will now create the release.')


if __name__ == '__main__':
    create_release()
