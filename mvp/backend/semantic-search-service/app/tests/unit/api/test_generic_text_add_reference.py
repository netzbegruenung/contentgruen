"""Regression test for /addGenericText with a source that does not exist yet.

The reference the user types into the contribution form is created with
ContentStatus.PENDING_REVIEW, and the repository search filter excludes that
status, so find_exact_match() never finds it again. The endpoint therefore
always takes the "create a new reference" branch - which must call
ReferenceService.add_reference() with its real signature.

The reference service mock is autospecced on purpose: it binds the call in the
router against the real signature, so an argument the service does not accept
fails here instead of turning into a 500 at runtime.
"""

import uuid
from unittest.mock import create_autospec

import pytest
from fastapi.testclient import TestClient

from main import app
from dependencies import get_generic_text_service, get_reference_service
from services.content.generic_text_service import GenericTextService
from services.content.reference_service import ReferenceService


NEW_REFERENCE_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
NEW_GENERIC_TEXT_ID = uuid.UUID("66666666-7777-8888-9999-000000000000")

REQUEST_BODY = {
    "generictext": {
        "title": "Quellentest",
        "text": "Ein ausreichend langer Testtext fuer die Hintergrundinfo.",
    },
    "references": [
        {
            "reference_string": "https://www.example.org/noch-nicht-vorhanden",
            "description": "Eine bislang unbekannte Quelle",
        }
    ],
}


@pytest.fixture
def services():
    """Autospecced services wired into the app; None from find_exact_match forces
    the 'reference does not exist yet' branch."""
    reference_service = create_autospec(ReferenceService, instance=True)
    reference_service.find_exact_match.return_value = None
    reference_service.add_reference.return_value = (
        NEW_REFERENCE_ID,
        True,
        "New reference created successfully",
    )

    generic_text_service = create_autospec(GenericTextService, instance=True)
    generic_text_service.add_generic_text.return_value = (
        True,
        NEW_GENERIC_TEXT_ID,
        "Ein ausreichend langer Testtext fuer die Hintergrundinfo.",
    )

    app.dependency_overrides[get_reference_service] = lambda: reference_service
    app.dependency_overrides[get_generic_text_service] = lambda: generic_text_service

    yield reference_service, generic_text_service

    app.dependency_overrides.clear()


@pytest.mark.unit
@pytest.mark.api
def test_add_generic_text_with_unknown_reference_is_stored(services):
    """A source that is new to the index must not break saving the contribution."""
    reference_service, generic_text_service = services
    client = TestClient(app)

    response = client.post(
        "/api/v1/generic_text/addGenericText",
        json=REQUEST_BODY,
        headers={"X-User": "testuser"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"id": str(NEW_GENERIC_TEXT_ID)}

    reference_service.add_reference.assert_called_once()

    # The generic text must carry the freshly created reference.
    generic_text_arg = generic_text_service.add_generic_text.call_args.args[0]
    assert [ref.reference_id for ref in generic_text_arg.references] == [
        NEW_REFERENCE_ID
    ]
