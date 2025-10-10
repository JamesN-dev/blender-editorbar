from typing import ClassVar

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import AddonPreferences

bl_info = {
    'name': 'EditorBar',
    'author': 'atetraxx',
    'version': (0, 3, 1),
    'blender': (4, 2, 0),
    'location': 'View3D > Sidebar > View Tab',
    'description': 'Turns the default Outliner and Properties editors in Blender workspaces into a sidebar that you can quickly collapse and expand',
    'warning': '',
    'category': 'UI',
}

# Default values as constants
DEFAULT_LEFT_SIDEBAR = False  # False = RIGHT, True = LEFT
DEFAULT_SPLIT_FACTOR = 40  # Default slider: 40 = 19% actual width
DEFAULT_STACK_RATIO = 66  # Actual percentage (10-90%) - properties height
DEFAULT_FLIP_EDITORS = False


class EditorBarPreferenceMonitor:
    """Monitors preference changes and applies them to VIEW_3D areas when preferences are open.

    This implements a timer-based monitoring system that:
    - Starts when the EditorBar preferences panel is drawn
    - Polls for changes every 150ms while preferences are open
    - Applies changes to VIEW_3D areas in real-time
    - Stops automatically when preferences are closed
    - Provides minimal performance overhead
    """

    def __init__(self):
        self._timer_active = False
        self._last_prefs = {}
        self._debug = True  # TEMPORARY: Debug enabled to diagnose slider issue
        self._debounce_delay = 0.15  # Wait 150ms after last change before applying

    def activate_monitoring(self):
        """Start monitoring when preferences UI is drawn."""
        if not self._timer_active and self._is_preferences_context():
            self._start_timer()

    def schedule_immediate_update(self):
        """Schedule a debounced update - cancels previous pending updates."""
        # Unregister any pending update to prevent rapid-fire updates
        if bpy.app.timers.is_registered(self._immediate_update):
            bpy.app.timers.unregister(self._immediate_update)
            if self._debug:
                print('[EditorBar] Cancelled previous pending update')

        # Schedule new update with debounce delay
        bpy.app.timers.register(
            self._immediate_update, first_interval=self._debounce_delay
        )
        if self._debug:
            print(f'[EditorBar] Scheduled debounced update ({self._debounce_delay}s)')

    def _start_timer(self):
        """Start the preference monitoring timer."""
        if not self._timer_active:
            self._timer_active = True
            if not bpy.app.timers.is_registered(self._timer_callback):
                bpy.app.timers.register(self._timer_callback, first_interval=0.1)
                if self._debug:
                    print('[EditorBar] Timer started')

    def _stop_timer(self):
        """Stop the preference monitoring timer."""
        if self._timer_active:
            self._timer_active = False
            if bpy.app.timers.is_registered(self._timer_callback):
                bpy.app.timers.unregister(self._timer_callback)
                if self._debug:
                    print('[EditorBar] Timer stopped')

    def cleanup(self):
        """Clean up all timers (called on unregister)."""
        self._stop_timer()
        if bpy.app.timers.is_registered(self._immediate_update):
            bpy.app.timers.unregister(self._immediate_update)

    def _is_preferences_context(self):
        """Check if we're in preferences and likely viewing EditorBar addon."""
        try:
            context = bpy.context
            if not context.area or context.area.type != 'PREFERENCES':
                return False
            if not context.preferences or not hasattr(context.preferences, 'addons'):
                return False
            # Check if our package is registered (ignore type check for dynamic addon dict)
            package = __package__
            if not package:
                return False
            return package in context.preferences.addons  # type: ignore[operator]
        except Exception:
            return False

    def _timer_callback(self):
        """Main timer callback - checks for changes and updates VIEW_3D."""
        # Stop timer if no longer in preferences
        if not self._is_preferences_context():
            if self._debug:
                print('[EditorBar] Not in preferences context, stopping timer')
            self._stop_timer()
            return None

        # Check for preference changes
        try:
            if not bpy.context.preferences or not hasattr(
                bpy.context.preferences, 'addons'
            ):
                return 0.15
            addon_prefs = bpy.context.preferences.addons[__package__].preferences  # type: ignore[index]
            current_prefs = {
                'left_sidebar': addon_prefs.left_sidebar,
                'split_factor': addon_prefs.split_factor,
                'stack_ratio': addon_prefs.stack_ratio,
                'flip_editors': addon_prefs.flip_editors,
            }

            if current_prefs != self._last_prefs:
                if self._debug:
                    print(f'[EditorBar] Preferences changed: {current_prefs}')
                self._last_prefs = current_prefs.copy()
                # Use debounced update to prevent rapid-fire changes
                self.schedule_immediate_update()
        except Exception:
            pass

        return 0.15  # Continue every 150ms

    def _immediate_update(self):
        """Immediate one-time update."""
        self._update_viewports()
        return None  # Run once

    def _update_viewports(self):
        """Apply changes to all VIEW_3D areas with sidebars."""
        try:
            # Import here to avoid circular dependencies
            from . import editorbar

            # Find VIEW_3D areas and check if sidebar exists
            screen = bpy.context.screen
            if not screen:
                if self._debug:
                    print('[EditorBar] No screen context available')
                return

            # Only update if sidebars actually exist
            if editorbar.has_sidebar_editors(screen):
                if self._debug:
                    print('[EditorBar] Updating viewports with new preferences')
                window = bpy.context.window
                if window:
                    # Close and reopen with new settings
                    editorbar.close_sidebars(screen, window)
                    editorbar.restore_sidebars(screen, window, bpy.context)
        except Exception:
            # Silently fail to avoid console spam during normal operations
            pass


