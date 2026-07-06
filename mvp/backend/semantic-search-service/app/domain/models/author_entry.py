from typing import Optional
from pydantic import BaseModel


class AuthorEntry(BaseModel):
    """
    Represents an author with optional metadata.

    Attributes:
    -----------
    name: str
        Name or identifier of the author.
    role: Optional[str]
        Role of the author (e.g., "primary author", "contributor").
    """

    name: str
    role: Optional[str] = None
