# Guía de Contribución para LogiTrack

¡Gracias por tu interés en contribuir a LogiTrack! Para mantener el orden y la calidad del código, por favor seguí estas reglas:

## 1. Estrategia de Ramas (GitFlow Simplificado)
* **`main`**: Código de producción. Siempre debe ser estable.
* **`develop`**: Rama de integración. Todo el código nuevo llega acá primero.
* **`feature/<nombre-tarea>`**: Ramas para nuevas funcionalidades (ej: `feature/actualizacion-prototipo`).
* **`hotfix/<nombre-error>`**: Ramas para arreglar errores urgentes en producción.

## 2. Convención de Commits (Conventional Commits)
Tus mensajes de commit deben ser descriptivos y usar prefijos:
* `feat:` Para nuevas funcionalidades (ej: *feat: agrega IA para prioridad*).
* `fix:` Para solución de errores (ej: *fix: corrige error en tabla de envíos*).
* `docs:` Para cambios en documentación (ej: *docs: actualiza README*).
* `test:` Para agregar o modificar pruebas (ej: *test: agrega pruebas de login*).
* `refactor:` Para reescribir código sin cambiar su comportamiento.

## 3. Pasos para subir tu código (Pull Requests)
1. Creá tu rama `feature/...` desde `develop` o `main`.
2. Hacé tus cambios y commits respetando las convenciones.
3. Asegurate de que los tests pasen localmente (`pytest tests/`).
4. Subí tu rama (`git push`) y abrí un Pull Request (PR) hacia `main`.
5. Esperá la revisión de al menos un compañero (Code Review) y que el pipeline de GitHub Actions (CI) se ponga en verde.