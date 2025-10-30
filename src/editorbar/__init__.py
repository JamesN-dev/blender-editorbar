from sys import platform
from typing import Any, ClassVar, cast

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, FloatProperty
from bpy.types import AddonPreferences, Context

from . import version_adapter

bl_info = {
    'name': 'EditorBar',
    'author': 'atetraxx',
    'version': (0, 4, 7),
    'blender': (4, 2, 0),
    'location': 'View3D > Sidebar > View Tab',
    'description': 'Turns the default Outliner and Properties editors in Blender workspaces into a sidebar that you can quickly collapse and expand (Alt/CMD+Shift+N)',
    'warning': '',
    'category': 'UI',
}

# Default values
DEFAULT_LEFT_SIDEBAR = False
DEFAULT_SPLIT_FACTOR: float = (
    41.75  # Inverted slider for better UI: Dragging right widens the sidebar.
)
DEFAULT_STACK_RATIO: float = 66.0
DEFAULT_FLIP_EDITORS = False

S_MIN: float = 10.0
S_MAX: float = 49.0
S_SUM: float = S_MIN + S_MAX
APPLY_ON_STARTUP_DEFAULT = True


LOAD_POST_DELAY: float = 0.2  # Seconds to wait after file load
REGISTER_DELAY: float = 0.4  # Seconds to wait after addon registration


class EditorBarPreferenceMonitor:
    """Monitors preference changes and applies them to VIEW_3D areas when preferences are open.

    This implements a timer-based monitoring system that:
    - Starts when the EditorBar preferences panel is drawn
    - Polls for changes every 150ms while preferences are open
    - Applies changes to VIEW_3D areas in real-time
    - Stops automatically when preferences are closed
    - Provides minimal performance overhead
    """

    def __init__(self) -> None:
        self._timer_active: bool = False
        self._last_prefs: dict[str, bool | float] = {}
        self._debug: bool = False
        self._debounce_delay: float = 0.05
        self._poll_interval: float = 0.15

    def activate_monitoring(self) -> None:
        if not self._timer_active and self._is_preferences_context():
            self._start_timer()

    def schedule_immediate_update(self) -> None:
        """Schedule a debounced update - cancels previous pending updates."""
        if bpy.app.timers.is_registered(self._immediate_update):
            bpy.app.timers.unregister(self._immediate_update)
            if self._debug:
                print('[EditorBar] Cancelled previous pending update')

        bpy.app.timers.register(
            self._immediate_update, first_interval=self._debounce_delay
        )
        if self._debug:
            print(f'[EditorBar] Scheduled debounced update ({self._debounce_delay}s)')

    def _start_timer(self) -> None:
        if not self._timer_active:
            self._timer_active = True
            if not bpy.app.timers.is_registered(self._timer_callback):
                bpy.app.timers.register(self._timer_callback, first_interval=0.1)
                if self._debug:
                    print('[EditorBar] Timer started')

    def _stop_timer(self) -> None:
        if self._timer_active:
            self._timer_active = False
            if bpy.app.timers.is_registered(self._timer_callback):
                bpy.app.timers.unregister(self._timer_callback)
                if self._debug:
                    print('[EditorBar] Timer stopped')

    def cleanup(self) -> None:
        """Clean up all timers (called on unregister)."""
        self._stop_timer()
        if bpy.app.timers.is_registered(self._immediate_update):
            bpy.app.timers.unregister(self._immediate_update)

    def _is_preferences_context(self) -> bool:
        """Check if we're in preferences and likely viewing EditorBar addon."""
        try:
            context = bpy.context
            if not context.area or context.area.type != 'PREFERENCES':
                return False
            if not context.preferences or not hasattr(context.preferences, 'addons'):
                return False

            package: str | None = __package__
            if not package:
                return False
            return package in context.preferences.addons
        except Exception:
            return False

    def _timer_callback(self) -> float | None:
        """Main timer callback - checks for changes and updates VIEW_3D."""
        if not self._is_preferences_context():
            if self._debug:
                print('[EditorBar] Not in preferences context, stopping timer')
            self._stop_timer()
            return None

        if not version_adapter.validate_timer_context():
            if self._debug:
                print('[EditorBar] Invalid timer context, stopping')
            self._stop_timer()
            return None

        # Check for preference changes
        try:
            if not bpy.context.preferences or not hasattr(
                bpy.context.preferences, 'addons'
            ):
                return self._poll_interval
            # Safely get addon prefs
            addon_pkg = bpy.context.preferences.addons.get(__package__)
            if not addon_pkg:
                return self._poll_interval  # Safety check for unlikely edge case
            addon_prefs = cast('EditorBarPreferences', addon_pkg.preferences)
            current_prefs: dict[str, bool | float] = {
                'left_sidebar': addon_prefs.left_sidebar,
                'split_factor': addon_prefs.split_factor,
                'stack_ratio': addon_prefs.stack_ratio,
                'flip_editors': addon_prefs.flip_editors,
            }

            if current_prefs != self._last_prefs:
                if self._debug:
                    print(f'[EditorBar] Preferences changed: {current_prefs}')
                self._last_prefs = current_prefs.copy()
                self.schedule_immediate_update()
        except Exception as e:
            if self._debug:
                print(f'[EditorBar] Error checking preferences: {e}')

        return self._poll_interval

    def _immediate_update(self) -> None:
        self._update_viewports()

    def _update_viewports(self) -> None:
        """Apply changes to all VIEW_3D areas with sidebars."""
        try:
            if not version_adapter.validate_timer_context():
                if self._debug:
                    print('[EditorBar] Invalid context for viewport update')
                return

            # Import here to avoid circular dependencies
            from . import editorbar

            # Find VIEW_3D areas and check if sidebar exists
            screen = bpy.context.screen
            if not screen:
                if self._debug:
                    print('[EditorBar] No screen context available')
                return

            window = bpy.context.window
            if not window:
                if self._debug:
                    print('[EditorBar] No window context available')
                return

            if not hasattr(window, 'screen') or window.screen != screen:
                if self._debug:
                    print('[EditorBar] Window/screen context mismatch')
                return

            if editorbar.has_sidebar_editors(screen):
                if self._debug:
                    print('[EditorBar] Updating viewports with new preferences')
                editorbar.close_sidebars(screen, window)
                editorbar.restore_sidebars(screen, window, bpy.context)
        except Exception as e:
            if self._debug:
                print(f'[EditorBar] Viewport update error: {e}')


