# ============================================================================
# Helper Functions (for backend to calculate permission differences)
# ============================================================================

from typing import List


def calculate_permission_overrides(
    role_default_permissions: List[str], selected_permissions: List[str]
) -> tuple[List[str], List[str]]:
    """
    Calculate which permissions should be added/removed based on selections.

    Args:
        role_default_permissions: Permissions that come with the role
        selected_permissions: Permissions checked in the UI

    Returns:
        Tuple of (added_permissions, removed_permissions)
    """
    role_set = set(role_default_permissions)
    selected_set = set(selected_permissions)

    # Added = selected but not in role defaults
    added = list(selected_set - role_set)

    # Removed = in role defaults but not selected
    removed = list(role_set - selected_set)

    return added, removed
