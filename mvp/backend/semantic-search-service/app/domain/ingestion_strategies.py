"""
Concrete ingestion strategies (Seam 1 of CONTENT_MODEL.md).

DirectText — identity strategy used by all types (text = user input), the image's
Unterschrift included (ADR 0003).
"""

from domain.protocols import ContentInput, DerivedContent


class DirectText:
    """Identity ingestion: the user-provided text is the searchable text."""

    async def derive_text(self, raw: ContentInput) -> DerivedContent:
        return DerivedContent(text=raw.text)
