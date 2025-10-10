# EditorBar Preference Monitoring System

## Overview

This document describes the timer-based preference monitoring system implemented in EditorBar v0.2.0, which provides real-time live updates when editing addon preferences.

## Problem Statement

Blender's Python API has limitations when detecting addon preference panel state:

1. **No Direct Expansion Detection**: There's no built-in way to detect if a specific addon's preferences section is expanded vs collapsed.
2. **Context Limitations**: While `bpy.context.area.type` can detect the 'PREFERENCES' area, it cannot determine which specific addon panel is expanded.
3. **Update Callback Context**: Property `update=` callbacks are called when preferences change, but the context may not be `VIEW_3D`, limiting the ability to apply changes immediately.

## Solution Architecture

EditorBar implements a **hybrid approach** combining:

1. **Direct Updates**: When properties are changed in `VIEW_3D` context, updates are applied immediately via property `update=` callbacks.
2. **Timer-Based Monitoring**: When preferences are edited, a lightweight timer monitors for changes and applies them to `VIEW_3D` areas in real-time.

### Key Components

```
EditorBarPreferenceMonitor
├── Timer Management
│   ├── _start_timer()      # Start monitoring when preferences open
│   ├── _stop_timer()       # Stop when preferences close
│   └── cleanup()           # Clean up on addon unregister
├── Context Detection
│   └── _is_preferences_context()  # Detect if in preferences
├── Change Detection
│   └── _timer_callback()   # Poll for preference changes
└── Update Application
    ├── _immediate_update() # One-time scheduled update
    └── _update_viewports() # Apply changes to VIEW_3D areas
```

## How It Works

### 1. Activation

When the EditorBar preferences panel is drawn, the monitoring system activates:

```python
def draw(self, context):
    # Activate monitoring when preferences panel is drawn
    _preference_monitor.activate_monitoring()
    # ... rest of UI code
```

The monitor checks if we're in the preferences context and starts a timer if not already running.

### 2. Monitoring Loop

The timer runs at **150ms intervals** (configurable) and:

1. Checks if we're still in the preferences context
2. Reads current preference values
3. Compares with cached previous values
4. If changed, applies updates to `VIEW_3D` areas
5. Stops automatically when preferences are closed

```python
def _timer_callback(self):
    """Main timer callback - checks for changes and updates VIEW_3D."""
    if not self._is_preferences_context():
        self._stop_timer()
        return None  # Stop timer

    # Check for changes and update
    current_prefs = {...}
    if current_prefs != self._last_prefs:
        self._update_viewports()

    return 0.15  # Continue every 150ms
```

### 3. Update Application

When changes are detected:

1. Import the `editorbar` module (deferred to avoid circular imports)
2. Check if sidebar editors exist in the current screen
3. Close existing sidebars with old settings
4. Restore sidebars with new settings
5. All updates are wrapped in exception handling to prevent console spam

### 4. Cleanup

When the addon is unregistered, all timers are properly cleaned up:

```python
def unregister():
    _preference_monitor.cleanup()
    # ... rest of unregister code
```

## Debouncing: Preventing Slider Drag Issues

### The Problem

When users drag sliders rapidly (e.g., adjusting sidebar width), the property `update=` callback fires on **every micro-movement**. This was causing:

1. **Rapid sidebar recreation**: `close_sidebars()` + `restore_sidebars()` on every tick
2. **Timer leak**: `restore_sidebars()` registers a timer for `split_for_properties()` - multiple rapid calls created multiple timers
3. **Area spawning**: Multiple OUTLINER/PROPERTIES areas created faster than Blender can close them
4. **Visual chaos**: 3+ sidebar instances appear before cleanup catches up
5. **Performance degradation**: Hundreds of area operations per second

### The Solution: Dual Fix

EditorBar implements **two fixes** to prevent spawning:

#### 1. Debounced Updates (150ms)

- Cancels any pending update when a new change is detected
- Waits 150ms after the last change before applying
- Ensures only one update happens after user stops dragging

