# Blender EditorBar - Blender Addon

Blender EditorBar turns the default Outliner and Properties editors in Blender workspaces into a sidebar that you can quickly collapse and expand.

A common annoyance when working in blender, for me, is that there's no simple, intuitive way to collapse & expand the default outliner and properties editors in object and edit views. Those key editors are at default docked on the right and feel like they should be easily collapsable, but Blender doesn't provide that out of the box.

**This add-on fixes that.**

When activating the shortcut or clicking a button in the N panel 'View' menu, you can collapse & expand both editors at once, turning those default editors into a toggleable sidebar. By default, the shortcut is <kbd>Alt</kbd>/<kbd>Opt</kbd> + <kbd>Shift</kbd> + <kbd>N</kbd>, echoing Blender's own "N panel" sidebar shortcut.

---

## Customizing the Shortcut

Want a different shortcut?
You can easily change or add your own in **Edit > Preferences > Keymap**.
Search for "Editor Sidebar" `wm.toggle_outliner_properties` and assign any key combination you like.

---

## Installation (Blender Extension)

## Installation (Legacy)

1. **Download the Addon**
    - Copy or download `editorbar.py` from this repository.

2. **Install in Blender**
    - Open Blender.
    - Go to **Edit > Preferences > Add-ons > Install**.
    - Select `editorbar.py` and enable the addon.

---

## Usage

There are three ways to toggle the sidebar:

- **3D Viewport Menu** at very bottom of menu
- **Sidebar button** a button residing within the N panel (View menu)
- **Keyboard shortcut:** <kbd>Alt</kbd>/<kbd>Opt</kbd> + <kbd>Shift</kbd> + <kbd>N</kbd>

---

## Disclaimer

Blender EditorBar is built and tested for Blender's official workspace/layout presets (e.g., Default, Animation, Scripting).

If you use custom or heavily modified workspaces—such as non-standard editor splits, unusual panel placements, or floating editors—sidebar expansion and collapse may behave unpredictably.

The add-on is optimized for layouts where Outliner and Properties editors are positioned on the right side of the screen as in Blender’s default configurations.

Unexpected or undesired behavior may occur when used in custom setups. Future versions may support more dynamic layouts, but official layouts are the primary target.

For best results, use Blender EditorBar within Blender's official workspace presets.

---

## Development

### Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (dependency management)
- [basedpyright](https://github.com/RobertCraigie/basedpyright) (type checking)
- [fake-bpy-module-latest](https://pypi.org/project/fake-bpy-module-latest/) (Blender API stubs for dev)

### Setup

```bash
uv init
uv add --dev fake-bpy-module-latest basedpyright
uv sync
```

### Type Checking

```bash
basedpyright
```

### Linting (optional)

If you use [ruff](https://github.com/astral-sh/ruff):

```bash
uv add --dev ruff
ruff check .
```

---

## Troubleshooting

- **Type errors about `bpy` or Blender API:**
  Ensure `fake-bpy-module-latest` is installed and your editor is using the correct Python environment.
- **Addon not showing in Blender:**
  Double-check you installed the correct file and enabled the addon in Preferences.

---

## License

GPL-3.0-or-later

---
