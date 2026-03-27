import pytest
from app import app

# ==========================================
# FIXTURE: CONFIGURACIÓN DEL ENTORNO DE TEST
# ==========================================
@pytest.fixture
def client():
    """Configura un cliente de pruebas de Flask para simular peticiones de navegador"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# ==========================================
# CASO 1: SMOKE TESTS (¿La app arranca?)
# ==========================================
def test_login_page_loads(client):
    """Prueba que la página de login cargue correctamente (HTTP 200 OK)"""
    respuesta = client.get('/login')
    assert respuesta.status_code == 200

# ==========================================
# CASO 2: SEGURIDAD Y PROTECCIÓN DE RUTAS (NFR-02)
# ==========================================
def test_rutas_protegidas_sin_login(client):
    """Prueba que un usuario sin sesión sea redirigido al login (HTTP 302)"""
    respuesta = client.get('/envios')
    assert respuesta.status_code == 302
    assert '/login' in respuesta.headers.get('Location', '')

# ==========================================
# CASO 3: FLUJO DE AUTENTICACIÓN (Roles - US-08)
# ==========================================
def test_login_exitoso_supervisor(client):
    """Prueba el inicio de sesión con el diccionario USUARIOS de app.py"""
    datos_login = {
        'usuario': 'supervisor', 
        'password': 'sup123'
    }
    # follow_redirects=True hace que Flask siga a /panel tras loguearse
    respuesta = client.post('/login', data=datos_login, follow_redirects=True)
    
    assert respuesta.status_code == 200
    texto_html = respuesta.data.decode('utf-8')
    assert "Bienvenido, supervisor" in texto_html

# ==========================================
# CASO 4: CONTROL DE ACCESO POR ROL (US-03)
# ==========================================
def test_operador_no_accede_panel(client):
    """Prueba que el Operador no pueda entrar a /panel (Solo Supervisor)"""
    # 1. Logueamos al operador
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'}, follow_redirects=True)
    
    # 2. Intenta entrar al panel gerencial
    respuesta = client.get('/panel', follow_redirects=True)
    
    # 3. El decorador @role_required debe atajarlo y mostrar el error de permisos
    texto_html = respuesta.data.decode('utf-8')
    assert "No tenés permisos para acceder a esta pantalla" in texto_html

# ==========================================
# CASO 5: VALIDACIÓN LEGAL - LEY 25.326 (US-01 / NFR-04)
# ==========================================
def test_alta_envio_requiere_ley(client):
    """Prueba que no se pueda crear envío sin marcar 'acepta_ley'"""
    # 1. Logueamos al operador
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'}, follow_redirects=True)
    
    # 2. Mandamos todos los campos llenos pero SIN enviar 'acepta_ley'
    datos_formulario = {
        'remitente_nombre': 'Juan', 'remitente_dni': '111', 
        'remitente_direccion': 'Dir 1', 'remitente_telefono': '123', 'remitente_email': 'a@a.com',
        'destinatario_nombre': 'Maria', 'destinatario_dni': '222', 
        'destinatario_direccion': 'Dir 2', 'destinatario_telefono': '321', 'destinatario_email': 'b@b.com',
        'origen': 'A', 'destino': 'B', 'peso': '10', 'dimensiones': '1x1x1'
    }
    
    respuesta = client.post('/envios/nuevo', data=datos_formulario, follow_redirects=True)
    
    # 3. El sistema debe rebotar la petición y mostrar la validación legal
    texto_html = respuesta.data.decode('utf-8')
    assert "Debés aceptar términos y política de privacidad" in texto_html

# ==========================================
# CASO 6: MANEJO DE ERRORES (US-12)
# ==========================================
def test_error_404_ruta_inexistente(client):
    """Prueba el comportamiento del sistema ante una URL inventada"""
    respuesta = client.get('/ruta-que-no-existe')
    assert respuesta.status_code == 404
