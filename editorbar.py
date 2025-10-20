from collections.abc import Sequence
from functools import partial
from typing import Any, ClassVar, cast

import bpy
from bpy.types import Operator, Panel

from . import version_adapter

_split_timer_func = None


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
            # Use safe wrapper to prevent crashes on 4.2
            version_adapter.safe_area_close(screen, window, area)


def map_split_factor(slider_value: float) -> float:
    """Convert percentage to split factor."""
    return slider_value / 100.0


def map_stack_ratio(percentage: int) -> float:
    """Convert percentage to stack ratio."""
    return percentage / 100.0


def get_editorbar_prefs(context: bpy.types.Context) -> Any:
    """Get EditorBar preferences with fallback to defaults."""
    try:
        prefs_obj = cast(Any, cast(Any, context).preferences)
        addons = getattr(prefs_obj, 'addons', None)
        pkg = __package__ or ''
        if addons and pkg in addons:
            return addons[pkg].preferences  # type: ignore[index]
    except Exception:
        pass

        class DefaultPrefs:
            left_sidebar: bool = False
            split_factor: int = 19
            stack_ratio: int = 66
            flip_editors: bool = False

        return DefaultPrefs()


def restore_sidebars(
    screen: bpy.types.Screen, window: bpy.types.Window, context: bpy.types.Context
) -> bool:
    """Restore sidebar editors using user preferences."""
    prefs = get_editorbar_prefs(context)

    left_sidebar = prefs.left_sidebar
    # Reverse width: slider shows 10-49, but we invert so left=wider, right=narrower
    split_factor = map_split_factor(59.0 - prefs.split_factor)
    stack_ratio = map_stack_ratio(prefs.stack_ratio)
    flip_editors = prefs.flip_editors

    split_value = split_factor if left_sidebar else 1.0 - split_factor

    main_areas = [
        a
        for a in screen.areas
        if a.type not in {'OUTLINER', 'PROPERTIES', 'DOPESHEET_EDITOR'}
    ]
    if not main_areas:
        return False

    base_area = get_rightmost_area(main_areas)
    # Use safe wrapper to split the area
    split_success = version_adapter.safe_area_split(
        screen, window, base_area, 'VERTICAL', split_value
    )

    if not split_success:
        return False

    sidebar_area = screen.areas[-1]
    version_adapter.safe_change_area_type(sidebar_area, 'OUTLINER')

    global _split_timer_func
    if _split_timer_func and bpy.app.timers.is_registered(_split_timer_func):
        bpy.app.timers.unregister(_split_timer_func)

    _split_timer_func = partial(
        split_for_properties, screen, window, stack_ratio, flip_editors
    )
    bpy.app.timers.register(_split_timer_func, first_interval=0.2)

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

    areas_before = screen.areas[:]

    # Compute split factor from stack_ratio only - flip_editors doesn't affect slider behavior
    split_factor = stack_ratio
    # Avoid ambiguous 0.5 edge case by nudging slightly
    if abs(split_factor - 0.5) < 1e-6:
        split_factor = 0.501

    # Use safe wrapper to split the area
    split_success = version_adapter.safe_area_split(
        screen, window, original_area, 'HORIZONTAL', split_factor
    )

    if not split_success:
        return None

    new_area = None
    for area in screen.areas:
        if area not in areas_before:
            new_area = area
            break

    if not new_area:
        return None

    # Determine top/bottom by Y coordinate - larger Y is higher on screen
    if new_area.y > original_area.y:
        top_area, bottom_area = new_area, original_area
    else:
        top_area, bottom_area = original_area, new_area

    if flip_editors:
        # Properties bottom, Outliner top
        version_adapter.safe_change_area_type(top_area, 'OUTLINER')
        version_adapter.safe_change_area_type(bottom_area, 'PROPERTIES')
    else:
        # Outliner bottom, Properties top
        version_adapter.safe_change_area_type(top_area, 'PROPERTIES')
        version_adapter.safe_change_area_type(bottom_area, 'OUTLINER')

    return None


class EDITORBAR_OT_toggle_sidebar(Operator):
    bl_idname: ClassVar[str] = 'editorbar.toggle_sidebar'
    bl_label: ClassVar[str] = 'Toggle EditorBar Sidebar'
    bl_description: ClassVar[str] = 'Toggle the EditorBar sidebar'

    def execute(self, context: bpy.types.Context) -> set[str]:
        # Validate context before any operations
        area = getattr(context, 'area', None)
        if not area or area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'EditorBar only works in 3D Viewport')
            return {'CANCELLED'}

        if area.type == 'PREFERENCES':
            return {'CANCELLED'}

        window = context.window
        if not window:
            self.report({'WARNING'}, 'No valid window context')
            return {'CANCELLED'}

        screen = window.screen
        if not screen:
            self.report({'WARNING'}, 'No valid screen context')
            return {'CANCELLED'}

        # Additional validation for safe context
        if not version_adapter.check_area(window, screen, area):
            self.report({'WARNING'}, 'Context not safe for area operations')
            return {'CANCELLED'}

        try:
            if has_sidebar_editors(screen):
                close_sidebars(screen, window)
            else:
                restore_sidebars(screen, window, context)
        except Exception as e:
            self.report({'ERROR'}, f'Failed to toggle sidebar: {e}')
            return {'CANCELLED'}

        return {'FINISHED'}


