"""
Concrete ingestion strategies (Seam 1 of CONTENT_MODEL.md, rung-2 Phase B).

DirectText — identity strategy used by all types (text = user input). An image's
Unterschrift is user input as well: an AI suggestion counts only once a person takes it
over (ADR 0003, #281).
"""

from domain.protocols import ContentInput, DerivedContent


class DirectText:
    """Identity ingestion: the user-provided text is the searchable text."""

    async def derive_text(self, raw: ContentInput) -> DerivedContent:
        return DerivedContent(text=raw.text)
