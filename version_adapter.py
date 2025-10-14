"""Version adapter for safe Blender API operations across versions 4.2+.

This module provides version-safe wrappers around risky Blender API operations
that may behave differently or cause crashes on older Blender versions.
"""

from typing import Any, cast

import bpy


def get_blender_version() -> tuple[int, int, int]:
    """Get current Blender version as tuple (major, minor, patch)."""
    return bpy.app.version


def is_version_at_least(major: int, minor: int, patch: int = 0) -> bool:
    """Check if current Blender version is at least the specified version."""
    current = get_blender_version()
    return current >= (major, minor, patch)


def is_safe_context_for_area_ops(
    window: bpy.types.Window | None,
    screen: bpy.types.Screen | None,
    area: bpy.types.Area | None,
) -> bool:
    """Validate that context is safe for area manipulation operations.

    Performs deep validation to prevent segfaults on Blender 4.2-4.4.

    Args:
        window: Window context
        screen: Screen context
        area: Area to validate

    Returns:
        True if context is safe for area operations
    """
    # Check basic None guards
    if not window or not screen or not area:
        return False

    # Verify window has valid screen
    if not hasattr(window, 'screen') or window.screen != screen:
        return False

    # Verify area exists in screen
    if not hasattr(screen, 'areas') or area not in screen.areas:
        return False

    # Verify area has valid dimensions (not being destroyed)
    if not hasattr(area, 'width') or not hasattr(area, 'height'):
        return False
    if area.width <= 0 or area.height <= 0:
        return False

    # Verify area has valid type
    if not hasattr(area, 'type') or not area.type:
        return False

    return True


def safe_area_close(
    screen: bpy.types.Screen,
    window: bpy.types.Window,
    area: bpy.types.Area,
) -> bool:
    """Safely close an area with version-specific validation.

    Args:
        screen: Screen containing the area
        window: Window context
        area: Area to close

    Returns:
        True if area was closed successfully, False otherwise
    """
    # Pre-validate context
    if not is_safe_context_for_area_ops(window, screen, area):
        return False

    # Additional validation for older versions
    if not is_version_at_least(4, 5, 0):
        # 4.2-4.4: Extra safety checks
        # Ensure we have at least 2 areas before closing
        if len(screen.areas) < 2:
            return False

        # Don't close if area is too small (might be mid-operation)
        if area.width < 50 or area.height < 50:
            return False

    try:
        override = {'window': window, 'screen': screen, 'area': area}
        with cast(Any, bpy.context).temp_override(**override):
            bpy.ops.screen.area_close()
        return True
    except Exception as e:
        # Silently handle errors - context may have changed
        if hasattr(bpy.context, 'preferences'):
            print(f'[EditorBar] Area close failed: {e}')
        return False


def safe_area_split(
    screen: bpy.types.Screen,
    window: bpy.types.Window,
    area: bpy.types.Area,
    direction: str,
    factor: float,
) -> bool:
    """Safely split an area with version-specific validation.

    Args:
        screen: Screen containing the area
        window: Window context
        area: Area to split
        direction: Split direction ('VERTICAL' or 'HORIZONTAL')
        factor: Split factor (0.0-1.0)

    Returns:
        True if area was split successfully, False otherwise
    """
    # Pre-validate context
    if not is_safe_context_for_area_ops(window, screen, area):
        return False

    # Validate split parameters
    if direction not in {'VERTICAL', 'HORIZONTAL'}:
        return False
    if not 0.0 < factor < 1.0:
        return False

    # Additional validation for older versions
    if not is_version_at_least(4, 5, 0):
        # 4.2-4.4: Extra safety checks
        # Ensure area is large enough to split
        min_size = 200
        if direction == 'VERTICAL' and area.width < min_size:
            return False
        if direction == 'HORIZONTAL' and area.height < min_size:
            return False

        # Avoid edge cases with very small or large factors
        if factor < 0.1 or factor > 0.9:
            return False

    try:
        override = {'window': window, 'screen': screen, 'area': area}
        with cast(Any, bpy.context).temp_override(**override):
            bpy.ops.screen.area_split(direction=direction, factor=factor)
        return True
    except Exception as e:
        # Silently handle errors - context may have changed
        if hasattr(bpy.context, 'preferences'):
            print(f'[EditorBar] Area split failed: {e}')
        return False


def safe_change_area_type(area: bpy.types.Area, new_type: str) -> bool:
    """Safely change an area's type with validation.

    Args:
        area: Area to modify
        new_type: New area type (e.g., 'VIEW_3D', 'OUTLINER', 'PROPERTIES')

    Returns:
        True if type was changed successfully, False otherwise
    """
    if not area or not hasattr(area, 'type'):
        return False

    valid_types = {
        'VIEW_3D',
        'OUTLINER',
        'PROPERTIES',
        'DOPESHEET_EDITOR',
        'PREFERENCES',
        'INFO',
        'FILE_BROWSER',
        'CONSOLE',
        'TEXT_EDITOR',
        'NODE_EDITOR',
        'IMAGE_EDITOR',
        'SEQUENCE_EDITOR',
        'CLIP_EDITOR',
        'SPREADSHEET',
        'NLA_EDITOR',
        'GRAPH_EDITOR',
    }

    if new_type not in valid_types:
        return False

    try:
        area.type = new_type
        if hasattr(area, 'tag_redraw'):
            area.tag_redraw()
        return True
    except Exception as e:
        if hasattr(bpy.context, 'preferences'):
            print(f'[EditorBar] Area type change failed: {e}')
        return False


def validate_timer_context() -> bool:
    """Validate that current context is safe for timer-based operations.

    Timer callbacks can execute in unexpected contexts. This validates
    that we're in a safe state to perform UI operations.

    Returns:
        True if context is safe for timer operations
    """
    try:
        # Check basic context availability
        if not hasattr(bpy, 'context'):
            return False

        context = bpy.context

        # Must have valid window and screen
        if not hasattr(context, 'window') or not context.window:
            return False
        if not hasattr(context, 'screen') or not context.screen:
            return False

        window = context.window
        screen = context.screen

        # Verify window's screen matches context screen
        if not hasattr(window, 'screen') or window.screen != screen:
            return False

        # Verify screen has areas
        if not hasattr(screen, 'areas') or not screen.areas:
            return False

        # Additional checks for older versions
        if not is_version_at_least(4, 5, 0):
            # On 4.2-4.4, be extra cautious
            # Check that we're not in a transitional state
            if len(screen.areas) < 1:
                return False

            # Verify at least one area is valid
            valid_area_found = False
            for area in screen.areas:
                if (
                    hasattr(area, 'type')
                    and hasattr(area, 'width')
                    and hasattr(area, 'height')
                ):
                    if area.width > 0 and area.height > 0:
                        valid_area_found = True
                        break

            if not valid_area_found:
                return False

        return True

    except Exception:
        return False


def get_version_info() -> str:
    """Get formatted version information for debugging.

    Returns:
        Human-readable version string
    """
    version = get_blender_version()
    return f'{version[0]}.{version[1]}.{version[2]}'
