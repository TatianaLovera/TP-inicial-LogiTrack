from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import jsonify
import uuid
import datetime
import joblib
import random
import re
from math import ceil
import pandas as pd

app = Flask(__name__)
app.secret_key = "logitrack-secret-2024"

envios = []
audit_logs = []

# Cargar el modelo de IA en memoria
try:
    modelo_ia = joblib.load('models/modelo_prioridad.pkl')
    print("🤖 Modelo de IA cargado correctamente y listo para predecir.")
except Exception as e:
    modelo_ia = None
    print("⚠️ No se encontró el modelo de IA. Primero ejecutá ml_prioridad.py")

USUARIOS = {
    "operador": {"password": "op123", "rol": "Operador"},
    "supervisor": {"password": "sup123", "rol": "Supervisor"},
    "transportista": {"password": "tra123", "rol": "Transportista"},
}

ESTADOS = [
    "Ingresado",
    "En tránsito",
    "En sucursal",
    "Entregado",
    "Cancelado",
    "Visita Fallida",
    "Vuelve a remitente",
    "Entregado a remitente",
]


def generar_tracking_id():
    return "LT-" + str(uuid.uuid4()).upper()[:8]


def usuario_logueado():
    return "usuario" in session


def get_usuario():
    return session.get("usuario"), session.get("rol")


def get_usuario_context():
    usuario, rol = get_usuario()
    return {"usuario": usuario, "rol": rol}


def ahora():
    return datetime.datetime.now()


def ahora_str():
    return ahora().strftime("%d/%m/%Y %H:%M")


def parse_fecha(fecha_str):
    return datetime.datetime.strptime(fecha_str, "%d/%m/%Y %H:%M")


def puede_editar_envio(envio):
    _, rol = get_usuario()
    if rol != "Supervisor":
        return False
    # Estados finales - no se pueden editar
    estados_finales = ["Cancelado", "Entregado", "Entregado a remitente"]
    if envio["estado"] in estados_finales:
        return False
    return ahora() - parse_fecha(envio["fecha_creacion"]) <= datetime.timedelta(days=5)


def validar_dni(dni):
    """Valida que el DNI pertenezca a rangos válidos, excluyendo el salto administrativo."""
    if not bool(re.match(r"^\d+$", dni)):
        return False
        
    dni_num = int(dni)
    
    # Argentinos nativos (antes del salto administrativo)
    es_nativo_1 = 1500000 <= dni_num <= 59999999
    
    # Argentinos nativos (después del salto administrativo)
    es_nativo_2 = 70000000 <= dni_num <= 72000000
    
    # Extranjeros residentes
    es_extranjero = 92000000 <= dni_num <= 96000000
    
    # Si es 65.000.000, las tres variables darán False, rechazando el DNI.
    return es_nativo_1 or es_nativo_2 or es_extranjero


def validar_telefono(telefono):
    """Valida que el teléfono tenga solo números (ignorando guiones y espacios)"""
    # Limpiamos guiones y espacios para la validación
    telefono_limpio = telefono.replace("-", "").replace(" ", "")
    return bool(re.match(r"^\d+$", telefono_limpio)) and len(telefono_limpio) >= 6


def validar_email(email):
    """Valida que el email tenga formato válido: una arroba y un dominio con extensión"""
    if email == "":
        return True  # Email es opcional
    # Patrón: algo@algo.extensión
    patron = r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(patron, email))


def registrar_auditoria(tracking_id, accion, detalle, usuario=None):
    if usuario is None:
        usuario, _ = get_usuario()
    audit_logs.append({
        "tracking_id": tracking_id,
        "accion": accion,
        "detalle": detalle,
        "usuario": usuario or "sistema",
        "fecha": ahora_str(),
    })


def destino_post_login():
    rol = session.get("rol")
    if rol == "Supervisor":
        return url_for("panel")
    if rol == "Transportista":
        return url_for("hoja_ruta")
    return url_for("listar_envios")


def role_required(*roles):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if not usuario_logueado():
                return redirect(url_for("login"))
            if session.get("rol") not in roles:
                flash("No tenés permisos para acceder a esta pantalla.", "error")
                return redirect(destino_post_login())
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


