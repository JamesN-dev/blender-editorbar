from collections.abc import Sequence
from typing import Any, cast

import bpy


class EditorTogglePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    sidebar_side = bpy.props.EnumProperty(
        name='Sidebar Side',
        description='Choose which side to create sidebar',
        items=[('LEFT', 'Left', ''), ('RIGHT', 'Right', '')],
        default='RIGHT',
    )
    split_factor = bpy.props.FloatProperty(
        name='Sidebar Width',
        description='Proportion of window width for sidebar',
        min=0.1,
        max=0.5,
        default=0.173,
    )
    stack_ratio = bpy.props.FloatProperty(
        name='Stack Height Ratio',
        description='Proportion of sidebar height for Properties',
        min=0.5,
        max=0.9,
        default=0.66,
    )
    flip_editors = bpy.props.BoolProperty(
        name='Flip Editors Vertically',
        description='Outliner on bottom, Properties on top',
        default=False,
    )

    def draw(self, context):
        print('=== EditorBar Preferences draw() called ===')
        layout = self.layout
        layout.label(text='EditorBar Preferences')
        layout.prop(self, 'sidebar_side')
        layout.prop(self, 'split_factor')
        layout.prop(self, 'stack_ratio')
        layout.prop(self, 'flip_editors')


def get_rightmost_area(areas: Sequence[bpy.types.Area]) -> bpy.types.Area:
    return max(areas, key=lambda a: a.x + a.width)


def has_sidebar_editors(screen: bpy.types.Screen) -> bool:
    """Check if Outliner or Properties editors exist."""
    return any(a.type in {'OUTLINER', 'PROPERTIES'} for a in screen.areas)


def close_sidebars(screen: bpy.types.Screen, window: bpy.types.Window) -> None:
    """Close all sidebar editors."""
    for area_type in ['OUTLINER', 'PROPERTIES']:
        areas = [a for a in screen.areas if a.type == area_type]
        if areas:
            area = get_rightmost_area(areas)
            override = {'window': window, 'screen': screen, 'area': area}
            with cast(Any, bpy.context).temp_override(**override):
                bpy.ops.screen.area_close()


def get_editorbar_prefs(context: bpy.types.Context) -> Any:
    """Get EditorBar preferences with fallback to defaults."""
    try:
        return context.preferences.addons['editorbar'].preferences
    except (KeyError, AttributeError):
        # Return a simple object with default values if preferences not found
        class DefaultPrefs:
            sidebar_side: str = 'RIGHT'
            split_factor: float = 0.173
            stack_ratio: float = 0.66
            flip_editors: bool = False

        return DefaultPrefs()


def restore_sidebars(
    screen: bpy.types.Screen, window: bpy.types.Window, context: bpy.types.Context
) -> bool:
    """Restore sidebar editors using user preferences."""
    prefs = get_editorbar_prefs(context)

    sidebar_side = prefs.sidebar_side
    split_factor = prefs.split_factor
    stack_ratio = prefs.stack_ratio
    flip_editors = prefs.flip_editors

    # Choose split value based on sidebar side
    split_value = 1.0 - split_factor if sidebar_side == 'RIGHT' else split_factor

    main_areas = [
        a
        for a in screen.areas
        if a.type not in {'OUTLINER', 'PROPERTIES', 'DOPESHEET_EDITOR'}
    ]
    if not main_areas:
        return False

    base_area = get_rightmost_area(main_areas)
    override = {'window': window, 'area': base_area}

    with cast(Any, bpy.context).temp_override(**override):
        bpy.ops.screen.area_split(direction='VERTICAL', factor=split_value)

    sidebar_area = screen.areas[-1]
    sidebar_area.type = 'OUTLINER'
    sidebar_area.tag_redraw()

    # Use stack_ratio for the horizontal split
    bpy.app.timers.register(
        lambda: split_for_properties(screen, window, stack_ratio, flip_editors),
        first_interval=0.2,
    )

    return True


def split_for_properties(
    screen: bpy.types.Screen,
    window: bpy.types.Window,
    stack_ratio: float,
    flip_editors: bool,
) -> float | None:
    """Timer callback to split Outliner area for Properties."""
    outliner_areas = [a for a in screen.areas if a.type == 'OUTLINER']
    if not outliner_areas:
        return None

    original_area = get_rightmost_area(outliner_areas)

    if original_area.height < 200:
        return None

    # Copy the areas list BEFORE splitting
    areas_before = screen.areas[:]

    override = {'window': window, 'area': original_area}
    with cast(Any, bpy.context).temp_override(**override):
        bpy.ops.screen.area_split(
            direction='HORIZONTAL',
            factor=stack_ratio,
        )

    # Find the NEW area
    new_area = None
    for area in screen.areas:
        if area not in areas_before:
            new_area = area
            break

    if new_area:
        if flip_editors:
            # Flip: Properties on top, Outliner on bottom
            new_area.type = 'PROPERTIES'
            original_area.type = 'OUTLINER'
        else:
            # Default: Outliner on top, Properties on bottom
            new_area.type = 'OUTLINER'
            original_area.type = 'PROPERTIES'

        new_area.tag_redraw()
        original_area.tag_redraw()

    return None


class EDITORBAR_OT_toggle_sidebar(bpy.types.Operator):
    bl_idname = 'editorbar.toggle_sidebar'
    bl_label = 'Toggle EditorBar Sidebar'
    bl_description = 'Toggle the EditorBar sidebar'

    def execute(self, context: bpy.types.Context) -> set[str]:
        window = context.window
        assert window is not None
        screen = window.screen

        if has_sidebar_editors(screen):
            close_sidebars(screen, window)
        else:
            restore_sidebars(screen, window, context)

        return {'FINISHED'}


class EDITORBAR_OT_debug_prefs(bpy.types.Operator):
    bl_idname = 'editorbar.debug_prefs'
    bl_label = 'Debug EditorBar Preferences'
    bl_description = 'Print EditorBar preferences to console'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        prefs = get_editorbar_prefs(context)
        info = f'Sidebar Side: {prefs.sidebar_side}, Split: {prefs.split_factor}, Stack: {prefs.stack_ratio}, Flip: {prefs.flip_editors}'
        self.report({'INFO'}, info)
        print('=== EditorBar Preferences Debug ===')
        print(info)
        return {'FINISHED'}


class VIEW3D_PT_toggle_editorbar_sidebar(bpy.types.Panel):
    bl_label = 'Toggle EditorBar Sidebar'
    bl_idname = 'VIEW3D_PT_toggle_editorbar_sidebar'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'View'

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.operator('editorbar.toggle_sidebar', icon='HIDE_OFF')  # type: ignore[reportOptionalMemberAccess]


def menu_func(self: Any, context: bpy.types.Context) -> None:
    self.layout.operator('editorbar.toggle_sidebar', text='Toggle Sidebar')


addon_keymaps: Any = []


def register() -> None:
    bpy.utils.register_class(EDITORBAR_OT_toggle_sidebar)
    bpy.utils.register_class(VIEW3D_PT_toggle_editorbar_sidebar)
    bpy.types.VIEW3D_MT_view.append(menu_func)
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
            addon_keymaps.append((km, kmi))


def unregister() -> None:
    bpy.types.VIEW3D_MT_view.remove(menu_func)
    bpy.utils.unregister_class(VIEW3D_PT_toggle_editorbar_sidebar)
    bpy.utils.unregister_class(EDITORBAR_OT_toggle_sidebar)
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
