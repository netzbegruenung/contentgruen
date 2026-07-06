from enum import Enum


class ContentVisibility(str, Enum):
    """
    Enum class for content visibility

    Attributes:
    -----------
    VISIBLE : str
        Content is accessible to all authorized users.
    HIDDEN : str
        Content is hidden but still exists in the system.
    INTERNAL : str
        Content is visible only within the organization.
    RESTRICTED : str
        Content is visible to specific roles or groups.
    """

    VISIBLE = "visible"
    HIDDEN = "hidden"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