```python
def schedule_immediate_update(self):
    """Schedule a debounced update - cancels previous pending updates."""
    # Cancel previous pending update
    if bpy.app.timers.is_registered(self._immediate_update):
        bpy.app.timers.unregister(self._immediate_update)

    # Schedule new update with debounce delay (150ms)
    bpy.app.timers.register(
        self._immediate_update,
        first_interval=self._debounce_delay
    )
```

#### 2. Timer Leak Prevention

`restore_sidebars()` registers a timer for `split_for_properties()` to create the stacked layout. Without cleanup, each call adds a new timer:

```python
# In restore_sidebars()
# Cancel any existing timer first to prevent multiple sidebars
global _split_timer_func
if _split_timer_func and bpy.app.timers.is_registered(_split_timer_func):
    bpy.app.timers.unregister(_split_timer_func)

_split_timer_func = partial(
    split_for_properties, screen, window, stack_ratio, flip_editors
)
bpy.app.timers.register(_split_timer_func, first_interval=0.2)
```

This ensures only **one** `split_for_properties` timer exists at any time.

### Why 150ms?

- **Too short (< 100ms)**: Still causes multiple updates during drag
- **Too long (> 300ms)**: Feels unresponsive
- **150ms**: Sweet spot - feels instant but prevents rapid-fire updates

### Benefits

✅ Smooth slider dragging without visual glitches
✅ Single sidebar instance maintained
✅ No performance degradation during adjustment
✅ Clean user experience

## Context-Aware Updates

The `on_sidebar_settings_update()` callback handles two scenarios:

### Scenario 1: Changes in VIEW_3D

```python
if area and area.type == 'VIEW_3D':
    # Direct update - we have proper context
    editorbar.close_sidebars(screen, window)
    editorbar.restore_sidebars(screen, window, context)
```

### Scenario 2: Changes in Preferences

```python
else:
    # Schedule update via monitor
    _preference_monitor.schedule_immediate_update()
```

This ensures updates happen regardless of where the user is editing preferences.

## Performance Considerations

### **Timer Interval**

- **150ms polling interval**: Balanced for responsiveness vs performance
- **150ms debounce delay**: Prevents rapid-fire updates during slider drag
- **Timer leak prevention**: Cancels existing `split_for_properties` timers before creating new ones
- Only runs when preferences are actually open
- Automatically stops when preferences are closed

### Caching Strategy

- Previous preference values are cached in `_last_prefs` dictionary
- Updates only trigger when values actually change
- Reduces unnecessary viewport refreshes

### Minimal Overhead

```python
try:
    # Update logic
except Exception:
    pass  # Silently fail to avoid console spam
```

Error handling prevents log spam during normal operations while allowing the system to recover gracefully from edge cases.

## Usage Examples

### For Users

1. Open Blender Preferences (Edit > Preferences)
2. Navigate to Add-ons > EditorBar
3. Adjust any setting (sidebar width, stack ratio, etc.)
4. **Changes apply immediately** to any open 3D Viewports

### For Developers

The monitoring system is fully automatic:

```python
# Define properties with update callbacks
split_factor: FloatProperty(
    name='Sidebar Width',
    update=on_sidebar_settings_update,  # Auto-wired
)

# Monitor activates automatically when preferences draw
def draw(self, context):
    _preference_monitor.activate_monitoring()  # That's it!
```

## Technical Details

### Context Detection

The system uses multiple checks to determine if preferences are active:

```python
def _is_preferences_context(self):
    if not context.area or context.area.type != 'PREFERENCES':
        return False
    if not context.preferences or not hasattr(context.preferences, 'addons'):
        return False
    return __package__ in context.preferences.addons
```

### Type Safety

All Blender API access uses type guards and ignore annotations where necessary:

```python
addon_prefs = bpy.context.preferences.addons[__package__].preferences  # type: ignore[index]
```

This accommodates Blender's dynamic API while maintaining type safety for static analysis.

## Comparison with Alternative Approaches