@app.route("/")
def index():
    if usuario_logueado():
        return redirect(destino_post_login())
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()
        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            session["usuario"] = usuario
            session["rol"] = USUARIOS[usuario]["rol"]
            flash(f"Bienvenido, {usuario} ({USUARIOS[usuario]['rol']})", "success")
            return redirect(destino_post_login())
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


@app.route("/panel")
@role_required("Supervisor")
def panel():
    stats = {estado: 0 for estado in ESTADOS}
    for e in envios:
        stats[e["estado"]] += 1
    recientes = sorted(envios, key=lambda x: parse_fecha(x["fecha_creacion"]), reverse=True)[:5]
    return render_template(
        "panel.html",
        envios=recientes,
        stats=stats,
        total=len(envios),
        **get_usuario_context(),
    )


@app.route("/envios")
@role_required("Supervisor", "Operador")
def listar_envios():
    busqueda = request.args.get("q", "").strip().lower()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    sort_by = request.args.get("sort", "fecha_creacion")
    sort_order = request.args.get("order", "desc")
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    per_page = 10

    resultado = sorted(envios, key=lambda x: parse_fecha(x["fecha_creacion"]), reverse=True)
    
    # Apply text search filter
    if busqueda:
        resultado = [
            e for e in resultado
            if busqueda in e["tracking_id"].lower()
            or busqueda in e["destinatario"]["nombre"].lower()
            or busqueda in e["remitente"]["nombre"].lower()
        ]
    
    # Apply date range filter
    if date_from or date_to:
        filtered = []
        for e in resultado:
            fecha_envio = parse_fecha(e["fecha_creacion"])
            include = True
            
            if date_from:
                try:
                    fecha_desde = datetime.datetime.strptime(date_from, "%Y-%m-%d")
                    if fecha_envio.date() < fecha_desde.date():
                        include = False
                except ValueError:
                    pass  # Invalid date format, ignore filter
            
            if date_to:
                try:
                    fecha_hasta = datetime.datetime.strptime(date_to, "%Y-%m-%d")
                    if fecha_envio.date() > fecha_hasta.date():
                        include = False
                except ValueError:
                    pass  # Invalid date format, ignore filter
            
            if include:
                filtered.append(e)
        resultado = filtered

    # Apply sorting
    sort_key_map = {
        "tracking_id": lambda x: x["tracking_id"],
        "remitente": lambda x: x["remitente"]["nombre"].lower(),
        "destinatario": lambda x: x["destinatario"]["nombre"].lower(),
        "origen": lambda x: x["origen"].lower(),
        "destino": lambda x: x["destino"].lower(),
        "estado": lambda x: x["estado"],
        "peso": lambda x: float(x["peso"]),
        "fecha_creacion": lambda x: parse_fecha(x["fecha_creacion"])
    }
    
    if sort_by in sort_key_map:
        resultado.sort(key=sort_key_map[sort_by], reverse=(sort_order == "desc"))

    total_items = len(resultado)
    total_pages = max(ceil(total_items / per_page), 1)
    if page > total_pages:
        page = total_pages

    start = (page - 1) * per_page
    paginados = resultado[start:start + per_page]

    return render_template(
        "listar.html",
        envios=paginados,
        busqueda=busqueda,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        **get_usuario_context(),
    )