# Global monitor instance
_preference_monitor = EditorBarPreferenceMonitor()


def on_sidebar_settings_update(self, context):
    """Update sidebar when settings change - debounced updates.

    This callback is triggered by property update= parameters.
    Uses debouncing to prevent rapid-fire updates while dragging sliders.
    """
    # Always use debounced update to prevent slider drag issues
    _preference_monitor.schedule_immediate_update()


class EditorBarPreferences(AddonPreferences):
    bl_idname = __package__  # type: ignore[assignment]

    left_sidebar: BoolProperty(
        name='Left Sidebar',
        description='Place sidebar on left side (unchecked = right side)',
        default=DEFAULT_LEFT_SIDEBAR,
        update=on_sidebar_settings_update,
    )
    split_factor: IntProperty(
        name='Sidebar Width',
        description='Sidebar width percentage (10-49%)',
        min=10,
        max=49,
        default=DEFAULT_SPLIT_FACTOR,
        subtype='PERCENTAGE',
        update=on_sidebar_settings_update,
    )

    stack_ratio: IntProperty(
        name='Stack Height Ratio',
        description='Properties panel height percentage (10-90%)',
        min=10,
        max=90,
        default=DEFAULT_STACK_RATIO,
        subtype='PERCENTAGE',
        update=on_sidebar_settings_update,
    )
    flip_editors: BoolProperty(
        name='Flip Editors Vertically',
        description='Outliner on bottom, Properties on top',
        default=DEFAULT_FLIP_EDITORS,
        update=on_sidebar_settings_update,
    )

    def draw(self, context):
        # Activate monitoring when preferences panel is drawn
        _preference_monitor.activate_monitoring()

        layout = self.layout
        layout.label(text='EditorBar Preferences')

        layout.separator()

        # Main controls with checkmarks
        col = layout.column()

        # Sidebar side with dynamic text
        row = col.row()
        side_text = 'Move to Right' if self.left_sidebar else 'Move to Left'
        row.label(text=side_text)
        row.prop(self, 'left_sidebar', text='')

        # Flip stack with checkmark
        row = col.row()
        flip_text = (
            'Outliner Bottom, Properties Top'
            if self.flip_editors
            else 'Properties Bottom, Outliner Top'
        )
        row.label(text=flip_text)
        row.prop(self, 'flip_editors', text='')

        layout.separator()

        # Width slider with reversed direction (left=wider, right=narrower)
        col = layout.column()

        # Calculate actual width using reversed mapping
        from .editorbar import map_split_factor, map_stack_ratio

        actual_width_percent = int(map_split_factor(self.split_factor) * 100)
        actual_height_percent = int(map_stack_ratio(self.stack_ratio) * 100)

        col = layout.column()
        col.prop(
            self,
            'split_factor',
            text=f'Sidebar Width ({actual_width_percent}%)',
            slider=True,
        )
        layout.separator()
        col.prop(
            self,
            'stack_ratio',
            text=f'Properties Height ({actual_height_percent}%)',
            slider=True,
        )
        layout.separator()
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

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences  # type: ignore[index]
        # Get default values directly from property definitions
        for prop in ['split_factor', 'stack_ratio', 'left_sidebar', 'flip_editors']:
            default_value = type(prefs).bl_rna.properties[prop].default
            setattr(prefs, prop, default_value)
        # Trigger immediate update to apply changes
        on_sidebar_settings_update(prefs, context)
        self.report({'INFO'}, 'EditorBar preferences reset to defaults')
        return {'FINISHED'}


# Classes to register
classes: list[type] = [
    EditorBarPreferences,
    EDITORBAR_OT_reset_preferences,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    editorbar.register()


def unregister():
    # Clean up preference monitor timers before unregistering
    _preference_monitor.cleanup()
    editorbar.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
