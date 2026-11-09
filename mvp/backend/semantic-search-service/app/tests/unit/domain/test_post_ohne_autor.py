"""#618: „Gepostet von“ ist optional, nur bei Organisationen oder öffentlichen Konten."""

from domain.models.post import Post
from dtos.beitrag import PostResponse


def test_post_ohne_autor_ist_gueltig():
    post = Post(
        text="Ein Post über Wärmepumpen", title="Gut erklärt", platform="Mastodon"
    )

    assert post.author is None


def test_post_response_ohne_autor_ist_gueltig():
    assert "author" not in PostResponse.model_fields or (
        PostResponse.model_fields["author"].is_required() is False
    )
