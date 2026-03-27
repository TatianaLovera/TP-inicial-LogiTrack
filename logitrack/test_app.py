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

# ==========================================
# CASO 15: LISTADO GENERAL DE ENVÍOS (US-02)
# ==========================================

def test_listado_envios_muestra_columnas_correctas(client):
    """Prueba el CAMINO FELIZ: Que la tabla renderice los encabezados y datos clave"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    respuesta = client.get('/envios')
    assert respuesta.status_code == 200
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos los Criterios de Aceptación (Columnas visibles)
    assert "Tracking ID" in texto_html
    assert "Remitente" in texto_html
    assert "Destinatario" in texto_html
    assert "Estado" in texto_html
    
    # Verificamos que al menos un paquete real se esté mostrando en pantalla
    from app import envios
    if envios: # Tomamos el tracking del paquete más reciente
        tracking_reciente = envios[-1]['tracking_id']
        assert tracking_reciente in texto_html

def test_listado_envios_paginacion_dinamica(client):
    """Prueba el CAMINO FELIZ: Que la paginación funcione sin romper la app"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    # Forzamos al sistema a ir a la página 2
    respuesta = client.get('/envios?page=2')
    assert respuesta.status_code == 200
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos que el control de paginación nos confirme que estamos en la pág 2
    assert "Página 2" in texto_html

def test_listado_envios_busqueda_sin_resultados(client):
    """Prueba EDGE CASE (Romper todo): Búsqueda de un ID que no existe"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    # Le mandamos basura al buscador por la URL
    respuesta = client.get('/envios?q=TRACKING-FALSO-999X')
    assert respuesta.status_code == 200
    texto_html = respuesta.data.decode('utf-8')
    
    # El sistema no debe crashear, sino mostrar el "Empty State" amigable
    assert "No se encontraron resultados para" in texto_html
    # Como app.py usa .lower(), buscamos la cadena en minúsculas
    assert "tracking-falso-999x" in texto_html

def test_listado_envios_seguridad_transportista(client):
    """Prueba SEGURIDAD: Un rol inferior no debe poder ver el listado general"""
    # Nos logueamos como el chofer (Transportista)
    client.post('/login', data={'usuario': 'transportista', 'password': 'tra123'})
    
    # Intenta entrar al listado general
    respuesta = client.get('/envios', follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # El sistema (gracias al decorador @role_required) debe bloquear el acceso
    assert "No tenés permisos para acceder a esta pantalla" in texto_html

# ==========================================
# HELPERS PARA US-03
# ==========================================
def obtener_tracking_semilla():
    """Obtiene un ID real de los datos de ejemplo cargados al iniciar la app"""
    from app import envios
    return envios[0]['tracking_id'] # Agarramos el primero ("Juan Pérez")

# ==========================================
# CASO 16: DETALLE DE ENVÍO - ATÓMICOS (US-03)
# ==========================================

def test_detalle_supervisor_ve_datos_personales(client):
    """Prueba AC3: El Supervisor debe ver DNI, teléfono y dirección exacta"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    tracking = obtener_tracking_semilla()
    
    respuesta = client.get(f'/envios/{tracking}')
    texto_html = respuesta.data.decode('utf-8')
    
    # En app.py el primer remitente semilla es "Juan Pérez", DNI "12345678"
    assert "DNI: 12345678" in texto_html
    assert "11-2345-6789" in texto_html # Teléfono

def test_detalle_operador_no_ve_datos_personales(client):
    """Prueba AC1 y AC2: Privacidad Ley 25.326. El Operador NO debe ver datos sensibles"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    tracking = obtener_tracking_semilla()
    
    respuesta = client.get(f'/envios/{tracking}')
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos que los datos logísticos sí estén...
    assert tracking in texto_html
    
    # ...Pero que la info personal esté censurada por el HTML
    assert "DNI: 12345678" not in texto_html
    assert "11-2345-6789" not in texto_html

def test_detalle_supervisor_genera_auditoria(client):
    """Prueba AC4: Trazabilidad. Ver el detalle como Supervisor debe dejar registro"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    tracking = obtener_tracking_semilla()
    
    from app import audit_logs
    cantidad_logs_antes = len(audit_logs)
    
    # El supervisor entra a ver el detalle
    client.get(f'/envios/{tracking}')
    
    # Verificamos silenciosamente la lista de auditoría en memoria
    cantidad_logs_despues = len(audit_logs)
    assert cantidad_logs_despues > cantidad_logs_antes
    assert audit_logs[-1]['accion'] == "Consulta"
    assert audit_logs[-1]['tracking_id'] == tracking

