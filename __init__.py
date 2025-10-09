# editor_toggle/__init__.py
from . import editorbar

bl_info = editorbar.bl_info


def register() -> None:
    editorbar.register()


def unregister() -> None:
    editorbar.unregister()
