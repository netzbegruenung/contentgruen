from enum import Enum


class ContentVisibility(str, Enum):
    """
    Legacy visibility marker. Every Beitrag is visible to everyone; new content sets no
    visibility. Kept only so stored values still parse until the status cleanup (#214).

    Attributes (former meaning; no value restricts who sees a Beitrag):
    -----------
    VISIBLE : str
        Was meant as: accessible to all authorized users.
    HIDDEN : str
        Was meant as: hidden but still in the system.
    INTERNAL : str
        Was meant as: visible only within the organization ("Grün-Intern").
    RESTRICTED : str
        Was meant as: visible to specific roles or groups.
    """

    VISIBLE = "visible"
    HIDDEN = "hidden"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
