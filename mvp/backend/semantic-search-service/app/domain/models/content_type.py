from enum import Enum


class ContentType(str, Enum):
    """
    Enum class for content types

    Attributes:
    -----------
    STATEMENT: str
        Content type for a statement - see statement.py for details
    COMMENTARY: str
        Content type for a commentary - see commentary.py for details
    REFERENCE: str
        Content type for a reference - see reference.py for details
    GENERIC_TEXT: str
        Content type for generic text that does not yet have a specific content type
    POST: str
        Content type for a social-media post - see post.py for details
    TEST: str
        Content type for test content
    DEFAULT: str
        Default content type
    """

    STATEMENT = "statement"
    COMMENTARY = "commentary"
    REFERENCE = "reference"
    GENERIC_TEXT = "generic_text"
    POST = "post"
    IMAGE = "image"
    TEST = "test"
    DEFAULT = "default"
