import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_CAPTION_PROMPT = (
    "Beschreibe dieses Bild in 1–3 kurzen Sätzen auf Deutsch. "
    "Fokus auf den politischen oder gesellschaftlichen Inhalt. "
    "Keine Markdown-Formatierung."
)


class CaptionSuggestionService:
    """Thin wrapper around the OpenAI vision API for synchronous caption suggestion."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def suggest_caption(self, image_url: str) -> str:
        """Call GPT-4o mini vision with a fixed German prompt; return the suggested caption."""
        if not image_url:
            raise ValueError("image_url must not be empty")

        logger.debug(f"Requesting caption suggestion for image: {image_url[:80]}")
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": _CAPTION_PROMPT},
                    ],
                }
            ],
            max_tokens=300,
        )
        raw = response.choices[0].message.content or ""
        caption = raw.strip()
        if not caption:
            raise ValueError("Empty caption returned by vision API")
        logger.debug(f"Caption suggestion received ({len(caption)} chars)")
        return caption
