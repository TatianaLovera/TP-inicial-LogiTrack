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

# ==========================================
# CASO 7: SEGURIDAD DE CREDENCIALES
# ==========================================
def test_login_fallido_credenciales_invalidas(client):
    """Prueba que el sistema rechace contraseñas incorrectas y no inicie sesión"""
    datos_login = {
        'usuario': 'supervisor', 
        'password': 'clave-inventada-123'
    }
    respuesta = client.post('/login', data=datos_login, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # Debe volver a mostrar el login y la alerta de error
    assert "Usuario o contraseña incorrectos" in texto_html
    assert "Bienvenido" not in texto_html

# ==========================================
# CASO 8: DESTRUCCIÓN DE SESIÓN (US-27)
# ==========================================
def test_logout_destruye_sesion(client):
    """Prueba que al hacer logout la sesión se limpie y las rutas se bloqueen"""
    # 1. Iniciamos sesión
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    
    # 2. Hacemos logout
    respuesta_logout = client.get('/logout', follow_redirects=True)
    texto_logout = respuesta_logout.data.decode('utf-8')
    assert "Sesión cerrada correctamente" in texto_logout
    
    # 3. Intentamos entrar a una ruta protegida
    respuesta_restringida = client.get('/envios')
    assert respuesta_restringida.status_code == 302 # Nos rebota al login

# ==========================================
# CASO 9: ROBUSTECIMIENTO DE FORMULARIOS (Task-17)
# ==========================================
def test_alta_envio_faltan_datos_obligatorios(client):
    """Prueba que el sistema no guarde envíos con campos vacíos"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'}, follow_redirects=True)
    
    # Mandamos el formulario pero intencionalmente sin "peso" y sin "origen"
    datos_incompletos = {
        'remitente_nombre': 'Juan', 'remitente_dni': '111', 
        'remitente_direccion': 'Dir 1', 'remitente_telefono': '123',
        'destinatario_nombre': 'Maria', 'destinatario_dni': '222', 
        'destinatario_direccion': 'Dir 2', 'destinatario_telefono': '321',
        'acepta_ley': 'on'
    }
    
    respuesta = client.post('/envios/nuevo', data=datos_incompletos, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # El backend debe frenarlo
    assert "Por favor completá todos los campos obligatorios" in texto_html

# ==========================================
# CASO 10: REGLAS DE NEGOCIO - LOGÍSTICA (US-05 / NFR-05)
# ==========================================
def test_supervisor_transito_sin_transportista(client):
    """Prueba que no se pueda pasar a 'En tránsito' sin asignar un chofer"""
    # Usamos la cuenta del supervisor
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'}, follow_redirects=True)
    
    # Buscamos dinámicamente un paquete que esté "Ingresado" o "En sucursal"
    from app import envios
    envio_valido = next((e for e in envios if e["estado"] in ["Ingresado", "En sucursal"]), None)
    tracking_de_prueba = envio_valido['tracking_id']
    
    datos_estado = {
        'nuevo_estado': 'En tránsito',
        'transportista': '' # Dejamos el chofer vacío intencionalmente
    }
    
    respuesta = client.post(f'/envios/{tracking_de_prueba}/cambiar-estado', data=datos_estado, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # El sistema debe bloquear la transición exigiendo un transportista
    assert "debés asignar un transportista" in texto_html

# ==========================================
# CASO 11: REGLAS DE NEGOCIO - ESTADOS FINALES (US-05)
# ==========================================
def test_modificar_estado_final_bloqueado(client):
    """Prueba que un paquete 'Entregado' o 'Cancelado' sea inmutable"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'}, follow_redirects=True)
    
    # Buscamos un envío que ya esté "Entregado" en los datos semilla de app.py
    from app import envios
    envio_entregado = next((e for e in envios if e["estado"] == "Entregado"), None)
    
    if envio_entregado:
        datos_estado = {'nuevo_estado': 'En tránsito'}
        respuesta = client.post(f'/envios/{envio_entregado["tracking_id"]}/cambiar-estado', data=datos_estado, follow_redirects=True)
        texto_html = respuesta.data.decode('utf-8')
        
        # El sistema debe proteger la integridad del estado final
        assert "Este envío está en un estado final y no puede ser modificado" in texto_html

# ==========================================
# CASO 12: HACKING DE ROLES (US-09)
# ==========================================
def test_operador_cambiando_a_entregado(client):
    """Prueba de seguridad: Un operador intentando forzar un estado no permitido"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'}, follow_redirects=True)
    
    from app import envios
    tracking_de_prueba = envios[0]['tracking_id']
    
    # El operador intenta mandar un POST directo saltándose la UI para poner "Entregado"
    datos_estado = {'nuevo_estado': 'Entregado'}
    respuesta = client.post(f'/envios/{tracking_de_prueba}/cambiar-estado', data=datos_estado, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # El backend debe rechazar la operación (Solo puede pasar a Cancelado si está Ingresado)
    assert "No tenés permisos para realizar ese cambio de estado" in texto_html

# ==========================================
# HELPERS (Funciones de apoyo para los tests)
# ==========================================
def obtener_datos_envio_perfecto():
    """Devuelve un diccionario con datos válidos para reutilizar en los tests de Alta"""
    return {
        'remitente_nombre': 'Carlos Test', 'remitente_dni': '12345678', 
        'remitente_direccion': 'Calle Falsa 123', 'remitente_telefono': '11223344', 'remitente_email': 'c@c.com',
        'destinatario_nombre': 'Ana Test', 'destinatario_dni': '87654321', 
        'destinatario_direccion': 'Av Siempre 742', 'destinatario_telefono': '55443322', 'destinatario_email': 'a@a.com',
        'origen': 'CABA', 'destino': 'Rosario', 'peso': '2.5', 'dimensiones': '10x10x10',
        'acepta_ley': 'on'
    }

def simular_alta_envio(client):
    """Loguea al operador y manda el formulario. Retorna la respuesta y la lista de envíos"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    respuesta = client.post('/envios/nuevo', data=obtener_datos_envio_perfecto(), follow_redirects=True)
    from app import envios
    return respuesta, envios

# ==========================================
# CASO 13: ALTA DE ENVÍO - ATÓMICOS (US-01)
# ==========================================

def test_alta_envio_guarda_datos_correctamente(client):
    """Prueba EXCLUSIVAMENTE que los datos viajen del form a la base de datos"""
    _, envios = simular_alta_envio(client)
    ultimo_envio = envios[-1]
    
    # Verificamos integridad de datos ingresados
    assert ultimo_envio['remitente']['nombre'] == 'Carlos Test'
    assert ultimo_envio['destino'] == 'Rosario'

def test_alta_envio_genera_tracking_id_valido(client):
    """Prueba EXCLUSIVAMENTE la regla de negocio de generación de Tracking ID"""
    _, envios = simular_alta_envio(client)
    tracking_generado = envios[-1]['tracking_id']
    
    # Verificamos el formato del ID
    assert tracking_generado.startswith('LT-')
    assert len(tracking_generado) > 5

def test_alta_envio_asigna_estado_inicial_ingresado(client):
    """Prueba EXCLUSIVAMENTE que el estado por defecto sea 'Ingresado'"""
    _, envios = simular_alta_envio(client)
    estado_asignado = envios[-1]['estado']
    
    # Verificamos la regla de estado inicial
    assert estado_asignado == 'Ingresado'

def test_alta_envio_muestra_mensaje_exito(client):
    """Prueba EXCLUSIVAMENTE la respuesta visual (UI) para el usuario"""
    respuesta, _ = simular_alta_envio(client)
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos el feedback del sistema
    assert "Envío creado con tracking ID" in texto_html

# ==========================================
# CASO 14: SEGURIDAD EN ALTA DE ENVÍO (US-01)
# ==========================================
def test_alta_envio_rol_no_autorizado(client):
    """Prueba que un Transportista NO pueda acceder ni crear envíos (Romper el sistema)"""
    # 1. Nos logueamos como Transportista (Rol más bajo)
    client.post('/login', data={'usuario': 'transportista', 'password': 'tra123'}, follow_redirects=True)
    
    # 2. Intentamos entrar por la fuerza a la pantalla de nuevo envío
    respuesta = client.get('/envios/nuevo', follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # 3. El decorador de Flask debería patearnos afuera
    assert "No tenés permisos para acceder a esta pantalla" in texto_html
