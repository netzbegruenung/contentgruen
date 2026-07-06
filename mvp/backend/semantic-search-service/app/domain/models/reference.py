from typing import Optional
from domain.models.content_type import ContentType
from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class Reference(BaseContent):
    """
    Reference model representing a reference for any type of content.
    A reference is a citation of a source of information. This can be a URL, a book, a paper, a speech, whatever.
    The 'text' field inherited from BaseContent contains the description of what this source contains.

    Attributes:
    -----------
    reference_string: str
        String representation of the reference (e.g. a URL)
    """

    content_type: ContentType = ContentType.REFERENCE

    reference_string: str
    # TODO: Add a date of publication
    # TODO: Add author?


class ReferenceDbEntry(Reference, BaseContentDbEntry):
    """
    ReferenceInput model representing a reference with additional properties to insert it into the reference_index

    Attributes:
    -----------
    usage_count: Optional[int]
        Number of times this reference has been used in commentaries
    """

    usage_count: Optional[int] = None


class ReferenceSearchResult(ReferenceDbEntry, BaseContentSearchResult):
    """
    Representing a reference with score and additional result metadata
    """
