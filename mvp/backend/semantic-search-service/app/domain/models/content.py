from domain.models.base_content import (
    BaseContent,
    BaseContentDbEntry,
    BaseContentSearchResult,
)


class Content(BaseContent):
    """
    Representing a generic content item, currently contains only the base content properties
    """


class ContentDbEntry(Content, BaseContentDbEntry):
    """
    Representing a generic content item with additional input metadata to insert it into the content_index
    """


class ContentSearchResult(ContentDbEntry, BaseContentSearchResult):
    """
    Representing a generic content item with score and additional content result metadata
    """
