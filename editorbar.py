from collections.abc import Sequence
from typing import Any, cast

import bpy

bl_info = {
    'name': 'Blender EditorBar',
    'author': 'atetraxx',
    'version': (1, 0),
    'blender': (4, 5, 0),
    'location': 'View3D > Sidebar > View Tab',
    'description': 'Turns the default Outliner and Properties editors in Blender workspaces into a sidebar that you can quickly collapse and expand',
    'warning': '',
    'category': 'UI',
}


class EditorTogglePreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    sidebar_side: Any = bpy.props.EnumProperty(
        name='Sidebar Side',
        description='Choose which side to create sidebar',
        items=[('LEFT', 'Left', ''), ('RIGHT', 'Right', '')],
        default='RIGHT',
    )
    split_factor: Any = bpy.props.FloatProperty(
        name='Sidebar Width',
        description='Proportion of window width for sidebar',
        min=0.1,
        max=0.5,
        default=0.173,
    )
    stack_ratio: Any = bpy.props.FloatProperty(
        name='Stack Height Ratio',
        description='Proportion of sidebar height for Properties',
        min=0.5,
        max=0.9,
        default=0.66,
    )
    flip_editors: Any = bpy.props.BoolProperty(
        name='Flip Editors Vertically',
        description='Outliner on bottom, Properties on top',
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'sidebar_side')
        layout.prop(self, 'split_factor')
        layout.prop(self, 'stack_ratio')
        layout.prop(self, 'flip_editors')


SIDEBAR_WIDTH_FACTOR: float = 0.173
PROPERTIES_HEIGHT_FACTOR: float = 0.66


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


def restore_sidebars(screen: bpy.types.Screen, window: bpy.types.Window) -> bool:
    """Restore sidebar editors."""
    # Find the rightmost non-sidebar area to split from
    main_areas = [
        a
        for a in screen.areas
        if a.type not in {'OUTLINER', 'PROPERTIES', 'DOPESHEET_EDITOR'}
    ]
    if not main_areas:
        return False

    base_area = get_rightmost_area(main_areas)
    override = {'window': window, 'area': base_area}

    # First split: create OUTLINER sidebar
    with cast(Any, bpy.context).temp_override(**override):
        bpy.ops.screen.area_split(
            direction='VERTICAL', factor=1.0 - SIDEBAR_WIDTH_FACTOR
        )

    # Get the newly created sidebar and set it to OUTLINER
    sidebar_area = screen.areas[-1]
    sidebar_area.type = 'OUTLINER'
    sidebar_area.tag_redraw()

    # Second split: add Properties below Outliner (needs timer delay)
    bpy.app.timers.register(
        lambda: split_for_properties(screen, window), first_interval=0.2
    )

    return True


def split_for_properties(
    screen: bpy.types.Screen, window: bpy.types.Window
) -> float | None:
    """Timer callback to split Outliner area for Properties below."""
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
            factor=PROPERTIES_HEIGHT_FACTOR,
        )

    # Find the NEW area
    new_area = None
    for area in screen.areas:
        if area not in areas_before:
            new_area = area
            break

    if new_area:
        # NEW area at bottom (34%) = OUTLINER
        new_area.type = 'OUTLINER'
        # ORIGINAL area at top (66%) = PROPERTIES
        original_area.type = 'PROPERTIES'

        new_area.tag_redraw()
        original_area.tag_redraw()

    return None


class WM_OT_toggle_outliner_properties(bpy.types.Operator):
    bl_idname = 'wm.toggle_outliner_properties'
    bl_label = 'Toggle Outliner/Properties'
    bl_description = 'Toggle the Outliner/Properties editor sidebars'

    def execute(self, context: bpy.types.Context) -> set[str]:
        window = context.window
        assert window is not None
        screen = window.screen

        if has_sidebar_editors(screen):
            close_sidebars(screen, window)
        else:
            restore_sidebars(screen, window)

        return {'FINISHED'}


class VIEW3D_PT_toggle_outliner_props(bpy.types.Panel):
    bl_label = 'Toggle Outliner/Properties'
    bl_idname = 'VIEW3D_PT_toggle_outliner_props'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'View'

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.operator('wm.toggle_outliner_properties', icon='HIDE_OFF')  # type: ignore[reportOptionalMemberAccess]


def menu_func(self: Any, context: bpy.types.Context) -> None:
    self.layout.operator('wm.toggle_outliner_properties', text='Toggle Sidebar')


addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


def register() -> None:
    bpy.utils.register_class(WM_OT_toggle_outliner_properties)
    bpy.utils.register_class(VIEW3D_PT_toggle_outliner_props)
    bpy.types.VIEW3D_MT_view.append(menu_func)
    wm = bpy.context.window_manager
    if wm:
        kc = wm.keyconfigs.addon
        if kc:
            km = kc.keymaps.new(name='Window', space_type='EMPTY')
            kmi = km.keymap_items.new(
                idname='wm.toggle_outliner_properties',
                type='N',
                value='PRESS',
                shift=True,
                alt=True,
            )
            addon_keymaps.append((km, kmi))


def unregister() -> None:
    bpy.types.VIEW3D_MT_view.remove(menu_func)
    bpy.utils.unregister_class(VIEW3D_PT_toggle_outliner_props)
    bpy.utils.unregister_class(WM_OT_toggle_outliner_properties)
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
