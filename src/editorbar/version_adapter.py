"""Version adapter for safe Blender API operations across versions 4.2+.

This module provides version-safe wrappers around risky Blender API operations
that may behave differently or cause crashes on older Blender versions.
"""

from typing import Any, cast

import bpy

_BLENDER_VER: tuple[int, int, int] | None = None
_IS_4_5: bool | None = None

DEBUG = False


def debug_log(message: str) -> None:
    """Log debug message if DEBUG flag is enabled."""
    if DEBUG:
        print(f'[EditorBar-Adapter] {message}')


def get_blender_version() -> tuple[int, int, int]:
    global _BLENDER_VER
    if _BLENDER_VER is None:
        _BLENDER_VER = bpy.app.version
        debug_log(
            f'Blender {_BLENDER_VER[0]}.{_BLENDER_VER[1]}.{_BLENDER_VER[2]} detected'
        )
    return _BLENDER_VER


def is_version_at_least(major: int, minor: int, patch: int = 0) -> bool:
    global _IS_4_5

    if (major, minor, patch) == (4, 5, 0):
        if _IS_4_5 is None:
            current = get_blender_version()
            _IS_4_5 = current >= (4, 5, 0)
            debug_log(f'Version >= 4.5.0: {_IS_4_5}')
        else:
            debug_log(f'Version >= 4.5.0: {_IS_4_5} (cached)')
        return _IS_4_5

    return False


def check_area(
    window: bpy.types.Window | None,
    screen: bpy.types.Screen | None,
    area: bpy.types.Area | None,
) -> bool:
    """Check if it's safe to perform area operations without triggering known Blender crashes.

    Args:
        window: Window context
        screen: Screen context
        area: Area to validate

    Returns:
        True if context is safe for area operations
    """
    if not window or not screen or not area:
        debug_log('Context validation FAILED: window, screen, or area is None')
        return False

    if not hasattr(window, 'screen') or window.screen != screen:
        debug_log('Context validation FAILED: window.screen mismatch')
        return False

    if not hasattr(screen, 'areas'):
        debug_log('Context validation FAILED: screen has no areas attribute')
        return False

    area_found = False
    try:
        for a in screen.areas:
            if a == area:
                area_found = True
                break
    except Exception:
        debug_log('Context validation FAILED: error iterating screen.areas')
        return False

    if not area_found:
        debug_log('Context validation FAILED: area not found in screen.areas')
        return False

    if not hasattr(area, 'width') or not hasattr(area, 'height'):
        debug_log('Context validation FAILED: area missing width/height attributes')
        return False
    if area.width <= 0 or area.height <= 0:
        debug_log(
            f'Context validation FAILED: area dimensions invalid (w={area.width}, h={area.height})'
        )
        return False

    if not hasattr(area, 'type') or not area.type:
        debug_log('Context validation FAILED: area missing or invalid type')
        return False

    return True


def safe_area_close(
    screen: bpy.types.Screen, window: bpy.types.Window, area: bpy.types.Area
) -> bool:
    """Safely close an area based on version."""
    if not check_area(window, screen, area):
        debug_log('Area close aborted: invalid context')
        return False

    if not is_version_at_least(4, 5, 0):
        debug_log('Applying 4.2-4.4 safety checks')
        if len(screen.areas) < 2:
            debug_log(f'Area close aborted: only {len(screen.areas)} area(s)')
            return False
        if area.width < 50 or area.height < 50:
            debug_log(f'Area close aborted: too small ({area.width}x{area.height})')
            return False

    try:
        override = {'window': window, 'screen': screen, 'area': area}
        with cast(Any, bpy.context).temp_override(**override):
            bpy.ops.screen.area_close()
        return True
    except Exception as e:
        debug_log(f'Area close failed: {e}')
        return False


def safe_area_split(
    screen: bpy.types.Screen,
    window: bpy.types.Window,
    area: bpy.types.Area,
    direction: str,
    factor: float,
) -> bool:
    """Safely split an area with version-specific validation."""
    if not check_area(window, screen, area):
        debug_log('Area split aborted: invalid context')
        return False

    if direction not in {'VERTICAL', 'HORIZONTAL'}:
        debug_log(f"Area split aborted: invalid direction '{direction}'")
        return False
    if not 0.0 < factor < 1.0:
        debug_log(f'Area split aborted: invalid factor {factor}')
        return False

    if not is_version_at_least(4, 5, 0):
        debug_log('Applying 4.2-4.4 safety checks')
        min_size = 200
        if direction == 'VERTICAL' and area.width < min_size:
            debug_log(f'Area split aborted: width {area.width} < {min_size}')
            return False
        if direction == 'HORIZONTAL' and area.height < min_size:
            debug_log(f'Area split aborted: height {area.height} < {min_size}')
            return False
        if factor < 0.1 or factor > 0.9:
            debug_log(f'Area split aborted: factor {factor} outside [0.1, 0.9]')
            return False

    try:
        override = {'window': window, 'screen': screen, 'area': area}
        with cast(Any, bpy.context).temp_override(**override):
            bpy.ops.screen.area_split(direction=direction, factor=factor)
        return True
    except Exception as e:
        debug_log(f'Area split failed: {e}')
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
        debug_log('Area type change aborted: invalid area')
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
        debug_log(f"Area type change aborted: invalid type '{new_type}'")
        return False

    try:
        area.type = new_type
        if hasattr(area, 'tag_redraw'):
            area.tag_redraw()
        return True
    except Exception as e:
        debug_log(f'Area type change failed: {e}')
        return False


def validate_timer_context() -> bool:
    """Validate that current context is safe for timer-based operations.

    Timer callbacks can execute in unexpected contexts. This validates
    that we're in a safe state to perform UI operations.

    Returns:
        True if context is safe for timer operations
    """
    try:
        if not hasattr(bpy, 'context'):
            debug_log('Timer context invalid: bpy.context unavailable')
            return False

        context = bpy.context

        if not hasattr(context, 'window') or not context.window:
            debug_log('Timer context invalid: no window')
            return False
        if not hasattr(context, 'screen') or not context.screen:
            debug_log('Timer context invalid: no screen')
            return False

        window = context.window
        screen = context.screen

        if not hasattr(window, 'screen') or window.screen != screen:
            debug_log('Timer context invalid: screen mismatch')
            return False

        if not hasattr(screen, 'areas') or not screen.areas:
            debug_log('Timer context invalid: no areas')
            return False

        if not is_version_at_least(4, 5, 0):
            debug_log('Applying 4.2-4.4 timer checks')
            valid_area_found = any(
                hasattr(area, 'type')
                and hasattr(area, 'width')
                and hasattr(area, 'height')
                and area.width > 0
                and area.height > 0
                for area in screen.areas
            )

            if not valid_area_found:
                debug_log('Timer context invalid: no valid areas')
                return False

        return True

    except Exception as e:
        debug_log(f'Timer context invalid: {e}')
        return False
