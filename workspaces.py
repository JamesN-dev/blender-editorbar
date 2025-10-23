from collections.abc import Sequence
import bpy
from bpy.types import Area, Screen

# --- Helper Functions ---


def get_rightmost_area(areas: Sequence[Area]) -> Area | None:
    """Gets the rightmost area from a sequence of areas."""
    if not areas:
        return None
    return max(areas, key=lambda a: a.x + a.width)


# --- Workspace Specific Logic ---


def handle_simple_layout(screen: Screen) -> list[Area]:
    """Finds the single main area for simple, common layouts."""
    # For these simple layouts, we find the rightmost area that isn't a sidebar.
    # We explicitly exclude the Dope Sheet for this simple case.
    main_areas = [
        a
        for a in screen.areas
        if a.type not in {'OUTLINER', 'PROPERTIES', 'DOPESHEET_EDITOR'}
    ]
    base_area = get_rightmost_area(main_areas)
    return [base_area] if base_area else []


def handle_animation_layout(screen: Screen) -> list[Area]:
    """Finds the target areas for the 'Animation' workspace."""
    # TODO: Implement the multi-area logic for Animation
    print('Animation workspace logic not yet implemented.')
    return []


# --- Main Dispatcher Function ---


def get_target_areas(screen: Screen, workspace_name: str) -> list[Area]:
    """
    Identifies which editor areas to split based on the active workspace.

    This acts as a dispatcher, calling the appropriate function for each layout.
    """
    if workspace_name in {
        'Layout',
        'Modeling',
        'Sculpting',
        'UV Editing',
        'Texture Paint',
        'Geometry Nodes',
        'Scripting',
    }:
        return handle_simple_layout(screen)

    elif workspace_name == 'Animation':
        return handle_animation_layout(screen)

    # Fallback for any other workspaces
    else:
        # The fallback can use the simple logic, but be less restrictive.
        main_areas = [
            a for a in screen.areas if a.type not in {'OUTLINER', 'PROPERTIES'}
        ]
        base_area = get_rightmost_area(main_areas)
        return [base_area] if base_area else []