class EDITORBAR_OT_flip_side(Operator):
    bl_idname: ClassVar[str] = 'editorbar.flip_side'
    bl_label: ClassVar[str] = 'Flip Side'
    bl_description: ClassVar[str] = 'Toggle sidebar between left and right'
    bl_options: ClassVar[set[str]] = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        area = getattr(context, 'area', None)
        if not area or area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'EditorBar only works in 3D Viewport')
            return {'CANCELLED'}

        window = context.window
        if not window:
            self.report({'WARNING'}, 'No valid window context')
            return {'CANCELLED'}

        screen = window.screen
        if not screen:
            self.report({'WARNING'}, 'No valid screen context')
            return {'CANCELLED'}

        try:
            prefs = get_editorbar_prefs(context)
            prefs.left_sidebar = not prefs.left_sidebar

            side = 'left' if prefs.left_sidebar else 'right'
            self.report({'INFO'}, f'Sidebar moved to {side}')
        except Exception as e:
            self.report({'ERROR'}, f'Failed to flip side: {e}')
            return {'CANCELLED'}

        return {'FINISHED'}


class EDITORBAR_OT_flip_stack(Operator):
    bl_idname: ClassVar[str] = 'editorbar.flip_stack'
    bl_label: ClassVar[str] = 'Flip Stack'
    bl_description: ClassVar[str] = 'Toggle stacking order (Outliner/Properties)'
    bl_options: ClassVar[set[str]] = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        area = getattr(context, 'area', None)
        if not area or area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'EditorBar only works in 3D Viewport')
            return {'CANCELLED'}

        window = context.window
        if not window:
            self.report({'WARNING'}, 'No valid window context')
            return {'CANCELLED'}

        screen = window.screen
        if not screen:
            self.report({'WARNING'}, 'No valid screen context')
            return {'CANCELLED'}

        try:
            prefs = get_editorbar_prefs(context)
            prefs.flip_editors = not prefs.flip_editors

            order = (
                'Properties bottom, Outliner top'
                if prefs.flip_editors
                else 'Outliner bottom, Properties top'
            )
            self.report({'INFO'}, f'Stack flipped: {order}')
        except Exception as e:
            self.report({'ERROR'}, f'Failed to flip stack: {e}')
            return {'CANCELLED'}

        return {'FINISHED'}


class EDITORBAR_OT_debug_prefs(Operator):
    bl_idname: ClassVar[str] = 'editorbar.debug_prefs'
    bl_label: ClassVar[str] = 'Debug EditorBar Preferences'
    bl_description: ClassVar[str] = 'Print EditorBar preferences to console'
    bl_options: ClassVar[set[str]] = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        prefs = get_editorbar_prefs(context)
        side = 'left' if prefs.left_sidebar else 'right'
        info = f'Sidebar Side: {side}, Split: {prefs.split_factor}, Stack: {prefs.stack_ratio}, Flip: {prefs.flip_editors}'
        self.report({'INFO'}, info)
        print('=== EditorBar Preferences Debug ===')
        print(info)
        return {'FINISHED'}


class VIEW3D_PT_toggle_editorbar_sidebar(Panel):
    bl_label: ClassVar[str] = 'EditorBar'
    bl_idname: ClassVar[str] = 'VIEW3D_PT_toggle_editorbar_sidebar'
    bl_space_type: ClassVar[str] = 'VIEW_3D'
    bl_region_type: ClassVar[str] = 'UI'
    bl_category: ClassVar[str] = 'View'

    def draw(self, context: bpy.types.Context) -> None:
        layout = cast(Any, self.layout)

        row = layout.row(align=True)
        row.operator('editorbar.toggle_sidebar', icon='HIDE_OFF')  # type: ignore[reportOptionalMemberAccess]
        row.operator('editorbar.flip_side', icon='ARROW_LEFTRIGHT')  # type: ignore[reportOptionalMemberAccess]
        row.operator('editorbar.flip_stack', icon='UV_SYNC_SELECT')  # type: ignore[reportOptionalMemberAccess]

        layout.separator()  # type: ignore[reportOptionalMemberAccess]
        layout.operator(  # type: ignore[reportOptionalMemberAccess]
            'editorbar.reset_preferences', text='Reset to Defaults', icon='LOOP_BACK'
        )


def menu_func(self: Any, context: bpy.types.Context) -> None:
    self.layout.operator('editorbar.toggle_sidebar', text='Toggle Sidebar')


addon_keymaps: Any = []  # type: ignore[misc]


classes = [
    EDITORBAR_OT_toggle_sidebar,
    EDITORBAR_OT_flip_side,
    EDITORBAR_OT_flip_stack,
    EDITORBAR_OT_debug_prefs,
    VIEW3D_PT_toggle_editorbar_sidebar,
]


def register() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)
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
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
