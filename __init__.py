import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty
from bpy.types import AddonPreferences

bl_info = {
    'name': 'EditorBar',
    'author': 'atetraxx',
    'version': (0, 1, 0),
    'blender': (4, 0, 0),
    'location': 'View3D > Sidebar > View Tab',
    'description': 'Turns the default Outliner and Properties editors in Blender workspaces into a sidebar that you can quickly collapse and expand',
    'warning': '',
    'category': 'UI',
}

sidebar_items = [
    ('LEFT', 'Left', 'Sidebar on the left'),
    ('RIGHT', 'Right', 'Sidebar on the right'),
]


class EditorBarPreferences(AddonPreferences):
    bl_idname = __package__  # type: ignore[assignment]

    sidebar_side: EnumProperty(
        name='Sidebar Side',
        description='Choose which side to create sidebar',
        items=sidebar_items,
        default='RIGHT',
    )
    split_factor: FloatProperty(
        name='Sidebar Width',
        description='Proportion of window width for sidebar',
        min=0.1,
        max=0.5,
        default=0.173,
    )
    stack_ratio: FloatProperty(
        name='Stack Height Ratio',
        description='Proportion of sidebar height for Properties',
        min=0.5,
        max=0.9,
        default=0.66,
    )
    flip_editors: BoolProperty(
        name='Flip Editors Vertically',
        description='Outliner on bottom, Properties on top',
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text='EditorBar Preferences')
        layout.prop(self, 'sidebar_side')
        layout.prop(self, 'split_factor')
        layout.prop(self, 'stack_ratio')
        layout.prop(self, 'flip_editors')


if 'bpy' in locals():
    import importlib

    from . import editorbar

    importlib.reload(editorbar)
else:
    from . import editorbar

# Classes to register
classes = [
    EditorBarPreferences,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    editorbar.register()


def unregister():
    editorbar.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