# Global monitor instance
_preference_monitor = EditorBarPreferenceMonitor()


def on_sidebar_settings_update(self, context: Context) -> None:
    """Update sidebar when settings change - debounced updates.

    This callback is triggered by property update= parameters.
    Uses debouncing to prevent rapid-fire updates while dragging sliders.
    """
    _preference_monitor.schedule_immediate_update()


class EditorBarPreferences(AddonPreferences):
    bl_idname = __package__

    left_sidebar: BoolProperty(
        name='Swap Sidebar Side',
        description='unchecked = right side',
        default=DEFAULT_LEFT_SIDEBAR,
        update=on_sidebar_settings_update,
    )
    split_factor_internal: FloatProperty(
        name='Sidebar Width (internal)',
        description='Internal inverted width storage',
        min=S_MIN,
        max=S_MAX,
        default=(S_SUM - DEFAULT_SPLIT_FACTOR),
        options={'HIDDEN'},
    )

    def _get_split(self) -> float:
        val = getattr(self, 'split_factor_internal', (S_SUM - DEFAULT_SPLIT_FACTOR))
        if val < S_MIN:
            val = S_MIN
        elif val > S_MAX:
            val = S_MAX
        return S_SUM - val

    def _set_split(self, value: float) -> None:
        if value < S_MIN:
            value = S_MIN
        elif value > S_MAX:
            value = S_MAX
        self.split_factor_internal = S_SUM - value

    split_factor: FloatProperty(
        name='Sidebar Width',
        description='Default = 41.75%',
        min=10.0,
        max=49.0,
        default=DEFAULT_SPLIT_FACTOR,
        get=_get_split,
        set=_set_split,
        precision=2,
        update=on_sidebar_settings_update,
    )

    stack_ratio: FloatProperty(
        name='Properties Height',
        description='Default = 66.00%',
        min=51.0,
        max=90.0,
        default=DEFAULT_STACK_RATIO,
        precision=2,
        update=on_sidebar_settings_update,
    )
    flip_editors: BoolProperty(
        name='Flip Editors Vertically',
        description='Check to swap stack',
        default=DEFAULT_FLIP_EDITORS,
        update=on_sidebar_settings_update,
    )
    applyOnStartup: BoolProperty(
        name='Apply on Blender Startup',
        description='Rebuild the EditorBar layout from these preferences whenever Blender opens',
        default=APPLY_ON_STARTUP_DEFAULT,
    )

    def draw(self, context: bpy.types.Context) -> None:
        _preference_monitor.activate_monitoring()

        layout = self.layout
        layout.label(text='EditorBar Preferences')
        if platform == 'darwin':
            layout.label(text='Shortcut: Option+Shift+N', icon='KEYINGSET')
        else:
            layout.label(text='Shortcut: Alt+Shift+N', icon='KEYINGSET')

        layout.separator()

        # Toggle checkboxes
        row = layout.row(align=True)
        row.prop(self, 'left_sidebar', text='Left Side')
        row.prop(self, 'flip_editors', text='Flip Stack')

        layout.separator()

        # Slider bars
        col = layout.column()
        col.prop(self, 'split_factor', text='Sidebar Width', slider=True)
        col.prop(self, 'stack_ratio', text='Properties Height', slider=True)

        layout.separator()

        # Other settings
        col = layout.column()
        col.prop(self, 'applyOnStartup', text='Apply on Blender Startup')
        layout.operator(
            'editorbar.reset_preferences', text='Reset to Defaults', icon='LOOP_BACK'
        )


