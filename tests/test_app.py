import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse


def mock_parse_args():
    return argparse.Namespace(
        host="127.0.0.1",
        port=8000,
        db_host="127.0.0.1",
        db_port=3306,
        db_user="test",
        db_password="test",
        db_name="test"
    )


with patch("argparse.ArgumentParser.parse_args", return_value=mock_parse_args()):
    with patch("pymysql.connect") as mock_conn:
        mock_conn.return_value = MagicMock()
        import app as app_module
        client = TestClient(app_module.app)


def make_mock_conn(fetchall=None, fetchone=None, lastrowid=1):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall or []
    mock_cursor.fetchone.return_value = fetchone
    mock_cursor.lastrowid = lastrowid
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    return mock_connection, mock_cursor


# --- Health endpoints ---

def test_alive():
    response = client.get("/health/alive")
    assert response.status_code == 200
    assert "OK" in response.text


def test_ready_db_ok():
    with patch("app.get_connection") as mock_get_conn:
        mock_get_conn.return_value = MagicMock()
        response = client.get("/health/ready")
        assert response.status_code == 200


def test_ready_db_fail():
    with patch("app.get_connection") as mock_get_conn:
        mock_get_conn.side_effect = Exception("DB error")
        response = client.get("/health/ready")
        assert response.status_code == 500


# --- Root ---

def test_root_html():
    response = client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "notes" in response.text.lower()


# --- Notes API (JSON) ---

def test_get_notes_empty():
    mock_conn, _ = make_mock_conn(fetchall=[])
    with patch("app.get_connection", return_value=mock_conn):
        response = client.get("/notes", headers={"Accept": "application/json"})
        assert response.status_code == 200
        assert response.json() == []


def test_get_notes_with_data():
    mock_conn, _ = make_mock_conn(fetchall=[{"id": 1, "title": "Test Note"}])
    with patch("app.get_connection", return_value=mock_conn):
        response = client.get("/notes", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Note"


def test_create_note_json():
    mock_conn, mock_cursor = make_mock_conn(lastrowid=42)
    with patch("app.get_connection", return_value=mock_conn):
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
    mock_conn, _ = make_mock_conn(
        fetchone={"id": 1, "title": "Test", "content": "Content", "created_at": "2025-01-01 00:00:00"}
    )
    with patch("app.get_connection", return_value=mock_conn):
        response = client.get("/notes/1", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Test"


def test_get_note_not_found():
    mock_conn, _ = make_mock_conn(fetchone=None)
    with patch("app.get_connection", return_value=mock_conn):
        response = client.get("/notes/9999", headers={"Accept": "application/json"})
        assert response.status_code == 404


# --- HTML responses ---

def test_get_notes_html():
    mock_conn, _ = make_mock_conn(fetchall=[{"id": 1, "title": "HTML Note"}])
    with patch("app.get_connection", return_value=mock_conn):
        response = client.get("/notes", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "HTML Note" in response.text


def test_get_note_html():
    mock_conn, _ = make_mock_conn(
        fetchone={"id": 1, "title": "Test", "content": "Content", "created_at": "2025-01-01 00:00:00"}
    )
    with patch("app.get_connection", return_value=mock_conn):
        response = client.get("/notes/1", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "Test" in response.text