# Contributing

## Development

### Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (dependency management)
- [ruff](https://github.com/astral-sh/ruff) (linting & formatting)
- [basedpyright](https://github.com/RobertCraigie/basedpyright) (type checking)
- [fake-bpy-module-latest](https://pypi.org/project/fake-bpy-module-latest/) (Blender API stubs for dev)

### Setup

```bash
uv sync
```

### Releasing

_Note: For maintainers only._

1. Update version in `blender_manifest.toml`
2. Commit changes
3. Run `python release.py`
