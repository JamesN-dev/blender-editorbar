#!/usr/bin/env python3
"""Release helper script."""

import re
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path

def get_current_version():
    """Get version from blender_manifest.toml."""
    manifest_path = Path("blender_manifest.toml")
    with open(manifest_path, "rb") as f:
        data = tomllib.load(f)
    return data["version"]

def get_last_tag():
    """Get the last git tag."""
    try:
        result = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def get_commits_since_tag(tag):
    """Get commit messages since the last tag."""
    if tag:
        cmd = ["git", "log", f"{tag}..HEAD", "--pretty=format:%s"]
    else:
        cmd = ["git", "log", "--pretty=format:%s"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout.strip() else []

def update_changelog(version):
    """Update CHANGELOG.md with new version."""
    changelog_path = Path("CHANGELOG.md")
    
    # Get commits since last tag
    last_tag = get_last_tag()
    commits = get_commits_since_tag(last_tag)
    
    if not commits or commits == ['']:
        print("No new commits found")
        return
    
    # Create new entry
    date = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"## [{version}] - {date}\n\n"
    
    for commit in commits:
        if commit.strip():
            new_entry += f"- {commit.strip()}\n"
    
    new_entry += "\n"
    
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
        updated_content = f"# Changelog\n\n{new_entry}"
    
    changelog_path.write_text(updated_content)
    print(f"Updated CHANGELOG.md with {len(commits)} commits")

def update_pyproject_version(version):
    """Update version in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    updated = re.sub(r'version = "[^"]+"', f'version = "{version}"', content)
    pyproject_path.write_text(updated)
    print(f"Updated pyproject.toml to {version}")

def update_init_version(version):
    """Update version tuple in __init__.py."""
    init_path = Path("__init__.py")
    content = init_path.read_text()
    
    # Convert version string to tuple (e.g., "0.3.2" -> (0, 3, 2))
    parts = version.split(".")
    version_tuple = f"({', '.join(parts)})"
    
    updated = re.sub(r"'version': \([^)]+\)", f"'version': {version_tuple}", content)
    init_path.write_text(updated)
    print(f"Updated __init__.py to {version_tuple}")

def create_release():
    """Sync versions and create git tag."""
    version = get_current_version()
    tag = f"v{version}"
    
    print(f"Syncing all files to version {version}")
    
    # Update other version files
    update_pyproject_version(version)
    update_init_version(version)
    update_changelog(version)
    
    # Commit the changelog and version updates
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Release {version}: Update versions and changelog"], check=True)
    
    print(f"Creating release for version {version}")
    
    # Push commits first
    subprocess.run(["git", "push"], check=True)
    
    # Create tag
    subprocess.run(["git", "tag", tag], check=True)
    
    # Push tag
    subprocess.run(["git", "push", "origin", tag], check=True)
    
    print(f"✓ Released {tag}")

if __name__ == "__main__":
    create_release()