# Core Functionality

EditorBar's main functionality for creating and managing sidebar editors.

## Key Functions

### `restore_sidebars()`
Creates the sidebar by splitting the rightmost area and setting up Outliner/Properties editors.

**Process:**
1. Gets user preferences (width, position, stacking)
2. Splits main area vertically for sidebar
3. Sets new area to Outliner
4. Schedules timer to split Outliner horizontally for Properties

### `close_sidebars()`
Closes all Outliner and Properties editors by finding the rightmost instance of each type.

### `split_for_properties()`
Timer callback that splits the Outliner area horizontally to create stacked layout.

**Features:**
- Robust area detection using pre-split bounds
- Handles editor flipping (Outliner top/bottom)
- Prevents timer leaks by canceling existing timers

## Utility Functions

### `map_split_factor()`
Converts slider value (10-49) to split factor with reversed logic:
- Lower slider = wider sidebar
- Higher slider = narrower sidebar

### `map_stack_ratio()`
Converts percentage (10-90) to decimal ratio for Properties panel height.

### `get_editorbar_prefs()`
Gets addon preferences with fallback to defaults if preferences unavailable.

## Operators

### `EDITORBAR_OT_toggle_sidebar`
Main toggle operator - creates or closes sidebar based on current state.

### `EDITORBAR_OT_flip_side`
Toggles sidebar between left and right sides.

### `EDITORBAR_OT_flip_stack`
Toggles stacking order (Outliner/Properties positions).

### `EDITORBAR_OT_debug_prefs`
Debug utility to print current preferences to console.

## UI Panel

### `VIEW3D_PT_toggle_editorbar_sidebar`
N-panel in VIEW_3D with buttons for toggle, flip side, flip stack, and reset preferences.

## Keymap

Default shortcut: `Alt + Shift + N` (echoes Blender's N-panel shortcut)