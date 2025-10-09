import bpy

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

if 'bpy' in locals():
    import importlib

    from . import editorbar

    importlib.reload(editorbar)
else:
    from . import editorbar

# Classes to register
classes = [
    editorbar.EditorTogglePreferences,
    editorbar.EDITORBAR_OT_toggle_sidebar,
    editorbar.VIEW3D_PT_toggle_editorbar_sidebar,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_view.append(editorbar.menu_func)

    wm = bpy.context.window_manager
    if wm:
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name='Window', space_type='EMPTY')
            kmi = km.keymap_items.new(
                idname='editorbar.toggle_sidebar',
                type='N',
                value='PRESS',
                shift=True,
                alt=True,
            )
            editorbar.addon_keymaps.append((km, kmi))


def unregister():
    bpy.types.VIEW3D_MT_view.remove(editorbar.menu_func)

    for km, kmi in editorbar.addon_keymaps:
        km.keymap_items.remove(kmi)
    editorbar.addon_keymaps.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
