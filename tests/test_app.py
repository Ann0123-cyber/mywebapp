import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse

def mock_parse_args():
    args = argparse.Namespace(
        host="127.0.0.1",
        port=8000,
        db_host="127.0.0.1",
        db_user="test",
        db_password="test",
        db_name="test"
    )
    return args

with patch("argparse.ArgumentParser.parse_args", return_value=mock_parse_args()):
    with patch("mysql.connector.connect") as mock_conn:
        mock_conn.return_value = MagicMock()
        import app as app_module
        client = TestClient(app_module.app)


# --- Health endpoints ---

def test_alive():
    response = client.get("/health/alive")
    assert response.status_code == 200
    assert response.text == '"OK"' or response.json() == "OK" or "OK" in response.text


def test_ready_db_ok():
    with patch.object(app_module, "db_conn") as mock_db:
        mock_cursor = MagicMock()
        mock_db.cursor.return_value = mock_cursor
        response = client.get("/health/ready")
        assert response.status_code == 200


def test_ready_db_fail():
    with patch.object(app_module, "db_conn", None):
        response = client.get("/health/ready")
        assert response.status_code == 500


# --- Notes API (JSON) ---

def test_get_notes_empty():
    with patch.object(app_module, "db_conn") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_db.cursor.return_value = mock_cursor
        response = client.get("/notes", headers={"Accept": "application/json"})
        assert response.status_code == 200
        assert response.json() == []


def test_get_notes_with_data():
    with patch.object(app_module, "db_conn") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "Test Note")]
        mock_db.cursor.return_value = mock_cursor
        response = client.get("/notes", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Test Note"


def test_create_note_json():
    with patch.object(app_module, "db_conn") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        mock_db.cursor.return_value = mock_cursor
        response = client.post(
            "/notes",
            json={"title": "New Note", "content": "Some content"},
            headers={"Accept": "application/json"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 42
        assert data["title"] == "New Note"


def test_get_note_by_id():
    with patch.object(app_module, "db_conn") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, "Test", "Content", "2025-01-01 00:00:00")
        mock_db.cursor.return_value = mock_cursor
        response = client.get("/notes/1", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Test"


def test_get_note_not_found():
    with patch.object(app_module, "db_conn") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.cursor.return_value = mock_cursor
        response = client.get("/notes/9999", headers={"Accept": "application/json"})
        assert response.status_code == 404


# --- HTML responses ---

def test_get_notes_html():
    with patch.object(app_module, "db_conn") as mock_db:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "HTML Note")]
        mock_db.cursor.return_value = mock_cursor
        response = client.get("/notes", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "HTML Note" in response.text


def test_root_html():
    response = client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "notes" in response.text.lower()