@app.route("/envios/nuevo", methods=["GET", "POST"])
@role_required("Supervisor", "Operador")
def nuevo_envio():
    if request.method == "POST":
        remitente_nombre = request.form.get("remitente_nombre", "").strip()
        remitente_dni = request.form.get("remitente_dni", "").strip()
        remitente_direccion = request.form.get("remitente_direccion", "").strip()
        remitente_telefono = request.form.get("remitente_telefono", "").strip()
        remitente_email = request.form.get("remitente_email", "").strip()
        destinatario_nombre = request.form.get("destinatario_nombre", "").strip()
        destinatario_dni = request.form.get("destinatario_dni", "").strip()
        destinatario_direccion = request.form.get("destinatario_direccion", "").strip()
        destinatario_telefono = request.form.get("destinatario_telefono", "").strip()
        destinatario_email = request.form.get("destinatario_email", "").strip()
        origen = request.form.get("origen", "").strip()
        destino = request.form.get("destino", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        peso = request.form.get("peso", "").strip()
        dimensiones = request.form.get("dimensiones", "").strip()
        acepta_ley = request.form.get("acepta_ley") == "on"
        
        # 👇 LÍNEA CORREGIDA: Ahora sí leemos el botón del HTML 👇
        envio_express = request.form.get("envio_express") == "on"

        if not all([remitente_nombre, remitente_dni, remitente_direccion, remitente_telefono, destinatario_nombre, destinatario_dni, destinatario_direccion, destinatario_telefono, origen, destino, peso, dimensiones]):
            flash("Por favor completá todos los campos obligatorios.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        # Validar DNI remitente
        if not validar_dni(remitente_dni):
            flash("DNI del remitente inválido (debe ser un número real entre los rangos vigentes).", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        # Validar DNI destinatario
        if not validar_dni(destinatario_dni):
            flash("DNI del destinatario inválido (debe ser un número real entre los rangos vigentes).", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        #  VALIDACIÓN: DNIs iguales 
        if remitente_dni == destinatario_dni:
            flash("El DNI del remitente y del destinatario no pueden ser el mismo.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        # Validar teléfono remitente
        if not validar_telefono(remitente_telefono):
            flash("Teléfono del remitente debe contener solo números.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        # Validar teléfono destinatario
        if not validar_telefono(destinatario_telefono):
            flash("Teléfono del destinatario debe contener solo números.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        # Validar email remitente
        if remitente_email and not validar_email(remitente_email):
            flash("Email del remitente inválido. Debe contener @ y dominio válido.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        # Validar email destinatario
        if destinatario_email and not validar_email(destinatario_email):
            flash("Email del destinatario inválido. Debe contener @ y dominio válido.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())
        
        if remitente_direccion.lower() == destinatario_direccion.lower():
            flash("La dirección del remitente y del destinatario no pueden ser la misma.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        if not acepta_ley:
            flash("Debés aceptar términos y política de privacidad para crear el envío.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        # ==========================================
        # 🤖 LÓGICA DE MACHINE LEARNING ACÁ
        # ==========================================
        peso_float = float(peso) if peso else 0.0
        distancia_simulada = random.randint(10, 2000) 
        es_express_ia = 1 if envio_express else 0
        
        prioridad_calc = "Normal" # Valor por defecto por si la IA falla
        if modelo_ia:
            try:
                datos_para_ia = pd.DataFrame(
                    [[distancia_simulada, peso_float, es_express_ia]], 
                    columns=['distancia_km', 'peso_kg', 'es_express']
                )
                pred = modelo_ia.predict(datos_para_ia)
                prioridad_calc = pred[0]
            except Exception as e:
                print(f"Error al calcular IA: {e}")
        # ==========================================

        usuario, _ = get_usuario()
        fecha = ahora_str()
        nuevo = {
            "tracking_id": generar_tracking_id(),
            "prioridad": prioridad_calc,   # <-- Resultado de la IA
            "envio_express": envio_express, # <-- Guardamos si es express o no
            "remitente": {
                "nombre": remitente_nombre,
                "dni": remitente_dni,
                "direccion": remitente_direccion,
                "telefono": remitente_telefono,
                "email": remitente_email,
            },
            "destinatario": {
                "nombre": destinatario_nombre,
                "dni": destinatario_dni,
                "direccion": destinatario_direccion,
                "telefono": destinatario_telefono,
                "email": destinatario_email,
            },
            "origen": origen,
            "destino": destino,
            "descripcion": descripcion or "Sin descripción",
            "peso": peso,
            "dimensiones": dimensiones,
            "estado": "Ingresado",
            "fecha_creacion": fecha,
            "historial": [{
                "estado": "Ingresado",
                "fecha": fecha,
                "usuario": usuario,
                "nota": "Envío creado en el sistema."
            }],
            "creado_por": usuario,
            "transportista": None,
            "acepta_ley": True,
            "acepta_ley_fecha": fecha,
        }
        envios.append(nuevo)
        registrar_auditoria(nuevo["tracking_id"], "Creación", "Alta de envío con consentimiento de privacidad.", usuario)
        flash(f"Envío creado con tracking ID: {nuevo['tracking_id']}", "success")
        return redirect(url_for("detalle_envio", tracking_id=nuevo["tracking_id"]))

    return render_template("nuevo_envio.html", form={}, **get_usuario_context())


@app.route("/envios/<tracking_id>")
def detalle_envio(tracking_id):
    if not usuario_logueado():
        return redirect(url_for("login"))
    envio = next((e for e in envios if e["tracking_id"] == tracking_id), None)
    if not envio:
        flash("Envío no encontrado.", "error")
        return redirect(destino_post_login())

    usuario, rol = get_usuario()
    if rol == "Transportista":
        if envio.get("transportista") != usuario:
            flash("No tenés permisos para ver este envío.", "error")
            return redirect(url_for("hoja_ruta"))

    if rol == "Supervisor":
        registrar_auditoria(tracking_id, "Consulta", "Acceso al detalle completo del envío.", usuario)

    return render_template(
        "detalle.html",
        envio=envio,
        estados=ESTADOS,
        puede_editar=puede_editar_envio(envio),
        **get_usuario_context(),
    )


@app.route("/envios/<tracking_id>/editar", methods=["GET", "POST"])
@role_required("Supervisor")
def editar_envio(tracking_id):
    envio = next((e for e in envios if e["tracking_id"] == tracking_id), None)
    if not envio:
        flash("Envío no encontrado.", "error")
        return redirect(url_for("listar_envios"))
    if not puede_editar_envio(envio):
        # Verificar si es porque está en estado final
        estados_finales = ["Cancelado", "Entregado", "Entregado a remitente"]
        if envio["estado"] in estados_finales:
            flash("No se puede editar un envío con estado final (Cancelado, Entregado o Entregado a remitente).", "error")
        else:
            flash("Solo se puede editar un envío durante los primeros 5 días desde su creación.", "error")
        return redirect(url_for("detalle_envio", tracking_id=tracking_id))

    if request.method == "POST":
        remitente_nombre = request.form.get("remitente_nombre", "").strip()
        remitente_dni = request.form.get("remitente_dni", "").strip()
        remitente_direccion = request.form.get("remitente_direccion", "").strip()
        remitente_telefono = request.form.get("remitente_telefono", "").strip()
        remitente_email = request.form.get("remitente_email", "").strip()
        destinatario_nombre = request.form.get("destinatario_nombre", "").strip()
        destinatario_dni = request.form.get("destinatario_dni", "").strip()
        destinatario_direccion = request.form.get("destinatario_direccion", "").strip()
        destinatario_telefono = request.form.get("destinatario_telefono", "").strip()
        destinatario_email = request.form.get("destinatario_email", "").strip()
        origen = request.form.get("origen", "").strip()
        destino = request.form.get("destino", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        peso = request.form.get("peso", "").strip()
        dimensiones = request.form.get("dimensiones", "").strip()
        envio_express = request.form.get("envio_express") == "on"

        if not all([remitente_nombre, remitente_dni, remitente_direccion, remitente_telefono, destinatario_nombre, destinatario_dni, destinatario_direccion, destinatario_telefono, origen, destino, peso, dimensiones]):
            flash("Todos los campos obligatorios deben estar completos.", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())

        # Validar DNI remitente
        if not validar_dni(remitente_dni):
            flash("DNI del remitente inválido (debe ser un número real entre los rangos vigentes).", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())

        # Validar DNI destinatario
        if not validar_dni(destinatario_dni):
            flash("DNI del destinatario inválido (debe ser un número real entre los rangos vigentes).", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())

        # VALIDACIÓN: DNIs iguales 
        if remitente_dni == destinatario_dni:
            flash("El DNI del remitente y del destinatario no pueden ser el mismo.", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())
    

        # Validar teléfono remitente
        if not validar_telefono(remitente_telefono):
            flash("Teléfono del remitente debe contener solo números.", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())

        # Validar teléfono destinatario
        if not validar_telefono(destinatario_telefono):
            flash("Teléfono del destinatario debe contener solo números.", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())

        # Validar email remitente
        if remitente_email and not validar_email(remitente_email):
            flash("Email del remitente inválido. Debe contener @ y dominio válido.", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())

        # Validar email destinatario
        if destinatario_email and not validar_email(destinatario_email):
            flash("Email del destinatario inválido. Debe contener @ y dominio válido.", "error")
            return render_template("editar_envio.html", envio=envio, **get_usuario_context())
        
        if remitente_direccion.lower() == destinatario_direccion.lower():
            flash("La dirección del remitente y del destinatario no pueden ser la misma.", "error")
            return render_template("nuevo_envio.html", form=request.form, **get_usuario_context())

        cambios = []
        def cambia(campo_path, valor_nuevo, valor_anterior):
            if valor_nuevo != valor_anterior:
                cambios.append(f"{campo_path}: '{valor_anterior}' → '{valor_nuevo}'")
                return valor_nuevo
            return valor_anterior

        envio["remitente"]["nombre"] = cambia("remitente.nombre", remitente_nombre, envio["remitente"]["nombre"])
        envio["remitente"]["dni"] = cambia("remitente.dni", remitente_dni, envio["remitente"]["dni"])
        envio["remitente"]["direccion"] = cambia("remitente.direccion", remitente_direccion, envio["remitente"]["direccion"])
        envio["remitente"]["telefono"] = cambia("remitente.telefono", remitente_telefono, envio["remitente"]["telefono"])
        envio["remitente"]["email"] = cambia("remitente.email", remitente_email, envio["remitente"]["email"])

        envio["destinatario"]["nombre"] = cambia("destinatario.nombre", destinatario_nombre, envio["destinatario"]["nombre"])
        envio["destinatario"]["dni"] = cambia("destinatario.dni", destinatario_dni, envio["destinatario"]["dni"])
        envio["destinatario"]["direccion"] = cambia("destinatario.direccion", destinatario_direccion, envio["destinatario"]["direccion"])
        envio["destinatario"]["telefono"] = cambia("destinatario.telefono", destinatario_telefono, envio["destinatario"]["telefono"])
        envio["destinatario"]["email"] = cambia("destinatario.email", destinatario_email, envio["destinatario"]["email"])

        envio["origen"] = cambia("origen", origen, envio["origen"])
        envio["destino"] = cambia("destino", destino, envio["destino"])
        envio["descripcion"] = cambia("descripcion", descripcion or "Sin descripción", envio["descripcion"])
        envio["peso"] = cambia("peso", peso, envio["peso"])
        envio["dimensiones"] = cambia("dimensiones", dimensiones, envio["dimensiones"])
        envio["envio_express"] = cambia("envio_express", envio_express, envio.get("envio_express", False))

        if cambios:
            registrar_auditoria(tracking_id, "Edición", "; ".join(cambios))
            flash("Envío actualizado correctamente.", "success")
        else:
            flash("No hubo cambios para guardar.", "info")
        return redirect(url_for("detalle_envio", tracking_id=tracking_id))

    return render_template("editar_envio.html", envio=envio, **get_usuario_context())


@app.route("/envios/<tracking_id>/cambiar-estado", methods=["POST"])
def cambiar_estado(tracking_id):
    if not usuario_logueado():
        return redirect(url_for("login"))
    
    envio = next((e for e in envios if e["tracking_id"] == tracking_id), None)
    if not envio:
        flash("Envío no encontrado.", "error")
        return redirect(destino_post_login())

    nuevo_estado = request.form.get("nuevo_estado", "").strip()
    nota = request.form.get("nota", "").strip() or "Sin nota adicional."
    transportista = request.form.get("transportista", "").strip() or None
    
    # 1. Agregamos la captura del DNI desde el formulario (si existe)
    dni_retiro = request.form.get("dni_retiro", "").strip() 
    
    usuario, rol = get_usuario()

    # Check if current state is final
    estados_finales = ["Cancelado", "Entregado", "Entregado a remitente"]
    if envio["estado"] in estados_finales:
        flash("Este envío está en un estado final y no puede ser modificado.", "error")
        return redirect(url_for("detalle_envio", tracking_id=tracking_id))

    if nuevo_estado not in ESTADOS:
        flash("Estado inválido.", "error")
        return redirect(url_for("detalle_envio", tracking_id=tracking_id))

    estado_actual = envio["estado"]
    permitido = False

    if rol == "Supervisor":
        transitions = {
            "Ingresado": ["Cancelado", "En sucursal", "En tránsito"],
            "En sucursal": ["En tránsito", "Entregado"],
            "En tránsito": ["Entregado", "Visita Fallida"],
            "Visita Fallida": ["Vuelve a remitente", "En sucursal"],
            "Vuelve a remitente": ["Entregado a remitente"],
        }
        permitido = nuevo_estado in transitions.get(estado_actual, [])
    elif rol == "Operador":
        permitido = estado_actual == "Ingresado" and nuevo_estado == "Cancelado"
    elif rol == "Transportista":
        permitido = envio.get("transportista") == usuario and estado_actual == "En tránsito" and nuevo_estado in ["Entregado", "Visita Fallida"]

    if not permitido:
        flash("No tenés permisos para realizar ese cambio de estado.", "error")
        return redirect(url_for("detalle_envio", tracking_id=tracking_id))

    if nuevo_estado == "En tránsito" and rol == "Supervisor" and not transportista:
        flash("Para pasar a 'En tránsito' debés asignar un transportista.", "error")
        return redirect(url_for("detalle_envio", tracking_id=tracking_id))

    # 2. INICIO DE LA NUEVA VALIDACIÓN LOGÍSTICA (AC10)
    if estado_actual == "En sucursal" and nuevo_estado == "Entregado" and not dni_retiro:
        flash("Debe ingresar el DNI de quien retira.", "error")
        return redirect(url_for("detalle_envio", tracking_id=tracking_id))
    
    if dni_retiro:
        nota = f"Retirado por DNI: {dni_retiro} - {nota}"

    if transportista:
        envio["transportista"] = transportista

    envio["historial"].append({
        "estado": nuevo_estado,
        "fecha": ahora_str(),
        "usuario": usuario,
        "nota": nota,
    })
    envio["estado"] = nuevo_estado
    registrar_auditoria(tracking_id, "Cambio de estado", f"{estado_actual} → {nuevo_estado}. Nota: {nota}")
    flash(f"Estado actualizado a: {nuevo_estado}", "success")
    return redirect(url_for("detalle_envio", tracking_id=tracking_id))


@app.route("/auditoria")
@role_required("Supervisor")
def auditoria():
    busqueda = request.args.get("q", "").strip().lower()
    
    # Filter logs to only include state changes and data modifications
    filtered_logs = [log for log in audit_logs if log["accion"] in ["Cambio de estado", "Edición", "Creación"]]
    
    if busqueda:
        filtered_logs = [log for log in filtered_logs if busqueda in log["tracking_id"].lower()]
    
    # Group logs by tracking_id
    grouped_logs = {}
    for log in filtered_logs:
        tracking_id = log["tracking_id"]
        if tracking_id not in grouped_logs:
            grouped_logs[tracking_id] = []
        grouped_logs[tracking_id].append(log)
    
    # Sort groups by most recent log
    sorted_groups = sorted(grouped_logs.items(), key=lambda x: max(parse_fecha(log["fecha"]) for log in x[1]), reverse=True)
    
    return render_template("auditoria.html", grouped_logs=sorted_groups, busqueda=busqueda, **get_usuario_context())


@app.route("/hoja-ruta")
@role_required("Transportista")
def hoja_ruta():
    usuario, _ = get_usuario()
    asignados = [e for e in envios if e.get("transportista") == usuario and e.get("estado") == "En tránsito"]
    asignados = sorted(asignados, key=lambda x: parse_fecha(x["fecha_creacion"]), reverse=True)
    return render_template("hoja_ruta.html", envios=asignados, **get_usuario_context())


def cargar_datos_ejemplo():
    ejemplos = [
        # remitente_nombre, remitente_dni, remitente_direccion, remitente_telefono, remitente_email,
        # destinatario_nombre, destinatario_dni, destinatario_direccion, destinatario_telefono, destinatario_email,
        # origen, destino, descripcion, peso, dimensiones, estado, transportista, envio_express
        ("Juan Pérez", "12345678", "Av. Rivadavia 1234, CABA", "11-2345-6789", "juan@email.com",
         "María García", "87654321", "Bv. San Juan 567, Córdoba", "351-987-6543", "maria@email.com",
         "Buenos Aires", "Córdoba", "Documentos", "2.5", "30x20x10 cm", "En tránsito", "transportista", False),
        ("Tech S.A.", "20123456789", "Calle Falsa 123, Rosario", "341-555-0123", "contacto@tech.com",
         "Roberto López", "34567890", "Av. Libertador 890, Mendoza", "261-444-5678", "roberto@email.com",
         "Rosario", "Mendoza", "Equipo electrónico", "5", "40x30x20 cm", "En sucursal", None, False),
        ("Ana Martínez", "11223344", "Plaza Moreno 456, La Plata", "221-333-7890", "ana@email.com",
         "Carlos Rodríguez", "44332211", "Calle 24 de Septiembre 234, Tucumán", "381-222-3456", "carlos@email.com",
         "La Plata", "Tucumán", "Ropa y accesorios", "1.2", "25x20x8 cm", "Entregado", "transportista", False),
        ("Paula Díaz", "55667788", "Av. San Martín 789, Salta", "387-111-2233", "paula@email.com",
         "Néstor Ruiz", "88776655", "Bv. Pellegrini 345, Jujuy", "388-999-8765", "nestor@email.com",
         "Salta", "Jujuy", "Repuestos", "3.4", "45x25x15 cm", "Ingresado", None, False),
        ("Sol S.R.L.", "27987654321", "Florida 1000, CABA", "11-4000-5000", "ventas@sol.com",
         "Andrea Sosa", "33445566", "Av. Luro 678, Mar del Plata", "223-777-1234", "andrea@email.com",
         "CABA", "Mar del Plata", "Indumentaria", "2", "35x25x10 cm", "Cancelado", None, False),
        ("Distribuidora Norte", "27111222333", "Ruta 8 Km 45, Pilar", "2320-55-6677", "info@distnorte.com",
         "Lucía Torres", "77889900", "Av. del Trabajo 123, Tigre", "11-4747-8899", "lucia@email.com",
         "Pilar", "Tigre", "Alimentos secos", "7", "50x35x25 cm", "Visita Fallida", "transportista", False),
        ("Ramiro Gómez", "44556677", "Bv. Rondeau 567, Morón", "11-5252-3344", "ramiro@email.com",
         "Elena Paz", "77665544", "Ruta 5 Km 23, Luján", "2323-66-7788", "elena@email.com",
         "Morón", "Luján", "Libros", "4", "30x25x20 cm", "Vuelve a remitente", None, False),
        ("Papelera Sur", "27333444555", "Av. Hipólito Yrigoyen 890, Lanús", "11-4242-5566", "ventas@papelera.com",
         "Iván Núñez", "99887766", "Rivadavia 456, Quilmes", "11-4040-7788", "ivan@email.com",
         "Lanús", "Quilmes", "Papelería", "6", "55x35x30 cm", "Entregado a remitente", None, False),
        ("Olga Peña", "22334455", "Av. Pres. Perón 234, San Justo", "11-3535-6677", "olga@email.com",
         "Micaela Rey", "55443322", "Bv. Urquiza 789, Merlo", "220-44-8899", "micaela@email.com",
         "San Justo", "Merlo", "Cosmética", "1", "20x15x8 cm", "Ingresado", None, False),
        ("Taller Centro", "27222333444", "Av. Vélez Sarsfield 1234, Córdoba", "351-333-4455", "taller@centro.com",
         "Diego Silva", "66778899", "Bv. Arturo Rawson 567, Villa María", "353-555-6677", "diego@email.com",
         "Córdoba", "Villa María", "Herramientas", "8", "60x40x25 cm", "En sucursal", None, False),
        ("Nora Castro", "33445566", "Bv. Gálvez 890, Santa Fe", "342-666-7788", "nora@email.com",
         "Pedro Lima", "66554433", "Av. Urquiza 345, Paraná", "343-777-8899", "pedro@email.com",
         "Santa Fe", "Paraná", "Juguetes", "2.7", "28x25x18 cm", "En tránsito", "transportista", False),
        ("ACME", "27444555666", "Av. Argentina 1234, Neuquén", "299-888-9999", "contacto@acme.com",
         "Julia Mora", "88776655", "Calle Mitre 678, Bariloche", "294-444-5566", "julia@email.com",
         "Neuquén", "Bariloche", "Accesorios", "1.8", "25x20x12 cm", "Ingresado", None, False),
    ]
    for i, (rem_nom, rem_dni, rem_dir, rem_tel, rem_email, dest_nom, dest_dni, dest_dir, dest_tel, dest_email, orig, dst, desc, peso, dim, estado, transportista, envio_express) in enumerate(ejemplos):
        fecha_dt = ahora() - datetime.timedelta(days=min(i, 6), hours=i)
        fecha = fecha_dt.strftime("%d/%m/%Y %H:%M")
        tracking = generar_tracking_id()
        nuevo = {
            "tracking_id": tracking,
            "remitente": {
                "nombre": rem_nom,
                "dni": rem_dni,
                "direccion": rem_dir,
                "telefono": rem_tel,
                "email": rem_email
            },
            "destinatario": {
                "nombre": dest_nom,
                "dni": dest_dni,
                "direccion": dest_dir,
                "telefono": dest_tel,
                "email": dest_email
            },
            "origen": orig,
            "destino": dst,
            "descripcion": desc,
            "peso": peso,
            "dimensiones": dim,
            "envio_express": envio_express,
            "estado": estado,
            "fecha_creacion": fecha,
            "historial": [{"estado": "Ingresado", "fecha": fecha, "usuario": "operador", "nota": "Envío de ejemplo."}],
            "creado_por": "operador",
            "transportista": transportista,
            "acepta_ley": True,
            "acepta_ley_fecha": fecha,
        }
        if estado != "Ingresado":
            nuevo["historial"].append({"estado": estado, "fecha": fecha, "usuario": "supervisor", "nota": "Actualización de ejemplo."})
        envios.append(nuevo)
        registrar_auditoria(tracking, "Creación", "Registro de envío semilla.", "sistema")

@app.errorhandler(404)
def page_not_found(e):
    # Forzamos el renderizado de tu archivo
    return render_template('404.html'), 404

# ==========================================
# MOCK API RESTFUL (Devuelve JSON puro)
# ==========================================

@app.route('/api/envios', methods=['GET'])
def api_get_envios():
    """Retorna todos los envíos en formato JSON"""
    return jsonify({
        "status": "success", 
        "total": len(envios), 
        "data": envios
    }), 200

@app.route('/api/envios/<tracking_id>', methods=['GET'])
def api_get_envio_detalle(tracking_id):
    """Retorna el detalle de un envío específico"""
    envio = next((e for e in envios if e['tracking_id'] == tracking_id), None)
    if envio:
        return jsonify({"status": "success", "data": envio}), 200
    return jsonify({"status": "error", "message": "Envío no encontrado"}), 404

@app.route('/api/predecir', methods=['POST'])
def api_predecir_prioridad():
    """Endpoint para predecir la prioridad usando IA"""
    if not modelo_ia:
        return jsonify({"error": "Modelo de IA no disponible"}), 500

    datos = request.json
    try:
        # Extraemos los datos que nos mandan
        distancia = float(datos.get('distancia_km', 0))
        peso = float(datos.get('peso_kg', 0))
        express = int(datos.get('es_express', 0))

        # Le pasamos los datos al cerebro (espera una lista de listas)
        datos_para_ia = pd.DataFrame(
            [[distancia, peso, express]], 
            columns=['distancia_km', 'peso_kg', 'es_express']
        )
        prediccion = modelo_ia.predict(datos_para_ia)
        prioridad_calculada = prediccion[0]

        return jsonify({
            "status": "success",
            "prioridad_sugerida": prioridad_calculada,
            "inputs": datos
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

cargar_datos_ejemplo()
if __name__ == "__main__":
    
    app.run(debug=True)
