# TP-inicial-LogiTrack

https://logitrack-fj41.onrender.com

# LogiTrack — Sistema Federal de Gestión de Envíos

Prototipo funcional (MVP) desarrollado con Flask (Python). 
Incluye funcionalidades de despliegue continuo (CI/CD), pruebas automatizadas, Mock API RESTful y un modelo de Machine Learning para asignación inteligente de prioridades. Almacenamiento en memoria (sin base de datos real en esta fase).

---

## 📂 Estructura del proyecto

```text
logitrack/
├── app.py                  # Aplicación Flask principal (Backend & Mock API)
├── ml_prioridad.py         # Script de entrenamiento del modelo de IA
├── test_app.py             # Suite de pruebas automatizadas (QA)
├── requirements.txt        # Dependencias del proyecto
├── README.md               # Documentación principal
├── models/                 # Cerebros de Inteligencia Artificial
│   └── modelo_prioridad.pkl
├── docs/                   # Documentación técnica
│   └── swagger.yaml        # Contrato OpenAPI (Swagger)
├── static/
│   ├── css/style.css       # Estilos globales
│   └── js/main.js          # Scripts del cliente
└── templates/              # Vistas HTML (Jinja2)
    ├── base.html           # Layout base con navbar
    ├── login.html          # Pantalla de inicio de sesión
    ├── panel.html          # Dashboard con estadísticas
    ├── listar.html         # Listado, búsqueda y prioridad IA
    ├── nuevo_envio.html    # Formulario de alta
    └── detalle.html        # Detalle, ofuscación y auditoría

---

## Requisitos

- Python 3.8 o superior
- pip

---

## Instalación y ejecución

### 1. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Entrenar el modelo de Inteligencia Artificial (Opcional/Primera vez)
Genera el dataset semilla y entrena el algoritmo Random Forest para predecir prioridades.

```bash
python ml_prioridad.py
```

### 4.Ejecutar pruebas automatizadas (QA)
Ejecuta la suite de pruebas unitarias y de integración configuradas para el pipeline de CI.

```bash
pytest test_app.py -v
```

### 5. Ejecutar la aplicación

```bash
python app.py
```

### 6. Abrir en el navegador

```
http://localhost:5000
```

---

## Usuarios de prueba

| Usuario        | Contraseña | Rol           |
|----------------|------------|---------------|
| operador       | op123      | Operador      |
| supervisor     | sup123     | Supervisor    |
| transportista  | tra123     | Transportista |

---

## Funcionalidades destacadas (MVP)

- **Inteligencia Artificial (Machine Learning):** Asignación automática de prioridad logística `Alta, Media, Baja` mediante un modelo Random Forest basado en distancia, peso y modalidad.

- **Mock API RESTful:** `/api/envios` documentada con estándar OpenAPI `Swagger` para futuras integraciones móviles.

- **Privacidad desde el Diseño `Ley 25.326`:** Ofuscación dinámica de datos sensibles `DNI` según el rol del usuario mediante renderizado SSR.

- **Auditoría Inmutable:** Registro automático de usuario, fecha y cambios de estado logístico.

- **Alta de envío:** Generación automática de Tracking ID `LT-XXXXXXXX` y validación de términos de servicio.

- **Dashboard y Búsqueda:** Tabla paginable, ordenamiento dinámico, filtros por fecha y estadísticas en tiempo real.


## Notas

- Los datos se pierden al reiniciar el servidor (almacenamiento en memoria).
- Para persistencia real, reemplazar la lista `envios` por una base de datos (SQLite, PostgreSQL, etc.).
- Persistencia: Los datos se reinician al apagar el servidor (almacenamiento en memoria para agilidad del MVP).
- Desacoplamiento: El modelo predictivo fue entrenado de forma aislada y acoplado al backend vía serialización (joblib), garantizando la separación de responsabilidades.
- CI/CD: El repositorio cuenta con GitHub Actions configurado para validación de código (Flake8) y ejecución de tests (Pytest) ante cada Pull Request.