### Modal Operator Pattern (Not Used)

**Pros:**

- Full event handling
- Can track all user interactions

**Cons:**

- Complex lifecycle management
- Window manager overhead
- Difficult to integrate with property callbacks

### Draw Handler Pattern (Not Used)

**Pros:**

- Runs on every draw call
- Immediate response

**Cons:**

- High performance overhead
- Runs constantly, not just when needed
- Complex registration/unregistration

### Timer Pattern (Implemented)

**Pros:**

- Lightweight and efficient
- Easy to start/stop based on context
- Clean integration with property callbacks
- Professional addons (BlenderKit, etc.) use this pattern

**Cons:**

- Slight delay (150ms) between change and update
- Requires careful cleanup on unregister

## Known Limitations

1. **No True Expansion Detection**: Cannot detect if the EditorBar preferences panel is specifically expanded vs collapsed. We assume if preferences are open and our addon is registered, we should monitor.

2. **Polling Interval Trade-off**: 150ms provides good responsiveness but isn't truly instantaneous. Lowering the interval increases CPU usage.

3. **Debounce Delay**: 150ms delay means changes aren't applied until user stops dragging. This is intentional to prevent visual glitches and timer leaks, but means there's a slight lag before updates appear.

4. **Multiple Windows**: The current implementation updates all `VIEW_3D` areas across all windows. This is usually desired but could be more targeted.

5. **Context Requirements**: Updates require a valid `bpy.context` with screen and window. In rare cases (headless mode, startup), this might not be available.

## Future Improvements

### Potential Enhancements

1. **Panel Expansion Detection**: If Blender adds API support for detecting expanded panels, we could be more targeted in when to run the timer.

2. **Adaptive Polling**: Adjust timer interval based on whether changes are detected (e.g., poll faster when actively editing, slower when idle).

3. **Multi-Window Awareness**: Track which specific window/screen has preferences open and only update related `VIEW_3D` areas.

4. **Preference Change Events**: If Blender adds event-based notification for preference changes, migrate from polling to event-driven updates.

### API Requests for Blender

Features that would improve this system:

- `bpy.types.Panel.is_expanded()` method
- `bpy.app.handlers.addon_preferences_changed` event
- `bpy.context.preferences.active_addon` property

## References

### Research Sources

This implementation is based on research of:

- Blender API documentation (`bpy.app.timers`, `bpy.context`, `AddonPreferences`)
- Professional addon patterns (BlenderKit, Curve Tools)
- Community discussions on preference monitoring limitations
- Best practices from `devtalk.blender.org` and `blenderartists.org`

### Key Documentation

- [bpy.app.timers](https://docs.blender.org/api/current/bpy.app.timers.html) - Timer registration and management
- [bpy.types.AddonPreferences](https://docs.blender.org/api/current/bpy.types.AddonPreferences.html) - Addon preference system
- [bpy.types.Context](https://docs.blender.org/api/current/bpy.types.Context.html) - Context access and limitations

## Testing Recommendations

### Manual Testing Checklist

- [ ] Open preferences, change setting, verify VIEW_3D updates
- [ ] Close preferences, verify timer stops (check console)
- [ ] Change settings in VIEW_3D panel, verify immediate update
- [ ] Test with multiple 3D Viewports open
- [ ] Disable/re-enable addon, verify no orphaned timers
- [ ] Test in different workspace layouts

### Performance Testing

Monitor `bpy.app.timers._registered_functions` to ensure:

- Timer starts when preferences open
- Timer stops when preferences close
- No orphaned timers after addon unregister

## Conclusion

The timer-based preference monitoring system provides a professional, performant solution for real-time preference updates in EditorBar. While it works around Blender API limitations, it follows established patterns from successful addons and provides a smooth user experience with minimal overhead.

The implementation is production-ready, well-documented, and maintainable for future improvements as Blender's API evolves.

---

**Version**: 0.2.0
**Last Updated**: 2024
**Author**: EditorBar Development Team
