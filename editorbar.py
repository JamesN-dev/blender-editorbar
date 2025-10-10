from collections.abc import Sequence
from functools import partial
from typing import Any, ClassVar, cast

import bpy
from bpy.types import Operator, Panel

# Global reference to track the split timer
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
            override = {'window': window, 'area': area}
            with cast(Any, bpy.context).temp_override(**override):
                bpy.ops.screen.area_close()


def map_split_factor(normalized: float) -> float:
    """Map normalized 0-1 value to actual split factor (0.1 to 0.5)."""
    return 0.1 + (normalized * 0.4)  # 0 -> 0.1, 1 -> 0.5


def map_stack_ratio(normalized: float) -> float:
    """Map normalized 0-1 value to actual stack ratio (0.5 to 0.9)."""
    return 0.5 + (normalized * 0.4)  # 0 -> 0.5, 1 -> 0.9


def get_editorbar_prefs(context: bpy.types.Context) -> Any:
    """Get EditorBar preferences with fallback to defaults."""
    try:
        return context.preferences.addons[__package__].preferences  # type: ignore[index]
    except (KeyError, AttributeError):
        # Return a simple object with default values if preferences not found
        class DefaultPrefs:
            sidebar_side: str = 'RIGHT'
            split_factor: float = 0.35  # Normalized value
            stack_ratio: float = 0.32  # Normalized value
            flip_editors: bool = False

        return DefaultPrefs()


def restore_sidebars(
    screen: bpy.types.Screen, window: bpy.types.Window, context: bpy.types.Context
) -> bool:
    """Restore sidebar editors using user preferences."""
    prefs = get_editorbar_prefs(context)

    sidebar_side = prefs.sidebar_side
    # Map normalized 0-1 values to actual ranges
    split_factor = map_split_factor(prefs.split_factor)
    stack_ratio = map_stack_ratio(prefs.stack_ratio)
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
    # Cancel any existing timer first to prevent multiple sidebars
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


class EDITORBAR_OT_toggle_sidebar(Operator):
    bl_idname: ClassVar[str] = 'editorbar.toggle_sidebar'
    bl_label: ClassVar[str] = 'Toggle EditorBar Sidebar'
    bl_description: ClassVar[str] = 'Toggle the EditorBar sidebar'

    def execute(self, context: bpy.types.Context) -> set[str]:
        # Strict area check - MUST be in VIEW_3D only
        area = getattr(context, 'area', None)
        if not area or area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'EditorBar only works in 3D Viewport')
            return {'CANCELLED'}

        # Extra check: explicitly block PREFERENCES and other non-viewport areas
        if area.type == 'PREFERENCES':
            return {'CANCELLED'}

        window = context.window
        assert window is not None
        screen = window.screen

        if has_sidebar_editors(screen):
            close_sidebars(screen, window)
        else:
            restore_sidebars(screen, window, context)

        return {'FINISHED'}


class EDITORBAR_OT_flip_side(Operator):
    bl_idname: ClassVar[str] = 'editorbar.flip_side'
    bl_label: ClassVar[str] = 'Flip Side'
    bl_description: ClassVar[str] = 'Toggle sidebar between left and right'
    bl_options: ClassVar[set[str]] = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        # Strict area check - MUST be in VIEW_3D only
        area = getattr(context, 'area', None)
        if not area or area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'EditorBar only works in 3D Viewport')
            return {'CANCELLED'}

        prefs = get_editorbar_prefs(context)
        # Toggle between LEFT and RIGHT
        prefs.sidebar_side = 'LEFT' if prefs.sidebar_side == 'RIGHT' else 'RIGHT'

        self.report({'INFO'}, f'Sidebar moved to {prefs.sidebar_side.lower()}')
        return {'FINISHED'}


class EDITORBAR_OT_flip_stack(Operator):
    bl_idname: ClassVar[str] = 'editorbar.flip_stack'
    bl_label: ClassVar[str] = 'Flip Stack'
    bl_description: ClassVar[str] = 'Toggle stacking order (Outliner/Properties)'
    bl_options: ClassVar[set[str]] = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        # Strict area check - MUST be in VIEW_3D only
        area = getattr(context, 'area', None)
        if not area or area.type != 'VIEW_3D':
            self.report({'WARNING'}, 'EditorBar only works in 3D Viewport')
            return {'CANCELLED'}

        prefs = get_editorbar_prefs(context)
        # Toggle flip_editors
        prefs.flip_editors = not prefs.flip_editors

        order = (
            'Outliner bottom, Properties top'
            if prefs.flip_editors
            else 'Properties bottom, Outliner top'
        )
        self.report({'INFO'}, f'Stack flipped: {order}')
        return {'FINISHED'}


class EDITORBAR_OT_debug_prefs(Operator):
    bl_idname: ClassVar[str] = 'editorbar.debug_prefs'
    bl_label: ClassVar[str] = 'Debug EditorBar Preferences'
    bl_description: ClassVar[str] = 'Print EditorBar preferences to console'
    bl_options: ClassVar[set[str]] = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        prefs = get_editorbar_prefs(context)
        info = f'Sidebar Side: {prefs.sidebar_side}, Split: {prefs.split_factor}, Stack: {prefs.stack_ratio}, Flip: {prefs.flip_editors}'
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
        layout = self.layout

        # Three buttons in a row
        row = layout.row(align=True)
        row.operator('editorbar.toggle_sidebar', icon='HIDE_OFF')  # type: ignore[reportOptionalMemberAccess]
        row.operator('editorbar.flip_side', icon='ARROW_LEFTRIGHT')  # type: ignore[reportOptionalMemberAccess]
        row.operator('editorbar.flip_stack', icon='UV_SYNC_SELECT')  # type: ignore[reportOptionalMemberAccess]

        # Reset button
        layout.operator(
            'editorbar.reset_preferences', text='Reset to Defaults', icon='LOOP_BACK'
        )  # type: ignore[reportOptionalMemberAccess]


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
