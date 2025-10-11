# EditorBar Documentation

Technical documentation for the EditorBar Blender addon.

## Overview

EditorBar transforms Blender's default Outliner and Properties editors into a toggleable sidebar, providing a more streamlined workspace experience.

## Documentation Pages

### [Core Functionality](CORE_FUNCTIONALITY.md)
Main sidebar creation and management functions, operators, and UI components.

### [Preferences System](PREFERENCES.md)
Preference properties, real-time monitoring, and update mechanisms.

### [Preference Monitoring](PREFERENCES_MONITORING.md)
Timer-based system for real-time preference updates with debouncing.

### [Architecture Overview](ARCHITECTURE.md)
Component relationships, data flow, and system design.

## Quick Reference

### Key Components
- **Sidebar Toggle**: Creates/destroys Outliner + Properties sidebar
- **Real-time Preferences**: Live updates while editing preferences
- **Flexible Layout**: Left/right positioning, stacking order, sizing
- **Timer Management**: Robust cleanup and leak prevention

### Main Functions
- `restore_sidebars()` - Creates sidebar layout
- `close_sidebars()` - Removes sidebar editors
- `split_for_properties()` - Creates stacked layout

### Operators
- `editorbar.toggle_sidebar` - Main toggle (Alt+Shift+N)
- `editorbar.flip_side` - Switch left/right
- `editorbar.flip_stack` - Change stacking order

### Preferences
- Sidebar position (left/right)
- Width (10-49%, reversed mapping)
- Properties height (10-90%)
- Editor stacking order