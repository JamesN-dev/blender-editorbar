# Contributing

## Development

### Dev tools used

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (dependency management)
- [ruff](https://github.com/astral-sh/ruff) (linting & formatting)
- [basedpyright](https://github.com/RobertCraigie/basedpyright) (type checking)
- [fake-bpy-module-latest](https://pypi.org/project/fake-bpy-module-latest/) (Blender API stubs for dev)

### Setup

```bash
uv sync
```

### Testing

To create a local test build of the addon, you can run the following command:

```bash
uv run build.py
```

Build.py creates `editorbar.zip` file in the `dist/` directory, which you can then install in Blender for testing purposes.

- Note: If creating a new file, make sure it is added to capture in the build.py script.

### Releasing

_Note: For maintainers only._

1.  Make your commits.
2.  Update the version number in `pyproject.toml`.
3.  Run `uv run release.py`.

The `release.py` script will handle updating all necessary files, building the addon, committing the changes, and creating a new release tag. The GitHub Actions workflow will then automatically create the GitHub release.
