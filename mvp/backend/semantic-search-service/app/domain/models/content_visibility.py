from enum import Enum


class ContentVisibility(str, Enum):
    """
    Legacy visibility marker. Every Beitrag is visible to everyone; new content sets no
    visibility. Kept only so stored values still parse until the status cleanup (#214).

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