def test_detalle_historial_visible(client):
    """Prueba AC5: La línea de tiempo de estados debe renderizarse"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    tracking = obtener_tracking_semilla()
    
    respuesta = client.get(f'/envios/{tracking}')
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos que la clase CSS del timeline que usás en detalle.html esté presente
    assert "timeline-item" in texto_html
    assert "Ingresado" in texto_html

def test_detalle_transportista_espiando_paquete_ajeno(client):
    """Prueba EDGE CASE: Un transportista intenta ver un paquete que no tiene asignado"""
    client.post('/login', data={'usuario': 'transportista', 'password': 'tra123'})
    
    # Buscamos el paquete de "Tech S.A.", que en app.py tiene transportista = None
    from app import envios
    envio_ajeno = next(e for e in envios if e["remitente"]["nombre"] == "Tech S.A.")
    
    respuesta = client.get(f'/envios/{envio_ajeno["tracking_id"]}', follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # Ahora sí, al no ser su paquete, el sistema debe echarlo
    assert "No tenés permisos para ver este envío" in texto_html

# ==========================================
# CASO 17: BÚSQUEDA Y FILTRADO - ATÓMICOS (US-04)
# ==========================================

def test_busqueda_tracking_id_exacto(client):
    """Prueba AC1: Búsqueda exacta por Tracking ID"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    
    # Tomamos un ID real generado dinámicamente
    from app import envios
    tracking_buscado = envios[0]['tracking_id']
    
    respuesta = client.get(f'/envios?q={tracking_buscado}')
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos que encuentre el paquete
    assert tracking_buscado in texto_html
    # Y verificamos que NO muestre la pantalla de "sin resultados"
    assert "No se encontraron resultados" not in texto_html

def test_busqueda_parcial_destinatario_insensitive(client):
    """Prueba AC2: Búsqueda parcial y sin distinguir mayúsculas/minúsculas"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    
    # Buscamos "mArÍa" (mezcla intencional de mayúsculas/minúsculas y tildes)
    # En app.py tenemos de destinatario a "María García"
    respuesta = client.get('/envios?q=mArÍa')
    texto_html = respuesta.data.decode('utf-8')
    
    # El sistema backend (.lower()) debe saber emparejarlo
    assert "María García" in texto_html

def test_busqueda_filtros_combinados_fechas(client):
    """Prueba AC3: Combinar búsqueda de texto con filtro de rango de fechas"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    from app import envios
    tracking_buscado = envios[0]['tracking_id']
    
    # Le mandamos por URL la query "q" + los campos "date_from" y "date_to"
    # Usamos un rango de fechas amplio (2020 a 2030) para asegurar que el paquete entre
    respuesta = client.get(f'/envios?q={tracking_buscado}&date_from=2020-01-01&date_to=2030-12-31')
    
    # El sistema no debe crashear por procesar ambos filtros juntos (200 OK)
    assert respuesta.status_code == 200
    texto_html = respuesta.data.decode('utf-8')
    assert tracking_buscado in texto_html

