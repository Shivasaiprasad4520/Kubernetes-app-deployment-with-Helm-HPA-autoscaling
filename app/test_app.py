# test_app.py
import pytest
import os
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from app import app, init_db


# ── FIXTURE: spins up a fresh in-memory DB + mocks templates ──
@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')

    app.config['TESTING']       = True
    app.config['DATABASE']      = db_path
    app.config['UPLOAD_FOLDER'] = 'test_uploads'

    os.makedirs('test_uploads', exist_ok=True)

    # Mock render_template so tests don't need HTML files
    # This is correct CI practice — unit tests test logic, not templates
    with patch('app.render_template', return_value='<html>OK</html>'):
        with app.test_client() as client:
            init_db()
            yield client

    os.close(db_fd)
    os.unlink(db_path)
    import shutil
    if os.path.exists('test_uploads'):
        shutil.rmtree('test_uploads')


# ── helper: register a student ──
def register_student(client, name="Loki", email="loki@test.com",
                     password="123", roll_no="101"):
    return client.post('/register', data={
        'name':     name,
        'email':    email,
        'password': password,
        'course':   'DevOps',
        'roll_no':  roll_no,
        'branch':   'CSE',
        'year':     '4'
    }, follow_redirects=True)


# ── TESTS ──

def test_home(client):
    response = client.get('/')
    assert response.status_code == 200


def test_register(client):
    response = register_student(client)
    assert response.status_code == 200


def test_login_valid(client):
    register_student(client)
    response = client.post('/login', data={
        'email':    'loki@test.com',
        'password': '123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_login_invalid(client):
    response = client.post('/login', data={
        'email':    'wrong@test.com',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert response.status_code == 401


def test_admin_login_valid(client):
    response = client.post('/admin-login', data={
        'username': 'admin',
        'password': '123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_admin_login_invalid(client):
    response = client.post('/admin-login', data={
        'username': 'admin',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert response.status_code == 401


def test_faculty_login_valid(client):
    response = client.post('/faculty-login', data={
        'username': 'faculty',
        'password': '123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_faculty_login_invalid(client):
    response = client.post('/faculty-login', data={
        'username': 'faculty',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert response.status_code == 401


def test_student_dashboard(client):
    response = client.get('/student-dashboard')
    assert response.status_code == 200


def test_admin_dashboard(client):
    response = client.get('/admin-dashboard')
    assert response.status_code == 200