if 'bpy' in locals():
    import importlib

    from . import editorbar

    importlib.reload(editorbar)
else:
    from . import editorbar


class EDITORBAR_OT_reset_preferences(bpy.types.Operator):
    bl_idname: ClassVar[str] = 'editorbar.reset_preferences'
    bl_label: ClassVar[str] = 'Reset to Defaults'
    bl_description: ClassVar[str] = 'Reset all EditorBar preferences to default values'
    bl_options: ClassVar[set[str]] = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        if not context.preferences:
            self.report({'WARNING'}, 'Could not access preferences.')
            return {'CANCELLED'}

        addon_pkg = context.preferences.addons.get(__package__)
        if not addon_pkg:
            self.report({'WARNING'}, 'Could not find addon preferences to reset.')
            return {'CANCELLED'}

        prefs = addon_pkg.preferences
        for prop in [
            'split_factor',
            'stack_ratio',
            'left_sidebar',
            'flip_editors',
        ]:
            default_value = type(prefs).bl_rna.properties[prop].default
            setattr(prefs, prop, default_value)

        on_sidebar_settings_update(prefs, context)
        self.report({'INFO'}, 'EditorBar preferences reset to defaults')
        return {'FINISHED'}


classes: list[type] = [
    EditorBarPreferences,
    EDITORBAR_OT_reset_preferences,
]


def applyPrefsOnce() -> None:
    try:
        from . import editorbar as _eb

        if not bpy.context.preferences:
            return None

        addon_pkg = bpy.context.preferences.addons.get(__package__)
        if not addon_pkg:
            return None
        prefs = addon_pkg.preferences

        if not getattr(prefs, 'applyOnStartup', True):
            return None

        wm = bpy.context.window_manager
        if not wm:
            return None

        for window in wm.windows:
            screen = window.screen
            if not screen:
                continue
            try:
                if _eb.has_sidebar_editors(screen):
                    _eb.close_sidebars(screen, window)
                _eb.restore_sidebars(screen, window, bpy.context)
            except Exception as e:
                version_adapter.debug_log(f'Apply-on-startup failed on a window: {e}')
        return None
    except Exception as e:
        version_adapter.debug_log(f'Apply-on-startup error: {e}')
        return None


@persistent
def onLoadPost(_dummy: Any) -> None:
    """Apply preferences each time a new .blend file is loaded."""
    bpy.app.timers.register(applyPrefsOnce, first_interval=LOAD_POST_DELAY)


def register() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)
    editorbar.register()

    if onLoadPost not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(onLoadPost)

    # Apply settings on initial startup and when the addon is enabled.
    bpy.app.timers.register(applyPrefsOnce, first_interval=REGISTER_DELAY)


def unregister() -> None:
    _preference_monitor.cleanup()

    if onLoadPost in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(onLoadPost)

    editorbar.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