def test_busqueda_muestra_boton_limpiar(client):
    """Prueba AC5: Comportamiento de la UI al tener un filtro activo"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    
    # Hacemos una búsqueda cualquiera
    respuesta = client.get('/envios?q=Perez')
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos que el Jinja en listar.html dibuje el botón secundario "Limpiar"
    assert "Limpiar" in texto_html
    # Verificamos que el input de búsqueda no se borre y conserve lo que el usuario escribió
    assert 'value="perez"' in texto_html.lower()

# ==========================================
# CASO 18: CAMBIO DE ESTADO - ATÓMICOS (US-05)
# ==========================================

def test_operador_cancela_envio_ingresado(client):
    """Prueba AC6: El sistema permite al Operador cancelar un envío recién ingresado"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    
    # Buscamos dinámicamente un paquete "Ingresado"
    from app import envios
    envio = next(e for e in envios if e["estado"] == "Ingresado")
    
    respuesta = client.post(f'/envios/{envio["tracking_id"]}/cambiar-estado', 
                            data={'nuevo_estado': 'Cancelado'}, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    assert "Estado actualizado a: Cancelado" in texto_html

def test_supervisor_transicion_logica_invalida(client):
    """Prueba EDGE CASE: Evitar saltos de estado mágicos (Ingresado -> Entregado)"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    from app import envios
    # Buscamos uno "Ingresado"
    envio = next(e for e in envios if e["estado"] == "Ingresado")
    
    # Intentamos saltarnos toda la cadena logística
    respuesta = client.post(f'/envios/{envio["tracking_id"]}/cambiar-estado', 
                            data={'nuevo_estado': 'Entregado'}, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # Tu diccionario 'transitions' en app.py es brillante y debería frenar esto
    assert "No tenés permisos para realizar ese cambio de estado" in texto_html

def test_flujo_retorno_vuelve_remitente(client):
    """Prueba AC11: Flujo válido de Visita Fallida a Vuelve a remitente"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    from app import envios
    envio = next(e for e in envios if e["estado"] == "Visita Fallida")
    
    respuesta = client.post(f'/envios/{envio["tracking_id"]}/cambiar-estado', 
                            data={'nuevo_estado': 'Vuelve a remitente'}, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    assert "Estado actualizado a: Vuelve a remitente" in texto_html

def test_cambio_estado_registra_auditoria(client):
    """Prueba AC7: El cambio de estado alimenta el Log de Auditoría interno"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    from app import envios, audit_logs
    envio = next(e for e in envios if e["estado"] == "En sucursal")
    logs_antes = len(audit_logs)
    
    # Hacemos el cambio enviando todos los datos
    client.post(f'/envios/{envio["tracking_id"]}/cambiar-estado', 
                data={'nuevo_estado': 'En tránsito', 'transportista': 'Juan Perez', 'nota': 'Sale a reparto'}, 
                follow_redirects=True)
    
    # Aislamos solo los logs que se agregaron en este último segundo
    nuevos_logs = audit_logs[logs_antes:]
    
    # Buscamos el log específico de cambio de estado ignorando el de "Consulta"
    log_cambio = next((log for log in nuevos_logs if log["accion"] == "Cambio de estado"), None)
    
    # Verificamos que efectivamente se haya creado
    assert log_cambio is not None
    assert "En sucursal → En tránsito" in log_cambio["detalle"]
    assert "Sale a reparto" in log_cambio["detalle"]

# ==========================================
# TEST TDD PARA COMPLETAR EL CÓDIGO (AC10)
# ==========================================
def test_retiro_sucursal_requiere_dni(client):
    """Prueba AC10 (NFR-02): Validar DNI al entregar en sucursal. 
       ⚠️ ESTE TEST FALLARÁ hasta que modifiques app.py"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    from app import envios
    envio = next(e for e in envios if e["estado"] == "En sucursal")
    
    # Intentamos entregar SIN enviar el DNI de quien retira
    respuesta = client.post(f'/envios/{envio["tracking_id"]}/cambiar-estado', 
                            data={'nuevo_estado': 'Entregado'}, follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # El test exige que tu sistema rechace el intento mostrando este mensaje
    assert "Debe ingresar el DNI de quien retira" in texto_html

# ==========================================
# CASO 19: AUDITORÍA DE EDICIÓN - ATÓMICOS (US-06)
# ==========================================

def test_editar_envio_registra_auditoria_valores(client):
    """Prueba AC1: Editar datos de cliente guarda el valor viejo y el nuevo en el log"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    from app import envios, audit_logs
    # Tomamos el primer paquete que es editable (Juan Pérez)
    envio = envios[0] 
    tracking = envio["tracking_id"]
    nombre_viejo = envio["remitente"]["nombre"]
    nombre_nuevo = "Juan Editado Test"
    
    logs_antes = len(audit_logs)
    
    # Preparamos todos los datos requeridos para la edición, cambiando solo el nombre
    datos_edicion = {
        'remitente_nombre': nombre_nuevo,
        'remitente_dni': envio['remitente']['dni'],
        'remitente_direccion': envio['remitente']['direccion'],
        'remitente_telefono': envio['remitente']['telefono'],
        'remitente_email': envio['remitente']['email'],
        'destinatario_nombre': envio['destinatario']['nombre'],
        'destinatario_dni': envio['destinatario']['dni'],
        'destinatario_direccion': envio['destinatario']['direccion'],
        'destinatario_telefono': envio['destinatario']['telefono'],
        'destinatario_email': envio['destinatario']['email'],
        'origen': envio['origen'],
        'destino': envio['destino'],
        'peso': envio['peso'],
        'dimensiones': envio['dimensiones'],
        'descripcion': envio['descripcion']
    }
    
    client.post(f'/envios/{tracking}/editar', data=datos_edicion, follow_redirects=True)
    
    # Verificamos que se haya generado el log de "Edición"
    nuevos_logs = audit_logs[logs_antes:]
    log_edicion = next((log for log in nuevos_logs if log["accion"] == "Edición"), None)
    
    assert log_edicion is not None
    # Verificamos la regla de oro: Que quede guardado lo que era y lo que es ahora
    assert nombre_viejo in log_edicion["detalle"]
    assert nombre_nuevo in log_edicion["detalle"]
    assert "→" in log_edicion["detalle"] # Símbolo que programaste en app.py

def test_auditoria_pantalla_acceso_supervisor(client):
    """Prueba AC3: El Supervisor puede acceder a la pantalla y ver la tabla"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    respuesta = client.get('/auditoria')
    assert respuesta.status_code == 200
    
    texto_html = respuesta.data.decode('utf-8')
    assert "Auditoría" in texto_html
    assert "Acción" in texto_html
    assert "Detalle" in texto_html

def test_auditoria_pantalla_bloqueo_operador(client):
    """Prueba EDGE CASE de Seguridad: El Operador tiene prohibido ver la bitácora"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    
    respuesta = client.get('/auditoria', follow_redirects=True)
    texto_html = respuesta.data.decode('utf-8')
    
    # El sistema debe echarlo
    assert "No tenés permisos para acceder a esta pantalla" in texto_html

def test_auditoria_inmutabilidad_bloqueo_metodos(client):
    """Prueba AC2: Inmutabilidad. Nadie puede inyectar o borrar logs por la fuerza"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    # Un "hacker" intenta enviar una orden de BORRADO a la ruta de auditoría
    respuesta_delete = client.delete('/auditoria')
    
    # Un "hacker" intenta INYECTAR un log falso enviando un formulario POST a la ruta
    respuesta_post = client.post('/auditoria', data={'accion': 'Falsa'})
    
    # Flask es seguro por defecto: Al no haber habilitado methods=['POST', 'DELETE'] 
    # en el @app.route de app.py, debe devolver HTTP 405 (Método no permitido)
    assert respuesta_delete.status_code == 405
    assert respuesta_post.status_code == 405

# ==========================================
# CASO 19: HISTORIAL VISIBLE - ATÓMICOS (US-07)
# ==========================================

def test_historial_estado_inicial_tras_alta(client):
    """Prueba AC4: Un envío recién creado muestra inmediatamente su evento original de creación"""
    client.post('/login', data={'usuario': 'operador', 'password': 'op123'})
    
    # Preparamos datos mínimos obligatorios para crear un envío rápido
    datos_minimos = {
        'remitente_nombre': 'A', 'remitente_dni': '1', 'remitente_direccion': 'A', 'remitente_telefono': '1', 'remitente_email': 'a@a.com',
        'destinatario_nombre': 'B', 'destinatario_dni': '2', 'destinatario_direccion': 'B', 'destinatario_telefono': '2', 'destinatario_email': 'b@b.com',
        'origen': 'C', 'destino': 'D', 'peso': '1', 'dimensiones': '1x1', 'acepta_ley': 'on'
    }
    client.post('/envios/nuevo', data=datos_minimos, follow_redirects=True)
    
    # Vamos al detalle del último envío creado
    from app import envios
    ultimo_tracking = envios[-1]["tracking_id"]
    
    respuesta = client.get(f'/envios/{ultimo_tracking}')
    texto_html = respuesta.data.decode('utf-8')
    
    # Verificamos que la nota dura que pusiste en app.py aparezca en el HTML
    assert "Envío creado en el sistema" in texto_html
    assert "Ingresado" in texto_html

def test_historial_muestra_datos_completos_evento(client):
    """Prueba AC2: El historial renderiza fecha, estado y notas del Mock API"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    # Tomamos un paquete semilla de app.py que ya tenga historial avanzado (más de 1 evento)
    from app import envios
    envio_avanzado = next(e for e in envios if len(e["historial"]) > 1)
    tracking = envio_avanzado["tracking_id"]
    
    # Agarramos el último evento de la lista de ese paquete
    ultimo_evento = envio_avanzado["historial"][-1]
    
    respuesta = client.get(f'/envios/{tracking}')
    texto_html = respuesta.data.decode('utf-8')
    
    # Comprobamos que los datos exactos del diccionario se hayan inyectado en el HTML
    assert ultimo_evento["estado"] in texto_html
    assert ultimo_evento["fecha"] in texto_html
    assert ultimo_evento["nota"] in texto_html

def test_historial_agrega_nuevo_evento_dinamicamente(client):
    """Prueba EDGE CASE / AC3: Cambiar el estado suma un nodo visual sin borrar los viejos"""
    client.post('/login', data={'usuario': 'supervisor', 'password': 'sup123'})
    
    from app import envios
    envio = next(e for e in envios if e["estado"] == "Ingresado")
    tracking = envio["tracking_id"]
    
    # Hacemos un cambio de estado inyectando una nota de prueba MUY específica
    nota_unica = "NOTA_TEST_HISTORIAL_999"
    client.post(f'/envios/{tracking}/cambiar-estado', 
                data={'nuevo_estado': 'Cancelado', 'nota': nota_unica}, 
                follow_redirects=True)
    
    # Entramos a ver el detalle
    respuesta = client.get(f'/envios/{tracking}')
    texto_html = respuesta.data.decode('utf-8')
    
    # 1. Verificamos que el evento original (Ingresado) siga existiendo
    assert "Envío creado en el sistema" in texto_html
    
    # 2. Verificamos que el nuevo evento se haya sumado a la pantalla
    assert nota_unica in texto_html
    assert "Cancelado" in texto_html
