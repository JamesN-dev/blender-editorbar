# Preference Monitoring

EditorBar uses a timer-based system for real-time preference updates when the preferences panel is open.

## How It Works

1. **Activation**: When preferences panel is drawn, monitoring starts
2. **Polling**: Timer checks for changes every 150ms
3. **Debouncing**: 50ms delay prevents rapid updates during slider drag
4. **Updates**: Changes apply to all VIEW_3D areas with sidebars
5. **Cleanup**: Timer stops when preferences close

## Implementation

### Timer System
- Polls preference values every 150ms while preferences are open
- Automatically starts/stops based on context
- Compares current vs cached values to detect changes

### Debouncing
- 50ms delay after last change before applying updates
- Prevents visual glitches during slider dragging
- Cancels pending updates when new changes detected

### Update Process
- Closes existing sidebars with old settings
- Restores sidebars with new preference values
- Handles multiple VIEW_3D areas across windows

## Why This Approach

Blender's API limitations require this workaround:
- No direct way to detect preference panel expansion
- Property `update=` callbacks may not have VIEW_3D context
- Timer provides reliable cross-context updates

## Performance

- Minimal overhead: only runs when preferences open
- Efficient caching prevents unnecessary updates
- Automatic cleanup prevents timer leaks