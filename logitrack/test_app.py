import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_page_loads(client):
    """Smoke Test: Verifica que la página de login devuelva status 200 OK"""
    respuesta = client.get('/login')
    assert respuesta.status_code == 200
    assert b'LogiTrack' in respuesta.data
