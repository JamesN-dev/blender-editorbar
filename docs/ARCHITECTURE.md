# Architecture Overview

EditorBar's modular architecture and component relationships.

## File Structure

```
editorbar/
├── __init__.py          # Preferences, monitoring, registration
├── editorbar.py         # Core functionality, operators, UI
├── blender_manifest.toml # Addon metadata
├── build.py             # Build script
└── docs/                # Documentation
```

## Component Relationships

### `__init__.py`
- **EditorBarPreferences**: Addon preference panel
- **EditorBarPreferenceMonitor**: Real-time preference monitoring
- **Registration**: Class registration and cleanup

### `editorbar.py`
- **Core Functions**: Sidebar creation/destruction logic
- **Operators**: User-facing commands
- **UI Panel**: N-panel interface
- **Keymap**: Keyboard shortcuts

## Data Flow

1. **User Action** → Operator execution
2. **Preference Change** → Monitor detects → Debounced update
3. **Sidebar Toggle** → Check state → Create/destroy sidebar
4. **Area Management** → Split areas → Set editor types → Timer cleanup

## Timer Management

### Primary Timer
- **Function**: `_timer_callback()` in preference monitor
- **Interval**: 150ms
- **Purpose**: Detect preference changes

### Secondary Timer
- **Function**: `split_for_properties()`
- **Interval**: 200ms (one-shot)
- **Purpose**: Create stacked Outliner/Properties layout

### Timer Safety
- Automatic cleanup on addon unregister
- Prevention of multiple timer instances
- Context-aware start/stop

## Error Handling

- Graceful fallbacks for missing preferences
- Silent failure in timer callbacks to prevent console spam
- Context validation before area operations
- Type safety with cast annotations for Blender API

## Performance Considerations

- Minimal polling overhead (150ms intervals)
- Debouncing prevents excessive updates
- Efficient area detection using bounds checking
- Lazy imports to avoid circular dependencies