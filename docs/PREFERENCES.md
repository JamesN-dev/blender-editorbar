# Preferences System

EditorBar's preference system with real-time updates and monitoring.

## Preference Properties

### `left_sidebar` (Boolean)
- **Default**: False (right side)
- **Description**: Places sidebar on left or right side of viewport

### `split_factor` (Integer)
- **Range**: 10-49
- **Default**: 40
- **Description**: Sidebar width percentage with reversed mapping
- **Mapping**: Lower values = wider sidebar, higher values = narrower sidebar

### `stack_ratio` (Integer)
- **Range**: 10-90
- **Default**: 66
- **Description**: Properties panel height as percentage of sidebar

### `flip_editors` (Boolean)
- **Default**: False (Properties bottom)
- **Description**: Toggles vertical stacking order of Outliner/Properties

## Preference Monitoring

### `EditorBarPreferenceMonitor`
Handles real-time preference updates when preferences panel is open.

**Key Features:**
- Timer-based polling (150ms intervals)
- Debounced updates (50ms delay)
- Automatic start/stop based on context
- Prevents timer leaks and visual glitches

### Update Callbacks
All properties use `update=on_sidebar_settings_update` which:
- Schedules debounced updates to prevent rapid-fire changes
- Works in both VIEW_3D and preferences contexts
- Applies changes to all VIEW_3D areas with sidebars

## UI Elements

### Dynamic Labels
Preference panel shows contextual labels:
- "Move to Left/Right" based on current side
- "Outliner Bottom/Properties Bottom" based on flip state
- Real-time width/height percentages in slider labels

### Reset Operator
`EDITORBAR_OT_reset_preferences` restores all settings to defaults and immediately applies changes.

## Default Values
Defined as constants in `__init__.py`:
- `DEFAULT_LEFT_SIDEBAR = False`
- `DEFAULT_SPLIT_FACTOR = 40`
- `DEFAULT_STACK_RATIO = 66`
- `DEFAULT_FLIP_EDITORS = False`