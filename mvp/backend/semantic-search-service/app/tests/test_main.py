# test_main.py
import os
import pytest
from fastapi.testclient import TestClient
from main import app

# Set the environment variable for the test
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 404  # Assuming the root endpoint is not defined


def test_test_router():
    response = client.get("/api/v1/test")
    assert (
        response.status_code == 200
    )  # Assuming the test router is defined and returns 200


def test_content_router():
    response = client.get("/api/v1/content")
    assert (
        response.status_code == 200
    )  # Assuming the content router is defined and returns 200


def test_statement_router():
    response = client.get("/api/v1/statement")
    assert (
        response.status_code == 200
    )  # Assuming the statement router is defined and returns 200
